"""Discord Signal arena layout."""

import random
from typing import List, Tuple

import config
from shared import ArenaTemplate, ArenaShape


class DiscordSignalArena(ArenaTemplate):
    """Rectangular arena split into four signal zones."""

    WIDTH = int(
        getattr(
            config,
            "DISCORD_SIGNAL_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )[2]
    )
    HEIGHT = int(
        getattr(
            config,
            "DISCORD_SIGNAL_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )[3]
    )
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False

    def __init__(self):
        super().__init__()
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "DISCORD_SIGNAL_ARENA_RECT",
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

        self.zones = [0, 1, 2, 3]
        self._update_zones()

    def _update_zones(self):
        mid_x = (self.left + self.right) / 2
        mid_y = (self.top + self.bottom) / 2
        self.zone_rects = {
            0: (self.left, self.top, mid_x, mid_y),
            1: (mid_x, self.top, self.right, mid_y),
            2: (self.left, mid_y, mid_x, self.bottom),
            3: (mid_x, mid_y, self.right, self.bottom),
        }

    def get_zone_rect(self, zone_id: int) -> Tuple[float, float, float, float]:
        return self.zone_rects[int(zone_id)]

    def get_zone_center(self, zone_id: int) -> Tuple[float, float]:
        left, top, right, bottom = self.get_zone_rect(zone_id)
        return ((left + right) / 2, (top + bottom) / 2)

    def get_zone_bounds(self, zone_id: int, margin: float = 0.0) -> Tuple[float, float, float, float]:
        left, top, right, bottom = self.get_zone_rect(zone_id)
        left += margin
        top += margin
        right -= margin
        bottom -= margin
        if right < left:
            mid = (left + right) / 2
            left = right = mid
        if bottom < top:
            mid = (top + bottom) / 2
            top = bottom = mid
        return (left, top, right, bottom)

    def get_random_position_in_zone(self, zone_id: int, margin: float = 0.0) -> Tuple[float, float]:
        left, top, right, bottom = self.get_zone_bounds(zone_id, margin=margin)
        if right <= left or bottom <= top:
            return (self.center_x, self.center_y)
        return (
            random.uniform(left, right),
            random.uniform(top, bottom),
        )

    def get_zone_for_position(self, x: float, y: float) -> int:
        mid_x = (self.left + self.right) / 2
        mid_y = (self.top + self.bottom) / 2
        if x < mid_x and y < mid_y:
            return 0
        if x >= mid_x and y < mid_y:
            return 1
        if x < mid_x and y >= mid_y:
            return 2
        return 3
