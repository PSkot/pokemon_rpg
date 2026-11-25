"""A town's map: buildings to walk past, a quest board, and doorways onto
routes (Up).

Arriving heals the party, and the town becomes where a fainted party wakes
up. The town's name shows for a moment on arrival. Up at the quest board
opens it; Up at a building a quest step needs does that step, and Up at a
Poké Mart goes inside (mart.py); a route's doorway can stay shut until a
quest is started or done. Up next to a townsfolk (towns.Folk) talks to
them: a quest step, a quest they give, a trial they send the player to
(a route with `Route.folk`), or a chat line.
"""

import math
from functools import cache

import pygame

from .. import saves, settings
from ..engine import ui
from ..engine.animation import Animation
from ..engine.scene import Transition
from ..world import tileset
from ..world import quests
from ..world.quests import QUESTS
from ..world.instance import ROUTES, Instance
from ..world.level import TILE
from ..world.player import FOOT_SINK
from ..world.progress import Game
from ..mechanics.pokemon import SPECIES, animations
from ..world.towns import TOWNS, Building, Folk, Town, building_mid
from . import quest_ui
from .mart import MartScene
from .recruit import RecruitScene
from .smith import SmithMenu
from .dept_store import DeptStoreScene
from .overworld import HAND_IN_MARK, QUEST_MARK, Doorway, MapScene, OverworldScene, door_label, quest_mark

BANNER_TIME = 2.5   # seconds the town's name shows on arrival
ARRIVE_GAP = 3 * TILE  # how far from the doorway the player arrives
class _NPC:  # what an NPC townsfolk stands like (`Folk.npc`): drawn flat on the ground
    foot_sink = -FOOT_SINK  # (cancels the sink every species' sprite gets, below)


@cache
def _npc_animation(name: str) -> Animation:
    return Animation(tileset.npc_frames(name), fps=6, loop=True)


LINK = "town:"  # a `Town.exits` target that's another part of the same city ("town:<key>"), not a route


def _door_name(target: str) -> str:
    """What a doorway leads to: a route's name, or another part of the city's."""
    return TOWNS[target[len(LINK):]].name if target.startswith(LINK) else ROUTES[target].name


FOLK_REACH = 22  # px from a townsfolk within which Up talks to them


