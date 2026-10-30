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
- Browser build (for phones): `tools/web_build.py` packs the game with
  pygbag into `build/web-app/build/web/` (`--serve`: test on
  localhost:8000; use pygbag's server, as a page on localhost loads
  pygame through it). Hence the async main loop (`await asyncio.sleep(0)`
  per frame). In the browser (`saves.WEB`) save files are mirrored into
  localStorage and restored on start, and `main.fit_canvas` sizes the
  page's canvas each frame. pygbag fetches its template and runtime
  (and pygame, via the generated main.py's imports) from
  pygame-web.github.io.
  `.github/workflows/pages.yml` builds it on every push (main and the
  dev branch) and publishes it on GitHub Pages:
  https://pskot.github.io/pokemon_rpg/
- Code layout (`game/`; module names below are within these folders):
  - `main.py` (game loop), `settings.py`, `saves.py`
  - `engine/`: scenes and transitions (`scene.py`), menu windows and text
    (`ui.py`), sprite animation (`animation.py`), hats on sprites (`hats.py`),
    touch controls (`touch.py`)
  - `mechanics/`: game rules and data: species and stats (`pokemon.py`),
    moves (`moves.py`), skill trees (`skills.py`), damage (`combat.py`),
    types, status conditions, items and gear (`items.py`), loot
  - `world/`: maps (`level.py`), themes, placeholder map art
    (`tileset.py`), towns, routes/instances, the player character,
    progress (`progress.Game`)
  - `scenes/`: title, map scenes (`overworld.py`, `town.py`, `mart.py`), battle,
    party screen (`summary.py`), pause menu, save/load list
  Dependencies point downwards: scenes → world/mechanics → engine.
- `docs/mechanics.md` documents every rule and number (stats, levels/XP,
  damage, status, healing, gear rolls, loot, wild Pokémon, types). When
  changing a rule or number, update it in the same change.
- Test headlessly with `SDL_VIDEODRIVER=dummy`: drive
  `Player.update(dt, Controls(...), level)` and save frames with
  `pygame.image.save()`.
- The game is a set of scenes (`scene.Scene`): title (`title.py`), maps
  (`scenes/overworld.MapScene`: towns in `town.py`, Poké Marts in
  `mart.py`, instance maps in
  `overworld.py`), battle (`battle.py`) and party screen (`summary.py`).
  A scene switches by setting `next_scene`. Scenes
  draw sprites on the logical canvas and text on the scaled window
  (`draw_overlay`), so text stays sharp. `ui.font` draws every size
  `ui.TEXT_SCALE` (1.25) bigger than asked, for phones (`ui.text` keeps
  it centred on its line; touch buttons use `ui.unscaled_font`). In the
  browser, `fit_canvas` smooths the canvas when it's shown smaller than
  its pixels (pixelated, text loses columns).
- Battles: separate battle screen, Final Fantasy style (enemies left, party
  right), strict turn-based: the party picks actions, then everyone's
  actions play out fastest first. Single-target moves/items are aimed in
  the target menu (arrows, or tap a Pokémon / its row; tap again to
  confirm; tapping an enemy in the command menu fights it); it starts on
  the member's last target (`Combatant.last_target`), and the names of
  members who already aimed show under their targets. A spread move (e.g.
  Fight with Sweeping) goes through the target menu too, with an arrow
  over every one it hits (`_aimed`, `_spread_aim`): confirm, or tap any;
  its user's name then shows under all of them. Battle sequences are generator "scripts"
  that yield seconds to wait (`BattleScene._round` / `_perform`).
- Each `Animation` aligns its own baseline (lowest opaque row) to the feet
  position, because rows in a sheet sit at different heights. Rows whose
  effects reach below the feet pass an explicit `baseline=` instead (one
  row, or a tuple per frame with None = the frame's own).
- Gear (`items.py`): each Pokémon has typed slots (head, held, worn, berry).
  Gear is rolled (`Gear.roll`): the item's own effect plus random affixes
  (prefixes/suffixes, e.g. "Fierce Red Bandana of the Aerodactyl"; suffixes
  are named after Pokémon). Rarity (Common/Uncommon/Rare/Epic/Legendary)
  sets the affix count (0, 1, 2–3, 3–4, 4–5) and multiplies rolled
  bonuses, not penalties. Item level (`Gear.level`) = the level needed to
  equip it (`usable_by`); it also scales stat/power/damage bonuses
  (`level_factor`, +4%/level), not chances. Drops get the defeated
  Pokémon's level, chests the area's level range. Mods:
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
  gear at weighted rarities), rolled 1+ times; built per set of rarity
  weights (`wild_loot`, `chest_loot`, `boss_loot`). Each `Route` sets which
  rarities drop (`loot`, `boss_loot`): early on Common only, Uncommon from
  bosses; Rare and up are for later areas. A won battle rolls the
  battle's table once per enemy; Poké Balls on the map (`Level.balls`,
  `overworld.Ball`, 2–4 a map, Up) give one item (`ball_loot`); the rarer
  `Chest`s (`level.CHEST_CHANCE`; Up) roll their table once. Both show a `ui.ListPanel`. The starter begins
  with just a Common Oran Berry.
