import math
import random

import pygame

import config
from shared import EntityTemplate


class SuperFollowerBrosPlayer(EntityTemplate):
    def _init_entity(self, follower_data: dict):
        self.radius = float(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_RADIUS", 10.0))

        self.gravity = float(getattr(config, "SUPER_FOLLOWER_BROS_GRAVITY", 1200.0))
        self.max_fall_speed = float(getattr(config, "SUPER_FOLLOWER_BROS_MAX_FALL_SPEED", 900.0))
        target_height = getattr(config, "SUPER_FOLLOWER_BROS_JUMP_HEIGHT", None)
        if target_height is not None:
            self.jump_velocity = -math.sqrt(2.0 * self.gravity * float(target_height))
        else:
            self.jump_velocity = float(getattr(config, "SUPER_FOLLOWER_BROS_JUMP_VELOCITY", -460.0))

        base_speed = float(getattr(config, "SUPER_FOLLOWER_BROS_RUN_SPEED", 140.0))
        variance = float(getattr(config, "SUPER_FOLLOWER_BROS_RUN_SPEED_VARIANCE", 20.0))
        seed = int(getattr(config, "DAY_NUMBER", 1))
        self.rng = random.Random(seed + self._seed_from_id(self.id))
        self.run_speed = max(40.0, base_speed + self.rng.uniform(-variance, variance))

        self.jump_cooldown = float(getattr(config, "SUPER_FOLLOWER_BROS_JUMP_COOLDOWN", 0.18))
        self.jump_timer = 0.0

        self.on_ground = False
        self.finished = False
        self.finish_time = None
        self.best_x = self.x
        self.bumped_block = None

        self.power_level = 0
        self.small_radius = self.radius
        self.big_radius = self.radius * float(getattr(config, "SUPER_FOLLOWER_BROS_BIG_SIZE_MULTIPLIER", 1.5))
        self.star_until = 0.0
        self.hurt_until = 0.0
        self.fire_timer = 0.0
        self.fire_cooldown = float(getattr(config, "SUPER_FOLLOWER_BROS_FIRE_COOLDOWN", 0.7))
        self.fire_range = float(getattr(config, "SUPER_FOLLOWER_BROS_FIRE_RANGE", 260.0))
        self.fire_vertical_tolerance = float(getattr(config, "SUPER_FOLLOWER_BROS_FIRE_VERTICAL_TOLERANCE", 60.0))
        self.fire_chance = float(getattr(config, "SUPER_FOLLOWER_BROS_FIRE_CHANCE", 0.35))

        self.aim_bias = self.rng.uniform(-0.1, 0.1)
        self.jump_chance = float(getattr(config, "SUPER_FOLLOWER_BROS_RANDOM_JUMP_CHANCE", 0.04))

        self.item_seek_chance = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_CHANCE", 0.55))
        self.item_seek_range = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_RANGE", 280.0))
        self.item_seek_backtrack = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_BACKTRACK", 24.0))
        self.item_seek_interval = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_INTERVAL", 0.25))
        self.item_seek_tolerance = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_TOLERANCE", 6.0))
        self.item_seek_max_adjust = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_MAX_ADJUST", 0.6))
        self.item_seek_drop = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SEEK_DROP", 40.0))
        self.item_seek_timer = 0.0
        self.item_target_index = None

        self.powerup_seek_chance = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_SEEK_CHANCE", 0.8))
        self.powerup_seek_range = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_SEEK_RANGE", 360.0))
        self.powerup_seek_backtrack = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_SEEK_BACKTRACK", 60.0))
        self.powerup_seek_interval = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_SEEK_INTERVAL", 0.2))
        self.powerup_seek_tolerance = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_SEEK_TOLERANCE", 10.0))
        self.powerup_seek_max_adjust = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_SEEK_MAX_ADJUST", 0.9))
        self.powerup_seek_timer = 0.0
        self.powerup_target = None

        self.max_jump_height = self._compute_jump_height()
        self.stuck_timeout = float(getattr(config, "SUPER_FOLLOWER_BROS_STUCK_TIMEOUT", 1.35))
        self.stuck_progress_ratio = float(getattr(config, "SUPER_FOLLOWER_BROS_STUCK_PROGRESS_RATIO", 0.35))
        self.stuck_wall_lookahead = float(getattr(config, "SUPER_FOLLOWER_BROS_STUCK_WALL_LOOKAHEAD", 24.0))
        self.stuck_speed_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_STUCK_SPEED_MULTIPLIER", 1.1))
        self.stuck_jump_cooldown_multiplier = float(
            getattr(config, "SUPER_FOLLOWER_BROS_STUCK_JUMP_COOLDOWN_MULTIPLIER", 0.65)
        )
        self.stuck_jump_boost = float(getattr(config, "SUPER_FOLLOWER_BROS_STUCK_JUMP_BOOST", 1.08))
        self.stuck_reverse_bias = float(getattr(config, "SUPER_FOLLOWER_BROS_STUCK_REVERSE_BIAS", 0.8))
        self.stuck_reverse_bias = max(0.0, min(1.0, self.stuck_reverse_bias))
        backtrack_window = getattr(config, "SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_TIME", (0.45, 1.1))
        if isinstance(backtrack_window, (list, tuple)) and len(backtrack_window) >= 2:
            self.stuck_backtrack_min = float(backtrack_window[0])
            self.stuck_backtrack_max = float(backtrack_window[1])
        else:
            duration = float(backtrack_window)
            self.stuck_backtrack_min = duration
            self.stuck_backtrack_max = duration
        if self.stuck_backtrack_max < self.stuck_backtrack_min:
            self.stuck_backtrack_min, self.stuck_backtrack_max = (
                self.stuck_backtrack_max,
                self.stuck_backtrack_min,
            )
        self.stuck_backtrack_min_distance = float(
            getattr(config, "SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_MIN_DISTANCE", 120.0)
        )
        self.stuck_blocked_extra_distance = float(
            getattr(config, "SUPER_FOLLOWER_BROS_STUCK_BLOCKED_EXTRA_DISTANCE", 120.0)
        )
        self.stuck_backtrack_hard_max_distance = float(
            getattr(config, "SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_HARD_MAX_DISTANCE", 420.0)
        )
        if self.stuck_backtrack_hard_max_distance < self.stuck_backtrack_min_distance:
            self.stuck_backtrack_hard_max_distance = self.stuck_backtrack_min_distance
        self.stuck_backtrack_max_time = float(
            getattr(config, "SUPER_FOLLOWER_BROS_STUCK_BACKTRACK_MAX_TIME", 3.0)
        )
        self.stuck_timer = 0.0
        self.stuck_recovery_timer = 0.0
        self.stuck_recovery_elapsed = 0.0
        self.stuck_recovery_start_x = self.x
        self.stuck_recovery_target_distance = 0.0
        self.stuck_direction = 1.0

        self.set_base_radius(self.radius)

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

    def _compute_jump_height(self) -> float:
        target_height = getattr(config, "SUPER_FOLLOWER_BROS_JUMP_HEIGHT", None)
        if target_height is not None:
            try:
                return float(target_height)
            except (TypeError, ValueError):
                return 0.0
        if self.gravity <= 0:
            return 0.0
        return (self.jump_velocity * self.jump_velocity) / (2.0 * self.gravity)

    def set_base_radius(self, radius: float) -> None:
        base = max(1.0, float(radius))
        self.small_radius = base
        self.big_radius = base * float(getattr(config, "SUPER_FOLLOWER_BROS_BIG_SIZE_MULTIPLIER", 1.5))
        if self.power_level >= 1:
            self.radius = self.big_radius
        else:
            self.radius = self.small_radius

    def apply_mushroom(self) -> None:
        if self.power_level < 1:
            self.power_level = 1
            delta = self.big_radius - self.radius
            self.radius = self.big_radius
            if delta > 0:
                self.y -= delta

    def apply_fireflower(self) -> None:
        self.power_level = 2
        delta = self.big_radius - self.radius
        self.radius = self.big_radius
        if delta > 0:
            self.y -= delta

    def apply_star(self, now: float) -> None:
        duration = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_DURATION", 10.0))
        self.star_until = max(self.star_until, now + duration)

    def reset_powerups(self) -> None:
        self.power_level = 0
        self.star_until = 0.0
        self.hurt_until = 0.0
        self.fire_timer = 0.0
        self.radius = self.small_radius

    def is_star_active(self, now: float) -> bool:
        return now < self.star_until

    def is_hurt_invincible(self, now: float) -> bool:
        return now < self.hurt_until

    def take_hit(self, now: float) -> bool:
        if self.is_hurt_invincible(now):
            return True
        if self.power_level >= 2:
            self.power_level = 1
            delta = self.radius - self.big_radius
            self.radius = self.big_radius
            if delta > 0:
                self.y += delta
        elif self.power_level == 1:
            self.power_level = 0
            delta = self.radius - self.small_radius
            self.radius = self.small_radius
            if delta > 0:
                self.y += delta
        else:
            return False
        invinc = float(getattr(config, "SUPER_FOLLOWER_BROS_HURT_INVINCIBLE_TIME", 1.0))
        if invinc > 0:
            self.hurt_until = now + invinc
        return True

    def request_fire(self, enemies, now: float):
        if self.power_level < 2:
            return None
        if self.fire_timer > 0.0:
            return None
        target = self._select_fire_target(enemies)
        if target is None:
            return None
        if self.rng.random() > self.fire_chance:
            return None
        self.fire_timer = self.fire_cooldown
        return 1.0 if target.x >= self.x else -1.0

    def _select_fire_target(self, enemies):
        if not enemies:
            return None
        best = None
        best_dist = None
        for enemy in enemies:
            if getattr(enemy, "state", "") == "dead":
                continue
            dx = enemy.x - self.x
            if dx <= 0:
                continue
            if abs(dx) > self.fire_range:
                continue
            if abs(enemy.y - self.y) > self.fire_vertical_tolerance:
                continue
            dist = abs(dx)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = enemy
        return best

    def _get_block_by_index(self, level, index):
        if level is None:
            return None
        blocks = getattr(level, "blocks", None)
        if not blocks:
            return None
        if index is None:
            return None
        if 0 <= index < len(blocks):
            return blocks[index]
        return None

    def _update_item_target(self, dt: float, level) -> None:
        self.item_seek_timer += dt

        if self.item_target_index is not None:
            block = self._get_block_by_index(level, self.item_target_index)
            if not block or block.get("state") != "closed" or not block.get("contents"):
                self.item_target_index = None
            else:
                dx = block["rect"].centerx - self.x
                if dx < -self.item_seek_drop:
                    self.item_target_index = None

        if self.item_target_index is None and self.item_seek_timer >= self.item_seek_interval:
            self.item_seek_timer = 0.0
            if self.rng.random() <= self.item_seek_chance:
                target_index = self._find_item_target(level)
                if target_index is not None:
                    self.item_target_index = target_index

    def _update_powerup_target(self, dt: float, powerups) -> None:
        self.powerup_seek_timer += dt

        if self.powerup_target is not None:
            if self.powerup_target not in powerups:
                self.powerup_target = None

        if self.powerup_target is None and self.powerup_seek_timer >= self.powerup_seek_interval:
            self.powerup_seek_timer = 0.0
            if self.rng.random() <= self.powerup_seek_chance:
                target = self._find_powerup_target(powerups)
                if target is not None:
                    self.powerup_target = target

    def _find_powerup_target(self, powerups):
        if not powerups:
            return None
        best = None
        best_score = None
        for powerup in powerups:
            if getattr(powerup, "state", "") == "reveal":
                continue
            dx = powerup.x - self.x
            if dx < -self.powerup_seek_backtrack or dx > self.powerup_seek_range:
                continue
            dy = abs(powerup.y - self.y)
            score = abs(dx) + dy * 0.35
            if best_score is None or score < best_score:
                best_score = score
                best = powerup
        return best

    def _find_item_target(self, level):
        blocks = getattr(level, "blocks", None)
        if not blocks:
            return None
        head_y = self.y - self.radius
        max_reach = self.max_jump_height * 1.1 if self.max_jump_height > 0 else 0.0
        best_index = None
        best_score = None

        for block in blocks:
            contents = block.get("contents")
            if contents is None:
                continue
            if block.get("state") != "closed":
                continue
            cooldown_until = block.get("cooldown_until")
            if cooldown_until is not None:
                continue
            rect = block.get("rect")
            if rect is None:
                continue
            dx = rect.centerx - self.x
            if dx < -self.item_seek_backtrack or dx > self.item_seek_range:
                continue
            vertical_gap = head_y - rect.bottom
            if vertical_gap < -self.radius:
                continue
            if max_reach and vertical_gap > max_reach:
                continue

            score = abs(dx) + max(0.0, vertical_gap) * 0.25
            if best_score is None or score < best_score:
                best_score = score
                best_index = block.get("index")

        return best_index

    def update(self, dt: float, level, camera_x: float, powerups=None, enemies=None):
        if not self.alive:
            self.update_fade()
            return

        if self.finished:
            return

        self.bumped_block = None
        self.jump_timer += dt
        if self.fire_timer > 0.0:
            self.fire_timer = max(0.0, self.fire_timer - dt)
        if self.x > self.best_x:
            self.best_x = self.x

        prev_x = self.x
        self._ai_move(dt, level, powerups or [], enemies or [])
        self._apply_physics(dt, level)
        self._update_stuck_state(dt, level, prev_x)

    def _ai_move(self, dt: float, level, powerups, enemies):
        if self.stuck_recovery_timer > 0.0 or self._should_keep_stuck_recovery(level):
            self.stuck_recovery_elapsed += dt
            self.stuck_recovery_timer = max(0.0, self.stuck_recovery_timer - dt)
            self.item_target_index = None
            self.powerup_target = None
            speed = self.run_speed * self.stuck_speed_multiplier
            self.vx = speed * self.stuck_direction
            jump_cooldown = self.jump_cooldown * self.stuck_jump_cooldown_multiplier
            if self.on_ground and self.jump_timer >= jump_cooldown:
                self.vy = self.jump_velocity * self.stuck_jump_boost * self._jump_variation()
                self.on_ground = False
                self.jump_timer = 0.0
            if self._should_keep_stuck_recovery(level):
                return
            self.stuck_recovery_timer = 0.0
            self.stuck_recovery_elapsed = 0.0
            self.stuck_recovery_target_distance = 0.0
            return

        self._update_powerup_target(dt, powerups)
        self._update_item_target(dt, level)

        self.vx = self.run_speed
        target_powerup = self.powerup_target if self.powerup_target in powerups else None
        target_block = self._get_block_by_index(level, self.item_target_index)
        if target_powerup is not None:
            target_x = target_powerup.x
            dx = target_x - self.x
            max_adjust = self.run_speed * self.powerup_seek_max_adjust
            if self.powerup_seek_range > 0:
                adjust = max_adjust * max(-1.0, min(1.0, dx / self.powerup_seek_range))
            else:
                adjust = 0.0
            self.vx = self.run_speed + adjust
        elif target_block:
            target_x = target_block["rect"].centerx
            dx = target_x - self.x
            max_adjust = self.run_speed * self.item_seek_max_adjust
            if self.item_seek_range > 0:
                adjust = max_adjust * max(-1.0, min(1.0, dx / self.item_seek_range))
            else:
                adjust = 0.0
            self.vx = self.run_speed + adjust

        enemy_threat = self._detect_enemy_jump_threat(enemies)
        jump_cooldown = self.jump_cooldown
        if enemy_threat:
            jump_cooldown *= max(
                0.2,
                float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_JUMP_COOLDOWN_MULTIPLIER", 0.7)),
            )

        if self.on_ground and self.jump_timer >= jump_cooldown:
            if target_powerup is not None:
                dx = target_powerup.x - self.x
                if abs(dx) <= self.powerup_seek_tolerance and target_powerup.y < (self.y - self.radius * 0.2):
                    self.vy = self.jump_velocity * self._jump_variation()
                    self.on_ground = False
                    self.jump_timer = 0.0
                    self.powerup_target = None
                    return

            if target_block:
                target_x = target_block["rect"].centerx
                if abs(target_x - self.x) <= self.item_seek_tolerance:
                    self.vy = self.jump_velocity * self._jump_variation()
                    self.on_ground = False
                    self.jump_timer = 0.0
                    self.item_target_index = None
                    return

            if self._should_jump(level, enemies, enemy_threat):
                self.vy = self.jump_velocity * self._jump_variation()
                self.on_ground = False
                self.jump_timer = 0.0

    def _jump_variation(self) -> float:
        variance = float(getattr(config, "SUPER_FOLLOWER_BROS_JUMP_VARIANCE", 0.08))
        return self.rng.uniform(1.0 - variance, 1.0 + variance)

    def _should_jump(self, level, enemies=None, enemy_threat: bool = False) -> bool:
        if enemy_threat or self._detect_enemy_jump_threat(enemies or []):
            return True

        lookahead = float(getattr(config, "SUPER_FOLLOWER_BROS_LOOKAHEAD", 28.0))
        foot_y = self.y + self.radius + 2
        ahead_x = self.x + self.radius + lookahead

        # Gap detection
        if not level.is_solid_at(ahead_x, foot_y + self.radius * 0.6):
            return True

        # Obstacle detection
        head_y = self.y - self.radius * 0.6
        if level.is_solid_at(ahead_x, head_y) or level.is_solid_at(ahead_x, self.y):
            return True

        # Occasional random jumps to desync
        if self.rng.random() < self.jump_chance:
            return True

        return False

    def _detect_enemy_jump_threat(self, enemies) -> bool:
        if not enemies:
            return False

        lookahead = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_JUMP_LOOKAHEAD", 92.0))
        min_ahead = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_JUMP_MIN_AHEAD", 2.0))
        vertical_tolerance = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_JUMP_VERTICAL_TOLERANCE", 46.0))
        urgent_window = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_JUMP_URGENT_WINDOW", 0.5))

        for enemy in enemies:
            state = getattr(enemy, "state", "")
            if state == "dead":
                continue
            dx = float(getattr(enemy, "x", self.x)) - self.x
            if dx < min_ahead or dx > lookahead:
                continue
            dy = abs(float(getattr(enemy, "y", self.y)) - self.y)
            if dy > vertical_tolerance:
                continue

            enemy_vx = float(getattr(enemy, "vx", 0.0))
            relative_speed = max(1.0, max(self.run_speed * 0.45, self.vx - enemy_vx))
            time_to_reach = dx / relative_speed

            # Sliding shells are immediate hazards.
            if state == "shell_slide":
                return True
            # Enemy is near and likely on collision course.
            if enemy_vx <= 0.0 or time_to_reach <= urgent_window:
                return True

        return False

    def _update_stuck_state(self, dt: float, level, prev_x: float) -> None:
        progress = self.x - prev_x
        progress_threshold = max(0.2, self.run_speed * dt * self.stuck_progress_ratio)
        forward_blocked = self._is_direction_blocked(level, 1.0)

        # Any meaningful forward movement resets stuck pressure.
        if progress > progress_threshold:
            self.stuck_timer = 0.0
            if self.stuck_direction > 0 and self.stuck_recovery_timer > 0.0:
                self.stuck_recovery_timer = 0.0
            return

        if self.stuck_recovery_timer > 0.0 or self._should_keep_stuck_recovery(level):
            return

        if not self.on_ground:
            if forward_blocked and progress <= progress_threshold * 0.25:
                self.stuck_timer += dt * 0.35
            else:
                self.stuck_timer = max(0.0, self.stuck_timer - dt * 0.8)
            return

        if progress <= progress_threshold * 0.25 or forward_blocked:
            self.stuck_timer += dt
        else:
            self.stuck_timer = max(0.0, self.stuck_timer - dt * 0.5)

        if self.stuck_timer >= self.stuck_timeout:
            self._start_stuck_recovery(level)

    def _is_direction_blocked(self, level, direction: float) -> bool:
        lookahead = max(2.0, self.stuck_wall_lookahead)
        head_y = self.y - self.radius * 0.6
        body_y = self.y
        near_probe = self.x + direction * (self.radius + 2.0)
        far_probe = self.x + direction * (self.radius + lookahead)
        for probe_x in (near_probe, far_probe):
            if level.is_solid_at(probe_x, head_y) or level.is_solid_at(probe_x, body_y):
                return True
        return False

    def _choose_stuck_direction(self, level) -> float:
        forward_blocked = self._is_direction_blocked(level, 1.0)
        backward_blocked = self._is_direction_blocked(level, -1.0)
        if forward_blocked and not backward_blocked:
            return -1.0
        if backward_blocked and not forward_blocked:
            return 1.0
        if self.rng.random() < self.stuck_reverse_bias:
            return -1.0
        return 1.0

    def _start_stuck_recovery(self, level) -> None:
        self.stuck_direction = self._choose_stuck_direction(level)
        self.stuck_recovery_timer = self.rng.uniform(
            self.stuck_backtrack_min,
            self.stuck_backtrack_max,
        )
        self.stuck_recovery_elapsed = 0.0
        self.stuck_recovery_start_x = self.x
        if self.stuck_direction < 0:
            # Ensure reverse recovery commits to enough distance to clear local traps.
            distance_from_time = self.run_speed * self.stuck_backtrack_min * self.stuck_speed_multiplier
            self.stuck_recovery_target_distance = min(
                self.stuck_backtrack_hard_max_distance,
                max(self.stuck_backtrack_min_distance, distance_from_time, self.radius * 10.0),
            )
        else:
            self.stuck_recovery_target_distance = 0.0
        self.stuck_timer = 0.0
        self.item_target_index = None
        self.powerup_target = None
        self.jump_timer = max(
            self.jump_timer,
            self.jump_cooldown * self.stuck_jump_cooldown_multiplier,
        )

    def _should_keep_stuck_recovery(self, level=None) -> bool:
        if self.stuck_recovery_timer > 0.0:
            return True
        if self.stuck_direction >= 0:
            return False
        if self.stuck_recovery_target_distance <= 0.0:
            return False
        if self.stuck_recovery_elapsed >= self.stuck_backtrack_max_time:
            return False
        required_distance = self.stuck_recovery_target_distance
        if level is not None and self._is_direction_blocked(level, 1.0):
            required_distance += self.stuck_blocked_extra_distance
        required_distance = min(required_distance, self.stuck_backtrack_hard_max_distance)
        backed_up = max(0.0, self.stuck_recovery_start_x - self.x)
        return backed_up < required_distance

    def _apply_physics(self, dt: float, level):
        # Horizontal movement
        self.x += self.vx * dt
        self._resolve_horizontal(level)

        # Vertical movement
        prev_bottom = self.y + self.radius
        self.vy += self.gravity * dt
        if self.vy > self.max_fall_speed:
            self.vy = self.max_fall_speed
        self.y += self.vy * dt
        self._resolve_vertical(level, prev_bottom=prev_bottom)
        self._resolve_penetration(level)

    def _is_moving_platform_tile(self, level, tile: pygame.Rect) -> bool:
        checker = getattr(level, "is_moving_platform_rect", None)
        if callable(checker):
            try:
                return bool(checker(tile))
            except Exception:
                return False
        return False

    def _platform_is_solid_for_player(self, level, tile: pygame.Rect, prev_bottom: float = None) -> bool:
        if not self._is_moving_platform_tile(level, tile):
            return True
        # Moving platforms are semisolid: land from above, pass through underside/sides.
        if self.vy < 0.0:
            return False
        landing_tolerance = float(
            getattr(config, "SUPER_FOLLOWER_BROS_PLATFORM_LANDING_TOLERANCE", 6.0)
        )
        if prev_bottom is None:
            prev_bottom = self.y + self.radius
        return prev_bottom <= float(tile.top) + landing_tolerance

    def _resolve_horizontal(self, level):
        rect = self._bounds()
        for tile in level.iter_solid_tiles(rect):
            if not self._platform_is_solid_for_player(level, tile):
                continue
            if rect.colliderect(tile):
                if self.vx > 0:
                    self.x = tile.left - self.radius - 0.5
                elif self.vx < 0:
                    self.x = tile.right + self.radius + 0.5
                self.vx = 0
                rect = self._bounds()

    def _resolve_vertical(self, level, prev_bottom: float = None):
        rect = self._bounds()
        self.on_ground = False
        for tile in level.iter_solid_tiles(rect):
            if not self._platform_is_solid_for_player(level, tile, prev_bottom=prev_bottom):
                continue
            if rect.colliderect(tile):
                if self.vy > 0:
                    self.y = tile.top - self.radius - 0.5
                    self.vy = 0
                    self.on_ground = True
                    rect = self._bounds()
                elif self.vy < 0:
                    self.y = tile.bottom + self.radius + 0.5
                    self.vy = 0
                    if self.bumped_block is None:
                        self.bumped_block = level.get_block_for_rect(tile)
                    rect = self._bounds()

    def _bounds(self):
        return pygame.Rect(
            int(self.x - self.radius),
            int(self.y - self.radius),
            int(self.radius * 2),
            int(self.radius * 2),
        )

    def _resolve_penetration(self, level, max_iterations: int = 4):
        for _ in range(max_iterations):
            rect = self._bounds()
            hit = None
            for tile in level.iter_solid_tiles(rect):
                if rect.colliderect(tile):
                    if not self._platform_is_solid_for_player(level, tile):
                        continue
                    hit = tile
                    break
            if hit is None:
                return

            dx_left = rect.right - hit.left
            dx_right = hit.right - rect.left
            dy_top = rect.bottom - hit.top
            dy_bottom = hit.bottom - rect.top

            move_x = -dx_left if dx_left < dx_right else dx_right
            move_y = -dy_top if dy_top < dy_bottom else dy_bottom

            if abs(move_x) < abs(move_y):
                self.x += move_x
                self.vx = 0.0
            else:
                self.y += move_y
                self.vy = 0.0
                if move_y < 0:
                    self.on_ground = True
