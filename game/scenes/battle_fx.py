"""Battle move effects, drawn in code (no art): particles, beams, bolts,
rings, screen shake, flash and tint.

A move's effect comes in two parts, both from `RECIPES` (by move name;
`_fallback` by type for the rest):

- `launch`, on the attack animation's strike frame: what leaves the user
  (a fireball, a beam, a gust...); returns how long it takes to reach the
  target, which the battle waits before the hit lands;
- `land`, as the hit lands (or misses: `Ctx.landed`): what happens at the
  target (a burst, flames left burning, rocks crumbling...); returns how
  long it lingers, which the battle holds for.

The bigger the move (`Ctx.p`: its power, 0..1 at 120+), the bigger the
show: more particles, a longer shake, a flash. Charging moves (Solar Beam,
Sky Attack...) gather on the user in their first round (`charge`).

`Fx` holds everything alive: `draw_back` (behind the Pokémon: tint, wave
and ground effects), `draw_front` (over them), and `offset` (the shake).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from ..mechanics.type_chart import COLORS

Color = tuple[int, int, int]
Point = tuple[float, float]

WHITE: Color = (255, 255, 255)
BODY_SCALE = 1.4  # particle bodies are drawn this much bigger than their sizes say ...
UNSCALED = {"ring", "slash", "line", "spark", "custom"}  # ... except these (sizes are lengths and radii)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c0: Color, c1: Color, t: float) -> Color:
    return (round(lerp(c0[0], c1[0], t)), round(lerp(c0[1], c1[1], t)), round(lerp(c0[2], c1[2], t)))


def scale(c: Color, k: float) -> Color:
    k = max(0.0, min(1.0, k))
    return (round(c[0] * k), round(c[1] * k), round(c[2] * k))


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 2


# ------------------------------------------------------------------ sprites

_cache: dict = {}


def _cached(key, make):
    if key not in _cache:
        if len(_cache) > 3000:
            _cache.clear()
        _cache[key] = make()
    return _cache[key]


def _q(c: Color) -> Color:  # (quantized, to keep the caches small)
    return (c[0] & ~7, c[1] & ~7, c[2] & ~7)


def glow_surface(radius: int, color: Color) -> pygame.Surface:
    """A soft round glow, for additive blending: `color` in the middle,
    fading to black at `radius`."""
    radius, color = max(1, radius), _q(color)

    def make():
        s = pygame.Surface((radius * 2 + 1, radius * 2 + 1))
        for r in range(radius, 0, -1):
            k = (1 - r / (radius + 1)) ** 1.6
            pygame.draw.circle(s, scale(color, k), (radius, radius), r)
        return s
    return _cached(("glow", radius, color), make)


def soft_surface(radius: int, color: Color, alpha: int) -> pygame.Surface:
    """A soft-edged see-through blob (smoke, dust, gas, powder)."""
    radius, color, alpha = max(1, radius), _q(color), alpha & ~15

    def make():
        s = pygame.Surface((radius * 2 + 1, radius * 2 + 1), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            a = round(alpha * min(1.0, 1.4 * (1 - r / (radius + 1))))
            pygame.draw.circle(s, (*color, a), (radius, radius), r)
        return s
    return _cached(("soft", radius, color, alpha), make)


def add(surface: pygame.Surface, img: pygame.Surface, center: Point) -> None:
    surface.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))), special_flags=pygame.BLEND_RGB_ADD)


def sub(surface: pygame.Surface, img: pygame.Surface, center: Point) -> None:
    surface.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))), special_flags=pygame.BLEND_RGB_SUB)


def add_line(surface: pygame.Surface, color: Color, a: Point, b: Point, width: int = 1) -> None:
    """A line, added to what's under it (light)."""
    x0, y0 = min(a[0], b[0]) - width - 1, min(a[1], b[1]) - width - 1
    w, h = int(abs(a[0] - b[0]) + 2 * width + 3), int(abs(a[1] - b[1]) + 2 * width + 3)
    if w * h > 400_000:
        return
    s = pygame.Surface((w, h))
    pygame.draw.line(s, color, (a[0] - x0, a[1] - y0), (b[0] - x0, b[1] - y0), width)
    surface.blit(s, (round(x0), round(y0)), special_flags=pygame.BLEND_RGB_ADD)


def add_lines(surface: pygame.Surface, color: Color, points: list[Point], width: int = 1) -> None:
    if len(points) < 2:
        return
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = min(xs) - width - 1, min(ys) - width - 1
    w, h = int(max(xs) - x0 + width + 3), int(max(ys) - y0 + width + 3)
    if w * h > 400_000:
        return
    s = pygame.Surface((w, h))
    pygame.draw.lines(s, color, False, [(x - x0, y - y0) for x, y in points], width)
    surface.blit(s, (round(x0), round(y0)), special_flags=pygame.BLEND_RGB_ADD)


def paint_lines(surface: pygame.Surface, color: Color, alpha: float, points: list[Point], width: int = 1) -> None:
    """Lines painted see-through (`alpha` 0..1): they show on any backdrop."""
    if len(points) < 2 or alpha <= 0.02:
        return
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = min(xs) - width - 1, min(ys) - width - 1
    w, h = int(max(xs) - x0 + width + 3), int(max(ys) - y0 + width + 3)
    if w * h > 400_000:
        return
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.lines(s, (*color, round(255 * min(1.0, alpha))), False, [(x - x0, y - y0) for x, y in points], width)
    surface.blit(s, (round(x0), round(y0)))


def add_ring(surface: pygame.Surface, color: Color, center: Point, radius: float, width: int = 1,
             squash: float = 1.0) -> None:
    r = max(2, round(radius))
    rh = max(2, round(radius * squash))
    s = pygame.Surface((2 * r + 2, 2 * rh + 2))
    pygame.draw.ellipse(s, color, s.get_rect(), min(width, rh))
    surface.blit(s, s.get_rect(center=(round(center[0]), round(center[1]))), special_flags=pygame.BLEND_RGB_ADD)


def paint_ring(surface: pygame.Surface, color: Color, alpha: float, center: Point, radius: float, width: int = 1,
               squash: float = 1.0) -> None:
    r = max(2, round(radius))
    rh = max(2, round(radius * squash))
    s = pygame.Surface((2 * r + 2, 2 * rh + 2), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*color, round(255 * max(0.0, min(1.0, alpha)))), s.get_rect(), min(width, rh))
    surface.blit(s, s.get_rect(center=(round(center[0]), round(center[1]))))


def _rot(points, angle, cx, cy):
    c, s = math.cos(angle), math.sin(angle)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in points]


# ---------------------------------------------------------------- particles

class Particle:
    """One bit of an effect. Moves by its velocity (with acceleration and
    drag), or along `path(p, u)` (u: 0..1 through its life) if it has one;
    `emit(fx, p, dt)` runs each frame (trails). Waits `delay` first."""

    __slots__ = ("x", "y", "vx", "vy", "ax", "ay", "drag", "life", "age", "s0", "s1", "c0", "c1",
                 "kind", "rot", "spin", "path", "emit", "data", "front", "px", "py")

    def __init__(self, x, y, vx=0.0, vy=0.0, life=0.5, size=3.0, size1=None, color=WHITE, color1=None,
                 kind="glow", ax=0.0, ay=0.0, drag=0.0, delay=0.0, rot=0.0, spin=0.0, path=None, emit=None,
                 data=None, front=True):
        self.x, self.y, self.vx, self.vy, self.ax, self.ay = x, y, vx, vy, ax, ay
        self.px, self.py = x, y
        self.drag, self.life, self.age = drag, max(0.01, life), -delay
        self.s0, self.s1 = size, size if size1 is None else size1
        self.c0, self.c1 = color, color if color1 is None else color1
        self.kind, self.rot, self.spin = kind, rot, spin
        self.path, self.emit, self.data, self.front = path, emit, data, front

    @property
    def u(self) -> float:
        return max(0.0, min(1.0, self.age / self.life))

    @property
    def size(self) -> float:
        k = 1.0 if self.kind in UNSCALED else BODY_SCALE
        return lerp(self.s0, self.s1, self.u) * k

    @property
    def color(self) -> Color:
        return mix(self.c0, self.c1, self.u)

    def update(self, fx: "Fx", dt: float) -> bool:
        self.age += dt
        if self.age < 0:
            return True
        self.px, self.py = self.x, self.y
        if self.path:
            self.x, self.y = self.path(self, self.u)
        else:
            self.vx += self.ax * dt
            self.vy += self.ay * dt
            if self.drag:
                k = max(0.0, 1 - self.drag * dt)
                self.vx *= k
                self.vy *= k
            self.x += self.vx * dt
            self.y += self.vy * dt
        self.rot += self.spin * dt
        if self.emit:
            self.emit(fx, self, dt)
        return self.age < self.life

    def draw(self, s: pygame.Surface) -> None:
        if self.age < 0:
            return
        DRAW[self.kind](self, s)


def _fade(p) -> float:
    return min(1.0, (1 - p.u) * 1.6)


def _d_glow(p, s):  # a flame, a spark of light: a see-through body with a halo
    r = p.size
    if r > 14:  # a big glow is light only (an aura, a halo), no body
        add(s, glow_surface(round(r), p.color), (p.x, p.y))
        return
    if r >= 0.6:
        k = _fade(p)
        body = soft_surface(max(1, round(r * 0.75)), p.c0 if p.u < 0.3 else p.color, round(255 * k))
        s.blit(body, body.get_rect(center=(round(p.x), round(p.y))))
        add(s, glow_surface(max(1, round(r * 1.5)), scale(p.color, 0.45 * k)), (p.x, p.y))


