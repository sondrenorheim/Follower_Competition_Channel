"""
Team Fighter Module (open arena, no walls)
Team-aware fighter with sequential matchup targeting.
"""

import math
import random
from typing import Optional, Tuple
import pygame
import config
from fighter_arena import Fighter
from enum import Enum, auto


class Team(Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"


TEAM_COLORS = {
    Team.RED: (200, 50, 50),
    Team.BLUE: (50, 100, 220),
    Team.GREEN: (30, 170, 70),
    Team.YELLOW: (200, 170, 40),
}


class TeamFighter(Fighter):
    """
    Fighter that belongs to a team. Targeting respects current_opponent_team (sequential brackets)
    and freeforall_mode for the winning team.
    """

    def __init__(self, follower_data: dict, position: Tuple[float, float], team: Team):
        super().__init__(follower_data, position)
        self.team = team
        self.team_color = TEAM_COLORS[team]

        # Override with team battle stats
        stats = config.TEAM_BATTLE_DEFAULT_STATS
        boosts = config.TEAM_BATTLE_STAT_BOOSTS.get(self.username, {})
        self.max_hp = stats["hp"] + boosts.get("hp", 0)
        self.current_hp = self.max_hp
        self.speed_stat = stats["speed"] + boosts.get("speed", 0)
        self.attack_stat = stats["attack"] + boosts.get("attack", 0)
        self.regeneration_stat = stats["regeneration"] + boosts.get("regeneration", 0)
        self.knockback_stat = stats["knockback"] + boosts.get("knockback", 0)
        self.attack_speed_stat = stats["attack_speed"] + boosts.get("attack_speed", 0)

        # Team targeting state
        self.current_opponent_team: Optional[Team] = None
        self.freeforall_mode = False  # Set True for final FFA of winning team
        self.targeting_enabled = False

        # Movement smoothing - initialize with random direction
        angle = random.random() * math.tau
        self._dir_dx = math.cos(angle)
        self._dir_dy = math.sin(angle)
        # Remember spawn for potential reuse
        self.spawn_x, self.spawn_y = position

    def set_targeting_enabled(self, enabled: bool, opponent_team: Optional[Team] = None, freeforall: Optional[bool] = None):
        self.targeting_enabled = enabled
        # When entering free-for-all, clear opponent team and allow friendly targets
        if freeforall is not None:
            self.freeforall_mode = freeforall
            if freeforall:
                self.current_opponent_team = None
        else:
            self.current_opponent_team = opponent_team
        if not enabled:
            self.target_follower = None

    def respawn(self, position: Tuple[float, float]):
        """Respawn fighter at a given position with full HP."""
        self.alive = True
        self.current_hp = self.max_hp
        self.x, self.y = position
        self.vx = self.vy = 0.0
        self.target_follower = None
        self.last_attack_time = 0.0
        self.knockback_frames_remaining = 0
        self.is_attacking = False
        self.attack_animation_frames = 0

    def set_spawn_position(self, x: float, y: float):
        """Backward-compat: store a spawn position (not otherwise used in team mode)."""
        self.spawn_x = x
        self.spawn_y = y

    def _choose_target_fighter(self, all_fighters: list):
        """
        Choose a target. In normal mode, only targets the current opponent team.
        In free-for-all mode, targets anyone.
        When targeting is disabled, moves randomly without a target.
        Always scans the full list to stay aggressive.
        """
        if not self.targeting_enabled:
            self.target_follower = None
            return

        # Aggressive mode if set
        aggressive = getattr(self, "aggressive_mode", False)
        MAX_SEARCH_DISTANCE = 1_000_000 if aggressive else 10_000  # effectively whole arena
        sample_pool = all_fighters  # always consider full set to avoid idling

        # Filter sample according to mode/opponent
        if self.freeforall_mode:
            alive_targets = [f for f in sample_pool if f.alive and f is not self]
        elif self.current_opponent_team is not None:
            alive_targets = [f for f in sample_pool
                             if f.alive and f is not self
                             and isinstance(f, TeamFighter)
                             and f.team == self.current_opponent_team]
        else:
            alive_targets = [f for f in sample_pool
                             if f.alive and f is not self
                             and isinstance(f, TeamFighter)
                             and f.team != self.team]

        if not alive_targets:
            self.target_follower = None
            return

        # 70% nearest, 30% random
        if random.random() < 0.7:
            nearest = None
            min_distance_sq = float("inf")
            max_distance_sq = MAX_SEARCH_DISTANCE * MAX_SEARCH_DISTANCE
            for f in alive_targets:
                dx = f.x - self.x
                dy = f.y - self.y
                dist_sq = dx * dx + dy * dy
                if dist_sq < min_distance_sq and dist_sq <= max_distance_sq:
                    min_distance_sq = dist_sq
                    nearest = f
            if nearest is None and alive_targets:
                self.target_follower = random.choice(alive_targets)
            else:
                self.target_follower = nearest
        else:
            self.target_follower = random.choice(alive_targets)

    def _move_toward_target_fighter(self, dt: float, combat_enabled: bool, arena_rect: Tuple[int, int, int, int] = None):
        """Smooth pursuit toward target; idle random wander otherwise."""
        if not self.target_follower:
            # More frequent direction changes for active movement
            if random.random() < 0.05:
                angle = random.random() * math.tau
                self._dir_dx = math.cos(angle)
                self._dir_dy = math.sin(angle)

            # Wall avoidance - push away from walls to prevent sticking
            if arena_rect:
                left, top, arena_w, arena_h = arena_rect
                right = left + arena_w
                bottom = top + arena_h
                wall_avoid_distance = config.FOLLOWER_RADIUS * 4
                wall_avoid_strength = 0.15

                # Check proximity to each wall and add avoidance force
                if self.x - left < wall_avoid_distance:
                    # Too close to left wall - push right
                    push_strength = 1.0 - (self.x - left) / wall_avoid_distance
                    self._dir_dx += wall_avoid_strength * push_strength
                elif right - self.x < wall_avoid_distance:
                    # Too close to right wall - push left
                    push_strength = 1.0 - (right - self.x) / wall_avoid_distance
                    self._dir_dx -= wall_avoid_strength * push_strength

                if self.y - top < wall_avoid_distance:
                    # Too close to top wall - push down
                    push_strength = 1.0 - (self.y - top) / wall_avoid_distance
                    self._dir_dy += wall_avoid_strength * push_strength
                elif bottom - self.y < wall_avoid_distance:
                    # Too close to bottom wall - push up
                    push_strength = 1.0 - (bottom - self.y) / wall_avoid_distance
                    self._dir_dy -= wall_avoid_strength * push_strength

                # Normalize direction after adding avoidance
                mag = math.hypot(self._dir_dx, self._dir_dy)
                if mag > 0.1:
                    self._dir_dx /= mag
                    self._dir_dy /= mag

            # Apply center bias regardless of combat state to keep fighters from clustering at edges
            if arena_rect:
                arena_x, arena_y, arena_w, arena_h = arena_rect
                center_x = arena_x + arena_w * 0.5
                center_y = arena_y + arena_h * 0.5
                to_cx = center_x - self.x
                to_cy = center_y - self.y
                dist = math.hypot(to_cx, to_cy) or 1.0
                norm_cx = to_cx / dist
                norm_cy = to_cy / dist
                # Stronger bias during combat, lighter during countdown
                bias = 0.04 if combat_enabled else 0.02
                self._dir_dx = (1 - bias) * self._dir_dx + bias * norm_cx
                self._dir_dy = (1 - bias) * self._dir_dy + bias * norm_cy

            movement_speed = self.get_movement_speed()
            self.vx = self._dir_dx * movement_speed
            self.vy = self._dir_dy * movement_speed
            return

        dx = self.target_follower.x - self.x
        dy = self.target_follower.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-3:
            return

        movement_speed = self.get_movement_speed()
        smoothing = 0.12
        target_vx = (dx / dist) * movement_speed
        target_vy = (dy / dist) * movement_speed
        self.vx += (target_vx - self.vx) * smoothing
        self.vy += (target_vy - self.vy) * smoothing

    def update_fighter(self, dt: float, arena_rect: Tuple[int, int, int, int],
                       all_fighters: list, current_time: float,
                       combat_enabled: bool = True, gate_progress: float = 1.0):
        """
        Update fighter state.
        gate_progress ignored (no walls/gates).
        """
        if not self.alive:
            return

        # Target selection (only matters when combat enabled)
        if combat_enabled:
            self._choose_target_fighter(all_fighters)
        else:
            self.target_follower = None

        # Movement
        self._move_toward_target_fighter(dt, combat_enabled, arena_rect)
        # Apply physics similar to base Fighter.update (no safe zone), adapted for open arena
        self.x += self.push_vx
        self.y += self.push_vy
        self.push_vx *= self.stats['friction']
        self.push_vy *= self.stats['friction']

        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vx *= self.stats['friction']
        self.vy *= self.stats['friction']

        # Clamp to arena bounds - actively push away from walls instead of just bouncing
        left, top, right, bottom = arena_rect[0], arena_rect[1], arena_rect[0] + arena_rect[2], arena_rect[1] + arena_rect[3]
        radius = config.FOLLOWER_RADIUS
        if self.x < left + radius:
            self.x = left + radius
            self.vx = abs(self.vx) * 0.5  # Push right
            self._dir_dx = abs(self._dir_dx)  # Point away from wall
        elif self.x > right - radius:
            self.x = right - radius
            self.vx = -abs(self.vx) * 0.5  # Push left
            self._dir_dx = -abs(self._dir_dx)  # Point away from wall
        if self.y < top + radius:
            self.y = top + radius
            self.vy = abs(self.vy) * 0.5  # Push down
            self._dir_dy = abs(self._dir_dy)  # Point away from wall
        elif self.y > bottom - radius:
            self.y = bottom - radius
            self.vy = -abs(self.vy) * 0.5  # Push up
            self._dir_dy = -abs(self._dir_dy)  # Point away from wall

        # Regeneration
        if self.regeneration_stat > 0 and self.current_hp < self.max_hp:
            self.current_hp = min(self.max_hp, self.current_hp + (self.regeneration_stat * dt))

        # Attempt attack
        if self.target_follower and combat_enabled:
            self.attack(self.target_follower, current_time, combat_enabled, alive_count=len(all_fighters))

    def attack(self, target: 'TeamFighter', current_time: float, combat_enabled: bool = True, alive_count: int = 0) -> bool:
        """Override to prevent friendly fire and use team attack range."""
        if not self.target_follower or not self.targeting_enabled:
            return False
        # In free-for-all mode we can attack anyone; otherwise block friendly fire
        if isinstance(target, TeamFighter) and target.team == self.team and not self.freeforall_mode:
            return False
        return super().attack(target, current_time, combat_enabled, alive_count)
