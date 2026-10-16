"""Instances: runs through several generated maps of one theme.

A route between two towns (Route 1, ...) is an instance: each trip along it
has its own seed, so it's new every time, and its last doorway leads into
the town at the other end. An instance with a boss ends in an arena where a
boss group guards the way out.
"""

import random
from dataclasses import dataclass, field

from ..mechanics.loot import COMMON_ONLY, EARLY_BOSS, Rarities
from .level import Level, generate
from .themes import FOREST, MEADOW, Theme


@dataclass(frozen=True)
class Route:
    key: str
    name: str
    theme: Theme
    maps: int
    towns: tuple[str, str]  # the town keys at either end
    boss: bool = False
    loot: Rarities = COMMON_ONLY        # gear rarities from wild Pokémon and chests
    boss_loot: Rarities = EARLY_BOSS    # ... from a boss group and its chest
    # The boss group (species, level), its leader first; () = 4-5 random
    # Pokémon from the pool.
    boss_group: tuple[tuple[str, int], ...] = ()
    boss_scale: int = 1                 # the leader is drawn this many times bigger

    def other_end(self, town: str) -> str:
        return self.towns[1] if town == self.towns[0] else self.towns[0]


ROUTES = {r.key: r for r in [
    Route("route_1", "Route 1", MEADOW, maps=2, towns=("pallet", "viridian")),
    Route("viridian_forest", "Viridian Forest", FOREST, maps=3, towns=("viridian", "pewter"), boss=True,
          boss_group=(("caterpie", 10), ("metapod", 8), ("kakuna", 8)), boss_scale=2),
]}


@dataclass
class Instance:
    route: Route
    destination: str  # the town the last map's doorway leads into
    seed: int = field(default_factory=lambda: random.randrange(1 << 30))
    index: int = 0    # the map the player is on

    @property
    def theme(self) -> Theme:
        return self.route.theme

    @property
    def maps(self) -> int:
        return self.route.maps

    @property
    def final(self) -> bool:
        return self.index == self.maps - 1

    def level(self) -> Level:
        """The current map (the same one every time for the same run and index)."""
        level = generate(self.theme, self.seed * 101 + self.index, final=self.final and self.route.boss)
        if level.boss and self.route.boss_group:
            level.boss.encounter = list(self.route.boss_group)
        return level
