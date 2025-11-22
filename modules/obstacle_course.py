"""
Obstacle Course Module
Defines the course structure with waypoints and obstacles
"""

from typing import List, Tuple
import config


class ObstacleCourse:
    """
    Represents the obstacle course track
    Contains waypoints defining the path and obstacles along the way
    """

    def __init__(self, waypoints: List[Tuple[float, float]], obstacles: List['Obstacle']):
        """
        Initialize the obstacle course

        Args:
            waypoints: List of (x, y) points defining the center path
            obstacles: List of obstacle objects on the course
        """
        self.waypoints = waypoints
        self.obstacles = obstacles

        # Course boundaries
        self.start_line = waypoints[0] if waypoints else (config.SCREEN_WIDTH // 2, 0)
        self.finish_line = waypoints[-1] if waypoints else (config.SCREEN_WIDTH // 2, config.OBSTACLE_COURSE_LENGTH)

        # Track dimensions
        self.width = config.OBSTACLE_COURSE_WIDTH
        self.length = config.OBSTACLE_COURSE_LENGTH

    def get_progress(self, position: Tuple[float, float]) -> float:
        """
        Calculate how far along the course a position is (0.0 to 1.0)

        Args:
            position: (x, y) position to check

        Returns:
            Progress as percentage (0.0 at start, 1.0 at finish)
        """
        # Horizontal progress (left to right)
        x_progress = (position[0] - self.start_line[0]) / (self.finish_line[0] - self.start_line[0])
        return max(0.0, min(1.0, x_progress))

    def get_distance_to_finish(self, position: Tuple[float, float]) -> float:
        """
        Calculate straight-line distance from position to finish line

        Args:
            position: (x, y) position to check

        Returns:
            Distance in pixels
        """
        import math
        dx = position[0] - self.finish_line[0]
        dy = position[1] - self.finish_line[1]
        return math.sqrt(dx * dx + dy * dy)

    def get_nearest_waypoint_index(self, position: Tuple[float, float]) -> int:
        """
        Find the index of the nearest waypoint ahead of the given position

        Args:
            position: (x, y) position to check

        Returns:
            Index of nearest waypoint ahead
        """
        import math

        # Find waypoints ahead of current position (further along course in X direction)
        for i, waypoint in enumerate(self.waypoints):
            if waypoint[0] > position[0]:  # Ahead in X direction
                return i

        # If no waypoint ahead, return last waypoint
        return len(self.waypoints) - 1

    def is_past_finish(self, position: Tuple[float, float]) -> bool:
        """
        Check if a position has crossed the finish line

        Args:
            position: (x, y) position to check

        Returns:
            True if position is past the finish line
        """
        return position[0] >= self.finish_line[0]

    def get_track_bounds_at_x(self, x: float) -> Tuple[float, float]:
        """
        Get the top and bottom boundaries of the track at a given X position
        Interpolates between waypoints for accurate boundaries along curves

        NOTE: This method is deprecated for curved tracks. Use get_track_bounds_at_position() instead.
        Kept for backwards compatibility with renderer.

        Args:
            x: X position along track

        Returns:
            (top_y, bottom_y) boundaries
        """
        # Find the two waypoints that bracket this X position
        prev_waypoint = self.waypoints[0]
        next_waypoint = self.waypoints[-1]

        for i in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[i]
            wp2 = self.waypoints[i + 1]

            # Check if x is between these two waypoints
            if wp1[0] <= x <= wp2[0]:
                prev_waypoint = wp1
                next_waypoint = wp2
                break
            elif x < wp1[0]:
                # Before first waypoint, use first waypoint
                prev_waypoint = wp1
                next_waypoint = wp1
                break
        else:
            # Past last waypoint, use last waypoint
            prev_waypoint = self.waypoints[-1]
            next_waypoint = self.waypoints[-1]

        # Interpolate Y position between waypoints
        if prev_waypoint[0] == next_waypoint[0]:
            # Same X position, no interpolation needed
            center_y = prev_waypoint[1]
        else:
            # Linear interpolation
            t = (x - prev_waypoint[0]) / (next_waypoint[0] - prev_waypoint[0])
            t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
            center_y = prev_waypoint[1] + t * (next_waypoint[1] - prev_waypoint[1])

        half_width = self.width / 2
        return (center_y - half_width, center_y + half_width)



    def __repr__(self):
        return f"ObstacleCourse(waypoints={len(self.waypoints)}, obstacles={len(self.obstacles)}, length={self.length})"
