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

- **1 point per level-up.** A Pokémon has `level − 3` points in total (none
  below Lv3): 2 for a new Lv5 starter, 97 at Lv100.
- **Costs** (`Skill.cost`, points per rank): a move costs by its power
  (`skills.POWER_TIERS`): status moves and power ≤ 40: **1**; 41–70: **2**;
  71–99: **3**; 100 and up (and Super Fang): **4**. Each rank of a buff
  costs 1; each rank of a link **2** (`LINK_COST`). The first moves (the
  base attacks) are free.
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
   up to 24 levels later), and for each further rank of a buff or link
   **5 more levels** (`skills.RANK_LEVELS`): a Lv10 buff's ranks open at
   Lv10, 15, 20, 25, 30;
   A move never opens before the line learns it by level in **Red/Blue**
   (`skills.GEN1_LEVELS`: the earliest level any of its stages learns it
   at; e.g. Geodude's Rock Throw at Lv16, Venonat's Confusion at Lv27).
   Moves the line only gets from TMs keep their tree level;
2. it has **every parent** skill (a move's path; a buff's place in its
   branch; both moves of a link);
3. the Pokémon is at least the **evolution stage** the skill needs (every
   damaging move's capstone needs the line's last stage);
4. it has the **points** for it (strong moves and links cost more).

On top of each skill's own level and stage, tree-wide rules
(`skills._gated`) hold strong moves and the mid-game tricks back:

| Skill | Earliest | Evolution |
| --- | --- | --- |
| Move of power 71–99 | Lv25 | the line's first evolution |
| Move of power 100+ (or Super Fang) | Lv35 | the line's last stage |
| A damaging move's area buff | its own level (see Area buffs) | by its move's strength |
| Wide (status moves on every enemy) | Lv25 | the first evolution |
| Wide on a move that disables (sleep, paralysis, freeze, confusion: Sleep Powder, Stun Spore, Sing, Supersonic, Thunder Wave, Glare, ...) | Lv30 | the first evolution |
| Link setting off a status or stat move (Growl, Leer, Leech Seed, Poison Powder, ...) | Lv20 | the first evolution |
| *Strong* link: setting off a damaging move, or one that disables or binds | Lv25, at most 2 ranks | the first evolution |

A line that doesn't evolve gets each of these 5 levels later. A move set
off by a link only hits the one aimed at: its area buff or Wide doesn't
carry over (`BattleScene._apply`).

(A stage the game doesn't have yet, e.g. Kadabra, can't be reached: those
skills wait for it.) Older saves get every point back once
(`saves.SKILLS_VERSION`), to spend again under these rules.

### Area buffs

Each damaging move reaches past its target in its own way, or not at all
(`skills.AREAS`; Tackle, Scratch, Bite, Peck, Quick Attack, ... stay
single-target): **sweep** (hits every enemy, the others at a share),
**reach** (also hits one enemy standing next to the target, at a share)
or **spill** (a chance to put a status or a stat drop on each enemy next
to the target, no damage). Each opens at its own level (or 6 levels after
its move, if later), at the first evolution, or the last stage for
strong moves (power 71+, counting average hits and crits,
`skills._sweep_power`: Slash crits half the time, so it counts as 85). In
one tree, no two open within 3 levels of each other (`AREA_STEP`): the
later one waits.

| Move | Buff | Effect (rank 1 / 2) | Earliest | Evolution |
| --- | --- | --- | --- | --- |
| Slash | Sweeping | every enemy, the others at 30% / 45% | Lv40 | last stage |
| Fury Swipes | Sweeping | every enemy, the others at 20% / 30% | Lv30 | first evolution |
| Razor Leaf | Scattering | every enemy, the others at 30% / 40% | Lv34 | first evolution |
| Gust | Gale | every enemy, the others at 20% / 30% | Lv26 | first evolution |
| Wing Attack | Gale | every enemy, the others at 25% / 35% | Lv31 | first evolution |
| Swift | Starfall | every enemy, the others at 30% / 40% | Lv33 | first evolution |
| Bubble | Foaming | every enemy, the others at 20% / 30% | Lv25 | first evolution |
| Bubble Beam | Foaming | every enemy, the others at 30% / 40% | Lv37 | first evolution |
| Surf | Tidal | every enemy, the others at 50% / 65% | Lv50 | last stage |
| Rock Slide | Landslide | every enemy, the others at 35% / 50% | Lv44 | last stage |
| Earthquake | Shockwave | every enemy, the others at 50% / 65% | Lv55 | last stage |
| Blizzard | Whiteout | every enemy, the others at 45% / 60% | Lv58 | last stage |
| Pin Missile | Volley | every enemy, the others at 25% / 35% | Lv32 | first evolution |
| Thrash | Rampaging | every enemy, the others at 30% / 45% | Lv46 | last stage |
| Thunder Shock | Arcing | one enemy next to the target, at 30% / 45% | Lv27 | first evolution |
| Thunderbolt | Arcing | one enemy next to the target, at 40% / 55% | Lv42 | last stage |
| Thunder | Arcing | one enemy next to the target, at 50% / 65% | Lv55 | last stage |
| Water Gun | Piercing | one enemy next to the target, at 25% / 40% | Lv28 | first evolution |
| Hydro Pump | Piercing | one enemy next to the target, at 45% / 60% | Lv52 | last stage |
| Vine Whip | Lashing | one enemy next to the target, at 30% / 45% | Lv25 | first evolution |
| Rock Throw | Shrapnel | one enemy next to the target, at 35% / 50% | Lv30 | first evolution |
| Body Slam | Bowling | one enemy next to the target, at 30% / 45% | Lv38 | last stage |
| Slam | Bowling | one enemy next to the target, at 35% / 50% | Lv41 | last stage |
| Take Down | Bowling | one enemy next to the target, at 35% / 50% | Lv39 | last stage |
| Double-Edge | Bowling | one enemy next to the target, at 40% / 55% | Lv48 | last stage |
| Skull Bash | Bowling | one enemy next to the target, at 45% / 60% | Lv50 | last stage |
| Hyper Beam | Piercing | one enemy next to the target, at 50% / 70% | Lv60 | last stage |
| Solar Beam | Piercing | one enemy next to the target, at 45% / 60% | Lv56 | last stage |
| Sky Attack | Piercing | one enemy next to the target, at 50% / 65% | Lv58 | last stage |
| Ember | Spreading | each enemy next to the target: 10% / 20% chance to burn | Lv25 | first evolution |
| Fire Spin | Spreading | each enemy next to the target: 15% / 25% chance to burn | Lv30 | first evolution |
| Flamethrower | Spreading | each enemy next to the target: 15% / 30% chance to burn | Lv42 | last stage |
| Fire Blast | Spreading | each enemy next to the target: 25% / 40% chance to burn | Lv55 | last stage |
| Poison Sting | Venom Cloud | each enemy next to the target: 10% / 20% chance to poison | Lv26 | first evolution |
| Acid | Splashing | each enemy next to the target: 20% / 40% chance to lower Defense | Lv30 | first evolution |
| Ice Beam | Frost | each enemy next to the target: 25% / 50% chance to lower Speed | Lv45 | last stage |
| Aurora Beam | Frost | each enemy next to the target: 20% / 40% chance to lower Attack | Lv36 | first evolution |
| Ice Punch | Frost | each enemy next to the target: 20% / 40% chance to lower Speed | Lv44 | last stage |
| Confusion | Rippling | each enemy next to the target: 10% / 20% chance to confuse | Lv30 | first evolution |
| Psybeam | Rippling | each enemy next to the target: 15% / 25% chance to confuse | Lv36 | first evolution |
| Psychic | Rippling | each enemy next to the target: 20% / 35% chance to confuse | Lv50 | last stage |
| Dig | Cave-in | each enemy next to the target: 25% / 50% chance to lower accuracy | Lv40 | last stage |

