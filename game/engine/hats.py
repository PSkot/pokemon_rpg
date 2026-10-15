"""Hats: head gear, drawn on the Pokémon that wears it.

Hats are 32×32 cells of a hat sheet (assets/sprites/pixellab/hats*.png).
Most are drawn on a reference face; that face and its outline are cut out
when the sheet loads, leaving a hole the Pokémon's own face shows through.

Where a hat sits comes from hat_anchors.json (written by tools/hat_viewer.py):
- "heads": per sprite sheet and row, each frame's head anchor (the top of
  the head, in frame pixels), so the hat follows the head as it moves;
- "sheets": per hat sheet, the hat size per species and per-hat changes
  (anchor, mirrored, face kept). A hat's anchor is the point of the hat
  that goes on the head anchor.
"""

import json
from functools import cache

import pygame

from .. import settings

SPRITES = settings.ASSETS / "sprites" / "pixellab"
ANCHORS_JSON = SPRITES / "hat_anchors.json"
SHEET = "hats_new.png"      # the hat sheet the game's hats come from
HAT = 32                    # hat cell size
HAT_SINK = 0.3              # sheets without faces: anchor this fraction of the hat's height up from its bottom
# Hats drawn on a reference face: the face hole's top edge goes this many px
# below the head anchor, and its centre this many px in front of it.
FACE_DROP = 5
FACE_FORWARD = 1
# The reference face's skin colours (light tones, shades, and the orange
# tint under gold helmets). Skin-like tones next to them are cut out too.
FACE_COLOURS = {(243, 173, 140), (242, 172, 128), (236, 177, 139), (206, 124, 113), (198, 112, 90),
                (213, 142, 94), (205, 121, 85)}
FACE_SKIN = (243, 173, 140)  # the main skin colour, which hats never use


# --- cutting out the face ------------------------------------------------

def _neighbours(x: int, y: int, size: int, diagonal: bool = True) -> list[tuple[int, int]]:
    steps = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i or j) and (diagonal or not i or not j)]
    return [(x + i, y + j) for i, j in steps if 0 <= x + i < size and 0 <= y + j < size]


def _groups(points: set, size: int) -> list[set]:
    """`points` split into 8-connected groups."""
    points, groups = set(points), []
    while points:
        todo = [points.pop()]
        group = set(todo)
        while todo:
            for q in _neighbours(*todo.pop(), size):
                if q in points:
                    points.remove(q)
                    group.add(q)
                    todo.append(q)
        groups.append(group)
    return groups


def strip_face(cell: pygame.Surface) -> tuple[pygame.Surface, pygame.Rect | None]:
    """The hat without its reference face, and where the face was (None: no face)."""
    hat = cell.copy()
    n = hat.get_width()
    pixels = [(x, y) for x in range(n) for y in range(n) if hat.get_at((x, y)).a]
    if not pixels:
        return hat, None
    skin = {p for p in pixels if tuple(hat.get_at(p))[:3] in FACE_COLOURS}
    # A face is in the lower part of the hat and face-sized; other patches of
    # skin colours (small, high up or tall) are part of the hat.
    top, bottom = min(y for _, y in pixels), max(y for _, y in pixels)

    def is_face(group: set) -> bool:
        ys = [y for _, y in group]
        return max(ys) >= top + 0.6 * (bottom - top) and max(ys) - min(ys) < 14

    groups = _groups(skin, n)
    face = set().union(*[g for g in groups if len(g) >= 12 and is_face(g)])
    if not face:
        return hat, None
    # Also bare skin elsewhere, like the scalp above a headband.
    face |= set().union(*[g for g in groups if any(hat.get_at(p)[:3] == FACE_SKIN for p in g)])

    def skin_like(c: pygame.Color) -> bool:
        return c.a and c.r > 180 and 35 <= c.r - c.g <= 110 and 0 <= c.g - c.b <= 60

    def dark(c: pygame.Color) -> bool:
        return c.a and c.r + c.g + c.b < 60

    todo = list(face)
    while todo:
        for q in _neighbours(*todo.pop(), n):
            if q not in face and skin_like(hat.get_at(q)):
                face.add(q)
                todo.append(q)
    box = pygame.Rect(min(x for x, _ in face), min(y for _, y in face), 0, 0)
    box.size = (max(x for x, _ in face) - box.x + 1, max(y for _, y in face) - box.y + 1)
    # The face's outline goes too, except where it is also the hat's edge
    # (it touches hat colours).
    outline = {q for p in face for q in _neighbours(*p, n) if q not in face and dark(hat.get_at(q))
               and not any(r not in face and hat.get_at(r).a and not dark(hat.get_at(r))
                           for r in _neighbours(*q, n, diagonal=False))}
    for p in face | outline:
        hat.set_at(p, (0, 0, 0, 0))
    left = {p for p in pixels if p not in face and p not in outline}
    for group in _groups(left, n):  # stray bits of outline
        if len(group) < 8:
            for p in group:
                hat.set_at(p, (0, 0, 0, 0))
    return hat, box


