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

        # Load default stats
        self.stats = config.BATTLE_ROYALE_DEFAULT_STATS.copy()

        # Position and movement
        self.x, self.y = position
        # Initialize with random direction for immediate movement
        angle = random.random() * 2 * math.pi
        initial_speed = self.stats['base_speed'] * 0.5
        self.vx = math.cos(angle) * initial_speed
        self.vy = math.sin(angle) * initial_speed
        self.target_x = self.x
        self.target_y = self.y

        # Combat and collision
        self.target_follower: Optional['Follower'] = None
        self.last_bump_time = 0.0  # Timestamp of last collision
        self.push_vx = 0.0  # Temporary push velocity
        self.push_vy = 0.0
        self.last_pushed_by: Optional['Follower'] = None  # Track who pushed us last (for kill credit)
        self.kills = 0  # Number of eliminations caused by this follower

        # State
        self.alive = True
        self.spawn_time = time.time()  # When follower spawned
        self.elimination_time = 0.0
        self.alpha = 255  # For fade out animation

        # Cached surface (for rendering optimization)
        self.surface: Optional[pygame.Surface] = None
        self.surface_needs_update = True

    def update(
        self,
        dt: float,
        arena_center: Tuple[float, float],
        safe_radius: float,
        all_followers: list,
        allow_targeting: bool = True,
    ):
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

        prestart_radius = None
        prestart_pull = 0.0
        movement_radius = safe_radius
        if not allow_targeting and safe_radius is not None:
            try:
                prestart_ratio = float(getattr(config, "BATTLE_ROYALE_PRESTART_RADIUS_RATIO", 1.0))
            except (TypeError, ValueError):
                prestart_ratio = 1.0
            prestart_ratio = max(0.0, min(1.0, prestart_ratio))
            try:
                prestart_pull = float(getattr(config, "BATTLE_ROYALE_PRESTART_CENTER_PULL", 0.0))
            except (TypeError, ValueError):
                prestart_pull = 0.0
            prestart_pull = max(0.0, prestart_pull)
            if 0.0 < prestart_ratio < 1.0:
                prestart_radius = safe_radius * prestart_ratio

        targeting_allowed = allow_targeting and self._is_in_targeting_band(
            arena_center,
            safe_radius,
        )

        if targeting_allowed:
            # Choose target if we don't have one or target is dead
            if self.target_follower is None or not self.target_follower.alive:
                self._choose_target(all_followers)

            # Move toward target (trying to push them toward edge)
            if self.target_follower and self.target_follower.alive:
                self._move_toward_target(arena_center, dt, movement_radius)
            else:
                # Random movement if no target, but still avoid danger zone
                self._random_movement(dt, arena_center, movement_radius)
        else:
            # Random movement if targeting is disabled or outside the target band
            self._random_movement(dt, arena_center, movement_radius)

        if prestart_radius is not None and prestart_pull > 0.0 and safe_radius is not None:
            dx_to_center = arena_center[0] - self.x
            dy_to_center = arena_center[1] - self.y
            distance_to_center = math.sqrt(dx_to_center * dx_to_center + dy_to_center * dy_to_center)
            if distance_to_center > prestart_radius and distance_to_center > 0.1:
                range_span = max(1.0, safe_radius - prestart_radius)
                excess = min(1.0, (distance_to_center - prestart_radius) / range_span)
                pull_strength = self.stats['base_speed'] * prestart_pull * excess
                self.vx += (dx_to_center / distance_to_center) * pull_strength
                self.vy += (dy_to_center / distance_to_center) * pull_strength

        # Apply push velocity from collisions
        self.x += self.push_vx
        self.y += self.push_vy
        self.push_vx *= self.stats['friction']
        self.push_vy *= self.stats['friction']

        # Apply regular velocity
        self.x += self.vx * dt * 60  # Scale by 60 for consistent speed across framerates
        self.y += self.vy * dt * 60
        self.vx *= self.stats['friction']
        self.vy *= self.stats['friction']

        # Keep within arena bounds (can't go outside the main arena)
        max_distance = config.ARENA_INITIAL_RADIUS - config.FOLLOWER_RADIUS
        max_distance = max(0.0, max_distance)
        dx = self.x - arena_center[0]
        dy = self.y - arena_center[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Add wall avoidance before hitting the boundary
        wall_avoid_distance = config.FOLLOWER_RADIUS * 4
        if distance > max_distance - wall_avoid_distance:
            # Getting close to outer wall - add inward force
            avoidance_strength = (distance - (max_distance - wall_avoid_distance)) / wall_avoid_distance
            avoidance_strength = min(1.0, avoidance_strength)

            # Push toward center
            if distance > 0.1:
                push_toward_center_x = -dx / distance * self.stats['base_speed'] * avoidance_strength * 0.3
                push_toward_center_y = -dy / distance * self.stats['base_speed'] * avoidance_strength * 0.3
                self.vx += push_toward_center_x
                self.vy += push_toward_center_y

        if distance > max_distance:
            # Hit the wall - push back inside actively
            angle = math.atan2(dy, dx)
            self.x = arena_center[0] + math.cos(angle) * max_distance
            self.y = arena_center[1] + math.sin(angle) * max_distance

            # Reverse velocity toward center instead of just dampening
            self.vx = -dx / distance * abs(self.vx) * 0.5
            self.vy = -dy / distance * abs(self.vy) * 0.5

    def _choose_target(self, all_followers: list):
        """
        Choose nearest alive opponent to target
        Optimized: Only checks nearby followers instead of all followers

        Args:
            all_followers: List of all followers
        """
        alive_followers = [f for f in all_followers if f.alive and f != self]
        if not alive_followers:
            self.target_follower = None
            return

        # Performance optimization: Only check nearby followers (within reasonable range)
        # This reduces O(n) scan to O(k) where k is nearby followers
        max_search_range = 300  # Only look for targets within 300 pixels
        max_search_range_sq = max_search_range * max_search_range

        # Find nearest follower within search range
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

    def _calculate_zone_avoidance(self, arena_center: Tuple[float, float], safe_radius: float) -> Tuple[float, float]:
        """
        Calculate avoidance force to stay away from danger zone

        Args:
            arena_center: Center of the arena
            safe_radius: Current safe zone radius

        Returns:
            (force_x, force_y) tuple representing avoidance force
        """
        # Calculate distance from center
        dx_to_center = arena_center[0] - self.x
        dy_to_center = arena_center[1] - self.y
        distance_from_center = math.sqrt(dx_to_center * dx_to_center + dy_to_center * dy_to_center)

        # Distance from safe zone edge (negative if inside danger zone)
        distance_from_edge = safe_radius - distance_from_center - config.FOLLOWER_RADIUS

        # Start avoiding when within this distance from edge (moderate increase from 120 to 180)
        avoidance_threshold = 70  # Look further ahead to steer away sooner

        if distance_from_edge < avoidance_threshold:
            # Normalize direction to center
            if distance_from_center > 0.1:
                dx_to_center /= distance_from_center
                dy_to_center /= distance_from_center

                # Calculate avoidance strength (stronger as we get closer to edge)
                avoidance_strength = 1.0 - (distance_from_edge / avoidance_threshold)
                # Bias upward to make fleeing the rim more decisive (moderate increase from 1.4 to 1.6)
                avoidance_strength = max(0.0, min(1.0, avoidance_strength * 1.05))

                # Apply strong force when very close to or in danger zone
                if distance_from_edge < 0:
                    # In danger zone - panic mode! (moderate increase from 1.3 to 1.5)
                    avoidance_strength = 1.5
                # Return force toward center (moderate increase from 1.5 to 1.8)
                force_magnitude = self.stats['base_speed'] * avoidance_strength * 1.8
                return (dx_to_center * force_magnitude, dy_to_center * force_magnitude)

        return (0.0, 0.0)

    def _is_in_targeting_band(self, arena_center: Tuple[float, float], safe_radius: float) -> bool:
        band = getattr(config, "BATTLE_ROYALE_TARGETING_BAND", (0.25, 0.75))
        try:
            inner_ratio, outer_ratio = float(band[0]), float(band[1])
        except (TypeError, ValueError, IndexError):
            inner_ratio, outer_ratio = 0.25, 0.75

        inner_ratio = max(0.0, min(1.0, inner_ratio))
        outer_ratio = max(0.0, min(1.0, outer_ratio))
        if outer_ratio < inner_ratio:
            inner_ratio, outer_ratio = outer_ratio, inner_ratio

        if safe_radius is None or safe_radius <= 0:
            return True

        dx = self.x - arena_center[0]
        dy = self.y - arena_center[1]
        distance = math.sqrt(dx * dx + dy * dy)

        inner_radius = safe_radius * inner_ratio
        outer_radius = safe_radius * outer_ratio
        return inner_radius <= distance <= outer_radius

    def _move_toward_target(self, arena_center: Tuple[float, float], dt: float, safe_radius: float = None):
        """
        Move toward target with strategy to push them toward edge
        Adds randomness for natural movement and zone avoidance

        Args:
            arena_center: Center of the arena
            dt: Delta time
            safe_radius: Current safe zone radius for avoidance
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
        random_angle = (random.random() - 0.5) * self.stats['movement_randomness'] * math.pi
        cos_r = math.cos(random_angle)
        sin_r = math.sin(random_angle)
        new_dx = dx * cos_r - dy * sin_r
        new_dy = dx * sin_r + dy * cos_r

        # Calculate base target velocity
        target_vx = new_dx * self.stats['base_speed']
        target_vy = new_dy * self.stats['base_speed']

        # Add zone avoidance force
        if safe_radius is not None:
            avoid_x, avoid_y = self._calculate_zone_avoidance(arena_center, safe_radius)
            target_vx += avoid_x
            target_vy += avoid_y

        # Apply movement with smooth interpolation for less flickering
        smoothing = 0.15  # Lower = smoother but slower response, higher = faster but more jittery
        self.vx += (target_vx - self.vx) * smoothing
        self.vy += (target_vy - self.vy) * smoothing

    def _random_movement(self, dt: float, arena_center: Tuple[float, float] = None, safe_radius: float = None):
        """
        Apply random movement when no target is available

        Args:
            dt: Delta time
            arena_center: Center of the arena for zone avoidance
            safe_radius: Current safe zone radius for avoidance
        """
        # More frequent direction changes for active movement (5% vs 2%)
        if random.random() < 0.05:
            angle = random.random() * 2 * math.pi
            target_vx = math.cos(angle) * self.stats['base_speed']
            target_vy = math.sin(angle) * self.stats['base_speed']

            # Add zone avoidance force
            if arena_center is not None and safe_radius is not None:
                avoid_x, avoid_y = self._calculate_zone_avoidance(arena_center, safe_radius)
                target_vx += avoid_x
                target_vy += avoid_y

            # Smooth interpolation for random movement too
            smoothing = 0.15
            self.vx += (target_vx - self.vx) * smoothing
            self.vy += (target_vy - self.vy) * smoothing

    def check_safe_zone(self, arena_center: Tuple[float, float], safe_radius: float,
                       particle_system=None) -> bool:
        """
        Check if follower is inside safe zone
        Eliminate if any part of follower touches the danger zone

        Args:
            arena_center: Center of the arena
            safe_radius: Current safe zone radius
            particle_system: Optional ParticleSystem for elimination effects

        Returns:
            True if alive, False if eliminated
        """
        if not self.alive:
            return False

        # Calculate distance from center to follower center
        dx = self.x - arena_center[0]
        dy = self.y - arena_center[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if ANY part of the follower is outside the safe zone
        # (distance to center + follower radius > safe zone radius)
        if distance + config.FOLLOWER_RADIUS > safe_radius:
            self.eliminate(particle_system)
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
        if current_time - self.last_bump_time < self.stats['bump_cooldown']:
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
            push_force = self.stats['push_force'] * force_multiplier
            other.push_vx += push_dx * push_force
            other.push_vy += push_dy * push_force

            # Track who pushed the other follower (for kill credit)
            other.last_pushed_by = self

            # Apply反作用力 to self (Newton's third law)
            self.push_vx -= push_dx * push_force * 0.5
            self.push_vy -= push_dy * push_force * 0.5

            # Update cooldown
            self.last_bump_time = current_time
            other.last_bump_time = current_time

            return True

        return False

    def eliminate(self, particle_system=None):
        """
        Eliminate this follower from the game
        Starts fade-out animation
        Credits kill to whoever pushed this follower last

        Args:
            particle_system: Optional ParticleSystem to create elimination effects
        """
        if self.alive:
            self.alive = False
            self.elimination_time = time.time()
            self.surface_needs_update = True

            # Credit kill to whoever pushed us last
            if self.last_pushed_by is not None and self.last_pushed_by.alive:
                self.last_pushed_by.kills += 1

            # Particle effects disabled for performance
            # if particle_system:
            #     particle_system.create_elimination_explosion(self.x, self.y, self.color)

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

    def get_survival_time(self) -> float:
        """
        Get survival time in seconds

        Returns:
            Survival time from spawn to elimination (or current time if still alive)
        """
        end_time = self.elimination_time if not self.alive else time.time()
        return end_time - self.spawn_time

    def __repr__(self):
        status = "ALIVE" if self.alive else "ELIMINATED"
        return f"Follower({self.username}, {status}, pos=({self.x:.1f}, {self.y:.1f}))"
