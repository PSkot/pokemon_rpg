"""A gym's arena: before its waves (`Route.waves`, then the boss group), the
player picks the Pokémon that fight them all (`Route.wave_team`), in a
panel on the map (`TeamPick`)."""

import pygame

from ..engine import ui
from ..mechanics.pokemon import SPECIES, Monster
from ..world.instance import Route

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)

PICKED_COLOR = (120, 200, 255)


class TeamPick:
    """Pick `route.wave_team` party members (fewer if fewer are standing),
    then Fight!. Afterwards `team` holds them, in party order, or None if
    the player backed out."""

    RECT = pygame.Rect(150, 60, 340, 240)
    ROW_H = 18
    PAD = 9

    def __init__(self, route: Route, party: list[Monster]):
        self.route = route
        self.party = party
        self.picked: list[Monster] = []
        self.choice = 0
        self.team: list[Monster] | None = None

    def can_pick(self, m: Monster) -> bool:
        """Standing, and (a trial) of the species it's for."""
        return m.alive and (not self.route.wave_species or m.species.key in self.route.wave_species)

    @property
    def needed(self) -> int:
        return min(self.route.wave_team, sum(1 for m in self.party if self.can_pick(m)))

    def _rows(self) -> list[Monster | None]:
        return list(self.party) + [None]  # None: Fight!

    def handle_key(self, key: int) -> bool:
        rows = self._rows()
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(rows)
        elif key in CONFIRM_KEYS:
            m = rows[self.choice]
            if m is None:
                if self.needed and len(self.picked) == self.needed:
                    self.team = [p for p in self.party if p in self.picked]
                    return True
            elif m in self.picked:
                self.picked.remove(m)
            elif self.can_pick(m) and len(self.picked) < self.needed:
                self.picked.append(m)
                if len(self.picked) == self.needed:
                    self.choice = len(rows) - 1  # on to Fight!
        elif key in BACK_KEYS:
            return True
        return False

    def _row_y(self, i: int) -> int:
        return self.RECT.y + self.PAD + 60 + i * self.ROW_H

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        ui.cursor(canvas, self.RECT.x + 14, self._row_y(self.choice) + 5)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r, route = self.RECT, self.route
        waves = len(route.waves) + 1
        ui.text(window, route.name, (r.x + 12, r.y + self.PAD), ui.YELLOW)
        ui.text(window, f"{waves} waves in a row, no healing in between.", (r.x + 12, r.y + self.PAD + 18),
                ui.GREY, size=20)
        if self.needed:
            alone = " alone" if route.wave_team == 1 else ""
            ui.text(window, f"Pick {self.needed} Pokémon to fight them all{alone}: {len(self.picked)}/{self.needed}",
                    (r.x + 12, r.y + self.PAD + 32), ui.GREY, size=20)
        else:
            ui.text(window, f"Only your {SPECIES[route.wave_species[0]].name} can take this on (in the party, standing).",
                    (r.x + 12, r.y + self.PAD + 32), ui.GREY, size=20)
        for i, m in enumerate(self._rows()):
            y = self._row_y(i)
            if m is None:
                ready = self.needed and len(self.picked) == self.needed
                ui.text(window, "Fight!", (r.x + 22, y), ui.YELLOW if ready else ui.GREY, size=24)
                continue
            color = PICKED_COLOR if m in self.picked else ui.WHITE if self.can_pick(m) else ui.GREY
            ui.text(window, m.name, (r.x + 22, y), color, size=24)
            ui.text(window, f"Lv{m.level}   {m.hp}/{m.max_hp}", (r.right - 12, y + 2), ui.GREY, size=20,
                    align="right")
        ui.text(window, "Enter: pick   X: not yet", (r.right - 12, r.bottom - self.PAD - 9), ui.GREY, size=20,
                align="right")
