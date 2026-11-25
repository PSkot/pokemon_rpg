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
  (Bulbasaur, Charmander, Squirtle); the early routes' Pidgey, Rattata,
  Spearow, Nidoran ♀ and ♂, Caterpie, Weedle and Pikachu; the Pewter Gym's
  Geodude and Onix, Route 3's Jigglypuff, Sandshrew and Ekans, and Mt.
  Moon's Zubat, Paras and Clefairy, and the Cerulean Gym's Goldeen, Staryu
  (and Starmie), Horsea, Shellder and Psyduck, and Routes 24 and 25's
  Oddish, Bellsprout, Abra (and Kadabra) and Venonat; Diglett, from
  the Pewter Gym's waves; Route 5's Meowth and Mankey; the S.S. Anne's
  Machop, Tentacool and Growlithe; and the Vermilion Gym's Voltorb and
  Magnemite (Raichu takes Pikachu's moves and talents). Every line in the game now has talents. (Dugtrio, Graveler,
  Sandslash, Arbok, Golbat, Parasect, Seaking, Seadra, Golduck, Gloom,
  Weepinbell, Venomoth, Alakazam, Persian, Primeape, Machoke, Tentacruel, Arcanine, Electrode and Magneton aren't in the game yet, and Staryu
  doesn't evolve in it, so those lines can't learn their
  evolved forms' moves; their trees are built on the moves they can.)
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
    Charge Up; Rock: Stone Fist, Landslide, Sharp Rocks, Rockfall,
    Stone Edge, Jagged Hide; Ground: Mud Claws, Groundswell, Tremor, Burrow
    Feast, Sand Veil, Sand Force, Sand Stream; Fighting: Fighting Spirit,
    Last Stand, Combo, Victory Rush, Pressure Points, Stagger; Psychic:
    Telepathy, Mind Over Matter, Focus Mind, Mind Feast, Magic Guard; Fire: Blaze, Searing, Scorch, Smoulder, Ash Cloud, Wildfire,
    Heat Haze; Water: Torrent, Undertow, Splash Zone, Hydration; Ice:
    Frostbite, Chill; sleep: Nightmare, Deep Sleep, Lull, Yawn, Dream
    Eater, Bedtime Story; paralysis: Conductor; freezing: Shatter;
    confusion: Mind Games, Mind Crush, Hysteria). A type's "low HP", "in a row" and "knockout heals" talents
    share one mechanism (Overgrow / Cornered / Swarm / Surge; Ripening /
    Momentum / Hive Mind / Charge Up; Harvest / Scavenger / Bird of Prey /
    Feeding Frenzy / Discharge); the rest of each pool is the type's own;
  - **move pools**: for lines that learn that move (Growl: Taunting Growl,
    Echoing Growl; Quick Attack: Lightning Reflexes, Hit and Run,
    Lightning Speed; Leech Seed: Creeping Seed, Seed Bomb, ...);
  - **any**: any line can have them (Sturdy, Second Wind, Guardian, Head
    Start, Lucky Strikes, Tenacity, Unbreakable, Ambush, Gang Up, Blur,
    Apex Predator, Intimidate, Resilience, Bulwark Stance, Solid Rock,
    Squeeze, Exploit Weakness, Wish);
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
  to at most 100%; `keen`, `hunt`, `power`, `bleed` (wounds) and a spreading
  move's `spread_share` keep the higher value, so a later talent never weakens an earlier one;
  `type`, `hits` are set): `"basic"` (the basic
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
    hit taken each battle: half; Juggernaut, Iron Turtle: none); **filter**
    (Solid Rock: super-effective hits on the holder deal 25% less);
    **prey:bound** (Squeeze: +30% on a bound target); **sniper** (the
    holder's critical hits deal ×2, not ×1.5); **magic_guard** (Magic
    Guard: no damage from poison, burns, seeds, binds, wounds or
    nightmares); **Pyre**
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
    Absolute Zero: 20% frozen; Dazzling Fins: 25% confused), **intimidate** (every foe's Attack −1
    stage; Sand Veil: accuracy −1, Sand Stream −2: **lower:<stat>**).
- **Move fields** they use (`moves.Move`): `taunt` (Taunting Growl, Decoy,
  Mob Rule, Lightning Rod: for this round and the next, the foes'
  single-target moves go to the user), `hunt`
  and `hunt_crit` (Apex Predator; Stone Edge, Tidal Force, Keen Edge,
  Thunder God: that many more percentage points of crit chance on a target
  below that share of its HP; `keen`, always a crit, is left to the gear
  effect Executioner),
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
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Sprout Strike**: The basic attack becomes a Grass move (with STAB). *(Grass)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Creeping Seed**: When a seeded enemy faints, its seed jumps to an enemy next to it. *(Leech Seed)* | **Seed Bomb**: Leech Seed also deals damage (Grass, 30 power) when it lands. *(Leech Seed)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 3 | 14 | **Thorned Whip**: Vine Whip has a 30% chance to poison. *(Vine Whip)* | **Double Lash**: Vine Whip hits twice, at 60% power each. *(Vine Whip)* | **Thirsty Vines**: Vine Whip heals the user half the damage it deals. *(Vine Whip)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Ripening**: Each Grass move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Grass)* | **Canopy**: Leaf Shield covers the whole party. *(Leaf Shield)* |
| 6 | 27 | **Pollen Cloud**: Poison Powder hits every enemy, each at half the chance (one alone: the full chance). *(Poison Powder)* | **Keen Edge**: Razor Leaf has +30% critical-hit chance on a target below half HP. *(Razor Leaf)* | **Thornskin**: For 3 rounds, whoever hits a Pokémon behind Leaf Shield loses 1/16 of its max HP. *(Leaf Shield)* |
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
| 6 | 27 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Blade Dance**: Swords Dance also makes the user's next damaging move deal 50% more. *(Swords Dance)* | **Feed the Flames**: Knocking an enemy out with a Fire move heals the user 1/4 of its max HP. *(Fire)* |
| 7 | 32 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Scorching Breath**: Flamethrower is 20% more likely to burn. *(Flamethrower)* | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Blowtorch**: Flamethrower also hits one enemy next to the target, at half damage. *(Flamethrower)* |
| 9 | 44 | **Wildfire**: Burns the user inflicts have a 30% chance each round to spread to an enemy next to it. *(Fire)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 10 | 50 | **Vortex**: Fire Spin's flames hurt twice as much: 1/8 of max HP each round. *(Fire Spin)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Firestorm**: Fire Spin hits every enemy. *(Fire Spin)* |
| 11 | 60 | **Heat Haze** *(needs 4)*: At the start of each battle, each enemy has a 30% chance to be burned. *(Fire)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Fault Line** *(needs 4)*: Earthquake hits every enemy, the others at 60% damage. *(Earthquake)* |
| 12 | 75 | **Pyre** *(needs 6)*: Enemies the user's side burned lose a further 1/8 of their max HP each round. *(**own**)* | **Dragon Claw** *(needs 6)*: Slash is always a critical hit. *(Slash)* | **Supernova** *(needs 6)*: Fire Blast hits every enemy at full damage, and burns 50% of the time. *(**own**)* |

### Squirtle → Wartortle → Blastoise

Moves: Tackle, Tail Whip, Bubble 8, Water Gun 15, Bite 22, Withdraw 28, Ice Beam 30 (Wartortle), Skull Bash 35 (Blastoise), Hydro Pump 42 (Blastoise), Blizzard 55 (Blastoise).

Paths: **Torrent** (water damage); **Shell** (withdraw and shells: taking the hits, and shielding the party); **Tide** (slowing, freezing and wearing enemies down).

| Tier | Lv | Torrent | Shell | Tide |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Splash Strike**: The basic attack becomes a Water move (with STAB). *(Water)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 2 | 10 | **Bubble Burst**: Bubble hits every enemy, the others at 60% damage. *(Bubble)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Froth**: Bubble is twice as likely to lower Speed. *(Bubble)* |
| 3 | 14 | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* | **Rough Shell**: Whoever hits the user loses 1/16 of its max HP. *(Water)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* |
| 4 | 18 | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* |
| 5 | 22 | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* |
| 6 | 27 | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* | **Riptide**: Enemies with lowered Speed take 30% more damage from the user's party. *(**own**)* |
| 7 | 32 | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* | **Shell Shield**: Withdraw also halves the damage the user takes for 2 rounds. *(Withdraw)* | **Frostbite**: The user's Ice moves are 10% more likely to freeze. *(Ice)* |
| 8 | 38 | **Headlong**: Once the user has used Withdraw in a battle, Skull Bash needs no charging. *(Skull Bash)* | **Turtle Wall**: Withdraw works on the whole party. *(Withdraw)* | **Frost Ray**: Ice Beam hits every enemy, the others at 50% damage. *(Ice Beam)* |
| 9 | 44 | **Geyser**: Hydro Pump hits every enemy, the others at 50% damage. *(Hydro Pump)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Shatter**: Frozen enemies take 50% more damage from the user. *(Freeze)* |
| 10 | 50 | **Hydro Cannon**: Hydro Pump never misses. *(Hydro Pump)* | **Shell Formation**: While the user stands, the whole party takes 15% less damage. *(**own**)* | **Chill**: The user's Ice moves have a 30% chance to lower the target's Speed 1 stage. *(Ice)* |
| 11 | 60 | **Tsunami** *(needs 4)*: Hydro Pump hits every enemy at full damage. *(Hydro Pump)* | **Iron Turtle** *(needs 4)*: The first hit the user takes in each battle deals no damage, and Withdraw heals the user 1/4 of its max HP. *(Withdraw)* | **Whiteout** *(needs 4)*: Blizzard never misses and hits every enemy, the others at 60% damage. *(Blizzard)* |
| 12 | 75 | **Tidal Force** *(needs 6)*: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* | **Absolute Zero** *(needs 6)*: At the start of each battle, each enemy has a 20% chance to be frozen. *(Freeze)* |

### Spearow → Fearow

Moves: Peck, Growl, Leer 9, Fury Attack 15, Swift 20, Whirlwind 22, Drill Peck 29 (Fearow), Agility 36, Hyper Beam 45 (Fearow).

Paths: **Talon** (pecks and Drill Peck: hard Flying strikes); **Flock** (fury Attack and ganging up); **Bully** (growl and Leer: weakening and scaring the enemies).

| Tier | Lv | Talon | Flock | Bully |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Pecking Order**: Peck has a 30% chance to make the target flinch. *(Peck)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 2 | 10 | **Rapid Pecks**: Peck hits twice, at 70% power each. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 3 | 14 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 4 | 18 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Screech Growl**: Growl lowers Attack 2 stages. *(**own**)* |
| 5 | 22 | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* | **Harrier**: Fury Attack becomes a Flying move. *(**own**)* | **Mob Rule**: Leer also makes every enemy attack the user, this round and the next. *(**own**)* |
| 6 | 27 | **Aerial Ace**: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Drill Run**: Drill Peck also hits one enemy next to the target, at half damage. *(Drill Peck)* | **Howling Wind**: Whirlwind also deals damage (Normal, 30 power) to every enemy. *(Whirlwind)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 8 | 38 | **Fearsome Beak**: Drill Peck has a 30% chance to make the target flinch. *(**own**)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 9 | 44 | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* | **Tailwind**: Agility works on the whole party. *(Agility)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Tempest**: Whirlwind lowers Speed 2 stages. *(Whirlwind)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 11 | 60 | **Sky Tyrant** *(needs 4)*: The user's Flying moves always go first, and its moves deal 50% more to a target that hasn't moved yet this round. *(**own**)* | **Murder of Crows** *(needs 4)*: The user's moves deal 50% more to a target a partner already hit this round. *(**own**)* | **Spiteful** *(needs 4)*: Enemies with lowered Attack take 30% more damage from the user's party. *(**own**)* |
| 12 | 75 | **Apex Predator** *(needs 6)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Storm of Beaks** *(needs 6)*: Fury Attack hits every enemy, at full damage. *(**own**)* | **Reign of Terror** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Nidoran F → Nidorina → Nidoqueen

Moves: Tackle, Growl, Scratch 8, Poison Sting 14, Tail Whip 21, Body Slam 25 (Nidorina), Bite 29, Fury Swipes 36, Double Kick 43, Earthquake 48 (Nidoqueen).

Paths: **Venom** (poison, and making it worse); **Claw** (scratching, biting and kicking); **Matriarch** (keeping the partner safe).

| Tier | Lv | Venom | Claw | Matriarch |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 2 | 10 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 3 | 14 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Thorny Hide**: Whoever hits the user loses 1/16 of its max HP. *(**own**)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Venom Claws**: Scratch has a 30% chance to poison. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Echoing Growl**: Growl works on every enemy. *(Growl)* |
| 8 | 38 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Raking Claws**: Fury Swipes wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Fury Swipes)* | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(Any)* |
| 9 | 44 | **Toxic Fangs**: Bite has a 30% chance to poison. *(Bite)* | **Rapid Kicks**: Each of Double Kick's hits has a 30% chance to make the target flinch. *(Double Kick)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Toxic Swipes**: Fury Swipes has a 20% chance per hit to poison. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Den Mother** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |
| 12 | 75 | **Venom Queen** *(needs 6)*: All poison the user inflicts is bad poison, and poisoned enemies take 25% more damage from it. *(**own**)* | **Frenzy Claws** *(needs 6)*: Fury Swipes always hits 5 times. *(Fury Swipes)* | **Queen's Guard** *(needs 6)*: Once a battle, a partner that would faint keeps 1 HP, and the user heals it 1/4 of its max HP. *(**own**)* |

### Nidoran M → Nidorino → Nidoking

Moves: Tackle, Leer, Horn Attack 8, Poison Sting 14, Focus Energy 21, Body Slam 25 (Nidorino), Fury Attack 29, Thrash 38 (Nidoking), Double Kick 43, Earthquake 48 (Nidoking).

Paths: **Venom** (poison, and making it worse); **Horn** (horn Attack: critical hits and piercing); **Brawler** (focus, charging and momentum).

| Tier | Lv | Venom | Horn | Brawler |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Charge**: Tackle hits harder: 50 power. *(Tackle)* |
| 2 | 10 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Gore**: Horn Attack has a high critical-hit ratio. *(Horn Attack)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 3 | 14 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Piercing Horn**: Horn Attack also hits one enemy next to the target, at half damage. *(Horn Attack)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 5 | 22 | **Horn Drill**: Horn Attack has a 30% chance to poison. *(**own**)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 7 | 32 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Battle Focus**: Focus Energy also makes the user's next damaging move deal 50% more. *(**own**)* |
| 8 | 38 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* |
| 9 | 44 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Rapid Kicks**: Each of Double Kick's hits has a 30% chance to make the target flinch. *(Double Kick)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 10 | 50 | **Toxic Horn**: Horn Attack is a Poison move, and poisons 30% of the time. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Shared Focus** *(needs 4)*: Focus Energy works on the whole party. *(Focus Energy)* |
| 12 | 75 | **Venom Lord** *(needs 6)*: All poison the user inflicts is bad poison, and the user's hits have a 20% chance to poison. *(**own**)* | **Megahorn** *(needs 6)*: Horn Attack hits much harder: 100 power. *(Horn Attack)* | **Juggernaut** *(needs 6)*: The first hit the user takes in each battle deals no damage, and its Normal moves never miss. *(**own**)* |

### Pidgey → Pidgeotto → Pidgeot

Moves: Gust, Sand-Attack 5, Quick Attack 12, Whirlwind 19, Wing Attack 28, Double-Edge 35 (Pidgeot), Agility 36, Sky Attack 44 (Pidgeot).

Paths: **Gale** (wind that hits every enemy); **Raptor** (fast, hard strikes on one target); **Scout** (sand in the eyes, decoys, and keeping the partner up).

| Tier | Lv | Gale | Raptor | Scout |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Squall**: Gust hits every enemy, the others at 50% damage. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Sandstorm**: Sand-Attack works on every enemy. *(Sand-Attack)* |
| 2 | 10 | **Buffeting Winds**: Gust has a 30% chance to lower the target's Speed 1 stage. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Blinding Grit**: Sand-Attack lowers accuracy 2 stages. *(Sand-Attack)* |
| 3 | 14 | **Cyclone**: Gust has a 10% chance to confuse. *(**own**)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* | **Kick Up Dust**: After Sand-Attack, the user hits the target with its basic attack at 60% power. *(Sand-Attack)* |
| 4 | 18 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Howling Wind**: Whirlwind also deals damage (Normal, 30 power) to every enemy. *(Whirlwind)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Dust Devil**: Sand-Attack also makes the target take 20% more damage from everyone, for 3 rounds. *(Sand-Attack)* |
| 6 | 27 | **Tempest**: Whirlwind lowers Speed 2 stages. *(Whirlwind)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 7 | 32 | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* | **Gale Wings**: Wing Attack always goes first. *(Wing Attack)* | **Decoy**: Sand-Attack also makes every enemy attack the user, this round and the next. *(Sand-Attack)* |
| 8 | 38 | **Downdraft**: Wing Attack hits every enemy, the others at 60% damage. *(**own**)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 9 | 44 | **Eye of the Storm**: Below 1/3 HP, the user's Normal and Flying moves deal 1.5× damage. *(**own**)* | **Ascend**: Once the user has used Agility in a battle, Sky Attack needs no charging. *(Sky Attack)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Gale Force**: The user's moves that hit every enemy deal 25% more. *(**own**)* | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* | **Preening**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* |
| 11 | 60 | **Wind Shear** *(needs 4)*: The user's moves that hit every enemy have a 20% chance to make each one flinch. *(**own**)* | **Aerial Ace** *(needs 4)*: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* | **Blind Spot** *(needs 4)*: Enemies with lowered accuracy take 20% more damage from the user's party. *(Any)* |
| 12 | 75 | **Hurricane** *(needs 6)*: Gust becomes a Flying move with 60 power, and hits every enemy at full damage. *(**own**)* | **Apex Predator** *(needs 6)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Sheltering Wings** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Rattata → Raticate

Moves: Tackle, Tail Whip, Quick Attack 7, Focus Energy 23, Hyper Fang 25 (Raticate), Body Slam 25 (Raticate), Super Fang 35 (Raticate), Hyper Beam 45 (Raticate).

Paths: **Fang** (biting: wounds, flinches and fangs); **Scurry** (speed: Quick Attack, and striking first); **Survivor** (scrappy: fighting on when cornered).

| Tier | Lv | Fang | Scurry | Survivor |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Gnawing Tackle**: Tackle wounds the target: 1/12 of its max HP each round, for 3 rounds. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 2 | 10 | **Nip**: Tackle has a 30% chance to make the target flinch. *(**own**)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 3 | 14 | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Overtake**: Quick Attack is 4× as likely to be a critical hit. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 6 | 27 | **Bone Crusher**: Hyper Fang is 20% more likely to make the target flinch. *(Hyper Fang)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 7 | 32 | **Crushing Fang**: Hyper Fang has a 50% chance to lower the target's Defense 1 stage. *(**own**)* | **Shared Focus**: Focus Energy works on the whole party. *(Focus Energy)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 8 | 38 | **Gnaw**: Super Fang also wounds: 1/12 of the target's max HP each round, for 3 rounds. *(Super Fang)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Frenzied Bite**: Super Fang has a 50% chance to make the target flinch. *(**own**)* | **Sprinter**: Quick Attack hits twice, at 70% power each. *(**own**)* | **Nesting**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* |
| 10 | 50 | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Quick Claws**: Tackle always goes first. *(**own**)* | **Plague Rat**: The user's hits have a 15% chance to poison. *(**own**)* |
| 11 | 60 | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Hyper Gnasher** *(needs 6)*: Hyper Beam wounds: 1/8 of the target's max HP each round, for 3 rounds; no rest after a knockout. *(**own**)* | **Lightning Speed** *(needs 6)*: Quick Attack hits 3 times, at 70% power each. *(Quick Attack)* | **Pack Leader** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |

