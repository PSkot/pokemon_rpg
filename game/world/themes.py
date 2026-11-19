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
    # A painted background instead (assets/sprites/pixellab/backdrops/), at
    # half the battle area's size: drawn 2x.
    art: str = ""


MEADOW_BACKDROP = Backdrop(art="meadow.png")


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
    # A painted far wall instead (assets/sprites/pixellab/walls/, 320×180,
    # drawn 2×, mirrored every other time so it joins up), dimmed by `dim`.
    wall: str = ""
    dim: int = 90
    near_rocks: bool = True  # rock drawn in front of the far wall (not in halls)
    # A built tunnel's far wall instead of rock: courses of wall tiles, and a
    # lamp (in `glow`'s colours) every `lamps` px (the Underground Path).
    lamps: int = 0


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
    decor: str = ""                     # whose decorations a code-drawn map uses (tileset.DECOR); "" = its own
    doorway: str = "doorway"            # its doorways' prop (tileset.draw_prop); "" = drawn in code
    far: str = ""                       # "woods" maps: a painted far layer (pixellab/far/) instead of sky and hills
    built: bool = False                 # a built interior (the S.S. Anne): flat floors and ceilings, of planks

    @property
    def decor_key(self) -> str:
        return self.decor or self.key

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
        PoolEntry("pidgey", 55, (2, 4)),
        PoolEntry("rattata", 45, (2, 3)),
    ),
    backdrop=MEADOW_BACKDROP,
    group_sizes=((1, 80), (2, 20)),  # mostly one at a time: the starter starts out alone
)

# Viridian Forest: Red's and Blue's forest Pokémon together, at their Gen 1
# levels. (Same map art as the meadow for now; a darker battle backdrop.)
FOREST = Theme(
    "forest", "Viridian Forest",
    MEADOW.palette,
    pool=(
        PoolEntry("caterpie", 25, (4, 6)),
        PoolEntry("metapod", 20, (5, 7)),
        PoolEntry("weedle", 25, (4, 6)),
        PoolEntry("kakuna", 20, (5, 7)),
        PoolEntry("pikachu", 5, (4, 6)),
    ),
    backdrop=Backdrop(art="forest.png", sky_top=(70, 120, 90), sky_bottom=(140, 180, 130),
                      hills=((52, 104, 64), (44, 92, 56)),
                      field_far=(88, 150, 72), field_near=(62, 122, 56), stripe=(74, 136, 64),
                      shadow=(40, 80, 40)),
    far="forest.png",
)

