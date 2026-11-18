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
"""

from dataclasses import dataclass, field, replace
from functools import cache

from .moves import MOVES, Move

TIER_LEVELS = (6, 10, 14, 18, 22, 27, 32, 38, 44, 50, 60, 75)
DEEP = {10: 4, 11: 6}  # tier index -> earlier picks the talent needs in its own path
MAX_EQUIPPED = 4


def key_of(name: str) -> str:
    """A move's key (saved in `Monster.equipped`): "Leech Seed" -> "leech_seed"."""
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


# --- moves by level --------------------------------------------------------
# Per line (its species by stage): (move, level, evolution stage needed),
# the moves known from the start (level 0) first; the first of them is the
# basic attack. Levels are Red/Blue's learn levels; strong moves and TMs
# open later and at later stages.

LEARNSETS = {
    ('bulbasaur', 'ivysaur', 'venusaur'): (
        ('Tackle', 0), ('Growl', 0), ('Leech Seed', 7), ('Vine Whip', 13), ('Poison Powder', 20),
        ('Leaf Shield', 22, 1), ('Take Down', 25, 1), ('Razor Leaf', 27), ('Body Slam', 30, 1),
        ('Growth', 34), ('Sleep Powder', 41, 1), ('Solar Beam', 48, 2), ('Double-Edge', 50, 2),
        ('Hyper Beam', 55, 2),
    ),
    ('charmander', 'charmeleon', 'charizard'): (
        ('Scratch', 0), ('Growl', 0), ('Ember', 9), ('Leer', 15), ('Swords Dance', 25, 1), ('Slash', 30),
        ('Flamethrower', 38, 1), ('Fire Spin', 46), ('Fire Blast', 50, 2), ('Earthquake', 55, 2),
    ),
    ('squirtle', 'wartortle', 'blastoise'): (
        ('Tackle', 0), ('Tail Whip', 0), ('Bubble', 8), ('Water Gun', 15), ('Bite', 22), ('Withdraw', 28),
        ('Ice Beam', 30, 1), ('Skull Bash', 35, 2), ('Hydro Pump', 42, 2), ('Blizzard', 55, 2),
    ),
    ('spearow', 'fearow'): (
        ('Peck', 0), ('Growl', 0), ('Leer', 9), ('Fury Attack', 15), ('Swift', 20), ('Whirlwind', 22),
        ('Drill Peck', 29, 1), ('Agility', 36), ('Hyper Beam', 45, 1),
    ),
    ('nidoran_f', 'nidorina'): (
        ('Tackle', 0), ('Growl', 0), ('Scratch', 8), ('Poison Sting', 14), ('Tail Whip', 21),
        ('Body Slam', 25, 1), ('Bite', 29), ('Fury Swipes', 36), ('Double Kick', 43),
    ),
    ('nidoran_m', 'nidorino'): (
        ('Tackle', 0), ('Leer', 0), ('Horn Attack', 8), ('Poison Sting', 14), ('Focus Energy', 21),
        ('Body Slam', 25, 1), ('Fury Attack', 29), ('Double Kick', 43),
    ),
    ('pidgey', 'pidgeotto', 'pidgeot'): (
        ('Gust', 0), ('Sand-Attack', 5), ('Quick Attack', 12), ('Whirlwind', 19), ('Wing Attack', 28),
        ('Double-Edge', 35, 2), ('Agility', 36), ('Sky Attack', 44, 2),
    ),
    ('rattata', 'raticate'): (
        ('Tackle', 0), ('Tail Whip', 0), ('Quick Attack', 7), ('Focus Energy', 23), ('Hyper Fang', 25, 1),
        ('Body Slam', 25, 1), ('Super Fang', 35, 1), ('Hyper Beam', 45, 1),
    ),
    ('caterpie', 'metapod', 'butterfree'): (
        ('Tackle', 0), ('String Shot', 0), ('Harden', 7, 1), ('Confusion', 12, 2), ('Poison Powder', 15, 2),
        ('Stun Spore', 16, 2), ('Sleep Powder', 17, 2), ('Supersonic', 21, 2), ('Mega Drain', 25, 2),
        ('Whirlwind', 26, 2), ('Psybeam', 32, 2),
    ),
    ('weedle', 'kakuna', 'beedrill'): (
        ('Poison Sting', 0), ('String Shot', 0), ('Harden', 7, 1), ('Fury Attack', 12, 2),
        ('Focus Energy', 16, 2), ('Twineedle', 20, 2), ('Swords Dance', 25, 2), ('Pin Missile', 30, 2),
        ('Agility', 35, 2),
    ),
    ('oddish', 'gloom', 'vileplume'): (
        ('Absorb', 0), ('Poison Powder', 15), ('Stun Spore', 17), ('Sleep Powder', 19), ('Acid', 24),
        ('Mega Drain', 25, 1), ('Petal Dance', 33), ('Solar Beam', 46, 2),
    ),
    ('goldeen', 'seaking'): (
        ('Peck', 0), ('Tail Whip', 0), ('Water Gun', 10), ('Supersonic', 19), ('Horn Attack', 24),
        ('Bubble Beam', 24), ('Fury Attack', 30), ('Ice Beam', 40, 1), ('Double-Edge', 42, 1),
        ('Agility', 54),
    ),
    ('staryu', 'starmie'): (
        ('Tackle', 0), ('Water Gun', 17), ('Harden', 22), ('Bubble Beam', 24), ('Thunder Wave', 26),
        ('Recover', 27), ('Swift', 32), ('Psychic', 36, 1), ('Thunderbolt', 38, 1), ('Ice Beam', 40, 1),
        ('Hydro Pump', 47, 1),
    ),
    ('abra', 'kadabra', 'alakazam'): (
        ('Confusion', 0), ('Kinesis', 0), ('Thunder Wave', 12), ('Body Slam', 25, 1), ('Psybeam', 27, 1),
        ('Recover', 31, 1), ('Psychic', 38, 1), ('Reflect', 42), ('Hyper Beam', 50, 2),
    ),
    ('venonat', 'venomoth'): (
        ('Tackle', 0), ('Supersonic', 24), ('Confusion', 27), ('Poison Powder', 30), ('Leech Life', 35),
        ('Double-Edge', 36, 1), ('Stun Spore', 38), ('Psybeam', 43), ('Sleep Powder', 46),
        ('Psychic', 51, 1),
    ),
    ('bellsprout', 'weepinbell', 'victreebel'): (
        ('Vine Whip', 0), ('Growth', 0), ('Wrap', 13), ('Poison Powder', 15), ('Sleep Powder', 18),
        ('Stun Spore', 21), ('Acid', 26), ('Swords Dance', 30, 1), ('Razor Leaf', 33), ('Slam', 42, 1),
    ),
    ('pikachu',): (
        ('Thunder Shock', 0), ('Growl', 0), ('Thunder Wave', 9), ('Quick Attack', 16), ('Swift', 26),
        ('Thunderbolt', 30), ('Agility', 33), ('Thunder', 43),
    ),
    ('seel', 'dewgong'): (
        ('Headbutt', 0), ('Water Gun', 10), ('Bubble Beam', 25), ('Growl', 30), ('Aurora Beam', 35),
        ('Rest', 40), ('Surf', 40, 1), ('Take Down', 45, 1), ('Ice Beam', 50, 1), ('Blizzard', 55, 1),
    ),
    ('shellder',): (
        ('Tackle', 0), ('Withdraw', 0), ('Water Gun', 10), ('Supersonic', 18), ('Clamp', 23),
        ('Bubble Beam', 25), ('Aurora Beam', 30), ('Leer', 39), ('Ice Beam', 50),
    ),
    ('psyduck', 'golduck'): (
        ('Scratch', 0), ('Water Gun', 8), ('Bubble Beam', 20), ('Tail Whip', 28), ('Confusion', 36),
        ('Fury Swipes', 43), ('Ice Beam', 45, 1), ('Hydro Pump', 52, 1),
    ),
    ('horsea', 'seadra'): (
        ('Bubble', 0), ('Smokescreen', 19), ('Bubble Beam', 20), ('Leer', 24), ('Water Gun', 30),
        ('Agility', 37), ('Ice Beam', 40, 1), ('Hydro Pump', 45, 1),
    ),
    ('jynx',): (
        ('Pound', 0), ('Lovely Kiss', 0), ('Lick', 18), ('Double Slap', 23), ('Ice Punch', 31),
        ('Psychic', 35), ('Body Slam', 39), ('Thrash', 47), ('Blizzard', 58),
    ),
    ('lapras',): (
        ('Water Gun', 0), ('Growl', 0), ('Sing', 16), ('Body Slam', 25), ('Confuse Ray', 31),
        ('Ice Beam', 38), ('Hydro Pump', 46), ('Blizzard', 50),
    ),
    ('geodude', 'graveler', 'golem'): (
        ('Tackle', 0), ('Defense Curl', 11), ('Rock Throw', 16), ('Rock Slide', 25, 1), ('Harden', 26),
        ('Body Slam', 30, 1), ('Earthquake', 35, 2), ('Dig', 35, 2),
    ),
    ('onix',): (
        ('Tackle', 0), ('Screech', 0), ('Bind', 15), ('Rock Throw', 19), ('Rock Slide', 28), ('Slam', 33),
        ('Earthquake', 38), ('Harden', 43),
    ),
    ('diglett', 'dugtrio'): (
        ('Scratch', 0), ('Growl', 15), ('Sand-Attack', 24), ('Slash', 31), ('Dig', 35, 1),
        ('Rock Slide', 35, 1), ('Earthquake', 40, 1),
    ),
    ('sandshrew', 'sandslash'): (
        ('Scratch', 0), ('Sand-Attack', 10), ('Slash', 17), ('Poison Sting', 24), ('Swift', 31),
        ('Dig', 35, 1), ('Fury Swipes', 38), ('Rock Slide', 40, 1), ('Earthquake', 45, 1),
    ),
    ('ekans', 'arbok'): (
        ('Wrap', 0), ('Leer', 0), ('Poison Sting', 10), ('Bite', 17), ('Glare', 24), ('Screech', 31),
        ('Dig', 35, 1), ('Acid', 38),
    ),
    ('jigglypuff',): (
        ('Pound', 0), ('Sing', 0), ('Defense Curl', 19), ('Double Slap', 24), ('Rest', 29),
        ('Body Slam', 34), ('Double-Edge', 39),
    ),
    ('zubat', 'golbat'): (
        ('Leech Life', 0), ('Supersonic', 10), ('Bite', 15), ('Confuse Ray', 21), ('Wing Attack', 28),
        ('Swift', 32), ('Double-Edge', 38, 1),
    ),
    ('paras', 'parasect'): (
        ('Scratch', 0), ('Stun Spore', 13), ('Leech Life', 20), ('Mega Drain', 24), ('Spore', 27),
        ('Slash', 34), ('Growth', 41), ('Solar Beam', 44, 1),
    ),
    ('clefairy', 'clefable'): (
        ('Pound', 0), ('Growl', 0), ('Sing', 13), ('Double Slap', 18), ('Body Slam', 30, 1),
        ('Thunder Wave', 34), ('Defense Curl', 39), ('Psychic', 40, 1), ('Rest', 44),
    ),
}


