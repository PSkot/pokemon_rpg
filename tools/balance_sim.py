"""Simulate battles for balance (headless): the story's major battles at the
party's expected levels, and 1v1 matches between every line.

    python tools/balance_sim.py [--runs N] [--part story|duels|teams|all] [--gear] [--talents-only]

--gear dresses the party as a player would (`player_gear`): for Head, Held
and Worn, the best of 4 random pieces at the area's boss rarities.

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
from game.mechanics.combat import damage, expected_damage  # noqa: E402
from game.mechanics.items import ITEMS, MEDICINE, Bag, Gear  # noqa: E402
from game.mechanics.moves import Move  # noqa: E402
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


def _gear_score(m: Monster) -> float:
    """How good a player would think `m`'s gear is: a standard move's
    expected damage × how much a standard hit takes of its HP (inversely)."""
    offense = expected_damage(m, Move("Standard", 70, "enemy", type=m.species.types[0])) or 1.0
    bulk = m.max_hp * (m.defense + m.base_special * (1 + m.gear_bonus("defense") / 100)) / 2
    return offense * bulk ** 0.8  # (a little more weight on hitting: players lean that way)


def player_gear(m: Monster, rarities, rng: random.Random, tries: int = 4) -> None:
    """Dress `m` as a player would: Head, Held and Worn each the best (by
    `_gear_score`) of `tries` random pieces at `rarities` (item level: its own)."""
    for slot in ("head", "held", "worn"):
        best, best_score = None, -1.0
        for _ in range(tries):
            rarity = rng.choices([r for r, _ in rarities], weights=[w for _, w in rarities])[0]
            item = rng.choice([n for n, i in ITEMS.items() if i.slot == slot and i.drops_at(rarity)])
            piece = Gear.roll(item, rarity, rng, level=m.level)
            old = m.gear.get(slot)
            m.gear[slot] = piece
            score = _gear_score(m)
            if old is not None:
                m.gear[slot] = old
            else:
                m.gear.pop(slot)
            if score > best_score:
                best, best_score = piece, score
        m.equip(best)
        m.hp = m.max_hp


GEAR = False  # --gear


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
    ("Stench Patch (Gloom)", "stench_patch", (23, 22), False, {"Super Potion": 2}),
    ("Pitcher Grove (Weepinbell)", "pitcher_grove", (23, 22), False, {"Super Potion": 2}),
    ("Cerulean burglar", "cerulean_backyard", (24, 23), False, {"Super Potion": 3}),
    ("S.S. Anne rival", "ss_anne", (27, 26), False, {"Super Potion": 3}),
    # (three fight from the S.S. Anne on; the gym is meant to be very hard
    # for two: TEAM=2 tries it with two)
    ("Vermilion Gym (2 waves + battalion)", "vermilion_gym", (29, 28), False, {"Super Potion": 4, "Hyper Potion": 1}),
    ("Diglett's Cave boss", "digletts_cave", (31, 30), False, {"Super Potion": 3, "Hyper Potion": 1}),
    ("Rock Tunnel Hiker Crew", "rock_tunnel", (33, 32), False, {"Super Potion": 3, "Hyper Potion": 1}),
    ("Celadon Gym (2 waves + troupe)", "celadon_gym", (37, 36), False, {"Hyper Potion": 3, "Full Heal": 2}),
    # (the stone quests, after the badge)
    ("Leaf Stone: Overgrown Wing (2 waves + Exeggutor)", "celadon_garden", (39, 38), False,
     {"Hyper Potion": 3, "Full Heal": 2}),
    ("Moon Stone: Moonlit Crater (Clefable)", "mt_moon_crater", (39, 38), False, {"Hyper Potion": 2}),
    ("Thunder Stone: Power Plant (Electabuzz)", "power_plant", (39, 38), False, {"Hyper Potion": 2}),
    ("Rocket Hideout Boss", "rocket_hideout", (40, 39), False, {"Hyper Potion": 3, "Revive": 1}),
]
# How many fight in each story battle: 1 (solo), 2, or 3 from the S.S. Anne on.
TEAM_SIZE = {"Vermilion Gym (2 waves + battalion)": 3, "Diglett's Cave boss": 3, "Rock Tunnel Hiker Crew": 3,
             "Celadon Gym (2 waves + troupe)": 3, "Leaf Stone: Overgrown Wing (2 waves + Exeggutor)": 3,
             "Moon Stone: Moonlit Crater (Clefable)": 3, "Thunder Stone: Power Plant (Electabuzz)": 3,
             "Rocket Hideout Boss": 3}
PARTNERS = ["pidgey", "rattata", "nidoran_m", "spearow", "caterpie", "pikachu"]


def story_battles(route_key: str, starter: str, levels, solo: bool, talents: bool) -> list:
    """The battles the route's major fight is made of (gym: waves, then the boss)."""
    route = ROUTES[route_key]
    if route.rooms:  # a dungeon: its room's boss (Mt. Moon's Rocket leader, the S.S. Anne's rival)
        room = next(r for r in route.rooms if r.boss_group)
        return [(list(room.boss_group), room.trainer, True)]
    if route_key == "nugget_bridge":
        t = next(t for t in route.trainers if t.key == "nugget_rival")
        return [(list(t.team), "Rival", False)]
    out = [(list(w.team), w.name, False) for w in route.waves]
    out.append((list(route.boss_group) + (list(route.boss_extra) if not solo else []), route.trainer, True))
    return out