- XP (`pokemon.py`): defeating a Pokémon is worth `base_exp × level / 7`
  (Gen 1; `Species.base_exp`), and reaching a level takes `level³` total XP.
  A won battle gives every party member still standing the XP of all the
  enemies (`BattleScene._give_xp`; ×0.5 wild, ×1.5 trainer), filling the
  XP bar and leveling up (keeping the damage taken). Quests are the main
  XP source.
- Skills (`skills.py`, `docs/skill_trees.md`): moves come from skill trees
  (one per evolution line, `TREES`), not learn levels. Skill points =
  level − 5; a skill opens by level + all its parents + evolution stage.
  Kinds: moves (each Gen 1 move one 1-point skill, linked by paths; the
  free ones are base attacks, the first = Fight; 4 equipped,
  `Monster.equipped`), buffs (1–5 ranks, branches off one move, generated
  per kind of move by `skills._buffs`: Potent, riders, Wounding, Sweeping,
  capstones, ...) and links (`Link`: two moves; the first sets off the
  second, `Move.triggers`). A rank is a dict of `Move` field changes,
  added up by `apply_changes`; `SkillTree.effective_move` applies them
  (`Monster.move(key)`). Trees cost 115–207 points (95 at Lv100): builds
  choose. Every line in the game has a tree (`docs/skill_trees.md`'s
  tables are generated: `python tools/skill_docs.py`). `Monster.create` auto-builds skills (wild Pokémon,
  starter). The skill
  tree screen (`scenes/skill_tree.py`, party screen → S: a panning node
  map, `layout`, with a mini-map (M; tap/drag on it to jump); arrows go
  to the nearest node that way, taps pick a node, Q/W switch Pokémon) spends points,
  equips moves and resets points (towns only, `Scene.in_town`). A species
  without a tree gets Tackle (`stand_in_tree`). Battle: stat stages
  incl. accuracy (`Combatant.stages`; misses only come from lowered
  accuracy), priority, multi-hit, flinch, confusion, bind, Leech Seed,
  spread moves, recoil, recharge, drain, Rest, Focus Energy, Toxic,
  wounds (`Move.bleed`), stages on the user (`self_stages`), set-off
  moves (`BattleScene._apply`).
- Evolution (`pokemon.py`): `EVOLUTIONS` lists every Red/Blue level
  evolution (species key → `Evolution(into, level)`); trade/stone
  evolutions aren't in yet. An evolution is only active once its target
  is in `SPECIES` (`Species.evolution`) and its evolution quest unlocks it
  (`quests.can_evolve`: a quest whose step is "evolve" that species; no
  quest = no evolution). Evolution quests don't come from boards: they
  start when their key item drops (`Quest.drop`; Metapod/Kakuna Shell in
  Viridian Forest), later also from NPCs or trainer battles. The first
  time, E on the party screen evolves an eligible member (same flashing,
  `quests.evolve`, finishes the quest); once done, members that leveled
  up in a won battle and reached the level evolve (`BattleScene.evolves`,
  `_evolve`: X stops it, retried at the next level-up). The map player
  takes the lead Pokémon's species (`Player.become`).
- Medicine (`items.MEDICINE`: potions, Revive, status cures) is counted in
  `Bag.medicine` and used from the battle's Item menu (taking the user's
  turn; items act before moves) or from the bag. The Escape Rope is in
  `MEDICINE` too (`Medicine.escape`: not in battle; from the bag on an
  instance map → `TownScene` of `Game.town`). An item is only used up
  when it has an effect (`Medicine.has_effect`: Revive only on the
  fainted, the rest only on the standing).
