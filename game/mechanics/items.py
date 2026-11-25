"""Items: gear a Pokémon equips, medicine used in battle, and the bag that
holds what the player owns.

Each Pokémon has one slot of each kind in `SLOTS`. A piece of gear is
rolled when it drops: its item's own effect plus a number of random
affixes (prefixes and suffixes, which also name it: "Fierce Red Bandana of
the Aerodactyl"). Its rarity decides how many affixes it gets and multiplies
every rolled bonus (penalties stay as they are). Its item level is the
level needed to equip it, and sets how strong it is (`scale`): the ranges
below are a Lv50 Common item's, and lower levels get a share of them, so
early gear is mild and newer gear of a lower rarity can beat older gear of
a higher one. Every kind of bonus is priced by what it's worth (a bonus
that only works sometimes, like Super effective, gets bigger numbers).
Berries are eaten once per battle (or more, with Seedy) and roll berry
affixes (`BERRY_AFFIXES`) instead of gear's. Hats (the head slot) are drawn on the Pokémon wearing them
(see hats.py).
"""

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import type_chart
from .status import STATUSES
from .type_chart import TYPES

if TYPE_CHECKING:
    from .pokemon import Monster

STATS = ("hp", "attack", "defense", "speed")
STAT_NAMES = {"hp": "HP", "attack": "Attack", "defense": "Defense", "speed": "Speed"}

# Everything gear can change. Stats are in %, crit in % points, power is
# added to the power of damaging moves. Per type: "power:fire" raises the
# damage of Fire moves by %, "added:fire" makes every hit deal that % extra
# as Fire damage (which is super effective, resisted, ... on its own).
# "status:poison" is the % chance that a hit poisons the target.
MOD_TEXT = {
    "hp": "HP {:+d}%",
    "attack": "Attack {:+d}%",
    "defense": "Defense {:+d}%",
    "speed": "Speed {:+d}%",
    "crit": "Crit chance {:+d}%",
    "power": "Move power {:+d}",
    "first": "Act first {:d}%",          # chance to move first in a round
    "endure": "Endure {:d}%",            # chance to survive a knockout hit with 1 HP
    "super": "Super effective {:+d}%",   # more damage on super effective hits
    "regen": "Regen {:d}% HP/round",
    "drain": "Drain {:d}% of damage",    # heals by this share of damage dealt
    # Berries, eaten (at most) once per battle; HP amounts are absolute, like potions':
    "berry_heal": "Heals {:d} HP when low",
    "berry_attack": "Attack +{:d} when low",
    "berry_cure": "{:d}% a round to cure",
    "berry_juicy": "Also heals {:d} HP",
    "berry_lum": "{:d}% to cure any status",
    "berry_regen": "+{:d} HP a round, 3 rounds",
    "berry_seed": "{:d}% not used up",
    "berry_early": "Eaten sooner",
}
for _stat in ("attack", "defense", "speed"):
    MOD_TEXT[f"berry_stage:{_stat}"] = f"Also {STAT_NAMES[_stat]} +{{:d}} stage"
for _t in TYPES:
    MOD_TEXT[f"power:{_t}"] = f"{type_chart.name(_t)} moves {{:+d}}%"
    MOD_TEXT[f"added:{_t}"] = f"Adds {{:d}}% {type_chart.name(_t)}"
for _s in STATUSES.values():
    MOD_TEXT[f"status:{_s.key}"] = f"{_s.name} chance {{:+d}}%"

SLOTS = ("head", "held", "worn", "berry")
SLOT_NAMES = {"head": "Head", "held": "Held", "worn": "Worn", "berry": "Berry"}
AFFIX_SLOTS = ("head", "held", "worn")  # gear affixes; berries roll berry affixes

Range = tuple[int, int]  # a roll's lowest and highest value, at Common


@dataclass(frozen=True)
class Rarity:
    name: str
    factor: float          # multiplies rolled bonuses (not penalties)
    affixes: Range         # how many affixes gear of this rarity gets
    color: tuple[int, int, int]


COMMON = Rarity("Common", 1.0, (0, 0), (240, 240, 248))
UNCOMMON = Rarity("Uncommon", 1.15, (1, 1), (120, 230, 120))
RARE = Rarity("Rare", 1.3, (1, 2), (110, 210, 255))
EPIC = Rarity("Epic", 1.45, (2, 2), (220, 150, 255))
LEGENDARY = Rarity("Legendary", 1.6, (2, 3), (255, 176, 64))
RARITIES = {r.name: r for r in (COMMON, UNCOMMON, RARE, EPIC, LEGENDARY)}
RARITY_ORDER = list(RARITIES)

# Special effects (rather than plain stat bonuses) are weak on everyday gear
# and come into their own on rare gear: instead of the rarity's factor they
# take these.
SPECIAL_MODS = ("first", "endure", "regen", "drain")  # and status:<status>
# Berries' chances: they grow gently with level, like special effects, but
# take the rarity's factor.
BERRY_CHANCES = ("berry_cure", "berry_lum", "berry_seed")
SPECIAL_FACTOR = {"Common": 0.5, "Uncommon": 0.75, "Rare": 1.0, "Epic": 1.5, "Legendary": 2.0}
HEAL_MODS = ("berry_heal", "berry_juicy", "berry_regen")  # absolute HP
# Counts that don't scale (stages, a switch). Liechi's stage: +1 more from Epic up.
FIXED_MODS = ("berry_attack", "berry_early")  # and berry_stage:<stat>
EPIC_STAGE = ("Epic", "Legendary")