### Caterpie → Metapod → Butterfree

Moves: Tackle, String Shot, Harden 7 (Metapod), Confusion 12 (Butterfree), Poison Powder 15 (Butterfree), Stun Spore 16 (Butterfree), Sleep Powder 17 (Butterfree), Supersonic 21 (Butterfree), Mega Drain 25 (Butterfree), Whirlwind 26 (Butterfree), Psybeam 32 (Butterfree).

Paths: **Psychic** (confusion and Psybeam: muddled minds); **Powder** (string Shot and powders: status on every enemy); **Cocoon** (harden and shells: lasting, and shielding the partner).

| Tier | Lv | Psychic | Powder | Cocoon |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Web**: String Shot works on every enemy. *(String Shot)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Sticky Silk**: String Shot also makes the target take 20% more damage from everyone, for 3 rounds. *(String Shot)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* |
| 3 | 14 | **Psychic Wings**: Confusion and Psybeam are 20% more likely to confuse. *(Confusion)* | **Silk Strike**: After String Shot, the user hits the target with its basic attack at 60% power. *(**own**)* | **Cocoon**: Harden heals the user 1/4 of its max HP. *(**own**)* |
| 4 | 18 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Numbing Cloud**: Stun Spore works on every enemy, each at half the chance (one alone: the full chance). *(Stun Spore)* | **Shed Skin**: At the end of each round, the user has a 30% chance to shake off its status. *(Bug)* |
| 5 | 22 | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Shell Wall**: Harden works on the whole party. *(Harden)* |
| 6 | 27 | **Howling Wind**: Whirlwind also deals damage (Normal, 30 power) to every enemy. *(Whirlwind)* | **Drowsy Dust**: Sleep Powder works on every enemy, each at half the chance (one alone: the full chance). *(Sleep Powder)* | **Gluttony**: Mega Drain heals the user all the damage it deals (not half). *(Mega Drain)* |
| 7 | 32 | **Butterfly Dance**: The user's status moves also raise its Speed 1 stage. *(**own**)* | **Pollen Cloud**: Poison Powder hits every enemy, each at half the chance (one alone: the full chance). *(Poison Powder)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* | **Scale Dust**: Stun Spore, Poison Powder and Sleep Powder never miss and work 25% more often. *(Stun Spore)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 10 | 50 | **Tempest**: Whirlwind lowers Speed 2 stages. *(Whirlwind)* | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Soothing Spores**: Sleep Powder also cures the party's status conditions. *(Sleep Powder)* |
| 11 | 60 | **Psychic Mastery** *(needs 4)*: Psybeam hits every enemy, the others at 60% damage. *(Psybeam)* | **Powder Storm** *(needs 4)*: Psybeam has a 20% chance to set off Stun Spore, Poison Powder or Sleep Powder. *(Psybeam)* | **Monarch** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |
| 12 | 75 | **Mind Crush** *(needs 6)*: Confused enemies take 30% more damage from the user. *(Confusion)* | **Dream Eater** *(needs 6)*: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Metamorphosis** *(needs 6)*: Once a battle, ending a round below 1/3 HP heals the user half its max HP. *(**own**)* |

### Weedle → Kakuna → Beedrill

Moves: Poison Sting, String Shot, Harden 7 (Kakuna), Fury Attack 12 (Beedrill), Focus Energy 16 (Beedrill), Twineedle 20 (Beedrill), Swords Dance 25 (Beedrill), Pin Missile 30 (Beedrill), Agility 35 (Beedrill).

Paths: **Venom** (poison, and making it worse); **Swarm** (many quick stings); **Hive** (harden, silk and guarding the partner).

| Tier | Lv | Venom | Swarm | Hive |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Stinger**: Poison Sting hits harder: 30 power. *(**own**)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
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

### Oddish → Gloom → Vileplume

Moves: Absorb, Poison Powder 15, Stun Spore 17, Sleep Powder 19, Acid 24, Mega Drain 25 (Gloom), Petal Dance 33, Solar Beam 46 (Vileplume).

Paths: **Spore** (powders: poison, paralysis and sleep); **Bloom** (absorb and Petal Dance: Grass damage); **Root** (draining, healing, and keeping the party up).

| Tier | Lv | Spore | Bloom | Root |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Root Drink**: Absorb hits harder: 40 power. *(Absorb)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* | **Sap**: Absorb heals the user all the damage it deals (not half). *(Absorb)* |
| 3 | 14 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Ripening**: Each Grass move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Grass)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 4 | 18 | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Flower Power**: The user's Grass moves also hit one enemy next to the target, at half damage. *(Grass)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Numbing Cloud**: Stun Spore works on every enemy, each at half the chance (one alone: the full chance). *(Stun Spore)* | **Harvest**: Knocking an enemy out with a Grass move heals the user 1/4 of its max HP. *(Grass)* | **Soothing Spores**: Sleep Powder also cures the party's status conditions. *(Sleep Powder)* |
| 6 | 27 | **Drowsy Dust**: Sleep Powder works on every enemy, each at half the chance (one alone: the full chance). *(Sleep Powder)* | **Corrode**: Acid is twice as likely to lower Defense. *(Acid)* | **Photosynthesis**: The user heals 1/16 of its max HP at the end of each round. *(Grass)* |
| 7 | 32 | **Pollen Cloud**: Poison Powder hits every enemy, each at half the chance (one alone: the full chance). *(Poison Powder)* | **Acid Rain**: Acid hits every enemy, the others at 50% damage. *(Acid)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 8 | 38 | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Calm Petals**: Petal Dance no longer confuses the user. *(Petal Dance)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 9 | 44 | **Scale Dust**: Stun Spore, Poison Powder and Sleep Powder never miss and work 25% more often. *(Stun Spore)* | **Petal Storm**: Petal Dance's other targets take 60% damage (not 35%). *(Petal Dance)* | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(Any)* |
| 10 | 50 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Wish**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Petal Blizzard** *(needs 4)*: Petal Dance hits every enemy at full damage. *(**own**)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 12 | 75 | **Toxic Bloom** *(needs 6)*: At the start of each battle, each enemy has a 30% chance to be poisoned, and 30% to be paralyzed. *(**own**)* | **Last Bloom** *(needs 6)*: Below 1/3 HP, the user's Grass moves deal double damage. *(**own**)* | **Rafflesia** *(needs 6)*: While the user stands, the whole party heals 1/8 of its max HP at the end of each round. *(**own**)* |

### Goldeen → Seaking

Moves: Peck, Tail Whip, Water Gun 10, Supersonic 19, Horn Attack 24, Bubble Beam 24, Fury Attack 30, Ice Beam 40 (Seaking), Double-Edge 42 (Seaking), Agility 54.

Paths: **Horn** (peck and Horn Attack: piercing strikes); **Current** (water Gun and Bubble Beam); **Showy** (tail Whip and Supersonic: dazzling enemies, and staying up).

| Tier | Lv | Horn | Current | Showy |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Pecking Order**: Peck has a 30% chance to make the target flinch. *(Peck)* | **Water Peck**: Peck becomes a Water move (with STAB). *(**own**)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* |
| 2 | 10 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* |
| 3 | 14 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 4 | 18 | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* |
| 6 | 27 | **Gore**: Horn Attack has a high critical-hit ratio. *(Horn Attack)* | **Bubble Barrage**: Bubble Beam hits every enemy, the others at 50% damage. *(Bubble Beam)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* |
| 7 | 32 | **Piercing Horn**: Horn Attack also hits one enemy next to the target, at half damage. *(Horn Attack)* | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Foam**: Bubble Beam is twice as likely to lower Speed. *(Bubble Beam)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* |
| 11 | 60 | **Megahorn** *(needs 4)*: Horn Attack hits much harder: 100 power. *(Horn Attack)* | **Tidal Force** *(needs 4)*: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 12 | 75 | **Drill Horn** *(needs 6)*: Horn Attack always goes first and never misses. *(**own**)* | **Waterfall** *(needs 6)*: Bubble Beam hits much harder (100 power) and has a 20% chance to make the target flinch. *(**own**)* | **Dazzling Fins** *(needs 6)*: At the start of each battle, each enemy has a 25% chance to be confused. *(**own**)* |

### Staryu → Starmie

Moves: Tackle, Water Gun 17, Harden 22, Bubble Beam 24, Thunder Wave 26, Recover 27, Swift 32, Psychic 36 (Starmie), Thunderbolt 38 (Starmie), Ice Beam 40 (Starmie), Hydro Pump 47 (Starmie).

Paths: **Core** (harden and Recover: a star that keeps coming back); **Prism** (swift, Psychic, Thunderbolt, Ice Beam: beams of every kind); **Torrent** (water damage).

| Tier | Lv | Core | Prism | Torrent |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Splash Strike**: The basic attack becomes a Water move (with STAB). *(Water)* |
| 2 | 10 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* |
| 3 | 14 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* |
| 4 | 18 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* |
| 5 | 22 | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* |
| 6 | 27 | **Natural Cure**: Recover also cures the user's status. *(Recover)* | **Chain Lightning**: Thunder Wave works on every enemy, each at half the chance (one alone: the full chance). *(Thunder Wave)* | **Bubble Barrage**: Bubble Beam hits every enemy, the others at 50% damage. *(Bubble Beam)* |
| 7 | 32 | **Shell Wall**: Harden works on the whole party. *(Harden)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* |
| 8 | 38 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Foam**: Bubble Beam is twice as likely to lower Speed. *(Bubble Beam)* |
| 9 | 44 | **Regenerating Core**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* |
| 10 | 50 | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* |
| 11 | 60 | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* | **Sandblast** *(needs 4)*: Swift has a 50% chance to lower the target's accuracy 1 stage. *(Swift)* | **Tidal Force** *(needs 4)*: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* |
| 12 | 75 | **Star Core** *(needs 6)*: Recover heals all the user's HP. *(**own**)* | **Rainbow Beam** *(needs 6)*: Swift hits every enemy at full damage. *(**own**)* | **Whirlpool** *(needs 6)*: Bubble Beam hits every enemy at full damage. *(Bubble Beam)* |

### Abra → Kadabra → Alakazam

Moves: Confusion, Kinesis, Thunder Wave 12, Body Slam 25 (Kadabra), Psybeam 27 (Kadabra), Recover 31 (Kadabra), Psychic 38 (Kadabra), Reflect 42, Hyper Beam 50 (Alakazam).

Paths: **Mind** (confusion, Psybeam and Psychic: Psychic damage); **Spoon** (kinesis and Thunder Wave: blinding and stopping enemies); **Ward** (reflect and Recover: shielding itself and the party).

| Tier | Lv | Mind | Spoon | Ward |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Telepathy**: The user's Psychic moves never miss. *(Psychic)* | **Bend Spoons**: Kinesis works on every enemy. *(Kinesis)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Dizzying Mind**: Confusion is 20% more likely to confuse. *(Confusion)* | **Spoon Strike**: After Kinesis, the user hits the target with its basic attack at 60% power. *(Kinesis)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 3 | 14 | **Mind Over Matter**: Below 1/3 HP, the user's Psychic moves deal 1.5× damage. *(Psychic)* | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 4 | 18 | **Focus Mind**: Each Psychic move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Psychic)* | **Chain Lightning**: Thunder Wave works on every enemy, each at half the chance (one alone: the full chance). *(Thunder Wave)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 5 | 22 | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Blind Spot**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 6 | 27 | **Psychic Wings**: Confusion and Psybeam are 20% more likely to confuse. *(Confusion)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 7 | 32 | **Psychic Mastery**: Psybeam hits every enemy, the others at 60% damage. *(Psybeam)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Natural Cure**: Recover also cures the user's status. *(Recover)* |
| 8 | 38 | **Mind Blast**: Psychic hits every enemy, the others at 50% damage. *(Psychic)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Magic Guard**: The user takes no damage from poison, burns, seeds, binds, wounds or nightmares. *(Psychic)* |
| 9 | 44 | **Psycho Cut**: Psychic is 4× as likely to be a critical hit. *(Psychic)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* | **Barrier**: Reflect covers the whole party. *(Reflect)* |
| 10 | 50 | **Mind Feast**: Knocking an enemy out with a Psychic move heals the user 1/4 of its max HP. *(Psychic)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Mirror Shards**: For 3 rounds, whoever hits a Pokémon behind Reflect loses 1/16 of its max HP. *(Reflect)* |
| 11 | 60 | **Precognition** *(needs 4)*: Psychic always goes first. *(**own**)* | **Spoon Bender** *(needs 4)*: At the start of each battle, each enemy's accuracy has a 50% chance to fall 1 stage. *(**own**)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 12 | 75 | **Mind Storm** *(needs 6)*: Psychic hits every enemy at full damage. *(**own**)* | **Kinetic Crush** *(needs 6)*: Enemies with lowered accuracy take 50% more damage from the user's party. *(**own**)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* |

### Venonat → Venomoth

Moves: Tackle, Supersonic 24, Confusion 27, Poison Powder 30, Leech Life 35, Double-Edge 36 (Venomoth), Stun Spore 38, Psybeam 43, Sleep Powder 46, Psychic 51 (Venomoth).

Paths: **Eyes** (compound eyes: never missing, and muddling minds); **Powder** (poison, and powders on every enemy); **Swarm** (leech Life: a bug that won't go down).

| Tier | Lv | Eyes | Powder | Swarm |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Compound Eyes**: The user's damaging moves never miss. *(**own**)* | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* |
| 2 | 10 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 3 | 14 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 4 | 18 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 5 | 22 | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Hive Mind**: Each Bug move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Bug)* |
| 6 | 27 | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Shed Skin**: At the end of each round, the user has a 30% chance to shake off its status. *(Bug)* |
| 7 | 32 | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 8 | 38 | **Dizzying Mind**: Confusion is 20% more likely to confuse. *(Confusion)* | **Pollen Cloud**: Poison Powder hits every enemy, each at half the chance (one alone: the full chance). *(Poison Powder)* | **Bloodsucker**: Leech Life heals the user all the damage it deals (not half). *(Leech Life)* |
| 9 | 44 | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* | **Numbing Cloud**: Stun Spore works on every enemy, each at half the chance (one alone: the full chance). *(Stun Spore)* | **Vampire Fangs**: Leech Life hits harder: 40 power. *(Leech Life)* |
| 10 | 50 | **Psychic Mastery**: Psybeam hits every enemy, the others at 60% damage. *(Psybeam)* | **Drowsy Dust**: Sleep Powder works on every enemy, each at half the chance (one alone: the full chance). *(Sleep Powder)* | **Feeding Frenzy**: Knocking an enemy out with a Bug move heals the user 1/4 of its max HP. *(Bug)* |
| 11 | 60 | **Hysteria** *(needs 4)*: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Bedlam** *(needs 6)*: Enemies the user confuses always hurt themselves. *(Confusion)* | **Powder Storm** *(needs 6)*: Psybeam has a 20% chance to set off Stun Spore, Poison Powder or Sleep Powder. *(Psybeam)* | **Venom Swarm** *(needs 6)*: Leech Life hits every enemy at full damage. *(**own**)* |

### Meowth → Persian

Moves: Scratch, Growl, Bite 12, Pay Day 17, Screech 24, Fury Swipes 33, Slash 44 (Persian).

Paths: **Coin** (pay Day: lucky critical hits, and money); **Claw** (scratch, Fury Swipes and Slash: claws and wounds); **Prowl** (striking first: Bite, Screech and ambushes).

| Tier | Lv | Coin | Claw | Prowl |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Sharp Claws**: Scratch is 4× as likely to be a critical hit. *(Scratch)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Amulet Coin**: Pay Day hits harder (60 power) and scatters twice as much money. *(**own**)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 3 | 14 | **Lucky Coin**: Pay Day has a high critical-hit ratio. *(**own**)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* |
| 4 | 18 | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Raking Claws**: Fury Swipes wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Fury Swipes)* | **Piercing Screech**: Screech works on every enemy. *(Screech)* |
| 5 | 22 | **Coin Toss**: Pay Day hits every enemy, the others at 60% damage. *(**own**)* | **Frenzy Claws**: Fury Swipes always hits 5 times. *(Fury Swipes)* | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* |
| 6 | 27 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Glittering Coins**: Pay Day has a 30% chance to lower the target's accuracy 1 stage. *(**own**)* | **Crush Claw**: Slash has a 30% chance to lower the target's Defense 1 stage. *(Slash)* | **Stalker**: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* |
| 9 | 44 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Rending Claws**: Slash and Fury Swipes wound the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 10 | 50 | **Blind Spot**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Any)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Fortune** *(needs 4)*: Pay Day is always a critical hit. *(**own**)* | **Dragon Claw** *(needs 4)*: Slash is always a critical hit. *(Slash)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 12 | 75 | **Jackpot** *(needs 6)*: Pay Day hits 2-5 times, at 60% power each. *(**own**)* | **Thousand Cuts** *(needs 6)*: Fury Swipes and Slash hit every enemy, the others at 60% damage. *(**own**)* | **Pounce** *(needs 6)*: Bite always goes first, and makes the target flinch 50% of the time. *(**own**)* |

### Machop → Machoke → Machamp

Moves: Karate Chop, Low Kick 20, Leer 25, Focus Energy 32, Seismic Toss 39, Submission 46 (Machoke).

Paths: **Power** (karate Chop and Submission: heavy Fighting blows); **Grapple** (low Kick and Seismic Toss: throws, holds and combos); **Discipline** (leer and Focus Energy: training hard and lasting long).

| Tier | Lv | Power | Grapple | Discipline |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Fighting Spirit**: The basic attack becomes a Fighting move (with STAB). *(Fighting)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 2 | 10 | **Pressure Points**: The user's Fighting moves are 4× as likely to be critical hits. *(Fighting)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 3 | 14 | **Mach Punch**: Karate Chop always goes first. *(**own**)* | **Combo**: Each Fighting move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Fighting)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 4 | 18 | **Last Stand**: Below 1/3 HP, the user's Fighting moves deal 1.5× damage. *(Fighting)* | **Stagger**: The user's Fighting moves have a 30% chance to lower the target's Defense 1 stage. *(Fighting)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Dynamic Punch**: Karate Chop has a 30% chance to confuse. *(**own**)* | **Seismic Slam**: Seismic Toss hits every enemy, at full damage. *(**own**)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* |
| 6 | 27 | **Victory Rush**: Knocking an enemy out with a Fighting move heals the user 1/4 of its max HP. *(Fighting)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 7 | 32 | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* | **Body Throw**: Low Kick also lowers the target's Speed 1 stage. *(**own**)* | **Bulk Up**: Focus Energy also raises the user's Attack and Defense 1 stage. *(**own**)* |
| 8 | 38 | **Submission Hold**: Submission no longer hurts the user. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Shared Focus**: Focus Energy works on the whole party. *(Focus Energy)* |
| 9 | 44 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Momentum** *(needs 4)*: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 12 | 75 | **Close Combat** *(needs 6)*: Submission hits much harder: 120 power. *(**own**)* | **Atomic Drop** *(needs 6)*: Seismic Toss always goes first and never misses. *(**own**)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* |