class TownScene(MapScene):
    in_town = True
    def __init__(self, game: Game, town: Town, arrive: str = "home"):
        """`arrive`: "home" (a new game, or after fainting), the key of
        the route the player came back by (they arrive at its doorway, or
        its building for a gym), or the name of a building they came out
        of (no banner then)."""
        super().__init__(game, town.level())
        self.town = town
        game.town = town.key
        game.visited.add(town.key)
        self.healed = game.heal()
        level, palette = self.level, self.level.theme.palette
        ground = level.ground_y(0)
        # (doorway, route key, where: "left"/"right" edge or a column)
        self.doors = [(Doorway(self._door_x(where), ground, palette, art=level.theme.doorway), route, where) for where, route in town.exits]
        out_of = next((b for b in town.buildings
                       if b.name and (b.name == arrive or (arrive in ROUTES and ROUTES[arrive].building == b.name))),
                      None)
        sent_by = next((f for f in town.folk if arrive in ROUTES and ROUTES[arrive].folk == f.key), None)
        self.chats: dict[str, int] = {}  # townsfolk key -> chat lines said
        if arrive == "home":
            self.place_player(town.home_col * TILE + TILE / 2, 1)
        elif out_of:  # (back out of a shop, a gym, ...)
            self.place_player(building_mid(out_of), 1)
            self.t = BANNER_TIME
        elif sent_by:  # back from a trial: next to who sent them
            self.place_player(sent_by.x - FOLK_REACH, 1)
            self.t = BANNER_TIME
        else:  # from a route (the gear counter restocks), or another part of the same city
            if not arrive.startswith(LINK):
                game.arrive(town.key)
            where = town.exit_to(arrive)
            if where == "left":
                self.place_player(level.entry_x + ARRIVE_GAP, 1)
            elif where == "right":
                self.place_player(level.exit_x - ARRIVE_GAP, -1)
            else:  # a doorway in the town: right in front of it
                self.place_player(self._door_x(where), 1)
        self.show_event(quests.reach(game, town.key))

    def _door_x(self, where: str | int) -> float:
        if where == "left":
            return self.level.entry_x
        if where == "right":
            return self.level.exit_x
        return where * TILE + TILE / 2

    def where(self) -> str:
        return self.town.name

    def _door_at_player(self) -> tuple[Doorway, str, str | int] | None:
        """(doorway, route key, where) of the doorway the player stands in."""
        return next((d for d in self.doors if self.player.body_rect.colliderect(d[0].rect)), None)

    @property
    def board_x(self) -> float | None:
        return None if self.town.board_col is None else self.town.board_col * TILE + TILE / 2

    def _at_board(self) -> bool:
        return self.board_x is not None and abs(self.player.x - self.board_x) < 24

    def _route_in(self, building: Building | None):
        """The route walked from `building` (a gym), if any."""
        if not building:
            return None
        return next((r for r in ROUTES.values() if r.building == building.name and self.town.key in r.towns), None)

    def _tree_key(self, building: Building) -> str:
        return f"cut:{self.town.key}/{building.name}"

    def _tree_at(self, building: Building) -> bool:
        """Whether a small tree still grows over `building`'s door (`Building.tree`)."""
        return bool(building.tree) and self._tree_key(building) not in self.game.trainers

    @property
    def folk(self) -> list[Folk]:
        """The town's townsfolk who are here (not gone after their quest: `Folk.gone_after`)."""
        return [f for f in self.town.folk if not (f.gone_after and quests.gone(self.game, f.gone_after))]

    def _building_at_player(self) -> Building | None:
        return next((b for b in self.town.buildings
                     if b.name and b.x <= self.player.x < b.x + tileset.building(b.sprite)[0].get_width()), None)

    def _folk_at_player(self) -> Folk | None:
        return next((f for f in self.folk if abs(self.player.x - f.x) < FOLK_REACH), None)

    def _folk_anim(self, folk: Folk):
        if folk.npc:  # (an NPC's own animation: the smith)
            return _NPC, _npc_animation(folk.npc)
        species = SPECIES[folk.species_for(self.game.starter)]
        return species, animations(species)["idle"]

    def _forge_glow(self, layer: pygame.Surface, x: int, y: int) -> None:
        """The furnace's fire at (`x`, `y`), flickering: a soft orange glow."""
        r = 9 + round(2 * math.sin(self.t * 9) + math.sin(self.t * 23))
        glow = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 150, 40, 70), (r, r), r)
        pygame.draw.circle(glow, (255, 210, 90, 60), (r, r), r // 2)
        layer.blit(glow, (x - r, y - r))

    def _folk_top(self, folk: Folk) -> float:
        species, anim = self._folk_anim(folk)
        return anim.body_rect(0, folk.x, self.level.ground_y(0) + species.foot_sink + FOOT_SINK).top

    def _trial_from(self, folk: Folk):
        """The route `folk` sends the player to now (an active quest is at
        the step of beating it), if any."""
        for quest in quests.active(self.game):
            step = quests.current(self.game, quest.key)
            for target in step.targets if step.kind == "defeat" else ():
                route = ROUTES.get(target)
                if route and route.folk == folk.key and quests.chosen(self.game, quest.key, folk.key):
                    return route
        return None

    def _talk(self, folk: Folk) -> None:
        name = folk.name_for(self.game.starter)
        trial = self._trial_from(folk)
        if trial:
            def go():
                first_map = OverworldScene(Instance(trial, self.town.key), self.game)
                saves.autosave(first_map)
                self.next_scene = Transition(self, first_map, flashes=0)
            line = trial.folk_line or f"The {trial.name} awaits. Go, and show me what you've learned!"
            self.show(quest_ui.Dialogue([(name if not trial.folk_line else "", line)]), after=go)
            return
        if folk.key == quests.SMITH and quests.smith_open(self.game):  # the smithy: salvage, enhance, smelt
            self.show(SmithMenu(self.game), after=lambda: saves.autosave(self))
            return
        event = quests.talk(self.game, folk.key)
        if event:
            self.show_event(event)
            saves.autosave(self)
        elif folk.lines:
            said = self.chats.get(folk.key, 0)
            self.chats[folk.key] = said + 1
            partner = SPECIES[self.game.starter].name
            self.show(quest_ui.Dialogue([(name, folk.lines[said % len(folk.lines)].format(partner=partner))]))

    def interact(self) -> None:
        folk = self._folk_at_player()
        if folk and not self._at_board():
            self._talk(folk)
            return
        if self._at_board():
            event = quests.hand_in(self.game)  # (any board takes any finished quest)
            if event:
                self.show_event(event)
                saves.autosave(self)
            board = quest_ui.QuestBoard(self.game, self.town.name, self.town.key)
            self.show(board, after=lambda: board.taken and self.show_event(quests.accept(self.game, board.taken)))
            return
        door = self._door_at_player()
        if door and door[1].startswith(LINK):  # into another part of the city (`Town.exits` "town:<key>")
            self.next_scene = Transition(self, TownScene(self.game, TOWNS[door[1][len(LINK):]],
                                                         arrive=LINK + self.town.key), flashes=0)
            return
        if door and not quests.open_for(self.game, ROUTES[door[1]].needs):
            self.show(quest_ui.Dialogue([("", quests.blocked_text(self.game, ROUTES[door[1]]))]))
            return
        building = None if door else self._building_at_player()
        if building and building.inside == "mart":
            self.next_scene = Transition(self, MartScene(self.game, self.town), flashes=0)
            return
        if building and building.inside == "dept":  # the Celadon Department Store, its floors
            self.next_scene = Transition(self, DeptStoreScene(self.game, self.town), flashes=0)
            return
        if building and building.inside == "tower":  # the Battle Tower's lobby (once it's open)
            from .battle_tower import TowerLobbyScene, is_open
            if is_open(self.game):
                self.next_scene = Transition(self, TowerLobbyScene(self.game), flashes=0)
            else:
                self.show(quest_ui.Dialogue([("", building.note)]))
            return
        if building and building.inside == "safari":  # the Safari Zone's desk (scenes/safari.py)
            self._safari_gate()
            return
        if building and building.inside == "recruit":
            self.next_scene = Transition(self, RecruitScene(self.game, self.town), flashes=0)
            return
        if building and self._tree_at(building):
            if quests.step(self.game, building.tree) is None:  # (no Cut yet)
                gym = self._route_in(building)
                self.show(quest_ui.Dialogue([("", gym.blocked if gym else building.note)]))
            else:  # cut it down, once and for all
                self.game.trainers.add(self._tree_key(building))
                lead = self.game.party[0].name
                self.show(quest_ui.Dialogue([("", f"{lead} used Cut! The little tree fell. The way in is clear.")]))
                saves.autosave(self)
            return
        gym = self._route_in(building)
        if gym:
            if not quests.open_for(self.game, gym.needs):
                self.show(quest_ui.Dialogue([("", quests.blocked_text(self.game, gym))]))
                return
            first_map = OverworldScene(Instance(gym, self.town.key), self.game)
            saves.autosave(first_map)
            self.next_scene = Transition(self, first_map, flashes=0)
            return
        if building:
            event = quests.visit(self.game, self.town.key, building.name)
            if event:
                self.show_event(event)
                saves.autosave(self)
            elif building.name == "Pokémon Center":  # a checkpoint: heals, and a fainted party wakes up here
                self.game.heal()
                self.game.town = self.town.key
                self.show(quest_ui.Dialogue([("Nurse", "We've restored your Pokémon to full health. "
                                                       "We hope to see you again!")]))
                saves.autosave(self)
            elif early := quests.early_text(self.game, self.town.key, building.name):
                self.show(quest_ui.Dialogue([("", early)]))
            elif building.note_after and quests.is_done(self.game, building.note_after[0]):
                self.show(quest_ui.Dialogue([("", building.note_after[1])]))
            elif building.note:
                self.show(quest_ui.Dialogue([("", building.note)]))
            return
        if door:
            route = ROUTES[door[1]]
            instance = Instance(route, route.other_end(self.town.key), came_from=self.town.key)
            first_map = OverworldScene(instance, self.game)
            saves.autosave(first_map)
            self.next_scene = Transition(self, first_map, flashes=0)

    def _safari_gate(self) -> None:
        from .safari import SafariGate, SafariScene
        from ..world import safari
        gate = SafariGate(self.game.bag.money, self.game.kudos)

        def chosen():
            if gate.picked != "enter":
                return
            if self.game.bag.money < safari.FEE:
                self.show(quest_ui.Dialogue([("", "You can't afford the entrance fee.")]))
                return
            self.game.bag.money -= safari.FEE
            self.next_scene = Transition(self, SafariScene(self.game, safari.Visit()), flashes=0)
        self.show(gate, after=chosen)

    def prompt(self) -> tuple[float, float] | None:
        folk = self._folk_at_player()
        if folk:
            return folk.x, self._folk_top(folk) - 12
        if self._at_board():
            return self.board_x, self.level.ground_y(0) - 74
        door = self._door_at_player()
        if door:
            return door[0].x, door[0].feet_y - 66
        building = self._building_at_player()
        if building and (building.inside or self._route_in(building) or building.name == "Pokémon Center"
                         or building.note):
            return building_mid(building), self.level.ground_y(0) - 60
        return None

    def markers(self) -> list[tuple[float, float]]:
        ground, marks = self.level.ground_y(0), []
        if self.board_x is not None:
            for quest in quests.can_take(self.game, self.town.key):
                marks.append((self.board_x, ground - 60, quest_mark(quest)))
            if quests.ready_to_hand_in(self.game):
                marks.append((self.board_x, ground - 60, HAND_IN_MARK))
        for quest in quests.active(self.game):
            step = quests.current(self.game, quest.key)
            route = None
            if step.kind == "defeat":  # a route's boss, or one of its map trainers (the Lift Key Guard)
                route = ROUTES.get(step.target) or next(
                    (r for r in ROUTES.values() if any(t.key == step.target for t in r.trainers)), None)
            route = route if route and route.building else None
            # (A route without towns, a recruitment map, starts in every such building.)
            if (step.kind == "visit" and step.town == self.town.key) or (
                    route and (self.town.key in route.towns or not route.towns)):
                for b in self.town.buildings:  # the building it needs (a gym: the one its route starts in)
                    if b.name == (route.building if route else step.target):
                        marks.append((building_mid(b), ground - tileset.building(b.sprite)[1] - 20,
                                      quest_mark(quest)))
        if any(quests.ready(self.game, q) for q in QUESTS.values() if q.board == quests.RECRUIT_BOARD):
            for b in self.town.buildings:  # a recruitment has opened
                if b.inside == "recruit":
                    marks.append((building_mid(b), ground - tileset.building(b.sprite)[1] - 20, QUEST_MARK))
        for folk in self.folk:  # a quest to give or to move on, or a trial to send the player to
            if folk is self._folk_at_player():
                continue  # (their name and the Up arrow show instead)
            top = self._folk_top(folk) - 4
            for quest in quests.folk_quests(self.game, folk.key):
                marks.append((folk.x, top, quest_mark(quest)))
            trial = self._trial_from(folk)
            for quest in quests.active(self.game) if trial else ():
                if trial.key in quests.current(self.game, quest.key).targets:
                    marks.append((folk.x, top, quest_mark(quest)))
        return list(dict.fromkeys(marks))

    def draw_things(self, layer: pygame.Surface) -> None:
        ground = round(self.level.ground_y(0))
        for b in self.town.buildings:
            tileset.draw_building(layer, b.sprite, b.x, ground)
            if self._tree_at(b):  # over its door
                tileset.draw_prop(layer, "cut_tree", round(building_mid(b)), ground)
        if self.board_x is not None:
            tileset.quest_board(layer, round(self.board_x), ground, len(quests.can_take(self.game, self.town.key)))
        for door, _, _ in self.doors:
            door.draw(layer)
        for folk in self.folk:  # the smith's furnace behind him and anvil beside him
            if folk.key == quests.SMITH:
                tileset.draw_prop(layer, "furnace", round(folk.x - 46), ground)
                self._forge_glow(layer, round(folk.x - 46) + 5, ground - 17)  # (its fire, in the painting)
                tileset.draw_prop(layer, "anvil", round(folk.x + 32), ground)
        for folk in self.folk:  # facing the player (unless fast asleep)
            species, anim = self._folk_anim(folk)
            flip = self.player.x < folk.x and not folk.asleep
            index = anim.index_at(self.t)
            # (sunk into the ground like the player: the sheets' feet are drawn at a 3/4 angle)
            layer.blit(anim.frame(index, flip), anim.place(index, folk.x, ground + species.foot_sink + FOOT_SINK, flip))
        for side in ("left", "right"):
            if all(where != side for _, _, where in self.doors):  # the town ends here (for now)
                x = TILE if side == "left" else self.level.width - 5 * TILE
                tileset.fence(layer, x, ground, 4 * TILE)

    def draw_overlay(self, window: pygame.Surface) -> None:
        super().draw_overlay(window)
        door = self._door_at_player()
        if door and not self.panel:  # any doorway (in the town, or at its ends): where it leads
            door_label(window, _door_name(door[1]), door[0].x - self.camera, door[0].rect.top)
        for sleeper in (f for f in self.folk if f.asleep):  # Zzz rising over it, by turns
            top = self._folk_top(sleeper)
            for i, letter in enumerate("zZZ"):
                phase = (self.t * 0.6 + i / 3) % 1
                x = sleeper.x - 6 + 10 * phase + 4 * i - self.camera
                ui.text(window, letter, (x, top - 4 - 22 * phase), (230, 236, 255), size=14 + 6 * i)
        folk = self._folk_at_player()
        if folk and not self.panel:  # their name, over them
            ui.text(window, folk.name_for(self.game.starter), (folk.x - self.camera, self._folk_top(folk) - 30),
                    ui.WHITE, size=26, align="center")
        building = None if door or folk else self._building_at_player()
        if building and not self.panel:  # its name, over the roof
            image, base = tileset.building(building.sprite)
            top = self.level.ground_y(0) - base - 16
            ui.text(window, building.name, (building.x + image.get_width() / 2 - self.camera, top), ui.WHITE, size=26,
                    align="center")
        if self.t < BANNER_TIME:
            center = settings.LOGICAL_SIZE[0] / 2
            ui.text(window, self.town.name, (center, 60), ui.YELLOW, size=48, align="center")
            if self.healed:
                ui.text(window, "Your party is rested.", (center, 84), ui.WHITE, size=24, align="center")

    # ----------------------------------------------------------------- saves

    def location(self) -> dict:
        p = self.player
        return {"kind": "town", "town": self.town.key, "x": p.x, "facing": p.facing}

    def restore(self, state: dict) -> None:
        self.place_player(state["x"], state["facing"])
        self.t = BANNER_TIME  # no banner when loading
