"""Strength's boulders (HM04 Strength, from the Safari Zone Warden): big
boulders in dungeon rooms (`Room.boulders`), sitting over a ladder to a
bonus room. A boulder is `WIDTH` × `HEIGHT` tiles of solid rock, too tall
to jump. With Strength in the bag, walking into one and keeping on
pushing (`PUSH_TIME`) slides it a tile along the ground; it won't climb a
step or squeeze under a ledge. Without it, it won't budge. Where each one
has been pushed is kept in the room's state for the trip (so coming back
up the ladder never lands inside one).
"""

from __future__ import annotations

import math
import random

import pygame

from ..world.level import EMPTY, SOLID, TILE, Level

WIDTH, HEIGHT = 4, 4   # tiles (a jump reaches just under 4 tiles)
PUSH_TIME = 0.35       # seconds of pushing per tile
SLIDE_TIME = 0.22      # seconds a slide takes (drawn; the rock is already there)
TOAST_TIME = 2.6
STRENGTH = "HM04 Strength"


def _sprite(seed: int) -> pygame.Surface:
    """A big round boulder: shaded rock, cracks, a highlight."""
    w, h = WIDTH * TILE, HEIGHT * TILE
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = random.Random(seed)
    body = pygame.Rect(1, 3, w - 2, h - 3)
    pts = []
    for i in range(14):  # a lumpy outline
        a = i / 14 * math.tau
        r = 1 - rng.uniform(0, 0.07)
        pts.append((body.centerx + math.cos(a) * body.w / 2 * r, body.centery + math.sin(a) * body.h / 2 * r))
    pts = [(x, min(y, h - 1)) for x, y in pts]
    pygame.draw.polygon(s, (118, 106, 94), pts)
    mask = pygame.mask.from_surface(s)  # (the rock's outline: the shading stays inside it)
    shade = pygame.Surface((w, h), pygame.SRCALPHA)  # darker underside, lighter top-left
    for y in range(h):
        k = y / h
        pygame.draw.line(shade, (30, 24, 20, round(110 * k ** 1.5)), (0, y), (w, y))
    pygame.draw.ellipse(shade, (255, 245, 225, 55), (6, 8, w * 0.55, h * 0.45))
    s.blit(shade, (0, 0))
    s = mask.to_surface(setsurface=s, unsetcolor=(0, 0, 0, 0))
    for _ in range(4):  # cracks
        x, y = rng.uniform(8, w - 8), rng.uniform(10, h - 12)
        crack = [(x, y)]
        for _ in range(3):
            x += rng.uniform(-6, 6)
            y += rng.uniform(2, 6)
            crack.append((x, y))
        pygame.draw.lines(s, (70, 60, 52), False, crack, 1)
    for _ in range(10):  # speckles
        pygame.draw.circle(s, (150, 138, 124), (rng.uniform(6, w - 6), rng.uniform(8, h - 6)), 1)
    pygame.draw.polygon(s, (52, 44, 38), pts, 2)
    return s


class Boulder:
    def __init__(self, col: int, ground_row: int, seed: int):
        self.col, self.ground_row = col, ground_row  # left column; the row its base stands on
        self.image = _sprite(seed)
        self.slide = 0.0      # seconds left of the slide being drawn
        self.slide_from = 0   # columns it slid (drawn offset fades from this)
        self.push = 0.0

    @property
    def rows(self) -> range:
        return range(self.ground_row - HEIGHT, self.ground_row)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.col * TILE, (self.ground_row - HEIGHT) * TILE, WIDTH * TILE, HEIGHT * TILE)


