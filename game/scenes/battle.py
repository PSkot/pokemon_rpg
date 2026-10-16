"""Turn-based battle screen: enemies on the left, the player's party on the right.

Each round has two phases. First every party member picks an action
through the menus; then everyone's actions (the enemies' too) are carried
out one at a time, fastest first, with animations.
"""

import math
import random
from collections import Counter
from dataclasses import dataclass
from functools import cache

import pygame

from .. import settings
from ..dev import DEV
from ..engine import hats, ui
from ..engine.animation import Animation
from ..engine.scene import Scene, Transition
from ..mechanics.combat import MAX_STAGE, STAGE_STATS, Hit, damage, stage_factor
from ..mechanics.items import MEDICINE, Bag, Medicine
from ..mechanics.loot import LootTable, merge, wild_loot
from ..mechanics.moves import Move
from ..mechanics.pokemon import MAX_LEVEL, SPECIES, Monster, animations
from ..mechanics.status import FULLY_PARALYZED, PARALYSIS_SPEED, ROUND_DAMAGE, STATUSES, THAW_CHANCE
from ..mechanics.type_chart import COLORS
from ..mechanics.type_chart import name as type_name
from ..world.themes import MEADOW_BACKDROP, Backdrop

HORIZON_Y = 118
PANEL_Y = 264  # top of the menu windows

ENEMY_WINDOW = pygame.Rect(6, PANEL_Y, 170, 90)
COMMAND_WINDOW = pygame.Rect(180, PANEL_Y, 104, 90)
PARTY_WINDOW = pygame.Rect(288, PANEL_Y, 346, 90)
SKILL_WINDOW = pygame.Rect(6, PANEL_Y, 278, 90)  # opens over the enemy + command windows
ROW_H = 19   # menu line height
LIST_ROWS = 4  # rows that fit in the skill/item list
PAD = 9      # space above the first line in a window
MESSAGE_WINDOW = pygame.Rect(6, 6, 628, PAD * 2 + ROW_H)
INFO_WINDOW = MESSAGE_WINDOW.move(0, 16)  # item descriptions, below the key hints

COMMANDS = ["Fight", "Skills", "Item", "Run"]
TARGET_TEXT = {"enemy": "Enemy", "ally": "Ally", "self": "Self"}
SPREAD_TEXT = {"enemy": "All", "ally": "Party"}
STAT_NAMES = {"attack": "attack", "defense": "defense", "speed": "speed", "accuracy": "accuracy"}
STAT_ABBREV = {"attack": "ATK", "defense": "DEF", "speed": "SPD", "accuracy": "ACC"}
SEED_COLOR = (150, 220, 90)
CONFUSED_COLOR = (230, 150, 230)
CONFUSION_ROUNDS = (2, 5)   # turns a confusion lasts (counted on its own turns)
CONFUSION_SELF_HIT = 0.5    # chance a confused Pokémon hurts itself instead of acting
SELF_HIT = Move("its confusion", 40, "self")  # typeless, as in Gen 1
BIND_ROUNDS = (2, 5)
REST_ROUNDS = 2
HEAL_COLOR = (120, 230, 120)
XP_COLOR = (88, 168, 248)

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
CANCEL_KEYS = (pygame.K_x, pygame.K_BACKSPACE)

STEP_FORWARD = 14    # px the party member choosing a command steps out of line
ATTACK_STEP = 28     # px a combatant steps forward to act

# Pacing of a round, in seconds.
ROUND_START_PAUSE = 0.4  # after the last command is chosen
WIND_UP_TIME = 0.4       # stepping forward, with the move's name shown
IMPACT_HOLD = 0.35       # extra time on the last frame after the hit lands
STEP_BACK_TIME = 0.4     # stepping back into line
STATUS_MESSAGE_TIME = 1.0  # "is fast asleep", "is hurt by poison", ...
QUICK_MESSAGE_TIME = 0.7   # "is quick to act!"
REGEN_MESSAGE_TIME = 0.8   # "restored 2 HP."
ACTION_PAUSE = 0.6       # quiet gap (no message) before the next action
VICTORY_PAUSE = 1.0      # "You won!", before the XP is handed out
XP_FILL_TIME = 1.2       # seconds for an XP bar to fill completely
XP_MESSAGE_TIME = 0.8    # after a party member's XP bar has filled
LEVEL_UP_TIME = 1.2      # "grew to Lv6!"
EVOLVE_INTRO_TIME = 1.5  # "What? Bulbasaur is evolving!"
EVOLVE_TIME = 4.0        # flashing between the old and the new form
EVOLVE_MESSAGE_TIME = 2.0  # "evolved into Ivysaur!" / "stopped evolving!"
HIT_TIME = 0.35      # seconds a hit combatant shakes and flickers
HEAL_TIME = 0.8      # seconds healing sparkles rise around a combatant
FADE_TIME = 0.5      # seconds a fainting combatant takes to fade
HP_DRAIN_TIME = 0.6  # seconds for an HP bar to drain completely
POPUP_TIME = 0.9     # seconds a damage number stays up
FAINTED_OPACITY = 0.35  # fainted party members stay visible, dimmed

# Feet positions for the player's side, by party size: a diagonal column, as
# in the classic Final Fantasy games. Enemies use the mirror image.
PARTY_SLOTS = {
    1: [(492, 205)],
    2: [(472, 180), (512, 236)],
    3: [(452, 160), (492, 200), (532, 240)],
    # Bigger groups (bosses) stand in two staggered lines.
    4: [(450, 170), (490, 232), (540, 160), (580, 222)],
    5: [(440, 160), (470, 205), (500, 250), (555, 180), (590, 232)],
}


