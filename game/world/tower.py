"""The Battle Tower (Celadon City's west end, open once the Rainbow Badge is
won): 25 floors of wave battles, each floor a short hall up to an arena,
fought like a gym (`Route.waves`, then its master's band), getting harder
and grander the higher it goes.

- Every run starts on floor 1. There's no healing between floors (or
  waves), and losing ends the run with nothing.
- After each cleared floor, the player goes on or stops; stopping (or
  clearing the last floor open) gives the run's chest (`chest`): gems,
  medicine and gear for the floors cleared.
- Floors open five at a time (`GATES`): 1-5 with the tower (the Rainbow
  Badge, the 4th), 6-10 at 6 badges, 11-15 at 7, 16-20 at 8 (in any
  order), and 21-25 once the player is Champion.
- Its battles give XP (as trainers'), no drops or prize money.
- Enemies' level climbs from Lv35 (floor 1) to Lv68 (floor 25), each tier
  starting about at the party's level when it opens (`TIER_LEVELS`); with each
  tier of five floors they come in more waves and bigger bands, wear more
  and better gear and have more talents. Every fifth floor's master is a
  giant (`BOSS_FLOORS`), the 25th a Dragonite.
- The gems (`GEMS`: Quartz from floor 1, Jade from 6, Sapphire from 11,
  Ruby from 16, Diamond from 21) buy gear and special Pokémon from Mew in the lobby
  (`GEM_GEAR`, `GEM_POKEMON`; scenes/battle_tower.py).
"""

from __future__ import annotations

import random
from collections import Counter

from ..mechanics.items import ITEMS, Gear
from ..mechanics.loot import Reward
from ..mechanics.pokemon import Monster
from .instance import ROUTES, Route, Wave
from .themes import TOWER_THEMES

FLOORS = 25
TIER = 5  # floors in a tier
GEMS = ("Quartz", "Jade", "Sapphire", "Ruby", "Diamond")  # by tier: floors 1-5, 6-10, ..., 21-25
TIER_NAMES = ("Marble Halls", "Sky Gardens", "Storm Spire", "Celestial Summit", "Eclipse Throne")
LOBBY_TOWN = "celadon_west"  # where the tower stands (and a run's chest is claimed)
OPENS_AFTER = "rainbow_badge"  # the quest that opens it (the Celadon Gym, coming next)
# The gym badges' quests (some still to come) and the League's.
BADGES = ("boulder_badge", "cascade_badge", "thunder_badge", "rainbow_badge", "soul_badge", "marsh_badge",
          "volcano_badge", "earth_badge")
LEAGUE = "pokemon_league"
# What opens each tier's floors: badges won (any of them), or "league".
GATES = (4, 6, 7, 8, "league")
# Each tier's enemy levels (first floor, last floor): about the party's
# expected level when it opens (Lv38 at 4 badges, 48 at 6, 52 at 7, 56 at
# 8, 63 as Champion), climbing to a few above.
TIER_LEVELS = ((35, 40), (47, 51), (52, 56), (57, 61), (63, 68))

# What each tier's bands are made of: strong Pokémon, the strongest at the top.
POOLS = (
    ("pidgeot", "raticate", "fearow", "arbok", "sandslash", "nidorina", "nidorino", "golbat", "persian", "primeape",
     "machoke", "graveler", "magneton", "electrode", "golduck", "seaking", "kadabra", "venomoth", "gloom",
     "weepinbell", "parasect", "raichu", "dugtrio", "hypno"),
    ("arcanine", "nidoking", "nidoqueen", "vileplume", "victreebel", "tentacruel", "cloyster", "seadra", "wigglytuff",
     "clefable", "starmie", "magneton", "haunter", "dragonair", "rhyhorn", "exeggcute", "kangaskhan", "tauros",
     "scyther", "pinsir", "machoke", "golbat"),
    ("alakazam", "golem", "machamp", "gengar", "gyarados", "exeggutor", "rhydon", "scyther", "pinsir", "kangaskhan",
     "tauros", "jynx", "magmar", "electabuzz", "arcanine", "dragonair", "cloyster", "starmie"),
    ("aerodactyl", "lapras", "gyarados", "charizard", "venusaur", "blastoise", "alakazam", "gengar", "golem",
     "machamp", "arcanine", "exeggutor", "rhydon", "jynx", "electabuzz", "magmar", "pidgeot", "dragonair"),
    ("dragonite", "aerodactyl", "lapras", "gyarados", "charizard", "venusaur", "blastoise", "alakazam", "gengar",
     "golem", "machamp", "arcanine", "exeggutor", "rhydon", "starmie", "cloyster", "kangaskhan", "tauros"),
)
# Every fifth floor's master: a giant, leading the tier's strongest.
BOSS_FLOORS = {5: "nidoking", 10: "gengar", 15: "gyarados", 20: "aerodactyl", 25: "dragonite"}
WAVES = (2, 3, 3, 4, 4)     # waves before the master's band, by tier
BAND = (3, 3, 4, 4, 5)      # Pokémon in a band, by tier (a master's band: one more)
# The gear the tower's Pokémon wear: rarities and pieces (each, and the master), by tier.
WORN = ((("Common", 3), ("Uncommon", 2)), (("Uncommon", 3), ("Rare", 1)), (("Uncommon", 1), ("Rare", 3), ("Epic", 1)),
        (("Rare", 2), ("Epic", 3)), (("Rare", 1), ("Epic", 5)))
