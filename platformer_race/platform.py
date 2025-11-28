"""
Platform classes for the platformer race game.

Includes static platforms and moving platforms (horizontal/vertical).
"""


class Platform:
    """Static horizontal platform"""

    def __init__(self, x, y, width, height, color=(100, 100, 100)):
        """
        Create a static platform

        Args:
            x: Top-left X position
            y: Top-left Y position
            width: Platform width in pixels
            height: Platform height in pixels
            color: RGB color tuple
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color

    def get_bounds(self):
        """
        Return platform bounds as (left, top, right, bottom)

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def contains_point(self, x, y):
        """
        Check if a point is inside the platform

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if point is inside platform, False otherwise
        """
        bounds = self.get_bounds()
        return (bounds[0] <= x <= bounds[2] and
                bounds[1] <= y <= bounds[3])


class MovingPlatform(Platform):
    """Platform that moves horizontally or vertically"""

    def __init__(self, x, y, width, height, move_type, move_distance, move_speed, color=(120, 120, 120)):
        """
        Create a moving platform

        Args:
            x: Starting top-left X position
            y: Starting top-left Y position
            width: Platform width in pixels
            height: Platform height in pixels
            move_type: "horizontal" or "vertical"
            move_distance: How far platform travels (pixels)
            move_speed: Speed in pixels/second
            color: RGB color tuple
        """
        super().__init__(x, y, width, height, color)

        self.move_type = move_type
        self.move_distance = move_distance
        self.move_speed = move_speed

        # Store starting position
        self.start_x = x
        self.start_y = y

        # Current direction (1 or -1)
        self.direction = 1

        # Distance traveled from start
        self.distance_traveled = 0.0

    def update(self, dt):
        """
        Update platform position based on movement pattern

        Args:
            dt: Delta time in seconds
        """
        # Calculate movement this frame
        movement = self.move_speed * dt * self.direction

        if self.move_type == "horizontal":
            # Move horizontally
            self.x += movement
            self.distance_traveled += abs(movement)

            # Reverse direction at limits
            if self.distance_traveled >= self.move_distance:
                self.direction *= -1
                self.distance_traveled = 0

                # Snap to exact position to prevent drift
                if self.direction == 1:
                    self.x = self.start_x
                else:
                    self.x = self.start_x + self.move_distance

        elif self.move_type == "vertical":
            # Move vertically
            self.y += movement
            self.distance_traveled += abs(movement)

            # Reverse direction at limits
            if self.distance_traveled >= self.move_distance:
                self.direction *= -1
                self.distance_traveled = 0

                # Snap to exact position to prevent drift
                if self.direction == 1:
                    self.y = self.start_y
                else:
                    self.y = self.start_y + self.move_distance

    def get_velocity(self):
        """
        Get current velocity of platform (for moving racers with platform)

        Returns:
            Tuple of (vx, vy) velocity
        """
        if self.move_type == "horizontal":
            return (self.move_speed * self.direction, 0)
        elif self.move_type == "vertical":
            return (0, self.move_speed * self.direction)
        return (0, 0)
