"""Instances: runs through several generated maps of one theme.

A route between two towns (Route 1, ...) is an instance: each trip along it
has its own seed, so it's new every time, and its last doorway leads into
the town at the other end. An instance with a boss ends in an arena where a
boss group guards the way out.

Routes can have trainers (`Route.trainers`): each stands in for one of a
map's wild groups, fights once for good (`Game.trainers`) and pays prize
money. A gym is a route walked from its building, with only trainers.

Recruitment maps (`RECRUITS`) are routes too: one map full of one species,
with a giant one as the boss, walked from a Recruitment Center's board
(quests.py makes their quests).

A dungeon (Mt. Moon) is a route of `rooms` instead of a row of maps: each
room has stairs (ladders up and down) to other rooms and doorways out,
so there are dead ends and the way through has to be found. A room is
laid out the same every time (its own fixed seed); its wild Pokémon are
rolled anew for every trip. Within a trip, what's been beaten or opened
stays that way when the player comes back to a room (`Instance.rooms`).
"""

import random
import zlib
from dataclasses import dataclass, field, replace

from ..mechanics.loot import COMMON_ONLY, EARLY_BOSS, MID_BOSS, Rarities
from ..mechanics.pokemon import EVOLUTIONS, SPECIES
from .level import Level, encounter, generate, stair_col
from .themes import (CERULEAN_GYM, DIGLETTS_CAVE, FOREST, MEADOW, MT_MOON, PEWTER_GYM, ROCK_TUNNEL, ROUTE_2,
                     ROUTE_3, ROUTE_4, ROUTE_5, ROUTE_6, ROUTE_8, ROUTE_9, ROUTE_16, ROUTE_7, SILPH_CO, SAFFRON_GYM, FIGHTING_DOJO, ROUTE_11, ROUTE_12, ROUTE_13, ROUTE_14, ROUTE_15, HIDDEN_SPRING, SKATE_ROAD, SKYWARD_CLIFFS, ROUTE_18, FUCHSIA_GYM, ROUTE_22, ROUTE_24, ROUTE_25, SS_ANNE,
                     UNDERGROUND, UNDERGROUND_WEST, VERMILION_GYM, CELADON_GYM, ROCKET_HIDEOUT, POKEMON_TOWER, PoolEntry,
                     Theme)
from .spinners import carve, layout_of
from .towns import Folk

# Stands in a boss group for the rival's starter, which depends on the
# player's (`progress.Game.rival_starter`).
RIVAL_STARTER = "rival_starter"
RIVAL_STARTER_EVOLVED = "rival_starter_evolved"  # ... its next form (Charmander → Charmeleon)
RIVAL_STARTER_FINAL = "rival_starter_final"  # ... its last form (Charizard)


# What a shut Saffron gate says (before quest "saffron_gates").
SAFFRON_SHUT = "The gate to Saffron City is shut. Orders from up high: nobody gets through."


def rival_species(species: str, rival_starter: str) -> str:
    """`species`, or for a rival stand-in the rival's starter at that form."""
    if species == RIVAL_STARTER:
        return rival_starter
    if species == RIVAL_STARTER_EVOLVED:
        return EVOLUTIONS[rival_starter].into
    if species == RIVAL_STARTER_FINAL:
        return EVOLUTIONS[EVOLUTIONS[rival_starter].into].into
    return species


@dataclass(frozen=True)
class Trainer:
    """A trainer on one of a route's maps: a band of Pokémon standing in for
    a Gen 1 trainer (there are no human trainers). Beaten once for good. Prize
    money is `prize` × the level of its last Pokémon (Gen 1's rule)."""
    key: str     # unique in the game (saved in Game.trainers once beaten)
    name: str    # the band's name, shown over the team on the map: "Crawler Swarm"
    team: tuple[tuple[str, int], ...]  # (species, level), shown in a row on the map
    map: int     # which of the route's maps it's on
    prize: int   # the Gen 1 class's base prize it stands in for (Youngster 15, Bug Catcher 10, ...)
    # The rival on Nugget Bridge: at the map's first wild-group spot (`first`),
    # not to be got past (`blocks`: platforms over it don't help), with the
    # route's boss loot as its reward (`boss_loot`). Its key is a "defeat"
    # quest step's target (`quests.defeat`).
    first: bool = False
    blocks: bool = False
    boss_loot: bool = False
    spirit: bool = False  # drawn as a pale, see-through ghost on the map (the Pokémon Tower's Marowak)


@dataclass(frozen=True)
class Wave:
    """One of the bands a gym's arena sends in before its boss group."""
    name: str    # "Boulder Gang Diggers"
    team: tuple[tuple[str, int], ...]  # (species, level)
    prize: int   # base prize (as Trainer.prize)


@dataclass(frozen=True)
class Stair:
    """A way out of a dungeon room: a ladder "down" or "up" to the room `to`
    (it arrives at that room's stair back here), or a doorway "out" to the
    town `to`. `at`: how far along the room (0 = left end, 1 = right end)."""
    kind: str
    to: str
    at: float


@dataclass(frozen=True)
class Room:
    """A room of a dungeon. A room with a boss group (a trainer's team if
    `trainer`) has it guard its last stair, at the right end."""
    key: str
    name: str   # its floor, shown on the map: "B1F"
    width: int  # in tiles
    stairs: tuple[Stair, ...]
    boss_group: tuple[tuple[str, int], ...] = ()
    trainer: str = ""
    prize: int = 0
    # Who's there to talk to (as townsfolk: quests.talk): (how far along
    # the room, as `Stair.at`; who), on flat ground.
    folk: tuple[tuple[float, Folk], ...] = ()
    puzzle: str = ""  # "spinners:<layout>": the Rocket Hideout's spinner floors (world/spinners.py)
    # A painted wall (walls/<wall>) and battle backdrop (backdrops/<wall>) of
    # its own, instead of its dungeon's (Silph Co.'s President's office).
    wall: str = ""
    # Strength's boulders (scenes/boulders.py): the stairs (by their `to`)
    # a boulder sits over, until it's pushed off.
    boulders: tuple[str, ...] = ()
    # A bonus room's own wild Pokémon (instead of its dungeon's), its boss
    # drawn this many times bigger, and the chest that boss leaves
    # ("plain" / "fancy", at `boss_loot`); "" / None: the dungeon's.
    pool: tuple[PoolEntry, ...] = ()
    boss_scale: int = 0
    boss_chest: str = ""
    boss_loot: Rarities | None = None


@dataclass(frozen=True)
class Route:
    key: str
    name: str
    theme: Theme
    maps: int
    towns: tuple[str, str]  # the town keys at either end
    boss: bool = False
    loot: Rarities = COMMON_ONLY        # gear rarities from wild Pokémon and chests
    boss_loot: Rarities = EARLY_BOSS    # ... from a boss group and its chest
    # The boss group (species, level), its leader first; () = 4-5 random
    # Pokémon from the pool.
    boss_group: tuple[tuple[str, int], ...] = ()
    boss_scale: int = 1                 # the leader is drawn this many times bigger
    trainer: str = ""                   # the boss group is this trainer's team (a trainer battle)
    # What beating the boss leaves: "plain" (a chest), "fancy" (a gym's
    # chest, with the boss loot), "battle" (the boss loot comes with the
    # battle) or "" (nothing more: a recruitment, whose reward is the Pokémon).
    boss_chest: str = "plain"
    # Its doorways need (quest key, "started" or "done"); `blocked` says why not.
    needs: tuple[str, str] | None = None
    blocked: str = ""
    needs_from: str = ""   # ... only when entered from this town ("": from either end)
    blocked_done: str = ""  # ... once that quest is done, if it says something else then
    # Once this quest is done (or this key is in Game.trainers: a beaten
    # `boss_key`), the boss is this group instead (no trainer).
    boss_after: tuple[str, tuple[tuple[str, int], ...]] | None = None
    boss_key: str = ""   # saved in Game.trainers once the boss is beaten (a one-time boss trainer)
    boss_extra: tuple[tuple[str, int], ...] = ()  # with two (or more) fighting, these join the boss group
    boss_gift: str = ""  # an item (in MEDICINE) the boss gives the first time it's beaten (the Nugget)
    # A one-of-a-kind piece (`Item.unique`: item, rarity, item level) the
    # boss's leader wears, on the map too, and always drops, until it's won
    # (`boss_key` beaten): Tony's Bike Helmet.
    boss_wears: tuple[str, str, int] = ()
    boss_dialogue: tuple[tuple[str, str], ...] = ()  # what it says then
    prize: int = 0                      # a boss trainer's base prize (as Trainer.prize)
    trainers: tuple[Trainer, ...] = ()  # trainers on its maps
    wild: bool = True                   # wild Pokémon and chests (a gym: only its trainers)
    building: str = ""                  # walked from this building in its town (a gym), not a doorway
    rooms: tuple[Room, ...] = ()        # a dungeon's rooms (then `maps` is how many there are)
    cols: int = 0                       # its maps' width in tiles (0: random)
    # A gym's arena: these waves come first, then the boss group, one battle
    # after another, fought by `wave_team` Pokémon the player picks.
    waves: tuple[Wave, ...] = ()
    wave_team: int = 2
    wave_species: tuple[str, ...] = ()  # only these can be picked for the waves (() = anyone)
    # A Pokémon lent for the waves (species, level) when none in the party
    # that may fight them is at `wave_loan_below` or higher (the Sky Trial:
    # the Old Pidgeot's own Pidgeot). It fights, and goes back afterwards.
    wave_loan: tuple[str, int] = ()
    wave_loan_below: int = 0
    puzzle: str = ""  # a puzzle on the way to the arena: "trash_cans" (the Vermilion Gym, scenes/power_grid.py)
    tower: int = 0    # a Battle Tower floor (world/tower.py): its number
    sky: bool = False  # its battles are sky battles (mechanics/sky.py: the Sky Trial)
    folk: str = ""                      # walked by talking to this townsfolk (a trial), not a doorway
    folk_line: str = ""                 # ... who says this, sending the player there ("" = a trial's words)

    def other_end(self, town: str) -> str:
        return self.towns[1] if town == self.towns[0] else self.towns[0]


