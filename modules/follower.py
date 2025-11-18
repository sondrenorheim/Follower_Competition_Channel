"""
Follower Character Module
Represents individual followers in the battle royale
"""

import pygame
import math
import random
import time
from typing import Optional, Tuple
from PIL import Image
import config


class Follower:
    """
    Represents a single follower character in the battle royale
    Handles position, movement, collision, and elimination state
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize a follower character

        Args:
            follower_data: Dictionary containing 'id', 'username', 'avatar', and optionally 'color'
            position: (x, y) starting position
        """
        self.id = follower_data["id"]
        self.username = follower_data["username"]
        self.avatar_image = follower_data.get("avatar")  # PIL Image or None
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        # Position and movement
        self.x, self.y = position
        self.vx = 0.0  # Velocity X
        self.vy = 0.0  # Velocity Y
        self.target_x = self.x
        self.target_y = self.y

        # Combat and collision
        self.target_follower: Optional['Follower'] = None
        self.last_bump_time = 0.0  # Timestamp of last collision
        self.push_vx = 0.0  # Temporary push velocity
        self.push_vy = 0.0

        # State
        self.alive = True
        self.elimination_time = 0.0
        self.alpha = 255  # For fade out animation

        # Cached surface (for rendering optimization)
        self.surface: Optional[pygame.Surface] = None
        self.surface_needs_update = True

    def update(self, dt: float, arena_center: Tuple[float, float], safe_radius: float, all_followers: list):
        """
        Update follower state each frame

        Args:
            dt: Delta time in seconds
            arena_center: (x, y) center of the arena
            safe_radius: Current safe zone radius
            all_followers: List of all followers for targeting
        """
        if not self.alive:
            # Handle fade out animation
            if time.time() - self.elimination_time < config.FADE_DURATION:
                # Fade out over FADE_DURATION seconds
                progress = (time.time() - self.elimination_time) / config.FADE_DURATION
                self.alpha = int(255 * (1 - progress))
                self.surface_needs_update = True
            return

        # Choose target if we don't have one or target is dead
        if self.target_follower is None or not self.target_follower.alive:
            self._choose_target(all_followers)

        # Move toward target (trying to push them toward edge)
        if self.target_follower and self.target_follower.alive:
            self._move_toward_target(arena_center, dt)
        else:
            # Random movement if no target
            self._random_movement(dt)

        # Apply push velocity from collisions
        self.x += self.push_vx
        self.y += self.push_vy
        self.push_vx *= config.FRICTION
        self.push_vy *= config.FRICTION

        # Apply regular velocity
        self.x += self.vx * dt * 60  # Scale by 60 for consistent speed across framerates
        self.y += self.vy * dt * 60
        self.vx *= config.FRICTION
        self.vy *= config.FRICTION

        # Keep within arena bounds (can't go outside the main arena)
        max_distance = config.ARENA_INITIAL_RADIUS - config.FOLLOWER_RADIUS
        dx = self.x - arena_center[0]
        dy = self.y - arena_center[1]
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > max_distance:
            # Push back inside
            angle = math.atan2(dy, dx)
            self.x = arena_center[0] + math.cos(angle) * max_distance
            self.y = arena_center[1] + math.sin(angle) * max_distance
            self.vx *= -0.5
            self.vy *= -0.5

    def _choose_target(self, all_followers: list):
        """
        Choose nearest alive opponent to target

        Args:
            all_followers: List of all followers
        """
        alive_followers = [f for f in all_followers if f.alive and f != self]
        if not alive_followers:
            self.target_follower = None
            return

        # Find nearest follower
        min_distance = float('inf')
        nearest = None

        for follower in alive_followers:
            dx = follower.x - self.x
            dy = follower.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < min_distance:
                min_distance = distance
                nearest = follower

        self.target_follower = nearest

    def _move_toward_target(self, arena_center: Tuple[float, float], dt: float):
        """
        Move toward target with strategy to push them toward edge
        Adds randomness for natural movement

        Args:
            arena_center: Center of the arena
            dt: Delta time
        """
        if not self.target_follower:
            return

        # Calculate direction to target
        dx = self.target_follower.x - self.x
        dy = self.target_follower.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.1:
            return

        # Normalize direction
        dx /= distance
        dy /= distance

        # Add randomness for natural movement
        random_angle = (random.random() - 0.5) * config.MOVEMENT_RANDOMNESS * math.pi
        cos_r = math.cos(random_angle)
        sin_r = math.sin(random_angle)
        new_dx = dx * cos_r - dy * sin_r
        new_dy = dx * sin_r + dy * cos_r

        # Apply movement
        self.vx = new_dx * config.BASE_SPEED
        self.vy = new_dy * config.BASE_SPEED

    def _random_movement(self, dt: float):
        """
        Apply random movement when no target is available

        Args:
            dt: Delta time
        """
        # Occasionally change direction
        if random.random() < 0.02:  # 2% chance per frame
            angle = random.random() * 2 * math.pi
            self.vx = math.cos(angle) * config.BASE_SPEED
            self.vy = math.sin(angle) * config.BASE_SPEED

    def check_safe_zone(self, arena_center: Tuple[float, float], safe_radius: float) -> bool:
        """
        Check if follower is inside safe zone
        Eliminate if completely outside

        Args:
            arena_center: Center of the arena
            safe_radius: Current safe zone radius

        Returns:
            True if alive, False if eliminated
        """
        if not self.alive:
            return False

        # Calculate distance from center
        dx = self.x - arena_center[0]
        dy = self.y - arena_center[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if completely outside safe zone (center is outside)
        if distance > safe_radius:
            self.eliminate()
            return False

        return True

    def check_collision(self, other: 'Follower', current_time: float) -> bool:
        """
        Check collision with another follower and apply push force

        Args:
            other: Other follower to check collision with
            current_time: Current game time

        Returns:
            True if collision occurred
        """
        if not self.alive or not other.alive:
            return False

        # Check if on cooldown
        if current_time - self.last_bump_time < config.BUMP_COOLDOWN:
            return False

        # Calculate distance
        dx = other.x - self.x
        dy = other.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if colliding
        if distance < config.COLLISION_DISTANCE and distance > 0:
            # Calculate push direction (away from each other)
            push_dx = dx / distance
            push_dy = dy / distance

            # Check if moving toward target (increases push force)
            moving_toward = (self.vx * push_dx + self.vy * push_dy) > 0
            force_multiplier = 1.5 if moving_toward else 1.0

            # Apply push force to other follower
            push_force = config.PUSH_FORCE * force_multiplier
            other.push_vx += push_dx * push_force
            other.push_vy += push_dy * push_force

            # Apply反作用力 to self (Newton's third law)
            self.push_vx -= push_dx * push_force * 0.5
            self.push_vy -= push_dy * push_force * 0.5

            # Update cooldown
            self.last_bump_time = current_time
            other.last_bump_time = current_time

            return True

        return False

    def eliminate(self):
        """
        Eliminate this follower from the game
        Starts fade-out animation
        """
        if self.alive:
            self.alive = False
            self.elimination_time = time.time()
            self.surface_needs_update = True

    def get_position(self) -> Tuple[float, float]:
        """
        Get current position

        Returns:
            (x, y) position tuple
        """
        return (self.x, self.y)

    def is_fading(self) -> bool:
        """
        Check if follower is currently in fade-out animation

        Returns:
            True if fading, False otherwise
        """
        return not self.alive and (time.time() - self.elimination_time < config.FADE_DURATION)

    def __repr__(self):
        status = "ALIVE" if self.alive else "ELIMINATED"
        return f"Follower({self.username}, {status}, pos=({self.x:.1f}, {self.y:.1f}))"
