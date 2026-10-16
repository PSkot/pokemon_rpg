"""Choosing the first Pokémon (a new game): Professor Oak's three starters
side by side. Left/Right picks, Enter asks to confirm, X goes back to the
title screen. The game then starts in Pallet Town.
"""

import pygame

from .. import settings
from ..engine import ui
from ..engine.scene import Scene, Transition
from ..mechanics.pokemon import SPECIES, Monster, animations
from ..mechanics.type_chart import COLORS
from ..mechanics.type_chart import name as type_name
from ..world.progress import STARTERS, Game
from ..world.towns import TOWNS
from .town import TownScene

PAD = 9
PANEL_W, PANEL_H = 196, 236
PANELS = [pygame.Rect(14 + i * (PANEL_W + 12), 66, PANEL_W, PANEL_H) for i in range(len(STARTERS))]
SPRITE_BOX = 92  # height of the sprite area at the top of a panel
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)
BLURB = {  # what each is good against, as Professor Oak might put it
    "bulbasaur": "A Grass type: strong against Water Pokémon.",
    "charmander": "A Fire type: strong against Grass Pokémon.",
    "squirtle": "A Water type: strong against Fire Pokémon.",
}
STATS = (("HP", "base_hp"), ("Attack", "base_attack"), ("Defense", "base_defense"), ("Speed", "base_speed"))


class StarterScene(Scene):
    pausable = False  # X/Esc go back to the title

    def __init__(self, title: Scene):
        self.title = title
        self.choice = 0
        self.asking = False  # "Choose ...?"
        self.monsters = [Monster.create(key, 5) for key in STARTERS]  # to show their moves
        self.t = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if self.asking:
            if key in CONFIRM_KEYS:
                town = TownScene(Game.new(STARTERS[self.choice]), TOWNS["pallet"])
                self.next_scene = Transition(self, town, flashes=0)
            elif key in BACK_KEYS:
                self.asking = False
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.choice = (self.choice + (1 if key == pygame.K_RIGHT else -1)) % len(STARTERS)
        elif key in CONFIRM_KEYS:
            self.asking = True
        elif key in BACK_KEYS:
            self.next_scene = self.title

    def update(self, dt: float) -> None:
        self.t += dt

    # ------------------------------------------------------------------ draw

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((24, 32, 72))
        for y in range(0, settings.LOGICAL_SIZE[1], 4):  # faint stripes, as on the title screen
            pygame.draw.line(canvas, (28, 38, 82), (0, y), (settings.LOGICAL_SIZE[0], y))
        for i, (rect, key) in enumerate(zip(PANELS, STARTERS)):
            ui.window_box(canvas, rect)
            species = SPECIES[key]
            frame = animations(species)["idle"].frame(0)
            # Same size on screen, whether a 64px sprite or a smaller icon; the chosen one bobs.
            scale = 2 if frame.get_bounding_rect().h > 40 else 3
            sprite = pygame.transform.scale_by(frame.subsurface(frame.get_bounding_rect()), scale)
            if sprite.get_height() > SPRITE_BOX - 8:
                sprite = pygame.transform.scale_by(sprite, (SPRITE_BOX - 8) / sprite.get_height())
            lift = 3 if i == self.choice and int(self.t * 3) % 2 else 0
            canvas.blit(sprite, sprite.get_rect(midbottom=(rect.centerx, rect.y + SPRITE_BOX - lift)))
            for t, pos in self._badges(i):
                ui.badge(canvas, pos, COLORS[t])
            for k, (_, attr) in enumerate(STATS):  # base stat bars
                bar = self._stat_bar(i, k)
                pygame.draw.rect(canvas, ui.SHADOW, bar)
                fill = bar.inflate(-2, -2)
                fill.w = round(fill.w * min(1, getattr(species, attr) / 100))
                pygame.draw.rect(canvas, (120, 200, 255), fill)
            if i == self.choice:
                pygame.draw.rect(canvas, ui.YELLOW, rect.inflate(4, 4), 2, border_radius=4)

    def _lines(self, i: int) -> tuple[list[str], int]:
        """The panel's blurb lines, and the y its stats start at."""
        blurb = _wrap(BLURB[STARTERS[i]], 34)
        return blurb, PANELS[i].y + SPRITE_BOX + 46 + len(blurb) * 12 + 4 + 16

    def _stat_bar(self, i: int, k: int) -> pygame.Rect:
        rect, (_, y) = PANELS[i], self._lines(i)
        return pygame.Rect(rect.x + 12 + 56, y + k * 13 + 3, rect.w - 24 - 84, 6)

    def _badges(self, i: int) -> list[tuple[str, tuple[int, int]]]:
        types = SPECIES[STARTERS[i]].types
        rect = PANELS[i]
        total = len(types) * (ui.BADGE_SIZE[0] + 4) - 4
        x0 = rect.centerx - total // 2
        return [(t, (x0 + k * (ui.BADGE_SIZE[0] + 4), rect.y + SPRITE_BOX + 26)) for k, t in enumerate(types)]

    def draw_overlay(self, window: pygame.Surface) -> None:
        center = settings.LOGICAL_SIZE[0] / 2
        ui.text(window, "Choose your first Pokémon!", (center, 18), ui.YELLOW, size=40, align="center")
        ui.text(window, "Professor Oak has three Pokémon for you. Your rival will pick the one that beats yours.",
                (center, 42), ui.GREY, size=20, align="center")
        for i, (rect, m) in enumerate(zip(PANELS, self.monsters)):
            x, right = rect.x + 12, rect.right - 12
            ui.text(window, m.name, (rect.centerx, rect.y + SPRITE_BOX + 6), ui.YELLOW if i == self.choice
                    else ui.WHITE, align="center")
            for t, pos in self._badges(i):
                ui.badge_text(window, type_name(t), pos)
            blurb, stats_y = self._lines(i)
            y = rect.y + SPRITE_BOX + 46
            for part in blurb:
                ui.text(window, part, (x, y), size=20)
                y += 12
            moves = [m.basic_attack.name] + [mv.name for mv in m.moves]
            ui.text(window, "Moves: " + ", ".join(moves), (x, y + 4), ui.GREY, size=20)
            for k, (label, attr) in enumerate(STATS):
                y = stats_y + k * 13
                ui.text(window, label, (x, y), ui.GREY, size=20)
                ui.text(window, str(getattr(m.species, attr)), (right, y), ui.WHITE, size=20, align="right")
        bottom = settings.LOGICAL_SIZE[1] - 26
        if self.asking:
            name = self.monsters[self.choice].name
            ui.text(window, f"Choose {name}?   Enter: yes   X: no", (center, bottom), ui.YELLOW, align="center")
        else:
            ui.text(window, "Left/Right: choose   Enter: pick   X: back", (center, bottom), ui.GREY, size=22,
                    align="center")


def _wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + [line] if line else lines