ROUTES = {r.key: r for r in [
    Route("route_1", "Route 1", MEADOW, maps=2, towns=("pallet", "viridian")),
    Route("viridian_forest", "Viridian Forest", FOREST, maps=3, towns=("viridian", "pewter"), boss=True,
          # (tuned with tools/balance_sim.py: a lone Lv11 starter wins about 70%, and
          # a pair, which meets two more Weedle, about the same)
          boss_group=(("caterpie", 12), ("weedle", 10), ("kakuna", 9)), boss_scale=2,
          boss_extra=(("weedle", 11), ("weedle", 11)),
          needs=("oaks_parcel", "done"),
          blocked="An old man is lying in the road. He hasn't had his coffee yet, and won't let anyone pass."),
    # A side trip from Viridian and back (Gen 1's first rival battle at its end).
    Route("route_22", "Route 22", ROUTE_22, maps=2, towns=("viridian", "viridian"), boss=True,
          # (Gen 1's Pidgey 9 and starter 8, two levels down: here both attack the
          # starter at once, which fights alone at this point; balance_sim.py)
          boss_group=(("pidgey", 7), (RIVAL_STARTER, 6)), trainer="Rival", boss_chest="battle",
          needs=("rival_22", "started"), blocked="A guard says there's nothing to see on Route 22 for now.",
          boss_after=("rival_22", (("pidgey", 9), ("spearow", 9))), prize=35),
    # The Pewter Gym, from its building: a short walk up to the arena, where
    # the Boulder Gang sends in two waves, then comes itself, led by an Onix
    # (Gen 1's Brock's team).
    Route("pewter_gym", "Pewter Gym", PEWTER_GYM, maps=1, towns=("pewter", "pewter"), boss=True,
          boss_group=(("geodude", 14), ("onix", 16)), trainer="Boulder Gang", boss_chest="fancy", prize=99,
          waves=(Wave("Boulder Gang Diggers", (("diglett", 12), ("sandshrew", 12)), 20),
                 Wave("Boulder Gang Rollers", (("geodude", 13), ("geodude", 13)), 20)),
          wild=False, building="Pewter Gym", cols=44,
          needs=("boulder_badge", "not_done"),
          blocked="Onix: You already have the Boulder Badge. The road east, Route 3, is open to you!"),
    # Route 3, from Pewter to the foot of Mt. Moon: Gen 1's trainer road.
    Route("route_3", "Route 3", ROUTE_3, maps=3, towns=("pewter", "mt_moon"),
          needs=("boulder_badge", "done"),
          blocked="A Geodude blocks the way: \"The Boulder Gang holds the gym! Beat them first!\"",
          trainers=(
              Trainer("route_3_youngster_1", "Alley Gang", (("rattata", 15), ("ekans", 15)), 0, 15),
              Trainer("route_3_bug_catcher_1", "Crawler Swarm", (("caterpie", 14), ("weedle", 14), ("caterpie", 14)),
                      0, 10),
              Trainer("route_3_lass_1", "Pidgey Flock", (("pidgey", 13), ("pidgey", 13)), 1, 15),
              Trainer("route_3_bug_catcher_2", "Bug Brood", (("weedle", 13), ("kakuna", 13), ("caterpie", 13),
                                                               ("metapod", 13)), 1, 10),
              Trainer("route_3_youngster_2", "Lone Spearow", (("spearow", 18),), 2, 15),
              Trainer("route_3_lass_2", "Singing Jigglypuff", (("jigglypuff", 18),), 2, 15),
          )),
    # Mt. Moon, as in Red/Blue: three ladders down from 1F, two of them to
    # dead ends; the way on goes down to B2F, past Team Rocket, and up to
    # the B1F room with the way out to Route 4.
    Route("mt_moon_cave", "Mt. Moon", MT_MOON, maps=7, towns=("mt_moon", "route_4"), boss_chest="battle",
          rooms=(
              Room("1f", "1F", 110, (Stair("out", "mt_moon", 0), Stair("down", "b1_west", 0.3),
                                     Stair("down", "b1_east", 0.55), Stair("down", "b1_grotto", 0.7),
                                     Stair("down", "b1_nook", 0.85)),
                   boulders=("b1_grotto",)),
              # Strength's bonus room (behind 1F's boulder): the Clefairy's moonlit grotto, Pokémon at the
              # levels of a party that comes back with Strength, and a giant Clefable guarding a fancy chest.
              Room("b1_grotto", "Moonlit Grotto", 70, (Stair("up", "1f", 0.1), Stair("up", "1f", 1)),
                   boss_group=(("clefable", 52), ("clefairy", 47), ("clefairy", 47)), boss_scale=2,
                   boss_chest="fancy", boss_loot=MID_BOSS,
                   pool=(PoolEntry("clefairy", 35, (44, 47)), PoolEntry("golbat", 25, (45, 48)),
                         PoolEntry("graveler", 20, (45, 48)), PoolEntry("parasect", 20, (44, 47)))),
              Room("b1_west", "B1F", 60, (Stair("up", "1f", 0.2), Stair("down", "b2_west", 0.8))),
              Room("b1_nook", "B1F", 44, (Stair("up", "1f", 0.5),)),
              Room("b1_east", "B1F", 70, (Stair("up", "1f", 0.15), Stair("down", "b2", 0.85))),
              Room("b2_west", "B2F", 80, (Stair("up", "b1_west", 0.15),)),
              Room("b2", "B2F", 90, (Stair("up", "b1_east", 0.1), Stair("up", "b1_exit", 1)),
                   boss_group=(("sandshrew", 18), ("rattata", 18), ("zubat", 19)), trainer="Rocket Gang Leader",
                   prize=30),
              Room("b1_exit", "B1F", 50, (Stair("down", "b2", 0.2), Stair("out", "route_4", 1))),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("mt_moon_bug_catcher", "Stinger Nest", (("weedle", 17), ("kakuna", 17)), 0, 10),
              Trainer("mt_moon_lass", "Moon Clefairy", (("clefairy", 20),), 0, 15),
              Trainer("mt_moon_youngster", "Cave Rats", (("rattata", 16), ("rattata", 16), ("zubat", 16)), 0, 15),
              Trainer("mt_moon_hiker", "Rockslide Clan", (("geodude", 16), ("geodude", 16), ("geodude", 16), ("onix", 17)),
                      3, 35),
              Trainer("mt_moon_rocket_1", "Rocket Gang", (("rattata", 19), ("zubat", 19)), 4, 30),
              Trainer("mt_moon_rocket_2", "Rocket Gang", (("zubat", 18), ("ekans", 18)), 5, 30),
          )),
    # Route 4's way down from the stop at Mt. Moon's exit to Cerulean City
    # (its key isn't "route_4": that's the stop, a town).
    Route("route_4_east", "Route 4", ROUTE_4, maps=2, towns=("route_4", "cerulean"),
          trainers=(
              Trainer("route_4_lass", "Hillside Pack", (("spearow", 19), ("rattata", 19), ("ekans", 19)), 0, 15),
              Trainer("route_4_hiker", "Dune Diggers", (("sandshrew", 20), ("sandshrew", 20)), 1, 20),
          )),
    # Route 24 north of Cerulean, as in Red/Blue: the rival waits at the
    # bridge's start (Gen 1's second rival battle, with Abra and an evolved
    # starter), then the bridge's five bands in a row, and at the far end a
    # Rocket who hands over the Nugget, then fights (once; later trips find
    # wild Pokémon there).
    Route("nugget_bridge", "Nugget Bridge", ROUTE_24, maps=2, towns=("cerulean", "route_24"), boss=True,
          boss_group=(("ekans", 23), ("zubat", 22)), trainer="Rocket Gang", boss_chest="battle", prize=30,
          boss_key="nugget_rocket", boss_gift="Nugget",
          boss_dialogue=(("Rocket", "Congratulations! You beat our five contest trainers! Here's your prize: "
                                    "a Nugget!"),
                         ("", "You received a Nugget!"),
                         ("Rocket", "...Hey, kid. That was the contest. This is Team Rocket's way of finding "
                                    "fresh talent. Pity you said no."),),
          boss_after=("nugget_rocket", (("oddish", 22), ("bellsprout", 22), ("abra", 21))),
          trainers=(
              # (Gen 1's team a couple of levels up; tuned with tools/balance_sim.py:
              # all four attack at once, against the player's two)
              Trainer("nugget_rival", "Rival", (("pidgeotto", 19), ("abra", 16), ("rattata", 16),
                                                (RIVAL_STARTER_EVOLVED, 20)), 0, 50,
                      first=True, blocks=True, boss_loot=True),
              Trainer("nugget_1", "Bridge Crawlers", (("caterpie", 20), ("weedle", 20), ("metapod", 20)), 0, 10),
              Trainer("nugget_2", "Bridge Flock", (("pidgey", 20), ("nidoran_f", 20)), 0, 15),
              Trainer("nugget_3", "Bridge Rats", (("rattata", 20), ("ekans", 20), ("zubat", 20)), 0, 15),
              Trainer("nugget_4", "Bridge Thorns", (("nidoran_f", 21), ("nidoran_m", 21)), 0, 15),
              Trainer("nugget_5", "Bridge Champs", (("sandshrew", 22), ("spearow", 22)), 1, 20),
          )),
    # The Cerulean Gym, from its building, as the Pewter Gym: the Cascade
    # Crew's two waves of Water Pokémon, then the crew itself, led by a
    # Starmie (Gen 1's Misty's team, Staryu and Starmie).
    Route("cerulean_gym", "Cerulean Gym", CERULEAN_GYM, maps=1, towns=("cerulean", "cerulean"), boss=True,
          # (Misty's Staryu 18 and Starmie 21, a little up; the waves come first,
          # without healing; tuned with tools/balance_sim.py)
          boss_group=(("starmie", 22), ("staryu", 19)), trainer="Cascade Crew", boss_chest="fancy", prize=99,
          waves=(Wave("Cascade Crew Swimmers", (("goldeen", 18), ("psyduck", 18)), 30),
                 Wave("Cascade Crew Divers", (("horsea", 19), ("shellder", 19)), 30)),
          wild=False, building="Cerulean Gym", cols=44,
          needs=("cascade_badge", "not_done"),
          blocked="Starmie: Hyah! You already have the Cascade Badge. Show it off somewhere else!"),
    # The Vermilion Gym, from its building, as the other gyms: the Thunder
    # Battalion's two waves of Electric Pokémon, then the battalion itself,
    # led by a Raichu (Gen 1's Lt. Surge: Voltorb, Pikachu, Raichu). Three
    # fight its waves (the party has three places from the S.S. Anne on):
    # it's meant to be very hard with fewer (tools/balance_sim.py).
    Route("vermilion_gym", "Vermilion Gym", VERMILION_GYM, maps=1, towns=("vermilion", "vermilion"), boss=True,
          boss_group=(("raichu", 31), ("voltorb", 29), ("magnemite", 29)), trainer="Thunder Battalion",
          boss_chest="fancy", prize=99,
          waves=(Wave("Thunder Battalion Privates", (("pikachu", 27), ("voltorb", 27), ("magnemite", 27)), 30),
                 Wave("Thunder Battalion Sergeants", (("magnemite", 28), ("voltorb", 28), ("pikachu", 28)), 30)),
          wave_team=3, wild=False, building="Vermilion Gym", cols=44, puzzle="trash_cans",
          needs=("thunder_badge", "active"),
          blocked="A small, thorny tree has grown over the gym's door. It would have to be cut down to get in.",
          blocked_done="Raichu: Hey, kid! You've got the Thunder Badge already. Go show it off!"),
    # The Celadon Gym (quest "rainbow_badge"): Erika's greenhouse. Clouds of
    # spores drift over the walk to the arena (`puzzle` "spores",
    # scenes/spores.py), so the team may arrive asleep, poisoned or
    # paralysed; then the Blossom Troupe's two waves of Grass Pokémon, and
    # the troupe itself, led by a Vileplume (Gen 1's Erika: Victreebel,
    # Tangela, Vileplume).
    Route("celadon_gym", "Celadon Gym", CELADON_GYM, maps=1, towns=("celadon_square", "celadon_square"), boss=True,
          boss_group=(("vileplume", 39), ("victreebel", 38), ("tangela", 37)), trainer="Blossom Troupe",
          boss_chest="fancy", prize=99, boss_loot=MID_BOSS,
          waves=(Wave("Blossom Troupe Buds", (("oddish", 35), ("bellsprout", 35), ("gloom", 36)), 20),
                 Wave("Blossom Troupe Petals", (("weepinbell", 36), ("exeggcute", 36), ("gloom", 37)), 25)),
          wave_team=3, wild=False, building="Celadon Gym", cols=60, puzzle="spores",
          needs=("rainbow_badge", "active"),
          blocked="The gym's glass doors are locked. A sign: \"Closed for watering. - Erika\"",
          blocked_done="Vileplume: Oh, it's you again... The Rainbow Badge suits you. Do come back to smell the "
                       "flowers."),
    # The Fuchsia Gym (quest "soul_badge"): Koga's ninja dojo. Invisible
    # walls and poison vents on the walk to the arena (`puzzle` "ninja",
    # scenes/ninja.py), then the Ninja Clan's two waves of Poison Pokémon,
    # and the clan itself, led by a giant Weezing (Gen 1's Koga: Koffing,
    # Muk, Koffing, Weezing; Muk has no art: Grimer stands in).
    Route("fuchsia_gym", "Fuchsia Gym", FUCHSIA_GYM, maps=1, towns=("fuchsia", "fuchsia"), boss=True,
          # (a party of three at Lv47/46/46 with 3 Hyper Potions and 2 Full Heals wins about 71%,
          # tools/balance_sim.py, not counting the gas on the way in)
          boss_group=(("weezing", 54), ("koffing", 51), ("grimer", 51), ("golbat", 51)), boss_scale=2,
          trainer="Ninja Clan", boss_chest="fancy", prize=99, boss_loot=MID_BOSS,
          waves=(Wave("Ninja Clan Initiates", (("koffing", 49), ("golbat", 49), ("grimer", 49)), 25),
                 Wave("Ninja Clan Shadows", (("venomoth", 50), ("arbok", 50), ("koffing", 50)), 30)),
          wave_team=3, wild=False, building="Fuchsia Gym", cols=64, puzzle="ninja",
          needs=("soul_badge", "active"),
          blocked="The Fuchsia Gym's doors are shut, and something hisses on the other side. A sign: \"Closed "
                  "for ninja training. Intruders will be poisoned.\"",
          blocked_done="Weezing: Hsss... The Soul Badge suits you. Koga's students still talk about your visit."),
    # Team Rocket's Hideout under the Celadon Game Corner (quest
    # "rocket_hideout"), as in Red/Blue: four basement floors of Rockets
    # (bands; no wild Pokémon). A guard at the poster blocks the way in; on
    # B4F a Rocket with the Lift Key blocks the lift down to the boss's
    # office, where the Boss (a Persian, with Gen 1's Giovanni's team) has
    # the Silph Scope. Rocket Pokémon stand in for Gen 1's: Koffing, Grimer,
    # Raticate, Zubat/Golbat, Ekans/Arbok, Machop/Machoke, Drowzee/Hypno.
    Route("rocket_hideout", "Rocket Hideout", ROCKET_HIDEOUT, maps=5, towns=("celadon_square", "celadon_square"),
          boss_chest="battle", boss_loot=MID_BOSS, wild=False, building="Game Corner",
          needs=("rocket_hideout", "started"),
          blocked="The Game Corner. Slot machines jingle and clatter inside. A grumpy-looking man in black stands "
                  "by a poster at the back...",
          rooms=(
              Room("b1", "B1F", 90, (Stair("out", "celadon_square", 0), Stair("down", "b2", 1))),
              # (B2F and B3F: spinner floors, as in Red/Blue: world/spinners.py)
              Room("b2", "B2F", 100, (Stair("up", "b1", 0.05), Stair("down", "b3", 0.95)), puzzle="spinners:b2"),
              Room("b3", "B3F", 100, (Stair("up", "b2", 0.05), Stair("down", "b4", 0.95)), puzzle="spinners:b3"),
              Room("b4", "B4F", 80, (Stair("up", "b3", 0.05), Stair("down", "office", 1))),
              # (the Boss guards the back door out, up to the Game Corner)
              Room("office", "Boss's Office", 50, (Stair("up", "b4", 0.1), Stair("out", "celadon_square", 1)),
                   boss_group=(("persian", 43), ("onix", 41), ("rhyhorn", 41), ("kangaskhan", 42)),
                   trainer="Rocket Boss", prize=99),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("hideout_poster_guard", "Poster Guard", (("raticate", 37), ("zubat", 37)), 0, 30,
                      first=True, blocks=True),
              Trainer("hideout_b1_1", "Rocket Gang", (("koffing", 37), ("grimer", 37), ("ekans", 37)), 0, 30),
              Trainer("hideout_b1_2", "Rocket Gang", (("machop", 38), ("drowzee", 38)), 0, 30),
              Trainer("hideout_b2_1", "Rocket Gang", (("golbat", 38), ("arbok", 38)), 1, 30),
              Trainer("hideout_b2_2", "Rocket Gang", (("raticate", 38), ("koffing", 38), ("zubat", 37)), 1, 30),
              Trainer("hideout_b3_1", "Rocket Gang", (("machoke", 39), ("grimer", 38)), 2, 30),
              Trainer("hideout_b3_2", "Rocket Gang", (("drowzee", 39), ("koffing", 39), ("ekans", 38)), 2, 30),
              Trainer("hideout_lift_rocket", "Lift Key Guard", (("koffing", 40), ("golbat", 40), ("raticate", 40)),
                      3, 30, first=True, blocks=True, boss_loot=True),
              Trainer("hideout_b4", "Rocket Gang", (("hypno", 39), ("arbok", 39)), 3, 30),
          )),
    # Lavender Town's Pokémon Tower (quest "pokemon_tower"), as in Red/Blue:
    # seven floors of graves, with wild ghosts (Gastly, Haunter) and Cubone,
    # and Channelers' bands. The rival waits on 2F; on 6F Marowak's restless
    # ghost bars the stairs (it leaves the Thick Bone); on 7F Team Rocket
    # holds Mr. Fuji, and guards the back stairs out.
    Route("pokemon_tower", "Pokémon Tower", POKEMON_TOWER, maps=7, towns=("lavender", "lavender"),
          boss_chest="battle", boss_loot=MID_BOSS, building="Pokémon Tower",
          needs=("pokemon_tower", "started"),
          blocked="The Pokémon Tower, where Pokémon are laid to rest. A cold draught blows from the door... "
                  "Something moves inside, but you can't make out what. You'd need a way to see it.",
          rooms=(
              Room("1f", "1F", 70, (Stair("out", "lavender", 0), Stair("up", "2f", 1))),
              Room("2f", "2F", 80, (Stair("down", "1f", 0.05), Stair("up", "3f", 0.95))),
              Room("3f", "3F", 90, (Stair("down", "2f", 0.05), Stair("up", "4f", 0.95))),
              Room("4f", "4F", 90, (Stair("down", "3f", 0.05), Stair("up", "5f", 0.95))),
              Room("5f", "5F", 90, (Stair("down", "4f", 0.05), Stair("up", "6f", 0.95))),
              Room("6f", "6F", 70, (Stair("down", "5f", 0.05), Stair("up", "7f", 1))),
              # (the Rockets guard the back stairs down and out)
              Room("7f", "7F", 50, (Stair("down", "6f", 0.1), Stair("out", "lavender", 1)),
                   boss_group=(("arbok", 43), ("golbat", 42), ("koffing", 42), ("raticate", 42)),
                   trainer="Rocket Gang", prize=30),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("tower_rival", "Rival", (("pidgeotto", 40), ("growlithe", 39), ("kadabra", 39),
                                               (RIVAL_STARTER_EVOLVED, 42)), 1, 35,
                      first=True, blocks=True, boss_loot=True),
              Trainer("tower_channeler_1", "Channeler's Spirits", (("gastly", 39), ("gastly", 39)), 2, 30),
              Trainer("tower_channeler_2", "Channeler's Spirits", (("haunter", 40),), 2, 30),
              Trainer("tower_channeler_3", "Channeler's Spirits", (("gastly", 40), ("cubone", 39), ("gastly", 39)),
                      3, 30),
              Trainer("tower_channeler_4", "Channeler's Spirits", (("haunter", 40), ("gastly", 40)), 3, 30),
              Trainer("tower_channeler_5", "Channeler's Spirits", (("haunter", 41), ("haunter", 40)), 4, 30),
              Trainer("tower_channeler_6", "Channeler's Spirits", (("cubone", 41), ("gastly", 41)), 4, 30),
              # (Marowak alone would fall at once to three: the lost spirits gather round her)
              Trainer("tower_marowak", "Restless Spirits", (("marowak", 50), ("haunter", 44), ("gastly", 44),
                                                            ("haunter", 44)), 5, 0, first=True, blocks=True,
                      spirit=True),
          )),
    # The S.S. Anne, docked at Vermilion City (quest "ss_anne"), as in
    # Red/Blue: cabins full of trainers (sailors, gentlemen, a fisherman),
    # the rival waiting on the upper deck, and the seasick Captain, who
    # gives HM01 Cut. A dungeon of rooms; no wild Pokémon aboard. Once the
    # quest is done the ship has sailed.
    Route("ss_anne", "S.S. Anne", SS_ANNE, maps=4, towns=("vermilion", "vermilion"), boss_chest="battle",
          wild=False, needs=("ss_anne", "active"),
          blocked="A sailor checks tickets at the gangway: \"Passengers only! No ticket, no boarding.\"",
          blocked_done="The S.S. Anne has set sail. She'll be back in port next year.",
          rooms=(
              Room("deck", "1F", 90, (Stair("out", "vermilion", 0), Stair("down", "hold", 0.45),
                                      Stair("up", "upper", 0.9))),
              Room("hold", "B1F", 70, (Stair("up", "deck", 0.15),)),
              Room("upper", "2F", 80, (Stair("down", "deck", 0.1), Stair("up", "cabin", 1)),
                   # (Gen 1's Pidgeotto 19, Raticate 16, Kadabra 18 and the starter's next form 20, a few
                   # levels up: all four attack the player's two at once; tuned with tools/balance_sim.py)
                   boss_group=(("pidgeotto", 22), ("raticate", 19), ("kadabra", 18), (RIVAL_STARTER_EVOLVED, 22)),
                   trainer="Rival", prize=35),
              Room("cabin", "Captain's cabin", 40, (Stair("down", "upper", 0.15),),
                   folk=((0.7, Folk("ss_anne_captain", "Captain", "machop", 0, (
                       "Ooargh... the sea's calm as glass and I still feel dreadful...",
                       "A captain who gets seasick. Don't tell the passengers, will you?",
                   ))),)),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("ss_anne_gentleman_1", "Gentleman's Hounds", (("growlithe", 26), ("growlithe", 26)), 0, 70),
              Trainer("ss_anne_lass", "Seaside Lass", (("pidgey", 25), ("nidoran_f", 25), ("jigglypuff", 25)), 0, 15),
              Trainer("ss_anne_youngster", "Cabin Boys", (("rattata", 25), ("ekans", 25), ("raticate", 24)), 0, 15),
              Trainer("ss_anne_sailor_1", "Deckhands", (("machop", 26), ("shellder", 26)), 1, 30),
              Trainer("ss_anne_sailor_2", "Bosun's Crew", (("machop", 26), ("tentacool", 26), ("horsea", 26)), 1, 30),
              Trainer("ss_anne_fisherman", "Fishing Party", (("goldeen", 25), ("tentacool", 25), ("staryu", 25)),
                      1, 35),
              Trainer("ss_anne_gentleman_2", "First Class", (("pikachu", 28), ("growlithe", 27)), 2, 70),
              Trainer("ss_anne_lass_2", "Ballroom Belles", (("jigglypuff", 26), ("clefairy", 26)), 2, 15),
          )),
    # Route 25, from the top of Route 24 east to Bill's Sea Cottage.
    Route("route_25", "Route 25", ROUTE_25, maps=2, towns=("route_24", "sea_cottage"),
          trainers=(
              Trainer("route_25_hiker", "Hill Hikers", (("geodude", 21), ("geodude", 21), ("onix", 21)), 0, 35),
              Trainer("route_25_picnicker", "Picnic Party", (("pidgey", 21), ("nidoran_f", 21), ("nidoran_m", 21)),
                      0, 15),
              Trainer("route_25_camper", "Camping Crew", (("rattata", 22), ("ekans", 22), ("spearow", 22)), 1, 15),
              Trainer("route_25_lass", "Garden Club", (("oddish", 22), ("bellsprout", 22)), 1, 15),
          )),
    # The burgled house at the end of Cerulean City's street (quest
    # "burglary"): through it, its backyard, where the Rocket who broke in
    # is hiding (Gen 1's Machop and Drowzee: Mankey and Abra stand in).
    Route("cerulean_backyard", "Burgled House", MEADOW, maps=1, towns=("cerulean", "cerulean"), boss=True,
          boss_group=(("mankey", 24), ("abra", 22), ("zubat", 22)), trainer="Rocket Gang", boss_chest="battle",
          prize=30, wild=False, building="Burgled House", cols=30,
          needs=("burglary", "active"),
          blocked="The door is taped shut. A note says: \"Police business. Nobody goes in until the thief is found.\"",
          blocked_done="The owner is tidying up: \"Thanks for chasing off that thief! The backyard's open, by the way: "
                       "it's the way south, onto Route 5.\""),
    # Route 5, south from Cerulean City (through the burgled house's
    # backyard) to the stop by the Underground Path and Saffron City's gate
    # (its key isn't "route_5": that's the stop, a town). No trainers, as
    # in Red/Blue.
    Route("route_5_south", "Route 5", ROUTE_5, maps=2, towns=("cerulean", "route_5"),
          needs=("burglary", "done"),
          blocked="A fence blocks the road south. Past it, footprints lead into the backyard of the burgled house."),
    # The Underground Path under Saffron City (its gates are shut), from the
    # Route 5 stop to the one at Route 6's top. No trainers, as in Red/Blue.
    Route("underground_path", "Underground Path", UNDERGROUND, maps=2, towns=("route_5", "route_6")),
    # Route 6, down to Vermilion City (its key isn't "route_6": that's the
    # stop at the tunnel's south end). Gen 1's Bug Catchers and Jr.
    # Trainers (here bands), a couple of levels up.
    Route("route_6_south", "Route 6", ROUTE_6, maps=2, towns=("route_6", "vermilion"),
          trainers=(
              Trainer("route_6_bug_catcher_1", "Meadow Swarm", (("butterfree", 24), ("beedrill", 24)), 0, 10),
              Trainer("route_6_jr_trainer_1", "Pond Pals", (("psyduck", 24), ("goldeen", 24)), 0, 20),
              Trainer("route_6_jr_trainer_2", "Spark Squad", (("pikachu", 25), ("rattata", 25), ("raticate", 24)),
                      1, 20),
              Trainer("route_6_bug_catcher_2", "Thicket Crawlers", (("venonat", 25), ("paras", 25), ("metapod", 25)),
                      1, 10),
          )),
    # Route 11, east of Vermilion City (after the Thunder Badge): Gen 1's
    # Engineers, Gamblers and Youngsters, as bands, about level with the
    # party. It ends at the mouth of Diglett's Cave, where Snorlax sleeps
    # across the road to Route 12.
    Route("route_11", "Route 11", ROUTE_11, maps=2, towns=("vermilion", "route_11"),
          needs=("thunder_badge", "done"),
          blocked="Soldiers of the Thunder Battalion are drilling on the road east. Nobody gets past until "
                  "someone beats their gym.",
          trainers=(
              Trainer("route_11_engineer_1", "Engine Crew", (("magnemite", 29), ("voltorb", 29)), 0, 50),
              Trainer("route_11_youngster_1", "Roadside Gang", (("rattata", 28), ("ekans", 28), ("zubat", 28)), 0, 15),
              Trainer("route_11_gambler_1", "High Rollers", (("horsea", 29), ("goldeen", 29), ("shellder", 28)), 1, 70),
              Trainer("route_11_engineer_2", "Rolling Stones", (("geodude", 29), ("onix", 30)), 1, 50),
              Trainer("route_11_youngster_2", "Sleepy Heads", (("drowzee", 30), ("drowzee", 29), ("jigglypuff", 29)),
                      1, 15),
          )),
    # Diglett's Cave, from Route 11 to Route 2 by Pewter City: one long
    # tunnel of Diglett and Dugtrio, with a giant Dugtrio's band at its end.
    Route("digletts_cave", "Diglett's Cave", DIGLETTS_CAVE, maps=3, towns=("route_11", "route_2"), boss=True,
          boss_group=(("dugtrio", 35), ("dugtrio", 32), ("diglett", 31), ("diglett", 31)), boss_scale=2,
          boss_loot=MID_BOSS),
    # Route 9, east of Cerulean City (once Flash is in hand) to the Route 10
    # Pokémon Center: Gen 1's Jr. Trainers, Hikers and Bug Catchers, as
    # bands, about level with the party.
    Route("route_9", "Route 9", ROUTE_9, maps=2, towns=("cerulean", "route_10"),
          needs=("flash", "done"),
          blocked="A Hiker blocks the road east: \"Rock Tunnel's past here, and it's pitch dark! Don't even "
                  "think about it without a way to light it.\"",
          trainers=(
              Trainer("route_9_jr_trainer_1", "Meadow Duo", (("oddish", 31), ("bellsprout", 31)), 0, 20),
              Trainer("route_9_hiker_1", "Boulder Bunch", (("geodude", 31), ("machop", 31), ("geodude", 31)), 0, 35),
              Trainer("route_9_bug_catcher", "Silk Spinners", (("butterfree", 32), ("beedrill", 32)), 1, 10),
              Trainer("route_9_jr_trainer_2", "Roadside Pals", (("pidgeotto", 32), ("raticate", 31), ("nidorino", 31)),
                      1, 20),
              Trainer("route_9_hiker_2", "Mountain Men", (("onix", 33), ("machop", 32)), 1, 35),
          )),
    # Rock Tunnel, from the Route 10 Pokémon Center down to Lavender Town:
    # pitch dark (Flash's light), two floors; a Hiker's crew guards the
    # stairs back up to the south exit, as Gen 1's Hikers fill the tunnel.
    Route("rock_tunnel", "Rock Tunnel", ROCK_TUNNEL, maps=3, towns=("route_10", "lavender"), boss_chest="plain",
          boss_loot=MID_BOSS, needs=("flash", "done"),
          blocked="It's pitch dark inside. Without a way to light it, you'd be lost in no time.",
          rooms=(
              Room("1f", "1F", 100, (Stair("out", "route_10", 0), Stair("down", "b1", 0.9))),
              Room("b1", "B1F", 110, (Stair("up", "1f", 0.1), Stair("down", "b2_den", 0.5),
                                      Stair("up", "1f_south", 1)),
                   boss_group=(("onix", 36), ("machop", 34), ("machop", 34), ("geodude", 34)), trainer="Hiker Crew",
                   prize=35, boulders=("b2_den",)),
              # Strength's bonus room (behind B1F's boulder): an Onix's den deep in the rock, and a giant
              # Onix with its diggers guarding a fancy chest.
              Room("b2_den", "Onix's Den", 70, (Stair("up", "b1", 0.1), Stair("up", "b1", 1)),
                   boss_group=(("onix", 53), ("graveler", 49), ("machoke", 49), ("golbat", 48)), boss_scale=2,
                   boss_chest="fancy", boss_loot=MID_BOSS,
                   pool=(PoolEntry("onix", 25, (45, 48)), PoolEntry("graveler", 30, (45, 48)),
                         PoolEntry("machoke", 25, (45, 48)), PoolEntry("golbat", 20, (45, 47)))),
              Room("1f_south", "1F", 70, (Stair("down", "b1", 0.15), Stair("out", "lavender", 1))),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("rock_tunnel_hiker_1", "Pick and Shovel", (("geodude", 32), ("geodude", 32), ("onix", 32)), 0, 35),
              Trainer("rock_tunnel_maniac", "Collector's Pride", (("clefairy", 32), ("psyduck", 32)), 0, 50),
              Trainer("rock_tunnel_jr_trainer", "Lost Hikers", (("jigglypuff", 33), ("pidgeotto", 33)), 1, 20),
              Trainer("rock_tunnel_hiker_2", "Rubble Rousers", (("machop", 33), ("geodude", 33), ("machop", 33)), 1, 35),
              Trainer("rock_tunnel_jr_trainer_2", "Tunnel Twins", (("oddish", 33), ("bellsprout", 33)), 2, 20),
          )),
    # Route 8, west of Lavender Town to the gate at Saffron's east side:
    # Gen 1's Gamblers, Lasses, Super Nerds and Twins, as bands.
    Route("route_8", "Route 8", ROUTE_8, maps=2, towns=("lavender", "route_8_gate"),
          trainers=(
              Trainer("route_8_gambler", "Lucky Streak", (("growlithe", 34), ("meowth", 34)), 0, 70),
              Trainer("route_8_lass", "Pretty Pals", (("clefairy", 34), ("jigglypuff", 34), ("nidorina", 33)), 0, 15),
              Trainer("route_8_super_nerd", "Gadget Nerds", (("magnemite", 35), ("voltorb", 35), ("magnemite", 35)),
                      1, 25),
              Trainer("route_8_twins", "Twin Tails", (("nidoran_f", 35), ("nidoran_m", 35)), 1, 20),
          )),
    # The Underground Path's west-east tunnel, from the Route 8 Gate under
    # Saffron City to Route 7, by Celadon City (no trainers, as in Red/Blue).
    Route("underground_west", "Underground Path", UNDERGROUND_WEST, maps=2, towns=("route_8_gate", "celadon")),
    # Route 16, west of Celadon West End (once the Snorlax asleep across it
    # is awake and calmed down: "boss:snorlax_wakes"), to the Route 16 Gate:
    # Gen 1's Bikers, as bands.
    Route("route_16", "Route 16", ROUTE_16, maps=2, towns=("route_16", "celadon_west"),
          needs=("boss:snorlax_wakes", "beaten"),
          blocked="A huge Pokémon is fast asleep right across the road west. There's no getting past it.",
          trainers=(
              Trainer("route_16_biker", "Road Hogs", (("raticate", 41), ("fearow", 41)), 0, 40),
              Trainer("route_16_biker_2", "Exhaust Pipes", (("koffing", 41), ("grimer", 41), ("koffing", 41)), 1, 40),
          )),
    # The Snorlax west of Celadon, woken with a feast and the Poké Flute
    # (quest "snorlax_west"; or, after it, the flute alone: "snorlax_second"):
    # grumpy, it has to be calmed down in a battle, with the Route 8 snack
    # thieves, back for the leftovers (alone, it's no match for a team of
    # three; this way a party of three at Lv42/41/41 with 3 Hyper Potions
    # wins about 75%, tools/balance_sim.py). Then it may join.
    Route("snorlax_wakes", "Snorlax's Rude Awakening", ROUTE_16, maps=1, towns=("celadon_west", "celadon_west"),
          boss=True, boss_group=(("snorlax", 42), ("persian", 42), ("primeape", 42), ("raticate", 42)), boss_scale=2,
          boss_chest="", wild=False, cols=30, trainer="Snack Pack", folk="celadon_snorlax",
          folk_line="SNOOORT! Snorlax heaves itself up, grumpy and still hungry, and the snack thieves are back "
                    "for the leftovers. Calm them all down!"),
    # ... and the one at the Route 11 Gate, across the road to Route 12: the
    # same, with the dream eaters that have been feeding on its dreams (the
    # Route 11 Hypno's Drowzee, and a Jigglypuff that sings them all to
    # sleep), furious their dinner woke up (about 72%, as above).
    Route("snorlax_wakes_east", "Snorlax's Rude Awakening", ROUTE_11, maps=1, towns=("route_11", "route_11"),
          boss=True, boss_group=(("snorlax", 42), ("hypno", 40), ("drowzee", 40), ("jigglypuff", 40)), boss_scale=2,
          boss_chest="", wild=False, cols=30, trainer="Dream Eaters", folk="route_12_snorlax",
          folk_line="SNOOORT! Snorlax heaves itself up, grumpy and hungry, and the Drowzee that were feeding on "
                    "its dreams are furious their dinner woke up. Calm them all down!"),
    # Route 12, from the Route 11 Gate (once its Snorlax is awake and calmed
    # down: "boss:snorlax_wakes_east") up the coast to Lavender Town:
    # Gen 1's Fishermen, Jr. Trainers and Rockers, as bands, about level
    # with the party after the Snorlax.
    Route("route_12", "Route 12", ROUTE_12, maps=2, towns=("route_11", "lavender"),
          needs=("boss:snorlax_wakes_east", "beaten"), needs_from="route_11",  # (from Lavender: walk down to it)
          blocked="A huge Pokémon is fast asleep right across the road to Route 12. There's no getting past it.",
          trainers=(
              Trainer("route_12_fisherman_1", "Pier Anglers", (("goldeen", 43), ("tentacool", 43), ("goldeen", 43)),
                      0, 35),
              Trainer("route_12_jr_trainer", "Seaside Pals", (("nidorina", 43), ("weepinbell", 43)), 0, 20),
              Trainer("route_12_rocker", "Static Band", (("voltorb", 44), ("electrode", 44)), 1, 25),
              Trainer("route_12_fisherman_2", "Deep Sea Haul", (("seaking", 44), ("shellder", 43), ("horsea", 43)),
                      1, 35),
          )),
    # The Hidden Spring, up the cliffs behind the Route 16 Gate (quest
    # "thirsty_guard": the guard points the way): one map of Water
    # Pokémon, and a giant Golduck's gang squatting at the spring.
    Route("hidden_spring", "Hidden Spring", HIDDEN_SPRING, maps=1, towns=("route_16", "route_16"), boss=True,
          boss_group=(("golduck", 47), ("seaking", 43), ("golduck", 42), ("psyduck", 43)), boss_scale=2,
          trainer="Spring Squatters", boss_loot=MID_BOSS, cols=60, folk="route_16_guard",
          folk_line="The spring's just up the cliff path behind the gate. Mind the Golduck: they don't share."),
    # The skate road (Red/Blue's Cycling Road), from the Route 16 Gate down
    # to the Route 18 Gate, once the guard has had his water and the player
    # has a board (quest "skate_board"): downhill all the way, everyone on a
    # board (`Theme.skate`). Gen 1's Bikers as skater bands; at the bottom,
    # Tony, the road's legend: a giant Kangaskhan in his Bike Helmet, which
    # drops for sure (`boss_wears`; once, `boss_key`).
    Route("skate_road", "Skate Road", SKATE_ROAD, maps=3, towns=("route_16", "route_18"), boss=True,
          boss_group=(("kangaskhan", 50), ("primeape", 45), ("machoke", 45), ("raticate", 45)), boss_scale=2,
          trainer="Tony", boss_key="tony", boss_wears=("Bike Helmet", "Rare", 45), boss_loot=MID_BOSS,
          needs=("skate_board", "done"),
          blocked="Skaters come rocketing up out of the gate. Nobody walks the skate road: you'd need a board.",
          trainers=(
              Trainer("skate_kickflip", "Kickflip Crew", (("primeape", 44), ("mankey", 44)), 0, 40),
              Trainer("skate_grind", "Grind Gang", (("machoke", 44), ("machop", 44), ("machop", 44)), 0, 40),
              Trainer("skate_halfpipe", "Half-Pipe Hogs", (("raticate", 45), ("fearow", 45)), 1, 40),
              Trainer("skate_ollie", "Ollie Outlaws", (("koffing", 45), ("grimer", 45), ("koffing", 45)), 1, 40),
              Trainer("skate_rail", "Rail Riders", (("arbok", 46), ("golbat", 45)), 2, 40),
          )),
    # The Sky Trial (quest "learn_to_fly"), up the Skyward Cliffs from the
    # Route 16 Gate: the bird alone (a Pidgeotto, Pidgeot or Fearow), sky
    # battles (`sky`), one foe at a time, back to back: a Primeape leaping
    # off the cliffs, a Magneton's sparks, then a giant Electabuzz, the
    # storm itself (a lone bird at Lv44-45 with 2 Hyper Potions, perching
    # when hurt, wins about 70%; Rock types resist all its moves: none).
    Route("sky_trial", "Sky Trial", SKYWARD_CLIFFS, maps=1, towns=("route_16", "route_16"), boss=True,
          boss_group=(("electabuzz", 41),), boss_scale=2, trainer="Storm Guardian", boss_chest="battle",
          waves=(Wave("Cliff Climber", (("primeape", 42),), 0),
                 Wave("Static Spark", (("magneton", 42),), 0)),
          wave_team=1, wave_species=("pidgeotto", "pidgeot", "fearow"), wild=False, cols=30, sky=True,
          wave_loan=("pidgeot", 45), wave_loan_below=42,
          folk="route_16_pidgeot",
          folk_line="Up you go. Remember: read the wind, perch to rest, and fly out of reach."),
    # Route 18, from the Route 18 Gate (the skate road's bottom) east to
    # Fuchsia City: Gen 1's Bird Keepers, as bands, about level with the
    # party after Tony. (Its key isn't "route_18": that's the gate.)
    Route("route_18_east", "Route 18", ROUTE_18, maps=2, towns=("route_18", "fuchsia"),
          trainers=(
              Trainer("route_18_bird_keeper_1", "Coast Flock", (("pidgeotto", 46), ("spearow", 45), ("spearow", 45)),
                      0, 25),
              Trainer("route_18_bird_keeper_2", "Beak Brigade", (("fearow", 46), ("fearow", 46)), 1, 25),
              Trainer("route_18_bird_keeper_3", "Sea Breeze", (("pidgeot", 47), ("pidgeotto", 46)), 1, 25),
          )),
    # The coastal road (Red/Blue's Routes 13-15), from the Route 11 Gate's
    # doorway past its Snorlax down to Fuchsia City, the other way there
    # than the skate road (quest "coastal_road"). Route 13: fences and
    # flower beds to Silence Bridge; Route 14: woods to the Route 15 Gate;
    # Route 15: the bird keepers' road into Fuchsia, ending at the
    # Thornwood Gang, a giant Victreebel's band that's overgrown it.
    Route("route_13", "Route 13", ROUTE_13, maps=2, towns=("route_11", "silence_bridge"),
          needs=("boss:snorlax_wakes_east", "beaten"),
          blocked="A huge Pokémon is fast asleep right across the road. There's no getting past it.",
          trainers=(
              Trainer("route_13_bird_keeper", "Fence Hoppers", (("pidgeotto", 45), ("spearow", 44), ("spearow", 44)),
                      0, 25),
              Trainer("route_13_jr_trainer", "Picnic Pals", (("gloom", 45), ("nidorina", 45)), 0, 20),
              Trainer("route_13_beauty", "Petal Parade", (("vileplume", 46), ("weepinbell", 45)), 1, 70),
              Trainer("route_13_biker", "Fence Riders", (("koffing", 45), ("grimer", 45), ("koffing", 45)), 1, 20),
          )),
    Route("route_14", "Route 14", ROUTE_14, maps=2, towns=("silence_bridge", "route_15"),
          trainers=(
              Trainer("route_14_bird_keeper", "High Flyers", (("pidgeot", 47), ("fearow", 46)), 0, 25),
              Trainer("route_14_bug_catcher", "Moth Swarm", (("venomoth", 46), ("venonat", 45), ("venomoth", 46)),
                      0, 15),
              Trainer("route_14_biker", "Smoke Riders", (("koffing", 46), ("weezing", 47)), 1, 20),
              Trainer("route_14_beauty", "Garden Club", (("vileplume", 47), ("victreebel", 46)), 1, 70),
          )),
    Route("route_15", "Route 15", ROUTE_15, maps=3, towns=("route_15", "fuchsia"), boss=True,
          boss_group=(("victreebel", 52), ("vileplume", 48), ("weepinbell", 47), ("venomoth", 48)), boss_scale=2,
          trainer="Thornwood Gang", boss_loot=MID_BOSS,
          trainers=(
              Trainer("route_15_bird_keeper", "Shore Wings", (("pidgeotto", 47), ("pidgeotto", 47)), 0, 25),
              Trainer("route_15_jr_trainer", "Tide Pool Pals", (("tentacool", 46), ("seaking", 47)), 0, 20),
              Trainer("route_15_biker", "Exhaust Pipes", (("weezing", 47), ("grimer", 46)), 1, 20),
              Trainer("route_15_beauty", "Moonlight Duo", (("clefable", 48), ("wigglytuff", 47)), 1, 70),
              Trainer("route_15_bird_keeper_2", "Last Gust", (("fearow", 48), ("pidgeot", 48)), 2, 25),
          )),
    # Saffron City's gates (quest "saffron_gates": open once the Soul Badge
    # is won and a guard has heard what's going on in Silph Co.): short walks
    # through the gatehouses from Route 5 (north), Route 6 (south), the
    # Route 8 Gate (east) and, by Route 7, Celadon City (west).
    Route("saffron_north", "Saffron Gate", ROUTE_7, maps=1, towns=("route_5", "saffron"), wild=False, cols=34,
          needs=("saffron_gates", "done"), blocked=SAFFRON_SHUT),
    Route("saffron_south", "Saffron Gate", ROUTE_7, maps=1, towns=("saffron", "route_6"), wild=False, cols=34,
          needs=("saffron_gates", "done"), blocked=SAFFRON_SHUT),
    Route("saffron_east", "Saffron Gate", ROUTE_7, maps=1, towns=("saffron", "route_8_gate"), wild=False, cols=34,
          needs=("saffron_gates", "done"), blocked=SAFFRON_SHUT),
    Route("route_7", "Route 7", ROUTE_7, maps=1, towns=("celadon", "saffron"), wild=False, cols=44,
          needs=("saffron_gates", "done"), blocked=SAFFRON_SHUT),
    # Silph Co. (quest "silph_co"), as in Red/Blue: Team Rocket has taken the
    # tower. A Rocket holding the Card Key bars 5F, the rival waits on 7F,
    # and the Rocket Boss holds the President's office at the top (the
    # Persian again, with Team Rocket's heavy hitters).
    Route("silph_co", "Silph Co.", SILPH_CO, maps=6, towns=("saffron", "saffron"),
          boss_chest="battle", boss_loot=MID_BOSS, wild=False, building="Silph Co.",
          needs=("silph_co", "started"),
          blocked="Silph Co.'s doors are locked tight. Through the glass, men in black pace the lobby.",
          rooms=(
              Room("1f", "1F", 70, (Stair("out", "saffron", 0), Stair("up", "3f", 1))),
              Room("3f", "3F", 90, (Stair("down", "1f", 0.05), Stair("up", "5f", 0.95))),
              Room("5f", "5F", 90, (Stair("down", "3f", 0.05), Stair("up", "7f", 0.95))),
              Room("7f", "7F", 90, (Stair("down", "5f", 0.05), Stair("up", "9f", 0.95)),
                   folk=((0.3, Folk("silph_worker", "Silph Worker", "chansey", 0, (
                       "You came to help? Bless you! The Rockets locked us all in the meeting rooms.",
                       "They're after the President, and his Master Ball. He's up on 11F. Please hurry!",
                   ))),)),
              Room("9f", "9F", 90, (Stair("down", "7f", 0.05), Stair("up", "11f", 0.95))),
              # (the Boss guards the President's office, and the way back down)
              Room("11f", "President's Office", 50, (Stair("down", "9f", 0.1), Stair("out", "saffron", 1)),
                   wall="silph_office.png",
                   boss_group=(("persian", 54), ("nidoking", 51), ("nidoqueen", 51), ("kangaskhan", 51)),
                   trainer="Rocket Boss", prize=99),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("silph_lobby", "Lobby Guards", (("raticate", 48), ("golbat", 48)), 0, 30),
              Trainer("silph_3f_1", "Rocket Gang", (("koffing", 48), ("grimer", 48), ("arbok", 48)), 1, 30),
              Trainer("silph_3f_2", "Rocket Gang", (("machoke", 49), ("hypno", 49)), 1, 30),
              Trainer("silph_card_key_rocket", "Card Key Guard", (("weezing", 51), ("golbat", 50), ("arbok", 50)),
                      2, 30, first=True, blocks=True, boss_loot=True),
              Trainer("silph_5f", "Rocket Gang", (("primeape", 49), ("raticate", 49)), 2, 30),
              Trainer("silph_rival", "Rival", (("pidgeot", 50), ("growlithe", 49), ("kadabra", 49),
                                              (RIVAL_STARTER_FINAL, 52)), 3, 35, first=True, blocks=True,
                      boss_loot=True),
              Trainer("silph_7f", "Rocket Gang", (("golbat", 50), ("weezing", 50)), 3, 30),
              Trainer("silph_9f_1", "Rocket Gang", (("machoke", 50), ("primeape", 50), ("arbok", 50)), 4, 30),
              Trainer("silph_9f_2", "Rocket Elite", (("persian", 51), ("hypno", 51)), 4, 30),
          )),
    # The Saffron Gym (quest "marsh_badge"), as in Red/Blue: Sabrina's hall
    # of warp pads (`puzzle` "psychic", scenes/psychic_pads.py): barriers cut
    # the walk into sections, and only the right pads lead on. Then her
    # psychics in the arena, fought by three: two waves, then a giant
    # Alakazam with Gen 1 Sabrina's Kadabra, Mr. Mime and Venomoth.
    Route("saffron_gym", "Saffron Gym", SAFFRON_GYM, maps=1, towns=("saffron", "saffron"), boss=True,
          boss_group=(("alakazam", 53), ("kadabra", 49), ("mr_mime", 49), ("venomoth", 50)), boss_scale=2,
          trainer="Mind Circle", boss_chest="fancy", prize=99, boss_loot=MID_BOSS,
          waves=(Wave("Psychic Trainees", (("drowzee", 48), ("kadabra", 47), ("hypno", 48)), 25),
                 Wave("Mind Readers", (("mr_mime", 48), ("venomoth", 49)), 30)),
          wave_team=3, wild=False, building="Saffron Gym", cols=96, puzzle="psychic",
          needs=("marsh_badge", "active"),
          blocked="Sabrina's gym. The doors won't budge: a strange force holds them shut. A sign: \"Closed while "
                  "the city is in danger.\"",
          blocked_done="Alakazam: ...I foresaw your return. The Marsh Badge shines on you. Sabrina is pleased."),
    # Saffron's Fighting Dojo (quest "fighting_dojo"), as in Red/Blue: one
    # long hall of black belts' bands, and the Karate Master (a giant Machamp
    # stands in) at its end. Hitmonlee and Hitmonchan wait by the door: beat
    # the master, and one of them joins (the player's pick).
    Route("fighting_dojo", "Fighting Dojo", FIGHTING_DOJO, maps=1, towns=("saffron", "saffron"),
          boss_chest="battle", boss_loot=MID_BOSS, boss_scale=2, wild=False, building="Fighting Dojo",
          needs=("fighting_dojo", "started"),
          blocked="The Fighting Dojo. Nobody's training: the master marched into Silph Co. to throw the Rockets "
                  "out, and hasn't come back.",
          rooms=(
              Room("hall", "Dojo Hall", 84, (Stair("out", "saffron", 0), Stair("out", "saffron", 1)),
                   boss_group=(("machamp", 63), ("primeape", 59), ("machoke", 59), ("hitmonchan", 58)),
                   trainer="Karate Master", prize=99,
                   folk=((0.12, Folk("dojo_hitmonlee", "Hitmonlee", "hitmonlee", 0, (
                       "Hyah! I am the master's kicking student. Beat him, and you may train with me!",
                       "My legs stretch further than you think. Hyah!",
                   ), gone_after="fighting_dojo")),
                         (0.2, Folk("dojo_hitmonchan", "Hitmonchan", "hitmonchan", 0, (
                       "Hup hup! I'm the master's boxing student. Beat him, and I'll fight at your side!",
                       "Fire Punch, Ice Punch, Thunder Punch: I've got a punch for everyone. Hup!",
                   ), gone_after="fighting_dojo")))),
          ),
          trainers=(
              Trainer("dojo_belt_1", "White Belts", (("machop", 50), ("mankey", 50), ("machop", 50)), 0, 25),
              Trainer("dojo_belt_2", "Brown Belts", (("primeape", 51), ("machoke", 50)), 0, 25),
              Trainer("dojo_belt_3", "Black Belts", (("machoke", 52), ("primeape", 51), ("hitmonlee", 50)), 0, 25),
          )),
    # Route 2's north end, from the cave up to Pewter City: a short walk.
    Route("route_2_north", "Route 2", ROUTE_2, maps=1, towns=("pewter", "route_2"), wild=False, cols=40),
]}


