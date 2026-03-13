import random
import time
import math
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import TinyFollowersArena
from .player import TinyFollower
from .renderer import TinyFollowersRenderer
from .terrain import TinyTerrain


class TinyFollowersGame(GameTemplate):
    GAME_TITLE = "TINY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers glide every day"
    PLAYER_LABEL = "followers"

    def __init__(self):
        super().__init__()

        self.game_time = 0.0
        self.game_history = GameHistory()
        self.recent_eliminations: List[str] = []
        self.club_spotlight = None

        self.max_recent_eliminations = int(getattr(config, "TINY_ELIMINATION_TRACK_LIMIT", 400))
        self.max_game_time = float(getattr(config, "TINY_MAX_GAME_TIME", 80.0))
        self.difficulty_ramp = float(getattr(config, "TINY_DIFFICULTY_RAMP", 55.0))
        self.finish_grace_duration = float(getattr(config, "TINY_FINISH_GRACE_DURATION", 6.0))
        base_water_margin = float(getattr(config, "TINY_WATER_ELIMINATION_MARGIN", 120.0))
        # Allow deep but recoverable gap dives so slope timing can convert into big leaps.
        self.water_elimination_margin = max(base_water_margin, self.arena.height * 0.9)
        self.camera_follow_ratio = float(getattr(config, "TINY_CAMERA_FOLLOW_RATIO", 0.35))
        self.camera_smoothing = float(getattr(config, "TINY_CAMERA_SMOOTHING", 5.0))
        self.distance_scale = float(getattr(config, "TINY_DISTANCE_SCALE", 0.1))

        self.spawn_x = float(getattr(config, "TINY_START_X", 14.0))
        self.spawn_variance = float(getattr(config, "TINY_START_X_VARIANCE", 6.0))

        self.terrain = TinyTerrain(self.arena, seed=getattr(config, "DAY_NUMBER", 1))
        self.finish_x = self.terrain.finish_x
        self.camera_x = self.terrain.clamp_camera_x(self.terrain.world_start_x - 30.0)
        self.leader_x = self.terrain.world_start_x
        self.leader_name = ""
        self.first_finisher = None
        self.finish_trigger_time = None
        self.active_count = 0
        self.finished_count = 0
        self._detail_update_phase = 0
        self._last_detail_stride = 1
        self._high_pop_mode_logged = False
        self.high_pop_threshold = int(getattr(config, "TINY_HIGH_POP_OPTIMIZATION_THRESHOLD", 25000))
        self.target_detailed_updates = int(getattr(config, "TINY_TARGET_DETAILED_UPDATES_PER_FRAME", 14000))
        self.max_decision_throttle = float(getattr(config, "TINY_MAX_DECISION_THROTTLE", 3.5))

        self.sound.background_music_path = str(
            getattr(config, "TINY_BACKGROUND_MUSIC_PATH", "assets/Sydney Tour Song adjusted.m4a")
        )
        self.sound.preload_audio()
        self.recorder.background_music_path = self.sound.background_music_path

    def _init_game_components(self):
        self.arena = TinyFollowersArena()
        self.renderer = TinyFollowersRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)
        club_members = load_club_member_set()

        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]

            spawn_x = self.spawn_x + random.uniform(-self.spawn_variance, self.spawn_variance)
            ground_y, _, has_ground = self.terrain.sample(spawn_x)
            if not has_ground:
                spawn_x = self.spawn_x
                ground_y, _, _ = self.terrain.sample(spawn_x)

            player = TinyFollower(payload, (spawn_x, ground_y))
            player.y = ground_y - player.radius
            player.on_ground = True
            player.vy = 0.0
            player.vx = max(player.vx, player.min_ground_speed * random.uniform(0.94, 1.08))
            player.start_y = player.y
            player.best_y = player.y
            player.max_height_gain = 0.0

            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            self.players.append(player)

        self.club_spotlight = select_club_spotlight(self.players)
        self.active_count = len(self.players)
        self.finished_count = 0
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _difficulty(self) -> float:
        if self.difficulty_ramp <= 0:
            return 1.0
        return min(1.4, self.game_time / self.difficulty_ramp)

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        difficulty = self._difficulty()
        player_count = len(self.players)
        detail_stride = 1
        decision_scale = 1.0
        if (
            player_count >= self.high_pop_threshold
            and self.target_detailed_updates > 0
        ):
            detail_stride = max(1, int(math.ceil(player_count / float(self.target_detailed_updates))))
            decision_scale = min(self.max_decision_throttle, 1.0 + (detail_stride - 1) * 0.55)
            if detail_stride > 1 and not self._high_pop_mode_logged:
                print(
                    f"[INFO] Tiny high-pop optimization active: "
                    f"{player_count} players, detail stride={detail_stride}"
                )
                self._high_pop_mode_logged = True

        active_count = 0
        finished_count = 0
        leader_player = None

        for idx, player in enumerate(self.players):
            if detail_stride <= 1 or ((idx + self._detail_update_phase) % detail_stride == 0):
                player.update(
                    dt,
                    self.terrain,
                    self.game_time,
                    difficulty,
                    decision_scale=decision_scale,
                )
            else:
                player.fast_update(dt, self.terrain, difficulty)

            if player.finished:
                finished_count += 1
            elif player.alive:
                active_count += 1
                if player.y - player.radius > self.arena.bottom + self.water_elimination_margin:
                    self._eliminate_player(player)
                    active_count -= 1
                elif player.x >= self.finish_x:
                    player.mark_finished(self.game_time)
                    finished_count += 1
                    active_count -= 1
                    if self.first_finisher is None:
                        self.first_finisher = player
                        self.finish_trigger_time = self.game_time

            if (player.alive or player.finished) and (leader_player is None or player.max_x > leader_player.max_x):
                leader_player = player

        if detail_stride > 1:
            self._detail_update_phase = (self._detail_update_phase + 1) % detail_stride
        else:
            self._detail_update_phase = 0
        self._last_detail_stride = detail_stride
        self.active_count = active_count
        self.finished_count = finished_count

        if leader_player is not None:
            self.leader_x = leader_player.max_x
            self.leader_name = leader_player.username

        target_camera = self.leader_x - self.arena.width * self.camera_follow_ratio
        target_camera = self.terrain.clamp_camera_x(target_camera)
        lerp_strength = min(1.0, self.camera_smoothing * dt)
        self.camera_x += (target_camera - self.camera_x) * lerp_strength

        if self.first_finisher is not None and self.finish_trigger_time is None:
            self.finish_trigger_time = self.game_time

        should_finish = False
        if self.finish_trigger_time is not None:
            should_finish = (self.game_time - self.finish_trigger_time) >= self.finish_grace_duration
        elif self.max_game_time > 0 and self.game_time >= self.max_game_time:
            should_finish = True
        elif active_count <= 0:
            should_finish = True

        if should_finish:
            self._finish_game()

    def _eliminate_player(self, player: TinyFollower):
        if not player.alive:
            return
        player.eliminate()
        player.survival_time = self.game_time
        if player.username:
            self.recent_eliminations.insert(0, player.username)
            if len(self.recent_eliminations) > self.max_recent_eliminations:
                self.recent_eliminations.pop()

    def _finish_game(self):
        if self.game_over:
            return

        for player in self.players:
            if player.finished:
                player.survival_time = player.finish_time if player.finish_time is not None else self.game_time
            elif player.alive and player.survival_time <= 0:
                player.survival_time = self.game_time

        sorted_players = sorted(
            self.players,
            key=lambda p: (
                0 if p.finished else 1,
                p.finish_time if p.finish_time is not None else float("inf"),
                -(getattr(p, "max_x", p.x)),
                0 if p.alive else 1,
                p.username,
            ),
        )

        self.finish_game(sorted_players)

    def render(self):
        finish_ground_y, _, _ = self.terrain.sample(self.finish_x)
        distance_to_finish = max(0.0, (self.finish_x - self.leader_x) * self.distance_scale)

        game_state = {
            "phase": self.phase,
            "terrain": self.terrain,
            "camera_x": self.camera_x,
            "finish_x": self.finish_x,
            "finish_ground_y": finish_ground_y,
            "active_count": self.active_count,
            "finished_count": self.finished_count,
            "total_count": len(self.players),
            "elapsed_time": self.game_time,
            "leader_name": self.leader_name,
            "distance_to_finish": distance_to_finish,
            "highscore": self.statistics.get_game_highscore("tiny_followers"),
            "recent_eliminations": self.recent_eliminations,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
            "detail_stride": self._last_detail_stride,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[TinyFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "tiny_followers"
        game_display_name = "Tiny Followers"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)
            survival_time = getattr(player, "survival_time", 0.0)

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played,
            )

            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=points,
                survival_time=survival_time,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((player.username, placement, points, survival_time))
            game_history_results.append(
                {
                    "username": player.username,
                    "placement": placement,
                    "points": points,
                    "survival_time": survival_time,
                    "kills": 0,
                    "damage": 0.0,
                }
            )

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
        )

        if self.players:
            record_player = max(self.players, key=lambda p: getattr(p, "max_x", p.x))
            distance = max(0.0, (record_player.max_x - self.terrain.world_start_x) * self.distance_scale)
            self.statistics.update_game_highscore(
                game_type=game_type,
                score=int(distance),
                username=record_player.username,
                label="Meters",
            )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
