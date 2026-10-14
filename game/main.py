"""Entry point: window and game loop.

    python -m game

Controls (map): Left/Right walk, hold Shift to run, Space jumps (hold for a
higher jump), 1-5 attack, F1 toggles debug boxes. Walk into the Pidgey to
start a battle. Esc quits.
"""

import pygame

from . import settings
from .overworld import OverworldScene
from .scene import Scene


def main() -> None:
    pygame.init()
    window = pygame.display.set_mode(settings.WINDOW_SIZE)
    pygame.display.set_caption(settings.TITLE)
    canvas = pygame.Surface(settings.LOGICAL_SIZE)
    clock = pygame.time.Clock()

    scene: Scene = OverworldScene()

    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            else:
                scene.handle_event(event)

        scene.update(dt)
        scene.draw(canvas)
        pygame.transform.scale(canvas, settings.WINDOW_SIZE, window)
        scene.draw_overlay(window)
        pygame.display.flip()

        if scene.next_scene:
            previous, scene = scene, scene.next_scene
            previous.next_scene = None

    pygame.quit()


if __name__ == "__main__":
    main()
