import math
import random

import config
from shared import EntityTemplate


class JetpackFollower(EntityTemplate):
    def _init_entity(self, follower_data: dict):
        self.size = float(getattr(config, "JETPACK_PLAYER_SIZE", 30.0))
        self.radius = self.size * 0.5

        self.gravity = float(getattr(config, "JETPACK_GRAVITY", 1080.0))
        self.thrust = float(getattr(config, "JETPACK_THRUST", 1820.0))
        self.max_fall_speed = float(getattr(config, "JETPACK_MAX_FALL_SPEED", 520.0))
        self.max_rise_speed = float(getattr(config, "JETPACK_MAX_RISE_SPEED", 460.0))

        self.reaction_distance = float(getattr(config, "JETPACK_REACTION_DISTANCE", 250.0))
        self.reaction_distance_scale_min = float(getattr(config, "JETPACK_REACTION_DISTANCE_SCALE_MIN", 0.72))
        self.reaction_distance_scale_max = float(getattr(config, "JETPACK_REACTION_DISTANCE_SCALE_MAX", 1.02))
        self.obstacle_horizon_mult = float(getattr(config, "JETPACK_OBSTACLE_HORIZON_MULT", 1.1))
        self.rocket_horizon_mult = float(getattr(config, "JETPACK_ROCKET_HORIZON_MULT", 1.2))
        self.score_horizon_mult = float(getattr(config, "JETPACK_SCORE_HORIZON_MULT", 1.35))
        self.avoid_margin = float(getattr(config, "JETPACK_AVOID_MARGIN", 14.0))
        self.target_jitter = float(getattr(config, "JETPACK_TARGET_JITTER", 16.0))
        self.thrust_buffer = float(getattr(config, "JETPACK_THRUST_BUFFER", 14.0))
        self.control_gain = float(getattr(config, "JETPACK_CONTROL_GAIN", 3.8))
        self.control_deadband = float(getattr(config, "JETPACK_CONTROL_DEADBAND", 14.0))
        self.boundary_margin = float(getattr(config, "JETPACK_BOUNDARY_MARGIN", 36.0))
        self.boundary_soft_cap = float(getattr(config, "JETPACK_BOUNDARY_SOFT_CAP", 210.0))
        self.obstacle_extra_clearance = float(getattr(config, "JETPACK_OBSTACLE_EXTRA_CLEARANCE", 18.0))
        self.rocket_evade_multiplier = float(getattr(config, "JETPACK_ROCKET_EVADE_MULTIPLIER", 6.4))
        self.lookahead_min_speed = float(getattr(config, "JETPACK_LOOKAHEAD_MIN_SPEED", 70.0))
        self.hazard_escape_speed = float(getattr(config, "JETPACK_HAZARD_ESCAPE_SPEED", 980.0))
        self.max_controlled_descent = float(
            getattr(config, "JETPACK_MAX_CONTROLLED_DESCENT", self.max_fall_speed * 0.72)
        )
        self.escape_up_accel = float(getattr(config, "JETPACK_ESCAPE_UP_ACCEL", self.hazard_escape_speed * 3.1))
        self.escape_down_accel = float(getattr(config, "JETPACK_ESCAPE_DOWN_ACCEL", self.hazard_escape_speed * 1.8))
        self.escape_intent_attack = float(getattr(config, "JETPACK_ESCAPE_INTENT_ATTACK", 5.2))
        self.escape_intent_release = float(getattr(config, "JETPACK_ESCAPE_INTENT_RELEASE", 2.6))
        self.escape_downward_bias = float(getattr(config, "JETPACK_ESCAPE_DOWNWARD_BIAS", 1.26))
        self.downward_target_penalty = float(getattr(config, "JETPACK_DOWNWARD_TARGET_PENALTY", 0.038))
        self.escape_up_max_vy = float(getattr(config, "JETPACK_ESCAPE_UP_MAX_VY", self.max_rise_speed * 0.92))
        self.escape_down_max_vy = float(
            getattr(config, "JETPACK_ESCAPE_DOWN_MAX_VY", self.max_fall_speed * 0.54)
        )
        self.target_move_penalty = float(getattr(config, "JETPACK_TARGET_MOVE_PENALTY", 0.014))
        self.hover_thrust_base = float(getattr(config, "JETPACK_HOVER_THRUST_BASE", 0.58))
        self.hover_thrust_response = float(getattr(config, "JETPACK_HOVER_THRUST_RESPONSE", 6.8))
        self.vertical_oscillation_amplitude = float(getattr(config, "JETPACK_VERTICAL_OSCILLATION_AMPLITUDE", 20.0))
        self.vertical_oscillation_speed = float(getattr(config, "JETPACK_VERTICAL_OSCILLATION_SPEED", 1.85))
        self.steer_assist = float(getattr(config, "JETPACK_STEER_ASSIST", 0.34))
        self.target_smoothing = float(getattr(config, "JETPACK_TARGET_SMOOTHING", 6.8))

        self.separation_gap_mult = float(getattr(config, "JETPACK_SEPARATION_GAP", 3.8))
        self.separation_strength = float(getattr(config, "JETPACK_SEPARATION_STRENGTH", 5.0))
        self.separation_x_range_mult = float(getattr(config, "JETPACK_SEPARATION_X_RANGE", 8.0))
        self.path_variation = float(getattr(config, "JETPACK_PATH_VARIATION", 2.4))

        self.x_sway_amplitude = float(getattr(config, "JETPACK_X_SWAY_AMPLITUDE", 34.0))
        self.x_sway_speed = float(getattr(config, "JETPACK_X_SWAY_SPEED", 1.3))
        self.x_sway_lerp = float(getattr(config, "JETPACK_X_SWAY_LERP", 6.0))
        self.x_sway_jitter = float(getattr(config, "JETPACK_X_SWAY_JITTER", 0.2))

        self.cruise_wobble_amp = float(getattr(config, "JETPACK_CRUISE_WOBBLE_AMPLITUDE", 42.0))
        self.cruise_wobble_speed = float(getattr(config, "JETPACK_CRUISE_WOBBLE_SPEED", 1.1))

        # Keep variance between followers so movement patterns diverge naturally.
        self.skill = random.uniform(0.82, 1.0)
        self.miss_chance = (1.0 - self.skill) * 0.01

        # Maintain strong control but avoid all players reacting at the same early distance.
        self.gravity *= 0.9 + (1.0 - self.skill) * 0.12
        self.thrust *= 1.05 + self.skill * 0.28
        self.reaction_distance *= random.uniform(self.reaction_distance_scale_min, self.reaction_distance_scale_max)

        self.base_x = self.x
        self.x_sway_phase = random.uniform(0.0, math.tau)
        self.x_sway_rate = self.x_sway_speed * (1.0 + random.uniform(-self.x_sway_jitter, self.x_sway_jitter))
        self.cruise_phase = random.uniform(0.0, math.tau)
        self.target_phase = random.uniform(0.0, math.tau)
        self.idle_vertical_phase = random.uniform(0.0, math.tau)
        cruise_bias_range = float(getattr(config, "JETPACK_CRUISE_BIAS_RANGE", 120.0))
        self.cruise_bias = random.uniform(-cruise_bias_range, cruise_bias_range)
        drift_amp_min = float(getattr(config, "JETPACK_CRUISE_BIAS_DRIFT_MIN", 8.0))
        drift_amp_max = float(getattr(config, "JETPACK_CRUISE_BIAS_DRIFT_MAX", 22.0))
        drift_speed_min = float(getattr(config, "JETPACK_CRUISE_BIAS_DRIFT_SPEED_MIN", 0.35))
        drift_speed_max = float(getattr(config, "JETPACK_CRUISE_BIAS_DRIFT_SPEED_MAX", 0.85))
        self.cruise_bias_drift_amp = random.uniform(min(drift_amp_min, drift_amp_max), max(drift_amp_min, drift_amp_max))
        self.cruise_bias_drift_speed = random.uniform(min(drift_speed_min, drift_speed_max), max(drift_speed_min, drift_speed_max))
        self.cruise_bias_drift_phase = random.uniform(0.0, math.tau)

        self.target_y = self.y
        self.target_y_smoothed = self.y
        self.thrusting = False
        self.thrust_intensity = self.hover_thrust_base
        self.escape_intent = 0.0

    def update(
        self,
        dt,
        arena,
        upcoming_obstacles,
        next_rocket,
        game_time,
        difficulty=0.0,
        world_speed=0.0,
        nearby_players=None,
    ):
        if not self.alive:
            self.update_fade()
            self.thrusting = False
            return

        if upcoming_obstacles is None:
            upcoming_obstacles = []
        elif not isinstance(upcoming_obstacles, (list, tuple)):
            upcoming_obstacles = [upcoming_obstacles]
        if nearby_players is None:
            nearby_players = []

        target_y, urgency = self._pick_target_y(
            arena,
            upcoming_obstacles,
            next_rocket,
            game_time,
            difficulty,
            world_speed,
        )

        # Keep players visibly "alive" in calm sections instead of hovering perfectly.
        if urgency < 0.35:
            bob_strength = 1.0 - urgency / 0.35
            target_y += (
                math.sin(game_time * self.vertical_oscillation_speed + self.idle_vertical_phase)
                * self.vertical_oscillation_amplitude
                * bob_strength
                * 0.45
            )

        if nearby_players:
            # Keep followers from collapsing into one lane while still prioritizing danger response.
            separation_scale = max(0.2, 1.0 - urgency * 0.8)
            target_y += self._separation_offset(nearby_players, game_time) * separation_scale

        jitter_scale = max(0.0, 0.18 - urgency * 0.16)
        target_y += math.sin(game_time * 2.3 + self.target_phase) * self.target_jitter * 0.18 * jitter_scale
        target_y = arena.clamp_y(target_y, self.radius)
        smooth_gain = self.target_smoothing * (0.65 + urgency * 0.85)
        smooth_alpha = min(1.0, max(0.0, smooth_gain * dt))
        self.target_y_smoothed += (target_y - self.target_y_smoothed) * smooth_alpha
        target_y = self.target_y_smoothed
        self.target_y = target_y
        desired_escape_intent = self._compute_escape_intent(arena, upcoming_obstacles, next_rocket)
        self._update_escape_intent(desired_escape_intent, dt)

        desired_vy = (target_y - self.y) * self.control_gain
        max_down = min(
            self.max_controlled_descent,
            self.max_fall_speed * (0.34 + 0.18 * urgency),
        )
        max_up = self.max_rise_speed * (0.58 + 0.42 * urgency)
        desired_vy = max(-max_up, min(max_down, desired_vy))

        top_guard = arena.top + self.radius + self.boundary_margin
        bottom_guard = arena.bottom - self.radius - self.boundary_margin

        if self.y < top_guard and self.vy < -self.boundary_soft_cap:
            self.vy = -self.boundary_soft_cap
        if self.y > bottom_guard and self.vy > self.boundary_soft_cap:
            self.vy = self.boundary_soft_cap

        max_speed_ref = max(self.max_fall_speed, self.max_rise_speed, 1.0)
        velocity_error = desired_vy - self.vy
        deadband = max(6.0, self.control_deadband * (0.65 + (1.0 - urgency) * 0.45))
        # Jetpack only provides lift. Falling should primarily come from gravity.
        target_thrust = 0.0
        if velocity_error < -deadband:
            lift_need = min(1.0, max(0.0, (-velocity_error) / max_speed_ref))
            target_thrust = self.hover_thrust_base + lift_need * (0.58 + urgency * 0.18)

        # Boundary protection: hard lift near floor, cut lift near ceiling.
        if self.y > bottom_guard:
            target_thrust = max(target_thrust, 0.92)
        elif self.y < top_guard:
            target_thrust = 0.0

        target_thrust = max(0.0, min(1.0, target_thrust))
        response = self.hover_thrust_response * (0.8 + urgency * 0.9)
        blend = min(1.0, response * dt)
        self.thrust_intensity += (target_thrust - self.thrust_intensity) * blend
        # Fire should show while actively commanding upward thrust,
        # not during passive falling or residual smoothing.
        self.thrusting = target_thrust > 0.14 and self.thrust_intensity > 0.16

        gravity_scale = 1.0 + difficulty * 0.06
        self.vy += self.gravity * gravity_scale * dt
        self.vy -= self.thrust * self.thrust_intensity * dt
        self._apply_escape_force(dt)

        self.vy = max(-self.max_rise_speed, min(self.max_fall_speed, self.vy))
        self.y += self.vy * dt

        # Keep followers safely inside vertical bounds without hard elimination.
        top_limit = arena.top + self.radius
        bottom_limit = arena.bottom - self.radius
        if self.y < top_limit:
            self.y = top_limit
            self.vy = max(0.0, self.vy * 0.35)
        elif self.y > bottom_limit:
            self.y = bottom_limit
            self.vy = min(0.0, self.vy * 0.35)

        sway_amp = self.x_sway_amplitude * (0.75 + (1.0 - urgency) * 0.25)
        target_x = self.base_x + math.sin(game_time * self.x_sway_rate + self.x_sway_phase) * sway_amp
        min_x = arena.left + self.radius
        max_x = arena.right - self.radius
        target_x = max(min_x, min(max_x, target_x))

        lerp_strength = min(1.0, self.x_sway_lerp * dt)
        self.x += (target_x - self.x) * lerp_strength

    def _pick_target_y(self, arena, upcoming_obstacles, next_rocket, game_time, difficulty, world_speed):
        cruise_drift = (
            math.sin(game_time * self.cruise_bias_drift_speed + self.cruise_bias_drift_phase)
            * self.cruise_bias_drift_amp
        )
        center_target = (
            arena.center_y
            + self.cruise_bias
            + cruise_drift
            + math.sin(game_time * self.cruise_wobble_speed + self.cruise_phase) * self.cruise_wobble_amp
        )
        center_target = arena.clamp_y(center_target, self.radius)

        candidates = [arena.clamp_y(center_target, self.radius)]
        obstacle_urgency = 0.0
        obstacle_horizon = max(self.radius * 3.0, self.reaction_distance * self.obstacle_horizon_mult)

        for obstacle in (upcoming_obstacles or [])[:3]:
            if obstacle is None:
                continue
            distance_x = obstacle.x - self.x
            if distance_x > obstacle_horizon:
                continue

            half_clearance = (
                obstacle.height * 0.5
                + self.radius
                + self.avoid_margin
                + self.obstacle_extra_clearance
            )
            top_safe = arena.clamp_y(obstacle.y - half_clearance, self.radius)
            bottom_safe = arena.clamp_y(obstacle.y + half_clearance, self.radius)
            extra_offset = self.radius * 0.55
            candidates.extend(
                (
                    top_safe,
                    bottom_safe,
                    arena.clamp_y(top_safe - extra_offset, self.radius),
                    arena.clamp_y(bottom_safe + extra_offset, self.radius),
                )
            )
            obstacle_urgency = max(
                obstacle_urgency,
                min(1.0, max(0.0, 1.0 - distance_x / max(1.0, obstacle_horizon))),
            )

        rocket_urgency = 0.0
        if next_rocket is not None:
            distance_x = next_rocket.x - self.x
            rocket_horizon = max(self.radius * 3.5, self.reaction_distance * self.rocket_horizon_mult)
            if distance_x <= rocket_horizon:
                evade_span = self.radius * self.rocket_evade_multiplier + self.avoid_margin + self.obstacle_extra_clearance
                target_up = arena.clamp_y(next_rocket.y - evade_span, self.radius)
                target_down = arena.clamp_y(next_rocket.y + evade_span, self.radius)
                extra_offset = self.radius * 0.6
                candidates.extend(
                    (
                        target_up,
                        target_down,
                        arena.clamp_y(target_up - extra_offset, self.radius),
                        arena.clamp_y(target_down + extra_offset, self.radius),
                    )
                )
                rocket_urgency = min(1.0, max(0.0, 1.0 - distance_x / max(1.0, rocket_horizon)))

        # De-duplicate candidate lanes so scoring remains stable.
        unique_candidates = []
        for candidate in candidates:
            if not any(abs(candidate - existing) < 1.0 for existing in unique_candidates):
                unique_candidates.append(candidate)

        best_target = unique_candidates[0]
        best_score = float("inf")
        move_penalty = self.target_move_penalty * (0.75 + (1.0 - self.skill) * 0.8)
        for candidate in unique_candidates:
            score = self._target_score(candidate, center_target, arena, upcoming_obstacles, world_speed)
            score += abs(candidate - self.y) * move_penalty
            if candidate > self.y:
                score += (candidate - self.y) * self.downward_target_penalty
            if score < best_score:
                best_score = score
                best_target = candidate

        urgency = max(obstacle_urgency, rocket_urgency)
        if urgency <= 0.03:
            return center_target, 0.0

        blend = max(0.0, 0.4 - urgency * 0.45)
        target = best_target * (1.0 - blend) + center_target * blend
        return target, urgency

    def _separation_offset(self, nearby_players, game_time: float) -> float:
        separation_force = 0.0
        preferred_gap = max(self.radius, self.radius * self.separation_gap_mult)
        x_range = max(self.radius * 2.0, self.radius * self.separation_x_range_mult)

        for other in nearby_players:
            if other is self or not other.alive:
                continue

            dx = abs(other.x - self.x)
            if dx > x_range:
                continue

            dy = self.y - other.y
            distance_y = abs(dy)
            if distance_y >= preferred_gap:
                continue

            if distance_y < 0.001:
                phase_mix = game_time * 1.3 + self.target_phase + getattr(other, "target_phase", 0.0)
                direction = 1.0 if math.sin(phase_mix) >= 0 else -1.0
            else:
                direction = 1.0 if dy >= 0 else -1.0

            y_weight = 1.0 - distance_y / preferred_gap
            x_weight = 1.0 - dx / x_range
            separation_force += direction * y_weight * x_weight

        max_offset = self.radius * 2.6
        raw_offset = separation_force * self.separation_strength * 0.28
        return max(-max_offset, min(max_offset, raw_offset))

    def _choose_escape_target(self, target_up: float, target_down: float) -> float:
        up_dist = abs(self.y - target_up)
        down_dist = abs(self.y - target_down) * self.escape_downward_bias
        return target_up if up_dist <= down_dist else target_down

    def _update_escape_intent(self, desired_intent: float, dt: float):
        desired = max(-1.0, min(1.0, desired_intent))
        response = self.escape_intent_attack if abs(desired) > abs(self.escape_intent) else self.escape_intent_release
        alpha = min(1.0, max(0.0, response * dt))
        self.escape_intent += (desired - self.escape_intent) * alpha
        if abs(desired) < 0.001:
            decay = max(0.0, 1.0 - self.escape_intent_release * dt * 0.75)
            self.escape_intent *= decay
            if abs(self.escape_intent) < 0.001:
                self.escape_intent = 0.0

    def _apply_escape_force(self, dt: float):
        if self.escape_intent < -0.001:
            intent = -self.escape_intent
            self.vy -= self.escape_up_accel * intent * dt
            self.vy = max(-self.escape_up_max_vy, self.vy)
        elif self.escape_intent > 0.001:
            intent = self.escape_intent
            self.vy += self.escape_down_accel * intent * dt
            self.vy = min(self.escape_down_max_vy, self.vy)

    def _compute_escape_intent(self, arena, upcoming_obstacles, next_rocket) -> float:
        escape_padding = self.radius * 0.45 + self.avoid_margin * 0.35
        best_intent = 0.0
        best_strength = 0.0

        for obstacle in (upcoming_obstacles or [])[:2]:
            if obstacle is None:
                continue

            overlap_x = self.radius + obstacle.width * 0.5 + 95.0
            dx = obstacle.x - self.x
            if abs(dx) > overlap_x:
                continue

            hazard_half = (
                obstacle.height * 0.5
                + self.radius
                + self.avoid_margin
                + self.obstacle_extra_clearance
                + 8.0
            )
            top = obstacle.y - hazard_half
            bottom = obstacle.y + hazard_half
            if top <= self.y <= bottom:
                target_up = arena.clamp_y(top - escape_padding, self.radius)
                target_down = arena.clamp_y(bottom + escape_padding, self.radius)
                target = self._choose_escape_target(target_up, target_down)
                moving_down = target > self.y
                direction = 1.0 if moving_down else -1.0
                center = (top + bottom) * 0.5
                half_span = max(1.0, (bottom - top) * 0.5)
                depth = max(0.0, 1.0 - abs(self.y - center) / half_span)
                x_weight = max(0.0, 1.0 - abs(dx) / max(1.0, overlap_x))
                strength = min(1.0, 0.25 + depth * 0.5 + x_weight * 0.35)
                if strength > best_strength:
                    best_strength = strength
                    best_intent = direction * strength

        if next_rocket is None:
            return best_intent

        overlap_x = self.radius + next_rocket.width * 0.5 + 130.0
        dx = next_rocket.x - self.x
        if abs(dx) > overlap_x:
            return best_intent

        hazard_half = next_rocket.height * 0.5 + self.radius + self.avoid_margin * 1.6 + 6.0
        top = next_rocket.y - hazard_half
        bottom = next_rocket.y + hazard_half
        if top <= self.y <= bottom:
            target_up = arena.clamp_y(top - escape_padding, self.radius)
            target_down = arena.clamp_y(bottom + escape_padding, self.radius)
            target = self._choose_escape_target(target_up, target_down)
            moving_down = target > self.y
            direction = 1.0 if moving_down else -1.0
            center = (top + bottom) * 0.5
            half_span = max(1.0, (bottom - top) * 0.5)
            depth = max(0.0, 1.0 - abs(self.y - center) / half_span)
            x_weight = max(0.0, 1.0 - abs(dx) / max(1.0, overlap_x))
            strength = min(1.0, 0.35 + depth * 0.55 + x_weight * 0.35)
            if strength > best_strength:
                best_strength = strength
                best_intent = direction * strength

        return best_intent

    def _target_score(self, target_y, center_target, arena, obstacles, world_speed):
        score = abs(target_y - center_target) * 0.013
        score += math.sin(target_y * 0.03 + self.target_phase) * self.path_variation

        top_edge = arena.top + self.radius
        bottom_edge = arena.bottom - self.radius
        edge_clearance = min(target_y - top_edge, bottom_edge - target_y)
        if edge_clearance < self.boundary_margin * 1.1:
            score += (self.boundary_margin * 1.1 - edge_clearance) * 2.5

        if obstacles:
            horizon = max(self.radius * 3.0, self.reaction_distance * self.score_horizon_mult)
            for obstacle in obstacles[:4]:
                if obstacle is None:
                    continue
                distance_x = obstacle.x - self.x
                if distance_x < -obstacle.width:
                    continue

                weight = max(0.15, 1.0 - max(0.0, distance_x) / max(1.0, horizon))
                hazard_half = obstacle.height * 0.5 + self.radius + self.avoid_margin + self.obstacle_extra_clearance
                hazard_top = obstacle.y - hazard_half
                hazard_bottom = obstacle.y + hazard_half

                if hazard_top <= target_y <= hazard_bottom:
                    score += 420.0 * weight
                else:
                    if target_y < hazard_top:
                        clearance = hazard_top - target_y
                    else:
                        clearance = target_y - hazard_bottom
                    if clearance < 46.0:
                        score += (46.0 - clearance) * 2.2 * weight

                effective_speed = max(
                    self.lookahead_min_speed,
                    float(world_speed) * float(getattr(obstacle, "speed_multiplier", 1.0)),
                )
                ttc = max(0.05, max(0.0, distance_x) / effective_speed)
                required_rate = abs(target_y - self.y) / ttc
                rate_cap = self.max_rise_speed * 0.95
                if required_rate > rate_cap:
                    score += (required_rate - rate_cap) * 0.95 * weight

        return score
