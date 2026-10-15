"""Dev mode's item maker (pause menu → Add item): any gear or medicine, made
to order and put in the bag, for testing how items behave.

Gear: pick the item, its rarity, up to `MAX_AFFIXES` affixes of your
choice, and whether every value rolls at random, lowest or highest.
Medicine: pick it and how many. It's drawn on top of everything, like the
pause menu.
"""

import pygame

from .. import settings
from ..engine import ui
from ..mechanics.items import (AFFIX_BY_NAME, AFFIX_SLOTS, AFFIXES, ITEMS, MEDICINE, RARITIES, SLOT_NAMES, SLOTS,
                               Bag, Gear, Roll, mod_text)

PAD = 9
ROW_H = 19
VISIBLE = 10      # rows shown at once in a list; it scrolls
MAX_AFFIXES = 5
COUNTS = (1, 99)  # medicine
VALUES = {"random": "Random", "min": "Lowest", "max": "Highest"}
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
RECT = pygame.Rect(0, 0, 480, PAD * 2 + ROW_H * (VISIBLE + 2) + 8)
RECT.center = (settings.LOGICAL_SIZE[0] // 2, settings.LOGICAL_SIZE[1] // 2)

Entry = tuple[str | None, str, tuple[int, int, int], str]  # (value, text, colour, right-hand text)


def _range_text(mod: str, low: int, high: int) -> str:
    """A mod's range, e.g. "Attack +4–8%"."""
    text = mod_text(mod, high)
    return text if low == high else text.replace(str(abs(high)), f"{abs(low)}–{abs(high)}", 1)


def _mods_text(mods: dict) -> str:
    return ", ".join(_range_text(mod, low, high) for mod, (low, high) in mods.items())


class Picker:
    """A scrolling list to pick one entry from (Up/Down, PgUp/PgDn)."""

    def __init__(self, title: str, entries: list[Entry], current: str | None):
        self.title, self.entries = title, entries
        values = [e[0] for e in entries]
        self.choice = values.index(current) if current in values else 0
        self.top = max(0, self.choice - VISIBLE // 2)
        self.done = False
        self.picked: str | None = None
        self.cancelled = False

    def handle_key(self, key: int) -> None:
        step = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -VISIBLE, pygame.K_PAGEDOWN: VISIBLE}.get(key)
        if step:
            if abs(step) == 1:
                self.choice = (self.choice + step) % len(self.entries)
            else:
                self.choice = max(0, min(len(self.entries) - 1, self.choice + step))
            self.top = min(self.choice, max(self.top, self.choice - VISIBLE + 1))
        elif key in CONFIRM_KEYS:
            self.picked, self.done = self.entries[self.choice][0], True
        elif key in BACK_KEYS:
            self.cancelled = self.done = True

    def draw(self, box: pygame.Surface) -> None:
        ui.cursor(box, 16, PAD + ROW_H + 4 + (self.choice - self.top) * ROW_H + 5)
        x = RECT.w - 10
        if self.top > 0:
            pygame.draw.polygon(box, ui.WHITE, [(x - 3, 9), (x + 3, 9), (x, 5)])
        if self.top + VISIBLE < len(self.entries):
            y = RECT.h - 9
            pygame.draw.polygon(box, ui.WHITE, [(x - 3, y), (x + 3, y), (x, y + 4)])

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, self.title, (RECT.x + 12, RECT.y + PAD), ui.YELLOW)
        ui.text(window, "Enter: pick   PgUp/PgDn: scroll   X: back", (RECT.right - 14, RECT.y + PAD + 2), ui.GREY,
                size=20, align="right")
        for row, (_, text, color, side) in enumerate(self.entries[self.top:self.top + VISIBLE]):
            y = RECT.y + PAD + ROW_H + 4 + row * ROW_H
            selected = self.top + row == self.choice
            ui.text(window, text, (RECT.x + 22, y), ui.YELLOW if selected else color)
            ui.text(window, side, (RECT.right - 14, y + 2), ui.GREY, size=22, align="right")


