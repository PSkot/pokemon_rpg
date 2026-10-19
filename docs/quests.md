# Quests

How quests work, and every quest in the game. Keep this file in step with
the code (`game/world/quests.py`, screens in `game/scenes/quest_ui.py`).

**Built:** everything below except the Boulder Badge quest (comes with the
gym battles), and the "catch" / "bring an item" steps.

Quests carry the story (following Red/Blue) and gate progress: some
routes only open once a quest has started or is done, and some areas
change once a quest is finished.

---

## How quests work

### A quest

| Part | What it is |
| --- | --- |
| **Name and summary** | Shown in the quest log. |
| **Prerequisites** | Quests that must be done first. Until then it's *locked* (not shown). |
| **Start** | Taken from a town's **quest board** (`Quest.board`), or *automatic* (as soon as its prerequisites are done, with a notice). Other givers (people, buildings) can come later. |
| **Steps** | Objectives done in order; the quest shows the current one. |
| **Rewards** | Given when the last step is done: medicine, gear (at a rarity and item level), key items. |
| **Unlocks** | What changes once it's started or done: a doorway opens, a route's boss changes, the next quest becomes available. |

### Kinds of steps

| Step | Done when |
| --- | --- |
| **Visit** | You press Up at a building or doorway in a town (e.g. the Viridian Poké Mart). Shows a short dialogue. |
| **Defeat** | You beat a route's boss (a boss group or a trainer). |
| **Reach** | You arrive in a town (or on a route's last map). |
| *Later:* **Catch**, **Bring an item** | Once catching and key items are used more. |

### States, saved in the game

Each quest is *locked*, *available*, *active* (at step *n*) or *done*;
stored in `Game.quests` (quest key → step number, or done). Key items
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
- **Tracker:** the active quest's current step under the location line on
  the map, e.g. "Deliver Oak's Parcel to Professor Oak (Pallet Town)".
- **Markers:** a bouncing "!" over a quest board with something new, and
  over the building the current step needs (when it's in the town you're
  in).
- **Quest log:** pause menu → Quests: active quests with their steps
  (done ones ticked), and finished ones.
- **Notices:** "New quest: …" and "Quest complete: …" banners, plus the
  rewards in a panel (like loot).

---

## The opening chain (Red/Blue)

### 1. Oak's Parcel

- **Starts:** taken from the Viridian City quest board.
- **Steps:**
  1. Visit the **Viridian Poké Mart**: the clerk hands you **Oak's
     Parcel** (key item).
  2. Visit **Professor Oak's Lab** in Pallet Town: Oak takes the parcel
     and gives you the **Pokédex** (key item).
- **Rewards:** 5 Potions (Gen 1 gives Poké Balls here; those can come
  once catching exists).
- **Unlocks:** quest 2; **Viridian Forest** (until then its doorway is
  blocked: "An old man is lying in the road. He hasn't had his coffee
  yet.", as Route 2 is in Red/Blue).

### 2. Rival on Route 22

- **Starts:** automatically when quest 1 is done (Oak: "Your rival went
  west, to Route 22. He wants to battle you!").
- **Steps:**
  1. Defeat your **rival** at the end of Route 22 (Pidgey Lv9 and his
     starter Lv8, as now).
- **Rewards:** the trainer battle's reward roll (as now).
- **Unlocks:** **Route 22** opens when the quest *starts* (its doorway is
  closed before that). Once it's *done*, Route 22's boss becomes a wild
  **Pidgey Lv9 and Spearow Lv9** (no trainer, still the reward roll, no
  chest), so the route stays worth repeating.

### Bugs in the Forest (side quest)

- **Starts:** taken from the Viridian City quest board, once Oak's Parcel
  is done.
- **Steps:** defeat the giant Caterpie (and its escort) in Viridian
  Forest.
- **Rewards:** 2 Super Potions and a Common gear piece (item level 10).

### 3. The Boulder Badge (next)

- **Starts:** automatically on first arriving in Pewter City.
- **Steps:** beat Brock at the Pewter Gym (the gym battles come next).

---

## Code

- `game/world/quests.py`: `Quest` and `Step` data and `QUESTS`; a game's
  quest state (`step`, `is_active`, `is_done`, `current`, `board`,
  `can_take`) and the events that move it on (`accept`, `visit`, `defeat`,
  `reach`), each returning an `Event` (dialogue, quests started and
  finished, rewards given) for the map scene to show (`MapScene.show_event`).
  Quests with no board start by themselves once their prerequisites are
  done.
- `Game.quests` (quest key → step reached; the number of steps = done),
  `Bag.key_items`; both saved.
- `Route.needs` / `Route.blocked` (a quest condition for its doorways, and
  what's said when it isn't met), `Route.boss_after` (the boss group once a
  quest is done).
- `scenes/quest_ui.py`: `Dialogue`, `QuestBoard`, `QuestLog`, and the
  "New quest" / "Quest complete" panels. Map scenes show panels one after
  another (`MapScene.show`).
