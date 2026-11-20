"""The Rocket Hideout's spinner floors in play (`world/spinners.py` has
the layouts and the rules): the pads under the player carry them along or
launch them up, and are drawn on the floor and the catwalk."""

from __future__ import annotations

import math

import pygame

from ..world.level import TILE, Level
from ..world.player import Controls, Player
from ..world.spinners import START_COL, Layout, catwalk_row, floor_row

SLIDE_SPEED = 210    # px/s along the arrows
LAUNCH_SPEED = 500   # px/s up off a launch pad (rises about 110 px: past the catwalk, 80 px up)
MAX_TURNS = 8        # arrows that may turn one slide around, before it stops (no endless ping-pong)

ARROW = (250, 200, 60)
STOP = (230, 60, 60)
LAUNCH = (110, 220, 120)
PLATE = (34, 34, 42)
PLATE_EDGE = (16, 16, 20)


class SpinnerFloor:
    def __init__(self, level: Level, layout: Layout):
        self.level, self.layout = level, layout
        self.floor_y = floor_row(level) * TILE
        self.catwalk_y = catwalk_row(level) * TILE
        self.slide = 0            # -1 / 1 while carried along, else 0
        self.turns = 0
        self.launching = False    # rising off a launch pad: no steering until it lands
        self.launched_from: tuple | None = None  # (a pad doesn't fire again on landing back on it)
        self.cell: tuple | None = None  # (on catwalk?, column in the layout) the player stands on
        self.airborne = False
        self.last_x = 0.0

    # ----------------------------------------------------------------- rules

    def pad(self, cell: tuple[int, int]) -> str:
        up, i = cell
        return (self.layout.catwalk if up else self.layout.floor)[i]

    def _cell_at(self, player: Player) -> tuple[int, int] | None:
        """(1 on the catwalk / 0 on the floor, column in the layout) under the
        player's feet, if they stand in the puzzle."""
        i = int(player.x // TILE) - START_COL
        if not 0 <= i < self.layout.cols:
            return None
        if abs(player.feet_y - self.catwalk_y) < 1 and self.layout.catwalk[i] != " ":
            return 1, i
        if abs(player.feet_y - self.floor_y) < 1:
            return 0, i
        return None

    def steer(self, c: Controls) -> Controls:
        if self.launching:  # straight up (holding "jump" for the full rise)
            return Controls(jump_held=True)
        if self.slide:
            return Controls(left=self.slide < 0, right=self.slide > 0, carried=SLIDE_SPEED)
        return c

    def update(self, player: Player) -> None:
        if player.state == "air":
            self.airborne = True
            return
        landed, self.airborne = self.airborne, False
        if self.launching:
            self.launching = False
        cell = self._cell_at(player)
        if cell is None:  # off the puzzle
            self.slide, self.cell = 0, None
            self.last_x = player.x
            return
        if self.slide and not landed and abs(player.x - self.last_x) < 0.01:
            self.slide = 0  # against a wall
        if cell != self.cell or landed:
            self.cell = cell
            self._enter(player, cell, landed)
        self.last_x = player.x

    def _enter(self, player: Player, cell: tuple[int, int], landed: bool) -> None:
        pad = self.pad(cell)
        if pad in "<>":
            way = 1 if pad == ">" else -1
            if self.slide and way != self.slide:
                self.turns += 1
            elif not self.slide:
                self.turns = 0
            self.slide = 0 if self.turns > MAX_TURNS else way
        elif pad == "o":
            self.slide = 0
        elif pad == "^" and not cell[0]:
            if landed and cell == self.launched_from:
                return  # (back down on the pad it went up from)
            self.slide = 0
            self.launching, self.launched_from = True, cell
            player.x = (START_COL + cell[1]) * TILE + TILE / 2
            player.vy = -LAUNCH_SPEED
            player.set_state("air")
            self.airborne = True
        if pad not in "^":
            self.launched_from = None

    # ------------------------------------------------------------------ draw

    def draw(self, surface: pygame.Surface, t: float) -> None:
        for up, row, y in ((0, self.layout.floor, self.floor_y), (1, self.layout.catwalk, self.catwalk_y)):
            for i, pad in enumerate(row):
                if pad in "<>o^":
                    _draw_pad(surface, pad, (START_COL + i) * TILE, y, t, i)


def _draw_pad(surface: pygame.Surface, pad: str, x: int, y: float, t: float, i: int) -> None:
    """A pad set into the surface at (x, y): a dark plate with its sign
    standing up from it."""
    top = round(y) - 2
    plate = pygame.Rect(x + 1, top, TILE - 2, 6)
    pygame.draw.rect(surface, PLATE, plate)
    pygame.draw.rect(surface, PLATE_EDGE, plate, 1)
    cx = x + TILE // 2
    if pad in "<>":
        d = 1 if pad == ">" else -1
        # A chevron, glowing in a wave that runs the arrows' way.
        glow = 0.6 + 0.4 * math.sin(t * 8 - i * d * 1.2)
        color = [round(c * glow) for c in ARROW]
        tip = cx + 3 * d
        pygame.draw.lines(surface, color, False, [(tip - 5 * d, top - 4), (tip, top + 1), (tip - 5 * d, top + 6)], 3)
    elif pad == "o":
        pygame.draw.circle(surface, STOP, (cx, top + 2), 4)
        pygame.draw.circle(surface, (255, 150, 140), (cx - 1, top + 1), 1)
    else:  # a launch pad: an up-arrow that bobs
        lift = round(abs(math.sin(t * 4)) * 3)
        for dy in (0, 5):
            pygame.draw.lines(surface, LAUNCH, False, [(cx - 5, top + 3 - lift - dy), (cx, top - 2 - lift - dy),
                                                       (cx + 5, top + 3 - lift - dy)], 2)
