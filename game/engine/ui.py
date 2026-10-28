"""Menu windows and text, in the style of the classic Final Fantasy menus.

Windows are drawn on the logical canvas; text is drawn on the scaled window
(positions are still given in logical pixels) so it stays sharp.
"""

from functools import cache

import pygame

from .. import settings

WHITE = (240, 240, 248)
GREY = (150, 150, 165)
YELLOW = (248, 224, 96)
SHADOW = (8, 8, 24)

# Text is drawn this much bigger than the sizes the screens ask for (they
# were laid out for smaller text), so it stays readable on phones.
TEXT_SCALE = 1.25

TOP_COLOR = (52, 72, 176)
BOTTOM_COLOR = (16, 20, 88)


@cache
def font(size: int) -> pygame.font.Font:
    """The font for text of `size` (enlarged by TEXT_SCALE)."""
    return pygame.font.Font(None, round(size * TEXT_SCALE))


@cache
def unscaled_font(size: int) -> pygame.font.Font:
    """The font at exactly `size` (e.g. labels sized to fit a button)."""
    return pygame.font.Font(None, size)


@cache
def _grown(size: int) -> int:
    """How much taller (window px) text of `size` is than unscaled."""
    return font(size).get_height() - unscaled_font(size).get_height()


def text(window: pygame.Surface, s: str, pos: tuple[float, float], color=WHITE,
         size: int = 28, align: str = "left", shadow: bool = True) -> None:
    """Draw `s`, by default with a drop shadow. `pos` is in logical pixels:
    the top-left, or the top-right / top-centre with `align="right"`/"center"."""
    # (Grown text stays centred on the line it was laid out for.)
    x, y = round(pos[0] * settings.SCALE), round(pos[1] * settings.SCALE) - _grown(size) // 2
    f = font(size)
    if align == "right":
        x -= f.size(s)[0]
    elif align == "center":
        x -= f.size(s)[0] // 2
    if shadow:
        window.blit(_render(f, s, SHADOW), (x + 2, y + 2))
    window.blit(_render(f, s, color), (x, y))


def _render(f: pygame.font.Font, s: str, color) -> pygame.Surface:
    """`s` rendered; the font has no Poké Dollar sign (₽), so it's drawn
    as a P with a bar across its stem."""
    if "₽" not in s:
        return f.render(s, True, color)
    surface = f.render(s.replace("₽", "P"), True, color)
    min_x, max_x, _, cap, _ = f.metrics("P")[0]
    bar_y = f.get_ascent() - round(cap * 0.28)
    thick = max(1, round(f.get_height() / 14))
    for i, ch in enumerate(s):
        if ch == "₽":
            left = f.size(s[:i].replace("₽", "P"))[0] + min_x
            surface.fill(color, (left - thick, bar_y, round((max_x - min_x) * 0.75) + thick, thick))
    return surface


@cache
def _gradient(w: int, h: int) -> pygame.Surface:
    surface = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        color = [round(a + (b - a) * t) for a, b in zip(TOP_COLOR, BOTTOM_COLOR)]
        pygame.draw.line(surface, color, (0, y), (w, y))
    return surface


def window_box(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """A blue gradient window with a light double border."""
    rect = pygame.Rect(rect)
    surface.blit(_gradient(rect.w, rect.h), rect)
    pygame.draw.rect(surface, GREY, rect, 1, border_radius=3)
    pygame.draw.rect(surface, WHITE, rect.inflate(-2, -2), 1, border_radius=3)


def cursor(surface: pygame.Surface, right: int, mid_y: int) -> None:
    """A small pointer whose tip is at (`right`, `mid_y`)."""
    pygame.draw.polygon(surface, SHADOW, [(right - 6, mid_y - 3), (right + 1, mid_y + 1), (right - 6, mid_y + 5)])
    pygame.draw.polygon(surface, WHITE, [(right - 7, mid_y - 4), (right, mid_y), (right - 7, mid_y + 4)])


def hp_bar(surface: pygame.Surface, rect: pygame.Rect, fraction: float) -> None:
    color = (88, 208, 96) if fraction > 0.5 else (232, 192, 48) if fraction > 0.2 else (224, 64, 56)
    bar(surface, rect, fraction, color)


def bar(surface: pygame.Surface, rect: pygame.Rect, fraction: float, color) -> None:
    """A dark bar, filled from the left to `fraction`."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, SHADOW, rect)
    inner = rect.inflate(-2, -2)
    inner.w = round(inner.w * max(0.0, min(1.0, fraction)))
    if inner.w:
        pygame.draw.rect(surface, color, inner)


BADGE_SIZE = (46, 13)


def badge(surface: pygame.Surface, pos: tuple[int, int], color) -> pygame.Rect:
    """A small coloured label box (for a type) at top-left `pos`; its text
    goes on the window with `badge_text`."""
    rect = pygame.Rect(pos, BADGE_SIZE)
    pygame.draw.rect(surface, SHADOW, rect.move(1, 1), border_radius=3)
    pygame.draw.rect(surface, color, rect, border_radius=3)
    pygame.draw.rect(surface, [c // 2 for c in color], rect, 1, border_radius=3)
    return rect


def badge_text(window: pygame.Surface, s: str, pos: tuple[int, int]) -> None:
    rect = pygame.Rect(pos, BADGE_SIZE)
    text(window, s.upper(), (rect.centerx, rect.y + 2.5), WHITE, size=19, align="center")


class ListPanel:
    """A window with a title and rows of (text, colour, right-hand text),
    centred on `center` (e.g. the loot from a battle or a chest)."""

    ROW_H = 17
    PAD = 9

    def __init__(self, title: str, rows: list[tuple[str, tuple[int, int, int], str]],
                 center: tuple[int, int], width: int = 320, footer: str = "Enter: continue"):
        self.title, self.rows, self.footer = title, rows, footer
        height = self.PAD * 2 + self.ROW_H * (len(rows) + (2 if footer else 1)) + 4
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = center

    def draw(self, surface: pygame.Surface) -> None:
        window_box(surface, self.rect)

    def draw_overlay(self, window: pygame.Surface) -> None:
        x, right = self.rect.x + 12, self.rect.right - 12
        y = self.rect.y + self.PAD
        text(window, self.title, (x, y), YELLOW)
        for i, (s, color, side) in enumerate(self.rows):
            row_y = y + self.ROW_H * (i + 1) + 4
            text(window, s, (x, row_y), color, size=26)
            text(window, side, (right, row_y), GREY, size=22, align="right")
        if self.footer:
            text(window, self.footer, (right, self.rect.bottom - self.PAD - 11), GREY, size=20, align="right")


def blit_scaled(window: pygame.Surface, surface: pygame.Surface, pos: tuple[int, int]) -> None:
    """Draw a logical-resolution `surface` (e.g. a menu window drawn over
    everything) on the scaled window, at logical `pos`."""
    s = settings.SCALE
    window.blit(pygame.transform.scale_by(surface, s), (pos[0] * s, pos[1] * s))


def wrap(s: str, size: int, width: float) -> list[str]:
    """`s` split into lines that fit `width` logical px at font `size`."""
    f, lines, line = font(size), [], ""
    for word in s.split():
        attempt = f"{line} {word}" if line else word
        if line and f.size(attempt)[0] / settings.SCALE > width:
            lines.append(line)
            line = word
        else:
            line = attempt
    return lines + [line] if line else lines
