"""Moves: what a Pokémon does in battle.

A move here is its Gen 1 base form. The buff and link skills learned in
its skill tree (skills.py) make a changed copy of it for a particular
Pokémon (`skills.apply_changes`), so every effect is a field.
`describe` puts a move into words for the skill tree screen.
"""

from dataclasses import dataclass
from fractions import Fraction

from .type_chart import name as type_name


@dataclass(frozen=True)
class Move:
    name: str
    power: int          # 0 = status move (no damage)
    target: str         # "enemy" (the other side), "ally" (own side) or "self"
    anim: str = ""      # animation name; "" = the species' `fight_anim`
    type: str = ""      # one of type_chart.TYPES; "" = typeless
    # Moves with a charge message spend a round charging (the first half of
    # the animation) and fire the next round (the second half).
    charge: str = ""
    status: str = ""    # a status (see status.STATUSES) the move inflicts ...
    status_chance: int = 0  # ... with this % chance (a status move's chance to work)
    stages: tuple[tuple[str, int], ...] = ()  # stat stage changes on the target ("attack", -1)
    stage_chance: int = 100  # damaging moves: % chance the stage changes happen
    confuse: int = 0    # % chance to confuse the target
    flinch: int = 0     # % chance the target flinches (loses its turn, if it hasn't moved yet)
    seed: float = 0.0   # Leech Seed: share of the target's max HP drained each round
    bind: float = 0.0   # Wrap: share of the target's max HP lost each round, for 2-5 rounds
    shield: int = 0     # Leaf Shield: rounds the target takes half damage
    spread: bool = False      # hits every target on that side
    spread_share: float = 1.0  # damage share of each hit when it spreads
    hits: tuple[int, int] = (1, 1)  # hits per use (2-5: Fury Attack)
    priority: int = 0   # goes before moves with a lower priority (Quick Attack: 1)
    halve: bool = False  # Super Fang: takes half the target's HP instead of normal damage
    drain: float = 0.0  # the user heals this share of the damage dealt (Absorb)
    heal: float = 0.0   # the user also heals this share of its max HP
    rest: bool = False  # Rest: the user heals fully, is cured, and sleeps 2 rounds
    focus: bool = False  # Focus Energy: the user's crit chance ×4 for the battle
    recoil: float = 0.0  # the user takes this share of the damage dealt
    recharge: bool = False  # the user must rest the next round (Hyper Beam)
    self_confuse: bool = False  # the user becomes confused afterwards (Thrash)
    crit_ratio: float = 1.0  # × crit chance (8 = Gen 1's high crit ratio)
    sure_hit: bool = False  # ignores the user's lowered accuracy (Swift)
    immune: tuple[str, ...] = ()  # types it doesn't affect (Leech Seed: Grass)
    toxic: bool = False  # its poison gets worse every round (Toxic)
    sleep_bonus: int = 0  # extra rounds asleep
    scale: float = 1.0   # power × this (from buffs)
    bleed: float = 0.0   # wounds the target: it loses this share of its max HP each round, for 3 rounds
    self_stages: tuple[tuple[str, int], ...] = ()  # stat stage changes on the user, after the move
    # Other moves of the user's this one sets off when it lands: (skill key,
    # move name, % chance); a set-off move doesn't set off more.
    triggers: tuple[tuple[str, str, int], ...] = ()

    @property
    def damaging(self) -> bool:
        return self.power > 0 or self.halve


def _status(key: str, chance: int = 100) -> dict:
    return {"status": key, "status_chance": chance}


