"""The skill tree screen (party screen → S): spend skill points, choose the
equipped moves, and reset points (in towns).

Left: the Pokémon's tree as an outline: moves along their paths (each
under the move that opens it), and under the move the cursor is on, its
buffs and links (the other moves show how much of their branch is
learned). Right: the chosen skill: what it does, its ranks, requirements
and what can be done with it.
"""

import pygame

from ..engine import ui
from ..engine.scene import Scene
from ..mechanics.moves import describe
from ..mechanics.pokemon import Monster
from ..mechanics.skills import MAX_EQUIPPED, Skill, SkillTree
from ..mechanics.type_chart import COLORS
from ..mechanics.type_chart import name as type_name

PAD = 9
ROW_H = 15
INDENT = 12
HEADER = pygame.Rect(6, 6, 628, 40)
TREE_WINDOW = pygame.Rect(6, HEADER.bottom + 6, 300, 360 - HEADER.bottom - 12)
INFO_WINDOW = pygame.Rect(TREE_WINDOW.right + 6, TREE_WINDOW.y, 634 - TREE_WINDOW.right - 6, TREE_WINDOW.h)
VISIBLE = (TREE_WINDOW.h - PAD * 2 - 14 - 12) // ROW_H  # rows that fit above the key hints; it scrolls
PIP = 5
BADGE_POS = (INFO_WINDOW.right - 12 - ui.BADGE_SIZE[0], INFO_WINDOW.y + PAD + 19)  # the move's type
WRAP = 56  # characters per line in the info window

GREEN = (120, 230, 120)
RED = (240, 110, 100)
DIM = (96, 104, 140)
BUFF_COLOR = (200, 170, 255)
LINK_COLOR = (255, 200, 120)

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_s, pygame.K_TAB)


def outline(tree: SkillTree, expanded: str) -> list[tuple[Skill, int, tuple[bool, ...]]]:
    """The tree in outline order: (skill, depth, whether each level of its
    ancestry, itself last, is the last child there). Every skill hangs
    under its first parent; only the `expanded` move shows its buffs and
    links (before the moves it opens)."""
    children: dict[str, list[Skill]] = {}
    for s in tree.skills.values():
        children.setdefault(s.parents[0] if s.parents else "", []).append(s)
    for kids in children.values():
        kids.sort(key=lambda s: s.kind == "move")
    rows = []

    def walk(key: str, depth: int, lasts: tuple[bool, ...]) -> None:
        kids = [s for s in children.get(key, []) if s.kind == "move" or tree.owner(s.key) == expanded]
        for i, s in enumerate(kids):
            here = lasts + (i == len(kids) - 1,)
            rows.append((s, depth, here))
            walk(s.key, depth + 1, here)

    walk("", 0, ())
    return rows


