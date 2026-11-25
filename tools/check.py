"""A quick headless check that the game still runs: run it after a change.

    .venv/bin/python tools/check.py           # everything (about a minute)
    .venv/bin/python tools/check.py --quick   # skips the slow parts (every move's effect, full battles)
    .venv/bin/python tools/check.py places quests   # only those sections

Sections:

- imports: every module in game/ imports;
- places: every town, route, gym, dungeon, trial and recruitment ground
  (dev Teleport's list) and a Safari visit loads, runs and draws; on
  maps the player walks right (and jumps) for a few seconds;
- quests: every quest restarts, steps forward to done, back, and resets;
- saves: a game saves and loads back the same (into a temp folder);
- items: random gear at every rarity and slot rolls; medicine and key items add;
- moves: every move is used in a battle scene (its effect too), drawn;
- battles: a few battles played out round by round to a win or a loss;
- safari: both Safari minigames play to the end;
- puzzles: the Saffron Gym's warp pads always lead through to the arena;
  Strength's boulders push off their ladders (and don't without it).

Prints one line per section and every failure with its traceback; exits
non-zero if anything failed.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import random
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
from game import settings  # noqa: E402

WINDOW = pygame.display.set_mode(settings.WINDOW_SIZE)
CANVAS = pygame.Surface(settings.LOGICAL_SIZE)
DT = 1 / 30

failures: list[str] = []


def fail(what: str) -> None:
    failures.append(what)
    print(f"  FAIL {what}")
    traceback.print_exc(limit=6)


def frame(scene) -> None:
    scene.draw(CANVAS)
    pygame.transform.scale(CANVAS, settings.WINDOW_SIZE, WINDOW)
    scene.draw_overlay(WINDOW)


def new_game():
    from game.mechanics.pokemon import Monster
    from game.world.progress import Game
    g = Game.new("charmander")
    g.party = [Monster.create("charizard", 50), Monster.create("pikachu", 45)]
    g.slots = 2
    g.bag.money = 50_000
    return g


# --------------------------------------------------------------- sections

def check_imports() -> int:
    import game
    n = 0
    for info in pkgutil.walk_packages(game.__path__, "game."):
        if info.name == "game.main" or info.name.endswith("__main__"):
            continue
        try:
            importlib.import_module(info.name)
            n += 1
        except Exception:
            fail(f"import {info.name}")
    return n


class _Held:
    """Keys held (for touch.pressed): the right arrow, and Space now and then."""

    def __init__(self):
        self.t = 0

    def __getitem__(self, key):
        return key == pygame.K_RIGHT or (key == pygame.K_SPACE and self.t % 40 < 10)


def check_places() -> int:
    from game.dev import DEV
    from game.engine import touch
    from game.scenes import dev_menu
    held = _Held()
    real = touch.pressed
    touch.pressed = lambda: held
    DEV.skip = DEV.enabled = True  # (walk through packs: no battles start)
    try:
        dests = dev_menu.destinations()
        for value, *_ in dests:
            try:
                scene = dev_menu.teleport(new_game(), value)
                for i in range(90):  # 3 seconds
                    held.t = i
                    scene.update(DT)
                    if scene.next_scene:  # (a doorway or battle: that's fine)
                        break
                frame(scene)
            except Exception:
                fail(f"place {value}")
    finally:
        touch.pressed = real
        DEV.skip = DEV.enabled = False
    return len(dests)


def check_quests() -> int:
    from game.world import quests
    g = new_game()
    for key, q in quests.QUESTS.items():
        try:
            quests.restart(g, key)
            for _ in range(len(q.steps) + 1):
                quests.step_forward(g, key)
            assert quests.is_done(g, key), f"{key} not done after stepping through"
            quests.step_back(g, key)
            assert quests.is_active(g, key), f"{key} not active after a step back"
            quests.reset(g, key)
            assert quests.step(g, key) is None, f"{key} still started after a reset"
        except Exception:
            fail(f"quest {key}")
    return len(quests.QUESTS)


def check_saves() -> int:
    from game import saves
    from game.scenes import dev_menu
    from game.world import quests
    real = saves.SAVE_DIR
    with tempfile.TemporaryDirectory() as tmp:
        saves.SAVE_DIR = Path(tmp)
        try:
            n = 0
            for where in ("town:pallet", "town:celadon", "route:route_1"):
                g = new_game()
                quests.step_forward(g, "oaks_parcel")
                g.kudos["chansey"] = 40
                scene = dev_menu.teleport(g, where)
                for _ in range(10):
                    scene.update(DT)
                name = saves.save(scene)
                info = next(s for s in saves.list_saves() if s.name == name)
                back = saves.load(info)
                frame(back)
                h = back.game
                assert [m.species.key for m in h.party] == [m.species.key for m in g.party], "party"
                assert h.quests == g.quests and h.kudos == g.kudos and h.bag.money == g.bag.money, "state"
                n += 1
        except Exception:
            fail("saves")
        finally:
            saves.SAVE_DIR = real
    return n


def check_items() -> int:
    from game.mechanics.items import KEY_ITEMS, MEDICINE, RARITIES, SLOTS
    from game.scenes import dev_menu
    g = new_game()
    maker = dev_menu.ItemMaker(g.bag)
    maker.item = dev_menu.RANDOM
    n = 0
    for rarity in RARITIES:
        for slot in ["", *SLOTS]:
            maker.rarity, maker.slot, maker.level = rarity, slot, random.choice((5, 30, 60))
            try:
                maker._make()
                n += 1
            except Exception:
                fail(f"random gear {rarity} {slot or 'any'}")
    for item in list(MEDICINE)[:5] + list(KEY_ITEMS)[:5]:
        maker.item = item
        try:
            maker._make()
            n += 1
        except Exception:
            fail(f"item {item}")
    return n


def _battle(party, enemies):
    from game.engine.scene import Scene
    from game.mechanics.items import Bag
    from game.scenes.battle import BattleScene
    b = BattleScene(Scene(), party, enemies, Bag())
    for _ in range(600):
        b.update(DT)
        if not b.script:
            break
    return b


def _run(b, script, limit=900) -> None:
    b.script, b.wait = script, 0.0
    for i in range(limit):
        b.update(DT)
        if i % 3 == 0:
            frame(b)
        if not b.script:
            return


def check_moves() -> int:
    from game.mechanics.moves import MOVES
    from game.mechanics.pokemon import Monster
    from game.scenes import battle as B
    n = 0
    for name, move in MOVES.items():
        try:
            party = [Monster.create("venusaur", 50), Monster.create("pikachu", 50)]
            enemies = [Monster.create("blastoise", 50), Monster.create("rattata", 50)]
            b = _battle(party, enemies)
            user = b.party[0]
            target = b.enemies[0] if move.target == "enemy" else user
            for c in b.everyone:
                c.monster.hp = c.monster.max_hp

            def script():
                if move.charge:
                    yield from b._perform(B.Action(user, move, target))
                yield from b._perform(B.Action(user, move, target))
            _run(b, script())
            n += 1
        except Exception:
            fail(f"move {name}")
    return n


def check_battles() -> int:
    from game.mechanics.pokemon import Monster
    from game.scenes import battle as B
    rng = random.Random(1)
    n = 0
    teams = [(["charizard", "blastoise"], ["onix", "geodude"]), (["pikachu"], ["pidgey", "rattata", "spearow"]),
             (["venusaur", "snorlax", "alakazam"], ["weezing", "koffing", "golbat"])]
    for ours, theirs in teams:
        try:
            b = _battle([Monster.create(s, 30) for s in ours], [Monster.create(s, 28) for s in theirs])
            for _ in range(30):  # rounds
                if b.won or b.lost or not any(c.alive for c in b.enemies):
                    break
                actions = []
                for c in b.everyone:
                    if not c.alive:
                        continue
                    move = rng.choice(c.monster.moves)
                    side = b.party if c.enemy else b.enemies
                    foes = [t for t in side if t.alive]
                    if not foes:
                        break
                    target = rng.choice(foes) if move.target == "enemy" else c
                    actions.append(B.Action(c, move, target))
                _run(b, b._round(actions), limit=3000)
            n += 1
        except Exception:
            fail(f"battle {ours} vs {theirs}")
    return n


def check_safari() -> int:
    from game.engine.scene import Scene
    from game.scenes import safari_games as sg
    from game.world.safari import ZONES
    n = 0
    for cls, species in ((sg.EggCatch, "chansey"), (sg.FruitSlice, "scyther")):
        try:
            g = cls(Scene(), species, ZONES[0].theme.backdrop, lambda s: None, seed=3)
            for i in range(60 * 60):
                g.update(1 / 60)
                if i % 20 == 0:
                    g.pointer((320 + (i % 200) - 100, 200), i % 40 == 0)
                    g.draw(CANVAS)
                if g.over:
                    break
            assert g.over, f"{species}'s game never ended"
            n += 1
        except Exception:
            fail(f"safari {species}")
    return n


def check_puzzles() -> int:
    from game.scenes.overworld import OverworldScene
    from game.world.instance import ROUTES, Instance
    n = 0
    for seed in range(20):
        try:
            scene = OverworldScene(Instance(ROUTES["saffron_gym"], "saffron", seed=seed), new_game())
            hall = scene.hall
            for section in range(len(hall.barriers)):  # (the way on, section by section, by stepping on pads)
                pad = next(p for p in hall.pads if p.section == section and p.to.section > section)
                scene.place_player(pad.x)
                hall.standing_on = None
                to = hall.update(DT, scene.player)
                assert to is not None, f"seed {seed}: the pad in section {section} didn't warp"
                scene.place_player(to)
            assert abs(scene.player.x - hall.arena.x) < 1, f"seed {seed}: didn't reach the arena"
            n += 1
        except Exception:
            fail(f"saffron gym pads, seed {seed}")
    import pygame as pg
    from game.engine import touch
    from game.scenes.boulders import STRENGTH
    real = touch.pressed
    touch.pressed = lambda: type("Held", (), {"__getitem__": lambda self, k: k == pg.K_RIGHT})()
    try:
        for key, route in ROUTES.items():
            for i, room in enumerate(route.rooms):
                for target in room.boulders:
                    for strength in (True, False):
                        try:
                            g = new_game()
                            if strength:
                                g.bag.key_items.append(STRENGTH)
                            scene = OverworldScene(Instance(route, route.towns[1], index=i), g)
                            boulder = scene.boulders.boulders[0]
                            ladder = next(t for s, t in scene.stairs if s.to == target)
                            scene.place_player(boulder.rect.left - 24)
                            for f in range(300):
                                if f % 25 == 0:
                                    scene.jump = True
                                scene.update(DT)
                            free = boulder.rect.left > ladder.x + 12 or boulder.rect.right < ladder.x - 12
                            assert free == strength, f"{key}/{room.key}: ladder free {free} with strength {strength}"
                            n += 1
                        except Exception:
                            fail(f"boulder {key}/{room.key} (strength {strength})")
    finally:
        touch.pressed = real
    return n


SECTIONS = {
    "imports": check_imports, "places": check_places, "quests": check_quests, "saves": check_saves,
    "items": check_items, "moves": check_moves, "battles": check_battles, "safari": check_safari,
    "puzzles": check_puzzles,
}
SLOW = {"moves", "battles"}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quick = "--quick" in sys.argv
    names = args or [s for s in SECTIONS if not (quick and s in SLOW)]
    unknown = [n for n in names if n not in SECTIONS]
    if unknown:
        print(f"Unknown section(s): {', '.join(unknown)}. Sections: {', '.join(SECTIONS)}")
        return 2
    random.seed(0)
    start = time.perf_counter()
    for name in names:
        t = time.perf_counter()
        before = len(failures)
        count = SECTIONS[name]()
        bad = len(failures) - before
        print(f"{name:8s} {count:4d} checked  {'OK' if not bad else f'{bad} FAILED'}  ({time.perf_counter() - t:.1f}s)")
    print(f"\n{'All OK' if not failures else f'{len(failures)} failure(s)'} in {time.perf_counter() - start:.0f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
