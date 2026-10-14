"""The map: the player walks around; touching a wild Pokémon starts a battle."""

import pygame

from . import settings
from .battle import BattleScene
from .player import Controls, Player
from .pokemon import SPECIES, Monster, animations
from .scene import Scene, Transition

HELP = "Left/Right: walk   Shift: run   Space: jump (hold = higher)   1-5: attack   F1: debug   Esc: quit"


class WildPokemon:
    """A Pokémon standing still on the map. Touching it starts a battle
    against `encounter`: a list of (species, level)."""

    def __init__(self, species: str, x: float, encounter: list[tuple[str, int]]):
        self.species = SPECIES[species]
        self.anim = animations(self.species)["idle"]
        self.x = x
        self.feet_y = settings.GROUND_Y + self.species.foot_sink
        self.encounter = encounter
        self.facing = -1
        # Only trigger once per touch, so returning from a battle while still
        # touching it doesn't start another one straight away.
        self.armed = True

    @property
    def body_rect(self) -> pygame.Rect:
        return self.anim.body_rect(0, self.x, self.feet_y, self.facing < 0)

    def draw(self, surface: pygame.Surface, debug: bool = False) -> None:
        flip = self.facing < 0
        surface.blit(self.anim.frame(0, flip), self.anim.place(0, self.x, self.feet_y, flip))
        if debug:
            pygame.draw.rect(surface, (255, 255, 0), self.body_rect, 1)


def draw_world(surface: pygame.Surface) -> None:
    w, h = settings.LOGICAL_SIZE
    surface.fill(settings.SKY_COLOR)
    pygame.draw.rect(surface, settings.GROUND_COLOR, (0, settings.GROUND_Y, w, h - settings.GROUND_Y))
    pygame.draw.rect(surface, settings.GRASS_COLOR, (0, settings.GROUND_Y, w, 4))


class OverworldScene(Scene):
    def __init__(self):
        self.player = Player(x=settings.LOGICAL_SIZE[0] / 2)
        self.party = [Monster.create("bulbasaur", 5)]
        self.wild = [WildPokemon("pidgey", x=500, encounter=[("pidgey", 3)])]
        self.debug = False
        self.jump = False
        self.attack = 0
        self.font = pygame.font.Font(None, 24)
        self.fps = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_SPACE:
            self.jump = True
        elif pygame.K_1 <= event.key <= pygame.K_9:
            self.attack = event.key - pygame.K_0
        elif event.key == pygame.K_F1:
            self.debug = not self.debug

    def update(self, dt: float) -> None:
        self.fps = 1 / dt if dt else 0.0
        keys = pygame.key.get_pressed()
        self.player.update(dt, Controls(
            left=keys[pygame.K_LEFT],
            right=keys[pygame.K_RIGHT],
            run=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            jump=self.jump,
            jump_held=keys[pygame.K_SPACE],
            attack=self.attack,
        ))
        self.jump, self.attack = False, 0

        for wild in self.wild:
            wild.facing = 1 if self.player.x > wild.x else -1
            touching = self.player.body_rect.colliderect(wild.body_rect)
            if touching and wild.armed:
                enemies = [Monster.create(species, level) for species, level in wild.encounter]
                self.next_scene = Transition(self, BattleScene(self, self.party, enemies))
            wild.armed = not touching

    def draw(self, canvas: pygame.Surface) -> None:
        draw_world(canvas)
        for wild in self.wild:
            wild.draw(canvas, self.debug)
        self.player.draw(canvas, self.debug)

    def draw_overlay(self, window: pygame.Surface) -> None:
        p = self.player
        lines = [
            HELP,
            f"state: {p.state}   animation: {p.anim_name}   "
            f"frame: {p.frame_index + 1}/{len(p.anim.frames)}   "
            f"facing: {'right' if p.facing > 0 else 'left'}   fps: {self.fps:.0f}",
        ]
        for i, text in enumerate(lines):
            window.blit(self.font.render(text, True, (20, 24, 32)), (12, 10 + i * 22))