### Tentacool → Tentacruel

Moves: Acid, Supersonic 7, Wrap 13, Poison Sting 18, Water Gun 22, Constrict 27, Barrier 33, Screech 40, Hydro Pump 48 (Tentacruel).

Paths: **Toxin** (acid and Poison Sting: poison that eats away); **Tide** (water Gun and Hydro Pump: Water damage); **Tangle** (wrap, Constrict, Supersonic and Barrier: holding enemies off).

| Tier | Lv | Toxin | Tide | Tangle |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Splash Strike**: The basic attack becomes a Water move (with STAB). *(Water)* | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* |
| 2 | 10 | **Corrode**: Acid is twice as likely to lower Defense. *(Acid)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 3 | 14 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* | **Coil Crush**: Wrap and Bind catch every enemy. *(Bind)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* | **Toxic Tentacles**: Constrict has a 30% chance to poison. *(**own**)* |
| 5 | 22 | **Acid Spray**: Acid has a 20% chance to poison. *(**own**)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* | **Crushing Coils**: Wrap and Bind have a 30% chance to paralyze. *(Bind)* |
| 7 | 32 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* |
| 8 | 38 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* | **Barrier Reef**: Barrier works on the whole party. *(**own**)* |
| 9 | 44 | **Acid Rain**: Acid hits every enemy, the others at 50% damage. *(Acid)* | **Geyser**: Hydro Pump hits every enemy, the others at 50% damage. *(Hydro Pump)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Tidal Force**: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 11 | 60 | **Virulent** *(needs 4)*: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Hydro Cannon** *(needs 4)*: Hydro Pump never misses. *(Hydro Pump)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Miasma** *(needs 6)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Tsunami** *(needs 6)*: Hydro Pump hits every enemy at full damage. *(Hydro Pump)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* |

### Growlithe → Arcanine

Moves: Bite, Roar, Ember 18, Leer 23, Take Down 30, Agility 39, Flamethrower 50 (Arcanine).

Paths: **Flame** (ember and Flamethrower: fire and burns); **Hound** (bite and Take Down: a fast, loyal hunter); **Guard** (roar and Leer: guarding the party).

| Tier | Lv | Flame | Hound | Guard |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Fireball**: Ember hits harder: 60 power. *(Ember)* | **Fire Fang**: Bite has a 20% chance to burn. *(**own**)* | **Howl**: Roar also raises the user's Attack 1 stage. *(**own**)* |
| 2 | 10 | **Searing**: The user's Fire moves are 20% more likely to burn. *(Fire)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 3 | 14 | **Blaze**: Below 1/3 HP, the user's Fire moves deal 1.5× damage. *(Fire)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 4 | 18 | **Ember Shower**: Ember hits every enemy, the others at 50% damage. *(Ember)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Intimidating Roar**: Roar also makes every enemy attack the user, this round and the next. *(**own**)* |
| 5 | 22 | **Stoke the Flames**: Each Fire move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Fire)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 6 | 27 | **Smoulder**: The user's Fire moves wound the target: 1/16 of its max HP each round, for 3 rounds. *(Fire)* | **Extreme Speed**: Take Down always goes first. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Scorch**: Burned enemies take 25% more damage from the user. *(Fire)* | **Flare Blitz**: Take Down becomes a Fire move (with STAB). *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Scorching Breath**: Flamethrower is 20% more likely to burn. *(Flamethrower)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Blowtorch**: Flamethrower also hits one enemy next to the target, at half damage. *(Flamethrower)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 10 | 50 | **Feed the Flames**: Knocking an enemy out with a Fire move heals the user 1/4 of its max HP. *(Fire)* | **Tailwind**: Agility works on the whole party. *(Agility)* | **Wish**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* |
| 11 | 60 | **Heat Haze** *(needs 4)*: At the start of each battle, each enemy has a 30% chance to be burned. *(Fire)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Sacred Fire** *(needs 6)*: Flamethrower burns 50% of the time, and also hits one enemy next to the target at half damage. *(**own**)* | **Apex Predator** *(needs 6)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* |

### Voltorb → Electrode

Moves: Tackle, Screech, Thunder Shock 12, Sonic Boom 17, Self-Destruct 22, Light Screen 29, Swift 36, Explosion 43 (Electrode).

Paths: **Spark** (thunder Shock: Electric damage and paralysis); **Roll** (tackle, Swift and Screech: rolling in first); **Blast** (light Screen, Self-Destruct and Explosion: going out with a bang).

| Tier | Lv | Spark | Roll | Blast |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Static**: Whoever hits the user has a 25% chance to be paralyzed. *(Electric)* | **Rolling Charge**: Tackle always goes first. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 3 | 14 | **Charge Up**: Each Electric move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Electric)* | **Charge**: Tackle hits harder: 50 power. *(Tackle)* | **Screen Wall**: Light Screen covers the whole party. *(**own**)* |
| 4 | 18 | **Surge**: Below 1/3 HP, the user's Electric moves deal 1.5× damage. *(Electric)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Live Bomb**: Self-Destruct deals 50% more. *(**own**)* |
| 5 | 22 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 6 | 27 | **Discharge**: Knocking an enemy out with a Electric move heals the user 1/4 of its max HP. *(Electric)* | **Sandblast**: Swift has a 50% chance to lower the target's accuracy 1 stage. *(Swift)* | **Chain Reaction**: Self-Destruct and Explosion hit every enemy, the others at 50% damage. *(**own**)* |
| 7 | 32 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Piercing Screech**: Screech works on every enemy. *(Screech)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 8 | 38 | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 9 | 44 | **Sonic Barrage**: Sonic Boom hits every enemy, at full damage. *(**own**)* | **Flash Bang**: Sonic Boom has a 30% chance to make the target flinch. *(**own**)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 11 | 60 | **Overcharge** *(needs 4)*: Thunder Shock hits much harder: 80 power. *(**own**)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Fortress** *(needs 4)*: While the user stands, the whole party takes 25% less damage. *(Any)* |
| 12 | 75 | **Ball Lightning** *(needs 6)*: Thunder Shock hits every enemy at full damage. *(**own**)* | **Gyro Ball** *(needs 6)*: Swift hits much harder: 90 power. *(**own**)* | **Big Bang** *(needs 6)*: Explosion hits every enemy at full damage. *(**own**)* |

### Magnemite → Magneton

Moves: Tackle, Sonic Boom 21, Thunder Shock 25, Supersonic 29, Thunder Wave 35, Swift 41, Screech 47.

Paths: **Magnet** (thunder Shock and Thunder Wave: paralysis); **Steel** (sonic Boom and a steel body: hard to bring down); **Pulse** (supersonic and Screech: scrambling enemies).

| Tier | Lv | Magnet | Steel | Pulse |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* |
| 2 | 10 | **Static**: Whoever hits the user has a 25% chance to be paralyzed. *(Electric)* | **Sonic Pulse**: Sonic Boom has a 30% chance to confuse. *(**own**)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* |
| 3 | 14 | **Charge Up**: Each Electric move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Electric)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Piercing Screech**: Screech works on every enemy. *(Screech)* |
| 4 | 18 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Lock-On**: The user's damaging moves never miss. *(**own**)* | **Gravity Pull**: Supersonic also lowers the target's Speed 1 stage. *(**own**)* |
| 5 | 22 | **Chain Lightning**: Thunder Wave works on every enemy, each at half the chance (one alone: the full chance). *(Thunder Wave)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* |
| 6 | 27 | **Surge**: Below 1/3 HP, the user's Electric moves deal 1.5× damage. *(Electric)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* |
| 7 | 32 | **Tri Attack**: Swift has a 30% chance to paralyze. *(**own**)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* |
| 8 | 38 | **Discharge**: Knocking an enemy out with a Electric move heals the user 1/4 of its max HP. *(Electric)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* | **Sandblast**: Swift has a 50% chance to lower the target's accuracy 1 stage. *(Swift)* |
| 9 | 44 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Magnet Pull**: Supersonic also makes every enemy attack the user, this round and the next. *(**own**)* |
| 10 | 50 | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 11 | 60 | **Zap Cannon** *(needs 4)*: Thunder Shock is 40% more likely to paralyze, and never misses. *(**own**)* | **Wish** *(needs 4)*: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* | **Bedlam** *(needs 4)*: Enemies the user confuses always hurt themselves. *(Confusion)* |
| 12 | 75 | **Magnet Storm** *(needs 6)*: Thunder Shock hits every enemy, the others at 60% damage. *(**own**)* | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* | **Blind Spot** *(needs 6)*: Enemies with lowered accuracy take 20% more damage from the user's party. *(Any)* |

### Mankey → Primeape

Moves: Scratch, Leer, Karate Chop 15, Low Kick 18, Fury Swipes 21, Focus Energy 27, Seismic Toss 33, Thrash 39 (Primeape).

Paths: **Fury** (fury Swipes and Thrash: a temper that builds); **Chop** (karate Chop and Low Kick: Fighting blows and critical hits); **Brawler** (leer, Focus Energy and Seismic Toss: picking fights and lasting them).

| Tier | Lv | Fury | Chop | Brawler |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Fighting Spirit**: The basic attack becomes a Fighting move (with STAB). *(Fighting)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 2 | 10 | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 3 | 14 | **Raking Claws**: Fury Swipes wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Fury Swipes)* | **Chop Chop**: Karate Chop hits twice, at 60% power each. *(**own**)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 4 | 18 | **Last Stand**: Below 1/3 HP, the user's Fighting moves deal 1.5× damage. *(Fighting)* | **Combo**: Each Fighting move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Fighting)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 5 | 22 | **Frenzy Claws**: Fury Swipes always hits 5 times. *(Fury Swipes)* | **Pressure Points**: The user's Fighting moves are 4× as likely to be critical hits. *(Fighting)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* |
| 6 | 27 | **Cool Head**: Thrash confuses the user only half the time. *(**own**)* | **Sweep Kick**: Low Kick hits every enemy, the others at 50% damage. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 7 | 32 | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Stagger**: The user's Fighting moves have a 30% chance to lower the target's Defense 1 stage. *(Fighting)* | **Vital Throw**: Seismic Toss always goes first. *(**own**)* |
| 8 | 38 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Victory Rush**: Knocking an enemy out with a Fighting move heals the user 1/4 of its max HP. *(Fighting)* | **Shared Focus**: Focus Energy works on the whole party. *(Focus Energy)* |
| 9 | 44 | **Rampaging Fists**: Thrash hits every enemy, the others at 50% damage. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* |
| 10 | 50 | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 11 | 60 | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 12 | 75 | **Primal Rage** *(needs 6)*: Thrash deals 50% more and no longer confuses the user. *(**own**)* | **Mega Kick** *(needs 6)*: Low Kick hits much harder: 100 power, and makes the target flinch 50% of the time. *(**own**)* | **Pick a Fight** *(needs 6)*: Leer works on every enemy, and makes them all attack the user, this round and the next. *(**own**)* |

### Bellsprout → Weepinbell → Victreebel

Moves: Vine Whip, Growth, Wrap 13, Poison Powder 15, Sleep Powder 18, Stun Spore 21, Acid 26, Swords Dance 30 (Weepinbell), Razor Leaf 33, Slam 42 (Weepinbell).

Paths: **Vine** (vine Whip and Wrap: whipping and binding); **Pitcher** (acid and poison: digesting enemies); **Leaf** (growth and Razor Leaf: sharp Grass damage).

| Tier | Lv | Vine | Pitcher | Leaf |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Double Lash**: Vine Whip hits twice, at 60% power each. *(Vine Whip)* | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Full Bloom**: Growth also makes the user's next damaging move deal 50% more. *(Growth)* |
| 2 | 10 | **Thirsty Vines**: Vine Whip heals the user half the damage it deals. *(Vine Whip)* | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* |
| 3 | 14 | **Constrict**: Wrap and Bind squeeze twice as hard: 1/8 of max HP each round. *(Bind)* | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Ripening**: Each Grass move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Grass)* |
| 4 | 18 | **Crushing Coils**: Wrap and Bind have a 30% chance to paralyze. *(Bind)* | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Shared Sun**: Growth works on the whole party. *(Growth)* |
| 5 | 22 | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* | **Drowsy Dust**: Sleep Powder works on every enemy, each at half the chance (one alone: the full chance). *(Sleep Powder)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 6 | 27 | **Thorned Whip**: Vine Whip has a 30% chance to poison. *(Vine Whip)* | **Corrode**: Acid is twice as likely to lower Defense. *(Acid)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 7 | 32 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Acid Rain**: Acid hits every enemy, the others at 50% damage. *(Acid)* | **Harvest**: Knocking an enemy out with a Grass move heals the user 1/4 of its max HP. *(Grass)* |
| 8 | 38 | **Coil Crush**: Wrap and Bind catch every enemy. *(Bind)* | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Keen Edge**: Razor Leaf has +30% critical-hit chance on a target below half HP. *(Razor Leaf)* |
| 9 | 44 | **Lashing Vines**: Vine Whip hits every enemy, the others at 50% damage. *(**own**)* | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Flower Power**: The user's Grass moves also hit one enemy next to the target, at half damage. *(Grass)* |
| 10 | 50 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 11 | 60 | **Constrictor** *(needs 4)*: Wrap's and Bind's grip hurts far more: a further 1/8 of max HP each round. *(**own**)* | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Leaf Storm** *(needs 4)*: Razor Leaf hits every enemy, the others at 60% damage. *(**own**)* |
| 12 | 75 | **Strangler Fig** *(needs 6)*: Enemies caught in a bind take 50% more damage from the user. *(**own**)* | **Digest** *(needs 6)*: Acid hits every enemy at full damage, and lowers Defense 2 stages. *(**own**)* | **Razor Wind** *(needs 6)*: Razor Leaf is always a critical hit. *(**own**)* |

### Pikachu → Raichu

Moves: Thunder Shock, Growl, Thunder Wave 9, Quick Attack 16, Swift 26, Thunderbolt 30, Agility 33, Thunder 43.

Paths: **Spark** (paralysis: slowing and stopping enemies); **Bolt** (raw Electric damage); **Agile** (quick Attack, speed and dodging trouble).

| Tier | Lv | Spark | Bolt | Agile |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Spark**: Thunder Shock is 20% more likely to paralyze. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Static**: Whoever hits the user has a 25% chance to be paralyzed. *(Electric)* | **Surge**: Below 1/3 HP, the user's Electric moves deal 1.5× damage. *(Electric)* | **Cheek Pouch**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(**own**)* |
| 3 | 14 | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 4 | 18 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Charge Up**: Each Electric move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Electric)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* |
| 5 | 22 | **Chain Lightning**: Thunder Wave works on every enemy, each at half the chance (one alone: the full chance). *(Thunder Wave)* | **Discharge**: Knocking an enemy out with a Electric move heals the user 1/4 of its max HP. *(Electric)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* |
| 6 | 27 | **Arc Flash**: Thunder Shock also hits one enemy next to the target, at half damage. *(**own**)* | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Volt Tackle**: Quick Attack becomes an Electric move with 60 power. *(**own**)* |
| 7 | 32 | **Lightning Rod**: Thunder Wave also makes every enemy attack the user, this round and the next. *(**own**)* | **High Voltage**: Thunderbolt is 4× as likely to be a critical hit. *(Thunderbolt)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 8 | 38 | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* |
| 9 | 44 | **Thunderstorm**: Thunder never misses, and paralyzes 30% of the time. *(**own**)* | **Overload**: Thunderbolt and Thunder hit every enemy, the others at 50% damage. *(**own**)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 10 | 50 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Thunderclap**: Thunder always goes first. *(**own**)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 11 | 60 | **Thunder Cloud** *(needs 4)*: At the start of each battle, each enemy has a 30% chance to be paralyzed. *(**own**)* | **Gigavolt** *(needs 4)*: Thunder hits every enemy, at full damage. *(**own**)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 12 | 75 | **Supercharged** *(needs 6)*: The user's Electric moves deal 50% more to paralyzed enemies. *(**own**)* | **Thunder God** *(needs 6)*: Thunderbolt and Thunder never miss, and have +30% critical-hit chance on a target below half HP. *(**own**)* | **Lightning Speed** *(needs 6)*: Quick Attack hits 3 times, at 70% power each. *(Quick Attack)* |

### Shellder → Cloyster

Moves: Tackle, Withdraw, Water Gun 10, Supersonic 18, Clamp 23, Bubble Beam 25, Aurora Beam 30, Spike Cannon 35 (Cloyster), Leer 39, Ice Beam 50, Blizzard 55 (Cloyster).

Paths: **Shell** (withdraw: the hardest shell in the sea); **Clamp** (clamp and Supersonic: catching and confusing); **Frost** (water Gun, then Aurora Beam and Ice Beam).

| Tier | Lv | Shell | Clamp | Frost |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Frost Tackle**: Tackle becomes an Ice move. *(**own**)* |
| 2 | 10 | **Shell Shield**: Withdraw also halves the damage the user takes for 2 rounds. *(Withdraw)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* |
| 3 | 14 | **Rough Shell**: Whoever hits the user loses 1/16 of its max HP. *(Water)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* |
| 4 | 18 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* |
| 5 | 22 | **Turtle Wall**: Withdraw works on the whole party. *(Withdraw)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* |
| 6 | 27 | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* | **Iron Jaw**: Clamp grips twice as hard: 1/8 of max HP each round. *(Clamp)* | **Bubble Barrage**: Bubble Beam hits every enemy, the others at 50% damage. *(Bubble Beam)* |
| 7 | 32 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* | **Frostbite**: The user's Ice moves are 10% more likely to freeze. *(Ice)* |
| 8 | 38 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Chill**: The user's Ice moves have a 30% chance to lower the target's Speed 1 stage. *(Ice)* |
| 9 | 44 | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* | **Northern Lights**: Aurora Beam has a 50% chance to lower the target's Attack. *(Aurora Beam)* |
| 10 | 50 | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* | **Frost Ray**: Ice Beam hits every enemy, the others at 50% damage. *(Ice Beam)* |
| 11 | 60 | **Iron Turtle** *(needs 4)*: The first hit the user takes in each battle deals no damage, and Withdraw heals the user 1/4 of its max HP. *(Withdraw)* | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Shatter** *(needs 4)*: Frozen enemies take 50% more damage from the user. *(Freeze)* |
| 12 | 75 | **Fortress** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(Any)* | **Pearl Crusher** *(needs 6)*: Clamp hits much harder (80 power) and grips harder: a further 1/16 of max HP a round. *(**own**)* | **Absolute Zero** *(needs 6)*: At the start of each battle, each enemy has a 20% chance to be frozen. *(Freeze)* |

### Psyduck → Golduck

