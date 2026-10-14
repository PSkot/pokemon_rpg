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
  scales ×2; the ground is at logical y=300.
- Test headlessly with `SDL_VIDEODRIVER=dummy`: drive `Player.update()` with
  `Controls(...)` objects and save frames with `pygame.image.save()`.
- The game is a set of scenes (`scene.Scene`): map (`overworld.py`) and
  battle (`battle.py`). A scene switches by setting `next_scene`. Scenes
  draw sprites on the logical canvas and text on the scaled window
  (`draw_overlay`), so text stays sharp.
- Battles: separate battle screen, Final Fantasy style (enemies left, party
  right), strict turn-based: the party picks actions, then everyone's
  actions play out fastest first. Battle sequences are generator "scripts"
  that yield seconds to wait (`BattleScene._round` / `_perform`).
- Each `Animation` aligns its own baseline (lowest opaque row) to the feet
  position, because rows in a sheet sit at different heights. Rows whose
  effects reach below the feet pass an explicit `baseline=` instead.
- Controls: arrows move, Shift runs, Space jumps, number keys 1–9 are
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
- `assets/sprites/pokemon_icons/` holds reference icons only, not in-game art.
