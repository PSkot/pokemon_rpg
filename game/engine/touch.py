"""On-screen touch controls (for phones): a virtual gamepad beside the game.

With touch controls on, the window is wider than the game: the game sits in
the middle (`view_rect`) and the controls fill a panel on either side, so
they never cover it. Touching a button presses its key: it posts the same
KEYDOWN/KEYUP events as the keyboard, so scenes handle it like a key press.
Keys a scene reads while they're held (walking, holding jump) come from
`pressed()`, which adds the held buttons to the keyboard's state. Run is a
toggle (tap it on or off) rather than a key to hold. Scenes can add buttons
for their own keys (`Scene.touch_keys`, e.g. the party screen's S: skills).
A finger can slide from one button to another (e.g. across the D-pad).

The player can resize the buttons, narrow the panels (down to none, with
the buttons over the game, see-through) and move each side's buttons
(`Layout`, set in the pause menu's Controls screen).

The controls are on for touch screens in the browser, or with
POKEMON_TOUCH=1 (the mouse then works as a finger) for testing. Positions
here are in window pixels.
"""

import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass, fields
from functools import cache

import pygame

from .. import settings
from . import ui

SIDE = 300         # width of each side panel, at its widest
MOUSE_FINGER = -1  # finger id of the mouse, with POKEMON_TOUCH=1
REACH = 1.2        # a touch counts this many radii from a button's centre
PANEL_COLOR = (12, 12, 32)
FACE_COLOR = (36, 40, 84)
EDGE_COLOR = (150, 150, 165)
SEE_THROUGH = 140  # opacity of a button over the game


@dataclass(frozen=True)
class Button:
    key: int
    label: str            # "" on the D-pad: an arrow away from its centre
    pos: tuple[int, int]  # centre
    radius: int
    map_only: bool = False  # only on maps (Run)
    toggle: bool = False    # tap on / tap off instead of hold
    pill: bool = False      # a rounded rectangle (menu buttons), twice as wide as tall


@dataclass(frozen=True)
class Spot:
    """Where a button goes in the default layout (panels at their widest)."""
    key: int
    label: str
    right: bool         # in the right panel (else the left)
    edge: int           # centre's distance from the window's edge
    y: int              # centre's height
    radius: int
    top: bool = False   # kept at the top (menu pills) instead of moving with the buttons
    map_only: bool = False
    toggle: bool = False
    pill: bool = False


@dataclass(frozen=True)
class Layout:
    """The player's adjustments to the default layout."""
    size: int = 100   # % of the default button size
    panel: int = 100  # % of the side panels' full width (SIDE)
    left_x: int = 0   # left buttons moved inwards (px; negative = outwards)
    left_y: int = 0   # ... and up (negative = down)
    right_x: int = 0
    right_y: int = 0


# Ranges of the Layout settings: (lowest, highest, step).
RANGES = {"size": (60, 160, 10), "panel": (0, 100, 25), "left_x": (-60, 400, 20), "left_y": (-100, 400, 20),
          "right_x": (-60, 400, 20), "right_y": (-100, 400, 20)}

PILL_Y, PILL_STEP = 56, 68  # first pill's centre, pill to pill
DPAD_STEP = 88              # D-pad centre to button (at size 100)
SPOTS = [
    # Left: menu, D-pad, Run.
    Spot(pygame.K_ESCAPE, "Menu", False, 150, PILL_Y, 26, top=True, pill=True),
    Spot(pygame.K_LEFT, "", False, 150 - DPAD_STEP, 460, 46),
    Spot(pygame.K_RIGHT, "", False, 150 + DPAD_STEP, 460, 46),
    Spot(pygame.K_UP, "", False, 150, 460 - DPAD_STEP, 46),
    Spot(pygame.K_DOWN, "", False, 150, 460 + DPAD_STEP, 46),
    Spot(pygame.K_LSHIFT, "Run", False, 150, 656, 34, map_only=True, toggle=True),
    # Right: party, (the scene's own pills,) A and B.
    Spot(pygame.K_TAB, "Party", True, 150, PILL_Y, 26, top=True, pill=True),
    Spot(pygame.K_SPACE, "A", True, 110, 560, 58),
    Spot(pygame.K_x, "B", True, 255, 640, 40),
]

layout = Layout()
enabled = os.environ.get("POKEMON_TOUCH") == "1"
_mouse = enabled  # the mouse acts as a finger (desktop testing)
_fingers: dict[int, Button | None] = {}  # finger id -> the button it's on
_held: Counter = Counter()               # key -> fingers holding it
_toggled: set[int] = set()               # toggle buttons that are on


def init() -> None:
    """Switch the controls on in the browser on a touch screen. (Before the
    window is made: it's wider with them.)"""
    global enabled
    if sys.platform == "emscripten":
        import platform  # pygbag's: gives access to the page (`window`)
        if platform.window.navigator.maxTouchPoints > 0:
            enabled = True


def configure(prefs: dict) -> None:
    """Use the saved layout settings (`Layout`'s fields; others ignored)."""
    global layout
    names = {f.name for f in fields(Layout)}
    layout = Layout(**{k: int(v) for k, v in prefs.items() if k in names})


def prefs() -> dict:
    """The layout settings, to save."""
    return asdict(layout)


