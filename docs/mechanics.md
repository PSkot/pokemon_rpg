# Game mechanics

How the numbers work: stats, levels and XP, damage, status conditions,
gear rolls, items, loot and money. Keep this file in step with the code: when a
rule or a number changes, update the section here too.

Most rules follow Gen 1 (Red/Blue), simplified, with gear on top. Where
the game deliberately differs from Gen 1, that's called out.

---

## Stats

`game/mechanics/pokemon.py` (`Monster`)

Each species has Gen 1's five base stats: HP, Attack, Defense, Speed and
**Special** (`Species.base_special`). As in Red/Blue, Special is one stat
used both ways: **Fire, Water, Grass, Electric, Ice, Psychic and Dragon
moves** (`combat.SPECIAL_TYPES`) use the user's Special instead of its
Attack and the target's Special instead of its Defense; every other move
(and a typeless one) is physical. So Geodude (Defense 100, Special 30)
shrugs off Tackle but not Water Gun or Ember. No IVs/EVs, no natures.
Its stats at level
`L` are worked out using whole-number division (`//`, rounding down):

| Stat | Formula |
| --- | --- |
| Max HP | `(base_hp × 2 × L // 100 + L + 10) × (100 + L) // 100` |
| Attack, Defense, Speed, Special | `base × 2 × L // 100 + 5` |

Max HP is Gen 1's, × (1 + L/100) (`pokemon.max_hp_at`, `HP_GROWTH`): ×1.1
at Lv10, ×1.3 at Lv30, ×1.5 at Lv50. Damage grows faster than level (new
moves of 90–120 power, gear), so HP grows faster too: a good move takes
about the same share of a same-level foe's HP all game.

Example: Bulbasaur (45 / 49 / 49 / 45, Special 65) at Lv5 has 19 HP,
9 Attack and 11 Special.

### Gear on stats

Gear gives stats a percentage bonus. Bonuses from every equipped piece
(and every roll on a piece) are **added together** before being applied:
two +10% Attack bonuses make +20%, not +21%. They are applied to the
level-based stat like this (`items.boosted`):

```
change = round(stat × percent / 100)
change is at least +1 for a bonus, at most -1 for a penalty
final  = max(1, stat + change)
```

The "at least 1" keeps small bonuses meaningful at low levels. In code,
`Monster.attack` etc. include gear; `Monster.base_attack` etc. don't.
Gear has no Special bonus: its **Attack** bonus also counts when the
Pokémon attacks with a special move (`Monster.special_attack`), its
**Defense** bonus when it's hit by one (`special_defense`).

Changing gear keeps the **damage taken**: a Pokémon at full HP stays at
full HP when its max HP goes up or down.

---

## Levels and XP

`game/mechanics/pokemon.py` (`xp_for_level`, `Monster.xp_yield`),
`game/scenes/battle.py` (`_give_xp`)

- **XP to reach a level:** `L³` total XP (Gen 1's "medium fast" growth
  rate; Lv1 is 0). All species use this curve for now. Lv5 = 125,
  Lv6 = 216, Lv10 = 1000. Max level 100.
- **XP for defeating a Pokémon:** `base_exp × L // 7`, where `base_exp` is
  the species' Gen 1 base experience yield (`Species.base_exp`; e.g.
  Pidgey 55, Bulbasaur 64, Venusaur 208). This is Gen 1's formula for wild
  Pokémon.
- **Wild battles give ×0.15** (`WILD_XP`) and trainer battles ×0.45
  (`TRAINER_XP`): quests are the main source of XP (about ¾ of it; see
  `quests.md` for the budget). (Until the Pewter → Vermilion check they
  were ×0.5 / ×1.5, unsplit: a party that fought everything reached the
  Vermilion Gym around Lv42 instead of 29.)
- **Sharing:** after a won battle, the XP of **all** enemies is added up
  and **split evenly between the party members still standing** (as in
  Gen 1), rounded. Fainted members get nothing. So a bigger party doesn't
  earn more from the same fights (with two fighting, wild groups are
  bigger, which makes up for part of it).
- **Level up:** stats are recalculated at once. Max HP goes up, and the
  HP gained is added to current HP (damage taken stays the same).
  Several level-ups from one battle are possible.

Example: beating wild Lv6 Pidgey (47), Lv7 Rattata (57) and Lv5 Pidgey
(39) gives 143 × 0.15 = 21 XP to a lone starter (11 each to two).

- **Quest XP:** a finished quest gives its XP (`Quest.xp`) to **every**
  party member, fainted ones too (`quests._give_xp`), with the same level
  ups. A Pokémon that reaches its evolution level this way (and whose
  evolution is unlocked) evolves at its next level up in a battle, or
  from the party screen.

---

## Evolution

`game/mechanics/pokemon.py` (`EVOLUTIONS`, `Monster.evolve`),
`game/world/quests.py` (`can_evolve`, `evolve`), `game/scenes/battle.py`
(`_evolve`), `game/scenes/summary.py` (E)

Pokémon evolve at the levels from Red/Blue, but **only once a quest
unlocks the evolution** (see `quests.md`, *Evolution quests*). Without its
quest, a line doesn't evolve, whatever its level (`quests.md` lists the
lines that have one, e.g. Oddish → Gloom and Bellsprout → Weepinbell);
Pokémon already evolved stay as they are. Trade evolutions aren't in yet; stone evolutions are below.

- **First time (the quest):** with the quest's item, a party member of
  that species at or above the evolution level shows "Evolve!" on the
  party screen; **E** there evolves it (the same flashing) and finishes
  the quest.
- **After that (unlocked):** at the end of a won battle, after the XP, for
  each party member that **leveled up in that battle** and is at or above
  its evolution level. Its sprite flashes white between the two forms,
  faster and faster. E on the party screen also works (e.g. a Pokémon
  already past the level).
- **Stopping it:** pressing **X** during the flashing stops the evolution
  (B in Red/Blue). It tries again the next time that Pokémon levels up.
- **What changes:** the species, and with it base stats, types, sprite,
  XP yield, and the moves it now knows (see `talents.md`; the new moves
  are equipped while there's room). The level, XP, talents, gear and
  status stay. Stats are
  recalculated, and the HP gained is added to current HP (damage taken
  stays the same).
- **Only into species that are in the game:** an evolution is skipped
  while its species isn't defined yet (e.g. Rattata won't evolve until
  Raticate is added). The full table is already registered.

The lead Pokémon is also the player character on the map, so evolving it
changes how the player looks.

| Evolves | Into | Level | | Evolves | Into | Level |
| --- | --- | --- | --- | --- | --- | --- |
| Bulbasaur | **Ivysaur** | 16 | | Psyduck | Golduck | 33 |
| Ivysaur | Venusaur | 32 | | Mankey | Primeape | 28 |
| Charmander | Charmeleon | 16 | | Poliwag | Poliwhirl | 25 |
| Charmeleon | Charizard | 36 | | Abra | Kadabra | 16 |
| Squirtle | Wartortle | 16 | | Machop | Machoke | 28 |
| Wartortle | Blastoise | 36 | | Bellsprout | Weepinbell | 21 |
| Caterpie | **Metapod** | 7 | | Tentacool | Tentacruel | 30 |
| Metapod | Butterfree | 10 | | Geodude | Graveler | 25 |
| Weedle | **Kakuna** | 7 | | Ponyta | Rapidash | 40 |
| Kakuna | Beedrill | 10 | | Slowpoke | Slowbro | 37 |
| Pidgey | Pidgeotto | 18 | | Magnemite | Magneton | 30 |
| Pidgeotto | Pidgeot | 36 | | Doduo | Dodrio | 31 |
| Rattata | Raticate | 20 | | Seel | Dewgong | 34 |
| Spearow | Fearow | 20 | | Grimer | Muk | 38 |
| Ekans | Arbok | 22 | | Gastly | Haunter | 25 |
| Sandshrew | Sandslash | 22 | | Drowzee | Hypno | 26 |
| Nidoran♀ | Nidorina | 16 | | Krabby | Kingler | 28 |
| Nidoran♂ | Nidorino | 16 | | Voltorb | Electrode | 30 |
| Zubat | Golbat | 22 | | Cubone | Marowak | 28 |
| Oddish | Gloom | 21 | | Koffing | Weezing | 35 |
| Paras | Parasect | 24 | | Rhyhorn | Rhydon | 42 |
| Venonat | Venomoth | 31 | | Horsea | Seadra | 32 |
| Diglett | Dugtrio | 26 | | Goldeen | Seaking | 33 |
| Meowth | Persian | 28 | | Magikarp | Gyarados | 20 |
| Dratini | Dragonair | 30 | | Omanyte | Omastar | 40 |
| Dragonair | Dragonite | 55 | | Kabuto | Kabutops | 40 |

**Bold** = in the game now.

### Evolution stones

`pokemon.STONE_EVOLUTIONS`, `scenes/bag.py`, `scenes/summary.py` (`stone`)

Stones are **key items**, each from its own quest (`quests.md` → *The
evolution stones*). Bag → Key items → Enter on a stone → pick a party
member: if the stone works on that species, the party screen shows it
evolving (the same flashing), and **the stone is used up**. Any level
will do. A stone has no effect on other species: the bag says which ones
it works on. Only evolutions into species already in the game count.

| Stone | Evolves | Its quest |
| --- | --- | --- |
| Leaf Stone | Gloom → Vileplume, Weepinbell → Victreebel, Exeggcute → Exeggutor | *The Overgrown Wing* |
| Moon Stone | Nidorina → Nidoqueen, Nidorino → Nidoking, Clefairy → Clefable, Jigglypuff → Wigglytuff | *The Moonlit Dance* |
| Thunder Stone | Pikachu → Raichu | *Live Wires* |
| Fire Stone | Growlithe → Arcanine | (later, with Cinnabar) |
| Water Stone | Shellder → Cloyster, Staryu → Starmie | (later, with the coast) |

---

## Damage

`game/mechanics/combat.py` (`damage`), applied in
`game/scenes/battle.py` (`_apply`)

**Misses:** a move hits with its **Gen 1 accuracy** (`Move.accuracy`,
`moves.GEN1_ACCURACY`): Tackle and Razor Leaf 95%; Hyper Fang, Super Fang,
Hyper Beam, Sky Attack, Rock Slide and Blizzard 90%; Take Down, Fury
Attack, Double Slap, Wrap, Pin Missile and Fire Blast 85%; Fury Swipes and
Hydro Pump 80%; Slam, Bind and Clamp 75%; Fire Spin and Thunder 70%; Rock
Throw 65%; of the status moves, Screech, Whirlwind 85%, String Shot 95%,
Kinesis 80%, Leech Seed 90% (the others' chance to work is their status or
confusion chance). Everything else always hits. Lowered **accuracy**
stages multiply that (see *Stat stages*); Swift never misses. One roll
per use (a multi-hit or spread move hits all or nothing). A hit is worked
out in these steps:

1. **Attack:** the user's Attack (with gear) × its **Attack stage**
   multiplier (see *Stat stages*); for a special move (Fire, Water,
   Grass, Electric, Ice, Psychic, Dragon), its Special instead (with
   gear's Attack bonus). Halved if the user is **burned** (physical moves
   only, as in Gen 1).
2. **Power:** the move's power × its `scale` (talents: Double Lash 0.6
   for its two hits). Fight uses the
   Pokémon's basic attack (see `talents.md`).
3. **Base damage** (the Gen 1 formula):

   ```
   base = (2 × L / 5 + 2) × power × attack / defense / 50 + 2
   ```

   `L` is the user's level, `defense` the target's Defense with gear ×
   its **Defense stage** multiplier (a special move: its Special, with
   gear's Defense bonus, × the same stage).
4. **Critical hit** (`combat.crit_chance`): a **5%** chance × the move's
   crit ratio (×3 for Slash, Razor Leaf, Karate Chop and Sky Attack, a
   "high critical-hit ratio": 15%; ×20 or more: always), × 4 with Focus
   Energy, plus the user's gear `crit` (and Lucky Strikes) in percentage
   points (e.g. +3 → 8%), at most 100%. There's no cap: gear's crit is
   small (an all-crit set of top Legendary Lv60 rolls reaches 27%; Slash 37%). Always a crit with Keen Edge on a target below half HP (Apex
   Predator: below ⅓). A crit
   multiplies `base` by **×1.5** (Gen 2+ style; *not* Gen 1's level-based
   crits; ×2 with the Sniper talent).
5. **Leaf Shield:** if the target is shielded, `base` × **0.5**.
6. **Random spread:** `base` × a random number from 0.85 to 1.0, × the
   move's share if it hits several targets (Petal Dance 0.35), except
   for the enemy it was aimed at, which takes full damage.
7. **Type effectiveness:** × the type chart multiplier for the move's type
   against each of the target's types (multiplied together: 0, ¼, ½, 1,
   2 or 4). Typeless moves are always ×1.
