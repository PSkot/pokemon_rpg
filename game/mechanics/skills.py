"""Skill trees: how Pokémon get and improve their moves (docs/skill_trees.md).

Each evolution line has a tree of skills, bought with skill points (1 per
level from Lv6). A skill opens once the Pokémon has its level, all its
parent skills and its evolution stage. Kinds:

- moves: every move of the line's Gen 1 learnset (and TMs) is one skill
  (1 point), linked by paths (Vine Whip opens Razor Leaf). The first free
  ones are known from the start; the first of all is the basic attack
  (Fight). Learned moves are used in battle once equipped (`MAX_EQUIPPED`).
- buffs: each move has its own branches of buffs, 1-5 ranks each, that
  change it (more power, a status chance, hitting every enemy, wounds, ...);
  deeper buffs need the ones before them.
- links: need two moves, and make one set off the other when it lands.

A buff's or link's rank is a set of changes to its move's fields (see
moves.Move); `effective_move` adds up every learned one (`apply_changes`).
A tree holds far more than the 95 points a Lv100 Pokémon has: builds
choose.
"""

from dataclasses import dataclass, field, replace
from fractions import Fraction
from functools import cache

from .moves import MOVES, STAT_WORDS, Move

FIRST_POINT_LEVEL = 5   # skill points = level − this
MAX_EQUIPPED = 4


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    kind: str      # "move", "buff" or "link"
    move: str      # move: its move (in MOVES); buff/link: the skill key of the move it changes
    max_rank: int = 1
    level: int = 0     # opens at this level
    parents: tuple[str, ...] = ()  # skill keys: needs all of these first
    stage: int = 0     # evolution stage needed (0 = the line's first species)
    # What each rank changes (rank 1 first). A rank's entry is the full set
    # of changes at that rank, not added to the ones before.
    ranks: tuple[dict, ...] = field(default=(), hash=False)
    text: tuple[str, ...] = ()  # what each rank does, in words (rank 1 first; moves: none)
    free: bool = False  # a move known from the start, at no cost
    short: str = ""     # its name in the tree, under its move ("" = `name`)

    @property
    def label(self) -> str:
        return self.short or self.name

    def changes(self, rank: int) -> dict:
        return self.ranks[min(rank, len(self.ranks)) - 1] if self.ranks and rank else {}


@dataclass(frozen=True)
class SkillTree:
    species: tuple[str, ...]   # the line's species keys, by stage
    skills: dict[str, Skill] = field(hash=False)  # by key, in tree order

    @property
    def moves(self) -> list[Skill]:
        return [s for s in self.skills.values() if s.kind == "move"]

    @property
    def base(self) -> list[Skill]:
        """The moves known from the start."""
        return [s for s in self.skills.values() if s.free]

    @property
    def basic(self) -> Skill:
        """The basic attack: the first free move."""
        return self.base[0]

    @property
    def cost(self) -> int:
        """Points to learn everything."""
        return sum(s.max_rank for s in self.skills.values() if not s.free)

    def owner(self, key: str) -> str:
        """The move skill `key` belongs to (itself, for a move)."""
        skill = self.skills[key]
        return key if skill.kind == "move" else skill.move

    def total_points(self, level: int) -> int:
        return max(0, level - FIRST_POINT_LEVEL)

    def spent(self, ranks: dict[str, int]) -> int:
        """Points in `ranks` (free moves cost nothing)."""
        return sum(r for key, r in ranks.items() if key in self.skills and not self.skills[key].free)

    def why_not(self, ranks: dict[str, int], key: str, level: int, stage: int) -> str:
        """Why skill `key` can't be learned or ranked up now ("" if it can)."""
        skill, rank = self.skills[key], ranks.get(key, 0)
        if rank >= skill.max_rank:
            return "Max rank" if skill.max_rank > 1 else "Learned"
        if stage < skill.stage:
            return f"Needs {self.species[skill.stage].capitalize()}"
        if level < skill.level:
            return f"Opens at Lv{skill.level}"
        missing = [self.skills[p].name for p in skill.parents if not ranks.get(p)]
        if missing:
            return f"Needs {' and '.join(missing)}"
        if self.spent(ranks) >= self.total_points(level):
            return "No skill points"
        return ""

    def effective_move(self, ranks: dict[str, int], key: str) -> Move:
        """Move skill `key`'s move with its learned buffs and links applied."""
        move = MOVES[self.skills[key].move]
        for node in self.skills.values():
            if node.kind != "move" and node.move == key and ranks.get(node.key):
                move = apply_changes(move, node.changes(ranks[node.key]))
        return move

    def auto_build(self, level: int, stage: int) -> tuple[dict[str, int], list[str]]:
        """Ranks and equipped moves for a Pokémon that builds itself (wild
        ones): every move it can learn, in level order, equipping the last 4
        learned (as in Gen 1). The rest of its points go into the buffs of
        the basic attack and the equipped moves (a rank each in turn), then
        their links, then whatever else is open."""
        ranks = {s.key: 1 for s in self.base}
        learned = [s.key for s in self.base[1:]]
        for skill in sorted((s for s in self.moves if not s.free), key=lambda s: s.level):
            if not self.why_not(ranks, skill.key, level, stage):
                ranks[skill.key] = 1
                learned.append(skill.key)
        equipped = learned[-MAX_EQUIPPED:]
        used = {self.basic.key, *equipped}
        nodes = [s for s in self.skills.values() if s.kind != "move"]
        for keys in ([s.key for s in nodes if s.kind == "buff" and s.move in used],
                     [s.key for s in nodes if s.kind == "link" and s.move in used],
                     [s.key for s in self.skills.values()]):
            spending = True
            while spending:
                spending = False
                for key in keys:
                    if not self.why_not(ranks, key, level, stage):
                        ranks[key] = ranks.get(key, 0) + 1
                        spending = True
        return ranks, equipped