def side() -> int:
    """The width of each side panel."""
    return SIDE * layout.panel // 100 if enabled else 0


def window_size() -> tuple[int, int]:
    """The whole window: the game, plus the side panels if the controls are on.
    (It changes with the panels' width: the main loop remakes the window.)"""
    w, h = settings.WINDOW_SIZE
    return w + 2 * side(), h


def view_rect() -> pygame.Rect:
    """Where in the window the game is drawn."""
    return pygame.Rect((side(), 0), settings.WINDOW_SIZE)


@cache
def _placed(lay: Layout, extra: tuple[tuple[int, str], ...]) -> list[Button]:
    """Every button, placed by `lay`: sizes and distances from the edges
    scale with `lay.size` (towards the bottom corners; the pills towards the
    top ones), and the buttons, not the pills, move by the offsets."""
    scale = lay.size / 100
    width, height = settings.WINDOW_SIZE[0] + 2 * SIDE * lay.panel // 100, settings.WINDOW_SIZE[1]
    spots = SPOTS + [Spot(key, label, True, 150, PILL_Y + PILL_STEP * (i + 1), 26, top=True, pill=True)
                     for i, (key, label) in enumerate(extra)]
    buttons = []
    for spot in spots:
        dx, dy = (lay.right_x, lay.right_y) if spot.right else (lay.left_x, lay.left_y)
        edge = spot.edge * scale + (0 if spot.top else dx)
        y = spot.y * scale if spot.top else height - (height - spot.y) * scale - dy
        x = width - edge if spot.right else edge
        buttons.append(Button(spot.key, spot.label, (round(x), round(y)), round(spot.radius * scale),
                              spot.map_only, spot.toggle, spot.pill))
    return buttons


def _buttons(on_map: bool, extra: tuple[tuple[int, str], ...] = ()) -> list[Button]:
    """The buttons shown: `extra` = the scene's own (key, label)s, as pills
    under Party."""
    return [b for b in _placed(layout, extra) if on_map or not b.map_only]


def _hit(b: Button, pos: tuple[float, float]) -> bool:
    reach = b.radius * REACH
    dx, dy = abs(pos[0] - b.pos[0]), abs(pos[1] - b.pos[1])
    if b.pill:
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
    if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
        if enabled:
            w, h = window_size()
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
        if event.type == pygame.MOUSEBUTTONDOWN:
            _fingers.pop(MOUSE_FINGER, None)
            _move_finger(MOUSE_FINGER, event.pos, on_map, extra)
        elif event.type == pygame.MOUSEBUTTONUP:
            _move_finger(MOUSE_FINGER, None, on_map, extra)
        elif MOUSE_FINGER in _fingers:
            _move_finger(MOUSE_FINGER, event.pos, on_map, extra)
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
def _face(radius: int, pill: bool, lit: bool, see_through: bool) -> pygame.Surface:
    """A button's background (`see_through`: over the game)."""
    r = radius
    surface = pygame.Surface((r * 4, r * 2) if pill else (r * 2, r * 2), pygame.SRCALPHA)
    rect = surface.get_rect()
    fill = ui.TOP_COLOR if lit else FACE_COLOR
    pygame.draw.rect(surface, fill, rect, border_radius=r)
    pygame.draw.rect(surface, EDGE_COLOR, rect, 2, border_radius=r)
    if see_through:
        surface.set_alpha(SEE_THROUGH)
    return surface


def draw(window: pygame.Surface, on_map: bool, extra: tuple[tuple[int, str], ...] = ()) -> None:
    """Draw the side panels and their buttons on the whole window."""
    if not enabled:
        return
    w, h = window_size()
    view = view_rect()
    window.fill(PANEL_COLOR, (0, 0, view.left, h))
    window.fill(PANEL_COLOR, (view.right, 0, w - view.right, h))
    scale = layout.size / 100
    for b in _buttons(on_map, extra):
        lit = _held[b.key] > 0 or b.key in _toggled
        face = _face(b.radius, b.pill, lit, view.left < b.pos[0] < view.right)
        window.blit(face, face.get_rect(center=b.pos))
        color = ui.YELLOW if lit else ui.WHITE
        if b.label:
            size = 40 if b.label in "AB" else 30 if len(b.label) == 1 else 26
            _label(window, b.label, b.pos, color, round(size * scale))
        else:
            _arrow(window, b, color, scale)


def _label(window: pygame.Surface, s: str, center: tuple[int, int], color, size: int) -> None:
    font = ui.font(size)
    rect = font.render(s, True, color).get_rect(center=center)
    window.blit(font.render(s, True, ui.SHADOW), rect.move(2, 2))
    window.blit(font.render(s, True, color), rect)


def _arrow(window: pygame.Surface, b: Button, color, scale: float) -> None:
    """A D-pad button's arrow, pointing away from the D-pad's centre."""
    dx, dy = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}[b.key]
    cx, cy = b.pos
    tip, back, half = 17 * scale, 12 * scale, 16 * scale
    points = [(cx + dx * tip, cy + dy * tip),
              (cx - dx * back - dy * half, cy - dy * back + dx * half),
              (cx - dx * back + dy * half, cy - dy * back - dx * half)]
    pygame.draw.polygon(window, ui.SHADOW, [(x + 2, y + 2) for x, y in points])
    pygame.draw.polygon(window, color, points)
