"""Area themes: what a generated map looks like and which Pokémon live there."""

from dataclasses import dataclass

from ..mechanics.items import Range

Color = tuple[int, int, int]


@dataclass(frozen=True)
class Backdrop:
    """The colours of the battle background (sky, distant hills, field)."""
    sky_top: tuple[int, int, int] = (104, 168, 232)
    sky_bottom: tuple[int, int, int] = (196, 228, 244)
    hills: tuple[tuple[int, int, int], tuple[int, int, int]] = ((120, 176, 112), (104, 160, 100))
    field_far: tuple[int, int, int] = (112, 184, 88)
    field_near: tuple[int, int, int] = (84, 160, 68)
    stripe: tuple[int, int, int] = (96, 168, 76)
    shadow: tuple[int, int, int] = (60, 110, 50)  # under the combatants


MEADOW_BACKDROP = Backdrop()


@dataclass(frozen=True)
class PoolEntry:
    """A species that can appear, how often (relative weight), and at what levels."""
    species: str
    weight: int
    levels: Range


@dataclass(frozen=True)
class Palette:
    """Tile colours: the solid ground (fill), its surface (top), and platforms."""
    fill: Color
    fill_dark: Color
    fill_light: Color
    top: Color
    top_dark: Color
    top_light: Color
    platform: Color
    platform_dark: Color
    platform_light: Color


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    palette: Palette
    pool: tuple[PoolEntry, ...]
    backdrop: Backdrop                  # battle background
    group_sizes: tuple[tuple[int, int], ...] = ((1, 60), (2, 30), (3, 10))  # (size, weight)
    ceiling: bool = False               # caves have a rocky ceiling
    art: str = "woods"                  # map art (tileset.py): "woods" (Pixellab) or "cave" (drawn in code)

    @property
    def levels(self) -> Range:
        """The lowest and highest level its Pokémon come at (chests' item levels)."""
        return min(e.levels[0] for e in self.pool), max(e.levels[1] for e in self.pool)


MEADOW = Theme(
    "meadow", "Meadow",
    Palette(fill=(124, 92, 60), fill_dark=(100, 72, 46), fill_light=(148, 112, 76),
            top=(98, 178, 72), top_dark=(70, 140, 56), top_light=(140, 210, 100),
            platform=(150, 96, 48), platform_dark=(96, 58, 28), platform_light=(186, 128, 72)),
    pool=(
        PoolEntry("pidgey", 30, (2, 4)),
        PoolEntry("rattata", 30, (2, 4)),
        PoolEntry("caterpie", 15, (2, 4)),
        PoolEntry("weedle", 15, (2, 4)),
        PoolEntry("oddish", 8, (3, 5)),
        PoolEntry("bellsprout", 8, (3, 5)),
        PoolEntry("pikachu", 3, (3, 5)),
        PoolEntry("bulbasaur", 1, (4, 5)),
    ),
    backdrop=MEADOW_BACKDROP,
)

ICE_CAVE = Theme(
    "ice_cave", "Ice Cave",
    Palette(fill=(70, 88, 128), fill_dark=(52, 66, 100), fill_light=(110, 140, 180),
            top=(232, 244, 252), top_dark=(180, 206, 230), top_light=(255, 255, 255),
            platform=(150, 210, 240), platform_dark=(96, 160, 210), platform_light=(220, 245, 255)),
    pool=(
        PoolEntry("seel", 30, (3, 5)),
        PoolEntry("shellder", 30, (3, 5)),
        PoolEntry("psyduck", 15, (3, 5)),
        PoolEntry("horsea", 15, (3, 5)),
        PoolEntry("jynx", 5, (4, 6)),
        PoolEntry("dewgong", 3, (5, 7)),
        PoolEntry("lapras", 1, (6, 8)),
    ),
    backdrop=Backdrop(sky_top=(20, 28, 52), sky_bottom=(48, 66, 104),
                      hills=((60, 80, 120), (52, 70, 108)),
                      field_far=(176, 204, 228), field_near=(140, 176, 210), stripe=(160, 192, 222),
                      shadow=(96, 124, 160)),
    ceiling=True,
    art="cave",
)

# Viridian Forest: Red's and Blue's forest Pokémon together, at their Gen 1
# levels. (Same map art as the meadow for now; a darker battle backdrop.)
FOREST = Theme(
    "forest", "Viridian Forest",
    MEADOW.palette,
    pool=(
        PoolEntry("caterpie", 25, (3, 5)),
        PoolEntry("metapod", 20, (4, 6)),
        PoolEntry("weedle", 25, (3, 5)),
        PoolEntry("kakuna", 20, (4, 6)),
        PoolEntry("pikachu", 5, (3, 5)),
    ),
    backdrop=Backdrop(sky_top=(70, 120, 90), sky_bottom=(140, 180, 130),
                      hills=((52, 104, 64), (44, 92, 56)),
                      field_far=(88, 150, 72), field_near=(62, 122, 56), stripe=(74, 136, 64),
                      shadow=(40, 80, 40)),
)

THEMES = {t.key: t for t in (MEADOW, FOREST, ICE_CAVE)}
