"""
Math Drop arena.
Upper half shows answer squares, lower half holds players.
"""

import random
from typing import List, Tuple

import config
from shared import ArenaTemplate, ArenaShape


class MathDropArena(ArenaTemplate):
    WIDTH = int(getattr(config, "MATH_DROP_ARENA_RECT", config.FIGHTER_ARENA_RECT)[2])
    HEIGHT = int(getattr(config, "MATH_DROP_ARENA_RECT", config.FIGHTER_ARENA_RECT)[3])
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False

    def __init__(self):
        super().__init__()
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "MATH_DROP_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )

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

        self.choice_ids = (0, 1, 2)
        self.choice_rects: List[Tuple[float, float, float, float]] = []
        self._update_layout()

    def _update_layout(self):
        self.mid_y = self.top + (self.current_height / 2)
        self.upper_top = self.top
        self.upper_bottom = self.mid_y
        self.lower_top = self.mid_y
        self.lower_bottom = self.bottom

        total_width = self.right - self.left
        third_width = total_width / 3.0 if total_width > 0 else 0.0

        self.choice_rects = []
        for i in range(3):
            left = self.left + i * third_width
            right = self.left + (i + 1) * third_width
            rect = (left, self.upper_top, right, self.upper_bottom)
            self.choice_rects.append(rect)

    def get_choices(self) -> Tuple[int, int, int]:
        return self.choice_ids

    def get_choice_rect(self, choice: int) -> Tuple[float, float, float, float]:
        return self.choice_rects[int(choice)]

    def get_choice_rects(self) -> List[Tuple[float, float, float, float]]:
        return list(self.choice_rects)

    def get_choice_bounds(self, choice: int, margin: float = 0.0) -> Tuple[float, float, float, float]:
        left, top, right, bottom = self.get_choice_rect(choice)

        left += margin
        right -= margin
        top += margin
        bottom -= margin

        if right < left:
            mid = (left + right) / 2
            left = right = mid
        if bottom < top:
            mid = (top + bottom) / 2
            top = bottom = mid

        return (left, top, right, bottom)

    def get_random_position_in_choice(self, choice: int, margin: float = 0.0) -> Tuple[float, float]:
        left, top, right, bottom = self.get_choice_bounds(choice, margin=margin)
        if right <= left or bottom <= top:
            return self.get_center()
        return (
            random.uniform(left, right),
            random.uniform(top, bottom),
        )

    def get_lower_bounds(self, margin: float = 0.0) -> Tuple[float, float, float, float]:
        left = self.left + margin
        right = self.right - margin
        top = self.lower_top + margin
        bottom = self.lower_bottom - margin
        return (left, top, right, bottom)

    def get_random_position_in_lower_half(self, margin: float = 0.0) -> Tuple[float, float]:
        left, top, right, bottom = self.get_lower_bounds(margin=margin)
        if right <= left or bottom <= top:
            return self.get_center()
        return (
            random.uniform(left, right),
            random.uniform(top, bottom),
        )

    def clamp_to_lower_half(self, x: float, y: float, radius: float = 0.0) -> Tuple[float, float]:
        left, top, right, bottom = self.get_lower_bounds(margin=radius)
        return (
            max(left, min(right, x)),
            max(top, min(bottom, y)),
        )

    def clamp_to_choice(self, choice: int, x: float, y: float, radius: float = 0.0) -> Tuple[float, float]:
        left, top, right, bottom = self.get_choice_bounds(choice, margin=radius)
        return (
            max(left, min(right, x)),
            max(top, min(bottom, y)),
        )
