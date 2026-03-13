import math
import random
import zlib

import config
from shared import EntityTemplate


class TinyFollower(EntityTemplate):
    def _init_entity(self, follower_data: dict):
        self.size = float(getattr(config, "TINY_PLAYER_SIZE", 30.0))
        self.radius = self.size * 0.5

        self.gravity = float(getattr(config, "TINY_GRAVITY", 900.0))
        self.dive_force = float(getattr(config, "TINY_DIVE_FORCE", 2100.0))
        self.dive_ground_boost = float(getattr(config, "TINY_DIVE_GROUND_BOOST", 950.0))
        self.air_forward_accel = float(getattr(config, "TINY_AIR_FORWARD_ACCEL", 260.0))
        self.passive_forward_accel = float(getattr(config, "TINY_PASSIVE_FORWARD_ACCEL", 46.0))
        self.dive_air_forward_bonus = float(getattr(config, "TINY_DIVE_AIR_FORWARD_BONUS", 170.0))
        self.max_fall_speed = float(getattr(config, "TINY_MAX_FALL_SPEED", 780.0))
        self.max_upward_air_speed = float(getattr(config, "TINY_MAX_UPWARD_AIR_SPEED", 760.0))
        self.total_speed_abs_cap = float(getattr(config, "TINY_TOTAL_SPEED_ABS_CAP", 1000.0))
        self.max_air_speed = float(getattr(config, "TINY_MAX_AIR_SPEED", 620.0))
        self.air_speed_cap_scale = float(getattr(config, "TINY_AIR_SPEED_CAP_SCALE", 1.0))
        self.air_speed_cap_decay = float(getattr(config, "TINY_AIR_SPEED_CAP_DECAY", 0.45))
        self.air_speed_abs_cap = float(getattr(config, "TINY_AIR_SPEED_ABS_CAP", 2400.0))
        self.air_top_margin = float(getattr(config, "TINY_AIR_TOP_MARGIN", 14.0))

        self.base_min_ground_speed = float(getattr(config, "TINY_MIN_GROUND_SPEED", 120.0))
        self.base_max_ground_speed = float(getattr(config, "TINY_MAX_GROUND_SPEED", 520.0))
        self.base_min_air_speed = float(getattr(config, "TINY_MIN_AIR_SPEED", 90.0))

        self.ground_drag = float(getattr(config, "TINY_GROUND_DRAG", 0.12))
        self.ground_gravity_scale = float(getattr(config, "TINY_GROUND_GRAVITY_SCALE", 0.12))
        self.downhill_accel_gain = float(getattr(config, "TINY_DOWNHILL_ACCEL_GAIN", 360.0))
        self.downhill_accel_curve = float(getattr(config, "TINY_DOWNHILL_ACCEL_CURVE", 1.25))
        self.downhill_drag_reduction = float(getattr(config, "TINY_DOWNHILL_DRAG_REDUCTION", 0.45))
        self.downhill_extra_speed_cap = float(getattr(config, "TINY_DOWNHILL_EXTRA_SPEED_CAP", 220.0))
        self.downhill_speed_abs_cap = float(getattr(config, "TINY_DOWNHILL_SPEED_ABS_CAP", 2200.0))
        self.downhill_landing_min_slope = float(getattr(config, "TINY_DOWNHILL_LANDING_MIN_SLOPE", 0.02))
        self.downhill_landing_transfer = float(getattr(config, "TINY_DOWNHILL_LANDING_TRANSFER", 1.0))
        self.downhill_landing_speed_cap = float(getattr(config, "TINY_DOWNHILL_LANDING_SPEED_CAP", 2200.0))
        self.downhill_momentum_hold_time = float(getattr(config, "TINY_DOWNHILL_MOMENTUM_HOLD_TIME", 0.95))
        self.downhill_momentum_decay = float(getattr(config, "TINY_DOWNHILL_MOMENTUM_DECAY", 140.0))
        self.downhill_momentum_abs_cap = float(getattr(config, "TINY_DOWNHILL_MOMENTUM_ABS_CAP", 2600.0))
        self.uphill_mismatch_carry_reduction = float(
            getattr(config, "TINY_UPHILL_MISMATCH_CARRY_REDUCTION", 1.0)
        )
        self.uphill_carry_transfer = float(getattr(config, "TINY_UPHILL_CARRY_TRANSFER", 0.92))
        self.jump_landing_min_airtime = float(getattr(config, "TINY_JUMP_LANDING_MIN_AIRTIME", 0.30))
        self.landing_slope_threshold = float(getattr(config, "TINY_LANDING_SLOPE_THRESHOLD", 0.02))
        self.jump_downhill_speed_gain = float(getattr(config, "TINY_JUMP_DOWNHILL_SPEED_GAIN", 0.32))
        self.jump_uphill_speed_loss = float(getattr(config, "TINY_JUMP_UPHILL_SPEED_LOSS", 0.56))
        self.max_launch_up_speed = float(getattr(config, "TINY_MAX_LAUNCH_UP_SPEED", 760.0))
        self.launch_clearance = float(getattr(config, "TINY_LAUNCH_CLEARANCE", 3.0))
        self.perfect_takeoff_vy = float(getattr(config, "TINY_PERFECT_TAKEOFF_VY", 85.0))
        self.hit_angle_threshold = float(getattr(config, "TINY_HIT_ANGLE_THRESHOLD", 2.4))
        self.hit_speed_loss = float(getattr(config, "TINY_HIT_SPEED_LOSS", 0.72))
        self.pump_min_down_speed = float(getattr(config, "TINY_PUMP_MIN_DOWN_SPEED", 170.0))
        self.pump_downhill_slope = float(getattr(config, "TINY_PUMP_DOWNHILL_SLOPE", 0.04))
        self.pump_speed_gain = float(getattr(config, "TINY_PUMP_SPEED_GAIN", 0.22))
        self.pump_streak_step = float(getattr(config, "TINY_PUMP_STREAK_STEP", 0.95))
        self.pump_streak_max = float(getattr(config, "TINY_PUMP_STREAK_MAX", 5.0))
        self.pump_streak_mult = float(getattr(config, "TINY_PUMP_STREAK_MULT", 0.13))
        self.pump_streak_decay = float(getattr(config, "TINY_PUMP_STREAK_DECAY", 0.4))
        self.pump_launch_bonus = float(getattr(config, "TINY_PUMP_LAUNCH_BONUS", 0.75))
        self.coast_speed_bleed = float(getattr(config, "TINY_COAST_SPEED_BLEED", 0.32))
        self.missed_pump_speed_loss = float(getattr(config, "TINY_MISSED_PUMP_SPEED_LOSS", 0.22))
        self.missed_pump_downhill_slope = float(getattr(config, "TINY_MISSED_PUMP_DOWNHILL_SLOPE", 0.045))
        self.missed_pump_min_down_speed = float(getattr(config, "TINY_MISSED_PUMP_MIN_DOWN_SPEED", 96.0))
        self.dive_hold_ramp_rate = float(getattr(config, "TINY_DIVE_HOLD_RAMP_RATE", 1.8))
        self.dive_hold_max_mult = float(getattr(config, "TINY_DIVE_HOLD_MAX_MULT", 2.4))
        self.dive_hold_release_decay = float(getattr(config, "TINY_DIVE_HOLD_RELEASE_DECAY", 3.0))
        self.dive_hold_fall_bonus = float(getattr(config, "TINY_DIVE_HOLD_FALL_BONUS", 420.0))
        self.dive_charge_pump_bonus = float(getattr(config, "TINY_DIVE_CHARGE_PUMP_BONUS", 0.7))
        self.uphill_mismatch_slope = float(getattr(config, "TINY_UPHILL_MISMATCH_SLOPE", -0.06))
        self.uphill_mismatch_min_down_speed = float(getattr(config, "TINY_UPHILL_MISMATCH_MIN_DOWN_SPEED", 150.0))
        self.uphill_mismatch_speed_loss = float(getattr(config, "TINY_UPHILL_MISMATCH_SPEED_LOSS", 0.78))
        self.uphill_mismatch_min_keep = float(getattr(config, "TINY_UPHILL_MISMATCH_MIN_KEEP", 0.18))
        self.horizontal_pump_gain = float(getattr(config, "TINY_HORIZONTAL_PUMP_GAIN", 0.0))
        self.horizontal_pump_cap = float(getattr(config, "TINY_HORIZONTAL_PUMP_CAP", 420.0))
        self.horizontal_charge_bonus = float(getattr(config, "TINY_HORIZONTAL_CHARGE_BONUS", 1.0))
        self.horizontal_jump_bonus = float(getattr(config, "TINY_HORIZONTAL_JUMP_BONUS", 1.0))
        self.horizontal_jump_ref_height = float(getattr(config, "TINY_HORIZONTAL_JUMP_REF_HEIGHT", 220.0))
        self.horizontal_miss_penalty = float(getattr(config, "TINY_HORIZONTAL_MISS_PENALTY", 0.8))
        self.horizontal_uphill_penalty = float(getattr(config, "TINY_HORIZONTAL_UPHILL_PENALTY", 1.0))
        self.horizontal_min_tangent = float(getattr(config, "TINY_HORIZONTAL_MIN_TANGENT", 0.35))
        self.vertical_speed_reward = float(getattr(config, "TINY_VERTICAL_SPEED_REWARD", 0.0))
        self.vertical_speed_reward_cap = float(getattr(config, "TINY_VERTICAL_SPEED_REWARD_CAP", 240.0))
        self.vertical_reward_min_height = float(getattr(config, "TINY_VERTICAL_REWARD_MIN_HEIGHT", 18.0))
        self.vertical_reward_downhill_bonus = float(getattr(config, "TINY_VERTICAL_REWARD_DOWNHILL_BONUS", 0.6))
        self.vertical_speed_cap_bonus = float(getattr(config, "TINY_VERTICAL_SPEED_CAP_BONUS", 180.0))
        self.vertical_speed_cap_gain = float(getattr(config, "TINY_VERTICAL_SPEED_CAP_GAIN", 0.9))
        self.launch_boost_factor = float(getattr(config, "TINY_LAUNCH_BOOST_FACTOR", 0.24))
        self.launch_boost_cap = float(getattr(config, "TINY_LAUNCH_BOOST_CAP", 180.0))
        self.crest_lookahead = float(getattr(config, "TINY_CREST_LOOKAHEAD", 36.0))
        self.crest_drop_threshold = float(getattr(config, "TINY_CREST_DROP_THRESHOLD", 8.0))
        self.launch_crest_slope_min = float(getattr(config, "TINY_LAUNCH_CREST_SLOPE_MIN", -0.15))
        self.launch_crest_slope_max = float(getattr(config, "TINY_LAUNCH_CREST_SLOPE_MAX", -0.004))
        self.launch_near_slope_min = float(getattr(config, "TINY_LAUNCH_NEAR_SLOPE_MIN", -0.08))
        self.launch_far_slope_min = float(getattr(config, "TINY_LAUNCH_FAR_SLOPE_MIN", 0.02))
        self.launch_max_rise_ahead = float(getattr(config, "TINY_LAUNCH_MAX_RISE_AHEAD", 26.0))
        self.launch_min_rise_ahead = float(getattr(config, "TINY_LAUNCH_MIN_RISE_AHEAD", 4.0))
        self.launch_min_flattening = float(getattr(config, "TINY_LAUNCH_MIN_FLATTENING", 0.018))
        self.release_margin = float(getattr(config, "TINY_RELEASE_MARGIN", 28.0))
        self.dive_hold_bias = float(getattr(config, "TINY_DIVE_HOLD_BIAS", 0.62))

        self.lookahead_base = float(getattr(config, "TINY_LOOKAHEAD_BASE", 120.0))
        self.lookahead_time = float(getattr(config, "TINY_LOOKAHEAD_TIME", 0.35))
        self.dive_enter_slope = float(getattr(config, "TINY_DIVE_ENTER_SLOPE", 0.08))
        self.dive_exit_slope = float(getattr(config, "TINY_DIVE_EXIT_SLOPE", -0.03))
        self.air_dive_velocity = float(getattr(config, "TINY_AIR_DIVE_VELOCITY", 90.0))
        self.air_dive_clearance = float(getattr(config, "TINY_AIR_DIVE_CLEARANCE", 36.0))
        self.air_release_velocity = float(getattr(config, "TINY_AIR_RELEASE_VELOCITY", 45.0))
        self.air_release_clearance = float(getattr(config, "TINY_AIR_RELEASE_CLEARANCE", 18.0))
        self.decision_interval_min = float(getattr(config, "TINY_DECISION_INTERVAL_MIN", 0.08))
        self.decision_interval_max = float(getattr(config, "TINY_DECISION_INTERVAL_MAX", 0.18))

        # Keep bots skilled so movement resembles Tiny Wings rhythm.
        self.skill = random.uniform(0.74, 1.0)
        self.decision_error = (1.0 - self.skill) * 0.12
        self.risk = random.uniform(0.6, 1.0)
        self.apex_focus = random.uniform(0.58, 1.0)
        self.rhythm_phase = random.uniform(0.0, math.tau)
        self.rhythm_speed = random.uniform(1.6, 2.3)
        self.release_margin *= random.uniform(0.92, 1.12)
        self.pump_speed_gain *= random.uniform(0.94, 1.14)
        self.dive_ground_boost *= random.uniform(0.95, 1.12)
        self.passive_forward_accel *= random.uniform(0.92, 1.08)

        self.min_ground_speed = self.base_min_ground_speed * (0.82 + self.skill * 0.38)
        self.max_ground_speed = self.base_max_ground_speed * (0.88 + self.skill * 0.25)
        self.min_air_speed = self.base_min_air_speed * (0.85 + self.skill * 0.3)
        self.max_air_speed = self.max_air_speed * (0.9 + self.skill * 0.2)
        self.dive_force = self.dive_force * (0.82 + self.skill * 0.38)
        self.air_forward_accel = self.air_forward_accel * (0.8 + self.skill * 0.4)
        self.passive_forward_accel = self.passive_forward_accel * (0.9 + self.skill * 0.25)
        self.dive_air_forward_bonus = self.dive_air_forward_bonus * (0.82 + self.skill * 0.36)

        self.on_ground = True
        self.diving = False
        self.finished = False
        self.finish_time = None
        self.is_club_member = False

        self.perfect_slide_chain = 0
        self.max_x = self.x
        self.decision_timer = random.uniform(self.decision_interval_min, self.decision_interval_max)
        self.start_y = self.y
        self.best_y = self.y
        self.max_height_gain = 0.0
        self.target_height_gain = random.uniform(110.0, 230.0) * (0.75 + self.apex_focus * 0.7)
        self.last_pump_quality = 0.0
        self.pump_streak = 0.0
        self.airborne_launch_y = self.y
        self.airborne_apex_y = self.y
        self.airborne_time = 0.0
        self.dive_hold_time = 0.0
        self.dive_hold_charge = 0.0
        self.airborne_peak_dive_charge = 0.0
        self.current_air_speed_cap = self.max_air_speed
        self.downhill_momentum_cap = self.max_ground_speed
        self.downhill_momentum_timer = 0.0

        self.vx = self.min_ground_speed * random.uniform(0.95, 1.08)
        self.vy = 0.0
        username_bytes = str(self.username or "").encode("utf-8", errors="ignore")
        self.render_hash = zlib.crc32(username_bytes) & 0xFFFF

    def mark_finished(self, finish_time: float):
        if self.finished:
            return
        self.finished = True
        self.finish_time = float(finish_time)
        self.survival_time = float(finish_time)
        self.diving = False
        self.vx = max(self.vx, self.min_ground_speed * 0.6)
        self.vy = 0.0

    def update(self, dt, terrain, game_time, difficulty=0.0, decision_scale: float = 1.0):
        if not self.alive:
            self.update_fade()
            return

        if self.finished:
            self.max_x = max(self.max_x, self.x)
            self._update_height_tracking()
            return

        if self.downhill_momentum_timer > 0.0:
            self.downhill_momentum_timer = max(0.0, self.downhill_momentum_timer - dt)

        self.decision_timer -= dt
        if self.decision_timer <= 0.0:
            self._choose_dive_state(terrain, game_time, difficulty)
            scale = 1.16 - self.skill * 0.44
            decision_scale = max(1.0, float(decision_scale))
            self.decision_timer = (
                random.uniform(self.decision_interval_min, self.decision_interval_max)
                * max(0.45, scale)
                * decision_scale
            )

        if self.on_ground and not self.diving and self.pump_streak > 0.0:
            self.pump_streak = max(0.0, self.pump_streak - dt * self.pump_streak_decay)

        if self.on_ground:
            self._update_on_ground(dt, terrain)
        else:
            self._update_in_air(dt, terrain, difficulty)

        self.max_x = max(self.max_x, self.x)
        self._update_height_tracking()

    def fast_update(self, dt: float, terrain, difficulty: float = 0.0):
        """
        Lightweight physics path for very high population counts.
        Keeps motion smooth while avoiding expensive per-frame decision logic.
        """
        if not self.alive:
            self.update_fade()
            return

        if self.finished:
            self.max_x = max(self.max_x, self.x)
            self._update_height_tracking()
            return

        self.decision_timer -= dt
        if self.decision_timer <= 0.0:
            # Cheap behavior toggle based on local terrain only.
            _, slope, on_ground_here = terrain.sample(self.x)
            if self.on_ground and on_ground_here:
                if slope > self.dive_enter_slope * 1.1:
                    self.diving = True
                elif slope < self.dive_exit_slope * 0.95:
                    self.diving = False
            elif self.vy < -self.air_release_velocity:
                self.diving = False
            self.decision_timer = random.uniform(self.decision_interval_min, self.decision_interval_max) * 2.2

        if self.on_ground:
            self._fast_update_on_ground(dt, terrain, difficulty)
        else:
            self._fast_update_in_air(dt, terrain, difficulty)

        self.max_x = max(self.max_x, self.x)
        self._update_height_tracking()

    def _fast_update_on_ground(self, dt: float, terrain, difficulty: float):
        ground_y, slope, on_ground = terrain.sample(self.x)
        if not on_ground:
            self._begin_airborne()
            self.on_ground = False
            return

        tangent_x = 1.0
        tangent_y = slope
        length = math.hypot(tangent_x, tangent_y)
        if length > 1e-6:
            tangent_x /= length
            tangent_y /= length
        else:
            tangent_x, tangent_y = 1.0, 0.0

        tangent_speed = self.vx * tangent_x + self.vy * tangent_y
        floor_speed = self.min_ground_speed * 0.72
        if tangent_speed < floor_speed:
            tangent_speed = floor_speed

        speed_boost = self.passive_forward_accel * (0.8 + 0.2 * max(0.0, difficulty))
        downhill_ratio = min(1.0, max(0.0, slope) / 0.45)
        if downhill_ratio > 0.0:
            speed_boost += self.downhill_accel_gain * 0.28 * downhill_ratio
        if self.diving and downhill_ratio > 0.0:
            speed_boost += self.dive_ground_boost * 0.22 * downhill_ratio

        tangent_speed += speed_boost * dt
        tangent_speed *= max(0.0, 1.0 - self.ground_drag * 0.45 * dt)
        tangent_speed = min(self.total_speed_abs_cap, max(floor_speed, tangent_speed))

        self.vx = tangent_x * tangent_speed
        self.vy = tangent_y * tangent_speed
        self.x += self.vx * dt

        next_ground_y, next_slope, next_ground = terrain.sample(self.x)
        if not next_ground:
            self._begin_airborne()
            self.on_ground = False
            # Small upward nudge so drops from crests don't look sticky.
            self.vy = min(self.vy, -self.perfect_takeoff_vy * 0.45)
            return

        next_tangent_x = 1.0
        next_tangent_y = next_slope
        next_len = math.hypot(next_tangent_x, next_tangent_y)
        if next_len > 1e-6:
            next_tangent_x /= next_len
            next_tangent_y /= next_len

        self.vx = next_tangent_x * tangent_speed
        self.vy = next_tangent_y * tangent_speed
        self.y = next_ground_y - self.radius
        self.on_ground = True

    def _fast_update_in_air(self, dt: float, terrain, difficulty: float):
        self.airborne_time += dt

        if self.diving:
            self.vy += self.dive_force * 0.55 * dt
        self.vy += self.gravity * dt
        if self.vy < -self.max_upward_air_speed:
            self.vy = -self.max_upward_air_speed
        if self.vy > self.max_fall_speed:
            self.vy = self.max_fall_speed

        forward_acc = (self.passive_forward_accel + self.air_forward_accel * 0.12) * (1.0 + 0.1 * difficulty)
        self.vx += forward_acc * dt
        if self.vx < self.min_air_speed:
            self.vx = self.min_air_speed
        self.vx = min(self.total_speed_abs_cap, self.vx)

        self.x += self.vx * dt
        self.y += self.vy * dt

        top_limit = self.radius + self.air_top_margin
        if self.y < top_limit:
            self.y = top_limit
            if self.vy < 0.0:
                self.vy = 0.0

        ground_y, slope, on_ground = terrain.sample(self.x)
        if not on_ground or self.y + self.radius < ground_y:
            return

        tangent_x = 1.0
        tangent_y = slope
        length = math.hypot(tangent_x, tangent_y)
        if length > 1e-6:
            tangent_x /= length
            tangent_y /= length
        else:
            tangent_x, tangent_y = 1.0, 0.0

        incoming_speed = math.hypot(self.vx, self.vy)
        tangent_speed = max(self.min_ground_speed * 0.72, min(self.total_speed_abs_cap, incoming_speed))
        if slope > 0.02 and self.vy > 0.0:
            tangent_speed *= 1.0 + self.jump_downhill_speed_gain * 0.22
        elif slope < -0.02 and self.vy > 0.0:
            tangent_speed *= max(0.45, 1.0 - self.jump_uphill_speed_loss * 0.25)

        self.vx = tangent_x * tangent_speed
        self.vy = tangent_y * tangent_speed
        self.y = ground_y - self.radius
        self.on_ground = True
        self.airborne_time = 0.0
        self.airborne_launch_y = self.y
        self.airborne_apex_y = self.y
        self.dive_hold_time = 0.0
        self.dive_hold_charge = 0.0
        self.airborne_peak_dive_charge = 0.0

    def _update_height_tracking(self):
        if self.y < self.best_y:
            self.best_y = self.y
        gain = self.start_y - self.best_y
        if gain > self.max_height_gain:
            self.max_height_gain = gain

    def _scan_future_profile(self, terrain, lookahead: float):
        samples = 5
        step = max(12.0, lookahead / float(samples))
        previous_slope = None
        valley_distance = None
        crest_distance = None
        future_top_y = None

        for i in range(1, samples + 1):
            distance = step * i
            y, slope, has_ground = terrain.sample(self.x + distance)
            if not has_ground:
                continue

            if future_top_y is None or y < future_top_y:
                future_top_y = y

            if previous_slope is not None:
                if previous_slope > 0.0 and slope <= 0.0 and valley_distance is None:
                    valley_distance = distance
                if previous_slope < 0.0 and slope >= 0.0 and crest_distance is None:
                    crest_distance = distance
            previous_slope = slope

        return valley_distance, crest_distance, future_top_y

    def _choose_dive_state(self, terrain, game_time: float, difficulty: float):
        ground_y, slope, on_ground = terrain.sample(self.x)
        if self.on_ground and not on_ground:
            self._begin_airborne()
            self.on_ground = False

        lookahead = self.lookahead_base + max(0.0, self.vx) * self.lookahead_time
        future_y, future_slope, future_ground = terrain.sample(self.x + lookahead)
        valley_distance, crest_distance, future_top_y = self._scan_future_profile(terrain, lookahead)

        rhythm = 0.5 + 0.5 * math.sin(game_time * self.rhythm_speed + self.rhythm_phase)
        target_progress = min(1.0, self.max_height_gain / max(1.0, self.target_height_gain))
        apex_urge = (1.0 - target_progress) * (0.45 + self.apex_focus * 0.55)

        if self.on_ground and on_ground:
            threshold_jitter = random.uniform(-0.02, 0.02) * (0.18 + self.decision_error * 1.4)
            dynamic_enter_slope = self.dive_enter_slope * (0.85 + rhythm * 0.35) * (0.9 + self.risk * 0.3)
            dynamic_enter_slope += threshold_jitter
            release_slope = self.dive_exit_slope + 0.012 * apex_urge

            should_dive = slope > dynamic_enter_slope
            if future_ground and future_slope > dynamic_enter_slope * 0.35:
                should_dive = True

            if slope < release_slope and self.vx > self.min_ground_speed * 1.05:
                should_dive = False

            if valley_distance is not None:
                # Release slightly before valley to convert slide momentum into hop height.
                release_window = self.release_margin + self.vx * 0.075 + apex_urge * 40.0
                if valley_distance <= release_window:
                    should_dive = False
                elif valley_distance >= release_window * 2.0 and slope > dynamic_enter_slope * 0.45:
                    should_dive = True

            if crest_distance is not None and crest_distance <= self.release_margin * 0.6 and slope < -0.02:
                should_dive = False

            if future_top_y is not None and future_top_y < ground_y - 24.0 and slope > 0.03:
                should_dive = False

            # If we're climbing, stop pressing and let launch boost do the jump.
            if slope <= release_slope:
                should_dive = False
        else:
            impact_x = self.x + max(8.0, self.vx * 0.16)
            impact_y, impact_slope, impact_ground = terrain.sample(impact_x)
            clearance = impact_y - (self.y + self.radius) if impact_ground else 9999.0

            min_dive_clearance = self.air_dive_clearance * (0.75 + 0.5 * (1.0 - self.apex_focus))
            should_dive = False

            if self.vy > self.air_dive_velocity and clearance > min_dive_clearance:
                should_dive = True
                if impact_ground and impact_slope < self.pump_downhill_slope * (0.7 + (1.0 - self.risk) * 0.3):
                    should_dive = False

            if (
                impact_ground
                and self.vy > self.air_dive_velocity * 0.65
                and impact_slope > self.pump_downhill_slope * 0.45
                and clearance > min_dive_clearance * 0.65
            ):
                should_dive = True

            if future_ground:
                fallback_clearance = future_y - (self.y + self.radius)
                if self.vy > self.air_dive_velocity * 0.85 and fallback_clearance > min_dive_clearance:
                    should_dive = should_dive or future_slope > self.pump_downhill_slope * 0.8

            release_clearance = self.air_release_clearance * (0.7 + self.apex_focus * 0.6)
            if self.vy < -self.air_release_velocity:
                should_dive = False
            if impact_ground and clearance < release_clearance and impact_slope <= 0.0:
                should_dive = False

        if self.diving and not should_dive:
            hold_chance = self.dive_hold_bias * (1.0 - self.skill) * 0.35
            if random.random() < hold_chance:
                should_dive = True

        if random.random() < self.decision_error * (0.55 + difficulty * 0.18):
            should_dive = not should_dive

        self.diving = should_dive

    def _update_on_ground(self, dt: float, terrain):
        ground_y, slope, on_ground = terrain.sample(self.x)
        if not on_ground:
            self.on_ground = False
            return

        tangent_x = 1.0
        tangent_y = slope
        length = math.hypot(tangent_x, tangent_y)
        if length <= 1e-6:
            tangent_x = 1.0
            tangent_y = 0.0
        else:
            tangent_x /= length
            tangent_y /= length

        tangent_speed = self.vx * tangent_x + self.vy * tangent_y
        floor_speed = self.min_ground_speed * (0.78 + self.skill * 0.18)
        if self.diving:
            floor_speed *= 1.08
        if tangent_speed < floor_speed:
            tangent_speed = floor_speed

        coast_acc = self.passive_forward_accel * (0.85 + self.skill * 0.35)
        # Sliding uphill should not trigger abrupt slope-based punishment.
        gravity_along_tangent = self.gravity * self.ground_gravity_scale * max(0.0, tangent_y)
        tangent_acc = gravity_along_tangent + coast_acc
        downhill_ratio = min(1.0, max(0.0, slope) / 0.45)
        if downhill_ratio > 0.0:
            downhill_push = self.downhill_accel_gain * (downhill_ratio ** self.downhill_accel_curve)
            tangent_acc += downhill_push * (0.78 + 0.32 * self.skill)
            self.downhill_momentum_timer = self.downhill_momentum_hold_time
        if self.diving:
            downhill_scale = 0.4 + max(0.0, slope) * 2.4
            tangent_acc += self.dive_ground_boost * downhill_scale
        tangent_speed += tangent_acc * dt

        drag = self.ground_drag
        if downhill_ratio > 0.0:
            drag *= max(0.2, 1.0 - self.downhill_drag_reduction * downhill_ratio)
        if self.diving and slope > 0.0:
            drag *= 0.78
        tangent_speed *= max(0.0, 1.0 - drag * dt)

        # Riding terrain without timing pumps should lose pace over time.
        if not self.diving and self.coast_speed_bleed > 0.0:
            pump_memory = min(1.0, self.last_pump_quality + self.pump_streak * 0.14)
            bleed = self.coast_speed_bleed * (1.0 + max(0.0, slope) * 0.35)
            bleed *= max(0.15, 1.0 - pump_memory * 0.55)
            tangent_speed *= max(0.0, 1.0 - bleed * dt)

        speed_cap = self.max_ground_speed + self.downhill_extra_speed_cap * downhill_ratio
        if downhill_ratio > 0.0:
            # Preserve downhill momentum instead of clamping it away immediately.
            speed_cap = max(speed_cap, tangent_speed * (1.0 + downhill_ratio * 0.25))
            speed_cap = min(self.downhill_speed_abs_cap, speed_cap)
            self.downhill_momentum_cap = max(self.downhill_momentum_cap, speed_cap, tangent_speed)
            self.downhill_momentum_cap = min(self.downhill_momentum_abs_cap, self.downhill_momentum_cap)

        if self.downhill_momentum_cap > self.max_ground_speed:
            speed_cap = max(speed_cap, self.downhill_momentum_cap)
        tangent_speed = max(floor_speed, min(speed_cap, tangent_speed))
        tangent_speed = min(self.total_speed_abs_cap, tangent_speed)

        self.vx = tangent_x * tangent_speed
        self.vy = tangent_y * tangent_speed
        self.x += self.vx * dt

        next_ground_y, _, next_ground = terrain.sample(self.x)
        if not next_ground:
            self._begin_airborne()
            self._apply_launch_boost(terrain, slope, tangent_speed)
            self.on_ground = False
            self._register_takeoff()
            return

        # Crest launch: treat slopes as ramps and detach only when crest geometry is present.
        if self._apply_launch_boost(terrain, slope, tangent_speed):
            self._begin_airborne()
            self.on_ground = False
            self._register_takeoff()
            return

        target_y = next_ground_y - self.radius
        self.y = target_y
        self.on_ground = True

    def _begin_airborne(self):
        if not self.on_ground:
            return
        self.airborne_launch_y = self.y
        self.airborne_apex_y = self.y
        self.airborne_time = 0.0
        self.dive_hold_time = 0.0
        self.dive_hold_charge = 0.0
        self.airborne_peak_dive_charge = 0.0
        launch_cap = max(self.max_air_speed, abs(self.vx) * self.air_speed_cap_scale)
        self.current_air_speed_cap = min(self.air_speed_abs_cap, launch_cap)

    def _apply_launch_boost(self, terrain, slope: float, tangent_speed: float) -> bool:
        # Releasing near crest turns an uphill into a ramp launch.
        if self.diving and slope > 0.12:
            return False
        if slope < self.launch_crest_slope_min or slope > self.launch_crest_slope_max:
            return False
        if tangent_speed < self.min_ground_speed * 1.02:
            return False

        ground_y, _, on_ground = terrain.sample(self.x)
        if not on_ground:
            return False

        near_x = self.x + self.crest_lookahead * 0.65
        far_x = self.x + self.crest_lookahead * 1.45
        near_y, near_slope, near_ground = terrain.sample(near_x)
        far_y, far_slope, far_ground = terrain.sample(far_x)

        if not (near_ground and far_ground):
            return False

        rise_ahead = max(0.0, ground_y - near_y)
        drop_after = max(0.0, far_y - near_y)
        flattening = near_slope - slope

        hard_rise_ok = self.launch_min_rise_ahead <= rise_ahead <= self.launch_max_rise_ahead
        hard_flat_ok = flattening >= self.launch_min_flattening
        hard_drop_ok = drop_after >= self.crest_drop_threshold * 0.55
        if far_slope < self.launch_far_slope_min and drop_after < self.crest_drop_threshold * 0.75:
            return False

        soft_min_rise = max(0.8, self.launch_min_rise_ahead * 0.2)
        soft_max_rise = self.launch_max_rise_ahead * 1.7
        soft_min_flattening = -max(0.006, self.launch_min_flattening * 0.35)
        soft_drop_ok = drop_after >= self.crest_drop_threshold * 0.35
        soft_geometry_ok = (
            rise_ahead >= soft_min_rise
            and rise_ahead <= soft_max_rise
            and flattening >= soft_min_flattening
            and soft_drop_ok
        )

        hard_geometry_ok = hard_rise_ok and hard_flat_ok and hard_drop_ok
        if not hard_geometry_ok and not soft_geometry_ok:
            return False

        slope_window = (slope - self.launch_crest_slope_min) / max(
            1e-6, self.launch_crest_slope_max - self.launch_crest_slope_min
        )
        slope_window = max(0.0, min(1.0, slope_window))
        crest_readiness = 1.0 - min(1.0, rise_ahead / max(1.0, self.launch_max_rise_ahead))
        crest_signal = min(1.0, drop_after / max(1.0, self.crest_drop_threshold * 1.8))
        ramp_alignment = min(1.0, max(0.0, -slope) / 0.25)

        speed_ratio = min(1.0, tangent_speed / max(1.0, self.max_ground_speed))
        launch_quality = (
            0.18
            + 0.32 * speed_ratio
            + 0.46 * slope_window
            + 0.50 * crest_signal
            + 0.30 * crest_readiness
            + 0.22 * ramp_alignment
        ) * (0.78 + self.apex_focus * 0.4)

        min_quality = 0.44 - self.skill * 0.06
        if launch_quality < min_quality and hard_geometry_ok:
            return False

        quality_scale = 1.0
        if launch_quality < min_quality:
            quality_scale = max(0.58, launch_quality / max(1e-6, min_quality))
        if not hard_geometry_ok:
            quality_scale *= 0.82

        boost = tangent_speed * self.launch_boost_factor * (
            0.42 + speed_ratio * 0.55 + slope_window * 0.45 + crest_signal * 0.50 + ramp_alignment * 0.35
        )
        boost = min(self.launch_boost_cap, boost)
        pump_memory = min(1.0, self.last_pump_quality + self.pump_streak * 0.16)
        boost *= 1.0 + self.pump_launch_bonus * pump_memory
        boost *= quality_scale

        ramp_upward = tangent_speed * min(1.35, max(0.0, -slope) * 2.2)
        perfect_component = self.perfect_takeoff_vy * (
            0.52 + min(1.0, launch_quality) * 0.42 + pump_memory * 0.18
        )
        perfect_component *= quality_scale
        target_upward_speed = max(
            ramp_upward * (0.85 + crest_signal * 0.55),
            self.perfect_takeoff_vy * 0.75,
            perfect_component,
            boost,
        )
        target_upward_speed = min(self.max_launch_up_speed, target_upward_speed)
        self.vy = min(self.vy, -target_upward_speed)
        return True

    def _update_in_air(self, dt: float, terrain, difficulty: float):
        self.airborne_time += dt
        if self.diving:
            self.dive_hold_time += dt
        else:
            self.dive_hold_time = max(0.0, self.dive_hold_time - dt * self.dive_hold_release_decay)
        self.dive_hold_charge = min(1.0, self.dive_hold_time * self.dive_hold_ramp_rate)
        if self.dive_hold_charge > self.airborne_peak_dive_charge:
            self.airborne_peak_dive_charge = self.dive_hold_charge

        forward_scale = 1.0 + difficulty * 0.1
        forward_accel = self.passive_forward_accel + self.air_forward_accel * 0.18
        if self.diving:
            forward_accel += self.dive_air_forward_bonus * (1.0 + 0.35 * self.dive_hold_charge)

        self.vx += forward_accel * dt * forward_scale
        if self.vx < self.min_air_speed:
            self.vx = self.min_air_speed
        active_air_cap = min(self.total_speed_abs_cap, max(self.max_air_speed, self.current_air_speed_cap))
        if self.vx > active_air_cap:
            self.vx = active_air_cap
        if self.current_air_speed_cap > self.max_air_speed:
            cap_drop = self.current_air_speed_cap * self.air_speed_cap_decay * dt
            self.current_air_speed_cap = max(self.max_air_speed, self.current_air_speed_cap - cap_drop)

        dynamic_max_fall = self.max_fall_speed + self.dive_hold_fall_bonus * self.dive_hold_charge
        if self.diving:
            dive_mult = 1.0 + (self.dive_hold_max_mult - 1.0) * self.dive_hold_charge
            self.vy += self.dive_force * dive_mult * dt

        self.vy += self.gravity * dt
        if self.vy < -self.max_upward_air_speed:
            self.vy = -self.max_upward_air_speed
        if self.vy > dynamic_max_fall:
            self.vy = dynamic_max_fall

        self.x += self.vx * dt
        self.y += self.vy * dt
        top_limit = self.radius + self.air_top_margin
        if self.y < top_limit:
            self.y = top_limit
            if self.vy < 0.0:
                self.vy = 0.0
        if self.y < self.airborne_apex_y:
            self.airborne_apex_y = self.y

        ground_y, slope, on_ground = terrain.sample(self.x)
        if not on_ground:
            return

        if self.y + self.radius < ground_y:
            return

        impact = self._landing_impact_angle(slope)
        hard_impact = impact > self.hit_angle_threshold
        downhill_landing = slope > 0.0
        hard_impact_loss = hard_impact and not downhill_landing
        incoming_speed = math.hypot(self.vx, self.vy)

        tangent_x = 1.0
        tangent_y = slope
        length = math.hypot(tangent_x, tangent_y)
        if length > 1e-6:
            tangent_x /= length
            tangent_y /= length
        else:
            tangent_x, tangent_y = 1.0, 0.0

        downward_speed = max(0.0, self.vy)
        tangent_speed = self.vx * tangent_x + self.vy * tangent_y
        jump_landing = self.airborne_time >= self.jump_landing_min_airtime
        landed_downhill = slope >= self.landing_slope_threshold
        landed_uphill = slope <= -self.landing_slope_threshold

        if jump_landing:
            if landed_downhill and downward_speed > 0.0:
                transferred = incoming_speed * self.downhill_landing_transfer
                tangent_speed = max(tangent_speed, transferred)
                fall_ratio = min(1.0, downward_speed / max(1.0, self.max_fall_speed))
                gain_mult = 1.0 + self.jump_downhill_speed_gain * (0.45 + 0.55 * fall_ratio)
                tangent_speed *= gain_mult
                self.downhill_momentum_timer = self.downhill_momentum_hold_time
                self.downhill_momentum_cap = max(
                    self.downhill_momentum_cap,
                    min(self.downhill_momentum_abs_cap, tangent_speed),
                )
            elif landed_uphill and downward_speed > 0.0:
                tangent_speed *= self.jump_uphill_speed_loss
                # Uphill landing should clearly reset downhill carry.
                self.downhill_momentum_timer = 0.0
                self.downhill_momentum_cap = self.max_ground_speed

            floor_speed = self.min_ground_speed * 0.72
            speed_cap = self.max_ground_speed
            if landed_downhill:
                speed_cap = max(speed_cap, self.downhill_momentum_cap)
            tangent_speed = max(floor_speed, min(speed_cap, tangent_speed))
            tangent_speed = min(self.total_speed_abs_cap, tangent_speed)

            self.vx = tangent_x * tangent_speed
            self.vy = tangent_y * tangent_speed
            self.y = ground_y - self.radius
            self.on_ground = True
            self.current_air_speed_cap = self.max_air_speed
            self.airborne_time = 0.0
            self.airborne_launch_y = self.y
            self.airborne_apex_y = self.y
            self.dive_hold_time = 0.0
            self.dive_hold_charge = 0.0
            self.airborne_peak_dive_charge = 0.0
            return

        preserve_downhill_momentum = downhill_landing and downward_speed > 0.0 and slope >= self.downhill_landing_min_slope
        if preserve_downhill_momentum:
            transferred_speed = incoming_speed * self.downhill_landing_transfer
            tangent_speed = max(tangent_speed, transferred_speed)
            self.downhill_momentum_timer = self.downhill_momentum_hold_time
            self.downhill_momentum_cap = max(
                self.downhill_momentum_cap,
                min(self.downhill_momentum_abs_cap, transferred_speed),
            )
        else:
            transferred_speed = 0.0
        carry_active = (
            self.downhill_momentum_timer > 0.0
            or self.downhill_momentum_cap > self.max_ground_speed * 1.03
        )
        uphill_carry_landing = False
        if (
            not preserve_downhill_momentum
            and slope < -self.downhill_landing_min_slope
            and downward_speed > 0.0
            and carry_active
        ):
            uphill_carry_landing = True
            carried_speed = incoming_speed * self.uphill_carry_transfer
            tangent_speed = max(tangent_speed, carried_speed)
            transferred_speed = max(transferred_speed, carried_speed)
            self.downhill_momentum_cap = max(
                self.downhill_momentum_cap,
                min(self.downhill_momentum_abs_cap, carried_speed),
            )
        if carry_active and slope < 0.0:
            hard_impact_loss = False
        dive_charge_memory = max(self.airborne_peak_dive_charge, self.dive_hold_charge)
        miss_loss = 0.0
        mismatch_loss = 0.0
        made_pump = False
        if self.diving and slope > self.pump_downhill_slope and downward_speed > self.pump_min_down_speed:
            speed_ratio = min(1.0, downward_speed / max(1.0, self.max_fall_speed))
            slope_ratio = min(1.0, (slope - self.pump_downhill_slope) / 0.4)
            pump_quality = speed_ratio * slope_ratio * (0.55 + 0.45 * self.skill) * (0.7 + 0.3 * self.risk)
            streak_ratio = min(1.0, min(self.pump_streak_max, self.pump_streak) / max(1e-6, self.pump_streak_max))
            streak_multiplier = 1.0 + (streak_ratio ** 1.1) * self.pump_streak_mult * self.pump_streak_max
            charge_multiplier = 1.0 + (dive_charge_memory ** 1.3) * self.dive_charge_pump_bonus
            quality_multiplier = 0.82 + 1.28 * pump_quality
            tangent_speed += (
                downward_speed
                * self.pump_speed_gain
                * pump_quality
                * quality_multiplier
                * streak_multiplier
                * charge_multiplier
            )
            self.last_pump_quality = pump_quality
            self.pump_streak = min(
                self.pump_streak_max,
                self.pump_streak + self.pump_streak_step * (0.65 + pump_quality * 0.6),
            )
            made_pump = True
        else:
            if (
                not self.diving
                and not carry_active
                and slope < -self.missed_pump_downhill_slope
                and downward_speed > self.missed_pump_min_down_speed
            ):
                miss_speed_ratio = min(1.0, downward_speed / max(1.0, self.max_fall_speed))
                miss_slope_ratio = min(1.0, (-slope - self.missed_pump_downhill_slope) / 0.45)
                miss_loss = self.missed_pump_speed_loss * (
                    0.55 + 0.45 * miss_speed_ratio + 0.35 * miss_slope_ratio
                )
                tangent_speed *= max(0.4, 1.0 - miss_loss)
            self.last_pump_quality *= 0.45
            self.pump_streak *= 0.72

        if hard_impact_loss:
            tangent_speed *= self.hit_speed_loss
            self.perfect_slide_chain = 0
            self.last_pump_quality *= 0.25
            self.pump_streak = 0.0
        elif not made_pump and slope <= 0.0:
            self.pump_streak *= 0.9

        if slope < self.uphill_mismatch_slope and downward_speed > self.uphill_mismatch_min_down_speed:
            if carry_active:
                mismatch_loss = 0.0
            else:
                uphill_ratio = min(1.0, (-slope + self.uphill_mismatch_slope) / 0.65)
                down_ratio = min(
                    1.0,
                    (downward_speed - self.uphill_mismatch_min_down_speed)
                    / max(1.0, self.max_fall_speed - self.uphill_mismatch_min_down_speed),
                )
                mismatch_ratio = min(1.0, impact / math.pi)
                mismatch_loss = self.uphill_mismatch_speed_loss * (
                    0.25 + 0.75 * uphill_ratio
                ) * (
                    0.25 + 0.75 * down_ratio
                ) * (
                    0.2 + 0.8 * mismatch_ratio
                )
                carry_ratio = min(
                    1.0,
                    max(0.0, self.downhill_momentum_cap - self.max_ground_speed) / max(1.0, self.max_ground_speed),
                )
                timer_ratio = min(
                    1.0,
                    self.downhill_momentum_timer / max(1e-6, self.downhill_momentum_hold_time),
                )
                carry_protection = max(carry_ratio, timer_ratio)
                mismatch_loss *= max(0.0, 1.0 - self.uphill_mismatch_carry_reduction * carry_protection)
                tangent_speed *= max(self.uphill_mismatch_min_keep, 1.0 - mismatch_loss)
                self.last_pump_quality *= 0.2
                self.pump_streak *= 0.35

        speed_cap = max(self.max_ground_speed, self.downhill_momentum_cap)
        if preserve_downhill_momentum or uphill_carry_landing:
            speed_cap = max(speed_cap, min(self.downhill_landing_speed_cap, transferred_speed))
        jump_height = max(0.0, self.airborne_launch_y - self.airborne_apex_y)
        jump_ratio = min(1.0, jump_height / max(1.0, self.horizontal_jump_ref_height))
        streak_ratio = min(1.0, min(self.pump_streak_max, self.pump_streak) / max(1.0, self.pump_streak_max))
        horizontal_bonus = 0.0
        if made_pump and self.horizontal_pump_gain > 0.0:
            pump_push = downward_speed * self.horizontal_pump_gain * (0.45 + 0.55 * self.last_pump_quality)
            pump_push *= 1.0 + self.horizontal_charge_bonus * dive_charge_memory
            pump_push *= 1.0 + self.horizontal_jump_bonus * jump_ratio
            pump_push *= 1.0 + 0.35 * streak_ratio
            horizontal_bonus += min(self.horizontal_pump_cap, pump_push)

        if miss_loss > 0.0 and self.horizontal_miss_penalty > 0.0:
            horizontal_bonus -= max(self.min_ground_speed, abs(self.vx)) * miss_loss * self.horizontal_miss_penalty
        if mismatch_loss > 0.0 and self.horizontal_uphill_penalty > 0.0:
            horizontal_bonus -= max(self.min_ground_speed, abs(self.vx)) * mismatch_loss * self.horizontal_uphill_penalty

        if horizontal_bonus != 0.0:
            tangent_x_abs = max(self.horizontal_min_tangent, abs(tangent_x))
            tangent_speed += horizontal_bonus / tangent_x_abs

        if (
            not hard_impact_loss
            and self.vertical_speed_reward > 0.0
            and jump_height > self.vertical_reward_min_height
        ):
            bonus_height = jump_height - self.vertical_reward_min_height
            slope_factor = 1.0 + max(-0.08, slope) * self.vertical_reward_downhill_bonus
            apex_factor = 1.0 + min(0.35, jump_height / 120.0)
            airtime_factor = min(1.4, 0.8 + self.airborne_time * 1.05)
            reward = bonus_height * self.vertical_speed_reward * slope_factor * apex_factor * airtime_factor
            tangent_speed += min(self.vertical_speed_reward_cap, reward)
            speed_cap += min(self.vertical_speed_cap_bonus, bonus_height * self.vertical_speed_cap_gain)

        floor_speed = self.min_ground_speed * 0.72
        tangent_speed = max(floor_speed, min(speed_cap, tangent_speed))
        tangent_speed = min(self.total_speed_abs_cap, tangent_speed)

        self.vx = tangent_x * tangent_speed
        self.vy = tangent_y * tangent_speed
        self.y = ground_y - self.radius
        self.on_ground = True
        self.current_air_speed_cap = self.max_air_speed
        self.airborne_time = 0.0
        self.airborne_launch_y = self.y
        self.airborne_apex_y = self.y
        self.dive_hold_time = 0.0
        self.dive_hold_charge = 0.0
        self.airborne_peak_dive_charge = 0.0

    def _register_takeoff(self):
        # y-down coordinates: upward launch means negative vertical speed.
        if self.vy < -self.perfect_takeoff_vy:
            self.perfect_slide_chain += 1
        else:
            self.perfect_slide_chain = 0

    def _landing_impact_angle(self, slope: float) -> float:
        normal_angle = math.atan2(1.0, -slope)
        velocity_angle = math.atan2(self.vy, self.vx if abs(self.vx) > 1e-6 else 1e-6)
        delta = (normal_angle - velocity_angle + math.pi) % (2.0 * math.pi) - math.pi
        return abs(delta)
