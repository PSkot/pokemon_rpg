"""Side-scrolling maps: what every map has (`MapScene`), and the maps of
an instance (`OverworldScene`), such as a route between two towns.

On an instance's maps, touching wild Pokémon starts a battle (beaten ones
are gone for the run), chests open with Up, and the doorway at the end of
the map leads on (Up). An instance with a boss ends with a boss group
guarding the doorway out; beating it opens the way and leaves a reward
chest. Towns are in town.py.
"""

import math
import random

import pygame

from .. import saves, settings
from ..dev import DEV
from ..engine import touch, ui
from ..engine.scene import Scene, Transition
from ..mechanics.items import Range
from ..mechanics.loot import LootTable, boss_loot, chest_loot, wild_loot
from ..mechanics.pokemon import SPECIES, Monster, animations
from ..world import tileset
from ..world.instance import RIVAL_STARTER, Instance, Trainer
from ..world.level import Level, Spawn
from ..world.player import Controls, Player
from ..world import quests
from ..world.progress import Game
from ..world.themes import Palette
from ..world.towns import TOWNS
from . import quest_ui
from .battle import BattleScene
from .summary import SummaryScene

HELP = ("Left/Right: walk   Shift: run   Space: jump (hold = higher)   Up: open / go through"
        "   Tab: party   F1: debug   Esc: menu")
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z, pygame.K_UP)

WOOD = (150, 96, 48)
WOOD_DARK = (96, 58, 28)
OUTLINE = (48, 28, 16)
GOLD = (232, 192, 72)
TRACKED = 3  # active quests shown under the location
GROUP_SPACING = 30  # px between the members of a wild group, standing in a row


def draw_prompt(surface: pygame.Surface, x: float, top: float, t: float) -> None:
    """A bobbing arrow: press Up here."""
    x, top = round(x), round(top + math.sin(t * 6) * 2)
    for color, d in ((ui.SHADOW, 1), (ui.WHITE, 0)):
        pygame.draw.polygon(surface, color, [(x - 5 + d, top + 6 + d), (x + 5 + d, top + 6 + d), (x + d, top + d)])


