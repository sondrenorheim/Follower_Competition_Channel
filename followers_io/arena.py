import random

import config


class FollowersIOArena:
    def __init__(self):
        self.x, self.y, self.width, self.height = config.FOLLOWERS_IO_ARENA_RECT
        self.left = self.x
        self.top = self.y
        self.right = self.x + self.width
        self.bottom = self.y + self.height
        self.center_x = self.x + self.width * 0.5
        self.center_y = self.y + self.height * 0.5

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def get_bounds(self):
        return (self.left, self.top, self.right, self.bottom)

    def get_random_position(self, margin: float = 0.0):
        x = random.uniform(self.left + margin, self.right - margin)
        y = random.uniform(self.top + margin, self.bottom - margin)
        return (x, y)

    def clamp_position(self, x: float, y: float, radius: float = 0.0):
        clamped_x = max(self.left + radius, min(self.right - radius, x))
        clamped_y = max(self.top + radius, min(self.bottom - radius, y))
        return (clamped_x, clamped_y)
