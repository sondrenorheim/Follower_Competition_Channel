"""
Camera system for vertical climbing platformer.

Static camera showing entire vertical course at once.
"""


class PlatformerCamera:
    """
    Static camera for vertical climbing platformer

    Shows entire 500x700px game area at once, no scrolling.
    """

    def __init__(self, game_area_x, game_area_y, game_area_width, game_area_height):
        """
        Initialize static camera

        Args:
            game_area_x: X position of game area on screen
            game_area_y: Y position of game area on screen
            game_area_width: Width of game area (500px)
            game_area_height: Height of game area (700px, extended from original 500px)
        """
        self.game_area_x = game_area_x
        self.game_area_y = game_area_y
        self.game_area_width = game_area_width
        self.game_area_height = game_area_height

        # Static camera - no movement
        self.camera_x = 0
        self.camera_y = 0

    def update(self, racers, level, first_finisher=None):
        """
        Update camera (no-op for static camera)

        Args:
            racers: List of racer objects (unused)
            level: Level object (unused)
            first_finisher: First finisher racer (unused)
        """
        # Static camera never moves
        pass

    def world_to_screen(self, world_pos):
        """
        Convert world coordinates to screen coordinates

        Since camera is static, this is just a simple translation
        to the game area position on screen.

        Args:
            world_pos: Tuple (x, y) in world coordinates

        Returns:
            Tuple (screen_x, screen_y) in screen coordinates
        """
        screen_x = self.game_area_x + world_pos[0]
        screen_y = self.game_area_y + world_pos[1]
        return (screen_x, screen_y)

    def is_visible(self, x, y):
        """
        Check if world position is visible in camera view

        Args:
            x: World X coordinate
            y: World Y coordinate

        Returns:
            bool: True if position is within game area bounds
        """
        return (0 <= x <= self.game_area_width and
                0 <= y <= self.game_area_height)

    def get_visible_bounds(self):
        """
        Get world coordinates of visible area

        Returns:
            Tuple (left, top, right, bottom) in world coordinates
        """
        return (0, 0, self.game_area_width, self.game_area_height)