# Route 22, west of Viridian: its Red/Blue Pokémon (same look as the meadow).
ROUTE_22 = Theme(
    "route_22", "Route 22",
    MEADOW.palette,
    pool=(
        PoolEntry("rattata", 40, (3, 6)),
        PoolEntry("spearow", 15, (4, 6)),
        PoolEntry("nidoran_f", 20, (3, 5)),
        PoolEntry("nidoran_m", 25, (3, 5)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# Route 3, east of Pewter: its Red/Blue Pokémon (Sandshrew from Blue, Ekans
# from Red), at their Gen 1 levels.
ROUTE_3 = Theme(
    "route_3", "Route 3",
    MEADOW.palette,
    pool=(
        PoolEntry("spearow", 35, (11, 13)),
        PoolEntry("jigglypuff", 20, (8, 12)),
        PoolEntry("sandshrew", 25, (11, 13)),
        PoolEntry("ekans", 20, (11, 13)),
    ),
    backdrop=Backdrop(art="route_3.png", field_far=(176, 176, 96), field_near=(150, 150, 76), stripe=(162, 162, 86),
                      shadow=(100, 100, 50)),  # a dry, sandy field
    far="route_3.png",
)

# Route 4, from Mt. Moon's far side down to Cerulean City: the same dry
# hills as Route 3, with its Red/Blue Pokémon a little stronger.
ROUTE_4 = Theme(
    "route_4", "Route 4",
    MEADOW.palette,
    pool=(
        PoolEntry("rattata", 30, (16, 19)),
        PoolEntry("spearow", 30, (16, 19)),
        PoolEntry("ekans", 20, (16, 20)),
        PoolEntry("sandshrew", 20, (16, 20)),
    ),
    backdrop=ROUTE_3.backdrop,
    far="route_3.png",
)

# Route 24 (Nugget Bridge, north of Cerulean) and Route 25 (east to Bill's
# Sea Cottage): their Red/Blue grass Pokémon (Oddish from Red, Bellsprout
# from Blue), Abra, and Venonat on Route 25.
ROUTE_24 = Theme(
    "route_24", "Route 24",
    MEADOW.palette,
    pool=(
        PoolEntry("oddish", 25, (18, 21)),
        PoolEntry("bellsprout", 25, (18, 21)),
        PoolEntry("pidgey", 20, (19, 22)),
        PoolEntry("abra", 10, (17, 20)),
        PoolEntry("caterpie", 10, (16, 18)),
        PoolEntry("weedle", 10, (16, 18)),
    ),
    backdrop=MEADOW_BACKDROP,
)

ROUTE_25 = Theme(
    "route_25", "Route 25",
    MEADOW.palette,
    pool=(
        PoolEntry("oddish", 20, (19, 22)),
        PoolEntry("bellsprout", 20, (19, 22)),
        PoolEntry("venonat", 20, (19, 22)),
        PoolEntry("pidgey", 15, (20, 23)),
        PoolEntry("abra", 10, (18, 21)),
        PoolEntry("metapod", 8, (18, 20)),
        PoolEntry("kakuna", 7, (18, 20)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# Route 5, south of Cerulean City: Red/Blue's Pokémon there (Meowth from
# Blue, Mankey from Red), with Route 24's grass ones.
ROUTE_5 = Theme(
    "route_5", "Route 5",
    MEADOW.palette,
    pool=(
        PoolEntry("meowth", 25, (20, 23)),
        PoolEntry("mankey", 25, (20, 23)),
        PoolEntry("pidgey", 20, (21, 24)),
        PoolEntry("oddish", 15, (20, 23)),
        PoolEntry("bellsprout", 15, (20, 23)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# The Underground Path under Saffron City, from Route 5 to Route 6: a
# lamp-lit tunnel (drawn in code). No wild Pokémon live there in Red/Blue;
# here the Diglett who dug it out again, and what moved in after them.
UNDERGROUND = Theme(
    "underground", "Underground Path",
    Palette(fill=(104, 98, 92), fill_dark=(76, 72, 68), fill_light=(138, 130, 122),
            top=(170, 160, 144), top_dark=(134, 126, 114), top_light=(204, 194, 176),
            platform=(120, 100, 76), platform_dark=(80, 66, 50), platform_light=(160, 136, 104)),
    pool=(
        PoolEntry("diglett", 35, (21, 24)),
        PoolEntry("rattata", 30, (22, 25)),
        PoolEntry("zubat", 20, (22, 25)),
        PoolEntry("ekans", 15, (22, 25)),
    ),
    backdrop=Backdrop(art="underground.png", sky_top=(40, 36, 34), sky_bottom=(84, 78, 72), hills=((96, 90, 84), (86, 80, 74)),
                      field_far=(160, 150, 136), field_near=(138, 128, 116), stripe=(150, 140, 126),
                      shadow=(90, 84, 76)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(30, 28, 28), sky_bottom=(66, 60, 56), far_rock=(54, 50, 48), near_rock=(72, 66, 62),
                  glow=((150, 120, 60), (255, 232, 160)), wall="underground.png", dim=60, near_rocks=False,
                  lamps=96),
    doorway="",
)

# Route 6, from the Underground Path's south end down to Vermilion City:
# Route 5's Pokémon, a little stronger, and Psyduck from its pond.
ROUTE_6 = Theme(
    "route_6", "Route 6",
    MEADOW.palette,
    pool=(
        PoolEntry("meowth", 20, (22, 25)),
        PoolEntry("mankey", 20, (22, 25)),
        PoolEntry("pidgey", 20, (23, 26)),
        PoolEntry("oddish", 15, (22, 25)),
        PoolEntry("bellsprout", 15, (22, 25)),
        PoolEntry("psyduck", 10, (22, 25)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# The S.S. Anne: a luxury liner's corridors (polished planks, a painted
# wall of portholes and brass). No wild Pokémon live aboard: its pool is
# never met (`Route.wild`).
SS_ANNE = Theme(
    "ss_anne", "S.S. Anne",
    Palette(fill=(110, 72, 44), fill_dark=(78, 50, 30), fill_light=(146, 98, 60),
            top=(176, 120, 72), top_dark=(138, 92, 54), top_light=(210, 154, 96),
            platform=(150, 104, 60), platform_dark=(98, 66, 38), platform_light=(196, 146, 88)),
    pool=(PoolEntry("tentacool", 1, (24, 26)),),
    backdrop=Backdrop(art="ss_anne.png", sky_top=(220, 206, 180), sky_bottom=(200, 186, 160),
                      hills=((120, 80, 50), (110, 74, 46)), field_far=(170, 116, 70), field_near=(150, 100, 60),
                      stripe=(160, 108, 66), shadow=(100, 66, 40)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(60, 44, 30), sky_bottom=(110, 84, 60), far_rock=(80, 60, 44), near_rock=(96, 70, 50),
                  glow=None, wall="ss_anne.png", dim=40, near_rocks=False),
    doorway="",
    built=True,
)

# The Vermilion Gym: Lt. Surge's army-style hall of steel (flat floors,
# a painted wall of hazard stripes and pylons). Its pool is never met.
VERMILION_GYM = Theme(
    "vermilion_gym", "Vermilion Gym",
    Palette(fill=(92, 96, 100), fill_dark=(62, 66, 70), fill_light=(130, 136, 140),
            top=(168, 172, 160), top_dark=(126, 130, 120), top_light=(210, 214, 196),
            platform=(200, 170, 60), platform_dark=(120, 100, 30), platform_light=(240, 214, 100)),
    pool=(PoolEntry("voltorb", 1, (25, 27)),),
    backdrop=Backdrop(art="vermilion_gym.png", sky_top=(80, 86, 70), sky_bottom=(120, 126, 104),
                      hills=((96, 100, 84), (90, 94, 78)), field_far=(150, 154, 150), field_near=(130, 134, 130),
                      stripe=(140, 144, 140), shadow=(80, 84, 80)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(40, 44, 36), sky_bottom=(80, 86, 70), far_rock=(60, 64, 56), near_rock=(76, 80, 70),
                  glow=None, wall="vermilion_gym.png", dim=50, near_rocks=False),
    doorway="",
    built=True,
)

# The Pewter Gym: an indoor rock hall (drawn in code). Its pool is never
# met: gyms have only their trainers (`Route.wild`).
PEWTER_GYM = Theme(
    "pewter_gym", "Pewter Gym",
    Palette(fill=(112, 92, 72), fill_dark=(84, 68, 54), fill_light=(150, 126, 100),
            top=(176, 156, 120), top_dark=(140, 120, 92), top_light=(208, 190, 152),
            platform=(128, 104, 80), platform_dark=(84, 68, 54), platform_light=(170, 144, 112)),
    pool=(PoolEntry("geodude", 1, (10, 12)),),
    backdrop=Backdrop(art="pewter_gym.png", sky_top=(58, 46, 40), sky_bottom=(96, 80, 66),
                      hills=((110, 92, 76), (98, 82, 68)),
                      field_far=(168, 146, 110), field_near=(146, 124, 92), stripe=(158, 136, 100),
                      shadow=(96, 80, 60)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(34, 26, 24), sky_bottom=(70, 56, 46), far_rock=(56, 44, 38), near_rock=(84, 68, 56),
                  glow=None, wall="pewter_gym.png", near_rocks=False),
    doorway="",
)

# The Cerulean Gym: an indoor pool hall (drawn in code, with a painted
# far wall). Like the Pewter Gym, its pool is never met.
CERULEAN_GYM = Theme(
    "cerulean_gym", "Cerulean Gym",
    Palette(fill=(70, 96, 140), fill_dark=(50, 70, 108), fill_light=(110, 140, 184),
            top=(206, 222, 236), top_dark=(160, 184, 210), top_light=(240, 248, 255),
            platform=(96, 150, 200), platform_dark=(60, 100, 150), platform_light=(160, 200, 236)),
    pool=(PoolEntry("goldeen", 1, (17, 19)),),
    backdrop=Backdrop(art="cerulean_gym.png", sky_top=(60, 110, 170), sky_bottom=(120, 170, 220),
                      hills=((90, 140, 190), (80, 128, 176)),
                      field_far=(200, 216, 232), field_near=(176, 196, 218), stripe=(188, 206, 226),
                      shadow=(110, 130, 160)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(30, 50, 80), sky_bottom=(60, 96, 140), far_rock=(50, 76, 110), near_rock=(70, 100, 140),
                  glow=None, wall="cerulean_gym.png", near_rocks=False, dim=70),
    doorway="",
)

# Mt. Moon: a grey-violet cave with faint moonstone glints; its Red/Blue
# Pokémon, a few levels up (the party comes in around Lv18).
MT_MOON = Theme(
    "mt_moon", "Mt. Moon",
    Palette(fill=(88, 82, 100), fill_dark=(64, 60, 76), fill_light=(120, 114, 136),
            top=(150, 144, 164), top_dark=(116, 110, 130), top_light=(186, 180, 200),
            platform=(110, 104, 124), platform_dark=(72, 68, 84), platform_light=(150, 144, 166)),
    pool=(
        PoolEntry("zubat", 45, (14, 18)),
        PoolEntry("geodude", 30, (14, 17)),
        PoolEntry("paras", 18, (15, 19)),
        PoolEntry("clefairy", 7, (15, 19)),
    ),
    backdrop=Backdrop(art="mt_moon.png", sky_top=(22, 20, 34), sky_bottom=(58, 54, 76),
                      hills=((74, 70, 92), (66, 62, 82)),
                      field_far=(132, 126, 146), field_near=(110, 104, 124), stripe=(120, 114, 134),
                      shadow=(70, 66, 82)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(14, 12, 24), sky_bottom=(42, 38, 58), far_rock=(30, 28, 44), near_rock=(48, 44, 64),
                  glow=((90, 80, 140), (210, 200, 255)), wall="mt_moon.png"),
    doorway="doorway_cave",
)

THEMES = {t.key: t for t in (MEADOW, ROUTE_22, FOREST, ROUTE_3, PEWTER_GYM, MT_MOON)}
