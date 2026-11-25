"""The talent system's parts (`talents.py` puts them together): moves
learned by level (`LearnedMove`), how talents change moves
(`apply_changes`, `_selects`), talents (`Talent`, `_t`) and a line's tree
(`TalentTree`, `Path`). The data: `learnsets.py`, `talent_list*.py`,
`talent_trees*.py`."""

from dataclasses import dataclass, field, replace

from .moves import MOVES, Move

TIER_LEVELS = (6, 10, 14, 18, 22, 27, 32, 38, 44, 50, 60, 75)
DEEP = {10: 4, 11: 6}  # tier index -> earlier picks the talent needs in its own path
MAX_EQUIPPED = 4
TALENT_MODS = {"first", "crit", "endure", "regen", "drain"}  # talent flags that work as the gear mods (and status:<status>)


def key_of(name: str) -> str:
    """A move's key (saved in `Monster.equipped`): "Leech Seed" -> "leech_seed"."""
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")



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
         "priority", "sleep_bonus", "scale", "crit_ratio", "recoil", "reach", "empower", "spikes",
         "contagious", "siphon", "nightmare", "hunt_crit"}
CHANCES = {"status_chance", "stage_chance", "confuse", "flinch", "contagious"}


def _add_stages(old: tuple, extra: tuple) -> tuple:
    total = dict(old)
    for stat, change in extra:
        total[stat] = total.get(stat, 0) + change
    return tuple((stat, change) for stat, change in total.items() if change)


def apply_changes(move: Move, changes: dict) -> Move:
    """`move` with a talent's changes: numbers add up (chances to at most
    100%), stage changes add per stat, triggers join; `keen`, `power`, `bleed`
    and a spreading move's `spread_share` keep the higher value; other fields
    are set.
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
        elif name in ("keen", "hunt", "power", "bleed") or (name == "spread_share" and move.spread):
            new[name] = max(old, value)  # (a later talent never weakens an earlier one's: Apex Predator, Keen Edge)
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
#   aura:<status>    % chance per foe at the battle's start to give it the status ("confused" too)
#   sniper           critical hits deal this much more (on top of ×1.5)
#   magic_guard      no damage from status, seeds, binds, wounds or nightmares
#   pyre             burned foes of the holder's side lose this share of max HP more a round
#   lower:<stat>     the foes' stat falls this many stages at the battle's start (Intimidate, Sand Veil)
#   filter           super-effective hits on the user deal this share less
#   drain            (as the gear mod) % of the damage dealt the user heals
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
STONE = (170, 160, 150)
SKY, RED, SAND, PINK = (110, 170, 235), (220, 100, 90), (200, 160, 110), (230, 120, 190)
