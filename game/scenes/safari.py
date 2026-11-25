"""The Safari Zone's maps (`world/safari.py` has the maze): one map of the
visit's maze, with a door back and up to three doors on, a clue to the
true door (tracks or a signpost), tall grass where wild Pokémon turn up,
the steps left, and the key items deep in. The entrance (`SafariGate`) is
a building in Fuchsia City."""

from __future__ import annotations

import math
import random
from dataclasses import replace

import pygame

from .. import saves
from ..engine import ui
from ..engine.scene import Transition
from ..mechanics.items import money_text
from ..mechanics.pokemon import SPECIES
from ..world import safari, tileset
from ..world.instance import Instance, Room, Route, Stair
from ..world.level import TILE
from ..world.towns import TOWNS
from . import quest_ui
from .overworld import OverworldScene, door_label

WIDTH = 46                      # a map's width in tiles
DOOR_AT = {0: (), 1: (0.9,), 2: (0.62, 0.93), 3: (0.45, 0.7, 0.94)}  # doors on, along the map
BACK_AT = 0.03                  # the door back
BUILDING = "Safari Zone"        # its building in Fuchsia City
TRACK_LENGTH = 6 * TILE         # how far a trail of tracks runs up to its door
GRASS_H = 15                    # px of grass over the ground

_ROUTE = Route("safari", "Safari Zone", safari.ZONES[0].theme, maps=1, towns=("fuchsia", "fuchsia"), wild=False)


class Signpost:
    W, H = 22, 26

    def __init__(self, x: float, ground: float, text: str):
        self.x, self.ground, self.text = x, ground, text

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 14, round(self.ground) - 30, 28, 30)

    def draw(self, s: pygame.Surface) -> None:
        x, g = round(self.x), round(self.ground)
        pygame.draw.rect(s, (90, 60, 34), (x - 2, g - 16, 4, 16))  # the post
        board = pygame.Rect(x - self.W // 2, g - self.H, self.W, 12)
        pygame.draw.rect(s, (176, 128, 74), board)
        pygame.draw.rect(s, (70, 44, 24), board, 1)
        for i in range(3):  # scribbles
            pygame.draw.line(s, (100, 70, 40), (board.x + 4, board.y + 3 + 3 * i), (board.right - 5 - 3 * i, board.y + 3 + 3 * i))


class Pickup:
    """A key item lying on the map (a Poké Ball): Up picks it up."""

    def __init__(self, x: float, ground: float, item: str, lines: list[tuple[str, str]]):
        self.x, self.ground, self.item, self.lines = x, ground, item, lines
        self.taken = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 10, round(self.ground) - 16, 20, 16)

    def draw(self, s: pygame.Surface) -> None:
        tileset.draw_prop(s, "poke_ball", round(self.x), round(self.ground))