# --- changing a move ------------------------------------------------------

ADDED = {"status_chance", "stage_chance", "confuse", "flinch", "seed", "bind", "shield", "drain", "heal",
         "priority", "sleep_bonus", "bleed", "scale", "crit_ratio", "recoil"}
CHANCES = {"status_chance", "stage_chance", "confuse", "flinch"}


def _add_stages(old: tuple, extra: tuple) -> tuple:
    total = dict(old)
    for stat, change in extra:
        total[stat] = total.get(stat, 0) + change
    return tuple((stat, change) for stat, change in total.items() if change)


def apply_changes(move: Move, changes: dict) -> Move:
    """`move` with a buff's changes: numbers add up (chances to at most
    100%), stage changes add per stat, triggers join; other fields are set.
    A status only lands on a move without one (or adds to the same one's
    chance); stages added to a damaging move without any bring their own
    chance."""
    new = {}
    clash = move.status and changes.get("status", move.status) != move.status  # (a move has one status)
    for name, value in changes.items():
        old = getattr(move, name)
        if clash and name in ("status", "status_chance"):
            continue
        if name == "status":
            new["status"] = value
        elif name == "status_chance" and not move.status:
            new[name] = value
        elif name == "stage_chance" and not move.stages:
            new[name] = value
        elif name in ADDED:
            new[name] = old + value
        elif name in ("stages", "self_stages"):
            new[name] = _add_stages(old, value)
        elif name == "triggers":
            new[name] = old + value
        else:
            new[name] = value
    for name in CHANCES & new.keys():
        new[name] = min(100, new[name])
    if "recoil" in new:
        new["recoil"] = max(0.0, new["recoil"])
    return replace(move, **new)


# --- buff templates ---------------------------------------------------------
# Every move gets its own branches of buffs, by what kind of move it is
# (`_buffs`): numbers below are per rank.