Moves: Scratch, Water Gun 8, Bubble Beam 20, Tail Whip 28, Confusion 36, Fury Swipes 43, Ice Beam 45 (Golduck), Hydro Pump 52 (Golduck).

Paths: **Headache** (confusion: a head full of pain and power); **Paddle** (water damage); **Scratch** (scratch and Fury Swipes).

| Tier | Lv | Headache | Paddle | Scratch |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Migraine**: Below 1/3 HP, all the user's moves deal 1.5× damage. *(**own**)* | **Splash Strike**: The basic attack becomes a Water move (with STAB). *(Water)* | **Sharp Claws**: Scratch is 4× as likely to be a critical hit. *(Scratch)* |
| 2 | 10 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 3 | 14 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 4 | 18 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 5 | 22 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Bubble Barrage**: Bubble Beam hits every enemy, the others at 50% damage. *(Bubble Beam)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 6 | 27 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 7 | 32 | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* | **Foam**: Bubble Beam is twice as likely to lower Speed. *(Bubble Beam)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 8 | 38 | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 9 | 44 | **Dizzying Mind**: Confusion is 20% more likely to confuse. *(Confusion)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* | **Raking Claws**: Fury Swipes wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Fury Swipes)* |
| 10 | 50 | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* | **Frenzy Claws**: Fury Swipes always hits 5 times. *(Fury Swipes)* |
| 11 | 60 | **Mind Crush** *(needs 4)*: Confused enemies take 30% more damage from the user. *(Confusion)* | **Tidal Force** *(needs 4)*: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 12 | 75 | **Psychic Surge** *(needs 6)*: Confusion hits every enemy at full damage, and confuses half the time. *(**own**)* | **Whirlpool** *(needs 6)*: Bubble Beam hits every enemy at full damage. *(Bubble Beam)* | **Blur** *(needs 6)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |

### Horsea → Seadra

Moves: Bubble, Smokescreen 19, Bubble Beam 20, Leer 24, Water Gun 30, Agility 37, Ice Beam 40 (Seadra), Hydro Pump 45 (Seadra).

Paths: **Ink** (smokescreen: blinding enemies, and punishing the blind); **Current** (bubble and Bubble Beam); **Dart** (speed, and striking first).

| Tier | Lv | Ink | Current | Dart |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Murky Water**: Bubble has a 20% chance to lower the target's accuracy 1 stage. *(**own**)* | **Bubble Burst**: Bubble hits every enemy, the others at 60% damage. *(Bubble)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Froth**: Bubble is twice as likely to lower Speed. *(Bubble)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 3 | 14 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 5 | 22 | **Smoke Cloud**: Smokescreen works on every enemy. *(Smokescreen)* | **Bubble Barrage**: Bubble Beam hits every enemy, the others at 50% damage. *(Bubble Beam)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 6 | 27 | **Ink Blind**: Smokescreen lowers accuracy 2 stages. *(Smokescreen)* | **Foam**: Bubble Beam is twice as likely to lower Speed. *(Bubble Beam)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 7 | 32 | **Blind Spot**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Any)* | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 8 | 38 | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* |
| 9 | 44 | **Menacing Leer**: Leer works on every enemy. *(Leer)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 10 | 50 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 11 | 60 | **Smoke Bomb** *(needs 4)*: At the start of each battle, each enemy's accuracy has a 50% chance to fall 1 stage. *(**own**)* | **Tidal Force** *(needs 4)*: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Phantom Ink** *(needs 6)*: Enemies with lowered accuracy take 50% more damage from the user's party. *(Any)* | **Whirlpool** *(needs 6)*: Bubble Beam hits every enemy at full damage. *(Bubble Beam)* | **Sniper** *(needs 6)*: The user's critical hits deal double damage (not 1.5×). *(**own**)* |

### Geodude → Graveler → Golem

Moves: Tackle, Defense Curl 11, Rock Throw 16, Rock Slide 25 (Graveler), Harden 26, Body Slam 30 (Graveler), Earthquake 35 (Golem), Dig 35 (Golem).

Paths: **Boulder** (rock Throw: hard Rock hits); **Bedrock** (defense Curl and Harden: taking the hits); **Tumble** (tackle and momentum: rolling over enemies).

| Tier | Lv | Boulder | Bedrock | Tumble |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Stone Fist**: The basic attack becomes a Rock move (with STAB). *(Rock)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 2 | 10 | **Landslide**: Below 1/3 HP, the user's Rock moves deal 1.5× damage. *(Rock)* | **Jagged Hide**: Whoever hits the user loses 1/16 of its max HP. *(Rock)* | **Charge**: Tackle hits harder: 50 power. *(Tackle)* |
| 3 | 14 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Curl Up**: Defense Curl also halves the damage the user takes for 2 rounds. *(Defense Curl)* | **Rollout**: Defense Curl also makes the user's next damaging move deal 50% more. *(Defense Curl)* |
| 4 | 18 | **Sure Aim**: Rock Throw never misses. *(Rock Throw)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 5 | 22 | **Sharp Rocks**: The user's Rock moves are 4× as likely to be critical hits. *(Rock)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* | **Rolling Stones**: Each Rock move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Rock)* |
| 6 | 27 | **Rock Barrage**: Rock Throw hits every enemy, the others at 50% damage. *(Rock Throw)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 7 | 32 | **Rockfall**: The user's Rock moves have a 30% chance to make the target flinch. *(Rock)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 8 | 38 | **Heavy Stone**: Rock Throw hits harder: 80 power. *(**own**)* | **Shell Wall**: Harden works on the whole party. *(Harden)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 9 | 44 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 10 | 50 | **Rock Blast**: Rock Throw hits 2-5 times, at 40% power each. *(**own**)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Steamroller**: Tackle hits every enemy at full damage. *(**own**)* |
| 11 | 60 | **Stone Edge** *(needs 4)*: The user's Rock moves have +30% critical-hit chance on a target below half HP. *(Rock)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* | **Boulder Roll** *(needs 4)*: Tackle always goes first and never misses. *(**own**)* |
| 12 | 75 | **Avalanche** *(needs 6)*: Rock Throw hits every enemy at full damage. *(**own**)* | **Living Mountain** *(needs 6)*: The first hit the user takes in each battle deals no damage, and while it stands the whole party takes 25% less damage. *(**own**)* | **Unstoppable** *(needs 6)*: Each Normal or Rock move in a row deals 30% more than the last, up to +90%. *(**own**)* |

### Onix

Moves: Tackle, Screech, Bind 15, Rock Throw 19, Rock Slide 28, Slam 33, Earthquake 38, Harden 43.

Paths: **Quake** (rock Slide and Earthquake: Rock and Ground damage); **Coil** (bind: catching and crushing enemies); **Titan** (size and stone: scaring enemies and shrugging off hits).

| Tier | Lv | Quake | Coil | Titan |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Stone Fist**: The basic attack becomes a Rock move (with STAB). *(Rock)* | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Landslide**: Below 1/3 HP, the user's Rock moves deal 1.5× damage. *(Rock)* | **Piercing Screech**: Screech works on every enemy. *(Screech)* | **Jagged Hide**: Whoever hits the user loses 1/16 of its max HP. *(Rock)* |
| 3 | 14 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 4 | 18 | **Rolling Stones**: Each Rock move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Rock)* | **Constrict**: Wrap and Bind squeeze twice as hard: 1/8 of max HP each round. *(Bind)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Sure Aim**: Rock Throw never misses. *(Rock Throw)* | **Crushing Coils**: Wrap and Bind have a 30% chance to paralyze. *(Bind)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 6 | 27 | **Rock Barrage**: Rock Throw hits every enemy, the others at 50% damage. *(Rock Throw)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 7 | 32 | **Rockfall**: The user's Rock moves have a 30% chance to make the target flinch. *(Rock)* | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 8 | 38 | **Fault Line**: Earthquake hits every enemy, the others at 60% damage. *(Earthquake)* | **Body Blow**: Slam never misses. *(Slam)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 9 | 44 | **Aftershock**: Earthquake has a 30% chance to make the target flinch. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* |
| 10 | 50 | **Stone Edge**: The user's Rock moves have +30% critical-hit chance on a target below half HP. *(Rock)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Shell Wall**: Harden works on the whole party. *(Harden)* |
| 11 | 60 | **Rock Storm** *(needs 4)*: Rock Slide hits every enemy, the others at 60% damage. *(**own**)* | **Coil Crush** *(needs 4)*: Wrap and Bind catch every enemy. *(Bind)* | **Bulwark Stance** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 12 | 75 | **Magnitude 10** *(needs 6)*: Earthquake hits every enemy at full damage. *(**own**)* | **Constrictor** *(needs 6)*: Wrap's and Bind's grip hurts far more: a further 1/8 of max HP each round. *(**own**)* | **Living Mountain** *(needs 6)*: The first hit the user takes in each battle deals no damage, and while it stands the whole party takes 25% less damage. *(**own**)* |

### Dratini → Dragonair → Dragonite

Moves: Wrap, Leer, Thunder Wave 10, Dragon Rage 18, Agility 24, Slam 30, Body Slam 36 (Dragonair), Wing Attack 40 (Dragonite), Hyper Beam 50 (Dragonair).

Paths: **Serpent** (wrap, Leer and Thunder Wave: binding and stopping enemies); **Dragon** (dragon Rage and raw power); **Sky** (agility and wings: speed, and Dragonite's might).

| Tier | Lv | Serpent | Dragon | Sky |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Chain Lightning**: Thunder Wave works on every enemy, each at half the chance (one alone: the full chance). *(Thunder Wave)* | **Dragon Pulse**: Dragon Rage deals 60 damage (not 40). *(**own**)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 3 | 14 | **Menacing Leer**: Leer works on every enemy. *(Leer)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 4 | 18 | **Constrictor**: Wrap's and Bind's grip hurts far more: a further 1/8 of max HP each round. *(**own**)* | **Body Blow**: Slam never misses. *(Slam)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* |
| 5 | 22 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Gale Wings**: Wing Attack always goes first. *(Wing Attack)* |
| 6 | 27 | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* | **Outrage**: Dragon Rage hits every enemy. *(**own**)* | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* |
| 7 | 32 | **Strangler Fig**: Enemies caught in a bind take 50% more damage from the user. *(**own**)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* | **Multiscale**: The first hit the user takes in each battle deals half damage. *(**own**)* |
| 8 | 38 | **Crushing Coils**: Wrap and Bind have a 30% chance to paralyze. *(Bind)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Aerial Ace**: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* |
| 9 | 44 | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Dragon Dance**: Agility also raises the user's Attack 1 stage. *(**own**)* |
| 10 | 50 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 11 | 60 | **Dragon Coil** *(needs 4)*: Wrap hits every enemy. *(**own**)* | **Draco Meteor** *(needs 4)*: Hyper Beam becomes a Dragon move. *(**own**)* | **Dragon Wings** *(needs 4)*: Wing Attack hits harder: 70 power, and hits every enemy, the others at 50% damage. *(**own**)* |
| 12 | 75 | **Thunder Cloud** *(needs 6)*: At the start of each battle, each enemy has a 30% chance to be paralyzed. *(**own**)* | **Dragon Rush** *(needs 6)*: Each Normal or Dragon move in a row deals 30% more than the last, up to +90%. *(**own**)* | **Sky Sovereign** *(needs 6)*: Wing Attack and Hyper Beam deal 30% more. *(**own**)* |

### Aerodactyl

Moves: Wing Attack, Agility, Supersonic 33, Bite 38, Take Down 45, Rock Slide 48, Hyper Beam 54.

Paths: **Fossil** (rock Slide and ancient rock); **Raptor** (bite and Take Down: a predator's strikes); **Skies** (wings and speed).

| Tier | Lv | Fossil | Raptor | Skies |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Stone Fist**: The basic attack becomes a Rock move (with STAB). *(Rock)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 3 | 14 | **Rolling Stones**: Each Rock move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Rock)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* |
| 4 | 18 | **Sharp Rocks**: The user's Rock moves are 4× as likely to be critical hits. *(Rock)* | **Pounce**: Bite always goes first, and makes the target flinch 50% of the time. *(**own**)* | **Gale Wings**: Wing Attack always goes first. *(Wing Attack)* |
| 5 | 22 | **Jagged Hide**: Whoever hits the user loses 1/16 of its max HP. *(Rock)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* |
| 6 | 27 | **Rockfall**: The user's Rock moves have a 30% chance to make the target flinch. *(Rock)* | **Extreme Speed**: Take Down always goes first. *(**own**)* | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* |
| 7 | 32 | **Landslide**: Below 1/3 HP, the user's Rock moves deal 1.5× damage. *(Rock)* | **Stalker**: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* | **Aerial Ace**: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* |
| 8 | 38 | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* | **Night Feeder**: The user heals 15% of the damage it deals. *(**own**)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 9 | 44 | **Stone Edge**: The user's Rock moves have +30% critical-hit chance on a target below half HP. *(Rock)* | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* |
| 10 | 50 | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Ancient Power** *(needs 4)*: Rock Slide hits every enemy at full damage. *(**own**)* | **Primeval Jaws** *(needs 4)*: Bite hits much harder: 100 power, making the target flinch 30% of the time. *(**own**)* | **Sky Terror** *(needs 4)*: Wing Attack hits every enemy at full damage. *(**own**)* |
| 12 | 75 | **Unstoppable** *(needs 6)*: Each Normal or Rock move in a row deals 30% more than the last, up to +90%. *(**own**)* | **Sniper** *(needs 6)*: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Prehistoric Roar** *(needs 6)*: At the start of each battle, each enemy's Attack and Speed have a 50% chance to fall 1 stage. *(**own**)* |

### Magikarp → Gyarados

Moves: Tackle, Splash, Bite 20 (Gyarados), Dragon Rage 25 (Gyarados), Leer 32 (Gyarados), Hydro Pump 41 (Gyarados), Hyper Beam 52 (Gyarados).

Paths: **Flop** (splash and Tackle: Magikarp never gives up); **Rage** (bite, Dragon Rage and Gyarados's fury); **Torrent** (hydro Pump: Water damage).

| Tier | Lv | Flop | Rage | Torrent |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* |
| 2 | 10 | **Charge**: Tackle hits harder: 50 power. *(Tackle)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Splash Strike**: The basic attack becomes a Water move (with STAB). *(Water)* |
| 3 | 14 | **Bounce**: Splash raises the user's Attack and Speed 1 stage. *(**own**)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* |
| 4 | 18 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Dragon Pulse**: Dragon Rage deals 60 damage (not 40). *(**own**)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* |
| 5 | 22 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* |
| 6 | 27 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Pounce**: Bite always goes first, and makes the target flinch 50% of the time. *(**own**)* | **Geyser**: Hydro Pump hits every enemy, the others at 50% damage. *(Hydro Pump)* |
| 7 | 32 | **Flail**: Below 1/3 HP, the user's Normal moves deal 2× damage. *(**own**)* | **Outrage**: Dragon Rage hits every enemy. *(**own**)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* |
| 8 | 38 | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Hydro Cannon**: Hydro Pump never misses. *(Hydro Pump)* |
| 9 | 44 | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Splash Zone**: The user's Water moves also hit one enemy next to the target, at half damage. *(Water)* |
| 10 | 50 | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Tidal Force**: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* |
| 11 | 60 | **Never Give Up** *(needs 4)*: Once a battle, ending a round below 1/3 HP heals the user half its max HP, and Splash heals it 1/4 of its max HP. *(**own**)* | **Raging Storm** *(needs 4)*: Each Normal or Water move in a row deals 25% more than the last, up to +75%. *(**own**)* | **Aqua Rage** *(needs 4)*: Hydro Pump never misses, and hits 20% harder. *(**own**)* |
| 12 | 75 | **Shining Scales** *(needs 6)*: The first hit the user takes in each battle deals no damage, and while it stands the whole party takes 15% less damage. *(**own**)* | **Giga Impact** *(needs 6)*: Hyper Beam hits harder (180 power), and needs no rest after knocking an enemy out. *(**own**)* | **Tsunami** *(needs 6)*: Hydro Pump hits every enemy at full damage. *(Hydro Pump)* |

### Lapras

Moves: Water Gun, Growl, Sing 16, Body Slam 25, Confuse Ray 31, Ice Beam 38, Hydro Pump 46, Blizzard 52.

Paths: **Ferry** (sing and a gentle heart: carrying the whole party); **Glacier** (ice Beam and Blizzard: freezing); **Tide** (water Gun and Hydro Pump: Water damage).

| Tier | Lv | Ferry | Glacier | Tide |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Frostbite**: The user's Ice moves are 10% more likely to freeze. *(Ice)* | **Torrent**: Below 1/3 HP, the user's Water moves deal 1.5× damage. *(Water)* |
| 2 | 10 | **Sweet Voice**: Sing is 25% more likely to work. *(Sing)* | **Chill**: The user's Ice moves have a 30% chance to lower the target's Speed 1 stage. *(Ice)* | **Pressure Jet**: Water Gun hits harder: 60 power. *(Water Gun)* |
| 3 | 14 | **Echoing Growl**: Growl works on every enemy. *(Growl)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Rain Dish**: Knocking an enemy out with a Water move heals the user 1/4 of its max HP. *(Water)* |
| 4 | 18 | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(Any)* | **Frost Ray**: Ice Beam hits every enemy, the others at 50% damage. *(Ice Beam)* | **Hydration**: At the end of each round, the user has a 30% chance to wash off its status. *(Water)* |
| 5 | 22 | **Chorus**: Sing works on every enemy, each at half the chance (one alone: the full chance). *(Sing)* | **Shatter**: Frozen enemies take 50% more damage from the user. *(Freeze)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 6 | 27 | **Shell Armor**: Super-effective hits on the user deal 30% less damage. *(**own**)* | **Freeze-Dry**: Ice Beam freezes 30% of the time. *(**own**)* | **Geyser**: Hydro Pump hits every enemy, the others at 50% damage. *(Hydro Pump)* |
| 7 | 32 | **Siren Song**: Sing never misses. *(Sing)* | **Whiteout**: Blizzard never misses and hits every enemy, the others at 60% damage. *(Blizzard)* | **Rising Tide**: Each Water move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Water)* |
| 8 | 38 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Absolute Zero**: At the start of each battle, each enemy has a 20% chance to be frozen. *(Freeze)* | **Hydro Cannon**: Hydro Pump never misses. *(Hydro Pump)* |
| 9 | 44 | **Wish**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* | **Wide Ray**: Confuse Ray works on every enemy. *(Confuse Ray)* | **Undertow**: The user's Water moves have a 20% chance to lower the target's Speed 1 stage. *(Water)* |
| 10 | 50 | **Soothing Song**: Sing also cures the party's status conditions. *(Sing)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Tidal Force**: The user's Water moves have +30% critical-hit chance on a target below half HP. *(Water)* |
| 11 | 60 | **Gentle Ferry** *(needs 4)*: While the user stands, the whole party takes 20% less damage. *(**own**)* | **Sheer Cold** *(needs 4)*: Blizzard hits every enemy at full damage, and freezes 20% of the time. *(**own**)* | **Tsunami** *(needs 4)*: Hydro Pump hits every enemy at full damage. *(Hydro Pump)* |
| 12 | 75 | **Song of the Sea** *(needs 6)*: While the user stands, the whole party heals 1/12 of its max HP at the end of each round. *(**own**)* | **Ice Age** *(needs 6)*: Frozen enemies take 80% more damage from the user. *(**own**)* | **Surf** *(needs 6)*: Water Gun hits much harder: 95 power, and hits every enemy at full damage. *(**own**)* |

### Gastly → Haunter → Gengar

Moves: Lick, Confuse Ray, Night Shade, Hypnosis 27, Psychic 35 (Gengar), Thunderbolt 40 (Gengar).

Paths: **Haunt** (confuse Ray and Lick: tormenting minds); **Dream** (hypnosis and sleep: nightmares); **Curse** (psychic and Thunderbolt: Gengar's raw power).

| Tier | Lv | Haunt | Dream | Curse |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Mesmerize**: Hypnosis is 25% more likely to work. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 2 | 10 | **Wide Ray**: Confuse Ray works on every enemy. *(Confuse Ray)* | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* | **Telepathy**: The user's Psychic moves never miss. *(Psychic)* |
| 3 | 14 | **Shadow Lick**: Lick hits harder: 50 power, and paralyzes 40% of the time. *(**own**)* | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Focus Mind**: Each Psychic move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Psychic)* |
| 4 | 18 | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* | **Lull**: Sleeping enemies take 30% more damage from the user. *(Sleep)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 5 | 22 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Mass Hypnosis**: Hypnosis works on every enemy, each at half the chance (one alone: the full chance). *(**own**)* | **Mind Over Matter**: Below 1/3 HP, the user's Psychic moves deal 1.5× damage. *(Psychic)* |
| 6 | 27 | **Bedlam**: Enemies the user confuses always hurt themselves. *(Confusion)* | **Yawn**: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* |
| 7 | 32 | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* | **Pendulum**: Hypnosis never misses. *(**own**)* | **High Voltage**: Thunderbolt is 4× as likely to be a critical hit. *(Thunderbolt)* |
| 8 | 38 | **Cursed Body**: Whoever hits the user loses 1/12 of its max HP. *(**own**)* | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Mind Blast**: Psychic hits every enemy, the others at 50% damage. *(Psychic)* |
| 9 | 44 | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Endless Dream**: Enemies the user puts to sleep sleep 1 more round (on top of Deep Sleep's). *(Sleep)* | **Mind Feast**: Knocking an enemy out with a Psychic move heals the user 1/4 of its max HP. *(Psychic)* |
| 10 | 50 | **Magic Guard**: The user takes no damage from poison, burns, seeds, binds, wounds or nightmares. *(Psychic)* | **Bedtime Story**: At the start of each battle, each enemy has a 15% chance to fall asleep. *(Sleep)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 11 | 60 | **Shadow Reach** *(needs 4)*: Night Shade hits every enemy. *(**own**)* | **Drowsy Jab** *(needs 4)*: After Hypnosis, the user also hits the target with its basic attack, at full power. *(**own**)* | **Psychic Storm** *(needs 4)*: Psychic hits every enemy, the others at 80% damage. *(**own**)* |
| 12 | 75 | **Shadow Ball** *(needs 6)*: Lick hits much harder: 90 power, and confuses 30% of the time. *(**own**)* | **Dreamland** *(needs 6)*: Hypnosis also exposes its target: it takes 30% more damage from everyone, for 3 rounds. *(**own**)* | **Mind Storm** *(needs 6)*: Psychic hits every enemy at full damage. *(**own**)* |

### Cubone → Marowak

Moves: Bone Club, Growl, Leer 25, Focus Energy 31, Thrash 38, Bonemerang 43.

Paths: **Bone** (bone Club and Bonemerang: Ground damage); **Grief** (thrash and a lonely rage); **Guard** (growl and Leer: a little one standing its ground).

| Tier | Lv | Bone | Grief | Guard |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Mud Claws**: The basic attack becomes a Ground move (with STAB). *(Ground)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Tremor**: Each Ground move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Ground)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Echoing Growl**: Growl works on every enemy. *(Growl)* |
| 3 | 14 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Battle Focus**: Focus Energy also makes the user's next damaging move deal 50% more. *(**own**)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 4 | 18 | **Thick Club**: Bone Club and Bonemerang deal 30% more. *(**own**)* | **Cool Head**: Thrash confuses the user only half the time. *(**own**)* | **Skull Helm**: Super-effective hits on the user deal 40% less damage. *(**own**)* |
| 5 | 22 | **Groundswell**: Below 1/3 HP, the user's Ground moves deal 1.5× damage. *(Ground)* | **Mother's Memory**: Below 1/3 HP, the user's Ground and Normal moves deal 1.5× damage. *(**own**)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 6 | 27 | **Burrow Feast**: Knocking an enemy out with a Ground move heals the user 1/4 of its max HP. *(Ground)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 7 | 32 | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* | **Bulk Up**: Focus Energy also raises the user's Attack and Defense 1 stage. *(**own**)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 8 | 38 | **Sand Force**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Ground)* | **Rampaging Fists**: Thrash hits every enemy, the others at 50% damage. *(**own**)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 9 | 44 | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Pick a Fight**: Leer works on every enemy, and makes them all attack the user, this round and the next. *(**own**)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* |
| 11 | 60 | **Bone Zone** *(needs 4)*: Bonemerang hits every enemy. *(**own**)* | **Primal Rage** *(needs 4)*: Thrash deals 50% more and no longer confuses the user. *(**own**)* | **Bone Shield** *(needs 4)*: While the user stands, the whole party takes 20% less damage. *(**own**)* |
| 12 | 75 | **Bone Rush** *(needs 6)*: Bone Club hits every enemy at full damage, and makes them flinch 30% of the time. *(**own**)* | **Guardian Spirit** *(needs 6)*: The first hit the user takes in each battle deals no damage, and a hit that would knock it out has a 30% chance to leave it 1 HP. *(**own**)* | **Immovable** *(needs 6)*: The first hit the user takes in each battle deals no damage, and super-effective hits deal half. *(**own**)* |