WORN_PIECES = (1, 1, 2, 2, 3)
TALENTS = ("half", "half", "all", "all", "all")
# A chest's gear: rarities by the tier of the deepest floor cleared (Epic at most).
CHEST_RARITIES = ((("Uncommon", 3), ("Rare", 1)), (("Uncommon", 1), ("Rare", 3)), (("Rare", 3), ("Epic", 1)),
                  (("Rare", 1), ("Epic", 3)), (("Epic", 1),))
MAX_ITEM_LEVEL = 60

# Mew's gem exchange. Gear: (gem, rarity or rarities, item level) for 12 of
# the gem, in a slot the player picks; Ruby's has a 60% chance of a special
# effect (rather than Epic's 20%), Diamond's always has one and its best rolls.
GEM_PRICE = 12
GEM_GEAR = (("Quartz", ("Uncommon",), 40), ("Jade", ("Rare",), 47), ("Sapphire", ("Rare", "Epic"), 55),
            ("Ruby", ("Epic",), 60), ("Diamond", ("Epic",), 60))
RUBY_EFFECT = 60
# Special Pokémon, each once: (species, level, gem, price).
GEM_POKEMON = (("dratini", 30, "Jade", 20), ("chansey", 35, "Sapphire", 20), ("lapras", 40, "Ruby", 25),
               ("aerodactyl", 50, "Diamond", 25))


