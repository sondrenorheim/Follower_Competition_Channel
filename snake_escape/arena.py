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

    # Arena dimensions - square arena
    WIDTH = 500
    HEIGHT = 500

    # Rectangular arena, no shrinking
    SHAPE = ArenaShape.RECTANGLE
    SHRINKS = False

    def __init__(self):
        """Initialize the arena with centered positioning."""
        # Override positioning to center vertically on screen
        self.left = (config.SCREEN_WIDTH - self.WIDTH) // 2
        self.top = (config.SCREEN_HEIGHT - self.HEIGHT) // 2  # Center vertically
        self.right = self.left + self.WIDTH
        self.bottom = self.top + self.HEIGHT

        # Center point
        self.center_x = self.left + self.WIDTH // 2
        self.center_y = self.top + self.HEIGHT // 2

        # Current dimensions (for shrinking arenas)
        self.current_width = self.WIDTH
        self.current_height = self.HEIGHT

        # For circular arenas
        self.initial_radius = self.WIDTH // 2
        self.current_radius = self.initial_radius

        # Game-specific initialization
        self._init_arena()

    def _init_arena(self):
        """Initialize any arena-specific features."""
        pass
