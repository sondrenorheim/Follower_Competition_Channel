"""
Follower Entity for Snake Escape - Prey that flees from the snake.
"""

import pygame
import math
import random
import time
from typing import Tuple, Optional, List

import config


class SnakeEscapeFollower:
    """
    A follower in the Snake Escape game.

    Behavior:
    - Flees from the snake when it's nearby
    - Wanders randomly when snake is far
    - Can push other followers (toward the snake if desperate)
    - Gets eliminated when eaten by the snake
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize a follower.

        Args:
            follower_data: Dictionary with 'id', 'username', 'avatar', optionally 'color'
            position: (x, y) starting position
        """
        # Identity
        self.id = follower_data.get("id", random.randint(1, 999999))
        self.username = follower_data.get("username", f"Player{self.id}")
        self.avatar_image = follower_data.get("avatar")  # PIL Image or None
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        # Position and movement
        self.x, self.y = position
        self.vx = 0.0
        self.vy = 0.0
        self.radius = config.FOLLOWER_RADIUS

        # Push mechanics (from Battle Royale)
        self.push_vx = 0.0
        self.push_vy = 0.0
        self.last_bump_time = 0.0
        self.last_pushed_by: Optional['SnakeEscapeFollower'] = None

        # State
        self.alive = True
        self.spawn_time = time.time()
        self.elimination_time = 0.0
        self.alpha = 255  # For fade animation
        self.placement = None  # Final placement for scoring

        # AI behavior
        self.flee_distance = getattr(config, 'SNAKE_FLEE_DISTANCE', 150)  # Start fleeing when snake is this close
        self.panic_distance = getattr(config, 'SNAKE_PANIC_DISTANCE', 80)  # Panic mode when very close
        self.target_x = self.x
        self.target_y = self.y
        self.direction_change_interval = random.uniform(1.0, 3.0)
        self.last_direction_change = time.time()

        # Pushing behavior
        self.push_cooldown = config.BUMP_COOLDOWN
        self.push_aggression = random.uniform(0.3, 0.8)  # How likely to push others

        # Surface caching
        self.surface: Optional[pygame.Surface] = None
        self.surface_needs_update = True

    def update(self, dt: float, arena, snake, all_followers: list):
        """
        Update follower state.

        Args:
            dt: Delta time in seconds
            arena: The game arena
            snake: The snake entity
            all_followers: List of all followers
        """
        if not self.alive:
            self._update_fade(dt)
            return

        current_time = time.time()

        # Calculate distance to snake
        snake_dx = snake.x - self.x
        snake_dy = snake.y - self.y
        snake_distance = math.sqrt(snake_dx * snake_dx + snake_dy * snake_dy)

        # Determine behavior based on snake distance
        if snake_distance < self.panic_distance:
            # PANIC - run directly away from snake at max speed
            self._flee_from_snake(snake, dt, panic=True)
        elif snake_distance < self.flee_distance:
            # Flee - move away from snake
            self._flee_from_snake(snake, dt, panic=False)
        else:
            # Wander - random movement
            if current_time - self.last_direction_change > self.direction_change_interval:
                self._pick_new_target(arena)
                self.last_direction_change = current_time
            self._move_toward_target(dt)

        # Apply push velocity from collisions
        self.x += self.push_vx
        self.y += self.push_vy
        self.push_vx *= config.FRICTION
        self.push_vy *= config.FRICTION

        # Apply regular velocity
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vx *= config.FRICTION
        self.vy *= config.FRICTION

        # Keep inside arena (bounce off walls)
        self._handle_arena_bounds(arena)

    def _flee_from_snake(self, snake, dt: float, panic: bool = False):
        """
        Flee from the snake.

        Args:
            snake: The snake entity
            dt: Delta time
            panic: If True, move at maximum speed
        """
        # Direction away from snake
        dx = self.x - snake.x
        dy = self.y - snake.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.1:
            # Directly on snake, random direction
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
        else:
            dx /= distance
            dy /= distance

        # Speed boost when fleeing
        speed_multiplier = 1.5 if panic else 1.2
        flee_speed = config.BASE_SPEED * speed_multiplier

        # Add some randomness to prevent all followers moving identically
        if not panic:
            random_angle = random.uniform(-0.3, 0.3)
            cos_r = math.cos(random_angle)
            sin_r = math.sin(random_angle)
            new_dx = dx * cos_r - dy * sin_r
            new_dy = dx * sin_r + dy * cos_r
            dx, dy = new_dx, new_dy

        # Apply velocity
        target_vx = dx * flee_speed
        target_vy = dy * flee_speed

        # Smoother movement through interpolation
        smoothing = 0.3 if panic else 0.15
        self.vx += (target_vx - self.vx) * smoothing
        self.vy += (target_vy - self.vy) * smoothing

    def _pick_new_target(self, arena):
        """Pick a new random target position."""
        # Random position within arena
        self.target_x, self.target_y = arena.get_random_position(self.radius + 20)
        self.direction_change_interval = random.uniform(1.0, 3.0)

    def _move_toward_target(self, dt: float):
        """Move toward the target position."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 10:
            return  # Close enough

        # Normalize
        dx /= distance
        dy /= distance

        # Add randomness
        randomness = config.MOVEMENT_RANDOMNESS
        dx += random.uniform(-randomness, randomness)
        dy += random.uniform(-randomness, randomness)

        # Apply velocity
        target_vx = dx * config.BASE_SPEED
        target_vy = dy * config.BASE_SPEED

        smoothing = 0.15
        self.vx += (target_vx - self.vx) * smoothing
        self.vy += (target_vy - self.vy) * smoothing

    def _handle_arena_bounds(self, arena):
        """Keep follower inside arena and bounce off walls."""
        left, top, right, bottom = arena.get_bounds()

        # Bounce off walls
        if self.x - self.radius < left:
            self.x = left + self.radius
            self.vx = abs(self.vx) * 0.5
            self.push_vx = abs(self.push_vx) * 0.5
        elif self.x + self.radius > right:
            self.x = right - self.radius
            self.vx = -abs(self.vx) * 0.5
            self.push_vx = -abs(self.push_vx) * 0.5

        if self.y - self.radius < top:
            self.y = top + self.radius
            self.vy = abs(self.vy) * 0.5
            self.push_vy = abs(self.push_vy) * 0.5
        elif self.y + self.radius > bottom:
            self.y = bottom - self.radius
            self.vy = -abs(self.vy) * 0.5
            self.push_vy = -abs(self.push_vy) * 0.5

    def check_collision(self, other: 'SnakeEscapeFollower', current_time: float, snake=None) -> bool:
        """
        Check collision with another follower and separate them (no pushing).

        Args:
            other: Other follower to check
            current_time: Current game time
            snake: The snake (unused - pushing disabled)

        Returns:
            True if collision occurred
        """
        if not self.alive or not other.alive:
            return False

        # Calculate distance
        dx = other.x - self.x
        dy = other.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if overlapping
        min_distance = self.radius + other.radius
        if distance < min_distance and distance > 0:
            # Separate the followers - push them apart equally
            overlap = min_distance - distance

            # Normalize direction
            nx = dx / distance
            ny = dy / distance

            # Move each follower half the overlap distance
            separation = overlap / 2 + 0.5  # Small extra to prevent sticking

            self.x -= nx * separation
            self.y -= ny * separation
            other.x += nx * separation
            other.y += ny * separation

            return True

        return False

    def eliminate(self, placement: int = None, particle_system=None):
        """
        Eliminate this follower (eaten by snake).

        Args:
            placement: Final placement
            particle_system: Unused - no particle effects in snake escape
        """
        if not self.alive:
            return

        self.alive = False
        self.elimination_time = time.time()
        self.surface_needs_update = True

        if placement is not None:
            self.placement = placement

        # No particle effect - follower just gets eaten

    def _update_fade(self, dt: float):
        """Update fade-out animation."""
        if self.elimination_time == 0:
            return

        elapsed = time.time() - self.elimination_time
        if elapsed >= config.FADE_DURATION:
            self.alpha = 0
        else:
            progress = elapsed / config.FADE_DURATION
            self.alpha = int(255 * (1 - progress))
            self.surface_needs_update = True

    def is_fading(self) -> bool:
        """Check if follower is in fade-out animation."""
        if self.elimination_time == 0:
            return False
        return time.time() - self.elimination_time < config.FADE_DURATION

    def get_survival_time(self) -> float:
        """Get survival time in seconds."""
        if self.elimination_time > 0:
            return self.elimination_time - self.spawn_time
        return time.time() - self.spawn_time

    def get_position(self) -> Tuple[float, float]:
        """Get current position."""
        return (self.x, self.y)

    def distance_to(self, other) -> float:
        """Calculate distance to another entity."""
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def __repr__(self):
        status = "ALIVE" if self.alive else "EATEN"
        return f"SnakeEscapeFollower({self.username}, {status}, pos=({self.x:.1f}, {self.y:.1f}))"
