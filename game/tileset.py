"""Placeholder art for maps, drawn in code from the theme's colours: tiles,
decorations (grass tufts, flowers, ice crystals, icicles) and parallax
backgrounds. To be replaced by Pixellab tilesets.
"""

import random

import pygame

from . import settings
from .level import EMPTY, PLATFORM, ROWS, SOLID, TILE, Level
from .themes import Palette, Theme

PARALLAX = (0.2, 0.5)  # how fast the far and near background layers scroll


def _speckle(surface: pygame.Surface, rect: pygame.Rect, rng: random.Random, colors, count: int) -> None:
    for _ in range(count):
        surface.set_at((rng.randrange(rect.left, rect.right), rng.randrange(rect.top, rect.bottom)),
                       rng.choice(colors))


def _fill_tile(surface: pygame.Surface, rect: pygame.Rect, p: Palette, rng: random.Random) -> None:
    surface.fill(p.fill, rect)
    _speckle(surface, rect, rng, (p.fill_dark, p.fill_dark, p.fill_light), 9)
    if rng.random() < 0.25:  # a pebble
        x, y = rng.randrange(rect.left + 2, rect.right - 4), rng.randrange(rect.top + 2, rect.bottom - 3)
        pygame.draw.rect(surface, p.fill_dark, (x, y, 3, 2))
        surface.set_at((x, y), p.fill_light)


def _top_tile(surface: pygame.Surface, rect: pygame.Rect, p: Palette, rng: random.Random) -> None:
    """Ground with grass or snow on top, its lower edge ragged."""
    _fill_tile(surface, rect, p, rng)
    for x in range(rect.left, rect.right):
        depth = rng.choice((4, 5, 5, 6))
        pygame.draw.line(surface, p.top, (x, rect.top), (x, rect.top + depth - 1))
        surface.set_at((x, rect.top + depth), p.top_dark)
    _speckle(surface, pygame.Rect(rect.left, rect.top + 1, TILE, 3), rng, (p.top_light, p.top_dark), 3)
    pygame.draw.line(surface, p.top_light, (rect.left, rect.top), (rect.right - 1, rect.top))