MOVES = {m.name: m for m in [
    # Normal
    Move("Tackle", 35, "enemy", "tackle", type="normal"),
    Move("Scratch", 40, "enemy", type="normal"),
    Move("Pound", 40, "enemy", type="normal"),
    Move("Quick Attack", 40, "enemy", type="normal", priority=1),
    Move("Headbutt", 70, "enemy", type="normal", flinch=30),
    Move("Bite", 60, "enemy", type="normal", flinch=10),
    Move("Horn Attack", 65, "enemy", type="normal"),
    Move("Slash", 70, "enemy", type="normal", crit_ratio=8),
    Move("Hyper Fang", 80, "enemy", type="normal", flinch=10),
    Move("Super Fang", 0, "enemy", type="normal", halve=True),
    Move("Slam", 80, "enemy", type="normal"),
    Move("Body Slam", 85, "enemy", type="normal", **_status("paralysis", 30)),
    Move("Take Down", 90, "enemy", type="normal", recoil=0.25),
    Move("Skull Bash", 100, "enemy", type="normal", charge="{user} lowered its head!"),
    Move("Double-Edge", 100, "enemy", type="normal", recoil=0.25),
    Move("Thrash", 90, "enemy", type="normal", self_confuse=True),
    Move("Hyper Beam", 150, "enemy", type="normal", recharge=True),
    Move("Swift", 60, "enemy", type="normal", sure_hit=True),
    Move("Fury Attack", 15, "enemy", type="normal", hits=(2, 5)),
    Move("Fury Swipes", 18, "enemy", type="normal", hits=(2, 5)),
    Move("Double Slap", 15, "enemy", type="normal", hits=(2, 5)),
    Move("Wrap", 15, "enemy", type="normal", bind=1 / 16),
    Move("Growl", 0, "enemy", type="normal", stages=(("attack", -1),)),
    Move("Tail Whip", 0, "enemy", type="normal", stages=(("defense", -1),)),
    Move("Leer", 0, "enemy", type="normal", stages=(("defense", -1),)),
    Move("Sand-Attack", 0, "enemy", type="normal", stages=(("accuracy", -1),)),
    Move("Smokescreen", 0, "enemy", type="normal", stages=(("accuracy", -1),)),
    Move("String Shot", 0, "enemy", type="bug", stages=(("speed", -1),)),
    # Whirlwind ended a wild battle in Gen 1; here it lowers every enemy's Speed.
    Move("Whirlwind", 0, "enemy", type="normal", stages=(("speed", -1),), spread=True),
    Move("Growth", 0, "self", "growth", type="normal", stages=(("attack", 1),)),
    Move("Harden", 0, "self", type="normal", stages=(("defense", 1),)),
    Move("Withdraw", 0, "self", type="water", stages=(("defense", 1),)),
    Move("Agility", 0, "self", type="psychic", stages=(("speed", 2),)),
    Move("Swords Dance", 0, "self", type="normal", stages=(("attack", 2),)),
    Move("Focus Energy", 0, "self", type="normal", focus=True),
    Move("Rest", 0, "self", type="psychic", rest=True),
    Move("Supersonic", 0, "enemy", type="normal", confuse=55),
    Move("Bind", 15, "enemy", type="normal", bind=1 / 16),
    Move("Defense Curl", 0, "self", type="normal", stages=(("defense", 1),)),
    Move("Screech", 0, "enemy", type="normal", stages=(("defense", -2),)),
    Move("Glare", 0, "enemy", type="normal", **_status("paralysis", 75)),
    Move("Sing", 0, "enemy", type="normal", **_status("sleep", 55)),
    # Flying
    Move("Gust", 40, "enemy", "gust", type="flying"),  # Normal in Gen 1, Flying since Gen 2
    Move("Peck", 35, "enemy", type="flying"),
    Move("Drill Peck", 80, "enemy", type="flying"),
    Move("Wing Attack", 35, "enemy", type="flying"),
    Move("Sky Attack", 140, "enemy", type="flying", charge="{user} is glowing!", crit_ratio=8),
    # Grass
    Move("Absorb", 20, "enemy", type="grass", drain=0.5),
    Move("Mega Drain", 40, "enemy", type="grass", drain=0.5),
    Move("Vine Whip", 35, "enemy", type="grass"),
    Move("Razor Leaf", 55, "enemy", type="grass", crit_ratio=8),
    Move("Petal Dance", 70, "enemy", type="grass", spread=True, self_confuse=True),
    Move("Solar Beam", 120, "enemy", "solar_beam", type="grass", charge="{user} took in sunlight!"),
    Move("Leech Seed", 0, "enemy", type="grass", seed=1 / 16, immune=("grass",)),
    Move("Leaf Shield", 0, "ally", "leaf_shield", type="grass", shield=2),
    Move("Sleep Powder", 0, "enemy", type="grass", **_status("sleep", 75)),
    Move("Stun Spore", 0, "enemy", type="grass", **_status("paralysis", 75)),
    # Poison
    Move("Poison Sting", 15, "enemy", type="poison", **_status("poison", 30)),
    Move("Acid", 40, "enemy", type="poison", stages=(("defense", -1),), stage_chance=33),
    Move("Poison Powder", 0, "enemy", type="poison", **_status("poison", 75)),
    # Bug
    Move("Twineedle", 25, "enemy", type="bug", hits=(2, 2), **_status("poison", 20)),
    Move("Pin Missile", 14, "enemy", type="bug", hits=(2, 5)),
    # Fire
    Move("Ember", 40, "enemy", type="fire", **_status("burn", 10)),
    Move("Flamethrower", 95, "enemy", type="fire", **_status("burn", 10)),
    Move("Fire Spin", 15, "enemy", type="fire", bind=1 / 16),
    Move("Fire Blast", 120, "enemy", type="fire", **_status("burn", 30)),
    # Fighting and Ground
    Move("Double Kick", 30, "enemy", type="fighting", hits=(2, 2)),
    Move("Earthquake", 100, "enemy", type="ground"),
    Move("Dig", 100, "enemy", type="ground", charge="{user} dug a hole!"),
    # Rock
    Move("Rock Throw", 50, "enemy", type="rock"),
    Move("Rock Slide", 75, "enemy", type="rock"),
    # Electric
    Move("Thunder Shock", 40, "enemy", type="electric", **_status("paralysis", 10)),
    Move("Thunderbolt", 95, "enemy", type="electric", **_status("paralysis", 10)),
    Move("Thunder", 120, "enemy", type="electric", **_status("paralysis", 10)),
    Move("Thunder Wave", 0, "enemy", type="electric", **_status("paralysis"), immune=("ground",)),
    # Water
    Move("Water Gun", 40, "enemy", type="water"),
    Move("Bubble", 20, "enemy", type="water", stages=(("speed", -1),), stage_chance=33),
    Move("Bubble Beam", 65, "enemy", type="water", stages=(("speed", -1),), stage_chance=33),
    Move("Clamp", 35, "enemy", type="water", bind=1 / 16),
    Move("Surf", 95, "enemy", type="water"),
    Move("Hydro Pump", 120, "enemy", type="water"),
    # Ice
    Move("Aurora Beam", 65, "enemy", type="ice", stages=(("attack", -1),), stage_chance=10),
    Move("Ice Punch", 75, "enemy", type="ice", **_status("freeze", 10)),
    Move("Ice Beam", 95, "enemy", type="ice", **_status("freeze", 10)),
    Move("Blizzard", 120, "enemy", type="ice", **_status("freeze", 10)),
    Move("Lovely Kiss", 0, "enemy", type="normal", **_status("sleep", 75)),
    # Psychic and Ghost
    Move("Confusion", 50, "enemy", type="psychic", confuse=10),
    Move("Psybeam", 65, "enemy", type="psychic", confuse=10),
    # Gen 1's Psychic lowered Special (not in this game); here it's Defense.
    Move("Psychic", 90, "enemy", type="psychic", stages=(("defense", -1),), stage_chance=33),
    Move("Lick", 20, "enemy", type="ghost", **_status("paralysis", 30)),
    Move("Confuse Ray", 0, "enemy", type="ghost", confuse=100),
]}

