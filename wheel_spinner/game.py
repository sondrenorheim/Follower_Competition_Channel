"""
Wheel Spinner game controller.
"""

import math
import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import WheelSpinnerArena
from .player import WheelSpinnerPlayer
from .renderer import WheelSpinnerRenderer


class WheelSpinnerGame(GameTemplate):
    GAME_TITLE = "WHEEL SPINNER"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        if hasattr(self, "recorder"):
            self.recorder.countdown_audio_path = ""
            self.recorder.greenscreen_video_path = None
            self.recorder.greenscreen_start_frame = None
        self.game_time = 0.0
        self.round_index = 0
        self.char_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0

        self.wheel_angle = float(getattr(config, "WHEEL_SPINNER_START_ANGLE", 0.0))
        self.options = []
        self.winning_option = None
        self.winning_index = None
        self.last_eliminated = 0
        self.selected_sequence = []
        self.username_length_hint = 0
        self.option_weights = []

        self.windup_duration = float(getattr(config, "WHEEL_SPINNER_WINDUP_DURATION", 0.6))
        self.spin_duration = float(getattr(config, "WHEEL_SPINNER_SPIN_DURATION", 3.0))
        self.result_duration = float(getattr(config, "WHEEL_SPINNER_RESULT_DURATION", 1.6))

        windup_deg = float(getattr(config, "WHEEL_SPINNER_WINDUP_ANGLE_DEG", 18.0))
        self.windup_angle = math.radians(windup_deg)
        self.spin_turns_min = int(getattr(config, "WHEEL_SPINNER_SPIN_TURNS_MIN", 4))
        self.spin_turns_max = int(getattr(config, "WHEEL_SPINNER_SPIN_TURNS_MAX", 7))
        if self.spin_turns_max < self.spin_turns_min:
            self.spin_turns_max = self.spin_turns_min
        self.spin_ease_power = float(getattr(config, "WHEEL_SPINNER_SPIN_EASE_POWER", 2.0))
        if self.spin_ease_power < 1.0:
            self.spin_ease_power = 1.0
        self.tail_fraction = float(getattr(config, "WHEEL_SPINNER_TAIL_FRACTION", 0.3))
        if self.tail_fraction < 0.0:
            self.tail_fraction = 0.0
        if self.tail_fraction > 0.9:
            self.tail_fraction = 0.9
        self.tail_power = float(getattr(config, "WHEEL_SPINNER_TAIL_POWER", 4.0))
        if self.tail_power < 1.0:
            self.tail_power = 1.0

        self.pointer_angle = -math.pi / 2

        self.windup_elapsed = 0.0
        self.spin_elapsed = 0.0
        self.windup_start_angle = self.wheel_angle
        self.windup_target_angle = self.wheel_angle
        self.spin_start_angle = self.wheel_angle
        self.spin_target_angle = self.wheel_angle

        self.game_history = GameHistory()

    def run(self):
        self.setup_players()

        self.phase = "playing"
        self.round_phase = None
        self._start_round()

        self.sound.start_background_music()
        self.sound.set_music_volume_high()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            dt = self.clock.tick(config.FPS) / 1000.0

            self.update(dt)
            self.render()

            if self.game_over and self.show_leaderboards:
                if time.time() - self.leaderboard_display_start >= 5.0:
                    self.running = False

        self.cleanup()

    def _init_game_components(self):
        self.arena = WheelSpinnerArena()
        self.renderer = WheelSpinnerRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        center = self.arena.get_center()
        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = self._create_player(payload, center)
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _create_player(self, follower_data: dict, position: tuple) -> WheelSpinnerPlayer:
        return WheelSpinnerPlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        return self.arena.get_center()

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt

        if not self.players:
            self._finish_game()
            return

        if self.round_phase is None:
            self._start_round()
            return

        if self.round_phase == "windup":
            self._update_windup(dt)
        elif self.round_phase == "spin":
            self._update_spin(dt)
        elif self.round_phase == "resolve":
            self.phase_time_left -= dt
            if self.phase_time_left <= 0:
                self._start_round()

    def _start_round(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        max_len = max((len(p.username) for p in alive_players), default=0)
        self.username_length_hint = max_len
        if self.char_index >= max_len:
            self._finish_game(force_random_winner=True)
            return

        self.options = self._build_options(alive_players)
        if not self.options:
            self._finish_game(force_random_winner=True)
            return

        self.round_index += 1
        self.last_eliminated = 0

        self.winning_option = random.choices(self.options, weights=self.option_weights, k=1)[0]
        self.winning_index = self.options.index(self.winning_option)

        self._start_windup()

    def _build_options(self, alive_players: List[WheelSpinnerPlayer]) -> List[str]:
        counts = {}
        for player in alive_players:
            option = player.get_char_at(self.char_index)
            counts[option] = counts.get(option, 0) + 1

        items = list(counts.items())
        random.shuffle(items)
        self.option_weights = [count for _, count in items]
        return [option for option, _ in items]

    def _start_windup(self):
        self.round_phase = "windup"
        self.phase_time_left = self.windup_duration
        self.windup_elapsed = 0.0
        self.windup_start_angle = self.wheel_angle
        self.windup_target_angle = self.wheel_angle - self.windup_angle

    def _update_windup(self, dt: float):
        self.windup_elapsed += dt
        if self.windup_duration <= 0:
            self.wheel_angle = self.windup_target_angle
            self._start_spin()
            return

        progress = max(0.0, min(1.0, self.windup_elapsed / self.windup_duration))
        ease = progress * progress * (3 - 2 * progress)
        self.wheel_angle = self._lerp(self.windup_start_angle, self.windup_target_angle, ease)

        if progress >= 1.0:
            self._start_spin()

    def _start_spin(self):
        self.round_phase = "spin"
        self.phase_time_left = self.spin_duration
        self.spin_elapsed = 0.0
        self.spin_start_angle = self.wheel_angle
        self.spin_target_angle = self._calculate_spin_target_angle()

    def _update_spin(self, dt: float):
        self.spin_elapsed += dt
        if self.spin_duration <= 0:
            self.wheel_angle = self.spin_target_angle
            self._resolve_spin()
            return

        progress = max(0.0, min(1.0, self.spin_elapsed / self.spin_duration))
        ease = self._ease_spin(progress)
        self.wheel_angle = self._lerp(self.spin_start_angle, self.spin_target_angle, ease)

        if progress >= 1.0:
            self._resolve_spin()

    def _calculate_spin_target_angle(self) -> float:
        if not self.options:
            return self.wheel_angle

        slice_angle = (2 * math.pi) / len(self.options)
        base_target = self.pointer_angle - (self.winning_index * slice_angle)

        two_pi = 2 * math.pi
        current = self.wheel_angle
        spins = random.randint(self.spin_turns_min, self.spin_turns_max)
        rotations_needed = max(0, math.ceil((current - base_target) / two_pi))
        total_spins = spins + rotations_needed
        target = base_target + two_pi * total_spins

        return target

    def _resolve_spin(self):
        self.wheel_angle = self.spin_target_angle

        alive_players = [p for p in self.players if p.alive]
        if not alive_players:
            self._finish_game()
            return

        placement = len(alive_players)
        survivors = []
        eliminated = []

        for player in alive_players:
            option = player.get_char_at(self.char_index)
            if option == self.winning_option:
                survivors.append(player)
            else:
                eliminated.append(player)

        for player in eliminated:
            player.eliminate(placement, self.game_time)

        self.last_eliminated = len(eliminated)
        if self.winning_option is not None:
            self.selected_sequence.append(self.winning_option)
        self.char_index += 1

        if len(survivors) <= 1:
            self._finish_game()
            return

        self.round_phase = "resolve"
        self.phase_time_left = self.result_duration

    def _finish_game(self, force_random_winner: bool = False):
        if self.game_over:
            return

        alive_players = [p for p in self.players if p.alive]
        if force_random_winner and len(alive_players) > 1:
            winner = random.choice(alive_players)
            for player in alive_players:
                if player is winner:
                    player.placement = 1
                    player.survival_time = self.game_time
                else:
                    player.eliminate(len(alive_players), self.game_time)
        else:
            for player in alive_players:
                player.placement = 1
                player.survival_time = self.game_time

        total_players = len(self.players)
        for player in self.players:
            if player.placement is None:
                player.placement = total_players
            if not player.survival_time:
                player.survival_time = player.elimination_time or self.game_time

        sorted_players = sorted(self.players, key=lambda p: (p.placement, p.username))
        self.winner = next((p for p in sorted_players if p.placement == 1), None)

        self.game_over = True
        self.phase = "finished"

        self._calculate_and_save_scores(sorted_players)

    def render(self):
        alive_count = sum(1 for p in self.players if p.alive)

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index,
            "char_index": self.char_index,
            "options": self.options,
            "wheel_angle": self.wheel_angle,
            "winning_option": self.winning_option,
            "selected_sequence": list(self.selected_sequence),
            "username_length_hint": self.username_length_hint,
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

    def _calculate_and_save_scores(self, sorted_players: List[WheelSpinnerPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "wheel_spinner"
        game_display_name = "Wheel Spinner"
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

    def _ease_spin(self, progress: float) -> float:
        progress = max(0.0, min(1.0, progress))
        tail_fraction = self.tail_fraction
        if tail_fraction > 0.0:
            tail_start = 1.0 - tail_fraction
            if progress > tail_start:
                tail_progress = (progress - tail_start) / tail_fraction
                progress = tail_start + (tail_progress ** self.tail_power) * tail_fraction
        return 1.0 - pow(1.0 - progress, self.spin_ease_power)

    def _lerp(self, start: float, end: float, t: float) -> float:
        return start + (end - start) * t
