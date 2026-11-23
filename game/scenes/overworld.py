"""Side-scrolling maps: what every map has (`MapScene`), and the maps of
an instance (`OverworldScene`), such as a route between two towns.

On an instance's maps, touching wild Pokémon starts a battle (beaten ones
are gone for the run), Poké Balls lying around (one item each) and the
rarer chests open with Up, and the doorway at the end of
the map leads on (Up). An instance with a boss ends with a boss group
guarding the doorway out; beating it opens the way and leaves a reward
chest. Towns are in town.py.

A dungeon's rooms (Mt. Moon) have ladders up and down (`Ladder`) to other
rooms and doorways out instead: Up (or Down, at a ladder down) uses them.
"""

import math
from functools import cache
import random

import pygame

from .. import saves, settings
from ..dev import DEV
from ..engine import touch, ui
from ..engine.scene import Scene, Transition
from ..mechanics.items import Range
from ..mechanics.loot import BOSS_GEAR, TRAINER_GEAR, LootTable, ball_loot, boss_loot, chest_loot, dress, wild_loot
from ..mechanics.pokemon import EVOLUTIONS, SPECIES, Monster, animations
from ..world import tileset
from ..world import tower
from ..world.instance import RIVAL_STARTER, RIVAL_STARTER_EVOLVED, Instance, Stair, Trainer
from ..world.level import EMPTY, PLATFORM, SOLID, TILE, Level, Spawn, extra_member
from ..world.player import FOOT_SINK, Controls, Player
from ..world import quests
from ..world.spinners import layout_of
from ..world.progress import Game
from ..world.themes import Palette
from ..world.towns import TOWNS
from . import quest_ui
from .battle import BattleScene
from .gym import TeamPick
from .power_grid import AMBUSH, PowerGrid
from .spinners import SpinnerFloor
from .spores import SporeGarden
from .summary import SummaryScene

HELP = ("Left/Right: walk   Shift: run   Space: jump (hold = higher)   Up: open / go through"
        "   Tab: party   I: bag   Q: quests   Esc: menu")
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z, pygame.K_UP)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE)  # also close a panel (B on touch screens)

WOOD = (150, 96, 48)
OUTLINE = (48, 28, 16)
TRACKED = 3  # active quests shown under the location
EXTRA_FOE_CHANCE = 0.5  # with two fighting: a wild group's chance of one more Pokémon
LADDER_SEGMENT = pygame.Rect(8, 16, 16, 16)  # a repeating stretch of the ladder prop
# A wild group stands as a loose cluster, not a line: each member a share
# of their widths behind the one before (so they overlap), every other one
# in a back row (a little higher, dimmed, drawn behind), with a few px of
# jitter per group (from the map's seed).
GROUP_OVERLAP = 0.55   # × the two members' half-widths added: the step from one to the next
BACK_ROW_LIFT = 5      # px the back row stands higher
BACK_ROW_SHADE = 0.8   # its colours × this
GROUP_JITTER = 3       # px, either way
MIN_SQUEEZE = 0.6      # a group squeezes to as little as this of its spacing to stay on level ground
# A wild group also catches the player this high above its feet (an invisible
# column over it), up to the first tile overhead: so it can't be jumped over
# from the ground, only passed on a platform over it (or jumped from one).
GROUP_REACH = 6 * TILE
FOLK_REACH = 22  # px from someone in a dungeon room within which Up talks to them (as in towns)
EVOLVE_COLOR = (255, 130, 200)  # evolution quests (their marks and tracked steps)
# Marks over what quests need: (symbol, colour).
QUEST_MARK = ("!", ui.YELLOW)    # a quest to take, or the next step's place
EVOLVE_MARK = ("!", EVOLVE_COLOR)  # ... an evolution quest's
HAND_IN_MARK = ("?", ui.YELLOW)  # quests to hand in


def quest_mark(quest: quests.Quest) -> tuple[str, tuple[int, int, int]]:
    return EVOLVE_MARK if quest.evolves else QUEST_MARK


def draw_prompt(surface: pygame.Surface, x: float, top: float, t: float) -> None:
    """A bobbing arrow: press Up here."""
    x, top = round(x), round(top + math.sin(t * 6) * 2)
    for color, d in ((ui.SHADOW, 1), (ui.WHITE, 0)):
        pygame.draw.polygon(surface, color, [(x - 5 + d, top + 6 + d), (x + 5 + d, top + 6 + d), (x + d, top + d)])