class SkillTreeScene(Scene):
    touch_keys = ((pygame.K_e, "Equip"), (pygame.K_r, "Reset"))

    def __init__(self, return_to: Scene, party: list[Monster], member: int, can_reset: bool):
        self.return_to = return_to
        self.party = party
        self.member = member
        self.can_reset = can_reset
        self.cursor = self.monster.tree.basic.key  # the chosen skill's key
        self.top = 0
        self.asking = False  # "reset all points?"
        self.message = ""

    @property
    def monster(self) -> Monster:
        return self.party[self.member]

    @property
    def rows(self):
        tree = self.monster.tree
        return outline(tree, tree.owner(self.cursor))

    @property
    def row(self) -> int:
        return next(i for i, (s, _, _) in enumerate(self.rows) if s.key == self.cursor)

    @property
    def skill(self) -> Skill:
        return self.monster.tree.skills[self.cursor]

    def save_point(self):
        return self.return_to.save_point()

    # ----------------------------------------------------------------- input

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key, m = event.key, self.monster
        if self.asking:
            if key in CONFIRM_KEYS:
                m.reset_skills()
                self.message = "All skill points are back."
            self.asking = False
            return
        if key in (pygame.K_UP, pygame.K_DOWN):
            rows = self.rows
            self.cursor = rows[(self.row + (1 if key == pygame.K_DOWN else -1)) % len(rows)][0].key
            row = self.row  # (opening another move's branch moves the rows)
            self.top = max(0, min(row, max(self.top, row - VISIBLE + 1), len(self.rows) - VISIBLE))
            self.message = ""
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.member = (self.member + (1 if key == pygame.K_RIGHT else -1)) % len(self.party)
            self.cursor, self.top = self.monster.tree.basic.key, 0
            self.message = ""
        elif key in CONFIRM_KEYS:
            skill = self.skill
            reason = m.why_not(skill.key)
            if reason:
                self.message = reason
            else:
                m.rank_up(skill.key)
                rank = m.skills[skill.key]
                self.message = f"Learned {skill.name}!" if rank == 1 else f"{skill.name} is now rank {rank}."
        elif key == pygame.K_e:
            self.message = self._toggle_equip()
        elif key == pygame.K_r:
            if self.can_reset:
                self.asking = True
            else:
                self.message = "Skill points can only be reset in towns."
        elif key in BACK_KEYS:
            self.return_to.member = self.member
            self.next_scene = self.return_to

    def _toggle_equip(self) -> str:
        m, skill = self.monster, self.skill
        if skill.kind != "move":
            return f"{skill.name} works on its move by itself."
        if skill.key == m.tree.basic.key:
            return f"{skill.name} is the basic attack (Fight)."
        if not m.skills.get(skill.key):
            return f"Learn {skill.name} first."
        if skill.key in m.equipped:
            m.equipped.remove(skill.key)
            return f"{skill.name} unequipped."
        if len(m.equipped) >= MAX_EQUIPPED:
            return f"All {MAX_EQUIPPED} slots are full: unequip a move first."
        m.equipped.append(skill.key)
        return f"{skill.name} equipped."

    # ------------------------------------------------------------------ draw

    def _row_y(self, i: int) -> int:
        return TREE_WINDOW.y + PAD + 14 + (i - self.top) * ROW_H

    def _state(self, skill: Skill) -> str:
        """"learned", "open" (can be learned or ranked up now) or "locked"."""
        m = self.monster
        rank = m.skills.get(skill.key, 0)
        if rank and (rank >= skill.max_rank or m.why_not(skill.key)):
            return "learned"
        return "locked" if m.why_not(skill.key) else "open"

    def _branch(self, move_key: str) -> tuple[int, int]:
        """(points spent, points it can take) in a move's buffs and links."""
        m, tree = self.monster, self.monster.tree
        nodes = [s for s in tree.skills.values() if s.kind != "move" and s.move == move_key]
        return sum(m.skills.get(s.key, 0) for s in nodes), sum(s.max_rank for s in nodes)

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(ui.SHADOW)
        for rect in (HEADER, TREE_WINDOW, INFO_WINDOW):
            ui.window_box(canvas, rect)
        m, rows = self.monster, self.rows
        for i, (skill, depth, lasts) in enumerate(rows):
            if not self.top <= i < self.top + VISIBLE:
                continue
            y = self._row_y(i) + 6  # the row's middle
            x = TREE_WINDOW.x + 22 + depth * INDENT
            # Connectors: ancestors that have more children below, then this one's branch.
            for d, last in enumerate(lasts[:-1]):
                if not last:
                    lx = TREE_WINDOW.x + 22 + d * INDENT + 3
                    pygame.draw.line(canvas, DIM, (lx, y - 8), (lx, y + 7))
            if depth:
                lx = x - INDENT + 3
                pygame.draw.line(canvas, DIM, (lx, y - 8), (lx, y if lasts[-1] else y + 7))
                pygame.draw.line(canvas, DIM, (lx, y), (x - 1, y))
            learned = bool(m.skills.get(skill.key))
            marker = pygame.Rect(x, y - 3, 7, 7)
            if skill.kind == "move":
                move = m.tree.effective_move(m.skills, skill.key)
                color = COLORS.get(move.type, (168, 168, 120)) if learned else DIM
                pygame.draw.rect(canvas, color, marker, 0 if learned else 1)
            elif skill.kind == "buff":
                points = [(marker.centerx, marker.top), (marker.right, marker.centery),
                          (marker.centerx, marker.bottom), (marker.left, marker.centery)]
                pygame.draw.polygon(canvas, BUFF_COLOR if learned else DIM, points, 0 if learned else 1)
            else:
                pygame.draw.circle(canvas, LINK_COLOR if learned else DIM, marker.center, 3, 0 if learned else 1)
            if skill.kind != "move":  # rank pips at the right
                rank = m.skills.get(skill.key, 0)
                for p in range(skill.max_rank):
                    pip = pygame.Rect(TREE_WINDOW.right - 12 - (skill.max_rank - p) * (PIP + 2), y - 2, PIP, PIP)
                    pygame.draw.rect(canvas, ui.YELLOW if p < rank else DIM, pip, 0 if p < rank else 1)
        ui.cursor(canvas, TREE_WINDOW.x + 16, self._row_y(self.row) + 6)
        x = TREE_WINDOW.right - 10  # scroll arrows
        if self.top > 0:
            pygame.draw.polygon(canvas, ui.WHITE, [(x - 3, TREE_WINDOW.y + 9), (x + 3, TREE_WINDOW.y + 9),
                                                   (x, TREE_WINDOW.y + 5)])
        if self.top + VISIBLE < len(rows):
            y = TREE_WINDOW.bottom - 9
            pygame.draw.polygon(canvas, ui.WHITE, [(x - 3, y), (x + 3, y), (x, y + 4)])
        move = m.tree.effective_move(m.skills, m.tree.owner(self.cursor))
        if move.type:
            ui.badge(canvas, BADGE_POS, COLORS[move.type])

    def draw_overlay(self, window: pygame.Surface) -> None:
        m, tree = self.monster, self.monster.tree
        # Header: who, points, equipped moves.
        ui.text(window, f"{m.name}   Lv{m.level}", (HEADER.x + 12, HEADER.y + 6), ui.YELLOW)
        points = m.skill_points
        spent = tree.spent(m.skills)
        ui.text(window, f"Skill points: {points}   (tree: {spent}/{tree.cost})", (HEADER.right - 12, HEADER.y + 6),
                GREEN if points else ui.GREY, align="right", size=24)
        slots = [f"{i + 2} {m.tree.skills[k].name}" for i, k in enumerate(m.equipped)]
        slots += [f"{i + 2} -" for i in range(len(m.equipped), MAX_EQUIPPED)]
        ui.text(window, "   ".join([f"Fight: {tree.basic.name}"] + slots), (HEADER.x + 12, HEADER.y + 24),
                ui.GREY, size=20)
        # The outline.
        ui.text(window, "Skill tree", (TREE_WINDOW.x + 12, TREE_WINDOW.y + 6), ui.GREY, size=20)
        rows = self.rows
        for i, (skill, depth, _) in enumerate(rows):
            if not self.top <= i < self.top + VISIBLE:
                continue
            state = self._state(skill)
            color = (ui.YELLOW if skill.key == self.cursor else ui.WHITE if state == "learned"
                     else GREEN if state == "open" else ui.GREY)
            x = TREE_WINDOW.x + 22 + depth * INDENT + 11
            ui.text(window, skill.label, (x, self._row_y(i)), color, size=22)
            right = TREE_WINDOW.right - 12
            if skill.kind == "move":
                spent, room = self._branch(skill.key)
                if room:  # how much of its branch is learned
                    ui.text(window, f"{spent}/{room}", (right, self._row_y(i) + 1), GREEN if spent else DIM,
                            size=18, align="right")
                    right -= 26
                slot = (m.equipped.index(skill.key) + 2 if skill.key in m.equipped
                        else "F" if skill.key == tree.basic.key else None)
                if slot is not None:
                    ui.text(window, str(slot), (right, self._row_y(i) + 1), ui.YELLOW, size=18, align="right")
        self._draw_info(window)
        hints = ("Up/Down: skill   Left/Right: Pokémon   Enter: learn / rank up   E: equip   "
                 f"R: reset{'' if self.can_reset else ' (towns)'}   S: back")
        ui.text(window, hints, (TREE_WINDOW.x + 12, TREE_WINDOW.bottom - PAD - 7), ui.GREY, size=16)

    def _draw_info(self, window: pygame.Surface) -> None:
        m, tree, skill = self.monster, self.monster.tree, self.skill
        x, right = INFO_WINDOW.x + 12, INFO_WINDOW.right - 12
        y = INFO_WINDOW.y + PAD
        rank = m.skills.get(skill.key, 0)
        owner = tree.skills[tree.owner(skill.key)]
        move = tree.effective_move(m.skills, owner.key)
        ui.text(window, skill.name, (x, y), ui.YELLOW)
        kind = ("Basic attack" if skill.key == tree.basic.key else "Move" if skill.kind == "move"
                else "Buff" if skill.kind == "buff" else "Link")
        ui.text(window, kind, (right, y + 2), ui.GREY, size=22, align="right")
        if move.type:
            ui.badge_text(window, type_name(move.type), BADGE_POS)
        y += 20
        if skill.kind == "move":
            ui.text(window, "Learned" if rank else "1 point", (x, y), GREEN if rank else ui.GREY, size=22)
            y += 18
        else:
            what = (f"Changes {owner.name}" if skill.kind == "buff"
                    else f"{owner.name} sets off {tree.skills[skill.parents[1]].name}")
            ui.text(window, what, (x, y), BUFF_COLOR if skill.kind == "buff" else LINK_COLOR, size=22)
            y += 18
            ui.text(window, f"Rank {rank}/{skill.max_rank}", (x, y), ui.WHITE if rank else ui.GREY, size=22)
            y += 17
            for r in range(1, skill.max_rank + 1):  # what each rank does
                color = GREEN if r <= rank else ui.WHITE if r == rank + 1 else ui.GREY
                ui.text(window, f"R{r}", (x, y), color, size=20)
                parts = _wrap(skill.text[r - 1], WRAP - 4)
                for i, part in enumerate(parts):
                    ui.text(window, part, (x + 22, y + i * 12), color, size=20)
                y += 12 * len(parts) + 1
            y += 5
        # The move as it is now, with what's learned.
        ui.text(window, f"{owner.name} now:" if skill.kind != "move" else "What it does:", (x, y), ui.GREY, size=20)
        y += 13
        for part in _wrap(describe(move), WRAP)[:7]:
            ui.text(window, part, (x, y), ui.WHITE, size=20)
            y += 12
        y += 5
        # Requirements.
        checks = []
        if skill.level:
            checks.append((f"Lv{skill.level}", m.level >= skill.level))
        checks += [(tree.skills[p].name, bool(m.skills.get(p))) for p in skill.parents]
        if skill.stage:
            checks.append((f"{tree.species[skill.stage].capitalize()}", m.species.stage >= skill.stage))
        if checks:
            ui.text(window, "Needs:", (x, y), ui.GREY, size=20)
            cx = x + 40
            for label, ok in checks:
                width = ui.font(20).size(label)[0] / 2
                if cx + width > right:
                    cx, y = x + 40, y + 12
                ui.text(window, label, (cx, y), GREEN if ok else RED, size=20)
                cx += width + 12
        # What can be done.
        if self.asking:
            line, color = "Reset all skill points?   Enter: yes   X: no", ui.YELLOW
        elif self.message:
            line, color = self.message, ui.YELLOW
        else:
            reason = m.why_not(skill.key)
            if not reason:
                line, color = ("Enter: learn (1 point)" if not rank else "Enter: rank up (1 point)"), GREEN
            else:
                line, color = reason, ui.GREY
        ui.text(window, line, (x, INFO_WINDOW.bottom - PAD - 30), color, size=22)
        if skill.kind != "move":
            equip = "Works on its move by itself."
        elif skill.key == tree.basic.key:
            equip = "The basic attack: used by Fight."
        elif skill.key in m.equipped:
            equip = f"Equipped (key {m.equipped.index(skill.key) + 2}).   E: unequip"
        elif rank:
            equip = "Not equipped.   E: equip"
        else:
            equip = ""
        ui.text(window, equip, (x, INFO_WINDOW.bottom - PAD - 14), ui.GREY, size=20)


def _wrap(text: str, width: int) -> list[str]:
    """`text` split into lines of at most `width` characters, at spaces."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + [line] if line else lines