8. **Same-type bonus (STAB):** × **1.5** if the move's type is one of the
   user's types.
9. **Type power gear:** × `(1 + power:<type> / 100)` for the move's type
   (e.g. Charcoal, "of the Moltres").
10. The result is rounded, with a minimum of **1**, or **0** if the
    target is immune (×0).

11. **Talents** (`BattleScene._talent_factor`, applied with step 6's
    share): pinch (Overgrow, Cornered, Swarm, Surge: ×1.5 for the user's
    moves of that type below ⅓ HP), streak (Ripening, Momentum, ...: +15–25%
    per move of the type in a row before it, up to 3), Ambush (+30% on a
    target that hasn't moved this round), Gang Up (+30% on a target a
    partner already hit this round), Gale Force (+25% for spread moves),
    prey (+25–50% on a target with a status), spot (+30% on a target with
    a lowered stat), Sapping (×0.8 for a poisoned attacker against a
    Sapping Pokémon's side), Ancient Roots and its copies (×0.85 on its
    side), Sturdy (×0.5 on its first hit taken in a battle; Juggernaut
    ×0), Solid Rock (×0.75 for super-effective hits on it), Squeeze (+30%
    on a bound target). See `talents.md`.

Steps 7–9 all multiply together; their order doesn't matter.

**Total damage** is capped at the target's remaining HP. (Gear used to add
flat move power, extra type damage and a super-effective bonus; the gear
rework of `GEAR_VERSION` 4 dropped them, and older saves' gear is rolled
again: see *Item level*.)

### Expected damage (the party screen)

The party screen's **Damage** page (D) shows each move's **expected damage
per use** (`combat.expected_damage`), to compare gear by: against a typical
foe of the Pokémon's own level (base Defense, Special and HP 70, no gear,
neutral to every type: `REFERENCE_BASE`). It's the formula above on
average: the spread's mean (×0.925), crits at their chance (move ratio and
gear crit; Sniper's ×2), × the chance to hit, × the
average number of hits (2–5: 3.5), with STAB and the move type's power gear.
What depends on the battle isn't counted: type matchups, stat stages, Leaf
Shield, conditional talents (pinch, streak, Ambush, ...). Super Fang: half
the foe's HP; Seismic Toss and Sonic Boom: their fixed damage. While
choosing gear it shows Now / New / Change per move, like the stats.

**Rating** (`combat.rating`): while choosing gear, the party window shows
three numbers, now and with the highlighted piece (the change in green or
red, and in %), to tell an upgrade at a glance:

- **<Type> hit:** the expected damage of a standard 70-power move of the
  Pokémon's (first) type (`RATING_POWER`);
- **Neutral hit:** the same for a typeless one (physical, no STAB);
- **Toughness:** how many standard hits from the typical foe it survives:
  max HP over the average of a physical and a special 70-power hit (with
  the foe's crit chance and the spread's mean).

### Worked example

Lv10 Bulbasaur (Attack 14, no gear) uses Tackle (Normal, 35) on Lv10
Pidgey (Defense 13):

```
base = (2×10/5 + 2) × 35 × 14 / 13 / 50 + 2 = 6 × 35 × 14 / 650 + 2 ≈ 6.52
spread: 5.54 … 6.52
Normal vs Normal/Flying = ×1, no STAB (Bulbasaur is Grass/Poison)
→ 6 or 7 damage (crit: 8–10)
```

With Sprout Strike, Tackle is a Grass move: it uses Bulbasaur's Special (and Pidgey's) and gets
×1.5 STAB. (Talents that change a move's type change whether it's special.)

### Effects that happen when a hit lands

In the order the battle checks them:

- **Endure** (gear `endure`: Focus Band, Halo): if the hit would knock the
  target out, an `endure`% chance to survive with 1 HP instead.
- **Drain** (gear `drain`: Shell Bell, Tricorne, "Draining"; moves:
  Absorb, Mega Drain heal 1/2): the user heals that share of the damage
  actually dealt (min 1), if it's hurt. Gear and move drain add up.
- **Status from gear** (`status:<status>`, e.g. Witch Hat, "of the Muk"):
  each status the user's gear has is rolled at its % chance, and the first
  that succeeds is inflicted. Only if no gear status went through does the
  **move's own status** roll at its chance (Poison Sting 30% poison,
  Thunder Shock 10% paralysis, ...). See *Status conditions* for who can
  get what.
- **Recoil** (Take Down, Double-Edge): the user loses 1/4 of the damage
  it dealt (min 1).
- **Stat changes by chance** (Acid 33% Defense, Bubble 33% Speed, Aurora
  Beam 10% Attack, ...): lowered on the target.
- **Confusion by chance** (Confusion, Psybeam 10%): see *Confusion*.
- **Flinch** (Headbutt 30%, Hyper Fang 10%): the target loses its turn
  this round, if it hasn't moved yet.
- **Bind** (Wrap, Clamp): the target loses 1/16 of its max HP at the end of
  each round for 2–5 rounds (Gen 2+ style; Gen 1 locked the target). A
  bound Pokémon isn't bound again until it's free.

**Several hits** (Fury Attack, Pin Missile, Double Slap: 2–5 hits; 2 or 3
each 3/8 of the time, 4 or 5 each 1/8; Twineedle: 2): each hit is worked
out on its own (its own crit), the total shows as one number, and each
hit rolls the added effects' chances.

**Super Fang** takes half the target's current HP (min 1), whatever the
stats; only type immunity stops it (Ghost).

**Seismic Toss** (`Move.fixed`) deals damage equal to the user's level,
whatever the stats and types (as in Gen 1): no crits, STAB or gear.

**Pay Day** (`Move.pay_day`: 2): each hit by a party member scatters
₽2 × the user's level (Gen 1's rule); the party picks it up if it wins
the battle (`BattleScene.scattered`, added to the prize row of the
rewards). Meowth's Amulet Coin talent doubles it.
- **Berries:** the target (and the user, after recoil) may eat its berry
  right after the move (see *Berries*).

### Moves that aren't attacks

- **Status moves** that inflict a status or confusion work with their
  Gen 1 chance (Poison Powder, Sleep Powder, Stun Spore, Lovely Kiss 75%;
  Hypnosis 60%; Sing, Supersonic, Poison Gas 55%; Thunder Wave, Confuse
  Ray 100%), unless the
  target already has a status or its type is immune. Every other status
  move always works.
- **On every enemy** (Drowsy Dust, Numbing Cloud, Pollen Cloud, Chorus,
  Spore Cloud, Mass Hypnosis, Echo, Chain Lightning, Fungal Bloom, the
  Megaphone gear effect): each enemy rolls its own chance, at **half** the
  move's (`moves.SPREAD_STATUS`): Sleep Powder 37.5% each, Spore 50% each.
  Against one enemy left standing it keeps the move's own chance.
  A lucky use can put the whole team to sleep, an unlucky one nobody, but
  on average about a third of them (not three in four).
- **Immune types:** Leech Seed doesn't affect Grass types, Thunder Wave
  doesn't affect Ground types.
- **Stat stages** (Growl, Growth, Sand-Attack, ...): see *Stat stages*.
- **Leech Seed:** the target is seeded; see *End of round*.
- **Leaf Shield** and **Reflect** (the same effect): the target takes
  half damage for its rounds.
