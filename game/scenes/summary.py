"""Party screen: each Pokémon's stats and gear, and equipping gear from the bag.

Two modes:
  slots    pick a Pokémon (Left/Right) and one of its gear slots (Up/Down)
  choose   pick what goes in that slot: gear from the bag, or "Remove";
           the stats table previews the change
"""

from dataclasses import replace

import pygame

from ..engine import hats, ui
from ..engine.scene import Scene
from ..mechanics.combat import CRIT_CHANCE
from ..mechanics.items import RARITIES, SLOT_NAMES, SLOTS, STAT_NAMES, STATS, Bag, Gear, mod_text
from ..mechanics.pokemon import Monster, animations
from ..mechanics.status import STATUSES
from ..mechanics.type_chart import COLORS
from ..mechanics.type_chart import name as type_name
from .battle import XP_COLOR
from .skill_tree import SkillTreeScene

ROW_H = 19
PAD = 9

PARTY_WINDOW = pygame.Rect(6, 6, 150, 348)
STATS_WINDOW = pygame.Rect(162, 6, 472, PAD * 2 + ROW_H * 8 - 4)
GEAR_WINDOW = pygame.Rect(162, STATS_WINDOW.bottom + 6, 472, PAD * 2 + ROW_H * len(SLOTS))
INFO_WINDOW = pygame.Rect(162, GEAR_WINDOW.bottom + 6, 472, 354 - GEAR_WINDOW.bottom - 6)
SPRITE_BOX = pygame.Rect(STATS_WINDOW.x + 8, STATS_WINDOW.y + 8, 128, STATS_WINDOW.h - 16)
LIST_ROWS = len(SLOTS)  # the gear list opens in the gear window

STATS_X = STATS_WINDOW.x + 150  # left edge of the stats table
COLUMNS = (190, 250, 310)       # right edges of the table's number columns, from STATS_X
GREEN = (120, 230, 120)
RED = (240, 110, 100)

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
CLOSE_KEYS = (pygame.K_TAB, pygame.K_x, pygame.K_BACKSPACE)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE)

HINTS = {
    "slots": ("Left/Right: Pokémon", "Up/Down: gear slot", "Enter: change gear", "S: skills", "Tab: close"),
    "choose": ("Up/Down: choose gear", "Enter: equip", "X: back"),
}


def _type_badges(m: Monster) -> list[tuple[str, tuple[int, int]]]:
    """Each of `m`'s types with its badge position, right-aligned on the name row."""
    right = STATS_WINDOW.right - 12
    n = len(m.species.types)
    return [(t, (right - (n - i) * (ui.BADGE_SIZE[0] + 4) + 4, STATS_WINDOW.y + PAD + 1))
            for i, t in enumerate(m.species.types)]


def _bonus_color(percent: float):
    return GREEN if percent > 0 else RED if percent < 0 else ui.GREY


def _rarity_rank(gear: Gear) -> int:
    return list(RARITIES).index(gear.rarity.name)


