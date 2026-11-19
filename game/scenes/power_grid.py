"""The Vermilion Gym's puzzle (`Route.puzzle` "trash_cans"), after Red/Blue's
trash cans, with a few twists.

An electric fence cuts the arena off. Two switches, hidden in the gym's
trash cans, turn it off. The first is in any can, and that can gives off a
faint spark now and then (a clue for the watchful). The second is always
in a can right next to the first. Rummage in the wrong neighbour and a
Voltorb that was hiding in the trash jumps out (a battle; the gym's waves
come with no healing in between, so it costs). Both switches then move.
Empty cans hold junk. Once the fence is off it stays off (`Game.trainers`
"puzzle:<route>").
"""

from __future__ import annotations

import math
import random

import pygame

from ..world import tileset
from ..world.level import TILE, Level

CANS = 8            # trash cans along the walk
FENCE_GAP = 7       # tiles between the fence and the arena's band
SPARK_EVERY = 2.6   # seconds between the first switch's can's sparks ...
SPARK_TIME = 0.3    # ... which last this long
AMBUSH = (("voltorb", 27),)  # what jumps out of the wrong can

JUNK = (
    "Just trash. A crumpled \"Lt. Surge: Lightning Never Strikes Twice\" poster.",
    "Nothing but trash. Someone threw away half a Rage Candy Bar.",
    "Only trash. Dog tags reading \"Pvt. Pikachu\".",
    "Trash. A burnt-out light bulb. Many, many burnt-out light bulbs.",
    "Nope, only trash. An instruction manual: \"So You've Been Paralyzed\".",
    "Just trash. A soggy sandwich. You close the lid quickly.",
    "Only trash... and a note: \"The switches are NOT in the trash cans. - Lt. Surge\"",
    "Trash. A broken Poké Doll, singed around the edges.",
)


