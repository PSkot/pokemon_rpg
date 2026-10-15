"""Entry point: window and game loop.

    python -m game

The game starts at the title screen (continue, load or start a new game).
A new game starts in Pallet Town; doorways at a town's edges lead onto
routes (Route 1 to Viridian City). On the maps: Left/Right walk,
hold Shift to run, Space jumps (hold for a higher jump), Up opens chests
and goes through doorways, Tab opens the party screen, F1 toggles debug
boxes. Walk into wild Pokémon to battle them. Esc pauses (resume, save,
load or quit). Battles, chests, fainting and leaving a map autosave.
"""

import pygame

from . import saves, settings
from .engine import ui
from .engine.scene import Scene, Transition
from .scenes.pause import PauseMenu
from .scenes.title import TitleScene


def main() -> None:
    pygame.init()
    window = pygame.display.set_mode(settings.WINDOW_SIZE)
    pygame.display.set_caption(settings.TITLE)
    canvas = pygame.Surface(settings.LOGICAL_SIZE)
    clock = pygame.time.Clock()

    scene: Scene = TitleScene()

    pause: PauseMenu | None = None

    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000
        for event in pygame.event.get():
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
        pygame.display.flip()

        if scene.next_scene:
            previous, scene = scene, scene.next_scene
            previous.next_scene = None

    pygame.quit()


if __name__ == "__main__":
    main()