def _d_core(p, s):  # a fireball / energy ball: a glow with a white-hot middle
    r = round(p.size)
    if r >= 1:
        add(s, glow_surface(r * 2, scale(p.color, 0.7)), (p.x, p.y))
        body = soft_surface(r, p.color, 255)
        s.blit(body, body.get_rect(center=(round(p.x), round(p.y))))
        pygame.draw.circle(s, mix(p.color, WHITE, 0.7), (round(p.x), round(p.y)), max(1, r // 2))


def _d_spark(p, s):
    n = p.data or 0.04
    dx, dy = (p.x - p.px), (p.y - p.py)
    if p.path is None:
        dx, dy = p.vx * n, p.vy * n
    k = _fade(p)
    add_line(s, scale(p.color, 0.6 * k), (p.x - dx, p.y - dy), (p.x, p.y), max(1, round(p.size)) + 1)
    paint_lines(s, mix(p.c0, WHITE, 0.3), k, [(p.x - dx * 0.6, p.y - dy * 0.6), (p.x, p.y)], max(1, round(p.size)))


def _d_dark(p, s):  # a shadow: takes light away
    r = round(p.size)
    if r >= 1:
        sub(s, glow_surface(r, p.color), (p.x, p.y))


def _d_soft(p, s):
    r = round(p.size)
    if r >= 1:
        a = int(255 * (p.data if p.data is not None else 0.7) * (1 - p.u) ** 0.7)
        img = soft_surface(r, p.color, a)
        s.blit(img, img.get_rect(center=(round(p.x), round(p.y))))


def _d_dot(p, s):
    r = p.size
    if r >= 0.5:
        pygame.draw.circle(s, p.color, (round(p.x), round(p.y)), max(1, round(r)))


def _outlined(s, color, pts, dark=None):
    pygame.draw.polygon(s, color, pts)
    pygame.draw.polygon(s, dark or scale(color, 0.45), pts, 1)


def _d_leaf(p, s):
    r = max(2.0, p.size)
    pts = _rot([(-r, 0), (0, -r * 0.45), (r, 0), (0, r * 0.45)], p.rot, p.x, p.y)
    _outlined(s, p.color, pts)
    a, b = _rot([(-r, 0), (r, 0)], p.rot, p.x, p.y)
    pygame.draw.line(s, scale(p.color, 0.6), a, b)


def _d_petal(p, s):
    r = max(2.0, p.size)
    pts = _rot([(-r, 0), (-r * 0.3, -r * 0.6), (r * 0.6, -r * 0.3), (r, 0), (0, r * 0.5)], p.rot, p.x, p.y)
    _outlined(s, p.color, pts, mix(p.color, (120, 40, 80), 0.6))


def _d_rock(p, s):
    r = max(2.0, p.size)
    shape = p.data or (1, 0.8, 1, 0.9, 0.75, 1)
    n = len(shape)
    pts = _rot([(math.cos(i / n * 6.283) * r * k, math.sin(i / n * 6.283) * r * k) for i, k in enumerate(shape)],
               p.rot, p.x, p.y)
    pygame.draw.polygon(s, p.color, pts)
    lit = _rot([(-r * 0.4, -r * 0.4), (r * 0.1, -r * 0.6), (-r * 0.1, -r * 0.1)], p.rot, p.x, p.y)
    pygame.draw.polygon(s, mix(p.color, WHITE, 0.3), lit)
    pygame.draw.polygon(s, (40, 30, 25), pts, 1)


def _d_bubble(p, s):
    r = max(2, round(p.size))
    c = (round(p.x), round(p.y))
    pygame.draw.circle(s, mix(p.color, WHITE, 0.2), c, r, 1)
    s.set_at((c[0] - r // 2, c[1] - r // 2), WHITE)
    if r > 3:
        s.set_at((c[0] - r // 2 + 1, c[1] - r // 2), WHITE)


def _d_drop(p, s):
    r = max(1.0, p.size)
    ang = math.atan2(p.vy, p.vx) if (p.vx or p.vy) else math.pi / 2
    pts = _rot([(r * 1.8, 0), (0, -r), (-r, 0), (0, r)], ang, p.x, p.y)
    pygame.draw.polygon(s, p.color, pts)
    pygame.draw.polygon(s, scale(p.color, 0.6), pts, 1)


def _d_ring(p, s):
    squash = p.data if p.data is not None else 1.0
    w = 2 if p.size > 10 else 1
    paint_ring(s, p.color, 0.9 * (1 - p.u), (p.x, p.y), p.size, w, squash)
    add_ring(s, scale(p.color, 0.5 * (1 - p.u)), (p.x, p.y), p.size, w + 1, squash)


def _d_star(p, s):  # a four-point twinkle
    r = max(1.0, p.size)
    c = scale(p.color, 1 - p.u * 0.5)
    pts = _rot([(0, -r), (r * 0.25, -r * 0.25), (r, 0), (r * 0.25, r * 0.25), (0, r), (-r * 0.25, r * 0.25),
                (-r, 0), (-r * 0.25, -r * 0.25)], p.rot, p.x, p.y)
    pygame.draw.polygon(s, c, pts)


def _d_star5(p, s):  # Swift's stars
    r = max(2.0, p.size)
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = i * math.pi / 5 - math.pi / 2
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    pts = _rot(pts, p.rot, p.x, p.y)
    _outlined(s, p.color, pts, (150, 110, 20))


def _d_burst(p, s):  # an impact star: spiky, white in the middle
    r = max(2.0, p.size) * (1 - p.u * 0.3)
    n = 8
    pts = []
    for i in range(n * 2):
        rr = r if i % 2 == 0 else r * 0.45
        a = i * math.pi / n + p.rot
        pts.append((p.x + math.cos(a) * rr, p.y + math.sin(a) * rr))
    k = 1 - p.u
    layer = pygame.Surface((int(r * 2 + 4), int(r * 2 + 4)), pygame.SRCALPHA)
    off = (p.x - r - 2, p.y - r - 2)
    local = [(x - off[0], y - off[1]) for x, y in pts]
    a = round(255 * min(1.0, k * 1.5))
    pygame.draw.polygon(layer, (*p.color, a), local)
    inner = [((x - off[0] - r - 2) * 0.5 + r + 2, (y - off[1] - r - 2) * 0.5 + r + 2) for x, y in pts]
    pygame.draw.polygon(layer, (255, 255, 255, a), inner)
    s.blit(layer, (round(off[0]), round(off[1])))


def _d_slash(p, s):  # a claw / blade stroke: a white crescent sweeping across
    length = p.size
    ang = p.rot
    k = 1 - p.u
    grow = min(1.0, p.u * 3)
    pts = []
    for i in range(9):
        t = i / 8 * grow
        x = (t - 0.5) * length
        y = math.sin(t * math.pi) * length * 0.18
        pts.append((x, y))
    pts = _rot(pts, ang, p.x, p.y)
    paint_lines(s, p.color, k * 0.7, pts, 4)
    paint_lines(s, WHITE, k, pts, 2)


def _d_note(p, s):
    x, y = round(p.x), round(p.y)
    c = p.color
    pygame.draw.circle(s, c, (x, y), 2)
    pygame.draw.line(s, c, (x + 2, y), (x + 2, y - 7))
    pygame.draw.line(s, c, (x + 2, y - 7), (x + 5, y - 5))


def _d_heart(p, s):
    r = max(2, round(p.size))
    x, y = round(p.x), round(p.y)
    pygame.draw.circle(s, p.color, (x - r // 2, y - r // 3), (r + 1) // 2)
    pygame.draw.circle(s, p.color, (x + r // 2, y - r // 3), (r + 1) // 2)
    pygame.draw.polygon(s, p.color, [(x - r, y - r // 4), (x + r, y - r // 4), (x, y + r)])


def _d_zzz(p, s):
    r = max(2, round(p.size))
    x, y = round(p.x), round(p.y)
    pygame.draw.lines(s, p.color, False, [(x - r, y - r), (x + r, y - r), (x - r, y + r), (x + r, y + r)])


def _d_coin(p, s):
    r = max(2, round(p.size))
    w = max(1, round(abs(math.cos(p.rot)) * r))
    rect = pygame.Rect(0, 0, w * 2, r * 2)
    rect.center = (round(p.x), round(p.y))
    pygame.draw.ellipse(s, (250, 210, 60), rect)
    pygame.draw.ellipse(s, (150, 100, 20), rect, 1)


def _d_bone(p, s):
    r = max(4.0, p.size)
    a, b = _rot([(-r, 0), (r, 0)], p.rot, p.x, p.y)
    pygame.draw.line(s, (40, 35, 30), a, b, 5)
    pygame.draw.line(s, (240, 235, 215), a, b, 3)
    for e in (a, b):
        pygame.draw.circle(s, (40, 35, 30), (round(e[0]), round(e[1])), 3)
        pygame.draw.circle(s, (240, 235, 215), (round(e[0]), round(e[1])), 2)


def _d_needle(p, s):
    r = max(3.0, p.size)
    ang = math.atan2(p.y - p.py, p.x - p.px) if (p.x != p.px or p.y != p.py) else p.rot
    a, b = _rot([(-r, 0), (r, 0)], ang, p.x, p.y)
    pygame.draw.line(s, scale(p.color, 0.5), a, b, 3)
    pygame.draw.line(s, p.color, a, b, 1)
    add(s, glow_surface(3, scale(p.color, 0.6)), b)


def _d_shard(p, s):  # ice
    r = max(2.0, p.size)
    pts = _rot([(0, -r * 1.4), (r * 0.5, 0), (0, r * 1.4), (-r * 0.5, 0)], p.rot, p.x, p.y)
    pygame.draw.polygon(s, p.color, pts)
    pygame.draw.polygon(s, WHITE, pts, 1)


def _d_feather(p, s):
    r = max(3.0, p.size)
    pts = _rot([(-r, 0), (-r * 0.2, -r * 0.35), (r, 0), (-r * 0.2, r * 0.35)], p.rot, p.x, p.y)
    _outlined(s, p.color, pts)


def _d_egg(p, s):
    r = max(3, round(p.size))
    rect = pygame.Rect(0, 0, r * 2, round(r * 2.5))
    rect.center = (round(p.x), round(p.y))
    pygame.draw.ellipse(s, (250, 245, 225), rect)
    pygame.draw.ellipse(s, (120, 100, 80), rect, 1)
    pygame.draw.circle(s, (230, 120, 90), (rect.centerx - 2, rect.centery), 2)


def _d_line(p, s):  # a speed / wind streak, fixed length along its velocity
    n = p.data or 14
    sp = math.hypot(p.vx, p.vy) or 1
    dx, dy = p.vx / sp * n, p.vy / sp * n
    paint_lines(s, p.color, 0.85 * (1 - p.u), [(p.x - dx, p.y - dy), (p.x, p.y)], max(1, round(p.size)))


def _d_custom(p, s):
    p.data(p, s)


DRAW = {
    "glow": _d_glow, "core": _d_core, "spark": _d_spark, "dark": _d_dark, "soft": _d_soft, "dot": _d_dot,
    "leaf": _d_leaf, "petal": _d_petal, "rock": _d_rock, "bubble": _d_bubble, "drop": _d_drop, "ring": _d_ring,
    "star": _d_star, "star5": _d_star5, "burst": _d_burst, "slash": _d_slash, "note": _d_note,
    "heart": _d_heart, "zzz": _d_zzz, "coin": _d_coin, "bone": _d_bone, "needle": _d_needle,
    "shard": _d_shard, "feather": _d_feather, "egg": _d_egg, "line": _d_line, "custom": _d_custom,
}


# ------------------------------------------------------------- beams, bolts

class Beam:
    """A beam from `a` to `b`: it shoots out over `reach` seconds, holds,
    then thins away. kind "beam" (a glowing column), "bolt" (lightning,
    jagged and flickering), "rainbow" (Aurora Beam), "vine" (a green whip,
    solid)."""

    def __init__(self, a: Point, b: Point, life: float, width: float, color: Color, kind: str = "beam",
                 reach: float = 0.12, delay: float = 0.0, core: Color = WHITE, jag: float = 10, branches: int = 0):
        self.a, self.b, self.life, self.width, self.color, self.kind = a, b, life, width, color, kind
        self.reach, self.age, self.core, self.jag, self.branches = reach, -delay, core, jag, branches
        self.front = True
        self._pts: list[Point] = []
        self._t = 1.0

    def update(self, fx: "Fx", dt: float) -> bool:
        self.age += dt
        self._t += dt
        if self.kind == "bolt" and self._t > 0.05:  # a new jag every few frames
            self._t = 0.0
            self._pts = _zigzag(self.a, self.b, self.jag)
            self._branches = [_zigzag(self._pts[i], (self._pts[i][0] + random.uniform(-30, 30),
                                                     self._pts[i][1] + random.uniform(10, 40)), self.jag * 0.6)
                              for i in random.sample(range(1, len(self._pts) - 1),
                                                     min(self.branches, max(0, len(self._pts) - 2)))]
        return self.age < self.life

    def end(self) -> Point:
        t = min(1.0, max(0.0, self.age) / self.reach) if self.reach else 1.0
        return (lerp(self.a[0], self.b[0], t), lerp(self.a[1], self.b[1], t))

    def draw(self, s: pygame.Surface) -> None:
        if self.age < 0:
            return
        fade = 1.0 if self.age < self.life * 0.7 else max(0.0, (self.life - self.age) / (self.life * 0.3))
        e = self.end()
        if self.kind == "bolt":
            k = fade * (0.6 + 0.4 * random.random())
            w = max(1, round(self.width))
            pts = self._pts or [self.a, self.b]
            add_lines(s, scale(self.color, k * 0.5), pts, w + 5)
            paint_lines(s, self.color, k, pts, w + 2)
            paint_lines(s, WHITE, k, pts, max(1, w))
            for br in getattr(self, "_branches", []):
                paint_lines(s, self.color, k * 0.9, br, max(1, w - 1))
                paint_lines(s, WHITE, k * 0.9, br, 1)
            add(s, glow_surface(round(6 + self.width * 3), scale(self.color, k * 0.8)), pts[-1])
            return
        if self.kind == "vine":
            n = 14
            dx, dy = e[0] - self.a[0], e[1] - self.a[1]
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length, dx / length
            pts = [(self.a[0] + dx * i / n + nx * math.sin(i / n * 7 + self.age * 14) * 5,
                    self.a[1] + dy * i / n + ny * math.sin(i / n * 7 + self.age * 14) * 5) for i in range(n + 1)]
            pygame.draw.lines(s, (30, 70, 30), False, pts, round(self.width) + 2)
            pygame.draw.lines(s, self.color, False, pts, round(self.width))
            for i in range(2, n, 4):
                pygame.draw.circle(s, (120, 200, 90), (round(pts[i][0]), round(pts[i][1])), 2)
            return
        wob = 1 + 0.18 * math.sin(self.age * 40)
        w = self.width * wob * (0.4 + 0.6 * fade)
        color = self.color
        if self.kind == "rainbow":
            color = _hue(self.age * 1.5)
        add_line(s, scale(color, 0.4 * fade), self.a, e, round(w * 2.4) + 2)
        paint_lines(s, color, 0.55 * fade, [self.a, e], round(w * 1.5) + 1)
        paint_lines(s, color, fade, [self.a, e], round(w) + 1)
        paint_lines(s, self.core, fade, [self.a, e], max(1, round(w * 0.45)))
        add(s, glow_surface(round(w * 1.6 + 4), scale(color, fade)), self.a)
        add(s, glow_surface(round(w * 2 + 6), scale(color, fade)), e)


def _zigzag(a: Point, b: Point, jag: float) -> list[Point]:
    n = max(3, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 14))
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    pts = [a]
    for i in range(1, n):
        t = i / n
        o = random.uniform(-jag, jag)
        pts.append((a[0] + dx * t + nx * o, a[1] + dy * t + ny * o))
    pts.append(b)
    return pts


def _hue(h: float) -> Color:
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    q, t = 1 - f, f
    r, g, b = [(1, t, 0), (q, 1, 0), (0, 1, t), (0, q, 1), (t, 0, 1), (1, 0, q)][i % 6]
    return (round(140 + 115 * r), round(140 + 115 * g), round(140 + 115 * b))


class Custom:
    """Anything else: `draw(s, u)` over its life (u: 0..1); `back` draws it
    behind the Pokémon."""

    def __init__(self, life: float, draw, delay: float = 0.0, back: bool = False):
        self.life, self.fn, self.age, self.front = life, draw, -delay, not back

    def update(self, fx: "Fx", dt: float) -> bool:
        self.age += dt
        return self.age < self.life

    def draw(self, s: pygame.Surface) -> None:
        if self.age >= 0:
            self.fn(s, self.age / self.life)


# --------------------------------------------------------------- the system

@dataclass
class Ctx:
    """Where a move happens: the user's body and mouth, which way it faces
    (+1 right, -1 left), the targets' bodies, and the move's size (`p`:
    0..1)."""
    user: pygame.Rect
    mouth: Point
    dir: int
    targets: list[pygame.Rect]
    p: float
    landed: bool = True
    hits: int = 1

    @property
    def target(self) -> pygame.Rect:
        return self.targets[0] if self.targets else self.user

    @property
    def tc(self) -> Point:
        return self.target.center

    @property
    def dist(self) -> float:
        return math.hypot(self.tc[0] - self.mouth[0], self.tc[1] - self.mouth[1])

    def flight(self, speed: float, lo: float = 0.18, hi: float = 0.7) -> float:
        """Seconds a projectile at `speed` px/s takes to reach the target."""
        return max(lo, min(hi, self.dist / speed))


class Fx:
    FIELD_H = 264

    def __init__(self):
        self.items: list = []
        self.shake_amp = 0.0
        self.shake_t = 0.0
        self.flash_t = 0.0
        self.flash_life = 1.0
        self.flash_color: Color = WHITE
        self.flash_k = 0.4
        self.tint: tuple[Color, float, float, float] | None = None  # color, strength, age, life
        self.t = 0.0

    # making
    def part(self, x, y, **kw) -> Particle:
        p = Particle(x, y, **kw)
        self.items.append(p)
        return p

    def put(self, thing):
        self.items.append(thing)
        return thing

    def shake(self, amp: float, time: float) -> None:
        self.shake_amp = max(self.shake_amp if self.shake_t > 0 else 0.0, amp)
        self.shake_t = max(self.shake_t, time)

    def flash(self, time: float = 0.25, color: Color = WHITE, strength: float = 0.4) -> None:
        """The field lights up (`strength` 1: white) and fades back."""
        self.flash_t, self.flash_life, self.flash_color, self.flash_k = time, time, color, strength

    def darken(self, color: Color, strength: float, life: float) -> None:
        """The field fades towards `color` (and back) over `life` seconds."""
        self.tint = (color, strength, 0.0, life)

    # running
    def update(self, dt: float) -> None:
        self.t += dt
        self.items = [i for i in self.items if i.update(self, dt)]
        self.shake_t = max(0.0, self.shake_t - dt)
        self.flash_t = max(0.0, self.flash_t - dt)
        if self.tint:
            c, k, age, life = self.tint
            age += dt
            self.tint = (c, k, age, life) if age < life else None

    @property
    def busy(self) -> bool:
        return bool(self.items)

    @property
    def offset(self) -> tuple[int, int]:
        if not self.shake_t:
            return (0, 0)
        a = self.shake_amp * min(1.0, self.shake_t * 4)
        return (round(math.sin(self.t * 71) * a), round(math.cos(self.t * 53) * a * 0.6))

    def draw_back(self, s: pygame.Surface) -> None:
        if self.tint:
            c, k, age, life = self.tint
            u = age / life
            strength = k * min(1.0, u * 5, (1 - u) * 4)
            if strength > 0:
                layer = pygame.Surface((s.get_width(), self.FIELD_H), pygame.SRCALPHA)
                layer.fill((*c, round(255 * strength)))
                s.blit(layer, (0, 0))
        for i in self.items:
            if not i.front:
                i.draw(s)

    def draw_front(self, s: pygame.Surface) -> None:
        for i in self.items:
            if i.front:
                i.draw(s)
        if self.flash_t:
            k = self.flash_t / self.flash_life
            layer = pygame.Surface((s.get_width(), self.FIELD_H))
            layer.fill(scale(self.flash_color, k * self.flash_k))
            s.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # a move
    def launch(self, move, ctx: Ctx, charging: bool = False) -> float:
        r = RECIPES.get(move.name) or _fallback(move)
        if charging:
            return (r.charge or _charge_glow)(self, ctx) or 0.0
        return (r.launch(self, ctx) if r.launch else 0.0) or 0.0

    def land(self, move, ctx: Ctx) -> float:
        r = RECIPES.get(move.name) or _fallback(move)
        if not r.land:
            return 0.0
        return r.land(self, ctx) or 0.0


@dataclass
class Recipe:
    launch: object = None
    land: object = None
    charge: object = None


def power_of(move) -> float:
    if move.fixed or move.halve:
        return 0.45
    return max(0.15, min(1.0, move.power * move.hits[1] ** 0.5 / 120)) if move.power else 0.25


# ============================================================ the building blocks

R = random.uniform


def _spray(fx: Fx, pos: Point, n: float, colors, speed=(40, 120), life=(0.3, 0.6), size=(1, 2),
           kind="spark", gravity=0.0, drag=3.0, angle=(0, 6.283), delay=0.0, spin=0.0, size1=None, data=None):
    """`n` bits flying out from `pos`. Light (sparks, glows) fades to dark;
    matter (rocks, drops...) keeps its colour and shrinks."""
    light = kind in ("spark", "glow", "core", "line")
    for _ in range(int(n)):
        a = R(*angle)
        v = R(*speed)
        c = random.choice(colors) if isinstance(colors, list) else colors
        sz = R(*size)
        fx.part(pos[0] + R(-2, 2), pos[1] + R(-2, 2), vx=math.cos(a) * v, vy=math.sin(a) * v, ay=gravity,
                drag=drag, life=R(*life), size=sz, size1=(sz * 0.3 if light else sz * 0.6) if size1 is None else size1,
                color=c, color1=scale(c, 0.3) if light else c, kind=kind, delay=delay, rot=R(0, 6.28),
                spin=R(-spin, spin), data=data)


def _impact(fx: Fx, pos: Point, color: Color, p: float, delay: float = 0.0) -> None:
    """The basic hit: an impact star, sparks and (big moves) a shake."""
    fx.part(*pos, life=0.22, size=8 + 10 * p, size1=12 + 16 * p, color=color, kind="burst", rot=R(0, 1), delay=delay)
    _spray(fx, pos, 6 + 14 * p, [mix(color, WHITE, 0.5), color], speed=(60, 140 + 120 * p), life=(0.2, 0.4),
           delay=delay)
    if p > 0.5:
        fx.shake(1 + 3 * p, 0.15 + 0.25 * p)


def _ring(fx: Fx, pos: Point, color: Color, r0: float, r1: float, life: float, delay=0.0, squash=1.0):
    fx.part(*pos, life=life, size=r0, size1=r1, color=color, kind="ring", data=squash, delay=delay)


def _arc(a: Point, b: Point, height: float):
    def path(p, u):
        return (lerp(a[0], b[0], u), lerp(a[1], b[1], u) - height * 4 * u * (1 - u))
    return path


def _line(a: Point, b: Point, ease=None):
    def path(p, u):
        uu = ease(u) if ease else u
        return (lerp(a[0], b[0], uu), lerp(a[1], b[1], uu))
    return path


def _trail(kind="glow", colors=((255, 160, 40),), rate=60, size=(2, 4), life=(0.15, 0.3), spread=10, rise=0.0,
           data=None):
    acc = [0.0]

    def emit(fx, p, dt):
        acc[0] += rate * dt
        while acc[0] >= 1:
            acc[0] -= 1
            c = random.choice(colors)
            sz = R(*size)
            fx.part(p.x + R(-2, 2), p.y + R(-2, 2), vx=R(-spread, spread), vy=R(-spread, spread) - rise,
                    life=R(*life), size=sz, size1=sz * 0.2, color=c, color1=scale(c, 0.2), kind=kind, data=data)
    return emit


def _projectile(fx: Fx, a: Point, b: Point, t: float, kind="core", size=4.0, color=(255, 150, 40), height=0.0,
                delay=0.0, trail=None, spin=0.0, size1=None, data=None) -> Particle:
    return fx.part(*a, life=t, size=size, size1=size1, color=color, kind=kind, delay=delay,
                   path=_arc(a, b, height), emit=trail, spin=spin, data=data)


def _jitter(c: pygame.Rect, k: float = 0.3) -> Point:
    return (c.centerx + R(-c.w * k, c.w * k), c.centery + R(-c.h * k, c.h * k))


def _foot(c: pygame.Rect) -> Point:
    return (c.centerx, c.bottom - 2)


FIRE = [(255, 220, 90), (255, 160, 40), (240, 90, 30), (255, 120, 20)]
WATER = [(90, 170, 255), (140, 210, 255), (60, 120, 230)]
LEAF = [(90, 190, 70), (120, 220, 90), (60, 150, 50)]
ICE = [(200, 240, 255), (150, 220, 250), (240, 255, 255)]
ELEC = [(255, 240, 90), (255, 255, 200), (250, 210, 40)]
PSY = [(250, 110, 200), (200, 120, 255), (255, 170, 230)]
POISON = [(170, 80, 210), (200, 120, 230), (120, 50, 160)]
ROCK = [(150, 125, 95), (120, 100, 80), (175, 150, 115), (105, 90, 75)]
DIRT = [(160, 120, 80), (130, 95, 60), (185, 150, 105)]
GHOST = [(120, 70, 170), (90, 50, 140), (160, 110, 210)]


# --- fire

class _Emitter(Particle):
    __slots__ = ()

    def draw(self, s):
        pass


def _emitter(fx: Fx, time: float, fn, delay: float = 0.0, rate: float = 30.0):
    """Calls `fn(fx, u)` `rate` times a second for `time` seconds."""
    acc = [0.0]

    def emit(fx, p, dt):
        acc[0] += rate * dt
        while acc[0] >= 1:
            acc[0] -= 1
            fn(fx, p.u)
    fx.items.append(_Emitter(0, 0, life=time, emit=emit, delay=delay))


def flames(fx: Fx, c: pygame.Rect, time: float, rate: float, size=(3, 6), delay=0.0, spread=0.4, colors=None):
    colors = colors or FIRE

    def one(fx, u):
        x = c.centerx + R(-c.w * spread, c.w * spread)
        y = c.bottom - R(2, c.h * 0.6)
        col = random.choice(colors)
        sz = R(*size)
        fx.part(x, y, vx=R(-8, 8), vy=-R(30, 70), life=R(0.3, 0.6), size=sz, size1=0.5, color=col,
                color1=scale(col, 0.25), kind="glow")
    _emitter(fx, time, one, delay, rate)


def ember_launch(fx, c):
    t = c.flight(520)
    for i in range(3):
        _projectile(fx, (c.mouth[0], c.mouth[1] + R(-3, 3)), _jitter(c.target, 0.2), t, size=3, height=12 + i * 6,
                    delay=i * 0.06, trail=_trail(colors=FIRE, rate=50, size=(1.5, 3)))
    return t + 0.12


def ember_land(fx, c):
    for tg in c.targets:
        if c.landed:
            _spray(fx, tg.center, 12, FIRE, kind="glow", speed=(30, 90), size=(2, 4), life=(0.2, 0.5))
            flames(fx, tg, 1.2, 24, size=(2.5, 4.5), spread=0.3)
    return 0.3


def fire_punch_land(fx, c):
    for tg in c.targets:
        _impact(fx, tg.center, (255, 140, 40), c.p)
        _ring(fx, tg.center, (255, 140, 40), 6, 34, 0.35)
        _spray(fx, tg.center, 20, FIRE, kind="glow", speed=(50, 140), size=(2, 4), life=(0.25, 0.5), gravity=-80)
        if c.landed:
            flames(fx, tg, 0.7, 20)
    return 0.3


def flamethrower_launch(fx, c):
    t = 0.55
    a, b = c.mouth, c.tc

    def puff(fx, u):
        col = random.choice(FIRE)
        sz = R(2, 4)
        tt = R(0.18, 0.26)
        bb = (b[0] + R(-8, 8), b[1] + R(-8, 8))
        fx.part(*a, life=tt, size=sz, size1=sz * 2.5, color=col, color1=(150, 30, 0), kind="glow",
                path=_wavy(a, bb, R(3, 8), R(0, 6)))
    _emitter(fx, t, puff, rate=90)
    return 0.28


def _wavy(a, b, amp, phase):
    def path(p, u):
        x, y = lerp(a[0], b[0], u), lerp(a[1], b[1], u)
        return (x, y + math.sin(u * 9 + phase) * amp * u)
    return path


def flamethrower_land(fx, c):
    for tg in c.targets:
        flames(fx, tg, 0.9, 50, size=(3, 7), spread=0.45)
        _spray(fx, tg.center, 16, FIRE, kind="spark", speed=(80, 160))
    fx.shake(2, 0.3)
    return 0.6


def fire_spin_land(fx, c):
    for tg in c.targets:
        cx, cy = tg.centerx, tg.bottom - 4
        r = max(tg.w, 24) * 0.7

        def one(fx, u, cx=cx, cy=cy, r=r):
            a0 = R(0, 6.28)
            col = random.choice(FIRE)

            def path(p, uu, a0=a0):
                a = a0 + uu * 9
                return (cx + math.cos(a) * r * (1 - uu * 0.3), cy - uu * 50 + math.sin(a) * r * 0.3)
            fx.part(cx, cy, life=R(0.45, 0.7), size=R(3, 5), size1=1, color=col, color1=(140, 20, 0),
                    kind="glow", path=path)
        _emitter(fx, 1.2, one, rate=70)
    return 0.9


def fire_blast_launch(fx, c):
    t = c.flight(380, 0.35, 0.6)
    _projectile(fx, c.mouth, c.tc, t, size=7, size1=9, color=(255, 140, 40),
                trail=_trail(colors=FIRE, rate=140, size=(3, 6), life=(0.2, 0.4), spread=20))
    fx.darken((40, 10, 0), 0.35, t + 1.2)
    return t


def fire_blast_land(fx, c):
    for tg in c.targets:
        x, y = tg.center
        # The 大: five arms of fire.
        for arm in range(5):
            ang = -math.pi / 2 + arm * 2 * math.pi / 5 + (0.0 if arm == 0 else 0.25 * (1 if arm in (1, 4) else -1))
            for k in range(14):
                d = 6 + k * 4.5
                fx.part(x, y, life=1.0 - k * 0.025, size=7 - k * 0.25, size1=2, color=random.choice(FIRE),
                        color1=(200, 50, 0), kind="glow", delay=k * 0.02,
                        path=_line((x, y), (x + math.cos(ang) * d, y + math.sin(ang) * d), ease_out))
        _ring(fx, (x, y), (255, 160, 60), 8, 70, 0.5)
        _spray(fx, (x, y), 40, FIRE, kind="glow", speed=(60, 200), size=(2, 5), life=(0.3, 0.8), gravity=-40)
        if c.landed:
            flames(fx, tg, 1.2, 40, size=(3, 7))
    fx.flash(0.3, (255, 160, 80), 0.35)
    fx.shake(5, 0.6)
    return 0.9


# --- water

def bubble_launch(fx, c):
    t = c.flight(220, 0.4, 0.8)
    n = 5 + round(4 * c.p)
    for i in range(n):
        a = (c.mouth[0], c.mouth[1] + R(-4, 4))
        b = _jitter(c.target, 0.35)
        ph, amp = R(0, 6), R(4, 10)
        fx.part(*a, life=t, size=R(2, 4), kind="bubble", color=(150, 210, 255), delay=i * t * 0.6 / n,
                path=_wavy(a, b, amp, ph))
    return t


def _pop(fx, c, n=12):
    for tg in c.targets:
        for _ in range(n):
            pos = _jitter(tg, 0.35)
            fx.part(*pos, life=0.2, size=2, size1=6, color=(170, 220, 255), kind="ring", delay=R(0, 0.15))
        _spray(fx, tg.center, n, WATER, kind="drop", speed=(40, 110), size=(1, 2), gravity=300, life=(0.3, 0.5),
               drag=0.5)


def bubble_land(fx, c):
    _pop(fx, c, 6 + round(10 * c.p))
    return 0.2


def water_gun_launch(fx, c):
    t = c.flight(480, 0.25, 0.45)
    a, b = c.mouth, c.tc

    def drop(fx, u):
        bb = (b[0] + R(-5, 5), b[1] + R(-5, 5))
        fx.part(*a, life=t * 0.8, size=R(1.5, 3), color=random.choice(WATER), kind="drop", path=_arc(a, bb, 14))
    _emitter(fx, t * 0.9, drop, rate=70)
    return t


def splash_land(fx, c, big=1.0):
    for tg in c.targets:
        _spray(fx, (tg.centerx, tg.centery), 18 * big, WATER, kind="drop", speed=(60, 160 * big), size=(1, 3),
               gravity=380, drag=0.3, life=(0.4, 0.7), angle=(-math.pi * 0.95, -math.pi * 0.05))
        _ring(fx, (tg.centerx, tg.bottom - 2), (120, 190, 255), 4, 20 + 20 * big, 0.4, squash=0.35)
    if big > 1.2:
        fx.shake(3, 0.35)
    return 0.3


def bubble_beam_launch(fx, c):
    t = c.flight(330, 0.35, 0.6)
    for i in range(16):
        a = (c.mouth[0], c.mouth[1] + R(-3, 3))
        b = _jitter(c.target, 0.3)
        fx.part(*a, life=t * R(0.8, 1.0), size=R(2, 5), kind="bubble", color=(170, 220, 255), delay=i * t * 0.03,
                path=_wavy(a, b, R(2, 6), R(0, 6)))
    fx.put(Beam(c.mouth, c.tc, t + 0.2, 3, (60, 130, 230), reach=t * 0.8))
    return t


def bubble_beam_land(fx, c):
    _pop(fx, c, 18)
    fx.shake(1.5, 0.2)
    return 0.3


def hydro_pump_launch(fx, c):
    t = c.flight(600, 0.2, 0.35)
    fx.put(Beam(c.mouth, c.tc, t + 0.7, 7, (60, 130, 240), reach=t, core=(220, 240, 255)))

    def spray(fx, u):
        e = (lerp(c.mouth[0], c.tc[0], min(1, u * 2)), lerp(c.mouth[1], c.tc[1], min(1, u * 2)))
        fx.part(*e, vx=R(-60, 60) - 60 * c.dir, vy=R(-120, -20), ay=380, life=R(0.3, 0.5), size=R(1, 3),
                color=random.choice(WATER), kind="drop")
    _emitter(fx, t + 0.6, spray, rate=70)
    return t


def hydro_pump_land(fx, c):
    splash_land(fx, c, 1.8)
    fx.shake(4, 0.6)
    return 0.6


def surf_launch(fx, c):
    """A wave across the whole field, from the user's side."""
    t = 0.7
    W = 640
    start = -80 if c.dir > 0 else W + 80
    end = W + 120 if c.dir > 0 else -120
    ground = max(tg.bottom for tg in c.targets) + 6

    def draw(s, u):
        x = lerp(start, end, u)
        h = 70
        pts = []
        for i in range(0, 13):
            px = x - c.dir * i * 14
            crest = math.sin(i * 0.5 + u * 10) * 5
            pts.append((px, ground - h * (1 - i / 14) ** 0.6 + crest))
        back = x - c.dir * 13 * 14
        poly = [(x + c.dir * 18, ground)] + [(x + c.dir * 18, ground - 30)] + pts + [(back - c.dir * 400, ground - 8),
                                                                                    (back - c.dir * 400, ground)]
        layer = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(layer, (60, 140, 230, 170), poly)
        pygame.draw.lines(layer, (220, 240, 255, 230), False, [(x + c.dir * 18, ground - 30)] + pts[:8], 3)
        s.blit(layer, (0, 0))

    fx.put(Custom(t + 0.25, draw))

    def foam(fx, u):
        x = lerp(start, end, u * (t + 0.25) / t)
        fx.part(x + R(-10, 10), ground - R(10, 60), vx=c.dir * R(80, 200), vy=-R(40, 140), ay=350, life=R(0.3, 0.6),
                size=R(1, 3), color=random.choice(WATER + [(230, 245, 255)]), kind="drop")
    _emitter(fx, t, foam, rate=80)
    fx.shake(2, t)
    return t * 0.75


def surf_land(fx, c):
    splash_land(fx, c, 1.3)
    return 0.4


def withdraw(fx, c):
    _ring(fx, c.user.center, (150, 200, 255), 36, 8, 0.35)
    _glint(fx, c.user)
    return 0.3


def _glint(fx, rect, color=WHITE, delay=0.15):
    fx.part(rect.right - rect.w * 0.3, rect.top + rect.h * 0.3, life=0.35, size=2, size1=9, color=color,
            kind="star", delay=delay, spin=3)


# --- grass

def drain_land(fx, c, colors=None, n=10):
    """Absorb, Mega Drain, Leech Life: orbs of life drift from the target to the user."""
    colors = colors or [(120, 230, 100), (190, 255, 150)]
    if not c.landed:
        return 0.0
    for tg in c.targets:
        for i in range(n):
            a = _jitter(tg, 0.3)
            b = _jitter(c.user, 0.25)
            mid = ((a[0] + b[0]) / 2 + R(-20, 20), min(a[1], b[1]) - R(20, 50))
            fx.part(*a, life=R(0.5, 0.7), size=R(2, 4), size1=2, color=random.choice(colors), kind="core",
                    delay=i * 0.04, path=_bezier(a, mid, b))
    return 0.7


def _bezier(a, m, b):
    def path(p, u):
        v = 1 - u
        return (v * v * a[0] + 2 * v * u * m[0] + u * u * b[0], v * v * a[1] + 2 * v * u * m[1] + u * u * b[1])
    return path


def vine_whip_launch(fx, c):
    t = 0.2
    for k, off in enumerate((-6, 6)):
        fx.put(Beam((c.mouth[0], c.mouth[1] + off), (c.tc[0], c.tc[1] + off * 1.5), 0.5, 2, (70, 160, 60),
                    kind="vine", reach=t, delay=k * 0.07))
    return t + 0.05


def vine_whip_land(fx, c):
    for tg in c.targets:
        for k in range(2):
            fx.part(*tg.center, life=0.25, size=34, color=(150, 255, 120), kind="slash",
                    rot=-0.6 + k * 1.2 + R(-0.2, 0.2), delay=k * 0.08)
        _impact(fx, tg.center, (150, 230, 110), c.p * 0.6)
    return 0.2


def razor_leaf_launch(fx, c):
    t = c.flight(520, 0.25, 0.5)
    for i in range(6):
        b = _jitter(c.target, 0.3)
        a = (c.mouth[0], c.mouth[1] + R(-10, 10))
        fx.part(*a, life=t, size=R(3, 5), color=random.choice(LEAF), kind="leaf", spin=R(18, 30) * c.dir,
                delay=i * 0.04, path=_arc(a, b, R(-25, 25)))
    return t + 0.15


def razor_leaf_land(fx, c):
    for tg in c.targets:
        for k in range(3):
            fx.part(*_jitter(tg, 0.2), life=0.22, size=26, color=(180, 255, 140), kind="slash", rot=R(-1, 1),
                    delay=k * 0.05)
        _spray(fx, tg.center, 8, LEAF, kind="leaf", speed=(40, 100), size=(2, 3), gravity=120, spin=12,
               life=(0.4, 0.7))
    return 0.3


def petal_dance_launch(fx, c):
    t = 0.75
    pink = [(250, 150, 200), (255, 190, 220), (230, 110, 170)]
    for i in range(28):
        a0 = R(0, 6.28)
        cx, cy = c.user.center
        b = _jitter(c.target, 0.35)

        def path(p, u, a0=a0, b=b, cx=cx, cy=cy):
            if u < 0.55:  # a whirl around the user...
                k = u / 0.55
                a = a0 + k * 8
                return (cx + math.cos(a) * (20 + 10 * k), cy + math.sin(a) * 12 - k * 10)
            k = (u - 0.55) / 0.45  # ... then a rush at the target
            a = a0 + 8
            sx, sy = cx + math.cos(a) * 30, cy + math.sin(a) * 12 - 10
            return (lerp(sx, b[0], k), lerp(sy, b[1], k))
        fx.part(cx, cy, life=t, size=R(3, 4), color=random.choice(pink), kind="petal", spin=R(-12, 12),
                delay=i * 0.008, path=path)
    return t


def petal_dance_land(fx, c):
    pink = [(250, 150, 200), (255, 190, 220), (230, 110, 170)]
    for tg in c.targets:
        _spray(fx, tg.center, 26, pink, kind="petal", speed=(60, 160), size=(2, 4), gravity=90, spin=14,
               life=(0.5, 0.9), drag=2)
        _impact(fx, tg.center, (255, 160, 210), c.p)
    return 0.5


def _gather(fx, center: Point, colors, time: float, rate=60, radius=60, size=(1.5, 3), kind="glow"):
    """Particles drawn in from all round to `center` (charging up)."""
    def one(fx, u):
        a = R(0, 6.28)
        r = R(radius * 0.6, radius)
        start = (center[0] + math.cos(a) * r, center[1] + math.sin(a) * r)
        col = random.choice(colors)
        fx.part(*start, life=R(0.3, 0.45), size=R(*size), size1=size[1] * 1.3, color=scale(col, 0.4), color1=col,
                kind=kind, path=_line(start, center, lambda x: x * x))
    _emitter(fx, time, one, rate=rate)


def solar_charge(fx, c):
    sun = [(255, 250, 180), (255, 230, 120), (255, 255, 230)]
    _gather(fx, c.user.center, sun, 0.9, rate=70, radius=70)
    fx.part(*c.user.center, life=1.0, size=4, size1=18, color=(120, 110, 40), color1=(255, 240, 140), kind="glow")
    fx.darken((255, 240, 160), 0.18, 1.1)
    # rays of sun coming down
    for i in range(5):
        x = c.user.centerx + R(-50, 50)
        fx.put(Beam((x + 40, -10), (x, c.user.bottom), 0.8, 3, (90, 80, 30), reach=0.25, delay=i * 0.1))
    return 0.6


def solar_launch(fx, c):
    t = 0.18
    fx.part(*c.mouth, life=0.25, size=6, size1=26, color=(255, 250, 200), kind="glow")
    fx.put(Beam(c.mouth, c.tc, 1.0, 11, (255, 230, 110), reach=t, core=(255, 255, 240)))
    fx.darken((255, 245, 200), 0.3, 1.2)
    fx.flash(0.25, (255, 240, 180), 0.35)
    return t


def solar_land(fx, c):
    for tg in c.targets:
        _ring(fx, tg.center, (255, 240, 140), 10, 70, 0.6)
        _spray(fx, tg.center, 40, [(255, 250, 200), (255, 230, 110)], kind="spark", speed=(120, 300),
               life=(0.3, 0.6), size=(1, 2))
        fx.part(*tg.center, life=0.6, size=30, size1=10, color=(200, 180, 80), kind="glow")
    fx.shake(5, 0.7)
    return 0.8


def leaf_shield(fx, c):
    for tg in c.targets:
        cx, cy = tg.center
        for i in range(12):
            a0 = i / 12 * 6.28

            def path(p, u, a0=a0, cx=cx, cy=cy, w=tg.w, h=tg.h):
                a = a0 + u * 7
                r = lerp(w * 0.9, w * 0.55, u)
                return (cx + math.cos(a) * r, cy + math.sin(a) * h * 0.55)
            fx.part(cx, cy, life=0.7, size=3.5, color=random.choice(LEAF), kind="leaf", spin=10, path=path)
        _ring(fx, (cx, cy), (150, 240, 140), 10, max(tg.w, tg.h) * 0.7, 0.5)
    return 0.5


def leech_seed_launch(fx, c):
    t = c.flight(300, 0.35, 0.6)
    for i in range(3):
        _projectile(fx, c.mouth, _jitter(c.target, 0.25), t, kind="egg", size=2, height=40 + 10 * i, delay=i * 0.05)
    return t + 0.1


def leech_seed_land(fx, c):
    if not c.landed:
        return 0.1
    for tg in c.targets:
        for k in range(3):
            a = (tg.centerx + (k - 1) * tg.w * 0.25, tg.bottom - 4)
            b = (a[0] + R(-10, 10), tg.centery - R(0, tg.h * 0.3))
            fx.put(Beam(a, b, 0.8, 2, (80, 170, 60), kind="vine", reach=0.35, delay=k * 0.1))
        _spray(fx, tg.center, 10, LEAF, kind="leaf", speed=(20, 60), size=(2, 3), gravity=50, spin=8,
               life=(0.5, 0.8))
    return 0.6


def powder(colors, sleep=False):
    def launch(fx, c):
        t = c.flight(260, 0.35, 0.55)
        for i in range(10):
            _projectile(fx, c.mouth, (c.tc[0] + R(-10, 10), c.target.top - 10), t, kind="soft", size=R(3, 5),
                        color=random.choice(colors), height=30, delay=i * 0.02, data=0.6)
        return t

    def land(fx, c):
        for tg in c.targets:
            def one(fx, u, tg=tg):
                fx.part(tg.centerx + R(-tg.w * 0.5, tg.w * 0.5), tg.top - R(0, 14), vx=R(-10, 10), vy=R(25, 50),
                        life=R(0.5, 0.9), size=R(1, 2.2), color=random.choice(colors), kind="glow",
                        color1=scale(random.choice(colors), 0.2))
            _emitter(fx, 0.8, one, rate=60)
            fx.part(tg.centerx, tg.top, vy=12, life=0.9, size=10, size1=22, color=colors[0], kind="soft", data=0.35)
            if sleep and c.landed:
                for k in range(3):
                    fx.part(tg.right - 4, tg.top, vx=14, vy=-24, life=0.9, size=3 + k, color=WHITE, kind="zzz",
                            delay=0.3 + k * 0.25)
        return 0.7
    return Recipe(launch, land)


# --- electric

def thunder_shock_launch(fx, c):
    t = 0.16
    fx.put(Beam(c.mouth, c.tc, 0.35, 1, (255, 240, 80), kind="bolt", reach=0.0, jag=8))
    return t


def thunder_shock_land(fx, c):
    for tg in c.targets:
        _spray(fx, tg.center, 14, ELEC, kind="spark", speed=(80, 200), life=(0.15, 0.35))
        fx.part(*tg.center, life=0.3, size=18, size1=8, color=(140, 130, 40), kind="glow")
    return 0.25


def thunderbolt_launch(fx, c):
    fx.put(Beam(c.mouth, c.tc, 0.6, 2.5, (255, 240, 90), kind="bolt", reach=0.0, jag=14, branches=3))
    fx.put(Beam((c.mouth[0], c.mouth[1] - 6), c.tc, 0.45, 1, (255, 255, 160), kind="bolt", jag=10, delay=0.08))
    fx.flash(0.12, (255, 250, 200), 0.2)
    return 0.2


def thunderbolt_land(fx, c):
    for tg in c.targets:
        _spray(fx, tg.center, 30, ELEC, kind="spark", speed=(100, 260), life=(0.2, 0.45))
        fx.part(*tg.center, life=0.5, size=30, size1=10, color=(170, 160, 50), kind="glow")
        _ring(fx, tg.center, (255, 240, 120), 6, 46, 0.35)
        if c.landed:
            _crackle(fx, tg, 0.7)
    fx.shake(3, 0.4)
    return 0.5


def _crackle(fx, tg, time):
    def one(fx, u, tg=tg):
        a = _jitter(tg, 0.4)
        b = (a[0] + R(-12, 12), a[1] + R(-12, 12))
        fx.put(Beam(a, b, 0.08, 1, (255, 240, 120), kind="bolt", jag=4))
    _emitter(fx, time, one, rate=14)


def thunder_launch(fx, c):
    fx.darken((10, 10, 40), 0.55, 1.6)
    return 0.45


def thunder_land(fx, c):
    for k, tg in enumerate(c.targets):
        top = (tg.centerx + R(-30, 30), -20)
        fx.put(Beam(top, (tg.centerx, tg.bottom - 6), 0.6, 4, (255, 250, 150), kind="bolt", jag=18, branches=4,
                    delay=k * 0.05))
        fx.put(Beam((top[0] + 20, -20), tg.center, 0.4, 2, (230, 230, 255), kind="bolt", jag=14, branches=2,
                    delay=0.1 + k * 0.05))
        _spray(fx, (tg.centerx, tg.bottom - 4), 40, ELEC, kind="spark", speed=(120, 320), life=(0.25, 0.55),
               angle=(-math.pi, 0))
        _ring(fx, (tg.centerx, tg.bottom - 2), (255, 240, 120), 8, 70, 0.5, squash=0.35)
        if c.landed:
            _crackle(fx, tg, 0.9)
    fx.flash(0.35, WHITE, 0.55)
    fx.shake(6, 0.7)
    return 0.9


def thunder_punch_land(fx, c):
    for tg in c.targets:
        _impact(fx, tg.center, (255, 230, 80), c.p)
        for _ in range(5):
            a = tg.center
            ang = R(0, 6.28)
            b = (a[0] + math.cos(ang) * 30, a[1] + math.sin(ang) * 30)
            fx.put(Beam(a, b, 0.25, 1, (255, 240, 100), kind="bolt", jag=6))
        _crackle(fx, tg, 0.4)
    return 0.3


def thunder_wave_launch(fx, c):
    t = c.flight(300, 0.3, 0.5)
    for k in range(3):
        fx.part(*c.mouth, life=t, size=5, size1=14, color=(255, 240, 90), kind="ring", data=1.6, delay=k * 0.08,
                path=_line(c.mouth, c.tc))
    return t + 0.16


def thunder_wave_land(fx, c):
    for tg in c.targets:
        _crackle(fx, tg, 0.6)
        _spray(fx, tg.center, 12, ELEC, kind="spark", speed=(40, 120))
    return 0.4


# --- ice

def ice_beam_launch(fx, c):
    t = 0.2
    fx.put(Beam(c.mouth, c.tc, 0.8, 5, (130, 210, 255), reach=t, core=(240, 255, 255)))

    def flake(fx, u):
        k = R(0, min(1, u * 4))
        x, y = lerp(c.mouth[0], c.tc[0], k), lerp(c.mouth[1], c.tc[1], k)
        fx.part(x, y + R(-5, 5), vx=R(-20, 20), vy=R(-30, 10), life=R(0.3, 0.6), size=R(1.5, 3), color=WHITE,
                kind="star", spin=6)
    _emitter(fx, 0.7, flake, rate=50)
    return t


def ice_land(fx, c, big=1.0):
    for tg in c.targets:
        for _ in range(int(8 * big)):
            a = R(0, 6.28)
            d = R(6, 18) * big
            fx.part(tg.centerx + math.cos(a) * d, tg.centery + math.sin(a) * d * 0.8, life=R(0.6, 0.9),
                    size=R(2, 4) * big, size1=1, color=random.choice(ICE), kind="shard", rot=a + math.pi / 2)
        _spray(fx, tg.center, 16 * big, ICE, kind="spark", speed=(60, 180), life=(0.2, 0.5))
        fx.part(*tg.center, life=0.5, size=26 * big, size1=10, color=(80, 130, 160), kind="glow")
    fx.shake(2 * big, 0.3)
    return 0.5


def aurora_launch(fx, c):
    t = 0.2
    fx.put(Beam(c.mouth, c.tc, 0.8, 5, (200, 200, 255), kind="rainbow", reach=t))

    def glit(fx, u):
        k = R(0, 1)
        x, y = lerp(c.mouth[0], c.tc[0], k), lerp(c.mouth[1], c.tc[1], k)
        fx.part(x, y + R(-8, 8), vy=-R(10, 30), life=0.5, size=2, size1=0.5, color=_hue(R(0, 1)), kind="glow")
    _emitter(fx, 0.7, glit, rate=40)
    return t


def blizzard_launch(fx, c):
    fx.darken((200, 230, 255), 0.3, 1.8)

    def flake(fx, u):
        x = R(-40, 680)
        fx.part(x, R(-20, 250), vx=c.dir * R(260, 420), vy=R(30, 90), life=R(0.6, 1.0),
                size=R(1, 2.5), color=random.choice(ICE), kind="glow" if random.random() < 0.5 else "dot")
        if random.random() < 0.3:
            fx.part(R(0, 640), R(0, 250), vx=c.dir * R(400, 600), vy=R(20, 50), life=0.5, size=1, color=(200, 230, 255),
                    kind="line", data=24)
    _emitter(fx, 1.4, flake, rate=160)
    fx.shake(2, 1.2)
    return 0.5


def blizzard_land(fx, c):
    ice_land(fx, c, 1.5)
    return 0.9


def ice_punch_land(fx, c):
    for tg in c.targets:
        _impact(fx, tg.center, (160, 220, 255), c.p)
    return ice_land(fx, c, 0.9)


# --- rock and ground

def _rock_shape():
    return tuple(R(0.7, 1.05) for _ in range(random.randint(5, 7)))


def rock_throw_launch(fx, c):
    t = c.flight(320, 0.35, 0.55)
    for i in range(3):
        b = _jitter(c.target, 0.25)
        a = (c.mouth[0], c.user.top)
        fx.part(*a, life=t, size=R(5, 7), color=random.choice(ROCK), kind="rock", spin=R(-8, 8), delay=i * 0.07,
                path=_arc(a, b, R(40, 60)), data=_rock_shape())
    return t + 0.14


def crumble(fx, tg, n=10, big=1.0):
    _spray(fx, tg.center, n, ROCK, kind="rock", speed=(50, 140 * big), size=(1.5, 3 * big), gravity=420, drag=0.5,
           spin=10, life=(0.4, 0.7), angle=(-math.pi, 0))
    for _ in range(int(4 * big)):
        fx.part(tg.centerx + R(-14, 14), tg.bottom - R(2, 10), vx=R(-20, 20), vy=-R(5, 20), life=R(0.5, 0.9),
                size=R(5, 9) * big, size1=R(10, 16) * big, color=(170, 150, 120), kind="soft", data=0.5)


def rock_throw_land(fx, c):
    for tg in c.targets:
        _impact(fx, tg.center, (220, 200, 160), c.p * 0.7)
        crumble(fx, tg, 12)
    return 0.4


def rock_slide_launch(fx, c):
    t = 0.55
    for tg in c.targets:
        for i in range(7):
            x = tg.centerx + R(-tg.w * 0.7, tg.w * 0.7)
            a = (x + R(-30, 30) - c.dir * 40, -30 - R(0, 40))
            b = (x, tg.centery + R(-tg.h * 0.3, tg.h * 0.3))
            fx.part(*a, life=t * R(0.7, 1.0), size=R(5, 9), color=random.choice(ROCK), kind="rock", spin=R(-6, 6),
                    delay=i * 0.05, path=_line(a, b, lambda u: u * u), data=_rock_shape())
    return t


def rock_slide_land(fx, c):
    for tg in c.targets:
        crumble(fx, tg, 20, 1.5)
        _impact(fx, tg.center, (230, 210, 170), c.p)
    fx.shake(5, 0.5)
    return 0.6


def earthquake_launch(fx, c):
    fx.shake(7, 1.3)
    for tg in c.targets:
        def one(fx, u, tg=tg):
            fx.part(tg.centerx + R(-tg.w, tg.w), tg.bottom - R(0, 4), vx=R(-30, 30), vy=-R(40, 160), ay=400,
                    life=R(0.4, 0.8), size=R(1.5, 3.5), color=random.choice(ROCK + DIRT), kind="rock", spin=10,
                    data=_rock_shape())
        _emitter(fx, 1.0, one, rate=40)
    # cracks running along the ground
    ground = max(t.bottom for t in c.targets)

    def cracks(s, u):
        k = min(1.0, u * 2.5)
        fade = 1 - max(0.0, (u - 0.6) / 0.4)
        col = scale((40, 30, 20), 1)
        rnd = random.Random(7)
        for tg in c.targets:
            x0 = tg.centerx
            for side in (-1, 1):
                pts = [(x0, ground)]
                x, y = x0, ground
                for _ in range(int(6 * k) + 1):
                    x += side * rnd.uniform(6, 12)
                    y += rnd.uniform(-2, 2)
                    pts.append((x, y))
                if fade > 0.05:
                    pygame.draw.lines(s, col, False, pts, 2)
    fx.put(Custom(1.3, cracks, back=True))
    return 0.35


def earthquake_land(fx, c):
    for tg in c.targets:
        crumble(fx, tg, 10, 1.2)
    return 0.9


def dig_charge(fx, c):
    _spray(fx, _foot(c.user), 26, DIRT + ROCK, kind="rock", speed=(80, 200), size=(1.5, 3), gravity=500, drag=0.3,
           spin=10, angle=(-math.pi * 0.9, -math.pi * 0.1), life=(0.4, 0.8))
    for _ in range(5):
        fx.part(c.user.centerx + R(-16, 16), c.user.bottom - 4, vy=-R(10, 30), life=R(0.6, 1.0), size=R(6, 10),
                size1=R(14, 20), color=(160, 130, 90), kind="soft", data=0.5)
    return 0.3


def dig_land(fx, c):
    for tg in c.targets:
        _spray(fx, _foot(tg), 30, DIRT + ROCK, kind="rock", speed=(100, 260), size=(1.5, 3.5), gravity=500, drag=0.3,
               spin=12, angle=(-math.pi * 0.85, -math.pi * 0.15), life=(0.4, 0.8))
        _impact(fx, tg.center, (230, 200, 150), c.p)
    fx.shake(4, 0.4)
    return 0.5


def bone_launch(fx, c, back=False):
    t = c.flight(360, 0.3, 0.55)
    a, b = c.mouth, c.tc
    if back:
        def path(p, u):
            k = math.sin(u * math.pi)  # out and back
            return (lerp(a[0], b[0], k), lerp(a[1], b[1], k) - 20 * math.sin(u * 2 * math.pi))
        fx.part(*a, life=t * 2, size=7, kind="bone", spin=20 * c.dir, path=path)
        return t
    fx.part(*a, life=t, size=7, kind="bone", spin=20 * c.dir, path=_arc(a, b, 20))
    return t


# --- psychic and ghost

def psy_rings(fx, tg, n=4, color=(250, 120, 210), time=0.6, big=1.0):
    for k in range(n):
        _ring(fx, tg.center, color, 4, max(tg.w, tg.h) * 0.7 * big, time, delay=k * time / n, squash=0.6)


def confusion_launch(fx, c):
    fx.darken((120, 40, 120), 0.2, 0.9)
    return 0.15


def confusion_land(fx, c):
    for tg in c.targets:
        psy_rings(fx, tg, 5)
        _wobble_glow(fx, tg, (130, 60, 120), 0.6)
    return 0.5


def _wobble_glow(fx, tg, color, time):
    def draw(s, u, tg=tg):
        r = round(max(tg.w, tg.h) * (0.5 + 0.1 * math.sin(u * 30)))
        add(s, glow_surface(r, scale(color, 1 - u)), tg.center)
    fx.put(Custom(time, draw))


def psybeam_launch(fx, c):
    t = c.flight(420, 0.3, 0.5)
    for k in range(7):
        fx.part(*c.mouth, life=t, size=4, size1=12, color=PSY[k % 3], kind="ring", data=1.8, delay=k * 0.05,
                path=_line(c.mouth, c.tc))
    fx.put(Beam(c.mouth, c.tc, t + 0.35, 2, (230, 120, 220), kind="rainbow", reach=t))
    return t + 0.1


def psybeam_land(fx, c):
    for tg in c.targets:
        psy_rings(fx, tg, 4)
        _spray(fx, tg.center, 16, PSY, kind="star", speed=(40, 120), size=(1.5, 3), life=(0.3, 0.6), spin=8)
    return 0.4


def psychic_launch(fx, c):
    fx.darken((70, 10, 90), 0.4, 1.5)

    def wave(s, u):  # the air rippling
        for k in range(3):
            r = ((u * 2 + k / 3) % 1.0) * 380
            add_ring(s, scale((200, 90, 230), (1 - r / 380) * 0.6), c.user.center, r, 2, 0.5)
    fx.put(Custom(1.0, wave, back=True))
    return 0.35


def psychic_land(fx, c):
    for tg in c.targets:
        psy_rings(fx, tg, 7, big=1.4, time=0.8)
        _wobble_glow(fx, tg, (180, 70, 190), 0.8)
        _spray(fx, tg.center, 24, PSY, kind="spark", speed=(80, 200), life=(0.3, 0.6))
    fx.shake(4, 0.6)
    fx.flash(0.2, (220, 120, 255), 0.2)
    return 0.8


def hypnosis_launch(fx, c):
    t = c.flight(220, 0.45, 0.7)
    for k in range(5):
        fx.part(*c.mouth, life=t, size=4 + k * 2, size1=3, color=(200, 130, 255), kind="ring", data=0.8,
                delay=k * 0.07, path=_line(c.mouth, c.tc))
    return t + 0.2


def hypnosis_land(fx, c):
    for tg in c.targets:
        def spiral(s, u, tg=tg):
            pts = [(tg.centerx + math.cos(a / 4 + u * 12) * a * 0.9, tg.centery + math.sin(a / 4 + u * 12) * a * 0.6)
                   for a in range(0, 30)]
            add_lines(s, scale((200, 140, 255), 1 - u), pts, 1)
        fx.put(Custom(0.8, spiral))
        if c.landed:
            for k in range(3):
                fx.part(tg.right - 4, tg.top, vx=14, vy=-24, life=0.9, size=3 + k, color=WHITE, kind="zzz",
                        delay=0.3 + k * 0.25)
    return 0.6


def night_shade_launch(fx, c):
    fx.darken((10, 0, 20), 0.6, 1.5)
    return 0.4


def night_shade_land(fx, c):
    for tg in c.targets:
        def wisp(fx, u, tg=tg):
            fx.part(tg.centerx + R(-tg.w * 0.6, tg.w * 0.6), tg.bottom - R(0, tg.h), vx=R(-10, 10), vy=-R(20, 50),
                    life=R(0.4, 0.7), size=R(5, 9), size1=2, color=(70, 90, 50), kind="dark")
            fx.part(tg.centerx + R(-tg.w * 0.5, tg.w * 0.5), tg.bottom - R(0, tg.h), vy=-R(20, 40), life=0.5,
                    size=R(2, 3), size1=0.5, color=random.choice(GHOST), kind="glow")
        _emitter(fx, 0.9, wisp, rate=40)
        for side in (-1, 1):  # red eyes
            fx.part(tg.centerx + side * 8, tg.top - 12, life=0.9, size=3, size1=1, color=(255, 40, 40), kind="glow",
                    delay=0.2)
    return 0.8


def lick_land(fx, c):
    for tg in c.targets:
        fx.part(*tg.center, life=0.35, size=26, color=(230, 120, 200), kind="slash", rot=1.2)
        _spray(fx, tg.center, 8, [(240, 150, 220), (180, 120, 230)], kind="drop", speed=(30, 80), gravity=200,
               size=(1, 2))
        _wobble_glow(fx, tg, (90, 40, 110), 0.4)
    return 0.3


def confuse_ray_launch(fx, c):
    t = c.flight(160, 0.5, 0.8)
    a, b = c.mouth, c.target.center

    def path(p, u):
        return (lerp(a[0], b[0], u) + math.sin(u * 14) * 10, lerp(a[1], b[1], u) + math.cos(u * 11) * 12)
    fx.part(*a, life=t, size=6, color=(255, 230, 120), kind="core", path=path,
            emit=_trail(colors=[(255, 220, 100), (200, 120, 255)], rate=50, size=(1.5, 3)))
    return t


def confuse_ray_land(fx, c):
    for tg in c.targets:
        _orbit_stars(fx, tg)
    return 0.5


def _orbit_stars(fx, tg, n=3, time=0.9, color=(255, 240, 120)):
    for k in range(n):
        a0 = k / n * 6.28

        def path(p, u, a0=a0, tg=tg):
            a = a0 + u * 12
            return (tg.centerx + math.cos(a) * tg.w * 0.45, tg.top - 4 + math.sin(a) * 4)
        fx.part(tg.centerx, tg.top, life=time, size=3, color=color, kind="star5", spin=6, path=path)


# --- poison, bug

def sludge_launch(fx, c, colors=POISON, n=3, size=4):
    t = c.flight(330, 0.35, 0.55)
    for i in range(n):
        _projectile(fx, c.mouth, _jitter(c.target, 0.25), t, kind="dot", size=R(size - 1, size + 1),
                    color=random.choice(colors), height=R(20, 40), delay=i * 0.05,
                    trail=_trail(kind="dot", colors=colors, rate=25, size=(1, 2), life=(0.15, 0.3), spread=6))
    return t + 0.1


def sludge_land(fx, c, colors=POISON, n=16):
    for tg in c.targets:
        _spray(fx, tg.center, n, colors, kind="dot", speed=(50, 140), size=(1.5, 3), gravity=320, drag=0.5,
               life=(0.4, 0.7))
        if c.landed:
            def bub(fx, u, tg=tg):
                fx.part(*_jitter(tg, 0.35), vy=-R(10, 25), life=R(0.3, 0.5), size=R(1.5, 3), size1=4,
                        color=random.choice(colors), kind="bubble")
            _emitter(fx, 0.6, bub, rate=24)
    return 0.4


def gas_land(fx, c, colors=((150, 90, 170), (120, 110, 130), (170, 120, 190))):
    for tg in c.targets:
        for _ in range(14):
            fx.part(*_jitter(tg, 0.4), vx=R(-20, 20), vy=-R(5, 25), life=R(0.7, 1.1), size=R(6, 10), size1=R(14, 22),
                    color=random.choice(colors), kind="soft", data=0.55, delay=R(0, 0.25))
    return 0.7


def gas_launch(fx, c, colors=((150, 90, 170), (120, 110, 130), (170, 120, 190))):
    t = c.flight(260, 0.35, 0.55)
    for i in range(10):
        _projectile(fx, c.mouth, _jitter(c.target, 0.3), t, kind="soft", size=R(4, 7), size1=R(8, 12),
                    color=random.choice(colors), height=R(-10, 20), delay=i * 0.03, data=0.5)
    return t


def needle_launch(fx, c, n=1, color=(230, 230, 240)):
    t = c.flight(600, 0.18, 0.35)
    for i in range(n):
        a = (c.mouth[0], c.mouth[1] + R(-4, 4))
        fx.part(*a, life=t, size=5, color=color, kind="needle", delay=i * 0.07,
                path=_line(a, _jitter(c.target, 0.25)))
    return t + (n - 1) * 0.07


def string_shot_launch(fx, c):
    t = c.flight(400, 0.25, 0.45)
    for k in range(3):
        fx.put(Beam((c.mouth[0], c.mouth[1] + k - 1), _jitter(c.target, 0.3), 0.9, 1, (130, 130, 130),
                    reach=t, delay=k * 0.05, core=(200, 200, 200)))
    return t


def string_shot_land(fx, c):
    for tg in c.targets:
        def web(s, u, tg=tg):
            k = 1 - max(0.0, (u - 0.7) / 0.3)
            for i in range(5):
                y = tg.top + tg.h * (i + 0.5) / 5
                add_line(s, scale((170, 170, 170), k), (tg.left, y + math.sin(i) * 3), (tg.right, y - math.sin(i) * 3))
        fx.put(Custom(0.8, web))
    return 0.5


# --- normal, fighting, flying

def contact(color=(255, 230, 160), stars=1, slash=0, shake=1.0):
    """A plain hit: impact stars (several for multi-hit moves), claw slashes."""
    def land(fx, c):
        n = max(stars, min(5, c.hits))
        for tg in c.targets:
            for k in range(n):
                _impact(fx, _jitter(tg, 0.2) if n > 1 else tg.center, color, c.p * shake, delay=k * 0.12)
            for k in range(slash):
                fx.part(*_jitter(tg, 0.12), life=0.22, size=26 + 10 * c.p, color=(255, 255, 255), kind="slash",
                        rot=-0.9 + k * 0.25 + (0 if c.dir > 0 else 0), delay=k * 0.04)
        return 0.15 + 0.12 * (n - 1)
    return land


def bite_land(fx, c, color=(255, 255, 255)):
    for tg in c.targets:
        cx, cy = tg.center

        def jaws(s, u, cx=cx, cy=cy):
            gap = 22 * (1 - min(1.0, u * 3)) + 2
            k = 1 - max(0.0, (u - 0.5) * 2)
            for side in (-1, 1):
                y = cy + side * gap
                pts = [(cx - 18 + i * 6, y - side * (5 if i % 2 else 0)) for i in range(7)]
                add_lines(s, scale(color, k), pts, 2)
        fx.put(Custom(0.35, jaws))
        _impact(fx, tg.center, (255, 220, 200), c.p * 0.8, delay=0.1)
    return 0.25


def hyper_beam_launch(fx, c):
    fx.darken((40, 0, 30), 0.45, 1.6)
    t = 0.45
    _gather(fx, c.mouth, [(255, 220, 140), (255, 160, 80), WHITE], 0.4, rate=90, radius=50)
    fx.part(*c.mouth, life=0.45, size=3, size1=14, color=(255, 200, 120), kind="glow")
    fx.put(Beam(c.mouth, c.tc, 1.1, 13, (255, 150, 70), reach=0.12, delay=0.38, core=(255, 250, 230)))
    return t + 0.1


def hyper_beam_land(fx, c):
    for tg in c.targets:
        _ring(fx, tg.center, (255, 180, 100), 10, 90, 0.6)
        _ring(fx, tg.center, (255, 220, 160), 6, 60, 0.5, delay=0.1)
        _spray(fx, tg.center, 50, [(255, 230, 160), (255, 160, 80), WHITE], kind="spark", speed=(150, 380),
               life=(0.3, 0.7), size=(1, 2))
    fx.flash(0.4, (255, 200, 150), 0.45)
    fx.shake(8, 0.9)
    return 1.0


def explosion_launch(fx, c):
    big = 1.0 if c.p >= 1 else 0.75
    x, y = c.user.center
    fx.part(x, y, life=0.3, size=6, size1=60 * big, color=(255, 240, 200), kind="glow")
    for k in range(3):
        _ring(fx, (x, y), (255, 200, 120), 8, 140 * big, 0.6, delay=k * 0.08)
    _spray(fx, (x, y), 80 * big, FIRE + [WHITE], kind="glow", speed=(100, 380), size=(2, 6), life=(0.4, 0.9),
           drag=2.5)
    for _ in range(int(16 * big)):
        fx.part(x + R(-30, 30), y + R(-30, 20), vx=R(-40, 40), vy=-R(20, 60), life=R(0.9, 1.5), size=R(10, 16),
                size1=R(24, 34), color=random.choice([(90, 80, 75), (120, 110, 100), (70, 65, 60)]), kind="soft",
                data=0.7, delay=0.15)
    _spray(fx, (x, y), 20, ROCK, kind="rock", speed=(120, 300), size=(2, 4), gravity=400, drag=0.3, spin=12,
           life=(0.5, 0.9))
    fx.flash(0.5, WHITE, 0.6 * big)
    fx.shake(10 * big, 1.0)
    return 0.15


def explosion_land(fx, c):
    for tg in c.targets:
        _impact(fx, tg.center, (255, 200, 120), 1.0)
    return 1.0


def swift_launch(fx, c):
    t = c.flight(420, 0.3, 0.55)
    for i in range(6):
        a = (c.mouth[0], c.mouth[1] + R(-10, 10))
        b = _jitter(c.target, 0.3)
        fx.part(*a, life=t, size=4, color=(255, 230, 90), kind="star5", spin=14, delay=i * 0.05,
                path=_arc(a, b, R(-30, 30)), emit=_trail(colors=[(255, 240, 150)], rate=30, size=(1, 2), spread=4))
    return t + 0.25


def swift_land(fx, c):
    for tg in c.targets:
        _spray(fx, tg.center, 20, [(255, 240, 150), WHITE], kind="star", speed=(50, 140), size=(1.5, 3), spin=6,
               life=(0.3, 0.5))
    return 0.3


def egg_bomb_launch(fx, c):
    t = c.flight(300, 0.4, 0.6)
    _projectile(fx, (c.mouth[0], c.user.top), c.tc, t, kind="egg", size=5, height=60, spin=8)
    return t


def egg_bomb_land(fx, c):
    for tg in c.targets:
        x, y = tg.center
        fx.part(x, y, life=0.3, size=6, size1=34, color=(255, 220, 160), kind="glow")
        _spray(fx, (x, y), 40, FIRE, kind="glow", speed=(60, 220), size=(2, 5), life=(0.3, 0.7))
        _spray(fx, (x, y), 10, [(250, 245, 225)], kind="rock", speed=(80, 180), size=(1.5, 2.5), gravity=400,
               spin=10, life=(0.4, 0.7))
        for _ in range(6):
            fx.part(x + R(-12, 12), y + R(-12, 12), vy=-R(10, 30), life=R(0.7, 1.0), size=R(6, 10), size1=R(14, 20),
                    color=(110, 100, 95), kind="soft", data=0.6, delay=0.1)
    fx.flash(0.2, (255, 200, 140), 0.3)
    fx.shake(5, 0.5)
    return 0.6


def sonic_boom_launch(fx, c):
    t = c.flight(500, 0.2, 0.4)
    for k in range(3):
        fx.part(*c.mouth, life=t, size=10 + k * 3, color=(220, 240, 255), kind="ring", data=2.5, delay=k * 0.05,
                path=_line(c.mouth, c.tc))
    return t + 0.1


def pay_day_launch(fx, c):
    t = c.flight(400, 0.3, 0.5)
    for i in range(4):
        _projectile(fx, c.mouth, _jitter(c.target, 0.3), t, kind="coin", size=4, height=R(20, 40), spin=20,
                    delay=i * 0.05)
    return t + 0.15


def pay_day_land(fx, c):
    for tg in c.targets:
        _spray(fx, tg.center, 10, [(250, 210, 60)], kind="coin", speed=(60, 140), size=(3, 4), gravity=400, drag=0.3,
               spin=16, life=(0.5, 0.8), angle=(-math.pi * 0.9, -math.pi * 0.1))
        _impact(fx, tg.center, (255, 230, 120), c.p)
    return 0.4


def sound(kind="ring", color=(255, 255, 255), n=4, notes=False):
    """Growl, Screech, Sing, Supersonic, Roar: waves of sound rolling out."""
    def launch(fx, c):
        t = c.flight(300, 0.35, 0.6)
        for k in range(n):
            fx.part(*c.mouth, life=t, size=5, size1=16, color=color, kind="ring", data=1.8, delay=k * 0.08,
                    path=_line(c.mouth, c.tc))
        if notes:
            for k in range(6):
                a = (c.mouth[0], c.mouth[1] - 6)
                fx.part(*a, life=t + 0.2, size=3, color=random.choice([(255, 150, 200), (150, 200, 255),
                                                                      (255, 240, 120)]),
                        kind="note", delay=k * 0.07, path=_wavy(a, _jitter(c.target, 0.4), 8, R(0, 6)))
        return t
    return launch


def wind(fx, c, n=24, time=0.6, color=(220, 235, 255), leaves=False):
    for tg in c.targets:
        def one(fx, u, tg=tg):
            y = tg.centery + R(-tg.h * 0.6, tg.h * 0.6)
            x0 = tg.centerx - c.dir * R(60, 140)
            fx.part(x0, y, vx=c.dir * R(380, 560), vy=R(-20, 20), life=R(0.25, 0.4), size=2, color=color, kind="line",
                    data=R(14, 26))
            if leaves and random.random() < 0.3:
                fx.part(x0, y, vx=c.dir * R(250, 380), vy=R(-40, 0), life=0.4, size=3, color=random.choice(LEAF),
                        kind="leaf", spin=20)
        _emitter(fx, time, one, rate=n / time)
    return 0.15


def gust_launch(fx, c):
    t = c.flight(360, 0.3, 0.5)
    for tg in c.targets:
        cx, cy = tg.center

        def whirl(s, u, cx=cx, cy=cy):
            k = 1 - u
            for j in range(3):
                r = 10 + j * 8
                pts = [(cx + math.cos(a / 6 + u * 20 + j) * r, cy + math.sin(a / 6 + u * 20 + j) * r * 0.5)
                       for a in range(0, 30)]
                add_lines(s, scale((210, 230, 255), k), pts, 1)
        fx.put(Custom(0.6, whirl, delay=t * 0.6))
    wind(fx, c, n=20, time=t + 0.3, leaves=True)
    return t


def feathers_land(fx, c):
    for tg in c.targets:
        fx.part(*tg.center, life=0.22, size=32, color=WHITE, kind="slash", rot=-0.8)
        _spray(fx, tg.center, 8, [(250, 245, 230), (220, 200, 170)], kind="feather", speed=(30, 90), size=(3, 4),
               gravity=40, drag=2, spin=6, life=(0.6, 1.0))
        _impact(fx, tg.center, (255, 255, 230), c.p * 0.7)
    return 0.4


def drill_land(fx, c):
    for tg in c.targets:
        def drill(s, u, tg=tg):
            for j in range(6):
                a = u * 30 + j
                r = (1 - u) * 18 + 2
                add(s, glow_surface(3, (200, 200, 230)), (tg.centerx + math.cos(a) * r, tg.centery + math.sin(a) * r))
        fx.put(Custom(0.35, drill))
        _impact(fx, tg.center, (230, 230, 255), c.p, delay=0.2)
    return 0.4


def sky_attack_charge(fx, c):
    _gather(fx, c.user.center, [(255, 250, 200), (255, 220, 120), WHITE], 1.0, rate=60, radius=80)
    fx.part(*c.user.center, life=1.1, size=8, size1=34, color=(120, 100, 50), color1=(220, 190, 110), kind="glow")
    return 0.6


def sky_attack_launch(fx, c):
    t = 0.25
    fx.put(Beam(c.user.center, c.tc, 0.6, 9, (255, 220, 130), reach=t, core=WHITE))
    for _ in range(30):
        k = R(0, 1)
        fx.part(lerp(c.user.centerx, c.tc[0], k), lerp(c.user.centery, c.tc[1], k) + R(-12, 12),
                vx=-c.dir * R(60, 160), life=R(0.3, 0.5), size=1, color=(255, 240, 180), kind="line", data=20,
                delay=k * t)
    return t


def sky_attack_land(fx, c):
    for tg in c.targets:
        _ring(fx, tg.center, (255, 230, 150), 10, 90, 0.6)
        _spray(fx, tg.center, 40, [(255, 240, 180), WHITE, (255, 200, 100)], kind="spark", speed=(150, 350),
               life=(0.3, 0.6))
        _spray(fx, tg.center, 10, [(250, 245, 230)], kind="feather", speed=(40, 120), size=(3, 4), gravity=40,
               spin=6, life=(0.7, 1.1))
    fx.flash(0.35, (255, 240, 200), 0.45)
    fx.shake(7, 0.7)
    return 0.8


def fly_charge(fx, c):
    _spray(fx, _foot(c.user), 14, [(200, 190, 160)], kind="soft", speed=(30, 90), size=(5, 8), size1=14,
           angle=(-math.pi, 0), life=(0.5, 0.8), data=0.5)
    _spray(fx, _foot(c.user), 10, [(230, 240, 255)], kind="line", speed=(200, 300), angle=(-math.pi * 0.6, -math.pi * 0.4),
           life=(0.2, 0.3), data=18)
    return 0.2


def fly_land(fx, c):
    for tg in c.targets:
        fx.put(Beam((tg.centerx + c.dir * -30, tg.top - 120), tg.center, 0.25, 4, (220, 235, 255), reach=0.08))
        _impact(fx, tg.center, (230, 240, 255), c.p)
        _spray(fx, _foot(tg), 10, [(200, 190, 160)], kind="soft", speed=(30, 90), size=(5, 8), size1=14,
               angle=(-math.pi, 0), life=(0.5, 0.8), data=0.5)
    return 0.4


def skull_bash_charge(fx, c):
    fx.part(*c.user.center, life=0.9, size=10, size1=26, color=(70, 70, 90), color1=(150, 150, 190), kind="glow")
    _gather(fx, c.user.center, [(220, 220, 255)], 0.7, rate=40, radius=50)
    return 0.4


def quick_attack_launch(fx, c):
    for _ in range(10):
        fx.part(c.user.centerx + R(-10, 10), c.user.centery + R(-c.user.h * 0.4, c.user.h * 0.4),
                vx=-c.dir * R(200, 300), life=R(0.2, 0.3), size=1, color=(230, 240, 255), kind="line", data=16)
    return 0.0


def wrap_land(fx, c, color=(200, 170, 120)):
    for tg in c.targets:
        def coils(s, u, tg=tg):
            k = min(1.0, u * 4) * (1 - max(0.0, (u - 0.75) * 4))
            for j in range(3):
                y = tg.centery + (j - 1) * tg.h * 0.22
                r = tg.w * 0.55 * (1.3 - 0.3 * min(1.0, u * 3))
                rect = pygame.Rect(0, 0, round(r * 2), 8)
                rect.center = (tg.centerx, round(y))
                pygame.draw.ellipse(s, scale(color, 0.4 + 0.6 * k), rect, 2)
        fx.put(Custom(0.6, coils))
        _impact(fx, tg.center, (255, 230, 180), c.p * 0.5, delay=0.2)
    return 0.4


def dragon_rage_launch(fx, c):
    t = c.flight(340, 0.35, 0.55)
    cols = [(120, 90, 255), (90, 150, 255), (200, 120, 255)]

    def puff(fx, u):
        bb = _jitter(c.target, 0.2)
        fx.part(*c.mouth, life=R(0.25, 0.35), size=R(3, 5), size1=R(6, 9), color=random.choice(cols),
                color1=(40, 10, 80), kind="glow", path=_wavy(c.mouth, bb, R(4, 10), R(0, 6)))
    _emitter(fx, t, puff, rate=80)
    return t * 0.6


def dragon_rage_land(fx, c):
    cols = [(120, 90, 255), (90, 150, 255), (200, 120, 255)]
    for tg in c.targets:
        flames(fx, tg, 0.8, 40, size=(3, 6), colors=cols)
        _ring(fx, tg.center, (140, 110, 255), 8, 50, 0.4)
    fx.shake(3, 0.4)
    return 0.6


# --- moves on the user or its side

def aura(color, rising=True, n=14):
    def fn(fx, c):
        for tg in c.targets:
            def one(fx, u, tg=tg):
                x = tg.centerx + R(-tg.w * 0.5, tg.w * 0.5)
                fx.part(x, tg.bottom - R(0, 6), vy=-R(60, 110) if rising else R(40, 80), life=R(0.4, 0.6), size=2,
                        color=color, kind="line", data=R(6, 12))
            _emitter(fx, 0.6, one, rate=n / 0.6 * 2)
            fx.part(*tg.center, life=0.6, size=max(tg.w, tg.h) * 0.5, size1=max(tg.w, tg.h) * 0.7,
                    color=scale(color, 0.35), color1=(0, 0, 0), kind="glow")
        return 0.5
    return fn


def harden(fx, c):
    for tg in c.targets:
        def shine(s, u, tg=tg):
            x = lerp(tg.left - 10, tg.right + 10, u)
            paint_lines(s, WHITE, 0.8 * (1 - u * 0.5), [(x - 8, tg.bottom), (x + 8, tg.top)], 3)
        fx.put(Custom(0.35, shine))
        _glint(fx, tg, delay=0.3)
    return 0.45


def swords_dance(fx, c):
    for tg in c.targets:
        for k in range(4):
            a0 = k / 4 * 6.28

            def path(p, u, a0=a0, tg=tg):
                a = a0 + u * 14
                return (tg.centerx + math.cos(a) * tg.w * 0.7, tg.centery + math.sin(a) * tg.h * 0.35)
            fx.part(tg.centerx, tg.centery, life=0.8, size=16, color=(230, 235, 255), kind="slash", spin=14, path=path)
        fx.part(*tg.center, life=0.8, size=max(tg.w, tg.h) * 0.6, color=(70, 50, 30), color1=(0, 0, 0), kind="glow")
    return 0.6


def agility(fx, c):
    for tg in c.targets:
        for _ in range(14):
            fx.part(tg.centerx + R(-tg.w * 0.5, tg.w * 0.5), tg.centery + R(-tg.h * 0.5, tg.h * 0.5),
                    vx=-c.dir * R(250, 400), life=R(0.2, 0.35), size=2, color=(230, 240, 255), kind="line", data=22,
                    delay=R(0, 0.3))
    return 0.4


def screen(color):
    """Light Screen, Reflect, Barrier: glassy panes rise in front of the side."""
    def fn(fx, c):
        for tg in c.targets:
            def pane(s, u, tg=tg):
                k = min(1.0, u * 4) * (1 - max(0.0, (u - 0.6) / 0.4))
                x = tg.centerx + c.dir * (tg.w * 0.6)
                h = tg.h * 1.1 * min(1.0, u * 3)
                rect = pygame.Rect(0, 0, 14, max(2, round(h)))
                rect.midbottom = (round(x), tg.bottom)
                layer = pygame.Surface(rect.size, pygame.SRCALPHA)
                layer.fill((*color, round(110 * k)))
                pygame.draw.rect(layer, (*color, round(255 * k)), layer.get_rect(), 1)
                pygame.draw.line(layer, (255, 255, 255, round(255 * k)), (3, 3), (3, max(3, rect.h - 4)))
                s.blit(layer, rect)
            fx.put(Custom(0.8, pane))
            _glint(fx, tg, color, delay=0.3)
        return 0.6
    return fn


def recover(fx, c):
    for tg in c.targets:
        fx.part(*tg.center, life=0.7, size=8, size1=max(tg.w, tg.h) * 0.8, color=(60, 120, 60), color1=(0, 0, 0),
                kind="glow")
        _ring(fx, tg.center, (160, 255, 170), max(tg.w, tg.h) * 0.8, 6, 0.6)
    return 0.4


def rest(fx, c):
    for tg in c.targets:
        for k in range(3):
            fx.part(tg.right - 4, tg.top, vx=14, vy=-24, life=1.0, size=3 + k, color=WHITE, kind="zzz", delay=k * 0.3)
    return recover(fx, c)


def splash(fx, c):
    _spray(fx, _foot(c.user), 14, WATER, kind="drop", speed=(60, 140), size=(1, 2.5), gravity=380, drag=0.3,
           angle=(-math.pi * 0.9, -math.pi * 0.1), life=(0.4, 0.7))
    return 0.4


def kiss_launch(fx, c):
    t = c.flight(220, 0.4, 0.6)
    for k in range(4):
        a = c.mouth
        fx.part(*a, life=t, size=4, color=(255, 120, 170), kind="heart", delay=k * 0.07,
                path=_wavy(a, _jitter(c.target, 0.3), 8, k))
    return t + 0.2


def glare_launch(fx, c):
    for k in range(2):
        a = (c.mouth[0] - c.dir * 4, c.mouth[1] - 4 + k * 4)
        fx.put(Beam(a, c.tc, 0.35, 1, (255, 240, 120), reach=0.08, delay=k * 0.03))
    return 0.12


def smoke_land(fx, c, colors=((60, 60, 60), (90, 90, 90), (40, 40, 45))):
    for tg in c.targets:
        for _ in range(16):
            fx.part(*_jitter(tg, 0.35), vx=R(-25, 25), vy=-R(5, 20), life=R(0.8, 1.2), size=R(8, 12),
                    size1=R(16, 24), color=random.choice(colors), kind="soft", data=0.75, delay=R(0, 0.2))
    return 0.8


def sand_launch(fx, c):
    t = c.flight(360, 0.25, 0.45)
    for i in range(30):
        a = (c.mouth[0], c.user.bottom - 6)
        fx.part(*a, life=t, size=R(1, 1.6), color=random.choice([(220, 200, 140), (200, 175, 110)]), kind="dot",
                delay=R(0, 0.12), path=_arc(a, _jitter(c.target, 0.4), R(10, 40)))
    return t + 0.1


def glint_target(fx, c):
    for tg in c.targets:
        _glint(fx, tg, (255, 255, 255), delay=0.0)
        fx.part(*tg.center, life=0.3, size=20, size1=6, color=(70, 50, 50), kind="glow")
    return 0.3


def tail_whip(fx, c):
    for _ in range(3):
        fx.part(*c.user.center, life=0.4, size=16, color=(230, 230, 230), kind="slash", rot=R(-0.5, 0.5),
                delay=R(0, 0.2))
    return 0.15


def growth(fx, c):
    aura((140, 230, 110))(fx, c)
    for tg in c.targets:
        _spray(fx, tg.center, 12, LEAF, kind="leaf", speed=(20, 50), size=(2, 3), gravity=-40, spin=8,
               life=(0.5, 0.8))
    return 0.5


def kinesis(fx, c):
    for tg in c.targets:
        _orbit_stars(fx, tg, 4, 0.8, (230, 160, 255))
        psy_rings(fx, tg, 3, (200, 140, 255))
    return 0.5


def thrash_land(fx, c):
    for tg in c.targets:
        for k in range(4):
            _impact(fx, _jitter(tg, 0.3), (255, 210, 160), c.p, delay=k * 0.09)
    return 0.45


def double_kick_land(fx, c):
    return contact((255, 220, 170), stars=2)(fx, c)


def seismic_land(fx, c):
    for tg in c.targets:
        _impact(fx, (tg.centerx, tg.bottom - 6), (255, 210, 150), 0.9)
        _spray(fx, _foot(tg), 18, DIRT, kind="soft", speed=(40, 120), size=(4, 7), size1=12,
               angle=(-math.pi, 0), life=(0.4, 0.7), data=0.5)
    fx.shake(6, 0.5)
    return 0.5


def roar_launch(fx, c):
    sound(color=(255, 220, 200), n=6)(fx, c)
    fx.shake(3, 0.5)
    return 0.4


# --- fallbacks by type

TYPE_FX = {
    "fire": Recipe(ember_launch, fire_punch_land),
    "water": Recipe(water_gun_launch, splash_land),
    "grass": Recipe(razor_leaf_launch, razor_leaf_land),
    "electric": Recipe(thunder_shock_launch, thunder_shock_land),
    "ice": Recipe(ice_beam_launch, ice_land),
    "psychic": Recipe(confusion_launch, confusion_land),
    "rock": Recipe(rock_throw_launch, rock_throw_land),
    "ground": Recipe(None, seismic_land),
    "poison": Recipe(sludge_launch, sludge_land),
    "ghost": Recipe(night_shade_launch, night_shade_land),
    "dragon": Recipe(dragon_rage_launch, dragon_rage_land),
}


def _fallback(move) -> Recipe:
    if move.target != "enemy":
        color = COLORS.get(move.type, (220, 220, 220)) if move.type else (220, 220, 220)
        return Recipe(None, aura(color))
    if move.type in TYPE_FX and move.type not in ("normal", "fighting", "flying", "bug"):
        return TYPE_FX[move.type]
    color = mix(COLORS.get(move.type, (230, 230, 230)) if move.type else (230, 230, 230), WHITE, 0.4)
    return Recipe(None, contact(color))


def _charge_glow(fx, c):
    fx.part(*c.user.center, life=0.8, size=8, size1=24, color=(60, 60, 80), color1=(120, 120, 160), kind="glow")
    _gather(fx, c.user.center, [(220, 220, 255), WHITE], 0.6, rate=40, radius=50)
    return 0.4


# --------------------------------------------------------------- the recipes

RECIPES: dict[str, Recipe] = {
    # Normal
    "Tackle": Recipe(None, contact()),
    "Scratch": Recipe(None, contact(slash=3)),
    "Pound": Recipe(None, contact()),
    "Quick Attack": Recipe(quick_attack_launch, contact((230, 240, 255))),
    "Headbutt": Recipe(None, contact(shake=1.3)),
    "Bite": Recipe(None, bite_land),
    "Horn Attack": Recipe(None, contact(slash=1)),
    "Slash": Recipe(None, contact(slash=3, shake=1.2)),
    "Hyper Fang": Recipe(None, bite_land),
    "Super Fang": Recipe(None, bite_land),
    "Vice Grip": Recipe(None, bite_land),
    "Slam": Recipe(None, contact(shake=1.2)),
    "Body Slam": Recipe(None, contact(shake=1.4)),
    "Take Down": Recipe(None, contact(shake=1.4)),
    "Skull Bash": Recipe(None, contact((220, 220, 255), shake=1.5), skull_bash_charge),
    "Double-Edge": Recipe(quick_attack_launch, contact(shake=1.6)),
    "Thrash": Recipe(None, thrash_land),
    "Hyper Beam": Recipe(hyper_beam_launch, hyper_beam_land),
    "Swift": Recipe(swift_launch, swift_land),
    "Fury Attack": Recipe(None, contact(slash=1)),
    "Fury Swipes": Recipe(None, contact(slash=3)),
    "Double Slap": Recipe(None, contact()),
    "Comet Punch": Recipe(None, contact((255, 240, 180))),
    "Mega Punch": Recipe(None, contact((255, 230, 150), shake=1.5)),
    "Mega Kick": Recipe(None, contact((255, 230, 150), shake=1.7)),
    "Dizzy Punch": Recipe(None, lambda fx, c: (contact()(fx, c), [_orbit_stars(fx, t) for t in c.targets])[0] + 0.3),
    "Stomp": Recipe(None, seismic_land),
    "Constrict": Recipe(None, wrap_land),
    "Wrap": Recipe(None, wrap_land),
    "Bind": Recipe(None, wrap_land),
    "Spike Cannon": Recipe(lambda fx, c: needle_launch(fx, c, 4), contact()),
    "Self-Destruct": Recipe(explosion_launch, explosion_land),
    "Explosion": Recipe(explosion_launch, explosion_land),
    "Egg Bomb": Recipe(egg_bomb_launch, egg_bomb_land),
    "Sonic Boom": Recipe(sonic_boom_launch, contact((220, 240, 255))),
    "Pay Day": Recipe(pay_day_launch, pay_day_land),
    "Gust": Recipe(gust_launch, contact((220, 235, 255))),
    "Karate Chop": Recipe(None, contact(slash=1)),
    "Growl": Recipe(sound(color=(255, 220, 200)), None),
    "Screech": Recipe(sound(color=(255, 160, 160), n=6), glint_target),
    "Supersonic": Recipe(sound(color=(200, 230, 255), n=6), None),
    "Sing": Recipe(sound(color=(255, 200, 230), n=3, notes=True), None),
    "Roar": Recipe(roar_launch, lambda fx, c: wind(fx, c)),
    "Whirlwind": Recipe(None, lambda fx, c: wind(fx, c, n=40, time=0.7)),
    "Tail Whip": Recipe(tail_whip, None),
    "Leer": Recipe(glare_launch, glint_target),
    "Glare": Recipe(glare_launch, glint_target),
    "Sand-Attack": Recipe(sand_launch, lambda fx, c: smoke_land(fx, c, ((210, 190, 130), (190, 170, 110)))),
    "Smokescreen": Recipe(lambda fx, c: gas_launch(fx, c, ((50, 50, 55), (80, 80, 85))), smoke_land),
    "Lovely Kiss": Recipe(kiss_launch, lambda fx, c: hypnosis_land(fx, c)),
    "Defense Curl": Recipe(None, harden),
    "Harden": Recipe(None, harden),
    "Focus Energy": Recipe(None, aura((255, 160, 90))),
    "Growth": Recipe(None, growth),
    "Recover": Recipe(None, recover),
    "Softboiled": Recipe(None, recover),
    "Swords Dance": Recipe(None, swords_dance),
    "Splash": Recipe(None, splash),
    # Fighting
    "Low Kick": Recipe(None, contact((255, 220, 170))),
    "Double Kick": Recipe(None, double_kick_land),
    "Submission": Recipe(None, thrash_land),
    "Seismic Toss": Recipe(None, seismic_land),
    # Flying
    "Peck": Recipe(None, contact((255, 250, 220))),
    "Wing Attack": Recipe(None, feathers_land),
    "Drill Peck": Recipe(None, drill_land),
    "Fly": Recipe(None, fly_land, fly_charge),
    "Sky Attack": Recipe(sky_attack_launch, sky_attack_land, sky_attack_charge),
    "Perch": Recipe(None, lambda fx, c: _spray(fx, _foot(c.user), 8, [(250, 245, 230)], kind="feather",
                                               speed=(20, 60), size=(3, 4), gravity=40, spin=6,
                                               life=(0.6, 1.0)) or 0.3),
    # Fire
    "Ember": Recipe(ember_launch, ember_land),
    "Fire Punch": Recipe(None, fire_punch_land),
    "Fire Spin": Recipe(lambda fx, c: ember_launch(fx, c), fire_spin_land),
    "Flamethrower": Recipe(flamethrower_launch, flamethrower_land),
    "Fire Blast": Recipe(fire_blast_launch, fire_blast_land),
    # Water
    "Bubble": Recipe(bubble_launch, bubble_land),
    "Water Gun": Recipe(water_gun_launch, splash_land),
    "Bubble Beam": Recipe(bubble_beam_launch, bubble_beam_land),
    "Clamp": Recipe(None, lambda fx, c: bite_land(fx, c, (150, 200, 255))),
    "Surf": Recipe(surf_launch, surf_land),
    "Hydro Pump": Recipe(hydro_pump_launch, hydro_pump_land),
    "Withdraw": Recipe(None, withdraw),
    # Grass
    "Absorb": Recipe(None, lambda fx, c: (contact((150, 255, 130))(fx, c), drain_land(fx, c, n=6))[1]),
    "Mega Drain": Recipe(None, lambda fx, c: (contact((150, 255, 130))(fx, c), drain_land(fx, c, n=12))[1]),
    "Vine Whip": Recipe(vine_whip_launch, vine_whip_land),
    "Razor Leaf": Recipe(razor_leaf_launch, razor_leaf_land),
    "Petal Dance": Recipe(petal_dance_launch, petal_dance_land),
    "Solar Beam": Recipe(solar_launch, solar_land, solar_charge),
    "Leaf Shield": Recipe(None, leaf_shield),
    "Leech Seed": Recipe(leech_seed_launch, leech_seed_land),
    "Sleep Powder": powder([(120, 160, 255), (170, 200, 255)], sleep=True),
    "Spore": powder([(200, 230, 140), (230, 240, 180)], sleep=True),
    "Stun Spore": powder([(255, 230, 90), (250, 210, 60)]),
    "Poison Powder": powder([(190, 110, 220), (160, 80, 200)]),
    # Electric
    "Thunder Shock": Recipe(thunder_shock_launch, thunder_shock_land),
    "Thunderbolt": Recipe(thunderbolt_launch, thunderbolt_land),
    "Thunder": Recipe(thunder_launch, thunder_land),
    "Thunder Punch": Recipe(None, thunder_punch_land),
    "Thunder Wave": Recipe(thunder_wave_launch, thunder_wave_land),
    # Ice
    "Ice Beam": Recipe(ice_beam_launch, ice_land),
    "Aurora Beam": Recipe(aurora_launch, ice_land),
    "Blizzard": Recipe(blizzard_launch, blizzard_land),
    "Ice Punch": Recipe(None, ice_punch_land),
    # Rock, ground
    "Rock Throw": Recipe(rock_throw_launch, rock_throw_land),
    "Rock Slide": Recipe(rock_slide_launch, rock_slide_land),
    "Earthquake": Recipe(earthquake_launch, earthquake_land),
    "Dig": Recipe(None, dig_land, dig_charge),
    "Bone Club": Recipe(lambda fx, c: bone_launch(fx, c), contact((255, 240, 210), shake=1.2)),
    "Bonemerang": Recipe(lambda fx, c: bone_launch(fx, c, back=True), contact((255, 240, 210), stars=2)),
    # Psychic
    "Confusion": Recipe(confusion_launch, confusion_land),
    "Psybeam": Recipe(psybeam_launch, psybeam_land),
    "Psychic": Recipe(psychic_launch, psychic_land),
    "Hypnosis": Recipe(hypnosis_launch, hypnosis_land),
    "Kinesis": Recipe(None, kinesis),
    "Agility": Recipe(None, agility),
    "Barrier": Recipe(None, screen((180, 220, 255))),
    "Light Screen": Recipe(None, screen((255, 240, 140))),
    "Reflect": Recipe(None, screen((140, 190, 255))),
    "Meditate": Recipe(None, aura((230, 150, 255))),
    "Rest": Recipe(None, rest),
    # Ghost
    "Lick": Recipe(None, lick_land),
    "Night Shade": Recipe(night_shade_launch, night_shade_land),
    "Confuse Ray": Recipe(confuse_ray_launch, confuse_ray_land),
    # Poison
    "Poison Sting": Recipe(lambda fx, c: needle_launch(fx, c, 1, (200, 120, 230)), contact((220, 150, 240))),
    "Acid": Recipe(lambda fx, c: sludge_launch(fx, c, [(170, 230, 80), (140, 200, 60)], 3, 3),
                   lambda fx, c: sludge_land(fx, c, [(170, 230, 80), (140, 200, 60)])),
    "Sludge": Recipe(lambda fx, c: sludge_launch(fx, c, POISON, 4, 5), lambda fx, c: sludge_land(fx, c, POISON, 24)),
    "Smog": Recipe(gas_launch, gas_land),
    "Poison Gas": Recipe(gas_launch, gas_land),
    # Bug
    "String Shot": Recipe(string_shot_launch, string_shot_land),
    "Pin Missile": Recipe(lambda fx, c: needle_launch(fx, c, 4), contact((240, 240, 200))),
    "Twineedle": Recipe(lambda fx, c: needle_launch(fx, c, 2, (220, 240, 160)), contact((230, 250, 170), stars=2)),
    "Leech Life": Recipe(None, lambda fx, c: (bite_land(fx, c, (255, 150, 150)),
                                              drain_land(fx, c, [(255, 90, 90), (255, 160, 140)], 8))[1]),
    # Dragon
    "Dragon Rage": Recipe(dragon_rage_launch, dragon_rage_land),
}
