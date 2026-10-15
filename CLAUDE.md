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
- Test headlessly with `SDL_VIDEODRIVER=dummy`: drive
  `Player.update(dt, Controls(...), level)` and save frames with
  `pygame.image.save()`.
- The game is a set of scenes (`scene.Scene`): map (`overworld.py`),
  battle (`battle.py`) and party screen (`summary.py`). A scene switches by setting `next_scene`. Scenes
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
- Dungeon instances (`instance.py`): 3–5 maps of one theme from one seed
  (a replay rolls a new seed). The last map ends in an arena where a boss
  group of 4–5 pool Pokémon (normal levels; stronger variants are kept for
  gyms/legendaries) guards the sealed way out; beating it unseals the door
  and drops a `BOSS_LOOT` chest. The hub (`hub.py`, a stand-in for towns)
  starts runs, heals the party, and is where you return after clearing a
  dungeon or fainting. `tileset.py` draws
  placeholder tiles, decorations and parallax backgrounds in code (to be
  replaced by Pixellab tilesets). The player collides with a fixed hitbox.
- Tab on the map opens the party screen (`summary.py`): stats and gear;
  Enter on a slot lists the bag's gear for it (or Remove), previewing the
  stat changes, and equips it.
- Controls: arrows move, Up opens chests, Shift runs, Space jumps, number keys 1–9 are
  reserved for attacks (1 = basic attack, 2–5 = extra attacks).
- `tools/` holds standalone helper scripts. `tools/anim_viewer.py` uses only
  the standard library (it renders an HTML page and opens it in the browser).
- Firefox on this machine is a snap and cannot open files under `/tmp`;
  write files it needs to open inside the project (e.g. `build/`).

## Assets

- Sprite sheets in `assets/sprites/pixellab/`: grid of 64×64 frames, one
  animation per row, sprites face right (mirror for left). Row order:
  walk, run, jump (crouch/rise/fall/land), attack.
- `bulbasaur attacks.png` holds the extra attacks for keys 2–5, one per row:
  growth, solar_beam, leaf_shield, tackle.
- `pidgey.png` rows: walk, fly, gust, tackle. Its frames don't all face
  right; the left-facing ones are listed in `face_left` and mirrored on load.
- Every species' animations are defined in `pokemon.py` (`AnimSpec`: sheet,
  row, fps, baseline, ...) and shared by the map player and battles.
- `assets/sprites/pokemon_icons/` holds reference icons. Species without a
  Pixellab sheet use their icon as a still placeholder sprite
  (`Species.icon`; mirrored to face right) until they get one.
