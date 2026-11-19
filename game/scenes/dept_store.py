"""The Celadon Department Store (`Building.inside = "dept"`): one screen per
floor, joined by stairs (Up at them), as in Red/Blue:

- 1F Lobby: Meowth at the information desk (the store guide); the glass
  door out to the street.
- 2F Trainer's Market: medicine (`ShopMenu`, `MARKET`).
- 3F Gear Gallery: Persian on its pile of gear (`GearShop`, the town's gear
  counter).
- 4F Smith Supplies: a Machop sells the smith's materials (`MaterialShop`,
  `items.MATERIAL_PRICE`).
- Rooftop: vending machines selling drinks (Fresh Water, Soda Pop,
  Lemonade) over the city.

Saving inside saves the player outside, at the store's door.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import pygame

from .. import settings
from ..engine import ui
from ..engine.scene import Transition
from ..mechanics.items import MATERIAL_PRICE, MATERIALS, RARITIES, Bag, money_text
from ..mechanics.pokemon import SPECIES, animations
from ..world import tileset
from ..world.level import EMPTY, ROWS, SOLID, Level
from ..world.progress import Game
from ..world.towns import Town, building_mid
from .mart import (COUNTER_W, DEN_STANDS, LOOSE_COINS, PERSIAN_W, SPILL_DROP, GearShop, ShopMenu, _coin)
from .overworld import MapScene

NAME = "Department Store"
COLS, GROUND = 40, 4
LEFT_X, RIGHT_X = 56, 584     # the glass door / stairs down, and the stairs up
COUNTER_X = 232               # the counter, with the clerk behind it
CLERK_X = COUNTER_X + COUNTER_W // 2
SHELVES = [392, 472]
VENDING = (248, 320, 392)     # the rooftop's machines
REACH = 24
MARKET = ("Potion", "Super Potion", "Hyper Potion", "Max Potion", "Revive", "Full Heal", "Escape Rope",
          "Antidote", "Burn Heal", "Awakening", "Paralyze Heal", "Ice Heal")
DRINKS = ("Fresh Water", "Soda Pop", "Lemonade")


@dataclass(frozen=True)
class Floor:
    key: str     # "1F", ..., "Roof"
    name: str    # "Trainer's Market"
    room: str    # its wall and floor (pixellab/rooms/<room>_wall.png, _floor.png)
    kind: str    # "guide", "shop", "gear", "materials" or "drinks"


FLOORS = (
    Floor("1F", "Lobby", "mart", "guide"),
    Floor("2F", "Trainer's Market", "mart", "shop"),
    Floor("3F", "Gear Gallery", "den", "gear"),
    Floor("4F", "Smith Supplies", "mart", "materials"),
    Floor("Roof", "Rooftop", "roof", "drinks"),
)

GUIDE = (("Meowth", "Welcome to the Celadon Department Store, meow! The biggest store in Kanto!"),
         ("Meowth", "2F: the Trainer's Market, for medicine. 3F: the Gear Gallery, Persian's very own."),
         ("Meowth", "4F: Smith Supplies, materials for working gear. And on the roof: drinks, and the view!"))


def _level(town: Town, floor: int) -> Level:
    surface = [ROWS - GROUND] * COLS
    grid = [[SOLID if row >= surface[col] else EMPTY for col in range(COLS)] for row in range(ROWS)]
    return Level(town.theme, zlib.crc32(f"{town.key} dept {floor}".encode()), grid, surface)


class DeptStoreScene(MapScene):
    in_town = True

    def __init__(self, game: Game, town: Town, floor: int = 0, came: str = "door"):
        """`came`: "door" (in from the street), "down" (up the stairs from
        below: at this floor's stairs down) or "up" (down from above)."""
        super().__init__(game, _level(town, floor))
        self.town, self.floor = town, FLOORS[floor]
        self.index = floor
        self.ground = round(self.level.ground_y(0))
        self.tiles = pygame.Surface((1, 1), pygame.SRCALPHA)
        kind = self.floor.kind
        doors = []
        if floor > 0:
            doors.append(("stairs_down", LEFT_X))
        if floor < len(FLOORS) - 1:
            doors.append(("stairs_up", RIGHT_X))
        shelves = SHELVES if kind in ("shop", "materials") else []
        room = tileset.room(self.floor.room, self.level.width, self.ground, shelves, LEFT_X if floor == 0 else None,
                            tuple(doors))
        if kind == "gear":  # Persian's gallery: its stands and coins
            for stand, x in DEN_STANDS:
                tileset.draw_prop(room, stand, x, self.ground)
            for dx, dy in LOOSE_COINS:
                _coin(room, CLERK_X + dx, self.ground + dy)
        if kind == "drinks":
            for x, machine in zip(VENDING, ("vending_machine", "vending_machine_2", "vending_machine_3")):
                tileset.draw_prop(room, machine, x, self.ground)
        self.backgrounds = [(room, 0.0)]
        if kind == "gear":
            self.clerk_frames = tileset.npc_frames("persian", PERSIAN_W)
        elif kind == "materials":  # (a Machop in an apron: the smith's apprentice)
            self.clerk_frames = animations(SPECIES["machop"])["idle"].frames
        elif kind != "drinks":
            self.clerk_frames = tileset.npc_frames("meowth")
        else:
            self.clerk_frames = []
        if came == "down":
            self.place_player(LEFT_X + 36, 1)
        elif came == "up":
            self.place_player(RIGHT_X - 36, -1)
        else:
            self.place_player(LEFT_X + 36, 1)

    def where(self) -> str:
        return f"{NAME} {self.floor.key}: {self.floor.name}"

    def location(self) -> dict:
        """Saved as standing outside, at the store's door."""
        building = next(b for b in self.town.buildings if b.inside == "dept")
        return {"kind": "town", "town": self.town.key, "x": building_mid(building), "facing": 1}

    # ---------------------------------------------------------------- where

    def _at_clerk(self) -> bool:
        if self.floor.kind == "drinks":
            return any(abs(self.player.x - x) < REACH for x in VENDING)
        reach = 44 if self.floor.kind == "gear" else COUNTER_W // 2 + REACH
        return abs(self.player.x - CLERK_X) < reach

    def _at_left(self) -> bool:
        return abs(self.player.x - LEFT_X) < REACH

    def _at_right(self) -> bool:
        return self.index < len(FLOORS) - 1 and abs(self.player.x - RIGHT_X) < REACH

    @property
    def clerk(self) -> pygame.Surface | None:
        if not self.clerk_frames:
            return None
        return self.clerk_frames[int(self.t * 6) % len(self.clerk_frames)]

    def interact(self) -> None:
        if self._at_left():
            if self.index == 0:  # out to the street
                from .town import TownScene  # (town.py enters this scene)
                self.next_scene = Transition(self, TownScene(self.game, self.town, arrive=NAME), flashes=0)
            else:
                self.next_scene = Transition(self, DeptStoreScene(self.game, self.town, self.index - 1, "up"),
                                             flashes=0)
        elif self._at_right():
            self.next_scene = Transition(self, DeptStoreScene(self.game, self.town, self.index + 1, "down"),
                                         flashes=0)
        elif self._at_clerk():
            kind = self.floor.kind
            if kind == "guide":
                from . import quest_ui
                self.show(quest_ui.Dialogue(list(GUIDE)))
            elif kind == "shop":
                self.show(ShopMenu(self.town, self.bag, MARKET, "Meowth! The Trainer's Market has it all, meow!",
                                   "Trainer's Market"))
            elif kind == "gear":
                self.show(GearShop(self.town, self.game))
            elif kind == "materials":
                self.show(MaterialShop(self.bag))
            else:
                self.show(ShopMenu(self.town, self.bag, DRINKS, "The machine hums. A cold drink, anyone?",
                                   "Vending machine"))

    def prompt(self) -> tuple[float, float] | None:
        if self._at_left():
            return LEFT_X, self.ground - 84
        if self._at_right():
            return RIGHT_X, self.ground - 84
        if self._at_clerk():
            if self.floor.kind == "drinks":
                x = min(VENDING, key=lambda v: abs(self.player.x - v))
                return x, self.ground - 56
            image = self.clerk
            return CLERK_X, self.ground - (image.get_height() if image else 40) - 12
        return None

    def draw_things(self, layer: pygame.Surface) -> None:
        image, kind = self.clerk, self.floor.kind
        if image is not None:  # (4F's Machop is too short for the counter: it stands beside it)
            x = COUNTER_X + COUNTER_W + 18 if kind == "materials" else CLERK_X
            if kind == "materials":  # (facing the counter)
                image = pygame.transform.flip(image, True, False)
            layer.blit(image, (x - image.get_width() // 2, self.ground - image.get_height()))
        if kind == "gear":
            tileset.draw_prop(layer, "coin_spill", CLERK_X, self.ground + SPILL_DROP)
        elif kind in ("guide", "shop", "materials"):
            tileset.mart_counter(layer, COUNTER_X, self.ground, COUNTER_W)
            tileset.mart_sign(layer, CLERK_X, 70)

    def draw_overlay(self, window: pygame.Surface) -> None:
        if self.floor.kind in ("guide", "shop", "materials"):
            ui.text(window, f"{self.floor.key} {self.floor.name.upper()}", (CLERK_X, 74), ui.WHITE, size=20,
                    align="center")
        for x, step in ((LEFT_X, -1 if self.index else 0), (RIGHT_X, 1 if self._has_up else 0)):
            if step:  # where each staircase goes
                floor = FLOORS[self.index + step]
                ui.text(window, f"{'Up' if step > 0 else 'Down'} to {floor.key}", (x - self.camera, self.ground - 92),
                        ui.YELLOW, size=20, align="center")
        super().draw_overlay(window)

    @property
    def _has_up(self) -> bool:
        return self.index < len(FLOORS) - 1


class MaterialShop:
    """4F: the smith's materials for sale (Scrap, Alloy, Crystal; `MATERIAL_PRICE`),
    one at a time. A panel like the shops."""

    RECT = ShopMenu.RECT
    ROW_H, PAD = 17, 9
    CONFIRM, BACK = ShopMenu.CONFIRM, ShopMenu.BACK

    def __init__(self, bag: Bag):
        self.bag = bag
        self.items = list(MATERIAL_PRICE)
        self.item = 0
        self.message = "Mach! Materials for working gear. The smith's own. Buy one?"

    def handle_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.item = (self.item + (1 if key == pygame.K_DOWN else -1)) % len(self.items)
        elif key in self.CONFIRM:
            name = self.items[self.item]
            price = MATERIAL_PRICE[name]
            if self.bag.money < price:
                self.message = "Mach... Not enough money for that one."
            else:
                self.bag.money -= price
                self.bag.materials[name] += 1
                self.message = f"One {name}! Mach! (You have {self.bag.materials[name]}.)"
        elif key in self.BACK:
            return True
        return False

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.item) + 6)

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 46 + i * self.ROW_H

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        x, right = r.x + 22, r.right - 14
        ui.text(window, "Smith Supplies", (r.x + 12, r.y + self.PAD), ui.YELLOW)
        ui.text(window, money_text(self.bag.money), (right, r.y + self.PAD + 2), ui.YELLOW, size=24, align="right")
        for i, line in enumerate(ui.wrap(self.message, 22, r.w - 26)[:2]):
            ui.text(window, line, (r.x + 12, r.y + self.PAD + 20 + i * 12), ui.WHITE, size=22)
        rarities = {m: r for r, m in MATERIALS.items()}
        for i, name in enumerate(self.items):
            y = self._row_y(i)
            ui.text(window, name, (x, y), RARITIES[rarities[name]].color, size=24)
            ui.text(window, f"have {self.bag.materials[name]}   {money_text(MATERIAL_PRICE[name])}", (right, y + 2),
                    ui.GREY, size=20, align="right")
        ui.text(window, "Used by the smith to enhance gear (and smelted into rarer ones).", (r.x + 12,
                self._row_y(len(self.items)) + 8), ui.GREY, size=18)
        ui.text(window, "Enter: buy one   X: leave", (right, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")
