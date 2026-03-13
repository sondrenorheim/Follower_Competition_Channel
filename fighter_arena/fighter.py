"""
Fighter Character Module
Represents individual fighters in the Fighter Arena game mode
Extends Follower with combat stats and abilities
"""

import pygame
import math
import random
import time
from typing import Optional, Tuple, List
from PIL import Image
import config
from battle_royale import Follower


class Fighter(Follower):
    """
    Represents a single fighter character in the Fighter Arena
    Extends Follower with combat stats: HP, Speed, Attack, Regeneration, Knockback, Attack Speed
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float]):
        """
        Initialize a fighter character

        Args:
            follower_data: Dictionary containing 'id', 'username', 'avatar', and optionally 'color'
            position: (x, y) starting position
        """
        super().__init__(follower_data, position)

        # Get default stats
        default_stats = config.FIGHTER_DEFAULT_STATS

        # Get stat boosts for this username (if any)
        boosts = config.FIGHTER_STAT_BOOSTS.get(self.username, {})

        # Initialize combat stats with defaults + boosts
        self.max_hp = default_stats["hp"] + boosts.get("hp", 0)
        self.current_hp = self.max_hp
        self.speed_stat = default_stats["speed"] + boosts.get("speed", 0)
        self.attack_stat = default_stats["attack"] + boosts.get("attack", 0)
        self.regeneration_stat = default_stats["regeneration"] + boosts.get("regeneration", 0)
        self.knockback_stat = default_stats["knockback"] + boosts.get("knockback", 0)
        self.attack_speed_stat = default_stats["attack_speed"] + boosts.get("attack_speed", 0)

        # Combat state
        self.last_attack_time = 0.0
        self.knockback_frames_remaining = 0  # Frames until can attack again (stun)
        self.is_attacking = False
        self.attack_animation_frames = 0

        # Track stats
        self.damage_dealt = 0.0
        self.damage_taken = 0.0
        self.kills = 0

    def get_attacks_per_second(self) -> float:
        """Calculate attacks per second from attack_speed stat"""
        return self.attack_speed_stat / 10.0

    def get_attack_cooldown(self) -> float:
        """Get cooldown between attacks in seconds"""
        aps = self.get_attacks_per_second()
        return 1.0 / aps if aps > 0 else 1.0

    def get_movement_speed(self) -> float:
        """
        Get movement speed (pixels per frame)
        Speed stat divided by 1.5 for balanced movement
        """
        return self.speed_stat / 1.5

    def can_attack(self, current_time: float, combat_enabled: bool = True) -> bool:
        """
        Check if fighter can attack

        Args:
            current_time: Current game time
            combat_enabled: Whether combat is currently allowed (False during intro/countdown)

        Returns:
            True if can attack (not on cooldown and not stunned)
        """
        if not combat_enabled:
            return False

        if self.knockback_frames_remaining > 0:
            return False

        cooldown = self.get_attack_cooldown()
        return current_time - self.last_attack_time >= cooldown

    def attack(self, target: 'Fighter', current_time: float, combat_enabled: bool = True, alive_count: int = 0) -> bool:
        """
        Attack another fighter

        Args:
            target: Fighter to attack
            current_time: Current game time
            combat_enabled: Whether combat is currently allowed
            alive_count: Number of fighters currently alive (for damage scaling)

        Returns:
            True if attack landed
        """
        if not self.can_attack(current_time, combat_enabled):
            return False

        if not target.alive:
            return False

        # Calculate distance to target
        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if in attack range
        if distance > config.FIGHTER_ATTACK_RANGE:
            return False

        # Land the attack!
        self.last_attack_time = current_time
        self.is_attacking = True

        # Debug: Log attacks with timestamp
        # import time
        # print(f"⚔️  [{time.time():.2f}] {self.username} attacked {target.username} (combat_enabled={combat_enabled})")
        self.attack_animation_frames = 10  # Brief attack animation

        # Late game uses fixed damage; early game uses one-shot for faster eliminations.
        late_game_threshold = int(getattr(config, "FIGHTER_ARENA_LATE_GAME_THRESHOLD", 400))
        late_game_damage = float(getattr(config, "FIGHTER_ARENA_LATE_GAME_ATTACK_DAMAGE", 15))
        one_shot_threshold = int(getattr(config, "FIGHTER_ARENA_ONE_SHOT_THRESHOLD", 200))
        one_shot_damage = float(getattr(config, "FIGHTER_ARENA_ONE_SHOT_DAMAGE", 40))

        if alive_count <= late_game_threshold:
            damage = late_game_damage
        elif alive_count > one_shot_threshold:
            damage = one_shot_damage
        else:
            damage = self.attack_stat

        killed = target.take_damage(damage, self)
        self.damage_dealt += damage

        if killed:
            self.kills += 1

        # Apply knockback to target
        if distance > 0:
            knockback_dx = dx / distance
            knockback_dy = dy / distance
            target.apply_knockback(knockback_dx, knockback_dy, self.knockback_stat)

        return True

    def take_damage(self, damage: float, attacker: 'Fighter' = None) -> bool:
        """
        Take damage from an attack

        Args:
            damage: Amount of damage to take
            attacker: Fighter who dealt the damage (optional)

        Returns:
            True if this killed the fighter
        """
        self.current_hp -= damage
        self.damage_taken += damage

        if self.current_hp <= 0:
            self.current_hp = 0
            self.eliminate()
            return True

        return False

    def apply_knockback(self, dx: float, dy: float, knockback_power: float):
        """
        Apply knockback from being hit

        Args:
            dx: Normalized X direction of knockback
            dy: Normalized Y direction of knockback
            knockback_power: Knockback stat of attacker
        """
        # Apply push velocity (knockback / 10 pixels for smaller knockback)
        push_distance = knockback_power / 10.0
        self.push_vx += dx * push_distance
        self.push_vy += dy * push_distance

        # Apply stun (knockback * 0.8 frames)
        self.knockback_frames_remaining = int(knockback_power * 0.8)

    def regenerate(self, dt: float):
        """
        Regenerate HP over time

        Args:
            dt: Delta time in seconds
        """
        if not self.alive:
            return

        if self.current_hp < self.max_hp:
            # Divide regeneration stat by 2 for balanced healing
            regen_amount = (self.regeneration_stat / 2.0) * dt
            self.current_hp = min(self.max_hp, self.current_hp + regen_amount)

    def update_fighter(self, dt: float, arena_rect: Tuple[int, int, int, int],
                      all_fighters: List['Fighter'], current_time: float,
                      combat_enabled: bool = True, alive_count_hint: int = None,
                      simplified_mode: bool = False):
        """
        Update fighter state each frame (Fighter Arena specific)

        Args:
            dt: Delta time in seconds
            arena_rect: (x, y, width, height) of the arena
            all_fighters: List of all fighters for targeting
            current_time: Current game time
            combat_enabled: Whether combat is allowed (False during intro/countdown)
            alive_count_hint: Optional precomputed alive count to avoid O(n) per fighter
            simplified_mode: Disable combat/targeting for high-count performance mode
        """
        if not self.alive:
            # Handle fade out animation
            fade_elapsed = current_time - self.elimination_time
            if fade_elapsed < config.FADE_DURATION:
                progress = fade_elapsed / config.FADE_DURATION
                self.alpha = int(255 * (1 - progress))
            return

        if simplified_mode:
            self.knockback_frames_remaining = 0
            self.attack_animation_frames = 0
            self.is_attacking = False
            self.target_follower = None
            speed_multiplier = getattr(config, "FIGHTER_ARENA_SIMPLIFIED_SPEED_MULTIPLIER", 2.5)
            turn_chance = getattr(config, "FIGHTER_ARENA_SIMPLIFIED_TURN_CHANCE", 0.12)
            self._random_movement_fighter(dt, speed_multiplier=speed_multiplier, turn_chance=turn_chance)
        elif not combat_enabled:
            # Countdown/intro should avoid expensive target searches.
            self.target_follower = None
            self._random_movement_fighter(dt, speed_multiplier=1.0, turn_chance=0.05)
        else:
            # Decrement knockback stun
            if self.knockback_frames_remaining > 0:
                self.knockback_frames_remaining -= 1

            # Decrement attack animation
            if self.attack_animation_frames > 0:
                self.attack_animation_frames -= 1
                if self.attack_animation_frames == 0:
                    self.is_attacking = False

            # Regenerate HP
            self.regenerate(dt)

            # Choose target if we don't have one or target is dead.
            # Also occasionally re-target (0.2% chance per frame) to break circular patterns.
            if self.target_follower is None or not self.target_follower.alive or random.random() < 0.002:
                self._choose_target_fighter(all_fighters)

            # Move toward target
            if self.target_follower and self.target_follower.alive:
                self._move_toward_target_fighter(dt)

                # Try to attack if in range (only if combat is enabled)
                if combat_enabled and isinstance(self.target_follower, Fighter):
                    # Use precomputed alive count when provided (huge speedup at 30k+ fighters)
                    alive_count = alive_count_hint if alive_count_hint is not None else sum(1 for f in all_fighters if f.alive)
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

        # Clamp position to arena bounds
        self.x = max(arena_x + radius, min(arena_x + arena_w - radius, self.x))
        self.y = max(arena_y + radius, min(arena_y + arena_h - radius, self.y))

        # Bounce off walls
        if self.x <= arena_x + radius or self.x >= arena_x + arena_w - radius:
            self.vx *= -0.5
            self.push_vx *= -0.5
        if self.y <= arena_y + radius or self.y >= arena_y + arena_h - radius:
            self.vy *= -0.5
            self.push_vy *= -0.5

    def _choose_target_fighter(self, all_fighters: list):
        """
        Choose a target with some randomness to prevent circular chasing

        OPTIMIZED: Sample first, filter second for massive speedup.

        Args:
            all_fighters: List of all fighters
        """
        # MEGA OPTIMIZATION: Sample BEFORE filtering (not after!)
        MAX_SEARCH_DISTANCE = 500  # Don't chase enemies too far
        SAMPLE_SIZE = 200  # Check at most 200 fighters

        # Sample first (much faster than filtering all!)
        if len(all_fighters) > SAMPLE_SIZE * 2:
            sample_pool = random.sample(all_fighters, SAMPLE_SIZE)
        else:
            sample_pool = all_fighters

        # Filter the sample (not the full list!)
        alive_fighters = [f for f in sample_pool if f.alive and f != self]
        if not alive_fighters:
            self.target_follower = None
            return

        search_pool = alive_fighters

        # 70% chance to pick nearest, 30% chance to pick random target
        if random.random() < 0.7:
            # Find nearest fighter using squared distance (avoid sqrt)
            min_distance_sq = float('inf')
            nearest = None
            max_distance_sq = MAX_SEARCH_DISTANCE * MAX_SEARCH_DISTANCE

            for fighter in search_pool:
                dx = fighter.x - self.x
                dy = fighter.y - self.y
                distance_sq = dx * dx + dy * dy

                # Early reject if too far
                if distance_sq > max_distance_sq:
                    continue

                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
                    nearest = fighter

            # If no nearby target found, pick random from full list
            if nearest is None and alive_fighters:
                self.target_follower = random.choice(alive_fighters)
            else:
                self.target_follower = nearest
        else:
            # Pick a random target
            self.target_follower = random.choice(alive_fighters)

    def _move_toward_target_fighter(self, dt: float):
        """
        Move toward target using fighter's speed stat

        Args:
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

        # Add significant randomness to prevent circular chasing patterns
        # Higher randomness when far from target, less when close
        randomness_factor = min(1.0, distance / 100.0) * 0.8 + 0.2
        random_angle = (random.random() - 0.5) * math.pi * randomness_factor
        cos_r = math.cos(random_angle)
        sin_r = math.sin(random_angle)
        new_dx = dx * cos_r - dy * sin_r
        new_dy = dx * sin_r + dy * cos_r

        # Occasionally pick a completely random direction (5% chance)
        if random.random() < 0.05:
            rand_angle = random.random() * 2 * math.pi
            new_dx = math.cos(rand_angle)
            new_dy = math.sin(rand_angle)

        # Use fighter's speed stat instead of BASE_SPEED
        movement_speed = self.get_movement_speed()
        target_vx = new_dx * movement_speed
        target_vy = new_dy * movement_speed

        # Apply movement with smooth interpolation
        smoothing = 0.15
        self.vx += (target_vx - self.vx) * smoothing
        self.vy += (target_vy - self.vy) * smoothing

    def _random_movement_fighter(self, dt: float, speed_multiplier: float = 1.0, turn_chance: float = 0.02):
        """
        Apply random movement when no target

        Args:
            dt: Delta time
            speed_multiplier: Movement speed multiplier
            turn_chance: Probability to pick a new direction each frame
        """
        if random.random() < turn_chance:
            angle = random.random() * 2 * math.pi
            movement_speed = self.get_movement_speed() * speed_multiplier
            target_vx = math.cos(angle) * movement_speed
            target_vy = math.sin(angle) * movement_speed

            smoothing = 0.15
            self.vx += (target_vx - self.vx) * smoothing
            self.vy += (target_vy - self.vy) * smoothing

    def get_hp_percentage(self) -> float:
        """Get current HP as percentage (0.0 to 1.0)"""
        return self.current_hp / self.max_hp if self.max_hp > 0 else 0.0

    def get_stats_summary(self) -> dict:
        """Get summary of fighter's stats"""
        return {
            "hp": f"{self.current_hp:.0f}/{self.max_hp}",
            "speed": self.speed_stat,
            "attack": self.attack_stat,
            "regen": self.regeneration_stat,
            "knockback": self.knockback_stat,
            "attack_speed": f"{self.get_attacks_per_second():.1f}/s",
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "kills": self.kills
        }

    def __repr__(self):
        status = "ALIVE" if self.alive else "ELIMINATED"
        hp_str = f"HP:{self.current_hp:.0f}/{self.max_hp}"
        return f"Fighter({self.username}, {status}, {hp_str}, pos=({self.x:.1f}, {self.y:.1f}))"
