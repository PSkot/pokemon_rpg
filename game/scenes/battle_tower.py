"""The Battle Tower's lobby (Celadon's west end; world/tower.py has the
rules): a one-screen marble hall where Mew floats, bobbing in the air. Up at
Mew opens its menu (`MewMenu`): Climb (a run from floor 1: Mew heals the
team first), the gem exchange (gear of a tier for 12 of its gem, in a slot
the player picks; and special Pokémon, each once), how the tower works, and
Leave. Up at the stairs at the back starts a run too; Up at the glass door
goes back out. Saving here (or on a floor) saves the player outside.

After each floor's master, `TowerChoice` asks: on up, or stop and claim the
run's chest (`claim`)."""

import math
import zlib

import pygame

from .. import settings
from ..engine import ui
from ..engine.scene import Transition
from ..mechanics.items import RARITIES, SLOT_NAMES, SLOTS
from ..mechanics.loot import Reward
from ..mechanics.pokemon import SPECIES, Monster
from ..world import quests, tileset, tower
from ..world.instance import Instance
from ..world.level import EMPTY, ROWS, SOLID, Level
from ..world.progress import Game
from ..world.towns import TOWNS, building_mid
from .mart import ShopMenu
from .overworld import MapScene, OverworldScene

NAME = "Battle Tower"
COLS = 40
GROUND = 4
DOOR_X = 44         # the glass door out
STAIRS_X = 604      # the grand stairs at the back (the wall's arch, right): up into the tower
MEW_X = 450         # in front of the great Poké Ball emblem
MEW_FLOAT = 96      # how high Mew floats over the floor (to its middle)
SPARKLES = 9        # glints circling it
MEW_SCALE = 2       # drawn 2× (the sprite is small; Mew's the host)
MEW_BOB, MEW_BOB_SPEED = 6, 1.6  # px, cycles a second
MEW_SWAY = 10       # it drifts sideways a little too
REACH = 26
GEM_COLORS = {"Quartz": (236, 236, 246), "Jade": (100, 214, 140), "Sapphire": (110, 156, 250),
              "Ruby": (240, 84, 100)}


def is_open(game: Game) -> bool:
    """Open once the Rainbow Badge is won (in dev mode: always)."""
    from ..dev import DEV
    return DEV.enabled or (tower.OPENS_AFTER in quests.QUESTS and quests.is_done(game, tower.OPENS_AFTER))


def lobby_location() -> dict:
    """A save in the tower (lobby or a floor) is a save outside its doors."""
    town = TOWNS[tower.LOBBY_TOWN]
    building = next(b for b in town.buildings if b.name == NAME)
    return {"kind": "town", "town": town.key, "x": building_mid(building), "facing": 1}


def _level() -> Level:
    surface = [ROWS - GROUND] * COLS
    grid = [[SOLID if row >= surface[col] else EMPTY for col in range(COLS)] for row in range(ROWS)]
    return Level(TOWNS[tower.LOBBY_TOWN].theme, zlib.crc32(b"battle tower lobby"), grid, surface)


def start_run(scene: MapScene) -> None:
    """Up the stairs: floor 1, with the team healed."""
    scene.game.heal()
    first = OverworldScene(Instance(tower.TOWER_ROUTES[tower.floor_key(1)], tower.LOBBY_TOWN), scene.game)
    scene.next_scene = Transition(scene, first, flashes=0)


def gem_row(gem: str, count: int) -> tuple[str, tuple[int, int, int], str]:
    return f"{count} {gem}", GEM_COLORS[gem], "gems"


def claim(game: Game, floor: int) -> ui.ListPanel:
    """Stop after `floor`: the run's chest, into the bag (shown as a list)."""
    rewards, gems = tower.chest(floor)
    for r in rewards:
        r.give(game.bag)
    game.bag.gems.update(gems)
    rows = [gem_row(g, gems[g]) for g in tower.GEMS if gems[g]] + [r.row() for r in rewards]
    return ui.ListPanel(f"The chest of floor {floor}:", rows, (320, 180), width=360)


