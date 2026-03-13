import math
import random

import config
from shared import EntityTemplate


class FlappyFollower(EntityTemplate):
    def _init_entity(self, follower_data: dict):
        self.size = float(getattr(config, "FLAPPY_BIRD_SIZE", 16))
        self.radius = self.size * 0.5

        self.base_gravity = float(getattr(config, "FLAPPY_GRAVITY", 1200.0))
        self.base_flap_velocity = float(getattr(config, "FLAPPY_FLAP_VELOCITY", 380.0))
        self.max_fall_speed = float(getattr(config, "FLAPPY_MAX_FALL_SPEED", 520.0))
        self.flap_cooldown = float(getattr(config, "FLAPPY_FLAP_COOLDOWN", 0.18))
        self.reaction_distance = float(getattr(config, "FLAPPY_REACTION_DISTANCE", 260.0))
        self.flap_buffer = float(getattr(config, "FLAPPY_FLAP_BUFFER", 8.0))
        self.bias_scale = float(getattr(config, "FLAPPY_GAP_BIAS_SCALE", 0.35))
        self.target_jitter = float(getattr(config, "FLAPPY_TARGET_JITTER", 0.12))
        self.panic_margin = float(getattr(config, "FLAPPY_PANIC_MARGIN", 28.0))

        self.skill = random.uniform(0.55, 1.0)
        self.gravity = self.base_gravity * (0.9 + (1.0 - self.skill) * 0.35)
        self.flap_velocity = self.base_flap_velocity * (0.85 + 0.3 * self.skill)
        self.flap_cooldown *= 1.2 - 0.6 * self.skill
        self.miss_chance = (1.0 - self.skill) * 0.35
        self.bias_factor = random.uniform(-1.0, 1.0) * self.bias_scale
        self.jitter_factor = random.uniform(-1.0, 1.0) * self.target_jitter

        self.last_flap_time = -999.0
        self.elapsed = 0.0

        self.base_x = self.x
        self.pipes_passed = None
        self.x_sway_amplitude = float(getattr(config, "FLAPPY_X_SWAY_AMPLITUDE", 22.0))
        self.x_sway_speed = float(getattr(config, "FLAPPY_X_SWAY_SPEED", 1.4))
        self.x_sway_lerp = float(getattr(config, "FLAPPY_X_SWAY_LERP", 6.0))
        self.x_sway_jitter = float(getattr(config, "FLAPPY_X_SWAY_JITTER", 0.25))
        self.x_sway_phase = random.uniform(0.0, math.tau)
        self.x_sway_rate = self.x_sway_speed * (1.0 + random.uniform(-self.x_sway_jitter, self.x_sway_jitter))

    def update(self, dt, arena, next_pipe, game_time, difficulty=0.0):
        if not self.alive:
            self.update_fade()
            return

        self.elapsed += dt

        gravity_scale = 1.0 + difficulty * 0.15
        self.vy += self.gravity * gravity_scale * dt
        if self.vy > self.max_fall_speed:
            self.vy = self.max_fall_speed
        self.y += self.vy * dt

        target_y = arena.center_y
        gap_half = 40.0
        distance_x = None

        if next_pipe is not None:
            gap_half = next_pipe.gap_size * 0.5
            target_y = next_pipe.gap_center + (self.bias_factor + self.jitter_factor) * gap_half
            distance_x = next_pipe.x + next_pipe.width - self.x

        min_target = arena.top + self.radius + gap_half * 0.15
        max_target = arena.bottom - self.radius - gap_half * 0.15
        if target_y < min_target:
            target_y = min_target
        elif target_y > max_target:
            target_y = max_target

        if self.y > arena.bottom - self.radius - self.panic_margin:
            self._flap(game_time)
            return

        if distance_x is None or distance_x <= self.reaction_distance:
            if self.y > target_y + self.flap_buffer and self.vy >= -self.flap_velocity * 0.3:
                self._try_flap(game_time)

        target_x = self.base_x + math.sin(game_time * self.x_sway_rate + self.x_sway_phase) * self.x_sway_amplitude
        min_x = arena.left + self.radius
        max_x = arena.right - self.radius
        if target_x < min_x:
            target_x = min_x
        elif target_x > max_x:
            target_x = max_x

        lerp_strength = min(1.0, self.x_sway_lerp * dt)
        self.x += (target_x - self.x) * lerp_strength

    def _try_flap(self, game_time):
        if game_time - self.last_flap_time < self.flap_cooldown:
            return
        if random.random() < self.miss_chance:
            self.last_flap_time = game_time
            return
        self._flap(game_time)

    def _flap(self, game_time):
        self.vy = -self.flap_velocity
        self.last_flap_time = game_time
