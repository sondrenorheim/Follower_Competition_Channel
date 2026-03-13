"""Discord Signal game controller."""

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

from .arena import DiscordSignalArena
from .player import DiscordSignalPlayer
from .renderer import DiscordSignalRenderer


class DiscordSignalGame(GameTemplate):
    GAME_TITLE = "DISCORD SIGNAL"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.safe_zone = None
        self.spinner_zone = None
        self.target_zone = None
        self.open_zones = []
        self.result_elapsed = 0.0
        self.spinner_order = [0, 1, 3, 2]
        self.spinner_index = 0
        self.spin_steps_remaining = 0
        self.spin_step_timer = 0.0
        self.last_safe_zone = None
        self.last_eliminated = 0
        self.active_players = []
        self.initial_total_players = 0
        self.last_player_radius = config.FOLLOWER_RADIUS
        self.survival_ratio = float(getattr(config, "DISCORD_SIGNAL_SURVIVAL_RATIO", 0.55))
        self.selection_duration = float(
            getattr(
                config,
                "DISCORD_SIGNAL_SELECTION_DURATION",
                getattr(config, "DISCORD_SIGNAL_ROUND_DURATION", 7.0),
            )
        )
        self.spin_duration = float(getattr(config, "DISCORD_SIGNAL_SPIN_DURATION", 2.4))
        self.spin_step = float(getattr(config, "DISCORD_SIGNAL_SPIN_STEP", 0.18))
        self.result_duration = float(getattr(config, "DISCORD_SIGNAL_RESULT_DURATION", 2.0))
        self.radius_multiplier = float(getattr(config, "DISCORD_SIGNAL_RADIUS_MULT", 1.0))
        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = DiscordSignalArena()
        self.renderer = DiscordSignalRenderer(self.screen)

    def setup_players(self):
        self._refresh_discord_followers()
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        start_radius = config.FOLLOWER_RADIUS
        if config.USE_DYNAMIC_SCALING:
            total_players = len(follower_data)
            safe_radius = min(self.arena.current_width, self.arena.current_height) / 2
            start_radius = config.calculate_dynamic_follower_radius(
                total_players=total_players,
                alive_count=total_players,
                safe_zone_radius=safe_radius,
                initial_zone_radius=safe_radius,
            )
        start_radius *= self.radius_multiplier
        config.FOLLOWER_RADIUS = start_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

        for i, data in enumerate(follower_data):
            position = self._get_starting_position(i, len(follower_data))
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = self._create_player(payload, position)
            self.players.append(player)

        self.active_players = list(self.players)
        self.initial_total_players = len(self.players)
        self.last_player_radius = config.FOLLOWER_RADIUS
        if hasattr(self, "renderer") and hasattr(self.renderer, "clear_avatar_cache"):
            self.renderer.clear_avatar_cache()

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _apply_dynamic_radius(self, new_radius: float) -> None:
        if abs(new_radius - self.last_player_radius) <= 0.01:
            return
        self.last_player_radius = new_radius
        config.FOLLOWER_RADIUS = new_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
        for player in self.active_players:
            if not player.alive:
                continue
            player.radius = new_radius
            player.x, player.y = self.arena.clamp_position(player.x, player.y, new_radius)
        if hasattr(self, "renderer") and hasattr(self.renderer, "clear_avatar_cache"):
            self.renderer.clear_avatar_cache()

    def _prune_inactive_players(self) -> None:
        self.active_players = [player for player in self.active_players if player.alive or player.falling]

    def _refresh_discord_followers(self):
        if config.TEST_MINIMAL_PLAYERS:
            return

        repo_root = Path(__file__).resolve().parents[1]
        overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
        output_file = getattr(config, "FOLLOWER_IMPORT_FILE", "") or ""
        if isinstance(overrides, dict):
            output_file = overrides.get("discord_signal", output_file) or output_file
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

        print("Refreshing Discord followers for Discord Signal...")
        result = subprocess.run(command)
        if result.returncode != 0:
            if output_path.exists():
                print(
                    "Discord export failed (exit code "
                    f"{result.returncode}); using existing file: {output_path}"
                )
            else:
                print(
                    "Discord export failed (exit code "
                    f"{result.returncode}); no existing file found."
                )
        else:
            print(f"Discord followers updated: {output_path}")

    def _create_player(self, follower_data: dict, position: tuple) -> DiscordSignalPlayer:
        return DiscordSignalPlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        margin = max(2.0, config.FOLLOWER_RADIUS + 2)
        zone_id = random.choice(self.arena.zones)
        return self.arena.get_random_position_in_zone(zone_id, margin=margin)

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt

        if not self.players:
            return

        if self.round_phase is None:
            self._start_selection_round()

        self._prune_inactive_players()
        for player in self.active_players:
            player.update(dt, self.arena, self.round_phase or "")

        self._prune_inactive_players()
        alive_players = [p for p in self.active_players if p.alive]

        if self.round_phase not in {"selection", "spin", "result"}:
            return

        falling_players_active = any(player.falling for player in self.active_players)
        if config.USE_DYNAMIC_SCALING and self.initial_total_players > 0 and not falling_players_active:
            safe_radius = min(self.arena.current_width, self.arena.current_height) / 2
            new_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=max(1, len(alive_players)),
                safe_zone_radius=safe_radius,
                initial_zone_radius=safe_radius,
            )
            self._apply_dynamic_radius(new_radius * self.radius_multiplier)

        if self.round_phase == "selection":
            self.phase_time_left -= dt
            if self.phase_time_left <= 0:
                self._start_spin_phase([p for p in self.active_players if p.alive])
        elif self.round_phase == "spin":
            self._update_spinner(dt, alive_players)
        elif self.round_phase == "result":
            self.phase_time_left -= dt
            self.result_elapsed += dt
            if self.phase_time_left <= 0:
                self._end_result_phase()

    def _start_selection_round(self):
        alive_players = [p for p in self.active_players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_index += 1
        self.round_phase = "selection"
        self.phase_time_left = self.selection_duration
        self.last_eliminated = 0
        self.safe_zone = None
        self.spinner_zone = None
        self.target_zone = None
        self.open_zones = []
        self.result_elapsed = 0.0

        self._assign_selection_zones(alive_players)

    def _assign_selection_zones(self, alive_players: List[DiscordSignalPlayer]) -> None:
        zones = list(self.arena.zones)
        if not zones:
            return
        shuffled_players = list(alive_players)
        random.shuffle(shuffled_players)
        random.shuffle(zones)
        for index, player in enumerate(shuffled_players):
            if index < len(zones):
                zone = zones[index]
            else:
                zone = random.choice(zones)
            player.assign_zone(zone, self.arena)

    def _start_spin_phase(self, alive_players: List[DiscordSignalPlayer]):
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_phase = "spin"
        self.phase_time_left = self.spin_duration
        self.result_elapsed = 0.0
        self.safe_zone = None
        self.open_zones = []

        self.target_zone = self._choose_target_zone(alive_players)
        self._start_spinner()

        if self.round_phase == "spin":
            for player in alive_players:
                player.assign_target((player.x, player.y))
                player.vx = 0.0
                player.vy = 0.0

    def _choose_target_zone(self, alive_players: List[DiscordSignalPlayer]) -> int:
        alive_count = len(alive_players)
        zone_counts = {zone: 0 for zone in self.arena.zones}
        for player in alive_players:
            zone = self.arena.get_zone_for_position(player.x, player.y)
            zone_counts[zone] += 1

        valid_zones = [zone for zone, count in zone_counts.items() if count > 0]
        if not valid_zones:
            valid_zones = list(self.arena.zones)

        if alive_count <= 0:
            return random.choice(valid_zones)

        target_survivors = max(1, int(round(alive_count * self.survival_ratio)))
        best_delta = min(abs(zone_counts.get(zone, 0) - target_survivors) for zone in valid_zones)
        best_zones = [
            zone for zone in valid_zones
            if abs(zone_counts.get(zone, 0) - target_survivors) == best_delta
        ]

        if self.last_safe_zone in best_zones and len(best_zones) > 1:
            best_zones = [zone for zone in best_zones if zone != self.last_safe_zone]

        if not best_zones:
            best_zones = valid_zones

        return random.choice(best_zones)

    def _start_spinner(self):
        order = [zone for zone in self.spinner_order if zone in self.arena.zones]
        if not order:
            order = list(self.arena.zones)
        self.spinner_order = order

        if self.spin_duration <= 0 or self.spin_step <= 0:
            self.spin_steps_remaining = 0
            self.spinner_zone = self.target_zone
            self._start_result_phase([p for p in self.active_players if p.alive])
            return

        steps = max(1, int(round(self.spin_duration / self.spin_step)))
        self.spin_steps_remaining = steps
        self.spin_step_timer = 0.0

        if self.target_zone not in self.spinner_order:
            self.target_zone = random.choice(self.spinner_order)
        target_index = self.spinner_order.index(self.target_zone)
        self.spinner_index = (target_index - steps) % len(self.spinner_order)
        self.spinner_zone = self.spinner_order[self.spinner_index]

    def _update_spinner(self, dt: float, alive_players: List[DiscordSignalPlayer]):
        if self.round_phase != "spin":
            return

        self.phase_time_left -= dt
        self.spin_step_timer += dt

        while self.spin_step_timer >= self.spin_step and self.spin_steps_remaining > 0:
            self.spin_step_timer -= self.spin_step
            self.spin_steps_remaining -= 1
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_order)
            self.spinner_zone = self.spinner_order[self.spinner_index]

        if self.phase_time_left <= 0 or self.spin_steps_remaining <= 0:
            self._start_result_phase(alive_players)

    def _start_result_phase(self, alive_players: List[DiscordSignalPlayer]):
        if self.round_phase == "result":
            return
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_phase = "result"
        self.phase_time_left = self.result_duration
        self.result_elapsed = 0.0
        self.safe_zone = self.target_zone
        self.spinner_zone = None
        self.last_safe_zone = self.safe_zone

        survivors = []
        eliminated = []
        for player in alive_players:
            zone = self.arena.get_zone_for_position(player.x, player.y)
            if zone == self.safe_zone:
                survivors.append(player)
            else:
                eliminated.append(player)

        if not survivors and eliminated:
            fallback = random.choice(eliminated)
            self.safe_zone = self.arena.get_zone_for_position(fallback.x, fallback.y)
            survivors = [player for player in alive_players if self.arena.get_zone_for_position(player.x, player.y) == self.safe_zone]
            eliminated = [player for player in alive_players if player not in survivors]

        self.open_zones = [zone for zone in self.arena.zones if zone != self.safe_zone]

        alive_players = [p for p in self.active_players if p.alive]
        alive_count = len(alive_players)
        eliminated.sort(key=lambda p: (p.x - self.arena.center_x) ** 2 + (p.y - self.arena.center_y) ** 2)
        placement = alive_count
        for player in eliminated:
            player.start_fall(placement, self.game_time)
            placement -= 1

        self.last_eliminated = len(eliminated)

    def _end_result_phase(self):
        alive_players = [p for p in self.active_players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
        else:
            self._start_selection_round()

    def _finish_game(self):
        if self.game_over:
            return

        alive_players = [p for p in self.players if p.alive]
        winner = alive_players[0] if alive_players else None
        if winner:
            winner.placement = 1
            winner.survival_time = self.game_time

        total_players = len(self.players)
        for player in self.players:
            if player.placement is None:
                player.placement = total_players
            if not player.survival_time:
                player.survival_time = player.elimination_time or self.game_time

        sorted_players = sorted(self.players, key=lambda p: p.placement)
        self.winner = winner
        self.finish_game(sorted_players)

    def render(self):
        alive_count = sum(1 for p in self.active_players if p.alive)

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index,
            "phase_time_left": max(0.0, self.phase_time_left),
            "alive_count": alive_count,
            "total_count": len(self.players),
            "last_eliminated": self.last_eliminated,
            "safe_zone": self.safe_zone,
            "spinner_zone": self.spinner_zone,
            "open_zones": self.open_zones,
            "result_elapsed": self.result_elapsed,
            "result_duration": self.result_duration,
            "arena": self.arena,
            "elapsed_time": self.game_time,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.active_players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[DiscordSignalPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "discord_signal"
        game_display_name = "Discord Signal"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=player.survival_time,
                games_played=games_played,
            )

            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=points,
                survival_time=player.survival_time,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((player.username, placement, points, player.survival_time))
            game_history_results.append(
                {
                    "username": player.username,
                    "placement": placement,
                    "points": points,
                    "survival_time": player.survival_time,
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

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
