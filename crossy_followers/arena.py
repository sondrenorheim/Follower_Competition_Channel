import config


class CrossyFollowersArena:
    def __init__(self):
        rect = getattr(
            config,
            "CROSSY_ARENA_RECT",
            getattr(config, "DOODLE_ARENA_RECT", (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)),
        )
        self.screen_left, self.screen_top, self.width, self.height = rect
        self.screen_right = self.screen_left + self.width
        self.screen_bottom = self.screen_top + self.height

        lane_count = int(getattr(config, "CROSSY_LANE_COUNT", 9))
        self.lane_count = max(5, lane_count)
        self.lane_width = self.width / float(self.lane_count)
        self.row_height = float(getattr(config, "CROSSY_ROW_HEIGHT", 56.0))

    def lane_to_x(self, lane_index: int) -> float:
        lane = max(0, min(self.lane_count - 1, int(lane_index)))
        return self.screen_left + (lane + 0.5) * self.lane_width

    def x_to_lane(self, x: float) -> int:
        lane = int(round((x - self.screen_left) / max(1e-6, self.lane_width) - 0.5))
        return max(0, min(self.lane_count - 1, lane))

    def clamp_x(self, x: float) -> float:
        min_x = self.screen_left + self.lane_width * 0.5
        max_x = self.screen_right - self.lane_width * 0.5
        return max(min_x, min(max_x, x))

    def get_rect(self):
        return (self.screen_left, self.screen_top, self.width, self.height)
