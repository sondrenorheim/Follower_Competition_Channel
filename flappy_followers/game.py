import random
import time
from dataclasses import dataclass
from typing import List, Optional

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight
from shared.participant_resolver import resolve_participants
from shared.platform_targets import (
    format_profile_text,
    get_youtube_game_profile,
    write_video_meta_sidecar,
)

from .arena import FlappyArena
from .player import FlappyFollower
from .renderer import FlappyFollowersRenderer


@dataclass
class PipePair:
    x: float
    gap_center: float
    gap_size: float
    width: float
    passed: bool = False


class FlappyFollowersGame(GameTemplate):
    GAME_TITLE = "FLAPPY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers flap every day"
    PLAYER_LABEL = "birds"

    def __init__(self):
        super().__init__()

        self.game_time = 0.0
        self.pipes: List[PipePair] = []
        self.pipes_cleared = 0
        self.game_history = GameHistory()
        self.recent_eliminations = []
        self.club_spotlight = None
        self.participant_source_info = {}
        self.youtube_profile = get_youtube_game_profile("flappy_followers")

        self.pipe_width = float(getattr(config, "FLAPPY_PIPE_WIDTH", 70.0))
        self.pipe_spacing = float(getattr(config, "FLAPPY_PIPE_SPACING", 220.0))
        self.pipe_start_offset = float(getattr(config, "FLAPPY_PIPE_START_OFFSET", 120.0))

        self.base_gap_size = float(getattr(config, "FLAPPY_GAP_SIZE", 160.0))
        self.min_gap_size = float(getattr(config, "FLAPPY_MIN_GAP_SIZE", 110.0))
        self.gap_shrink = float(getattr(config, "FLAPPY_GAP_SHRINK", 50.0))
        self.gap_edge_padding = float(getattr(config, "FLAPPY_GAP_EDGE_PADDING", 12.0))

        self.base_pipe_speed = float(getattr(config, "FLAPPY_PIPE_SPEED", 160.0))
        self.pipe_speed_boost = float(getattr(config, "FLAPPY_SPEED_BOOST", 80.0))
        self.difficulty_ramp = float(getattr(config, "FLAPPY_DIFFICULTY_RAMP", 50.0))
        self.max_game_time = float(getattr(config, "FLAPPY_MAX_GAME_TIME", 90.0))

        self.player_x_ratio = float(getattr(config, "FLAPPY_PLAYER_X_RATIO", 0.32))
        self.player_x_variance = float(getattr(config, "FLAPPY_PLAYER_X_VARIANCE", 18.0))

        if self.native_youtube_mode:
            self._apply_native_youtube_profile()

        self.current_gap_size = self.base_gap_size
        self.current_pipe_speed = self.base_pipe_speed
        self.player_x = self.arena.left + self.arena.width * self.player_x_ratio

        self._init_pipes()

    def _init_game_components(self):
        self.arena = FlappyArena()
        self.renderer = FlappyFollowersRenderer(self.screen)

    def _apply_native_youtube_profile(self):
        speed_multiplier = float(self.youtube_profile.get("speed_multiplier", 1.12) or 1.12)
        gap_scale = float(self.youtube_profile.get("gap_scale", 0.94) or 0.94)
        start_offset_scale = float(self.youtube_profile.get("start_offset_scale", 0.55) or 0.55)
        max_duration_seconds = float(self.youtube_profile.get("max_duration_seconds", 30.0) or 30.0)

        self.base_pipe_speed *= max(0.5, speed_multiplier)
        self.pipe_speed_boost *= max(0.5, speed_multiplier)
        self.base_gap_size *= max(0.5, gap_scale)
        self.min_gap_size *= max(0.5, gap_scale)
        self.pipe_start_offset *= max(0.2, start_offset_scale)
        self.max_game_time = max(6.0, min(self.max_game_time, max_duration_seconds))

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        participant_bundle = resolve_participants(
            "flappy_followers",
            platform_target=self.platform_target,
        )
        self.participant_source_info = dict(participant_bundle)
        follower_data = list(participant_bundle.get("participants") or [])

        random.shuffle(follower_data)
        club_members = set() if self.native_youtube_mode else load_club_member_set()

        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]

            x = self.player_x + random.uniform(-self.player_x_variance, self.player_x_variance)
            x = max(self.arena.left + 10, min(self.arena.right - 10, x))
            y = random.uniform(self.arena.top + 20, self.arena.bottom - 20)

            player = FlappyFollower(payload, (x, y))
            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            self.players.append(player)

        self.club_spotlight = None if self.native_youtube_mode else select_club_spotlight(self.players)
        self._write_platform_sidecar()
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _write_platform_sidecar(self) -> None:
        if not self.native_youtube_mode:
            return
        try:
            requested_count = int(
                self.participant_source_info.get("requested_count")
                or len(self.players)
                or 0
            )
        except Exception:
            requested_count = len(self.players)

        payload = {
            "platform_target": self.platform_target,
            "game_mode": "flappy_followers",
            "record_game_type": self.record_game_type,
            "record_game_display_name": self.record_game_display_name,
            "requested_count": requested_count,
            "participant_count": len(self.players),
            "youtube_count": int(self.participant_source_info.get("youtube_count") or 0),
            "instagram_top_up_count": int(self.participant_source_info.get("instagram_top_up_count") or 0),
            "used_fallback": bool(self.participant_source_info.get("used_fallback")),
            "hook_text": format_profile_text(self.youtube_profile.get("hook_primary"), requested_count),
            "hook_secondary": format_profile_text(self.youtube_profile.get("hook_secondary"), requested_count),
            "cta_text": str(self.youtube_profile.get("cta_text", "") or ""),
            "ending_text": str(self.youtube_profile.get("ending_text", "") or ""),
        }
        sidecar_path = write_video_meta_sidecar(config.OUTPUT_VIDEO_PATH, payload)
        print(f"[INFO] Wrote native YouTube sidecar: {sidecar_path}")

    def _init_pipes(self):
        self.pipes = []
        self.pipes_cleared = 0

        spacing = self.pipe_spacing
        start_x = self.arena.right + self.pipe_start_offset
        pipe_count = int((self.arena.width + spacing * 2) // spacing) + 2

        for i in range(pipe_count):
            x = start_x + i * spacing
            gap_center = self._random_gap_center(self.current_gap_size)
            self.pipes.append(PipePair(x=x, gap_center=gap_center, gap_size=self.current_gap_size, width=self.pipe_width))

    def _random_gap_center(self, gap_size: float) -> float:
        gap_half = gap_size * 0.5
        min_y = self.arena.top + gap_half + self.gap_edge_padding
        max_y = self.arena.bottom - gap_half - self.gap_edge_padding
        if min_y >= max_y:
            min_y = self.arena.top + gap_half
            max_y = self.arena.bottom - gap_half
        return random.uniform(min_y, max_y)

    def _difficulty(self) -> float:
        if self.difficulty_ramp <= 0:
            return 1.0
        return min(1.0, self.game_time / self.difficulty_ramp)

    def _update_pipes(self, dt: float):
        if not self.pipes:
            return

        for pipe in self.pipes:
            pipe.x -= self.current_pipe_speed * dt
            if not pipe.passed and pipe.x + pipe.width < self.player_x:
                pipe.passed = True
                self.pipes_cleared += 1

        max_x = max(pipe.x for pipe in self.pipes)
        reset_threshold = self.arena.left - self.pipe_spacing

        for pipe in self.pipes:
            if pipe.x + pipe.width < reset_threshold:
                pipe.x = max_x + self.pipe_spacing
                max_x = pipe.x
                pipe.gap_size = self.current_gap_size
                pipe.gap_center = self._random_gap_center(pipe.gap_size)
                pipe.passed = False

    def _get_next_pipe(self) -> Optional[PipePair]:
        if not self.pipes:
            return None

        target_x = self.player_x
        candidates = [pipe for pipe in self.pipes if pipe.x + pipe.width >= target_x]
        if not candidates:
            return None
        return min(candidates, key=lambda p: p.x)

    def _collides_with_pipe(self, player: FlappyFollower) -> bool:
        for pipe in self.pipes:
            if player.x + player.radius < pipe.x or player.x - player.radius > pipe.x + pipe.width:
                continue

            gap_half = pipe.gap_size * 0.5
            gap_top = pipe.gap_center - gap_half
            gap_bottom = pipe.gap_center + gap_half

            if player.y - player.radius < gap_top or player.y + player.radius > gap_bottom:
                return True

        return False

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        difficulty = self._difficulty()

        self.current_gap_size = max(self.min_gap_size, self.base_gap_size - self.gap_shrink * difficulty)
        self.current_pipe_speed = self.base_pipe_speed + self.pipe_speed_boost * difficulty

        self._update_pipes(dt)
        next_pipe = self._get_next_pipe()

        for player in self.players:
            player.update(dt, self.arena, next_pipe, self.game_time, difficulty)

            if not player.alive:
                continue

            if not self.arena.is_inside_vertical(player.y, player.radius):
                player.eliminate()
                player.survival_time = self.game_time
                self._record_player_pipes(player)
                self._record_elimination(player)
                continue

            if self._collides_with_pipe(player):
                player.eliminate()
                player.survival_time = self.game_time
                self._record_player_pipes(player)
                self._record_elimination(player)

        alive_count = sum(1 for p in self.players if p.alive)
        if alive_count <= 1 or self.game_time >= self.max_game_time:
            self._finish_game()

    def _record_player_pipes(self, player: FlappyFollower):
        if getattr(player, "pipes_passed", None) is None:
            player.pipes_passed = int(self.pipes_cleared)

    def _record_elimination(self, player: FlappyFollower):
        if not player or not getattr(player, "username", ""):
            return
        self.recent_eliminations.insert(0, player.username)

    def _finish_game(self):
        if self.game_over:
            return

        for player in self.players:
            if player.alive and player.survival_time <= 0:
                player.survival_time = self.game_time
            if getattr(player, "pipes_passed", None) is None:
                if player.alive:
                    player.pipes_passed = int(self.pipes_cleared)
                else:
                    player.pipes_passed = 0

        sorted_players = sorted(
            self.players,
            key=lambda p: (
                not p.alive,
                -(getattr(p, "pipes_passed", 0) or 0),
                -getattr(p, "survival_time", 0.0),
                p.username,
            ),
        )

        self.finish_game(sorted_players)

    def _apply_tied_placements(self, sorted_players: List[FlappyFollower]):
        placement = 1
        last_pipes = None

        for idx, player in enumerate(sorted_players):
            pipes_passed = getattr(player, "pipes_passed", 0) or 0
            if last_pipes is None:
                placement = 1
            elif pipes_passed != last_pipes:
                placement = idx + 1
            player.placement = placement
            last_pipes = pipes_passed

    def finish_game(self, sorted_players: List[FlappyFollower]):
        self.game_over = True
        self.phase = "finished"

        self._apply_tied_placements(sorted_players)

        if sorted_players:
            self.winner = sorted_players[0]

        print("\n" + "=" * 60)
        print("  GAME COMPLETE")
        print("=" * 60)

        print("\nTop 10:")
        for i, player in enumerate(sorted_players[:10]):
            print(f"{i+1}. {player.username}")

        self._calculate_and_save_scores(sorted_players)

    def render(self):
        alive_count = sum(1 for p in self.players if p.alive)

        game_state = {
            "phase": self.phase,
            "pipes": self.pipes,
            "alive_count": alive_count,
            "pipes_cleared": self.pipes_cleared,
            "elapsed_time": self.game_time,
            "highscore": self.statistics.get_game_highscore(self.record_game_type),
            "recent_eliminations": self.recent_eliminations,
            "platform_target": self.platform_target,
            "native_youtube_mode": self.native_youtube_mode,
            "participant_count": len(self.players),
            "requested_count": int(self.participant_source_info.get("requested_count") or len(self.players) or 0),
            "youtube_profile": self.youtube_profile,
            "current_pipe_speed": self.current_pipe_speed,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[FlappyFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = self.record_game_type
        game_display_name = self.record_game_display_name
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
            game_history_results.append({
                "username": player.username,
                "placement": placement,
                "points": points,
                "survival_time": survival_time,
                "kills": 0,
                "damage": 0.0,
            })

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
            extra_data={
                "platform_target": self.platform_target,
                "youtube_participant_count": int(self.participant_source_info.get("youtube_count") or 0),
                "instagram_top_up_count": int(self.participant_source_info.get("instagram_top_up_count") or 0),
                "used_fallback": bool(self.participant_source_info.get("used_fallback")),
            },
        )

        record_player = None
        record_pipes = 0
        for player in self.players:
            pipes_passed = int(getattr(player, "pipes_passed", 0) or 0)
            if pipes_passed > record_pipes:
                record_pipes = pipes_passed
                record_player = player

        if record_player is not None:
            self.statistics.update_game_highscore(
                game_type=game_type,
                score=int(record_pipes),
                username=record_player.username,
                label="Pipes",
            )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
