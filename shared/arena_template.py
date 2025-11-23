"""
Arena Template - Blueprint for game areas
Copy this file to your new game folder and customize it.

This template provides:
- Standard game area dimensions (500px width, configurable)
- Centered positioning on screen
- Boundary checking methods
- Support for different shapes (rectangle, circle, etc.)
- Optional shrinking/dynamic behavior

Usage:
1. Copy this file to your_game/arena.py
2. Rename the class to match your game (e.g., YourGameArena)
3. Customize the shape and behavior for your game
4. Add game-specific features (obstacles, zones, etc.)
"""

import pygame
import math
from typing import Tuple, Optional
from enum import Enum

import config


# =============================================================================
# LAYOUT CONSTANTS - Standard positioning for all games
# =============================================================================

# Default game area dimensions (same as obstacle course track width)
DEFAULT_GAME_WIDTH = 500
DEFAULT_GAME_HEIGHT = 700

# Calculate positions based on screen size
GAME_AREA_LEFT = (config.SCREEN_WIDTH - DEFAULT_GAME_WIDTH) // 2
GAME_AREA_TOP = 160
GAME_AREA_RIGHT = GAME_AREA_LEFT + DEFAULT_GAME_WIDTH
GAME_AREA_BOTTOM = GAME_AREA_TOP + DEFAULT_GAME_HEIGHT


class ArenaShape(Enum):
    """Supported arena shapes."""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    SQUARE = "square"
    HEXAGON = "hexagon"
    OCTAGON = "octagon"


