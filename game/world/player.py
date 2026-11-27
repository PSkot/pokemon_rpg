"""The player character: walking, running and jumping around a map's tiles."""

import math
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

# Skating (a theme with `skate`: the skate road): the player rides a board,
# with momentum. Left/Right push (Shift: harder), letting go keeps rolling,
# slowing to a drift downhill (to the right); pushing against the roll
# brakes. Drawn SKATE_LIFT px up, on a board (`tileset.SKATEBOARDS`).
SKATE_SPEED = 190       # px/s, pushing
SKATE_RUN_SPEED = 250   # ... with Shift
SKATE_PUSH = 320        # px/s² towards that speed
SKATE_BRAKE = 520       # px/s² pushing against the roll
SKATE_DRIFT = 45        # px/s: letting go, the board keeps rolling downhill at least this fast
SKATE_FRICTION = 70     # px/s² slowing down to the drift
SKATE_LIFT = 9          # px: the deck's height over the ground
SKATE_KICK = 0.9        # a 1-tile step up is a ramp: it launches the board up at this × its speed (px/s)
SKATE_KICK_MAX = 330    # ... at most

# Surfing (on a water map's water, world/hms.py): the Water Pokémon
# carrying the player swims along the surface (as fast as walking and
# running), sunk SURF_SINK px into it and bobbing SURF_BOB px; it can jump
# from the water as from the ground.
SURF_BOB = 1.5
SURF_BOB_SPEED = 4.0  # radians per second

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
    carried: float = 0.0     # px/s: carried along (a spinner pad), in the idle pose, instead of walking


class Player:
    def __init__(self, x: float, feet_y: float, species: Species = SPECIES["bulbasaur"]):
        self.species = species
        self.anims = animations(species)
        self.x = x                    # centre of the sprite
        self.feet_y = float(feet_y)
        self.vy = 0.0                 # vertical speed, positive = down
        self.facing = 1               # 1 = right, -1 = left
        self.state = "idle"           # idle, walk, run, squat, air, land
        self.state_time = 0.0
        self.skating = False          # on a board (the skate road): momentum, `vx`
        self.vx = 0.0                 # skating: horizontal speed, positive = right
        self.board = 0                # skating: which board (`tileset.SKATEBOARDS` row)
        self.surfing = False          # on the water (a water map): swimming
        self.t = 0.0                  # seconds on the map (the swimmer's bobbing)

    def become(self, species: Species) -> None:
        """Look like `species` (the lead Pokémon, e.g. after it evolves)."""
        if species != self.species:
            self.species, self.anims = species, animations(species)

    # ------------------------------------------------------------------ state

    @property
    def anim_name(self) -> str:
        return "jump" if self.state in ("squat", "air", "land") else self.state

    @property
    def anim(self) -> Animation:
        # (Placeholder icons only have idle/walk: they use those.)
        return self.anims.get(self.anim_name) or self.anims["walk" if self.state == "run" else "idle"]

    @property
    def frame_index(self) -> int:
        """Jump frames follow the jump's phase; everything else plays on a timer."""
        last = len(self.anim.frames) - 1  # (placeholders have a single frame)
        if self.state == "squat":
            return min(JUMP_CROUCH, last)
        if self.state == "air":
            return min(JUMP_RISE if self.vy < 0 else JUMP_FALL, last)
        if self.state == "land":
            return min(JUMP_LAND, last)
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
        self.t += dt
        self._update(dt, c, level)
        self.surfing = (self.on_ground and level.water_at(self.x)
                        and abs(self.feet_y - level.ground_y(self.x)) < 0.5)

    def _update(self, dt: float, c: Controls, level: Level) -> None:

        if self.on_ground and self.state != "squat" and c.jump:
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

        moving = c.left != c.right and not c.carried
        if self.skating:  # (riding: standing on the board, whatever the speed)
            moving = False
        self.set_state(("run" if c.run else "walk") if moving else "idle")

    def _span(self, x: float | None = None) -> tuple[float, float]:
        """Left and right edge of the hitbox (at `x`, or where it is now)."""
        x = self.x if x is None else x
        return x - HITBOX_HALF_W, x + HITBOX_HALF_W

    def _skate(self, dt: float, c: Controls) -> float:
        """The board's speed this frame (see SKATE_SPEED ...)."""
        push = int(c.right) - int(c.left)
        if push:
            top = push * (SKATE_RUN_SPEED if c.run else SKATE_SPEED)
            rate = SKATE_BRAKE if self.vx * push < 0 else SKATE_PUSH
            self.vx = min(top, self.vx + rate * dt) if top > self.vx else max(top, self.vx - rate * dt)
        elif self.on_ground:  # rolling on, slowing to the drift downhill
            if self.vx > SKATE_DRIFT:
                self.vx = max(SKATE_DRIFT, self.vx - SKATE_FRICTION * dt)
            else:
                self.vx = min(SKATE_DRIFT, self.vx + SKATE_PUSH * dt)
        if abs(self.vx) > 1:
            self.facing = 1 if self.vx > 0 else -1
        return self.vx

    def _move_horizontally(self, dt: float, c: Controls, level: Level) -> None:
        if self.skating:
            speed = self._skate(dt, c)
            direction = (speed > 0) - (speed < 0)
            if not direction:
                return
            x = self.x + speed * dt
            left, right = self._span(x)
            if level.hits_solid(left, self.feet_y - HITBOX_H, right, self.feet_y):
                up = self.feet_y - TILE  # a step of one tile: a ramp, up and over it
                if self.on_ground and not level.hits_solid(left, up - HITBOX_H, right, up - 0.01):
                    self.x, self.feet_y = x, up
                    self.vy = -min(SKATE_KICK_MAX, abs(self.vx) * SKATE_KICK)
                    self.set_state("air")
                    return
                self.vx = 0.0  # (into a higher step: stopped dead)
                x = (right // TILE) * TILE - HITBOX_HALF_W if direction > 0 else (left // TILE + 1) * TILE + HITBOX_HALF_W
                left, right = self._span(x)
                if level.hits_solid(left, self.feet_y - HITBOX_H, right, self.feet_y):
                    return
            self.x = x
            return
        direction = int(c.right) - int(c.left)
        if not direction:
            return
        self.facing = direction
        speed = c.carried or (RUN_SPEED if c.run else WALK_SPEED)
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
        lift = SKATE_LIFT if self.skating else 0
        if self.surfing:
            from .water import SURF_SINK  # (drawing only)
            lift = -SURF_SINK + round(SURF_BOB * math.sin(self.t * SURF_BOB_SPEED))
        box = anim.place(i, self.x, self.feet_y + FOOT_SINK - lift, flip)
        if self.skating:
            from .tileset import draw_skateboard  # (drawing only)
            draw_skateboard(surface, self.board, self.x, self.feet_y, flip)
        surface.blit(anim.frame(i, flip), box)
        if monster:
            hats.draw_worn(surface, monster, anim, i, box, flip)
        if debug:
            pygame.draw.rect(surface, (255, 0, 255), box, 1)
            pygame.draw.rect(surface, (255, 255, 0), self.body_rect, 1)
            pygame.draw.circle(surface, (255, 0, 0), (round(self.x), round(self.feet_y)), 2)
