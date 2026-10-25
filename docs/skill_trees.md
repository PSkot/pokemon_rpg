# Skill trees

How skills work, and every line's tree. Keep this file in step with the
code (`game/mechanics/skills.py`, moves in `game/mechanics/moves.py`). The
tree tables at the end are generated from the code: after changing a tree,
run `python tools/skill_docs.py`.

Trees exist for every line in the game: Bulbasaur, the Route 1 Pokémon
(Pidgey, Rattata, Caterpie, Weedle, Oddish, Bellsprout, Pikachu) and the
Ice Cave Pokémon (Seel/Dewgong, Shellder, Psyduck, Horsea, Jynx, Lapras).

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
| **Base attack** | Known from the start, rank 1 for free. The first one is the Pokémon's **basic attack** (the Fight command). | 1–5 |
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

A species added without a tree gets Tackle as its only skill
(`skills.stand_in_tree`) until its line has one.

### Battle mechanics for skills

Described in `mechanics.md` (*Moves*, *Stat stages*, *End of round*):
stat stages (Attack, Defense, Speed, accuracy), Leech Seed, binding, moves
that hit every target or several times, priority, flinching, confusion,
recoil, the recharge round, crit ratio and Focus Energy, Rest, draining
and badly poisoned (Toxic).

---

## How the trees are built

- **Base attacks:** the moves the first species knows at the start in
  Red/Blue (1 or 2).
- **Moves:** the rest of the line's Red/Blue learnset, at the first
  species' learn levels, plus a few TMs/HMs the line could learn (marked
  in the code) where the learnset is thin or to give an evolution
  something of its own. Moves only the evolved forms learn need that
  stage.
- **Parents** group moves into branches (attacks under the basic attack,
  support moves under the status base attack).
- **Modifiers** (3–5 per line) add an effect, raise a chance, or make a
  move hit every enemy; the strongest need an evolved stage.
