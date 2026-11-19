"""Towns: flat, peaceful maps with buildings (no wild Pokémon). Doorways at
their edges lead onto routes. Arriving in a town heals the party (a
stand-in for Mom and Poké Centers).

Buildings are Pixellab sprites (see tileset.building). Poké Marts can be
entered (`Building.inside`, scenes/mart.py); going inside Poké Centers and
gyms comes later. Townsfolk (`Folk`, Pokémon living there) can be talked to:
they chat, and give and move on quests (quests.talk).
"""

import random
import zlib
from dataclasses import dataclass

from ..mechanics.items import ITEMS, Gear, Range
from ..mechanics.pokemon import EVOLUTIONS, SPECIES
from .level import EMPTY, ROWS, SOLID, TILE, Level
from .themes import LAVENDER, MEADOW, Theme

GROUND = 4  # tiles of ground


HOUSES, FUNCTIONAL = "houses.png", "functional_buildings.png"  # Pixellab sheets, 2×2 cells of 128×128
DEPT_STORE, MANSION = "dept_store.png", "celadon_mansion.png"  # Celadon's big buildings: 160×160 cells
GAME_CORNER = "game_corner.png"   # 128×128
BATTLE_TOWER = "battle_tower.png"  # 160×256
TOWER = "pokemon_tower.png"  # Lavender's Pokémon Tower: one 160×256 cell (tileset.BUILDING_CELLS)


@dataclass(frozen=True)
class Building:
    name: str                 # shown when standing in front of it ("" = an unnamed house)
    sprite: tuple   # (sheet, cell) or (sheet, cell, scale): see tileset.building
    col: int                  # left edge, in tiles
    # What Up there enters: "mart" (scenes/mart.py), "recruit" (a Recruitment
    # Center, scenes/recruit.py), "dept" (scenes/dept_store.py), "tower" (the
    # Battle Tower's lobby, scenes/battle_tower.py, once open), or "" (nothing).
    inside: str = ""
    note: str = ""  # what Up there says, if nothing else happens there (a shut gym)
    # A small tree grows over its door until this quest has started (then the
    # first Up there cuts it down: the Vermilion Gym and HM01 Cut).
    tree: str = ""

    @property
    def x(self) -> int:
        return self.col * TILE


ELDER = "elder"  # a Folk's species: the last form of the player's starter's line


@dataclass(frozen=True)
class Folk:
    """Someone living in a town: a Pokémon standing at `col`. Up next to
    them talks: a quest step or a quest they give (quests.talk), else the
    next of their `lines`."""
    key: str     # unique in the game (quest steps "talk" name it; Quest.giver)
    name: str    # shown over them when near; "{}" = their species' name ("Old {}")
    species: str  # their look (its idle animation), or ELDER
    col: int
    # Chat, one line per talk in turn; "{partner}" = the player's starter's name.
    lines: tuple[str, ...] = ()
    asleep: bool = False  # fast asleep (Snorlax): doesn't turn to face the player, Zzz over it
    npc: str = ""  # drawn as this NPC's idle animation (props/<npc>.png, tileset.npc_frames), not a species

    @property
    def x(self) -> float:
        return self.col * TILE + TILE / 2

    def species_for(self, starter: str) -> str:
        if self.species != ELDER:
            return self.species
        species = starter
        while species in EVOLUTIONS and EVOLUTIONS[species].into in SPECIES:
            species = EVOLUTIONS[species].into
        return species

    def name_for(self, starter: str) -> str:
        return self.name.format(SPECIES[self.species_for(starter)].name)


def building_mid(b: Building) -> float:
    """The x of a building's middle (where its door is)."""
    from .tileset import building  # (drawing: imported only when needed)
    return b.x + building(b.sprite)[0].get_width() / 2


@dataclass(frozen=True)
class Town:
    key: str
    name: str
    width: int                      # in tiles
    buildings: tuple[Building, ...]
    exits: tuple[tuple[str | int, str], ...]  # (where: "left"/"right" edge or a column, route key)
    home_col: int                   # where a new game starts and a fainted party wakes up
    board_col: int | None = None    # where its quest board stands (see quests.py)
    theme: Theme = MEADOW           # tiles and background
    mart: tuple[str, ...] = ()      # what its Poké Mart sells (medicine names)
    folk: tuple[Folk, ...] = ()     # who lives there (between the buildings)
    # Its Poké Mart's gear counter (Persian): the item levels and rarity
    # weights its pieces come at (None: no gear counter).
    gear: tuple[Range, tuple[tuple[str, int], ...]] | None = None

    def exit_to(self, route: str) -> str | int:
        """Where the exit onto `route` is ("left", "right" or a column)."""
        return next(where for where, r in self.exits if r == route)

    def level(self) -> Level:
        """The town's map: flat ground."""
        surface = [ROWS - GROUND] * self.width
        grid = [[SOLID if row >= surface[col] else EMPTY for col in range(self.width)] for row in range(ROWS)]
        return Level(self.theme, zlib.crc32(self.key.encode()), grid, surface)


