import config


class TinyFollowersArena:
    def __init__(self):
        arena_rect = getattr(config, "TINY_ARENA_RECT", config.FIGHTER_ARENA_RECT)
        arena_top = arena_rect[1]
        arena_height = arena_rect[3]

        # Keep the same full-width arena profile as Flappy Followers.
        self.left = 0
        self.top = arena_top
        self.width = config.SCREEN_WIDTH
        self.height = arena_height
        self.right = self.left + self.width
        self.bottom = self.top + self.height
        self.center_x = self.left + self.width / 2
        self.center_y = self.top + self.height / 2

    def get_rect(self):
        return (self.left, self.top, self.width, self.height)

    def get_bounds(self):
        return (self.left, self.top, self.right, self.bottom)

    def clamp_y(self, y, radius):
        min_y = self.top + radius
        max_y = self.bottom - radius
        return max(min_y, min(max_y, y))
