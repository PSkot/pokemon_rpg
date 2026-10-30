"""Towns: flat, peaceful maps with buildings (no wild Pokémon). Doorways at
their edges lead onto routes. Arriving in a town heals the party (a
stand-in for Mom and Poké Centers).

Buildings are Pixellab sprites (see tileset.building). Poké Marts can be
entered (`Building.inside`, scenes/mart.py); going inside Poké Centers and
gyms comes later. Townsfolk (`Folk`, Pokémon living there) can be talked to:
they chat, and give and move on quests (quests.talk).
"""

import zlib
from dataclasses import dataclass

from ..mechanics.pokemon import EVOLUTIONS, SPECIES
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


ELDER = "elder"  # a Folk's species: the last form of the player's starter's line


@dataclass(frozen=True)
class Folk:
    """Someone living in a town: a Pokémon standing at `col`. Up next to
    them talks: a quest step or a quest they give (quests.talk), else the
    next of their `lines`."""
    key: str     # unique in the game (quest steps "talk" name it; Quest.giver)
    name: str    # shown over them when near; "{}" = their species' name ("Old {}")
    species: str  # their look (its idle animation), or ELDER
    col: int
    # Chat, one line per talk in turn; "{partner}" = the player's starter's name.
    lines: tuple[str, ...] = ()

    @property
    def x(self) -> float:
        return self.col * TILE + TILE / 2

    def species_for(self, starter: str) -> str:
        if self.species != ELDER:
            return self.species
        species = starter
        while species in EVOLUTIONS and EVOLUTIONS[species].into in SPECIES:
            species = EVOLUTIONS[species].into
        return species

    def name_for(self, starter: str) -> str:
        return self.name.format(SPECIES[self.species_for(starter)].name)


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
    folk: tuple[Folk, ...] = ()     # who lives there (between the buildings)

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
    ), exits=(("right", "route_1"),), home_col=10, board_col=15,
       folk=(Folk("pallet_pidgey", "Pidgey", "pidgey", 41, (
           "Coo! Professor Oak's lab is just up the road.",
           "Route 1 is to the east. The grass there is full of Pidgey like me!",
       )),)),
    Town("viridian", "Viridian City", 72, (
        Building("", (HOUSES, 2), 8),
        Building("Pokémon Center", (FUNCTIONAL, 0), 17),
        Building("Poké Mart", (FUNCTIONAL, 2), 30, inside="mart"),
        Building("Recruitment Center", (HOUSES, 3), 42, inside="recruit"),
        Building("Viridian Gym", (FUNCTIONAL, 1), 53),
    ), exits=(("left", "route_1"), ("right", "viridian_forest"), (39, "route_22")), home_col=21, board_col=50,
       mart=("Potion", "Antidote", "Paralyze Heal", "Burn Heal"),
       folk=(
           Folk("viridian_rattata", "Rattata", "rattata", 27, (
               "Squeak! The Recruitment Center up the road finds you new friends.",
               "Viridian Forest is to the east. Bugs everywhere. Yuck!",
           )),
           # The feud on Route 22: the Pidgey flock's leader and the Spearow's,
           # glaring at each other (quests feud_pidgey / feud_spearow).
           Folk("viridian_pidgeotto", "Pidgeotto", "pidgeotto", 62, (
               "The Spearow on Route 22 peck at my flock all day. Somebody should teach them manners.",
               "A Pidgey that stands up to those bullies grows strong. Strong enough to fly like me.",
           )),
           Folk("viridian_fearow", "Fearow", "fearow", 66, (
               "Hmph. The Pidgey think the sky belongs to them. My Spearow know better.",
               "A Spearow that wins its fights grows a long beak. Like mine.",
           )),
       )),
    Town("pewter", "Pewter City", 72, (
        Building("", (HOUSES, 3), 7),
        Building("Pokémon Center", (FUNCTIONAL, 0), 19),
        Building("Poké Mart", (FUNCTIONAL, 2), 32, inside="mart"),
        Building("Pewter Gym", (FUNCTIONAL, 1), 45),
        Building("Recruitment Center", (HOUSES, 2), 58, inside="recruit"),
    ), exits=(("left", "viridian_forest"), ("right", "route_3")), home_col=23, board_col=15,
       mart=("Potion", "Super Potion", "Escape Rope", "Antidote", "Burn Heal", "Awakening", "Paralyze Heal"),
       folk=(
           Folk("pewter_elder", "Old {}", ELDER, 29, (
               "I was young once, like your {partner}. Every Pokémon grows up in its own time.",
               "When your {partner} is strong enough (Lv16), come and see me. I'll show it the way.",
           )),
           Folk("pewter_geodude", "Geodude", "geodude", 55, (
               "Grr! The Boulder Gang runs the gym. Rock beats everything!",
               "Well... except Water and Grass. Don't tell anyone.",
           )),
       )),
    # The Pokémon Center at the foot of Mt. Moon (Gen 1: on Route 4), where
    # Route 3 ends: the last stop before the cave.
    Town("mt_moon", "Mt. Moon Pokémon Center", 44, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 18),
    ), exits=(("left", "route_3"), ("right", "mt_moon_cave")), home_col=14),
    # Route 4, out of Mt. Moon's far side. Cerulean City comes later.
    Town("route_4", "Route 4", 40, (), exits=(("left", "mt_moon_cave"),), home_col=8),
]}