class WildPokemon:
    """A group of wild Pokémon on the map, all shown, standing together
    behind the first (a loose cluster: `_placed`). Touching them starts a battle against `encounter`:
    a list of (species, level). A boss group's leader (the first) can be
    drawn `scale` times bigger (on the map and in battle)."""

    def __init__(self, spawn: Spawn, boss: bool = False, scale: int = 1, level: Level | None = None):
        self.spawn = spawn
        self.level = level  # (each member stands on the ground under it)
        self.x, self.ground_y = spawn.x, spawn.feet_y
        self.encounter = spawn.encounter
        self.boss = boss
        self.members = [SPECIES[species] for species, _ in self.encounter]
        self.scales = [scale] + [1] * (len(self.members) - 1)
        self.facing = -1
        # Only trigger once per touch, so returning from a battle (after
        # running away) while still touching them doesn't start another one.
        self.armed = True
        self.trainer: Trainer | None = None  # a route trainer's team, or None (wild)
        rng = random.Random(round(spawn.x * 31 + spawn.feet_y))
        self.jitter = [0.0] + [rng.uniform(-GROUP_JITTER, GROUP_JITTER) for _ in self.members[1:]]
        self._layout: list | None = None  # (worked out once: `_lay_out`)

    def _placed(self):
        """(species, idle animation, x, feet y, back row?) per member, in
        drawing order: the back row first, the leader last (in front; a
        boss first, behind its escort)."""
        if self._layout is None:
            self._layout = self._lay_out()
        return self._layout

    def _lay_out(self) -> list[tuple]:
        """A loose cluster around the leader: the others beside it, by turns
        on either side, every other one in the back row, each a share of
        their widths from the next (`GROUP_OVERLAP`), with a little jitter;
        slid along (and if need be squeezed onto) the level ground under
        the leader, so the group doesn't straddle a step."""
        anims = [animations(sp, scale)["idle"] for sp, scale in zip(self.members, self.scales)]
        widths = [a.frames[0].get_bounding_rect().w for a in anims]
        order = [0]  # members from left to right: the leader in the middle, the others by turns beside it
        for i in range(1, len(anims)):
            order = order + [i] if i % 2 else [i] + order
        xs = [0.0]
        for a, b in zip(order, order[1:]):
            xs.append(xs[-1] + GROUP_OVERLAP * (widths[a] + widths[b]) / 2 + self.jitter[b])
        lead = order.index(0)
        xs = [x - xs[lead] for x in xs]  # the leader at 0
        left, right = xs[0] - widths[order[0]] / 2, xs[-1] + widths[order[-1]] / 2
        lo, hi = self._flat_run()
        if right - left > hi - lo:  # squeeze it (no closer than MIN_SQUEEZE)
            k = max(MIN_SQUEEZE, (hi - lo) / (right - left))
            xs, left, right = [x * k for x in xs], left * k, right * k
        if right - left <= hi - lo:  # slide it onto the level stretch
            shift = min(max(0.0, lo - left), hi - right)
        else:  # (too wide even so: centred on it)
            shift = (lo + hi) / 2 - (left + right) / 2
        spots = []
        for pos, i in enumerate(order):
            x = self.x + xs[pos] + shift
            ground = self.level.ground_y(x) if self.level and not self.boss else self.ground_y
            # The leader's neighbours stand behind it; a boss looms behind its escort instead.
            back = abs(pos - lead) % 2 == 1 and not self.boss
            # (sunk into the ground like the player, `FOOT_SINK`: the sheets' feet are drawn at a 3/4 angle)
            feet = ground + (self.members[i].foot_sink + FOOT_SINK) * self.scales[i] - (BACK_ROW_LIFT if back else 0)
            spots.append((back, (i == 0) != self.boss, self.members[i], anims[i], x, feet))
        spots.sort(key=lambda s: (not s[0], s[1]))
        return [(sp, anim, x, feet, back) for back, _, sp, anim, x, feet in spots]

    def _flat_run(self) -> tuple[float, float]:
        """The stretch around the leader (px from its x) where the ground is
        level with its own (a map with no level: unbounded)."""
        if not self.level:
            return -math.inf, math.inf
        ends = []
        for d in (-1, 1):
            x = self.x
            while abs(x - self.x) < 10 * TILE and abs(self.level.ground_y(x + d * TILE / 2) - self.ground_y) < 1:
                x += d * TILE / 2
            ends.append(x - self.x)
        return ends[0], ends[1]

    @property
    def body_rect(self) -> pygame.Rect:
        rects = [anim.body_rect(0, x, y, self.facing < 0) for _, anim, x, y, _ in self._placed()]
        return rects[0].unionall(rects[1:])

    def reach_rects(self, level: Level) -> list[pygame.Rect]:
        """Where touching the group starts a battle: its body, and a column
        over each map column it stands in, up to GROUP_REACH above its feet
        or the first tile overhead (a platform, also one a column further,
        or a cave's ceiling)."""
        body = self.body_rect
        rects = [body]
        if self.trainer and self.trainer.blocks:  # (the rival: no getting past, platforms or not)
            return rects + [pygame.Rect(body.left, 0, body.w, body.bottom)]
        feet_row = math.ceil(self.ground_y / TILE - 0.001)
        lowest = self.ground_y - GROUP_REACH
        cols = list(level._cols(body.left, body.right))
        tops, under_platform = {}, []
        for col in cols:
            top = lowest
            for row in range(feet_row - 1, math.floor(lowest / TILE) - 1, -1):
                # A platform also caps the columns next to it, so a group
                # sticking out a little past its end doesn't catch the player
                # jumping up onto it.
                if level.tile(col, row) != EMPTY or PLATFORM in (level.tile(col - 1, row), level.tile(col + 1, row)):
                    top = max(lowest, (row + 1) * TILE)
                    if PLATFORM in (level.tile(col - 1, row), level.tile(col, row), level.tile(col + 1, row)):
                        under_platform.append(top)
                    break
            tops[col] = top
        # A group partly under a platform is capped there all along: from the
        # platform, the player can jump clean over the part sticking out past it.
        cap = max(under_platform, default=None)
        for col in cols:
            top = tops[col] if cap is None else max(tops[col], cap)
            left, right = max(body.left, col * TILE), min(body.right, (col + 1) * TILE)
            if top < body.bottom and left < right:
                rects.append(pygame.Rect(left, math.floor(top), right - left, body.bottom - math.floor(top)))
        return rects

    def touches(self, rect: pygame.Rect, level: Level) -> bool:
        return rect.collidelist(self.reach_rects(level)) >= 0

    def draw(self, surface: pygame.Surface, level: Level, debug: bool = False) -> None:
        flip = self.facing < 0
        for _, anim, x, y, back in self._placed():
            frame = anim.frame(0, flip)
            surface.blit(_shaded(frame) if back else frame, anim.place(0, x, y, flip))
        if debug:
            color = (255, 0, 0) if self.boss else (255, 255, 0)
            for rect in self.reach_rects(level):
                pygame.draw.rect(surface, color, rect, 1)


_SHADED: dict[int, pygame.Surface] = {}


def _shaded(frame: pygame.Surface) -> pygame.Surface:
    """`frame` a little darker (a back-row member), cached."""
    key = id(frame)
    if key not in _SHADED:
        shade = round(255 * BACK_ROW_SHADE)
        dark = frame.copy()
        dark.fill((shade, shade, shade, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _SHADED[key] = dark
    return _SHADED[key]


class Chest:
    """A chest. Opening it rolls `loot` once, its gear at an item level in
    `levels`; it stays open. A `fancy` one (the boss's reward) is trimmed
    with gold."""

    W, BODY_H, LID_H = 32, 16, 9  # size in logical px

    def __init__(self, x: float, feet_y: float, loot: LootTable, levels: Range, fancy: bool = False):
        self.x, self.feet_y = x, feet_y
        self.loot, self.levels = loot, levels
        self.fancy = fancy
        self.opened = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - self.W // 2, round(self.feet_y) - self.BODY_H - self.LID_H,
                           self.W, self.BODY_H + self.LID_H)

    def draw(self, surface: pygame.Surface) -> None:
        name = ("chest_fancy" if self.fancy else "chest") + ("_open" if self.opened else "")
        tileset.draw_prop(surface, name, round(self.x), round(self.feet_y))


FLASH_RADIUS = 92  # px of Flash's light around the player in a dark cave (`Theme.dark`) ...
FLASH_SOFT = 40    # ... fading out over this much
DARK = (6, 6, 10, 238)


@cache
def _flash_hole(grow: int = 0) -> pygame.Surface:
    """How much darkness Flash takes away around its middle (alpha to
    subtract), its radius `grow` px bigger (its flicker)."""
    radius = FLASH_RADIUS + grow
    r = radius + FLASH_SOFT
    hole = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
    for d in range(r, 0, -2):
        lit = 1.0 if d <= radius else 1 - (d - radius) / FLASH_SOFT
        pygame.draw.circle(hole, (0, 0, 0, round(DARK[3] * lit)), (r, r), d)
    return hole


def _darkness(x: float, y: float, t: float) -> pygame.Surface:
    """The dark over the screen, with Flash's light around (`x`, `y`), flickering a little."""
    dark = pygame.Surface(settings.LOGICAL_SIZE, pygame.SRCALPHA)
    dark.fill(DARK)
    hole = _flash_hole(round(2 * math.sin(t * 7) + 1.2 * math.sin(t * 17)))
    dark.blit(hole, (round(x - hole.get_width() / 2), round(y - hole.get_height() / 2)),
              special_flags=pygame.BLEND_RGBA_SUB)
    return dark


class Ball:
    """A Poké Ball lying on the map: Up picks it up (one item, `ball_loot`)."""

    def __init__(self, x: float, feet_y: float):
        self.x, self.feet_y = x, feet_y
        self.taken = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 10, round(self.feet_y) - 16, 20, 16)

    def draw(self, surface: pygame.Surface) -> None:
        x, ground = round(self.x), round(self.feet_y)
        pygame.draw.ellipse(surface, (0, 0, 0, 70), (x - 6, ground - 2, 12, 4))  # shadow
        tileset.draw_prop(surface, "poke_ball", x, ground)


