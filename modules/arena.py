"""
Arena Module
Manages the battle arena and shrinking safe zone
"""

import time
import math
from typing import Tuple
import config


class Arena:
    """
    Manages the circular battle arena with shrinking safe zone
    The safe zone shrinks periodically, eliminating followers outside
    """

    def __init__(self):
        """
        Initialize the arena with full-size safe zone
        """
        self.center = config.ARENA_CENTER
        self.initial_radius = config.ARENA_INITIAL_RADIUS
        self.current_radius = config.ARENA_INITIAL_RADIUS
        self.min_radius = config.ARENA_MIN_RADIUS

        # Shrinking logic
        self.shrink_interval = config.SHRINK_INTERVAL  # Seconds between shrinks
        self.shrink_percentage = config.SHRINK_PERCENTAGE  # Percentage to shrink each time
        self.last_shrink_time = time.time()
        self.total_shrinks = 0

        # Game state
        self.game_over = False
        self.start_time = time.time()

    def update(self, dt: float) -> bool:
        """
        Update arena state (handle zone shrinking)

        Args:
            dt: Delta time in seconds

        Returns:
            True if zone shrunk this frame, False otherwise
        """
        current_time = time.time()

        # Check if it's time to shrink
        if current_time - self.last_shrink_time >= self.shrink_interval:
            if self.current_radius > self.min_radius:
                # Shrink by percentage
                shrink_amount = self.current_radius * self.shrink_percentage
                self.current_radius -= shrink_amount

                # Don't go below minimum
                if self.current_radius < self.min_radius:
                    self.current_radius = self.min_radius

                self.last_shrink_time = current_time
                self.total_shrinks += 1

                print(f"⚠️  ZONE SHRINK #{self.total_shrinks} - New radius: {self.current_radius:.1f}px")
                return True
            else:
                # Reached minimum size
                if not self.game_over:
                    print(f"🔴 Safe zone reached minimum size ({self.min_radius}px)")
                    self.game_over = True

        return False

    def is_point_in_safe_zone(self, x: float, y: float) -> bool:
        """
        Check if a point is inside the safe zone

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if point is in safe zone, False otherwise
        """
        dx = x - self.center[0]
        dy = y - self.center[1]
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.current_radius

    def get_distance_from_center(self, x: float, y: float) -> float:
        """
        Calculate distance from a point to arena center

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Distance in pixels
        """
        dx = x - self.center[0]
        dy = y - self.center[1]
        return math.sqrt(dx * dx + dy * dy)

    def get_safe_zone_percentage(self) -> float:
        """
        Get current safe zone size as percentage of initial size

        Returns:
            Percentage (0-100)
        """
        return (self.current_radius / self.initial_radius) * 100

    def get_time_until_next_shrink(self) -> float:
        """
        Get seconds until next zone shrink

        Returns:
            Time in seconds
        """
        elapsed = time.time() - self.last_shrink_time
        return max(0, self.shrink_interval - elapsed)

    def get_game_duration(self) -> float:
        """
        Get total game duration in seconds

        Returns:
            Duration in seconds
        """
        return time.time() - self.start_time

    def reset(self):
        """
        Reset arena to initial state
        """
        self.current_radius = self.initial_radius
        self.last_shrink_time = time.time()
        self.total_shrinks = 0
        self.game_over = False
        self.start_time = time.time()

    def __repr__(self):
        return (f"Arena(radius={self.current_radius:.1f}px, "
                f"shrinks={self.total_shrinks}, "
                f"zone={self.get_safe_zone_percentage():.1f}%)")
