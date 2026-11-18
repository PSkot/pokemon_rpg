# Talents

How Pokémon get their moves and make them their own. Keep this file in
step with the code (`game/mechanics/talents.py`; battle effects in
`game/scenes/battle.py`). The tables at the end are generated from the
code: after changing a line's moves or talents, run
`python tools/talent_docs.py`.

Talents replaced the skill trees (skill points, ~100 buffs and links per
line): instead of spending points, the player makes about 12 choices per
Pokémon, each one written by hand.

## Moves

- **Moves come by level.** Each line has its Red/Blue level-up moves (and
  some TMs) at set levels and evolution stages (`talents.LEARNSETS`):
  strong moves and TMs open later and need an evolution (Bulbasaur's
  Solar Beam: Lv48, as Venusaur). A Pokémon knows every move its level
  and stage allow (`Monster.known`); a battle or quest level-up shows
  "learned …".
- The **first** move is the **basic attack** (Fight). Up to **4 more**
  are equipped (`Monster.equipped`, keys 2–5 in battle). A newly learned
  move is equipped while there's room; the talent screen's moves list (M)
  equips and unequips them, with every slot full asking which one a move
  replaces; O orders them.
- Lines without talents yet still get their moves by level.

## Talents

- **Paths.** Each line has 3 paths, each a way to play it (Bulbasaur:
  **Toxin**, **Bloom**, **Bulwark**; Pidgey: **Gale**, **Raptor**,
  **Scout**; see *Lines*). Lines with talents so far: the three starters
  (Bulbasaur, Charmander, Squirtle), and the early routes' Pidgey,
  Rattata, Spearow, Nidoran ♀ and ♂, Caterpie, Weedle and Pikachu.
- **Tiers.** 12 tiers open at **Lv6, 10, 14, 18, 22, 27, 32, 38, 44, 50,
  60, 75** (`TIER_LEVELS`). At each tier the player picks **1 of its 3
  talents**, one per path. Paths can be mixed freely. Tier 11's talents
  also need **4** earlier picks in their own path, tier 12's **6**
  (`DEEP`).
- **No ranks, no plain stat bonuses:** every talent changes how something
  plays.
- **Changing picks:** a tier's first pick can be made anywhere; changing
  a pick, or taking them all back (R), only in towns. Changing one can
  take back later picks that no longer have their earlier picks.
- **Shared talents** (`TALENTS`, `Talent.pool`): a talent is written once
  and placed in any line's tiers that fit it:
  - **type or status pools**: for lines of that type, or with moves that
    inflict that status (Grass: Overgrow, Harvest, ...; Poison: Sapping,
    Contagion, Poison Point, ...; Normal: Cornered, Momentum; Flying:
    Riding the Wind, Aerial Ace; Bug: Swarm, Shed Skin; Electric: Static,
    Charge Up; Fire: Blaze, Searing, Scorch, Smoulder, Ash Cloud, Wildfire,
    Heat Haze; Water: Torrent, Undertow, Splash Zone, Hydration; Ice:
    Frostbite, Chill; sleep: Nightmare; paralysis: Conductor; freezing:
    Shatter; confusion: Mind Games). A type's "low HP", "in a row" and "knockout heals" talents
    share one mechanism (Overgrow / Cornered / Swarm / Surge; Ripening /
    Momentum / Hive Mind / Charge Up; Harvest / Scavenger / Bird of Prey /
    Feeding Frenzy / Discharge); the rest of each pool is the type's own;
  - **move pools**: for lines that learn that move (Growl: Taunting Growl,
    Echoing Growl; Quick Attack: Lightning Reflexes, Hit and Run,
    Lightning Speed; Leech Seed: Creeping Seed, Seed Bomb, ...);
  - **any**: any line can have them (Sturdy, Second Wind, Guardian, Head
    Start, Lucky Strikes, Tenacity, Unbreakable, Ambush, Gang Up, Blur,
    Apex Predator);
  - **own**: one line's signature talents, mostly its capstones.

  A line places shared talents at the tiers that suit its moves, so the
  same talent can be at different tiers in different lines.
- **Wild and trainers' Pokémon** pick their own (`Monster.create`): a
  talent in every open tier, three in four along one path chosen at
  random.
- **Old saves** (from the skill trees): every member keeps the equipped
  moves it still knows and has no talents picked (`saves.TALENTS_VERSION`).

### How talents work

A talent changes moves and/or works in battle by itself:

- **Move changes** (`Talent.moves`): Move field changes for a selector,
  applied in tier order (`talents.apply_changes`: numbers add up, chances
  to at most 100%; `power`, `type`, `hits` are set): `"basic"` (the basic
  attack), a move's name, `"type:grass"` (the user's damaging moves of
  that type), `"status:poison"` (its moves that inflict it), `"confuse"`,
  `"damaging"`, `"status_moves"`, `"spread"` (moves that hit every target
  by then). So Sprout Strike's Grass Tackle also gets Flower Power, and
  Toxic Touch's poison also gets Contagion and Siphon. Changed moves show
  a "*" on the talent screen.