@dataclass(frozen=True)
class LearnedMove:
    name: str
    level: int = 0
    stage: int = 0

    @property
    def key(self) -> str:
        return key_of(self.name)


# --- changing a move ---------------------------------------------------------

ADDED = {"status_chance", "stage_chance", "confuse", "flinch", "seed", "bind", "shield", "drain", "heal",
         "priority", "sleep_bonus", "bleed", "scale", "crit_ratio", "recoil", "reach", "empower", "spikes",
         "contagious", "siphon", "nightmare"}
CHANCES = {"status_chance", "stage_chance", "confuse", "flinch", "contagious"}


def _add_stages(old: tuple, extra: tuple) -> tuple:
    total = dict(old)
    for stat, change in extra:
        total[stat] = total.get(stat, 0) + change
    return tuple((stat, change) for stat, change in total.items() if change)


def apply_changes(move: Move, changes: dict) -> Move:
    """`move` with a talent's changes: numbers add up (chances to at most
    100%), stage changes add per stat, triggers join; other fields are set.
    A status only lands on a move without one (or adds to the same one's
    chance)."""
    new = {}
    clash = move.status and changes.get("status", move.status) != move.status  # (a move has one status)
    for name, value in changes.items():
        old = getattr(move, name)
        if clash and name in ("status", "status_chance"):
            continue
        if name == "status_chance" and not move.status:
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


