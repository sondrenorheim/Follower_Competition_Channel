import config


class SubwayArena:
    def __init__(self):
        arena_top = config.FIGHTER_ARENA_RECT[1]
        arena_height = config.FIGHTER_ARENA_RECT[3]
        self.left = 0
        self.top = arena_top
        self.width = config.SCREEN_WIDTH
        self.height = arena_height
        self.right = self.left + self.width
        self.bottom = self.top + self.height
        self.center_x = self.left + self.width / 2
        self.center_y = self.top + self.height / 2

        self.lane_count = int(getattr(config, "SUBWAY_LANE_COUNT", 3))
        self.lane_padding = float(getattr(config, "SUBWAY_LANE_PADDING", 24))
        usable_width = max(1.0, self.width - self.lane_padding * 2)
        self.lane_width = usable_width / max(1, self.lane_count)
        self.lane_centers = [
            self.left + self.lane_padding + self.lane_width * (i + 0.5)
            for i in range(self.lane_count)
        ]

    def get_rect(self):
        return (self.left, self.top, self.width, self.height)

    def get_bounds(self):
        return (self.left, self.top, self.right, self.bottom)

    def lane_left(self, lane_index: int) -> float:
        return self.left + self.lane_padding + self.lane_width * lane_index

    def lane_center(self, lane_index: int) -> float:
        lane_index = max(0, min(self.lane_count - 1, lane_index))
        return self.lane_centers[lane_index]

    def clamp_position(self, x, y, radius):
        min_x = self.left + radius
        max_x = self.right - radius
        min_y = self.top + radius
        max_y = self.bottom - radius
        return (max(min_x, min(max_x, x)), max(min_y, min(max_y, y)))

    def get_lane_for_x(self, x: float) -> int:
        relative = x - (self.left + self.lane_padding)
        if self.lane_width <= 0:
            return 0
        lane = int(relative // self.lane_width)
        return max(0, min(self.lane_count - 1, lane))