def _underside(surface: pygame.Surface, rect: pygame.Rect, p: Palette) -> None:
    """The bottom edge of a ceiling."""
    pygame.draw.line(surface, p.fill_dark, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
    pygame.draw.line(surface, p.fill_dark, (rect.left, rect.bottom - 2), (rect.right - 1, rect.bottom - 2))


def _platform_tile(surface: pygame.Surface, rect: pygame.Rect, p: Palette, left_end: bool, right_end: bool,
                   theme: Theme) -> None:
    """A thin plank (or slab of ice) along the top of the tile."""
    plank = pygame.Rect(rect.left, rect.top, TILE, 6)
    if left_end:
        plank.left += 1
        plank.width -= 1
    if right_end:
        plank.width -= 1
    pygame.draw.rect(surface, p.platform, plank)
    pygame.draw.line(surface, p.platform_light, plank.topleft, (plank.right - 1, plank.top))
    pygame.draw.line(surface, p.platform_dark, (plank.left, plank.bottom - 1), (plank.right - 1, plank.bottom - 1))
    if theme.key == "meadow":
        for x in (rect.left + 3, rect.left + 11):  # nails / plank joints
            surface.set_at((x, rect.top + 3), p.platform_dark)
        pygame.draw.line(surface, p.platform_dark, (rect.right - 1, rect.top + 1), (rect.right - 1, rect.top + 4))
    else:
        surface.set_at((rect.left + 5, rect.top + 2), p.platform_light)
    if left_end:
        pygame.draw.line(surface, p.platform_dark, (plank.left, plank.top), (plank.left, plank.bottom - 1))
    if right_end:
        pygame.draw.line(surface, p.platform_dark, (plank.right - 1, plank.top), (plank.right - 1, plank.bottom - 1))


# ------------------------------------------------------------- decorations

def _tuft(s, x, y, rng, p):
    for dx, h in ((-2, 3), (0, 4), (2, 3)):
        pygame.draw.line(s, p.top_dark if dx else p.top, (x + dx, y - 1), (x + dx + (dx > 0) - (dx < 0), y - h))


def _flower(s, x, y, rng, p):
    pygame.draw.line(s, p.top_dark, (x, y - 1), (x, y - 4))
    petal = rng.choice(((240, 80, 80), (250, 220, 80), (250, 250, 250), (200, 120, 240)))
    for dx, dy in ((-1, -5), (1, -5), (0, -6), (0, -4)):
        s.set_at((x + dx, y + dy), petal)
    s.set_at((x, y - 5), (250, 200, 60))


def _bush(s, x, y, rng, p):
    for cx, cy, r in ((x - 4, y - 4, 4), (x + 4, y - 4, 4), (x, y - 6, 5)):
        pygame.draw.circle(s, p.top_dark, (cx, cy), r)
    for cx, cy, r in ((x - 4, y - 5, 3), (x + 3, y - 5, 3), (x, y - 7, 3)):
        pygame.draw.circle(s, p.top, (cx, cy), r)
    s.set_at((x - 1, y - 9), p.top_light)


def _rock(s, x, y, rng, p):
    pygame.draw.ellipse(s, p.fill_dark, (x - 4, y - 5, 9, 6))
    pygame.draw.ellipse(s, p.fill_light, (x - 3, y - 5, 5, 3))


def _crystal(s, x, y, rng, p):
    for dx, h, color in ((-3, 6, (110, 200, 240)), (2, 9, (150, 225, 255)), (0, 12, (190, 240, 255))):
        pygame.draw.polygon(s, color, [(x + dx - 2, y), (x + dx + 2, y), (x + dx, y - h)])
    s.set_at((x, y - 9), (255, 255, 255))


def _snow_mound(s, x, y, rng, p):
    pygame.draw.ellipse(s, p.top_dark, (x - 6, y - 4, 13, 6))
    pygame.draw.ellipse(s, p.top, (x - 5, y - 5, 10, 5))


def _icicle(s, x, y, rng, p):
    """Hangs down from a ceiling whose underside is at `y`."""
    h = rng.randint(4, 10)
    pygame.draw.polygon(s, (170, 220, 250), [(x - 2, y), (x + 2, y), (x, y + h)])
    pygame.draw.line(s, (235, 250, 255), (x - 1, y), (x, y + h - 2))


DECOR = {  # theme -> [(chance per ground tile, draw)]
    "meadow": [(0.30, _tuft), (0.10, _flower), (0.05, _bush), (0.04, _rock)],
    "ice_cave": [(0.07, _crystal), (0.10, _snow_mound), (0.05, _rock)],
}


# --------------------------------------------------------------------- map

def render(level: Level) -> pygame.Surface:
    """The map's tiles and decorations, drawn once (transparent where empty)."""
    p, theme = level.theme.palette, level.theme
    surface = pygame.Surface((level.width, ROWS * TILE), pygame.SRCALPHA)
    decor = []
    for row in range(ROWS):
        for col in range(level.cols):
            kind = level.grid[row][col]
            rng = random.Random(level.seed * 1_000_003 + row * 7919 + col)
            rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            if kind == SOLID:
                above, below = level.tile(col, row - 1), level.tile(col, row + 1)
                if above == SOLID or row == 0:
                    _fill_tile(surface, rect, p, rng)
                else:
                    _top_tile(surface, rect, p, rng)
                    for chance, draw in DECOR[theme.key]:
                        if rng.random() < chance:
                            decor.append((draw, rect.left + rng.randint(4, 12), rect.top, rng))
                            break
                if below != SOLID and row + 1 < ROWS:  # a ceiling's underside
                    _underside(surface, rect, p)
                    if theme.ceiling and rng.random() < 0.4:
                        decor.append((_icicle, rect.left + rng.randint(3, 13), rect.bottom, rng))
                # Darken the sides of steps, so height changes read clearly.
                for dx, edge in ((-1, rect.left), (1, rect.right - 1)):
                    if level.tile(col + dx, row) == EMPTY:
                        pygame.draw.line(surface, p.fill_dark, (edge, rect.top), (edge, rect.bottom - 1))
            elif kind == PLATFORM:
                _platform_tile(surface, rect, p, level.tile(col - 1, row) != PLATFORM,
                               level.tile(col + 1, row) != PLATFORM, theme)
    for draw, x, y, rng in decor:  # on top of the tiles they stick out over
        draw(surface, x, y, rng, p)
    return surface


# -------------------------------------------------------------- background

def _layer_width(level: Level, factor: float) -> int:
    return round(settings.LOGICAL_SIZE[0] + (level.width - settings.LOGICAL_SIZE[0]) * factor) + 1


def backgrounds(level: Level) -> list[pygame.Surface]:
    """The far and near background layers, each just wide enough for its parallax."""
    rng = random.Random(level.seed)
    h = settings.LOGICAL_SIZE[1]
    far_w, near_w = (_layer_width(level, f) for f in PARALLAX)
    far = pygame.Surface((far_w, h))
    near = pygame.Surface((near_w, h), pygame.SRCALPHA)
    if level.theme.key == "ice_cave":
        _gradient(far, (16, 22, 42), (40, 56, 92))
        for x in range(0, far_w, 24):  # the cave's back wall: hanging and standing rock
            w = rng.randint(14, 30)
            pygame.draw.polygon(far, (30, 42, 72), [(x, 0), (x + w, 0), (x + w // 2, rng.randint(30, 90))])
            pygame.draw.polygon(far, (30, 42, 72), [(x, h), (x + w, h), (x + w // 2, h - rng.randint(60, 160))])
        for _ in range(far_w // 40):  # faint glowing crystals
            x, y = rng.randrange(far_w), rng.randint(100, 280)
            pygame.draw.circle(far, (60, 100, 150), (x, y), 3)
            far.set_at((x, y), (150, 220, 255))
        for x in range(0, near_w, 40):
            w = rng.randint(24, 44)
            pygame.draw.polygon(near, (44, 60, 98), [(x, h), (x + w, h), (x + w // 2, h - rng.randint(90, 190))])
            pygame.draw.polygon(near, (44, 60, 98), [(x, 0), (x + w, 0), (x + w // 2, rng.randint(40, 110))])
    else:
        _gradient(far, (120, 190, 240), (205, 234, 250))
        for _ in range(far_w // 90):  # clouds
            x, y = rng.randrange(far_w), rng.randint(20, 120)
            for dx, dy, r in ((0, 0, 10), (12, -4, 13), (24, 0, 10)):
                pygame.draw.circle(far, (245, 250, 255), (x + dx, y + dy), r)
        for x in range(-60, far_w, 110):  # distant hills
            r = rng.randint(80, 140)
            pygame.draw.circle(far, (150, 200, 170), (x + r // 2, 250 + r // 3), r)
        for x in range(-20, near_w, 18):  # a line of trees
            top = rng.randint(200, 235)
            pygame.draw.circle(near, (84, 150, 96), (x, top), rng.randint(14, 20))
            pygame.draw.rect(near, (84, 150, 96), (x - 12, top, 24, h - top))
    return [far, near]


def _gradient(surface: pygame.Surface, top, bottom) -> None:
    h = surface.get_height()
    for y in range(h):
        t = y / (h - 1)
        pygame.draw.line(surface, [round(a + (b - a) * t) for a, b in zip(top, bottom)], (0, y),
                         (surface.get_width(), y))