class Combatant:
    """A Pokémon taking part in a battle: where it stands, what it is
    animating, and its battle-only state (stat stages, shield, charging,
    Leech Seed, ...)."""

    def __init__(self, monster: Monster, label: str, pos: tuple[int, int], enemy: bool):
        self.monster = monster
        self.label = label
        self.x, self.feet_y = pos
        self.enemy = enemy
        self.anims = animations(monster.species, monster.scale)
        self.anim = self.anims["idle"]
        self.anim_time = 0.0
        self.step = 0.0        # how far it has stepped forward, towards the other side
        self.step_goal = 0.0
        self.hit_time = 0.0    # > 0 while shaking from a hit
        self.heal_time = 0.0   # > 0 while healing sparkles show
        self.opacity = 1.0 if monster.alive else FAINTED_OPACITY
        self.shown_hp = float(monster.hp)  # drains towards the real HP
        self.stages = dict.fromkeys(STAGE_STATS, 0)  # -6 … +6 (Growth, Growl, ...)
        self.shield = 0        # rounds of Leaf Shield left
        self.charging: Action | None = None  # a charged move that fires next round
        self.recharging = False  # after Hyper Beam: rests next round
        self.seeded_by: Combatant | None = None  # Leech Seed: who gets the drained HP ...
        self.seed = 0.0                           # ... and what share of max HP each round
        self.toxic = 0         # badly poisoned: poison damage is toxic/16 of max HP, growing
        self.confused = 0      # turns of confusion left
        self.flinched = False  # loses its turn this round (hit by a flinching move first)
        self.focused = False   # Focus Energy: crit chance ×4
        self.bound = 0         # rounds left bound by Wrap/Clamp ...
        self.bind_share = 0.0  # ... losing this share of max HP each round
        self.berry_used = False  # its berry can be eaten once per battle
        self.evolving: Animation | None = None  # the new form's idle pose, while evolving
        self.evolve_time = 0.0
        self.shown_xp = self.xp_goal = self.xp_fraction  # the XP bar fills towards its goal

    @property
    def alive(self) -> bool:
        return self.monster.alive

    @property
    def status(self) -> str:
        return self.monster.status

    @property
    def can_choose(self) -> bool:
        """Alive, not busy charging a move or recharging, and awake (asleep
        or frozen Pokémon don't get to pick anything)."""
        return (self.alive and self.charging is None and not self.recharging
                and self.status not in ("sleep", "freeze"))

    @property
    def speed(self) -> float:
        speed = self.monster.speed * stage_factor(self.stages["speed"])
        return speed * PARALYSIS_SPEED if self.status == "paralysis" else speed

    @property
    def xp_fraction(self) -> float:
        """How far it is from its level to the next."""
        done, needed = self.monster.xp_progress
        return done / needed if needed else 0.0

    def fill_xp(self, goal: float) -> float:
        """Let the XP bar fill up to `goal`; returns how long that takes."""
        self.xp_goal = goal
        return max(0.0, goal - self.shown_xp) * XP_FILL_TIME

    def revive(self, hp: int) -> None:
        """Back on its feet, with its battle-only state and status cleared."""
        self.monster.hp = hp
        self.monster.cure()
        self.stages = dict.fromkeys(STAGE_STATS, 0)
        self.shield, self.charging, self.recharging = 0, None, False
        self.seeded_by, self.seed, self.toxic = None, 0.0, 0
        self.confused, self.flinched, self.focused, self.bound = 0, False, False, 0

    @property
    def flip(self) -> bool:
        return not self.enemy  # sprites face right; the party faces left

    @property
    def draw_x(self) -> float:
        shake = math.sin(self.hit_time * 70) * 2 if self.hit_time else 0.0
        return self.x + (self.step if self.enemy else -self.step) + shake

    @property
    def sprite_feet_y(self) -> int:
        return self.feet_y + self.monster.species.foot_sink

    @property
    def body_rect(self) -> pygame.Rect:
        """The standing pose's body, at its place in line (for cursors, effects)."""
        return self.anims["idle"].body_rect(0, self.x, self.sprite_feet_y, self.flip)

    def play(self, anim: Animation) -> None:
        self.anim, self.anim_time = anim, 0.0

    def stand(self) -> None:
        self.play(self.anims["idle"])

    def update(self, dt: float) -> None:
        self.anim_time += dt
        self.step += (self.step_goal - self.step) * min(1.0, dt * 14)
        self.hit_time = max(0.0, self.hit_time - dt)
        self.heal_time = max(0.0, self.heal_time - dt)
        if not self.hit_time:  # a fainting hit finishes shaking before the fade
            goal = 1.0 if self.alive else 0.0 if self.enemy else FAINTED_OPACITY
            rate = dt / FADE_TIME
            self.opacity += max(-rate, min(rate, goal - self.opacity))
        drain = self.monster.max_hp * dt / HP_DRAIN_TIME
        self.shown_hp += max(-drain, min(drain, self.monster.hp - self.shown_hp))
        self.shown_xp = min(self.xp_goal, self.shown_xp + dt / XP_FILL_TIME)
        if self.evolving:
            self.evolve_time += dt

    def draw(self, surface: pygame.Surface, shadow_color) -> None:
        if self.opacity <= 0:
            return
        x = self.draw_x
        if self.alive:
            shadow = pygame.Rect(0, 0, round(self.body_rect.w * 0.8), 8)
            shadow.center = (round(x), self.feet_y)
            pygame.draw.ellipse(surface, shadow_color, shadow)
        if self.evolving:
            self._draw_evolving(surface)
            return
        if self.hit_time and int(self.hit_time * 30) % 2:
            return  # flicker
        i = self.anim.index_at(self.anim_time)
        frame = self.anim.frame(i, self.flip)
        if self.opacity < 1:
            frame = frame.copy()
            frame.set_alpha(round(255 * self.opacity))
        box = self.anim.place(i, x, self.sprite_feet_y, self.flip)
        surface.blit(frame, box)
        hats.draw_worn(surface, self.monster, self.anim, i, box, self.flip, round(255 * self.opacity))
        if self.shield and self.alive:
            self._draw_shield(surface)
        if self.heal_time:
            self._draw_sparkles(surface)

    def _draw_evolving(self, surface: pygame.Surface) -> None:
        """A white silhouette switching between the old and the new form,
        faster and faster (from 1 to 10 times a second)."""
        t = self.evolve_time
        cycles = t + 1.125 * t * t
        anim = self.evolving if math.sin(cycles * 2 * math.pi) > 0 else self.anims["idle"]
        box = anim.place(0, self.draw_x, self.sprite_feet_y, self.flip)
        surface.blit(_silhouette(anim.frame(0, self.flip)), box)

    def _draw_sparkles(self, surface: pygame.Surface) -> None:
        """Small crosses rising up through the body while it heals."""
        t = 1 - self.heal_time / HEAL_TIME  # 0 → 1
        body = self.body_rect
        for i in range(6):
            phase = (t * 1.6 + i / 6) % 1.0
            x = round(self.draw_x + math.sin(i * 2.4) * body.w * 0.4)
            y = round(body.bottom - phase * (body.h + 8))
            color = HEAL_COLOR if i % 2 else ui.WHITE
            pygame.draw.line(surface, color, (x - 2, y), (x + 2, y))
            pygame.draw.line(surface, color, (x, y - 2), (x, y + 2))

    def _draw_shield(self, surface: pygame.Surface) -> None:
        bubble = self.body_rect.inflate(14, 10)
        bubble.centerx = round(self.draw_x)
        layer = pygame.Surface(bubble.size, pygame.SRCALPHA)
        pygame.draw.ellipse(layer, (150, 240, 140, 50), layer.get_rect())
        pygame.draw.ellipse(layer, (200, 255, 190, 150), layer.get_rect(), 1)
        surface.blit(layer, bubble)


def _hit_count(move: Move) -> int:
    """How many times a move hits this use: 2-5 times as in Gen 1 (2 or 3
    each 3/8 of the time, 4 or 5 each 1/8)."""
    lo, hi = move.hits
    if lo == hi:
        return lo
    weights = {2: 3, 3: 3, 4: 1, 5: 1}
    counts = list(range(lo, hi + 1))
    return random.choices(counts, weights=[weights.get(n, 1) for n in counts])[0]


_silhouettes: dict[pygame.Surface, pygame.Surface] = {}


def _silhouette(frame: pygame.Surface) -> pygame.Surface:
    """`frame` in plain white."""
    if frame not in _silhouettes:
        _silhouettes[frame] = pygame.mask.from_surface(frame).to_surface(setcolor=(255, 255, 255, 255),
                                                                         unsetcolor=(0, 0, 0, 0))
    return _silhouettes[frame]


Choice = Move | Medicine  # what a combatant can do on its turn


