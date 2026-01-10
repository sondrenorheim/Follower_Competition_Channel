"""
Mingle Arena - circular arena with a central platform and ring of rooms.
"""

import math
from typing import List, Tuple

import config
from shared.arena_template import ArenaTemplate, ArenaShape


class MingleRoom:
    """Represents a single room on the outer ring."""

    def __init__(
        self,
        index: int,
        center: Tuple[float, float],
        angle: float,
        color: Tuple[int, int, int],
        width: int,
        height: int,
    ):
        self.index = index
        self.center = center
        self.angle = angle
        self.color = color
        self.width = width
        self.height = height
        self.capacity = 0
        self.assigned_players = []
        self.occupancy = 0
        self.locked = False
        self.sealed_players = set()

    def reset(self):
        self.capacity = 0
        self.assigned_players = []
        self.occupancy = 0
        self.locked = False
        self.sealed_players = set()


class MingleArena(ArenaTemplate):
    """Circular arena with a smaller central platform."""

    WIDTH = 500
    HEIGHT = 700
    SHAPE = ArenaShape.CIRCLE

    def _init_arena(self):
        self.platform_radius = getattr(config, "MINGLE_PLATFORM_RADIUS", 140)
        self.room_width = getattr(config, "MINGLE_ROOM_WIDTH", getattr(config, "MINGLE_ROOM_SIZE", 26))
        self.room_height = getattr(config, "MINGLE_ROOM_HEIGHT", getattr(config, "MINGLE_ROOM_SIZE", 26))
        self.room_ring_padding = getattr(config, "MINGLE_ROOM_RING_PADDING", 36)
        self.rooms = self._build_rooms()

    def _build_rooms(self) -> List[MingleRoom]:
        room_count = getattr(config, "MINGLE_ROOM_COUNT", 50)
        colors = getattr(config, "MINGLE_ROOM_COLORS", [(200, 80, 80)])
        radial_half = self.room_height * 0.5
        ring_radius = max(0.0, self.current_radius - self.room_ring_padding - radial_half)
        rooms = []

        for i in range(room_count):
            angle = (2 * math.pi * i / room_count) - (math.pi / 2)
            x = self.center_x + ring_radius * math.cos(angle)
            y = self.center_y + ring_radius * math.sin(angle)
            color = colors[i % len(colors)]
            rooms.append(MingleRoom(i, (x, y), angle, color, self.room_width, self.room_height))

        return rooms

    def clamp_to_platform(self, x: float, y: float, entity_radius: float = 0) -> Tuple[float, float]:
        dx = x - self.center_x
        dy = y - self.center_y
        distance = math.hypot(dx, dy)
        max_distance = max(0.0, self.platform_radius - entity_radius)

        if distance <= max_distance:
            return (x, y)

        if distance > 0:
            scale = max_distance / distance
            return (self.center_x + dx * scale, self.center_y + dy * scale)

        return (self.center_x, self.center_y)

    def get_room_ring_radius(self) -> float:
        return max(0.0, self.current_radius - self.room_ring_padding)
