"""The player character: walking, running and jumping around a map's tiles."""

from dataclasses import dataclass

import pygame

from ..engine import hats
from ..engine.animation import Animation
from ..mechanics.pokemon import SPECIES, Monster, Species, animations
from .level import TILE, Level

WALK_SPEED = 70   # logical pixels per second
RUN_SPEED = 150
# Sink the sprite this many pixels into the ground: the sheet is drawn at a
# slight 3/4 angle, so the background legs end ~2px above the near feet and would
# otherwise hover over the grass.
FOOT_SINK = 3

# Jumping. Full jump height = JUMP_VELOCITY**2 / (2 * GRAVITY) ≈ 62 px: just under
# 4 tiles, so platforms 3 tiles up are comfortably in reach.
GRAVITY = 1100          # px/s²
JUMP_VELOCITY = 370     # px/s upwards at take-off
JUMP_CUT_GRAVITY = 3.0  # gravity multiplier while rising with Space released (short hops)
JUMP_SQUAT = 0.05       # seconds crouched on the ground before leaving it
LAND_TIME = 0.10        # seconds the landing frame is held

# The box that collides with the map's tiles: a fixed size, so the
# animation frames don't change what fits where.
HITBOX_HALF_W = 11
HITBOX_H = 30

# Jump sheet row: crouch, leap (rising), airborne (falling), landing.
JUMP_CROUCH, JUMP_RISE, JUMP_FALL, JUMP_LAND = range(4)

@dataclass
class Controls:
    """One frame of player input, decoupled from the keyboard."""
    left: bool = False
    right: bool = False
    run: bool = False
    jump: bool = False       # True only on the frame the button is pressed
    jump_held: bool = False
    attack: int = 0          # attack key (1-9) pressed this frame, 0 = none


class Player:
    def __init__(self, x: float, feet_y: float, species: Species = SPECIES["bulbasaur"]):
        self.species = species
        self.anims = animations(species)
        self.x = x                    # centre of the sprite
        self.feet_y = float(feet_y)
        self.vy = 0.0                 # vertical speed, positive = down
        self.facing = 1               # 1 = right, -1 = left
        self.state = "idle"           # idle, walk, run, attack, squat, air, land
        self.state_time = 0.0
        self.attacks = ["attack"]     # animation per attack key (1 = basic attack, 2-5 = equipped moves)
        self.attack = "attack"        # animation of the current/last attack

    def become(self, species: Species, attacks: list[str] | None = None) -> None:
        """Look like `species` (the lead Pokémon, e.g. after it evolves),
        with `attacks` as the animations for keys 1, 2, ..."""
        if species != self.species:
            self.species, self.anims = species, animations(species)
        if attacks:
            self.attacks = attacks

    # ------------------------------------------------------------------ state

    @property
    def anim_name(self) -> str:
        if self.state == "attack":  # its basic attack if it doesn't have this one
            return self.attack if self.attack in self.anims else "attack"
        return "jump" if self.state in ("squat", "air", "land") else self.state

    @property
    def anim(self) -> Animation:
        return self.anims[self.anim_name]

    @property
    def frame_index(self) -> int:
        """Jump frames follow the jump's phase; everything else plays on a timer."""
        if self.state == "squat":
            return JUMP_CROUCH
        if self.state == "air":
            return JUMP_RISE if self.vy < 0 else JUMP_FALL
        if self.state == "land":
            return JUMP_LAND
        return self.anim.index_at(self.state_time)

    @property
    def on_ground(self) -> bool:
        return self.state != "air"

    def set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.state_time = 0.0

    # ----------------------------------------------------------------- update

    def update(self, dt: float, c: Controls, level: Level) -> None:
        self.state_time += dt

        if self.state == "attack":
            if not self.anim.finished(self.state_time):
                return  # rooted in place until the attack ends
            self.set_state("idle")

        if self.on_ground and self.state != "squat":
            if 1 <= c.attack <= len(self.attacks):
                self.attack = self.attacks[c.attack - 1]
                self.set_state("attack")
                return
            if c.jump:
                self.set_state("squat")

        self._move_horizontally(dt, c, level)

        if self.state == "squat" and self.state_time >= JUMP_SQUAT:
            self.vy = -JUMP_VELOCITY
            self.set_state("air")
        elif self.on_ground and not level.supported(*self._span(), self.feet_y):
            self.vy = 0.0  # walked off a ledge
            self.set_state("air")

        if self.state == "air":
            self._fall(dt, c, level)
            return

        if self.state in ("squat", "land"):
            if self.state == "land" and self.state_time >= LAND_TIME:
                self.set_state("idle")
            else:
                return

        moving = c.left != c.right
        self.set_state(("run" if c.run else "walk") if moving else "idle")

    def _span(self, x: float | None = None) -> tuple[float, float]:
        """Left and right edge of the hitbox (at `x`, or where it is now)."""
        x = self.x if x is None else x
        return x - HITBOX_HALF_W, x + HITBOX_HALF_W

    def _move_horizontally(self, dt: float, c: Controls, level: Level) -> None:
        direction = int(c.right) - int(c.left)
        if not direction:
            return
        self.facing = direction
        speed = RUN_SPEED if c.run else WALK_SPEED
        x = self.x + direction * speed * dt
        left, right = self._span(x)
        if level.hits_solid(left, self.feet_y - HITBOX_H, right, self.feet_y):
            # Stop against the wall: flush with the tile edge.
            if direction > 0:
                x = (right // TILE) * TILE - HITBOX_HALF_W
            else:
                x = (left // TILE + 1) * TILE + HITBOX_HALF_W
            left, right = self._span(x)
            if level.hits_solid(left, self.feet_y - HITBOX_H, right, self.feet_y):
                return
        self.x = x

    def _fall(self, dt: float, c: Controls, level: Level) -> None:
        """In the air: gravity, landing on ground or platforms, bumping the ceiling."""
        gravity = GRAVITY
        if self.vy < 0 and not c.jump_held:
            gravity *= JUMP_CUT_GRAVITY
        self.vy += gravity * dt
        feet = self.feet_y + self.vy * dt
        left, right = self._span()
        if self.vy > 0:
            ground = level.landing(left, right, self.feet_y, feet)
            if ground is not None:
                self.feet_y, self.vy = ground, 0.0
                self.set_state("land")
                return
        elif level.hits_solid(left, feet - HITBOX_H, right, feet):
            # Head against the ceiling: stop rising just below it.
            feet = (int((feet - HITBOX_H) // TILE) + 1) * TILE + HITBOX_H
            self.vy = 0.0
        self.feet_y = feet

    # ------------------------------------------------------------------- draw

    @property
    def body_rect(self) -> pygame.Rect:
        """The opaque part of the current frame, for collisions."""
        return self.anim.body_rect(self.frame_index, self.x, self.feet_y + FOOT_SINK, self.facing < 0)

    def draw(self, surface: pygame.Surface, debug: bool = False, monster: Monster | None = None) -> None:
        """Draw the player; `monster` is the Pokémon it is (for its hat)."""
        anim, i, flip = self.anim, self.frame_index, self.facing < 0
        box = anim.place(i, self.x, self.feet_y + FOOT_SINK, flip)
        surface.blit(anim.frame(i, flip), box)
        if monster:
            hats.draw_worn(surface, monster, anim, i, box, flip)
        if debug:
            pygame.draw.rect(surface, (255, 0, 255), box, 1)
            pygame.draw.rect(surface, (255, 255, 0), self.body_rect, 1)
            pygame.draw.circle(surface, (255, 0, 0), (round(self.x), round(self.feet_y)), 2)
