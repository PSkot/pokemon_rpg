"""A map: a grid of tiles, randomly generated from a theme, plus what's on it.

The grid holds solid ground ("#"), one-way platforms ("=", you can jump up
through them and land on top) and empty space ("."). Positions are in
logical pixels; a tile is TILE px square. Maps scroll sideways and are one
screen high (the last row is partly below the screen).
"""

import math
import random
from dataclasses import dataclass, field

from .themes import Theme

TILE = 16
ROWS = 23

EMPTY, SOLID, PLATFORM = ".", "#", "="

# Generation.
WIDTH = (90, 120)          # map width in tiles
GROUND = (3, 8)            # ground height in tiles
FLAT_ENDS = 8              # flat tiles at the start and the end
ARENA = 20                 # flat tiles at the end of an instance's last map (the boss)
BOSS_SIZE = (4, 5)         # Pokémon in the boss group
PLATFORM_RISE = 3          # tiles above the highest ground under it (a full jump reaches ~3)
CLEARANCE = 10             # rows kept free between a cave's ceiling and the ground


@dataclass
class Spawn:
    """Wild Pokémon waiting on the map: the first one is shown, and touching
    it starts a battle against all of `encounter` [(species, level)]."""
    x: float
    feet_y: float
    encounter: list[tuple[str, int]]


