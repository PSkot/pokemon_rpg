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

## Project layout

```
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
python3 tools/anim_viewer.py path/to/sheet.png --frame 64 --rows walk "run 1" "run 2" attack
```

## Sprite sheet format

- Each sheet is a grid of equally sized frames (currently 64×64).
- Each row is one animation, read left to right.
- Sprites face **right**; the game mirrors them to face left.
- Bulbasaur rows: `walk`, `run 1`, `run 2`, `attack`.
