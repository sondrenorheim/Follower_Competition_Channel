"""
Side Choice player behavior.
"""

import math
import random
from typing import Tuple

import config


class SideChoicePlayer:
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
        self.radius = float(getattr(config, "SIDE_CHOICE_PLAYER_RADIUS", 15))

        self.alive = True
        self.falling = False
        self.alpha = 255
        self.placement = None
        self.elimination_time = None
        self.survival_time = 0.0

        self.target_side = None
        self.target_x = self.x
        self.target_y = self.y
        self.target_timer = 0.0
        self.target_refresh_range = getattr(config, "SIDE_CHOICE_TARGET_REFRESH", (0.6, 1.4))
        self.target_refresh = random.uniform(*self.target_refresh_range)

        self.move_speed = float(getattr(config, "SIDE_CHOICE_MOVE_SPEED", 80.0))
        self.turn_rate = float(getattr(config, "SIDE_CHOICE_TURN_RATE", 0.18))
        self.direction_jitter = float(getattr(config, "SIDE_CHOICE_DIRECTION_JITTER", 0.2))

        self.wander_speed = float(getattr(config, "SIDE_CHOICE_WANDER_SPEED", 35.0))
        self.wander_interval_range = getattr(config, "SIDE_CHOICE_WANDER_INTERVAL", (0.8, 1.6))
        self.wander_interval = random.uniform(*self.wander_interval_range)
        self.wander_timer = 0.0
        self.wander_angle = random.uniform(0.0, 2 * math.pi)

        self.fall_speed = float(getattr(config, "SIDE_CHOICE_FALL_SPEED", 260.0))

    def assign_side(self, side: str, arena):
        self.target_side = side
        self._pick_new_target(arena)
        self.target_timer = 0.0
        self.target_refresh = random.uniform(*self.target_refresh_range)

    def start_fall(self, placement: int, current_time: float):
        if not self.alive or self.falling:
            return
        self.alive = False
        self.falling = True
        self.placement = placement
        self.elimination_time = current_time
        self.survival_time = current_time
        self.vx = 0.0
        self.vy = 0.0

    def update(self, dt: float, arena, phase: str):
        if self.falling:
            self.y += self.fall_speed * dt
            if self.y - self.radius > arena.bottom + (self.radius * 2):
                self.falling = False
            return

        if not self.alive:
            return

        if phase == "selection":
            self._update_target(dt, arena)
            self._move_toward_target()
        elif phase == "result":
            self.vx = 0.0
            self.vy = 0.0
        else:
            self._wander(dt)

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

    def _update_target(self, dt: float, arena):
        if not self.target_side:
            return

        self.target_timer += dt
        dist = math.hypot(self.target_x - self.x, self.target_y - self.y)
        if dist <= self.radius * 1.5 or self.target_timer >= self.target_refresh:
            self._pick_new_target(arena)
            self.target_timer = 0.0
            self.target_refresh = random.uniform(*self.target_refresh_range)

    def _pick_new_target(self, arena):
        if self.target_side and hasattr(arena, "get_random_position_in_side"):
            self.target_x, self.target_y = arena.get_random_position_in_side(
                self.target_side,
                margin=self.radius + 4,
            )
        else:
            self.target_x, self.target_y = arena.get_random_position(margin=self.radius + 4)

    def _move_toward_target(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-3:
            return

        dir_x = dx / dist
        dir_y = dy / dist

        if self.direction_jitter > 0:
            dir_x += random.uniform(-self.direction_jitter, self.direction_jitter)
            dir_y += random.uniform(-self.direction_jitter, self.direction_jitter)
            norm = math.hypot(dir_x, dir_y) or 1.0
            dir_x /= norm
            dir_y /= norm

        desired_vx = dir_x * self.move_speed
        desired_vy = dir_y * self.move_speed

        self.vx += (desired_vx - self.vx) * self.turn_rate
        self.vy += (desired_vy - self.vy) * self.turn_rate

    def _wander(self, dt: float):
        self.wander_timer += dt
        if self.wander_timer >= self.wander_interval:
            self.wander_angle = random.uniform(0.0, 2 * math.pi)
            self.wander_interval = random.uniform(*self.wander_interval_range)
            self.wander_timer = 0.0

        desired_vx = math.cos(self.wander_angle) * self.wander_speed
        desired_vy = math.sin(self.wander_angle) * self.wander_speed

        self.vx += (desired_vx - self.vx) * self.turn_rate
        self.vy += (desired_vy - self.vy) * self.turn_rate
