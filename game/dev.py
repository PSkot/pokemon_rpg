"""Dev mode: tools for testing, switched on in the pause menu.

While it's on: XP from battles can be multiplied, god mode makes the party
take no damage and knocks out every enemy it hits, and items can be made
to order (pause menu → Add item). The settings only last until the game
is closed; they aren't saved.
"""

from dataclasses import dataclass

XP_BOOSTS = (1, 3, 5, 10, 20)


@dataclass
class DevMode:
    enabled: bool = False
    xp_boost: int = 1   # one of XP_BOOSTS
    god: bool = False

    @property
    def xp_multiplier(self) -> int:
        return self.xp_boost if self.enabled else 1

    @property
    def god_mode(self) -> bool:
        return self.enabled and self.god

    def summary(self) -> str:
        """What's on, e.g. "DEV  XP×5  GOD" ("" while dev mode is off)."""
        if not self.enabled:
            return ""
        parts = ["DEV"]
        if self.xp_boost > 1:
            parts.append(f"XP×{self.xp_boost}")
        if self.god:
            parts.append("GOD")
        return "  ".join(parts)


DEV = DevMode()
