"""Inside a Recruitment Center: a one-screen room with the recruitment
board, and Mr. Mime beside it.

Up at the board opens it (`RecruitBoard`): every recruitable line, locked
until enough of it are defeated (`Recruit.needed`), then open; Enter takes
its recruitment quest and goes straight to its map (a route full of that
Pokémon, with a giant one as the boss: beating it makes it join). Up at Mr.
Mime: a word from him, then the team (`TeamPanel`: swap Pokémon between the
party and the reserve). Up at the door goes back out. Saving here saves
the player outside, at the door.
"""

import zlib

import pygame

from .. import saves, settings
from ..engine import ui
from ..engine.scene import Transition
from ..mechanics.pokemon import SPECIES, animations
from ..world import quests, tileset
from ..world.instance import RECRUIT_BUILDING, RECRUITS, ROUTES, Instance
from ..world.level import EMPTY, ROWS, SOLID, Level
from ..world.progress import MAX_PARTY, Game
from ..world.quests import QUESTS
from ..world.towns import Town, building_mid
from . import quest_ui
from .overworld import MapScene, OverworldScene

COLS = 40            # one screen wide
GROUND = 4           # tiles of floor
BOARD = pygame.Rect(70, 150, 200, 110)  # the cork board on the wall (it stands on short legs)
MIME_X = 320         # Mr. Mime, beside the board
MIME_FPS = 6        # Mr. Mime's idle animation
DOOR_X = 592
REACH = 26
PIN_SIZE = 0.55      # the open recruitments' icons pinned on the board

LOCKED_COLOR = (150, 150, 165)
NEW_COLOR = (120, 200, 255)
DONE_COLOR = (120, 230, 120)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE)

MIME_LINES = [
    ("Mr. Mime", "Mime! Mime mime!"),
    ("", "Mr. Mime points at the board: Pokémon you've beaten often enough may want to join you."),
    ("", "He mimes a big wall, then a door. He can swap your party with the Pokémon waiting here."),
]


def _level(town: Town) -> Level:
    surface = [ROWS - GROUND] * COLS
    grid = [[SOLID if row >= surface[col] else EMPTY for col in range(COLS)] for row in range(ROWS)]
    return Level(town.theme, zlib.crc32(f"{town.key} recruit".encode()), grid, surface)


def _quest(species: str):
    return QUESTS[f"recruit_{species}"]


def _still(species: str) -> pygame.Surface:
    """A species' standing pose (its sheet's or its placeholder icon's)."""
    return animations(SPECIES[species])["idle"].frame(0, False)