@dataclass
class Level:
    theme: Theme
    seed: int
    grid: list[list[str]]                 # [row][col]
    surface: list[int]                    # per column: the row of the ground's top tile
    spawns: list[Spawn] = field(default_factory=list)
    chests: list[tuple[float, float]] = field(default_factory=list)  # (x, feet y)
    platforms: list[tuple[int, int, int]] = field(default_factory=list)  # (row, first col, last col)
    boss: Spawn | None = None  # the last map of an instance ends with a big group

    @property
    def cols(self) -> int:
        return len(self.grid[0])

    @property
    def width(self) -> int:
        return self.cols * TILE

    @property
    def entry_x(self) -> float:
        """The doorway the player comes in by."""
        return 2 * TILE

    @property
    def start_x(self) -> float:
        return 4 * TILE

    @property
    def exit_x(self) -> float:
        """The doorway on to the next map (or out, after the boss)."""
        return (self.cols - 3) * TILE

    @property
    def boss_chest_x(self) -> float:
        return (self.cols - 7) * TILE

    def ground_y(self, x: float) -> float:
        """The top of the ground at `x`."""
        return self.surface[min(self.cols - 1, max(0, int(x // TILE)))] * TILE

    # ------------------------------------------------------------- collision

    def tile(self, col: int, row: int) -> str:
        if col < 0 or col >= self.cols or row >= ROWS:
            return SOLID  # walls at the ends, and below the map
        if row < 0:
            return EMPTY
        return self.grid[row][col]

    @staticmethod
    def _cols(left: float, right: float) -> range:
        return range(math.floor(left / TILE), math.floor((right - 0.001) / TILE) + 1)

    def hits_solid(self, left: float, top: float, right: float, bottom: float) -> bool:
        """Whether the box overlaps any solid tile (platforms don't count)."""
        rows = range(math.floor(top / TILE), math.floor((bottom - 0.001) / TILE) + 1)
        return any(self.tile(c, r) == SOLID for c in self._cols(left, right) for r in rows)

    def supported(self, left: float, right: float, feet: float) -> bool:
        """Whether something stands on a tile top at `feet`."""
        row = round(feet / TILE)
        if abs(feet - row * TILE) > 0.01:
            return False
        return any(self.tile(c, row) != EMPTY for c in self._cols(left, right))

    def landing(self, left: float, right: float, old_feet: float, new_feet: float) -> float | None:
        """Falling from `old_feet` to `new_feet`: the first tile top crossed
        (ground or platform), or None."""
        for row in range(math.ceil(old_feet / TILE - 0.001), math.floor(new_feet / TILE) + 1):
            if any(self.tile(c, row) != EMPTY for c in self._cols(left, right)):
                return row * TILE
        return None


def _walk(rng: random.Random, cols: int, low: int, high: int, start: int, flat_start: int,
          flat_end: int) -> list[int]:
    """A height per column: flat ends, and in between flat stretches that
    step up or down by up to 2."""
    heights, h = [start] * flat_start, start
    while len(heights) < cols - flat_end:
        h = max(low, min(high, h + rng.choice((-2, -1, -1, 0, 1, 1, 2))))
        heights += [h] * rng.randint(5, 12)
    heights = heights[:cols - flat_end]
    return heights + [heights[-1]] * flat_end


def _pick(rng: random.Random, weighted):
    """One item of `weighted`, a sequence of (item, weight)."""
    return rng.choices([i for i, _ in weighted], weights=[w for _, w in weighted])[0]


def encounter(theme: Theme, rng: random.Random) -> list[tuple[str, int]]:
    """A random group of wild Pokémon from the theme's pool."""
    size = _pick(rng, theme.group_sizes)
    entries = [_pick(rng, [(e, e.weight) for e in theme.pool]) for _ in range(size)]
    return [(e.species, rng.randint(*e.levels)) for e in entries]


def boss_encounter(theme: Theme, rng: random.Random) -> list[tuple[str, int]]:
    """A big group from the theme's pool, at the pool's usual levels."""
    entries = [_pick(rng, [(e, e.weight) for e in theme.pool]) for _ in range(rng.randint(*BOSS_SIZE))]
    return [(e.species, rng.randint(*e.levels)) for e in entries]


def generate(theme: Theme, seed: int, final: bool = False) -> Level:
    """A map. The `final` one of an instance ends in an arena with a boss group."""
    rng = random.Random(seed)
    cols = rng.randint(*WIDTH)
    end = ARENA if final else FLAT_ENDS
    if final:
        cols += ARENA - FLAT_ENDS
    heights = _walk(rng, cols, *GROUND, start=4, flat_start=FLAT_ENDS, flat_end=end)
    surface = [ROWS - h for h in heights]
    grid = [[SOLID if row >= surface[col] else EMPTY for col in range(cols)] for row in range(ROWS)]

    ceiling = [0] * cols
    if theme.ceiling:
        ceiling = _walk(rng, cols, 1, 3, start=1, flat_start=0, flat_end=0)
        for col in range(cols):
            ceiling[col] = min(ceiling[col], surface[col] - CLEARANCE)
            for row in range(ceiling[col]):
                grid[row][col] = SOLID

    level = Level(theme, seed, grid, surface)

    # One-way platforms, a full jump above the highest ground beneath them.
    col = FLAT_ENDS + 4
    while col < cols - end - 6:
        length = rng.randint(3, 6)
        span = range(col, col + length)
        row = min(surface[c] for c in span) - PLATFORM_RISE
        if rng.random() < 0.6 and row - max(ceiling[c] for c in span) >= 4:
            for c in span:
                grid[row][c] = PLATFORM
            level.platforms.append((row, span.start, span.stop - 1))
        col += length + rng.randint(4, 10)

    # Wild Pokémon, spread out along the ground.
    col = FLAT_ENDS + rng.randint(4, 8)
    while col < cols - end:
        x = col * TILE + TILE / 2
        level.spawns.append(Spawn(x, surface[col] * TILE, encounter(theme, rng)))
        col += rng.randint(9, 16)

    # Chests: on platforms when there are some (a reward for the climb).
    for _ in range(rng.randint(1, 2)):
        if level.platforms and rng.random() < 0.8:
            row, first, last = rng.choice(level.platforms)
            spot = ((first + last + 1) / 2 * TILE, row * TILE)
        else:
            c = rng.randint(FLAT_ENDS, cols - end)
            spot = (c * TILE + TILE / 2, surface[c] * TILE)
        if spot not in level.chests:
            level.chests.append(spot)

    if final:
        x = (cols - 12) * TILE
        level.boss = Spawn(x, surface[cols - 12] * TILE, boss_encounter(theme, rng))
    return level
