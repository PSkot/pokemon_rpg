"""The Rocket Hideout's spinner floors (`Room.puzzle` "spinners:<key>"),
after Red/Blue's arrow-tile mazes, turned on their side.

A stretch of the room is the puzzle: the floor is covered in pads, and a
catwalk (one-way platforms, too high to jump up to) runs over it, with
gaps. Each layout is two strings, one character per column: the floor's
pads (`floor`) and the catwalk (`catwalk`).

    >  <   an arrow pad: step on it and you're spun along that way, out
           of control, until a stop pad or a wall (arrows on the way turn
           you; spun off the catwalk, you fly on about 5 tiles as you fall)
    o      a stop pad
    ^      a launch pad (floor only): shoots you straight up onto the
           catwalk above it
    .  =   plain floor / plain catwalk
    (space)  no catwalk there

The arrow fields are too wide to jump over, and every arrow points
somewhere you can get out of: no layout can trap the player (checked with
a solver when they were made). The way through takes the catwalk, the
right gaps, and a running jump off its end.
"""

from dataclasses import dataclass

from .level import PLATFORM, TILE, Level

START_COL = 20     # the puzzle's first column in its room
CATWALK_RISE = 5   # tiles above the floor (a full jump reaches under 4)
CLEAR = 2          # columns either side kept free of Pokémon and platforms


def _row(*parts: str) -> str:
    return "".join(parts)


@dataclass(frozen=True)
class Layout:
    floor: str
    catwalk: str

    def __post_init__(self):
        assert len(self.floor) == len(self.catwalk)

    @property
    def cols(self) -> int:
        return len(self.floor)


LAYOUTS = {
    # B2F: up at once (the floor ahead only spins you back), over the
    # catwalk's first gap, then the arrows throw you down and along to a
    # second launch; a running jump off the catwalk's end lands past the
    # last field.
    "b2": Layout(
        floor=_row("..", "^", "<" * 10, "o", "^", ">" * 12, "^", "<" * 10, "o", "..."),
        catwalk=_row("  ", "=" * 8, "  ", "=" * 5, ">" * 4, " " * 6, "=" * 7, " " * 8),
    ),
    # B3F: longer. Up, over a gap, down through the right gap and up again;
    # the catwalk's arrows fling you off its end, onto back-arrows that
    # bring you to the next launch; then a field of back-arrows on the
    # catwalk to jump clean over, and the same leap at the end.
    "b3": Layout(
        floor=_row("..", "^", "<" * 7, "o", ">" * 8, "^", "<" * 8, "o", "^", "<" * 10, "^", "<" * 6, "o",
                   "...."),
        catwalk=_row("  ", "=" * 5, "  ", "=" * 5, " " * 5, "=" * 6, ">" * 3, " ", "=" * 6, "<" * 4, " ",
                     "=" * 3, " " * 9),
    ),
}


def layout_of(puzzle: str) -> Layout | None:
    """The layout a room's `puzzle` names ("spinners:b2"), if any."""
    kind, _, key = puzzle.partition(":")
    return LAYOUTS[key] if kind == "spinners" else None


def carve(level: Level, layout: Layout) -> None:
    """Lay the puzzle into a generated room: the catwalk's platforms, and
    nothing else in the way (no other platforms, Pokémon, chests or balls)."""
    first, last = START_COL - CLEAR, START_COL + layout.cols + CLEAR
    inside = lambda col: first <= col < last  # noqa: E731
    for row, a, b in level.platforms:
        for col in range(a, b + 1):
            if inside(col):
                level.grid[row][col] = "."
    level.platforms = [(r, a, b) for r, a, b in level.platforms if not (inside(a) or inside(b))]
    level.spawns = [s for s in level.spawns if not inside(int(s.x // TILE))]
    level.chests = [c for c in level.chests if not inside(int(c[0] // TILE))]
    level.balls = [b for b in level.balls if not inside(int(b[0] // TILE))]
    row = catwalk_row(level)
    run = None
    for i, c in enumerate(layout.catwalk + " "):
        col = START_COL + i
        if c != " " and i < layout.cols:
            level.grid[row][col] = PLATFORM
            run = run if run is not None else col
        elif run is not None:
            level.platforms.append((row, run, col - 1))
            run = None


def floor_row(level: Level) -> int:
    return level.surface[START_COL]


def catwalk_row(level: Level) -> int:
    return floor_row(level) - CATWALK_RISE