- The bag (`scenes/bag.py`, `BagScreen`; pause menu → Bag, or I / the
  Bag touch pill on maps): pockets Items (medicine on a party member,
  `Medicine.use_on`; Escape Rope), Gear (equip on a party member) and
  Key items (`items.KEY_ITEMS` descriptions; an evolution item on an
  eligible member, `quests.item_evolves`, opens the party screen
  evolving it). Hosted by the pause menu like its other screens;
  `loaded` switches scene.
- Status conditions (`status.py`): burn, poison, paralysis, sleep, freeze;
  one per Pokémon, stored on `Monster` and kept after battle; cleared on
  fainting. Asleep/frozen party members skip the menu. Cured by medicine.
- Types (`type_chart.py`): the 15 Gen 1 types and chart (Ghost→Psychic fixed to
  2×). Species have 1–2 types, moves one (or none). STAB ×1.5.
- Maps (`level.py`): a tile grid (16 px tiles; "#" solid, "=" one-way
  platform) generated from a seed and a theme (`themes.py`: tile palette,
  weighted encounter pool with level ranges, group sizes, battle backdrop,
  cave ceiling). Maps scroll sideways and end at a doorway (Up) to the next
  map. Wild groups are shown in full and stay gone once beaten.
- World: the game follows the Kanto map. Towns (`towns.py` data,
  `town.py` scene) are flat maps with Pixellab buildings (scenery, except Poké Marts;
  `Building.sprite` = (sheet, cell) of `houses.png` /
  `functional_buildings.png`, 2×2 cells of 128×128, drawn by
  `tileset.draw_building` standing on their base row) and doorways onto
  routes (`Town.exits`: at an edge, or at a column inside the town, e.g.
  Viridian's Route 22 door; Pewter → Route 3 → the Mt. Moon Pokémon
  Center stop → Mt. Moon (a dungeon) → Route 4). Poké Marts can be entered
  (`Building.inside = "mart"`; `scenes/mart.py`: a one-screen room,
  `tileset.room`: a painted wall and floor, `rooms/<name>_wall.png` /
  `_floor.png` drawn 2×, with Pixellab shelves, counter and glass door
  props; run by a Meowth: an idle
  animation, `props/meowth.png`, `tileset.npc_frames`): Up at the counter does a quest step there,
  else opens the shop (`ShopMenu`: buy the town's stock, `Town.mart`;
  sell medicine for half; `Medicine.price`); Up at the door goes back
  out (`TownScene(arrive=building name)`). Saving inside saves the player
  outside the shop. Only medicine is sold for now (gear later). The user
  makes the PixelLab art themselves: don't generate it unasked.
  A new game starts in Pallet Town; arriving in
  a town heals the party and makes it the town a fainted party wakes up
  in (`Game.town`). Progress lives in `progress.Game`
  (party, bag, last town, routes cleared).