# --- trials --------------------------------------------------------------------
# A starter's evolution trial (quest "Coming of Age"): the elder in Pewter
# City sends it alone through waves of Pokémon its type beats, then a giant
# of its own next form.

def _trial(starter: str, name: str, theme: Theme, waves: tuple[Wave, ...], master: str, level: int = 16,
           town: str = "pewter", folk: str = "pewter_elder") -> Route:
    """A solo trial for `starter` (any species about to evolve): its waves,
    then a giant `master` at `level`; walked by talking to `folk` in `town`."""
    line = (starter, EVOLUTIONS[starter].into)
    return Route(f"trial_{starter}", name, theme, maps=1, towns=(town, town), boss=True,
                 boss_group=((master, level),), boss_scale=2, trainer="Trial Master", boss_chest="battle",
                 waves=waves, wave_team=1, wave_species=line, wild=False, folk=folk, cols=30)


ROUTES.update({r.key: r for r in [
    _trial("bulbasaur", "Trial of Leaves", FOREST, (
        Wave("Mud Diggers", (("diglett", 11), ("sandshrew", 11)), 0),
        Wave("Stone Rollers", (("geodude", 12), ("geodude", 12)), 0)), "ivysaur"),
    _trial("charmander", "Trial of Flame", MT_MOON, (
        Wave("Crawler Nest", (("caterpie", 11), ("weedle", 11)), 0),
        Wave("Spore Grove", (("paras", 12), ("paras", 12)), 0)), "charmeleon"),
    _trial("squirtle", "Trial of Tides", ROUTE_22, (
        Wave("Stone Rollers", (("geodude", 11), ("geodude", 11)), 0),
        Wave("Rock Burrowers", (("diglett", 12), ("geodude", 12)), 0)), "wartortle"),
    # Abra -> Kadabra (quest evolve_kadabra, Cerulean's Kadabra): Poison
    # Pokémon, which Psychic moves hit hard.
    _trial("abra", "Trial of Mind", ROUTE_25, (
        Wave("Night Swarm", (("venonat", 18), ("venonat", 18)), 0),
        Wave("Cave Biters", (("zubat", 19), ("ekans", 19)), 0)), "kadabra", level=20,
        town="cerulean", folk="cerulean_kadabra"),
    # The starters' last evolutions (quests master_<form>, the master in
    # Celadon's west end) and Pidgeot's (quest evolve_pidgeot, Celadon's
    # Pidgeot): harder solo trials, ending with a giant of the final form.
    _trial("ivysaur", "Trial of the Great Tree", FOREST, (
        Wave("Stone Wall", (("graveler", 29), ("onix", 30)), 0),
        Wave("Tide Pool", (("golduck", 30), ("seaking", 30)), 0)), "venusaur", level=29,
        town="celadon_west", folk="celadon_master"),
    _trial("charmeleon", "Trial of the Inferno", MT_MOON, (
        Wave("Silk Spinners", (("venomoth", 29), ("parasect", 30)), 0),
        Wave("Thorn Hedge", (("weepinbell", 30), ("gloom", 30)), 0)), "charizard", level=29,
        town="celadon_west", folk="celadon_master"),
    _trial("wartortle", "Trial of the Deep", CERULEAN_GYM, (
        Wave("Rock Crew", (("graveler", 29), ("onix", 30)), 0),
        Wave("Blaze Pack", (("growlithe", 30), ("growlithe", 30)), 0)), "blastoise", level=30,
        town="celadon_west", folk="celadon_master"),
    _trial("pidgeotto", "Trial of the Skies", ROUTE_25, (
        Wave("Bug Swarm", (("venomoth", 29), ("butterfree", 29)), 0),
        Wave("Garden Pests", (("paras", 30), ("bellsprout", 30)), 0)), "pidgeot", level=28,
        town="celadon", folk="celadon_pidgeot"),
]})


