"""Discord Signal player behavior."""

import math
import random
from typing import Tuple

import config


class DiscordSignalPlayer:
    """Player moving toward assigned signal zones."""

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
        self.falling = False
        self.alpha = 255
        self.placement = None
        self.elimination_time = None
        self.survival_time = 0.0

        self.selected_zone = None
        self.target_x = self.x
        self.target_y = self.y
        self.target_timer = 0.0
        self.target_refresh_range = getattr(config, "DISCORD_SIGNAL_TARGET_REFRESH", (0.5, 1.2))
        self.target_refresh = random.uniform(*self.target_refresh_range)
        self.move_speed = float(getattr(config, "DISCORD_SIGNAL_MOVE_SPEED", 90.0))
        self.turn_rate = float(getattr(config, "DISCORD_SIGNAL_TURN_RATE", 0.2))
        self.jitter = float(getattr(config, "DISCORD_SIGNAL_JITTER", 0.2))
        self.fall_speed = float(getattr(config, "DISCORD_SIGNAL_FALL_SPEED", 280.0))

    def assign_zone(self, zone_id: int, arena):
        self.selected_zone = zone_id
        self._pick_new_target(arena)
        self.target_timer = 0.0
        self.target_refresh = random.uniform(*self.target_refresh_range)

    def assign_target(self, target: Tuple[float, float]):
        self.target_x, self.target_y = target

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
            self._update_selection_target(dt, arena)
            self._move_toward_target()
        elif phase in {"spin", "result"}:
            self.vx = 0.0
            self.vy = 0.0

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

    def _update_selection_target(self, dt: float, arena):
        if self.selected_zone is None:
            return

        self.target_timer += dt
        dist = math.hypot(self.target_x - self.x, self.target_y - self.y)
        if dist <= self.radius * 1.5 or self.target_timer >= self.target_refresh:
            self._pick_new_target(arena)
            self.target_timer = 0.0
            self.target_refresh = random.uniform(*self.target_refresh_range)

    def _pick_new_target(self, arena):
        if self.selected_zone is None:
            self.target_x, self.target_y = arena.center_x, arena.center_y
            return
        self.target_x, self.target_y = arena.get_random_position_in_zone(
            self.selected_zone,
            margin=self.radius + 2,
        )

    def _move_toward_target(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist <= 1e-3:
            return

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

    def eliminate(self, placement: int, current_time: float):
        self.start_fall(placement, current_time)

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
