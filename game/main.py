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

import pygame

from . import saves, settings
from .engine import touch, ui
from .engine.scene import Scene, Transition
from .scenes.pause import PauseMenu
from .scenes.title import TitleScene


def fit_canvas() -> None:
    """In the browser: make the page's canvas as big as fits, in the game's
    shape. (pygbag sizes it once, before the window exists, so it comes out
    square; this also follows the page's size, e.g. when a phone turns.)"""
    import platform  # pygbag's: gives access to the page (`window`)
    window = platform.window
    w, h = settings.WINDOW_SIZE
    scale = min(window.innerWidth / w, window.innerHeight / h)
    width, height = f"{int(w * scale)}px", f"{int(h * scale)}px"
    style = window.canvas.style
    if style.width != width or style.height != height:
        style.width, style.height = width, height
        style.imageRendering = "pixelated"


async def main() -> None:
    pygame.init()
    window = pygame.display.set_mode(settings.WINDOW_SIZE)
    pygame.display.set_caption(settings.TITLE)
    canvas = pygame.Surface(settings.LOGICAL_SIZE)
    clock = pygame.time.Clock()

    touch.init()
    scene: Scene = TitleScene()

    pause: PauseMenu | None = None

    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000
        for event in pygame.event.get():
            if touch.handle(event, scene.touch_map and not pause, () if pause else scene.touch_keys):
                continue  # (touch buttons post key events)
            if event.type == pygame.QUIT:
                running = False
            elif pause:
                pause.handle_event(event)
                if pause.done:
                    running = not pause.quit
                    if pause.loaded:
                        scene = Transition(scene, pause.loaded, flashes=0)
                    pause = None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and scene.pausable:
                pause = PauseMenu(scene.save_point(), scene.bag)
            else:
                scene.handle_event(event)

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
        touch.draw(window, scene.touch_map and not pause, () if pause else scene.touch_keys)
        pygame.display.flip()
        if saves.WEB:
            fit_canvas()

        if scene.next_scene:
            previous, scene = scene, scene.next_scene
            previous.next_scene = None

        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
