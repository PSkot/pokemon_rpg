"""Talents: how Pokémon get their moves and make them their own
(docs/talents.md).

Moves come by level: each line has its Red/Blue level-up moves (and some
TMs) at set levels and evolution stages (`LEARNSETS`), learned on their
own. The first is the basic attack (Fight). Up to `MAX_EQUIPPED` more are
used in battle.

Talents are the build: a line's `TalentTree` has 3 paths and 12 tiers
(`TIER_LEVELS`); at each tier the player picks 1 of 3 talents, one per
path. The last tiers' talents also need earlier picks in their path
(`DEEP`). A talent changes moves (`Talent.moves`: Move field changes,
for a move, the basic attack, or every move of a type or status) and/or
works in battle by itself (`Talent.flags`, read by `BattleScene`).
Talents are written once (`TALENTS`) and shared between lines: type and
status pools, move pools, any line, or one line's own (`Talent.pool`).

The parts: talent_core.py (the classes and rules), learnsets.py (moves
by level), talent_list.py / talent_list_2.py (every talent),
talent_trees.py / talent_trees_2.py (each line's paths and tiers).
"""

from functools import cache

from .learnsets import LEARNSETS
from .talent_core import (ADDED, CHANCES, DEEP, MAX_EQUIPPED, TALENT_MODS, TIER_LEVELS, LearnedMove, Path, Talent,  # noqa: F401
                          TalentTree, _selects, apply_changes, key_of)
from .talent_list import TALENTS  # noqa: F401
from .talent_trees import TALENT_TREES


def _line(species: tuple[str, ...], moves: tuple) -> TalentTree:
    paths, tiers = TALENT_TREES.get(species[0], ((), ()))
    return TalentTree(species, tuple(LearnedMove(*m) for m in moves), paths, tiers)


TREES = {species[0]: _line(species, moves) for species, moves in LEARNSETS.items()}


@cache
def stand_in_tree(species: str) -> TalentTree:
    """For lines without moves yet: Tackle."""
    return TalentTree((species,), (LearnedMove("Tackle"),))
