"""Regenerate the talent tables in docs/talents.md from the code
(game/mechanics/talents.py): each line's moves by level and its tiers.

    python tools/talent_docs.py

Rewrites everything after the "<!-- generated -->" line.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game.mechanics.pokemon import SPECIES  # noqa: E402
from game.mechanics.talents import DEEP, TIER_LEVELS, TREES  # noqa: E402

DOC = os.path.join(os.path.dirname(__file__), "..", "docs", "talents.md")
MARK = "<!-- generated -->"


def _name(key: str) -> str:
    return SPECIES[key].name if key in SPECIES else key.capitalize()


def _pool(pool: str) -> str:
    if pool == "own":
        return "**own**"
    kind, _, what = pool.partition(":")
    return what if kind == "move" else pool.capitalize()


def tables() -> str:
    out = []
    for tree in TREES.values():
        if not tree.tiers:
            continue
        out.append(f"### {' → '.join(_name(s) for s in tree.species)}\n")
        moves = []
        for lm in tree.moves:
            stage = f" ({_name(tree.species[lm.stage])})" if lm.stage else ""
            moves.append(f"{lm.name} {lm.level}{stage}" if lm.level else lm.name)
        out.append("Moves: " + ", ".join(moves) + ".\n")
        out.append("Paths: " + "; ".join(f"**{p.name}** ({p.blurb[0].lower() + p.blurb[1:].rstrip('.')})"
                                         for p in tree.paths) + ".\n")
        out.append("| Tier | Lv | " + " | ".join(p.name for p in tree.paths) + " |")
        out.append("| --- | --- | " + " | ".join("---" for _ in tree.paths) + " |")
        for i, row in enumerate(tree.tiers):
            need = f" *(needs {DEEP[i]})*" if i in DEEP else ""
            cells = [f"**{t.name}**{need}: {t.text} *({_pool(t.pool)})*" for t in row]
            out.append(f"| {i + 1} | {TIER_LEVELS[i]} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def main() -> None:
    with open(DOC, encoding="utf-8") as f:
        text = f.read()
    head = text.split(MARK)[0]
    with open(DOC, "w", encoding="utf-8") as f:
        f.write(head + MARK + "\n\n" + tables())


if __name__ == "__main__":
    main()
