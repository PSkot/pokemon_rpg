"""Towns: flat, peaceful maps with buildings (no wild Pokémon). Doorways at
their edges lead onto routes. Arriving in a town heals the party (a
stand-in for Mom and Poké Centers).

Buildings are scenery for now: shops, Poké Centers and gyms come later.
"""

import zlib
from dataclasses import dataclass

from .level import EMPTY, ROWS, SOLID, TILE, Level
from .themes import MEADOW, Theme

GROUND = 4  # tiles of ground


@dataclass(frozen=True)
class Building:
    name: str   # shown when standing in front of it ("" = an unnamed house)
    kind: str   # how it's drawn: "house", "lab", "center", "mart" or "gym" (see tileset.draw_building)
    col: int    # left edge, in tiles
    width: int  # in tiles
    roof: tuple[int, int, int] | None = None  # a house's roof colour (None: the kind's own)

    @property
    def x(self) -> int:
        return self.col * TILE

    @property
    def w(self) -> int:
        return self.width * TILE


@dataclass(frozen=True)
class Town:
    key: str
    name: str
    width: int                      # in tiles
    buildings: tuple[Building, ...]
    exits: tuple[tuple[str, str], ...]  # (side "left"/"right", route key)
    home_col: int                   # where a new game starts and a fainted party wakes up
    theme: Theme = MEADOW           # tiles and background

    def exit_to(self, route: str) -> str:
        """The side the exit onto `route` is on."""
        return next(side for side, r in self.exits if r == route)

    def level(self) -> Level:
        """The town's map: flat ground."""
        surface = [ROWS - GROUND] * self.width
        grid = [[SOLID if row >= surface[col] else EMPTY for col in range(self.width)] for row in range(ROWS)]
        return Level(self.theme, zlib.crc32(self.key.encode()), grid, surface)


TOWNS = {t.key: t for t in [
    Town("pallet", "Pallet Town", 50, (
        Building("Your House", "house", 7, 7),
        Building("Rival's House", "house", 18, 7, roof=(72, 104, 176)),
        Building("Professor Oak's Lab", "lab", 29, 11),
    ), exits=(("right", "route_1"),), home_col=10),
    Town("viridian", "Viridian City", 72, (
        Building("", "house", 8, 6, roof=(120, 152, 88)),
        Building("Pokémon Center", "center", 17, 9),
        Building("Poké Mart", "mart", 30, 8),
        Building("", "house", 42, 6),
        Building("Viridian Gym", "gym", 53, 12),
    ), exits=(("left", "route_1"),), home_col=21),
]}
