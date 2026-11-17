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
(`Layout`, set in the pause menu's Controls screen). By default the panels
are Auto: as wide as the screen's shape leaves beside the game, so the
game fills the screen's height (each side's buttons are fitted into its panel,
`_fit`: moved in, drawn closer together and smaller, the pills stacked
down the panel and spilling over to the other side; only with no panels
do they go over the game).

The controls are on for touch screens in the browser, or with
POKEMON_TOUCH=1 (the mouse then works as a finger) for testing. Positions
here are in window pixels.

The game is landscape only. A phone showing the page upright (`portrait`:
its rotation locked, or the page simply held upright) gets a portrait
window with the game drawn into it turned a quarter turn clockwise
(`rotated`, set by the main loop), so it's played with the phone held
sideways, its top to the left; touches are turned back (`_unturn`).
POKEMON_PORTRAIT=1 forces this on the desktop, for testing.
"""

import math
import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass, fields, replace
from functools import cache

import pygame

from .. import settings
from . import ui

SIDE = 300         # width of each side panel, at its widest
AUTO = -1          # Layout.panel: fit the screen's shape (`side`)
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
    scale: float = 1.0      # its label's (or arrow's) size: the Layout's size, shrunk to fit a panel


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
    size: int = 80     # % of the default button size
    panel: int = AUTO  # % of the side panels' full width (SIDE), or AUTO
    left_x: int = 0   # left buttons moved inwards (px; negative = outwards)
    left_y: int = 0   # ... and up (negative = down)
    right_x: int = 0
    right_y: int = 0


# Ranges of the Layout settings: (lowest, highest, step); the panels' AUTO
# comes before the lowest.
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
rotated = False  # the window is portrait, with the game turned into it (set by the main loop)
_mouse = enabled  # the mouse acts as a finger (desktop testing)
_fingers: dict[int, Button | None] = {}  # finger id -> the button it's on
_held: Counter = Counter()               # key -> fingers holding it
# Presses on the game that hit no button, for the scene (`Scene.tap`):
# (position in logical px, whether it's a drag after the press).
_taps: list[tuple[tuple[float, float], bool]] = []
_mouse_down = False  # the left button is held (mouse without touch controls)
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
    if not enabled:
        return 0
    if layout.panel != AUTO:
        return SIDE * layout.panel // 100
    # Auto: the window takes the screen's shape (the game at full height).
    w, h = settings.WINDOW_SIZE
    screen_w, screen_h = _screen_size()
    return max(0, min(SIDE, round((h * screen_w / screen_h - w) / 2)))


def _page_size() -> tuple[int, int]:
    """The space the window is shown in: the page (it changes when a phone
    turns or goes fullscreen), or the desktop."""
    if sys.platform == "emscripten":
        import platform  # pygbag's: gives access to the page (`window`)
        return platform.window.innerWidth or 1, platform.window.innerHeight or 1
    return pygame.display.get_desktop_sizes()[0]


def portrait() -> bool:
    """A touch screen showing the page upright: the game is turned to fit
    it sideways (see the module's notes)."""
    if os.environ.get("POKEMON_PORTRAIT") == "1":
        return True
    if not enabled or sys.platform != "emscripten":
        return False
    w, h = _page_size()
    return h > w


def _screen_size() -> tuple[int, int]:
    """The space the game is shown in, the way it's played: landscape (a
    page shown upright is played sideways)."""
    w, h = _page_size()
    return (max(w, h), min(w, h)) if portrait() else (w, h)


def display_size() -> tuple[int, int]:
    """The real window: `window_size`, turned upright when `portrait`."""
    w, h = window_size()
    return (h, w) if portrait() else (w, h)


def _unturn(pos: tuple[float, float]) -> tuple[float, float]:
    """A position in the real window, in the game's (landscape) window: the
    game is drawn turned a quarter turn clockwise when `rotated`."""
    if not rotated:
        return pos
    return pos[1], window_size()[1] - 1 - pos[0]


def window_size() -> tuple[int, int]:
    """The whole window: the game, plus the side panels if the controls are on.
    (It changes with the panels' width: the main loop remakes the window.)"""
    w, h = settings.WINDOW_SIZE
    return w + 2 * side(), h


def view_rect() -> pygame.Rect:
    """Where in the window the game is drawn."""
    return pygame.Rect((side(), 0), settings.WINDOW_SIZE)


@cache
def _placed(lay: Layout, side: int, extra: tuple[tuple[int, str], ...]) -> list[Button]:
    """Every button, placed by `lay`: sizes and distances from the edges
    scale with `lay.size` (towards the bottom corners; the pills towards the
    top ones), and the buttons, not the pills, move by the offsets."""
    scale = lay.size / 100
    width, height = settings.WINDOW_SIZE[0] + 2 * side, settings.WINDOW_SIZE[1]
    spots = SPOTS + [Spot(key, label, True, 150, PILL_Y + PILL_STEP * (i + 1), 26, top=True, pill=True)
                     for i, (key, label) in enumerate(extra)]
    buttons = []
    for spot in spots:
        dx, dy = (lay.right_x, lay.right_y) if spot.right else (lay.left_x, lay.left_y)
        edge = spot.edge * scale + (0 if spot.top else dx)
        y = spot.y * scale if spot.top else height - (height - spot.y) * scale - dy
        x = width - edge if spot.right else edge
        buttons.append(Button(spot.key, spot.label, (round(x), round(y)), round(spot.radius * scale),
                              spot.map_only, spot.toggle, spot.pill, scale))
    if side <= 0:
        return buttons  # no panels: the buttons go over the game, as placed
    return _fit(buttons, [s.right for s in spots], side, width, height)


FIT_MARGIN = 6   # px kept between the buttons and the panel's edges
MIN_FIT = 0.6    # round buttons shrink to fit a narrow panel down to this much
PILL_GAP = 6     # px between pills, and between the pills and the round buttons
MIN_PILL = 40    # a pill's least height plus gap (px), squeezed in with many


def _fit(buttons: list[Button], rights: list[bool], side: int, width: int, height: int) -> list[Button]:
    """The buttons fitted into the side panels, off the game: each side's
    round buttons shrunk (down to `MIN_FIT`) and moved into its panel; the
    pills narrowed to the panels and stacked down their middles, from the
    top to just above the round buttons. The scene's pills go under Party,
    and those that don't fit there under Menu; only if neither has room
    are they squeezed closer (and smaller)."""
    room = side - 2 * FIT_MARGIN
    fitted, floors, pills = [], [], []
    for right in (False, True):
        group = [b for b, r in zip(buttons, rights) if r == right and not b.pill]
        placed = _fit_rounds(group, width - side if right else 0, side, height)
        fitted += placed
        floors.append(min((b.pos[1] - b.radius for b in placed), default=height) - PILL_GAP)
        pills.append([b for b, r in zip(buttons, rights) if r == right and b.pill])
    first = next(b for b in buttons if b.pill)
    radius = min(first.radius, room // 4)
    step = PILL_STEP * first.scale
    top = first.pos[1] - first.radius
    # How many pills each side holds at the normal spacing; the right's extras overflow left.
    fits = [max(1, int((floor - top - 2 * radius) // step) + 1) for floor in floors]
    while len(pills[1]) > fits[1] and len(pills[0]) < fits[0]:
        pills[0].append(pills[1].pop(fits[1]))
    for column, floor, x in zip(pills, floors, (side // 2, width - side // 2)):
        r, gap = radius, step
        if len(column) > 1 and top + gap * (len(column) - 1) + 2 * r > floor:
            gap = max(MIN_PILL, (floor - top) / len(column))  # (buttons moved up high: over them)
            r = min(r, round(gap - PILL_GAP) // 2)
        for i, b in enumerate(column):
            fitted.append(replace(b, pos=(x, round(top + r + gap * i)), radius=r, scale=b.scale * r / b.radius))
    return fitted


def _fit_rounds(group: list[Button], x0: int, side: int, height: int) -> list[Button]:
    """One panel's round buttons (it starts at `x0`), fitted into it: moved
    closer together (`spread`) and shrunk (`size`), keeping them as big as
    the room allows without touching each other; then moved into the panel
    (or, too wide for it even at `MIN_FIT`, against the window's edge)."""
    if not group:
        return []
    room = side - 2 * FIT_MARGIN
    old_cx = (min(b.pos[0] for b in group) + max(b.pos[0] for b in group)) / 2
    pairs = [(a, b) for i, a in enumerate(group) for b in group[i + 1:]]

    def size_for(spread: float) -> float:
        """The buttons' biggest size with their centres `spread` apart."""
        size = min([1.0] + [(room / 2 - abs(b.pos[0] - old_cx) * spread) / b.radius for b in group])
        for a, b in pairs:
            size = min(size, (math.dist(a.pos, b.pos) * spread - 4) / (a.radius + b.radius))
        return size

    spread, size = max(((f / 40, size_for(f / 40)) for f in range(16, 41)), key=lambda t: (t[1], t[0]))
    if size < MIN_FIT:
        spread = size = MIN_FIT
    lo = min(old_cx + (b.pos[0] - old_cx) * spread - b.radius * size for b in group)
    hi = max(old_cx + (b.pos[0] - old_cx) * spread + b.radius * size for b in group)
    if hi - lo <= room:
        shift = min(max(lo, x0 + FIT_MARGIN), x0 + side - FIT_MARGIN - (hi - lo)) - lo
    else:
        shift = (x0 if x0 == 0 else x0 + side - (hi - lo)) - lo
    # Shrunk towards the lowest button, kept on the screen.
    low = max(group, key=lambda b: b.pos[1])
    low_y = min(low.pos[1], height - FIT_MARGIN - low.radius * size)
    top = min(low_y - (low.pos[1] - b.pos[1]) * spread - b.radius * size for b in group)
    low_y += max(0, FIT_MARGIN - top)
    return [replace(b, pos=(round(old_cx + (b.pos[0] - old_cx) * spread + shift),
                            round(low_y - (low.pos[1] - b.pos[1]) * spread)),
                    radius=round(b.radius * size), scale=b.scale * size) for b in group]


def _buttons(on_map: bool, extra: tuple[tuple[int, str], ...] = ()) -> list[Button]:
    """The buttons shown: `extra` = the scene's own (key, label)s, as pills
    under Party."""
    return [b for b in _placed(layout, side(), extra) if on_map or not b.map_only]


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
    """Handle a touch or mouse event. True if it was one: the scenes don't
    get them, only the taps (`taps`). `on_map`: show the map's buttons;
    `extra`: the scene's own buttons (see `_buttons`)."""
    global _mouse_down
    if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
        if enabled:
            w, h = (window_size()[::-1]) if rotated else window_size()  # (the real window)
            pos = _unturn((event.x * w, event.y * h))
            if event.type == pygame.FINGERDOWN:
                _fingers.pop(event.finger_id, None)
            _finger(event.finger_id, None if event.type == pygame.FINGERUP else pos, on_map, extra,
                    drag=event.type == pygame.FINGERMOTION)
        return True
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
        if getattr(event, "touch", False):
            return True  # the mouse events a touch also makes
        mouse_pos = _unturn(event.pos)
        if not _mouse:  # a plain mouse: only taps on the game (left button)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _mouse_down = True
                _tap(mouse_pos, drag=False)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                _mouse_down = False
            elif event.type == pygame.MOUSEMOTION and _mouse_down:
                _tap(mouse_pos, drag=True)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            _fingers.pop(MOUSE_FINGER, None)
            _finger(MOUSE_FINGER, mouse_pos, on_map, extra, drag=False)
        elif event.type == pygame.MOUSEBUTTONUP:
            _finger(MOUSE_FINGER, None, on_map, extra, drag=False)
        elif MOUSE_FINGER in _fingers:
            _finger(MOUSE_FINGER, mouse_pos, on_map, extra, drag=True)
        return True
    return False


def _finger(finger: int, pos: tuple[float, float] | None, on_map: bool, extra, drag: bool) -> None:
    """A finger moved: buttons first; a press (or a drag after one) that
    started on no button is a tap on the game."""
    started_free = finger in _fingers and _fingers[finger] is None
    _move_finger(finger, pos, on_map, extra)
    if pos is None:
        _fingers.pop(finger, None)
    elif finger not in _fingers:
        _fingers[finger] = None  # down on no button: followed, for dragging
    if pos and _fingers.get(finger) is None and (started_free or not drag):
        _tap(pos, drag)


def _tap(pos: tuple[float, float], drag: bool) -> None:
    view = view_rect()
    if view.collidepoint(pos):
        _taps.append((((pos[0] - view.x) / settings.SCALE, (pos[1] - view.y) / settings.SCALE), drag))


def taps() -> list[tuple[tuple[float, float], bool]]:
    """The taps on the game since the last call: (position in logical px,
    whether it's a drag)."""
    got = _taps[:]
    _taps.clear()
    return got


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
    for b in _buttons(on_map, extra):
        lit = _held[b.key] > 0 or b.key in _toggled
        face = _face(b.radius, b.pill, lit, view.left < b.pos[0] < view.right)
        window.blit(face, face.get_rect(center=b.pos))
        color = ui.YELLOW if lit else ui.WHITE
        if b.label:
            size = 40 if b.label in "AB" else 30 if len(b.label) == 1 else 26
            _label(window, b.label, b.pos, color, round(size * b.scale))
        else:
            _arrow(window, b, color, b.scale)


def _label(window: pygame.Surface, s: str, center: tuple[int, int], color, size: int) -> None:
    font = ui.unscaled_font(size)
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
