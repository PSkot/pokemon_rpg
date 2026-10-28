"""Towns: flat, peaceful maps with buildings (no wild Pokémon). Doorways at
their edges lead onto routes. Arriving in a town heals the party (a
stand-in for Mom and Poké Centers).

Buildings are Pixellab sprites (see tileset.building). Poké Marts can be
entered (`Building.inside`, scenes/mart.py); going inside Poké Centers and
gyms comes later.
"""

import zlib
from dataclasses import dataclass

from .level import EMPTY, ROWS, SOLID, TILE, Level
from .themes import MEADOW, Theme

GROUND = 4  # tiles of ground


HOUSES, FUNCTIONAL = "houses.png", "functional_buildings.png"  # Pixellab sheets, 2×2 cells of 128×128


@dataclass(frozen=True)
class Building:
    name: str                 # shown when standing in front of it ("" = an unnamed house)
    sprite: tuple[str, int]   # (sheet, cell): see tileset.building
    col: int                  # left edge, in tiles
    # What Up there enters: "mart" (scenes/mart.py), "recruit" (a Recruitment
    # Center, scenes/recruit.py), or "" (nothing).
    inside: str = ""

    @property
    def x(self) -> int:
        return self.col * TILE


def building_mid(b: Building) -> float:
    """The x of a building's middle (where its door is)."""
    from .tileset import building  # (drawing: imported only when needed)
    return b.x + building(b.sprite)[0].get_width() / 2


@dataclass(frozen=True)
class Town:
    key: str
    name: str
    width: int                      # in tiles
    buildings: tuple[Building, ...]
    exits: tuple[tuple[str | int, str], ...]  # (where: "left"/"right" edge or a column, route key)
    home_col: int                   # where a new game starts and a fainted party wakes up
    board_col: int | None = None    # where its quest board stands (see quests.py)
    theme: Theme = MEADOW           # tiles and background
    mart: tuple[str, ...] = ()      # what its Poké Mart sells (medicine names)

    def exit_to(self, route: str) -> str | int:
        """Where the exit onto `route` is ("left", "right" or a column)."""
        return next(where for where, r in self.exits if r == route)

    def level(self) -> Level:
        """The town's map: flat ground."""
        surface = [ROWS - GROUND] * self.width
        grid = [[SOLID if row >= surface[col] else EMPTY for col in range(self.width)] for row in range(ROWS)]
        return Level(self.theme, zlib.crc32(self.key.encode()), grid, surface)


TOWNS = {t.key: t for t in [
    Town("pallet", "Pallet Town", 50, (
        Building("Your House", (HOUSES, 0), 7),
        Building("Rival's House", (HOUSES, 1), 18),
        Building("Professor Oak's Lab", (FUNCTIONAL, 3), 29),
    ), exits=(("right", "route_1"),), home_col=10, board_col=15),
    Town("viridian", "Viridian City", 72, (
        Building("", (HOUSES, 2), 8),
        Building("Pokémon Center", (FUNCTIONAL, 0), 17),
        Building("Poké Mart", (FUNCTIONAL, 2), 30, inside="mart"),
        Building("Recruitment Center", (HOUSES, 3), 42, inside="recruit"),
        Building("Viridian Gym", (FUNCTIONAL, 1), 53),
    ), exits=(("left", "route_1"), ("right", "viridian_forest"), (39, "route_22")), home_col=21, board_col=50,
       mart=("Potion", "Antidote", "Paralyze Heal", "Burn Heal")),
    Town("pewter", "Pewter City", 72, (
        Building("", (HOUSES, 3), 7),
        Building("Pokémon Center", (FUNCTIONAL, 0), 19),
        Building("Poké Mart", (FUNCTIONAL, 2), 32, inside="mart"),
        Building("Pewter Gym", (FUNCTIONAL, 1), 45),
        Building("Recruitment Center", (HOUSES, 2), 58, inside="recruit"),
    ), exits=(("left", "viridian_forest"), ("right", "route_3")), home_col=23, board_col=15,
       mart=("Potion", "Super Potion", "Antidote", "Burn Heal", "Awakening", "Paralyze Heal")),
    # The Pokémon Center at the foot of Mt. Moon (Gen 1: on Route 4), where
    # Route 3 ends: the last stop before the cave.
    Town("mt_moon", "Mt. Moon Pokémon Center", 44, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 18),
    ), exits=(("left", "route_3"), ("right", "mt_moon_cave")), home_col=14),
    # Route 4, out of Mt. Moon's far side. Cerulean City comes later.
    Town("route_4", "Route 4", 40, (), exits=(("left", "mt_moon_cave"),), home_col=8),
]}
