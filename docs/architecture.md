# Architecture notes

Detailed notes on how each part of the game is built, moved out of
`CLAUDE.md` so they only load when needed. Read the section for the area
you are working on.

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
  page's canvas each frame. Pause menu → Fullscreen (browser only, not
  on iPhones) toggles fullscreen (`engine/fullscreen.py`: a JS helper on
  the page, retried when the key/finger is let go, as browsers only allow
  it during a press). pygbag fetches its template and runtime
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
    moves (`moves.py`), talents (`talents.py`), damage (`combat.py`),
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
  members who already aimed show under their targets. A spread move on
  enemies (e.g. Fight with Sweeping) is aimed too: a big arrow over the
  main target (full damage, and any set-off move goes there), small ones
  over the rest (`_splashed`, at `Move.spread_share`; `_land`); one on the
  own side just hits them all (`_spread_aim`: confirm, or tap any). Its
  user's name shows under everyone it hits. Each party member's
  menus open on what it chose last (`Combatant.last_command`/`last_skill`).
  In the Skills list, O (touch: Reorder moves) carries the highlighted move up or
  down: the equipped moves' order, kept after the battle (`_move_skill`);
  which moves are equipped only changes outside battles. The info window
  describes the highlighted skill (`moves.describe`, talents included;
  `_skill_info`), and with Fight highlighted, the basic attack. Up to 6 a side
  (`PARTY_SLOTS`; the party and enemy windows' rows squeeze, `row_height`). Enemies show an HP bar
  under their feet (`_enemy_bar`; those names go under it) and their HP
  left as numbers in the enemy window, between name and level/status. Battle sequences are generator "scripts"
  that yield seconds to wait (`BattleScene._round` / `_perform`).
- Move effects (`scenes/battle_fx.py`, all drawn in code): a recipe per
  move (`RECIPES`, a fallback by type) with a `launch` on the attack's
  strike frame (returns its travel time: the hit lands when it arrives),
  a `land` at the targets (returns how long it lingers) and, for charging
  moves, a `charge`. Built from particles (light kinds: a see-through body
  plus an additive halo, so they read on any backdrop; matter: rocks,
  leaves, drops...), beams and bolts, rings, and field-wide shake, flash
  and tint (`BattleScene.fx`; drawn behind/over the Pokémon). Effects grow
  with the move's power (`power_of`).
- Each `Animation` aligns its own baseline (lowest opaque row) to the feet
  position, because rows in a sheet sit at different heights. Rows whose
  effects reach below the feet pass an explicit `baseline=` instead (one
  row, or a tuple per frame with None = the frame's own).
- Gear (`items.py`): each Pokémon has typed slots (head, held, worn, berry).
  Gear is rolled (`Gear.roll`): the item's own effect plus random affixes
  (prefixes/suffixes, e.g. "Fierce Red Bandana of the Aerodactyl"; suffixes
  are named after Pokémon). Rarity (Common/Uncommon/Rare/Epic/Legendary)
  sets the affix count (0, 1, 1–2, 2, 2–3) and multiplies rolled
  bonuses, not penalties (×1.0 to ×1.6). Item level (`Gear.level`) = the
  level needed to equip it (`usable_by`); ranges are a Lv50 Common item's
  and the level scales them gently (`items.scale`: stats/type damage/crit
  × `STAT_SCALE` 0.25 + 0.25 × level/100, chances and specials ×
  √(level/50), berry healing by absolute HP × (level+5)/55); every kind of
  bonus is priced by its worth. Drops get the defeated Pokémon's level,
  chests the area's level range. Mods (six for numbers, since the gear
  rework, `GEAR_VERSION` 4): stats in %, `crit` (% points; base 5%:
  `combat.crit_chance`), `power:<type>` (%
  on that type's moves); and effects: `status:<status>` (% chance a hit
  inflicts it), `first` (Quick Claw), `endure` (Focus Band), `regen`,
  `drain`, `berry_*` (Oran heals absolute HP; cure berries
  (`Item.cures`) have a `berry_cure`% chance each round end their holder
  has the status). Berries roll berry affixes (`BERRY_AFFIXES`: Juicy,
  Bitter, Spicy/Dry/Sweet, of the Vileplume (heals 3 rounds), of the
  Exeggcute (may not be used up), of the Jolteon (eaten sooner);
  `affixes_for(slot)`)
  and are eaten at most once per battle (`BattleScene._berry`), not used
  up. `Monster.attack` etc. include gear; `base_*` don't.
  Special effects (`items.GEAR_EFFECTS`, `Gear.effect`, "red text" as in
  Borderlands): Rare 10% / Epic 20% / Legendary 40% (`EFFECT_CHANCE`) roll
  one, a talent-like change (Earthshaker: the basic attack spreads, Thornmail,
  Plague Charm, ...), written as talent data (`GearEffect.moves`/`flags`);
  `Monster.talent` reads their flags and `Monster.move` applies their move
  changes after the talents' (`Monster.gear_effects`, `has_effects`); shown
  in red (`EFFECT_COLOR`) on the party screen, bag and gear counter; worth
  ×1.5 (`EFFECT_VALUE`); saved as "effect".
- Hats (`hats.py`): head-slot items (`items.HATS`) are cells of
  `hats_new.png`, drawn on the Pokémon wearing them (map, battle, party
  screen). The cells' reference faces are cut out on load, so the Pokémon's
  face shows through. Placement comes from `hat_anchors.json`: a head anchor
  per animation frame (`Animation.heads`, in sheet pixels), a hat size per
  species (× `Species.size`) and per-hat tweaks. Every species with a sheet
  has them: `tools/hat_autofit.py` (a hand-set anchor on each standing pose,
  `REFS`, tracked into every frame; `SCALES`) fills them in; fine-tune with
  `tools/hat_viewer.py`. Placeholder species (icons) don't show hats.
- Loot (`loot.py`): `LootTable`s of weighted entries (nothing / medicine /
  gear at weighted rarities), rolled 1+ times; built per set of rarity
  weights (`wild_loot`, `chest_loot`, `boss_loot`). Each `Route` sets which
  rarities drop (`loot`, `boss_loot`): early on Common only, Uncommon from
  bosses; Rare and up are for later areas. A won battle rolls the
  battle's table once per enemy; Poké Balls on the map (`Level.balls`,
  `overworld.Ball`, 0–2 a map, Up) give one item (`ball_loot`). There are
  no roadside chests (`Level.chests` spots are unused): only bosses leave one. Gear drops
  from battles only rarely (4%). Bosses and trainers' Pokémon wear gear
  (`loot.dress`: the boss 2 pieces, the rest 1, at the enemy's level and
  the area's rarities), each piece dropping 10% of the time
  (`worn_drops`). After a boss, `Route.boss_chest`: "plain"
  (a chest: route bosses), "fancy" (the boss loot: gyms), "battle" (the
  boss loot with the battle: rival, trials, feud, Team Rocket) or ""
  (recruitments). Both show a `ui.ListPanel`. The starter begins
  with just a Common Oran Berry.
- XP (`pokemon.py`): defeating a Pokémon is worth `base_exp × level / 7`
  (Gen 1; `Species.base_exp`), and reaching a level takes `level³` total XP.
  A won battle gives the party members still standing the XP of all the
  enemies, split between them (`BattleScene._give_xp`; ×0.15 wild, ×0.45 trainer), filling the
  XP bar and leveling up (keeping the damage taken). Quests are the main
  XP source.
- Talents (`talents.py` puts together `talent_core.py`, `learnsets.py`,
  `talent_list*.py` and `talent_trees*.py`; `docs/talents.md`): moves come by level
  (`LEARNSETS`: per line (move, level, evolution stage); Red/Blue's
  levels, strong moves and TMs later; `Monster.known`); the first is the
  basic attack (Fight), 4 more equipped (`Monster.equipped`; new moves
  equip while there's room, `_learn_new`; level-ups say "learned").
  Builds are talents: a line's `TalentTree` has 3 paths (Bulbasaur: Toxin,
  Bloom, Bulwark) and 12 tiers (`TIER_LEVELS` Lv6–75); each tier, pick 1
  of 3 (one per path; tiers 11/12 need 4/6 earlier picks in that path,
  `DEEP`); `Monster.talents` (keys), `pick`, `why_not`. No ranks or plain
  stat bonuses: each talent is hand-written (`TALENTS`) and shared through
  pools (`Talent.pool`: a type/status, a move ("move:Growl"), "any", or
  "own" = the line's signatures; each type's pool written for that type).
  A talent changes moves (`Talent.moves`: (selector, Move field changes),
  selector "basic", a move name, "type:grass", "status:poison",
  "confuse", "damaging", "status_moves" or "spread"; `apply_changes`, in
  tier order; `Monster.move(key)`) and/or works in battle (`Talent.flags`,
  listed above `TALENTS`, `Monster.talent(flag)`; per-type ones like
  "pinch:grass" (Overgrow/Cornered/Swarm share it), "streak:<type>",
  "harvest:<type>"; damage ones in `BattleScene._talent_factor` (pinch,
  streak, ambush, gang, wide, prey, spot, Sapping, Ancient Roots, Sturdy);
  `first`/`crit`/`endure`/`regen`/`status:<s>` add to `Monster.gear_bonus`
  (`TALENT_MODS`); Second Wind, Shed Skin, Nurturing, Dream Eater in
  `_regen`; harvest, Guardian/World Tree, retaliate, thorns in `_hit`;
  aura and Intimidate at the start, `_auras`; Move fields `taunt`, `keen`,
  `charge_skip`, `ko_no_recharge`, `soothe`; same-effect talents don't
  add up, the strongest counts). Lines with talents (`TALENT_TREES`): the
  starters, Pidgey, Rattata, Spearow, Nidoran F/M, Caterpie, Weedle,
  Pikachu, Geodude, Onix, Jigglypuff, Sandshrew, Ekans, Zubat, Paras,
  Clefairy, Goldeen, Staryu (Starmie), Horsea, Shellder, Psyduck, Oddish,
  Bellsprout, Abra, Venonat, Diglett, Meowth, Mankey, Machop, Tentacool,
  Growlithe, Voltorb, Magnemite, Drowzee (Raichu: Pikachu's, `LATER_FORMS`): every line in the game (a new
  line without `TALENT_TREES` would have just its moves). `Monster.create`
  picks for wild/trainer Pokémon (mostly one random path). The talent
  screen (`scenes/talent_screen.py`, party screen → S): a grid (tiers ×
  paths, scrolls), info on the right with the known moves; Enter picks
  (first picks anywhere; changing picks and R reset only in towns,
  `Scene.in_town`), M the moves list (equip, `MovesList`; the highlighted move's description
  in the info pane; with 4 equipped
  it asks which to replace), O orders them (`scenes/moves_panel.MovesPanel`),
  Q/W switch Pokémon; taps choose / pick. Tables in `docs/talents.md` are
  generated: `python tools/talent_docs.py`. Saves from the skill trees
  keep their equipped moves, no talents (`saves.TALENTS_VERSION`). A
  species without moves gets Tackle (`stand_in_tree`). Battle: stat stages
  incl. accuracy (`Combatant.stages`; moves miss by their Gen 1 accuracy,
  `Move.accuracy`/`moves.GEN1_ACCURACY`, × lowered accuracy's
  `hit_chance`; `BattleScene._misses`), priority, multi-hit, flinch, confusion, bind, Leech Seed,
  spread moves, recoil, recharge, drain, Rest, Focus Energy, Toxic,
  wounds (`Move.bleed`), stages on the user (`self_stages`), Seismic
  Toss (`Move.fixed`: the user's level; Sonic Boom `fixed_amount` 20),
  Self-Destruct/Explosion (`Move.self_ko`: the user faints), Pay Day (`Move.pay_day`:
  money picked up after a win, `BattleScene.scattered`), set-off
  moves (`Move.triggers`, `BattleScene._apply`), reach/spill
  (`_beside`). Sky battles (`BattleScene(sky=True)`, rules in
  `mechanics/sky.py`): the party's Flying types (`Combatant.flier`) get a
  Sky command (Fly, Perch: `SKY_MOVES`) in place of Run, feel the round's
  wind (`Combatant.wind`; `BattleScene.wind`/`next_wind`, `_blow`) and tire
  (`_fatigue`); Fly's first round is `Combatant.up_high` (attacks on it
  miss, `_perform`), a perched one loses its Flying type
  (`Combatant.types`, read by `combat.damage`).
- Evolution (`pokemon.py`): `EVOLUTIONS` lists every Red/Blue level
  evolution (species key → `Evolution(into, level)`); trade evolutions
  aren't in yet. Stones (`STONE_EVOLUTIONS`: stone → {from: into}, any
  level) are key items from one quest each ("leaf_stone": Celadon
  Square's Oddish → route "celadon_garden", the gym's back wing with
  spores and waves; "moon_stone": the Mt. Moon Center's Clefairy → dark
  route "mt_moon_crater"; "thunder_stone": the Route 10 Voltorb → route
  "power_plant", `puzzle` "sparks"; Fire/Water later), used from the bag
  on a party member (`SummaryScene.stone`: evolves via
  `Monster.evolve(into)`, the stone is used up). An evolution is only active once its target
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
  turn; items act before all moves and always work: no status,
  confusion or flinch stops them, `_perform`; an asleep user's sleep still
  counts down, `_doze`) or from the bag. The Escape Rope is in
  `MEDICINE` too (`Medicine.escape`: not in battle; from the bag on an
  instance map → `TownScene` of `Game.town`). An item is only used up
  when it has an effect (`Medicine.has_effect`: Revive only on the
  fainted, the rest only on the standing).
