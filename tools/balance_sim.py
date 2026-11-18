"""Simulate battles for balance (headless): the story's major battles at the
party's expected levels, and 1v1 matches between every line.

    python tools/balance_sim.py [--runs N] [--part story|duels|all]

Battles use the real battle code (`BattleScene`). The party picks, each
turn, the move and target with the most expected damage (finishing a
target first); enemies choose at random, as in the game. Bosses' and
trainers' Pokémon wear gear as on the map (`loot.dress`). Gym waves are
fought back to back without healing.
"""

import argparse
import os
import random
import sys
from statistics import mean

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((10, 10))

from game.engine.scene import Scene  # noqa: E402
from game.mechanics.combat import damage  # noqa: E402
from game.mechanics.items import MEDICINE, Bag, Gear  # noqa: E402
from game.mechanics.loot import BOSS_GEAR, TRAINER_GEAR, dress  # noqa: E402
from game.mechanics.pokemon import EVOLUTIONS, SPECIES, Monster  # noqa: E402
from game.mechanics.status import STATUSES  # noqa: E402
from game.mechanics.talents import TREES  # noqa: E402
from game.scenes.battle import Action, BattleScene  # noqa: E402
from game.world.instance import RIVAL_STARTER, RIVAL_STARTER_EVOLVED, ROUTES  # noqa: E402

RIVAL_OF = {"bulbasaur": "charmander", "charmander": "squirtle", "squirtle": "bulbasaur"}


def form(line: str, level: int) -> str:
    """The line's form at `level` (as far as the game has its evolutions)."""
    key = line
    while key in EVOLUTIONS and level >= EVOLUTIONS[key].level and EVOLUTIONS[key].into in SPECIES:
        key = EVOLUTIONS[key].into
    return key


def member(line: str, level: int, talents: bool = True, berry: bool = False) -> Monster:
    m = Monster.create(form(line, level), level, talents="all" if talents else "none")  # (the player's: all picked)
    if berry:  # (the starter's Common Oran Berry)
        m.equip(Gear.roll("Oran Berry", "Common", level=min(level, 5)))
    return m


def _expected(user, move, target) -> float:
    return mean(damage(user, move, target).damage for _ in range(6)) if move.damaging else 0.0


def _choose(b: BattleScene, c) -> Action:
    """The greedy party member: below 35% HP it drinks its best potion (if
    any); else the most expected damage, a knockout first."""
    if c.monster.hp < 0.35 * c.monster.max_hp:
        potions = [MEDICINE[n] for n in ("Super Potion", "Potion") if b.bag.medicine.get(n)]
        if potions:
            return Action(c, potions[0], c)
    best, best_score = None, -1.0
    moves = [c.monster.basic_attack] + c.monster.moves
    for move in moves:
        if not move.damaging or move.charge:
            continue
        for t in b._candidates(c, move):
            exp = _expected(c, move, t)
            score = exp * (1.0 if not move.spread else 1.5) + (1000 if exp >= t.monster.hp else 0)
            if score > best_score:
                best, best_score = Action(c, move, t), score
    # A status move on an enemy without that status is worth a turn too
    # (sleep and paralysis most), while the fight isn't nearly won.
    top = max(best_score, 1.0) if best_score < 1000 else None
    if top is not None:
        for move in moves:
            if move.damaging:
                continue
            for t in b._candidates(c, move):
                if t.enemy == c.enemy:
                    continue
                worth = 0.0
                types = set(t.monster.species.types)
                if (move.status and not t.monster.status and not (set(move.immune) & types)
                        and STATUSES[move.status].immune not in types):
                    worth = {"sleep": 1.6, "paralysis": 1.3, "freeze": 1.6}.get(move.status, 1.0) * move.status_chance / 100
                elif move.seed and not t.seeded_by and "grass" not in t.monster.species.types:
                    worth = 1.1
                elif move.confuse and not t.confused:
                    worth = 0.9 * move.confuse / 100
                score = top * worth * (1.5 if move.spread else 1.0)
                if score > best_score:
                    best, best_score = Action(c, move, t), score
    if best is None:  # only status moves: the basic attack on someone
        move = c.monster.basic_attack
        best = Action(c, move, random.choice(b._candidates(c, move)))
    return best


def fight(party: list[Monster], enemies: list[Monster], trainer: str = "", boss: bool = False,
          max_rounds: int = 40, bag: Bag | None = None, smart_enemies: bool = False) -> tuple[bool, int]:
    """One battle; returns (won, rounds). `smart_enemies`: the enemies pick
    as the party does (for fair duels), not at random as in the game."""
    b = BattleScene(Scene(), party, enemies, bag or Bag(), boss=boss, trainer=trainer)
    if smart_enemies:
        b._enemy_action = lambda e: _choose(b, e)
    for _ in b.script:
        pass
    b.script = None
    rounds = 0
    while not b._over() and rounds < max_rounds:
        b.actions = [_choose(b, c) for c in b.party if c.alive and c.can_choose]
        b._run_round()
        for _ in b.script:
            pass
        b.script = None
        rounds += 1
    return b.won, rounds


def enemy_team(group, boss_rarities, rival_starter: str, boss: bool, trainer: bool, talents: bool = True):
    team = []
    for i, (species, level) in enumerate(group):
        species = {RIVAL_STARTER: rival_starter, RIVAL_STARTER_EVOLVED: EVOLUTIONS[rival_starter].into}.get(species,
                                                                                                          species)
        m = Monster.create(species, level, talents="half" if (boss or trainer) and talents else "none")
        if boss or trainer:
            dress(m, boss_rarities, BOSS_GEAR if boss and i == 0 else TRAINER_GEAR)
        team.append(m)
    return team