@dataclass
class Action:
    """What one combatant will do this round. No choice: it couldn't pick
    one (asleep or frozen), but still gets a turn to wake up or thaw."""
    user: Combatant
    choice: Choice | None
    target: Combatant
    first: bool = False  # gear (Quick Claw) lets it move before the others this round


@dataclass
class Popup:
    """A number or word that bounces up from a combatant (damage, "ATK UP")."""
    text: str
    pos: tuple[float, float]  # logical, bottom centre
    color: tuple[int, int, int]
    t: float = 0.0

    @property
    def lift(self) -> float:
        """Height above `pos`: a bounce that settles."""
        return abs(math.sin(self.t * 9)) * 12 * math.exp(-self.t * 4)


def _labels(monsters: list[Monster]) -> list[str]:
    """Names, with A, B, ... added when a species appears more than once."""
    counts = Counter(m.name for m in monsters)
    seen: Counter = Counter()
    labels = []
    for m in monsters:
        if counts[m.name] > 1:
            labels.append(f"{m.name} {chr(ord('A') + seen[m.name])}")
            seen[m.name] += 1
        else:
            labels.append(m.name)
    return labels


def _side(monsters: list[Monster], enemy: bool) -> list[Combatant]:
    slots = PARTY_SLOTS[len(monsters)]
    if enemy:
        slots = [(settings.LOGICAL_SIZE[0] - x, y) for x, y in slots]
    return [Combatant(m, label, pos, enemy)
            for m, label, pos in zip(monsters, _labels(monsters), slots)]


