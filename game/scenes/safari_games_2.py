"""More Safari Zone games (see safari_games.py, whose `MiniGame` frame they
use): keyboard and touch both work in each.

- Tauros, **Rodeo** (`Rodeo`): stay on a bucking Tauros. It tilts further
  and further unless you lean against it (Left/Right, or touch and hold
  either half of the screen); every moment you sit steady scores, and the
  steadier the more. Tilt too far and you're thrown: points lost, and a
  moment to climb back on.
- Pinsir, **Pinch!** (`Pinch`): logs roll past between Pinsir's horns:
  pinch (Space/Enter/Up, or a tap) as one is right between them. Dead
  centre is a Perfect; a big log is worth more; pinching a Geodude hurts,
  and so does snapping at nothing.
"""

from __future__ import annotations

import math

import pygame

from ..engine import touch, ui
from .safari_games import GAME_TIME, MiniGame, W, _icon

PINCH_KEYS = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z, pygame.K_UP)


# --- Tauros: Rodeo -------------------------------------------------------------

STEADY, WOBBLY = 0.15, 0.4   # |tilt| within these: +2 / +1 a second
THROWN_AT = 1.0              # |tilt| this far and you're off
REMOUNT = 1.2                # seconds back on the ground
LEAN = 3.2                   # tilt/s² your leaning pushes
TIP = 1.6                    # how strongly a tilt pulls itself further (it's unstable)
THROWN_COST = 4