def _spot(level: Level, ladder: int) -> int:
    """Where a boulder covering the ladder at column `ladder` goes: on its
    ground, with 2 flat tiles to stand on and push from on one side and
    room to slide it clear of the ladder on the other (the most room
    first)."""
    ground = level.surface[ladder]

    def flat(c0: int, c1: int) -> bool:
        return all(0 <= c < level.cols and level.surface[c] == ground for c in range(c0, c1))

    best, best_room = ladder - WIDTH // 2, -1
    for col in range(ladder - WIDTH + 1, ladder + 1):
        if not flat(col, col + WIDTH):
            continue
        for push in (1, -1):  # pushed right (stand on its left), or left
            need = (ladder - col + 2) if push > 0 else (col + WIDTH - 1 - ladder + 2)
            stand = flat(col - 2, col) if push > 0 else flat(col + WIDTH, col + WIDTH + 2)
            slide = flat(col + WIDTH, col + WIDTH + need) if push > 0 else flat(col - need, col)
            if stand and slide and need > best_room:
                best, best_room = col, need
    return best


class BoulderField:
    """The boulders of a room. `xs`: the x each starts centred on."""

    def __init__(self, level: Level, xs: list[float], seed: int):
        self.level = level
        self.boulders: list[Boulder] = []
        for i, x in enumerate(xs):
            col = _spot(level, int(x // TILE))
            b = Boulder(col, level.surface[int(x // TILE)], seed * 31 + i)
            self.boulders.append(b)
            self._carve(b, SOLID)
        self.toast, self.toast_t = "", 0.0
        self.told = False

    def _carve(self, b: Boulder, tile: str) -> None:
        for row in b.rows:
            for col in range(b.col, b.col + WIDTH):
                self.level.grid[row][col] = tile

    def _can_move(self, b: Boulder, step: int) -> bool:
        """Whether the column it moves into is free, on the same ground."""
        col = b.col + WIDTH if step > 0 else b.col - 1
        if not 1 <= col < self.level.cols - 1:
            return False
        if self.level.surface[col] != b.ground_row:
            return False
        return all(self.level.grid[row][col] == EMPTY for row in b.rows)

    def move(self, b: Boulder, step: int) -> None:
        self._carve(b, EMPTY)
        b.col += step
        self._carve(b, SOLID)

    def place(self, cols: list[int]) -> None:
        """Back where they were pushed to (a room's saved state)."""
        for b, col in zip(self.boulders, cols):
            self._carve(b, EMPTY)
            b.col = col
            self._carve(b, SOLID)

    @property
    def cols(self) -> list[int]:
        return [b.col for b in self.boulders]

    def update(self, dt: float, player, pressing: int, has_strength: bool, lead: str) -> None:
        """`pressing`: the direction held (-1, 0, 1)."""
        self.toast_t = max(0.0, self.toast_t - dt)
        left, right = player.x - 11, player.x + 11
        for b in self.boulders:
            b.slide = max(0.0, b.slide - dt)
            r = b.rect
            beside = r.top < player.feet_y <= r.bottom + 1
            touching = (pressing > 0 and abs(right - r.left) < 2.5) or (pressing < 0 and abs(left - r.right) < 2.5)
            if not (beside and touching and player.on_ground):
                b.push = 0.0
                continue
            if not has_strength:
                if not self.told:
                    self._say("A huge boulder. It won't budge... (Strength could move it.)")
                    self.told = True
                continue
            b.push += dt
            if b.push >= PUSH_TIME:
                b.push = 0.0
                if self._can_move(b, pressing):
                    self.move(b, pressing)
                    b.slide, b.slide_from = SLIDE_TIME, -pressing
                    if not self.told:
                        self._say(f"{lead} used Strength! It can move boulders.")
                        self.told = True
                else:
                    self._say("The boulder won't go any further this way.")

    def _say(self, text: str) -> None:
        self.toast, self.toast_t = text, TOAST_TIME

    def draw(self, layer: pygame.Surface) -> None:
        for b in self.boulders:
            r = b.rect
            dx = round(b.slide_from * TILE * (b.slide / SLIDE_TIME)) if b.slide else 0
            shadow = pygame.Rect(0, 0, r.w - 4, 6)
            shadow.midbottom = (r.centerx + dx, r.bottom + 2)
            pygame.draw.ellipse(layer, (0, 0, 0, 90) if layer.get_flags() & pygame.SRCALPHA else (40, 34, 30), shadow)
            layer.blit(b.image, (r.x + dx, r.y + 2))
