# Skill trees

How skills work, and every line's tree. Keep this file in step with the
code (`game/mechanics/skills.py`, moves in `game/mechanics/moves.py`). The
tree tables at the end are generated from the code: after changing a tree,
run `python tools/skill_docs.py`.

Trees exist for every line in the game: the starters, the Route 1, Route 22
and Viridian Forest Pokémon, and the Ice Cave Pokémon.

Pokémon don't learn moves at fixed levels. Each evolution line has a
**skill tree**: every move of its Red/Blue learnset (plus some TMs) is one
skill, linked by paths, and every move has its own branches of **buffs**
that change it. **Links** join two moves so that one sets off the other.
A tree costs far more points than a Pokémon ever has (115–207 against 95
at Lv100), so every build chooses.

### The skill tree screen

Party screen → **S** (`game/scenes/skill_tree.py`). Left: the tree as a
**map of nodes**, laid out left to right (`skill_tree.layout`: a tidy
tree, each skill right of its first parent, leaves a row each, parents
centred on their children). Moves are circles in their type's colour,
buffs diamonds, links small orange nodes with a dashed line to their
second move; each shows its name (buffs and links with their rank, e.g.
"Potent 3/5"; equipped moves their key, F = the basic attack). Filled =
learned, green outline = can be learned or ranked up now, grey = locked;
learned paths light up. The view pans smoothly to follow the cursor
(keeping the chosen skill's move in view). A **mini-map** in the view's
top-right corner shows the whole tree: the paths between moves, a dot per
skill (learned in its colour, open green, locked dim), the cursor
(flashing) and a frame for the part in view; **M** hides or shows it.
**Tapping or clicking** on the mini-map jumps to the skill nearest that
spot (dragging scrubs along); tapping a node in the tree picks it. The
header shows the points
left and how much of the whole tree is learned. Right: the chosen skill:
each rank's effect, the move as it is now with everything learned, its
requirements (green = met) and what can be done. Keys: **arrows** go to
the nearest node that way, **Enter** spends a point, **E** equips or
unequips a move (4 at most), **R** resets all points (in towns only,
after asking), **Q/W** switch Pokémon (touch: the Next pill), **M** the
mini-map.

---

## Rules

### Skill points

- **1 point per level-up.** A Pokémon has `level − 5` points in total (none
  below Lv5): 0 for a new Lv5 starter, 95 at Lv100.
- **A move costs 1 point; each rank of a buff or link costs 1 point.** The
  first moves (the base attacks) are free.
- Points can be reset for free in towns, to try a different build.

### Kinds of skills

| Kind | What it is | Ranks |
| --- | --- | --- |
| **Move** | One Gen 1 move. Learned moves are used in battle once equipped. The first free move is the **basic attack** (Fight). | 1 |
| **Buff** | Changes one move: more power, an added effect, more targets, ... Buffs hang off their move in short paths: deeper buffs need the ones before them. | 1–5 |
| **Link** | Needs two moves: when the first lands, it has a chance to set off the second (with all the second's buffs) on the same target, at once and without its charge or recharge. A move set off this way doesn't set off more. | 1–3 |

A buff's ranks add to the move: numbers add up (chances to at most 100%),
stat stage changes add per stat, a status is only added to a move without
one (or adds to the same status's chance).

### Unlocking

A skill can be learned when **all** of these are true:

1. the Pokémon's **level** is at least the skill's level (Gen 1's learn
   level for moves; buffs open a few levels after their move, deep ones
   up to 24 levels later);
2. it has **every parent** skill (a move's path; a buff's place in its
   branch; both moves of a link);
3. the Pokémon is at least the **evolution stage** the skill needs (every
   damaging move's capstone needs the line's last stage).

### The buffs of each move

Every move gets its branches from its kind (`skills._buffs`); per rank:

**Damaging moves**

| Buff | Ranks | Effect | Opens | Needs |
| --- | --- | --- | --- | --- |
| Potent | 5 | +8% power per rank | move's Lv | the move |
| *Rider* | 3 | by type: Searing (fire, +10% burn), Crackling (electric, +10% paralysis), Chilling (ice, +5% freeze), Venomous (poison/bug, +10% poison), Draining (grass, heals 15% of the damage), Rippling (water, 10% Speed down), Dusting (ground, 10% accuracy down), Bewildering/Haunting (psychic/ghost, +10% confusion), Staggering (others, +10% flinch) | +3 | the move |
| Wounding | 2 | wounds: 1/16, then 1/12 of max HP per round for 3 rounds | +16 | the rider |
| Keen | 3 | crits ×2/×3/×4 as likely (not on high-crit moves) | +6 | Potent |
| Sweeping | 2 | hits every enemy at 50%, then 75% damage (not on spread moves) | +12 | Potent |
| Instant / Tireless / Cushioned / Calm | 1–2 | take away a drawback: the charge round, the recharge round, recoil (half, then none), the user's confusion | +10 to +20 | Potent |
| *Capstone* | 1 | Swift (power ≥ 90: always goes first), Relentless (multi-hit: 1 more hit) or Twin (hits twice at −30% power) | +24 (Lv30 at least), last stage | Keen |

Super Fang (half the target's HP) has no Potent, Keen or capstone.

**Moves that lower an enemy's stat** (Leer, Growl, Sand-Attack, ...)

| Buff | Ranks | Effect | Opens | Needs |
| --- | --- | --- | --- | --- |
| Deep | 2 | lowers the stat 1 more stage per rank | move's Lv | the move |
| Wide | 1 | works on every enemy | +4 | the move |
| Lingering | 3 | wounds (passive damage): 1/16, 1/12, 1/8 of max HP per round for 3 rounds | +8 | Deep |
| Hexing | 2 | also lowers a second stat (Attack ↔ Defense, accuracy ↔ Speed) | +12 | Wide |
| Emboldening | 2 | also raises one of the user's stats (Leer: Attack; Growl: Defense; Sand-Attack, String Shot: Speed) | +16 | Lingering |
| Quick | 1 | always goes first | +10 | the move |

**Moves that raise the user's stat** (Growth, Harden, Agility, ...):
Greater (2: +1 stage per rank), Renewing (3: heals 1/16, 1/8, 1/4),
Fortifying (2: a second stat), Warding (2: halves damage for 2/3 rounds),
Quick.

**Moves that inflict a status or confusion** (Poison Powder, Sing, ...):
Sure (3: +8% chance per rank, up to 100%), Wide, Lingering (2), then one
by status: Toxic (poison gets worse), Deep (sleep: +1/+2 rounds), Numbing
(paralysis: Speed down), Dizzying (confusion: accuracy down); Quick.

**Others:** Leech Seed (Deep-Rooted: drains more), Leaf Shield (Thick:
longer; Shared: the whole party), Focus Energy (Fired-Up: Attack up),
Rest; each with Wide/Shared, Lingering or Renewing, and Quick.

### In battle

- **Fight** uses the basic attack (Tackle for Bulbasaur), with its buffs.
- **Skills:** up to **4 equipped moves**, like Gen 1's four move slots.
  Learned moves that aren't equipped can be swapped in outside battle.
- Buffs and links work on their move automatically. A link's set-off move
  shows its name over the user and "Vine Whip set off Leech Seed!".
- **Wounds** (Wounding, Lingering): the target loses its share of max HP
  at the end of each round for 3 rounds; a new wound restarts the count
  (the bigger share stays).

### Wild Pokémon

They follow the same tree (`SkillTree.auto_build`): they learn every move
their level, parents and stage allow (in level order), and equip their 4
most recently learned moves (as in Gen 1). Their other points go, a rank
at a time in turn, into the buffs of the basic attack and the equipped
moves, then those moves' links, then anything else still open. The
starter is built the same way.

### Lines without a tree yet

A species added without a tree gets Tackle as its only skill
(`skills.stand_in_tree`) until its line has one.

---

## How the trees are built

- **Base attacks:** the moves the first species knows at the start in
  Red/Blue (1 or 2), free.
- **Moves:** the rest of the line's Red/Blue learnset, at the first
  species' learn levels, plus a few TMs/HMs the line could learn (marked
  in the code). Moves only the evolved forms learn need that stage.
- **Paths:** each move is opened by an earlier one (Vine Whip → Razor
  Leaf → Solar Beam → Hyper Beam; support moves under the status base
  attack).
- **Buffs** come from the templates above; **links** are written per line
  (2–5 each, e.g. Bulbasaur: Vine Whip → Leech Seed, Growth → Leaf Shield).
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

---

<!-- trees:start -->

## The Bulbasaur line

Stages: Bulbasaur → Ivysaur (Lv16) → Venusaur (Lv32). Whole tree: 207 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Bulbasaur | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Growl | free | – | Bulbasaur | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Leech Seed | 7 | Growl | Bulbasaur | Seeds an enemy: drains 1/16 of its max HP each round. Doesn't affect Grass types. | Deep-Rooted, Wide, Lingering, Quick (7) |
| Vine Whip | 13 | Tackle | Bulbasaur | Grass, 35 power. | Potent, Draining, Wounding, Keen, Sweeping, Twin (16) |
| Poison Powder | 20 | Growl | Bulbasaur | Poisons an enemy (75% chance). | Sure, Wide, Lingering, Toxic, Quick (8) |
| Take Down | 20 | Tackle | Bulbasaur | Normal, 90 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Sweeping, Cushioned, Swift (18) |
| Leaf Shield | 22 | Leech Seed | Ivysaur | Halves the damage an ally takes for 2 rounds. | Thick, Shared, Renewing, Quick (7) |
| Razor Leaf | 27 | Vine Whip | Bulbasaur | Grass, 55 power. High critical-hit ratio. | Potent, Draining, Wounding, Sweeping, Twin (13) |
| Body Slam | 30 | Take Down | Ivysaur | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Growth | 34 | Leech Seed | Bulbasaur | Raises its Attack 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Sleep Powder | 41 | Poison Powder | Ivysaur | Puts an enemy to sleep (75% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Solar Beam | 48 | Razor Leaf | Ivysaur | Grass, 120 power. Charges for a round first. | Potent, Draining, Wounding, Keen, Sweeping, Instant, Swift (17) |
| Double-Edge | 50 | Body Slam | Venusaur | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Sweeping, Cushioned, Swift (18) |
| Hyper Beam | 55 | Solar Beam | Venusaur | Normal, 150 power. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Sweeping, Tireless, Swift (17) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Seeding Lash | Vine Whip → Leech Seed | 15 | Bulbasaur | 15% / 30% / 45% |
| Rough Play | Tackle → Growl | 8 | Bulbasaur | 20% / 40% |
| Spore Storm | Razor Leaf → Poison Powder | 30 | Bulbasaur | 10% / 20% / 30% |
| Photosynthesis | Growth → Leaf Shield | 36 | Ivysaur | 50% / 100% |
| Drowsy Sun | Solar Beam → Sleep Powder | 50 | Venusaur | 20% / 40% |

---

## The Charmander line

Stages: Charmander → Charmeleon (Lv16) → Charizard (Lv36). Whole tree: 158 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Scratch | free | – | Charmander | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Growl | free | – | Charmander | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Ember | 9 | Scratch | Charmander | Fire, 40 power. 10% chance to burn. | Potent, Searing, Wounding, Keen, Sweeping, Twin (16) |
| Leer | 15 | Growl | Charmander | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Swords Dance | 25 | Leer | Charmeleon | Raises its Attack 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Slash | 30 | Scratch | Charmander | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (13) |
| Flamethrower | 38 | Ember | Charmander | Fire, 95 power. 10% chance to burn. | Potent, Searing, Wounding, Keen, Sweeping, Swift (16) |
| Fire Spin | 46 | Flamethrower | Charmander | Fire, 15 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Searing, Wounding, Keen, Sweeping, Twin (16) |
| Fire Blast | 50 | Flamethrower | Charizard | Fire, 120 power. 30% chance to burn. | Potent, Searing, Wounding, Keen, Sweeping, Swift (16) |
| Earthquake | 55 | Slash | Charizard | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Smoldering Claws | Scratch → Ember | 11 | Charmander | 15% / 30% / 45% |
| Menace | Leer → Growl | 17 | Charmander | 50% / 100% |
| Melting Heat | Flamethrower → Leer | 40 | Charmander | 30% / 60% |
| Blazing Slash | Slash → Fire Spin | 48 | Charmeleon | 20% / 40% |

---

## The Squirtle line

Stages: Squirtle → Wartortle (Lv16) → Blastoise (Lv36). Whole tree: 167 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Squirtle | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Tail Whip | free | – | Squirtle | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Bubble | 8 | Tackle | Squirtle | Water, 20 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Water Gun | 15 | Bubble | Squirtle | Water, 40 power. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Bite | 22 | Tackle | Squirtle | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Withdraw | 28 | Tail Whip | Squirtle | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Ice Beam | 30 | Water Gun | Wartortle | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |
| Skull Bash | 35 | Bite | Wartortle | Normal, 100 power. Charges for a round first. | Potent, Staggering, Wounding, Keen, Sweeping, Instant, Swift (17) |
| Hydro Pump | 42 | Water Gun | Squirtle | Water, 120 power. | Potent, Rippling, Wounding, Keen, Sweeping, Swift (16) |
| Blizzard | 55 | Ice Beam | Blastoise | Ice, 120 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Splash Tackle | Tackle → Bubble | 10 | Squirtle | 15% / 30% / 45% |
| Snapping Jaws | Bite → Tail Whip | 24 | Squirtle | 30% / 60% |
| Shell Counter | Withdraw → Tail Whip | 30 | Squirtle | 50% / 100% |
| Frost Spray | Hydro Pump → Ice Beam | 46 | Blastoise | 10% / 20% |

---

## The Spearow line

Stages: Spearow → Fearow (Lv20, not in the game yet). Whole tree: 134 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Peck | free | – | Spearow | Flying, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Growl | free | – | Spearow | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Leer | 9 | Growl | Spearow | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Fury Attack | 15 | Peck | Spearow | Normal, 15 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Swift | 20 | Peck | Spearow | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Whirlwind | 22 | Leer | Spearow | Lowers every enemy's Speed 1 stage. | Deep, Lingering, Hexing, Emboldening, Quick (10) |
| Drill Peck | 29 | Fury Attack | Spearow | Flying, 80 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Agility | 36 | Leer | Spearow | Raises its Speed 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Hyper Beam | 45 | Drill Peck | Fearow | Normal, 150 power. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Sweeping, Tireless, Swift (17) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Harrying Pecks | Fury Attack → Leer | 17 | Spearow | 20% / 40% |
| Tailwind | Whirlwind → Agility | 38 | Spearow | 50% / 100% |

---

## The Nidoran F line

Stages: Nidoran F → Nidorina (Lv16, not in the game yet). Whole tree: 145 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Nidoran F | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Growl | free | – | Nidoran F | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Scratch | 8 | Tackle | Nidoran F | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Poison Sting | 14 | Tackle | Nidoran F | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| Tail Whip | 21 | Growl | Nidoran F | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Body Slam | 25 | Tackle | Nidorina | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Bite | 29 | Scratch | Nidoran F | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Fury Swipes | 36 | Scratch | Nidoran F | Normal, 18 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Double Kick | 43 | Bite | Nidoran F | Fighting, 30 power, hits twice. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Toxic Claws | Scratch → Poison Sting | 16 | Nidoran F | 15% / 30% |
| Taunting Bite | Bite → Growl | 31 | Nidoran F | 30% / 60% |

---

## The Nidoran M line

Stages: Nidoran M → Nidorino (Lv16, not in the game yet). Whole tree: 123 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Nidoran M | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Leer | free | – | Nidoran M | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Horn Attack | 8 | Tackle | Nidoran M | Normal, 65 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Poison Sting | 14 | Tackle | Nidoran M | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| Focus Energy | 21 | Leer | Nidoran M | The user's critical-hit chance ×4 for the battle. | Fired-Up, Renewing, Quick (6) |
| Body Slam | 25 | Tackle | Nidorino | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Fury Attack | 29 | Horn Attack | Nidoran M | Normal, 15 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Double Kick | 43 | Horn Attack | Nidoran M | Fighting, 30 power, hits twice. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Poison Horn | Horn Attack → Poison Sting | 16 | Nidoran M | 15% / 30% |
| Battle Cry | Focus Energy → Leer | 23 | Nidoran M | 50% / 100% |

---

## The Pidgey line

Stages: Pidgey → Pidgeotto (Lv18) → Pidgeot (Lv36). Whole tree: 121 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Gust | free | – | Pidgey | Flying, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Sand-Attack | free | – | Pidgey | Lowers an enemy's accuracy 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Quick Attack | 12 | Gust | Pidgey | Normal, 40 power. Always goes first. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Whirlwind | 19 | Sand-Attack | Pidgey | Lowers every enemy's Speed 1 stage. | Deep, Lingering, Hexing, Emboldening, Quick (10) |
| Wing Attack | 28 | Gust | Pidgey | Flying, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Double-Edge | 30 | Quick Attack | Pidgeotto | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Sweeping, Cushioned, Swift (18) |
| Agility | 36 | Whirlwind | Pidgey | Raises its Speed 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Sky Attack | 44 | Wing Attack | Pidgeot | Flying, 140 power. Charges for a round first. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Instant, Swift (14) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Dust Devil | Gust → Sand-Attack | 10 | Pidgey | 20% / 40% |
| Slipstream | Quick Attack → Agility | 38 | Pidgeotto | 15% / 30% |

---

## The Rattata line

Stages: Rattata → Raticate (Lv20, not in the game yet). Whole tree: 115 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Rattata | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Tail Whip | free | – | Rattata | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Quick Attack | 7 | Tackle | Rattata | Normal, 40 power. Always goes first. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Hyper Fang | 14 | Quick Attack | Rattata | Normal, 80 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Focus Energy | 23 | Tail Whip | Rattata | The user's critical-hit chance ×4 for the battle. | Fired-Up, Renewing, Quick (6) |
| Body Slam | 25 | Tackle | Rattata | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Super Fang | 34 | Hyper Fang | Rattata | Normal. Takes half the target's HP. | Staggering, Wounding, Sweeping (7) |
| Hyper Beam | 45 | Super Fang | Raticate | Normal, 150 power. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Sweeping, Tireless, Swift (17) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Nip and Tuck | Quick Attack → Tail Whip | 9 | Rattata | 20% / 40% |
| Gnashing Fangs | Hyper Fang → Super Fang | 36 | Rattata | 10% / 20% |

---

## The Caterpie line

Stages: Caterpie → Metapod (Lv7) → Butterfree (Lv10, not in the game yet). Whole tree: 143 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Caterpie | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| String Shot | free | – | Caterpie | Lowers an enemy's Speed 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Harden | 7 | String Shot | Metapod | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Confusion | 12 | Tackle | Butterfree | Psychic, 50 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Sweeping, Twin (16) |
| Poison Powder | 15 | String Shot | Butterfree | Poisons an enemy (75% chance). | Sure, Wide, Lingering, Toxic, Quick (8) |
| Stun Spore | 16 | Poison Powder | Butterfree | Paralyzes an enemy (75% chance). | Sure, Wide, Lingering, Numbing, Quick (9) |
| Sleep Powder | 17 | Stun Spore | Butterfree | Puts an enemy to sleep (75% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Supersonic | 21 | Confusion | Butterfree | 55% chance to confuse. | Sure, Wide, Lingering, Dizzying, Quick (9) |
| Mega Drain | 25 | Confusion | Butterfree | Grass, 40 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Wounding, Keen, Sweeping, Twin (16) |
| Whirlwind | 26 | Supersonic | Butterfree | Lowers every enemy's Speed 1 stage. | Deep, Lingering, Hexing, Emboldening, Quick (10) |
| Psybeam | 32 | Confusion | Butterfree | Psychic, 65 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Sweeping, Twin (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Silk Shell | Harden → String Shot | 9 | Metapod | 50% / 100% |
| Scale Dust | Psybeam → Stun Spore | 34 | Butterfree | 15% / 30% |

---

## The Weedle line

Stages: Weedle → Kakuna (Lv7) → Beedrill (Lv10, not in the game yet). Whole tree: 122 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Poison Sting | free | – | Weedle | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| String Shot | free | – | Weedle | Lowers an enemy's Speed 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Harden | 7 | String Shot | Kakuna | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Fury Attack | 12 | Poison Sting | Beedrill | Normal, 15 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Focus Energy | 16 | Harden | Beedrill | The user's critical-hit chance ×4 for the battle. | Fired-Up, Renewing, Quick (6) |
| Twineedle | 20 | Fury Attack | Beedrill | Bug, 25 power, hits twice. 20% chance to poison. | Potent, Venomous, Wounding, Keen, Sweeping, Relentless (16) |
| Swords Dance | 25 | Focus Energy | Beedrill | Raises its Attack 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Pin Missile | 30 | Twineedle | Beedrill | Bug, 14 power, hits 2-5 times. | Potent, Venomous, Wounding, Keen, Sweeping, Relentless (16) |
| Agility | 35 | Focus Energy | Beedrill | Raises its Speed 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Webbed Sting | Poison Sting → String Shot | 5 | Weedle | 20% / 40% |
| Stinger Volley | Pin Missile → Poison Sting | 32 | Beedrill | 20% / 40% |

---

## The Oddish line

Stages: Oddish → Gloom (Lv21, not in the game yet) → Vileplume (by stone, not in the game yet). Whole tree: 117 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Absorb | free | – | Oddish | Grass, 20 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Wounding, Keen, Sweeping, Twin (16) |
| Poison Powder | 15 | Absorb | Oddish | Poisons an enemy (75% chance). | Sure, Wide, Lingering, Toxic, Quick (8) |
| Stun Spore | 17 | Poison Powder | Oddish | Paralyzes an enemy (75% chance). | Sure, Wide, Lingering, Numbing, Quick (9) |
| Sleep Powder | 19 | Stun Spore | Oddish | Puts an enemy to sleep (75% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Acid | 24 | Absorb | Oddish | Poison, 40 power. 33% chance to lower its Defense. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| Mega Drain | 25 | Absorb | Gloom | Grass, 40 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Wounding, Keen, Sweeping, Twin (16) |
| Petal Dance | 33 | Acid | Oddish | Grass, 70 power. Hits every enemy. The user becomes confused afterwards. | Potent, Draining, Wounding, Keen, Calm, Twin (15) |
| Solar Beam | 46 | Petal Dance | Oddish | Grass, 120 power. Charges for a round first. | Potent, Draining, Wounding, Keen, Sweeping, Instant, Swift (17) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Spore Sap | Absorb → Poison Powder | 16 | Oddish | 15% / 30% |
| Pollen Dance | Petal Dance → Sleep Powder | 35 | Gloom | 15% / 30% |

---

## The Bellsprout line

Stages: Bellsprout → Weepinbell (Lv21, not in the game yet) → Victreebel (by stone, not in the game yet). Whole tree: 135 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Vine Whip | free | – | Bellsprout | Grass, 35 power. | Potent, Draining, Wounding, Keen, Sweeping, Twin (16) |
| Growth | free | – | Bellsprout | Raises its Attack 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Wrap | 13 | Vine Whip | Bellsprout | Normal, 15 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Poison Powder | 15 | Growth | Bellsprout | Poisons an enemy (75% chance). | Sure, Wide, Lingering, Toxic, Quick (8) |
| Sleep Powder | 18 | Poison Powder | Bellsprout | Puts an enemy to sleep (75% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Stun Spore | 21 | Poison Powder | Bellsprout | Paralyzes an enemy (75% chance). | Sure, Wide, Lingering, Numbing, Quick (9) |
| Acid | 26 | Wrap | Bellsprout | Poison, 40 power. 33% chance to lower its Defense. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| Swords Dance | 30 | Growth | Weepinbell | Raises its Attack 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Razor Leaf | 33 | Vine Whip | Bellsprout | Grass, 55 power. High critical-hit ratio. | Potent, Draining, Wounding, Sweeping, Twin (13) |
| Slam | 42 | Wrap | Bellsprout | Normal, 80 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Snaring Vines | Vine Whip → Wrap | 15 | Bellsprout | 15% / 30% |
| Corroding Grip | Wrap → Acid | 28 | Bellsprout | 20% / 40% |

---

## The Pikachu line

Stages: Pikachu. Whole tree: 117 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Thunder Shock | free | – | Pikachu | Electric, 40 power. 10% chance to paralyze. | Potent, Crackling, Wounding, Keen, Sweeping, Twin (16) |
| Growl | free | – | Pikachu | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Thunder Wave | 9 | Growl | Pikachu | Paralyzes an enemy. Doesn't affect Ground types. | Wide, Lingering, Numbing, Quick (6) |
| Quick Attack | 16 | Thunder Shock | Pikachu | Normal, 40 power. Always goes first. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Swift | 26 | Quick Attack | Pikachu | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Thunderbolt | 30 | Thunder Shock | Pikachu | Electric, 95 power. 10% chance to paralyze. | Potent, Crackling, Wounding, Keen, Sweeping, Swift (16) |
| Agility | 33 | Thunder Wave | Pikachu | Raises its Speed 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Thunder | 43 | Thunderbolt | Pikachu | Electric, 120 power. 10% chance to paralyze. | Potent, Crackling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Static Charge | Quick Attack → Thunder Wave | 18 | Pikachu | 15% / 30% |
| Overcharge | Agility → Thunder Shock | 35 | Pikachu | 50% / 100% |

---

## The Seel line

Stages: Seel → Dewgong (Lv34). Whole tree: 158 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Headbutt | free | – | Seel | Normal, 70 power. 30% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Water Gun | 10 | Headbutt | Seel | Water, 40 power. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Bubble Beam | 25 | Water Gun | Seel | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Growl | 30 | Headbutt | Seel | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Aurora Beam | 35 | Headbutt | Seel | Ice, 65 power. 10% chance to lower its Attack. | Potent, Chilling, Wounding, Keen, Sweeping, Twin (16) |
| Rest | 40 | Growl | Seel | The user heals fully, is cured, and sleeps for 2 rounds. | Renewing, Quick (4) |
| Surf | 40 | Bubble Beam | Dewgong | Water, 95 power. | Potent, Rippling, Wounding, Keen, Sweeping, Swift (16) |
| Take Down | 45 | Headbutt | Seel | Normal, 90 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Sweeping, Cushioned, Swift (18) |
| Ice Beam | 50 | Aurora Beam | Seel | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |
| Blizzard | 55 | Ice Beam | Dewgong | Ice, 120 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Bellow | Headbutt → Growl | 32 | Seel | 20% / 40% |
| Polar Spray | Water Gun → Aurora Beam | 37 | Seel | 10% / 20% |

---

## The Shellder line

Stages: Shellder. Whole tree: 137 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Shellder | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Withdraw | free | – | Shellder | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Water Gun | 10 | Tackle | Shellder | Water, 40 power. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Supersonic | 18 | Withdraw | Shellder | 55% chance to confuse. | Sure, Wide, Lingering, Dizzying, Quick (9) |
| Clamp | 23 | Water Gun | Shellder | Water, 35 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Bubble Beam | 25 | Water Gun | Shellder | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Aurora Beam | 30 | Clamp | Shellder | Ice, 65 power. 10% chance to lower its Attack. | Potent, Chilling, Wounding, Keen, Sweeping, Twin (16) |
| Leer | 39 | Supersonic | Shellder | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Ice Beam | 50 | Aurora Beam | Shellder | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Clam Shell | Withdraw → Clamp | 25 | Shellder | 25% / 50% |
| Icy Grip | Clamp → Aurora Beam | 32 | Shellder | 15% / 30% |

---

## The Psyduck line

Stages: Psyduck → Golduck (Lv33, not in the game yet). Whole tree: 134 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Scratch | free | – | Psyduck | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Water Gun | 8 | Scratch | Psyduck | Water, 40 power. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Bubble Beam | 20 | Water Gun | Psyduck | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Tail Whip | 28 | Scratch | Psyduck | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Confusion | 36 | Tail Whip | Psyduck | Psychic, 50 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Sweeping, Twin (16) |
| Fury Swipes | 43 | Scratch | Psyduck | Normal, 18 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Ice Beam | 45 | Bubble Beam | Golduck | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |
| Hydro Pump | 52 | Bubble Beam | Psyduck | Water, 120 power. | Potent, Rippling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Headache | Water Gun → Confusion | 38 | Psyduck | 10% / 20% |
| Flailing | Fury Swipes → Tail Whip | 45 | Psyduck | 20% / 40% |

---

## The Horsea line

Stages: Horsea → Seadra (Lv32, not in the game yet). Whole tree: 123 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Bubble | free | – | Horsea | Water, 20 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Smokescreen | 19 | Bubble | Horsea | Lowers an enemy's accuracy 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Bubble Beam | 20 | Bubble | Horsea | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Leer | 24 | Smokescreen | Horsea | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Water Gun | 30 | Bubble | Horsea | Water, 40 power. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Agility | 37 | Leer | Horsea | Raises its Speed 2 stages. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Ice Beam | 40 | Bubble Beam | Seadra | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |
| Hydro Pump | 45 | Water Gun | Horsea | Water, 120 power. | Potent, Rippling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Ink Jet | Water Gun → Smokescreen | 32 | Horsea | 20% / 40% |
| Riptide | Agility → Bubble Beam | 39 | Horsea | 25% / 50% |

---

## The Jynx line

Stages: Jynx. Whole tree: 149 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Pound | free | – | Jynx | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Lovely Kiss | free | – | Jynx | Puts an enemy to sleep (75% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Lick | 18 | Pound | Jynx | Ghost, 20 power. 30% chance to paralyze. | Potent, Haunting, Wounding, Keen, Sweeping, Twin (16) |
| Double Slap | 23 | Pound | Jynx | Normal, 15 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Ice Punch | 31 | Lick | Jynx | Ice, 75 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Twin (16) |
| Psychic | 35 | Lovely Kiss | Jynx | Psychic, 90 power. 33% chance to lower its Defense. | Potent, Bewildering, Wounding, Keen, Sweeping, Swift (16) |
| Body Slam | 39 | Double Slap | Jynx | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Thrash | 47 | Body Slam | Jynx | Normal, 90 power. The user becomes confused afterwards. | Potent, Staggering, Wounding, Keen, Sweeping, Calm, Swift (17) |
| Blizzard | 58 | Ice Punch | Jynx | Ice, 120 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Blown Kiss | Double Slap → Lovely Kiss | 25 | Jynx | 10% / 20% |
| Mind Freeze | Psychic → Ice Punch | 37 | Jynx | 15% / 30% |

---

## The Lapras line

Stages: Lapras. Whole tree: 116 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Water Gun | free | – | Lapras | Water, 40 power. | Potent, Rippling, Wounding, Keen, Sweeping, Twin (16) |
| Growl | free | – | Lapras | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Sing | 16 | Growl | Lapras | Puts an enemy to sleep (55% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Body Slam | 25 | Water Gun | Lapras | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Confuse Ray | 31 | Sing | Lapras | Confuses an enemy. | Wide, Lingering, Dizzying, Quick (6) |
| Ice Beam | 38 | Water Gun | Lapras | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |
| Hydro Pump | 46 | Ice Beam | Lapras | Water, 120 power. | Potent, Rippling, Wounding, Keen, Sweeping, Swift (16) |
| Blizzard | 50 | Ice Beam | Lapras | Ice, 120 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Lullaby | Water Gun → Sing | 18 | Lapras | 10% / 20% |
| Haunting Song | Sing → Confuse Ray | 33 | Lapras | 25% / 50% |

---

## The Geodude line

Stages: Geodude → Graveler (Lv25, not in the game yet) → Golem (by stone, not in the game yet). Whole tree: 127 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Geodude | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Defense Curl | free | – | Geodude | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Rock Throw | 11 | Tackle | Geodude | Rock, 50 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Harden | 21 | Defense Curl | Geodude | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Rock Slide | 24 | Rock Throw | Geodude | Rock, 75 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Earthquake | 26 | Rock Throw | Geodude | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Sweeping, Swift (16) |
| Body Slam | 30 | Tackle | Graveler | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Dig | 34 | Earthquake | Graveler | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Sweeping, Instant, Swift (17) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Rolling Stone | Tackle → Rock Throw | 13 | Geodude | 15% / 30% |
| Avalanche | Rock Slide → Earthquake | 28 | Graveler | 10% / 20% |

---

## The Onix line

Stages: Onix. Whole tree: 127 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Tackle | free | – | Onix | Normal, 35 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Screech | free | – | Onix | Lowers an enemy's Defense 2 stages. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Bind | 14 | Tackle | Onix | Normal, 15 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Rock Throw | 19 | Tackle | Onix | Rock, 50 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Rock Slide | 28 | Rock Throw | Onix | Rock, 75 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Slam | 33 | Bind | Onix | Normal, 80 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Earthquake | 38 | Rock Throw | Onix | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Sweeping, Swift (16) |
| Harden | 43 | Screech | Onix | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Crushing Coils | Bind → Screech | 16 | Onix | 25% / 50% |
| Rumbling Rocks | Rock Slide → Screech | 30 | Onix | 15% / 30% |

---

## The Diglett line

Stages: Diglett → Dugtrio (Lv26, not in the game yet). Whole tree: 110 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Scratch | free | – | Diglett | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Growl | 15 | Scratch | Diglett | Lowers an enemy's Attack 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Dig | 19 | Scratch | Diglett | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Sweeping, Instant, Swift (17) |
| Sand-Attack | 24 | Growl | Diglett | Lowers an enemy's accuracy 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Slash | 31 | Scratch | Diglett | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (13) |
| Rock Slide | 35 | Dig | Diglett | Rock, 75 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Earthquake | 40 | Dig | Diglett | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Dust Cloud | Dig → Sand-Attack | 21 | Diglett | 20% / 40% |
| Tunneling Claws | Scratch → Dig | 26 | Diglett | 5% / 10% |

---

## The Sandshrew line

Stages: Sandshrew → Sandslash (Lv22, not in the game yet). Whole tree: 149 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Scratch | free | – | Sandshrew | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Sand-Attack | 10 | Scratch | Sandshrew | Lowers an enemy's accuracy 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Slash | 17 | Scratch | Sandshrew | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (13) |
| Poison Sting | 24 | Scratch | Sandshrew | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| Dig | 28 | Sand-Attack | Sandshrew | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Sweeping, Instant, Swift (17) |
| Swift | 31 | Slash | Sandshrew | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Fury Swipes | 38 | Slash | Sandshrew | Normal, 18 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Rock Slide | 40 | Dig | Sandshrew | Rock, 75 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Earthquake | 45 | Dig | Sandslash | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Sweeping, Swift (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Sandstorm | Slash → Sand-Attack | 19 | Sandshrew | 20% / 40% |
| Barbed Claws | Fury Swipes → Poison Sting | 40 | Sandshrew | 15% / 30% |

---

## The Ekans line

Stages: Ekans → Arbok (Lv22, not in the game yet). Whole tree: 122 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Wrap | free | – | Ekans | Normal, 15 power. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Leer | free | – | Ekans | Lowers an enemy's Defense 1 stage. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Poison Sting | 10 | Wrap | Ekans | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |
| Bite | 17 | Wrap | Ekans | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Glare | 24 | Leer | Ekans | Paralyzes an enemy (75% chance). | Sure, Wide, Lingering, Numbing, Quick (9) |
| Screech | 31 | Glare | Ekans | Lowers an enemy's Defense 2 stages. | Deep, Wide, Lingering, Hexing, Emboldening, Quick (11) |
| Dig | 33 | Bite | Arbok | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Sweeping, Instant, Swift (17) |
| Acid | 38 | Poison Sting | Ekans | Poison, 40 power. 33% chance to lower its Defense. | Potent, Venomous, Wounding, Keen, Sweeping, Twin (16) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Venom Coils | Wrap → Poison Sting | 12 | Ekans | 15% / 30% |
| Paralyzing Gaze | Bite → Glare | 26 | Ekans | 15% / 30% |

---

## The Jigglypuff line

Stages: Jigglypuff. Whole tree: 98 points.

| Move | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- |
| Pound | free | – | Jigglypuff | Normal, 40 power. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Sing | free | – | Jigglypuff | Puts an enemy to sleep (55% chance). | Sure, Wide, Lingering, Deep, Quick (9) |
| Defense Curl | 14 | Sing | Jigglypuff | Raises its Defense 1 stage. | Greater, Renewing, Fortifying, Warding, Quick (10) |
| Double Slap | 24 | Pound | Jigglypuff | Normal, 15 power, hits 2-5 times. | Potent, Staggering, Wounding, Keen, Sweeping, Relentless (16) |
| Rest | 29 | Defense Curl | Jigglypuff | The user heals fully, is cured, and sleeps for 2 rounds. | Renewing, Quick (4) |
| Body Slam | 34 | Double Slap | Jigglypuff | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Sweeping, Twin (16) |
| Double-Edge | 39 | Body Slam | Jigglypuff | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Sweeping, Cushioned, Swift (18) |

| Link | Sets off | Lv | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Lullaby Slaps | Double Slap → Sing | 26 | Jigglypuff | 10% / 20% |
| Heavy Sleeper | Body Slam → Sing | 36 | Jigglypuff | 10% / 20% |

<!-- trees:end -->
