"""The Safari Zone's games: a wild Pokémon met in the tall grass challenges
the player to one (`Challenge`: Play or Decline) instead of a battle.

- Chansey, **Egg Catch** (`EggCatch`): catch the eggs Chansey tosses down
  in a basket (Left/Right, or tap/drag where it should go); golden eggs
  are worth more; a Voltorb that drops in by mistake costs points and
  stuns the basket.
- Scyther, **Fruit Slice** (`FruitSlice`): swipe (mouse or finger) through
  the berries tossed up from below; slicing several in one swipe is a
  combo; slicing a Voltorb costs points. Touch and mouse only.

Each lasts `GAME_TIME` seconds, then shows the score and goes back to the
map (`on_done(score)`), which turns it into Kudos (Part C).
"""

from __future__ import annotations

import math
import random

import pygame

from .. import settings
from ..engine import touch, ui
from ..engine.scene import Scene, Transition
from ..mechanics.pokemon import SPECIES, animations
from ..world.themes import Backdrop

GAME_TIME = 30.0
COUNTDOWN = 2.4  # "3, 2, 1, Go!" before the clock starts
W, H = settings.LOGICAL_SIZE
# The species with a game, and which (safari_games_2.py has the later ones).
GAMES = {"chansey": "egg_catch", "scyther": "fruit_slice", "tauros": "rodeo", "pinsir": "pinch",
         "kangaskhan": "wheres_baby", "exeggcute": "egg_pop"}


def _icon(species: str, height: int) -> pygame.Surface:
    frame = animations(SPECIES[species])["idle"].frame(0)
    box = frame.get_bounding_rect()
    frame = frame.subsurface(box)
    return pygame.transform.scale_by(frame, height / max(1, box.h))


class Challenge:
    """A wild Pokémon's challenge: Play or Decline (`picked`: "play" or "")."""

    TEXT = {
        "egg_catch": ("Egg Catch!", ["Catch the eggs it tosses down in your basket.",
                                     "Golden eggs are worth 3. Don't catch the Voltorb!",
                                     "Move: Left/Right, or tap where the basket should go."]),
        "fruit_slice": ("Fruit Slice!", ["Slice the berries it tosses up: swipe through them.",
                                         "Several in one swipe: a combo. Don't slice the Voltorb!",
                                         "Swipe with the mouse (hold the button) or a finger."]),
        "rodeo": ("Rodeo!", ["Ride the bucking Tauros: lean against its tilt to stay on.",
                             "The steadier you sit, the more you score. Too far, and you're thrown!",
                             "Lean: Left/Right, or touch and hold either half of the screen."]),
        "pinch": ("Pinch!", ["Logs roll past between Pinsir's horns: pinch them!",
                             "Dead centre is a Perfect. Big logs are worth more. Not the Geodude!",
                             "Pinch: Space or Enter, or tap."]),
        "wheres_baby": ("Where's Baby?", ["Its baby hides in a bush, and the bushes shuffle.",
                                          "Pick the one it's in. Right picks in a row are worth more!",
                                          "Pick: Left/Right and Space, or tap the bush."]),
        "egg_pop": ("Egg Pop!", ["Eggs pop up out of the nests: bop the awake ones!",
                                 "Not the sleeping ones. Cracked golden eggs are lucky.",
                                 "Bop: Left, Up/Space, Right for the nests, or tap one."]),
    }

    def __init__(self, species: str):
        self.species = species
        self.title, self.lines = self.TEXT[GAMES[species]]
        self.options = (("play", "Play"), ("", "Decline"))
        self.choice = 0
        self.picked = ""
        self.rect = pygame.Rect(0, 0, 420, 156)
        self.rect.center = (320, 170)
        self.icon = _icon(species, 40)

    def handle_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.options)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            self.picked = self.options[self.choice][0]
            return True
        elif key in (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE):
            return True
        return False

    def _row_y(self, i: int) -> int:
        return self.rect.bottom - 18 - (len(self.options) - i) * 17

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.rect)
        canvas.blit(self.icon, (self.rect.right - self.icon.get_width() - 12, self.rect.y + 10))
        ui.cursor(canvas, self.rect.x + 16, self._row_y(self.choice) + 6)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.rect
        ui.text(window, f"A wild {SPECIES[self.species].name} challenges you: {self.title}", (r.x + 12, r.y + 9),
                ui.YELLOW, size=24)
        for i, line in enumerate(self.lines):
            ui.text(window, line, (r.x + 12, r.y + 30 + i * 13), ui.WHITE, size=22)
        for i, (_, label) in enumerate(self.options):
            ui.text(window, label, (r.x + 22, self._row_y(i)), ui.YELLOW if i == self.choice else ui.WHITE, size=26)


