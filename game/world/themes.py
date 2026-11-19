"""Area themes: what a generated map looks like and which Pokémon live there."""

from dataclasses import dataclass, replace

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
    dark: bool = False                  # pitch dark (Rock Tunnel): only Flash's light around the player shows
    # "woods" maps: the sky's gradient (top, bottom; None = the meadow's
    # blue), and a colour the clouds and background strips are multiplied by
    # (Lavender Town's dusk).
    sky: tuple[Color, Color] | None = None
    tint: Color | None = None

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

# Lavender Town: the meadow at dusk, under a purple sky (a town: its pool
# is never met).
LAVENDER = replace(MEADOW, key="lavender", name="Lavender Town",
                   sky=((58, 40, 96), (206, 140, 164)), tint=(176, 146, 200))

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

# The Underground Path's west-east tunnel under Saffron (Route 8 to Route 7,
# by Celadon City): the same tunnel as the north-south one, deeper in.
UNDERGROUND_WEST = replace(UNDERGROUND, key="underground_west", name="Underground Path", decor="underground", pool=(
    PoolEntry("diglett", 30, (32, 35)),
    PoolEntry("raticate", 20, (33, 35)),
    PoolEntry("zubat", 20, (32, 35)),
    PoolEntry("ekans", 15, (32, 35)),
    PoolEntry("dugtrio", 15, (33, 36)),
))

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