- **Battle effects** (`Talent.flags`, `Monster.talent(flag)`; the list is
  in `talents.py` above `TALENTS`). Talents with the same effect don't add
  up: the strongest counts, so a later one is an upgrade (Fortress after
  Shell Formation, Unbreakable after Tenacity, Rampage after Momentum,
  Murder of Crows after Gang Up):
  - damage (`BattleScene._talent_factor`, multiplying the hit): the
    user's **pinch:<type>** (×1.5 for that type's moves below ⅓ HP:
    Overgrow, Cornered, Swarm, Surge, Eye of the Storm), **streak:<type>**
    (+20% per move of that type used in a row before it, up to 3: Ripening,
    Hive Mind, Charge Up; Momentum +15%, Rampage +25%; any other move
    starts it over), **ambush** (+30% on a target that hasn't moved yet
    this round), **gang** (+30% on a target a partner already hit this
    round; Murder of Crows +50%), **wide** (Gale Force: +25% for moves
    that hit every enemy), **prey:<status>** (+% on a poisoned/paralyzed/
    confused target: Queen's Venom, Venom Queen, Supercharged, Mind Crush);
    its side's **spot:<stat>** (+30% on an enemy with that stat lowered:
    Blind Spot, Spiteful); **Sapping** (a poisoned attacker deals 20% less
    to the holder's side), **Ancient Roots** and its copies (the holder's
    side takes 15% less while it stands), **Sturdy** (the holder's first
    hit taken each battle: half; Juggernaut, Iron Turtle: none); **Pyre**
    (burned foes of its side lose a further 1/8 of max HP each round);
  - like gear mods (`Monster.gear_bonus`): `first` (Head Start: 30% to
    act first), `crit` (Lucky Strikes: +10 points), `endure` (Tenacity
    25%, Unbreakable 50%), `regen` (Photosynthesis, Preening, Nesting:
    1/16 a round), `status:<status>` (Plague Rat, Venom Lord: every hit's
    chance to inflict it);
  - **Second Wind** (and Cheek Pouch; Metamorphosis heals ½): once a
    battle, ending a round below ⅓ HP heals ¼ of max HP. **harvest:<type>**:
    knocking an enemy out with a move of that type heals ¼. **Nurturing**:
    the holder's side heals 1/16 a round. **Dream Eater**: 1/8 a round per
    sleeping foe. **Shed Skin**: 30% each round end to shake off its
    status;
  - **Guardian** / **World Tree** / **Hive Queen**: once a battle, a
    partner hit for the last of its HP keeps 1 HP (Queen's Guard: and
    heals ¼);
  - when hit: **retaliate:<status>** (Static, Poison Point: 25% that the
    attacker gets the status), **thorns** (Thorny Hide: the attacker loses
    1/16 of its max HP, as Thornskin's spikes do);
  - at the start of each battle: **aura:<status>** (Miasma: 50% per foe to
    be poisoned; Thunder Cloud: 30% paralyzed; Heat Haze: 30% burned;
    Absolute Zero: 20% frozen), **intimidate** (every foe's Attack −1
    stage).
- **Move fields** they use (`moves.Move`): `taunt` (Taunting Growl, Decoy,
  Mob Rule, Lightning Rod: for this round and the next, the foes'
  single-target moves go to the user), `keen` (Keen Edge, Apex Predator:
  always a critical hit on a target below that share of its HP),
  `charge_skip` (Sunlit, Ascend: no charging once that move was used in
  the battle), `ko_no_recharge` (Overdrive), `soothe` (Soothing Spores),
  and the older `follow_up`, `expose`, `empower`, `rally`, `spikes`,
  `reach`, `shield`, `heal`, `self_stages`, `priority`, `triggers`, ...
  A damaging move with `seed` (Seed Bomb) seeds what it hits; poison from
  a damaging move carries its Contagion/Siphon.

## The talent screen

Party screen → **S** (`game/scenes/talent_screen.py`). Left: the grid, a
row per tier (its level at the left) and a column per path (with how many
are picked in it). Picked talents are filled in their path's colour and
joined by a line; talents that can be picked now are outlined green;
locked ones are grey. The grid scrolls to keep the cursor in view. Right:
the chosen talent (its path and tier, where it comes from, what it does,
what it needs or "Enter: pick"), then the moves it knows (F = the basic
attack, 2–5 = equipped, * = changed by a talent) and the next two to
come, with their levels.

Keys: **arrows** move, **Enter** picks, **M** the moves list (equip or
unequip: E / Enter), **O** reorders the equipped moves, **R** takes every
talent back (in towns, after asking), **Q/W** switch Pokémon, **S** / X
back. Touch: tap a talent to choose it and again to pick it; pills Moves,
Reorder moves, Reset, Next.

## Lines

<!-- generated -->

### Bulbasaur → Ivysaur → Venusaur

Moves: Tackle, Growl, Leech Seed 7, Vine Whip 13, Poison Powder 20, Leaf Shield 22 (Ivysaur), Take Down 25 (Ivysaur), Razor Leaf 27, Body Slam 30 (Ivysaur), Growth 34, Sleep Powder 41 (Ivysaur), Solar Beam 48 (Venusaur), Double-Edge 50 (Venusaur), Hyper Beam 55 (Venusaur).

Paths: **Toxin** (poison, seeds and sleep: wearing enemies down); **Bloom** (grass damage); **Bulwark** (staying up, and keeping the partner up).

| Tier | Lv | Toxin | Bloom | Bulwark |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Sprout Strike**: The basic attack becomes a Grass move (with STAB). *(Grass)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 2 | 10 | **Creeping Seed**: When a seeded enemy faints, its seed jumps to an enemy next to it. *(Leech Seed)* | **Seed Bomb**: Leech Seed also deals damage (Grass, 30 power) when it lands. *(Leech Seed)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 3 | 14 | **Thorned Whip**: Vine Whip has a 30% chance to poison. *(**own**)* | **Double Lash**: Vine Whip hits twice, at 60% power each. *(Vine Whip)* | **Thirsty Vines**: Vine Whip heals the user half the damage it deals. *(Vine Whip)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Ripening**: Each Grass move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Grass)* | **Canopy**: Leaf Shield covers the whole party. *(Leaf Shield)* |
| 6 | 27 | **Pollen Cloud**: Poison Powder hits every enemy. *(Poison Powder)* | **Keen Edge**: Razor Leaf is always a critical hit on a target below half HP. *(Razor Leaf)* | **Thornskin**: For 3 rounds, whoever hits a Pokémon behind Leaf Shield loses 1/16 of its max HP. *(Leaf Shield)* |
| 7 | 32 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Flower Power**: The user's Grass moves also hit one enemy next to the target, at half damage. *(Grass)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 8 | 38 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Full Bloom**: Growth also makes the user's next damaging move deal 50% more. *(Growth)* | **Shared Sun**: Growth works on the whole party. *(Growth)* |
| 9 | 44 | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Harvest**: Knocking an enemy out with a Grass move heals the user 1/4 of its max HP. *(Grass)* | **Soothing Spores**: Sleep Powder also cures the party's status conditions. *(Sleep Powder)* |
| 10 | 50 | **Spore Storm**: Razor Leaf has a 15% chance to set off Poison Powder and a 10% chance to set off Sleep Powder on its target. *(**own**)* | **Sunlit**: Once the user has used Growth in a battle, Solar Beam needs no charging. *(**own**)* | **Photosynthesis**: The user heals 1/16 of its max HP at the end of each round. *(Grass)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Solar Flare** *(needs 4)*: Solar Beam hits every enemy, at full power. *(Solar Beam)* | **World Tree** *(needs 4)*: Once a battle, a partner that would faint keeps 1 HP instead. *(**own**)* |
| 12 | 75 | **Venom Garden** *(needs 6)*: All poison the user inflicts is bad poison, and Leech Seed poisons too. *(**own**)* | **Hyper Bloom** *(needs 6)*: Hyper Beam is a Grass move and needs no rest after knocking an enemy out. *(**own**)* | **Ancient Roots** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Charmander → Charmeleon → Charizard