class TowerLobbyScene(MapScene):
    in_town = False  # (no talent changes here: it's the tower)

    def __init__(self, game: Game):
        super().__init__(game, _level())
        self.ground = round(self.level.ground_y(0))
        self.tiles = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.backgrounds = [(tileset.room("tower", self.level.width, self.ground, [], DOOR_X), 0.0)]
        self.mew = pygame.transform.scale_by(tileset.prop("mew"), MEW_SCALE)  # (nearest-neighbour)
        self.place_player(DOOR_X + 40, 1)

    def where(self) -> str:
        return f"{NAME} lobby   best: floor {self.game.tower_best}" if self.game.tower_best else f"{NAME} lobby"

    def location(self) -> dict:
        return lobby_location()

    @property
    def mew_pos(self) -> tuple[float, float]:
        """Mew's middle: floating, bobbing and drifting."""
        x = MEW_X + MEW_SWAY * math.sin(self.t * MEW_BOB_SPEED * 0.37 * math.tau)
        y = self.ground - MEW_FLOAT + MEW_BOB * math.sin(self.t * MEW_BOB_SPEED * math.tau)
        return x, y

    def _at_mew(self) -> bool:
        return abs(self.player.x - self.mew_pos[0]) < REACH + 8

    def _at_stairs(self) -> bool:
        return abs(self.player.x - STAIRS_X) < REACH + 10

    def _at_door(self) -> bool:
        return abs(self.player.x - DOOR_X) < REACH

    def interact(self) -> None:
        if self._at_mew():
            menu = MewMenu(self.game)
            self.show(menu, after=lambda: menu.climb and start_run(self))
        elif self._at_stairs():
            ask = TowerChoice(0)
            self.show(ask, after=lambda: ask.picked == "climb" and start_run(self))
        elif self._at_door():
            from .town import TownScene
            town = TownScene(self.game, TOWNS[tower.LOBBY_TOWN], arrive=NAME)
            self.next_scene = Transition(self, town, flashes=0)

    def prompt(self) -> tuple[float, float] | None:
        if self._at_mew():
            x, y = self.mew_pos
            return x, y - self.mew.get_height() / 2 - 10
        if self._at_stairs():
            return STAIRS_X, self.ground - 96
        if self._at_door():
            return DOOR_X, self.ground - 84
        return None

    def draw_things(self, layer: pygame.Surface) -> None:
        x, y = self.mew_pos
        # A soft pink glow, glints circling it, and a shadow on the floor
        # (smaller the higher it bobs).
        glow = pygame.Surface((112, 112), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self.t * 3.1)
        for r, a in ((54, 26), (44, 40), (34, 55), (24, 70)):
            pygame.draw.circle(glow, (236, 110, 190, int(a * (0.7 + 0.3 * pulse))), (56, 56), r)
        layer.blit(glow, (x - 56, y - 56))
        for i in range(SPARKLES):
            angle = self.t * 1.3 + i * math.tau / SPARKLES
            sx, sy = x + 44 * math.cos(angle), y + 20 * math.sin(angle)
            if math.sin(angle) < 0:  # (behind Mew: drawn first, fainter)
                _sparkle(layer, sx, sy, 1, (255, 200, 240))
        lift = self.ground - y
        w = max(10, int(30 - lift * 0.12))
        shadow = pygame.Surface((w, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (40, 20, 40, 70), shadow.get_rect())
        layer.blit(shadow, (x - w / 2, self.ground - 3))
        image = pygame.transform.flip(self.mew, self.player.x > x, False)  # (it faces the player)
        layer.blit(image, (round(x - image.get_width() / 2), round(y - image.get_height() / 2)))
        for i in range(SPARKLES):
            angle = self.t * 1.3 + i * math.tau / SPARKLES
            if math.sin(angle) >= 0:  # (in front)
                twinkle = 2 if (int(self.t * 6) + i) % 3 == 0 else 1
                _sparkle(layer, x + 44 * math.cos(angle), y + 20 * math.sin(angle), twinkle, (255, 255, 255))

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        if self.panel:
            return
        x = 6
        for gem in tower.GEMS:  # what the bag holds, under where the player is
            label = f"{gem} {self.game.bag.gems[gem]}"
            ui.text(window, label, (x, 30), GEM_COLORS[gem], size=22)
            x += 10 + ui.font(22).size(label)[0] / settings.SCALE


def _sparkle(s: pygame.Surface, x: float, y: float, size: int, color) -> None:
    """A little four-pointed glint."""
    x, y = round(x), round(y)
    pygame.draw.line(s, color, (x - size, y), (x + size, y))
    pygame.draw.line(s, color, (x, y - size), (x, y + size))


class TowerChoice:
    """After floor `floor` (0: in the lobby, about to start): climb on, or
    stop and claim the chest. Floor 20 can only claim. X closes it undecided
    (`picked` ""): Up at the doorway asks again."""

    OPTIONS_ON = (("climb", "Climb on"), ("claim", "Stop and claim the chest"))
    CONFIRM, BACK = ShopMenu.CONFIRM, ShopMenu.BACK

    def __init__(self, floor: int):
        self.floor = floor
        if floor == 0:
            self.options = (("climb", "Climb (from floor 1)"), ("", "Not yet"))
        elif floor >= tower.FLOORS:
            self.options = (("claim", "Claim the summit's chest"),)
        else:
            self.options = self.OPTIONS_ON
        self.choice = 0
        self.picked = ""
        self.rect = pygame.Rect(0, 0, 380, 148)
        self.rect.center = (320, 170)

    def _lines(self) -> list[str]:
        f = self.floor
        if f == 0:
            return ["Every run starts on floor 1, with your team healed.",
                    "No healing between floors; losing ends the run with nothing."]
        if f >= tower.FLOORS:
            return ["You stand at the top of the Battle Tower!", "The summit's chest is yours."]
        nxt = f + 1
        gem = tower.GEMS[tower.tier(nxt)]
        return [f"Next: floor {nxt}, Lv{tower.floor_level(nxt)} ({tower.TIER_NAMES[tower.tier(nxt)]}).",
                f"Its chest would add {gem} gems. Your team stays as it is.",
                f"Or stop now and claim the chest of floor {f}."]

    def handle_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.options)
        elif key in self.CONFIRM:
            self.picked = self.options[self.choice][0]
            return True
        elif key in self.BACK:
            return True
        return False

    def _row_y(self, i: int) -> int:
        return self.rect.bottom - 18 - (len(self.options) - i) * 17

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.rect)
        ui.cursor(canvas, self.rect.x + 16, self._row_y(self.choice) + 6)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.rect
        title = "The Battle Tower" if self.floor == 0 else f"Floor {self.floor} cleared!"
        ui.text(window, title, (r.x + 12, r.y + 9), ui.YELLOW)
        for i, line in enumerate(self._lines()):
            ui.text(window, line, (r.x + 12, r.y + 29 + i * 13), ui.WHITE, size=22)
        for i, (_, label) in enumerate(self.options):
            ui.text(window, label, (r.x + 22, self._row_y(i)), ui.YELLOW if i == self.choice else ui.WHITE, size=26)
        ui.text(window, "Enter: choose   X: not now", (r.right - 12, r.bottom - 18), ui.GREY, size=20, align="right")


