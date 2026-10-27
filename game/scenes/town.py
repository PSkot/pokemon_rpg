"""A town's map: buildings to walk past, a quest board, and doorways onto
routes (Up).

Arriving heals the party, and the town becomes where a fainted party wakes
up. The town's name shows for a moment on arrival. Up at the quest board
opens it; Up at a building a quest step needs does that step, and Up at a
Poké Mart goes inside (mart.py); a route's doorway can stay shut until a
quest is started or done.
"""

import pygame

from .. import saves, settings
from ..engine import ui
from ..engine.scene import Transition
from ..world import tileset
from ..world import quests
from ..world.instance import ROUTES, Instance
from ..world.level import TILE
from ..world.progress import Game
from ..world.towns import Building, Town, building_mid
from . import quest_ui
from .mart import MartScene
from .overworld import Doorway, MapScene, OverworldScene

BANNER_TIME = 2.5   # seconds the town's name shows on arrival
ARRIVE_GAP = 3 * TILE  # how far from the doorway the player arrives


class TownScene(MapScene):
    in_town = True
    def __init__(self, game: Game, town: Town, arrive: str = "home"):
        """`arrive`: "home" (a new game, or after fainting), the key of
        the route the player came back by (they arrive at its doorway), or
        the name of a building they came out of (no banner then)."""
        super().__init__(game, town.level())
        self.town = town
        game.town = town.key
        self.healed = game.heal()
        level, palette = self.level, self.level.theme.palette
        ground = level.ground_y(0)
        # (doorway, route key, where: "left"/"right" edge or a column)
        self.doors = [(Doorway(self._door_x(where), ground, palette), route, where) for where, route in town.exits]
        out_of = next((b for b in town.buildings if b.name == arrive), None)
        if arrive == "home":
            self.place_player(town.home_col * TILE + TILE / 2, 1)
        elif out_of:
            self.place_player(building_mid(out_of), 1)
            self.t = BANNER_TIME
        else:
            where = town.exit_to(arrive)
            if where == "left":
                self.place_player(level.entry_x + ARRIVE_GAP, 1)
            elif where == "right":
                self.place_player(level.exit_x - ARRIVE_GAP, -1)
            else:  # a doorway in the town: right in front of it
                self.place_player(self._door_x(where), 1)
        self.show_event(quests.reach(game, town.key))

    def _door_x(self, where: str | int) -> float:
        if where == "left":
            return self.level.entry_x
        if where == "right":
            return self.level.exit_x
        return where * TILE + TILE / 2

    def where(self) -> str:
        return self.town.name

    def _door_at_player(self) -> tuple[Doorway, str, str | int] | None:
        """(doorway, route key, where) of the doorway the player stands in."""
        return next((d for d in self.doors if self.player.body_rect.colliderect(d[0].rect)), None)

    @property
    def board_x(self) -> float | None:
        return None if self.town.board_col is None else self.town.board_col * TILE + TILE / 2

    def _at_board(self) -> bool:
        return self.board_x is not None and abs(self.player.x - self.board_x) < 24

    def _building_at_player(self) -> Building | None:
        return next((b for b in self.town.buildings
                     if b.name and b.x <= self.player.x < b.x + tileset.building(b.sprite)[0].get_width()), None)

    def interact(self) -> None:
        if self._at_board():
            board = quest_ui.QuestBoard(self.game, self.town.name, self.town.key)
            self.show(board, after=lambda: board.taken and self.show_event(quests.accept(self.game, board.taken)))
            return
        door = self._door_at_player()
        if door and not quests.open_for(self.game, ROUTES[door[1]].needs):
            self.show(quest_ui.Dialogue([("", ROUTES[door[1]].blocked)]))
            return
        building = None if door else self._building_at_player()
        if building and building.inside == "mart":
            self.next_scene = Transition(self, MartScene(self.game, self.town), flashes=0)
            return
        if building:
            event = quests.visit(self.game, self.town.key, building.name)
            if event:
                self.show_event(event)
                saves.autosave(self)
            return
        if door:
            route = ROUTES[door[1]]
            instance = Instance(route, route.other_end(self.town.key))
            first_map = OverworldScene(instance, self.game)
            saves.autosave(first_map)
            self.next_scene = Transition(self, first_map, flashes=0)

    def prompt(self) -> tuple[float, float] | None:
        if self._at_board():
            return self.board_x, self.level.ground_y(0) - 74
        door = self._door_at_player()
        if door:
            return door[0].x, door[0].feet_y - 66
        building = self._building_at_player()
        if building and building.inside:  # it can be entered
            return building_mid(building), self.level.ground_y(0) - 60
        return None

    def markers(self) -> list[tuple[float, float]]:
        ground, marks = self.level.ground_y(0), []
        if self.board_x is not None and quests.can_take(self.game, self.town.key):
            marks.append((self.board_x, ground - 60))
        for quest in quests.active(self.game):
            step = quests.current(self.game, quest.key)
            if step.kind == "visit" and step.town == self.town.key:
                for b in self.town.buildings:
                    if b.name == step.target:
                        marks.append((building_mid(b), ground - tileset.building(b.sprite)[1] - 20))
        return marks

    def draw_things(self, layer: pygame.Surface) -> None:
        ground = round(self.level.ground_y(0))
        for b in self.town.buildings:
            tileset.draw_building(layer, b.sprite, b.x, ground)
        if self.board_x is not None:
            tileset.quest_board(layer, round(self.board_x), ground, len(quests.can_take(self.game, self.town.key)))
        for door, _, _ in self.doors:
            door.draw(layer)
        for side in ("left", "right"):
            if all(where != side for _, _, where in self.doors):  # the town ends here (for now)
                x = TILE if side == "left" else self.level.width - 5 * TILE
                tileset.fence(layer, x, ground, 4 * TILE)

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        door = self._door_at_player()
        if door and not isinstance(door[2], str) and not self.panel:  # a doorway in the town: where it leads
            ui.text(window, ROUTES[door[1]].name, (door[0].x - self.camera, door[0].rect.top - 16), ui.WHITE,
                    size=26, align="center")
        building = None if door else self._building_at_player()
        if building and not self.panel:  # its name, over the roof
            image, base = tileset.building(building.sprite)
            top = self.level.ground_y(0) - base - 16
            ui.text(window, building.name, (building.x + image.get_width() / 2 - self.camera, top), ui.WHITE, size=26,
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
