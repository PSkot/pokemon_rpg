"""Combat rules: the damage formula and the numbers battles are tuned by.

`damage` works on battle combatants (`scenes.battle.Combatant`): a Pokémon
plus its battle-only state (stat stages, shield, status). See
docs/mechanics.md for the whole calculation.
"""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .moves import Move
from .status import BURN_ATTACK
from .type_chart import TYPES, effectiveness

if TYPE_CHECKING:
    from ..scenes.battle import Combatant

SHIELD_FACTOR = 0.5  # damage taken while shielded
MAX_STAGE = 6        # stat stages go from -6 to +6
STAGE_STATS = ("attack", "defense", "speed", "accuracy")
FOCUS_CRIT = 4       # Focus Energy: crit chance × this
CRIT_CHANCE = 6.25   # % (1 in 16, as in Gen 2+); gear adds to it
CRIT_FACTOR = 1.5
# Gen 1's special types: their moves use the user's and the target's Special
# instead of Attack and Defense. (The rest are physical, typeless ones too.)
SPECIAL_TYPES = frozenset(("fire", "water", "grass", "electric", "ice", "psychic", "dragon"))
STAB = 1.5           # same-type attack bonus: a move of one of the user's own types


def stage_factor(stage: int) -> float:
    """A stat's multiplier at `stage` (Gen 1): +1 = ×1.5, +6 = ×4, -1 = ×2/3, -6 = ×1/4."""
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def hit_chance(accuracy_stage: int) -> float:
    """The chance a move hits at a lowered accuracy stage: 1/12 less per
    stage, down to 1/2 at -6 (gentler than the stat multipliers' 1/4)."""
    return 1 + min(0, accuracy_stage) / (2 * MAX_STAGE)


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


def is_special(move: Move) -> bool:
    """Whether `move` uses Special (Gen 1: by its type)."""
    return move.type in SPECIAL_TYPES


def damage(user: "Combatant", move: Move, target: "Combatant", share: float = 1.0) -> Hit:
    """The Gen 1 damage formula, simplified (misses are rolled first, by
    BattleScene._misses), plus talents
    and gear. `share`: the part of the damage each target takes (a move
    that hits every enemy)."""
    m, types = user.monster, getattr(target, "types", target.monster.species.types)  # (a perched flier: not Flying)
    if move.halve:  # Super Fang: half the target's HP, whatever the stats
        multiplier = effectiveness(move.type, types)
        return Hit(max(1, target.monster.hp // 2) if multiplier else 0, False, multiplier, [])
    if move.fixed:  # Seismic Toss: the user's level, whatever the stats and types (Gen 1)
        return Hit(max(1, round((move.fixed_amount or m.level) * share)), False, 1.0, [])
    special = is_special(move)  # (Gen 1: these types use Special, attacking and defending)
    attack = (m.special_attack if special else m.attack) * stage_factor(user.stages["attack"])
    if user.status == "burn" and not special:  # (a burn weakens physical moves only)
        attack *= BURN_ATTACK
    target_m = target.monster
    defense = (target_m.special_defense if special else target_m.defense) * stage_factor(target.stages["defense"])
    power = move.power * move.scale + m.gear_bonus("power")
    level_factor = 2 * m.level / 5 + 2
    base = level_factor * power * attack / defense / 50 + 2
    focus = FOCUS_CRIT if user.focused else 1
    crit = random.random() * 100 < CRIT_CHANCE * move.crit_ratio * focus + m.gear_bonus("crit")
    if move.keen and target.monster.hp < target.monster.max_hp * move.keen:  # (Keen Edge)
        crit = True
    if crit:
        base *= CRIT_FACTOR + (m.talent("sniper") if m.has_effects else 0)  # (Sniper: ×2)
    if target.shield:
        base *= SHIELD_FACTOR
    base *= random.uniform(0.85, 1.0) * share

    multiplier = effectiveness(move.type, types)
    amount = base * multiplier
    if move.type:
        if move.type in m.species.types:
            amount *= STAB
        amount *= 1 + m.gear_bonus(f"power:{move.type}") / 100
    if multiplier > 1:
        amount *= 1 + m.gear_bonus("super") / 100
    # Status moves' buffs: Empowering (the user), Exposing and Shocking (the target).
    amount *= 1 + getattr(user, "empowered", 0.0)
    if getattr(target, "exposed", 0):
        amount *= 1 + target.expose_share
    if target.monster.status == "paralysis":
        amount *= 1 + getattr(target, "shock", 0.0)
    # Gear's added type damage: a share of the hit, with its own effectiveness.
    added = []
    for t in TYPES:
        extra = round(base * m.gear_bonus(f"added:{t}") / 100 * effectiveness(t, types))
        if extra:
            added.append((t, extra))
    return Hit(max(1, round(amount)) if multiplier else 0, crit, multiplier, added)
