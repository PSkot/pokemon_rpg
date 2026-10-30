# Pokémon RPG Platformer

A 2D RPG platformer fan game that follows the story of the original Kanto
games (Red/Blue), built with [pygame-ce](https://pyga.me/).

> Personal, non-commercial fan project. Pokémon and all related names and
> artwork are © Nintendo / Creatures Inc. / GAME FREAK inc. This project is
> not affiliated with or endorsed by them, and must not be sold or
> distributed commercially.

## Setup

Requires Python 3.11+.

On Debian/Ubuntu, make sure pip and venv are available (one-time):

```sh
sudo apt install python3-venv python3-pip
```

Then create a virtual environment and install the dependencies:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```sh
source .venv/bin/activate
python -m game
```

Currently a test map with Bulbasaur and a wild Pidgey. Walk into the
Pidgey to start a turn-based battle: choose Fight or a skill and a target
for each party member, then everyone acts in Speed order. Solar Beam
charges for a round before firing; Growth raises Attack; Leaf Shield halves
the damage an ally takes this round and the next.

| Key | Action |
| --- | --- |
| Left / Right | walk |
| Shift (held) | run |
| Space | jump (tap = small hop, hold = full jump) |
| 1–5 | attacks (attacks will go on 1–9) |
| F1 | debug boxes (frame, body, feet position) |
| Esc | quit |

In battle: arrows choose, Enter (or Space/Z) confirms, X (or Backspace) goes
back. Going back from the command menu undoes the previous party member's
choice.

## Project layout

```
game/
  main.py            Window and game loop
  scene.py           Scene base class, battle transition effect
  overworld.py       The map scene; wild Pokémon that start battles
  battle.py          Turn-based battle scene
  ui.py              Menu windows, text, HP bars
  pokemon.py         Moves, species (stats, animations) and Monster (level, HP)
  player.py          Player movement + animation states
  animation.py       Sprite sheet loading, Animation class
  settings.py        Resolution, colours, paths
assets/
  sprites/
    pixellab/        Animated sprite sheets made with Pixellab (64x64 frames)
    pokemon_icons/   Gen 1 reference icons from pokemondb (NNN_name.png)
tools/
  anim_viewer.py     Preview the animations in a sprite sheet in the browser
build/               Generated files (git-ignored)
```

## Tools

### Animation viewer

Plays every row of a sprite sheet as its own animation, with speed, zoom,
flip and background controls. Uses only the Python standard library.

```sh
python3 tools/anim_viewer.py                      # Bulbasaur sheet
python3 tools/anim_viewer.py path/to/sheet.png --frame 64 --rows walk run jump attack
```

## Sprite sheet format

- Each sheet is a grid of equally sized frames (currently 64×64).
- Each row is one animation, read left to right.
- Sprites face **right**; the game mirrors them to face left.
- Most species (the starters, Rattata, ...): rows `idle`, `walk`, `run`,
  `attack`, `jump`.
- Jump rows have 4 frames: crouch, leap (rising), airborne (falling), landing.
  The game picks the frame from the jump's phase, not from a timer.
