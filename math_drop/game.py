"""
Math Drop game controller.
"""

import random
import time
from typing import List, Tuple

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import MathDropArena
from .player import MathDropPlayer
from .renderer import MathDropRenderer


class MathDropGame(GameTemplate):
    GAME_TITLE = "MATH DROP"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.round_index = 0
        self.round_phase = None
        self.phase_time_left = 0.0
        self.open_choices = []
        self.correct_choice = None
        self.correct_answer = None
        self.answer_options = []
        self.equation_text = ""
        self.last_eliminated = 0

        self.reveal_elapsed = 0.0
        self.reveal_resolved = False
        self.reveal_duration = float(getattr(config, "MATH_DROP_REVEAL_DURATION", 1.2))
        self.reveal_effective_duration = self.reveal_duration

        self.selection_duration = float(getattr(config, "MATH_DROP_SELECTION_DURATION", 6.0))
        self.result_duration = float(getattr(config, "MATH_DROP_RESULT_DURATION", 2.0))

        self.teleport_flash_timer = 0.0
        self.teleport_flash_duration = float(getattr(config, "MATH_DROP_TELEPORT_FLASH_DURATION", 0.35))

        self.game_history = GameHistory()
        self.club_spotlight = None

    def _init_game_components(self):
        self.arena = MathDropArena()
        self.renderer = MathDropRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)
        club_members = load_club_member_set()

        for i, data in enumerate(follower_data):
            position = self._get_starting_position(i, len(follower_data))
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = self._create_player(payload, position)
            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            self.players.append(player)

        self.club_spotlight = select_club_spotlight(self.players)
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _create_player(self, follower_data: dict, position: tuple) -> MathDropPlayer:
        return MathDropPlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        margin = float(getattr(config, "MATH_DROP_PLAYER_RADIUS", 15)) + 6
        return self.arena.get_random_position_in_lower_half(margin=margin)

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
            self._update_reveal(dt)

        if self.teleport_flash_timer > 0:
            self.teleport_flash_timer = max(0.0, self.teleport_flash_timer - dt)

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
        self.open_choices = []
        self.last_eliminated = 0
        self.reveal_elapsed = 0.0
        self.reveal_resolved = False

        self._teleport_survivors_to_lower_half(alive_players)
        self._generate_round_equation()
        self._assign_choices_for_round(alive_players)

    def _start_result_phase(self):
        alive_players = [p for p in self.players if p.alive]
        if len(alive_players) <= 1:
            self._finish_game()
            return

        self.round_phase = "result"
        self.phase_time_left = self.result_duration

        self._ensure_non_empty_choices(alive_players)
        self.open_choices = []
        self.last_eliminated = 0
        self.reveal_elapsed = 0.0
        self.reveal_resolved = False
        self.reveal_effective_duration = min(
            self.reveal_duration,
            max(0.2, self.result_duration * 0.9),
        )

    def _assign_choices_for_round(self, alive_players: List[MathDropPlayer]):
        choices = list(self.arena.get_choices())
        random.shuffle(alive_players)

        correct_choice = self.correct_choice if self.correct_choice in choices else random.choice(choices)
        incorrect_choices = [choice for choice in choices if choice != correct_choice]
        correct_prob = self._get_correct_probability()

        for player in alive_players:
            if random.random() < correct_prob:
                player.assign_choice(correct_choice, self.arena)
            else:
                player.assign_choice(random.choice(incorrect_choices), self.arena)

        # Guarantee at least one correct answer.
        if not any(player.choice == correct_choice for player in alive_players):
            mover = random.choice(alive_players)
            mover.assign_choice(correct_choice, self.arena)

        self._ensure_non_empty_choices(alive_players)

    def _ensure_non_empty_choices(self, alive_players: List[MathDropPlayer]):
        if len(alive_players) < 3:
            return

        choices = list(self.arena.get_choices())
        choice_players = {choice: [] for choice in choices}
        for player in alive_players:
            choice_players.get(player.choice, choice_players[choices[0]]).append(player)

        empty_choices = [choice for choice, players in choice_players.items() if not players]
        if not empty_choices:
            return

        def move_player(source_choice: int, target_choice: int):
            mover = random.choice(choice_players[source_choice])
            choice_players[source_choice].remove(mover)
            choice_players[target_choice].append(mover)
            mover.assign_choice(target_choice, self.arena)
            new_x, new_y = self.arena.get_random_position_in_choice(
                target_choice,
                margin=mover.radius + 4,
            )
            mover.x = new_x
            mover.y = new_y
            mover.vx = 0.0
            mover.vy = 0.0

        for empty_choice in empty_choices:
            populated = [choice for choice in choices if choice_players[choice]]
            if not populated:
                return

            sources = [choice for choice in populated if len(choice_players[choice]) > 1]
            if self.correct_choice in sources and len(choice_players[self.correct_choice]) <= 1:
                sources = [choice for choice in sources if choice != self.correct_choice]
            if not sources:
                sources = populated

            source_choice = max(sources, key=lambda c: len(choice_players[c]))
            move_player(source_choice, empty_choice)

        # Ensure correct choice still has at least one player.
        if self.correct_choice in choices and not choice_players.get(self.correct_choice):
            sources = [choice for choice in choices if choice_players.get(choice)]
            if sources:
                source_choice = max(sources, key=lambda c: len(choice_players[c]))
                move_player(source_choice, self.correct_choice)

    def _update_reveal(self, dt: float):
        if self.reveal_resolved:
            return
        self.reveal_elapsed += dt
        if self.reveal_elapsed >= self.reveal_effective_duration:
            alive_players = [p for p in self.players if p.alive]
            self._resolve_drop(alive_players)

    def _resolve_drop(self, alive_players: List[MathDropPlayer]):
        if self.reveal_resolved:
            return
        if len(alive_players) <= 1:
            self.reveal_resolved = True
            return

        choices = list(self.arena.get_choices())
        if self.correct_choice is None or self.correct_choice not in choices:
            self.correct_choice = self._choose_correct_choice(alive_players)

        self.open_choices = [choice for choice in choices if choice != self.correct_choice]
        self.last_eliminated = self._eliminate_choices(self.open_choices, alive_players)
        self.reveal_resolved = True

    def _choose_correct_choice(self, alive_players: List[MathDropPlayer]) -> int:
        counts = {choice: 0 for choice in self.arena.get_choices()}
        for player in alive_players:
            if player.choice in counts:
                counts[player.choice] += 1

        non_empty = [choice for choice, count in counts.items() if count > 0]
        if not non_empty:
            return random.choice(self.arena.get_choices())
        return random.choice(non_empty)

    def _eliminate_choices(self, choices: List[int], alive_players: List[MathDropPlayer]) -> int:
        eliminated = [player for player in alive_players if player.choice in choices]
        if not eliminated:
            return 0

        random.shuffle(eliminated)
        placement = len(alive_players)
        for player in eliminated:
            player.start_fall(placement, self.game_time)
            placement -= 1

        return len(eliminated)

    def _end_result_phase(self):
        alive_players = [p for p in self.players if p.alive]
        if not self.reveal_resolved:
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
            "open_choices": self.open_choices,
            "correct_choice": self.correct_choice,
            "correct_answer": self.correct_answer,
            "answer_options": self.answer_options,
            "equation_text": self.equation_text,
            "reveal_elapsed": self.reveal_elapsed,
            "reveal_duration": self.reveal_effective_duration,
            "reveal_resolved": self.reveal_resolved,
            "teleport_flash_alpha": self._get_teleport_flash_alpha(),
            "teleport_text": getattr(config, "MATH_DROP_TELEPORT_TEXT", ""),
            "alive_count": alive_count,
            "total_count": len(self.players),
            "last_eliminated": self.last_eliminated,
            "arena": self.arena,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _generate_round_equation(self):
        equation_text, correct_answer, result_min, result_max = self._generate_equation()
        answers, correct_choice = self._generate_answer_options(correct_answer, result_min, result_max)

        self.equation_text = equation_text
        self.correct_answer = correct_answer
        self.answer_options = answers
        self.correct_choice = correct_choice

    def _get_teleport_flash_alpha(self) -> float:
        if self.teleport_flash_duration <= 0:
            return 0.0
        return max(0.0, min(1.0, self.teleport_flash_timer / self.teleport_flash_duration))

    def _teleport_survivors_to_lower_half(self, alive_players: List[MathDropPlayer]):
        margin = float(getattr(config, "MATH_DROP_PLAYER_RADIUS", 15)) + 6
        for player in alive_players:
            player.choice = None
            player.vx = 0.0
            player.vy = 0.0
            x, y = self.arena.get_random_position_in_lower_half(margin=margin)
            player.x = x
            player.y = y
        self.teleport_flash_timer = self.teleport_flash_duration

    def _generate_equation(self) -> Tuple[str, int, int, int]:
        operators = getattr(config, "MATH_DROP_OPERATORS", ["+", "-", "*"])
        if isinstance(operators, str):
            operators = [op for op in operators if op.strip()]

        min_val = int(getattr(config, "MATH_DROP_OPERAND_MIN", 1))
        max_val = int(getattr(config, "MATH_DROP_OPERAND_MAX", 20))
        result_min = int(getattr(config, "MATH_DROP_RESULT_MIN", 0))
        result_max = int(getattr(config, "MATH_DROP_RESULT_MAX", 99))
        allow_negative = bool(getattr(config, "MATH_DROP_ALLOW_NEGATIVE", False))

        difficulty = max(0, self.round_index - 1)
        min_val = max(1, int(min_val + difficulty * 2))
        if self.round_index <= 3:
            max_val = min(max_val, 9)
        else:
            max_val = int(max_val + difficulty * 8)
        result_max = int(result_max + difficulty * 80)

        if self.round_index >= 3 and "*" not in operators:
            operators = operators + ["*"]
        if self.round_index >= 5 and "/" not in operators:
            operators = operators + ["/"]

        terms = 3
        precedence = {"+": 1, "-": 1, "*": 2, "/": 2}

        def apply_op(a: int, op: str, b: int):
            if op == "+":
                return a + b, True
            if op == "-":
                res = a - b
                if not allow_negative and res < 0:
                    return 0, False
                return res, True
            if op == "*":
                return a * b, True
            if op == "/":
                if b == 0 or a % b != 0:
                    return 0, False
                return a // b, True
            return 0, False

        def evaluate_three_terms(a: int, op1: str, b: int, op2: str, c: int):
            # Enforce order of operations:
            # * and / are evaluated before + and -.
            if precedence.get(op2, 0) > precedence.get(op1, 0):
                right, ok = apply_op(b, op2, c)
                if not ok:
                    return 0, False
                return apply_op(a, op1, right)

            left, ok = apply_op(a, op1, b)
            if not ok:
                return 0, False
            return apply_op(left, op2, c)

        for _ in range(400):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, max_val)
            op1 = random.choice(operators)

            res1, ok = apply_op(a, op1, b)
            if not ok:
                continue

            if terms == 2:
                result = res1
                equation = f"{a} {op1} {b} = ?"
            else:
                c = random.randint(min_val, max_val)
                op2 = random.choice(operators)
                res2, ok = evaluate_three_terms(a, op1, b, op2, c)
                if not ok:
                    continue
                result = res2
                equation = f"{a} {op1} {b} {op2} {c} = ?"

            if not allow_negative and result < 0:
                continue
            if result < result_min or result > result_max:
                continue

            return equation, result, result_min, result_max

        fallback = random.randint(result_min, result_max)
        return f"{fallback} + 0 = ?", fallback, result_min, result_max

    def _get_correct_probability(self) -> float:
        probs = getattr(config, "MATH_DROP_CORRECT_PROB_BY_ROUND", None)
        floor = float(getattr(config, "MATH_DROP_CORRECT_PROB_FLOOR", 0.05))
        if isinstance(probs, (list, tuple)) and probs:
            index = max(0, self.round_index - 1)
            if index < len(probs):
                return max(floor, float(probs[index]))
            return max(floor, float(probs[-1]))
        return max(floor, 0.5)

    def _generate_answer_options(
        self,
        correct_answer: int,
        result_min: int,
        result_max: int,
    ) -> Tuple[List[int], int]:
        options = {correct_answer}
        attempts = 0

        while len(options) < 3 and attempts < 60:
            span = max(2, int(abs(correct_answer) * 0.3) + 2)
            delta = random.randint(1, span)
            candidate = correct_answer + random.choice([-1, 1]) * delta
            if result_min <= candidate <= result_max:
                options.add(candidate)
            attempts += 1

        while len(options) < 3:
            candidate = random.randint(result_min, result_max)
            if candidate not in options:
                options.add(candidate)

        options_list = list(options)
        random.shuffle(options_list)
        correct_choice = options_list.index(correct_answer)
        return options_list, correct_choice

    def _calculate_and_save_scores(self, sorted_players: List[MathDropPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "math_drop"
        game_display_name = "Math Drop"
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
