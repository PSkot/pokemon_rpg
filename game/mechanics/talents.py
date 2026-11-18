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
TALENT_MODS = {"first", "crit", "endure", "regen"}  # talent flags that work as the gear mods (and status:<status>)


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
    move's name, "type:<type>" (the user's damaging moves of that type),
    "status:<status>" (its moves that inflict it), "confuse" (moves that
    confuse), "damaging", "status_moves" (the others) or "spread" (moves
    that hit every target, as changed so far)."""
    if selector == "basic":
        return is_basic
    if selector in ("damaging", "status_moves"):
        return move.damaging == (selector == "damaging")
    if selector == "confuse":
        return bool(move.confuse)
    if selector == "spread":
        return move.spread
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
        verbs = {"sleep": "put to sleep", "paralysis": "paralyze", "confusion": "confuse", "freeze": "freeze"}
        if self.pool in verbs:
            return f"Shared by lines that {verbs[self.pool]}"
        return f"Shared by {self.pool.capitalize()} lines"


def _t(name: str, pool: str, text: str, *moves: tuple[str, dict], **flags: float) -> Talent:
    """A talent. Flags with a type or status in them are written with "__"
    (`pinch__grass` = "pinch:grass")."""
    return Talent(key_of(name), name, text, pool, tuple(moves),
                  tuple((f.replace("__", ":"), v) for f, v in flags.items()))


def _pinch(name: str, kind: str) -> Talent:
    return _t(name, kind, f"Below 1/3 HP, the user's {kind.capitalize()} moves deal 1.5× damage.",
              **{f"pinch__{kind}": 0.5})


def _harvest(name: str, kind: str, what: str) -> Talent:
    return _t(name, kind, f"Knocking an enemy out with a {kind.capitalize()} move {what} 1/4 of its max HP.",
              **{f"harvest__{kind}": 0.25})


# Battle effects (`Talent.flags`, read by `BattleScene`):
#   pinch:<type>     the user's moves of that type × (1 + value) below 1/3 HP
#   streak:<type>    + value per move of that type used in a row before this one (up to 3)
#   harvest:<type>   knocking an enemy out with a move of that type heals value × max HP
#   ambush           + value on a target that hasn't moved yet this round
#   gang             + value on a target a partner already hit this round
#   wide             + value for moves that hit every enemy
#   spot:<stat>      the holder's side deals + value to enemies with that stat lowered
#   prey:<status>    + value on a target with that status ("confused" too)
#   aura:<status>    % chance per foe at the battle's start to give it the status
#   pyre             burned foes of the holder's side lose this share of max HP more a round
#   intimidate       the foes' Attack falls this many stages at the battle's start
#   thorns           whoever hits the user loses this share of its max HP
#   party_regen      the holder's side heals this % of max HP at each round's end
#   guard_heal       with world_tree: the partner held up also heals this share
#   dream            the user heals this share of max HP a round per sleeping foe
#   retaliate:<status>  % chance that whoever hits the user gets the status
#   shed             % chance at each round's end to shake off its status
#   sapping, ancient_roots, sturdy, second_wind, world_tree: see their talents
# Talents with the same effect don't add up: the strongest counts (`Monster.talent`).
#   first, crit, endure, regen, status:<status>: added to the gear mods of that name
#                    (see items.MOD_TEXT)
TALENTS = {t.key: t for t in [
    # --- Any line.
    _t("Sturdy", "any", "The first hit the user takes in each battle deals half damage.", sturdy=0.5),
    _t("Second Wind", "any", "Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP.",
       second_wind=0.25),
    _t("Guardian", "any", "Once a battle, a partner that would faint keeps 1 HP instead.", world_tree=1),
    _t("Head Start", "any", "The user has a 30% chance each round to act before the others.", first=30),
    _t("Lucky Strikes", "any", "+10% chance of critical hits.", crit=10),
    _t("Tenacity", "any", "A hit that would knock the user out has a 25% chance to leave it 1 HP.", endure=25),
    _t("Ambush", "any", "The user's moves deal 30% more to a target that hasn't moved yet this round.",
       ambush=0.3),
    _t("Gang Up", "any", "The user's moves deal 30% more to a target a partner already hit this round.",
       gang=0.3),
    _t("Apex Predator", "any", "The user's moves are always critical hits on a target below 1/3 HP.",
       ("damaging", {"keen": 1 / 3})),
    _t("Blur", "any", "The user's damaging moves go before others' (as Quick Attack does).",
       ("damaging", {"priority": 1})),
    _t("Unbreakable", "any", "A hit that would knock the user out has a 50% chance to leave it 1 HP.", endure=50),
    # --- Type pools.
    _t("Sprout Strike", "grass", "The basic attack becomes a Grass move (with STAB).", ("basic", {"type": "grass"})),
    _pinch("Overgrow", "grass"),
    _t("Ripening", "grass", "Each Grass move in a row deals 20% more than the last, up to +60%. "
       "Any other move starts it over.", streak__grass=0.2),
    _t("Flower Power", "grass", "The user's Grass moves also hit one enemy next to the target, at half damage.",
       ("type:grass", {"reach": 0.5})),
    _harvest("Harvest", "grass", "heals the user"),
    _t("Photosynthesis", "grass", "The user heals 1/16 of its max HP at the end of each round.", regen=6.25),
    _t("Toxic Touch", "poison", "The basic attack has a 20% chance to poison.",
       ("basic", {"status": "poison", "status_chance": 20})),
    _t("Sapping", "poison", "Poisoned enemies deal 20% less damage.", sapping=0.2),
    _t("Contagion", "poison", "Poison the user inflicts has a 30% chance each round to spread to "
       "an enemy next to it.", ("status:poison", {"contagious": 30})),
    _t("Siphon", "poison", "The user heals half the poison damage of the enemies it poisoned.",
       ("status:poison", {"siphon": 0.5})),
    _t("Miasma", "poison", "At the start of each battle, each enemy has a 50% chance to be poisoned.", aura__poison=50),
    _t("Poison Point", "poison", "Whoever hits the user has a 25% chance to be poisoned.", retaliate__poison=25),
    _t("Virulent", "poison", "The user's poison is bad poison: it gets worse every round.",
       ("status:poison", {"toxic": True})),
    _pinch("Cornered", "normal"),
    _harvest("Scavenger", "normal", "heals the user"),
    _t("Momentum", "normal", "Each Normal move in a row deals 15% more than the last, up to +45%. "
       "Any other move starts it over.", streak__normal=0.15),
    _t("Riding the Wind", "flying", "The user's Flying moves raise its Speed 1 stage.",
       ("type:flying", {"self_stages": (("speed", 1),)})),
    _harvest("Bird of Prey", "flying", "heals the user"),
    _t("Aerial Ace", "flying", "The user's Flying moves never miss and are twice as likely to be critical hits.",
       ("type:flying", {"sure_hit": True, "crit_ratio": 1.0})),
    _pinch("Swarm", "bug"),
    _t("Shed Skin", "bug", "At the end of each round, the user has a 30% chance to shake off its status.", shed=30),
    _t("Hive Mind", "bug", "Each Bug move in a row deals 20% more than the last, up to +60%. "
       "Any other move starts it over.", streak__bug=0.2),
    _harvest("Feeding Frenzy", "bug", "heals the user"),
    _t("Charge Up", "electric", "Each Electric move in a row deals 20% more than the last, up to +60%. "
       "Any other move starts it over.", streak__electric=0.2),
    _harvest("Discharge", "electric", "heals the user"),
    _t("Static", "electric", "Whoever hits the user has a 25% chance to be paralyzed.", retaliate__paralysis=25),
    _pinch("Surge", "electric"),
    _t("Live Wire", "electric", "The user's Electric moves are 20% more likely to paralyze.",
       ("type:electric", {"status_chance": 20})),
    _t("Conductor", "paralysis", "Enemies the user paralyzes take 30% more damage from everyone.",
       ("status:paralysis", {"shock": 0.3})),
    _t("Nightmare", "sleep", "Enemies the user puts to sleep lose 1/8 of their max HP each round.",
       ("status:sleep", {"nightmare": 1 / 8})),
    _t("Mind Games", "confusion", "Enemies the user confuses hurt themselves 75% of the time (not 50%).",
       ("confuse", {"madness": 75})),
    # Fire lines: burns that bite, and fire that spreads.
    _pinch("Blaze", "fire"),
    _t("Stoke the Flames", "fire", "Each Fire move in a row deals 20% more than the last, up to +60%. "
       "Any other move starts it over.", streak__fire=0.2),
    _t("Searing", "fire", "The user's Fire moves are 20% more likely to burn.", ("type:fire", {"status_chance": 20})),
    _t("Scorch", "fire", "Burned enemies take 25% more damage from the user.", prey__burn=0.25),
    _t("Smoulder", "fire", "The user's Fire moves wound the target: 1/16 of its max HP each round, for 3 rounds.",
       ("type:fire", {"bleed": 1 / 16})),
    _t("Ash Cloud", "fire", "The user's Fire moves have a 20% chance to lower the target's accuracy 1 stage.",
       ("type:fire", {"stages": (("accuracy", -1),), "stage_chance": 20})),
    _t("Wildfire", "fire", "Burns the user inflicts have a 30% chance each round to spread to an enemy next to it.",
       ("status:burn", {"contagious": 30})),
    _harvest("Feed the Flames", "fire", "heals the user"),
    _t("Heat Haze", "fire", "At the start of each battle, each enemy has a 30% chance to be burned.", aura__burn=30),
    # Water lines: pressure, tides and staying cool.
    _pinch("Torrent", "water"),
    _t("Rising Tide", "water", "Each Water move in a row deals 20% more than the last, up to +60%. "
       "Any other move starts it over.", streak__water=0.2),
    _t("Undertow", "water", "The user's Water moves have a 20% chance to lower the target's Speed 1 stage.",
       ("type:water", {"stages": (("speed", -1),), "stage_chance": 20})),
    _t("Splash Zone", "water", "The user's Water moves also hit one enemy next to the target, at half damage.",
       ("type:water", {"reach": 0.5})),
    _harvest("Rain Dish", "water", "heals the user"),
    _t("Hydration", "water", "At the end of each round, the user has a 30% chance to wash off its status.", shed=30),
    # Lines with Ice moves.
    _t("Frostbite", "ice", "The user's Ice moves are 10% more likely to freeze.", ("type:ice", {"status_chance": 10})),
    _t("Shatter", "freeze", "Frozen enemies take 50% more damage from the user.", prey__freeze=0.5),
    _t("Chill", "ice", "The user's Ice moves have a 30% chance to lower the target's Speed 1 stage.",
       ("type:ice", {"stages": (("speed", -1),), "stage_chance": 30})),
    # --- Move pools.
    _t("Echoing Growl", "move:Growl", "Growl works on every enemy.", ("Growl", {"spread": True})),
    _t("Taunting Growl", "move:Growl", "Growl also makes every enemy attack the user, this round and the next.",
       ("Growl", {"taunt": 2})),
    _t("Wagging Tail", "move:Tail Whip", "Tail Whip works on every enemy.", ("Tail Whip", {"spread": True})),
    _t("Tail Slap", "move:Tail Whip", "After Tail Whip, the user hits the target with its basic attack at 60% "
       "power.", ("Tail Whip", {"follow_up": 0.6})),
    _t("Menacing Leer", "move:Leer", "Leer works on every enemy.", ("Leer", {"spread": True})),
    _t("Piercing Gaze", "move:Leer", "Leer also makes the target take 25% more damage from everyone, "
       "for 3 rounds.", ("Leer", {"expose": 0.25})),
    _t("Sandstorm", "move:Sand-Attack", "Sand-Attack works on every enemy.", ("Sand-Attack", {"spread": True})),
    _t("Blinding Grit", "move:Sand-Attack", "Sand-Attack lowers accuracy 2 stages.",
       ("Sand-Attack", {"stages": (("accuracy", -1),)})),
    _t("Kick Up Dust", "move:Sand-Attack", "After Sand-Attack, the user hits the target with its basic attack at "
       "60% power.", ("Sand-Attack", {"follow_up": 0.6})),
    _t("Lightning Reflexes", "move:Quick Attack", "Quick Attack has a 30% chance to make the target flinch.",
       ("Quick Attack", {"flinch": 30})),
    _t("Hit and Run", "move:Quick Attack", "Quick Attack also raises the user's Speed 1 stage.",
       ("Quick Attack", {"self_stages": (("speed", 1),)})),
    _t("Keen Focus", "move:Focus Energy", "Focus Energy also raises the user's Attack 1 stage.",
       ("Focus Energy", {"self_stages": (("attack", 1),)})),
    _t("Shared Focus", "move:Focus Energy", "Focus Energy works on the whole party.",
       ("Focus Energy", {"rally": True})),
    _t("Tailwind", "move:Agility", "Agility works on the whole party.", ("Agility", {"rally": True})),
    _t("Afterimage", "move:Agility", "Agility also makes the user's next damaging move deal 50% more.",
       ("Agility", {"empower": 0.5})),
    _t("Howling Wind", "move:Whirlwind", "Whirlwind also deals damage (Normal, 30 power) to every enemy.",
       ("Whirlwind", {"power": 30})),
    _t("Tempest", "move:Whirlwind", "Whirlwind lowers Speed 2 stages.", ("Whirlwind", {"stages": (("speed", -1),)})),
    _t("Star Shower", "move:Swift", "Swift hits every enemy, the others at 60% damage.",
       ("Swift", {"spread": True, "spread_share": 0.6})),
    _t("Frenzy", "move:Fury Attack", "Fury Attack always hits at least 3 times.", ("Fury Attack", {"hits": (3, 5)})),
    _t("Raking Claws", "move:Fury Swipes", "Fury Swipes wounds the target: 1/16 of its max HP each round, "
       "for 3 rounds.", ("Fury Swipes", {"bleed": 1 / 16})),
    _t("Needle Storm", "move:Pin Missile", "Pin Missile always hits at least 3 times.",
       ("Pin Missile", {"hits": (3, 5)})),
    _t("Rapid Kicks", "move:Double Kick", "Each of Double Kick's hits has a 30% chance to make the target flinch.",
       ("Double Kick", {"flinch": 30})),
    _t("Barbed Sting", "move:Poison Sting", "Poison Sting is 30% more likely to poison.",
       ("Poison Sting", {"status_chance": 30})),
    _t("Venom Needle", "move:Poison Sting", "Poison Sting wounds the target: 1/16 of its max HP each round, "
       "for 3 rounds.", ("Poison Sting", {"bleed": 1 / 16})),
    _t("Iron Shell", "move:Harden", "Harden also halves the damage the user takes for 2 rounds.",
       ("Harden", {"shield": 2})),
    _t("Shell Wall", "move:Harden", "Harden works on the whole party.", ("Harden", {"rally": True})),
    _t("Web", "move:String Shot", "String Shot works on every enemy.", ("String Shot", {"spread": True})),
    _t("Sticky Silk", "move:String Shot", "String Shot also makes the target take 20% more damage from "
       "everyone, for 3 rounds.", ("String Shot", {"expose": 0.2})),
    _t("Heavy Body", "move:Body Slam", "Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% "
       "of the time.", ("Take Down", {"recoil": -1.0}), ("Double-Edge", {"recoil": -1.0}),
       ("Body Slam", {"status_chance": 20})),
    _t("Overdrive", "move:Hyper Beam", "Hyper Beam needs no rest after knocking an enemy out.",
       ("Hyper Beam", {"ko_no_recharge": True})),
    _t("Chain Lightning", "move:Thunder Wave", "Thunder Wave works on every enemy.",
       ("Thunder Wave", {"spread": True})),
    _t("Numbing Cloud", "move:Stun Spore", "Stun Spore works on every enemy.", ("Stun Spore", {"spread": True})),
    _t("Echo", "move:Supersonic", "Supersonic works on every enemy.", ("Supersonic", {"spread": True})),
    _t("Envenom", "move:Twineedle", "Twineedle is 30% more likely to poison.", ("Twineedle", {"status_chance": 30})),
    _t("Blade Dance", "move:Swords Dance", "Swords Dance also makes the user's next damaging move deal 50% more.",
       ("Swords Dance", {"empower": 0.5})),
    _t("Crunch", "move:Bite", "Bite has a 30% chance to lower the target's Defense 1 stage.",
       ("Bite", {"stages": (("defense", -1),), "stage_chance": 30})),
    _t("Gnaw", "move:Super Fang", "Super Fang also wounds: 1/12 of the target's max HP each round, for 3 rounds.",
       ("Super Fang", {"bleed": 1 / 12})),
    _t("Bone Crusher", "move:Hyper Fang", "Hyper Fang is 20% more likely to make the target flinch.",
       ("Hyper Fang", {"flinch": 20})),
    _t("Drill Run", "move:Drill Peck", "Drill Peck also hits one enemy next to the target, at half damage.",
       ("Drill Peck", {"reach": 0.5})),
    _t("Gale Wings", "move:Wing Attack", "Wing Attack always goes first.", ("Wing Attack", {"priority": 1})),
    _t("Ascend", "move:Sky Attack", "Once the user has used Agility in a battle, Sky Attack needs no charging.",
       ("Sky Attack", {"charge_skip": "Agility"})),
    _t("Gluttony", "move:Mega Drain", "Mega Drain heals the user all the damage it deals (not half).",
       ("Mega Drain", {"drain": 0.5})),
    _t("Gore", "move:Horn Attack", "Horn Attack is 8× as likely to be a critical hit.",
       ("Horn Attack", {"crit_ratio": 7.0})),
    _t("Toxic Spores", "move:Poison Powder", "Poison Powder badly poisons: it gets worse every round.",
       ("Poison Powder", {"toxic": True})),
    _t("Pollen Cloud", "move:Poison Powder", "Poison Powder hits every enemy.", ("Poison Powder", {"spread": True})),
    _t("Creeping Seed", "move:Leech Seed", "When a seeded enemy faints, its seed jumps to an enemy next to it.",
       ("Leech Seed", {"seed_spread": True})),
    _t("Seed Bomb", "move:Leech Seed", "Leech Seed also deals damage (Grass, 30 power) when it lands.",
       ("Leech Seed", {"power": 30})),
    _t("Double Lash", "move:Vine Whip", "Vine Whip hits twice, at 60% power each.",
       ("Vine Whip", {"hits": (2, 2), "scale": -0.4})),
    _t("Thirsty Vines", "move:Vine Whip", "Vine Whip heals the user half the damage it deals.",
       ("Vine Whip", {"drain": 0.5})),
    _t("Canopy", "move:Leaf Shield", "Leaf Shield covers the whole party.", ("Leaf Shield", {"spread": True})),
    _t("Thornskin", "move:Leaf Shield", "For 3 rounds, whoever hits a Pokémon behind Leaf Shield loses "
       "1/16 of its max HP.", ("Leaf Shield", {"spikes": 1 / 16})),
    _t("Keen Edge", "move:Razor Leaf", "Razor Leaf is always a critical hit on a target below half HP.",
       ("Razor Leaf", {"keen": 0.5})),
    _t("Full Bloom", "move:Growth", "Growth also makes the user's next damaging move deal 50% more.",
       ("Growth", {"empower": 0.5})),
    _t("Shared Sun", "move:Growth", "Growth works on the whole party.", ("Growth", {"rally": True})),
    _t("Soothing Spores", "move:Sleep Powder", "Sleep Powder also cures the party's status conditions.",
       ("Sleep Powder", {"soothe": True})),
    _t("Drowsy Dust", "move:Sleep Powder", "Sleep Powder works on every enemy.", ("Sleep Powder", {"spread": True})),
    _t("Solar Flare", "move:Solar Beam", "Solar Beam hits every enemy, at full power.",
       ("Solar Beam", {"spread": True})),
    _t("Sharp Claws", "move:Scratch", "Scratch is 4× as likely to be a critical hit.", ("Scratch", {"crit_ratio": 3.0})),
    _t("Rend", "move:Slash", "Slash wounds the target: 1/12 of its max HP each round, for 3 rounds.",
       ("Slash", {"bleed": 1 / 12})),
    _t("Sweeping Claw", "move:Slash", "Slash hits every enemy, the others at 50% damage.",
       ("Slash", {"spread": True, "spread_share": 0.5})),
    _t("Ember Shower", "move:Ember", "Ember hits every enemy, the others at 50% damage.",
       ("Ember", {"spread": True, "spread_share": 0.5})),
    _t("Fireball", "move:Ember", "Ember hits harder: 60 power.", ("Ember", {"power": 60})),
    _t("Scorching Breath", "move:Flamethrower", "Flamethrower is 20% more likely to burn.",
       ("Flamethrower", {"status_chance": 20})),
    _t("Blowtorch", "move:Flamethrower", "Flamethrower also hits one enemy next to the target, at half damage.",
       ("Flamethrower", {"reach": 0.5})),
    _t("Firestorm", "move:Fire Spin", "Fire Spin hits every enemy.", ("Fire Spin", {"spread": True})),
    _t("Vortex", "move:Fire Spin", "Fire Spin's flames hurt twice as much: 1/8 of max HP each round.",
       ("Fire Spin", {"bind": 1 / 16})),
    _t("Fault Line", "move:Earthquake", "Earthquake hits every enemy, the others at 60% damage.",
       ("Earthquake", {"spread": True, "spread_share": 0.6})),
    _t("Bubble Burst", "move:Bubble", "Bubble hits every enemy, the others at 60% damage.",
       ("Bubble", {"spread": True, "spread_share": 0.6})),
    _t("Froth", "move:Bubble", "Bubble is twice as likely to lower Speed.", ("Bubble", {"stage_chance": 33})),
    _t("Pressure Jet", "move:Water Gun", "Water Gun hits harder: 60 power.", ("Water Gun", {"power": 60})),
    _t("Shell Shield", "move:Withdraw", "Withdraw also halves the damage the user takes for 2 rounds.",
       ("Withdraw", {"shield": 2})),
    _t("Turtle Wall", "move:Withdraw", "Withdraw works on the whole party.", ("Withdraw", {"rally": True})),
    _t("Headlong", "move:Skull Bash", "Once the user has used Withdraw in a battle, Skull Bash needs no charging.",
       ("Skull Bash", {"charge_skip": "Withdraw"})),
    _t("Geyser", "move:Hydro Pump", "Hydro Pump hits every enemy, the others at 50% damage.",
       ("Hydro Pump", {"spread": True, "spread_share": 0.5})),
    _t("Hydro Cannon", "move:Hydro Pump", "Hydro Pump never misses.", ("Hydro Pump", {"sure_hit": True})),
    _t("Frost Ray", "move:Ice Beam", "Ice Beam hits every enemy, the others at 50% damage.",
       ("Ice Beam", {"spread": True, "spread_share": 0.5})),
    _t("Whiteout", "move:Blizzard", "Blizzard never misses and hits every enemy, the others at 60% damage.",
       ("Blizzard", {"sure_hit": True, "spread": True, "spread_share": 0.6})),
    # --- Lines' own.
    # Charmander
    _t("Kindling", "own", "Scratch has a 10% chance to burn.", ("Scratch", {"status": "burn", "status_chance": 10})),
    _t("Flame Claw", "own", "Scratch becomes a Fire move (with STAB).", ("Scratch", {"type": "fire"})),
    _t("Dragon Claw", "own", "Slash is always a critical hit.", ("Slash", {"crit_ratio": 8.0})),
    _t("Pyre", "own", "Enemies the user's side burned lose a further 1/8 of their max HP each round.", pyre=1 / 8),
    _t("Supernova", "own", "Fire Blast hits every enemy at full damage, and burns 50% of the time.",
       ("Fire Blast", {"spread": True, "status_chance": 20})),
    # Squirtle
    _t("Splash Tackle", "own", "Tackle becomes a Water move (with STAB).", ("Tackle", {"type": "water"})),
    _t("Rough Shell", "own", "Whoever hits the user loses 1/16 of its max HP.", thorns=1 / 16),
    _t("Riptide", "own", "Enemies with lowered Speed take 30% more damage from the user's party.", spot__speed=0.3),
    _t("Shell Formation", "own", "While the user stands, the whole party takes 15% less damage.",
       ancient_roots=0.15),
    _t("Iron Turtle", "own", "The first hit the user takes in each battle deals no damage, and Withdraw heals the "
       "user 1/4 of its max HP.", ("Withdraw", {"heal": 0.25}), sturdy=1.0),
    _t("Fortress", "own", "While the user stands, the whole party takes 25% less damage.", ancient_roots=0.25),
    _t("Tsunami", "own", "Hydro Pump hits every enemy at full damage.",
       ("Hydro Pump", {"spread": True, "spread_share": 1.0})),
    _t("Tidal Force", "own", "The user's Water moves are always critical hits on a target below half HP.",
       ("type:water", {"keen": 0.5})),
    _t("Absolute Zero", "own", "At the start of each battle, each enemy has a 20% chance to be frozen.",
       aura__freeze=20),
    # Bulbasaur
    _t("Thorned Whip", "own", "Vine Whip has a 30% chance to poison.",
       ("Vine Whip", {"status": "poison", "status_chance": 30})),
    _t("Spore Storm", "own", "Razor Leaf has a 15% chance to set off Poison Powder and a 10% chance to set "
       "off Sleep Powder on its target.",
       ("Razor Leaf", {"triggers": (("poison_powder", "Poison Powder", 15), ("sleep_powder", "Sleep Powder", 10))})),
    _t("Sunlit", "own", "Once the user has used Growth in a battle, Solar Beam needs no charging.",
       ("Solar Beam", {"charge_skip": "Growth"})),
    _t("World Tree", "own", "Once a battle, a partner that would faint keeps 1 HP instead.", world_tree=1),
    _t("Venom Garden", "own", "All poison the user inflicts is bad poison, and Leech Seed poisons too.",
       ("Leech Seed", {"status": "poison", "status_chance": 100}), ("status:poison", {"toxic": True})),
    _t("Hyper Bloom", "own", "Hyper Beam is a Grass move and needs no rest after knocking an enemy out.",
       ("Hyper Beam", {"type": "grass", "ko_no_recharge": True})),
    _t("Ancient Roots", "own", "While the user stands, the whole party takes 15% less damage.", ancient_roots=0.15),
    # Pidgey
    _t("Squall", "own", "Gust hits every enemy, the others at 50% damage.",
       ("Gust", {"spread": True, "spread_share": 0.5})),
    _t("Buffeting Winds", "own", "Gust has a 30% chance to lower the target's Speed 1 stage.",
       ("Gust", {"stages": (("speed", -1),), "stage_chance": 30})),
    _t("Cyclone", "own", "Gust has a 10% chance to confuse.", ("Gust", {"confuse": 10})),
    _t("Decoy", "own", "Sand-Attack also makes every enemy attack the user, this round and the next.",
       ("Sand-Attack", {"taunt": 2})),
    _t("Dust Devil", "own", "Sand-Attack also makes the target take 20% more damage from everyone, "
       "for 3 rounds.", ("Sand-Attack", {"expose": 0.2})),
    _t("Downdraft", "own", "Wing Attack hits every enemy, the others at 60% damage.",
       ("Wing Attack", {"spread": True, "spread_share": 0.6})),
    _t("Eye of the Storm", "own", "Below 1/3 HP, the user's Normal and Flying moves deal 1.5× damage.",
       pinch__normal=0.5, pinch__flying=0.5),
    _t("Preening", "own", "The user heals 1/16 of its max HP at the end of each round.", regen=6.25),
    _t("Gale Force", "own", "The user's moves that hit every enemy deal 25% more.", wide=0.25),
    _t("Blind Spot", "own", "Enemies with lowered accuracy take 30% more damage from the user's party.",
       spot__accuracy=0.3),
    _t("Hurricane", "own", "Gust becomes a Flying move with 60 power, and hits every enemy at full damage.",
       ("Gust", {"type": "flying", "power": 60, "spread": True, "spread_share": 1.0})),
    _t("Sheltering Wings", "own", "While the user stands, the whole party takes 15% less damage.",
       ancient_roots=0.15),
    # Rattata
    _t("Gnawing Tackle", "own", "Tackle wounds the target: 1/16 of its max HP each round, for 3 rounds.",
       ("Tackle", {"bleed": 1 / 16})),
    _t("Nip", "own", "Tackle has a 20% chance to make the target flinch.", ("Tackle", {"flinch": 20})),
    _t("Overtake", "own", "Quick Attack is 4× as likely to be a critical hit.", ("Quick Attack", {"crit_ratio": 3.0})),
    _t("Crushing Fang", "own", "Hyper Fang has a 50% chance to lower the target's Defense 1 stage.",
       ("Hyper Fang", {"stages": (("defense", -1),), "stage_chance": 50})),
    _t("Frenzied Bite", "own", "Super Fang has a 50% chance to make the target flinch.", ("Super Fang", {"flinch": 50})),
    _t("Sprinter", "own", "Quick Attack hits twice, at 70% power each.",
       ("Quick Attack", {"hits": (2, 2), "scale": -0.3})),
    _t("Nesting", "own", "The user heals 1/16 of its max HP at the end of each round.", regen=6.25),
    _t("Quick Claws", "own", "Tackle always goes first.", ("Tackle", {"priority": 1})),
    _t("Plague Rat", "own", "The user's hits have a 15% chance to poison.", status__poison=15),
    _t("Hyper Gnasher", "own", "Hyper Beam wounds: 1/8 of the target's max HP each round, for 3 rounds; no "
       "rest after a knockout.", ("Hyper Beam", {"bleed": 1 / 8, "ko_no_recharge": True})),
    # Spearow
    _t("Pecking Order", "own", "Peck has a 30% chance to make the target flinch.", ("Peck", {"flinch": 30})),
    _t("Rapid Pecks", "own", "Peck hits twice, at 60% power each.", ("Peck", {"hits": (2, 2), "scale": -0.4})),
    _t("Screech Growl", "own", "Growl lowers Attack 2 stages.", ("Growl", {"stages": (("attack", -1),)})),
    _t("Harrier", "own", "Fury Attack becomes a Flying move.", ("Fury Attack", {"type": "flying"})),
    _t("Mob Rule", "own", "Leer also makes every enemy attack the user, this round and the next.",
       ("Leer", {"taunt": 2})),
    _t("Fearsome Beak", "own", "Drill Peck has a 30% chance to make the target flinch.", ("Drill Peck", {"flinch": 30})),
    _t("Sky Tyrant", "own", "The user's Flying moves always go first, and its moves deal 50% more to a target "
       "that hasn't moved yet this round.", ("type:flying", {"priority": 1}), ambush=0.5),
    _t("Murder of Crows", "own", "The user's moves deal 50% more to a target a partner already hit this round.",
       gang=0.5),
    # Nidoran F
    _t("Thorny Hide", "own", "Whoever hits the user loses 1/16 of its max HP.", thorns=1 / 16),
    _t("Venom Claws", "own", "Scratch has a 30% chance to poison.", ("Scratch", {"status": "poison", "status_chance": 30})),
    _t("Toxic Fangs", "own", "Bite has a 30% chance to poison.", ("Bite", {"status": "poison", "status_chance": 30})),
    _t("Den Mother", "own", "While the user stands, the whole party takes 15% less damage.", ancient_roots=0.15),
    _t("Queen's Guard", "own", "Once a battle, a partner that would faint keeps 1 HP, and the user heals it "
       "1/4 of its max HP.", world_tree=1, guard_heal=0.25),
    _t("Toxic Swipes", "own", "Fury Swipes has a 20% chance per hit to poison.",
       ("Fury Swipes", {"status": "poison", "status_chance": 20})),
    _t("Venom Queen", "own", "All poison the user inflicts is bad poison, and poisoned enemies take 25% more "
       "damage from it.", ("status:poison", {"toxic": True}), prey__poison=0.25),
    # Nidoran M
    _t("Horn Drill", "own", "Horn Attack has a 30% chance to poison.",
       ("Horn Attack", {"status": "poison", "status_chance": 30})),
    _t("Charge", "own", "Tackle hits harder: 50 power.", ("Tackle", {"power": 50})),
    _t("Rampage", "own", "Each Normal move in a row deals 25% more than the last, up to +75%.", streak__normal=0.25),
    _t("Piercing Horn", "own", "Horn Attack also hits one enemy next to the target, at half damage.",
       ("Horn Attack", {"reach": 0.5})),
    _t("Toxic Horn", "own", "Horn Attack is a Poison move, and poisons 30% of the time.",
       ("Horn Attack", {"type": "poison", "status": "poison", "status_chance": 30})),
    _t("Battle Focus", "own", "Focus Energy also makes the user's next damaging move deal 50% more.",
       ("Focus Energy", {"empower": 0.5})),
    _t("Venom Lord", "own", "All poison the user inflicts is bad poison, and the user's hits have a 20% chance "
       "to poison.", ("status:poison", {"toxic": True}), status__poison=20),
    # Caterpie
    _t("Silk Strike", "own", "After String Shot, the user hits the target with its basic attack at 60% power.",
       ("String Shot", {"follow_up": 0.6})),
    _t("Cocoon", "own", "Harden heals the user 1/4 of its max HP.", ("Harden", {"heal": 0.25})),
    _t("Psychic Wings", "own", "Confusion and Psybeam are 20% more likely to confuse.",
       ("Confusion", {"confuse": 20}), ("Psybeam", {"confuse": 20})),
    _t("Scale Dust", "own", "Stun Spore, Poison Powder and Sleep Powder never miss and work 25% more often.",
       ("Stun Spore", {"status_chance": 25, "sure_hit": True}),
       ("Poison Powder", {"status_chance": 25, "sure_hit": True}),
       ("Sleep Powder", {"status_chance": 25, "sure_hit": True})),
    _t("Butterfly Dance", "own", "The user's status moves also raise its Speed 1 stage.",
       ("status_moves", {"self_stages": (("speed", 1),)})),
    _t("Powder Storm", "own", "Psybeam has a 20% chance to set off Stun Spore, Poison Powder or Sleep Powder.",
       ("Psybeam", {"triggers": (("stun_spore", "Stun Spore", 7), ("poison_powder", "Poison Powder", 7),
                                 ("sleep_powder", "Sleep Powder", 6))})),
    _t("Psychic Mastery", "own", "Psybeam hits every enemy, the others at 60% damage.",
       ("Psybeam", {"spread": True, "spread_share": 0.6})),
    _t("Monarch", "own", "While the user stands, the whole party takes 15% less damage.", ancient_roots=0.15),
    _t("Dream Eater", "own", "The user heals 1/8 of its max HP each round for each sleeping enemy.", dream=1 / 8),
    # Weedle
    _t("Stinger", "own", "Poison Sting hits harder: 30 power.", ("Poison Sting", {"power": 30})),
    _t("Hornet's Nest", "own", "Whoever hits the user has a 25% chance to be poisoned, and takes 1/16 of its "
       "max HP.", retaliate__poison=25, thorns=1 / 16),
    _t("Twin Stingers", "own", "Twineedle hits 3 times.", ("Twineedle", {"hits": (3, 3)})),
    _t("Killer Bee", "own", "Pin Missile has a 20% chance per hit to poison.",
       ("Pin Missile", {"status": "poison", "status_chance": 20})),
    _t("Queen's Venom", "own", "The user's moves deal 30% more to poisoned enemies.", prey__poison=0.3),
    _t("Hive Queen", "own", "Once a battle, a partner that would faint keeps 1 HP instead.", world_tree=1),
    _t("Barrage", "own", "Pin Missile always hits 5 times.", ("Pin Missile", {"hits": (5, 5)})),
    _t("Stinging Swarm", "own", "Fury Attack and Pin Missile hit every enemy, the others at 50% damage.",
       ("Fury Attack", {"spread": True, "spread_share": 0.5}), ("Pin Missile", {"spread": True, "spread_share": 0.5})),
    # Pikachu
    _t("Spark", "own", "Thunder Shock is 20% more likely to paralyze.", ("Thunder Shock", {"status_chance": 20})),
    _t("Cheek Pouch", "own", "Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP.",
       second_wind=0.25),
    _t("Volt Tackle", "own", "Quick Attack becomes an Electric move with 60 power.",
       ("Quick Attack", {"type": "electric", "power": 60})),
    _t("Arc Flash", "own", "Thunder Shock also hits one enemy next to the target, at half damage.",
       ("Thunder Shock", {"reach": 0.5})),
    _t("Lightning Rod", "own", "Thunder Wave also makes every enemy attack the user, this round and the next.",
       ("Thunder Wave", {"taunt": 2})),
    _t("Overload", "own", "Thunderbolt and Thunder hit every enemy, the others at 50% damage.",
       ("Thunderbolt", {"spread": True, "spread_share": 0.5}), ("Thunder", {"spread": True, "spread_share": 0.5})),
    _t("Thunderstorm", "own", "Thunder never misses, and paralyzes 30% of the time.",
       ("Thunder", {"sure_hit": True, "status_chance": 20})),
    _t("Supercharged", "own", "The user's Electric moves deal 50% more to paralyzed enemies.", prey__paralysis=0.5),
    _t("Wind Shear", "own", "The user's moves that hit every enemy have a 20% chance to make each one flinch.",
       ("spread", {"flinch": 20})),
    _t("Pack Leader", "own", "While the user stands, the whole party takes 15% less damage.", ancient_roots=0.15),
    _t("Storm of Beaks", "own", "Fury Attack hits every enemy, at full damage.",
       ("Fury Attack", {"spread": True, "spread_share": 1.0})),
    _t("Intimidate", "own", "At the start of each battle, every enemy's Attack falls 1 stage.", intimidate=1),
    _t("Spiteful", "own", "Enemies with lowered Attack take 30% more damage from the user's party.",
       spot__attack=0.3),
    _t("Reign of Terror", "own", "While the user stands, the whole party takes 15% less damage.",
       ancient_roots=0.15),
    _t("Nurturing", "own", "While the user stands, the whole party heals 1/16 of its max HP at the end of each "
       "round.", party_regen=6.25),
    _t("Fury Queen", "own", "Fury Swipes always hits 5 times.", ("Fury Swipes", {"hits": (5, 5)})),
    _t("Megahorn", "own", "Horn Attack hits much harder: 100 power.", ("Horn Attack", {"power": 100})),
    _t("Juggernaut", "own", "The first hit the user takes in each battle deals no damage, and its Normal moves "
       "never miss.", ("type:normal", {"sure_hit": True}), sturdy=1.0),
    _t("Mind Crush", "own", "Confused enemies take 30% more damage from the user.", prey__confused=0.3),
    _t("Metamorphosis", "own", "Once a battle, ending a round below 1/3 HP heals the user half its max HP.",
       second_wind=0.5),
    _t("High Voltage", "own", "Thunderbolt is 4× as likely to be a critical hit.", ("Thunderbolt", {"crit_ratio": 3.0})),
    _t("Thunderclap", "own", "Thunder always goes first.", ("Thunder", {"priority": 1})),
    _t("Gigavolt", "own", "Thunder hits every enemy, at full damage.", ("Thunder", {"spread": True, "spread_share": 1.0})),
    _t("Thunder Cloud", "own", "At the start of each battle, each enemy has a 30% chance to be paralyzed.",
       aura__paralysis=30),
    _t("Lightning Speed", "move:Quick Attack", "Quick Attack hits 3 times, at 70% power each.",
       ("Quick Attack", {"hits": (3, 3), "scale": -0.3})),
    _t("Thunder God", "own", "Thunderbolt and Thunder never miss, and are always critical hits on a target "
       "below half HP.", ("Thunderbolt", {"sure_hit": True, "keen": 0.5}), ("Thunder", {"sure_hit": True, "keen": 0.5})),
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


# Path colours.
PURPLE, GREEN, GOLD = (170, 100, 210), (100, 190, 90), (210, 170, 90)
SKY, RED, SAND, PINK = (110, 170, 235), (220, 100, 90), (200, 160, 110), (230, 120, 190)


def _tiers(*rows: tuple[str, str, str]) -> tuple[tuple[Talent, ...], ...]:
    assert len(rows) == len(TIER_LEVELS)
    return tuple(tuple(TALENTS[key_of(n)] for n in row) for row in rows)


TALENT_TREES = {
    "bulbasaur": (
        (Path("Toxin", "Poison, seeds and sleep: wearing enemies down.", PURPLE),
         Path("Bloom", "Grass damage.", GREEN),
         Path("Bulwark", "Staying up, and keeping the partner up.", GOLD)),
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
    "charmander": (
        (Path("Cinder", "Burns, and making them hurt.", RED),
         Path("Claw", "Scratch and Slash: critical hits and wounds.", SAND),
         Path("Inferno", "Fire damage, on every enemy.", GOLD)),
        _tiers(("Kindling", "Sharp Claws", "Flame Claw"),
               ("Searing", "Lucky Strikes", "Ember Shower"),
               ("Ash Cloud", "Head Start", "Blaze"),
               ("Scorch", "Piercing Gaze", "Stoke the Flames"),
               ("Smoulder", "Gang Up", "Fireball"),
               ("Sturdy", "Blade Dance", "Feed the Flames"),
               ("Tenacity", "Rend", "Second Wind"),
               ("Scorching Breath", "Sweeping Claw", "Blowtorch"),
               ("Wildfire", "Ambush", "Unbreakable"),
               ("Vortex", "Apex Predator", "Firestorm"),
               ("Heat Haze", "Blur", "Fault Line"),
               ("Pyre", "Dragon Claw", "Supernova")),
    ),
    "squirtle": (
        (Path("Torrent", "Water damage.", SKY),
         Path("Shell", "Withdraw and shells: taking the hits, and shielding the party.", GREEN),
         Path("Tide", "Slowing, freezing and wearing enemies down.", PINK)),
        _tiers(("Splash Tackle", "Sturdy", "Wagging Tail"),
               ("Bubble Burst", "Tenacity", "Froth"),
               ("Torrent", "Rough Shell", "Tail Slap"),
               ("Pressure Jet", "Second Wind", "Undertow"),
               ("Rising Tide", "Guardian", "Crunch"),
               ("Splash Zone", "Hydration", "Riptide"),
               ("Rain Dish", "Shell Shield", "Frostbite"),
               ("Headlong", "Turtle Wall", "Frost Ray"),
               ("Geyser", "Unbreakable", "Shatter"),
               ("Hydro Cannon", "Shell Formation", "Chill"),
               ("Tsunami", "Iron Turtle", "Whiteout"),
               ("Tidal Force", "Fortress", "Absolute Zero")),
    ),
    "pidgey": (
        (Path("Gale", "Wind that hits every enemy.", SKY),
         Path("Raptor", "Fast, hard strikes on one target.", RED),
         Path("Scout", "Sand in the eyes, decoys, and keeping the partner up.", SAND)),
        _tiers(("Squall", "Head Start", "Sandstorm"),
               ("Buffeting Winds", "Lucky Strikes", "Blinding Grit"),
               ("Cyclone", "Lightning Reflexes", "Kick Up Dust"),
               ("Second Wind", "Hit and Run", "Tenacity"),
               ("Howling Wind", "Ambush", "Dust Devil"),
               ("Tempest", "Momentum", "Sturdy"),
               ("Riding the Wind", "Gale Wings", "Decoy"),
               ("Downdraft", "Afterimage", "Tailwind"),
               ("Eye of the Storm", "Ascend", "Guardian"),
               ("Gale Force", "Bird of Prey", "Preening"),
               ("Wind Shear", "Aerial Ace", "Blind Spot"),
               ("Hurricane", "Apex Predator", "Sheltering Wings")),
    ),
    "rattata": (
        (Path("Fang", "Biting: wounds, flinches and fangs.", RED),
         Path("Scurry", "Speed: Quick Attack, and striking first.", SKY),
         Path("Survivor", "Scrappy: fighting on when cornered.", SAND)),
        _tiers(("Gnawing Tackle", "Head Start", "Wagging Tail"),
               ("Nip", "Lightning Reflexes", "Scavenger"),
               ("Tail Slap", "Hit and Run", "Cornered"),
               ("Lucky Strikes", "Momentum", "Tenacity"),
               ("Gang Up", "Overtake", "Second Wind"),
               ("Bone Crusher", "Keen Focus", "Heavy Body"),
               ("Crushing Fang", "Shared Focus", "Sturdy"),
               ("Gnaw", "Ambush", "Guardian"),
               ("Frenzied Bite", "Sprinter", "Nesting"),
               ("Overdrive", "Quick Claws", "Plague Rat"),
               ("Apex Predator", "Blur", "Unbreakable"),
               ("Hyper Gnasher", "Lightning Speed", "Pack Leader")),
    ),
    "spearow": (
        (Path("Talon", "Pecks and Drill Peck: hard Flying strikes.", RED),
         Path("Flock", "Fury Attack and ganging up.", SKY),
         Path("Bully", "Growl and Leer: weakening and scaring the enemies.", SAND)),
        _tiers(("Pecking Order", "Gang Up", "Taunting Growl"),
               ("Rapid Pecks", "Lucky Strikes", "Menacing Leer"),
               ("Head Start", "Cornered", "Piercing Gaze"),
               ("Ambush", "Frenzy", "Screech Growl"),
               ("Riding the Wind", "Harrier", "Mob Rule"),
               ("Aerial Ace", "Star Shower", "Tenacity"),
               ("Drill Run", "Howling Wind", "Sturdy"),
               ("Fearsome Beak", "Afterimage", "Second Wind"),
               ("Bird of Prey", "Tailwind", "Guardian"),
               ("Overdrive", "Tempest", "Intimidate"),
               ("Sky Tyrant", "Murder of Crows", "Spiteful"),
               ("Apex Predator", "Storm of Beaks", "Reign of Terror")),
    ),
    "nidoran_f": (
        (Path("Venom", "Poison, and making it worse.", PURPLE),
         Path("Claw", "Scratching, biting and kicking.", RED),
         Path("Matriarch", "Keeping the partner safe.", GOLD)),
        _tiers(("Toxic Touch", "Lucky Strikes", "Taunting Growl"),
               ("Poison Point", "Cornered", "Sturdy"),
               ("Barbed Sting", "Head Start", "Thorny Hide"),
               ("Sapping", "Venom Claws", "Second Wind"),
               ("Venom Needle", "Tail Slap", "Wagging Tail"),
               ("Contagion", "Gang Up", "Tenacity"),
               ("Siphon", "Crunch", "Echoing Growl"),
               ("Virulent", "Raking Claws", "Nurturing"),
               ("Toxic Fangs", "Rapid Kicks", "Guardian"),
               ("Toxic Swipes", "Ambush", "Heavy Body"),
               ("Miasma", "Apex Predator", "Den Mother"),
               ("Venom Queen", "Fury Queen", "Queen's Guard")),
    ),
    "nidoran_m": (
        (Path("Venom", "Poison, and making it worse.", PURPLE),
         Path("Horn", "Horn Attack: critical hits and piercing.", RED),
         Path("Brawler", "Focus, charging and momentum.", SAND)),
        _tiers(("Toxic Touch", "Lucky Strikes", "Charge"),
               ("Poison Point", "Gore", "Momentum"),
               ("Barbed Sting", "Piercing Horn", "Cornered"),
               ("Sapping", "Head Start", "Menacing Leer"),
               ("Horn Drill", "Piercing Gaze", "Keen Focus"),
               ("Contagion", "Ambush", "Heavy Body"),
               ("Siphon", "Frenzy", "Battle Focus"),
               ("Virulent", "Gang Up", "Rampage"),
               ("Venom Needle", "Rapid Kicks", "Second Wind"),
               ("Toxic Horn", "Tenacity", "Sturdy"),
               ("Miasma", "Apex Predator", "Shared Focus"),
               ("Venom Lord", "Megahorn", "Juggernaut")),
    ),
    "caterpie": (
        (Path("Psychic", "Confusion and Psybeam: muddled minds.", PINK),
         Path("Powder", "String Shot and powders: status on every enemy.", SAND),
         Path("Cocoon", "Harden and shells: lasting, and shielding the partner.", GREEN)),
        _tiers(("Head Start", "Web", "Sturdy"),
               ("Mind Games", "Sticky Silk", "Iron Shell"),
               ("Psychic Wings", "Silk Strike", "Cocoon"),
               ("Lucky Strikes", "Numbing Cloud", "Shed Skin"),
               ("Echo", "Toxic Spores", "Shell Wall"),
               ("Howling Wind", "Drowsy Dust", "Gluttony"),
               ("Butterfly Dance", "Pollen Cloud", "Second Wind"),
               ("Ambush", "Conductor", "Guardian"),
               ("Swarm", "Scale Dust", "Tenacity"),
               ("Tempest", "Nightmare", "Soothing Spores"),
               ("Psychic Mastery", "Powder Storm", "Monarch"),
               ("Mind Crush", "Dream Eater", "Metamorphosis")),
    ),
    "weedle": (
        (Path("Venom", "Poison, and making it worse.", PURPLE),
         Path("Swarm", "Many quick stings.", GOLD),
         Path("Hive", "Harden, silk and guarding the partner.", SAND)),
        _tiers(("Barbed Sting", "Stinger", "Sturdy"),
               ("Toxic Touch", "Lucky Strikes", "Iron Shell"),
               ("Poison Point", "Frenzy", "Web"),
               ("Sapping", "Swarm", "Shed Skin"),
               ("Envenom", "Hive Mind", "Shell Wall"),
               ("Contagion", "Blade Dance", "Sticky Silk"),
               ("Siphon", "Needle Storm", "Shared Focus"),
               ("Virulent", "Twin Stingers", "Tenacity"),
               ("Venom Needle", "Afterimage", "Tailwind"),
               ("Killer Bee", "Feeding Frenzy", "Second Wind"),
               ("Miasma", "Barrage", "Hornet's Nest"),
               ("Queen's Venom", "Stinging Swarm", "Hive Queen")),
    ),
    "pikachu": (
        (Path("Spark", "Paralysis: slowing and stopping enemies.", GOLD),
         Path("Bolt", "Raw Electric damage.", SKY),
         Path("Agile", "Quick Attack, speed and dodging trouble.", RED)),
        _tiers(("Spark", "Lucky Strikes", "Head Start"),
               ("Static", "Surge", "Cheek Pouch"),
               ("Live Wire", "Gang Up", "Sturdy"),
               ("Conductor", "Charge Up", "Lightning Reflexes"),
               ("Chain Lightning", "Discharge", "Hit and Run"),
               ("Arc Flash", "Star Shower", "Volt Tackle"),
               ("Lightning Rod", "High Voltage", "Ambush"),
               ("Taunting Growl", "Apex Predator", "Afterimage"),
               ("Thunderstorm", "Overload", "Tailwind"),
               ("Tenacity", "Thunderclap", "Guardian"),
               ("Thunder Cloud", "Gigavolt", "Blur"),
               ("Supercharged", "Thunder God", "Lightning Speed")),
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
