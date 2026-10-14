"""A map of a dungeon instance: generated and side-scrolling.

Touching wild Pokémon starts a battle (beaten ones are gone for the run),
chests open with Up, and the doorway at the end of the map leads on (Up).
On the last map a boss group guards the doorway out; beating it opens the
way and leaves a reward chest.
"""

import math
from typing import TYPE_CHECKING

import pygame

from . import settings, tileset, ui
from .battle import BattleScene
from .instance import Instance
from .items import Bag, Gear
from .level import Level, Spawn
from .loot import BOSS_LOOT, CHEST_LOOT, LootTable
from .player import Controls, Player
from .pokemon import SPECIES, Monster, animations
from .scene import Scene, Transition
from .summary import SummaryScene
from .themes import Palette

if TYPE_CHECKING:
    from .hub import HubScene

HELP = ("Left/Right: walk   Shift: run   Space: jump (hold = higher)   1-5: attack   Up: open / go through"
        "   Tab: party   F1: debug   Esc: quit")
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z, pygame.K_UP)

WOOD = (150, 96, 48)
WOOD_DARK = (96, 58, 28)
OUTLINE = (48, 28, 16)
GOLD = (232, 192, 72)
GROUP_SPACING = 30  # px between the members of a wild group, standing in a row


def new_game() -> tuple[list[Monster], Bag]:
    """The starting party and bag (with some gear and items, for trying things out)."""
    party = [Monster.create("bulbasaur", 5)]
    bag = Bag()
    for gear in [Gear.roll("Poison Barb", "Legendary", affixes=["Venomous", "of the Muk"]),
                 Gear.roll("Power Bracer", "Epic"), Gear.roll("Oran Berry"),
                 Gear.roll("Scope Lens", "Legendary"), Gear.roll("Assault Vest")]:
        bag.add(gear)
    for gear in list(bag.gear)[:3]:
        bag.equip(party[0], gear)
    for name, count in [("Potion", 3), ("Super Potion", 1), ("Revive", 1), ("Antidote", 2),
                        ("Paralyze Heal", 1), ("Full Heal", 1)]:
        bag.add_medicine(name, count)
    return party, bag


def draw_prompt(surface: pygame.Surface, x: float, top: float, t: float) -> None:
    """A bobbing arrow: press Up here."""
    x, top = round(x), round(top + math.sin(t * 6) * 2)
    for color, d in ((ui.SHADOW, 1), (ui.WHITE, 0)):
        pygame.draw.polygon(surface, color, [(x - 5 + d, top + 6 + d), (x + 5 + d, top + 6 + d), (x + d, top + d)])


class WildPokemon:
    """A group of wild Pokémon on the map, all shown, standing in a row
    behind the first. Touching them starts a battle against `encounter`:
    a list of (species, level)."""

    def __init__(self, spawn: Spawn, boss: bool = False):
        self.x, self.ground_y = spawn.x, spawn.feet_y
        self.encounter = spawn.encounter
        self.boss = boss
        self.members = [SPECIES[species] for species, _ in self.encounter]
        self.facing = -1
        # Only trigger once per touch, so returning from a battle (after
        # running away) while still touching them doesn't start another one.
        self.armed = True

    def _placed(self):
        """(species, idle animation, x, feet y) per member, the back ones first."""
        behind = -self.facing  # the others stand further from the player
        for i in reversed(range(len(self.members))):
            species = self.members[i]
            yield (species, animations(species)["idle"], self.x + behind * i * GROUP_SPACING,
                   self.ground_y + species.foot_sink)

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
    """A chest. Opening it rolls `loot` once; it stays open. A `fancy` one
    (the boss's reward) is trimmed with gold."""

    W, BODY_H, LID_H = 32, 16, 9  # size in logical px

    def __init__(self, x: float, feet_y: float, loot: LootTable = CHEST_LOOT, fancy: bool = False):
        self.x, self.feet_y = x, feet_y
        self.loot = loot
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


