"""Quests: the story (following Red/Blue) and side jobs (docs/quests.md).

A quest has steps done in order: visit a building in a town (press Up at
it), defeat a route's boss, or reach a town. Quests are taken from a
town's quest board, or start by themselves once the quests they need are
done. Their state lives in `Game.quests` (quest key → the step it's at;
`len(steps)` = done).

Everything that happens (accepting, visiting, winning, arriving) goes
through `Event`s: the dialogue to show, quests started or finished, and
rewards given; the map scene shows them in turn.

Every quest pays Poké Dollars and XP (each party member gets the XP, as
from a battle); major quests (rival and gym battles, story milestones)
also give items.
"""

import random
from dataclasses import dataclass, field

from ..dev import DEV
from ..mechanics.items import ITEMS, Gear, money_text
from ..mechanics.loot import Reward
from ..mechanics.pokemon import MAX_LEVEL

Line = tuple[str, str]  # (speaker, text) of a dialogue page


@dataclass(frozen=True)
class Step:
    kind: str     # "visit" (a building in a town), "defeat" (a route's boss) or "reach" (a town)
    target: str   # visit: the building's name; defeat: the route key; reach: the town key
    text: str     # the objective, as shown on the map and in the quest log
    town: str = ""  # visit: the town the building is in
    dialogue: tuple[Line, ...] = ()  # shown when the step is done
    gives: tuple[str, ...] = ()      # key items received ...
    takes: tuple[str, ...] = ()      # ... and handed over


@dataclass(frozen=True)
class Quest:
    key: str
    name: str
    summary: str
    steps: tuple[Step, ...]
    money: int  # Poké Dollars, given when it's done ...
    xp: int     # ... and XP for each party member
    board: str = ""                  # the town whose quest board posts it ("" = starts by itself)
    requires: tuple[str, ...] = ()   # quests that must be done first
    # Items given too: ("medicine", name, count) or ("gear", item, rarity, level).
    rewards: tuple[tuple, ...] = ()
    done_dialogue: tuple[Line, ...] = ()  # shown when it's done (after the last step's)


QUESTS = {q.key: q for q in [
    Quest(
        "oaks_parcel", "Oak's Parcel",
        "The Viridian Poké Mart has a parcel for Professor Oak and needs someone to take it to Pallet Town.",
        board="viridian",
        steps=(
            Step("visit", "Poké Mart", "Pick up the parcel at the Viridian Poké Mart", town="viridian",
                 dialogue=(("Clerk", "Hey! You came from Pallet Town? Then you know Professor Oak!"),
                           ("Clerk", "His order came in. Will you take it to him?"),
                           ("", "You received Oak's Parcel!")),
                 gives=("Oak's Parcel",)),
            Step("visit", "Professor Oak's Lab", "Deliver Oak's Parcel to Professor Oak (Pallet Town)",
                 town="pallet",
                 dialogue=(("Oak", "Oh, that's the custom Poké Ball I ordered! Thank you!"),
                           ("Oak", "Here: take this Pokédex. It records every Pokémon you see."),
                           ("", "You received the Pokédex!"),
                           ("Oak", "Your rival went west of Viridian City, to Route 22. "
                                   "He said he wants to battle you!")),
                 takes=("Oak's Parcel",), gives=("Pokédex",)),
        ),
        money=300, xp=200,
        rewards=(("medicine", "Potion", 5),),
    ),
    Quest(
        "rival_22", "Rival on Route 22",
        "Your rival is waiting for you on Route 22, west of Viridian City.",
        requires=("oaks_parcel",),
        steps=(Step("defeat", "route_22", "Defeat your rival on Route 22 (west of Viridian City)"),),
        money=600, xp=300,
        rewards=(("medicine", "Super Potion", 2), ("gear", None, "Uncommon", 9)),
        done_dialogue=(("Rival", "What? I can't believe I lost! I'm off to Pewter City. Smell ya later!"),),
    ),
    Quest(
        "forest_bugs", "Bugs in the Forest",
        "A giant Caterpie is blocking the path through Viridian Forest. Clear the way to Pewter City.",
        board="viridian", requires=("oaks_parcel",),
        steps=(Step("defeat", "viridian_forest", "Defeat the giant Caterpie in Viridian Forest"),),
        money=500, xp=400,
        rewards=(("medicine", "Super Potion", 2), ("gear", None, "Common", 10)),
    ),
]}


@dataclass
class Event:
    """Something to show after a quest event, in order."""
    dialogue: list[Line] = field(default_factory=list)
    started: list[str] = field(default_factory=list)   # quest keys
    finished: list[str] = field(default_factory=list)  # quest keys
    rewards: list[Reward] = field(default_factory=list)
    xp: int = 0  # XP each party member got
    level_ups: list[str] = field(default_factory=list)  # e.g. "Bulbasaur grew to Lv8!"

    def __bool__(self) -> bool:
        return bool(self.dialogue or self.started or self.finished or self.rewards)


