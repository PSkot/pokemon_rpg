"""Write every skill tree into docs/skill_trees.md, from the code.

    python tools/skill_docs.py

Replaces what's between the `<!-- trees:start -->` and `<!-- trees:end -->`
markers with one section per evolution line (game/mechanics/skills.py),
so the tables always match the game. Run it after changing a tree.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from game.mechanics.moves import MOVES, describe  # noqa: E402
from game.mechanics.pokemon import EVOLUTIONS, SPECIES  # noqa: E402
from game.mechanics.skills import TREES, SkillTree  # noqa: E402

DOC = ROOT / "docs" / "skill_trees.md"
START, END = "<!-- trees:start -->", "<!-- trees:end -->"


def _name(key: str) -> str:
    species = SPECIES.get(key)
    return species.name if species else key.capitalize()


def _stages(tree: SkillTree) -> str:
    parts = []
    for i, key in enumerate(tree.species):
        notes = []
        if i:
            evolution = EVOLUTIONS.get(tree.species[i - 1])
            notes.append(f"Lv{evolution.level}" if evolution else "by stone")
        if key not in SPECIES:
            notes.append("not in the game yet")
        parts.append(_name(key) + (f" ({', '.join(notes)})" if notes else ""))
    return " → ".join(parts)


def _section(tree: SkillTree) -> str:
    lines = [f"## The {_name(tree.species[0])} line", "",
             f"Stages: {_stages(tree)}. Whole tree: {tree.cost} points.", ""]
    stage_name = lambda s: _name(tree.species[s])  # noqa: E731
    lines += ["| Move | Lv | Opened by | Stage | Effect | Buffs (points) |", "| --- | --- | --- | --- | --- | --- |"]
    for s in tree.moves:
        buffs = [b for b in tree.skills.values() if b.kind == "buff" and b.move == s.key]
        names = ", ".join(b.label for b in buffs)
        level = "free" if s.free else s.level
        parent = tree.skills[s.parents[0]].name if s.parents else "–"
        lines.append(f"| {s.name} | {level} | {parent} | {stage_name(s.stage)} | {describe(MOVES[s.move])} | "
                     f"{names} ({sum(b.max_rank for b in buffs)}) |")
    links = [s for s in tree.skills.values() if s.kind == "link"]
    if links:
        lines += ["", "| Link | Sets off | Lv | Stage | Chance per rank |", "| --- | --- | --- | --- | --- |"]
        for s in links:
            chances = " / ".join(f"{r['triggers'][0][2]}%" for r in s.ranks)
            lines.append(f"| {s.name} | {tree.skills[s.parents[0]].name} → {tree.skills[s.parents[1]].name} | "
                         f"{s.level} | {stage_name(s.stage)} | {chances} |")
    return "\n".join(lines)


def main() -> None:
    assert all(s.move in MOVES for t in TREES.values() for s in t.moves)
    text = DOC.read_text(encoding="utf-8")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    body = "\n\n---\n\n".join(_section(t) for t in TREES.values())
    DOC.write_text(f"{before}{START}\n\n{body}\n\n{END}{after}", encoding="utf-8")
    print(f"Wrote {len(TREES)} trees to {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