- **Recover:** the user heals half its max HP.
- **Kinesis:** lowers the target's accuracy 1 stage, like Sand-Attack.
- **Focus Energy:** the user's crit chance ×4 for the rest of the battle
  (Gen 1's intended effect; its real one was a bug).
- **Rest:** the user's status is cured, it heals fully, and it falls
  asleep for exactly 2 turns.
- Moves that **hit every target** (Pollen Cloud, Solar Flare, ...): one on
  the enemies is still aimed at one of them (big arrow; the others get
  small ones), which takes full damage, the others the move's share; a
  move it sets off (Spore Storm) goes to that one only (a set-off move
  never hits every target). One on the own side (Canopy) needs no target
  choice and works on each Pokémon there. Enemies using one aim at a
  random target.
- **Extras talents add to moves** (`docs/talents.md`; the `Move` fields
  stay from the skill trees, so more talents can use them): *Empowering*
  (Full Bloom: the user's next damaging move deals +50%, spent by it);
  *Rallying* (Shared Sun: a move on the user works on its whole side);
  *Spiked* (Thornskin: for 3 rounds, whoever hits the protected Pokémon
  loses 1/16 of its max HP); *Siphoning* (Siphon: the poisoner heals a
  share of the poison damage); *Nightmare*, *Contagion* (see *End of
  round*); also `follow_up`, `expose`, `shock`, `madness`, `cleanse`,
  `light_sleep` (no talent uses them yet).
- **Reach** (`BattleScene._beside`; Flower Power): after the move lands on
  its target, it also hits one random enemy standing next to it (the one
  before or after it in the line) at its share, with no added effects; a
  *spill* move (`Move.spill`) rolls its chance for each enemy next to the
  target to burn/poison it, lower a stat 1 stage or confuse it. Neither
  carries into a set-off move.

### Confusion

Not a status (it can come on top of one), and only for the battle.
Confusion (the move) and Psybeam have a 10% chance, Supersonic 55%,
Confuse Ray always; Thrash and Petal Dance confuse their user. It lasts
2–5 of the Pokémon's turns. Each turn it's confused, it has a 50% chance
to hurt itself instead of acting (a typeless 40-power hit on itself);
on the last turn it snaps out of it and acts.

### Stat stages

Attack, Defense, Speed and accuracy each have a stage from **−6 to +6**
for the rest of the battle (Gen 1's multipliers):

| Stage | −6 | −5 | −4 | −3 | −2 | −1 | 0 | +1 | +2 | +3 | +4 | +5 | +6 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| × | 1/4 | 2/7 | 1/3 | 2/5 | 1/2 | 2/3 | 1 | 1.5 | 2 | 2.5 | 3 | 3.5 | 4 |

Growl lowers Attack, Growth raises Attack, a Liechi Berry raises Attack.
The Attack and Defense stages also count for special moves (there's no
separate Special stage).

**Accuracy** is only ever lowered (Sand-Attack, Smokescreen) and doesn't
use the multipliers above: a Pokémon with lowered accuracy hits with a
chance of 1/12 less per stage, whatever move it uses (gentler than Gen 1,
where −6 hit only 1/4 of the time). Swift and Aerial Ace ignore it.

| Accuracy stage | −1 | −2 | −3 | −4 | −5 | −6 |
| --- | --- | --- | --- | --- | --- | --- |
| Hit chance | 92% | 83% | 75% | 67% | 58% | 50% |

### Turn order

`game/scenes/battle.py` (`_run_round`)

Each round, everyone picks first, then all actions play out in this order:

1. **Items** (medicine) before any move.
2. Then moves with **priority** (Quick Attack) before the rest.
3. Then Pokémon whose **"act first"** gear roll succeeded (`first`: Quick
   Claw, Officer's Cap, "Hasty"; rolled every round).
4. Then **fastest first** by Speed (with gear, × its Speed stage
   multiplier; **halved if paralyzed**).
5. Ties are settled at random.

**Solar Beam** spends one round charging and hits the next (with Sunlit,
not once the user has used Growth in the battle). After **Hyper Beam**
the user must rest the next round (with Hyper Bloom, not after a knockout).

**Taunting Growl:** for the round it's used and the next, the foes'
single-target moves go to the user (`Combatant.taunt`).

**Talents at the battle's start** (`BattleScene._auras`): Miasma (50% per
foe: poisoned), Thunder Cloud (30%: paralyzed), Heat Haze, Absolute Zero,
Bedtime Story and the like (burned, frozen, asleep), Intimidate (every
foe's Attack −1), Sand Veil (every foe's accuracy −1). **When hit** (`_hit`): Static / Poison Point (25%: the
attacker is paralyzed / poisoned), Thorny Hide (the attacker loses 1/16 of
its max HP); Guardian and its copies (once a battle, a partner hit for its
last HP keeps 1).

### End of round

After all actions, in this order:

1. **Burn and poison damage** (see below; Pyre: burned foes of its side lose
   a further 1/8), then healing berries may be eaten.
2. **Leech Seed:** each seeded Pokémon loses its seed's share of its max
   HP (1/16; min 1), and whoever seeded it
   gets that much back (if it's still standing).
3. **Bind:** bound Pokémon lose their bind's share of max HP (min 1).
4. **Wounds** (`Move.bleed`): wounded Pokémon lose their
   wound's share of max HP (min 1), for 3 rounds.
5. **Regen:** first **Second Wind** (once a battle, below ⅓ HP: ¼ of max
   HP), then Shed Skin (30%: cures its status). Then gear `regen`
   (Leftovers, Nightcap, "of the Chansey") and talents (Photosynthesis
   and the like: 1/16; Nurturing: the whole side 1/16; Dream Eater: 1/8
   per sleeping foe): heals that share of max HP (min 1), plus a
   Lingering berry's HP (3 rounds after it's eaten). Then each cure berry whose holder has its status gets its
   chance (`berry_cure`).
6. **Lasting effects** (`BattleScene._afflictions`): Nightmare (a
   sleeper loses its share of max HP), Contagion (its chance for the
   status to spread to a free neighbour, with the same extras), Exposing
   and Spiked count down (3 rounds).
7. **Leaf Shield** counts down: it lasts the round it's used and the next
   Taunts count down. Flinching wears off.

---

## Status conditions

`game/mechanics/status.py`, `game/scenes/battle.py` (`_can_act`,
`_status_damage`)

A Pokémon has at most one status. It **stays after battle** until it's
cured, it faints (fainting clears it), or the party reaches a town.

| Status | Effect | Immune type |
| --- | --- | --- |
| Burn | Attack ×0.5; loses 1/16 max HP at the end of each round | Fire |
| Poison | Loses 1/8 max HP at the end of each round. **Badly poisoned** (Toxic Spores): 1/16, then 2/16, 3/16, ... for the rest of the battle | Poison |
| Paralysis | Speed ×0.5; 25% chance each turn to be fully paralyzed (can't act) | Electric |
| Sleep | Loses 1–3 turns; it wakes up on the last of them | none |
| Freeze | Loses its turns; each turn a 20% chance to thaw out | Ice |

Waking up or thawing out still uses up that turn; the Pokémon acts again
from the next round. Burn/poison damage is at least 1 HP. Asleep or frozen
party members still get the menu, but only items work: Fight and Skills
(greyed) sleep through the turn (`Combatant.dozing`).

---

## Healing

- **Towns** fully heal the party (HP and status) on arrival. This is a
  stand-in for Poké Centers and Mom's house.
- **Pokémon Centers:** Up at one heals the party too (the Nurse), and
  makes that town where a fainted party wakes up: the checkpoint before
  Mt. Moon is the Pokémon Center stop at the end of Route 3.
- **Medicine** (`game/mechanics/items.py`, `MEDICINE`) is used from the
  battle's Item menu (it takes the user's turn) or from the **bag**
  outside battle. In battle an item always goes first (before any move,
  priority ones too) and always works: sleep, freezing, paralysis,
  confusion or a flinch never stop it. An asleep user's sleep still counts
  down that turn, and a frozen one may still thaw (`BattleScene._doze`).
  Outside battle, from the **bag** (I on a map: pick the item, then
  the party member). It's only used up if it has an effect: Revive only
  works on a fainted Pokémon, everything else only on one still standing.

| Medicine | Effect |
| --- | --- |
| Potion / Super Potion / Hyper Potion | +20 / +50 / +200 HP |
| Max Potion | Full HP |
| Full Restore | Full HP and cures any status |
| Revive | A fainted Pokémon comes back with half its max HP (rounded up) |
| Antidote / Burn Heal / Paralyze Heal / Awakening / Ice Heal | Cures that one status |
| Full Heal | Cures any status |
| Escape Rope | Not in battle: from the bag on a route or in a dungeon, back to the last town or Pokémon Center (where a fainted party would wake up) |
| Nugget | Only worth money (`Medicine.valuable`): sold at a Poké Mart for ₽5,000; not in the battle's Item menu. From the Nugget Bridge Rocket |

### Berries

Berries are eaten **at most once per battle** and are **not used up** (the
same berry works again next battle). Healing amounts are **absolute HP**,
like potions', so a berry is worth less to a stronger Pokémon. A berry is
only eaten when it does something:

| Berry | When | Effect (Lv50 Common; see *Item level*) |
| --- | --- | --- |
| Oran Berry | HP at or below 1/2 (Early: 2/3); checked at the start of battle, after being hit, and after end-of-round damage | Heals `berry_heal` HP: 20–24 (Lv5 Common: 4) |
| Liechi Berry | HP at or below 1/4 (Early: 1/2) | Attack stage +1 (+2 at Epic and up; not above +6) |
| Pecha / Rawst / Cheri / Chesto / Aspear | At the end of each round its holder has that status | `berry_cure`% chance to cure poison / burn / paralysis / sleep / freeze: 30–40% (Lv5 Common 13%) |
| Lum Berry | Same, any status | 15–20% chance to cure it |

**Berry affixes** (`items.BERRY_AFFIXES`; as many as gear's by rarity:
Uncommon 1, Rare 2–3, Epic 3–4, Legendary 4–5) add to what happens when
it's eaten:

| Affix | When eaten (Lv50 Common) |
| --- | --- |
| Juicy | also heals 10–12 HP |
| Bitter | 30–40% chance to also cure any status |
| Spicy / Dry / Sweet | also Attack / Defense / Speed +1 stage |
| of the Vileplume | then heals 5–6 HP at the end of each of the next 3 rounds |
| of the Exeggcute | 20–30% chance it isn't used up (can be eaten again this battle) |
| of the Jolteon | eaten sooner (Oran at 2/3 HP, Liechi at 1/2) |

---

## Gear

`game/mechanics/items.py`

Each Pokémon has four slots: **Head** (hats, drawn on the Pokémon),
**Held**, **Worn** and **Berry**. A piece of gear is an item at a rarity and
an **item level**, plus its rolls.

**Starting gear:** the starter (Bulbasaur, Charmander or Squirtle, chosen
at the start, Lv5) holds a Common Lv5 Oran Berry (heals 4 HP at half HP,
once per battle); the bag starts without gear.

### Item level

- A piece's **item level** is the level needed to **equip** it: the
  Pokémon's level must be at least the item level. (The party screen lists
  gear it can't use yet greyed out, with the level in red.)
- Dropped gear gets the **defeated Pokémon's level**; chest gear a level in
  the area's range (its Pokémon's lowest to highest level; a boss chest:
  the boss group's highest level).
- Every range in `ITEMS`, `HATS` and the affixes is a **Lv50 Common**
  item's (`items.FULL_LEVEL`). The item level scales it (`items.scale`):
  - **stats, type damage and crit** (`hp`, `attack`, `defense`, `speed`,
    `power:<type>`, `crit`): × (0.25 + 0.25 × level/100) (`STAT_SCALE`:
    Lv5 ×0.26, Lv20 ×0.3, Lv50 ×0.375, Lv100 ×0.5). Gently: new gear is
    better, but a piece doesn't double from one area to the next, and a
    whole set adds about ×1.15 damage early and ×1.5 late;
  - **chances and special effects** (`first`, `endure`, `status:*`,
    `regen`, `drain`, berries' chances): × √(level/50) (Lv5 ×0.32, Lv20
    ×0.63, Lv50 ×1, Lv100 ×1.41), so they still show early;
  - **berry healing** (absolute HP): × (level + 5)/55 (Lv5 ×0.18, Lv20
    ×0.45, Lv50 ×1);
  - stages and switches (Liechi, Spicy, Early) don't scale.
- **Special effects** (`first`, `endure`, `regen`, `drain`, `status:*`)
  don't use the rarity factor but their own, steeper ladder
  (`items.SPECIAL_FACTOR`): Common ×0.5, Uncommon ×0.75, Rare ×1.0, Epic
  ×1.5, Legendary ×2.0. Quick Claw (12…18%) at Lv50: Common 6…9%, Rare
  12…18%, Legendary 24…36%.
- **Endure** items (Focus Band, Halo) only drop at **Epic or better**
  (`Item.min_rarity`). Loot, enemies' gear and quest rewards pick the
  rarity first, then an item that drops at it.
- **Every bonus is priced by what it's worth**, so items of the same
  level and rarity are about equally strong (ranges before scaling):
  Attack/Defense/HP 14–18 is the yardstick; Speed (only turn order)
  20–26; one type's moves 18–24; crit 8–10 points (rare and capped: a
  point is about +0.5% damage); trade-off items (Power Bracer) 26–34 for
  a Speed penalty. Affixes are about a third of an item's effect.
- **Six mods** make up gear's numbers: HP, Attack, Defense, Speed (%),
  crit (points) and one type's damage (%); the rest are special effects
  (act first, endure, regen, drain, status chance) and berries'.
- **Older saves** (gear saved under older rules, `items.GEAR_VERSION`)
  are rolled again once, on loading (`items.updated_gear`): same item
  (an Endure item below Epic becomes another of its slot), rarity, level
  and affixes, new values.
- So newer gear of a lower rarity can beat older gear of a higher one.
  Red Bandana (Attack 14…18) at its highest roll: Common Lv5 +5%,
  Common Lv25 +6%, Rare Lv25 +8%, Common Lv50 +7%, Legendary Lv50 +11%,
  Legendary Lv100 +16% (affixes on top).

### Rolling a piece (`Gear.roll`)

1. **The item's own effect** is rolled from its range (e.g. Red Bandana:
   Attack +14…18% at Lv50).
2. **Affixes:** Head, Held and Worn items get the number of affixes their
   rarity gives (Common none), berries as many berry affixes. Affixes are picked by weight without
   repeats (normal affixes weight 3; Hasty, Draining and of the Chansey 2;
   type and status affixes 1).
3. **Each value** is rolled as a whole number in its range, then:
   - a **bonus** (positive) is × the rarity factor (× the special factor
     instead for a special effect, see above) × its item-level scale,
     rounded, min 1 (Python rounds .5 to the even number: 7.5 → 8, but
     2.5 → 2);
   - a **penalty** (negative, e.g. Power Bracer's Speed −10% at Lv50) is ×
     the item-level scale only, rounded, at least −1.
4. **Name:** the first prefix + item + the first suffix ("Fierce Red Bandana
   of the Aerodactyl"). Further affixes still count but aren't in the name.
5. **Special effect** (Rare and up only): a 10% (Rare), 20% (Epic) or 40%
   (Legendary) chance (`EFFECT_CHANCE`) of one special effect, picked
   evenly (see *Special effects*).

Affixes can stack on the same stat as the item (a Fierce Red Bandana has
two Attack rolls), and all rolls simply add up.

| Rarity | Factor | Affixes | Where it drops (for now) |
| --- | --- | --- | --- |
| Common (white) | ×1.0 | 0 | everywhere |
| Uncommon (green) | ×1.15 | 1 | boss groups (from the second area on) |
| Rare (blue) | ×1.3 | 1–2 | mid game (bosses from Diglett's Cave on) |
| Epic (purple) | ×1.45 | 2 | late game, the Battle Tower |
| Legendary (orange) | ×1.6 | 2–3 | end game |

Example: Muscle Band (Attack 14…18) at Legendary Lv20 rolls 14…18 × 1.6
× 0.3 = Attack +7…9%.

### What gear can do (mods)

| Mod | Meaning |
| --- | --- |
| `hp`, `attack`, `defense`, `speed` | % on that stat (see *Gear on stats*) |
| `crit` | + percentage points of crit chance (base 5%) |
| `power:<type>` | % more damage with moves of that type |
| `status:<status>` | % chance per hit to inflict that status |
| `first` | % chance per round to act before everyone else (after items) |
| `endure` | % chance to survive a knockout hit with 1 HP |
| `regen` | % of max HP healed at the end of each round |
| `drain` | % of damage dealt healed |
| `berry_*` | berry effects and berry affixes (see *Berries*) |

### Affixes

Values at Lv50 Common (before the rarity factor and item level).

| Prefix | Mods | | Suffix | Mods |
| --- | --- | --- | --- | --- |
| Fierce | Attack 5…6 | | of the Machamp | Attack 5…6 |
| Sturdy | Defense 5…6 | | of the Onix | Defense 5…6 |
| Swift | Speed 7…9 | | of the Pidgeot | Speed 7…9 |
| Hearty | HP 5…6 | | of the Snorlax | HP 5…6 |
| Keen | Crit 3…4 | | of the Tauros | Attack 3, Speed 4 |
| Hasty | First 3…6% | | of the Golem | Defense 3, HP 3 |
| Draining | Drain 3…6% | | of the Scyther | Crit 3, Attack 3 |
| | | | of the Chansey | Regen 2…3% |
| | | | of the Moltres, of the Gyarados, … (15 types) | Type power 6…8 |
| | | | of the Magmar / Muk / Pikachu | Burn / poison / paralysis chance 5…10% |
| | | | of the Hypno / Jynx | Sleep / freeze chance 3…6% |

Berries roll their own affixes (see *Berries*).

### Special effects

`items.GEAR_EFFECTS`, `Gear.effect`

Gear's "red text": rare pieces that change how their wearer fights rather
than adding a bigger number. They're written like talents (move changes by
selector and battle flags, see `docs/talents.md`) and work the same way:
`Monster.talent` reads gear effects' flags too, and `Monster.move` applies
their move changes after the talents' (talents' rules: numbers add up, a
spread share keeps the higher, ...). An effect and a talent with the same
flag don't add up: the stronger counts. They work for any wearer (selectors
by kind of move, not by name). A piece has at most one; shown in red (its
name, what it does and a quote) on the party screen, in the bag and at
Persian's counter. A piece with one is worth ×1.5 (`EFFECT_VALUE`: its
price and what it sells for).

