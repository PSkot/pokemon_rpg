"""Loot: what battles and chests hand out.

A loot table rolls a number of times; each roll picks one weighted entry:
nothing, some medicine, or a piece of gear (rolled at a weighted rarity).
Gear is rolled at the item level the roll is given (the defeated Pokémon's
level, or the area's for chests).

Which rarities can drop is set per area (`world.instance.Route`), so the
tables are built for a set of rarity weights: `wild_loot`, `chest_loot`,
`boss_loot`.
"""

import random
from dataclasses import dataclass
from functools import cache

from ..engine import ui
from .items import ITEMS, SLOT_NAMES, Bag, Gear, Range, money_text


@dataclass(frozen=True)
class MedicineDrop:
    name: str
    count: Range = (1, 1)


Rarities = tuple[tuple[str, int], ...]  # (rarity name, weight)


@dataclass(frozen=True)
class GearDrop:
    rarity: Rarities
    items: tuple[str, ...] = ()  # () = any item


Drop = MedicineDrop | GearDrop | None  # None = nothing


@dataclass(frozen=True)
class LootTable:
    entries: tuple[tuple[int, Drop], ...]  # (weight, drop)
    rolls: Range = (1, 1)

    def roll(self, rng: random.Random | None = None, level: int = 1) -> list["Reward"]:
        """Its rewards; gear comes at item level `level`."""
        rng = rng or random.Random()
        rewards: list[Reward] = []
        for _ in range(rng.randint(*self.rolls)):
            drop = rng.choices([d for _, d in self.entries], weights=[w for w, _ in self.entries])[0]
            if isinstance(drop, MedicineDrop):
                rewards.append(Reward(medicine=drop.name, count=rng.randint(*drop.count)))
            elif isinstance(drop, GearDrop):
                item = rng.choice(drop.items or tuple(ITEMS))
                rarity = rng.choices([r for r, _ in drop.rarity], weights=[w for _, w in drop.rarity])[0]
                rewards.append(Reward(gear=Gear.roll(item, rarity, rng, level=level)))
        return merge(rewards)


@dataclass
class Reward:
    """One line of loot: a piece of gear, some of one medicine, or money."""
    gear: Gear | None = None
    medicine: str = ""
    count: int = 0
    money: int = 0  # Poké Dollars

    def give(self, bag: Bag) -> None:
        if self.gear:
            bag.add(self.gear)
        elif self.money:
            bag.money += self.money
        else:
            bag.add_medicine(self.medicine, self.count)

    def row(self) -> tuple[str, tuple[int, int, int], str]:
        """(text, colour, right-hand text) for a reward list."""
        if self.gear:
            g = self.gear
            return g.name, g.rarity.color, f"Lv{g.level} {g.rarity.name} {SLOT_NAMES[g.slot]}"
        if self.money:
            return money_text(self.money), ui.YELLOW, "Poké Dollars"
        return self.medicine, ui.WHITE, f"x{self.count}"


def merge(rewards: list[Reward]) -> list[Reward]:
    """Add up the counts of the same medicine (gear stays one line each)."""
    merged: list[Reward] = []
    for r in rewards:
        same = next((m for m in merged if r.medicine and m.medicine == r.medicine), None)
        if same:
            same.count += r.count
        else:
            merged.append(r)
    return merged


# Rarity weights for areas. Early on only Common gear drops; bosses can
# also drop Uncommon. Rare, Epic and Legendary are for later areas.
COMMON_ONLY: Rarities = (("Common", 1),)
EARLY_BOSS: Rarities = (("Common", 3), ("Uncommon", 2))


@cache
def wild_loot(rarity: Rarities = COMMON_ONLY) -> LootTable:
    """Rolled once for each defeated wild Pokémon."""
    return LootTable((
        (55, None),
        (18, MedicineDrop("Potion")),
        (4, MedicineDrop("Super Potion")),
        (3, MedicineDrop("Antidote")),
        (2, MedicineDrop("Paralyze Heal")),
        (2, MedicineDrop("Burn Heal")),
        (2, MedicineDrop("Awakening")),
        (2, MedicineDrop("Ice Heal")),
        (12, GearDrop(rarity)),
    ))


@cache
def chest_loot(rarity: Rarities = COMMON_ONLY) -> LootTable:
    """A chest by the roadside: a few things, never empty."""
    return LootTable((
        (25, MedicineDrop("Potion", (1, 3))),
        (12, MedicineDrop("Super Potion")),
        (4, MedicineDrop("Hyper Potion")),
        (5, MedicineDrop("Revive")),
        (6, MedicineDrop("Antidote", (1, 2))),
        (6, MedicineDrop("Paralyze Heal")),
        (4, MedicineDrop("Full Heal")),
        (30, GearDrop(rarity)),
    ), rolls=(2, 3))


@cache
def boss_loot(rarity: Rarities = EARLY_BOSS) -> LootTable:
    """The reward for beating a boss group: more gear, and better medicine."""
    return LootTable((
        (45, GearDrop(rarity)),
        (12, MedicineDrop("Super Potion", (1, 2))),
        (8, MedicineDrop("Hyper Potion")),
        (8, MedicineDrop("Revive")),
        (6, MedicineDrop("Full Heal")),
        (3, MedicineDrop("Full Restore")),
    ), rolls=(3, 4))