class Doorway:
    """An archway between maps: a dark opening in a frame of the theme's
    stone, or the theme's `art` (a prop). A `sealed` one is boarded up (the
    boss is still guarding it)."""

    W, H = 34, 50

    def __init__(self, x: float, feet_y: float, palette: Palette, sealed: bool = False, art: str = ""):
        self.x, self.feet_y, self.p = x, feet_y, palette
        self.sealed, self.art = sealed, art

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - self.W // 2, round(self.feet_y) - self.H, self.W, self.H)

    def draw(self, surface: pygame.Surface) -> None:
        if self.art:
            drawn = tileset.draw_prop(surface, self.art, round(self.x), round(self.feet_y))
            opening = pygame.Rect(drawn.x + drawn.w // 4, drawn.y + drawn.h // 3, drawn.w // 2, drawn.h * 2 // 3)
            self._planks(surface, opening)
            return
        r, p = self.rect, self.p
        arch = [(r.left, r.bottom), (r.left, r.top + 12), (r.left + 5, r.top + 4), (r.centerx, r.top),
                (r.right - 5, r.top + 4), (r.right, r.top + 12), (r.right, r.bottom)]
        pygame.draw.polygon(surface, p.fill_light, arch)
        pygame.draw.polygon(surface, OUTLINE, arch, 1)
        opening = r.inflate(-12, -8).move(0, 4)
        pygame.draw.rect(surface, (14, 14, 24), opening, border_top_left_radius=9, border_top_right_radius=9)
        for y in range(r.top + 14, r.bottom - 2, 8):  # stone courses
            pygame.draw.line(surface, p.fill, (r.left + 1, y), (opening.left - 1, y))
            pygame.draw.line(surface, p.fill, (opening.right, y), (r.right - 1, y))
        pygame.draw.rect(surface, p.top, (r.left - 2, r.top + 1, 6, 3))  # a bit of grass / snow
        pygame.draw.rect(surface, p.top, (r.right - 4, r.top + 3, 6, 3))
        self._planks(surface, opening)

    def _planks(self, surface: pygame.Surface, opening: pygame.Rect) -> None:
        if self.sealed:
            for y in (opening.top + 8, opening.centery + 2, opening.bottom - 8):
                plank = pygame.Rect(opening.left - 3, y - 2, opening.width + 6, 5)
                pygame.draw.rect(surface, WOOD, plank)
                pygame.draw.rect(surface, OUTLINE, plank, 1)


class Ladder:
    """A dungeon room's ladder: "down" sticks out of a hole in the floor,
    "up" climbs to a hole in the ceiling (`ceiling_y`). A `sealed` one is
    boarded up (a boss guards it)."""

    def __init__(self, kind: str, x: float, feet_y: float, ceiling_y: float, sealed: bool = False):
        self.kind, self.x, self.feet_y, self.ceiling_y = kind, x, feet_y, ceiling_y
        self.sealed = sealed

    @property
    def rect(self) -> pygame.Rect:
        if self.kind == "down":
            return pygame.Rect(round(self.x) - 16, round(self.feet_y) - 40, 32, 40)
        return pygame.Rect(round(self.x) - 12, round(self.feet_y) - 50, 24, 50)

    @property
    def prompt_top(self) -> float:
        return self.feet_y - 62 if self.kind == "down" else self.feet_y - 72

    def draw(self, surface: pygame.Surface) -> None:
        x, ground = round(self.x), round(self.feet_y)
        if self.kind == "down":
            hole = pygame.Rect(x - 15, ground - 3, 30, 12)
            pygame.draw.ellipse(surface, (10, 8, 16), hole)
            pygame.draw.ellipse(surface, OUTLINE, hole, 1)
            top, bottom = ground - 14, ground + 5
        else:
            top, bottom = round(self.ceiling_y) - 2, ground
            hole = pygame.Rect(x - 14, top - 8, 28, 12)
            pygame.draw.ellipse(surface, (10, 8, 16), hole)
        # The ladder prop's middle (two rungs, 16 px) repeated from the bottom up.
        art = tileset.prop("ladder")
        segment = art.subsurface(LADDER_SEGMENT)
        w, h = segment.get_size()
        y = bottom
        while y > top:
            part = min(h, y - top)
            surface.blit(segment, (x - w // 2, y - part), (0, h - part, w, part))
            y -= part
        top_row = pygame.Rect(LADDER_SEGMENT.x, LADDER_SEGMENT.y - 1, w, 1)
        surface.blit(art, (x - w // 2, top - 1), top_row)  # the rails' rounded tops
        if self.sealed:  # rocks piled against it
            for dx, dy, r in ((-9, -6, 7), (6, -7, 8), (-1, -15, 7)):
                pygame.draw.circle(surface, (96, 90, 104), (x + dx, ground + dy), r)
                pygame.draw.circle(surface, OUTLINE, (x + dx, ground + dy), r, 1)


class MapScene(Scene):
    """A map the player walks around: the tiles, the player and the camera,
    the party screen (Tab), and panels (loot, notices, dialogue, a quest
    board) that pause the map, shown one after another. The active quests'
    current steps show under the location (up to TRACKED), and a "!" over
    what they need.
    Subclasses put things on it."""

    touch_map = True
    touch_keys = ((pygame.K_i, "Bag"), (pygame.K_q, "Quests"))

    def __init__(self, game: Game, level: Level):
        self.game = game
        quests.fit_party(game)  # (the party's size can change with the story)
        self.party, self.bag = game.party, game.bag
        self.level = level
        self.tiles = tileset.render(level)
        self.backgrounds = tileset.backgrounds(level)
        self.layer = pygame.Surface((level.width, settings.LOGICAL_SIZE[1]), pygame.SRCALPHA)
        self.player = Player(level.start_x, level.ground_y(level.start_x), self.party[0].species)
        # The panel showing (a ui.ListPanel, or a quest_ui screen with
        # handle_key); the map waits. Then the queued ones, in turn.
        self.panel = None
        self.after_panel = None  # what closing the panel does next
        self.queue: list[tuple[object, object]] = []  # (panel, after)
        self.camera = 0
        self.t = 0.0
        self.debug = False
        self.jump = False
        self.fps = 0.0

    def place_player(self, x: float, facing: int = 1) -> None:
        self.player.x, self.player.feet_y = x, self.level.ground_y(x)
        self.player.facing = facing
        self._follow()

    # Subclasses fill these in.
    def where(self) -> str:
        """Where the player is, shown on the map and in the save list."""
        return ""

    def location(self) -> dict:
        """Where the player is, for a save (see saves.py)."""
        return {}

    def interact(self) -> None:
        """Up was pressed."""

    def interact_down(self) -> None:
        """Down was pressed."""

    def prompt(self) -> tuple[float, float] | None:
        """(x, top) for a "press Up" arrow, if there's something to do here."""
        return None

    def draw_things(self, layer: pygame.Surface) -> None:
        """What's on the map, behind the player (in map coordinates)."""

    def steer(self, controls: Controls) -> Controls:
        """The player's input this frame, as the map lets it be (a spinner
        pad carries them along)."""
        return controls

    def moved(self) -> None:
        """After the player has moved this frame."""

    def markers(self) -> list[tuple[float, float, tuple]]:
        """(x, top, mark) in map coordinates of things quests need here: a
        quest to take or a step's place (`quest_mark`), or quests to hand in
        (`HAND_IN_MARK`)."""
        return []

    # ---------------------------------------------------------------- panels

    def show(self, panel, after=None) -> None:
        """Show `panel` now, or after the ones before it; `after` runs when it closes."""
        if self.panel is None:
            self.panel, self.after_panel = panel, after
        else:
            self.queue.append((panel, after))

    def show_event(self, event: quests.Event) -> None:
        """What a quest event brings: its dialogue, then quests finished and started."""
        if event.dialogue:
            self.show(quest_ui.Dialogue(event.dialogue))
        for done in event.finished:
            self.show(quest_ui.finished(done))
        for key in event.started:
            self.show(quest_ui.started(key))

    def _close_panel(self) -> None:
        after = self.after_panel
        self.panel, self.after_panel = None, None
        if after:
            after()
        if self.panel is None and self.queue:
            self.panel, self.after_panel = self.queue.pop(0)

    def save_point(self):
        # Not while the party is about to head off (e.g. after fainting).
        return None if self.after_panel else self

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if self.panel:
            closed = (self.panel.handle_key(event.key) if hasattr(self.panel, "handle_key")
                      else event.key in CONFIRM_KEYS + BACK_KEYS)
            if closed:
                self._close_panel()
            return
        if event.key == pygame.K_UP:
            self.interact()
        elif event.key == pygame.K_DOWN:
            self.interact_down()
        elif event.key == pygame.K_SPACE:
            self.jump = True
        elif event.key == pygame.K_TAB:
            self.next_scene = SummaryScene(self, self.party, self.bag)
        elif event.key == pygame.K_F1:
            self.debug = not self.debug

    def update(self, dt: float) -> None:
        self.fps = 1 / dt if dt else 0.0
        self.t += dt
        if self.panel:
            return
        lead = self.party[0]  # (it may have evolved or learned moves since)
        self.player.become(lead.species)
        keys = touch.pressed()  # (keyboard and touch buttons)
        self.player.update(dt, self.steer(Controls(
            left=keys[pygame.K_LEFT],
            right=keys[pygame.K_RIGHT],
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=self.jump,
            jump_held=keys[pygame.K_SPACE],
        )), self.level)
        self.jump = False
        self.moved()
        self._follow()

    def _follow(self) -> None:
        """Keep the player in the middle of the view, within the map."""
        view_w = settings.LOGICAL_SIZE[0]
        self.camera = round(max(0, min(self.level.width - view_w, self.player.x - view_w / 2)))

    def draw(self, canvas: pygame.Surface) -> None:
        for layer, factor in self.backgrounds:
            canvas.blit(layer, (-round(self.camera * factor), 0))
        canvas.blit(self.tiles, (-self.camera, 0))
        # Everything on the map is drawn in map coordinates, then the part in
        # view is copied to the screen.
        self.layer.fill((0, 0, 0, 0))
        self.draw_things(self.layer)
        self.player.draw(self.layer, self.debug, self.party[0])
        prompt = None if self.panel else self.prompt()
        if prompt:
            draw_prompt(self.layer, *prompt, self.t)
        canvas.blit(self.layer, (0, 0), pygame.Rect(self.camera, 0, *settings.LOGICAL_SIZE))
        if self.level.theme.dark:  # pitch dark: only Flash's light around the player
            canvas.blit(_darkness(self.player.x - self.camera, self.player.feet_y - 14, self.t), (0, 0))
        if self.panel:
            self.panel.draw(canvas)

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, HELP, (6, 4), size=20)
        ui.text(window, self.where(), (6, 15), ui.WHITE, size=20)
        if DEV.enabled:  # what dev mode has on, after the location
            ui.text(window, DEV.summary(), (6 + ui.font(20).size(self.where())[0] / settings.SCALE + 16, 15),
                    ui.YELLOW, size=20)
        y = 26
        for quest in quests.active(self.game)[:TRACKED]:  # the active quests' next steps
            text = quests.step_text(self.game, quest, quests.step(self.game, quest.key))
            ui.text(window, f"{quest.name}: {text}", (6, y), quest_mark(quest)[1], size=20)
            y += 11
        if self.debug:
            p, level = self.player, self.level
            ui.text(window, f"seed: {level.seed}   state: {p.state}   x: {p.x:.0f}  feet: {p.feet_y:.0f}"
                            f"   fps: {self.fps:.0f}", (6, y), ui.YELLOW, size=20)
        if not self.panel:
            lift = abs((self.t * 2) % 2 - 1) * 4
            marks = list(dict.fromkeys(self.markers()))
            for x, top, (symbol, color) in marks:
                here = [m for m in marks if m[:2] == (x, top)]  # several at one place: side by side
                x += (here.index((x, top, (symbol, color))) - (len(here) - 1) / 2) * 12
                ui.text(window, symbol, (x - self.camera, top - 14 - lift), color, size=32, align="center")
        if self.panel:
            self.panel.draw_overlay(window)


class OverworldScene(MapScene):
    """One map of an instance."""

    def __init__(self, instance: Instance, game: Game, arrive: str = ""):
        """`arrive` (a dungeon room): the room or town key the player came
        from; they arrive at the stair or doorway from there."""
        super().__init__(game, instance.level())
        self.instance = instance
        level, palette = self.level, self.level.theme.palette
        route = instance.route
        # Trainers stand in for some of the map's wild groups (each always at
        # the same one, beaten or not); a gym has nothing else.
        trainers = [t for t in route.trainers if t.map == instance.index]
        first = [t for t in trainers if t.first][:1]  # (the rival: at the first spot)
        rest = [t for t in trainers if t not in first]
        placed = dict(zip([0] if first else [], first))
        offset = len(placed)
        placed |= {offset + i: t for i, t in zip(_spread(len(level.spawns) - offset, len(rest)), rest)}
        rival = {RIVAL_STARTER: game.rival_starter, RIVAL_STARTER_EVOLVED: EVOLUTIONS[game.rival_starter].into}
        for i, trainer in placed.items():
            if i < len(level.spawns):  # (the rival's starter depends on the player's)
                level.spawns[i].encounter = [(rival.get(sp, sp), lv) for sp, lv in trainer.team]
        # Each one fighting after the first gives every wild group a chance
        # (`EXTRA_FOE_CHANCE`) of one more Pokémon: with two, about half have
        # one more; with three, one more on average (the same ones each time
        # this map is shown).
        chances = quests.active_limit(game) - 1
        if route.wild and chances:
            rng = random.Random(instance.seed * 7919 + instance.index)
            for i, spawn in enumerate(level.spawns):
                for _ in range(chances):
                    if i not in placed and rng.random() < EXTRA_FOE_CHANCE:
                        spawn.encounter = list(spawn.encounter) + [extra_member(level.theme, rng)]
        self.wild = []
        for i, spawn in enumerate(level.spawns):
            trainer = placed.get(i)
            if (trainer and not quests.trainer_beaten(game, trainer.key)) or (not trainer and route.wild):
                self.wild.append(WildPokemon(spawn, level=level))
                self.wild[-1].trainer = trainer
        room = instance.room
        self.trainer = room.trainer if room else route.trainer  # whose team the boss group is ("" = wild)
        # A boss is a boss once: beaten, it's an ordinary group there on later
        # trips (its normal size; no boss loot, no chest, the way out open),
        # unless a quest wants it beaten (again).
        # (The Battle Tower's masters are there every run.)
        beaten = not route.tower and (level.boss and self._boss_key() in game.trainers
                                      or game.cleared[route.key] > 0) and not quests.boss_wanted(game, route.key)
        if level.boss and route.boss_after and (route.boss_after[0] in game.trainers
                                                or (route.boss_after[0] in quests.QUESTS
                                                    and quests.is_done(game, route.boss_after[0]))):
            level.boss.encounter, self.trainer = list(route.boss_after[1]), ""  # the quest's boss is beaten
        elif level.boss and route.boss_extra and quests.active_limit(game) >= 2:
            level.boss.encounter = list(level.boss.encounter) + list(route.boss_extra)  # (more of them for a pair)
        if level.boss:  # the rival's starter depends on the player's
            level.boss.encounter = [(rival.get(species, species), lv) for species, lv in level.boss.encounter]
        if level.boss and beaten:
            if not route.boss_after:  # (the group it led, without the extras for a pair)
                level.boss.encounter = [(rival.get(sp, sp), lv) for sp, lv in (room.boss_group if room else
                                                                                route.boss_group or level.boss.encounter)]
            self.trainer = ""
            self.wild.append(WildPokemon(level.boss, level=level))
            self.wild[-1].trainer = None
            self.boss = None
        else:
            self.boss = (WildPokemon(level.boss, boss=True, scale=instance.route.boss_scale, level=level)
                         if level.boss else None)
        if self.boss:
            self.wild.append(self.boss)
        # No roadside chests (the map still has spots for them): chests are
        # special, only bosses leave one (`_boss_beaten`).
        self.chests: list[Chest] = []
        self.balls = [Ball(x, y) for x, y in level.balls] if route.wild else []
        # The Vermilion Gym's trash cans and electric fence (solved once, it stays open).
        self.grid = (PowerGrid(level, random.Random(instance.seed), self._puzzle_key() in game.trainers)
                     if route.puzzle == "trash_cans" and self.boss else None)
        # The Celadon Gym's drifting spore clouds.
        # (the Power Plant's loose sparks work the same way; both need the arena's boss)
        # The Rocket Hideout's spinner floors.
        layout = layout_of(instance.room.puzzle) if instance.room else None
        self.spinners = SpinnerFloor(level, layout) if layout else None
        self.spores = (SporeGarden(level, random.Random(instance.seed), sparks=route.puzzle == "sparks")
                       if route.puzzle in ("spores", "sparks") and level.boss else None)
        # The doorways in and out; a dungeon room has its stairs instead.
        art = level.theme.doorway
        self.entry = Doorway(level.entry_x, level.ground_y(level.entry_x), palette, art=art)
        self.exit = Doorway(level.exit_x, level.ground_y(level.exit_x), palette, sealed=bool(self.boss), art=art)
        self.stairs: list[tuple[Stair, Doorway | Ladder]] = []
        if room:
            for i, (stair, col) in enumerate(zip(room.stairs, level.stairs)):
                x = col * TILE + TILE / 2
                sealed = bool(self.boss) and i == len(room.stairs) - 1  # the boss guards the last one
                thing = (Doorway(x, level.ground_y(x), palette, sealed, art) if stair.kind == "out"
                         else Ladder(stair.kind, x, level.ground_y(x), self._ceiling_y(col), sealed))
                self.stairs.append((stair, thing))
            self.exit = self.stairs[-1][1]  # (what the boss guards)
            here = next((thing for stair, thing in self.stairs if stair.to == (arrive or instance.came_from)), None)
            if here:
                self.place_player(here.x, 1 if here.x < level.width / 2 else -1)
        # Who stands in a dungeon room to talk to (`Room.folk`: the S.S. Anne's Captain).
        self.folk = [(folk, col * TILE + TILE / 2) for (_, folk), col in zip(room.folk, level.folk_cols)] if room else []
        self.chats: dict[str, int] = {}  # their key -> chat lines said
        self.fighting: tuple[WildPokemon, BattleScene] | None = None
        self.battle_event = quests.Event()  # quests started by the last battle's drops
        if str(instance.index) in instance.rooms:  # back in a room left earlier this trip
            self._apply_room_state(instance.rooms[str(instance.index)])

    def _ceiling_y(self, col: int) -> float:
        """The bottom of the cave's ceiling over `col` (a ladder up reaches it)."""
        row = 0
        while row < len(self.level.grid) and self.level.grid[row][col] == SOLID:
            row += 1
        return max(row * TILE, self.level.ground_y(col * TILE) - 9 * TILE)

    def where(self) -> str:
        inst = self.instance
        if inst.route.tower:
            text = f"Battle Tower {inst.route.name}"
        elif inst.room:
            text = f"{inst.route.name} {inst.room.name}"
        else:
            text = f"{inst.route.name}   map {inst.index + 1}/{inst.maps}   to {TOWNS[inst.destination].name}"
        if self.boss and inst.route.tower:
            text += "   the master awaits!" if self.boss in self.wild else "   floor cleared!"
        elif self.boss:
            text += "   the way out is guarded!" if self.boss in self.wild else "   the way out is open"
        return text

    def _ball_at_player(self) -> Ball | None:
        return next((b for b in self.balls if not b.taken and self.player.body_rect.colliderect(b.rect)), None)

    def _chest_at_player(self) -> Chest | None:
        """A closed chest the player is standing at."""
        return next((c for c in self.chests if not c.opened and self.player.body_rect.colliderect(c.rect)),
                    None)

    def _at_exit(self) -> bool:
        return not self.exit.sealed and self.player.body_rect.colliderect(self.exit.rect)

    def _stair_at_player(self) -> tuple[Stair, Doorway | Ladder] | None:
        """The (open) stair or doorway of a dungeon room the player stands at."""
        return next(((stair, thing) for stair, thing in self.stairs
                     if not thing.sealed and self.player.body_rect.colliderect(thing.rect)), None)

    def _folk_at_player(self):
        """(folk, x) of who the player stands next to, if anyone."""
        return next(((f, x) for f, x in self.folk if abs(self.player.x - x) < FOLK_REACH), None)

    def _folk_anim(self, folk):
        species = SPECIES[folk.species_for(self.game.starter)]
        return species, animations(species)["idle"]

    def _folk_top(self, folk, x: float) -> float:
        species, anim = self._folk_anim(folk)
        return anim.body_rect(0, x, self.level.ground_y(x) + species.foot_sink + FOOT_SINK).top

    def markers(self) -> list[tuple[float, float, tuple]]:
        """Over a room's folk: a quest step that waits for them."""
        near = self._folk_at_player()
        return [(x, self._folk_top(folk, x) - 4, quest_mark(quest)) for folk, x in self.folk
                if not (near and near[0] is folk) for quest in quests.folk_quests(self.game, folk.key)]

    def _talk(self, folk) -> None:
        """A quest step that waits for them, else their next chat line."""
        event = quests.talk(self.game, folk.key)
        if event:
            self.show_event(event)
            saves.autosave(self)
        elif folk.lines:
            said = self.chats.get(folk.key, 0)
            self.chats[folk.key] = said + 1
            self.show(quest_ui.Dialogue([(folk.name_for(self.game.starter), folk.lines[said % len(folk.lines)])]))

    def _puzzle_key(self) -> str:
        return f"puzzle:{self.instance.route.key}"

    def _search(self, i: int) -> None:
        """Rummage in trash can `i` (the gym's puzzle)."""
        lines, ambush = self.grid.search(i)
        if self.grid.open:
            self.game.trainers.add(self._puzzle_key())
        if not ambush:
            self.show(quest_ui.Dialogue([("", line) for line in lines]))
            return
        x = self.grid.cans[i]  # out it pops: a wild group standing there, which fights at once
        voltorb = WildPokemon(Spawn(x, self.level.ground_y(x), list(AMBUSH)), level=self.level)
        voltorb.armed = False
        self.wild.append(voltorb)
        self.show(quest_ui.Dialogue([("", line) for line in lines]), after=lambda: self._fight(voltorb))

    def interact(self) -> None:
        chest, ball = self._chest_at_player(), self._ball_at_player()
        folk = self._folk_at_player()
        can = self.grid.can_at(self.player.x) if self.grid else None
        if can is not None:
            self._search(can)
        elif self.grid and self.grid.at_fence(self.player.x):
            self.show(quest_ui.Dialogue([("", line) for line in self.grid.SIGN]))
        elif folk:
            self._talk(folk[0])
        elif ball:
            self._pick_up(ball)
        elif chest:
            self._open(chest)
        elif self.stairs:
            at = self._stair_at_player()
            if at:
                self._take(at[0])
        elif self._at_exit():
            self._go_on()

    def interact_down(self) -> None:
        at = self._stair_at_player()
        if at and at[0].kind == "down":
            self._take(at[0])

    def prompt(self) -> tuple[float, float] | None:
        can = self.grid.can_at(self.player.x) if self.grid else None
        if can is not None:
            x = self.grid.cans[can]
            return x, self.level.ground_y(x) - 34
        if self.grid and self.grid.at_fence(self.player.x):
            return self.grid.fence_x - 30, self.level.ground_y(self.grid.fence_x) - 44
        folk = self._folk_at_player()
        if folk:
            return folk[1], self._folk_top(*folk) - 12
        ball = self._ball_at_player()
        if ball:
            return ball.x, ball.feet_y - 26
        chest = self._chest_at_player()
        if chest:
            return chest.x, chest.feet_y - 62
        if self.stairs:
            at = self._stair_at_player()
            if not at:
                return None
            thing = at[1]
            return thing.x, (thing.prompt_top if isinstance(thing, Ladder) else thing.feet_y - 66)
        if self._at_exit():
            return self.exit.x, self.exit.feet_y - 66
        return None

    def _pick_up(self, ball: Ball) -> None:
        ball.taken = True
        rewards = ball_loot().roll()
        for r in rewards:
            r.give(self.bag)
        self.show(ui.ListPanel("You found:", [r.row() for r in rewards], (320, 140)))
        saves.autosave(self)

    def _open(self, chest: Chest) -> None:
        chest.opened = True
        rewards = chest.loot.roll(level=random.randint(*chest.levels))
        for r in rewards:
            r.give(self.bag)
        self.show(ui.ListPanel("The chest contained:", [r.row() for r in rewards], (320, 140)))
        saves.autosave(self)

    def _take(self, stair: Stair) -> None:
        """Up or down a ladder to another room of the dungeon, or out of a
        doorway into a town (going through to the far end clears it). The
        room left keeps what's been beaten and opened for this trip."""
        inst = self.instance
        inst.rooms[str(inst.index)] = self.room_state()
        if stair.kind == "out":
            if stair.to == inst.destination:
                self.game.cleared[inst.route.key] += 1
            next_map = town_scene(self.game, TOWNS[stair.to], arrive=inst.route.key)
        else:
            here = inst.room.key
            inst.index = next(i for i, room in enumerate(inst.route.rooms) if room.key == stair.to)
            next_map = OverworldScene(inst, self.game, arrive=here)
        saves.autosave(next_map)
        self.next_scene = Transition(self, next_map, flashes=0)

    def _go_on(self) -> None:
        """Through the doorway: the next map, or into the town at the end of
        the route after the last. Either way, autosave where the player arrives."""
        inst = self.instance
        if inst.route.tower:  # (the Battle Tower: on up, or stop)
            self._tower_choice()
            return
        if inst.final:
            self.game.cleared[inst.route.key] += 1
            town = TOWNS[inst.destination]
            next_map = town_scene(self.game, town, arrive=inst.route.key)
        else:
            inst.index += 1
            next_map = OverworldScene(inst, self.game)
        saves.autosave(next_map)
        self.next_scene = Transition(self, next_map, flashes=0)

    def _after_battle(self, wild: WildPokemon, battle: BattleScene) -> None:
        if battle.won:
            self.wild.remove(wild)
            if wild.trainer:  # beaten for good (and maybe a quest step: the rival)
                self.game.trainers.add(wild.trainer.key)
            self.show_event(self.battle_event)
            if wild.trainer:
                self.show_event(quests.defeat(self.game, wild.trainer.key))
            if wild is self.boss and self.instance.route.tower:  # a Battle Tower floor cleared
                self._boss_beaten()
                self._tower_choice()
            elif wild is self.boss:
                self.game.trainers.add(self._boss_key())  # (an ordinary group from now on)
                route = self.instance.route
                if route.boss_key and self.trainer and route.boss_key not in self.game.trainers:
                    self.game.trainers.add(route.boss_key)  # a one-time boss trainer (the Rocket): its gift
                    if route.boss_gift:
                        self.bag.add_medicine(route.boss_gift, 1)
                    self.show_event(quests.Event(dialogue=list(route.boss_dialogue)))
                self._boss_beaten()
                self.show_event(quests.defeat(self.game, route.key))
            saves.autosave(self)
        elif battle.lost:
            town = TOWNS[self.game.town]
            if self.instance.route.tower:
                self.show(ui.ListPanel("Your party fainted...", [("The run is over: no chest this time.", ui.WHITE, ""),
                                                                 (f"You hurry back to {town.name}.", ui.WHITE, "")],
                                       (320, 140)), after=self._fainted)
                return
            self.show(ui.ListPanel("Your party fainted...", [(f"You hurry back to {town.name}.", ui.WHITE, "")],
                                   (320, 140)), after=self._fainted)

    def _tower_choice(self) -> None:
        """A Battle Tower floor is cleared: on up to the next (no healing),
        or stop and claim the run's chest, back in the lobby."""
        from . import battle_tower  # (it builds on this module)
        floor = self.instance.route.tower
        self.game.tower_best = max(self.game.tower_best, floor)
        choice = battle_tower.TowerChoice(floor, tower.top_floor(self.game))

        def chosen():
            if choice.picked == "climb":
                inst = Instance(tower.TOWER_ROUTES[tower.floor_key(floor + 1)], tower.LOBBY_TOWN)
                self.next_scene = Transition(self, OverworldScene(inst, self.game), flashes=0)
            elif choice.picked == "claim":
                self.show(battle_tower.claim(self.game, floor), after=self._to_lobby)
        self.show(choice, after=chosen)

    def _to_lobby(self) -> None:
        from .battle_tower import TowerLobbyScene
        lobby = TowerLobbyScene(self.game)
        saves.autosave(lobby)
        self.next_scene = Transition(self, lobby, flashes=0)

    def _boss_key(self) -> str:
        """What `Game.trainers` keeps once this map's boss is beaten."""
        room = self.instance.room
        return f"boss:{self.instance.route.key}" + (f"/{room.key}" if room else "")

    def _boss_beaten(self) -> None:
        """The way out opens, and the boss leaves its chest (`Route.boss_chest`):
        a plain one (a chest's loot, at the boss's rarities) or a gym's fancy
        one (the boss loot); none if its loot comes with the battle, or there
        is none."""
        self.exit.sealed = False
        route = self.instance.route
        if route.boss_chest not in ("plain", "fancy"):
            return
        fancy = route.boss_chest == "fancy"
        x = self.level.boss_chest_x
        top = max(lv for _, lv in self.level.boss.encounter)  # the boss group's highest level
        loot = boss_loot(route.boss_loot) if fancy else chest_loot(route.boss_loot)
        self.chests.append(Chest(x, self.level.ground_y(x), loot, (top, top), fancy=fancy))

    def _fainted(self) -> None:
        """Back to the last town visited, where the party is healed."""
        town = town_scene(self.game, TOWNS[self.game.town], arrive="home")
        saves.autosave(town)
        self.next_scene = Transition(self, town, flashes=0)

    def update(self, dt: float) -> None:
        # Back from a battle. (Not while still heading into it: a gym's waves
        # start from the team pick, closed by a key press, and the map is
        # updated once more in that frame.)
        if self.fighting and not self.next_scene:
            self._after_battle(*self.fighting)
            self.fighting = None
        super().update(dt)
        if self.grid:  # the electric fence holds the player back
            self.player.x = self.grid.blocks(self.player.x)
        if self.panel:
            return
        if self.spores:
            self.spores.update(dt, self.t, self.player.body_rect, self.party, random)
        for wild in self.wild:
            wild.facing = 1 if self.player.x > wild.x else -1
            touching = wild.touches(self.player.body_rect, self.level)
            if DEV.skip_packs and wild is not self.boss:  # (dev mode: walk straight through ...
                wild.armed = not touching                   # ... and not caught in it once switched off)
                continue
            if touching and wild.armed:
                if wild is self.boss and self.instance.route.waves:  # a gym's arena: pick the team first
                    pick = TeamPick(self.instance.route, self.party, quests.active_limit(self.game))
                    self.show(pick, after=lambda: pick.team and self._start_waves(wild, pick.team))
                else:
                    self._fight(wild)
            wild.armed = not touching

    def _battle(self, wild: WildPokemon, party: list[Monster], encounter: list[tuple[str, int]],
                trainer: str, prize: int, boss: bool, **extra) -> BattleScene:
        """A battle against `encounter` (the battle `wild` is fought for)."""
        # Trainers' and bosses' Pokémon have some talents (every other open tier); wild ones none.
        enemies = [Monster.create(species, level, talents="half" if boss or trainer else "none")
                   for species, level in encounter]
        if boss:
            for enemy, scale in zip(enemies, wild.scales):
                enemy.scale = scale
        route = self.instance.route
        if route.tower:  # the Battle Tower: talents and gear by its tier, nothing dropped, no prize
            enemies = [Monster.create(species, level, talents=tower.TALENTS[tower.tier(route.tower)])
                       for species, level in encounter]
            if boss:
                for enemy, scale in zip(enemies, wild.scales):
                    enemy.scale = scale
            for i, enemy in enumerate(enemies):
                tower.dress_up(enemy, route.tower, master=boss and i == 0)
            extra.setdefault("drops", False)
            prize = 0
        elif boss or trainer:  # they wear gear (the boss itself 2 pieces), which can drop
            for i, enemy in enumerate(enemies):
                dress(enemy, route.boss_loot if boss else route.loot, BOSS_GEAR if boss and i == 0 else TRAINER_GEAR)
        battle = BattleScene(self, party, enemies, self.bag, loot=wild_loot(route.boss_loot if boss else route.loot),
                             backdrop=self.level.theme.backdrop, boss=boss, trainer=trainer,
                             prize=prize_money(prize, encounter) if trainer and prize else 0,
                             bonus=None if route.tower else boss_loot(route.boss_loot) if (boss and route.boss_chest == "battle") or (
                                 wild.trainer and wild.trainer.boss_loot) else None,
                             on_win=lambda key=route.key, defeated=[s for s, _ in encounter], wild=not (boss or trainer):
                                 quests.won_battle(self.game, key, defeated, self.battle_event, recruits=wild),
                             evolves=lambda m: quests.can_evolve(self.game, m), **extra)
        self.fighting = (wild, battle)
        return battle

    def _fight(self, wild: WildPokemon) -> None:
        """Into battle with a group on the map, the active party members
        (`quests.fighters`)."""
        boss = wild is self.boss
        boss_prize = self.instance.room.prize if self.instance.room else self.instance.route.prize
        trainer, prize = (self.trainer, boss_prize) if boss else (
            (wild.trainer.name, wild.trainer.prize) if wild.trainer else ("", 0))
        self.battle_event = quests.Event()  # quests a battle's drops start
        self.next_scene = Transition(self, self._battle(wild, quests.fighters(self.game), wild.encounter, trainer, prize,
                                                        boss))

    def _start_waves(self, boss: WildPokemon, team: list[Monster]) -> None:
        """A gym's arena: its waves, then the boss group, one battle straight
        after another (no healing in between), fought by `team` alone. Losing
        any of them is losing the gym; the last one is the boss battle."""
        route = self.instance.route
        waves = [(w.name, list(w.team), w.prize) for w in route.waves] + [(self.trainer, boss.encounter, route.prize)]

        def battle(i: int) -> BattleScene:
            name, encounter, prize = waves[i]
            last = i == len(waves) - 1
            return self._battle(boss, team, encounter, name, prize, boss=last, wave=(i + 1, len(waves)),
                                next_battle=None if last else lambda: battle(i + 1))

        self.battle_event = quests.Event()
        self.next_scene = Transition(self, battle(0))

    def steer(self, controls: Controls) -> Controls:
        return self.spinners.steer(controls) if self.spinners else controls

    def moved(self) -> None:
        if self.spinners:
            self.spinners.update(self.player)

    def draw_things(self, layer: pygame.Surface) -> None:
        if self.stairs:
            for _, thing in self.stairs:
                thing.draw(layer)
        else:
            self.entry.draw(layer)
            self.exit.draw(layer)
        if self.grid:
            self.grid.draw(layer, self.t)
        if self.spinners:
            self.spinners.draw(layer, self.t)
        if self.spores:
            self.spores.draw(layer, self.t)
        for chest in self.chests:
            chest.draw(layer)
        for ball in self.balls:
            if not ball.taken:
                ball.draw(layer)
        for wild in self.wild:
            wild.draw(layer, self.level, self.debug)
        for folk, x in self.folk:  # facing the player
            species, anim = self._folk_anim(folk)
            flip, index = self.player.x < x, anim.index_at(self.t)
            layer.blit(anim.frame(index, flip), anim.place(index, x, self.level.ground_y(x) + species.foot_sink + FOOT_SINK,
                                                           flip))

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.panel:
            return
        if self.spores and self.spores.toast_t:  # what a spore cloud just did
            ui.text(window, self.spores.toast, (320, 300), ui.WHITE, size=24, align="center")
        near = self._folk_at_player()
        if near:  # their name, over them
            ui.text(window, near[0].name_for(self.game.starter), (near[1] - self.camera, self._folk_top(*near) - 26),
                    ui.WHITE, size=26, align="center")
        for wild in self.wild:  # whose team it is, over trainers' groups
            name = self.trainer if wild is self.boss else wild.trainer.name if wild.trainer else ""
            if name:
                box = wild.body_rect
                ui.text(window, name, (box.centerx - self.camera, box.top - 14), ui.YELLOW, size=24,
                        align="center")

    # ----------------------------------------------------------------- saves

    def save_point(self):
        # Not right after a battle, or while the party is about to head home.
        return None if self.fighting else super().save_point()

    def room_state(self) -> dict:
        """What's been beaten and opened on this map."""
        return {
            "beaten": [i for i, s in enumerate(self.level.spawns) if all(w.spawn is not s for w in self.wild)],
            "boss_beaten": bool(self.boss) and self.boss not in self.wild,
            "opened": [i for i, c in enumerate(self.chests) if c.opened],
            "balls": [i for i, b in enumerate(self.balls) if b.taken],
        }

    def location(self) -> dict:
        """Where the run is at: the map, what's been beaten and opened on it
        (in a dungeon: in every room visited), and where the player stands."""
        inst, p = self.instance, self.player
        if inst.route.tower:  # (a Battle Tower run isn't saved: outside the tower)
            from .battle_tower import lobby_location
            return lobby_location()
        return {
            "kind": "route", "route": inst.route.key, "destination": inst.destination,
            "seed": inst.seed, "map": inst.index, **self.room_state(),
            "rooms": inst.rooms, "came_from": inst.came_from,
            "player": [p.x, p.feet_y, p.facing],
        }

    def _apply_room_state(self, state: dict) -> None:
        beaten = [self.level.spawns[i] for i in state["beaten"]]
        self.wild = [w for w in self.wild if all(w.spawn is not s for s in beaten)]
        if state["boss_beaten"] and self.boss in self.wild:
            self.wild.remove(self.boss)
            self._boss_beaten()
        # (Indexes past the end: a save from before the map's chests changed.)
        for i in state["opened"]:
            if i < len(self.chests):
                self.chests[i].opened = True
        for i in state.get("balls", []):
            if i < len(self.balls):
                self.balls[i].taken = True

    def restore(self, state: dict) -> None:
        """Back to a saved `location` on this map."""
        self._apply_room_state(state)
        p = self.player
        p.x, p.feet_y, p.facing = state["player"]
        self._follow()
        for wild in self.wild:  # don't start a battle just by loading next to a group
            wild.armed = not wild.touches(p.body_rect, self.level)


def _spread(spawns: int, n: int) -> list[int]:
    """`n` of a map's spawn indices, spread out evenly (for trainers)."""
    spots = []
    for k in range(n):
        i = min(spawns - 1, max(0, round((k + 1) * spawns / (n + 1)) - 1))
        while i in spots and i < spawns - 1:
            i += 1
        spots.append(i)
    return spots


def prize_money(base: int, team) -> int:
    """A trainer's prize: its base × its last Pokémon's level (Gen 1's rule),
    halved like the shop's prices."""
    return base * team[-1][1] // 2


def town_scene(game: Game, town, arrive: str) -> MapScene:
    # Imported here: town.py builds on this module.
    from .town import TownScene
    return TownScene(game, town, arrive)