def _special(mod: str) -> bool:
    return mod in SPECIAL_MODS or mod.startswith("status:")


def _fixed(mod: str) -> bool:
    return mod in FIXED_MODS or mod.startswith("berry_stage:")


# Item level: the ranges are a Lv50 Common item's (`FULL_LEVEL`). Stats,
# type damage and crit grow gently with the level: ×0.25 at Lv1, ×0.375 at
# Lv50, ×0.5 at Lv100 (`STAT_SCALE`: new gear is better, but a piece
# doesn't double from one area to the next, and a whole set adds about
# +15% damage early and +40% late); chances and other special
# effects as the square root of the level (Lv5: about a third); healing
# berries by HP, like potions (Lv5: a fifth).
FULL_LEVEL = 50
STAT_SCALE = (0.25, 0.25)  # stats, type damage and crit: × (first + second × level / 100)


def scale(mod: str, level: int) -> float:
    """How much item level `level` multiplies `mod`'s range."""
    level = max(1, level)
    if _fixed(mod):
        return 1.0
    if mod in HEAL_MODS:
        return (level + 5) / (FULL_LEVEL + 5)
    if _special(mod) or mod in BERRY_CHANCES:
        return math.sqrt(level / FULL_LEVEL)
    return STAT_SCALE[0] + STAT_SCALE[1] * level / 100


def level_factor(level: int) -> float:
    """How much item level `level` multiplies stat and damage bonuses (Lv50: ×0.9)."""
    return scale("attack", level)


@dataclass(frozen=True)
class Item:
    name: str
    slot: str          # one of SLOTS
    description: str
    mods: dict[str, Range] = field(default_factory=dict, hash=False)  # its own effect
    cures: tuple[str, ...] = ()  # berries: statuses it cures (once per battle)
    sprite: int = -1   # hats: its cell in the hat sheet (hats.SHEET)
    min_rarity: str = "Common"  # it only drops at this rarity or better
    # One of a kind: never rolled as loot or stock; a boss wears it
    # (`Route.boss_wears`), and it always drops when that boss is beaten.
    unique: bool = False

    def drops_at(self, rarity: str) -> bool:
        return not self.unique and RARITY_ORDER.index(rarity) >= RARITY_ORDER.index(self.min_rarity)


TYPE_ITEMS = {  # type -> (held item that powers up its moves, description)
    "normal": ("Silk Scarf", "A sumptuous scarf."),
    "fire": ("Charcoal", "A hot lump of coal."),
    "water": ("Mystic Water", "A teardrop-shaped gem."),
    "electric": ("Magnet", "A powerful magnet."),
    "grass": ("Miracle Seed", "A seed bursting with life."),
    "ice": ("Never-Melt Ice", "A piece of ice that never melts."),
    "fighting": ("Black Belt", "A belt that boosts determination."),
    "poison": ("Poison Barb", "A small, venomous barb."),
    "ground": ("Soft Sand", "Loose, silky sand."),
    "flying": ("Sharp Beak", "A long, sharp beak."),
    "psychic": ("Twisted Spoon", "A spoon imbued with psychic power."),
    "bug": ("Silver Powder", "A shiny silver powder."),
    "rock": ("Hard Stone", "An unbreakable stone."),
    "ghost": ("Spell Tag", "A sinister, eerie tag."),
    "dragon": ("Dragon Fang", "A hard and sharp fang."),
}

# Hats: (cell in the hat sheet, name, description, own effect).
HATS = [
    (16, "Wizard Hat", "A tall, pointed hat full of arcane power.", {"attack": (8, 10), "hp": (7, 9)}),
    (17, "Witch Hat", "Its buckle glints with a sleepy hex.", {"status:sleep": (4, 7)}),
    (19, "Starry Hat", "Stitched with stars that point out weak spots.", {"crit": (8, 10)}),
    (20, "Nightcap", "A cosy cap. Its wearer rests even in battle.", {"regen": (3, 5)}),
    (24, "Mitre", "A tall ceremonial hat that steadies the spirit.", {"hp": (12, 15), "regen": (1, 1)}),
    (26, "Crown", "A crown fit for a champion.", {"attack": (7, 9), "defense": (7, 9)}),
    (27, "Halo", "A glowing ring. Its wearer may hang on with 1 HP.", {"endure": (6, 8)}),
    (28, "Tiara", "A jewelled tiara, light and graceful.", {"hp": (7, 9), "speed": (10, 13)}),
    (29, "Turban", "Thick folds of cloth that soften blows.", {"defense": (14, 18)}),
    (31, "Mortarboard", "A scholar's cap. Its wearer knows every weakness.", {"attack": (8, 10), "crit": (5, 5)}),
    (32, "Archer's Cap", "A feathered cap for sharp-eyed hunters.", {"crit": (5, 5), "speed": (10, 13)}),
    (36, "Headband", "A plain headband tied tight for focus.", {"attack": (7, 9), "speed": (10, 13)}),
    (37, "Tricorne", "A buccaneer's hat. Takes a share of every hit.", {"drain": (6, 10)}),
    (38, "Blue Bandana", "A light bandana for quick getaways.", {"speed": (20, 26)}),
    (39, "Officer's Cap", "Its wearer is always first to act.", {"first": (8, 12)}),
    (40, "Jester's Cap", "Its jingling bells can leave foes stunned.", {"status:paralysis": (5, 8)}),
    (41, "Pirate Hat", "A captain's hat. Bold and ruthless.", {"attack": (10, 12), "crit": (3, 3)}),
    (42, "Red Bandana", "A fiery bandana that boosts strength.", {"attack": (14, 18)}),
    (43, "Plumed Hat", "A dashing, feathered hat.", {"speed": (14, 18), "crit": (3, 3)}),
    (45, "Straw Hat", "A wide hat that keeps its wearer going.", {"hp": (14, 18)}),
    (56, "Visor Helmet", "A sturdy helmet. Tough, but heavy.", {"defense": (26, 34), "speed": (-10, -10)}),
    (61, "Alpine Hat", "A warm hat for long climbs.", {"hp": (7, 9), "defense": (7, 9)}),
    (62, "Fez", "A smart hat with a tassel. It sharpens the aim.", {"crit": (6, 8), "attack": (4, 5)}),
    (63, "Sultan's Turban", "A grand turban with a healing jewel.", {"hp": (9, 11), "regen": (2, 3)}),
]

