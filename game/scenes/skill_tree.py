"""The skill tree screen (party screen → S): spend skill points, choose the
equipped moves, and reset points (in towns).

Left: the Pokémon's tree as a map of nodes, laid out left to right: each
skill sits right of its first parent (moves as circles in their type's
colour, buffs as diamonds, links as small orange nodes, with a line to
their second move too). Learned paths light up. The view pans to follow
the cursor; the arrow keys go to the nearest node that way. Right: the
chosen skill: what it does, its ranks, requirements and what can be done.
"""

import math

import pygame

from .. import settings
from ..engine import ui
from ..engine.scene import Scene
from ..mechanics.moves import describe
from ..mechanics.pokemon import Monster
from ..mechanics.skills import MAX_EQUIPPED, Skill, SkillTree
from ..mechanics.type_chart import COLORS
from ..mechanics.type_chart import name as type_name

PAD = 9
HEADER = pygame.Rect(6, 6, 628, 40)
TREE_WINDOW = pygame.Rect(6, HEADER.bottom + 6, 392, 360 - HEADER.bottom - 12)
INFO_WINDOW = pygame.Rect(TREE_WINDOW.right + 6, TREE_WINDOW.y, 634 - TREE_WINDOW.right - 6, TREE_WINDOW.h)
VIEW = TREE_WINDOW.inflate(-8, -24).move(0, -6)  # where the nodes are drawn (room for the hints)
BADGE_POS = (INFO_WINDOW.right - 12 - ui.BADGE_SIZE[0], INFO_WINDOW.y + PAD + 19)  # the move's type
WRAP = 40  # characters per line in the info window

COL = 84       # px between a node and the ones right of it
ROW = 19       # px between rows of leaves
ROOT_GAP = 10  # extra px between the trees of two free moves
MOVE_R, LINK_R, BUFF_R = 7, 4, 5  # node sizes
PAN_SPEED = 10.0  # how fast the view catches up with the cursor (per second)

GREEN = (120, 230, 120)
RED = (240, 110, 100)
DIM = (96, 104, 140)
UNLEARNED = (30, 36, 84)  # a node's fill until it's learned
EDGE_LIT = (210, 210, 230)
BUFF_COLOR = (200, 170, 255)
LINK_COLOR = (255, 200, 120)

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_s, pygame.K_TAB)
DIRECTIONS = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}


def layout(tree: SkillTree) -> dict[str, tuple[float, float]]:
    """Each skill's (x, y) in the map: a tidy tree, left to right. A skill
    sits right of its first parent; leaves take a row each, in order, and
    a parent is centred on its children. Under a move, its buffs and links
    come before the moves it opens."""
    children: dict[str, list[Skill]] = {}
    for s in tree.skills.values():
        children.setdefault(s.parents[0] if s.parents else "", []).append(s)
    for kids in children.values():
        kids.sort(key=lambda s: ("buff", "link", "move").index(s.kind))
    spots: dict[str, tuple[float, float]] = {}
    next_row = 0.0

    def place(skill: Skill, depth: int) -> float:
        nonlocal next_row
        kids = children.get(skill.key, [])
        if kids:
            rows = [place(k, depth + 1) for k in kids]
            y = (rows[0] + rows[-1]) / 2
        else:
            y, next_row = next_row, next_row + ROW
        spots[skill.key] = (depth * COL, y)
        return y

    for root in children.get("", []):
        place(root, 0)
        next_row += ROOT_GAP
    return spots


