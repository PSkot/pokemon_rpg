"""Inside a Poké Mart: a one-screen room run by a Meowth behind the counter.

Up at the counter talks to Meowth: a quest step at the Poké Mart if there
is one, else the shop (`ShopMenu`: buy the town's medicine, sell the bag's
for half). In towns with a gear counter, a curtained doorway at the back
leads to Persian's den (`DenScene`): Persian lazes on a pile of gear there,
and Up at it opens the gear counter (`GearShop`: buy the pieces on offer,
`towns.gear_stock`, restocked each time the player arrives in the town from
a route; sell the bag's gear for half its worth). Up at the glass door goes
back out into the town. Saving in either room saves the player outside, at
the shop's door.
"""

import zlib

import pygame

from .. import saves, settings
from ..engine import ui
from ..engine.scene import Transition
from ..mechanics.items import EFFECT_COLOR, MEDICINE, SLOT_NAMES, Bag, Gear, mod_text, money_text
from ..world import quests, tileset
from ..world.level import EMPTY, ROWS, SOLID, TILE, Level
from ..world.progress import Game
from ..world.towns import Town, building_mid, gear_stock
from .overworld import MapScene, quest_mark

NAME = "Poké Mart"  # the building's name (quest steps visit it)
COLS = 40           # one screen wide
GROUND = 4          # tiles of floor
COUNTER_X, COUNTER_W = 40, 136
MEOWTH_X = 92       # behind the counter
MEOWTH_LIFT = 0     # Meowth stands on the floor: it peeps over the counter
MEOWTH_FPS = 6         # Meowth's idle animation
SHELVES = [232, 328, 424]
DOOR_X = 592
BACK_X = 532        # the curtained doorway to Persian's den, between the last shelf and the glass door
PERSIAN_FPS = 5
PERSIAN_W = 80      # its frames' width (lying on its pile of gear)
REACH = 24          # how close the player must be to the counter or door

MAX_AMOUNT = 99


def _level(town: Town) -> Level:
    surface = [ROWS - GROUND] * COLS
    grid = [[SOLID if row >= surface[col] else EMPTY for col in range(COLS)] for row in range(ROWS)]
    return Level(town.theme, zlib.crc32(f"{town.key} mart".encode()), grid, surface)


