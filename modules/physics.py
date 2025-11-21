"""
Physics Engine Module
Handles collision detection and physics calculations
"""

import time
from typing import List
import config
from .follower import Follower


class PhysicsEngine:
    """
    Manages physics simulation including collision detection and resolution
    Optimized for handling many followers simultaneously
    """

    def __init__(self):
        """
        Initialize the physics engine
        """
        self.collision_checks = 0  # For debugging/stats
        self.collisions_detected = 0

    def update(self, followers: List[Follower], dt: float):
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

    def resolve_overlaps(self, followers: List[Follower]):
        """
        Immediately resolve overlapping followers by repositioning them
        This prevents followers' radii from overlapping

        Args:
            followers: List of all followers
        """
        alive_followers = [f for f in followers if f.alive]
        min_distance = config.FOLLOWER_RADIUS * 2  # Minimum distance between centers

        # Iterate multiple times to resolve chain overlaps
        for iteration in range(3):  # 3 iterations is usually enough
            for i, follower in enumerate(alive_followers):
                for other in alive_followers[i + 1:]:
                    dx = other.x - follower.x
                    dy = other.y - follower.y
                    distance = (dx * dx + dy * dy) ** 0.5

                    # If overlapping, push them apart
                    if distance < min_distance and distance > 0.1:
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
                    elif distance <= 0.1:
                        # Followers at exact same position, separate randomly
                        import random
                        angle = random.random() * 6.28318  # 2 * pi
                        import math
                        move_amount = min_distance * 0.5
                        follower.x -= math.cos(angle) * move_amount
                        follower.y -= math.sin(angle) * move_amount
                        other.x += math.cos(angle) * move_amount
                        other.y += math.sin(angle) * move_amount

    def apply_separation_force(self, followers: List[Follower], strength: float = 0.3):
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
