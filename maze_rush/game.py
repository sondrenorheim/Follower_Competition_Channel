import json
from PIL import Image
import math
import random
import time
from pathlib import Path
from typing import List, Set

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.participant_resolver import resolve_participants
from shared.platform_targets import (
    format_profile_text,
    get_youtube_game_profile,
    write_video_meta_sidecar,
)

from .arena import MazeRushArena
from .maze import Maze
from .player import MazeRushPlayer
from .renderer import MazeRushRenderer


class MazeRushGame(GameTemplate):
    GAME_TITLE = "MAZE RUSH"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.first_finisher = None
        self.game_history = GameHistory()
        self.player_speed = self._calculate_player_speed()
        self.render_players = []
        self.club_member_set = set()
        self.club_spotlight = None
        self.participant_source_info = {}
        self.youtube_profile = get_youtube_game_profile("maze_rush")
        self.finish_order: list[MazeRushPlayer] = []
        self.youtube_escape_target = int(self.youtube_profile.get("escape_target", 8) or 8)
        self.youtube_max_duration = float(self.youtube_profile.get("max_duration_seconds", 26.0) or 26.0)

    def _init_game_components(self):
        self.arena = MazeRushArena()
        arena_rect = self.arena.get_rect()
        cell_size = int(getattr(config, "MAZE_RUSH_CELL_SIZE", 20))
        wall_thickness = int(getattr(config, "MAZE_RUSH_WALL_THICKNESS", 3))
        corridor_size = cell_size - wall_thickness
        config.MAZE_RUSH_PLAYER_SIZE = max(4.0, float(corridor_size))
        seed = int(getattr(config, "DAY_NUMBER", 1))
        start_cell = (0, max(0, (arena_rect[3] // cell_size) - 1))
        self.maze = Maze(arena_rect, cell_size, seed, start_cell=start_cell)
        self.renderer = MazeRushRenderer(self.screen)

    def _calculate_player_speed(self) -> float:
        target_seconds = float(getattr(config, "MAZE_RUSH_TARGET_SECONDS", 52.5))
        speed_multiplier = float(getattr(config, "MAZE_RUSH_SPEED_MULTIPLIER", 1.0))
        shortest_steps = self.maze.distance_from_start.get(self.maze.exit_cell, 1)
        shortest_distance = shortest_steps * self.maze.cell_size
        if target_seconds <= 0:
            target_seconds = 52.5
        base_speed = shortest_distance / target_seconds
        return max(10.0, base_speed * speed_multiplier)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        participant_bundle = resolve_participants(
            "maze_rush",
            platform_target=self.platform_target,
        )
        self.participant_source_info = dict(participant_bundle)
        follower_data = list(participant_bundle.get("participants") or [])

        random.shuffle(follower_data)

        self.club_member_set = set() if self.native_youtube_mode else self._load_club_member_set()
        club_players = []
        regular_players = []

        start_pos = self.maze.cell_center(self.maze.start_cell)
        seed = int(getattr(config, "DAY_NUMBER", 1))

        for i, data in enumerate(follower_data):
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            username = str(payload.get("username", "") or "").strip().lstrip("@").lower()
            is_club_member = username in self.club_member_set
            player = MazeRushPlayer(
                payload,
                self.maze.start_cell,
                start_pos,
                rng_seed=seed + i + 1,
                size=getattr(config, "MAZE_RUSH_PLAYER_SIZE", 12),
                is_club_member=is_club_member,
            )
            self.players.append(player)
            if is_club_member:
                club_players.append(player)
            else:
                regular_players.append(player)

        if self.native_youtube_mode:
            self.render_players = list(self.players)
            self.club_spotlight = None
        else:
            self.render_players = regular_players + club_players
            self._select_club_spotlight()

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
            "game_mode": "maze_rush",
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

    def _load_club_member_set(self) -> Set[str]:
        base_dir = Path(__file__).resolve().parents[1]
        club_path = base_dir / "Followers" / "club_members_followers.json"
        if not club_path.exists():
            return set()

        try:
            with club_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Failed to load club members from {club_path}: {exc}")
            return set()

        members = set()
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                username = str(entry.get("username", "") or "").strip().lstrip("@").lower()
                if username:
                    members.add(username)
        return members

    def _select_club_spotlight(self) -> None:
        club_players = [
            player for player in self.players
            if getattr(player, "is_club_member", False)
        ]
        if not club_players:
            self.club_spotlight = None
            return
        day_seed = int(getattr(config, "DAY_NUMBER", 1))
        rng = random.Random(day_seed + 1337)
        spotlight = rng.choice(club_players)

        if spotlight.avatar_image is None:
            cache_dir = Path("avatar_cache")
            candidates = [
                cache_dir / f"{spotlight.username}.jpg",
                cache_dir / f"{str(spotlight.username).lower()}.jpg",
            ]
            for path in candidates:
                if not path.exists():
                    continue
                try:
                    with Image.open(path) as img:
                        spotlight.avatar_image = img.convert("RGBA")
                    break
                except Exception:
                    continue

        self.club_spotlight = spotlight
    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        newly_finished = []

        for player in self.players:
            if player.finished:
                continue
            player.update(dt, self.maze, self.player_speed, exit_cell=self.maze.exit_cell)
            if player.finished and player.finish_time is None:
                player.finish_time = self.game_time
                player.survival_time = self.game_time
                newly_finished.append(player)

        for player in newly_finished:
            if self.first_finisher is None:
                self.first_finisher = player
            self.finish_order.append(player)

        if self.native_youtube_mode:
            remaining_players = sum(1 for player in self.players if not player.finished)
            timed_out = self.youtube_max_duration > 0 and self.game_time >= self.youtube_max_duration
            if (
                remaining_players <= 0
                or len(self.finish_order) >= max(1, self.youtube_escape_target)
                or timed_out
            ):
                self._finish_game()
            return

        if self.first_finisher:
            self._finish_game()

    def _finish_game(self):
        if self.game_over:
            return

        finish_time = self.game_time
        if self.first_finisher and self.first_finisher.finish_time is not None:
            finish_time = self.first_finisher.finish_time

        distances = []
        for player in self.players:
            dist = self._distance_to_exit(player)
            distances.append((player, dist))
            player.survival_time = finish_time

        def sort_key(item):
            player, dist = item
            if self.native_youtube_mode:
                finish_index = finish_lookup.get(player)
                if finish_index is not None:
                    return (0, finish_index, 0.0, player.username)
                return (1, 999999.0, dist, player.username)
            is_winner = 0 if player is self.first_finisher else 1
            return (is_winner, dist, player.username)

        finish_lookup = {player: index for index, player in enumerate(self.finish_order)}
        sorted_players = [player for player, _ in sorted(distances, key=sort_key)]
        self.finish_game(sorted_players)

    def _distance_to_exit(self, player: MazeRushPlayer) -> float:
        cell_size = self.maze.cell_size
        if player.current_cell == self.maze.exit_cell and player.target_cell is None:
            return 0.0

        current_distance = self.maze.distance_to_exit.get(player.current_cell, 0) * cell_size
        if player.target_cell is None:
            return float(current_distance)

        target_distance = self.maze.distance_to_exit.get(player.target_cell, 0) * cell_size
        current_center = self.maze.cell_center(player.current_cell)
        target_center = self.maze.cell_center(player.target_cell)
        dist_to_current = math.hypot(player.x - current_center[0], player.y - current_center[1])
        dist_to_target = math.hypot(player.x - target_center[0], player.y - target_center[1])

        return min(dist_to_current + current_distance, dist_to_target + target_distance)

    def _get_leader(self):
        leader = None
        leader_distance = None
        for player in self.players:
            dist = self._distance_to_exit(player)
            if leader is None or dist < leader_distance:
                leader = player
                leader_distance = dist
        return leader

    def render(self):
        leader = self._get_leader() if self.players else None
        leader_name = leader.username if leader else None
        requested_count = int(
            self.participant_source_info.get("requested_count")
            or len(self.players)
            or 0
        )
        escaped_count = len(self.finish_order)
        remaining_count = max(0, len(self.players) - escaped_count)

        game_state = {
            "phase": self.phase,
            "maze": self.maze,
            "elapsed_time": self.game_time,
            "leader_name": leader_name,
            "club_spotlight": self.club_spotlight,
            "platform_target": self.platform_target,
            "native_youtube_mode": self.native_youtube_mode,
            "participant_count": len(self.players),
            "requested_count": requested_count,
            "escaped_count": escaped_count,
            "remaining_count": remaining_count,
            "youtube_profile": self.youtube_profile,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        render_players = self.render_players if self.render_players else self.players
        self.renderer.render_frame(render_players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[MazeRushPlayer]):
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
                "platform_target": self.platform_target,
                "youtube_participant_count": int(self.participant_source_info.get("youtube_count") or 0),
                "instagram_top_up_count": int(self.participant_source_info.get("instagram_top_up_count") or 0),
                "used_fallback": bool(self.participant_source_info.get("used_fallback")),
            },
        )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
