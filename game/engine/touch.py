"""On-screen touch controls (for phones): a virtual gamepad over the game.

Touching a button presses its key: it posts the same KEYDOWN/KEYUP events
as the keyboard, so scenes handle it like a key press. Keys a scene reads
while they're held (walking, holding jump) come from `pressed()`, which
adds the held buttons to the keyboard's state. Run is a toggle (tap it on
or off) rather than a key to hold. Scenes can add buttons for their own
keys (`Scene.touch_keys`, e.g. the party screen's S: skills). A finger can slide from one button to
another (e.g. across the D-pad).

The controls show on touch screens in the browser, after any touch, or
with POKEMON_TOUCH=1 (the mouse then works as a finger) for testing.
"""

import math
import os
import sys
from collections import Counter
from dataclasses import dataclass
from functools import cache

import pygame

from .. import settings
from . import ui

MOUSE_FINGER = -1  # finger id of the mouse, with POKEMON_TOUCH=1
REACH = 1.2        # a touch counts this many radii from a button's centre
ALPHA = 110        # opacity of a button (pressed: PRESSED_ALPHA)
PRESSED_ALPHA = 190


@dataclass(frozen=True)
class Button:
    key: int
    label: str            # "" on the D-pad: an arrow away from its centre
    pos: tuple[int, int]  # centre, in logical pixels
    radius: int
    map_only: bool = False  # only on maps (attacks, Run)
    toggle: bool = False    # tap on / tap off instead of hold
    pill: bool = False      # a rounded rectangle (menu buttons) instead of a circle


def _arc(i: int) -> tuple[int, int]:
    """The i-th attack button's place on an arc around the A button."""
    angle = math.radians(90 + i * 25)
    return round(A_POS[0] + 95 * math.cos(angle)), round(A_POS[1] - 95 * math.sin(angle))


A_POS = (588, 290)
DPAD = (78, 282)  # centre of the D-pad
BUTTONS = [
    Button(pygame.K_LEFT, "", (DPAD[0] - 44, DPAD[1]), 24),
    Button(pygame.K_RIGHT, "", (DPAD[0] + 44, DPAD[1]), 24),
    Button(pygame.K_UP, "", (DPAD[0], DPAD[1] - 44), 24),
    Button(pygame.K_DOWN, "", (DPAD[0], DPAD[1] + 44), 24),
    Button(pygame.K_LSHIFT, "Run", (152, 330), 17, map_only=True, toggle=True),
    Button(pygame.K_SPACE, "A", A_POS, 28),
    Button(pygame.K_x, "B", (536, 335), 18),
    *[Button(pygame.K_1 + i, str(i + 1), _arc(i), 18 if i == 0 else 16, map_only=True) for i in range(5)],
    Button(pygame.K_ESCAPE, "Menu", (604, 18), 14, pill=True),
    Button(pygame.K_TAB, "Party", (546, 18), 14, pill=True),
]

enabled = os.environ.get("POKEMON_TOUCH") == "1"
_mouse = enabled  # the mouse acts as a finger (desktop testing)
_fingers: dict[int, Button | None] = {}  # finger id -> the button it's on
_held: Counter = Counter()               # key -> fingers holding it
_toggled: set[int] = set()               # toggle buttons that are on


def init() -> None:
    """Switch the controls on in the browser on a touch screen."""
    global enabled
    if sys.platform == "emscripten":
        import platform  # pygbag's: gives access to the page (`window`)
        if platform.window.navigator.maxTouchPoints > 0:
            enabled = True


def _buttons(on_map: bool, extra: tuple[tuple[int, str], ...]) -> list[Button]:
    """The buttons shown: `extra` = the scene's own (key, label)s, as pills
    left of Party."""
    scene_buttons = [Button(key, label, (488 - 58 * i, 18), 14, pill=True) for i, (key, label) in enumerate(extra)]
    return [b for b in BUTTONS if on_map or not b.map_only] + scene_buttons


def _hit(b: Button, pos: tuple[float, float]) -> bool:
    reach = b.radius * REACH
    dx, dy = abs(pos[0] - b.pos[0]), abs(pos[1] - b.pos[1])
    if b.pill:  # (twice as wide as tall)
        return dx <= reach * 2 and dy <= reach
    return dx * dx + dy * dy <= reach * reach


def _button_at(pos: tuple[float, float], on_map: bool, extra) -> Button | None:
    return next((b for b in _buttons(on_map, extra) if _hit(b, pos)), None)


def _post(kind: int, key: int) -> None:
    pygame.event.post(pygame.event.Event(kind, key=key, mod=0, unicode="", scancode=0))


def _press(b: Button) -> None:
    if b.toggle:
        _toggled.symmetric_difference_update({b.key})
        return
    _held[b.key] += 1
    if _held[b.key] == 1:
        _post(pygame.KEYDOWN, b.key)