def _selects(selector: str, move: Move, is_basic: bool) -> bool:
    """Whether a talent's change is for `move`: "basic" (the basic attack), a
    move's name, "type:<type>" (the user's damaging moves of that type) or
    "status:<status>" (its moves that inflict it)."""
    if selector == "basic":
        return is_basic
    kind, _, what = selector.partition(":")
    if kind == "type":
        return move.damaging and move.type == what
    if kind == "status":
        return move.status == what
    return move.name == selector


# --- talents -----------------------------------------------------------------

@dataclass(frozen=True)
class Talent:
    key: str
    name: str
    text: str
    pool: str  # where it comes from: a type or status ("grass", "sleep"), a move ("move:Growl"), "any" or "own"
    moves: tuple[tuple[str, dict], ...] = field(default=(), hash=False)  # (selector, Move field changes)
    flags: tuple[tuple[str, float], ...] = ()  # battle effects of its own: (flag, value)

    @property
    def pool_text(self) -> str:
        """Where it comes from, in words."""
        if self.pool == "own":
            return "Signature talent"
        if self.pool == "any":
            return "Shared by every line"
        kind, _, what = self.pool.partition(":")
        if kind == "move":
            return f"Shared by lines with {what}"
        return f"Shared by {self.pool.capitalize()} lines"


