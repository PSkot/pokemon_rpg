"""Sky battles: the rules of the "Learn to Fly" trial (docs/mechanics.md →
Sky battles).

The party's Flying-type Pokémon ("fliers") fight in the open air:
- they're lent Fly and Perch (`SKY_MOVES`, the battle's "Sky" command);
- the wind changes every round (`WINDS`), and the next one is known a round
  ahead, so the player can plan;
- their wings tire: every round they end in the air costs `FATIGUE` of their
  max HP, unless they perched that round.
"""

import random
from dataclasses import dataclass

from .moves import MOVES

SKY_MOVES = (MOVES["Fly"], MOVES["Perch"])
FATIGUE = 1 / 16  # share of a flier's max HP lost at the end of each round it spends in the air


@dataclass(frozen=True)
class Wind:
    name: str
    text: str            # said when it starts blowing
    weight: int          # how often it comes (relative)
    speed: float = 1.0   # fliers' Speed ×
    power: float = 1.0   # fliers' Flying moves' power ×
    accuracy: float = 1.0  # fliers' moves' chance to hit ×
    updraft: bool = False  # Fly strikes at once (no round up high)
    effect: str = ""     # what it does, in short (the wind panel)


WINDS = {w.name: w for w in [
    Wind("Calm", "The air is calm.", 30, effect="No effect"),
    Wind("Tailwind", "A tailwind blows! Fliers speed up, and their Flying moves hit harder.", 25,
         speed=1.5, power=1.3, effect="SPD x1.5, Flying x1.3"),
    Wind("Headwind", "A headwind blows! Fliers slow down, and their aim is off.", 25,
         speed=2 / 3, accuracy=0.85, effect="SPD x0.67, ACC x0.85"),
    Wind("Updraft", "An updraft rises! Fly strikes at once.", 20, updraft=True, effect="Fly: no charging"),
]}


def roll_wind(previous: str = "", rng=random) -> str:
    """The next round's wind: never the same twice in a row."""
    options = [w for w in WINDS.values() if w.name != previous]
    return rng.choices(options, weights=[w.weight for w in options])[0].name