- Instances (`instance.py`): a `Route` (Route 1: 2 meadow maps, Pallet ↔
  Viridian; Viridian Forest: 3 forest maps, Viridian ↔ Pewter, with a boss;
  Route 22: 2 maps from Viridian and back, with the rival at the end)
  is walked as an `Instance` of generated maps from one seed; every trip
  rolls a new seed, and the last map's doorway leads into the town at the
  other end. A route with `boss=True` ends in an arena where a boss group
  (`boss_group`, or else 4–5 pool Pokémon) guards the sealed way out,
  drawn `boss_scale` times bigger (`Monster.scale`, `animations(species,
  scale)`); beating it unseals the door and drops a boss chest (or, with
  `boss_chest=False`, the boss loot comes with the battle). A route with
  `trainer` makes the boss fight a trainer battle (no running, ×1.5 XP).
  `RIVAL_STARTER` in a boss group becomes the rival's starter, which beats
  the player's (`Game.starter`, `Game.rival_starter`). Routes can have
  map trainers (`Route.trainers`, `Trainer`: bands of Pokémon named for
  their team, e.g. "Crawler Swarm" (no human trainers in this game; each
  stands in for a Gen 1 trainer); each takes one of a map's
  wild-group spots, `overworld._spread`; name over the team; fight once,
  `Game.trainers`; prize money = base × last level / 2, `prize_money`;
  boss trainers use `Route.prize`). Gyms are routes walked from their
  building (`Route.building`, `wild=False`: no wild Pokémon or chests): a
  short walk (`Route.cols`) up to an arena, fought in waves: touching the
  band opens `scenes/gym.TeamPick` (pick `Route.wave_team` = 2), then
  `OverworldScene._start_waves` chains the battles (`Route.waves`, then
  the boss group; `BattleScene.wave`/`next_battle`), no healing in
  between; losing one loses the gym. The Pewter Gym: Boulder Gang
  Diggers, Rollers, then the Boulder Gang (Geodude, Onix led by the Onix);
  shut once the Boulder Badge is won, `needs` "not_done"). Dungeons (Mt. Moon, `Route.rooms`): `Room`s
  joined by `Stair`s (ladder "up"/"down" to another room, arriving at its
  stair back; "out" doorway to a town); each room is laid out from its own
  fixed seed (`generate(cols=, stairs=)`: flat, clear ground at each
  stair) with wild Pokémon rolled per trip; `Instance.rooms` keeps rooms'
  beaten/opened state for the trip (saved); a room's `boss_group` guards
  its last stair (`overworld.Ladder`, sealed with rocks). The Mt. Moon
  Pokémon Center stop (town "mt_moon") is the checkpoint before the cave;
  Up at any Pokémon Center heals and sets the respawn town. Route 4 is a
  stop on the far side for now. Code-drawn caves take their colours from
  `Theme.cave` (`CaveLook`) and ceiling decor from `tileset.CEILING_DECOR`.
  Themes (`themes.py`) pick their map art with `Theme.art` ("woods":
  Pixellab ground and background; "cave": drawn in code). `tileset.py` draws the meadow's ground
  from `tileset_woods.png` (`_render_woods`); the ice cave's tiles and all
  one-way platforms are still drawn in code. The
  meadow's background (towns and routes) is Pixellab art: a sky gradient
  with clouds, then three parallax strips (`MEADOW_STRIPS`: far mountains,
  mid hills, near tree line; 20/35/50% of the camera). `backgrounds()`
  returns (layer, parallax) pairs. The player collides with a fixed hitbox.
- Saves (`saves.py`): JSON files in `saves/`: one `autosave.json` (written
  after every won battle, opened chest, party faint and leaving a map) and
  numbered manual saves (pause menu → Save game; not during battles). A
  save stores the `Game` and the map scene's `location()`: the town and
  position, or on an instance the route, seed, map number, beaten groups,
  opened chests and position (`restore` puts it back); maps are
  regenerated from the seed. Scenes say what can be saved via
  `Scene.save_point()`. The game starts at
  the title screen (`title.py`: Continue / Load game / New game); the save
  and load lists are `save_menu.SaveList`. New game opens the starter
  choice (`scenes/starter.py`: Bulbasaur, Charmander or Squirtle,
  `progress.STARTERS`; `Game.new(starter)`, saved as `Game.starter`).
- Quests (`world/quests.py`, `docs/quests.md`): `QUESTS` with steps (visit
  a building in a town, defeat a route's boss, reach a town), taken from a
  town's quest board (`Town.board_col`) or started automatically once their
  prerequisites are done (`Quest.starts_in`: only on arriving in that
  town, e.g. the Boulder Badge in Pewter). Board jobs: hunt (defeat N of a species) and
  collect (N quest items dropped by species on a route,
  `quests.won_battle` via `BattleScene.on_win`), handed in at any board
  (`HAND_IN`); counts in `Game.quest_counts`. Quests are the main XP
  source (wild battles ×0.5, `WILD_XP`; trainers ×1.5). Every quest pays Poké Dollars and XP
  (`Quest.money`, `Quest.xp`: XP to each party member); major quests
  (rival, gyms) also give items (`Quest.rewards`). State in
  `Game.quests`, key items in `Bag.key_items`, money in `Bag.money`
  (₽, `items.money_text`; `ui.text` draws the ₽ sign itself). Quest events return an `Event` the map scene shows
  (`MapScene.show_event`: dialogue, "New quest", "Quest complete" with
  rewards); map panels queue (`MapScene.show`). Routes can be gated
  (`Route.needs`/`blocked`) and change boss after a quest (`boss_after`).
  Screens in `scenes/quest_ui.py` (dialogue box, quest board, quest log in
  the pause menu); the map shows the current step and "!" markers.
- Recruitment (`docs/quests.md` → Recruitment): won route battles count
  defeated Pokémon per line (`Game.defeated`, `pokemon.line_base`); at
  `instance.RECRUITS[line].needed` its recruitment quest opens (board
  `quests.RECRUIT_BOARD`, `Quest.unlock`). Recruitment Centers
  (`Building.inside = "recruit"`, a house for now; `scenes/recruit.py`:
  a painted room (`tileset.room("recruit")`) with the cork board and Mr. Mime (`props/mr_mime.png`), `RecruitBoard`, `TeamPanel`) send the
  player to the line's map (a generated route: only that species, a giant
  boss); beating it adds it (`Game.add_member`: party of at most
  `MAX_PARTY` = 4, else `Game.reserve`). Mr. Mime swaps party and reserve.
