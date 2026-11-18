# Talents (draft: the new skill tree)

A design draft, not in the game yet. It replaces the skill trees
(`docs/skill_trees.md`): moves are no longer bought with points, and the
build is a short list of hand-written choices instead of ~100 generic
buffs.

A mock-up of the screen: `talents_mock.png` (Ivysaur Lv23, choosing tier 5).

## Rules

- **Moves are learned by level.** A line learns its Red/Blue level-up
  moves at their Gen 1 levels, on its own. TM moves (Take Down, Leaf
  Shield (Reflect), Body Slam, Double-Edge, Hyper Beam for Bulbasaur) come
  later from quests or drops; until that exists, they open at the levels
  the tree has them at now. 4 equipped, as now.
- **Paths.** Each line has 3 themed paths. Bulbasaur's: **Toxin** (poison,
  seeds, sleep: wearing enemies down), **Bloom** (Grass damage) and
  **Bulwark** (staying up and keeping the partner up).
- **Tiers.** A new tier opens at each tier level (12 tiers by Lv75), and the
  player picks **1 of its 3 talents**: one per path. Paths can be mixed
  freely. The last two tiers' talents also need 4 / 6 earlier picks in
  their own path, which rewards going deep.
- **No ranks, no plain stat bonuses.** Every talent changes how something
  plays.
- **Reset** for free in towns, as now.
- **Old saves:** skill points are gone; members get their level's moves and
  no talents picked (`saves.SKILLS_VERSION`).

Tier levels are dense early, as the game so far runs to about Lv21
(Cerulean): start Lv5, Brock ~Lv15, Ivysaur Lv16, Venusaur Lv32.

## Bulbasaur → Ivysaur → Venusaur

Moves by level: Tackle, Growl (start), Leech Seed 7, Vine Whip 13, Poison
Powder 20, Razor Leaf 27, Growth 34, Sleep Powder 41, Solar Beam 48.

"Code": **have** = the battle code already does this (an existing `Move`
field or buff); **new** = needs new battle code.

| Tier | Lv | Toxin | Bloom | Bulwark |
| --- | --- | --- | --- | --- |
| 1 | 6 | **Bitter Sap**: Tackle has a 20% chance to poison. *(have)* | **Sprout Strike**: Tackle becomes a Grass move (gets STAB). *(have: type change)* | **Sturdy Bulb**: the first hit the user takes in each battle deals half damage. *(new)* |
| 2 | 10 | **Creeping Seed**: when a seeded enemy faints, its seed jumps to an enemy next to it. *(have)* | **Seed Bomb**: Leech Seed also deals damage (30 power, Grass) when it lands. *(have: power)* | **Taunting Growl**: Growl also makes every enemy attack the user this round. *(new)* |
| 3 | 14 | **Thorned Whip**: Vine Whip has a 30% chance to poison. *(have)* | **Double Lash**: Vine Whip hits twice, at 60% power each. *(have)* | **Thirsty Vines**: Vine Whip heals the user half the damage dealt. *(have)* |
| 4 | 18 | **Sapping**: poisoned or seeded enemies deal 20% less damage. *(new)* | **Overgrow**: below ⅓ HP, the user's Grass moves deal 1.5× damage. *(new)* | **Second Wind**: once a battle, ending a round below ⅓ HP heals the user ¼ of its max HP. *(new)* |
| 5 | 22 | **Toxic Spores**: Poison Powder badly poisons (it gets worse every round). *(have)* | **Ripening**: each Grass move in a row deals 20% more than the last, up to +60%. Any other move resets it. *(new)* | **Canopy**: Leaf Shield covers the whole party. *(have)* |
| 6 | 27 | **Pollen Cloud**: Poison Powder hits every enemy. *(have)* | **Keen Edge**: Razor Leaf always crits a target below half HP. *(new)* | **Thornskin**: while Leaf Shield is up, whoever hits the user loses 1/16 of its max HP. *(have: spikes)* |
| 7 | 32 | **Contagion**: each round, an enemy's poison has a 30% chance to spread to an enemy next to it. *(have)* | **Flower Power**: the user's Grass moves also hit one enemy next to the target, at half damage. *(have: reach)* | **Heavy Bulb**: Take Down and Double-Edge have no recoil; Body Slam paralyzes 50% of the time. *(have)* |
| 8 | 38 | **Siphon**: the user heals half the poison damage its enemies take. *(have)* | **Full Bloom**: Growth also makes the user's next damaging move deal 50% more. *(have: empower)* | **Shared Sun**: Growth works on the whole party. *(have: rally)* |
| 9 | 44 | **Nightmare**: enemies the user put to sleep lose 1/8 of their max HP each round. *(have)* | **Harvest**: knocking out an enemy with a Grass move heals the user ¼ of its max HP. *(new)* | **Soothing Spores**: Sleep Powder also cures the party's status conditions. *(new)* |
| 10 | 50 | **Spore Storm**: Razor Leaf has a 25% chance to poison or put to sleep each enemy it hits. *(have: set-off)* | **Sunlit**: once the user has used Growth in a battle, Solar Beam needs no charge. *(new)* | **Photosynthesis**: the user heals 1/16 of its max HP at the end of each round. *(have: regen)* |
| 11 | 60 | **Miasma** *(4 Toxin)*: at the start of each battle, each enemy has a 50% chance to be poisoned. *(new)* | **Solar Flare** *(4 Bloom)*: Solar Beam hits every enemy at full power. *(have: spread)* | **World Tree** *(4 Bulwark)*: once a battle, a partner that would faint keeps 1 HP instead. *(have: endure, for allies)* |
| 12 | 75 | **Venom Garden** *(6 Toxin)*: all poison the user inflicts is bad poison, and Leech Seed poisons too. *(new)* | **Hyper Bloom** *(6 Bloom)*: Hyper Beam is a Grass move and needs no recharge when it knocks an enemy out. *(new)* | **Ancient Roots** *(6 Bulwark)*: while the user stands, the whole party takes 15% less damage. *(new)* |

That's 23 *have* and 13 *new*. The new ones are each small (a check in
one place of `battle.py`), except **Taunting Growl**, which needs enemy
targeting to honour it.

### Builds this allows (examples)

- **Pure Toxin**: poisons with everything, spreads it, heals from it.
  Slow but safe. It plays very differently from Bloom.
- **Bloom with Bulwark**: Sprout Strike, Double Lash, Overgrow, then
  Bulwark picks for staying up.
- **Partner support** (once two fight): Taunting Growl, Canopy, Shared
  Sun, World Tree. Bulbasaur takes the hits and keeps the partner up.

## Open questions

- Tier levels: are 12 tiers up to Lv75 right, or should there be fewer?
- Shared pool: some talents here could be shared by every Grass (or
  Poison) line, e.g. Overgrow, Harvest, Contagion, Siphon, Nightmare. The
  signature talents stay per line.
- Links (one move setting off another) live on only as talents (Spore
  Storm), not as their own kind of skill.
