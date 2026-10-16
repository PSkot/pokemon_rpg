"""Moves: what a Pokémon does in battle.

A move here is its Gen 1 base form. Skill ranks and modifiers (skills.py)
make a changed copy of it for a particular Pokémon (`dataclasses.replace`
with the rank's and modifiers' changes), so every effect is a field.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    name: str
    power: int          # 0 = status move (no damage)
    target: str         # "enemy" (the other side), "ally" (own side) or "self"
    anim: str = ""      # animation name; "" = the species' `fight_anim`
    type: str = ""      # one of type_chart.TYPES; "" = typeless
    # Moves with a charge message spend a round charging (the first half of
    # the animation) and fire the next round (the second half).
    charge: str = ""
    status: str = ""    # a status (see status.STATUSES) the move inflicts ...
    status_chance: int = 0  # ... with this % chance (100 for status moves)
    stages: tuple[tuple[str, int], ...] = ()  # stat stage changes on the target ("attack", -1)
    seed: float = 0.0   # Leech Seed: share of the target's max HP drained each round
    shield: int = 0     # Leaf Shield: rounds the target takes half damage
    spread: bool = False      # hits every target on that side
    spread_share: float = 1.0  # damage share of each hit when it spreads
    heal: float = 0.0   # the user also heals this share of its max HP
    recoil: float = 0.0  # the user takes this share of the damage dealt
    recharge: bool = False  # the user must rest the next round (Hyper Beam)
    crit_ratio: float = 1.0  # × crit chance (8 = Gen 1's high crit ratio)
    toxic: bool = False  # its poison gets worse every round (Toxic)
    sleep_bonus: int = 0  # extra rounds asleep
    scale: float = 1.0   # damage × this (from the skill's rank)

    @property
    def damaging(self) -> bool:
        return self.power > 0


MOVES = {m.name: m for m in [
    # The Bulbasaur line (see skills.py).
    Move("Tackle", 35, "enemy", "tackle", type="normal"),
    Move("Growl", 0, "enemy", type="normal", stages=(("attack", -1),)),
    Move("Leech Seed", 0, "enemy", type="grass", seed=1 / 16),
    Move("Vine Whip", 35, "enemy", type="grass"),
    Move("Poison Powder", 0, "enemy", type="poison", status="poison", status_chance=100),
    Move("Take Down", 90, "enemy", type="normal", recoil=0.25),
    Move("Razor Leaf", 55, "enemy", type="grass", crit_ratio=8),
    Move("Growth", 0, "self", "growth", type="normal", stages=(("attack", 1),)),
    Move("Leaf Shield", 0, "ally", "leaf_shield", type="grass", shield=2),
    Move("Sleep Powder", 0, "enemy", type="grass", status="sleep", status_chance=100),
    Move("Body Slam", 85, "enemy", type="normal", status="paralysis", status_chance=30),
    Move("Solar Beam", 120, "enemy", "solar_beam", type="grass", charge="{user} took in sunlight!"),
    Move("Double-Edge", 100, "enemy", type="normal", recoil=0.25),
    Move("Hyper Beam", 150, "enemy", type="normal", recharge=True),
    # Other species' moves, until their lines get skill trees.
    Move("Gust", 40, "enemy", "gust", type="flying"),  # Normal in Gen 1, Flying since Gen 2
    Move("Scratch", 40, "enemy", type="normal"),
    Move("Bite", 60, "enemy", type="normal"),
    Move("Headbutt", 70, "enemy", type="normal"),
    Move("Quick Attack", 40, "enemy", type="normal"),
    Move("Poison Sting", 15, "enemy", type="poison", status="poison", status_chance=30),
    Move("Acid", 40, "enemy", type="poison", status="poison", status_chance=10),
    Move("Absorb", 20, "enemy", type="grass"),
    Move("Thunder Shock", 40, "enemy", type="electric", status="paralysis", status_chance=10),
    Move("Water Gun", 40, "enemy", type="water"),
    Move("Bubble", 40, "enemy", type="water"),
    Move("Powder Snow", 40, "enemy", type="ice", status="freeze", status_chance=10),
    Move("Aurora Beam", 65, "enemy", type="ice"),
    Move("Ice Beam", 90, "enemy", type="ice", status="freeze", status_chance=10),
    Move("Confusion", 50, "enemy", type="psychic"),
]}
