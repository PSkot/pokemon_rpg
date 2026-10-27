"""Quest screens: the dialogue box, a town's quest board and the quest log.

They're drawn on top of a map scene (or the pause menu) and take its keys
while open: `handle_key` returns True once they're closed.
"""

import pygame

from .. import settings
from ..engine import ui
from ..world import quests
from ..world.quests import QUESTS, Line, Quest
from .battle import XP_COLOR

PAD = 9
ROW_H = 19
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z, pygame.K_UP)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
DONE_COLOR = (120, 230, 120)
W, H = settings.LOGICAL_SIZE


def _box(window: pygame.Surface, rect: pygame.Rect) -> None:
    box = pygame.Surface(rect.size, pygame.SRCALPHA)
    ui.window_box(box, box.get_rect())
    ui.blit_scaled(window, box, rect.topleft)


class Dialogue:
    """Pages of (speaker, text) at the bottom of the screen; Enter goes on."""

    RECT = pygame.Rect(6, H - 82, W - 12, 76)

    def __init__(self, pages: list[Line]):
        self.pages = pages
        self.page = 0

    def handle_key(self, key: int) -> bool:
        if key in CONFIRM_KEYS:
            self.page += 1
        return self.page >= len(self.pages)

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)

    def draw_overlay(self, window: pygame.Surface) -> None:
        speaker, text = self.pages[self.page]
        x, y = self.RECT.x + 14, self.RECT.y + PAD
        if speaker:
            ui.text(window, speaker, (x, y), ui.YELLOW)
            y += 18
        for i, line in enumerate(ui.wrap(text, 26, self.RECT.w - 28)[:3]):
            ui.text(window, line, (x, y + i * 15), ui.WHITE if speaker else ui.GREY, size=26)
        more = "Enter" if self.page + 1 < len(self.pages) else "Enter: close"
        ui.text(window, more, (self.RECT.right - 12, self.RECT.bottom - 16), ui.GREY, size=20, align="right")