Moves: Scratch, Growl, Ember 9, Leer 15, Swords Dance 25 (Charmeleon), Slash 30, Flamethrower 38 (Charmeleon), Fire Spin 46, Fire Blast 50 (Charizard), Earthquake 55 (Charizard).

Paths: **Cinder** (burns, and making them hurt); **Claw** (scratch and Slash: critical hits and wounds); **Inferno** (fire damage, on every enemy).

| Tier | Lv | Cinder | Claw | Inferno |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Kindling**: Scratch has a 10% chance to burn. *(**own**)* | **Sharp Claws**: Scratch is 4× as likely to be a critical hit. *(Scratch)* | **Flame Claw**: Scratch becomes a Fire move (with STAB). *(**own**)* |
| 2 | 10 | **Searing**: The user's Fire moves are 20% more likely to burn. *(Fire)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Ember Shower**: Ember hits every enemy, the others at 50% damage. *(Ember)* |
| 3 | 14 | **Ash Cloud**: The user's Fire moves have a 20% chance to lower the target's accuracy 1 stage. *(Fire)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Blaze**: Below 1/3 HP, the user's Fire moves deal 1.5× damage. *(Fire)* |
| 4 | 18 | **Scorch**: Burned enemies take 25% more damage from the user. *(Fire)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* | **Stoke the Flames**: Each Fire move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Fire)* |
| 5 | 22 | **Smoulder**: The user's Fire moves wound the target: 1/16 of its max HP each round, for 3 rounds. *(Fire)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Fireball**: Ember hits harder: 60 power. *(Ember)* |
| 6 | 27 | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* | **Blade Dance**: Swords Dance also makes the user's next damaging move deal 50% more. *(Swords Dance)* | **Feed the Flames**: Knocking an enemy out with a Fire move heals the user 1/4 of its max HP. *(Fire)* |
| 7 | 32 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Scorching Breath**: Flamethrower is 20% more likely to burn. *(Flamethrower)* | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Blowtorch**: Flamethrower also hits one enemy next to the target, at half damage. *(Flamethrower)* |
| 9 | 44 | **Wildfire**: Burns the user inflicts have a 30% chance each round to spread to an enemy next to it. *(Fire)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 10 | 50 | **Vortex**: Fire Spin's flames hurt twice as much: 1/8 of max HP each round. *(Fire Spin)* | **Apex Predator**: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Firestorm**: Fire Spin hits every enemy. *(Fire Spin)* |
| 11 | 60 | **Heat Haze** *(needs 4)*: At the start of each battle, each enemy has a 30% chance to be burned. *(Fire)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Fault Line** *(needs 4)*: Earthquake hits every enemy, the others at 60% damage. *(Earthquake)* |
| 12 | 75 | **Pyre** *(needs 6)*: Enemies the user's side burned lose a further 1/8 of their max HP each round. *(**own**)* | **Dragon Claw** *(needs 6)*: Slash is always a critical hit. *(**own**)* | **Supernova** *(needs 6)*: Fire Blast hits every enemy at full damage, and burns 50% of the time. *(**own**)* |