### Hitmonlee

Moves: Double Kick, Meditate, Rolling Kick 33, Jump Kick 38, Focus Energy 43, Hi Jump Kick 48, Mega Kick 53.

Paths: **Kicks** (kicks of every kind: Fighting damage); **Focus** (meditate and Focus Energy: one perfect strike); **Limber** (reach and speed: legs that stretch).

| Tier | Lv | Kicks | Focus | Limber |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Combo**: Each Fighting move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Fighting)* | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Rapid Kicks**: Each of Double Kick's hits has a 30% chance to make the target flinch. *(Double Kick)* | **Mind Over Body**: Meditate raises the user's Attack 1 stage more (2 in all). *(**own**)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 3 | 14 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Battle Focus**: Focus Energy also makes the user's next damaging move deal 50% more. *(**own**)* | **Limber**: At the end of each round, the user has a 40% chance to shake off its status. *(**own**)* |
| 4 | 18 | **Stagger**: The user's Fighting moves have a 30% chance to lower the target's Defense 1 stage. *(Fighting)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Long Reach**: The user's Fighting moves also hit an enemy next to the target, at 50% damage. *(**own**)* |
| 5 | 22 | **Pressure Points**: The user's Fighting moves are 4× as likely to be critical hits. *(Fighting)* | **Bulk Up**: Focus Energy also raises the user's Attack and Defense 1 stage. *(**own**)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 6 | 27 | **Rolling Sweep**: Rolling Kick hits every enemy, the others at 60% damage. *(**own**)* | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Last Stand**: Below 1/3 HP, the user's Fighting moves deal 1.5× damage. *(Fighting)* | **Stalker**: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Victory Rush**: Knocking an enemy out with a Fighting move heals the user 1/4 of its max HP. *(Fighting)* | **Shared Focus**: Focus Energy works on the whole party. *(Focus Energy)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 9 | 44 | **Reckless**: Jump Kick and Hi Jump Kick never miss. *(**own**)* | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 11 | 60 | **Hi Jump Mastery** *(needs 4)*: Hi Jump Kick hits much harder: 120 power. *(**own**)* | **Inner Focus** *(needs 4)*: +20% chance of critical hits. *(**own**)* | **Triple Kick** *(needs 4)*: Double Kick hits 3 times. *(**own**)* |
| 12 | 75 | **Kickmaster** *(needs 6)*: Mega Kick becomes a Fighting move (with STAB) and never misses. *(**own**)* | **One-Inch Kick** *(needs 6)*: The user's critical hits deal 2.5× damage (not 1.5×). *(**own**)* | **Whirlwind Kick** *(needs 6)*: Double Kick hits every enemy. *(**own**)* |

### Hitmonchan

Moves: Comet Punch, Agility, Fire Punch 38, Ice Punch 43, Thunder Punch 48, Mega Punch 53, Submission 58.

Paths: **Elements** (fire, Ice and Thunder Punch: an answer for everyone); **Boxer** (comet Punch, Mega Punch and Submission); **Footwork** (agility: dodging and countering).

| Tier | Lv | Elements | Boxer | Footwork |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Searing**: The user's Fire moves are 20% more likely to burn. *(Fire)* | **Fighting Spirit**: The basic attack becomes a Fighting move (with STAB). *(Fighting)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* | **Combo**: Each Fighting move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Fighting)* | **Tailwind**: Agility works on the whole party. *(Agility)* |
| 3 | 14 | **Frostbite**: The user's Ice moves are 10% more likely to freeze. *(Ice)* | **Iron Fist**: Comet Punch, Mega Punch and Dizzy Punch deal 20% more. *(**own**)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 4 | 18 | **Elemental Fists**: Fire, Ice and Thunder Punch are 20% more likely to burn, freeze and paralyze. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* |
| 5 | 22 | **Scorch**: Burned enemies take 25% more damage from the user. *(Fire)* | **Pressure Points**: The user's Fighting moves are 4× as likely to be critical hits. *(Fighting)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 6 | 27 | **Shatter**: Frozen enemies take 50% more damage from the user. *(Freeze)* | **Sucker Punch**: Mega Punch always goes first. *(**own**)* | **Counter Stance**: Whoever hits the user loses 1/8 of its max HP. *(**own**)* |
| 7 | 32 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Stagger**: The user's Fighting moves have a 30% chance to lower the target's Defense 1 stage. *(Fighting)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 8 | 38 | **Chill**: The user's Ice moves have a 30% chance to lower the target's Speed 1 stage. *(Ice)* | **Close Combat**: Submission hits much harder: 120 power. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 9 | 44 | **Elemental Barrage**: Fire, Ice and Thunder Punch hit harder: 90 power. *(**own**)* | **Submission Hold**: Submission no longer hurts the user. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Last Stand**: Below 1/3 HP, the user's Fighting moves deal 1.5× damage. *(Fighting)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Elemental Storm** *(needs 4)*: Fire, Ice and Thunder Punch hit every enemy, the others at 50% damage. *(**own**)* | **Comet Barrage** *(needs 4)*: Comet Punch hits 3-5 times. *(**own**)* | **Stalker** *(needs 4)*: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* |
| 12 | 75 | **Plasma Fists** *(needs 6)*: Fire, Ice and Thunder Punch never miss and are twice as likely to be critical hits. *(**own**)* | **Knockout Blow** *(needs 6)*: Mega Punch hits much harder: 120 power, and never misses. *(**own**)* | **Dodge and Weave** *(needs 6)*: The first hit the user takes in each battle deals no damage, and it has a 50% chance each round to act before the others. *(**own**)* |

### Mr. Mime

Moves: Confusion, Barrier, Light Screen 23, Double Slap 31, Reflect 35, Meditate 39, Psychic 47.

Paths: **Mime** (barrier, Light Screen and Reflect: walls nobody can see); **Psychic** (confusion and Psychic); **Prankster** (double Slap and tricks).

| Tier | Lv | Mime | Psychic | Prankster |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Telepathy**: The user's Psychic moves never miss. *(Psychic)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Invisible Wall**: Barrier raises the user's Defense 1 stage more (3 in all). *(**own**)* | **Dizzying Mind**: Confusion is 20% more likely to confuse. *(Confusion)* | **Flurry Slap**: Double Slap always hits at least 3 times. *(Double Slap)* |
| 3 | 14 | **Barrier**: Reflect covers the whole party. *(Reflect)* | **Focus Mind**: Each Psychic move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Psychic)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* |
| 4 | 18 | **Screen Wall**: Light Screen covers the whole party. *(**own**)* | **Psychic Wings**: Confusion and Psybeam are 20% more likely to confuse. *(Confusion)* | **Pummel**: Double Slap always hits 5 times. *(Double Slap)* |
| 5 | 22 | **Filter**: Super-effective hits on the user deal 40% less damage. *(**own**)* | **Mind Over Matter**: Below 1/3 HP, the user's Psychic moves deal 1.5× damage. *(Psychic)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 6 | 27 | **Barrier Reef**: Barrier works on the whole party. *(**own**)* | **Psychic Surge**: Confusion hits every enemy at full damage, and confuses half the time. *(**own**)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* |
| 7 | 32 | **Mirror Shards**: For 3 rounds, whoever hits a Pokémon behind Reflect loses 1/16 of its max HP. *(Reflect)* | **Mind Blast**: Psychic hits every enemy, the others at 50% damage. *(Psychic)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 8 | 38 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Mind Feast**: Knocking an enemy out with a Psychic move heals the user 1/4 of its max HP. *(Psychic)* | **Bedlam**: Enemies the user confuses always hurt themselves. *(Confusion)* |
| 9 | 44 | **Quick Screen**: Light Screen and Reflect always go first. *(**own**)* | **Precognition**: Psychic always goes first. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 10 | 50 | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* | **Magic Guard**: The user takes no damage from poison, burns, seeds, binds, wounds or nightmares. *(Psychic)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* |
| 11 | 60 | **Wall Mime** *(needs 4)*: Light Screen lasts 2 rounds longer. *(**own**)* | **Psychic Storm** *(needs 4)*: Psychic hits every enemy, the others at 80% damage. *(**own**)* | **Prank** *(needs 4)*: The user's status moves always go first. *(**own**)* |
| 12 | 75 | **Grand Illusion** *(needs 6)*: While the user stands, the whole party takes 30% less damage. *(**own**)* | **Mind Storm** *(needs 6)*: Psychic hits every enemy at full damage. *(**own**)* | **Mime's Encore** *(needs 6)*: Meditate raises the Attack of the user's whole party. *(**own**)* |

### Snorlax

Moves: Headbutt, Defense Curl, Rest, Body Slam 35, Harden 41, Double-Edge 48, Hyper Beam 56.

Paths: **Slumber** (resting, healing, and shrugging things off); **Heavyweight** (throwing its weight around: Normal damage); **Bulwark** (a wall the whole party hides behind).

| Tier | Lv | Slumber | Heavyweight | Bulwark |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Belly Bump**: Headbutt hits harder: 85 power, with a 40% chance to make the target flinch. *(**own**)* | **Curl Up**: Defense Curl also halves the damage the user takes for 2 rounds. *(Defense Curl)* |
| 3 | 14 | **Light Sleep**: Rest makes the user sleep 1 round instead of 2. *(Rest)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* |
| 4 | 18 | **Snooze**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Lazy Lure**: Defense Curl also makes every enemy attack the user, this round and the next. *(**own**)* |
| 5 | 22 | **Midnight Snack**: Rest also raises the user's Attack and Defense 1 stage. *(**own**)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 6 | 27 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Crushing Weight**: Body Slam hits harder: 100 power. *(**own**)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 7 | 32 | **Big Belly**: Once a battle, ending a round below 1/3 HP heals the user half its max HP. *(**own**)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 8 | 38 | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(Any)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Shell Wall**: Harden works on the whole party. *(Harden)* |
| 9 | 44 | **Deep Hibernation**: The user heals 1/8 of its max HP at the end of each round. *(**own**)* | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* |
| 10 | 50 | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 11 | 60 | **Bottomless Stomach** *(needs 4)*: Rest also cures the status conditions of the user's whole party. *(**own**)* | **Body Press** *(needs 4)*: Body Slam hits every enemy, at 75% damage each. *(**own**)* | **Immovable** *(needs 4)*: The first hit the user takes in each battle deals no damage, and super-effective hits deal half. *(**own**)* |
| 12 | 75 | **Sleeping Giant** *(needs 6)*: The first hit the user takes in each battle deals no damage, and it heals 1/8 of its max HP at the end of each round. *(**own**)* | **Giga Impact** *(needs 6)*: Hyper Beam hits harder (180 power), and needs no rest after knocking an enemy out. *(**own**)* | **Living Wall** *(needs 6)*: The first hit the user takes in each battle deals no damage, and while it stands the whole party takes 30% less damage. *(**own**)* |

### Chansey

Moves: Pound, Double Slap, Sing 24, Growl 30, Softboiled 34, Defense Curl 38, Light Screen 44, Seismic Toss 46, Egg Bomb 48, Double-Edge 54.

Paths: **Nurse** (softboiled and healing: keeping everyone standing); **Lucky** (egg Bomb and Double Slap: lucky hits); **Lullaby** (sing and Light Screen: soothing and shielding).

| Tier | Lv | Nurse | Lucky | Lullaby |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Sweet Voice**: Sing is 25% more likely to work. *(Sing)* |
| 2 | 10 | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(Any)* | **Heavy Hand**: Pound hits harder: 60 power. *(Pound)* | **Echoing Growl**: Growl works on every enemy. *(Growl)* |
| 3 | 14 | **Curl Up**: Defense Curl also halves the damage the user takes for 2 rounds. *(Defense Curl)* | **Flurry Slap**: Double Slap always hits at least 3 times. *(Double Slap)* | **Soothing Song**: Sing also cures the party's status conditions. *(Sing)* |
| 4 | 18 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Pummel**: Double Slap always hits 5 times. *(Double Slap)* | **Screen Wall**: Light Screen covers the whole party. *(**own**)* |
| 5 | 22 | **Natural Remedy**: Softboiled also cures the status conditions of the user's whole party. *(**own**)* | **Lucky Egg**: Egg Bomb never misses. *(**own**)* | **Chorus**: Sing works on every enemy, each at half the chance (one alone: the full chance). *(Sing)* |
| 6 | 27 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* |
| 7 | 32 | **Soft Body**: Once a battle, ending a round below 1/3 HP heals the user half its max HP. *(**own**)* | **Vital Throw**: Seismic Toss always goes first. *(**own**)* | **Siren Song**: Sing never misses. *(Sing)* |
| 8 | 38 | **Healing Egg**: Softboiled heals the user's whole party. *(**own**)* | **Seismic Slam**: Seismic Toss hits every enemy, at full damage. *(**own**)* | **Lull**: Sleeping enemies take 30% more damage from the user. *(Sleep)* |
| 9 | 44 | **Wish**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* | **Egg Barrage**: Egg Bomb hits every enemy, the others at 60% damage. *(**own**)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 10 | 50 | **Queen's Guard**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it 1/4 of its max HP. *(**own**)* | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Bedtime Story**: At the start of each battle, each enemy has a 15% chance to fall asleep. *(Sleep)* |
| 11 | 60 | **Full Moon** *(needs 4)*: While the user stands, the whole party takes 25% less damage. *(**own**)* | **Lucky Punch** *(needs 4)*: +30% chance of critical hits. *(**own**)* | **Yawn** *(needs 4)*: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* |
| 12 | 75 | **Blissful** *(needs 6)*: While the user stands, the whole party heals 1/8 of its max HP at the end of each round. *(**own**)* | **Golden Egg** *(needs 6)*: Egg Bomb hits every enemy at full damage, and never misses. *(**own**)* | **Dream Eater** *(needs 6)*: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* |