### The buffs of each move

Every move gets its branches from its kind (`skills._buffs`); per rank:

**Damaging moves**

| Buff | Ranks | Effect | Opens | Needs |
| --- | --- | --- | --- | --- |
| Potent | 3 | +10% power per rank | move's Lv | the move |
| *Rider* | 3 | by type: Searing (fire, +10% burn), Crackling (electric, +10% paralysis), Chilling (ice, +5% freeze), Venomous (poison/bug, +10% poison), Draining (grass, heals 15% of the damage), Rippling (water, 10% Speed down), Dusting (ground, 10% accuracy down), Bewildering/Haunting (psychic/ghost, +10% confusion), Staggering (others, +10% flinch) | +3 | the move |
| Wounding | 2 | wounds: 1/16, then 1/12 of max HP per round for 3 rounds (not on weak moves) | +16 | the rider |
| Keen | 2 | crits ×3/×4 as likely (not on high-crit or weak moves) | +6 | Potent |
| *Area* | 2 | the move's own area buff, if it has one (see Area buffs) | its own level | Potent |
| Instant / Tireless / Cushioned / Calm | 1–2 | take away a drawback: the charge round, the recharge round, recoil (half, then none), the user's confusion | +10 to +20 | Potent |
| *Capstone* | 1 | Swift (power ≥ 90: always goes first), Relentless (multi-hit: 1 more hit) or Twin (hits twice at −30% power) | +24 (Lv30 at least), last stage | Keen |

