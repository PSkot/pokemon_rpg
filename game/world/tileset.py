"""Map art: tiles, decorations, buildings and parallax backgrounds.

The meadow (towns and routes) uses Pixellab art: its ground from the woods
tileset, buildings, and a parallax background. The ice cave and one-way
platforms are still placeholders drawn in code from the theme's colours.
"""

import random
from dataclasses import dataclass
from functools import cache

import pygame

from .. import settings
from .level import EMPTY, PLATFORM, ROWS, SOLID, TILE, Level
from .themes import Palette, Theme

FAR, NEAR = 0.2, 0.5  # how fast the farthest and nearest background layers scroll (× the camera)

# Pixellab background art: sheets of cells in assets/sprites/pixellab/.
ART = settings.ASSETS / "sprites" / "pixellab"
MEADOW_SKY = ((120, 190, 240), (205, 234, 250))  # top and bottom of the sky gradient
CLOUDS = ("background.png", (8, 9, 10, 11, 13))  # white clouds (64×64 cells)
JOIN_BLEND = 6  # columns each side of a join over which flat bands' heights are evened out


@dataclass(frozen=True)
class StripArt:
    """A background layer chained from strip pieces: cells of a sheet
    whose edges join up side by side. Cells have a 1px transparent column
    on each side facing another cell; it's cut off."""
    sheet: str
    cell: tuple[int, int]    # cell size in the sheet
    pieces: tuple[int, ...]  # the cells used, row by row
    top: int                 # y of the strip's top row on screen; its bottom colour fills below it
    parallax: float          # how fast it scrolls (× the camera)
    max_step: int            # how far the silhouette may jump at a join (px; summed over the bands if smooth)
    max_colour: int = 255    # mean colour difference allowed down a join
    smooth: bool = False     # flat colour bands (far hills): their heights are evened out at each join


# The meadow, back to front: distant mountains, hills with trees, a tree line.
MEADOW_STRIPS = (
    StripArt("background_far.png", (64, 64), (9, 10, 13, 14), top=150, parallax=FAR, max_step=20, smooth=True),
    StripArt("background_mid.png", (64, 32), tuple(range(8, 32)), top=196, parallax=0.35, max_step=1,
             max_colour=30),
    StripArt("background_near.png", (64, 64), tuple(range(16)), top=232, parallax=NEAR, max_step=1,
             max_colour=45),
)


def _speckle(surface: pygame.Surface, rect: pygame.Rect, rng: random.Random, colors, count: int) -> None:
    for _ in range(count):
        surface.set_at((rng.randrange(rect.left, rect.right), rng.randrange(rect.top, rect.bottom)),
                       rng.choice(colors))


def _fill_tile(surface: pygame.Surface, rect: pygame.Rect, p: Palette, rng: random.Random) -> None:
    surface.fill(p.fill, rect)
    _speckle(surface, rect, rng, (p.fill_dark, p.fill_dark, p.fill_light), 9)
    if rng.random() < 0.25:  # a pebble
        x, y = rng.randrange(rect.left + 2, rect.right - 4), rng.randrange(rect.top + 2, rect.bottom - 3)
        pygame.draw.rect(surface, p.fill_dark, (x, y, 3, 2))
        surface.set_at((x, y), p.fill_light)


def _top_tile(surface: pygame.Surface, rect: pygame.Rect, p: Palette, rng: random.Random) -> None:
    """Ground with grass or snow on top, its lower edge ragged."""
    _fill_tile(surface, rect, p, rng)
    for x in range(rect.left, rect.right):
        depth = rng.choice((4, 5, 5, 6))
        pygame.draw.line(surface, p.top, (x, rect.top), (x, rect.top + depth - 1))
        surface.set_at((x, rect.top + depth), p.top_dark)
    _speckle(surface, pygame.Rect(rect.left, rect.top + 1, TILE, 3), rng, (p.top_light, p.top_dark), 3)
    pygame.draw.line(surface, p.top_light, (rect.left, rect.top), (rect.right - 1, rect.top))


