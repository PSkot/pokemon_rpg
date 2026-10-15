"""Try the hats in a hat sheet on a Pokémon, and tune where they sit.

    python tools/hat_viewer.py [species] [sheet]   (default: bulbasaur hats_new.png)

Hat sheets are the hats*.png files in assets/sprites/pixellab/: grids of
32×32 hats. Hats may be drawn on a reference face (skin colour); the face
and its outline are cut out, leaving a hole the Pokémon's face shows
through, so the hat covers the head like a helmet.

A hat is placed by two points:
- the head anchor: where on the Pokémon the hat sits (top of the head),
  one per animation frame, since the head moves;
- the hat anchor: the point of the hat that goes there. For a hat drawn
  on a face it lines the face hole up with the Pokémon's face; otherwise
  it is the bottom centre, a bit up so the hat sits down over the head.

Head anchors are found automatically (the head of walk frame 0 is matched
against every frame) and can be corrected by hand. Everything is saved to
assets/sprites/pixellab/hat_anchors.json on every change.

Controls
  Left/Right or click a hat   choose hat (Left/Right: only kept ones, if any)
  K                           keep / drop this hat (dropped ones are dimmed)
  Tab                         next hat sheet
  Up/Down                     choose animation
  Space                       pause / play;  , and .  step frames
  click on the Pokémon        put this frame's head anchor there
  I J K L                     nudge this frame's head anchor
  R                           re-detect this frame's head anchor
  W A S D                     nudge this hat (its own anchor)
  Backspace                   reset this hat
  G                           mirror this hat
  E                           keep this hat's face (if its own colours were cut out)
  [ and ]                     hat size (per species and sheet)
  N                           smooth / pixel (nearest) scaling of the hat
  F  face the other way    M  show anchors    H  hide hat    B  background
"""

import json
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from game import settings  # noqa: E402
from game.engine.hats import ANCHORS_JSON, HAT, SPRITES, HatSheet, load_data  # noqa: E402
from game.mechanics import pokemon  # noqa: E402

SCALES = [0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25]
ZOOM = 4                    # stage zoom
PAD = 24                    # room around the 64×64 frame for the hat
WINDOW = (1280, 720)
BACKGROUNDS = [(143, 209, 106), (43, 45, 49), (216, 216, 208)]


# --- data ---------------------------------------------------------------

def save_data(data: dict) -> None:
    # One frame row / hat per line, so the file stays readable and diffs well.
    def block(items: dict, indent: str) -> list[str]:
        items = sorted(items.items(), key=lambda kv: int(kv[0]))
        return [f"{indent}{json.dumps(k)}: {json.dumps(v)}" + ("," if i < len(items) - 1 else "")
                for i, (k, v) in enumerate(items)]

    lines = ["{", '  "heads": {']
    heads = list(data["heads"].items())
    for i, (sheet, rows) in enumerate(heads):
        lines += [f"    {json.dumps(sheet)}: {{", *block(rows, "      "),
                  "    }" + ("," if i < len(heads) - 1 else "")]
    lines += ["  },", '  "sheets": {']
    sheets = list(data["sheets"].items())
    for i, (sheet, conf) in enumerate(sheets):
        lines += [f"    {json.dumps(sheet)}: {{",
                  f'      "scale": {json.dumps(conf.get("scale", {}))},',
                  f'      "smooth": {json.dumps(conf.get("smooth", True))},',
                  f'      "keep": {json.dumps(conf.get("keep", []))},',
                  '      "hats": {', *block(conf.get("hats", {}), "        "), "      }",
                  "    }" + ("," if i < len(sheets) - 1 else "")]
    lines += ["  }", "}"]
    ANCHORS_JSON.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- head anchors -------------------------------------------------------

def detect_head(reference: pygame.Surface, ref_anchor: tuple[int, int],
                frame: pygame.Surface) -> tuple[int, int]:
    """Find the head of `reference` (around `ref_anchor`) in `frame`.

    Compares the head's pixels at every nearby offset and keeps the closest
    match. Effects that cover the head (e.g. a beam) can fool it.
    """
    ax, ay = ref_anchor
    area = pygame.Rect(ax - 9, ay - 5, 22, 20).clip(reference.get_rect())
    template = [(x, y, reference.get_at((x, y))) for x in range(area.left, area.right)
                for y in range(area.top, area.bottom)]
    template = [(x, y, c) for x, y, c in template if c.a]
    w, h = frame.get_size()
    best = None
    for dx in range(-6, 9):
        for dy in range(-16, 24):
            cost = 0
            for x, y, c in template:
                x2, y2 = x + dx, y + dy
                p = frame.get_at((x2, y2)) if 0 <= x2 < w and 0 <= y2 < h else None
                if p is None or not p.a:
                    cost += 300
                else:
                    cost += abs(p.r - c.r) + abs(p.g - c.g) + abs(p.b - c.b)
                if best and cost >= best[0]:
                    break
            if not best or cost < best[0]:
                best = (cost, dx, dy)
    return ax + best[1], ay + best[2]