### Squirtle → Wartortle → Blastoise

Moves: Tackle, Tail Whip, Bubble 8, Water Gun 15, Bite 22, Withdraw 28, Ice Beam 30 (Wartortle), Skull Bash 35 (Blastoise), Hydro Pump 42 (Blastoise), Blizzard 55 (Blastoise).

Paths: **Torrent** (water damage); **Shell** (withdraw and shells: taking the hits, and shielding the party); **Tide** (slowing, freezing and wearing enemies down).

| Tier | Lv | Torrent | Shell | Tide |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Splash Tackle**: Tackle becomes a Water move (with STAB). *(**own**)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 2 | 10 | **Bubble Burst**: Bubble hits every enemy, the others at 60% damage. *(Bubble)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Froth**: Bubble is twice as likely to lower Speed. *(Bubble)* |
| 3 | 14 | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* | **Rough Shell**: Whoever hits the user loses 1/16 of its max HP. *(**own**)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* |
| 4 | 18 | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* |
| 5 | 22 | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* |
| 6 | 27 | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* | **Riptide**: Enemies with lowered Speed take 30% more damage from the user's party. *(**own**)* |
| 7 | 32 | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* | **Shell Shield**: Withdraw also halves the damage the user takes for 2 rounds. *(Withdraw)* | **Frostbite**: The user's Ice moves are 10% more likely to freeze. *(Ice)* |
| 8 | 38 | **Headlong**: Once the user has used Withdraw in a battle, Skull Bash needs no charging. *(Skull Bash)* | **Turtle Wall**: Withdraw works on the whole party. *(Withdraw)* | **Frost Ray**: Ice Beam hits every enemy, the others at 50% damage. *(Ice Beam)* |
| 9 | 44 | **Geyser**: Hydro Pump hits every enemy, the others at 50% damage. *(Hydro Pump)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Shatter**: Frozen enemies take 50% more damage from the user. *(Freeze)* |
| 10 | 50 | **Hydro Cannon**: Hydro Pump never misses. *(Hydro Pump)* | **Shell Formation**: While the user stands, the whole party takes 15% less damage. *(**own**)* | **Chill**: The user's Ice moves have a 30% chance to lower the target's Speed 1 stage. *(Ice)* |
| 11 | 60 | **Tsunami** *(needs 4)*: Hydro Pump hits every enemy at full damage. *(**own**)* | **Iron Turtle** *(needs 4)*: The first hit the user takes in each battle deals no damage, and Withdraw heals the user 1/4 of its max HP. *(**own**)* | **Whiteout** *(needs 4)*: Blizzard never misses and hits every enemy, the others at 60% damage. *(Blizzard)* |
| 12 | 75 | **Tidal Force** *(needs 6)*: The user's Water moves are always critical hits on a target below half HP. *(**own**)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(**own**)* | **Absolute Zero** *(needs 6)*: At the start of each battle, each enemy has a 20% chance to be frozen. *(**own**)* |

