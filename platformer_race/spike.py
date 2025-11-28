"""
Spike hazard for vertical climbing platformer.

Spikes kill on contact and cause respawn.
"""

import math


class Spike:
    """
    Spike hazard that kills on contact
    """

    def __init__(self, x, y, width=40, height=10, orientation="up"):
        """
        Create a spike hazard

        Args:
            x: X position (left edge)
            y: Y position (base)
            width: Width in pixels (default 40)
            height: Height in pixels (default 10)
            orientation: "up", "down", "left", or "right" (default "up")
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.orientation = orientation
        self.color = (180, 50, 50)  # Dark red

    def check_collision(self, racer):
        """
        Check if racer touches spike

        Args:
            racer: PlatformerRacer instance

        Returns:
            bool: True if collision detected
        """
        # Simple box collision with racer circle
        racer_left = racer.x - racer.radius
        racer_right = racer.x + racer.radius
        racer_top = racer.y - racer.radius
        racer_bottom = racer.y + racer.radius

        spike_left = self.x
        spike_right = self.x + self.width
        spike_top = self.y
        spike_bottom = self.y + self.height

        # AABB collision
        if (racer_right >= spike_left and racer_left <= spike_right and
            racer_bottom >= spike_top and racer_top <= spike_bottom):
            return True

        return False