def default_ref_anchor(frame: pygame.Surface) -> tuple[int, int]:
    """A first guess before anything is set: the top of the front third."""
    box = frame.get_bounding_rect()
    x = box.right - box.width // 6
    y = next((y for y in range(box.top, box.bottom) if frame.get_at((x, y)).a), box.top)
    return x, y


class Viewer:
    def __init__(self, species_key: str, sheet: str):
        self.species = pokemon.SPECIES[species_key]
        self.species_key = species_key
        self.anims = pokemon.animations(self.species)
        self.names = [n for n in self.species.anims if n != "idle"]
        self.sheets = sorted(p.name for p in SPRITES.glob("hats*.png"))
        self.sheet_i = self.sheets.index(sheet)
        self.loaded: dict[str, HatSheet] = {}
        self.data = load_data()
        self.anim_i = 0
        self.hat_i = 0
        self.t = 0.0
        self.paused = False
        self.frame_i = 0
        self.flip = False
        self.show_marks = True
        self.show_hat = True
        self.bg = 0
        self.font = pygame.font.SysFont("consolas,dejavusansmono,monospace", 16)
        self.small = pygame.font.SysFont("consolas,dejavusansmono,monospace", 13)
        self._fill_missing_heads()

    # data access

    def spec(self, name: str | None = None) -> pokemon.AnimSpec:
        return self.species.anims[name or self.names[self.anim_i]]

    def head_list(self, spec: pokemon.AnimSpec) -> list:
        return self.data["heads"].setdefault(spec.sheet, {}).setdefault(str(spec.row), [])

    def _fill_missing_heads(self) -> None:
        walk = self.spec("walk")
        reference = self.anims["walk"].frames[0]
        walk_heads = self.head_list(walk)
        if not walk_heads:
            walk_heads.append(list(default_ref_anchor(reference)))
        ref_anchor = tuple(walk_heads[0])
        for name in self.names:
            heads = self.head_list(self.spec(name))
            for i, frame in enumerate(self.anims[name].frames):
                if i >= len(heads):
                    heads.append(list(detect_head(reference, ref_anchor, frame)))
        self.save()

    def save(self) -> None:
        save_data(self.data)

    @property
    def sheet(self) -> HatSheet:
        name = self.sheets[self.sheet_i]
        if name not in self.loaded:
            self.loaded[name] = HatSheet(name)
        return self.loaded[name]

    @property
    def conf(self) -> dict:
        """This sheet's saved settings."""
        return self.data["sheets"].setdefault(self.sheet.name, {"scale": {}, "smooth": True, "keep": [], "hats": {}})

    def step_hat(self, step: int) -> None:
        """The next (step 1) or previous (-1) hat, going through kept hats only if there are any."""
        keep = self.conf.get("keep") or range(len(self.sheet))
        i = self.hat_i
        while True:
            i = (i + step) % len(self.sheet)
            if i in keep:
                self.hat_i = i
                return

    @property
    def scale(self) -> float:
        return self.conf["scale"].get(self.species_key, self.sheet.default_scale)

    @property
    def smooth(self) -> bool:
        return self.conf.get("smooth", True)

    def hat_info(self, index: int) -> dict:
        info = self.conf["hats"].get(str(index), {})
        return {"anchor": info.get("anchor", self.sheet.default_anchor(index, self.scale)),
                "flip": info.get("flip", False), "keep_face": info.get("keep_face", False)}

    def set_hat_info(self, index: int, **changes) -> None:
        self.conf["hats"][str(index)] = self.hat_info(index) | changes
        self.save()

    def hat_image(self, index: int) -> pygame.Surface:
        keep = self.hat_info(index)["keep_face"]
        return (self.sheet.originals if keep else self.sheet.stripped)[index]

    # drawing

    @property
    def anim(self):
        return self.anims[self.names[self.anim_i]]

    def current_frame(self) -> int:
        if self.paused:
            return self.frame_i
        return int(self.t * self.anim.fps) % len(self.anim.frames)

    def frame_topleft(self, index: int) -> tuple[int, int]:
        """Where the frame goes in the composite (feet on a fixed line, like the game)."""
        feet = (PAD + 64 // 2, PAD + 60)
        return self.anim.place(index, *feet).topleft

    def compose(self, index: int, marks: bool) -> pygame.Surface:
        """Pokémon plus hat at game resolution (facing right), PAD px of room around."""
        size = 64 + 2 * PAD
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        fx, fy = self.frame_topleft(index)
        canvas.blit(self.anim.frames[index], (fx, fy))
        head = self.head_list(self.spec())[index]
        hx, hy = fx + head[0], fy + head[1]
        info = self.hat_info(self.hat_i)
        if self.show_hat:
            hat = self.hat_image(self.hat_i)
            ax, ay = info["anchor"]
            if info["flip"]:
                hat = pygame.transform.flip(hat, True, False)
                ax = HAT - 1 - ax
            if self.scale != 1:
                scale = pygame.transform.smoothscale_by if self.smooth else pygame.transform.scale_by
                hat = scale(hat, self.scale)
            canvas.blit(hat, (round(hx - ax * self.scale), round(hy - ay * self.scale)))
        if marks:
            canvas.set_at((hx, hy), (255, 40, 40))
        return canvas

    def stage_rect(self) -> pygame.Rect:
        size = (64 + 2 * PAD) * ZOOM
        return pygame.Rect(20, (WINDOW[1] - size) // 2 - 20, size, size)

    def grid_rect(self) -> pygame.Rect:
        return pygame.Rect(WINDOW[0] - 8 * HAT * 2 - 20, 40, 8 * HAT * 2, 8 * HAT * 2)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((30, 31, 34))
        index = self.current_frame()

        stage = self.stage_rect()
        pygame.draw.rect(screen, BACKGROUNDS[self.bg], stage)
        image = self.compose(index, self.show_marks)
        if self.flip:
            image = pygame.transform.flip(image, True, False)
        screen.blit(pygame.transform.scale_by(image, ZOOM), stage)

        # In-game size: the game draws at 640×360 and scales ×2.
        game = pygame.Rect(stage.right + 20, stage.top, (64 + 2 * PAD) * 2, (64 + 2 * PAD) * 2)
        pygame.draw.rect(screen, BACKGROUNDS[self.bg], game)
        image = self.compose(index, False)
        if self.flip:
            image = pygame.transform.flip(image, True, False)
        screen.blit(pygame.transform.scale_by(image, settings.SCALE), game)
        self.text(screen, "in-game size", (game.left, game.bottom + 6), self.small)

        # Hat grid
        grid = self.grid_rect()
        pygame.draw.rect(screen, (56, 58, 64), grid.inflate(8, 8))
        for i in range(len(self.sheet)):
            cell = pygame.Rect(grid.left + (i % 8) * HAT * 2, grid.top + (i // 8) * HAT * 2, HAT * 2, HAT * 2)
            if str(i) in self.conf["hats"]:
                pygame.draw.rect(screen, (70, 72, 80), cell)
            image = pygame.transform.scale_by(self.hat_image(i), 2)
            if self.conf.get("keep") and i not in self.conf["keep"]:
                image.set_alpha(60)
            screen.blit(image, cell)
            if i == self.hat_i:
                pygame.draw.rect(screen, (240, 192, 64), cell, 2)
        self.text(screen, f"{self.sheet.name}  (Tab: next sheet; shaded = adjusted, dim = dropped)",
                  (grid.left, grid.bottom + 8), self.small)

        info = self.hat_info(self.hat_i)
        head = self.head_list(self.spec())[index]
        lines = [
            f"{self.species.name}  ·  {self.names[self.anim_i]}  frame {index + 1}/{len(self.anim.frames)}"
            + ("  (paused)" if self.paused else ""),
            f"hat {self.hat_i}  ·  size {self.scale} {'smooth' if self.smooth else 'pixel'}  ·  "
            f"hat anchor {info['anchor']}" + ("  mirrored" if info["flip"] else "")
            + ("  face kept" if info["keep_face"] else ""),
            f"head anchor {head}",
            "Left/Right hat  Tab sheet  Up/Down anim  Space pause  , . step  click/IJKL head  R redetect",
            "WASD hat  Bksp reset hat  K keep  G mirror  E keep face  [ ] size  N smooth  F face  M marks  H hat  B bg",
        ]
        y = WINDOW[1] - 20 * len(lines) - 10
        for line in lines:
            self.text(screen, line, (20, y))
            y += 20

    def text(self, screen, text, pos, font=None) -> None:
        screen.blit((font or self.font).render(text, True, (230, 230, 230)), pos)

    # input

    def pause_here(self) -> int:
        if not self.paused:
            self.frame_i = self.current_frame()
            self.paused = True
        return self.frame_i

    def nudge_head(self, dx: int, dy: int) -> None:
        index = self.pause_here()
        head = self.head_list(self.spec())[index]
        head[0] += -dx if self.flip else dx
        head[1] += dy
        self.save()

    def nudge_hat(self, dx: int, dy: int) -> None:
        # Moving the hat right means moving its anchor left.
        ax, ay = self.hat_info(self.hat_i)["anchor"]
        if self.flip != self.hat_info(self.hat_i)["flip"]:
            dx = -dx
        self.set_hat_info(self.hat_i, anchor=[ax - dx, ay - dy])

    def click(self, pos: tuple[int, int]) -> None:
        grid = self.grid_rect()
        if grid.collidepoint(pos):
            i = (pos[1] - grid.top) // (HAT * 2) * 8 + (pos[0] - grid.left) // (HAT * 2)
            if i < len(self.sheet):
                self.hat_i = i
            return
        stage = self.stage_rect()
        if stage.collidepoint(pos):
            index = self.pause_here()
            x = (pos[0] - stage.left) // ZOOM
            y = (pos[1] - stage.top) // ZOOM
            if self.flip:
                x = 64 + 2 * PAD - 1 - x
            fx, fy = self.frame_topleft(index)
            self.head_list(self.spec())[index][:] = [x - fx, y - fy]
            self.save()

    def key(self, key: int) -> None:
        n_anims, n_frames = len(self.names), len(self.anim.frames)
        if key in (pygame.K_RIGHT, pygame.K_LEFT):
            self.step_hat(1 if key == pygame.K_RIGHT else -1)
        elif key == pygame.K_k:
            keep = self.conf.setdefault("keep", [])
            if self.hat_i in keep:
                keep.remove(self.hat_i)
            else:
                keep.append(self.hat_i)
                keep.sort()
            self.save()
        elif key == pygame.K_TAB:
            self.sheet_i = (self.sheet_i + 1) % len(self.sheets)
            self.hat_i = min(self.hat_i, len(self.sheet) - 1)
        elif key in (pygame.K_UP, pygame.K_DOWN):
            self.anim_i = (self.anim_i + (1 if key == pygame.K_DOWN else -1)) % n_anims
            self.t = self.frame_i = 0
        elif key == pygame.K_SPACE:
            if self.paused:
                self.t = self.frame_i / self.anim.fps
                self.paused = False
            else:
                self.pause_here()
        elif key in (pygame.K_COMMA, pygame.K_PERIOD):
            index = self.pause_here()
            self.frame_i = (index + (1 if key == pygame.K_PERIOD else -1)) % n_frames
        elif key in (pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l):
            self.nudge_head(*{pygame.K_i: (0, -1), pygame.K_k: (0, 1),
                              pygame.K_j: (-1, 0), pygame.K_l: (1, 0)}[key])
        elif key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
            self.nudge_hat(*{pygame.K_w: (0, -1), pygame.K_s: (0, 1),
                             pygame.K_a: (-1, 0), pygame.K_d: (1, 0)}[key])
        elif key == pygame.K_r:
            index = self.pause_here()
            walk_head = tuple(self.head_list(self.spec("walk"))[0])
            self.head_list(self.spec())[index][:] = detect_head(
                self.anims["walk"].frames[0], walk_head, self.anim.frames[index])
            self.save()
        elif key == pygame.K_BACKSPACE:
            self.conf["hats"].pop(str(self.hat_i), None)
            self.save()
        elif key == pygame.K_g:
            self.set_hat_info(self.hat_i, flip=not self.hat_info(self.hat_i)["flip"])
        elif key == pygame.K_e:
            self.set_hat_info(self.hat_i, keep_face=not self.hat_info(self.hat_i)["keep_face"])
        elif key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            i = min(range(len(SCALES)), key=lambda j: abs(SCALES[j] - self.scale))
            i = max(0, min(len(SCALES) - 1, i + (1 if key == pygame.K_RIGHTBRACKET else -1)))
            self.conf["scale"][self.species_key] = SCALES[i]
            self.save()
        elif key == pygame.K_n:
            self.conf["smooth"] = not self.smooth
            self.save()
        elif key == pygame.K_f:
            self.flip = not self.flip
        elif key == pygame.K_m:
            self.show_marks = not self.show_marks
        elif key == pygame.K_h:
            self.show_hat = not self.show_hat
        elif key == pygame.K_b:
            self.bg = (self.bg + 1) % len(BACKGROUNDS)


def main() -> None:
    species = sys.argv[1] if len(sys.argv) > 1 else "bulbasaur"
    sheet = sys.argv[2] if len(sys.argv) > 2 else "hats_new.png"
    pygame.init()
    screen = pygame.display.set_mode(WINDOW)
    pygame.display.set_caption("Hat viewer")
    viewer = Viewer(species, sheet)
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                viewer.key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                viewer.click(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                viewer.step_hat(-event.y)
        if not viewer.paused:
            viewer.t += dt
        viewer.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
