"""Dev mode: tools for testing, switched on in the pause menu.

While it's on: XP from battles can be multiplied, god mode makes the party
take no damage and knocks out every enemy it hits, pack skipping lets the
player walk through wild packs and map trainers' bands (not bosses), all
the Battle Tower's floors can be opened (otherwise badges open them, as
usual), and items can be made to order (pause menu → Add item). Once the password has
been given, it and these settings are remembered in the player's settings
(saves.save_prefs: settings.json, and in the browser its localStorage), so
they come back on the next start; they're never part of a save.
"""

from dataclasses import dataclass

XP_BOOSTS = (1, 3, 5, 10, 20)
PASSWORD = "iamthedev"  # asked before dev mode first switches on (scenes/dev_menu.PasswordPrompt)


@dataclass
class DevMode:
    enabled: bool = False
    xp_boost: int = 1   # one of XP_BOOSTS
    god: bool = False
    skip: bool = False  # walk through packs (wild groups and map trainers; bosses still fight)
    tower: bool = False  # the Battle Tower open, with all its floors (off: as badges open them)
    unlocked: bool = False  # the password was given (asked once; remembered in the player's settings)

    @property
    def xp_multiplier(self) -> int:
        return self.xp_boost if self.enabled else 1

    @property
    def god_mode(self) -> bool:
        return self.enabled and self.god

    @property
    def skip_packs(self) -> bool:
        return self.enabled and self.skip

    @property
    def tower_open(self) -> bool:
        return self.enabled and self.tower

    def prefs(self) -> dict:
        """What's remembered in the player's settings ({} until unlocked)."""
        if not self.unlocked:
            return {}
        return {"unlocked": True, "enabled": self.enabled, "xp_boost": self.xp_boost, "god": self.god,
                "skip": self.skip, "tower": self.tower}

    def configure(self, prefs: dict) -> None:
        """Back as remembered (`prefs`), at the start."""
        if not prefs.get("unlocked"):
            return
        self.unlocked = True
        self.enabled = bool(prefs.get("enabled"))
        self.xp_boost = prefs.get("xp_boost") if prefs.get("xp_boost") in XP_BOOSTS else 1
        self.god, self.skip = bool(prefs.get("god")), bool(prefs.get("skip"))
        self.tower = bool(prefs.get("tower"))

    def summary(self) -> str:
        """What's on, e.g. "DEV  XP×5  GOD" ("" while dev mode is off)."""
        if not self.enabled:
            return ""
        parts = ["DEV"]
        if self.xp_boost > 1:
            parts.append(f"XP×{self.xp_boost}")
        if self.god:
            parts.append("GOD")
        if self.skip:
            parts.append("SKIP")
        if self.tower:
            parts.append("TOWER")
        return "  ".join(parts)


DEV = DevMode()