- Tab on the map opens the party screen (`summary.py`): stats and gear;
  Enter on a slot lists the bag's gear for it (or Remove), previewing the
  stat changes (Now / Gear / New / Change) and each mod's difference from
  the worn item (mods it would lose struck through), and equips it. S opens the skill tree screen.
- Dev mode (`dev.py`, `DEV`): switched on in the pause menu; not saved.
  XP boost (×1/3/5/10/20, `DEV.xp_multiplier` in `_give_xp`), god mode
  (`DEV.god_mode`: the party takes no damage, every hit knocks an enemy
  out) and an item maker (`scenes/dev_menu.ItemMaker`: any gear with
  chosen rarity/affixes and random/min/max values, or medicine, into
  `Scene.bag`) and Teleport (Left/Right picks a town; Enter goes there,
  as a fresh arrival: healed, it becomes the respawn town; from map scenes
  only). Active settings show in the window title and on the map.
- Controls: arrows move, Up opens chests, Shift runs, Space jumps. (There are
  no attacks on the map: fights happen in battles.)
- Touch controls (`engine/touch.py`, for phones): a virtual gamepad in
  side panels: with them on, the window is wider (`touch.window_size()`,
  `SIDE` px each side) and the game is drawn in the middle
  (`touch.view_rect()`; `main.py` gives scenes that subsurface as
  `window`). Buttons post the same KEYDOWN/KEYUP events as the
  keyboard; held keys are read with `touch.pressed()` (instead of
  `pygame.key.get_pressed()`). Presses (fingers, or the mouse) on the game
  that miss the buttons become taps for the scene (`touch.taps` →
  `Scene.tap(pos, drag)`, logical px; the skill tree uses them).
  D-pad (arrows), A = Space (jump/confirm),
  B = X (back), Menu = Esc, Party = Tab; on maps (`Scene.touch_map`) also
  Run (a toggle); scenes add their own keys as pills
  (`Scene.touch_keys`: party screen S, skill tree E/R; pills under
  Party). On for touch screens in the browser (decided before the window
  is made), or with `POKEMON_TOUCH=1` (mouse = finger) on desktop.
  The player sets the layout (`touch.Layout`: button size, panel width
  down to 0 = buttons over the game, see-through; each side's buttons
  moved across/up) in pause menu → Controls (`scenes/controls_menu.py`,
  only with touch on; every button shows meanwhile). Positions come from
  `touch.SPOTS` (the default layout) placed by the layout (`_placed`).
  Changing the panel width remakes the window (main loop). Saved in the
  player's settings (`saves.load_prefs`/`save_prefs`: `saves/settings.json`,
  mirrored to localStorage like saves; key "touch").
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
- `pidgeotto.png` and `pidgeot.png` (generated through the PixelLab MCP
  connector): the same rows as `pidgey.png`, but 88×88 cells (`AnimSpec.cell`,
  room for spread wings) and 5 frames a row (the still pose, then 4
  generated frames). Pidgeot is drawn 1.2× (`Species.size`, nearest-neighbour
  `Animation.scaled`) so the line grows in size.
- `ivysaur.png`, `charmander.png` and `squirtle.png` have the same rows
  as `bulbasaur.png` (no extra-attack sheets yet: their skills use the
  basic attack animation).
