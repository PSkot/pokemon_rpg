"""Sprite sheet loading and frame animations."""

from pathlib import Path

import pygame


def load_sheet(path: Path, frame_w: int, frame_h: int) -> list[list[pygame.Surface]]:
    """Cut a sprite sheet into rows of frames, dropping fully transparent frames."""
    sheet = pygame.image.load(path).convert_alpha()
    rows = []
    for y in range(0, sheet.get_height() - frame_h + 1, frame_h):
        row = []
        for x in range(0, sheet.get_width() - frame_w + 1, frame_w):
            frame = sheet.subsurface((x, y, frame_w, frame_h)).copy()
            if frame.get_bounding_rect().width:
                row.append(frame)
        rows.append(row)
    return rows


VISIBLE_ALPHA = 128  # pixels at least this opaque count as the sprite's body (baselines)


class Animation:
    """A sequence of frames played at a fixed speed.

    Frames are drawn so that their baseline (where the feet touch the ground)
    lines up with the character's feet position. By default the whole
    animation shares one baseline: the lowest opaque pixel row of any frame.
    That keeps in-frame motion such as a run cycle's bounce. With
    `per_frame_baseline`, every frame is aligned by its own lowest pixel
    instead; use that when the code moves the character itself (e.g. jumps).
    Pass `baseline` to set the row explicitly, for sheets whose effects (auras,
    shields) reach below the feet: one row for every frame, or a row per
    frame (None = that frame's own lowest pixel, or the shared one).
    """

    def __init__(self, frames: list[pygame.Surface], fps: float, loop: bool = True,
                 per_frame_baseline: bool = False,
                 baseline: int | tuple[int | None, ...] | None = None):
        self.frames = frames
        self.flipped = [pygame.transform.flip(f, True, False) for f in frames]
        self.fps = fps
        self.loop = loop
        # (Ignore nearly transparent rows: smoothly scaled icons fade out at the edges.)
        bottoms = [f.get_bounding_rect(min_alpha=VISIBLE_ALPHA).bottom for f in frames]
        if isinstance(baseline, int):
            self.baselines = [baseline] * len(frames)
        elif per_frame_baseline:
            self.baselines = bottoms
        else:
            self.baselines = [max(bottoms)] * len(frames)
        if isinstance(baseline, tuple):
            self.baselines = [b if b is not None else own for b, own in zip(baseline, self.baselines)]
        # Each frame's head anchor (where a hat goes), if known; see hats.py.
        self.heads: list[tuple[int, int]] | None = None

    def sub(self, start: int, stop: int, loop: bool | None = None) -> "Animation":
        """Frames `start`..`stop` as their own animation, keeping their baselines."""
        part = Animation(self.frames[start:stop], self.fps, self.loop if loop is None else loop)
        part.baselines = self.baselines[start:stop]
        part.heads = self.heads[start:stop] if self.heads else None
        return part

    def scaled(self, factor: int) -> "Animation":
        """The same animation drawn `factor` times bigger (pixels stay sharp)."""
        big = Animation([pygame.transform.scale_by(f, factor) for f in self.frames], self.fps, self.loop)
        big.baselines = [b * factor for b in self.baselines]
        big.heads = [(x * factor, y * factor) for x, y in self.heads] if self.heads else None
        return big

    @property
    def duration(self) -> float:
        return len(self.frames) / self.fps

    def index_at(self, t: float) -> int:
        i = int(t * self.fps)
        if self.loop:
            return i % len(self.frames)
        return min(i, len(self.frames) - 1)

    def finished(self, t: float) -> bool:
        return not self.loop and t >= self.duration

    def frame(self, index: int, flip: bool = False) -> pygame.Surface:
        return (self.flipped if flip else self.frames)[index]

    def place(self, index: int, centre_x: float, feet_y: float, flip: bool = False) -> pygame.Rect:
        """Where frame `index` goes so its baseline sits on `feet_y`."""
        return self.frame(index, flip).get_rect(topleft=(
            round(centre_x - self.frames[index].get_width() / 2),
            round(feet_y - self.baselines[index])))

    def body_rect(self, index: int, centre_x: float, feet_y: float, flip: bool = False) -> pygame.Rect:
        """The opaque part of frame `index` when placed at `centre_x`, `feet_y`."""
        top_left = self.place(index, centre_x, feet_y, flip).topleft
        return self.frame(index, flip).get_bounding_rect().move(top_left)