ITEMS = {i.name: i for i in [
    # Head: hats.
    *(Item(name, "head", description, mods, sprite=cell, min_rarity="Epic" if "endure" in mods else "Common")
      for cell, name, description, mods in HATS),
    # Tony's (the skate road's boss): one of a kind.
    Item("Bike Helmet", "head", "Tony's own helmet, scuffed from a thousand wipeouts. Nothing gets through it.",
         {"defense": (30, 36), "hp": (18, 22)}, sprite=64, unique=True),
    # Held: type items and battle tools.
    *(Item(name, "held", f"{description} Powers up {type_chart.name(t)} moves.", {f"power:{t}": (18, 24)})
      for t, (name, description) in TYPE_ITEMS.items()),
    Item("Quick Claw", "held", "A light, sharp claw. Its holder may move first.", {"first": (12, 18)}),
    Item("Leftovers", "held", "Restores a little HP every round.", {"regen": (4, 6)}),
    Item("Shell Bell", "held", "Restores HP when its holder deals damage.", {"drain": (8, 12)}),
    Item("Scope Lens", "held", "A lens that spots weak points.", {"crit": (8, 10)}),
    # Worn: bands, belts and vests.
    Item("Muscle Band", "worn", "A headband that boosts strength.", {"attack": (14, 18)}),
    Item("Assault Vest", "worn", "A sturdy vest for the front line.", {"defense": (14, 18)}),
    Item("Choice Scarf", "worn", "A scarf that makes its wearer quicker.", {"speed": (20, 26)}),
    Item("Focus Band", "worn", "Its wearer may hang on with 1 HP after a knockout hit.", {"endure": (6, 8)},
         min_rarity="Epic"),
    Item("Expert Belt", "worn", "A well-worn belt for all-round fighters.", {"attack": (8, 10), "defense": (8, 10)}),
    Item("Power Bracer", "worn", "A heavy bracer. Strong, but slow.", {"attack": (26, 34), "speed": (-10, -10)}),
    Item("Power Belt", "worn", "A heavy belt. Tough, but slow.", {"defense": (26, 34), "speed": (-10, -10)}),
    # Berries: eaten (at most) once per battle, when they're needed. Cure
    # berries get a chance every round their holder has the status.
    Item("Oran Berry", "berry", "Restores HP when its holder is at half HP or less.", {"berry_heal": (20, 24)}),
    Item("Liechi Berry", "berry", "Raises Attack when its holder is at 1/4 HP or less.", {"berry_attack": (1, 1)}),
    Item("Pecha Berry", "berry", "May cure poison.", {"berry_cure": (30, 40)}, cures=("poison",)),
    Item("Rawst Berry", "berry", "May heal a burn.", {"berry_cure": (30, 40)}, cures=("burn",)),
    Item("Cheri Berry", "berry", "May cure paralysis.", {"berry_cure": (30, 40)}, cures=("paralysis",)),
    Item("Chesto Berry", "berry", "May wake its holder up.", {"berry_cure": (30, 40)}, cures=("sleep",)),
    Item("Aspear Berry", "berry", "May thaw its holder out.", {"berry_cure": (30, 40)}, cures=("freeze",)),
    Item("Lum Berry", "berry", "May cure any status.", {"berry_cure": (15, 20)}, cures=tuple(STATUSES)),
]}


@dataclass(frozen=True)
class Affix:
    """A random bonus on gear. Prefixes go before the item's name, suffixes
    after it; suffixes are named after Pokémon known for those stats."""
    name: str
    prefix: bool
    mods: dict[str, Range] = field(hash=False)
    weight: int = 3   # how likely it is to be rolled, relative to the others


# Prefixes that add type damage, and suffixes that power up a type's moves.
TYPE_AFFIXES = {  # type -> (prefix, suffix)
    "normal": (None, "of the Kangaskhan"),  # Normal damage on hits would add nothing
    "fire": ("Blazing", "of the Moltres"),
    "water": ("Drenching", "of the Gyarados"),
    "electric": ("Shocking", "of the Zapdos"),
    "grass": ("Thorny", "of the Venusaur"),
    "ice": ("Frozen", "of the Articuno"),
    "fighting": ("Brawling", "of the Hitmonchan"),
    "poison": ("Venomous", "of the Arbok"),
    "ground": ("Quaking", "of the Dugtrio"),
    "flying": ("Soaring", "of the Fearow"),
    "psychic": ("Mystic", "of the Alakazam"),
    "bug": ("Stinging", "of the Beedrill"),
    "rock": ("Jagged", "of the Aerodactyl"),
    "ghost": ("Haunted", "of the Gengar"),
    "dragon": ("Draconic", "of the Dragonite"),
}

