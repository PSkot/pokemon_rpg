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

- **Paths.** Each line has 3 paths, each a way to play it. Bulbasaur's:
  **Toxin** (poison, seeds and sleep: wearing enemies down), **Bloom**
  (Grass damage) and **Bulwark** (staying up, and keeping the partner up).
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
    Contagion, ...; sleep: Nightmare). Each type's pool is written for
    that type, not one set renamed per type, so types still play
    differently;
  - **move pools**: for lines that learn that move (Growl: Taunting Growl;
    Leech Seed: Creeping Seed, Seed Bomb, ...);
  - **any**: any line can have them (Sturdy, Second Wind, World Tree);
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

- **Move changes** (`Talent.moves`): Move field changes for the basic
  attack, one move, the user's damaging moves of a type
  (`"type:grass"`) or its moves that inflict a status
  (`"status:poison"`), applied in tier order (`talents.apply_changes`:
  numbers add up, chances to at most 100%). So Sprout Strike's Grass
  Tackle also gets Flower Power, and Toxic Touch's poison also gets
  Contagion and Siphon. Changed moves show a "*" on the talent screen.
- **Battle effects** (`Talent.flags`, `Monster.talent(flag)`):
  - damage (`BattleScene._talent_factor`, multiplying the hit):
    **Overgrow** (the user's Grass moves ×1.5 below ⅓ HP), **Ripening**
    (+20% per Grass move used in a row before it, up to +60%; any other
    move starts it over), **Sapping** (a poisoned attacker deals 20% less
    to the holder's side), **Ancient Roots** (the holder's side takes 15%
    less while it stands), **Sturdy** (the holder's first hit taken each
    battle deals half);
  - **Second Wind**: once a battle, ending a round below ⅓ HP heals ¼ of
    max HP. **Photosynthesis**: 1/16 of max HP each round end (with gear
    regen). **Harvest**: knocking an enemy out with a Grass move heals ¼;
  - **World Tree**: once a battle, a partner hit for the last of its HP
    keeps 1 HP;
  - **Miasma**: at the start of each battle, each foe has a 50% chance to
    be poisoned (with the holder's poison move's extras).
- **New move fields** they use (`moves.Move`): `taunt` (Taunting Growl:
  for this round and the next, the foes' single-target moves go to the
  user), `keen` (Keen Edge: always a critical hit on a target below half
  HP), `charge_skip` (Sunlit: Solar Beam needs no charging once Growth was
  used in the battle), `ko_no_recharge` (Hyper Bloom), `soothe`
  (Soothing Spores: cures the user's side's statuses). A damaging move
  with `seed` (Seed Bomb) seeds what it hits; poison from a damaging
  move carries its Contagion/Siphon.

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
| 11 | 60 | **Miasma** *(needs 4)*: At the start of each battle, each enemy has a 50% chance to be poisoned. *(Poison)* | **Solar Flare** *(needs 4)*: Solar Beam hits every enemy, at full power. *(Solar Beam)* | **World Tree** *(needs 4)*: Once a battle, a partner that would faint keeps 1 HP instead. *(Any)* |
| 12 | 75 | **Venom Garden** *(needs 6)*: All poison the user inflicts is bad poison, and Leech Seed poisons too. *(**own**)* | **Hyper Bloom** *(needs 6)*: Hyper Beam is a Grass move and needs no rest after knocking an enemy out. *(**own**)* | **Ancient Roots** *(needs 6)*: While the user stands, the whole party takes 15% less damage. *(**own**)* |
