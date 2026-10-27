"""Instances: runs through several generated maps of one theme.

A route between two towns (Route 1, ...) is an instance: each trip along it
has its own seed, so it's new every time, and its last doorway leads into
the town at the other end. An instance with a boss ends in an arena where a
boss group guards the way out.

Routes can have trainers (`Route.trainers`): each stands in for one of a
map's wild groups, fights once for good (`Game.trainers`) and pays prize
money. A gym is a route walked from its building, with only trainers.
"""

import random
from dataclasses import dataclass, field

from ..mechanics.loot import COMMON_ONLY, EARLY_BOSS, Rarities
from .level import Level, generate
from .themes import FOREST, MEADOW, PEWTER_GYM, ROUTE_3, ROUTE_22, Theme

# Stands in a boss group for the rival's starter, which depends on the
# player's (`progress.Game.rival_starter`).
RIVAL_STARTER = "rival_starter"


@dataclass(frozen=True)
class Trainer:
    """A trainer on one of a route's maps: beaten once for good. Prize
    money is `prize` × the level of its last Pokémon (Gen 1's rule)."""
    key: str     # unique in the game (saved in Game.trainers once beaten)
    name: str    # shown over the team on the map: "Bug Catcher"
    team: tuple[tuple[str, int], ...]  # (species, level), shown in a row on the map
    map: int     # which of the route's maps it's on
    prize: int   # Gen 1's base prize for its class (Youngster 15, Bug Catcher 10, ...)


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
    # The Pewter Gym, from its building: a Jr. Trainer, then Brock (Gen 1's teams).
    Route("pewter_gym", "Pewter Gym", PEWTER_GYM, maps=1, towns=("pewter", "pewter"), boss=True,
          boss_group=(("geodude", 12), ("onix", 14)), trainer="Brock", boss_chest=False, prize=99,
          trainers=(Trainer("pewter_gym_jr", "Jr. Trainer", (("diglett", 11), ("sandshrew", 11)), 0, 20),),
          wild=False, building="Pewter Gym",
          needs=("boulder_badge", "not_done"),
          blocked="Brock: You already have the Boulder Badge. The road east, Route 3, is open to you!"),
    # Route 3, from Pewter to the foot of Mt. Moon: Gen 1's trainer road.
    Route("route_3", "Route 3", ROUTE_3, maps=3, towns=("pewter", "mt_moon"),
          needs=("boulder_badge", "done"),
          blocked="A boy blocks the way: \"You're a trainer? Brock's looking for challengers! Beat him first!\"",
          trainers=(
              Trainer("route_3_youngster_1", "Youngster", (("rattata", 11), ("ekans", 11)), 0, 15),
              Trainer("route_3_bug_catcher_1", "Bug Catcher", (("caterpie", 10), ("weedle", 10), ("caterpie", 10)),
                      0, 10),
              Trainer("route_3_lass_1", "Lass", (("pidgey", 9), ("pidgey", 9)), 1, 15),
              Trainer("route_3_bug_catcher_2", "Bug Catcher", (("weedle", 9), ("kakuna", 9), ("caterpie", 9),
                                                               ("metapod", 9)), 1, 10),
              Trainer("route_3_youngster_2", "Youngster", (("spearow", 14),), 2, 15),
              Trainer("route_3_lass_2", "Lass", (("jigglypuff", 14),), 2, 15),
          )),
]}


@dataclass
class Instance:
    route: Route
    destination: str  # the town the last map's doorway leads into
    seed: int = field(default_factory=lambda: random.randrange(1 << 30))
    index: int = 0    # the map the player is on

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
        level = generate(self.theme, self.seed * 101 + self.index, final=self.final and self.route.boss)
        if level.boss and self.route.boss_group:
            level.boss.encounter = list(self.route.boss_group)
        return level
