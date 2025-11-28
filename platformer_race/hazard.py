"""
Hazard classes for the platformer race game.

Includes fireballs with different movement patterns.
"""

import math


class Fireball:
    """Moving hazard that kills on contact (like Super Mario fireballs)"""

    def __init__(self, x, y, vx, vy, pattern="linear", radius=20, color=(255, 100, 50)):
        """
        Create a fireball hazard

        Args:
            x: Starting center X position
            y: Starting center Y position
            vx: Horizontal velocity (pixels/sec)
            vy: Vertical velocity (pixels/sec)
            pattern: Movement pattern - "linear", "arc", or "bounce"
            radius: Collision radius (default 20px)
            color: RGB color tuple (default orange/red)
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.pattern = pattern
        self.radius = radius
        self.color = color

        # For bounce pattern - store bounds
        self.bounce_top = y - 100
        self.bounce_bottom = y + 100

        # For arc pattern - apply gravity
        self.gravity = 800.0 if pattern == "arc" else 0.0

    def update(self, dt, platforms=None):
        """
        Update fireball position based on pattern

        Args:
            dt: Delta time in seconds
            platforms: List of platforms (for bounce pattern)
        """
        if self.pattern == "linear":
            # Simple linear movement
            self.x += self.vx * dt
            self.y += self.vy * dt

        elif self.pattern == "arc":
            # Parabolic trajectory with gravity
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.vy += self.gravity * dt  # Apply gravity

        elif self.pattern == "bounce":
            # Bounces up and down while moving horizontally
            self.x += self.vx * dt
            self.y += self.vy * dt

            # Bounce at top/bottom limits
            if self.y <= self.bounce_top and self.vy < 0:
                self.vy = abs(self.vy)  # Bounce down
            elif self.y >= self.bounce_bottom and self.vy > 0:
                self.vy = -abs(self.vy)  # Bounce up

    def check_collision(self, racer):
        """
        Check if fireball collides with racer (circle-circle collision)

        Args:
            racer: PlatformerRacer instance

        Returns:
            True if collision detected, False otherwise
        """
        # Calculate distance between centers
        dx = self.x - racer.x
        dy = self.y - racer.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if circles overlap
        collision_distance = self.radius + racer.radius
        return distance < collision_distance

    def is_off_screen(self, camera):
        """
        Check if fireball is off-screen and should be removed

        Args:
            camera: PlatformerCamera instance

        Returns:
            True if off-screen, False otherwise
        """
        visible_bounds = camera.get_visible_bounds()
        buffer = 500  # Extra buffer to keep fireballs a bit off-screen

        return (self.x < visible_bounds[0] - buffer or
                self.x > visible_bounds[2] + buffer)
