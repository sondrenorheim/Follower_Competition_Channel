import config


class MiniGolfArena:
    def __init__(self):
        self.x, self.y, self.width, self.height = getattr(
            config,
            "MAZE_RUSH_ARENA_RECT",
            config.FIGHTER_ARENA_RECT,
        )

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def get_bounds(self):
        return (self.x, self.y, self.x + self.width, self.y + self.height)