class PowerGrid:
    """The cans (x positions), which hold the switches, and the fence."""

    def __init__(self, level: Level, rng: random.Random, solved: bool):
        self.level, self.rng = level, rng
        boss_x = level.boss.x if level.boss else level.width - 8 * TILE
        self.fence_x = boss_x - FENCE_GAP * TILE
        first, last = 7 * TILE, self.fence_x - 3 * TILE
        self.cans = [first + (last - first) * i / (CANS - 1) for i in range(CANS)]
        self.searched: set[int] = set()  # cans with their lid off (looked in since the switches last moved)
        self.open = solved
        self.found = 0  # switches found (0, 1; 2 = open)
        self._hide()

    def _hide(self) -> None:
        """Put the switches in new cans: the first anywhere, the second next to it."""
        self.first = self.rng.randrange(CANS)
        self.second = self.rng.choice([i for i in (self.first - 1, self.first + 1) if 0 <= i < CANS])
        self.found = 0
        self.searched.clear()

    def can_at(self, x: float) -> int | None:
        """The can the player at `x` stands at (while the fence is up)."""
        if self.open:
            return None
        return next((i for i, cx in enumerate(self.cans) if abs(x - cx) < 12), None)

    def search(self, i: int) -> tuple[list[str], bool]:
        """Rummage in can `i`: (what happens, in lines; whether a Voltorb jumps out)."""
        self.searched.add(i)
        if self.found == 0:
            if i == self.first:
                self.found = 1
                return (["There's a switch hidden under the trash! You flip it.",
                         "Click! The fence's first lock opens. The second switch must be close by..."], False)
            return [self.rng.choice(JUNK)], False
        if i == self.second:
            self.open, self.found = True, 2
            return (["Another switch! You flip it.", "Click! The second lock opens. With a dying fizz, the "
                     "electric fence shuts off!"], False)
        if i == self.first:
            return ["The first switch is still flipped. The second one must be in a can next to it..."], False
        self._hide()
        return (["The trash can wobbles... It's not trash! A Voltorb was hiding in it!",
                 "Zzzt! The fence's locks reset. The switches must have moved..."], True)

    SIGN = ("A warning sign on the fence: \"DANGER: 10,000 VOLTS. Two switches cut the power.\"",
            "Scrawled under it: \"Hid 'em where nobody'd ever look. Ha! - Lt. Surge\"")

    def at_fence(self, x: float) -> bool:
        """The player at `x` stands at the fence (while it's up): Up reads its sign."""
        return not self.open and self.fence_x - 40 < x < self.fence_x

    def blocks(self, x: float) -> float:
        """`x` held back from the fence while it's up."""
        return x if self.open else min(x, self.fence_x - 24)

    # ------------------------------------------------------------------ draw

    def draw(self, layer: pygame.Surface, t: float) -> None:
        for i, x in enumerate(self.cans):
            ground = round(self.level.ground_y(x))
            searched = i in self.searched and not self.open
            tileset.draw_prop(layer, "trash_can_open" if searched or self.open else "trash_can", round(x), ground)
            if not self.open and self.found == 0 and i == self.first and (t % SPARK_EVERY) < SPARK_TIME:
                self._spark(layer, round(x), ground - 22, t)
        self._draw_fence(layer, t)

    def _spark(self, layer: pygame.Surface, x: int, y: int, t: float) -> None:
        """A little crackle out of the first switch's can: two tiny bolts."""
        rng = random.Random(int(t * 20))
        for side in (-1, 1):
            x0 = x + side * rng.randint(2, 6)
            points = [(x0, y + 4), (x0 + side * 2, y + 1), (x0, y - 1), (x0 + side * 3, y - 4)]
            pygame.draw.lines(layer, (255, 236, 110), False, points, 1)
            layer.set_at(points[-1], (255, 255, 230))

    def _draw_fence(self, layer: pygame.Surface, t: float) -> None:
        x, ground = round(self.fence_x), round(self.level.ground_y(self.fence_x))
        top = ground - 5 * TILE
        half = 16  # the pylons stand this far either side of the fence's middle
        if not self.open:  # a blue haze between them
            haze = pygame.Surface((2 * half, ground - top), pygame.SRCALPHA)
            haze.fill((120, 160, 255, 40 + int(20 * math.sin(t * 9))))
            layer.blit(haze, (x - half, top))
        for px in (x - half, x + half):  # the pylons: posts striped in hazard yellow and black
            pygame.draw.rect(layer, (40, 40, 44), (px - 4, top, 9, ground - top))
            for y in range(top + 6, ground - 3, 10):
                pygame.draw.rect(layer, (230, 190, 40), (px - 3, y, 7, 5))
            pygame.draw.rect(layer, (150, 150, 160), (px - 5, top - 4, 11, 5))
            for k in range(4):  # insulators
                pygame.draw.rect(layer, (200, 200, 210), (px - 5, top + 12 + k * 18, 11, 2))
        box = pygame.Rect(x - half - 13, ground - 30, 10, 18)  # its lock box: a light per switch
        pygame.draw.rect(layer, (60, 62, 66), box)
        pygame.draw.rect(layer, (24, 24, 28), box, 1)
        for n in range(2):
            lit = self.open or self.found > n
            pygame.draw.circle(layer, (90, 230, 110) if lit else (240, 70, 60), (box.centerx, box.y + 5 + 8 * n), 2)
        if self.open:
            return
        rng = random.Random(int(t * 14))
        for strand in range(5):  # crackling arcs between the pylons
            y0 = top + 10 + strand * 15
            points = ([(x - half + 4, y0)] + [(x - half + 4 + 6 * k, y0 + rng.randint(-4, 4)) for k in range(1, 4)]
                      + [(x + half - 4, y0)])
            glow = 170 + int(60 * math.sin(t * 20 + strand))
            pygame.draw.lines(layer, (glow, glow, 255), False, points, 2)
            if rng.random() < 0.5:  # (a white-hot core, flickering)
                pygame.draw.lines(layer, (255, 255, 230), False, points, 1)
