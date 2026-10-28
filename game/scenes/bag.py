"""The bag: everything the player carries, and using it outside battle.

Opened from the pause menu (Bag), or with I / the Bag touch button on a
map. Three pockets (Left/Right):
  Items      medicine: Enter, then a party member, to heal or cure it; the
             Escape Rope leads back to the last town or Pokémon Center
             (on a route or in a dungeon)
  Gear       Enter, then a party member, to equip it (what it wore in that
             slot comes back to the bag)
  Key items  story items; an evolution item (Metapod Shell) is used on a
             party member that can evolve with it (the party screen shows
             the evolution)
Like the pause menu's other screens, it's drawn over the scene and takes
its keys; `closed` once X is pressed, `loaded` a scene to switch to.
"""

import pygame

from .. import settings
from ..engine import ui
from ..mechanics.items import KEY_ITEMS, MEDICINE, RARITIES, SLOT_NAMES, SLOTS, Bag, Gear, mod_text, money_text
from ..mechanics.pokemon import SPECIES
from ..mechanics.status import STATUSES
from ..world import quests
from ..world.towns import TOWNS

PAD = 9
ROW_H = 18
POCKETS = ("Items", "Gear", "Key items")
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
GREEN = (120, 230, 120)
RED = (240, 110, 100)
W, H = settings.LOGICAL_SIZE


def _box(window: pygame.Surface, rect: pygame.Rect) -> None:
    box = pygame.Surface(rect.size, pygame.SRCALPHA)
    ui.window_box(box, box.get_rect())
    ui.blit_scaled(window, box, rect.topleft)