def _t(name: str, pool: str, text: str, *moves: tuple[str, dict], **flags: float) -> Talent:
    return Talent(key_of(name), name, text, pool, tuple(moves), tuple(flags.items()))


TALENTS = {t.key: t for t in [
    # Any line.
    _t("Sturdy", "any", "The first hit the user takes in each battle deals half damage.", sturdy=0.5),
    _t("Second Wind", "any", "Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP.",
       second_wind=0.25),
    _t("World Tree", "any", "Once a battle, a partner that would faint keeps 1 HP instead.", world_tree=1),
    # Grass lines.
    _t("Sprout Strike", "grass", "The basic attack becomes a Grass move (with STAB).", ("basic", {"type": "grass"})),
    _t("Overgrow", "grass", "Below 1/3 HP, the user's Grass moves deal 1.5× damage.", overgrow=0.5),
    _t("Ripening", "grass", "Each Grass move in a row deals 20% more than the last, up to +60%. "
       "Any other move starts it over.", ripening=0.2),
    _t("Flower Power", "grass", "The user's Grass moves also hit one enemy next to the target, at half damage.",
       ("type:grass", {"reach": 0.5})),
    _t("Harvest", "grass", "Knocking an enemy out with a Grass move heals the user 1/4 of its max HP.",
       harvest=0.25),
    _t("Photosynthesis", "grass", "The user heals 1/16 of its max HP at the end of each round.", regen=1 / 16),
    # Poison lines.
    _t("Toxic Touch", "poison", "The basic attack has a 20% chance to poison.",
       ("basic", {"status": "poison", "status_chance": 20})),
    _t("Sapping", "poison", "Poisoned enemies deal 20% less damage.", sapping=0.2),
    _t("Contagion", "poison", "Poison the user inflicts has a 30% chance each round to spread to "
       "an enemy next to it.", ("status:poison", {"contagious": 30})),
    _t("Siphon", "poison", "The user heals half the poison damage of the enemies it poisoned.",
       ("status:poison", {"siphon": 0.5})),
    _t("Miasma", "poison", "At the start of each battle, each enemy has a 50% chance to be poisoned.", miasma=50),
    # Lines with sleep moves.
    _t("Nightmare", "sleep", "Enemies the user puts to sleep lose 1/8 of their max HP each round.",
       ("status:sleep", {"nightmare": 1 / 8})),
    # Move pools.
    _t("Taunting Growl", "move:Growl", "Growl also makes every enemy attack the user, this round and the next.",
       ("Growl", {"taunt": 2})),
    _t("Creeping Seed", "move:Leech Seed", "When a seeded enemy faints, its seed jumps to an enemy next to it.",
       ("Leech Seed", {"seed_spread": True})),
    _t("Seed Bomb", "move:Leech Seed", "Leech Seed also deals damage (Grass, 30 power) when it lands.",
       ("Leech Seed", {"power": 30})),
    _t("Double Lash", "move:Vine Whip", "Vine Whip hits twice, at 60% power each.",
       ("Vine Whip", {"hits": (2, 2), "scale": -0.4})),
    _t("Thirsty Vines", "move:Vine Whip", "Vine Whip heals the user half the damage it deals.",
       ("Vine Whip", {"drain": 0.5})),
    _t("Toxic Spores", "move:Poison Powder", "Poison Powder badly poisons: it gets worse every round.",
       ("Poison Powder", {"toxic": True})),
    _t("Pollen Cloud", "move:Poison Powder", "Poison Powder hits every enemy.", ("Poison Powder", {"spread": True})),
    _t("Canopy", "move:Leaf Shield", "Leaf Shield covers the whole party.", ("Leaf Shield", {"spread": True})),
    _t("Thornskin", "move:Leaf Shield", "For 3 rounds, whoever hits a Pokémon behind Leaf Shield loses "
       "1/16 of its max HP.", ("Leaf Shield", {"spikes": 1 / 16})),
    _t("Keen Edge", "move:Razor Leaf", "Razor Leaf is always a critical hit on a target below half HP.",
       ("Razor Leaf", {"keen": 0.5})),
    _t("Heavy Body", "move:Body Slam", "Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% "
       "of the time.", ("Take Down", {"recoil": -1.0}), ("Double-Edge", {"recoil": -1.0}),
       ("Body Slam", {"status_chance": 20})),
    _t("Full Bloom", "move:Growth", "Growth also makes the user's next damaging move deal 50% more.",
       ("Growth", {"empower": 0.5})),
    _t("Shared Sun", "move:Growth", "Growth works on the whole party.", ("Growth", {"rally": True})),
    _t("Soothing Spores", "move:Sleep Powder", "Sleep Powder also cures the party's status conditions.",
       ("Sleep Powder", {"soothe": True})),
    _t("Solar Flare", "move:Solar Beam", "Solar Beam hits every enemy, at full power.",
       ("Solar Beam", {"spread": True})),
    # Bulbasaur's own.
    _t("Thorned Whip", "own", "Vine Whip has a 30% chance to poison.",
       ("Vine Whip", {"status": "poison", "status_chance": 30})),
    _t("Spore Storm", "own", "Razor Leaf has a 15% chance to set off Poison Powder and a 10% chance to set "
       "off Sleep Powder on its target.",
       ("Razor Leaf", {"triggers": (("poison_powder", "Poison Powder", 15), ("sleep_powder", "Sleep Powder", 10))})),
    _t("Sunlit", "own", "Once the user has used Growth in a battle, Solar Beam needs no charging.",
       ("Solar Beam", {"charge_skip": "Growth"})),
    _t("Venom Garden", "own", "All poison the user inflicts is bad poison, and Leech Seed poisons too.",
       ("Leech Seed", {"status": "poison", "status_chance": 100}), ("status:poison", {"toxic": True})),
    _t("Hyper Bloom", "own", "Hyper Beam is a Grass move and needs no rest after knocking an enemy out.",
       ("Hyper Beam", {"type": "grass", "ko_no_recharge": True})),
    _t("Ancient Roots", "own", "While the user stands, the whole party takes 15% less damage.", ancient_roots=0.15),
]}


