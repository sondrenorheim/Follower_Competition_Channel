"""Beacon Blitz game controller."""

import math
import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import BeaconBlitzArena
from .player import BeaconBlitzPlayer
from .renderer import BeaconBlitzRenderer


class BeaconBlitzGame(GameTemplate):
    GAME_TITLE = "BEACON BLITZ"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.beacon_pos = None
        self.last_eliminated = 0
        self.active_players = []
        self.update_frame_counter = 0
        self.update_batches_per_frame = int(getattr(config, "UPDATE_BATCHES_PER_FRAME", 4))
        self.throttle_threshold = int(getattr(config, "BEACON_BLITZ_THROTTLE_THRESHOLD", 12000))
        self.survival_ratio = float(getattr(config, "BEACON_BLITZ_SURVIVAL_RATIO", 0.55))
        self.rush_duration = float(getattr(config, "BEACON_BLITZ_RUSH_DURATION", 8.0))
        self.pulse_duration = float(getattr(config, "BEACON_BLITZ_PULSE_DURATION", 1.5))
        self.target_radius = float(getattr(config, "BEACON_BLITZ_TARGET_RADIUS", 60.0))
        self.initial_total_players = 0
        self.last_player_radius = config.FOLLOWER_RADIUS
        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = BeaconBlitzArena()
        self.renderer = BeaconBlitzRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        if config.USE_DYNAMIC_SCALING:
            total_players = len(follower_data)
            safe_radius = min(self.arena.current_width, self.arena.current_height) / 2
            start_radius = config.calculate_dynamic_follower_radius(
                total_players=total_players,
                alive_count=total_players,
                safe_zone_radius=safe_radius,
                initial_zone_radius=safe_radius,
            )
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

        # Initialize dynamic scaling radius.
        if config.USE_DYNAMIC_SCALING and self.players:
            safe_radius = min(self.arena.current_width, self.arena.current_height) / 2
            initial_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=self.initial_total_players,
                safe_zone_radius=safe_radius,
                initial_zone_radius=safe_radius,
            )
            self._apply_dynamic_radius(initial_radius)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _apply_dynamic_radius(self, new_radius: float) -> None:
        if abs(new_radius - self.last_player_radius) <= 0.01:
            return
        self.last_player_radius = new_radius
        config.FOLLOWER_RADIUS = new_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
        for player in self.active_players:
            player.radius = new_radius
        if hasattr(self, "renderer") and hasattr(self.renderer, "clear_avatar_cache"):
            self.renderer.clear_avatar_cache()

    def _prune_inactive_players(self, current_time: float) -> None:
        fade_duration = float(getattr(config, "FADE_DURATION", 0.5))
        fade_cutoff = current_time - fade_duration
        self.active_players = [
            player for player in self.active_players
            if player.alive or (player.elimination_time is not None and player.elimination_time >= fade_cutoff)
        ]

    def _create_player(self, follower_data: dict, position: tuple) -> BeaconBlitzPlayer:
        return BeaconBlitzPlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        margin = max(2.0, config.FOLLOWER_RADIUS + 2)
        return self.arena.get_random_point(margin=margin)

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
            self._start_round()

        self._prune_inactive_players(self.game_time)
        self._update_players(dt)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            if self.round_phase == "rush":
                self._start_pulse()
            elif self.round_phase == "pulse":
                self._start_round()

    def _update_players(self, dt: float):
        alive_players = [player for player in self.active_players if player.alive]
        alive_count = len(alive_players)

        if not alive_players:
            return

        if config.ENABLE_UPDATE_THROTTLING and alive_count > self.throttle_threshold:
            self.update_frame_counter += 1
            batch_index = self.update_frame_counter % self.update_batches_per_frame
            batch_size = (alive_count + self.update_batches_per_frame - 1) // self.update_batches_per_frame
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, alive_count)
            players_to_update = alive_players[start_idx:end_idx]
        else:
            players_to_update = alive_players

        for player in players_to_update:
            player.update(dt, self.arena)

        # Dynamic scaling based on remaining players.
        if config.USE_DYNAMIC_SCALING and self.initial_total_players > 0:
            safe_radius = min(self.arena.current_width, self.arena.current_height) / 2
            new_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=alive_count,
                safe_zone_radius=safe_radius,
                initial_zone_radius=safe_radius,
            )
            self._apply_dynamic_radius(new_radius)

    def _start_round(self):
        alive_players = [p for p in self.active_players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_index += 1
        self.round_phase = "rush"
        self.phase_time_left = self.rush_duration
        self.last_eliminated = 0

        margin = max(10.0, self.target_radius + 10)
        self.beacon_pos = self.arena.get_random_point(margin=margin)

        for player in alive_players:
            player.set_target(self.beacon_pos, self.target_radius)

    def _start_pulse(self):
        alive_players = [p for p in self.active_players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_phase = "pulse"
        self.phase_time_left = self.pulse_duration
        self._resolve_pulse(alive_players)

    def _resolve_pulse(self, alive_players: List[BeaconBlitzPlayer]):
        alive_count = len(alive_players)
        if alive_count <= 1:
            self._finish_game()
            return

        ratio = max(0.05, min(self.survival_ratio, 0.95))
        survivors_target = int(math.ceil(alive_count * ratio))
        survivors_target = max(1, min(alive_count - 1, survivors_target))

        distances = []
        for player in alive_players:
            dx = player.x - self.beacon_pos[0]
            dy = player.y - self.beacon_pos[1]
            dist = math.hypot(dx, dy)
            distances.append((player, dist))

        distances.sort(key=lambda item: item[1])
        survivors = [player for player, _ in distances[:survivors_target]]
        eliminated = [player for player, _ in distances[survivors_target:]]

        eliminated.sort(
            key=lambda p: (p.x - self.beacon_pos[0]) ** 2 + (p.y - self.beacon_pos[1]) ** 2,
            reverse=True,
        )

        placement = alive_count
        for player in eliminated:
            player.eliminate(placement, self.game_time)
            placement -= 1

        self.last_eliminated = len(eliminated)

        if len(survivors) <= 1:
            self._finish_game()

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
            "beacon_pos": self.beacon_pos,
            "elapsed_time": self.game_time,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.active_players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[BeaconBlitzPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "beacon_blitz"
        game_display_name = "Beacon Blitz"
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
