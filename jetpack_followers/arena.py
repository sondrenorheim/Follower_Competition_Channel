import config


class JetpackArena:
    def __init__(self):
        arena_top = config.FIGHTER_ARENA_RECT[1]
        arena_height = config.FIGHTER_ARENA_RECT[3]

        # Match Flappy Followers footprint: full width with the same vertical arena size.
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

    def get_center(self):
        return (self.center_x, self.center_y)

    def clamp_position(self, x: float, y: float, radius: float):
        min_x = self.left + radius
        max_x = self.right - radius
        min_y = self.top + radius
        max_y = self.bottom - radius
        return (
            max(min_x, min(max_x, x)),
            max(min_y, min(max_y, y)),
        )

    def clamp_y(self, y: float, radius: float):
        min_y = self.top + radius
        max_y = self.bottom - radius
        return max(min_y, min(max_y, y))

    def is_inside_vertical(self, y: float, radius: float):
        return self.top + radius <= y <= self.bottom - radius
