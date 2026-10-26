# Game mechanics

How the numbers work: stats, levels and XP, damage, status conditions,
gear rolls, items and loot. Keep this file in step with the code: when a
rule or a number changes, update the section here too.

Most rules follow Gen 1 (Red/Blue), simplified, with gear on top. Where
the game deliberately differs from Gen 1, that's called out.

---

## Stats

`game/mechanics/pokemon.py` (`Monster`)

Each species has four Gen 1 base stats: HP, Attack, Defense and Speed.
There's no Special stat, no IVs/EVs and no natures. Its stats at level
`L` are worked out using whole-number division (`//`, rounding down):

| Stat | Formula |
| --- | --- |
| Max HP | `base_hp × 2 × L // 100 + L + 10` |
| Attack, Defense, Speed | `base × 2 × L // 100 + 5` |

Example: Bulbasaur (45 / 49 / 49 / 45) at Lv5 has 19 HP and 9 Attack.

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
  Pidgey 55, Bulbasaur 64, Lapras 219). This is Gen 1's formula for wild
  Pokémon.
- **Sharing:** after a won battle, the XP of **all** enemies is added up,
  and **every party member still standing gets the full amount** (no
  splitting). Fainted members get nothing. *Gen 1 split XP between the
  Pokémon that took part.*
- **Level up:** stats are recalculated at once. Max HP goes up, and the
  HP gained is added to current HP (damage taken stays the same).
  Several level-ups from one battle are possible.

Example: beating Lv6 Pidgey (47), Lv7 Rattata (57) and Lv5 Pidgey (39)
gives 143 XP to each party member still standing.

---

## Evolution

`game/mechanics/pokemon.py` (`EVOLUTIONS`, `Monster.evolve`),
`game/scenes/battle.py` (`_evolve`)

Pokémon evolve **by level**, at the levels from Red/Blue. Trade and stone
evolutions aren't in yet.

- **When:** at the end of a won battle, after the XP, for each party member
  that **leveled up in that battle** and is at or above its evolution
  level. Its sprite flashes white between the two forms, faster and
  faster.
- **Stopping it:** pressing **X** during the flashing stops the evolution
  (B in Red/Blue). It tries again the next time that Pokémon levels up.
- **What changes:** the species, and with it base stats, types, sprite,
  XP yield and its part of the skill tree (see `skill_trees.md`). The
  level, XP, skills, gear and status stay. Stats are
  recalculated, and the HP gained is added to current HP (damage taken
  stays the same).
- **Only into species that are in the game:** an evolution is skipped
  while its species isn't defined yet (e.g. Spearow won't evolve until
  Fearow is added). The full table is already registered.

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

**Bold** = in the game now. Seel → Dewgong can happen once Seel is in the
party (Dewgong exists as a placeholder species).

---

## Damage

`game/mechanics/combat.py` (`damage`), applied in
`game/scenes/battle.py` (`_apply`)

Moves only miss when the user's **accuracy** has been lowered (see *Stat
stages*). A hit is worked out in these steps:

1. **Attack:** the user's Attack (with gear) × its **Attack stage**
   multiplier (see *Stat stages*). Halved if the user is **burned**.
2. **Power:** the move's power × its **skill rank** (+15% per rank after
   the first: R5 = ×1.6), + the user's gear `power` bonus. Fight uses the
   Pokémon's basic attack (see `skill_trees.md`).
3. **Base damage** (the Gen 1 formula):

   ```
   base = (2 × L / 5 + 2) × power × attack / defense / 50 + 2
   ```

   `L` is the user's level, `defense` the target's Defense with gear ×
   its **Defense stage** multiplier.
4. **Critical hit:** a 6.25% chance (1 in 16) × the move's crit ratio
   (×8 for Razor Leaf, Gen 1's "high critical-hit ratio": 50%), plus the
   user's gear `crit` in percentage points (e.g. +5 → 11.25%). A crit
   multiplies `base` by **×1.5** (Gen 2+ style; *not* Gen 1's level-based
   crits).
5. **Leaf Shield:** if the target is shielded, `base` × **0.5**.
6. **Random spread:** `base` × a random number from 0.85 to 1.0, × the
   move's share if it hits several targets (Whirling Leaves: 0.75).
7. **Type effectiveness:** × the type chart multiplier for the move's type
   against each of the target's types (multiplied together: 0, ¼, ½, 1,
   2 or 4). Typeless moves are always ×1.