# Suffixes that give hits a chance to inflict a status, named after
# Pokémon known for it.
STATUS_AFFIXES = {
    "burn": ("of the Magmar", (5, 10)),
    "poison": ("of the Muk", (5, 10)),
    "paralysis": ("of the Pikachu", (5, 10)),
    "sleep": ("of the Hypno", (3, 6)),
    "freeze": ("of the Jynx", (3, 6)),
}

AFFIXES = [  # about a third of an item's own effect
    Affix("Fierce", True, {"attack": (5, 6)}),
    Affix("Sturdy", True, {"defense": (5, 6)}),
    Affix("Swift", True, {"speed": (7, 9)}),
    Affix("Hearty", True, {"hp": (5, 6)}),
    Affix("Keen", True, {"crit": (3, 4)}),
    Affix("Hasty", True, {"first": (3, 6)}, weight=2),
    Affix("Draining", True, {"drain": (3, 6)}, weight=2),
    Affix("of the Machamp", False, {"attack": (5, 6)}),
    Affix("of the Onix", False, {"defense": (5, 6)}),
    Affix("of the Pidgeot", False, {"speed": (7, 9)}),
    Affix("of the Snorlax", False, {"hp": (5, 6)}),
    Affix("of the Tauros", False, {"attack": (3, 3), "speed": (4, 4)}),
    Affix("of the Golem", False, {"defense": (3, 3), "hp": (3, 3)}),
    Affix("of the Scyther", False, {"crit": (3, 3), "attack": (3, 3)}),
    Affix("of the Chansey", False, {"regen": (2, 3)}, weight=2),
    *(Affix(suffix, False, {f"power:{t}": (6, 8)}, weight=1)
      for t, (_, suffix) in TYPE_AFFIXES.items()),
    *(Affix(suffix, False, {f"status:{s}": chance}, weight=1)
      for s, (suffix, chance) in STATUS_AFFIXES.items()),
]

# Berries' affixes: extra effects when the berry is eaten (more of them on
# rarer berries, as gear's).
BERRY_AFFIXES = [
    Affix("Juicy", True, {"berry_juicy": (10, 12)}),
    Affix("Bitter", True, {"berry_lum": (30, 40)}),
    Affix("Spicy", True, {"berry_stage:attack": (1, 1)}),
    Affix("Dry", True, {"berry_stage:defense": (1, 1)}),
    Affix("Sweet", True, {"berry_stage:speed": (1, 1)}),
    Affix("of the Vileplume", False, {"berry_regen": (5, 6)}),
    Affix("of the Exeggcute", False, {"berry_seed": (20, 30)}, weight=2),
    Affix("of the Jolteon", False, {"berry_early": (1, 1)}),
]


def affixes_for(slot: str) -> list[Affix]:
    """The affixes gear of `slot` can roll."""
    return BERRY_AFFIXES if slot == "berry" else AFFIXES if slot in AFFIX_SLOTS else []


AFFIX_BY_NAME = {a.name: a for a in AFFIXES + BERRY_AFFIXES}


def _pick_affixes(count: int, rng: random.Random, pool: list[Affix] | None = None) -> list[Affix]:
    """`count` different affixes of `pool` (gear's), picked by weight."""
    pool, picked = list(AFFIXES if pool is None else pool), []
    for _ in range(min(count, len(pool))):
        affix = rng.choices(pool, weights=[a.weight for a in pool])[0]
        pool.remove(affix)
        picked.append(affix)
    return picked


def _roll(mods: dict[str, Range], rarity: Rarity, level: int, rng: random.Random,
          values: str = "random") -> dict[str, int]:
    """Roll each mod's value in its range ("min"/"max" values: the lowest or
    highest instead), then apply the item level (`scale`) and the rarity
    (special effects: `SPECIAL_FACTOR`). Penalties only follow the level."""
    rolled = {}
    for mod, (low, high) in mods.items():
        value = low if values == "min" else high if values == "max" else rng.randint(low, high)
        if _fixed(mod):
            value += 1 if mod == "berry_attack" and rarity.name in EPIC_STAGE else 0
        elif value > 0:
            factor = SPECIAL_FACTOR[rarity.name] if _special(mod) else rarity.factor
            value = max(1, round(value * factor * scale(mod, level)))
        else:
            value = min(-1, round(value * scale(mod, level)))
        rolled[mod] = value
    return rolled


# --- special effects (rare gear's "red text") ----------------------------------
# Now and then a Rare piece or better rolls one of these on top of its
# mods: not a bigger number, but a change in how its wearer fights, like a
# talent (and written the same way: move changes by selector, and battle
# flags; see talents.py). They work for any wearer: their selectors pick
# moves by kind ("basic", "damaging", "status_moves"), not by name.

@dataclass(frozen=True)
class GearEffect:
    key: str
    name: str    # shown in red, as the effect's title
    text: str    # what it does
    quote: str   # its line of flavour, in red
    moves: tuple[tuple[str, dict], ...] = field(default=(), hash=False)  # (selector, Move field changes)
    flags: tuple[tuple[str, float], ...] = ()  # battle effects, as `Talent.flags`


