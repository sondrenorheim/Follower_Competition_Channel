"""
Team Arena Module
Open arena for sequential team battle tournaments
"""

import pygame
import random
from typing import Tuple, List, Optional

import config
from .team_fighter import Team


class TeamArena:
    """
    Rectangular arena for sequential team battles.

    Teams spawn on opposite sides for head-to-head matches.
    No walls or quadrants - simple open arena design.
    """

    def __init__(self):
        """Initialize the team arena"""
        # Get arena bounds from config (same as fighter arena)
        self.x, self.y, self.width, self.height = config.FIGHTER_ARENA_RECT

        # Calculate center
        self.center_x = self.x + self.width // 2
        self.center_y = self.y + self.height // 2

        print(f"Team Arena initialized: {self.width}x{self.height} (open arena)")

    def get_rect(self) -> Tuple[int, int, int, int]:
        """Get arena rectangle bounds"""
        return (self.x, self.y, self.width, self.height)

    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get arena bounds as (left, top, right, bottom)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def get_spawn_position_for_team(self, team: Team, match_teams: Tuple[Team, Team]) -> Tuple[float, float]:
        """
        Get spawn position for a team in the current match.
        Teams spawn on opposite sides of the arena.

        Args:
            team: Team to spawn
            match_teams: Tuple of (team_a, team_b) currently fighting

        Returns:
            (x, y) position
        """
        # Determine if this team is on left or right
        is_left_team = team == match_teams[0]

        # Spawn area: 30% of arena width on each side
        margin = 50
        spawn_width = int(self.width * 0.3)

        if is_left_team:
            # Left 30% of arena
            x = random.uniform(self.x + margin, self.x + spawn_width - margin)
        else:
            # Right 30% of arena
            x = random.uniform(self.x + self.width - spawn_width + margin,
                              self.x + self.width - margin)

        # Full height available
        y = random.uniform(self.y + margin, self.y + self.height - margin)

        return (x, y)

    def clamp_position(self, x: float, y: float, radius: float) -> Tuple[float, float]:
        """
        Clamp position to arena bounds (no walls)

        Args:
            x, y: Current position
            radius: Entity radius

        Returns:
            (clamped_x, clamped_y)
        """
        left, top, right, bottom = self.get_bounds()

        # Clamp to arena bounds
        new_x = max(left + radius, min(right - radius, x))
        new_y = max(top + radius, min(bottom - radius, y))

        return (new_x, new_y)

    def __repr__(self):
        return f"TeamArena(open, {self.width}x{self.height})"
