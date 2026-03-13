"""Club Relic game controller."""

import math
import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import ClubRelicArena
from .player import ClubRelicPlayer
from .renderer import ClubRelicRenderer


class ClubRelicGame(GameTemplate):
    GAME_TITLE = "RELIC RALLY"
    PLAYER_LABEL = "members"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.relic_pos = None
        self.relic_vel = (0.0, 0.0)
        self.last_eliminated = 0
        self.survival_ratio = float(getattr(config, "CLUB_RELIC_SURVIVAL_RATIO", 0.6))
        self.round_duration = float(getattr(config, "CLUB_RELIC_ROUND_DURATION", 6.0))
        self.relic_speed = float(getattr(config, "CLUB_RELIC_RELIC_SPEED", 60.0))
        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = ClubRelicArena()
        self.renderer = ClubRelicRenderer(self.screen)

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

    def _create_player(self, follower_data: dict, position: tuple) -> ClubRelicPlayer:
        return ClubRelicPlayer(follower_data, position)

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

        self._update_relic(dt)

        for player in self.players:
            if player.alive:
                player.update(dt, self.arena, self.relic_pos)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            self._resolve_round()

    def _start_round(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_index += 1
        self.round_phase = "hunt"
        self.phase_time_left = self.round_duration
        self.last_eliminated = 0

        self.relic_pos = self.arena.get_random_point(margin=20.0)
        angle = random.uniform(0.0, 2 * math.pi)
        self.relic_vel = (
            math.cos(angle) * self.relic_speed,
            math.sin(angle) * self.relic_speed,
        )

    def _update_relic(self, dt: float):
        if not self.relic_pos:
            return
        x, y = self.relic_pos
        vx, vy = self.relic_vel
        x += vx * dt
        y += vy * dt

        margin = float(getattr(config, "CLUB_RELIC_RELIC_RADIUS", 16)) + 6
        if x <= self.arena.left + margin or x >= self.arena.right - margin:
            vx *= -1
            x = max(self.arena.left + margin, min(self.arena.right - margin, x))
        if y <= self.arena.top + margin or y >= self.arena.bottom - margin:
            vy *= -1
            y = max(self.arena.top + margin, min(self.arena.bottom - margin, y))

        self.relic_pos = (x, y)
        self.relic_vel = (vx, vy)

    def _resolve_round(self):
        alive_players = [p for p in self.players if p.alive]
        alive_count = len(alive_players)
        if alive_count <= 1:
            self._finish_game()
            return

        ratio = max(0.05, min(self.survival_ratio, 0.95))
        survivors_target = int(math.ceil(alive_count * ratio))
        survivors_target = max(1, min(alive_count - 1, survivors_target))

        distances = []
        for player in alive_players:
            dx = player.x - self.relic_pos[0]
            dy = player.y - self.relic_pos[1]
            dist = math.hypot(dx, dy)
            distances.append((player, dist))

        distances.sort(key=lambda item: item[1])
        survivors = [player for player, _ in distances[:survivors_target]]
        eliminated = [player for player, _ in distances[survivors_target:]]

        eliminated.sort(
            key=lambda p: (p.x - self.relic_pos[0]) ** 2 + (p.y - self.relic_pos[1]) ** 2,
            reverse=True,
        )

        placement = alive_count
        for player in eliminated:
            player.eliminate(placement, self.game_time)
            placement -= 1

        self.last_eliminated = len(eliminated)

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
            "arena": self.arena,
            "relic_pos": self.relic_pos,
            "elapsed_time": self.game_time,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[ClubRelicPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "club_relic"
        game_display_name = "Relic Rally"
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
