"""A town's map: buildings to walk past and doorways onto routes (Up).

Arriving heals the party, and the town becomes where a fainted party wakes
up. The town's name shows for a moment on arrival.
"""

import pygame

from .. import saves, settings
from ..engine import ui
from ..engine.scene import Transition
from ..world import tileset
from ..world.instance import ROUTES, Instance
from ..world.level import TILE
from ..world.progress import Game
from ..world.towns import Building, Town
from .overworld import Doorway, MapScene, OverworldScene

BANNER_TIME = 2.5   # seconds the town's name shows on arrival
ARRIVE_GAP = 3 * TILE  # how far from the doorway the player arrives


class TownScene(MapScene):
    in_town = True
    def __init__(self, game: Game, town: Town, arrive: str = "home"):
        """`arrive`: "home" (a new game, or after fainting), or the side
        ("left"/"right") of the doorway the player came in by."""
        super().__init__(game, town.level())
        self.town = town
        game.town = town.key
        self.healed = game.heal()
        level, palette = self.level, self.level.theme.palette
        ground = level.ground_y(0)
        self.doors = {side: (Doorway(level.entry_x if side == "left" else level.exit_x, ground, palette), route)
                      for side, route in town.exits}
        if arrive == "left":
            self.place_player(level.entry_x + ARRIVE_GAP, 1)
        elif arrive == "right":
            self.place_player(level.exit_x - ARRIVE_GAP, -1)
        else:
            self.place_player(town.home_col * TILE + TILE / 2, 1)

    def where(self) -> str:
        return self.town.name

    def _door_at_player(self) -> tuple[Doorway, str] | None:
        """(doorway, route key) of the doorway the player stands in."""
        return next((d for d in self.doors.values() if self.player.body_rect.colliderect(d[0].rect)), None)

    def _building_at_player(self) -> Building | None:
        return next((b for b in self.town.buildings if b.name and b.x <= self.player.x < b.x + b.w), None)

    def interact(self) -> None:
        door = self._door_at_player()
        if door:
            route = ROUTES[door[1]]
            instance = Instance(route, route.other_end(self.town.key))
            first_map = OverworldScene(instance, self.game)
            saves.autosave(first_map)
            self.next_scene = Transition(self, first_map, flashes=0)

    def prompt(self) -> tuple[float, float] | None:
        door = self._door_at_player()
        return (door[0].x, door[0].feet_y - 66) if door else None

    def draw_things(self, layer: pygame.Surface) -> None:
        ground = round(self.level.ground_y(0))
        for b in self.town.buildings:
            tileset.draw_building(layer, b.kind, b.x, ground, b.w, b.roof)
        for side in ("left", "right"):
            if side in self.doors:
                self.doors[side][0].draw(layer)
            else:  # the town ends here (for now)
                x = TILE if side == "left" else self.level.width - 5 * TILE
                tileset.fence(layer, x, ground, 4 * TILE)

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        building = self._building_at_player()
        if building and not self.panel:  # its name, over the roof
            wall_h, roof_h, *_ = tileset.BUILDINGS[building.kind]
            top = self.level.ground_y(0) - wall_h - roof_h - 30
            ui.text(window, building.name, (building.x + building.w / 2 - self.camera, top), ui.WHITE, size=26,
                    align="center")
        if self.t < BANNER_TIME:
            center = settings.LOGICAL_SIZE[0] / 2
            ui.text(window, self.town.name, (center, 60), ui.YELLOW, size=48, align="center")
            if self.healed:
                ui.text(window, "Your party is rested.", (center, 84), ui.WHITE, size=24, align="center")

    # ----------------------------------------------------------------- saves

    def location(self) -> dict:
        p = self.player
        return {"kind": "town", "town": self.town.key, "x": p.x, "facing": p.facing}

    def restore(self, state: dict) -> None:
        self.place_player(state["x"], state["facing"])
        self.t = BANNER_TIME  # no banner when loading
