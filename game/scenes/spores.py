"""The Celadon Gym's hazard (`Route.puzzle` "spores"): a greenhouse where
clouds of Sleep Powder, Poison Powder and Stun Spore drift over the walk up
to the arena. Some sweep to and fro along the floor, some rise and sink.
Walking into one gives a party member that status (one who has none and
isn't immune), and it carries on into the gym's waves, which come with no
healing in between. Each cloud then settles for a moment before it can
strike again. Jump over the low ones, slip under the high ones, or wait for
a gap.

The Power Plant's sparks (`Route.puzzle` "sparks", the Thunder Stone's
quest) work the same way: crackling balls of loose current that paralyse
(`SPARKS`).
"""

from __future__ import annotations

import math
import random

import pygame

from ..mechanics.status import STATUSES
from ..world.level import TILE, Level

CLOUDS = 8             # along the walk
START = 12 * TILE      # the first one's spot from the entrance ...
ARENA_GAP = 9 * TILE   # ... and the last one's from the arena's band
RADIUS = (18, 13)      # its body (an ellipse's half-width, half-height)
RESETTLE = 1.4         # seconds a cloud needs before it can strike again
LOW, HIGH = 14, 78     # its middle's height over the floor: low and high
SWEEP = 44             # how far a sweeping cloud drifts either way
TOAST_TIME = 2.6
# The three powders: (status, name, colour).
POWDERS = (("sleep", "Sleep Powder", (120, 180, 250)), ("poison", "Poison Powder", (180, 80, 210)),
           ("paralysis", "Stun Spore", (240, 200, 50)))
SPARKS = (("paralysis", "loose current", (255, 236, 90)),)


