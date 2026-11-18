"""The equipped moves' panel (talent screen): reorder them, or pick the
one a newly equipped move replaces when every slot is full.

    order    Up/Down choose, Enter pick up (then Up/Down carry it, Enter
             put it down), X close
    replace  Up/Down choose the slot, Enter replace, X cancel

(Battles reorder the Skills list in place: `BattleScene`, O.)
"""

import pygame

from ..engine import ui
from ..mechanics.pokemon import Monster

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_o)


def move_equipped(monster: Monster, index: int, step: int) -> int:
    """Swap equipped move `index` with its neighbour `step` (±1) away, if
    there is one; returns its new index."""
    other = index + step
    if 0 <= other < len(monster.equipped):
        eq = monster.equipped
        eq[index], eq[other] = eq[other], eq[index]
        return other
    return index


class MovesPanel:
    RECT = pygame.Rect(40, 90, 330, 150)  # (over the talent grid)
    ROW_H = 18
    PAD = 9

    def __init__(self, monster: Monster, replace_with: str = ""):
        self.monster = monster
        self.replace_with = replace_with  # a skill key: "replace" mode
        self.choice = 0
        self.carrying = False
        self.message = ""  # what happened (the caller shows it)

    @property
    def title(self) -> str:
        if self.replace_with:
            return f"Equip {self.monster.tree.learned(self.replace_with).name}: which move does it replace?"
        return "Reorder moves (keys 2-5 in battle)"

    def handle_key(self, key: int) -> bool:
        """True when the panel closes."""
        m, n = self.monster, len(self.monster.equipped)
        if key in (pygame.K_UP, pygame.K_DOWN) and n:
            step = 1 if key == pygame.K_DOWN else -1
            if self.carrying:
                self.choice = move_equipped(m, self.choice, step)
            else:
                self.choice = (self.choice + step) % n
        elif key in CONFIRM_KEYS and n:
            if self.replace_with:
                old = m.tree.learned(m.equipped[self.choice]).name
                m.equipped[self.choice] = self.replace_with
                self.message = (f"{m.tree.learned(self.replace_with).name} equipped in place of {old} "
                                f"(key {self.choice + 2}). {old} is still known.")
                return True
            self.carrying = not self.carrying
        elif key in BACK_KEYS:
            if self.carrying:
                self.carrying = False
            else:
                if self.replace_with:
                    name = m.tree.learned(self.replace_with).name
                    self.message = f"{name} is known but not used in battle (E: equip move, later)."
                return True
        return False

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 40 + i * self.ROW_H

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.monster.equipped:
            ui.cursor(canvas, self.RECT.x + 14, self._row_y(self.choice) + 5)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r, m = self.RECT, self.monster
        ui.text(window, self.title, (r.x + 12, r.y + self.PAD), ui.YELLOW, size=22)
        ui.text(window, f"Fight: {m.tree.basic.name}", (r.x + 22, r.y + self.PAD + 20), ui.GREY, size=20)
        for i, key in enumerate(m.equipped):
            carried = self.carrying and i == self.choice
            color = ui.YELLOW if carried else ui.WHITE
            ui.text(window, f"{i + 2}  {m.move(key).name}", (r.x + 22, self._row_y(i)), color, size=22)
            if carried:
                ui.text(window, "moving", (r.right - 12, self._row_y(i) + 2), ui.YELLOW, size=18, align="right")
        if self.replace_with:
            hint = "Up/Down: choose   Enter: replace it   X: don't equip"
        elif self.carrying:
            hint = "Up/Down: move it   Enter: put down"
        else:
            hint = "Up/Down: choose   Enter: pick up   X: close"
        ui.text(window, hint, (r.x + 12, r.bottom - self.PAD - 12), ui.GREY, size=18)
