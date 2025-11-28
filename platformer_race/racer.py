"""
PlatformerRacer class - extends Follower for vertical climbing platformer racing.

Adds platformer-specific attributes: jumping, climbing, progress tracking, checkpoints.
"""

import random
import time
from enum import Enum
from battle_royale.follower import Follower
import config


class RacerState(Enum):
    """Racer states for vertical climbing platformer"""
    STANDING = "standing"      # On platform, can jump or grab
    JUMPING = "jumping"         # In air, moving upward
    FALLING = "falling"         # In air, moving downward
    CLIMBING = "climbing"       # On ladder/rope/wall, can move up/down


class PlatformerRacer(Follower):
    """Follower adapted for platformer racing"""

    def __init__(self, follower_data, position):
        """
        Create a platformer racer

        Args:
            follower_data: Dictionary with 'id', 'username', 'avatar', 'color'
            position: Tuple of (x, y) starting position
        """
        super().__init__(follower_data, position)

        # Override radius (use config)
        self.radius = config.FOLLOWER_RADIUS

        # Physics state
        self.on_ground = False
        self.state = RacerState.FALLING  # Start falling onto starting platform
        # vx, vy already defined in parent

        # Climbing state
        self.current_climbable = None  # Currently climbing object
        self.climb_direction = 0  # 1 = up, -1 = down, 0 = stationary

        # Racing state
        self.progress = 0.0  # 0.0 to 1.0
        self.checkpoint_index = 0  # Current checkpoint
        self.checkpoint_position = None  # Last checkpoint position for respawn
        self.finished = False
        self.finish_time = 0.0
        self.placement = 0  # Final placement (1st, 2nd, etc.)

        # Per-racer stats (slight variation for natural spread)
        self.horizontal_speed = random.uniform(120, 170)  # pixels/sec (increased for longer jumps)
        self.jump_velocity = random.uniform(-420, -460)  # upward velocity (slightly increased for better jumps)
        self.jump_cooldown = 0.2  # seconds
        self.last_jump_time = 0.0

        # AI mistake chance (5-20% error rate)
        self.mistake_chance = random.uniform(0.05, 0.20)

        # Floor tracking for dynamic direction changes
        self.current_floor = 1
        self.target_direction = "right"  # "left" or "right"

        # Initialize floor tracking based on starting position
        self.update_floor_tracking()

    def attempt_jump(self, current_time):
        """
        Attempt to jump if conditions are met

        Args:
            current_time: Current game time

        Returns:
            True if jumped, False otherwise
        """
        if self.on_ground and (current_time - self.last_jump_time >= self.jump_cooldown):
            self.vy = self.jump_velocity  # Negative = upward
            self.on_ground = False
            self.last_jump_time = current_time
            return True
        return False

    def calculate_progress(self, level):
        """
        Calculate race completion percentage (vertical climbing)

        Progress is based on vertical distance climbed

        Args:
            level: PlatformerLevel instance

        Returns:
            Float between 0.0 and 1.0
        """
        start_y = level.start_y  # Starting Y position (450, bottom)
        goal_y = level.goal_y    # Goal Y position (50, top)

        if start_y <= goal_y:
            return 0.0

        # Progress = how far up they've climbed
        vertical_distance = start_y - self.y
        total_distance = start_y - goal_y

        progress = vertical_distance / total_distance
        return max(0.0, min(1.0, progress))

    def update_floor_tracking(self):
        """
        Update current floor and target direction based on Y position

        5-Floor layout (extended viewport):
        - Floor 1 (Y > 540): Ground floor (Y=600) - move RIGHT
        - Floor 2 (Y 420-540): Lower mid (Y=480) - move LEFT
        - Floor 3 (Y 330-420): Center (Y=360, racers at ~346) - move RIGHT
        - Floor 4 (Y 160-330): Upper mid (Y=240) + stairs (Y=325, racers at ~313) - move LEFT
        - Floor 5 (Y <= 160): Top floor (Y=120) + finish - move RIGHT

        Thresholds carefully set between racer positions:
        - Floor 3 racers at Y≈346, stairs at Y≈313 → threshold at 330
        """
        old_floor = self.current_floor
        old_direction = self.target_direction

        if self.y > 540:
            # Ground floor - move right
            self.current_floor = 1
            self.target_direction = "right"
        elif self.y > 420:
            # Lower mid floor - move left
            self.current_floor = 2
            self.target_direction = "left"
        elif self.y > 330:
            # Center floor - move right (Y=346 on platforms)
            self.current_floor = 3
            self.target_direction = "right"
        elif self.y > 160:
            # Upper mid floor - move left (includes stairs at Y=325)
            self.current_floor = 4
            self.target_direction = "left"
        else:
            # Top floor and finish area - move right
            self.current_floor = 5
            self.target_direction = "right"

    def check_finish_line(self, level, current_time):
        """
        Check if racer reached the goal

        Args:
            level: PlatformerLevel instance
            current_time: Current game time

        Returns:
            True if just finished, False otherwise
        """
        if not self.finished and level.goal and level.goal.check_reached(self):
            self.finished = True
            self.finish_time = current_time
            self.progress = 1.0
            return True
        return False

    def respawn_at_start(self, start_x=70, start_y=580):
        """
        Respawn racer at starting position (bottom-left)

        Args:
            start_x: X position to respawn at (default 70)
            start_y: Y position to respawn at (default 580)
        """
        self.x = start_x
        self.y = start_y
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.state = RacerState.FALLING
        self.current_climbable = None
        self.climb_direction = 0
        # Update floor tracking after respawn
        self.update_floor_tracking()

    def respawn_at_checkpoint(self, level):
        """
        Respawn racer at last checkpoint reached, or at start if no checkpoint reached

        Args:
            level: PlatformerLevel instance
        """
        # If racer has reached a checkpoint, respawn there
        if self.checkpoint_index > 0:
            # Find the checkpoint with matching index
            for checkpoint in level.checkpoints:
                if checkpoint.index == self.checkpoint_index:
                    checkpoint.respawn_racer(self)
                    self.update_floor_tracking()
                    return

        # No checkpoint reached yet, respawn at start
        self.respawn_at_start()

    def update_racer(self, dt, level, camera, physics, ai, current_time):
        """
        Main update loop for racer (vertical climbing version)

        Args:
            dt: Delta time in seconds
            level: PlatformerLevel instance
            camera: PlatformerCamera instance
            physics: PlatformerPhysics instance
            ai: JumpAI instance (vertical climbing AI)
            current_time: Current game time
        """
        if not self.alive or self.finished:
            return

        # Get all platforms
        all_platforms = level.platforms

        # AI decides action based on state
        action = ai.decide_action(self, level)

        # SIMPLE LADDER LOGIC: Force upward movement when near ladder between Floor 2 and 3
        # Ladder is at x=35, y=360, height=120, width=20
        # Climb until reaching Floor 3 (y=360)
        # Use Y range check instead of floor check to handle threshold changes
        if 25 <= self.x <= 65 and 360 < self.y < 480:
            # Player is in ladder area - force them up until reaching Floor 3
            climb_speed = 120.0  # pixels per second
            self.y -= climb_speed * dt
            self.vy = 0  # Cancel gravity
            self.on_ground = False
            # Skip normal physics when auto-climbing
            self.progress = self.calculate_progress(level)
            self.check_finish_line(level, current_time)
            return

        # FLOOR 4 LADDER AUTO-CLIMB: Force upward movement when near ladder between Floor 4 and 5
        # Ladder is at x=35, y=120, height=120, width=20
        # Climb until reaching Floor 5 (y=120)
        # Use Y range check instead of floor check to handle threshold changes
        if 25 <= self.x <= 65 and 120 < self.y < 240:
            # Player is in ladder area - force them up until reaching Floor 5
            climb_speed = 120.0  # pixels per second
            self.y -= climb_speed * dt
            self.vy = 0  # Cancel gravity
            self.on_ground = False
            # Skip normal physics when auto-climbing
            self.progress = self.calculate_progress(level)
            self.check_finish_line(level, current_time)
            return

        # Execute action based on state
        if self.state == RacerState.CLIMBING:
            # Currently climbing
            if self.current_climbable:
                physics.update_climbing_movement(self, self.current_climbable, self.climb_direction, dt)

                # Check if should stop climbing
                if action != "climb_up" and action != "climb_down":
                    self.state = RacerState.FALLING
                    self.current_climbable = None
                    self.climb_direction = 0
        else:
            # Not climbing - normal physics
            if action == "climb_up" or action == "climb_down":
                # Try to grab climbable
                from .climbable import get_climbable_for_racer
                climbable = get_climbable_for_racer(self, level.get_all_climbables())

                # FORCE CLIMB on floor 2 left side if no climbable found
                if not climbable and self.current_floor == 2 and self.x < 120:
                    # Force find the ladder manually
                    all_climbables = level.get_all_climbables()
                    if len(all_climbables) > 0:
                        climbable = all_climbables[0]  # Use first climbable (should be the ladder)

                if climbable:
                    self.state = RacerState.CLIMBING
                    self.current_climbable = climbable
                    self.climb_direction = 1 if action == "climb_up" else -1
            elif action == "jump":
                # Jump AND maintain horizontal movement in floor direction
                jumped = self.attempt_jump(current_time)
                # Continue moving horizontally while jumping based on floor direction
                if self.target_direction == "right":
                    self.x += self.horizontal_speed * dt
                else:
                    self.x += -self.horizontal_speed * dt
            elif action == "walk_left":
                # Move left
                self.x += -self.horizontal_speed * dt
            elif action == "walk_right":
                # Move right
                self.x += self.horizontal_speed * dt
            elif action == "air_right":
                # Air control - move right with full control
                self.x += self.horizontal_speed * dt
            elif action == "air_left":
                # Air control - move left with full control
                self.x += -self.horizontal_speed * dt
            elif action == "air_brake":
                # Air control - slow down (reduce horizontal movement significantly)
                # Apply 10% of normal speed to allow fine positioning
                if self.target_direction == "right":
                    self.x += self.horizontal_speed * 0.1 * dt
                else:
                    self.x += -self.horizontal_speed * 0.1 * dt
            elif action == "air_continue":
                # Air control - continue in floor direction at full speed
                if self.target_direction == "right":
                    self.x += self.horizontal_speed * dt
                else:
                    self.x += -self.horizontal_speed * dt

            # Legacy air control (fallback for non-air actions while in air)
            if not self.on_ground and action not in ["climb_up", "climb_down", "jump", "air_right", "air_left", "air_brake", "air_continue"]:
                # In air but not from a jump or air command - still move in floor direction
                # Reduced air control (30% speed)
                if self.target_direction == "right":
                    self.x += self.horizontal_speed * 0.3 * dt
                else:
                    self.x += -self.horizontal_speed * 0.3 * dt

            # Update physics (gravity, vertical movement, collision)
            physics.update_racer_physics(self, all_platforms, dt)

            # Update state based on velocity
            if self.on_ground:
                self.state = RacerState.STANDING
                # Only update floor tracking when on ground to prevent direction changes mid-air
                self.update_floor_tracking()
            elif self.vy < 0:
                self.state = RacerState.JUMPING
            else:
                self.state = RacerState.FALLING

        # Update progress
        self.progress = self.calculate_progress(level)

        # Check goal reached
        self.check_finish_line(level, current_time)

        # Check checkpoint activation
        for checkpoint in level.checkpoints:
            checkpoint.check_activation(self)

        # Check spike collisions
        for spike in level.spikes:
            if spike.check_collision(self):
                # Hit spike - respawn at last checkpoint
                self.respawn_at_checkpoint(level)
                break

        # Check if fell off the bottom of the screen
        if self.y > level.height:
            # Fell off screen - respawn at last checkpoint
            self.respawn_at_checkpoint(level)