8. **Same-type bonus (STAB):** × **1.5** if the move's type is one of the
   user's types.
9. **Type power gear:** × `(1 + power:<type> / 100)` for the move's type
   (e.g. Charcoal, "of the Moltres").
10. **Super-effective gear:** if the hit is super effective, × `(1 + super / 100)`
    (Expert Belt, Mortarboard).
11. The result is rounded, with a minimum of **1**, or **0** if the
    target is immune (×0).

Steps 7–10 all multiply together; their order doesn't matter.

**Added type damage** (gear `added:<type>`, e.g. "Blazing" = Fire): every
damaging hit also deals `round(base × added% / 100 × effectiveness)` extra
damage of that type. `base` here is the value after step 6, so crits and
Leaf Shield count, but STAB and type power don't. Effectiveness is that of
the *added* type against the target, so it can be super effective even
when the move itself isn't, and it still deals damage when the move's type
has no effect. Each added type shows as its own coloured number.

**Total damage** = main hit + all added damage, capped at the target's
remaining HP.

### Worked example

Lv10 Bulbasaur (Attack 14, no gear) uses Tackle (Normal, 35) on Lv10
Pidgey (Defense 13):

```
base = (2×10/5 + 2) × 35 × 14 / 13 / 50 + 2 = 6 × 35 × 14 / 650 + 2 ≈ 6.52
spread: 5.54 … 6.52
Normal vs Normal/Flying = ×1, no STAB (Bulbasaur is Grass/Poison)
→ 6 or 7 damage (crit: 8–10)
```

At Tackle rank 3 the power is 35 × 1.3 = 45.5, so `base` ≈ 8.2 → 7–8.

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
- **Berries:** the target (and the user, after recoil) may eat its berry
  right after the move (see *Berries*).

### Moves that aren't attacks

- **Status moves** that inflict a status or confusion work with their
  Gen 1 chance (Poison Powder, Sleep Powder, Stun Spore, Lovely Kiss 75%;
  Sing, Supersonic 55%; Thunder Wave, Confuse Ray 100%), unless the
  target already has a status or its type is immune. Every other status
  move always works.
- **Immune types:** Leech Seed doesn't affect Grass types, Thunder Wave
  doesn't affect Ground types.
