"""
Wheel Spinner player model.
"""

import random
from typing import Tuple

import config


class WheelSpinnerPlayer:
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
        self.alive = True
        self.placement = None
        self.elimination_time = None
        self.survival_time = 0.0

    def get_char_at(self, index: int) -> str:
        if index < 0:
            return ""
        if index < len(self.username):
            return self.username[index]
        return ""

    def eliminate(self, placement: int, current_time: float):
        if not self.alive:
            return
        self.alive = False
        self.placement = placement
        self.elimination_time = current_time
        self.survival_time = current_time

    def get_survival_time(self) -> float:
        if self.survival_time:
            return self.survival_time
        return self.elimination_time or 0.0
