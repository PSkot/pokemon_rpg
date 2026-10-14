"""Pokémon species and individual Pokémon (party members and enemies)."""

from dataclasses import dataclass, field
from functools import cache

import pygame

from . import settings
from .animation import Animation, load_sheet


@dataclass(frozen=True)
class Move:
    name: str
    power: int          # 0 = status move (no damage)
    target: str         # "enemy" (the other side), "ally" (own side) or "self"
    anim: str = ""      # animation name; "" = the species' `fight_anim`
    effect: str = ""    # status moves: "attack_up" or "shield"
    # Moves with a charge message spend a round charging (the first half of
    # the animation) and fire the next round (the second half).
    charge: str = ""


# "Fight" is every Pokémon's basic attack; the rest are its skills.
FIGHT = Move("Fight", 30, "enemy")

MOVES = {m.name: m for m in [
    Move("Tackle", 35, "enemy", "tackle"),
    Move("Growth", 0, "self", "growth", effect="attack_up"),
    Move("Solar Beam", 120, "enemy", "solar_beam", charge="{user} took in sunlight!"),
    Move("Leaf Shield", 0, "ally", "leaf_shield", effect="shield"),
    Move("Gust", 40, "enemy", "gust"),
]}


@dataclass(frozen=True)
class AnimSpec:
    """Where an animation is in the sprite sheets, and how it plays."""
    sheet: str                 # file in assets/sprites/pixellab/
    row: int
    fps: float = 8
    loop: bool = False
    frames: int | None = None  # use only the first N frames
    baseline: int | None = None
    per_frame_baseline: bool = False
    face_left: tuple[int, ...] = ()  # frames drawn facing left; mirrored on load


@dataclass(frozen=True)
class Species:
    name: str
    base_hp: int         # Gen 1 base stats
    base_attack: int
    base_defense: int
    base_speed: int
    moves: tuple[str, ...]  # skills, by name in MOVES
    fight_anim: str         # animation used by Fight
    anims: dict[str, AnimSpec] = field(hash=False, compare=False)
    foot_sink: int = 0   # px the sprite is drawn into the ground (3/4-angle feet)


BULBASAUR_ATTACKS = "bulbasaur attacks.png"

SPECIES = {
    "bulbasaur": Species(
        "Bulbasaur", 45, 49, 49, 45,
        moves=("Tackle", "Growth", "Solar Beam", "Leaf Shield"),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("bulbasaur.png", 0, fps=1, loop=True, frames=1),
            "walk": AnimSpec("bulbasaur.png", 0, loop=True),
            "run": AnimSpec("bulbasaur.png", 1, fps=12, loop=True),
            "jump": AnimSpec("bulbasaur.png", 2, fps=1, per_frame_baseline=True),
            "attack": AnimSpec("bulbasaur.png", 3),
            # The aura and shield effects reach below the feet, so those rows
            # get their feet row set by hand.
            "growth": AnimSpec(BULBASAUR_ATTACKS, 0, baseline=59),
            "solar_beam": AnimSpec(BULBASAUR_ATTACKS, 1),
            "leaf_shield": AnimSpec(BULBASAUR_ATTACKS, 2, baseline=60),
            "tackle": AnimSpec(BULBASAUR_ATTACKS, 3),
        },
        foot_sink=3),
    "pidgey": Species(
        "Pidgey", 40, 45, 40, 56,
        moves=("Gust", "Tackle"),
        fight_anim="tackle",
        anims={
            "idle": AnimSpec("pidgey.png", 0, fps=1, loop=True, frames=1),
            "walk": AnimSpec("pidgey.png", 0, loop=True),
            "fly": AnimSpec("pidgey.png", 1, loop=True, face_left=(0, 1, 2, 3)),
            "gust": AnimSpec("pidgey.png", 2, face_left=(0, 1)),
            "tackle": AnimSpec("pidgey.png", 3, face_left=(0,)),
        },
        foot_sink=1),
}


@cache
def _sheet(name: str) -> list[list[pygame.Surface]]:
    return load_sheet(settings.ASSETS / "sprites" / "pixellab" / name, 64, 64)


@cache
def animations(species: Species) -> dict[str, Animation]:
    """The species' animations, all facing right."""
    anims = {}
    for name, spec in species.anims.items():
        frames = _sheet(spec.sheet)[spec.row][:spec.frames]
        frames = [pygame.transform.flip(f, True, False) if i in spec.face_left else f
                  for i, f in enumerate(frames)]
        anims[name] = Animation(frames, spec.fps, spec.loop,
                                per_frame_baseline=spec.per_frame_baseline, baseline=spec.baseline)
    return anims


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
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def moves(self) -> list[Move]:
        return [MOVES[name] for name in self.species.moves]

    def anim_for(self, move: Move) -> str:
        return move.anim or self.species.fight_anim

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
