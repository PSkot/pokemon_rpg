"""Fill in hat anchors for every species with a sprite sheet.

    python tools/hat_autofit.py [--force] [species ...]

For each species: its head anchor on the standing pose (idle frame 0) comes
from REFS below (set by eye: about 7 px above the eye, where the hat's face
hole lines up), then the head is tracked into every frame of every row
(`hat_viewer.detect_head`). Rows that already have anchors are kept unless
--force. The hat size per species comes from SCALES (relative to
Bulbasaur's head; the game also multiplies it by `Species.size`).
Everything goes into hat_anchors.json; fine-tune with tools/hat_viewer.py.
"""

import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from game.engine.hats import SHEET, load_data  # noqa: E402
from game.mechanics import pokemon  # noqa: E402
from hat_viewer import save_data  # noqa: E402

# Head anchor on idle frame 0 (sheet pixels).
REFS = {
    "bulbasaur": (38, 40), "ivysaur": (43, 36), "venusaur": (42, 27),
    "charmander": (37, 32), "charmeleon": (40, 29), "charizard": (49, 23),
    "squirtle": (35, 35), "wartortle": (36, 29), "blastoise": (40, 21),
    "pidgey": (36, 34), "pidgeotto": (48, 25), "pidgeot": (47, 18),
    "spearow": (41, 35), "fearow": (43, 24),
    "nidoran_f": (39, 44), "nidoran_m": (39, 42), "rattata": (39, 38),
    "caterpie": (35, 34), "metapod": (35, 33), "weedle": (41, 40), "kakuna": (38, 29),
    "pikachu": (37, 33), "geodude": (33, 40), "onix": (50, 17), "diglett": (34, 33),
    "sandshrew": (39, 29), "ekans": (39, 26), "jigglypuff": (41, 38), "zubat": (40, 38),
    "paras": (36, 41), "clefairy": (39, 34),
    "oddish": (38, 44), "bellsprout": (36, 31), "abra": (37, 35), "venonat": (36, 35),
    "goldeen": (38, 42), "staryu": (33, 36), "starmie": (32, 29), "horsea": (34, 33), "shellder": (33, 37), "psyduck": (33, 33),
    "butterfree": (39, 38), "beedrill": (37, 33), "raticate": (41, 40),
    "nidorina": (41, 38), "nidorino": (40, 39), "kadabra": (37, 28),
    "meowth": (35, 39), "mankey": (38, 43),
    "machop": (34, 35), "tentacool": (33, 36), "growlithe": (38, 35),
    "raichu": (39, 35), "voltorb": (32, 46), "magnemite": (31, 46), "drowzee": (32, 35), "dugtrio": (31, 35),
    "kangaskhan": (40, 21), "snorlax": (36, 9),
    "arbok": (36, 33), "sandslash": (43, 33), "nidoqueen": (46, 26), "nidoking": (42, 30), "koffing": (37, 36),
    "grimer": (38, 37), "golbat": (38, 43), "persian": (44, 35), "primeape": (36, 38), "machoke": (36, 32),
    "graveler": (33, 40), "magneton": (34, 37), "electrode": (36, 38), "golduck": (43, 28), "seaking": (41, 44),
    "venomoth": (39, 44), "gloom": (33, 42), "vileplume": (32, 36), "weepinbell": (33, 40), "victreebel": (36, 31),
    "parasect": (28, 38), "wigglytuff": (34, 41), "clefable": (36, 36), "hypno": (32, 34), "gastly": (36, 42),
    "haunter": (34, 41), "cubone": (37, 36), "marowak": (39, 35), "rhyhorn": (41, 40), "exeggcute": (32, 41),
    "exeggutor": (38, 20), "electabuzz": (37, 30), "tangela": (34, 40),
}