def run_story(runs: int, talents: bool = True) -> None:
    print(f"\n## Story battles ({'with' if talents else 'without'} talents on either side, {runs} runs per party)\n")
    for name, key, (lv, plv), solo, potions in STORY:
        route = ROUTES[key]
        rarities = route.boss_loot if hasattr(route, "boss_loot") else None
        rows = []
        size = int(os.environ.get("TEAM", TEAM_SIZE.get(name, 1 if solo else 2)))
        for starter in ("bulbasaur", "charmander", "squirtle"):
            # (partners: each one in turn; with three, each one and the next)
            partners = [None] if size == 1 else [
                tuple(PARTNERS[(i + k) % len(PARTNERS)] for k in range(size - 1)) for i in range(len(PARTNERS))]
            for partner in partners:
                wins, hp_left = 0, []
                for r in range(runs):
                    random.seed(hash((name, starter, partner, r, talents)) & 0xFFFFFFFF)
                    party = [member(starter, lv, talents, berry=True)] + [member(p, plv, talents) for p in partner or ()]
                    if GEAR:
                        for m in party:
                            player_gear(m, rarities, random)
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
                rows.append((starter, "+".join(partner) if partner else "-", wins / runs, mean(hp_left)))
        print(f"### {name}  (party Lv{lv}" + ("" if solo else f" + Lv{plv}") + ")")
        for starter, partner, wr, hp in rows:
            print(f"  {starter:<10} + {partner:<19}  win {wr:5.0%}   HP left {hp:4.0%}")
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


def run_teams(runs: int, level: int) -> None:
    """3v3: each line in `runs` random teams of three (two random partners)
    against random teams of three, all with talents, both sides playing the
    same; then the same matchups with that line's talents taken away. Team
    effects show here (spread status, support, Gang Up) as they can't 1v1."""
    lines = [k for k, t in TREES.items() if t.tiers]
    print(f"\n## 3v3 teams at Lv{level} ({runs} random matchups per line, both sides playing the same)\n")
    rows = []
    for k in lines:
        wins, bare = [], []
        for r in range(runs):
            rng = random.Random(hash((k, r, level)) & 0xFFFFFFFF)
            others = [x for x in lines if x != k]
            mates, foes = rng.sample(others, 2), rng.sample(others, 3)
            for with_talents, out in ((True, wins), (False, bare)):
                random.seed(hash((k, r, level, "fight")) & 0xFFFFFFFF)  # (the same fight both ways)
                team = [member(k, level, with_talents)] + [member(x, level) for x in mates]
                won, _ = fight(team, [member(x, level) for x in foes], smart_enemies=True)
                out.append(won)
        rows.append((form(k, level), mean(wins), mean(bare)))
        print(f"  {rows[-1][0]:<11} {rows[-1][1]:5.0%} with, {rows[-1][2]:5.0%} without", flush=True)
    print("\nSorted by the talents' worth (with - without):")
    for name, w, b_ in sorted(rows, key=lambda r: -(r[1] - r[2])):
        print(f"  {name:<11} {w - b_:+5.0%}   ({w:4.0%} with, {b_:4.0%} without)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--part", default="all", choices=("story", "duels", "teams", "all"))
    ap.add_argument("--level", type=int, default=25)
    ap.add_argument("--gear", action="store_true", help="the party wears gear, as a player would")
    ap.add_argument("--talents-only", action="store_true", help="story battles: only with talents")
    args = ap.parse_args()
    global GEAR
    GEAR = args.gear
    if args.part in ("story", "all"):
        run_story(args.runs, True)
        if not args.talents_only:
            run_story(args.runs, False)
    if args.part in ("duels", "all"):
        run_duels(args.runs, args.level)
    if args.part in ("teams", "all"):
        run_teams(args.runs, args.level)


if __name__ == "__main__":
    main()