- The bag (`scenes/bag.py`, `BagScreen`; I / the Bag touch pill on
  maps): pockets Items (medicine on a party member,
  `Medicine.use_on`; Escape Rope), Gear (equip on a party member) and
  Key items (`items.KEY_ITEMS` descriptions; an evolution item on an
  eligible member, `quests.item_evolves`, opens the party screen
  evolving it). Hosted by the pause menu (`PauseMenu.open_bag`, closing
  resumes; the pause menu itself only has out-of-game options);
  `loaded` switches scene.
- Status conditions (`status.py`): burn, poison, paralysis, sleep, freeze;
  one per Pokémon, stored on `Monster` and kept after battle; cleared on
  fainting. Asleep/frozen party members only
  get to use items (Fight/Skills skip the turn, `Combatant.dozing`). Cured by medicine.
- Types (`type_chart.py`): the 15 Gen 1 types and chart (Ghost→Psychic fixed to
  2×). Species have 1–2 types, moves one (or none). STAB ×1.5. Gen 1's
  Special stat (`Species.base_special`): Fire/Water/Grass/Electric/Ice/
  Psychic/Dragon moves (`combat.SPECIAL_TYPES`) use Special for attack and
  defense (`Monster.special_attack`/`special_defense`: gear's Attack and
  Defense bonuses apply); burns only weaken physical moves. The party
  screen and the starter choice show it.
