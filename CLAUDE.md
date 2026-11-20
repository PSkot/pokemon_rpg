# Pokémon RPG Platformer

2D RPG platformer fan game following the Kanto (Red/Blue) story. Personal,
non-commercial project.

## Working style

- Build the game slowly, one part at a time: get each part right ("perfect")
  and confirmed by the user before starting the next.
- Show results visually where possible (screenshots, previews) before moving on.

## Where things are documented

Read only what the task needs:

- `docs/architecture.md`: how each system is built (scenes, battles, gear,
  hats, loot, XP, talents, evolution, items, maps, towns, routes, dungeons,
  gyms, Battle Tower, saves, quests, recruitment, dev mode, touch controls,
  assets). Grep it for the system you're touching, e.g. `grep -n Gear`.
- `docs/mechanics.md`: every rule and number (stats, XP, damage, status,
  gear rolls, loot, types).
- `docs/quests.md`: quests, area levels, recruitment.
- `docs/talents.md`: generated talent tables (big: grep it, don't read it all).

## Tech

- Python + pygame-ce (`import pygame`); dependencies in `requirements.txt`,
  installed into `.venv/`. Run with `.venv/bin/python -m game`. Renders at
  640×360, scaled ×2.
- Async main loop (`await asyncio.sleep(0)` per frame) for the browser
  build: `tools/web_build.py` (pygbag; `--serve` on localhost:8000).
  `.github/workflows/pages.yml` publishes it to
  https://pskot.github.io/pokemon_rpg/ on every push.
- Code in `game/`: `main.py`, `settings.py`, `saves.py`, `dev.py`;
  `engine/` (scenes, UI, animation, hats, touch), `mechanics/` (rules and
  data), `world/` (maps, towns, routes, progress, quests), `scenes/`
  (title, maps, battle, menus). Dependencies point downwards:
  scenes → world/mechanics → engine.
- Scenes (`engine/scene.Scene`) switch by setting `next_scene`; sprites go
  on the logical canvas, text on the scaled window (`draw_overlay`).
  Battle sequences are generator scripts yielding seconds to wait.
- Test headlessly with `SDL_VIDEODRIVER=dummy`: drive
  `Player.update(dt, Controls(...), level)` and save frames with
  `pygame.image.save()`.
- `tools/`: standalone helpers (`balance_sim.py` battle balance,
  `talent_docs.py` regenerates `docs/talents.md`, `hat_autofit.py` /
  `hat_viewer.py`, `anim_viewer.py`).

## Rules

- When changing a rule or number, update `docs/mechanics.md` in the same
  change. After changing talents, run `python tools/talent_docs.py`.
- Keep `docs/architecture.md` current when a system's design changes, but
  don't add per-feature detail to this file: it loads every session.
- Claude may make art with PixelLab (the PixelLab MCP tools): show the candidates
  (e.g. base poses) for the user to pick before animating and wiring them in.
- Firefox on this machine is a snap and cannot open files under `/tmp`;
  write files it needs inside the project (e.g. `build/`).
