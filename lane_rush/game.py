"""Lane Rush game controller."""

import math
import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import LaneRushArena
from .player import LaneRushPlayer
from .renderer import LaneRushRenderer


class LaneRushGame(GameTemplate):
    GAME_TITLE = "LANE RUSH"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.last_eliminated = 0
        self.boost_lanes = []
        self.survival_ratio = float(getattr(config, "LANE_RUSH_SURVIVAL_RATIO", 0.65))
        self.round_duration = float(getattr(config, "LANE_RUSH_ROUND_DURATION", 7.0))
        self.boost_lane_count = int(getattr(config, "LANE_RUSH_BOOST_LANES", 2))
        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = LaneRushArena()
        self.renderer = LaneRushRenderer(self.screen)

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
            lane_index = i % self.arena.lane_count
            position = self._get_starting_position(lane_index)
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = self._create_player(payload, position, lane_index)
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _create_player(self, follower_data: dict, position: tuple, lane_index: int) -> LaneRushPlayer:
        return LaneRushPlayer(follower_data, position, lane_index)

    def _get_starting_position(self, lane_index: int) -> tuple:
        margin = max(2.0, config.FOLLOWER_RADIUS + 2)
        lane_left, lane_right = self.arena.get_lane_bounds(lane_index, margin=margin)
        x = (lane_left + lane_right) / 2
        y = self.arena.bottom - margin
        return (x, y)

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

        self._update_players(dt)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            self._resolve_round()

    def _update_players(self, dt: float):
        boost_set = set(self.boost_lanes)
        for player in self.players:
            if player.alive:
                player.update(dt, self.arena, player.lane_index in boost_set)

    def _start_round(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_index += 1
        self.round_phase = "dash"
        self.phase_time_left = self.round_duration
        self.last_eliminated = 0

        lane_indices = list(range(self.arena.lane_count))
        random.shuffle(lane_indices)
        count = max(1, min(self.boost_lane_count, self.arena.lane_count))
        self.boost_lanes = lane_indices[:count]

    def _resolve_round(self):
        alive_players = [p for p in self.players if p.alive]
        alive_count = len(alive_players)
        if alive_count <= 1:
            self._finish_game()
            return

        ratio = max(0.05, min(self.survival_ratio, 0.95))
        survivors_target = int(math.ceil(alive_count * ratio))
        survivors_target = max(1, min(alive_count - 1, survivors_target))

        alive_players.sort(key=lambda p: p.progress, reverse=True)
        survivors = alive_players[:survivors_target]
        eliminated = alive_players[survivors_target:]

        eliminated.sort(key=lambda p: p.progress)
        placement = alive_count
        for player in eliminated:
            player.eliminate(placement, self.game_time)
            placement -= 1

        self.last_eliminated = len(eliminated)

        for player in survivors:
            player.progress = max(0.0, min(1.0, player.progress * 0.9))

        if len(survivors) <= 1:
            self._finish_game()
        else:
            self._start_round()

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
        alive_count = sum(1 for p in self.players if p.alive)

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index,
            "phase_time_left": max(0.0, self.phase_time_left),
            "alive_count": alive_count,
            "total_count": len(self.players),
            "last_eliminated": self.last_eliminated,
            "boost_lanes": list(self.boost_lanes),
            "arena": self.arena,
            "elapsed_time": self.game_time,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[LaneRushPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "lane_rush"
        game_display_name = "Lane Rush"
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
