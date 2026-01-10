"""
Mingle Player - follower behavior for Mingle rounds.
"""

import math
import random
from typing import Tuple

import config
from shared.entity_template import EntityTemplate


class MinglePlayer(EntityTemplate):
    """Follower that can orbit the platform and rush rooms."""

    def _init_entity(self, follower_data: dict):
        avatar = follower_data.get("avatar")
        if avatar and self.avatar_image is None:
            self.avatar_image = avatar

        self.target_room = None
        self.fallback_target = None
        self.in_room = False

        self.orbit_angle = random.uniform(0.0, 2 * math.pi)
        min_radius = max(10.0, config.MINGLE_PLATFORM_RADIUS * 0.35)
        max_radius = max(min_radius + 5.0, config.MINGLE_PLATFORM_RADIUS * 0.9)
        self.orbit_radius = random.uniform(min_radius, max_radius)
        self.orbit_speed = random.uniform(-1.0, 1.0) * config.MINGLE_PLATFORM_SPIN_SPEED

    def assign_room(self, room):
        self.target_room = room
        self.in_room = False

    def clear_room(self):
        self.target_room = None
        self.in_room = False
        self.fallback_target = None

    def set_fallback_target(self, target: Tuple[float, float]):
        self.fallback_target = target

    def update(self, dt: float, arena, phase: str):
        if not self.alive:
            self.update_fade()
            return

        if phase == "mixing":
            self._update_mixing(dt, arena)
        elif phase == "scramble":
            self._update_scramble(dt, arena)

    def _update_mixing(self, dt: float, arena):
        center_x, center_y = arena.get_center()
        self.orbit_angle += self.orbit_speed * dt

        target_x = center_x + math.cos(self.orbit_angle) * self.orbit_radius
        target_y = center_y + math.sin(self.orbit_angle) * self.orbit_radius

        speed = getattr(config, "MINGLE_MIX_SPEED", 80.0)
        self._move_toward((target_x, target_y), speed, dt)

        self.x, self.y = arena.clamp_to_platform(self.x, self.y, self.radius)

    def _update_scramble(self, dt: float, arena):
        speed = getattr(config, "MINGLE_SCRAMBLE_SPEED", 150.0)

        if self.target_room:
            target = self.target_room.center
        elif self.fallback_target:
            target = self.fallback_target
        else:
            target = arena.get_center()

        self._move_toward(target, speed, dt)
        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

        if self.target_room:
            self.in_room = self._is_inside_room(self.target_room)
        else:
            self.in_room = False

    def _move_toward(self, target: Tuple[float, float], speed: float, dt: float):
        dx = target[0] - self.x
        dy = target[1] - self.y
        dist = math.hypot(dx, dy)

        if dist < 1e-3:
            return

        nx = dx / dist
        ny = dy / dist

        jitter = getattr(config, "MINGLE_WANDER_JITTER", 0.0)
        if jitter:
            nx += random.uniform(-jitter, jitter)
            ny += random.uniform(-jitter, jitter)
            jitter_mag = math.hypot(nx, ny)
            if jitter_mag > 1e-3:
                nx /= jitter_mag
                ny /= jitter_mag

        self.x += nx * speed * dt
        self.y += ny * speed * dt

    def _is_inside_room(self, room) -> bool:
        dx = self.x - room.center[0]
        dy = self.y - room.center[1]

        radial_x = math.cos(room.angle)
        radial_y = math.sin(room.angle)
        tangent_x = -radial_y
        tangent_y = radial_x

        radial_dist = (dx * radial_x) + (dy * radial_y)
        tangent_dist = (dx * tangent_x) + (dy * tangent_y)

        half_width = room.width * 0.5
        half_height = room.height * 0.5

        return abs(tangent_dist) <= half_width and abs(radial_dist) <= half_height
