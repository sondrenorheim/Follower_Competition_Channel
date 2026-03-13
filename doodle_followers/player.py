import random
import math

import config
from shared import EntityTemplate


class DoodleFollower(EntityTemplate):
    def _init_entity(self, follower_data: dict):
        self.radius = float(getattr(config, "DOODLE_PLAYER_RADIUS", config.FOLLOWER_RADIUS))

        self.gravity = float(getattr(config, "DOODLE_GRAVITY", 1200.0))
        self.max_fall_speed = float(getattr(config, "DOODLE_MAX_FALL_SPEED", 900.0))
        self.jump_velocity = float(getattr(config, "DOODLE_JUMP_VELOCITY", -620.0))
        self.spring_velocity = float(getattr(config, "DOODLE_SPRING_VELOCITY", -900.0))
        self.trampoline_velocity = float(getattr(config, "DOODLE_TRAMPOLINE_VELOCITY", -1100.0))

        self.move_speed = float(getattr(config, "DOODLE_MOVE_SPEED", 160.0))
        self.move_smoothing = float(getattr(config, "DOODLE_MOVE_SMOOTH", 8.0))
        self.panic_speed_multiplier = float(getattr(config, "DOODLE_PANIC_SPEED_MULTIPLIER", 1.45))
        self.panic_fall_speed = float(getattr(config, "DOODLE_PANIC_FALL_SPEED", 320.0))
        self.move_gain_base = float(getattr(config, "DOODLE_MOVE_GAIN_BASE", 3.0))
        self.move_gain_boost = float(getattr(config, "DOODLE_MOVE_GAIN_BOOST", 3.0))
        self.move_gain_distance = float(getattr(config, "DOODLE_MOVE_GAIN_DISTANCE", 180.0))
        self.move_smooth_boost = float(getattr(config, "DOODLE_MOVE_SMOOTH_BOOST", 6.0))
        self.move_smooth_distance = float(getattr(config, "DOODLE_MOVE_SMOOTH_DISTANCE", 180.0))
        self.jump_height_factor = float(getattr(config, "DOODLE_JUMP_HEIGHT_FACTOR", 0.82))
        self.reach_safety = float(getattr(config, "DOODLE_REACH_SAFETY", 0.85))
        self.target_spread = float(getattr(config, "DOODLE_TARGET_SPREAD", 0.25))
        self.jump_reach_safety = float(getattr(config, "DOODLE_JUMP_TARGET_REACH_SAFETY", 0.78))
        self.jump_cross_speed = float(getattr(config, "DOODLE_JUMP_CROSS_SCREEN_SPEED", 520.0))
        self.jump_gain_multiplier = float(getattr(config, "DOODLE_JUMP_GAIN_MULTIPLIER", 1.8))
        self.jump_smooth_multiplier = float(getattr(config, "DOODLE_JUMP_SMOOTH_MULTIPLIER", 1.4))
        self.horiz_accel = float(getattr(config, "DOODLE_HORIZ_ACCEL", 900.0))
        self.horiz_accel_jump = float(getattr(config, "DOODLE_HORIZ_ACCEL_JUMP", 1200.0))
        self.apex_x_ratio = float(getattr(config, "DOODLE_APEX_X_RATIO", 0.5))
        self.landing_brake_factor = float(getattr(config, "DOODLE_LANDING_BRAKE_FACTOR", 4.0))
        self.landing_brake_lookahead = float(getattr(config, "DOODLE_LANDING_BRAKE_LOOKAHEAD", 140.0))
        self.landing_brake_min_vx = float(getattr(config, "DOODLE_LANDING_BRAKE_MIN_VX", 40.0))
        day_seed = int(getattr(config, "DAY_NUMBER", 1))
        seed_base = self._seed_from_id(self.id)
        self.rng = random.Random(seed_base + day_seed * 1000)

        self.spawn_y = self.y
        self.base_jump_velocity = self.jump_velocity
        self.base_spring_velocity = self.spring_velocity
        self.base_trampoline_velocity = self.trampoline_velocity
        self.jump_height_variance = float(getattr(config, "DOODLE_JUMP_HEIGHT_VARIANCE", 0.08))
        self.jump_height_multiplier = 1.0

        self.horizontal_jitter = float(getattr(config, "DOODLE_HORIZONTAL_JITTER", 0.22))
        self.horizontal_wobble_speed = float(getattr(config, "DOODLE_HORIZONTAL_WOBBLE_SPEED", 1.8))
        self.horizontal_jitter_height_ramp = float(getattr(config, "DOODLE_JITTER_HEIGHT_RAMP", 2000.0))
        self.horizontal_jitter_max_mult = float(getattr(config, "DOODLE_JITTER_MAX_MULT", 1.35))
        self.horizontal_wobble_phase = self.rng.uniform(0.0, 6.283)

        self.ai_retarget_min = float(getattr(config, "DOODLE_AI_RETARGET_MIN", 0.18))
        self.ai_retarget_max = float(getattr(config, "DOODLE_AI_RETARGET_MAX", 0.5))
        self.ai_timer = 0.0

        self.ai_retarget_time = self.rng.uniform(self.ai_retarget_min, self.ai_retarget_max)
        self.target_x = self.x
        self.drift_direction = self.rng.choice([-1, 1])
        aim_error_range = float(getattr(config, "DOODLE_AIM_ERROR_RANGE", 0.08))
        self.aim_error = self.rng.uniform(-aim_error_range, aim_error_range)

        self.best_height = self.y
        self.last_platform_id = None
        self.last_platform_y = None
        self.current_platform_index = None
        self.target_platform_index = None
        self.jump_target = None
        self.jump_target_offset = 0.0
        self.jump_target_speed = None

    @staticmethod
    def _seed_from_id(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            text = str(value)
            seed = 0
            for idx, char in enumerate(text):
                seed += (idx + 1) * ord(char)
            return seed

    def update(self, dt: float, arena, platforms, difficulty: float, camera_y: float, is_leader: bool = False):
        if not self.alive:
            self.update_fade()
            return

        # Jump height multiplier is updated when a jump is triggered.
        leader_slow = float(getattr(config, "DOODLE_LEADER_AIRTIME_SLOW", 1.0))
        if is_leader and leader_slow > 1.0:
            dt *= 1.0 / leader_slow

        self.ai_timer += dt
        if self.jump_target is not None:
            if self.jump_target.broken or self.jump_target.height <= 0:
                self.jump_target = None
                self.jump_target_speed = None
            else:
                wobble = self._horizontal_wobble(dt, arena.width)
                self.target_x = max(0.0, min(arena.width, self.jump_target.x + self.jump_target_offset + wobble))

        if self.jump_target is None and self.target_platform_index is not None:
            self.lock_jump_target(platforms, arena.width)

        if self.jump_target is None and self.vy >= 0:
            self._pick_fall_target(platforms, arena.width)
        elif self.jump_target is None and self.ai_timer >= self.ai_retarget_time:
            self.ai_timer = 0.0
            self.ai_retarget_time = self.rng.uniform(self.ai_retarget_min, self.ai_retarget_max)
            self._pick_target(platforms, difficulty, arena.width)

        if self.jump_target is None and self.target_x is not None:
            self.target_x = max(0.0, min(arena.width, self.target_x + self._horizontal_wobble(dt, arena.width)))

        speed_mult = self.panic_speed_multiplier if self.vy > self.panic_fall_speed else 1.0
        dx = 0.0 if self.target_x is None else self.target_x - self.x
        distance_ratio = min(1.0, abs(dx) / max(1.0, self.move_gain_distance))
        gain_mult = self.jump_gain_multiplier if self.jump_target is not None else 1.0
        desired_vx = self._calculate_desired_vx(speed_mult, distance_ratio, gain_mult)

        if self.jump_target is not None and self.vy < 0 and self.gravity > 0:
            t_apex = max(0.05, -self.vy / self.gravity)
            apex_ratio = max(0.2, min(0.8, self.apex_x_ratio))
            desired_vx = (dx * apex_ratio) / t_apex
            max_speed = self._get_max_speed(speed_mult)
            if desired_vx > max_speed:
                desired_vx = max_speed
            elif desired_vx < -max_speed:
                desired_vx = -max_speed

        accel = self.horiz_accel_jump if self.jump_target is not None else self.horiz_accel
        dv = desired_vx - self.vx
        max_dv = accel * dt
        if dv > max_dv:
            dv = max_dv
        elif dv < -max_dv:
            dv = -max_dv
        self.vx += dv

        if self.jump_target is not None and self.vy > 0:
            self._apply_landing_brake(platforms, dt)

        self.vy += self.gravity * dt
        if self.vy > self.max_fall_speed:
            self.vy = self.max_fall_speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        wrap_margin = self.radius * 0.5
        if self.x < -wrap_margin:
            self.x = arena.width + wrap_margin
        elif self.x > arena.width + wrap_margin:
            self.x = -wrap_margin

        if self.y < self.best_height:
            self.best_height = self.y

    def _get_max_speed(self, speed_multiplier: float = 1.0) -> float:
        max_speed = self.move_speed * max(0.5, speed_multiplier)
        if self.jump_target_speed:
            max_speed = max(max_speed, self.jump_target_speed)
        return max_speed

    def _calculate_desired_vx(
        self,
        speed_multiplier: float = 1.0,
        distance_ratio: float = 0.0,
        gain_multiplier: float = 1.0,
    ) -> float:
        max_speed = self._get_max_speed(speed_multiplier)
        if self.target_x is None:
            return max_speed * self.drift_direction

        dx = self.target_x - self.x
        if abs(dx) < 4:
            return max_speed * 0.25 * self.drift_direction

        gain = (self.move_gain_base + self.move_gain_boost * max(0.0, min(1.0, distance_ratio))) * gain_multiplier
        desired = dx * gain
        if desired > max_speed:
            desired = max_speed
        elif desired < -max_speed:
            desired = -max_speed
        return desired

    def lock_jump_target(self, platforms, arena_width: float):
        self.jump_target = None
        self.jump_target_offset = 0.0
        self.jump_target_speed = None

        if self.target_platform_index is None:
            return

        target_platform = None
        for platform in platforms:
            if platform.broken or platform.height <= 0:
                continue
            if platform.index == self.target_platform_index:
                target_platform = platform
                break

        if target_platform is None:
            return

        self.jump_target = target_platform
        self.jump_target_offset = 0.0
        self.target_x = max(0.0, min(arena_width, target_platform.x))

        gravity = self.gravity
        jump_speed = abs(self.vy)
        if gravity <= 0 or jump_speed <= 0:
            return

        dy = (self.last_platform_y or self.y) - target_platform.y
        if dy <= 0:
            return

        disc = jump_speed * jump_speed - 2.0 * gravity * dy
        if disc <= 0:
            return

        t_reach = (jump_speed - disc ** 0.5) / gravity
        if t_reach <= 0:
            return

        dx = abs(target_platform.x - self.x)
        required_speed = dx / t_reach
        self.jump_target_speed = max(self.jump_cross_speed, required_speed * 1.15)

    def roll_jump_multiplier(self):
        self.jump_height_multiplier = self.rng.uniform(
            1.0 - self.jump_height_variance,
            1.0 + self.jump_height_variance,
        )

    def _pick_target(self, platforms, difficulty: float, arena_width: float):
        if not platforms:
            self.target_x = self.rng.uniform(0, arena_width)
            return

        gravity = self.gravity
        jump_velocity = abs(self.jump_velocity)
        max_jump_height = (jump_velocity * jump_velocity) / (2.0 * gravity) if gravity > 0 else 160.0
        max_jump_height *= self.jump_height_factor

        lookahead_min = float(getattr(config, "DOODLE_AIM_MIN", 40.0))
        lookahead_max = float(getattr(config, "DOODLE_AIM_MAX", 220.0))
        lookahead_max *= (1.0 - 0.35 * difficulty)
        lookahead_max = min(lookahead_max, max_jump_height)

        reach_factor = float(getattr(config, "DOODLE_HORIZONTAL_REACH_FACTOR", 1.15))
        fall_min = float(getattr(config, "DOODLE_FALL_LOOKAHEAD_MIN", 8.0))
        fall_max = float(getattr(config, "DOODLE_FALL_LOOKAHEAD_MAX", 260.0))
        vertical_weight = float(getattr(config, "DOODLE_AI_VERTICAL_WEIGHT", 0.35))
        breakable_penalty = float(getattr(config, "DOODLE_PLATFORM_PENALTY_BREAKABLE", 0.18))
        moving_penalty = float(getattr(config, "DOODLE_PLATFORM_PENALTY_MOVING", 0.1))
        trampoline_penalty = float(getattr(config, "DOODLE_PLATFORM_PENALTY_TRAMPOLINE", 0.08))

        scored_candidates = []

        if self.vy >= 0:
            lower = self.y + fall_min
            upper = self.y + fall_max
            for platform in platforms:
                if platform.broken:
                    continue
                if not (lower <= platform.y <= upper):
                    continue
                dy = platform.y - self.y
                disc = self.vy * self.vy + 2.0 * gravity * dy
                if disc <= 0:
                    continue
                t_reach = (-self.vy + disc ** 0.5) / gravity
                if t_reach <= 0:
                    continue
                max_horizontal = self.move_speed * t_reach * reach_factor * self.reach_safety
                dx = abs(platform.x - self.x)
                if dx > max_horizontal:
                    continue
                reach_ratio = dx / max(1.0, max_horizontal)
                penalty = 0.0
                if platform.kind == "breakable":
                    penalty += breakable_penalty
                elif platform.kind == "moving":
                    penalty += moving_penalty
                elif platform.kind == "trampoline":
                    penalty += trampoline_penalty
                norm = max(1.0, fall_max)
                score = reach_ratio + (dy / norm) * vertical_weight + penalty
                scored_candidates.append((score, dy, platform))
        else:
            upper = self.y - lookahead_min
            lower = self.y - lookahead_max
            for platform in platforms:
                if platform.broken:
                    continue
                if not (lower <= platform.y <= upper):
                    continue
                dy = self.y - platform.y
                disc = jump_velocity * jump_velocity - 2.0 * gravity * dy
                if disc < 0:
                    continue
                t_reach = (jump_velocity + disc ** 0.5) / gravity
                max_horizontal = self.move_speed * t_reach * reach_factor * self.reach_safety
                dx = abs(platform.x - self.x)
                if dx > max_horizontal:
                    continue
                reach_ratio = dx / max(1.0, max_horizontal)
                penalty = 0.0
                if platform.kind == "breakable":
                    penalty += breakable_penalty
                elif platform.kind == "moving":
                    penalty += moving_penalty
                elif platform.kind == "trampoline":
                    penalty += trampoline_penalty
                norm = max(1.0, max_jump_height)
                score = reach_ratio + (dy / norm) * vertical_weight + penalty
                scored_candidates.append((score, dy, platform))

        if not scored_candidates:
            chosen = self._pick_fallback_platform(platforms, fall_min, fall_max)
        else:
            scored_candidates.sort(key=lambda item: (item[0], item[1]))
            chosen = scored_candidates[0][2]

        if chosen:
            spread = chosen.width * self.target_spread
            offset = self.rng.uniform(-spread, spread)
            target = chosen.x + offset
        else:
            target = self.rng.uniform(0, arena_width)

        error_range = float(getattr(config, "DOODLE_AIM_ERROR_RANGE", 0.08))
        error_scale = max(0.2, 1.0 - 0.45 * difficulty)
        target += self.aim_error * error_scale * arena_width * 0.05
        self.target_x = max(0.0, min(arena_width, target))

    def _pick_fallback_platform(self, platforms, fall_min: float, fall_max: float):
        best = None
        best_score = None
        extended_max = fall_max * 1.6

        for platform in platforms:
            if platform.broken or platform.height <= 0:
                continue
            dy = platform.y - self.y
            if dy < fall_min:
                continue
            if dy > extended_max:
                continue
            dx = abs(platform.x - self.x)
            score = dy + dx * 0.45
            if best_score is None or score < best_score:
                best_score = score
                best = platform

        return best

    def _pick_fall_target(self, platforms, arena_width: float):
        fall_min = float(getattr(config, "DOODLE_FALL_LOOKAHEAD_MIN", 8.0))
        fall_max = float(getattr(config, "DOODLE_FALL_LOOKAHEAD_MAX", 260.0))
        gravity = self.gravity
        if gravity <= 0:
            return

        best = None
        best_score = None

        lower = self.y + fall_min
        upper = self.y + fall_max

        for platform in platforms:
            if platform.broken or platform.height <= 0:
                continue
            if not (lower <= platform.y <= upper):
                continue
            dy = platform.y - self.y
            disc = self.vy * self.vy + 2.0 * gravity * dy
            if disc <= 0:
                continue
            t_reach = (-self.vy + disc ** 0.5) / gravity
            if t_reach <= 0:
                continue
            max_horizontal = self.move_speed * t_reach * self.reach_safety
            dx = abs(platform.x - self.x)
            if dx > max_horizontal:
                continue

            score = dy + dx * 0.5
            if best_score is None or score < best_score:
                best_score = score
                best = platform

        if best is None:
            return

        spread = best.width * self.target_spread
        offset = self.rng.uniform(-spread, spread)
        self.target_x = max(0.0, min(arena_width, best.x + offset))

    def _horizontal_wobble(self, dt: float, arena_width: float) -> float:
        if self.horizontal_jitter <= 0:
            return 0.0
        self.horizontal_wobble_phase += self.horizontal_wobble_speed * dt
        height = max(0.0, self.spawn_y - self.y)
        ramp = max(1.0, self.horizontal_jitter_height_ramp)
        mult = 1.0 + min(max(0.0, self.horizontal_jitter_max_mult - 1.0), height / ramp)
        amp = arena_width * self.horizontal_jitter * 0.03 * mult
        return math.sin(self.horizontal_wobble_phase) * amp

    def _apply_landing_brake(self, platforms, dt: float):
        if self.jump_target is None or self.landing_brake_factor <= 0:
            return
        if self.landing_brake_lookahead <= 0:
            return

        dy = self.jump_target.y - self.y
        if dy <= 0 or dy > self.landing_brake_lookahead:
            return

        next_target = None
        next_index = self.jump_target.index + 1
        for platform in platforms:
            if platform.broken or platform.height <= 0:
                continue
            if platform.index == next_index:
                next_target = platform
                break

        if next_target is None:
            return

        future_dx = next_target.x - self.jump_target.x
        if abs(future_dx) < 1:
            return

        future_dir = 1.0 if future_dx > 0 else -1.0
        if self.vx * future_dir >= 0:
            return
        if abs(self.vx) < self.landing_brake_min_vx:
            return

        brake = self.landing_brake_factor
        self.vx *= max(0.0, 1.0 - brake * dt)
