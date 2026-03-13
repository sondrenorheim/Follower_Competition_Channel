import random
import time
from dataclasses import dataclass
from typing import List, Optional

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push

from .arena import SubwayArena
from .player import SubwayFollower
from .renderer import SubwayFollowersRenderer


@dataclass
class SubwayObstacle:
    x: float
    y: float
    width: float
    height: float
    lane_index: int
    lane_span: int
    kind: str
    speed_multiplier: float
    color: tuple
    outline: tuple
    accent: tuple
    target_lane: Optional[int] = None
    lateral_speed: float = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.width / 2), int(self.y), int(self.width), int(self.height))


class SubwayFollowersGame(GameTemplate):
    GAME_TITLE = "SUBWAY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers run every day"
    PLAYER_LABEL = "runners"
    GAME_WIDTH = config.SCREEN_WIDTH
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self):
        super().__init__()

        self.game_time = 0.0
        self.obstacles: List[SubwayObstacle] = []
        self.spawn_timer = 0.0
        self.recent_eliminations = []

        self.game_history = GameHistory()

        self.base_speed = float(getattr(config, "SUBWAY_BASE_SPEED", 180.0))
        self.speed_boost = float(getattr(config, "SUBWAY_SPEED_BOOST", 120.0))
        self.difficulty_ramp = float(getattr(config, "SUBWAY_DIFFICULTY_RAMP", 55.0))
        self.max_game_time = float(getattr(config, "SUBWAY_MAX_GAME_TIME", 90.0))

        self.spawn_interval_min = float(getattr(config, "SUBWAY_SPAWN_INTERVAL_MIN", 0.45))
        self.spawn_interval_max = float(getattr(config, "SUBWAY_SPAWN_INTERVAL_MAX", 0.9))
        self.obstacle_gap_min = float(getattr(config, "SUBWAY_OBSTACLE_GAP_MIN", 140.0))

    def _init_game_components(self):
        self.arena = SubwayArena()
        self.renderer = SubwayFollowersRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        run_top, run_bottom = self._runner_band()

        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]

            lane_index = random.randint(0, self.arena.lane_count - 1)
            x = self.arena.lane_center(lane_index)
            y = random.uniform(run_top, run_bottom)
            player = SubwayFollower(payload, (x, y), lane_index)
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _runner_band(self):
        band = getattr(config, "SUBWAY_RUNNER_Y_RANGE", (0.6, 0.9))
        band_top_ratio = min(0.95, max(0.0, float(band[0])))
        band_bottom_ratio = min(1.0, max(band_top_ratio + 0.05, float(band[1])))
        run_top = self.arena.top + self.arena.height * band_top_ratio
        run_bottom = self.arena.top + self.arena.height * band_bottom_ratio
        return run_top, run_bottom

    def _difficulty(self) -> float:
        if self.difficulty_ramp <= 0:
            return 1.0
        return min(1.0, self.game_time / self.difficulty_ramp)

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        difficulty = self._difficulty()
        speed = self.base_speed + self.speed_boost * difficulty

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn_obstacle(difficulty)
            interval = random.uniform(self.spawn_interval_min, self.spawn_interval_max)
            interval *= 1.0 - 0.35 * difficulty
            self.spawn_timer = max(0.2, interval)

        self._update_obstacles(dt, speed)

        for player in self.players:
            player.update(dt, self.arena, self.obstacles, difficulty)

        for player in self.players:
            if not player.alive:
                continue
            if self._collides_with_obstacle(player):
                player.eliminate()
                player.survival_time = self.game_time
                if player.username:
                    self.recent_eliminations.insert(0, player.username)

        alive_count = sum(1 for p in self.players if p.alive)
        if alive_count <= 1 or self.game_time >= self.max_game_time:
            self._finish_game()

    def _update_obstacles(self, dt: float, speed: float):
        for obstacle in self.obstacles:
            obstacle.y += speed * obstacle.speed_multiplier * dt

            if obstacle.target_lane is not None and obstacle.lateral_speed > 0:
                target_x = self.arena.lane_center(obstacle.target_lane)
                delta = target_x - obstacle.x
                step = obstacle.lateral_speed * dt
                if abs(delta) <= step:
                    obstacle.x = target_x
                    obstacle.target_lane = None
                else:
                    obstacle.x += step if delta > 0 else -step

        self.obstacles = [
            obstacle for obstacle in self.obstacles
            if obstacle.y <= self.arena.bottom + obstacle.height + 20
        ]

    def _spawn_obstacle(self, difficulty: float):
        lane_count = self.arena.lane_count
        lane_width = self.arena.lane_width
        lane_gap = float(getattr(config, "SUBWAY_LANE_GAP", 6))

        kinds = ["train", "barrier", "pole", "tunnel_wall"]
        weights = [0.35, 0.3, 0.2, 0.15]
        kind = random.choices(kinds, weights=weights, k=1)[0]

        lane_span = 1
        if kind == "train" and random.random() < float(getattr(config, "SUBWAY_TRAIN_DOUBLE_CHANCE", 0.25)):
            lane_span = 2

        max_lane = max(0, lane_count - lane_span)
        lane_index = random.randint(0, max_lane)

        if not self._is_spawn_clear(lane_index, lane_span):
            return

        width = max(12.0, lane_width * lane_span - lane_gap)
        height = self._obstacle_height(kind, lane_width)

        left = self.arena.lane_left(lane_index)
        x = left + width / 2
        y = self.arena.top - height - random.uniform(12, 40)

        speed_multiplier = 1.0 + random.uniform(-0.05, 0.15)
        color, outline, accent = self._obstacle_colors(kind)

        obstacle = SubwayObstacle(
            x=x,
            y=y,
            width=width,
            height=height,
            lane_index=lane_index,
            lane_span=lane_span,
            kind=kind,
            speed_multiplier=speed_multiplier,
            color=color,
            outline=outline,
            accent=accent,
        )

        if kind == "train" and lane_span == 1:
            if random.random() < float(getattr(config, "SUBWAY_TRAIN_LATERAL_CHANCE", 0.35)):
                direction = random.choice([-1, 1])
                target_lane = lane_index + direction
                if 0 <= target_lane < lane_count:
                    obstacle.target_lane = target_lane
                    obstacle.lateral_speed = float(getattr(config, "SUBWAY_TRAIN_LATERAL_SPEED", 180.0))

        self.obstacles.append(obstacle)

    def _is_spawn_clear(self, lane_index: int, lane_span: int) -> bool:
        for obstacle in self.obstacles:
            if not self._lanes_overlap(lane_index, lane_span, obstacle.lane_index, obstacle.lane_span):
                continue
            if obstacle.y < self.arena.top + self.obstacle_gap_min:
                return False
        return True

    def _lanes_overlap(self, start_a: int, span_a: int, start_b: int, span_b: int) -> bool:
        end_a = start_a + max(1, span_a) - 1
        end_b = start_b + max(1, span_b) - 1
        return not (end_a < start_b or end_b < start_a)

    def _obstacle_height(self, kind: str, lane_width: float) -> float:
        if kind == "train":
            return float(getattr(config, "SUBWAY_TRAIN_HEIGHT", lane_width * 2.2))
        if kind == "pole":
            return float(getattr(config, "SUBWAY_POLE_HEIGHT", lane_width * 0.9))
        if kind == "tunnel_wall":
            return float(getattr(config, "SUBWAY_WALL_HEIGHT", lane_width * 1.1))
        return float(getattr(config, "SUBWAY_BARRIER_HEIGHT", lane_width * 0.6))

    def _obstacle_colors(self, kind: str):
        if kind == "train":
            return (
                getattr(config, "SUBWAY_TRAIN_COLOR", (180, 60, 60)),
                getattr(config, "SUBWAY_TRAIN_OUTLINE", (40, 40, 40)),
                getattr(config, "SUBWAY_TRAIN_ACCENT", (240, 210, 110)),
            )
        if kind == "pole":
            return (
                getattr(config, "SUBWAY_POLE_COLOR", (80, 110, 170)),
                getattr(config, "SUBWAY_POLE_OUTLINE", (20, 30, 50)),
                getattr(config, "SUBWAY_POLE_ACCENT", (220, 230, 245)),
            )
        if kind == "tunnel_wall":
            return (
                getattr(config, "SUBWAY_WALL_COLOR", (70, 75, 90)),
                getattr(config, "SUBWAY_WALL_OUTLINE", (25, 25, 30)),
                getattr(config, "SUBWAY_WALL_ACCENT", (120, 130, 150)),
            )
        return (
            getattr(config, "SUBWAY_BARRIER_COLOR", (200, 120, 50)),
            getattr(config, "SUBWAY_BARRIER_OUTLINE", (60, 40, 20)),
            getattr(config, "SUBWAY_BARRIER_ACCENT", (250, 210, 140)),
        )

    def _collides_with_obstacle(self, player: SubwayFollower) -> bool:
        lane_index = self.arena.get_lane_for_x(player.x)
        for obstacle in self.obstacles:
            if not self._lanes_overlap(lane_index, 1, obstacle.lane_index, obstacle.lane_span):
                continue
            rect = obstacle.rect()
            closest_x = max(rect.left, min(player.x, rect.right))
            closest_y = max(rect.top, min(player.y, rect.bottom))
            dx = player.x - closest_x
            dy = player.y - closest_y
            if dx * dx + dy * dy <= player.radius * player.radius:
                return True
        return False

    def _finish_game(self):
        if self.game_over:
            return

        for player in self.players:
            if player.alive and player.survival_time <= 0:
                player.survival_time = self.game_time

        sorted_players = sorted(
            self.players,
            key=lambda p: (
                not p.alive,
                -(getattr(p, "survival_time", 0.0) or 0.0),
                p.username,
            ),
        )

        self.finish_game(sorted_players)

    def render(self):
        alive_count = sum(1 for p in self.players if p.alive)
        difficulty = self._difficulty()
        speed = self.base_speed + self.speed_boost * difficulty

        game_state = {
            "phase": self.phase,
            "obstacles": self.obstacles,
            "alive_count": alive_count,
            "elapsed_time": self.game_time,
            "speed": speed,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[SubwayFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "subway_followers"
        game_display_name = "Subway Followers"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)
            survival_time = getattr(player, "survival_time", 0.0)

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played,
            )

            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=points,
                survival_time=survival_time,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((player.username, placement, points, survival_time))
            game_history_results.append({
                "username": player.username,
                "placement": placement,
                "points": points,
                "survival_time": survival_time,
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
