"""The touch controls' layout (pause menu → Controls, on touch screens):
button size, side panel width and where each side's buttons sit, changed
with Left/Right while the controls show every button, so each change shows
at once. Saved in the player's settings (saves.save_prefs) on closing.
"""

from dataclasses import replace

import pygame

from .. import saves, settings
from ..engine import touch, ui

PAD = 9
ROW_H = 19
WIDTH = 260
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
# (Layout field, label); "reset" and "done" are actions.
ROWS = [("size", "Button size"), ("panel", "Side panels"), ("left_x", "Left buttons: across"),
        ("left_y", "Left buttons: height"), ("right_x", "Right buttons: across"),
        ("right_y", "Right buttons: height"), ("reset", "Reset to default"), ("done", "Done")]
# Left/Right move the buttons left/right; the right side's inward is leftwards.
FLIPPED = {"right_x"}


class ControlsMenu:
    def __init__(self):
        self.choice = 0
        self.closed = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        field = ROWS[self.choice][0]
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if event.key == pygame.K_DOWN else -1)) % len(ROWS)
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and field in touch.RANGES:
            step = 1 if event.key == pygame.K_RIGHT else -1
            self._change(field, -step if field in FLIPPED else step)
        elif event.key in CONFIRM_KEYS and field == "reset":
            touch.layout = touch.Layout()
        elif (event.key in CONFIRM_KEYS and field == "done") or event.key in BACK_KEYS:
            prefs = saves.load_prefs()
            prefs["touch"] = touch.prefs()
            saves.save_prefs(prefs)
            self.closed = True

    def _change(self, field: str, step: int) -> None:
        low, high, size = touch.RANGES[field]
        value = max(low, min(high, getattr(touch.layout, field) + step * size))
        touch.layout = replace(touch.layout, **{field: value})

    @staticmethod
    def _value(field: str) -> str:
        value = getattr(touch.layout, field)
        if field in ("size", "panel"):
            return f"{value}%"
        return f"{value:+d}" if value else "0"

    @property
    def rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, WIDTH, PAD * 2 + ROW_H * (len(ROWS) + 2))
        rect.center = (settings.LOGICAL_SIZE[0] // 2, settings.LOGICAL_SIZE[1] // 2)
        return rect

    def _row_y(self, i: int) -> int:
        return self.rect.y + PAD + ROW_H * (i + 1) + 4

    def draw_overlay(self, window: pygame.Surface) -> None:
        rect = self.rect
        box = pygame.Surface(rect.size, pygame.SRCALPHA)
        ui.window_box(box, box.get_rect())
        ui.cursor(box, 16, self._row_y(self.choice) - rect.y + 5)
        ui.blit_scaled(window, box, rect.topleft)
        ui.text(window, "Touch controls", (rect.centerx, rect.y + PAD), ui.YELLOW, align="center")
        for i, (field, label) in enumerate(ROWS):
            y = self._row_y(i)
            ui.text(window, label, (rect.x + 22, y), size=24)
            if field in touch.RANGES:
                ui.text(window, f"< {self._value(field)} >", (rect.right - 14, y), ui.YELLOW, size=24, align="right")
        ui.text(window, "Up/Down: choose   Left/Right: change   B: done", (rect.centerx, self._row_y(len(ROWS)) + 2),
                ui.GREY, size=20, align="center")
