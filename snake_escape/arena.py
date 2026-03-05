"""
Snake Escape Arena - Rectangular play area for the snake escape game.
"""

import config
from shared.arena_template import ArenaTemplate, ArenaShape


class SnakeEscapeArena(ArenaTemplate):
    """
    Rectangular arena for the Snake Escape game.
    Players must stay inside the arena to avoid being eliminated.
    The snake hunts players within this confined space.

    Uses a 500x500 square arena centered on screen.
    """

    # Arena dimensions default to square; final rect can be overridden from config.
    WIDTH = 500
    HEIGHT = 500

    # Rectangular arena, no shrinking
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False

    def __init__(self):
        """Initialize the arena with centered positioning."""
        arena_rect = getattr(config, "SNAKE_ESCAPE_ARENA_RECT", None)
        if arena_rect is None:
            arena_rect = getattr(
                config,
                "MAZE_RUSH_ARENA_RECT",
                (
                    (config.SCREEN_WIDTH - self.WIDTH) // 2,
                    (config.SCREEN_HEIGHT - self.HEIGHT) // 2,
                    self.WIDTH,
                    self.HEIGHT,
                ),
            )

        x, y, w, h = arena_rect

        self.left = float(x)
        self.top = float(y)
        self.right = self.left + float(w)
        self.bottom = self.top + float(h)

        # Center point
        self.center_x = self.left + (float(w) / 2.0)
        self.center_y = self.top + (float(h) / 2.0)

        # Current dimensions (for shrinking arenas)
        self.current_width = float(w)
        self.current_height = float(h)

        # For circular arenas
        self.initial_radius = min(self.current_width, self.current_height) / 2.0
        self.current_radius = self.initial_radius

        # Game-specific initialization
        self._init_arena()

    def _init_arena(self):
        """Initialize any arena-specific features."""
        pass
