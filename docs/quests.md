# Quests

How quests work, and every quest in the game. Keep this file in step with
the code (`game/world/quests.py`, screens in `game/scenes/quest_ui.py`).

**Built:** everything below except the "catch" / "bring an item" steps.

Quests carry the story (following Red/Blue) and gate progress: some
routes only open once a quest has started or is done, and some areas
change once a quest is finished. Board jobs ("defeat 6 Rattata", "collect
5 Pidgey Feathers") fill the gaps between story beats.

**Quests are the main source of XP** (about ¾ of it). Wild battles give
×0.15 of their Gen 1 XP and trainer battles ×0.45 (`WILD_XP`,
`TRAINER_XP`, see `mechanics.md`), split between the party members still
standing. Budget up to Pewter City: the quests pay about 2,900 XP (with
Pewter's two board jobs), a full run of each route there about 400 in
battle XP, so a player who does both reaches the gym around Lv14–15 (the
Boulder Gang's Onix is Lv16, two levels above Brock's in Gen 1).

Expected levels after that, for a pair that fights everything on the way
and does the story quests and the area's board jobs (checked with a
script that walks every route's maps; the major fights in
`tools/balance_sim.py` are tuned for these):

| Arriving at | Lead's level | Battle XP there (each) | Quest XP there |
| --- | --- | --- | --- |
| Pewter Gym | 14–15 | 230 | 400 |
| Route 3 | 15 | 620 | 1,350 |
| Mt. Moon | 18 | 1,000 | 600 |
| Route 4 | 19–20 | 540 | 400 |
| Cerulean Gym | 20–21 | 430 | 1,650 |
| Nugget Bridge | 22 | 1,000 | 1,850 |
| Route 25 | 23–24 | 850 | 1,400 |
| Cerulean burglar | 24–25 | 150 | 900 |
| Route 5, Underground Path, Route 6 | 25–27 | 2,000 | 3,200 |
| S.S. Anne | 28 | 1,740 | 1,000 |
| Vermilion Gym | 29 | 520 (each of three) | 1,300 |
| Route 11 | 29–30 | 1,060 | 1,700 |
| Diglett's Cave | 30–31 | 1,200 | 2,500 |
| Route 9 | 32 | 1,300 | 1,100 |
| Rock Tunnel | 32–33 | 1,550 | 3,200 |
| Route 8 | 34 | 1,100 | 3,200 |
| Underground Path (west) | 35 | 740 | 1,500 |
| Celadon City | 36 | | |
| Celadon Gym | 37 | | 1,700 |
| Rocket Hideout | 38–40 | | 1,900 |
| Pokémon Tower | 40–42 | | 2,100 |

(Before this check, battles gave ×0.5 / ×1.5 to every member unsplit:
about 62,000 battle XP each from Pewter to Vermilion against 14,000
from quests, reaching Mt. Moon at Lv22 and the Vermilion Gym at Lv42.)

**Levels track the party.** From Viridian Forest on, the areas' levels
sit around where the party is expected to be (raised well above Red/Blue's
from Route 3 on, as quests give far more XP than Red/Blue did): wild
Pokémon a few levels under the party, trainers about level with it,
bosses and gyms a few above. Route 1, where the starter is alone, is kept
low (Lv2–4, mostly one at a time). With two fighting, about half the
wild groups have one more Pokémon (see `mechanics.md`, *Wild Pokémon*).

---

## How quests work

### A quest

| Part | What it is |
| --- | --- |
| **Name and summary** | Shown in the quest log. |
| **Prerequisites** | Quests that must be done first. Until then it's *locked* (not shown). |
| **Start** | Taken from a town's **quest board** (`Quest.board`), given by a **townsfolk** you talk to (`Quest.giver`, with `Quest.offer` as their words), dropped as an item (`Quest.drop`), or *automatic* (as soon as its prerequisites are done, with a notice). |
| **Steps** | Objectives done in order; the quest shows the current one. |
| **Rewards** | Given when the last step is done. **Every** quest pays Poké Dollars (`Quest.money`) and XP (`Quest.xp`, to each party member, as in battle). **Major** quests (rival and gym battles, story milestones) also give items: medicine, gear (at a rarity and item level). Key items come from steps. |
| **Unlocks** | What changes once it's started or done: a doorway opens, a route's boss changes, the next quest becomes available. |

### Kinds of steps

| Step | Done when |
| --- | --- |
| **Visit** | You press Up at a building or doorway in a town (e.g. Professor Oak's Lab), or, for a Poké Mart, at the counter inside (Meowth). Shows a short dialogue. |
| **Talk** (`Step("talk", folk)`) | You talk to that townsfolk (Up next to them). Shows a short dialogue. |
| **Defeat** | You beat a route's boss (a boss group or a trainer). |
| **Reach** | You arrive in a town (or on a route's last map). |
| **Hunt** (`hunt(species, count, where)`) | You've beaten `count` of a species in won battles, anywhere (wild or a trainer's). Shown as "Defeat 6 Rattata (Route 1): 3/6". |
| **Collect** (`collect(item, count, route, species, chance, where)`) | You've collected `count` quest items. In every won battle on `route` **or any route after it** in the story (`instance.STORY_ORDER`; wild or trainer), each defeated Pokémon of `species` drops one with `chance` %: so the player needn't stay on one route, and can't farm an earlier, easier one. (Recruitment maps and the evolution quests' one-off maps don't count.) Shown as "(Pidgey on Route 1 or later)". Only while the quest is active; they're not bag items, just the count. |
| **Evolve** (`Step("evolve", species)`) | You evolve a Pokémon of that species from the party screen (E), once it has the level. |
| **Hand in** (`HAND_IN`) | You press Up at **any** town's quest board (for now): every quest waiting there is handed in, then the board opens. Board jobs end with it. |
| *Later:* **Catch**, **Bring an item** | Once catching and key items are used more. |

### States, saved in the game

Each quest is *locked*, *available*, *active* (at step *n*) or *done*;
stored in `Game.quests` (quest key → step number, or done). A hunt or
collect step's count so far is in `Game.quest_counts` (cleared when the
step is done). Key items
(Oak's Parcel, the Pokédex) go in a separate key-item list in the bag:
they can't be sold, used or dropped.

### Gates and changes

- **Locked doorways:** a route's doorway can need a quest to be started
  or done. Pressing Up there shows why ("An old man is lying in the road.
  He won't let you pass.") instead of entering.
- **Bosses that change:** a route can have different boss groups
  depending on quest state (e.g. the rival the first time, wild Pokémon
  after).

### On screen

- **Quest board:** a wooden notice board next to a house in Pallet Town,
  Viridian City and Pewter City (`Town.board_col`), with a paper note for
  each quest that can be taken. Up opens it: the town's quests (New /
  Active / Done) with the chosen one's summary and steps; Enter takes a
  new one. An empty board says "Nothing posted right now."
- **Dialogue box:** text at the bottom of the screen during quest moments
  (a speaker's name, pages advanced with Enter). Townsfolk speak in person;
  others (Oak, the Nurse) "speak" from their buildings.
- **Townsfolk** (`towns.Folk`, `Town.folk`): Pokémon living in a town,
  standing between the buildings and turning to face you, their name over
  them when you're near. Up next to one talks: a quest step waiting for
  them, else a quest they give, else a trial they send you to (a route
  with `Route.folk`), else their next chat line. A "!" over them when they
  have something for a quest (pink for an evolution quest). For now:
  a Pidgey in Pallet Town, a Rattata in Viridian City, a Geodude and the
  **old Venusaur / Charizard / Blastoise** in Pewter City (the last form of
  your starter's line: `ELDER`).
- **Tracker:** up to 3 active quests' current steps under the location
  line on the map, e.g. "Pest Control: Defeat 6 Rattata (Route 1): 3/6".
- **Markers:** a bouncing "!" over a quest board with something new and
  over the building the current step needs (when it's in the town you're
  in); a "?" over a quest board when a quest is ready to hand in. An
  evolution quest's "!" (and its line in the tracker) is pink. Several
  marks over one place stand side by side ("! ?").
- **Quest log:** Q (or the Quests touch button) on a map: active quests with their steps
  (done ones ticked), and finished ones; Up/Down scrolls.
- **Battle rewards:** a won battle's rewards panel also lists quest
  progress in light blue: "Rattata defeated — Pest Control 4/6",
  "Pidgey Feather — Soft Feathers 2/5".
- **Board states:** New / Active / Hand in / Done.
- **Notices:** "New quest: …" and "Quest complete: …" banners, plus the
  rewards in a panel (like loot): money, items, the XP and who leveled up
  (one panel per quest).
- The quest board lists each quest's rewards ("Rewards: ₽300, 200 XP,
  5 Potions").

---

## The opening chain (Red/Blue)

### 1. Oak's Parcel

- **Starts:** taken from the Viridian City quest board.
- **Steps:**
  1. Visit the **Viridian Poké Mart**: Meowth, the shopkeeper, hands you **Oak's
     Parcel** (key item).
  2. Visit **Professor Oak's Lab** in Pallet Town: Oak takes the parcel
     and gives you the **Pokédex** (key item).
- **Rewards:** ₽300, 150 XP, 5 Potions (Gen 1 gives Poké Balls here;
  those can come once catching exists).
- **Unlocks:** quest 2; **Viridian Forest** (until then its doorway is
  blocked: "An old man is lying in the road. He hasn't had his coffee
  yet.", as Route 2 is in Red/Blue).

### 2. Rival on Route 22

- **Starts:** automatically when quest 1 is done (Oak: "Your rival went
  west, to Route 22. He wants to battle you!").
- **Steps:**
  1. Defeat your **rival** at the end of Route 22 (Pidgey Lv7 and his
     starter Lv6: Gen 1's team two levels down, as both attack at once).
- **Rewards:** ₽600, 300 XP, 2 Super Potions and an Uncommon gear piece
  (item level 9), on top of the trainer battle's reward roll, and a
  **Teamwork Ribbon** (a special key item: Prof. Oak sends it over the
  Pokédex, "I'm sending you something special"; used from the bag, one
  more Pokémon can fight, see `mechanics.md`, *Party and reserve*).
- **Unlocks:** **Route 22** opens when the quest *starts* (its doorway is
  closed before that). Once it's *done*, Route 22's boss becomes a wild
  **Pidgey Lv9 and Spearow Lv9** (no trainer, still the reward roll, no
  chest), so the route stays worth repeating.

### Bugs in the Forest (side quest)

- **Starts:** taken from the Viridian City quest board, once Oak's Parcel
  is done.
- **Steps:** defeat the giant Caterpie (Lv12, with Weedle 10 and Kakuna 9;
  two more Weedle with two fighting) in Viridian Forest.
- **Rewards:** ₽500, 350 XP, 2 Super Potions and a Common gear piece
  (item level 10).

### Board jobs

Each town's board posts a few hunt and collect jobs for the route out of
town (Pewter's for Viridian Forest, and for Route 3 once the badge is won). All end with
handing them in at any board.

| Board | Quest | Needs | Steps | Drop chance | Rewards |
| --- | --- | --- | --- | --- | --- |
| Pallet | Pest Control | – | Defeat 6 Rattata (Route 1) | – | ₽300, 150 XP |
| Pallet | Soft Feathers | – | Collect 5 Pidgey Feathers (Pidgey, Route 1) | 50% | ₽400, 150 XP |
| Viridian | Spearow Trouble | Oak's Parcel | Defeat 4 Spearow (Route 22) | – | ₽450, 200 XP |
| Viridian | Shed Horns | Oak's Parcel | Collect 6 Nidoran Horns (Nidoran ♀/♂, Route 22) | 40% | ₽500, 250 XP |
| Viridian | Bug Silk | Oak's Parcel | Collect 5 Silk Threads (Caterpie, Metapod; Viridian Forest) | 40% | ₽600, 250 XP |
| Pewter | Poison Barbs | – | Collect 6 Poison Barbs (Weedle, Kakuna; Viridian Forest) | 35% | ₽700, 500 XP |
| Pewter | Sparks in the Forest | – | Defeat 3 Pikachu (Viridian Forest) | – | ₽800, 600 XP |
| Pewter | Snake Charmer | Boulder Badge | Defeat 5 Ekans (Route 3) | – | ₽500, 300 XP |
| Pewter | Soft as Fluff | Boulder Badge | Collect 5 Jigglypuff Fluff (Jigglypuff, Route 3) | 40% | ₽600, 350 XP |
| Cerulean | Hilltop Raiders | Cerulean City | Defeat 6 Spearow (Route 4) | – | ₽600, 400 XP |
| Cerulean | Shed Skins | Cerulean City | Collect 5 Ekans Skins (Ekans, Route 4) | 40% | ₽700, 450 XP |
| Cerulean | Bent Spoons | Cerulean City | Defeat 3 Abra (Route 24) | – | ₽800, 550 XP |
| Cerulean | Sweet Nectar | Rival at Nugget Bridge | Collect 5 Sweet Nectar (Oddish, Bellsprout; Route 25) | 40% | ₽900, 600 XP |
| Cerulean | Night Swarm | Rival at Nugget Bridge | Defeat 6 Venonat (Route 25) | – | ₽900, 600 XP |
| Cerulean | Pickpockets | The Cerulean Burglar | Defeat 6 Meowth (Route 5) | – | ₽1,000, 650 XP |
| Cerulean | Hot Tempers | The Cerulean Burglar | Collect 5 Mankey Fur (Mankey, Route 5) | 40% | ₽1,000, 650 XP |
| Vermilion | Tunnel Trouble | Vermilion City | Defeat 6 Diglett (Underground Path) | – | ₽1,100, 700 XP |
| Vermilion | Lucky Coins | Vermilion City | Collect 5 Lucky Coins (Meowth, Route 6) | 40% | ₽1,100, 700 XP |
| Vermilion | Sleepy Heads | The Thunder Badge | Defeat 6 Drowzee (Route 11) | – | ₽1,200, 800 XP |
| Vermilion | Trouble Underfoot | East of Vermilion | Defeat 5 Dugtrio (Diglett's Cave) | – | ₽1,300, 900 XP |
| Cerulean | Bats in the Dark | Oak's Aide | Defeat 8 Zubat (Rock Tunnel) | – | ₽1,400, 900 XP |
| Cerulean | Muscle Trouble | Oak's Aide | Defeat 6 Machop (Rock Tunnel) | – | ₽1,400, 900 XP |
| Lavender | Hot Dogs | Rock Tunnel | Defeat 6 Growlithe (Route 8) | – | ₽1,500, 1,000 XP |
| Lavender | Fangs for the Memories | Rock Tunnel | Collect 5 Ekans Fangs (Ekans, Route 8 or later) | 40% | ₽1,500, 1,000 XP |

Each takes about one or two runs of its route. They can't be repeated
yet.

### 3. The Boulder Badge

- **Starts:** automatically on first arriving in Pewter City
  (`Quest.starts_in`).
- **Steps:** defeat the **Boulder Gang** (Rock types led by an Onix) at
  the end of the Pewter Gym (Up at the gym building), the third of three
  waves fought by two Pokémon the player picks (see `mechanics.md`,
  *Gyms*). Onix: "I took you for granted.
  As proof of your victory, here's the Boulder Badge!" (key item).
- **Rewards:** ₽500, 400 XP, 3 Super Potions and a **Rare** gear piece
  (item level 14), on top of the gang's prize money (₽792) and reward roll.
- **Unlocks:** **Route 3** (its doorway on Pewter's east edge: "The
  Boulder Gang holds the gym! Beat them first!"), quest 4 and Pewter's Route 3 jobs. The gym shuts once
  the badge is won.

### 4. Road to Mt. Moon

- **Starts:** automatically when the Boulder Badge is won.
- **Steps:** reach **Mt. Moon** (the Pokémon Center at its foot) by Route
  3. Six bands of Pokémon have claimed the road (see `mechanics.md`, *Trainer battles*).
- **Rewards:** ₽400, 300 XP.
- **Unlocks:** quest 5 (Mt. Moon's doorway is on the stop's right edge).

### 5. Through Mt. Moon

- **Starts:** automatically when quest 4 is done (or on arriving at the
  Mt. Moon Pokémon Center if it already is).
- **Steps:** reach **Route 4** through Mt. Moon, a dungeon of ladders and
  dead ends (see `mechanics.md`, *Dungeons*); the Rocket Gang Leader on B2F
  guards the ladder to the way out.
- **Rewards:** ₽800, 600 XP, 3 Super Potions and an Uncommon gear piece
  (item level 14).
- **Unlocks:** quest 6 (Route 4's road on is on the stop's right edge).

### 6. Cerulean City

- **Starts:** automatically when quest 5 is done.
- **Steps:** reach **Cerulean City** down Route 4 (2 maps, two trainers).
- **Rewards:** ₽500, 400 XP.
- **Unlocks:** Cerulean's board jobs. Cerulean City has a Pokémon Center,
  a Poké Mart (adds Ice Heal), a Recruitment Center, the Cerulean Gym
  (quest 6b), the Bike Shop and the burgled house (scenery for now).

### 6b. The Cascade Badge

- **Starts:** on arriving in Cerulean City once quest 6 is done
  (`Quest.starts_in`); it can be done before or after quests 7–8.
- **Steps:** defeat the **Cascade Crew** (Water types led by a Starmie)
  at the end of the Cerulean Gym (Up at the gym building), the third of
  three waves (Goldeen 18 and Psyduck 18; Horsea 19 and Shellder 19;
  Starmie 22 and Staryu 19), fought by the Pokémon the player picks.
  Starmie: "Hyah... Hyah! You really are strong. Here, the Cascade
  Badge!" (key item).
- **Rewards:** ₽900, 800 XP, 2 Hyper Potions and a **Rare** gear piece
  (item level 21), on top of the crew's prize money (₽940) and the gym's
  fancy chest.
- **Unlocks:** nothing yet (in Red/Blue the badge lets you use Cut).

### 7. Rival at Nugget Bridge

- **Starts:** automatically when quest 6 is done.
- **Steps:** beat the **rival**, who waits at the start of **Nugget
  Bridge** (Route 24, Cerulean's east doorway), as in Red/Blue: Pidgeotto
  19, Abra 16, Rattata 16 and his starter's next form (Charmeleon,
  Wartortle or Ivysaur) at 20. He stands at the bridge's first spot and
  can't be got past (`Trainer.blocks`); beaten once for good
  (`Trainer.first`, key `nugget_rival`, the step's target).
- **The rest of the bridge:** the five trainer bands, then at the far end
  a **Rocket** (the arena boss: Ekans 23, Zubat 22) who hands over a
  **Nugget** (sells for ₽5,000) and then fights, once (`Route.boss_key`,
  `boss_gift`, `boss_dialogue`); later trips find Oddish, Bellsprout and
  Abra there instead.
- **Rewards:** ₽900, 700 XP, 3 Super Potions and an Uncommon gear piece
  (item level 16).
- **Unlocks:** quest 8, Route 25 (from the Route 24 stop at the bridge's
  far end) and Cerulean's Route 25 jobs.

### 8. Bill's Sea Cottage

- **Starts:** automatically when quest 7 is done.
- **Steps:** walk Route 25 to Bill's Sea Cottage and talk to the Clefairy
  outside (Bill, mixed up with it by his teleporter), then go in and run
  the Cell Separator (Up at the cottage). Up at the cottage before talking
  says the door is locked and points to the Clefairy (`Step.before`).
- **Rewards:** ₽1,000, 800 XP, the **S.S. Ticket** (a key item, for the
  S.S. Anne at Vermilion City later), 2 Revives and an Uncommon gear piece
  (item level 17).
- **Unlocks:** quest 9 (Bill mentions the break-in in Cerulean).

### 9. The Cerulean Burglar

- **Starts:** automatically when quest 8 is done.
- **Steps:** Up at the **Burgled House** at the end of Cerulean's street
  (shut before: "Police business"), a short walk through to its backyard,
  and beat the burglar's **Rocket Gang** there (Mankey 24, Abra 22, Zubat
  22; Gen 1's Machop and Drowzee). He drops the stolen TM28, which goes
  back to the owner (TMs aren't in the game yet).
- **Rewards:** ₽1,000, 900 XP, 3 Super Potions and an Uncommon gear piece
  (item level 18), on top of the prize (₽330).
- **Unlocks:** Cerulean's doorway behind the house onto **Route 5**
  (fenced off before), quest 10 and Cerulean's Route 5 jobs. The house
  stays shut after (`Route.blocked_done`: the owner thanks you).

### 10. South of Cerulean

- **Starts:** automatically when quest 9 is done.
- **Steps:** walk **Route 5** (2 maps, wild Meowth and Mankey) to the
  Route 5 stop at its bottom (town "route_5"): the Day Care (scenery),
  Saffron City's gate guard (the gate is shut, as in Red/Blue), and a
  Diglett who dug the **Underground Path** out again.
- **Rewards:** ₽600, 500 XP.
- **Unlocks:** quest 11.

### 11. Under Saffron

- **Starts:** automatically when quest 10 is done.
- **Steps:** take the **Underground Path** (the Route 5 stop's east
  doorway; 2 maps of lamp-lit tunnel under Saffron City, whose gates are
  shut; wild Diglett, Rattata, Zubat and Ekans, no trainers) to the stop at
  the top of Route 6 (town "route_6").
- **Rewards:** ₽700, 600 XP.

### 12. Vermilion City

- **Starts:** automatically when quest 11 is done.
- **Steps:** follow **Route 6** (2 maps, four trainer bands) down to
  **Vermilion City**.
- **Rewards:** ₽900, 800 XP, 3 Super Potions and an Uncommon gear piece
  (item level 22).
- **Unlocks:** Vermilion's board jobs. Vermilion City has a Pokémon Center,
  a Poké Mart, a Recruitment Center, the Pokémon Fan Club (scenery), the
  Vermilion Gym (a small tree grows over its door, as in Red/Blue: Cut
  comes from the S.S. Anne) and, at the east end, the dock where the S.S.
  Anne lies (quest 13).

### 13. The S.S. Anne

- **Starts:** automatically when quest 12 is done (Bill's S.S. Ticket gets
  you aboard: the gangway is Vermilion's east doorway).
- **The ship** (`Route` "ss_anne", a dungeon of rooms like Mt. Moon; no
  wild Pokémon, as in Red/Blue): **1F** (the gangway out, three bands,
  stairs down and up), **B1F** (the hold, a dead end: two sailors' bands
  and a fisherman's), **2F** (two bands, and the **rival** guarding the
  stairs up: Pidgeotto 22, Raticate 19, Kadabra 18 and his starter's next
  form at 22; Gen 1's, a few levels up; about 64% in `tools/balance_sim.py`
  at Lv27 + Lv26, as all four attack at once), and the **Captain's cabin**.
- **Steps:** beat the rival (he tells you about the seasick "Cut master"),
  then talk to the **Captain** in his cabin: you rub his back, and he
  gives you **HM01 Cut** (a key item; it opens the Vermilion Gym in the
  next part), and a **Teamwork Ribbon** ("My crew's finest wore it").
- **Rewards:** ₽1,200, 1,000 XP, 3 Super Potions, a Revive and an Uncommon
  gear piece (item level 25), on top of the rival's prize and boss loot.
- **Unlocks:** with the ribbon used, a third place in the party (filled at
  a Recruitment Center, from the reserve).
- **Afterwards** the S.S. Anne sets sail: the gangway is shut
  (`Route.needs` "active": only while the quest is going on).

### 14. The Thunder Badge

- **Starts:** automatically when quest 13 is done (with HM01 Cut).
- **Steps:** a small tree grows over the **Vermilion Gym**'s door
  (`Building.tree`; Up before Cut: "It would have to be cut down"). The
  first Up once the quest has started cuts it down for good ("<lead> used
  Cut!"); then Up walks the gym. Defeat the **Thunder Battalion**, the
  third of three waves, fought by **three** Pokémon the player picks
  (`Route.wave_team` = 3): Privates (Pikachu, Voltorb, Magnemite 27),
  Sergeants (Magnemite, Voltorb, Pikachu 28), then the battalion: Raichu 31,
  Voltorb 29, Magnemite 29 (Gen 1's Lt. Surge: Voltorb, Pikachu, Raichu).
  Raichu: "Whoa! You're the real deal, kid! Fine then, take the Thunder
  Badge!" (key item).
- **Meant to need a full team:** in `tools/balance_sim.py` a team of three
  at Lv29 + Lv28 wins about 70%; two win about 14% (`TEAM=2`).
- **Rewards:** ₽1,500, 1,300 XP, 2 Hyper Potions and a **Rare** gear piece
  (item level 28), on top of the battalion's prize (₽1,534) and the gym's
  fancy chest.

---

### 15. East of Vermilion

- **Starts:** automatically when quest 14 is done.
- **Steps:** follow **Route 11** (2 maps, five trainer bands; its doorway
  is at Vermilion's east end, by the dock; shut until the Thunder Badge:
  "Soldiers of the Thunder Battalion are drilling on the road east...")
  to the **Route 11 Gate** (town "route_11").
- **There:** the mouth of **Diglett's Cave**, a Diglett (townsfolk; it
  gives *Three Heads Are Better*), and **Snorlax**, fast asleep across the
  road to Route 12 (`Folk.asleep`: its sleeping sprite, breathing, with a
  Zzz rising over it; it doesn't turn to face you). Talking to it: "A huge
  Pokémon is fast asleep, sprawled right across the road to Route 12. It
  won't budge." The town ends there: turn back. (As in Red/Blue, it takes
  the Poké Flute to wake it, later.)
- **Rewards:** ₽1,000, 900 XP.

### 16. Diglett's Cave

- **Starts:** automatically when quest 15 is done.
- **Steps:** go through **Diglett's Cave** (3 maps of Diglett and
  Dugtrio, a giant Dugtrio's band at the end) to the **Route 2** stop.
- **Rewards:** ₽1,200, 1,100 XP, 2 Hyper Potions and a **Rare** gear piece
  (item level 30).
- **Afterwards:** Route 2 (one short map, no wild Pokémon) leads up to
  Pewter City (a new doorway at its east end), so the trip back east goes
  through Pewter, or back through the cave.

### 17. Oak's Aide

- **Starts:** automatically when quest 16 is done.
- **Steps:** talk to **Professor Oak's aide** (a Kadabra) on Route 2.
- **Rewards:** **HM05 Flash** (a key item, for the dark Rock Tunnel
  later; Gen 1's aide wants 10 Pokémon caught first, here it's just
  given), ₽600, 500 XP.

### 18. The Road East

- **Starts:** automatically when quest 17 is done (with Flash).
- **Steps:** follow **Route 9** (2 maps, five trainer bands; its doorway
  is at Cerulean's east end; shut until Flash: a Hiker warns that Rock
  Tunnel is pitch dark) to the **Route 10 Pokémon Center** (town
  "route_10", a checkpoint with a Voltorb by the Power Plant road).
- **Rewards:** ₽1,200, 1,100 XP.

### 19. Rock Tunnel

- **Starts:** automatically when quest 18 is done.
- **Steps:** go through **Rock Tunnel** (3 dark rooms, Flash lights a
  circle around you; five bands and the Hiker Crew guarding B1F's stairs
  up) to **Lavender Town**.
- **Lavender Town** (town "lavender"): Pokémon Center, Poké Mart (with
  Hyper Potions and Revives) and Persian's gear den, a quest board, the
  **Pokémon Tower** (`pokemon_tower.png`; shut for now: "Something moves
  inside, but you can't make out what. You'd need a way to see it." The
  Silph Scope comes later), Mr. Fuji's house ("Gone to the Tower"), and a
  Drowzee and a Jigglypuff who talk about the tower's ghosts. The town
  ends there for now (Route 8 west to Saffron comes later).
- **Rewards:** ₽1,500, 1,400 XP, 2 Hyper Potions, a Revive and a **Rare**
  gear piece (item level 33).

### 20. West of Lavender

- **Starts:** automatically when quest 19 is done.
- **Steps:** follow **Route 8** (2 maps, four trainer bands; its doorway
  is at Lavender's east end, past the smith) to the **Route 8 Gate**
  (town "route_8_gate"): Saffron City's east gate, shut, its guard too
  thirsty to talk sense, and the Underground Path's doorway on.
- **Rewards:** ₽1,300, 1,200 XP.

### 21. Celadon City

- **Starts:** automatically when quest 20 is done.
- **Steps:** take the **Underground Path** west (2 maps of tunnel) to
  **Celadon City**, a city in three parts joined by doorways at their
  ends (`Town.exits` "town:<key>"):
  - **Celadon City** (town "celadon", the east end, where the tunnel comes
    up): the Pokémon Center, a quest board and the **Celadon Department
    Store** (`scenes/dept_store.py`), one screen per floor joined by
    stairs: **1F** Lobby (Meowth's store guide), **2F** Trainer's Market
    (medicine, Max Potions and Full Heals too), **3F** Gear Gallery
    (Persian on its pile: the gear counter, Lv34–38 pieces up to Rare),
    **4F** Smith Supplies (a Machop sells Scrap ₽300, Alloy ₽1,000 and
    Crystal ₽3,000, `items.MATERIAL_PRICE`) and the **Rooftop** (three
    vending machines: Fresh Water ₽200, Soda Pop ₽300, Lemonade ₽350, which
    restore 50/60/80 HP; and the view over the city).
  - **Celadon Square** ("celadon_square"): the Game Corner (Team
    Rocket's Hideout under it, quest 23), the Celadon Gym (quest 22), the Recruitment Center
    and the smith.
  - **Celadon West End** ("celadon_west"): the Celadon Mansion and the
    **Battle Tower**. It opens after the Rainbow Badge: 25 floors of wave
    battles, five more opening at 6, 7 and 8 badges and the
    last five after the League, run by Mew, with gems that buy gear and special Pokémon
    (`docs/mechanics.md` → The Battle Tower).
- **Rewards:** ₽1,600, 1,500 XP, 2 Hyper Potions and a **Rare** gear piece
  (item level 35).

### 22. The Rainbow Badge

- **Starts:** automatically when quest 21 is done.
- **Steps:** defeat the **Blossom Troupe** in the **Celadon Gym** (Celadon
  Square; route "celadon_gym"), Erika's greenhouse. **Clouds of spores**
  drift over the walk to the arena: walking into one puts a party member
  to sleep, poisons or paralyses it, and the status lasts into the waves
  (`mechanics.md` → *The Celadon Gym's spores*). Three fight
  (`wave_team=3`): two waves of Grass Pokémon (Oddish 35, Bellsprout 35,
  Gloom 36; Weepinbell 36, Exeggcute 36, Gloom 37), then the troupe
  (Vileplume 39, Victreebel 38, Tangela 37). With three at the expected
  Lv37/36, the gym's battles are won about 69% of the time before any
  spores (`tools/balance_sim.py`). The leader, Vileplume, gives the
  **Rainbow Badge**. The gym is shut once the badge is won.
- **Rewards:** ₽1,800, 1,700 XP, 2 Hyper Potions, 3 Full Heals and a
  **Rare** gear piece (item level 38). Winning the badge opens the
  **Battle Tower** (floors 1–5).

### 23. Team Rocket's Hideout

- **Starts:** automatically when quest 22 is done.
- **Steps:** (1) Up at the **Game Corner** (Celadon Square; shut before the
  quest, its note says a man in black guards a poster) goes behind the
  poster, down into the **Rocket Hideout** (route "rocket_hideout", a
  dungeon: `ROCKET_HIDEOUT`, steel halls with Team Rocket banners, drawn in
  code; no wild Pokémon). Four floors straight down, B1F to B4F, two
  Rocket bands on each; B2F and B3F are **spinner floors** (arrow, stop
  and launch pads under a catwalk: `mechanics.md`, *The Rocket Hideout's
  spinner floors*); on B1F the **Poster Guard** stands first and can't
  be got past, and on B4F the **Lift Key Guard** blocks the lift. Beating
  him gives the **Lift Key**. (2) The lift goes down to the **Boss's
  Office**, where the **Rocket Boss** waits: a Persian (Giovanni's
  cat) with Gen 1 Giovanni's team (Onix, Rhyhorn, Kangaskhan; see
  `mechanics.md`, *Trainer battles*). Beating it takes the Lift Key and
  gives the **Silph Scope**, and opens the office's back door up to the
  Game Corner.
- **Rewards:** ₽2,000, 1,900 XP, 3 Hyper Potions, 2 Revives and a **Rare**
  gear piece (item level 40). The smith's hammer quest goes on offer.

### 25. The Sleeping Giant

- **Starts:** automatically when quest 24 is done (the Poké Flute).
- **There:** two **Snorlax**, fast asleep across doorways: one at Celadon
  West End's west end, blocking **Route 16** (`Folk` "celadon_snorlax"), and
  one at the **Route 11 Gate**'s east end, blocking **Route 12** up to
  Lavender Town ("route_12_snorlax"). Each is gone once its own battle is
  won (`Folk.gone_after` "boss:<route>"), and its road opens (`Route.needs`
  ("boss:<route>", "beaten")). A Hypno lives near each: the **Old Hypno** by
  the Battle Tower, and the Route 11 Gate's.
- **Steps** (either Snorlax, either Hypno: `Step.alt`; the battle is at the
  Snorlax that was fed, `quests.chosen`):
  1. Play the Poké Flute for a Snorlax (talk to it): it rolls over and
     snores on. Too deep asleep for a tune alone.
  2. Ask a Hypno: a Snorlax only wakes up hungry. Put a feast under its
     nose, then play the flute. Route 8's Meowth and Mankey have been raiding
     the market stalls.
  3. Collect **6 Stolen Snacks** (Meowth and Mankey on Route 8 or later,
     50% each).
  4. Buy a **Soda Pop Crate** at the Department Store's rooftop vending
     machines (a "visit" step at `dept_store.ROOFTOP`).
  5. Lay out the feast for a Snorlax and play the flute (talk to it, takes
     the crate): it wakes, wolfs it down, and is still hungry and grumpy.
  6. Calm it down (talk to it again; `Route.folk_line`):
     - west: **Snack Pack**, Snorlax 48 (giant) with Persian 42, Primeape 42
       and Raticate 42 (route "snorlax_wakes"), the snack thieves back for
       the leftovers;
     - east: **Dream Eaters**, Snorlax 48 (giant) with Hypno 42, Drowzee 42
       and Drowzee 41 (route "snorlax_wakes_east"), furious their dinner
       woke up.

     A party of three at Lv42/41/41 with 3 Hyper Potions wins about 55%
     (west) and 51% (east) (`tools/balance_sim.py`).
- **Rewards:** ₽2,400, 2,300 XP, and **Snorlax (Lv40) joins** (the party,
  or the reserve). Its road opens.

### 25b. The Other Sleeping Giant

- **Starts:** automatically when quest 25 is done.
- **Steps:** wake the other Snorlax with the Poké Flute alone (talk to it),
  and win the same battle as above at its place.
- **Rewards:** ₽2,000, 1,900 XP, 2 Hyper Potions. It doesn't join; its road
  opens too.

### Thirsty Work (side quest)

- **Starts:** from the **Route 16 Gate guard** (a Fearow), once quest 25 is
  done (he's only reachable past the Celadon Snorlax anyway). He won't let
  anyone down the road south until he's had a proper drink, and the
  Department Store's bottled water won't do: he wants spring water.
- **Steps:**
  1. Ask Celadon's **Bellsprout** (Celadon City, east end): the best spring
     in Kanto is on the cliffs behind the Route 16 Gate, but a Golduck gang
     has taken it.
  2. Talk to the guard: he points the way up (route "hidden_spring", one
     map of Water Pokémon, Lv41–44). Beat the **Spring Squatters**: Golduck
     47 (giant), Seaking 43, Psyduck 43, Psyduck 43. A party of three at
     Lv43/42/42 with 3 Hyper Potions wins about 74%. Gives the **Spring
     Water** (key item).
  3. Bring it to the guard: he drinks, and opens the road south (the skate
     road, next).
- **Rewards:** ₽2,200, 2,000 XP, 2 Hyper Potions and a **Rare** gear piece
  (item level 44).

### Route 12

From the Route 11 Gate's east doorway (past its Snorlax) up to Lavender
Town (a doorway at col 67, by the smith): 2 maps, wild Gloom, Weepinbell,
Venonat, Pidgeotto, Tentacool, Goldeen and Shellder (Lv40–43), and four
bands: **Pier Anglers** (Goldeen 43, Tentacool 43, Goldeen 43), **Seaside
Pals** (Nidorina 43, Weepinbell 43), **Static Band** (Voltorb 44,
Electrode 44) and **Deep Sea Haul** (Seaking 44, Shellder 43, Horsea 43).

### Planned: Learn to Fly (with Route 16)

Not built yet: Route 16 is in (west of Celadon, past the Snorlax), the
quest comes next; Red/Blue gives HM02 Fly there. Its battle rules are already in: *Sky battles* in
`mechanics.md` (`BattleScene(sky=True)`, `mechanics/sky.py`).

- **Giver:** a Bird Keeper at the Route 16 Gate; on offer once a Pidgey or
  Spearow has evolved (a Pidgeotto, Pidgeot or Fearow in the party or
  reserve).
- **Steps:** (1) win 5 wild battles on Route 7/8/16 with only the bird
  fighting; (2) talk to the keeper; (3) the **Sky Trial** on a new map,
  **Skyward Cliffs**: the bird alone (`wave_species`: the Pidgey and
  Spearow lines), a sky battle: two waves of anti-air Pokémon (Rock and
  Electric: Geodude/Graveler, Magnemite/Voltorb; Ground ones like Diglett
  and Sandshrew can't touch it), then a giant boss (Dodrio, "the bird that
  never flew", once it has art; else a giant Onix).
- **On the map:** the player can glide (hold jump to fall slowly) on
  Skyward Cliffs only, to cross its gaps.
- **Reward:** money and XP, and **Fly**: fast travel from the pause menu
  to any town already visited.

### 24. The Pokémon Tower

- **Starts:** automatically when quest 23 is done (the Silph Scope).
- **Steps:** (1) Up at the **Pokémon Tower** (Lavender Town; shut before the
  quest) goes in: route "pokemon_tower", a dungeon of 7 floors
  (`POKEMON_TOWER`: violet stone, candle lamps and rows of gravestones,
  drawn in code), with wild Gastly, Haunter and Cubone (Lv37–41) and
  **Channelers' bands** (3F–5F). The **rival** waits on 2F and can't be got
  past (Pidgeotto 40, Growlithe 39, Kadabra 39, his starter's next form 42).
  On 6F the **Restless Spirits** bar the stairs up: Marowak's ghost (50)
  with the lost spirits round her (Haunter 44, Gastly 44, Haunter 44),
  drawn pale and see-through (`Trainer.spirit`). Beating them lays her to
  rest and leaves the **Thick Bone** (the smith's hammer). (2) On 7F,
  **Team Rocket** holds Mr. Fuji (Arbok 43, Golbat 42, Koffing 42, Raticate
  42), guarding the back stairs out. (3) Up at **Mr. Fuji's House**: he
  gives the **Poké Flute**.
- **Balance:** a party of three at Lv41/40/40 with 3 Hyper Potions wins
  about 85% against the rival, 78% against the spirits and 74% against the
  Rockets (`tools/balance_sim.py`-style runs).
- **Rewards:** ₽2,200, 2,100 XP, 3 Hyper Potions, 2 Revives and a **Rare**
  gear piece (item level 42). The Poké Flute wakes Snorlax (Route 12, later).

### A Hammer Fit for a Smith (side quest)

- **Starts:** from the **Machamp smith** (Lavender Town and the major towns
  after it), once quest 23 is done (the Silph Scope, the way into the
  Pokémon Tower, is in hand): his hammer snapped, and nothing from a
  Mart survives four arms. "Bring me something STRONG."
- **Steps:** bring him something strong enough for a hammer: the
  **Thick Bone** (a key item; it comes from the Pokémon Tower's Marowak,
  quest 24). Until it's in the bag, talking to him says to keep looking (and
  no "!" shows over him: `Step.takes`/`waiting`). When it turns up:
  "You found a Thick Bone! It's heavier than stone, and not a scratch on
  it. / Something this strong must be good for more than gathering
  dust..." (`quests.BONE_FOUND`).
- **Rewards:** ₽1,000, 800 XP, and his menu opens: salvage, enhance and
  smelt (`mechanics.md`, *The smith*). (Dev mode's item maker can add the
  Thick Bone meanwhile: key items are in its list.)

---

## The evolution stones

Each stone has one quest, given by a townsperson once the **Rainbow
Badge** is won (`Quest.giver`). Talking to the giver again sends the
party to the place (`Route.folk`). There a giant leader's band waits at
the end. Beating it gives the stone, a key item that evolves one Pokémon
and is then used up (`mechanics.md` → *Evolution stones*). The battle
odds below are for three at Lv39/38 (`tools/balance_sim.py`), not
counting the way there.

- **The Overgrown Wing** (`leaf_stone`, Celadon Square's **Oddish**): the
  Celadon Gym's back wing (route "celadon_garden"), a 64-tile greenhouse
  thick with the gym's **spore clouds**. Three fight two waves with no
  healing (Tangela 36, Weepinbell 36, Gloom 36; Parasect 37, Exeggcute 37,
  Gloom 37), then the **Overgrowth**: a giant Exeggutor 40 with Victreebel
  38 and Vileplume 38. About 60% won: the hardest of the three.
  **Leaf Stone**.
- **The Moonlit Dance** (`moon_stone`, the **Clefairy** at the Mt. Moon
  Pokémon Center): Mt. Moon's crater (route "mt_moon_crater", 70 tiles),
  **pitch dark** but for Flash's light, with wild Clefairy (Sing,
  Metronome), Golbat and Graveler (Lv36–38) in groups of 2–3, then the
  **Moon Dancers**: a giant Clefable 45 with three Clefairy (42, 42, 41).
  About 81% won. **Moon Stone**.
- **Live Wires** (`thunder_stone`, the Route 10 **Voltorb**): the
  abandoned **Power Plant** (route "power_plant", 70 tiles, the Vermilion
  Gym's steel look), its **loose current** paralysing on touch, wild
  Voltorb, Magnemite, Magneton and Electrode (Lv36–39), then the **Live
  Wire Gang**: a giant Electabuzz 45 with Magneton 41 and Electrode 41.
  About 78% won. **Thunder Stone**.
- Rewards: ₽1,500 and 1,400 XP each, besides the stone.
- **Fire Stone** and **Water Stone**: later, with Cinnabar and the coast.

---

## Evolution quests

Every evolution is unlocked by a quest (`quests.can_evolve`); a line
without one doesn't evolve yet. These quests don't come from boards:
they start when their key item turns up: dropped in battles
(`Quest.drop`: item, route, species, chance; "You found a Metapod
Shell!" and the New quest notice after the battle), and later from NPCs
or trainer battles (gyms, the rival, Team Rocket). An evolution
quest is only on offer, and its item only drops, once the party or the
reserve has a Pokémon of that species at its evolution level
(`Quest.evolves`, `quests.evolution_level`): no Metapod Shell before a
Lv7 Caterpie. The party screen then shows "Evolve!" and E
evolves it (or use the item from the bag's Key items on that Pokémon),
using up the item and finishing the quest. After that the
line evolves by level as usual (end of a won battle).

| Quest | Item (drop) | Steps | Rewards |
| --- | --- | --- | --- |
| Cocoon of Steel | Metapod Shell: 15% per Caterpie or Metapod beaten in Viridian Forest | Evolve a Caterpie (Lv7+) into Metapod | ₽200, 100 XP |
| Poison Cocoon | Kakuna Shell: 15% per Weedle or Kakuna beaten in Viridian Forest | Evolve a Weedle (Lv7+) into Kakuna | ₽200, 100 XP |

### Coming of Age (the starters, Lv16)

Given by the **old Venusaur / Charizard / Blastoise** in Pewter City (the
one for your starter's line) once your starter is Lv16, in the party or
the reserve (`evolve_bulbasaur` / `_charmander` / `_squirtle`):
1. **Collect** 3 tokens of its element: Sun Leaves (25% per Spearow,
   Jigglypuff, Sandshrew or Ekans on Route 3), Moon Flints (35% per Geodude
   in Mt. Moon) or Forest Dew (20% per Pokémon in Viridian Forest).
2. **Talk** to the elder with them.
3. **Defeat** the trial: talk to the elder again and they send you to it
   (`Route.folk`). A short map up to an arena, fought like a gym in waves
   (see `mechanics.md`, *Gyms*), but by your starter **alone**
   (`wave_team=1`, `wave_species`: its line, in the party and standing).
4. **Evolve** it (party screen: E). Ivysaur, Charmeleon and Wartortle then
   evolve on by level as usual once their own quests exist.

Rewards: ₽600, 400 XP.

| Trial | Wave 1 | Wave 2 | Wave 3 (Trial Master, giant) |
| --- | --- | --- | --- |
| Trial of Leaves (Bulbasaur; forest) | Mud Diggers: Diglett 11, Sandshrew 11 | Stone Rollers: Geodude 12, Geodude 12 | Ivysaur 16 |
| Trial of Flame (Charmander; Mt. Moon) | Crawler Nest: Caterpie 11, Weedle 11 | Spore Grove: Paras 12, Paras 12 | Charmeleon 16 |
| Trial of Tides (Squirtle; Route 22) | Stone Rollers: Geodude 11, Geodude 11 | Rock Burrowers: Diglett 12, Geodude 12 | Wartortle 16 |

Each wave is a trainer battle (trainer XP, no prize money). Tuned so a Lv16
starter gets through with a few Potions (Sandshrew's Sand-Attack is kept
out of the Trial of Tides: Squirtle can't out-hit it alone).

### The feud (Pidgey Lv18, Spearow Lv20)

On Route 22 the Pidgey flocks and the Spearow are at war. Their leaders
stand in Viridian City, glaring at each other: a **Pidgeotto** and a
**Fearow** (townsfolk). Each gives its side's quest once your Pidgey
(Lv18) or Spearow (Lv20) is at its evolution level, in the party or the
reserve. Picking a side: while one is active, the other isn't on offer
(`Quest.excludes`); once it's done, the other opens.

| | Ruffled Feathers (`feud_pidgey`) | Sharp Beaks (`feud_spearow`) |
| --- | --- | --- |
| Giver | Pidgeotto, Viridian City | Fearow, Viridian City |
| 1. Hunt | 8 Spearow (Route 22) | 8 Pidgey (Route 1) |
| 2. Talk | Report to Pidgeotto | Report to Fearow |
| 3. Defeat | **Beak Gang** at the Beak Gang Roost: giant Fearow 17, Spearow 14 ×2 | **Sky Flock** in the Sky Flock Meadow: giant Pidgeotto 21, Pidgey 17 ×2 |
| 4. Evolve | Pidgey into Pidgeotto | Spearow into Fearow |
| Rewards | ₽700, 500 XP | ₽700, 500 XP |

Step 3: talk to the giver again and they send you there (`Route.folk`):
one map (`instance._feud`) full of the other side (groups of 2–3, around
the escorts' level), its band at the end; a trainer battle with the
whole party, then back to the giver. The Fearow comes in lower than the
Pidgeotto: it's far stronger (Attack 90, Speed 100).

### Butterfree, Beedrill and Raticate (Lv10, Lv10, Lv20)

Each from a townsfolk of the species it evolves into, on offer once your
Metapod / Kakuna (Lv10) or Rattata (Lv20) is at its evolution level, in
the party or the reserve. A home ground is a map like the feud's
(`instance._feud`, with its town): talk to the giver again to go there.

| | Spread Your Wings (`evolve_butterfree`) | The Hive (`evolve_beedrill`) | Rat King (`evolve_raticate`) |
| --- | --- | --- | --- |
| Giver | Butterfree, Pewter City | Beedrill, Pewter City | Rattata, Viridian City |
| 1. | Hunt 6 Pidgey (Route 1, Routes 24–25): they prey on Metapod | Collect 4 Royal Jelly (30% per Weedle or Kakuna in Viridian Forest) | Hunt 5 Ekans (Routes 3 and 4) |
| 2. Talk | Tell Butterfree the skies are safe | Bring the jelly to Beedrill | Report to Rattata |
| 3. | – | Defeat the **Hive Queen** in the Beedrill Thicket (forest): giant Beedrill 13, Kakuna 11 ×2 | Defeat the **Rat King's Gang** in the Rat King's Burrows (meadow): giant Raticate 23, Rattata 19 ×2 |
| Last | Evolve Metapod into Butterfree | Evolve Kakuna into Beedrill | Evolve Rattata into Raticate |
| Rewards | ₽400, 300 XP | ₽600, 450 XP | ₽700, 500 XP |

### Nidorina, Nidorino and Kadabra (Lv16)

The same way, once your Nidoran F / Nidoran M / Abra is Lv16. Kadabra's
test is a solo trial like the starters' (`instance._trial`, from Cerulean
City): Abra alone, Poison Pokémon that Psychic moves hit hard.

| | Mother's Thorns (`evolve_nidorina`) | Horn Rush (`evolve_nidorino`) | Bent Spoon (`evolve_kadabra`) |
| --- | --- | --- | --- |
| Giver | Nidorina, Viridian City | Nidorino, Viridian City | Kadabra, Cerulean City |
| 1. | Collect 4 Soft Grass (35% per Nidoran F or Rattata on Route 22) | Hunt 6 Spearow (Route 22) | Hunt 6 Venonat (Route 25) |
| 2. Talk | Bring the grass to Nidorina | Report to Nidorino | Report to Kadabra |
| 3. | – | Defeat the **Horn Brothers** in Horn Hollow (Route 22's look): giant Nidorino 19, Nidoran M 15 ×2 | Pass the **Trial of Mind** (Route 25's look): Venonat 18 ×2; Zubat 19 and Ekans 19; then a giant Kadabra 20 |
| Last | Evolve Nidoran F into Nidorina | Evolve Nidoran M into Nidorino | Evolve Abra into Kadabra |
| Rewards | ₽400, 300 XP | ₽600, 450 XP | ₽700, 500 XP |

### Golbat, Arbok (Lv22), Persian and Machoke (Lv28)

The same way: from a townsfolk of the evolved form, once your Zubat /
Ekans (Lv22) or Meowth / Machop (Lv28) is at its level, in the party or
the reserve; a home ground like the feud's (`instance._feud`), talking to
the giver again to go there. Their evolved forms are placeholders for now
(no PixelLab sheets yet). With a pair (the starter 3 levels up and the
Pokémon at its level, 2 Super Potions), the home grounds are won about
55–60% of the time (`tools/balance_sim.py`-style runs; the Persian, fast
and hard-hitting, comes in lower).

| | Wings in the Dark (`evolve_golbat`) | The Coil Clan (`evolve_arbok`) | Nine Lives (`evolve_persian`) | Heavy Lifting (`evolve_machoke`) |
| --- | --- | --- | --- | --- |
| Giver | Golbat, the Route 6 stop | Arbok, Route 4 (Mt. Moon's exit) | Persian, Vermilion City | Machoke, Lavender Town (the smith's apprentice) |
| 1. | Hunt 6 Diglett (the Underground Path) | Hunt 6 Sandshrew (Routes 3 and 4) | Hunt 6 Mankey (Routes 5 and 6) | Hunt 6 Geodude (Rock Tunnel) |
| 2. Talk | Report to Golbat | Report to Arbok | Report to Persian | Report to Machoke |
| 3. | Defeat the **Night Swarm** in the Golbat Roost (Mt. Moon's look): giant Golbat 27, Zubat 22 ×2 | Defeat the **Coil Clan** in the Snake Pit (Route 4's look): giant Arbok 26, Ekans 22 ×2 | Defeat the **Alley Cats** in the Alley of Cats (Route 6's look): giant Persian 31, Meowth 27 ×2 | Defeat the **Iron Lifters** on the Training Grounds (Route 9's look): giant Machoke 33, Machop 28 ×2 |
| Last | Evolve Zubat into Golbat | Evolve Ekans into Arbok | Evolve Meowth into Persian | Evolve Machop into Machoke |
| Rewards | ₽700, 500 XP | ₽700, 500 XP | ₽900, 700 XP | ₽900, 700 XP |

### Sandslash (Lv22), Parasect (Lv24), Graveler (Lv25) and Hypno (Lv26)

The same way again (the second batch). Tuned like the first: with a pair
(the starter 3 levels up, the Pokémon at its level, 2 Super Potions), the
home grounds are won about 55–63% of the time.

| | Sharp as Spines (`evolve_sandslash`) | The Mushroom Decides (`evolve_parasect`) | Rolling Stones (`evolve_graveler`) | Sweet Dreams (`evolve_hypno`) |
| --- | --- | --- | --- | --- |
| Giver | Sandslash, the Mt. Moon Pokémon Center | Parasect, the Route 5 stop | Graveler, the Route 10 Pokémon Center | Hypno, the Route 11 Gate |
| 1. | Hunt 6 Ekans (Routes 3 and 4) | Hunt 6 Bellsprout (Routes 24, 25 and 5) | Hunt 6 Machop (Rock Tunnel) | Hunt 6 Spearow (Route 11) |
| 2. Talk | Report to Sandslash | Report to Parasect | Report to Graveler | Report to Hypno |
| 3. | Defeat the **Spike Pack** in the Spike Burrows (Route 3's look): giant Sandslash 30, Sandshrew 25 ×2 | Defeat the **Spore Colony** in Mushroom Hollow (the forest's look): giant Parasect 31, Paras 25 ×2 | Defeat the **Boulder Rollers** in the Rumbling Quarry (Diglett's Cave's look): giant Graveler 35, Geodude 28 ×2 | Defeat the **Dream Eaters** in Dreamer's Hollow (Route 11's look): giant Hypno 29, Drowzee 23 ×2 |
| Last | Evolve Sandshrew into Sandslash | Evolve Paras into Parasect | Evolve Geodude into Graveler | Evolve Drowzee into Hypno |
| Rewards | ₽700, 500 XP | ₽800, 600 XP | ₽800, 600 XP | ₽900, 700 XP |

### Primeape (Lv28), Electrode (Lv30), Venomoth (Lv31) and Golduck (Lv33)

The third batch, the same way. Tuned like the others (a pair, 2 Super
Potions): about 56–60%. Primeape's band, hard-hitting, comes in lower;
Electrode's, whose Voltorb may blow themselves up, higher.

| | Anger Management (`evolve_primeape`) | Full Charge (`evolve_electrode`) | Dust to Wings (`evolve_venomoth`) | Clear Headed (`evolve_golduck`) |
| --- | --- | --- | --- | --- |
| Giver | Primeape, the Route 8 Gate | Electrode, the Route 10 Pokémon Center | Venomoth, the top of Route 24 | Golduck, Cerulean City |
| 1. | Hunt 6 Growlithe (Route 8) | Hunt 6 Sandshrew (Routes 9 and 11) | Hunt 6 Pidgey (Routes 24 and 25) | Hunt 6 Meowth (Routes 6 and 8) |
| 2. Talk | Report to Primeape | Report to Electrode | Report to Venomoth | Report to Golduck |
| 3. | Defeat the **Rage Brawlers** in the Brawlers' Ring (Route 8's look): giant Primeape 31, Mankey 26 ×2 | Defeat the **Spark Rollers** on the Static Field (Route 9's look): giant Electrode 38, Voltorb 33 ×2 | Defeat the **Dust Wings** in the Moth Glade (the forest's look): giant Venomoth 37, Venonat 31 ×2 | Defeat the **Headache Club** on Headache Pond (Route 6's look): giant Golduck 39, Psyduck 33 ×2 |
| Last | Evolve Mankey into Primeape | Evolve Voltorb into Electrode | Evolve Venonat into Venomoth | Evolve Psyduck into Golduck |
| Rewards | ₽900, 700 XP | ₽900, 700 XP | ₽900, 700 XP | ₽1000, 800 XP |

### Dugtrio (Lv26)

| | Three Heads Are Better (`evolve_dugtrio`) |
| --- | --- |
| Giver | Diglett, Route 11 Gate |
| 1. | Hunt 6 Dugtrio (Diglett's Cave) |
| 2. Talk | Report to Diglett |
| Last | Evolve Diglett into Dugtrio |
| Rewards | ₽700, 600 XP |

### Mastery: the starters' last forms (Ivysaur Lv32, Charmeleon and Wartortle Lv36)

A harder "Coming of Age", from the **master** of your starter's line
(Master Venusaur, Charizard or Blastoise: the `ELDER`), retired to
Celadon's west end, by the Mansion. First beat 8 of a kind your starter
fears, then a **solo trial** (`instance._trial`, from Celadon West End):
the starter alone through two waves, then a **giant of its final form**.
With the starter at Lv36 and all its talents, the trials are won about
50–60% of the time (`tools/balance_sim.py`-style runs; the giant is the
hard part). The masters are lower-levelled, as a final form's stats are
far above a middle form's.

| | Mastery (`master_ivysaur`) | Mastery (`master_charmeleon`) | Mastery (`master_wartortle`) |
| --- | --- | --- | --- |
| 1. | Hunt 8 Pidgeotto (Route 8) | Hunt 8 Diglett (Underground Path, west) | Hunt 8 Growlithe (Route 8) |
| 2. Talk | Report to the master | Report to the master | Report to the master |
| 3. | **Trial of the Great Tree** (Viridian Forest's look): Graveler 29 and Onix 30; Golduck 30 and Seaking 30; then a giant Venusaur 29 | **Trial of the Inferno** (Mt. Moon's look): Venomoth 29 and Parasect 30; Weepinbell 30 and Gloom 30; then a giant Charizard 29 | **Trial of the Deep** (the Cerulean Gym's look): Graveler 29 and Onix 30; Growlithe 30 ×2; then a giant Blastoise 30 |
| Last | Evolve Ivysaur into Venusaur | Evolve Charmeleon into Charizard | Evolve Wartortle into Blastoise |
| Rewards | ₽1,500, 1,300 XP | ₽1,500, 1,300 XP | ₽1,500, 1,300 XP |

### Pidgeot (Lv36)

| | Lord of the Skies (`evolve_pidgeot`) |
| --- | --- |
| Giver | Pidgeot, Celadon City (east) |
| 1. | Hunt 8 Pidgeotto (Route 8) |
| 2. Talk | Report to Pidgeot |
| 3. | **Trial of the Skies** (Route 25's look), Pidgeotto alone: Venomoth 29 and Butterfree 29; Paras 30 and Bellsprout 30; then a giant Pidgeot 28 (about 45% won at Lv36) |
| Last | Evolve Pidgeotto into Pidgeot |
| Rewards | ₽1,500, 1,300 XP |

### Gloom and Weepinbell (Lv21)

Once your Oddish / Bellsprout (recruited from Route 24) is Lv21. Each
ends on a home ground like the feud's (`instance._feud`): a map of that
line, its giant leader waiting with two of them. With two at Lv23/22,
the leader's band is beaten about 66% (Stench Patch) and 79% (Pitcher
Grove) of the time (`tools/balance_sim.py`). Their next forms come by
the **Leaf Stone** (`The evolution stones`).

| | Sweet Stench (`evolve_gloom`) | Pitcher's Appetite (`evolve_weepinbell`) |
| --- | --- | --- |
| Giver | Gloom, Cerulean City (by the east exit) | Weepinbell, Route 24 (the stop past Nugget Bridge) |
| 1. | Collect 5 Sweet Nectar (35% per Oddish or Bellsprout, from Route 24 on) | Hunt 6 Venonat (Route 25) |
| 2. Talk | Bring the nectar to Gloom | Report to Weepinbell |
| 3. | Defeat the **Stench Patch** (Route 25's look): giant Gloom 26, Oddish 21 ×2 | Defeat the **Vine Lashers** in Pitcher Grove (Route 24's look): giant Weepinbell 26, Bellsprout 21 ×2 |
| Last | Evolve Oddish into Gloom | Evolve Bellsprout into Weepinbell |
| Rewards | ₽900, 700 XP | ₽900, 700 XP |

---

## Recruitment

How the party grows (`world/instance.py` `RECRUITS`, quests made in
`world/quests.py`, screens in `scenes/recruit.py`).

- **Defeat counts:** every Pokémon defeated in a won **wild** battle on a
  route (an ordinary group: not a trainer's band, a gym's wave or a boss)
  counts for its **line** (`Game.defeated`, by the
  line's first species: Metapod counts for Caterpie).
- **Unlocking:** once a line's count reaches its number (`Recruit.needed`,
  10 for most, fewer for rare ones), its **recruitment quest** opens. The
  battle's rewards say so ("Pidgey can be recruited!"), and a "!" shows
  over the Recruitment Centers.
- **Recruitment Centers** (in Viridian, Pewter, Cerulean and Vermilion, for now in one of the
  town's houses): inside, a **recruitment board** with the open
  recruitments' Pokémon pinned on it, and **Mr. Mime** beside it.
  - Up at the board: every recruitable line, locked (with its count),
    Open, Taken or Recruited, and the chosen one's map, levels and
    rewards. **Enter** on an open (or taken) one takes its quest and
    walks straight to its map.
  - Up at Mr. Mime: a few words, then the **team**: swap Pokémon between
    the party (1; 2 once the Route 22 rival is beaten; 3 after the S.S. Anne; see `mechanics.md` →
    Party and reserve) and the reserve, and choose the lead.
- **A recruitment map** ("Pidgey Grounds"): one map that looks like the
  Pokémon's home area, full of groups of 2–3 of it (Lv `level` − 2 to
  `level`), with chests, and a boss: a giant one (Lv `level` + 3, drawn
  double size) with two escorts. Beating it finishes the quest: it **joins
  the party** (the reserve if the party is full), at the boss's level,
  with its skills filled in. The door leads back to the Recruitment Center
  it was walked from.
- **Rewards:** ₽25 × `level`, 20 × `level` XP, and the Pokémon.

| Line | Defeats | Map looks like | Levels | Joins at |
| --- | --- | --- | --- | --- |
| Pidgey | 10 | Route 1 | 4–6 | Lv9 |
| Rattata | 10 | Route 1 | 4–6 | Lv9 |
| Caterpie | 10 | Viridian Forest | 6–8 | Lv11 |
| Weedle | 10 | Viridian Forest | 6–8 | Lv11 |
| Pikachu | 4 | Viridian Forest | 8–10 | Lv13 |
| Spearow | 10 | Route 22 | 7–9 | Lv12 |
| Nidoran F | 10 | Route 22 | 7–9 | Lv12 |
| Nidoran M | 10 | Route 22 | 7–9 | Lv12 |
| Sandshrew | 10 | Route 3 | 12–14 | Lv17 |
| Ekans | 10 | Route 3 | 12–14 | Lv17 |
| Jigglypuff | 8 | Route 3 | 12–14 | Lv17 |
| Zubat | 10 | Mt. Moon | 15–17 | Lv20 |
| Paras | 8 | Mt. Moon | 15–17 | Lv20 |
| Clefairy | 4 | Mt. Moon | 15–17 | Lv20 |
| Oddish | 10 | Route 24 | 17–19 | Lv22 |
| Bellsprout | 10 | Route 24 | 17–19 | Lv22 |
| Abra | 4 | Route 24 | 17–19 | Lv22 |
| Venonat | 10 | Route 25 | 18–20 | Lv23 |
| Meowth | 10 | Route 5 | 19–21 | Lv24 |
| Mankey | 10 | Route 5 | 19–21 | Lv24 |
| Diglett | 8 | Underground Path | 20–22 | Lv25 |
| Psyduck | 6 | Route 6 | 21–23 | Lv26 |
| Drowzee | 8 | Route 11 | 25–27 | Lv30 |
| Voltorb | 5 | Route 9 | 28–30 | Lv33 |
| Geodude | 10 | Rock Tunnel | 29–31 | Lv34 |
| Machop | 8 | Rock Tunnel | 29–31 | Lv34 |
| Onix | 4 | Rock Tunnel | 30–32 | Lv35 |
| Growlithe | 6 | Route 8 | 31–33 | Lv36 |

Not every Pokémon comes this way: the starters, and those only met with
trainers (Geodude, Onix, the S.S. Anne's Machop, Tentacool and
Growlithe, the Vermilion Gym's Voltorb, Magnemite and Raichu), will have
special quests. Trainers' bands, gyms' waves and
bosses don't count towards recruitment: only ordinary wild groups do.

---

## Code

- **Steps done early:** a step to beat a map trainer that's already beaten
  for good (fought before the quest asked for it, e.g. the Nugget Bridge
  rival in dev mode) completes by itself: when its quest starts or reaches
  that step (`quests._skip_beaten`), and for saves stuck on such a step,
  when the save is loaded (`quests.catch_up`, shown on the map).
- `game/world/quests.py`: `Quest` and `Step` data and `QUESTS`; a game's
  quest state (`step`, `is_active`, `is_done`, `current`, `board`,
  `can_take`, `ready_to_hand_in`, `step_text`) and the events that move it
  on (`accept`, `visit`, `defeat`, `reach`, `hand_in`), each returning an `Event` (dialogue, quests started and
  finished with what each gave, `Finished`) for the map scene to show
  (`MapScene.show_event`). `won_battle` (called through
  `BattleScene.on_win`) counts hunts and rolls collect drops, returning
  rows for the battle's rewards.
  Quests with no board start by themselves once their prerequisites are
  done.
- `Quest.money` and `Quest.xp` are required (every quest pays both);
  `Quest.rewards` lists the items. `quests.reward_text` is the board's
  rewards line.
- `Game.quests` (quest key → step reached; the number of steps = done),
  `Game.quest_counts`, `Bag.key_items`, `Bag.money`; all saved.
- Recruitment quests: `Quest.unlock` (line, defeats), board
  `RECRUIT_BOARD`, reward ("pokemon", species, level) → `Reward.pokemon`,
  given by `Game.add_member`. Their routes (`instance.RECRUITS`,
  `_recruit_route`) have no `towns` and `building` "Recruitment Center".
- `Route.needs` / `Route.blocked` (a quest condition for its doorways, and
  what's said when it isn't met; `Route.blocked_done`: what's said instead
  once that quest is done, `quests.blocked_text`), `Route.boss_after` (the boss group once a
  quest is done).
- `scenes/quest_ui.py`: `Dialogue`, `QuestBoard`, `QuestLog`, and the
  "New quest" / "Quest complete" panels. Map scenes show panels one after
  another (`MapScene.show`).
