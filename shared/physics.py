"""
Physics Engine Module
Handles collision detection and physics calculations
"""

import time
import math
import random
from typing import List, TYPE_CHECKING
import config
import numpy as np

# Try to import Numba for accelerated physics
try:
    from shared.physics_numba import detect_collisions_numba, resolve_overlaps_numba
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("⚠️  Numba not available - using standard physics (slower)")

if TYPE_CHECKING:
    from battle_royale import Follower


class PhysicsEngine:
    """
    Manages physics simulation including collision detection and resolution
    Optimized for handling many followers simultaneously using spatial partitioning
    """

    @staticmethod
    def _is_gorilla(entity) -> bool:
        """Helper to detect gorilla entities (which should ignore follower collisions)."""
        return getattr(entity, "__class__", None).__name__ == "Gorilla"

    def __init__(self):
        """
        Initialize the physics engine
        """
        self.collision_checks = 0  # For debugging/stats
        self.collisions_detected = 0

        # Spatial grid for O(n) collision detection
        self.spatial_grid = {}  # Grid for fast neighbor queries
        self.last_grid_cell_size = 0  # Track cell size changes

        # Track if Numba activation message has been shown
        self.numba_message_shown = False

    def update(self, followers: List['Follower'], dt: float):
        """
        Update physics for all followers
        Handles collision detection and resolution

        Args:
            followers: List of all followers
            dt: Delta time in seconds
        """
        game_mode = getattr(config, "GAME_MODE", "")

        # Use Numba acceleration for large player counts (>1000 players)
        use_numba = NUMBA_AVAILABLE and getattr(config, 'USE_NUMBA_PHYSICS', True)
        if use_numba and len(followers) > 1000:
            # For gorilla mode, only run fast collision separation on followers (skip gorillas),
            # then do a lightweight follower<->gorilla separation to keep them apart.
            if game_mode == "gorillas_vs_followers":
                alive_followers = [f for f in followers if f.alive and not self._is_gorilla(f)]
                if alive_followers:
                    self._update_with_numba(alive_followers, dt)
                # Push followers off gorillas without moving the gorillas
                gorillas = [g for g in followers if g.alive and self._is_gorilla(g)]
                if gorillas:
                    for f in alive_followers:
                        for g in gorillas:
                            ra = getattr(f, "radius", config.FOLLOWER_RADIUS)
                            rg = getattr(g, "radius", config.FOLLOWER_RADIUS)
                            min_dist = ra + rg
                            dx = f.x - g.x
                            dy = f.y - g.y
                            dist_sq = dx * dx + dy * dy
                            if dist_sq < (min_dist * min_dist) and dist_sq > 0.0001:
                                dist = math.sqrt(dist_sq)
                                overlap = min_dist - dist
                                sep_x = dx / dist
                                sep_y = dy / dist
                                f.x += sep_x * overlap
                                f.y += sep_y * overlap
                return
            else:
                return self._update_with_numba(followers, dt)

        if game_mode == "gorillas_vs_followers":
            # Simple separation between all alive entities, keeping gorillas immovable.
            alive_entities = [f for f in followers if getattr(f, "alive", False)]
            for i, a in enumerate(alive_entities):
                for b in alive_entities[i + 1:]:
                    ra = getattr(a, "radius", config.FOLLOWER_RADIUS)
                    rb = getattr(b, "radius", config.FOLLOWER_RADIUS)
                    min_dist = ra + rb

                    dx = b.x - a.x
                    dy = b.y - a.y
                    dist_sq = dx * dx + dy * dy

                    if dist_sq < (min_dist * min_dist) and dist_sq > 0.0001:
                        dist = math.sqrt(dist_sq)
                        overlap = min_dist - dist
                        sep_x = dx / dist
                        sep_y = dy / dist

                        a_is_gorilla = self._is_gorilla(a)
                        b_is_gorilla = self._is_gorilla(b)

                        if a_is_gorilla and not b_is_gorilla:
                            b.x += sep_x * overlap
                            b.y += sep_y * overlap
                        elif b_is_gorilla and not a_is_gorilla:
                            a.x -= sep_x * overlap
                            a.y -= sep_y * overlap
                        else:
                            move = overlap * 0.5
                            a.x -= sep_x * move
                            a.y -= sep_y * move
                            b.x += sep_x * move
                            b.y += sep_y * move

                    elif dist_sq <= 0.0001:
                        angle = random.random() * math.tau
                        move = config.FOLLOWER_RADIUS * 0.5
                        a.x -= math.cos(angle) * move
                        a.y -= math.sin(angle) * move
                        b.x += math.cos(angle) * move
                        b.y += math.sin(angle) * move
            return

        current_time = time.time()
        # Skip gorillas for follower-style collisions; they are immovable.
        alive_followers = [f for f in followers if f.alive and not self._is_gorilla(f)]

        # Reset stats
        self.collision_checks = 0
        self.collisions_detected = 0

        # Build spatial grid ONCE for efficient collision detection
        self._build_spatial_grid(alive_followers)

        # Track processed pairs to avoid duplicate checks
        processed_pairs = set()

        # Check collisions using spatial grid (O(n) instead of O(n²))
        for follower in alive_followers:
            # Only check nearby followers using spatial grid
            nearby_followers = self._get_nearby_followers(follower)

            for other in nearby_followers:
                if other == follower:
                    continue

                # Skip if we've already processed this pair
                pair_key = (min(id(follower), id(other)), max(id(follower), id(other)))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

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

    def _update_with_numba(self, followers: List['Follower'], dt: float):
        """
        Ultra-fast physics update using Numba JIT compilation.
        Provides 10-50x speedup for large player counts.

        Args:
            followers: List of all followers
            dt: Delta time in seconds
        """
        # Show activation message once
        if not self.numba_message_shown:
            print("🚀 Numba physics activated - using JIT-compiled collision detection")
            self.numba_message_shown = True

        current_time = time.time()

        # Reset stats
        self.collision_checks = 0
        self.collisions_detected = 0

        try:
            # Extract data into numpy arrays for Numba
            n = len(followers)
            positions_x = np.zeros(n, dtype=np.float32)
            positions_y = np.zeros(n, dtype=np.float32)
            radii = np.zeros(n, dtype=np.float32)
            alive = np.zeros(n, dtype=np.bool_)

            for i, f in enumerate(followers):
                positions_x[i] = f.x
                positions_y[i] = f.y
                radii[i] = getattr(f, 'radius', config.FOLLOWER_RADIUS)
                alive[i] = f.alive

            # Calculate grid size dynamically
            grid_size = max(config.COLLISION_DISTANCE * 2, 8)

            # Run Numba-accelerated collision detection
            collision_pairs, collision_count = detect_collisions_numba(
                positions_x, positions_y, radii, alive,
                config.COLLISION_DISTANCE, grid_size,
                config.SCREEN_WIDTH, config.SCREEN_HEIGHT
            )
        except (MemoryError, RuntimeError, Exception) as e:
            # Allocation failed - player count too large for Numba
            print(f"⚠️  Numba allocation failed with {len(followers):,} players")
            print(f"   Falling back to minimal collision detection")
            print(f"   Note: For 500k+ players, collision detection is disabled for performance")

            # Disable Numba for future frames
            self.use_numba = False

            # Use minimal fallback (no collision detection for extreme counts)
            return

        self.collision_checks = collision_count

        # Apply collision results to follower objects
        for i, j in collision_pairs:
            # Call the follower's collision handler
            if followers[i].check_collision(followers[j], current_time):
                self.collisions_detected += 1

    def _build_spatial_grid(self, followers: List['Follower']):
        """
        Build spatial grid for fast neighbor queries.
        Reduces collision checks from O(n²) to O(n).

        Args:
            followers: List of all followers
        """
        # Calculate cell size dynamically based on current FOLLOWER_RADIUS
        # This is critical because FOLLOWER_RADIUS changes with dynamic scaling
        # Use minimum of 8px to prevent too many cells, but keep cells small enough for efficiency
        # Cell size should be ~2x collision distance for optimal performance
        self.grid_cell_size = max(config.COLLISION_DISTANCE * 2, 8)

        # Clear grid for current frame
        self.spatial_grid.clear()

        for follower in followers:
            if not follower.alive:
                continue

            # Calculate grid cell using current grid_cell_size
            cell_x = int(follower.x / self.grid_cell_size)
            cell_y = int(follower.y / self.grid_cell_size)
            cell_key = (cell_x, cell_y)

            # Add to grid
            if cell_key not in self.spatial_grid:
                self.spatial_grid[cell_key] = []
            self.spatial_grid[cell_key].append(follower)

    def _get_nearby_followers(self, follower):
        """
        Get followers in nearby grid cells (current + 4 adjacent, not diagonals).
        Optimized to reduce false positives while maintaining collision detection accuracy.

        Args:
            follower: The follower to query around

        Returns:
            List of nearby followers
        """
        cell_x = int(follower.x / self.grid_cell_size)
        cell_y = int(follower.y / self.grid_cell_size)

        nearby = []
        # Check current cell + 4 adjacent cells (up, down, left, right)
        # Skip diagonal cells to reduce false positives
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
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
        alive_followers = [f for f in followers if f.alive and not self._is_gorilla(f)]
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
        Uses spatial grid for O(n) performance

        Args:
            followers: List of all followers
            strength: Strength of separation force
        """
        alive_followers = [f for f in followers if f.alive and not self._is_gorilla(f)]
        # Reduced personal space to allow closer combat
        personal_space = config.FOLLOWER_RADIUS * 2.1  # Just slightly more than touching

        # Spatial grid should already be built from update(), but rebuild if needed
        if not self.spatial_grid:
            self._build_spatial_grid(alive_followers)

        for follower in alive_followers:
            separation_x = 0
            separation_y = 0
            neighbor_count = 0

            # Only check nearby followers using spatial grid
            nearby_followers = self._get_nearby_followers(follower)

            for other in nearby_followers:
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
