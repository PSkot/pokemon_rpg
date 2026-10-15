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

## Damage

`game/mechanics/combat.py` (`damage`), applied in
`game/scenes/battle.py` (`_apply`)

There are no misses: every damaging move hits. A hit is worked out in
these steps:

1. **Attack:** the user's Attack (with gear) × `(2 + stage) / 2`, where
   `stage` is 0–6 (Growth adds +1, a Liechi Berry +1 or +2; +1 = ×1.5,
   +6 = ×4). Halved if the user is **burned**.
2. **Power:** the move's power + the user's gear `power` bonus. The basic
   attack *Fight* has power 30 and no type.
3. **Base damage** (the Gen 1 formula):

   ```
   base = (2 × L / 5 + 2) × power × attack / defense / 50 + 2
   ```

   `L` is the user's level, `defense` the target's Defense with gear.
4. **Critical hit:** a 6.25% chance (1 in 16), plus the user's gear `crit`
   in percentage points (e.g. +5 → 11.25%). A crit multiplies `base` by
   **×1.5** (Gen 2+ style; *not* Gen 1's level-based crits).
5. **Leaf Shield:** if the target is shielded, `base` × **0.5**.
6. **Random spread:** `base` × a random number from 0.85 to 1.0.
7. **Type effectiveness:** × the type chart multiplier for the move's type
   against each of the target's types (multiplied together: 0, ¼, ½, 1,
   2 or 4). Typeless moves (Fight) are always ×1.
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

### Effects that happen when a hit lands

In the order the battle checks them:

- **Endure** (gear `endure`: Focus Band, Halo): if the hit would knock the
  target out, an `endure`% chance to survive with 1 HP instead.
- **Drain** (gear `drain`: Shell Bell, Tricorne, "Draining"): the user heals
  `drain`% of the damage actually dealt (min 1), if it's hurt.
- **Status from gear** (`status:<status>`, e.g. Witch Hat, "of the Muk"):
  each status the user's gear has is rolled at its % chance, and the first
  that succeeds is inflicted. Only if no gear status went through does the
  **move's own status** roll at its chance (Poison Sting 30% poison,
  Thunder Shock 10% paralysis, ...). See *Status conditions* for who can
  get what.
- **Berries:** the target may eat its berry right after being hit (see
  *Berries*).

### Turn order

`game/scenes/battle.py` (`_run_round`)

Each round, everyone picks first, then all actions play out in this order:

1. **Items** (medicine) before any move.
2. Then Pokémon whose **"act first"** gear roll succeeded (`first`: Quick
   Claw, Officer's Cap, "Hasty"; rolled every round).
3. Then **fastest first** by Speed (with gear; **halved if paralyzed**).
4. Ties are settled at random.

**Solar Beam** spends one round charging and hits the next.

### End of round

After all actions, in this order:

1. **Burn and poison damage** (see below), then berries may be eaten.
2. **Regen** (gear `regen`: Leftovers, Nightcap, "of the Chansey"): heals
   `regen`% of max HP (min 1).
3. **Leaf Shield** counts down: it lasts the round it's used and the next.

---

## Status conditions

`game/mechanics/status.py`, `game/scenes/battle.py` (`_can_act`,
`_status_damage`)

A Pokémon has at most one status. It **stays after battle** until it's
cured, it faints (fainting clears it), or the party reaches a town.

| Status | Effect | Immune type |
| --- | --- | --- |
| Burn | Attack ×0.5; loses 1/16 max HP at the end of each round | Fire |
| Poison | Loses 1/8 max HP at the end of each round | Poison |
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
**Held**, **Worn** and **Berry**. A piece of gear is an item plus its
rolls.

### Rolling a piece (`Gear.roll`)

1. **The item's own effect** is rolled from its range (e.g. Red Bandana:
   Attack +8…12%).
2. **Affixes:** Head, Held and Worn items get a random number of affixes
   for their rarity. Berries get none. Affixes are picked by weight without
   repeats (normal affixes weight 3; Hasty, Draining and of the Chansey 2;
   type and status affixes 1).
3. **Each value** is rolled as a whole number in its range, then:
   - a **bonus** (positive) is × the rarity factor, rounded, min 1
     (Python rounds .5 to the even number: 7.5 → 8, but 2.5 → 2);
   - a **penalty** (negative, e.g. Power Bracer's Speed −10%) stays as it is.
4. **Name:** the first prefix + item + the first suffix ("Fierce Red Bandana
   of the Aerodactyl"). Further affixes still count but aren't in the name.

Affixes can stack on the same stat as the item (a Fierce Red Bandana has
two Attack rolls), and all rolls simply add up.

| Rarity | Factor | Affixes |
| --- | --- | --- |
| Common | ×1.0 | 1–2 |
| Rare | ×1.5 | 2–3 |
| Epic | ×2.0 | 3–4 |
| Legendary | ×2.5 | 4–5 |

Example: Muscle Band (Attack +8…12%) at Legendary rolls 8…12 × 2.5 =
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
rarity picked by weight).

- **Won battle:** `WILD_LOOT` is rolled **once per defeated enemy**.
- **Chest** on a map (Up): `CHEST_LOOT` once (2–3 rolls).
- **Boss chest** (dungeons with a boss): `BOSS_LOOT` once (3–4 rolls).

| Table | Rolls | Nothing | Medicine | Gear |
| --- | --- | --- | --- | --- |
| Wild (per enemy) | 1 | 55% | 33% (Potion 18%, Super Potion 4%, status cures 11%) | 12% |
| Chest | 2–3 | – | 67% (Potions 1–3, Revive, cures, ...) | 33% |
| Boss | 3–4 | – | 45% (Super/Hyper Potion, Revive, Full Heal/Restore) | 55% |

Gear rarity weights:

| | Common | Rare | Epic | Legendary |
| --- | --- | --- | --- | --- |
| Wild | 70% | 24% | 5% | 1% |
| Chest | 50% | 35% | 12% | 3% |
| Boss | 25% | 45% | 24% | 6% |

---

## Wild Pokémon

`game/world/themes.py`, `game/world/level.py`

Each map theme has a weighted pool of species with level ranges. A wild
group has 1, 2 or 3 Pokémon (weights 60 / 30 / 10), each picked from the
pool, each at a random level in its entry's range. A boss group (dungeons
only) has 4–5 Pokémon from the same pool at the same levels.

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

Wild Pokémon have no gear, and pick a random move and a random target
each turn.

---

## Types

`game/mechanics/type_chart.py`

The 15 Gen 1 types and the Gen 1 chart as intended, with one fix: Ghost is
**super effective** against Psychic (the original games had a bug that
made it have no effect). Against a Pokémon with two types, the two
multipliers are multiplied together.
