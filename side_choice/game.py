"""
Heads/Tails game controller.
"""

import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import SideChoiceArena
from .player import SideChoicePlayer
from .renderer import SideChoiceRenderer


class SideChoiceGame(GameTemplate):
    GAME_TITLE = "HEADS / TAILS"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.open_side = None
        self.last_eliminated = 0
        self.pending_drop_side = None
        self.coin_flip_elapsed = 0.0
        self.coin_flip_resolved = False
        self.coin_flip_duration = float(getattr(config, "SIDE_CHOICE_COIN_FLIP_DURATION", 1.2))
        self.coin_flip_effective_duration = self.coin_flip_duration

        self.selection_duration = float(getattr(config, "SIDE_CHOICE_SELECTION_DURATION", 6.0))
        self.result_duration = float(getattr(config, "SIDE_CHOICE_RESULT_DURATION", 2.0))

        self.update_frame_counter = 0
        self.update_batches_per_frame = getattr(config, "UPDATE_BATCHES_PER_FRAME", 4)

        self.game_history = GameHistory()

    def _init_game_components(self):
        self.arena = SideChoiceArena()
        self.renderer = SideChoiceRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        for i, data in enumerate(follower_data):
            position = self._get_starting_position(i, len(follower_data))
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = self._create_player(payload, position)
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _create_player(self, follower_data: dict, position: tuple) -> SideChoicePlayer:
        return SideChoicePlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        margin = float(getattr(config, "SIDE_CHOICE_PLAYER_RADIUS", 15)) + 6
        return self.arena.get_random_position(margin=margin)

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

        self._update_players(dt)

        if self.round_phase == "result":
            self._update_coin_flip(dt)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            if self.round_phase == "selection":
                self._start_result_phase()
            elif self.round_phase == "result":
                self._end_result_phase()

    def _update_players(self, dt: float):
        alive_players = [p for p in self.players if p.alive]
        falling_players = [p for p in self.players if p.falling]

        for player in alive_players:
            player.update(dt, self.arena, self.round_phase)

        for player in falling_players:
            player.update(dt, self.arena, self.round_phase)

    def _start_selection_round(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_index += 1
        self.round_phase = "selection"
        self.phase_time_left = self.selection_duration
        self.open_side = None
        self.last_eliminated = 0
        self.pending_drop_side = None
        self.coin_flip_elapsed = 0.0
        self.coin_flip_resolved = False

        self._assign_sides_for_round(alive_players)

    def _start_result_phase(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_phase = "result"
        self.phase_time_left = self.result_duration

        self._ensure_non_empty_sides(alive_players)
        self.pending_drop_side = self._choose_drop_side(alive_players)
        self.open_side = None
        self.last_eliminated = 0
        self.coin_flip_elapsed = 0.0
        self.coin_flip_resolved = False
        self.coin_flip_effective_duration = min(
            self.coin_flip_duration,
            max(0.2, self.result_duration * 0.9),
        )

    def _assign_sides_for_round(self, alive_players: List[SideChoicePlayer]):
        sides = list(self.arena.get_sides())
        random.shuffle(sides)
        random.shuffle(alive_players)

        if len(alive_players) >= 2:
            alive_players[0].assign_side(sides[0], self.arena)
            alive_players[1].assign_side(sides[1], self.arena)
            for player in alive_players[2:]:
                player.assign_side(random.choice(sides), self.arena)
        else:
            for player in alive_players:
                player.assign_side(random.choice(sides), self.arena)

    def _ensure_non_empty_sides(self, alive_players: List[SideChoicePlayer]):
        if len(alive_players) < 2:
            return

        sides = list(self.arena.get_sides())
        side_players = {side: [] for side in sides}
        for player in alive_players:
            side_players[self.arena.get_side(player.x, player.y)].append(player)

        empty_sides = [side for side in sides if not side_players[side]]
        if not empty_sides:
            return

        for empty_side in empty_sides:
            populated_sides = [side for side in sides if side_players[side]]
            if not populated_sides:
                return
            source_side = max(populated_sides, key=lambda s: len(side_players[s]))
            mover = random.choice(side_players[source_side])
            side_players[source_side].remove(mover)
            side_players[empty_side].append(mover)

            mover.assign_side(empty_side, self.arena)
            new_x, new_y = self.arena.get_random_position_in_side(
                empty_side,
                margin=mover.radius + 4,
            )
            mover.x = new_x
            mover.y = new_y
            mover.vx = 0.0
            mover.vy = 0.0

    def _update_coin_flip(self, dt: float):
        if self.coin_flip_resolved:
            return
        self.coin_flip_elapsed += dt
        if self.coin_flip_elapsed >= self.coin_flip_effective_duration:
            alive_players = [p for p in self.players if p.alive]
            self._resolve_drop(alive_players)

    def _resolve_drop(self, alive_players: List[SideChoicePlayer]):
        if self.coin_flip_resolved:
            return
        if len(alive_players) <= 1:
            self.coin_flip_resolved = True
            return

        side = self.pending_drop_side or self._choose_drop_side(alive_players)
        self.open_side = side
        self.last_eliminated = self._eliminate_side(side, alive_players)
        self.coin_flip_resolved = True

    def _choose_drop_side(self, alive_players: List[SideChoicePlayer]) -> str:
        counts = {side: 0 for side in self.arena.get_sides()}
        for player in alive_players:
            counts[self.arena.get_side(player.x, player.y)] += 1

        non_empty = [side for side, count in counts.items() if count > 0]
        if not non_empty:
            return random.choice(self.arena.get_sides())
        if len(non_empty) == 1:
            for side in self.arena.get_sides():
                if side not in non_empty:
                    return side
            return non_empty[0]
        return random.choice(non_empty)

    def _eliminate_side(self, side: str, alive_players: List[SideChoicePlayer]) -> int:
        eliminated = [
            player for player in alive_players
            if self.arena.get_side(player.x, player.y) == side
        ]

        placement = len(alive_players)
        for index, player in enumerate(eliminated):
            player.start_fall(placement - index, self.game_time)

        return len(eliminated)

    def _end_result_phase(self):
        alive_players = [p for p in self.players if p.alive]
        if not self.coin_flip_resolved:
            self._resolve_drop(alive_players)
        if len(alive_players) <= 1:
            self._finish_game()
        else:
            self._start_selection_round()

    def _finish_game(self):
        if self.game_over:
            return

        alive_players = [p for p in self.players if p.alive]
        for player in alive_players:
            player.placement = 1
            player.survival_time = self.game_time

        for player in self.players:
            if player.placement is None:
                player.placement = len(self.players)
            if not player.survival_time:
                player.survival_time = player.elimination_time or self.game_time

        sorted_players = sorted(self.players, key=lambda p: p.placement)
        self.finish_game(sorted_players)

        if not any(p.alive for p in self.players):
            self.winner = None

    def render(self):
        alive_count = sum(1 for p in self.players if p.alive)

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index,
            "phase_time_left": max(0.0, self.phase_time_left),
            "open_side": self.open_side,
            "coin_flip_elapsed": self.coin_flip_elapsed,
            "coin_flip_duration": self.coin_flip_effective_duration,
            "coin_flip_resolved": self.coin_flip_resolved,
            "coin_flip_side": self.open_side or self.pending_drop_side,
            "alive_count": alive_count,
            "total_count": len(self.players),
            "last_eliminated": self.last_eliminated,
            "arena": self.arena,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[SideChoicePlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "heads_or_tails"
        game_display_name = "Heads/Tails"
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
            game_history_results.append({
                "username": player.username,
                "placement": placement,
                "points": points,
                "survival_time": player.survival_time,
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
