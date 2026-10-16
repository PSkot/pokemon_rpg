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

from .moves import MOVES, Move, describe

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


# --- building trees -------------------------------------------------------

SPREAD = {"spread": True}
SPREAD_75 = {"spread": True, "spread_share": 0.75}


def _key(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def _tree(species: tuple[str, ...], *skills: Skill) -> SkillTree:
    return SkillTree(species, {s.key: s for s in skills})


def _base(name: str, max_rank: int = 5, ranks: tuple[dict, ...] = (), more: tuple[str, ...] = ()) -> Skill:
    """A base attack. Its rank 1 text is the move's description; `more`
    says what the ranks after that do (damaging moves: +15% each, unsaid)."""
    return Skill(_key(name), name, "base", name, max_rank, ranks=ranks, text=(describe(MOVES[name]),) + more)


def _move(name: str, level: int, parent: str, max_rank: int = 5, stage: int = 0, ranks: tuple[dict, ...] = (),
          more: tuple[str, ...] = ()) -> Skill:
    return Skill(_key(name), name, "move", name, max_rank, level, parent, stage, ranks,
                 (describe(MOVES[name]),) + more)


def _mod(name: str, of: str, level: int, ranks: tuple[dict, ...], text: tuple[str, ...], stage: int = 0) -> Skill:
    """A modifier of the move skill `of`, with one entry in `ranks` and
    `text` per rank."""
    return Skill(_key(name), name, "modifier", of, len(ranks), level, of, stage, ranks, text)


def _chance(status: str, *chances: int) -> tuple[dict, ...]:
    return tuple({"status": status, "status_chance": c} for c in chances)


def _each(field_name: str, *values) -> tuple[dict, ...]:
    return tuple({field_name: v} for v in values)


def _percent(what: str, *chances: int) -> tuple[str, ...]:
    """Rank texts: "<what>: 10% chance ...", then just the new chance."""
    return (f"{what.format(chances[0])}",) + tuple(f"{c}% chance." for c in chances[1:])


def _stage_chance(stat: str, change: int, *chances: int) -> tuple[dict, ...]:
    return tuple({"stages": ((stat, change),), "stage_chance": c} for c in chances)


TREES = {t.species[0]: t for t in [
    _tree(
        ("bulbasaur", "ivysaur", "venusaur"),
        _base("Tackle"),
        _base("Growl", 2, ({}, SPREAD), ("Lowers every enemy's Attack.",)),
        _move("Leech Seed", 7, "growl", 3, ranks=({}, {"seed": 1 / 12}, {"seed": 1 / 8}),
              more=("Drains 1/12.", "Drains 1/8.")),
        _move("Vine Whip", 13, "tackle"),
        _move("Poison Powder", 20, "growl", 3, ranks=({}, {"stages": (("speed", -1),)}, {"stages": (("speed", -2),)}),
              more=("Also lowers its Speed 1 stage.", "Also lowers its Speed 2 stages.")),
        _move("Take Down", 20, "tackle"),  # TM09
        _move("Razor Leaf", 27, "vine_whip"),
        _move("Growth", 34, "leech_seed", 3,
              ranks=({}, {"stages": (("attack", 2),)}, {"stages": (("attack", 2), ("defense", 1))}),
              more=("Raises Attack 2 stages.", "Raises Attack 2 stages and Defense 1 stage.")),
        _move("Leaf Shield", 22, "growl", 3, stage=1, ranks=({}, {"shield": 3}, {"shield": 3, "spread": True}),
              more=("For 3 rounds.", "For 3 rounds, on the whole party.")),  # Gen 1's Reflect (TM33)
        _move("Sleep Powder", 41, "poison_powder", 3, stage=1, ranks=({}, {"sleep_bonus": 1}, {"sleep_bonus": 2}),
              more=("It sleeps 1 round longer.", "It sleeps 2 rounds longer.")),
        _move("Body Slam", 30, "take_down", stage=1),  # TM08
        _move("Solar Beam", 48, "razor_leaf", stage=1),
        _move("Double-Edge", 50, "body_slam", stage=2),  # TM10
        _move("Hyper Beam", 55, "solar_beam", stage=2),  # TM15
        _mod("Binding Vines", "vine_whip", 15, _chance("paralysis", 10, 20, 30),
             _percent("Vine Whip: {}% chance to paralyze.", 10, 20, 30)),
        _mod("Spreading Seeds", "leech_seed", 18, (SPREAD,), ("Leech Seed seeds every enemy.",)),
        _mod("Bloom", "growth", 36, _each("heal", 1 / 8, 1 / 6, 1 / 4),
             ("Growth also heals the user 1/8 of its max HP.", "Heals 1/6.", "Heals 1/4.")),
        _mod("Whirling Leaves", "razor_leaf", 32, (SPREAD_75,), ("Razor Leaf hits every enemy, at 75% damage.",),
             stage=1),
        _mod("Toxic Spores", "poison_powder", 28, ({"toxic": True},),
             ("Poison Powder's poison gets worse every round (Toxic).",), stage=1),
        _mod("Drowsy Cloud", "sleep_powder", 45, (SPREAD,), ("Sleep Powder hits every enemy.",), stage=2),
        _mod("Sunburn", "solar_beam", 50, _chance("burn", 10, 20, 30),
             _percent("Solar Beam: {}% chance to burn.", 10, 20, 30), stage=2),
        _mod("Quick Bloom", "solar_beam", 60, ({"charge": ""},), ("Solar Beam fires without charging.",), stage=2),
    ),
    _tree(
        ("pidgey", "pidgeotto", "pidgeot"),
        _base("Gust"),
        _base("Sand-Attack", 2, ({}, SPREAD), ("Lowers every enemy's accuracy.",)),
        _move("Quick Attack", 12, "gust"),
        _move("Whirlwind", 19, "sand_attack", 2, ranks=({}, {"stages": (("speed", -2),)}),
              more=("Lowers their Speed 2 stages.",)),
        _move("Wing Attack", 28, "gust"),
        _move("Double-Edge", 30, "quick_attack", stage=1),  # TM10
        _move("Agility", 36, "whirlwind", 2, ranks=({}, {"stages": (("speed", 3),)}),
              more=("Raises its Speed 3 stages.",)),
        _move("Sky Attack", 44, "wing_attack", stage=2),  # TM43
        _mod("Gale Force", "gust", 10, _stage_chance("speed", -1, 10, 20, 30),
             _percent("Gust: {}% chance to lower the target's Speed.", 10, 20, 30)),
        _mod("Swift Strike", "quick_attack", 20, _each("flinch", 10, 20, 30),
             _percent("Quick Attack: {}% chance to make it flinch.", 10, 20, 30)),
        _mod("Twister", "gust", 25, (SPREAD_75,), ("Gust hits every enemy, at 75% damage.",), stage=1),
        _mod("Aerial Ace", "wing_attack", 33, ({"sure_hit": True, "crit_ratio": 8},),
             ("Wing Attack ignores accuracy drops and has a high critical-hit ratio.",), stage=1),
        _mod("Swoop", "sky_attack", 55, ({"charge": ""},), ("Sky Attack fires without charging.",), stage=2),
    ),
    _tree(
        ("rattata", "raticate"),
        _base("Tackle"),
        _base("Tail Whip", 2, ({}, SPREAD), ("Lowers every enemy's Defense.",)),
        _move("Quick Attack", 7, "tackle"),
        _move("Hyper Fang", 14, "quick_attack"),
        _move("Focus Energy", 23, "tail_whip", 1),
        _move("Body Slam", 25, "tackle"),  # TM08
        _move("Super Fang", 34, "hyper_fang", 1),
        _move("Hyper Beam", 45, "super_fang", stage=1),  # TM15
        _mod("Frenzy", "quick_attack", 12, ({"hits": (2, 2)},), ("Quick Attack hits twice.",)),
        _mod("Sharp Fangs", "hyper_fang", 18, _each("flinch", 20, 30, 40),
             _percent("Hyper Fang: {}% chance to make it flinch.", 20, 30, 40)),
        _mod("Laser Focus", "focus_energy", 28, ({"stages": (("attack", 1),)},),
             ("Focus Energy also raises Attack 1 stage.",)),
        _mod("Gnaw", "super_fang", 40, ({"drain": 0.5},), ("Super Fang heals the user half the damage dealt.",),
             stage=1),
    ),
    _tree(
        ("caterpie", "metapod", "butterfree"),
        _base("Tackle"),
        _base("String Shot", 2, ({}, SPREAD), ("Lowers every enemy's Speed.",)),
        _move("Harden", 7, "string_shot", 2, stage=1, ranks=({}, {"stages": (("defense", 2),)}),
              more=("Raises its Defense 2 stages.",)),
        _move("Confusion", 12, "tackle", stage=2),
        _move("Poison Powder", 15, "string_shot", 1, stage=2),
        _move("Stun Spore", 16, "poison_powder", 1, stage=2),
        _move("Sleep Powder", 17, "stun_spore", 1, stage=2),
        _move("Supersonic", 21, "confusion", 1, stage=2),
        _move("Mega Drain", 25, "confusion", stage=2),  # TM21
        _move("Whirlwind", 26, "supersonic", 1, stage=2),
        _move("Psybeam", 32, "confusion", stage=2),
        _mod("Compound Eyes", "supersonic", 24, _each("confuse", 70, 85, 100),
             ("Supersonic: 70% chance to work.", "85% chance.", "Always works."), stage=2),
        _mod("Mind Bend", "psybeam", 35, _each("confuse", 20, 30, 40),
             _percent("Psybeam: {}% chance to confuse.", 20, 30, 40), stage=2),
        _mod("Powder Cloud", "sleep_powder", 38, (SPREAD,), ("Sleep Powder hits every enemy.",), stage=2),
    ),
    _tree(
        ("weedle", "kakuna", "beedrill"),
        _base("Poison Sting"),
        _base("String Shot", 2, ({}, SPREAD), ("Lowers every enemy's Speed.",)),
        _move("Harden", 7, "string_shot", 2, stage=1, ranks=({}, {"stages": (("defense", 2),)}),
              more=("Raises its Defense 2 stages.",)),
        _move("Fury Attack", 12, "poison_sting", stage=2),
        _move("Focus Energy", 16, "harden", 1, stage=2),
        _move("Twineedle", 20, "fury_attack", stage=2),
        _move("Swords Dance", 25, "focus_energy", 1, stage=2),  # TM03
        _move("Pin Missile", 30, "twineedle", stage=2),
        _move("Agility", 35, "focus_energy", 1, stage=2),
        _mod("Venom Barbs", "poison_sting", 5, _chance("poison", 40, 50, 60),
             _percent("Poison Sting: {}% chance to poison.", 40, 50, 60)),
        _mod("Toxic Barbs", "twineedle", 28, ({"toxic": True},), ("Twineedle's poison gets worse every round.",),
             stage=2),
        _mod("Skill Link", "pin_missile", 40, ({"hits": (5, 5)},), ("Pin Missile always hits 5 times.",), stage=2),
    ),
    _tree(
        ("oddish", "gloom", "vileplume"),
        _base("Absorb"),
        _move("Poison Powder", 15, "absorb", 1),
        _move("Stun Spore", 17, "poison_powder", 1),
        _move("Sleep Powder", 19, "stun_spore", 1),
        _move("Acid", 24, "absorb"),
        _move("Mega Drain", 25, "absorb", stage=1),  # TM21
        _move("Petal Dance", 33, "acid"),
        _move("Solar Beam", 46, "petal_dance"),
        _mod("Deep Roots", "absorb", 10, _each("drain", 0.65, 0.8, 1.0),
             ("Absorb heals 65% of the damage dealt.", "80%.", "All of it.")),
        _mod("Corrosive", "acid", 28, _stage_chance("defense", -1, 50, 70, 90),
             _percent("Acid: {}% chance to lower Defense.", 50, 70, 90)),
        _mod("Spore Cloud", "stun_spore", 30, (SPREAD,), ("Stun Spore hits every enemy.",), stage=1),
        _mod("Calm Bloom", "petal_dance", 40, ({"self_confuse": False},),
             ("Petal Dance no longer confuses the user.",), stage=1),
    ),
    _tree(
        ("bellsprout", "weepinbell", "victreebel"),
        _base("Vine Whip"),
        _base("Growth", 2, ({}, {"stages": (("attack", 2),)}), ("Raises its Attack 2 stages.",)),
        _move("Wrap", 13, "vine_whip"),
        _move("Poison Powder", 15, "growth", 1),
        _move("Sleep Powder", 18, "poison_powder", 1),
        _move("Stun Spore", 21, "poison_powder", 1),
        _move("Acid", 26, "wrap"),
        _move("Swords Dance", 30, "growth", 1, stage=1),  # TM03
        _move("Razor Leaf", 33, "vine_whip"),
        _move("Slam", 42, "wrap"),
        _mod("Whiplash", "vine_whip", 10, _each("flinch", 10, 20, 30),
             _percent("Vine Whip: {}% chance to make it flinch.", 10, 20, 30)),
        _mod("Tight Grip", "wrap", 16, _each("bind", 1 / 12, 1 / 8),
             ("Wrap: 1/12 of its max HP each round.", "1/8.")),
        _mod("Gastro Acid", "acid", 30, _stage_chance("defense", -1, 50, 70, 90),
             _percent("Acid: {}% chance to lower Defense.", 50, 70, 90)),
        _mod("Leaf Storm", "razor_leaf", 38, (SPREAD_75,), ("Razor Leaf hits every enemy, at 75% damage.",),
             stage=1),
    ),
    _tree(
        ("pikachu",),  # Raichu evolves by stone (not in yet)
        _base("Thunder Shock"),
        _base("Growl", 2, ({}, SPREAD), ("Lowers every enemy's Attack.",)),
        _move("Thunder Wave", 9, "growl", 1),
        _move("Quick Attack", 16, "thunder_shock"),
        _move("Swift", 26, "quick_attack"),
        _move("Thunderbolt", 30, "thunder_shock"),  # TM24
        _move("Agility", 33, "thunder_wave", 1),
        _move("Thunder", 43, "thunderbolt"),
        _mod("Static", "thunder_shock", 12, _chance("paralysis", 20, 30, 40),
             _percent("Thunder Shock: {}% chance to paralyze.", 20, 30, 40)),
        _mod("Chain Lightning", "thunderbolt", 38, (SPREAD_75,), ("Thunderbolt hits every enemy, at 75% damage.",)),
        _mod("Thunderstorm", "thunder", 48, _chance("paralysis", 20, 30, 40),
             _percent("Thunder: {}% chance to paralyze.", 20, 30, 40)),
    ),
    _tree(
        ("seel", "dewgong"),
        _base("Headbutt"),
        _move("Water Gun", 10, "headbutt"),  # TM12
        _move("Bubble Beam", 25, "water_gun"),  # TM11
        _move("Growl", 30, "headbutt", 2, ranks=({}, SPREAD), more=("Lowers every enemy's Attack.",)),
        _move("Aurora Beam", 35, "headbutt"),
        _move("Rest", 40, "growl", 1),
        _move("Surf", 40, "bubble_beam", stage=1),  # HM03
        _move("Take Down", 45, "headbutt"),  # TM09
        _move("Ice Beam", 50, "aurora_beam"),
        _move("Blizzard", 55, "ice_beam", stage=1),  # TM14
        _mod("Hard Head", "headbutt", 15, _each("flinch", 40, 50, 60),
             _percent("Headbutt: {}% chance to make it flinch.", 40, 50, 60)),
        _mod("Frostbite", "aurora_beam", 38, _stage_chance("attack", -1, 30, 50, 70),
             _percent("Aurora Beam: {}% chance to lower Attack.", 30, 50, 70)),
        _mod("Deep Freeze", "ice_beam", 52, _chance("freeze", 20, 30),
             _percent("Ice Beam: {}% chance to freeze.", 20, 30), stage=1),
    ),
    _tree(
        ("shellder",),  # Cloyster evolves by stone (not in yet)
        _base("Tackle"),
        _base("Withdraw", 2, ({}, {"stages": (("defense", 2),)}), ("Raises its Defense 2 stages.",)),
        _move("Water Gun", 10, "tackle"),  # TM12
        _move("Supersonic", 18, "withdraw", 1),
        _move("Clamp", 23, "water_gun"),
        _move("Bubble Beam", 25, "water_gun"),  # TM11
        _move("Aurora Beam", 30, "clamp"),
        _move("Leer", 39, "supersonic", 2, ranks=({}, SPREAD), more=("Lowers every enemy's Defense.",)),
        _move("Ice Beam", 50, "aurora_beam"),
        _mod("Shell Armor", "withdraw", 20, ({"heal": 1 / 8},), ("Withdraw also heals the user 1/8 of its max HP.",)),
        _mod("Iron Jaws", "clamp", 26, _each("bind", 1 / 12, 1 / 8), ("Clamp: 1/12 of its max HP each round.", "1/8.")),
        _mod("Icicle", "aurora_beam", 34, _chance("freeze", 10, 20, 30),
             _percent("Aurora Beam: {}% chance to freeze.", 10, 20, 30)),
    ),
    _tree(
        ("psyduck", "golduck"),
        _base("Scratch"),
        _move("Water Gun", 8, "scratch"),  # TM12
        _move("Bubble Beam", 20, "water_gun"),  # TM11
        _move("Tail Whip", 28, "scratch", 2, ranks=({}, SPREAD), more=("Lowers every enemy's Defense.",)),
        _move("Confusion", 36, "tail_whip"),
        _move("Fury Swipes", 43, "scratch"),
        _move("Ice Beam", 45, "bubble_beam", stage=1),  # TM13
        _move("Hydro Pump", 52, "bubble_beam"),
        _mod("Swift Swim", "water_gun", 12, ({"priority": 1},), ("Water Gun always goes first.",)),
        _mod("Headache", "confusion", 38, _each("confuse", 20, 30, 40),
             _percent("Confusion: {}% chance to confuse.", 20, 30, 40)),
        _mod("Frenzied Claws", "fury_swipes", 45, ({"hits": (3, 5)},), ("Fury Swipes hits 3-5 times.",)),
    ),
    _tree(
        ("horsea", "seadra"),
        _base("Bubble"),
        _move("Smokescreen", 19, "bubble", 2, ranks=({}, SPREAD), more=("Lowers every enemy's accuracy.",)),
        _move("Bubble Beam", 20, "bubble"),  # TM11
        _move("Leer", 24, "smokescreen", 2, ranks=({}, SPREAD), more=("Lowers every enemy's Defense.",)),
        _move("Water Gun", 30, "bubble"),
        _move("Agility", 37, "leer", 1),
        _move("Ice Beam", 40, "bubble_beam", stage=1),  # TM13
        _move("Hydro Pump", 45, "water_gun"),
        _mod("Swift Current", "bubble", 10, ({"priority": 1},), ("Bubble always goes first.",)),
        _mod("Thick Ink", "smokescreen", 22, ({"stages": (("accuracy", -2),)},),
             ("Smokescreen lowers accuracy 2 stages.",)),
        _mod("Sniper", "water_gun", 32, ({"crit_ratio": 8},), ("Water Gun has a high critical-hit ratio.",)),
    ),
    _tree(
        ("jynx",),
        _base("Pound"),
        _base("Lovely Kiss", 1),
        _move("Lick", 18, "pound"),
        _move("Double Slap", 23, "pound"),
        _move("Ice Punch", 31, "lick"),
        _move("Psychic", 35, "lovely_kiss"),  # TM29
        _move("Body Slam", 39, "double_slap"),
        _move("Thrash", 47, "body_slam"),
        _move("Blizzard", 58, "ice_punch"),
        _mod("Sweet Kiss", "lovely_kiss", 20, _chance("sleep", 85, 95),
             ("Lovely Kiss: 85% chance to work.", "95% chance.")),
        _mod("Frost Touch", "ice_punch", 34, _chance("freeze", 20, 30),
             _percent("Ice Punch: {}% chance to freeze.", 20, 30)),
        _mod("Whiteout", "blizzard", 60, (SPREAD_75,), ("Blizzard hits every enemy, at 75% damage.",)),
    ),
    _tree(
        ("lapras",),
        _base("Water Gun"),
        _base("Growl", 2, ({}, SPREAD), ("Lowers every enemy's Attack.",)),
        _move("Sing", 16, "growl", 1),
        _move("Body Slam", 25, "water_gun"),
        _move("Confuse Ray", 31, "sing", 1),
        _move("Ice Beam", 38, "water_gun"),
        _move("Hydro Pump", 46, "ice_beam"),
        _move("Blizzard", 50, "ice_beam"),  # TM14
        _mod("Siren Song", "sing", 20, _chance("sleep", 70, 85, 100),
             ("Sing: 70% chance to work.", "85% chance.", "Always works.")),
        _mod("Freeze-Dry", "ice_beam", 40, _chance("freeze", 20, 30),
             _percent("Ice Beam: {}% chance to freeze.", 20, 30)),
        _mod("Tidal Wave", "hydro_pump", 50, (SPREAD_75,), ("Hydro Pump hits every enemy, at 75% damage.",)),
    ),
]}


@cache
def stand_in_tree(species: str) -> SkillTree:
    """For lines without a tree yet: Tackle as their only skill."""
    return _tree((species,), _base("Tackle"))
