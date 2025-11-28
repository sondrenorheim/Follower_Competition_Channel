"""
Physics Engine Module
Handles collision detection and physics calculations
"""

import time
from typing import List, TYPE_CHECKING
import config

if TYPE_CHECKING:
    from battle_royale import Follower


class PhysicsEngine:
    """
    Manages physics simulation including collision detection and resolution
    Optimized for handling many followers simultaneously using spatial partitioning
    """

    def __init__(self):
        """
        Initialize the physics engine
        """
        self.collision_checks = 0  # For debugging/stats
        self.collisions_detected = 0

        # Spatial grid for O(n) collision detection
        self.grid_cell_size = config.FOLLOWER_RADIUS * 4  # Cell size for spatial partitioning
        self.spatial_grid = {}  # Grid for fast neighbor queries

    def update(self, followers: List['Follower'], dt: float):
        """
        Update physics for all followers
        Handles collision detection and resolution

        Args:
            followers: List of all followers
            dt: Delta time in seconds
        """
        current_time = time.time()
        alive_followers = [f for f in followers if f.alive]

        # Reset stats
        self.collision_checks = 0
        self.collisions_detected = 0

        # Check collisions between all pairs of followers
        # Using spatial optimization: only check nearby followers
        for i, follower in enumerate(alive_followers):
            # Check against followers ahead in the list (avoid duplicate checks)
            for other in alive_followers[i + 1:]:
                # Skip collision check if they're teammates (unless in free-for-all mode)
                if hasattr(follower, 'team') and hasattr(other, 'team'):
                    # Both are TeamFighters
                    if follower.team == other.team and not follower.freeforall_mode:
                        continue  # Don't check collisions between teammates

                self.collision_checks += 1

                # Quick distance check before expensive collision calculation
                dx = abs(follower.x - other.x)
                dy = abs(follower.y - other.y)

                # Early rejection if too far apart (Manhattan distance)
                if dx > config.COLLISION_DISTANCE or dy > config.COLLISION_DISTANCE:
                    continue

                # Perform actual collision check
                if follower.check_collision(other, current_time):
                    self.collisions_detected += 1

    def _build_spatial_grid(self, followers: List['Follower']):
        """
        Build spatial grid for fast neighbor queries.
        Reduces collision checks from O(n²) to O(n).

        Args:
            followers: List of all followers
        """
        self.spatial_grid.clear()

        for follower in followers:
            if not follower.alive:
                continue

            # Calculate grid cell
            cell_x = int(follower.x / self.grid_cell_size)
            cell_y = int(follower.y / self.grid_cell_size)
            cell_key = (cell_x, cell_y)

            # Add to grid
            if cell_key not in self.spatial_grid:
                self.spatial_grid[cell_key] = []
            self.spatial_grid[cell_key].append(follower)

    def _get_nearby_followers(self, follower):
        """
        Get followers in nearby grid cells (3x3 around the follower).

        Args:
            follower: The follower to query around

        Returns:
            List of nearby followers
        """
        cell_x = int(follower.x / self.grid_cell_size)
        cell_y = int(follower.y / self.grid_cell_size)

        nearby = []
        # Check 3x3 grid of cells around the follower
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell_key = (cell_x + dx, cell_y + dy)
                if cell_key in self.spatial_grid:
                    nearby.extend(self.spatial_grid[cell_key])

        return nearby

    def resolve_overlaps(self, followers: List['Follower']):
        """
        Immediately resolve overlapping followers by repositioning them.
        Uses spatial partitioning for O(n) performance instead of O(n²).

        Args:
            followers: List of all followers
        """
        alive_followers = [f for f in followers if f.alive]
        min_distance = config.FOLLOWER_RADIUS * 2  # Minimum distance between centers
        min_distance_sq = min_distance * min_distance

        # Iterate multiple times to resolve chain overlaps (reduced from 3 to 2 for performance)
        for iteration in range(2):
            # Build spatial grid for this iteration
            self._build_spatial_grid(alive_followers)

            # Track which pairs we've already processed to avoid duplicates
            processed_pairs = set()

            # Check each follower only against nearby followers
            for follower in alive_followers:
                nearby_followers = self._get_nearby_followers(follower)

                for other in nearby_followers:
                    if other == follower:
                        continue

                    # Skip if we've already processed this pair
                    pair_key = (min(id(follower), id(other)), max(id(follower), id(other)))
                    if pair_key in processed_pairs:
                        continue
                    processed_pairs.add(pair_key)

                    dx = other.x - follower.x
                    dy = other.y - follower.y
                    distance_sq = dx * dx + dy * dy  # Use squared distance to avoid sqrt

                    # If overlapping, push them apart
                    if distance_sq < min_distance_sq and distance_sq > 0.01:
                        distance = distance_sq ** 0.5

                        # Calculate overlap amount
                        overlap = min_distance - distance

                        # Calculate separation direction (normalized)
                        sep_x = dx / distance
                        sep_y = dy / distance

                        # Move each follower half the overlap distance
                        move_amount = overlap * 0.5
                        follower.x -= sep_x * move_amount
                        follower.y -= sep_y * move_amount
                        other.x += sep_x * move_amount
                        other.y += sep_y * move_amount
                    elif distance_sq <= 0.01:
                        # Followers at exact same position, separate randomly
                        import random
                        import math
                        angle = random.random() * 6.28318  # 2 * pi
                        move_amount = min_distance * 0.5
                        follower.x -= math.cos(angle) * move_amount
                        follower.y -= math.sin(angle) * move_amount
                        other.x += math.cos(angle) * move_amount
                        other.y += math.sin(angle) * move_amount

    def apply_separation_force(self, followers: List['Follower'], strength: float = 0.3):
        """
        Apply gentle separation force to prevent followers from stacking
        This ensures followers spread out naturally without interfering with combat

        Args:
            followers: List of all followers
            strength: Strength of separation force
        """
        alive_followers = [f for f in followers if f.alive]
        # Reduced personal space to allow closer combat
        personal_space = config.FOLLOWER_RADIUS * 2.1  # Just slightly more than touching

        for follower in alive_followers:
            separation_x = 0
            separation_y = 0
            neighbor_count = 0

            # Check nearby followers
            for other in alive_followers:
                if other == follower:
                    continue

                dx = follower.x - other.x
                dy = follower.y - other.y
                distance = (dx * dx + dy * dy) ** 0.5

                # Only apply separation when very close (to prevent stacking)
                if distance < personal_space and distance > 0.1:
                    # Gentle separation force - doesn't interfere with push mechanics
                    force = strength * (personal_space - distance) / personal_space
                    separation_x += (dx / distance) * force
                    separation_y += (dy / distance) * force
                    neighbor_count += 1

            # Apply average separation force
            if neighbor_count > 0:
                follower.vx += separation_x / neighbor_count
                follower.vy += separation_y / neighbor_count

    def get_stats(self) -> dict:
        """
        Get physics engine statistics

        Returns:
            Dictionary with collision stats
        """
        return {
            "collision_checks": self.collision_checks,
            "collisions_detected": self.collisions_detected
        }

    def __repr__(self):
        return f"PhysicsEngine(checks={self.collision_checks}, collisions={self.collisions_detected})"
