"""Combat rules: the damage formula and the numbers battles are tuned by.

`damage` works on battle combatants (`scenes.battle.Combatant`): a Pokémon
plus its battle-only state (attack stage, shield, status). See
docs/mechanics.md for the whole calculation.
"""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pokemon import Move
from .status import BURN_ATTACK
from .type_chart import TYPES, effectiveness

if TYPE_CHECKING:
    from ..scenes.battle import Combatant

SHIELD_ROUNDS = 2    # Leaf Shield lasts the round it is used and the next
SHIELD_FACTOR = 0.5  # damage taken while shielded
MAX_ATTACK_STAGE = 6
CRIT_CHANCE = 6.25   # % (1 in 16, as in Gen 2+); gear adds to it
CRIT_FACTOR = 1.5
STAB = 1.5           # same-type attack bonus: a move of one of the user's own types


@dataclass
class Hit:
    """The outcome of one damaging move."""
    damage: int          # from the move itself
    crit: bool
    effectiveness: float
    added: list[tuple[str, int]]  # extra damage by type, from gear

    @property
    def total(self) -> int:
        return self.damage + sum(amount for _, amount in self.added)


def damage(user: "Combatant", move: Move, target: "Combatant") -> Hit:
    """The Gen 1 damage formula, simplified (no misses), plus gear."""
    m, types = user.monster, target.monster.species.types
    attack = m.attack * (2 + user.attack_stage) / 2
    if user.status == "burn":
        attack *= BURN_ATTACK
    power = move.power + m.gear_bonus("power")
    level_factor = 2 * m.level / 5 + 2
    base = level_factor * power * attack / target.monster.defense / 50 + 2
    crit = random.random() * 100 < CRIT_CHANCE + m.gear_bonus("crit")
    if crit:
        base *= CRIT_FACTOR
    if target.shield:
        base *= SHIELD_FACTOR
    base *= random.uniform(0.85, 1.0)

    multiplier = effectiveness(move.type, types)
    amount = base * multiplier
    if move.type:
        if move.type in m.species.types:
            amount *= STAB
        amount *= 1 + m.gear_bonus(f"power:{move.type}") / 100
    if multiplier > 1:
        amount *= 1 + m.gear_bonus("super") / 100
    # Gear's added type damage: a share of the hit, with its own effectiveness.
    added = []
    for t in TYPES:
        extra = round(base * m.gear_bonus(f"added:{t}") / 100 * effectiveness(t, types))
        if extra:
            added.append((t, extra))
    return Hit(max(1, round(amount)) if multiplier else 0, crit, multiplier, added)