class MartScene(MapScene):
    in_town = True

    def __init__(self, game: Game, town: Town, from_den: bool = False):
        super().__init__(game, _level(town))
        self.town = town
        self.ground = round(self.level.ground_y(0))
        self.tiles = pygame.Surface((1, 1), pygame.SRCALPHA)  # the floor is part of the room
        doors = (("den_curtain", BACK_X),) if town.gear else ()
        self.backgrounds = [(tileset.room("mart", self.level.width, self.ground, SHELVES, DOOR_X, doors), 0.0)]
        self.meowth_frames = tileset.npc_frames("meowth")
        if from_den:
            self.place_player(BACK_X, -1)
        else:
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

    def _at_back(self) -> bool:
        return bool(self.town.gear) and abs(self.player.x - BACK_X) < REACH and not self._at_door()

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
        elif self._at_back():
            self.next_scene = Transition(self, DenScene(self.game, self.town), flashes=0)
        elif self._at_door():
            from .town import TownScene  # (town.py enters this scene)
            self.next_scene = Transition(self, TownScene(self.game, self.town, arrive=NAME), flashes=0)

    def prompt(self) -> tuple[float, float] | None:
        if self._at_counter():
            return MEOWTH_X, self._meowth_top - 12
        if self._at_back():
            return BACK_X, self.ground - 84
        if self._at_door():
            return DOOR_X, self.ground - 84
        return None

    def markers(self) -> list[tuple[float, float]]:
        for quest in quests.active(self.game):
            step = quests.current(self.game, quest.key)
            if step.kind == "visit" and step.town == self.town.key and step.target == NAME:
                return [(MEOWTH_X, self._meowth_top - 4, quest_mark(quest))]
        return []

    def draw_things(self, layer: pygame.Surface) -> None:
        image = self.meowth
        layer.blit(image, (MEOWTH_X - image.get_width() // 2, self._meowth_top))
        tileset.mart_counter(layer, COUNTER_X, self.ground, COUNTER_W)
        tileset.mart_sign(layer, COUNTER_X + COUNTER_W // 2, 70)

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, "POKé MART", (COUNTER_X + COUNTER_W / 2, 74), ui.WHITE, size=26, align="center")
        super().draw_overlay(window)


DEN_CURTAIN_X = 56            # the way back into the mart
DEN_PERSIAN_X = 320          # Persian on its pile, under its own portrait
DEN_STANDS = (("gear_stand", 172), ("gear_stand_2", 468))  # gilded stands showing off gear
PERSIAN_REACH = 44           # (its pile is wide)
SPILL_DROP = 4
# Loose coins on the den's carpet: (x from Persian, y below the floor line).
LOOSE_COINS = ((-96, 7), (-78, 13), (-120, 18), (88, 6), (104, 15), (130, 9), (-30, 22), (52, 20), (190, 17))


def _coin(s: pygame.Surface, x: int, y: int) -> None:
    """A gold coin lying flat on the floor (5×3 px, outlined)."""
    pygame.draw.ellipse(s, (120, 80, 20), (x - 3, y - 2, 7, 4))
    pygame.draw.ellipse(s, (240, 190, 50), (x - 2, y - 1, 5, 2))
    s.set_at((x - 1, y - 1), (255, 240, 150))              # the coins spilling from its pile lie this far down the carpet


class DenScene(MapScene):
    """Persian's den behind a Poké Mart: a lavish one-screen room where
    Persian lazes on its pile of gear and coins. Up at Persian opens the gear
    counter (`GearShop`); Up at the curtain goes back into the mart."""
    in_town = True

    def __init__(self, game: Game, town: Town):
        super().__init__(game, _level(town))
        self.town = town
        self.ground = round(self.level.ground_y(0))
        self.tiles = pygame.Surface((1, 1), pygame.SRCALPHA)
        room = tileset.room("den", self.level.width, self.ground, [], None, (("den_curtain", DEN_CURTAIN_X),))
        for stand, x in DEN_STANDS:
            tileset.draw_prop(room, stand, x, self.ground)
        for dx, dy in LOOSE_COINS:  # strays from Persian's pile, out on the carpet
            _coin(room, DEN_PERSIAN_X + dx, self.ground + dy)
        self.backgrounds = [(room, 0.0)]
        self.persian_frames = tileset.npc_frames("persian", PERSIAN_W)
        self.place_player(DEN_CURTAIN_X + 36, 1)

    def where(self) -> str:
        return f"{self.town.name} {NAME}: Persian's den"

    def location(self) -> dict:
        return MartScene.location(self)

    @property
    def persian(self) -> pygame.Surface:
        return self.persian_frames[int(self.t * PERSIAN_FPS) % len(self.persian_frames)]

    def _at_persian(self) -> bool:
        return abs(self.player.x - DEN_PERSIAN_X) < PERSIAN_REACH

    def _at_curtain(self) -> bool:
        return abs(self.player.x - DEN_CURTAIN_X) < REACH

    def interact(self) -> None:
        if self._at_persian():
            self.show(GearShop(self.town, self.game))
        elif self._at_curtain():
            self.next_scene = Transition(self, MartScene(self.game, self.town, from_den=True), flashes=0)

    def prompt(self) -> tuple[float, float] | None:
        if self._at_persian():
            return DEN_PERSIAN_X, self.ground - self.persian.get_height() - 12
        if self._at_curtain():
            return DEN_CURTAIN_X, self.ground - 84
        return None

    def draw_things(self, layer: pygame.Surface) -> None:
        image = self.persian
        layer.blit(image, (DEN_PERSIAN_X - image.get_width() // 2, self.ground - image.get_height()))
        # The coins spilling from its pile, in front of the pile's foot.
        tileset.draw_prop(layer, "coin_spill", DEN_PERSIAN_X, self.ground + SPILL_DROP)


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


class GearShop:
    """Persian's gear counter, a panel over the mart like `ShopMenu`: Buy
    (the pieces on offer, `towns.gear_stock`) / Sell (the bag's gear, for
    half its price) / Leave. One piece at a time, each asked to confirm."""

    RECT = ShopMenu.RECT
    OPTIONS = ("Buy", "Sell", "Leave")
    ROW_H, PAD, ROWS = 15, 9, 6
    CONFIRM, BACK = ShopMenu.CONFIRM, ShopMenu.BACK
    GREETING = "*Yawn*... Oh. A customer. Buying, selling, or just blocking my light?"

    def __init__(self, town: Town, game: Game):
        self.town, self.game, self.bag = town, game, game.bag
        visit = game.shop_visits.get(town.key, 0)
        self.stock = gear_stock(town, game.seed, visit)  # (bought ones stay out of the list)
        self.mode = "main"   # "main", "buy", "sell" or "confirm" (buying or selling `list_mode`'s piece)
        self.list_mode = "buy"
        self.choice = 0
        self.item = self.top = 0
        self.message = self.GREETING

    # ---------------------------------------------------------------- state

    @property
    def _bought(self) -> list[int]:
        return self.game.shop_bought.setdefault(self.town.key, [])

    def _pieces(self, mode: str | None = None) -> list[Gear]:
        if (mode or self.mode) == "buy":
            return [g for i, g in enumerate(self.stock) if i not in self._bought]
        return self.bag.gear

    @property
    def _selected(self) -> Gear | None:
        pieces = self._pieces(self.list_mode)
        return pieces[self.item] if 0 <= self.item < len(pieces) else None

    def _price(self, gear: Gear) -> int:
        return gear.price if self.list_mode == "buy" else gear.sell_price

    def _wearable(self, gear: Gear) -> bool:
        return any(gear.usable_by(m) for m in self.game.party + self.game.reserve)

    # ----------------------------------------------------------------- keys

    def handle_key(self, key: int) -> bool:
        """Returns True once the shop is closed."""
        if self.mode == "main":
            return self._main_key(key)
        if self.mode == "confirm":
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
            self.mode = self.list_mode = option.lower()
            self.item = self.top = 0
            self.message = ("Look all you like. I get new things whenever you've been away a while." if option == "Buy"
                            else "Fine. Show me what you dragged in.")
        elif key in self.BACK:
            return True
        return False

    def _list_key(self, key: int) -> None:
        pieces = self._pieces()
        if key in (pygame.K_UP, pygame.K_DOWN) and pieces:
            self.item = (self.item + (1 if key == pygame.K_DOWN else -1)) % len(pieces)
            self.top = min(self.item, max(self.top, self.item - self.ROWS + 1))
        elif key in self.CONFIRM and pieces:
            gear = pieces[self.item]
            if self.list_mode == "buy" and self.bag.money < gear.price:
                self.message = "Hmph. Come back when you can afford it."
                return
            self.mode = "confirm"
            verb = "Buy" if self.list_mode == "buy" else "Sell"
            self.message = f"{verb} the {gear.name} for {money_text(self._price(gear))}?"
        elif key in self.BACK:
            self.mode, self.message = "main", "Mm. Anything else?"

    def _confirm_key(self, key: int) -> None:
        gear = self._selected
        if key in self.CONFIRM:
            if self.list_mode == "buy":
                self.bag.money -= gear.price
                self.bag.add(gear)
                self._bought.append(self.stock.index(gear))
                self.message = f"The {gear.name}. Yours. Now let me nap."
            else:
                self.bag.money += gear.sell_price
                self.bag.gear.remove(gear)
                self.message = f"{money_text(gear.sell_price)}. Take it or leave it... you took it."
            pieces = self._pieces(self.list_mode)
            self.item = max(0, min(self.item, len(pieces) - 1))
            self.top = max(0, min(self.top, len(pieces) - self.ROWS))
            self.mode = self.list_mode
        elif key in self.BACK:
            self.mode, self.message = self.list_mode, "Whatever."

    # -------------------------------------------------------------- drawing

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 46 + i * self.ROW_H

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.mode == "main":
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.choice) + 6)
        elif self._pieces(self.list_mode):
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.item - self.top) + 5)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        x, right = r.x + 22, r.right - 14
        title = {"main": "Gear counter", "buy": "Buy gear", "sell": "Sell gear"}.get(
            self.mode, "Buy gear" if self.list_mode == "buy" else "Sell gear")
        ui.text(window, title, (r.x + 12, r.y + self.PAD), ui.YELLOW)
        ui.text(window, money_text(self.bag.money), (right, r.y + self.PAD + 2), ui.YELLOW, size=24, align="right")
        for i, line in enumerate(ui.wrap(self.message, 22, r.w - 26)[:2]):
            ui.text(window, line, (r.x + 12, r.y + self.PAD + 20 + i * 12), ui.WHITE, size=22)
        if self.mode == "main":
            for i, option in enumerate(self.OPTIONS):
                ui.text(window, option, (x, ShopMenu._row_y(self, i)), ui.YELLOW if i == self.choice else ui.WHITE,
                        size=26)
            hint = "Enter: choose   X: leave"
        else:
            self._draw_list(window, x, right)
            hint = "Enter: yes   X: no" if self.mode == "confirm" else "Enter: choose   X: back"
        ui.text(window, hint, (right, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")

    def _draw_list(self, window: pygame.Surface, x: int, right: int) -> None:
        r, pieces = self.RECT, self._pieces(self.list_mode)
        if not pieces:
            empty = ("That's all of it. Go away for a while, then come back." if self.list_mode == "buy"
                     else "You've no gear in your bag to sell.")
            ui.text(window, empty, (x, self._row_y(0)), ui.GREY, size=22)
            return
        shown = pieces[self.top:self.top + self.ROWS]
        for i, gear in enumerate(shown):
            y = self._row_y(i)
            price = money_text(self._price(gear))
            room = right - x - ui.font(20).size(price)[0] / settings.SCALE - 10
            ui.text(window, _fit(gear.name, 22, room), (x, y), gear.rarity.color, size=22)
            ui.text(window, price, (right, y + 1), ui.GREY, size=20, align="right")
        if self.top > 0:
            ui.text(window, "more above", (right, self._row_y(0) - 9), ui.GREY, size=16, align="right")
        if self.top + self.ROWS < len(pieces):
            ui.text(window, "more below", (right, self._row_y(self.ROWS) - 5), ui.GREY, size=16, align="right")
        gear = pieces[self.item]
        y = self._row_y(self.ROWS) + 8
        s = settings.SCALE
        pygame.draw.line(window, ui.GREY, ((r.x + 12) * s, (y - 4) * s), ((r.right - 12) * s, (y - 4) * s))
        level_color = ui.GREY if self._wearable(gear) else (240, 110, 100)
        ui.text(window, f"Lv{gear.level} {gear.rarity.name} {SLOT_NAMES[gear.slot]} item", (r.x + 14, y),
                level_color, size=22)
        if not self._wearable(gear):
            ui.text(window, "(no one is that level yet)", (right, y), level_color, size=20, align="right")
        y += 14
        effect = gear.special  # (its special effect, in red, in place of the description)
        about = f"{effect.name}: {effect.text}" if effect else gear.item.description
        for line in ui.wrap(about, 20, r.w - 28)[:2]:
            ui.text(window, line, (r.x + 14, y), EFFECT_COLOR if effect else ui.WHITE, size=20)
            y += 12
        mods = [(mod_text(mod, value), value) for mod, value in gear.mods.items()]
        half = (len(mods) + 1) // 2
        for i, (text, value) in enumerate(mods):
            col_x = r.x + 14 + (i // half) * ((r.w - 28) // 2) if len(mods) > 3 else r.x + 14
            row = i % half if len(mods) > 3 else i
            ui.text(window, text, (col_x, y + row * 12), (120, 230, 120) if value > 0 else (240, 110, 100), size=20)


def _fit(text: str, size: int, room: float) -> str:
    """`text`, cut short with "..." to fit `room` logical px."""
    if ui.font(size).size(text)[0] / settings.SCALE <= room:
        return text
    while text and ui.font(size).size(text + "...")[0] / settings.SCALE > room:
        text = text[:-1]
    return text.rstrip() + "..."