# --- the feud on Route 22 ------------------------------------------------------
# Quests feud_pidgey / feud_spearow: Viridian City's Pidgeotto or Fearow
# sends the player to the other side's home ground (a map full of them),
# where its leader waits, giant, with two of its flock.

def _feud(key: str, name: str, area: Theme, species: str, leader: str, band: str, folk: str,
          levels: tuple[int, int], town: str = "viridian") -> Route:
    """A home ground: a map full of `species`, its giant `leader` waiting with
    two of them; walked by talking to `folk` in `town`. `levels`: the
    leader's and its flock's (the Fearow, far stronger than a Pidgeotto,
    comes in lower)."""
    lead, flock = levels
    theme = replace(area, key=key, decor=area.decor_key, pool=(PoolEntry(species, 1, (flock - 1, flock + 1)),),
                    group_sizes=((2, 60), (3, 40)))
    return Route(key, name, theme, maps=1, towns=(town, town), boss=True,
                 boss_group=((leader, lead), (species, flock), (species, flock)), boss_scale=2, trainer=band,
                 boss_chest="battle", prize=20, folk=folk)


ROUTES.update({r.key: r for r in [
    _feud("feud_beak_gang", "Beak Gang Roost", ROUTE_22, "spearow", "fearow", "Beak Gang", "viridian_pidgeotto",
          (17, 14)),
    _feud("feud_sky_flock", "Sky Flock Meadow", MEADOW, "pidgey", "pidgeotto", "Sky Flock", "viridian_fearow",
          (21, 17)),
    # Evolution quests' home grounds (quests evolve_beedrill, evolve_raticate).
    _feud("hive_queen", "Beedrill Thicket", FOREST, "kakuna", "beedrill", "Hive Queen", "pewter_beedrill",
          (13, 11), town="pewter"),
    _feud("rat_den", "Rat King's Burrows", MEADOW, "rattata", "raticate", "Rat King's Gang", "viridian_rattata",
          (23, 19)),
    _feud("horn_hollow", "Horn Hollow", ROUTE_22, "nidoran_m", "nidorino", "Horn Brothers", "viridian_nidorino",
          (19, 15)),
    # (quests evolve_golbat, evolve_arbok, evolve_persian, evolve_machoke; a
    # pair a few levels up wins about 55-60%: tools/balance_sim.py-style runs.
    # The Persian, fast and hard-hitting, comes in lower.)
    _feud("golbat_roost", "Golbat Roost", MT_MOON, "zubat", "golbat", "Night Swarm", "route_6_golbat",
          (27, 22), town="route_6"),
    _feud("snake_pit", "Snake Pit", ROUTE_4, "ekans", "arbok", "Coil Clan", "route_4_arbok", (26, 22),
          town="route_4"),
    _feud("alley_cats", "Alley of Cats", ROUTE_6, "meowth", "persian", "Alley Cats", "vermilion_persian",
          (31, 27), town="vermilion"),
    _feud("training_grounds", "Training Grounds", ROUTE_9, "machop", "machoke", "Iron Lifters", "lavender_machoke",
          (33, 28), town="lavender"),
    # (quests evolve_sandslash, evolve_parasect, evolve_graveler, evolve_hypno;
    # tuned like the four above: about 55-63%. Hypno's band, with Hypnosis,
    # comes in lower; Graveler's, hard to dent, higher.)
    _feud("spike_burrows", "Spike Burrows", ROUTE_3, "sandshrew", "sandslash", "Spike Pack", "mt_moon_sandslash",
          (30, 25), town="mt_moon"),
    _feud("mushroom_hollow", "Mushroom Hollow", FOREST, "paras", "parasect", "Spore Colony", "route_5_parasect",
          (31, 25), town="route_5"),
    _feud("rumbling_quarry", "Rumbling Quarry", DIGLETTS_CAVE, "geodude", "graveler", "Boulder Rollers",
          "route_10_graveler", (35, 28), town="route_10"),
    _feud("dreamers_hollow", "Dreamer's Hollow", ROUTE_11, "drowzee", "hypno", "Dream Eaters", "route_11_hypno",
          (29, 23), town="route_11"),
    # (quests evolve_primeape, evolve_electrode, evolve_venomoth,
    # evolve_golduck; tuned like the eight above, about 56-60%. Primeape's
    # band, hard-hitting, comes in lower; Electrode's, which may blow
    # itself up, higher.)
    _feud("brawlers_ring", "Brawlers' Ring", ROUTE_8, "mankey", "primeape", "Rage Brawlers", "route_8_primeape",
          (31, 26), town="route_8_gate"),
    _feud("static_field", "Static Field", ROUTE_9, "voltorb", "electrode", "Spark Rollers", "route_10_electrode",
          (38, 33), town="route_10"),
    _feud("moth_glade", "Moth Glade", FOREST, "venonat", "venomoth", "Dust Wings", "route_24_venomoth",
          (37, 31), town="route_24"),
    _feud("duck_pond", "Headache Pond", ROUTE_6, "psyduck", "golduck", "Headache Club", "cerulean_golduck",
          (39, 33), town="cerulean"),
    # (quests evolve_gloom, evolve_weepinbell: Route 24/25's grass lines)
    _feud("stench_patch", "Stench Patch", ROUTE_25, "oddish", "gloom", "Stench Patch", "cerulean_gloom",
          (26, 21), town="cerulean"),
    _feud("pitcher_grove", "Pitcher Grove", ROUTE_24, "bellsprout", "weepinbell", "Vine Lashers",
          "route_24_weepinbell", (26, 21), town="route_24"),
]})


