"""
Gorillas vs Followers Arena Module
Handles the rectangular arena for Gorillas vs Followers game mode
Extended height arena compared to fighter arena
"""

import pygame
from typing import Tuple
import config


class GorillasArena:
    """
    Rectangular arena for the Gorillas vs Followers game mode
    Extended height to accommodate more chaos
    Static arena that doesn't shrink
    """

    def __init__(self):
        """
        Initialize the gorillas arena
        """
        # Get arena bounds from config (extended height)
        self.x, self.y, self.width, self.height = config.GORILLAS_ARENA_RECT

        # Calculate center
        self.center = (self.x + self.width // 2, self.y + self.height // 2)

        # Arena state
        self.is_active = True

        print(f"Gorillas Arena initialized: ({self.x}, {self.y}) - {self.width}x{self.height}")

    def get_rect(self) -> Tuple[int, int, int, int]:
        """
        Get arena rectangle bounds

        Returns:
            (x, y, width, height) tuple
        """
        return (self.x, self.y, self.width, self.height)

    def get_bounds(self) -> Tuple[int, int, int, int]:
        """
        Get arena bounds as (left, top, right, bottom)

        Returns:
            (left, top, right, bottom) tuple
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def is_inside(self, x: float, y: float, radius: float = 0) -> bool:
        """
        Check if a point (with optional radius) is inside the arena

        Args:
            x: X position
            y: Y position
            radius: Optional radius to account for object size

        Returns:
            True if inside arena bounds
        """
        left, top, right, bottom = self.get_bounds()
        return (x - radius >= left and
                x + radius <= right and
                y - radius >= top and
                y + radius <= bottom)

    def clamp_position(self, x: float, y: float, radius: float = 0) -> Tuple[float, float]:
        """
        Clamp a position to be inside the arena

        Args:
            x: X position
            y: Y position
            radius: Object radius to account for

        Returns:
            (clamped_x, clamped_y) tuple
        """
        left, top, right, bottom = self.get_bounds()
        clamped_x = max(left + radius, min(right - radius, x))
        clamped_y = max(top + radius, min(bottom - radius, y))
        return (clamped_x, clamped_y)

    def get_random_position(self, radius: float = 0) -> Tuple[float, float]:
        """
        Get a random position inside the arena

        Args:
            radius: Object radius to account for

        Returns:
            (x, y) random position
        """
        import random
        left, top, right, bottom = self.get_bounds()
        x = random.uniform(left + radius, right - radius)
        y = random.uniform(top + radius, bottom - radius)
        return (x, y)

    def get_area(self) -> float:
        """
        Get arena area in square pixels

        Returns:
            Area in square pixels
        """
        return self.width * self.height

    def update(self, dt: float) -> bool:
        """
        Update arena state (placeholder for future features)

        Args:
            dt: Delta time in seconds

        Returns:
            False (no shrinking in Gorillas Arena)
        """
        # Gorillas Arena doesn't shrink
        return False

    def __repr__(self):
        return f"GorillasArena({self.x}, {self.y}, {self.width}x{self.height})"