| Effect | What it does | As talent data |
| --- | --- | --- |
| Earthshaker | The basic attack hits every enemy, the others at 50% | basic: spread, share 0.5 |
| Double Tap | The basic attack hits twice, at 65% power each | basic: hits 2, scale −0.35 |
| Megaphone | Status moves work on every Pokémon on the side they aim at | status moves: spread |
| Ricochet | Damaging moves also hit an enemy next to the target, at half damage | damaging: reach 0.5 |
| Quickdraw | Damaging moves always go first | damaging: priority +1 |
| Executioner | Damaging moves always crit a target below 1/3 HP | damaging: keen 1/3 |
| Armor Breaker | Damaging moves: 30% chance to lower the target's Defense 1 stage | damaging: Defense −1, 30% |
| Thornmail | Whoever hits the wearer loses 1/8 of its max HP | thorns 1/8 |
| Phoenix Feather | Once a battle, ending a round below 1/3 HP heals half max HP | second_wind 0.5 |
| Storm Cell | Whoever hits the wearer: 30% chance to be paralyzed | retaliate:paralysis 30 |
| Plague Charm | Battle start: each enemy 40% chance to be poisoned | aura:poison 40 |
| Dread Mask | Battle start: every enemy's Attack −1 stage | lower:attack 1 |
| Hunter's Mark | +50% damage to a target that hasn't moved this round | ambush 0.5 |
| Pack Tactics | +40% damage to a target a partner already hit this round | gang 0.4 |
| Gale Banner | +40% damage with moves that hit every enemy | wide 0.4 |
| Rallying Cry | The whole side heals 1/16 max HP at each round's end | party_regen 6.25 |
| Aegis | While the wearer stands, its side takes 20% less damage | ancient_roots 0.2 |
| Last Rites | Once a battle, a partner that would faint keeps 1 HP and is healed half its max HP | world_tree, guard_heal 0.5 |

Item stats are listed in `ITEMS` and `HATS` in `items.py`.

---

## Loot

`game/mechanics/loot.py`

A loot table rolls one or more times. Each roll picks one entry by
weight: nothing, some medicine, or a piece of gear (a random item, at a
rarity picked by weight, at an item level: see *Item level*).

- **Won battle:** the wild table is rolled **once per defeated enemy**, at
  that enemy's level. Each piece of gear a defeated enemy wore (bosses and
  trainers, below) also drops with a **10%** chance (`WORN_DROP_CHANCE`).
- **Poké Ball** lying on a map (Up): the ball table once: **one item**,
  never nothing. Maps have 0–2 (on platforms or along the ground), a
  dungeon room's at the same spots every trip.
- **Chests** are special: there are none by the roadside, only the one a
  boss leaves (below). Up opens it.
- **Boss chest** (`Route.boss_chest`): after a route's boss (e.g. the
  giant Caterpie) a **plain chest**: the chest table once, at the boss
  rarities. After a **gym**, the **fancy chest**: the boss table once
  (3–4 rolls). The rival, the trials, the feud and Team Rocket give the
  boss table with the battle instead ("battle"); recruitments give no
  chest (the Pokémon is the reward).
- **A boss is a boss once.** Once beaten (`Game.trainers` keeps
  "boss:<route>", or "boss:<route>/<room>" in a dungeon; older saves: a
  route walked all the way through), later trips find its group there at
  normal size: an ordinary wild battle (the group it led, without the
  extras that join it for a pair; or the `Route.boss_after` group), with no
  boss loot or chest, and the way out open. The exception: while a quest
  is at the step of defeating that route's boss (`quests.boss_wanted`, e.g.
  the board's *Bugs in the Forest*), it's there as a boss again.

Which **rarities** can drop is set per area (`Route.loot` for wild
Pokémon and chests, `Route.boss_loot` for a boss group's drops and chest):

| Table | Rolls | Nothing | Medicine | Gear |
| --- | --- | --- | --- | --- |
| Wild (per enemy) | 1 | 60% | 36% (Potion 20%, Super Potion 4%, status cures 12%) | 4% (rare: gear mostly comes from chests) |
| Poké Ball | 1 | – | 100%: Potion 40%, Super Potion 14%, Antidote 8%, Revive 6%, Paralyze Heal 6%, Burn Heal 5%, Awakening 5%, **Escape Rope 4%**, Ice Heal 3%, Full Heal 3%, Hyper Potion 2% | – |
| Chest | 2–3 | – | 67% (Potions 1–3, Revive, cures, ...) | 33% |
| Boss | 3–4 | – | 45% (Super/Hyper Potion, Revive, Full Heal/Restore) | 55% |

| Area | Wild and chests | Boss |
| --- | --- | --- |
| Route 1 | Common | (no boss) |
| Viridian Forest | Common | Common 60%, Uncommon 40% |
| Route 22 | Common | Common 60%, Uncommon 40% (the rival: a reward roll with the battle, no chest) |
| Pewter Gym | (no wild Pokémon or chests) | Common 60%, Uncommon 40% (the Boulder Gang: the fancy chest) |
| Cerulean Gym | (no wild Pokémon or chests) | Common 60%, Uncommon 40% (the Cascade Crew: the fancy chest) |
| Vermilion Gym | (no wild Pokémon or chests) | Common 60%, Uncommon 40% (the Thunder Battalion: the fancy chest) |
| Celadon Gym | (no wild Pokémon or chests) | Common 33%, Uncommon 50%, Rare 17% (`MID_BOSS`: the Blossom Troupe, the fancy chest) |
| Pokémon Tower | Common | Common 33%, Uncommon 50%, Rare 17% (`MID_BOSS`: the rival and the Rockets, a reward roll with each battle, no chest) |
| Rocket Hideout | (no wild Pokémon or chests) | Common 33%, Uncommon 50%, Rare 17% (`MID_BOSS`: the Lift Key Guard and the Rocket Boss, a reward roll with each battle, no chest) |
| Route 3 | Common | (no boss) |
| Mt. Moon | Common | Common 60%, Uncommon 40% (Team Rocket: a reward roll with the battle, no chest) |
| Route 4 | Common | (no boss) |
| Nugget Bridge (Route 24) | Common | Common 60%, Uncommon 40% (the rival: a reward roll with the battle) |
| Route 25 | Common | (no boss) |
| Burgled House (Cerulean) | (no wild Pokémon or chests) | Common 60%, Uncommon 40% (the burglar: a reward roll with the battle) |
| Route 5 | Common | (no boss) |
| Underground Path | Common | (no boss) |
| Route 6 | Common | (no boss) |
| S.S. Anne | (no wild Pokémon or chests) | Common 60%, Uncommon 40% (the rival: a reward roll with the battle) |
| Route 11 | Common | (no boss) |
| Diglett's Cave | Common | Common 33%, Uncommon 50%, Rare 17% (`MID_BOSS`: the giant Dugtrio's band, a chest) |
| Route 2 (north) | (no wild Pokémon or chests) | (no boss) |
| Route 9 | Common | (no boss) |
| Rock Tunnel | Common | Common 33%, Uncommon 50%, Rare 17% (`MID_BOSS`: the Hiker Crew, a chest) |
| Route 8 | Common | (no boss) |
| Underground Path (west) | Common | (no boss) |
| Route 16 | Common | (no boss) |
| Snorlax's Rude Awakening | (no wild Pokémon or chests) | none: the Snack Pack drops nothing, Snorlax joins (quest *The Sleeping Giant*) |
| Default for new areas (`COMMON_ONLY` / `EARLY_BOSS`) | Common | Common 60%, Uncommon 40% |

---

## Party and reserve

`game/world/progress.py` (`MAX_PARTY`, `Game.slots`, `Game.reserve`,
`Game.add_member`), `game/world/quests.py` (`active_limit`, `fit_party`,
`fighters`, `use_ribbon`), `game/mechanics/items.py` (`RIBBON`)

- The **party** is everyone who fights: **1** Pokémon at first, and one
  more place for each **Teamwork Ribbon** used (`Game.slots`, saved;
  `MAX_PARTY` = 6 at most). A ribbon is a special key item, given by the
  quests *Rival on Route 22* and *The S.S. Anne* (so far); the quest's
  dialogue says so. Using it from the bag (Key items → Enter) adds the
  place and uses it up ("Three Pokémon can now fight at your side!").
  Ribbons can be saved up (key items you can hold more than one of:
  `items.STACKING`). Saves from before the ribbons get one place per
  ribbon quest done.