# --- a game's quest state (`game` is a progress.Game) --------------------

def step(game, key: str) -> int | None:
    """The step `key` is at (None: not started; len(steps): done)."""
    return game.quests.get(key)


def is_done(game, key: str) -> bool:
    return step(game, key) == len(QUESTS[key].steps)


def is_active(game, key: str) -> bool:
    s = step(game, key)
    return s is not None and s < len(QUESTS[key].steps)


def current(game, key: str) -> Step | None:
    """The step an active quest is at."""
    return QUESTS[key].steps[step(game, key)] if is_active(game, key) else None


def active(game) -> list[Quest]:
    return [q for q in QUESTS.values() if is_active(game, q.key)]


def ready(game, quest: Quest) -> bool:
    """Not started yet, and the quests it needs are done."""
    return step(game, quest.key) is None and all(is_done(game, r) for r in quest.requires)


def board(game, town: str) -> list[Quest]:
    """The quests a town's board shows: ready to take, active and done."""
    return [q for q in QUESTS.values() if q.board == town and (ready(game, q) or step(game, q.key) is not None)]


def can_take(game, town: str) -> list[Quest]:
    return [q for q in board(game, town) if ready(game, q)]


def accept(game, key: str) -> Event:
    event = Event()
    _start(game, key, event)
    return event


def visit(game, town: str, building: str) -> Event:
    """The player pressed Up at `building` in `town`."""
    return _advance_where(game, lambda s: s.kind == "visit" and s.town == town and s.target == building)


def defeat(game, route: str) -> Event:
    """The player beat `route`'s boss."""
    return _advance_where(game, lambda s: s.kind == "defeat" and s.target == route)


def reach(game, town: str) -> Event:
    """The player arrived in `town` (also starts quests that start by themselves)."""
    event = _advance_where(game, lambda s: s.kind == "reach" and s.target == town)
    _start_automatic(game, event)
    return event


def open_for(game, needs: tuple[str, str] | None) -> bool:
    """Whether a (quest, "started"/"done") condition holds (None: always)."""
    if not needs:
        return True
    key, what = needs
    return is_done(game, key) if what == "done" else step(game, key) is not None


# --- inside ------------------------------------------------------------------

def _start(game, key: str, event: Event) -> None:
    game.quests[key] = 0
    event.started.append(key)


def _advance_where(game, matches) -> Event:
    event = Event()
    for quest in active(game):
        s = current(game, quest.key)
        if s and matches(s):
            _advance(game, quest, event)
    return event


def _advance(game, quest: Quest, event: Event) -> None:
    s = current(game, quest.key)
    event.dialogue += s.dialogue
    for item in s.takes:
        if item in game.bag.key_items:
            game.bag.key_items.remove(item)
    game.bag.key_items += [i for i in s.gives if i not in game.bag.key_items]
    game.quests[quest.key] += 1
    if is_done(game, quest.key):
        event.dialogue += quest.done_dialogue
        event.finished.append(quest.key)
        rewards = [Reward(money=quest.money)] + [_reward(r) for r in quest.rewards]
        for r in rewards:
            r.give(game.bag)
        event.rewards += rewards
        _give_xp(game, quest.xp * DEV.xp_multiplier, event)
        _start_automatic(game, event)


def _give_xp(game, xp: int, event: Event) -> None:
    """Every party member gets `xp`, leveling up as in battle (evolving
    waits for its next level up in a battle)."""
    event.xp += xp
    for m in game.party:
        if m.level >= MAX_LEVEL:
            continue
        start = m.level
        m.xp += xp
        while m.can_level_up:
            m.level_up()
        if m.level > start:
            event.level_ups.append(f"{m.name} grew to Lv{m.level}!")


def reward_text(quest: Quest) -> str:
    """What it pays, e.g. "₽300, 200 XP, 5 Potions, Uncommon gear (Lv9)"."""
    parts = [money_text(quest.money), f"{quest.xp} XP"]
    for spec in quest.rewards:
        if spec[0] == "medicine":
            parts.append(f"{spec[2]} {spec[1]}{'s' if spec[2] > 1 else ''}")
        else:
            parts.append(f"{spec[2]} {spec[1] or 'gear'} (Lv{spec[3]})")
    return ", ".join(parts)


def _reward(spec: tuple) -> Reward:
    """A quest reward: ("medicine", name, count) or ("gear", item or None for
    any but a berry, rarity, item level)."""
    if spec[0] == "medicine":
        return Reward(medicine=spec[1], count=spec[2])
    item = spec[1] or random.choice([name for name, i in ITEMS.items() if i.slot != "berry"])
    return Reward(gear=Gear.roll(item, spec[2], level=spec[3]))


def _start_automatic(game, event: Event) -> None:
    for quest in QUESTS.values():
        if not quest.board and ready(game, quest):
            _start(game, quest.key, event)
