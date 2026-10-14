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