def tier(floor: int) -> int:
    return min(len(TIER_NAMES) - 1, (floor - 1) // TIER)


def floor_level(floor: int) -> int:
    """Its enemies' level: each tier from its first floor's to its last's
    (`TIER_LEVELS`): Lv35 on floor 1 up to Lv68 on floor 25."""
    low, high = TIER_LEVELS[tier(floor)]
    return low + round(((floor - 1) % TIER) * (high - low) / (TIER - 1))


def badges(game) -> int:
    from . import quests  # (quests imports the routes, which import this)
    return sum(1 for key in BADGES if key in quests.QUESTS and quests.is_done(game, key))


def tier_open(game, t: int) -> bool:
    """Whether tier `t`'s floors are open (dev mode: all)."""
    from ..dev import DEV
    from . import quests
    gate = GATES[t]
    if DEV.enabled:
        return True
    if gate == "league":
        return LEAGUE in quests.QUESTS and quests.is_done(game, LEAGUE)
    return badges(game) >= gate


def top_floor(game) -> int:
    """The highest floor open to the player."""
    t = 0
    while t + 1 < len(GATES) and tier_open(game, t + 1):
        t += 1
    return (t + 1) * TIER


def gate_text(t: int) -> str:
    """What opens tier `t`."""
    gate = GATES[t]
    return "once you're the Champion" if gate == "league" else f"once you have {gate} badges"


def floor_key(floor: int) -> str:
    return f"tower_{floor}"


def floor_of(route_key: str) -> int:
    """The floor a tower route is (0 if it isn't one)."""
    return int(route_key[len("tower_"):]) if route_key.startswith("tower_") else 0


def _band(rng: random.Random, t: int, level: int, size: int) -> tuple[tuple[str, int], ...]:
    return tuple((rng.choice(POOLS[t]), level + rng.choice((-1, 0, 0))) for _ in range(size))


def _floor(floor: int) -> Route:
    """Floor `floor`'s route: the same bands every run (it's a designed tower)."""
    t, level = tier(floor), floor_level(floor)
    rng = random.Random(floor * 7919)
    waves = tuple(Wave(f"Floor {floor} Challengers", _band(rng, t, level - 1, BAND[t]), 0) for _ in range(WAVES[t]))
    leader = BOSS_FLOORS.get(floor)
    if leader:  # a giant master, with the tier's strongest
        master = ((leader, level + 2),) + _band(rng, t, level, BAND[t])
    else:
        master = _band(rng, t, level + 1, BAND[t] + 1)
    name = f"{TIER_NAMES[t]}: Floor {floor}"
    return Route(floor_key(floor), name, TOWER_THEMES[t], maps=1, towns=(LOBBY_TOWN, LOBBY_TOWN), boss=True,
                 boss_group=master, boss_scale=2 if leader else 1, trainer=f"Floor {floor} Master", boss_chest="",
                 waves=waves, wave_team=6, wild=False, cols=44, loot=WORN[t], boss_loot=WORN[t], tower=floor)


TOWER_ROUTES = {r.key: r for r in map(_floor, range(1, FLOORS + 1))}
ROUTES.update(TOWER_ROUTES)


def dress_up(monster: Monster, floor: int, master: bool) -> None:
    """Gear for one of the tower's Pokémon (by its floor's tier)."""
    from ..mechanics.loot import dress  # (loot imports items, like this)
    t = tier(floor)
    dress(monster, WORN[t], WORN_PIECES[t] + (1 if master else 0))


def chest(floor: int, rng: random.Random | None = None) -> tuple[list[Reward], Counter]:
    """A run's chest for clearing floors 1..`floor`: (items, gems). Gems:
    2 of each cleared floor's tier's gem, 3 more for every fifth floor.
    Medicine and gear grow with the deepest floor; gear is at that floor's
    level (Lv60 at most) and tier's rarities (Epic at most)."""
    rng = rng or random.Random()
    gems = Counter()
    for f in range(1, floor + 1):
        gems[GEMS[tier(f)]] += 2 + (3 if f % TIER == 0 else 0)
    rewards = [Reward(medicine="Hyper Potion", count=1 + floor // 4)]
    if floor >= 5:
        rewards.append(Reward(medicine="Revive", count=floor // 5))
    if floor >= 8:
        rewards.append(Reward(medicine="Max Potion", count=floor // 8))
    if floor >= 12:
        rewards.append(Reward(medicine="Full Restore", count=floor // 12))
    rarities, level = CHEST_RARITIES[tier(floor)], min(MAX_ITEM_LEVEL, floor_level(floor))
    for _ in range(1 + floor // 5):
        rarity = rng.choices([r for r, _ in rarities], weights=[w for _, w in rarities])[0]
        item = rng.choice([n for n, i in ITEMS.items() if i.drops_at(rarity)])
        rewards.append(Reward(gear=Gear.roll(item, rarity, rng, level=level)))
    return rewards, gems


def gem_gear(tier_: int, slot: str, rng: random.Random | None = None) -> Gear:
    """A piece from Mew's exchange: `tier_`'s gear, in `slot`."""
    rng = rng or random.Random()
    _, rarities, level = GEM_GEAR[tier_]
    rarity = rng.choice(rarities)
    items = [n for n, i in ITEMS.items() if i.slot == slot and i.drops_at(rarity)]
    item = rng.choice(items or [n for n, i in ITEMS.items() if i.slot == slot])
    effect, values = None, "random"
    if tier_ >= 3:  # (Ruby: special effects far likelier; Diamond: always, and the best rolls)
        from ..mechanics.items import GEAR_EFFECTS
        if tier_ == 4 or rng.random() * 100 < RUBY_EFFECT:
            effect = rng.choice(sorted(GEAR_EFFECTS))
        else:
            effect = ""
        values = "max" if tier_ == 4 else values
    return Gear.roll(item, rarity, rng, level=level, effect=effect, values=values)