# --- evolution stones ----------------------------------------------------------
# One quest per stone (quests leaf_stone, moon_stone, thunder_stone), each
# walked by talking to its giver, after the Rainbow Badge. Each place is
# themed on its stone and fights a giant leader's band at the end.

ROUTES.update({r.key: r for r in [
    # The Leaf Stone: the Celadon Gym's overgrown back wing, thick with
    # spores (as in the gym, more of them), two waves of Grass Pokémon fought
    # by three with no healing, then a giant Exeggutor's band.
    Route("celadon_garden", "Overgrown Wing", replace(CELADON_GYM, key="celadon_garden", decor="celadon_gym"),
          maps=1, towns=("celadon_square", "celadon_square"), boss=True,
          boss_group=(("exeggutor", 40), ("victreebel", 38), ("vileplume", 38)), boss_scale=2, trainer="Overgrowth",
          boss_chest="battle", prize=40, boss_loot=MID_BOSS,
          waves=(Wave("Tangled Vines", (("tangela", 36), ("weepinbell", 36), ("gloom", 36)), 0),
                 Wave("Spore Patch", (("parasect", 37), ("exeggcute", 37), ("gloom", 37)), 0)),
          wave_team=3, wild=False, cols=64, puzzle="spores", folk="celadon_oddish"),
    # The Moon Stone: Mt. Moon's crater, under the night sky, pitch dark but
    # for Flash's light; Clefairy everywhere (Sing, Metronome...), and a giant
    # Clefable dancing round the stone with its two Clefairy.
    Route("mt_moon_crater", "Moonlit Crater",
          replace(MT_MOON, key="mt_moon_crater", decor="mt_moon", dark=True,
                  pool=(PoolEntry("clefairy", 5, (36, 38)), PoolEntry("golbat", 2, (36, 38)),
                        PoolEntry("graveler", 1, (36, 38))),
                  group_sizes=((2, 50), (3, 50))),
          maps=1, towns=("mt_moon", "mt_moon"), boss=True,
          boss_group=(("clefable", 45), ("clefairy", 42), ("clefairy", 42), ("clefairy", 41)), boss_scale=2, trainer="Moon Dancers",
          boss_chest="battle", prize=40, boss_loot=MID_BOSS, cols=70, folk="mt_moon_clefairy"),
    # The Thunder Stone: the abandoned Power Plant, its loose current
    # crackling over the floor (`puzzle` "sparks": paralysis), full of wild
    # Electric Pokémon, and a giant Electabuzz's gang at the generator.
    Route("power_plant", "Power Plant",
          replace(VERMILION_GYM, key="power_plant", name="Power Plant", decor="vermilion_gym",
                  pool=(PoolEntry("voltorb", 3, (36, 38)), PoolEntry("magnemite", 3, (36, 38)),
                        PoolEntry("magneton", 1, (37, 39)), PoolEntry("electrode", 1, (37, 39))),
                  group_sizes=((2, 50), (3, 50))),
          maps=1, towns=("route_10", "route_10"), boss=True,
          boss_group=(("electabuzz", 45), ("magneton", 41), ("electrode", 41)), boss_scale=2,
          trainer="Live Wire Gang", boss_chest="battle", prize=40, boss_loot=MID_BOSS, cols=70, puzzle="sparks",
          folk="route_10_voltorb"),
]})