Super Fang (half the target's HP) has no Potent, Keen or capstone. Weak
moves (power 40 or less, `WEAK_POWER`: Tackle, Scratch, Ember, Gust, ...)
get no Wounding or Keen.

**Moves that lower an enemy's stat** (Leer, Growl, Sand-Attack, ...)

| Buff | Ranks | Effect | Opens | Needs |
| --- | --- | --- | --- | --- |
| Deep | 2 | lowers the stat 1 more stage per rank | move's Lv | the move |
| Follow-up | 2 | then the user hits the same enemy with its basic attack, at 50% / 75% power | +4 | the move |
| Wide | 1 | works on every enemy (Whirlwind, already on every enemy: **Gale**, also hits them for 20 power) | +4 (Lv25) | the move |
| Exposing | 2 | for 3 rounds the target takes 15% / 25% more damage from everyone | +6 | Deep |
| Emboldening | 2 | also raises one of the user's stats (Leer: Attack; Growl: Defense; Sand-Attack, String Shot: Speed) | +12 | Deep |
| Quick | 1 | always goes first | +10 | the move |

**Moves that raise the user's stat** (Growth, Harden, Agility, ...)

| Buff | Ranks | Effect | Opens | Needs |
| --- | --- | --- | --- | --- |
| Greater | 2 | raises the stat 1 more stage per rank | move's Lv | the move |
| Empowering | 2 | the user's next damaging move deals 30% / 60% more | +4 | the move |
| Renewing | 3 | heals the user 1/16, 1/8, 1/4 of its max HP | +6 | the move |
| Spiked (Defense moves: Harden, Withdraw, Defense Curl) | 2 | for 3 rounds, whoever hits the user loses 1/16 / 1/8 of its max HP | +8 | the move |
| Rallying | 1 | works on the whole party | +10 (Lv25) | the move |
| Quick | 1 | always goes first | +8 | the move |

Focus Energy: Fired-Up (also Attack +1/+2), Empowering and Rallying.

**Moves that inflict a status or confusion** (Poison Powder, Sing, Supersonic, ...)

| Buff | Ranks | Effect | Opens | Needs |
| --- | --- | --- | --- | --- |
| Sure | 3 | +8% chance to work per rank, up to 100% | move's Lv | the move |
| Wide | 1 | works on every enemy | +6 (Lv25; sleep, paralysis, confusion Lv30) | the move |
| Contagious | 2 | at the end of each round, 15% / 30% chance its status (or confusion) spreads to an enemy next to it (with its buffs) | +10 (Lv25) | Sure |
| Poison: Toxic, Siphoning | 1, 2 | the poison gets worse every round; the user heals 50% / 100% of the poison damage | +12, +8 | Sure |
| Sleep: Deep, Nightmare | 2, 2 | it sleeps 1 / 2 rounds longer; while asleep it loses 1/16 / 1/8 of its max HP a round | +12, +8 | Sure |
| Paralysis: Shocking | 2 | while paralyzed it takes 15% / 25% more damage | +8 | Sure |
| Confusion: Maddening | 2 | while confused it hurts itself 66% / 75% of the time (not 50%) | +8 | Sure |
| Quick | 1 | always goes first | +8 | the move |

**Others:** Leech Seed (Deep-Rooted: drains more; Spreading: when its
target faints, the seed jumps to an enemy next to it), Leaf Shield and
Reflect (Thick: longer; Shared: the whole party), Recover (Cleansing:
also cures the user's status), Rest (Light Sleep: sleeps 1 round); each
with Wide/Shared, Lingering or Renewing, and Quick.

Wide, Contagious, Rallying and the area buffs open at least 3 levels
apart in one tree (`AREA_STEP`), so no two group effects come at once.

### In battle

- **Fight** uses the basic attack (Tackle for Bulbasaur), with its buffs.
- **Skills:** up to **4 equipped moves**, like Gen 1's four move slots.
  Learned moves that aren't equipped can be swapped in outside battle
  (skill tree: **E** on the move; with all 4 slots full it asks which one
  it replaces). Learning a move with all 4 slots full asks the same right
  away, as Gen 1 did ("forget a move?"); X leaves it unequipped.
- Buffs and links work on their move automatically. A link's set-off move
  shows its name over the user and "Vine Whip set off Leech Seed!". It
  only hits the one aimed at (no area buff carries over).
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
  every enemy, the others at 35%); Focus Energy works as intended (Gen 1's was bugged).
  Mirror Move, Disable, Mist and other moves that don't fit are left out.
- **Status moves** that inflict a status or confusion have their Gen 1
  hit chance (Sleep Powder 75%, Sing 55%, ...); everything else always
  works.
- Lines that evolve by stone (Pikachu, Shellder, Oddish and Bellsprout's
  last stage) stop at the last stage reachable by level for now.

---

<!-- trees:start -->

## The Bulbasaur line

Stages: Bulbasaur → Ivysaur (Lv16) → Venusaur (Lv32). Whole tree: 203 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Bulbasaur | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Growl | – | free | – | Bulbasaur | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Leech Seed | 1 | 7 | Growl | Bulbasaur | 90% accurate. Seeds an enemy: drains 1/16 of its max HP each round. Doesn't affect Grass types. | Deep-Rooted, Spreading, Wide, Lingering, Quick (8) |
| Vine Whip | 1 | 13 | Tackle | Bulbasaur | Grass, 35 power. | Potent, Draining, Lashing, Twin (9) |
| Poison Powder | 1 | 20 | Growl | Bulbasaur | Poisons an enemy (75% chance). | Sure, Wide, Contagious, Toxic, Siphoning, Quick (10) |
| Take Down | 3 | 25 | Tackle | Ivysaur | Normal, 90 power. 85% accurate. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |
| Leaf Shield | 1 | 22 | Leech Seed | Ivysaur | Halves the damage an ally takes for 2 rounds. | Thick, Shared, Renewing, Quick (7) |
| Razor Leaf | 2 | 27 | Vine Whip | Bulbasaur | Grass, 55 power. 95% accurate. High critical-hit ratio. | Potent, Draining, Wounding, Scattering, Twin (11) |
| Body Slam | 3 | 30 | Take Down | Ivysaur | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Growth | 1 | 34 | Leech Seed | Bulbasaur | Raises its Attack 1 stage. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Sleep Powder | 1 | 41 | Poison Powder | Ivysaur | Puts an enemy to sleep (75% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Solar Beam | 4 | 48 | Razor Leaf | Venusaur | Grass, 120 power. Charges for a round first. | Potent, Draining, Wounding, Keen, Piercing, Instant, Swift (14) |
| Double-Edge | 4 | 50 | Body Slam | Venusaur | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |
| Hyper Beam | 4 | 55 | Solar Beam | Venusaur | Normal, 150 power. 90% accurate. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Piercing, Tireless, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Seeding Lash | Vine Whip → Leech Seed | 20 / 25 / 30 | Ivysaur | 15% / 30% / 45% |
| Rough Play | Tackle → Growl | 20 / 25 | Ivysaur | 20% / 40% |
| Spore Storm | Razor Leaf → Poison Powder | 30 / 35 / 40 | Ivysaur | 10% / 20% / 30% |
| Photosynthesis | Growth → Leaf Shield | 36 / 41 | Ivysaur | 50% / 100% |
| Drowsy Sun | Solar Beam → Sleep Powder | 50 / 55 | Venusaur | 20% / 40% |

---

## The Charmander line

Stages: Charmander → Charmeleon (Lv16) → Charizard (Lv36). Whole tree: 137 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | – | free | – | Charmander | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Growl | – | free | – | Charmander | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Ember | 1 | 9 | Scratch | Charmander | Fire, 40 power. 10% chance to burn. | Potent, Searing, Spreading, Twin (9) |
| Leer | 1 | 15 | Growl | Charmander | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Swords Dance | 1 | 25 | Leer | Charmeleon | Raises its Attack 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Slash | 2 | 30 | Scratch | Charmander | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (11) |
| Flamethrower | 3 | 38 | Ember | Charmeleon | Fire, 95 power. 10% chance to burn. | Potent, Searing, Wounding, Keen, Spreading, Swift (13) |
| Fire Spin | 1 | 46 | Flamethrower | Charmander | Fire, 15 power. 70% accurate. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Searing, Spreading, Twin (9) |
| Fire Blast | 4 | 50 | Flamethrower | Charizard | Fire, 120 power. 85% accurate. 30% chance to burn. | Potent, Searing, Wounding, Keen, Spreading, Swift (13) |
| Earthquake | 4 | 55 | Slash | Charizard | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Shockwave, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Smoldering Claws | Scratch → Ember | 25 / 30 | Charmeleon | 15% / 30% |
| Menace | Leer → Growl | 20 / 25 | Charmeleon | 50% / 100% |
| Melting Heat | Flamethrower → Leer | 40 / 45 | Charmeleon | 30% / 60% |
| Blazing Slash | Slash → Fire Spin | 48 / 53 | Charmeleon | 20% / 40% |

---

## The Squirtle line

Stages: Squirtle → Wartortle (Lv16) → Blastoise (Lv36). Whole tree: 146 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Squirtle | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Tail Whip | – | free | – | Squirtle | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Bubble | 1 | 8 | Tackle | Squirtle | Water, 30 power. 33% chance to lower its Speed. | Potent, Rippling, Foaming, Twin (9) |
| Water Gun | 1 | 15 | Bubble | Squirtle | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Bite | 2 | 22 | Tackle | Squirtle | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Withdraw | 1 | 28 | Tail Whip | Squirtle | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Ice Beam | 3 | 30 | Water Gun | Wartortle | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Skull Bash | 4 | 35 | Bite | Blastoise | Normal, 100 power. Charges for a round first. | Potent, Staggering, Wounding, Keen, Bowling, Instant, Swift (14) |
| Hydro Pump | 4 | 42 | Water Gun | Blastoise | Water, 120 power. 80% accurate. | Potent, Rippling, Wounding, Keen, Piercing, Swift (13) |
| Blizzard | 4 | 55 | Ice Beam | Blastoise | Ice, 120 power. 90% accurate. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Whiteout, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Splash Tackle | Tackle → Bubble | 25 / 30 | Wartortle | 15% / 30% |
| Snapping Jaws | Bite → Tail Whip | 24 / 29 | Wartortle | 30% / 60% |
| Shell Counter | Withdraw → Tail Whip | 30 / 35 | Wartortle | 50% / 100% |
| Frost Spray | Hydro Pump → Ice Beam | 46 / 51 | Blastoise | 10% / 20% |

---

## The Spearow line

Stages: Spearow → Fearow (Lv20). Whole tree: 112 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Peck | – | free | – | Spearow | Flying, 35 power. | Potent, Staggering, Twin (7) |
| Growl | – | free | – | Spearow | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Leer | 1 | 9 | Growl | Spearow | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Fury Attack | 1 | 15 | Peck | Spearow | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Swift | 2 | 20 | Peck | Spearow | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Starfall, Twin (13) |
| Whirlwind | 1 | 22 | Leer | Spearow | 85% accurate. Lowers every enemy's Speed 1 stage. | Deep, Follow-up, Gale, Exposing, Emboldening, Quick (10) |
| Drill Peck | 3 | 29 | Fury Attack | Fearow | Flying, 80 power. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Agility | 1 | 36 | Leer | Spearow | Raises its Speed 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Hyper Beam | 4 | 45 | Drill Peck | Fearow | Normal, 150 power. 90% accurate. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Piercing, Tireless, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Harrying Pecks | Fury Attack → Leer | 20 / 25 | Fearow | 20% / 40% |
| Tailwind | Whirlwind → Agility | 38 / 43 | Fearow | 50% / 100% |

---

## The Nidoran F line

Stages: Nidoran F → Nidorina (Lv16). Whole tree: 101 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Nidoran F | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Growl | – | free | – | Nidoran F | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Scratch | 1 | 8 | Tackle | Nidoran F | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Poison Sting | 1 | 14 | Tackle | Nidoran F | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Venom Cloud, Twin (9) |
| Tail Whip | 1 | 21 | Growl | Nidoran F | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Body Slam | 3 | 25 | Tackle | Nidorina | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Bite | 2 | 29 | Scratch | Nidoran F | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Fury Swipes | 1 | 36 | Scratch | Nidoran F | Normal, 18 power, hits 2-5 times. 80% accurate. | Potent, Staggering, Sweeping, Relentless (9) |
| Double Kick | 1 | 43 | Bite | Nidoran F | Fighting, 30 power, hits twice. | Potent, Staggering, Relentless (7) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Toxic Claws | Scratch → Poison Sting | 25 / 30 | Nidorina | 15% / 30% |
| Taunting Bite | Bite → Growl | 31 / 36 | Nidorina | 30% / 60% |

---

## The Nidoran M line

Stages: Nidoran M → Nidorino (Lv16). Whole tree: 90 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Nidoran M | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Leer | – | free | – | Nidoran M | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Horn Attack | 2 | 8 | Tackle | Nidoran M | Normal, 65 power. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Poison Sting | 1 | 14 | Tackle | Nidoran M | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Venom Cloud, Twin (9) |
| Focus Energy | 1 | 21 | Leer | Nidoran M | The user's critical-hit chance ×4 for the battle. | Fired-Up, Empowering, Rallying, Renewing, Quick (9) |
| Body Slam | 3 | 25 | Tackle | Nidorino | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Fury Attack | 1 | 29 | Horn Attack | Nidoran M | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Double Kick | 1 | 43 | Horn Attack | Nidoran M | Fighting, 30 power, hits twice. | Potent, Staggering, Relentless (7) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Poison Horn | Horn Attack → Poison Sting | 25 / 30 | Nidorino | 15% / 30% |
| Battle Cry | Focus Energy → Leer | 23 / 28 | Nidorino | 50% / 100% |

---

## The Pidgey line

Stages: Pidgey → Pidgeotto (Lv18) → Pidgeot (Lv36). Whole tree: 102 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Gust | – | free | – | Pidgey | Normal, 40 power. | Potent, Staggering, Gale, Twin (9) |
| Sand-Attack | 1 | 5 | Gust | Pidgey | Lowers an enemy's accuracy 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Quick Attack | 1 | 12 | Gust | Pidgey | Normal, 40 power. Always goes first. | Potent, Staggering, Twin (7) |
| Whirlwind | 1 | 19 | Sand-Attack | Pidgey | 85% accurate. Lowers every enemy's Speed 1 stage. | Deep, Follow-up, Gale, Exposing, Emboldening, Quick (10) |
| Wing Attack | 1 | 28 | Gust | Pidgey | Flying, 35 power. | Potent, Staggering, Gale, Twin (9) |
| Double-Edge | 4 | 35 | Quick Attack | Pidgeot | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |
| Agility | 1 | 36 | Whirlwind | Pidgey | Raises its Speed 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Sky Attack | 4 | 44 | Wing Attack | Pidgeot | Flying, 140 power. 90% accurate. Charges for a round first. High critical-hit ratio. | Potent, Staggering, Wounding, Piercing, Instant, Swift (12) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Dust Devil | Gust → Sand-Attack | 20 / 25 | Pidgeotto | 20% / 40% |
| Slipstream | Quick Attack → Agility | 38 / 43 | Pidgeotto | 15% / 30% |

---

## The Rattata line

Stages: Rattata → Raticate (Lv20). Whole tree: 100 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Rattata | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Tail Whip | – | free | – | Rattata | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Quick Attack | 1 | 7 | Tackle | Rattata | Normal, 40 power. Always goes first. | Potent, Staggering, Twin (7) |
| Hyper Fang | 3 | 25 | Quick Attack | Raticate | Normal, 80 power. 90% accurate. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Focus Energy | 1 | 23 | Tail Whip | Rattata | The user's critical-hit chance ×4 for the battle. | Fired-Up, Empowering, Rallying, Renewing, Quick (9) |
| Body Slam | 3 | 25 | Tackle | Raticate | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Super Fang | 4 | 35 | Hyper Fang | Raticate | Normal. Takes half the target's HP. 90% accurate. | Staggering, Wounding (5) |
| Hyper Beam | 4 | 45 | Super Fang | Raticate | Normal, 150 power. 90% accurate. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Piercing, Tireless, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Nip and Tuck | Quick Attack → Tail Whip | 20 / 25 | Raticate | 20% / 40% |
| Gnashing Fangs | Hyper Fang → Super Fang | 36 / 41 | Raticate | 10% / 20% |

---

## The Caterpie line

Stages: Caterpie → Metapod (Lv7) → Butterfree (Lv10). Whole tree: 129 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Caterpie | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| String Shot | – | free | – | Caterpie | 95% accurate. Lowers an enemy's Speed 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Harden | 1 | 7 | String Shot | Metapod | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Confusion | 2 | 12 | Tackle | Butterfree | Psychic, 50 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |
| Poison Powder | 1 | 15 | String Shot | Butterfree | Poisons an enemy (75% chance). | Sure, Wide, Contagious, Toxic, Siphoning, Quick (10) |
| Stun Spore | 1 | 16 | Poison Powder | Butterfree | Paralyzes an enemy (75% chance). | Sure, Wide, Contagious, Shocking, Quick (9) |
| Sleep Powder | 1 | 17 | Stun Spore | Butterfree | Puts an enemy to sleep (75% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Supersonic | 1 | 21 | Confusion | Butterfree | 55% chance to confuse. | Sure, Wide, Contagious, Maddening, Quick (9) |
| Mega Drain | 1 | 25 | Confusion | Butterfree | Grass, 40 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Twin (7) |
| Whirlwind | 1 | 26 | Supersonic | Butterfree | 85% accurate. Lowers every enemy's Speed 1 stage. | Deep, Follow-up, Gale, Exposing, Emboldening, Quick (10) |
| Psybeam | 2 | 32 | Confusion | Butterfree | Psychic, 65 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Silk Shell | Harden → String Shot | 20 / 25 | Metapod | 50% / 100% |
| Scale Dust | Psybeam → Stun Spore | 34 / 39 | Butterfree | 15% / 30% |

---

## The Weedle line

Stages: Weedle → Kakuna (Lv7) → Beedrill (Lv10). Whole tree: 95 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Poison Sting | – | free | – | Weedle | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Venom Cloud, Twin (9) |
| String Shot | – | free | – | Weedle | 95% accurate. Lowers an enemy's Speed 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Harden | 1 | 7 | String Shot | Kakuna | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Fury Attack | 1 | 12 | Poison Sting | Beedrill | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Focus Energy | 1 | 16 | Harden | Beedrill | The user's critical-hit chance ×4 for the battle. | Fired-Up, Empowering, Rallying, Renewing, Quick (9) |
| Twineedle | 1 | 20 | Fury Attack | Beedrill | Bug, 25 power, hits twice. 20% chance to poison. | Potent, Venomous, Relentless (7) |
| Swords Dance | 1 | 25 | Focus Energy | Beedrill | Raises its Attack 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Pin Missile | 1 | 30 | Twineedle | Beedrill | Bug, 14 power, hits 2-5 times. 85% accurate. | Potent, Venomous, Volley, Relentless (9) |
| Agility | 1 | 35 | Focus Energy | Beedrill | Raises its Speed 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Webbed Sting | Poison Sting → String Shot | 20 / 25 | Kakuna | 20% / 40% |
| Stinger Volley | Pin Missile → Poison Sting | 32 / 37 | Beedrill | 20% / 40% |

---

## The Oddish line

Stages: Oddish → Gloom (Lv21, not in the game yet) → Vileplume (by stone, not in the game yet). Whole tree: 98 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Absorb | – | free | – | Oddish | Grass, 20 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Twin (7) |
| Poison Powder | 1 | 15 | Absorb | Oddish | Poisons an enemy (75% chance). | Sure, Wide, Contagious, Toxic, Siphoning, Quick (10) |
| Stun Spore | 1 | 17 | Poison Powder | Oddish | Paralyzes an enemy (75% chance). | Sure, Wide, Contagious, Shocking, Quick (9) |
| Sleep Powder | 1 | 19 | Stun Spore | Oddish | Puts an enemy to sleep (75% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Acid | 1 | 24 | Absorb | Oddish | Poison, 40 power. 33% chance to lower its Defense. | Potent, Venomous, Splashing, Twin (9) |
| Mega Drain | 1 | 25 | Absorb | Gloom | Grass, 40 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Twin (7) |
| Petal Dance | 2 | 33 | Acid | Oddish | Grass, 70 power. Hits every enemy, the others at 35% damage. The user becomes confused afterwards. | Potent, Draining, Wounding, Keen, Calm, Twin (12) |
| Solar Beam | 4 | 46 | Petal Dance | Vileplume | Grass, 120 power. Charges for a round first. | Potent, Draining, Wounding, Keen, Piercing, Instant, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Spore Sap | Absorb → Poison Powder | 20 / 25 | Gloom | 15% / 30% |
| Pollen Dance | Petal Dance → Sleep Powder | 35 / 40 | Gloom | 15% / 30% |

---

## The Goldeen line

Stages: Goldeen → Seaking (Lv33, not in the game yet). Whole tree: 126 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Peck | – | free | – | Goldeen | Flying, 35 power. | Potent, Staggering, Twin (7) |
| Tail Whip | – | free | – | Goldeen | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Water Gun | 1 | 10 | Peck | Goldeen | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Supersonic | 1 | 19 | Tail Whip | Goldeen | 55% chance to confuse. | Sure, Wide, Contagious, Maddening, Quick (9) |
| Horn Attack | 2 | 24 | Peck | Goldeen | Normal, 65 power. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Bubble Beam | 2 | 24 | Water Gun | Goldeen | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Foaming, Twin (13) |
| Fury Attack | 1 | 30 | Horn Attack | Goldeen | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Agility | 1 | 54 | Supersonic | Goldeen | Raises its Speed 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Ice Beam | 3 | 40 | Bubble Beam | Seaking | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Double-Edge | 4 | 42 | Fury Attack | Seaking | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Splash Peck | Peck → Water Gun | 25 / 30 | Seaking | 15% / 30% |
| Dizzy Dive | Horn Attack → Supersonic | 25 / 30 | Seaking | 15% / 30% |

---

## The Staryu line

Stages: Staryu → Starmie (by stone). Whole tree: 149 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Staryu | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Water Gun | 1 | 17 | Tackle | Staryu | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Harden | 1 | 22 | Tackle | Staryu | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Recover | 1 | 27 | Harden | Staryu | Heals the user 1/2 of its max HP. | Cleansing, Renewing, Quick (5) |
| Swift | 2 | 32 | Tackle | Staryu | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Starfall, Twin (13) |
| Bubble Beam | 2 | 24 | Water Gun | Staryu | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Foaming, Twin (13) |
| Thunder Wave | 1 | 26 | Harden | Staryu | Paralyzes an enemy. Doesn't affect Ground types. | Wide, Contagious, Shocking, Quick (6) |
| Psychic | 3 | 36 | Swift | Starmie | Psychic, 90 power. 33% chance to lower its Defense. | Potent, Bewildering, Wounding, Keen, Rippling, Swift (13) |
| Thunderbolt | 3 | 38 | Thunder Wave | Starmie | Electric, 95 power. 10% chance to paralyze. | Potent, Crackling, Wounding, Keen, Arcing, Swift (13) |
| Ice Beam | 3 | 40 | Bubble Beam | Starmie | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Hydro Pump | 4 | 47 | Bubble Beam | Starmie | Water, 120 power. 80% accurate. | Potent, Rippling, Wounding, Keen, Piercing, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Star Spin | Tackle → Water Gun | 25 / 30 | Starmie | 15% / 30% |
| Shining Core | Recover → Harden | 20 / 25 | Starmie | 50% / 100% |
| Static Tide | Bubble Beam → Thunder Wave | 28 / 33 | Starmie | 15% / 30% |

---

## The Abra line

Stages: Abra → Kadabra (Lv16) → Alakazam (by stone, not in the game yet). Whole tree: 121 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Confusion | – | free | – | Abra | Psychic, 50 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |
| Kinesis | – | free | – | Abra | 80% accurate. Lowers an enemy's accuracy 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Thunder Wave | 1 | 12 | Kinesis | Abra | Paralyzes an enemy. Doesn't affect Ground types. | Wide, Contagious, Shocking, Quick (6) |
| Reflect | 1 | 42 | Kinesis | Abra | Halves the damage an ally takes for 2 rounds. | Thick, Shared, Renewing, Quick (7) |
| Psybeam | 2 | 27 | Confusion | Kadabra | Psychic, 65 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |
| Body Slam | 3 | 25 | Confusion | Kadabra | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Recover | 1 | 31 | Reflect | Kadabra | Heals the user 1/2 of its max HP. | Cleansing, Renewing, Quick (5) |
| Psychic | 3 | 38 | Psybeam | Kadabra | Psychic, 90 power. 33% chance to lower its Defense. | Potent, Bewildering, Wounding, Keen, Rippling, Swift (13) |
| Hyper Beam | 4 | 50 | Psychic | Alakazam | Normal, 150 power. 90% accurate. The user must rest the next round. | Potent, Staggering, Wounding, Keen, Piercing, Tireless, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Mind Lock | Confusion → Kinesis | 20 / 25 | Kadabra | 20% / 40% |
| Static Mind | Psybeam → Thunder Wave | 25 / 30 | Kadabra | 15% / 30% |
| Mending Wall | Recover → Reflect | 30 / 35 | Kadabra | 50% / 100% |

---

## The Venonat line

Stages: Venonat → Venomoth (Lv31, not in the game yet). Whole tree: 131 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Venonat | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Supersonic | 1 | 24 | Tackle | Venonat | 55% chance to confuse. | Sure, Wide, Contagious, Maddening, Quick (9) |
| Leech Life | 1 | 35 | Tackle | Venonat | Bug, 20 power. Heals the user 1/2 of the damage dealt. | Potent, Venomous, Twin (7) |
| Confusion | 2 | 27 | Tackle | Venonat | Psychic, 50 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |
| Poison Powder | 1 | 30 | Supersonic | Venonat | Poisons an enemy (75% chance). | Sure, Wide, Contagious, Toxic, Siphoning, Quick (10) |
| Stun Spore | 1 | 38 | Poison Powder | Venonat | Paralyzes an enemy (75% chance). | Sure, Wide, Contagious, Shocking, Quick (9) |
| Psybeam | 2 | 43 | Confusion | Venonat | Psychic, 65 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |
| Sleep Powder | 1 | 46 | Stun Spore | Venonat | Puts an enemy to sleep (75% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Double-Edge | 4 | 36 | Leech Life | Venomoth | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |
| Psychic | 3 | 51 | Psybeam | Venomoth | Psychic, 90 power. 33% chance to lower its Defense. | Potent, Bewildering, Wounding, Keen, Rippling, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Dizzy Spores | Supersonic → Poison Powder | 20 / 25 | Venomoth | 15% / 30% |
| Mind Drain | Leech Life → Confusion | 25 / 30 | Venomoth | 15% / 30% |

---

## The Bellsprout line

Stages: Bellsprout → Weepinbell (Lv21, not in the game yet) → Victreebel (by stone, not in the game yet). Whole tree: 116 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Vine Whip | – | free | – | Bellsprout | Grass, 35 power. | Potent, Draining, Lashing, Twin (9) |
| Growth | – | free | – | Bellsprout | Raises its Attack 1 stage. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Wrap | 1 | 13 | Vine Whip | Bellsprout | Normal, 15 power. 85% accurate. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Staggering, Twin (7) |
| Poison Powder | 1 | 15 | Growth | Bellsprout | Poisons an enemy (75% chance). | Sure, Wide, Contagious, Toxic, Siphoning, Quick (10) |
| Sleep Powder | 1 | 18 | Poison Powder | Bellsprout | Puts an enemy to sleep (75% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Stun Spore | 1 | 21 | Poison Powder | Bellsprout | Paralyzes an enemy (75% chance). | Sure, Wide, Contagious, Shocking, Quick (9) |
| Acid | 1 | 26 | Wrap | Bellsprout | Poison, 40 power. 33% chance to lower its Defense. | Potent, Venomous, Splashing, Twin (9) |
| Swords Dance | 1 | 30 | Growth | Weepinbell | Raises its Attack 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Razor Leaf | 2 | 33 | Vine Whip | Bellsprout | Grass, 55 power. 95% accurate. High critical-hit ratio. | Potent, Draining, Wounding, Scattering, Twin (11) |
| Slam | 3 | 42 | Wrap | Weepinbell | Normal, 80 power. 75% accurate. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Snaring Vines | Vine Whip → Wrap | 25 / 30 | Weepinbell | 15% / 30% |
| Corroding Grip | Wrap → Acid | 28 / 33 | Weepinbell | 20% / 40% |

---

## The Pikachu line

Stages: Pikachu. Whole tree: 100 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Thunder Shock | – | free | – | Pikachu | Electric, 40 power. 10% chance to paralyze. | Potent, Crackling, Arcing, Twin (9) |
| Growl | – | free | – | Pikachu | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Thunder Wave | 1 | 9 | Growl | Pikachu | Paralyzes an enemy. Doesn't affect Ground types. | Wide, Contagious, Shocking, Quick (6) |
| Quick Attack | 1 | 16 | Thunder Shock | Pikachu | Normal, 40 power. Always goes first. | Potent, Staggering, Twin (7) |
| Swift | 2 | 26 | Quick Attack | Pikachu | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Starfall, Twin (13) |
| Thunderbolt | 3 | 30 | Thunder Shock | Pikachu | Electric, 95 power. 10% chance to paralyze. | Potent, Crackling, Wounding, Keen, Arcing, Swift (13) |
| Agility | 1 | 33 | Thunder Wave | Pikachu | Raises its Speed 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Thunder | 4 | 43 | Thunderbolt | Pikachu | Electric, 120 power. 70% accurate. 10% chance to paralyze. | Potent, Crackling, Wounding, Keen, Arcing, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Static Charge | Quick Attack → Thunder Wave | 30 / 35 | Pikachu | 15% / 30% |
| Overcharge | Agility → Thunder Shock | 35 / 40 | Pikachu | 50% / 100% |

---

## The Seel line

Stages: Seel → Dewgong (Lv34). Whole tree: 143 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Headbutt | – | free | – | Seel | Normal, 70 power. 30% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Water Gun | 1 | 10 | Headbutt | Seel | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Bubble Beam | 2 | 25 | Water Gun | Seel | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Foaming, Twin (13) |
| Growl | 1 | 30 | Headbutt | Seel | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Aurora Beam | 2 | 35 | Headbutt | Seel | Ice, 65 power. 10% chance to lower its Attack. | Potent, Chilling, Wounding, Keen, Frost, Twin (13) |
| Rest | 1 | 40 | Growl | Seel | The user heals fully, is cured, and sleeps for 2 rounds. | Light Sleep, Renewing, Quick (5) |
| Surf | 3 | 40 | Bubble Beam | Dewgong | Water, 95 power. | Potent, Rippling, Wounding, Keen, Tidal, Swift (13) |
| Take Down | 3 | 45 | Headbutt | Dewgong | Normal, 90 power. 85% accurate. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |
| Ice Beam | 3 | 50 | Aurora Beam | Dewgong | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Blizzard | 4 | 55 | Ice Beam | Dewgong | Ice, 120 power. 90% accurate. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Whiteout, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Bellow | Headbutt → Growl | 32 / 37 | Dewgong | 20% / 40% |
| Polar Spray | Water Gun → Aurora Beam | 37 / 42 | Dewgong | 10% / 20% |

---

## The Shellder line

Stages: Shellder. Whole tree: 111 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Shellder | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Withdraw | – | free | – | Shellder | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Water Gun | 1 | 10 | Tackle | Shellder | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Supersonic | 1 | 18 | Withdraw | Shellder | 55% chance to confuse. | Sure, Wide, Contagious, Maddening, Quick (9) |
| Clamp | 1 | 23 | Water Gun | Shellder | Water, 35 power. 75% accurate. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Rippling, Twin (7) |
| Bubble Beam | 2 | 25 | Water Gun | Shellder | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Foaming, Twin (13) |
| Aurora Beam | 2 | 30 | Clamp | Shellder | Ice, 65 power. 10% chance to lower its Attack. | Potent, Chilling, Wounding, Keen, Frost, Twin (13) |
| Leer | 1 | 39 | Supersonic | Shellder | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Ice Beam | 3 | 50 | Aurora Beam | Shellder | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Clam Shell | Withdraw → Clamp | 30 / 35 | Shellder | 25% / 50% |
| Icy Grip | Clamp → Aurora Beam | 32 / 37 | Shellder | 15% / 30% |

---

## The Psyduck line

Stages: Psyduck → Golduck (Lv33, not in the game yet). Whole tree: 109 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | – | free | – | Psyduck | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Water Gun | 1 | 8 | Scratch | Psyduck | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Bubble Beam | 2 | 20 | Water Gun | Psyduck | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Foaming, Twin (13) |
| Tail Whip | 1 | 28 | Scratch | Psyduck | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Confusion | 2 | 36 | Tail Whip | Psyduck | Psychic, 50 power. 10% chance to confuse. | Potent, Bewildering, Wounding, Keen, Rippling, Twin (13) |
| Fury Swipes | 1 | 43 | Scratch | Psyduck | Normal, 18 power, hits 2-5 times. 80% accurate. | Potent, Staggering, Sweeping, Relentless (9) |
| Ice Beam | 3 | 45 | Bubble Beam | Golduck | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Hydro Pump | 4 | 52 | Bubble Beam | Golduck | Water, 120 power. 80% accurate. | Potent, Rippling, Wounding, Keen, Piercing, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Headache | Water Gun → Confusion | 38 / 43 | Golduck | 10% / 20% |
| Flailing | Fury Swipes → Tail Whip | 45 / 50 | Golduck | 20% / 40% |

---

## The Horsea line

Stages: Horsea → Seadra (Lv32, not in the game yet). Whole tree: 107 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Bubble | – | free | – | Horsea | Water, 30 power. 33% chance to lower its Speed. | Potent, Rippling, Foaming, Twin (9) |
| Smokescreen | 1 | 19 | Bubble | Horsea | Lowers an enemy's accuracy 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Bubble Beam | 2 | 20 | Bubble | Horsea | Water, 65 power. 33% chance to lower its Speed. | Potent, Rippling, Wounding, Keen, Foaming, Twin (13) |
| Leer | 1 | 24 | Smokescreen | Horsea | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Water Gun | 1 | 30 | Bubble | Horsea | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Agility | 1 | 37 | Leer | Horsea | Raises its Speed 2 stages. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Ice Beam | 3 | 40 | Bubble Beam | Seadra | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Hydro Pump | 4 | 45 | Water Gun | Seadra | Water, 120 power. 80% accurate. | Potent, Rippling, Wounding, Keen, Piercing, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Ink Jet | Water Gun → Smokescreen | 32 / 37 | Seadra | 20% / 40% |
| Riptide | Agility → Bubble Beam | 39 / 44 | Seadra | 25% / 50% |

---

## The Jynx line

Stages: Jynx. Whole tree: 124 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Pound | – | free | – | Jynx | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Lovely Kiss | – | free | – | Jynx | Puts an enemy to sleep (75% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Lick | 1 | 18 | Pound | Jynx | Ghost, 20 power. 30% chance to paralyze. | Potent, Haunting, Twin (7) |
| Double Slap | 1 | 23 | Pound | Jynx | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Ice Punch | 3 | 31 | Lick | Jynx | Ice, 75 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Twin (13) |
| Psychic | 3 | 35 | Lovely Kiss | Jynx | Psychic, 90 power. 33% chance to lower its Defense. | Potent, Bewildering, Wounding, Keen, Rippling, Swift (13) |
| Body Slam | 3 | 39 | Double Slap | Jynx | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Thrash | 3 | 47 | Body Slam | Jynx | Normal, 90 power. The user becomes confused afterwards. | Potent, Staggering, Wounding, Keen, Rampaging, Calm, Swift (14) |
| Blizzard | 4 | 58 | Ice Punch | Jynx | Ice, 120 power. 90% accurate. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Whiteout, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Blown Kiss | Double Slap → Lovely Kiss | 30 / 35 | Jynx | 10% / 20% |
| Mind Freeze | Psychic → Ice Punch | 37 / 42 | Jynx | 15% / 30% |

---

## The Lapras line

Stages: Lapras. Whole tree: 112 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Water Gun | – | free | – | Lapras | Water, 40 power. | Potent, Rippling, Piercing, Twin (9) |
| Growl | – | free | – | Lapras | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Sing | 1 | 16 | Growl | Lapras | Puts an enemy to sleep (55% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Body Slam | 3 | 25 | Water Gun | Lapras | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Confuse Ray | 1 | 31 | Sing | Lapras | Confuses an enemy. | Wide, Contagious, Maddening, Quick (6) |
| Ice Beam | 3 | 38 | Water Gun | Lapras | Ice, 95 power. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Frost, Swift (13) |
| Hydro Pump | 4 | 46 | Ice Beam | Lapras | Water, 120 power. 80% accurate. | Potent, Rippling, Wounding, Keen, Piercing, Swift (13) |
| Blizzard | 4 | 50 | Ice Beam | Lapras | Ice, 120 power. 90% accurate. 10% chance to freeze. | Potent, Chilling, Wounding, Keen, Whiteout, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Lullaby | Water Gun → Sing | 30 / 35 | Lapras | 10% / 20% |
| Haunting Song | Sing → Confuse Ray | 33 / 38 | Lapras | 25% / 50% |

---

## The Geodude line

Stages: Geodude → Graveler (Lv25, not in the game yet) → Golem (by stone, not in the game yet). Whole tree: 121 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Geodude | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Defense Curl | 1 | 11 | Tackle | Geodude | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Rock Throw | 2 | 16 | Tackle | Geodude | Rock, 50 power. 65% accurate. | Potent, Staggering, Wounding, Keen, Shrapnel, Twin (13) |
| Harden | 1 | 26 | Defense Curl | Geodude | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Rock Slide | 3 | 25 | Rock Throw | Graveler | Rock, 75 power. 90% accurate. | Potent, Staggering, Wounding, Keen, Landslide, Twin (13) |
| Earthquake | 4 | 35 | Rock Throw | Golem | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Shockwave, Swift (13) |
| Body Slam | 3 | 30 | Tackle | Graveler | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Dig | 4 | 35 | Earthquake | Golem | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Cave-in, Instant, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Rolling Stone | Tackle → Rock Throw | 25 / 30 | Graveler | 15% / 30% |
| Avalanche | Rock Slide → Earthquake | 28 / 33 | Graveler | 10% / 20% |

---

## The Onix line

Stages: Onix. Whole tree: 109 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Tackle | – | free | – | Onix | Normal, 35 power. 95% accurate. | Potent, Staggering, Twin (7) |
| Screech | – | free | – | Onix | 85% accurate. Lowers an enemy's Defense 2 stages. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Bind | 1 | 15 | Tackle | Onix | Normal, 15 power. 75% accurate. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Staggering, Twin (7) |
| Rock Throw | 2 | 19 | Tackle | Onix | Rock, 50 power. 65% accurate. | Potent, Staggering, Wounding, Keen, Shrapnel, Twin (13) |
| Rock Slide | 3 | 28 | Rock Throw | Onix | Rock, 75 power. 90% accurate. | Potent, Staggering, Wounding, Keen, Landslide, Twin (13) |
| Slam | 3 | 33 | Bind | Onix | Normal, 80 power. 75% accurate. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Earthquake | 4 | 38 | Rock Throw | Onix | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Shockwave, Swift (13) |
| Harden | 1 | 43 | Screech | Onix | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Crushing Coils | Bind → Screech | 25 / 30 | Onix | 25% / 50% |
| Rumbling Rocks | Rock Slide → Screech | 30 / 35 | Onix | 15% / 30% |

---

## The Diglett line

Stages: Diglett → Dugtrio (Lv26, not in the game yet). Whole tree: 101 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | – | free | – | Diglett | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Growl | 1 | 15 | Scratch | Diglett | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Dig | 4 | 35 | Scratch | Dugtrio | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Cave-in, Instant, Swift (14) |
| Sand-Attack | 1 | 24 | Growl | Diglett | Lowers an enemy's accuracy 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Slash | 2 | 31 | Scratch | Diglett | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (11) |
| Rock Slide | 3 | 35 | Dig | Dugtrio | Rock, 75 power. 90% accurate. | Potent, Staggering, Wounding, Keen, Landslide, Twin (13) |
| Earthquake | 4 | 40 | Dig | Dugtrio | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Shockwave, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Dust Cloud | Dig → Sand-Attack | 21 / 26 | Dugtrio | 20% / 40% |
| Tunneling Claws | Scratch → Dig | 26 / 31 | Dugtrio | 5% / 10% |

---

## The Sandshrew line

Stages: Sandshrew → Sandslash (Lv22, not in the game yet). Whole tree: 125 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | – | free | – | Sandshrew | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Sand-Attack | 1 | 10 | Scratch | Sandshrew | Lowers an enemy's accuracy 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Slash | 2 | 17 | Scratch | Sandshrew | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (11) |
| Poison Sting | 1 | 24 | Scratch | Sandshrew | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Venom Cloud, Twin (9) |
| Dig | 4 | 35 | Sand-Attack | Sandslash | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Cave-in, Instant, Swift (14) |
| Swift | 2 | 31 | Slash | Sandshrew | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Starfall, Twin (13) |
| Fury Swipes | 1 | 38 | Slash | Sandshrew | Normal, 18 power, hits 2-5 times. 80% accurate. | Potent, Staggering, Sweeping, Relentless (9) |
| Rock Slide | 3 | 40 | Dig | Sandslash | Rock, 75 power. 90% accurate. | Potent, Staggering, Wounding, Keen, Landslide, Twin (13) |
| Earthquake | 4 | 45 | Dig | Sandslash | Ground, 100 power. | Potent, Dusting, Wounding, Keen, Shockwave, Swift (13) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Sandstorm | Slash → Sand-Attack | 20 / 25 | Sandslash | 20% / 40% |
| Barbed Claws | Fury Swipes → Poison Sting | 40 / 45 | Sandslash | 15% / 30% |

---

## The Ekans line

Stages: Ekans → Arbok (Lv22, not in the game yet). Whole tree: 97 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Wrap | – | free | – | Ekans | Normal, 15 power. 85% accurate. Binds it for 2-5 rounds: 1/16 of its max HP each round. | Potent, Staggering, Twin (7) |
| Leer | – | free | – | Ekans | Lowers an enemy's Defense 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Poison Sting | 1 | 10 | Wrap | Ekans | Poison, 15 power. 30% chance to poison. | Potent, Venomous, Venom Cloud, Twin (9) |
| Bite | 2 | 17 | Wrap | Ekans | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Glare | 1 | 24 | Leer | Ekans | Paralyzes an enemy (75% chance). | Sure, Wide, Contagious, Shocking, Quick (9) |
| Screech | 1 | 31 | Glare | Ekans | 85% accurate. Lowers an enemy's Defense 2 stages. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Dig | 4 | 35 | Bite | Arbok | Ground, 100 power. Charges for a round first. | Potent, Dusting, Wounding, Keen, Cave-in, Instant, Swift (14) |
| Acid | 1 | 38 | Poison Sting | Ekans | Poison, 40 power. 33% chance to lower its Defense. | Potent, Venomous, Splashing, Twin (9) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Venom Coils | Wrap → Poison Sting | 25 / 30 | Arbok | 15% / 30% |
| Paralyzing Gaze | Bite → Glare | 26 / 31 | Arbok | 15% / 30% |

---

## The Jigglypuff line

Stages: Jigglypuff. Whole tree: 87 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Pound | – | free | – | Jigglypuff | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Sing | – | free | – | Jigglypuff | Puts an enemy to sleep (55% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Defense Curl | 1 | 19 | Sing | Jigglypuff | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Double Slap | 1 | 24 | Pound | Jigglypuff | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Rest | 1 | 29 | Defense Curl | Jigglypuff | The user heals fully, is cured, and sleeps for 2 rounds. | Light Sleep, Renewing, Quick (5) |
| Body Slam | 3 | 34 | Double Slap | Jigglypuff | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Double-Edge | 4 | 39 | Body Slam | Jigglypuff | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Lullaby Slaps | Double Slap → Sing | 30 / 35 | Jigglypuff | 10% / 20% |
| Heavy Sleeper | Body Slam → Sing | 36 / 41 | Jigglypuff | 10% / 20% |

---

## The Zubat line

Stages: Zubat → Golbat (Lv22, not in the game yet). Whole tree: 89 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Leech Life | – | free | – | Zubat | Bug, 20 power. Heals the user 1/2 of the damage dealt. | Potent, Venomous, Twin (7) |
| Supersonic | 1 | 10 | Leech Life | Zubat | 55% chance to confuse. | Sure, Wide, Contagious, Maddening, Quick (9) |
| Bite | 2 | 15 | Leech Life | Zubat | Normal, 60 power. 10% chance to make it flinch. | Potent, Staggering, Wounding, Keen, Twin (11) |
| Confuse Ray | 1 | 21 | Supersonic | Zubat | Confuses an enemy. | Wide, Contagious, Maddening, Quick (6) |
| Wing Attack | 1 | 28 | Bite | Zubat | Flying, 35 power. | Potent, Staggering, Gale, Twin (9) |
| Swift | 2 | 32 | Wing Attack | Zubat | Normal, 60 power. Ignores accuracy drops. | Potent, Staggering, Wounding, Keen, Starfall, Twin (13) |
| Double-Edge | 4 | 38 | Wing Attack | Golbat | Normal, 100 power. The user takes 1/4 of the damage dealt. | Potent, Staggering, Wounding, Keen, Bowling, Cushioned, Swift (15) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Dizzying Bite | Bite → Supersonic | 25 / 30 | Golbat | 15% / 30% |
| Draining Swoop | Wing Attack → Leech Life | 30 / 35 | Golbat | 15% / 30% |

---

## The Paras line

Stages: Paras → Parasect (Lv24, not in the game yet). Whole tree: 91 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Scratch | – | free | – | Paras | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Stun Spore | 1 | 13 | Scratch | Paras | Paralyzes an enemy (75% chance). | Sure, Wide, Contagious, Shocking, Quick (9) |
| Leech Life | 1 | 20 | Scratch | Paras | Bug, 20 power. Heals the user 1/2 of the damage dealt. | Potent, Venomous, Twin (7) |
| Mega Drain | 1 | 24 | Leech Life | Paras | Grass, 40 power. Heals the user 1/2 of the damage dealt. | Potent, Draining, Twin (7) |
| Spore | 1 | 27 | Stun Spore | Paras | Puts an enemy to sleep. | Wide, Contagious, Deep, Nightmare, Quick (8) |
| Slash | 2 | 34 | Scratch | Paras | Normal, 70 power. High critical-hit ratio. | Potent, Staggering, Wounding, Sweeping, Twin (11) |
| Growth | 1 | 41 | Spore | Paras | Raises its Attack 1 stage. | Greater, Empowering, Renewing, Rallying, Quick (9) |
| Solar Beam | 4 | 44 | Mega Drain | Parasect | Grass, 120 power. Charges for a round first. | Potent, Draining, Wounding, Keen, Piercing, Instant, Swift (14) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Spore Claws | Scratch → Stun Spore | 25 / 30 | Parasect | 10% / 20% |
| Fungal Feast | Leech Life → Spore | 29 / 34 | Parasect | 10% / 20% |

---

## The Clefairy line

Stages: Clefairy → Clefable (by stone, not in the game yet). Whole tree: 102 points.

| Move | Cost | Lv | Opened by | Stage | Effect | Buffs (points) |
| --- | --- | --- | --- | --- | --- | --- |
| Pound | – | free | – | Clefairy | Normal, 40 power. | Potent, Staggering, Twin (7) |
| Growl | – | free | – | Clefairy | Lowers an enemy's Attack 1 stage. | Deep, Follow-up, Wide, Exposing, Emboldening, Quick (10) |
| Sing | 1 | 13 | Growl | Clefairy | Puts an enemy to sleep (55% chance). | Sure, Wide, Contagious, Deep, Nightmare, Quick (11) |
| Double Slap | 1 | 18 | Pound | Clefairy | Normal, 15 power, hits 2-5 times. 85% accurate. | Potent, Staggering, Relentless (7) |
| Defense Curl | 1 | 39 | Growl | Clefairy | Raises its Defense 1 stage. | Greater, Empowering, Renewing, Spiked, Rallying, Quick (11) |
| Body Slam | 3 | 30 | Double Slap | Clefable | Normal, 85 power. 30% chance to paralyze. | Potent, Staggering, Wounding, Keen, Bowling, Twin (13) |
| Thunder Wave | 1 | 34 | Sing | Clefairy | Paralyzes an enemy. Doesn't affect Ground types. | Wide, Contagious, Shocking, Quick (6) |
| Psychic | 3 | 40 | Thunder Wave | Clefable | Psychic, 90 power. 33% chance to lower its Defense. | Potent, Bewildering, Wounding, Keen, Rippling, Swift (13) |
| Rest | 1 | 44 | Defense Curl | Clefairy | The user heals fully, is cured, and sleeps for 2 rounds. | Light Sleep, Renewing, Quick (5) |

Links cost 2 points a rank.

| Link | Sets off | Lv per rank | Stage | Chance per rank |
| --- | --- | --- | --- | --- |
| Moonlit Song | Double Slap → Sing | 25 / 30 | Clefable | 10% / 20% |
| Static Slam | Body Slam → Thunder Wave | 36 / 41 | Clefable | 15% / 30% |

<!-- trees:end -->