class ArenaTemplate:
    """
    Template for game arenas/play areas.

    Provides:
    - Configurable dimensions and shape
    - Centered positioning on screen
    - Boundary checking
    - Optional shrinking behavior

    Override methods to customize for your specific game.
    """

    # =============================================================================
    # CONFIGURATION - Override in subclass
    # =============================================================================

    # Dimensions
    WIDTH = DEFAULT_GAME_WIDTH
    HEIGHT = DEFAULT_GAME_HEIGHT

    # Shape (for circular arenas, WIDTH is used as diameter)
    SHAPE = ArenaShape.RECTANGLE

    # Shrinking (set to True for battle royale style shrinking)
    SHRINKS = False
    SHRINK_RATE = 0.1  # Pixels per second
    MIN_SIZE = 50  # Minimum width/radius before game ends

    def __init__(self):
        """Initialize the arena."""
        # Calculate position (centered on screen)
        self.left = (config.SCREEN_WIDTH - self.WIDTH) // 2
        self.top = GAME_AREA_TOP
        self.right = self.left + self.WIDTH
        self.bottom = self.top + self.HEIGHT

        # Center point
        self.center_x = self.left + self.WIDTH // 2
        self.center_y = self.top + self.HEIGHT // 2

        # Current dimensions (for shrinking arenas)
        self.current_width = self.WIDTH
        self.current_height = self.HEIGHT

        # For circular arenas
        self.initial_radius = self.WIDTH // 2
        self.current_radius = self.initial_radius

        # Game-specific initialization
        self._init_arena()

    def _init_arena(self):
        """
        Initialize arena-specific features.
        Override to add obstacles, zones, etc.
        """
        pass

    # =============================================================================
    # BOUNDARY CHECKING
    # =============================================================================

    def is_inside(self, x: float, y: float, entity_radius: float = 0) -> bool:
        """
        Check if a point/entity is inside the arena.

        Args:
            x, y: Position to check
            entity_radius: Radius of entity (for collision margin)

        Returns:
            True if position is inside arena bounds
        """
        if self.SHAPE == ArenaShape.CIRCLE:
            return self._is_inside_circle(x, y, entity_radius)
        elif self.SHAPE == ArenaShape.HEXAGON:
            return self._is_inside_hexagon(x, y, entity_radius)
        elif self.SHAPE == ArenaShape.OCTAGON:
            return self._is_inside_octagon(x, y, entity_radius)
        else:
            return self._is_inside_rectangle(x, y, entity_radius)

    def _is_inside_rectangle(self, x: float, y: float, radius: float = 0) -> bool:
        """Check if inside rectangular bounds."""
        # Calculate current bounds (for shrinking arenas)
        half_w = self.current_width / 2
        half_h = self.current_height / 2

        left = self.center_x - half_w + radius
        right = self.center_x + half_w - radius
        top = self.center_y - half_h + radius
        bottom = self.center_y + half_h - radius

        return left <= x <= right and top <= y <= bottom

    def _is_inside_circle(self, x: float, y: float, radius: float = 0) -> bool:
        """Check if inside circular bounds."""
        dx = x - self.center_x
        dy = y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= (self.current_radius - radius)

    def _is_inside_hexagon(self, x: float, y: float, radius: float = 0) -> bool:
        """Check if inside hexagonal bounds."""
        # Hexagon inscribed in circle
        dx = abs(x - self.center_x)
        dy = abs(y - self.center_y)

        effective_radius = self.current_radius - radius

        # Quick circle check first
        if dx * dx + dy * dy > effective_radius * effective_radius:
            return False

        # Hexagon check (flat-top orientation)
        return dy <= effective_radius * 0.866 and \
               dx <= effective_radius * (1 - dy / (effective_radius * 1.732))

    def _is_inside_octagon(self, x: float, y: float, radius: float = 0) -> bool:
        """Check if inside octagonal bounds."""
        dx = abs(x - self.center_x)
        dy = abs(y - self.center_y)

        effective_radius = self.current_radius - radius

        # Quick circle check first
        if dx * dx + dy * dy > effective_radius * effective_radius:
            return False

        # Octagon check
        corner_cut = effective_radius * 0.414  # tan(22.5 degrees)
        return dx <= effective_radius and dy <= effective_radius and \
               (dx + dy) <= effective_radius * 1.414 - corner_cut

    def get_distance_to_edge(self, x: float, y: float) -> float:
        """
        Get distance from a point to the nearest arena edge.

        Args:
            x, y: Position to check

        Returns:
            Distance to edge (negative if outside)
        """
        if self.SHAPE == ArenaShape.CIRCLE:
            dx = x - self.center_x
            dy = y - self.center_y
            distance = math.sqrt(dx * dx + dy * dy)
            return self.current_radius - distance
        else:
            # Rectangle: find distance to nearest edge
            half_w = self.current_width / 2
            half_h = self.current_height / 2

            dx = half_w - abs(x - self.center_x)
            dy = half_h - abs(y - self.center_y)

            return min(dx, dy)

    def clamp_position(self, x: float, y: float, entity_radius: float = 0) -> Tuple[float, float]:
        """
        Clamp a position to stay inside the arena.

        Args:
            x, y: Position to clamp
            entity_radius: Radius of entity

        Returns:
            (x, y) clamped position
        """
        if self.SHAPE == ArenaShape.CIRCLE:
            return self._clamp_to_circle(x, y, entity_radius)
        else:
            return self._clamp_to_rectangle(x, y, entity_radius)

    def _clamp_to_rectangle(self, x: float, y: float, radius: float = 0) -> Tuple[float, float]:
        """Clamp to rectangular bounds."""
        half_w = self.current_width / 2
        half_h = self.current_height / 2

        min_x = self.center_x - half_w + radius
        max_x = self.center_x + half_w - radius
        min_y = self.center_y - half_h + radius
        max_y = self.center_y + half_h - radius

        return (
            max(min_x, min(max_x, x)),
            max(min_y, min(max_y, y))
        )

    def _clamp_to_circle(self, x: float, y: float, radius: float = 0) -> Tuple[float, float]:
        """Clamp to circular bounds."""
        dx = x - self.center_x
        dy = y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)

        max_distance = self.current_radius - radius

        if distance <= max_distance:
            return (x, y)

        # Push back to edge
        if distance > 0:
            scale = max_distance / distance
            return (
                self.center_x + dx * scale,
                self.center_y + dy * scale
            )

        return (self.center_x, self.center_y)

    # =============================================================================
    # SHRINKING BEHAVIOR
    # =============================================================================

    def update(self, dt: float):
        """
        Update arena state (for shrinking, animations, etc.).

        Args:
            dt: Delta time in seconds
        """
        if self.SHRINKS:
            self._update_shrinking(dt)

        # Game-specific updates
        self._update_arena(dt)

    def _update_shrinking(self, dt: float):
        """Update shrinking behavior."""
        shrink_amount = self.SHRINK_RATE * dt

        if self.SHAPE == ArenaShape.CIRCLE:
            self.current_radius = max(self.MIN_SIZE, self.current_radius - shrink_amount)
        else:
            # Shrink rectangle uniformly
            self.current_width = max(self.MIN_SIZE, self.current_width - shrink_amount * 2)
            self.current_height = max(self.MIN_SIZE, self.current_height - shrink_amount * 2)

    def _update_arena(self, dt: float):
        """
        Update arena-specific behavior.
        Override for game-specific updates (obstacles, zones, etc.).
        """
        pass

    def get_shrink_percentage(self) -> float:
        """
        Get the current shrink percentage.

        Returns:
            0.0 = full size, 1.0 = minimum size
        """
        if self.SHAPE == ArenaShape.CIRCLE:
            shrunk = self.initial_radius - self.current_radius
            max_shrink = self.initial_radius - self.MIN_SIZE
        else:
            shrunk = self.WIDTH - self.current_width
            max_shrink = self.WIDTH - self.MIN_SIZE

        if max_shrink <= 0:
            return 0.0

        return min(1.0, shrunk / max_shrink)

    def is_at_minimum_size(self) -> bool:
        """Check if arena has shrunk to minimum size."""
        if self.SHAPE == ArenaShape.CIRCLE:
            return self.current_radius <= self.MIN_SIZE
        else:
            return self.current_width <= self.MIN_SIZE

    # =============================================================================
    # BOUNDARY ACCESSORS
    # =============================================================================

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get current arena bounds.

        Returns:
            (left, top, right, bottom) tuple
        """
        half_w = self.current_width / 2
        half_h = self.current_height / 2

        return (
            self.center_x - half_w,
            self.center_y - half_h,
            self.center_x + half_w,
            self.center_y + half_h
        )

    def get_center(self) -> Tuple[float, float]:
        """Get arena center point."""
        return (self.center_x, self.center_y)

    def get_radius(self) -> float:
        """Get current radius (for circular arenas)."""
        return self.current_radius

    def get_random_position(self, margin: float = 0) -> Tuple[float, float]:
        """
        Get a random position inside the arena.

        Args:
            margin: Minimum distance from edges

        Returns:
            (x, y) random position
        """
        import random

        if self.SHAPE == ArenaShape.CIRCLE:
            # Random point in circle
            angle = random.uniform(0, 2 * math.pi)
            max_r = self.current_radius - margin
            r = random.uniform(0, max_r)

            return (
                self.center_x + r * math.cos(angle),
                self.center_y + r * math.sin(angle)
            )
        else:
            # Random point in rectangle
            half_w = self.current_width / 2 - margin
            half_h = self.current_height / 2 - margin

            return (
                self.center_x + random.uniform(-half_w, half_w),
                self.center_y + random.uniform(-half_h, half_h)
            )

    # =============================================================================
    # RENDERING HELPERS
    # =============================================================================

    def get_draw_rect(self) -> pygame.Rect:
        """Get a pygame Rect for drawing the arena."""
        left, top, right, bottom = self.get_bounds()
        return pygame.Rect(left, top, right - left, bottom - top)

    def draw_boundary(self, screen: pygame.Surface, color: Tuple[int, int, int],
                     width: int = 3):
        """
        Draw the arena boundary.

        Args:
            screen: Pygame surface to draw on
            color: Boundary color
            width: Line width
        """
        if self.SHAPE == ArenaShape.CIRCLE:
            pygame.draw.circle(screen, color,
                             (int(self.center_x), int(self.center_y)),
                             int(self.current_radius), width)
        elif self.SHAPE == ArenaShape.HEXAGON:
            self._draw_polygon(screen, 6, color, width)
        elif self.SHAPE == ArenaShape.OCTAGON:
            self._draw_polygon(screen, 8, color, width)
        else:
            rect = self.get_draw_rect()
            pygame.draw.rect(screen, color, rect, width)

    def _draw_polygon(self, screen: pygame.Surface, sides: int,
                     color: Tuple[int, int, int], width: int):
        """Draw a regular polygon arena boundary."""
        points = []
        angle_step = 2 * math.pi / sides

        for i in range(sides):
            angle = i * angle_step - math.pi / 2  # Start from top
            x = self.center_x + self.current_radius * math.cos(angle)
            y = self.center_y + self.current_radius * math.sin(angle)
            points.append((x, y))

        pygame.draw.polygon(screen, color, points, width)

    def fill(self, screen: pygame.Surface, color: Tuple[int, int, int]):
        """
        Fill the arena with a color.

        Args:
            screen: Pygame surface
            color: Fill color
        """
        if self.SHAPE == ArenaShape.CIRCLE:
            pygame.draw.circle(screen, color,
                             (int(self.center_x), int(self.center_y)),
                             int(self.current_radius))
        elif self.SHAPE == ArenaShape.HEXAGON:
            self._fill_polygon(screen, 6, color)
        elif self.SHAPE == ArenaShape.OCTAGON:
            self._fill_polygon(screen, 8, color)
        else:
            rect = self.get_draw_rect()
            pygame.draw.rect(screen, color, rect)

    def _fill_polygon(self, screen: pygame.Surface, sides: int,
                     color: Tuple[int, int, int]):
        """Fill a regular polygon."""
        points = []
        angle_step = 2 * math.pi / sides

        for i in range(sides):
            angle = i * angle_step - math.pi / 2
            x = self.center_x + self.current_radius * math.cos(angle)
            y = self.center_y + self.current_radius * math.sin(angle)
            points.append((x, y))

        pygame.draw.polygon(screen, color, points)
