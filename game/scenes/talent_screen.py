"""The talent screen (party screen → S): pick talents, choose the equipped
moves, and reset talents (in towns).

Left: the line's talents as a grid, a row per tier (its level on the left)
and a column per path; picked ones are filled in their path's colour and
joined by a line, the ones open now outlined green, locked ones grey. The
grid scrolls to keep the cursor in view. Arrows move the cursor; a tap
picks a cell, a second tap on it picks the talent. Right: the chosen
talent (what it does, where it comes from, what it needs), and the moves
the Pokémon knows, with the equipped ones' keys.

M opens the moves list (equip or unequip a known move: E or Enter), O
reorders the equipped moves (`MovesPanel`).
"""

import pygame

from .. import settings
from ..engine import ui
from ..engine.scene import Scene
from ..mechanics.moves import MOVES
from ..mechanics.pokemon import Monster
from ..mechanics.talents import DEEP, MAX_EQUIPPED, TIER_LEVELS, Talent
from .moves_panel import MovesPanel

PAD = 9
HEADER = pygame.Rect(6, 6, 628, 26)
GRID = pygame.Rect(6, HEADER.bottom + 6, 396, 360 - HEADER.bottom - 12)
INFO = pygame.Rect(GRID.right + 6, GRID.y, 634 - GRID.right - 6, GRID.h)
LEVEL_X = GRID.x + 10        # the tier's level
COLS_X = GRID.x + 52         # the first path's cells
CELL = (110, 28)             # a talent's cell
CELL_GAP = 4
ROW_H = 36                   # px per tier
HEAD_H = 22                  # the paths' names
VISIBLE = (GRID.h - HEAD_H - 26) // ROW_H  # tiers in view (the rest scroll)
WRAP = 34                    # characters per line in the info window

GREEN = (120, 230, 120)
RED = (240, 110, 100)
DIM = (70, 74, 110)
CELL_FILL = (28, 32, 72)
LOCKED_FILL = (22, 24, 52)
LINE = (210, 210, 230)

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)
BACK_KEYS = (pygame.K_x, pygame.K_BACKSPACE, pygame.K_s, pygame.K_TAB)


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


class MovesList:
    """The known moves: Up/Down choose, E or Enter equips or unequips one
    (with every slot full it asks which one it replaces), X closes."""

    RECT = pygame.Rect(40, 70, 330, 230)
    ROW_H = 19

    def __init__(self, monster: Monster):
        self.monster = monster
        self.keys = monster.known
        self.choice = 0
        self.replace: MovesPanel | None = None
        self.message = ""

    def handle_key(self, key: int) -> bool:
        """True when the list closes."""
        if self.replace:
            if self.replace.handle_key(key):
                self.message, self.replace = self.replace.message, None
            return False
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.keys)
            self.message = ""
        elif key in CONFIRM_KEYS + (pygame.K_e,):
            self.message = self._toggle(self.keys[self.choice])
        elif key in BACK_KEYS + (pygame.K_m,):
            return True
        return False

    def tap(self, pos: tuple[float, float]) -> None:
        if self.replace:
            return
        for i in range(len(self.keys)):
            if self._row(i).collidepoint(pos):
                if i == self.choice:
                    self.message = self._toggle(self.keys[i])
                self.choice = i

    def _toggle(self, key: str) -> str:
        m = self.monster
        name = m.tree.learned(key).name
        if key == m.tree.basic.key:
            return f"{name} is the basic attack (Fight)."
        if key in m.equipped:
            m.equipped.remove(key)
            return f"{name} unequipped: no longer used in battle."
        if len(m.equipped) >= MAX_EQUIPPED:
            self.replace = MovesPanel(m, replace_with=key)
            return ""
        m.equipped.append(key)
        return f"{name} equipped: used in battle (key {len(m.equipped) + 1})."

    def _row(self, i: int) -> pygame.Rect:
        return pygame.Rect(self.RECT.x + 8, self.RECT.y + 36 + i * self.ROW_H, self.RECT.w - 16, self.ROW_H)

    def draw(self, canvas: pygame.Surface) -> None:
        if self.replace:
            self.replace.draw(canvas)
            return
        ui.window_box(canvas, self.RECT)
        ui.cursor(canvas, self.RECT.x + 16, self._row(self.choice).centery)

    def draw_overlay(self, window: pygame.Surface) -> None:
        if self.replace:
            self.replace.draw_overlay(window)
            return
        r, m = self.RECT, self.monster
        ui.text(window, "Moves known", (r.x + 12, r.y + PAD), ui.YELLOW, size=22)
        for i, key in enumerate(self.keys):
            row = self._row(i)
            if key == m.tree.basic.key:
                slot, color = "F", ui.GREY
            elif key in m.equipped:
                slot, color = str(m.equipped.index(key) + 2), ui.WHITE
            else:
                slot, color = "-", ui.GREY
            ui.text(window, f"{slot}  {m.move(key).name}", (row.x + 14, row.y + 2), color, size=20)
        ui.text(window, self.message or "E / Enter: equip or unequip   X: close", (r.x + 12, r.bottom - PAD - 12),
                GREEN if self.message else ui.GREY, size=17)


