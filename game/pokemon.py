"""Pokémon species and individual Pokémon (party members and enemies)."""

from dataclasses import dataclass
from functools import cache

from . import settings
from .animation import Animation, load_sheet


@dataclass(frozen=True)
class Species:
    name: str
    sheet: str           # file in assets/sprites/pixellab/
    base_hp: int         # Gen 1 base stats
    base_attack: int
    base_defense: int
    base_speed: int
    foot_sink: int = 0   # px the sprite is drawn into the ground (3/4-angle feet)


SPECIES = {
    "bulbasaur": Species("Bulbasaur", "bulbasaur.png", 45, 49, 49, 45, foot_sink=3),
    "pidgey": Species("Pidgey", "pidgey.png", 40, 45, 40, 56, foot_sink=1),
}


@cache
def idle_animation(species: Species) -> Animation:
    """A standing pose: the first frame of the sheet's first row."""
    rows = load_sheet(settings.ASSETS / "sprites" / "pixellab" / species.sheet, 64, 64)
    return Animation(rows[0][:1], fps=1)


def _stat(base: int, level: int) -> int:
    # The Gen 1 formula without IVs/EVs.
    return base * 2 * level // 100 + 5


@dataclass
class Monster:
    """One Pokémon: its species, level and current HP."""
    species: Species
    level: int
    hp: int = -1  # -1 = full

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.max_hp

    @classmethod
    def create(cls, species: str, level: int) -> "Monster":
        return cls(SPECIES[species], level)

    @property
    def name(self) -> str:
        return self.species.name

    @property
    def max_hp(self) -> int:
        return self.species.base_hp * 2 * self.level // 100 + self.level + 10

    @property
    def attack(self) -> int:
        return _stat(self.species.base_attack, self.level)

    @property
    def defense(self) -> int:
        return _stat(self.species.base_defense, self.level)

    @property
    def speed(self) -> int:
        return _stat(self.species.base_speed, self.level)