class SafariScene(OverworldScene):
    """One map of a Safari Zone visit (`safari.Visit`). `arrive`: "back"
    (came in through the door back) or "door<i>" (came back from door i)."""

    def __init__(self, game, visit: safari.Visit, arrive: str = "back"):
        self.visit = visit
        n = self.node = visit.here()
        stairs = [Stair("out", "back", BACK_AT)] + [Stair("out", f"door{i}", at) for i, at in enumerate(DOOR_AT[n.doors])]
        room = Room(f"{visit.seed}/{'-'.join(map(str, n.path))}", n.zone.name, WIDTH, tuple(stairs))
        route = replace(_ROUTE, theme=n.zone.theme, rooms=(room,))
        super().__init__(Instance(route, "fuchsia", seed=visit.seed, came_from="back"), game, arrive=arrive)
        level = self.level
        rng = random.Random(f"{visit.seed}/{n.path}/things")
        doors = [thing for stair, thing in self.stairs if stair.to.startswith("door")]
        self.doors = doors
        # The clue to the true door (only on the true path).
        self.tracks: tuple[float, float] | None = None
        self.sign: Signpost | None = None
        if n.clue == "tracks":
            door = doors[n.true_door]
            self.tracks = (door.x - TRACK_LENGTH, door.x - 10)
        elif n.clue == "sign":
            x = 5 * TILE + TILE / 2
            self.sign = Signpost(x, level.ground_y(x), safari.sign_text(n))
        # Tall grass: patches between the doors (not in front of them).
        blocked = [d.x for d in doors] + [self.stairs[0][1].x] + ([self.sign.x] if self.sign else [])
        self.grass: list[tuple[float, float]] = []
        for _ in range(rng.randint(3, 4)):
            for _try in range(12):
                w = rng.randint(4, 8) * TILE
                x0 = rng.uniform(6 * TILE, level.width - 4 * TILE - w)
                spans = self.grass + ([self.tracks] if self.tracks else [])  # (grass keeps off the trail)
                if all(not (x0 - 2 * TILE < b < x0 + w + 2 * TILE) for b in blocked) and \
                        all(x0 + w + TILE < a or b + TILE < x0 for a, b in spans):
                    self.grass.append((x0, x0 + w))
                    break
        self.blades = [(x, rng.randint(-3, 3), rng.random()) for a, b in self.grass for x in range(round(a), round(b), 3)]
        # Key items deep in: the Gold Teeth in a dead end of the deepest zone,
        # HM03 Surf at the heart.
        self.pickup: Pickup | None = None
        keys = game.bag.key_items
        x = level.width * 0.6
        if n.dead_end and n.zone is safari.ZONES[-1] and safari.GOLD_TEETH not in keys:
            self.pickup = Pickup(x, level.ground_y(x), safari.GOLD_TEETH, [
                ("", "Something glints in the mud... a set of false teeth, made of solid gold!"),
                ("", "You found the Gold Teeth! They must be the Safari Zone Warden's.")])
        elif n.heart and safari.SURF not in keys:
            self.pickup = Pickup(x, level.ground_y(x), safari.SURF, [
                ("", "Deep in the marsh stands a little hut: the Secret House!"),
                ("", "A note on the table: \"You've reached the heart of the Safari Zone. Take this as your prize.\""),
                ("", "You received HM03 Surf!")])
        self.last_x = self.player.x

    # ------------------------------------------------------------------ rules

    def where(self) -> str:
        return f"Safari Zone   {self.node.zone.name}   steps left: {self.visit.steps}"

    def location(self) -> dict:
        """Saved outside the Safari Zone: a visit doesn't outlast a save."""
        b = next(b for b in TOWNS["fuchsia"].buildings if b.name == BUILDING)
        return {"kind": "town", "town": "fuchsia", "x": b.x + 4 * TILE, "facing": 1}

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.panel or self.next_scene:
            return
        self.visit.walked += abs(self.player.x - self.last_x)
        self.last_x = self.player.x
        while self.visit.walked >= TILE:
            self.visit.walked -= TILE
            self.visit.steps -= 1
            if self.visit.steps <= 0:
                self.show(quest_ui.Dialogue([("PA", "Ding-dong! Time's up! Please return to the Safari Zone's "
                                                    "entrance.")]), after=self._leave)
                return
            if self._in_grass() and random.random() < safari.GRASS_CHANCE:
                self._encounter()
                return

    def _in_grass(self) -> bool:
        return self.player.on_ground and any(a <= self.player.x <= b for a, b in self.grass)

    def _encounter(self) -> None:
        """A wild Pokémon leaps out of the grass and challenges the player to
        its game (scenes/safari_games.py): Play, or Decline and move on."""
        from .safari_games import Challenge, game_for
        zone = self.node.zone
        species = random.choices([s for s, _ in zone.grass], weights=[w for _, w in zone.grass])[0]
        name = SPECIES[species].name
        challenge = Challenge(species)

        def chosen():
            if challenge.picked != "play":
                self.show(quest_ui.Dialogue([("", f"You decline. The {name} shrugs and slips back into the grass.")]))
                return
            game = game_for(species)(self, species, zone.theme.backdrop, lambda score: self._played(species, score))
            self.next_scene = Transition(self, game, flashes=0)
        self.show(challenge, after=chosen)

    def _played(self, species: str, score: int) -> None:
        """Back from a game: its score earns Kudos with the species; at
        `KUDOS_NEEDED` it joins the team (`Game.kudos`)."""
        from ..mechanics.pokemon import Monster
        from ..world import quests
        from .safari_games import GAMES
        name = SPECIES[species].name
        verdict = ("The {} looks impressed!" if score >= 30 else "The {} nods." if score >= 15
                   else "The {} doesn't look impressed.").format(name)
        pages = [("", f"You scored {score}! {verdict}")]
        if safari.joined(self.game, species):
            pages.append(("", f"(The {name}s of the Safari Zone already count you as a friend.)"))
        else:
            gained = safari.kudos_for(GAMES[species], score)
            total = min(safari.KUDOS_NEEDED, self.game.kudos.get(species, 0) + gained)
            self.game.kudos[species] = total
            pages.append(("", f"+{gained} Kudos with {name}: {total}/{safari.KUDOS_NEEDED}."))
            if total >= safari.KUDOS_NEEDED:
                monster = Monster.create(species, self.node.zone.level)
                where = self.game.add_member(monster, quests.active_limit(self.game))
                pages.append(("", f"The {name} has taken a real liking to you!"))
                pages.append(("", f"{name} (Lv{monster.level}) joins you! " + (
                    "It's in your party." if where == "party" else "It went to the reserve (swap at a Recruitment "
                                                                   "Center).")))
                saves.autosave(self)
                self.show(quest_ui.Dialogue(pages))
                return
        pages.append(("", f"The {name} bounds back into the tall grass."))
        self.show(quest_ui.Dialogue(pages))

    def _leave(self) -> None:
        from .town import TownScene  # (it builds on the map scenes)
        town = TownScene(self.game, TOWNS["fuchsia"], arrive=BUILDING)
        saves.autosave(town)
        self.next_scene = Transition(self, town, flashes=0)

    def _go(self, to: str) -> None:
        v = self.visit
        if to == "back":
            if not v.path:  # the first map's door back: out
                self.show(quest_ui.Dialogue([("", "You leave the Safari Zone.")]), after=self._leave)
                return
            came = v.path[-1]
            v.path = v.path[:-1]
            nxt = SafariScene(self.game, v, arrive=f"door{came}")
        else:
            v.path = v.path + (int(to[4:]),)
            nxt = SafariScene(self.game, v, arrive="back")
        self.next_scene = Transition(self, nxt, flashes=0)

    def interact(self) -> None:
        if self.pickup and not self.pickup.taken and self.player.body_rect.colliderect(self.pickup.rect):
            self.pickup.taken = True
            self.game.bag.key_items.append(self.pickup.item)
            self.show(quest_ui.Dialogue(self.pickup.lines))
            return
        if self.sign and self.player.body_rect.colliderect(self.sign.rect):
            self.show(quest_ui.Dialogue([("", "A weathered signpost:"), ("", self.sign.text)]))
            return
        at = self._stair_at_player()
        if at:
            self._go(at[0].to)
            return
        super().interact()

    def prompt(self):
        if self.pickup and not self.pickup.taken and self.player.body_rect.colliderect(self.pickup.rect):
            return self.pickup.x, self.pickup.ground - 26
        if self.sign and self.player.body_rect.colliderect(self.sign.rect):
            return self.sign.x, self.sign.ground - 44
        return super().prompt()

    def _draw_door_label(self, window: pygame.Surface) -> None:
        """Standing at a door: what it is (no names: it's a maze)."""
        at = self._stair_at_player()
        if at:
            stair, thing = at
            text = ("Exit" if not self.visit.path else "Back") if stair.to == "back" else "Onward"
            door_label(window, text, thing.x - self.camera, thing.rect.top)

    # ------------------------------------------------------------------ draw

    def draw_things(self, layer: pygame.Surface) -> None:
        super().draw_things(layer)
        if self.tracks:  # three-toed prints leading to the true door
            a, b = self.tracks
            for i, x in enumerate(range(round(a), round(b), 13)):
                y = self.level.ground_y(x) - 1 - (i % 2) * 3
                pygame.draw.ellipse(layer, (58, 40, 26), (x - 3, y - 2, 7, 4))  # the pad
                for dx in (-3, 0, 3):  # three toes, pointing on to the door
                    pygame.draw.circle(layer, (58, 40, 26), (x + 4, y - 3 + dx), 1)
        if self.sign:
            self.sign.draw(layer)
        if self.pickup and not self.pickup.taken:
            self.pickup.draw(layer)

    def draw_front(self, layer: pygame.Surface) -> None:
        """Tall grass, swaying, in front of the player's feet."""
        dark, light = (40, 110, 40), (86, 168, 70)
        for x, lean, phase in self.blades:
            g = self.level.ground_y(x)
            sway = math.sin(self.t * 2.2 + phase * 6) * 1.5 + lean * 0.4
            h = GRASS_H - (x * 7 % 5)
            pygame.draw.line(layer, dark, (x, g + 1), (x + sway, g - h), 2)
            pygame.draw.line(layer, light, (x + 1, g), (x + 1 + sway, g - h + 3), 1)


