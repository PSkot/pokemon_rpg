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
    from .pokemon import Monster

SHIELD_FACTOR = 0.5  # damage taken while shielded
MAX_STAGE = 6        # stat stages go from -6 to +6
STAGE_STATS = ("attack", "defense", "speed", "accuracy")
FOCUS_CRIT = 4       # Focus Energy: crit chance × this
CRIT_CHANCE = 5.0    # % base; gear adds to it (no cap: gear's crit is small and rare)
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


def crit_chance(m: "Monster", move: Move, focused: bool = False) -> float:
    """The % chance a hit of `move` by `m` is critical: the base chance ×
    the move's crit ratio (× `FOCUS_CRIT` when focused), plus gear and
    talents' crit points; at most 100%."""
    focus = FOCUS_CRIT if focused else 1
    return min(100.0, CRIT_CHANCE * move.crit_ratio * focus + m.gear_bonus("crit"))


def is_special(move: Move) -> bool:
    """Whether `move` uses Special (Gen 1: by its type)."""
    return move.type in SPECIAL_TYPES


# The expected damage of a move (the party screen's Damage page, for picking
# gear): against a typical foe at the user's level: base Defense and Special
# `REFERENCE_BASE`, base HP `REFERENCE_BASE`, no gear, a type that takes
# neutral damage from everything.
REFERENCE_BASE = 70


def reference_stat(level: int) -> int:
    return REFERENCE_BASE * 2 * level // 100 + 5


def expected_damage(m: "Monster", move: Move) -> float | None:
    """The damage one use of `move` by `m` is expected to deal to the
    typical foe (`REFERENCE_BASE`), on average: the mean of the random
    spread, crits at their chance, the chance to hit, multi-hits at their
    average count, STAB, its type's power gear and added type damage (both
    neutral). Conditional bonuses (talents' pinch, streak, ...; stat
    stages; super-effective gear) aren't counted. None for a status move."""
    hits = (move.hits[0] + move.hits[1]) / 2
    accuracy = min(100, move.accuracy) / 100
    if move.halve:  # Super Fang: half the foe's (full) HP
        from .pokemon import max_hp_at  # (pokemon.py builds on this module's neighbours)
        return max_hp_at(REFERENCE_BASE, m.level) // 2 * accuracy
    if move.fixed:
        return (move.fixed_amount or m.level) * hits * accuracy
    if not move.power:
        return None
    special = is_special(move)
    attack = m.special_attack if special else m.attack
    power = move.power * move.scale + m.gear_bonus("power")
    base = (2 * m.level / 5 + 2) * power * attack / reference_stat(m.level) / 50 + 2
    crit = crit_chance(m, move) / 100
    crit_factor = CRIT_FACTOR + (m.talent("sniper") if m.has_effects else 0)
    base *= (1 + crit * (crit_factor - 1)) * 0.925  # (0.925: the spread's average)
    amount = base
    if move.type:
        if move.type in m.species.types:
            amount *= STAB
        amount *= 1 + m.gear_bonus(f"power:{move.type}") / 100
    amount += sum(base * m.gear_bonus(f"added:{t}") / 100 for t in TYPES)
    return max(1.0, amount) * hits * accuracy


# The party screen's Rating (gear at a glance): one use of a standard
# move of `RATING_POWER` against the typical foe, and how many such hits
# from it the Pokémon survives.
RATING_POWER = 70


@dataclass(frozen=True)
class Rating:
    same_type: float  # expected damage of a standard move of its (first) type
    neutral: float    # ... of a typeless one (physical, no STAB)
    toughness: float  # standard hits (physical and special, on average) it survives from the typical foe


def rating(m: "Monster") -> Rating:
    """`m`'s Rating, with its gear and talents' stat effects (see `expected_damage`)."""
    same = expected_damage(m, Move("Standard", RATING_POWER, "enemy", type=m.species.types[0]))
    neutral = expected_damage(m, Move("Standard", RATING_POWER, "enemy"))
    foe_attack = reference_stat(m.level)
    crit = 1 + CRIT_CHANCE / 100 * (CRIT_FACTOR - 1)

    def hit(defense: int) -> float:
        return ((2 * m.level / 5 + 2) * RATING_POWER * foe_attack / defense / 50 + 2) * crit * 0.925
    taken = (hit(m.defense) + hit(m.special_defense)) / 2
    return Rating(same or 0.0, neutral or 0.0, m.max_hp / taken)


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
    crit = random.random() * 100 < crit_chance(m, move, user.focused)
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
