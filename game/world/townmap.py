"""The Town Map (M on a map, `scenes/town_map.py`): Kanto as a schematic of
its towns and the routes between them, as far as the player has been
(`Game.visited`), with where they are and what quests want where.

Places are the towns (`NODES`, by grid position; Celadon's three parts are
one) and the routes between them (`EDGES`: a straight line, or a path of
points; caves and tunnels are drawn as such). Gyms, dungeons in a town and
quests' home grounds belong to their town's place.

What shows: a visited place; and, dimmed and unnamed, a route leading out
of a visited town, and the town at its far end.
"""

from __future__ import annotations

import re

from dataclasses import dataclass

from ..mechanics.pokemon import SPECIES
from . import quests
from .instance import ROUTES, Route
from .quests import QUESTS
from .towns import TOWNS

# Grid positions of the towns (x right, y down; drawn GRID px apart).
NODES: dict[str, tuple[float, float]] = {
    "pallet": (2, 14), "viridian": (2, 10), "pewter": (2, 4), "route_2": (5, 6),
    "mt_moon": (6, 2), "route_4": (9, 2), "cerulean": (12, 2), "route_24": (12, 0),
    "sea_cottage": (16, 0), "route_5": (12, 5), "route_6": (12, 10), "vermilion": (12, 13),
    "route_11": (15.5, 13), "route_10": (17, 2), "lavender": (17, 7.5), "route_8_gate": (14.5, 7.5),
    "celadon": (7.5, 7.5), "route_16": (3.6, 7.5), "route_18": (4.6, 13.2),
    "fuchsia": (8.5, 13.6), "silence_bridge": (14.5, 15.0), "route_15": (11.5, 15.0),
    "saffron": (12, 7.5),
}
# The cities' names on the map: (dx, dy) from their spot in logical px, and alignment.
CITY_LABELS = {"pallet": (8, -6, "left"), "viridian": (8, -6, "left"), "pewter": (8, -6, "left"),
               "cerulean": (8, 2, "left"), "vermilion": (8, 2, "left"), "lavender": (0, 8, "center"),
               "celadon": (0, -18, "center"), "fuchsia": (0, -18, "center"),
               "saffron": (0, 8, "center")}
SAFFRON = (12, 7.5)  # shut (drawn, never a place)
GROUP = {"celadon_square": "celadon", "celadon_west": "celadon"}  # parts of one town on the map
PARTS = {"celadon": ("celadon", "celadon_square", "celadon_west")}

# The routes between towns: their key -> the points their line goes through
# (towns' keys or grid points), and how it's drawn ("road", "cave", "tunnel").
EDGES: dict[str, tuple[tuple, str]] = {
    "route_1": (("pallet", "viridian"), "road"),
    "route_22": (("viridian", (0, 10)), "road"),  # (a dead end, west of Viridian)
    "viridian_forest": (("viridian", "pewter"), "road"),
    "route_2_north": (("pewter", "route_2"), "road"),
    "route_3": (("pewter", "mt_moon"), "road"),
    "mt_moon_cave": (("mt_moon", "route_4"), "cave"),
    "route_4_east": (("route_4", "cerulean"), "road"),
    "nugget_bridge": (("cerulean", "route_24"), "road"),
    "route_25": (("route_24", "sea_cottage"), "road"),
    "route_5_south": (("cerulean", "route_5"), "road"),
    "underground_path": (("route_5", (11, 6), (11, 9), "route_6"), "tunnel"),
    "route_6_south": (("route_6", "vermilion"), "road"),
    "route_11": (("vermilion", "route_11"), "road"),
    "digletts_cave": (("route_11", (15.5, 14.2), (5, 14.2), "route_2"), "tunnel"),
    "route_9": (("cerulean", "route_10"), "road"),
    "rock_tunnel": (("route_10", "lavender"), "cave"),
    "route_8": (("lavender", "route_8_gate"), "road"),
    "underground_west": (("route_8_gate", (13.5, 8.8), (9, 8.8), "celadon"), "tunnel"),
    "route_16": (("route_16", "celadon"), "road"),
    "route_12": (("route_11", (17, 13), "lavender"), "road"),
    "skate_road": (("route_16", (3.6, 13.2), "route_18"), "road"),
    "route_18_east": (("route_18", "fuchsia"), "road"),
    "route_13": (("route_11", (17, 13), (17, 15.0), "silence_bridge"), "road"),
    "route_14": (("silence_bridge", "route_15"), "road"),
    "route_15": (("route_15", (9.6, 15.0), "fuchsia"), "road"),
    "saffron_north": (("route_5", "saffron"), "road"),
    "saffron_south": (("saffron", "route_6"), "road"),
    "saffron_east": (("saffron", "route_8_gate"), "road"),
    "route_7": (("celadon", "saffron"), "road"),
}


