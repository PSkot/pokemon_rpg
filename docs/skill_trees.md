# Skill trees

How skills work, and every line's tree. Keep this file in step with the
code (`game/mechanics/skills.py`, moves in `game/mechanics/moves.py`).

**Built:** the rules, the Bulbasaur line's tree, its moves in battle, and
the skill tree screen. **Not yet:** the other lines' trees.

### The skill tree screen

Party screen → **S** (`game/scenes/skill_tree.py`). Left: the tree as an
outline, each skill under its parent (modifiers as diamonds), with rank
pips and the equipped moves' keys (F = the basic attack). White = learned,
green = can be learned now, grey = locked. Right: the chosen skill's ranks
(what each does; power now and at the next rank), its requirements (green
= met), and what can be done. Keys: **Enter** spends a point, **E** equips
or unequips a move (4 at most; equip order = keys 2–5 on the map), **R**
resets all points (in towns only, after asking), Left/Right switch
Pokémon. The party screen shows how many points are unspent.

Pokémon don't learn moves at fixed levels. Each evolution line has a
**skill tree**: skills are bought and ranked up with **skill points**. The
tree is built from the line's Gen 1 learnset (and the TMs it could learn),
with Gen 1's learn levels as the pacing.

---

## Rules

### Skill points

- **1 point per level-up.** A Pokémon has `level − 5` points in total (none
  below Lv5), so a new Lv5 starter has 0 and a Lv30 one has 25.
- **Each rank costs 1 point.**
- Points can be reset for free in towns (the Poké Center, later), to try a
  different build.

### Kinds of skills

| Kind | What it is | Ranks |
| --- | --- | --- |
| **Base attack** | Known from the start, rank 1 for free. The first one is the Pokémon's **basic attack** (the Fight command, key 1 on the map). | 1–5 |
| **Move** | A move to use in battle (damage, or a status/support effect). | 1–5 (damaging), 1–3 (status) |
| **Modifier** | A passive skill that changes one move: an added effect, a stronger effect, more targets. Hangs off the move it changes. | 1–3 |

**Ranks of a damaging move:** rank 1 is the Gen 1 power; each rank after
that adds **+15% damage** (rank 5 = ×1.6). Status moves and modifiers say
per rank what they do (see the tree).

### Unlocking

A skill can be bought when **all** of these are true:

1. the Pokémon's **level** is at least the skill's level (Gen 1's learn
   level for learnset moves);
2. its **parent** skill in the tree has at least rank 1;
3. the Pokémon is at least the **evolution stage** the skill needs.
   Evolving opens the stage's part of the tree; skills already bought stay.

### In battle

- **Fight** uses the basic attack (Tackle for Bulbasaur), at its rank.
- **Skills:** up to **4 equipped moves**, like Gen 1's four move slots (keys
  2–5 on the map). Learned moves that aren't equipped can be swapped in
  outside battle.
- Modifiers work on their move automatically.

### Wild Pokémon

They follow the same tree (`SkillTree.auto_build`): they learn every move
their level, parent skills and stage allow (in level order), and equip
their 4 most recently learned moves (as in Gen 1, where wild Pokémon know
the last four moves they learned). Their other points go, one rank at a
time in turn, into the basic attack and the equipped moves, then into
those moves' modifiers, then into anything else still open. The starter
is built the same way.

### Lines without a tree yet

Until a line gets its tree, its species' `moves` (in `pokemon.py`) are
its base attacks (`skills.stand_in_tree`): the first is the basic attack,
damaging ones can be ranked up to 5, status ones stay at 1.

### Battle mechanics for skills

Described in `mechanics.md`: stat stages (Attack, Defense, Speed; up and
down), Leech Seed, moves that hit every target, recoil, the recharge
round, high crit ratio, badly poisoned (Toxic). Status moves always work
(there are no misses), unless the target already has a status or is
immune.

Gen 1 moves that lower **accuracy** (Sand-Attack, Smokescreen) need an
accuracy system first, or a different effect: decided when those lines
get their trees.

---

## The Bulbasaur line

