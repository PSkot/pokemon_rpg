"""Drawing water (the `WATER` tiles of a map with `Theme.sea`): the water
itself, drawn with the map's tiles (`render`), and its front (`draw_front`),
drawn over everyone on the map, so swimmers sit in the water up to
SURF_SINK px and the surface's waves move."""

import math
import random

import pygame

from .level import ROWS, TILE, WATER, Level

SURF_SINK = 9      # px a swimmer's feet sit under the water's surface
FRONT = 12         # px of see-through water drawn over swimmers, from the surface down
FRONT_ALPHA = 150
CREST = (220, 244, 255)  # the waves' light crests ...
FOAM = (250, 254, 255)   # ... and the foam where the water meets land


def columns(level: Level) -> list[int]:
    """The map's water columns."""
    return [col for col, row in enumerate(level.surface) if row < ROWS and level.grid[row][col] == WATER]


def _shade(top, deep, t: float):
    return tuple(round(a + (b - a) * t) for a, b in zip(top, deep))


def render(level: Level, surface: pygame.Surface) -> None:
    """The water on the map's tiles: a gradient from the surface's colour
    down to the deep, with a light line along the top and ripples."""
    top_c, deep_c = level.theme.water
    rng = random.Random(level.seed * 17 + 3)
    h = surface.get_height()
    depth = pygame.Surface((TILE, h))  # one column of water, from the surface down
    for y in range(h):
        depth.fill(_shade(top_c, deep_c, min(1.0, y / 110)), (0, y, TILE, 1))
    depth.fill(_shade(top_c, CREST, 0.5), (0, 0, TILE, 2))
    for col in columns(level):
        x, top = col * TILE, level.surface[col] * TILE
        surface.blit(depth, (x, top))
        for _ in range(3):  # ripples: short light dashes under the surface
            y = top + rng.randint(14, 90)
            if y < h:
                surface.fill(_shade(_shade(top_c, deep_c, min(1.0, (y - top) / 110)), CREST, 0.35),
                             (x + rng.randint(0, TILE - 6), y, rng.randint(3, 6), 1))


def draw_front(layer: pygame.Surface, level: Level, t: float, camera: int, view_w: int) -> None:
    """The water's front over the swimmers, in view: see-through water from
    the surface down FRONT px, its top line rippling, with foam at the shores."""
    top_c = level.theme.water[0]
    band = pygame.Surface((TILE, FRONT), pygame.SRCALPHA)
    band.fill((*top_c, FRONT_ALPHA))
    first, last = max(0, camera // TILE - 1), min(level.cols - 1, (camera + view_w) // TILE + 1)
    for col in range(first, last + 1):
        row = level.surface[col]
        if row >= ROWS or level.grid[row][col] != WATER:
            continue
        x0, top = col * TILE, row * TILE
        layer.blit(band, (x0, top))
        for x in range(x0, x0 + TILE):  # the waves: a crest line rising and falling
            wave = math.sin(x / 9 + t * 2.6) + 0.6 * math.sin(x / 4.3 - t * 3.7)
            y = top + round(wave)
            layer.fill(CREST if wave > 0.9 else _shade(top_c, CREST, 0.55), (x, y - 1, 1, 2))
        for side in (-1, 1):  # foam against the land next to it
            n = col + side
            if 0 <= n < level.cols and level.grid[min(ROWS - 1, level.surface[n])][n] != WATER:
                edge = x0 if side < 0 else x0 + TILE - 4
                for i in range(4):
                    if (i + int(t * 6)) % 3:
                        layer.fill(FOAM, (edge + i, top - 1 + (i + int(t * 4)) % 2, 1, 2))
