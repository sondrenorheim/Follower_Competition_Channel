"""
Side Choice arena.
Square arena split into two halves.
"""

import random
from typing import Tuple

import config
from shared import ArenaTemplate, ArenaShape


class SideChoiceArena(ArenaTemplate):
    WIDTH = int(getattr(config, "SIDE_CHOICE_ARENA_SIZE", 500))
    HEIGHT = WIDTH
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False

    def __init__(self):
        super().__init__()
        self.orientation = str(getattr(config, "SIDE_CHOICE_ORIENTATION", "vertical")).lower()
        self._update_split()

    def _update_split(self):
        self.split_x = self.left + self.current_width / 2
        self.split_y = self.top + self.current_height / 2

    def get_sides(self) -> Tuple[str, str]:
        if self.orientation == "horizontal":
            return ("top", "bottom")
        return ("left", "right")

    def get_side(self, x: float, y: float) -> str:
        if self.orientation == "horizontal":
            return "top" if y < self.split_y else "bottom"
        return "left" if x < self.split_x else "right"

    def get_side_bounds(self, side: str, margin: float = 0.0) -> Tuple[float, float, float, float]:
        left, top, right, bottom = self.get_bounds()

        if self.orientation == "horizontal":
            if side == "top":
                bottom = self.split_y
            else:
                top = self.split_y
        else:
            if side == "left":
                right = self.split_x
            else:
                left = self.split_x

        left += margin
        top += margin
        right -= margin
        bottom -= margin

        return (left, top, right, bottom)

    def get_side_center(self, side: str) -> Tuple[float, float]:
        left, top, right, bottom = self.get_side_bounds(side)
        return ((left + right) / 2, (top + bottom) / 2)

    def get_random_position_in_side(self, side: str, margin: float = 0.0) -> Tuple[float, float]:
        left, top, right, bottom = self.get_side_bounds(side, margin=margin)
        if right <= left or bottom <= top:
            return self.get_center()
        return (
            random.uniform(left, right),
            random.uniform(top, bottom),
        )
