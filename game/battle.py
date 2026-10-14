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

from . import settings, ui
from .animation import Animation
from .pokemon import FIGHT, Monster, Move, animations
from .scene import Scene, Transition

HORIZON_Y = 118
PANEL_Y = 264  # top of the menu windows

ENEMY_WINDOW = pygame.Rect(6, PANEL_Y, 170, 90)
COMMAND_WINDOW = pygame.Rect(180, PANEL_Y, 104, 90)
PARTY_WINDOW = pygame.Rect(288, PANEL_Y, 346, 90)
SKILL_WINDOW = pygame.Rect(6, PANEL_Y, 278, 90)  # opens over the enemy + command windows
ROW_H = 19   # menu line height
PAD = 9      # space above the first line in a window
MESSAGE_WINDOW = pygame.Rect(6, 6, 628, PAD * 2 + ROW_H)

COMMANDS = ["Fight", "Skills", "Item", "Run"]
DISABLED = {"Item"}  # no items yet
TARGET_TEXT = {"enemy": "Enemy", "ally": "Ally", "self": "Self"}

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
CANCEL_KEYS = (pygame.K_x, pygame.K_BACKSPACE)

STEP_FORWARD = 14    # px the party member choosing a command steps out of line
ATTACK_STEP = 28     # px a combatant steps forward to act

# Pacing of a round, in seconds.
ROUND_START_PAUSE = 0.4  # after the last command is chosen
WIND_UP_TIME = 0.4       # stepping forward, with the move's name shown
IMPACT_HOLD = 0.35       # extra time on the last frame after the hit lands
STEP_BACK_TIME = 0.4     # stepping back into line
ACTION_PAUSE = 0.6       # quiet gap (no message) before the next action
HIT_TIME = 0.35      # seconds a hit combatant shakes and flickers
FADE_TIME = 0.5      # seconds a fainting combatant takes to fade
HP_DRAIN_TIME = 0.6  # seconds for an HP bar to drain completely
POPUP_TIME = 0.9     # seconds a damage number stays up
FAINTED_OPACITY = 0.35  # fainted party members stay visible, dimmed

SHIELD_ROUNDS = 2    # Leaf Shield lasts the round it is used and the next
SHIELD_FACTOR = 0.5  # damage taken while shielded
MAX_ATTACK_STAGE = 6

# Feet positions for the player's side, by party size: a diagonal column, as
# in the classic Final Fantasy games. Enemies use the mirror image.
PARTY_SLOTS = {
    1: [(492, 205)],
    2: [(472, 180), (512, 236)],
    3: [(452, 160), (492, 200), (532, 240)],
}


class Combatant:
    """A Pokémon taking part in a battle: where it stands, what it is
    animating, and its battle-only state (stat boosts, shield, charging)."""

    def __init__(self, monster: Monster, label: str, pos: tuple[int, int], enemy: bool):
        self.monster = monster
        self.label = label
        self.x, self.feet_y = pos
        self.enemy = enemy
        self.anims = animations(monster.species)
        self.anim = self.anims["idle"]
        self.anim_time = 0.0
        self.step = 0.0        # how far it has stepped forward, towards the other side
        self.step_goal = 0.0
        self.hit_time = 0.0    # > 0 while shaking from a hit
        self.opacity = 1.0 if monster.alive else FAINTED_OPACITY
        self.shown_hp = float(monster.hp)  # drains towards the real HP
        self.attack_stage = 0  # raised by Growth
        self.shield = 0        # rounds of Leaf Shield left
        self.charging: Action | None = None  # a charged move that fires next round

    @property
    def alive(self) -> bool:
        return self.monster.alive

    @property
    def can_choose(self) -> bool:
        return self.alive and self.charging is None

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
        if not self.hit_time:  # a fainting hit finishes shaking before the fade
            goal = 1.0 if self.alive else 0.0 if self.enemy else FAINTED_OPACITY
            rate = dt / FADE_TIME
            self.opacity += max(-rate, min(rate, goal - self.opacity))
        drain = self.monster.max_hp * dt / HP_DRAIN_TIME
        self.shown_hp += max(-drain, min(drain, self.monster.hp - self.shown_hp))

    def draw(self, surface: pygame.Surface) -> None:
        if self.opacity <= 0:
            return
        x = self.draw_x
        if self.alive:
            shadow = pygame.Rect(0, 0, round(self.body_rect.w * 0.8), 8)
            shadow.center = (round(x), self.feet_y)
            pygame.draw.ellipse(surface, (60, 110, 50), shadow)
        if self.hit_time and int(self.hit_time * 30) % 2:
            return  # flicker
        i = self.anim.index_at(self.anim_time)
        frame = self.anim.frame(i, self.flip)
        if self.opacity < 1:
            frame = frame.copy()
            frame.set_alpha(round(255 * self.opacity))
        surface.blit(frame, self.anim.place(i, x, self.sprite_feet_y, self.flip))
        if self.shield and self.alive:
            self._draw_shield(surface)

    def _draw_shield(self, surface: pygame.Surface) -> None:
        bubble = self.body_rect.inflate(14, 10)
        bubble.centerx = round(self.draw_x)
        layer = pygame.Surface(bubble.size, pygame.SRCALPHA)
        pygame.draw.ellipse(layer, (150, 240, 140, 50), layer.get_rect())
        pygame.draw.ellipse(layer, (200, 255, 190, 150), layer.get_rect(), 1)
        surface.blit(layer, bubble)


