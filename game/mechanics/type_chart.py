"""The 15 Gen 1 types and how well each attacks the others.

The chart is Gen 1's as intended: Ghost is super effective against Psychic
(the original games had a bug that made it have no effect).
"""

TYPES = ("normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison",
         "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon")

COLORS = {
    "normal": (168, 168, 120), "fire": (240, 128, 48), "water": (104, 144, 240),
    "electric": (248, 208, 48), "grass": (120, 200, 80), "ice": (152, 216, 216),
    "fighting": (192, 48, 40), "poison": (160, 64, 160), "ground": (224, 192, 104),
    "flying": (168, 144, 240), "psychic": (248, 88, 136), "bug": (168, 184, 32),
    "rock": (184, 160, 56), "ghost": (112, 88, 152), "dragon": (112, 56, 248),
}

# attacking type -> {defending type: multiplier}; anything not listed is 1.
_CHART = {
    "normal": {"rock": 0.5, "ghost": 0},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5},
    "water": {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5,
              "bug": 0.5, "rock": 2, "dragon": 0.5},
    "ice": {"water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2, "dragon": 2},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5,
                 "rock": 2, "ghost": 0},
    "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "bug": 2, "rock": 0.5, "ghost": 0.5},
    "ground": {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2},
    "flying": {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5},
    "bug": {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 2, "flying": 0.5, "psychic": 2,
            "ghost": 0.5},
    "rock": {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2},
    "ghost": {"normal": 0, "psychic": 2, "ghost": 2},
    "dragon": {"dragon": 2},
}


def name(type_: str) -> str:
    return type_.capitalize()


def effectiveness(attack: str, defender: tuple[str, ...]) -> float:
    """Damage multiplier of an `attack`-type hit on a Pokémon with types
    `defender`. Typeless attacks ("") are always 1."""
    result = 1.0
    for t in defender:
        result *= _CHART.get(attack, {}).get(t, 1)
    return result
