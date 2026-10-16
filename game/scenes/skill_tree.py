"""The skill tree screen (party screen → S): spend skill points, choose the
equipped moves, and reset points (in towns).

Left: the Pokémon's tree as an outline (each skill under its parent), with
rank pips and the equipped moves' slots. Right: the chosen skill's ranks,
requirements and what can be done with it.
"""

import pygame

from ..engine import ui
from ..engine.scene import Scene
from ..mechanics.pokemon import Monster
from ..mechanics.skills import MAX_EQUIPPED, RANK_DAMAGE, Skill
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

GREEN = (120, 230, 120)
RED = (240, 110, 100)
DIM = (96, 104, 140)
MODIFIER_COLOR = (200, 170, 255)

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_s, pygame.K_TAB)
KIND_NAMES = {"base": "Base attack", "move": "Move", "modifier": "Modifier"}


def _outline(skills: dict[str, Skill]) -> list[tuple[Skill, int, tuple[bool, ...]]]:
    """The tree in outline order: (skill, depth, whether each level of its
    ancestry, itself last, is the last child there). Modifiers come before
    a move's follow-up moves."""
    children: dict[str, list[Skill]] = {}
    for s in skills.values():
        children.setdefault(s.parent, []).append(s)
    for kids in children.values():
        kids.sort(key=lambda s: s.kind != "modifier")
    rows = []

    def walk(key: str, depth: int, lasts: tuple[bool, ...]) -> None:
        kids = children.get(key, [])
        for i, s in enumerate(kids):
            here = lasts + (i == len(kids) - 1,)
            rows.append((s, depth, here))
            walk(s.key, depth + 1, here)

    walk("", 0, ())
    return rows


