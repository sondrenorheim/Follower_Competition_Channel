"""
Team Fighter Module
Extends Fighter with team affiliation and respawn capability
"""

import math
import random
import time
from typing import Tuple, List, Optional
from enum import Enum

import config
from fighter_arena.fighter import Fighter


class Team(Enum):
    """Team identifiers with associated colors"""
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"


# Team colors (RGB)
TEAM_COLORS = {
    Team.RED: (220, 50, 50),
    Team.BLUE: (50, 100, 220),
    Team.GREEN: (50, 180, 50),
    Team.YELLOW: (220, 200, 50),
}


class TeamFighter(Fighter):
    """
    Fighter with team affiliation for team battle mode.
    Extends Fighter with:
    - Team assignment and team-colored ring
    - Respawn capability for between-phase revivals
    - Team-aware targeting (won't attack teammates)
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float], team: Team):
        """
        Initialize a team fighter

        Args:
            follower_data: Dictionary containing follower info
            position: (x, y) starting position
            team: Team enum value
        """
        # Temporarily override stats to use team battle stats
        original_default_stats = config.FIGHTER_DEFAULT_STATS
        original_stat_boosts = config.FIGHTER_STAT_BOOSTS

        config.FIGHTER_DEFAULT_STATS = config.TEAM_BATTLE_DEFAULT_STATS
        config.FIGHTER_STAT_BOOSTS = config.TEAM_BATTLE_STAT_BOOSTS

        super().__init__(follower_data, position)

        # Restore original stats
        config.FIGHTER_DEFAULT_STATS = original_default_stats
        config.FIGHTER_STAT_BOOSTS = original_stat_boosts

        # Team assignment
        self.team = team
        self.team_color = TEAM_COLORS[team]

        # Override color to match team color when no avatar
        if not self.avatar_image:
            self.color = self.team_color

        # Disable knockback for team battle
        self.knockback_stat = 0

        # Store spawn position for respawning
        self.spawn_x = position[0]
        self.spawn_y = position[1]

        # Track which phase the fighter was eliminated in
        self.eliminated_in_phase = None

        # Team battle stats
        self.team_kills = 0  # Kills against enemy teams

        # Free-for-all mode flag (when True, can attack teammates)
        self.freeforall_mode = False

        # Current opponent team (only target this team during semifinals/finals)
        # None means target any enemy team
        self.current_opponent_team = None

        # Targeting enabled flag (False during intro/countdown phases)
        self.targeting_enabled = False

        # Store death position for revival at same spot
        self.death_x = position[0]
        self.death_y = position[1]

        # Speed multiplier for team battle (can be set externally)
        self.speed_multiplier = 1.0

    def respawn(self, position: Optional[Tuple[float, float]] = None):
        """
        Respawn the fighter with full health at given position or spawn point

        Args:
            position: Optional (x, y) position. Uses spawn position if not provided.
        """
        # Restore alive state
        self.alive = True
        self.alpha = 255
        self.elimination_time = None

        # Reset HP
        self.current_hp = self.max_hp

        # Reset position
        if position:
            self.x, self.y = position
        else:
            self.x = self.spawn_x
            self.y = self.spawn_y

        # Reset velocity
        self.vx = 0
        self.vy = 0
        self.push_vx = 0
        self.push_vy = 0

        # Reset combat state
        self.knockback_frames_remaining = 0
        self.is_attacking = False
        self.attack_animation_frames = 0
        self.last_attack_time = 0

        # Reset target
        self.target_follower = None

        # Mark surface for redraw
        self.surface_needs_update = True

        # Reset spawn time for survival tracking
        self.spawn_time = time.time()

    def set_spawn_position(self, x: float, y: float):
        """Update the spawn position"""
        self.spawn_x = x
        self.spawn_y = y

    def _choose_target_fighter(self, all_fighters: list):
        """
        Choose a target. In normal mode, only targets the current opponent team.
        In free-for-all mode, targets anyone.
        When targeting is disabled, moves randomly without a target.

        OPTIMIZED: Uses sampling and distance cutoff for 100-1000x faster targeting.

        Args:
            all_fighters: List of all fighters
        """
        # If targeting is disabled (intro/countdown), don't pick any target
        if not self.targeting_enabled:
            self.target_follower = None
            return

        # MEGA OPTIMIZATION: Sample fighters BEFORE filtering
        # Instead of filtering ALL fighters (O(n)), then sampling,
        # we sample first, then filter. Much faster for large counts!
        aggressive = getattr(self, "aggressive_mode", False)
        if aggressive:
            MAX_SEARCH_DISTANCE = 1_000_000  # Entire arena
            SAMPLE_SIZE = len(all_fighters)  # Check all
        else:
            MAX_SEARCH_DISTANCE = 1200  # Much wider search in normal mode to find enemies faster
            # Use smaller sample at very high counts to keep targeting cheap
            SAMPLE_SIZE = config.TEAM_BATTLE_TARGET_SAMPLE_SIZE if len(all_fighters) > 2000 else 300

        # For large player counts, sample first (much faster!)
        if len(all_fighters) > SAMPLE_SIZE * 2:
            sample_pool = random.sample(all_fighters, SAMPLE_SIZE)
        else:
            sample_pool = all_fighters

        # Wall-aware row/column filtering to avoid targeting across closed walls
        def _same_row(t1, t2):
            top = (t1 in (Team.RED, Team.BLUE)) and (t2 in (Team.RED, Team.BLUE))
            bottom = (t1 in (Team.GREEN, Team.YELLOW)) and (t2 in (Team.GREEN, Team.YELLOW))
            return top or bottom

        def _same_col(t1, t2):
            left = (t1 in (Team.RED, Team.GREEN)) and (t2 in (Team.RED, Team.GREEN))
            right = (t1 in (Team.BLUE, Team.YELLOW)) and (t2 in (Team.BLUE, Team.YELLOW))
            return left or right

        horizontal_closed = getattr(self, "horizontal_wall_closed", False)
        vertical_closed = getattr(self, "vertical_wall_closed", False)

        def wall_ok(target_team: Team):
            if horizontal_closed and not _same_row(self.team, target_team):
                return False
            if vertical_closed and not _same_col(self.team, target_team):
                return False
            return True

        # NOW filter the sample (not the full list!)
        if self.freeforall_mode:
            alive_targets = [f for f in sample_pool
                            if f.alive and f != self
                            and (not horizontal_closed or _same_row(self.team, f.team))
                            and (not vertical_closed or _same_col(self.team, f.team))]
        elif self.current_opponent_team is not None:
            # Only target the specific opponent team (semifinals/finals)
            alive_targets = [f for f in sample_pool
                            if f.alive and f != self
                            and isinstance(f, TeamFighter)
                            and f.team == self.current_opponent_team
                            and wall_ok(f.team)]
        else:
            # Fallback: target any enemy team
            alive_targets = [f for f in sample_pool
                            if f.alive and f != self
                            and isinstance(f, TeamFighter)
                            and f.team != self.team
                            and wall_ok(f.team)]

        if not alive_targets:
            self.target_follower = None
            return

        search_pool = alive_targets

        # 70% chance to pick nearest, 30% chance to pick random target
        if random.random() < 0.7:
            # Find nearest target using squared distance (faster than sqrt)
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

            # If no nearby target found within range, pick random from full list
            if nearest is None and alive_targets:
                self.target_follower = random.choice(alive_targets)
            else:
                self.target_follower = nearest
        else:
            # Pick a random target
            self.target_follower = random.choice(alive_targets)

    def attack(self, target: 'TeamFighter', current_time: float, combat_enabled: bool = True, alive_count: int = 0) -> bool:
        """
        Attack another fighter. In normal mode, only attacks enemies.
        In free-for-all mode, can attack anyone.

        Args:
            target: Fighter to attack
            current_time: Current game time
            combat_enabled: Whether combat is currently allowed
            alive_count: Number of alive fighters (for special move scaling)

        Returns:
            True if attack landed
        """
        # Don't attack teammates unless in freeforall mode
        if not self.freeforall_mode:
            if isinstance(target, TeamFighter) and target.team == self.team:
                return False

        # Replicate Fighter.attack with aggressive-mode damage tweak
        if not self.can_attack(current_time, combat_enabled):
            return False

        if not target.alive:
            return False

        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > config.FIGHTER_ATTACK_RANGE:
            return False

        self.last_attack_time = current_time
        self.is_attacking = True
        self.attack_animation_frames = 10

        aggressive = getattr(self, "aggressive_mode", False)
        if aggressive:
            damage = 20
        elif alive_count > 200:
            damage = 40
        else:
            damage = self.attack_stat

        killed = target.take_damage(damage, self)
        self.damage_dealt += damage

        if killed:
            self.kills += 1
            if not self.freeforall_mode:
                self.team_kills += 1

        if distance > 0:
            knockback_dx = dx / distance
            knockback_dy = dy / distance
            target.apply_knockback(knockback_dx, knockback_dy, self.knockback_stat)

        return True

    def _move_toward_target_fighter(self, dt: float):
        """
        Override to reduce retarget jitter by limiting how often we fully recompute direction.
        This keeps CPU lower without changing behavior much.
        """
        if not self.target_follower:
            return

        # Simple cooldown on direction recalculation
        if not hasattr(self, "_direction_cooldown"):
            self._direction_cooldown = 0

        cooldown_reset = 1 if getattr(self, "aggressive_mode", False) else 2

        if self._direction_cooldown > 0:
            self._direction_cooldown -= 1
        else:
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
            randomness_factor = min(1.0, distance / 100.0) * 0.8 + 0.2
            random_angle = (random.random() - 0.5) * math.pi * randomness_factor
            cos_r = math.cos(random_angle)
            sin_r = math.sin(random_angle)
            self._dir_dx = dx * cos_r - dy * sin_r
            self._dir_dy = dx * sin_r + dy * cos_r

            # Occasionally pick a completely random direction (5% chance)
            if random.random() < 0.05:
                rand_angle = random.random() * 2 * math.pi
                self._dir_dx = math.cos(rand_angle)
                self._dir_dy = math.sin(rand_angle)

            # Reset cooldown
            self._direction_cooldown = cooldown_reset

        # Use fighter's speed stat instead of BASE_SPEED
        movement_speed = self.get_movement_speed()
        target_vx = self._dir_dx * movement_speed
        target_vy = self._dir_dy * movement_speed

        # Apply movement with smooth interpolation
        smoothing = 0.15
        self.vx += (target_vx - self.vx) * smoothing
        self.vy += (target_vy - self.vy) * smoothing

    def take_damage(self, damage: float, attacker: 'TeamFighter' = None) -> bool:
        """
        Override to store death position when eliminated

        Args:
            damage: Amount of damage to take
            attacker: Fighter who dealt the damage

        Returns:
            True if this killed the fighter
        """
        was_alive = self.alive
        result = super().take_damage(damage, attacker)

        # Store death position if just died
        if was_alive and not self.alive:
            self.death_x = self.x
            self.death_y = self.y

        return result

    def get_movement_speed(self) -> float:
        """
        Override to apply speed multiplier for team battle
        """
        base_speed = super().get_movement_speed()
        return base_speed * self.speed_multiplier

    def _random_movement_fighter(self, dt: float):
        """
        Make idle fighters wander more so they keep moving toward encounters.
        """
        aggressive = getattr(self, "aggressive_mode", False)
        change_chance = 0.10 if aggressive else 0.05

        # More frequent direction changes keep fighters roaming
        if random.random() < change_chance:
            angle = random.random() * 2 * math.pi
            movement_speed = self.get_movement_speed()
            target_vx = math.cos(angle) * movement_speed
            target_vy = math.sin(angle) * movement_speed

            smoothing = 0.25
            self.vx += (target_vx - self.vx) * smoothing
            self.vy += (target_vy - self.vy) * smoothing
        else:
            # If nearly stationary, give a small nudge to avoid parking
            speed_sq = self.vx * self.vx + self.vy * self.vy
            if speed_sq < 0.01:
                angle = random.random() * 2 * math.pi
                movement_speed = self.get_movement_speed() * 0.35
                self.vx += math.cos(angle) * movement_speed
                self.vy += math.sin(angle) * movement_speed

    def __repr__(self):
        status = "ALIVE" if self.alive else "ELIMINATED"
        hp_str = f"HP:{self.current_hp:.0f}/{self.max_hp}"
        return f"TeamFighter({self.username}, {self.team.value}, {status}, {hp_str})"
