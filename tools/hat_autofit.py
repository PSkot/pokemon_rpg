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
    "squirtle": (39, 34), "wartortle": (36, 29), "blastoise": (40, 21),
    "pidgey": (36, 34), "pidgeotto": (48, 25), "pidgeot": (47, 18),
    "spearow": (41, 35), "fearow": (43, 24),
    "nidoran_f": (39, 44), "nidoran_m": (39, 42), "rattata": (39, 38),
    "caterpie": (35, 34), "metapod": (35, 33), "weedle": (41, 40), "kakuna": (38, 29),
    "pikachu": (37, 33), "geodude": (33, 40), "onix": (50, 17), "diglett": (34, 33),
    "sandshrew": (39, 29), "ekans": (39, 26), "jigglypuff": (41, 38), "zubat": (40, 38),
    "paras": (36, 41), "clefairy": (39, 34),
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
