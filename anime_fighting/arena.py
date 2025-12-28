"""
Arena System for Anime Fighting

Defines battle arena boundaries and fighter spawn positions for 1v1 matches.
Adapted for 540x960 vertical screen layout.
"""

from typing import Tuple
import pygame


class AnimeFightingArena:
    """
    Battle arena for 1v1 combat

    Defines rectangular boundaries and spawn positions for fighters.
    """

    def __init__(self, screen_width: int, screen_height: int, margin: int = 20, y_offset: int = 120):
        """
        Initialize arena

        Args:
            screen_width: Screen width (540 for vertical layout)
            screen_height: Screen height (960 for vertical layout)
            margin: Margin from screen edges
            y_offset: Vertical offset from top (below title/timer)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin = margin
        self.y_offset = y_offset

        # Calculate arena dimensions
        # Target: Large arena (500 width x 700 height) for better camera view
        arena_width = min(screen_width - margin * 2, 500)
        arena_x = (screen_width - arena_width) // 2
        arena_y = y_offset

        # Expand vertical space - use more of the 960px height
        # Reserve ~200px for bottom UI, leaving ~640px for arena
        available_height = screen_height - y_offset - 200
        arena_height = min(available_height, 700)

        self.bounds = pygame.Rect(arena_x, arena_y, arena_width, arena_height)

    def get_bounds(self) -> pygame.Rect:
        """
        Get arena boundaries

        Returns:
            pygame.Rect defining arena area
        """
        return self.bounds

    def get_spawn_positions(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Get spawn positions for two fighters

        Returns:
            ((left_x, left_y), (right_x, right_y)) spawn positions
        """
        center_y = self.bounds.centery
        left_x = self.bounds.left + 100
        right_x = self.bounds.right - 100

        return ((left_x, center_y), (right_x, center_y))

    def get_center(self) -> Tuple[float, float]:
        """
        Get arena center position

        Returns:
            (x, y) center coordinates
        """
        return (self.bounds.centerx, self.bounds.centery)

    def contains(self, pos: Tuple[float, float], radius: float = 0) -> bool:
        """
        Check if position is inside arena (with optional radius check)

        Args:
            pos: (x, y) position
            radius: Entity radius for collision

        Returns:
            True if position is inside arena
        """
        x, y = pos
        return (self.bounds.left + radius <= x <= self.bounds.right - radius and
                self.bounds.top + radius <= y <= self.bounds.bottom - radius)

    def __repr__(self):
        """String representation"""
        return f"AnimeFightingArena(bounds={self.bounds}, size={self.bounds.width}x{self.bounds.height})"
