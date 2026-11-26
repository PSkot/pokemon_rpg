"""Swaps: the trade evolutions (Kadabra, Machoke, Graveler, Haunter), done
as a swap with townsfolk instead of a trade (docs/quests.md, "Swaps").

A swap quest's first step (`Step.swap` "out") sends the player's Pokémon
of `Swap.mine` to the townsfolk `Swap.partner`, who lends theirs
(`Swap.loan`) in its place: the borrowed one takes its spot in the party
(or at the party's front, if the player's was in the reserve), at the
level of the player's strongest (`Monster.loan` marks it). While it's away
the player's Pokémon stands in the partner's spot in town (`stand_in`), and
can't be used. The quest's trial is fought by the borrowed Pokémon alone;
then the last step (`Step.swap` "back") swaps back: the player's comes
home evolved (`Swap.into`), healed, with everything it wore; whatever the
player put on the borrowed one goes back to the bag.

Once a swap quest is done, its partner swaps another of that species any
time, straight away (`repeat`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..mechanics.pokemon import SPECIES, Monster
from .towns import Folk

Line = tuple[str, str]


@dataclass(frozen=True)
class Swap:
    quest: str     # the quest key (also `Monster.loan` and the key in `Game.away`)
    mine: str      # the player's species that goes
    into: str      # ... and what it comes back as
    partner: str   # the townsfolk's key
    loan: str      # the species they lend
    stay: tuple[str, ...]  # what the player's Pokémon "says" in the partner's spot while it's away ("{name}")


SWAPS = {s.quest: s for s in [
    Swap("swap_kadabra", "kadabra", "alakazam", "saffron_machoke", "machoke", (
        "Your {name} floats cross-legged in front of the Dojo, bending a spoon while the black belts do push-ups.",
        "Your {name} is watching the black belts spar very closely. It seems to be taking notes. In its head.",
    )),
]}
BY_PARTNER = {s.partner: s for s in SWAPS.values()}


def _team(game) -> list[Monster]:
    return game.party + game.reserve


def candidate(game, swap: Swap) -> Monster | None:
    """The player's Pokémon that would go: the first of `swap.mine` in the
    party, else in the reserve."""
    return next((m for m in _team(game) if m.species.key == swap.mine and not m.loan), None)


def loaned(game, swap: Swap) -> Monster | None:
    return next((m for m in _team(game) if m.loan == swap.quest), None)


def away(game, swap: Swap) -> Monster | None:
    return game.away.get(swap.quest)


def out(game, swap: Swap) -> list[Line]:
    """Send the player's Pokémon to the partner; theirs joins on loan."""
    mine = candidate(game, swap)
    if not mine:
        return []
    level = max(m.level for m in _team(game))
    loan = Monster.create(swap.loan, level, talents="all")
    loan.loan = swap.quest
    if mine in game.party:
        game.party[game.party.index(mine)] = loan
    else:  # (from the reserve: the borrowed one goes to the party's front, ready for the trial)
        game.reserve.remove(mine)
        game.party.insert(0, loan)
        from .quests import fit_party  # (quests.py imports this module)
        fit_party(game)
    game.away[swap.quest] = mine
    return [("", f"Your {mine.name} goes with {SPECIES[swap.loan].name}'s friends to train."),
            ("", f"{loan.name} (Lv{loan.level}) joined your party, on loan!")]


def back(game, swap: Swap, evolve: bool = True) -> list[Line]:
    """Swap back: the borrowed one leaves (anything the player put on it
    goes back to the bag), the player's comes home (evolved, if `evolve`)
    in its place, healed, wearing what it wore."""
    mine = game.away.pop(swap.quest, None)
    loan = loaned(game, swap)
    lines = []
    if loan and loan.gear:
        for slot in list(loan.gear):
            game.bag.unequip(loan, slot)
        lines.append(("", f"(What you gave {loan.name} to wear went back to the bag.)"))
    if mine is None:
        if loan:
            _remove(game, loan)
        return lines
    before = mine.name
    if evolve:
        mine.evolve(swap.into)
    mine.hp, mine.status, mine.sleep_rounds = mine.max_hp, "", 0
    if loan:
        team = game.party if loan in game.party else game.reserve
        team[team.index(loan)] = mine
    else:
        game.add_member(mine, len(game.party) + 1)
    said = f"Your {before} is back... as {mine.name}!" if evolve and before != mine.name else f"Your {before} is back!"
    return lines + [("", said)]


def _remove(game, monster: Monster) -> None:
    for team in (game.party, game.reserve):
        if monster in team:
            team.remove(monster)


def repeat(game, folk: str) -> list[Line]:
    """After its quest: the partner swaps another of the player's (party
    only) straight away, and it comes back evolved."""
    from .quests import is_done  # (quests.py imports this module)
    swap = BY_PARTNER.get(folk)
    if not swap or not is_done(game, swap.quest):
        return []
    mine = next((m for m in game.party if m.species.key == swap.mine and not m.loan), None)
    if not mine:
        return []
    before = mine.name
    mine.evolve(swap.into)
    return [(SPECIES[swap.loan].name, f"Another {before}? OSS! A few rounds with my friends, and..."),
            ("", f"Your {before} came back as {mine.name}!")]


def stand_in(game, folk: Folk) -> Folk:
    """`folk`, or the player's Pokémon in its place while it's away with them."""
    swap = BY_PARTNER.get(folk.key)
    mine = swap and away(game, swap)
    if not mine:
        return folk
    return replace(folk, name=f"Your {mine.name}", species=mine.species.key, npc="",
                   lines=tuple(line.format(name=mine.name) for line in swap.stay))
