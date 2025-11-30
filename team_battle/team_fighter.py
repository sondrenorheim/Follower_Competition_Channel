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

        Args:
            all_fighters: List of all fighters
        """
        # If targeting is disabled (intro/countdown), don't pick any target
        if not self.targeting_enabled:
            self.target_follower = None
            return

        # In freeforall mode, target anyone alive (including teammates)
        if self.freeforall_mode:
            alive_targets = [f for f in all_fighters if f.alive and f != self]
        elif self.current_opponent_team is not None:
            # Only target the specific opponent team (semifinals/finals)
            alive_targets = [f for f in all_fighters
                            if f.alive and f != self
                            and isinstance(f, TeamFighter)
                            and f.team == self.current_opponent_team]
        else:
            # Fallback: target any enemy team
            alive_targets = [f for f in all_fighters
                            if f.alive and f != self
                            and isinstance(f, TeamFighter)
                            and f.team != self.team]

        if not alive_targets:
            self.target_follower = None
            return

        # 70% chance to pick nearest, 30% chance to pick random target
        if random.random() < 0.7:
            # Find nearest target
            min_distance = float('inf')
            nearest = None

            for fighter in alive_targets:
                dx = fighter.x - self.x
                dy = fighter.y - self.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < min_distance:
                    min_distance = distance
                    nearest = fighter

            self.target_follower = nearest
        else:
            # Pick a random target
            self.target_follower = random.choice(alive_targets)

    def attack(self, target: 'TeamFighter', current_time: float, combat_enabled: bool = True) -> bool:
        """
        Attack another fighter. In normal mode, only attacks enemies.
        In free-for-all mode, can attack anyone.

        Args:
            target: Fighter to attack
            current_time: Current game time
            combat_enabled: Whether combat is currently allowed

        Returns:
            True if attack landed
        """
        # Don't attack teammates unless in freeforall mode
        if not self.freeforall_mode:
            if isinstance(target, TeamFighter) and target.team == self.team:
                return False

        # Call parent attack method
        result = super().attack(target, current_time, combat_enabled)

        # Track team kills separately (only count if not freeforall)
        if result and not target.alive and not self.freeforall_mode:
            self.team_kills += 1

        return result

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

    def __repr__(self):
        status = "ALIVE" if self.alive else "ELIMINATED"
        hp_str = f"HP:{self.current_hp:.0f}/{self.max_hp}"
        return f"TeamFighter({self.username}, {self.team.value}, {status}, {hp_str})"