def _effect(name: str, text: str, quote: str, *moves: tuple[str, dict], **flags: float) -> GearEffect:
    return GearEffect(name.lower().replace(" ", "_").replace("'", ""), name, text, quote, tuple(moves),
                      tuple((f.replace("__", ":"), v) for f, v in flags.items()))


GEAR_EFFECTS = {e.key: e for e in [
    _effect("Earthshaker", "The basic attack hits every enemy, the others at 50% damage.",
            "Why hit one when you can hit them all?", ("basic", {"spread": True, "spread_share": 0.5})),
    _effect("Double Tap", "The basic attack hits twice, at 65% power each.", "Two for the price of one.",
            ("basic", {"hits": (2, 2), "scale": -0.35})),
    _effect("Megaphone", "The wearer's status moves work on every Pokémon on the side they aim at (on two or more enemies, each at half the chance).",
            "CAN YOU HEAR ME IN THE BACK?", ("status_moves", {"spread": True})),
    _effect("Ricochet", "The wearer's damaging moves also hit an enemy next to the target, at half damage.",
            "Nobody stands next to me twice.", ("damaging", {"reach": 0.5})),
    _effect("Quickdraw", "The wearer's damaging moves always go first.", "Fastest paws in Kanto.",
            ("damaging", {"priority": 1})),
    _effect("Executioner", "The wearer's damaging moves are always critical hits on a target below 1/3 HP.",
            "It's nothing personal.", ("damaging", {"keen": 1 / 3})),
    _effect("Armor Breaker", "The wearer's damaging moves have a 30% chance to lower the target's Defense.",
            "Knock knock.", ("damaging", {"stages": (("defense", -1),), "stage_chance": 30})),
    _effect("Thornmail", "Whoever hits the wearer loses 1/8 of its max HP.", "Look, but don't touch.",
            thorns=1 / 8),
    _effect("Phoenix Feather", "Once a battle, ending a round below 1/3 HP heals the wearer half its max HP.",
            "Not today.", second_wind=0.5),
    _effect("Storm Cell", "Whoever hits the wearer has a 30% chance to be paralyzed.", "Shocking, really.",
            retaliate__paralysis=30),
    _effect("Plague Charm", "At the start of each battle, each enemy has a 40% chance to be poisoned.",
            "Something's in the air.", aura__poison=40),
    _effect("Dread Mask", "At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage.", "Everyone flinched.",
            lower__attack=1),
    _effect("Hunter's Mark", "The wearer's moves deal 50% more to a target that hasn't moved this round.",
            "Strike first. Strike hard.", ambush=0.5),
    _effect("Pack Tactics", "The wearer's moves deal 40% more to a target a partner already hit this round.",
            "Together, we bite.", gang=0.4),
    _effect("Gale Banner", "The wearer's moves that hit every enemy deal 40% more.", "Let the wind carry it.",
            wide=0.4),
    _effect("Rallying Cry", "The wearer's whole side heals 1/16 of its max HP at the end of each round.",
            "Hold the line!", party_regen=6.25),
    _effect("Aegis", "While the wearer stands, its whole side takes 20% less damage.", "Behind me!",
            ancient_roots=0.2),
    _effect("Last Rites", "Once a battle, a partner that would faint keeps 1 HP and is healed half its max HP.", "Not on my watch.", world_tree=1, guard_heal=0.5),
]}
# The chance a piece rolls one, by rarity (none below Rare).
EFFECT_CHANCE = {"Rare": 10, "Epic": 20, "Legendary": 40}
EFFECT_VALUE = 1.5  # a piece with one is worth (and costs) this much more
EFFECT_COLOR = (235, 70, 60)  # their text's red


@dataclass(frozen=True)
class Roll:
    """One rolled part of a piece of gear: its item's own effect (no affix),
    or one affix."""
    affix: Affix | None
    mods: dict[str, int] = field(hash=False)


