"""The hub: where dungeon runs start and end. A stand-in for towns.

Coming back here heals the party (as a Pokémon Center would).
"""

from collections import Counter

import pygame

from . import settings, ui
from .instance import MAPS, Instance
from .items import Bag
from .overworld import OverworldScene
from .pokemon import Monster
from .scene import Scene, Transition
from .summary import SummaryScene
from .themes import THEMES

ROW_H = 19
PAD = 9
LIST_WINDOW = pygame.Rect(170, 70, 300, PAD * 2 + ROW_H * (len(THEMES) + 1) + 4)
PARTY_WINDOW = pygame.Rect(170, LIST_WINDOW.bottom + 8, 300, PAD * 2 + ROW_H * 3)
MESSAGE_WINDOW = pygame.Rect(6, 6, 628, PAD * 2 + ROW_H)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)

DESCRIPTIONS = {
    "meadow": "Grassy fields. Normal, Bug and Grass Pokémon.",
    "ice_cave": "A frozen cave. Water and Ice Pokémon.",
}


class HubScene(Scene):
    def __init__(self, party: list[Monster], bag: Bag):
        self.party, self.bag = party, bag
        self.choice = 0
        self.cleared: Counter = Counter()  # theme -> runs finished
        self.message = ""
        self.welcome()

    def welcome(self, message: str = "") -> None:
        """Back at the hub: the party is healed."""
        for m in self.party:
            m.hp = m.max_hp
            m.cure()
        self.message = message

    def finish(self, instance: Instance) -> None:
        self.cleared[instance.theme.key] += 1
        self.welcome(f"You cleared the {instance.theme.name}! Your party is rested.")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        themes = list(THEMES.values())
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if event.key == pygame.K_DOWN else -1)) % len(themes)
        elif event.key in CONFIRM_KEYS:
            instance = Instance(themes[self.choice], self.party, self.bag)
            self.message = ""
            self.next_scene = Transition(self, OverworldScene(instance, self), flashes=0)
        elif event.key == pygame.K_TAB:
            self.next_scene = SummaryScene(self, self.party, self.bag)

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((24, 32, 72))
        for y in range(0, settings.LOGICAL_SIZE[1], 4):  # faint stripes
            pygame.draw.line(canvas, (28, 38, 82), (0, y), (settings.LOGICAL_SIZE[0], y))
        for rect in (LIST_WINDOW, PARTY_WINDOW):
            ui.window_box(canvas, rect)
        if self.message:
            ui.window_box(canvas, MESSAGE_WINDOW)
        ui.cursor(canvas, LIST_WINDOW.x + 16, LIST_WINDOW.y + PAD + 5 + (self.choice + 1) * ROW_H + 4)
        for i, m in enumerate(self.party):
            bar = pygame.Rect(PARTY_WINDOW.x + 150, PARTY_WINDOW.y + PAD + 3 + i * ROW_H, 80, 6)
            ui.hp_bar(canvas, bar, m.hp / m.max_hp)

    def draw_overlay(self, window: pygame.Surface) -> None:
        if self.message:
            ui.text(window, self.message, (MESSAGE_WINDOW.x + 12, MESSAGE_WINDOW.y + PAD))
        x, y = LIST_WINDOW.x + 12, LIST_WINDOW.y + PAD
        ui.text(window, "Choose a dungeon", (x, y), ui.YELLOW)
        themes = list(THEMES.values())
        for i, theme in enumerate(themes):
            row_y = y + (i + 1) * ROW_H + 4
            ui.text(window, theme.name, (x + 10, row_y), ui.YELLOW if i == self.choice else ui.WHITE)
            done = self.cleared[theme.key]
            ui.text(window, f"{MAPS[0]}-{MAPS[1]} maps" + (f"   cleared {done}x" if done else ""),
                    (LIST_WINDOW.right - 12, row_y + 2), ui.GREY, size=22, align="right")
        ui.text(window, DESCRIPTIONS.get(themes[self.choice].key, ""), (LIST_WINDOW.x, LIST_WINDOW.y - 18),
                ui.GREY, size=22)
        for i, m in enumerate(self.party):
            row_y = PARTY_WINDOW.y + PAD + i * ROW_H
            ui.text(window, f"{m.name}  Lv{m.level}", (PARTY_WINDOW.x + 12, row_y))
            ui.text(window, f"{m.hp}/{m.max_hp}", (PARTY_WINDOW.right - 12, row_y), align="right")
        ui.text(window, "Up/Down: choose   Enter: go   Tab: party   Esc: menu", (6, 342), ui.GREY, size=22)
