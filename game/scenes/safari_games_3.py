"""More Safari Zone games (see safari_games.py, whose `MiniGame` frame they
use): keyboard and touch both work in each.

- Kangaskhan, **Where's Baby?** (`WheresBaby`): Kangaskhan's baby peeks
  out of one of three bushes, then the bushes shuffle; pick the one it's
  in (Left/Right and Space, or tap it). Each right pick in a row is worth
  more, and the shuffles get faster and longer.
- Exeggcute, **Egg Pop** (`EggPop`): eggs pop up out of three nests; bop
  the awake ones (Left, Up/Space, Right for the nests, or tap one), not
  the sleeping ones. A cracked egg's lucky; bopping an empty nest costs.
"""

from __future__ import annotations

import math

import pygame

from ..engine import ui
from .safari_games import GAME_TIME, MiniGame, W, _icon

PICK_KEYS = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z)


# --- Kangaskhan: Where's Baby? -------------------------------------------------

BUSH_Y = 268
BUSH_XS = (180, 320, 460)    # the three spots
PEEK = 1.0                   # seconds the baby shows before the shuffle
REVEAL = 0.9                 # seconds after a pick, showing where it was
WRONG_COST = 1


class WheresBaby(MiniGame):
    TITLE = "Where's Baby?"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slots = [0, 1, 2]   # bush i stands at spot slots[i]
        self.baby = 0            # which bush the baby's in
        self.cursor = 1          # the spot picked with the keys
        self.round, self.streak = 0, 0
        self.phase, self.phase_t = "peek", PEEK
        self.swaps: list[tuple[int, int]] = []
        self.swap = None         # (bush a, bush b, from spot a, from spot b, progress 0..1)
        self.picked: int | None = None  # the spot picked (shown while revealing)
        self.mother = _icon("kangaskhan", 76)
        self.kid = _icon("kangaskhan", 34)

    # (where each bush is drawn: its spot, or between two while swapping)
    def _bush_x(self, bush: int) -> float:
        if self.swap and bush in self.swap[:2]:
            a, b, xa, xb, k = self.swap
            start, end = (xa, xb) if bush == a else (xb, xa)
            return BUSH_XS[start] + (BUSH_XS[end] - BUSH_XS[start]) * (0.5 - 0.5 * math.cos(math.pi * k))
        return BUSH_XS[self.slots[bush]]

    def _swap_time(self) -> float:
        return max(0.2, 0.5 - 0.035 * self.round)

    def _new_round(self) -> None:
        self.round += 1
        self.baby = self.rng.randrange(3)
        self.phase, self.phase_t = "peek", PEEK
        self.picked = None
        count = min(9, 3 + self.round)  # longer shuffles as it goes
        self.swaps = [tuple(self.rng.sample(range(3), 2)) for _ in range(count)]

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type != pygame.KEYDOWN or not self.playing or self.phase != "pick":
            return
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.cursor = max(0, min(2, self.cursor + (1 if event.key == pygame.K_RIGHT else -1)))
        elif event.key in PICK_KEYS + (pygame.K_UP,):
            self._pick(self.cursor)

    def pointer(self, pos, drag) -> None:
        if drag or self.phase != "pick":
            return
        spot = min(range(3), key=lambda s: abs(BUSH_XS[s] - pos[0]))
        if abs(BUSH_XS[spot] - pos[0]) < 60:
            self.cursor = spot
            self._pick(spot)

    def _pick(self, spot: int) -> None:
        self.picked = spot
        right = self.slots[self.baby] == spot
        if right:
            self.streak += 1
            self.pop(BUSH_XS[spot], BUSH_Y - 50, 2 + min(self.streak, 4))
        else:
            self.streak = 0
            self.pop(BUSH_XS[spot], BUSH_Y - 50, -WRONG_COST)
        self.phase, self.phase_t = "reveal", REVEAL

    def play(self, dt: float) -> None:
        if self.round == 0:
            self._new_round()
        if self.phase == "shuffle":
            a, b, xa, xb, k = self.swap
            k += dt / self._swap_time()
            if k < 1:
                self.swap = (a, b, xa, xb, k)
                return
            self.slots[a], self.slots[b] = xb, xa
            self.swap = None
            if self.swaps:
                self._next_swap()
            else:
                self.phase = "pick"
            return
        if self.phase in ("peek", "reveal"):
            self.phase_t -= dt
            if self.phase_t <= 0:
                if self.phase == "peek":
                    self.phase = "shuffle"
                    self._next_swap()
                else:
                    self._new_round()

    def _next_swap(self) -> None:
        a, b = self.swaps.pop()
        self.swap = (a, b, self.slots[a], self.slots[b], 0.0)

    def draw_play(self, canvas: pygame.Surface) -> None:
        canvas.blit(self.mother, self.mother.get_rect(bottomright=(W - 20, BUSH_Y + 30)))
        show_baby = self.phase in ("peek", "reveal")
        for bush in range(3):
            x = round(self._bush_x(bush))
            lift = 0
            if self.swap and bush in self.swap[:2]:  # (a hop while it swaps)
                lift = round(math.sin(math.pi * self.swap[4]) * 14)
            if show_baby and bush == self.baby:  # the baby, peeking out over the top (a little hop)
                hop = round(abs(math.sin(self.t * 6)) * 4)
                box = canvas.blit(self.kid, self.kid.get_rect(midbottom=(x, BUSH_Y - 30 - hop)))
                if self.phase == "peek":  # (easy to spot against the woods)
                    pygame.draw.rect(canvas, (255, 230, 80), (box.centerx - 2, box.y - 16, 4, 9))
                    pygame.draw.rect(canvas, (255, 230, 80), (box.centerx - 2, box.y - 5, 4, 3))
            _bush(canvas, x, BUSH_Y - lift)
        if self.phase == "pick" and self.playing:
            x = BUSH_XS[self.cursor]
            pygame.draw.polygon(canvas, (255, 240, 120), [(x, BUSH_Y + 30), (x - 7, BUSH_Y + 40), (x + 7, BUSH_Y + 40)])
        if self.phase == "reveal" and self.picked is not None:
            right = self.slots[self.baby] == self.picked
            color = (120, 240, 120) if right else (255, 110, 100)
            pygame.draw.circle(canvas, color, (BUSH_XS[self.picked], BUSH_Y - 4), 34, 2)

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.over:
            return
        text = {"peek": "Watch the baby!", "shuffle": "Keep your eye on it...",
                "pick": "Which bush? Left/Right and Space, or tap", "reveal": ""}[self.phase]
        if text and self.playing:
            ui.text(window, text, (W / 2, 100), ui.WHITE, size=24, align="center")
        if self.streak > 1:
            ui.text(window, f"{self.streak} in a row!", (W / 2, 124), ui.YELLOW, size=22, align="center")


