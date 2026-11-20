"""Entry point: window and game loop.

    python -m game

The game starts at the title screen (continue, load or start a new game).
A new game starts in Pallet Town; doorways at a town's edges lead onto
routes (Route 1 to Viridian City). On the maps: Left/Right walk,
hold Shift to run, Space jumps (hold for a higher jump), Up opens chests
and goes through doorways, Tab opens the party screen, F1 toggles debug
boxes. Walk into wild Pokémon to battle them. Esc pauses (resume, save,
load or quit). Battles, chests, fainting and leaving a map autosave.

The loop is async so the game can also run in a browser (pygbag, see
web/README.md): it hands control back to the page once per frame.
"""

import asyncio
import traceback

import pygame

from . import saves, settings
from .dev import DEV
from .engine import touch, ui
from .engine.scene import Scene, Transition
from .scenes.pause import PauseMenu
from .scenes.title import TitleScene


def fit_canvas(size: tuple[int, int]) -> None:
    """In the browser: make the page's canvas as big as fits, in the
    window's shape (`size`). (pygbag sizes it once, before the window
    exists, so it comes out square; this also follows the page's size, e.g.
    when a phone turns.)"""
    import platform  # pygbag's: gives access to the page (`window`)
    window = platform.window
    w, h = size
    scale = min(window.innerWidth / w, window.innerHeight / h)
    width, height = f"{int(w * scale)}px", f"{int(h * scale)}px"
    # Shrunk to fewer screen pixels than it has (e.g. on phones), the canvas
    # is smoothed: pixelated, whole columns of pixels drop out of the text.
    # (devicePixelRatio: screen pixels per CSS px.)
    rendering = "pixelated" if scale * window.devicePixelRatio >= 1 else "auto"
    style = window.canvas.style
    if style.width != width or style.height != height or style.imageRendering != rendering:
        style.width, style.height = width, height
        style.imageRendering = rendering
        platform.document.body.style.background = "#0c0c20"  # (touch.PANEL_COLOR)


async def main() -> None:
    pygame.init()
    touch.init()
    prefs = saves.load_prefs()
    touch.configure(prefs.get("touch", {}))
    DEV.configure(prefs.get("dev", {}))  # (the dev password and settings, if this machine or browser has them)
    # With touch controls, the window has side panels for them; the game is
    # drawn in the middle (`window`).
    screen, window = _make_window()
    pygame.display.set_caption(" ".join(p for p in (settings.TITLE, DEV.summary() and f"[{DEV.summary()}]") if p))
    canvas = pygame.Surface(settings.LOGICAL_SIZE)
    clock = pygame.time.Clock()

    scene: Scene = TitleScene()

    pause: PauseMenu | None = None

    running = True
    while running:
        if saves.WEB:  # a crash in the browser shows on the page instead of freezing it
            try:
                running, scene, pause, screen, window = _frame(clock, canvas, screen, window, scene, pause)
            except Exception:
                await _show_crash(screen, traceback.format_exc())
                return
        else:
            running, scene, pause, screen, window = _frame(clock, canvas, screen, window, scene, pause)
        await asyncio.sleep(0)

    pygame.quit()


def _make_window() -> tuple[pygame.Surface, pygame.Surface]:
    """The window (`screen`: the game and its touch panels, landscape) and
    where in it the game is drawn (`window`). On a phone held upright the
    real window is portrait and `screen` a surface of its own, drawn into
    it turned (`_show`; touch.portrait)."""
    touch.rotated = touch.portrait()
    display = pygame.display.set_mode(touch.display_size())
    screen = pygame.Surface(touch.window_size()) if touch.rotated else display
    return screen, screen.subsurface(touch.view_rect())


def _show(screen: pygame.Surface) -> None:
    """Put the frame on the real window (turned a quarter turn clockwise on
    a phone held upright) and show it."""
    if touch.rotated:
        pygame.display.get_surface().blit(pygame.transform.rotate(screen, -90), (0, 0))
    pygame.display.flip()


async def _show_crash(screen: pygame.Surface, text: str) -> None:
    """The error, on screen (for a screenshot) and in the browser's console."""
    print(text)
    screen = pygame.display.get_surface()
    lines = ["The game crashed. Please send a screenshot of this:", ""] + text.splitlines()[-24:]
    font = pygame.font.Font(None, 22)
    while True:
        pygame.event.get()
        screen.fill((20, 20, 40))
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, (255, 230, 120) if i == 0 else (230, 230, 230)), (12, 12 + i * 20))
        pygame.display.flip()
        await asyncio.sleep(0.2)


def _frame(clock, canvas, screen, window, scene, pause):
    """One frame of the game loop: returns what it changed."""
    running = True
    dt = clock.tick(settings.FPS) / 1000
    # The map's touch buttons show on maps, and all of them while their
    # layout is being set (pause menu -> Controls).
    on_map = pause.editing_controls if pause else scene.touch_map
    extra = pause.touch_keys if pause else scene.touch_keys
    for event in pygame.event.get():
        if touch.handle(event, on_map, extra):
            continue  # (touch buttons post key events)
        if event.type == pygame.QUIT:
            running = False
        elif pause:
            pause.handle_event(event)
            if pause.done:
                if pause.quit and saves.WEB:  # a page can't close itself: back to the title screen
                    scene = Transition(scene, TitleScene(), flashes=0)
                elif pause.quit:
                    running = False
                if pause.loaded:
                    scene = Transition(scene, pause.loaded, flashes=0)
                pause = None
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and scene.pausable:
            pause = PauseMenu(scene.save_point(), scene.bag)
        elif (event.type == pygame.KEYDOWN and event.key in (pygame.K_i, pygame.K_q) and scene.touch_map
              and scene.save_point() is not None):  # the bag or the quest log, straight from a map
            pause = PauseMenu(scene.save_point(), scene.bag)
            pause.open_bag() if event.key == pygame.K_i else pause.open_quests()
        else:
            scene.handle_event(event)
    for pos, drag in touch.taps():
        if not pause:
            scene.tap(pos, drag)

    if not pause:
        scene.update(dt)
    scene.draw(canvas)
    pygame.transform.scale(canvas, settings.WINDOW_SIZE, window)
    scene.draw_overlay(window)
    if saves.recently_autosaved():
        ui.text(window, "Autosaved", (settings.LOGICAL_SIZE[0] - 6, settings.LOGICAL_SIZE[1] - 14), ui.GREY,
                size=20, align="right")
    if pause:
        pause.draw_overlay(window)
    on_map = pause.editing_controls if pause else scene.touch_map
    touch.draw(screen, on_map, pause.touch_keys if pause else scene.touch_keys)
    _show(screen)
    if saves.WEB:
        fit_canvas(pygame.display.get_surface().get_size())

    if scene.next_scene:
        previous, scene = scene, scene.next_scene
        previous.next_scene = None

    # The touch panels' width changed, or the phone turned upright or back.
    if screen.get_size() != touch.window_size() or touch.rotated != touch.portrait():
        screen, window = _make_window()
    return running, scene, pause, screen, window


if __name__ == "__main__":
    asyncio.run(main())
