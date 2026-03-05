import math
import math
import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import SuperFollowerBrosArena
from .enemy import SuperFollowerBrosEnemy
from .fireball import SuperFollowerBrosFireball
from .level import SuperFollowerBrosLevel
from .level_data import ENEMY_GROUPS
from .player import SuperFollowerBrosPlayer
from .powerup import SuperFollowerBrosPowerup
from .renderer import SuperFollowerBrosRenderer


class SuperFollowerBros12Game(GameTemplate):
    GAME_TITLE = "SUPER FOLLOWER BROS."
    GAME_SUBTITLE = "World 1-2 Underground Run"
    PLAYER_LABEL = "club members"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.first_finisher = None
        self.game_history = GameHistory()

        self.level: SuperFollowerBrosLevel
        self.camera_x = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_CAMERA_START_X",
                getattr(config, "SUPER_FOLLOWER_BROS_CAMERA_START_X", 0.0),
            )
        )
        self.enemies: List[SuperFollowerBrosEnemy] = []
        self.spawned_enemy_groups = set()
        self.powerups: List[SuperFollowerBrosPowerup] = []
        self.fireballs: List[SuperFollowerBrosFireball] = []

        self.enemy_size = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_SIZE", 18.0))
        self.enemy_speed = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_SPEED", 60.0))
        self.enemy_spawn_lead = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_SPAWN_LEAD", 200.0))
        self.enemy_spawn_spacing = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_SPAWN_SPACING", 42.0))
        self.koopa_speed_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_KOOPA_SPEED_MULTIPLIER", 1.15))
        self.koopa_size_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_KOOPA_SIZE_MULTIPLIER", 1.1))
        self.enemy_sprite_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_SPRITE_SCALE", 2.5))
        self.enemy_respawn_time = float(getattr(config, "SUPER_FOLLOWER_BROS_ENEMY_RESPAWN_TIME", 10.0))
        self.shell_speed = float(getattr(config, "SUPER_FOLLOWER_BROS_SHELL_SPEED", 220.0))
        self.stomp_bounce = float(getattr(config, "SUPER_FOLLOWER_BROS_STOMP_BOUNCE", 0.6))
        self.powerup_respawn_time = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_RESPAWN_TIME", 20.0))
        self.powerup_reveal_time = float(getattr(config, "SUPER_FOLLOWER_BROS_POWERUP_REVEAL_TIME", 0.6))
        self.mushroom_alternate_fire = bool(getattr(config, "SUPER_FOLLOWER_BROS_MUSHROOM_ALTERNATE_FIRE", True))
        self.player_render_size = None
        self.checkpoints = []
        self.unlocked_checkpoint_index = -1
        self.invincible_music_path = config.project_path(
            "super_follower_bros_1_2",
            "resources_music_invincible.ogg",
        )
        self._star_music_active = False
        self._star_music_start = None
        self._star_music_intervals = []

        self.sound.background_music_path = config.project_path(
            "super_follower_bros",
            "Super Mario Bros. Underground Theme.mp3",
        )
        self.sound.preload_audio()
        self.recorder.background_music_path = self.sound.background_music_path

    def _init_game_components(self):
        self.arena = SuperFollowerBrosArena()
        self.level = SuperFollowerBrosLevel(arena_height=self.arena.height)
        self.renderer = SuperFollowerBrosRenderer(self.screen)
        self.player_render_size = self._get_player_render_size()
        self._initialize_checkpoints()

    def _ensure_checkpoints(self) -> None:
        if self.level is None:
            return
        if self.checkpoints:
            return
        self._initialize_checkpoints()

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        start_x = float(getattr(config, "SUPER_FOLLOWER_BROS_START_X", 32.0))
        start_y = float(getattr(config, "SUPER_FOLLOWER_BROS_START_Y", self.level.ground_y - 12))
        render_size = self._get_player_render_size()
        if render_size is None:
            render_size = float(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_SIZE", 16.0))

        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = SuperFollowerBrosPlayer(payload, (start_x, start_y))
            if render_size:
                player.set_base_radius(render_size / 2.0)
            player.y = self.level.ground_y - player.radius - 2.0
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        self.level.update(dt)
        self._ensure_checkpoints()

        for enemy in self.enemies:
            self._apply_platform_motion(enemy)
            enemy.update(dt, self.level)
        if self.enemies:
            margin = float(getattr(config, "SUPER_FOLLOWER_BROS_DESPAWN_MARGIN", 220.0))
            self.enemies = [
                enemy for enemy in self.enemies
                if enemy.state == "dead"
                or (-margin <= enemy.x <= self.level.pixel_width + margin
                    and enemy.y <= self.level.pixel_height + margin)
            ]

        for enemy in self.enemies:
            if enemy.state == "dead" and enemy.respawn_at is not None and self.game_time >= enemy.respawn_at:
                enemy.respawn()

        self._update_blocks_and_powerups(dt)

        for player in self.players:
            if player.finished:
                continue
            self._apply_platform_motion(player)
            player.update(dt, self.level, self.camera_x, self.powerups, self.enemies)
            self._refresh_unlocked_checkpoint(float(getattr(player, "best_x", 0.0)))

            respawn_margin = float(
                getattr(
                    config,
                    "SUPER_FOLLOWER_BROS_1_2_RESPAWN_Y_MARGIN",
                    getattr(config, "SUPER_FOLLOWER_BROS_RESPAWN_Y_MARGIN", 80.0),
                )
            )
            if (
                player.y < -respawn_margin
                or player.y > self.level.pixel_height + respawn_margin
            ):
                self._respawn(player)

            if player.bumped_block:
                self._handle_block_bump(player, player.bumped_block)

            direction = player.request_fire(self.enemies, self.game_time)
            if direction:
                self._spawn_fireball(player, direction)

            if self._has_reached_goal(player):
                player.finished = True
                player.finish_time = self.game_time
                self.first_finisher = player
                break

        if self.powerups:
            self._collect_powerups()

        self._update_fireballs(dt)

        for player in self.players:
            if player.finished:
                continue
            self._handle_player_enemy_collisions(player)

        if self.players:
            self._update_camera(dt)
            self._spawn_enemies_if_needed()

        self._update_star_music()

        if self.first_finisher:
            self._finish_game()

    def _respawn(self, player: SuperFollowerBrosPlayer):
        spawn_x, spawn_y = self._get_respawn_point_for_player(player)
        player.x = spawn_x
        player.vx = 0.0
        player.vy = 0.0
        player.on_ground = False
        player.jump_timer = 0.0
        best_x = float(getattr(player, "best_x", 0.0))
        if not math.isfinite(best_x):
            player.best_x = float(player.x)
        else:
            player.best_x = max(best_x, float(player.x))
        player.reset_powerups()
        player.y = spawn_y

    def _initialize_checkpoints(self) -> None:
        self.unlocked_checkpoint_index = -1
        if self.level is None:
            self.checkpoints = []
            return

        start_x = float(getattr(config, "SUPER_FOLLOWER_BROS_START_X", 32.0))
        configured_targets = list(
            getattr(config, "SUPER_FOLLOWER_BROS_1_2_CHECKPOINT_XS", [])
            or []
        )
        checkpoint_targets = []
        for value in configured_targets:
            try:
                x = float(value)
            except Exception:
                continue
            if math.isfinite(x):
                checkpoint_targets.append(x)

        if not checkpoint_targets:
            raw_span_end = float(getattr(self.level, "flag_x", 0.0))
            if not math.isfinite(raw_span_end) or raw_span_end <= start_x:
                raw_span_end = max(
                    start_x + 600.0,
                    float(getattr(self.level, "pixel_width", 0.0)) * 0.9,
                )
            span_end = max(start_x, raw_span_end)
            span = max(0.0, span_end - start_x)
            if span <= 0.0:
                self.checkpoints = []
                return
            checkpoint_targets = [
                start_x + span / 3.0,
                start_x + (span * 2.0) / 3.0,
            ]

        # Use actual runtime avatar radius for checkpoint spawn safety.
        base_radius = self._get_checkpoint_spawn_radius()
        self.checkpoints = []
        max_x = max(start_x + 32.0, float(getattr(self.level, "pixel_width", start_x + 32.0)) - 32.0)
        checkpoint_backtrack = float(
            getattr(config, "SUPER_FOLLOWER_BROS_CHECKPOINT_RESPAWN_BACKTRACK", 72.0)
        )
        checkpoint_min_runway = float(
            getattr(config, "SUPER_FOLLOWER_BROS_CHECKPOINT_MIN_RUNWAY", 180.0)
        )
        for target in sorted(checkpoint_targets):
            target = max(start_x + 32.0, min(max_x, float(target)))
            respawn_target = max(start_x + 32.0, min(max_x, float(target - checkpoint_backtrack)))
            spawn_x, spawn_y = self._find_respawn_location(
                respawn_target,
                base_radius,
                min_runway=checkpoint_min_runway,
            )
            self.checkpoints.append(
                {
                    "target_x": float(target),
                    "respawn_target_x": float(respawn_target),
                    "spawn_x": float(spawn_x),
                    "spawn_y": float(spawn_y),
                }
            )
        self._refresh_unlocked_checkpoint()

    def _get_respawn_point_for_player(self, player: SuperFollowerBrosPlayer):
        self._ensure_checkpoints()
        start_x = float(
            getattr(
                self.level,
                "start_x",
                getattr(config, "SUPER_FOLLOWER_BROS_START_X", 32.0),
            )
        )
        spawn_x, spawn_y = self._find_respawn_location(start_x, float(player.radius))
        player_progress = getattr(player, "best_x", player.x)
        idx = self._get_checkpoint_index_for_progress(player_progress)
        if 0 <= idx < len(self.checkpoints):
            checkpoint = self.checkpoints[idx]
            target_x = float(
                checkpoint.get(
                    "respawn_target_x",
                    checkpoint.get("target_x", checkpoint.get("spawn_x", spawn_x)),
                )
            )
            candidate_x = float(checkpoint.get("spawn_x", spawn_x))
            candidate_y = float(checkpoint.get("spawn_y", spawn_y))
            checkpoint_min_runway = float(
                getattr(config, "SUPER_FOLLOWER_BROS_CHECKPOINT_MIN_RUNWAY", 180.0)
            )
            if self._is_respawn_spot_clear(candidate_x, candidate_y, float(player.radius)):
                runway = self._measure_respawn_runway(
                    candidate_x,
                    candidate_y,
                    float(player.radius),
                    checkpoint_min_runway,
                )
                if runway < checkpoint_min_runway:
                    spawn_x, spawn_y = self._find_respawn_location(
                        target_x,
                        float(player.radius),
                        min_runway=checkpoint_min_runway,
                    )
                    checkpoint["spawn_x"] = float(spawn_x)
                    checkpoint["spawn_y"] = float(spawn_y)
                else:
                    spawn_x = candidate_x
                    spawn_y = candidate_y
            else:
                # Recompute using the actual player's radius to avoid trap spawns.
                spawn_x, spawn_y = self._find_respawn_location(
                    target_x,
                    float(player.radius),
                    min_runway=checkpoint_min_runway,
                )
                checkpoint["spawn_x"] = float(spawn_x)
                checkpoint["spawn_y"] = float(spawn_y)
        return spawn_x, spawn_y

    def _get_checkpoint_index_for_progress(self, progress_x: float) -> int:
        if not self.checkpoints:
            return -1
        try:
            progress_x = float(progress_x)
        except Exception:
            progress_x = 0.0
        if not math.isfinite(progress_x):
            progress_x = 0.0

        unlocked = -1
        for idx, checkpoint in enumerate(self.checkpoints):
            target_x = float(checkpoint.get("target_x", 0.0))
            if progress_x >= target_x:
                unlocked = idx
            else:
                break
        return unlocked

    def _get_checkpoint_spawn_radius(self) -> float:
        if self.player_render_size is not None:
            try:
                radius = float(self.player_render_size) * 0.5
                if math.isfinite(radius) and radius > 0:
                    return max(4.0, radius)
            except Exception:
                pass

        player_size = float(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_SIZE", 16.0))
        level_scale = float(getattr(self.level, "scale", 1.0)) if self.level is not None else 1.0
        if bool(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_MATCH_TILESET", True)):
            tile_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
            player_size *= tile_scale
        return max(4.0, player_size * 0.5 * level_scale)

    def _refresh_unlocked_checkpoint(self, progress_x: float = None) -> None:
        if not self.checkpoints:
            self.unlocked_checkpoint_index = -1
            return

        if progress_x is None:
            progress_x = self._get_furthest_progress_x()
        unlocked = self._get_checkpoint_index_for_progress(progress_x)
        self.unlocked_checkpoint_index = max(int(getattr(self, "unlocked_checkpoint_index", -1)), unlocked)

    def _find_respawn_location(self, target_x: float, radius: float, min_runway: float = 0.0):
        radius = max(2.0, float(radius))
        max_x = max(radius + 2.0, float(self.level.pixel_width) - radius - 2.0)
        target_x = max(radius + 2.0, min(max_x, float(target_x)))
        base_y = float(self.level.ground_y) - radius - 2.0
        search_step = max(4.0, float(getattr(config, "SUPER_FOLLOWER_BROS_CHECKPOINT_SEARCH_STEP", 8.0)))
        search_range = max(
            search_step,
            float(getattr(config, "SUPER_FOLLOWER_BROS_CHECKPOINT_SEARCH_RANGE", 360.0)),
        )

        attempts = [0.0]
        offset = search_step
        while offset <= search_range:
            attempts.append(offset)
            attempts.append(-offset)
            offset += search_step

        min_runway = max(0.0, float(min_runway))
        runway_scan = max(
            min_runway,
            float(getattr(config, "SUPER_FOLLOWER_BROS_CHECKPOINT_RUNWAY_SCAN", 320.0)),
        )
        fallback = None

        for delta in attempts:
            x = max(radius + 2.0, min(max_x, target_x + delta))
            if not self._is_respawn_spot_clear(x, base_y, radius):
                continue

            if min_runway <= 0.0:
                return x, base_y

            runway = self._measure_respawn_runway(x, base_y, radius, runway_scan)
            if runway >= min_runway:
                return x, base_y

            deficit = max(0.0, min_runway - runway)
            score = (deficit, abs(float(delta)))
            if fallback is None or score < fallback[0]:
                fallback = (score, x)

        if fallback is not None:
            return float(fallback[1]), base_y

        return target_x, base_y

    def _has_respawn_support_at(self, x: float, y: float, radius: float) -> bool:
        left = int(round(x - radius * 0.7))
        center = int(round(x))
        right = int(round(x + radius * 0.7))
        support_probe_offsets = (1.0, 3.0, 5.0)
        for offset in support_probe_offsets:
            foot = int(round(y + radius + offset))
            if (
                self._is_static_solid_at(left, foot)
                or self._is_static_solid_at(center, foot)
                or self._is_static_solid_at(right, foot)
            ):
                return True
        return False

    def _measure_respawn_runway(self, x: float, y: float, radius: float, max_distance: float) -> float:
        max_distance = max(0.0, float(max_distance))
        step = max(4.0, min(10.0, radius * 0.35))
        distance = 0.0
        while distance <= max_distance:
            if not self._has_respawn_support_at(x + distance, y, radius):
                return distance
            distance += step
        return max_distance

    def _is_respawn_spot_clear(self, x: float, y: float, radius: float) -> bool:
        left = int(round(x - radius * 0.7))
        center = int(round(x))
        right = int(round(x + radius * 0.7))
        if not self._has_respawn_support_at(x, y, radius):
            return False

        top = int(round(y - radius + 1.0))
        mid = int(round(y))
        bottom = int(round(y + radius - 1.0))
        for py in (top, mid, bottom):
            if (
                self._is_static_solid_at(left, py)
                or self._is_static_solid_at(center, py)
                or self._is_static_solid_at(right, py)
            ):
                return False

        # Full body overlap check with real-sized bbox to avoid narrow trap spawns.
        body_rect = pygame.Rect(
            int(round(x - radius + 1.0)),
            int(round(y - radius + 1.0)),
            max(1, int(round(radius * 2.0 - 2.0))),
            max(1, int(round(radius * 2.0 - 2.0))),
        )
        for rect in self.level.static_solid_rects:
            if rect.colliderect(body_rect):
                return False

        # Ensure there is enough room to start moving right.
        run_probe = max(10.0, radius * 1.4)
        probe_x = int(round(x + run_probe))
        if (
            self._is_static_solid_at(probe_x, int(round(y)))
            or self._is_static_solid_at(probe_x, int(round(y - radius * 0.35)))
            or self._is_static_solid_at(probe_x, int(round(y + radius * 0.35)))
        ):
            return False
        return True

    def _is_static_solid_at(self, x: int, y: int) -> bool:
        if x < 0 or y < 0:
            return False
        point = pygame.Rect(int(x), int(y), 1, 1)
        for rect in self.level.static_solid_rects:
            if rect.colliderect(point):
                return True
        return False

    def _handle_player_enemy_collisions(self, player: SuperFollowerBrosPlayer) -> None:
        if not self.enemies:
            return
        for enemy in self.enemies:
            if enemy.state == "dead":
                continue
            rect = enemy.rect()
            closest_x = max(rect.left, min(player.x, rect.right))
            closest_y = max(rect.top, min(player.y, rect.bottom))
            dx = player.x - closest_x
            dy = player.y - closest_y
            if dx * dx + dy * dy > player.radius * player.radius:
                continue

            stomp_zone = float(getattr(config, "SUPER_FOLLOWER_BROS_STOMP_ZONE", 0.7))
            stomp_limit = rect.top + rect.height * stomp_zone
            is_stomp = player.vy > 0 and (player.y + player.radius) <= stomp_limit
            if is_stomp:
                self._stomp_enemy(player, enemy)
                return

            if player.is_star_active(self.game_time):
                self._kill_enemy(enemy)
                return

            if player.is_hurt_invincible(self.game_time):
                return

            if enemy.kind == "koopa" and enemy.state == "shell":
                self._kick_shell(player, enemy)
                return

            if player.take_hit(self.game_time):
                return

            self._respawn(player)
            return

    def _handle_block_bump(self, player: SuperFollowerBrosPlayer, block: dict) -> None:
        if not block:
            return
        if block.get("kind") not in ("brick", "coin_box"):
            return

        bump_time = float(getattr(config, "SUPER_FOLLOWER_BROS_BLOCK_BUMP_TIME", 0.16))
        if bump_time > 0:
            block["bump_start"] = self.game_time
            block["bump_until"] = self.game_time + bump_time

        contents = block.get("contents")
        if not contents:
            return
        if block.get("state") == "opened":
            return

        block["state"] = "opened"
        block["cooldown_until"] = self.game_time + self.powerup_respawn_time
        block["last_bump_time"] = self.game_time

        spawn_kind = None
        if contents in ("mushroom", "fireflower"):
            if player.power_level >= 1:
                spawn_kind = "fireflower"
            else:
                spawn_kind = "mushroom"
        elif contents == "star":
            spawn_kind = "star"

        if spawn_kind:
            rect = block.get("rect")
            if rect:
                powerup = SuperFollowerBrosPowerup(
                    kind=spawn_kind,
                    x=float(rect.centerx),
                    y=float(rect.top),
                    spawn_time=self.game_time,
                    block_index=block.get("index", -1),
                    state="reveal",
                    block_top=float(rect.top),
                    block_height=float(rect.height),
                    expires_at=block.get("cooldown_until"),
                )
                self.powerups.append(powerup)

    def _update_blocks_and_powerups(self, dt: float) -> None:
        # Clear expired powerups and reset blocks
        if self.level and getattr(self.level, "blocks", None):
            for block in self.level.blocks:
                cooldown = block.get("cooldown_until")
                if block.get("state") == "opened" and cooldown is not None and self.game_time >= cooldown:
                    block["state"] = "closed"
                    block["cooldown_until"] = None
                    block["last_bump_time"] = None
                bump_until = block.get("bump_until")
                if bump_until is not None and self.game_time >= bump_until:
                    block["bump_until"] = None
                    block["bump_start"] = None

        if self.powerups:
            self.powerups = [
                powerup for powerup in self.powerups
                if powerup.expires_at is None or self.game_time < powerup.expires_at
            ]
            for powerup in self.powerups:
                self._apply_platform_motion(powerup)
                if powerup.state == "reveal" and self.game_time - powerup.spawn_time >= self.powerup_reveal_time:
                    if powerup.kind == "star":
                        self._start_star_bounce(powerup)
                    elif powerup.kind == "mushroom":
                        self._start_mushroom_move(powerup)
                    else:
                        powerup.state = "rest"

            # Update active powerups
            for powerup in self.powerups:
                if powerup.kind == "star" and powerup.state == "bounce":
                    self._update_star_powerup(powerup, dt)
                elif powerup.kind == "mushroom" and powerup.state == "move":
                    self._update_mushroom_powerup(powerup, dt)

    def _collect_powerups(self) -> None:
        remaining = []
        for powerup in self.powerups:
            collected = False
            collector = None
            rect = self._powerup_rect(powerup)
            for player in self.players:
                if player.finished:
                    continue
                closest_x = max(rect.left, min(player.x, rect.right))
                closest_y = max(rect.top, min(player.y, rect.bottom))
                dx = player.x - closest_x
                dy = player.y - closest_y
                if dx * dx + dy * dy <= player.radius * player.radius:
                    collected = True
                    collector = player
                    break
            if not collected:
                remaining.append(powerup)
            elif collector:
                self._apply_powerup(collector, powerup)
        self.powerups = remaining

    def _powerup_size(self, kind: str) -> tuple[float, float]:
        scale = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SCALE", 2.5)) * self.level.scale
        if kind == "star":
            width = 15.0 * scale
            height = 16.0 * scale
        else:
            width = 16.0 * scale
            height = 16.0 * scale
        return width, height

    def _powerup_rect_at(self, kind: str, x: float, y: float) -> pygame.Rect:
        width, height = self._powerup_size(kind)
        return pygame.Rect(
            int(x - width / 2),
            int(y - height / 2),
            max(1, int(width)),
            max(1, int(height)),
        )

    def _powerup_rect(self, powerup: SuperFollowerBrosPowerup) -> pygame.Rect:
        return self._powerup_rect_at(powerup.kind, powerup.x, powerup.y)

    def _start_star_bounce(self, powerup: SuperFollowerBrosPowerup) -> None:
        star_speed = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_SPEED", 120.0))
        bounce = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_BOUNCE", 360.0))

        powerup.state = "bounce"
        powerup.vx = star_speed if random.random() < 0.5 else -star_speed
        powerup.vy = -abs(bounce)

        _, height = self._powerup_size(powerup.kind)
        if powerup.block_top:
            powerup.y = powerup.block_top - height / 2

    def _update_star_powerup(self, powerup: SuperFollowerBrosPowerup, dt: float) -> None:
        gravity = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_GRAVITY", 900.0))
        jump_velocity = self._star_jump_velocity(gravity)

        powerup.vy += gravity * dt

        # Horizontal move + wall bounce
        next_x = powerup.x + powerup.vx * dt
        rect_x = self._powerup_rect_at(powerup.kind, next_x, powerup.y)
        hit_x = False
        for solid in self.level.iter_solid_tiles(rect_x):
            hit_x = True
            if powerup.vx > 0:
                next_x = solid.left - rect_x.width / 2
            else:
                next_x = solid.right + rect_x.width / 2
            powerup.vx = -powerup.vx
            break
        powerup.x = next_x

        # Vertical move + bounce
        next_y = powerup.y + powerup.vy * dt
        rect_y = self._powerup_rect_at(powerup.kind, powerup.x, next_y)
        hit_y = False
        for solid in self.level.iter_solid_tiles(rect_y):
            hit_y = True
            if powerup.vy > 0:
                next_y = solid.top - rect_y.height / 2
                # Always jump immediately on ground contact
                powerup.vy = -abs(jump_velocity)
            else:
                next_y = solid.bottom + rect_y.height / 2
                powerup.vy = abs(jump_velocity) * 0.4
            break
        powerup.y = next_y

    def _star_jump_velocity(self, gravity: float) -> float:
        height_factor = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_JUMP_HEIGHT_FACTOR", 0.85))
        target_height = getattr(config, "SUPER_FOLLOWER_BROS_JUMP_HEIGHT", None)
        if target_height is not None:
            try:
                star_height = float(target_height) * height_factor
                if star_height > 0 and gravity > 0:
                    return math.sqrt(2.0 * gravity * star_height)
            except (TypeError, ValueError):
                pass

        base_velocity = float(getattr(config, "SUPER_FOLLOWER_BROS_JUMP_VELOCITY", -460.0))
        return abs(base_velocity) * height_factor

    def _start_mushroom_move(self, powerup: SuperFollowerBrosPowerup) -> None:
        speed = float(getattr(config, "SUPER_FOLLOWER_BROS_MUSHROOM_SPEED", 110.0))
        powerup.state = "move"
        powerup.vx = abs(speed)
        powerup.vy = 0.0

        if powerup.block_top and powerup.block_height:
            # Start just below the block so gravity will drop it naturally
            powerup.y = powerup.block_top + powerup.block_height * 0.5
            if powerup.vy <= 0:
                powerup.vy = 1.0

    def _update_mushroom_powerup(self, powerup: SuperFollowerBrosPowerup, dt: float) -> None:
        gravity = float(getattr(config, "SUPER_FOLLOWER_BROS_MUSHROOM_GRAVITY", 900.0))
        powerup.vy += gravity * dt

        # Horizontal move + wall bounce
        next_x = powerup.x + powerup.vx * dt
        rect_x = self._powerup_rect_at(powerup.kind, next_x, powerup.y)
        for solid in self.level.iter_solid_tiles(rect_x):
            if powerup.vx > 0:
                next_x = solid.left - rect_x.width / 2
            else:
                next_x = solid.right + rect_x.width / 2
            powerup.vx = -powerup.vx
            break
        powerup.x = next_x

        # Vertical move (falling/landing)
        next_y = powerup.y + powerup.vy * dt
        rect_y = self._powerup_rect_at(powerup.kind, powerup.x, next_y)
        for solid in self.level.iter_solid_tiles(rect_y):
            if powerup.vy > 0:
                next_y = solid.top - rect_y.height / 2
                powerup.vy = 0.0
            else:
                next_y = solid.bottom + rect_y.height / 2
                powerup.vy = 0.0
            break
        powerup.y = next_y

    def _apply_powerup(self, player: SuperFollowerBrosPlayer, powerup: SuperFollowerBrosPowerup) -> None:
        if powerup.kind == "mushroom":
            player.apply_mushroom()
        elif powerup.kind == "fireflower":
            player.apply_fireflower()
        elif powerup.kind == "star":
            player.apply_star(self.game_time)

    def _stomp_enemy(self, player: SuperFollowerBrosPlayer, enemy: SuperFollowerBrosEnemy) -> None:
        player.y = enemy.rect().top - player.radius - 0.5
        player.vy = -abs(player.jump_velocity) * self.stomp_bounce
        player.on_ground = False

        if enemy.kind == "goomba":
            self._kill_enemy(enemy)
            return

        if enemy.kind == "koopa":
            enemy.set_state("shell")
            enemy.vx = 0.0

    def _kick_shell(self, player: SuperFollowerBrosPlayer, enemy: SuperFollowerBrosEnemy) -> None:
        direction = 1.0 if player.x < enemy.x else -1.0
        enemy.set_state("shell_slide")
        enemy.vx = self.shell_speed * direction

    def _kill_enemy(self, enemy: SuperFollowerBrosEnemy) -> None:
        enemy.state = "dead"
        enemy.vx = 0.0
        enemy.vy = 0.0
        enemy.respawn_at = self.game_time + self.enemy_respawn_time

    def _spawn_fireball(self, player: SuperFollowerBrosPlayer, direction: float) -> None:
        speed = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREBALL_SPEED", 240.0))
        bounce = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREBALL_BOUNCE", 320.0))
        offset = player.radius + max(4.0, player.radius * 0.3)
        x = player.x + offset * direction
        y = player.y
        fireball = SuperFollowerBrosFireball(
            x=x,
            y=y,
            vx=speed * direction,
            vy=-abs(bounce) * 0.4,
            spawn_time=self.game_time,
        )
        self.fireballs.append(fireball)

    def _update_fireballs(self, dt: float) -> None:
        if not self.fireballs:
            return
        gravity = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREBALL_GRAVITY", 1200.0))
        bounce = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREBALL_BOUNCE", 320.0))
        lifetime = float(getattr(config, "SUPER_FOLLOWER_BROS_FIREBALL_LIFETIME", 6.0))
        remaining = []

        for fireball in self.fireballs:
            self._apply_platform_motion(fireball)
            if lifetime > 0 and (self.game_time - fireball.spawn_time) > lifetime:
                continue

            fireball.vy += gravity * dt

            fireball.x += fireball.vx * dt
            rect = self._fireball_rect(fireball)
            if self._rect_hits_solid(rect):
                continue

            fireball.y += fireball.vy * dt
            rect = self._fireball_rect(fireball)
            hit_tile = self._first_solid_hit(rect)
            if hit_tile is not None:
                if fireball.vy > 0:
                    fireball.y = hit_tile.top - rect.height / 2 - 0.5
                    fireball.vy = -abs(bounce)
                else:
                    continue

            if self._fireball_hits_enemy(fireball):
                continue

            if fireball.x < -120 or fireball.x > self.level.pixel_width + 120:
                continue
            if fireball.y > self.level.pixel_height + 120:
                continue

            remaining.append(fireball)

        self.fireballs = remaining

    def _fireball_rect(self, fireball: SuperFollowerBrosFireball) -> pygame.Rect:
        scale = float(getattr(config, "SUPER_FOLLOWER_BROS_ITEM_SCALE", 2.5)) * self.level.scale
        width = max(1, int(round(8.0 * scale)))
        height = max(1, int(round(8.0 * scale)))
        return pygame.Rect(
            int(fireball.x - width / 2),
            int(fireball.y - height / 2),
            width,
            height,
        )

    def _rect_hits_solid(self, rect: pygame.Rect) -> bool:
        for tile in self.level.iter_solid_tiles(rect):
            if rect.colliderect(tile):
                return True
        return False

    def _first_solid_hit(self, rect: pygame.Rect):
        for tile in self.level.iter_solid_tiles(rect):
            if rect.colliderect(tile):
                return tile
        return None

    def _fireball_hits_enemy(self, fireball: SuperFollowerBrosFireball) -> bool:
        rect = self._fireball_rect(fireball)
        for enemy in self.enemies:
            if enemy.state == "dead":
                continue
            if rect.colliderect(enemy.rect()):
                self._kill_enemy(enemy)
                return True
        return False

    def _apply_platform_motion(self, entity) -> None:
        if entity is None:
            return
        if not hasattr(self.level, "get_platform_motion_for_entity"):
            return
        if hasattr(entity, "radius"):
            rect = pygame.Rect(
                int(entity.x - entity.radius),
                int(entity.y - entity.radius),
                max(1, int(entity.radius * 2)),
                max(1, int(entity.radius * 2)),
            )
        elif hasattr(entity, "rect"):
            try:
                rect = entity.rect()
            except Exception:
                return
        else:
            return

        dx, dy = self.level.get_platform_motion_for_entity(rect)
        if dx == 0.0 and dy == 0.0:
            return
        entity.x += dx
        entity.y += dy

    def _spawn_enemies_if_needed(self):
        if not ENEMY_GROUPS:
            return
        camera_right = self.camera_x + self.arena.width
        for idx, group in enumerate(ENEMY_GROUPS):
            if idx in self.spawned_enemy_groups:
                continue
            spawn_x = float(group.get("checkpoint", 0.0)) * self.level.scale
            if spawn_x < self.camera_x - self.arena.width:
                self.spawned_enemy_groups.add(idx)
                continue
            if camera_right + self.enemy_spawn_lead < spawn_x:
                continue
            self._spawn_enemy_group(group, spawn_x)
            self.spawned_enemy_groups.add(idx)

    def _spawn_enemy_group(self, group: dict, spawn_x: float):
        count = int(group.get("count", 1))
        y_hint = group.get("y")
        kind = group.get("kind", "goomba")
        size_w, size_h, shell_w, shell_h = self._enemy_dimensions(kind)
        if size_w <= 0 or size_h <= 0:
            size_w = self.enemy_size
            size_h = self.enemy_size * (self.koopa_size_multiplier if kind == "koopa" else 0.85)
            shell_w = size_w
            shell_h = size_h
        if y_hint is None:
            base_y = self.level.ground_y - size_h / 2 - 1.0
        else:
            base_y = float(y_hint) * self.level.scale - size_h / 2 - 1.0

        base_x = max(spawn_x, self.camera_x + self.arena.width + 40.0)
        speed = self.enemy_speed * (self.koopa_speed_multiplier if kind == "koopa" else 1.0)
        for i in range(max(1, count)):
            enemy_x = base_x + i * self.enemy_spawn_spacing
            self.enemies.append(
                SuperFollowerBrosEnemy(
                    x=enemy_x,
                    y=base_y,
                    vx=-abs(speed),
                    vy=0.0,
                    width=size_w,
                    height=size_h,
                    kind=kind,
                    state="walk",
                    spawn_x=enemy_x,
                    spawn_y=base_y,
                    base_speed=abs(speed),
                    walk_width=size_w,
                    walk_height=size_h,
                    shell_width=shell_w,
                    shell_height=shell_h,
                )
            )

    def _enemy_dimensions(self, kind: str):
        scale = self.enemy_sprite_scale * self.level.scale
        if scale <= 0:
            return 0.0, 0.0, 0.0, 0.0
        if kind == "koopa":
            base_w, base_h = 16.0, 24.0
        else:
            base_w, base_h = 16.0, 16.0
        shell_w, shell_h = 16.0 * scale, 15.0 * scale
        return base_w * scale, base_h * scale, shell_w, shell_h

    def _update_camera(self, dt: float):
        leader = self._get_leader()
        if leader is None:
            return
        follow_ratio = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_CAMERA_RATIO",
                getattr(config, "SUPER_FOLLOWER_BROS_CAMERA_RATIO", 0.35),
            )
        )
        target_x = float(leader.x) - self.arena.width * follow_ratio
        allow_backtrack = bool(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_CAMERA_ALLOW_BACKTRACK",
                getattr(config, "SUPER_FOLLOWER_BROS_CAMERA_ALLOW_BACKTRACK", False),
            )
        )
        if not allow_backtrack:
            target_x = max(self.camera_x, target_x)
        max_x = max(0.0, self.level.pixel_width - self.arena.width)
        target_x = max(0.0, min(max_x, target_x))

        smooth = float(getattr(config, "SUPER_FOLLOWER_BROS_CAMERA_SMOOTH", 8.0))
        if smooth <= 0:
            self.camera_x = target_x
            return
        step = 1.0 - math.exp(-smooth * max(0.001, dt))
        self.camera_x += (target_x - self.camera_x) * step

    def _is_camera_trackable(self, player: SuperFollowerBrosPlayer) -> bool:
        leader_max_y = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_CAMERA_LEADER_MAX_Y",
                getattr(config, "SUPER_FOLLOWER_BROS_CAMERA_LEADER_MAX_Y", 24.0),
            )
        )
        leader_min_y = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_CAMERA_LEADER_MIN_Y",
                -96.0,
            )
        )

        y = float(getattr(player, "y", 0.0))
        if y < leader_min_y or y > float(self.level.pixel_height) + leader_max_y:
            return False

        # Ignore candidates that are embedded in solid geometry.
        if self.level.is_solid_at(float(getattr(player, "x", 0.0)), y):
            return False
        return True

    @staticmethod
    def _camera_leader_sort_key(player: SuperFollowerBrosPlayer):
        return (float(player.x), float(player.best_x))

    def _get_leader(self):
        active = [player for player in self.players if player.alive and not player.finished]
        trackable = [player for player in active if self._is_camera_trackable(player)]
        if trackable:
            return max(trackable, key=self._camera_leader_sort_key)
        unfinished_trackable = [
            player for player in self.players
            if not player.finished and self._is_camera_trackable(player)
        ]
        if unfinished_trackable:
            return max(unfinished_trackable, key=self._camera_leader_sort_key)
        if active:
            return max(active, key=self._camera_leader_sort_key)

        unfinished = [player for player in self.players if not player.finished]
        if unfinished:
            return max(unfinished, key=lambda p: float(p.best_x))

        if self.players:
            return max(self.players, key=lambda p: float(p.best_x))
        return None

    def _get_furthest_progress_x(self) -> float:
        active = [player for player in self.players if player.alive and not player.finished]
        source = active if active else self.players
        if not source:
            return 0.0
        finite_progress = []
        for player in source:
            try:
                value = float(getattr(player, "best_x", 0.0))
            except Exception:
                continue
            if math.isfinite(value):
                finite_progress.append(value)
        if not finite_progress:
            return 0.0
        return max(finite_progress)

    def _has_reached_goal(self, player: SuperFollowerBrosPlayer) -> bool:
        x = float(getattr(player, "x", 0.0))
        y = float(getattr(player, "y", 0.0))
        r = float(getattr(player, "radius", 0.0))

        # Primary: enter the horizontal goal-pipe area at the end of 1-2.
        goal_x = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_GOAL_PIPE_X",
                float(getattr(self.level, "flag_x", 0.0)),
            )
        )
        goal_width = float(getattr(config, "SUPER_FOLLOWER_BROS_1_2_GOAL_PIPE_WIDTH", 150.0))
        goal_pre_entry = float(getattr(config, "SUPER_FOLLOWER_BROS_1_2_GOAL_PIPE_PRE_ENTRY", 56.0))
        goal_x -= goal_pre_entry
        goal_top = float(getattr(config, "SUPER_FOLLOWER_BROS_1_2_GOAL_PIPE_TOP_Y", 120.0)) * float(
            getattr(self.level, "scale", 1.0)
        )
        goal_bottom = float(getattr(config, "SUPER_FOLLOWER_BROS_1_2_GOAL_PIPE_BOTTOM_Y", 460.0)) * float(
            getattr(self.level, "scale", 1.0)
        )

        inside_goal_x = (x + r) >= goal_x and (x - r) <= (goal_x + goal_width)
        inside_goal_y = (y + r) >= goal_top and (y - r) <= goal_bottom
        if inside_goal_x and inside_goal_y:
            return True

        # Fallback: hard x crossing so races cannot stall forever near the end.
        fallback_x = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_FINISH_FALLBACK_X",
                goal_x + max(18.0, goal_width * 0.15),
            )
        )
        return x >= fallback_x

    def _finish_game(self):
        if self.game_over:
            return
        self._finalize_star_music()

        finish_time = self.game_time
        if self.first_finisher and self.first_finisher.finish_time is not None:
            finish_time = self.first_finisher.finish_time

        distances = []
        for player in self.players:
            dist = max(0.0, self.level.flag_x - player.best_x)
            distances.append((player, dist))
            player.survival_time = finish_time

        def sort_key(item):
            player, dist = item
            is_winner = 0 if player is self.first_finisher else 1
            return (is_winner, dist, player.username)

        sorted_players = [player for player, _ in sorted(distances, key=sort_key)]
        self.finish_game(sorted_players)

    def _finalize_star_music(self) -> None:
        if not getattr(config, "EXPORT_VIDEO", False):
            return
        if self._star_music_active and self._star_music_start is not None:
            self._star_music_intervals.append((float(self._star_music_start), float(self.game_time)))
        self._star_music_active = False
        self._star_music_start = None

        if not self._star_music_intervals:
            return

        total_end = float(self.game_time)
        background_path = self.sound.background_music_path
        invincible_path = self.invincible_music_path
        invincible_volume = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_MUSIC_VOLUME", 1.0))

        segments = []
        cursor = 0.0
        for start, end in sorted(self._star_music_intervals):
            start = max(0.0, start)
            end = max(start, end)
            if start > cursor and background_path:
                segments.append({
                    "path": background_path,
                    "start": cursor,
                    "end": start,
                    "volume": 1.0,
                })
            if invincible_path and end > start:
                segments.append({
                    "path": invincible_path,
                    "start": start,
                    "end": end,
                    "volume": invincible_volume,
                })
            cursor = max(cursor, end)

        if cursor < total_end and background_path:
            segments.append({
                "path": background_path,
                "start": cursor,
                "end": total_end,
                "volume": 1.0,
            })

        if segments:
            self.recorder.include_background_music = False
            self.recorder.music_segments = segments

    def _update_star_music(self) -> None:
        if not self.players:
            return

        margin = float(getattr(config, "SUPER_FOLLOWER_BROS_STAR_MUSIC_MARGIN", 40.0))
        left = self.camera_x - margin
        right = self.camera_x + self.arena.width + margin
        top = -margin
        bottom = self.arena.height + margin

        star_visible = False
        for player in self.players:
            if not player.alive or player.finished:
                continue
            if not player.is_star_active(self.game_time):
                continue
            if player.x < left or player.x > right:
                continue
            if player.y < top or player.y > bottom:
                continue
            star_visible = True
            break

        if getattr(config, "EXPORT_VIDEO", False):
            if star_visible and not self._star_music_active:
                self._star_music_active = True
                self._star_music_start = self.game_time
            elif not star_visible and self._star_music_active:
                self._star_music_intervals.append((float(self._star_music_start or self.game_time), float(self.game_time)))
                self._star_music_active = False
                self._star_music_start = None
            return

        if star_visible and not self._star_music_active:
            try:
                if self.invincible_music_path:
                    pygame.mixer.music.load(self.invincible_music_path)
                    pygame.mixer.music.set_volume(self.sound.current_music_volume * self.sound.master_volume)
                    pygame.mixer.music.play(-1)
                    self._star_music_active = True
            except Exception:
                self._star_music_active = False
        elif not star_visible and self._star_music_active:
            try:
                if self.sound.background_music_path:
                    pygame.mixer.music.load(self.sound.background_music_path)
                    pygame.mixer.music.set_volume(self.sound.current_music_volume * self.sound.master_volume)
                    pygame.mixer.music.play(-1)
            except Exception:
                pass
            self._star_music_active = False

    def render(self):
        self._ensure_checkpoints()
        leader = self._get_leader() if self.players else None
        leader_name = leader.username if leader else None
        furthest_progress = self._get_furthest_progress_x() if self.players else 0.0
        self._refresh_unlocked_checkpoint(furthest_progress)
        global_day = int(getattr(config, "DAY_NUMBER", 1))
        club_day = max(1, global_day - 71)

        game_state = {
            "phase": self.phase,
            "level": self.level,
            "camera_x": self.camera_x,
            "enemies": self.enemies,
            "powerups": self.powerups,
            "fireballs": self.fireballs,
            "elapsed_time": self.game_time,
            "leader_name": leader_name,
            "player_size": self.player_render_size,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_day_number": club_day,
            "global_day_number": global_day,
            "checkpoint_progress_x": float(furthest_progress),
            "checkpoint_unlocked_index": int(self.unlocked_checkpoint_index),
            "checkpoints": [
                {
                    "x": float(cp.get("target_x", 0.0)),
                    "spawn_x": float(cp.get("spawn_x", cp.get("target_x", 0.0))),
                    "active": bool(idx <= self.unlocked_checkpoint_index),
                }
                for idx, cp in enumerate(self.checkpoints)
            ],
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[SuperFollowerBrosPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "super_follower_bros_1_2"
        game_display_name = "Super Follower Bros. 1-2"
        day_number = int(getattr(config, "DAY_NUMBER", 1))
        club_day = max(1, day_number - 71)

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=player.survival_time or 0,
                games_played=games_played,
            )

            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=points,
                survival_time=player.survival_time or 0,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((player.username, placement, points, player.survival_time or 0))
            game_history_results.append({
                "username": player.username,
                "placement": placement,
                "points": points,
                "survival_time": player.survival_time or 0,
                "kills": 0,
                "damage": 0.0,
            })

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
            extra_data={
                "club_day": club_day,
                "global_day": day_number,
            },
        )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()

    def _get_player_render_size(self):
        if self.level is None:
            return None
        if not bool(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_MATCH_TILESET", True)):
            return None
        base = float(getattr(config, "SUPER_FOLLOWER_BROS_PLAYER_SIZE", 16.0))
        tile_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
        size = base * tile_scale * self.level.scale
        return max(1.0, size)
