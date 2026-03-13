"""
Entity Template - Blueprint for player/follower entities
Copy this file to your new game folder and customize it.

This template provides:
- Standard follower data (username, avatar, color)
- Position, velocity, and movement
- Alive/eliminated state tracking
- Placement for scoring
- Fade-out animation on elimination
- Profile picture support

Usage:
1. Copy this file to your_game/player.py
2. Rename the class to match your game (e.g., YourPlayer)
3. Add game-specific attributes and methods
4. Implement update() for your game's movement/behavior
"""

import pygame
import random
import time
from typing import Tuple, Optional, Dict, Any

import config
from .avatar_initials import draw_avatar_initials


class EntityTemplate:
    """
    Template for game entities (players/followers).

    Provides:
    - Follower identity (username, avatar, color)
    - Position and movement
    - Alive/eliminated state
    - Fade-out animation
    - Placement tracking for scoring

    Override methods to add game-specific behavior.
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize the entity.

        Args:
            follower_data: Dictionary containing:
                - 'id': Unique identifier
                - 'username': Display name
                - 'avatar': Avatar data (optional)
                - 'color': RGB tuple (optional, random if not provided)
                - 'avatar_image': PIL Image (optional, for profile pictures)
            position: (x, y) starting position
        """
        # Identity
        self.id = follower_data.get('id', random.randint(1, 999999))
        self.username = follower_data.get('username', f'Player{self.id}')

        # Avatar/appearance
        self.color = follower_data.get('color', self._random_color())
        self.avatar_image = follower_data.get('avatar_image', None)  # PIL Image

        # Position and movement
        self.x, self.y = position
        self.vx = 0.0  # Velocity X
        self.vy = 0.0  # Velocity Y
        self.radius = config.FOLLOWER_RADIUS

        # State
        self.alive = True
        self.alpha = 255  # For fade effects
        self.elimination_time = None
        self.placement = None  # Final placement for scoring

        # Timing
        self.spawn_time = time.time()
        self.survival_time = 0.0

        # Surface caching
        self.surface_needs_update = True
        self._cached_surface = None

        # Game-specific initialization
        self._init_entity(follower_data)

    def _init_entity(self, follower_data: dict):
        """
        Initialize game-specific attributes.
        Override to add custom stats, abilities, etc.

        Args:
            follower_data: Original follower data dictionary
        """
        pass

    def _random_color(self) -> Tuple[int, int, int]:
        """Generate a random color from the config palette."""
        return random.choice(config.RANDOM_COLORS)

    # =============================================================================
    # POSITION AND MOVEMENT
    # =============================================================================

    def get_position(self) -> Tuple[float, float]:
        """Get current position."""
        return (self.x, self.y)

    def set_position(self, x: float, y: float):
        """Set position directly."""
        self.x = x
        self.y = y

    def move(self, dx: float, dy: float):
        """Move by offset."""
        self.x += dx
        self.y += dy

    def apply_velocity(self, dt: float):
        """Apply current velocity to position."""
        self.x += self.vx * dt
        self.y += self.vy * dt

    def apply_friction(self, friction: float = None):
        """
        Apply friction to velocity.

        Args:
            friction: Friction multiplier (default: config.FRICTION)
        """
        if friction is None:
            friction = config.FRICTION

        self.vx *= friction
        self.vy *= friction

    def get_speed(self) -> float:
        """Get current speed (magnitude of velocity)."""
        import math
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    def normalize_velocity(self, max_speed: float):
        """Cap velocity to a maximum speed."""
        speed = self.get_speed()
        if speed > max_speed:
            scale = max_speed / speed
            self.vx *= scale
            self.vy *= scale

    def distance_to(self, other) -> float:
        """Calculate distance to another entity."""
        import math
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def direction_to(self, other) -> Tuple[float, float]:
        """Get normalized direction vector to another entity."""
        import math
        dx = other.x - self.x
        dy = other.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            return (0, 0)

        return (dx / dist, dy / dist)

    # =============================================================================
    # COLLISION
    # =============================================================================

    def collides_with(self, other) -> bool:
        """Check if this entity collides with another."""
        dist = self.distance_to(other)
        return dist < (self.radius + other.radius)

    def get_collision_overlap(self, other) -> float:
        """Get overlap distance with another entity (negative if not colliding)."""
        dist = self.distance_to(other)
        return (self.radius + other.radius) - dist

    def push_apart(self, other, force: float = None):
        """
        Push this entity away from another (mutual separation).

        Args:
            other: Other entity
            force: Push force (default: config.PUSH_FORCE)
        """
        if force is None:
            force = config.PUSH_FORCE

        import math

        dx = self.x - other.x
        dy = self.y - other.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            # Same position, push in random direction
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
            dist = 1

        # Normalize and apply force
        nx = dx / dist
        ny = dy / dist

        self.vx += nx * force
        self.vy += ny * force
        other.vx -= nx * force
        other.vy -= ny * force

    # =============================================================================
    # ELIMINATION AND STATE
    # =============================================================================

    def eliminate(self, placement: Optional[int] = None):
        """
        Mark entity as eliminated.

        Args:
            placement: Final placement (optional)
        """
        if not self.alive:
            return

        self.alive = False
        self.elimination_time = time.time()
        self.survival_time = self.elimination_time - self.spawn_time

        if placement is not None:
            self.placement = placement

    def is_fading(self) -> bool:
        """Check if entity is in fade-out animation."""
        if self.elimination_time is None:
            return False

        elapsed = time.time() - self.elimination_time
        return elapsed < config.FADE_DURATION

    def update_fade(self):
        """Update fade-out animation."""
        if self.elimination_time is None:
            return

        elapsed = time.time() - self.elimination_time

        if elapsed >= config.FADE_DURATION:
            self.alpha = 0
        else:
            progress = elapsed / config.FADE_DURATION
            self.alpha = int(255 * (1 - progress))
            self.surface_needs_update = True

    def get_survival_time(self) -> float:
        """Get total survival time in seconds."""
        if self.survival_time > 0:
            return self.survival_time
        return time.time() - self.spawn_time

    # =============================================================================
    # UPDATE - Override this method
    # =============================================================================

    def update(self, dt: float, *args, **kwargs):
        """
        Update entity state.
        Override this method to implement game-specific behavior.

        Args:
            dt: Delta time in seconds
            *args, **kwargs: Game-specific parameters (arena, other entities, etc.)

        Example:
            def update(self, dt, arena, all_players):
                if not self.alive:
                    self.update_fade()
                    return

                # Movement logic
                self.apply_velocity(dt)
                self.apply_friction()

                # Keep inside arena
                self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

                # Check for elimination
                if not arena.is_inside(self.x, self.y, self.radius):
                    self.eliminate()
        """
        if not self.alive:
            self.update_fade()
            return

        # Default: apply velocity and friction
        self.apply_velocity(dt)
        self.apply_friction()

    # =============================================================================
    # RENDERING HELPERS
    # =============================================================================

    def get_surface(self, size: Optional[int] = None) -> pygame.Surface:
        """
        Get the entity's rendered surface.

        Args:
            size: Override size (default: radius * 2)

        Returns:
            Pygame surface
        """
        if size is None:
            size = int(self.radius * 2)

        if self._cached_surface is None or self.surface_needs_update:
            self._cached_surface = self._create_surface(size)
            self.surface_needs_update = False

        return self._cached_surface

    def _create_surface(self, size: int) -> pygame.Surface:
        """
        Create the entity's visual surface.
        Override to customize appearance.

        Args:
            size: Surface size in pixels

        Returns:
            Pygame surface
        """
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        if self.avatar_image:
            # Use profile picture
            try:
                # Validate image dimensions before resizing
                if self.avatar_image.width == 0 or self.avatar_image.height == 0:
                    raise ValueError("Avatar image has invalid dimensions")

                pil_resized = self.avatar_image.resize((size, size))
                mode = pil_resized.mode
                data = pil_resized.tobytes()
                img_surface = pygame.image.fromstring(data, (size, size), mode)

                # Create circular mask
                mask = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(mask, (255, 255, 255, 255),
                                 (size // 2, size // 2), size // 2)

                # Apply mask
                img_surface = img_surface.convert_alpha()
                img_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(img_surface, (0, 0))
            except:
                # Fallback to colored circle
                pygame.draw.circle(surface, self.color,
                                 (size // 2, size // 2), size // 2)
                draw_avatar_initials(
                    surface,
                    self.username,
                    center=(size // 2, size // 2),
                    diameter=size,
                )
        else:
            # Colored circle
            pygame.draw.circle(surface, self.color,
                             (size // 2, size // 2), size // 2)
            draw_avatar_initials(
                surface,
                self.username,
                center=(size // 2, size // 2),
                diameter=size,
            )

        # White border
        pygame.draw.circle(surface, (255, 255, 255),
                          (size // 2, size // 2), size // 2,
                          config.FOLLOWER_BORDER_WIDTH)

        return surface

    def draw(self, screen: pygame.Surface, offset: Tuple[float, float] = (0, 0)):
        """
        Draw the entity on screen.

        Args:
            screen: Pygame surface to draw on
            offset: Camera offset (for scrolling games)
        """
        if not self.alive and self.alpha <= 0:
            return

        surface = self.get_surface()

        # Apply fade
        if self.alpha < 255:
            surface = surface.copy()
            surface.set_alpha(self.alpha)

        # Calculate screen position
        screen_x = int(self.x - offset[0])
        screen_y = int(self.y - offset[1])

        # Draw centered on position
        rect = surface.get_rect(center=(screen_x, screen_y))
        screen.blit(surface, rect)

    # =============================================================================
    # UTILITY
    # =============================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity state to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'alive': self.alive,
            'placement': self.placement,
            'survival_time': self.get_survival_time()
        }

    def __repr__(self) -> str:
        status = "ALIVE" if self.alive else "ELIMINATED"
        return f"{self.__class__.__name__}({self.username}, {status}, pos=({self.x:.1f}, {self.y:.1f}))"


# =============================================================================
# CONVENIENCE SUBCLASS EXAMPLE
# =============================================================================

class MovingEntity(EntityTemplate):
    """
    Entity with AI-driven random movement.
    Use this as a base for entities that move on their own.
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        super().__init__(follower_data, position)

        # Movement parameters
        self.target_x = self.x
        self.target_y = self.y
        self.move_speed = config.BASE_SPEED
        self.direction_change_interval = random.uniform(1.0, 3.0)
        self.last_direction_change = time.time()

    def update(self, dt: float, arena=None, all_entities=None):
        """Update with random movement."""
        if not self.alive:
            self.update_fade()
            return

        current_time = time.time()

        # Change direction periodically
        if current_time - self.last_direction_change > self.direction_change_interval:
            self._pick_new_target(arena)
            self.last_direction_change = current_time

        # Move toward target
        self._move_toward_target(dt)

        # Apply physics
        self.apply_velocity(dt)
        self.apply_friction()

        # Keep inside arena
        if arena:
            self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

    def _pick_new_target(self, arena=None):
        """Pick a new random target position."""
        import math

        if arena:
            self.target_x, self.target_y = arena.get_random_position(self.radius + 20)
        else:
            # Random movement in general area
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(50, 150)
            self.target_x = self.x + math.cos(angle) * distance
            self.target_y = self.y + math.sin(angle) * distance

        self.direction_change_interval = random.uniform(1.0, 3.0)

    def _move_toward_target(self, dt: float):
        """Apply force toward target."""
        import math

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 10:
            return  # Close enough

        # Normalize and apply speed
        nx = dx / dist
        ny = dy / dist

        # Add some randomness
        randomness = config.MOVEMENT_RANDOMNESS
        nx += random.uniform(-randomness, randomness)
        ny += random.uniform(-randomness, randomness)

        self.vx += nx * self.move_speed * dt * 60
        self.vy += ny * self.move_speed * dt * 60
