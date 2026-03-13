import math
import random
import time
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import MiniGolfArena
from .course import MiniGolfCourse
from .player import MiniGolfPlayer
from .renderer import MiniGolfRenderer
from . import numba_sim


class MiniGolfGame(GameTemplate):
    GAME_TITLE = "MINI GOLF"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.game_history = GameHistory()

        self.total_rounds = max(1, int(getattr(config, "MINIGOLF_TOTAL_ROUNDS", 3)))
        self.max_shots = max(1, int(getattr(config, "MINIGOLF_MAX_SHOTS", 10)))
        self.shot_delay = max(0.0, float(getattr(config, "MINIGOLF_SHOT_DELAY", 0.5)))
        self.round_intermission = max(0.0, float(getattr(config, "MINIGOLF_ROUND_INTERMISSION", 0.75)))
        self.elimination_mode = True

        self.stop_speed = max(0.1, float(getattr(config, "MINIGOLF_STOP_SPEED", 6.0)))
        self.friction = float(getattr(config, "MINIGOLF_FRICTION", 0.92))
        self.friction = max(0.0, min(0.999, self.friction))
        self.max_power = max(1.0, float(getattr(config, "MINIGOLF_MAX_SHOT_POWER", 600.0)))
        self.min_power = max(1.0, float(getattr(config, "MINIGOLF_MIN_SHOT_POWER", 120.0)))
        if self.max_power < self.min_power:
            self.max_power = self.min_power
        self.power_scale = max(0.1, float(getattr(config, "MINIGOLF_POWER_SCALE", 5.0)))
        self.power_candidates = max(1, int(getattr(config, "MINIGOLF_POWER_CANDIDATES", 1)))
        self.power_samples = max(0, int(getattr(config, "MINIGOLF_POWER_SAMPLES", 0)))
        self.power_range = float(getattr(config, "MINIGOLF_POWER_RANGE", 0.0))
        self.power_range = max(0.0, min(1.0, self.power_range))
        self.direction_jitter_deg = max(0.0, float(getattr(config, "MINIGOLF_DIRECTION_RANDOMNESS_DEG", 25.0)))
        self.power_jitter = max(0.0, float(getattr(config, "MINIGOLF_POWER_RANDOMNESS", 0.35)))
        self.mistake_chance = float(getattr(config, "MINIGOLF_MISTAKE_CHANCE", 0.2))
        self.mistake_chance = max(0.0, min(1.0, self.mistake_chance))
        self.lookahead_cells = max(1, int(getattr(config, "MINIGOLF_LOOKAHEAD_CELLS", 4)))
        self.direction_candidates = max(
            1, int(getattr(config, "MINIGOLF_DIRECTION_CANDIDATES", 5))
        )
        self.global_angle_samples = max(
            0, int(getattr(config, "MINIGOLF_GLOBAL_ANGLE_SAMPLES", 0))
        )
        self.refine_angle_samples = max(
            0, int(getattr(config, "MINIGOLF_REFINE_ANGLE_SAMPLES", 0))
        )
        self.refine_angle_spread_deg = float(
            getattr(config, "MINIGOLF_REFINE_ANGLE_SPREAD_DEG", 20.0)
        )
        self.refine_power_samples = max(
            0, int(getattr(config, "MINIGOLF_REFINE_POWER_SAMPLES", 0))
        )
        self.bounce_candidates = max(
            0, int(getattr(config, "MINIGOLF_BOUNCE_CANDIDATES", 2))
        )
        self.bounce_lookahead_cells = max(
            self.lookahead_cells,
            int(getattr(config, "MINIGOLF_BOUNCE_LOOKAHEAD_CELLS", self.lookahead_cells))
        )
        self.bounce_wall_scan_radius = max(
            0, int(getattr(config, "MINIGOLF_BOUNCE_WALL_SCAN_RADIUS", 1))
        )
        self.shot_sim_steps = max(1, int(getattr(config, "MINIGOLF_SHOT_SIM_STEPS", 12)))
        self.shot_sim_time = max(0.05, float(getattr(config, "MINIGOLF_SHOT_SIM_TIME", 0.8)))
        self.shot_sim_max_bounces = max(0, int(getattr(config, "MINIGOLF_SHOT_SIM_MAX_BOUNCES", 2)))
        self.hole_radius = max(2.0, float(getattr(config, "MINIGOLF_HOLE_RADIUS", 8.0)))
        self.use_numba = bool(getattr(config, "MINIGOLF_USE_NUMBA", True)) and numba_sim.NUMBA_AVAILABLE

        self.round_index = 0
        self.shot_cycle = 0
        self.round_state = "active"
        self.round_timer = 0.0
        self.shot_timer = 0.0
        self.finishers = []

        self.course = None
        self.hole_center = (0.0, 0.0)
        self.player_size = float(getattr(config, "MINIGOLF_PLAYER_SIZE", 12))

        self.active_players = []
        self.pending_finish = False
        self.sudden_death = False
        self._numba_cache = None
        self.moving_count = 0
        self.finished_count = 0
        self.next_shot_in = None
        self.leader_name = None
        self.club_spotlight = None

    def _init_game_components(self):
        self.arena = MiniGolfArena()
        self.renderer = MiniGolfRenderer(self.screen)

    def _create_course(self, round_index: int):
        arena_rect = self.arena.get_rect()
        cell_size = int(getattr(config, "MINIGOLF_CELL_SIZE", 25))
        seed_base = int(getattr(config, "DAY_NUMBER", 1))
        seed = seed_base * 100 + (round_index + 1) * 7
        self.course = MiniGolfCourse(arena_rect, cell_size, seed)
        self.hole_center = self.course.cell_center(self.course.hole_cell)
        if self.use_numba:
            self._numba_cache = numba_sim.build_course_cache(self.course, self._wall_padding())
        else:
            self._numba_cache = None

        if not self.players:
            wall_thickness = int(getattr(config, "MINIGOLF_WALL_THICKNESS", 3))
            corridor_size = max(6, cell_size - wall_thickness)
            self.player_size = min(self.player_size, float(corridor_size - 2))

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        seed = int(getattr(config, "DAY_NUMBER", 1))
        club_members = load_club_member_set()

        self._create_course(0)
        start_pos = self.course.cell_center(self.course.start_cell)

        for i, data in enumerate(follower_data):
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = MiniGolfPlayer(
                payload,
                start_pos,
                rng_seed=seed + i + 1,
                size=self.player_size,
            )
            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            player.eliminated = False
            player.rounds_completed = 0
            self.players.append(player)

        self.club_spotlight = select_club_spotlight(self.players)
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

        self.active_players = list(self.players)
        self._start_round(0, regenerate_course=False)

    def _start_round(self, round_index: int, regenerate_course: bool = True):
        self.round_index = round_index
        if regenerate_course or self.course is None:
            self._create_course(round_index)
        start_pos = self.course.cell_center(self.course.start_cell)

        for player in self.active_players:
            player.reset_for_round(start_pos)

        self.finishers = []
        self.shot_cycle = 0
        self.round_state = "active"
        self.round_timer = 0.0
        self.shot_timer = 0.0
        self.next_shot_in = None
        self.pending_finish = False
        self.sudden_death = False
        self.moving_count = 0
        self.finished_count = 0

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt

        if self.round_state == "intermission":
            self.round_timer += dt
            if self.round_timer >= self.round_intermission:
                if self.pending_finish:
                    self._finish_game()
                else:
                    self._start_round(self.round_index + 1)
            return

        active_players = self.active_players
        if not active_players:
            self.pending_finish = True
            self._finish_game()
            return

        moving_count = 0
        finished_count = 0

        for player in active_players:
            if player.eliminated:
                continue
            if player.finished:
                finished_count += 1
                continue
            player.update(dt, self.course, self.friction, self.stop_speed,
                          self.hole_center, self.hole_radius)
            if player.finished:
                self._record_finisher(player)
                finished_count += 1
            elif player.is_moving(self.stop_speed):
                moving_count += 1

        self.moving_count = moving_count
        self.finished_count = finished_count
        self.leader_name = self._get_leader_name()

        active_count = len(active_players)
        if finished_count >= active_count:
            self._end_round()
            return

        if moving_count == 0:
            if not self.sudden_death and self.shot_cycle >= self.max_shots:
                if finished_count == 0:
                    self.sudden_death = True
                else:
                    self._end_round()
                    return

            if self.sudden_death and finished_count > 0:
                self._end_round()
                return

            allow_shots = self.sudden_death or self.shot_cycle < self.max_shots
            if not allow_shots:
                self._end_round()
                return

            self.shot_timer += dt
            self.next_shot_in = max(0.0, self.shot_delay - self.shot_timer)
            if self.shot_timer >= self.shot_delay:
                self._fire_shot()
                self.shot_timer = 0.0
                self.next_shot_in = None
        else:
            self.shot_timer = 0.0
            self.next_shot_in = None

    def _fire_shot(self):
        self.shot_cycle += 1

        for player in self.active_players:
            if player.eliminated or player.finished:
                continue

            cell = self.course.world_to_cell(player.x, player.y)
            target_cell = self.course.get_line_of_sight_target(cell, self.lookahead_cells)
            path_target_cell = self.course.get_lookahead_cell(cell, self.bounce_lookahead_cells)

            if target_cell is None:
                target_cell = self.course.hole_cell
            if path_target_cell is None:
                path_target_cell = target_cell

            base_target_x, base_target_y = self.course.cell_center(target_cell)
            base_dx = base_target_x - player.x
            base_dy = base_target_y - player.y
            if abs(base_dx) < 1e-4 and abs(base_dy) < 1e-4:
                base_dx = self.hole_center[0] - player.x
                base_dy = self.hole_center[1] - player.y
            base_angle = math.atan2(base_dy, base_dx)

            base_distance = math.hypot(base_dx, base_dy)
            path_target_x, path_target_y = self.course.cell_center(path_target_cell)
            path_dx = path_target_x - player.x
            path_dy = path_target_y - player.y
            if abs(path_dx) < 1e-4 and abs(path_dy) < 1e-4:
                path_dx = base_dx
                path_dy = base_dy
            path_angle = math.atan2(path_dy, path_dx)
            path_distance = math.hypot(path_dx, path_dy)

            power_distance = max(base_distance, path_distance)
            base_power = power_distance * self.power_scale
            base_power = max(self.min_power, min(self.max_power, base_power))
            candidate_powers = self._get_power_candidates(base_power)

            hole_dx = self.hole_center[0] - player.x
            hole_dy = self.hole_center[1] - player.y
            hole_angle = math.atan2(hole_dy, hole_dx)

            candidate_angles = [base_angle, path_angle, hole_angle]
            candidate_angles.extend(self._get_global_angle_candidates())

            if self.bounce_candidates > 0:
                bounce_angles = self._get_bounce_angles(
                    player,
                    (path_target_x, path_target_y),
                    cell,
                    path_target_cell,
                )
                if bounce_angles:
                    bounce_angles.sort(key=lambda a: self._angle_delta(a, path_angle))
                    candidate_angles.extend(bounce_angles[:self.bounce_candidates])

            best_choice = self._evaluate_shot_candidates(
                player,
                candidate_angles,
                candidate_powers,
                base_angle,
                base_power,
            )

            if best_choice is None:
                continue

            if self.refine_angle_samples > 0:
                refine_angles = self._get_refined_angles(best_choice[1])
                refine_powers = self._get_refined_power_candidates(best_choice[2])
                refined = self._evaluate_shot_candidates(
                    player,
                    refine_angles,
                    refine_powers,
                    base_angle,
                    base_power,
                )
                if refined is not None and refined[0] < best_choice[0]:
                    best_choice = refined

            angle = best_choice[1]
            power = best_choice[2]

            jitter_rad = math.radians(self.direction_jitter_deg)
            angle += player.rng.uniform(-jitter_rad, jitter_rad)
            power *= player.rng.uniform(1.0 - self.power_jitter, 1.0 + self.power_jitter)

            if self.mistake_chance > 0.0 and player.rng.random() < self.mistake_chance:
                angle += player.rng.uniform(-jitter_rad * 3.0, jitter_rad * 3.0)
                power *= player.rng.uniform(1.0 - self.power_jitter * 2.0, 1.0 + self.power_jitter * 2.0)

            power = max(self.min_power, min(self.max_power, power))

            player.apply_shot(angle, power)
            player.round_shots += 1
            player.total_shots += 1

    def _get_bounce_angles(self, player: MiniGolfPlayer, target_pos: tuple,
                           start_cell: tuple, target_cell: tuple) -> list:
        course = self.course
        target_x, target_y = target_pos
        if start_cell is None:
            return []

        path_cells = self._get_path_cells(start_cell, target_cell)
        scan_radius = self.bounce_wall_scan_radius
        if scan_radius > 0:
            expanded = set(path_cells)
            for col, row in path_cells:
                for dcol in range(-scan_radius, scan_radius + 1):
                    for drow in range(-scan_radius, scan_radius + 1):
                        ncol = col + dcol
                        nrow = row + drow
                        if 0 <= ncol < course.cols and 0 <= nrow < course.rows:
                            expanded.add((ncol, nrow))
            path_cells = list(expanded)

        angles = []
        segments = self._get_wall_segments_for_cells(path_cells)
        for (x1, y1), (x2, y2) in segments:
            if abs(x1 - x2) < 1e-6:
                wall_x = x1
                mirror_x = 2 * wall_x - target_x
                denom = mirror_x - player.x
                if abs(denom) < 1e-6:
                    continue
                t = (wall_x - player.x) / denom
                if t <= 0.0 or t >= 1.0:
                    continue
                y_hit = player.y + t * (target_y - player.y)
                if y_hit < min(y1, y2) - 0.5 or y_hit > max(y1, y2) + 0.5:
                    continue
                angles.append(math.atan2(target_y - player.y, mirror_x - player.x))
            elif abs(y1 - y2) < 1e-6:
                wall_y = y1
                mirror_y = 2 * wall_y - target_y
                denom = mirror_y - player.y
                if abs(denom) < 1e-6:
                    continue
                t = (wall_y - player.y) / denom
                if t <= 0.0 or t >= 1.0:
                    continue
                x_hit = player.x + t * (target_x - player.x)
                if x_hit < min(x1, x2) - 0.5 or x_hit > max(x1, x2) + 0.5:
                    continue
                angles.append(math.atan2(mirror_y - player.y, target_x - player.x))

        return angles

    def _evaluate_shot_candidates(self, player: MiniGolfPlayer, candidate_angles: list,
                                  candidate_powers: list, base_angle: float,
                                  base_power: float):
        best_choice = None
        angles = self._dedupe_angles(candidate_angles)
        for angle in angles:
            angle_delta = self._angle_delta(angle, base_angle)
            for power in candidate_powers:
                best_dist, final_dist = self._simulate_shot_score(player, angle, power)
                power_delta = abs(power - base_power)
                key = (best_dist, final_dist, power_delta, angle_delta, angle, power)
                if best_choice is None or key < best_choice[0]:
                    best_choice = (key, angle, power)
        return best_choice

    def _dedupe_angles(self, angles: list) -> list:
        unique = []
        seen = set()
        for angle in angles:
            key = round(angle, 6)
            if key in seen:
                continue
            seen.add(key)
            unique.append(angle)
        return unique

    def _get_global_angle_candidates(self) -> list:
        samples = self.global_angle_samples
        if samples <= 0:
            return []
        step = (2 * math.pi) / samples
        return [step * i for i in range(samples)]

    def _get_refined_angles(self, center_angle: float) -> list:
        samples = self.refine_angle_samples
        if samples <= 1:
            return [center_angle]
        spread_rad = math.radians(self.refine_angle_spread_deg)
        if spread_rad <= 0.0:
            return [center_angle]
        step = (2 * spread_rad) / (samples - 1)
        return [center_angle - spread_rad + step * i for i in range(samples)]

    def _get_refined_power_candidates(self, base_power: float) -> list:
        if self.refine_power_samples <= 1:
            return self._get_power_candidates(base_power)
        span = max(0.0, self.max_power - self.min_power)
        if span <= 0.0:
            return [self.min_power]
        samples = self.refine_power_samples
        step = span / (samples - 1)
        candidates = [self.min_power + step * i for i in range(samples)]
        candidates.append(base_power)
        return self._dedupe_powers(candidates)

    def _dedupe_powers(self, candidates: list) -> list:
        unique = []
        seen = set()
        for power in candidates:
            key = round(power, 3)
            if key in seen:
                continue
            seen.add(key)
            unique.append(power)
        return unique

    def _get_power_candidates(self, base_power: float) -> list:
        candidates = [max(self.min_power, min(self.max_power, base_power))]

        if self.power_samples > 1:
            span = max(0.0, self.max_power - self.min_power)
            if span > 0.0:
                step = span / (self.power_samples - 1)
                for i in range(self.power_samples):
                    power = self.min_power + step * i
                    candidates.append(power)
            return self._dedupe_powers(candidates)

        if self.power_candidates <= 1:
            return self._dedupe_powers(candidates)

        sweep_min = max(self.min_power, self.max_power * self.power_range)
        sweep_max = self.max_power
        if sweep_min > sweep_max:
            sweep_min = sweep_max

        steps = self.power_candidates - 1
        if steps == 1:
            candidates.append(sweep_max)
            return self._dedupe_powers(candidates)

        step_size = (sweep_max - sweep_min) / (steps - 1) if steps > 1 else 0.0
        for i in range(steps):
            power = sweep_min + step_size * i
            power = max(self.min_power, min(self.max_power, power))
            candidates.append(power)

        return self._dedupe_powers(candidates)

    def _get_path_cells(self, start_cell: tuple, target_cell: tuple) -> list:
        course = self.course
        cells = []
        current = start_cell
        steps = max(1, int(self.bounce_lookahead_cells))
        for _ in range(steps + 1):
            cells.append(current)
            if target_cell is not None and current == target_cell:
                break
            next_cell = course.get_best_neighbor(current)
            if next_cell is None or next_cell == current:
                break
            current = next_cell
        return cells

    def _get_wall_segments_for_cells(self, cells: list) -> list:
        course = self.course
        seen = set()
        segments = []
        for col, row in cells:
            if not (0 <= col < course.cols and 0 <= row < course.rows):
                continue
            left, top, right, bottom = course.cell_bounds((col, row))
            walls = course.walls[row][col]
            if walls["N"]:
                segment = ((left, top), (right, top))
                if segment not in seen:
                    seen.add(segment)
                    segments.append(segment)
            if walls["S"]:
                segment = ((left, bottom), (right, bottom))
                if segment not in seen:
                    seen.add(segment)
                    segments.append(segment)
            if walls["W"]:
                segment = ((left, top), (left, bottom))
                if segment not in seen:
                    seen.add(segment)
                    segments.append(segment)
            if walls["E"]:
                segment = ((right, top), (right, bottom))
                if segment not in seen:
                    seen.add(segment)
                    segments.append(segment)
        return segments

    def _angle_delta(self, angle: float, target: float) -> float:
        return abs((angle - target + math.pi) % (2 * math.pi) - math.pi)

    def _simulate_shot_score(self, player: MiniGolfPlayer, angle: float, power: float) -> tuple:
        if self.use_numba and self._numba_cache is not None:
            cache = self._numba_cache
            radius = float(getattr(player, "radius", self.player_size * 0.5))
            return numba_sim.simulate_shot_score_numba(
                float(player.x),
                float(player.y),
                float(angle),
                float(power),
                radius,
                float(self.stop_speed),
                float(self.friction),
                int(self.shot_sim_steps),
                float(self.shot_sim_time),
                int(self.shot_sim_max_bounces),
                float(cache["origin_x"]),
                float(cache["origin_y"]),
                float(cache["cell_size"]),
                int(cache["cols"]),
                int(cache["rows"]),
                float(cache["width"]),
                float(cache["height"]),
                float(cache["padding"]),
                cache["walls"],
                cache["dist"],
            )

        course = self.course
        x = float(player.x)
        y = float(player.y)
        vx = math.cos(angle) * power
        vy = math.sin(angle) * power
        radius = float(getattr(player, "radius", self.player_size * 0.5))

        cell = course.world_to_cell(x, y)
        best_dist = course.distance_to_hole.get(cell, float("inf"))
        final_dist = best_dist

        steps = self.shot_sim_steps
        dt = self.shot_sim_time / steps
        decay = self.friction ** (dt * 60.0)
        stop_speed_sq = self.stop_speed * self.stop_speed
        bounce_count = 0

        for _ in range(steps):
            if (vx * vx + vy * vy) <= stop_speed_sq:
                break

            prev_x, prev_y = x, y
            dx = vx * dt
            dy = vy * dt

            if dx != 0.0 and dy != 0.0:
                if self._should_move_x_first_sim(course, x, y, dx, dy, radius):
                    x, y, vx, vy, bounced = self._step_axis_sim(course, x, y, vx, vy, dx, 0.0, prev_x, prev_y, radius)
                    prev_x, prev_y = x, y
                    x, y, vx, vy, bounced2 = self._step_axis_sim(course, x, y, vx, vy, 0.0, dy, prev_x, prev_y, radius)
                    bounced = bounced or bounced2
                else:
                    x, y, vx, vy, bounced = self._step_axis_sim(course, x, y, vx, vy, 0.0, dy, prev_x, prev_y, radius)
                    prev_x, prev_y = x, y
                    x, y, vx, vy, bounced2 = self._step_axis_sim(course, x, y, vx, vy, dx, 0.0, prev_x, prev_y, radius)
                    bounced = bounced or bounced2
            else:
                x, y, vx, vy, bounced = self._step_axis_sim(course, x, y, vx, vy, dx, dy, prev_x, prev_y, radius)

            if bounced:
                bounce_count += 1
                if self.shot_sim_max_bounces > 0 and bounce_count >= self.shot_sim_max_bounces:
                    x, y = course.clamp_position(x, y, radius)
                    cell = course.world_to_cell(x, y)
                    final_dist = course.distance_to_hole.get(cell, float("inf"))
                    if final_dist < best_dist:
                        best_dist = final_dist
                    break

            x, y = course.clamp_position(x, y, radius)
            vx *= decay
            vy *= decay

            cell = course.world_to_cell(x, y)
            final_dist = course.distance_to_hole.get(cell, float("inf"))
            if final_dist < best_dist:
                best_dist = final_dist

        return best_dist, final_dist

    def _step_axis_sim(self, course, x: float, y: float, vx: float, vy: float,
                       dx: float, dy: float, prev_x: float, prev_y: float,
                       radius: float) -> tuple:
        if dx == 0.0 and dy == 0.0:
            return x, y, vx, vy, False

        x += dx
        y += dy
        x, y, vx, vy, bounced = self._resolve_wall_collisions_sim(
            course, x, y, vx, vy, prev_x, prev_y, radius
        )
        return x, y, vx, vy, bounced

    def _should_move_x_first_sim(self, course, x: float, y: float,
                                 dx: float, dy: float, radius: float) -> bool:
        if dx == 0.0:
            return False
        if dy == 0.0:
            return True

        col, row = course.world_to_cell(x, y)
        left, top, right, bottom = course.cell_bounds((col, row))
        padding = self._wall_padding()
        walls = course.walls[row][col]

        if dx > 0.0:
            x_limit = right - padding - radius if walls["E"] else right
        else:
            x_limit = left + padding + radius if walls["W"] else left
        if dy > 0.0:
            y_limit = bottom - padding - radius if walls["S"] else bottom
        else:
            y_limit = top + padding + radius if walls["N"] else top

        tx = (x_limit - x) / dx
        ty = (y_limit - y) / dy
        if tx < 0.0:
            tx = 0.0
        if ty < 0.0:
            ty = 0.0
        return tx <= ty

    def _resolve_wall_collisions_sim(self, course, x: float, y: float,
                                     vx: float, vy: float,
                                     prev_x: float, prev_y: float,
                                     radius: float) -> tuple:
        padding = self._wall_padding()
        prev_col, prev_row = course.world_to_cell(prev_x, prev_y)
        col, row = course.world_to_cell(x, y)
        bounced = False

        if col > prev_col:
            if course.walls[prev_row][prev_col]["E"]:
                boundary = course.cell_bounds((prev_col, prev_row))[2] - padding
                x = boundary - radius
                vx = -abs(vx)
                bounced = True
                col = prev_col
        elif col < prev_col:
            if course.walls[prev_row][prev_col]["W"]:
                boundary = course.cell_bounds((prev_col, prev_row))[0] + padding
                x = boundary + radius
                vx = abs(vx)
                bounced = True
                col = prev_col

        if row > prev_row:
            if course.walls[prev_row][prev_col]["S"]:
                boundary = course.cell_bounds((prev_col, prev_row))[3] - padding
                y = boundary - radius
                vy = -abs(vy)
                bounced = True
                row = prev_row
        elif row < prev_row:
            if course.walls[prev_row][prev_col]["N"]:
                boundary = course.cell_bounds((prev_col, prev_row))[1] + padding
                y = boundary + radius
                vy = abs(vy)
                bounced = True
                row = prev_row

        col, row = course.world_to_cell(x, y)
        left, top, right, bottom = course.cell_bounds((col, row))
        walls = course.walls[row][col]

        if walls["W"] and x - radius < left + padding:
            x = left + padding + radius
            vx = abs(vx)
            bounced = True
        if walls["E"] and x + radius > right - padding:
            x = right - padding - radius
            vx = -abs(vx)
            bounced = True
        if walls["N"] and y - radius < top + padding:
            y = top + padding + radius
            vy = abs(vy)
            bounced = True
        if walls["S"] and y + radius > bottom - padding:
            y = bottom - padding - radius
            vy = -abs(vy)
            bounced = True

        if bounced:
            vx *= 0.9
            vy *= 0.9

        return x, y, vx, vy, bounced

    def _wall_padding(self) -> float:
        return max(0.0, float(getattr(config, "MINIGOLF_WALL_THICKNESS", 3)) * 0.45)

    def _end_round(self):
        if self.round_state == "intermission":
            return

        active_players = self.active_players
        if not active_players:
            self.pending_finish = True
            self.round_state = "intermission"
            self.round_timer = 0.0
            self.shot_timer = 0.0
            self.next_shot_in = None
            self.moving_count = 0
            self.finished_count = 0
            return

        finishers = [player for player in active_players if player.finished]
        if not finishers:
            self.sudden_death = True
            self.shot_timer = 0.0
            self.next_shot_in = None
            return

        finisher_set = set(finishers)
        for player in active_players:
            if player in finisher_set:
                player.rounds_completed += 1
                player.vx = 0.0
                player.vy = 0.0
                continue
            player.total_distance_remaining += self._distance_to_hole(player)
            player.vx = 0.0
            player.vy = 0.0
            player.eliminated = True

        self.active_players = finishers
        self.pending_finish = len(self.active_players) <= 1
        if self.pending_finish and self.active_players:
            self.winner = self.active_players[0]

        self.round_state = "intermission"
        self.round_timer = 0.0
        self.shot_timer = 0.0
        self.next_shot_in = None
        self.moving_count = 0
        self.finished_count = len(finishers)

    def _record_finisher(self, player: MiniGolfPlayer):
        self.finishers.insert(0, player.username)

    def _distance_to_hole(self, player: MiniGolfPlayer) -> float:
        return math.hypot(player.x - self.hole_center[0], player.y - self.hole_center[1])

    def _get_leader_name(self):
        leader = None
        leader_key = None
        for player in self.active_players:
            if player.eliminated:
                continue
            distance_now = self._distance_to_hole(player)
            key = (-player.rounds_completed, distance_now, player.username)
            if leader_key is None or key < leader_key:
                leader_key = key
                leader = player
        return leader.username if leader else None

    def _finish_game(self):
        if self.game_over:
            return

        sorted_players = sorted(
            self.players,
            key=lambda p: (-p.rounds_completed, p.username)
        )

        for player in sorted_players:
            player.survival_time = float(player.rounds_completed)

        self.finish_game(sorted_players)

    def finish_game(self, sorted_players: List[MiniGolfPlayer]):
        self.game_over = True
        self.phase = "finished"

        placement = 1
        index = 0
        while index < len(sorted_players):
            group_key = sorted_players[index].rounds_completed
            group_size = 0
            while index < len(sorted_players) and sorted_players[index].rounds_completed == group_key:
                sorted_players[index].placement = placement
                index += 1
                group_size += 1
            placement += group_size

        if sorted_players and self.winner is None:
            self.winner = sorted_players[0]

        print("\n" + "=" * 60)
        print("  GAME COMPLETE")
        print("=" * 60)

        print("\nTop 10:")
        for i, player in enumerate(sorted_players[:10]):
            print(f"{player.placement}. {player.username}")

        self._calculate_and_save_scores(sorted_players)

    def render(self):
        game_state = {
            "phase": self.phase,
            "course": self.course,
            "round_number": self.round_index + 1,
            "total_rounds": self.total_rounds,
            "shot_number": self.shot_cycle,
            "max_shots": self.max_shots,
            "finished_count": self.finished_count,
            "active_count": len(self.active_players),
            "moving_count": self.moving_count,
            "next_shot_in": self.next_shot_in,
            "leader_name": self.leader_name,
            "round_state": self.round_state,
            "recent_finishers": self.finishers,
            "elimination_mode": self.elimination_mode,
            "sudden_death": self.sudden_death,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[MiniGolfPlayer]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "mini_golf"
        game_display_name = "Mini Golf"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement
            if total_participants <= 1:
                percentile = 1.0
            else:
                percentile = (total_participants - placement) / (total_participants - 1)

            points = round(self.scoring.MAX_POINTS * max(0.0, min(1.0, percentile)), 2)
            rounds_survived = float(player.rounds_completed)

            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=points,
                survival_time=rounds_survived,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((player.username, placement, points, rounds_survived))
            game_history_results.append({
                "username": player.username,
                "placement": placement,
                "points": points,
                "survival_time": rounds_survived,
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
