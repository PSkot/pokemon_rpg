"""Pokémon species and individual Pokémon (party members and enemies)."""

import random
from dataclasses import dataclass, field
from functools import cache

import pygame

from .. import settings
from ..engine import hats
from ..engine.animation import Animation, load_sheet
from .items import SLOTS, Gear, boosted
from .status import SLEEP_ROUNDS, STATUSES


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
    type: str = ""      # one of type_chart.TYPES; "" = typeless
    status: str = ""    # a status (see status.STATUSES) a hit may inflict ...
    status_chance: int = 0  # ... with this % chance


# "Fight" is every Pokémon's basic attack; the rest are its skills. It has
# no type: always neutral, no same-type bonus.
FIGHT = Move("Fight", 30, "enemy")

MOVES = {m.name: m for m in [
    Move("Tackle", 35, "enemy", "tackle", type="normal"),
    Move("Growth", 0, "self", "growth", effect="attack_up", type="normal"),
    Move("Solar Beam", 120, "enemy", "solar_beam", charge="{user} took in sunlight!", type="grass"),
    Move("Leaf Shield", 0, "ally", "leaf_shield", effect="shield", type="grass"),
    Move("Gust", 40, "enemy", "gust", type="flying"),  # Normal in Gen 1, Flying since Gen 2
    # Moves for species without their own animations yet (they use `fight_anim`).
    Move("Scratch", 40, "enemy", type="normal"),
    Move("Bite", 60, "enemy", type="normal"),
    Move("Headbutt", 70, "enemy", type="normal"),
    Move("Quick Attack", 40, "enemy", type="normal"),
    Move("Poison Sting", 15, "enemy", type="poison", status="poison", status_chance=30),
    Move("Acid", 40, "enemy", type="poison", status="poison", status_chance=10),
    Move("Absorb", 20, "enemy", type="grass"),
    Move("Vine Whip", 45, "enemy", type="grass"),
    Move("Thunder Shock", 40, "enemy", type="electric", status="paralysis", status_chance=10),
    Move("Water Gun", 40, "enemy", type="water"),
    Move("Bubble", 40, "enemy", type="water"),
    Move("Powder Snow", 40, "enemy", type="ice", status="freeze", status_chance=10),
    Move("Aurora Beam", 65, "enemy", type="ice"),
    Move("Ice Beam", 90, "enemy", type="ice", status="freeze", status_chance=10),
    Move("Confusion", 50, "enemy", type="psychic"),
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
    types: tuple[str, ...]  # one or two of type_chart.TYPES
    moves: tuple[str, ...]  # skills, by name in MOVES
    fight_anim: str         # animation used by Fight
    anims: dict[str, AnimSpec] = field(hash=False, compare=False)
    foot_sink: int = 0   # px the sprite is drawn into the ground (3/4-angle feet)
    # Placeholder art: a reference icon (assets/sprites/pokemon_icons/), used
    # as a still sprite until the species gets a Pixellab sheet.
    icon: str = ""
    base_exp: int = 64  # Gen 1 base experience yield: XP for defeating one


BULBASAUR_ATTACKS = "bulbasaur attacks.png"

SPECIES = {
    "bulbasaur": Species(
        "Bulbasaur", 45, 49, 49, 45, ("grass", "poison"),
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
        foot_sink=3,
        base_exp=64),
    "pidgey": Species(
        "Pidgey", 40, 45, 40, 56, ("normal", "flying"),
        moves=("Gust", "Tackle"),
        fight_anim="tackle",
        anims={
            "idle": AnimSpec("pidgey.png", 0, fps=1, loop=True, frames=1),
            "walk": AnimSpec("pidgey.png", 0, loop=True),
            "fly": AnimSpec("pidgey.png", 1, loop=True, face_left=(0, 1, 2, 3)),
            "gust": AnimSpec("pidgey.png", 2, face_left=(0, 1)),
            "tackle": AnimSpec("pidgey.png", 3, face_left=(0,)),
        },
        foot_sink=1,
        base_exp=55),
}


def _placeholder(icon: str, name: str, stats: tuple[int, int, int, int], types: tuple[str, ...],
                 moves: tuple[str, ...], exp: int) -> Species:
    return Species(name, *stats, types, moves, fight_anim="attack", anims={}, icon=icon, base_exp=exp)


# Species that only have a reference icon so far: Gen 1 base stats (HP,
# Attack, Defense, Speed), types, a few early moves, and base experience yield.
SPECIES.update({
    "rattata": _placeholder("019_rattata", "Rattata", (30, 56, 35, 72), ("normal",),
                            ("Tackle", "Quick Attack"), exp=57),
    "caterpie": _placeholder("010_caterpie", "Caterpie", (45, 30, 35, 45), ("bug",), ("Tackle",), exp=53),
    "weedle": _placeholder("013_weedle", "Weedle", (40, 35, 30, 50), ("bug", "poison"),
                           ("Poison Sting",), exp=52),
    "oddish": _placeholder("043_oddish", "Oddish", (45, 50, 55, 30), ("grass", "poison"),
                           ("Absorb", "Acid"), exp=78),
    "bellsprout": _placeholder("069_bellsprout", "Bellsprout", (50, 75, 35, 40), ("grass", "poison"),
                               ("Vine Whip", "Acid"), exp=84),
    "pikachu": _placeholder("025_pikachu", "Pikachu", (35, 55, 30, 90), ("electric",),
                            ("Thunder Shock", "Quick Attack"), exp=82),
    "seel": _placeholder("086_seel", "Seel", (65, 45, 55, 45), ("water",),
                         ("Headbutt", "Powder Snow"), exp=100),
    "shellder": _placeholder("090_shellder", "Shellder", (30, 65, 100, 40), ("water",),
                             ("Tackle", "Water Gun"), exp=97),
    "psyduck": _placeholder("054_psyduck", "Psyduck", (50, 52, 48, 55), ("water",),
                            ("Scratch", "Water Gun"), exp=80),
    "horsea": _placeholder("116_horsea", "Horsea", (30, 40, 70, 60), ("water",),
                           ("Bubble", "Water Gun"), exp=83),
    "jynx": _placeholder("124_jynx", "Jynx", (65, 50, 35, 95), ("ice", "psychic"),
                         ("Powder Snow", "Confusion"), exp=137),
    "dewgong": _placeholder("087_dewgong", "Dewgong", (90, 70, 80, 70), ("water", "ice"),
                            ("Headbutt", "Aurora Beam"), exp=176),
    "lapras": _placeholder("131_lapras", "Lapras", (130, 85, 80, 60), ("water", "ice"),
                           ("Water Gun", "Ice Beam"), exp=219),
})

ICON_SCALE = 0.75  # icons share one scale, so species keep their relative sizes


@cache
def _sheet(name: str) -> list[list[pygame.Surface]]:
    return load_sheet(settings.ASSETS / "sprites" / "pixellab" / name, 64, 64)


@cache
def _icon_frame(icon: str) -> pygame.Surface:
    """A reference icon as a still sprite: cropped, scaled, facing right."""
    image = pygame.image.load(settings.ASSETS / "sprites" / "pokemon_icons" / f"{icon}.png").convert_alpha()
    image = image.subsurface(image.get_bounding_rect()).copy()
    image = pygame.transform.smoothscale_by(image, ICON_SCALE)
    return pygame.transform.flip(image, True, False)  # the icons face left


@cache
def animations(species: Species) -> dict[str, Animation]:
    """The species' animations, all facing right."""
    if species.icon:  # a placeholder: the same still frame for everything
        frame = _icon_frame(species.icon)
        still = Animation([frame], fps=1, loop=True)
        # Attacks get a few frames, so the battle's timing (impact on the
        # second-to-last frame) still works.
        return {"idle": still, "walk": still, "attack": Animation([frame] * 4, fps=8, loop=False)}
    anims = {}
    for name, spec in species.anims.items():
        frames = _sheet(spec.sheet)[spec.row][:spec.frames]
        frames = [pygame.transform.flip(f, True, False) if i in spec.face_left else f
                  for i, f in enumerate(frames)]
        anims[name] = Animation(frames, spec.fps, spec.loop,
                                per_frame_baseline=spec.per_frame_baseline, baseline=spec.baseline)
        anims[name].heads = hats.head_anchors(spec.sheet, spec.row, len(frames))
    return anims


MAX_LEVEL = 100


def xp_for_level(level: int) -> int:
    """Total XP needed to reach `level` (Gen 1's "medium fast" growth rate)."""
    return 0 if level <= 1 else level ** 3


def _stat(base: int, level: int) -> int:
    # The Gen 1 formula without IVs/EVs.
    return base * 2 * level // 100 + 5


@dataclass
class Monster:
    """One Pokémon: its species, level, XP, current HP, status and equipped gear."""
    species: Species
    level: int
    hp: int = -1  # -1 = full
    gear: dict[str, Gear] = field(default_factory=dict)  # slot -> gear
    status: str = ""       # a key of status.STATUSES, or "" for none
    sleep_rounds: int = 0  # rounds left asleep
    xp: int = -1  # total; -1 = just reached its level

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.max_hp
        if self.xp < 0:
            self.xp = xp_for_level(self.level)

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

    @property
    def xp_yield(self) -> int:
        """XP for defeating it (the Gen 1 formula for wild Pokémon)."""
        return self.species.base_exp * self.level // 7

    @property
    def xp_progress(self) -> tuple[int, int]:
        """(XP gained since its level, XP that level needs to the next)."""
        if self.level >= MAX_LEVEL:
            return 0, 0
        start = xp_for_level(self.level)
        return self.xp - start, xp_for_level(self.level + 1) - start

    @property
    def can_level_up(self) -> bool:
        return self.level < MAX_LEVEL and self.xp >= xp_for_level(self.level + 1)

    def level_up(self) -> None:
        """One level up. The HP it gains is added to its current HP, so the
        damage taken stays the same."""
        missing = self.max_hp - self.hp
        self.level += 1
        self._set_missing_hp(missing)

    def inflict(self, status: str) -> bool:
        """Give it `status`, unless it already has one or its type is immune."""
        if self.status or not self.alive or STATUSES[status].immune in self.species.types:
            return False
        self.status = status
        if status == "sleep":
            self.sleep_rounds = random.randint(*SLEEP_ROUNDS)
        return True

    def cure(self) -> None:
        self.status, self.sleep_rounds = "", 0

    def anim_for(self, move: Move) -> str:
        """The move's own animation if this species has one (placeholders
        don't), else its basic attack."""
        return move.anim if move.anim in self.species.anims else self.species.fight_anim

    def equip(self, gear: Gear) -> Gear | None:
        """Put on `gear`; returns what was in its slot before."""
        missing = self.max_hp - self.hp
        old = self.gear.get(gear.slot)
        self.gear[gear.slot] = gear
        self._set_missing_hp(missing)
        return old

    def unequip(self, slot: str) -> Gear | None:
        missing = self.max_hp - self.hp
        old = self.gear.pop(slot, None)
        self._set_missing_hp(missing)
        return old

    def _set_missing_hp(self, missing: int) -> None:
        # Gear changes keep the damage taken, so a full-HP Pokémon stays full.
        if self.alive:
            self.hp = max(1, self.max_hp - missing)

    def gear_bonus(self, mod: str) -> int:
        """Total of `mod` (see `items.MOD_TEXT`) from equipped gear."""
        return sum(self.gear[slot].mods.get(mod, 0) for slot in SLOTS if slot in self.gear)

    # Stats without gear.
    @property
    def base_max_hp(self) -> int:
        return self.species.base_hp * 2 * self.level // 100 + self.level + 10

    @property
    def base_attack(self) -> int:
        return _stat(self.species.base_attack, self.level)

    @property
    def base_defense(self) -> int:
        return _stat(self.species.base_defense, self.level)

    @property
    def base_speed(self) -> int:
        return _stat(self.species.base_speed, self.level)

    # Stats with gear: what battles use.
    @property
    def max_hp(self) -> int:
        return boosted(self.base_max_hp, self.gear_bonus("hp"))

    @property
    def attack(self) -> int:
        return boosted(self.base_attack, self.gear_bonus("attack"))

    @property
    def defense(self) -> int:
        return boosted(self.base_defense, self.gear_bonus("defense"))

    @property
    def speed(self) -> int:
        return boosted(self.base_speed, self.gear_bonus("speed"))