Stages: **B** = Bulbasaur, **I** = Ivysaur (Lv16), **V** = Venusaur (Lv32).

### Moves

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Base attack | – | – | B | Normal, 35 power. Basic attack. | 1–5 |
| Growl | Base attack | – | – | B | Lowers one enemy's Attack 1 stage. R2: every enemy. | 1–2 |
| Leech Seed | Move | 7 | Growl | B | Seeds one enemy (see above). R2: 1/12 per round, R3: 1/8. | 1–3 |
| Vine Whip | Move | 13 | Tackle | B | Grass, 35 power. | 1–5 |
| Poison Powder | Move | 20 | Growl | B | Poisons one enemy. R2: also lowers its Speed 1 stage, R3: 2 stages. | 1–3 |
| Take Down | Move | 20 | Tackle | B | Normal, 90 power; the user takes 1/4 of the damage dealt. (TM09) | 1–5 |
| Razor Leaf | Move | 27 | Vine Whip | B | Grass, 55 power, high crit ratio. | 1–5 |
| Growth | Move | 34 | Leech Seed | B | Raises the user's Attack 1 stage. R2: 2 stages, R3: also Defense 1 stage. | 1–3 |
| Leaf Shield | Move | 22 | Growl | I | Halves the damage one ally takes for 2 rounds. R2: 3 rounds, R3: the whole party. (Gen 1's Reflect, TM33, with our animation) | 1–3 |
| Sleep Powder | Move | 41 | Poison Powder | I | Puts one enemy to sleep. R2: sleeps 1 round longer, R3: 2 longer. | 1–3 |
| Body Slam | Move | 30 | Take Down | I | Normal, 85 power, 30% chance to paralyze. (TM08) | 1–5 |
| Solar Beam | Move | 48 | Razor Leaf | I | Grass, 120 power; charges for a round first. | 1–5 |
| Double-Edge | Move | 50 | Body Slam | V | Normal, 100 power; the user takes 1/4 of the damage dealt. (TM10) | 1–5 |
| Hyper Beam | Move | 55 | Solar Beam | V | Normal, 150 power; the user must rest the next round. (TM15) | 1–5 |

### Modifiers

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Binding Vines | Vine Whip | 15 | B | 10 / 20 / 30% chance to paralyze |
| Spreading Seeds | Leech Seed | 18 | B | R1: seeds every enemy |
| Bloom | Growth | 36 | B | Also heals the user 1/8 / 1/6 / 1/4 of max HP |
| Whirling Leaves | Razor Leaf | 32 | I | R1: hits every enemy (at 75% damage) |
| Toxic Spores | Poison Powder | 28 | I | Poison damage grows each round (1/16, 2/16, 3/16 ... of max HP, like Gen 1's Toxic); R1 only |
| Drowsy Cloud | Sleep Powder | 45 | V | R1: hits every enemy |
| Sunburn | Solar Beam | 50 | V | 10 / 20 / 30% chance to burn |
| Quick Bloom | Solar Beam | 60 | V | R1: no charging round |

### How it plays out

- **Lv5 Bulbasaur:** Tackle and Growl, 0 points.
- **Lv13:** 8 points, e.g. Tackle R4, Leech Seed R2, Vine Whip R1 and two
  spare.
- **Lv16 → Ivysaur:** Leaf Shield, Sleep Powder, Body Slam, Solar Beam and
  their modifiers appear in the tree (still level-gated).
- **Lv32 → Venusaur:** Double-Edge, Hyper Beam and the capstone modifiers.
- By Lv50 a Pokémon has 45 points: enough for a strong build (four moves
  at R5 and a few modifiers), not the whole tree (about 70 ranks).

---

## Other lines (next)

Built the same way, once the Bulbasaur line plays well: Pidgey, Rattata,
Caterpie, Weedle, Oddish, Bellsprout and Pikachu (Route 1), then the Ice
Cave Pokémon. For example, the **Pidgey line**: Gust (base), then
Quick Attack (12), Wing Attack (28) and Agility (36), with Whirlwind and
Sand-Attack reworked to fit this battle system.