- `venusaur.png`, `charmeleon.png`, `charizard.png`, `wartortle.png` and
  `blastoise.png` (generated with PixelLab, styled after the line's
  earlier sheets): the same rows as `bulbasaur.png` in 88×88 cells, 5
  frames a row (still pose + 4), the jump row's 4 frames being crouch,
  rise, fall, land. The final stages are drawn 1.2× (`Species.size`).
- Idle animations: `<species> idle.png` (one row, 8 frames, the sheet's
  cell size) for the starter lines and the Pidgey line; the Pidgey line
  also has `<species> run.png` (same layout). Generated with PixelLab
  (pixminimax) from each sheet's still pose.
- The species met up to Mt. Moon (Rattata ... Clefairy) have one PixelLab
  sheet each, `<species>.png` (`pokemon._animated`): 64×64 cells, rows
  idle, walk, run (8 frames each, looping), attack (9 frames: still
  pose + 8) and jump (crouch, rise, fall, land: picked from 9 generated
  frames). `hit=` is the attack frame that strikes; the attack is cut
  one frame after it (battles strike on the second-to-last frame). Their
  sprites are drawn small in the 64 px cells (bases generated at 32/44 px,
  roughly to scale with each other; side profiles facing right); Onix
  keeps its larger sheet, drawn 1.5×. Geodude's attack (a lunge) and jump
  are made from its base pose rather than generated. Placeholder
  quality: likely to be redone.
- Every species' animations are defined in `pokemon.py` (`AnimSpec`: sheet,
  row, fps, baseline, ...) and shared by the map player and battles.
- Background art (`tileset.py`): `background.png` (64×64 cells) rows 3–4
  are clouds (the white ones: `CLOUDS`). `background_far.png` (64×64,
  rows 3–4), `background_mid.png` (64×32, rows 2–7) and
  `background_near.png` (64×64) are strip pieces that join up side by
  side; cells have a 1px transparent gutter on each side facing another
  cell. Each layer (`StripArt`) is chained at random per map from pieces
  whose edges fit (`max_step`, `max_colour`); the far mountains' flat
  bands are also evened out at each join (`smooth`).
- `tileset_woods.png` (32×32 cells, 1px gutter on both sides): grass tops
  (rows 1–2, `GRASS_TOPS`) have the grass line at row 16 with plants above;
  each flat stretch of ground gets a strip chained from them, using only
  the 12 rows of grass and soil under the line (the cells end in a dark
  band meant for thin ledges). Below: plain soil speckled like the sheet's
  soil cell, with its pebbles. Step sides are drawn in the sheet's colours
  (its cliff cells don't fit 1–2 tile steps). Row 3 sits 3px lower,
  slopes/islands/roots aren't used yet.
- Battle backdrops (`assets/sprites/pixellab/backdrops/`, `Backdrop.art`):
  320×132 Pixellab paintings drawn 2× over the battle area (meadow, forest,
  route_3, pewter_gym, mt_moon), their ground starting high enough for the
  back row; themes without one (ice cave) are drawn in code from the
  `Backdrop` colours.
- Map props (`assets/sprites/pixellab/props/`, `tileset.draw_prop`: centred,
  standing on the ground): chests (closed/open, plain and the boss's fancy
  one), the Poké Ball, the quest board (its notes are drawn in code, one
  per quest on offer), doorways (`Theme.doorway`: a stone arch outside, a
  rock arch in Mt. Moon; "" = drawn in code, boards over a sealed one in
  code) and the ladder (its 16 px middle repeated to any height).
- Painted far layers (`assets/sprites/pixellab/far/`, `Theme.far`): Viridian
  Forest's and Route 3's maps show a 320×180 painting (drawn 2×, mirrored
  every other copy) instead of the meadow's sky and hills, with the
  meadow's tree line in front.
- The title screen's background: `backdrops/title.png` (dark bands keep
  the title and save line readable).
- Cave walls (`assets/sprites/pixellab/walls/`, `CaveLook.wall`): 320×180
  paintings of Mt. Moon's and the Pewter Gym's far wall, drawn 2×,
  mirrored every other copy, dimmed (`dim`); the code-drawn rock in front
  stays (`near_rocks`, off in the gym).
- `assets/sprites/pokemon_icons/` holds reference icons. Species without a
  Pixellab sheet use their icon as a still placeholder sprite
  (`Species.icon`; mirrored to face right) until they get one.
