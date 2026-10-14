"""Global constants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# The game is drawn at a low "logical" resolution and scaled up by a whole
# number, so pixel art stays crisp.
LOGICAL_SIZE = (640, 360)
SCALE = 2
WINDOW_SIZE = (LOGICAL_SIZE[0] * SCALE, LOGICAL_SIZE[1] * SCALE)
FPS = 60
TITLE = "Pokémon RPG Platformer"

GROUND_Y = 300  # logical y of the ground surface

SKY_COLOR = (148, 206, 240)
GROUND_COLOR = (124, 92, 60)
GRASS_COLOR = (98, 178, 72)