class Cloud:
    def __init__(self, x: float, ground: float, kind: str, powder: tuple, rng: random.Random, spark: bool = False):
        self.x0, self.ground, self.kind = x, ground, kind  # kind: "sweep" or "rise"
        self.status, self.name, self.color = powder
        self.spark = spark
        self.period = rng.uniform(3.2, 4.6)
        self.phase = rng.uniform(0, math.tau)
        self.rest = 0.0  # > 0 while settling after a hit
        self.motes = [(rng.uniform(0, math.tau), rng.uniform(8, 22), rng.uniform(0.8, 1.6)) for _ in range(14)]

    def pos(self, t: float) -> tuple[float, float]:
        wave = math.sin(t * math.tau / self.period + self.phase)
        if self.kind == "sweep":
            return self.x0 + SWEEP * wave, self.ground - LOW
        return self.x0, self.ground - (LOW + HIGH) / 2 - (HIGH - LOW) / 2 * wave

    def touches(self, t: float, body: pygame.Rect) -> bool:
        x, y = self.pos(t)
        # (the nearest point of the body to the middle, inside the ellipse)
        nx, ny = min(max(x, body.left), body.right), min(max(y, body.top), body.bottom)
        return ((nx - x) / RADIUS[0]) ** 2 + ((ny - y) / RADIUS[1]) ** 2 <= 1

    def draw(self, layer: pygame.Surface, t: float) -> None:
        if self.spark:
            self._draw_spark(layer, t)
            return
        x, y = self.pos(t)
        faded = 0.4 if self.rest > 0 else 1.0
        puff = pygame.Surface((56, 44), pygame.SRCALPHA)
        r, g, b = self.color
        dark = (r * 3 // 5, g * 3 // 5, b * 3 // 5)
        light = (min(255, r + 70), min(255, g + 70), min(255, b + 70))
        blobs = ((-10, 3, 11), (10, 3, 11), (0, -4, 13), (-4, 4, 11), (5, 0, 10))
        for dx, dy, rad in blobs:  # a dark rim, the body, then lit tops
            wobble = math.sin(t * 2.3 + dx) * 1.2
            pygame.draw.circle(puff, (*dark, int(200 * faded)), (28 + dx, 22 + dy + wobble), rad + 1)
        for dx, dy, rad in blobs:
            wobble = math.sin(t * 2.3 + dx) * 1.2
            pygame.draw.circle(puff, (r, g, b, int(210 * faded)), (28 + dx, 22 + dy + wobble), rad)
        for dx, dy, rad in blobs[2:]:
            wobble = math.sin(t * 2.3 + dx) * 1.2
            pygame.draw.circle(puff, (*light, int(170 * faded)), (28 + dx - 2, 22 + dy + wobble - 3), rad // 2)
        layer.blit(puff, (round(x - 28), round(y - 22)))
        for angle, dist, speed in self.motes:  # glittering spores swirling in it
            a = angle + t * speed
            mx, my = x + math.cos(a) * dist, y + math.sin(a) * dist * 0.6
            layer.set_at((round(mx), round(my)), (255, 255, 255) if faded == 1 else (r, g, b))


    def _draw_spark(self, layer: pygame.Surface, t: float) -> None:
        """A crackling ball of current: a glow, a bright core and jagged arcs."""
        x, y = self.pos(t)
        faded = 0.35 if self.rest > 0 else 1.0
        glow = pygame.Surface((56, 44), pygame.SRCALPHA)
        for rad, a in ((22, 70), (17, 110), (11, 170)):
            pygame.draw.ellipse(glow, (255, 220, 60, int(a * faded)), (28 - rad, 22 - rad * 0.75, rad * 2, rad * 1.5))
        pygame.draw.circle(glow, (255, 255, 235, int(240 * faded)), (28, 22), 6)
        layer.blit(glow, (round(x - 28), round(y - 22)))
        rng = random.Random(int(t * 14) * 31 + int(self.x0))  # (the arcs flicker, a new shape 14 times a second)
        for _ in range(6 if faded == 1 else 1):
            angle, px, py = rng.uniform(0, math.tau), x, y
            points = [(px, py)]
            for step in range(5):
                angle += rng.uniform(-0.9, 0.9)
                px, py = px + math.cos(angle) * 5, py + math.sin(angle) * 4
                points.append((px, py))
            pygame.draw.lines(layer, (255, 255, 200), False, points)


class SporeGarden:
    def __init__(self, level: Level, rng: random.Random, sparks: bool = False, count: int = CLOUDS):
        """`sparks`: the Power Plant's loose current instead of spores."""
        boss_x = level.boss.x if level.boss else level.width - 8 * TILE
        first, last = START, boss_x - ARENA_GAP
        kinds = SPARKS if sparks else POWDERS
        self.clouds = []
        for i in range(count):
            x = first + (last - first) * i / (count - 1)
            self.clouds.append(Cloud(x, level.ground_y(x), "rise" if i % 2 else "sweep", kinds[i % len(kinds)], rng,
                                     spark=sparks))
        self.toast, self.toast_t = "", 0.0
        self.flash = 0.0  # the player blinks after a hit

    def update(self, dt: float, t: float, body: pygame.Rect, party, rng: random.Random) -> None:
        """Clouds the player walks into breathe their powder on the party."""
        self.toast_t = max(0.0, self.toast_t - dt)
        self.flash = max(0.0, self.flash - dt)
        for cloud in self.clouds:
            cloud.rest = max(0.0, cloud.rest - dt)
            if cloud.rest or not cloud.touches(t, body):
                continue
            cloud.rest = RESETTLE
            self.flash = 0.6
            status = STATUSES[cloud.status]
            open_ = [m for m in party if m.alive and not m.status and status.immune not in m.species.types]
            if not open_:
                self._say(f"A crackle of {cloud.name}! Your team shrugs it off." if cloud.spark
                          else f"A cloud of {cloud.name}! Your team shrugs it off.")
                continue
            victim = rng.choice(open_)
            victim.inflict(cloud.status)
            verb = "was zapped by" if cloud.spark else "breathed in"
            self._say(f"{victim.name} {verb} the {cloud.name}! " + status.inflicted.format(victim.name))

    def _say(self, text: str) -> None:
        self.toast, self.toast_t = text, TOAST_TIME

    def draw(self, layer: pygame.Surface, t: float) -> None:
        for cloud in self.clouds:
            cloud.draw(layer, t)
