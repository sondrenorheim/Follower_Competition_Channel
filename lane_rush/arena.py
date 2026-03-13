"""Lane Rush arena layout."""

import random
from typing import List, Tuple

import config
from shared import ArenaTemplate, ArenaShape


class LaneRushArena(ArenaTemplate):
    """Rectangular arena with vertical lanes."""

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

        self.lane_count = int(getattr(config, "LANE_RUSH_LANES", 6))
        if self.lane_count < 2:
            self.lane_count = 2
        self._update_lanes()

    def _update_lanes(self):
        width = self.right - self.left
        lane_width = width / self.lane_count if self.lane_count else width
        self.lanes: List[Tuple[float, float]] = []
        for i in range(self.lane_count):
            lane_left = self.left + i * lane_width
            lane_right = lane_left + lane_width
            self.lanes.append((lane_left, lane_right))

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return (self.left, self.top, self.right, self.bottom)

    def get_lane_bounds(self, lane_index: int, margin: float = 0.0) -> Tuple[float, float]:
        lane_index = max(0, min(self.lane_count - 1, lane_index))
        left, right = self.lanes[lane_index]
        left += margin
        right -= margin
        if right < left:
            mid = (left + right) / 2
            left = right = mid
        return (left, right)

    def get_lane_center(self, lane_index: int) -> float:
        left, right = self.get_lane_bounds(lane_index)
        return (left + right) / 2

    def get_random_position(self, margin: float = 0.0) -> Tuple[float, float]:
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
