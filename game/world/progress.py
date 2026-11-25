"""The player's progress through the world (what a save stores, apart from
where the player stands)."""

import random
from collections import Counter
from dataclasses import dataclass, field

from ..mechanics.items import Bag, Gear
from ..mechanics.pokemon import Monster

START_TOWN = "pallet"
MAX_PARTY = 6  # the party's size at its biggest; the rest wait in the reserve
# The party's size: everyone in it fights. 1 at first; each Teamwork Ribbon
# used from the bag adds a place (`Game.slots`, items.RIBBON), up to MAX_PARTY.
# The quests that give one (the rival on Route 22, the S.S. Anne): saves from
# before the ribbons get a place for each of these done.
ACTIVE_STEPS = ("rival_22", "ss_anne")
STARTERS = ("bulbasaur", "charmander", "squirtle")  # what Professor Oak offers
# The rival picks the starter that beats the player's.
RIVAL_STARTERS = {"bulbasaur": "charmander", "charmander": "squirtle", "squirtle": "bulbasaur"}


@dataclass
class Game:
    party: list[Monster]
    bag: Bag
    town: str = START_TOWN  # the last town visited: where a fainted party wakes up
    cleared: Counter = field(default_factory=Counter)  # route key -> times walked all the way
    starter: str = "bulbasaur"  # the player's first Pokémon (species key)
    quests: dict[str, int] = field(default_factory=dict)  # quest key -> the step it's at (see quests.py)
    quest_counts: dict[str, int] = field(default_factory=dict)  # quest key -> its counted step's count so far
    trainers: set[str] = field(default_factory=set)  # the route trainers beaten (instance.Trainer.key)
    reserve: list[Monster] = field(default_factory=list)  # recruits not in the party (swapped at a Recruitment Center)
    defeated: Counter = field(default_factory=Counter)  # line (its first species) -> Pokémon of it defeated
    # Gear counters (towns.gear_stock): this game's seed for their stock, and
    # per town how often the player has arrived from a route (each arrival
    # restocks it) and which of the pieces on offer they bought since.
    seed: int = field(default_factory=lambda: random.randrange(1 << 30))
    shop_visits: dict[str, int] = field(default_factory=dict)
    shop_bought: dict[str, list[int]] = field(default_factory=dict)
    slots: int = 1  # places in the party (how many fight): +1 per Teamwork Ribbon used
    repel: int = 0  # steps of Repel left (overworld.py)
    tower_best: int = 0  # the Battle Tower's highest floor cleared (world/tower.py)
    visited: set[str] = field(default_factory=set)  # towns and routes been to (the Town Map, world/townmap.py)
    kudos: dict[str, int] = field(default_factory=dict)  # Safari Zone: species -> Kudos earned (world/safari.py)

    def arrive(self, town: str) -> None:
        """The player arrived in `town` from a route: its gear counter restocks."""
        self.shop_visits[town] = self.shop_visits.get(town, 0) + 1
        self.shop_bought.pop(town, None)

    @property
    def rival_starter(self) -> str:
        return RIVAL_STARTERS[self.starter]

    @classmethod
    def new(cls, starter: str = "bulbasaur") -> "Game":
        """The starting party and bag: the chosen starter (Lv5) holds a
        Common Oran Berry (heals a little at half HP, once per battle); a few
        medicines."""
        party = [Monster.create(starter, 5)]
        bag = Bag()
        party[0].equip(Gear.roll("Oran Berry", "Common", level=5))
        for name, count in [("Potion", 3), ("Super Potion", 1), ("Revive", 1), ("Antidote", 2),
                            ("Paralyze Heal", 1), ("Full Heal", 1)]:
            bag.add_medicine(name, count)
        return cls(party, bag, starter=starter)

    def heal(self) -> bool:
        """Restore the whole party (and the reserve); returns whether anyone
        in the party needed it."""
        needed = any(m.hp < m.max_hp or m.status for m in self.party)
        for m in self.party + self.reserve:
            m.hp = m.max_hp
            m.cure()
        return needed

    def add_member(self, monster: Monster, room: int) -> str:
        """A new Pokémon joins: the party if it has fewer than `room`, else
        the reserve. Returns which ("party" or "reserve")."""
        if len(self.party) < room:
            self.party.append(monster)
            return "party"
        self.reserve.append(monster)
        return "reserve"
