"""Dungeon instances: a run through several generated maps of one theme.

Each run has its own seed, so replaying a dungeon gives new maps. The last
map ends with a boss group guarding the way out.
"""

import random
from dataclasses import dataclass, field

from .items import Bag
from .level import Level, generate
from .pokemon import Monster
from .themes import Theme

MAPS = (3, 5)  # maps per instance


@dataclass
class Instance:
    theme: Theme
    party: list[Monster]
    bag: Bag
    seed: int = field(default_factory=lambda: random.randrange(1 << 30))
    index: int = 0      # the map the player is on

    def __post_init__(self):
        self.maps = random.Random(self.seed).randint(*MAPS)

    @property
    def final(self) -> bool:
        return self.index == self.maps - 1

    def level(self) -> Level:
        """The current map (the same one every time for the same run and index)."""
        return generate(self.theme, self.seed * 101 + self.index, final=self.final)
