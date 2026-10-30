"""Quests: the story (following Red/Blue) and side jobs (docs/quests.md).

A quest has steps done in order: visit a building in a town (press Up at
it), defeat a route's boss, reach a town, defeat a number of one species
("hunt"), collect a number of quest items that drop in battles on a route
("collect"), hand it in at any quest board ("hand_in"), or evolve a
Pokémon ("evolve", from the party screen). Quests are taken from a town's
quest board, start by themselves once the quests they need are done, or
start when their item drops in a battle (`Quest.drop`: evolution quests).
Evolutions only happen once their quest unlocks them (`can_evolve`). Their state lives in `Game.quests` (quest key → the
step it's at; `len(steps)` = done) and `Game.quest_counts` (how far a
counted step has got).

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
from ..mechanics.pokemon import MAX_LEVEL, SPECIES, Monster, line_base
from .instance import RECRUITS, Recruit

Line = tuple[str, str]  # (speaker, text) of a dialogue page


@dataclass(frozen=True)
class Step:
    # "visit" (a building in a town), "defeat" (a route's boss), "reach" (a
    # town), "hunt" (defeat `count` of a species), "collect" (`count` quest
    # items), "hand_in" (at any quest board) or "evolve" (a Pokémon, from the
    # party screen, once it has the level)
    kind: str
    # visit: the building's name; defeat: the route key; reach: the town
    # key; hunt: the species key; collect: the item's name; evolve: the
    # species key that evolves
    target: str
    text: str     # the objective, as shown on the map and in the quest log
    town: str = ""  # visit: the town the building is in
    dialogue: tuple[Line, ...] = ()  # shown when the step is done
    gives: tuple[str, ...] = ()      # key items received ...
    takes: tuple[str, ...] = ()      # ... and handed over
    count: int = 1                   # hunt / collect: how many
    # collect: each defeated Pokémon of `species` in a won battle on
    # `route` drops one with `chance` %.
    route: str = ""
    species: tuple[str, ...] = ()
    chance: int = 0


def hunt(species: str, count: int, where: str) -> Step:
    """Defeat `count` of `species` (anywhere; `where` says where they live)."""
    return Step("hunt", species, f"Defeat {count} {SPECIES[species].name} ({where})", count=count)


def collect(item: str, count: int, route: str, species: tuple[str, ...], chance: int, where: str) -> Step:
    """Collect `count` of `item`, dropped by `species` on `route`."""
    return Step("collect", item, f"Collect {count} {item}s ({where})", count=count, route=route,
                species=species, chance=chance)


HAND_IN = Step("hand_in", "", "Hand it in at any quest board")


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
    starts_in: str = ""              # a quest that starts by itself: only on arriving in this town
    unlock: tuple[str, int] | None = None  # (line, n): only once n of that line are defeated (recruitment)
    # Items given too: ("medicine", name, count), ("gear", item, rarity, level)
    # or ("pokemon", species, level): it joins the party (or the reserve).
    rewards: tuple[tuple, ...] = ()
    done_dialogue: tuple[Line, ...] = ()  # shown when it's done (after the last step's)
    # Starts when this key item drops: (item, route, species, chance %): in a
    # won battle on the route, each defeated Pokémon of those species drops
    # it with that chance (until it has dropped once).
    drop: tuple[str, str, tuple[str, ...], int] | None = None

    @property
    def evolves(self) -> str:
        """An evolution quest: the species it evolves ("" if it isn't one).
        It's only on offer (or drops its item) once that species is in the
        team at the level it evolves at."""
        return next((s.target for s in self.steps if s.kind == "evolve"), "")


QUESTS = {q.key: q for q in [
    Quest(
        "oaks_parcel", "Oak's Parcel",
        "The Viridian Poké Mart has a parcel for Professor Oak and needs someone to take it to Pallet Town.",
        board="viridian",
        steps=(
            Step("visit", "Poké Mart", "Pick up the parcel at the Viridian Poké Mart", town="viridian",
                 dialogue=(("Meowth", "Meowth! You came from Pallet Town? Then you know Professor Oak, meow!"),
                           ("Meowth", "His order came in. Will you take it to him?"),
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
        money=300, xp=150,
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
        money=500, xp=350,
        rewards=(("medicine", "Super Potion", 2), ("gear", None, "Common", 10)),
    ),

    # Board jobs: defeat a number of one species, or collect quest items
    # that drop on the route out of town; handed in at any board.
    Quest(
        "pest_control", "Pest Control",
        "Rattata keep chewing through the fences of Pallet Town. Thin them out on Route 1.",
        board="pallet",
        steps=(hunt("rattata", 6, "Route 1"), HAND_IN),
        money=300, xp=150,
    ),
    Quest(
        "soft_feathers", "Soft Feathers",
        "Mom wants Pidgey feathers to stuff a new pillow. Pidgey on Route 1 sometimes drop one.",
        board="pallet",
        steps=(collect("Pidgey Feather", 5, "route_1", ("pidgey",), 50, "Pidgey on Route 1"), HAND_IN),
        money=400, xp=150,
    ),
    Quest(
        "spearow_trouble", "Spearow Trouble",
        "A flock of Spearow on Route 22 pecks at anyone passing by. Show them who's boss.",
        board="viridian", requires=("oaks_parcel",),
        steps=(hunt("spearow", 4, "Route 22"), HAND_IN),
        money=450, xp=200,
    ),
    Quest(
        "nidoran_horns", "Shed Horns",
        "A Viridian collector pays well for the little horns Nidoran shed on Route 22.",
        board="viridian", requires=("oaks_parcel",),
        steps=(collect("Nidoran Horn", 6, "route_22", ("nidoran_f", "nidoran_m"), 40, "Nidoran on Route 22"),
               HAND_IN),
        money=500, xp=250,
    ),
    Quest(
        "bug_silk", "Bug Silk",
        "The Poké Mart weaves its bandanas from the silk of Caterpie and Metapod in Viridian Forest.",
        board="viridian", requires=("oaks_parcel",),
        steps=(collect("Silk Thread", 5, "viridian_forest", ("caterpie", "metapod"), 40,
                       "Caterpie and Metapod in Viridian Forest"), HAND_IN),
        money=600, xp=250,
    ),
    Quest(
        "poison_barbs", "Poison Barbs",
        "Pewter's Pokémon Center makes Antidotes from Weedle and Kakuna barbs. Bring some from Viridian Forest.",
        board="pewter",
        steps=(collect("Poison Barb", 6, "viridian_forest", ("weedle", "kakuna"), 35,
                       "Weedle and Kakuna in Viridian Forest"), HAND_IN),
        money=700, xp=500,
    ),
    Quest(
        "forest_sparks", "Sparks in the Forest",
        "Someone saw sparks between the trees of Viridian Forest. Track down the Pikachu behind them.",
        board="pewter",
        steps=(hunt("pikachu", 3, "Viridian Forest"), HAND_IN),
        money=800, xp=600,
    ),

    # Evolutions: each is unlocked by its quest (`can_evolve`); after that,
    # the line evolves by level as usual. Those not listed can't evolve yet.
    Quest(
        "evolve_metapod", "Cocoon of Steel",
        "An empty Metapod shell, hard as steel. A Caterpie strong enough (Lv7) could learn from it how to "
        "harden into a Metapod.",
        drop=("Metapod Shell", "viridian_forest", ("caterpie", "metapod"), 15),
        steps=(Step("evolve", "caterpie", "Show the Metapod Shell to a Caterpie at Lv7+ (party screen: E)",
                    takes=("Metapod Shell",)),),
        money=200, xp=100,
    ),
    Quest(
        "evolve_kakuna", "Poison Cocoon",
        "An empty Kakuna shell, still smelling of poison. A Weedle strong enough (Lv7) could learn from it how "
        "to wrap itself up as a Kakuna.",
        drop=("Kakuna Shell", "viridian_forest", ("weedle", "kakuna"), 15),
        steps=(Step("evolve", "weedle", "Show the Kakuna Shell to a Weedle at Lv7+ (party screen: E)",
                    takes=("Kakuna Shell",)),),
        money=200, xp=100,
    ),

    # Pewter City: the first gym, and the road on.
    Quest(
        "boulder_badge", "The Boulder Badge",
        "The Boulder Gang, Rock-type Pokémon led by an Onix, holds the Pewter Gym. Beat them for the Boulder "
        "Badge and the road east opens.",
        starts_in="pewter",
        steps=(Step("defeat", "pewter_gym", "Defeat the Boulder Gang at the Pewter Gym",
                    dialogue=(("Onix", "I took you for granted. As proof of your victory, here's the Boulder Badge!"),
                              ("", "You received the Boulder Badge!"),
                              ("Onix", "The road east, Route 3, is open to you. Mt. Moon lies beyond it.")),
                    gives=("Boulder Badge",)),),
        money=500, xp=400,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Rare", 14)),
    ),
    Quest(
        "to_mt_moon", "Road to Mt. Moon",
        "Route 3 runs east from Pewter City to the foot of Mt. Moon. Bands of Pokémon have claimed the road.",
        requires=("boulder_badge",),
        steps=(Step("reach", "mt_moon", "Reach Mt. Moon by Route 3 (east of Pewter City)"),),
        money=400, xp=300,
    ),
    Quest(
        "through_mt_moon", "Through Mt. Moon",
        "Mt. Moon's tunnels lead to Route 4 and on to Cerulean City. Ladders go every which way, and Team "
        "Rocket is said to be digging deep inside.",
        requires=("to_mt_moon",),
        steps=(Step("reach", "route_4", "Find the way through Mt. Moon to Route 4"),),
        money=800, xp=600,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Uncommon", 14)),
    ),
    Quest(
        "snake_charmer", "Snake Charmer",
        "Ekans on Route 3 keep frightening travelers. Drive a few of them off.",
        board="pewter", requires=("boulder_badge",),
        steps=(hunt("ekans", 5, "Route 3"), HAND_IN),
        money=500, xp=300,
    ),
    Quest(
        "puff_fluff", "Soft as Fluff",
        "A Pewter tailor wants the soft fluff Jigglypuff shed on Route 3.",
        board="pewter", requires=("boulder_badge",),
        steps=(collect("Jigglypuff Fluff", 5, "route_3", ("jigglypuff",), 40, "Jigglypuff on Route 3"), HAND_IN),
        money=600, xp=350,
    ),
]}


RECRUIT_BOARD = "recruit"  # the board of recruitment quests (in every Recruitment Center)


def _recruit_quest(r: Recruit) -> Quest:
    name = SPECIES[r.species].name
    return Quest(
        f"recruit_{r.species}", f"Recruit {name}",
        f"Mr. Mime has found a place teeming with {name}. Beat the giant one there, and it will join you.",
        board=RECRUIT_BOARD, unlock=(r.species, r.needed),
        steps=(Step("defeat", r.route_key, f"Defeat the giant {name} on the {name} Grounds"),),
        money=r.level * 25, xp=r.level * 20,
        rewards=(("pokemon", r.species, r.boss_level),),
    )


QUESTS.update({q.key: q for q in map(_recruit_quest, RECRUITS.values())})


@dataclass
class Finished:
    """A quest that was just done, and what it gave."""
    key: str
    rewards: list[Reward]
    xp: int  # XP each party member got
    level_ups: list[str] = field(default_factory=list)  # e.g. "Bulbasaur grew to Lv8!"


@dataclass
class Event:
    """Something to show after a quest event, in order."""
    dialogue: list[Line] = field(default_factory=list)
    started: list[str] = field(default_factory=list)  # quest keys
    finished: list[Finished] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.dialogue or self.started or self.finished)


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
    """Not started yet, the quests it needs are done, (recruitment) enough
    of its line defeated, and (evolution) its species at its level."""
    return (step(game, quest.key) is None and all(is_done(game, r) for r in quest.requires)
            and (not quest.unlock or game.defeated[quest.unlock[0]] >= quest.unlock[1])
            and (not quest.evolves or evolution_level(game, quest.evolves)))


def evolution_level(game, species: str) -> bool:
    """A `species` in the party or reserve has reached the level it evolves at."""
    evolution = SPECIES[species].evolution
    return bool(evolution) and any(m.species.key == species and m.level >= evolution.level
                                   for m in game.party + game.reserve)


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
    _start_automatic(game, event, town)
    return event


def won_battle(game, route: str, defeated: list[str], event: Event | None = None) -> list[tuple[str, str]]:
    """A battle on `route` was won against `defeated` (species keys): count
    them for hunts, and roll collect drops and quest items (which start
    their quest: added to `event`). Returns what happened, as (text,
    detail) rows for the battle's rewards; finished counts move their
    quest on (to handing it in)."""
    rows = []
    for quest in QUESTS.values():
        if not quest.drop or not ready(game, quest):
            continue
        item, where, species, chance = quest.drop
        if where == route and any(random.random() * 100 < chance for s in defeated if s in species):
            game.bag.key_items.append(item)
            event = event if event is not None else Event()
            event.dialogue.append(("", f"You found a {item}!"))
            _start(game, quest.key, event)
            rows.append((item, f"New quest: {quest.name}"))
    for species in defeated:  # towards recruitment
        line = line_base(species)
        game.defeated[line] += 1
        recruit = RECRUITS.get(line)
        if recruit and game.defeated[line] == recruit.needed and step(game, f"recruit_{line}") is None:
            rows.append((f"{SPECIES[line].name} can be recruited!", "Recruitment Center"))
    for quest in active(game):
        s = current(game, quest.key)
        if s.kind == "hunt":
            got = defeated.count(s.target)
            label = f"{SPECIES[s.target].name} defeated"
        elif s.kind == "collect" and s.route == route:
            got = sum(random.random() * 100 < s.chance for species in defeated if species in s.species)
            label = s.target
        else:
            continue
        if not got:
            continue
        have = min(s.count, game.quest_counts.get(quest.key, 0) + got)
        game.quest_counts[quest.key] = have
        rows.append((label, f"{quest.name} {have}/{s.count}"))
        if have >= s.count:
            _advance(game, quest, Event())  # (no dialogue for counted steps)
    return rows


def ready_to_hand_in(game) -> list[Quest]:
    return [q for q in active(game) if current(game, q.key).kind == "hand_in"]


def hand_in(game) -> Event:
    """At a quest board: finish every quest that's waiting to be handed in."""
    return _advance_where(game, lambda s: s.kind == "hand_in")


_EVOLUTION_QUESTS = {s.target: q.key for q in QUESTS.values() for s in q.steps if s.kind == "evolve"}


def evolution_unlocked(game, species: str) -> bool:
    """Whether `species` (a key) evolves by level: its evolution quest is done."""
    key = _EVOLUTION_QUESTS.get(species)
    return bool(key) and is_done(game, key)


def can_evolve(game, monster: Monster) -> bool:
    """`monster` has the level to evolve, and its evolution is unlocked or its
    quest is at the step of evolving it."""
    key = _EVOLUTION_QUESTS.get(monster.species.key)
    s = key and current(game, key)
    return monster.can_evolve and (evolution_unlocked(game, monster.species.key)
                                   or bool(s and s.kind == "evolve" and s.target == monster.species.key))


def item_evolves(game, item: str, monster: Monster) -> bool:
    """Whether key item `item` (an evolution quest's drop) evolves `monster`
    now: its quest is at the step of evolving that species, and it has the level."""
    quest = next((q for q in QUESTS.values() if q.drop and q.drop[0] == item), None)
    s = quest and current(game, quest.key)
    return bool(s and s.kind == "evolve" and s.target == monster.species.key and monster.can_evolve)


def evolution_target(item: str) -> str:
    """The species key an evolution item works on ("" if it isn't one)."""
    quest = next((q for q in QUESTS.values() if q.drop and q.drop[0] == item), None)
    return next((s.target for s in quest.steps if s.kind == "evolve"), "") if quest else ""


def evolve(game, monster: Monster) -> Event:
    """`monster` evolves (outside battle, from the party screen); this moves
    its evolution quest on if it's at that step."""
    species = monster.species.key
    monster.evolve()
    return _advance_where(game, lambda s: s.kind == "evolve" and s.target == species)


def step_text(game, quest: Quest, i: int) -> str:
    """Step `i`'s objective, with the count so far if it's the current counted one."""
    s = quest.steps[i]
    if s.kind in ("hunt", "collect") and step(game, quest.key) == i:
        return f"{s.text}: {game.quest_counts.get(quest.key, 0)}/{s.count}"
    return s.text


def open_for(game, needs: tuple[str, str] | None) -> bool:
    """Whether a (quest, "started"/"done"/"not_done") condition holds
    (None: always)."""
    if not needs:
        return True
    key, what = needs
    if what == "not_done":
        return not is_done(game, key)
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
    game.quest_counts.pop(quest.key, None)
    if is_done(game, quest.key):
        event.dialogue += quest.done_dialogue
        done = Finished(quest.key, [Reward(money=quest.money)] + [_reward(r) for r in quest.rewards],
                        quest.xp * DEV.xp_multiplier)
        for r in done.rewards:
            if r.pokemon:
                r.joined = game.add_member(r.pokemon)
            else:
                r.give(game.bag)
        _give_xp(game, done)
        event.finished.append(done)
        _start_automatic(game, event)


def _give_xp(game, done: Finished) -> None:
    """Every party member gets the quest's XP, leveling up as in battle
    (evolving waits for its next level up in a battle)."""
    xp = done.xp
    for m in game.party:
        if m.level >= MAX_LEVEL:
            continue
        start = m.level
        m.xp += xp
        while m.can_level_up:
            m.level_up()
        if m.level > start:
            done.level_ups.append(f"{m.name} grew to Lv{m.level}!")


def reward_text(quest: Quest) -> str:
    """What it pays, e.g. "₽300, 200 XP, 5 Potions, Uncommon gear (Lv9)"."""
    parts = [money_text(quest.money), f"{quest.xp} XP"]
    for spec in quest.rewards:
        if spec[0] == "medicine":
            parts.append(f"{spec[2]} {spec[1]}{'s' if spec[2] > 1 else ''}")
        elif spec[0] == "pokemon":
            parts.append(f"{SPECIES[spec[1]].name} (Lv{spec[2]}) joins you")
        else:
            parts.append(f"{spec[2]} {spec[1] or 'gear'} (Lv{spec[3]})")
    return ", ".join(parts)


def _reward(spec: tuple) -> Reward:
    """A quest reward: ("medicine", name, count) or ("gear", item or None for
    any but a berry, rarity, item level)."""
    if spec[0] == "medicine":
        return Reward(medicine=spec[1], count=spec[2])
    if spec[0] == "pokemon":
        return Reward(pokemon=Monster.create(spec[1], spec[2]))
    item = spec[1] or random.choice([name for name, i in ITEMS.items() if i.slot != "berry"])
    return Reward(gear=Gear.roll(item, spec[2], level=spec[3]))


def _start_automatic(game, event: Event, town: str = "") -> None:
    """Start the quests without a board that are ready (those that start in
    a town only when arriving in `town`)."""
    for quest in QUESTS.values():
        if not quest.board and not quest.drop and ready(game, quest) and quest.starts_in in ("", town):
            _start(game, quest.key, event)