# Route 11, east of Vermilion City to the gate where Snorlax sleeps: its
# Red/Blue Pokémon (Ekans from Red, Sandshrew from Blue), Spearow and
# Drowzee, a few levels under the party after the Thunder Badge.
ROUTE_11 = Theme(
    "route_11", "Route 11",
    MEADOW.palette,
    pool=(
        PoolEntry("drowzee", 30, (26, 29)),
        PoolEntry("spearow", 25, (26, 29)),
        PoolEntry("ekans", 20, (26, 29)),
        PoolEntry("sandshrew", 20, (26, 29)),
        PoolEntry("fearow", 5, (27, 29)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# Route 9, east of Cerulean City to the Route 10 Pokémon Center: Gen 1's
# Rattata, Spearow, Ekans and Sandshrew, their evolved forms, and Voltorb
# from the Power Plant down Route 10, a little under the party.
ROUTE_9 = Theme(
    "route_9", "Route 9",
    MEADOW.palette,
    pool=(
        PoolEntry("rattata", 20, (29, 32)),
        PoolEntry("spearow", 20, (29, 32)),
        PoolEntry("ekans", 15, (29, 32)),
        PoolEntry("sandshrew", 15, (29, 32)),
        PoolEntry("raticate", 10, (31, 33)),
        PoolEntry("fearow", 10, (31, 33)),
        PoolEntry("voltorb", 10, (30, 32)),
    ),
    backdrop=ROUTE_3.backdrop,
    far="route_3.png",
)

# Route 8, west of Lavender Town to the gate at Saffron City's east side:
# Gen 1's Route 8 Pokémon (Red's Growlithe and Ekans, Blue's Meowth and
# Sandshrew), Pidgeotto, Mankey and Abra, a little under the party.
ROUTE_8 = Theme(
    "route_8", "Route 8",
    MEADOW.palette,
    pool=(
        PoolEntry("pidgeotto", 20, (33, 35)),
        PoolEntry("growlithe", 15, (32, 35)),
        PoolEntry("mankey", 15, (32, 35)),
        PoolEntry("meowth", 15, (32, 35)),
        PoolEntry("ekans", 10, (32, 35)),
        PoolEntry("sandshrew", 10, (32, 35)),
        PoolEntry("abra", 10, (31, 33)),
        PoolEntry("kadabra", 5, (34, 36)),
    ),
    backdrop=MEADOW_BACKDROP,
)

# Rock Tunnel, from the Route 10 Pokémon Center to Lavender Town: pitch
# dark (Flash lights a circle around the player); Gen 1's Zubat, Geodude,
# Machop and Onix.
ROCK_TUNNEL = Theme(
    "rock_tunnel", "Rock Tunnel",
    Palette(fill=(84, 78, 72), fill_dark=(58, 54, 50), fill_light=(116, 108, 100),
            top=(138, 128, 116), top_dark=(104, 96, 88), top_light=(172, 162, 148),
            platform=(102, 94, 86), platform_dark=(66, 60, 56), platform_light=(140, 130, 120)),
    pool=(
        PoolEntry("zubat", 35, (30, 33)),
        PoolEntry("geodude", 30, (30, 33)),
        PoolEntry("machop", 20, (31, 33)),
        PoolEntry("onix", 15, (31, 34)),
    ),
    backdrop=Backdrop(art="rock_tunnel.png", sky_top=(18, 16, 16), sky_bottom=(54, 50, 46),
                      hills=((70, 64, 60), (62, 58, 54)), field_far=(120, 112, 104), field_near=(100, 94, 86),
                      stripe=(110, 102, 94), shadow=(60, 56, 52)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(10, 10, 12), sky_bottom=(36, 34, 32), far_rock=(30, 28, 26), near_rock=(46, 42, 40),
                  glow=None, wall="rock_tunnel.png", dim=30),
    doorway="doorway_cave",
    decor="mt_moon",
    dark=True,
)

# The Battle Tower's floors, by tier of five: built halls (flat floors), each
# grander than the last: marble halls, sky gardens, a storm spire, the
# celestial summit. Their pools are never met.
def _tower(key: str, name: str, palette: Palette, wall: str, look: CaveLook, backdrop: Backdrop) -> Theme:
    return Theme(key, name, palette, pool=(PoolEntry("pidgey", 1, (35, 35)),), backdrop=backdrop, ceiling=True,
                 art="cave", cave=look, doorway="", built=True)


TOWER_THEMES = (
    _tower("tower_1", "Battle Tower",
           Palette(fill=(196, 190, 176), fill_dark=(150, 144, 132), fill_light=(232, 228, 216),
                   top=(236, 230, 214), top_dark=(200, 190, 168), top_light=(252, 248, 236),
                   platform=(214, 180, 90), platform_dark=(150, 120, 50), platform_light=(244, 216, 130)),
           "tower_1.png", CaveLook(sky_top=(120, 116, 110), sky_bottom=(200, 196, 186), far_rock=(150, 146, 140),
                                   near_rock=(170, 166, 160), glow=None, wall="tower_1.png", dim=10,
                                   near_rocks=False),
           Backdrop(art="tower_1.png", sky_top=(200, 196, 186), sky_bottom=(236, 230, 214),
                    hills=((210, 204, 192), (200, 194, 182)), field_far=(232, 226, 210), field_near=(220, 214, 198),
                    stripe=(226, 220, 204), shadow=(180, 174, 160))),
    _tower("tower_2", "Battle Tower",
           Palette(fill=(150, 170, 140), fill_dark=(110, 130, 104), fill_light=(186, 204, 172),
                   top=(212, 222, 196), top_dark=(170, 186, 158), top_light=(236, 244, 222),
                   platform=(200, 160, 90), platform_dark=(140, 104, 50), platform_light=(232, 196, 128)),
           "tower_2.png", CaveLook(sky_top=(250, 200, 150), sky_bottom=(250, 230, 200), far_rock=(200, 180, 160),
                                   near_rock=(170, 160, 140), glow=None, wall="tower_2.png", dim=0,
                                   near_rocks=False),
           Backdrop(art="tower_2.png", sky_top=(250, 200, 150), sky_bottom=(250, 230, 200),
                    hills=((200, 210, 180), (190, 200, 170)), field_far=(212, 222, 196), field_near=(200, 210, 184),
                    stripe=(206, 216, 190), shadow=(160, 170, 150))),
    _tower("tower_3", "Battle Tower",
           Palette(fill=(70, 60, 96), fill_dark=(46, 40, 66), fill_light=(100, 88, 134),
                   top=(120, 108, 156), top_dark=(90, 80, 120), top_light=(150, 140, 190),
                   platform=(90, 200, 220), platform_dark=(40, 120, 150), platform_light=(160, 240, 250)),
           "tower_3.png", CaveLook(sky_top=(30, 20, 50), sky_bottom=(70, 50, 100), far_rock=(50, 40, 70),
                                   near_rock=(60, 50, 84), glow=((120, 220, 255), (220, 250, 255)),
                                   wall="tower_3.png", dim=10, near_rocks=False),
           Backdrop(art="tower_3.png", sky_top=(30, 20, 50), sky_bottom=(70, 50, 100),
                    hills=((60, 50, 90), (54, 44, 80)), field_far=(110, 100, 146), field_near=(96, 86, 130),
                    stripe=(104, 94, 140), shadow=(50, 40, 70))),
    _tower("tower_4", "Battle Tower",
           Palette(fill=(40, 36, 70), fill_dark=(24, 20, 46), fill_light=(66, 60, 106),
                   top=(210, 180, 90), top_dark=(160, 130, 60), top_light=(250, 226, 140),
                   platform=(230, 200, 110), platform_dark=(160, 130, 60), platform_light=(255, 240, 170)),
           "tower_4.png", CaveLook(sky_top=(10, 8, 30), sky_bottom=(40, 30, 80), far_rock=(30, 24, 60),
                                   near_rock=(40, 34, 70), glow=((255, 230, 150), (255, 250, 220)),
                                   wall="tower_4.png", dim=0, near_rocks=False),
           Backdrop(art="tower_4.png", sky_top=(10, 8, 30), sky_bottom=(40, 30, 80),
                    hills=((40, 34, 70), (34, 28, 60)), field_far=(80, 70, 120), field_near=(66, 58, 104),
                    stripe=(74, 64, 112), shadow=(30, 24, 56))),
)

# Route 2's north end, between Diglett's Cave and Pewter City: a short walk
# (no wild Pokémon: its Gen 1 ones are far below the party by now).
ROUTE_2 = Theme(
    "route_2", "Route 2",
    MEADOW.palette,
    pool=(PoolEntry("pidgey", 1, (5, 7)),),
    backdrop=MEADOW_BACKDROP,
)

# Diglett's Cave: a long tunnel dug by Diglett, from Route 11 to Route 2
# (soft brown earth, roots overhead). Diglett and, deeper in, Dugtrio.
DIGLETTS_CAVE = Theme(
    "digletts_cave", "Diglett's Cave",
    Palette(fill=(104, 76, 54), fill_dark=(74, 52, 36), fill_light=(140, 104, 74),
            top=(150, 112, 78), top_dark=(116, 84, 58), top_light=(186, 146, 104),
            platform=(120, 88, 60), platform_dark=(80, 58, 38), platform_light=(160, 122, 86)),
    pool=(
        PoolEntry("diglett", 70, (26, 29)),
        PoolEntry("dugtrio", 30, (28, 31)),
    ),
    backdrop=Backdrop(art="digletts_cave.png", sky_top=(44, 32, 24), sky_bottom=(92, 68, 50),
                      hills=((102, 76, 56), (92, 68, 50)), field_far=(150, 114, 82), field_near=(130, 98, 70),
                      stripe=(140, 106, 76), shadow=(90, 66, 46)),
    ceiling=True,
    art="cave",
    cave=CaveLook(sky_top=(30, 22, 16), sky_bottom=(70, 52, 38), far_rock=(56, 42, 30), near_rock=(76, 56, 40),
                  glow=((150, 110, 60), (255, 220, 150)), wall="digletts_cave.png", dim=50),
    doorway="doorway_cave",
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
