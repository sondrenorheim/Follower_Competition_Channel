"""
Lava Platform Player - follower behavior for reaching the safe platform.
"""

import math
import random
from typing import Tuple

import config
from shared.entity_template import EntityTemplate


class LavaPlatformPlayer(EntityTemplate):
    """Player that must reach the safe platform before lava arrives."""

    def _init_entity(self, follower_data: dict):
        """Initialize player-specific attributes."""
        avatar = follower_data.get("avatar")
        if avatar and self.avatar_image is None:
            self.avatar_image = avatar

        self.on_platform = False
        self.target_position = None
        self.panic_mode = False

        self.wander_angle = random.uniform(0, 2 * math.pi)
        self.wander_timer = 0.0
        self.wander_change_interval = random.uniform(1.0, 2.5)

    def update(self, dt: float, arena, phase: str, time_remaining: float = 0.0):
        """
        Update player state based on game phase.

        Args:
            dt: Delta time
            arena: Game arena reference
            phase: Current round phase ("waiting", "scramble", "lava", "resolve")
            time_remaining: Seconds until lava arrives
        """
        if not self.alive:
            self.update_fade()
            return

        if phase == "waiting":
            self._update_waiting(dt, arena)
        elif phase == "scramble":
            self._update_scramble(dt, arena, time_remaining)
        elif phase in ("lava", "resolve"):
            pass

        self._check_platform_position(arena)

    def _update_waiting(self, dt: float, arena):
        """Wander randomly during waiting phase (between rounds)."""
        self.wander_timer += dt
        if self.wander_timer >= self.wander_change_interval:
            self.wander_timer = 0.0
            self.wander_change_interval = random.uniform(1.0, 2.5)
            self.wander_angle = random.uniform(0, 2 * math.pi)

        speed = getattr(config, "LAVA_PLATFORM_WANDER_SPEED", 40.0)
        jitter = getattr(config, "LAVA_PLATFORM_WANDER_JITTER", 0.2)

        dx = math.cos(self.wander_angle)
        dy = math.sin(self.wander_angle)

        if jitter:
            dx += random.uniform(-jitter, jitter)
            dy += random.uniform(-jitter, jitter)
            mag = math.hypot(dx, dy)
            if mag > 1e-3:
                dx /= mag
                dy /= mag

        self.x += dx * speed * dt
        self.y += dy * speed * dt

        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

        # Push out of obstacles
        self.x, self.y = arena.get_obstacle_push(self.x, self.y, self.radius)

    def _update_scramble(self, dt: float, arena, time_remaining: float):
        """
        Rush to platform during scramble phase.
        Intensity increases as time runs out.
        Stop moving once safely on platform to prevent stacking in center.
        """
        if not arena.safe_platform or not arena.safe_platform.active:
            return

        platform = arena.safe_platform
        target = platform.center

        # Check if player is safely on platform (with margin from edge)
        dx_to_center = self.x - target[0]
        dy_to_center = self.y - target[1]
        dist_to_center = math.hypot(dx_to_center, dy_to_center)

        # Player is safe if their center + radius fits within platform with some margin
        safety_margin = self.radius + 5  # Extra 5px margin from edge
        is_safely_on_platform = dist_to_center + safety_margin < platform.radius

        # If safely on platform, stop moving toward center - just maintain position
        if is_safely_on_platform:
            return

        panic_threshold = getattr(config, "LAVA_PLATFORM_PANIC_THRESHOLD", 3.0)
        self.panic_mode = time_remaining <= panic_threshold

        if self.panic_mode:
            speed = getattr(config, "LAVA_PLATFORM_PANIC_SPEED", 120.0)
        else:
            speed = getattr(config, "LAVA_PLATFORM_MOVE_SPEED", 80.0)

        self._move_toward(target, speed, dt)
        self.x, self.y = arena.clamp_position(self.x, self.y, self.radius)

        # Push out of obstacles
        self.x, self.y = arena.get_obstacle_push(self.x, self.y, self.radius)

    def _check_platform_position(self, arena):
        """Update on_platform flag based on current position."""
        if not arena.safe_platform or not arena.safe_platform.active:
            self.on_platform = False
            return

        self.on_platform = arena.is_on_platform(self.x, self.y, self.radius)

    def _move_toward(self, target: Tuple[float, float], speed: float, dt: float):
        """Move toward a target position with jitter."""
        dx = target[0] - self.x
        dy = target[1] - self.y
        dist = math.hypot(dx, dy)

        if dist < 1e-3:
            return

        nx = dx / dist
        ny = dy / dist

        jitter = getattr(config, "LAVA_PLATFORM_WANDER_JITTER", 0.2)
        if jitter and not self.panic_mode:
            nx += random.uniform(-jitter, jitter)
            ny += random.uniform(-jitter, jitter)
            jitter_mag = math.hypot(nx, ny)
            if jitter_mag > 1e-3:
                nx /= jitter_mag
                ny /= jitter_mag

        self.x += nx * speed * dt
        self.y += ny * speed * dt