- The first is the **lead** (the one on the map; party screen T puts a
  member first). Recruits that don't fit wait in the **reserve** (saved).
  A new place stays **empty** until the player fills it at a Recruitment
  Center (Mr. Mime → team); recruited Pokémon join the party while it has
  room. `fit_party` (on every map) only moves extra members (an older
  save's) to the reserve. Gyms and trials pick at most that many too.
- Arriving in a town heals the reserve too. Quest XP goes to the party;
  battle XP to the members still standing.

---

## Money

`game/mechanics/items.py` (`Bag.money`, `money_text`)

- **Poké Dollars (₽)** are kept in the bag (`Bag.money`, saved) and shown
  in the pause menu and on the party screen. A new game starts with ₽0.
- **Earned from quests** (every quest pays its `Quest.money`, see
  `quests.md`), **trainer battles** (prize money, see *Trainer battles*),
  Pay Day, and selling medicine and gear.
- **Spent at Poké Marts** (`game/scenes/mart.py`): medicine from Meowth
  at the counter, gear from Persian in its den behind the shop (a curtained
  doorway at the back; see *Gear counter* below). Medicine prices are `Medicine.price`, **half of Gen 1's**
  (money only comes from quests so far); selling pays half the price
  (`Medicine.sell_price`, as in Gen 1). Up to 99 at a time.
- The font has no ₽ sign, so `ui.text` draws it as a P with a bar.

| Medicine | Price | Sells for |
| --- | --- | --- |
| Potion | ₽150 | ₽75 |
| Super Potion | ₽350 | ₽175 |
| Hyper Potion | ₽750 | ₽375 |
| Max Potion | ₽1,250 | ₽625 |
| Full Restore | ₽1,500 | ₽750 |
| Revive | ₽750 | ₽375 |
| Fresh Water (50 HP) | ₽200 | ₽100 |
| Soda Pop (60 HP) | ₽300 | ₽150 |
| Lemonade (80 HP) | ₽350 | ₽175 |
| Antidote | ₽50 | ₽25 |
| Burn Heal | ₽125 | ₽62 |
| Paralyze Heal | ₽100 | ₽50 |
| Awakening | ₽100 | ₽50 |
| Ice Heal | ₽125 | ₽62 |
| Full Heal | ₽300 | ₽150 |
| Escape Rope | ₽275 | ₽137 |
| Nugget | – (not sold) | ₽5,000 (as in Gen 1) |

The drinks are only sold by the Celadon Department Store's rooftop vending
machines. Its 4F also sells the smith's materials: Scrap ₽300, Alloy
₽1,000, Crystal ₽3,000 (`items.MATERIAL_PRICE`; Ether and Star Shards only
come from salvage and smelting).

What each Poké Mart sells (`Town.mart`; Gen 1's stock, minus the items
the game doesn't have yet: Poké Balls, Repel):

| Town | Stock |
| --- | --- |
| Viridian City | Potion, Antidote, Paralyze Heal, Burn Heal |
| Pewter City | Potion, Super Potion, Escape Rope, Antidote, Burn Heal, Awakening, Paralyze Heal (Super Potion added: Gen 1 has it from Cerulean) |
| Cerulean City, Vermilion City | Potion, Super Potion, Escape Rope, Antidote, Burn Heal, Awakening, Paralyze Heal, Ice Heal |

### The smith: salvage and enhancement

`game/scenes/smith.py` (`SmithMenu`), `game/mechanics/items.py`
(`MATERIALS`, `Gear.plus`, `Gear.enhance_cost`, `Gear.salvage_yield`,
`enhanced`), `game/world/towns.py` (`smith`)

A **Machamp smith** stands at his anvil and furnace in the major towns
from Lavender Town on (the same townsfolk, `quests.SMITH`). Until his
quest *A Hammer Fit for a Smith* is done (`docs/quests.md`) he only talks;
then Up at him opens his menu:

- **Materials,** one per rarity (`MATERIALS`): Scrap (Common), Alloy
  (Uncommon), Crystal (Rare), Ether (Epic), Star Shard (Legendary), kept in
  `Bag.materials` (saved) and shown at the top of the menu.
- **Salvage:** a piece from the bag (not one that's worn) is broken down
  for good into **1 + item level // 25** of its rarity's material (Lv30: 2),
  plus half of what its enhancements cost.
- **Enhance:** a piece in the bag or worn by the party goes up one, to at
  most **+5** (`MAX_PLUS`), for its rarity's material: the step to +n costs
  **2 × n × (1 + item level // 25)** (`PLUS_COST`; a Lv30 piece: 4, 8, 12,
  16, 20; 60 in all). Each + raises every **bonus** of the piece by **5% of
  its own value** (`PLUS_BOOST`; `enhanced`: value × (1 + 0.05 × plus),
  rounded half up, so +5 is +25% and small bonuses grow only a little or not
  at all: Attack 13% is 14, 14, 15, 16, 16%; Attack 20% is 21, 22, 23, 24,
  25%; Regen 1% stays 1%); **penalties stay**. The + shows after its name ("Swift
  Muscle Band of the Arbok +2") and it's worth 15% more per + (`PLUS_VALUE`).
  The menu previews each bonus's change.
- **Smelt:** **4** of one material (`SMELT`) into 1 of the next rarity's
  (Scrap → Alloy → Crystal → Ether → Star Shard).

### Gear counter

`game/scenes/mart.py` (`GearShop`), `game/world/towns.py` (`Town.gear`,
`gear_stock`), `game/mechanics/items.py` (`Gear.value`, `price`,
`sell_price`)

- **What gear is worth** (`Gear.value`): by rarity, growing with the item
  level: `GEAR_PRICE` × (level + 10) / 15, rounded to ₽10 (Lv5: ×1, Lv20:
  ×2, Lv35: ×3); ×1.5 with a special effect. `GEAR_PRICE`: Common ₽200, Uncommon ₽500, Rare ₽1,200,
  Epic ₽3,000, Legendary ₽8,000.
- **Persian sells gear for 5× its worth** (`GEAR_MARKUP`): gear is meant
  to be won, and buying it a goal to save up for (every quest up to
  Vermilion pays about ₽30,000 in all). **It buys gear for half its
  worth** (`Gear.sell_price`, as for medicine): from the bag, not what's
  equipped. The bag's gear info shows what a piece sells for.
- **Stock:** 6 pieces (`GEAR_STOCK`), any item, at the town's item levels
  and rarities (`Town.gear`). It restocks each time the player arrives in
  the town from a route (`Game.arrive`; back out of a shop, a gym or a
  trial doesn't count); what's bought is gone until then
  (`Game.shop_bought`). The pieces are rolled from the game's seed and the
  visit (`Game.seed`, `Game.shop_visits`, saved), so loading a save shows
  the same ones.
- Buying and selling is one piece at a time, each asked to confirm; a piece
  nobody in the team is the level for yet says so (in red).

| Town | Item levels | Rarities | Lv-range prices (buy) |
| --- | --- | --- | --- |
| Viridian City | 5–9 | Common | Common ₽1,000–1,250 |
| Pewter City | 11–15 | Common 75%, Uncommon 25% | Common ₽1,400–1,650, Uncommon ₽3,500–4,150 |
| Cerulean City | 17–22 | Common 60%, Uncommon 40% | Common ₽1,800–2,150, Uncommon ₽4,500–5,350 |
| Vermilion City | 22–26 | Common 50%, Uncommon 45%, Rare 5% | Common ₽2,150–2,400, Uncommon ₽5,350–6,000, Rare ₽12,800–14,400 |

---

## Wild Pokémon

`game/world/themes.py`, `game/world/level.py`

Each map theme has a weighted pool of species with level ranges. A wild
group has 1, 2 or 3 Pokémon (weights 60 / 30 / 10; Route 1: 1 or 2, 80 /
20), each picked from the pool, each at a random level in its entry's
range. **Each Pokémon fighting after the first** gives each wild group a
50% chance (`overworld.EXTRA_FOE_CHANCE`) of one more Pokémon from the
pool: with two fighting (once the Route 22 rival is beaten), about half
the groups have one more; with three (after the S.S. Anne), two chances,
one more on average. Rolled from the map's seed, so it's the same each
time the map is shown. A **boss** (areas with
one) guards the last map's exit: the group the area names (`Route.boss_group`),
or else 4–5 Pokémon from the pool at the same levels; its leader (the
first) can be drawn bigger (`Route.boss_scale`). With two fighting, a
boss group can bring more escorts (`Route.boss_extra`: Viridian Forest).

**Touching a group** starts the battle. Besides the Pokémon themselves,
each group catches the player in an invisible column over it, up to
6 tiles (96 px) above its feet (`overworld.GROUP_REACH`; a full jump is
~62 px), so it can't be jumped over from the ground. The column stops at
the first tile overhead (a platform, also one a column to the side, or a
cave's ceiling): a group can still be passed on a platform over it, or
with a jump from a platform. A group that is only partly under a platform
is capped at that platform all along (the part sticking out past its end
too), so a jump off the platform clears the whole group.

**Running away** (wild battles only; trainers and bosses can't be run
from): the chosen party member tries, with a chance by its level minus the
highest enemy level: **75%** at an even match, **±8%** per level, between
**10%** and **100%** (`battle.RUN_EVEN`, `RUN_PER_LEVEL`, `RUN_MIN`). So
5 levels under the strongest enemy it's 35%, and 4 or more over it's
sure. Failing ("Can't escape!") costs that member its turn. The hint line
shows the chance while Run is highlighted.

Route 1 (Meadow pool; Red/Blue's Route 1: only Pidgey and Rattata):

| Species | Weight | Levels |
| --- | --- | --- |
| Pidgey | 55 | 2–4 |
| Rattata | 45 | 2–3 |

Viridian Forest (3 maps, Viridian City → Pewter City; Red's and Blue's
forest Pokémon together):

| Species | Weight | Levels |
| --- | --- | --- |
| Caterpie | 25 | 4–6 |
| Metapod | 20 | 5–7 |
| Weedle | 25 | 4–6 |
| Kakuna | 20 | 5–7 |
| Pikachu | 5 | 4–6 |

**Boss:** a Lv12 Caterpie drawn at double size, escorted by a Lv10 Weedle
and a Lv9 Kakuna (only the leader, the first of a boss group, is drawn
bigger); with two fighting (once the Route 22 rival is beaten), two more
Lv11 Weedle join it (`Route.boss_extra`). Tuned with
`tools/balance_sim.py`: a lone Lv11 starter, or a Lv11 + Lv10 pair, wins
about 70%. Beating them opens the way to Pewter City and leaves a plain
chest (the chest table at the boss rarities, item level 12).

Route 22 (2 maps, from Viridian City and back):

| Species | Weight | Levels |
| --- | --- | --- |
| Rattata | 40 | 3–6 |
| Nidoran M | 25 | 3–5 |
| Nidoran F | 20 | 3–5 |
| Spearow | 15 | 4–6 |

Route 22 opens once the quest "Rival on Route 22" starts, and Viridian
Forest once "Oak's Parcel" is done (see `quests.md`).

**Boss:** the rival (a trainer battle, see below): Pidgey Lv7 and his
starter Lv6: Gen 1's first rival team, two levels down, as here both
attack the player's starter at once (and it fights alone at this point;
`tools/balance_sim.py`: a Lv9 starter wins about 40–70%). Once he's beaten (the quest is
done), the boss is a wild Pidgey Lv9 and Spearow Lv9 instead (no trainer;
the reward roll stays). His starter beats the player's
(Bulbasaur → Charmander, Charmander → Squirtle, Squirtle → Bulbasaur).
Instead of a chest, winning rolls the boss loot table once (at Lv9) on top
of the usual drops.

Route 3 (3 maps, Pewter City → Mt. Moon; opens once the Boulder Badge is
won; Sandshrew from Blue, Ekans from Red; no boss, but six trainers, see
below):

| Species | Weight | Levels |
| --- | --- | --- |
| Spearow | 35 | 11–13 |
| Sandshrew | 25 | 11–13 |
| Jigglypuff | 20 | 8–12 |
| Ekans | 20 | 11–13 |

**Mt. Moon** (`Route` "mt_moon_cave", a dungeon, see below; entered from
the Pokémon Center stop at the end of Route 3, out to Route 4; Gen 1's
Pokémon a few levels up):

| Species | Weight | Levels |
| --- | --- | --- |
| Zubat | 45 | 14–18 |
| Geodude | 30 | 14–17 |
| Paras | 18 | 15–19 |
| Clefairy | 7 | 15–19 |

**Dungeons** (`Route.rooms`, `Room`, `Stair`): instead of a row of maps, a
set of rooms joined by **ladders** (Up to climb; Up or Down to go down a
hole) and doorways out. Each room is laid out the same every visit (its
own fixed seed: where the ground, platforms, groups and chests are); the
wild groups' Pokémon are rolled anew for every trip. During a trip, rooms
remember what's been beaten and opened (`Instance.rooms`, saved too).
Mt. Moon: 1F has the entrance and three ladders down: two lead to dead
ends (one B1F room with loot, or B1F → B2F west with trainers and
chests), the middle one to B1F → B2F, where the **Rocket Gang Leader**
(Sandshrew 18, Rattata 18, Zubat 19) blocks the ladder up to the B1F room
with the way out. Rooms are shown by floor only ("Mt. Moon B1F").

**Route 4** (`Route` "route_4_east", 2 maps, from the Route 4 stop at Mt.
Moon's exit down to Cerulean City; the stop is a town, "route_4"; Route
3's dry look; no boss, two trainers, see below):

| Species | Weight | Levels |
| --- | --- | --- |
| Rattata | 30 | 16–19 |
| Spearow | 30 | 16–19 |
| Ekans | 20 | 16–20 |
| Sandshrew | 20 | 16–20 |

**Nugget Bridge** (`Route` "nugget_bridge", Route 24: 2 maps from Cerulean
City up to the Route 24 stop, a town), as in Red/Blue: the **rival** waits
at the bridge's start (Pidgeotto 19, Abra 16, Rattata 16 and his starter's
next form at 20, `RIVAL_STARTER_EVOLVED`: Gen 1's team a couple of levels
up, as all four attack at once; a reward roll with the battle), then the
five trainer bands, and the arena at the far end holds a **Rocket** (Ekans
23, Zubat 22) who gives the Nugget. Once he's beaten the arena holds
Oddish 22, Bellsprout 22 and Abra 21 instead (wild). Oddish from Red, Bellsprout from Blue:

| Species | Weight | Levels |
| --- | --- | --- |
| Oddish | 25 | 18–21 |
| Bellsprout | 25 | 18–21 |
| Pidgey | 20 | 19–22 |
| Abra | 10 | 17–20 |
| Caterpie | 10 | 16–18 |
| Weedle | 10 | 16–18 |

**Route 25** (`Route` "route_25", 2 maps from the Route 24 stop east to
Bill's Sea Cottage, a town; no boss, four trainers):

| Species | Weight | Levels |
| --- | --- | --- |
| Oddish | 20 | 19–22 |
| Bellsprout | 20 | 19–22 |
| Venonat | 20 | 19–22 |
| Pidgey | 15 | 20–23 |
| Abra | 10 | 18–21 |
| Metapod | 8 | 18–20 |
| Kakuna | 7 | 18–20 |

**Route 5** (`Route` "route_5_south", 2 maps from Cerulean City's
doorway behind the burgled house south to the Route 5 stop, a town; no
boss or trainers, as in Red/Blue). Meowth from Blue, Mankey from Red:

| Species | Weight | Levels |
| --- | --- | --- |
| Meowth | 25 | 20–23 |
| Mankey | 25 | 20–23 |
| Pidgey | 20 | 21–24 |
| Oddish | 15 | 20–23 |
| Bellsprout | 15 | 20–23 |

**Underground Path** (`Route` "underground_path", 2 maps of tunnel from
the Route 5 stop to the one at the top of Route 6; no boss or trainers, as
in Red/Blue, which has no wild Pokémon there; here the Diglett who dug it
out again, and what moved in):

| Species | Weight | Levels |
| --- | --- | --- |
| Diglett | 35 | 21–24 |
| Rattata | 30 | 22–25 |
| Zubat | 20 | 22–25 |
| Ekans | 15 | 22–25 |

**Route 6** (`Route` "route_6_south", 2 maps from the Route 6 stop down to
Vermilion City; four trainers):

| Species | Weight | Levels |
| --- | --- | --- |
| Meowth | 20 | 22–25 |
| Mankey | 20 | 22–25 |
| Pidgey | 20 | 23–26 |
| Oddish | 15 | 22–25 |
| Bellsprout | 15 | 22–25 |
| Psyduck | 10 | 22–25 |

The **S.S. Anne** (`Route` "ss_anne", a dungeon of 4 rooms docked at
Vermilion City, open only while its quest is going on): no wild Pokémon,
as in Red/Blue; its decks are `Theme.built` (flat, polished planks, the
painted wall of portholes). Its trainers are its only Pokémon, among them
the game's only Machop, Tentacool and Growlithe (not recruitable). The
Captain stands in his cabin (`Room.folk`: talked to like townsfolk).

The **Burgled House** (`Route` "cerulean_backyard", walked from the house
at the end of Cerulean's street, open while quest *The Cerulean Burglar*
is active): a short walk (30 tiles, no wild Pokémon) to its backyard,
where the burglar's **Rocket Gang** (Mankey 24, Abra 22, Zubat 22; Gen 1's
Machop and Drowzee) waits. Win rate in `tools/balance_sim.py` at Lv24 +
Lv23: about 73%.

**Route 11** (`Route` "route_11", 2 maps east of Vermilion City, from its
doorway by the dock to the Route 11 Gate stop; open once the Thunder
Badge is won; five trainers):

| Species | Weight | Levels |
| --- | --- | --- |
| Drowzee | 30 | 26–29 |
| Spearow | 25 | 26–29 |
| Ekans | 20 | 26–29 |
| Sandshrew | 20 | 26–29 |
| Fearow | 5 | 27–29 |

**Diglett's Cave** (`Route` "digletts_cave", 3 maps of earthen tunnel from
the Route 11 Gate to the Route 2 stop by Pewter City; theme
`DIGLETTS_CAVE`: its wall `walls/digletts_cave.png`, roots hanging from
the ceiling; Gen 1's Diglett 15–22 and Dugtrio 29–31, raised to the
party's levels). Its last map ends in an arena: a **giant Dugtrio 35**
with Dugtrio 32 and Diglett 31 ×2 guards the way out (×2 size; a chest,
`MID_BOSS` loot). Win rate in `tools/balance_sim.py` for three at Lv31 +
Lv30: about 82%.

| Species | Weight | Levels |
| --- | --- | --- |
| Diglett | 70 | 26–29 |
| Dugtrio | 30 | 28–31 |

**Route 2** (`Route` "route_2_north", one short map, 40 tiles, from the
Route 2 stop at the cave's far end up to Pewter City's doorway by its
east end): no wild Pokémon (`wild=False`; Gen 1's are far below the
party by now).

**Route 9** (`Route` "route_9", 2 maps east of Cerulean City, from its
doorway at the street's east end to the Route 10 Pokémon Center; open
once HM05 Flash is in hand; five trainers):

| Species | Weight | Levels |
| --- | --- | --- |
| Rattata | 20 | 29–32 |
| Spearow | 20 | 29–32 |
| Ekans | 15 | 29–32 |
| Sandshrew | 15 | 29–32 |
| Raticate | 10 | 31–33 |
| Fearow | 10 | 31–33 |
| Voltorb | 10 | 30–32 |

**Route 8** (`Route` "route_8", 2 maps west of Lavender Town, from its
doorway at the town's east end to the Route 8 Gate stop, at Saffron's
shut east gate; four trainers):

| Species | Weight | Levels |
| --- | --- | --- |
| Pidgeotto | 20 | 33–35 |
| Growlithe | 15 | 32–35 |
| Mankey | 15 | 32–35 |
| Meowth | 15 | 32–35 |
| Ekans | 10 | 32–35 |
| Sandshrew | 10 | 32–35 |
| Abra | 10 | 31–33 |
| Kadabra | 5 | 34–36 |

The **Underground Path's west-east tunnel** (`Route` "underground_west",
theme `UNDERGROUND_WEST`: the north-south tunnel's look, deeper in; 2 maps
from the Route 8 Gate under Saffron to Celadon City; no trainers):

| Species | Weight | Levels |
| --- | --- | --- |
| Diglett | 30 | 32–35 |
| Raticate | 20 | 33–35 |
| Zubat | 20 | 32–35 |
| Ekans | 15 | 32–35 |
| Dugtrio | 15 | 33–36 |

**Route 16** (`Route` "route_16", theme `ROUTE_16`: 2 maps west of
Celadon West End to the Route 16 Gate; shut until the Snorlax across it is
awake, quest *The Sleeping Giant*):

| Species | Weight | Levels |
| --- | --- | --- |
| Spearow | 25 | 39–41 |
| Pidgeotto | 25 | 40–42 |
| Raticate | 20 | 40–42 |
| Fearow | 15 | 41–43 |
| Rattata | 15 | 38–40 |

**Rock Tunnel** (`Route` "rock_tunnel", a dungeon of 3 rooms from the
Route 10 Pokémon Center to Lavender Town: 1F, B1F, then the south 1F;
needs Flash). It's **pitch dark** (`Theme.dark`): the screen is black
except for Flash's light, a circle of 92 px around the player fading out
over 40 px and flickering a little (`overworld._darkness`); wild groups
and trainers outside it can't be seen (trainers' names still show).
B1F's last stairs are guarded by the **Hiker Crew** (Onix 36, Machop 34 ×2,
Geodude 34; a trainer battle, ₽595, a chest with `MID_BOSS` loot).
Win rate in `tools/balance_sim.py` for three at Lv33 + Lv32: about 88%
(Charmander's teams about 70%: Rock Tunnel is hard on Fire, as in
Red/Blue).

| Species | Weight | Levels |
| --- | --- | --- |
| Zubat | 35 | 30–33 |
| Geodude | 30 | 30–33 |
| Machop | 20 | 31–33 |
| Onix | 15 | 31–34 |

**Gyms** are fought in waves. The gym is a short walk (one map,
`Route.cols` tiles plus the arena) up to an arena where the gym's band
stands. Touching it opens the team pick (`scenes/gym.TeamPick`): the
player picks **2 Pokémon** (`Route.wave_team`; fewer if fewer are
standing) to fight every wave. The waves (`Route.waves`, `Wave`) then
come one battle straight after another, ending with the boss group:
- **no healing in between**: HP, status and fainted members carry over
  (stat stages and the like reset with each battle), and only the two
  picked fight, earn XP and can level up or evolve;
- each wave is a trainer battle (no running, trainer XP) with its own loot
  roll and prize; the last also brings the boss loot and prize;
- losing any wave is losing the gym: back to the last town, as when the
  party faints.

**The Vermilion Gym's puzzle** (`Route.puzzle` "trash_cans",
`scenes/power_grid.PowerGrid`; Red/Blue's trash cans, with a few twists):
an **electric fence** (two hazard-striped pylons, crackling arcs, a lock
box with a red light per lock) stands 7 tiles before the arena's band and
holds the player back. 8 **trash cans** stand along the walk; Up at one
rummages in it (its lid comes off):
- the **first switch** is in any can (picked from the trip's seed), and
  that can gives off a little **spark** every 2.6 s (for 0.3 s): a clue
  for the watchful;
- the **second switch** is always in a can **right next to** the first;
- an empty can before the first switch is found holds **junk** (a random
  line: "Dog tags reading \"Pvt. Pikachu\"", "a note: \"The switches are
  NOT in the trash cans. - Lt. Surge\"", ...);
- after the first, the wrong neighbour hides a **Voltorb** (Lv27): it
  jumps out, a wild battle (it stands there as a group if you run), and
  **both switches move** (all lids back on). The waves after it come with
  no healing, so a miss costs;
- both switches flipped: the fence shuts off, and stays off for good
  (`Game.trainers` "puzzle:vermilion_gym"). Up at the fence reads its
  sign ("DANGER: 10,000 VOLTS. Two switches cut the power." / "Hid 'em
  where nobody'd ever look. Ha! - Lt. Surge").

**The Rocket Hideout's spinner floors** (`Room.puzzle` "spinners:b2" /
"spinners:b3", `world/spinners.py`, `scenes/spinners.SpinnerFloor`):
after Red/Blue's arrow mazes, on B2F (42 tiles) and B3F (52 tiles), from
20 tiles into the room. The floor is covered in pads, and a **catwalk**
(one-way platforms) runs **5 tiles** over it, with gaps: too high to jump
up to (a full jump is under 4).
- **Arrow pads** (yellow chevrons): stepping or landing on one carries the
  player along its way at **210 px/s**, out of control (idle pose), until
  a **stop pad** (red) or a wall. Other arrows on the way turn them (more
  than 8 turns in one slide stop it). Carried off the catwalk's end, they
  keep going as they fall (about 5 tiles further).
- **Launch pads** (green, floor only): shoot the player straight up
  (500 px/s, about 110 px) onto the catwalk above; landing back on the pad
  it fired from doesn't fire it again.
- Arrow fields are 6+ tiles wide (wider than a jump clears from the
  floor); every arrow leads somewhere with a way on, so the player can't
  be trapped (layouts checked with a solver, and with the real physics).
  The way through: up, the right gaps, jumping over the catwalk's
  back-arrows, and a **running jump** off the catwalk's end past the last
  field (walking off lands on back-arrows that return you to a launch).
- No Pokémon, chests or platforms stand in the puzzle (2 tiles clear
  either side); the floor's Rocket bands are before and after it.

**The Celadon Gym's spores** (`Route.puzzle` "spores",
`scenes/spores.SporeGarden`): Erika's greenhouse is a longer walk (60
tiles) with trellis platforms, and **8 clouds of spores** drift over it,
from 12 tiles in to 9 tiles before the arena's band. They take turns:
Sleep Powder (blue), Poison Powder (violet) and Stun Spore (yellow), and
every other cloud **sweeps** to and fro along the floor (44 px either
way) or **rises and sinks** (its middle 14 px to 78 px over the floor),
each at its own pace (a cycle of 3.2–4.6 s).
- Walking into a cloud gives **a random party member** its status: one
  who has none and isn't immune (a Poison type to poison, an Electric type
  to paralysis). If nobody can take it, nothing happens. A line at the
  bottom of the screen says who ("Ivysaur breathed in the Sleep Powder!
  Ivysaur fell asleep!").
- The cloud then fades for **1.4 s** before it can strike again.
- The statuses carry into the gym's waves (no healing in between): cure
  them from the bag first, or jump over the low clouds, slip under the
  high ones and wait for gaps.

**The Power Plant's sparks** (`Route.puzzle` "sparks", the Thunder
Stone's quest) work the same way with balls of **loose current**: 8 of
them, all paralysing (Electric types are immune), drawn as crackling
yellow glows. The Leaf Stone's Overgrown Wing has the gym's spores.

The starters' **trials** (`instance._trial`, quest *Coming of Age* in
`quests.md`) work the same way, with one Pokémon (`wave_team=1`) that
must be of the starter's line (`Route.wave_species`), walked by talking
to the elder in Pewter City (`Route.folk`) and back to them.