class WildPokemon:
    """A group of wild Pokémon on the map, all shown, standing in a row
    behind the first. Touching them starts a battle against `encounter`:
    a list of (species, level). A boss group's leader (the first) can be
    drawn `scale` times bigger (on the map and in battle)."""

    def __init__(self, spawn: Spawn, boss: bool = False, scale: int = 1):
        self.spawn = spawn
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

    def _placed(self):
        """(species, idle animation, x, feet y) per member, the back ones first."""
        behind = -self.facing  # the others stand further from the player
        offsets = [0.0]  # each one a spacing behind the one before (more next to a big one)
        for a, b in zip(self.scales, self.scales[1:]):
            offsets.append(offsets[-1] + GROUP_SPACING * (a + b) / 2)
        for i in reversed(range(len(self.members))):
            species, scale = self.members[i], self.scales[i]
            x = self.x + behind * offsets[i]
            yield species, animations(species, scale)["idle"], x, self.ground_y + species.foot_sink * scale

    @property
    def body_rect(self) -> pygame.Rect:
        rects = [anim.body_rect(0, x, y, self.facing < 0) for _, anim, x, y in self._placed()]
        return rects[0].unionall(rects[1:])

    def draw(self, surface: pygame.Surface, debug: bool = False) -> None:
        flip = self.facing < 0
        for _, anim, x, y in self._placed():
            surface.blit(anim.frame(0, flip), anim.place(0, x, y, flip))
        if debug:
            pygame.draw.rect(surface, (255, 0, 0) if self.boss else (255, 255, 0), self.body_rect, 1)


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
        x, ground, half = round(self.x), round(self.feet_y), self.W // 2
        wood, band = ((120, 40, 60), GOLD) if self.fancy else (WOOD, WOOD_DARK)
        body = pygame.Rect(x - half + 1, ground - self.BODY_H, self.W - 2, self.BODY_H)
        lid = pygame.Rect(x - half, body.y - self.LID_H + 1, self.W, self.LID_H)
        if self.opened:  # lid flipped up behind, the dark inside showing
            lid.bottom = body.y - 2  # hinged at the back edge
            pygame.draw.rect(surface, band if self.fancy else WOOD_DARK, lid)
            pygame.draw.rect(surface, OUTLINE, lid, 1)
        pygame.draw.rect(surface, wood, body)
        pygame.draw.line(surface, band, (body.x + 1, body.centery), (body.right - 2, body.centery))
        for bx in (body.x + 4, body.right - 6):  # metal corner bands
            pygame.draw.rect(surface, band, (bx, body.y + 1, 2, body.h - 2))
        pygame.draw.rect(surface, OUTLINE, body, 1)
        if self.opened:
            pygame.draw.rect(surface, OUTLINE, (body.x + 1, body.y - 3, body.w - 2, 4))
        else:
            corners = dict(border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.rect(surface, wood, lid, **corners)
            if self.fancy:
                pygame.draw.line(surface, GOLD, (lid.x + 2, lid.y + 2), (lid.right - 3, lid.y + 2))
            pygame.draw.rect(surface, OUTLINE, lid, 1, **corners)
            lock = pygame.Rect(x - 3, body.y - 3, 6, 7)
            pygame.draw.rect(surface, GOLD, lock)
            pygame.draw.rect(surface, OUTLINE, lock, 1)


class Doorway:
    """An archway between maps: a dark opening in a frame of the theme's
    stone. A `sealed` one is boarded up (the boss is still guarding it)."""

    W, H = 34, 50

    def __init__(self, x: float, feet_y: float, palette: Palette, sealed: bool = False):
        self.x, self.feet_y, self.p = x, feet_y, palette
        self.sealed = sealed

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - self.W // 2, round(self.feet_y) - self.H, self.W, self.H)

    def draw(self, surface: pygame.Surface) -> None:
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
        if self.sealed:
            for y in (opening.top + 8, opening.centery + 2, opening.bottom - 8):
                plank = pygame.Rect(opening.left - 3, y - 2, opening.width + 6, 5)
                pygame.draw.rect(surface, WOOD, plank)
                pygame.draw.rect(surface, OUTLINE, plank, 1)


class MapScene(Scene):
    """A map the player walks around: the tiles, the player and the camera,
    the party screen (Tab), and panels (loot, notices, dialogue, a quest
    board) that pause the map, shown one after another. The active quests'
    current steps show under the location (up to TRACKED), and a "!" over
    what they need.
    Subclasses put things on it."""

    touch_map = True

    def __init__(self, game: Game, level: Level):
        self.game = game
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

    def prompt(self) -> tuple[float, float] | None:
        """(x, top) for a "press Up" arrow, if there's something to do here."""
        return None

    def draw_things(self, layer: pygame.Surface) -> None:
        """What's on the map, behind the player (in map coordinates)."""

    def markers(self) -> list[tuple[float, float]]:
        """(x, top) in map coordinates of things the active quests need here."""
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
                      else event.key in CONFIRM_KEYS)
            if closed:
                self._close_panel()
            return
        if event.key == pygame.K_UP:
            self.interact()
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
        self.player.update(dt, Controls(
            left=keys[pygame.K_LEFT],
            right=keys[pygame.K_RIGHT],
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=self.jump,
            jump_held=keys[pygame.K_SPACE],
        ), self.level)
        self.jump = False
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
            ui.text(window, f"{quest.name}: {text}", (6, y), ui.YELLOW, size=20)
            y += 11
        if self.debug:
            p, level = self.player, self.level
            ui.text(window, f"seed: {level.seed}   state: {p.state}   x: {p.x:.0f}  feet: {p.feet_y:.0f}"
                            f"   fps: {self.fps:.0f}", (6, y), ui.YELLOW, size=20)
        if not self.panel:
            lift = abs((self.t * 2) % 2 - 1) * 4
            for x, top in self.markers():
                ui.text(window, "!", (x - self.camera, top - 14 - lift), ui.YELLOW, size=32, align="center")
        if self.panel:
            self.panel.draw_overlay(window)


