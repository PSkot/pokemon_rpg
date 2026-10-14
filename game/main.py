"""Entry point: a test scene for the player's animations.

    python -m game

Controls: Left/Right walk, hold Shift to run, Space jumps (hold for a
higher jump), 1 attacks, F1 toggles debug boxes, Esc quits.
"""

import pygame

from . import settings
from .player import Controls, Player

HELP = "Left/Right: walk   Shift: run   Space: jump (hold = higher)   1: attack   F1: debug   Esc: quit"


def draw_world(surface: pygame.Surface) -> None:
    w, h = settings.LOGICAL_SIZE
    surface.fill(settings.SKY_COLOR)
    pygame.draw.rect(surface, settings.GROUND_COLOR, (0, settings.GROUND_Y, w, h - settings.GROUND_Y))
    pygame.draw.rect(surface, settings.GRASS_COLOR, (0, settings.GROUND_Y, w, 4))


def draw_hud(window: pygame.Surface, font: pygame.font.Font, player: Player, fps: float) -> None:
    lines = [
        HELP,
        f"state: {player.state}   animation: {player.anim_name}   "
        f"frame: {player.frame_index + 1}/{len(player.anim.frames)}   "
        f"facing: {'right' if player.facing > 0 else 'left'}   fps: {fps:.0f}",
    ]
    for i, text in enumerate(lines):
        window.blit(font.render(text, True, (20, 24, 32)), (12, 10 + i * 22))


def main() -> None:
    pygame.init()
    window = pygame.display.set_mode(settings.WINDOW_SIZE)
    pygame.display.set_caption(settings.TITLE)
    canvas = pygame.Surface(settings.LOGICAL_SIZE)
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    player = Player(x=settings.LOGICAL_SIZE[0] / 2)
    debug = False

    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000
        attack = jump = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    jump = True
                elif event.key == pygame.K_1:
                    attack = True
                elif event.key == pygame.K_F1:
                    debug = not debug

        keys = pygame.key.get_pressed()
        player.update(dt, Controls(
            left=keys[pygame.K_LEFT],
            right=keys[pygame.K_RIGHT],
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=jump,
            jump_held=keys[pygame.K_SPACE],
            attack=attack,
        ))

        draw_world(canvas)
        player.draw(canvas, debug)
        pygame.transform.scale(canvas, settings.WINDOW_SIZE, window)
        draw_hud(window, font, player, clock.get_fps())
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