# --- recruitment -------------------------------------------------------------

@dataclass(frozen=True)
class Recruit:
    """A Pokémon that can be recruited: once `needed` of its line are
    defeated, its recruitment quest opens at the Recruitment Centers. Its
    map looks like `area` (where it lives), full of it around `level`; the
    boss, a giant one at `level` + 3, joins the party when beaten."""
    species: str   # the line's first species
    needed: int
    area: Theme
    level: int

    @property
    def route_key(self) -> str:
        return f"recruit_{self.species}"

    @property
    def boss_level(self) -> int:
        return self.level + 3


# The story's routes with wild Pokémon, in the order the story walks them:
# a collect step's items drop on its route and on every later one
# (`quests.won_battle`), so they don't need one route, and earlier
# (easier) ones don't count.
STORY_ORDER = ("route_1", "route_22", "viridian_forest", "route_3", "mt_moon_cave", "route_4_east", "nugget_bridge",
               "route_25", "route_5_south", "underground_path", "route_6_south", "route_11", "digletts_cave",
               "route_9", "rock_tunnel", "route_8", "underground_west", "route_16", "route_12", "skate_road", "route_18_east",
               "route_13", "route_14", "route_15", "silph_co")


def from_route(first: str, route: str) -> bool:
    """Whether `route` is `first` or comes after it in `STORY_ORDER`."""
    return route in STORY_ORDER and first in STORY_ORDER and STORY_ORDER.index(route) >= STORY_ORDER.index(first)