### Spearow → Fearow

Moves: Peck, Growl, Leer 9, Fury Attack 15, Swift 20, Whirlwind 22, Drill Peck 29 (Fearow), Agility 36, Hyper Beam 45 (Fearow).

Paths: **Talon** (pecks and Drill Peck: hard Flying strikes); **Flock** (fury Attack and ganging up); **Bully** (growl and Leer: weakening and scaring the enemies).

| Tier | Lv | Talon | Flock | Bully |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Pecking Order**: Peck has a 30% chance to make the target flinch. *(**own**)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 2 | 10 | **Rapid Pecks**: Peck hits twice, at 60% power each. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 3 | 14 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 4 | 18 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Screech Growl**: Growl lowers Attack 2 stages. *(**own**)* |
| 5 | 22 | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* | **Harrier**: Fury Attack becomes a Flying move. *(**own**)* | **Mob Rule**: Leer also makes every enemy attack the user, this round and the next. *(**own**)* |
| 6 | 27 | **Aerial Ace**: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Drill Run**: Drill Peck also hits one enemy next to the target, at half damage. *(Drill Peck)* | **Howling Wind**: Whirlwind also deals damage (Normal, 30 power) to every enemy. *(Whirlwind)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 8 | 38 | **Fearsome Beak**: Drill Peck has a 30% chance to make the target flinch. *(**own**)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 9 | 44 | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* | **Tailwind**: Agility works on the whole party. *(Agility)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Tempest**: Whirlwind lowers Speed 2 stages. *(Whirlwind)* | **Intimidate**: At the start of each battle, every enemy's Attack falls 1 stage. *(**own**)* |
| 11 | 60 | **Sky Tyrant** *(needs 4)*: The user's Flying moves always go first, and its moves deal 50% more to a target that hasn't moved yet this round. *(**own**)* | **Murder of Crows** *(needs 4)*: The user's moves deal 50% more to a target a partner already hit this round. *(**own**)* | **Spiteful** *(needs 4)*: Enemies with lowered Attack take 30% more damage from the user's party. *(**own**)* |
| 12 | 75 | **Apex Predator** *(needs 6)*: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Storm of Beaks** *(needs 6)*: Fury Attack hits every enemy, at full damage. *(**own**)* | **Reign of Terror** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Nidoran F → Nidorina

Moves: Tackle, Growl, Scratch 8, Poison Sting 14, Tail Whip 21, Body Slam 25 (Nidorina), Bite 29, Fury Swipes 36, Double Kick 43.

Paths: **Venom** (poison, and making it worse); **Claw** (scratching, biting and kicking); **Matriarch** (keeping the partner safe).

| Tier | Lv | Venom | Claw | Matriarch |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 2 | 10 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 3 | 14 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Thorny Hide**: Whoever hits the user loses 1/16 of its max HP. *(**own**)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Venom Claws**: Scratch has a 30% chance to poison. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Echoing Growl**: Growl works on every enemy. *(Growl)* |
| 8 | 38 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Raking Claws**: Fury Swipes wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Fury Swipes)* | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(**own**)* |
| 9 | 44 | **Toxic Fangs**: Bite has a 30% chance to poison. *(**own**)* | **Rapid Kicks**: Each of Double Kick's hits has a 30% chance to make the target flinch. *(Double Kick)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Toxic Swipes**: Fury Swipes has a 20% chance per hit to poison. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Apex Predator** *(needs 4)*: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Den Mother** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |
| 12 | 75 | **Venom Queen** *(needs 6)*: All poison the user inflicts is bad poison, and poisoned enemies take 25% more damage from it. *(**own**)* | **Fury Queen** *(needs 6)*: Fury Swipes always hits 5 times. *(**own**)* | **Queen's Guard** *(needs 6)*: Once a battle, a partner that would faint keeps 1 HP, and the user heals it 1/4 of its max HP. *(**own**)* |

### Nidoran M → Nidorino

Moves: Tackle, Leer, Horn Attack 8, Poison Sting 14, Focus Energy 21, Body Slam 25 (Nidorino), Fury Attack 29, Double Kick 43.

Paths: **Venom** (poison, and making it worse); **Horn** (horn Attack: critical hits and piercing); **Brawler** (focus, charging and momentum).

