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
        self.shape = getattr(config, 'ARENA_SHAPE', 'circle')

        # Continuous shrinking logic
        self.shrink_rate = getattr(config, 'SHRINK_RATE', 0.5)  # Pixels per second
        self.is_shrinking = False  # Will be enabled after countdown
        self.last_shrink_time = time.time()

        # Track shrink milestones for notifications
        self.last_notification_percentage = 100
        self.total_shrinks = 0  # Track major shrink milestones

        # Game state
        self.game_over = False
        self.start_time = time.time()

    def update(self, dt: float) -> bool:
        """
        Update arena state (handle continuous zone shrinking)

        Args:
            dt: Delta time in seconds

        Returns:
            True if significant shrink milestone reached, False otherwise
        """
        if not self.is_shrinking:
            return False

        # Continuous smooth shrinking
        if self.current_radius > self.min_radius:
            # Shrink by rate * delta time for smooth continuous shrinking
            shrink_amount = self.shrink_rate * dt * 60  # Scale by 60 for consistent feel
            self.current_radius -= shrink_amount

            # Don't go below minimum
            if self.current_radius < self.min_radius:
                self.current_radius = self.min_radius

            # Check for milestone notifications (every 10% shrink)
            current_percentage = (self.current_radius / self.initial_radius) * 100

            # Notify at major percentage milestones (90%, 80%, 70%, etc.)
            if current_percentage < self.last_notification_percentage - 10:
                self.last_notification_percentage = int(current_percentage / 10) * 10
                self.total_shrinks += 1
                print(f"⚠️  ZONE SHRINKING - Now at {current_percentage:.0f}% ({self.current_radius:.1f}px)")
                return True

        else:
            # Reached minimum size
            if not self.game_over:
                print(f"🔴 Safe zone reached minimum size ({self.min_radius}px)")
                self.game_over = True

        return False

    def start_shrinking(self):
        """
        Start the continuous zone shrinking (called after countdown)
        """
        self.is_shrinking = True
        self.last_shrink_time = time.time()
        print("🔴 Zone shrinking activated!")

    def is_point_in_safe_zone(self, x: float, y: float) -> bool:
        """
        Check if a point is inside the safe zone (supports different shapes)

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if point is in safe zone, False otherwise
        """
        dx = x - self.center[0]
        dy = y - self.center[1]

        if self.shape == "circle":
            distance = math.sqrt(dx * dx + dy * dy)
            return distance <= self.current_radius

        elif self.shape == "square":
            # Square arena - check if within bounds
            return abs(dx) <= self.current_radius and abs(dy) <= self.current_radius

        elif self.shape == "hexagon":
            # Regular hexagon - check using distance from edges
            # Hexagon inscribed in circle of radius current_radius
            abs_dx = abs(dx)
            abs_dy = abs(dy)

            # Hexagon has 6 sides, check distance to each edge
            # For regular hexagon: if y > sqrt(3) * (radius - abs(x)/2), outside
            if abs_dy > self.current_radius:
                return False
            if abs_dx > self.current_radius * 0.866:  # sqrt(3)/2
                return False
            if abs_dy > self.current_radius * 0.866 - abs_dx * 0.5:
                return False
            return True

        elif self.shape == "octagon":
            # Regular octagon
            abs_dx = abs(dx)
            abs_dy = abs(dy)

            # Octagon inscribed in circle
            threshold = self.current_radius * 0.7071  # 1/sqrt(2)

            if abs_dx <= threshold and abs_dy <= threshold:
                return True
            if abs_dx > self.current_radius or abs_dy > self.current_radius:
                return False

            # Check diagonal edges
            return abs_dx + abs_dy <= self.current_radius * 1.4142

        else:
            # Default to circle
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
        Get time-based indicator for zone warning
        For continuous shrinking, this returns a pulsing value

        Returns:
            Time-like value for warning effects
        """
        if not self.is_shrinking:
            return 10.0  # No warning before shrinking starts

        # Pulse based on zone size for urgency
        zone_percentage = self.get_safe_zone_percentage()
        if zone_percentage < 30:
            # Very urgent when small
            return 0.5
        elif zone_percentage < 50:
            # Moderate urgency
            return 1.5
        else:
            # Low urgency when zone is large
            return 3.0

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