### Scyther

Moves: Quick Attack, Leer 17, Focus Energy 20, Slash 24, Swords Dance 29, Agility 36, Wing Attack 42.

Paths: **Blades** (slash and Swords Dance: critical cuts); **Swift** (quick Attack and Agility: striking first); **Hunter** (wings, and a hunter's instinct).

| Tier | Lv | Blades | Swift | Hunter |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* |
| 2 | 10 | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 3 | 14 | **Keen Focus**: Focus Energy also raises the user's Attack 1 stage. *(Focus Energy)* | **Tailwind**: Agility works on the whole party. *(Agility)* | **Gale Wings**: Wing Attack always goes first. *(Wing Attack)* |
| 4 | 18 | **Blade Dance**: Swords Dance also makes the user's next damaging move deal 50% more. *(Swords Dance)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* | **Hive Mind**: Each Bug move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Bug)* |
| 5 | 22 | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Afterimage**: Agility also makes the user's next damaging move deal 50% more. *(Agility)* | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* |
| 6 | 27 | **Battle Focus**: Focus Energy also makes the user's next damaging move deal 50% more. *(**own**)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Aerial Ace**: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* |
| 7 | 32 | **Crush Claw**: Slash has a 30% chance to lower the target's Defense 1 stage. *(Slash)* | **Lightning Speed**: Quick Attack hits 3 times, at 70% power each. *(Quick Attack)* | **Feeding Frenzy**: Knocking an enemy out with a Bug move heals the user 1/4 of its max HP. *(Bug)* |
| 8 | 38 | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* |
| 9 | 44 | **Rending Claws**: Slash and Fury Swipes wound the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Stalker**: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 11 | 60 | **Thousand Cuts** *(needs 4)*: Fury Swipes and Slash hit every enemy, the others at 60% damage. *(**own**)* | **Fury Cutter** *(needs 4)*: Quick Attack hits 2 times. *(**own**)* | **Pick a Fight** *(needs 4)*: Leer works on every enemy, and makes them all attack the user, this round and the next. *(**own**)* |
| 12 | 75 | **X-Scissor** *(needs 6)*: Slash hits much harder: 100 power, and is twice as likely to be a critical hit. *(**own**)* | **Mantis Speed** *(needs 6)*: The user has a 60% chance each round to act before the others, and +10% chance of critical hits. *(**own**)* | **Air Slash** *(needs 6)*: Wing Attack hits harder: 75 power, and hits every enemy, the others at 60% damage. *(**own**)* |

### Kangaskhan

Moves: Comet Punch, Bite 26, Tail Whip 31, Mega Punch 36, Leer 41, Dizzy Punch 46.

Paths: **Parent** (a parent's guard over the whole party); **Brawler** (comet Punch and Mega Punch: a flurry of fists); **Pouch** (bite, Tail Whip and Dizzy Punch: the little one's tricks).

| Tier | Lv | Parent | Brawler | Pouch |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Fighting Spirit**: The basic attack becomes a Fighting move (with STAB). *(Fighting)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* |
| 3 | 14 | **Den Mother**: While the user stands, the whole party takes 15% less damage. *(**own**)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 4 | 18 | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* | **Iron Fist**: Comet Punch, Mega Punch and Dizzy Punch deal 20% more. *(**own**)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* |
| 5 | 22 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Dizzy Spin**: Dizzy Punch confuses 50% of the time. *(**own**)* |
| 6 | 27 | **Nurturing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(Any)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Pounce**: Bite always goes first, and makes the target flinch 50% of the time. *(**own**)* |
| 7 | 32 | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* |
| 8 | 38 | **Queen's Guard**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it 1/4 of its max HP. *(**own**)* | **Mother's Wrath**: Below 1/3 HP, the user's Normal moves deal 2× damage. *(**own**)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* |
| 9 | 44 | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 10 | 50 | **Wish**: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Bedlam**: Enemies the user confuses always hurt themselves. *(Confusion)* |
| 11 | 60 | **Full Moon** *(needs 4)*: While the user stands, the whole party takes 25% less damage. *(**own**)* | **Comet Barrage** *(needs 4)*: Comet Punch hits 3-5 times. *(**own**)* | **Pick a Fight** *(needs 4)*: Leer works on every enemy, and makes them all attack the user, this round and the next. *(**own**)* |
| 12 | 75 | **Living Wall** *(needs 6)*: The first hit the user takes in each battle deals no damage, and while it stands the whole party takes 30% less damage. *(**own**)* | **Parental Bond** *(needs 6)*: Mega Punch hits twice. *(**own**)* | **Mind Crush** *(needs 6)*: Confused enemies take 30% more damage from the user. *(Confusion)* |

### Tauros

Moves: Tackle, Stomp 21, Tail Whip 28, Body Slam 35, Take Down 44, Hyper Beam 51.

Paths: **Stampede** (take Down and Stomp: charging through); **Bull** (fury and momentum: Normal damage); **Hide** (a tough hide).

| Tier | Lv | Stampede | Bull | Hide |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Charge**: Tackle hits harder: 50 power. *(Tackle)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 3 | 14 | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* | **Wagging Tail**: Tail Whip works on every enemy. *(Tail Whip)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* |
| 4 | 18 | **Extreme Speed**: Take Down always goes first. *(**own**)* | **Crushing Weight**: Body Slam hits harder: 100 power. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Stampede**: Stomp hits every enemy at full damage. *(**own**)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 6 | 27 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 7 | 32 | **Horn Charge**: Take Down hits harder: 120 power. *(**own**)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 8 | 38 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Anger Point**: Below 1/3 HP, the user's Normal moves deal 2× damage, and it acts first 50% of the time. *(**own**)* | **Shell Armor**: Super-effective hits on the user deal 30% less damage. *(**own**)* |
| 9 | 44 | **Stalker**: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* | **Overdrive**: Hyper Beam needs no rest after knocking an enemy out. *(Hyper Beam)* | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Unstoppable**: Each Normal or Rock move in a row deals 30% more than the last, up to +90%. *(**own**)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Juggernaut** *(needs 4)*: The first hit the user takes in each battle deals no damage, and its Normal moves never miss. *(**own**)* | **Body Press** *(needs 4)*: Body Slam hits every enemy, at 75% damage each. *(**own**)* | **Guardian** *(needs 4)*: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 12 | 75 | **Raging Bull** *(needs 6)*: Take Down hits every enemy at full damage. *(**own**)* | **Giga Impact** *(needs 6)*: Hyper Beam hits harder (180 power), and needs no rest after knocking an enemy out. *(**own**)* | **Immovable** *(needs 6)*: The first hit the user takes in each battle deals no damage, and super-effective hits deal half. *(**own**)* |

### Rhyhorn → Rhydon

Moves: Horn Attack, Stomp 30, Tail Whip 35, Fury Attack 40, Rock Slide 44, Take Down 48 (Rhydon), Earthquake 50 (Rhydon).

Paths: **Drill** (horn Attack and Fury Attack: a drilling horn); **Quake** (earthquake and Rock Slide); **Armor** (rock-hard armor).

| Tier | Lv | Drill | Quake | Armor |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Gore**: Horn Attack has a high critical-hit ratio. *(Horn Attack)* | **Mud Claws**: The basic attack becomes a Ground move (with STAB). *(Ground)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Piercing Horn**: Horn Attack also hits one enemy next to the target, at half damage. *(Horn Attack)* | **Tremor**: Each Ground move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Ground)* | **Jagged Hide**: Whoever hits the user loses 1/16 of its max HP. *(Rock)* |
| 3 | 14 | **Frenzy**: Fury Attack always hits at least 3 times. *(Fury Attack)* | **Rolling Stones**: Each Rock move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Rock)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 4 | 18 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Groundswell**: Below 1/3 HP, the user's Ground moves deal 1.5× damage. *(Ground)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 5 | 22 | **Drill Horn**: Horn Attack always goes first and never misses. *(**own**)* | **Sand Force**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Ground)* | **Tail Slap**: After Tail Whip, the user hits the target with its basic attack at 60% power. *(Tail Whip)* |
| 6 | 27 | **Megahorn**: Horn Attack hits much harder: 100 power. *(Horn Attack)* | **Rockfall**: The user's Rock moves have a 30% chance to make the target flinch. *(Rock)* | **Shell Armor**: Super-effective hits on the user deal 30% less damage. *(**own**)* |
| 7 | 32 | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Burrow Feast**: Knocking an enemy out with a Ground move heals the user 1/4 of its max HP. *(Ground)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 8 | 38 | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* | **Stampede**: Stomp hits every enemy at full damage. *(**own**)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 9 | 44 | **Extreme Speed**: Take Down always goes first. *(**own**)* | **Ancient Power**: Rock Slide hits every enemy at full damage. *(**own**)* | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Fault Line**: Earthquake hits every enemy, the others at 60% damage. *(Earthquake)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Rock Drill** *(needs 4)*: Horn Attack becomes a Rock move (with STAB) and hits harder: 90 power. *(**own**)* | **Magnitude 10** *(needs 4)*: Earthquake hits every enemy at full damage. *(**own**)* | **Juggernaut** *(needs 4)*: The first hit the user takes in each battle deals no damage, and its Normal moves never miss. *(**own**)* |
| 12 | 75 | **Unstoppable** *(needs 6)*: Each Normal or Rock move in a row deals 30% more than the last, up to +90%. *(**own**)* | **Tectonic Rage** *(needs 6)*: Earthquake hits harder: 130 power. *(**own**)* | **Rock Armor** *(needs 6)*: The first hit the user takes in each battle deals no damage, and whoever hits the user loses 1/8 of its max HP. *(**own**)* |

### Exeggcute → Exeggutor

Moves: Confusion, Hypnosis, Reflect 25, Leech Seed 28, Stomp 28 (Exeggutor), Stun Spore 32, Egg Bomb 35 (Exeggutor), Psychic 40 (Exeggutor), Solar Beam 45, Sleep Powder 48.

Paths: **Mind** (confusion and Psychic); **Grove** (leech Seed, Egg Bomb and Solar Beam); **Slumber** (hypnosis and powders: sleep and paralysis).

| Tier | Lv | Mind | Grove | Slumber |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Telepathy**: The user's Psychic moves never miss. *(Psychic)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* | **Mesmerize**: Hypnosis is 25% more likely to work. *(**own**)* |
| 2 | 10 | **Dizzying Mind**: Confusion is 20% more likely to confuse. *(Confusion)* | **Creeping Seed**: When a seeded enemy faints, its seed jumps to an enemy next to it. *(Leech Seed)* | **Numbing Cloud**: Stun Spore works on every enemy, each at half the chance (one alone: the full chance). *(Stun Spore)* |
| 3 | 14 | **Focus Mind**: Each Psychic move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Psychic)* | **Photosynthesis**: The user heals 1/16 of its max HP at the end of each round. *(Grass)* | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* |
| 4 | 18 | **Psychic Wings**: Confusion and Psybeam are 20% more likely to confuse. *(Confusion)* | **Harvest**: Knocking an enemy out with a Grass move heals the user 1/4 of its max HP. *(Grass)* | **Mass Hypnosis**: Hypnosis works on every enemy, each at half the chance (one alone: the full chance). *(**own**)* |
| 5 | 22 | **Barrier**: Reflect covers the whole party. *(Reflect)* | **Seed Bomb**: Leech Seed also deals damage (Grass, 30 power) when it lands. *(Leech Seed)* | **Scale Dust**: Stun Spore, Poison Powder and Sleep Powder never miss and work 25% more often. *(Stun Spore)* |
| 6 | 27 | **Mind Over Matter**: Below 1/3 HP, the user's Psychic moves deal 1.5× damage. *(Psychic)* | **Lucky Egg**: Egg Bomb never misses. *(**own**)* | **Drowsy Dust**: Sleep Powder works on every enemy, each at half the chance (one alone: the full chance). *(Sleep Powder)* |
| 7 | 32 | **Psychic Surge**: Confusion hits every enemy at full damage, and confuses half the time. *(**own**)* | **Egg Barrage**: Egg Bomb hits every enemy, the others at 60% damage. *(**own**)* | **Pendulum**: Hypnosis never misses. *(**own**)* |
| 8 | 38 | **Mind Blast**: Psychic hits every enemy, the others at 50% damage. *(Psychic)* | **Stampede**: Stomp hits every enemy at full damage. *(**own**)* | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* |
| 9 | 44 | **Mind Feast**: Knocking an enemy out with a Psychic move heals the user 1/4 of its max HP. *(Psychic)* | **Solar Flare**: Solar Beam hits every enemy, at full power. *(Solar Beam)* | **Endless Dream**: Enemies the user puts to sleep sleep 1 more round (on top of Deep Sleep's). *(Sleep)* |
| 10 | 50 | **Mirror Shards**: For 3 rounds, whoever hits a Pokémon behind Reflect loses 1/16 of its max HP. *(Reflect)* | **Ancient Roots**: While the user stands, the whole party takes 15% less damage. *(**own**)* | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* |
| 11 | 60 | **Psychic Storm** *(needs 4)*: Psychic hits every enemy, the others at 80% damage. *(**own**)* | **Harvest Sun** *(needs 4)*: Solar Beam needs no charging. *(**own**)* | **Yawn** *(needs 4)*: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* |
| 12 | 75 | **Mind Storm** *(needs 6)*: Psychic hits every enemy at full damage. *(**own**)* | **Tropical Canopy** *(needs 6)*: While the user stands, the whole party takes 20% less damage and heals 1/16 of its max HP at the end of each round. *(**own**)* | **Dreamland** *(needs 6)*: Hypnosis also exposes its target: it takes 30% more damage from everyone, for 3 rounds. *(**own**)* |

### Jynx

Moves: Pound, Lovely Kiss, Ice Punch 31, Double Slap 39, Psychic 44, Body Slam 47, Blizzard 55.

Paths: **Kiss** (lovely Kiss: sleep, and what comes with it); **Frost** (ice Punch and Blizzard); **Dance** (psychic and Double Slap: a strange dance).

| Tier | Lv | Kiss | Frost | Dance |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* | **Frostbite**: The user's Ice moves are 10% more likely to freeze. *(Ice)* | **Telepathy**: The user's Psychic moves never miss. *(Psychic)* |
| 2 | 10 | **Perfect Kiss**: Lovely Kiss never misses, and works 20% more often. *(**own**)* | **Chill**: The user's Ice moves have a 30% chance to lower the target's Speed 1 stage. *(Ice)* | **Flurry Slap**: Double Slap always hits at least 3 times. *(Double Slap)* |
| 3 | 14 | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Focus Mind**: Each Psychic move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Psychic)* |
| 4 | 18 | **Lull**: Sleeping enemies take 30% more damage from the user. *(Sleep)* | **Ice Body**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* | **Mind Blast**: Psychic hits every enemy, the others at 50% damage. *(Psychic)* |
| 5 | 22 | **Sweet Kiss**: Lovely Kiss works on every enemy, each at half the chance (one alone: the full chance). *(**own**)* | **Shatter**: Frozen enemies take 50% more damage from the user. *(Freeze)* | **Mind Over Matter**: Below 1/3 HP, the user's Psychic moves deal 1.5× damage. *(Psychic)* |
| 6 | 27 | **Yawn**: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* | **Whiteout**: Blizzard never misses and hits every enemy, the others at 60% damage. *(Blizzard)* | **Pummel**: Double Slap always hits 5 times. *(Double Slap)* |
| 7 | 32 | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Absolute Zero**: At the start of each battle, each enemy has a 20% chance to be frozen. *(Freeze)* | **Precognition**: Psychic always goes first. *(**own**)* |
| 8 | 38 | **Endless Dream**: Enemies the user puts to sleep sleep 1 more round (on top of Deep Sleep's). *(Sleep)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Mind Feast**: Knocking an enemy out with a Psychic move heals the user 1/4 of its max HP. *(Psychic)* |
| 9 | 44 | **Bedtime Story**: At the start of each battle, each enemy has a 15% chance to fall asleep. *(Sleep)* | **Ice Age**: Frozen enemies take 80% more damage from the user. *(**own**)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 10 | 50 | **Magic Guard**: The user takes no damage from poison, burns, seeds, binds, wounds or nightmares. *(Psychic)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 11 | 60 | **Kiss of Death** *(needs 4)*: Sleeping enemies take 60% more damage from the user. *(**own**)* | **Sheer Cold** *(needs 4)*: Blizzard hits every enemy at full damage, and freezes 20% of the time. *(**own**)* | **Psychic Storm** *(needs 4)*: Psychic hits every enemy, the others at 80% damage. *(**own**)* |
| 12 | 75 | **Eternal Slumber** *(needs 6)*: Enemies the user puts to sleep sleep 2 rounds longer. *(**own**)* | **Frost Queen** *(needs 6)*: Ice Punch hits every enemy at full damage, and freezes 20% of the time. *(**own**)* | **Mind Storm** *(needs 6)*: Psychic hits every enemy at full damage. *(**own**)* |

### Electabuzz

Moves: Quick Attack, Thunder Shock, Leer 34, Screech 37, Thunder Punch 42, Light Screen 49, Thunder 54.

Paths: **Spark** (paralysis: slowing and stopping enemies); **Storm** (thunder: raw Electric damage); **Brawl** (thunder Punch and Quick Attack).

| Tier | Lv | Spark | Storm | Brawl |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Static**: Whoever hits the user has a 25% chance to be paralyzed. *(Electric)* | **Surge**: Below 1/3 HP, the user's Electric moves deal 1.5× damage. *(Electric)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Live Wire**: The user's Electric moves are 20% more likely to paralyze. *(Electric)* | **Charge Up**: Each Electric move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Electric)* | **Lightning Reflexes**: Quick Attack has a 30% chance to make the target flinch. *(Quick Attack)* |
| 3 | 14 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Overcharge**: Thunder Shock hits much harder: 80 power. *(**own**)* | **Fighting Spirit**: The basic attack becomes a Fighting move (with STAB). *(Fighting)* |
| 4 | 18 | **Screen Wall**: Light Screen covers the whole party. *(**own**)* | **Discharge**: Knocking an enemy out with a Electric move heals the user 1/4 of its max HP. *(Electric)* | **Hit and Run**: Quick Attack also raises the user's Speed 1 stage. *(Quick Attack)* |
| 5 | 22 | **Piercing Screech**: Screech works on every enemy. *(Screech)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Elemental Fists**: Fire, Ice and Thunder Punch are 20% more likely to burn, freeze and paralyze. *(**own**)* |
| 6 | 27 | **Thunder Cloud**: At the start of each battle, each enemy has a 30% chance to be paralyzed. *(**own**)* | **Thunderclap**: Thunder always goes first. *(**own**)* | **Lightning Speed**: Quick Attack hits 3 times, at 70% power each. *(Quick Attack)* |
| 7 | 32 | **Menacing Leer**: Leer works on every enemy. *(Leer)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 8 | 38 | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Combo**: Each Fighting move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Fighting)* |
| 9 | 44 | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 10 | 50 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Static Field** *(needs 4)*: Whoever hits the user has a 50% chance to be paralyzed. *(**own**)* | **Gigavolt** *(needs 4)*: Thunder hits every enemy, at full damage. *(**own**)* | **Thunder Fist** *(needs 4)*: Thunder Punch hits harder: 100 power, and paralyzes 30% of the time. *(**own**)* |
| 12 | 75 | **Plasma Storm** *(needs 6)*: At the start of each battle, each enemy has a 50% chance to be paralyzed. *(**own**)* | **Thunder God** *(needs 6)*: Thunderbolt and Thunder never miss, and have +30% critical-hit chance on a target below half HP. *(**own**)* | **Electric Rush** *(needs 6)*: Thunder Punch hits every enemy at full damage. *(**own**)* |

