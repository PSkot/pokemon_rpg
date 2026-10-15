"""Loot: what battles and chests hand out.

A loot table rolls a number of times; each roll picks one weighted entry:
nothing, some medicine, or a piece of gear (rolled at a weighted rarity).
"""

import random
from dataclasses import dataclass, field

from ..engine import ui
from .items import ITEMS, SLOT_NAMES, Bag, Gear, Range


@dataclass(frozen=True)
class MedicineDrop:
    name: str
    count: Range = (1, 1)


@dataclass(frozen=True)
class GearDrop:
    rarity: dict[str, int] = field(hash=False)  # rarity name -> weight
    items: tuple[str, ...] = ()                 # () = any item


Drop = MedicineDrop | GearDrop | None  # None = nothing


@dataclass(frozen=True)
class LootTable:
    entries: tuple[tuple[int, Drop], ...]  # (weight, drop)
    rolls: Range = (1, 1)

    def roll(self, rng: random.Random | None = None) -> list["Reward"]:
        rng = rng or random.Random()
        rewards: list[Reward] = []
        for _ in range(rng.randint(*self.rolls)):
            drop = rng.choices([d for _, d in self.entries], weights=[w for w, _ in self.entries])[0]
            if isinstance(drop, MedicineDrop):
                rewards.append(Reward(medicine=drop.name, count=rng.randint(*drop.count)))
            elif isinstance(drop, GearDrop):
                item = rng.choice(drop.items or tuple(ITEMS))
                rarity = rng.choices(list(drop.rarity), weights=list(drop.rarity.values()))[0]
                rewards.append(Reward(gear=Gear.roll(item, rarity, rng)))
        return merge(rewards)


@dataclass
class Reward:
    """One line of loot: a piece of gear, or some of one medicine."""
    gear: Gear | None = None
    medicine: str = ""
    count: int = 0

    def give(self, bag: Bag) -> None:
        if self.gear:
            bag.add(self.gear)
        else:
            bag.add_medicine(self.medicine, self.count)

    def row(self) -> tuple[str, tuple[int, int, int], str]:
        """(text, colour, right-hand text) for a reward list."""
        if self.gear:
            g = self.gear
            return g.name, g.rarity.color, f"{g.rarity.name} {SLOT_NAMES[g.slot]}"
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


# Rarity weights.
WILD_RARITY = {"Common": 70, "Rare": 24, "Epic": 5, "Legendary": 1}
CHEST_RARITY = {"Common": 50, "Rare": 35, "Epic": 12, "Legendary": 3}

# Rolled once for each defeated wild Pokémon.
WILD_LOOT = LootTable((
    (55, None),
    (18, MedicineDrop("Potion")),
    (4, MedicineDrop("Super Potion")),
    (3, MedicineDrop("Antidote")),
    (2, MedicineDrop("Paralyze Heal")),
    (2, MedicineDrop("Burn Heal")),
    (2, MedicineDrop("Awakening")),
    (2, MedicineDrop("Ice Heal")),
    (12, GearDrop(WILD_RARITY)),
))

# A chest by the roadside: a few things, never empty.
CHEST_LOOT = LootTable((
    (25, MedicineDrop("Potion", (1, 3))),
    (12, MedicineDrop("Super Potion")),
    (4, MedicineDrop("Hyper Potion")),
    (5, MedicineDrop("Revive")),
    (6, MedicineDrop("Antidote", (1, 2))),
    (6, MedicineDrop("Paralyze Heal")),
    (4, MedicineDrop("Full Heal")),
    (30, GearDrop(CHEST_RARITY)),
), rolls=(2, 3))

# The reward for beating an instance's boss: more, and better, gear.
BOSS_RARITY = {"Common": 25, "Rare": 45, "Epic": 24, "Legendary": 6}
BOSS_LOOT = LootTable((
    (45, GearDrop(BOSS_RARITY)),
    (12, MedicineDrop("Super Potion", (1, 2))),
    (8, MedicineDrop("Hyper Potion")),
    (8, MedicineDrop("Revive")),
    (6, MedicineDrop("Full Heal")),
    (3, MedicineDrop("Full Restore")),
), rolls=(3, 4))