def notice(title: str, lines: list[str], rows: list | None = None) -> ui.ListPanel:
    """A "New quest" / "Quest complete" panel: some wrapped text, then rows."""
    text_rows = [(line, ui.WHITE, "") for part in lines for line in ui.wrap(part, 26, 380)]
    return ui.ListPanel(title, text_rows + (rows or []), (W // 2, H // 2 - 20), width=420)


def started(key: str) -> ui.ListPanel:
    quest = QUESTS[key]
    return notice(f"New quest: {quest.name}", [quest.summary, f"Next: {quest.steps[0].text}."])


def finished(key: str, event: quests.Event | None = None) -> ui.ListPanel:
    """The quest's rewards: `event`'s (None: shown with another quest's)."""
    rows = []
    if event:
        rows = [r.row() for r in event.rewards]
        if event.xp:
            rows.append((f"{event.xp} XP", XP_COLOR, "each party member"))
        rows += [(line, ui.YELLOW, "") for line in event.level_ups]
    return notice(f"Quest complete: {QUESTS[key].name}", [], rows or [("No reward", ui.GREY, "")])


def _steps(game, quest: Quest) -> list[tuple[str, tuple]]:
    """Its steps so far: done ones, then the current one."""
    at = quests.step(game, quest.key) or 0
    return [(s.text, DONE_COLOR if i < at else ui.WHITE) for i, s in enumerate(quest.steps[:at + 1])]


class QuestBoard:
    """A town's quest board: its quests (new, active, done); Enter takes a
    new one. `taken` is the quest key accepted (the scene starts it)."""

    RECT = pygame.Rect(0, 0, 480, 270)
    RECT.center = (W // 2, H // 2)

    def __init__(self, game, town_name: str, town: str):
        self.game, self.town_name, self.town = game, town_name, town
        self.choice = 0
        self.taken: str | None = None

    @property
    def quests(self) -> list[Quest]:
        return quests.board(self.game, self.town)

    def _state(self, quest: Quest) -> tuple[str, tuple]:
        if quests.is_done(self.game, quest.key):
            return "Done", DONE_COLOR
        if quests.is_active(self.game, quest.key):
            return "Active", ui.YELLOW
        return "New", (120, 200, 255)

    def handle_key(self, key: int) -> bool:
        listed = self.quests
        if key in (pygame.K_UP, pygame.K_DOWN) and listed:
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(listed)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z) and listed:
            quest = listed[self.choice]
            if quests.ready(self.game, quest):
                self.taken = quest.key
                return True
        elif key in BACK_KEYS:
            return True
        return False

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.quests:
            ui.cursor(canvas, self.RECT.x + 16, self.RECT.y + PAD + 24 + self.choice * ROW_H + 5)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r, listed = self.RECT, self.quests
        x, right = r.x + 22, r.right - 14
        ui.text(window, f"{self.town_name} quest board", (r.x + 12, r.y + PAD), ui.YELLOW)
        if not listed:
            ui.text(window, "Nothing posted right now.", (x, r.y + PAD + 24), ui.GREY)
        for i, quest in enumerate(listed):
            y = r.y + PAD + 24 + i * ROW_H
            state, color = self._state(quest)
            ui.text(window, quest.name, (x, y), ui.YELLOW if i == self.choice else ui.WHITE)
            ui.text(window, state, (right, y + 2), color, size=22, align="right")
        if listed:
            quest = listed[self.choice]
            y = r.y + PAD + 24 + len(listed) * ROW_H + 10
            pygame.draw.line(window, ui.GREY, ((r.x + 12) * settings.SCALE, (y - 5) * settings.SCALE),
                             ((r.right - 12) * settings.SCALE, (y - 5) * settings.SCALE))
            for line in ui.wrap(quest.summary, 24, r.w - 34):
                ui.text(window, line, (r.x + 14, y), size=24)
                y += 14
            y += 4
            if quests.step(self.game, quest.key) is None:
                ui.text(window, f"First: {quest.steps[0].text}.", (r.x + 14, y), ui.GREY, size=22)
                y += 13
            else:
                for text, color in _steps(self.game, quest):
                    ui.text(window, f"- {text}", (r.x + 14, y), color, size=22)
                    y += 13
            for line in ui.wrap(f"Rewards: {quests.reward_text(quest)}", 22, r.w - 34):
                ui.text(window, line, (r.x + 14, y + 4), ui.YELLOW, size=22)
                y += 13
        hint = "Enter: take quest   X: close" if listed and quests.ready(self.game, listed[self.choice]) \
            else "X: close"
        ui.text(window, hint, (right, r.bottom - PAD - 9), ui.GREY, size=20, align="right")


class QuestLog:
    """Pause menu → Quests: active quests with their steps, then done ones."""

    RECT = pygame.Rect(0, 0, 480, 290)
    RECT.center = (W // 2, H // 2)

    def __init__(self, game):
        self.game = game

    def handle_key(self, key: int) -> bool:
        return key in BACK_KEYS or key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        _box(window, r)
        x, y = r.x + 14, r.y + PAD
        ui.text(window, "Quests", (r.x + 12, y), ui.YELLOW)
        y += 24
        current = quests.active(self.game)
        if not current:
            ui.text(window, "No active quests. Look for quest boards in towns.", (x, y), ui.GREY, size=24)
            y += 18
        for quest in current:
            ui.text(window, quest.name, (x, y), ui.WHITE)
            y += 17
            for text, color in _steps(self.game, quest):
                ui.text(window, f"- {text}", (x + 10, y), color, size=22)
                y += 13
            y += 6
        done = [q for q in QUESTS.values() if quests.is_done(self.game, q.key)]
        if done:
            ui.text(window, "Done: " + ", ".join(q.name for q in done), (x, y + 4), DONE_COLOR, size=22)
        ui.text(window, "X: back", (r.right - 14, r.bottom - PAD - 9), ui.GREY, size=20, align="right")