@dataclass
class Action:
    """What one combatant will do this round."""
    user: Combatant
    move: Move
    target: Combatant


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


def damage(user: Combatant, move: Move, target: Combatant) -> int:
    """The Gen 1 damage formula, simplified (no types, crits or misses)."""
    attack = user.monster.attack * (2 + user.attack_stage) / 2
    level_factor = 2 * user.monster.level / 5 + 2
    amount = level_factor * move.power * attack / target.monster.defense / 50 + 2
    if target.shield:
        amount *= SHIELD_FACTOR
    return max(1, round(amount * random.uniform(0.85, 1.0)))


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
def _background() -> pygame.Surface:
    w, _ = settings.LOGICAL_SIZE
    bg = pygame.Surface((w, PANEL_Y))
    sky_top, sky_bottom = (104, 168, 232), (196, 228, 244)
    for y in range(HORIZON_Y):
        t = y / HORIZON_Y
        pygame.draw.line(bg, [round(a + (b - a) * t) for a, b in zip(sky_top, sky_bottom)], (0, y), (w, y))
    # Distant hills along the horizon.
    for cx, rw, rh, color in [(80, 260, 60, (120, 176, 112)), (330, 320, 44, (104, 160, 100)),
                              (560, 280, 70, (120, 176, 112))]:
        pygame.draw.ellipse(bg, color, (cx - rw // 2, HORIZON_Y - rh // 2, rw, rh))
    # The field, with stripes spaced further apart towards the viewer.
    field_far, field_near = (112, 184, 88), (84, 160, 68)
    for y in range(HORIZON_Y, PANEL_Y):
        t = (y - HORIZON_Y) / (PANEL_Y - HORIZON_Y)
        pygame.draw.line(bg, [round(a + (b - a) * t) for a, b in zip(field_far, field_near)], (0, y), (w, y))
    y, gap = HORIZON_Y + 4, 4.0
    while y < PANEL_Y:
        pygame.draw.line(bg, (96, 168, 76), (0, round(y)), (w, round(y)))
        y += gap
        gap *= 1.35
    return bg


class BattleScene(Scene):
    """Runs the menus and the rounds.

    Menus (`self.menu`):
      command  Fight / Skills / Item / Run for the current party member
      skills   the member's moves
      target   pick who the chosen move is aimed at
      busy     a script is playing (intro, or the round's actions)
      end      one side has no Pokémon left standing

    Scripts are generators that change the scene and yield how many seconds
    to wait before they continue.
    """

    def __init__(self, return_to: Scene, party: list[Monster], enemies: list[Monster]):
        self.return_to = return_to
        self.party = _side(party, enemy=False)
        self.enemies = _side(enemies, enemy=True)
        self.command = 0        # cursor positions
        self.skill = 0
        self.target = 0
        self.move: Move | None = None   # the move being aimed in the target menu
        self.aim_from = "command"       # menu to go back to from the target menu
        self.blink = 0.0
        self.actions: list[Action] = []
        self.actor_index = 0
        self.message = ""
        self.popups: list[Popup] = []
        self.won = False
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
        return self.menu in ("command", "skills", "target")

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
            self.actor_index, self.menu, self.skill = i, "command", 0

    def _previous_actor(self) -> None:
        """Undo the last chosen action and let that party member choose again."""
        if self.actions:
            self.actor_index = self.party.index(self.actions.pop().user)
            self.menu = "command"

    def _candidates(self, user: Combatant, move: Move) -> list[Combatant]:
        """Who `user` can aim `move` at."""
        if move.target == "self":
            return [user] if user.alive else []
        other_side = move.target == "enemy"
        side = self.party if user.enemy == other_side else self.enemies
        return [c for c in side if c.alive]

    def _targets(self) -> list[Combatant]:
        return self._candidates(self.actor, self.move)

    def _choose(self, move: Move) -> None:
        if move.target == "self":
            self._commit(move, self.actor)
            return
        self.aim_from, self.move, self.menu = self.menu, move, "target"
        targets = self._targets()
        self.target = targets.index(self.actor) if self.actor in targets else 0

    def _commit(self, move: Move, target: Combatant) -> None:
        self.actions.append(Action(self.actor, move, target))
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
                    self._choose(FIGHT)
                elif command == "Skills":
                    self.menu = "skills"
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
        elif self.menu == "target":
            targets = self._targets()
            if up or down:
                self.target = (self.target + (1 if down else -1)) % len(targets)
                self.blink = 0.0
            elif key in CONFIRM_KEYS:
                self._commit(self.move, targets[self.target])
            elif key in CANCEL_KEYS:
                self.menu = self.aim_from
        elif self.menu == "end" and key in CONFIRM_KEYS:
            if not self.won:
                # Until defeat is handled properly: heal up so the next
                # battle doesn't start with a fainted party.
                for c in self.party:
                    c.monster.hp = c.monster.max_hp
            self.next_scene = Transition(self, self.return_to, flashes=0)

    # ---------------------------------------------------------------- scripts

    def _intro(self):
        if len(self.enemies) == 1:
            self.message = f"A wild {self.enemies[0].label} appeared!"
        else:
            self.message = "Wild Pokémon appeared!"
        yield 1.2
        self.message = ""
        self._start_round()

    def _enemy_action(self, enemy: Combatant) -> Action:
        # Random for now; smarter choices can go here later.
        move = random.choice(enemy.monster.moves)
        return Action(enemy, move, random.choice(self._candidates(enemy, move)))

    def _run_round(self) -> None:
        actions = self.actions + [c.charging for c in self.everyone if c.alive and c.charging]
        actions += [self._enemy_action(c) for c in self.enemies if c.can_choose]
        # Fastest first; ties are settled at random.
        actions.sort(key=lambda a: (-a.user.monster.speed, random.random()))
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
            yield from self._perform(action)
        self.message = ""
        for c in self.everyone:
            c.shield = max(0, c.shield - 1)
        if self._over():
            self.won = any(c.alive for c in self.party)
            self.message = "You won!" if self.won else "Your party has fainted..."
            self.menu = "end"
        else:
            self._start_round()

    def _perform(self, action: Action):
        user, move = action.user, action.move
        candidates = self._candidates(user, move)
        if not candidates:
            return
        # The planned target may have fainted since; aim at someone else.
        target = action.target if action.target in candidates else random.choice(candidates)

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
            user.charging = Action(user, move, target)
        else:
            user.charging = None
            self._apply(user, move, target)
        yield anim.duration - impact + IMPACT_HOLD  # finish, and hold the last frame
        if charging:
            user.play(anim.sub(len(anim.frames) - 1, len(anim.frames), loop=True))  # stay charged
        else:
            user.stand()
        user.step_goal = 0.0
        yield STEP_BACK_TIME
        if not target.alive:
            self.message = f"{target.label} fainted!"
            yield HIT_TIME + FADE_TIME + 0.4

    def _apply(self, user: Combatant, move: Move, target: Combatant) -> None:
        if move.power:
            amount = min(damage(user, move, target), target.monster.hp)
            target.monster.hp -= amount
            target.hit_time = HIT_TIME
            self._popup(target, str(amount), ui.WHITE)
        elif move.effect == "attack_up":
            if target.attack_stage < MAX_ATTACK_STAGE:
                target.attack_stage += 1
                self._popup(target, "ATK UP", ui.YELLOW)
                self.message = f"{target.label}'s attack rose!"
            else:
                self.message = f"{target.label}'s attack won't go any higher!"
        elif move.effect == "shield":
            target.shield = SHIELD_ROUNDS
            self._popup(target, "SHIELD", (150, 240, 140))
            self.message = f"Leaves protect {target.label}!"

    def _popup(self, c: Combatant, text: str, color) -> None:
        body = c.body_rect
        self.popups.append(Popup(text, (body.centerx, body.top + 4), color))

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
    def _skills_open(self) -> bool:
        return self.menu == "skills" or (self.menu == "target" and self.aim_from == "skills")

    @property
    def _aimed(self) -> Combatant | None:
        """The combatant under the target cursor."""
        return self._targets()[self.target] if self.menu == "target" else None

    def _hint(self) -> str:
        return {
            "command": "Up/Down: choose   Enter: confirm   X: back",
            "skills": "Up/Down: choose skill   Enter: confirm   X: back",
            "target": "Arrows: choose target   Enter: confirm   X: back",
        }.get(self.menu, "")

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(ui.SHADOW)
        canvas.blit(_background(), (0, 0))
        for c in sorted(self.everyone, key=lambda c: c.feet_y):
            c.draw(canvas)

        for rect in (ENEMY_WINDOW, COMMAND_WINDOW, PARTY_WINDOW):
            ui.window_box(canvas, rect)
        if self.choosing:
            ui.cursor(canvas, COMMAND_WINDOW.x + 16, COMMAND_WINDOW.y + PAD + 5 + self.command * ROW_H)
        if self._skills_open:
            ui.window_box(canvas, SKILL_WINDOW)
            ui.cursor(canvas, SKILL_WINDOW.x + 16, SKILL_WINDOW.y + PAD + 5 + self.skill * ROW_H)
        for i, c in enumerate(self.party):
            bar = pygame.Rect(PARTY_WINDOW.x + 168, PARTY_WINDOW.y + PAD + 3 + i * ROW_H, 90, 6)
            ui.hp_bar(canvas, bar, c.shown_hp / c.monster.max_hp)

        aimed = self._aimed
        if aimed and self.blink % 0.5 < 0.35:
            body = aimed.body_rect
            ui.cursor(canvas, body.left - 3, body.centery)
        if self.message:
            ui.window_box(canvas, MESSAGE_WINDOW)

    def draw_overlay(self, window: pygame.Surface) -> None:
        if self.choosing:
            ui.text(window, self._hint(), (8, 6), color=ui.SHADOW, size=22, shadow=False)
        if self.message:
            ui.text(window, self.message, (MESSAGE_WINDOW.x + 12, MESSAGE_WINDOW.y + PAD))
            if self.menu == "end":
                ui.text(window, "Enter: continue", (MESSAGE_WINDOW.right - 12, MESSAGE_WINDOW.y + PAD),
                        ui.GREY, align="right")
        aimed = self._aimed

        if self._skills_open:  # covers the enemy and command windows
            for i, move in enumerate(self.actor.monster.moves):
                y = SKILL_WINDOW.y + PAD + i * ROW_H
                ui.text(window, move.name, (SKILL_WINDOW.x + 22, y))
                ui.text(window, str(move.power) if move.power else "-", (SKILL_WINDOW.x + 200, y),
                        align="right")
                ui.text(window, TARGET_TEXT[move.target], (SKILL_WINDOW.x + 212, y), ui.GREY)
        else:
            standing = [c for c in self.enemies if c.opacity > 0]  # until faded out
            for i, c in enumerate(standing):
                color = ui.YELLOW if c is aimed else ui.WHITE
                ui.text(window, c.label, (ENEMY_WINDOW.x + 12, ENEMY_WINDOW.y + PAD + i * ROW_H), color)
            for i, name in enumerate(COMMANDS):
                color = ui.GREY if name in DISABLED else ui.WHITE
                ui.text(window, name, (COMMAND_WINDOW.x + 22, COMMAND_WINDOW.y + PAD + i * ROW_H), color)

        for i, c in enumerate(self.party):
            m, y = c.monster, PARTY_WINDOW.y + PAD + i * ROW_H
            if not c.alive:
                color = ui.GREY
            elif c is aimed or (self.menu in ("command", "skills") and c is self.actor):
                color = ui.YELLOW
            else:
                color = ui.WHITE
            ui.text(window, c.label, (PARTY_WINDOW.x + 12, y), color)
            ui.text(window, f"Lv{m.level}", (PARTY_WINDOW.x + 112, y), color)
            ui.text(window, f"{math.ceil(c.shown_hp)}/{m.max_hp}", (PARTY_WINDOW.right - 12, y), color,
                    align="right")

        for p in self.popups:
            ui.text(window, p.text, (p.pos[0], p.pos[1] - 12 - p.lift), p.color, size=32, align="center")