class BagScreen:
    RECT = pygame.Rect(0, 0, 600, 320)
    RECT.center = (W // 2, H // 2)
    LIST_W = 290  # the list's width; the info (or the party, when picking) is right of it
    TOP = 40      # the list starts this far under the window's top
    ROWS = 13     # rows shown

    def __init__(self, scene, bag: Bag):
        """`scene`: the map scene underneath (its game: the party, quests)."""
        self.scene, self.bag = scene, bag
        self.game = scene.game
        self.pocket = 0
        self.choice = 0
        self.top = 0
        self.picking = False  # choosing the party member to use it on
        self.member = 0
        self.message = ""
        self.closed = False
        self.loaded = None  # a scene to switch to (Escape Rope: a town; evolving: the party screen)

    # ---------------------------------------------------------------- contents

    def _entries(self) -> list:
        """The current pocket's contents: medicine names, Gear, or key item names."""
        if POCKETS[self.pocket] == "Items":
            return [name for name in MEDICINE if self.bag.medicine.get(name)]  # (in MEDICINE's order)
        if POCKETS[self.pocket] == "Gear":
            rank = list(RARITIES)
            return sorted(self.bag.gear, key=lambda g: (SLOTS.index(g.slot), -g.level, -rank.index(g.rarity.name),
                                                         g.name))
        return list(self.bag.key_items)

    @property
    def selected(self):
        entries = self._entries()
        return entries[self.choice] if entries else None

    @property
    def party(self):
        return self.game.party

    # ------------------------------------------------------------------- keys

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        self.message = ""
        if self.picking:
            if key in (pygame.K_UP, pygame.K_DOWN):
                self.member = (self.member + (1 if key == pygame.K_DOWN else -1)) % len(self.party)
            elif key in CONFIRM_KEYS:
                self._use_on(self.party[self.member])
            elif key in BACK_KEYS:
                self.picking = False
            return
        entries = self._entries()
        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.pocket = (self.pocket + (1 if key == pygame.K_RIGHT else -1)) % len(POCKETS)
            self.choice = self.top = 0
        elif key in (pygame.K_UP, pygame.K_DOWN) and entries:
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(entries)
            self.top = min(self.choice, max(self.top, self.choice - self.ROWS + 1))
        elif key in CONFIRM_KEYS and entries:
            self._use()
        elif key in BACK_KEYS:
            self.closed = True

    def _use(self) -> None:
        """Enter on the selected entry: pick who it's for, or use it right away."""
        item = self.selected
        if POCKETS[self.pocket] == "Items" and MEDICINE[item].escape:
            if not hasattr(self.scene, "instance"):  # (a route or dungeon map)
                self.message = "Use it on a route or in a cave."
                return
            from .town import TownScene  # (town.py imports the map scenes, which import this)
            self.bag.use_medicine(item)
            self.loaded = TownScene(self.game, TOWNS[self.game.town])  # as after fainting
            return
        if POCKETS[self.pocket] == "Key items" and not quests.evolution_target(item):
            self.message = "There's no use for it right now."
            return
        self.picking, self.member = True, 0

    def _use_on(self, m) -> None:
        item, pocket = self.selected, POCKETS[self.pocket]
        if pocket == "Items":
            medicine = MEDICINE[item]
            if not medicine.has_effect(m):
                self.message = "It won't have any effect."
                return
            self.message = medicine.use_on(m)
            self.bag.use_medicine(item)
        elif pocket == "Gear":
            gear: Gear = item
            if not gear.usable_by(m):
                self.message = f"{m.name} needs to be Lv{gear.level} for it."
                return
            old = m.gear.get(gear.slot)
            self.bag.equip(m, gear)
            self.message = f"{m.name} put on the {gear.name}." + (f" ({old.name} back in the bag.)" if old else "")
        else:
            if not quests.item_evolves(self.game, item, m):
                target = SPECIES[quests.evolution_target(item)]
                level = target.evolution.level if target.evolution else 0
                self.message = (f"{m.name} can't use it. It's for a {target.name} at Lv{level} or higher."
                                if m.species is not target else f"{m.name} needs to be Lv{level} first.")
                return
            from .summary import SummaryScene  # (the party screen shows the evolution)
            summary = SummaryScene(self.scene, self.party, self.bag)
            summary.member, summary.mode, summary.evolve_time = self.member, "evolving", 0.0
            self.loaded = summary
            return
        self.picking = False
        entries = self._entries()  # (it may have run out)
        self.choice = min(self.choice, max(0, len(entries) - 1))
        self.top = min(self.top, self.choice)

    # ------------------------------------------------------------------- draw

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        _box(window, r)
        x, y = r.x + 12, r.y + PAD
        ui.text(window, "Bag", (x, y), ui.YELLOW)
        tab_x = x + 52
        for i, name in enumerate(POCKETS):
            color = ui.YELLOW if i == self.pocket else ui.GREY
            label = f"< {name} >" if i == self.pocket else name
            ui.text(window, label, (tab_x, y + 2), color, size=24)
            tab_x += ui.font(24).size(label)[0] / settings.SCALE + 14
        ui.text(window, money_text(self.bag.money), (r.right - 12, y + 2), ui.YELLOW, size=24, align="right")
        self._draw_list(window)
        if self.picking:
            self._draw_party(window)
        else:
            self._draw_info(window)
        hint = ("Up/Down: who   Enter: use   X: back" if self.picking
                else "Left/Right: pocket   Up/Down: choose   Enter: use   X: close")
        ui.text(window, self.message or hint, (r.x + 12, r.bottom - PAD - 10), ui.WHITE if self.message else ui.GREY,
                size=20)

    def _draw_list(self, window: pygame.Surface) -> None:
        r, entries = self.RECT, self._entries()
        x, right, y0 = r.x + 22, r.x + self.LIST_W, r.y + self.TOP
        if not entries:
            ui.text(window, "Nothing here.", (x, y0), ui.GREY, size=24)
            return
        for i, entry in enumerate(entries[self.top:self.top + self.ROWS]):
            y = y0 + i * ROW_H
            row = self.top + i
            if row == self.choice:
                ui.text(window, ">", (r.x + 10, y), ui.YELLOW if not self.picking else ui.GREY, size=24)
            if POCKETS[self.pocket] == "Items":
                ui.text(window, entry, (x, y), size=24)
                ui.text(window, f"x{self.bag.medicine[entry]}", (right, y), ui.GREY, size=24, align="right")
            elif POCKETS[self.pocket] == "Gear":
                side = f"Lv{entry.level} {SLOT_NAMES[entry.slot]}"
                room = right - x - ui.font(20).size(side)[0] / settings.SCALE - 8
                ui.text(window, _fit(entry.name, 22, room), (x, y), entry.rarity.color, size=22)
                ui.text(window, side, (right, y), ui.GREY, size=20, align="right")
            else:
                ui.text(window, entry, (x, y), size=24)
        if self.top > 0:
            ui.text(window, "more above", (right, y0 - 12), ui.GREY, size=16, align="right")
        if self.top + self.ROWS < len(entries):
            ui.text(window, "more below", (right, y0 + self.ROWS * ROW_H - 4), ui.GREY, size=16, align="right")

    def _draw_info(self, window: pygame.Surface) -> None:
        item = self.selected
        if item is None:
            return
        r = self.RECT
        x, w, y = r.x + self.LIST_W + 18, r.right - (r.x + self.LIST_W + 18) - 12, r.y + self.TOP
        if POCKETS[self.pocket] == "Gear":
            gear: Gear = item
            for line in ui.wrap(gear.name, 26, w):
                ui.text(window, line, (x, y), gear.rarity.color, size=26)
                y += 16
            ui.text(window, f"Lv{gear.level} {gear.rarity.name} {SLOT_NAMES[gear.slot]} item", (x, y), ui.GREY,
                    size=22)
            y += 16
            for line in ui.wrap(gear.item.description, 22, w):
                ui.text(window, line, (x, y), size=22)
                y += 13
            y += 4
            for mod, value in gear.mods.items():
                ui.text(window, mod_text(mod, value), (x, y), GREEN if value > 0 else RED, size=22)
                y += 13
            return
        name = item
        ui.text(window, name, (x, y), ui.YELLOW, size=26)
        y += 18
        text = MEDICINE[name].description if POCKETS[self.pocket] == "Items" else KEY_ITEMS.get(name, "")
        for line in ui.wrap(text, 22, w):
            ui.text(window, line, (x, y), size=22)
            y += 13

    def _draw_party(self, window: pygame.Surface) -> None:
        """Who to use it on: each party member, with what matters for the item."""
        r = self.RECT
        x, right, y = r.x + self.LIST_W + 30, r.right - 14, r.y + self.TOP
        item, pocket = self.selected, POCKETS[self.pocket]
        ui.text(window, "Who wears it?" if pocket == "Gear" else f"Use the {item} on:", (x - 12, y), ui.YELLOW,
                size=22)
        y += 18
        for i, m in enumerate(self.party):
            if i == self.member:
                ui.text(window, ">", (x - 12, y), ui.YELLOW, size=24)
            ui.text(window, f"{m.name}  Lv{m.level}", (x, y), ui.YELLOW if i == self.member else ui.WHITE, size=24)
            if pocket == "Items":
                status = STATUSES[m.status].abbrev if m.status else ""
                side, color = f"{status}  {m.hp}/{m.max_hp}" if m.alive else "fainted", ui.GREY
            elif pocket == "Gear":
                worn = m.gear.get(item.slot)
                side, color = ((f"needs Lv{item.level}", RED) if not item.usable_by(m)
                               else (_fit(worn.name, 20, 120), worn.rarity.color) if worn else ("-", ui.GREY))
            else:
                ok = quests.item_evolves(self.game, item, m)
                side, color = ("can evolve!", GREEN) if ok else ("", ui.GREY)
            ui.text(window, side, (right, y + 2), color, size=20, align="right")
            y += ROW_H + 2


def _fit(s: str, size: int, width: float) -> str:
    """`s`, cut short with "..." if it's wider than `width` logical px at font `size`."""
    f = ui.font(size)
    if f.size(s)[0] / settings.SCALE <= width:
        return s
    while s and f.size(s + "...")[0] / settings.SCALE > width:
        s = s[:-1]
    return s.rstrip() + "..."