| Tier | Lv | Venom | Horn | Brawler |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Charge**: Tackle hits harder: 50 power. *(**own**)* |
| 2 | 10 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Gore**: Horn Attack is 8× as likely to be a critical hit. *(Horn Attack)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 3 | 14 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Piercing Horn**: Horn Attack also hits one enemy next to the target, at half damage. *(**own**)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 5 | 22 | **Horn Drill**: Horn Attack has a 30% chance to poison. *(**own**)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 7 | 32 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Battle Focus**: Focus Energy also makes the user's next damaging move deal 50% more. *(**own**)* |
| 8 | 38 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Rampage**: Each Normal move in a row deals 25% more than the last, up to +75%. *(**own**)* |
| 9 | 44 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Rapid Kicks**: Each of Double Kick's hits has a 30% chance to make the target flinch. *(Double Kick)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 10 | 50 | **Toxic Horn**: Horn Attack is a Poison move, and poisons 30% of the time. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Apex Predator** *(needs 4)*: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Shared Focus** *(needs 4)*: Focus Energy works on the whole party. *(Focus Energy)* |
| 12 | 75 | **Venom Lord** *(needs 6)*: All poison the user inflicts is bad poison, and the user's hits have a 20% chance to poison. *(**own**)* | **Megahorn** *(needs 6)*: Horn Attack hits much harder: 100 power. *(**own**)* | **Juggernaut** *(needs 6)*: The first hit the user takes in each battle deals no damage, and its Normal moves never miss. *(**own**)* |

### Pidgey → Pidgeotto → Pidgeot

Moves: Gust, Sand-Attack 5, Quick Attack 12, Whirlwind 19, Wing Attack 28, Double-Edge 35 (Pidgeot), Agility 36, Sky Attack 44 (Pidgeot).

Paths: **Gale** (wind that hits every enemy); **Raptor** (fast, hard strikes on one target); **Scout** (sand in the eyes, decoys, and keeping the partner up).

| Tier | Lv | Gale | Raptor | Scout |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Squall**: Gust hits every enemy, the others at 50% damage. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Sandstorm**: Sand-Attack works on every enemy. *(Sand-Attack)* |
| 2 | 10 | **Buffeting Winds**: Gust has a 30% chance to lower the target's Speed 1 stage. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Blinding Grit**: Sand-Attack lowers accuracy 2 stages. *(Sand-Attack)* |
| 3 | 14 | **Cyclone**: Gust has a 10% chance to confuse. *(**own**)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* | **Kick Up Dust**: After Sand-Attack, the user hits the target with its basic attack at 60% power. *(Sand-Attack)* |
| 4 | 18 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Howling Wind**: Whirlwind also deals damage (Normal, 30 power) to every enemy. *(Whirlwind)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Dust Devil**: Sand-Attack also makes the target take 20% more damage from everyone, for 3 rounds. *(**own**)* |
| 6 | 27 | **Tempest**: Whirlwind lowers Speed 2 stages. *(Whirlwind)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 7 | 32 | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* | **Gale Wings**: Wing Attack always goes first. *(Wing Attack)* | **Decoy**: Sand-Attack also makes every enemy attack the user, this round and the next. *(**own**)* |
| 8 | 38 | **Downdraft**: Wing Attack hits every enemy, the others at 60% damage. *(**own**)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 9 | 44 | **Eye of the Storm**: Below 1/3 HP, the user's Normal and Flying moves deal 1.5× damage. *(**own**)* | **Ascend**: Once the user has used Agility in a battle, Sky Attack needs no charging. *(Sky Attack)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Gale Force**: The user's moves that hit every enemy deal 25% more. *(**own**)* | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* | **Preening**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* |
| 11 | 60 | **Wind Shear** *(needs 4)*: The user's moves that hit every enemy have a 20% chance to make each one flinch. *(**own**)* | **Aerial Ace** *(needs 4)*: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* | **Blind Spot** *(needs 4)*: Enemies with lowered accuracy take 30% more damage from the user's party. *(**own**)* |
| 12 | 75 | **Hurricane** *(needs 6)*: Gust becomes a Flying move with 60 power, and hits every enemy at full damage. *(**own**)* | **Apex Predator** *(needs 6)*: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Sheltering Wings** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Rattata → Raticate

Moves: Tackle, Tail Whip, Quick Attack 7, Focus Energy 23, Hyper Fang 25 (Raticate), Body Slam 25 (Raticate), Super Fang 35 (Raticate), Hyper Beam 45 (Raticate).

Paths: **Fang** (biting: wounds, flinches and fangs); **Scurry** (speed: Quick Attack, and striking first); **Survivor** (scrappy: fighting on when cornered).