class SummaryScene(Scene):

    def __init__(self, return_to: Scene, party: list[Monster], bag: Bag):
        self.return_to = return_to
        self.party = party
        self.bag = bag
        self.member = 0
        self.slot = 0
        self.mode = "slots"
        self.choice = 0      # cursor in the gear list
        self.top = 0         # first row shown, when the list scrolls

    def save_point(self):
        return self.return_to.save_point()

    @property
    def monster(self) -> Monster:
        return self.party[self.member]

    @property
    def slot_name(self) -> str:
        return SLOTS[self.slot]

    def _options(self) -> list[Gear | None]:
        """What can go in the current slot: None (= remove what's there, if
        anything), then the bag's gear for it, best rarity first."""
        fits = [g for g in self.bag.gear if g.slot == self.slot_name]
        fits.sort(key=lambda g: (-_rarity_rank(g), g.name))
        return ([None] if self.slot_name in self.monster.gear else []) + fits

    def _preview(self) -> Monster | None:
        """The Pokémon as it would be with the highlighted choice equipped."""
        if self.mode != "choose":
            return None
        gear = dict(self.monster.gear)
        option = self._options()[self.choice]
        if option:
            gear[self.slot_name] = option
        else:
            gear.pop(self.slot_name, None)
        return replace(self.monster, gear=gear)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if self.mode == "slots":
            if key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.member = (self.member + (1 if key == pygame.K_RIGHT else -1)) % len(self.party)
            elif key in (pygame.K_UP, pygame.K_DOWN):
                self.slot = (self.slot + (1 if key == pygame.K_DOWN else -1)) % len(SLOTS)
            elif key in CONFIRM_KEYS and self._options():
                self.mode, self.choice, self.top = "choose", 0, 0
            elif key == pygame.K_s:
                self.next_scene = SkillTreeScene(self, self.party, self.member, self.return_to.in_town)
            elif key in CLOSE_KEYS:
                self.next_scene = self.return_to
        elif self.mode == "choose":
            options = self._options()
            if key in (pygame.K_UP, pygame.K_DOWN):
                self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(options)
                self.top = min(self.choice, max(self.top, self.choice - LIST_ROWS + 1))
            elif key in CONFIRM_KEYS:
                option = options[self.choice]
                if option:
                    self.bag.equip(self.monster, option)
                else:
                    self.bag.unequip(self.monster, self.slot_name)
                self.mode = "slots"
            elif key in BACK_KEYS:
                self.mode = "slots"

    # ------------------------------------------------------------------- draw

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(ui.SHADOW)
        for rect in (PARTY_WINDOW, STATS_WINDOW, GEAR_WINDOW, INFO_WINDOW):
            ui.window_box(canvas, rect)
        pygame.draw.rect(canvas, (24, 32, 96), SPRITE_BOX, border_radius=3)
        idle = animations(self.monster.species)["idle"]
        frame = idle.frame(0, False).copy()
        # The hat it wears, or the one being tried on while choosing.
        hats.draw_worn(frame, self._preview() or self.monster, idle, 0, frame.get_rect(), False)
        sprite = pygame.transform.scale_by(frame, 2)
        canvas.blit(sprite, sprite.get_rect(center=SPRITE_BOX.center))
        for t, pos in _type_badges(self.monster):
            ui.badge(canvas, pos, COLORS[t])
        ui.cursor(canvas, PARTY_WINDOW.x + 16, PARTY_WINDOW.y + PAD + 5 + self.member * ROW_H * 2)
        for i, m in enumerate(self.party):
            done, needed = m.xp_progress
            bar = pygame.Rect(PARTY_WINDOW.x + 22, PARTY_WINDOW.y + PAD + i * ROW_H * 2 + 29, 110, 4)
            ui.bar(canvas, bar, done / needed if needed else 0.0, XP_COLOR)
        row = self.slot if self.mode == "slots" else self.choice - self.top
        ui.cursor(canvas, GEAR_WINDOW.x + 16, GEAR_WINDOW.y + PAD + 5 + row * ROW_H)
        if self.mode == "choose":  # scroll arrows
            x = GEAR_WINDOW.right - 10
            if self.top > 0:
                y = GEAR_WINDOW.y + 5
                pygame.draw.polygon(canvas, ui.WHITE, [(x - 3, y + 4), (x + 3, y + 4), (x, y)])
            if self.top + LIST_ROWS < len(self._options()):
                y = GEAR_WINDOW.bottom - 9
                pygame.draw.polygon(canvas, ui.WHITE, [(x - 3, y), (x + 3, y), (x, y + 4)])

    def draw_overlay(self, window: pygame.Surface) -> None:
        self._draw_party(window)
        self._draw_stats(window)
        if self.mode == "slots":
            self._draw_slots(window)
            self._draw_info(window, self.monster.gear.get(self.slot_name))
        else:
            self._draw_choices(window)
            option = self._options()[self.choice]
            if option:
                self._draw_info(window, option)
            else:
                gear = self.monster.gear[self.slot_name]
                ui.text(window, f"Take off the {gear.name}.", (INFO_WINDOW.x + 12, INFO_WINDOW.y + PAD))

    def _draw_party(self, window: pygame.Surface) -> None:
        for i, m in enumerate(self.party):
            y = PARTY_WINDOW.y + PAD + i * ROW_H * 2
            color = ui.YELLOW if i == self.member else ui.WHITE
            ui.text(window, m.name, (PARTY_WINDOW.x + 22, y), color)
            ui.text(window, f"Lv{m.level}  {m.hp}/{m.max_hp}", (PARTY_WINDOW.x + 22, y + ROW_H - 3),
                    ui.GREY, size=22)
            if m.status:
                status = STATUSES[m.status]
                ui.text(window, status.abbrev, (PARTY_WINDOW.right - 10, y + ROW_H - 3), status.color,
                        size=22, align="right")
        hints = HINTS[self.mode]
        for i, hint in enumerate(hints):
            y = PARTY_WINDOW.bottom - PAD - 11 - (len(hints) - 1 - i) * 13
            ui.text(window, hint, (PARTY_WINDOW.x + 12, y), ui.GREY, size=20)

    def _draw_stats(self, window: pygame.Surface) -> None:
        """The stats table. While choosing gear it compares now and after:
        Now / Gear (after) / New, with New green or red where it changes."""
        m, after = self.monster, self._preview()
        x, y = STATS_X, STATS_WINDOW.y + PAD
        ui.text(window, f"{m.name}   Lv{m.level}", (x, y), ui.YELLOW)
        for t, pos in _type_badges(m):
            ui.badge_text(window, type_name(t), pos)
        y += ROW_H + 4
        done, needed = m.xp_progress
        ui.text(window, f"XP {done}/{needed}" if needed else "XP max", (x, y), ui.GREY, size=22)
        if m.skill_points:  # a reminder to spend them (S)
            xp_w = ui.font(22).size(f"XP {done}/{needed}" if needed else "XP max")[0] / 2
            ui.text(window, f"{m.skill_points} skill point{'s' if m.skill_points > 1 else ''}", (x + xp_w + 10, y),
                    GREEN, size=22)
        labels = ("Now", "Gear", "New") if after else ("Base", "Gear", "Total")
        for label, col in zip(labels, COLUMNS):
            ui.text(window, label, (x + col, y), ui.GREY, size=22, align="right")

        def row(name: str, first: str, first_color, gear: str, gear_color, total: str, total_color) -> None:
            nonlocal y
            y += ROW_H
            ui.text(window, name, (x, y))
            for s, color, col in ((first, first_color, COLUMNS[0]), (gear, gear_color, COLUMNS[1]),
                                  (total, total_color, COLUMNS[2])):
                ui.text(window, s, (x + col, y), color, align="right")

        shown = after or m
        for stat in STATS:
            attr = "max_hp" if stat == "hp" else stat
            base, now, total = getattr(m, f"base_{attr}"), getattr(m, attr), getattr(shown, attr)
            percent = shown.gear_bonus(stat)
            gear = f"{percent:+d}%" if percent else "-"
            if after:
                row(STAT_NAMES[stat], str(now), ui.WHITE, gear, _bonus_color(percent),
                    str(total), _bonus_color(total - now) if total != now else ui.WHITE)
            else:
                row(STAT_NAMES[stat], str(base), ui.GREY, gear, _bonus_color(percent),
                    str(total), _bonus_color(total - base) if total != base else ui.WHITE)

        crit_now, crit = m.gear_bonus("crit"), shown.gear_bonus("crit")
        power_now, power = m.gear_bonus("power"), shown.gear_bonus("power")
        for name, unit, base, value_now, value in (("Crit chance", "%", CRIT_CHANCE, crit_now, crit),
                                                   ("Move power", "", 0, power_now, power)):
            def fmt(v: float) -> str:
                return f"{base + v:g}{unit}" if unit else (f"{v:+d}" if v else "-")
            gear = f"{value:+d}{unit}" if value else "-"
            if after:
                row(name, fmt(value_now), ui.WHITE, gear, _bonus_color(value),
                    fmt(value), _bonus_color(value - value_now) if value != value_now else ui.WHITE)
            else:
                row(name, fmt(0) if unit else "-", ui.GREY, gear, _bonus_color(value),
                    fmt(value), _bonus_color(value) if value else ui.WHITE)

    def _draw_slots(self, window: pygame.Surface) -> None:
        for i, slot in enumerate(SLOTS):
            y = GEAR_WINDOW.y + PAD + i * ROW_H
            color = ui.YELLOW if i == self.slot else ui.WHITE
            ui.text(window, SLOT_NAMES[slot], (GEAR_WINDOW.x + 22, y), color)
            gear = self.monster.gear.get(slot)
            if gear:
                ui.text(window, gear.name, (GEAR_WINDOW.x + 100, y), gear.rarity.color)
                ui.text(window, gear.rarity.name, (GEAR_WINDOW.right - 12, y), gear.rarity.color,
                        align="right")
            else:
                ui.text(window, "(empty)", (GEAR_WINDOW.x + 100, y), ui.GREY)

    def _draw_choices(self, window: pygame.Surface) -> None:
        options = self._options()
        for i, option in enumerate(options[self.top:self.top + LIST_ROWS]):
            y = GEAR_WINDOW.y + PAD + i * ROW_H
            if option:
                ui.text(window, option.name, (GEAR_WINDOW.x + 22, y), option.rarity.color)
                ui.text(window, option.rarity.name, (GEAR_WINDOW.right - 18, y), option.rarity.color,
                        align="right")
            else:
                ui.text(window, f"Remove {SLOT_NAMES[self.slot_name].lower()} gear", (GEAR_WINDOW.x + 22, y),
                        ui.GREY)

    def _draw_info(self, window: pygame.Surface, gear: Gear | None) -> None:
        x, y = INFO_WINDOW.x + 12, INFO_WINDOW.y + PAD
        if not gear:
            ui.text(window, "Nothing equipped.", (x, y), ui.GREY)
            count = sum(g.slot == self.slot_name for g in self.bag.gear)
            ui.text(window, f"{count} in the bag" if count else "None in the bag", (x, y + 17), ui.GREY,
                    size=24)
            return
        ui.text(window, gear.name, (x, y), gear.rarity.color)
        ui.text(window, f"{gear.rarity.name} {SLOT_NAMES[gear.slot]} item", (INFO_WINDOW.right - 12, y),
                ui.GREY, align="right")
        ui.text(window, gear.item.description, (x, y + 15), size=24)
        mods = gear.mods
        if not mods and not gear.item.cures:  # (a cure berry's description says what it does)
            ui.text(window, "No stat changes.", (x, y + 31), ui.GREY, size=24)
        for i, (mod, value) in enumerate(mods.items()):  # three columns, up to 9
            pos = (x + (i % 3) * 152, y + 31 + 12 * (i // 3))
            ui.text(window, mod_text(mod, value), pos, _bonus_color(value), size=22)
