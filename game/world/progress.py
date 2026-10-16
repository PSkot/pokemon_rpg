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
        """The starting party and bag: the starter holds a Common Oran Berry
        (heals a little at half HP, once per battle); a few medicines."""
        party = [Monster.create("bulbasaur", 5)]
        bag = Bag()
        party[0].equip(Gear.roll("Oran Berry", "Common"))
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
