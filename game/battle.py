"""Turn-based battle screen: enemies on the left, the player's party on the right."""

from collections import Counter
from functools import cache

import pygame

from . import settings, ui
from .pokemon import Monster, idle_animation
from .scene import Scene, Transition

HORIZON_Y = 118
PANEL_Y = 264  # top of the menu windows

ENEMY_WINDOW = pygame.Rect(6, PANEL_Y, 170, 90)
COMMAND_WINDOW = pygame.Rect(180, PANEL_Y, 104, 90)
PARTY_WINDOW = pygame.Rect(288, PANEL_Y, 346, 90)
ROW_H = 19   # menu line height
PAD = 9      # space above the first line in a window

COMMANDS = ["Fight", "Skills", "Item", "Run"]

# Feet positions for the player's side, by party size: a diagonal column, as
# in the classic Final Fantasy games. Enemies use the mirror image.
PARTY_SLOTS = {
    1: [(492, 205)],
    2: [(472, 180), (512, 236)],
    3: [(452, 160), (492, 200), (532, 240)],
}


class Combatant:
    """A Pokémon taking part in a battle, and where it stands."""

    def __init__(self, monster: Monster, label: str, pos: tuple[int, int], enemy: bool):
        self.monster = monster
        self.label = label
        self.x, self.feet_y = pos
        self.enemy = enemy
        self.anim = idle_animation(monster.species)

    @property
    def flip(self) -> bool:
        return not self.enemy  # sprites face right; the party faces left

    def draw(self, surface: pygame.Surface) -> None:
        feet_y = self.feet_y + self.monster.species.foot_sink
        body = self.anim.body_rect(0, self.x, feet_y, self.flip)
        shadow = pygame.Rect(0, 0, round(body.w * 0.8), 8)
        shadow.center = (round(self.x), self.feet_y)
        pygame.draw.ellipse(surface, (60, 110, 50), shadow)
        surface.blit(self.anim.frame(0, self.flip), self.anim.place(0, self.x, feet_y, self.flip))


def _labels(monsters: list[Monster]) -> list[str]:
    """Names, with A, B, ... added when a species appears more than once."""
    counts = Counter(m.name for m in monsters)
    seen: Counter = Counter()
    labels = []
    for m in monsters:
        if counts[m.name] > 1:
            labels.append(f"{m.name} {chr(ord('A') + seen[m.name])}")
            seen[m.name] += 1
        else:
            labels.append(m.name)
    return labels


def _side(monsters: list[Monster], enemy: bool) -> list[Combatant]:
    slots = PARTY_SLOTS[len(monsters)]
    if enemy:
        slots = [(settings.LOGICAL_SIZE[0] - x, y) for x, y in slots]
    return [Combatant(m, label, pos, enemy)
            for m, label, pos in zip(monsters, _labels(monsters), slots)]


@cache
def _background() -> pygame.Surface:
    w, _ = settings.LOGICAL_SIZE
    bg = pygame.Surface((w, PANEL_Y))
    sky_top, sky_bottom = (104, 168, 232), (196, 228, 244)
    for y in range(HORIZON_Y):
        t = y / HORIZON_Y
        pygame.draw.line(bg, [round(a + (b - a) * t) for a, b in zip(sky_top, sky_bottom)], (0, y), (w, y))
    # Distant hills along the horizon.
    for cx, rw, rh, color in [(80, 260, 60, (120, 176, 112)), (330, 320, 44, (104, 160, 100)),
                              (560, 280, 70, (120, 176, 112))]:
        pygame.draw.ellipse(bg, color, (cx - rw // 2, HORIZON_Y - rh // 2, rw, rh))
    # The field, with stripes spaced further apart towards the viewer.
    field_far, field_near = (112, 184, 88), (84, 160, 68)
    for y in range(HORIZON_Y, PANEL_Y):
        t = (y - HORIZON_Y) / (PANEL_Y - HORIZON_Y)
        pygame.draw.line(bg, [round(a + (b - a) * t) for a, b in zip(field_far, field_near)], (0, y), (w, y))
    y, gap = HORIZON_Y + 4, 4.0
    while y < PANEL_Y:
        pygame.draw.line(bg, (96, 168, 76), (0, round(y)), (w, round(y)))
        y += gap
        gap *= 1.35
    return bg


class BattleScene(Scene):
    def __init__(self, return_to: Scene, party: list[Monster], enemies: list[Monster]):
        self.return_to = return_to
        self.party = _side(party, enemy=False)
        self.enemies = _side(enemies, enemy=True)
        self.cursor = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(COMMANDS)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(COMMANDS)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            if COMMANDS[self.cursor] == "Run":
                self.next_scene = Transition(self, self.return_to, flashes=0)

    # ------------------------------------------------------------------- draw

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(ui.SHADOW)
        canvas.blit(_background(), (0, 0))
        for c in sorted(self.party + self.enemies, key=lambda c: c.feet_y):
            c.draw(canvas)
        for rect in (ENEMY_WINDOW, COMMAND_WINDOW, PARTY_WINDOW):
            ui.window_box(canvas, rect)
        ui.cursor(canvas, COMMAND_WINDOW.x + 16, COMMAND_WINDOW.y + PAD + 5 + self.cursor * ROW_H)
        for i, c in enumerate(self.party):
            m = c.monster
            bar = pygame.Rect(PARTY_WINDOW.x + 168, PARTY_WINDOW.y + PAD + 3 + i * ROW_H, 90, 6)
            ui.hp_bar(canvas, bar, m.hp / m.max_hp)

    def draw_overlay(self, window: pygame.Surface) -> None:
        ui.text(window, "Up/Down: choose   Enter: confirm   (only Run works so far)",
                (8, 6), color=ui.SHADOW, size=22, shadow=False)
        for i, c in enumerate(self.enemies):
            ui.text(window, c.label, (ENEMY_WINDOW.x + 12, ENEMY_WINDOW.y + PAD + i * ROW_H))
        for i, name in enumerate(COMMANDS):
            ui.text(window, name, (COMMAND_WINDOW.x + 22, COMMAND_WINDOW.y + PAD + i * ROW_H))
        for i, c in enumerate(self.party):
            m, y = c.monster, PARTY_WINDOW.y + PAD + i * ROW_H
            color = ui.YELLOW if i == 0 else ui.WHITE  # whose turn it is
            ui.text(window, c.label, (PARTY_WINDOW.x + 12, y), color)
            ui.text(window, f"Lv{m.level}", (PARTY_WINDOW.x + 112, y), color)
            ui.text(window, f"{m.hp}/{m.max_hp}", (PARTY_WINDOW.right - 12, y), color, align="right")
