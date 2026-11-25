"""Quests: the rules that run them (the quests themselves, and what steps
and quests are, are in quest_data.py).

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
from ..mechanics.items import ITEMS, RIBBON, STACKING, Gear, money_text
from ..mechanics.loot import Reward
from ..mechanics.pokemon import MAX_LEVEL, SPECIES, Monster, line_base
from .instance import RECRUITS, ROUTES, from_route
from .progress import MAX_PARTY
from .quest_data import QUESTS, Line, Quest, Step


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


def active_limit(game) -> int:
    """The party's size, all of whom fight: `Game.slots` (1, and one more
    for each Teamwork Ribbon used)."""
    return min(MAX_PARTY, game.slots)


def fit_party(game) -> None:
    """Keep the party at most `active_limit`: extra members wait in the
    reserve (e.g. from an older save). New places stay empty until the
    player fills them (Mr. Mime, at a Recruitment Center)."""
    limit = active_limit(game)
    while len(game.party) > limit:
        game.reserve.insert(0, game.party.pop())


def smith_open(game) -> bool:
    """Whether the smith salvages and enhances gear (his hammer is made)."""
    return is_done(game, "smith_hammer")


def use_ribbon(game) -> str:
    """Use a Teamwork Ribbon from the bag: one more place in the party.
    Returns what to say."""
    game.bag.key_items.remove(RIBBON)
    game.slots += 1
    n = active_limit(game)
    words = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}.get(n, str(n))
    text = f"{words} Pokémon can now fight at your side!"
    if game.reserve:
        text += " Mr. Mime, at any Recruitment Center, can bring one from your reserve."
    return text


def fighters(game) -> list[Monster]:
    """Who fights the next battle: the party members still standing."""
    return [m for m in game.party if m.alive][:active_limit(game)]


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
    return (step(game, quest.key) is None and all(required(game, r) for r in quest.requires)
            and (not quest.needs or open_for(game, quest.needs))
            and (not quest.unlock or game.defeated[quest.unlock[0]] >= quest.unlock[1])
            and (not quest.evolves or evolution_level(game, quest.evolves))
            and not any(is_active(game, k) for k in quest.excludes)
            and (not quest.needs_species or any(m.species.key in quest.needs_species
                                                for m in game.party + game.reserve)))


def required(game, need: str | tuple[str, ...]) -> bool:
    """One of `Quest.requires`: that quest done (a tuple: any one of them)."""
    return any(is_done(game, k) for k in need) if isinstance(need, tuple) else is_done(game, need)


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


def talk(game, folk: str) -> Event:
    """The player talked to townsfolk `folk`: the quest steps that wait for
    that, or else a quest they give (its offer, and it starts)."""
    for quest in active(game):  # a step that wants an item the player hasn't got yet
        s = current(game, quest.key)
        if s.kind == "talk" and folk in s.targets and s.takes and not all(i in game.bag.key_items for i in s.takes):
            return Event(dialogue=list(s.waiting))
    for quest in active(game):  # (which of a step's alternatives it was: either Snorlax)
        s = current(game, quest.key)
        if s.kind == "talk" and s.alt and folk in s.targets:
            for other in s.targets:
                game.trainers.discard(_choice_key(quest.key, other))
            game.trainers.add(_choice_key(quest.key, folk))
    event = _advance_where(game, lambda s: s.kind == "talk" and folk in s.targets)
    if not event:
        for quest in QUESTS.values():
            if quest.giver == folk and ready(game, quest):
                event.dialogue += quest.offer
                _start(game, quest.key, event)
                break
    return event


def folk_quests(game, folk: str) -> list[Quest]:
    """The quests townsfolk `folk` has something for: ones they give that
    are ready, and active ones waiting to talk to them."""
    return [q for q in QUESTS.values()
            if (q.giver == folk and ready(game, q))
            or (is_active(game, q.key) and (s := current(game, q.key)).kind == "talk" and folk in s.targets
                and all(i in game.bag.key_items for i in s.takes))]  # (not while what it wants is missing)


def visit(game, town: str, building: str) -> Event:
    """The player pressed Up at `building` in `town` (a step there that wants
    key items the player hasn't got yet says its `waiting` lines instead)."""
    for quest in active(game):
        s = current(game, quest.key)
        if (s.kind == "visit" and s.town == town and s.target == building and s.takes
                and not all(i in game.bag.key_items for i in s.takes)):
            return Event(dialogue=list(s.waiting))
    return _advance_where(game, lambda s: s.kind == "visit" and s.town == town and s.target == building)


def early_text(game, town: str, building: str) -> str:
    """What Up at `building` says while an active quest's later step is a
    visit there (`Step.before`), or ""."""
    for quest in active(game):
        later = quest.steps[step(game, quest.key) + 1:]
        hint = next((s.before for s in later if s.kind == "visit" and s.town == town and s.target == building
                     and s.before), "")
        if hint:
            return hint
    return ""


def defeat(game, route: str) -> Event:
    """The player beat `route`'s boss, or the map trainer with that key (the
    rival on Nugget Bridge)."""
    return _advance_where(game, lambda s: s.kind == "defeat" and route in s.targets)


def trainer_beaten(game, key: str) -> bool:
    """Map trainer `key` is beaten for good, or a quest that needed beating
    it is done (saves from when the rival was Nugget Bridge's end boss)."""
    return key in game.trainers or any(
        is_done(game, q.key) for q in QUESTS.values() if any(s.kind == "defeat" and key in s.targets for s in q.steps))


def reach(game, town: str) -> Event:
    """The player arrived in `town` (also starts quests that start by themselves)."""
    event = _advance_where(game, lambda s: s.kind == "reach" and s.target == town)
    _start_automatic(game, event, town)
    return event


def won_battle(game, route: str, defeated: list[str], event: Event | None = None,
               recruits: bool = True) -> list[tuple[str, str]]:
    """A battle on `route` was won against `defeated` (species keys): count
    them for hunts and (`recruits`: an ordinary wild battle, not a
    trainer's or a boss's) recruitment, and roll collect drops and quest
    items (which start their quest: added to `event`). Returns what happened, as (text,
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
    for species in defeated if recruits else ():  # towards recruitment (wild groups only)
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
        elif s.kind == "collect" and (s.route == route or from_route(s.route, route)):
            got = sum(random.random() * 100 < s.chance for species in defeated if species in s.species)
            label = s.target
        elif (s.kind == "lead_wins" and recruits and (s.route == route or from_route(s.route, route))
              and game.party and game.party[0].species.key in s.species):  # (a wild battle, the bird leading)
            got = 1
            label = f"Won with {game.party[0].name} leading"
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
    if s.kind in ("hunt", "collect", "lead_wins") and step(game, quest.key) == i:
        return f"{s.text}: {game.quest_counts.get(quest.key, 0)}/{s.count}"
    return s.text


def boss_wanted(game, route: str) -> bool:
    """Whether an active quest is at the step of defeating `route`'s boss
    (then it's there as a boss again, even if it was beaten before)."""
    return any((s := current(game, q.key)) and s.kind == "defeat" and route in s.targets for q in active(game))


def can_fly(game) -> str:
    """"" if the party can Fly now (the Town Map), else why not."""
    if not is_done(game, "learn_to_fly"):
        return "You don't know how to Fly yet."
    if not any("flying" in m.species.types for m in game.party):
        return "Nobody in the party can carry you: you need a Flying Pokémon."
    return ""


def gone(game, after: str) -> bool:
    """A townsfolk's `Folk.gone_after` holds: that quest is done, or (a
    "boss:<route>" key) that boss is beaten (a Snorlax woken and calmed down)."""
    return after in game.trainers if after.startswith("boss:") else is_done(game, after)


def _choice_key(quest: str, folk: str) -> str:
    return f"chose:{quest}={folk}"


def chosen(game, quest: str, folk: str) -> bool:
    """Whether `folk` may send the player to `quest`'s current defeat step:
    no alternative was picked by an earlier talk step, or `folk` was."""
    picked = [k for k in game.trainers if k.startswith(f"chose:{quest}=")]
    return not picked or _choice_key(quest, folk) in picked


def blocked_text(game, route) -> str:
    """What a shut `route`'s doorway (or building) says."""
    if route.blocked_done and route.needs and is_done(game, route.needs[0]):
        return route.blocked_done
    return route.blocked


def open_for(game, needs: tuple[str, str] | None) -> bool:
    """Whether a (quest, "started"/"active"/"done"/"not_done") condition,
    or a (key, "beaten") one (that key is in `Game.trainers`: a boss beaten,
    e.g. "boss:snorlax_wakes"),
    holds ("started": started or done; "active": started and not done yet;
    None: always)."""
    if not needs or DEV.open_doors:
        return True
    key, what = needs
    if what == "beaten":  # a boss beaten for good ("boss:<route>", in Game.trainers)
        return key in game.trainers
    if what == "not_done":
        return not is_done(game, key)
    if what == "active":
        return is_active(game, key)
    return is_done(game, key) if what == "done" else step(game, key) is not None


# --- dev mode: replaying quests (scenes/dev_menu.QuestTool) -----------------

def _undo_step(game, s: Step) -> None:
    """Take back what a step did: the key items it gave (and gives back
    those it took), and the bosses and trainers it beat."""
    for item in s.gives:
        if item in game.bag.key_items:
            game.bag.key_items.remove(item)
    game.bag.key_items += [i for i in s.takes if i not in game.bag.key_items or i in STACKING]
    if s.kind == "defeat":
        for target in s.targets:
            game.trainers.discard(target)
            route = ROUTES.get(target)
            if route:
                game.trainers.discard(route.boss_key)
                game.trainers.discard(f"boss:{target}")


def reset(game, key: str) -> None:
    """`key` back to not started, as if it had never been: what its steps
    did is undone (`_undo_step`), its choices forgotten. It's offered again
    as it was the first time (its board, giver, or by itself). Rewards
    already given stay."""
    quest = QUESTS[key]
    at = step(game, key) or 0
    for s in reversed(quest.steps[:at]):
        _undo_step(game, s)
    game.quests.pop(key, None)
    game.quest_counts.pop(key, None)
    game.trainers -= {t for t in game.trainers if t.startswith(_choice_key(key, ""))}
    if quest.drop and quest.drop[0] in game.bag.key_items:
        game.bag.key_items.remove(quest.drop[0])


def restart(game, key: str) -> Event:
    """`key` reset, then started again at its first step."""
    reset(game, key)
    return accept(game, key)


def step_back(game, key: str) -> None:
    """`key` back one step (a done quest: back to its last step), undoing it."""
    at = step(game, key)
    if not at:
        return
    _undo_step(game, QUESTS[key].steps[at - 1])
    game.quests[key] = at - 1
    game.quest_counts.pop(key, None)


def step_forward(game, key: str) -> Event:
    """`key`'s current step done (started first, if it wasn't): what it
    gives, and the rewards if that finishes it."""
    event = Event()
    if step(game, key) is None:
        _start(game, key, event)
    elif is_active(game, key):
        _advance(game, QUESTS[key], event)
    return event


# --- inside ------------------------------------------------------------------

def _start(game, key: str, event: Event) -> None:
    game.quests[key] = 0
    event.started.append(key)
    _skip_beaten(game, QUESTS[key], event)


def _beaten_already(game, s: Step | None) -> bool:
    """A step to beat a map trainer (fought once: the rival on Nugget
    Bridge) that's already beaten for good, e.g. fought before the quest
    asked for it (in dev mode). It could never be done otherwise."""
    return bool(s) and s.kind == "defeat" and s.target in game.trainers


def _skip_beaten(game, quest: Quest, event: Event) -> None:
    if is_active(game, quest.key) and _beaten_already(game, current(game, quest.key)):
        _advance(game, quest, event)


def catch_up(game) -> Event:
    """On loading a save: the active quests' steps that were done before
    they were asked for (see `_beaten_already`) complete now."""
    event = Event()
    for quest in active(game):
        _skip_beaten(game, quest, event)
    return event


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
    game.bag.key_items += [i for i in s.gives if i not in game.bag.key_items or i in STACKING]
    game.quests[quest.key] += 1
    game.quest_counts.pop(quest.key, None)
    if is_done(game, quest.key):
        event.dialogue += quest.done_dialogue
        done = Finished(quest.key, [Reward(money=quest.money)] + [_reward(r) for r in quest.rewards],
                        quest.xp * DEV.xp_multiplier)
        for r in done.rewards:
            if r.pokemon:
                r.joined = game.add_member(r.pokemon, active_limit(game))
            else:
                r.give(game.bag)
        _give_xp(game, done)
        event.finished.append(done)
        _start_automatic(game, event)
    else:
        _skip_beaten(game, quest, event)  # (its next step may be done already)


def _give_xp(game, done: Finished) -> None:
    """Every party member gets the quest's XP, leveling up as in battle
    (evolving waits for its next level up in a battle)."""
    xp = done.xp
    for m in game.party:
        if m.level >= MAX_LEVEL:
            continue
        start, learned = m.level, []
        m.xp += xp
        while m.can_level_up:
            learned += m.level_up()
        if m.level > start:
            done.level_ups.append(f"{m.name} grew to Lv{m.level}!")
        done.level_ups += [f"{m.name} learned {name}!" for name in learned]


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
    item = spec[1] or random.choice([name for name, i in ITEMS.items() if i.slot != "berry" and i.drops_at(spec[2])])
    return Reward(gear=Gear.roll(item, spec[2], level=spec[3]))


def _start_automatic(game, event: Event, town: str = "") -> None:
    """Start the quests without a board that are ready (those that start in
    a town only when arriving in `town`)."""
    for quest in QUESTS.values():
        if (not quest.board and not quest.drop and not quest.giver and ready(game, quest)
                and quest.starts_in in ("", town)):
            _start(game, quest.key, event)