STAT_WORDS = {"attack": "Attack", "defense": "Defense", "speed": "Speed", "accuracy": "accuracy"}
STATUS_VERBS = {"poison": "poison", "burn": "burn", "paralysis": "paralyze", "sleep": "put to sleep",
                "freeze": "freeze"}


def _fraction(share: float) -> str:
    return str(Fraction(share).limit_denominator(32))


def describe(m: Move) -> str:
    """The move in words, e.g. "Grass, 55 power. High critical-hit ratio."."""
    who = {"enemy": "every enemy" if m.spread else "an enemy", "ally": "the party" if m.spread else "an ally",
           "self": "the user"}[m.target]
    kind = type_name(m.type) if m.type else "Typeless"
    parts = []
    if m.halve:
        parts.append(f"{kind}. Takes half the target's HP.")
    elif m.damaging:
        head = f"{kind}, {round(m.power * m.scale)} power"
        lo, hi = m.hits
        if hi > 1:
            head += ", hits twice" if lo == hi == 2 else f", hits {lo}-{hi} times"
        parts.append(head + ".")
        if m.spread:
            share = "" if m.spread_share == 1 else f" at {round(m.spread_share * 100)}% damage"
            parts.append(f"Hits every enemy{share}.")
    if m.priority:
        parts.append("Always goes first.")
    if m.charge:
        parts.append("Charges for a round first.")
    if m.crit_ratio == 8:
        parts.append("High critical-hit ratio.")
    elif m.crit_ratio > 1:
        parts.append(f"Critical hits ×{m.crit_ratio:g} as likely.")
    if m.sure_hit:
        parts.append("Ignores accuracy drops.")
    if m.status:
        verb = STATUS_VERBS[m.status]
        if m.damaging:
            parts.append(f"{m.status_chance}% chance to {verb}.")
        else:
            chance = "" if m.status_chance >= 100 else f" ({m.status_chance}% chance)"
            parts.append(f"{verb.capitalize()}s {who}{chance}." if verb != "put to sleep"
                         else f"Puts {who} to sleep{chance}.")
    if m.confuse:
        parts.append(f"{m.confuse}% chance to confuse." if m.damaging or m.confuse < 100
                     else f"Confuses {who}.")
    if m.flinch:
        parts.append(f"{m.flinch}% chance to make it flinch.")
    for stat, change in m.stages:
        verb = "Raises" if change > 0 else "Lowers"
        n = abs(change)
        target = "its" if m.damaging else ("its" if m.target == "self" else f"{who}'s")
        text = f"{verb} {target} {STAT_WORDS[stat]} {n} stage{'s' if n > 1 else ''}"
        if m.damaging and m.stage_chance < 100:
            text = f"{m.stage_chance}% chance to lower its {STAT_WORDS[stat]}"
        parts.append(text + ".")
    if m.seed:
        parts.append(f"Seeds {who}: drains {_fraction(m.seed)} of its max HP each round.")
    if m.bind:
        parts.append(f"Binds it for 2-5 rounds: {_fraction(m.bind)} of its max HP each round.")
    if m.shield:
        parts.append(f"Halves the damage {who} takes for {m.shield} rounds.")
    if m.drain:
        parts.append(f"Heals the user {_fraction(m.drain)} of the damage dealt.")
    if m.heal:
        parts.append(f"Heals the user {_fraction(m.heal)} of its max HP.")
    if m.rest:
        parts.append("The user heals fully, is cured, and sleeps for 2 rounds.")
    if m.focus:
        parts.append("The user's critical-hit chance ×4 for the battle.")
    if m.recoil:
        parts.append(f"The user takes {_fraction(m.recoil)} of the damage dealt.")
    if m.recharge:
        parts.append("The user must rest the next round.")
    if m.self_confuse:
        parts.append("The user becomes confused afterwards.")
    if m.immune:
        parts.append(f"Doesn't affect {', '.join(type_name(t) for t in m.immune)} types.")
    if m.toxic:
        parts.append("Its poison gets worse every round.")
    if m.sleep_bonus:
        parts.append(f"Sleeps {m.sleep_bonus} round{'s' if m.sleep_bonus > 1 else ''} longer.")
    if m.bleed:
        parts.append(f"Wounds it: {_fraction(m.bleed)} of its max HP each round for 3 rounds.")
    for stat, change in m.self_stages:
        n = abs(change)
        parts.append(f"{'Raises' if change > 0 else 'Lowers'} the user's {STAT_WORDS[stat]} {n} "
                     f"stage{'s' if n > 1 else ''}.")
    for _, name, chance in m.triggers:
        parts.append(f"{chance}% chance to set off {name}." if chance < 100 else f"Sets off {name}.")
    return " ".join(parts)
