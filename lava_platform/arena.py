"""
Lava Platform Arena - square arena with a circular safe platform.
"""

import math
import random
from typing import Tuple

import config
from shared.arena_template import ArenaTemplate, ArenaShape


class Obstacle:
    """Rectangular obstacle that blocks player movement."""

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains_point(self, px: float, py: float, radius: float = 0) -> bool:
        """Check if a point (with optional radius) intersects this obstacle."""
        return (self.x - radius <= px <= self.x + self.width + radius and
                self.y - radius <= py <= self.y + self.height + radius)

    def get_rect(self) -> tuple:
        """Return (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)


class SafePlatform:
    """Represents the circular safe platform that spawns each round."""

    def __init__(
        self,
        center: Tuple[float, float],
        radius: float,
    ):
        self.center = center
        self.radius = radius
        self.active = False

    def contains_point(self, x: float, y: float, entity_radius: float = 0) -> bool:
        """Check if a point is within the safe platform."""
        dx = x - self.center[0]
        dy = y - self.center[1]
        distance = math.hypot(dx, dy)
        return distance <= (self.radius - entity_radius)

    def reset(self):
        """Reset platform state for new round."""
        self.active = False


class LavaPlatformArena(ArenaTemplate):
    """Square arena with a circular safe platform that moves each round."""

    WIDTH = 460
    HEIGHT = 460
    SHAPE = ArenaShape.RECTANGLE

    def _init_arena(self):
        """Initialize arena-specific features."""
        self.arena_size = getattr(config, "LAVA_PLATFORM_ARENA_SIZE", 460)
        self.WIDTH = self.arena_size
        self.HEIGHT = self.arena_size

        initial_radius = getattr(config, "LAVA_PLATFORM_INITIAL_RADIUS", 120)
        self.safe_platform = SafePlatform(self.get_center(), initial_radius)
        self.lava_active = False
        self.lava_animation_progress = 0.0
        self.lava_animation_speed = 2.0
        self.obstacles = []

    def spawn_platform(self, radius: float, margin: float = None) -> SafePlatform:
        """
        Spawn platform at random position within bounds.

        Args:
            radius: Platform radius for this round
            margin: Minimum distance from arena edges

        Returns:
            SafePlatform at new position
        """
        if margin is None:
            margin = getattr(config, "LAVA_PLATFORM_PLATFORM_MARGIN", 30)

        min_x = self.left + margin + radius
        max_x = self.right - margin - radius
        min_y = self.top + margin + radius
        max_y = self.bottom - margin - radius

        if max_x <= min_x:
            cx = (self.left + self.right) / 2
        else:
            cx = random.uniform(min_x, max_x)

        if max_y <= min_y:
            cy = (self.top + self.bottom) / 2
        else:
            cy = random.uniform(min_y, max_y)

        self.safe_platform = SafePlatform((cx, cy), radius)
        self.safe_platform.active = True
        self.lava_active = False
        self.lava_animation_progress = 0.0

        return self.safe_platform

    def is_on_platform(self, x: float, y: float, entity_radius: float = 0) -> bool:
        """Check if position is on the safe platform."""
        if not self.safe_platform or not self.safe_platform.active:
            return False
        return self.safe_platform.contains_point(x, y, entity_radius)

    def activate_lava(self):
        """Trigger lava fill animation."""
        self.lava_active = True
        self.lava_animation_progress = 0.0

    def update_lava_animation(self, dt: float) -> float:
        """
        Update lava animation progress.

        Returns:
            Animation progress (0.0 to 1.0)
        """
        if not self.lava_active:
            return 0.0

        self.lava_animation_progress = min(
            1.0,
            self.lava_animation_progress + dt * self.lava_animation_speed
        )
        return self.lava_animation_progress

    def deactivate_lava(self):
        """Turn off lava between rounds."""
        self.lava_active = False
        self.lava_animation_progress = 0.0

    def get_platform_bounds(self) -> Tuple[float, float, float]:
        """Return (center_x, center_y, radius) of current platform."""
        if not self.safe_platform:
            center = self.get_center()
            return (center[0], center[1], 0)
        return (
            self.safe_platform.center[0],
            self.safe_platform.center[1],
            self.safe_platform.radius,
        )

    def spawn_obstacles(self, count: int = 4):
        """Spawn random obstacles that don't overlap with platform."""
        self.obstacles = []
        platform = self.safe_platform

        min_size = getattr(config, "LAVA_PLATFORM_OBSTACLE_MIN_SIZE", 30)
        max_size = getattr(config, "LAVA_PLATFORM_OBSTACLE_MAX_SIZE", 60)

        for _ in range(count):
            # Try up to 20 times to find valid position
            for attempt in range(20):
                width = random.randint(min_size, max_size)
                height = random.randint(min_size, max_size)
                x = random.uniform(self.left + 10, self.right - width - 10)
                y = random.uniform(self.top + 10, self.bottom - height - 10)

                # Check obstacle doesn't overlap platform (with margin)
                obstacle_center = (x + width / 2, y + height / 2)
                dist_to_platform = math.hypot(
                    obstacle_center[0] - platform.center[0],
                    obstacle_center[1] - platform.center[1]
                )

                # Ensure obstacle is far enough from platform
                min_dist = platform.radius + max(width, height) / 2 + 20
                if dist_to_platform > min_dist:
                    self.obstacles.append(Obstacle(x, y, width, height))
                    break

    def is_blocked_by_obstacle(self, x: float, y: float, radius: float) -> bool:
        """Check if position collides with any obstacle."""
        for obs in self.obstacles:
            if obs.contains_point(x, y, radius):
                return True
        return False

    def get_obstacle_push(self, x: float, y: float, radius: float) -> Tuple[float, float]:
        """Get push vector to move player out of obstacles."""
        for obs in self.obstacles:
            if obs.contains_point(x, y, radius):
                # Find closest edge and push player out
                cx = obs.x + obs.width / 2
                cy = obs.y + obs.height / 2
                dx = x - cx
                dy = y - cy

                # Push toward nearest edge
                if abs(dx) / obs.width > abs(dy) / obs.height:
                    # Push horizontally
                    if dx > 0:
                        return (obs.x + obs.width + radius + 1, y)
                    else:
                        return (obs.x - radius - 1, y)
                else:
                    # Push vertically
                    if dy > 0:
                        return (x, obs.y + obs.height + radius + 1)
                    else:
                        return (x, obs.y - radius - 1)
        return (x, y)