@cache
def _background(b: Backdrop) -> pygame.Surface:
    w, _ = settings.LOGICAL_SIZE
    bg = pygame.Surface((w, PANEL_Y))
    for y in range(HORIZON_Y):
        t = y / HORIZON_Y
        pygame.draw.line(bg, [round(a + (c - a) * t) for a, c in zip(b.sky_top, b.sky_bottom)], (0, y), (w, y))
    # Distant hills along the horizon.
    for cx, rw, rh, color in [(80, 260, 60, b.hills[0]), (330, 320, 44, b.hills[1]), (560, 280, 70, b.hills[0])]:
        pygame.draw.ellipse(bg, color, (cx - rw // 2, HORIZON_Y - rh // 2, rw, rh))
    # The field, with stripes spaced further apart towards the viewer.
    for y in range(HORIZON_Y, PANEL_Y):
        t = (y - HORIZON_Y) / (PANEL_Y - HORIZON_Y)
        pygame.draw.line(bg, [round(a + (c - a) * t) for a, c in zip(b.field_far, b.field_near)], (0, y), (w, y))
    y, gap = HORIZON_Y + 4, 4.0
    while y < PANEL_Y:
        pygame.draw.line(bg, b.stripe, (0, round(y)), (w, round(y)))
        y += gap
        gap *= 1.35
    return bg


class BattleScene(Scene):
    """Runs the menus and the rounds.

    Menus (`self.menu`):
      command  Fight / Skills / Item / Run for the current party member
      skills   the member's moves
      items    medicine from the bag
      target   pick who the chosen move or item is aimed at
      busy     a script is playing (intro, or the round's actions)
      end      one side has no Pokémon left standing

    Scripts are generators that change the scene and yield how many seconds
    to wait before they continue.
    """

    def __init__(self, return_to: Scene, party: list[Monster], enemies: list[Monster], bag: Bag,
                 loot: LootTable | None = None, backdrop: Backdrop = MEADOW_BACKDROP, boss: bool = False):
        self.return_to = return_to
        self.backdrop = backdrop
        self.boss = boss  # the area's boss group (changes the intro)
        self.party = _side(party, enemy=False)
        self.enemies = _side(enemies, enemy=True)
        self.bag = bag
        self.loot = loot or wild_loot()  # rolled once per enemy when the party wins (at its level)
        self.rewards: ui.ListPanel | None = None
        self.command = 0        # cursor positions
        self.skill = 0
        self.item = 0
        self.item_top = 0   # first item shown, when the list scrolls
        self.target = 0
        self.aim: Choice | None = None  # the move or item being aimed in the target menu
        self.aim_from = "command"       # menu to go back to from the target menu
        self.blink = 0.0
        self.actions: list[Action] = []
        self.actor_index = 0
        self.message = ""
        self.popups: list[Popup] = []
        self.won = False
        self.stop_evolving = False  # X pressed while a party member evolves
        self.lost = False  # the whole party fainted (running away is neither)
        self.menu = "busy"
        self.wait = 0.0
        self.script = self._intro()

    @property
    def everyone(self) -> list[Combatant]:
        return self.party + self.enemies

    # ------------------------------------------------------------- choosing

    @property
    def actor(self) -> Combatant:
        """The party member choosing an action."""
        return self.party[self.actor_index]

    @property
    def choosing(self) -> bool:
        return self.menu in ("command", "skills", "items", "target")

    def _available(self, medicine: Medicine) -> int:
        """How many are left in the bag, minus those already picked this round."""
        picked = sum(1 for a in self.actions if a.choice is medicine)
        return self.bag.medicine[medicine.name] - picked

    def _medicine(self) -> list[Medicine]:
        """The medicine the current party member can pick from."""
        return [m for m in MEDICINE.values() if self._available(m) > 0]

    def _start_round(self) -> None:
        self.actions = []
        self.actor_index = -1
        self._next_actor()

    def _next_actor(self) -> None:
        """Move on to the next party member who can choose, or start the round."""
        i = self.actor_index + 1
        while i < len(self.party) and not self.party[i].can_choose:
            i += 1
        if i == len(self.party):
            self._run_round()
        else:
            self.actor_index, self.menu = i, "command"
            self.skill = self.item = self.item_top = 0

    def _previous_actor(self) -> None:
        """Undo the last chosen action and let that party member choose again."""
        if self.actions:
            self.actor_index = self.party.index(self.actions.pop().user)
            self.menu = "command"

    def _candidates(self, user: Combatant, choice: Choice) -> list[Combatant]:
        """Who `user` can aim `choice` at."""
        own_side = self.enemies if user.enemy else self.party
        if isinstance(choice, Medicine):  # own side; Revive only on the fainted
            return [c for c in own_side if c.alive != choice.revive]
        if choice.target == "self":
            return [user] if user.alive else []
        side = own_side if choice.target == "ally" else self.party if user.enemy else self.enemies
        return [c for c in side if c.alive]

    def _targets(self) -> list[Combatant]:
        return self._candidates(self.actor, self.aim)

    def _choose(self, choice: Choice) -> None:
        targets = self._candidates(self.actor, choice)
        if isinstance(choice, Move) and (choice.target == "self" or choice.spread):
            if targets:  # nothing to aim
                self._commit(choice, targets[0])
            return
        if not targets:
            return  # e.g. a Revive with nobody fainted
        self.aim_from, self.aim, self.menu = self.menu, choice, "target"
        self.blink = 0.0
        self.target = targets.index(self.actor) if self.actor in targets else 0

    def _commit(self, choice: Choice, target: Combatant) -> None:
        self.actions.append(Action(self.actor, choice, target))
        self._next_actor()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        up = key in (pygame.K_UP, pygame.K_LEFT)
        down = key in (pygame.K_DOWN, pygame.K_RIGHT)
        if self.menu == "command":
            if key in (pygame.K_UP, pygame.K_DOWN):
                self.command = (self.command + (1 if key == pygame.K_DOWN else -1)) % len(COMMANDS)
            elif key in CONFIRM_KEYS:
                command = COMMANDS[self.command]
                if command == "Fight":
                    self._choose(self.actor.monster.basic_attack)
                elif command == "Skills" and self.actor.monster.moves:
                    self.menu = "skills"
                elif command == "Item" and self._medicine():
                    self.menu = "items"
                elif command == "Run":
                    self.next_scene = Transition(self, self.return_to, flashes=0)
            elif key in CANCEL_KEYS:
                self._previous_actor()
        elif self.menu == "skills":
            moves = self.actor.monster.moves
            if key in (pygame.K_UP, pygame.K_DOWN):
                self.skill = (self.skill + (1 if key == pygame.K_DOWN else -1)) % len(moves)
            elif key in CONFIRM_KEYS:
                self._choose(moves[self.skill])
            elif key in CANCEL_KEYS:
                self.menu = "command"
        elif self.menu == "items":
            medicine = self._medicine()
            if key in (pygame.K_UP, pygame.K_DOWN):
                self.item = (self.item + (1 if key == pygame.K_DOWN else -1)) % len(medicine)
                # Scroll to keep the cursor in view.
                self.item_top = min(self.item, max(self.item_top, self.item - LIST_ROWS + 1))
            elif key in CONFIRM_KEYS:
                self._choose(medicine[self.item])
            elif key in CANCEL_KEYS:
                self.menu = "command"
        elif self.menu == "target":
            targets = self._targets()
            if up or down:
                self.target = (self.target + (1 if down else -1)) % len(targets)
                self.blink = 0.0
            elif key in CONFIRM_KEYS:
                self._commit(self.aim, targets[self.target])
            elif key in CANCEL_KEYS:
                self.menu = self.aim_from
        elif self.menu == "evolving" and key in CANCEL_KEYS:
            self.stop_evolving = True
        elif self.menu == "end" and key in CONFIRM_KEYS:
            if not self.won:
                # Until defeat is handled properly: heal up so the next
                # battle doesn't start with a fainted party.
                for c in self.party:
                    c.monster.hp = c.monster.max_hp
                    c.monster.cure()
            self.next_scene = Transition(self, self.return_to, flashes=0)

    # ---------------------------------------------------------------- scripts

    def _intro(self):
        if self.boss:
            first = self.enemies[0]
            giant = "giant " if first.monster.scale > 1 else ""
            self.message = (f"A {giant}{first.label} blocks the way!" if len(self.enemies) == 1
                            else f"A {giant}{first.label} and its escort block the way!")
        elif len(self.enemies) == 1:
            self.message = f"A wild {self.enemies[0].label} appeared!"
        else:
            self.message = "Wild Pokémon appeared!"
        yield 1.2
        self.message = ""
        for c in self.everyone:  # e.g. a status from the last battle, cured by a berry
            yield from self._berry(c)
        self.message = ""
        self._start_round()

    def _enemy_action(self, enemy: Combatant) -> Action:
        # Random for now; smarter choices can go here later.
        move = random.choice([enemy.monster.basic_attack] + enemy.monster.moves)
        return Action(enemy, move, random.choice(self._candidates(enemy, move)))

    def _run_round(self) -> None:
        actions = list(self.actions)  # the party's choices
        for c in self.everyone:
            if not c.alive:
                continue
            if c.charging:
                actions.append(c.charging)
            elif not c.can_choose:
                actions.append(Action(c, None, c))  # asleep, frozen or recharging
            elif c.enemy:
                actions.append(self._enemy_action(c))
        # Items first, as in the main games; then those whose gear lets them
        # move first; then fastest first. Ties are settled at random.
        for a in actions:
            a.first = random.random() * 100 < a.user.monster.gear_bonus("first")
        actions.sort(key=lambda a: (not isinstance(a.choice, Medicine),
                                    -a.choice.priority if isinstance(a.choice, Move) else 0,
                                    not a.first, -a.user.speed, random.random()))
        for a in actions:  # only worth a mention if it got ahead of someone faster
            a.first = a.first and any(not b.first and b.user.speed > a.user.speed for b in actions)
        self.menu = "busy"
        self.script = self._round(actions)

    def _over(self) -> bool:
        return not any(c.alive for c in self.party) or not any(c.alive for c in self.enemies)

    def _round(self, actions: list[Action]):
        yield ROUND_START_PAUSE
        first = True
        for action in actions:
            if self._over():
                break
            if not action.user.alive:
                continue
            if not first:
                self.message = ""
                yield ACTION_PAUSE
            first = False
            if action.first and action.choice is not None and not isinstance(action.choice, Medicine):
                self.message = f"{action.user.label} is quick to act!"
                self._popup(action.user, "QUICK", ui.YELLOW)
                yield QUICK_MESSAGE_TIME
            yield from self._perform(action)
        self.message = ""
        if not self._over():
            yield from self._status_damage()
        if not self._over():
            yield from self._leech()
        if not self._over():
            yield from self._bind()
        if not self._over():
            yield from self._regen()
        self.message = ""
        for c in self.everyone:
            c.shield = max(0, c.shield - 1)
            c.flinched = False
        if self._over():
            self.won = any(c.alive for c in self.party)
            self.lost = not self.won
            self.message = "You won!" if self.won else "Your party has fainted..."
            if self.won:
                yield VICTORY_PAUSE
                leveled = yield from self._give_xp()
                for c in leveled:  # as in Red/Blue: after the battle, on reaching the level
                    if c.monster.can_evolve:
                        yield from self._evolve(c)
                self.message = "You won!"
                self._give_rewards()
            self.menu = "end"
        else:
            self._start_round()

    def _give_xp(self):
        """Every party member still standing gets the XP of all the enemies.
        Returns the members who leveled up."""
        xp = sum(c.monster.xp_yield for c in self.enemies) * DEV.xp_multiplier
        boost = f" (×{DEV.xp_multiplier})" if DEV.xp_multiplier > 1 else ""
        leveled = []
        for c in self.party:
            m = c.monster
            if not c.alive or m.level >= MAX_LEVEL:
                continue
            self.message = f"{c.label} gained {xp} XP!{boost}"
            m.xp += xp
            while m.can_level_up:
                yield c.fill_xp(1.0)
                m.level_up()
                if c not in leveled:
                    leveled.append(c)
                c.shown_xp = c.xp_goal = 0.0
                self._popup(c, "LEVEL UP", ui.YELLOW)
                self.message = f"{c.label} grew to Lv{m.level}!"
                yield LEVEL_UP_TIME
            yield c.fill_xp(c.xp_fraction)
            yield XP_MESSAGE_TIME
        return leveled

    def _evolve(self, c: Combatant):
        """A script: `c` evolves, unless the player stops it (X), in which
        case it tries again the next time it levels up."""
        m, old_name = c.monster, c.monster.name
        into = SPECIES[m.species.evolution.into]
        self.message = f"What? {c.label} is evolving!"
        yield EVOLVE_INTRO_TIME
        c.evolving, c.evolve_time = animations(into)["idle"], 0.0
        self.menu, self.stop_evolving = "evolving", False
        while c.evolve_time < EVOLVE_TIME and not self.stop_evolving:
            yield 0.02
        c.evolving = None
        self.menu = "busy"
        if self.stop_evolving:
            self.message = f"Huh? {c.label} stopped evolving!"
            yield EVOLVE_MESSAGE_TIME
            return
        old_label = c.label
        m.evolve()
        c.anims = animations(m.species)
        c.stand()
        c.label = c.label.replace(old_name, m.name)
        c.heal_time = HEAL_TIME  # sparkles
        self.message = f"{old_label} evolved into {m.name}!"
        yield EVOLVE_MESSAGE_TIME

    def _give_rewards(self) -> None:
        rewards = merge([r for e in self.enemies for r in self.loot.roll(level=e.monster.level)])
        for r in rewards:
            r.give(self.bag)
        if rewards:
            self.rewards = ui.ListPanel("Rewards", [r.row() for r in rewards], (320, 120), footer="")

    def _regen(self):
        """End of the round: gear that restores HP every round."""
        for c in self.everyone:
            percent = c.monster.gear_bonus("regen")
            if not c.alive or not percent or c.monster.hp == c.monster.max_hp:
                continue
            amount = self._heal(c, max(1, round(c.monster.max_hp * percent / 100)))
            self.message = f"{c.label} restored {amount} HP."
            yield REGEN_MESSAGE_TIME

    def _heal(self, c: Combatant, amount: int) -> int:
        """Restore up to `amount` HP, with a popup; returns what was restored."""
        amount = min(amount, c.monster.max_hp - c.monster.hp)
        c.monster.hp += amount
        c.heal_time = HEAL_TIME
        self._popup(c, f"+{amount}", HEAL_COLOR)
        return amount

    def _berry(self, c: Combatant):
        """A script: `c` eats its berry, if it has one left and needs it now."""
        gear = c.monster.gear.get("berry")
        if not gear or c.berry_used or not c.alive:
            return
        m, mods = c.monster, gear.mods
        if m.status and m.status in gear.item.cures:
            note = STATUSES[m.status].cured.format(c.label)
            m.cure()
        elif "berry_heal" in mods and m.hp * 2 <= m.max_hp:
            amount = self._heal(c, max(1, round(m.max_hp * mods["berry_heal"] / 100)))
            note = f"{c.label} restored {amount} HP!"
        elif "berry_attack" in mods and m.hp * 4 <= m.max_hp and c.stages["attack"] < MAX_STAGE:
            c.stages["attack"] = min(MAX_STAGE, c.stages["attack"] + mods["berry_attack"])
            self._popup(c, "ATK UP", ui.YELLOW)
            note = f"{c.label}'s attack rose!"
        else:
            return
        c.berry_used = True
        self.message = f"{c.label} ate its {gear.item.name}! {note}"
        yield STATUS_MESSAGE_TIME

    def _status_damage(self):
        """End of the round: burned and poisoned Pokémon lose HP."""
        for c in self.everyone:
            if not c.alive or c.status not in ROUND_DAMAGE or (DEV.god_mode and not c.enemy):
                continue
            share = c.toxic / 16 if c.status == "poison" and c.toxic else ROUND_DAMAGE[c.status]
            if c.toxic:
                c.toxic += 1
            amount = min(c.monster.hp, max(1, round(c.monster.max_hp * share)))
            c.monster.hp -= amount
            c.hit_time = HIT_TIME
            status = STATUSES[c.status]
            self._popup(c, str(amount), status.color)
            what = "its burn" if c.status == "burn" else "poison"
            self.message = f"{c.label} is hurt by {what}!"
            yield STATUS_MESSAGE_TIME
            yield from self._berry(c)
            if not c.alive:
                yield from self._faint(c)
            if self._over():
                return

    def _leech(self):
        """End of the round: Leech Seed drains the seeded, and heals whoever
        seeded them (if they're still standing)."""
        for c in self.everyone:
            if not c.alive or not c.seeded_by or (DEV.god_mode and not c.enemy):
                continue
            amount = min(c.monster.hp, max(1, round(c.monster.max_hp * c.seed)))
            c.monster.hp -= amount
            c.hit_time = HIT_TIME
            self._popup(c, str(amount), SEED_COLOR)
            self.message = f"Leech Seed saps {c.label}!"
            seeder = c.seeded_by
            if seeder.alive and seeder.monster.hp < seeder.monster.max_hp:
                self._heal(seeder, amount)
            yield STATUS_MESSAGE_TIME
            yield from self._berry(c)
            if not c.alive:
                yield from self._faint(c)
            if self._over():
                return

    def _can_act(self, user: Combatant):
        """A script: whether `user`'s status lets it act this turn (sleeping,
        frozen or fully paralyzed Pokémon lose their turn)."""
        status = user.status
        if status == "sleep":
            user.monster.sleep_rounds -= 1
            if user.monster.sleep_rounds <= 0:
                user.monster.cure()
                self.message = f"{user.label} woke up!"
            else:
                self.message = f"{user.label} is fast asleep."
        elif status == "freeze":
            if random.random() < THAW_CHANCE:
                user.monster.cure()
                self.message = f"{user.label} thawed out!"
            else:
                self.message = f"{user.label} is frozen solid!"
        elif status == "paralysis" and random.random() < FULLY_PARALYZED:
            self.message = f"{user.label} is fully paralyzed! It can't move!"
        else:
            return (yield from self._confusion(user))
        self._popup(user, STATUSES[status].abbrev, STATUSES[status].color)
        yield STATUS_MESSAGE_TIME
        return False

    def _confusion(self, user: Combatant):
        """A script: whether a confused `user` acts (it may hurt itself instead)."""
        if not user.confused:
            return True
        user.confused -= 1
        if not user.confused:
            self.message = f"{user.label} snapped out of confusion!"
            yield STATUS_MESSAGE_TIME
            return True
        self.message = f"{user.label} is confused!"
        self._popup(user, "CONF", CONFUSED_COLOR)
        yield STATUS_MESSAGE_TIME
        if random.random() >= CONFUSION_SELF_HIT:
            return True
        hurt = 0 if DEV.god_mode and not user.enemy else min(user.monster.hp, damage(user, SELF_HIT, user).damage)
        user.monster.hp -= hurt
        user.hit_time = HIT_TIME
        self._popup(user, str(hurt), ui.WHITE)
        self.message = "It hurt itself in its confusion!"
        yield STATUS_MESSAGE_TIME
        if not user.alive:
            yield from self._faint(user)
        return False

    def _bind(self):
        """End of the round: bound Pokémon (Wrap, Clamp) lose HP."""
        for c in self.everyone:
            if not c.alive or not c.bound:
                continue
            c.bound -= 1
            if DEV.god_mode and not c.enemy:
                continue
            amount = min(c.monster.hp, max(1, round(c.monster.max_hp * c.bind_share)))
            c.monster.hp -= amount
            c.hit_time = HIT_TIME
            self._popup(c, str(amount), ui.WHITE)
            self.message = f"{c.label} is hurt by the bind!" if c.bound else f"{c.label} was freed from the bind!"
            yield STATUS_MESSAGE_TIME
            yield from self._berry(c)
            if not c.alive:
                yield from self._faint(c)
            if self._over():
                return

    def _perform(self, action: Action):
        user, move = action.user, action.choice
        if user.recharging:
            user.recharging = False
            self.message = f"{user.label} must recharge!"
            yield STATUS_MESSAGE_TIME
            return
        if user.flinched and move is not None:
            user.flinched = False
            self.message = f"{user.label} flinched!"
            yield STATUS_MESSAGE_TIME
            return
        if not (yield from self._can_act(user)) or move is None:
            return  # (an action without a choice only ever wakes up or thaws)
        candidates = self._candidates(user, move)
        if not candidates:
            return
        if isinstance(move, Medicine):
            # The planned target may have fainted since; aim at someone else.
            target = action.target if action.target in candidates else random.choice(candidates)
            yield from self._use_item(user, move, target)
            return
        if move.spread:
            targets = candidates
        else:
            targets = [action.target if action.target in candidates else random.choice(candidates)]

        anim = user.anims[user.monster.anim_for(move)]
        charging = bool(move.charge) and user.charging is None
        if move.charge:
            half = len(anim.frames) // 2
            anim = anim.sub(0, half) if charging else anim.sub(half, len(anim.frames))
        self.message = (move.charge.format(user=user.label) if charging
                        else f"{user.label} uses {move.name}!")

        user.step_goal = ATTACK_STEP
        yield WIND_UP_TIME
        user.play(anim)
        impact = max(0, len(anim.frames) - 2) / anim.fps  # the second-to-last frame
        yield impact
        if charging:
            user.charging = Action(user, move, targets[0])
        else:
            user.charging = None
            if self._misses(user, move):
                self.message = f"{user.label}'s attack missed!"
            else:
                self._apply(user, move, targets)
        yield anim.duration - impact + IMPACT_HOLD  # finish, and hold the last frame
        if charging:
            user.play(anim.sub(len(anim.frames) - 1, len(anim.frames), loop=True))  # stay charged
        else:
            user.stand()
        user.step_goal = 0.0
        yield STEP_BACK_TIME
        for c in dict.fromkeys([*targets, user]):  # (the user can faint from recoil)
            yield from self._berry(c)
            if not c.alive:
                yield from self._faint(c)

    @staticmethod
    def _misses(user: Combatant, move: Move) -> bool:
        """Moves only miss when the user's accuracy has been lowered (Sand-Attack)."""
        accuracy = user.stages["accuracy"]
        return accuracy < 0 and not move.sure_hit and random.random() >= stage_factor(accuracy)

    def _faint(self, c: Combatant):
        """A script: `c` has just fainted (which clears its status and seed)."""
        c.monster.cure()
        c.seeded_by, c.toxic, c.confused, c.bound = None, 0, 0, 0
        self.message = f"{c.label} fainted!"
        yield HIT_TIME + FADE_TIME + 0.4

    def _use_item(self, user: Combatant, medicine: Medicine, target: Combatant):
        on = "" if target is user else f" on {target.label}"
        self.message = f"{user.label} uses a {medicine.name}{on}!"
        user.step_goal = ATTACK_STEP
        yield WIND_UP_TIME
        if medicine.has_effect(target.monster):
            self.bag.use_medicine(medicine.name)
            amount = medicine.heal_amount(target.monster)
            notes = []
            if medicine.cures_status(target.monster):
                notes.append(STATUSES[target.status].cured.format(target.label))
                target.monster.cure()
            if medicine.revive:
                target.revive(amount)
                notes.append(f"{target.label} was revived!")
            elif amount:
                target.monster.hp += amount
                notes.insert(0, f"{target.label} recovered {amount} HP!")
            self.message = " ".join(notes)
            target.heal_time = HEAL_TIME
            if amount:
                self._popup(target, f"+{amount}", HEAL_COLOR)
            yield HEAL_TIME
        else:
            self.message = "It won't have any effect."  # and it isn't used up
            yield IMPACT_HOLD
        user.step_goal = 0.0
        yield STEP_BACK_TIME

    def _apply(self, user: Combatant, move: Move, targets: list[Combatant]) -> None:
        """The move lands on each of `targets`; what happened goes in the message."""
        share = move.spread_share if len(targets) > 1 else 1.0
        notes: list[str] = []
        for target in targets:
            notes += self._hit(user, move, target, share) if move.damaging else self._effect(user, move, target)
        if move.heal and user.alive and user.monster.hp < user.monster.max_hp:
            amount = self._heal(user, max(1, round(user.monster.max_hp * move.heal)))
            notes.append(f"{user.label} restored {amount} HP!")
        if move.recharge:
            user.recharging = True
        if move.self_confuse and user.alive and not user.confused:
            user.confused = random.randint(*CONFUSION_ROUNDS)
            self._popup(user, "CONF", CONFUSED_COLOR, offset=(0, -14), delay=0.3)
            notes.append(f"{user.label} became confused due to fatigue!")
        if notes:
            self.message = " ".join(dict.fromkeys(notes))  # (the same note once, for spread moves)

    def _hit(self, user: Combatant, move: Move, target: Combatant, share: float) -> list[str]:
        """A damaging move hits `target` (once, or several times). Returns
        notes for the message."""
        hits = [damage(user, move, target, share) for _ in range(_hit_count(move))]
        hit = Hit(sum(h.damage for h in hits), any(h.crit for h in hits), hits[0].effectiveness,
                  [(t, sum(a for h in hits for u, a in h.added if u == t))
                   for t in dict.fromkeys(u for h in hits for u, _ in h.added)])
        if DEV.god_mode:  # the party takes nothing; enemies go down in one hit
            hit = Hit(target.monster.hp if target.enemy else 0, hit.crit, hit.effectiveness, [])
        dealt = min(hit.total, target.monster.hp)
        endured = (dealt == target.monster.hp and dealt > 0 and not DEV.god_mode
                   and random.random() * 100 < target.monster.gear_bonus("endure"))
        if endured:
            dealt -= 1  # hangs on with 1 HP
        target.monster.hp -= dealt
        if hit.total:
            target.hit_time = HIT_TIME
        if hit.damage:
            self._popup(target, str(hit.damage), ui.YELLOW if hit.crit else ui.WHITE)
        for i, (t, amount) in enumerate(hit.added):  # beside the main number, just after it
            self._popup(target, f"+{amount}", COLORS[t], offset=(28 + 24 * i, 8), delay=0.12 * (i + 1))
        notes = [f"Hit {len(hits)} times!"] if len(hits) > 1 and hit.effectiveness else []
        if hit.crit:
            notes.append("A critical hit!")
        if hit.effectiveness == 0:
            notes.append(f"It doesn't affect {target.label}...")
            return notes
        if hit.effectiveness > 1:
            notes.append("It's super effective!")
        elif hit.effectiveness < 1:
            notes.append("It's not very effective...")
        if endured:
            notes.append(f"{target.label} endured the hit!")
        drain = user.monster.gear_bonus("drain") / 100 + move.drain
        if drain and dealt and user.alive and user.monster.hp < user.monster.max_hp:
            amount = self._heal(user, max(1, round(dealt * drain)))
            notes.append(f"{user.label} drained {amount} HP!")
        if move.recoil and dealt and user.alive and not (DEV.god_mode and not user.enemy):
            recoil = min(user.monster.hp, max(1, round(dealt * move.recoil)))
            user.monster.hp -= recoil
            user.hit_time = HIT_TIME
            self._popup(user, str(recoil), ui.WHITE)
            notes.append(f"{user.label} is hit with recoil!")
        if not target.alive:
            return notes
        # Added effects, each hit rolling its own chance.
        status = self._roll_status(user)
        for _ in hits:
            if not status and move.status and random.random() * 100 < move.status_chance:
                status = move.status
        if status:
            notes.append(self._inflict(target, status, move))
        if move.stages and random.random() * 100 < move.stage_chance:
            notes += [self._change_stage(target, stat, change) for stat, change in move.stages]
        if move.confuse and any(random.random() * 100 < move.confuse for _ in hits):
            notes.append(self._confuse(target))
        if move.flinch and any(random.random() * 100 < move.flinch for _ in hits):
            target.flinched = True  # (only matters if it hasn't moved yet this round)
        if move.bind and not target.bound:
            target.bound, target.bind_share = random.randint(*BIND_ROUNDS), move.bind
            notes.append(f"{target.label} was caught in a bind!")
        return [n for n in notes if n]

    def _effect(self, user: Combatant, move: Move, target: Combatant) -> list[str]:
        """A status move works on `target`. Returns notes for the message."""
        if set(move.immune) & set(target.monster.species.types):
            return [f"It doesn't affect {target.label}..."]
        notes = []
        if move.status:
            if random.random() * 100 < move.status_chance:
                notes.append(self._inflict(target, move.status, move) or f"It didn't affect {target.label}...")
            else:
                notes.append(f"{target.label} avoided it!")
        if move.confuse:
            notes.append(self._confuse(target) if random.random() * 100 < move.confuse
                         else f"{target.label} avoided it!")
        for stat, change in move.stages:
            notes.append(self._change_stage(target, stat, change))
        if move.seed:
            if target.seeded_by:
                notes.append(f"{target.label} is already seeded!")
            else:
                target.seeded_by, target.seed = user, move.seed
                self._popup(target, "SEED", SEED_COLOR)
                notes.append(f"{target.label} was seeded!")
        if move.shield:
            target.shield = move.shield
            self._popup(target, "SHIELD", (150, 240, 140))
            notes.append(f"Leaves protect {target.label}!")
        if move.focus:
            target.focused = True
            self._popup(target, "FOCUS", ui.YELLOW)
            notes.append(f"{target.label} is getting pumped!")
        if move.rest:
            m = target.monster
            m.cure()
            m.hp = m.max_hp
            m.status, m.sleep_rounds = "sleep", REST_ROUNDS
            target.toxic = 0
            target.heal_time = HEAL_TIME
            self._popup(target, "SLP", STATUSES["sleep"].color)
            notes.append(f"{target.label} slept and became healthy!")
        return notes

    def _confuse(self, c: Combatant) -> str:
        if c.confused:
            return f"{c.label} is already confused!"
        c.confused = random.randint(*CONFUSION_ROUNDS)
        self._popup(c, "CONF", CONFUSED_COLOR, offset=(0, -14), delay=0.3)
        return f"{c.label} became confused!"

    def _inflict(self, target: Combatant, status: str, move: Move) -> str:
        """Give `target` a status; returns the message ("" if it didn't take)."""
        if not target.monster.inflict(status):
            return ""
        if status == "sleep":
            target.monster.sleep_rounds += move.sleep_bonus
        badly = status == "poison" and move.toxic
        if badly:
            target.toxic = 1
        info = STATUSES[status]
        self._popup(target, info.abbrev, info.color, offset=(0, -14), delay=0.3)
        return f"{target.label} was badly poisoned!" if badly else info.inflicted.format(target.label)

    def _change_stage(self, c: Combatant, stat: str, change: int) -> str:
        old = c.stages[stat]
        c.stages[stat] = max(-MAX_STAGE, min(MAX_STAGE, old + change))
        name = STAT_NAMES[stat]
        if c.stages[stat] == old:
            return f"{c.label}'s {name} won't go any {'higher' if change > 0 else 'lower'}!"
        rose = change > 0
        self._popup(c, f"{STAT_ABBREV[stat]} {'UP' if rose else 'DOWN'}", ui.YELLOW if rose else (150, 170, 255))
        how = "sharply " if abs(change) > 1 else ""
        return f"{c.label}'s {name} {how}{'rose' if rose else 'fell'}!"

    @staticmethod
    def _roll_status(user: Combatant) -> str:
        """A status `user`'s gear inflicts with this hit, if any."""
        for status in STATUSES:
            if random.random() * 100 < user.monster.gear_bonus(f"status:{status}"):
                return status
        return ""

    def _popup(self, c: Combatant, text: str, color, offset=(0, 0), delay: float = 0.0) -> None:
        body = c.body_rect
        self.popups.append(Popup(text, (body.centerx + offset[0], body.top + 4 + offset[1]), color, -delay))

    def update(self, dt: float) -> None:
        self.blink += dt
        if self.choosing:
            for c in self.party:
                c.step_goal = STEP_FORWARD if c is self.actor else 0.0
        for c in self.everyone:
            c.update(dt)
        for p in self.popups:
            p.t += dt
        self.popups = [p for p in self.popups if p.t < POPUP_TIME]

        if not self.script:
            return
        self.wait -= dt
        while self.script and self.wait <= 0:
            script = self.script
            try:
                self.wait += next(script)
            except StopIteration:
                if self.script is script:  # it may have started the next one
                    self.script = None
        if not self.script:
            self.wait = 0.0  # don't let time spent in the menus count towards the next script

    # ------------------------------------------------------------------- draw

    @property
    def _list_open(self) -> str:
        """"skills" or "items" while that list covers the enemy and command
        windows (also while aiming what was picked from it), else ""."""
        menu = self.aim_from if self.menu == "target" else self.menu
        return menu if menu in ("skills", "items") else ""

    @property
    def _aimed(self) -> Combatant | None:
        """The combatant under the target cursor."""
        return self._targets()[self.target] if self.menu == "target" else None

    @staticmethod
    def _badge_pos(row: int) -> tuple[int, int]:
        return SKILL_WINDOW.x + 118, SKILL_WINDOW.y + PAD + 1 + row * ROW_H

    @staticmethod
    def _party_badge_pos(row: int) -> tuple[int, int]:
        """A status badge, in place of the level."""
        return PARTY_WINDOW.x + 108, PARTY_WINDOW.y + PAD + 1 + row * ROW_H

    @staticmethod
    def _enemy_badge_pos(row: int, row_h: int) -> tuple[int, int]:
        return ENEMY_WINDOW.right - 10 - ui.BADGE_SIZE[0], ENEMY_WINDOW.y + PAD + 1 + row * row_h

    @property
    def _enemy_row_h(self) -> int:
        """Rows in the enemy window squeeze together for big groups."""
        return ROW_H if len(self.enemies) <= 4 else 15

    def _enemy_rows(self) -> list[Combatant]:
        """The enemies listed in the enemy window (fainted ones until faded out)."""
        return [c for c in self.enemies if c.opacity > 0]

    def _hint(self) -> str:
        return {
            "command": "Up/Down: choose   Enter: confirm   X: back",
            "skills": "Up/Down: choose skill   Enter: confirm   X: back",
            "items": "Up/Down: choose item   Enter: confirm   X: back",
            "target": "Arrows: choose target   Enter: confirm   X: back",
        }.get(self.menu, "")

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(ui.SHADOW)
        canvas.blit(_background(self.backdrop), (0, 0))
        for c in sorted(self.everyone, key=lambda c: c.feet_y):
            c.draw(canvas, self.backdrop.shadow)

        for rect in (ENEMY_WINDOW, COMMAND_WINDOW, PARTY_WINDOW):
            ui.window_box(canvas, rect)
        if self.choosing:
            ui.cursor(canvas, COMMAND_WINDOW.x + 16, COMMAND_WINDOW.y + PAD + 5 + self.command * ROW_H)
        if self._list_open:
            ui.window_box(canvas, SKILL_WINDOW)
            row = self.skill if self._list_open == "skills" else self.item - self.item_top
            ui.cursor(canvas, SKILL_WINDOW.x + 16, SKILL_WINDOW.y + PAD + 5 + row * ROW_H)
        if self._list_open == "items":  # scroll arrows
            x = SKILL_WINDOW.right - 10
            if self.item_top > 0:
                pygame.draw.polygon(canvas, ui.WHITE, [(x - 3, SKILL_WINDOW.y + 9), (x + 3, SKILL_WINDOW.y + 9),
                                                       (x, SKILL_WINDOW.y + 5)])
            if self.item_top + LIST_ROWS < len(self._medicine()):
                y = SKILL_WINDOW.bottom - 9
                pygame.draw.polygon(canvas, ui.WHITE, [(x - 3, y), (x + 3, y), (x, y + 4)])
        if self._list_open == "skills":
            for i, move in enumerate(self.actor.monster.moves):
                if move.type:
                    ui.badge(canvas, self._badge_pos(i), COLORS[move.type])
        if self.menu == "items":
            ui.window_box(canvas, INFO_WINDOW)
        for i, c in enumerate(self.party):
            bar = pygame.Rect(PARTY_WINDOW.x + 168, PARTY_WINDOW.y + PAD + 3 + i * ROW_H, 90, 6)
            ui.hp_bar(canvas, bar, c.shown_hp / c.monster.max_hp)
            ui.bar(canvas, pygame.Rect(bar.x, bar.bottom + 1, bar.w, 4), c.shown_xp, XP_COLOR)
            if c.status:
                ui.badge(canvas, self._party_badge_pos(i), STATUSES[c.status].color)
        if not self._list_open:
            for i, c in enumerate(self._enemy_rows()):
                if c.status:
                    ui.badge(canvas, self._enemy_badge_pos(i, self._enemy_row_h), STATUSES[c.status].color)

        aimed = self._aimed
        if aimed and self.blink % 0.5 < 0.35:
            body = aimed.body_rect
            ui.cursor(canvas, body.left - 3, body.centery)
        if self.message:
            ui.window_box(canvas, MESSAGE_WINDOW)
        if self.rewards:
            self.rewards.draw(canvas)

    def draw_overlay(self, window: pygame.Surface) -> None:
        if self.choosing:
            ui.text(window, self._hint(), (8, 6), color=ui.SHADOW, size=22, shadow=False)
        if self.message:
            ui.text(window, self.message, (MESSAGE_WINDOW.x + 12, MESSAGE_WINDOW.y + PAD))
            key_hint = {"end": "Enter: continue", "evolving": "X: stop"}.get(self.menu)
            if key_hint:
                ui.text(window, key_hint, (MESSAGE_WINDOW.right - 12, MESSAGE_WINDOW.y + PAD), ui.GREY,
                        align="right")
        aimed = self._aimed

        if self.rewards:
            self.rewards.draw_overlay(window)
        if self.menu == "items":
            description = self._medicine()[self.item].description
            ui.text(window, description, (INFO_WINDOW.x + 12, INFO_WINDOW.y + PAD))

        if self._list_open == "items":  # covers the enemy and command windows
            shown = self._medicine()[self.item_top:self.item_top + LIST_ROWS]
            for i, medicine in enumerate(shown):
                y = SKILL_WINDOW.y + PAD + i * ROW_H
                ui.text(window, medicine.name, (SKILL_WINDOW.x + 22, y))
                ui.text(window, f"x{self._available(medicine)}", (SKILL_WINDOW.x + 210, y), align="right")
                ui.text(window, "Fainted" if medicine.revive else "Ally", (SKILL_WINDOW.x + 222, y), ui.GREY)
        elif self._list_open == "skills":
            for i, move in enumerate(self.actor.monster.moves):
                y = SKILL_WINDOW.y + PAD + i * ROW_H
                ui.text(window, move.name, (SKILL_WINDOW.x + 22, y))
                if move.type:
                    ui.badge_text(window, type_name(move.type), self._badge_pos(i))
                power = "1/2" if move.halve else str(round(move.power * move.scale)) if move.damaging else "-"
                ui.text(window, power, (SKILL_WINDOW.x + 210, y), align="right")
                aim = SPREAD_TEXT.get(move.target) if move.spread else TARGET_TEXT[move.target]
                ui.text(window, aim, (SKILL_WINDOW.x + 222, y), ui.GREY)
        else:
            for i, c in enumerate(self._enemy_rows()):
                color = ui.YELLOW if c is aimed else ui.WHITE
                row_h = self._enemy_row_h
                y, size = ENEMY_WINDOW.y + PAD + i * row_h, 28 if row_h == ROW_H else 24
                ui.text(window, c.label, (ENEMY_WINDOW.x + 12, y), color, size=size)
                if c.status:  # in place of the level
                    ui.badge_text(window, STATUSES[c.status].abbrev, self._enemy_badge_pos(i, row_h))
                else:
                    ui.text(window, f"Lv{c.monster.level}", (ENEMY_WINDOW.right - 12, y), ui.GREY, size=size,
                            align="right")
            for i, name in enumerate(COMMANDS):
                unavailable = ((name == "Item" and not self._medicine())
                               or (name == "Skills" and self.choosing and not self.actor.monster.moves))
                color = ui.GREY if unavailable else ui.WHITE
                ui.text(window, name, (COMMAND_WINDOW.x + 22, COMMAND_WINDOW.y + PAD + i * ROW_H), color)

        for i, c in enumerate(self.party):
            m, y = c.monster, PARTY_WINDOW.y + PAD + i * ROW_H
            if c is aimed or (self.menu in ("command", "skills", "items") and c is self.actor):
                color = ui.YELLOW
            elif not c.alive:
                color = ui.GREY
            else:
                color = ui.WHITE
            ui.text(window, c.label, (PARTY_WINDOW.x + 12, y), color)
            if c.status:
                ui.badge_text(window, STATUSES[c.status].abbrev, self._party_badge_pos(i))
            else:
                ui.text(window, f"Lv{m.level}", (PARTY_WINDOW.x + 112, y), color)
            ui.text(window, f"{math.ceil(c.shown_hp)}/{m.max_hp}", (PARTY_WINDOW.right - 12, y), color,
                    align="right")

        for p in self.popups:
            if p.t < 0:
                continue  # not shown yet
            ui.text(window, p.text, (p.pos[0], p.pos[1] - 12 - p.lift), p.color, size=32, align="center")