class OverworldScene(MapScene):
    """One map of an instance."""

    def __init__(self, instance: Instance, game: Game):
        super().__init__(game, instance.level())
        self.instance = instance
        level, palette = self.level, self.level.theme.palette
        route = instance.route
        # Trainers stand in for some of the map's wild groups (each always at
        # the same one, beaten or not); a gym has nothing else.
        trainers = [t for t in route.trainers if t.map == instance.index]
        placed = dict(zip(_spread(len(level.spawns), len(trainers)), trainers))
        for i, trainer in placed.items():
            level.spawns[i].encounter = list(trainer.team)
        self.wild = []
        for i, spawn in enumerate(level.spawns):
            trainer = placed.get(i)
            if (trainer and trainer.key not in game.trainers) or (not trainer and route.wild):
                self.wild.append(WildPokemon(spawn))
                self.wild[-1].trainer = trainer
        self.trainer = route.trainer  # whose team the boss group is ("" = wild)
        if level.boss and route.boss_after and quests.is_done(game, route.boss_after[0]):
            level.boss.encounter, self.trainer = list(route.boss_after[1]), ""  # the quest's boss is beaten
        if level.boss:  # the rival's starter depends on the player's
            level.boss.encounter = [(game.rival_starter if species == RIVAL_STARTER else species, lv)
                                    for species, lv in level.boss.encounter]
        self.boss = WildPokemon(level.boss, boss=True, scale=instance.route.boss_scale) if level.boss else None
        if self.boss:
            self.wild.append(self.boss)
        self.chests = [Chest(x, y, chest_loot(route.loot), level.theme.levels)
                       for x, y in level.chests] if route.wild else []
        self.entry = Doorway(level.entry_x, level.ground_y(level.entry_x), palette)
        self.exit = Doorway(level.exit_x, level.ground_y(level.exit_x), palette, sealed=bool(self.boss))
        self.fighting: tuple[WildPokemon, BattleScene] | None = None
        self.battle_event = quests.Event()  # quests started by the last battle's drops

    def where(self) -> str:
        inst = self.instance
        text = f"{inst.route.name}   map {inst.index + 1}/{inst.maps}   to {TOWNS[inst.destination].name}"
        if self.boss:
            text += "   the way out is guarded!" if self.boss in self.wild else "   the way out is open"
        return text

    def _chest_at_player(self) -> Chest | None:
        """A closed chest the player is standing at."""
        return next((c for c in self.chests if not c.opened and self.player.body_rect.colliderect(c.rect)),
                    None)

    def _at_exit(self) -> bool:
        return not self.exit.sealed and self.player.body_rect.colliderect(self.exit.rect)

    def interact(self) -> None:
        chest = self._chest_at_player()
        if chest:
            self._open(chest)
        elif self._at_exit():
            self._go_on()

    def prompt(self) -> tuple[float, float] | None:
        chest = self._chest_at_player()
        if chest:
            return chest.x, chest.feet_y - 62
        if self._at_exit():
            return self.exit.x, self.exit.feet_y - 66
        return None

    def _open(self, chest: Chest) -> None:
        chest.opened = True
        rewards = chest.loot.roll(level=random.randint(*chest.levels))
        for r in rewards:
            r.give(self.bag)
        self.show(ui.ListPanel("The chest contained:", [r.row() for r in rewards], (320, 140)))
        saves.autosave(self)

    def _go_on(self) -> None:
        """Through the doorway: the next map, or into the town at the end of
        the route after the last. Either way, autosave where the player arrives."""
        inst = self.instance
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
            if wild.trainer:  # beaten for good
                self.game.trainers.add(wild.trainer.key)
            self.show_event(self.battle_event)
            if wild is self.boss:
                self._boss_beaten()
                self.show_event(quests.defeat(self.game, self.instance.route.key))
            saves.autosave(self)
        elif battle.lost:
            town = TOWNS[self.game.town]
            self.show(ui.ListPanel("Your party fainted...", [(f"You hurry back to {town.name}.", ui.WHITE, "")],
                                   (320, 140)), after=self._fainted)

    def _boss_beaten(self) -> None:
        """The way out opens, and the boss leaves a reward chest (unless the
        route's boss loot comes with the battle)."""
        self.exit.sealed = False
        if not self.instance.route.boss_chest:
            return
        x = self.level.boss_chest_x
        top = max(lv for _, lv in self.level.boss.encounter)  # the boss group's highest level
        self.chests.append(Chest(x, self.level.ground_y(x), boss_loot(self.instance.route.boss_loot), (top, top),
                                 fancy=True))

    def _fainted(self) -> None:
        """Back to the last town visited, where the party is healed."""
        town = town_scene(self.game, TOWNS[self.game.town], arrive="home")
        saves.autosave(town)
        self.next_scene = Transition(self, town, flashes=0)

    def update(self, dt: float) -> None:
        if self.fighting:  # back from a battle
            self._after_battle(*self.fighting)
            self.fighting = None
        super().update(dt)
        if self.panel:
            return
        for wild in self.wild:
            wild.facing = 1 if self.player.x > wild.x else -1
            touching = self.player.body_rect.colliderect(wild.body_rect)
            if touching and wild.armed:
                enemies = [Monster.create(species, level) for species, level in wild.encounter]
                for enemy, scale in zip(enemies, wild.scales):
                    enemy.scale = scale
                route, boss = self.instance.route, wild is self.boss
                loot = wild_loot(route.boss_loot if boss else route.loot)
                trainer, prize = (self.trainer, route.prize) if boss else (
                    (wild.trainer.name, wild.trainer.prize) if wild.trainer else ("", 0))
                battle = BattleScene(self, self.party, enemies, self.bag, loot=loot,
                                     backdrop=self.level.theme.backdrop, boss=boss, trainer=trainer,
                                     prize=prize_money(prize, wild.encounter) if trainer else 0,
                                     bonus=boss_loot(route.boss_loot) if boss and not route.boss_chest else None,
                                     on_win=lambda key=route.key, defeated=[s for s, _ in wild.encounter]:
                                         quests.won_battle(self.game, key, defeated, self.battle_event),
                                     evolves=lambda m: quests.can_evolve(self.game, m))
                self.battle_event = quests.Event()  # quests a battle's drops start
                self.fighting = (wild, battle)
                self.next_scene = Transition(self, battle)
            wild.armed = not touching

    def draw_things(self, layer: pygame.Surface) -> None:
        self.entry.draw(layer)
        self.exit.draw(layer)
        for chest in self.chests:
            chest.draw(layer)
        for wild in self.wild:
            wild.draw(layer, self.debug)

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.panel:
            return
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

    def location(self) -> dict:
        """Where the run is at: the map, what's been beaten and opened on it,
        and where the player stands."""
        inst, p = self.instance, self.player
        return {
            "kind": "route", "route": inst.route.key, "destination": inst.destination,
            "seed": inst.seed, "map": inst.index,
            "beaten": [i for i, s in enumerate(self.level.spawns) if all(w.spawn is not s for w in self.wild)],
            "boss_beaten": bool(self.boss) and self.boss not in self.wild,
            "opened": [i for i, c in enumerate(self.chests) if c.opened],
            "player": [p.x, p.feet_y, p.facing],
        }

    def restore(self, state: dict) -> None:
        """Back to a saved `location` on this map."""
        beaten = [self.level.spawns[i] for i in state["beaten"]]
        self.wild = [w for w in self.wild if all(w.spawn is not s for s in beaten)]
        if state["boss_beaten"]:
            self.wild.remove(self.boss)
            self._boss_beaten()
        for i in state["opened"]:
            self.chests[i].opened = True
        p = self.player
        p.x, p.feet_y, p.facing = state["player"]
        self._follow()
        for wild in self.wild:  # don't start a battle just by loading next to a group
            wild.armed = not p.body_rect.colliderect(wild.body_rect)


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
