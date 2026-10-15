"""The title screen: continue the latest save, load one, or start a new game."""

import pygame

from . import saves, settings, ui
from .save_menu import SaveList
from .saves import LoadError
from .scene import Scene, Transition
from .town import TownScene
from .towns import TOWNS
from .world import START_TOWN, Game

PAD = 9
ROW_H = 19
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)


class TitleScene(Scene):
    pausable = False  # Esc belongs to the load list here

    def __init__(self):
        self.saves: SaveList | None = None
        self.message = ""
        self._refresh()

    def _refresh(self) -> None:
        """The options: Continue and Load game only once there are saves."""
        self.latest = saves.latest()
        self.options = (["Continue", "Load game"] if self.latest else []) + ["New game"]
        self.choice = 0
        self.menu = pygame.Rect(0, 0, 160, PAD * 2 + ROW_H * len(self.options))
        self.menu.midtop = (settings.LOGICAL_SIZE[0] // 2, 190)

    def _start(self, info) -> None:
        try:
            self.next_scene = Transition(self, saves.load(info), flashes=0)
        except LoadError as e:
            self.message = str(e)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.saves:
            self.saves.handle_event(event)
            if self.saves.closed:
                self.saves = None
                self._refresh()  # saves may have been deleted
            elif self.saves.picked:
                self._start(self.saves.picked)
                self.saves.picked = None
                if self.message:  # couldn't load it
                    self.saves.message, self.message = self.message, ""
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if event.key == pygame.K_DOWN else -1)) % len(self.options)
        elif event.key in CONFIRM_KEYS:
            self.message = ""
            option = self.options[self.choice]
            if option == "Continue":
                self._start(self.latest)
            elif option == "Load game":
                self.saves = SaveList("load", confirm_load=False)
            else:
                town = TownScene(Game.new(), TOWNS[START_TOWN])
                self.next_scene = Transition(self, town, flashes=0)

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((24, 32, 72))
        for y in range(0, settings.LOGICAL_SIZE[1], 4):  # faint stripes
            pygame.draw.line(canvas, (28, 38, 82), (0, y), (settings.LOGICAL_SIZE[0], y))
        ui.window_box(canvas, self.menu)
        ui.cursor(canvas, self.menu.x + 16, self.menu.y + PAD + 5 + self.choice * ROW_H)

    def draw_overlay(self, window: pygame.Surface) -> None:
        center = settings.LOGICAL_SIZE[0] // 2
        ui.text(window, settings.TITLE, (center, 110), ui.YELLOW, size=56, align="center")
        for i, option in enumerate(self.options):
            ui.text(window, option, (self.menu.x + 22, self.menu.y + PAD + i * ROW_H))
        if self.latest:
            info = self.latest
            ui.text(window, f"Continue: {info.name}, {info.where}   {info.saved_at:%b %d  %H:%M}",
                    (center, self.menu.bottom + 10), ui.GREY, size=22, align="center")
        if self.message:
            ui.text(window, self.message, (center, self.menu.bottom + 26), ui.YELLOW, size=22, align="center")
        if self.saves:
            dim = pygame.Surface(window.get_size(), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 120))
            window.blit(dim, (0, 0))
            self.saves.draw_overlay(window)