@dataclass(frozen=True)
class Path:
    name: str
    blurb: str
    color: tuple[int, int, int]


@dataclass(frozen=True)
class TalentTree:
    """A line's moves by level and its talents: `tiers[i]` opens at
    `TIER_LEVELS[i]`, one talent per path. A line without talents yet has
    no tiers."""
    species: tuple[str, ...]
    moves: tuple[LearnedMove, ...]
    paths: tuple[Path, ...] = ()
    tiers: tuple[tuple[Talent, ...], ...] = ()

    @property
    def basic(self) -> LearnedMove:
        return self.moves[0]

    def learned(self, key: str) -> LearnedMove | None:
        return next((m for m in self.moves if m.key == key), None)

    def known(self, level: int, stage: int) -> list[str]:
        """The keys of the moves known at `level` and evolution `stage`."""
        return [m.key for m in self.moves if m.level <= level and m.stage <= stage]

    def tier_of(self, talent_key: str) -> tuple[int, int] | None:
        """(tier, path) of one of its talents."""
        for i, row in enumerate(self.tiers):
            for p, t in enumerate(row):
                if t.key == talent_key:
                    return i, p
        return None

    def picks(self, chosen: list[str]) -> dict[int, int]:
        """Tier -> path of the chosen talents."""
        return dict(spot for spot in map(self.tier_of, chosen) if spot)

    def why_not(self, chosen: list[str], tier: int, path: int, level: int) -> str:
        """Why the talent at (`tier`, `path`) can't be picked now ("" if it can;
        picking it replaces the tier's other pick)."""
        need = TIER_LEVELS[tier]
        if level < need:
            return f"Opens at Lv{need}"
        deep = DEEP.get(tier, 0)
        picks = self.picks(chosen)
        have = sum(1 for t, p in picks.items() if p == path and t < tier)
        if have < deep:
            return f"Needs {deep} earlier {self.paths[path].name} talents (has {have})"
        return ""

    def effective_move(self, chosen: list[str], key: str) -> Move:
        """Move `key` changed by the chosen talents (in tier order)."""
        move = MOVES[self.learned(key).name]
        basic = key == self.basic.key
        for talent in self.chosen_talents(chosen):
            for selector, changes in talent.moves:
                if _selects(selector, move, basic):
                    move = apply_changes(move, changes)
        return move

    def chosen_talents(self, chosen: list[str]) -> list[Talent]:
        picks = self.picks(chosen)
        return [self.tiers[t][p] for t, p in sorted(picks.items())]

    def open_tiers(self, level: int) -> int:
        """How many of its tiers are open at `level`."""
        return sum(1 for lv in TIER_LEVELS[:len(self.tiers)] if lv <= level)


