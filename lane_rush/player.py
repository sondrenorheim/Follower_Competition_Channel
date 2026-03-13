"""Lane Rush player behavior."""

import random
from typing import Tuple

import config


class LaneRushPlayer:
    """Player racing upward within a lane."""

    def __init__(self, follower_data: dict, position: Tuple[float, float], lane_index: int):
        self.id = follower_data.get("id", random.randint(1, 999999))
        self.username = follower_data.get("username", f"player_{self.id}")
        self.display_name = follower_data.get("display_name", self.username)

        avatar = follower_data.get("avatar_image")
        if avatar is None:
            avatar = follower_data.get("avatar")
        self.avatar_image = avatar
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        self.x, self.y = position
        self.radius = float(getattr(config, "FOLLOWER_RADIUS", 12))

        self.lane_index = lane_index
        self.progress = 0.0
        self.base_speed = float(getattr(config, "LANE_RUSH_BASE_SPEED", 0.12))
        self.boost_speed = float(getattr(config, "LANE_RUSH_BOOST_SPEED", 0.06))
        self.speed_variance = float(getattr(config, "LANE_RUSH_SPEED_VARIANCE", 0.015))
        self.speed_bias = random.uniform(-self.speed_variance, self.speed_variance)
        self.lane_offset = random.uniform(-0.35, 0.35)

        self.alive = True
        self.alpha = 255
        self.placement = None
        self.elimination_time = None
        self.survival_time = 0.0

    def update(self, dt: float, arena, boost_active: bool):
        if not self.alive:
            return

        speed = self.base_speed + self.speed_bias
        if boost_active:
            speed += self.boost_speed
        self.progress = min(1.25, self.progress + speed * dt)

        lane_left, lane_right = arena.get_lane_bounds(self.lane_index, margin=self.radius)
        lane_center = (lane_left + lane_right) / 2
        lane_width = max(1.0, lane_right - lane_left)
        offset = self.lane_offset * lane_width * 0.4
        self.x = lane_center + offset

        track_height = arena.bottom - arena.top - self.radius * 2
        self.y = arena.bottom - self.radius - (self.progress * track_height)

    def eliminate(self, placement: int, current_time: float):
        if not self.alive:
            return
        self.alive = False
        self.placement = placement
        self.elimination_time = current_time
        self.survival_time = current_time

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
