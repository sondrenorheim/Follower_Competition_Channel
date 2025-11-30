"""
Course Generator Module
Procedurally generates obstacle courses with seeded randomization
"""

import random
import math
from typing import List, Tuple
import config
from .course import ObstacleCourse
from .obstacles import StaticWall, MovingWall, Spinner, SpeedBoost, SlowZone, Bumper, Crusher


class CourseGenerator:
    """
    Generates procedural obstacle courses using seeded randomization
    """

    def __init__(self, seed: int = None):
        """
        Initialize course generator

        Args:
            seed: Random seed for reproducible generation (uses DAY_NUMBER if None)
        """
        self.seed = seed if seed is not None else config.DAY_NUMBER
        random.seed(self.seed)

    def generate_course(self) -> ObstacleCourse:
        """
        Generate a complete obstacle course

        Returns:
            ObstacleCourse object with waypoints and obstacles
        """
        print(f"Generating course with seed {self.seed}...")

        # Generate the winding path waypoints
        waypoints = self._generate_waypoints()

        # Generate obstacles along the path
        obstacles = self._generate_obstacles(waypoints)

        print(f"Generated course: {len(waypoints)} waypoints, {len(obstacles)} obstacles")

        return ObstacleCourse(waypoints, obstacles)

    def _generate_waypoints(self) -> List[Tuple[float, float]]:
        """
        Generate waypoints defining a simple horizontal race track with gentle vertical waves

        Returns:
            List of (x, y) waypoints
        """
        waypoints = []

        # Starting position (left side, center vertically)
        start_x = 100
        start_y = config.SCREEN_HEIGHT / 2

        current_x = start_x
        current_y = start_y

        # Add starting waypoint
        waypoints.append((current_x, current_y))

        # Generate horizontal track with gentle vertical variations
        finish_x = config.OBSTACLE_COURSE_LENGTH * 0.67

        while current_x < finish_x:
            # Move horizontally
            current_x += config.COURSE_SEGMENT_LENGTH

            # Don't overshoot finish line
            if current_x > finish_x:
                current_x = finish_x

            # Keep Y fixed for a straight horizontal track
            waypoints.append((current_x, current_y))

        return waypoints


    def _generate_obstacles(self, waypoints: List[Tuple[float, float]]) -> List:
        """
        Generate obstacles along the course path

        Args:
            waypoints: List of waypoints defining the path

        Returns:
            List of obstacle objects
        """
        obstacles = []

        # Obstacle type weights (controls frequency)
        obstacle_types = [
            ('static', 15),      # Static walls - common
            ('moving', 10),      # Moving walls - common
            ('spinner', 8),      # Spinners - moderate
            ('bumper', 12),      # Bumpers - moderate
            # ('speed_boost', 6),  # Speed boosts - REMOVED
            ('slow_zone', 6),    # Slow zones - occasional
            ('crusher', 4),      # Crushers - rare, timing-based
        ]

        # Build weighted list
        weighted_types = []
        for obs_type, weight in obstacle_types:
            weighted_types.extend([obs_type] * weight)

        # Calculate finish line position and no-obstacle zone
        finish_x = waypoints[-1][0]
        no_obstacle_zone_start = finish_x - 50

        # Place obstacles between waypoints
        for i in range(len(waypoints) - 1):
            # Get segment start and end
            start_wp = waypoints[i]
            end_wp = waypoints[i + 1]

            # Number of obstacles in this segment (90% less obstacles)
            # Only 10% chance of placing an obstacle per segment
            if random.random() > 0.60:
                continue

            num_obstacles = 1  # Max 1 obstacle per segment when we do place one

            for _ in range(num_obstacles):
                # Position along segment
                t = random.uniform(0.2, 0.8)  # Avoid placing at segment ends
                obstacle_x = start_wp[0] + (end_wp[0] - start_wp[0]) * t
                obstacle_y = start_wp[1] + (end_wp[1] - start_wp[1]) * t

                # Skip if obstacle would be in the final 50 pixels before finish line
                if obstacle_x >= no_obstacle_zone_start:
                    continue

                # Decide obstacle type
                obstacle_type = random.choice(weighted_types)

                if obstacle_type == 'static':
                    obstacles.append(self._create_static_wall(obstacle_x, obstacle_y, waypoints[i]))
                elif obstacle_type == 'moving':
                    obstacles.append(self._create_moving_wall(obstacle_x, obstacle_y, waypoints[i]))
                elif obstacle_type == 'spinner':
                    obstacles.append(self._create_spinner(obstacle_x, obstacle_y, waypoints[i]))
                elif obstacle_type == 'bumper':
                    obstacles.append(self._create_bumper(obstacle_x, obstacle_y, waypoints[i]))
                elif obstacle_type == 'speed_boost':
                    obstacles.append(self._create_speed_boost(obstacle_x, obstacle_y, waypoints[i]))
                elif obstacle_type == 'slow_zone':
                    obstacles.append(self._create_slow_zone(obstacle_x, obstacle_y, waypoints[i]))
                elif obstacle_type == 'crusher':
                    obstacles.append(self._create_crusher(obstacle_x, obstacle_y, waypoints[i]))

        return obstacles

    def _create_static_wall(self, x: float, y: float, waypoint: Tuple[float, float]) -> StaticWall:
        """
        Create a static wall obstacle

        Args:
            x: X position
            y: Y position
            waypoint: Nearby waypoint (for track bounds reference)

        Returns:
            StaticWall obstacle
        """
        # Wall size (swapped for horizontal orientation)
        wall_width = random.uniform(20, 40)  # Narrow in X direction
        wall_height = random.uniform(60, 120)  # Tall in Y direction

        # Position: offset from center to up or down
        offset_direction = random.choice([-1, 1])
        offset_amount = random.uniform(30, 80)

        wall_x = x
        wall_y = y + (offset_direction * offset_amount)

        # Ensure wall stays within track bounds
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)
        wall_y = max(track_top + 10, min(track_bottom - wall_height - 10, wall_y))

        return StaticWall((wall_x, wall_y), (wall_width, wall_height))

    def _create_moving_wall(self, x: float, y: float, waypoint: Tuple[float, float]) -> MovingWall:
        """
        Create a moving wall obstacle (moves vertically)

        Args:
            x: X position
            y: Y position
            waypoint: Nearby waypoint (for track bounds reference)

        Returns:
            MovingWall obstacle
        """
        # Wall size
        wall_width = random.uniform(25, 45)
        wall_height = random.uniform(80, 140)

        # Get track bounds
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)

        # Wall starts at random position within track
        wall_x = x
        wall_y = random.uniform(track_top + 10, track_bottom - wall_height - 10)

        # Vertical movement
        velocity = random.uniform(30, 60)
        if random.random() < 0.5:
            velocity *= -1

        min_y = track_top + 10
        max_y = track_bottom - 10

        return MovingWall((wall_x, wall_y), (wall_width, wall_height), velocity, min_y, max_y)

    def _get_track_bounds_at_position(self, waypoint: Tuple[float, float]) -> Tuple[float, float]:
        """
        Get track boundaries near a waypoint

        Args:
            waypoint: (x, y) waypoint position

        Returns:
            (top_y, bottom_y) track bounds
        """
        center_y = waypoint[1]
        half_width = config.OBSTACLE_COURSE_WIDTH / 2

        return (center_y - half_width, center_y + half_width)

    def _create_spinner(self, x: float, y: float, waypoint: Tuple[float, float]) -> Spinner:
        """Create a spinning bar obstacle"""
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)
        half_bar = 90  # Half of max bar length to keep spinner arms in bounds

        # Place spinner at random position within track (keeping bar arms inside)
        spinner_y = random.uniform(track_top + half_bar, track_bottom - half_bar)

        # Random bar length and rotation speed
        bar_length = random.uniform(120, 180)
        rotation_speed = random.uniform(0.5, 1.5)
        if random.random() < 0.5:
            rotation_speed *= -1  # Reverse direction

        return Spinner((x, spinner_y), bar_length, rotation_speed)

    def _create_bumper(self, x: float, y: float, waypoint: Tuple[float, float]) -> Bumper:
        """Create a pinball-style bumper"""
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)

        # Random size and stronger bounce force to push racers away
        radius = random.uniform(20, 35)
        bounce_force = random.uniform(18, 25)  # Increased from 10-15

        # Position bumper at random position within track
        bumper_y = random.uniform(track_top + radius + 10, track_bottom - radius - 10)

        return Bumper((x, bumper_y), radius, bounce_force)

    def _create_speed_boost(self, x: float, y: float, waypoint: Tuple[float, float]) -> SpeedBoost:
        """Create a speed boost zone"""
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)

        # Size of boost zone
        zone_width = random.uniform(40, 70)
        zone_height = random.uniform(60, 100)

        # Position within track
        zone_y = random.uniform(track_top + 10, track_bottom - zone_height - 10)

        # Boost multiplier
        boost = random.uniform(1.5, 2.0)

        return SpeedBoost((x, zone_y), (zone_width, zone_height), boost)

    def _create_slow_zone(self, x: float, y: float, waypoint: Tuple[float, float]) -> SlowZone:
        """Create a slow/mud zone"""
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)

        # Size of slow zone (larger than speed boost)
        zone_width = random.uniform(60, 100)
        zone_height = random.uniform(80, 140)

        # Position within track
        zone_y = random.uniform(track_top + 10, track_bottom - zone_height - 10)

        # Slow multiplier
        slow = random.uniform(0.3, 0.5)

        return SlowZone((x, zone_y), (zone_width, zone_height), slow)

    def _create_crusher(self, x: float, y: float, waypoint: Tuple[float, float]) -> Crusher:
        """Create a crusher/piston obstacle"""
        track_top, track_bottom = self._get_track_bounds_at_position(waypoint)
        track_height = track_bottom - track_top

        # Position at top or bottom of track (not blocking entire track)
        height = track_height * 0.4  # Only 40% of track height
        if random.random() < 0.5:
            crusher_y = track_top + 5
        else:
            crusher_y = track_bottom - height - 5

        # Size and timing - longer retract time so racers can pass
        base_width = random.uniform(20, 30)
        extended_width = random.uniform(60, 80)
        extend_time = random.uniform(0.8, 1.2)   # Short extended time
        retract_time = random.uniform(2.0, 3.0)  # Longer retracted time to allow passage

        return Crusher((x, crusher_y), (base_width, height), extend_time, retract_time, extended_width)