**The Pewter Gym** (`Route` "pewter_gym", walked from the gym building;
a rock hall drawn in code, no wild Pokémon, no chests): three waves, the
last being the **Boulder Gang** (Geodude Lv14, Onix Lv16: Brock's team in
Gen 1, two levels up; the Onix leads it); beating it finishes the Boulder Badge quest.
Once it's done the gym stays shut ("You already have the Boulder Badge").

| Wave | Band | Team | Prize |
| --- | --- | --- | --- |
| 1 | Boulder Gang Diggers | Diglett 12, Sandshrew 12 | ₽120 |
| 2 | Boulder Gang Rollers | Geodude 13, Geodude 13 | ₽130 |
| 3 | Boulder Gang | Geodude 14, Onix 16 | ₽792 |

**The Cerulean Gym** (`Route` "cerulean_gym", the same way: an indoor pool
hall, drawn in code with a painted far wall; puddles on the tiles): the
**Cascade Crew**'s two waves, then the crew itself (Starmie Lv22, Staryu
Lv19: Misty's team in Gen 1, a level up; the Starmie leads it; tuned with
`tools/balance_sim.py` so that a Lv21/20 party wins about 78%, a
Charmander, Fire against Water, about 40%); beating it finishes
the Cascade Badge quest, and the gym then stays shut. Starmie evolves by
Water Stone (not in yet); `pokemon.LATER_FORMS` gives it Staryu's moves
and talents, at stage 1.

