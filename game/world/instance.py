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

from ..mechanics.loot import COMMON_ONLY, EARLY_BOSS, Rarities
from ..mechanics.pokemon import SPECIES
from .level import Level, encounter, generate
from .themes import FOREST, MEADOW, MT_MOON, PEWTER_GYM, ROUTE_3, ROUTE_22, PoolEntry, Theme

# Stands in a boss group for the rival's starter, which depends on the
# player's (`progress.Game.rival_starter`).
RIVAL_STARTER = "rival_starter"


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
    boss_chest: bool = True             # beating the boss leaves a chest (else its loot comes with the battle)
    # Its doorways need (quest key, "started" or "done"); `blocked` says why not.
    needs: tuple[str, str] | None = None
    blocked: str = ""
    # Once this quest is done, the boss is this group instead (no trainer).
    boss_after: tuple[str, tuple[tuple[str, int], ...]] | None = None
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

    def other_end(self, town: str) -> str:
        return self.towns[1] if town == self.towns[0] else self.towns[0]


ROUTES = {r.key: r for r in [
    Route("route_1", "Route 1", MEADOW, maps=2, towns=("pallet", "viridian")),
    Route("viridian_forest", "Viridian Forest", FOREST, maps=3, towns=("viridian", "pewter"), boss=True,
          boss_group=(("caterpie", 10), ("metapod", 8), ("kakuna", 8)), boss_scale=2,
          needs=("oaks_parcel", "done"),
          blocked="An old man is lying in the road. He hasn't had his coffee yet, and won't let anyone pass."),
    # A side trip from Viridian and back (Gen 1's first rival battle at its end).
    Route("route_22", "Route 22", ROUTE_22, maps=2, towns=("viridian", "viridian"), boss=True,
          boss_group=(("pidgey", 9), (RIVAL_STARTER, 8)), trainer="Rival", boss_chest=False,
          needs=("rival_22", "started"), blocked="A guard says there's nothing to see on Route 22 for now.",
          boss_after=("rival_22", (("pidgey", 9), ("spearow", 9))), prize=35),
    # The Pewter Gym, from its building: a short walk up to the arena, where
    # the Boulder Gang sends in two waves, then comes itself, led by an Onix
    # (Gen 1's Brock's team).
    Route("pewter_gym", "Pewter Gym", PEWTER_GYM, maps=1, towns=("pewter", "pewter"), boss=True,
          boss_group=(("geodude", 12), ("onix", 14)), trainer="Boulder Gang", boss_chest=False, prize=99,
          waves=(Wave("Boulder Gang Diggers", (("diglett", 10), ("sandshrew", 10)), 20),
                 Wave("Boulder Gang Rollers", (("geodude", 11), ("geodude", 11)), 20)),
          wild=False, building="Pewter Gym", cols=44,
          needs=("boulder_badge", "not_done"),
          blocked="Onix: You already have the Boulder Badge. The road east, Route 3, is open to you!"),
    # Route 3, from Pewter to the foot of Mt. Moon: Gen 1's trainer road.
    Route("route_3", "Route 3", ROUTE_3, maps=3, towns=("pewter", "mt_moon"),
          needs=("boulder_badge", "done"),
          blocked="A Geodude blocks the way: \"The Boulder Gang holds the gym! Beat them first!\"",
          trainers=(
              Trainer("route_3_youngster_1", "Alley Gang", (("rattata", 11), ("ekans", 11)), 0, 15),
              Trainer("route_3_bug_catcher_1", "Crawler Swarm", (("caterpie", 10), ("weedle", 10), ("caterpie", 10)),
                      0, 10),
              Trainer("route_3_lass_1", "Pidgey Flock", (("pidgey", 9), ("pidgey", 9)), 1, 15),
              Trainer("route_3_bug_catcher_2", "Bug Brood", (("weedle", 9), ("kakuna", 9), ("caterpie", 9),
                                                               ("metapod", 9)), 1, 10),
              Trainer("route_3_youngster_2", "Lone Spearow", (("spearow", 14),), 2, 15),
              Trainer("route_3_lass_2", "Singing Jigglypuff", (("jigglypuff", 14),), 2, 15),
          )),
    # Mt. Moon, as in Red/Blue: three ladders down from 1F, two of them to
    # dead ends; the way on goes down to B2F, past Team Rocket, and up to
    # the B1F room with the way out to Route 4.
    Route("mt_moon_cave", "Mt. Moon", MT_MOON, maps=7, towns=("mt_moon", "route_4"), boss_chest=False,
          rooms=(
              Room("1f", "1F", 110, (Stair("out", "mt_moon", 0), Stair("down", "b1_west", 0.3),
                                     Stair("down", "b1_east", 0.55), Stair("down", "b1_nook", 0.85))),
              Room("b1_west", "B1F", 60, (Stair("up", "1f", 0.2), Stair("down", "b2_west", 0.8))),
              Room("b1_nook", "B1F", 44, (Stair("up", "1f", 0.5),)),
              Room("b1_east", "B1F", 70, (Stair("up", "1f", 0.15), Stair("down", "b2", 0.85))),
              Room("b2_west", "B2F", 80, (Stair("up", "b1_west", 0.15),)),
              Room("b2", "B2F", 90, (Stair("up", "b1_east", 0.1), Stair("up", "b1_exit", 1)),
                   boss_group=(("sandshrew", 12), ("rattata", 12), ("zubat", 13)), trainer="Rocket Gang Leader",
                   prize=30),
              Room("b1_exit", "B1F", 50, (Stair("down", "b2", 0.2), Stair("out", "route_4", 1))),
          ),
          trainers=(  # (`map`: the room's place in `rooms`)
              Trainer("mt_moon_bug_catcher", "Stinger Nest", (("weedle", 11), ("kakuna", 11)), 0, 10),
              Trainer("mt_moon_lass", "Moon Clefairy", (("clefairy", 14),), 0, 15),
              Trainer("mt_moon_youngster", "Cave Rats", (("rattata", 10), ("rattata", 10), ("zubat", 10)), 0, 15),
              Trainer("mt_moon_hiker", "Rockslide Clan", (("geodude", 10), ("geodude", 10), ("geodude", 10), ("onix", 11)),
                      3, 35),
              Trainer("mt_moon_rocket_1", "Rocket Gang", (("rattata", 13), ("zubat", 13)), 4, 30),
              Trainer("mt_moon_rocket_2", "Rocket Gang", (("zubat", 12), ("ekans", 12)), 5, 30),
          )),
]}


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