| Tier | Lv | Fang | Scurry | Survivor |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Gnawing Tackle**: Tackle wounds the target: 1/16 of its max HP each round, for 3 rounds. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 2 | 10 | **Nip**: Tackle has a 20% chance to make the target flinch. *(**own**)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 3 | 14 | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Overtake**: Quick Attack is 4× as likely to be a critical hit. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 6 | 27 | **Bone Crusher**: Hyper Fang is 20% more likely to make the target flinch. *(Hyper Fang)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 7 | 32 | **Crushing Fang**: Hyper Fang has a 50% chance to lower the target's Defense 1 stage. *(**own**)* | **Shared Focus**: Focus Energy works on the whole party. *(Focus Energy)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 8 | 38 | **Gnaw**: Super Fang also wounds: 1/12 of the target's max HP each round, for 3 rounds. *(Super Fang)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Frenzied Bite**: Super Fang has a 50% chance to make the target flinch. *(**own**)* | **Sprinter**: Quick Attack hits twice, at 70% power each. *(**own**)* | **Nesting**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* |
| 10 | 50 | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Quick Claws**: Tackle always goes first. *(**own**)* | **Plague Rat**: The user's hits have a 15% chance to poison. *(**own**)* |
| 11 | 60 | **Apex Predator** *(needs 4)*: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Hyper Gnasher** *(needs 6)*: Hyper Beam wounds: 1/8 of the target's max HP each round, for 3 rounds; no rest after a knockout. *(**own**)* | **Lightning Speed** *(needs 6)*: Quick Attack hits 3 times, at 70% power each. *(Quick Attack)* | **Pack Leader** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Caterpie → Metapod → Butterfree

Moves: Tackle, String Shot, Harden 7 (Metapod), Confusion 12 (Butterfree), Poison Powder 15 (Butterfree), Stun Spore 16 (Butterfree), Sleep Powder 17 (Butterfree), Supersonic 21 (Butterfree), Mega Drain 25 (Butterfree), Whirlwind 26 (Butterfree), Psybeam 32 (Butterfree).

Paths: **Psychic** (confusion and Psybeam: muddled minds); **Powder** (string Shot and powders: status on every enemy); **Cocoon** (harden and shells: lasting, and shielding the partner).

| Tier | Lv | Psychic | Powder | Cocoon |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Web**: String Shot works on every enemy. *(String Shot)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 2 | 10 | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Sticky Silk**: String Shot also makes the target take 20% more damage from everyone, for 3 rounds. *(String Shot)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* |
| 3 | 14 | **Psychic Wings**: Confusion and Psybeam are 20% more likely to confuse. *(**own**)* | **Silk Strike**: After String Shot, the user hits the target with its basic attack at 60% power. *(**own**)* | **Cocoon**: Harden heals the user 1/4 of its max HP. *(**own**)* |
| 4 | 18 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Numbing Cloud**: Stun Spore works on every enemy. *(Stun Spore)* | **Shed Skin**: At the end of each round, the user has a 30% chance to shake off its status. *(Bug)* |
| 5 | 22 | **Echo**: Supersonic works on every enemy. *(Supersonic)* | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Shell Wall**: Harden works on the whole party. *(Harden)* |
| 6 | 27 | **Howling Wind**: Whirlwind also deals damage (Normal, 30 power) to every enemy. *(Whirlwind)* | **Drowsy Dust**: Sleep Powder works on every enemy. *(Sleep Powder)* | **Gluttony**: Mega Drain heals the user all the damage it deals (not half). *(Mega Drain)* |
| 7 | 32 | **Butterfly Dance**: The user's status moves also raise its Speed 1 stage. *(**own**)* | **Pollen Cloud**: Poison Powder hits every enemy. *(Poison Powder)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* | **Scale Dust**: Stun Spore, Poison Powder and Sleep Powder never miss and work 25% more often. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 10 | 50 | **Tempest**: Whirlwind lowers Speed 2 stages. *(Whirlwind)* | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Soothing Spores**: Sleep Powder also cures the party's status conditions. *(Sleep Powder)* |
| 11 | 60 | **Psychic Mastery** *(needs 4)*: Psybeam hits every enemy, the others at 60% damage. *(**own**)* | **Powder Storm** *(needs 4)*: Psybeam has a 20% chance to set off Stun Spore, Poison Powder or Sleep Powder. *(**own**)* | **Monarch** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |
| 12 | 75 | **Mind Crush** *(needs 6)*: Confused enemies take 30% more damage from the user. *(**own**)* | **Dream Eater** *(needs 6)*: The user heals 1/8 of its max HP each round for each sleeping enemy. *(**own**)* | **Metamorphosis** *(needs 6)*: Once a battle, ending a round below 1/3 HP heals the user half its max HP. *(**own**)* |

### Weedle → Kakuna → Beedrill

Moves: Poison Sting, String Shot, Harden 7 (Kakuna), Fury Attack 12 (Beedrill), Focus Energy 16 (Beedrill), Twineedle 20 (Beedrill), Swords Dance 25 (Beedrill), Pin Missile 30 (Beedrill), Agility 35 (Beedrill).