def kudos_text(kudos: dict[str, int]) -> str:
    """"Kudos: Scyther 54/100, Chansey joined" ("" before any)."""
    if not kudos:
        return ""
    parts = [f"{SPECIES[s].name} " + ("joined" if k >= safari.KUDOS_NEEDED else f"{k}/{safari.KUDOS_NEEDED}")
             for s, k in kudos.items()]
    return "Kudos: " + ", ".join(parts)


class SafariGate:
    """The Safari Zone's entrance desk: pay `FEE` for `STEPS` steps, or not."""

    def __init__(self, money: int, kudos: dict[str, int] | None = None):
        self.money = money
        self.kudos = kudos_text(kudos or {})
        self.options = (("enter", f"Enter ({money_text(safari.FEE)})"), ("", "Not now"))
        self.choice = 0
        self.picked = ""
        self.rect = pygame.Rect(0, 0, 400, 150)
        self.rect.center = (320, 170)

    def handle_key(self, key: int) -> bool:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.choice = (self.choice + (1 if key == pygame.K_DOWN else -1)) % len(self.options)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            self.picked = self.options[self.choice][0]
            return True
        elif key in (pygame.K_x, pygame.K_BACKSPACE, pygame.K_ESCAPE):
            return True
        return False

    def _row_y(self, i: int) -> int:
        return self.rect.bottom - 18 - (len(self.options) - i) * 17

    def draw(self, canvas: pygame.Surface) -> None:
        ui.window_box(canvas, self.rect)
        ui.cursor(canvas, self.rect.x + 16, self._row_y(self.choice) + 6)

    def draw_overlay(self, window: pygame.Surface) -> None:
        r = self.rect
        ui.text(window, "The Safari Zone", (r.x + 12, r.y + 9), ui.YELLOW)
        lines = (f"{safari.STEPS} steps through a maze of wild lands, new every visit.",
                 "The deeper you go, the rarer the Pokémon. Mind the dead ends,",
                 f"and read the signs and tracks.   You have {money_text(self.money)}.",
                 self.kudos)
        for i, line in enumerate(lines):
            ui.text(window, line, (r.x + 12, r.y + 29 + i * 13), ui.WHITE, size=22)
        for i, (_, label) in enumerate(self.options):
            ui.text(window, label, (r.x + 22, self._row_y(i)), ui.YELLOW if i == self.choice else ui.WHITE, size=26)