@dataclass(eq=False)  # two copies of the same gear are still different pieces
class Gear:
    """One piece of gear the player owns: an item at a rarity and an item
    level (the level needed to equip it), with its rolls."""
    item: Item
    rarity: Rarity
    rolls: list[Roll]
    level: int = 1
    effect: str = ""  # a special effect (`GEAR_EFFECTS` key), if it rolled one
    plus: int = 0     # enhancements by the smith (0 to `MAX_PLUS`): each raises its bonuses `PLUS_BOOST`

    @classmethod
    def roll(cls, item: str, rarity: str = "Common", rng: random.Random | None = None,
             affixes: list[str] | None = None, values: str = "random", level: int = 1,
             effect: str | None = None) -> "Gear":
        """Roll a new piece at item level `level`. `affixes` picks its
        affixes by name instead of at random; `values` "min" or "max" gives
        every roll its lowest or highest value; `effect` picks its special
        effect ("" none) instead of rolling for one (`EFFECT_CHANCE`; these
        are for testing, see dev.py)."""
        rng = rng or random.Random()
        item_, rarity_ = ITEMS[item], RARITIES[rarity]
        rolls = [Roll(None, _roll(item_.mods, rarity_, level, rng, values))] if item_.mods else []
        if affixes is not None:
            picked = [AFFIX_BY_NAME[name] for name in affixes]
        elif affixes_for(item_.slot):
            picked = _pick_affixes(rng.randint(*rarity_.affixes), rng, affixes_for(item_.slot))
        else:
            picked = []
        for affix in picked:
            rolls.append(Roll(affix, _roll(affix.mods, rarity_, level, rng, values)))
        if effect is None:  # (rolled last, so a piece's mods come out as they always have from an rng)
            effect = (rng.choice(sorted(GEAR_EFFECTS)) if rng.random() * 100 < EFFECT_CHANCE.get(rarity, 0) else "")
        return cls(item_, rarity_, rolls, level, effect)

    @property
    def special(self) -> GearEffect | None:
        """Its special effect, if it has one."""
        return GEAR_EFFECTS.get(self.effect)

    @property
    def name(self) -> str:
        """The item's name, with its first prefix and first suffix."""
        prefix = next((r.affix.name for r in self.rolls if r.affix and r.affix.prefix), None)
        suffix = next((r.affix.name for r in self.rolls if r.affix and not r.affix.prefix), None)
        return " ".join(p for p in (prefix, self.item.name, suffix, self.plus and f"+{self.plus}") if p)

    @property
    def slot(self) -> str:
        return self.item.slot

    def usable_by(self, monster: "Monster") -> bool:
        """Whether `monster` is a high enough level to equip it."""
        return monster.level >= self.level

    @property
    def value(self) -> int:
        """What it's worth: by rarity, growing with its item level (`GEAR_PRICE`)."""
        worth = gear_price(self.rarity.name, self.level) * (EFFECT_VALUE if self.effect else 1) * (1 + PLUS_VALUE * self.plus)
        return round(worth / 10) * 10

    @property
    def price(self) -> int:
        """What Persian (a Poké Mart's gear counter) asks for it: far more
        than it's worth (`GEAR_MARKUP`), so gear is mostly won, not bought."""
        return self.value * GEAR_MARKUP

    @property
    def sell_price(self) -> int:
        """What Persian pays for it: half what it's worth, as for medicine."""
        return self.value // 2

    @property
    def mods(self) -> dict[str, int]:
        """All of its rolls added up; its enhancements raise the bonuses."""
        total: dict[str, int] = {}
        for roll in self.rolls:
            for mod, value in roll.mods.items():
                total[mod] = total.get(mod, 0) + value
        return {mod: enhanced(value, self.plus) for mod, value in total.items()} if self.plus else total

    # --- the smith (scenes/smith.py): salvage and enhancement

    @property
    def material(self) -> str:
        """What salvaging it gives, and what enhancing it costs: its rarity's material."""
        return MATERIALS[self.rarity.name]

    def enhance_cost(self, step: int | None = None) -> int:
        """Materials to take it to +`step` (the next one by default):
        `PLUS_COST` × `step` × (1 + item level // 25)."""
        step = self.plus + 1 if step is None else step
        return PLUS_COST * step * (1 + self.level // 25)

    @property
    def salvage_yield(self) -> int:
        """Materials salvaging it gives: 1 + item level // 25, and half of
        what its enhancements cost."""
        spent = sum(self.enhance_cost(n) for n in range(1, self.plus + 1))
        return 1 + self.level // 25 + spent // 2


def enhanced(value: int, plus: int) -> int:
    """A mod's value at +`plus`: bonuses × (1 + `PLUS_BOOST` × plus), rounded
    half up (so a small bonus only grows at the higher +s); penalties stay."""
    if value <= 0 or not plus:
        return value
    return math.floor(value * (1 + PLUS_BOOST * plus) + 0.5)


# Salvage and enhancement (the smith's, after his quest): breaking a piece
# down gives its rarity's material; enhancing a piece (+1 to +MAX_PLUS)
# costs its own rarity's material. Four of one smelt into one of the next.
MATERIALS = {"Common": "Scrap", "Uncommon": "Alloy", "Rare": "Crystal", "Epic": "Ether", "Legendary": "Star Shard"}
MAX_PLUS = 5
PLUS_BOOST = 0.05   # each enhancement: bonuses +5% (of the piece's own)
PLUS_COST = 2       # materials per step: PLUS_COST × step × (1 + item level // 25)
PLUS_VALUE = 0.15   # ... and its worth +15%
SMELT = 4           # materials of one kind that smelt into one of the next
# What the Celadon Department Store's 4F sells the first three for (the rarer
# ones only come from salvage and smelting).
MATERIAL_PRICE = {"Scrap": 300, "Alloy": 1000, "Crystal": 3000}


# Gear's worth: a Lv5 piece of each rarity is worth about this; it grows
# with the item level, (level + 10) / 15 times (Lv20: ×2, Lv35: ×3), rounded
# to ₽10. Persian sells gear for `GEAR_MARKUP` times its worth (it should
# take some grinding to buy) and buys it for half its worth.
GEAR_PRICE = {"Common": 200, "Uncommon": 500, "Rare": 1200, "Epic": 3000, "Legendary": 8000}
GEAR_MARKUP = 5


def gear_price(rarity: str, level: int) -> int:
    return round(GEAR_PRICE[rarity] * (max(1, level) + 10) / 15 / 10) * 10


@dataclass(frozen=True)
class Medicine:
    """An item used up to heal one of your own Pokémon (in battle, for now),
    or (`escape`) the Escape Rope, used on the map from the pause menu."""
    name: str
    description: str
    price: int              # in Poké Dollars, at a Poké Mart; it sells for half
    hp: int = 0             # HP restored
    fraction: float = 0.0   # ... or this share of max HP, if that's more
    revive: bool = False    # only works on (and revives) a fainted Pokémon
    cures: tuple[str, ...] = ()  # statuses it cures
    escape: bool = False    # Escape Rope: back to the last town or Pokémon Center (not in battle)
    valuable: bool = False  # only worth money (the Nugget): sold at a Poké Mart, never used
    repel: int = 0          # Repel: steps it keeps weaker wild packs away for (used from the bag, not in battle)

    @property
    def sell_price(self) -> int:
        return self.price // 2

    def heal_amount(self, monster: "Monster") -> int:
        amount = max(self.hp, math.ceil(monster.max_hp * self.fraction))
        return min(amount, monster.max_hp - monster.hp)

    def cures_status(self, monster: "Monster") -> bool:
        return monster.status in self.cures

    def has_effect(self, monster: "Monster") -> bool:
        if self.revive == monster.alive:  # Revive only on the fainted, the rest only on the standing
            return False
        return bool(self.heal_amount(monster)) or self.cures_status(monster)

    def use_on(self, monster: "Monster") -> str:
        """Used outside battle (from the bag): heal and cure `monster` (it
        must have an effect). Returns what happened."""
        amount = self.heal_amount(monster)
        notes = []
        if self.cures_status(monster):
            notes.append(STATUSES[monster.status].cured.format(monster.name))
            monster.cure()
        if amount:
            revived = not monster.alive
            monster.hp += amount
            notes.insert(0, f"{monster.name} was revived!" if revived else f"{monster.name} recovered {amount} HP!")
        return " ".join(notes)


# Prices are half of Gen 1's (money only comes from quests so far).
MEDICINE = {m.name: m for m in [
    Medicine("Potion", "Restores 20 HP.", 150, hp=20),
    Medicine("Super Potion", "Restores 50 HP.", 350, hp=50),
    Medicine("Hyper Potion", "Restores 200 HP.", 750, hp=200),
    Medicine("Max Potion", "Fully restores HP.", 1250, fraction=1.0),
    Medicine("Full Restore", "Fully restores HP and cures any status.", 1500, fraction=1.0,
             cures=tuple(STATUSES)),
    Medicine("Revive", "Revives a fainted Pokémon with half its HP.", 750, fraction=0.5, revive=True),
    # The Celadon Department Store's rooftop vending machines (Gen 1's drinks).
    Medicine("Fresh Water", "Mineral water. Restores 50 HP.", 200, hp=50),
    Medicine("Soda Pop", "A fizzy soda. Restores 60 HP.", 300, hp=60),
    Medicine("Lemonade", "A very sweet drink. Restores 80 HP.", 350, hp=80),
    Medicine("Antidote", "Cures poison.", 50, cures=("poison",)),
    Medicine("Burn Heal", "Heals a burn.", 125, cures=("burn",)),
    Medicine("Paralyze Heal", "Cures paralysis.", 100, cures=("paralysis",)),
    Medicine("Awakening", "Wakes up a sleeping Pokémon.", 100, cures=("sleep",)),
    Medicine("Ice Heal", "Thaws out a frozen Pokémon.", 125, cures=("freeze",)),
    Medicine("Full Heal", "Cures any status.", 300, cures=tuple(STATUSES)),
    Medicine("Escape Rope", "Leads back to the last town or Pokémon Center (pause menu, on a route).", 275,
             escape=True),
    # Repels, as in Gen 1: by steps (a tile walked on a route or in a dungeon); a new one replaces what's left.
    Medicine("Repel", "Wild packs weaker than your lead (its level above all of theirs) let you pass: 100 steps.",
             175, repel=100),
    Medicine("Super Repel", "Wild packs weaker than your lead let you pass: 200 steps.", 250, repel=200),
    Medicine("Max Repel", "Wild packs weaker than your lead let you pass: 250 steps.", 350, repel=250),
    Medicine("Nugget", "A nugget of pure gold. Sells for ₽5,000 at a Poké Mart.", 10000, valuable=True),
]}
ESCAPE_ROPE = "Escape Rope"

BONE = "Thick Bone"  # what the smith's hammer is made of (from the Pokémon Tower's Marowak, later)
RIBBON = "Teamwork Ribbon"  # a key item used up from the bag: one more place in the party (Game.slots)
STACKING = {RIBBON}  # key items one can hold more than one of

# Key items (`Bag.key_items`): story items from quests, never sold or used
# up, except an evolution item, used up by evolving (from the bag or the
# party screen; see quests.item_evolves).
KEY_ITEMS = {
    "Oak's Parcel": "A parcel for Professor Oak, from the Viridian Poké Mart.",
    "Pokédex": "Professor Oak's high-tech encyclopedia of Pokémon.",
    "Boulder Badge": "The Boulder Gang's badge, from the Pewter Gym.",
    "Cascade Badge": "The Cascade Crew's badge, from the Cerulean Gym.",
    "Thunder Badge": "The Thunder Battalion's badge, from the Vermilion Gym.",
    "Rainbow Badge": "The Blossom Troupe's badge, from the Celadon Gym.",
    "Soul Badge": "The Ninja Clan's badge, from the Fuchsia Gym.",
    "Marsh Badge": "The Mind Circle's badge, from the Saffron Gym.",
    "Leaf Stone": "A stone with a leaf pattern. It evolves Gloom, Weepinbell and Exeggcute. Used up.",
    "Moon Stone": "A stone as black as the night sky, faintly glittering. It evolves Nidorina, Nidorino, "
                  "Clefairy and Jigglypuff. Used up.",
    "Thunder Stone": "A stone with a lightning-bolt pattern, warm to the touch. It evolves Pikachu. Used up.",
    "Fire Stone": "A stone that glows like embers. It evolves Growlithe. Used up.",
    "Water Stone": "A clear blue stone, cool as a mountain spring. It evolves Shellder and Staryu. Used up.",
    "S.S. Ticket": "A ticket for the S.S. Anne, from Bill. The ship docks at Vermilion City.",
    "HM01 Cut": "A hidden machine from the S.S. Anne's Captain. Its technique, Cut, clears small trees out of the "
                "way, like the one over the Vermilion Gym's door.",
    "Lift Key": "A key with a big \"R\" on it. It works the lift down to the Boss's office in Team Rocket's "
                "Hideout.",
    "Poké Flute": "A flute from Mr. Fuji. Its tune wakes even the deepest sleeper.",
    "Silph Scope": "A scope made by Silph Co. It makes unseen things visible: even ghosts can't hide from it.",
    "Card Key": "A Silph Co. key card. It opens the locked floors of the Silph Co. tower in Saffron City.",
    BONE: "A huge, heavy bone, harder than stone. It must have belonged to a mighty Pokémon. Surely someone "
          "could put it to good use...",
    RIBBON: "A special ribbon, given for proving your team. Use it (here, in Key items): one more Pokémon "
            "can fight at your side. Then fill the new place with Mr. Mime, at any Recruitment Center.",
    "HM05 Flash": "A hidden machine from Professor Oak's aide on Route 2. Its technique, Flash, lights up dark "
                  "caves.",
    "Metapod Shell": "An empty Metapod shell, hard as steel. Use it on a Caterpie at Lv7 or higher: it evolves "
                     "into Metapod.",
    "Kakuna Shell": "An empty Kakuna shell, still smelling of poison. Use it on a Weedle at Lv7 or higher: it "
                    "evolves into Kakuna.",
}


def mod_text(mod: str, value: int) -> str:
    return MOD_TEXT[mod].format(value)


def boosted(value: int, percent: int) -> int:
    """`value` changed by `percent`, by at least 1 so gear matters at low levels."""
    if not percent:
        return value
    change = round(value * percent / 100)
    change = max(1, change) if percent > 0 else min(-1, change)
    return max(1, value + change)


def money_text(amount: int) -> str:
    """Poké Dollars as shown, e.g. "₽1,200"."""
    return f"₽{amount:,}"


GEAR_VERSION = 4  # saved gear from before version 4 was rolled under older rules (4: the gear rework)


def updated_gear(gear: Gear, rng: random.Random | None = None) -> Gear:
    """Gear rolled under older rules, rolled again under today's: the same
    item (or, if it can't drop at its rarity any more, e.g. Endure below
    Epic, another of the same slot), rarity, level and affixes, with new
    values. Its affixes come to as many as its rarity gives today: the
    first ones kept, the gaps (affixes the game no longer has) filled at
    random."""
    rng = rng or random.Random()
    item = gear.item
    if not item.drops_at(gear.rarity.name):
        item = ITEMS[rng.choice([n for n, i in ITEMS.items() if i.slot == item.slot and i.drops_at(gear.rarity.name)])]
    pool = affixes_for(item.slot)
    names = {a.name for a in pool}
    affixes = [r.affix.name for r in gear.rolls if r.affix and r.affix.name in names]
    low, high = gear.rarity.affixes if pool else (0, 0)
    old_count = sum(1 for r in gear.rolls if r.affix)
    want = max(low, min(high, old_count))
    affixes = affixes[:want]
    if len(affixes) < want:
        rest = [a for a in pool if a.name not in affixes]
        affixes += [a.name for a in _pick_affixes(want - len(affixes), rng, rest)]
    return Gear.roll(item.name, gear.rarity.name, rng, affixes=affixes, level=gear.level, effect=gear.effect)


@dataclass
class Bag:
    """Everything the player carries that isn't equipped."""
    gear: list[Gear] = field(default_factory=list)
    medicine: Counter = field(default_factory=Counter)  # name -> how many
    key_items: list[str] = field(default_factory=list)  # story items (Oak's Parcel): never used up or sold
    money: int = 0  # Poké Dollars
    materials: Counter = field(default_factory=Counter)  # the smith's materials (`MATERIALS`): name -> how many
    gems: Counter = field(default_factory=Counter)  # the Battle Tower's gems (world/tower.GEMS): name -> how many

    def add_medicine(self, name: str, count: int = 1) -> None:
        self.medicine[MEDICINE[name].name] += count

    def use_medicine(self, name: str) -> None:
        self.medicine[name] -= 1
        if not self.medicine[name]:
            del self.medicine[name]

    def add(self, gear: Gear) -> None:
        self.gear.append(gear)

    def equip(self, monster: "Monster", gear: Gear) -> bool:
        """Move `gear` from the bag onto `monster` (if its level allows);
        what it wore there comes back."""
        if not gear.usable_by(monster):
            return False
        self.gear.remove(gear)
        old = monster.equip(gear)
        if old:
            self.gear.append(old)
        return True

    def unequip(self, monster: "Monster", slot: str) -> None:
        old = monster.unequip(slot)
        if old:
            self.gear.append(old)
