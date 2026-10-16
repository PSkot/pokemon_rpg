"""Items: gear a Pokémon equips, medicine used in battle, and the bag that
holds what the player owns.

Each Pokémon has one slot of each kind in `SLOTS`. A piece of gear is
rolled when it drops: its item's own effect plus a number of random
affixes (prefixes and suffixes, which also name it: "Fierce Red Bandana of
the Aerodactyl"). Its rarity decides how many affixes it gets and multiplies
every rolled bonus (penalties stay as they are). Its item level is the
level needed to equip it, and makes stat, power and damage bonuses bigger
(`level_factor`), so newer gear of a lower rarity can beat older gear of a
higher one. Hats (the head slot) are drawn on the Pokémon wearing them
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
    # Berries, eaten once per battle:
    "berry_heal": "Heals {:d}% at half HP",
    "berry_attack": "Attack +{:d} at 1/4 HP",
}
for _t in TYPES:
    MOD_TEXT[f"power:{_t}"] = f"{type_chart.name(_t)} moves {{:+d}}%"
    MOD_TEXT[f"added:{_t}"] = f"Adds {{:d}}% {type_chart.name(_t)}"
for _s in STATUSES.values():
    MOD_TEXT[f"status:{_s.key}"] = f"{_s.name} chance {{:+d}}%"

SLOTS = ("head", "held", "worn", "berry")
SLOT_NAMES = {"head": "Head", "held": "Held", "worn": "Worn", "berry": "Berry"}
AFFIX_SLOTS = ("head", "held", "worn")  # berries only have their own effect

Range = tuple[int, int]  # a roll's lowest and highest value, at Common


@dataclass(frozen=True)
class Rarity:
    name: str
    factor: float          # multiplies rolled bonuses (not penalties)
    affixes: Range         # how many affixes gear of this rarity gets
    color: tuple[int, int, int]


COMMON = Rarity("Common", 1.0, (0, 0), (240, 240, 248))
UNCOMMON = Rarity("Uncommon", 1.25, (1, 1), (120, 230, 120))
RARE = Rarity("Rare", 1.5, (2, 3), (110, 210, 255))
EPIC = Rarity("Epic", 2.0, (3, 4), (220, 150, 255))
LEGENDARY = Rarity("Legendary", 2.5, (4, 5), (255, 176, 64))
RARITIES = {r.name: r for r in (COMMON, UNCOMMON, RARE, EPIC, LEGENDARY)}

# Item level: bonuses to stats, move power and damage grow by this much
# per level above 1 (`level_factor`). Chances (act first, endure, status,
# crit), regen, drain and berry effects only grow with rarity.
LEVEL_GROWTH = 0.04
LEVEL_SCALED = {"hp", "attack", "defense", "speed", "power", "super"}  # and power:<type>, added:<type>


def level_factor(level: int) -> float:
    """How much an item level multiplies the bonuses it scales: Lv1 ×1, Lv26 ×2, Lv51 ×3."""
    return 1 + LEVEL_GROWTH * (max(1, level) - 1)


def _level_scaled(mod: str) -> bool:
    return mod in LEVEL_SCALED or mod.startswith(("power:", "added:"))


@dataclass(frozen=True)
class Item:
    name: str
    slot: str          # one of SLOTS
    description: str
    mods: dict[str, Range] = field(default_factory=dict, hash=False)  # its own effect
    cures: tuple[str, ...] = ()  # berries: statuses it cures (once per battle)
    sprite: int = -1   # hats: its cell in the hat sheet (hats.SHEET)


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
    (16, "Wizard Hat", "A tall, pointed hat full of arcane power.", {"power": (3, 5)}),
    (17, "Witch Hat", "Its buckle glints with a sleepy hex.", {"status:sleep": (4, 7)}),
    (19, "Starry Hat", "Stitched with stars that point out weak spots.", {"crit": (3, 5)}),
    (20, "Nightcap", "A cosy cap. Its wearer rests even in battle.", {"regen": (3, 5)}),
    (24, "Mitre", "A tall ceremonial hat that steadies the spirit.", {"hp": (8, 12)}),
    (26, "Crown", "A crown fit for a champion.", {"attack": (5, 8), "defense": (5, 8)}),
    (27, "Halo", "A glowing ring. Its wearer may hang on with 1 HP.", {"endure": (8, 12)}),
    (28, "Tiara", "A jewelled tiara, light and graceful.", {"hp": (5, 8), "speed": (5, 8)}),
    (29, "Turban", "Thick folds of cloth that soften blows.", {"defense": (8, 12)}),
    (31, "Mortarboard", "A scholar's cap. Its wearer knows every weakness.", {"super": (10, 15)}),
    (32, "Archer's Cap", "A feathered cap for sharp-eyed hunters.", {"crit": (2, 4), "speed": (4, 6)}),
    (36, "Headband", "A plain headband tied tight for focus.", {"attack": (4, 6), "speed": (4, 6)}),
    (37, "Tricorne", "A buccaneer's hat. Takes a share of every hit.", {"drain": (6, 10)}),
    (38, "Blue Bandana", "A light bandana for quick getaways.", {"speed": (8, 12)}),
    (39, "Officer's Cap", "Its wearer is always first to act.", {"first": (8, 12)}),
    (40, "Jester's Cap", "Its jingling bells can leave foes stunned.", {"status:paralysis": (5, 8)}),
    (41, "Pirate Hat", "A captain's hat. Bold and ruthless.", {"attack": (6, 10), "crit": (1, 3)}),
    (42, "Red Bandana", "A fiery bandana that boosts strength.", {"attack": (8, 12)}),
    (43, "Plumed Hat", "A dashing, feathered hat.", {"speed": (6, 10), "crit": (1, 2)}),
    (45, "Straw Hat", "A wide hat that keeps its wearer going.", {"hp": (10, 15)}),
    (56, "Visor Helmet", "A sturdy helmet. Tough, but heavy.", {"defense": (16, 24), "speed": (-8, -8)}),
    (61, "Alpine Hat", "A warm hat for long climbs.", {"hp": (5, 8), "defense": (5, 8)}),
    (62, "Fez", "A smart hat with a tassel. It sharpens the aim.", {"power": (2, 4), "crit": (1, 2)}),
    (63, "Sultan's Turban", "A grand turban with a healing jewel.", {"hp": (6, 10), "regen": (2, 3)}),
]

ITEMS = {i.name: i for i in [
    # Head: hats.
    *(Item(name, "head", description, mods, sprite=cell) for cell, name, description, mods in HATS),
    # Held: type items and battle tools.
    *(Item(name, "held", f"{description} Powers up {type_chart.name(t)} moves.", {f"power:{t}": (10, 15)})
      for t, (name, description) in TYPE_ITEMS.items()),
    Item("Quick Claw", "held", "A light, sharp claw. Its holder may move first.", {"first": (12, 18)}),
    Item("Leftovers", "held", "Restores a little HP every round.", {"regen": (4, 6)}),
    Item("Shell Bell", "held", "Restores HP when its holder deals damage.", {"drain": (8, 12)}),
    Item("Scope Lens", "held", "A lens that spots weak points.", {"crit": (4, 6)}),
    # Worn: bands, belts and vests.
    Item("Muscle Band", "worn", "A headband that boosts strength.", {"attack": (8, 12)}),
    Item("Assault Vest", "worn", "A sturdy vest for the front line.", {"defense": (12, 18)}),
    Item("Choice Scarf", "worn", "A scarf that makes its wearer quicker.", {"speed": (12, 18)}),
    Item("Focus Band", "worn", "Its wearer may hang on with 1 HP after a knockout hit.", {"endure": (8, 12)}),
    Item("Expert Belt", "worn", "Powers up super effective moves.", {"super": (12, 18)}),
    Item("Power Bracer", "worn", "A heavy bracer. Strong, but slow.", {"attack": (16, 24), "speed": (-10, -10)}),
    Item("Power Belt", "worn", "A heavy belt. Tough, but slow.", {"defense": (16, 24), "speed": (-10, -10)}),
    # Berries: eaten (at most) once per battle, when they're needed.
    Item("Oran Berry", "berry", "Restores HP when its holder is at half HP or less.", {"berry_heal": (20, 25)}),
    Item("Liechi Berry", "berry", "Raises Attack when its holder is at 1/4 HP or less.", {"berry_attack": (1, 1)}),
    Item("Pecha Berry", "berry", "Cures poison.", cures=("poison",)),
    Item("Rawst Berry", "berry", "Heals a burn.", cures=("burn",)),
    Item("Cheri Berry", "berry", "Cures paralysis.", cures=("paralysis",)),
    Item("Chesto Berry", "berry", "Wakes its holder up.", cures=("sleep",)),
    Item("Aspear Berry", "berry", "Thaws its holder out.", cures=("freeze",)),
    Item("Lum Berry", "berry", "Cures any status.", cures=tuple(STATUSES)),
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

AFFIXES = [
    Affix("Fierce", True, {"attack": (4, 8)}),
    Affix("Sturdy", True, {"defense": (4, 8)}),
    Affix("Swift", True, {"speed": (4, 8)}),
    Affix("Hearty", True, {"hp": (4, 8)}),
    Affix("Keen", True, {"crit": (2, 4)}),
    Affix("Mighty", True, {"power": (3, 6)}),
    Affix("Hasty", True, {"first": (3, 6)}, weight=2),
    Affix("Draining", True, {"drain": (3, 6)}, weight=2),
    Affix("of the Machamp", False, {"attack": (4, 8)}),
    Affix("of the Onix", False, {"defense": (5, 10)}),
    Affix("of the Pidgeot", False, {"speed": (5, 10)}),
    Affix("of the Snorlax", False, {"hp": (5, 10)}),
    Affix("of the Tauros", False, {"attack": (2, 5), "speed": (2, 5)}),
    Affix("of the Golem", False, {"defense": (2, 5), "hp": (2, 5)}),
    Affix("of the Scyther", False, {"crit": (1, 3), "attack": (2, 4)}),
    Affix("of the Hitmonlee", False, {"power": (2, 4), "speed": (2, 4)}),
    Affix("of the Chansey", False, {"regen": (2, 3)}, weight=2),
    *(Affix(prefix, True, {f"added:{t}": (3, 6)}, weight=1)
      for t, (prefix, _) in TYPE_AFFIXES.items() if prefix),
    *(Affix(suffix, False, {f"power:{t}": (5, 10)}, weight=1)
      for t, (_, suffix) in TYPE_AFFIXES.items()),
    *(Affix(suffix, False, {f"status:{s}": chance}, weight=1)
      for s, (suffix, chance) in STATUS_AFFIXES.items()),
]
AFFIX_BY_NAME = {a.name: a for a in AFFIXES}


def _pick_affixes(count: int, rng: random.Random) -> list[Affix]:
    """`count` different affixes, picked by weight."""
    pool, picked = list(AFFIXES), []
    for _ in range(count):
        affix = rng.choices(pool, weights=[a.weight for a in pool])[0]
        pool.remove(affix)
        picked.append(affix)
    return picked


def _roll(mods: dict[str, Range], rarity: Rarity, level: int, rng: random.Random,
          values: str = "random") -> dict[str, int]:
    """Roll each mod's value in its range ("min"/"max" values: the lowest or
    highest instead), then apply the rarity and (to the mods it scales) the
    item level. Penalties stay as they are."""
    rolled = {}
    for mod, (low, high) in mods.items():
        value = low if values == "min" else high if values == "max" else rng.randint(low, high)
        if value > 0:
            factor = rarity.factor * (level_factor(level) if _level_scaled(mod) else 1)
            value = max(1, round(value * factor))
        rolled[mod] = value
    return rolled


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

    @classmethod
    def roll(cls, item: str, rarity: str = "Common", rng: random.Random | None = None,
             affixes: list[str] | None = None, values: str = "random", level: int = 1) -> "Gear":
        """Roll a new piece at item level `level`. `affixes` picks its
        affixes by name instead of at random; `values` "min" or "max" gives
        every roll its lowest or highest value (both are for testing, see
        dev.py)."""
        rng = rng or random.Random()
        item_, rarity_ = ITEMS[item], RARITIES[rarity]
        rolls = [Roll(None, _roll(item_.mods, rarity_, level, rng, values))] if item_.mods else []
        if affixes is not None:
            picked = [AFFIX_BY_NAME[name] for name in affixes]
        elif item_.slot in AFFIX_SLOTS:
            picked = _pick_affixes(rng.randint(*rarity_.affixes), rng)
        else:
            picked = []
        for affix in picked:
            rolls.append(Roll(affix, _roll(affix.mods, rarity_, level, rng, values)))
        return cls(item_, rarity_, rolls, level)

    @property
    def name(self) -> str:
        """The item's name, with its first prefix and first suffix."""
        prefix = next((r.affix.name for r in self.rolls if r.affix and r.affix.prefix), None)
        suffix = next((r.affix.name for r in self.rolls if r.affix and not r.affix.prefix), None)
        return " ".join(p for p in (prefix, self.item.name, suffix) if p)

    @property
    def slot(self) -> str:
        return self.item.slot

    def usable_by(self, monster: "Monster") -> bool:
        """Whether `monster` is a high enough level to equip it."""
        return monster.level >= self.level

    @property
    def mods(self) -> dict[str, int]:
        """All of its rolls added up."""
        total: dict[str, int] = {}
        for roll in self.rolls:
            for mod, value in roll.mods.items():
                total[mod] = total.get(mod, 0) + value
        return total


