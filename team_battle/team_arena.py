"""
Team Arena Module
Arena with 4 quadrants and openable walls for team battle
"""

import pygame
import random
from typing import Tuple, List, Optional
from enum import Enum

import config
from .team_fighter import Team


class TeamArena:
    """
    Rectangular arena divided into 4 quadrants with walls.

    Layout (2x2 grid):
    ┌─────────┬─────────┐
    │   RED   │  BLUE   │
    │ (top-L) │ (top-R) │
    ├─────────┼─────────┤
    │  GREEN  │ YELLOW  │
    │ (bot-L) │ (bot-R) │
    └─────────┴─────────┘

    Walls:
    - horizontal_wall: Separates top row from bottom row
    - vertical_wall: Separates left column from right column

    Semi-final matchups (horizontal wall opens):
    - Red vs Blue (top half)
    - Green vs Yellow (bottom half)

    Finals (vertical wall opens):
    - Winning teams fight
    """

    def __init__(self):
        """Initialize the team arena"""
        # Get arena bounds from config (same as fighter arena)
        self.x, self.y, self.width, self.height = config.FIGHTER_ARENA_RECT

        # Calculate center
        self.center_x = self.x + self.width // 2
        self.center_y = self.y + self.height // 2

        # Wall states (True = closed, False = open)
        self.horizontal_wall_closed = True  # Separates top/bottom
        self.vertical_wall_closed = True    # Separates left/right

        # Wall animation state (0.0 = fully closed, 1.0 = fully open)
        self.horizontal_wall_open_progress = 0.0
        self.vertical_wall_open_progress = 0.0
        self.wall_animation_speed = 1.5  # Takes ~0.67 seconds to fully open

        # Wall thickness for collision
        self.wall_thickness = 6

        # Quadrant dimensions
        self.quadrant_width = self.width // 2
        self.quadrant_height = self.height // 2

        # Calculate quadrant bounds
        self.quadrants = {
            Team.RED: (self.x, self.y, self.quadrant_width, self.quadrant_height),
            Team.BLUE: (self.center_x, self.y, self.quadrant_width, self.quadrant_height),
            Team.GREEN: (self.x, self.center_y, self.quadrant_width, self.quadrant_height),
            Team.YELLOW: (self.center_x, self.center_y, self.quadrant_width, self.quadrant_height),
        }

        print(f"Team Arena initialized: {self.width}x{self.height}")
        print(f"Quadrant size: {self.quadrant_width}x{self.quadrant_height}")

    def get_rect(self) -> Tuple[int, int, int, int]:
        """Get arena rectangle bounds"""
        return (self.x, self.y, self.width, self.height)

    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get arena bounds as (left, top, right, bottom)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def get_quadrant_bounds(self, team: Team) -> Tuple[int, int, int, int]:
        """
        Get bounds for a specific team's quadrant

        Args:
            team: Team enum value

        Returns:
            (x, y, width, height) of the quadrant
        """
        return self.quadrants[team]

    def get_random_position_in_quadrant(self, team: Team, margin: float = 30) -> Tuple[float, float]:
        """
        Get a random position within a team's quadrant

        Args:
            team: Team to get position for
            margin: Distance from edges

        Returns:
            (x, y) position
        """
        qx, qy, qw, qh = self.quadrants[team]
        x = random.uniform(qx + margin, qx + qw - margin)
        y = random.uniform(qy + margin, qy + qh - margin)
        return (x, y)

    def clamp_to_quadrant(self, x: float, y: float, radius: float, team: Team) -> Tuple[float, float]:
        """
        Clamp position to stay within a team's quadrant (used when walls are closed)

        Args:
            x, y: Current position
            radius: Entity radius
            team: Team whose quadrant to clamp to

        Returns:
            (clamped_x, clamped_y)
        """
        qx, qy, qw, qh = self.quadrants[team]

        # Add extra margin from center walls to prevent overlap issues
        wall_margin = self.wall_thickness + 2

        # Clamp to quadrant bounds with wall margin on interior edges
        # Exterior edges use normal radius, interior edges (near walls) use wall_margin
        is_left = team in (Team.RED, Team.GREEN)
        is_top = team in (Team.RED, Team.BLUE)

        # Left bound
        left_bound = qx + radius
        # Right bound - add wall margin if on left side (wall is on right)
        right_bound = qx + qw - radius - (wall_margin if is_left else 0)
        # Top bound
        top_bound = qy + radius
        # Bottom bound - add wall margin if on top side (wall is below)
        bottom_bound = qy + qh - radius - (wall_margin if is_top else 0)

        new_x = max(left_bound, min(right_bound, x))
        new_y = max(top_bound, min(bottom_bound, y))

        return (new_x, new_y)

    def start_opening_horizontal_wall(self):
        """Start animating horizontal wall open"""
        # Wall will be fully opened when animation completes
        print("Horizontal wall opening...")

    def start_opening_vertical_wall(self):
        """Start animating vertical wall open"""
        print("Vertical wall opening...")

    def open_horizontal_wall(self):
        """Instantly open the horizontal wall (for backwards compatibility)"""
        self.horizontal_wall_closed = False
        self.horizontal_wall_open_progress = 1.0
        print("Horizontal wall opened!")

    def open_vertical_wall(self):
        """Instantly open the vertical wall (for backwards compatibility)"""
        self.vertical_wall_closed = False
        self.vertical_wall_open_progress = 1.0
        print("Vertical wall opened!")

    def is_horizontal_wall_animating(self) -> bool:
        """Check if horizontal wall is currently animating"""
        return not self.horizontal_wall_closed and self.horizontal_wall_open_progress < 1.0

    def is_vertical_wall_animating(self) -> bool:
        """Check if vertical wall is currently animating"""
        return not self.vertical_wall_closed and self.vertical_wall_open_progress < 1.0

    def get_horizontal_wall_visual_height(self) -> float:
        """Get current visual height of horizontal wall (for rendering)"""
        if self.horizontal_wall_closed:
            return self.width  # Full width
        # Shrink from both ends toward center
        return self.width * (1.0 - self.horizontal_wall_open_progress)

    def get_vertical_wall_visual_height(self) -> float:
        """Get current visual height of vertical wall (for rendering)"""
        if self.vertical_wall_closed:
            return self.height  # Full height
        # Shrink from both ends toward center
        return self.height * (1.0 - self.vertical_wall_open_progress)

    def close_all_walls(self):
        """Close all walls"""
        self.horizontal_wall_closed = True
        self.vertical_wall_closed = True

    def is_blocked_by_wall(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """
        Check if movement from (x1, y1) to (x2, y2) is blocked by a wall

        Args:
            x1, y1: Starting position
            x2, y2: Ending position

        Returns:
            True if movement crosses a closed wall
        """
        # Check vertical wall (left/right barrier)
        if self.vertical_wall_closed:
            # Wall runs from center_x vertically
            # Check if line crosses the center_x
            if (x1 < self.center_x and x2 > self.center_x) or \
               (x1 > self.center_x and x2 < self.center_x):
                return True

        # Check horizontal wall (top/bottom barrier)
        if self.horizontal_wall_closed:
            # Wall runs from center_y horizontally
            # Check if line crosses the center_y
            if (y1 < self.center_y and y2 > self.center_y) or \
               (y1 > self.center_y and y2 < self.center_y):
                return True

        return False

    def clamp_position_with_walls(self, x: float, y: float, radius: float,
                                   prev_x: float = None, prev_y: float = None) -> Tuple[float, float]:
        """
        Clamp position to arena bounds and respect walls

        Args:
            x, y: Current position
            radius: Entity radius
            prev_x, prev_y: Previous position (for wall detection)

        Returns:
            (clamped_x, clamped_y)
        """
        left, top, right, bottom = self.get_bounds()

        # Clamp to arena bounds
        new_x = max(left + radius, min(right - radius, x))
        new_y = max(top + radius, min(bottom - radius, y))

        # If we don't have previous position, determine quadrant and constrain
        if prev_x is None:
            prev_x = x
        if prev_y is None:
            prev_y = y

        # Vertical wall check (left/right barrier)
        # Wall is solid if closed OR if animation hasn't completed
        if self.vertical_wall_closed or self.vertical_wall_open_progress < 1.0:
            wall_x = self.center_x
            half_thickness = self.wall_thickness / 2

            # Calculate how much of the wall is still blocking (shrinks from ends)
            wall_half_height = (self.height / 2) * (1.0 - self.vertical_wall_open_progress)
            wall_top = self.center_y - wall_half_height
            wall_bottom = self.center_y + wall_half_height

            # Only block if we're in the part of the wall that's still there
            if wall_top <= new_y <= wall_bottom:
                # Was on left side, trying to go right
                if prev_x < wall_x - half_thickness and new_x >= wall_x - half_thickness - radius:
                    new_x = wall_x - half_thickness - radius
                # Was on right side, trying to go left
                elif prev_x > wall_x + half_thickness and new_x <= wall_x + half_thickness + radius:
                    new_x = wall_x + half_thickness + radius

        # Horizontal wall check (top/bottom barrier)
        if self.horizontal_wall_closed or self.horizontal_wall_open_progress < 1.0:
            wall_y = self.center_y
            half_thickness = self.wall_thickness / 2

            # Calculate how much of the wall is still blocking (shrinks from ends)
            wall_half_width = (self.width / 2) * (1.0 - self.horizontal_wall_open_progress)
            wall_left = self.center_x - wall_half_width
            wall_right = self.center_x + wall_half_width

            # Only block if we're in the part of the wall that's still there
            if wall_left <= new_x <= wall_right:
                # Was on top side, trying to go bottom
                if prev_y < wall_y - half_thickness and new_y >= wall_y - half_thickness - radius:
                    new_y = wall_y - half_thickness - radius
                # Was on bottom side, trying to go top
                elif prev_y > wall_y + half_thickness and new_y <= wall_y + half_thickness + radius:
                    new_y = wall_y + half_thickness + radius

        return (new_x, new_y)

    def get_accessible_area(self, team: Team) -> List[Team]:
        """
        Get list of teams whose areas are accessible from a team's starting position

        Args:
            team: Starting team

        Returns:
            List of accessible teams (including self)
        """
        accessible = [team]

        # Determine which half the team is in
        is_top = team in (Team.RED, Team.BLUE)
        is_left = team in (Team.RED, Team.GREEN)

        # If horizontal wall is open, can access vertical neighbor
        if not self.horizontal_wall_closed:
            if is_top:
                # Top teams can access bottom teams in same column
                accessible.append(Team.GREEN if is_left else Team.YELLOW)
            else:
                # Bottom teams can access top teams in same column
                accessible.append(Team.RED if is_left else Team.BLUE)

        # If vertical wall is open, can access horizontal neighbor
        if not self.vertical_wall_closed:
            if is_left:
                # Left teams can access right teams in same row
                accessible.append(Team.BLUE if is_top else Team.YELLOW)
            else:
                # Right teams can access left teams in same row
                accessible.append(Team.RED if is_top else Team.GREEN)

        # If both walls open, all areas accessible
        if not self.horizontal_wall_closed and not self.vertical_wall_closed:
            accessible = list(Team)

        return accessible

    def update(self, dt: float):
        """Update arena state including wall animations"""
        # Animate horizontal wall opening
        if not self.horizontal_wall_closed and self.horizontal_wall_open_progress < 1.0:
            self.horizontal_wall_open_progress += dt * self.wall_animation_speed
            if self.horizontal_wall_open_progress >= 1.0:
                self.horizontal_wall_open_progress = 1.0
                print("Horizontal wall fully opened!")

        # Animate vertical wall opening
        if not self.vertical_wall_closed and self.vertical_wall_open_progress < 1.0:
            self.vertical_wall_open_progress += dt * self.wall_animation_speed
            if self.vertical_wall_open_progress >= 1.0:
                self.vertical_wall_open_progress = 1.0
                print("Vertical wall fully opened!")

    def __repr__(self):
        h_status = "closed" if self.horizontal_wall_closed else "open"
        v_status = "closed" if self.vertical_wall_closed else "open"
        return f"TeamArena(h_wall={h_status}, v_wall={v_status})"
