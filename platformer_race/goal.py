"""
Goal class for vertical climbing platformer.

Defines the finish line that racers must reach to complete the race.
"""

import math


class Goal:
    """
    Goal flag at the top of the vertical course
    """

    def __init__(self, x, y, radius=40):
        """
        Create a goal

        Args:
            x: X position (center)
            y: Y position (center)
            radius: Activation radius in pixels (default 40)
        """
        self.x = x
        self.y = y
        self.radius = radius
        self.reached_by = set()  # Set of racer IDs that reached goal

    def check_reached(self, racer):
        """
        Check if racer has reached the goal

        Racer must be on the ground (landed on platform) to finish

        Args:
            racer: Racer object to check

        Returns:
            bool: True if racer reached goal, False otherwise
        """
        distance = math.dist((racer.x, racer.y), (self.x, self.y))

        # Racer must be on ground and within radius to finish
        if distance < self.radius and racer.on_ground:
            if racer.id not in self.reached_by:
                self.reached_by.add(racer.id)
                return True

        return False

    def is_within_range(self, x, y, range_multiplier=1.5):
        """
        Check if position is within extended range of goal

        Useful for AI pathfinding to know when getting close to goal

        Args:
            x: X coordinate
            y: Y coordinate
            range_multiplier: Multiplier for radius check (default 1.5)

        Returns:
            bool: True if within range
        """
        distance = math.dist((x, y), (self.x, self.y))
        return distance < (self.radius * range_multiplier)

    def get_direction_to_goal(self, x, y):
        """
        Get normalized direction vector from position to goal

        Args:
            x: Current X position
            y: Current Y position

        Returns:
            Tuple[float, float]: Normalized direction (dx, dy)
        """
        dx = self.x - x
        dy = self.y - y

        distance = math.sqrt(dx**2 + dy**2)

        if distance > 0:
            return (dx / distance, dy / distance)
        else:
            return (0, 0)