class ItemMaker:
    """Rows: the item, then for gear its rarity, affixes and how values
    roll, or for medicine how many; then "Add to bag"."""

    def __init__(self, bag: Bag):
        self.bag = bag
        self.item = next(i.name for i in ITEMS.values() if i.slot == "head")
        self.rarity = "Common"
        self.affixes: list[str] = []
        self.values = "random"
        self.count = 1
        self.row = 0
        self.picker: Picker | None = None
        self.picking = ""   # what the picker is for: "item" or the affix row's index
        self.closed = False
        self.message: list[tuple[str, tuple[int, int, int]]] = []  # lines about what was just made

    @property
    def is_gear(self) -> bool:
        return self.item in ITEMS

    def rows(self) -> list[str]:
        rows = ["item"]
        if self.is_gear:
            rows.append("rarity")
            if ITEMS[self.item].slot in AFFIX_SLOTS:
                rows += [f"affix{i}" for i in range(min(len(self.affixes) + 1, MAX_AFFIXES))]
            rows.append("values")
        else:
            rows.append("count")
        return rows + ["make"]

    # ----------------------------------------------------------------- input

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if self.picker:
            self.picker.handle_key(event.key)
            if self.picker.done:
                if not self.picker.cancelled:
                    self._picked(self.picker.picked)
                self.picker = None
            return
        rows, key = self.rows(), event.key
        row = rows[self.row]
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.row = (self.row + (1 if key == pygame.K_DOWN else -1)) % len(rows)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._change(row, 1 if key == pygame.K_RIGHT else -1)
        elif key in CONFIRM_KEYS:
            if row == "item":
                self.picking, self.picker = "item", Picker("Item", self._item_entries(), self.item)
            elif row.startswith("affix"):
                i = int(row[5:])
                self.picking = row
                current = self.affixes[i] if i < len(self.affixes) else None
                self.picker = Picker(f"Affix {i + 1}", self._affix_entries(i), current)
            elif row == "make":
                self._make()
            else:
                self._change(row, 1)
        elif key == pygame.K_DELETE and row.startswith("affix"):
            self._picked(None, row)
        elif key in BACK_KEYS:
            self.closed = True

    def _change(self, row: str, step: int) -> None:
        if row == "rarity":
            names = list(RARITIES)
            self.rarity = names[(names.index(self.rarity) + step) % len(names)]
        elif row == "values":
            keys = list(VALUES)
            self.values = keys[(keys.index(self.values) + step) % len(keys)]
        elif row == "count":
            self.count = max(COUNTS[0], min(COUNTS[1], self.count + step))

    def _picked(self, value: str | None, row: str | None = None) -> None:
        row = row or self.picking
        if row == "item":
            self.item = value
            if not self.is_gear or ITEMS[self.item].slot not in AFFIX_SLOTS:
                self.affixes = []
        else:
            i = int(row[5:])
            if value is None:
                if i < len(self.affixes):
                    del self.affixes[i]
            elif i < len(self.affixes):
                self.affixes[i] = value
            else:
                self.affixes.append(value)
        self.row = min(self.row, len(self.rows()) - 1)

    def _item_entries(self) -> list[Entry]:
        gear = sorted(ITEMS.values(), key=lambda i: (SLOTS.index(i.slot), i.name))
        return ([(i.name, i.name, ui.WHITE, f"{SLOT_NAMES[i.slot]}   {_mods_text(i.mods)}") for i in gear]
                + [(m.name, m.name, ui.WHITE, f"Medicine   {m.description}") for m in MEDICINE.values()])

    def _affix_entries(self, row: int) -> list[Entry]:
        taken = set(self.affixes) - ({self.affixes[row]} if row < len(self.affixes) else set())
        return [(None, "(none)", ui.GREY, "")] + [
            (a.name, a.name, ui.WHITE, ("Prefix   " if a.prefix else "Suffix   ") + _mods_text(a.mods))
            for a in AFFIXES if a.name not in taken]

    def _make(self) -> None:
        if not self.is_gear:
            self.bag.add_medicine(self.item, self.count)
            self.message = [(f"Added {self.count} × {self.item} to the bag.", ui.WHITE)]
            return
        gear = Gear.roll(self.item, self.rarity, affixes=self.affixes, values=self.values)
        self.bag.add(gear)
        mods = ", ".join(mod_text(mod, value) for mod, value in gear.mods.items()) or "No stat changes"
        self.message = [(f"Added {gear.name} ({gear.rarity.name}) to the bag.", gear.rarity.color),
                        (mods, ui.GREY)]

    # ------------------------------------------------------------------ draw

    def draw_overlay(self, window: pygame.Surface) -> None:
        box = pygame.Surface(RECT.size, pygame.SRCALPHA)
        ui.window_box(box, box.get_rect())
        if self.picker:
            self.picker.draw(box)
            ui.blit_scaled(window, box, RECT.topleft)
            self.picker.draw_overlay(window)
            return
        ui.cursor(box, 16, PAD + ROW_H + 4 + self.row * ROW_H + 5)
        ui.blit_scaled(window, box, RECT.topleft)

        left, value_x, right = RECT.x + 22, RECT.x + 110, RECT.right - 14
        ui.text(window, "Add item (dev mode)", (RECT.x + 12, RECT.y + PAD), ui.YELLOW)
        ui.text(window, "Enter: choose / add   Left/Right: change   Del: remove affix   X: back",
                (right, RECT.y + PAD + 2), ui.GREY, size=18, align="right")
        rarity = RARITIES[self.rarity]
        for i, row in enumerate(self.rows()):
            y = RECT.y + PAD + ROW_H + 4 + i * ROW_H
            color = ui.YELLOW if i == self.row else ui.WHITE
            if row == "item":
                ui.text(window, "Item", (left, y), color)
                ui.text(window, self.item, (value_x, y), rarity.color if self.is_gear else ui.WHITE)
                side = (f"{SLOT_NAMES[ITEMS[self.item].slot]}   {_mods_text(ITEMS[self.item].mods)}" if self.is_gear
                        else "Medicine")
                ui.text(window, side, (right, y + 2), ui.GREY, size=22, align="right")
            elif row == "rarity":
                ui.text(window, "Rarity", (left, y), color)
                ui.text(window, f"< {self.rarity} >", (value_x, y), rarity.color)
                ui.text(window, f"bonuses ×{rarity.factor:g}", (right, y + 2), ui.GREY, size=22, align="right")
            elif row.startswith("affix"):
                n = int(row[5:])
                ui.text(window, f"Affix {n + 1}", (left, y), color)
                if n < len(self.affixes):
                    affix = AFFIX_BY_NAME[self.affixes[n]]
                    ui.text(window, affix.name, (value_x, y))
                    ui.text(window, _mods_text(affix.mods), (right, y + 2), ui.GREY, size=22, align="right")
                else:
                    ui.text(window, "(none)", (value_x, y), ui.GREY)
            elif row == "values":
                ui.text(window, "Values", (left, y), color)
                ui.text(window, f"< {VALUES[self.values]} >", (value_x, y))
            elif row == "count":
                ui.text(window, "Count", (left, y), color)
                ui.text(window, f"< {self.count} >", (value_x, y))
            else:
                ui.text(window, "Add to bag", (left, y), color)
        y = RECT.bottom - PAD - ROW_H * 2 - 4
        if self.is_gear:  # the name it will get
            rolls = [Roll(AFFIX_BY_NAME[a], {}) for a in self.affixes]  # enough for its name
            ui.text(window, Gear(ITEMS[self.item], rarity, rolls).name, (left, y), rarity.color, size=24)
        for i, (line, color) in enumerate(self.message):
            ui.text(window, line, (left, y + 15 + i * 13), color, size=20)