GEAR_STOCK = 6  # pieces on Persian's counter at a time


def gear_stock(town: Town, seed: int, visit: int) -> list[Gear]:
    """The pieces on `town`'s gear counter for the player's `visit`-th
    stay there (the same every time for one game, `seed`): any item, at the
    town's item levels and rarities."""
    if not town.gear:
        return []
    rng = random.Random(zlib.crc32(f"{seed}/{town.key}/{visit}".encode()))
    levels, rarities = town.gear
    stock = []
    for _ in range(GEAR_STOCK):
        rarity = rng.choices([r for r, _ in rarities], weights=[w for _, w in rarities])[0]
        item = rng.choice([name for name, i in ITEMS.items() if i.drops_at(rarity)])
        stock.append(Gear.roll(item, rarity, rng, level=rng.randint(*levels)))
    return stock


def smith(col: int) -> Folk:
    """The smith: a Machamp at his anvil and furnace (from Lavender Town on,
    in the major towns). His quest (quests.SMITH, "A Hammer Fit for a
    Smith") opens his menu (scenes/smith.py)."""
    return Folk("smith", "Machamp", "machop", col, (
        "HAH! You call that a grip? Four arms, kid. Four.",
        "A good smith listens to the metal. Mostly it says CLANG.",
    ), npc="machamp_smith")


