"""The smith's menu (Machamp at his anvil, once his hammer is made: quest
"A Hammer Fit for a Smith"), a panel over the town like the shops:

- Salvage: break a piece from the bag down into its rarity's material
  (`Gear.material`, `Gear.salvage_yield`).
- Enhance: raise a piece (in the bag, or worn by the party) by one, up to
  +`MAX_PLUS`: every bonus × (1 + 10% per +), for its rarity's material
  (`Gear.enhance_cost`).
- Smelt: `SMELT` of one material into one of the next rarity's.
"""

from __future__ import annotations

import pygame

from .. import settings
from ..engine import ui
from ..mechanics.items import MATERIALS, MAX_PLUS, RARITIES, SLOT_NAMES, SMELT, Gear, enhanced, mod_text
from ..world.progress import Game

GREEN, RED = (120, 230, 120), (240, 110, 100)


class SmithMenu:
    RECT = pygame.Rect(150, 34, 420, 312)
    OPTIONS = ("Enhance", "Salvage", "Smelt", "Leave")
    ROW_H, PAD, ROWS = 15, 9, 6
    CONFIRM = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
    BACK = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
    GREETING = "HAH! Back again? What'll it be: make something stronger, or break something down?"

    def __init__(self, game: Game):
        self.game, self.bag = game, game.bag
        self.mode = "main"   # "main", "enhance", "salvage", "smelt" or "confirm" (of `list_mode`)
        self.list_mode = "enhance"
        self.choice = self.item = self.top = 0
        self.message = self.GREETING

    # ---------------------------------------------------------------- state

    def _entries(self, mode: str | None = None) -> list:
        """The list's entries: (gear, wearer or None) to enhance or salvage,
        or the materials that smelt."""
        mode = mode or self.mode
        if mode == "smelt":
            return list(MATERIALS)[:-1]  # (rarity names: the last has nothing to smelt into)
        pieces = [(g, None) for g in self.bag.gear]
        if mode == "enhance":  # (what the party wears too)
            pieces += [(g, m) for m in self.game.party for g in m.gear.values()]
        return pieces

    @property
    def _selected(self):
        entries = self._entries(self.list_mode)
        return entries[self.item] if 0 <= self.item < len(entries) else None

    def handle_key(self, key: int) -> bool:
        """Returns True once the menu is closed."""
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
            self.message = {"enhance": "Pick a piece. Each + makes its bonuses stronger, up to +5.",
                            "salvage": "Pick a piece you don't need. I'll break it down for parts.",
                            "smelt": f"{SMELT} of one material and I'll smelt them into one of the next."}[self.mode]
        elif key in self.BACK:
            return True
        return False

    def _list_key(self, key: int) -> None:
        entries = self._entries()
        if key in (pygame.K_UP, pygame.K_DOWN) and entries:
            self.item = (self.item + (1 if key == pygame.K_DOWN else -1)) % len(entries)
            self.top = min(self.item, max(self.top, self.item - self.ROWS + 1))
        elif key in self.CONFIRM and entries:
            problem = self._problem()
            if problem:
                self.message = problem
                return
            self.mode = "confirm"
            self.message = self._question()
        elif key in self.BACK:
            self.mode, self.message = "main", "Anything else?"

    def _problem(self) -> str:
        """Why the selected entry can't be done now ("" if it can)."""
        if self.list_mode == "smelt":
            rarity = self._selected
            have = self.bag.materials[MATERIALS[rarity]]
            return "" if have >= SMELT else f"You need {SMELT} {MATERIALS[rarity]} for that. You've got {have}."
        gear, _ = self._selected
        if self.list_mode == "enhance":
            if gear.plus >= MAX_PLUS:
                return "That one's as strong as I can make it. +5!"
            cost, have = gear.enhance_cost(), self.bag.materials[gear.material]
            if have < cost:
                return f"That takes {cost} {gear.material}. You've got {have}. Break something down first!"
        return ""

    def _question(self) -> str:
        if self.list_mode == "smelt":
            rarity = self._selected
            nxt = list(MATERIALS)[list(MATERIALS).index(rarity) + 1]
            return f"Smelt {SMELT} {MATERIALS[rarity]} into 1 {MATERIALS[nxt]}?"
        gear, _ = self._selected
        if self.list_mode == "enhance":
            return f"Enhance the {gear.name} to +{gear.plus + 1} for {gear.enhance_cost()} {gear.material}?"
        return f"Break the {gear.name} down into {gear.salvage_yield} {gear.material}? It'll be gone for good."

    def _confirm_key(self, key: int) -> None:
        if key in self.CONFIRM:
            self.message = self._do()
            entries = self._entries(self.list_mode)
            self.item = max(0, min(self.item, len(entries) - 1))
            self.top = max(0, min(self.top, len(entries) - self.ROWS))
            self.mode = self.list_mode
        elif key in self.BACK:
            self.mode, self.message = self.list_mode, "Changed your mind? Fine by me."

    def _do(self) -> str:
        if self.list_mode == "smelt":
            rarity = self._selected
            nxt = MATERIALS[list(MATERIALS)[list(MATERIALS).index(rarity) + 1]]
            self.bag.materials[MATERIALS[rarity]] -= SMELT
            self.bag.materials[nxt] += 1
            return f"*CLANG* *CLANG* ...One {nxt}, still warm!"
        gear, _ = self._selected
        if self.list_mode == "enhance":
            self.bag.materials[gear.material] -= gear.enhance_cost()
            gear.plus += 1
            return f"*CLANG* *CLANG* *CLANG* There! The {gear.name}. Feel that?"
        self.bag.gear.remove(gear)
        self.bag.materials[gear.material] += gear.salvage_yield
        return f"*CRUNCH* {gear.salvage_yield} {gear.material}, good as new."

    # -------------------------------------------------------------- drawing

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 58 + i * self.ROW_H

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.mode == "main":
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.choice) + 6)
        elif self._entries(self.list_mode):
            ui.cursor(canvas, self.RECT.x + 16, self._row_y(self.item - self.top) + 5)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        x, right = r.x + 22, r.right - 14
        title = {"main": "Smithy", "enhance": "Enhance gear", "salvage": "Salvage gear", "smelt": "Smelt"}
        ui.text(window, title.get(self.mode, title[self.list_mode]), (r.x + 12, r.y + self.PAD), ui.YELLOW)
        for i, line in enumerate(ui.wrap(self.message, 22, r.w - 26)[:2]):
            ui.text(window, line, (r.x + 12, r.y + self.PAD + 20 + i * 12), ui.WHITE, size=22)
        self._draw_materials(window, r.y + self.PAD + 46)
        if self.mode == "main":
            for i, option in enumerate(self.OPTIONS):
                ui.text(window, option, (x, self._row_y(i)), ui.YELLOW if i == self.choice else ui.WHITE, size=26)
            hint = "Enter: choose   X: leave"
        else:
            self._draw_list(window, x, right)
            hint = "Enter: yes   X: no" if self.mode == "confirm" else "Enter: choose   X: back"
        ui.text(window, hint, (right, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")

    def _draw_materials(self, window: pygame.Surface, y: float) -> None:
        """What the player has: each material, in its rarity's colour."""
        x = self.RECT.x + 12
        for rarity, material in MATERIALS.items():
            s = f"{material} {self.bag.materials[material]}"
            ui.text(window, s, (x, y), RARITIES[rarity].color, size=20)
            x += ui.font(20).size(s)[0] / settings.SCALE + 12

    def _draw_list(self, window: pygame.Surface, x: int, right: int) -> None:
        entries = self._entries(self.list_mode)
        if not entries:
            ui.text(window, "Nothing to work on.", (x, self._row_y(0)), ui.GREY, size=22)
            return
        for i, entry in enumerate(entries[self.top:self.top + self.ROWS]):
            y = self._row_y(i)
            if self.list_mode == "smelt":
                nxt = list(MATERIALS)[list(MATERIALS).index(entry) + 1]
                ui.text(window, f"{SMELT} {MATERIALS[entry]}  ->  1 {MATERIALS[nxt]}", (x, y), RARITIES[entry].color,
                        size=22)
                ui.text(window, f"have {self.bag.materials[MATERIALS[entry]]}", (right, y + 1), ui.GREY, size=20,
                        align="right")
                continue
            gear, wearer = entry
            ui.text(window, gear.name, (x, y), gear.rarity.color, size=22)
            side = (f"{wearer.name}  " if wearer else "") + (
                f"{gear.enhance_cost()} {gear.material}" if self.list_mode == "enhance" and gear.plus < MAX_PLUS
                else "max" if self.list_mode == "enhance" else f"+{gear.salvage_yield} {gear.material}")
            ui.text(window, side, (right, y + 1), ui.GREY, size=20, align="right")
        if self.top > 0:
            ui.text(window, "more above", (right, self._row_y(0) - 9), ui.GREY, size=16, align="right")
        if self.top + self.ROWS < len(entries):
            ui.text(window, "more below", (right, self._row_y(self.ROWS) - 5), ui.GREY, size=16, align="right")
        if self.list_mode != "smelt":
            self._draw_piece(window, entries[self.item][0], self._row_y(self.ROWS) + 8)

    def _draw_piece(self, window: pygame.Surface, gear: Gear, y: float) -> None:
        """The selected piece: its rarity, level and mods; while enhancing,
        what the next + makes of them."""
        r, s = self.RECT, settings.SCALE
        pygame.draw.line(window, ui.GREY, ((r.x + 12) * s, (y - 4) * s), ((r.right - 12) * s, (y - 4) * s))
        ui.text(window, f"Lv{gear.level} {gear.rarity.name} {SLOT_NAMES[gear.slot]} item", (r.x + 14, y), ui.GREY,
                size=20)
        preview = self.list_mode == "enhance" and gear.plus < MAX_PLUS
        if preview:
            ui.text(window, f"+{gear.plus}  ->  +{gear.plus + 1}", (r.right - 14, y), ui.YELLOW, size=20,
                    align="right")
        y += 14
        base: dict[str, int] = {}
        for roll in gear.rolls:
            for mod, value in roll.mods.items():
                base[mod] = base.get(mod, 0) + value
        for i, (mod, value) in enumerate(gear.mods.items()):
            col_x, row = r.x + 14 + (i % 2) * ((r.w - 28) // 2), i // 2
            text = mod_text(mod, value)
            ui.text(window, text, (col_x, y + row * 12), GREEN if value > 0 else RED, size=20)
            if preview:
                new = enhanced(base[mod], gear.plus + 1)
                if new != value:
                    w = ui.font(20).size(text)[0] / s
                    ui.text(window, f"({new - value:+d})", (col_x + w + 3, y + row * 12 + 1), ui.YELLOW, size=18)