- **Stat stages** (Growl, Growth, Sand-Attack, ...): see *Stat stages*.
- **Leech Seed:** the target is seeded; see *End of round*.
- **Leaf Shield:** the target takes half damage for its rounds.
- **Focus Energy:** the user's crit chance ×4 for the rest of the battle
  (Gen 1's intended effect; its real one was a bug).
- **Rest:** the user's status is cured, it heals fully, and it falls
  asleep for exactly 2 turns.
- Moves that **hit every target** (Growl R2, Spreading Seeds, ...) need no
  target choice and work on each Pokémon on that side.

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

Growl lowers Attack, Growth raises Attack (and Defense at R3), Poison
Powder R2/R3 lowers Speed, a Liechi Berry raises Attack.

**Accuracy** is only ever lowered (Sand-Attack, Smokescreen): a Pokémon
with lowered accuracy hits with a chance of its multiplier (−1: 2/3, −6:
1/4), whatever move it uses. Swift and Aerial Ace ignore it.

### Turn order

`game/scenes/battle.py` (`_run_round`)

Each round, everyone picks first, then all actions play out in this order:

1. **Items** (medicine) before any move.
2. Then moves with **priority** (Quick Attack, and moves given it by a
   modifier) before the rest.
3. Then Pokémon whose **"act first"** gear roll succeeded (`first`: Quick
   Claw, Officer's Cap, "Hasty"; rolled every round).
4. Then **fastest first** by Speed (with gear, × its Speed stage
   multiplier; **halved if paralyzed**).
5. Ties are settled at random.

**Solar Beam** spends one round charging and hits the next (unless Quick
Bloom). After **Hyper Beam** the user must rest the next round.

### End of round

After all actions, in this order:

1. **Burn and poison damage** (see below), then berries may be eaten.
2. **Leech Seed:** each seeded Pokémon loses its seed's share of its max
   HP (1/16; 1/12 or 1/8 at higher ranks; min 1), and whoever seeded it
   gets that much back (if it's still standing).
3. **Bind:** bound Pokémon lose their bind's share of max HP (min 1).
4. **Regen** (gear `regen`: Leftovers, Nightcap, "of the Chansey"): heals
   `regen`% of max HP (min 1).
5. **Leaf Shield** counts down: it lasts the round it's used and the next
   (and more at higher ranks). Flinching wears off.

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
party members skip the menu.

---

## Healing

- **Towns** fully heal the party (HP and status) on arrival. This is a
  stand-in for Poké Centers and Mom's house.
- **Medicine** (`game/mechanics/items.py`, `MEDICINE`) is used from the
  battle's Item menu. It takes the user's turn, and is only used up if
  it has an effect.

| Medicine | Effect |
| --- | --- |
| Potion / Super Potion / Hyper Potion | +20 / +50 / +200 HP |
| Max Potion | Full HP |
| Full Restore | Full HP and cures any status |
| Revive | A fainted Pokémon comes back with half its max HP (rounded up) |
| Antidote / Burn Heal / Paralyze Heal / Awakening / Ice Heal | Cures that one status |
| Full Heal | Cures any status |

### Berries

Berries are eaten **at most once per battle** and are **not used up** (the
same berry works again next battle). They're checked at the start of
battle, after being hit, and after burn/poison damage. A berry is only
eaten when it does something:

| Berry | When | Effect |
| --- | --- | --- |
| Oran Berry | HP at or below 1/2 | Heals `berry_heal`% of max HP (rolled 20–25% at Common) |
| Liechi Berry | HP at or below 1/4 | Attack stage +1 at Common, +2 at Rare and up (not above +6) |
| Pecha / Rawst / Cheri / Chesto / Aspear | Has that status | Cures poison / burn / paralysis / sleep / freeze |
| Lum Berry | Has any status | Cures it |

---

## Gear

`game/mechanics/items.py`

Each Pokémon has four slots: **Head** (hats, drawn on the Pokémon),
**Held**, **Worn** and **Berry**. A piece of gear is an item at a rarity and
an **item level**, plus its rolls.

**Starting gear:** the starter (Bulbasaur, Charmander or Squirtle, chosen
at the start, Lv5) holds a Common Oran Berry (heals 20–25% of max HP at
half HP, once per battle); the bag starts without gear.

### Item level

- A piece's **item level** is the level needed to **equip** it: the
  Pokémon's level must be at least the item level. (The party screen lists
  gear it can't use yet greyed out, with the level in red.)
- Dropped gear gets the **defeated Pokémon's level**; chest gear a level in
  the area's range (its Pokémon's lowest to highest level; a boss chest:
  the boss group's highest level).
- Item level makes **stat, power and damage bonuses** bigger: × `1 + 0.04 ×
  (item level − 1)` (Lv1 ×1, Lv11 ×1.4, Lv26 ×2, Lv51 ×3). These are `hp`,
  `attack`, `defense`, `speed`, `power`, `power:<type>`, `added:<type>`
  and `super`. **Chances** (crit, act first, endure, status), regen, drain
  and berry effects only grow with rarity.
- So newer gear of a lower rarity can beat older gear of a higher one.
  Muscle Band (Attack +8…12%) at its highest roll: Common Lv5 +14%, Rare
  Lv10 +24%, Common Lv25 +24%, Uncommon Lv35 +35%, Epic Lv10 +33%.

### Rolling a piece (`Gear.roll`)

1. **The item's own effect** is rolled from its range (e.g. Red Bandana:
   Attack +8…12%).
2. **Affixes:** Head, Held and Worn items get the number of affixes their
   rarity gives (Common none). Berries get none. Affixes are picked by weight without
   repeats (normal affixes weight 3; Hasty, Draining and of the Chansey 2;
   type and status affixes 1).
3. **Each value** is rolled as a whole number in its range, then:
   - a **bonus** (positive) is × the rarity factor (and × the item-level
     factor if it's a stat, power or damage bonus), rounded, min 1
     (Python rounds .5 to the even number: 7.5 → 8, but 2.5 → 2);
   - a **penalty** (negative, e.g. Power Bracer's Speed −10%) stays as it is.
4. **Name:** the first prefix + item + the first suffix ("Fierce Red Bandana
   of the Aerodactyl"). Further affixes still count but aren't in the name.

Affixes can stack on the same stat as the item (a Fierce Red Bandana has
two Attack rolls), and all rolls simply add up.

| Rarity | Factor | Affixes | Where it drops (for now) |
| --- | --- | --- | --- |
| Common (white) | ×1.0 | 0 | everywhere |
| Uncommon (green) | ×1.25 | 1 | boss groups (from the second area on) |
| Rare (blue) | ×1.5 | 2–3 | not yet (mid game) |
| Epic (purple) | ×2.0 | 3–4 | not yet (late game) |
| Legendary (orange) | ×2.5 | 4–5 | not yet (end game) |

Example: Muscle Band (Attack +8…12%) at Legendary Lv1 rolls 8…12 × 2.5 =
Attack +20…30%.

### What gear can do (mods)

| Mod | Meaning |
| --- | --- |
| `hp`, `attack`, `defense`, `speed` | % on that stat (see *Gear on stats*) |
| `crit` | + percentage points of crit chance (base 6.25%) |
| `power` | added to the power of damaging moves |
| `power:<type>` | % more damage with moves of that type |
| `added:<type>` | every hit deals this % extra as that type (see *Damage*) |
| `super` | % more damage on super-effective hits |
| `status:<status>` | % chance per hit to inflict that status |
| `first` | % chance per round to act before everyone else (after items) |
| `endure` | % chance to survive a knockout hit with 1 HP |
| `regen` | % of max HP healed at the end of each round |
| `drain` | % of damage dealt healed |
| `berry_heal` / `berry_attack` | berry effects (see *Berries*) |

### Affixes

Values at Common (before the rarity factor).

| Prefix | Mods | | Suffix | Mods |
| --- | --- | --- | --- | --- |
| Fierce | Attack +4…8% | | of the Machamp | Attack +4…8% |
| Sturdy | Defense +4…8% | | of the Onix | Defense +5…10% |
| Swift | Speed +4…8% | | of the Pidgeot | Speed +5…10% |
| Hearty | HP +4…8% | | of the Snorlax | HP +5…10% |
| Keen | Crit +2…4 | | of the Tauros | Attack +2…5%, Speed +2…5% |
| Mighty | Power +3…6 | | of the Golem | Defense +2…5%, HP +2…5% |
| Hasty | First 3…6% | | of the Scyther | Crit +1…3, Attack +2…4% |
| Draining | Drain 3…6% | | of the Hitmonlee | Power +2…4, Speed +2…4% |
| Blazing, Drenching, … (14 types, not Normal) | Added type damage 3…6% | | of the Chansey | Regen 2…3% |
| | | | of the Moltres, of the Gyarados, … (15 types) | Type power +5…10% |
| | | | of the Magmar / Muk / Pikachu | Burn / poison / paralysis chance 5…10% |
| | | | of the Hypno / Jynx | Sleep / freeze chance 3…6% |

Item stats are listed in `ITEMS` and `HATS` in `items.py`.

---

## Loot

`game/mechanics/loot.py`

A loot table rolls one or more times. Each roll picks one entry by
weight: nothing, some medicine, or a piece of gear (a random item, at a
rarity picked by weight, at an item level: see *Item level*).

- **Won battle:** the wild table is rolled **once per defeated enemy**, at
  that enemy's level.
- **Chest** on a map (Up): the chest table once (2–3 rolls).
- **Boss chest** (areas with a boss): the boss table once (3–4 rolls).

Which **rarities** can drop is set per area (`Route.loot` for wild
Pokémon and chests, `Route.boss_loot` for a boss group's drops and chest):

| Table | Rolls | Nothing | Medicine | Gear |
| --- | --- | --- | --- | --- |
| Wild (per enemy) | 1 | 55% | 33% (Potion 18%, Super Potion 4%, status cures 11%) | 12% |
| Chest | 2–3 | – | 67% (Potions 1–3, Revive, cures, ...) | 33% |
| Boss | 3–4 | – | 45% (Super/Hyper Potion, Revive, Full Heal/Restore) | 55% |

| Area | Wild and chests | Boss |
| --- | --- | --- |
| Route 1 | Common | (no boss) |
| Viridian Forest | Common | Common 60%, Uncommon 40% |
| Route 22 | Common | Common 60%, Uncommon 40% (the rival: a reward roll with the battle, no chest) |
| Default for new areas (`COMMON_ONLY` / `EARLY_BOSS`) | Common | Common 60%, Uncommon 40% |

---

## Wild Pokémon

`game/world/themes.py`, `game/world/level.py`

Each map theme has a weighted pool of species with level ranges. A wild
group has 1, 2 or 3 Pokémon (weights 60 / 30 / 10), each picked from the
pool, each at a random level in its entry's range. A **boss** (areas with
one) guards the last map's exit: the group the area names (`Route.boss_group`),
or else 4–5 Pokémon from the pool at the same levels; its leader (the
first) can be drawn bigger (`Route.boss_scale`).

Route 1 (Meadow pool):

| Species | Weight | Levels |
| --- | --- | --- |
| Pidgey | 30 | 2–4 |
| Rattata | 30 | 2–4 |
| Caterpie | 15 | 2–4 |
| Weedle | 15 | 2–4 |
| Oddish | 8 | 3–5 |
| Bellsprout | 8 | 3–5 |
| Pikachu | 3 | 3–5 |
| Bulbasaur | 1 | 4–5 |

Viridian Forest (3 maps, Viridian City → Pewter City; Red's and Blue's
forest Pokémon together):

| Species | Weight | Levels |
| --- | --- | --- |
| Caterpie | 25 | 3–5 |
| Metapod | 20 | 4–6 |
| Weedle | 25 | 3–5 |
| Kakuna | 20 | 4–6 |
| Pikachu | 5 | 3–5 |

**Boss:** a Lv10 Caterpie drawn at double size, escorted by a Lv8 Metapod
and a Lv8 Kakuna (only the leader, the first of a boss group, is drawn
bigger). Beating them opens the way to Pewter City and leaves a chest
(item level 10).

Route 22 (2 maps, from Viridian City and back):

| Species | Weight | Levels |
| --- | --- | --- |
| Rattata | 40 | 2–5 |
| Nidoran M | 25 | 2–4 |
| Nidoran F | 20 | 2–4 |
| Spearow | 15 | 3–5 |

Route 22 opens once the quest "Rival on Route 22" starts, and Viridian
Forest once "Oak's Parcel" is done (see `quests.md`).

**Boss:** the rival (a trainer battle, see below): Pidgey Lv9 and his
starter Lv8, Gen 1's first rival team. Once he's beaten (the quest is
done), the boss is a wild Pidgey Lv9 and Spearow Lv9 instead (no trainer;
the reward roll stays). His starter beats the player's
(Bulbasaur → Charmander, Charmander → Squirtle, Squirtle → Bulbasaur).
Instead of a chest, winning rolls the boss loot table once (at Lv9) on top
of the usual drops.

Wild Pokémon have no gear. Their skills are filled in for their level
(see `skill_trees.md`), and each turn they pick at random between their
basic attack and their equipped moves, at a random target.

### Trainer battles

`game/scenes/battle.py` (`BattleScene.trainer`)

A route's boss group can be a trainer's team (`Route.trainer`):
- the battle opens with "<trainer> wants to battle!" and **can't be run
  from**;
- its Pokémon give **×1.5 XP** (as in Gen 1);
- the trainer's name shows above the team on the map.

---

## Dev mode

`game/dev.py` (switched on in the pause menu, for testing; not saved)

- **XP boost** ×3/×5/×10/×20 multiplies the total XP of a won battle
  before it's shared out.
- **God mode:** hits on the party deal 0 damage and burn/poison don't hurt
  it (statuses still land); every hit on an enemy deals exactly its
  remaining HP, and Endure can't save it.
- **Teleport** (Left/Right: town, Enter: go) takes the party to any town,
  arriving as after fainting (healed; it becomes the town you wake up in).
- **Add item** rolls gear with `Gear.roll(..., affixes=[...], values=...)`:
  the chosen affixes (any number, 0–5, regardless of rarity), and every
  value random, lowest or highest of its range (then × rarity as usual).

---

## Types

`game/mechanics/type_chart.py`

The 15 Gen 1 types and the Gen 1 chart as intended, with one fix: Ghost is
**super effective** against Psychic (the original games had a bug that
made it have no effect). Against a Pokémon with two types, the two
multipliers are multiplied together.
