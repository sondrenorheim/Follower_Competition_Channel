"""Club Relic arena layout."""

import random
from typing import Tuple

import config
from shared import ArenaTemplate, ArenaShape


class ClubRelicArena(ArenaTemplate):
    """Rectangular arena for relic chase."""

    WIDTH = int(config.FIGHTER_ARENA_RECT[2])
    HEIGHT = int(config.FIGHTER_ARENA_RECT[3])
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False

    def __init__(self):
        super().__init__()
        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.left = float(arena_x)
        self.top = float(arena_y)
        self.right = self.left + float(arena_w)
        self.bottom = self.top + float(arena_h)
        self.center_x = (self.left + self.right) / 2
        self.center_y = (self.top + self.bottom) / 2
        self.current_width = float(arena_w)
        self.current_height = float(arena_h)
        self.initial_radius = self.current_width / 2
        self.current_radius = self.initial_radius

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return (self.left, self.top, self.right, self.bottom)

    def get_random_point(self, margin: float = 0.0) -> Tuple[float, float]:
        left = self.left + margin
        right = self.right - margin
        top = self.top + margin
        bottom = self.bottom - margin
        if right <= left or bottom <= top:
            return (self.center_x, self.center_y)
        return (
            random.uniform(left, right),
            random.uniform(top, bottom),
        )