def _bush(canvas: pygame.Surface, x: int, bottom: int) -> None:
    for dx, dy, r, color in ((-16, -14, 16, (40, 110, 50)), (16, -14, 16, (40, 110, 50)), (0, -24, 19, (52, 132, 60)),
                             (-8, -16, 12, (70, 160, 76)), (10, -20, 9, (90, 180, 90))):
        pygame.draw.circle(canvas, color, (x + dx, bottom + dy), r)
    pygame.draw.circle(canvas, (24, 70, 32), (x, bottom - 22), 34, 1)


# --- Exeggcute: Egg Pop --------------------------------------------------------

NEST_Y = 290
NEST_XS = (180, 320, 460)
NEST_KEYS = {pygame.K_LEFT: 0, pygame.K_UP: 1, pygame.K_SPACE: 1, pygame.K_DOWN: 1, pygame.K_RIGHT: 2}
EGGS = {"awake": 1, "lucky": 3, "asleep": -2}
EMPTY_COST = 1
BOP_TIME = 0.25      # seconds a bopped egg shows squashed


class EggPop(MiniGame):
    TITLE = "Egg Pop"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eggs: list[list] = []   # [nest, kind, age, stay, bopped (0 or seconds since)]
        self.next_pop = 0.5
        self.host = _icon("exeggcute", 46)

    def handle_event(self, event: pygame.event.Event) -> None:
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in NEST_KEYS and self.playing:
            self._bop(NEST_KEYS[event.key])

    def pointer(self, pos, drag) -> None:
        if drag:
            return
        nest = min(range(3), key=lambda n: abs(NEST_XS[n] - pos[0]))
        if abs(NEST_XS[nest] - pos[0]) < 60:
            self._bop(nest)

    def _bop(self, nest: int) -> None:
        egg = next((e for e in self.eggs if e[0] == nest and not e[4]), None)
        if egg is None:
            self.pop(NEST_XS[nest], NEST_Y - 50, -EMPTY_COST)
            return
        egg[4] = 1e-6
        self.pop(NEST_XS[nest], NEST_Y - 50, EGGS[egg[1]])

    def play(self, dt: float) -> None:
        progress = 1 - self.time_left / GAME_TIME
        self.next_pop -= dt
        free = [n for n in range(3) if not any(e[0] == n for e in self.eggs)]
        if self.next_pop <= 0 and free:
            self.next_pop = self.rng.uniform(0.45, 0.8) - 0.25 * progress
            kind = self.rng.choices(tuple(EGGS), weights=(62, 10, 28))[0]
            self.eggs.append([self.rng.choice(free), kind, 0.0, 1.0 - 0.45 * progress, 0.0])
        for egg in self.eggs:
            egg[2] += dt
            if egg[4]:
                egg[4] += dt
        self.eggs = [e for e in self.eggs if (e[4] and e[4] < BOP_TIME) or (not e[4] and e[2] < e[3])]

    def draw_play(self, canvas: pygame.Surface) -> None:
        canvas.blit(self.host, self.host.get_rect(midbottom=(W - 60, NEST_Y + 12)))
        for n, x in enumerate(NEST_XS):  # the nests' backs
            pygame.draw.ellipse(canvas, (100, 70, 40), (x - 34, NEST_Y - 12, 68, 22))
        for nest, kind, age, stay, bopped in self.eggs:
            x = NEST_XS[nest]
            rise = min(1.0, age / 0.12, max(0.0, (stay - age) / 0.12)) if not bopped else 1.0
            y = NEST_Y - round(22 * rise)
            squash = 0.5 if bopped else 1.0
            _egg(canvas, x, y, kind, squash)
        for x in NEST_XS:  # the nests' fronts, over the eggs' bottoms
            pygame.draw.ellipse(canvas, (140, 100, 56), (x - 36, NEST_Y - 4, 72, 20))
            for i in range(-28, 30, 8):
                pygame.draw.line(canvas, (180, 140, 80), (x + i, NEST_Y), (x + i + 5, NEST_Y + 10))

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.t < 6 and not self.over:
            ui.text(window, "Bop the awake eggs, not the sleeping ones!", (W / 2, 100), ui.WHITE, size=22,
                    align="center")
            for x, label in zip(NEST_XS, ("Left", "Up / Space", "Right")):
                ui.text(window, label, (x, NEST_Y + 24), ui.WHITE, size=20, align="center")


