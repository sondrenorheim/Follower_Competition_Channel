"""
Plinko player behavior.
"""

import math
import random

import config


class PlinkoPlayer:
    def __init__(self, follower_data: dict, position: tuple, rng_seed: int | None = None):
        self.id = follower_data.get("id", random.randint(1, 999999))
        self.username = follower_data.get("username", f"player_{self.id}")
        self.display_name = follower_data.get("display_name", self.username)

        avatar = follower_data.get("avatar_image")
        if avatar is None:
            avatar = follower_data.get("avatar")
        self.avatar_image = avatar
        self.color = follower_data.get("color", random.choice(config.RANDOM_COLORS))

        self.x, self.y = position
        self.vx = 0.0
        self.vy = 0.0
        self.radius = float(getattr(config, "PLINKO_PLAYER_RADIUS", config.FOLLOWER_RADIUS))

        self.alive = True
        self.alpha = 255
        self.placement = None
        self.survival_time = 0.0

        self.eliminated = False
        self.round_complete = False
        self.current_hole = None
        self.eliminated_round = None
        self.target_hole_index = None
        self.target_x = None

        if rng_seed is not None:
            self.rng = random.Random(rng_seed)
        else:
            self.rng = random

        skill_min = float(getattr(config, "PLINKO_SKILL_MIN", 0.35))
        skill_max = float(getattr(config, "PLINKO_SKILL_MAX", 1.0))
        if skill_max < skill_min:
            skill_max = skill_min
        self.skill = self.rng.uniform(skill_min, skill_max)
        self.bias = self.rng.uniform(-0.25, 0.25)

        self.gravity = float(getattr(config, "PLINKO_GRAVITY", 520.0))
        self.max_fall_speed = float(getattr(config, "PLINKO_MAX_FALL_SPEED", 420.0))
        self.bias_strength = float(getattr(config, "PLINKO_BIAS_STRENGTH", 1.4))
        self.drift_damping = float(getattr(config, "PLINKO_DRIFT_DAMPING", 0.18))
        self.wall_bounce = float(getattr(config, "PLINKO_WALL_BOUNCE", 0.5))
        self.max_horizontal_speed = float(getattr(config, "PLINKO_MAX_HORIZONTAL_SPEED", 260.0))
        self.peg_bounce = float(getattr(config, "PLINKO_PEG_BOUNCE", 0.65))
        self.peg_jitter = float(getattr(config, "PLINKO_PEG_JITTER", 0.12))
        self.peg_hitbox_scale = float(getattr(config, "PLINKO_PEG_HITBOX_SCALE", 1.6))
        self.max_upward_speed = float(getattr(config, "PLINKO_MAX_UPWARD_SPEED", 140.0))
        self.min_fall_speed = float(getattr(config, "PLINKO_MIN_FALL_SPEED", 30.0))
        self.peg_slide_speed = float(getattr(config, "PLINKO_PEG_SLIDE_SPEED", 40.0))
        self.peg_stick_speed = float(getattr(config, "PLINKO_PEG_STICK_SPEED", 12.0))
        self.peg_stick_nudge = float(getattr(config, "PLINKO_PEG_STICK_NUDGE", 0.35))
        self.peg_top_normal_threshold = float(getattr(config, "PLINKO_PEG_TOP_NORMAL_THRESHOLD", 0.75))
        self.peg_top_escape_impulse = float(getattr(config, "PLINKO_PEG_TOP_ESCAPE_IMPULSE", 65.0))
        self.peg_center_escape_bias = float(getattr(config, "PLINKO_PEG_CENTER_ESCAPE_BIAS", 0.18))

        self.stall_time_limit = float(getattr(config, "PLINKO_STALL_TIME", 1.2))
        self.stall_min_move = float(getattr(config, "PLINKO_STALL_MIN_MOVE", 0.6))
        self.stall_progress_time = float(getattr(config, "PLINKO_STALL_PROGRESS_TIME", 0.7))
        self.stall_progress_epsilon = float(getattr(config, "PLINKO_STALL_PROGRESS_EPSILON", 1.2))
        self.stall_nudge_speed = float(getattr(config, "PLINKO_STALL_NUDGE_SPEED", 60.0))
        self.stall_nudge_x = float(getattr(config, "PLINKO_STALL_NUDGE_X", 40.0))
        self.stall_escape_drop = float(getattr(config, "PLINKO_STALL_ESCAPE_DROP", 14.0))
        self.stall_escape_x = float(getattr(config, "PLINKO_STALL_ESCAPE_X", 12.0))
        self.stall_escape_vy = float(getattr(config, "PLINKO_STALL_ESCAPE_VY", 90.0))
        self.stall_center_push = float(getattr(config, "PLINKO_STALL_CENTER_PUSH", 70.0))
        self.last_x = self.x
        self.last_y = self.y
        self.stall_timer = 0.0
        self.stall_progress_timer = 0.0
        self.max_progress_y = self.y

    def reset_for_round(self, arena):
        self.vx = 0.0
        self.vy = 0.0
        self.round_complete = False
        self.current_hole = None

        if arena.hole_centers:
            self.target_hole_index = self.rng.randrange(len(arena.hole_centers))
            self.target_x = arena.hole_centers[self.target_hole_index]
        else:
            self.target_hole_index = None
            self.target_x = None

        self.x, self.y = arena.get_spawn_position(self.radius, self.rng)
        self.last_x = self.x
        self.last_y = self.y
        self.stall_timer = 0.0
        self.stall_progress_timer = 0.0
        self.max_progress_y = self.y

    def update(self, dt: float, arena):
        if self.eliminated or self.round_complete:
            return None

        self.vy = min(self.vy + self.gravity * dt, self.max_fall_speed)

        if self.target_x is not None:
            bias = (self.target_x - self.x) * self.bias_strength * self.skill
            self.vx += bias * dt

        if self.drift_damping > 0:
            self.vx *= max(0.0, 1.0 - self.drift_damping * dt)

        self.x += self.vx * dt
        self.y += self.vy * dt

        self._resolve_peg_collisions(arena)

        self._update_stall(dt, arena)

        min_x, max_x = arena.get_horizontal_bounds(self.y, self.radius)
        if self.x < min_x:
            self.x = min_x
            self.vx = abs(self.vx) * self.wall_bounce
        elif self.x > max_x:
            self.x = max_x
            self.vx = -abs(self.vx) * self.wall_bounce

        if abs(self.vx) > self.max_horizontal_speed:
            self.vx = math.copysign(self.max_horizontal_speed, self.vx)

        if self.vy < -self.max_upward_speed:
            self.vy = -self.max_upward_speed
        elif self.vy >= 0:
            self.vy = max(self.vy, self.min_fall_speed)

        if self.y >= arena.hole_top - self.radius:
            success, hole_index = arena.check_hole(self.x)
            if not success:
                hole_index = arena.get_nearest_hole_index(self.x)
            if hole_index is not None:
                self.target_hole_index = hole_index
                return hole_index
            return None

        return None

    def _update_stall(self, dt: float, arena):
        dx = self.x - self.last_x
        dy = self.y - self.last_y
        moved = math.hypot(dx, dy)

        if moved < self.stall_min_move:
            self.stall_timer += dt
        else:
            self.stall_timer = 0.0

        if self.y > (self.max_progress_y + self.stall_progress_epsilon):
            self.max_progress_y = self.y
            self.stall_progress_timer = 0.0
        else:
            self.stall_progress_timer += dt

        if self.stall_timer >= self.stall_time_limit or self.stall_progress_timer >= self.stall_progress_time:
            self._force_unstick(arena)
            self.stall_timer = 0.0
            self.stall_progress_timer = 0.0

        self.last_x = self.x
        self.last_y = self.y

    def _force_unstick(self, arena):
        spacing_y = max(4.0, float(getattr(arena, "row_spacing_actual", 12.0)))
        spacing_x = max(4.0, float(getattr(arena, "peg_spacing_x", self.radius * 2.0) or (self.radius * 2.0)))

        drop = max(self.stall_escape_drop, spacing_y * 0.65)
        lateral = self.rng.uniform(-1.0, 1.0) * max(self.stall_escape_x, spacing_x * 0.22)

        self.y += drop
        self.x += lateral

        min_x, max_x = arena.get_horizontal_bounds(self.y, self.radius)
        if self.x < min_x:
            self.x = min_x
        elif self.x > max_x:
            self.x = max_x

        # Bias horizontal velocity toward center so edge traps clear quickly.
        to_center = arena.center_x - self.x
        if abs(to_center) > 1e-3:
            center_dir = 1.0 if to_center > 0 else -1.0
            self.vx += center_dir * self.stall_center_push

        self.vy = max(self.vy, self.stall_nudge_speed, self.stall_escape_vy, self.min_fall_speed)
        if self.stall_nudge_x > 0:
            self.vx += self.rng.uniform(-self.stall_nudge_x, self.stall_nudge_x)
        self.max_progress_y = max(self.max_progress_y, self.y)

    def _resolve_peg_collisions(self, arena):
        min_dist = self.radius + (arena.peg_radius * self.peg_hitbox_scale)
        min_dist_sq = min_dist * min_dist

        for peg_x, peg_y in arena.iter_nearby_pegs(self.x, self.y, self.radius):
            dx = self.x - peg_x
            dy = self.y - peg_y
            dist_sq = dx * dx + dy * dy
            if dist_sq <= 1e-6 or dist_sq >= min_dist_sq:
                continue

            dist = math.sqrt(dist_sq)
            nx = dx / dist
            ny = dy / dist

            overlap = min_dist - dist
            self.x += nx * overlap
            self.y += ny * overlap

            v_dot = (self.vx * nx) + (self.vy * ny)
            if v_dot < 0:
                bounce = 1.0 + max(0.0, self.peg_bounce)
                self.vx -= bounce * v_dot * nx
                self.vy -= bounce * v_dot * ny

            if self.peg_jitter > 0:
                tangent_x = -ny
                tangent_y = nx
                jitter = (self.rng.random() * 2.0 - 1.0) * self.peg_jitter
                self.vx += tangent_x * jitter * abs(self.vy)
                self.vy += tangent_y * jitter * abs(self.vx) * 0.25

            # Never allow stable balancing on a thin peg top.
            if ny < -self.peg_top_normal_threshold:
                self.vy = max(self.vy, self.peg_slide_speed, self.min_fall_speed)
                lateral = nx
                if abs(lateral) < self.peg_center_escape_bias:
                    lateral = self.peg_center_escape_bias if self.rng.random() < 0.5 else -self.peg_center_escape_bias
                self.vx += lateral * self.peg_top_escape_impulse
            elif dy < 0 and abs(self.vy) < self.peg_stick_speed:
                self.vy = max(self.vy, self.peg_slide_speed, self.min_fall_speed)
                if abs(dx) < min_dist * 0.25:
                    self.vx += self.rng.uniform(-1.0, 1.0) * self.peg_stick_nudge * self.peg_slide_speed
