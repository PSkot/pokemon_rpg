"""The player's progress through the world (what a save stores, apart from
where the player stands)."""

from collections import Counter
from dataclasses import dataclass, field

from ..mechanics.items import Bag, Gear
from ..mechanics.pokemon import Monster

START_TOWN = "pallet"


@dataclass
class Game:
    party: list[Monster]
    bag: Bag
    town: str = START_TOWN  # the last town visited: where a fainted party wakes up
    cleared: Counter = field(default_factory=Counter)  # route key -> times walked all the way

    @classmethod
    def new(cls) -> "Game":
        """The starting party and bag (with some gear and items, for trying things out)."""
        party = [Monster.create("bulbasaur", 5)]
        bag = Bag()
        for gear in [Gear.roll("Red Bandana", "Rare", affixes=["Fierce", "of the Aerodactyl"]),
                     Gear.roll("Poison Barb", "Legendary", affixes=["Venomous", "of the Muk"]),
                     Gear.roll("Power Bracer", "Epic"), Gear.roll("Oran Berry"),
                     Gear.roll("Wizard Hat"), Gear.roll("Crown", "Epic"),
                     Gear.roll("Scope Lens", "Legendary"), Gear.roll("Assault Vest")]:
            bag.add(gear)
        for gear in list(bag.gear)[:4]:
            bag.equip(party[0], gear)
        for name, count in [("Potion", 3), ("Super Potion", 1), ("Revive", 1), ("Antidote", 2),
                            ("Paralyze Heal", 1), ("Full Heal", 1)]:
            bag.add_medicine(name, count)
        return cls(party, bag)

    def heal(self) -> bool:
        """Restore the whole party; returns whether anyone needed it."""
        needed = any(m.hp < m.max_hp or m.status for m in self.party)
        for m in self.party:
            m.hp = m.max_hp
            m.cure()
        return needed
