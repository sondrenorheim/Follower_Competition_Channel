"""
Checkpoint system for respawning in the platformer race.

Checkpoints are placed at safe areas throughout the course.
"""

import math


class Checkpoint:
    """Safe respawn point"""

    ACTIVATION_RADIUS = 50  # Pixels within which checkpoint activates

    def __init__(self, x, y, index):
        """
        Create a checkpoint

        Args:
            x: X position (center)
            y: Y position (center, usually above a safe platform)
            index: Checkpoint number (0, 1, 2...)
        """
        self.x = x
        self.y = y
        self.index = index

        # Set of racer IDs that have passed through this checkpoint
        self.activated_by = set()

    def check_activation(self, racer):
        """
        Check if racer activates this checkpoint and update their checkpoint index

        Args:
            racer: PlatformerRacer instance

        Returns:
            True if checkpoint was newly activated, False otherwise
        """
        # Calculate distance from racer to checkpoint
        distance = math.sqrt(
            (racer.x - self.x) ** 2 +
            (racer.y - self.y) ** 2
        )

        # Check if within activation radius
        if distance < self.ACTIVATION_RADIUS:
            if racer.id not in self.activated_by:
                # Newly activated
                self.activated_by.add(racer.id)
                racer.checkpoint_index = self.index
                return True

        return False

    def respawn_racer(self, racer):
        """
        Respawn racer at this checkpoint position

        Args:
            racer: PlatformerRacer instance
        """
        # Reset position
        racer.x = self.x
        racer.y = self.y

        # Reset physics state
        racer.vx = 0
        racer.vy = 0
        racer.on_ground = False
