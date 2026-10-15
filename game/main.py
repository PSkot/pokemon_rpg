"""Entry point: window and game loop.

    python -m game

The game starts at the hub: pick a dungeon. On its maps: Left/Right walk,
hold Shift to run, Space jumps (hold for a higher jump), Up opens chests
and goes through doorways, Tab opens the party screen, F1 toggles debug
boxes. Walk into wild Pokémon to battle them. Esc pauses (resume or quit).
"""

import pygame

from . import settings
from .hub import HubScene
from .overworld import new_game
from .pause import PauseMenu
from .scene import Scene


def main() -> None:
    pygame.init()
    window = pygame.display.set_mode(settings.WINDOW_SIZE)
    pygame.display.set_caption(settings.TITLE)
    canvas = pygame.Surface(settings.LOGICAL_SIZE)
    clock = pygame.time.Clock()

    scene: Scene = HubScene(*new_game())

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
                    pause = None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pause = PauseMenu()
            else:
                scene.handle_event(event)

        if not pause:
            scene.update(dt)
        scene.draw(canvas)
        pygame.transform.scale(canvas, settings.WINDOW_SIZE, window)
        scene.draw_overlay(window)
        if pause:
            pause.draw_overlay(window)
        pygame.display.flip()

        if scene.next_scene:
            previous, scene = scene, scene.next_scene
            previous.next_scene = None

    pygame.quit()


if __name__ == "__main__":
    main()
