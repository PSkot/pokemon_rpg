"""The pause menu, opened with Esc over whichever scene is active."""

import pygame

from .. import saves, settings
from ..dev import DEV, XP_BOOSTS
from ..engine import ui
from ..saves import LoadError
from .dev_menu import ItemMaker
from ..world.towns import TOWNS
from .quest_ui import QuestLog
from .town import TownScene
from .save_menu import NEW_SAVE, SaveList

PAD = 9
ROW_H = 19
OPTIONS = ["Resume", "Quests", "Save game", "Load game", "Dev mode", "Quit game"]
DEV_OPTIONS = ["XP boost", "God mode", "Add item", "Teleport"]  # shown under "Dev mode" while it's on
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
WIDTH = 216


class PauseMenu:
    """Freezes the game (the main loop stops updating the scene) and offers
    Resume, Save, Load, Dev mode or Quit. Esc again resumes, so a stray Esc
    does no harm. Dev mode's settings (dev.py) are toggled here, with
    Enter or Left/Right.

    `save_point` is what the scene underneath can be saved as (see
    `Scene.save_point`); None greys out "Save game". `bag` is where "Add
    item" puts what it makes (None greys it out).
    """

    def __init__(self, save_point=None, bag=None):
        self.save_point = save_point
        self.bag = bag
        self.choice = 0
        self.done = False   # closed: resume the game
        self.quit = False   # "Quit game" chosen
        self.loaded = None  # the scene of a loaded save, to switch to
        self.saves: SaveList | None = None  # the save or load list, when open
        self.items: ItemMaker | None = None  # dev mode's item maker, when open
        self.log: QuestLog | None = None     # the quest log, when open
        self.teleport_to = list(TOWNS)[0]    # dev mode: the town Teleport goes to
        self.message = ""

    @property
    def options(self) -> list[str]:
        if not DEV.enabled:
            return OPTIONS
        i = OPTIONS.index("Dev mode") + 1
        return OPTIONS[:i] + DEV_OPTIONS + OPTIONS[i:]

    @property
    def rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, WIDTH, PAD * 2 + ROW_H * (len(self.options) + 2))
        rect.center = (settings.LOGICAL_SIZE[0] // 2, settings.LOGICAL_SIZE[1] // 2)
        return rect

    def _available(self, option: str) -> bool:
        return {"Save game": self.save_point is not None, "Quests": self.save_point is not None,
                "Teleport": self.save_point is not None, "Add item": self.bag is not None}.get(option, True)

    def _label(self, option: str) -> str:
        if option == "Dev mode":
            return f"Dev mode: {'On' if DEV.enabled else 'Off'}"
        if option == "XP boost":
            return f"XP boost: ×{DEV.xp_boost}"
        if option == "God mode":
            return f"God mode: {'On' if DEV.god else 'Off'}"
        if option == "Add item":
            return "Add item..."
        if option == "Teleport":
            return f"Teleport: < {TOWNS[self.teleport_to].name} >"
        return option

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.saves:
            self._handle_saves(event)
            return
        if self.items:
            self.items.handle_event(event)
            if self.items.closed:
                self.items = None
            return
        if self.log:
            if event.type == pygame.KEYDOWN and self.log.handle_key(event.key):
                self.log = None
            return
        if event.type != pygame.KEYDOWN:
            return
        option = self.options[self.choice]
        if event.key == pygame.K_ESCAPE:
            self.done = True
        elif event.key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if event.key == pygame.K_DOWN else -1)) % len(self.options)
            self.message = ""
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._toggle(option, 1 if event.key == pygame.K_RIGHT else -1)
        elif event.key in CONFIRM_KEYS:
            if option == "Save game":
                if self.save_point:
                    self.saves = SaveList("save")
                else:
                    self.message = "Can't save right now."
            elif option == "Load game":
                self.saves = SaveList("load")
            elif option == "Quests":
                if self.save_point:
                    self.log = QuestLog(self.save_point.game)
                else:
                    self.message = "Not during a battle."
            elif option == "Add item":
                if self.bag is not None:
                    self.items = ItemMaker(self.bag)
                else:
                    self.message = "No bag to add to here."
            elif option == "Teleport":
                if self.save_point:  # into that town, as after fainting (it becomes the respawn town)
                    self.loaded = TownScene(self.save_point.game, TOWNS[self.teleport_to])
                    self.done = True
                else:
                    self.message = "Not during a battle."
            elif option in ("Dev mode", "XP boost", "God mode"):
                self._toggle(option, 1)
            else:
                self.quit = option == "Quit game"
                self.done = True

    def _toggle(self, option: str, step: int) -> None:
        if option == "Dev mode":
            DEV.enabled = not DEV.enabled
        elif option == "XP boost":
            DEV.xp_boost = XP_BOOSTS[(XP_BOOSTS.index(DEV.xp_boost) + step) % len(XP_BOOSTS)]
        elif option == "God mode":
            DEV.god = not DEV.god
        elif option == "Teleport":
            keys = list(TOWNS)
            self.teleport_to = keys[(keys.index(self.teleport_to) + step) % len(keys)]
            return
        pygame.display.set_caption(" ".join(p for p in (settings.TITLE, DEV.summary() and f"[{DEV.summary()}]") if p))

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
        if self.items:
            self.items.draw_overlay(window)
            return
        if self.log:
            self.log.draw_overlay(window)
            return
        rect = self.rect
        box = pygame.Surface(rect.size, pygame.SRCALPHA)
        ui.window_box(box, box.get_rect())
        ui.cursor(box, 16, self._row_y(self.choice) - rect.y + 5)
        ui.blit_scaled(window, box, rect.topleft)
        ui.text(window, "Paused", (rect.centerx, rect.y + PAD), ui.YELLOW, align="center")
        for i, option in enumerate(self.options):
            dev = option in DEV_OPTIONS  # indented under "Dev mode"
            color = ui.GREY if not self._available(option) else ui.YELLOW if dev else ui.WHITE
            ui.text(window, self._label(option), (rect.x + (32 if dev else 22), self._row_y(i)), color,
                    size=24 if dev else 28)
        if self.message:
            ui.text(window, self.message, (rect.centerx, self._row_y(len(self.options)) + 2), ui.GREY, size=22,
                    align="center")