- Maps (`level.py`): a tile grid (16 px tiles; "#" solid, "=" one-way
  platform) generated from a seed and a theme (`themes.py`: tile palette,
  weighted encounter pool with level ranges, group sizes, battle backdrop,
  cave ceiling). Maps scroll sideways and end at a doorway (Up) to the next
  map. Wild groups are shown in full and stay gone once beaten. A group stands
  as a loose cluster around its leader (`WildPokemon._lay_out`: the others
  by turns on either side, overlapping, every other one in a dimmed back
  row; slid and squeezed onto the level ground under it; a boss looms
  behind its escort). A group
  can't be jumped over: it also catches the player in a column up to
  `GROUP_REACH` above it, stopped by a platform or ceiling overhead
  (`WildPokemon.reach_rects`; a group partly under a platform is capped
  there all along), so platforms still get past. With two
  fighting, about half the wild groups get one more Pokémon
  (`overworld.EXTRA_FOE_CHANCE`, `level.extra_member`; seeded by the map).
  Area levels track the party's expected level (`docs/quests.md`).
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
  sell medicine for half; `Medicine.price`); in towns with `Town.gear`,
  a curtained doorway at the back (`props/den_curtain.png`) leads to
  Persian's den (`DenScene`: `rooms/den_wall.png`/`den_floor.png`, gilded
  gear stands `props/gear_stand*.png`; `tileset.room(..., doors=)`), where
  Persian lies on a pile of gear (`props/persian.png`: 80 px frames,
  `npc_frames(name, width)`; `props/coin_spill.png` in front of its foot,
  loose coins drawn on the carpet, `LOOSE_COINS`); Up at it opens the gear counter
  (`GearShop`: 6 pieces, `towns.gear_stock`, rolled from `Game.seed` and
  the visit, restocked on arriving from a route, `Game.arrive`; buy at
  `Gear.price` = 5× `Gear.value`, `GEAR_MARKUP`, sell bag gear for half
  the value); Up at the door goes back
  out (`TownScene(arrive=building name)`). Saving inside (the den too) saves the player
  outside the shop. Art is made with
  PixelLab (Claude may use its tools; the user picks from the candidates).
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
  `trainer` makes the boss fight a trainer battle (no running, trainer XP).
  A boss is a boss once: beaten (`Game.trainers` "boss:<route>[/<room>]",
  `OverworldScene._boss_key`; or `Game.cleared`), it's an ordinary group
  at normal size on later trips (no boss loot, no chest, door open), unless
  a quest is at the step of defeating it (`quests.boss_wanted`).
  `RIVAL_STARTER` (`_EVOLVED`, `_FINAL`: its next and last forms) in a
  boss group or band becomes the rival's starter, which beats the player's
  (`Game.starter`, `Game.rival_starter`; `instance.rival_species`). Routes can have
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
  stop at the cave's far exit (town "route_4"); the road on, route
  "route_4_east" (2 maps), leads down to Cerulean City (Center, Mart,
  Recruitment Center, and the Cerulean Gym: the Cascade Crew's waves of
  Water Pokémon, then Starmie and Staryu, for the Cascade Badge; Starmie
  takes Staryu's moves via `pokemon.LATER_FORMS`). North of Cerulean (its right-edge doorway):
  route "nugget_bridge" (Route 24, as in Red/Blue: the rival's second
  battle at the bridge's start, a map trainer that can't be got past,
  `Trainer.first`/`blocks`/`boss_loot`, `RIVAL_STARTER_EVOLVED`, the
  quest step's target, `quests.trainer_beaten`; five bands; the arena
  boss is a Rocket who gives the Nugget once, `Route.boss_key`/
  `boss_gift`/`boss_dialogue`; the Nugget: `Medicine.valuable`, only sold) → stop town
  "route_24" → route "route_25" → town "sea_cottage" (quest "bill":
  talk to the Clefairy, i.e. Bill, then Up at the cottage → S.S. Ticket). Then quest "burglary": the
  Cerulean house at the street's end ("Burgled House") is walked as route
  "cerulean_backyard" (`Route.building`) to the burglar's Rocket Gang;
  beating it opens Cerulean's doorway behind it onto route
  "route_5_south" (Route 5: wild Meowth and Mankey)
  → stop town "route_5" (Day Care, the shut Saffron gate) → route
  "underground_path" (theme `UNDERGROUND`: a tunnel, its far wall the
  painting `walls/underground.png`; without it `CaveLook.lamps` draws a
  tiled wall with lamps in code, `tileset._tunnel_wall`; ceiling lamps) → stop town "route_6" → route "route_6_south" (four
  bands) → Vermilion City (Center, Mart, Recruitment Center, Fan Club,
  the gym shut by a tree) → its east doorway: route "ss_anne" (quest
  "ss_anne": a dungeon of rooms, deck/hold/2F/Captain's cabin; no wild
  Pokémon; `Theme.built`: flat plank decks, `walls/ss_anne.png`,
  `backdrops/ss_anne.png`; the rival guards 2F's stairs; the Captain is
  `Room.folk` (townsfolk in a dungeon room, `OverworldScene._talk`) and
  gives HM01 Cut; `Route.needs` "active": shut once the ship has sailed).
  Then quest "thunder_badge": the Vermilion Gym's door has a small tree
  (`Building.tree`, `props/cut_tree.png`; the first Up once the quest has
  started cuts it, kept in `Game.trainers` "cut:<town>/<building>"); route
  "vermilion_gym" (`VERMILION_GYM`, built: steel; the Thunder Battalion's
  waves of Pikachu, Voltorb, Magnemite, then Raichu's band; `wave_team=3`,
  tuned to need three: about 70% with three, 14% with two; its puzzle,
  `Route.puzzle` "trash_cans", `scenes/power_grid.py`: an electric fence
  before the arena, two switches in 8 trash cans (`props/trash_can*.png`),
  the first's can sparks, the second next to it, the wrong neighbour a
  Voltorb ambush that moves both; solved for good, "puzzle:<route>" in
  `Game.trainers`). After the badge
  (quests "to_route_11", "digletts_cave", "flash"): Vermilion's doorway by
  the dock (col 81) → route "route_11" (2 maps, five bands; wild Drowzee)
  → stop town "route_11" ("Route 11 Gate": the Diglett's Cave doorway, a
  Diglett giving `evolve_dugtrio`, and Snorlax asleep across the doorway
  to Route 12, `Folk.asleep`: not turning, Zzz drawn in `town.py`;
  `Folk.blocks`: `TownScene.update` keeps the player on their side of it;
  route "route_12" runs up to Lavender's doorway at col 67, its `needs`
  only checked from this end (`Route.needs_from`), so it can be walked
  down from Lavender to reach the Snorlax from the east) → route "digletts_cave" (theme `DIGLETTS_CAVE`, 3 maps
  of Diglett/Dugtrio, a giant Dugtrio's band, `MID_BOSS` loot) → stop town
  "route_2" (Oak's aide, a Kadabra: HM05 Flash) → route "route_2_north"
  (one map, `wild=False`) → Pewter's doorway at col 67. With Flash (quests
  "to_rock_tunnel", "rock_tunnel"): Cerulean's doorway at col 89 → route
  "route_9" (2 maps, five bands) → stop town "route_10" (Pokémon Center) →
  route "rock_tunnel" (a dungeon of 3 rooms, theme `ROCK_TUNNEL`,
  `Theme.dark`: black but for Flash's light around the player,
  `overworld._darkness`; the Hiker Crew guards B1F's stairs, `MID_BOSS`
  chest) → Lavender Town (Center, Mart, gear den, the Pokémon Tower, shut
  for now: `towns.TOWER` = `pokemon_tower.png`, a one-cell building sheet of its own
  size, 160×256, `tileset.BUILDING_CELLS`; `Building.sprite` can also take
  a scale, (sheet, cell, scale), nearest-neighbour;
  Mr. Fuji's house; the smith). Then (quests "route_8", "to_celadon"):
  Lavender's east doorway → route "route_8" (2 maps, four bands) → stop
  town "route_8_gate" (Saffron's shut east gate) → route
  "underground_west" (theme `UNDERGROUND_WEST`, 2 maps) → Celadon City, in
  three town maps joined by doorways (`Town.exits` "town:<key>",
  `town.LINK`: walking between them doesn't restock the gear counter):
  "celadon" (east: Center, board, the Department Store, `Building.inside`
  "dept" → `scenes/dept_store.DeptStoreScene`, `FLOORS`: 1F guide, 2F
  medicine, 3F Persian's gear, 4F materials, `MaterialShop`, rooftop
  vending machines selling drinks, `rooms/roof_*.png`; stairs props),
  "celadon_square" (the Game Corner, the Celadon Gym, Recruitment
  Center, smith) and "celadon_west" (Mansion, the Battle Tower);
  big buildings have their own sheets (`towns.DEPT_STORE`, `MANSION`,
  `GAME_CORNER`, `BATTLE_TOWER`, `tileset.BUILDING_CELLS`). The smith
  (`towns.smith(col)`, `Folk.npc` = "machamp_smith": drawn from
  `props/machamp_smith.png` with `props/furnace.png`, its glow, and
  `props/anvil.png`; one in each major town from Lavender on): quest
  "smith_hammer" (on offer once "rocket_hideout" is done) wants the Thick Bone (`items.BONE`, from the Tower's
  Marowak later; `Step.takes` + `waiting`: a talk step only once the item
  is in the bag), then `scenes/smith.SmithMenu`: salvage gear into its
  rarity's material (`items.MATERIALS`, `Bag.materials`), enhance to +5
  (`Gear.plus`, `items.enhanced`: bonuses +5% each, `PLUS_COST`), smelt 4 → 1 of the
  next. Then quest "rainbow_badge": route "celadon_gym" (`CELADON_GYM`,
  built: a greenhouse, `walls/`/`backdrops/celadon_gym.png`, flowers and
  hanging vines in code; the Blossom Troupe's waves of Grass Pokémon, then
  Vileplume's band with Tangela; `wave_team=3`, about 69% with three; its
  hazard, `Route.puzzle` "spores", `scenes/spores.py`: 8 drifting clouds
  of Sleep Powder / Poison Powder / Stun Spore that give a party member
  their status on touch, carried into the waves). Then quest
  "rocket_hideout": route "rocket_hideout" from the Game Corner
  (`Route.building`), a dungeon of 5 rooms (`ROCKET_HIDEOUT`, built, painted
  `walls/` and `backdrops/rocket_hideout.png`); its
  blocking map trainers (`Trainer.first`/`blocks`) are the poster guard
  and the Lift Key guard (a "defeat" step on its key gives the Lift Key);
  the office's boss guards its back door out (Silph Co., quest "silph_co",
  works the same way: `SILPH_CO`; a room can have its own painted wall and
  battle backdrop, `Room.wall`, as its President's office does; Strength's
  boulders, `Room.boulders`, `scenes/boulders.BoulderField`: solid tiles
  carved in and moved a column at a time, over a ladder to a bonus room
  with its own `pool`, `boss_scale`, `boss_chest` and `boss_loot`; the

  Saffron Gym's warp pads are `Route.puzzle` "psychic",
  `scenes/psychic_pads.PsychicHall`: barriers carved as solid columns, a
  pad graph rolled from the trip's seed). Then quest "pokemon_tower":
  route "pokemon_tower" from Lavender's Tower (7 rooms, `POKEMON_TOWER`,
  painted `walls/` and `backdrops/pokemon_tower.png`); the rival and
  the 6F Restless Spirits are blocking map trainers (the spirits drawn
  see-through, `Trainer.spirit`, `overworld._ghostly`; beating them gives
  the Thick Bone), 7F's room boss is the Rockets; Mr. Fuji's house's note
  changes once it's done (`Building.note_after`). B2F/B3F are spinner floors
  (`Room.puzzle` "spinners:<key>": `world/spinners.py` has the layouts,
  as strings, and carves the catwalk into the generated room;
  `scenes/spinners.SpinnerFloor` carries and launches the player through
  `MapScene.steer`/`moved` hooks and `Controls.carried`). The Battle Tower (`world/tower.py`, `scenes/battle_tower.py`;
  `Building.inside` "tower", open after `tower.OPENS_AFTER` "rainbow_badge"
  or in dev mode): post-story content. Its lobby (`TowerLobbyScene`,
  `rooms/tower_*.png`) has Mew floating, drawn 2× (`props/mew.png`), with
  `MewMenu`: Climb (heals, floor 1), gem exchange (`GEM_GEAR`: 12 of a gem
  for a piece, slot picked; `GEM_POKEMON`: Dratini/Chansey/Lapras, each
  once, "mew:<species>" in `Game.trainers`). 25 floors (`TOWER_ROUTES`,
  "tower_1".."tower_25", `Route.tower` = the floor): each a gym-like hall of
  waves then a master's band (`trainer`), Lv32 → Lv65
  (`floor_level`, `TIER_LEVELS`), five tiers (`TIER_NAMES`, `POOLS`, `WAVES`, `BAND`,
  `WORN`, `TALENTS`; themes `TOWER_THEMES`, walls and backdrops
  `tower_1..5.png`; giant masters on every fifth, `BOSS_FLOORS`), opening
  five at a time (`GATES`: 4/6/7/8 badges of `BADGES`, counted in any
  order, then `LEAGUE`; `top_floor`, `tier_open`). Tower
  battles: `tower.dress_up`, `drops=False`, no prize; masters every run
  (no boss-once). After a floor, `TowerChoice` (climb on, no healing, or
  claim: `battle_tower.claim` → `tower.chest`: medicine, gear, gems into
  `Bag.gems`); losing gives nothing. Saves on a floor or in the lobby are
  outside the tower (`lobby_location`). `Game.tower_best`. Placeholder
  species for the tower and later (Dragonite, Gengar, Golem, Alakazam, ...)
  have learnsets but no talent trees yet. `Route.blocked_done`: what a
  shut doorway says once its quest is done (`quests.blocked_text`);
  `Building.note`: what Up at a building says if nothing else happens (`Step.before`: what it says while a
  quest's visit there is still to come, `quests.early_text`).
  Code-drawn caves take their colours from
  `Theme.cave` (`CaveLook`) and ceiling decor from `tileset.CEILING_DECOR`.
  Themes (`themes.py`) pick their map art with `Theme.art` ("woods":
  Pixellab ground and background; "cave": drawn in code). `tileset.py` draws the meadow's ground
  from `tileset_woods.png` (`_render_woods`); all one-way platforms are
  still drawn in code. The
  meadow's background (towns and routes) is Pixellab art: a sky gradient
  with clouds, then three parallax strips (`MEADOW_STRIPS`: far mountains,
  mid hills, near tree line; 20/35/50% of the camera); a theme can give its
  own sky gradient and a tint multiplied into the clouds and strips
  (`Theme.sky`/`tint`: Lavender Town's dusk, `themes.LAVENDER`, `Town.theme`). `backgrounds()`
  returns (layer, parallax) pairs. The player collides with a fixed hitbox.
- Townsfolk can leave: `Folk.gone_after` (a quest key, or "boss:<route>":
  that boss beaten, `quests.gone`) hides them (`TownScene.folk`); a route
  walked by talking to a townsfolk (`Route.folk`) can have its own send-off
  (`Route.folk_line`). A route's `needs` can be ("boss:<route>", "beaten").
  A talk or defeat step can take alternatives (`Step.alt`): a talk step
  done with one records it in `Game.trainers` ("chose:<quest>=<folk>"), and
  a later defeat step only sends the player from that townsfolk
  (`quests.chosen`). Quest 25 (`snorlax_west`): two Snorlax, Celadon West
  End's (blocking Route 16) and the Route 11 Gate's (blocking Route 12, up
  to Lavender); either does: woken with a feast (a collect step, the
  Department Store rooftop's machines as a "visit" step,
  `dept_store.ROOFTOP`) and the Poké Flute, then a boss battle (route
  "snorlax_wakes" or "snorlax_wakes_east"); it joins, and leaves its road
  open. `snorlax_second`: the flute alone wakes the other one (no join).
- The Fuchsia Gym's hazard (`Route.puzzle` "ninja", `scenes/ninja.py`,
  `NinjaDojo`): invisible walls are SOLID tiles carved into the level
  after `MapScene` has rendered its tiles (so they aren't drawn); bumping
  one sets `HiddenWall.found` (a faint pane from then on); floor vents
  poison like the spores (`spores.py`).
- The Safari Zone (`world/safari.py`: `Visit`, `node`; `scenes/safari.py`:
  `SafariScene`, `SafariGate`): each map is an `OverworldScene` on a
  one-room `Route` built on the fly (its stairs: the door back and the
  doors on, all "out" doorways that `SafariScene._go` handles); the maze is
  a pure function of the visit's seed and the door path. `MapScene.draw_front`
  draws over the player (its tall grass). `location()` saves it as Fuchsia.
  `quests.visit` honours a visit step's `takes` (`waiting` until then).
  Its games (`scenes/safari_games.py`): `MiniGame` scenes (a countdown,
  30 s of `play`, the score) entered from `SafariScene._encounter` and
  handing the score back through `on_done`; taps (mouse or touch, with
  `drag` while held) are the swipes and basket moves.
- The skate road (`Theme.skate`): `level._downhill` steps the ground down
  to the right; `Player.skating` gives the player momentum (`vx`, 1-tile
  steps are ramps) and draws a board under it (`tileset.draw_skateboard`,
  props/skateboards.png, 4 boards); `WildPokemon.draw` puts every group
  member on a board (a giant on a giant one). `Route.boss_wears`: a unique
  piece (`Item.unique`, never rolled) the boss's leader wears, on the map
  too (`WildPokemon.hat`) and in battle, and always drops
  (`loot.worn_drops`), until `Route.boss_key` is beaten: Tony's Bike
  Helmet (hat sheet cell 64, a 9th row; flipped, anchored by hand in
  hat_anchors.json).
- Fly (quest `learn_to_fly`): `Quest.needs_species` gates the offer; a
  "lead_wins" step counts wild battles won with one of `Step.species`
  leading the party (`quests.won_battle`); `Route.sky` makes a route's
  battles sky battles (the Sky Trial); `Route.wave_loan` adds a lent
  Pokémon to the team picker (`TeamPick.loaner`) when no one in the party
  that may fight is at `wave_loan_below` or higher. The Town Map gets a `fly` mode
  (`TownMap.fly`, set by `PauseMenu.open_map` from `quests.can_fly` and
  `pause._fly_from`); Enter on a known city (`townmap.CITIES`: not routes' stops) sets `fly_to`, and the pause
  menu switches to that `TownScene` (autosaved).
- Saves (`saves.py`): JSON files in `saves/`: one `autosave.json` (written
  after every won battle, opened chest, party faint and leaving a map) and
  numbered manual saves (pause menu → Save game; not during battles). A
  save stores the `Game` and the map scene's `location()`: the town and
  position, or on an instance the route, seed, map number, beaten groups,
  opened chests and position (`restore` puts it back); maps are
  regenerated from the seed. Scenes say what can be saved via
  `Scene.save_point()`. The game starts at
  the title screen (`title.py`: Continue / Load game / New game); the save
  and load lists are `save_menu.SaveList` (Delete key, or the Delete touch
  pill `DELETE_PILL` shown by the title and pause menu, deletes a save after
  asking). Pause menu → Quit game closes the game; in the browser it goes
  back to the title screen (a page can't close itself). New game opens the starter
  choice (`scenes/starter.py`: Bulbasaur, Charmander or Squirtle,
  `progress.STARTERS`; `Game.new(starter)`, saved as `Game.starter`).
- Quests (`world/quests.py`: the rules; `world/quest_data.py`: `Step`, `Quest` and
  every quest; `docs/quests.md`): `QUESTS` (`Quest.requires` entries can be
  any-of tuples, `quests.required`; `Quest.needs` as a route's; a talk
  step's `Step.joins` adds the Pokémon of whichever `alt` was talked to) with steps (visit
  a building in a town, defeat a route's boss, reach a town), taken from a
  town's quest board (`Town.board_col`) or started automatically once their
  prerequisites are done (`Quest.starts_in`: only on arriving in that
  town, e.g. the Boulder Badge in Pewter). Board jobs: hunt (defeat N of a species) and
  collect (N quest items dropped by species on a route or any later one,
  `instance.STORY_ORDER`/`from_route`,
  `quests.won_battle` via `BattleScene.on_win`), handed in at any board
  (`HAND_IN`); counts in `Game.quest_counts`. Quests are the main XP
  source, about ¾ (wild battles ×0.15, `WILD_XP`; trainers ×0.45; split). Every quest pays Poké Dollars and XP
  (`Quest.money`, `Quest.xp`: XP to each party member); major quests
  (rival, gyms) also give items (`Quest.rewards`). State in
  `Game.quests`, key items in `Bag.key_items`, money in `Bag.money`
  (₽, `items.money_text`; `ui.text` draws the ₽ sign itself). Quest events return an `Event` the map scene shows
  (`MapScene.show_event`: dialogue, "New quest", "Quest complete" with
  rewards); map panels queue (`MapScene.show`). A "defeat" step for a map
  trainer already beaten for good completes by itself (`_skip_beaten`;
  on load, `quests.catch_up`). Routes can be gated
  (`Route.needs`/`blocked`) and change boss after a quest (`boss_after`).
  Screens in `scenes/quest_ui.py` (dialogue box, quest board, quest log: Q
  on a map, `PauseMenu.open_quests`); the map shows the current step and markers (`MapScene.markers`:
  "!" a quest to take or a step's place, pink for evolution quests,
  `quest_mark`; "?" quests to hand in). Evolution quests (`Quest.evolves`)
  are only on offer (and only drop their item) once that species is at
  its evolution level in the team (`quests.evolution_level`).
- Townsfolk (`towns.Folk`, `Town.folk`; drawn and talked to in `town.py`):
  Pokémon in towns (their species' idle animation, facing the player; `ELDER`
  = the last form of the player's starter's line). Up next to one
  (`FOLK_REACH`): a "talk" quest step (`quests.talk`), else a quest they give
  (`Quest.giver`/`offer`), else a trial they send to (`Route.folk`), else
  their chat `lines`. Starters evolve by "Coming of Age" (`evolve_<starter>`,
  the elder in Pewter): collect 3 tokens, talk, a solo trial
  (`instance._trial`: waves with `wave_team=1`, `wave_species`), evolve.
  Pidgey and Spearow by the feud (`feud_pidgey`/`feud_spearow`, Viridian's
  Pidgeotto and Fearow; `Quest.excludes`: one side at a time): hunt 8 of
  the other side, talk, beat its giant leader's band on its home ground
  (`instance._feud`, sent by the giver), evolve. Metapod → Butterfree,
  Kakuna → Beedrill (Pewter's Butterfree and Beedrill) and Rattata →
  Raticate (Viridian's Rattata) the same way (`evolve_butterfree`: hunt,
  talk, evolve; `evolve_beedrill`: collect Royal Jelly, the Hive Queen's
  thicket; `evolve_raticate`: hunt Ekans, the Rat King's burrows), as are
  Nidoran F → Nidorina and Nidoran M → Nidorino (Viridian's Nidorina and
  Nidorino: `evolve_nidorina`: collect Soft Grass; `evolve_nidorino`: hunt
  Spearow, the Horn Brothers' hollow) and Abra → Kadabra (Cerulean's
  Kadabra, `evolve_kadabra`: hunt Venonat, a solo Trial of Mind,
  `_trial(town=, folk=)`), the starters' last forms ("Mastery",
  `master_<form>`: Celadon West End's master, `celadon_master` (the
  `ELDER`): hunt, talk, a solo trial ending with a giant final form) and
  Pidgeotto → Pidgeot (Celadon's Pidgeot, `evolve_pidgeot`, the same
  way), Oddish → Gloom (Cerulean's Gloom,
  `evolve_gloom`: collect Sweet Nectar, the Stench Patch) and Bellsprout →
  Weepinbell (the Route 24 Weepinbell, `evolve_weepinbell`: hunt Venonat,
  Pitcher Grove), and Zubat, Ekans, Meowth and Machop (`evolve_golbat`,
  `evolve_arbok`, `evolve_persian`, `evolve_machoke`: Route 6's Golbat,
  Route 4's Arbok, Vermilion's Persian, Lavender's Machoke; their home
  grounds `golbat_roost`, `snake_pit`, `alley_cats`, `training_grounds`),
  and Sandshrew, Paras, Geodude and Drowzee (`evolve_sandslash`,
  `evolve_parasect`, `evolve_graveler`, `evolve_hypno`: the Mt. Moon
  Center's Sandslash, Route 5's Parasect, the Route 10 Center's Graveler,
  the Route 11 Gate's Hypno; `spike_burrows`, `mushroom_hollow`,
  `rumbling_quarry`, `dreamers_hollow`), and Mankey, Voltorb, Venonat and
  Psyduck (`evolve_primeape`, `evolve_electrode`, `evolve_venomoth`,
  `evolve_golduck`: the Route 8 Gate's Primeape, the Route 10 Center's
  Electrode, Route 24's Venomoth, Cerulean's Golduck; `brawlers_ring`,
  `static_field`, `moth_glade`, `duck_pond`).
- Recruitment (`docs/quests.md` → Recruitment): won wild battles on routes
  (not trainers', gyms' or bosses': `won_battle(recruits=)`) count
  defeated Pokémon per line (`Game.defeated`, `pokemon.line_base`); at
  `instance.RECRUITS[line].needed` its recruitment quest opens (board
  `quests.RECRUIT_BOARD`, `Quest.unlock`). Recruitment Centers
  (`Building.inside = "recruit"`, a house for now; `scenes/recruit.py`:
  a painted room (`tileset.room("recruit")`) with the cork board and Mr. Mime (`props/mr_mime.png`), `RecruitBoard`, `TeamPanel`) send the
  player to the line's map (a generated route: only that species, a giant
  boss); beating it adds it (`Game.add_member`: to the party if it has
  room, else `Game.reserve`). Mr. Mime swaps party and reserve. The
  party's size is how many fight (`quests.active_limit` = `Game.slots`:
  1, +1 per **Teamwork Ribbon** used from the bag, `items.RIBBON`,
  `quests.use_ribbon`; ribbons come from the Route 22 rival and the S.S.
  Anne quests, stack (`items.STACKING`); old saves get `ACTIVE_STEPS`'
  worth; `MAX_PARTY` = 6; gyms' `TeamPick` too); `quests.fit_party`
  (every map scene) only moves extras to the reserve: new places stay
  empty until filled at Mr. Mime. Party screen T moves a
  member to the front (the lead).
- Tab on the map opens the party screen (`summary.py`): stats and gear (D
  switches the stats window to the moves' expected damage,
  `combat.expected_damage`, compared Now / New / Change while choosing);
  Enter on a slot lists the bag's gear for it (or Remove), previewing the
  stat changes (Now / Gear / New / Change) and each mod's difference from
  the worn item (mods it would lose struck through), and equips it. S opens the talent screen ("N talents to pick" shows when tiers are open).
- Dev mode (`dev.py`, `DEV`): switched on in the pause menu, after a
  password (`dev.PASSWORD`, asked once a session: `scenes/dev_menu.PasswordPrompt`,
  typed, or letters picked with Up/Down + Space for touch); remembered in
  the player's settings, never in a save. XP boost (×1/3/5/10/20,
  `DEV.xp_multiplier` in `_give_xp`), god mode (`DEV.god_mode`: the party
  takes no damage, every hit knocks an enemy out), skip packs, open all
  (`DEV.open_doors`: `quests.open_for` lets every doorway and gym in, Cut's
  trees part), an item maker (`scenes/dev_menu.ItemMaker`: any gear with
  chosen rarity/level/affixes and random/min/max values, or "Random gear":
  any droppable piece, or one slot's, rolled at a chosen rarity and level;
  medicine; key items), Teleport (`dev_menu.destinations` / `teleport`:
  every town, route, gym, dungeon, trial and recruitment ground, and a
  fresh Safari visit; from map scenes only) and Quests (`dev_menu.QuestTool`:
  `quests.reset` / `restart` / `step_back` / `step_forward`; resetting
  undoes what its steps did: key items given back or taken, bosses it beat
  unbeaten, its choices; rewards stay). Active settings show in the window
  title and on the map.
- Town Map (`world/townmap.py` data, `scenes/town_map.TownMap` screen; M or
  the Map touch pill on a map, hosted by the pause menu like the bag and
  quest log): a schematic Kanto (`NODES` grid spots for towns, Celadon's
  parts as one; `EDGES` route lines: road, cave or tunnel). Shows places
  in `Game.visited` (saved; older saves: cleared routes, shopped towns,
  the last town), dimmed and unnamed what leads out of them, a blinking
  ring where the player is (`here`: a gym, in-town dungeon or home ground
  is its town's place), and quest marks (`marks`: "!" a quest to take,
  a diamond an active step's place (a hunt: the routes its text names,
  `hunt_places`), "?" hand-ins; evolution quests in pink). The cursor (arrows) picks a place; `info` lists its buildings,
  givers (evolution givers still waiting: the species and level they
  need), steps there, and a route's wild Pokémon.
- Controls: arrows move, Up opens chests, Shift runs, Space jumps, I bag,
  Q quest log, M Town Map, Tab party, Esc pause menu. X (B on touch) goes back / closes
  in every menu and panel (the pause menu too). (There are
  no attacks on the map: fights happen in battles.)
- Touch controls (`engine/touch.py`, for phones): a virtual gamepad in
  side panels: with them on, the window is wider (`touch.window_size()`,
  `SIDE` px each side) and the game is drawn in the middle
  (`touch.view_rect()`; `main.py` gives scenes that subsurface as
  `window`). Buttons post the same KEYDOWN/KEYUP events as the
  keyboard; held keys are read with `touch.pressed()` (instead of
  `pygame.key.get_pressed()`). Presses (fingers, or the mouse) on the game
  that miss the buttons become taps for the scene (`touch.taps` →
  `Scene.tap(pos, drag)`, logical px; the talent screen uses them).
  D-pad (arrows), A = Space (jump/confirm),
  B = X (back), Menu = Esc, Party = Tab; on maps (`Scene.touch_map`) also
  Run (a toggle); scenes add their own keys as pills
  (`Scene.touch_keys`: party screen Talents, talent screen Moves / Reorder moves / Reset; pills under
  Party). On for touch screens in the browser (decided before the window
  is made), or with `POKEMON_TOUCH=1` (mouse = finger) on desktop.
  The player sets the layout (`touch.Layout`: button size, panel width
  down to 0 = buttons over the game, see-through, or `AUTO` (the
  default): panels as wide as the screen's shape leaves, so the game fills
  its height (`touch.side`; the window is remade when the page's shape
  changes); each side's buttons moved across/up). With panels, the
  buttons are fitted into them (`touch._fit`: round ones moved in,
  closer and smaller, down to `MIN_FIT`; pills narrowed and stacked down
  the panel, the scene's pills spilling over under Menu when they'd reach
  A/B), so they don't cover the game or each other; pills with long
  labels grow wider, `Button.wide`, as the panel allows) in pause menu → Controls (`scenes/controls_menu.py`,
  only with touch on; every button shows meanwhile). Positions come from
  `touch.SPOTS` (the default layout) placed by the layout (`_placed`).
  Changing the panel width remakes the window (main loop). The game is
  landscape only: a touch screen showing the page upright
  (`touch.portrait`, e.g. rotation locked) gets a portrait window with the
  landscape frame drawn into it a quarter turn clockwise (`main._show`,
  `touch.rotated`; played with the phone's top to the left), touches
  turned back (`touch._unturn`); `POKEMON_PORTRAIT=1` forces it on the
  desktop. Turning the phone remakes the window. Saved in the
  player's settings (`saves.load_prefs`/`save_prefs`: `saves/settings.json`,
  mirrored to localStorage like saves; key "touch").
- `tools/` holds standalone helper scripts. `tools/balance_sim.py` simulates battles
  for balance (the story's major fights at the expected levels, with or
  without talents; 1v1 duels between every line; greedy party AI). `tools/anim_viewer.py` uses only
  the standard library (it renders an HTML page and opens it in the browser).
- Firefox on this machine is a snap and cannot open files under `/tmp`;
  write files it needs to open inside the project (e.g. `build/`).

## Assets

- Sprite sheets in `assets/sprites/pixellab/`: every species with art has
  one PixelLab sheet, `<species>.png` (`pokemon._animated`): 64×64 cells,
  sprites face right (mirrored for left), rows idle, walk, run (8 frames
  each, looping), attack (9 frames: still pose + 8) and jump (crouch,
  rise, fall, land: picked from 9 generated frames, `per_frame_baseline`).
  `hit=` is the attack frame that strikes; the attack is cut one frame
  after it (battles strike on the second-to-last frame). Each starts from
  a base sprite (create_image_pro, a side profile facing right, padded to
  the cell's bottom) animated with pixminimax. Bases are generated at
  sizes that keep species roughly to scale: 32–40 px canvases for small
  ones (Rattata, Spearow, the starters, Pidgey), 48–52 px for middle forms
  and big ones (Ivysaur, Charmeleon, Wartortle, Pidgeotto, Fearow,
  Pidgeot), 64 px for Venusaur. Charizard and Blastoise were redrawn
  bigger: Blastoise a 56 px base (mirrored to face right), Charizard a
  72 px redraw of a 56 px pick (about 52×56 in the cell; its run row
  regenerated with the wings held still). Onix keeps its larger
  sheet, drawn 1.5× (`Species.size`, nearest-neighbour; hats follow it).
  Geodude's attack and jump and Venusaur's jump are made from the base pose
  (a lunge, squash and stretch); so are Squirtle's and Pidgey's idles (the
  base with 1 px breathing, as the generated ones changed the face every
  frame) and Squirtle's jump crouch. Their bases were generated with the
  species' icon as a design reference and Charmander as a style reference
  (Oddish, Bellsprout, Abra, Venonat, Goldeen, Staryu, Starmie, Horsea,
  Shellder, Psyduck, Butterfree, Beedrill, Raticate, Nidorina, Nidorino,
  Kadabra, Meowth, Mankey, Machop, Tentacool, Growlithe, Voltorb, Magnemite,
  Raichu, Drowzee and Dugtrio too, made the same way (Meowth's, Mankey's, Tentacool's,
  Voltorb's and Magnemite's on 32 px canvases, Machop's and Growlithe's on
  36 px, Raichu's on 40 px with Pikachu as its style reference, Drowzee's and Dugtrio's on
  36 px, Dugtrio's with Diglett as its style reference; Meowth's idle is its base
  with 1 px breathing). Snorlax asleep (the species `snorlax_asleep`, a look for
  townsfolk only): `snorlax_asleep.png` is one row, a lying base (64×48)
  with 1 px breathing, drawn 1.5×; awake (`snorlax`, quest
  "snorlax_west") it battles and joins, with its own sheet (`snorlax.png`:
  a standing base on a 60 px canvas, the sleeping sheet as its style
  reference, pixminimax rows; hats fit); Weezing likewise (Koga's gym: a 48 px base,
  Koffing as its style reference, mirrored to face right); the Safari Zone's
  Chansey, Scyther, Tauros, Pinsir, Dratini and Dragonair likewise (bases
  picked from candidates, pixminimax rows; Dragonair drawn 1.25×), and
  Lapras (Silph Co.'s gift, a 64 px base), Mr. Mime (a 48 px base,
  Kadabra as style reference) and Alakazam (a 56 px base, Machoke as style
  reference: with Kadabra's it kept Kadabra's tail; walk and run rows
  regenerated with clearer steps), Hitmonchan (48 px), Hitmonlee (48 px,
  rerolled for its long legs, mirrored to face right; walk regenerated: the
  first kicked) and Machamp (56 px; the Dojo's Karate Master), Machoke as
  their style reference; Golbat, Arbok,
  Persian and Machoke were made by Claude the same way (48 px canvases,
  the pre-evolution's sprite as style reference; the base padded into the
  64 px cell, then pixminimax rows ending on the base so they loop; tiny
  stray specks cleared; Golbat's run row is its walk); so were Gloom,
  Vileplume, Weepinbell, Victreebel, Clefable, Wigglytuff, Nidoqueen and
  Nidoking (48 px canvases, 56 px for the final forms; Nidoking's base and
  Weepinbell's mirrored, as theirs faced left), and the Pokémon Tower's
  Gastly, Haunter (Zubat as style reference), Cubone and Marowak
  (Sandshrew's); and the Rocket Hideout's Koffing (Gastly's), Grimer
  (Ekans'), Hypno (Drowzee's), Rhyhorn (Nidorino's) and Kangaskhan
  (Drowzee's outline and shading only); and Sandslash, Graveler and
  Parasect (their pre-evolutions'); Goldeen's, Butterfree's, Raticate's and Nidorino's bases were mirrored, as
  their candidates faced left; Graveler's whole sheet was mirrored afterwards, as it
  faced left). Placeholder quality: likely to be redone.
- On maps, every species' sprite is drawn 3 px into the ground like the
  player's (`player.FOOT_SINK`: the sheets' feet are at a 3/4 angle), so
  townsfolk and wild packs stand in the grass, not on top of it; props
  (the smith, `town._NPC`) aren't sunk. Battles don't sink sprites.
- A move's `anim` plays if the species has that animation; otherwise the
  species' `fight_anim` does (no move-specific sheets for now).
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
  route_3, pewter_gym, mt_moon, cerulean_gym, underground, ss_anne,
  vermilion_gym, digletts_cave, rock_tunnel, celadon_gym, fuchsia_gym,
  silph_co, silph_office, saffron_gym, fighting_dojo, tower_1..5; underground and ss_anne shifted up 14 px, their floor extended), their ground starting high enough for the
  back row (about 40% down: a map's side-view wall art won't do, the
  Pokémon would float in front of it); a theme without one would be drawn in code from the
  `Backdrop` colours.
- Map props (`assets/sprites/pixellab/props/`, `tileset.draw_prop`: centred,
  standing on the ground): chests (closed/open, plain and the gyms' fancy
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
  paintings of Mt. Moon's, the Pewter Gym's, the Cerulean Gym's, the
  Underground Path's, the S.S. Anne's, the Vermilion Gym's, Diglett's Cave's, Rock Tunnel's, the Celadon Gym's and the Battle Tower's far wall, drawn 2×,
  mirrored every other copy, dimmed (`dim`); the code-drawn rock in front
  stays (`near_rocks`, off in the gym).
- `assets/sprites/pokemon_icons/` holds reference icons. Species without a
  Pixellab sheet use their icon as a still placeholder sprite
  (`Species.icon`; mirrored to face right) until they get one.
