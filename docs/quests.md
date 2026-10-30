# Quests

How quests work, and every quest in the game. Keep this file in step with
the code (`game/world/quests.py`, screens in `game/scenes/quest_ui.py`).

**Built:** everything below except the "catch" / "bring an item" steps.

Quests carry the story (following Red/Blue) and gate progress: some
routes only open once a quest has started or is done, and some areas
change once a quest is finished. Board jobs ("defeat 6 Rattata", "collect
5 Pidgey Feathers") fill the gaps between story beats.

**Quests are the main source of XP.** Wild battles give half their Gen 1
XP (`WILD_XP`, see `mechanics.md`); trainer battles give ×1.5, so they
stay worth fighting. Budget up to Pewter City: the quests before it pay
1,800 XP in all, a full run of each route there about 1,500 in battle XP,
so a player who does both arrives around Lv14–15 (the Boulder Gang's Onix is
Lv14, as Brock's in Gen 1). From Pewter to Mt. Moon: the quests pay 1,350 XP (Boulder Badge 400,
Road to Mt. Moon 300, Route 3 jobs 650), the Boulder Gang and its Diggers about
950 in battle XP and Route 3's six trainers about 1,200, so a party
arrives around Lv18–19.

---

## How quests work

### A quest

| Part | What it is |
| --- | --- |
| **Name and summary** | Shown in the quest log. |
| **Prerequisites** | Quests that must be done first. Until then it's *locked* (not shown). |
| **Start** | Taken from a town's **quest board** (`Quest.board`), or *automatic* (as soon as its prerequisites are done, with a notice). Other givers (people, buildings) can come later. |
| **Steps** | Objectives done in order; the quest shows the current one. |
| **Rewards** | Given when the last step is done. **Every** quest pays Poké Dollars (`Quest.money`) and XP (`Quest.xp`, to each party member, as in battle). **Major** quests (rival and gym battles, story milestones) also give items: medicine, gear (at a rarity and item level). Key items come from steps. |
| **Unlocks** | What changes once it's started or done: a doorway opens, a route's boss changes, the next quest becomes available. |

### Kinds of steps

| Step | Done when |
| --- | --- |
| **Visit** | You press Up at a building or doorway in a town (e.g. Professor Oak's Lab), or, for a Poké Mart, at the counter inside (Meowth). Shows a short dialogue. |
| **Defeat** | You beat a route's boss (a boss group or a trainer). |
| **Reach** | You arrive in a town (or on a route's last map). |
| **Hunt** (`hunt(species, count, where)`) | You've beaten `count` of a species in won battles, anywhere (wild or a trainer's). Shown as "Defeat 6 Rattata (Route 1): 3/6". |
| **Collect** (`collect(item, count, route, species, chance, where)`) | You've collected `count` quest items. In every won battle on `route` (wild or trainer), each defeated Pokémon of `species` drops one with `chance` %. Only while the quest is active; they're not bag items, just the count. |
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
  (a speaker's name, pages advanced with Enter). No character sprites for
  now: people "speak" from their buildings.
- **Tracker:** up to 3 active quests' current steps under the location
  line on the map, e.g. "Pest Control: Defeat 6 Rattata (Route 1): 3/6".
- **Markers:** a bouncing "!" over a quest board with something new or a
  quest to hand in, and over the building the current step needs (when
  it's in the town you're in).
- **Quest log:** pause menu → Quests: active quests with their steps
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
  1. Defeat your **rival** at the end of Route 22 (Pidgey Lv9 and his
     starter Lv8, as now).
- **Rewards:** ₽600, 300 XP, 2 Super Potions and an Uncommon gear piece
  (item level 9), on top of the trainer battle's reward roll.
- **Unlocks:** **Route 22** opens when the quest *starts* (its doorway is
  closed before that). Once it's *done*, Route 22's boss becomes a wild
  **Pidgey Lv9 and Spearow Lv9** (no trainer, still the reward roll, no
  chest), so the route stays worth repeating.

### Bugs in the Forest (side quest)

- **Starts:** taken from the Viridian City quest board, once Oak's Parcel
  is done.
- **Steps:** defeat the giant Caterpie (and its escort) in Viridian
  Forest.
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

Each takes about one or two runs of its route. They can't be repeated
yet.

### 3. The Boulder Badge

- **Starts:** automatically on first arriving in Pewter City
  (`Quest.starts_in`).
- **Steps:** defeat the **Boulder Gang** (Rock types led by an Onix) at
  the end of the Pewter Gym (Up at the gym building; the Boulder Gang
  Diggers stand midway). Onix: "I took you for granted.
  As proof of your victory, here's the Boulder Badge!" (key item).
- **Rewards:** ₽500, 400 XP, 3 Super Potions and a **Rare** gear piece
  (item level 14), on top of the gang's prize money (₽693) and reward roll.
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
- **Unlocks:** nothing yet: Route 4 is a stop for now; Cerulean City
  comes next.

---

## Evolution quests

Every evolution is unlocked by a quest (`quests.can_evolve`); a line
without one doesn't evolve yet. These quests don't come from boards:
they start when their key item turns up: dropped in battles
(`Quest.drop`: item, route, species, chance; "You found a Metapod
Shell!" and the New quest notice after the battle), and later from NPCs
or trainer battles (gyms, the rival, Team Rocket). The item can be found
at any time; it's only used once the player has a Pokémon of that
species at its evolution level: the party screen shows "Evolve!" and E
evolves it (or use the item from the bag's Key items on that Pokémon),
using up the item and finishing the quest. After that the
line evolves by level as usual (end of a won battle).

| Quest | Item (drop) | Steps | Rewards |
| --- | --- | --- | --- |
| Cocoon of Steel | Metapod Shell: 15% per Caterpie or Metapod beaten in Viridian Forest | Evolve a Caterpie (Lv7+) into Metapod | ₽200, 100 XP |
| Poison Cocoon | Kakuna Shell: 15% per Weedle or Kakuna beaten in Viridian Forest | Evolve a Weedle (Lv7+) into Kakuna | ₽200, 100 XP |

---

## Recruitment

How the party grows (`world/instance.py` `RECRUITS`, quests made in
`world/quests.py`, screens in `scenes/recruit.py`).

- **Defeat counts:** every Pokémon defeated in a won battle on a route
  (wild or a trainer's) counts for its **line** (`Game.defeated`, by the
  line's first species: Metapod counts for Caterpie).
- **Unlocking:** once a line's count reaches its number (`Recruit.needed`,
  10 for most, fewer for rare ones), its **recruitment quest** opens. The
  battle's rewards say so ("Pidgey can be recruited!"), and a "!" shows
  over the Recruitment Centers.
- **Recruitment Centers** (in Viridian and Pewter, for now in one of the
  town's houses): inside, a **recruitment board** with the open
  recruitments' Pokémon pinned on it, and **Mr. Mime** beside it.
  - Up at the board: every recruitable line, locked (with its count),
    Open, Taken or Recruited, and the chosen one's map, levels and
    rewards. **Enter** on an open (or taken) one takes its quest and
    walks straight to its map.
  - Up at Mr. Mime: a few words, then the **team**: swap Pokémon between
    the party (at most 4) and the reserve, and choose the lead.
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
| Caterpie | 10 | Viridian Forest | 4–6 | Lv9 |
| Weedle | 10 | Viridian Forest | 4–6 | Lv9 |
| Pikachu | 4 | Viridian Forest | 6–8 | Lv11 |
| Spearow | 10 | Route 22 | 6–8 | Lv11 |
| Nidoran F | 10 | Route 22 | 6–8 | Lv11 |
| Nidoran M | 10 | Route 22 | 6–8 | Lv11 |
| Sandshrew | 10 | Route 3 | 8–10 | Lv13 |
| Ekans | 10 | Route 3 | 8–10 | Lv13 |
| Jigglypuff | 8 | Route 3 | 8–10 | Lv13 |
| Zubat | 10 | Mt. Moon | 10–12 | Lv15 |
| Paras | 8 | Mt. Moon | 10–12 | Lv15 |
| Clefairy | 4 | Mt. Moon | 10–12 | Lv15 |

Not every Pokémon comes this way: the starters, and those only met with
trainers (Geodude, Onix, Diglett), will have special quests. Oddish and
Bellsprout are hidden until Routes 24/25 (where they live in Red/Blue)
exist.

---

## Code

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
  what's said when it isn't met), `Route.boss_after` (the boss group once a
  quest is done).
- `scenes/quest_ui.py`: `Dialogue`, `QuestBoard`, `QuestLog`, and the
  "New quest" / "Quest complete" panels. Map scenes show panels one after
  another (`MapScene.show`).
