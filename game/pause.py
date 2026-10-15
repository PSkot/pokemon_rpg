"""The pause menu, opened with Esc over whichever scene is active."""

import pygame

from . import saves, settings, ui
from .save_menu import NEW_SAVE, SaveList
from .saves import LoadError

PAD = 9
ROW_H = 19
OPTIONS = ["Resume", "Save game", "Load game", "Quit game"]
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)


class PauseMenu:
    """Freezes the game (the main loop stops updating the scene) and offers
    Resume, Save, Load or Quit. Esc again resumes, so a stray Esc does no harm.

    `save_point` is what the scene underneath can be saved as (see
    `Scene.save_point`); None greys out "Save game".
    """

    def __init__(self, save_point=None):
        self.save_point = save_point
        self.choice = 0
        self.done = False   # closed: resume the game
        self.quit = False   # "Quit game" chosen
        self.loaded = None  # the scene of a loaded save, to switch to
        self.saves: SaveList | None = None  # the save or load list, when open
        self.message = ""
        self.rect = pygame.Rect(0, 0, 160, PAD * 2 + ROW_H * (len(OPTIONS) + 2))
        self.rect.center = (settings.LOGICAL_SIZE[0] // 2, settings.LOGICAL_SIZE[1] // 2)

    def _available(self, option: str) -> bool:
        return option != "Save game" or self.save_point is not None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.saves:
            self._handle_saves(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.done = True
        elif event.key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if event.key == pygame.K_DOWN else -1)) % len(OPTIONS)
            self.message = ""
        elif event.key in CONFIRM_KEYS:
            option = OPTIONS[self.choice]
            if option == "Save game":
                if self.save_point:
                    self.saves = SaveList("save")
                else:
                    self.message = "Can't save right now."
            elif option == "Load game":
                self.saves = SaveList("load")
            else:
                self.quit = option == "Quit game"
                self.done = True

    def _handle_saves(self, event: pygame.event.Event) -> None:
        self.saves.handle_event(event)
        picked = self.saves.picked
        if self.saves.closed:
            self.saves = None
        elif picked and self.saves.mode == "save":
            name = saves.save(self.save_point, over=None if picked == NEW_SAVE else picked)
            self.message = f"Saved as {name}."
            self.saves = None
        elif picked:
            try:
                self.loaded = saves.load(picked)
                self.done = True
            except LoadError as e:
                self.saves.picked = None
                self.saves.message = str(e)

    def _row_y(self, i: int) -> int:
        return self.rect.y + PAD + ROW_H * (i + 1) + 4

    def draw_overlay(self, window: pygame.Surface) -> None:
        """Dim everything the scene drew (sprites and text), then draw the menu
        window at the logical resolution and scale it up on top."""
        dim = pygame.Surface(window.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        window.blit(dim, (0, 0))
        if self.saves:
            self.saves.draw_overlay(window)
            return
        box = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        ui.window_box(box, box.get_rect())
        ui.cursor(box, 16, self._row_y(self.choice) - self.rect.y + 5)
        ui.blit_scaled(window, box, self.rect.topleft)
        ui.text(window, "Paused", (self.rect.centerx, self.rect.y + PAD), ui.YELLOW, align="center")
        for i, name in enumerate(OPTIONS):
            color = ui.WHITE if self._available(name) else ui.GREY
            ui.text(window, name, (self.rect.x + 22, self._row_y(i)), color)
        if self.message:
            ui.text(window, self.message, (self.rect.centerx, self._row_y(len(OPTIONS)) + 2), ui.GREY, size=22,
                    align="center")
