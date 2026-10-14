"""The player character."""

from dataclasses import dataclass

import pygame

from . import settings
from .animation import Animation, load_sheet

WALK_SPEED = 70   # logical pixels per second
RUN_SPEED = 150
# Sink the sprite this many pixels into the ground: the sheet is drawn at a
# slight 3/4 angle, so the background legs end ~2px above the near feet and would
# otherwise hover over the grass.
FOOT_SINK = 3

# Jumping. Full jump height = JUMP_VELOCITY**2 / (2 * GRAVITY) ≈ 50 px.
GRAVITY = 1100          # px/s²
JUMP_VELOCITY = 330     # px/s upwards at take-off
JUMP_CUT_GRAVITY = 3.0  # gravity multiplier while rising with Space released (short hops)
JUMP_SQUAT = 0.05       # seconds crouched on the ground before leaving it
LAND_TIME = 0.10        # seconds the landing frame is held

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
    attack: bool = False     # True only on the frame the button is pressed


class Player:
    def __init__(self, x: float):
        rows = load_sheet(settings.ASSETS / "sprites" / "pixellab" / "bulbasaur.png", 64, 64)
        walk, run, jump, attack = rows
        self.anims = {
            "idle": Animation(walk[:1], fps=1),
            "walk": Animation(walk, fps=8),
            "run": Animation(run, fps=12),
            "jump": Animation(jump, fps=1, loop=False, per_frame_baseline=True),
            "attack": Animation(attack, fps=8, loop=False),
        }
        self.x = x                    # centre of the sprite
        self.feet_y = float(settings.GROUND_Y)
        self.vy = 0.0                 # vertical speed, positive = down
        self.facing = 1               # 1 = right, -1 = left
        self.state = "idle"           # idle, walk, run, attack, squat, air, land
        self.state_time = 0.0

    # ------------------------------------------------------------------ state

    @property
    def anim_name(self) -> str:
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

    def update(self, dt: float, c: Controls) -> None:
        self.state_time += dt

        if self.state == "attack":
            if not self.anim.finished(self.state_time):
                return  # rooted in place until the attack ends
            self.set_state("idle")

        if self.on_ground and self.state != "squat":
            if c.attack:
                self.set_state("attack")
                return
            if c.jump:
                self.set_state("squat")

        self._move_horizontally(dt, c)

        if self.state == "squat" and self.state_time >= JUMP_SQUAT:
            self.vy = -JUMP_VELOCITY
            self.set_state("air")

        if self.state == "air":
            gravity = GRAVITY
            if self.vy < 0 and not c.jump_held:
                gravity *= JUMP_CUT_GRAVITY
            self.vy += gravity * dt
            self.feet_y += self.vy * dt
            if self.feet_y >= settings.GROUND_Y:
                self.feet_y = float(settings.GROUND_Y)
                self.vy = 0.0
                self.set_state("land")
            return

        if self.state in ("squat", "land"):
            if self.state == "land" and self.state_time >= LAND_TIME:
                self.set_state("idle")
            else:
                return

        moving = c.left != c.right
        self.set_state(("run" if c.run else "walk") if moving else "idle")

    def _move_horizontally(self, dt: float, c: Controls) -> None:
        direction = int(c.right) - int(c.left)
        if not direction:
            return
        self.facing = direction
        speed = RUN_SPEED if c.run else WALK_SPEED
        half = 20  # keep the body on screen
        self.x = max(half, min(settings.LOGICAL_SIZE[0] - half, self.x + direction * speed * dt))

    # ------------------------------------------------------------------- draw

    def draw(self, surface: pygame.Surface, debug: bool = False) -> None:
        anim, i = self.anim, self.frame_index
        frame = anim.frame(i, flip=self.facing < 0)
        top_left = (round(self.x - frame.get_width() / 2),
                    round(self.feet_y + FOOT_SINK - anim.baselines[i]))
        surface.blit(frame, top_left)
        if debug:
            box = frame.get_rect(topleft=top_left)
            pygame.draw.rect(surface, (255, 0, 255), box, 1)
            body = frame.get_bounding_rect().move(top_left)
            pygame.draw.rect(surface, (255, 255, 0), body, 1)
            pygame.draw.circle(surface, (255, 0, 0), (round(self.x), round(self.feet_y)), 2)
