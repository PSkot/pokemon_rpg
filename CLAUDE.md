# Pokémon RPG Platformer

2D RPG platformer fan game following the Kanto (Red/Blue) story. Personal,
non-commercial project.

## Working style

- Build the game slowly, one part at a time: get each part right ("perfect")
  and confirmed by the user before starting the next.
- Show results visually where possible (screenshots, previews) before moving on.

## Tech

- Python + pygame-ce (`import pygame`); dependencies in `requirements.txt`,
  installed into `.venv/`.
- Run with `.venv/bin/python -m game`. The game renders at 640×360 and
  scales ×2.
- Code layout (`game/`; module names below are within these folders):
  - `main.py` (game loop), `settings.py`, `saves.py`
  - `engine/`: scenes and transitions (`scene.py`), menu windows and text
    (`ui.py`), sprite animation (`animation.py`), hats on sprites (`hats.py`)
  - `mechanics/`: game rules and data: species and stats (`pokemon.py`),
    moves (`moves.py`), skill trees (`skills.py`), damage (`combat.py`),
    types, status conditions, items and gear (`items.py`), loot
  - `world/`: maps (`level.py`), themes, placeholder map art
    (`tileset.py`), towns, routes/instances, the player character,
    progress (`progress.Game`)
  - `scenes/`: title, map scenes (`overworld.py`, `town.py`), battle,
    party screen (`summary.py`), pause menu, save/load list
  Dependencies point downwards: scenes → world/mechanics → engine.
- `docs/mechanics.md` documents every rule and number (stats, levels/XP,
  damage, status, healing, gear rolls, loot, wild Pokémon, types). When
  changing a rule or number, update it in the same change.
- Test headlessly with `SDL_VIDEODRIVER=dummy`: drive
  `Player.update(dt, Controls(...), level)` and save frames with
  `pygame.image.save()`.
- The game is a set of scenes (`scene.Scene`): title (`title.py`), maps
  (`scenes/overworld.MapScene`: towns in `town.py`, instance maps in
  `overworld.py`), battle (`battle.py`) and party screen (`summary.py`).
  A scene switches by setting `next_scene`. Scenes
  draw sprites on the logical canvas and text on the scaled window
  (`draw_overlay`), so text stays sharp.
- Battles: separate battle screen, Final Fantasy style (enemies left, party
  right), strict turn-based: the party picks actions, then everyone's
  actions play out fastest first. Battle sequences are generator "scripts"
  that yield seconds to wait (`BattleScene._round` / `_perform`).
- Each `Animation` aligns its own baseline (lowest opaque row) to the feet
  position, because rows in a sheet sit at different heights. Rows whose
  effects reach below the feet pass an explicit `baseline=` instead.
- Gear (`items.py`): each Pokémon has typed slots (head, held, worn, berry).
  Gear is rolled (`Gear.roll`): the item's own effect plus random affixes
  (prefixes/suffixes, e.g. "Fierce Red Bandana of the Aerodactyl"; suffixes
  are named after Pokémon). Rarity (Common/Rare/Epic/Legendary) sets the affix
  count (1–2 … 4–5) and multiplies rolled bonuses, not penalties. Mods:
  stats in %, `crit` (% points, base 6.25%), `power` (added to move power),
  `power:<type>` (% on that type's moves), `added:<type>` (every hit deals
  that % extra as that type), `status:<status>` (% chance a hit inflicts
  it), `first` (Quick Claw), `endure` (Focus Band), `super`, `regen`,
  `drain`, `berry_heal`/`berry_attack`; cure berries use `Item.cures`.
  Berries are eaten at most once per battle (`BattleScene._berry`), not
  used up. `Monster.attack` etc. include gear; `base_*` don't.
- Hats (`hats.py`): head-slot items (`items.HATS`) are cells of
  `hats_new.png`, drawn on the Pokémon wearing them (map, battle, party
  screen). The cells' reference faces are cut out on load, so the Pokémon's
  face shows through. Placement comes from `hat_anchors.json`: a head anchor
  per animation frame (`Animation.heads`) and per-hat tweaks. Edit it with
  `tools/hat_viewer.py`; species without head anchors don't show hats.
- Loot (`loot.py`): `LootTable`s of weighted entries (nothing / medicine /
  gear at weighted rarities), rolled 1+ times. A won battle rolls the
  battle's table once per enemy (`WILD_LOOT` by default); a `Chest` on the
  map (opened with Up) rolls `CHEST_LOOT` once. Both show a `ui.ListPanel`.
- XP (`pokemon.py`): defeating a Pokémon is worth `base_exp × level / 7`
  (Gen 1; `Species.base_exp`), and reaching a level takes `level³` total XP.
  A won battle gives every party member still standing the XP of all the
  enemies (`BattleScene._give_xp`), filling the XP bar and leveling up
  (keeping the damage taken).
- Skills (`skills.py`, `docs/skill_trees.md`): moves come from skill trees
  (one per evolution line, `TREES`), not learn levels. Skill points =
  level − 5; skills open by level + parent skill + evolution stage, ranks
  1–5. Kinds: base attacks (free; the first is the basic attack = Fight),
  moves (4 equipped, `Monster.equipped`), modifiers (change one move). A
  rank/modifier is a dict of `Move` field changes;
  `SkillTree.effective_move` applies them (`Monster.move(key)`).
  `Monster.create` auto-builds skills (wild Pokémon, starter). The skill
  tree screen (`scenes/skill_tree.py`, party screen → S) spends points,
  equips moves and resets points (towns only, `Scene.in_town`). Lines
  without a tree use their species' `moves` as base attacks
  (`stand_in_tree`). Battle: stat stages (`Combatant.stages`), Leech Seed,
  spread moves, recoil, recharge, Toxic.