Paths: **Venom** (poison, and making it worse); **Swarm** (many quick stings); **Hive** (harden, silk and guarding the partner).

| Tier | Lv | Venom | Swarm | Hive |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Stinger**: Poison Sting hits harder: 30 power. *(**own**)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 2 | 10 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* |
| 3 | 14 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Web**: String Shot works on every enemy. *(String Shot)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* | **Shed Skin**: At the end of each round, the user has a 30% chance to shake off its status. *(Bug)* |
| 5 | 22 | **Envenom**: Twineedle is 30% more likely to poison. *(Twineedle)* | **Hive Mind**: Each Bug move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Bug)* | **Shell Wall**: Harden works on the whole party. *(Harden)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Blade Dance**: Swords Dance also makes the user's next damaging move deal 50% more. *(Swords Dance)* | **Sticky Silk**: String Shot also makes the target take 20% more damage from everyone, for 3 rounds. *(String Shot)* |
| 7 | 32 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Needle Storm**: Pin Missile always hits at least 3 times. *(Pin Missile)* | **Shared Focus**: Focus Energy works on the whole party. *(Focus Energy)* |
| 8 | 38 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Twin Stingers**: Twineedle hits 3 times. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 9 | 44 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 10 | 50 | **Killer Bee**: Pin Missile has a 20% chance per hit to poison. *(**own**)* | **Feeding Frenzy**: Knocking an enemy out with a Bug move heals the user 1/4 of its max HP. *(Bug)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Barrage** *(needs 4)*: Pin Missile always hits 5 times. *(**own**)* | **Hornet's Nest** *(needs 4)*: Whoever hits the user has a 25% chance to be poisoned, and takes 1/16 of its max HP. *(**own**)* |
| 12 | 75 | **Queen's Venom** *(needs 6)*: The user's moves deal 30% more to poisoned enemies. *(**own**)* | **Stinging Swarm** *(needs 6)*: Fury Attack and Pin Missile hit every enemy, the others at 50% damage. *(**own**)* | **Hive Queen** *(needs 6)*: Once a battle, a partner that would faint keeps 1 HP instead. *(**own**)* |

### Pikachu

Moves: Thunder Shock, Growl, Thunder Wave 9, Quick Attack 16, Swift 26, Thunderbolt 30, Agility 33, Thunder 43.

Paths: **Spark** (paralysis: slowing and stopping enemies); **Bolt** (raw Electric damage); **Agile** (quick Attack, speed and dodging trouble).

| Tier | Lv | Spark | Bolt | Agile |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Spark**: Thunder Shock is 20% more likely to paralyze. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Static**: Whoever hits the user has a 25% chance to be paralyzed. *(Electric)* | **Surge**: Below 1/3 HP, the user's Electric moves deal 1.5× damage. *(Electric)* | **Cheek Pouch**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(**own**)* |
| 3 | 14 | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals half damage. *(Any)* |
| 4 | 18 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Charge Up**: Each Electric move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Electric)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* |
| 5 | 22 | **Chain Lightning**: Thunder Wave works on every enemy. *(Thunder Wave)* | **Discharge**: Knocking an enemy out with a Electric move heals the user 1/4 of its max HP. *(Electric)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* |
| 6 | 27 | **Arc Flash**: Thunder Shock also hits one enemy next to the target, at half damage. *(**own**)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Volt Tackle**: Quick Attack becomes an Electric move with 60 power. *(**own**)* |
| 7 | 32 | **Lightning Rod**: Thunder Wave also makes every enemy attack the user, this round and the next. *(**own**)* | **High Voltage**: Thunderbolt is 4× as likely to be a critical hit. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 8 | 38 | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* | **Apex Predator**: The user's moves are always critical hits on a target below 1/3 HP. *(Any)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* |
| 9 | 44 | **Thunderstorm**: Thunder never misses, and paralyzes 30% of the time. *(**own**)* | **Overload**: Thunderbolt and Thunder hit every enemy, the others at 50% damage. *(**own**)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 10 | 50 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Thunderclap**: Thunder always goes first. *(**own**)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 11 | 60 | **Thunder Cloud** *(needs 4)*: At the start of each battle, each enemy has a 30% chance to be paralyzed. *(**own**)* | **Gigavolt** *(needs 4)*: Thunder hits every enemy, at full damage. *(**own**)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 12 | 75 | **Supercharged** *(needs 6)*: The user's Electric moves deal 50% more to paralyzed enemies. *(**own**)* | **Thunder God** *(needs 6)*: Thunderbolt and Thunder never miss, and are always critical hits on a target below half HP. *(**own**)* | **Lightning Speed** *(needs 6)*: Quick Attack hits 3 times, at 70% power each. *(Quick Attack)* |