# The story's major battles: (name, route key, the party's expected (starter,
# partner) levels, solo?, the potions a player would have on them).
STORY = [
    ("Route 22 rival", "route_22", (9, 0), True, {"Potion": 2}),
    ("Viridian Forest boss", "viridian_forest", (11, 10), False, {"Potion": 3}),
    ("Pewter Gym (2 waves + gang)", "pewter_gym", (14, 13), False, {"Potion": 4}),
    ("Mt. Moon Rocket leader", "mt_moon_cave", (18, 17), False, {"Potion": 2, "Super Potion": 2}),
    ("Cerulean Gym (2 waves + crew)", "cerulean_gym", (21, 20), False, {"Super Potion": 4}),
    ("Nugget Bridge rival", "nugget_bridge", (22, 21), False, {"Super Potion": 3}),
]
PARTNERS = ["pidgey", "rattata", "nidoran_m", "spearow", "caterpie", "pikachu"]


def story_battles(route_key: str, starter: str, levels, solo: bool, talents: bool) -> list:
    """The battles the route's major fight is made of (gym: waves, then the boss)."""
    route = ROUTES[route_key]
    if route_key == "mt_moon_cave":
        room = next(r for r in route.rooms if r.boss_group)
        return [(list(room.boss_group), room.trainer, True)]
    if route_key == "nugget_bridge":
        t = next(t for t in route.trainers if t.key == "nugget_rival")
        return [(list(t.team), "Rival", False)]
    out = [(list(w.team), w.name, False) for w in route.waves]
    out.append((list(route.boss_group), route.trainer, True))
    return out


def run_story(runs: int, talents: bool = True) -> None:
    print(f"\n## Story battles ({'with' if talents else 'without'} talents on either side, {runs} runs per party)\n")
    for name, key, (lv, plv), solo, potions in STORY:
        route = ROUTES[key]
        rarities = route.boss_loot if hasattr(route, "boss_loot") else None
        rows = []
        for starter in ("bulbasaur", "charmander", "squirtle"):
            partners = [None] if solo else PARTNERS
            for partner in partners:
                wins, hp_left = 0, []
                for r in range(runs):
                    random.seed(hash((name, starter, partner, r, talents)) & 0xFFFFFFFF)
                    party = [member(starter, lv, talents, berry=True)] + (
                        [member(partner, plv, talents)] if partner else [])
                    bag = Bag()
                    for n, k in potions.items():
                        bag.add_medicine(n, k)
                    won = True
                    for group, trainer, boss in story_battles(key, starter, (lv, plv), solo, talents):
                        enemies = enemy_team(group, rarities, RIVAL_OF[starter], boss, bool(trainer), talents)
                        for i, e in enumerate(enemies):
                            if boss and i == 0 and getattr(route, "boss_scale", 1) > 1:
                                e.scale = route.boss_scale
                        won, _ = fight(party, enemies, trainer, boss, bag=bag)
                        if not won:
                            break
                    wins += won
                    hp_left.append(sum(m.hp for m in party) / sum(m.max_hp for m in party))
                rows.append((starter, partner or "-", wins / runs, mean(hp_left)))
        print(f"### {name}  (party Lv{lv}" + ("" if solo else f" + Lv{plv}") + ")")
        for starter, partner, wr, hp in rows:
            print(f"  {starter:<10} + {partner:<9}  win {wr:5.0%}   HP left {hp:4.0%}")
        print(f"  all: win {mean(r[2] for r in rows):.0%}")


def run_duels(runs: int, level: int) -> None:
    lines = [k for k, t in TREES.items() if t.tiers]
    print(f"\n## 1v1 duels at Lv{level} ({runs} runs per pair, both sides playing the same)\n")
    score = {k: [] for k in lines}
    for i, a in enumerate(lines):
        for b_ in lines[i + 1:]:
            wins = 0
            for r in range(runs):
                random.seed(hash((a, b_, r, level)) & 0xFFFFFFFF)
                won, _ = fight([member(a, level)], [member(b_, level)], smart_enemies=True)
                wins += won
            score[a].append(wins / runs)
            score[b_].append(1 - wins / runs)
    print("\nTalents' worth: each line's win rate against the field (every other line, with talents),")
    print("with its talents and without them:")
    for k in sorted(lines, key=lambda k: -mean(score[k])):
        bare = []
        for b_ in lines:
            if b_ == k:
                continue
            wins = 0
            for r in range(runs):
                random.seed(hash((k, b_, r, level, "bare")) & 0xFFFFFFFF)
                won, _ = fight([member(k, level, False)], [member(b_, level)], smart_enemies=True)
                wins += won
            bare.append(wins / runs)
        print(f"  {form(k, level):<11} {mean(score[k]):5.0%} with, {mean(bare):5.0%} without")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--part", default="all", choices=("story", "duels", "all"))
    ap.add_argument("--level", type=int, default=25)
    args = ap.parse_args()
    if args.part in ("story", "all"):
        run_story(args.runs, True)
        run_story(args.runs, False)
    if args.part in ("duels", "all"):
        run_duels(args.runs, args.level)


if __name__ == "__main__":
    main()