class SkillTreeScene(Scene):
    def __init__(self, return_to: Scene, party: list[Monster], member: int, can_reset: bool):
        self.return_to = return_to
        self.party = party
        self.member = member
        self.can_reset = can_reset
        self.row = 0
        self.top = 0
        self.asking = False  # "reset all points?"
        self.message = ""

    @property
    def monster(self) -> Monster:
        return self.party[self.member]

    @property
    def rows(self):
        return _outline(self.monster.tree.skills)

    @property
    def skill(self) -> Skill:
        return self.rows[self.row][0]

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
            self.row = (self.row + (1 if key == pygame.K_DOWN else -1)) % len(self.rows)
            self.top = min(self.row, max(self.top, self.row - VISIBLE + 1))
            self.message = ""
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.member = (self.member + (1 if key == pygame.K_RIGHT else -1)) % len(self.party)
            self.row = self.top = 0
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
        if skill.kind == "modifier":
            return "Modifiers work on their move by themselves."
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
        """"learned", "open" (can be learned now) or "locked"."""
        if self.monster.skills.get(skill.key):
            return "learned"
        return "locked" if self.monster.why_not(skill.key) else "open"

    def _marker_color(self, skill: Skill):
        if skill.kind == "modifier":
            return MODIFIER_COLOR
        move = self.monster.tree.effective_move(self.monster.skills, skill.key)
        return COLORS.get(move.type, (168, 168, 120))

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
            state, color = self._state(skill), self._marker_color(skill)
            marker = pygame.Rect(x, y - 3, 7, 7)
            if skill.kind == "modifier":
                points = [(marker.centerx, marker.top), (marker.right, marker.centery),
                          (marker.centerx, marker.bottom), (marker.left, marker.centery)]
                pygame.draw.polygon(canvas, color if state == "learned" else DIM, points, 0 if state == "learned" else 1)
            else:
                pygame.draw.rect(canvas, color if state == "learned" else DIM, marker, 0 if state == "learned" else 1)
            # Rank pips at the right.
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
        move = m.tree.effective_move(m.skills, self.skill.key) if self.skill.kind != "modifier" else None
        if move and move.type:
            ui.badge(canvas, BADGE_POS, COLORS[move.type])

    def draw_overlay(self, window: pygame.Surface) -> None:
        m, tree = self.monster, self.monster.tree
        # Header: who, points, equipped moves.
        ui.text(window, f"{m.name}   Lv{m.level}", (HEADER.x + 12, HEADER.y + 6), ui.YELLOW)
        points = m.skill_points
        ui.text(window, f"Skill points: {points}", (HEADER.right - 12, HEADER.y + 6), GREEN if points else ui.GREY,
                align="right")
        slots = [f"{i + 2} {m.tree.skills[k].name}" for i, k in enumerate(m.equipped)]
        slots += [f"{i + 2} -" for i in range(len(m.equipped), MAX_EQUIPPED)]
        ui.text(window, "   ".join([f"Fight: {tree.basic.name}"] + slots), (HEADER.x + 12, HEADER.y + 24),
                ui.GREY, size=20)
        # The outline.
        ui.text(window, "Skill tree", (TREE_WINDOW.x + 12, TREE_WINDOW.y + 6), ui.GREY, size=20)
        for i, (skill, depth, _) in enumerate(self.rows):
            if not self.top <= i < self.top + VISIBLE:
                continue
            state = self._state(skill)
            color = (ui.YELLOW if i == self.row else ui.WHITE if state == "learned"
                     else GREEN if state == "open" else ui.GREY)
            x = TREE_WINDOW.x + 22 + depth * INDENT + 11
            ui.text(window, skill.name, (x, self._row_y(i)), color, size=22)
            slot = (m.equipped.index(skill.key) + 2 if skill.key in m.equipped
                    else "F" if skill.key == tree.basic.key else None)
            if slot is not None:
                pips = skill.max_rank * (PIP + 2)
                ui.text(window, str(slot), (TREE_WINDOW.right - 18 - pips, self._row_y(i) + 1), ui.YELLOW, size=18,
                        align="right")
        self._draw_info(window)
        hints = ("Up/Down: skill   Left/Right: Pokémon   Enter: learn / rank up   E: equip   "
                 f"R: reset{'' if self.can_reset else ' (towns)'}   S: back")
        ui.text(window, hints, (TREE_WINDOW.x + 12, TREE_WINDOW.bottom - PAD - 7), ui.GREY, size=16)

    def _draw_info(self, window: pygame.Surface) -> None:
        m, tree, skill = self.monster, self.monster.tree, self.skill
        x, right = INFO_WINDOW.x + 12, INFO_WINDOW.right - 12
        y = INFO_WINDOW.y + PAD
        rank = m.skills.get(skill.key, 0)
        ui.text(window, skill.name, (x, y), ui.YELLOW)
        ui.text(window, KIND_NAMES[skill.kind], (right, y + 2), ui.GREY, size=22, align="right")
        y += 20
        if skill.kind == "modifier":
            ui.text(window, f"Changes {tree.skills[skill.move].name}", (x, y), MODIFIER_COLOR, size=22)
        else:
            move = tree.effective_move(m.skills, skill.key)
            if move.type:
                ui.badge_text(window, type_name(move.type), BADGE_POS)
            if move.halve:
                ui.text(window, "Takes half the target's HP", (x, y), size=22)
            elif move.damaging:
                now = round(move.power * (1 + RANK_DAMAGE * (max(rank, 1) - 1)))
                text = f"Power {now}"
                if rank and rank < skill.max_rank:
                    text += f"  ->  {round(move.power * (1 + RANK_DAMAGE * rank))} at rank {rank + 1}"
                ui.text(window, text, (x, y), size=22)
            else:
                ui.text(window, "Status move", (x, y), size=22)
        y += 18
        ui.text(window, f"Rank {rank}/{skill.max_rank}", (x, y), ui.WHITE if rank else ui.GREY, size=22)
        y += 18
        for r in range(1, skill.max_rank + 1):  # what each rank does
            if r - 1 < len(skill.text):
                line = skill.text[r - 1]
            elif tree.skills[skill.key].kind != "modifier":
                line = f"+{round(RANK_DAMAGE * 100 * (r - 1))}% damage."
            else:
                continue
            color = GREEN if r <= rank else ui.WHITE if r == rank + 1 else ui.GREY
            ui.text(window, f"R{r}", (x, y), color, size=20)
            parts = _wrap(line, 54)
            for i, part in enumerate(parts):
                ui.text(window, part, (x + 22, y + i * 12), color, size=20)
            y += 12 * len(parts) + 2
        y += 4
        # Requirements.
        stage_name = tree.species[skill.stage].capitalize()
        checks = [(f"Level {skill.level}", m.level >= skill.level) if skill.level else None,
                  (f"After {tree.skills[skill.parent].name}", bool(m.skills.get(skill.parent))) if skill.parent else None,
                  (f"{stage_name} or later", m.species.stage >= skill.stage) if skill.stage else None]
        checks = [c for c in checks if c]
        if checks:
            ui.text(window, "Needs:", (x, y), ui.GREY, size=20)
            cx = x + 40
            for label, ok in checks:
                ui.text(window, label, (cx, y), GREEN if ok else RED, size=20)
                cx += ui.font(20).size(label)[0] / 2 + 14
            y += 16
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
        if skill.kind == "modifier":
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