@dataclass(frozen=True)
class Medicine:
    """An item used up to heal one of your own Pokémon (in battle, for now)."""
    name: str
    description: str
    hp: int = 0             # HP restored
    fraction: float = 0.0   # ... or this share of max HP, if that's more
    revive: bool = False    # only works on (and revives) a fainted Pokémon
    cures: tuple[str, ...] = ()  # statuses it cures

    def heal_amount(self, monster: "Monster") -> int:
        amount = max(self.hp, math.ceil(monster.max_hp * self.fraction))
        return min(amount, monster.max_hp - monster.hp)

    def cures_status(self, monster: "Monster") -> bool:
        return monster.status in self.cures

    def has_effect(self, monster: "Monster") -> bool:
        return bool(self.heal_amount(monster)) or self.cures_status(monster)


MEDICINE = {m.name: m for m in [
    Medicine("Potion", "Restores 20 HP.", hp=20),
    Medicine("Super Potion", "Restores 50 HP.", hp=50),
    Medicine("Hyper Potion", "Restores 200 HP.", hp=200),
    Medicine("Max Potion", "Fully restores HP.", fraction=1.0),
    Medicine("Full Restore", "Fully restores HP and cures any status.", fraction=1.0,
             cures=tuple(STATUSES)),
    Medicine("Revive", "Revives a fainted Pokémon with half its HP.", fraction=0.5, revive=True),
    Medicine("Antidote", "Cures poison.", cures=("poison",)),
    Medicine("Burn Heal", "Heals a burn.", cures=("burn",)),
    Medicine("Paralyze Heal", "Cures paralysis.", cures=("paralysis",)),
    Medicine("Awakening", "Wakes up a sleeping Pokémon.", cures=("sleep",)),
    Medicine("Ice Heal", "Thaws out a frozen Pokémon.", cures=("freeze",)),
    Medicine("Full Heal", "Cures any status.", cures=tuple(STATUSES)),
]}


def mod_text(mod: str, value: int) -> str:
    return MOD_TEXT[mod].format(value)


def boosted(value: int, percent: int) -> int:
    """`value` changed by `percent`, by at least 1 so gear matters at low levels."""
    if not percent:
        return value
    change = round(value * percent / 100)
    change = max(1, change) if percent > 0 else min(-1, change)
    return max(1, value + change)


@dataclass
class Bag:
    """Everything the player carries that isn't equipped."""
    gear: list[Gear] = field(default_factory=list)
    medicine: Counter = field(default_factory=Counter)  # name -> how many

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