### Magmar

Moves: Ember, Leer 36, Confuse Ray 39, Fire Punch 43, Smog 48, Flamethrower 55.

Paths: **Flame** (ember, Fire Punch and Flamethrower: Fire damage); **Smoke** (smog and Confuse Ray: smoke and fumes); **Inferno** (burns, and their torment).

| Tier | Lv | Flame | Smoke | Inferno |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Blaze**: Below 1/3 HP, the user's Fire moves deal 1.5× damage. *(Fire)* | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Searing**: The user's Fire moves are 20% more likely to burn. *(Fire)* |
| 2 | 10 | **Ember Shower**: Ember hits every enemy, the others at 50% damage. *(Ember)* | **Wide Ray**: Confuse Ray works on every enemy. *(Confuse Ray)* | **Smoulder**: The user's Fire moves wound the target: 1/16 of its max HP each round, for 3 rounds. *(Fire)* |
| 3 | 14 | **Stoke the Flames**: Each Fire move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Fire)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Scorch**: Burned enemies take 25% more damage from the user. *(Fire)* |
| 4 | 18 | **Fireball**: Ember hits harder: 60 power. *(Ember)* | **Smog Cloud**: Smog hits every enemy. *(**own**)* | **Heat Haze**: At the start of each battle, each enemy has a 30% chance to be burned. *(Fire)* |
| 5 | 22 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Ash Cloud**: The user's Fire moves have a 20% chance to lower the target's accuracy 1 stage. *(Fire)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 6 | 27 | **Scorching Breath**: Flamethrower is 20% more likely to burn. *(Flamethrower)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* | **Wildfire**: Burns the user inflicts have a 30% chance each round to spread to an enemy next to it. *(Fire)* |
| 7 | 32 | **Feed the Flames**: Knocking an enemy out with a Fire move heals the user 1/4 of its max HP. *(Fire)* | **Toxic Smog**: Smog badly poisons: it gets worse every round. *(**own**)* | **Pyre**: Enemies the user's side burned lose a further 1/8 of their max HP each round. *(**own**)* |
| 8 | 38 | **Blowtorch**: Flamethrower also hits one enemy next to the target, at half damage. *(Flamethrower)* | **Bedlam**: Enemies the user confuses always hurt themselves. *(Confusion)* | **Flame Body**: Whoever hits the user has a 30% chance to be burned. *(**own**)* |
| 9 | 44 | **Elemental Fists**: Fire, Ice and Thunder Punch are 20% more likely to burn, freeze and paralyze. *(**own**)* | **Phantom Ink**: Enemies with lowered accuracy take 50% more damage from the user's party. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Heat Wave** *(needs 4)*: Flamethrower hits every enemy, the others at 60% damage. *(**own**)* | **Smoke Bomb** *(needs 4)*: At the start of each battle, each enemy's accuracy has a 50% chance to fall 1 stage. *(**own**)* | **Magma Armor** *(needs 4)*: The first hit the user takes in each battle deals no damage, and whoever hits the user has a 50% chance to be burned. *(**own**)* |
| 12 | 75 | **Inferno Fist** *(needs 6)*: Fire Punch hits every enemy at full damage, and burns 30% of the time. *(**own**)* | **Thick Fog** *(needs 6)*: At the start of each battle, each enemy's accuracy has a 50% chance to fall 2 stages. *(**own**)* | **Eruption** *(needs 6)*: Burned enemies take 60% more damage from the user. *(**own**)* |

### Tangela

Moves: Constrict, Bind, Absorb 29, Poison Powder 32, Stun Spore 36, Sleep Powder 39, Slam 45, Growth 49.

Paths: **Vines** (bind and Constrict: tangling enemies); **Powder** (powders on every enemy); **Growth** (absorb and Growth: feeding and growing).

| Tier | Lv | Vines | Powder | Growth |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* |
| 2 | 10 | **Toxic Tentacles**: Constrict has a 30% chance to poison. *(**own**)* | **Pollen Cloud**: Poison Powder hits every enemy, each at half the chance (one alone: the full chance). *(Poison Powder)* | **Root Drink**: Absorb hits harder: 40 power. *(Absorb)* |
| 3 | 14 | **Crushing Coils**: Wrap and Bind have a 30% chance to paralyze. *(Bind)* | **Numbing Cloud**: Stun Spore works on every enemy, each at half the chance (one alone: the full chance). *(Stun Spore)* | **Photosynthesis**: The user heals 1/16 of its max HP at the end of each round. *(Grass)* |
| 4 | 18 | **Constrictor**: Wrap's and Bind's grip hurts far more: a further 1/8 of max HP each round. *(**own**)* | **Drowsy Dust**: Sleep Powder works on every enemy, each at half the chance (one alone: the full chance). *(Sleep Powder)* | **Sap**: Absorb heals the user all the damage it deals (not half). *(Absorb)* |
| 5 | 22 | **Strangler Fig**: Enemies caught in a bind take 50% more damage from the user. *(**own**)* | **Toxic Spores**: Poison Powder badly poisons: it gets worse every round. *(Poison Powder)* | **Full Bloom**: Growth also makes the user's next damaging move deal 50% more. *(Growth)* |
| 6 | 27 | **Constrict**: Wrap and Bind squeeze twice as hard: 1/8 of max HP each round. *(Bind)* | **Scale Dust**: Stun Spore, Poison Powder and Sleep Powder never miss and work 25% more often. *(Stun Spore)* | **Harvest**: Knocking an enemy out with a Grass move heals the user 1/4 of its max HP. *(Grass)* |
| 7 | 32 | **Body Blow**: Slam never misses. *(Slam)* | **Soothing Spores**: Sleep Powder also cures the party's status conditions. *(Sleep Powder)* | **Shared Sun**: Growth works on the whole party. *(Growth)* |
| 8 | 38 | **Riptide**: Enemies with lowered Speed take 30% more damage from the user's party. *(**own**)* | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 9 | 44 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Vine Snare** *(needs 4)*: Bind hits every enemy. *(**own**)* | **Spore Burst** *(needs 4)*: At the start of each battle, each enemy has a 15% chance to fall asleep. *(**own**)* | **Giga Drain** *(needs 4)*: Absorb hits much harder: 75 power. *(**own**)* |
| 12 | 75 | **Power Whip** *(needs 6)*: Slam hits much harder: 120 power, and never misses. *(**own**)* | **Toxic Bloom** *(needs 6)*: At the start of each battle, each enemy has a 30% chance to be poisoned, and 30% to be paralyzed. *(**own**)* | **Overgrowth** *(needs 6)*: The user heals 1/8 of its max HP at the end of each round. *(**own**)* |

### Pinsir

Moves: Vice Grip, Seismic Toss 25, Harden 30, Slash 36, Swords Dance 49, Submission 52.

Paths: **Pincers** (vice Grip and Slash: crushing horns); **Throw** (seismic Toss and Submission); **Shell** (harden: a hard shell).

| Tier | Lv | Pincers | Throw | Shell |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Fighting Spirit**: The basic attack becomes a Fighting move (with STAB). *(Fighting)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Hyper Cutter**: Vice Grip is twice as likely to be a critical hit. *(**own**)* | **Vital Throw**: Seismic Toss always goes first. *(**own**)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* |
| 3 | 14 | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Combo**: Each Fighting move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Fighting)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 4 | 18 | **Blade Dance**: Swords Dance also makes the user's next damaging move deal 50% more. *(Swords Dance)* | **Submission Hold**: Submission no longer hurts the user. *(**own**)* | **Shell Wall**: Harden works on the whole party. *(Harden)* |
| 5 | 22 | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* | **Last Stand**: Below 1/3 HP, the user's Fighting moves deal 1.5× damage. *(Fighting)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 6 | 27 | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Atomic Drop**: Seismic Toss always goes first and never misses. *(**own**)* | **Jagged Hide**: Whoever hits the user loses 1/16 of its max HP. *(Rock)* |
| 7 | 32 | **Hive Mind**: Each Bug move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Bug)* | **Victory Rush**: Knocking an enemy out with a Fighting move heals the user 1/4 of its max HP. *(Fighting)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 8 | 38 | **Crush Claw**: Slash has a 30% chance to lower the target's Defense 1 stage. *(Slash)* | **Close Combat**: Submission hits much harder: 120 power. *(**own**)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 9 | 44 | **Sniper**: The user's critical hits deal double damage (not 1.5×). *(**own**)* | **Stagger**: The user's Fighting moves have a 30% chance to lower the target's Defense 1 stage. *(Fighting)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* |
| 11 | 60 | **X-Scissor** *(needs 4)*: Slash hits much harder: 100 power, and is twice as likely to be a critical hit. *(**own**)* | **Seismic Slam** *(needs 4)*: Seismic Toss hits every enemy, at full damage. *(**own**)* | **Juggernaut** *(needs 4)*: The first hit the user takes in each battle deals no damage, and its Normal moves never miss. *(**own**)* |
| 12 | 75 | **Guillotine** *(needs 6)*: Vice Grip hits much harder: 110 power, and is three times as likely to be a critical hit. *(**own**)* | **Storm Throw** *(needs 6)*: Submission hits every enemy, the others at 50% damage. *(**own**)* | **Immovable** *(needs 6)*: The first hit the user takes in each battle deals no damage, and super-effective hits deal half. *(**own**)* |

### Drowzee → Hypno

Moves: Pound, Hypnosis, Confusion 17, Headbutt 24, Poison Gas 29, Psychic 32, Meditate 37, Psybeam 40 (Hypno).

Paths: **Dream** (hypnosis and sleep: putting enemies to sleep and making them pay); **Mind** (confusion, Headbutt and Psychic: Psychic damage); **Haze** (poison Gas and confusion: wearing enemies down, and staying up).

| Tier | Lv | Dream | Mind | Haze |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Mesmerize**: Hypnosis is 25% more likely to work. *(**own**)* | **Telepathy**: The user's Psychic moves never miss. *(Psychic)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* | **Dizzying Mind**: Confusion is 20% more likely to confuse. *(Confusion)* | **Noxious Cloud**: Poison Gas works on every enemy. *(**own**)* |
| 3 | 14 | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Focus Mind**: Each Psychic move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Psychic)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 4 | 18 | **Mass Hypnosis**: Hypnosis works on every enemy, each at half the chance (one alone: the full chance). *(**own**)* | **Mind Over Matter**: Below 1/3 HP, the user's Psychic moves deal 1.5× damage. *(Psychic)* | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* |
| 5 | 22 | **Lull**: Sleeping enemies take 30% more damage from the user. *(Sleep)* | **Psychic Wings**: Confusion and Psybeam are 20% more likely to confuse. *(Confusion)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* |
| 6 | 27 | **Yawn**: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* | **Thick Skull**: Headbutt hits harder: 85 power, with a 40% chance to make the target flinch. *(**own**)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* |
| 7 | 32 | **Pendulum**: Hypnosis never misses. *(**own**)* | **Mind Feast**: Knocking an enemy out with a Psychic move heals the user 1/4 of its max HP. *(Psychic)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 8 | 38 | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Psycho Cut**: Psychic is 4× as likely to be a critical hit. *(Psychic)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* |
| 9 | 44 | **Bedtime Story**: At the start of each battle, each enemy has a 15% chance to fall asleep. *(Sleep)* | **Psychic Mastery**: Psybeam hits every enemy, the others at 60% damage. *(Psybeam)* | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* |
| 10 | 50 | **Drowsy Jab**: After Hypnosis, the user also hits the target with its basic attack, at full power. *(**own**)* | **Mind Blast**: Psychic hits every enemy, the others at 50% damage. *(Psychic)* | **Magic Guard**: The user takes no damage from poison, burns, seeds, binds, wounds or nightmares. *(Psychic)* |
| 11 | 60 | **Endless Dream** *(needs 4)*: Enemies the user puts to sleep sleep 1 more round (on top of Deep Sleep's). *(Sleep)* | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Dreamland** *(needs 6)*: Hypnosis also exposes its target: it takes 30% more damage from everyone, for 3 rounds. *(**own**)* | **Psychic Storm** *(needs 6)*: Psychic hits every enemy, the others at 80% damage. *(**own**)* | **Bedlam** *(needs 6)*: Enemies the user confuses always hurt themselves. *(Confusion)* |

### Diglett → Dugtrio

Moves: Scratch, Growl 15, Sand-Attack 24, Slash 31, Dig 35 (Dugtrio), Rock Slide 35 (Dugtrio), Earthquake 40 (Dugtrio).

Paths: **Burrow** (popping up first, and striking before anyone else); **Claw** (scratch and Slash, and Ground power); **Sand** (growl and Sand-Attack: blinding and slowing the enemies).

| Tier | Lv | Burrow | Claw | Sand |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Sharp Claws**: Scratch is 4× as likely to be a critical hit. *(Scratch)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 3 | 14 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Mud Claws**: The basic attack becomes a Ground move (with STAB). *(Ground)* | **Sand Veil**: At the start of each battle, each enemy's accuracy has a 50% chance to fall 1 stage. *(Ground)* |
| 4 | 18 | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Groundswell**: Below 1/3 HP, the user's Ground moves deal 1.5× damage. *(Ground)* | **Echoing Growl**: Growl works on every enemy. *(Growl)* |
| 5 | 22 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Tremor**: Each Ground move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Ground)* | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* |
| 6 | 27 | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* | **Sandstorm**: Sand-Attack works on every enemy. *(Sand-Attack)* |
| 7 | 32 | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Blinding Grit**: Sand-Attack lowers accuracy 2 stages. *(Sand-Attack)* |
| 8 | 38 | **Pop Up**: The user's moves deal 35% more to a target that hasn't moved yet this round. *(**own**)* | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Sand Force**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Ground)* |
| 9 | 44 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Crush Claw**: Slash has a 30% chance to lower the target's Defense 1 stage. *(Slash)* | **Kick Up Dust**: After Sand-Attack, the user hits the target with its basic attack at 60% power. *(Sand-Attack)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Burrow Feast**: Knocking an enemy out with a Ground move heals the user 1/4 of its max HP. *(Ground)* | **Dust Devil**: Sand-Attack also makes the target take 20% more damage from everyone, for 3 rounds. *(Sand-Attack)* |
| 11 | 60 | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Rending Claws** *(needs 4)*: Slash and Fury Swipes wound the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Sand Stream** *(needs 4)*: At the start of each battle, every enemy's accuracy falls 2 stages. *(Ground)* |
| 12 | 75 | **Triple Strike** *(needs 6)*: The basic attack hits 3 times, at 50% power each. *(**own**)* | **Dragon Claw** *(needs 6)*: Slash is always a critical hit. *(Slash)* | **Phantom Ink** *(needs 6)*: Enemies with lowered accuracy take 50% more damage from the user's party. *(Any)* |

### Sandshrew → Sandslash

Moves: Scratch, Sand-Attack 10, Slash 17, Poison Sting 24, Swift 31, Dig 35 (Sandslash), Fury Swipes 38, Rock Slide 40 (Sandslash), Earthquake 45 (Sandslash).

Paths: **Sand** (sand-Attack: blinding enemies, and punishing the blind); **Claw** (slash and Fury Swipes: critical hits and wounds); **Burrow** (spines and a hard hide: hard to take down).

| Tier | Lv | Sand | Claw | Burrow |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Sharp Claws**: Scratch is 4× as likely to be a critical hit. *(Scratch)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 2 | 10 | **Sandstorm**: Sand-Attack works on every enemy. *(Sand-Attack)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Spiny Back**: Whoever hits the user loses 1/16 of its max HP. *(**own**)* |
| 3 | 14 | **Blinding Grit**: Sand-Attack lowers accuracy 2 stages. *(Sand-Attack)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 4 | 18 | **Kick Up Dust**: After Sand-Attack, the user hits the target with its basic attack at 60% power. *(Sand-Attack)* | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Sand Veil**: At the start of each battle, each enemy's accuracy has a 50% chance to fall 1 stage. *(Ground)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 6 | 27 | **Dust Devil**: Sand-Attack also makes the target take 20% more damage from everyone, for 3 rounds. *(Sand-Attack)* | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* |
| 7 | 32 | **Sand Force**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Ground)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 8 | 38 | **Star Shower**: Swift hits every enemy, the others at 60% damage. *(Swift)* | **Raking Claws**: Fury Swipes wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Fury Swipes)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 9 | 44 | **Decoy**: Sand-Attack also makes every enemy attack the user, this round and the next. *(Sand-Attack)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Dig In**: Once a battle, ending a round below 1/3 HP heals the user half its max HP. *(**own**)* |
| 10 | 50 | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* | **Frenzy Claws**: Fury Swipes always hits 5 times. *(Fury Swipes)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* |
| 11 | 60 | **Sand Stream** *(needs 4)*: At the start of each battle, every enemy's accuracy falls 2 stages. *(Ground)* | **Crush Claw** *(needs 4)*: Slash has a 30% chance to lower the target's Defense 1 stage. *(Slash)* | **Spiked Armor** *(needs 4)*: Whoever hits the user loses 1/8 of its max HP. *(**own**)* |
| 12 | 75 | **Sandblast** *(needs 6)*: Swift has a 50% chance to lower the target's accuracy 1 stage. *(Swift)* | **Rending Claws** *(needs 6)*: Slash and Fury Swipes wound the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* | **Impregnable** *(needs 6)*: The first hit the user takes in each battle deals no damage, and super-effective hits deal half. *(**own**)* |

### Ekans → Arbok

Moves: Wrap, Leer, Poison Sting 10, Bite 17, Glare 24, Screech 31, Dig 35 (Arbok), Acid 38.

Paths: **Venom** (poison, and making it worse); **Coil** (wrap and Glare: catching and stopping enemies); **Menace** (leer, Screech and Glare: weakening and scaring the enemies).