class RecruitScene(MapScene):
    in_town = True

    def __init__(self, game: Game, town: Town):
        super().__init__(game, _level(town))
        self.town = town
        self.ground = round(self.level.ground_y(0))
        self.tiles = pygame.Surface((1, 1), pygame.SRCALPHA)  # the floor is part of the room
        room = tileset.mart_room(self.level.width, self.ground, [], DOOR_X, tileset.CENTER_WALLS,
                                 tileset.CENTER_TRIM)
        tileset.recruit_board(room, BOARD)
        self.backgrounds = [(room, 0.0)]
        self.mime_frames = tileset.npc_frames("mr_mime")
        self.place_player(DOOR_X - 36, -1)

    def where(self) -> str:
        return f"{self.town.name} {RECRUIT_BUILDING}"

    def location(self) -> dict:
        """Saved as standing outside, at the door."""
        building = next(b for b in self.town.buildings if b.inside == "recruit")
        return {"kind": "town", "town": self.town.key, "x": building_mid(building), "facing": 1}

    def _at_board(self) -> bool:
        return BOARD.left - 10 < self.player.x < BOARD.right + 10

    def _at_mime(self) -> bool:
        return abs(self.player.x - MIME_X) < REACH

    def _at_door(self) -> bool:
        return abs(self.player.x - DOOR_X) < REACH

    @property
    def mime(self) -> pygame.Surface:
        return self.mime_frames[int(self.t * MIME_FPS) % len(self.mime_frames)]

    @property
    def _mime_top(self) -> float:
        return self.ground - self.mime.get_height()

    def interact(self) -> None:
        if self._at_board():
            board = RecruitBoard(self.game)
            self.show(board, after=lambda: board.chosen and self._go(board.chosen))
        elif self._at_mime():
            self.show(quest_ui.Dialogue(list(MIME_LINES)))
            self.show(TeamPanel(self.game))
        elif self._at_door():
            from .town import TownScene  # (town.py enters this scene)
            self.next_scene = Transition(self, TownScene(self.game, self.town, arrive=RECRUIT_BUILDING), flashes=0)

    def _go(self, species: str) -> None:
        """Take the recruitment quest (if not yet) and walk to its map."""
        quest = _quest(species)
        if quests.ready(self.game, quest):
            quests.accept(self.game, quest.key)
        first_map = OverworldScene(Instance(ROUTES[RECRUITS[species].route_key], self.town.key), self.game)
        saves.autosave(first_map)
        self.next_scene = Transition(self, first_map)

    def prompt(self) -> tuple[float, float] | None:
        if self._at_board():
            return BOARD.centerx, BOARD.top - 12
        if self._at_mime():
            return MIME_X, self._mime_top - 12
        if self._at_door():
            return DOOR_X, self.ground - 84
        return None

    def markers(self) -> list[tuple[float, float]]:
        open_ = any(quests.ready(self.game, _quest(s)) for s in RECRUITS)
        return [(BOARD.centerx, BOARD.top - 2)] if open_ else []

    def draw_things(self, layer: pygame.Surface) -> None:
        # The open (and taken) recruitments, pinned on the board.
        pinned = [s for s in RECRUITS if quests.ready(self.game, _quest(s)) or quests.is_active(self.game, _quest(s).key)]
        for i, species in enumerate(pinned[:10]):
            icon = pygame.transform.smoothscale_by(_still(species), PIN_SIZE)
            x = BOARD.x + 14 + (i % 5) * 36
            y = BOARD.y + 12 + (i // 5) * 46
            layer.blit(icon, (x + 14 - icon.get_width() // 2, y + 38 - icon.get_height()))
            pygame.draw.circle(layer, (210, 60, 60), (x + 14, y + 2), 2)  # a pin
        layer.blit(self.mime, (MIME_X - self.mime.get_width() // 2, self._mime_top))

    def draw_overlay(self, window: pygame.Surface) -> None:
        if not self.panel:
            ui.text(window, "RECRUITMENT", (BOARD.centerx, BOARD.top - 26), ui.SHADOW, size=26, align="center",
                    shadow=False)
        super().draw_overlay(window)


class RecruitBoard:
    """The recruitment board: every recruitable line (locked with its count,
    open, taken, or recruited). Enter on an open or taken one sets `chosen`
    (the species; the scene takes the quest and goes there)."""

    RECT = pygame.Rect(30, 40, 580, 290)
    LIST_W = 210
    ROW_H = 16
    PAD = 9

    def __init__(self, game: Game):
        self.game = game
        self.species = list(RECRUITS)
        self.choice = 0
        self.chosen: str | None = None

    def _state(self, species: str) -> tuple[str, tuple]:
        quest = _quest(species)
        if quests.is_done(self.game, quest.key):
            return "Recruited", DONE_COLOR
        if quests.is_active(self.game, quest.key):
            return "Taken", ui.YELLOW
        if quests.ready(self.game, quest):
            return "Open", NEW_COLOR
        return f"{self.game.defeated[species]}/{RECRUITS[species].needed}", LOCKED_COLOR

    def handle_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.species)
        elif key in CONFIRM_KEYS:
            species = self.species[self.choice]
            if self._state(species)[0] in ("Open", "Taken"):
                self.chosen = species
                return True
        elif key in BACK_KEYS:
            return True
        return False

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        ui.cursor(canvas, self.RECT.x + 14, self.RECT.y + self.PAD + 24 + self.choice * self.ROW_H + 5)
        species = self.species[self.choice]
        icon = _still(species)
        right = pygame.Rect(self.RECT.x + self.LIST_W + 20, self.RECT.y + 30, 60, 50)
        canvas.blit(icon, (right.centerx - icon.get_width() // 2, right.bottom - icon.get_height()))

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        ui.text(window, "Recruitment board", (r.x + 12, r.y + self.PAD), ui.YELLOW)
        for i, species in enumerate(self.species):
            y = r.y + self.PAD + 24 + i * self.ROW_H
            state, color = self._state(species)
            ui.text(window, SPECIES[species].name, (r.x + 20, y), ui.YELLOW if i == self.choice else ui.WHITE, size=24)
            ui.text(window, state, (r.x + self.LIST_W, y + 2), color, size=20, align="right")
        s = settings.SCALE
        x0 = r.x + self.LIST_W + 12
        pygame.draw.line(window, ui.GREY, ((x0 - 4) * s, (r.y + 28) * s), ((x0 - 4) * s, (r.bottom - 12) * s))
        species = self.species[self.choice]
        recruit, quest = RECRUITS[species], _quest(species)
        state, color = self._state(species)
        x, y, width = x0 + 80, r.y + 34, r.right - x0 - 92
        ui.text(window, SPECIES[species].name, (x, y), ui.WHITE)
        y += 18
        if state == "Recruited":
            line = "Recruited!"
        elif state in ("Open", "Taken"):
            line = "Open: it's waiting for you." if state == "Open" else "Taken: on to its grounds!"
        else:
            line = "Locked"
        ui.text(window, line, (x, y), color, size=22)
        y = r.y + 96
        x, width = x0, r.right - x0 - 12
        for part in ui.wrap(quest.summary, 22, width):
            ui.text(window, part, (x, y), size=22)
            y += 13
        y += 6
        needed = (f"Needs {recruit.needed} of its line defeated (any of {SPECIES[species].name}'s "
                  f"evolutions count): {min(self.game.defeated[species], recruit.needed)}/{recruit.needed}")
        for part in ui.wrap(needed, 20, width):
            ui.text(window, part, (x, y), DONE_COLOR if self.game.defeated[species] >= recruit.needed else ui.GREY,
                    size=20)
            y += 12
        y += 4
        route = ROUTES[recruit.route_key]
        ui.text(window, f"Map: {route.name}, Lv{recruit.level - 2}-{recruit.level}; boss Lv{recruit.boss_level}",
                (x, y), ui.GREY, size=20)
        y += 14
        for part in ui.wrap(f"Rewards: {quests.reward_text(quest)}", 20, width):
            ui.text(window, part, (x, y), ui.YELLOW, size=20)
            y += 12
        hint = "Enter: go there   X: close" if state in ("Open", "Taken") else "X: close"
        ui.text(window, hint, (r.right - 12, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")


class TeamPanel:
    """The team (from Mr. Mime): the party's slots, then the reserve. Enter
    picks a Pokémon (or an empty slot), Enter on another swaps the two
    (or moves it there). The party keeps at least one Pokémon; the first is
    the one on the map."""

    RECT = pygame.Rect(150, 40, 340, 290)
    ROW_H = 17
    PAD = 9
    VISIBLE = 11  # rows that fit (it scrolls)

    def __init__(self, game: Game):
        self.game = game
        self.choice = 0
        self.picked: tuple[str, int] | None = None
        self.top = 0
        self.message = "Enter: pick, then Enter on another to swap."

    def _slots(self) -> list[tuple[str, int]]:
        """("party", i) for each party slot, then ("reserve", j) for each
        reserve Pokémon and one empty spot after them."""
        return [("party", i) for i in range(MAX_PARTY)] + [("reserve", j) for j in range(len(self.game.reserve) + 1)]

    def _get(self, slot: tuple[str, int]):
        group = self.game.party if slot[0] == "party" else self.game.reserve
        return group[slot[1]] if slot[1] < len(group) else None

    def _swap(self, a: tuple[str, int], b: tuple[str, int]) -> str:
        party = list(self.game.party) + [None] * (MAX_PARTY - len(self.game.party))
        reserve = list(self.game.reserve) + [None]
        groups = {"party": party, "reserve": reserve}
        groups[a[0]][a[1]], groups[b[0]][b[1]] = groups[b[0]][b[1]], groups[a[0]][a[1]]
        new_party = [m for m in party if m]
        if not new_party:
            return "The party can't be empty."
        self.game.party[:] = new_party  # (in place: the scenes hold this list)
        self.game.reserve[:] = [m for m in reserve if m]
        return "Swapped."

    def handle_key(self, key: int) -> bool:
        slots = self._slots()
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(slots)
            self.top = max(0, min(self.choice, max(self.top, self.choice - self.VISIBLE + 1)))
        elif key in CONFIRM_KEYS:
            slot = slots[self.choice]
            if self.picked is None:
                if self._get(slot):
                    self.picked = slot
                    self.message = f"Swap {self._get(slot).name} with...?"
                else:
                    self.message = "Pick a Pokémon first."
            else:
                self.message = self._swap(self.picked, slot) if slot != self.picked else "Enter: pick, then Enter on another to swap."
                self.picked = None
                self.choice = min(self.choice, len(self._slots()) - 1)
        elif key in BACK_KEYS:
            if self.picked is not None:
                self.picked, self.message = None, "Enter: pick, then Enter on another to swap."
            else:
                return True
        return False

    def _row_y(self, i: int) -> int:
        """A row's y (the reserve's rows sit under its heading)."""
        gap = 18 if i >= MAX_PARTY else 0
        return self.RECT.y + self.PAD + 54 + (i - self.top) * self.ROW_H + gap

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.RECT)
        if self.top <= self.choice < self.top + self.VISIBLE:
            ui.cursor(canvas, self.RECT.x + 14, self._row_y(self.choice) + 5)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.RECT
        ui.text(window, "Team", (r.x + 12, r.y + self.PAD), ui.YELLOW)
        ui.text(window, self.message, (r.x + 12, r.y + self.PAD + 18), ui.GREY, size=20)
        slots = self._slots()
        for i, slot in enumerate(slots):
            if not self.top <= i < self.top + self.VISIBLE:
                continue
            y = self._row_y(i)
            if i == MAX_PARTY and self.top <= MAX_PARTY:
                ui.text(window, f"Reserve ({len(self.game.reserve)})", (r.x + 12, y - 16), ui.GREY, size=20)
            if i == 0:
                ui.text(window, f"Party ({len(self.game.party)}/{MAX_PARTY})", (r.x + 12, y - 16), ui.GREY, size=20)
            m = self._get(slot)
            color = (ui.YELLOW if slot == self.picked else ui.WHITE if m else ui.GREY)
            if m:
                ui.text(window, m.name, (r.x + 22, y), color, size=24)
                ui.text(window, f"Lv{m.level}   {m.hp}/{m.max_hp}", (r.right - 12, y + 2), ui.GREY, size=20,
                        align="right")
                if slot == ("party", 0):
                    ui.text(window, "lead", (r.x + 22 + ui.font(24).size(m.name)[0] / settings.SCALE + 8, y + 2),
                            DONE_COLOR, size=18)
            else:
                ui.text(window, "- empty -", (r.x + 22, y), color, size=22)
        ui.text(window, "X: close", (r.right - 12, r.bottom - self.PAD - 9), ui.GREY, size=20, align="right")