RECRUIT_BUILDING = "Recruitment Center"

# Every line met up to Pewter City, on Route 3 and in Mt. Moon (rare ones need fewer
# defeats). Starters and others come by their own quests later; Oddish and
# Bellsprout (Recruit(..., 6, MEADOW, 8)) come back with Routes 24/25,
# where they live in Red/Blue.
RECRUITS = {r.species: r for r in [
    Recruit("pidgey", 10, MEADOW, 6),
    Recruit("rattata", 10, MEADOW, 6),
    Recruit("caterpie", 10, FOREST, 6),
    Recruit("weedle", 10, FOREST, 6),
    Recruit("pikachu", 4, FOREST, 8),
    Recruit("spearow", 10, ROUTE_22, 8),
    Recruit("nidoran_f", 10, ROUTE_22, 8),
    Recruit("nidoran_m", 10, ROUTE_22, 8),
    Recruit("sandshrew", 10, ROUTE_3, 10),
    Recruit("ekans", 10, ROUTE_3, 10),
    Recruit("jigglypuff", 8, ROUTE_3, 10),
    Recruit("zubat", 10, MT_MOON, 12),
    Recruit("paras", 8, MT_MOON, 12),
    Recruit("clefairy", 4, MT_MOON, 12),
]}


def _recruit_route(r: Recruit) -> Route:
    theme = replace(r.area, key=f"recruit_{r.species}", decor=r.area.decor_key,
                    pool=(PoolEntry(r.species, 1, (r.level - 2, r.level)),),
                    group_sizes=((2, 50), (3, 50)))  # a map full of them
    # (No `towns`: walked from any Recruitment Center, and back to it.)
    return Route(r.route_key, f"{SPECIES[r.species].name} Grounds", theme, maps=1, towns=(), boss=True,
                 boss_group=((r.species, r.boss_level), (r.species, r.level), (r.species, r.level)), boss_scale=2,
                 building=RECRUIT_BUILDING)


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
        return self.route.theme

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
                             final=bool(room.boss_group), cols=room.width, stairs=tuple(s.at for s in room.stairs))
            rng = random.Random(self.seed * 101 + self.index)
            for spawn in level.spawns:
                spawn.encounter = encounter(self.theme, rng)
            if level.boss:
                level.boss.encounter = list(room.boss_group)
            return level
        level = generate(self.theme, self.seed * 101 + self.index, final=self.final and self.route.boss,
                         cols=self.route.cols or None)
        if level.boss and self.route.boss_group:
            level.boss.encounter = list(self.route.boss_group)
        return level