- Evolution (`pokemon.py`): `EVOLUTIONS` lists every Red/Blue level
  evolution (species key → `Evolution(into, level)`); trade/stone
  evolutions aren't in yet. An evolution is only active once its target
  is in `SPECIES` (`Species.evolution`). After a won battle, members that
  leveled up and reached the level evolve (`BattleScene._evolve`: white
  flashing; X stops it, retried at the next level-up). The map player
  takes the lead Pokémon's species and attack animations (`Player.become`:
  key 1 = basic attack, 2–5 = equipped moves).
- Medicine (`items.MEDICINE`: potions, Revive, status cures) is counted in
  `Bag.medicine` and used from the battle's Item menu. Using one takes the
  user's turn; items act before moves. An item is only used up when it
  has an effect.
- Status conditions (`status.py`): burn, poison, paralysis, sleep, freeze;
  one per Pokémon, stored on `Monster` and kept after battle; cleared on
  fainting. Asleep/frozen party members skip the menu. Cured by medicine.
- Types (`type_chart.py`): the 15 Gen 1 types and chart (Ghost→Psychic fixed to
  2×). Species have 1–2 types, moves one; Fight is typeless. STAB ×1.5.
- Maps (`level.py`): a tile grid (16 px tiles; "#" solid, "=" one-way
  platform) generated from a seed and a theme (`themes.py`: tile palette,
  weighted encounter pool with level ranges, group sizes, battle backdrop,
  cave ceiling). Maps scroll sideways and end at a doorway (Up) to the next
  map. Wild groups are shown in full and stay gone once beaten.
- World: the game follows the Kanto map. Towns (`towns.py` data,
  `town.py` scene) are flat maps with placeholder buildings (scenery for
  now) and doorways at their edges onto routes. A new game starts in
  Pallet Town; arriving in a town heals the party and makes it the town a
  fainted party wakes up in (`Game.town`). Progress lives in `progress.Game`
  (party, bag, last town, routes cleared).
- Instances (`instance.py`): a `Route` (e.g. Route 1: 2 meadow maps
  between Pallet and Viridian) is walked as an `Instance` of generated maps
  from one seed; every trip rolls a new seed, and the last map's doorway
  leads into the town at the other end. Routes have no boss; an instance
  with `boss=True` (future dungeons) ends in an arena where a boss group of
  4–5 pool Pokémon (normal levels; stronger variants are kept for
  gyms/legendaries) guards the sealed way out; beating it unseals the door
  and drops a `BOSS_LOOT` chest. `tileset.py` draws placeholder tiles,
  decorations, buildings and parallax backgrounds in code (to be replaced
  by Pixellab tilesets). The player collides with a fixed hitbox.
- Saves (`saves.py`): JSON files in `saves/`: one `autosave.json` (written
  after every won battle, opened chest, party faint and leaving a map) and
  numbered manual saves (pause menu → Save game; not during battles). A
  save stores the `Game` and the map scene's `location()`: the town and
  position, or on an instance the route, seed, map number, beaten groups,
  opened chests and position (`restore` puts it back); maps are
  regenerated from the seed. Scenes say what can be saved via
  `Scene.save_point()`. The game starts at
  the title screen (`title.py`: Continue / Load game / New game); the save
  and load lists are `save_menu.SaveList`.
- Tab on the map opens the party screen (`summary.py`): stats and gear;
  Enter on a slot lists the bag's gear for it (or Remove), previewing the
  stat changes, and equips it. S opens the skill tree screen.
- Dev mode (`dev.py`, `DEV`): switched on in the pause menu; not saved.
  XP boost (×1/3/5/10/20, `DEV.xp_multiplier` in `_give_xp`), god mode
  (`DEV.god_mode`: the party takes no damage, every hit knocks an enemy
  out) and an item maker (`scenes/dev_menu.ItemMaker`: any gear with
  chosen rarity/affixes and random/min/max values, or medicine, into
  `Scene.bag`). Active settings show in the window title and on the map.
- Controls: arrows move, Up opens chests, Shift runs, Space jumps, number keys 1–9 are
  reserved for attacks (1 = basic attack, 2–5 = equipped moves).
- `tools/` holds standalone helper scripts. `tools/anim_viewer.py` uses only
  the standard library (it renders an HTML page and opens it in the browser).
- Firefox on this machine is a snap and cannot open files under `/tmp`;
  write files it needs to open inside the project (e.g. `build/`).

## Assets

- Sprite sheets in `assets/sprites/pixellab/`: grid of 64×64 frames, one
  animation per row, sprites face right (mirror for left). Row order:
  walk, run, jump (crouch/rise/fall/land), attack.
- `bulbasaur attacks.png` holds move animations, one per row: growth,
  solar_beam, leaf_shield, tackle (a move's `anim`; moves without one use
  the species' `fight_anim`).
- `pidgey.png` rows: walk, fly, gust, tackle. Its frames don't all face
  right; the left-facing ones are listed in `face_left` and mirrored on load.
- `ivysaur.png` has the same rows as `bulbasaur.png` (no extra-attack sheet
  yet: its skills use the basic attack animation).
- Every species' animations are defined in `pokemon.py` (`AnimSpec`: sheet,
  row, fps, baseline, ...) and shared by the map player and battles.
- `assets/sprites/pokemon_icons/` holds reference icons. Species without a
  Pixellab sheet use their icon as a still placeholder sprite
  (`Species.icon`; mirrored to face right) until they get one.
