"""The pause menu, opened with Esc over whichever scene is active."""

import pygame

from . import settings, ui

PAD = 9
ROW_H = 19
OPTIONS = ["Resume", "Quit game"]
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)


class PauseMenu:
    """Freezes the game (the main loop stops updating the scene) and offers
    Resume or Quit. Esc again resumes, so a stray Esc does no harm."""

    def __init__(self):
        self.choice = 0
        self.done = False   # closed: resume the game
        self.quit = False   # "Quit game" chosen
        self.rect = pygame.Rect(0, 0, 140, PAD * 2 + ROW_H * (len(OPTIONS) + 1))
        self.rect.center = (settings.LOGICAL_SIZE[0] // 2, settings.LOGICAL_SIZE[1] // 2)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.done = True
        elif event.key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if event.key == pygame.K_DOWN else -1)) % len(OPTIONS)
        elif event.key in CONFIRM_KEYS:
            if OPTIONS[self.choice] == "Quit game":
                self.quit = True
            self.done = True

    def _row_y(self, i: int) -> int:
        return self.rect.y + PAD + ROW_H * (i + 1) + 4

    def draw_overlay(self, window: pygame.Surface) -> None:
        """Dim everything the scene drew (sprites and text), then draw the menu
        window at the logical resolution and scale it up on top."""
        dim = pygame.Surface(window.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        window.blit(dim, (0, 0))
        box = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        local = self.rect.move(-self.rect.x, -self.rect.y)
        ui.window_box(box, local)
        ui.cursor(box, 16, self._row_y(self.choice) - self.rect.y + 5)
        s = settings.SCALE
        window.blit(pygame.transform.scale(box, (self.rect.w * s, self.rect.h * s)), (self.rect.x * s, self.rect.y * s))
        ui.text(window, "Paused", (self.rect.centerx, self.rect.y + PAD), ui.YELLOW, align="center")
        for i, name in enumerate(OPTIONS):
            ui.text(window, name, (self.rect.x + 22, self._row_y(i)))
