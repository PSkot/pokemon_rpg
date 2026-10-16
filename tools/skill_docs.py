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

from game.mechanics.moves import MOVES  # noqa: E402
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
    lines = [f"## The {_name(tree.species[0])} line", "", f"Stages: {_stages(tree)}.", ""]
    stage_name = lambda s: _name(tree.species[s])  # noqa: E731
    lines += ["| Skill | Kind | Lv | Parent | Stage | Effect | Ranks |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for s in tree.skills.values():
        if s.kind == "modifier":
            continue
        effect = s.text[0]
        later = [f"R{r}: {t}" for r, t in enumerate(s.text[1:], start=2)]
        if later:
            effect += " " + " ".join(later)
        kind = "Basic attack" if s is tree.basic else "Base attack" if s.kind == "base" else "Move"
        parent = tree.skills[s.parent].name if s.parent else "–"
        ranks = "1" if s.max_rank == 1 else f"1–{s.max_rank}"
        lines.append(f"| {s.name} | {kind} | {s.level or '–'} | {parent} | {stage_name(s.stage)} | {effect} | {ranks} |")
    mods = [s for s in tree.skills.values() if s.kind == "modifier"]
    if mods:
        lines += ["", "| Modifier | Changes | Lv | Stage | Per rank |", "| --- | --- | --- | --- | --- |"]
        for s in mods:
            per_rank = " / ".join(s.text) if s.max_rank > 1 else s.text[0]
            lines.append(f"| {s.name} | {tree.skills[s.move].name} | {s.level} | {stage_name(s.stage)} | {per_rank} |")
    return "\n".join(lines)


def main() -> None:
    assert all(s.move in MOVES for t in TREES.values() for s in t.skills.values() if s.kind != "modifier")
    text = DOC.read_text(encoding="utf-8")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    body = "\n\n---\n\n".join(_section(t) for t in TREES.values())
    DOC.write_text(f"{before}{START}\n\n{body}\n\n{END}{after}", encoding="utf-8")
    print(f"Wrote {len(TREES)} trees to {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