def _underside(surface: pygame.Surface, rect: pygame.Rect, p: Palette) -> None:
    """The bottom edge of a ceiling."""
    pygame.draw.line(surface, p.fill_dark, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
    pygame.draw.line(surface, p.fill_dark, (rect.left, rect.bottom - 2), (rect.right - 1, rect.bottom - 2))


def _platform_tile(surface: pygame.Surface, rect: pygame.Rect, p: Palette, left_end: bool, right_end: bool,
                   theme: Theme) -> None:
    """A thin plank (or slab of ice) along the top of the tile."""
    plank = pygame.Rect(rect.left, rect.top, TILE, 6)
    if left_end:
        plank.left += 1
        plank.width -= 1
    if right_end:
        plank.width -= 1
    pygame.draw.rect(surface, p.platform, plank)
    pygame.draw.line(surface, p.platform_light, plank.topleft, (plank.right - 1, plank.top))
    pygame.draw.line(surface, p.platform_dark, (plank.left, plank.bottom - 1), (plank.right - 1, plank.bottom - 1))
    if theme.art == "woods":
        for x in (rect.left + 3, rect.left + 11):  # nails / plank joints
            surface.set_at((x, rect.top + 3), p.platform_dark)
        pygame.draw.line(surface, p.platform_dark, (rect.right - 1, rect.top + 1), (rect.right - 1, rect.top + 4))
    else:
        surface.set_at((rect.left + 5, rect.top + 2), p.platform_light)
    if left_end:
        pygame.draw.line(surface, p.platform_dark, (plank.left, plank.top), (plank.left, plank.bottom - 1))
    if right_end:
        pygame.draw.line(surface, p.platform_dark, (plank.right - 1, plank.top), (plank.right - 1, plank.bottom - 1))


# ------------------------------------------------------------- decorations

def _rock(s, x, y, rng, p):
    pygame.draw.ellipse(s, p.fill_dark, (x - 4, y - 5, 9, 6))
    pygame.draw.ellipse(s, p.fill_light, (x - 3, y - 5, 5, 3))


def _crystal(s, x, y, rng, p):
    for dx, h, color in ((-3, 6, (110, 200, 240)), (2, 9, (150, 225, 255)), (0, 12, (190, 240, 255))):
        pygame.draw.polygon(s, color, [(x + dx - 2, y), (x + dx + 2, y), (x + dx, y - h)])
    s.set_at((x, y - 9), (255, 255, 255))


def _snow_mound(s, x, y, rng, p):
    pygame.draw.ellipse(s, p.top_dark, (x - 6, y - 4, 13, 6))
    pygame.draw.ellipse(s, p.top, (x - 5, y - 5, 10, 5))


def _icicle(s, x, y, rng, p):
    """Hangs down from a ceiling whose underside is at `y`."""
    h = rng.randint(4, 10)
    pygame.draw.polygon(s, (170, 220, 250), [(x - 2, y), (x + 2, y), (x, y + h)])
    pygame.draw.line(s, (235, 250, 255), (x - 1, y), (x, y + h - 2))


def _stalactite(s, x, y, rng, p):
    """A rock spike hanging from a ceiling whose underside is at `y`."""
    h = rng.randint(4, 9)
    pygame.draw.polygon(s, p.fill_dark, [(x - 3, y), (x + 3, y), (x, y + h)])
    pygame.draw.line(s, p.fill_light, (x - 1, y), (x, y + h - 2))


CEILING_DECOR = {"ice_cave": _icicle, "pewter_gym": _stalactite}  # theme -> what hangs from a cave's ceiling

DECOR = {  # theme -> [(chance per ground tile, draw)] (code-drawn themes; the meadow's come from its tileset)
    "ice_cave": [(0.07, _crystal), (0.10, _snow_mound), (0.05, _rock)],
    "pewter_gym": [(0.12, _rock)],
}


# --------------------------------------------------------------------- map

# ------------------------------------------------------- Pixellab ground

# tileset_woods.png: 32×32 cells (1px transparent gutter at both sides).
# Grass-top cells have the grass line at row SURFACE_Y, plants above it, and
# grass then soil below it; their last rows are a dark band (for thin
# ledges), which deep ground leaves out.
WOODS = "tileset_woods.png"
WOODS_CELL = (32, 32)
SURFACE_Y = 16
GROUND_ROWS = 12  # rows of grass and soil used under the grass line (they end in plain soil)
# Grass tops by cell (row × 8 + column), weighted: plain grass most often,
# tall grass and bushes now and then.
GRASS_TOPS = {12: 4, 13: 3, 14: 6, 15: 6, 16: 5, 17: 5, 18: 2, 19: 3, 8: 1, 9: 1, 20: 1, 21: 1}
# The tileset's soil and outline colours (the exposed sides of steps are
# drawn in them, as the tileset's own cliff pieces don't fit 1-tile steps).
SOIL = (139, 76, 48)
SOIL_SPECKS = ((131, 73, 53), (159, 114, 91), (106, 52, 45))  # as in its soil cell
SOIL_SPECK_DENSITY = 0.05
SOIL_SHADE = (106, 52, 45)
SOIL_DARK = (81, 37, 39)
OUTLINE_DARK = (38, 14, 20)
GRASS_OUTLINE = (13, 89, 47)
SOIL_DECALS = {51: 1}  # pebbles (on transparent)
SOIL_DECAL_GAP = (60, 140)  # px between soil decals along the map


@cache
def _woods(index: int, trim: bool = True) -> pygame.Surface:
    """A cell of the woods tileset, without its side gutters if `trim`."""
    cell = _cells(WOODS, WOODS_CELL)[index]
    return cell.subsurface((1, 0, 30, 32)) if trim else cell


def _surface_px(level: Level, col: int) -> int:
    return level.surface[col] * TILE


def _render_woods(level: Level, surface: pygame.Surface) -> None:
    """Meadow ground from the woods tileset: soil, then grass-top strips
    along each flat stretch, then cliff edges where the ground steps."""
    rng = random.Random(level.seed * 31 + 7)
    h = surface.get_height()
    # Soil everywhere under the grass, speckled like the tileset's soil.
    for col in range(level.cols):
        top = _surface_px(level, col) + GROUND_ROWS
        surface.fill(SOIL, (col * TILE, top, TILE, h - top))
        for _ in range(round(TILE * (h - top) * SOIL_SPECK_DENSITY)):
            surface.set_at((col * TILE + rng.randrange(TILE), rng.randrange(top, h)), rng.choice(SOIL_SPECKS))
    # Soil decals (pebbles, roots), only where the soil goes all the way across them.
    decals = list(SOIL_DECALS)
    x = rng.randint(0, 40)
    while x < level.width:
        decal = _woods(rng.choices(decals, weights=list(SOIL_DECALS.values()))[0])
        box = decal.get_bounding_rect()
        cols = range(max(0, x // TILE), min(level.cols, (x + box.w) // TILE + 1))
        lowest_grass = max(_surface_px(level, c) for c in cols) + GROUND_ROWS
        y = lowest_grass + rng.randint(4, 30)
        if y + box.h < h:
            surface.blit(decal, (x, y), box)
        x += box.w + rng.randint(*SOIL_DECAL_GAP)
    # Grass tops: one strip per flat stretch, chained from random cells and
    # cut to the stretch's width.
    tops, weights = list(GRASS_TOPS), list(GRASS_TOPS.values())
    col = 0
    while col < level.cols:
        end = col
        while end + 1 < level.cols and level.surface[end + 1] == level.surface[col]:
            end += 1
        width = (end - col + 1) * TILE
        strip = pygame.Surface((width, SURFACE_Y + GROUND_ROWS), pygame.SRCALPHA)
        x = -rng.randint(0, 29)
        while x < width:
            strip.blit(_woods(rng.choices(tops, weights=weights)[0]), (x, 0),
                       pygame.Rect(0, 0, 30, SURFACE_Y + GROUND_ROWS))
            x += 30
        surface.blit(strip, (col * TILE, _surface_px(level, col) - SURFACE_Y))
        col = end + 1
    # The exposed sides where the ground steps down: an outline, a shaded
    # band inside it, and the grass's end rounded off.
    for col in range(level.cols):
        top = _surface_px(level, col)
        for side in (-1, 1):
            n = col + side
            if not 0 <= n < level.cols or level.surface[n] <= level.surface[col]:
                continue
            bottom = _surface_px(level, n)
            x = col * TILE if side < 0 else col * TILE + TILE - 1
            inward = -side
            surface.fill(SOIL_SHADE, (min(x, x + inward * 2), top + 6, 3, bottom - top - 6))
            surface.fill(SOIL_DARK, pygame.Rect(x, top + 6, 1, bottom - top - 6))
            pygame.draw.line(surface, OUTLINE_DARK, (x, top + 6), (x, bottom - 1))
            pygame.draw.line(surface, GRASS_OUTLINE, (x, top + 1), (x, top + 6))  # the grass's end
            surface.set_at((x, top), (0, 0, 0, 0))  # a rounded corner
            surface.set_at((x + inward, top), GRASS_OUTLINE)


def render(level: Level) -> pygame.Surface:
    """The map's tiles and decorations, drawn once (transparent where empty)."""
    p, theme = level.theme.palette, level.theme
    if theme.art == "woods":
        surface = pygame.Surface((level.width, ROWS * TILE), pygame.SRCALPHA)
        _render_woods(level, surface)
        for row in range(ROWS):
            for col in range(level.cols):
                if level.grid[row][col] == PLATFORM:
                    rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
                    _platform_tile(surface, rect, p, level.tile(col - 1, row) != PLATFORM,
                                   level.tile(col + 1, row) != PLATFORM, theme)
        return surface
    surface = pygame.Surface((level.width, ROWS * TILE), pygame.SRCALPHA)
    decor = []
    for row in range(ROWS):
        for col in range(level.cols):
            kind = level.grid[row][col]
            rng = random.Random(level.seed * 1_000_003 + row * 7919 + col)
            rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            if kind == SOLID:
                above, below = level.tile(col, row - 1), level.tile(col, row + 1)
                if above == SOLID or row == 0:
                    _fill_tile(surface, rect, p, rng)
                else:
                    _top_tile(surface, rect, p, rng)
                    for chance, draw in DECOR[theme.key]:
                        if rng.random() < chance:
                            decor.append((draw, rect.left + rng.randint(4, 12), rect.top, rng))
                            break
                if below != SOLID and row + 1 < ROWS:  # a ceiling's underside
                    _underside(surface, rect, p)
                    if theme.ceiling and theme.key in CEILING_DECOR and rng.random() < 0.4:
                        decor.append((CEILING_DECOR[theme.key], rect.left + rng.randint(3, 13), rect.bottom, rng))
                # Darken the sides of steps, so height changes read clearly.
                for dx, edge in ((-1, rect.left), (1, rect.right - 1)):
                    if level.tile(col + dx, row) == EMPTY:
                        pygame.draw.line(surface, p.fill_dark, (edge, rect.top), (edge, rect.bottom - 1))
            elif kind == PLATFORM:
                _platform_tile(surface, rect, p, level.tile(col - 1, row) != PLATFORM,
                               level.tile(col + 1, row) != PLATFORM, theme)
    for draw, x, y, rng in decor:  # on top of the tiles they stick out over
        draw(surface, x, y, rng, p)
    return surface


# -------------------------------------------------------------- background

def _layer_width(level: Level, factor: float) -> int:
    return round(settings.LOGICAL_SIZE[0] + (level.width - settings.LOGICAL_SIZE[0]) * factor) + 1


@cache
def _cells(sheet: str, size: tuple[int, int] = (64, 64)) -> list[pygame.Surface]:
    """A sheet's cells, row by row."""
    image = pygame.image.load(ART / sheet).convert_alpha()
    w, h = size
    return [image.subsurface((c * w, r * h, w, h))
            for r in range(image.get_height() // h) for c in range(image.get_width() // w)]


@cache
def _piece(art: StripArt, index: int) -> pygame.Surface:
    """A strip piece without its gutters (sides facing another cell)."""
    cell = _cells(art.sheet, art.cell)[index]
    across = _cells(art.sheet, art.cell)[0].get_parent().get_width() // art.cell[0]
    column = index % across
    left, right = int(column > 0), int(column < across - 1)
    return cell.subsurface((left, 0, art.cell[0] - left - right, art.cell[1]))


Runs = list[list]  # one column: [start row, colour] for each run of a colour, top down


def _runs(surface: pygame.Surface, x: int) -> Runs:
    runs, last = [], None
    for y in range(surface.get_height()):
        c = surface.get_at((x, y))
        colour = tuple(c) if c.a else None
        if colour != last:
            runs.append([y, colour])
            last = colour
    return runs


def _step(left: Runs, right: Runs) -> float:
    """How far apart two neighbouring columns' bands are (inf: different bands)."""
    if [c for _, c in left] != [c for _, c in right]:
        return float("inf")
    return sum(abs(a[0] - b[0]) for a, b in zip(left, right))


def _join(art: StripArt, a: int, b: int) -> tuple[float, float]:
    """(silhouette step, mean colour difference) where piece `b` follows `a`."""
    left, right = _piece(art, a), _piece(art, b)
    lx = left.get_width() - 1
    if art.smooth:
        return _step(_runs(left, lx), _runs(right, 0)), 0
    h = left.get_height()
    top = lambda s, x: next((y for y in range(h) if s.get_at((x, y)).a), h)  # noqa: E731
    pairs = [(left.get_at((lx, y)), right.get_at((0, y))) for y in range(h)]
    diffs = [sum(abs(p - q) for p, q in zip(c1[:3], c2[:3])) for c1, c2 in pairs if c1.a and c2.a]
    return abs(top(left, lx) - top(right, 0)), sum(diffs) / max(1, len(diffs))


@cache
def _follows(art: StripArt) -> dict[int, list[int]]:
    """Which pieces can follow each piece (the closest one if none fits)."""
    follows = {}
    for a in art.pieces:
        costs = {b: _join(art, a, b) for b in art.pieces}
        fits = [b for b, (step, colour) in costs.items() if step <= art.max_step and colour <= art.max_colour]
        follows[a] = fits or [min(costs, key=lambda b: costs[b])]
    return follows


def _strip(art: StripArt, rng: random.Random, width: int) -> pygame.Surface:
    """At least `width` px of the layer: pieces chained at random, each
    followed only by one that fits (avoiding the last two used, if it can)."""
    follows, chain, width_so_far = _follows(art), [], 0
    piece = rng.choice(art.pieces)
    while width_so_far < width:
        chain.append(piece)
        width_so_far += _piece(art, piece).get_width()
        options = follows[piece]
        piece = rng.choice([b for b in options if b not in chain[-2:]] or options)
    if art.smooth:
        return _smoothed(art, chain)
    strip = pygame.Surface((width_so_far, art.cell[1]), pygame.SRCALPHA)
    x = 0
    for piece in chain:
        strip.blit(_piece(art, piece), (x, 0))
        x += _piece(art, piece).get_width()
    return strip


def _smoothed(art: StripArt, chain: list[int]) -> pygame.Surface:
    """Pieces of flat colour bands side by side, with the bands' heights
    evened out over a few columns at each join."""
    columns: list[Runs] = []
    for piece in chain:
        surface = _piece(art, piece)
        new = [_runs(surface, x) for x in range(surface.get_width())]
        join = len(columns)
        left = columns[-1] if columns else None
        columns += new
        if left is None or _step(left, new[0]) == float("inf"):
            continue
        deltas = [b[0] - a[0] for a, b in zip(left, new[0])]
        for t in range(-JOIN_BLEND, JOIN_BLEND):
            col = columns[join + t]
            if _step(col, left) == float("inf"):
                continue  # a different set of bands here: leave it
            share = (t + JOIN_BLEND) / (2 * JOIN_BLEND) - (1 if t >= 0 else 0)
            for run, delta in zip(col, deltas):
                run[0] += round(delta * share)
    h = art.cell[1]
    strip = pygame.Surface((len(columns), h), pygame.SRCALPHA)
    for x, col in enumerate(columns):
        for i, (start, colour) in enumerate(col):
            end = col[i + 1][0] if i + 1 < len(col) else h
            if colour and end > start:
                pygame.draw.line(strip, colour, (x, max(0, start)), (x, end - 1))
    return strip


def _layer_width(level: Level, factor: float) -> int:
    return round(settings.LOGICAL_SIZE[0] + (level.width - settings.LOGICAL_SIZE[0]) * factor) + 1


def _strip_layer(art: StripArt, level: Level, rng: random.Random, surface: pygame.Surface | None = None):
    """The layer for `art` (drawn onto `surface` if given): its strip at its
    height, and its bottom colour filled down to the bottom of the screen."""
    w, h = _layer_width(level, art.parallax), settings.LOGICAL_SIZE[1]
    layer = surface or pygame.Surface((w, h), pygame.SRCALPHA)
    strip = _strip(art, rng, w)
    layer.blit(strip, (0, art.top))
    bottom = strip.get_height() - 1
    layer.fill(strip.get_at((next(x for x in range(strip.get_width()) if strip.get_at((x, bottom)).a), bottom)),
               (0, art.top + strip.get_height(), w, h))
    return layer, art.parallax


def _meadow(level: Level, rng: random.Random) -> list[tuple[pygame.Surface, float]]:
    """Sky and clouds, then the meadow's strips (the first drawn on the sky)."""
    far_art = MEADOW_STRIPS[0]
    sky = pygame.Surface((_layer_width(level, far_art.parallax), settings.LOGICAL_SIZE[1]))
    _gradient(sky, *MEADOW_SKY)
    clouds = [cell.subsurface(cell.get_bounding_rect()) for cell in (_cells(CLOUDS[0])[i] for i in CLOUDS[1])]
    x = rng.randint(0, 60)
    while x < sky.get_width():
        cloud = rng.choice(clouds)
        sky.blit(cloud, (x, rng.randint(14, 100)))
        x += cloud.get_width() + rng.randint(40, 140)
    return [_strip_layer(far_art, level, rng, sky)] + [_strip_layer(art, level, rng) for art in MEADOW_STRIPS[1:]]


def backgrounds(level: Level) -> list[tuple[pygame.Surface, float]]:
    """The background layers, back to front, with how fast each scrolls;
    each is just wide enough for its parallax."""
    rng = random.Random(level.seed)
    if level.theme.art == "woods":
        return _meadow(level, rng)
    h = settings.LOGICAL_SIZE[1]
    far_w, near_w = _layer_width(level, FAR), _layer_width(level, NEAR)
    far = pygame.Surface((far_w, h))
    near = pygame.Surface((near_w, h), pygame.SRCALPHA)
    look = level.theme.cave
    _gradient(far, look.sky_top, look.sky_bottom)
    for x in range(0, far_w, 24):  # the cave's back wall: hanging and standing rock
        w = rng.randint(14, 30)
        pygame.draw.polygon(far, look.far_rock, [(x, 0), (x + w, 0), (x + w // 2, rng.randint(30, 90))])
        pygame.draw.polygon(far, look.far_rock, [(x, h), (x + w, h), (x + w // 2, h - rng.randint(60, 160))])
    if look.glow:
        for _ in range(far_w // 40):  # faint glowing crystals
            x, y = rng.randrange(far_w), rng.randint(100, 280)
            pygame.draw.circle(far, look.glow[0], (x, y), 3)
            far.set_at((x, y), look.glow[1])
    for x in range(0, near_w, 40):
        w = rng.randint(24, 44)
        pygame.draw.polygon(near, look.near_rock, [(x, h), (x + w, h), (x + w // 2, h - rng.randint(90, 190))])
        pygame.draw.polygon(near, look.near_rock, [(x, 0), (x + w, 0), (x + w // 2, rng.randint(40, 110))])
    return [(far, FAR), (near, NEAR)]


def _gradient(surface: pygame.Surface, top, bottom) -> None:
    h = surface.get_height()
    for y in range(h):
        t = y / (h - 1)
        pygame.draw.line(surface, [round(a + (b - a) * t) for a, b in zip(top, bottom)], (0, y),
                         (surface.get_width(), y))


# --------------------------------------------------------------- buildings

BUILDING_CELL = (128, 128)  # cells of the building sheets (houses.png, functional_buildings.png)
OUTLINE = (48, 28, 16)
BUILDING_SINK = 1  # px a building's base sits into the ground (over the grass edge)
WOOD_POST, WOOD_BOARD = (120, 78, 42), (164, 112, 64)  # the quest board


@cache
def building(sprite: tuple[str, int]) -> tuple[pygame.Surface, int]:
    """A building sprite (sheet, cell) cut to its outline, and the row its
    base stands on (the lowest row at least half its width wide: below it
    only small things like steps or plants hang)."""
    cell = _cells(sprite[0], BUILDING_CELL)[sprite[1]]
    box = cell.get_bounding_rect()
    image = cell.subsurface(box)
    wide = [y for y in range(box.h) if sum(image.get_at((x, y)).a > 0 for x in range(box.w)) > box.w / 2]
    return image, max(wide)


def draw_building(s: pygame.Surface, sprite: tuple[str, int], x: int, ground: int) -> pygame.Rect:
    """Draw a building with its left edge at `x`, standing on `ground`;
    returns where it was drawn."""
    image, base = building(sprite)
    return s.blit(image, (x, ground - base - 1 + BUILDING_SINK))


def fence(s: pygame.Surface, x: int, ground: int, w: int) -> None:
    """A low white picket fence."""
    for px in range(x, x + w, 8):
        pygame.draw.rect(s, (240, 236, 224), (px, ground - 14, 4, 14))
        pygame.draw.rect(s, OUTLINE, (px, ground - 14, 4, 14), 1)
    for y in (ground - 11, ground - 5):
        pygame.draw.line(s, (220, 214, 200), (x, y), (x + w - 4, y), 2)


def quest_board(s: pygame.Surface, x: int, ground: int, notes: int) -> pygame.Rect:
    """A wooden quest board (placeholder art) centred on `x`, with up to 5
    paper notes pinned to it; returns its outline."""
    board = pygame.Rect(x - 24, ground - 50, 48, 30)
    for px in (board.left + 5, board.right - 9):  # posts
        post = pygame.Rect(px, board.bottom - 2, 4, ground - board.bottom + 2)
        pygame.draw.rect(s, WOOD_POST, post)
        pygame.draw.rect(s, OUTLINE, post, 1)
    pygame.draw.rect(s, WOOD_BOARD, board)
    for y in range(board.top + 7, board.bottom - 2, 7):  # planks
        pygame.draw.line(s, WOOD_POST, (board.left + 1, y), (board.right - 2, y))
    pygame.draw.rect(s, OUTLINE, board, 1)
    roof = pygame.Rect(board.left - 4, board.top - 5, board.w + 8, 5)  # a little roof plank
    pygame.draw.rect(s, WOOD_POST, roof)
    pygame.draw.rect(s, OUTLINE, roof, 1)
    for i in range(min(notes, 5)):
        note = pygame.Rect(board.left + 4 + i * 8, board.top + 4 + (i % 2) * 5, 7, 10)
        pygame.draw.rect(s, (244, 238, 222), note)
        for ly in (note.top + 3, note.top + 6):
            pygame.draw.line(s, (180, 170, 150), (note.left + 1, ly), (note.right - 2, ly))
        s.set_at((note.centerx, note.top + 1), (210, 60, 60))  # a pin
    return roof.union(board).union(pygame.Rect(board.left, board.bottom, board.w, ground - board.bottom))


# ------------------------------------------------------------- Poké Mart
# Placeholder art drawn in code: the shop's room, shelves and counter.

MART_CEILING, MART_LIGHT = (62, 60, 78), (250, 244, 210)
MART_WALL, MART_WALL_LINE = (238, 232, 212), (224, 216, 192)
MART_BLUE, MART_BLUE_LIGHT, MART_BLUE_DARK = (64, 104, 184), (110, 150, 220), (36, 60, 120)
MART_FLOOR = ((226, 228, 236), (200, 204, 216))
MART_METAL, MART_METAL_DARK = (204, 208, 218), (60, 64, 80)
MART_GOODS = ((150, 90, 200), (230, 80, 80), (90, 180, 110), (240, 200, 80), (90, 150, 230), (240, 150, 70))
CEILING_H, WAINSCOT_H = 44, 64


def mart_room(width: int, ground: int, shelves: list[int], door_x: int) -> pygame.Surface:
    """The shop's room (drawn once): ceiling with lamps, wall, blue
    wainscot, tiled floor, shelves (left edges in `shelves`) and the glass
    door out at `door_x`."""
    h = settings.LOGICAL_SIZE[1]
    s = pygame.Surface((width, h))
    s.fill(MART_WALL)
    for x in range(0, width, 16):
        pygame.draw.line(s, MART_WALL_LINE, (x, CEILING_H), (x, ground - WAINSCOT_H))
    pygame.draw.rect(s, MART_CEILING, (0, 0, width, CEILING_H))
    pygame.draw.rect(s, MART_BLUE, (0, CEILING_H, width, 6))  # a blue band under the ceiling
    for x in range(48, width, 128):  # lamps
        pygame.draw.rect(s, MART_LIGHT, (x, CEILING_H - 5, 40, 4))
        pygame.draw.line(s, OUTLINE, (x, CEILING_H - 1), (x + 39, CEILING_H - 1))
    top = ground - WAINSCOT_H
    pygame.draw.rect(s, MART_BLUE, (0, top, width, WAINSCOT_H))
    pygame.draw.rect(s, MART_BLUE_LIGHT, (0, top, width, 3))
    for x in range(8, width, 48):  # panels
        pygame.draw.rect(s, MART_BLUE_DARK, (x, top + 10, 40, WAINSCOT_H - 18), 1)
    for row, y in enumerate(range(ground, h, 12)):  # floor tiles
        for col, x in enumerate(range(-(row % 2) * 12, width, 24)):
            pygame.draw.rect(s, MART_FLOOR[(row + col) % 2], (x, y, 24, 12))
    pygame.draw.line(s, MART_METAL_DARK, (0, ground), (width, ground))
    for x in shelves:
        _mart_shelf(s, x, ground, random.Random(x))
    door = pygame.Rect(door_x - 22, ground - 70, 44, 70)  # sliding glass doors
    pygame.draw.rect(s, MART_METAL, door)
    for half in (door.inflate(-8, -8).move(0, 4).clip((door.x, door.y, door.w // 2 - 1, door.h)),
                 door.inflate(-8, -8).move(0, 4).clip((door.centerx + 1, door.y, door.w // 2, door.h))):
        pygame.draw.rect(s, (170, 214, 240), half)
        pygame.draw.line(s, (230, 246, 255), (half.x + 3, half.bottom - 10), (half.right - 4, half.y + 8), 2)
    pygame.draw.rect(s, MART_METAL_DARK, door, 1)
    pygame.draw.rect(s, (190, 60, 60), (door.x - 6, ground + 1, door.w + 12, 4))  # door mat
    return s


def _mart_shelf(s: pygame.Surface, x: int, ground: int, rng: random.Random) -> None:
    """A shelf unit of goods (bottles, boxes, Poké Balls) against the wall."""
    w, h = 72, 104
    unit = pygame.Rect(x, ground - h, w, h)
    pygame.draw.rect(s, MART_METAL, unit)
    pygame.draw.rect(s, MART_METAL_DARK, unit, 1)
    for shelf_y in range(unit.top + 30, unit.bottom, 30):
        gx = unit.left + 4
        while gx < unit.right - 10:
            kind, color = rng.randrange(3), rng.choice(MART_GOODS)
            if kind == 0:  # a spray bottle
                pygame.draw.rect(s, color, (gx, shelf_y - 12, 7, 12))
                pygame.draw.rect(s, (245, 245, 250), (gx + 2, shelf_y - 16, 3, 4))
                pygame.draw.rect(s, OUTLINE, (gx, shelf_y - 12, 7, 12), 1)
                gx += 9
            elif kind == 1:  # a box
                bh = rng.randint(10, 18)
                pygame.draw.rect(s, color, (gx, shelf_y - bh, 11, bh))
                pygame.draw.line(s, (250, 250, 250), (gx + 2, shelf_y - bh + 3), (gx + 8, shelf_y - bh + 3))
                pygame.draw.rect(s, OUTLINE, (gx, shelf_y - bh, 11, bh), 1)
                gx += 13
            else:  # a Poké Ball
                c = (gx + 4, shelf_y - 5)
                pygame.draw.circle(s, (245, 245, 250), c, 4)
                pygame.draw.rect(s, (220, 60, 60), (gx, shelf_y - 10, 9, 5))
                pygame.draw.circle(s, OUTLINE, c, 5, 1)
                gx += 11
        pygame.draw.rect(s, MART_METAL_DARK, (unit.left + 1, shelf_y, w - 2, 3))
    pygame.draw.rect(s, MART_BLUE, (unit.left, unit.top, w, 8))  # a price strip on top
    pygame.draw.rect(s, MART_METAL_DARK, (unit.left, unit.top, w, 8), 1)


def mart_counter(s: pygame.Surface, x: int, ground: int, w: int) -> pygame.Rect:
    """The shop counter (in front of the shopkeeper), left edge at `x`;
    returns its outline."""
    counter = pygame.Rect(x, ground - 30, w, 30)
    pygame.draw.rect(s, MART_BLUE, counter)
    pygame.draw.rect(s, MART_BLUE_LIGHT, (x + 4, counter.top + 12, w - 8, 3))
    pygame.draw.rect(s, MART_BLUE_DARK, counter, 1)
    top = pygame.Rect(x - 3, counter.top - 4, w + 6, 5)
    pygame.draw.rect(s, (244, 244, 250), top)
    pygame.draw.rect(s, MART_METAL_DARK, top, 1)
    till = pygame.Rect(x + w - 30, top.top - 12, 22, 12)  # the till
    pygame.draw.rect(s, (150, 154, 170), till)
    pygame.draw.rect(s, (110, 200, 140), (till.x + 3, till.y + 2, 10, 4))
    pygame.draw.rect(s, MART_METAL_DARK, till, 1)
    return counter.union(top).union(till)


def mart_sign(s: pygame.Surface, center_x: int, y: int) -> pygame.Rect:
    """The blue sign board over the counter (the scene writes on it)."""
    sign = pygame.Rect(0, y, 120, 22)
    sign.centerx = center_x
    pygame.draw.rect(s, MART_BLUE, sign, border_radius=3)
    pygame.draw.rect(s, (245, 245, 250), sign.inflate(-4, -4), 1, border_radius=2)
    pygame.draw.rect(s, MART_BLUE_DARK, sign, 1, border_radius=3)
    return sign