- **Reworked Gen 1 moves:** Whirlwind lowers every enemy's Speed (it
  ended wild battles); Psychic lowers Defense (Gen 1: Special, not in this
  game); Wrap and Clamp hurt for 2–5 rounds instead of locking the target;
  Thrash and Petal Dance hit once and confuse the user (Petal Dance hits
  every enemy); Focus Energy works as intended (Gen 1's was bugged).
  Mirror Move, Disable, Mist and other moves that don't fit are left out.
- **Status moves** that inflict a status or confusion have their Gen 1
  hit chance (Sleep Powder 75%, Sing 55%, ...); everything else always
  works.
- Lines that evolve by stone (Pikachu, Shellder, Oddish and Bellsprout's
  last stage) stop at the last stage reachable by level for now.

### Example: the Bulbasaur line

- **Lv5 Bulbasaur:** Tackle and Growl, 0 points.
- **Lv13:** 8 points, e.g. Tackle R4, Leech Seed R2, Vine Whip R1 and two
  spare.
- **Lv16 → Ivysaur:** Leaf Shield, Sleep Powder, Body Slam, Solar Beam and
  their modifiers appear in the tree (still level-gated).
- **Lv32 → Venusaur:** Double-Edge, Hyper Beam and the capstone modifiers.
- By Lv50 a Pokémon has 45 points: enough for a strong build (four moves
  at R5 and a few modifiers), not the whole tree (about 70 ranks).

---

<!-- trees:start -->

## The Bulbasaur line

Stages: Bulbasaur → Ivysaur (Lv16) → Venusaur (Lv32, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Bulbasaur | Normal, 35 power. | 1–5 |
| Growl | Base attack | – | – | Bulbasaur | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Leech Seed | Move | 7 | Growl | Bulbasaur | Seeds an enemy: drains 1/16 of its max HP each round. Doesn't affect Grass types. R2: Drains 1/12. R3: Drains 1/8. | 1–3 |
| Vine Whip | Move | 13 | Tackle | Bulbasaur | Grass, 35 power. | 1–5 |
| Poison Powder | Move | 20 | Growl | Bulbasaur | Poisons an enemy (75% chance). R2: Also lowers its Speed 1 stage. R3: Also lowers its Speed 2 stages. | 1–3 |
| Take Down | Move | 20 | Tackle | Bulbasaur | Normal, 90 power. The user takes 1/4 of the damage dealt. | 1–5 |
| Razor Leaf | Move | 27 | Vine Whip | Bulbasaur | Grass, 55 power. High critical-hit ratio. | 1–5 |
| Growth | Move | 34 | Leech Seed | Bulbasaur | Raises its Attack 1 stage. R2: Raises Attack 2 stages. R3: Raises Attack 2 stages and Defense 1 stage. | 1–3 |
| Leaf Shield | Move | 22 | Growl | Ivysaur | Halves the damage an ally takes for 2 rounds. R2: For 3 rounds. R3: For 3 rounds, on the whole party. | 1–3 |
| Sleep Powder | Move | 41 | Poison Powder | Ivysaur | Puts an enemy to sleep (75% chance). R2: It sleeps 1 round longer. R3: It sleeps 2 rounds longer. | 1–3 |
| Body Slam | Move | 30 | Take Down | Ivysaur | Normal, 85 power. 30% chance to paralyze. | 1–5 |
| Solar Beam | Move | 48 | Razor Leaf | Ivysaur | Grass, 120 power. Charges for a round first. | 1–5 |
| Double-Edge | Move | 50 | Body Slam | Venusaur | Normal, 100 power. The user takes 1/4 of the damage dealt. | 1–5 |
| Hyper Beam | Move | 55 | Solar Beam | Venusaur | Normal, 150 power. The user must rest the next round. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Binding Vines | Vine Whip | 15 | Bulbasaur | Vine Whip: 10% chance to paralyze. / 20% chance. / 30% chance. |
| Spreading Seeds | Leech Seed | 18 | Bulbasaur | Leech Seed seeds every enemy. |
| Bloom | Growth | 36 | Bulbasaur | Growth also heals the user 1/8 of its max HP. / Heals 1/6. / Heals 1/4. |
| Whirling Leaves | Razor Leaf | 32 | Ivysaur | Razor Leaf hits every enemy, at 75% damage. |
| Toxic Spores | Poison Powder | 28 | Ivysaur | Poison Powder's poison gets worse every round (Toxic). |
| Drowsy Cloud | Sleep Powder | 45 | Venusaur | Sleep Powder hits every enemy. |
| Sunburn | Solar Beam | 50 | Venusaur | Solar Beam: 10% chance to burn. / 20% chance. / 30% chance. |
| Quick Bloom | Solar Beam | 60 | Venusaur | Solar Beam fires without charging. |

---

## The Charmander line

Stages: Charmander → Charmeleon (Lv16, not in the game yet) → Charizard (Lv36, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | Basic attack | – | – | Charmander | Normal, 40 power. | 1–5 |
| Growl | Base attack | – | – | Charmander | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Ember | Move | 9 | Scratch | Charmander | Fire, 40 power. 10% chance to burn. | 1–5 |
| Leer | Move | 15 | Growl | Charmander | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Swords Dance | Move | 25 | Leer | Charmeleon | Raises its Attack 2 stages. | 1 |
| Slash | Move | 30 | Scratch | Charmander | Normal, 70 power. High critical-hit ratio. | 1–5 |
| Flamethrower | Move | 38 | Ember | Charmander | Fire, 95 power. 10% chance to burn. | 1–5 |
| Fire Spin | Move | 46 | Flamethrower | Charmander | Fire, 15 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | 1–5 |
| Fire Blast | Move | 50 | Flamethrower | Charizard | Fire, 120 power. 30% chance to burn. | 1–5 |
| Earthquake | Move | 55 | Slash | Charizard | Ground, 100 power. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Kindling | Ember | 12 | Charmander | Ember: 20% chance to burn. / 30% chance. / 40% chance. |
| Razor Claws | Slash | 33 | Charmander | Slash: 10% chance to make it flinch. / 20% chance. / 30% chance. |
| Wildfire | Flamethrower | 42 | Charmeleon | Flamethrower hits every enemy, at 75% damage. |
| Inferno | Fire Spin | 48 | Charmander | Fire Spin: 1/12 of its max HP each round. / 1/8. |
| Scorch | Fire Blast | 55 | Charizard | Fire Blast: 40% chance to burn. / 50% chance. |

---

## The Squirtle line

Stages: Squirtle → Wartortle (Lv16, not in the game yet) → Blastoise (Lv36, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Squirtle | Normal, 35 power. | 1–5 |
| Tail Whip | Base attack | – | – | Squirtle | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Bubble | Move | 8 | Tackle | Squirtle | Water, 20 power. 33% chance to lower its Speed. | 1–5 |
| Water Gun | Move | 15 | Bubble | Squirtle | Water, 40 power. | 1–5 |
| Bite | Move | 22 | Tackle | Squirtle | Normal, 60 power. 10% chance to make it flinch. | 1–5 |
| Withdraw | Move | 28 | Tail Whip | Squirtle | Raises its Defense 1 stage. R2: Raises its Defense 2 stages. | 1–2 |
| Ice Beam | Move | 30 | Water Gun | Wartortle | Ice, 95 power. 10% chance to freeze. | 1–5 |
| Skull Bash | Move | 35 | Bite | Wartortle | Normal, 100 power. Charges for a round first. | 1–5 |
| Hydro Pump | Move | 42 | Water Gun | Squirtle | Water, 120 power. | 1–5 |
| Blizzard | Move | 55 | Ice Beam | Blastoise | Ice, 120 power. 10% chance to freeze. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Swift Current | Bubble | 10 | Squirtle | Bubble always goes first. |
| Strong Jaw | Bite | 24 | Squirtle | Bite: 20% chance to make it flinch. / 30% chance. / 40% chance. |
| Shell Armor | Withdraw | 30 | Squirtle | Withdraw also heals the user 1/8 of its max HP. |
| Hard Shell | Skull Bash | 38 | Wartortle | Skull Bash hits without lowering its head first. |
| Tidal Wave | Hydro Pump | 46 | Blastoise | Hydro Pump hits every enemy, at 75% damage. |

---

## The Spearow line

Stages: Spearow → Fearow (Lv20, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Peck | Basic attack | – | – | Spearow | Flying, 35 power. | 1–5 |
| Growl | Base attack | – | – | Spearow | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Leer | Move | 9 | Growl | Spearow | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Fury Attack | Move | 15 | Peck | Spearow | Normal, 15 power, hits 2-5 times. | 1–5 |
| Swift | Move | 20 | Peck | Spearow | Normal, 60 power. Ignores accuracy drops. | 1–5 |
| Whirlwind | Move | 22 | Leer | Spearow | Lowers every enemy's Speed 1 stage. | 1 |
| Drill Peck | Move | 29 | Fury Attack | Spearow | Flying, 80 power. | 1–5 |
| Agility | Move | 36 | Leer | Spearow | Raises its Speed 2 stages. | 1 |
| Hyper Beam | Move | 45 | Drill Peck | Fearow | Normal, 150 power. The user must rest the next round. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Keen Beak | Peck | 10 | Spearow | Peck has a high critical-hit ratio. |
| Frenzied Pecks | Fury Attack | 18 | Spearow | Fury Attack hits 3-5 times. |
| Drill Run | Drill Peck | 33 | Spearow | Drill Peck: 10% chance to make it flinch. / 20% chance. / 30% chance. |

---

## The Nidoran F line

Stages: Nidoran F → Nidorina (Lv16, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Nidoran F | Normal, 35 power. | 1–5 |
| Growl | Base attack | – | – | Nidoran F | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Scratch | Move | 8 | Tackle | Nidoran F | Normal, 40 power. | 1–5 |
| Poison Sting | Move | 14 | Tackle | Nidoran F | Poison, 15 power. 30% chance to poison. | 1–5 |
| Tail Whip | Move | 21 | Growl | Nidoran F | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Body Slam | Move | 25 | Tackle | Nidorina | Normal, 85 power. 30% chance to paralyze. | 1–5 |
| Bite | Move | 29 | Scratch | Nidoran F | Normal, 60 power. 10% chance to make it flinch. | 1–5 |
| Fury Swipes | Move | 36 | Scratch | Nidoran F | Normal, 18 power, hits 2-5 times. | 1–5 |
| Double Kick | Move | 43 | Bite | Nidoran F | Fighting, 30 power, hits twice. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Poison Point | Poison Sting | 16 | Nidoran F | Poison Sting: 40% chance to poison. / 50% chance. / 60% chance. |
| Strong Jaw | Bite | 32 | Nidoran F | Bite: 20% chance to make it flinch. / 30% chance. / 40% chance. |

---

## The Nidoran M line

Stages: Nidoran M → Nidorino (Lv16, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Nidoran M | Normal, 35 power. | 1–5 |
| Leer | Base attack | – | – | Nidoran M | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Horn Attack | Move | 8 | Tackle | Nidoran M | Normal, 65 power. | 1–5 |
| Poison Sting | Move | 14 | Tackle | Nidoran M | Poison, 15 power. 30% chance to poison. | 1–5 |
| Focus Energy | Move | 21 | Leer | Nidoran M | The user's critical-hit chance ×4 for the battle. | 1 |
| Body Slam | Move | 25 | Tackle | Nidorino | Normal, 85 power. 30% chance to paralyze. | 1–5 |
| Fury Attack | Move | 29 | Horn Attack | Nidoran M | Normal, 15 power, hits 2-5 times. | 1–5 |
| Double Kick | Move | 43 | Horn Attack | Nidoran M | Fighting, 30 power, hits twice. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Poison Point | Poison Sting | 16 | Nidoran M | Poison Sting: 40% chance to poison. / 50% chance. / 60% chance. |
| Sharp Horn | Horn Attack | 20 | Nidoran M | Horn Attack has a high critical-hit ratio. |
| Rampage | Fury Attack | 32 | Nidoran M | Fury Attack hits 3-5 times. |

---

## The Pidgey line

Stages: Pidgey → Pidgeotto (Lv18, not in the game yet) → Pidgeot (Lv36, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Gust | Basic attack | – | – | Pidgey | Flying, 40 power. | 1–5 |
| Sand-Attack | Base attack | – | – | Pidgey | Lowers an enemy's accuracy 1 stage. R2: Lowers every enemy's accuracy. | 1–2 |
| Quick Attack | Move | 12 | Gust | Pidgey | Normal, 40 power. Always goes first. | 1–5 |
| Whirlwind | Move | 19 | Sand-Attack | Pidgey | Lowers every enemy's Speed 1 stage. R2: Lowers their Speed 2 stages. | 1–2 |
| Wing Attack | Move | 28 | Gust | Pidgey | Flying, 35 power. | 1–5 |
| Double-Edge | Move | 30 | Quick Attack | Pidgeotto | Normal, 100 power. The user takes 1/4 of the damage dealt. | 1–5 |
| Agility | Move | 36 | Whirlwind | Pidgey | Raises its Speed 2 stages. R2: Raises its Speed 3 stages. | 1–2 |
| Sky Attack | Move | 44 | Wing Attack | Pidgeot | Flying, 140 power. Charges for a round first. High critical-hit ratio. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Gale Force | Gust | 10 | Pidgey | Gust: 10% chance to lower the target's Speed. / 20% chance. / 30% chance. |
| Swift Strike | Quick Attack | 20 | Pidgey | Quick Attack: 10% chance to make it flinch. / 20% chance. / 30% chance. |
| Twister | Gust | 25 | Pidgeotto | Gust hits every enemy, at 75% damage. |
| Aerial Ace | Wing Attack | 33 | Pidgeotto | Wing Attack ignores accuracy drops and has a high critical-hit ratio. |
| Swoop | Sky Attack | 55 | Pidgeot | Sky Attack fires without charging. |

---

## The Rattata line

Stages: Rattata → Raticate (Lv20, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Rattata | Normal, 35 power. | 1–5 |
| Tail Whip | Base attack | – | – | Rattata | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Quick Attack | Move | 7 | Tackle | Rattata | Normal, 40 power. Always goes first. | 1–5 |
| Hyper Fang | Move | 14 | Quick Attack | Rattata | Normal, 80 power. 10% chance to make it flinch. | 1–5 |
| Focus Energy | Move | 23 | Tail Whip | Rattata | The user's critical-hit chance ×4 for the battle. | 1 |
| Body Slam | Move | 25 | Tackle | Rattata | Normal, 85 power. 30% chance to paralyze. | 1–5 |
| Super Fang | Move | 34 | Hyper Fang | Rattata | Normal. Takes half the target's HP. | 1 |
| Hyper Beam | Move | 45 | Super Fang | Raticate | Normal, 150 power. The user must rest the next round. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Frenzy | Quick Attack | 12 | Rattata | Quick Attack hits twice. |
| Sharp Fangs | Hyper Fang | 18 | Rattata | Hyper Fang: 20% chance to make it flinch. / 30% chance. / 40% chance. |
| Laser Focus | Focus Energy | 28 | Rattata | Focus Energy also raises Attack 1 stage. |
| Gnaw | Super Fang | 40 | Raticate | Super Fang heals the user half the damage dealt. |

---

## The Caterpie line

Stages: Caterpie → Metapod (Lv7) → Butterfree (Lv10, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Caterpie | Normal, 35 power. | 1–5 |
| String Shot | Base attack | – | – | Caterpie | Lowers an enemy's Speed 1 stage. R2: Lowers every enemy's Speed. | 1–2 |
| Harden | Move | 7 | String Shot | Metapod | Raises its Defense 1 stage. R2: Raises its Defense 2 stages. | 1–2 |
| Confusion | Move | 12 | Tackle | Butterfree | Psychic, 50 power. 10% chance to confuse. | 1–5 |
| Poison Powder | Move | 15 | String Shot | Butterfree | Poisons an enemy (75% chance). | 1 |
| Stun Spore | Move | 16 | Poison Powder | Butterfree | Paralyzes an enemy (75% chance). | 1 |
| Sleep Powder | Move | 17 | Stun Spore | Butterfree | Puts an enemy to sleep (75% chance). | 1 |
| Supersonic | Move | 21 | Confusion | Butterfree | 55% chance to confuse. | 1 |
| Mega Drain | Move | 25 | Confusion | Butterfree | Grass, 40 power. Heals the user 1/2 of the damage dealt. | 1–5 |
| Whirlwind | Move | 26 | Supersonic | Butterfree | Lowers every enemy's Speed 1 stage. | 1 |
| Psybeam | Move | 32 | Confusion | Butterfree | Psychic, 65 power. 10% chance to confuse. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Compound Eyes | Supersonic | 24 | Butterfree | Supersonic: 70% chance to work. / 85% chance. / Always works. |
| Mind Bend | Psybeam | 35 | Butterfree | Psybeam: 20% chance to confuse. / 30% chance. / 40% chance. |
| Powder Cloud | Sleep Powder | 38 | Butterfree | Sleep Powder hits every enemy. |

---

## The Weedle line

Stages: Weedle → Kakuna (Lv7) → Beedrill (Lv10, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Poison Sting | Basic attack | – | – | Weedle | Poison, 15 power. 30% chance to poison. | 1–5 |
| String Shot | Base attack | – | – | Weedle | Lowers an enemy's Speed 1 stage. R2: Lowers every enemy's Speed. | 1–2 |
| Harden | Move | 7 | String Shot | Kakuna | Raises its Defense 1 stage. R2: Raises its Defense 2 stages. | 1–2 |
| Fury Attack | Move | 12 | Poison Sting | Beedrill | Normal, 15 power, hits 2-5 times. | 1–5 |
| Focus Energy | Move | 16 | Harden | Beedrill | The user's critical-hit chance ×4 for the battle. | 1 |
| Twineedle | Move | 20 | Fury Attack | Beedrill | Bug, 25 power, hits twice. 20% chance to poison. | 1–5 |
| Swords Dance | Move | 25 | Focus Energy | Beedrill | Raises its Attack 2 stages. | 1 |
| Pin Missile | Move | 30 | Twineedle | Beedrill | Bug, 14 power, hits 2-5 times. | 1–5 |
| Agility | Move | 35 | Focus Energy | Beedrill | Raises its Speed 2 stages. | 1 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Venom Barbs | Poison Sting | 5 | Weedle | Poison Sting: 40% chance to poison. / 50% chance. / 60% chance. |
| Toxic Barbs | Twineedle | 28 | Beedrill | Twineedle's poison gets worse every round. |
| Skill Link | Pin Missile | 40 | Beedrill | Pin Missile always hits 5 times. |

---

## The Oddish line

Stages: Oddish → Gloom (Lv21, not in the game yet) → Vileplume (by stone, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Absorb | Basic attack | – | – | Oddish | Grass, 20 power. Heals the user 1/2 of the damage dealt. | 1–5 |
| Poison Powder | Move | 15 | Absorb | Oddish | Poisons an enemy (75% chance). | 1 |
| Stun Spore | Move | 17 | Poison Powder | Oddish | Paralyzes an enemy (75% chance). | 1 |
| Sleep Powder | Move | 19 | Stun Spore | Oddish | Puts an enemy to sleep (75% chance). | 1 |
| Acid | Move | 24 | Absorb | Oddish | Poison, 40 power. 33% chance to lower its Defense. | 1–5 |
| Mega Drain | Move | 25 | Absorb | Gloom | Grass, 40 power. Heals the user 1/2 of the damage dealt. | 1–5 |
| Petal Dance | Move | 33 | Acid | Oddish | Grass, 70 power. Hits every enemy. The user becomes confused afterwards. | 1–5 |
| Solar Beam | Move | 46 | Petal Dance | Oddish | Grass, 120 power. Charges for a round first. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Deep Roots | Absorb | 10 | Oddish | Absorb heals 65% of the damage dealt. / 80%. / All of it. |
| Corrosive | Acid | 28 | Oddish | Acid: 50% chance to lower Defense. / 70% chance. / 90% chance. |
| Spore Cloud | Stun Spore | 30 | Gloom | Stun Spore hits every enemy. |
| Calm Bloom | Petal Dance | 40 | Gloom | Petal Dance no longer confuses the user. |

---

## The Bellsprout line

Stages: Bellsprout → Weepinbell (Lv21, not in the game yet) → Victreebel (by stone, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Vine Whip | Basic attack | – | – | Bellsprout | Grass, 35 power. | 1–5 |
| Growth | Base attack | – | – | Bellsprout | Raises its Attack 1 stage. R2: Raises its Attack 2 stages. | 1–2 |
| Wrap | Move | 13 | Vine Whip | Bellsprout | Normal, 15 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | 1–5 |
| Poison Powder | Move | 15 | Growth | Bellsprout | Poisons an enemy (75% chance). | 1 |
| Sleep Powder | Move | 18 | Poison Powder | Bellsprout | Puts an enemy to sleep (75% chance). | 1 |
| Stun Spore | Move | 21 | Poison Powder | Bellsprout | Paralyzes an enemy (75% chance). | 1 |
| Acid | Move | 26 | Wrap | Bellsprout | Poison, 40 power. 33% chance to lower its Defense. | 1–5 |
| Swords Dance | Move | 30 | Growth | Weepinbell | Raises its Attack 2 stages. | 1 |
| Razor Leaf | Move | 33 | Vine Whip | Bellsprout | Grass, 55 power. High critical-hit ratio. | 1–5 |
| Slam | Move | 42 | Wrap | Bellsprout | Normal, 80 power. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Whiplash | Vine Whip | 10 | Bellsprout | Vine Whip: 10% chance to make it flinch. / 20% chance. / 30% chance. |
| Tight Grip | Wrap | 16 | Bellsprout | Wrap: 1/12 of its max HP each round. / 1/8. |
| Gastro Acid | Acid | 30 | Bellsprout | Acid: 50% chance to lower Defense. / 70% chance. / 90% chance. |
| Leaf Storm | Razor Leaf | 38 | Weepinbell | Razor Leaf hits every enemy, at 75% damage. |

---

## The Pikachu line

Stages: Pikachu.

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Thunder Shock | Basic attack | – | – | Pikachu | Electric, 40 power. 10% chance to paralyze. | 1–5 |
| Growl | Base attack | – | – | Pikachu | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Thunder Wave | Move | 9 | Growl | Pikachu | Paralyzes an enemy. Doesn't affect Ground types. | 1 |
| Quick Attack | Move | 16 | Thunder Shock | Pikachu | Normal, 40 power. Always goes first. | 1–5 |
| Swift | Move | 26 | Quick Attack | Pikachu | Normal, 60 power. Ignores accuracy drops. | 1–5 |
| Thunderbolt | Move | 30 | Thunder Shock | Pikachu | Electric, 95 power. 10% chance to paralyze. | 1–5 |
| Agility | Move | 33 | Thunder Wave | Pikachu | Raises its Speed 2 stages. | 1 |
| Thunder | Move | 43 | Thunderbolt | Pikachu | Electric, 120 power. 10% chance to paralyze. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Static | Thunder Shock | 12 | Pikachu | Thunder Shock: 20% chance to paralyze. / 30% chance. / 40% chance. |
| Chain Lightning | Thunderbolt | 38 | Pikachu | Thunderbolt hits every enemy, at 75% damage. |
| Thunderstorm | Thunder | 48 | Pikachu | Thunder: 20% chance to paralyze. / 30% chance. / 40% chance. |

---

## The Seel line

Stages: Seel → Dewgong (Lv34).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Headbutt | Basic attack | – | – | Seel | Normal, 70 power. 30% chance to make it flinch. | 1–5 |
| Water Gun | Move | 10 | Headbutt | Seel | Water, 40 power. | 1–5 |
| Bubble Beam | Move | 25 | Water Gun | Seel | Water, 65 power. 33% chance to lower its Speed. | 1–5 |
| Growl | Move | 30 | Headbutt | Seel | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Aurora Beam | Move | 35 | Headbutt | Seel | Ice, 65 power. 10% chance to lower its Attack. | 1–5 |
| Rest | Move | 40 | Growl | Seel | The user heals fully, is cured, and sleeps for 2 rounds. | 1 |
| Surf | Move | 40 | Bubble Beam | Dewgong | Water, 95 power. | 1–5 |
| Take Down | Move | 45 | Headbutt | Seel | Normal, 90 power. The user takes 1/4 of the damage dealt. | 1–5 |
| Ice Beam | Move | 50 | Aurora Beam | Seel | Ice, 95 power. 10% chance to freeze. | 1–5 |
| Blizzard | Move | 55 | Ice Beam | Dewgong | Ice, 120 power. 10% chance to freeze. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Hard Head | Headbutt | 15 | Seel | Headbutt: 40% chance to make it flinch. / 50% chance. / 60% chance. |
| Frostbite | Aurora Beam | 38 | Seel | Aurora Beam: 30% chance to lower Attack. / 50% chance. / 70% chance. |
| Deep Freeze | Ice Beam | 52 | Dewgong | Ice Beam: 20% chance to freeze. / 30% chance. |

---

## The Shellder line

Stages: Shellder.

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | Basic attack | – | – | Shellder | Normal, 35 power. | 1–5 |
| Withdraw | Base attack | – | – | Shellder | Raises its Defense 1 stage. R2: Raises its Defense 2 stages. | 1–2 |
| Water Gun | Move | 10 | Tackle | Shellder | Water, 40 power. | 1–5 |
| Supersonic | Move | 18 | Withdraw | Shellder | 55% chance to confuse. | 1 |
| Clamp | Move | 23 | Water Gun | Shellder | Water, 35 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | 1–5 |
| Bubble Beam | Move | 25 | Water Gun | Shellder | Water, 65 power. 33% chance to lower its Speed. | 1–5 |
| Aurora Beam | Move | 30 | Clamp | Shellder | Ice, 65 power. 10% chance to lower its Attack. | 1–5 |
| Leer | Move | 39 | Supersonic | Shellder | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Ice Beam | Move | 50 | Aurora Beam | Shellder | Ice, 95 power. 10% chance to freeze. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Shell Armor | Withdraw | 20 | Shellder | Withdraw also heals the user 1/8 of its max HP. |
| Iron Jaws | Clamp | 26 | Shellder | Clamp: 1/12 of its max HP each round. / 1/8. |
| Icicle | Aurora Beam | 34 | Shellder | Aurora Beam: 10% chance to freeze. / 20% chance. / 30% chance. |

---

## The Psyduck line

Stages: Psyduck → Golduck (Lv33, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | Basic attack | – | – | Psyduck | Normal, 40 power. | 1–5 |
| Water Gun | Move | 8 | Scratch | Psyduck | Water, 40 power. | 1–5 |
| Bubble Beam | Move | 20 | Water Gun | Psyduck | Water, 65 power. 33% chance to lower its Speed. | 1–5 |
| Tail Whip | Move | 28 | Scratch | Psyduck | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Confusion | Move | 36 | Tail Whip | Psyduck | Psychic, 50 power. 10% chance to confuse. | 1–5 |
| Fury Swipes | Move | 43 | Scratch | Psyduck | Normal, 18 power, hits 2-5 times. | 1–5 |
| Ice Beam | Move | 45 | Bubble Beam | Golduck | Ice, 95 power. 10% chance to freeze. | 1–5 |
| Hydro Pump | Move | 52 | Bubble Beam | Psyduck | Water, 120 power. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Swift Swim | Water Gun | 12 | Psyduck | Water Gun always goes first. |
| Headache | Confusion | 38 | Psyduck | Confusion: 20% chance to confuse. / 30% chance. / 40% chance. |
| Frenzied Claws | Fury Swipes | 45 | Psyduck | Fury Swipes hits 3-5 times. |

---

## The Horsea line

Stages: Horsea → Seadra (Lv32, not in the game yet).

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Bubble | Basic attack | – | – | Horsea | Water, 20 power. 33% chance to lower its Speed. | 1–5 |
| Smokescreen | Move | 19 | Bubble | Horsea | Lowers an enemy's accuracy 1 stage. R2: Lowers every enemy's accuracy. | 1–2 |
| Bubble Beam | Move | 20 | Bubble | Horsea | Water, 65 power. 33% chance to lower its Speed. | 1–5 |
| Leer | Move | 24 | Smokescreen | Horsea | Lowers an enemy's Defense 1 stage. R2: Lowers every enemy's Defense. | 1–2 |
| Water Gun | Move | 30 | Bubble | Horsea | Water, 40 power. | 1–5 |
| Agility | Move | 37 | Leer | Horsea | Raises its Speed 2 stages. | 1 |
| Ice Beam | Move | 40 | Bubble Beam | Seadra | Ice, 95 power. 10% chance to freeze. | 1–5 |
| Hydro Pump | Move | 45 | Water Gun | Horsea | Water, 120 power. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Swift Current | Bubble | 10 | Horsea | Bubble always goes first. |
| Thick Ink | Smokescreen | 22 | Horsea | Smokescreen lowers accuracy 2 stages. |
| Sniper | Water Gun | 32 | Horsea | Water Gun has a high critical-hit ratio. |

---

## The Jynx line

Stages: Jynx.

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Pound | Basic attack | – | – | Jynx | Normal, 40 power. | 1–5 |
| Lovely Kiss | Base attack | – | – | Jynx | Puts an enemy to sleep (75% chance). | 1 |
| Lick | Move | 18 | Pound | Jynx | Ghost, 20 power. 30% chance to paralyze. | 1–5 |
| Double Slap | Move | 23 | Pound | Jynx | Normal, 15 power, hits 2-5 times. | 1–5 |
| Ice Punch | Move | 31 | Lick | Jynx | Ice, 75 power. 10% chance to freeze. | 1–5 |
| Psychic | Move | 35 | Lovely Kiss | Jynx | Psychic, 90 power. 33% chance to lower its Defense. | 1–5 |
| Body Slam | Move | 39 | Double Slap | Jynx | Normal, 85 power. 30% chance to paralyze. | 1–5 |
| Thrash | Move | 47 | Body Slam | Jynx | Normal, 90 power. The user becomes confused afterwards. | 1–5 |
| Blizzard | Move | 58 | Ice Punch | Jynx | Ice, 120 power. 10% chance to freeze. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Sweet Kiss | Lovely Kiss | 20 | Jynx | Lovely Kiss: 85% chance to work. / 95% chance. |
| Frost Touch | Ice Punch | 34 | Jynx | Ice Punch: 20% chance to freeze. / 30% chance. |
| Whiteout | Blizzard | 60 | Jynx | Blizzard hits every enemy, at 75% damage. |

---

## The Lapras line

Stages: Lapras.

| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |
| --- | --- | --- | --- | --- | --- | --- |
| Water Gun | Basic attack | – | – | Lapras | Water, 40 power. | 1–5 |
| Growl | Base attack | – | – | Lapras | Lowers an enemy's Attack 1 stage. R2: Lowers every enemy's Attack. | 1–2 |
| Sing | Move | 16 | Growl | Lapras | Puts an enemy to sleep (55% chance). | 1 |
| Body Slam | Move | 25 | Water Gun | Lapras | Normal, 85 power. 30% chance to paralyze. | 1–5 |
| Confuse Ray | Move | 31 | Sing | Lapras | Confuses an enemy. | 1 |
| Ice Beam | Move | 38 | Water Gun | Lapras | Ice, 95 power. 10% chance to freeze. | 1–5 |
| Hydro Pump | Move | 46 | Ice Beam | Lapras | Water, 120 power. | 1–5 |
| Blizzard | Move | 50 | Ice Beam | Lapras | Ice, 120 power. 10% chance to freeze. | 1–5 |

| Modifier | Changes | Lv | Stage | Per rank |
| --- | --- | --- | --- | --- |
| Siren Song | Sing | 20 | Lapras | Sing: 70% chance to work. / 85% chance. / Always works. |
| Freeze-Dry | Ice Beam | 40 | Lapras | Ice Beam: 20% chance to freeze. / 30% chance. |
| Tidal Wave | Hydro Pump | 50 | Lapras | Hydro Pump hits every enemy, at 75% damage. |

<!-- trees:end -->
