"""The Saffron Gym's hazard (`Route.puzzle` "psychic"): Sabrina's hall of
warp pads, as in Red/Blue. Psychic barriers (solid, floor to ceiling) cut
the walk to the arena into sections; the only way past one is a warp pad.
Each section has a few pads: one sends the player on to the next section,
the others back to an earlier one, or across the same one. Which is which
is new every trip (`Instance.seed`). A pad that's been used shows where it
went (an arrow: on, back, or the same section), so the way is learned as
it's walked.

Stepping onto a pad (standing on it) warps the player; arriving on a pad
doesn't send them on again until they've stepped off it.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from ..world.level import SOLID, TILE, Level

SECTIONS = 5           # sections of the walk (barriers between them: one fewer)
PADS = 3               # pads per section (the first: 2, the last: none, it's the arena's)
START = 8 * TILE       # the first barrier's distance from the entrance at least ...
ARENA_GAP = 9 * TILE   # ... and the last one's from the arena's band
PAD_HALF = 11          # px: standing within this of a pad's middle is standing on it
COLUMN_H = 30          # px: the light rising off a pad
WARP_TIME = 0.45       # seconds of the warp's flash
TOAST_TIME = 2.6
PAD_COLOR = (240, 120, 220)
BARRIER_COLOR = (200, 120, 255)


@dataclass
class Pad:
    x: float
    ground: float
    section: int
    to: "Pad | None" = None
    used: bool = False

    @property
    def kind(self) -> str:
        """Where it leads: "on" (the next section), "back" or "same"."""
        if self.to.section > self.section:
            return "on"
        return "back" if self.to.section < self.section else "same"


class PsychicHall:
    def __init__(self, level: Level, rng: random.Random):
        boss_x = level.boss.x if level.boss else level.width - 8 * TILE
        first, last = START, boss_x - ARENA_GAP
        span = (last - first) / (SECTIONS - 1)
        # Barriers between the sections: full-height solid columns.
        self.barriers: list[int] = []
        for i in range(SECTIONS - 1):
            col = round((first + span * i) / TILE)
            for row in range(len(level.grid)):
                level.grid[row][col] = SOLID
            self.barriers.append(col)
        edges = [0] + [c * TILE for c in self.barriers] + [level.width]
        # Pads, spread out in each section but the last (the arena's).
        self.pads: list[Pad] = []
        by_section: list[list[Pad]] = []
        for s in range(SECTIONS - 1):
            n = 2 if s == 0 else PADS
            lo, hi = edges[s] + 3 * TILE, edges[s + 1] - 2 * TILE
            here = []
            for k in range(n):
                x = (round((lo + (hi - lo) * (k + 0.5) / n) / TILE) + 0.5) * TILE
                here.append(Pad(x, level.ground_y(x), s))
            by_section.append(here)
            self.pads += here
        # Arrival pads in each section after the first: where pads from elsewhere land (one per section is
        # the way on's landing spot; the arena's is a plain spot by its barrier).
        landings = [None] + [sec[0] for sec in by_section[1:]]
        arena_x = edges[-2] + 3 * TILE
        arena = Pad(arena_x, level.ground_y(arena_x), SECTIONS - 1)
        landings.append(arena)
        self.arena = arena
        for s, sec in enumerate(by_section):
            pads = sec[:]
            rng.shuffle(pads)
            # One pad leads on (never the landing pad itself, so arriving
            # doesn't hand the way on over for free) ...
            onward = next((p for p in pads if p is not landings[s]), pads[0])
            onward.to = landings[s + 1]
            for p in pads:
                if p is onward:
                    continue
                # ... the others back (an earlier section's landing, or the start) or across.
                choices = [landings[t] or by_section[0][0] for t in range(max(0, s - 2), s)] or [None]
                if rng.random() < 0.3 or choices == [None]:
                    others = [q for q in sec if q is not p]
                    p.to = rng.choice(others)
                else:
                    p.to = rng.choice(choices)
        self.standing_on: Pad | None = None  # (arrived on it: no warp until stepped off)
        self.warp_t = 0.0
        self.toast, self.toast_t = "", 0.0
        self.told = False

    def update(self, dt: float, player) -> float | None:
        """The x to warp the player to, if they just stepped onto a pad."""
        self.warp_t = max(0.0, self.warp_t - dt)
        self.toast_t = max(0.0, self.toast_t - dt)
        on = next((p for p in self.pads if abs(player.x - p.x) <= PAD_HALF and abs(player.feet_y - p.ground) < 4),
                  None)
        if on is not self.standing_on:
            self.standing_on = None if on is None else self.standing_on
        if on and self.standing_on is None and player.on_ground:
            on.used = True
            dest = on.to
            self.standing_on = dest if dest in self.pads else None
            self.warp_t = WARP_TIME
            if not self.told:
                self._say("Whoosh! A warp pad! Barriers bar the way: only the right pads lead on.")
                self.told = True
            elif dest is self.arena:
                self._say("The last barrier is behind you. Sabrina's arena lies ahead!")
            elif on.kind == "back":
                self._say("Warped back! That pad leads the wrong way.")
            return dest.x
        return None

    def _say(self, text: str) -> None:
        self.toast, self.toast_t = text, TOAST_TIME

    def draw(self, layer: pygame.Surface, t: float, level: Level) -> None:
        h = layer.get_height()
        for col in self.barriers:  # a shimmering curtain, floor to ceiling
            x = col * TILE
            pane = pygame.Surface((TILE, h), pygame.SRCALPHA)
            pane.fill((*BARRIER_COLOR, 70))
            for y in range(0, h, 5):
                a = int(70 + 60 * math.sin(t * 5 + y * 0.15))
                pygame.draw.line(pane, (255, 200, 255, a), (2, y), (TILE - 3, y))
            pygame.draw.line(pane, (255, 220, 255, 200), (0, 0), (0, h))
            pygame.draw.line(pane, (255, 220, 255, 200), (TILE - 1, 0), (TILE - 1, h))
            layer.blit(pane, (x, 0))
        for p in self.pads:
            x, y = round(p.x), round(p.ground)
            glow = 0.6 + 0.4 * math.sin(t * 4 + p.x * 0.05)
            column = pygame.Surface((2 * PAD_HALF, COLUMN_H), pygame.SRCALPHA)  # a faint pillar of light
            for row in range(COLUMN_H):
                a = round(70 * glow * (row / COLUMN_H) ** 2)
                pygame.draw.line(column, (*PAD_COLOR, a), (2, row), (2 * PAD_HALF - 3, row))
            layer.blit(column, (x - PAD_HALF, y - COLUMN_H))
            for k in range(3):  # motes rising off it
                my = y - ((t * 22 + k * 9 + p.x) % COLUMN_H)
                mx = x + math.sin(t * 3 + k * 2 + p.x) * (PAD_HALF - 4)
                pygame.draw.rect(layer, (255, 210, 250), (round(mx), round(my), 2, 2))
            rect = pygame.Rect(0, 0, 2 * PAD_HALF + 6, 8)
            rect.midbottom = (x, y + 2)
            pygame.draw.ellipse(layer, (60, 30, 70), rect)
            inner = rect.inflate(-4, -3)
            pygame.draw.ellipse(layer, tuple(round(c * glow) for c in PAD_COLOR), inner)
            pygame.draw.ellipse(layer, (255, 230, 255), inner, 1)
            if p.used:  # where it went: an arrow above it
                color = {"on": (140, 255, 150), "back": (255, 130, 120), "same": (255, 230, 120)}[p.kind]
                ay = y - COLUMN_H - 4
                if p.kind == "same":
                    pygame.draw.circle(layer, color, (x, ay), 3, 1)
                else:
                    d = 1 if p.kind == "on" else -1
                    pygame.draw.polygon(layer, color, [(x + 4 * d, ay), (x - 3 * d, ay - 4), (x - 3 * d, ay + 4)])
        if self.warp_t:  # the warp's flash: rings
            k = self.warp_t / WARP_TIME
            surf = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
            surf.fill((255, 180, 255, round(90 * k)))
            layer.blit(surf, (0, 0))
