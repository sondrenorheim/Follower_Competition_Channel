from __future__ import annotations

import math
import random
import time
from typing import List

import pygame

import config
from shared import auto_push
from super_follower_bros_1_2.arena import SuperFollowerBrosArena
from super_follower_bros_1_2.enemy import SuperFollowerBrosEnemy
from super_follower_bros_1_2.fireball import SuperFollowerBrosFireball
from super_follower_bros_1_2.game import SuperFollowerBros12Game
from super_follower_bros_1_2.player import SuperFollowerBrosPlayer
from super_follower_bros_1_2.powerup import SuperFollowerBrosPowerup

from .levels import display_name_for_mode, normalize_smb_mode
from .scene_level import SuperFollowerBrosSceneLevel
from .scene_parser import load_level_for_mode
from .scene_renderer import SuperFollowerBrosSceneRenderer


class SuperFollowerBrosSceneGame(SuperFollowerBros12Game):
    GAME_TITLE = "SUPER FOLLOWER BROS."
    PLAYER_LABEL = "club members"

    def __init__(self, game_mode: str):
        self.game_mode = normalize_smb_mode(game_mode) or "super_follower_bros_1_1"
        self.mode_display_name = display_name_for_mode(self.game_mode)
        self.parsed_level = load_level_for_mode(self.game_mode)
        self._pending_enemy_spawns: list[dict] = []
        super().__init__()
        self.GAME_SUBTITLE = self.parsed_level.subtitle

        # Keep existing soundtrack behavior from SFB modes.
        self.invincible_music_path = config.project_path(
            "super_follower_bros",
            "resources_music_invincible.ogg",
        )
        overworld_music_path = config.project_path(
            "Super Mario Brothers 1 Music - Main Theme & Overworld.mp3",
        )
        underground_music_path = config.project_path(
            "super_follower_bros",
            "Super Mario Bros. Underground Theme.mp3",
        )
        if self.game_mode == "super_follower_bros_1_2":
            self.sound.background_music_path = underground_music_path
        else:
            self.sound.background_music_path = overworld_music_path
        self.sound.preload_audio()
        self.recorder.background_music_path = self.sound.background_music_path

    def _init_game_components(self):
        self.arena = SuperFollowerBrosArena()
        self.level = SuperFollowerBrosSceneLevel(self.parsed_level, arena_height=self.arena.height)
        self.renderer = SuperFollowerBrosSceneRenderer(
            self.screen,
            subtitle=self.parsed_level.subtitle,
            world_label=self.parsed_level.world_label,
        )
        self.player_render_size = self._get_player_render_size()
        self._initialize_checkpoints()
        self._pending_enemy_spawns = list(self.level.enemy_spawns)

        start_camera = max(0.0, float(getattr(self.level, "start_x", 0.0)) - self.arena.width * 0.4)
        if self.level.camera_right_limit is not None:
            start_camera = min(start_camera, max(0.0, self.level.camera_right_limit - self.arena.width))
        self.camera_x = float(start_camera)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        start_x = float(getattr(self.level, "start_x", 32.0))
        start_y = float(getattr(self.level, "start_y", self.level.ground_y - 12.0))
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
            player.y = start_y - player.radius
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _initialize_checkpoints(self) -> None:
        self.unlocked_checkpoint_index = -1
        if self.level is None:
            self.checkpoints = []
            return

        start_x = float(getattr(self.level, "start_x", getattr(config, "SUPER_FOLLOWER_BROS_START_X", 32.0)))
        configured_targets = list(
            getattr(config, "SUPER_FOLLOWER_BROS_1_2_CHECKPOINT_XS", []) or []
        )
        explicit_points = list(getattr(self.level, "checkpoint_points", []))
        if not explicit_points:
            explicit_points = list(getattr(self.level, "checkpoint_flag_points", []))
        for point in explicit_points:
            configured_targets.append(point.get("x", 0.0))

        checkpoint_targets = []
        for value in configured_targets:
            try:
                x = float(value)
            except Exception:
                continue
            if math.isfinite(x):
                checkpoint_targets.append(x)

        if not checkpoint_targets:
            span_end = max(start_x, float(self.level.flag_x))
            span = max(0.0, span_end - start_x)
            if span <= 0.0:
                self.checkpoints = []
                return
            checkpoint_targets = [
                start_x + span / 3.0,
                start_x + (span * 2.0) / 3.0,
            ]

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
                enemy
                for enemy in self.enemies
                if enemy.state == "dead"
                or (
                    -margin <= enemy.x <= self.level.pixel_width + margin
                    and enemy.y <= self.level.pixel_height + margin
                )
            ]

        for enemy in self.enemies:
            if enemy.state == "dead" and enemy.respawn_at is not None and self.game_time >= enemy.respawn_at:
                enemy.respawn()

        self._update_blocks_and_powerups(dt)

        respawn_margin = float(
            getattr(
                config,
                "SUPER_FOLLOWER_BROS_1_2_RESPAWN_Y_MARGIN",
                getattr(config, "SUPER_FOLLOWER_BROS_RESPAWN_Y_MARGIN", 80.0),
            )
        )

        for player in self.players:
            if player.finished:
                continue
            self._apply_platform_motion(player)
            player.update(dt, self.level, self.camera_x, self.powerups, self.enemies)
            self._refresh_unlocked_checkpoint(float(getattr(player, "best_x", 0.0)))

            if (
                player.y < -respawn_margin
                or player.y > self.level.pixel_height + respawn_margin
            ):
                self._respawn(player)
                continue

            player_rect = pygame.Rect(
                int(player.x - player.radius),
                int(player.y - player.radius),
                max(1, int(player.radius * 2)),
                max(1, int(player.radius * 2)),
            )
            if self.level.collides_hazard(player_rect):
                self._respawn(player)
                continue

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

    def _spawn_enemies_if_needed(self):
        if not self._pending_enemy_spawns:
            return

        camera_right = self.camera_x + self.arena.width
        allowed_left = self.camera_x - self.arena.width
        remaining: list[dict] = []
        for spec in self._pending_enemy_spawns:
            spawn_x = float(spec.get("x", 0.0))
            if spawn_x < allowed_left:
                continue
            if spawn_x > camera_right + self.enemy_spawn_lead:
                remaining.append(spec)
                continue
            self._spawn_enemy_from_spec(spec)
        self._pending_enemy_spawns = remaining

    def _spawn_enemy_from_spec(self, spec: dict):
        raw_kind = str(spec.get("kind", "goomba")).lower()
        enemy_kind = "koopa" if "koopa" in raw_kind else "goomba"
        if "piranha" in raw_kind:
            enemy_kind = "goomba"

        size_w, size_h, shell_w, shell_h = self._enemy_dimensions(enemy_kind)
        if size_w <= 0 or size_h <= 0:
            size_w = self.enemy_size
            size_h = self.enemy_size * (self.koopa_size_multiplier if enemy_kind == "koopa" else 0.85)
            shell_w = size_w
            shell_h = size_h

        spawn_x = float(spec.get("x", 0.0))
        y_hint = spec.get("y")
        if y_hint is None:
            base_y = self.level.ground_y - size_h * 0.5 - 1.0
        else:
            base_y = float(y_hint) - size_h * 0.5 - 1.0

        speed = self.enemy_speed * (self.koopa_speed_multiplier if enemy_kind == "koopa" else 1.0)
        vx = 0.0 if "piranha" in raw_kind else -abs(speed)
        enemy = SuperFollowerBrosEnemy(
            x=spawn_x,
            y=base_y,
            vx=vx,
            vy=0.0,
            width=size_w,
            height=size_h,
            kind=enemy_kind,
            state="walk",
            spawn_x=spawn_x,
            spawn_y=base_y,
            base_speed=abs(speed),
            walk_width=size_w,
            walk_height=size_h,
            shell_width=shell_w,
            shell_height=shell_h,
        )
        self.enemies.append(enemy)

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

        hard_limit = self.level.camera_right_limit
        if hard_limit is not None:
            max_x = max(0.0, hard_limit - self.arena.width)
        else:
            max_x = max(0.0, self.level.pixel_width - self.arena.width)
        target_x = max(0.0, min(max_x, target_x))

        smooth = float(getattr(config, "SUPER_FOLLOWER_BROS_CAMERA_SMOOTH", 8.0))
        if smooth <= 0:
            self.camera_x = target_x
            return
        step = 1.0 - math.exp(-smooth * max(0.001, dt))
        self.camera_x += (target_x - self.camera_x) * step

    def render(self):
        leader = self._get_leader() if self.players else None
        leader_name = leader.username if leader else None
        furthest_progress = self._get_furthest_progress_x() if self.players else 0.0
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
            "world_label": self.parsed_level.world_label,
            "checkpoints": [
                {
                    "x": float(cp.get("target_x", 0.0)),
                    "spawn_x": float(cp.get("spawn_x", cp.get("target_x", 0.0))),
                    "active": bool(furthest_progress >= float(cp.get("target_x", 0.0))),
                }
                for cp in self.checkpoints
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

        game_type = self.game_mode
        game_display_name = self.mode_display_name
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
            game_history_results.append(
                {
                    "username": player.username,
                    "placement": placement,
                    "points": points,
                    "survival_time": player.survival_time or 0,
                    "kills": 0,
                    "damage": 0.0,
                }
            )

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
            extra_data={
                "club_day": club_day,
                "global_day": day_number,
                "world": self.parsed_level.world_label,
            },
        )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