def place_of_town(town: str) -> str:
    return GROUP.get(town, town)


def place_of_route(route: Route, game) -> str:
    """The place a route is on the map: its own line, or (a gym, a dungeon in
    a town, a home ground) its town's; a recruitment map: the last town."""
    if route.key in EDGES:
        return route.key
    return place_of_town(route.towns[0] if route.towns else game.town)


def here(scene) -> str:
    """The place the player is at (a town or a map scene)."""
    town = getattr(scene, "town", None)  # (a Town, or in a building scene maybe its key)
    if town is not None:
        return place_of_town(town if isinstance(town, str) else town.key)
    instance = getattr(scene, "instance", None)
    if instance is not None:
        return place_of_route(instance.route, scene.game)
    return place_of_town(scene.game.town)  # (inside a building: the town it's in)


def visited(game) -> set[str]:
    """The places the player has been: `Game.visited`, and (older saves)
    what the save shows: routes cleared, towns shopped in, the last town."""
    seen = {place_of_town(k) if k in TOWNS else k for k in game.visited}
    seen |= {k for k in game.cleared if k in EDGES} | {place_of_town(t) for t in game.shop_visits}
    seen.add(place_of_town(game.town))
    for key in [k for k in seen if k in EDGES]:  # (a route walked: both its ends)
        seen |= {p for p in EDGES[key][0] if isinstance(p, str)}
    return seen


@dataclass
class View:
    """What the map shows: places known (named) and glimpsed (dim, unnamed)."""
    known: set[str]
    glimpsed: set[str]

    def shown(self, place: str) -> bool:
        return place in self.known or place in self.glimpsed


def view(game) -> View:
    known = visited(game) & (set(NODES) | set(EDGES))
    glimpsed = set()
    for key, (points, _) in EDGES.items():
        ends = [p for p in points if isinstance(p, str)]
        if key not in known and any(e in known for e in ends):
            glimpsed.add(key)
            glimpsed |= {e for e in ends if e not in known}
    return View(known, glimpsed)


def points(key: str) -> list[tuple[float, float]]:
    """A route's line, in grid units."""
    return [NODES[p] if isinstance(p, str) else p for p in EDGES[key][0]]


