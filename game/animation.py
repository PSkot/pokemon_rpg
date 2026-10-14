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


class Animation:
    """A sequence of frames played at a fixed speed.

    Frames are drawn so that their baseline (where the feet touch the ground)
    lines up with the character's feet position. By default the whole
    animation shares one baseline: the lowest opaque pixel row of any frame.
    That keeps in-frame motion such as a run cycle's bounce. With
    `per_frame_baseline`, every frame is aligned by its own lowest pixel
    instead; use that when the code moves the character itself (e.g. jumps).
    """

    def __init__(self, frames: list[pygame.Surface], fps: float, loop: bool = True,
                 per_frame_baseline: bool = False):
        self.frames = frames
        self.flipped = [pygame.transform.flip(f, True, False) for f in frames]
        self.fps = fps
        self.loop = loop
        bottoms = [f.get_bounding_rect().bottom for f in frames]
        self.baselines = bottoms if per_frame_baseline else [max(bottoms)] * len(frames)

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
