"""The Town Map (M, or the Map touch button, on a map; `world/townmap.py`
has what it shows): Kanto's towns and routes as far as the player has been,
where they are, quest marks, and what the place under the cursor has.
Arrows move the cursor from place to place; X (or M) closes it. Once Fly
is learned (quest "learn_to_fly"), Enter on a town visited flies there
(`fly_to`, which the pause menu acts on)."""

from __future__ import annotations

import math

import pygame

from ..engine import ui
from ..world import townmap
from ..world.townmap import EDGES, NODES, SAFFRON

EVOLVE_COLOR = (255, 130, 200)  # (as overworld.EVOLVE_COLOR)
CLOSE_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE, pygame.K_m)
FLY_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
DIRS = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}

GRID = 19          # px between grid units
CITIES = {"pallet", "viridian", "pewter", "cerulean", "vermilion", "lavender", "celadon"}
LAND = (58, 92, 62)
LAND_EDGE = (40, 66, 46)
ROAD = (226, 200, 140)
CAVE = (150, 104, 70)
TUNNEL = (170, 150, 120)
DIM = (92, 110, 96)
TOWN = (236, 236, 244)
TOWN_EDGE = (200, 60, 60)
HERE = (255, 80, 80)
PICK = ui.YELLOW


class TownMap:
    RECT = pygame.Rect(10, 8, 620, 344)
    MAP = pygame.Rect(22, 32, 352, 300)    # the map's area
    ORIGIN = (MAP.x + 16, MAP.y + 12)      # grid (0, 0)
    INFO_X = 386                           # the info column

    def __init__(self, game, here: str, fly: str | None = None):
        """`fly`: None (Fly not learned), "" (it can be used from here), or
        why it can't be used from here."""
        self.game = game
        self.here = here
        self.fly = fly
        self.fly_to = ""  # the town chosen to Fly to
        self.message = ""
        self.view = townmap.view(game)
        self.marks = townmap.marks(game)
        self.places = [p for p in list(NODES) + list(EDGES) if self.view.shown(p)]
        self.choice = here if here in self.places else next(iter(self.places))

    # ------------------------------------------------------------------ keys

    def handle_key(self, key: int) -> bool:
        if key in DIRS:
            self._move(*DIRS[key])
            self.message = ""
        elif key in FLY_KEYS and self.fly is not None:
            if self.fly:
                self.message = self.fly
            elif not self._flyable(self.choice):
                self.message = "Fly to a town you've visited."
            elif self.choice == self.here:
                self.message = "You're already here."
            else:
                self.fly_to = self.choice
                return True
        return key in CLOSE_KEYS

    def _flyable(self, place: str) -> bool:
        return place in NODES and place in self.view.known

    def _move(self, dx: int, dy: int) -> None:
        """To the nearest place that way (straight ahead counts more than off to the side)."""
        x0, y0 = townmap.anchor(self.choice)
        best, best_score = None, math.inf
        for p in self.places:
            x, y = townmap.anchor(p)
            ahead = (x - x0) * dx + (y - y0) * dy
            if p == self.choice or ahead <= 0.2:
                continue
            side = abs((x - x0) * dy) + abs((y - y0) * dx)
            score = ahead + 2.5 * side
            if score < best_score:
                best, best_score = p, score
        if best:
            self.choice = best

    # ------------------------------------------------------------------ draw

    def _px(self, pt: tuple[float, float]) -> tuple[int, int]:
        return round(self.ORIGIN[0] + pt[0] * GRID), round(self.ORIGIN[1] + pt[1] * GRID)

    def _draw_map(self, s: pygame.Surface, t: float) -> None:
        ox, oy = self.RECT.topleft  # (the surface is the box)
        area = self.MAP.move(-ox, -oy)
        pygame.draw.rect(s, LAND, area, border_radius=4)
        pygame.draw.rect(s, LAND_EDGE, area, 2, border_radius=4)
        px = lambda pt: (self._px(pt)[0] - ox, self._px(pt)[1] - oy)  # noqa: E731
        # Saffron City: shut.
        sx, sy = px(SAFFRON)
        pygame.draw.rect(s, (110, 110, 120), (sx - 6, sy - 6, 12, 12))
        pygame.draw.rect(s, (70, 70, 80), (sx - 6, sy - 6, 12, 12), 1)
        # The routes.
        for key, (_, kind) in EDGES.items():
            if not self.view.shown(key):
                continue
            pts = [px(p) for p in townmap.points(key)]
            known = key in self.view.known
            color = {"road": ROAD, "cave": CAVE, "tunnel": TUNNEL}[kind] if known else DIM
            if key == self.choice:
                pygame.draw.lines(s, PICK, False, pts, 7)
            if kind == "road" and known:
                pygame.draw.lines(s, color, False, pts, 4)
            else:  # dashed: caves, tunnels, and routes not walked yet
                _dashed(s, color, pts, 4 if kind == "cave" else 3)
        # The towns.
        for key, pt in NODES.items():
            if not self.view.shown(key):
                continue
            x, y = px(pt)
            r = 5 if key in CITIES else 3
            rect = pygame.Rect(x - r, y - r, 2 * r + 1, 2 * r + 1)
            if key == self.choice:
                pygame.draw.rect(s, PICK, rect.inflate(6, 6), 2)
            if key in self.view.known:
                pygame.draw.rect(s, TOWN, rect)
                pygame.draw.rect(s, TOWN_EDGE, rect, 1)
            else:
                pygame.draw.rect(s, DIM, rect)
        # Where the player is: a blinking ring.
        if self.here in self.places and int(t * 2.5) % 2 == 0:
            x, y = px(townmap.anchor(self.here))
            pygame.draw.circle(s, HERE, (x, y), 8, 2)
        # Quest marks: diamonds (a step's place) drawn here; "!" and "?" are text.
        for place, marks in self.marks.items():
            if place not in self.places:
                continue
            x, y = px(townmap.anchor(place))
            for i, mark in enumerate(m for m in marks if m.text == "◆"):
                color = EVOLVE_COLOR if mark.evolve else ui.YELLOW
                _diamond(s, x + 9 + i * 7, y - 9, color)

    def draw_overlay(self, window: pygame.Surface) -> None:
        t = pygame.time.get_ticks() / 1000
        r = self.RECT
        shade = pygame.Surface(window.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))  # (the map's own text under it, dimmed)
        window.blit(shade, (0, 0))
        box = pygame.Surface(r.size, pygame.SRCALPHA)
        ui.window_box(box, box.get_rect())
        self._draw_map(box, t)
        lx, ly = self.MAP.x + 96 - r.x, self.MAP.bottom + 8 - r.y  # (the legend's diamond)
        _diamond(box, lx, ly, ui.YELLOW)
        ui.blit_scaled(window, box, r.topleft)
        ui.text(window, "Town Map", (r.x + 12, r.y + 6), ui.YELLOW, size=24)
        # City names, and "!"/"?" marks.
        for key in NODES:
            if key in townmap.CITY_LABELS and key in self.view.known:
                x, y = self._px(NODES[key])
                dx, dy, align = townmap.CITY_LABELS[key]
                ui.text(window, townmap.name(key, self.view), (x + dx, y + dy), ui.WHITE, size=16, align=align)
        for place, marks in self.marks.items():
            if place not in self.places:
                continue
            x, y = self._px(townmap.anchor(place))
            texts = [m for m in marks if m.text != "◆"]
            for i, mark in enumerate(texts):
                color = EVOLVE_COLOR if mark.evolve else ui.YELLOW
                ui.text(window, mark.text, (x - 9 - i * 6, y - 18), color, size=22, align="center")
        self._draw_info(window)
        y = self.MAP.bottom + 3
        ui.text(window, "!   quest to take", (self.MAP.x + 4, y), ui.GREY, size=16)
        ui.text(window, "next step", (self.MAP.x + 102, y), ui.GREY, size=16)
        ui.text(window, "?   hand in", (self.MAP.x + 166, y), ui.GREY, size=16)
        sx, sy = self._px(SAFFRON)
        ui.text(window, "Saffron City (shut)", (sx, sy + 8), (170, 170, 180), size=14, align="center")
        keys = "Arrows: choose   Enter: fly here   X: close" if self.fly is not None else "Arrows: choose   X: close"
        ui.text(window, keys, (r.right - 12, r.bottom - 15), ui.GREY, size=18, align="right")
        if self.message:
            ui.text(window, self.message, (r.right - 12, r.bottom - 30), ui.YELLOW, size=18, align="right")

    def _draw_info(self, window: pygame.Surface) -> None:
        x, y, width = self.INFO_X, self.MAP.y, self.RECT.right - self.INFO_X - 12
        ui.text(window, townmap.name(self.choice, self.view), (x, y), ui.YELLOW, size=24)
        y += 18
        if self.choice == self.here:
            ui.text(window, "You are here", (x, y), HERE, size=18)
            y += 14
        colors = {"head": ui.WHITE, "new": ui.YELLOW, "evolve": EVOLVE_COLOR, "step": ui.YELLOW,
                  "step_evolve": EVOLVE_COLOR, "dim": ui.GREY, "": (200, 200, 215)}
        for kind, text in townmap.info(self.game, self.choice, self.view):
            if kind == "head":
                y += 4
            prefix = "- " if kind.startswith("step") else ""
            for line in ui.wrap(prefix + text, 18, width):
                if y > self.RECT.bottom - 30:
                    return
                ui.text(window, line, (x, y), colors[kind], size=18)
                y += 12
            y += 2


def _diamond(s: pygame.Surface, cx: int, cy: int, color) -> None:
    """A quest step's mark."""
    pygame.draw.polygon(s, ui.SHADOW, [(cx, cy - 3), (cx + 4, cy + 1), (cx, cy + 5), (cx - 4, cy + 1)])
    pygame.draw.polygon(s, color, [(cx, cy - 4), (cx + 3, cy), (cx, cy + 4), (cx - 3, cy)])


def _dashed(s: pygame.Surface, color, pts: list[tuple[int, int]], width: int, dash: int = 5) -> None:
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(length // dash))
        for i in range(0, n, 2):
            a, b = i / n, min(1, (i + 1) / n)
            pygame.draw.line(s, color, (x1 + (x2 - x1) * a, y1 + (y2 - y1) * a),
                             (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b), width)

