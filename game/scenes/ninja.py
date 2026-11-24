"""The Fuchsia Gym's hazard (`Route.puzzle` "ninja"): Koga's dojo, as in
Red/Blue, is full of walls nobody can see. They're solid tiles carved into
the map after it's drawn, so they don't show; bumping into one makes it
shimmer into view, and it stays faintly visible for the rest of the trip.
Most are low enough to jump (2 tiles), some need a full jump (3). Between
them, floor vents puff poison gas on a rhythm: walking into a puff poisons
a party member (one with no status that isn't a Poison type), which carries
on into the gym's waves (no healing in between), as Celadon's spores do.
"""

from __future__ import annotations

import math
import random

import pygame

from ..mechanics.status import STATUSES
from ..world.level import SOLID, TILE, Level
from ..world.player import HITBOX_H, HITBOX_HALF_W, Player

WALLS = 8              # along the walk
START = 10 * TILE      # the first one's spot from the entrance ...
ARENA_GAP = 8 * TILE   # ... and the last one's from the arena's band
HEIGHTS = (2, 2, 3)    # tiles: most can be jumped easily, some need a full jump
VENT_PERIOD = 3.2      # seconds between puffs
VENT_PUFF = 1.1        # seconds a puff lasts
GAS_HEIGHT = 58        # px a puff rises
RESETTLE = 1.4         # seconds a vent needs before it can poison again
SHIMMER = 1.2          # seconds a bumped wall shimmers brightly
TOAST_TIME = 2.6
WALL_COLOR = (170, 110, 230)
GAS_COLOR = (170, 80, 210)


class HiddenWall:
    def __init__(self, col: int, top: int, bottom: int, width: int):
        self.col, self.top, self.bottom, self.width = col, top, bottom, width  # tile rows: top .. bottom - 1
        self.rect = pygame.Rect(col * TILE, top * TILE, width * TILE, (bottom - top) * TILE)
        self.found = False
        self.shimmer = 0.0


class Vent:
    def __init__(self, x: float, ground: float, phase: float):
        self.x, self.ground, self.phase = x, ground, phase
        self.rest = 0.0

    def puffing(self, t: float) -> float:
        """How far into a puff (0..1), or -1 between puffs."""
        into = (t + self.phase) % VENT_PERIOD
        return into / VENT_PUFF if into < VENT_PUFF else -1.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 9, round(self.ground) - GAS_HEIGHT, 18, GAS_HEIGHT)


class NinjaDojo:
    def __init__(self, level: Level, rng: random.Random):
        boss_x = level.boss.x if level.boss else level.width - 8 * TILE
        first, last = START // TILE, int((boss_x - ARENA_GAP) // TILE)
        self.walls: list[HiddenWall] = []
        self.vents: list[Vent] = []
        step = (last - first) / WALLS
        for i in range(WALLS):
            col = round(first + step * (i + 0.5) + rng.uniform(-step / 5, step / 5))
            height = rng.choice(HEIGHTS)
            width = 2 if height == 2 and rng.random() < 0.4 else 1
            ground = level.surface[col]
            wall = HiddenWall(col, ground - height, ground, width)
            for row in range(wall.top, wall.bottom):  # (solid, but drawn after the tiles: unseen)
                for c in range(col, col + width):
                    level.grid[row][c] = SOLID
            self.walls.append(wall)
            if i % 2 == 0:  # a vent in the gap before every other wall
                x = (col - max(2, round(step / 2))) * TILE + TILE / 2
                self.vents.append(Vent(x, level.ground_y(x), rng.uniform(0, VENT_PERIOD)))
        self.toast, self.toast_t = "", 0.0
        self.bumped = False  # (the first bump explains what's going on)

    def update(self, dt: float, t: float, player: Player, party, rng: random.Random) -> None:
        self.toast_t = max(0.0, self.toast_t - dt)
        reach = pygame.Rect(round(player.x) - HITBOX_HALF_W - 2, round(player.feet_y) - HITBOX_H - 2,
                            2 * HITBOX_HALF_W + 4, HITBOX_H + 4)
        for wall in self.walls:
            wall.shimmer = max(0.0, wall.shimmer - dt)
            if reach.colliderect(wall.rect):
                if not wall.found:
                    wall.shimmer = SHIMMER
                    if not self.bumped:
                        self._say("Thud! An invisible wall! Koga's dojo is full of them.")
                        self.bumped = True
                wall.found = True
        body = player.body_rect
        for vent in self.vents:
            vent.rest = max(0.0, vent.rest - dt)
            if vent.rest or vent.puffing(t) < 0 or not vent.rect().colliderect(body):
                continue
            vent.rest = RESETTLE
            poison = STATUSES["poison"]
            open_ = [m for m in party if m.alive and not m.status and poison.immune not in m.species.types]
            if not open_:
                self._say("A puff of poison gas! Your team shrugs it off.")
                continue
            victim = rng.choice(open_)
            victim.inflict("poison")
            self._say(f"{victim.name} breathed in the poison gas! " + poison.inflicted.format(victim.name))

    def _say(self, text: str) -> None:
        self.toast, self.toast_t = text, TOAST_TIME

    def draw(self, layer: pygame.Surface, t: float) -> None:
        for wall in self.walls:
            r = wall.rect
            if wall.found:  # a faint pane, brighter while it shimmers
                glow = min(1.0, wall.shimmer / SHIMMER)
                pane = pygame.Surface(r.size, pygame.SRCALPHA)
                pane.fill((*WALL_COLOR, 40 + int(90 * glow)))
                pygame.draw.rect(pane, (*WALL_COLOR, 110 + int(120 * glow)), pane.get_rect(), 1)
                for y in range(0, r.h, 6):  # a ripple running up it
                    a = int(40 + 40 * math.sin(t * 4 + y * 0.4))
                    pygame.draw.line(pane, (230, 200, 255, a), (1, y), (r.w - 2, y))
                layer.blit(pane, r.topleft)
            elif (t + wall.col * 0.37) % 5 < 0.25:  # an unseen one: now and then the faintest ripple (a hint)
                pane = pygame.Surface(r.size, pygame.SRCALPHA)
                pane.fill((*WALL_COLOR, 18))
                layer.blit(pane, r.topleft)
        for vent in self.vents:
            x, ground = round(vent.x), round(vent.ground)
            pygame.draw.rect(layer, (40, 26, 40), (x - 9, ground - 3, 18, 3))  # the grate
            for i in range(-7, 8, 4):
                pygame.draw.line(layer, (90, 60, 90), (x + i, ground - 3), (x + i, ground - 1))
            into = vent.puffing(t)
            if into < 0:
                if (t + vent.phase) % VENT_PERIOD > VENT_PERIOD - 0.5:  # a hiss just before a puff
                    pygame.draw.circle(layer, (*GAS_COLOR, 90), (x, ground - 4), 4)
                continue
            gas = pygame.Surface((40, GAS_HEIGHT + 10), pygame.SRCALPHA)
            for k in range(9):  # puffs rising and swelling
                rise = (into + k / 9) % 1.0
                y = GAS_HEIGHT + 4 - rise * GAS_HEIGHT
                rad = 5 + rise * 9
                wobble = math.sin(t * 5 + k) * 3
                pygame.draw.circle(gas, (*GAS_COLOR, int(150 * (1 - rise * 0.6))), (20 + wobble, y), rad)
            layer.blit(gas, (x - 20, ground - GAS_HEIGHT - 6))
