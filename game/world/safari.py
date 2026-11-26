"""The Safari Zone (Fuchsia City): a maze of maps, rerolled for every visit.

A visit has a seed; every map in it is worked out from the seed and the
path of doors taken to reach it (`Node`), so going back through a door
leads to the same map as before. Each map has a door back (at its left:
to the map it was reached from, or, from the first, out) and up to three
doors on:

- the **true path** is `TRUE_DEPTH` maps long: on each of its maps one door
  leads on along it (a clue points to it: Pokémon tracks or a signpost);
  its last map is the heart of the zone (HM03 Surf, the "Secret House");
- the other doors lead into **side branches** 1 or 2 maps long that end in
  **dead ends** (no doors on). No clues off the true path.

Depth is the number of doors passed, right or wrong; every `ZONE_MAPS` of it
the zone changes (its look, and which Pokémon live in its tall grass), so
the scenery never tells a right door from a wrong one. The deepest zone's
dead ends hold the Warden's Gold Teeth (the first one found in).

A visit costs `FEE` and lasts `STEPS` steps (one per tile walked).

**Kudos:** a wild Pokémon in the tall grass challenges the player to its
game (scenes/safari_games.py); the score earns Kudos with that species
(`KUDOS_RATE` per point, by game: a good game of either is worth about the
same). At `KUDOS_NEEDED` it joins (`Game.kudos`, saved: it can take several
visits), at its zone's level.
"""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field, replace

from .themes import FOREST, MEADOW, PoolEntry, Theme

FEE = 500
STEPS = 600
ZONE_MAPS = 3            # doors passed per zone
TRUE_DEPTH = 9           # the true path's maps after the first (3 zones of 3)
SIDE_LENGTH = (1, 2)     # a side branch's maps
GRASS_CHANCE = 0.08      # per step in tall grass: an encounter
GOLD_TEETH, SURF = "Gold Teeth", "HM03 Surf"
KUDOS_NEEDED = 100
KUDOS_RATE = {"egg_catch": 1.0, "fruit_slice": 0.6, "rodeo": 1.0, "pinch": 0.45,
              "wheres_baby": 1.0, "egg_pop": 0.75}  # Kudos per point of a game's score


@dataclass(frozen=True)
class Zone:
    name: str
    theme: Theme
    # (species, weight) met in its tall grass (only those with a Safari game;
    # Chansey is the rare one).
    grass: tuple[tuple[str, int], ...]
    level: int  # what joins from here joins at this level


ZONES = (
    Zone("Outer Grassland", replace(MEADOW, key="safari_1", name="Safari Zone",
                                    pool=(PoolEntry("tauros", 1, (30, 32)),)),
         (("tauros", 3), ("pinsir", 2), ("scyther", 2), ("exeggcute", 2)), 40),
    Zone("Deep Woods", replace(FOREST, key="safari_2", name="Safari Zone",
                               pool=(PoolEntry("pinsir", 1, (35, 38)),)),
         (("kangaskhan", 3), ("pinsir", 3), ("scyther", 2), ("tauros", 1), ("exeggcute", 1)), 43),
    Zone("Ancient Marsh", replace(MEADOW, key="safari_3", name="Safari Zone",
                                  pool=(PoolEntry("chansey", 1, (40, 44)),),
                                  sky=((40, 70, 64), (170, 190, 150)), tint=(150, 190, 160)),
         (("kangaskhan", 2), ("exeggcute", 2), ("scyther", 2), ("tauros", 1), ("pinsir", 1), ("chansey", 1)), 46),
)


def kudos_for(game_kind: str, score: int) -> int:
    """The Kudos a game's score earns."""
    return round(score * KUDOS_RATE[game_kind])


def joined(game, species: str) -> bool:
    return game.kudos.get(species, 0) >= KUDOS_NEEDED


def zone_of(depth: int) -> Zone:
    return ZONES[min(depth // ZONE_MAPS, len(ZONES) - 1)]


@dataclass(frozen=True)
class Node:
    """A map of the maze: where it is (`path`: the doors taken from the
    first map), whether it's on the true path, and its doors on (`doors`:
    how many, 0 for a dead end or the heart) and which of them is the true
    one (`true_door`, on the true path)."""
    path: tuple[int, ...]
    true: bool
    remaining: int          # a side branch: maps left after this one (0: a dead end)
    doors: int
    true_door: int | None
    clue: str               # "tracks", "sign" or "" (off the true path, or the heart)

    @property
    def depth(self) -> int:
        return len(self.path)

    @property
    def zone(self) -> Zone:
        return zone_of(self.depth)

    @property
    def heart(self) -> bool:
        """The true path's last map (HM03 Surf)."""
        return self.true and self.depth == TRUE_DEPTH

    @property
    def dead_end(self) -> bool:
        return not self.true and self.doors == 0


def _rng(seed: int, path: tuple[int, ...]) -> random.Random:
    return random.Random(zlib.crc32(f"safari/{seed}/{'-'.join(map(str, path))}".encode()))


def node(seed: int, path: tuple[int, ...]) -> Node:
    """The map at `path` in the visit with `seed` (the same every time)."""
    true, remaining = True, 0
    for i in range(len(path) + 1):
        here = path[:i]
        rng = _rng(seed, here)
        if true:
            if len(here) == TRUE_DEPTH:
                doors, true_door = 0, None
            else:
                doors, true_door = 3, rng.randrange(3)
            clue = rng.choice(("tracks", "tracks", "sign")) if true_door is not None else ""
        else:
            doors = 0 if remaining == 0 else rng.randint(1, 2)
            true_door, clue = None, ""
        if i == len(path):
            return Node(here, true, remaining, doors, true_door, clue)
        door = path[i]
        if true and door != true_door:  # off into a side branch
            true, remaining = False, rng.randint(*SIDE_LENGTH) - 1
        elif not true:
            remaining -= 1
    raise AssertionError("unreachable")


def sign_text(n: Node) -> str:
    """A signpost's riddle pointing at the true door (of three: first,
    middle, last), different ways for the same door."""
    rng = _rng(0, n.path + (99,))
    names = ("first", "middle", "last")
    t = n.true_door
    others = [names[i] for i in range(3) if i != t]
    return rng.choice((
        f"\"The way on is the {names[t]} door.\"",
        f"\"Not the {others[0]} door, nor the {others[1]}.\"",
        f"\"Ranger's note: the {names[t]} path is the one the Pokémon use.\"",
    ))


@dataclass
class Visit:
    """One trip into the Safari Zone: its maze (`seed`), where the player is
    (`path`), and the steps left."""
    seed: int = field(default_factory=lambda: random.randrange(1 << 30))
    path: tuple[int, ...] = ()
    steps: int = STEPS
    walked: float = 0.0  # px walked since the last whole step

    def here(self) -> Node:
        return node(self.seed, self.path)
