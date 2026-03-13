"""Beacon Blitz player behavior."""

import math
import random
from typing import Tuple

import config


class BeaconBlitzPlayer:
    """Player agent that rushes toward the beacon."""

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        self.id = follower_data.get("id", random.randint(1, 999999))
        self.username = follower_data.get("username", f"player_{self.id}")
        self.display_name = follower_data.get("display_name", self.username)

        avatar = follower_data.get("avatar_image")
        if avatar is None:
            avatar = follower_data.get("avatar")
        self.avatar_image = avatar
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        self.x, self.y = position
        self.vx = 0.0
        self.vy = 0.0
        self.radius = float(getattr(config, "FOLLOWER_RADIUS", 12))

        self.alive = True
        self.alpha = 255
        self.placement = None
        self.elimination_time = None
        self.survival_time = 0.0

        self.target_x = self.x
        self.target_y = self.y
        self.target_radius = 0.0
        self.move_speed = float(getattr(config, "BEACON_BLITZ_MOVE_SPEED", 80.0))
        self.turn_rate = float(getattr(config, "BEACON_BLITZ_TURN_RATE", 0.2))
        self.jitter = float(getattr(config, "BEACON_BLITZ_JITTER", 0.2))

    def set_target(self, center: Tuple[float, float], radius: float):
        angle = random.uniform(0.0, 2 * math.pi)
        distance = random.uniform(0.0, radius)
        self.target_x = center[0] + math.cos(angle) * distance
        self.target_y = center[1] + math.sin(angle) * distance
        self.target_radius = radius

    def update(self, dt: float, arena):
        if not self.alive:
            return

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1e-3:
            dir_x = dx / dist
            dir_y = dy / dist
            if self.jitter:
                dir_x += random.uniform(-self.jitter, self.jitter)
                dir_y += random.uniform(-self.jitter, self.jitter)
                norm = math.hypot(dir_x, dir_y) or 1.0
                dir_x /= norm
                dir_y /= norm
            desired_vx = dir_x * self.move_speed
            desired_vy = dir_y * self.move_speed
            self.vx += (desired_vx - self.vx) * self.turn_rate
            self.vy += (desired_vy - self.vy) * self.turn_rate

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

    def eliminate(self, placement: int, current_time: float):
        if not self.alive:
            return
        self.alive = False
        self.placement = placement
        self.elimination_time = current_time
        self.survival_time = current_time
        self.vx = 0.0
        self.vy = 0.0

    def update_alpha(self, current_time: float, fade_duration: float):
        if self.alive:
            self.alpha = 255
            return
        if self.elimination_time is None:
            self.alpha = 0
            return
        elapsed = max(0.0, current_time - self.elimination_time)
        if fade_duration <= 0:
            self.alpha = 0
        elif elapsed >= fade_duration:
            self.alpha = 0
        else:
            self.alpha = int(255 * (1.0 - (elapsed / fade_duration)))

    def is_fading(self, current_time: float, fade_duration: float) -> bool:
        if self.alive or self.elimination_time is None:
            return False
        return (current_time - self.elimination_time) < fade_duration
