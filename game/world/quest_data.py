"""The quests themselves (docs/quests.md): what `Step`s and `Quest`s are,
and every quest in `QUESTS`, the story's (following Red/Blue) and the side
jobs, plus a recruitment quest per Recruitment Center find. The rules that
run them (state, events, rewards) are in quests.py, which re-exports all of
this.
"""

from dataclasses import dataclass

from ..mechanics.items import BONE, RIBBON
from ..mechanics.pokemon import SPECIES
from .instance import RECRUITS, Recruit

SMITH = "smith"  # the smith Machamp's townsfolk key (the same in every town he works in)
FLY_SPECIES = ("pidgeotto", "pidgeot", "fearow")  # the birds that can learn to Fly (quest "learn_to_fly")

Line = tuple[str, str]  # (speaker, text) of a dialogue page


@dataclass(frozen=True)
class Step:
    # "visit" (a building in a town), "talk" (to a townsfolk), "defeat" (a
    # route's boss), "reach" (a town), "hunt" (defeat `count` of a species),
    # "collect" (`count` quest items), "hand_in" (at any quest board),
    # "evolve" (a Pokémon, from the party screen, once it has the level) or
    # "lead_wins" (win `count` wild battles on `route` or later with one of
    # `species` leading the party)
    kind: str
    # visit: the building's name; talk: the townsfolk's key (towns.Folk);
    # defeat: the route key; reach: the town key; hunt: the species key;
    # collect: the item's name; evolve: the species key that evolves
    target: str
    text: str     # the objective, as shown on the map and in the quest log
    town: str = ""  # visit: the town the building is in
    dialogue: tuple[Line, ...] = ()  # shown when the step is done
    gives: tuple[str, ...] = ()      # key items received ...
    takes: tuple[str, ...] = ()      # ... and handed over
    count: int = 1                   # hunt / collect: how many
    # collect: each defeated Pokémon of `species` in a won battle on
    # `route` drops one with `chance` %.
    route: str = ""
    species: tuple[str, ...] = ()
    chance: int = 0
    # visit: what Up at the building says while the quest is still at an
    # earlier step (a hint at what to do first), `early_text`.
    before: str = ""
    # talk with `takes`: the step only happens once those key items are in
    # the bag; until then, talking says this instead.
    waiting: tuple[Line, ...] = ()
    # talk / defeat: other targets that do it too (either Snorlax). A talk
    # step done with one remembers it (`chosen`): a later defeat step then
    # only takes the route walked from that townsfolk (`Route.folk`).
    alt: tuple[str, ...] = ()
    # talk with `alt`: who joins, by which townsfolk was talked to (the
    # Fighting Dojo's Hitmonlee or Hitmonchan): (folk, species, level, what's
    # said then).
    joins: tuple[tuple[str, str, int, str], ...] = ()
    # talk: "out" sends the player's Pokémon away and theirs joins on loan;
    # "back" swaps back, the player's evolved (a swap quest, world/swaps.py).
    swap: str = ""

    @property
    def targets(self) -> tuple[str, ...]:
        return (self.target,) + self.alt


def hunt(species: str, count: int, where: str) -> Step:
    """Defeat `count` of `species` (anywhere; `where` says where they live)."""
    return Step("hunt", species, f"Defeat {count} {SPECIES[species].name} ({where})", count=count)


def collect(item: str, count: int, route: str, species: tuple[str, ...], chance: int, where: str,
            plural: str = "") -> Step:
    """Collect `count` of `item` (`plural`: its plural, if not just + "s"),
    dropped by `species` on `route` or any route after it (`instance.STORY_ORDER`)."""
    return Step("collect", item, f"Collect {count} {plural or item + 's'} ({where} or later)", count=count,
                route=route, species=species, chance=chance)


HAND_IN = Step("hand_in", "", "Hand it in at any quest board")


@dataclass(frozen=True)
class Quest:
    key: str
    name: str
    summary: str
    steps: tuple[Step, ...]
    money: int  # Poké Dollars, given when it's done ...
    xp: int     # ... and XP for each party member
    board: str = ""                  # the town whose quest board posts it ("" = starts by itself)
    # Quests that must be done first; an entry that's a tuple of keys is done
    # once any one of them is (two ways to the same place).
    requires: tuple[str | tuple[str, ...], ...] = ()
    # Only on offer while this holds (as `Route.needs`: e.g. a boss beaten,
    # ("boss:snorlax_wakes_east", "beaten")).
    needs: tuple[str, str] | None = None
    starts_in: str = ""              # a quest that starts by itself: only on arriving in this town
    giver: str = ""                  # starts by talking to this townsfolk (towns.Folk key) ...
    offer: tuple[Line, ...] = ()     # ... who says this
    excludes: tuple[str, ...] = ()   # not on offer while one of these is active (picking a side)
    needs_species: tuple[str, ...] = ()  # only on offer with one of these in the party or reserve
    unlock: tuple[str, int] | None = None  # (line, n): only once n of that line are defeated (recruitment)
    # Items given too: ("medicine", name, count), ("gear", item, rarity, level)
    # or ("pokemon", species, level): it joins the party (or the reserve).
    rewards: tuple[tuple, ...] = ()
    done_dialogue: tuple[Line, ...] = ()  # shown when it's done (after the last step's)
    # Starts when this key item drops: (item, route, species, chance %): in a
    # won battle on the route, each defeated Pokémon of those species drops
    # it with that chance (until it has dropped once).
    drop: tuple[str, str, tuple[str, ...], int] | None = None

    @property
    def evolves(self) -> str:
        """An evolution quest: the species it evolves ("" if it isn't one).
        It's only on offer (or drops its item) once that species is in the
        team at the level it evolves at."""
        return next((s.target for s in self.steps if s.kind == "evolve"), "")


# What the player sees when the Thick Bone turns up (the Pokémon Tower's
# Marowak; dev mode's item maker too).
BONE_FOUND = (("", f"You found a {BONE}! It's heavier than stone, and not a scratch on it."),
              ("", "Something this strong must be good for more than gathering dust..."))


