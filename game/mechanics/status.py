"""Status conditions: burn, poison, paralysis, sleep and freeze.

A Pokémon has at most one, and keeps it after battle until it is cured
(or faints).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Status:
    key: str
    name: str                    # as in "Burn chance", "of the Muk"
    abbrev: str                  # badge text
    color: tuple[int, int, int]
    immune: str                  # Pokémon of this type can't get it
    inflicted: str               # messages; {} is the Pokémon
    cured: str


BURN = Status("burn", "Burn", "BRN", (240, 128, 48), "fire",
              "{} was burned!", "{}'s burn was healed!")
POISON = Status("poison", "Poison", "PSN", (160, 64, 160), "poison",
                "{} was poisoned!", "{} was cured of poison!")
PARALYSIS = Status("paralysis", "Paralysis", "PAR", (248, 208, 48), "electric",
                   "{} is paralyzed! It may be unable to move!", "{} was cured of paralysis!")
SLEEP = Status("sleep", "Sleep", "SLP", (150, 150, 165), "",
               "{} fell asleep!", "{} woke up!")
FREEZE = Status("freeze", "Freeze", "FRZ", (152, 216, 216), "ice",
                "{} was frozen solid!", "{} thawed out!")
STATUSES = {s.key: s for s in (BURN, POISON, PARALYSIS, SLEEP, FREEZE)}

# Damage at the end of each round, as a share of max HP.
ROUND_DAMAGE = {"burn": 1 / 16, "poison": 1 / 8}
BURN_ATTACK = 0.5          # attack while burned
PARALYSIS_SPEED = 0.5      # speed while paralyzed
FULLY_PARALYZED = 0.25     # chance a paralyzed Pokémon can't move
SLEEP_ROUNDS = (1, 3)
THAW_CHANCE = 0.2          # per round