class SkillTreeScene(Scene):
    touch_keys = ((pygame.K_e, "Equip"), (pygame.K_r, "Reset"), (pygame.K_w, "Next"))

    def __init__(self, return_to: Scene, party: list[Monster], member: int, can_reset: bool):
        self.return_to = return_to
        self.party = party
        self.member = member
        self.can_reset = can_reset
        self.asking = False  # "reset all points?"
        self.message = ""
        self.t = 0.0
        self._pick_member(member)

    def _pick_member(self, member: int) -> None:
        self.member = member
        self.spots = layout(self.monster.tree)
        self.cursor = self.monster.tree.basic.key  # the chosen skill's key
        self.camera = list(self._camera_goal())
        self.message = ""

    @property
    def monster(self) -> Monster:
        return self.party[self.member]

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
        if key in DIRECTIONS:
            self.cursor = self._nearest(*DIRECTIONS[key]) or self.cursor
            self.message = ""
        elif key in (pygame.K_q, pygame.K_w):
            self._pick_member((self.member + (1 if key == pygame.K_w else -1)) % len(self.party))
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

    def _nearest(self, dx: int, dy: int) -> str | None:
        """The closest node in direction (dx, dy) from the cursor: ahead of
        it, the distance across counting double."""
        cx, cy = self.spots[self.cursor]
        best, best_score = None, math.inf
        for key, (x, y) in self.spots.items():
            ahead = (x - cx) * dx + (y - cy) * dy
            across = abs((x - cx) * dy) + abs((y - cy) * dx)
            if ahead <= 0 or across > ahead * 3:
                continue
            score = ahead + across * 2
            if score < best_score:
                best, best_score = key, score
        return best

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

    # ---------------------------------------------------------------- camera

    def _camera_goal(self) -> tuple[float, float]:
        """The view's top-left in map px, with the cursor a third in from the
        left (or its move at the left edge, if that's further left) and in
        the middle, kept within the map."""
        x, y = self.spots[self.cursor]
        owner_x = self.spots[self.monster.tree.owner(self.cursor)][0]
        xs, ys = [p[0] for p in self.spots.values()], [p[1] for p in self.spots.values()]
        left = min(x - VIEW.w / 3, owner_x - 20)
        left = min(max(left, min(xs) - 20), max(min(xs) - 20, max(xs) + 90 - VIEW.w))
        top = min(max(y - VIEW.h / 2, min(ys) - 14), max(min(ys) - 14, max(ys) + 14 - VIEW.h))
        return left, top

    def update(self, dt: float) -> None:
        self.t += dt
        goal = self._camera_goal()
        step = min(1.0, dt * PAN_SPEED)
        self.camera = [c + (g - c) * step for c, g in zip(self.camera, goal)]

    def _screen(self, key: str) -> tuple[int, int]:
        """Where a node is on the canvas."""
        x, y = self.spots[key]
        return round(VIEW.x + x - self.camera[0]), round(VIEW.y + y - self.camera[1])

    # ------------------------------------------------------------------ draw

    def _state(self, skill: Skill) -> str:
        """"learned", "open" (can be learned or ranked up now) or "locked"."""
        m = self.monster
        rank, reason = m.skills.get(skill.key, 0), m.why_not(skill.key)
        if rank and (rank >= skill.max_rank or reason):
            return "learned"
        return "locked" if reason else "open"

    def _color(self, skill: Skill):
        if skill.kind == "move":
            return COLORS.get(self.monster.tree.effective_move(self.monster.skills, skill.key).type, (168, 168, 120))
        return BUFF_COLOR if skill.kind == "buff" else LINK_COLOR

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill(ui.SHADOW)
        for rect in (HEADER, TREE_WINDOW, INFO_WINDOW):
            ui.window_box(canvas, rect)
        m, tree = self.monster, self.monster.tree
        view = canvas.subsurface(VIEW)
        shift = (-VIEW.x, -VIEW.y)
        learned = lambda key: bool(m.skills.get(key))  # noqa: E731
        # Edges: an elbow from each skill's first parent; a link's second
        # parent gets a straight line.
        for s in tree.skills.values():
            if not s.parents:
                continue
            (px, py), (x, y) = self._screen(s.parents[0]), self._screen(s.key)
            color = EDGE_LIT if learned(s.key) else GREEN if self._state(s) == "open" else DIM
            mid = px + COL // 2
            points = [(px, py), (mid, py), (mid, y), (x, y)]
            pygame.draw.lines(view, color, False, [(a + shift[0], b + shift[1]) for a, b in points])
            if s.kind == "link":
                (qx, qy) = self._screen(s.parents[1])
                _dashed(view, LINK_COLOR if learned(s.key) else DIM, (qx + shift[0], qy + shift[1]),
                        (x + shift[0], y + shift[1]))
        # Nodes.
        for s in tree.skills.values():
            x, y = self._screen(s.key)
            x, y = x + shift[0], y + shift[1]
            if not (-20 < x < VIEW.w + 20 and -20 < y < VIEW.h + 20):
                continue
            state, color = self._state(s), self._color(s)
            filled = state == "learned" or (s.kind != "move" and m.skills.get(s.key))
            edge = color if filled else GREEN if state == "open" else DIM
            fill = color if filled else UNLEARNED
            if s.kind == "move":
                pygame.draw.circle(view, ui.SHADOW, (x, y + 1), MOVE_R + 1)
                pygame.draw.circle(view, fill, (x, y), MOVE_R)
                pygame.draw.circle(view, ui.WHITE if filled else edge, (x, y), MOVE_R, 1)
            elif s.kind == "buff":
                r = BUFF_R
                diamond = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
                pygame.draw.polygon(view, fill, diamond)
                pygame.draw.polygon(view, edge, diamond, 1)
            else:
                pygame.draw.circle(view, fill, (x, y), LINK_R)
                pygame.draw.circle(view, edge, (x, y), LINK_R, 1)
        # The cursor: a pulsing ring.
        x, y = self._screen(self.cursor)
        r = (MOVE_R if self.skill.kind == "move" else BUFF_R) + 4 + round(math.sin(self.t * 6))
        pygame.draw.circle(view, ui.YELLOW, (x + shift[0], y + shift[1]), r, 1)
        move = tree.effective_move(m.skills, tree.owner(self.cursor))
        if move.type:
            ui.badge(canvas, BADGE_POS, COLORS[move.type])

    def draw_overlay(self, window: pygame.Surface) -> None:
        m, tree = self.monster, self.monster.tree
        # Header: who, points, equipped moves.
        ui.text(window, f"{m.name}   Lv{m.level}", (HEADER.x + 12, HEADER.y + 6), ui.YELLOW)
        points = m.skill_points
        ui.text(window, f"Skill points: {points}   (tree: {tree.spent(m.skills)}/{tree.cost})",
                (HEADER.right - 12, HEADER.y + 6), GREEN if points else ui.GREY, align="right", size=24)
        slots = [f"{i + 2} {tree.skills[k].name}" for i, k in enumerate(m.equipped)]
        slots += [f"{i + 2} -" for i in range(len(m.equipped), MAX_EQUIPPED)]
        ui.text(window, "   ".join([f"Fight: {tree.basic.name}"] + slots), (HEADER.x + 12, HEADER.y + 24),
                ui.GREY, size=20)
        # Labels, right of their nodes, clipped to the view.
        s = settings.SCALE
        window.set_clip(pygame.Rect(VIEW.x * s, VIEW.y * s, VIEW.w * s, VIEW.h * s))
        for skill in tree.skills.values():
            x, y = self._screen(skill.key)
            if not (VIEW.left - COL < x < VIEW.right and VIEW.top - 10 < y < VIEW.bottom + 10):
                continue
            state = self._state(skill)
            color = (ui.YELLOW if skill.key == self.cursor else ui.WHITE if state == "learned"
                     else GREEN if state == "open" else ui.GREY)
            label = skill.label
            if skill.kind != "move":
                label += f" {m.skills.get(skill.key, 0)}/{skill.max_rank}"
            elif skill.key == tree.basic.key:
                label += " [F]"
            elif skill.key in m.equipped:
                label += f" [{m.equipped.index(skill.key) + 2}]"
            size = 20 if skill.kind == "move" else 17
            r = MOVE_R if skill.kind == "move" else BUFF_R
            ui.text(window, label, (x + r + 2, y - (13 if skill.kind == "move" else 11)), color, size=size)
        window.set_clip(None)
        self._draw_info(window)
        ui.text(window, f"Arrows: move   Enter: learn   E: equip   R: reset{'' if self.can_reset else ' (towns)'}"
                        f"   Q/W: Pokémon   S: back",
                (TREE_WINDOW.x + 10, TREE_WINDOW.bottom - PAD - 6), ui.GREY, size=16)

    def _draw_info(self, window: pygame.Surface) -> None:
        m, tree, skill = self.monster, self.monster.tree, self.skill
        x, right = INFO_WINDOW.x + 10, INFO_WINDOW.right - 10
        y = INFO_WINDOW.y + PAD
        rank = m.skills.get(skill.key, 0)
        owner = tree.skills[tree.owner(skill.key)]
        move = tree.effective_move(m.skills, owner.key)
        ui.text(window, skill.name, (x, y), ui.YELLOW, size=24)
        y += 19
        kind = ("Basic attack" if skill.key == tree.basic.key else "Move" if skill.kind == "move"
                else "Buff" if skill.kind == "buff" else "Link")
        ui.text(window, kind, (x, y + 1), ui.GREY, size=20)
        if move.type:
            ui.badge_text(window, type_name(move.type), BADGE_POS)
        y += 16
        if skill.kind == "move":
            ui.text(window, "Learned" if rank else "1 point", (x, y), GREEN if rank else ui.GREY, size=20)
            y += 15
        else:
            what = (f"Changes {owner.name}" if skill.kind == "buff"
                    else f"{owner.name} sets off {tree.skills[skill.parents[1]].name}")
            for part in _wrap(what, WRAP - 4):
                ui.text(window, part, (x, y), BUFF_COLOR if skill.kind == "buff" else LINK_COLOR, size=20)
                y += 13
            ui.text(window, f"Rank {rank}/{skill.max_rank}", (x, y + 1), ui.WHITE if rank else ui.GREY, size=20)
            y += 16
            for r in range(1, skill.max_rank + 1):  # what each rank does
                color = GREEN if r <= rank else ui.WHITE if r == rank + 1 else ui.GREY
                ui.text(window, f"R{r}", (x, y), color, size=18)
                parts = _wrap(skill.text[r - 1], WRAP - 5)
                for i, part in enumerate(parts):
                    ui.text(window, part, (x + 18, y + i * 11), color, size=18)
                y += 11 * len(parts) + 1
        y += 4
        # The move as it is now, with what's learned.
        ui.text(window, f"{owner.name} now:" if skill.kind != "move" else "What it does:", (x, y), ui.GREY, size=18)
        y += 12
        for part in _wrap(describe(move), WRAP)[:8]:
            ui.text(window, part, (x, y), ui.WHITE, size=18)
            y += 11
        y += 4
        # Requirements.
        checks = []
        if skill.level:
            checks.append((f"Lv{skill.level}", m.level >= skill.level))
        checks += [(tree.skills[p].name, bool(m.skills.get(p))) for p in skill.parents]
        if skill.stage:
            checks.append((tree.species[skill.stage].capitalize(), m.species.stage >= skill.stage))
        if checks:
            ui.text(window, "Needs:", (x, y), ui.GREY, size=18)
            cx = x + 36
            for label, ok in checks:
                width = ui.font(18).size(label)[0] / settings.SCALE
                if cx + width > right:
                    cx, y = x + 36, y + 11
                ui.text(window, label, (cx, y), GREEN if ok else RED, size=18)
                cx += width + 8
        # What can be done.
        if self.asking:
            line, color = "Reset all points? Enter: yes  X: no", ui.YELLOW
        elif self.message:
            line, color = self.message, ui.YELLOW
        else:
            reason = m.why_not(skill.key)
            line, color = ((("Enter: learn (1 point)" if not rank else "Enter: rank up (1 point)"), GREEN)
                           if not reason else (reason, ui.GREY))
        for i, part in enumerate(_wrap(line, WRAP)[:2]):
            ui.text(window, part, (x, INFO_WINDOW.bottom - PAD - 38 + i * 12), color, size=20)
        if skill.kind != "move":
            equip = "Works on its move by itself."
        elif skill.key == tree.basic.key:
            equip = "The basic attack: used by Fight."
        elif skill.key in m.equipped:
            equip = f"Equipped (key {m.equipped.index(skill.key) + 2}).  E: unequip"
        elif rank:
            equip = "Not equipped.  E: equip"
        else:
            equip = ""
        ui.text(window, equip, (x, INFO_WINDOW.bottom - PAD - 11), ui.GREY, size=18)


def _dashed(surface: pygame.Surface, color, a: tuple[int, int], b: tuple[int, int], dash: int = 4) -> None:
    length = math.dist(a, b)
    for i in range(0, int(length), dash * 2):
        t0, t1 = i / length, min(1.0, (i + dash) / length)
        pygame.draw.line(surface, color, (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                         (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1))


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