class MiniGame(Scene):
    """A Safari game's frame: the backdrop, a countdown, `GAME_TIME` seconds
    of play (`play(dt)`), then the score; Enter goes back to `return_to`."""

    pausable = False
    TITLE = ""

    def __init__(self, return_to: Scene, species: str, backdrop: Backdrop, on_done, seed: int | None = None):
        self.return_to, self.species, self.on_done = return_to, species, on_done
        self.rng = random.Random(seed)
        from .battle import _background  # (the battle's painted field, cached)
        painted = _background(backdrop)
        # The painted field sits on the screen's bottom; above it, its top row, stretched.
        self.backdrop = pygame.Surface((W, H))
        gap = H - painted.get_height()
        row = painted.subsurface((0, 0, W, 1)).copy()
        colours = [tuple(row.get_at((x, 0)))[:3] for x in range(W)]
        sky = max(set(colours), key=colours.count)
        if colours.count(sky) >= W // 2:  # (open sky: a cloud cut by the edge would streak, so it's sky too)
            row.fill(sky)
        self.backdrop.blit(pygame.transform.scale(row, (W, gap)), (0, 0))
        self.backdrop.blit(painted, (0, gap))
        self.t = 0.0
        self.score = 0
        self.over = False
        self.pops: list[list] = []  # [x, y, text, color, age]: "+1" rising from where it happened

    @property
    def time_left(self) -> float:
        return max(0.0, GAME_TIME - (self.t - COUNTDOWN))

    @property
    def playing(self) -> bool:
        return self.t >= COUNTDOWN and not self.over

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and self.over and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z,
                                                                        pygame.K_x, pygame.K_ESCAPE):
            self._finish()

    def tap(self, pos: tuple[float, float], drag: bool) -> None:
        if self.over and not drag:
            self._finish()
        elif self.playing:
            self.pointer(pos, drag)

    def pointer(self, pos: tuple[float, float], drag: bool) -> None:
        """A tap or a drag during play."""

    def _finish(self) -> None:
        if self.next_scene is None:
            self.on_done(self.score)
            self.next_scene = Transition(self, self.return_to, flashes=0)

    def update(self, dt: float) -> None:
        self.t += dt
        for p in self.pops:
            p[4] += dt
        self.pops = [p for p in self.pops if p[4] < 0.8]
        if self.playing:
            self.play(dt)
            if self.time_left <= 0:
                self.over = True

    def play(self, dt: float) -> None:
        pass

    def pop(self, x: float, y: float, points: int) -> None:
        self.score = max(0, self.score + points)
        text = f"+{points}" if points > 0 else str(points)
        self.pops.append([x, y, text, ui.YELLOW if points > 0 else (255, 90, 90), 0.0])

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.blit(self.backdrop, (0, 0))
        self.draw_play(canvas)
        bar = pygame.Rect(170, 8, 300, 6)  # the time left
        pygame.draw.rect(canvas, (30, 30, 40), bar)
        pygame.draw.rect(canvas, ui.YELLOW, (bar.x, bar.y, round(bar.w * self.time_left / GAME_TIME), bar.h))

    def draw_play(self, canvas: pygame.Surface) -> None:
        pass

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, self.TITLE, (8, 4), ui.YELLOW, size=26)
        ui.text(window, f"Score: {self.score}", (W - 8, 4), ui.WHITE, size=26, align="right")
        for x, y, text, color, age in self.pops:
            ui.text(window, text, (x, y - 24 * age), color, size=24, align="center")
        if self.t < COUNTDOWN:
            n = 3 - int(self.t / (COUNTDOWN / 3))
            ui.text(window, str(n) if n > 0 else "Go!", (W / 2, H / 2 - 30), ui.YELLOW, size=64, align="center")
        if self.over:
            box = pygame.Rect(0, 0, 300, 90)
            box.center = (W // 2, H // 2)
            surface = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
            ui.window_box(surface, surface.get_rect())
            ui.blit_scaled(window, surface, box.topleft)
            ui.text(window, "Time's up!", (W / 2, box.y + 12), ui.YELLOW, size=30, align="center")
            ui.text(window, f"Score: {self.score}", (W / 2, box.y + 38), ui.WHITE, size=28, align="center")
            ui.text(window, "Enter or tap: continue", (W / 2, box.y + 64), ui.GREY, size=20, align="center")


# --- Chansey: Egg Catch --------------------------------------------------------

BASKET_W, BASKET_Y = 46, 318
BASKET_SPEED = 300       # px/s with the keys (or towards a tapped spot)
STUN = 0.7               # seconds the basket can't move after catching a Voltorb
EGG_R = 7


class EggCatch(MiniGame):
    TITLE = "Egg Catch"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.basket = W / 2
        self.target: float | None = None  # where a tap sent it
        self.stun = 0.0
        self.items: list[list] = []  # [kind, x, y, vy]
        self.next_drop = 0.4
        self.chansey = _icon("chansey", 48)
        self.voltorb = _icon("voltorb", 18)

    def pointer(self, pos, drag) -> None:
        self.target = pos[0]

    def _chansey_x(self) -> float:
        return W / 2 + math.sin(self.t * 1.3) * 200 + math.sin(self.t * 3.1) * 40

    def play(self, dt: float) -> None:
        progress = 1 - self.time_left / GAME_TIME  # (0 at the start, 1 at the end: faster and faster)
        self.stun = max(0.0, self.stun - dt)
        if not self.stun:
            keys = touch.pressed()  # (keyboard and the touch arrows)
            move = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * BASKET_SPEED * dt
            if move:
                self.target = None
            elif self.target is not None:
                d = self.target - self.basket
                move = max(-BASKET_SPEED * dt, min(BASKET_SPEED * dt, d))
            self.basket = max(BASKET_W / 2, min(W - BASKET_W / 2, self.basket + move))
        self.next_drop -= dt
        if self.next_drop <= 0:
            self.next_drop = 0.7 - 0.35 * progress
            kind = self.rng.choices(("egg", "gold", "voltorb"), weights=(70, 8, 22))[0]
            self.items.append([kind, self._chansey_x(), 92.0, 70 + 60 * progress])
        for item in self.items:
            item[3] += 260 * dt  # (falling faster)
            item[2] += item[3] * dt
        kept = []
        for item in self.items:
            kind, x, y, _ = item
            if BASKET_Y - 6 <= y <= BASKET_Y + 4 and abs(x - self.basket) < BASKET_W / 2 + EGG_R - 2:
                if kind == "voltorb":
                    self.stun = STUN
                    self.pop(x, y - 12, -3)
                else:
                    self.pop(x, y - 12, 3 if kind == "gold" else 1)
            elif y < H + 10:
                kept.append(item)
        self.items = kept

    def draw_play(self, canvas: pygame.Surface) -> None:
        cx = self._chansey_x()
        canvas.blit(self.chansey, (round(cx - self.chansey.get_width() / 2), 40))
        for kind, x, y, _ in self.items:
            if kind == "voltorb":
                canvas.blit(self.voltorb, (round(x - 9), round(y - 9)))
                continue
            color = (250, 214, 60) if kind == "gold" else (250, 246, 236)
            pygame.draw.ellipse(canvas, (60, 50, 40), (x - EGG_R - 1, y - EGG_R - 3, 2 * EGG_R + 2, 2 * EGG_R + 6))
            pygame.draw.ellipse(canvas, color, (x - EGG_R, y - EGG_R - 2, 2 * EGG_R, 2 * EGG_R + 4))
            if kind == "egg":
                pygame.draw.circle(canvas, (230, 150, 160), (round(x - 2), round(y - 2)), 2)
        b = pygame.Rect(0, 0, BASKET_W, 16)
        b.midtop = (round(self.basket), BASKET_Y)
        wobble = math.sin(self.t * 40) * 2 if self.stun else 0
        b.x += round(wobble)
        pygame.draw.rect(canvas, (120, 76, 40), b, border_radius=4)
        pygame.draw.rect(canvas, (70, 42, 20), b, 2, border_radius=4)
        for i in range(b.x + 6, b.right - 4, 7):  # the weave
            pygame.draw.line(canvas, (150, 100, 56), (i, b.y + 3), (i, b.bottom - 3))
        if self.stun:
            pygame.draw.circle(canvas, (255, 240, 90), (b.centerx, b.y - 6), 3)


# --- Scyther: Fruit Slice ------------------------------------------------------

GRAVITY = 520
FRUIT_R = 11
TRAIL_TIME = 0.18        # seconds a swipe's trail lasts
COMBO_WINDOW = 0.5       # slices this close in one swipe make a combo
FRUITS = {"oran": ((70, 120, 220), 1), "pecha": ((240, 140, 180), 1), "razz": ((250, 200, 60), 3)}


class FruitSlice(MiniGame):
    TITLE = "Fruit Slice"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items: list[list] = []   # [kind, x, y, vx, vy]
        self.halves: list[list] = []  # [color, x, y, vx, vy, side, age]
        self.trail: list[list] = []   # [x, y, age]
        self.last: tuple[float, float] | None = None
        self.combo, self.combo_t = 0, 0.0
        self.next_toss = 0.3
        self.scyther = _icon("scyther", 56)
        self.voltorb = _icon("voltorb", 2 * FRUIT_R)

    def pointer(self, pos, drag) -> None:
        if not drag or self.last is None:  # a new swipe
            self.last, self.combo = pos, 0
            self.trail = [[pos[0], pos[1], 0.0]]
            return
        a, b = self.last, pos
        self.trail.append([b[0], b[1], 0.0])
        for item in list(self.items):
            if _segment_hits(a, b, (item[1], item[2]), FRUIT_R + 2):
                self._slice(item, a, b)
        self.last = pos

    def _slice(self, item, a, b) -> None:
        self.items.remove(item)
        kind, x, y = item[0], item[1], item[2]
        if kind == "voltorb":
            self.pop(x, y - 14, -5)
            self.combo = 0
            return
        color, points = FRUITS[kind]
        self.combo = self.combo + 1 if self.t - self.combo_t < COMBO_WINDOW else 1
        self.combo_t = self.t
        self.pop(x, y - 14, points + (self.combo - 1))  # (each one after the first in a swipe: +1 more)
        nx, ny = b[1] - a[1], a[0] - b[0]  # the halves fly apart across the cut
        length = math.hypot(nx, ny) or 1
        for side in (-1, 1):
            self.halves.append([color, x, y, item[3] + side * 70 * nx / length, item[4] + side * 70 * ny / length,
                                side, 0.0])

    def play(self, dt: float) -> None:
        progress = 1 - self.time_left / GAME_TIME
        self.next_toss -= dt
        if self.next_toss <= 0:
            self.next_toss = 0.75 - 0.35 * progress
            for _ in range(1 if self.rng.random() < 0.75 else 2):
                kind = self.rng.choices(("oran", "pecha", "razz", "voltorb"), weights=(40, 40, 6, 16))[0]
                x = self.rng.uniform(80, W - 80)
                self.items.append([kind, x, H + 14, self.rng.uniform(-70, 70) - (x - W / 2) * 0.25,
                                   -self.rng.uniform(430, 500)])
        for item in self.items:
            item[4] += GRAVITY * dt
            item[1] += item[3] * dt
            item[2] += item[4] * dt
        self.items = [i for i in self.items if i[2] < H + 30]
        for half in self.halves:
            half[4] += GRAVITY * dt
            half[1] += half[3] * dt
            half[2] += half[4] * dt
            half[6] += dt
        self.halves = [h for h in self.halves if h[6] < 1.2]
        for point in self.trail:
            point[2] += dt
        self.trail = [p for p in self.trail if p[2] < TRAIL_TIME]

    def draw_play(self, canvas: pygame.Surface) -> None:
        sway = math.sin(self.t * 2) * 4
        canvas.blit(self.scyther, (W - self.scyther.get_width() - 14, round(H - self.scyther.get_height() - 30 + sway)))
        for kind, x, y, _, _ in self.items:
            if kind == "voltorb":
                canvas.blit(self.voltorb, (round(x - FRUIT_R), round(y - FRUIT_R)))
                continue
            color = FRUITS[kind][0]
            pygame.draw.circle(canvas, (40, 30, 30), (round(x), round(y)), FRUIT_R + 1)
            pygame.draw.circle(canvas, color, (round(x), round(y)), FRUIT_R)
            pygame.draw.circle(canvas, (255, 255, 255), (round(x - 4), round(y - 4)), 3)
            pygame.draw.line(canvas, (60, 130, 50), (x, y - FRUIT_R), (x + 3, y - FRUIT_R - 5), 2)
        for color, x, y, _, _, side, age in self.halves:
            r = pygame.Rect(0, 0, 2 * FRUIT_R, 2 * FRUIT_R)
            r.center = (round(x), round(y))
            pygame.draw.arc(canvas, color, r, math.pi / 2 if side < 0 else -math.pi / 2,
                            3 * math.pi / 2 if side < 0 else math.pi / 2, FRUIT_R)
        if len(self.trail) > 1:
            pts = [(round(x), round(y)) for x, y, _ in self.trail]
            pygame.draw.lines(canvas, (255, 255, 255), False, pts, 3)
            pygame.draw.lines(canvas, (180, 230, 255), False, pts, 1)


def _segment_hits(a, b, c, r) -> bool:
    """Whether the segment a-b passes within `r` of point `c`."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if not length2 else max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / length2))
    px, py = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def game_for(species: str):
    """The game scene class for `species` (see GAMES)."""
    from .safari_games_2 import Pinch, Rodeo  # (they build on this module)
    from .safari_games_3 import EggPop, WheresBaby
    return {"egg_catch": EggCatch, "fruit_slice": FruitSlice, "rodeo": Rodeo, "pinch": Pinch,
            "wheres_baby": WheresBaby, "egg_pop": EggPop}[GAMES[species]]
