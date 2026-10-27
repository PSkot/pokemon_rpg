"""Saving and loading: one autosave (overwritten each time) and any number
of manual saves, as JSON files in saves/, next to the player's settings
(settings.json: not a save).

A save holds the player's progress (`world.Game`) and where the player is:
in a town, or on a map of a route or dungeon run (`MapScene.location`).
Maps aren't stored: the run's seed generates the same maps again.

In the browser (pygbag) files don't outlast the page, so each save file is
also kept in the browser's localStorage and written back on start.
"""

import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import settings
from .mechanics.items import AFFIX_BY_NAME, ITEMS, RARITIES, Bag, Gear, Roll
from .mechanics.pokemon import SPECIES, Monster
from .world.progress import Game

SAVE_DIR = settings.ROOT / "saves"
AUTOSAVE = SAVE_DIR / "autosave.json"
PREFS = SAVE_DIR / "settings.json"  # the player's settings (e.g. touch controls), not a save
VERSION = 2
NOTICE_TIME = 2.0  # seconds "Autosaved" stays on screen

_autosaved_at = -NOTICE_TIME  # time.monotonic() of the last autosave

WEB = sys.platform == "emscripten"
WEB_PREFIX = "pokemon_rpg/saves/"  # localStorage key = prefix + file name


@dataclass
class SaveInfo:
    """A save file, as listed in the save and load menus."""
    path: Path
    saved_at: datetime
    where: str                      # "Pallet Town", "Route 1   map 1/2   to Viridian City"
    party: list[tuple[str, int]]    # (name, level)

    @property
    def auto(self) -> bool:
        return self.path == AUTOSAVE

    @property
    def number(self) -> int:
        """A manual save's number (save_3.json -> 3); 0 for the autosave."""
        return 0 if self.auto else int(self.path.stem.split("_")[1])

    @property
    def name(self) -> str:
        return "Autosave" if self.auto else f"Save {self.number}"


# ------------------------------------------------------------ to and from JSON

def _gear(g: Gear) -> dict:
    return {"item": g.item.name, "rarity": g.rarity.name, "level": g.level,
            "rolls": [{"affix": r.affix.name if r.affix else None, "mods": r.mods} for r in g.rolls]}


def _load_gear(d: dict) -> Gear:
    rolls = [Roll(AFFIX_BY_NAME[r["affix"]] if r["affix"] else None, r["mods"]) for r in d["rolls"]]
    return Gear(ITEMS[d["item"]], RARITIES[d["rarity"]], rolls, d.get("level", 1))


def _monster(m: Monster) -> dict:
    return {"species": m.species.key, "level": m.level, "xp": m.xp, "hp": m.hp, "status": m.status,
            "sleep_rounds": m.sleep_rounds, "gear": {slot: _gear(g) for slot, g in m.gear.items()},
            "skills": m.skills, "equipped": m.equipped}


def _load_monster(d: dict) -> Monster:
    gear = {slot: _load_gear(g) for slot, g in d["gear"].items()}
    species = SPECIES[d["species"]]
    # Skills its tree no longer has are dropped (and ranks above a skill's
    # max cut down); saves from before skill trees have none, so the
    # Pokémon starts with its base attacks.
    tree = species.tree.skills
    skills = {key: min(rank, tree[key].max_rank) for key, rank in d.get("skills", {}).items() if key in tree}
    equipped = [key for key in d.get("equipped", []) if key in skills]
    return Monster(species, d["level"], hp=d["hp"], gear=gear, status=d["status"],
                   sleep_rounds=d["sleep_rounds"], xp=d["xp"], skills=skills, equipped=equipped)


def snapshot(scene) -> dict:
    """The game's state, with the player on `scene`'s map (a `MapScene`)."""
    game = scene.game
    return {
        "version": VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {"where": scene.where(), "party": [[m.name, m.level] for m in game.party]},
        "party": [_monster(m) for m in game.party],
        "bag": {"gear": [_gear(g) for g in game.bag.gear], "medicine": dict(game.bag.medicine),
                "key_items": game.bag.key_items, "money": game.bag.money},
        "town": game.town,
        "cleared": dict(game.cleared),
        "starter": game.starter,
        "quests": game.quests,
        "quest_counts": game.quest_counts,
        "trainers": sorted(game.trainers),
        "location": scene.location(),
    }


