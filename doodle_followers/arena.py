import config


class DoodleFollowersArena:
    def __init__(self):
        rect = getattr(config, "DOODLE_ARENA_RECT", config.FIGHTER_ARENA_RECT)
        self.screen_left, self.screen_top, self.width, self.height = rect
        self.screen_right = self.screen_left + self.width
        self.screen_bottom = self.screen_top + self.height

    def get_rect(self):
        return (self.screen_left, self.screen_top, self.width, self.height)

    def get_bounds(self):
        return (self.screen_left, self.screen_top, self.screen_right, self.screen_bottom)
