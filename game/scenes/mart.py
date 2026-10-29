"""Inside a Poké Mart: a one-screen room run by a Meowth behind the counter.

Up at the counter talks to Meowth: a quest step at the Poké Mart if there
is one, else the shop (`ShopMenu`: buy the town's medicine, sell the bag's
for half). Up at the glass door goes back out into the town. Saving here
saves the player outside, at the shop's door.
"""

import zlib

import pygame

from .. import saves, settings
from ..engine import ui
from ..engine.scene import Transition
from ..mechanics.items import MEDICINE, Bag, money_text
from ..world import quests, tileset
from ..world.level import EMPTY, ROWS, SOLID, TILE, Level
from ..world.progress import Game
from ..world.towns import Town, building_mid
from .overworld import MapScene

NAME = "Poké Mart"  # the building's name (quest steps visit it)
COLS = 40           # one screen wide
GROUND = 4          # tiles of floor
COUNTER_X, COUNTER_W = 40, 136
MEOWTH_X = 92       # behind the counter
MEOWTH_LIFT = 0     # Meowth stands on the floor: it peeps over the counter
MEOWTH_FPS = 6         # Meowth's idle animation
SHELVES = [232, 328, 424]
DOOR_X = 592
REACH = 24          # how close the player must be to the counter or door

MAX_AMOUNT = 99


def _level(town: Town) -> Level:
    surface = [ROWS - GROUND] * COLS
    grid = [[SOLID if row >= surface[col] else EMPTY for col in range(COLS)] for row in range(ROWS)]
    return Level(town.theme, zlib.crc32(f"{town.key} mart".encode()), grid, surface)


