"""Pokémon species and individual Pokémon (party members and enemies)."""

import random
from dataclasses import dataclass, field
from functools import cache

import pygame

from .. import settings
from ..engine import hats
from ..engine.animation import Animation, load_sheet
from .items import SLOTS, Gear, boosted
from .moves import Move
from .skills import MAX_EQUIPPED, TREES, SkillTree, stand_in_tree
from .status import SLEEP_ROUNDS, STATUSES


@dataclass(frozen=True)
class AnimSpec:
    """Where an animation is in the sprite sheets, and how it plays."""
    sheet: str                 # file in assets/sprites/pixellab/
    row: int
    fps: float = 8
    loop: bool = False
    frames: int | None = None  # use only the first N frames
    baseline: int | tuple[int | None, ...] | None = None  # see Animation
    per_frame_baseline: bool = False
    face_left: tuple[int, ...] = ()  # frames drawn facing left; mirrored on load
    cell: int = 64             # the sheet's frame size (square)


@dataclass(frozen=True)
class Species:
    name: str
    base_hp: int         # Gen 1 base stats
    base_attack: int
    base_defense: int
    base_speed: int
    types: tuple[str, ...]  # one or two of type_chart.TYPES
    fight_anim: str         # animation for moves without their own
    anims: dict[str, AnimSpec] = field(hash=False, compare=False)
    foot_sink: int = 0   # px the sprite is drawn into the ground (3/4-angle feet)
    # Placeholder art: a reference icon (assets/sprites/pokemon_icons/), used
    # as a still sprite until the species gets a Pixellab sheet.
    icon: str = ""
    base_exp: int = 64  # Gen 1 base experience yield: XP for defeating one
    size: float = 1.0   # drawn this many times bigger than its sheet (e.g. Pidgeot)

    @property
    def key(self) -> str:
        """Its key in `SPECIES` ("bulbasaur")."""
        return _KEYS[self]

    @property
    def evolution(self) -> "Evolution | None":
        """How it evolves by level, if it does and what it evolves into is in
        the game yet."""
        evolution = EVOLUTIONS.get(self.key)
        return evolution if evolution and evolution.into in SPECIES else None

    @property
    def stage(self) -> int:
        """Its evolution stage: 0 for the first of its line (Bulbasaur), 1
        once evolved (Ivysaur), ..."""
        key, stage = self.key, 0
        while key in _EVOLVES_FROM:
            key, stage = _EVOLVES_FROM[key], stage + 1
        return stage

    @property
    def tree(self) -> SkillTree:
        """Its line's skill tree."""
        key = self.key
        while key in _EVOLVES_FROM:
            key = _EVOLVES_FROM[key]
        return TREES.get(key) or stand_in_tree(key)


BULBASAUR_ATTACKS = "bulbasaur attacks.png"

