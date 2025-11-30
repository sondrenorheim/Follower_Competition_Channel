"""
Obstacle Course Camera Module
Handles camera movement to follow the leader
"""

from typing import Tuple, Optional
import config


class ObstacleCourseCamera:
    """
    Camera that follows the leader in the obstacle course race
    Provides smooth scrolling and coordinate transformation
    """

    def __init__(self):
        """Initialize the camera"""
        self.camera_x = -150  # Start further left to show racers before race
        self.camera_y = config.SCREEN_HEIGHT / 2
        self.target_x = self.camera_x
        self.target_y = self.camera_y

        # Smoothing factor for camera movement (0.0 = no smoothing, 1.0 = instant)
        self.smoothing = 0.08

        # Minimum camera X (allows seeing behind starting line)
        self.min_camera_x = -150

    def update(self, leader_position: Optional[Tuple[float, float]], course_length: float, finish_line_x: Optional[float] = None):
        """
        Update camera to follow the leader (horizontal scrolling)

        Args:
            leader_position: (x, y) position of the leader, or None if no leader
            course_length: Total length of the course
            finish_line_x: X position of finish line (camera stops here)
        """
        if leader_position is None:
            return

        # Target camera position: keep leader at 60% from left (shows more racers behind)
        self.target_x = leader_position[0] - (config.SCREEN_WIDTH * 0.6)

        # Smooth camera movement using linear interpolation (X only)
        self.camera_x += (self.target_x - self.camera_x) * self.smoothing

        # Lock Y to screen center for straight horizontal track
        self.camera_y = config.SCREEN_HEIGHT / 2

        # Don't scroll left beyond minimum (allows seeing behind starting line)
        self.camera_x = max(self.min_camera_x, self.camera_x)

        # Stop camera at finish line if provided, otherwise use course length
        if finish_line_x is not None:
            # Stop when finish line is at 60% width from left of screen
            max_camera_x = finish_line_x - (config.SCREEN_WIDTH * 0.6)
        else:
            max_camera_x = course_length - config.SCREEN_WIDTH

        self.camera_x = min(max_camera_x, self.camera_x)

    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates

        Args:
            world_pos: (x, y) position in world space

        Returns:
            (screen_x, screen_y) position on screen
        """
        screen_x = int(world_pos[0] - self.camera_x)
        screen_y = int(world_pos[1] - self.camera_y + config.SCREEN_HEIGHT / 2)

        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos: Tuple[int, int]) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates

        Args:
            screen_pos: (x, y) position on screen

        Returns:
            (world_x, world_y) position in world space
        """
        world_x = screen_pos[0] + self.camera_x
        world_y = screen_pos[1] + self.camera_y - config.SCREEN_HEIGHT / 2

        return (world_x, world_y)

    def is_visible(self, world_pos: Tuple[float, float], margin: float = 100) -> bool:
        """
        Check if a position is visible on screen (with margin)

        Args:
            world_pos: (x, y) position in world space
            margin: Extra margin around screen edges

        Returns:
            True if position is visible
        """
        screen_pos = self.world_to_screen(world_pos)

        return (-margin <= screen_pos[0] <= config.SCREEN_WIDTH + margin and
                -margin <= screen_pos[1] <= config.SCREEN_HEIGHT + margin)

    def get_visible_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get the world space bounds of what's visible on screen

        Returns:
            (left, top, right, bottom) bounds in world coordinates
        """
        top_left = self.screen_to_world((0, 0))
        bottom_right = self.screen_to_world((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))

        return (top_left[0], top_left[1], bottom_right[0], bottom_right[1])

    def __repr__(self):
        return f"ObstacleCourseCamera(x={self.camera_x:.1f}, y={self.camera_y:.1f})"
