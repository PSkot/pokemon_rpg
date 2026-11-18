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
from .talents import MAX_EQUIPPED, TALENT_MODS, TREES, TalentTree, stand_in_tree
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
    size: float = 1.0  # drawn this many times its sheet's size (nearest-neighbour: Onix)

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
    def tree(self) -> TalentTree:
        """Its line's moves and talents."""
        key = self.key
        while key in _EVOLVES_FROM:
            key = _EVOLVES_FROM[key]
        return TREES.get(key) or stand_in_tree(key)


SPECIES: dict[str, Species] = {}  # filled in below (`_animated`, `_placeholder`)


def _placeholder(icon: str, name: str, stats: tuple[int, int, int, int], types: tuple[str, ...],
                 exp: int) -> Species:
    return Species(name, *stats, types, fight_anim="attack", anims={}, icon=icon, base_exp=exp)


def _animated(key: str, name: str, stats: tuple[int, int, int, int], types: tuple[str, ...], exp: int,
              hit: int, size: float = 1.0) -> Species:
    """A species with a PixelLab sheet `<key>.png` (64 px cells): rows idle,
    walk and run (8 frames, looping), attack (9 frames: the still pose,
    then 8 generated) and jump (crouch, rise, fall, land). `hit` is the
    attack frame that strikes; the attack stops one frame later, as battles
    strike on its second-to-last frame."""
    sheet = f"{key}.png"
    return Species(name, *stats, types, fight_anim="attack", anims={
        "idle": AnimSpec(sheet, 0, fps=6, loop=True),
        "walk": AnimSpec(sheet, 1, fps=12, loop=True),
        "run": AnimSpec(sheet, 2, fps=16, loop=True),
        "attack": AnimSpec(sheet, 3, fps=12, frames=hit + 2),
        "jump": AnimSpec(sheet, 4, fps=1, per_frame_baseline=True),
    }, base_exp=exp, size=size)