def _egg(canvas: pygame.Surface, x: int, y: int, kind: str, squash: float) -> None:
    """An Exeggcute egg: pink, a face; asleep, eyes shut; lucky, cracked and golden."""
    w, h = 26, round(30 * squash)
    body = pygame.Rect(0, 0, w, h)
    body.midbottom = (x, y + 14)
    color = (250, 214, 90) if kind == "lucky" else (246, 196, 196)
    pygame.draw.ellipse(canvas, (90, 60, 60), body.inflate(2, 2))
    pygame.draw.ellipse(canvas, color, body)
    ey = body.y + h // 2 - 2
    if kind == "asleep":
        for dx in (-5, 5):
            pygame.draw.line(canvas, (60, 40, 40), (x + dx - 3, ey), (x + dx + 3, ey), 2)
    else:
        for dx in (-5, 5):
            pygame.draw.circle(canvas, (255, 255, 255), (x + dx, ey), 3)
            pygame.draw.circle(canvas, (40, 30, 30), (x + dx, ey), 1)
        pygame.draw.line(canvas, (150, 60, 60), (x - 3, ey + 7), (x + 3, ey + 7), 1)
    if kind == "lucky":  # a crack
        pygame.draw.lines(canvas, (160, 110, 30), False,
                          [(body.x + 4, body.y + 8), (x - 3, body.y + 12), (x + 2, body.y + 7), (body.right - 4, body.y + 11)], 1)
