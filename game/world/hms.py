"""Hidden machines used from the bag (Key items): HM03 Surf.

Using one teaches its move (`talent_core.HM_MOVES`) to every Pokémon of
the player's of its type, in the party, the reserve or away on loan, and
to any that join later (`Game.add_member`); it stays usable from then on
(`Game.hms`). The move is equipped if there's a free slot (else it waits
in the moves panel, like any move learned).

Surf: Water Pokémon learn Surf, and water maps (`Theme.sea`) can be
crossed: on the water the party's first Water Pokémon carries the player
(it shows instead of the lead, `MapScene.update`). Without a Water
Pokémon in the party, there's no going on the water.
"""

from ..mechanics.pokemon import Monster
from ..mechanics.talents import MAX_EQUIPPED

SURF_ITEM = "HM03 Surf"
# HM -> (its move's key, the type that learns it)
HMS = {SURF_ITEM: ("surf", "water")}


def _owned(game) -> list[Monster]:
    return game.party + game.reserve + list(game.away.values())


def teach(game, monster: Monster) -> bool:
    """Teach `monster` the HM moves in use that its type learns; whether
    it learned one."""
    learned = False
    for move, kind in HMS.values():
        if move in game.hms and kind in monster.species.types and move not in monster.hms:
            monster.hms.append(move)
            if len(monster.equipped) < MAX_EQUIPPED:
                monster.equipped.append(move)
            learned = True
    return learned


def teach_all(game) -> None:
    """Teach every Pokémon of the player's what it should know (after
    loading a save, or evolving into a new type)."""
    for m in _owned(game):
        teach(game, m)


def surfer(game) -> Monster | None:
    """The Pokémon that carries the player on the water: the party's first
    Water Pokémon, or None."""
    return next((m for m in game.party if "water" in m.species.types), None)


def can_surf(game) -> str:
    """"" if the party can go on the water now, else why not."""
    if "surf" not in game.hms:
        if SURF_ITEM in game.bag.key_items:
            return "The water is deep. (Use HM03 Surf from the bag: Key items.)"
        return "The water is deep. A Pokémon could carry you across, if it knew how."
    if not surfer(game):
        return "The water is deep. You need a Water Pokémon in your team to Surf."
    return ""


def use(game, item: str) -> str:
    """Use HM `item` from the bag; what happens."""
    move, kind = HMS[item]
    if move in game.hms:
        return "Your Water Pokémon already know Surf."
    if not any(kind in m.species.types for m in game.party):
        return "Nobody in your team could learn it: you need a Water Pokémon in your team."
    game.hms.add(move)
    learned = [m for m in _owned(game) if teach(game, m)]
    names = ", ".join(m.name for m in learned)
    full = "" if all(move in m.equipped for m in learned) else " (Full moves: equip it on the talent screen, M.)"
    return f"{names} learned Surf! Your Water Pokémon can now carry you across the water.{full}"