SPECIES = {
    "bulbasaur": Species(
        "Bulbasaur", 45, 49, 49, 45, ("grass", "poison"),
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
    "ivysaur": Species(
        "Ivysaur", 60, 62, 63, 60, ("grass", "poison"),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("ivysaur.png", 0, fps=1, loop=True, frames=1),
            "walk": AnimSpec("ivysaur.png", 0, loop=True),
            "run": AnimSpec("ivysaur.png", 1, fps=12, loop=True),
            "jump": AnimSpec("ivysaur.png", 2, fps=1, per_frame_baseline=True),
            "attack": AnimSpec("ivysaur.png", 3),
        },
        foot_sink=3,
        base_exp=141),
    # The starters' evolutions (generated with PixelLab, like Pidgeotto): 88 px
    # cells, rows walk, run, jump (crouch, rise, fall, land) and attack.
    "venusaur": Species(
        "Venusaur", 80, 82, 83, 80, ("grass", "poison"),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("venusaur.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("venusaur.png", 0, loop=True, cell=88),
            "run": AnimSpec("venusaur.png", 1, fps=12, loop=True, cell=88),
            "jump": AnimSpec("venusaur.png", 2, fps=1, frames=4, per_frame_baseline=True, cell=88),
            "attack": AnimSpec("venusaur.png", 3, cell=88),
        },
        foot_sink=3,
        base_exp=208,
        size=1.2),
    "charmander": Species(
        "Charmander", 39, 52, 43, 65, ("fire",),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("charmander.png", 0, fps=1, loop=True, frames=1),
            "walk": AnimSpec("charmander.png", 0, loop=True),
            "run": AnimSpec("charmander.png", 1, fps=12, loop=True),
            # The rising frame's tail flame hangs below its feet.
            "jump": AnimSpec("charmander.png", 2, fps=1, per_frame_baseline=True,
                             baseline=(None, 57, None, None)),
            "attack": AnimSpec("charmander.png", 3),
        },
        foot_sink=2,
        base_exp=65),
    "charmeleon": Species(
        "Charmeleon", 58, 64, 58, 80, ("fire",),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("charmeleon.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("charmeleon.png", 0, loop=True, cell=88),
            "run": AnimSpec("charmeleon.png", 1, fps=12, loop=True, cell=88),
            "jump": AnimSpec("charmeleon.png", 2, fps=1, frames=4, per_frame_baseline=True, cell=88),
            "attack": AnimSpec("charmeleon.png", 3, cell=88),
        },
        foot_sink=2,
        base_exp=142),
    "charizard": Species(
        "Charizard", 78, 84, 78, 100, ("fire", "flying"),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("charizard.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("charizard.png", 0, loop=True, cell=88),
            "run": AnimSpec("charizard.png", 1, fps=12, loop=True, cell=88),
            "jump": AnimSpec("charizard.png", 2, fps=1, frames=4, per_frame_baseline=True, cell=88),
            "attack": AnimSpec("charizard.png", 3, cell=88),
        },
        foot_sink=2,
        base_exp=209,
        size=1.2),
    "squirtle": Species(
        "Squirtle", 44, 48, 65, 43, ("water",),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("squirtle.png", 0, fps=1, loop=True, frames=1),
            "walk": AnimSpec("squirtle.png", 0, loop=True),
            "run": AnimSpec("squirtle.png", 1, fps=12, loop=True),
            "jump": AnimSpec("squirtle.png", 2, fps=1, per_frame_baseline=True),
            "attack": AnimSpec("squirtle.png", 3),
        },
        foot_sink=2,
        base_exp=66),
    "wartortle": Species(
        "Wartortle", 59, 63, 80, 58, ("water",),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("wartortle.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("wartortle.png", 0, loop=True, cell=88),
            "run": AnimSpec("wartortle.png", 1, fps=12, loop=True, cell=88),
            "jump": AnimSpec("wartortle.png", 2, fps=1, frames=4, per_frame_baseline=True, cell=88),
            "attack": AnimSpec("wartortle.png", 3, cell=88),
        },
        foot_sink=2,
        base_exp=143),
    "blastoise": Species(
        "Blastoise", 79, 83, 100, 78, ("water",),
        fight_anim="attack",
        anims={
            "idle": AnimSpec("blastoise.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("blastoise.png", 0, loop=True, cell=88),
            "run": AnimSpec("blastoise.png", 1, fps=12, loop=True, cell=88),
            "jump": AnimSpec("blastoise.png", 2, fps=1, frames=4, per_frame_baseline=True, cell=88),
            "attack": AnimSpec("blastoise.png", 3, cell=88),
        },
        foot_sink=2,
        base_exp=210,
        size=1.2),
    "pidgey": Species(
        "Pidgey", 40, 45, 40, 56, ("normal", "flying"),
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
    # Pidgeotto's and Pidgeot's sheets have 88 px cells (room for the wings)
    # and 5 frames a row: the still pose, then 4 generated frames.
    "pidgeotto": Species(
        "Pidgeotto", 63, 60, 55, 71, ("normal", "flying"),
        fight_anim="tackle",
        anims={
            "idle": AnimSpec("pidgeotto.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("pidgeotto.png", 0, loop=True, cell=88),
            "fly": AnimSpec("pidgeotto.png", 1, loop=True, cell=88),
            "gust": AnimSpec("pidgeotto.png", 2, cell=88),
            "tackle": AnimSpec("pidgeotto.png", 3, cell=88),
        },
        foot_sink=1,
        base_exp=113),
    "pidgeot": Species(
        "Pidgeot", 83, 80, 75, 91, ("normal", "flying"),
        fight_anim="tackle",
        anims={
            "idle": AnimSpec("pidgeot.png", 0, fps=1, loop=True, frames=1, cell=88),
            "walk": AnimSpec("pidgeot.png", 0, loop=True, cell=88),
            "fly": AnimSpec("pidgeot.png", 1, loop=True, cell=88),
            "gust": AnimSpec("pidgeot.png", 2, cell=88),
            "tackle": AnimSpec("pidgeot.png", 3, cell=88),
        },
        foot_sink=1,
        base_exp=172,
        size=1.2),  # (its sprite is drawn about as big as Pidgeotto's)
}


def _placeholder(icon: str, name: str, stats: tuple[int, int, int, int], types: tuple[str, ...],
                 exp: int) -> Species:
    return Species(name, *stats, types, fight_anim="attack", anims={}, icon=icon, base_exp=exp)


# Species that only have a reference icon so far: Gen 1 base stats (HP,
# Attack, Defense, Speed), types and base experience yield. (Their moves come
# from their line's skill tree, skills.TREES.)
SPECIES.update({
    "spearow": _placeholder("021_spearow", "Spearow", (40, 60, 30, 70), ("normal", "flying"), exp=58),
    # (The game's font has no ♀/♂ symbols.)
    "nidoran_f": _placeholder("029_nidoran-f", "Nidoran F", (55, 47, 52, 41), ("poison",), exp=59),
    "nidoran_m": _placeholder("032_nidoran-m", "Nidoran M", (46, 57, 40, 50), ("poison",), exp=60),
    "rattata": _placeholder("019_rattata", "Rattata", (30, 56, 35, 72), ("normal",), exp=57),
    "caterpie": _placeholder("010_caterpie", "Caterpie", (45, 30, 35, 45), ("bug",), exp=53),
    "metapod": _placeholder("011_metapod", "Metapod", (50, 20, 55, 30), ("bug",), exp=72),
    "weedle": _placeholder("013_weedle", "Weedle", (40, 35, 30, 50), ("bug", "poison"), exp=52),
    "kakuna": _placeholder("014_kakuna", "Kakuna", (45, 25, 50, 35), ("bug", "poison"), exp=71),
    "oddish": _placeholder("043_oddish", "Oddish", (45, 50, 55, 30), ("grass", "poison"), exp=78),
    "bellsprout": _placeholder("069_bellsprout", "Bellsprout", (50, 75, 35, 40), ("grass", "poison"), exp=84),
    "pikachu": _placeholder("025_pikachu", "Pikachu", (35, 55, 30, 90), ("electric",), exp=82),
    "seel": _placeholder("086_seel", "Seel", (65, 45, 55, 45), ("water",), exp=100),
    "shellder": _placeholder("090_shellder", "Shellder", (30, 65, 100, 40), ("water",), exp=97),
    "psyduck": _placeholder("054_psyduck", "Psyduck", (50, 52, 48, 55), ("water",), exp=80),
    "horsea": _placeholder("116_horsea", "Horsea", (30, 40, 70, 60), ("water",), exp=83),
    "jynx": _placeholder("124_jynx", "Jynx", (65, 50, 35, 95), ("ice", "psychic"), exp=137),
    "dewgong": _placeholder("087_dewgong", "Dewgong", (90, 70, 80, 70), ("water", "ice"), exp=176),
    "lapras": _placeholder("131_lapras", "Lapras", (130, 85, 80, 60), ("water", "ice"), exp=219),
})

_KEYS = {species: key for key, species in SPECIES.items()}


@dataclass(frozen=True)
class Evolution:
    into: str   # species key
    level: int  # evolves on reaching this level


# Every evolution by level in Red/Blue (species key -> evolution). Trade and
# stone evolutions aren't here yet. An evolution only happens once the
# species it evolves into is in `SPECIES`.
EVOLUTIONS = {key: Evolution(into, level) for key, into, level in [
    ("bulbasaur", "ivysaur", 16), ("ivysaur", "venusaur", 32),
    ("charmander", "charmeleon", 16), ("charmeleon", "charizard", 36),
    ("squirtle", "wartortle", 16), ("wartortle", "blastoise", 36),
    ("caterpie", "metapod", 7), ("metapod", "butterfree", 10),
    ("weedle", "kakuna", 7), ("kakuna", "beedrill", 10),
    ("pidgey", "pidgeotto", 18), ("pidgeotto", "pidgeot", 36),
    ("rattata", "raticate", 20),
    ("spearow", "fearow", 20),
    ("ekans", "arbok", 22),
    ("sandshrew", "sandslash", 22),
    ("nidoran_f", "nidorina", 16),
    ("nidoran_m", "nidorino", 16),
    ("zubat", "golbat", 22),
    ("oddish", "gloom", 21),
    ("paras", "parasect", 24),
    ("venonat", "venomoth", 31),
    ("diglett", "dugtrio", 26),
    ("meowth", "persian", 28),
    ("psyduck", "golduck", 33),
    ("mankey", "primeape", 28),
    ("poliwag", "poliwhirl", 25),
    ("abra", "kadabra", 16),
    ("machop", "machoke", 28),
    ("bellsprout", "weepinbell", 21),
    ("tentacool", "tentacruel", 30),
    ("geodude", "graveler", 25),
    ("ponyta", "rapidash", 40),
    ("slowpoke", "slowbro", 37),
    ("magnemite", "magneton", 30),
    ("doduo", "dodrio", 31),
    ("seel", "dewgong", 34),
    ("grimer", "muk", 38),
    ("gastly", "haunter", 25),
    ("drowzee", "hypno", 26),
    ("krabby", "kingler", 28),
    ("voltorb", "electrode", 30),
    ("cubone", "marowak", 28),
    ("koffing", "weezing", 35),
    ("rhyhorn", "rhydon", 42),
    ("horsea", "seadra", 32),
    ("goldeen", "seaking", 33),
    ("magikarp", "gyarados", 20),
    ("omanyte", "omastar", 40),
    ("kabuto", "kabutops", 40),
    ("dratini", "dragonair", 30), ("dragonair", "dragonite", 55),
]}

_EVOLVES_FROM = {e.into: key for key, e in EVOLUTIONS.items()}

ICON_SCALE = 0.75  # icons share one scale, so species keep their relative sizes


@cache
def _sheet(name: str, cell: int = 64) -> list[list[pygame.Surface]]:
    return load_sheet(settings.ASSETS / "sprites" / "pixellab" / name, cell, cell)


@cache
def _icon_frame(icon: str) -> pygame.Surface:
    """A reference icon as a still sprite: cropped, scaled, facing right."""
    image = pygame.image.load(settings.ASSETS / "sprites" / "pokemon_icons" / f"{icon}.png").convert_alpha()
    image = image.subsurface(image.get_bounding_rect()).copy()
    image = pygame.transform.smoothscale_by(image, ICON_SCALE)
    return pygame.transform.flip(image, True, False)  # the icons face left


@cache
def animations(species: Species, scale: int = 1) -> dict[str, Animation]:
    """The species' animations, all facing right (`scale` times bigger, for bosses)."""
    if scale != 1:
        return {name: anim.scaled(scale) for name, anim in animations(species).items()}
    if species.icon:  # a placeholder: the same still frame for everything
        frame = _icon_frame(species.icon)
        still = Animation([frame], fps=1, loop=True)
        # Attacks get a few frames, so the battle's timing (impact on the
        # second-to-last frame) still works.
        return {"idle": still, "walk": still, "attack": Animation([frame] * 4, fps=8, loop=False)}
    anims = {}
    for name, spec in species.anims.items():
        frames = _sheet(spec.sheet, spec.cell)[spec.row][:spec.frames]
        frames = [pygame.transform.flip(f, True, False) if i in spec.face_left else f
                  for i, f in enumerate(frames)]
        anims[name] = Animation(frames, spec.fps, spec.loop,
                                per_frame_baseline=spec.per_frame_baseline, baseline=spec.baseline)
        anims[name].heads = hats.head_anchors(spec.sheet, spec.row, len(frames))
        if species.size != 1:
            anims[name] = anims[name].scaled(species.size)
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
    """One Pokémon: its species, level, XP, current HP, status, equipped
    gear, and skills (ranks in its line's skill tree, and the moves it has
    equipped)."""
    species: Species
    level: int
    hp: int = -1  # -1 = full
    gear: dict[str, Gear] = field(default_factory=dict)  # slot -> gear
    status: str = ""       # a key of status.STATUSES, or "" for none
    sleep_rounds: int = 0  # rounds left asleep
    xp: int = -1  # total; -1 = just reached its level
    skills: dict[str, int] = field(default_factory=dict)  # skill key -> rank
    equipped: list[str] = field(default_factory=list)     # skill keys of the moves it uses, besides Fight
    scale: int = 1  # drawn this many times bigger (bosses); not saved

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.max_hp
        if self.xp < 0:
            self.xp = xp_for_level(self.level)
        if not self.skills:  # (a save from before skill trees, too) its base attacks
            self.reset_skills()

    @classmethod
    def create(cls, species: str, level: int) -> "Monster":
        """A Pokémon whose skills are chosen for it (wild ones, and the
        starter): see `SkillTree.auto_build`."""
        monster = cls(SPECIES[species], level)
        monster.skills, monster.equipped = monster.tree.auto_build(level, monster.species.stage)
        return monster

    @property
    def name(self) -> str:
        return self.species.name

    @property
    def alive(self) -> bool:
        return self.hp > 0

    # ----------------------------------------------------------- skills

    @property
    def tree(self) -> SkillTree:
        return self.species.tree

    @property
    def skill_points(self) -> int:
        """Points not spent yet."""
        return self.tree.total_points(self.level) - self.tree.spent(self.skills)

    def why_not(self, key: str) -> str:
        """Why skill `key` can't be ranked up now ("" if it can)."""
        return self.tree.why_not(self.skills, key, self.level, self.species.stage)

    def rank_up(self, key: str) -> bool:
        """Spend a point on skill `key` (learning it at rank 1). A move
        learned while there's a free slot is equipped."""
        if self.why_not(key):
            return False
        self.skills[key] = self.skills.get(key, 0) + 1
        skill = self.tree.skills[key]
        if (self.skills[key] == 1 and skill.kind == "move" and key not in self.equipped
                and len(self.equipped) < MAX_EQUIPPED):
            self.equipped.append(key)
        return True

    def reset_skills(self) -> None:
        """Take back every point: only the base attacks are left, equipped."""
        tree = self.tree
        self.skills = {s.key: 1 for s in tree.base}
        self.equipped = [s.key for s in tree.base[1:]][:MAX_EQUIPPED]

    def move(self, key: str) -> Move:
        """Skill `key`'s move, with its rank and modifiers."""
        return self.tree.effective_move(self.skills, key)

    @property
    def basic_attack(self) -> Move:
        """What Fight does: the first base attack."""
        return self.move(self.tree.basic.key)

    @property
    def moves(self) -> list[Move]:
        """The equipped moves (the battle's Skills menu)."""
        return [self.move(key) for key in self.equipped if key in self.skills]

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

    @property
    def can_evolve(self) -> bool:
        evolution = self.species.evolution
        return bool(evolution) and self.level >= evolution.level

    def evolve(self) -> None:
        """Become what its species evolves into. Like a level up, the HP it
        gains is added to its current HP."""
        missing = self.max_hp - self.hp
        self.species = SPECIES[self.species.evolution.into]
        self._set_missing_hp(missing)

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
