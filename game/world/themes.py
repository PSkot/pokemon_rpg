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
class CaveLook:
    """The colours of a code-drawn cave's background (tileset.backgrounds)."""
    sky_top: Color = (16, 22, 42)       # the far wall's gradient
    sky_bottom: Color = (40, 56, 92)
    far_rock: Color = (30, 42, 72)      # hanging and standing rock on the far wall
    near_rock: Color = (44, 60, 98)
    glow: tuple[Color, Color] | None = ((60, 100, 150), (150, 220, 255))  # faint crystals (None: none)


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
    cave: CaveLook = CaveLook()         # a cave's background colours

    @property
    def levels(self) -> Range:
        """The lowest and highest level its Pokémon come at (chests' item levels)."""
        return min(e.levels[0] for e in self.pool), max(e.levels[1] for e in self.pool)


# The meadow: Route 1 (and the look of towns). Its Pokémon are Route 1's
# in Red/Blue: only Pidgey and Rattata.
MEADOW = Theme(
    "meadow", "Meadow",
    Palette(fill=(124, 92, 60), fill_dark=(100, 72, 46), fill_light=(148, 112, 76),
            top=(98, 178, 72), top_dark=(70, 140, 56), top_light=(140, 210, 100),
            platform=(150, 96, 48), platform_dark=(96, 58, 28), platform_light=(186, 128, 72)),
    pool=(
        PoolEntry("pidgey", 55, (2, 5)),
        PoolEntry("rattata", 45, (2, 4)),
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

# Route 22, west of Viridian: its Red/Blue Pokémon (same look as the meadow).
ROUTE_22 = Theme(
    "route_22", "Route 22",
    MEADOW.palette,
    pool=(
        PoolEntry("rattata", 40, (2, 5)),
        PoolEntry("spearow", 15, (3, 5)),
        PoolEntry("nidoran_f", 20, (2, 4)),
        PoolEntry("nidoran_m", 25, (2, 4)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# Route 3, east of Pewter: its Red/Blue Pokémon (Sandshrew from Blue, Ekans
# from Red), at their Gen 1 levels.
ROUTE_3 = Theme(
    "route_3", "Route 3",
    MEADOW.palette,
    pool=(
        PoolEntry("spearow", 35, (6, 8)),
        PoolEntry("jigglypuff", 20, (3, 7)),
        PoolEntry("sandshrew", 25, (6, 8)),
        PoolEntry("ekans", 20, (6, 8)),
    ),
    backdrop=Backdrop(field_far=(176, 176, 96), field_near=(150, 150, 76), stripe=(162, 162, 86),
                      shadow=(100, 100, 50)),  # a dry, sandy field
)

# The Pewter Gym: an indoor rock hall (drawn in code). Its pool is never
# met: gyms have only their trainers (`Route.wild`).
PEWTER_GYM = Theme(
    "pewter_gym", "Pewter Gym",
    Palette(fill=(112, 92, 72), fill_dark=(84, 68, 54), fill_light=(150, 126, 100),
            top=(176, 156, 120), top_dark=(140, 120, 92), top_light=(208, 190, 152),
            platform=(128, 104, 80), platform_dark=(84, 68, 54), platform_light=(170, 144, 112)),
    pool=(PoolEntry("geodude", 1, (10, 12)),),
    backdrop=Backdrop(sky_top=(58, 46, 40), sky_bottom=(96, 80, 66),
                      hills=((110, 92, 76), (98, 82, 68)),
                      field_far=(168, 146, 110), field_near=(146, 124, 92), stripe=(158, 136, 100),
                      shadow=(96, 80, 60)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(34, 26, 24), sky_bottom=(70, 56, 46), far_rock=(56, 44, 38), near_rock=(84, 68, 56),
                  glow=None),
)

# Mt. Moon: a grey-violet cave with faint moonstone glints; its Red/Blue
# Pokémon, a few levels up (the party comes in around Lv18).
MT_MOON = Theme(
    "mt_moon", "Mt. Moon",
    Palette(fill=(88, 82, 100), fill_dark=(64, 60, 76), fill_light=(120, 114, 136),
            top=(150, 144, 164), top_dark=(116, 110, 130), top_light=(186, 180, 200),
            platform=(110, 104, 124), platform_dark=(72, 68, 84), platform_light=(150, 144, 166)),
    pool=(
        PoolEntry("zubat", 45, (8, 12)),
        PoolEntry("geodude", 30, (8, 11)),
        PoolEntry("paras", 18, (9, 13)),
        PoolEntry("clefairy", 7, (9, 13)),
    ),
    backdrop=Backdrop(sky_top=(22, 20, 34), sky_bottom=(58, 54, 76),
                      hills=((74, 70, 92), (66, 62, 82)),
                      field_far=(132, 126, 146), field_near=(110, 104, 124), stripe=(120, 114, 134),
                      shadow=(70, 66, 82)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(14, 12, 24), sky_bottom=(42, 38, 58), far_rock=(30, 28, 44), near_rock=(48, 44, 64),
                  glow=((90, 80, 140), (210, 200, 255))),
)

THEMES = {t.key: t for t in (MEADOW, ROUTE_22, FOREST, ICE_CAVE, ROUTE_3, PEWTER_GYM, MT_MOON)}
