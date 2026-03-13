import config


class SuperFollowerBrosArena:
    def __init__(self):
        rect = getattr(config, "SUPER_FOLLOWER_BROS_ARENA_RECT", config.FIGHTER_ARENA_RECT)
        self.left, self.top, self.width, self.height = rect
        self.right = self.left + self.width
        self.bottom = self.top + self.height

    def get_rect(self):
        return (self.left, self.top, self.width, self.height)
