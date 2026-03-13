"""Club Duel game controller."""

import math
import random
import time
from typing import List, Tuple

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import ClubDuelArena
from .player import ClubDuelPlayer
from .renderer import ClubDuelRenderer


class ClubDuelGame(GameTemplate):
    GAME_TITLE = "CLUB DUEL"
    PLAYER_LABEL = "members"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.duel_pairs: List[Tuple[ClubDuelPlayer, ClubDuelPlayer]] = []
        self.duel_positions = []
        self.last_eliminated = 0
        self.approach_duration = float(getattr(config, "CLUB_DUEL_APPROACH_DURATION", 4.0))
        self.resolve_duration = float(getattr(config, "CLUB_DUEL_RESOLVE_DURATION", 2.0))
        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = ClubDuelArena()
        self.renderer = ClubDuelRenderer(self.screen)

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

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _create_player(self, follower_data: dict, position: tuple) -> ClubDuelPlayer:
        return ClubDuelPlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        margin = max(2.0, config.FOLLOWER_RADIUS + 2)
        return (
            random.uniform(self.arena.left + margin, self.arena.right - margin),
            random.uniform(self.arena.top + margin, self.arena.bottom - margin),
        )

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

        for player in self.players:
            if player.alive:
                player.update(dt, self.arena)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            if self.round_phase == "approach":
                self._resolve_duels()
            elif self.round_phase == "duel":
                self._start_round()

    def _start_round(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        random.shuffle(alive_players)
        pair_count = len(alive_players) // 2
        duel_centers = self.arena.duel_positions(pair_count)
        self.duel_positions = duel_centers
        self.duel_pairs = []
        self.last_eliminated = 0

        offset = float(getattr(config, "CLUB_DUEL_PAIR_OFFSET", 18.0))

        for idx in range(pair_count):
            p1 = alive_players[idx * 2]
            p2 = alive_players[idx * 2 + 1]
            center = duel_centers[idx]
            dx = center[0] - self.arena.center_x
            dy = center[1] - self.arena.center_y
            dist = math.hypot(dx, dy) or 1.0
            tangent_x = -dy / dist
            tangent_y = dx / dist
            p1.assign_target((center[0] + tangent_x * offset, center[1] + tangent_y * offset))
            p2.assign_target((center[0] - tangent_x * offset, center[1] - tangent_y * offset))
            self.duel_pairs.append((p1, p2))

        if len(alive_players) % 2 == 1:
            bye_player = alive_players[-1]
            bye_player.assign_target((self.arena.center_x, self.arena.center_y))

        self.round_index += 1
        self.round_phase = "approach"
        self.phase_time_left = self.approach_duration

    def _resolve_duels(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_phase = "duel"
        self.phase_time_left = self.resolve_duration

        eliminated = []
        for p1, p2 in self.duel_pairs:
            if not p1.alive or not p2.alive:
                continue
            score1 = p1.skill + random.random()
            score2 = p2.skill + random.random()
            loser = p2 if score1 >= score2 else p1
            eliminated.append(loser)

        placement = len(alive_players)
        for player in eliminated:
            player.eliminate(placement, self.game_time)
            placement -= 1

        self.last_eliminated = len(eliminated)

        if len([p for p in self.players if p.alive]) <= 1:
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
        alive_count = sum(1 for p in self.players if p.alive)

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index,
            "phase_time_left": max(0.0, self.phase_time_left),
            "alive_count": alive_count,
            "total_count": len(self.players),
            "last_eliminated": self.last_eliminated,
            "arena": self.arena,
            "duel_positions": list(self.duel_positions),
            "elapsed_time": self.game_time,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[ClubDuelPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "club_duel"
        game_display_name = "Club Duel"
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