TOWNS = {t.key: t for t in [
    Town("pallet", "Pallet Town", 50, (
        Building("Your House", (HOUSES, 0), 7),
        Building("Rival's House", (HOUSES, 1), 18),
        Building("Professor Oak's Lab", (FUNCTIONAL, 3), 29),
    ), exits=(("right", "route_1"),), home_col=10, board_col=15,
       folk=(Folk("pallet_pidgey", "Pidgey", "pidgey", 41, (
           "Coo! Professor Oak's lab is just up the road.",
           "Route 1 is to the east. The grass there is full of Pidgey like me!",
       )),)),
    Town("viridian", "Viridian City", 82, (
        Building("", (HOUSES, 2), 8),
        Building("Pokémon Center", (FUNCTIONAL, 0), 17),
        Building("Poké Mart", (FUNCTIONAL, 2), 30, inside="mart"),
        Building("Recruitment Center", (HOUSES, 3), 42, inside="recruit"),
        Building("Viridian Gym", (FUNCTIONAL, 1), 53),
    ), exits=(("left", "route_1"), ("right", "viridian_forest"), (39, "route_22")), home_col=21, board_col=50,
       mart=("Potion", "Antidote", "Paralyze Heal", "Burn Heal"),
       gear=((5, 9), (("Common", 1),)),
       folk=(
           Folk("viridian_rattata", "Rattata", "rattata", 27, (
               "Squeak! The Recruitment Center up the road finds you new friends.",
               "Viridian Forest is to the east. Bugs everywhere. Yuck!",
           )),
           # The feud on Route 22: the Pidgey flock's leader and the Spearow's,
           # glaring at each other (quests feud_pidgey / feud_spearow).
           Folk("viridian_pidgeotto", "Pidgeotto", "pidgeotto", 62, (
               "The Spearow on Route 22 peck at my flock all day. Somebody should teach them manners.",
               "A Pidgey that stands up to those bullies grows strong. Strong enough to fly like me.",
           )),
           Folk("viridian_fearow", "Fearow", "fearow", 66, (
               "Hmph. The Pidgey think the sky belongs to them. My Spearow know better.",
               "A Spearow that wins its fights grows a long beak. Like mine.",
           )),
           # Evolution quests: Nidoran F -> Nidorina, Nidoran M -> Nidorino.
           Folk("viridian_nidorina", "Nidorina", "nidorina", 72, (
               "The Nidoran on Route 22 are such sweet little things. Somebody has to look after them.",
               "When your Nidoran F is ready to grow up (Lv16), come and see me.",
           )),
           Folk("viridian_nidorino", "Nidorino", "nidorino", 76, (
               "Hmph. My horn's sharper than any Spearow beak. Want to see?",
               "A Nidoran M with a strong horn (Lv16) can grow into one of us. Come back then.",
           )),
       )),
    Town("pewter", "Pewter City", 80, (
        Building("", (HOUSES, 3), 7),
        Building("Pokémon Center", (FUNCTIONAL, 0), 19),
        Building("Poké Mart", (FUNCTIONAL, 2), 32, inside="mart"),
        Building("Pewter Gym", (FUNCTIONAL, 1), 45),
        Building("Recruitment Center", (HOUSES, 2), 58, inside="recruit"),
    ), exits=(("left", "viridian_forest"), ("right", "route_3"), (67, "route_2_north")), home_col=23, board_col=15,
       mart=("Potion", "Super Potion", "Escape Rope", "Antidote", "Burn Heal", "Awakening", "Paralyze Heal"),
       gear=((11, 15), (("Common", 75), ("Uncommon", 25))),
       folk=(
           Folk("pewter_elder", "Old {}", ELDER, 29, (
               "I was young once, like your {partner}. Every Pokémon grows up in its own time.",
               "When your {partner} is strong enough (Lv16), come and see me. I'll show it the way.",
           )),
           Folk("pewter_geodude", "Geodude", "geodude", 55, (
               "Grr! The Boulder Gang runs the gym. Rock beats everything!",
               "Well... except Water and Grass. Don't tell anyone.",
           )),
           # Evolution quests: Metapod -> Butterfree, Kakuna -> Beedrill.
           Folk("pewter_butterfree", "Butterfree", "butterfree", 42, (
               "Flutter... The flowers here grow on rocks. Tough flowers, for a tough town.",
               "Every Metapod dreams of flying. When yours is ready (Lv10), come and see me.",
           )),
           Folk("pewter_beedrill", "Beedrill", "beedrill", 72, (
               "Bzzz. The hive is deep in Viridian Forest. Keep away, unless you're one of us.",
               "A Kakuna that serves the hive (Lv10) earns its stingers. Bzzz.",
           )),
       )),
    # The Pokémon Center at the foot of Mt. Moon (Gen 1: on Route 4), where
    # Route 3 ends: the last stop before the cave.
    Town("mt_moon", "Mt. Moon Pokémon Center", 44, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 18),
    ), exits=(("left", "route_3"), ("right", "mt_moon_cave")), home_col=14),
    # Route 4, out of Mt. Moon's far side: a stop at the cave's exit, where
    # the road on (route_4_east) runs down to Cerulean City.
    Town("route_4", "Route 4", 40, (), exits=(("left", "mt_moon_cave"), ("right", "route_4_east")), home_col=8),
    # Cerulean City: the water gym, Bill's road north over Nugget Bridge and
    # the burgled house.
    Town("cerulean", "Cerulean City", 100, (
        Building("Bike Shop", (HOUSES, 1), 6),
        Building("Pokémon Center", (FUNCTIONAL, 0), 18),
        Building("Poké Mart", (FUNCTIONAL, 2), 30, inside="mart"),
        Building("Cerulean Gym", (FUNCTIONAL, 1), 44),
        Building("Recruitment Center", (HOUSES, 3), 57, inside="recruit"),
        Building("Burgled House", (HOUSES, 0), 70),
    ), exits=(("left", "route_4_east"), ("right", "nugget_bridge"), (82, "route_5_south"), (89, "route_9")),
       home_col=22, board_col=41,
       mart=("Potion", "Super Potion", "Escape Rope", "Antidote", "Burn Heal", "Awakening", "Paralyze Heal",
             "Ice Heal"),
       gear=((17, 22), (("Common", 60), ("Uncommon", 40))),
       folk=(
           Folk("cerulean_sandshrew", "Sandshrew", "sandshrew", 15, (
               "Phew, you made it through Mt. Moon! Route 4 is all downhill from there.",
               "The Bike Shop sells bicycles. Nobody can afford one, though.",
           )),
           Folk("cerulean_psyduck", "Psyduck", "psyduck", 54, (
               "Psy...? The gym is full of water. And Water Pokémon. My head hurts.",
               "Someone broke into the house at the end of the street last night. Psyduck...",
           )),
           # Evolution quest: Abra -> Kadabra.
           Folk("cerulean_kadabra", "Kadabra", "kadabra", 67, (
               "...I bent this spoon with my mind. Yes, it's mine. No, you can't have it.",
               "An Abra sleeps most of the day. Yours will wake up for good once it's ready (Lv16).",
           )),
       )),
    # The top of Route 24, past Nugget Bridge: a stop where Route 25 turns
    # east to Bill's Sea Cottage.
    Town("route_24", "Route 24", 40, (), exits=(("left", "nugget_bridge"), ("right", "route_25")), home_col=10,
         folk=(Folk("route_24_pidgey", "Pidgey", "pidgey", 22, (
             "Coo! You crossed Nugget Bridge? Route 25 runs east from here, to the sea.",
             "A Pokémaniac called Bill lives by the sea. Strange noises come from his cottage.",
         )),)),
    # The bottom of Route 5: the Day Care, Saffron City's gate (shut) and the
    # Underground Path to Route 6 (being dug out: the next part).
    Town("route_5", "Route 5", 48, (
        Building("Day Care", (HOUSES, 1), 8),
    ), exits=(("left", "route_5_south"), ("right", "underground_path")), home_col=5,
       folk=(
           Folk("route_5_guard", "Gate Guard", "nidorino", 22, (
               "The gate to Saffron City is shut. Orders from up high. Nobody gets through.",
               "Phew, I'm parched. Standing guard all day is thirsty work...",
           )),
           Folk("route_5_diglett", "Diglett", "diglett", 34, (
               "Dig dig! We dug the Underground Path out again. It runs under Saffron City to Route 6.",
               "Dig...? Some of us stayed down in the tunnel. They don't like being stepped on. Dig dig!",
           )),
       )),
    # The top of Route 6, at the Underground Path's south end: Saffron
    # City's south gate (shut too), and the road on down to Vermilion.
    Town("route_6", "Route 6", 40, (), exits=(("left", "underground_path"), ("right", "route_6_south")), home_col=8,
         folk=(Folk("route_6_psyduck", "Psyduck", "psyduck", 22, (
             "Psy...? The gate to Saffron City is shut on this side too. Everyone has to go under it.",
             "Vermilion City is down the road. It smells of the sea... Psyduck likes that.",
         )),)),
    # Vermilion City, the port: Lt. Surge's gym (a little tree blocks its
    # door, as in Red/Blue: Cut comes from the S.S. Anne), the Pokémon Fan
    # Club and the dock where the S.S. Anne lies (the next part).
    Town("vermilion", "Vermilion City", 90, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 10),
        Building("Pokémon Fan Club", (HOUSES, 1), 22,
                 note="A sign on the door: \"Pokémon Fan Club. Members only. Meetings: whenever the chairman "
                      "feels like talking.\""),
        Building("Poké Mart", (FUNCTIONAL, 2), 34, inside="mart"),
        Building("Recruitment Center", (HOUSES, 3), 46, inside="recruit"),
        Building("Vermilion Gym", (FUNCTIONAL, 1), 60, tree="thunder_badge"),
        Building("", (HOUSES, 2), 72),
    ), exits=(("left", "route_6_south"), ("right", "ss_anne"), (81, "route_11")), home_col=14, board_col=57,
       mart=("Potion", "Super Potion", "Escape Rope", "Antidote", "Burn Heal", "Awakening", "Paralyze Heal",
             "Ice Heal"),
       gear=((22, 26), (("Common", 50), ("Uncommon", 45), ("Rare", 5))),
       folk=(
           Folk("vermilion_jigglypuff", "Jigglypuff", "jigglypuff", 31, (
               "Puff! The Pokémon Fan Club meets next door. The chairman talks about his Pokémon for hours.",
               "Jiggly... Everyone's here for the S.S. Anne. It only comes to port once a year!",
           )),
           Folk("vermilion_pikachu", "Pikachu", "pikachu", 69, (
               "Pika! Lt. Surge's gym is full of Electric Pokémon. He says only a full team can stand the shocks.",
               "The gym's leader, Lt. Surge, uses Electric Pokémon. Pika pika! Ground types don't mind them at all.",
           )),
           Folk("vermilion_shellder", "Shellder", "shellder", 84, (
               "Clack! The S.S. Anne is in port, at the dock just past here. Only passengers with a ticket may board.",
               "Clack clack. The sailors on the S.S. Anne have strong Pokémon from all over the world.",
           )),
       )),
    # The east end of Route 11: the mouth of Diglett's Cave, and the road on
    # to Route 12, where a Snorlax sleeps across it (as in Red/Blue: it takes
    # the Poké Flute to wake it, later).
    Town("route_11", "Route 11 Gate", 50, (), exits=(("left", "route_11"), (22, "digletts_cave")), home_col=6,
         folk=(
             Folk("route_11_diglett", "Diglett", "diglett", 28, (
                 "Dig! That's Diglett's Cave. We dug it all the way to Route 2, near Pewter City!",
                 "Dig dig... The Dugtrio deep inside don't like visitors. Watch your feet.",
             )),
             Folk("route_12_snorlax", "Snorlax", "snorlax", 43, (
                 "A huge Pokémon is fast asleep, sprawled right across the road to Route 12. It won't budge.",
                 "Snorlax is snoring loudly. Pushing, shouting... nothing wakes it. (Maybe something will, one "
                 "day.)",
             ), asleep=True),
         )),
    # Route 2's north end, at the far end of Diglett's Cave: Professor Oak's
    # aide waits by the cave with HM05 Flash (as in Red/Blue).
    Town("route_2", "Route 2", 40, (), exits=(("left", "route_2_north"), ("right", "digletts_cave")), home_col=30,
         folk=(Folk("route_2_aide", "Oak's Aide", "kadabra", 20, (
             "I'm one of Professor Oak's aides. I study Pokémon that live in caves... from the outside.",
             "Pewter City is just up the road. The Professor says hello!",
         )),)),
    # The Pokémon Center at the end of Route 9 (Gen 1: on Route 10), the
    # last stop before Rock Tunnel.
    Town("route_10", "Route 10 Pokémon Center", 44, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 18),
    ), exits=(("left", "route_9"), ("right", "rock_tunnel")), home_col=14,
         folk=(Folk("route_10_voltorb", "Voltorb", "voltorb", 32, (
             "Bzzt! The Power Plant is down the river from here. It's been shut for ages... Bzzt.",
             "Rock Tunnel is right there. Pitch dark! Even we Voltorb don't glow enough to light it.",
         )),)),
    # Lavender Town, at Rock Tunnel's south end: a small, quiet town, home
    # of the Pokémon Tower, where Pokémon are laid to rest (its ghosts are
    # for later: the tower is shut for now).
    Town("lavender", "Lavender Town", 72, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 6),
        Building("Poké Mart", (FUNCTIONAL, 2), 18, inside="mart"),
        Building("Pokémon Tower", (TOWER, 0), 28,
                 note="The Pokémon Tower, where Pokémon are laid to rest. A cold draught blows from the door... "
                      "Something moves inside, but you can't make out what. You'd need a way to see it."),
        Building("Mr. Fuji's House", (HOUSES, 0), 46,
                 note="Nobody's home. A note on the door: \"Gone to the Tower. Back soon. - Mr. Fuji\""),
    ), exits=(("left", "rock_tunnel"), ("right", "route_8")), home_col=14, board_col=41, theme=LAVENDER,
       mart=("Potion", "Super Potion", "Hyper Potion", "Revive", "Escape Rope", "Antidote", "Burn Heal", "Awakening",
             "Paralyze Heal", "Ice Heal"),
       gear=((30, 34), (("Common", 40), ("Uncommon", 45), ("Rare", 15))),
       folk=(
           Folk("lavender_drowzee", "Drowzee", "drowzee", 26, (
               "Drowzee... The tower's full of ghosts these days. They give even me bad dreams.",
               "Mr. Fuji looks after the Pokémon that lost their trainers. He's up in the tower every day.",
           )),
           Folk("lavender_jigglypuff", "Jigglypuff", "jigglypuff", 56, (
               "Puff... Lavender Town is so quiet. Everyone whispers here.",
               "Jiggly... Some say a lost Pokémon's mother still waits at the top of the tower.",
           )),
           smith(62),
       )),
    # The west end of Route 8: Saffron City's east gate (shut, its guard
    # thirsty, as in Red/Blue) and the Underground Path's doorway west.
    Town("route_8_gate", "Route 8 Gate", 44, (), exits=(("left", "route_8"), ("right", "underground_west")),
         home_col=8,
         folk=(Folk("route_8_guard", "Gate Guard", "nidorino", 24, (
             "Saffron City is shut. Nobody in, nobody out. I'm so thirsty I could drink a Psyduck...",
             "Want to go west? Take the Underground Path. It comes out on Route 7, right by Celadon City.",
         )),)),
    # Celadon City, the city of rainbow dreams (as in Red/Blue), in three
    # parts joined by doorways ("town:<key>" exits): the east end, where the
    # Underground Path comes up (the Pokémon Center and the huge Department
    # Store, its floors in scenes/dept_store.py); the square (the Game
    # Corner, Team Rocket's later; Erika's gym, the next part; the
    # Recruitment Center and the smith); and the west end (the Celadon
    # Mansion and the Battle Tower, opening later).
    Town("celadon", "Celadon City", 64, (
        Building("Pokémon Center", (FUNCTIONAL, 0), 6),
        Building("Department Store", (DEPT_STORE, 0), 19, inside="dept"),
    ), exits=(("right", "underground_west"), ("left", "town:celadon_square")), home_col=12, board_col=34,
       mart=("Potion", "Super Potion", "Hyper Potion", "Revive", "Escape Rope", "Antidote", "Burn Heal", "Awakening",
             "Paralyze Heal", "Ice Heal"),
       gear=((34, 38), (("Common", 30), ("Uncommon", 45), ("Rare", 25))),
       folk=(
           Folk("celadon_bellsprout", "Bellsprout", "bellsprout", 40, (
               "Sprout! The Department Store sells everything! Well, everything a Bellsprout needs. Water.",
               "Erika's gym is on the square, past the Game Corner. She waters every one of her Pokémon herself.",
           )),
           Folk("celadon_pidgeotto", "Pidgeotto", "pidgeotto", 52, (
               "Kaw! From the store's roof you can see all of Celadon. Even the Battle Tower out west!",
               "The drinks on the roof are the best in Kanto. Kaw! Thirsty gate guards would kill for one.",
           )),
       )),
    Town("celadon_square", "Celadon Square", 72, (
        Building("Game Corner", (GAME_CORNER, 0), 6,
                 note="The Game Corner. Slot machines jingle and clatter inside. A grumpy-looking man in black "
                      "stands by a poster at the back..."),
        Building("Celadon Gym", (FUNCTIONAL, 1), 22,
                 note="The Celadon Gym: a great glasshouse, overgrown with flowers."),
        Building("Recruitment Center", (HOUSES, 1), 36, inside="recruit"),
    ), exits=(("right", "town:celadon"), ("left", "town:celadon_west")), home_col=48,
       folk=(
           Folk("celadon_meowth", "Meowth", "meowth", 18, (
               "Meowth! The Game Corner pays out in coins. I've never seen anyone win, though...",
               "Mrrr. The men in black by the Game Corner don't smile much. Meowth doesn't like them.",
           )),
           Folk("celadon_oddish", "Oddish", "oddish", 46, (
               "Oddish! Erika's gym smells wonderful. All those flowers... Oddish could nap there forever.",
               "Ish... The square is the heart of Celadon. The rich folk live out west, by the Mansion.",
           )),
           smith(60),
       )),
    Town("celadon_west", "Celadon West End", 56, (
        Building("Celadon Mansion", (MANSION, 0), 6,
                 note="The Celadon Mansion. A sign: \"Residents only. The Pokémon here are very well fed.\""),
        Building("Battle Tower", (BATTLE_TOWER, 0), 30, inside="tower",
                 note="The Battle Tower. A banner over its doors: \"GRAND OPENING SOON! Twenty-five floors "
                      "of the toughest battles in Kanto!\""),
    ), exits=(("right", "town:celadon_square"),), home_col=24,
       folk=(Folk("celadon_clefairy", "Clefairy", "clefairy", 24, (
           "Clefairy! The Battle Tower goes up and up. They say only the strongest teams reach the top.",
           "Fairy... Someone pink and tiny was floating around the tower last night. Clefairy saw it!",
       )),)),
    # Bill's Sea Cottage at the end of Route 25. Bill got mixed up with a
    # Clefairy in his teleporter (quest "bill").
    Town("sea_cottage", "Sea Cottage", 40, (
        Building("Bill's Sea Cottage", (HOUSES, 2), 16,
                 note="Bill's Sea Cottage. Nobody answers the door."),
    ), exits=(("left", "route_25"),), home_col=8,
       folk=(Folk("bill_clefairy", "Clefairy", "clefairy", 28, (
           "Clefairy! (It hops around the garden.)",
           "Clefai...? (It keeps an eye on the cottage door.)",
       )),)),
]}