def anchor(place: str) -> tuple[float, float]:
    """Where a place's marks go (grid units): a town's spot, a route's middle."""
    if place in NODES:
        return NODES[place]
    pts = points(place)
    if len(pts) == 2:
        return ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
    return ((pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2)


# --------------------------------------------------------------------- quests

FOLK_TOWN = {f.key: t.key for t in TOWNS.values() for f in t.folk}
FOLK = {f.key: f for t in TOWNS.values() for f in t.folk}
BOARDS = {t.key for t in TOWNS.values() if t.board_col is not None}


def _route_of(target: str) -> Route | None:
    """A defeat step's route: the route itself, or the one a map trainer is on."""
    return ROUTES.get(target) or next((r for r in ROUTES.values() if any(t.key == target for t in r.trainers)), None)


def step_places(game, step) -> list[str]:
    """Where an active quest's current step happens, on the map."""
    if step.kind == "talk":
        return [place_of_town(step.town or FOLK_TOWN.get(step.target, game.town))]
    if step.kind == "visit":
        return [place_of_town(step.town)]
    if step.kind == "reach":
        return [place_of_town(step.target)]
    if step.kind == "defeat":
        route = _route_of(step.target)
        return [place_of_route(route, game)] if route else []
    if step.kind == "hunt":
        return hunt_places(step)
    if step.kind in ("collect", "lead_wins"):
        return [step.route] if step.route in EDGES else []
    if step.kind == "hand_in":
        return sorted(BOARDS)
    return []


ALSO_NAMED = {"nugget_bridge": "Route 24"}  # (Nugget Bridge is Route 24's south end)


def _names(key: str) -> set[str]:
    return {ROUTES[key].name} | ({ALSO_NAMED[key]} if key in ALSO_NAMED else set())


def _lives_on(key: str, species: str) -> bool:
    return ROUTES[key].wild and any(e.species == species for e in ROUTES[key].theme.pool)


def hunt_places(step) -> list[str]:
    """A hunt's places: the routes its text names ("Defeat 6 Ekans (Routes 3
    and 4)": "Route 3" and "Route 4"; "(the Underground Path (west))"). Of
    routes sharing a name, those where the species lives; if the text names
    none, every route it lives on."""
    where = step.text[step.text.find("(") + 1:step.text.rfind(")")]
    names = {f"Route {n}" for n in re.findall(r"\d+", where)} if "Route" in where else set()
    names |= {ROUTES[k].name for k in EDGES if not ROUTES[k].name.startswith("Route ") and ROUTES[k].name in where}
    named = [k for k in EDGES if _names(k) & names]
    if "(west)" in where:
        named = [k for k in named if k != "underground_path"]
    by_name: dict[str, list[str]] = {}
    for k in named:
        for n in _names(k) & names:
            by_name.setdefault(n, []).append(k)
    places = []
    for keys in by_name.values():  # (of routes with one name, where it lives: else all of them)
        living = [k for k in keys if _lives_on(k, step.target)]
        places += [k for k in living or keys if k not in places]
    return places or [k for k in EDGES if _lives_on(k, step.target)]


@dataclass(frozen=True)
class Mark:
    text: str    # "!" a quest to take, "◆" a step's place, "?" quests to hand in
    evolve: bool  # an evolution quest's (its own colour)


def marks(game) -> dict[str, list[Mark]]:
    """Each place's quest marks."""
    out: dict[str, list[Mark]] = {}

    def add(place: str, mark: Mark) -> None:
        if mark not in out.setdefault(place, []):
            out[place].append(mark)
    for quest in QUESTS.values():
        if not quests.ready(game, quest):
            continue
        if quest.giver in FOLK_TOWN:
            add(place_of_town(FOLK_TOWN[quest.giver]), Mark("!", bool(quest.evolves)))
        elif quest.board in TOWNS:
            add(place_of_town(quest.board), Mark("!", False))
    for quest in quests.active(game):
        step = quests.current(game, quest.key)
        for place in step_places(game, step):
            add(place, Mark("?" if step.kind == "hand_in" else "◆", bool(quest.evolves)))
    return out


# ---------------------------------------------------------------------- info

def _evolution_wait(game, quest) -> str:
    """Why an evolution quest's giver has nothing yet ("" if they do, or it's
    started or done)."""
    if quests.step(game, quest.key) is not None or quests.ready(game, quest):
        return ""
    species = SPECIES[quest.evolves]
    level = species.evolution.level if species.evolution else 0
    return f"{species.name} at Lv{level}"


def info(game, place: str, view_: View) -> list[tuple[str, str]]:
    """What the selected place has, as (kind, text) lines: kind "head"
    (a heading), "new" / "evolve" (a quest to take; an evolution quest),
    "step" / "step_evolve" (an active quest's step here), "dim" or "" (plain)."""
    lines: list[tuple[str, str]] = []
    if place not in view_.known:
        return [("dim", "Not visited yet.")]
    for quest in quests.active(game):
        step = quests.current(game, quest.key)
        if place in step_places(game, step):
            lines.append(("step_evolve" if quest.evolves else "step", f"{quest.name}: {step.text}"))
    if place in NODES:
        towns = PARTS.get(place, (place,))
        names = [b.name for t in towns for b in TOWNS[t].buildings if b.name and b.name not in ("Your House",)]
        if any(TOWNS[t].board_col is not None for t in towns):
            names.append("Quest board")
        if names:
            lines.append(("head", "Here"))
            lines.append(("", ", ".join(dict.fromkeys(names))))
        folk = [(f, t) for t in towns for f in TOWNS[t].folk]
        offers = []
        for f, _ in folk:
            for quest in QUESTS.values():
                if quest.giver != f.key or quests.is_done(game, quest.key):
                    continue
                name = f.name.replace("{}", SPECIES[f.species].name if f.species in SPECIES else "")
                if quests.ready(game, quest):
                    offers.append(("evolve" if quest.evolves else "new", f"{name}: {quest.name}"))
                elif quest.evolves and (wait := _evolution_wait(game, quest)):
                    offers.append(("dim", f"{name}: evolution quest (bring a {wait})"))
        if offers:
            lines.append(("head", "Townsfolk"))
            lines += offers
    else:
        route = ROUTES[place]
        pool = route.theme.pool if route.wild else ()
        if pool:
            low = min(e.levels[0] for e in pool)
            high = max(e.levels[1] for e in pool)
            lines.append(("head", f"Wild Pokémon  Lv{low}-{high}"))
            lines.append(("", ", ".join(dict.fromkeys(SPECIES[e.species].name for e in pool))))
        if game.cleared[place]:
            lines.append(("dim", f"Walked through {game.cleared[place]}x"))
    return lines


def name(place: str, view_: View) -> str:
    if place not in view_.known:
        return "???"
    return TOWNS[place].name if place in NODES else ROUTES[place].name
