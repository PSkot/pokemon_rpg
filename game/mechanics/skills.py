"""Skill trees: how Pokémon get and improve their moves (docs/skill_trees.md).

Each evolution line has a tree of skills, bought and ranked up with skill
points (1 per level from Lv6). A skill opens once the Pokémon has its
level, its parent skill and its evolution stage. Kinds:

- base attacks: known from the start (rank 1 free); the first is the basic
  attack (Fight);
- moves: used in battle once learned and equipped (up to `MAX_EQUIPPED`);
- modifiers: passive, they change one move.

A skill's ranks and the modifiers on it are changes to its move's fields
(see moves.Move); `effective_move` applies them. Damaging moves also get
+`RANK_DAMAGE` damage per rank after the first.
"""

from dataclasses import dataclass, field, replace
from functools import cache

from .moves import MOVES, Move

FIRST_POINT_LEVEL = 5   # skill points = level − this
RANK_DAMAGE = 0.15
MAX_EQUIPPED = 4


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    kind: str      # "base", "move" or "modifier"
    move: str      # base/move: its move (in MOVES); modifier: the skill key of the move it changes
    max_rank: int
    level: int = 0     # opens at this level
    parent: str = ""   # skill key: needs this skill first
    stage: int = 0     # evolution stage needed (0 = the line's first species)
    # What each rank changes (rank 1 first; {} = nothing). A rank's entry is
    # the full set of changes at that rank, not added to the ones before.
    ranks: tuple[dict, ...] = field(default=(), hash=False)
    text: tuple[str, ...] = ()  # what each rank does, in words (rank 1 first)

    def changes(self, rank: int) -> dict:
        return self.ranks[min(rank, len(self.ranks)) - 1] if self.ranks and rank else {}


@dataclass(frozen=True)
class SkillTree:
    species: tuple[str, ...]   # the line's species keys, by stage
    skills: dict[str, Skill] = field(hash=False)  # by key, in tree order

    @property
    def base(self) -> list[Skill]:
        return [s for s in self.skills.values() if s.kind == "base"]

    @property
    def basic(self) -> Skill:
        """The basic attack: the first base attack."""
        return self.base[0]

    def total_points(self, level: int) -> int:
        return max(0, level - FIRST_POINT_LEVEL)

    def spent(self, ranks: dict[str, int]) -> int:
        """Points in `ranks` (base attacks' first rank is free)."""
        return sum(ranks.values()) - sum(1 for s in self.base if ranks.get(s.key))

    def why_not(self, ranks: dict[str, int], key: str, level: int, stage: int) -> str:
        """Why skill `key` can't be ranked up now ("" if it can)."""
        skill, rank = self.skills[key], ranks.get(key, 0)
        if rank >= skill.max_rank:
            return "Max rank"
        if stage < skill.stage:
            return f"Needs {self.species[skill.stage].capitalize()}"
        if level < skill.level:
            return f"Opens at Lv{skill.level}"
        if skill.parent and not ranks.get(skill.parent):
            return f"Needs {self.skills[skill.parent].name}"
        if self.spent(ranks) >= self.total_points(level):
            return "No skill points"
        return ""

    def effective_move(self, ranks: dict[str, int], key: str) -> Move:
        """Skill `key`'s move with its rank and its modifiers applied."""
        skill, rank = self.skills[key], max(1, ranks.get(key, 0))
        move = MOVES[skill.move]
        changes = dict(skill.changes(rank))
        if move.damaging:
            changes["scale"] = 1 + RANK_DAMAGE * (rank - 1)
        for mod in self.skills.values():
            if mod.kind == "modifier" and mod.move == key and ranks.get(mod.key):
                changes.update(mod.changes(ranks[mod.key]))
        return replace(move, **changes)

    def auto_build(self, level: int, stage: int) -> tuple[dict[str, int], list[str]]:
        """Ranks and equipped moves for a Pokémon that builds itself (wild
        ones): every move it can learn, in level order, equipping the last 4
        learned (as in Gen 1). The rest of its points go into ranks of the
        basic attack and the equipped moves (one each in turn), then into
        those moves' modifiers, then into whatever else is open."""
        ranks = {s.key: 1 for s in self.base}
        learned = [s.key for s in self.base[1:]]
        for skill in sorted((s for s in self.skills.values() if s.kind == "move"), key=lambda s: s.level):
            if not self.why_not(ranks, skill.key, level, stage):
                ranks[skill.key] = 1
                learned.append(skill.key)
        equipped = learned[-MAX_EQUIPPED:]
        used = [self.basic.key] + equipped
        by_level = sorted(self.skills.values(), key=lambda s: s.level)
        for keys in (used,
                     [s.key for s in by_level if s.kind == "modifier" and s.move in used],
                     [s.key for s in by_level]):
            spending = True
            while spending:
                spending = False
                for key in keys:
                    if not self.why_not(ranks, key, level, stage):
                        ranks[key] = ranks.get(key, 0) + 1
                        spending = True
        return ranks, equipped


def _tree(species: tuple[str, ...], *skills: Skill) -> SkillTree:
    return SkillTree(species, {s.key: s for s in skills})


def _chance(status: str, *chances: int) -> tuple[dict, ...]:
    return tuple({"status": status, "status_chance": c} for c in chances)