# ------------------------------------------------------------------- files

def _web_storage():
    import platform  # pygbag's: gives access to the page (`window`)
    return platform.window.localStorage


def _restore_web_saves() -> None:
    """Write the saves kept in localStorage back into SAVE_DIR."""
    SAVE_DIR.mkdir(exist_ok=True)
    storage = _web_storage()
    for i in range(storage.length):
        key = storage.key(i)
        if key.startswith(WEB_PREFIX):
            (SAVE_DIR / key[len(WEB_PREFIX):]).write_text(storage.getItem(key))


def _write(path: Path, data: dict) -> None:
    """Write via a temporary file, so a crash mid-save can't ruin the old save."""
    SAVE_DIR.mkdir(exist_ok=True)
    text = json.dumps(data, indent=1)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
    if WEB:
        _web_storage().setItem(WEB_PREFIX + path.name, text)


def autosave(scene) -> None:
    global _autosaved_at
    _write(AUTOSAVE, snapshot(scene))
    _autosaved_at = time.monotonic()


def recently_autosaved() -> bool:
    return time.monotonic() - _autosaved_at < NOTICE_TIME


def save(scene, over: SaveInfo | None = None) -> str:
    """A manual save: over an existing one, or a new one. Returns its name."""
    number = over.number if over else max((s.number for s in list_saves()), default=0) + 1
    _write(SAVE_DIR / f"save_{number}.json", snapshot(scene))
    return f"Save {number}"


def delete(info: SaveInfo) -> None:
    info.path.unlink(missing_ok=True)
    if WEB:
        _web_storage().removeItem(WEB_PREFIX + info.path.name)


def load_prefs() -> dict:
    """The player's settings ({} if none are saved or the file is damaged)."""
    try:
        prefs = json.loads(PREFS.read_text())
        return prefs if isinstance(prefs, dict) else {}
    except (OSError, ValueError):
        return {}


def save_prefs(prefs: dict) -> None:
    _write(PREFS, prefs)


def list_saves() -> list[SaveInfo]:
    """The autosave first, then the manual saves, newest first. Files that
    can't be read are left out."""
    saves = []
    for path in SAVE_DIR.glob("*.json"):
        if path != AUTOSAVE and not (path.stem.startswith("save_") and path.stem[5:].isdigit()):
            continue
        try:
            data = json.loads(path.read_text())
            summary = data["summary"]
            saves.append(SaveInfo(path, datetime.fromisoformat(data["saved_at"]), summary["where"],
                                  [tuple(p) for p in summary["party"]]))
        except (OSError, ValueError, KeyError, IndexError):
            continue
    return sorted(saves, key=lambda s: (not s.auto, -s.saved_at.timestamp()))


def latest() -> SaveInfo | None:
    saves = list_saves()
    return max(saves, key=lambda s: s.saved_at) if saves else None


def load(info: SaveInfo):
    """The map scene to continue on. Raises `LoadError` if the file is
    damaged or from an incompatible version."""
    # Imported here: the scenes import this module (for autosaves).
    from .world.instance import ROUTES, Instance
    from .scenes.overworld import OverworldScene
    from .scenes.town import TownScene
    from .world.towns import TOWNS

    try:
        data = json.loads(info.path.read_text())
        if data["version"] != VERSION:
            raise LoadError(f"{info.name} is from an older version of the game.")
        party = [_load_monster(m) for m in data["party"]]
        bag = Bag([_load_gear(g) for g in data["bag"]["gear"]], Counter(data["bag"]["medicine"]),
                  list(data["bag"].get("key_items", [])), data["bag"].get("money", 0))
        game = Game(party, bag, data["town"], Counter(data["cleared"]), data.get("starter", "bulbasaur"),
                    dict(data.get("quests", {})), dict(data.get("quest_counts", {})),
                    set(data.get("trainers", [])))
        where = data["location"]
        if where["kind"] == "town":
            scene = TownScene(game, TOWNS[where["town"]])
        else:
            instance = Instance(ROUTES[where["route"]], where["destination"], seed=where["seed"], index=where["map"])
            scene = OverworldScene(instance, game)
        scene.restore(where)
        return scene
    except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
        raise LoadError(f"{info.name} couldn't be loaded.") from e


class LoadError(Exception):
    pass


if WEB:
    _restore_web_saves()
