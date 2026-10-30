"""The list of saves, for saving (pause menu) and loading (pause menu and
title screen). It's drawn on top of everything, like the pause menu.

Picking a save sets `picked`: a `SaveInfo`, or `NEW_SAVE`. Overwriting,
loading over a game in progress and deleting (Delete key, or the Delete
touch button: `DELETE_PILL`, which the screens hosting the list show) ask
first.
"""

import pygame

from .. import saves, settings
from ..engine import ui
from ..saves import SaveInfo

PAD = 9
ROW_H = 19
ENTRY_H = 34      # two lines per save
VISIBLE = 5       # entries shown at once; the list scrolls
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
DELETE_KEYS = (pygame.K_DELETE,)
DELETE_PILL = ((pygame.K_DELETE, "Delete"),)  # the touch button for it (phones have no Delete key)

NEW_SAVE = "new"


class SaveList:
    def __init__(self, mode: str, confirm_load: bool = True):
        """`mode` is "save" or "load"; `confirm_load`: loading would throw
        away a game in progress, so ask first."""
        self.mode = mode
        self.confirm_load = confirm_load
        self.choice = 0
        self.top = 0
        self.asking = ""    # "" or what Enter will do: "overwrite", "load", "delete"
        self.picked: SaveInfo | str | None = None
        self.closed = False  # backed out
        self.message = ""
        self.refresh()
        self.rect = pygame.Rect(0, 0, 460, PAD * 2 + ROW_H + 4 + ENTRY_H * VISIBLE + 14)
        self.rect.center = (settings.LOGICAL_SIZE[0] // 2, settings.LOGICAL_SIZE[1] // 2)

    def refresh(self) -> None:
        found = saves.list_saves()
        if self.mode == "save":  # the autosave can't be saved over by hand
            self.entries: list[SaveInfo | str] = [NEW_SAVE] + [s for s in found if not s.auto]
        else:
            self.entries = list(found)
        self.choice = min(self.choice, max(0, len(self.entries) - 1))
        self._scroll()

    def _scroll(self) -> None:
        self.top = min(self.choice, max(self.top, self.choice - VISIBLE + 1))

    @property
    def current(self) -> SaveInfo | str | None:
        return self.entries[self.choice] if self.entries else None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key, current = event.key, self.current
        if self.asking:
            if key in CONFIRM_KEYS:
                if self.asking == "delete":
                    saves.delete(current)
                    self.message = f"{current.name} deleted."
                    self.refresh()
                else:
                    self.picked = current
                self.asking = ""
            elif key in BACK_KEYS:
                self.asking = ""
            return
        if key in (pygame.K_UP, pygame.K_DOWN) and self.entries:
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.entries)
            self._scroll()
            self.message = ""
        elif key in CONFIRM_KEYS and current:
            if self.mode == "save" and current != NEW_SAVE:
                self.asking = "overwrite"
            elif self.mode == "load" and self.confirm_load:
                self.asking = "load"
            else:
                self.picked = current
        elif key in DELETE_KEYS and isinstance(current, SaveInfo):
            self.asking = "delete"
        elif key in BACK_KEYS:
            self.closed = True

    # ------------------------------------------------------------------- draw

    def _entry_y(self, row: int) -> int:
        return self.rect.y + PAD + ROW_H + 4 + row * ENTRY_H

    def draw_overlay(self, window: pygame.Surface) -> None:
        box = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        ui.window_box(box, box.get_rect())
        if self.entries:
            ui.cursor(box, 16, self._entry_y(self.choice - self.top) - self.rect.y + 5)
        x = self.rect.w - 10
        if self.top > 0:
            pygame.draw.polygon(box, ui.WHITE, [(x - 3, 9), (x + 3, 9), (x, 5)])
        if self.top + VISIBLE < len(self.entries):
            y = self.rect.h - 9
            pygame.draw.polygon(box, ui.WHITE, [(x - 3, y), (x + 3, y), (x, y + 4)])
        ui.blit_scaled(window, box, self.rect.topleft)

        left, right = self.rect.x + 22, self.rect.right - 14
        ui.text(window, "Save game" if self.mode == "save" else "Load game", (self.rect.x + 12, self.rect.y + PAD),
                ui.YELLOW)
        if self.message:
            ui.text(window, self.message, (right, self.rect.y + PAD + 2), ui.GREY, size=22, align="right")
        if not self.entries:
            ui.text(window, "No saves yet.", (left, self._entry_y(0)), ui.GREY)
        for row, entry in enumerate(self.entries[self.top:self.top + VISIBLE]):
            y = self._entry_y(row)
            selected = self.top + row == self.choice
            color = ui.YELLOW if selected else ui.WHITE
            if entry == NEW_SAVE:
                ui.text(window, "New save", (left, y), color)
                ui.text(window, "Make a new save file.", (left, y + 16), ui.GREY, size=22)
                continue
            ui.text(window, entry.name, (left, y), color)
            ui.text(window, entry.where, (left + 90, y))
            ui.text(window, f"{entry.saved_at:%b %d  %H:%M}", (right, y), ui.GREY, size=22, align="right")
            if selected and self.asking:
                question = {"overwrite": "Save over this?", "load": "Load this? Unsaved progress is lost.",
                            "delete": "Delete this save?"}[self.asking]
                ui.text(window, f"{question}   Enter: yes   X: no", (left, y + 16), ui.YELLOW, size=22)
            else:
                party = "   ".join(f"{name} Lv{level}" for name, level in entry.party)
                ui.text(window, party, (left, y + 16), ui.GREY, size=22)
        verb = "save" if self.mode == "save" else "load"
        ui.text(window, f"Enter: {verb}   Del: delete   X: back", (right, self.rect.bottom - PAD - 9), ui.GREY,
                size=20, align="right")