| Wave | Band | Team | Prize |
| --- | --- | --- | --- |
| 1 | Cascade Crew Swimmers | Goldeen 18, Psyduck 18 | ₽270 |
| 2 | Cascade Crew Divers | Horsea 19, Shellder 19 | ₽285 |
| 3 | Cascade Crew | Starmie 22, Staryu 19 | ₽940 |

Wild Pokémon have no gear. **Bosses and trainers' Pokémon wear gear**
(`loot.dress`, set up in `OverworldScene._battle`): a boss (the leader of
a boss group) **2 pieces**, its escorts and every trainer's Pokémon
(map trainers, gym waves, the rival) **1**, each in a different slot, a
random item at the enemy's level, at the area's rarities (`Route.boss_loot`
for boss battles, `Route.loot` for map trainers and gym waves). It works
as on the player's Pokémon (stats, effects, hats drawn, berries eaten),
and each piece can drop when it's beaten (see Loot). Their moves and talents are filled in for their level
(see `talents.md`), and each turn they pick at random between their
basic attack and their equipped moves, at a random target.

### Trainer battles

`game/scenes/battle.py` (`BattleScene.trainer`)

A route's boss group can be a trainer's team (`Route.trainer`), and
routes can have **trainers on their maps** (`Route.trainers`, `Trainer`).
There are no human trainers: each is a **band of Pokémon** with a name
("Crawler Swarm", "Rocket Gang") standing in for a Gen 1 trainer. Each stands where one of the map's wild groups would (spread out evenly,
always the same spot), with its team in a row.
- the battle opens with "<name> challenges you!" and **can't be run
  from**;
- its Pokémon give **trainer XP** (×0.45; wild ones ×0.15; see *Levels and XP*);
- the band's name shows above the team on the map;
- **prize money:** the base prize of the Gen 1 trainer class it stands in
  for × the level of its last Pokémon, **halved** like the shop's prices
  (`overworld.prize_money`): Bug Catcher 10, Youngster 15, Lass 15, Jr.
  Trainer 20, Team Rocket Grunt 30, Channeler 30, the rival 35, Hiker 35, Brock 99
  (Lv16 Onix → ₽792);
- map trainers fight **once**: beaten ones are saved (`Game.trainers`) and
  don't come back on later trips.