def _key(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


def _frac(share: float) -> str:
    return str(Fraction(share).limit_denominator(48))


def _stages_text(stat: str, n: int, whose: str = "its") -> str:
    return f"{'Raises' if n > 0 else 'Lowers'} {whose} {STAT_WORDS[stat]} {abs(n)} more stage{'s' if abs(n) > 1 else ''}."


# A damaging move's rider, by its type: (word, rank changes, rank texts).
def _status_rider(status: str, step: int, verb: str):
    return (tuple({"status": status, "status_chance": step * r} for r in (1, 2, 3)),
            tuple(f"+{step * r}% chance to {verb}." for r in (1, 2, 3)))


def _flinch_rider():
    return (tuple({"flinch": 10 * r} for r in (1, 2, 3)),
            tuple(f"+{10 * r}% chance to make it flinch." for r in (1, 2, 3)))


def _stage_rider(stat: str):
    return (tuple({"stages": ((stat, -1),), "stage_chance": 10 * r} for r in (1, 2, 3)),
            tuple(f"{10 * r}% chance to lower its {STAT_WORDS[stat]}." for r in (1, 2, 3)))


RIDERS = {
    "fire": ("Searing", lambda: _status_rider("burn", 10, "burn")),
    "electric": ("Crackling", lambda: _status_rider("paralysis", 10, "paralyze")),
    "ice": ("Chilling", lambda: _status_rider("freeze", 5, "freeze")),
    "poison": ("Venomous", lambda: _status_rider("poison", 10, "poison")),
    "bug": ("Venomous", lambda: _status_rider("poison", 10, "poison")),
    "grass": ("Draining", lambda: (tuple({"drain": 0.15 * r} for r in (1, 2, 3)),
                                   tuple(f"Heals the user {15 * r}% of the damage dealt." for r in (1, 2, 3)))),
    "water": ("Rippling", lambda: _stage_rider("speed")),
    "ground": ("Dusting", lambda: _stage_rider("accuracy")),
    "psychic": ("Bewildering", lambda: (tuple({"confuse": 10 * r} for r in (1, 2, 3)),
                                        tuple(f"+{10 * r}% chance to confuse." for r in (1, 2, 3)))),
    "ghost": ("Haunting", lambda: (tuple({"confuse": 10 * r} for r in (1, 2, 3)),
                                   tuple(f"+{10 * r}% chance to confuse." for r in (1, 2, 3)))),
}
SECOND_STAT = {"attack": "defense", "defense": "attack", "accuracy": "speed", "speed": "accuracy"}
# Lowering an enemy's stat can raise one of the user's (Leer → Attack).
MIRROR_STAT = {"attack": "defense", "defense": "attack", "accuracy": "speed", "speed": "speed"}
BLEED = (1 / 16, 1 / 12, 1 / 8)


def _node(move_key: str, word: str, move_name: str, level: int, parents: tuple[str, ...],
          ranks: tuple[dict, ...], text: tuple[str, ...], stage: int = 0) -> Skill:
    return Skill(f"{move_key}_{_key(word)}", f"{word} {move_name}", "buff", move_key, len(ranks), level, parents,
                 stage, ranks, text, short=word)


def _bleed_ranks(n: int) -> tuple[tuple[dict, ...], tuple[str, ...]]:
    return (tuple({"bleed": b} for b in BLEED[:n]),
            tuple(f"Wounds it: {_frac(b)} of its max HP each round for 3 rounds." for b in BLEED[:n]))


def _quick(k: str, name: str, level: int, parent: str) -> Skill:
    return _node(k, "Quick", name, level, (parent,), ({"priority": 1},), ("Always goes first.",))


def _buffs(move_skill: Skill, last_stage: int) -> list[Skill]:
    """The buffs of one move, by what kind of move it is."""
    k, m = move_skill.key, MOVES[move_skill.move]
    name, base = m.name, move_skill.level
    if m.damaging:
        return _damaging_buffs(k, m, base, last_stage)
    if m.target == "enemy" and m.stages and not (m.status or m.confuse or m.seed):
        return _lowering_buffs(k, m, base)
    if m.target == "self" and m.stages:
        return _raising_buffs(k, m, base)
    if m.status or m.confuse:
        return _inflicting_buffs(k, m, base)
    nodes = []
    if m.seed:
        nodes.append(_node(k, "Deep-Rooted", name, base, (k,),
                           tuple({"seed": s} for s in (1 / 48, 1 / 24, 1 / 16)),
                           tuple(f"Drains {_frac(1 / 16 + s)} of its max HP." for s in (1 / 48, 1 / 24, 1 / 16))))
    if m.shield:
        nodes.append(_node(k, "Thick", name, base, (k,), ({"shield": 1}, {"shield": 2}),
                           ("Lasts 1 round longer.", "Lasts 2 rounds longer.")))
    if m.focus:
        nodes.append(_node(k, "Fired-Up", name, base, (k,), ({"self_stages": (("attack", 1),)},
                                                             {"self_stages": (("attack", 2),)}),
                           ("Also raises the user's Attack 1 stage.", "Also raises it 2 stages.")))
    first = nodes[0].key if nodes else k
    if m.target == "enemy" and not m.spread:
        nodes.append(_node(k, "Wide", name, base + 6, (first,), ({"spread": True},), ("Works on every enemy.",)))
    if m.target == "ally" and not m.spread:
        nodes.append(_node(k, "Shared", name, base + 6, (first,), ({"spread": True},), ("Works on the whole party.",)))
    if m.target == "enemy":
        nodes.append(_node(k, "Lingering", name, base + 10, (first,), *_bleed_ranks(2)))
    if m.target != "enemy":
        nodes.append(_node(k, "Renewing", name, base + 8, (first,),
                           tuple({"heal": h} for h in (1 / 16, 1 / 8, 1 / 4)),
                           tuple(f"Heals the user {_frac(h)} of its max HP." for h in (1 / 16, 1 / 8, 1 / 4))))
    nodes.append(_quick(k, name, base + 12, first))
    return nodes


def _damaging_buffs(k: str, m: Move, base: int, last_stage: int) -> list[Skill]:
    name = m.name
    nodes = []
    rider_word, rider = RIDERS.get(m.type, ("Staggering", _flinch_rider))
    rider_ranks, rider_text = rider()
    if m.stages and "stages" in rider_ranks[0]:  # it lowers a stat already: just more often
        stat = STAT_WORDS[m.stages[0][0]]
        rider_ranks = tuple({"stage_chance": r["stage_chance"]} for r in rider_ranks)
        rider_text = tuple(f"+{r['stage_chance']}% chance to lower its {stat}." for r in rider_ranks)
    potent = None
    if not m.halve:
        potent = _node(k, "Potent", name, base, (k,), tuple({"scale": 0.08 * r} for r in range(1, 6)),
                       tuple(f"+{8 * r}% power." for r in range(1, 6)))
        nodes.append(potent)
    rider_node = _node(k, rider_word, name, base + 3, (k,), rider_ranks, rider_text)
    nodes.append(rider_node)
    nodes.append(_node(k, "Wounding", name, base + 16, (rider_node.key,), *_bleed_ranks(2)))
    trunk = potent.key if potent else rider_node.key
    if potent and m.crit_ratio <= 1:
        nodes.append(_node(k, "Keen", name, base + 6, (trunk,), tuple({"crit_ratio": r} for r in (1, 2, 3)),
                           ("Critical hits ×2 as likely.", "×3 as likely.", "×4 as likely.")))
    if not m.spread:
        nodes.append(_node(k, "Sweeping", name, base + 12, (trunk,),
                           ({"spread": True, "spread_share": 0.5}, {"spread": True, "spread_share": 0.75}),
                           ("Hits every enemy, at 50% damage.", "At 75% damage.")))
    # Buffs that take away a drawback.
    if m.charge:
        nodes.append(_node(k, "Instant", name, base + 20, (trunk,), ({"charge": ""},), ("Fires without charging.",)))
    if m.recharge:
        nodes.append(_node(k, "Tireless", name, base + 20, (trunk,), ({"recharge": False},),
                           ("No rest needed afterwards.",)))
    if m.recoil:
        nodes.append(_node(k, "Cushioned", name, base + 10, (trunk,),
                           ({"recoil": -m.recoil / 2}, {"recoil": -m.recoil}),
                           (f"Recoil: {_frac(m.recoil / 2)} of the damage.", "No recoil.")))
    if m.self_confuse:
        nodes.append(_node(k, "Calm", name, base + 14, (trunk,), ({"self_confuse": False},),
                           ("The user doesn't become confused.",)))
    # The capstone, deep down, at the line's last stage.
    deep = max(base + 24, 30)
    keen = next((n.key for n in nodes if n.short == "Keen"), trunk)
    if m.power >= 90:
        nodes.append(_node(k, "Swift", name, deep, (keen,), ({"priority": 1},), ("Always goes first.",),
                           stage=last_stage))
    elif m.hits[1] > 1:
        lo, hi = m.hits
        nodes.append(_node(k, "Relentless", name, deep, (keen,), ({"hits": (lo + 1, hi + 1)},),
                           (f"Hits {lo + 1}-{hi + 1} times." if lo != hi else f"Hits {lo + 1} times.",),
                           stage=last_stage))
    elif not m.halve:
        nodes.append(_node(k, "Twin", name, deep, (keen,), ({"hits": (2, 2), "scale": -0.3},),
                           ("Hits twice, at 30% less power each.",), stage=last_stage))
    return nodes


def _lowering_buffs(k: str, m: Move, base: int) -> list[Skill]:
    """Leer, Growl, Sand-Attack, ...: lowers an enemy's stat."""
    name, (stat, _) = m.name, m.stages[0]
    deep = _node(k, "Deep", name, base, (k,), ({"stages": ((stat, -1),)}, {"stages": ((stat, -2),)}),
                 (_stages_text(stat, -1), _stages_text(stat, -2)))
    nodes = [deep]
    wide = None
    if not m.spread:
        wide = _node(k, "Wide", name, base + 4, (k,), ({"spread": True},), ("Works on every enemy.",))
        nodes.append(wide)
    lingering = _node(k, "Lingering", name, base + 8, (deep.key,), *_bleed_ranks(3))
    nodes.append(lingering)
    other = SECOND_STAT[stat]
    nodes.append(_node(k, "Hexing", name, base + 12, ((wide or deep).key,),
                       ({"stages": ((other, -1),)}, {"stages": ((other, -2),)}),
                       (f"Also lowers its {STAT_WORDS[other]} 1 stage.", "2 stages.")))
    mine = MIRROR_STAT[stat]
    nodes.append(_node(k, "Emboldening", name, base + 16, (lingering.key,),
                       ({"self_stages": ((mine, 1),)}, {"self_stages": ((mine, 2),)}),
                       (f"Also raises the user's {STAT_WORDS[mine]} 1 stage.", "2 stages.")))
    nodes.append(_quick(k, name, base + 10, k))
    return nodes


def _raising_buffs(k: str, m: Move, base: int) -> list[Skill]:
    """Growth, Harden, Agility, ...: raises the user's stat."""
    name, (stat, _) = m.name, m.stages[0]
    greater = _node(k, "Greater", name, base, (k,), ({"stages": ((stat, 1),)}, {"stages": ((stat, 2),)}),
                    (_stages_text(stat, 1), _stages_text(stat, 2)))
    renewing = _node(k, "Renewing", name, base + 6, (k,), tuple({"heal": h} for h in (1 / 16, 1 / 8, 1 / 4)),
                     tuple(f"Heals the user {_frac(h)} of its max HP." for h in (1 / 16, 1 / 8, 1 / 4)))
    other = SECOND_STAT[stat] if stat != "accuracy" else "speed"
    fortifying = _node(k, "Fortifying", name, base + 10, (greater.key,),
                       ({"stages": ((other, 1),)}, {"stages": ((other, 2),)}),
                       (f"Also raises its {STAT_WORDS[other]} 1 stage.", "2 stages."))
    warding = _node(k, "Warding", name, base + 14, (renewing.key,), ({"shield": 2}, {"shield": 3}),
                    ("Halves the damage it takes for 2 rounds.", "For 3 rounds."))
    return [greater, renewing, fortifying, warding, _quick(k, name, base + 8, k)]


def _inflicting_buffs(k: str, m: Move, base: int) -> list[Skill]:
    """Poison Powder, Sleep Powder, Supersonic, ...: a status or confusion."""
    name = m.name
    field_name = "status_chance" if m.status else "confuse"
    chance = m.status_chance if m.status else m.confuse
    nodes = []
    if chance < 100:
        steps = [min(100 - chance, 8 * r) for r in (1, 2, 3)]
        nodes.append(_node(k, "Sure", name, base, (k,), tuple({field_name: s} for s in steps),
                           tuple(f"{chance + s}% chance to work." for s in steps)))
    first = nodes[0].key if nodes else k
    if not m.spread:
        nodes.append(_node(k, "Wide", name, base + 6, (k,), ({"spread": True},), ("Works on every enemy.",)))
    nodes.append(_node(k, "Lingering", name, base + 10, (first,), *_bleed_ranks(2)))
    if m.status == "poison":
        nodes.append(_node(k, "Toxic", name, base + 12, (first,), ({"toxic": True},),
                           ("Its poison gets worse every round.",)))
    elif m.status == "sleep":
        nodes.append(_node(k, "Deep", name, base + 12, (first,), ({"sleep_bonus": 1}, {"sleep_bonus": 2}),
                           ("It sleeps 1 round longer.", "2 rounds longer.")))
    elif m.status == "paralysis":
        nodes.append(_node(k, "Numbing", name, base + 12, (first,),
                           ({"stages": (("speed", -1),)}, {"stages": (("speed", -2),)}),
                           ("Also lowers its Speed 1 stage.", "2 stages.")))
    elif m.confuse:
        nodes.append(_node(k, "Dizzying", name, base + 12, (first,),
                           ({"stages": (("accuracy", -1),)}, {"stages": (("accuracy", -2),)}),
                           ("Also lowers its accuracy 1 stage.", "2 stages.")))
    nodes.append(_quick(k, name, base + 8, k))
    return nodes


# --- building trees -------------------------------------------------------

def _base(name: str) -> Skill:
    """A move known from the start."""
    return Skill(_key(name), name, "move", name, free=True)


def _move(name: str, level: int, parent: str, stage: int = 0) -> Skill:
    """A move, opened by `parent` (a move's skill key) at `level`."""
    return Skill(_key(name), name, "move", name, level=level, parents=(parent,), stage=stage)


@dataclass(frozen=True)
class Link:
    """A link skill: `source` sets off `target` (move names) with these
    chances per rank; needs both moves."""
    name: str
    source: str
    target: str
    level: int
    chances: tuple[int, ...]
    stage: int = 0


def _link(link: Link) -> Skill:
    src, dst, target_move = _key(link.source), _key(link.target), MOVES[link.target]
    ranks = tuple({"triggers": ((dst, target_move.name, c),)} for c in link.chances)
    text = tuple(f"{link.source}: {c}% chance to also use {link.target}." if c < 100
                 else f"{link.source} always also uses {link.target}." for c in link.chances)
    return Skill(_key(link.name), link.name, "link", src, len(ranks), link.level, (src, dst), link.stage, ranks, text)


def _tree(species: tuple[str, ...], *items: Skill | Link) -> SkillTree:
    """A line's tree: its moves (each followed by its buffs), then its links."""
    last_stage = len(species) - 1
    skills: dict[str, Skill] = {}
    for item in items:
        if isinstance(item, Skill):
            skills[item.key] = item
            for buff in _buffs(item, last_stage):
                skills[buff.key] = buff
    for item in items:
        if isinstance(item, Link):
            skill = _link(item)
            skills[skill.key] = skill
    return SkillTree(species, skills)


TREES = {t.species[0]: t for t in [
    _tree(
        ("bulbasaur", "ivysaur", "venusaur"),
        _base("Tackle"),
        _base("Growl"),
        _move("Leech Seed", 7, "growl"),
        _move("Vine Whip", 13, "tackle"),
        _move("Poison Powder", 20, "growl"),
        _move("Take Down", 20, "tackle"),  # TM09
        _move("Leaf Shield", 22, "leech_seed", stage=1),  # Gen 1's Reflect (TM33)
        _move("Razor Leaf", 27, "vine_whip"),
        _move("Body Slam", 30, "take_down", stage=1),  # TM08
        _move("Growth", 34, "leech_seed"),
        _move("Sleep Powder", 41, "poison_powder", stage=1),
        _move("Solar Beam", 48, "razor_leaf", stage=1),
        _move("Double-Edge", 50, "body_slam", stage=2),  # TM10
        _move("Hyper Beam", 55, "solar_beam", stage=2),  # TM15
        Link("Seeding Lash", "Vine Whip", "Leech Seed", 15, (15, 30, 45)),
        Link("Rough Play", "Tackle", "Growl", 8, (20, 40)),
        Link("Spore Storm", "Razor Leaf", "Poison Powder", 30, (10, 20, 30)),
        Link("Photosynthesis", "Growth", "Leaf Shield", 36, (50, 100), stage=1),
        Link("Drowsy Sun", "Solar Beam", "Sleep Powder", 50, (20, 40), stage=2),
    ),
    _tree(
        ("charmander", "charmeleon", "charizard"),
        _base("Scratch"),
        _base("Growl"),
        _move("Ember", 9, "scratch"),
        _move("Leer", 15, "growl"),
        _move("Swords Dance", 25, "leer", stage=1),  # TM03
        _move("Slash", 30, "scratch"),
        _move("Flamethrower", 38, "ember"),
        _move("Fire Spin", 46, "flamethrower"),
        _move("Fire Blast", 50, "flamethrower", stage=2),  # TM38
        _move("Earthquake", 55, "slash", stage=2),  # TM26
        Link("Smoldering Claws", "Scratch", "Ember", 11, (15, 30, 45)),
        Link("Menace", "Leer", "Growl", 17, (50, 100)),
        Link("Melting Heat", "Flamethrower", "Leer", 40, (30, 60)),
        Link("Blazing Slash", "Slash", "Fire Spin", 48, (20, 40), stage=1),
    ),
    _tree(
        ("squirtle", "wartortle", "blastoise"),
        _base("Tackle"),
        _base("Tail Whip"),
        _move("Bubble", 8, "tackle"),
        _move("Water Gun", 15, "bubble"),
        _move("Bite", 22, "tackle"),
        _move("Withdraw", 28, "tail_whip"),
        _move("Ice Beam", 30, "water_gun", stage=1),  # TM13
        _move("Skull Bash", 35, "bite", stage=1),
        _move("Hydro Pump", 42, "water_gun"),
        _move("Blizzard", 55, "ice_beam", stage=2),  # TM14
        Link("Splash Tackle", "Tackle", "Bubble", 10, (15, 30, 45)),
        Link("Snapping Jaws", "Bite", "Tail Whip", 24, (30, 60)),
        Link("Shell Counter", "Withdraw", "Tail Whip", 30, (50, 100)),
        Link("Frost Spray", "Hydro Pump", "Ice Beam", 46, (10, 20), stage=2),
    ),
    _tree(
        ("spearow", "fearow"),
        _base("Peck"),
        _base("Growl"),
        _move("Leer", 9, "growl"),
        _move("Fury Attack", 15, "peck"),
        _move("Swift", 20, "peck"),  # TM39
        _move("Whirlwind", 22, "leer"),  # TM04
        _move("Drill Peck", 29, "fury_attack"),
        _move("Agility", 36, "leer"),
        _move("Hyper Beam", 45, "drill_peck", stage=1),  # TM15
        Link("Harrying Pecks", "Fury Attack", "Leer", 17, (20, 40)),
        Link("Tailwind", "Whirlwind", "Agility", 38, (50, 100)),
    ),
    _tree(
        ("nidoran_f", "nidorina"),  # Nidoqueen evolves by stone (not in yet)
        _base("Tackle"),
        _base("Growl"),
        _move("Scratch", 8, "tackle"),
        _move("Poison Sting", 14, "tackle"),
        _move("Tail Whip", 21, "growl"),
        _move("Body Slam", 25, "tackle", stage=1),  # TM08
        _move("Bite", 29, "scratch"),
        _move("Fury Swipes", 36, "scratch"),
        _move("Double Kick", 43, "bite"),
        Link("Toxic Claws", "Scratch", "Poison Sting", 16, (15, 30)),
        Link("Taunting Bite", "Bite", "Growl", 31, (30, 60)),
    ),
    _tree(
        ("nidoran_m", "nidorino"),  # Nidoking evolves by stone (not in yet)
        _base("Tackle"),
        _base("Leer"),
        _move("Horn Attack", 8, "tackle"),
        _move("Poison Sting", 14, "tackle"),
        _move("Focus Energy", 21, "leer"),
        _move("Body Slam", 25, "tackle", stage=1),  # TM08
        _move("Fury Attack", 29, "horn_attack"),
        _move("Double Kick", 43, "horn_attack"),
        Link("Poison Horn", "Horn Attack", "Poison Sting", 16, (15, 30)),
        Link("Battle Cry", "Focus Energy", "Leer", 23, (50, 100)),
    ),
    _tree(
        ("pidgey", "pidgeotto", "pidgeot"),
        _base("Gust"),
        _base("Sand-Attack"),
        _move("Quick Attack", 12, "gust"),
        _move("Whirlwind", 19, "sand_attack"),
        _move("Wing Attack", 28, "gust"),
        _move("Double-Edge", 30, "quick_attack", stage=1),  # TM10
        _move("Agility", 36, "whirlwind"),
        _move("Sky Attack", 44, "wing_attack", stage=2),  # TM43
        Link("Dust Devil", "Gust", "Sand-Attack", 10, (20, 40)),
        Link("Slipstream", "Quick Attack", "Agility", 38, (15, 30), stage=1),
    ),
    _tree(
        ("rattata", "raticate"),
        _base("Tackle"),
        _base("Tail Whip"),
        _move("Quick Attack", 7, "tackle"),
        _move("Hyper Fang", 14, "quick_attack"),
        _move("Focus Energy", 23, "tail_whip"),
        _move("Body Slam", 25, "tackle"),  # TM08
        _move("Super Fang", 34, "hyper_fang"),
        _move("Hyper Beam", 45, "super_fang", stage=1),  # TM15
        Link("Nip and Tuck", "Quick Attack", "Tail Whip", 9, (20, 40)),
        Link("Gnashing Fangs", "Hyper Fang", "Super Fang", 36, (10, 20)),
    ),
    _tree(
        ("caterpie", "metapod", "butterfree"),
        _base("Tackle"),
        _base("String Shot"),
        _move("Harden", 7, "string_shot", stage=1),
        _move("Confusion", 12, "tackle", stage=2),
        _move("Poison Powder", 15, "string_shot", stage=2),
        _move("Stun Spore", 16, "poison_powder", stage=2),
        _move("Sleep Powder", 17, "stun_spore", stage=2),
        _move("Supersonic", 21, "confusion", stage=2),
        _move("Mega Drain", 25, "confusion", stage=2),  # TM21
        _move("Whirlwind", 26, "supersonic", stage=2),
        _move("Psybeam", 32, "confusion", stage=2),
        Link("Silk Shell", "Harden", "String Shot", 9, (50, 100), stage=1),
        Link("Scale Dust", "Psybeam", "Stun Spore", 34, (15, 30), stage=2),
    ),
    _tree(
        ("weedle", "kakuna", "beedrill"),
        _base("Poison Sting"),
        _base("String Shot"),
        _move("Harden", 7, "string_shot", stage=1),
        _move("Fury Attack", 12, "poison_sting", stage=2),
        _move("Focus Energy", 16, "harden", stage=2),
        _move("Twineedle", 20, "fury_attack", stage=2),
        _move("Swords Dance", 25, "focus_energy", stage=2),  # TM03
        _move("Pin Missile", 30, "twineedle", stage=2),
        _move("Agility", 35, "focus_energy", stage=2),
        Link("Webbed Sting", "Poison Sting", "String Shot", 5, (20, 40)),
        Link("Stinger Volley", "Pin Missile", "Poison Sting", 32, (20, 40), stage=2),
    ),
    _tree(
        ("oddish", "gloom", "vileplume"),
        _base("Absorb"),
        _move("Poison Powder", 15, "absorb"),
        _move("Stun Spore", 17, "poison_powder"),
        _move("Sleep Powder", 19, "stun_spore"),
        _move("Acid", 24, "absorb"),
        _move("Mega Drain", 25, "absorb", stage=1),  # TM21
        _move("Petal Dance", 33, "acid"),
        _move("Solar Beam", 46, "petal_dance"),
        Link("Spore Sap", "Absorb", "Poison Powder", 16, (15, 30)),
        Link("Pollen Dance", "Petal Dance", "Sleep Powder", 35, (15, 30), stage=1),
    ),
    _tree(
        ("bellsprout", "weepinbell", "victreebel"),
        _base("Vine Whip"),
        _base("Growth"),
        _move("Wrap", 13, "vine_whip"),
        _move("Poison Powder", 15, "growth"),
        _move("Sleep Powder", 18, "poison_powder"),
        _move("Stun Spore", 21, "poison_powder"),
        _move("Acid", 26, "wrap"),
        _move("Swords Dance", 30, "growth", stage=1),  # TM03
        _move("Razor Leaf", 33, "vine_whip"),
        _move("Slam", 42, "wrap"),
        Link("Snaring Vines", "Vine Whip", "Wrap", 15, (15, 30)),
        Link("Corroding Grip", "Wrap", "Acid", 28, (20, 40)),
    ),
    _tree(
        ("pikachu",),  # Raichu evolves by stone (not in yet)
        _base("Thunder Shock"),
        _base("Growl"),
        _move("Thunder Wave", 9, "growl"),
        _move("Quick Attack", 16, "thunder_shock"),
        _move("Swift", 26, "quick_attack"),
        _move("Thunderbolt", 30, "thunder_shock"),  # TM24
        _move("Agility", 33, "thunder_wave"),
        _move("Thunder", 43, "thunderbolt"),
        Link("Static Charge", "Quick Attack", "Thunder Wave", 18, (15, 30)),
        Link("Overcharge", "Agility", "Thunder Shock", 35, (50, 100)),
    ),
    _tree(
        ("seel", "dewgong"),
        _base("Headbutt"),
        _move("Water Gun", 10, "headbutt"),  # TM12
        _move("Bubble Beam", 25, "water_gun"),  # TM11
        _move("Growl", 30, "headbutt"),
        _move("Aurora Beam", 35, "headbutt"),
        _move("Rest", 40, "growl"),
        _move("Surf", 40, "bubble_beam", stage=1),  # HM03
        _move("Take Down", 45, "headbutt"),  # TM09
        _move("Ice Beam", 50, "aurora_beam"),
        _move("Blizzard", 55, "ice_beam", stage=1),  # TM14
        Link("Bellow", "Headbutt", "Growl", 32, (20, 40)),
        Link("Polar Spray", "Water Gun", "Aurora Beam", 37, (10, 20)),
    ),
    _tree(
        ("shellder",),  # Cloyster evolves by stone (not in yet)
        _base("Tackle"),
        _base("Withdraw"),
        _move("Water Gun", 10, "tackle"),  # TM12
        _move("Supersonic", 18, "withdraw"),
        _move("Clamp", 23, "water_gun"),
        _move("Bubble Beam", 25, "water_gun"),  # TM11
        _move("Aurora Beam", 30, "clamp"),
        _move("Leer", 39, "supersonic"),
        _move("Ice Beam", 50, "aurora_beam"),
        Link("Clam Shell", "Withdraw", "Clamp", 25, (25, 50)),
        Link("Icy Grip", "Clamp", "Aurora Beam", 32, (15, 30)),
    ),
    _tree(
        ("psyduck", "golduck"),
        _base("Scratch"),
        _move("Water Gun", 8, "scratch"),  # TM12
        _move("Bubble Beam", 20, "water_gun"),  # TM11
        _move("Tail Whip", 28, "scratch"),
        _move("Confusion", 36, "tail_whip"),
        _move("Fury Swipes", 43, "scratch"),
        _move("Ice Beam", 45, "bubble_beam", stage=1),  # TM13
        _move("Hydro Pump", 52, "bubble_beam"),
        Link("Headache", "Water Gun", "Confusion", 38, (10, 20)),
        Link("Flailing", "Fury Swipes", "Tail Whip", 45, (20, 40)),
    ),
    _tree(
        ("horsea", "seadra"),
        _base("Bubble"),
        _move("Smokescreen", 19, "bubble"),
        _move("Bubble Beam", 20, "bubble"),  # TM11
        _move("Leer", 24, "smokescreen"),
        _move("Water Gun", 30, "bubble"),
        _move("Agility", 37, "leer"),
        _move("Ice Beam", 40, "bubble_beam", stage=1),  # TM13
        _move("Hydro Pump", 45, "water_gun"),
        Link("Ink Jet", "Water Gun", "Smokescreen", 32, (20, 40)),
        Link("Riptide", "Agility", "Bubble Beam", 39, (25, 50)),
    ),
    _tree(
        ("jynx",),
        _base("Pound"),
        _base("Lovely Kiss"),
        _move("Lick", 18, "pound"),
        _move("Double Slap", 23, "pound"),
        _move("Ice Punch", 31, "lick"),
        _move("Psychic", 35, "lovely_kiss"),  # TM29
        _move("Body Slam", 39, "double_slap"),
        _move("Thrash", 47, "body_slam"),
        _move("Blizzard", 58, "ice_punch"),
        Link("Blown Kiss", "Double Slap", "Lovely Kiss", 25, (10, 20)),
        Link("Mind Freeze", "Psychic", "Ice Punch", 37, (15, 30)),
    ),
    _tree(
        ("lapras",),
        _base("Water Gun"),
        _base("Growl"),
        _move("Sing", 16, "growl"),
        _move("Body Slam", 25, "water_gun"),
        _move("Confuse Ray", 31, "sing"),
        _move("Ice Beam", 38, "water_gun"),
        _move("Hydro Pump", 46, "ice_beam"),
        _move("Blizzard", 50, "ice_beam"),  # TM14
        Link("Lullaby", "Water Gun", "Sing", 18, (10, 20)),
        Link("Haunting Song", "Sing", "Confuse Ray", 33, (25, 50)),
    ),
    _tree(
        ("geodude", "graveler", "golem"),  # Golem evolves by trade (not in yet)
        _base("Tackle"),
        _base("Defense Curl"),
        _move("Rock Throw", 11, "tackle"),
        _move("Harden", 21, "defense_curl"),
        _move("Rock Slide", 24, "rock_throw"),  # TM48
        _move("Earthquake", 26, "rock_throw"),
        _move("Body Slam", 30, "tackle", stage=1),  # TM08
        _move("Dig", 34, "earthquake", stage=1),  # TM28
        Link("Rolling Stone", "Tackle", "Rock Throw", 13, (15, 30)),
        Link("Avalanche", "Rock Slide", "Earthquake", 28, (10, 20), stage=1),
    ),
    _tree(
        ("onix",),  # Steelix comes later
        _base("Tackle"),
        _base("Screech"),
        _move("Bind", 14, "tackle"),  # (Gen 1: 15; Brock's Lv14 Onix knows it)
        _move("Rock Throw", 19, "tackle"),
        _move("Rock Slide", 28, "rock_throw"),  # TM48
        _move("Slam", 33, "bind"),
        _move("Earthquake", 38, "rock_throw"),  # TM26
        _move("Harden", 43, "screech"),
        Link("Crushing Coils", "Bind", "Screech", 16, (25, 50)),
        Link("Rumbling Rocks", "Rock Slide", "Screech", 30, (15, 30)),
    ),
    _tree(
        ("diglett", "dugtrio"),
        _base("Scratch"),
        _move("Growl", 15, "scratch"),
        _move("Dig", 19, "scratch"),
        _move("Sand-Attack", 24, "growl"),
        _move("Slash", 31, "scratch"),
        _move("Rock Slide", 35, "dig"),  # TM48
        _move("Earthquake", 40, "dig"),
        Link("Dust Cloud", "Dig", "Sand-Attack", 21, (20, 40)),
        Link("Tunneling Claws", "Scratch", "Dig", 26, (5, 10)),
    ),
    _tree(
        ("sandshrew", "sandslash"),
        _base("Scratch"),
        _move("Sand-Attack", 10, "scratch"),
        _move("Slash", 17, "scratch"),
        _move("Poison Sting", 24, "scratch"),
        _move("Dig", 28, "sand_attack"),  # TM28
        _move("Swift", 31, "slash"),
        _move("Fury Swipes", 38, "slash"),
        _move("Rock Slide", 40, "dig"),  # TM48
        _move("Earthquake", 45, "dig", stage=1),  # TM26
        Link("Sandstorm", "Slash", "Sand-Attack", 19, (20, 40)),
        Link("Barbed Claws", "Fury Swipes", "Poison Sting", 40, (15, 30)),
    ),
    _tree(
        ("ekans", "arbok"),
        _base("Wrap"),
        _base("Leer"),
        _move("Poison Sting", 10, "wrap"),
        _move("Bite", 17, "wrap"),
        _move("Glare", 24, "leer"),
        _move("Screech", 31, "glare"),
        _move("Dig", 33, "bite", stage=1),  # TM28
        _move("Acid", 38, "poison_sting"),
        Link("Venom Coils", "Wrap", "Poison Sting", 12, (15, 30)),
        Link("Paralyzing Gaze", "Bite", "Glare", 26, (15, 30)),
    ),
    _tree(
        ("jigglypuff",),  # Wigglytuff evolves by stone (not in yet)
        _base("Pound"),
        _base("Sing"),
        _move("Defense Curl", 14, "sing"),
        _move("Double Slap", 24, "pound"),
        _move("Rest", 29, "defense_curl"),
        _move("Body Slam", 34, "double_slap"),
        _move("Double-Edge", 39, "body_slam"),
        Link("Lullaby Slaps", "Double Slap", "Sing", 26, (10, 20)),
        Link("Heavy Sleeper", "Body Slam", "Sing", 36, (10, 20)),
    ),
    _tree(
        ("zubat", "golbat"),
        _base("Leech Life"),
        _move("Supersonic", 10, "leech_life"),
        _move("Bite", 15, "leech_life"),
        _move("Confuse Ray", 21, "supersonic"),
        _move("Wing Attack", 28, "bite"),
        _move("Swift", 32, "wing_attack"),  # TM39
        _move("Double-Edge", 38, "wing_attack", stage=1),  # TM10
        Link("Dizzying Bite", "Bite", "Supersonic", 17, (15, 30)),
        Link("Draining Swoop", "Wing Attack", "Leech Life", 30, (15, 30)),
    ),
    _tree(
        ("paras", "parasect"),
        _base("Scratch"),
        _move("Stun Spore", 13, "scratch"),
        _move("Leech Life", 20, "scratch"),
        _move("Mega Drain", 24, "leech_life"),  # TM21
        _move("Spore", 27, "stun_spore"),
        _move("Slash", 34, "scratch"),
        _move("Growth", 41, "spore"),
        _move("Solar Beam", 44, "mega_drain", stage=1),  # TM22
        Link("Spore Claws", "Scratch", "Stun Spore", 15, (10, 20)),
        Link("Fungal Feast", "Leech Life", "Spore", 29, (10, 20)),
    ),
    _tree(
        ("clefairy", "clefable"),  # Clefable evolves by stone (not in yet)
        _base("Pound"),
        _base("Growl"),
        _move("Sing", 13, "growl"),
        _move("Double Slap", 18, "pound"),
        _move("Defense Curl", 24, "growl"),
        _move("Body Slam", 30, "double_slap"),  # TM08
        _move("Thunder Wave", 34, "sing"),  # TM45
        _move("Psychic", 40, "thunder_wave"),  # TM29
        _move("Rest", 44, "defense_curl"),  # TM44
        Link("Moonlit Song", "Double Slap", "Sing", 20, (10, 20)),
        Link("Static Slam", "Body Slam", "Thunder Wave", 36, (15, 30)),
    ),
]}


@cache
def stand_in_tree(species: str) -> SkillTree:
    """For lines without a tree yet: Tackle as their only skill."""
    return _tree((species,), _base("Tackle"))