class Rodeo(MiniGame):
    TITLE = "Rodeo"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tilt, self.spin = 0.0, 0.0  # tilt: -1 (left) .. 1 (right); spin: tilt/s
        self.next_buck = 0.8
        self.off = 0.0                   # seconds left on the ground after being thrown
        self.held = 0                    # touch: the side held (-1, 0, 1)
        self.held_t = 0.0
        self.tick = 0.0                  # scoring: a point every so often while steady
        self.tauros = _icon("tauros", 70)

    def pointer(self, pos, drag) -> None:
        self.held = -1 if pos[0] < W / 2 else 1
        self.held_t = 0.25  # (a tap leans for a moment; holding keeps it up)

    def _lean(self) -> int:
        keys = touch.pressed()
        lean = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        return lean or (self.held if self.held_t > 0 else 0)

    def play(self, dt: float) -> None:
        progress = 1 - self.time_left / GAME_TIME
        self.held_t = max(0.0, self.held_t - dt)
        if self.off:
            self.off = max(0.0, self.off - dt)
            return
        self.next_buck -= dt
        if self.next_buck <= 0:  # a buck: a kick to one side, harder as it goes
            self.next_buck = self.rng.uniform(0.5, 1.1) - 0.25 * progress
            self.spin += self.rng.choice((-1, 1)) * self.rng.uniform(0.7, 1.2) * (1 + 0.8 * progress)
        self.spin += (TIP * self.tilt - LEAN * self._lean()) * dt
        self.spin *= 1 - 0.8 * dt  # (some damping)
        self.tilt += self.spin * dt
        if abs(self.tilt) >= THROWN_AT:
            self.pop(W / 2, 200, -THROWN_COST)
            self.tilt, self.spin, self.off, self.tick = 0.0, 0.0, REMOUNT, 0.0
            return
        if abs(self.tilt) < WOBBLY:
            self.tick += dt * (2 if abs(self.tilt) < STEADY else 1)
            if self.tick >= 1:
                self.tick -= 1
                self.pop(W / 2 + self.rng.uniform(-30, 30), 150, 1)

    def draw_play(self, canvas: pygame.Surface) -> None:
        ground = 300
        buck = 0 if self.off else abs(math.sin(self.t * 9)) * 10  # (bouncing)
        angle = 0 if self.off else -self.tilt * 28
        bull = pygame.transform.rotate(self.tauros, angle)
        rect = bull.get_rect(midbottom=(W // 2, ground - round(buck)))
        canvas.blit(bull, rect)
        # You, on its back (just behind the hump), or sitting in the dust.
        if self.off:
            rx, ry, lean = W // 2 + 70, ground - 2, 0
        else:
            a = math.radians(-angle)
            back = (-12, 4 - bull_back(self.tauros))  # (from the bull's middle, unrotated)
            rx = W // 2 + back[0] * math.cos(a) - back[1] * math.sin(a)
            ry = rect.centery + back[0] * math.sin(a) + back[1] * math.cos(a)
            lean = self._lean()
        rx, ry = round(rx), round(ry)
        tilt = -self.tilt * 10 + lean * 5  # (the rider sways with the bull, and leans against it)
        hip, neck = (rx, ry), (round(rx + tilt), ry - 16)
        pygame.draw.line(canvas, (50, 60, 140), (rx - 5, ry), (rx - 9, ry + 9), 3)         # legs
        pygame.draw.line(canvas, (50, 60, 140), (rx + 5, ry), (rx + 9, ry + 9), 3)
        pygame.draw.line(canvas, (60, 80, 170), hip, neck, 6)                               # body
        pygame.draw.line(canvas, (240, 200, 160), neck, (neck[0] - 9 + lean * 4, neck[1] - 8), 2)  # arm up
        pygame.draw.circle(canvas, (240, 200, 160), (neck[0], neck[1] - 6), 6)              # head
        pygame.draw.rect(canvas, (200, 60, 50), (neck[0] - 7, neck[1] - 14, 14, 5))         # cap
        pygame.draw.rect(canvas, (200, 60, 50), (neck[0] + 3, neck[1] - 11, 7, 2))
        # The balance bar: the steady zone green, the wobbly one yellow.
        bar = pygame.Rect(W // 2 - 120, 322, 240, 10)
        pygame.draw.rect(canvas, (150, 50, 40), bar)
        pygame.draw.rect(canvas, (220, 190, 60), bar.inflate(-round(bar.w * (1 - WOBBLY)), 0))
        pygame.draw.rect(canvas, (80, 190, 80), bar.inflate(-round(bar.w * (1 - STEADY)), 0))
        pygame.draw.rect(canvas, (30, 30, 30), bar, 1)
        x = bar.centerx + round(self.tilt / THROWN_AT * bar.w / 2)
        pygame.draw.polygon(canvas, (255, 255, 255), [(x, bar.y - 1), (x - 4, bar.y - 7), (x + 4, bar.y - 7)])

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.off and not self.over:
            ui.text(window, "Thrown off! Climbing back on...", (W / 2, 120), (255, 120, 100), size=26,
                    align="center")
        elif self.t < 6 and not self.over:
            ui.text(window, "Lean against it: Left/Right, or hold a side", (W / 2, 100), ui.WHITE, size=22,
                    align="center")


def bull_back(image: pygame.Surface) -> int:
    """How far above its middle the bull's back is (its body's top, behind the head)."""
    box = image.get_bounding_rect()
    return box.h // 2 - 8


# --- Pinsir: Pinch! ------------------------------------------------------------

TRACK_Y = 236       # the log run, up at the height of Pinsir's horns
GROUND = 312
JAW_X = 190          # the middle of Pinsir's horns
PERFECT, GOOD = 4, 11  # px from the middle
PINCH_TIME = 0.28    # seconds the horns stay shut (no pinching again meanwhile)
LOG_W, BIG_W = 26, 40


class Pinch(MiniGame):
    TITLE = "Pinch!"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items: list[list] = []  # [kind, x]
        self.next_roll = 0.5
        self.shut = 0.0
        self.chips: list[list] = []  # [x, y, vx, vy, age]: bits of a crunched log
        self.pinsir = _icon("pinsir", GROUND - TRACK_Y + 14)  # (horn tips just above the run)
        self.geodude = _icon("geodude", 24)

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in PINCH_KEYS and self.playing:
            self._pinch()

    def pointer(self, pos, drag) -> None:
        if not drag:
            self._pinch()

    def _speed(self) -> float:
        return 150 + 110 * (1 - self.time_left / GAME_TIME)

    def _pinch(self) -> None:
        if self.shut:
            return
        self.shut = PINCH_TIME
        hit = min(self.items, key=lambda i: abs(i[1] - JAW_X), default=None)
        off = abs(hit[1] - JAW_X) if hit else 999
        if hit and hit[0] == "geodude" and off < 14:
            self.items.remove(hit)
            self.pop(JAW_X, TRACK_Y - 40, -4)
            return
        if not hit or hit[0] == "geodude" or off > (BIG_W if hit[0] == "big" else LOG_W) / 2:
            self.pop(JAW_X, TRACK_Y - 40, -1)  # (snapping at nothing: no mashing)
            return
        self.items.remove(hit)
        points = (3 if off <= PERFECT else 2 if off <= GOOD else 1) + (1 if hit[0] == "big" else 0)
        self.pop(JAW_X, TRACK_Y - 40, points)
        if off <= PERFECT:
            self.pops.append([JAW_X, TRACK_Y - 62, "Perfect!", (140, 255, 150), 0.0])
        for i in range(6):
            self.chips.append([JAW_X, TRACK_Y - 8, self.rng.uniform(-90, 90), self.rng.uniform(-200, -60), 0.0])

    def play(self, dt: float) -> None:
        progress = 1 - self.time_left / GAME_TIME
        self.shut = max(0.0, self.shut - dt)
        self.next_roll -= dt
        if self.next_roll <= 0:
            self.next_roll = self.rng.uniform(0.6, 1.0) - 0.3 * progress
            kind = self.rng.choices(("log", "big", "geodude"), weights=(64, 14, 22))[0]
            self.items.append([kind, W + 30.0])
        speed = self._speed()
        for item in self.items:
            item[1] -= speed * dt
        self.items = [i for i in self.items if i[1] > -40]
        for c in self.chips:
            c[3] += 500 * dt
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[4] += dt
        self.chips = [c for c in self.chips if c[4] < 0.8]

    def draw_play(self, canvas: pygame.Surface) -> None:
        # Pinsir stands under the log run; its horns reach up around it.
        lunge = -4 if self.shut else 0
        canvas.blit(self.pinsir, self.pinsir.get_rect(midbottom=(JAW_X, GROUND + lunge)))
        for x in range(30, W, 140):  # the run's posts (not through Pinsir)
            if abs(x - JAW_X) < 50:
                continue
            pygame.draw.rect(canvas, (90, 64, 40), (x, TRACK_Y + 12, 6, GROUND - TRACK_Y - 12))
        pygame.draw.rect(canvas, (130, 94, 60), (0, TRACK_Y + 8, W, 6))
        pygame.draw.line(canvas, (70, 50, 30), (0, TRACK_Y + 8), (W, TRACK_Y + 8), 2)
        zone = pygame.Surface((2 * GOOD, 6), pygame.SRCALPHA)  # where to pinch
        zone.fill((255, 230, 90, 120))
        canvas.blit(zone, (JAW_X - GOOD, TRACK_Y + 8))
        for kind, x in self.items:
            if kind == "geodude":
                canvas.blit(self.geodude, (round(x - 12), TRACK_Y - 16))
                continue
            w = BIG_W if kind == "big" else LOG_W
            h = 18 if kind == "big" else 14
            r = pygame.Rect(0, 0, w, h)
            r.midbottom = (round(x), TRACK_Y + 8)
            pygame.draw.rect(canvas, (150, 100, 60), r, border_radius=6)
            pygame.draw.rect(canvas, (80, 52, 30), r, 2, border_radius=6)
            pygame.draw.ellipse(canvas, (210, 170, 120), (r.right - 8, r.y + 2, 6, h - 4))
        if self.shut > PINCH_TIME - 0.12:  # the snap: a burst where the horns meet
            k = (PINCH_TIME - self.shut) / 0.12
            for i in range(8):
                a = i * math.tau / 8
                r1, r2 = 6 + 10 * k, 12 + 14 * k
                pygame.draw.line(canvas, (255, 250, 220), (JAW_X + math.cos(a) * r1, TRACK_Y + math.sin(a) * r1),
                                 (JAW_X + math.cos(a) * r2, TRACK_Y + math.sin(a) * r2), 2)
        for x, y, _, _, _ in self.chips:
            pygame.draw.rect(canvas, (170, 120, 70), (round(x), round(y), 3, 3))

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.t < 6 and not self.over:
            ui.text(window, "Pinch when a log is between the horns: Space, or tap", (W / 2, 100), ui.WHITE,
                    size=22, align="center")