# Hat size, relative to Bulbasaur's head (about 18 px across).
SCALES = {
    "bulbasaur": 0.7, "ivysaur": 0.85, "venusaur": 1.0,
    "charmander": 0.65, "charmeleon": 0.7, "charizard": 0.8,
    "squirtle": 0.7, "wartortle": 0.8, "blastoise": 0.9,
    "pidgey": 0.6, "pidgeotto": 0.75, "pidgeot": 0.8, "spearow": 0.6, "fearow": 0.6,
    "nidoran_f": 0.65, "nidoran_m": 0.6, "rattata": 0.6,
    "caterpie": 0.6, "metapod": 0.65, "weedle": 0.6, "kakuna": 0.65,
    "pikachu": 0.7, "geodude": 0.8, "onix": 0.9, "diglett": 0.65, "sandshrew": 0.7,
    "ekans": 0.6, "jigglypuff": 0.85, "zubat": 0.6, "paras": 0.6, "clefairy": 0.8,
    "oddish": 0.6, "bellsprout": 0.6, "abra": 0.65, "venonat": 0.7,
    "goldeen": 0.6, "staryu": 0.6, "starmie": 0.7, "horsea": 0.6, "shellder": 0.65, "psyduck": 0.65, "butterfree": 0.65, "beedrill": 0.65, "raticate": 0.65,
    "nidorina": 0.7, "nidorino": 0.7, "kadabra": 0.7,
    "meowth": 0.65, "mankey": 0.7,
    "machop": 0.7, "tentacool": 0.65, "growlithe": 0.7,
    "raichu": 0.75, "voltorb": 0.6, "magnemite": 0.6, "drowzee": 0.7, "dugtrio": 0.6,
    "kangaskhan": 0.85, "snorlax": 1.0,
    "arbok": 0.7, "sandslash": 0.7, "nidoqueen": 0.8, "nidoking": 0.8, "koffing": 0.8, "grimer": 0.7,
    "golbat": 0.65, "persian": 0.65, "primeape": 0.85, "machoke": 0.7, "graveler": 0.9, "magneton": 0.6,
    "electrode": 0.85, "golduck": 0.7, "seaking": 0.65, "venomoth": 0.6, "gloom": 0.8, "vileplume": 1.0,
    "weepinbell": 0.7, "victreebel": 0.8, "parasect": 0.8, "wigglytuff": 0.85, "clefable": 0.8, "hypno": 0.7,
    "gastly": 0.8, "haunter": 0.75, "cubone": 0.7, "marowak": 0.7, "rhyhorn": 0.8, "exeggcute": 0.6,
    "exeggutor": 0.9, "electabuzz": 0.75, "tangela": 0.85,
}


def _pixels(frame: pygame.Surface) -> list[list[tuple[int, int, int, int]]]:
    w, h = frame.get_size()
    return [[tuple(frame.get_at((x, y))) for x in range(w)] for y in range(h)]


def track(reference: pygame.Surface, anchor: tuple[int, int], frame: pygame.Surface) -> tuple[int, int]:
    """Where the head around `anchor` in `reference` is in `frame`: the
    offset whose pixels match best (like hat_viewer.detect_head, sampled
    every other pixel, so a whole sheet runs in seconds). It searches around
    no move and around the body's own move (its top and front edges: jumps);
    when nothing matches (the body turned or became an effect), the anchor
    just follows the body's top and front edges."""
    ax, ay = anchor
    ref, pix = _pixels(reference), _pixels(frame)
    h, w = len(pix), len(pix[0])
    template = [(x, y, ref[y][x]) for y in range(max(0, ay - 5), min(len(ref), ay + 15), 1)
                for x in range(max(0, ax - 10), min(len(ref[0]), ax + 12), 1)
                if (x + y) % 2 == 0 and ref[y][x][3]]
    rb, fb = reference.get_bounding_rect(), frame.get_bounding_rect()
    moved = (fb.right - rb.right, fb.top - rb.top)
    offsets = {(dx, dy) for cx, cy in ((0, 0), moved)
               for dy in range(cy - 10, cy + 11) for dx in range(cx - 8, cx + 9)}
    best = None
    for dx, dy in sorted(offsets, key=lambda o: abs(o[0]) + abs(o[1])):
        cost = 0
        for x, y, c in template:
            x2, y2 = x + dx, y + dy
            if 0 <= x2 < w and 0 <= y2 < h and pix[y2][x2][3]:
                p = pix[y2][x2]
                cost += abs(p[0] - c[0]) + abs(p[1] - c[1]) + abs(p[2] - c[2])
            else:
                cost += 300
            if best and cost >= best[0]:
                break
        if not best or cost < best[0]:
            best = (cost, dx, dy)
    if best[0] > 220 * len(template):  # no likeness left
        return ax + moved[0], ay + moved[1]
    return ax + best[1], ay + best[2]


def fit(key: str, data: dict, force: bool) -> None:
    species = replace(pokemon.SPECIES[key], size=1.0)  # anchors are in sheet pixels
    anims = pokemon.animations(species)
    reference = anims["idle"].frames[0]
    for name, spec in species.anims.items():
        rows = data["heads"].setdefault(spec.sheet, {})
        frames = anims[name].frames
        if not force and len(rows.get(str(spec.row), [])) >= len(frames):
            continue
        rows[str(spec.row)] = [list(track(reference, REFS[key], f)) for f in frames]
    scale = data["sheets"].setdefault(SHEET, {}).setdefault("scale", {})
    scale[pokemon.SPECIES[key].name.lower()] = SCALES[key]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    pygame.init()
    pygame.display.set_mode((1, 1))
    data = load_data()
    for key in args or REFS:
        fit(key, data, force)
        print("fitted", key)
    save_data(data)


if __name__ == "__main__":
    main()