# The other species: Gen 1 base stats (HP, Attack, Defense, Speed), types and
# base experience yield. (Their moves and talents come from their line's
# talents.TREES.) Those met up to Mt. Moon have PixelLab sheets; the rest only
# a reference icon so far.
SPECIES.update({
    # The starters' lines and the Pidgey line.
    "bulbasaur": _animated("bulbasaur", "Bulbasaur", (45, 49, 49, 45), ("grass", "poison"), exp=64, hit=4),
    "ivysaur": _animated("ivysaur", "Ivysaur", (60, 62, 63, 60), ("grass", "poison"), exp=141, hit=5),
    "venusaur": _animated("venusaur", "Venusaur", (80, 82, 83, 80), ("grass", "poison"), exp=208, hit=6),
    "charmander": _animated("charmander", "Charmander", (39, 52, 43, 65), ("fire",), exp=65, hit=4),
    "charmeleon": _animated("charmeleon", "Charmeleon", (58, 64, 58, 80), ("fire",), exp=142, hit=3),
    "charizard": _animated("charizard", "Charizard", (78, 84, 78, 100), ("fire", "flying"), exp=209, hit=4),
    "squirtle": _animated("squirtle", "Squirtle", (44, 48, 65, 43), ("water",), exp=66, hit=5),
    "wartortle": _animated("wartortle", "Wartortle", (59, 63, 80, 58), ("water",), exp=143, hit=3),
    "blastoise": _animated("blastoise", "Blastoise", (79, 83, 100, 78), ("water",), exp=210, hit=4),
    "pidgey": _animated("pidgey", "Pidgey", (40, 45, 40, 56), ("normal", "flying"), exp=55, hit=5),
    "pidgeotto": _animated("pidgeotto", "Pidgeotto", (63, 60, 55, 71), ("normal", "flying"), exp=113, hit=3),
    "pidgeot": _animated("pidgeot", "Pidgeot", (83, 80, 75, 91), ("normal", "flying"), exp=172, hit=3),
    "spearow": _animated("spearow", "Spearow", (40, 60, 30, 70), ("normal", "flying"), exp=58, hit=4),
    "fearow": _animated("fearow", "Fearow", (65, 90, 65, 100), ("normal", "flying"), exp=162, hit=3),
    # (The game's font has no ♀/♂ symbols.)
    "nidoran_f": _animated("nidoran_f", "Nidoran F", (55, 47, 52, 41), ("poison",), exp=59, hit=4),
    "nidoran_m": _animated("nidoran_m", "Nidoran M", (46, 57, 40, 50), ("poison",), exp=60, hit=4),
    "nidorina": _animated("nidorina", "Nidorina", (70, 62, 67, 56), ("poison",), exp=117, hit=5),
    "nidorino": _animated("nidorino", "Nidorino", (61, 72, 57, 65), ("poison",), exp=118, hit=4),
    "rattata": _animated("rattata", "Rattata", (30, 56, 35, 72), ("normal",), exp=57, hit=5),
    "caterpie": _animated("caterpie", "Caterpie", (45, 30, 35, 45), ("bug",), exp=53, hit=5),
    "metapod": _animated("metapod", "Metapod", (50, 20, 55, 30), ("bug",), exp=72, hit=2),
    # Butterfree hits with its Special (80), as Abra does: its moves are Confusion and powders.
    "butterfree": _animated("butterfree", "Butterfree", (60, 80, 50, 70), ("bug", "flying"), exp=160, hit=3),
    "weedle": _animated("weedle", "Weedle", (40, 35, 30, 50), ("bug", "poison"), exp=52, hit=4),
    "kakuna": _animated("kakuna", "Kakuna", (45, 25, 50, 35), ("bug", "poison"), exp=71, hit=5),
    "beedrill": _animated("beedrill", "Beedrill", (65, 80, 40, 75), ("bug", "poison"), exp=159, hit=5),
    "raticate": _animated("raticate", "Raticate", (55, 81, 60, 97), ("normal",), exp=116, hit=5),
    "oddish": _animated("oddish", "Oddish", (45, 50, 55, 30), ("grass", "poison"), exp=78, hit=4),
    "bellsprout": _animated("bellsprout", "Bellsprout", (50, 75, 35, 40), ("grass", "poison"), exp=84, hit=4),
    # Psychic Pokémon hit with Gen 1's Special, so Abra's Attack is its
    # Special (105) rather than its Attack (20); Kadabra's is 120.
    "abra": _animated("abra", "Abra", (25, 105, 15, 90), ("psychic",), exp=73, hit=5),
    "kadabra": _animated("kadabra", "Kadabra", (40, 120, 30, 105), ("psychic",), exp=145, hit=5),
    "venonat": _animated("venonat", "Venonat", (60, 55, 50, 45), ("bug", "poison"), exp=75, hit=5),
    "pikachu": _animated("pikachu", "Pikachu", (35, 55, 30, 90), ("electric",), exp=82, hit=5),
    "shellder": _animated("shellder", "Shellder", (30, 65, 100, 40), ("water",), exp=97, hit=4),
    "psyduck": _animated("psyduck", "Psyduck", (50, 52, 48, 55), ("water",), exp=80, hit=3),
    "goldeen": _animated("goldeen", "Goldeen", (45, 67, 60, 63), ("water",), exp=111, hit=4),
    "staryu": _animated("staryu", "Staryu", (30, 45, 55, 85), ("water",), exp=106, hit=5),
    "starmie": _animated("starmie", "Starmie", (60, 75, 85, 115), ("water", "psychic"), exp=207, hit=6),
    "horsea": _animated("horsea", "Horsea", (30, 40, 70, 60), ("water",), exp=83, hit=3),
    # The Pewter Gym and Route 3.
    "geodude": _animated("geodude", "Geodude", (40, 80, 100, 20), ("rock", "ground"), exp=86, hit=5),
    "onix": _animated("onix", "Onix", (35, 45, 160, 70), ("rock", "ground"), exp=108, hit=5, size=1.5),
    "diglett": _animated("diglett", "Diglett", (10, 55, 25, 95), ("ground",), exp=81, hit=4),
    "sandshrew": _animated("sandshrew", "Sandshrew", (50, 75, 85, 40), ("ground",), exp=93, hit=5),
    "ekans": _animated("ekans", "Ekans", (35, 60, 44, 55), ("poison",), exp=62, hit=4),
    "jigglypuff": _animated("jigglypuff", "Jigglypuff", (115, 45, 20, 20), ("normal",), exp=76, hit=4),
    # Mt. Moon.
    "zubat": _animated("zubat", "Zubat", (40, 45, 35, 55), ("poison", "flying"), exp=54, hit=5),
    "paras": _animated("paras", "Paras", (35, 70, 55, 25), ("bug", "grass"), exp=70, hit=4),
    "clefairy": _animated("clefairy", "Clefairy", (70, 45, 48, 35), ("normal",), exp=68, hit=3),
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

# Stone and trade evolutions aren't in yet, but some later forms already
# appear (Starmie leads the Cerulean Gym): this gives them their line's
# moves, talents and stage (they don't evolve from it).
LATER_FORMS = {"starmie": "staryu"}

_EVOLVES_FROM = {e.into: key for key, e in EVOLUTIONS.items()} | LATER_FORMS

ICON_SCALE = 0.75  # icons share one scale, so species keep their relative sizes


@cache
def _sheet(name: str, cell: int = 64) -> list[list[pygame.Surface]]:
    return load_sheet(settings.ASSETS / "sprites" / "pixellab" / name, cell, cell)


@cache
def icon_frame(icon: str) -> pygame.Surface:
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
        frame = icon_frame(species.icon)
        still = Animation([frame], fps=1, loop=True)
        # Attacks get a few frames, so the battle's timing (impact on the
        # second-to-last frame) still works.
        return {"idle": still, "walk": still, "attack": Animation([frame] * 4, fps=8, loop=False)}
    anims = {}
    for name, spec in species.anims.items():
        frames = _sheet(spec.sheet, spec.cell)[spec.row][:spec.frames]
        anims[name] = Animation(frames, spec.fps, spec.loop,
                                per_frame_baseline=spec.per_frame_baseline, baseline=spec.baseline)
        anims[name].heads = hats.head_anchors(spec.sheet, spec.row, len(frames))
        if species.size != 1:
            anims[name] = anims[name].scaled(species.size)
    return anims


MAX_LEVEL = 100


def line_base(species: str) -> str:
    """The first species of `species`'s evolution line (Metapod → Caterpie)."""
    earlier = _EVOLVES_FROM
    while species in earlier:
        species = earlier[species]
    return species


def xp_for_level(level: int) -> int:
    """Total XP needed to reach `level` (Gen 1's "medium fast" growth rate)."""
    return 0 if level <= 1 else level ** 3


def _stat(base: int, level: int) -> int:
    # The Gen 1 formula without IVs/EVs.
    return base * 2 * level // 100 + 5


@dataclass
class Monster:
    """One Pokémon: its species, level, XP, current HP, status, equipped
    gear, the talents picked (keys, from its line's `TalentTree`) and the
    moves it has equipped (its known moves come with its level)."""
    species: Species
    level: int
    hp: int = -1  # -1 = full
    gear: dict[str, Gear] = field(default_factory=dict)  # slot -> gear
    status: str = ""       # a key of status.STATUSES, or "" for none
    sleep_rounds: int = 0  # rounds left asleep
    xp: int = -1  # total; -1 = just reached its level
    talents: list[str] = field(default_factory=list)   # talent keys picked (one per tier at most)
    equipped: list[str] = field(default_factory=list)  # keys of the moves it uses, besides Fight
    scale: int = 1  # drawn this many times bigger (bosses); not saved

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.max_hp
        if self.xp < 0:
            self.xp = xp_for_level(self.level)
        known = self.known
        self.equipped = [k for k in dict.fromkeys(self.equipped) if k in known and k != self.tree.basic.key]
        self.talents = [k for k in self.talents if self.tree.tier_of(k)]

    @classmethod
    def create(cls, species: str, level: int) -> "Monster":
        """A Pokémon that builds itself (wild ones, trainers', the starter):
        its last 4 moves equipped (as in Gen 1), and a talent in every open
        tier, mostly along one path (picked at random)."""
        monster = cls(SPECIES[species], level)
        known = monster.known[1:]
        monster.equipped = known[-MAX_EQUIPPED:]
        tree = monster.tree
        if tree.paths:
            main = random.randrange(len(tree.paths))
            for tier in range(tree.open_tiers(level)):
                path = main if random.random() < 0.75 else random.randrange(len(tree.paths))
                for p in (path, main, *range(len(tree.paths))):
                    if not tree.why_not(monster.talents, tier, p, level):
                        monster.talents.append(tree.tiers[tier][p].key)
                        break
        return monster

    @property
    def name(self) -> str:
        return self.species.name

    @property
    def alive(self) -> bool:
        return self.hp > 0

    # ------------------------------------------------------ moves and talents

    @property
    def tree(self) -> TalentTree:
        return self.species.tree

    @property
    def known(self) -> list[str]:
        """The keys of the moves it knows (by its level and evolution stage)."""
        return self.tree.known(self.level, self.species.stage)

    def _learn_new(self, before: list[str]) -> list[str]:
        """Moves known now but not in `before`: equipped while there's room.
        Returns their names."""
        new = [k for k in self.known if k not in before]
        for key in new:
            if len(self.equipped) < MAX_EQUIPPED and key != self.tree.basic.key:
                self.equipped.append(key)
        return [self.tree.learned(k).name for k in new]

    @property
    def open_picks(self) -> int:
        """Open tiers without a talent picked (a reminder on the party screen)."""
        picked = self.tree.picks(self.talents)
        return sum(1 for t in range(self.tree.open_tiers(self.level)) if t not in picked)

    def why_not(self, tier: int, path: int) -> str:
        """Why the talent at (`tier`, `path`) can't be picked ("" if it can)."""
        return self.tree.why_not(self.talents, tier, path, self.level)

    def pick(self, tier: int, path: int) -> bool:
        """Pick a tier's talent (in place of the tier's other pick). Picks
        in later tiers that need this path's earlier talents and no longer
        have them are taken back."""
        if self.why_not(tier, path):
            return False
        tree = self.tree
        self.talents = [k for k in self.talents if tree.tier_of(k)[0] != tier] + [tree.tiers[tier][path].key]
        while True:  # (taking one back can leave another without what it needs)
            bad = [k for k in self.talents if tree.why_not([o for o in self.talents if o != k], *tree.tier_of(k),
                                                           self.level)]
            if not bad:
                return True
            self.talents.remove(bad[0])

    def reset_talents(self) -> None:
        self.talents = []

    def talent(self, flag: str) -> float:
        """The value of a talent's battle effect (`Talent.flags`), 0 if it has
        none. Talents with the same effect don't add up: the strongest counts
        (Fortress after Shell Formation, Unbreakable after Tenacity, ...)."""
        return max((v for t in self.tree.chosen_talents(self.talents) for f, v in t.flags if f == flag), default=0)

    def move(self, key: str) -> Move:
        """Move `key`, as its talents change it."""
        return self.tree.effective_move(self.talents, key)

    @property
    def basic_attack(self) -> Move:
        """What Fight does: the first move it knows."""
        return self.move(self.tree.basic.key)

    @property
    def moves(self) -> list[Move]:
        """The equipped moves (the battle's Skills menu)."""
        known = self.known
        return [self.move(key) for key in self.equipped if key in known]

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

    def evolve(self) -> list[str]:
        """Become what its species evolves into. Like a level up, the HP it
        gains is added to its current HP."""
        missing, before = self.max_hp - self.hp, self.known
        self.species = SPECIES[self.species.evolution.into]
        self._set_missing_hp(missing)
        return self._learn_new(before)

    def level_up(self) -> list[str]:
        """One level up. The HP it gains is added to its current HP, so the
        damage taken stays the same. Returns the names of moves it learns."""
        missing, before = self.max_hp - self.hp, self.known
        self.level += 1
        self._set_missing_hp(missing)
        return self._learn_new(before)

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

    def gear_bonus(self, mod: str) -> float:
        """Total of `mod` (see `items.MOD_TEXT`) from equipped gear, and for a
        few battle mods also from talents (Head Start: "first", ...)."""
        total = sum(self.gear[slot].mods.get(mod, 0) for slot in SLOTS if slot in self.gear)
        if self.talents and (mod in TALENT_MODS or mod.startswith("status:")):
            total += self.talent(mod)
        return total

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