TREES = {t.species[0]: t for t in [
    _tree(
        ("bulbasaur", "ivysaur", "venusaur"),
        # Base attacks.
        Skill("tackle", "Tackle", "base", "Tackle", 5, text=("Normal, 35 power. Basic attack.",)),
        Skill("growl", "Growl", "base", "Growl", 2, ranks=({}, {"spread": True}),
              text=("Lowers one enemy's Attack.", "Lowers every enemy's Attack.")),
        # Moves.
        Skill("leech_seed", "Leech Seed", "move", "Leech Seed", 3, 7, "growl",
              ranks=({}, {"seed": 1 / 12}, {"seed": 1 / 8}),
              text=("Seeds an enemy: drains 1/16 of its max HP each round.", "Drains 1/12.", "Drains 1/8.")),
        Skill("vine_whip", "Vine Whip", "move", "Vine Whip", 5, 13, "tackle", text=("Grass, 35 power.",)),
        Skill("poison_powder", "Poison Powder", "move", "Poison Powder", 3, 20, "growl",
              ranks=({}, {"stages": (("speed", -1),)}, {"stages": (("speed", -2),)}),
              text=("Poisons an enemy.", "Also lowers its Speed 1 stage.", "Also lowers its Speed 2 stages.")),
        Skill("take_down", "Take Down", "move", "Take Down", 5, 20, "tackle",
              text=("Normal, 90 power. The user takes 1/4 of the damage dealt.",)),
        Skill("razor_leaf", "Razor Leaf", "move", "Razor Leaf", 5, 27, "vine_whip",
              text=("Grass, 55 power. High critical-hit ratio.",)),
        Skill("growth", "Growth", "move", "Growth", 3, 34, "leech_seed",
              ranks=({}, {"stages": (("attack", 2),)}, {"stages": (("attack", 2), ("defense", 1))}),
              text=("Raises the user's Attack 1 stage.", "Raises Attack 2 stages.",
                    "Raises Attack 2 stages and Defense 1 stage.")),
        Skill("leaf_shield", "Leaf Shield", "move", "Leaf Shield", 3, 22, "growl", stage=1,
              ranks=({}, {"shield": 3}, {"shield": 3, "spread": True}),
              text=("Halves the damage an ally takes for 2 rounds.", "For 3 rounds.",
                    "For 3 rounds, on the whole party.")),
        Skill("sleep_powder", "Sleep Powder", "move", "Sleep Powder", 3, 41, "poison_powder", stage=1,
              ranks=({}, {"sleep_bonus": 1}, {"sleep_bonus": 2}),
              text=("Puts an enemy to sleep.", "It sleeps 1 round longer.", "It sleeps 2 rounds longer.")),
        Skill("body_slam", "Body Slam", "move", "Body Slam", 5, 30, "take_down", stage=1,
              text=("Normal, 85 power. 30% chance to paralyze.",)),
        Skill("solar_beam", "Solar Beam", "move", "Solar Beam", 5, 48, "razor_leaf", stage=1,
              text=("Grass, 120 power. Charges for a round first.",)),
        Skill("double_edge", "Double-Edge", "move", "Double-Edge", 5, 50, "body_slam", stage=2,
              text=("Normal, 100 power. The user takes 1/4 of the damage dealt.",)),
        Skill("hyper_beam", "Hyper Beam", "move", "Hyper Beam", 5, 55, "solar_beam", stage=2,
              text=("Normal, 150 power. The user must rest the next round.",)),
        # Modifiers.
        Skill("binding_vines", "Binding Vines", "modifier", "vine_whip", 3, 15, "vine_whip",
              ranks=_chance("paralysis", 10, 20, 30),
              text=("Vine Whip: 10% chance to paralyze.", "20% chance.", "30% chance.")),
        Skill("spreading_seeds", "Spreading Seeds", "modifier", "leech_seed", 1, 18, "leech_seed",
              ranks=({"spread": True},), text=("Leech Seed seeds every enemy.",)),
        Skill("bloom", "Bloom", "modifier", "growth", 3, 36, "growth",
              ranks=({"heal": 1 / 8}, {"heal": 1 / 6}, {"heal": 1 / 4}),
              text=("Growth also heals the user 1/8 of its max HP.", "Heals 1/6.", "Heals 1/4.")),
        Skill("whirling_leaves", "Whirling Leaves", "modifier", "razor_leaf", 1, 32, "razor_leaf", stage=1,
              ranks=({"spread": True, "spread_share": 0.75},),
              text=("Razor Leaf hits every enemy, at 75% damage.",)),
        Skill("toxic_spores", "Toxic Spores", "modifier", "poison_powder", 1, 28, "poison_powder", stage=1,
              ranks=({"toxic": True},), text=("Poison Powder's poison gets worse every round (Toxic).",)),
        Skill("drowsy_cloud", "Drowsy Cloud", "modifier", "sleep_powder", 1, 45, "sleep_powder", stage=2,
              ranks=({"spread": True},), text=("Sleep Powder hits every enemy.",)),
        Skill("sunburn", "Sunburn", "modifier", "solar_beam", 3, 50, "solar_beam", stage=2,
              ranks=_chance("burn", 10, 20, 30),
              text=("Solar Beam: 10% chance to burn.", "20% chance.", "30% chance.")),
        Skill("quick_bloom", "Quick Bloom", "modifier", "solar_beam", 1, 60, "solar_beam", stage=2,
              ranks=({"charge": ""},), text=("Solar Beam fires without charging.",)),
    ),
]}


@cache
def stand_in_tree(species: str, moves: tuple[str, ...]) -> SkillTree:
    """For lines without a tree yet: their moves as base attacks."""
    return SkillTree((species,), {
        name: Skill(name, name, "base", name, 5 if MOVES[name].damaging else 1) for name in moves})
