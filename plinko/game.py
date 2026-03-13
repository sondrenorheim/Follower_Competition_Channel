"""
Plinko game controller.
"""

import random
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import pygame

import config
import shared.api as shared_api
from shared import GameTemplate, GameHistory, auto_push

from .arena import PlinkoArena
from .player import PlinkoPlayer
from .renderer import PlinkoRenderer


class PlinkoGame(GameTemplate):
    GAME_TITLE = "PLINKO"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = "dropping"
        self.hole_counts = []
        self.safe_holes = set()
        self.round_start_time = 0.0
        self.recent_eliminations: List[str] = []
        self.round_players: List[PlinkoPlayer] = []
        self.round_reopen_pairs = 0
        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = PlinkoArena()
        self.renderer = PlinkoRenderer(self.screen)

    def setup_players(self):
        self._refresh_discord_followers()
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        player_radius = float(getattr(config, "PLINKO_PLAYER_RADIUS", 12))
        config.FOLLOWER_RADIUS = player_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

        seed = int(getattr(config, "DAY_NUMBER", 1))

        for i, data in enumerate(follower_data):
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            start_pos = self.arena.get_spawn_position(player_radius)
            player = PlinkoPlayer(payload, start_pos, rng_seed=seed + i + 1)
            player.eliminated = False
            player.round_complete = False
            player.current_hole = None
            player.eliminated_round = None
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")
        self._start_round(increment_round=True)

    def _refresh_discord_followers(self):
        if config.TEST_MINIMAL_PLAYERS:
            return

        repo_root = Path(__file__).resolve().parents[1]
        overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
        output_file = getattr(config, "FOLLOWER_IMPORT_FILE", "") or ""
        if isinstance(overrides, dict):
            output_file = overrides.get("plinko", output_file) or output_file
        if not output_file:
            output_file = "Followers/discord_followers.json"

        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = repo_root / output_path

        self.api.import_file = str(output_path)

        export_script = Path("discord_members_export.py")
        if not export_script.is_absolute():
            export_script = repo_root / export_script
        if not export_script.exists():
            print(f"Discord export script not found: {export_script}")
            return

        guild_file = Path("guild.txt")
        if not guild_file.is_absolute():
            guild_file = repo_root / guild_file

        token_file = Path("discord_bot_token.txt")
        if not token_file.is_absolute():
            token_file = repo_root / token_file

        try:
            shared_api.clear_prefetched_followers()
        except Exception:
            pass

        command = [
            sys.executable,
            str(export_script),
            "--guild-id-file",
            str(guild_file),
            "--out",
            str(output_path),
            "--token-file",
            str(token_file),
            "--use-nick",
        ]

        print("Refreshing Discord followers for Plinko...")
        result = subprocess.run(command)
        if result.returncode != 0:
            if output_path.exists():
                print(
                    f"Discord export failed (exit code {result.returncode}); "
                    f"using existing file: {output_path}"
                )
            else:
                print(
                    f"Discord export failed (exit code {result.returncode}); "
                    f"no existing file found."
                )
        else:
            print(f"Discord followers updated: {output_path}")

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt

        active_players = list(self.round_players)
        for player in active_players:
            if player.round_complete:
                continue
            hole_index = player.update(dt, self.arena)
            if hole_index is not None:
                player.round_complete = True
                player.current_hole = hole_index
                if 0 <= hole_index < len(self.hole_counts):
                    self.hole_counts[hole_index] += 1
                if 0 <= hole_index < len(self.arena.hole_centers):
                    player.x = self.arena.hole_centers[hole_index]
                player.y = self.arena.hole_top + player.radius + 1
                player.vx = 0.0
                player.vy = 0.0
                self._apply_live_elimination_if_needed(player)

        self._force_round_completion_if_needed(active_players)

        if active_players and all(p.round_complete for p in active_players):
            self._resolve_round(active_players)

    def render(self):
        leader_name = None

        game_state = {
            "phase": self.phase,
            "arena": self.arena,
            "round_number": self.round_index,
            "safe_holes": set(self.safe_holes),
            "hole_counts": list(self.hole_counts),
            "alive_count": sum(1 for p in self.players if not p.eliminated),
            "recent_eliminations": list(self.recent_eliminations),
            "leader_name": leader_name,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _start_round(self, increment_round: bool):
        if increment_round:
            self.round_index += 1
            self.round_reopen_pairs = 0

        base_safe_holes = self._compute_safe_holes()
        self.safe_holes = self._expand_safe_holes_from_outer(base_safe_holes)
        hole_count = len(self.arena.holes)
        self.hole_counts = [0 for _ in range(hole_count)]
        self.round_start_time = self.game_time
        self.round_players = []

        for player in self.players:
            if player.eliminated:
                continue
            player.reset_for_round(self.arena)
            self.round_players.append(player)

    def _compute_safe_holes(self):
        hole_count = len(self.arena.holes)
        if hole_count == 0:
            return set()

        if hole_count % 2 == 1:
            eliminated_span = 1 + 2 * (self.round_index - 1)
        else:
            eliminated_span = 2 + 2 * (self.round_index - 1)
        eliminated_span = min(hole_count - 2, max(1, eliminated_span))

        if hole_count % 2 == 1:
            center = hole_count // 2
            half = eliminated_span // 2
            start = center - half
            end = center + half
        else:
            center_left = hole_count // 2 - 1
            half = eliminated_span // 2
            start = center_left - (half - 1)
            end = center_left + half

        eliminated = set(range(max(0, start), min(hole_count, end + 1)))
        safe = set(range(hole_count)) - eliminated
        return safe

    def _resolve_round(self, active_players: List[PlinkoPlayer]):
        survivors = [p for p in active_players if p.current_hole in self.safe_holes]
        if not survivors:
            # Reopen one outer pair (2 holes) and retry same round.
            self._rollback_live_eliminations(active_players)
            self.round_reopen_pairs += 1
            self._start_round(increment_round=False)
            return

        if len(survivors) == 1:
            self._finish_game(winner=survivors[0])
            return

        self._start_round(increment_round=True)

    def _expand_safe_holes_from_outer(self, base_safe_holes: set):
        hole_count = len(self.arena.holes)
        if hole_count <= 0:
            return set()

        safe = set(base_safe_holes)
        pairs_to_open = max(0, int(self.round_reopen_pairs))
        if pairs_to_open <= 0:
            return safe

        left = 0
        right = hole_count - 1
        while left <= right and pairs_to_open > 0:
            if left not in safe or right not in safe:
                safe.add(left)
                safe.add(right)
                pairs_to_open -= 1
            left += 1
            right -= 1

        return safe

    def _record_elimination(self, username: str):
        if not username:
            return
        self.recent_eliminations.insert(0, username)

    def _remove_elimination(self, username: str):
        if not username:
            return
        try:
            index = self.recent_eliminations.index(username)
        except ValueError:
            return
        self.recent_eliminations.pop(index)

    def _apply_live_elimination_if_needed(self, player: PlinkoPlayer):
        if player.current_hole in self.safe_holes or player.eliminated:
            return
        player.eliminated = True
        player.alive = False
        player.eliminated_round = self.round_index
        player.survival_time = self.game_time
        self._record_elimination(player.username)

    def _rollback_live_eliminations(self, active_players: List[PlinkoPlayer]):
        for player in active_players:
            if player.current_hole in self.safe_holes:
                continue
            if not player.eliminated:
                continue
            player.eliminated = False
            player.alive = True
            player.eliminated_round = None
            player.survival_time = 0.0
            self._remove_elimination(player.username)

    def _force_round_completion_if_needed(self, active_players: List[PlinkoPlayer]):
        time_limit = float(getattr(config, "PLINKO_ROUND_TIME_LIMIT", 20.0))
        if time_limit <= 0:
            return
        if (self.game_time - self.round_start_time) < time_limit:
            return

        for player in active_players:
            if player.round_complete:
                continue
            hole_index = self.arena.get_nearest_hole_index(player.x)
            if hole_index is None:
                continue
            player.round_complete = True
            player.current_hole = hole_index
            if 0 <= hole_index < len(self.hole_counts):
                self.hole_counts[hole_index] += 1
            if 0 <= hole_index < len(self.arena.hole_centers):
                player.x = self.arena.hole_centers[hole_index]
            player.y = self.arena.hole_top + player.radius + 1
            player.vx = 0.0
            player.vy = 0.0
            self._apply_live_elimination_if_needed(player)

    def _finish_game(self, winner: PlinkoPlayer):
        if self.game_over:
            return

        finish_time = self.game_time
        for player in self.players:
            if player.survival_time is None:
                player.survival_time = finish_time

        winner.eliminated = False
        winner.alive = True

        def sort_key(player: PlinkoPlayer):
            round_value = player.eliminated_round or (self.round_index + 1)
            return (-round_value, player.username)

        sorted_players = sorted(self.players, key=sort_key)
        self.finish_game(sorted_players)

    def _calculate_and_save_scores(self, sorted_players: List[PlinkoPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "plinko"
        game_display_name = "Plinko"
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
        )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