QUESTS = {q.key: q for q in [
    Quest(
        "oaks_parcel", "Oak's Parcel",
        "The Viridian Poké Mart has a parcel for Professor Oak and needs someone to take it to Pallet Town.",
        board="viridian",
        steps=(
            Step("visit", "Poké Mart", "Pick up the parcel at the Viridian Poké Mart", town="viridian",
                 dialogue=(("Meowth", "Meowth! You came from Pallet Town? Then you know Professor Oak, meow!"),
                           ("Meowth", "His order came in. Will you take it to him?"),
                           ("", "You received Oak's Parcel!")),
                 gives=("Oak's Parcel",)),
            Step("visit", "Professor Oak's Lab", "Deliver Oak's Parcel to Professor Oak (Pallet Town)",
                 town="pallet",
                 dialogue=(("Oak", "Oh, that's the custom Poké Ball I ordered! Thank you!"),
                           ("Oak", "Here: take this Pokédex. It records every Pokémon you see."),
                           ("", "You received the Pokédex!"),
                           ("Oak", "Your rival went west of Viridian City, to Route 22. "
                                   "He said he wants to battle you!")),
                 takes=("Oak's Parcel",), gives=("Pokédex",)),
        ),
        money=300, xp=150,
        rewards=(("medicine", "Potion", 5),),
    ),
    Quest(
        "rival_22", "Rival on Route 22",
        "Your rival is waiting for you on Route 22, west of Viridian City.",
        requires=("oaks_parcel",),
        steps=(Step("defeat", "route_22", "Defeat your rival on Route 22 (west of Viridian City)",
                    gives=(RIBBON,)),),
        money=600, xp=300,
        rewards=(("medicine", "Super Potion", 2), ("gear", None, "Uncommon", 9)),
        done_dialogue=(("Rival", "What? I can't believe I lost! I'm off to Pewter City. Smell ya later!"),
                       ("Prof. Oak", "(over the Pokédex) Splendid battle! A team that wins together grows "
                                     "together. I'm sending you something special."),
                       ("", "You received a Teamwork Ribbon! A special item: use it in the bag (Key items), and "
                            "one more Pokémon can fight at your side.")),
    ),
    Quest(
        "forest_bugs", "Bugs in the Forest",
        "A giant Caterpie is blocking the path through Viridian Forest. Clear the way to Pewter City.",
        board="viridian", requires=("oaks_parcel",),
        steps=(Step("defeat", "viridian_forest", "Defeat the giant Caterpie in Viridian Forest"),),
        money=500, xp=350,
        rewards=(("medicine", "Super Potion", 2), ("gear", None, "Common", 10)),
    ),

    # Board jobs: defeat a number of one species, or collect quest items
    # that drop on the route out of town; handed in at any board.
    Quest(
        "pest_control", "Pest Control",
        "Rattata keep chewing through the fences of Pallet Town. Thin them out on Route 1.",
        board="pallet",
        steps=(hunt("rattata", 6, "Route 1"), HAND_IN),
        money=300, xp=150,
    ),
    Quest(
        "soft_feathers", "Soft Feathers",
        "Mom wants Pidgey feathers to stuff a new pillow. Pidgey on Route 1 sometimes drop one.",
        board="pallet",
        steps=(collect("Pidgey Feather", 5, "route_1", ("pidgey",), 50, "Pidgey on Route 1"), HAND_IN),
        money=400, xp=150,
    ),
    Quest(
        "spearow_trouble", "Spearow Trouble",
        "A flock of Spearow on Route 22 pecks at anyone passing by. Show them who's boss.",
        board="viridian", requires=("oaks_parcel",),
        steps=(hunt("spearow", 4, "Route 22"), HAND_IN),
        money=450, xp=200,
    ),
    Quest(
        "nidoran_horns", "Shed Horns",
        "A Viridian collector pays well for the little horns Nidoran shed on Route 22.",
        board="viridian", requires=("oaks_parcel",),
        steps=(collect("Nidoran Horn", 6, "route_22", ("nidoran_f", "nidoran_m"), 40, "Nidoran on Route 22"),
               HAND_IN),
        money=500, xp=250,
    ),
    Quest(
        "bug_silk", "Bug Silk",
        "The Poké Mart weaves its bandanas from the silk of Caterpie and Metapod in Viridian Forest.",
        board="viridian", requires=("oaks_parcel",),
        steps=(collect("Silk Thread", 5, "viridian_forest", ("caterpie", "metapod"), 40,
                       "Caterpie and Metapod in Viridian Forest"), HAND_IN),
        money=600, xp=250,
    ),
    Quest(
        "poison_barbs", "Poison Barbs",
        "Pewter's Pokémon Center makes Antidotes from Weedle and Kakuna barbs. Bring some from Viridian Forest.",
        board="pewter",
        steps=(collect("Poison Barb", 6, "viridian_forest", ("weedle", "kakuna"), 35,
                       "Weedle and Kakuna in Viridian Forest"), HAND_IN),
        money=700, xp=500,
    ),
    Quest(
        "forest_sparks", "Sparks in the Forest",
        "Someone saw sparks between the trees of Viridian Forest. Track down the Pikachu behind them.",
        board="pewter",
        steps=(hunt("pikachu", 3, "Viridian Forest"), HAND_IN),
        money=800, xp=600,
    ),

    # Evolutions: each is unlocked by its quest (`can_evolve`); after that,
    # the line evolves by level as usual. Those not listed can't evolve yet.
    Quest(
        "evolve_metapod", "Cocoon of Steel",
        "An empty Metapod shell, hard as steel. A Caterpie strong enough (Lv7) could learn from it how to "
        "harden into a Metapod.",
        drop=("Metapod Shell", "viridian_forest", ("caterpie", "metapod"), 15),
        steps=(Step("evolve", "caterpie", "Show the Metapod Shell to a Caterpie at Lv7+ (party screen: E)",
                    takes=("Metapod Shell",)),),
        money=200, xp=100,
    ),
    Quest(
        "evolve_kakuna", "Poison Cocoon",
        "An empty Kakuna shell, still smelling of poison. A Weedle strong enough (Lv7) could learn from it how "
        "to wrap itself up as a Kakuna.",
        drop=("Kakuna Shell", "viridian_forest", ("weedle", "kakuna"), 15),
        steps=(Step("evolve", "weedle", "Show the Kakuna Shell to a Weedle at Lv7+ (party screen: E)",
                    takes=("Kakuna Shell",)),),
        money=200, xp=100,
    ),

    # Their next forms, and Rattata's: each from a townsfolk of that species.
    Quest(
        "evolve_butterfree", "Spread Your Wings",
        "The Butterfree in Pewter City says your Metapod is ready to hatch, once the skies are safe for it.",
        giver="pewter_butterfree",
        offer=(("Butterfree", "Your Metapod is ready to hatch. I can feel it. But a cocoon only opens when it's "
                              "safe."),
               ("Butterfree", "Pidgey hunt Caterpie and Metapod. Chase off 6 of them, then come back to me.")),
        steps=(hunt("pidgey", 6, "Route 1, Routes 24 and 25"),
               Step("talk", "pewter_butterfree", "Tell Butterfree the skies are safe (Pewter City)", town="pewter",
                    dialogue=(("Butterfree", "The Pidgey keep their distance now. Your Metapod can feel it too."),
                              ("Butterfree", "Go on. Spread your wings!"))),
               Step("evolve", "metapod", "Evolve your Metapod into Butterfree (party screen: E)")),
        money=400, xp=300,
    ),
    Quest(
        "evolve_beedrill", "The Hive",
        "The Beedrill in Pewter City says a Kakuna earns its stingers by serving the hive, and facing its "
        "Queen.",
        giver="pewter_beedrill",
        offer=(("Beedrill", "Bzzz. Your Kakuna is ready to break out. But only one that has served the hive gets its "
                            "stingers."),
               ("Beedrill", "Bring 4 Royal Jelly from the Weedle and Kakuna of Viridian Forest.")),
        steps=(collect("Royal Jelly", 4, "viridian_forest", ("weedle", "kakuna"), 30,
                       "Weedle and Kakuna in Viridian Forest", "Royal Jelly"),
               Step("talk", "pewter_beedrill", "Bring the Royal Jelly to Beedrill (Pewter City)", town="pewter",
                    dialogue=(("Beedrill", "Good jelly. The hive will remember."),
                              ("Beedrill", "Now face the Hive Queen in her thicket. Talk to me when you're ready."))),
               Step("defeat", "hive_queen", "Beat the Hive Queen in her thicket (talk to Beedrill, Pewter City)",
                    dialogue=(("Beedrill", "The Queen bows to your Kakuna. It has earned its stingers. Bzzz!"),)),
               Step("evolve", "kakuna", "Evolve your Kakuna into Beedrill (party screen: E)")),
        money=600, xp=450,
    ),
    Quest(
        "evolve_raticate", "Rat King",
        "Viridian City's Rattata says the Rat King rules the burrows by Route 1. A Rattata that beats him could "
        "grow into a Raticate.",
        giver="viridian_rattata",
        offer=(("Rattata", "Squeak! Your Rattata has big teeth now. Big enough to take on the Rat King?"),
               ("Rattata", "First show the snakes who's boss: beat 5 Ekans on Routes 3 and 4. Then come back.")),
        steps=(hunt("ekans", 5, "Routes 3 and 4"),
               Step("talk", "viridian_rattata", "Report to Rattata (Viridian City)", town="viridian",
                    dialogue=(("Rattata", "Snakes beaten! Squeak!"),
                              ("Rattata", "The Rat King's gang lives in the burrows. Talk to me when you're ready."))),
               Step("defeat", "rat_den", "Beat the Rat King in his burrows (talk to Rattata, Viridian City)",
                    dialogue=(("Rattata", "The Rat King is beaten! Your Rattata is the king now!"),)),
               Step("evolve", "rattata", "Evolve your Rattata into Raticate (party screen: E)")),
        money=700, xp=500,
    ),
    # Golbat, Arbok, Persian and Machoke: the same way (hunt, report, beat
    # the line's giant leader on its home ground, evolve).
    Quest(
        "evolve_golbat", "Wings in the Dark",
        "The Golbat at the Route 6 stop says a Zubat grows into a Golbat by ruling a roost. The Night Swarm's "
        "roost is the one to take.",
        giver="route_6_golbat",
        offer=(("Golbat", "Skree! Your Zubat flaps well. But a Golbat needs a roost of its own."),
               ("Golbat", "Diglett keep tunnelling into the Underground Path's ceiling and bringing our roosts down. "
                          "Chase off 6 of them. Then come back.")),
        steps=(hunt("diglett", 6, "the Underground Path"),
               Step("talk", "route_6_golbat", "Report to Golbat (the Route 6 stop)", town="route_6",
                    dialogue=(("Golbat", "Skreee! The ceiling holds. Now, the Night Swarm's roost..."),
                              ("Golbat", "Their leader has the biggest mouth in Kanto. Talk to me when you're "
                                         "ready."))),
               Step("defeat", "golbat_roost", "Beat the Night Swarm in its roost (talk to Golbat, the Route 6 stop)",
                    dialogue=(("Golbat", "The roost is yours! Your Zubat's wings will never be the same."),)),
               Step("evolve", "zubat", "Evolve your Zubat into Golbat (party screen: E)")),
        money=700, xp=500,
    ),
    Quest(
        "evolve_arbok", "The Coil Clan",
        "The Arbok sunning itself at Mt. Moon's exit says an Ekans grows into an Arbok by facing the Coil "
        "Clan in their pit.",
        giver="route_4_arbok",
        offer=(("Arbok", "Hsss... Your Ekans is long enough to coil properly now. Is it brave enough?"),
               ("Arbok", "The Sandshrew on Routes 3 and 4 keep digging up our sunning rocks. Drive off 6 of them.")),
        steps=(hunt("sandshrew", 6, "Routes 3 and 4"),
               Step("talk", "route_4_arbok", "Report to Arbok (Route 4, by Mt. Moon)", town="route_4",
                    dialogue=(("Arbok", "Ssss. The rocks are ours again. Now, the Coil Clan..."),
                              ("Arbok", "Their leader's hood frightens even me. Talk to me when you're ready."))),
               Step("defeat", "snake_pit", "Beat the Coil Clan in the Snake Pit (talk to Arbok, Route 4)",
                    dialogue=(("Arbok", "Hsss! Your Ekans stared down the Coil Clan. Its hood is coming in."),)),
               Step("evolve", "ekans", "Evolve your Ekans into Arbok (party screen: E)")),
        money=700, xp=500,
    ),
    Quest(
        "evolve_persian", "Nine Lives",
        "Vermilion City's Persian says a Meowth becomes a Persian by beating the Alley Cats at their own "
        "game.",
        giver="vermilion_persian",
        offer=(("Persian", "Mrrrow. Your Meowth has... potential. Rough around the whiskers, but potential."),
               ("Persian", "Those Mankey on Routes 5 and 6 keep stealing from my saucer. Teach 6 of them "
                           "manners.")),
        steps=(hunt("mankey", 6, "Routes 5 and 6"),
               Step("talk", "vermilion_persian", "Report to Persian (Vermilion City)", town="vermilion",
                    dialogue=(("Persian", "Purr... Adequate. Now the Alley Cats. They think the docks are theirs."),
                              ("Persian", "Their boss has been sharpening his claws all week. Talk to me when "
                                          "you're ready."))),
               Step("defeat", "alley_cats", "Beat the Alley Cats (talk to Persian, Vermilion City)",
                    dialogue=(("Persian", "Mrrrow! The alley bows to your Meowth. It's ready to become one of "
                                          "us."),)),
               Step("evolve", "meowth", "Evolve your Meowth into Persian (party screen: E)")),
        money=900, xp=700,
    ),
    Quest(
        "evolve_machoke", "Heavy Lifting",
        "The smith's apprentice in Lavender Town, a Machoke, says a Machop grows into a Machoke by out-lifting "
        "the Iron Lifters on their training grounds.",
        giver="lavender_machoke",
        offer=(("Machoke", "HUP! Your Machop's got muscles! Not as big as mine. Yet."),
               ("Machoke", "First, weights! Beat 6 Geodude in Rock Tunnel. Best boulders in Kanto. Then come "
                           "back.")),
        steps=(hunt("geodude", 6, "Rock Tunnel"),
               Step("talk", "lavender_machoke", "Report to Machoke (Lavender Town)", town="lavender",
                    dialogue=(("Machoke", "HUP HUP! Now the Iron Lifters. They train out past Route 9."),
                              ("Machoke", "Their leader can lift a Snorlax. Twice. Talk to me when you're "
                                          "ready."))),
               Step("defeat", "training_grounds", "Out-lift the Iron Lifters (talk to Machoke, Lavender Town)",
                    dialogue=(("Machoke", "HUUUP! Your Machop out-lifted them all! Time for a growth spurt."),)),
               Step("evolve", "machop", "Evolve your Machop into Machoke (party screen: E)")),
        money=900, xp=700,
    ),
    # Batch 2 of the overdue evolutions: Sandslash, Parasect, Graveler, Hypno.
    Quest(
        "evolve_sandslash", "Sharp as Spines",
        'The Sandslash by the Mt. Moon Pokémon Center says a Sandshrew grows its spines by facing the Spike Pack in its burrows.',
        giver="mt_moon_sandslash",
        offer=(("Sandslash", "Shhh-rrk. Your Sandshrew's claws are long enough. Are its spines?"),
               ("Sandslash", "The Ekans on Routes 3 and 4 keep slithering into our burrows. Drive off 6 of them.")),
        steps=(hunt("ekans", 6, "Routes 3 and 4"),
               Step("talk", "mt_moon_sandslash", "Report to Sandslash (the Mt. Moon Pokémon Center)", town="mt_moon",
                    dialogue=(("Sandslash", "Shrrk! The burrows are ours again. Now, the Spike Pack."),
                              ("Sandslash", "Their leader's spines are sharper than mine. Talk to me when you're ready."))),
               Step("defeat", "spike_burrows", "Beat the Spike Pack in the Spike Burrows (talk to Sandslash, the Mt. Moon Pokémon Center)",
                    dialogue=(("Sandslash", "Your Sandshrew held its ground! Its back is already prickling."),)),
               Step("evolve", "sandshrew", "Evolve your Sandshrew into Sandslash (party screen: E)")),
        money=700, xp=500,
    ),
    Quest(
        "evolve_parasect", "The Mushroom Decides",
        "The Parasect at the Route 5 stop says a Paras grows into a Parasect once its mushroom is strong enough to win the Spore Colony's respect.",
        giver="route_5_parasect",
        offer=(("Parasect", "...Your Paras's mushroom is ready. The mushroom told me so."),
               ("Parasect", "...Bellsprout keep stealing the best soil on Routes 24, 25 and 5. Chase off 6 of them.")),
        steps=(hunt("bellsprout", 6, "Routes 24, 25 and 5"),
               Step("talk", "route_5_parasect", "Report to Parasect (the Route 5 stop)", town="route_5",
                    dialogue=(("Parasect", "...The soil is ours. Now, the Spore Colony in Mushroom Hollow."),
                              ("Parasect", "...Their leader's mushroom is the biggest anyone has seen. Talk to me when you're ready."))),
               Step("defeat", "mushroom_hollow", "Beat the Spore Colony in Mushroom Hollow (talk to Parasect, the Route 5 stop)",
                    dialogue=(("Parasect", "...The mushroom approves. Your Paras is ready."),)),
               Step("evolve", "paras", "Evolve your Paras into Parasect (party screen: E)")),
        money=800, xp=600,
    ),
    Quest(
        "evolve_graveler", "Rolling Stones",
        'The Graveler at the Route 10 Pokémon Center says a Geodude grows two more arms by out-rolling the Boulder Rollers in their quarry.',
        giver="route_10_graveler",
        offer=(("Graveler", "Grrrock. Your Geodude's a solid one. Solid enough for two more arms?"),
               ("Graveler", "The Machop in Rock Tunnel keep using us for training weights. Beat 6 of them.")),
        steps=(hunt("machop", 6, "Rock Tunnel"),
               Step("talk", "route_10_graveler", "Report to Graveler (the Route 10 Pokémon Center)", town="route_10",
                    dialogue=(("Graveler", "Ha! No more lifting us. Now, the Boulder Rollers' quarry."),
                              ("Graveler", "Their leader rolls like a landslide. Talk to me when you're ready."))),
               Step("defeat", "rumbling_quarry", "Beat the Boulder Rollers in the Rumbling Quarry (talk to Graveler, the Route 10 Pokémon Center)",
                    dialogue=(("Graveler", "Grrrock! Your Geodude rolled right over them. Time to grow some arms."),)),
               Step("evolve", "geodude", "Evolve your Geodude into Graveler (party screen: E)")),
        money=800, xp=600,
    ),
    Quest(
        "evolve_hypno", "Sweet Dreams",
        'The Hypno at the Route 11 Gate says a Drowzee becomes a Hypno by out-staring the Dream Eaters in their hollow.',
        giver="route_11_hypno",
        offer=(("Hypno", "Your Drowzee has a hungry look. Hungry for dreams... and for a pendulum of its own."),
               ("Hypno", "The Spearow on Route 11 screech all night and wake everyone up. Silence 6 of them.")),
        steps=(hunt("spearow", 6, "Route 11"),
               Step("talk", "route_11_hypno", "Report to Hypno (the Route 11 Gate)", town="route_11",
                    dialogue=(("Hypno", "Ahh, quiet. Everyone sleeps, and dreams. Now, the Dream Eaters."),
                              ("Hypno", "They gather in a hollow off Route 11. Talk to me when you're ready."))),
               Step("defeat", "dreamers_hollow", "Beat the Dream Eaters in Dreamer's Hollow (talk to Hypno, the Route 11 Gate)",
                    dialogue=(("Hypno", "Your Drowzee stared them all down. Here, look at the pendulum... it's time."),)),
               Step("evolve", "drowzee", "Evolve your Drowzee into Hypno (party screen: E)")),
        money=900, xp=700,
    ),
    # Batch 3: Primeape, Electrode, Venomoth, Golduck.
    Quest(
        "evolve_primeape", "Anger Management",
        "The Primeape at the Route 8 Gate says a Mankey becomes a Primeape by out-raging the Rage Brawlers in their ring.",
        giver="route_8_primeape",
        offer=(("Primeape", "GRRR! Your Mankey! It's got a temper! I LIKE IT!"),
               ("Primeape", "Those Growlithe on Route 8 bark at me ALL DAY. Beat 6 of them. QUIETLY. ...Please.")),
        steps=(hunt("growlithe", 6, "Route 8"),
               Step("talk", "route_8_primeape", "Report to Primeape (the Route 8 Gate)", town="route_8_gate",
                    dialogue=(("Primeape", "Ahh... silence. Now! The Rage Brawlers! In their ring!"),
                              ("Primeape", "Their boss is even angrier than me. Talk to me when you're ready. GRR."))),
               Step("defeat", "brawlers_ring", "Beat the Rage Brawlers in the Brawlers' Ring (talk to Primeape, the Route 8 Gate)",
                    dialogue=(("Primeape", "RAAAH! Your Mankey's fury is magnificent! It's time!"),)),
               Step("evolve", "mankey", "Evolve your Mankey into Primeape (party screen: E)")),
        money=900, xp=700,
    ),
    Quest(
        "evolve_electrode", "Full Charge",
        "The Electrode at the Route 10 Pokémon Center says a Voltorb becomes an Electrode by out-sparking the Spark Rollers on their field.",
        giver="route_10_electrode",
        offer=(("Electrode", "BZZRT! Your Voltorb's buzzing nicely. But can it hold a real charge?"),
               ("Electrode", "Sandshrew on Routes 9 and 11 keep digging through the power lines. Stop 6 of them.")),
        steps=(hunt("sandshrew", 6, "Routes 9 and 11"),
               Step("talk", "route_10_electrode", "Report to Electrode (the Route 10 Pokémon Center)", town="route_10",
                    dialogue=(("Electrode", "Bzzt! The lines hum again. Now, the Spark Rollers on the Static Field."),
                              ("Electrode", "Their leader's charged to bursting. Talk to me when you're ready."))),
               Step("defeat", "static_field", "Beat the Spark Rollers on the Static Field (talk to Electrode, the Route 10 Pokémon Center)",
                    dialogue=(("Electrode", "BZZRRRT! Your Voltorb's crackling all over. It's ready to grow!"),)),
               Step("evolve", "voltorb", "Evolve your Voltorb into Electrode (party screen: E)")),
        money=900, xp=700,
    ),
    Quest(
        "evolve_venomoth", "Dust to Wings",
        "The Venomoth at the top of Route 24 says a Venonat earns its wings by facing the Dust Wings in their glade.",
        giver="route_24_venomoth",
        offer=(("Venomoth", "Flutter... Your Venonat's eyes are so bright. It sees what's coming, doesn't it?"),
               ("Venomoth", "The Pidgey on Routes 24 and 25 hunt us at dusk. Chase off 6 of them.")),
        steps=(hunt("pidgey", 6, "Routes 24 and 25"),
               Step("talk", "route_24_venomoth", "Report to Venomoth (the top of Route 24)", town="route_24",
                    dialogue=(("Venomoth", "Flutter... The skies are safe again. Now, the Dust Wings in the Moth Glade."),
                              ("Venomoth", "Their leader's dust can put a Snorlax to sleep. Talk to me when you're ready."))),
               Step("defeat", "moth_glade", "Beat the Dust Wings in the Moth Glade (talk to Venomoth, the top of Route 24)",
                    dialogue=(("Venomoth", "Your Venonat's back is itching, isn't it? Those are wings coming."),)),
               Step("evolve", "venonat", "Evolve your Venonat into Venomoth (party screen: E)")),
        money=900, xp=700,
    ),
    Quest(
        "evolve_golduck", "Clear Headed",
        "The Golduck in Cerulean City says a Psyduck's headache clears for good once it out-swims the Headache Club on their pond.",
        giver="cerulean_golduck",
        offer=(("Golduck", "Duck. Your Psyduck's holding its head again. I remember that feeling."),
               ("Golduck", "The Meowth on Routes 6 and 8 keep fishing in our pond. Shoo off 6 of them.")),
        steps=(hunt("meowth", 6, "Routes 6 and 8"),
               Step("talk", "cerulean_golduck", "Report to Golduck (Cerulean City)", town="cerulean",
                    dialogue=(("Golduck", "Duck. The fish are safe. Now, the Headache Club on Headache Pond."),
                              ("Golduck", "Their leader swims faster than a Seaking. Talk to me when you're ready."))),
               Step("defeat", "duck_pond", "Beat the Headache Club on Headache Pond (talk to Golduck, Cerulean City)",
                    dialogue=(("Golduck", "Your Psyduck's headache... it's gone quiet. It's time."),)),
               Step("evolve", "psyduck", "Evolve your Psyduck into Golduck (party screen: E)")),
        money=1000, xp=800,
    ),
    Quest(
        "evolve_nidorino", "Horn Rush",
        "Viridian City's Nidorino says a Nidoran M sharpens its horn on its rivals. Beat the Horn Brothers in "
        "their hollow, and yours could grow into a Nidorino.",
        giver="viridian_nidorino",
        offer=(("Nidorino", "That Nidoran of yours has a horn worth sharpening. Spearow keep pecking at ours, though."),
               ("Nidorino", "Beat 6 Spearow on Route 22. Then we'll talk.")),
        steps=(hunt("spearow", 6, "Route 22"),
               Step("talk", "viridian_nidorino", "Report to Nidorino (Viridian City)", town="viridian",
                    dialogue=(("Nidorino", "Good. Now for the real test: the Horn Brothers rule Horn Hollow."),
                              ("Nidorino", "Their leader's horn is twice the size of mine. Talk to me when "
                                           "you're ready."))),
               Step("defeat", "horn_hollow", "Beat the Horn Brothers in Horn Hollow (talk to Nidorino, Viridian City)",
                    dialogue=(("Nidorino", "Ha! Your Nidoran's horn is the sharpest in the hollow now."),)),
               Step("evolve", "nidoran_m", "Evolve your Nidoran M into Nidorino (party screen: E)")),
        money=600, xp=450,
    ),
    Quest(
        "evolve_gloom", "Sweet Stench",
        "Cerulean City's Gloom says an Oddish grows into a Gloom by learning to make a smell all its own. Its "
        "teacher: the Stench Patch's leader, out past Route 25.",
        giver="cerulean_gloom",
        offer=(("Gloom", "Glooom... Your Oddish is ready to smell like a real Gloom. It needs to know what's sweet."),
               ("Gloom", "Bring me 5 drops of Sweet Nectar. The Oddish and Bellsprout up north carry it.")),
        steps=(collect("Sweet Nectar", 5, "nugget_bridge", ("oddish", "bellsprout"), 35,
                       "Oddish and Bellsprout, from Route 24 on", "drops of Sweet Nectar"),
               Step("talk", "cerulean_gloom", "Bring the Sweet Nectar to Gloom (Cerulean City)", town="cerulean",
                    dialogue=(("Gloom", "Mmm, sweet. Now the stink! The Stench Patch's leader is the smelliest Gloom "
                                        "of all."),
                              ("Gloom", "Beat its patch, and your Oddish will have learned. Talk to me when "
                                        "you're ready."))),
               Step("defeat", "stench_patch", "Beat the Stench Patch (talk to Gloom, Cerulean City)",
                    dialogue=(("Gloom", "Pee-yew! Your Oddish stinks wonderfully now. It's a Gloom at heart!"),)),
               Step("evolve", "oddish", "Evolve your Oddish into Gloom (party screen: E)")),
        money=900, xp=700,
    ),
    Quest(
        "evolve_weepinbell", "Pitcher's Appetite",
        "The Route 24 Weepinbell says a Bellsprout grows into a Weepinbell by catching its fill of bugs, and "
        "by out-lashing the Vine Lashers in Pitcher Grove.",
        giver="route_24_weepinbell",
        offer=(("Weepinbell", "Weepin'! Your Bellsprout's vines are long enough. But is it hungry enough?"),
               ("Weepinbell", "Catch 6 Venonat on Route 25. Then we'll see.")),
        steps=(hunt("venonat", 6, "Route 25"),
               Step("talk", "route_24_weepinbell", "Report to Weepinbell (Route 24)", town="route_24",
                    dialogue=(("Weepinbell", "Bugs caught! Weepin'!"),
                              ("Weepinbell", "Now the Vine Lashers in Pitcher Grove. Their leader's mouth is twice "
                                             "the size of mine. Talk to me when you're ready."))),
               Step("defeat", "pitcher_grove", "Beat the Vine Lashers in Pitcher Grove (talk to Weepinbell, Route "
                                               "24)",
                    dialogue=(("Weepinbell", "Snap! Your Bellsprout out-lashed them all. It's a Weepinbell now in "
                                             "all but shape!"),)),
               Step("evolve", "bellsprout", "Evolve your Bellsprout into Weepinbell (party screen: E)")),
        money=900, xp=700,
    ),
    Quest(
        "evolve_nidorina", "Mother's Thorns",
        "Viridian City's Nidorina says a Nidoran F grows by caring for others. Bring soft grass for the young "
        "ones' nests.",
        giver="viridian_nidorina",
        offer=(("Nidorina", "Your Nidoran is so grown-up now. A Nidorina looks after the little ones, you know."),
               ("Nidorina", "Their nests on Route 22 need soft grass. Bring me 4 bundles?")),
        steps=(collect("Soft Grass", 4, "route_22", ("nidoran_f", "rattata"), 35,
                       "Nidoran F and Rattata on Route 22", "Soft Grass bundles"),
               Step("talk", "viridian_nidorina", "Bring the Soft Grass to Nidorina (Viridian City)", town="viridian",
                    dialogue=(("Nidorina", "Lovely and soft. The little ones will sleep well tonight."),
                              ("Nidorina", "Your Nidoran has a kind heart. It's ready to grow up."))),
               Step("evolve", "nidoran_f", "Evolve your Nidoran F into Nidorina (party screen: E)")),
        money=400, xp=300,
    ),
    Quest(
        "evolve_kadabra", "Bent Spoon",
        "Cerulean City's Kadabra says an Abra's mind wakes when it's tested. Pass the Trial of Mind, and yours "
        "could grow into a Kadabra.",
        giver="cerulean_kadabra",
        offer=(("Kadabra", "...Your Abra is awake. Barely. Its mind is ready for more."),
               ("Kadabra", "Sharpen it first: beat 6 Venonat on Route 25. Their poison clouds the mind.")),
        steps=(hunt("venonat", 6, "Route 25"),
               Step("talk", "cerulean_kadabra", "Report to Kadabra (Cerulean City)", town="cerulean",
                    dialogue=(("Kadabra", "Clear. Focused. Good."),
                              ("Kadabra", "Now the Trial of Mind. Your Abra goes in alone. Talk to me when "
                                          "you're ready."))),
               Step("defeat", "trial_abra", "Pass the Trial of Mind (talk to Kadabra, Cerulean City)",
                    dialogue=(("Kadabra", "...Impressive. Take this spoon. Your Abra will know what to do with it."),)),
               Step("evolve", "abra", "Evolve your Abra into Kadabra (party screen: E)")),
        money=700, xp=500,
    ),

    # The starters' evolutions: the elder in Pewter City (the last form of
    # the player's starter's line) gives the one for the player's starter.
    Quest(
        "evolve_bulbasaur", "Coming of Age",
        "The old Venusaur in Pewter City says your Bulbasaur is ready to grow up, but first it must "
        "prove itself.",
        giver="pewter_elder",
        offer=(("Old Venusaur", "Your Bulbasaur has grown strong. I remember being just like it."),
               ("Old Venusaur", "Bring me three Sun Leaves from Route 3, and I'll test it in the Trial of Leaves.")),
        steps=(collect("Sun Leaf", 3, "route_3", ('spearow', 'jigglypuff', 'sandshrew', 'ekans'), 25, "Route 3", "Sun Leaves"),
               Step("talk", "pewter_elder", "Bring the Sun Leaves to the old Venusaur (Pewter City)",
                    town="pewter",
                    dialogue=(("Old Venusaur", "These will do. Feel the sun in them? That is where a Grass Pokémon's strength comes from."),
                              ("Old Venusaur", "Now, the Trial of Leaves. Your Bulbasaur goes in alone. Talk to me when "
                                              "you're ready."))),
               Step("defeat", "trial_bulbasaur", "Pass the Trial of Leaves (talk to the old Venusaur in Pewter City)",
                    dialogue=(("Old Venusaur", "Well done. Your Bulbasaur is ready to become a Ivysaur."),)),
               Step("evolve", "bulbasaur", "Evolve your Bulbasaur into Ivysaur (party screen: E)")),
        money=600, xp=400,
    ),
    Quest(
        "evolve_charmander", "Coming of Age",
        "The old Charizard in Pewter City says your Charmander is ready to grow up, but first it must "
        "prove itself.",
        giver="pewter_elder",
        offer=(("Old Charizard", "Your Charmander has grown strong. I remember being just like it."),
               ("Old Charizard", "Bring me three Moon Flints from Mt. Moon, and I'll test it in the Trial of Flame.")),
        steps=(collect("Moon Flint", 3, "mt_moon_cave", ('geodude',), 35, "Mt. Moon"),
               Step("talk", "pewter_elder", "Bring the Moon Flints to the old Charizard (Pewter City)",
                    town="pewter",
                    dialogue=(("Old Charizard", "These will do. Strike them together and they spark. A Fire Pokémon's flame must burn just as hot."),
                              ("Old Charizard", "Now, the Trial of Flame. Your Charmander goes in alone. Talk to me when "
                                              "you're ready."))),
               Step("defeat", "trial_charmander", "Pass the Trial of Flame (talk to the old Charizard in Pewter City)",
                    dialogue=(("Old Charizard", "Well done. Your Charmander is ready to become a Charmeleon."),)),
               Step("evolve", "charmander", "Evolve your Charmander into Charmeleon (party screen: E)")),
        money=600, xp=400,
    ),
    Quest(
        "evolve_squirtle", "Coming of Age",
        "The old Blastoise in Pewter City says your Squirtle is ready to grow up, but first it must "
        "prove itself.",
        giver="pewter_elder",
        offer=(("Old Blastoise", "Your Squirtle has grown strong. I remember being just like it."),
               ("Old Blastoise", "Bring me three Forest Dews from Viridian Forest, and I'll test it in the Trial of Tides.")),
        steps=(collect("Forest Dew", 3, "viridian_forest", ('caterpie', 'metapod', 'weedle', 'kakuna', 'pikachu'), 20, "Viridian Forest"),
               Step("talk", "pewter_elder", "Bring the Forest Dews to the old Blastoise (Pewter City)",
                    town="pewter",
                    dialogue=(("Old Blastoise", "These will do. Clear as a spring. A Water Pokémon must flow like this: never still."),
                              ("Old Blastoise", "Now, the Trial of Tides. Your Squirtle goes in alone. Talk to me when "
                                              "you're ready."))),
               Step("defeat", "trial_squirtle", "Pass the Trial of Tides (talk to the old Blastoise in Pewter City)",
                    dialogue=(("Old Blastoise", "Well done. Your Squirtle is ready to become a Wartortle."),)),
               Step("evolve", "squirtle", "Evolve your Squirtle into Wartortle (party screen: E)")),
        money=600, xp=400,
    ),

    # The starters' last evolutions (the master in Celadon's west end: the
    # last form of the player's starter's line) and Pidgeot's.
    Quest(
        "master_ivysaur", "Mastery",
        "The master Venusaur in Celadon's west end says your Ivysaur is ready for its last step. "
        "First it must stand up to what it fears most; then, alone, face what it will become.",
        giver="celadon_master",
        offer=(("Master Venusaur", "Your Ivysaur's bud is about to bloom. I can smell it. But a flower must weather the wind first."),
               ("Master Venusaur", "Beat 8 Pidgeotto on Route 8. Then come back to me.")),
        steps=(hunt("pidgeotto", 8, "Route 8"),
               Step("talk", "celadon_master", "Report to the master Venusaur (Celadon West End)",
                    town="celadon_west",
                    dialogue=(("Master Venusaur", "The birds didn't scare it off. Good. Roots that deep don't come up easily."),
                              ("Master Venusaur", "Now, the Trial of the Great Tree. Your Ivysaur goes in alone, "
                                                        "and at the end, a Venusaur waits. Talk to me when "
                                                        "you're ready."))),
               Step("defeat", "trial_ivysaur", "Pass the Trial of the Great Tree (talk to the master Venusaur, Celadon West End)",
                    dialogue=(("Master Venusaur", "Magnificent. Your Ivysaur stood against a Venusaur and did not wither. It is ready to bloom."),)),
               Step("evolve", "ivysaur", "Evolve your Ivysaur into Venusaur (party screen: E)")),
        money=1500, xp=1300,
    ),
    Quest(
        "master_charmeleon", "Mastery",
        "The master Charizard in Celadon's west end says your Charmeleon is ready for its last step. "
        "First it must stand up to what it fears most; then, alone, face what it will become.",
        giver="celadon_master",
        offer=(("Master Charizard", "Your Charmeleon's flame burns hot. But a flame that fears the earth will be smothered."),
               ("Master Charizard", "Beat 8 Diglett on the Underground Path (west). Then come back to me.")),
        steps=(hunt("diglett", 8, "the Underground Path (west)"),
               Step("talk", "celadon_master", "Report to the master Charizard (Celadon West End)",
                    town="celadon_west",
                    dialogue=(("Master Charizard", "It stood its ground against the ground itself. Good. That flame won't go out."),
                              ("Master Charizard", "Now, the Trial of the Inferno. Your Charmeleon goes in alone, "
                                                        "and at the end, a Charizard waits. Talk to me when "
                                                        "you're ready."))),
               Step("defeat", "trial_charmeleon", "Pass the Trial of the Inferno (talk to the master Charizard, Celadon West End)",
                    dialogue=(("Master Charizard", "The sky is yours now. Your Charmeleon faced a Charizard and its flame never wavered."),)),
               Step("evolve", "charmeleon", "Evolve your Charmeleon into Charizard (party screen: E)")),
        money=1500, xp=1300,
    ),
    Quest(
        "master_wartortle", "Mastery",
        "The master Blastoise in Celadon's west end says your Wartortle is ready for its last step. "
        "First it must stand up to what it fears most; then, alone, face what it will become.",
        giver="celadon_master",
        offer=(("Master Blastoise", "Your Wartortle's shell has grown hard. But a shell is only as strong as the will inside it."),
               ("Master Blastoise", "Beat 8 Growlithe on Route 8. Then come back to me.")),
        steps=(hunt("growlithe", 8, "Route 8"),
               Step("talk", "celadon_master", "Report to the master Blastoise (Celadon West End)",
                    town="celadon_west",
                    dialogue=(("Master Blastoise", "It put out every fire. Good. The deep sea is calm, and so is it."),
                              ("Master Blastoise", "Now, the Trial of the Deep. Your Wartortle goes in alone, "
                                                        "and at the end, a Blastoise waits. Talk to me when "
                                                        "you're ready."))),
               Step("defeat", "trial_wartortle", "Pass the Trial of the Deep (talk to the master Blastoise, Celadon West End)",
                    dialogue=(("Master Blastoise", "Your Wartortle held firm against a Blastoise's cannons. It is ready to carry its own."),)),
               Step("evolve", "wartortle", "Evolve your Wartortle into Blastoise (party screen: E)")),
        money=1500, xp=1300,
    ),
    Quest(
        "evolve_pidgeot", "Lord of the Skies",
        "Celadon's Pidgeot says a Pidgeotto becomes a Pidgeot only once it leads the flock, and once it has "
        "flown higher than the rest.",
        giver="celadon_pidgeot",
        offer=(("Pidgeot", "Kaw! Your Pidgeotto has strong wings. But a Pidgeot leads, it doesn't follow."),
               ("Pidgeot", "Out-fly 8 wild Pidgeotto on Route 8. Then come back to me.")),
        steps=(hunt("pidgeotto", 8, "Route 8"),
               Step("talk", "celadon_pidgeot", "Report to Pidgeot (Celadon City)", town="celadon",
                    dialogue=(("Pidgeot", "The flock follows you now. Kaw!"),
                              ("Pidgeot", "Last, the Trial of the Skies. Your Pidgeotto flies alone, and at the end "
                                          "a giant Pidgeot waits. Talk to me when you're ready."))),
               Step("defeat", "trial_pidgeotto", "Pass the Trial of the Skies (talk to Pidgeot, Celadon City)",
                    dialogue=(("Pidgeot", "Kaw! You flew higher than any of them. The skies are yours."),)),
               Step("evolve", "pidgeotto", "Evolve your Pidgeotto into Pidgeot (party screen: E)")),
        money=1500, xp=1300,
    ),
    # The feud on Route 22: help the Pidgey or the Spearow (one at a time;
    # the other side opens again once the first is done).
    Quest(
        "feud_pidgey", "Ruffled Feathers",
        "Viridian City's Pidgeotto wants the Spearow on Route 22 to leave its flock alone. A Pidgey that "
        "stands up to them could grow into a Pidgeotto.",
        giver="viridian_pidgeotto", excludes=("feud_spearow",),
        offer=(("Pidgeotto", "Your Pidgey is ready to spread its wings. But the Spearow won't let it."),
               ("Pidgeotto", "Chase off 8 of those Spearow on Route 22, then come back to me.")),
        steps=(hunt("spearow", 8, "Route 22"),
               Step("talk", "viridian_pidgeotto", "Report to Pidgeotto (Viridian City)", town="viridian",
                    dialogue=(("Pidgeotto", "They won't forget that. But their leader, a huge Fearow, is still "
                                            "at their roost."),
                              ("Pidgeotto", "Beat the Beak Gang at their roost, and my flock is safe. "
                                            "Talk to me when you're ready."))),
               Step("defeat", "feud_beak_gang", "Beat the Beak Gang at their roost (talk to Pidgeotto, Viridian City)",
                    dialogue=(("Pidgeotto", "You did it! Your Pidgey fought like a true flock leader."),)),
               Step("evolve", "pidgey", "Evolve your Pidgey into Pidgeotto (party screen: E)")),
        money=700, xp=500,
    ),
    Quest(
        "feud_spearow", "Sharp Beaks",
        "Viridian City's Fearow says the Pidgey flocks hog the skies. A Spearow that wins its fights could "
        "grow into a Fearow.",
        giver="viridian_fearow", excludes=("feud_pidgey",),
        offer=(("Fearow", "That Spearow of yours has a sharp beak. Let's see if it has the guts to match."),
               ("Fearow", "Beat 8 Pidgey on Route 1. Show them who rules the sky.")),
        steps=(hunt("pidgey", 8, "Route 1"),
               Step("talk", "viridian_fearow", "Report to Fearow (Viridian City)", town="viridian",
                    dialogue=(("Fearow", "Ha! Not bad. But their leader, a giant Pidgeotto, still sits in "
                                         "their meadow."),
                              ("Fearow", "Beat the Sky Flock in their meadow. Talk to me when you're ready."))),
               Step("defeat", "feud_sky_flock", "Beat the Sky Flock in their meadow (talk to Fearow, Viridian City)",
                    dialogue=(("Fearow", "Hah! Now that's a Spearow with a beak worth fearing."),)),
               Step("evolve", "spearow", "Evolve your Spearow into Fearow (party screen: E)")),
        money=700, xp=500,
    ),

    # Pewter City: the first gym, and the road on.
    Quest(
        "boulder_badge", "The Boulder Badge",
        "The Boulder Gang, Rock-type Pokémon led by an Onix, holds the Pewter Gym. Beat them for the Boulder "
        "Badge and the road east opens.",
        starts_in="pewter",
        steps=(Step("defeat", "pewter_gym", "Defeat the Boulder Gang at the Pewter Gym",
                    dialogue=(("Onix", "I took you for granted. As proof of your victory, here's the Boulder Badge!"),
                              ("", "You received the Boulder Badge!"),
                              ("Onix", "The road east, Route 3, is open to you. Mt. Moon lies beyond it.")),
                    gives=("Boulder Badge",)),),
        money=500, xp=400,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Rare", 14)),
    ),
    Quest(
        "to_mt_moon", "Road to Mt. Moon",
        "Route 3 runs east from Pewter City to the foot of Mt. Moon. Bands of Pokémon have claimed the road.",
        requires=("boulder_badge",),
        steps=(Step("reach", "mt_moon", "Reach Mt. Moon by Route 3 (east of Pewter City)"),),
        money=400, xp=300,
    ),
    Quest(
        "through_mt_moon", "Through Mt. Moon",
        "Mt. Moon's tunnels lead to Route 4 and on to Cerulean City. Ladders go every which way, and Team "
        "Rocket is said to be digging deep inside.",
        requires=("to_mt_moon",),
        steps=(Step("reach", "route_4", "Find the way through Mt. Moon to Route 4"),),
        money=800, xp=600,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Uncommon", 14)),
    ),
    Quest(
        "to_cerulean", "Cerulean City",
        "Route 4 runs down from Mt. Moon to Cerulean City, home of the second gym.",
        requires=("through_mt_moon",),
        steps=(Step("reach", "cerulean", "Follow Route 4 down to Cerulean City"),),
        money=500, xp=400,
    ),
    Quest(
        "cascade_badge", "The Cascade Badge",
        "The Cascade Crew, Water Pokémon led by a Starmie, holds the Cerulean Gym. Beat them for the Cascade "
        "Badge.",
        starts_in="cerulean", requires=("to_cerulean",),
        steps=(Step("defeat", "cerulean_gym", "Defeat the Cascade Crew at the Cerulean Gym",
                    dialogue=(("Starmie", "Hyah... Hyah! You really are strong. Here, the Cascade Badge!"),
                              ("", "You received the Cascade Badge!")),
                    gives=("Cascade Badge",)),),
        money=900, xp=800,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 21)),
    ),
    Quest(
        "rival_cerulean", "Rival at Nugget Bridge",
        "Your rival went north from Cerulean City, over Nugget Bridge, to see a Pokémaniac called Bill.",
        requires=("to_cerulean",),
        steps=(Step("defeat", "nugget_rival", "Beat your rival at Nugget Bridge (Route 24, north of Cerulean)"),),
        money=900, xp=700,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Uncommon", 16)),
        done_dialogue=(("Rival", "What? Again?! I was just warming up."),
                       ("Rival", "I already went to see Bill. He's got loads of rare Pokémon. Go see for "
                                 "yourself, then. Smell ya!"),),
    ),
    Quest(
        "bill", "Bill's Sea Cottage",
        "Bill the Pokémaniac lives at the end of Route 25. Something has gone very wrong at his cottage.",
        requires=("rival_cerulean",),
        steps=(Step("talk", "bill_clefairy", "Talk to the Clefairy outside Bill's Sea Cottage (Routes 24 and 25, north of Cerulean)",
                    town="sea_cottage",
                    dialogue=(("Clefairy", "Hiya! I'm a Pokémon... No wait! I'm Bill, a Pokémaniac!"),
                              ("Bill", "My teleporter mixed me up with this Clefairy! Please help me out."),
                              ("Bill", "I'll step back into the teleporter. Then go into the cottage and run the "
                                       "Cell Separator!"))),
               Step("visit", "Bill's Sea Cottage", "Run the Cell Separator in Bill's Sea Cottage",
                    town="sea_cottage",
                    before="The door is locked. Something whirs inside... The Clefairy by the path is waving "
                           "at you frantically.",
                    dialogue=(("", "You switch on the Cell Separator. The teleporter whirs..."),
                              ("Bill", "Yeehah! Thanks, pal! I was stuck like that for days."),
                              ("Bill", "Here, take this. It's a ticket for the S.S. Anne. It's docked at "
                                       "Vermilion City, and I can't go anyway."),
                              ("", "You received the S.S. Ticket!")),
                    gives=("S.S. Ticket",))),
        money=1000, xp=800,
        rewards=(("medicine", "Revive", 2), ("gear", None, "Uncommon", 17)),
        done_dialogue=(("Bill", "Oh, and on your way back: someone broke into a house in Cerulean City. The police "
                                "gave up, but they say the thief is still hiding nearby!"),),
    ),
    Quest(
        "burglary", "The Cerulean Burglar",
        "A house at the end of Cerulean City's street was broken into. The police have gone, but the thief is "
        "said to be hiding in its backyard.",
        requires=("bill",),
        steps=(Step("defeat", "cerulean_backyard", "Catch the thief behind the burgled house (Cerulean City)",
                    dialogue=(("Rocket", "Argh! OK, OK! Take it back, I don't even know what a TM28 does!"),
                              ("", "The Rocket drops the stolen TM and runs off south."),
                              ("", "You gave TM28 back to the house's owner."),
                              ("", "With the thief gone, the backyard is the way south: Route 5 is open.")),),),
        money=1000, xp=900,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Uncommon", 18)),
    ),
    Quest(
        "to_route_5", "South of Cerulean",
        "Route 5 runs south from Cerulean City, through the burgled house's backyard, towards Saffron City.",
        requires=("burglary",),
        steps=(Step("reach", "route_5", "Follow Route 5 south of Cerulean City"),),
        money=600, xp=500,
    ),
    Quest(
        "underground_path", "Under Saffron",
        "Saffron City's gates are shut. The Underground Path runs beneath the city, from Route 5 to Route 6.",
        requires=("to_route_5",),
        steps=(Step("reach", "route_6", "Take the Underground Path to Route 6 (from the Route 5 stop)"),),
        money=700, xp=600,
    ),
    Quest(
        "to_vermilion", "Vermilion City",
        "Route 6 runs down to Vermilion City, the port where the S.S. Anne is docked.",
        requires=("underground_path",),
        steps=(Step("reach", "vermilion", "Follow Route 6 down to Vermilion City"),),
        money=900, xp=800,
        rewards=(("medicine", "Super Potion", 3), ("gear", None, "Uncommon", 22)),
        done_dialogue=(("", "The S.S. Anne is in port. With Bill's S.S. Ticket, you can go aboard."),),
    ),
    Quest(
        "ss_anne", "The S.S. Anne",
        "The luxury liner S.S. Anne is docked at Vermilion City for its yearly party, full of trainers from all "
        "over the world. Your rival is aboard too, and the Captain is said to know a secret technique.",
        requires=("to_vermilion",),
        steps=(Step("defeat", "ss_anne", "Find your rival aboard the S.S. Anne (Vermilion City's dock)",
                    dialogue=(("Rival", "Humph! At least you're raising your Pokémon a little."),
                              ("Rival", "I heard there was a Cut master on board. But he was just a seasick old "
                                        "man! Cut's useful, though. Go see him. Smell ya!"))),
               Step("talk", "ss_anne_captain", "See the Captain in his cabin (top of the S.S. Anne)",
                    dialogue=(("Captain", "Ooargh... I feel hideous... Urrp! Seasick..."),
                              ("", "You rub the Captain's back..."),
                              ("Captain", "Whew! Thank you! I feel much better. You want to see my Cut technique?"),
                              ("Captain", "I could show you if I wasn't so ill... I know! You can have this. "
                                          "Teach it to your Pokémon and you can see it Cut any time!"),
                              ("", "You received HM01 Cut!"),
                              ("Captain", "And for a sailor who stands by a seasick old man... this ribbon. My "
                                          "crew's finest wore it."),
                              ("", "You received a Teamwork Ribbon! A special item: use it in the bag (Key items), "
                                   "and one more Pokémon can fight at your side.")),
                    gives=("HM01 Cut", RIBBON))),
        money=1200, xp=1000,
        rewards=(("medicine", "Super Potion", 3), ("medicine", "Revive", 1), ("gear", None, "Uncommon", 25)),
        done_dialogue=(("", "The S.S. Anne's horn sounds: she's about to set sail. Time to go ashore!"),),
    ),
    Quest(
        "thunder_badge", "The Thunder Badge",
        "The Thunder Battalion, Electric Pokémon led by a Raichu, holds the Vermilion Gym. With Cut, the little "
        "tree over its door is no obstacle any more. It's said they only fall to a full team of three.",
        requires=("ss_anne",),
        steps=(Step("defeat", "vermilion_gym", "Cut the tree at the Vermilion Gym's door, and defeat the Thunder "
                                               "Battalion",
                    dialogue=(("Raichu", "Whoa! You're the real deal, kid! Fine then, take the Thunder Badge!"),
                              ("", "You received the Thunder Badge!")),
                    gives=("Thunder Badge",)),),
        money=1500, xp=1300,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 28)),
    ),
    # After the Thunder Badge, as in Red/Blue: east along Route 11 to where
    # Snorlax blocks the road, and through Diglett's Cave to Route 2.
    Quest(
        "to_route_11", "East of Vermilion",
        "With the Thunder Battalion beaten, the road east of Vermilion City is open. Route 11 leads to Diglett's "
        "Cave.",
        requires=("thunder_badge",),
        steps=(Step("reach", "route_11", "Follow Route 11 east of Vermilion City (its doorway by the dock)"),),
        money=1000, xp=900,
        done_dialogue=(("", "A huge Pokémon is fast asleep across the road ahead. There's no getting past it."),
                       ("", "Diglett's Cave opens beside the road. They say it runs all the way to Route 2.")),
    ),
    Quest(
        "digletts_cave", "Diglett's Cave",
        "Diglett dug a long tunnel from Route 11 all the way to Route 2, near Pewter City. Something big lives "
        "at its far end.",
        requires=("to_route_11",),
        steps=(Step("reach", "route_2", "Go through Diglett's Cave to Route 2 (from Route 11's end)"),),
        money=1200, xp=1100,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 30)),
    ),
    Quest(
        "flash", "Oak's Aide",
        "One of Professor Oak's aides is waiting on Route 2, by the mouth of Diglett's Cave.",
        requires=("digletts_cave",),
        steps=(Step("talk", "route_2_aide", "Talk to Professor Oak's aide (Route 2)",
                    dialogue=(("Oak's Aide", "Oh! You came out of Diglett's Cave? Professor Oak said you might."),
                              ("Oak's Aide", "He asked me to give you this. With Flash, even the darkest cave is "
                                             "no trouble."),
                              ("", "You received HM05 Flash!")),
                    gives=("HM05 Flash",)),),
        money=600, xp=500,
        done_dialogue=(("Oak's Aide", "Pewter City is just up the road, if you want to rest. Good luck!"),),
    ),
    # With Flash, as in Red/Blue: east of Cerulean along Route 9 to the
    # Route 10 Pokémon Center, then through the dark Rock Tunnel to Lavender.
    Quest(
        "to_rock_tunnel", "The Road East",
        "With Flash, even a pitch-dark cave is no trouble. Route 9 runs east of Cerulean City to the Pokémon "
        "Center at Rock Tunnel.",
        requires=("flash",),
        steps=(Step("reach", "route_10", "Follow Route 9 east of Cerulean City (its doorway at the street's east "
                                         "end) to the Route 10 Pokémon Center"),),
        money=1200, xp=1100,
        done_dialogue=(("", "Rock Tunnel's entrance gapes beside the Pokémon Center. Not a glimmer of light "
                            "inside."),),
    ),
    Quest(
        "rock_tunnel", "Rock Tunnel",
        "Rock Tunnel runs from the Route 10 Pokémon Center to Lavender Town. It's pitch dark: Flash lights the "
        "way.",
        requires=("to_rock_tunnel",),
        steps=(Step("reach", "lavender", "Go through Rock Tunnel to Lavender Town (Flash lights the way)"),),
        money=1500, xp=1400,
        rewards=(("medicine", "Hyper Potion", 2), ("medicine", "Revive", 1), ("gear", None, "Rare", 33)),
        done_dialogue=(("", "Lavender Town: a small, quiet town. The Pokémon Tower looms over it, where Pokémon "
                            "are laid to rest."),),
    ),
    # The smith (a Machamp at an anvil, in the major towns from Lavender on):
    # bring him something strong enough for a hammer (the Thick Bone, from
    # the Pokémon Tower's Marowak, later), and he salvages and enhances gear.
    # On offer once the Silph Scope is in hand (the way into the Tower).
    Quest(
        "smith_hammer", "A Hammer Fit for a Smith",
        "Machamp the smith broke his hammer, and no ordinary hammer survives four arms. He needs something "
        "truly strong to make a new one.",
        giver=SMITH, requires=("rocket_hideout",),
        offer=(("Machamp", "HAH! A traveller! Look at this. My hammer. Snapped clean in two."),
               ("Machamp", "Four arms, kid. Nothing they sell in a Mart lasts a day in these hands."),
               ("Machamp", "Bring me something STRONG. Stronger than iron. I'll make a hammer worth swinging, "
                           "and then I'll show you what a real smith can do with your gear.")),
        steps=(Step("talk", SMITH, "Find something strong enough for Machamp's hammer", takes=(BONE,),
                    waiting=(("Machamp", "Still nothing? I need something STRONG. Stronger than iron, "
                                         "stronger than stone."),
                             ("Machamp", "Keep your eyes open, kid. Strong things turn up in strange places.")),
                    dialogue=(("Machamp", "...What's that you've got? Let me see."),
                              ("Machamp", "HAH! Now THAT is a bone! Heavier than steel, and not a crack in it."),
                              ("", "Machamp fits the Thick Bone into an iron head, heats it, and pounds it with "
                                   "all four fists."),
                              ("Machamp", "A hammer fit for a smith! Now we can get to work."),
                              ("Machamp", "Bring me gear you don't need, and I'll break it down for parts. "
                                          "Bring me parts, and I'll make your gear stronger. Up to +5!"))),),
        money=1000, xp=800,
    ),
    # West of Lavender, as in Red/Blue: Route 8 to the shut Saffron gate,
    # then the Underground Path under the city to Celadon.
    Quest(
        "route_8", "West of Lavender",
        "Route 8 runs west of Lavender Town, towards Saffron City.",
        requires=("rock_tunnel",),
        steps=(Step("reach", "route_8_gate", "Follow Route 8 west of Lavender Town (its doorway at the town's east "
                                             "end) to the Saffron gate"),),
        money=1300, xp=1200,
        done_dialogue=(("", "The gate to Saffron City is shut here too. The guard points you to the Underground "
                            "Path."),),
    ),
    Quest(
        "to_celadon", "Celadon City",
        "The Underground Path runs under Saffron City from Route 8 to Route 7, right by Celadon City.",
        requires=("route_8",),
        steps=(Step("reach", "celadon", "Take the Underground Path from the Route 8 Gate to Celadon City"),),
        money=1600, xp=1500,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 35)),
        done_dialogue=(("", "Celadon City: the city of rainbow dreams. Its gym, its Game Corner and its huge "
                            "Department Store glitter in the sun."),),
    ),
    # The Celadon Gym, as in Red/Blue: Erika's greenhouse of Grass Pokémon.
    Quest(
        "rainbow_badge", "The Rainbow Badge",
        "The Blossom Troupe, Grass Pokémon led by a Vileplume, tends the Celadon Gym's greenhouse. Spores drift "
        "over every path in there: sleepy, poisonous, numbing. Bring Full Heals, and mind where you step.",
        requires=("to_celadon",),
        steps=(Step("defeat", "celadon_gym", "Defeat the Blossom Troupe in the Celadon Gym (Celadon Square)",
                    dialogue=(("Vileplume", "Oh my... I must have dozed off. You beat us fair and square. Please, "
                                            "take the Rainbow Badge."),
                              ("", "You received the Rainbow Badge!")),
                    gives=("Rainbow Badge",)),),
        money=1800, xp=1700,
        rewards=(("medicine", "Hyper Potion", 2), ("medicine", "Full Heal", 3), ("gear", None, "Rare", 38)),
        done_dialogue=(("", "Word of your badge spreads fast. Out in Celadon's west end, the Battle Tower throws "
                            "open its doors!"),),
    ),
    # After the Rainbow Badge, as in Red/Blue: Team Rocket's hideout under
    # the Game Corner (route "rocket_hideout"), for the Silph Scope.
    Quest(
        "rocket_hideout", "Team Rocket's Hideout",
        "Men in black keep slipping in and out of the Celadon Game Corner, and never seem to play the slots. A "
        "Rocket stands guard by a poster at the back. What's behind it?",
        requires=("rainbow_badge",),
        steps=(Step("defeat", "hideout_lift_rocket", "Get behind the poster in the Game Corner (Celadon Square), "
                                                     "and find the key to the hideout's lift",
                    dialogue=(("Rocket", "Ugh! You'll never get past the Boss! ...Oops. I dropped something."),
                              ("", "You picked up the Lift Key!")),
                    gives=("Lift Key",)),
               Step("defeat", "rocket_hideout", "Take the lift down to the Boss's office, and defeat the Boss",
                    dialogue=(("Persian", "Mrrrow... So. You've beaten the Boss of Team Rocket. Impressive."),
                              ("Persian", "Take this, then. We have no more use for it."),
                              ("", "You received the Silph Scope! It makes unseen things visible."),
                              ("Persian", "Team Rocket will not forget this. Until we meet again..."),
                              ("", "The Persian slinks into the shadows, and is gone.")),
                    takes=("Lift Key",), gives=("Silph Scope",))),
        money=2000, xp=1900,
        rewards=(("medicine", "Hyper Potion", 3), ("medicine", "Revive", 2), ("gear", None, "Rare", 40)),
        done_dialogue=(("", "With the Silph Scope, ghosts can't hide any more. Lavender Town's Pokémon Tower is "
                            "said to be full of them..."),),
    ),
    # After the Silph Scope, as in Red/Blue: up the Pokémon Tower (route
    # "pokemon_tower") past the rival and the ghost of Marowak, to Team Rocket
    # holding Mr. Fuji at the top; he gives the Poké Flute.
    Quest(
        "pokemon_tower", "The Pokémon Tower",
        "With the Silph Scope, the ghosts of the Pokémon Tower can be seen for what they are. Mr. Fuji went up "
        "the tower days ago and never came back down.",
        requires=("rocket_hideout",),
        steps=(Step("defeat", "tower_marowak", "Climb the Pokémon Tower (Lavender Town): something bars the "
                                               "stairs on 6F",
                    dialogue=(("", "The Silph Scope reveals the ghost: a Marowak, a mother still guarding her "
                                   "young."),
                              ("", "The ghost fades... At last, it can rest."),
                              ("", "Where it stood lies a huge, heavy bone.")) + BONE_FOUND,
                    gives=(BONE,)),
               Step("defeat", "pokemon_tower", "Rescue Mr. Fuji from Team Rocket at the top of the Tower",
                    dialogue=(("Mr. Fuji", "Heh? You came to save me? Thank you. Team Rocket wanted the Pokémon "
                                           "here for... I'd rather not say."),
                              ("Mr. Fuji", "Come to my house, by the tower. I have something for you."))),
               Step("visit", "Mr. Fuji's House", "See Mr. Fuji at his house (Lavender Town)", town="lavender",
                    dialogue=(("Mr. Fuji", "I am Mr. Fuji. I look after the Pokémon that lose their trainers."),
                              ("Mr. Fuji", "Please, take this. Its tune wakes even the deepest sleeper."),
                              ("", "You received the Poké Flute!")),
                    gives=("Poké Flute",))),
        money=2200, xp=2100,
        rewards=(("medicine", "Hyper Potion", 3), ("medicine", "Revive", 2), ("gear", None, "Rare", 42)),
        done_dialogue=(("", "The Poké Flute... Word is two Snorlax are fast asleep across Kanto's roads: one west "
                            "of Celadon City, on the way to Route 16, and one at the Route 11 Gate, on the way to "
                            "Route 12."),),
    ),
    # The Poké Flute isn't enough on its own: a Snorlax only wakes up hungry.
    # Two sleep across the roads, one west of Celadon (blocking Route 16) and
    # one at the Route 11 Gate (blocking Route 12, up to Lavender): either
    # does. A feast (snacks won back from Route 8's Meowth and Mankey, and a
    # crate of Soda Pop from the Department Store's roof), the flute, and a
    # battle to calm it down; then it joins, and its road opens. The other
    # one is for `snorlax_second`.
    Quest(
        "snorlax_west", "The Sleeping Giant",
        "Two Snorlax are fast asleep across Kanto's roads: one west of Celadon City (the way to Route 16), one at "
        "the Route 11 Gate (the way to Route 12 and Lavender Town). Perhaps the Poké Flute will wake one.",
        requires=("pokemon_tower",),
        steps=(Step("talk", "celadon_snorlax", "Play the Poké Flute for a sleeping Snorlax (Celadon West End or the "
                                               "Route 11 Gate)",
                    alt=("route_12_snorlax",),
                    dialogue=(("", "You played the Poké Flute. A soft, bright tune drifts over Snorlax..."),
                              ("", "Snorlax snorts, scratches its belly, rolls over... and goes on snoring."),
                              ("", "It's too deep asleep for a tune alone. Maybe a Hypno would know: they know "
                                   "all about sleep."))),
               Step("talk", "celadon_hypno", "Ask a Hypno how to wake Snorlax (Celadon West End or the Route 11 Gate)",
                    alt=("route_11_hypno",),
                    dialogue=(("Hypno", "The Poké Flute didn't do it? Of course not. That Snorlax is dreaming of "
                                        "dinner."),
                              ("Hypno", "A Snorlax only ever wakes up hungry. Put a feast under its nose, THEN play "
                                        "your flute."),
                              ("Hypno", "The Meowth and Mankey on Route 8 have been raiding the market stalls. Win "
                                        "the snacks back, and buy it something to wash them down."))),
               collect("Stolen Snack", 6, "route_8", ("meowth", "mankey"), 50, "Meowth and Mankey on Route 8"),
               Step("visit", "Rooftop", "Buy a crate of Soda Pop at the Department Store's rooftop (Celadon City)",
                    town="celadon",
                    dialogue=(("", "The vending machine rumbles and rumbles... and rumbles. A whole crate of Soda Pop "
                                   "rattles out!"),
                              ("", "You received a Soda Pop Crate! That should be enough for a Snorlax. Maybe.")),
                    gives=("Soda Pop Crate",)),
               Step("talk", "celadon_snorlax", "Lay out the feast for a Snorlax and play the Poké Flute (Celadon West "
                                               "End or the Route 11 Gate)",
                    alt=("route_12_snorlax",), takes=("Soda Pop Crate",),
                    dialogue=(("", "You set out the snacks and the Soda Pop in front of Snorlax, and play the Poké "
                                   "Flute..."),
                              ("", "Its nose twitches. Its belly rumbles. One eye opens..."),
                              ("", "Snorlax wolfs down the whole feast in three bites... and it's still hungry. And "
                                   "grumpy!"),
                              ("", "And there's a rustling nearby: whoever's been loafing around it wants the "
                                   "leftovers!"))),
               Step("defeat", "snorlax_wakes", "Calm down the Snorlax you fed (talk to it)",
                    alt=("snorlax_wakes_east",),
                    dialogue=(("", "Snorlax flops down, puffing... then looks at you, and at your bag. You fed it, "
                                   "after all."),
                              ("", "Snorlax yawns, stretches, and lumbers along after you. It wants to come along!")))),
        money=2400, xp=2300,
        rewards=(("pokemon", "snorlax", 40),),
        done_dialogue=(("", "With Snorlax up and about, the road it slept across is clear."),
                       ("", "The other Snorlax is still snoring. Now that you know the trick, the Poké Flute alone "
                            "will do to wake it: it'll be just as grumpy, though.")),
    ),
    # The other Snorlax (whichever wasn't woken for "The Sleeping Giant"):
    # the flute alone wakes it, grumpy; calming it down opens its road. It
    # doesn't join (one Snorlax is plenty).
    Quest(
        "snorlax_second", "The Other Sleeping Giant",
        "One Snorlax is still asleep across a road. Now that you know how, the Poké Flute will wake it, and it "
        "won't be happy about it.",
        requires=("snorlax_west",),
        steps=(Step("defeat", "snorlax_wakes", "Wake the other Snorlax with the Poké Flute (talk to it)",
                    alt=("snorlax_wakes_east",),
                    dialogue=(("", "Snorlax flops down, yawns hugely... and rolls off the road into the grass, "
                                   "fast asleep again."),)),),
        money=2000, xp=1900,
        rewards=(("medicine", "Hyper Potion", 2),),
        done_dialogue=(("", "Both roads are clear now."),),
    ),
    # The Route 16 Gate's guard, a Fearow, won't let anyone down the road
    # south until he's had a proper drink: spring water, not the bottled
    # stuff. Celadon's Bellsprout knows where; a Golduck's gang has taken
    # the spring over.
    Quest(
        "thirsty_guard", "Thirsty Work",
        "The Fearow guarding the Route 16 Gate is parched, and won't let anyone through until he's had a proper "
        "drink. Bottled water won't do: he wants it fresh from a spring.",
        giver="route_16_guard", requires=("snorlax_west",),
        offer=(("Gate Guard", "Kaw... You want the road south? Not today. Not until I've had a drink."),
               ("Gate Guard", "And don't bring me that bottled stuff from the Department Store. Tastes like the "
                              "bottle. I want SPRING water."),
               ("Gate Guard", "There's a spring around here somewhere. A Bellsprout would know: they drink like "
                              "nobody's business.")),
        steps=(Step("talk", "celadon_bellsprout", "Ask Celadon's Bellsprout where to find spring water (Celadon City)",
                    dialogue=(("Bellsprout", "Sprout! Spring water? The best in Kanto bubbles up on the cliffs "
                                             "behind the Route 16 Gate."),
                              ("Bellsprout", "But a gang of Golduck moved in and splash anyone who comes near. "
                                             "Rude!"),
                              ("Bellsprout", "The guard knows the path up. Ask him!"))),
               Step("defeat", "hidden_spring", "Win back the Hidden Spring from the Golduck gang (talk to the Route "
                                               "16 Gate guard)",
                    dialogue=(("", "The Golduck gang slinks off, dripping. The spring bubbles up clear and cold."),
                              ("", "You fill a flask with Spring Water!")),
                    gives=("Spring Water",)),
               Step("talk", "route_16_guard", "Bring the Spring Water to the Route 16 Gate guard",
                    takes=("Spring Water",),
                    waiting=(("Gate Guard", "Kaw... Water. Spring water. Please."),),
                    dialogue=(("Gate Guard", "Is that... SPRING water? Give it here!"),
                              ("", "The Fearow drains the flask in one long gulp."),
                              ("Gate Guard", "KAAAW! Now THAT is water. I feel ten years younger."),
                              ("Gate Guard", "Fair's fair: the road south is yours. They turned it into a skate road, "
                                             "downhill all the way. Got a board? No? Primeape over there "
                                             "builds them.")))),
        money=2200, xp=2000,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 44)),
    ),
    # The skate road needs a board: the skater Primeape at the Route 16 Gate
    # builds one from wheels the Route 16 Pokémon keep running off with.
    Quest(
        "skate_board", "Wheels Needed",
        "The skate road past the Route 16 Gate is for boards only. The skater Primeape there will build you one, "
        "if you win back the wheels Route 16's Pokémon keep running off with.",
        giver="route_16_primeape", requires=("thirsty_guard",),
        offer=(("Skater Primeape", "You wanna go down the skate road? On FOOT? Grrr-ha! Nobody walks it!"),
               ("Skater Primeape", "I'll build you a board. But the Pokémon on Route 16 keep running off with my "
                                   "wheels. Rattata chew 'em, Spearow think they're eggs..."),
               ("Skater Primeape", "Win me back four wheels, and the board's yours.")),
        steps=(collect("Skate Wheel", 4, "route_16", ("rattata", "raticate", "spearow", "fearow", "pidgeotto", "koffing",
                                                      "grimer"), 40, "Pokémon on Route 16"),
               Step("talk", "route_16_primeape", "Bring the Skate Wheels to the skater Primeape (Route 16 Gate)",
                    dialogue=(("Skater Primeape", "Four wheels! Gimme a sec..."),
                              ("", "Primeape bolts the wheels onto a deck, spins each one, and shoves the board at "
                                   "you."),
                              ("", "You received a Skateboard!"),
                              ("Skater Primeape", "Lean to steer, push to go, and DON'T stop at the bottom: that's "
                                                  "Tony's turf. Kangaskhan. Huge. Wears a helmet. Never wipes out.")),
                    gives=("Skateboard",))),
        money=1500, xp=1400,
    ),
    # Down the skate road (route "skate_road"), to Tony at the bottom.
    Quest(
        "king_of_the_hill", "King of the Hill",
        "Tony, a Kangaskhan who's never wiped out, rules the bottom of the skate road with his crew. Skate down "
        "and take his crown. Well, his helmet.",
        requires=("skate_board",),
        steps=(Step("defeat", "skate_road", "Skate down the skate road (Route 16 Gate) and beat Tony at the bottom",
                    dialogue=(("Tony", "...Whoa. Nobody's ever beaten me on my own hill."),
                              ("Tony", "Here. Take the lid. A helmet like that belongs on the head of a champ."),
                              ("Tony", "Just... keep the chin strap done up, yeah?"))),),
        money=2600, xp=2400,
        rewards=(("medicine", "Hyper Potion", 2), ("medicine", "Revive", 1)),
        done_dialogue=(("", "The skaters at the bottom of the hill cheer: there's a new King of the Hill."),),
    ),
    # Learn to Fly (Red/Blue's HM02, given on Route 16): the old Pidgeot at
    # the Route 16 Gate teaches a grown bird (a Pidgeotto, Pidgeot or
    # Fearow) to carry its trainer. Leading the way in 5 wild battles, then
    # the Sky Trial, a sky battle it fights alone; then Fly: fast travel on
    # the Town Map (`can_fly`).
    Quest(
        "learn_to_fly", "Learn to Fly",
        "The old Pidgeot at the Route 16 Gate says a grown bird can learn to carry its trainer anywhere they've "
        "been. First it has to lead the way, then pass the Sky Trial on its own.",
        # (No quest needed first: he's only reachable past the Celadon Snorlax anyway, and a
        # requirement here only ever hid the quest from a player who got there another way.)
        giver="route_16_pidgeot", needs_species=FLY_SPECIES,
        offer=(("Old Pidgeot", "Kaaw... That bird of yours. Strong wings. Strong enough to carry you, one day."),
               ("Old Pidgeot", "A bird that carries its trainer has to lead. Let it go first into 5 wild battles, "
                               "anywhere from Route 8 on."),
               ("Old Pidgeot", "Then come back, and I'll take it up to the Skyward Cliffs for the Sky Trial.")),
        steps=(Step("lead_wins", "", "Win 5 wild battles with your Pidgeotto, Pidgeot or Fearow leading (Route 8 "
                                     "or later)", count=5, route="route_8", species=FLY_SPECIES),
               Step("talk", "route_16_pidgeot", "Tell the old Pidgeot your bird is ready (Route 16 Gate)",
                    dialogue=(("Old Pidgeot", "Kaaw! It leads well. Now: the Skyward Cliffs."),
                              ("Old Pidgeot", "Up there your bird fights alone, in the air, one foe after another, "
                                              "and the winds change every moment."),
                              ("Old Pidgeot", "Perch to rest its wings, fly up out of reach, and read the wind."),
                              ("Old Pidgeot", "And if your bird's still a bit young for it (under Lv42), you can "
                                              "borrow my old partner. Talk to me when you're ready."))),
               Step("defeat", "sky_trial", "Pass the Sky Trial on the Skyward Cliffs (talk to the old Pidgeot)",
                    dialogue=(("Old Pidgeot", "KAAAW! It flew like it was born up there. Because it was."),
                              ("Old Pidgeot", "Your bird can carry you now: anywhere you've been. Open the Town Map "
                                              "(M), pick a town, and fly."),
                              ("", "You can now use Fly! (Town Map: Enter on a town you've visited, with a Flying "
                                   "Pokémon in the party.)")))),
        money=2400, xp=2200,
        rewards=(("medicine", "Hyper Potion", 2),),
    ),
    # Down the skate road and along Route 18 to Fuchsia City (as in
    # Red/Blue, by Cycling Road).
    # Or along the coast (Red/Blue's Routes 13-15), once the Route 11 Gate's
    # Snorlax is awake: either way opens Fuchsia City's quests.
    Quest(
        "coastal_road", "The Coastal Road",
        "With the Route 11 Gate's Snorlax awake, the coastal road runs south past it: Route 13's fences and flower "
        "beds to Silence Bridge, Route 14's woods, and Route 15 into Fuchsia City. Something has overgrown the "
        "road's far end.",
        requires=("snorlax_west",), needs=("boss:snorlax_wakes_east", "beaten"),
        steps=(Step("reach", "silence_bridge", "Follow Route 13 from the Route 11 Gate (past its Snorlax) to "
                                               "Silence Bridge"),
               Step("reach", "route_15", "Follow Route 14 through the woods to the Route 15 Gate"),
               Step("defeat", "route_15", "Clear the Thornwood Gang at the end of Route 15",
                    dialogue=(("", "The giant Victreebel wilts, and its gang scatters into the long grass."),
                              ("", "The vines pull back from the road. Fuchsia City is just ahead!")))),
        money=2600, xp=2500,
        rewards=(("medicine", "Hyper Potion", 2), ("medicine", "Revive", 1), ("gear", None, "Rare", 47)),
    ),
    Quest(
        "to_fuchsia", "Fuchsia City",
        "Fuchsia City lies on the coast: east along Route 18 from the bottom of the skate road, or at the end of "
        "the coastal road (Route 15).",
        requires=(("king_of_the_hill", "coastal_road"),),
        steps=(Step("reach", "fuchsia", "Reach Fuchsia City (Route 18 from the skate road, or Route 15 along "
                                        "the coast)"),),
        money=2800, xp=2600,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 46)),
        done_dialogue=(("", "Fuchsia City: a town by the sea, home of the Safari Zone and of Koga, the ninja gym "
                            "leader."),),
    ),
    # The Fuchsia Gym, as in Red/Blue: Koga's ninja dojo of Poison Pokémon,
    # behind walls nobody can see.
    Quest(
        "soul_badge", "The Soul Badge",
        "Koga's Ninja Clan trains in the Fuchsia Gym: Poison Pokémon behind walls nobody can see, and vents that "
        "puff poison gas. Feel your way through, bring Antidotes and Full Heals, and mind the fumes.",
        requires=("to_fuchsia",),
        steps=(Step("defeat", "fuchsia_gym", "Defeat the Ninja Clan in the Fuchsia Gym (Fuchsia City)",
                    dialogue=(("Weezing", "Hsssss... You found your way through walls you couldn't see. Koga would "
                                          "be proud."),
                              ("Weezing", "Take the Soul Badge. You've earned it, ninja."),
                              ("", "You received the Soul Badge!")),
                    gives=("Soul Badge",)),),
        money=3000, xp=2800,
        rewards=(("medicine", "Hyper Potion", 3), ("medicine", "Full Heal", 3), ("gear", None, "Rare", 48)),
    ),
    # Saffron City (Red/Blue's middle of Kanto), once the Soul Badge is won:
    # Team Rocket has taken over Silph Co.; the gate guards, helpless, let
    # the badge holder in (the gate routes need it done).
    Quest(
        "saffron_gates", "Saffron Under Siege",
        "Something's wrong in Saffron City: its gates have been shut for weeks. Now that you hold the Soul Badge, "
        "the guards at the Route 8 Gate or on Route 5 might tell you why.",
        requires=("soul_badge",),
        steps=(Step("talk", "route_8_guard", "Ask a Saffron gate guard what's going on (the Route 8 Gate or Route 5)",
                    alt=("route_5_guard",),
                    dialogue=(("Gate Guard", "That's the Soul Badge! You beat Koga? Then listen..."),
                              ("Gate Guard", "Team Rocket has taken over Silph Co. They've got the President "
                                             "locked up, and the whole city's afraid to step outside."),
                              ("Gate Guard", "We're only guards: we can't stand up to them. But you can. The gates "
                                             "are open for you. Please, save Saffron!"),
                              ("", "Saffron City's gates are open: from Route 5, Route 6, the Route 8 Gate, and "
                                   "Route 7 by Celadon City."))),),
        money=1500, xp=1500,
    ),
    Quest(
        "silph_co", "Silph Co. Siege",
        "Team Rocket holds Silph Co.'s tower in Saffron City, floor by floor. Somewhere inside is a Card Key that "
        "opens its locked floors, and at the top, the President they're after.",
        requires=("saffron_gates",),
        steps=(Step("reach", "saffron", "Go into Saffron City (by any of its gates)"),
               Step("defeat", "silph_card_key_rocket", "Fight your way into Silph Co. (Saffron City) and take the "
                                                       "Card Key from the Rocket on 5F",
                    dialogue=(("Rocket", "No! The Card Key! The Boss is gonna kill me..."),
                              ("", "You picked up the Card Key! It opens Silph Co.'s locked floors.")),
                    gives=("Card Key",)),
               Step("defeat", "silph_rival", "Get past your rival on 7F",
                    dialogue=(("Rival", "Hah! I came to see what the fuss was about, and you STILL beat me?"),
                              ("Rival", "Fine. Go on up and play hero. I've got better things to do."))),
               Step("defeat", "silph_co", "Defeat the Rocket Boss in the President's office (11F)",
                    takes=("Card Key",),
                    dialogue=(("Persian", "You again! Twice now you've ruined Team Rocket's plans..."),
                              ("Persian", "Silph Co. is yours. But Team Rocket will rise again. Remember that."),
                              ("", "The Persian bounds out of the window and across the rooftops."),
                              ("President", "You saved us! Silph Co. owes you everything."),
                              ("President", "Please, take these from our labs, with all our thanks."))),),
        money=3200, xp=3000,
        rewards=(("medicine", "Hyper Potion", 3), ("medicine", "Max Potion", 3), ("medicine", "Revive", 2),
                 ("gear", None, "Epic", 52)),
        done_dialogue=(("", "With Team Rocket gone, Saffron City breathes again. Sabrina's gym and the Fighting "
                            "Dojo will open their doors soon."),),
    ),
    # The Saffron Gym, as in Red/Blue: Sabrina's psychics, behind barriers
    # and warp pads (once Silph Co. is free, her doors open).
    Quest(
        "marsh_badge", "The Marsh Badge",
        "With Team Rocket gone, Sabrina has opened the Saffron Gym. Her hall is cut up by psychic barriers: only "
        "the right warp pads lead on, and they're never the same twice. Her psychics wait at the end.",
        requires=("silph_co",),
        steps=(Step("defeat", "saffron_gym", "Find your way through the warp pads and defeat Sabrina's Mind Circle "
                                             "(Saffron Gym, Saffron City)",
                    dialogue=(("Alakazam", "...I foresaw this. Not the outcome: only that you would come."),
                              ("Alakazam", "Your mind is strong. Sabrina wishes you to have the Marsh Badge."),
                              ("", "You received the Marsh Badge!")),
                    gives=("Marsh Badge",)),),
        money=3400, xp=3200,
        rewards=(("medicine", "Hyper Potion", 3), ("medicine", "Max Potion", 2), ("gear", None, "Epic", 54)),
    ),
    # The Fighting Dojo, as in Red/Blue: its master is back from Silph Co.
    # and taking challengers. Beat him, and Hitmonlee or Hitmonchan joins.
    Quest(
        "fighting_dojo", "The Fighting Dojo",
        "The Fighting Dojo's master is back from Silph Co., and he's taking challengers. Beat his black belts and "
        "the master himself, and one of his prize students, Hitmonlee or Hitmonchan, will train with you.",
        giver="saffron_machoke", requires=("silph_co",),
        offer=(("Machoke", "OSS! The master came back from Silph Co.! He says the Rockets were no challenge."),
               ("Machoke", "He wants a real fight. You beat the Rockets... You should face him!"),
               ("Machoke", "Beat him, and Hitmonlee or Hitmonchan will go with you. The master's rule. OSS!")),
        steps=(Step("defeat", "fighting_dojo", "Defeat the black belts and the Karate Master in the Fighting Dojo "
                                               "(Saffron City)",
                    dialogue=(("Machamp", "HAAA... Splendid! It has been years since I lost a fair fight."),
                              ("Machamp", "As promised: Hitmonlee and Hitmonchan wait by the door. Choose one. "
                                          "Only one!"))),
               Step("talk", "dojo_hitmonlee", "Choose a partner by the Dojo's door: Hitmonlee or Hitmonchan",
                    alt=("dojo_hitmonchan",),
                    joins=(("dojo_hitmonlee", "hitmonlee", 50, "Hitmonlee: Hyah! Let's kick our way to the top!"),
                           ("dojo_hitmonchan", "hitmonchan", 50, "Hitmonchan: Hup hup! I'm ready for the next "
                                                                 "round!")))),
        money=3000, xp=2900,
        rewards=(("medicine", "Hyper Potion", 2), ("gear", None, "Rare", 54)),
        done_dialogue=(("", "The other one bows, and heads back to training."),),
    ),
    # The swaps (world/swaps.py): the trade evolutions, done by swapping
    # with townsfolk for a while. Theirs joins on loan and fights a trial
    # alone; then the player's comes back evolved, wearing what it wore.
    Quest(
        "swap_kadabra", "Mind and Muscle",
        "Saffron's Machoke wants to know how a Kadabra thinks. Swap for a while: your Kadabra trains with the "
        "Dojo, and Machoke goes with you.",
        giver="saffron_machoke", requires=("fighting_dojo",), needs_species=("kadabra",),
        offer=(("Machoke", "OSS! Your Kadabra... it beat me without touching me! How?!"),
               ("Machoke", "Let's swap for a while! Your Kadabra trains with us at the Dojo, and I go with you."),
               ("Machoke", "Muscle learns mind, mind learns muscle. That's how a Kadabra becomes something "
                           "more. Talk to me when you're ready to swap!")),
        steps=(Step("talk", "saffron_machoke", "Swap your Kadabra for Machoke (Saffron City, by the Dojo)",
                    town="saffron", swap="out",
                    dialogue=(("Machoke", "OSS! Partners! Don't worry about your Kadabra: the black belts will "
                                          "look after it."),
                              ("Machoke", "First we run the Dojo Gauntlet. Just me! Talk to your Kadabra by the "
                                          "Dojo when we're ready."))),
               Step("defeat", "trial_swap_kadabra", "Run the Dojo Gauntlet with Machoke alone (by the Dojo, Saffron "
                                                    "City)",
                    dialogue=(("Machoke", "HUUUP! We did it! Let's go and see how your Kadabra is doing."),)),
               Step("talk", "saffron_machoke", "Swap back (Saffron City, by the Dojo)", town="saffron", swap="back",
                    dialogue=(("", "Your Kadabra floats out of the Dojo. It's... bigger. Much bigger."),
                              ("Machoke", "OSS! I learned to think before I punch. It learned to punch with its "
                                          "mind!")))),
        money=3500, xp=3200,
        done_dialogue=(("Machoke", "Bring me another Kadabra any time. Hup!"),),
    ),
    # The Safari Zone Warden lost his Gold Teeth in the Safari Zone (as in
    # Red/Blue): they lie in a dead end of its deepest zone (world/safari.py).
    # He gives HM04 Strength for them.
    Quest(
        "warden_teeth", "The Warden's Teeth",
        "The Safari Zone Warden lost his Gold Teeth somewhere deep in the Safari Zone, and nobody can understand a "
        "word he says without them. Find them, deep in, in one of the dead ends.",
        requires=("to_fuchsia",),
        steps=(Step("visit", "Warden's House", "Find the Warden's Gold Teeth deep in the Safari Zone, and bring them "
                                               "to his house (Fuchsia City)", town="fuchsia",
                    takes=("Gold Teeth",), gives=("HM04 Strength",),
                    waiting=(("Warden", "Mmf! Mmmf mf, mfmf! (He points at the Safari Zone, then at his empty "
                                        "mouth.)"),),
                    dialogue=(("Warden", "Mmf? MMF! My teeth!"),
                              ("", "The Warden pops the Gold Teeth back in."),
                              ("Warden", "Ah, that's better! Thank you, young one. Here: a little something for your "
                                         "trouble."),
                              ("", "You received HM04 Strength! Big boulders block a few cave ladders: in Mt. Moon and "
                                   "Rock Tunnel. With Strength, you can push them aside."))),),
        money=2500, xp=2300,
        rewards=(("medicine", "Hyper Potion", 2),),
    ),
    # The evolution stones: one quest each, from after the Rainbow Badge (the
    # Fire and Water Stones come later, with Cinnabar and the coast). A stone
    # evolves one Pokémon and is used up (bag: Key items).
    Quest(
        "leaf_stone", "The Overgrown Wing",
        "Celadon Square's Oddish says the Celadon Gym's back wing has run wild: an Exeggutor has taken root "
        "there, around a Leaf Stone. Spores everywhere, and no way back out for a breather.",
        giver="celadon_oddish", requires=("rainbow_badge",),
        offer=(("Oddish", "Oddish... The gym's back wing is all overgrown! Nobody goes in any more."),
               ("Oddish", "A huge Exeggutor grew in there, right over a Leaf Stone. And the spores... achoo!"),
               ("Oddish", "Talk to me when you're ready, and I'll show you the way in.")),
        steps=(Step("defeat", "celadon_garden", "Clear the gym's Overgrown Wing (talk to Oddish, Celadon Square)",
                    dialogue=(("Oddish", "You did it! The Exeggutor dropped this. Oddish thinks you should have it."),
                              ("", "You received a Leaf Stone! (It evolves Gloom, Weepinbell or Exeggcute: one, "
                                   "and it's used up.)")),
                    gives=("Leaf Stone",)),),
        money=1500, xp=1400,
    ),
    Quest(
        "moon_stone", "The Moonlit Dance",
        "A Clefairy at the Mt. Moon Pokémon Center says its kin dance in the mountain's crater on clear nights, "
        "around a Moon Stone. The crater is pitch dark, and the dancers don't like to be interrupted.",
        giver="mt_moon_clefairy", requires=("rainbow_badge",),
        offer=(("Clefairy", "Clefairy! Tonight's a clear night. The great Clefable will be dancing in the crater."),
               ("Clefairy", "It dances round the Moon Stone, and it won't share it with anyone who can't keep up!"),
               ("Clefairy", "It's pitch dark up there, so bring Flash. Talk to me when you're ready.")),
        steps=(Step("defeat", "mt_moon_crater", "Win the Moonlit Dance in Mt. Moon's crater (talk to Clefairy, "
                                                "Mt. Moon Pokémon Center)",
                    dialogue=(("Clefairy", "Clefa! The great Clefable bowed to you! It left you the Moon Stone."),
                              ("", "You received a Moon Stone! (It evolves Nidorina, Nidorino, Clefairy or "
                                   "Jigglypuff: one, and it's used up.)")),
                    gives=("Moon Stone",)),),
        money=1500, xp=1400,
    ),
    Quest(
        "thunder_stone", "Live Wires",
        "The Route 10 Voltorb says the old Power Plant is running wild: loose current crackles across the floor, "
        "and an Electabuzz guards a Thunder Stone at the generator.",
        giver="route_10_voltorb", requires=("rainbow_badge",),
        offer=(("Voltorb", "Bzzt! The Power Plant down the river switched itself back on! Sparks everywhere!"),
               ("Voltorb", "An Electabuzz gang moved in. Their boss sits on a Thunder Stone, and it's charging "
                           "the whole plant. Bzzt!"),
               ("Voltorb", "Mind the loose current: one touch and you're numb. Talk to me when you're ready.")),
        steps=(Step("defeat", "power_plant", "Defeat the Live Wire Gang at the Power Plant (talk to Voltorb, "
                                             "Route 10 Pokémon Center)",
                    dialogue=(("Voltorb", "Bzzt! The plant's quiet again. And look: the Thunder Stone!"),
                              ("", "You received a Thunder Stone! (It evolves Pikachu: one, and it's used up.)")),
                    gives=("Thunder Stone",)),),
        money=1500, xp=1400,
    ),
    Quest(
        "hot_dogs", "Hot Dogs",
        "Growlithe on Route 8 keep chasing travellers' Pokémon up the trees. Calm a few of them down.",
        board="lavender", requires=("rock_tunnel",),
        steps=(hunt("growlithe", 6, "Route 8"), HAND_IN),
        money=1500, xp=1000,
    ),
    Quest(
        "ekans_fangs", "Fangs for the Memories",
        "A Lavender herbalist makes antidotes from shed Ekans fangs. Bring her a few from Route 8.",
        board="lavender", requires=("rock_tunnel",),
        steps=(collect("Ekans Fang", 5, "route_8", ("ekans",), 40, "Ekans on Route 8"), HAND_IN),
        money=1500, xp=1000,
    ),
    Quest(
        "pitch_black", "Bats in the Dark",
        "Zubat swarm Rock Tunnel, and travellers keep losing their way among them. Thin them out a bit.",
        board="cerulean", requires=("flash",),
        steps=(hunt("zubat", 8, "Rock Tunnel"), HAND_IN),
        money=1400, xp=900,
    ),
    Quest(
        "muscle_trouble", "Muscle Trouble",
        "Machop in Rock Tunnel keep moving the Hikers' boulders around for training. Teach them some manners.",
        board="cerulean", requires=("flash",),
        steps=(hunt("machop", 6, "Rock Tunnel"), HAND_IN),
        money=1400, xp=900,
    ),
    Quest(
        "sleepy_heads", "Sleepy Heads",
        "Drowzee on Route 11 keep putting travellers to sleep and eating their dreams. Wake the road up.",
        board="vermilion", requires=("thunder_badge",),
        steps=(hunt("drowzee", 6, "Route 11"), HAND_IN),
        money=1200, xp=800,
    ),
    Quest(
        "mole_hunt", "Trouble Underfoot",
        "Dugtrio deep in Diglett's Cave keep collapsing the tunnel. Chase a few of them off.",
        board="vermilion", requires=("to_route_11",),
        steps=(hunt("dugtrio", 5, "Diglett's Cave"), HAND_IN),
        money=1300, xp=900,
    ),
    # Diglett -> Dugtrio: from the Diglett at the cave's mouth on Route 11.
    Quest(
        "evolve_dugtrio", "Three Heads Are Better",
        "The Diglett at the mouth of Diglett's Cave says your Diglett is ready to become a Dugtrio, once it has "
        "proved itself underground.",
        giver="route_11_diglett",
        offer=(("Diglett", "Dig! Your Diglett is ready to become three. But a Dugtrio has to know the tunnels."),
               ("Diglett", "Chase off 6 Dugtrio in Diglett's Cave, then come back. Dig dig!")),
        steps=(hunt("dugtrio", 6, "Diglett's Cave"),
               Step("talk", "route_11_diglett", "Tell the Diglett at Diglett's Cave (Route 11)", town="route_11",
                    dialogue=(("Diglett", "Dig! The Dugtrio say you're one of us now."),
                              ("Diglett", "Go on, Diglett. Pop up three times as tall!"))),
               Step("evolve", "diglett", "Evolve your Diglett into Dugtrio (party screen: E)")),
        money=700, xp=600,
    ),
    Quest(
        "snake_charmer", "Snake Charmer",
        "Ekans on Route 3 keep frightening travelers. Drive a few of them off.",
        board="pewter", requires=("boulder_badge",),
        steps=(hunt("ekans", 5, "Route 3"), HAND_IN),
        money=500, xp=300,
    ),
    Quest(
        "puff_fluff", "Soft as Fluff",
        "A Pewter tailor wants the soft fluff Jigglypuff shed on Route 3.",
        board="pewter", requires=("boulder_badge",),
        steps=(collect("Jigglypuff Fluff", 5, "route_3", ("jigglypuff",), 40, "Jigglypuff on Route 3"), HAND_IN),
        money=600, xp=350,
    ),

    # Cerulean City's board: jobs on Route 4.
    Quest(
        "hill_spearow", "Hilltop Raiders",
        "Spearow swoop on travellers coming down Route 4 from Mt. Moon. Scare them off.",
        board="cerulean", requires=("to_cerulean",),
        steps=(hunt("spearow", 6, "Route 4"), HAND_IN),
        money=600, xp=400,
    ),
    Quest(
        "shed_skins", "Shed Skins",
        "A Cerulean pharmacist brews medicine from the skins Ekans shed on Route 4.",
        board="cerulean", requires=("to_cerulean",),
        steps=(collect("Ekans Skin", 5, "route_4_east", ("ekans",), 40, "Ekans on Route 4"), HAND_IN),
        money=700, xp=450,
    ),
    Quest(
        "bent_spoons", "Bent Spoons",
        "Spoons all over Cerulean keep bending by themselves. Someone saw Abra near Nugget Bridge.",
        board="cerulean", requires=("to_cerulean",),
        steps=(hunt("abra", 3, "Route 24"), HAND_IN),
        money=800, xp=550,
    ),
    Quest(
        "sweet_nectar", "Sweet Nectar",
        "The Cerulean bakery wants the nectar of Oddish and Bellsprout on Route 25.",
        board="cerulean", requires=("rival_cerulean",),
        steps=(collect("Sweet Nectar", 5, "route_25", ("oddish", "bellsprout"), 40, "Oddish and Bellsprout on Route 25",
                       "Sweet Nectar"), HAND_IN),
        money=900, xp=600,
    ),
    Quest(
        "venonat_swarm", "Night Swarm",
        "Venonat swarm the lights on Route 25 every night, and Bill can't sleep. Thin them out.",
        board="cerulean", requires=("rival_cerulean",),
        steps=(hunt("venonat", 6, "Route 25"), HAND_IN),
        money=900, xp=600,
    ),
    # Vermilion City's board: jobs in the Underground Path and on Route 6.
    Quest(
        "tunnel_diggers", "Tunnel Trouble",
        "Diglett keep popping up under travellers' feet in the Underground Path. Shoo a few of them off.",
        board="vermilion", requires=("to_vermilion",),
        steps=(hunt("diglett", 6, "Underground Path"), HAND_IN),
        money=1100, xp=700,
    ),
    Quest(
        "lucky_coins", "Lucky Coins",
        "Meowth on Route 6 pick up every coin they find. A Vermilion sailor wants his lucky ones back.",
        board="vermilion", requires=("to_vermilion",),
        steps=(collect("Lucky Coin", 5, "route_6_south", ("meowth",), 40, "Meowth on Route 6"), HAND_IN),
        money=1100, xp=700,
    ),
    Quest(
        "pickpockets", "Pickpockets",
        "Meowth on Route 5 snatch anything shiny from travellers' bags. Teach a few of them a lesson.",
        board="cerulean", requires=("burglary",),
        steps=(hunt("meowth", 6, "Route 5"), HAND_IN),
        money=1000, xp=650,
    ),
    Quest(
        "hot_tempers", "Hot Tempers",
        "A Cerulean tailor wants the bristly fur of the Mankey on Route 5, the angrier the better.",
        board="cerulean", requires=("burglary",),
        steps=(collect("Mankey Fur", 5, "route_5_south", ("mankey",), 40, "Mankey on Route 5", "Mankey Fur"),
               HAND_IN),
        money=1000, xp=650,
    ),
]}


RECRUIT_BOARD = "recruit"  # the board of recruitment quests (in every Recruitment Center)


def _recruit_quest(r: Recruit) -> Quest:
    name = SPECIES[r.species].name
    return Quest(
        f"recruit_{r.species}", f"Recruit {name}",
        f"Mr. Mime has found a place teeming with {name}. Beat the giant one there, and it will join you.",
        board=RECRUIT_BOARD, unlock=(r.species, r.needed),
        steps=(Step("defeat", r.route_key, f"Defeat the giant {name} on the {name} Grounds"),),
        money=r.level * 25, xp=r.level * 20,
        rewards=(("pokemon", r.species, r.boss_level),),
    )


QUESTS.update({q.key: q for q in map(_recruit_quest, RECRUITS.values())})
