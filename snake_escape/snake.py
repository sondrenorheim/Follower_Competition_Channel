"""
Snake Entity - The predator that hunts followers in Snake Escape.
"""

import pygame
import math
import random
import time
from typing import Tuple, List, Optional

import config


class SnakeSegment:
    """A single segment of the snake's body."""

    def __init__(self, x: float, y: float, radius: float = 12):
        self.x = x
        self.y = y
        self.radius = radius


class Snake:
    """
    The snake predator that hunts followers.

    Features:
    - Head + body segments (classic snake visual)
    - Only eats with its head
    - Seeks out nearest follower
    - Speed increases as followers are eliminated
    """

    # Snake colors
    HEAD_COLOR = (50, 150, 50)       # Dark green head
    BODY_COLOR = (80, 180, 80)       # Lighter green body
    EYE_COLOR = (255, 255, 255)      # White eyes
    PUPIL_COLOR = (0, 0, 0)          # Black pupils
    TONGUE_COLOR = (255, 50, 50)     # Red tongue

    def __init__(self, position: Tuple[float, float], initial_speed: float = None):
        """
        Initialize the snake.

        Args:
            position: (x, y) starting position for the head
            initial_speed: Starting speed (default: config.SNAKE_INITIAL_SPEED)
        """
        # Head position
        self.x, self.y = position
        self.head_radius = 18  # Slightly larger than followers

        # Movement
        if initial_speed is None:
            initial_speed = getattr(config, 'SNAKE_INITIAL_SPEED', config.BASE_SPEED * 1.2)
        self.base_speed = initial_speed
        self.current_speed = initial_speed

        # Start with random velocity so snake moves immediately
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * initial_speed
        self.vy = math.sin(angle) * initial_speed

        # Targeting
        self.target = None
        self.target_change_interval = 0.5  # How often to recalculate target
        self.last_target_change = 0.0

        # Body segments
        self.segments: List[SnakeSegment] = []
        self.segment_spacing = 14  # Distance between segments
        self.initial_segment_count = 8
        self._init_segments()

        # Eating
        self.eat_radius = self.head_radius + 5  # Radius for eating followers
        self.kills = 0
        self.can_eat = False  # Set to True when game starts (after countdown)
        self.hunting = False  # Set to True when game starts - before this, snake wanders randomly

        # Animation
        self.tongue_out = False
        self.tongue_timer = 0.0
        self.tongue_interval = 2.0  # Seconds between tongue flicks

        # Speed scaling
        self.speed_multiplier = 1.0
        self.max_speed_multiplier = getattr(config, 'SNAKE_MAX_SPEED_MULTIPLIER', 2.0)

    def _init_segments(self):
        """Initialize the snake's body segments behind the head."""
        self.segments = []
        for i in range(self.initial_segment_count):
            # Place segments behind the head
            segment_x = self.x - (i + 1) * self.segment_spacing
            segment_y = self.y
            # Segments get slightly smaller toward the tail
            radius = max(8, self.head_radius - 2 - i * 0.5)
            self.segments.append(SnakeSegment(segment_x, segment_y, radius))

    def update(self, dt: float, arena, followers: list):
        """
        Update the snake's state.

        Args:
            dt: Delta time in seconds
            arena: The game arena
            followers: List of all followers (for targeting)
        """
        current_time = time.time()

        # Update tongue animation
        self.tongue_timer += dt
        if self.tongue_timer >= self.tongue_interval:
            self.tongue_out = not self.tongue_out
            self.tongue_timer = 0.0
            if self.tongue_out:
                self.tongue_interval = 0.2  # Tongue stays out briefly
            else:
                self.tongue_interval = random.uniform(1.5, 3.0)  # Random delay before next flick

        # Only hunt if hunting mode is enabled (after countdown)
        if self.hunting:
            # Choose target - periodically, when no target, or 1% random chance to switch
            should_retarget = (
                self.target is None or
                current_time - self.last_target_change > self.target_change_interval or
                random.random() < 0.01  # 1% chance per frame to change target
            )

            if should_retarget:
                self._choose_target(followers)
                self.last_target_change = current_time

            # Move toward target
            if self.target and self.target.alive:
                self._move_toward_target(dt)
            else:
                # No target or target dead, wander randomly
                self._choose_target(followers)  # Try to find a new target
                if self.target and self.target.alive:
                    self._move_toward_target(dt)
                else:
                    self._random_movement(dt)
        else:
            # Before game starts, wander randomly
            self._random_movement(dt)

        # Apply velocity
        new_x = self.x + self.vx * dt * 60
        new_y = self.y + self.vy * dt * 60

        # Bounce off arena walls
        bounds = arena.get_bounds()
        left, top, right, bottom = bounds

        # Check horizontal bounds
        if new_x - self.head_radius < left:
            new_x = left + self.head_radius
            self.vx = abs(self.vx)  # Bounce right
        elif new_x + self.head_radius > right:
            new_x = right - self.head_radius
            self.vx = -abs(self.vx)  # Bounce left

        # Check vertical bounds
        if new_y - self.head_radius < top:
            new_y = top + self.head_radius
            self.vy = abs(self.vy)  # Bounce down
        elif new_y + self.head_radius > bottom:
            new_y = bottom - self.head_radius
            self.vy = -abs(self.vy)  # Bounce up

        self.x = new_x
        self.y = new_y

        # Update body segments to follow the head
        self._update_segments()

    def _choose_target(self, followers: list):
        """Choose the nearest alive follower as target."""
        alive_followers = [f for f in followers if f.alive]
        if not alive_followers:
            self.target = None
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

        self.target = nearest

    def _move_toward_target(self, dt: float):
        """Move toward the current target with continuous smooth movement."""
        if not self.target:
            return

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1:
            return

        # Normalize direction
        dx /= distance
        dy /= distance

        # Apply speed - continuous movement without stopping
        speed = self.current_speed * self.speed_multiplier

        # Set velocity directly for continuous movement
        self.vx = dx * speed
        self.vy = dy * speed

    def _random_movement(self, dt: float):
        """Apply random movement when no target is available - continuous wandering."""
        speed = self.current_speed * 0.7  # Wander at 70% speed

        # Change direction occasionally (5% chance per frame)
        if random.random() < 0.05:
            # Add some randomness to current direction rather than completely random
            current_angle = math.atan2(self.vy, self.vx)
            angle_change = random.uniform(-0.5, 0.5)  # Turn up to ~30 degrees
            new_angle = current_angle + angle_change
            self.vx = math.cos(new_angle) * speed
            self.vy = math.sin(new_angle) * speed

        # Ensure we're always moving at the target speed
        current_speed = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        if current_speed < speed * 0.5:
            # If too slow, pick a random direction
            angle = random.uniform(0, 2 * math.pi)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed

    def _update_segments(self):
        """Update body segments to follow the head."""
        if not self.segments:
            return

        # First segment follows the head
        prev_x, prev_y = self.x, self.y

        for segment in self.segments:
            # Calculate direction from segment to previous position
            dx = prev_x - segment.x
            dy = prev_y - segment.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > self.segment_spacing:
                # Move segment toward previous position
                ratio = (distance - self.segment_spacing) / distance
                segment.x += dx * ratio
                segment.y += dy * ratio

            # This segment becomes the reference for the next
            prev_x, prev_y = segment.x, segment.y

    def check_eat_follower(self, follower) -> bool:
        """
        Check if the snake's head can eat a follower.

        Args:
            follower: The follower to check

        Returns:
            True if the follower was eaten
        """
        # Can't eat if eating is disabled (during countdown)
        if not self.can_eat:
            return False

        if not follower.alive:
            return False

        # Calculate distance from snake head to follower
        dx = follower.x - self.x
        dy = follower.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if follower is within eating radius of HEAD only
        if distance < self.eat_radius + follower.radius:
            self.kills += 1
            return True

        return False

    def update_speed_scaling(self, alive_count: int, total_count: int):
        """
        Update the snake's speed based on how many followers remain.

        Args:
            alive_count: Number of alive followers
            total_count: Total number of followers at game start
        """
        if total_count <= 0:
            return

        # Calculate progress (0 = all alive, 1 = none alive)
        progress = 1.0 - (alive_count / total_count)

        # Scale speed: starts at 1.0x, increases toward max_speed_multiplier
        self.speed_multiplier = 1.0 + progress * (self.max_speed_multiplier - 1.0)

    def get_head_position(self) -> Tuple[float, float]:
        """Get the snake's head position."""
        return (self.x, self.y)

    def get_direction(self) -> Tuple[float, float]:
        """Get the snake's current direction of movement (normalized)."""
        speed = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        if speed < 0.1:
            return (1, 0)  # Default facing right
        return (self.vx / speed, self.vy / speed)

    def draw(self, screen: pygame.Surface):
        """
        Draw the snake on the screen.

        Args:
            screen: Pygame surface to draw on
        """
        # Draw body segments (from tail to head so head is on top)
        for i, segment in enumerate(reversed(self.segments)):
            # Gradient from lighter (tail) to darker (near head)
            factor = i / max(1, len(self.segments))
            r = int(self.BODY_COLOR[0] + (self.HEAD_COLOR[0] - self.BODY_COLOR[0]) * factor)
            g = int(self.BODY_COLOR[1] + (self.HEAD_COLOR[1] - self.BODY_COLOR[1]) * factor)
            b = int(self.BODY_COLOR[2] + (self.HEAD_COLOR[2] - self.BODY_COLOR[2]) * factor)
            color = (r, g, b)

            pygame.draw.circle(screen, color,
                             (int(segment.x), int(segment.y)),
                             int(segment.radius))
            # Dark border
            pygame.draw.circle(screen, (30, 80, 30),
                             (int(segment.x), int(segment.y)),
                             int(segment.radius), 2)

        # Draw head
        pygame.draw.circle(screen, self.HEAD_COLOR,
                          (int(self.x), int(self.y)),
                          self.head_radius)
        # Head border
        pygame.draw.circle(screen, (30, 80, 30),
                          (int(self.x), int(self.y)),
                          self.head_radius, 2)

        # Draw eyes
        direction = self.get_direction()
        eye_offset = 6
        eye_radius = 5
        pupil_radius = 2

        # Calculate eye positions (perpendicular to direction)
        perp_x = -direction[1]
        perp_y = direction[0]

        for side in [-1, 1]:
            eye_x = self.x + direction[0] * 5 + perp_x * eye_offset * side
            eye_y = self.y + direction[1] * 5 + perp_y * eye_offset * side

            # White of eye
            pygame.draw.circle(screen, self.EYE_COLOR,
                             (int(eye_x), int(eye_y)), eye_radius)

            # Pupil (slightly toward target/direction)
            pupil_x = eye_x + direction[0] * 2
            pupil_y = eye_y + direction[1] * 2
            pygame.draw.circle(screen, self.PUPIL_COLOR,
                             (int(pupil_x), int(pupil_y)), pupil_radius)

        # Draw tongue if out
        if self.tongue_out:
            tongue_start_x = self.x + direction[0] * self.head_radius
            tongue_start_y = self.y + direction[1] * self.head_radius
            tongue_length = 15

            # Forked tongue
            for fork in [-0.3, 0.3]:
                fork_dir_x = direction[0] * math.cos(fork) - direction[1] * math.sin(fork)
                fork_dir_y = direction[0] * math.sin(fork) + direction[1] * math.cos(fork)

                tongue_end_x = tongue_start_x + fork_dir_x * tongue_length
                tongue_end_y = tongue_start_y + fork_dir_y * tongue_length

                pygame.draw.line(screen, self.TONGUE_COLOR,
                               (int(tongue_start_x), int(tongue_start_y)),
                               (int(tongue_end_x), int(tongue_end_y)), 2)