RECRUIT_BUILDING = "Recruitment Center"

# Every line met up to Pewter City, on Route 3, in Mt. Moon and on Routes
# 24 and 25 (rare ones need fewer defeats). Starters and others come by
# their own quests later.
RECRUITS = {r.species: r for r in [
    Recruit("pidgey", 10, MEADOW, 6),
    Recruit("rattata", 10, MEADOW, 6),
    Recruit("caterpie", 10, FOREST, 8),
    Recruit("weedle", 10, FOREST, 8),
    Recruit("pikachu", 4, FOREST, 10),
    Recruit("spearow", 10, ROUTE_22, 9),
    Recruit("nidoran_f", 10, ROUTE_22, 9),
    Recruit("nidoran_m", 10, ROUTE_22, 9),
    Recruit("sandshrew", 10, ROUTE_3, 14),
    Recruit("ekans", 10, ROUTE_3, 14),
    Recruit("jigglypuff", 8, ROUTE_3, 14),
    Recruit("zubat", 10, MT_MOON, 17),
    Recruit("paras", 8, MT_MOON, 17),
    Recruit("clefairy", 4, MT_MOON, 17),
    Recruit("oddish", 10, ROUTE_24, 19),
    Recruit("bellsprout", 10, ROUTE_24, 19),
    Recruit("abra", 4, ROUTE_24, 19),
    Recruit("venonat", 10, ROUTE_25, 20),
    Recruit("meowth", 10, ROUTE_5, 21),
    Recruit("mankey", 10, ROUTE_5, 21),
    Recruit("diglett", 8, UNDERGROUND, 22),
    Recruit("psyduck", 6, ROUTE_6, 23),
    Recruit("drowzee", 8, ROUTE_11, 27),
    Recruit("voltorb", 5, ROUTE_9, 30),
    Recruit("geodude", 10, ROCK_TUNNEL, 31),
    Recruit("machop", 8, ROCK_TUNNEL, 31),
    Recruit("onix", 4, ROCK_TUNNEL, 32),
    Recruit("growlithe", 6, ROUTE_8, 33),
]}


