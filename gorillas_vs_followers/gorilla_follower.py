"""
Gorilla Follower Module
Represents followers in the Gorillas vs Followers game mode
Extends Fighter with gorilla damage tracking for scoring
"""

import pygame
import math
import time
import random
from typing import Tuple
import config
from fighter_arena import Fighter


class GorillaFollower(Fighter):
    """
    A follower in the Gorillas vs Followers game mode
    Extends Fighter with damage tracking specific to gorillas
    Uses default stats (no 1000+ boost) and tracks damage dealt to gorillas for scoring
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize a gorilla follower

        Args:
            follower_data: Dictionary containing 'id', 'username', 'avatar', and optionally 'color'
            position: (x, y) starting position
        """
        # Initialize as normal follower, but we'll override stats
        super().__init__(follower_data, position)

        # Override with gorillas mode stats (no boosts)
        stats = config.GORILLAS_MODE_FOLLOWER_STATS

        self.max_hp = stats["hp"]
        self.current_hp = self.max_hp
        self.speed_stat = stats["speed"]
        self.attack_stat = stats["attack"]
        self.regeneration_stat = stats["regeneration"]
        self.knockback_stat = stats["knockback"]
        self.attack_speed_stat = stats["attack_speed"]

        # Damage tracking for scoring (only damage to gorillas counts)
        self.gorilla_damage_dealt = 0.0

    def _choose_target_fighter(self, all_fighters: list):
        """
        Choose a target - ONLY gorillas (not other followers)
        Overrides Fighter's method to filter for gorillas only

        Args:
            all_fighters: List of all entities in the game
        """
        # Filter to only alive gorillas (not other followers)
        alive_gorillas = [f for f in all_fighters if f.alive and f.__class__.__name__ == 'Gorilla']

        if not alive_gorillas:
            self.target_follower = None
            return

        # Always pick nearest gorilla (100% deterministic targeting)
        min_distance = float('inf')
        nearest = None

        for gorilla in alive_gorillas:
            dx = gorilla.x - self.x
            dy = gorilla.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < min_distance:
                min_distance = distance
                nearest = gorilla

        self.target_follower = nearest

    def apply_knockback(self, dx: float, dy: float, knockback_power: float, attacker=None):
        """
        Apply knockback - but ONLY from Gorillas
        Followers cannot knockback other followers

        Args:
            dx: Normalized X direction of knockback
            dy: Normalized Y direction of knockback
            knockback_power: Knockback stat of attacker
            attacker: Entity applying the knockback (optional)
        """
        # Only accept knockback from Gorillas
        if attacker and attacker.__class__.__name__ != 'Gorilla':
            # Ignore knockback from other followers
            return

        # Accept knockback from Gorillas (or unknown source)
        super().apply_knockback(dx, dy, knockback_power)

    def attack(self, target, current_time: float, combat_enabled: bool = True, alive_count: int = 0) -> bool:
        """
        Attack another entity (follower or gorilla)
        Tracks damage dealt to gorillas specifically for scoring
        Passes self as attacker for knockback filtering

        Args:
            target: Entity to attack
            current_time: Current game time
            combat_enabled: Whether combat is currently allowed
            alive_count: Number of entities currently alive (unused for gorillas mode)

        Returns:
            True if attack landed
        """
        # Check if we should attack (same logic as parent)
        if not combat_enabled or not self.alive or not target.alive:
            return False

        attack_cooldown = 1.0 / self.get_attacks_per_second()
        if current_time - self.last_attack_time < attack_cooldown:
            return False

        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Adjust reach to include target's radius (gorillas are much larger)
        target_radius = getattr(target, "radius", config.FOLLOWER_RADIUS)
        reach = config.FOLLOWER_RADIUS + target_radius + (config.FOLLOWER_RADIUS * 0.3)

        if distance > reach:
            return False

        # Perform attack
        self.last_attack_time = current_time
        self.is_attacking = True
        self.attack_animation_frames = 10

        # Damage calculation
        damage = self.attack_stat

        killed = target.take_damage(damage, self)
        self.damage_dealt += damage

        if killed:
            self.kills += 1

        # Apply knockback with attacker info (so target can filter)
        if distance > 0:
            knockback_dx = dx / distance
            knockback_dy = dy / distance
            # Pass self as attacker so followers can reject knockback from other followers
            if hasattr(target, 'apply_knockback'):
                # Try to pass attacker parameter if supported
                try:
                    target.apply_knockback(knockback_dx, knockback_dy, self.knockback_stat, attacker=self)
                except TypeError:
                    # Fallback for entities that don't support attacker parameter
                    target.apply_knockback(knockback_dx, knockback_dy, self.knockback_stat)

        # Track damage to gorillas
        if target.__class__.__name__ == 'Gorilla':
            self.gorilla_damage_dealt += self.attack_stat

        return True

    def get_stats_summary(self) -> dict:
        """Get summary of follower's stats for debugging"""
        return {
            "hp": f"{self.current_hp:.1f}/{self.max_hp}",
            "speed": self.speed_stat,
            "attack": self.attack_stat,
            "attack_speed": f"{self.get_attacks_per_second():.1f}/sec",
            "gorilla_damage": f"{self.gorilla_damage_dealt:.1f}",
            "damage_dealt": f"{self.damage_dealt:.1f}",
            "damage_taken": f"{self.damage_taken:.1f}",
            "kills": self.kills
        }

    def update_fighter(self, dt: float, arena_rect: Tuple[int, int, int, int],
                       all_fighters: list, current_time: float, combat_enabled: bool = True,
                       gate_progress: float = 1.0):
        """
        Fighter update with gorilla targeting (allows attacking non-Fighter gorillas).
        gate_progress: 0 (closed) prevents targeting; 1 fully open.
        """
        if not self.alive:
            if time.time() - self.elimination_time < config.FADE_DURATION:
                progress = (time.time() - self.elimination_time) / config.FADE_DURATION
                self.alpha = int(255 * (1 - progress))
                self.surface_needs_update = True
            return

        if self.knockback_frames_remaining > 0:
            self.knockback_frames_remaining -= 1

        if self.attack_animation_frames > 0:
            self.attack_animation_frames -= 1
            if self.attack_animation_frames == 0:
                self.is_attacking = False

        # No regen in gorilla mode (regeneration_stat is 0 by default)

        # If gate fully closed, just damp velocity and stay put
        if gate_progress <= 0.0:
            # Apply friction to any residual push and clamp to arena
            self.vx *= config.FRICTION
            self.vy *= config.FRICTION
            self.push_vx *= config.FRICTION
            self.push_vy *= config.FRICTION
            self.x += self.push_vx
            self.y += self.push_vy
            arena_x, arena_y, arena_w, arena_h = arena_rect
            radius = config.FOLLOWER_RADIUS
            self.x = max(arena_x + radius, min(arena_x + arena_w - radius, self.x))
            self.y = max(arena_y + radius, min(arena_y + arena_h - radius, self.y))
            return

        # Retarget when needed or occasionally (gate partially/fully open)
        if self.target_follower is None or not getattr(self.target_follower, "alive", False) or random.random() < 0.02:
            self._choose_target_fighter(all_fighters)

        if self.target_follower and getattr(self.target_follower, "alive", False):
            self._move_toward_target_fighter(dt)

            if combat_enabled:
                alive_count = sum(1 for f in all_fighters if getattr(f, "alive", False))
                self.attack(self.target_follower, current_time, combat_enabled, alive_count)
        else:
            self._random_movement_fighter(dt)

        # Apply push velocity from knockback
        self.x += self.push_vx
        self.y += self.push_vy
        self.push_vx *= config.FRICTION
        self.push_vy *= config.FRICTION

        # Apply regular velocity
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vx *= config.FRICTION
        self.vy *= config.FRICTION

        # Keep within arena bounds (rectangle)
        arena_x, arena_y, arena_w, arena_h = arena_rect
        radius = config.FOLLOWER_RADIUS

        self.x = max(arena_x + radius, min(arena_x + arena_w - radius, self.x))
        self.y = max(arena_y + radius, min(arena_y + arena_h - radius, self.y))

        # Bounce off walls
        if self.x <= arena_x + radius or self.x >= arena_x + arena_w - radius:
            self.vx *= -0.5
            self.push_vx *= -0.5
        if self.y <= arena_y + radius or self.y >= arena_y + arena_h - radius:
            self.vy *= -0.5
            self.push_vy *= -0.5

    def __repr__(self):
        status = "ALIVE" if self.alive else "DEAD"
        return f"GorillaFollower({self.username}, {status}, HP={self.current_hp:.0f}/{self.max_hp}, GorillaDmg={self.gorilla_damage_dealt:.0f})"