class MartScene(MapScene):
    in_town = True

    def __init__(self, game: Game, town: Town):
        super().__init__(game, _level(town))
        self.town = town
        self.ground = round(self.level.ground_y(0))
        self.tiles = pygame.Surface((1, 1), pygame.SRCALPHA)  # the floor is part of the room
        self.backgrounds = [(tileset.room("mart", self.level.width, self.ground, SHELVES, DOOR_X), 0.0)]
        self.meowth_frames = tileset.npc_frames("meowth")
        self.place_player(DOOR_X - 36, -1)

    def where(self) -> str:
        return f"{self.town.name} {NAME}"

    def location(self) -> dict:
        """Saved as standing outside, at the shop's door."""
        building = next(b for b in self.town.buildings if b.inside == "mart")
        return {"kind": "town", "town": self.town.key, "x": building_mid(building), "facing": 1}

    def _at_counter(self) -> bool:
        return self.player.x < COUNTER_X + COUNTER_W + REACH

    def _at_door(self) -> bool:
        return abs(self.player.x - DOOR_X) < REACH

    @property
    def meowth(self) -> pygame.Surface:
        return self.meowth_frames[int(self.t * MEOWTH_FPS) % len(self.meowth_frames)]

    @property
    def _meowth_top(self) -> float:
        return self.ground - MEOWTH_LIFT - self.meowth.get_height()

    def interact(self) -> None:
        if self._at_counter():
            event = quests.visit(self.game, self.town.key, NAME)
            if event:
                self.show_event(event)
                saves.autosave(self)
            else:
                self.show(ShopMenu(self.town, self.bag))
        elif self._at_door():
            from .town import TownScene  # (town.py enters this scene)
            self.next_scene = Transition(self, TownScene(self.game, self.town, arrive=NAME), flashes=0)

    def prompt(self) -> tuple[float, float] | None:
        if self._at_counter():
            return MEOWTH_X, self._meowth_top - 12
        if self._at_door():
            return DOOR_X, self.ground - 84
        return None

    def markers(self) -> list[tuple[float, float]]:
        for quest in quests.active(self.game):
            step = quests.current(self.game, quest.key)
            if step.kind == "visit" and step.town == self.town.key and step.target == NAME:
                return [(MEOWTH_X, self._meowth_top - 4)]
        return []

    def draw_things(self, layer: pygame.Surface) -> None:
        image = self.meowth
        layer.blit(image, (MEOWTH_X - image.get_width() // 2, self._meowth_top))
        tileset.mart_counter(layer, COUNTER_X, self.ground, COUNTER_W)
        tileset.mart_sign(layer, COUNTER_X + COUNTER_W // 2, 70)

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, "POKé MART", (COUNTER_X + COUNTER_W / 2, 74), ui.WHITE, size=26, align="center")
        super().draw_overlay(window)


class ShopMenu:
    """Meowth's shop, a panel over the mart (like quest_ui's screens):
    Buy (the town's stock) / Sell (the bag's medicine, for half) / Leave.
    Picking an item asks how many (Up/Down ±1, Left/Right ±10)."""

    RECT = pygame.Rect(236, 52, 398, 292)
    OPTIONS = ("Buy", "Sell", "Leave")
    ROW_H = 17
    PAD = 9
    CONFIRM = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
    BACK = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
    GREETING = "Meowth! Welcome to the Poké Mart, meow! What'll it be?"

    def __init__(self, town: Town, bag: Bag):
        self.stock, self.bag = list(town.mart), bag
        self.mode = "main"  # "main", "buy", "sell" or "amount" (how many, of `self.list_mode`'s item)
        self.list_mode = "buy"
        self.choice = 0     # in the main menu
        self.item = 0       # in the buy / sell list
        self.amount = 1
        self.message = self.GREETING

    # ---------------------------------------------------------------- state

    def _items(self, mode: str | None = None) -> list[str]:
        if (mode or self.mode) == "buy":
            return self.stock
        return [name for name in MEDICINE if self.bag.medicine.get(name)]  # (in MEDICINE's order)

    @property
    def _selected(self) -> str | None:
        items = self._items(self.list_mode)
        return items[self.item] if items else None

    def _price(self, name: str) -> int:
        m = MEDICINE[name]
        return m.price if self.list_mode == "buy" else m.sell_price

    def _max_amount(self, name: str) -> int:
        if self.list_mode == "buy":
            return min(MAX_AMOUNT, self.bag.money // MEDICINE[name].price)
        return self.bag.medicine[name]

    # ----------------------------------------------------------------- keys

    def handle_key(self, key: int) -> bool:
        """Returns True once the shop is closed."""
        if self.mode == "main":
            return self._main_key(key)
        if self.mode == "amount":
            self._amount_key(key)
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
            self.mode = self.list_mode = option.lower()
            self.item = 0
            self.message = "Take your time, meow." if option == "Buy" else "What'll you sell me, meow?"
        elif key in self.BACK:
            return True
        return False

    def _list_key(self, key: int) -> None:
        items = self._items()
        if key in (pygame.K_UP, pygame.K_DOWN) and items:
            self.item = (self.item + (1 if key == pygame.K_DOWN else -1)) % len(items)
        elif key in self.CONFIRM and items:
            name = items[self.item]
            if self._max_amount(name) < 1:
                self.message = "You can't afford that, meow!"
                return
            self.mode, self.amount = "amount", 1
            self.message = f"How many {name}s, meow?"
        elif key in self.BACK:
            self.mode, self.message = "main", "Anything else, meow?"

    def _amount_key(self, key: int) -> None:
        name = self._selected
        most = self._max_amount(name)
        steps = {pygame.K_UP: 1, pygame.K_DOWN: -1, pygame.K_RIGHT: 10, pygame.K_LEFT: -10}
        if key in steps:
            self.amount = max(1, min(most, self.amount + steps[key]))
        elif key in self.CONFIRM:
            total = self.amount * self._price(name)
            things = f"{self.amount} {name}{'s' if self.amount > 1 else ''}"
            if self.list_mode == "buy":
                self.bag.money -= total
                self.bag.add_medicine(name, self.amount)
                self.message = f"Here you go: {things}! Thank you, meow!"
            else:
                self.bag.money += total
                for _ in range(self.amount):
                    self.bag.use_medicine(name)
                self.message = f"Sold {things} for {money_text(total)}. Pleasure, meow!"
                self.item = max(0, min(self.item, len(self._items("sell")) - 1))
            self.mode = self.list_mode
        elif key in self.BACK:
            self.mode, self.message = self.list_mode, "Changed your mind, meow?"

    # -------------------------------------------------------------- drawing

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 46 + i * self.ROW_H

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.mode == "main":
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.choice) + 6)
        elif self._items(self.list_mode):
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.item) + 6)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        x, right = r.x + 22, r.right - 14
        title = {"main": "Poké Mart", "buy": "Buy", "sell": "Sell"}.get(self.mode, self.list_mode.title())
        ui.text(window, title, (r.x + 12, r.y + self.PAD), ui.YELLOW)
        ui.text(window, money_text(self.bag.money), (right, r.y + self.PAD + 2), ui.YELLOW, size=24, align="right")
        for i, line in enumerate(ui.wrap(self.message, 22, r.w - 26)[:2]):
            ui.text(window, line, (r.x + 12, r.y + self.PAD + 20 + i * 12), ui.WHITE, size=22)
        if self.mode == "main":
            for i, option in enumerate(self.OPTIONS):
                ui.text(window, option, (x, self._row_y(i)), ui.YELLOW if i == self.choice else ui.WHITE, size=26)
            hint = "Enter: choose   X: leave"
        else:
            self._draw_list(window, x, right)
            hint = ("Up/Down: 1   Left/Right: 10   Enter: OK   X: back" if self.mode == "amount"
                    else "Enter: choose   X: back")
        ui.text(window, hint, (right, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")

    def _draw_list(self, window: pygame.Surface, x: int, right: int) -> None:
        r, items = self.RECT, self._items(self.list_mode)
        if not items:
            ui.text(window, "You've got nothing to sell, meow.", (x, self._row_y(0)), ui.GREY, size=24)
            return
        for i, name in enumerate(items):
            color = ui.YELLOW if i == self.item else ui.WHITE
            label = name if self.list_mode == "buy" else f"{name}  x{self.bag.medicine[name]}"
            ui.text(window, label, (x, self._row_y(i)), color, size=26)
            ui.text(window, money_text(self._price(name)), (right, self._row_y(i) + 2), ui.GREY, size=22,
                    align="right")
        name = items[self.item]
        info_y = r.bottom - self.PAD - 46
        s = settings.SCALE
        pygame.draw.line(window, ui.GREY, ((r.x + 12) * s, (info_y - 5) * s), ((r.right - 12) * s, (info_y - 5) * s))
        if self.mode == "amount":
            total = money_text(self.amount * self._price(name))
            ui.text(window, f"{name}  × {self.amount}", (r.x + 14, info_y), ui.WHITE, size=26)
            ui.text(window, total, (right, info_y), ui.YELLOW, size=26, align="right")
        else:
            ui.text(window, MEDICINE[name].description, (r.x + 14, info_y), ui.WHITE, size=22)
            ui.text(window, f"In bag: {self.bag.medicine.get(name, 0)}", (r.x + 14, info_y + 14), ui.GREY, size=22)