def _release(b: Button) -> None:
    if b.toggle:
        return
    _held[b.key] -= 1
    if _held[b.key] == 0:
        _post(pygame.KEYUP, b.key)


def _move_finger(finger: int, pos: tuple[float, float] | None, on_map: bool, extra) -> None:
    """Put `finger` on the button at `pos` (None: lifted)."""
    old = _fingers.get(finger)
    new = _button_at(pos, on_map, extra) if pos else None
    if new == old:
        return
    if old:
        _release(old)
    # Sliding onto a toggle doesn't flip it; only touching it does.
    if new and not (new.toggle and finger in _fingers):
        _press(new)
    if pos:
        _fingers[finger] = new
    else:
        _fingers.pop(finger, None)


def handle(event: pygame.event.Event, on_map: bool, extra: tuple[tuple[int, str], ...] = ()) -> bool:
    """Handle a touch (or, for testing, mouse) event. True if it was one:
    the game itself doesn't use touches or the mouse. `on_map`: show the
    map's buttons; `extra`: the scene's own buttons (see `_buttons`)."""
    global enabled
    w, h = settings.LOGICAL_SIZE
    if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
        enabled = True
        pos = (event.x * w, event.y * h)
        if event.type == pygame.FINGERDOWN:
            _fingers.pop(event.finger_id, None)
        _move_finger(event.finger_id, None if event.type == pygame.FINGERUP else pos, on_map, extra)
        return True
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
        if getattr(event, "touch", False):
            return True  # the mouse events a touch also makes
        if not _mouse:
            return False
        pos = (event.pos[0] / settings.SCALE, event.pos[1] / settings.SCALE)
        if event.type == pygame.MOUSEBUTTONDOWN:
            _fingers.pop(MOUSE_FINGER, None)
            _move_finger(MOUSE_FINGER, pos, on_map, extra)
        elif event.type == pygame.MOUSEBUTTONUP:
            _move_finger(MOUSE_FINGER, None, on_map, extra)
        elif MOUSE_FINGER in _fingers:
            _move_finger(MOUSE_FINGER, pos, on_map, extra)
        return True
    return False


class _Pressed:
    """`pygame.key.get_pressed()`, plus the held (and toggled) buttons."""

    def __init__(self):
        self.keys = pygame.key.get_pressed()

    def __getitem__(self, key: int) -> bool:
        return bool(self.keys[key]) or _held[key] > 0 or key in _toggled


def pressed() -> _Pressed:
    return _Pressed()


# ------------------------------------------------------------------ drawing

@cache
def _face(radius: int, pill: bool, lit: bool) -> pygame.Surface:
    """A button's background, in window pixels."""
    r = radius * settings.SCALE
    size = (r * 4, r * 2) if pill else (r * 2, r * 2)
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    fill = (*(ui.TOP_COLOR if lit else ui.SHADOW), PRESSED_ALPHA if lit else ALPHA)
    if pill:
        pygame.draw.rect(surface, fill, rect, border_radius=r)
        pygame.draw.rect(surface, (*ui.WHITE, 150), rect, 2, border_radius=r)
    else:
        pygame.draw.circle(surface, fill, (r, r), r)
        pygame.draw.circle(surface, (*ui.WHITE, 150), (r, r), r, 2)
    return surface


def draw(window: pygame.Surface, on_map: bool, extra: tuple[tuple[int, str], ...] = ()) -> None:
    if not enabled:
        return
    for b in _buttons(on_map, extra):
        lit = _held[b.key] > 0 or b.key in _toggled
        face = _face(b.radius, b.pill, lit)
        window.blit(face, face.get_rect(center=(b.pos[0] * settings.SCALE, b.pos[1] * settings.SCALE)))
        if not b.label:
            _arrow(window, b, lit)
            continue
        size = 30 if b.radius >= 24 else 24 if len(b.label) == 1 else 20
        y = b.pos[1] - size / 2 / settings.SCALE * 0.75
        ui.text(window, b.label, (b.pos[0], y), ui.YELLOW if lit else ui.WHITE, size=size, align="center")


def _arrow(window: pygame.Surface, b: Button, lit: bool) -> None:
    """A D-pad button's arrow, pointing away from the D-pad's centre."""
    dx, dy = (b.pos[0] - DPAD[0]) / 44, (b.pos[1] - DPAD[1]) / 44
    cx, cy = b.pos[0] * settings.SCALE, b.pos[1] * settings.SCALE
    tip, back, half = 14, 10, 13
    points = [(cx + dx * tip, cy + dy * tip),
              (cx - dx * back - dy * half, cy - dy * back + dx * half),
              (cx - dx * back + dy * half, cy - dy * back - dx * half)]
    pygame.draw.polygon(window, ui.SHADOW, [(x + 2, y + 2) for x, y in points])
    pygame.draw.polygon(window, ui.YELLOW if lit else ui.WHITE, points)
