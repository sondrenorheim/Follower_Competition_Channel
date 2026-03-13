"""Club Duel arena layout."""

import math
from typing import List, Tuple

import config
from shared import ArenaTemplate, ArenaShape


class ClubDuelArena(ArenaTemplate):
    """Rectangular arena with duel ring positions."""

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

        self.ring_radius = float(getattr(config, "CLUB_DUEL_RING_RADIUS", min(arena_w, arena_h) * 0.32))

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return (self.left, self.top, self.right, self.bottom)

    def duel_positions(self, pair_count: int) -> List[Tuple[float, float]]:
        if pair_count <= 0:
            return []
        positions = []
        angle_step = (2 * math.pi) / pair_count
        for i in range(pair_count):
            angle = angle_step * i
            x = self.center_x + math.cos(angle) * self.ring_radius
            y = self.center_y + math.sin(angle) * self.ring_radius
            positions.append((x, y))
        return positions
