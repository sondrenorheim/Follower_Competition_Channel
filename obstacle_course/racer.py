"""
Racer Character Module
Represents racers in the Obstacle Course game mode
Extends Follower with racing-specific AI and abilities
"""

import pygame
import math
import random
import time
from typing import Optional, Tuple, List
import config
from battle_royale import Follower


class Racer(Follower):
    """
    Represents a racer in the Obstacle Course
    Extends Follower with racing AI, grab mechanic, and progress tracking
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize a racer

        Args:
            follower_data: Dictionary containing 'id', 'username', 'avatar', and optionally 'color'
            position: (x, y) starting position
        """
        super().__init__(follower_data, position)

        # Get default stats
        default_stats = config.RACER_DEFAULT_STATS

        # Get stat boosts for this username (if any)
        boosts = config.RACER_STAT_BOOSTS.get(self.username, {})

        # Initialize racing stats with defaults + boosts (no random variation)
        self.speed_stat = default_stats["speed"] + boosts.get("speed", 0)
        self.agility_stat = default_stats["agility"] + boosts.get("agility", 0)
        self.intelligence_stat = default_stats["intelligence"] + boosts.get("intelligence", 0)

        # Racing state
        self.progress = 0.0  # Progress along course (0.0 to 1.0)
        self.current_waypoint_index = 0
        self.finished = False
        self.finish_time = None
        self.placement = None

        # Dynamic speed multiplier that varies throughout the race
        self.speed_multiplier = random.uniform(0.85, 1.15)  # Tighter speed variance (was 0.5-1.5)
        self.next_speed_change_time = time.time() + random.uniform(0.5, 1.5)

        # Simple racing direction - primarily moves right with random Y adjustments
        self.target_y = self.y  # Target Y position for smooth vertical movement
        self.direction_change_time = 0  # When to pick new target Y
        self.vertical_velocity = 0.0
        self.vertical_accel = random.uniform(120.0, 180.0)  # Pixels per second^2

        # Speed modifier effects from obstacles
        self.speed_boost = 1.0  # Multiplier from speed boost zones
        self.speed_boost_end_time = 0  # When speed boost expires
        self.in_slow_zone = False  # Currently in a slow zone
        self.slow_zone_multiplier = 1.0  # Speed reduction in slow zone

        # Acceleration system - varies per racer for natural variation
        self.current_velocity = 0.0  # Current speed (accelerates toward target)
        self.acceleration_rate = random.uniform(0.015, 0.025)  # Slower acceleration for longer races

    def get_target_speed(self) -> float:
        """
        Get target movement speed (pixels per frame)
        Based on speed stat and dynamic multiplier (no zone effects)
        """
        base_speed = self.speed_stat / 2  # Reduced to 12 for slower, more watchable races

        # Apply dynamic speed multiplier (varies throughout race)
        return base_speed * self.speed_multiplier

    def get_movement_speed(self) -> float:
        """
        Get actual movement speed with acceleration system.
        Speed boosts and slow zones apply instantly, but normal acceleration is gradual.
        """
        target_speed = self.get_target_speed()

        # Check for instant velocity changes from obstacles
        # Speed boost (temporary effect) - INSTANT
        if time.time() < self.speed_boost_end_time:
            self.current_velocity = target_speed * self.speed_boost
            return self.current_velocity
        else:
            self.speed_boost = 1.0

        # Slow zone effect - INSTANT while in zone
        if self.in_slow_zone:
            self.current_velocity = target_speed * self.slow_zone_multiplier
            return self.current_velocity

        # Normal acceleration - gradual increase toward target speed
        if self.current_velocity < target_speed:
            self.current_velocity += self.acceleration_rate
            self.current_velocity = min(self.current_velocity, target_speed)

        return self.current_velocity

    def update_racer(self, dt: float, course, all_racers: List['Racer'], current_time: float):
        """
        Update racer state for obstacle course racing

        Args:
            dt: Delta time in seconds
            course: ObstacleCourse object
            all_racers: List of all racers
            current_time: Current game time
        """
        import math

        if not self.alive or self.finished:
            # Handle fade out animation for eliminated racers
            if not self.alive and time.time() - self.elimination_time < config.FADE_DURATION:
                progress = (time.time() - self.elimination_time) / config.FADE_DURATION
                self.alpha = int(255 * (1 - progress))
                self.surface_needs_update = True
            return

        # Update progress (simple horizontal progress)
        self.progress = course.get_progress((self.x, self.y))

        # Reset slow zone flag (will be set again if still in zone)
        self.in_slow_zone = False

        # Update speed multiplier periodically (varies throughout race)
        if current_time >= self.next_speed_change_time:
            # Change speed multiplier to a new random value
            self.speed_multiplier = random.uniform(0.85, 1.15)  # Tighter speed variance (was 0.5-1.5)
            # Next change in 0.5-1.5 seconds
            self.next_speed_change_time = current_time + random.uniform(0.5, 1.5)

        # Pick new target Y position periodically
        if current_time >= self.direction_change_time:
            self._pick_new_target_y(course, current_time)

        # Store old position for collision resolution
        old_x, old_y = self.x, self.y
        radius = config.OBSTACLE_COURSE_FOLLOWER_RADIUS

        # Calculate movement - primarily horizontal (right) with smooth vertical adjustments
        movement_speed = self.get_movement_speed()

        # Horizontal movement (always moving right)
        move_x = movement_speed * dt * 60

        # Vertical movement (smooth interpolation toward target Y)
        # Block vertical movement for first 100 pixels after start line
        start_line_x = course.start_line[0]
        if self.x < start_line_x + 100:
            move_y = 0  # No vertical movement in starting zone
            self.vertical_velocity = 0.0
        else:
            y_diff = self.target_y - self.y
            max_vertical_speed = movement_speed * 0.75 * 60
            target_velocity = max(-max_vertical_speed, min(max_vertical_speed, y_diff * 1.5))
            if self.vertical_velocity < target_velocity:
                self.vertical_velocity = min(target_velocity, self.vertical_velocity + self.vertical_accel * dt)
            else:
                self.vertical_velocity = max(target_velocity, self.vertical_velocity - self.vertical_accel * dt)
            move_y = self.vertical_velocity * dt

        # Apply movement
        self.x += move_x
        self.y += move_y

        # Keep within track bounds
        track_top, track_bottom = course.get_track_bounds_at_x(self.x)
        if self.y - radius < track_top:
            self.y = track_top + radius
            self._pick_new_target_y(course, current_time)
        elif self.y + radius > track_bottom:
            self.y = track_bottom - radius
            self._pick_new_target_y(course, current_time)

        # Check obstacle collisions AFTER movement
        from .obstacles import SpeedBoost, SlowZone

        hit_obstacle = False
        for obstacle in course.obstacles:
            if obstacle.check_collision((self.x, self.y), radius):
                # Speed boost and slow zones are pass-through - don't push out
                if isinstance(obstacle, (SpeedBoost, SlowZone)):
                    # Just apply the effect, don't block movement
                    obstacle.apply_collision_effect(self)
                else:
                    # Solid obstacle - push out
                    hit_obstacle = True
                    self._push_out_of_obstacle(obstacle, old_x, old_y)
                    # Pick new target Y to avoid obstacle
                    self._pick_new_target_y(course, current_time)
                    break

        # Check for finish line crossing
        if course.is_past_finish((self.x, self.y)) and not self.finished:
            self.finished = True
            self.finish_time = current_time

    def _push_out_of_obstacle(self, obstacle, old_x: float, old_y: float):
        """
        Push racer out of obstacle to the nearest edge

        Args:
            obstacle: The obstacle we collided with
            old_x, old_y: Position before movement
        """
        from .obstacles import Spinner
        if isinstance(obstacle, Spinner):
            self._push_out_of_spinner(obstacle)
            return

        bounds = obstacle.get_bounds()  # (left, top, right, bottom)
        radius = config.OBSTACLE_COURSE_FOLLOWER_RADIUS

        # Calculate how far into each side we are
        penetration_left = (bounds[0] - radius) - self.x   # negative if inside from left
        penetration_right = self.x - (bounds[2] + radius)  # negative if inside from right
        penetration_top = (bounds[1] - radius) - self.y    # negative if inside from top
        penetration_bottom = self.y - (bounds[3] + radius) # negative if inside from bottom

        # Find which edge is closest (least penetration to escape)
        # We want to push to the edge that requires least movement
        escapes = []

        # Can escape left?
        if old_x < self.x:  # We were moving right, escape left
            escapes.append(('left', abs(self.x - (bounds[0] - radius))))
        else:  # Moving left or stationary, escape right
            escapes.append(('right', abs((bounds[2] + radius) - self.x)))

        # Can escape top/bottom based on movement direction
        if old_y < self.y:  # Moving down, escape up
            escapes.append(('top', abs(self.y - (bounds[1] - radius))))
        else:  # Moving up, escape down
            escapes.append(('bottom', abs((bounds[3] + radius) - self.y)))

        # Pick the shortest escape
        escape_dir, _ = min(escapes, key=lambda x: x[1])

        if escape_dir == 'left':
            self.x = bounds[0] - radius
        elif escape_dir == 'right':
            self.x = bounds[2] + radius
        elif escape_dir == 'top':
            self.y = bounds[1] - radius
        elif escape_dir == 'bottom':
            self.y = bounds[3] + radius

    def _push_out_of_spinner(self, spinner):
        import math

        end1, end2 = spinner.get_bar_endpoints()
        ax, ay = end1
        bx, by = end2
        px, py = self.x, self.y

        abx = bx - ax
        aby = by - ay
        ab_sq = abx * abx + aby * aby
        if ab_sq == 0:
            return

        t = ((px - ax) * abx + (py - ay) * aby) / ab_sq
        t = max(0.0, min(1.0, t))
        closest_x = ax + t * abx
        closest_y = ay + t * aby

        dx = px - closest_x
        dy = py - closest_y
        dist = math.hypot(dx, dy)
        min_dist = config.OBSTACLE_COURSE_FOLLOWER_RADIUS + (spinner.bar_width / 2) + 2.0

        if dist == 0:
            # Use bar normal if we land exactly on the bar line
            nx = -aby
            ny = abx
            norm = math.hypot(nx, ny)
            if norm > 0:
                dx = nx / norm
                dy = ny / norm
                dist = 1.0
            else:
                dx, dy, dist = 1.0, 0.0, 1.0

        self.x = closest_x + (dx / dist) * min_dist
        self.y = closest_y + (dy / dist) * min_dist

    def _pick_new_target_y(self, course, current_time: float):
        """
        Pick a new target Y position for vertical movement (lane changes)

        Args:
            course: ObstacleCourse object
            current_time: Current game time
        """
        # Get track bounds at current position
        track_top, track_bottom = course.get_track_bounds_at_x(self.x)

        # Pick any position within the full track height
        margin = config.OBSTACLE_COURSE_FOLLOWER_RADIUS + 6
        track_height = track_bottom - track_top - 2 * margin
        if track_height <= 0:
            return

        new_target = track_top + margin + random.uniform(0, track_height)
        if abs(new_target - self.y) < track_height * 0.15:
            if new_target < self.y:
                new_target = max(track_top + margin, new_target - track_height * 0.25)
            else:
                new_target = min(track_bottom - margin, new_target + track_height * 0.25)
        self.target_y = new_target

        # Set time for next direction change
        self.direction_change_time = current_time + random.uniform(2.5, 4.5)

    def get_stats_summary(self) -> dict:
        """Get summary of racer's stats"""
        return {
            "speed": self.speed_stat,
            "agility": self.agility_stat,
            "intelligence": self.intelligence_stat,
            "progress": f"{self.progress * 100:.1f}%",
        }

    def __repr__(self):
        status = "FINISHED" if self.finished else ("ALIVE" if self.alive else "ELIMINATED")
        progress_str = f"{self.progress * 100:.1f}%"
        return f"Racer({self.username}, {status}, progress={progress_str}, pos=({self.x:.1f}, {self.y:.1f}))"
