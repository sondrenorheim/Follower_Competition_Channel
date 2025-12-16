"""
Gorilla Module
Represents the boss-like gorilla enemies in Gorillas vs Followers game mode
Extended from Follower with custom stats, arm animation, and combat behavior
"""

import pygame
import math
import random
import time
from typing import Tuple, Optional, List
import config
from battle_royale import Follower


class Gorilla(Follower):
    """
    A gorilla boss enemy in the Gorillas vs Followers game mode

    Features:
    - High HP (9000) with low speed (1) and high attack (30)
    - Animated arms using sine wave oscillation
    - Always targets nearest opponent (100% deterministic)
    - Immune to knockback from followers (only takes stun)
    - Massive knockback dealt to followers (55 distance)
    """

    def __init__(self, position: Tuple[float, float], gorilla_id: int):
        """
        Initialize a gorilla boss enemy

        Args:
            position: (x, y) starting position
            gorilla_id: Unique identifier for this gorilla
        """
        # Create dummy follower data for base class
        # Pick a variant based on weighted probabilities
        variant_name, variant = self._choose_variant()

        follower_data = {
            'id': f'gorilla_{gorilla_id}',
            'username': f'{variant_name.capitalize()} Gorilla #{gorilla_id}',
            'avatar': None,
            'color': variant.get('color', random.choice(config.GORILLA_COLORS))
        }

        super().__init__(follower_data, position)

        # Override with gorilla stats (variant)
        self.max_hp = variant["hp"]
        self.current_hp = self.max_hp
        self.speed_stat = variant["speed"]
        self.attack_stat = variant["attack"]
        self.regeneration_stat = variant["regeneration"]
        self.knockback_stat = variant["knockback_distance"]
        self.attack_speed_stat = variant["attack_speed"]

        # Gorilla visual properties
        size_mult = variant.get("size_multiplier", 1.0) * config.GORILLA_SIZE_MULTIPLIER
        self.radius = config.FOLLOWER_RADIUS * size_mult
        self.color = follower_data['color']
        self.attack_speed_debuff = 1.0

        # Animation state for arms
        self.animation_time = random.uniform(0, 2 * math.pi)  # Random starting phase
        self.arm_left_angle = -90  # degrees from horizontal
        self.arm_right_angle = 90
        self.is_attacking_animation = False
        self.attack_animation_timer = 0.0

        # Combat properties
        self.last_attack_time = 0
        self.attack_range = config.FIGHTER_ATTACK_RANGE * config.GORILLA_SIZE_MULTIPLIER
        self.base_attack_range = self.attack_range
        self.knockback_frames_remaining = 0  # Stun frames from being attacked

    def _choose_variant(self):
        """
        Choose a gorilla variant based on configured weights.
        """
        variants = getattr(config, "GORILLA_VARIANTS", {})
        if not variants:
            return "default", config.GORILLA_STATS

        names = list(variants.keys())
        weights = [variants[n].get("weight", 1.0) for n in names]
        total = sum(weights)
        pick = random.uniform(0, total)
        accum = 0.0
        for name, w in zip(names, weights):
            accum += w
            if pick <= accum:
                return name, variants[name]
        return names[-1], variants[names[-1]]

    def update(self, dt: float, arena, all_entities: List, combat_enabled: bool = True, gate_progress: float = 1.0):
        """
        Update gorilla state including arm animation

        Args:
            dt: Delta time in seconds
            arena: Arena bounds (GorillasArena object)
            all_entities: List of all entities in the game
            combat_enabled: Whether combat is currently allowed
        """
        if not self.alive:
            # Update fade out
            if self.is_fading():
                self.fade_timer += dt
                self.alpha = int(255 * (1 - self.fade_timer / self.fade_duration))
                if self.alpha <= 0:
                    self.alpha = 0
            return

        current_time = time.time()

        # Handle knockback/stun
        if self.knockback_frames_remaining > 0:
            self.knockback_frames_remaining -= 1

        # Apply push velocity (from knockback)
        if abs(self.push_vx) > 0.1 or abs(self.push_vy) > 0.1:
            self.x += self.push_vx
            self.y += self.push_vy
            self.push_vx *= 0.85
            self.push_vy *= 0.85

        # Clamp position to arena
        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

        # Movement and combat (only if not stunned and gate at least partially open)
        if self.knockback_frames_remaining <= 0 and combat_enabled and gate_progress > 0.0:
            # Choose target (nearest follower)
            target = self._choose_target(all_entities)

            if target:
                # Move toward target
                dx = target.x - self.x
                dy = target.y - self.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance > 0:
                    # Normalize and move
                    dx /= distance
                    dy /= distance
                    move_speed = self.speed_stat
                    self.x += dx * move_speed * dt * 60
                    self.y += dy * move_speed * dt * 60

                # Try to attack
                self.attack(target, current_time, combat_enabled, all_entities=all_entities)

        # Update arm animation
        self.animation_time += dt

        # Check if currently in attack animation
        if self.is_attacking_animation:
            self.attack_animation_timer += dt
            if self.attack_animation_timer >= 0.2:  # Attack animation duration
                self.is_attacking_animation = False
                self.attack_animation_timer = 0.0

        # Continuous arm oscillation (when not attacking)
        if not self.is_attacking_animation:
            frequency = 2 * math.pi / config.GORILLA_ARM_SWING_PERIOD
            amplitude = config.GORILLA_ARM_SWING_AMPLITUDE

            # Left arm swings from -90-amplitude to -90+amplitude
            self.arm_left_angle = -90 + amplitude * math.sin(frequency * self.animation_time)

            # Right arm swings opposite phase
            self.arm_right_angle = 90 + amplitude * math.sin(frequency * self.animation_time + math.pi)
        else:
            # Attack animation - arms swing forward
            progress = self.attack_animation_timer / 0.2  # 0 to 1
            swing_amount = math.sin(progress * math.pi) * 60  # 0 to 60 to 0
            self.arm_left_angle = -90 + swing_amount
            self.arm_right_angle = 90 - swing_amount

    def _choose_target(self, all_entities: List) -> Optional:
        """
        Choose the nearest follower as target (100% deterministic)

        Args:
            all_entities: List of all entities in the game

        Returns:
            Nearest alive follower, or None if none exist
        """
        # Filter to only alive followers (not other gorillas)
        alive_followers = [
            entity for entity in all_entities
            if entity.alive and entity != self and entity.__class__.__name__ != 'Gorilla'
        ]

        if not alive_followers:
            return None

        # Find nearest follower
        nearest = min(alive_followers, key=lambda f: self._distance_to(f))
        return nearest

    def _distance_to(self, other) -> float:
        """Calculate Euclidean distance to another entity"""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def attack(self, target, current_time: float, combat_enabled: bool = True, alive_count: int = 0, all_entities=None) -> bool:
        """
        Attack another entity with gorilla's massive power

        Args:
            target: Entity to attack
            current_time: Current game time
            combat_enabled: Whether combat is currently allowed
            alive_count: Number of entities currently alive (unused)
            all_entities: Optional list of all entities (for splash damage)

        Returns:
            True if attack landed
        """
        def _is_gorilla(entity) -> bool:
            return getattr(entity, "__class__", None).__name__ == "Gorilla"

        if not combat_enabled or not self.alive or not target.alive:
            return False

        # Check attack cooldown
        attack_cooldown = 1.0 / self.get_attacks_per_second()
        if current_time - self.last_attack_time < attack_cooldown:
            return False

        # Check if target is in range
        distance = self._distance_to(target)
        if distance > self.attack_range:
            return False

        # Perform attack
        self.last_attack_time = current_time
        self.is_attacking_animation = True
        self.attack_animation_timer = 0.0

        # Helper to apply knockback displacement/velocity
        knockback_power = getattr(config, "GORILLA_ATTACK_KNOCKBACK", 40)

        def apply_knock(entity, dx_norm, dy_norm):
            # Direct displacement
            entity.x += dx_norm * knockback_power
            entity.y += dy_norm * knockback_power
            # Add push velocity if available
            if hasattr(entity, "push_vx") and hasattr(entity, "push_vy"):
                entity.push_vx += dx_norm * knockback_power * 0.3
                entity.push_vy += dy_norm * knockback_power * 0.3
            # Apply stun/knockback state if supported
            if hasattr(entity, "knockback_frames_remaining"):
                entity.knockback_frames_remaining = max(
                    getattr(entity, "knockback_frames_remaining", 0),
                    int(knockback_power * 0.5)
                )

        # Deal damage to primary target
        target.take_damage(self.attack_stat, current_time)

        # Apply knockback to primary target
        dx = target.x - self.x
        dy = target.y - self.y
        dist_primary = math.sqrt(dx * dx + dy * dy)
        if dist_primary > 0:
            nx = dx / dist_primary
            ny = dy / dist_primary
            apply_knock(target, nx, ny)

        # Splash damage around the target (area attack)
        base_inner = getattr(config, "GORILLA_ATTACK_SPLASH_RADIUS", 21)
        base_outer = getattr(config, "GORILLA_ATTACK_SPLASH_FALLOFF_RADIUS", 30)
        base_player = getattr(config, "GORILLA_SPLASH_BASE_PLAYER_RADIUS", 14)
        scale = config.FOLLOWER_RADIUS / base_player if base_player > 0 else 1.0
        splash_radius_inner = base_inner * scale
        splash_radius_outer = base_outer * scale
        if all_entities:
            for entity in all_entities:
                if entity is target or entity is self or not getattr(entity, "alive", False):
                    continue
                if _is_gorilla(entity):
                    continue

                dx = entity.x - target.x
                dy = entity.y - target.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= splash_radius_outer * splash_radius_outer:
                    dist = math.sqrt(dist_sq) if dist_sq > 0 else 0
                    dmg = self.attack_stat
                    if dist > splash_radius_inner:
                        dmg *= 0.25
                    entity.take_damage(dmg, current_time)
                    if dist > 0:
                        nx = dx / dist
                        ny = dy / dist
                        apply_knock(entity, nx, ny)

        return True

    def take_damage(self, damage: float, attacker=None) -> bool:
        """
        Take damage from an attack

        Args:
            damage: Amount of damage to take
            attacker: Entity dealing the damage (optional)

        Returns:
            True if this killed the gorilla
        """
        self.current_hp -= damage
        # Gorilla inherits from Follower which has no damage_taken; guard attribute.
        if not hasattr(self, "damage_taken"):
            self.damage_taken = 0.0
        self.damage_taken += damage

        if self.current_hp <= 0:
            self.current_hp = 0
            self.alive = False
            # Follower has eliminate(), but gorillas should fade; guard if method missing.
            if hasattr(self, "start_fade_out"):
                self.start_fade_out()
            return True

        return False

    def apply_knockback(self, dx: float, dy: float, power: float, attacker=None):
        """
        Apply knockback to gorilla (COMPLETELY IMMUNE - no stun, no movement)

        Args:
            dx: Normalized x direction
            dy: Normalized y direction
            power: Knockback power
            attacker: Entity applying knockback (optional)
        """
        # Gorillas are COMPLETELY IMMUNE to knockback
        # No stun, no movement - gorillas are unstoppable!
        pass  # Do absolutely nothing

    def get_attacks_per_second(self) -> float:
        """Calculate attacks per second based on attack_speed_stat"""
        # attack_speed_stat = 20 means 2 attacks per second
        return (self.attack_speed_stat / 10.0) * self.attack_speed_debuff

    def get_hp_percentage(self) -> float:
        """Get current HP as percentage (0.0 to 1.0)"""
        if self.max_hp <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_hp / self.max_hp))

    def get_arm_endpoints(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Calculate the endpoints of both arms for rendering

        Returns:
            ((left_x, left_y), (right_x, right_y)) tuple of arm endpoints
        """
        # Shoulder positions (70% of radius from center)
        shoulder_offset = self.radius * 0.7
        left_shoulder_x = self.x - shoulder_offset
        right_shoulder_x = self.x + shoulder_offset
        shoulder_y = self.y

        # Arm length
        arm_length = self.radius * config.GORILLA_ARM_LENGTH_MULTIPLIER

        # Calculate endpoints based on angles
        left_end_x = left_shoulder_x + arm_length * math.cos(math.radians(self.arm_left_angle))
        left_end_y = shoulder_y + arm_length * math.sin(math.radians(self.arm_left_angle))

        right_end_x = right_shoulder_x + arm_length * math.cos(math.radians(self.arm_right_angle))
        right_end_y = shoulder_y + arm_length * math.sin(math.radians(self.arm_right_angle))

        return ((left_end_x, left_end_y), (right_end_x, right_end_y))

    def get_stats_summary(self) -> dict:
        """Get summary of gorilla's stats for debugging"""
        return {
            "hp": f"{self.current_hp:.1f}/{self.max_hp}",
            "hp_pct": f"{self.get_hp_percentage() * 100:.1f}%",
            "speed": self.speed_stat,
            "attack": self.attack_stat,
            "attack_speed": f"{self.get_attacks_per_second():.1f}/sec",
            "knockback": self.knockback_stat,
            "damage_dealt": f"{self.damage_dealt:.1f}",
            "damage_taken": f"{self.damage_taken:.1f}",
            "kills": self.kills
        }

    def __repr__(self):
        status = "ALIVE" if self.alive else "DEAD"
        return f"Gorilla({self.username}, {status}, HP={self.current_hp:.0f}/{self.max_hp}, Kills={self.kills})"