| Tier | Lv | Venom | Coil | Menace |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Constrict**: Wrap and Bind squeeze twice as hard: 1/8 of max HP each round. *(Bind)* | **Menacing Leer**: Leer works on every enemy. *(Leer)* |
| 2 | 10 | **Barbed Sting**: Poison Sting is 30% more likely to poison. *(Poison Sting)* | **Crushing Coils**: Wrap and Bind have a 30% chance to paralyze. *(Bind)* | **Piercing Gaze**: Leer also makes the target take 25% more damage from everyone, for 3 rounds. *(Leer)* |
| 3 | 14 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Intimidate**: At the start of each battle, each enemy's Attack has a 50% chance to fall 1 stage. *(Any)* |
| 4 | 18 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Squeeze**: Enemies caught in a bind take 30% more damage from the user. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 5 | 22 | **Venom Needle**: Poison Sting wounds the target: 1/16 of its max HP each round, for 3 rounds. *(Poison Sting)* | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 6 | 27 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Evil Eye**: Glare always works (unless the target can't be paralyzed). *(Glare)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 7 | 32 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Piercing Screech**: Screech works on every enemy. *(Screech)* |
| 8 | 38 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* |
| 9 | 44 | **Corrode**: Acid is twice as likely to lower Defense. *(Acid)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Petrify**: Glare works on every enemy. *(Glare)* |
| 10 | 50 | **Toxic Fangs**: Bite has a 30% chance to poison. *(Bite)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* |
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Coil Crush** *(needs 4)*: Wrap and Bind catch every enemy. *(Bind)* | **Unbreakable** *(needs 4)*: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 12 | 75 | **Coil of Venom** *(needs 6)*: Poisoned enemies take 40% more damage from the user. *(**own**)* | **Constrictor** *(needs 6)*: Wrap's and Bind's grip hurts far more: a further 1/8 of max HP each round. *(**own**)* | **Gorgon Gaze** *(needs 6)*: At the start of each battle, each enemy has a 25% chance to be paralyzed. *(**own**)* |

### Jigglypuff → Wigglytuff

Moves: Pound, Sing, Defense Curl 19, Double Slap 24, Rest 29, Body Slam 34, Double-Edge 39.

Paths: **Lullaby** (sing: putting enemies to sleep, and keeping them there); **Puff** (soft and hard to put down: healing and keeping the partner up); **Slap** (pound and Double Slap: a flurry of hits).

| Tier | Lv | Lullaby | Puff | Slap |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Sweet Voice**: Sing is 25% more likely to work. *(Sing)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 2 | 10 | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 3 | 14 | **Chorus**: Sing works on every enemy, each at half the chance (one alone: the full chance). *(Sing)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 4 | 18 | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 5 | 22 | **Lull**: Sleeping enemies take 30% more damage from the user. *(Sleep)* | **Curl Up**: Defense Curl also halves the damage the user takes for 2 rounds. *(Defense Curl)* | **Heavy Hand**: Pound hits harder: 60 power. *(Pound)* |
| 6 | 27 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Flurry Slap**: Double Slap always hits at least 3 times. *(Double Slap)* |
| 7 | 32 | **Yawn**: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* | **Light Sleep**: Rest makes the user sleep 1 round instead of 2. *(Rest)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 8 | 38 | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Heavy Body**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(Body Slam)* |
| 9 | 44 | **Siren Song**: Sing never misses. *(Sing)* | **Sweet Song**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(**own**)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 10 | 50 | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Soothing Song**: Sing also cures the party's status conditions. *(Sing)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 11 | 60 | **Bedtime Story** *(needs 4)*: At the start of each battle, each enemy has a 15% chance to fall asleep. *(Sleep)* | **Plush** *(needs 4)*: While the user stands, the whole party takes 15% less damage. *(**own**)* | **Rampage** *(needs 4)*: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* |
| 12 | 75 | **Endless Dream** *(needs 6)*: Enemies the user puts to sleep sleep 1 more round (on top of Deep Sleep's). *(Sleep)* | **Wish** *(needs 6)*: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* | **Pummel** *(needs 6)*: Double Slap always hits 5 times. *(Double Slap)* |

### Koffing → Weezing

Moves: Tackle, Smog, Sludge 32, Smokescreen 37, Self-Destruct 40, Explosion 48 (Weezing).

Paths: **Fumes** (smog and Sludge: poison on every enemy); **Haze** (smokescreen and fog: blinding enemies, shielding the party); **Volatile** (self-Destruct and Explosion: going out with a bang).

| Tier | Lv | Fumes | Haze | Volatile |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Smoke Cloud**: Smokescreen works on every enemy. *(Smokescreen)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Smog Cloud**: Smog hits every enemy. *(**own**)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Live Bomb**: Self-Destruct deals 50% more. *(**own**)* |
| 3 | 14 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Ink Blind**: Smokescreen lowers accuracy 2 stages. *(Smokescreen)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 4 | 18 | **Toxic Smog**: Smog badly poisons: it gets worse every round. *(**own**)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 5 | 22 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Smoke Bomb**: At the start of each battle, each enemy's accuracy has a 50% chance to fall 1 stage. *(**own**)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 6 | 27 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Blind Spot**: Enemies with lowered accuracy take 20% more damage from the user's party. *(Any)* | **Chain Reaction**: Self-Destruct and Explosion hit every enemy, the others at 50% damage. *(**own**)* |
| 7 | 32 | **Sludge Bomb**: Sludge hits harder: 90 power, and poisons 40% of the time. *(**own**)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 8 | 38 | **Miasma**: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Phantom Ink**: Enemies with lowered accuracy take 50% more damage from the user's party. *(Any)* | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* |
| 9 | 44 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 10 | 50 | **Poison Point**: Whoever hits the user has a 25% chance to be poisoned. *(Poison)* | **Fortress**: While the user stands, the whole party takes 25% less damage. *(Any)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* |
| 11 | 60 | **Toxic Storm** *(needs 4)*: Sludge hits every enemy at full damage. *(**own**)* | **Thick Fog** *(needs 4)*: At the start of each battle, each enemy's accuracy has a 50% chance to fall 2 stages. *(**own**)* | **Big Bang** *(needs 4)*: Explosion hits every enemy at full damage. *(**own**)* |
| 12 | 75 | **Plague Cloud** *(needs 6)*: At the start of each battle, each enemy has a 60% chance to be poisoned. *(**own**)* | **Smog Shroud** *(needs 6)*: While the user stands, the whole party takes 20% less damage. *(**own**)* | **Final Flash** *(needs 6)*: Self-Destruct and Explosion hit harder: 200 and 250 power. *(**own**)* |

### Grimer → Muk

Moves: Pound, Poison Gas 30, Sludge 37, Harden 42, Screech 48.

Paths: **Sludge** (sludge and poison: wearing every enemy down); **Ooze** (a body of muck: shrugging off blows, poisoning attackers); **Grime** (pound and Screech: breaking defenses down).

| Tier | Lv | Sludge | Ooze | Grime |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Toxic Touch**: The basic attack has a 20% chance to poison. *(Poison)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Heavy Hand**: Pound hits harder: 60 power. *(Pound)* |
| 2 | 10 | **Noxious Cloud**: Poison Gas works on every enemy. *(**own**)* | **Iron Shell**: Harden also halves the damage the user takes for 2 rounds. *(Harden)* | **Piercing Screech**: Screech works on every enemy. *(Screech)* |
| 3 | 14 | **Contagion**: Poison the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Poison)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 4 | 18 | **Sticky Sludge**: Sludge has a 50% chance to lower the target's Speed 1 stage. *(**own**)* | **Toxic Body**: Whoever hits the user has a 30% chance to be poisoned. *(**own**)* | **Exploit Weakness**: Enemies with lowered Defense take 30% more damage from the user's party. *(Any)* |
| 5 | 22 | **Siphon**: The user heals half the poison damage of the enemies it poisoned. *(Poison)* | **Shell Wall**: Harden works on the whole party. *(Harden)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 6 | 27 | **Virulent**: The user's poison is bad poison: it gets worse every round. *(Poison)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Shriek**: After Screech, the user hits the target with its basic attack at 60% power. *(Screech)* |
| 7 | 32 | **Sludge Bomb**: Sludge hits harder: 90 power, and poisons 40% of the time. *(**own**)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 8 | 38 | **Sapping**: Poisoned enemies deal 20% less damage. *(Poison)* | **Solid Rock**: Super-effective hits on the user deal 25% less damage. *(Any)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 9 | 44 | **Miasma**: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* | **Rampage**: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* |
| 10 | 50 | **Gunk Feast**: Knocking an enemy out with a Poison move heals the user half its max HP. *(**own**)* | **Unbreakable**: A hit that would knock the user out has a 50% chance to leave it 1 HP. *(Any)* | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 11 | 60 | **Sludge Wave** *(needs 4)*: Sludge hits every enemy, the others at 60% damage. *(**own**)* | **Acid Armor** *(needs 4)*: Harden raises the user's Defense 2 stages more (3 in all). *(**own**)* | **Sludge Fist** *(needs 4)*: The basic attack becomes a Poison move (with STAB), with a 30% chance to poison. *(**own**)* |
| 12 | 75 | **Plague Cloud** *(needs 6)*: At the start of each battle, each enemy has a 60% chance to be poisoned. *(**own**)* | **Muck Mountain** *(needs 6)*: The first hit the user takes in each battle deals no damage, and whoever hits the user has a 30% chance to be poisoned. *(**own**)* | **Putrid Rot** *(needs 6)*: Poisoned enemies take 40% more damage from the user. *(**own**)* |

### Zubat → Golbat

Moves: Leech Life, Supersonic 10, Bite 15, Confuse Ray 21, Wing Attack 28, Swift 32, Double-Edge 38 (Golbat).

Paths: **Fang** (leech Life and Bite: feeding on enemies); **Echo** (supersonic and Confuse Ray: muddling every enemy); **Wing** (speed, and Wing Attack).

| Tier | Lv | Fang | Echo | Wing |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Bloodsucker**: Leech Life heals the user all the damage it deals (not half). *(Leech Life)* | **Echolocation**: The user's damaging moves never miss. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* |
| 2 | 10 | **Vampire Fangs**: Leech Life hits harder: 40 power. *(Leech Life)* | **Echo**: Supersonic works on every enemy, each at half the chance (one alone: the full chance). *(Supersonic)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 3 | 14 | **Feeding Frenzy**: Knocking an enemy out with a Bug move heals the user 1/4 of its max HP. *(Bug)* | **Mind Games**: Enemies the user confuses hurt themselves 75% of the time (not 50%). *(Confusion)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Crunch**: Bite has a 30% chance to lower the target's Defense 1 stage. *(Bite)* | **Disorient**: Supersonic is 20% more likely to confuse. *(**own**)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 5 | 22 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Wide Ray**: Confuse Ray works on every enemy. *(Confuse Ray)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 6 | 27 | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* | **Mind Crush**: Confused enemies take 30% more damage from the user. *(Confusion)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 7 | 32 | **Hive Mind**: Each Bug move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Bug)* | **Hysteria**: Confusion the user causes has a 30% chance each round to spread to an enemy next to it. *(Confusion)* | **Riding the Wind**: The user's Flying moves raise its Speed 1 stage. *(Flying)* |
| 8 | 38 | **Lucky Strikes**: +10% chance of critical hits. *(Any)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* | **Gale Wings**: Wing Attack always goes first. *(Wing Attack)* |
| 9 | 44 | **Night Feeder**: The user heals 15% of the damage it deals. *(**own**)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Aerial Ace**: The user's Flying moves never miss and are twice as likely to be critical hits. *(Flying)* |
| 10 | 50 | **Apex Predator**: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Bird of Prey**: Knocking an enemy out with a Flying move heals the user 1/4 of its max HP. *(Flying)* |
| 11 | 60 | **Bat Swarm** *(needs 4)*: Leech Life hits every enemy, the others at 50% damage. *(**own**)* | **Bedlam** *(needs 4)*: Enemies the user confuses always hurt themselves. *(Confusion)* | **Blur** *(needs 4)*: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 12 | 75 | **Blood Feast** *(needs 6)*: The user heals 30% of the damage it deals. *(**own**)* | **Supersonic Wave** *(needs 6)*: Supersonic and Confuse Ray never miss. *(**own**)* | **Night Flight** *(needs 6)*: The user's Flying moves always go first and deal 30% more. *(**own**)* |

### Paras → Parasect

Moves: Scratch, Stun Spore 13, Leech Life 20, Mega Drain 24, Spore 27, Slash 34, Growth 41, Solar Beam 44 (Parasect).

Paths: **Spore** (stun Spore and Spore: status on every enemy); **Mushroom** (leech Life and Mega Drain: draining enemies); **Claw** (scratch and Slash).

| Tier | Lv | Spore | Mushroom | Claw |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Effect Spore**: Whoever hits the user has a 10% chance each to be paralyzed, poisoned or put to sleep. *(**own**)* | **Sprout Strike**: The basic attack becomes a Grass move (with STAB). *(Grass)* | **Sharp Claws**: Scratch is 4× as likely to be a critical hit. *(Scratch)* |
| 2 | 10 | **Spore Claws**: Scratch has a 20% chance to poison. *(**own**)* | **Overgrow**: Below 1/3 HP, the user's Grass moves deal 1.5× damage. *(Grass)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 3 | 14 | **Numbing Cloud**: Stun Spore works on every enemy, each at half the chance (one alone: the full chance). *(Stun Spore)* | **Swarm**: Below 1/3 HP, the user's Bug moves deal 1.5× damage. *(Bug)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* |
| 4 | 18 | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* | **Ripening**: Each Grass move in a row deals 20% more than the last, up to +60%. Any other move starts it over. *(Grass)* | **Sturdy**: The first hit the user takes in each battle deals 35% less damage. *(Any)* |
| 5 | 22 | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* | **Bloodsucker**: Leech Life heals the user all the damage it deals (not half). *(Leech Life)* | **Tenacity**: A hit that would knock the user out has a 25% chance to leave it 1 HP. *(Any)* |
| 6 | 27 | **Spore Cloud**: Spore works on every enemy, each at half the chance (one alone: the full chance). *(Spore)* | **Gluttony**: Mega Drain heals the user all the damage it deals (not half). *(Mega Drain)* | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* |
| 7 | 32 | **Nightmare**: Enemies the user puts to sleep lose 1/8 of their max HP each round. *(Sleep)* | **Harvest**: Knocking an enemy out with a Grass move heals the user 1/4 of its max HP. *(Grass)* | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* |
| 8 | 38 | **Yawn**: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* | **Feeding Frenzy**: Knocking an enemy out with a Bug move heals the user 1/4 of its max HP. *(Bug)* | **Rend**: Slash wounds the target: 1/12 of its max HP each round, for 3 rounds. *(Slash)* |
| 9 | 44 | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Full Bloom**: Growth also makes the user's next damaging move deal 50% more. *(Growth)* | **Sweeping Claw**: Slash hits every enemy, the others at 50% damage. *(Slash)* |
| 10 | 50 | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* | **Shared Sun**: Growth works on the whole party. *(Growth)* | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 11 | 60 | **Spore Burst** *(needs 4)*: At the start of each battle, each enemy has a 15% chance to fall asleep. *(**own**)* | **Photosynthesis** *(needs 4)*: The user heals 1/16 of its max HP at the end of each round. *(Grass)* | **Apex Predator** *(needs 4)*: The user's moves have +30% critical-hit chance on a target below 1/3 HP. *(Any)* |
| 12 | 75 | **Fungal Bloom** *(needs 6)*: Spore and Stun Spore never miss and work on every enemy. *(**own**)* | **Parasitic** *(needs 6)*: The user heals 30% of the damage it deals. *(**own**)* | **Dragon Claw** *(needs 6)*: Slash is always a critical hit. *(Slash)* |

### Clefairy → Clefable

Moves: Pound, Growl, Sing 13, Double Slap 18, Body Slam 30 (Clefable), Thunder Wave 34, Defense Curl 39, Psychic 40 (Clefable), Rest 44.

Paths: **Moon** (moonlight: healing and keeping the partner up); **Song** (sing: putting enemies to sleep); **Pixie** (pound and Double Slap).

| Tier | Lv | Moon | Song | Pixie |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Moonlight**: The user heals 1/16 of its max HP at the end of each round. *(**own**)* | **Head Start**: The user has a 30% chance each round to act before the others. *(Any)* | **Lucky Strikes**: +10% chance of critical hits. *(Any)* |
| 2 | 10 | **Echoing Growl**: Growl works on every enemy. *(Growl)* | **Cornered**: Below 1/3 HP, the user's Normal moves deal 1.5× damage. *(Normal)* | **Momentum**: Each Normal move in a row deals 15% more than the last, up to +45%. Any other move starts it over. *(Normal)* |
| 3 | 14 | **Guardian**: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* | **Sweet Voice**: Sing is 25% more likely to work. *(Sing)* | **Gang Up**: The user's moves deal 30% more to a target a partner already hit this round. *(Any)* |
| 4 | 18 | **Lunar Blessing**: While the user stands, the whole party heals 1/16 of its max HP at the end of each round. *(**own**)* | **Chorus**: Sing works on every enemy, each at half the chance (one alone: the full chance). *(Sing)* | **Flurry Slap**: Double Slap always hits at least 3 times. *(Double Slap)* |
| 5 | 22 | **Second Wind**: Once a battle, ending a round below 1/3 HP heals the user 1/4 of its max HP. *(Any)* | **Deep Sleep**: Enemies the user puts to sleep sleep 1 round longer. *(Sleep)* | **Heavy Hand**: Pound hits harder: 60 power. *(Pound)* |
| 6 | 27 | **Resilience**: At the end of each round, the user has a 30% chance to shake off its status. *(Any)* | **Lull**: Sleeping enemies take 30% more damage from the user. *(Sleep)* | **Ambush**: The user's moves deal 30% more to a target that hasn't moved yet this round. *(Any)* |
| 7 | 32 | **Taunting Growl**: Growl also makes every enemy attack the user, this round and the next. *(Growl)* | **Yawn**: Sleep the user inflicts has a 30% chance each round to spread to an enemy next to it. *(Sleep)* | **Scavenger**: Knocking an enemy out with a Normal move heals the user 1/4 of its max HP. *(Normal)* |
| 8 | 38 | **Bulwark Stance**: While the user stands, the whole party takes 15% less damage. *(Any)* | **Siren Song**: Sing never misses. *(Sing)* | **Conductor**: Enemies the user paralyzes take 30% more damage from everyone. *(Paralysis)* |
| 9 | 44 | **Soothing Song**: Sing also cures the party's status conditions. *(Sing)* | **Dream Eater**: The user heals 1/8 of its max HP each round for each sleeping enemy. *(Sleep)* | **Rollout**: Defense Curl also makes the user's next damaging move deal 50% more. *(Defense Curl)* |
| 10 | 50 | **Light Sleep**: Rest makes the user sleep 1 round instead of 2. *(Rest)* | **Chain Lightning**: Thunder Wave works on every enemy, each at half the chance (one alone: the full chance). *(Thunder Wave)* | **Blur**: The user's damaging moves go before others' (as Quick Attack does). *(Any)* |
| 11 | 60 | **Wish** *(needs 4)*: Once a battle, a partner that would faint keeps 1 HP, and the user heals it half its max HP. *(Any)* | **Bedtime Story** *(needs 4)*: At the start of each battle, each enemy has a 15% chance to fall asleep. *(Sleep)* | **Rampage** *(needs 4)*: Each Normal move in a row deals 20% more than the last, up to +60%. *(Normal)* |
| 12 | 75 | **Full Moon** *(needs 6)*: While the user stands, the whole party takes 25% less damage. *(**own**)* | **Endless Dream** *(needs 6)*: Enemies the user puts to sleep sleep 1 more round (on top of Deep Sleep's). *(Sleep)* | **Pummel** *(needs 6)*: Double Slap always hits 5 times. *(Double Slap)* |