class MewMenu:
    """Mew's menu: Climb / Gem exchange / Pokémon / How it works / Leave.
    The exchange lists a row per tier (Left/Right: the slot); Pokémon each
    once (`Game.trainers` "mew:<species>")."""

    RECT = ShopMenu.RECT
    OPTIONS = ("Climb the tower", "Gem exchange: gear", "Gem exchange: Pokémon", "How it works", "Leave")
    ROW_H, PAD = 17, 9
    CONFIRM, BACK = ShopMenu.CONFIRM, ShopMenu.BACK
    GREETING = "Mew! ♪  (Mew loops around you, giggling. It seems to run this place.)"
    HELP = ("Twenty floors, each a hall of waves and a master's band; every fifth master is a giant.",
            "Every run starts on floor 1. No healing between floors, and losing ends the run.",
            "After each floor: climb on, or stop and claim a chest (medicine, gear and gems).",
            "Gems: Quartz from floor 1, Jade from 6, Sapphire from 11, Ruby from 16.",
            "No drops or prize money up there, but plenty of XP.")

    def __init__(self, game: Game):
        self.game, self.bag = game, game.bag
        self.mode = "main"  # "main", "gear", "pokemon", "confirm" or "help"
        self.list_mode = "gear"
        self.choice = self.item = 0
        self.slot = 0       # the gear exchange's slot (`SLOTS`)
        self.climb = False
        self.message = self.GREETING

    # --------------------------------------------------------------- state

    def _rows(self) -> list:
        return list(tower.GEM_GEAR) if self.list_mode == "gear" else list(tower.GEM_POKEMON)

    def _bought(self, species: str) -> bool:
        return f"mew:{species}" in self.game.trainers

    def _price(self, row) -> tuple[str, int]:
        return (row[0], tower.GEM_PRICE) if self.list_mode == "gear" else (row[2], row[3])

    # ---------------------------------------------------------------- keys

    def handle_key(self, key: int) -> bool:
        if self.mode == "main":
            return self._main_key(key)
        if self.mode == "help":
            if key in self.CONFIRM + self.BACK:
                self.mode, self.message = "main", "Mew!"
        elif self.mode == "confirm":
            self._confirm_key(key)
        else:
            self._list_key(key)
        return False

    def _main_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.OPTIONS)
        elif key in self.CONFIRM:
            option = self.OPTIONS[self.choice]
            if option == "Leave":
                return True
            if option.startswith("Climb"):
                self.climb = True  # (Mew's glow heals the team; the scene starts the run)
                return True
            if option == "How it works":
                self.mode = "help"
                return False
            self.mode = self.list_mode = "gear" if option.endswith("gear") else "pokemon"
            self.item = 0
            self.message = ("Mew? (Pick a gem and a slot. Mew conjures a piece.)" if self.list_mode == "gear"
                            else "Mew mew! (Friends who'd like to join a strong team.)")
        elif key in self.BACK:
            return True
        return False

    def _list_key(self, key: int) -> None:
        rows = self._rows()
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.item = (self.item + (1 if key == pygame.K_DOWN else -1)) % len(rows)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT) and self.list_mode == "gear":
            self.slot = (self.slot + (1 if key == pygame.K_RIGHT else -1)) % len(SLOTS)
        elif key in self.CONFIRM:
            row = rows[self.item]
            gem, price = self._price(row)
            if self.list_mode == "pokemon" and self._bought(row[0]):
                self.message = "Mew~ (They've already joined you.)"
            elif self.bag.gems[gem] < price:
                self.message = f"Mew... (That takes {price} {gem}; you have {self.bag.gems[gem]}.)"
            else:
                self.mode = "confirm"
                what = (f"a {SLOT_NAMES[SLOTS[self.slot]]} piece" if self.list_mode == "gear"
                        else SPECIES[row[0]].name)
                self.message = f"Trade {price} {gem} for {what}?"
        elif key in self.BACK:
            self.mode, self.message = "main", "Mew!"

    def _confirm_key(self, key: int) -> None:
        if key in self.CONFIRM:
            row = self._rows()[self.item]
            gem, price = self._price(row)
            self.bag.gems[gem] -= price
            if self.list_mode == "gear":
                gear = tower.gem_gear(self.item, SLOTS[self.slot])
                self.bag.add(gear)
                self.message = f"Mew! ✦ ({gear.name}, Lv{gear.level} {gear.rarity.name}.)"
            else:
                species, level = row[0], row[1]
                monster = Monster.create(species, level)
                joined = self.game.add_member(monster, quests.active_limit(self.game))
                self.game.trainers.add(f"mew:{species}")
                where = "joined your party" if joined == "party" else "went to the reserve (swap at Mr. Mime)"
                self.message = f"Mew mew! {monster.name} {where}!"
            self.mode = self.list_mode
        elif key in self.BACK:
            self.mode, self.message = self.list_mode, "Mew?"

    # ------------------------------------------------------------- drawing

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 50 + i * self.ROW_H * 2

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.mode == "main":
            ui.cursor(canvas, self.RECT.x + 16, self.RECT.y + self.PAD + 50 + self.choice * self.ROW_H + 6)
        elif self.mode in ("gear", "pokemon", "confirm"):
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.item) + 6)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        x, right = r.x + 22, r.right - 14
        title = {"main": "Mew", "help": "How the tower works"}.get(
            self.mode, "Gem exchange: gear" if self.list_mode == "gear" else "Gem exchange: Pokémon")
        ui.text(window, title, (r.x + 12, r.y + self.PAD), ui.YELLOW)
        gx = right
        for gem in reversed(tower.GEMS):
            label = f"{gem} {self.bag.gems[gem]}"
            ui.text(window, label, (gx, r.y + self.PAD + 2), GEM_COLORS[gem], size=20, align="right")
            gx -= 6 + ui.font(20).size(label)[0] / settings.SCALE
        if self.mode == "help":
            y = r.y + self.PAD + 22
            for para in self.HELP:
                for line in ui.wrap(para, 22, r.w - 26):
                    ui.text(window, line, (r.x + 12, y), ui.WHITE, size=22)
                    y += 12
                y += 5
            ui.text(window, "Enter: back", (right, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")
            return
        for i, line in enumerate(ui.wrap(self.message, 22, r.w - 26)[:2]):
            ui.text(window, line, (r.x + 12, r.y + self.PAD + 20 + i * 12), ui.WHITE, size=22)
        if self.mode == "main":
            for i, option in enumerate(self.OPTIONS):
                ui.text(window, option, (x, r.y + self.PAD + 50 + i * self.ROW_H),
                        ui.YELLOW if i == self.choice else ui.WHITE, size=26)
            hint = "Enter: choose   X: leave"
        elif self.list_mode == "gear":
            slot = SLOT_NAMES[SLOTS[self.slot]]
            for i, (gem, rarities, level) in enumerate(tower.GEM_GEAR):
                y = self._row_y(i)
                rarity = RARITIES[rarities[-1]]
                name = "/".join(rarities) + f" {slot}, Lv{level}"
                ui.text(window, name, (x, y), rarity.color, size=26)
                ui.text(window, f"{tower.GEM_PRICE} {gem}", (right, y), GEM_COLORS[gem], size=22, align="right")
                note = "special effect likely" if i == 3 else "rolled for you"
                ui.text(window, f"< {slot} >   {note}" if i == self.item else note, (x + 8, y + 14), ui.GREY,
                        size=20)
            hint = "Enter: trade   Left/Right: slot   X: back" if self.mode != "confirm" else "Enter: yes   X: no"
        else:
            for i, (species, level, gem, price) in enumerate(tower.GEM_POKEMON):
                y = self._row_y(i)
                done = self._bought(species)
                ui.text(window, f"{SPECIES[species].name} Lv{level}", (x, y), ui.GREY if done else ui.WHITE, size=26)
                ui.text(window, "joined" if done else f"{price} {gem}", (right, y),
                        ui.GREY if done else GEM_COLORS[gem], size=22, align="right")
                ui.text(window, "/".join(t.title() for t in SPECIES[species].types), (x + 8, y + 14), ui.GREY,
                        size=20)
            hint = "Enter: trade   X: back" if self.mode != "confirm" else "Enter: yes   X: no"
        ui.text(window, hint, (right, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")