class TalentScene(Scene):
    touch_keys = ((pygame.K_m, "Moves"), (pygame.K_o, "Reorder moves"), (pygame.K_r, "Reset"),
                  (pygame.K_w, "Next"))

    def __init__(self, return_to: Scene, party: list[Monster], member: int, can_reset: bool):
        self.return_to = return_to
        self.party = party
        self.can_reset = can_reset
        self.asking = False  # "reset all talents?"
        self.panel: MovesList | MovesPanel | None = None
        self.message = ""
        self.t = 0.0
        self._pick_member(member)

    def _pick_member(self, member: int) -> None:
        self.member = member
        m = self.monster
        open_ = m.tree.open_tiers(m.level)
        picked = m.tree.picks(m.talents)
        # Start on the first open tier without a pick (else the last open one).
        tier = next((t for t in range(open_) if t not in picked), max(0, open_ - 1))
        self.cursor = (tier, picked.get(tier, 0))
        self.top = max(0, min(tier - VISIBLE // 2, len(m.tree.tiers) - VISIBLE))
        self.message = ""

    @property
    def monster(self) -> Monster:
        return self.party[self.member]

    @property
    def talent(self) -> Talent | None:
        tiers = self.monster.tree.tiers
        return tiers[self.cursor[0]][self.cursor[1]] if tiers else None

    def save_point(self):
        return self.return_to.save_point()

    # ----------------------------------------------------------------- input

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key, m = event.key, self.monster
        if self.panel:
            if self.panel.handle_key(key):
                self.message, self.panel = self.panel.message, None
            return
        if self.asking:
            if key in CONFIRM_KEYS:
                m.reset_talents()
                self.message = "All talents taken back."
            self.asking = False
            return
        tiers = m.tree.tiers
        if key in (pygame.K_UP, pygame.K_DOWN) and tiers:
            tier = (self.cursor[0] + (1 if key == pygame.K_DOWN else -1)) % len(tiers)
            self._go(tier, self.cursor[1])
        elif key in (pygame.K_LEFT, pygame.K_RIGHT) and tiers:
            self._go(self.cursor[0], (self.cursor[1] + (1 if key == pygame.K_RIGHT else -1)) % len(m.tree.paths))
        elif key in (pygame.K_q, pygame.K_w):
            self._pick_member((self.member + (1 if key == pygame.K_w else -1)) % len(self.party))
        elif key in CONFIRM_KEYS and tiers:
            self._choose()
        elif key in (pygame.K_m, pygame.K_e):
            self.panel = MovesList(m)
        elif key == pygame.K_o:
            if m.equipped:
                self.panel = MovesPanel(m)
            else:
                self.message = "No moves equipped besides Fight."
        elif key == pygame.K_r:
            if not self.can_reset:
                self.message = "Talents can only be reset in towns."
            elif m.talents:
                self.asking = True
        elif key in BACK_KEYS:
            self.return_to.member = self.member
            self.next_scene = self.return_to

    def _go(self, tier: int, path: int) -> None:
        self.cursor = (tier, path)
        self.top = min(max(self.top, tier - VISIBLE + 1), tier)
        self.message = ""

    def _choose(self) -> None:
        m, (tier, path) = self.monster, self.cursor
        talent = self.talent
        if talent.key in m.talents:
            self.message = f"{talent.name} is picked."
            return
        reason = m.why_not(tier, path)
        if reason:
            self.message = reason
            return
        if not self.can_reset and m.tree.picks(m.talents).get(tier) is not None:
            self.message = "A tier's pick can only be changed in towns."
            return
        before = set(m.talents)
        m.pick(tier, path)
        lost = [m.tree.tiers[t][p].name for t, p in map(m.tree.tier_of, before - set(m.talents))
                if t != tier]
        self.message = f"Picked {talent.name}!" + (f" ({', '.join(lost)} no longer has what it needs.)"
                                                   if lost else "")

    def tap(self, pos: tuple[float, float], drag: bool) -> None:
        if drag or self.asking:
            return
        if isinstance(self.panel, MovesList):
            self.panel.tap(pos)
            return
        if self.panel:
            return
        for tier, path, rect in self._cells():
            if rect.collidepoint(pos):
                if (tier, path) == self.cursor:
                    self._choose()
                else:
                    self._go(tier, path)
                return

    def update(self, dt: float) -> None:
        self.t += dt

    # ------------------------------------------------------------------ draw

    def _cells(self):
        """(tier, path, rect) of each talent cell in view."""
        tree = self.monster.tree
        for tier in range(self.top, min(len(tree.tiers), self.top + VISIBLE)):
            y = GRID.y + HEAD_H + 6 + (tier - self.top) * ROW_H
            for path in range(len(tree.paths)):
                yield tier, path, pygame.Rect(COLS_X + path * (CELL[0] + CELL_GAP), y, *CELL)

    def _state(self, tier: int, path: int) -> str:
        m = self.monster
        talent = m.tree.tiers[tier][path]
        if talent.key in m.talents:
            return "picked"
        if m.level < TIER_LEVELS[tier]:
            return "locked"
        if m.tree.picks(m.talents).get(tier) is not None:
            return "other"  # the tier has a pick
        return "open" if not m.why_not(tier, path) else "locked"

    def draw(self, canvas: pygame.Surface) -> None:
        canvas.fill((14, 16, 40))
        for rect in (HEADER, GRID, INFO):
            ui.window_box(canvas, rect)
        m, tree = self.monster, self.monster.tree
        cells = list(self._cells())
        picked = tree.picks(m.talents)
        centres = {(t, p): r.center for t, p, r in cells}
        for t in range(self.top, self.top + VISIBLE - 1):  # lines joining picks in tiers next to each other
            if t in picked and t + 1 in picked and (t, picked[t]) in centres and (t + 1, picked[t + 1]) in centres:
                (ax, ay), (bx, by) = centres[(t, picked[t])], centres[(t + 1, picked[t + 1])]
                pygame.draw.line(canvas, LINE, (ax, ay + CELL[1] // 2), (bx, by - CELL[1] // 2))
        for tier, path, rect in cells:
            state, color = self._state(tier, path), tree.paths[path].color
            fill = color if state == "picked" else LOCKED_FILL if state == "locked" else CELL_FILL
            edge = {"picked": ui.WHITE, "open": GREEN, "other": (90, 100, 160), "locked": DIM}[state]
            pygame.draw.rect(canvas, fill, rect, border_radius=5)
            pygame.draw.rect(canvas, edge, rect, 1, border_radius=5)
            if (tier, path) == self.cursor and not self.panel:
                flash = ui.YELLOW if (self.t * 3) % 2 < 1.4 else ui.WHITE
                pygame.draw.rect(canvas, flash, rect.inflate(4, 4), 2, border_radius=7)
        if self.top > 0:
            _arrow(canvas, GRID.centerx + 26, GRID.y + HEAD_H + 2, -1)
        if self.top + VISIBLE < len(tree.tiers):
            _arrow(canvas, GRID.centerx + 26, GRID.y + HEAD_H + 6 + VISIBLE * ROW_H - 2, 1)
        if self.panel:
            self.panel.draw(canvas)
        if self.asking:
            ui.window_box(canvas, pygame.Rect(150, 150, 340, 50))

    def draw_overlay(self, window: pygame.Surface) -> None:
        m, tree = self.monster, self.monster.tree
        ui.text(window, f"{m.name}   Lv{m.level}   -   Talents", (HEADER.x + 12, HEADER.y + 6), ui.YELLOW, size=24)
        if tree.tiers:
            n = m.open_picks
            right = (f"{n} talent{'s' if n > 1 else ''} to pick" if n
                     else f"{len(tree.picks(m.talents))} of {len(tree.tiers)} tiers picked")
            ui.text(window, right, (HEADER.right - 12, HEADER.y + 7), GREEN if n else ui.GREY, size=20, align="right")
            for path, p in enumerate(tree.paths):
                count = sum(1 for q in tree.picks(m.talents).values() if q == path)
                ui.text(window, f"{p.name}  {count}", (COLS_X + path * (CELL[0] + CELL_GAP) + CELL[0] / 2,
                                                       GRID.y + 8), p.color, size=20, align="center")
            for tier, path, rect in self._cells() if not self.panel else ():  # (a panel covers them)
                if path == 0:
                    lv = TIER_LEVELS[tier]
                    ui.text(window, f"Lv{lv}", (LEVEL_X, rect.y + 10), ui.WHITE if m.level >= lv else ui.GREY, size=18)
                state = self._state(tier, path)
                color = ui.GREY if state == "locked" else ui.WHITE
                ui.text(window, tree.tiers[tier][path].name, (rect.centerx, rect.y + 10), color, size=16,
                        align="center")
        else:
            ui.text(window, "No talents for this line yet.", (GRID.x + 14, GRID.y + 14), ui.GREY, size=22)
            ui.text(window, "Its moves still come with its level.", (GRID.x + 14, GRID.y + 32), ui.GREY, size=20)
        self._draw_info(window)
        keys = "Arrows: move   Enter: pick   M: moves   O: reorder   " \
               f"R: reset{'' if self.can_reset else ' (towns)'}   Q/W: Pokémon   S: back"
        ui.text(window, keys, (GRID.x + 10, GRID.bottom - PAD - 8), ui.GREY, size=15)
        if self.panel:
            self.panel.draw_overlay(window)
        if self.asking:
            ui.text(window, f"Take back all of {m.name}'s talents?", (320, 158), ui.WHITE, size=22, align="center")
            ui.text(window, "Enter: yes   X: no", (320, 178), ui.GREY, size=20, align="center")

    def _draw_info(self, window: pygame.Surface) -> None:
        m, tree, talent = self.monster, self.monster.tree, self.talent
        x, y = INFO.x + 10, INFO.y + PAD
        if talent:
            tier, path = self.cursor
            ui.text(window, talent.name, (x, y), tree.paths[path].color, size=26)
            y += 19
            ui.text(window, f"{tree.paths[path].name}   tier {tier + 1} (Lv{TIER_LEVELS[tier]})", (x, y),
                    ui.GREY, size=17)
            y += 13
            ui.text(window, talent.pool_text, (x, y), ui.GREY, size=17)
            y += 17
            for line in _wrap(talent.text, WRAP):
                ui.text(window, line, (x, y), size=18)
                y += 13
            y += 4
            if DEEP.get(tier):
                ui.text(window, f"Needs {DEEP[tier]} earlier {tree.paths[path].name} talents", (x, y), ui.GREY,
                        size=16)
                y += 13
            state = self._state(tier, path)
            if self.message:
                note, color = self.message, GREEN if self.message.startswith("Picked") else ui.YELLOW
            elif state == "picked":
                note, color = "Picked", GREEN
            elif state == "open":
                note, color = "Enter: pick", GREEN
            elif state == "other":
                reason = m.why_not(tier, path)
                note = reason or ("Enter: pick instead" if self.can_reset else "Change picks in towns")
                color = RED if reason else GREEN if self.can_reset else ui.GREY
            else:
                note, color = m.why_not(tier, path), RED
            for line in _wrap(note, WRAP + 4):
                ui.text(window, line, (x, y), color, size=17)
                y += 13
        elif self.message:
            ui.text(window, self.message, (x, y), ui.YELLOW, size=17)
        # The moves it knows (and the next ones to come).
        y = max(y + 8, INFO.y + 150) if talent else INFO.y + PAD
        k = settings.SCALE
        pygame.draw.line(window, (70, 80, 140), (x * k, y * k), ((INFO.right - 10) * k, y * k), 2)
        y += 10
        ui.text(window, "Moves", (x, y), ui.YELLOW, size=18)
        ui.text(window, "M: equip", (INFO.right - 10, y + 1), ui.GREY, size=15, align="right")
        y += 15
        known = m.known
        coming = [lm for lm in tree.moves if lm.key not in known][:2]
        for key in known:
            slot = "F" if key == tree.basic.key else str(m.equipped.index(key) + 2) if key in m.equipped else ""
            move = m.move(key)
            changed = move != MOVES[move.name]
            ui.text(window, slot, (x, y), ui.YELLOW, size=15)
            ui.text(window, move.name + (" *" if changed else ""), (x + 12, y), ui.WHITE if slot else ui.GREY,
                    size=16)
            y += 12
            if y > INFO.bottom - 30:
                break
        for lm in coming:
            if y > INFO.bottom - 30:
                break
            stage = f", {tree.species[lm.stage].capitalize()}" if lm.stage > m.species.stage else ""
            ui.text(window, f"{lm.name}  (Lv{lm.level}{stage})", (x + 12, y), DIM, size=16)
            y += 12
        ui.text(window, "* changed by a talent", (x, INFO.bottom - PAD - 8), ui.GREY, size=14)


def _arrow(surface: pygame.Surface, x: int, y: int, direction: int) -> None:
    """A small triangle pointing up (-1) or down (1): more tiers that way."""
    pygame.draw.polygon(surface, ui.WHITE, [(x - 4, y), (x + 4, y), (x, y + 4 * direction)])