TOXIN, BLOOM, BULWARK = (170, 100, 210), (100, 190, 90), (210, 170, 90)


def _tiers(*rows: tuple[str, str, str]) -> tuple[tuple[Talent, ...], ...]:
    assert len(rows) == len(TIER_LEVELS)
    return tuple(tuple(TALENTS[key_of(n)] for n in row) for row in rows)


TALENT_TREES = {
    "bulbasaur": (
        (Path("Toxin", "Poison, seeds and sleep: wearing enemies down.", TOXIN),
         Path("Bloom", "Grass damage.", BLOOM),
         Path("Bulwark", "Staying up, and keeping the partner up.", BULWARK)),
        _tiers(("Toxic Touch", "Sprout Strike", "Sturdy"),
               ("Creeping Seed", "Seed Bomb", "Taunting Growl"),
               ("Thorned Whip", "Double Lash", "Thirsty Vines"),
               ("Sapping", "Overgrow", "Second Wind"),
               ("Toxic Spores", "Ripening", "Canopy"),
               ("Pollen Cloud", "Keen Edge", "Thornskin"),
               ("Contagion", "Flower Power", "Heavy Body"),
               ("Siphon", "Full Bloom", "Shared Sun"),
               ("Nightmare", "Harvest", "Soothing Spores"),
               ("Spore Storm", "Sunlit", "Photosynthesis"),
               ("Miasma", "Solar Flare", "World Tree"),
               ("Venom Garden", "Hyper Bloom", "Ancient Roots")),
    ),
}


def _line(species: tuple[str, ...], moves: tuple) -> TalentTree:
    paths, tiers = TALENT_TREES.get(species[0], ((), ()))
    return TalentTree(species, tuple(LearnedMove(*m) for m in moves), paths, tiers)


TREES = {species[0]: _line(species, moves) for species, moves in LEARNSETS.items()}


@cache
def stand_in_tree(species: str) -> TalentTree:
    """For lines without moves yet: Tackle."""
    return TalentTree((species,), (LearnedMove("Tackle"),))