class HatSheet:
    """A sheet of hats, each with its reference face cut out."""

    def __init__(self, name: str):
        self.name = name
        sheet = pygame.image.load(SPRITES / name).convert_alpha()
        self.originals = [sheet.subsurface((c * HAT, r * HAT, HAT, HAT)).copy()
                          for r in range(sheet.get_height() // HAT) for c in range(sheet.get_width() // HAT)]
        stripped = [strip_face(cell) for cell in self.originals]
        self.stripped = [hat for hat, _ in stripped]
        self.faces = [face for _, face in stripped]
        found = sorted((f for f in self.faces if f), key=lambda f: f.y)
        self.typical_face = found[len(found) // 2] if found else None

    def __len__(self) -> int:
        return len(self.originals)

    @property
    def default_scale(self) -> float:
        return 1.0 if self.typical_face else 0.75

    def default_anchor(self, index: int, scale: float) -> list[int]:
        box = self.originals[index].get_bounding_rect()
        face = self.faces[index]
        if face:
            # Aligned by the chin: the face's top edge varies (brims, bare scalps).
            top = face.bottom - self.typical_face.height
            return [round(face.centerx - FACE_FORWARD / scale), round(top - FACE_DROP / scale)]
        if self.typical_face:
            # Drawn without a face (brimmed hats, crowns): the bottom edge goes
            # where a face's top edge would, just above the eyes.
            return [round(box.centerx - FACE_FORWARD / scale), round(box.bottom - FACE_DROP / scale)]
        # A sheet without faces: hats sit on top of the head.
        return [box.centerx, box.bottom - round(box.height * HAT_SINK)]


def load_data() -> dict:
    data = json.loads(ANCHORS_JSON.read_text(encoding="utf-8")) if ANCHORS_JSON.exists() else {}
    data.setdefault("heads", {})
    data.setdefault("sheets", {})
    return data


# --- in the game ---------------------------------------------------------

@cache
def _data() -> dict:
    return load_data()


@cache
def _sheet() -> HatSheet:
    return HatSheet(SHEET)


def head_anchors(sheet: str, row: int, count: int) -> list[tuple[int, int]] | None:
    """The head anchors of the first `count` frames of a sprite sheet row
    (None: not set, so hats aren't drawn)."""
    anchors = _data()["heads"].get(sheet, {}).get(str(row), [])
    return [tuple(a) for a in anchors[:count]] if len(anchors) >= count else None


@cache
def _image(index: int, species: str, flip: bool) -> tuple[pygame.Surface, tuple[int, int]]:
    """Hat `index` as drawn on `species`, and the point that goes on the head."""
    sheet, conf = _sheet(), _data()["sheets"].get(SHEET, {})
    scale = conf.get("scale", {}).get(species, sheet.default_scale)
    info = conf.get("hats", {}).get(str(index), {})
    image = (sheet.originals if info.get("keep_face") else sheet.stripped)[index]
    ax, ay = info.get("anchor", sheet.default_anchor(index, scale))
    if info.get("flip"):
        image, ax = pygame.transform.flip(image, True, False), HAT - 1 - ax
    if scale != 1:
        resize = pygame.transform.smoothscale_by if conf.get("smooth", True) else pygame.transform.scale_by
        image = resize(image, scale)
    ax, ay = round(ax * scale), round(ay * scale)
    if flip:
        image, ax = pygame.transform.flip(image, True, False), image.get_width() - 1 - ax
    return image, (ax, ay)


def draw(surface: pygame.Surface, index: int, species: str, anim, frame: int, frame_rect: pygame.Rect,
         flip: bool, alpha: int = 255) -> None:
    """Draw hat `index` on the head of `species` (its key, e.g. "bulbasaur"),
    showing frame `frame` of `anim` at `frame_rect` (mirrored if `flip`)."""
    if index < 0 or not anim.heads:
        return
    hx, hy = anim.heads[frame]
    if flip:
        hx = frame_rect.width - 1 - hx
    image, (ax, ay) = _image(index, species, flip)
    if alpha < 255:
        image = image.copy()
        image.set_alpha(alpha)
    surface.blit(image, (frame_rect.x + hx - ax, frame_rect.y + hy - ay))


def draw_worn(surface: pygame.Surface, monster, anim, frame: int, frame_rect: pygame.Rect, flip: bool,
              alpha: int = 255) -> None:
    """Draw the hat `monster` wears (if any) on frame `frame` of `anim`."""
    gear = monster.gear.get("head")
    if gear:
        draw(surface, gear.item.sprite, monster.species.name.lower(), anim, frame, frame_rect, flip, alpha)