| Where | Band (Gen 1 class) | Team | Prize |
| --- | --- | --- | --- |
| Pewter Gym (boss) | Boulder Gang (Brock) | Geodude 14, Onix 16 | ₽792 |
| Cerulean Gym (boss) | Cascade Crew (Misty) | Starmie 22, Staryu 19 | ₽940 |
| Vermilion Gym (boss) | Thunder Battalion (Lt. Surge) | Raichu 31, Voltorb 29, Magnemite 29 (after its two waves, fought by three) | ₽1,534 |
| Celadon Gym (boss) | Blossom Troupe (Erika) | Vileplume 39, Victreebel 38, Tangela 37 (after its two waves: Oddish 35, Bellsprout 35, Gloom 36; Weepinbell 36, Exeggcute 36, Gloom 37; fought by three) | ₽1,831 |
| Route 3, map 1 | Alley Gang (Youngster) | Rattata 15, Ekans 15 | ₽112 |
| Route 3, map 1 | Crawler Swarm (Bug Catcher) | Caterpie 14, Weedle 14, Caterpie 14 | ₽70 |
| Route 3, map 2 | Pidgey Flock (Lass) | Pidgey 13, Pidgey 13 | ₽97 |
| Route 3, map 2 | Bug Brood (Bug Catcher) | Weedle 13, Kakuna 13, Caterpie 13, Metapod 13 | ₽65 |
| Route 3, map 3 | Lone Spearow (Youngster) | Spearow 18 | ₽135 |
| Route 3, map 3 | Singing Jigglypuff (Lass) | Jigglypuff 18 | ₽135 |
| Mt. Moon 1F | Stinger Nest (Bug Catcher) | Weedle 17, Kakuna 17 | ₽85 |
| Mt. Moon 1F | Moon Clefairy (Lass) | Clefairy 20 | ₽150 |
| Mt. Moon 1F | Cave Rats (Youngster) | Rattata 16, Rattata 16, Zubat 16 | ₽120 |
| Mt. Moon B1F (on the way) | Rockslide Clan (Hiker) | Geodude 16, Geodude 16, Geodude 16, Onix 17 | ₽297 |
| Mt. Moon B2F west (dead end) | Rocket Gang (Team Rocket Grunt) | Rattata 19, Zubat 19 | ₽285 |
| Mt. Moon B2F | Rocket Gang (Team Rocket Grunt) | Zubat 18, Ekans 18 | ₽270 |
| Mt. Moon B2F (boss) | Rocket Gang Leader (Team Rocket Grunt) | Sandshrew 18, Rattata 18, Zubat 19 | ₽285 |
| Route 4, map 1 | Hillside Pack (Lass) | Spearow 19, Rattata 19, Ekans 19 | ₽142 |
| Route 4, map 2 | Dune Diggers (Hiker) | Sandshrew 20, Sandshrew 20 | ₽200 |
| Nugget Bridge, map 1 | Bridge Crawlers (Bug Catcher) | Caterpie 20, Weedle 20, Metapod 20 | ₽100 |
| Nugget Bridge, map 1 | Bridge Flock (Lass) | Pidgey 20, Nidoran F 20 | ₽150 |
| Nugget Bridge, map 1 | Bridge Rats (Youngster) | Rattata 20, Ekans 20, Zubat 20 | ₽150 |
| Nugget Bridge, map 1 | Bridge Thorns (Lass) | Nidoran F 21, Nidoran M 21 | ₽157 |
| Nugget Bridge, map 2 | Bridge Champs (Camper) | Sandshrew 22, Spearow 22 | ₽220 |
| Nugget Bridge, map 1 | Rival | Pidgeotto 19, Abra 16, Rattata 16, starter's next form 20 | ₽500 |
| Nugget Bridge (boss) | Rocket | Ekans 23, Zubat 22 (gives the Nugget, once) | ₽330 |
| Route 25, map 1 | Hill Hikers (Hiker) | Geodude 21, Geodude 21, Onix 21 | ₽367 |
| Route 25, map 1 | Picnic Party (Picnicker) | Pidgey 21, Nidoran F 21, Nidoran M 21 | ₽157 |
| Route 25, map 2 | Camping Crew (Camper) | Rattata 22, Ekans 22, Spearow 22 | ₽165 |
| Route 25, map 2 | Garden Club (Lass) | Oddish 22, Bellsprout 22 | ₽165 |
| Burgled House (boss) | Rocket Gang (Team Rocket Grunt) | Mankey 24, Abra 22, Zubat 22 | ₽330 |
| Route 6, map 1 | Meadow Swarm (Bug Catcher) | Butterfree 24, Beedrill 24 | ₽120 |
| Route 6, map 1 | Pond Pals (Jr. Trainer) | Psyduck 24, Goldeen 24 | ₽240 |
| Route 6, map 2 | Spark Squad (Jr. Trainer) | Pikachu 25, Rattata 25, Raticate 24 | ₽240 |
| Route 6, map 2 | Thicket Crawlers (Bug Catcher) | Venonat 25, Paras 25, Metapod 25 | ₽125 |
| Route 11, map 1 | Engine Crew (Engineer) | Magnemite 29, Voltorb 29 | ₽725 |
| Route 11, map 1 | Roadside Gang (Youngster) | Rattata 28, Ekans 28, Zubat 28 | ₽210 |
| Route 11, map 2 | High Rollers (Gambler) | Horsea 29, Goldeen 29, Shellder 28 | ₽980 |
| Route 11, map 2 | Rolling Stones (Engineer) | Geodude 29, Onix 30 | ₽750 |
| Route 11, map 2 | Sleepy Heads (Youngster) | Drowzee 30, Drowzee 29, Jigglypuff 29 | ₽217 |
| Route 9, map 1 | Meadow Duo (Jr. Trainer) | Oddish 31, Bellsprout 31 | ₽310 |
| Route 9, map 1 | Boulder Bunch (Hiker) | Geodude 31, Machop 31, Geodude 31 | ₽542 |
| Route 9, map 2 | Silk Spinners (Bug Catcher) | Butterfree 32, Beedrill 32 | ₽160 |
| Route 9, map 2 | Roadside Pals (Jr. Trainer) | Pidgeotto 32, Raticate 31, Nidorino 31 | ₽310 |
| Route 9, map 2 | Mountain Men (Hiker) | Onix 33, Machop 32 | ₽560 |
| Rock Tunnel 1F | Pick and Shovel (Hiker) | Geodude 32, Geodude 32, Onix 32 | ₽560 |
| Rock Tunnel 1F | Collector's Pride (Pokémaniac) | Clefairy 32, Psyduck 32 | ₽800 |
| Rock Tunnel B1F | Lost Hikers (Jr. Trainer) | Jigglypuff 33, Pidgeotto 33 | ₽330 |
| Rock Tunnel B1F | Rubble Rousers (Hiker) | Machop 33, Geodude 33, Machop 33 | ₽577 |
| Rock Tunnel B1F (boss) | Hiker Crew | Onix 36, Machop 34, Machop 34, Geodude 34 | ₽595 |
| Rock Tunnel 1F (south) | Tunnel Twins (Jr. Trainer) | Oddish 33, Bellsprout 33 | ₽330 |
| Route 8, map 1 | Lucky Streak (Gambler) | Growlithe 34, Meowth 34 | ₽1,190 |
| Route 8, map 1 | Pretty Pals (Lass) | Clefairy 34, Jigglypuff 34, Nidorina 33 | ₽247 |
| Route 8, map 2 | Gadget Nerds (Super Nerd) | Magnemite 35, Voltorb 35, Magnemite 35 | ₽437 |
| Route 8, map 2 | Twin Tails (Twins) | Nidoran F 35, Nidoran M 35 | ₽350 |
| Route 16, map 1 | Road Hogs (Biker) | Raticate 41, Fearow 41 | ₽820 |
| Route 16, map 2 | Exhaust Pipes (Biker) | Koffing 41, Grimer 41, Koffing 41 | ₽820 |
| Celadon West End | Snack Pack (Snorlax, woken) | Snorlax 48, Persian 42, Primeape 42, Raticate 42 | ₽0 |
| S.S. Anne 1F | Gentleman's Hounds (Gentleman) | Growlithe 26, Growlithe 26 | ₽910 |
| S.S. Anne 1F | Seaside Lass (Lass) | Pidgey 25, Nidoran F 25, Jigglypuff 25 | ₽187 |
| S.S. Anne 1F | Cabin Boys (Youngster) | Rattata 25, Ekans 25, Raticate 24 | ₽180 |
| S.S. Anne B1F | Deckhands (Sailor) | Machop 26, Shellder 26 | ₽390 |
| S.S. Anne B1F | Bosun's Crew (Sailor) | Machop 26, Tentacool 26, Horsea 26 | ₽390 |
| S.S. Anne B1F | Fishing Party (Fisherman) | Goldeen 25, Tentacool 25, Staryu 25 | ₽437 |
| S.S. Anne 2F | First Class (Gentleman) | Pikachu 28, Growlithe 27 | ₽945 |
| S.S. Anne 2F | Ballroom Belles (Lass) | Jigglypuff 26, Clefairy 26 | ₽195 |
| S.S. Anne 2F (boss) | Rival | Pidgeotto 22, Raticate 19, Kadabra 18, starter's next form 22 | ₽385 |
| Route 22 (boss) | the rival | Pidgey 7, starter 6 | ₽105 |
| Rocket Hideout B1F (blocks the way) | Poster Guard (Team Rocket Grunt) | Raticate 37, Zubat 37 | ₽555 |
| Rocket Hideout B1F | Rocket Gang (Team Rocket Grunt) | Koffing 37, Grimer 37, Ekans 37 | ₽555 |
| Rocket Hideout B1F | Rocket Gang (Team Rocket Grunt) | Machop 38, Drowzee 38 | ₽570 |
| Rocket Hideout B2F | Rocket Gang (Team Rocket Grunt) | Golbat 38, Arbok 38 | ₽570 |
| Rocket Hideout B2F | Rocket Gang (Team Rocket Grunt) | Raticate 38, Koffing 38, Zubat 37 | ₽555 |
| Rocket Hideout B3F | Rocket Gang (Team Rocket Grunt) | Machoke 39, Grimer 38 | ₽570 |
| Rocket Hideout B3F | Rocket Gang (Team Rocket Grunt) | Drowzee 39, Koffing 39, Ekans 38 | ₽570 |
| Rocket Hideout B4F (blocks the lift; the boss loot) | Lift Key Guard (Team Rocket Grunt) | Koffing 40, Golbat 40, Raticate 40 | ₽600 |
| Rocket Hideout B4F | Rocket Gang (Team Rocket Grunt) | Hypno 39, Arbok 39 | ₽585 |
| Pokémon Tower 2F (blocks the way; the boss loot) | Rival | Pidgeotto 40, Growlithe 39, Kadabra 39, starter's next form 42 | ₽735 |
| Pokémon Tower 3F | Channeler's Spirits (Channeler) | Gastly 39, Gastly 39 | ₽585 |
| Pokémon Tower 3F | Channeler's Spirits (Channeler) | Haunter 40 | ₽600 |
| Pokémon Tower 4F | Channeler's Spirits (Channeler) | Gastly 40, Cubone 39, Gastly 39 | ₽585 |
| Pokémon Tower 4F | Channeler's Spirits (Channeler) | Haunter 40, Gastly 40 | ₽600 |
| Pokémon Tower 5F | Channeler's Spirits (Channeler) | Haunter 41, Haunter 40 | ₽600 |
| Pokémon Tower 5F | Channeler's Spirits (Channeler) | Cubone 41, Gastly 41 | ₽615 |
| Pokémon Tower 6F (blocks the stairs) | Restless Spirits (Marowak's ghost) | Marowak 50, Haunter 44, Gastly 44, Haunter 44 | – |
| Pokémon Tower 7F (boss) | Rocket Gang (Team Rocket Grunt) | Arbok 43, Golbat 42, Koffing 42, Raticate 42 | ₽630 |
| Rocket Hideout, Boss's Office (boss) | Rocket Boss (Giovanni) | Persian 43, Onix 41, Rhyhorn 41, Kangaskhan 42 (fought by three: won about 78% at Lv40/39 with 3 Hyper Potions and a Revive, `tools/balance_sim.py`) | ₽2,079 |

---

## The Battle Tower

`game/world/tower.py`, `game/scenes/battle_tower.py`

Celadon's west end has the Battle Tower, open once the Rainbow Badge is won
(`tower.OPENS_AFTER`; always in dev mode). It's meant for the end of the
story and after it. Its lobby is a marble hall where **Mew** floats. Up at
Mew opens its menu: Climb, the gem exchange (gear or Pokémon), how the
tower works, and Leave. Up at the stairs also starts a climb.

- **25 floors**, in five tiers of five. Each floor is a short hall up to an
  arena, fought like a gym: pick the team (as many as the party's places),
  then **waves** of challengers one after another, then the floor master's
  band. Every run **starts on floor 1**, and Mew heals the team first.
- **Gates:** floors 1–5 open with the tower (the Rainbow Badge, the 4th
  badge). The next fives need more badges, in any order
  (`tower.GATES`, `top_floor`): floors 6–10 at 6 badges, 11–15 at 7 and
  16–20 at all 8. Floors 21–25 open once you're the Champion
  (`tower.LEAGUE`). In dev mode every floor is open. On the last open
  floor, the way up is sealed and you can only claim the chest.
- **No healing** between waves or floors. Losing any battle ends the run
  with **nothing**: back to the last town, no chest.
- After each floor's master, choose: **climb on** to the next floor, or
  **stop and claim the chest**. After floor 25 (or the last open
  floor) you can only claim. X
  puts the choice off, and Up at the arena's doorway asks again.
- **XP:** trainer XP (×0.45), split as usual. There are **no drops**
  (loot, worn gear) and **no prize money** (`BattleScene.drops=False`).
- **Saving:** a run isn't saved. A save in the lobby or on a floor is a
  save outside the tower's doors (`battle_tower.lobby_location`).

| Tier | Floors | Look | Waves + master | Band (master's) | Talents | Gear worn (pieces; master +1) |
| --- | --- | --- | --- | --- | --- | --- |
| Marble Halls | 1–5 | marble and gold | 2 + 1 | 3 (4) | half | 1: Common 3 / Uncommon 2 |
| Sky Gardens | 6–10 | ruins in the clouds | 3 + 1 | 3 (4) | half | 1: Uncommon 3 / Rare 1 |
| Storm Spire | 11–15 | lightning and crystals | 3 + 1 | 4 (5) | all | 2: Uncommon 1 / Rare 3 / Epic 1 |
| Celestial Summit | 16–20 | the edge of space | 4 + 1 | 4 (5) | all | 2: Rare 2 / Epic 3 |
| Eclipse Throne | 21–25 | black and gold under an eclipse | 4 + 1 | 5 (6) | all | 3: Rare 1 / Epic 5 |

- **Levels:** each tier starts a few levels below the party's expected
  level when it opens (Lv38 after the Celadon Gym, about 48 at 6 badges,
  52 at 7, 56 at 8 and 63 as Champion) and climbs a level a floor
  (`tower.TIER_LEVELS`): floors 1–5 Lv32–37, 6–10 Lv44–48, 11–15 Lv49–53,
  16–20 Lv54–58 and 21–25 Lv60–65. Challengers are 1 below that (or 2), and
  masters 1 above (or 0). (3 lower since the gear rework: a geared team of
  three at the floor's old level wins about 88% on floor 1, 75% on floor 5,
  58% on floors 6–8 and 88% on floor 10.)
- **Pools:** each tier draws from its own pool of strong evolved Pokémon
  (`tower.POOLS`, no legendaries): Pidgeot, Machoke and Kadabra low down;
  Arcanine, Nidoking, Dragonair and Scyther next; then Alakazam, Golem,
  Machamp, Gengar and Gyarados; then Aerodactyl, Lapras and the three
  starters' final forms; and at the top Dragonite with the strongest of all.
  The bands are the same every run, as each floor is seeded by its number.
- **Giant masters:** every fifth floor's master is drawn twice as big and
  leads the tier's strongest: Nidoking (floor 5, Lv42), Gengar (10, Lv53),
  Gyarados (15, Lv58), Aerodactyl (20, Lv63) and Dragonite (25, Lv70).

**The chest** (`tower.chest`) after clearing floors 1 to *f*:
- **gems:** 2 of each cleared floor's gem, 3 more on every fifth floor.
  Quartz comes from floors 1–5, Jade 6–10, Sapphire 11–15, Ruby 16–20 and
  Diamond 21–25. Stopping at floor 25 gives 13 of each;
- 1 + ⌊*f*/4⌋ Hyper Potions, ⌊*f*/5⌋ Revives (from floor 5), ⌊*f*/8⌋ Max
  Potions (from 8) and ⌊*f*/12⌋ Full Restores (from 12);
- 1 + ⌊*f*/5⌋ pieces of gear at the floor's level (Lv60 at most), with
  rarities by tier, Epic at most: Uncommon 3 / Rare 1, Uncommon 1 / Rare 3,
  Rare 3 / Epic 1, Rare 1 / Epic 3, and Epic only.

**Mew's gem exchange:**

| Gear for 12 gems | Rarity | Item level |
| --- | --- | --- |
| Quartz | Uncommon | 40 |
| Jade | Rare | 47 |
| Sapphire | Rare or Epic (half each) | 55 |
| Ruby | Epic, with a **60%** chance of a special effect (Epic's own is 20%) | 60 |
| Diamond | Epic, always with a special effect, every bonus at its best roll | 60 |

You pick the slot (Left/Right) and Mew rolls the piece: a random item for
that slot at that rarity, with random affixes.

| Pokémon (each once, `Game.trainers` "mew:<species>") | Level | Price |
| --- | --- | --- |
| Dratini | 30 | 20 Jade |
| Chansey | 35 | 20 Sapphire |
| Lapras | 40 | 25 Ruby |
| Aerodactyl | 50 | 25 Diamond |

A bought Pokémon joins the party if it has room, or else the reserve.

The bag keeps the gems (`Bag.gems`, shown in the Key items pocket), and
`Game.tower_best` keeps the highest floor cleared (shown in the lobby).

---

## Dev mode

`game/dev.py` (switched on in the pause menu, for testing; never part of a save)

- **Password:** switching it on the first time asks for a password
  (`dev.PASSWORD`; `scenes/dev_menu.PasswordPrompt`): typed on a
  keyboard (Enter checks it), or picked letter by letter without one
  (Up/Down, Space adds, Left deletes, "OK" checks). Esc cancels.
- **Remembered:** once the password is given, that machine or browser
  doesn't ask again. Dev mode's on/off and its settings (XP boost, God
  mode, Skip packs) come back on the next start too. They're kept in the
  player's settings (`saves/settings.json`, key "dev", `DevMode.prefs` /
  `configure`), which in the browser live in its localStorage.

- **XP boost** ×3/×5/×10/×20 multiplies the total XP of a won battle
  before it's shared out, and a quest's XP.
- **God mode:** hits on the party deal 0 damage and burn/poison don't hurt
  it (statuses still land); every hit on an enemy deals exactly its
  remaining HP, and Endure can't save it.
- **Skip packs:** walking into a wild pack or a map trainer's band
  (blocking ones too: the rival on Nugget Bridge, the hideout's guards)
  starts no battle: the player walks straight through. Bosses (an area's
  end group, a gym's arena, a dungeon room's boss) still fight, as they
  guard the way out. Skipped trainers stay unbeaten, so quest steps that
  need them aren't done.
- **Teleport** (Left/Right: town, Enter: go) takes the party to any town,
  arriving as after fainting (healed; it becomes the town you wake up in).
- **Add item** rolls gear with `Gear.roll(..., affixes=[...], values=...)`:
  the chosen affixes (any number, 0–5, regardless of rarity), and every
  value random, lowest or highest of its range (then × rarity as usual),
  and its special effect: Random (rolled as usual), none, or any one
  (`effect=`, regardless of rarity).

---

## Sky battles

`game/mechanics/sky.py`; `BattleScene(sky=True)`

The rules of the "Learn to Fly" trial. A **flier** is a Flying-type party
member (enemies are never fliers). Fliers hover above their place in line.

- **Sky command** (in place of Run, as a trial can't be fled), for fliers
  only:
  - **Fly**: Flying, 90 power, 95% accurate. The first round the user flies
    up high: every attack aimed at it, status moves too, misses ("out of
    reach"). The next round it strikes.
  - **Perch**: always goes first; the user lands and heals 1/8 of its max HP.
    While perched, it isn't Flying (Ground moves hit it; a pure Flying type
    counts as Normal) and its wings don't tire. It takes off again when it
    next uses any other move.
- **Wind**: a new wind every round (never the same twice in a row), on the
  fliers only. The next round's wind is shown in the top-right corner,
  so the player can plan ahead.

  | Wind | Weight | Effect on fliers |
  | --- | --- | --- |
  | Calm | 30 | none |
  | Tailwind | 25 | Speed ×1.5; Flying moves' power ×1.3 |
  | Headwind | 25 | Speed ×2/3; chance to hit ×0.85 |
  | Updraft | 20 | Fly strikes at once (no round up high) |

- **Wing fatigue**: at the end of every round, each flier that isn't
  perched loses 1/16 of its max HP (at least 1), after the other
  round-end damage.

---

## Types

`game/mechanics/type_chart.py`

The 15 Gen 1 types and the Gen 1 chart as intended, with one fix: Ghost is
**super effective** against Psychic (the original games had a bug that
made it have no effect). Against a Pokémon with two types, the two
multipliers are multiplied together.