class OverworldScene(Scene):
    def __init__(self, instance: Instance, hub: "HubScene"):
        self.instance, self.hub = instance, hub
        self.party, self.bag = instance.party, instance.bag
        self.level: Level = instance.level()
        self.tiles = tileset.render(self.level)
        self.backgrounds = tileset.backgrounds(self.level)
        self.layer = pygame.Surface((self.level.width, settings.LOGICAL_SIZE[1]), pygame.SRCALPHA)

        level, palette = self.level, self.level.theme.palette
        self.player = Player(level.start_x, level.ground_y(level.start_x))
        self.wild = [WildPokemon(s) for s in level.spawns]
        self.boss = WildPokemon(level.boss, boss=True) if level.boss else None
        if self.boss:
            self.wild.append(self.boss)
        self.chests = [Chest(x, y) for x, y in level.chests]
        self.entry = Doorway(level.entry_x, level.ground_y(level.entry_x), palette)
        self.exit = Doorway(level.exit_x, level.ground_y(level.exit_x), palette, sealed=bool(self.boss))
        self.fighting: tuple[WildPokemon, BattleScene] | None = None
        self.panel: ui.ListPanel | None = None  # loot or a notice; the map waits
        self.after_panel = None  # what closing the panel does next
        self.camera = 0
        self.t = 0.0
        self.debug = False
        self.jump = False
        self.attack = 0
        self.fps = 0.0

    def _chest_at_player(self) -> Chest | None:
        """A closed chest the player is standing at."""
        return next((c for c in self.chests if not c.opened and self.player.body_rect.colliderect(c.rect)),
                    None)

    def _at_exit(self) -> bool:
        return not self.exit.sealed and self.player.body_rect.colliderect(self.exit.rect)

    def _open(self, chest: Chest) -> None:
        chest.opened = True
        rewards = chest.loot.roll()
        for r in rewards:
            r.give(self.bag)
        self.panel = ui.ListPanel("The chest contained:", [r.row() for r in rewards], (320, 140))

    def _go_on(self) -> None:
        """Through the doorway: the next map, or out of the dungeon after the last."""
        if self.instance.final:
            self.hub.finish(self.instance)
            self.next_scene = Transition(self, self.hub, flashes=0)
        else:
            self.instance.index += 1
            self.next_scene = Transition(self, OverworldScene(self.instance, self.hub), flashes=0)

    def _after_battle(self, wild: WildPokemon, battle: BattleScene) -> None:
        if battle.won:
            self.wild.remove(wild)
            if wild is self.boss:  # the way out opens, and the boss leaves a reward
                self.exit.sealed = False
                x = self.level.boss_chest_x
                self.chests.append(Chest(x, self.level.ground_y(x), BOSS_LOOT, fancy=True))
        elif battle.lost:
            self.panel = ui.ListPanel("Your party fainted...", [("You hurry back to safety.", ui.WHITE, "")],
                                      (320, 140))
            self.after_panel = lambda: self._leave(self.hub.welcome)

    def _leave(self, then) -> None:
        then()
        self.next_scene = Transition(self, self.hub, flashes=0)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if self.panel:
            if event.key in CONFIRM_KEYS:
                self.panel = None
                after, self.after_panel = self.after_panel, None
                if after:
                    after()
            return
        if event.key == pygame.K_UP:
            chest = self._chest_at_player()
            if chest:
                self._open(chest)
            elif self._at_exit():
                self._go_on()
        elif event.key == pygame.K_SPACE:
            self.jump = True
        elif pygame.K_1 <= event.key <= pygame.K_9:
            self.attack = event.key - pygame.K_0
        elif event.key == pygame.K_TAB:
            self.next_scene = SummaryScene(self, self.party, self.bag)
        elif event.key == pygame.K_F1:
            self.debug = not self.debug

    def update(self, dt: float) -> None:
        self.fps = 1 / dt if dt else 0.0
        self.t += dt
        if self.fighting:  # back from a battle
            self._after_battle(*self.fighting)
            self.fighting = None
        if self.panel:
            return
        keys = pygame.key.get_pressed()
        self.player.update(dt, Controls(
            left=keys[pygame.K_LEFT],
            right=keys[pygame.K_RIGHT],
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=self.jump,
            jump_held=keys[pygame.K_SPACE],
            attack=self.attack,
        ), self.level)
        self.jump, self.attack = False, 0
        view_w = settings.LOGICAL_SIZE[0]
        self.camera = round(max(0, min(self.level.width - view_w, self.player.x - view_w / 2)))

        for wild in self.wild:
            wild.facing = 1 if self.player.x > wild.x else -1
            touching = self.player.body_rect.colliderect(wild.body_rect)
            if touching and wild.armed:
                enemies = [Monster.create(species, level) for species, level in wild.encounter]
                battle = BattleScene(self, self.party, enemies, self.bag, backdrop=self.level.theme.backdrop)
                self.fighting = (wild, battle)
                self.next_scene = Transition(self, battle)
            wild.armed = not touching

    def draw(self, canvas: pygame.Surface) -> None:
        for layer, factor in zip(self.backgrounds, tileset.PARALLAX):
            canvas.blit(layer, (-round(self.camera * factor), 0))
        canvas.blit(self.tiles, (-self.camera, 0))
        # Everything on the map is drawn in map coordinates, then the part in
        # view is copied to the screen.
        self.layer.fill((0, 0, 0, 0))
        self.entry.draw(self.layer)
        self.exit.draw(self.layer)
        for chest in self.chests:
            chest.draw(self.layer)
        for wild in self.wild:
            wild.draw(self.layer, self.debug)
        self.player.draw(self.layer, self.debug)
        if not self.panel:
            chest = self._chest_at_player()
            if chest:
                draw_prompt(self.layer, chest.x, chest.feet_y - 62, self.t)
            elif self._at_exit():
                draw_prompt(self.layer, self.exit.x, self.exit.feet_y - 66, self.t)
        canvas.blit(self.layer, (0, 0), pygame.Rect(self.camera, 0, *settings.LOGICAL_SIZE))
        if self.panel:
            self.panel.draw(canvas)

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, HELP, (6, 4), size=20)
        inst = self.instance
        where = f"{inst.theme.name}   map {inst.index + 1}/{inst.maps}"
        if self.boss:
            where += "   the way out is guarded!" if self.boss in self.wild else "   the way out is open"
        ui.text(window, where, (6, 15), ui.WHITE, size=20)
        if self.debug:
            p, level = self.player, self.level
            ui.text(window, f"seed: {level.seed}   state: {p.state}   x: {p.x:.0f}  feet: {p.feet_y:.0f}"
                            f"   fps: {self.fps:.0f}", (6, 26), ui.YELLOW, size=20)
        if self.panel:
            self.panel.draw_overlay(window)
