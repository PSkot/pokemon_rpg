"""Scenes (map, battle, ...) and the transition between them."""

import pygame


class Scene:
    """One screen of the game. The main loop runs whichever scene is active.

    A scene switches to another by setting `next_scene`; the main loop picks
    it up at the end of the frame.
    """

    next_scene: "Scene | None" = None
    pausable = True  # Esc opens the pause menu (else the scene gets the key)
    bag = None       # the player's bag, if the scene has one (dev mode adds items to it)
    in_town = False  # skill points can be reset here
    touch_map = False  # show the map's touch buttons (Run; see touch.py)
    touch_keys: tuple[tuple[int, str], ...] = ()  # extra touch buttons: (key, label)s

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, canvas: pygame.Surface) -> None:
        """Draw at the logical resolution."""

    def draw_overlay(self, window: pygame.Surface) -> None:
        """Draw on the scaled window, after `draw` (crisp text goes here)."""

    def save_point(self):
        """The map scene to save the game from (see saves.py), or None if
        the game can't be saved right now (e.g. in a battle)."""
        return None


class Transition(Scene):
    """Flash the old scene, close it behind blinds, then open them on the new one.

    Neither scene is updated meanwhile, so both stay frozen.
    """

    FLASH = 0.08   # seconds per flash half (on, then off)
    CLOSE = 0.35   # seconds for the blinds to close (and again to open)
    BLINDS = 12

    def __init__(self, old: Scene, new: Scene, flashes: int = 3):
        self.old, self.new = old, new
        self.flash_time = flashes * 2 * self.FLASH
        self.t = 0.0

    @property
    def showing_new(self) -> bool:
        return self.t >= self.flash_time + self.CLOSE

    def update(self, dt: float) -> None:
        self.t += dt
        if self.t >= self.flash_time + 2 * self.CLOSE:
            self.next_scene = self.new

    def draw(self, canvas: pygame.Surface) -> None:
        (self.new if self.showing_new else self.old).draw(canvas)

    def draw_overlay(self, window: pygame.Surface) -> None:
        (self.new if self.showing_new else self.old).draw_overlay(window)
        if self.t < self.flash_time:
            if int(self.t / self.FLASH) % 2 == 0:
                flash = pygame.Surface(window.get_size())
                flash.fill((255, 255, 255))
                flash.set_alpha(200)
                window.blit(flash, (0, 0))
            return
        t = self.t - self.flash_time
        closed = t / self.CLOSE if t < self.CLOSE else 2 - t / self.CLOSE  # 0 → 1 → 0
        band = window.get_height() / self.BLINDS
        h = band * min(1.0, closed)
        for i in range(self.BLINDS):
            mid = (i + 0.5) * band
            pygame.draw.rect(window, (0, 0, 0), (0, round(mid - h / 2), window.get_width(), round(h) + 1))