def _recruit_route(r: Recruit) -> Route:
    theme = replace(r.area, key=f"recruit_{r.species}", decor=r.area.decor_key,
                    pool=(PoolEntry(r.species, 1, (r.level - 2, r.level)),),
                    group_sizes=((2, 50), (3, 50)))  # a map full of them
    # (No `towns`: walked from any Recruitment Center, and back to it.)
    return Route(r.route_key, f"{SPECIES[r.species].name} Grounds", theme, maps=1, towns=(), boss=True,
                 boss_group=((r.species, r.boss_level), (r.species, r.level), (r.species, r.level)), boss_scale=2,
                 boss_chest="", building=RECRUIT_BUILDING)


ROUTES.update({r.route_key: _recruit_route(r) for r in RECRUITS.values()})


@dataclass
class Instance:
    route: Route
    destination: str  # the town the last map's doorway leads into
    seed: int = field(default_factory=lambda: random.randrange(1 << 30))
    index: int = 0    # the map (a dungeon: the room) the player is on
    came_from: str = ""  # a dungeon: the town it was entered from (it starts in the room with that doorway)
    # A dungeon: what's been beaten and opened in rooms left during this trip
    # (room index as a string -> OverworldScene.room_state()).
    rooms: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        if self.route.rooms and self.came_from:
            self.index = self.room_index(self.came_from)

    def room_index(self, to: str) -> int:
        """The room with a stair or doorway to `to` (a room or town key)."""
        return next(i for i, room in enumerate(self.route.rooms) if any(s.to == to for s in room.stairs))

    @property
    def room(self) -> Room | None:
        return self.route.rooms[self.index] if self.route.rooms else None

    @property
    def theme(self) -> Theme:
        room, theme = self.room, self.route.theme
        if room and room.wall:  # (a room with a look of its own)
            theme = replace(theme, cave=replace(theme.cave, wall=room.wall),
                            backdrop=replace(theme.backdrop, art=room.wall))
        if room and room.pool:  # (... or Pokémon of its own)
            theme = replace(theme, pool=room.pool)
        return theme

    @property
    def maps(self) -> int:
        return self.route.maps

    @property
    def final(self) -> bool:
        return self.index == self.maps - 1

    def level(self) -> Level:
        """The current map (the same one every time for the same run and index)."""
        room = self.room
        if room:  # laid out the same every time; Pokémon new every trip
            level = generate(self.theme, zlib.crc32(f"{self.route.key}/{room.key}".encode()),
                             final=bool(room.boss_group), cols=room.width,
                             stairs=tuple(s.at for s in room.stairs) + tuple(at for at, _ in room.folk),
                             wide=tuple(s.at for s in room.stairs if s.to in room.boulders))
            level.stairs = level.stairs[:len(room.stairs)]  # (the rest is flat ground for its folk)
            level.folk_cols = [stair_col(at, level.cols) for at, _ in room.folk]
            rng = random.Random(self.seed * 101 + self.index)
            for spawn in level.spawns:
                spawn.encounter = encounter(self.theme, rng)
            if level.boss:
                level.boss.encounter = list(room.boss_group)
            if layout_of(room.puzzle):
                carve(level, layout_of(room.puzzle))
            return level
        level = generate(self.theme, self.seed * 101 + self.index, final=self.final and self.route.boss,
                         cols=self.route.cols or None)
        if level.boss and self.route.boss_group:
            level.boss.encounter = list(self.route.boss_group)
        return level


from . import tower  # noqa: E402,F401  (the Battle Tower's floors join ROUTES)
