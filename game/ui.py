"""Menu windows and text, in the style of the classic Final Fantasy menus.

Windows are drawn on the logical canvas; text is drawn on the scaled window
(positions are still given in logical pixels) so it stays sharp.
"""

from functools import cache

import pygame

from . import settings

WHITE = (240, 240, 248)
GREY = (150, 150, 165)
YELLOW = (248, 224, 96)
SHADOW = (8, 8, 24)

TOP_COLOR = (52, 72, 176)
BOTTOM_COLOR = (16, 20, 88)


@cache
def font(size: int) -> pygame.font.Font:
    return pygame.font.Font(None, size)


def text(window: pygame.Surface, s: str, pos: tuple[float, float], color=WHITE,
         size: int = 28, align: str = "left", shadow: bool = True) -> None:
    """Draw `s`, by default with a drop shadow. `pos` is in logical pixels:
    the top-left, or the top-right / top-centre with `align="right"`/"center"."""
    x, y = round(pos[0] * settings.SCALE), round(pos[1] * settings.SCALE)
    f = font(size)
    if align == "right":
        x -= f.size(s)[0]
    elif align == "center":
        x -= f.size(s)[0] // 2
    if shadow:
        window.blit(f.render(s, True, SHADOW), (x + 2, y + 2))
    window.blit(f.render(s, True, color), (x, y))


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
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, SHADOW, rect)
    color = (88, 208, 96) if fraction > 0.5 else (232, 192, 48) if fraction > 0.2 else (224, 64, 56)
    inner = rect.inflate(-2, -2)
    inner.w = round(inner.w * max(0.0, min(1.0, fraction)))
    if inner.w:
        pygame.draw.rect(surface, color, inner)
