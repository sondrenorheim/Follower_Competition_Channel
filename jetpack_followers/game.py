import random
import time
from dataclasses import dataclass
from typing import List, Optional

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import JetpackArena
from .player import JetpackFollower
from .renderer import JetpackFollowersRenderer


@dataclass
class JetpackObstacle:
    x: float
    y: float
    width: float
    height: float
    sprite_index: int
    speed_multiplier: float
    hitbox_inset_x: float
    hitbox_inset_y: float
    animation_phase: float
    animation_speed: float

    def hitbox_rect(self) -> pygame.Rect:
        left = self.x - self.width * 0.5 + self.hitbox_inset_x
        top = self.y - self.height * 0.5 + self.hitbox_inset_y
        width = max(1.0, self.width - self.hitbox_inset_x * 2.0)
        height = max(1.0, self.height - self.hitbox_inset_y * 2.0)
        return pygame.Rect(int(left), int(top), int(width), int(height))


@dataclass
class JetpackRocket:
    x: float
    y: float
    width: float
    height: float
    target: Optional[JetpackFollower]
    speed_multiplier: float = 1.0
    age: float = 0.0
    warning_active: bool = True

    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.width * 0.5),
            int(self.y - self.height * 0.5),
            max(1, int(self.width)),
            max(1, int(self.height)),
        )


class JetpackFollowersGame(GameTemplate):
    GAME_TITLE = "JETPACK FOLLOWERS"
    GAME_SUBTITLE = "Making my club members jetpack every day"
    PLAYER_LABEL = "club members"

    def __init__(self):
        super().__init__()

        self.game_time = 0.0
        self.world_distance = 0.0
        self.background_scroll = 0.0
        self.current_world_speed = 0.0
        self.obstacles: List[JetpackObstacle] = []
        self.rockets: List[JetpackRocket] = []
        self.recent_eliminations = []
        self.game_history = GameHistory()
        self.club_spotlight = None

        self.player_x_ratio = float(getattr(config, "JETPACK_PLAYER_X_RATIO", 0.32))
        self.player_x_variance = float(getattr(config, "JETPACK_PLAYER_X_VARIANCE", 28.0))
        self.player_x = self.arena.left + self.arena.width * self.player_x_ratio

        self.base_world_speed = float(getattr(config, "JETPACK_WORLD_SPEED", 170.0))
        self.speed_boost = float(getattr(config, "JETPACK_SPEED_BOOST", 95.0))
        self.difficulty_ramp = float(getattr(config, "JETPACK_DIFFICULTY_RAMP", 55.0))
        self.max_game_time = float(getattr(config, "JETPACK_MAX_GAME_TIME", 95.0))
        self.distance_scale = float(getattr(config, "JETPACK_DISTANCE_SCALE", 0.06))
        self.background_scroll_factor = float(getattr(config, "JETPACK_BACKGROUND_SCROLL_FACTOR", 1.2))

        self.obstacle_width = float(getattr(config, "JETPACK_OBSTACLE_WIDTH", 86.0))
        self.obstacle_height_min = float(getattr(config, "JETPACK_OBSTACLE_HEIGHT_MIN", 82.0))
        self.obstacle_height_max = float(getattr(config, "JETPACK_OBSTACLE_HEIGHT_MAX", 210.0))
        self.obstacle_spawn_min = float(getattr(config, "JETPACK_OBSTACLE_SPAWN_MIN", 0.9))
        self.obstacle_spawn_max = float(getattr(config, "JETPACK_OBSTACLE_SPAWN_MAX", 1.45))
        self.obstacle_spawn_offset = float(getattr(config, "JETPACK_OBSTACLE_SPAWN_OFFSET", 140.0))
        self.obstacle_edge_padding = float(getattr(config, "JETPACK_OBSTACLE_EDGE_PADDING", 18.0))
        self.obstacle_hitbox_inset_x = float(getattr(config, "JETPACK_OBSTACLE_HITBOX_INSET_X", 12.0))
        self.obstacle_hitbox_inset_y = float(getattr(config, "JETPACK_OBSTACLE_HITBOX_INSET_Y", 14.0))
        self.double_obstacle_chance = float(getattr(config, "JETPACK_DOUBLE_OBSTACLE_CHANCE", 0.18))
        self.obstacle_pair_x_gap = tuple(getattr(config, "JETPACK_OBSTACLE_PAIR_X_GAP", (120.0, 210.0)))
        self.obstacle_pair_y_gap_max = float(getattr(config, "JETPACK_OBSTACLE_PAIR_Y_GAP_MAX", 180.0))
        self.obstacle_lookahead_mult = float(getattr(config, "JETPACK_OBSTACLE_LOOKAHEAD_MULT", 1.15))
        self.rocket_lookahead_mult = float(getattr(config, "JETPACK_ROCKET_LOOKAHEAD_MULT", 1.05))
        self.zapper_anim_speed_min = float(getattr(config, "JETPACK_ZAPPER_ANIMATION_SPEED_MIN", 0.85))
        self.zapper_anim_speed_max = float(getattr(config, "JETPACK_ZAPPER_ANIMATION_SPEED_MAX", 1.2))

        self.rocket_enabled = bool(getattr(config, "JETPACK_ROCKET_ENABLED", True))
        self.rocket_warmup_time = float(getattr(config, "JETPACK_ROCKET_WARMUP_TIME", 7.0))
        self.rocket_spawn_min = float(getattr(config, "JETPACK_ROCKET_SPAWN_INTERVAL_MIN", 3.0))
        self.rocket_spawn_max = float(getattr(config, "JETPACK_ROCKET_SPAWN_INTERVAL_MAX", 5.2))
        self.rocket_speed = float(getattr(config, "JETPACK_ROCKET_SPEED", 310.0))
        self.rocket_track_speed = float(getattr(config, "JETPACK_ROCKET_TRACK_SPEED", 180.0))
        self.rocket_track_stop_distance = float(getattr(config, "JETPACK_ROCKET_TRACK_STOP_DISTANCE", 80.0))
        self.rocket_width = float(getattr(config, "JETPACK_ROCKET_WIDTH", 68.0))
        self.rocket_height = float(getattr(config, "JETPACK_ROCKET_HEIGHT", 30.0))
        self.rocket_spawn_offset = float(getattr(config, "JETPACK_ROCKET_SPAWN_OFFSET", 220.0))
        self.rocket_max_age = float(getattr(config, "JETPACK_ROCKET_MAX_AGE", 10.0))
        self.rocket_warning_distance = float(getattr(config, "JETPACK_ROCKET_WARNING_DISTANCE", 120.0))
        self.max_recent_eliminations = int(getattr(config, "JETPACK_ELIMINATION_TRACK_LIMIT", 400))

        self.obstacle_spawn_timer = random.uniform(self.obstacle_spawn_min, self.obstacle_spawn_max)
        self.rocket_spawn_timer = random.uniform(self.rocket_spawn_min, self.rocket_spawn_max)

        # Keep export music aligned with Flappy Followers behavior.
        self.sound.background_music_path = str(
            getattr(config, "JETPACK_BACKGROUND_MUSIC_PATH", "assets/Sydney Tour Song adjusted.m4a")
        )
        self.sound.preload_audio()
        self.recorder.background_music_path = self.sound.background_music_path

    def _init_game_components(self):
        self.arena = JetpackArena()
        self.renderer = JetpackFollowersRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)
        club_members = load_club_member_set()

        spawn_top = self.arena.top + 24
        spawn_bottom = self.arena.bottom - 24
        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]

            x = self.player_x + random.uniform(-self.player_x_variance, self.player_x_variance)
            x = max(self.arena.left + 12, min(self.arena.right - 12, x))
            y = random.uniform(spawn_top, spawn_bottom)

            player = JetpackFollower(payload, (x, y))
            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            self.players.append(player)

        self.club_spotlight = select_club_spotlight(self.players)
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _difficulty(self) -> float:
        if self.difficulty_ramp <= 0:
            return 1.0
        # Keep ramping past 1.0 so speed and spawn pressure continue to rise
        # in long rounds until a true last survivor remains.
        return self.game_time / self.difficulty_ramp

    def _next_obstacle_spawn_interval(self, difficulty: float) -> float:
        interval = random.uniform(self.obstacle_spawn_min, self.obstacle_spawn_max)
        interval *= 1.0 - 0.35 * difficulty
        return max(0.22, interval)

    def _next_rocket_spawn_interval(self, difficulty: float) -> float:
        interval = random.uniform(self.rocket_spawn_min, self.rocket_spawn_max)
        interval *= 1.0 - 0.25 * difficulty
        return max(1.2, interval)

    def _spawn_obstacle_at(self, x: float, y: float, width: float, height: float):
        self.obstacles.append(
            JetpackObstacle(
                x=x,
                y=y,
                width=width,
                height=height,
                sprite_index=random.randint(0, 3),
                speed_multiplier=random.uniform(0.92, 1.15),
                hitbox_inset_x=self.obstacle_hitbox_inset_x,
                hitbox_inset_y=self.obstacle_hitbox_inset_y,
                animation_phase=random.random(),
                animation_speed=random.uniform(self.zapper_anim_speed_min, self.zapper_anim_speed_max),
            )
        )

    def _spawn_obstacle(self):
        arena_span = self.arena.height - self.obstacle_edge_padding * 2.0
        if arena_span <= 20:
            return

        height = random.uniform(self.obstacle_height_min, self.obstacle_height_max)
        height = min(height, max(20.0, arena_span))
        width = random.uniform(self.obstacle_width * 0.9, self.obstacle_width * 1.15)

        y_min = self.arena.top + self.obstacle_edge_padding + height * 0.5
        y_max = self.arena.bottom - self.obstacle_edge_padding - height * 0.5
        if y_min >= y_max:
            return

        y = random.uniform(y_min, y_max)
        x = self.arena.right + self.obstacle_spawn_offset
        self._spawn_obstacle_at(x, y, width, height)

        if random.random() < self.double_obstacle_chance:
            gap_min, gap_max = self.obstacle_pair_x_gap if len(self.obstacle_pair_x_gap) == 2 else (120.0, 210.0)
            pair_x = x + random.uniform(float(gap_min), float(gap_max))
            vertical_gap = random.uniform(height * 0.8, self.obstacle_pair_y_gap_max)
            pair_dir = random.choice((-1.0, 1.0))
            pair_y = y + vertical_gap * pair_dir
            pair_y = max(y_min, min(y_max, pair_y))
            pair_height = height * random.uniform(0.8, 1.05)
            self._spawn_obstacle_at(pair_x, pair_y, width, pair_height)

    def _update_obstacles(self, dt: float, difficulty: float):
        for obstacle in self.obstacles:
            obstacle.x -= self.current_world_speed * obstacle.speed_multiplier * dt

        cutoff = self.arena.left - max(120.0, self.obstacle_spawn_offset)
        self.obstacles = [o for o in self.obstacles if o.x + o.width * 0.5 >= cutoff]

        self.obstacle_spawn_timer -= dt
        if self.obstacle_spawn_timer <= 0:
            self._spawn_obstacle()
            self.obstacle_spawn_timer = self._next_obstacle_spawn_interval(difficulty)

    def _spawn_rocket(self):
        alive_players = [p for p in self.players if p.alive]
        if not alive_players:
            return

        target = random.choice(alive_players)
        spawn_y = target.y + random.uniform(-70.0, 70.0)
        spawn_y = self.arena.clamp_y(spawn_y, self.rocket_height * 0.5)
        spawn_x = self.arena.right + self.rocket_spawn_offset

        self.rockets.append(
            JetpackRocket(
                x=spawn_x,
                y=spawn_y,
                width=self.rocket_width,
                height=self.rocket_height,
                target=target,
                speed_multiplier=random.uniform(0.92, 1.2),
                warning_active=True,
            )
        )

    def _update_rockets(self, dt: float, difficulty: float):
        if self.rocket_enabled and self.game_time >= self.rocket_warmup_time:
            self.rocket_spawn_timer -= dt
            if self.rocket_spawn_timer <= 0:
                self._spawn_rocket()
                self.rocket_spawn_timer = self._next_rocket_spawn_interval(difficulty)

        for rocket in self.rockets:
            speed = self.rocket_speed * rocket.speed_multiplier * (1.0 + difficulty * 0.2)
            rocket.x -= speed * dt
            rocket.age += dt

            if (
                rocket.target is not None
                and rocket.target.alive
                and rocket.x > self.player_x + self.rocket_track_stop_distance
            ):
                delta_y = rocket.target.y - rocket.y
                step = self.rocket_track_speed * dt
                if abs(delta_y) <= step:
                    rocket.y = rocket.target.y
                else:
                    rocket.y += step if delta_y > 0 else -step

            rocket.y = self.arena.clamp_y(rocket.y, rocket.height * 0.5)
            rocket.warning_active = rocket.x > self.arena.right - self.rocket_warning_distance

        cutoff = self.arena.left - 180.0
        self.rockets = [
            r for r in self.rockets
            if (r.x + r.width * 0.5 >= cutoff) and (r.age <= self.rocket_max_age)
        ]

    def _find_upcoming_obstacles_for(self, player: JetpackFollower, max_count: int = 3) -> List[JetpackObstacle]:
        lookahead_mult = max(0.5, self.obstacle_lookahead_mult)
        lookahead = float(getattr(player, "reaction_distance", 250.0)) * lookahead_mult
        upcoming = []

        for obstacle in self.obstacles:
            front_x = obstacle.x - obstacle.width * 0.5
            distance = front_x - (player.x + player.radius)
            if distance < -obstacle.width:
                continue
            if distance > lookahead:
                continue
            upcoming.append((distance, obstacle))

        upcoming.sort(key=lambda item: item[0])
        return [item[1] for item in upcoming[:max(1, max_count)]]

    def _find_next_rocket_for(self, player: JetpackFollower) -> Optional[JetpackRocket]:
        reaction_distance = getattr(player, "reaction_distance", 250.0)
        lookahead = reaction_distance * max(0.5, self.rocket_lookahead_mult)
        candidates = [
            rocket for rocket in self.rockets
            if rocket.x + rocket.width * 0.5 >= player.x - 80.0
            and rocket.x <= player.x + lookahead
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda rocket: rocket.x)

    @staticmethod
    def _circle_rect_overlap(px: float, py: float, radius: float, rect: pygame.Rect) -> bool:
        left = float(rect.left)
        right = float(rect.right)
        top = float(rect.top)
        bottom = float(rect.bottom)
        closest_x = max(left, min(px, right))
        closest_y = max(top, min(py, bottom))
        dx = px - closest_x
        dy = py - closest_y
        return dx * dx + dy * dy <= radius * radius

    def _player_collides_with_obstacle(self, player: JetpackFollower) -> bool:
        for obstacle in self.obstacles:
            if player.x + player.radius < obstacle.x - obstacle.width * 0.5:
                continue
            if player.x - player.radius > obstacle.x + obstacle.width * 0.5:
                continue
            if self._circle_rect_overlap(player.x, player.y, player.radius, obstacle.hitbox_rect()):
                return True
        return False

    def _player_collides_with_rocket(self, player: JetpackFollower) -> bool:
        for rocket in self.rockets:
            if player.x + player.radius < rocket.x - rocket.width * 0.5:
                continue
            if player.x - player.radius > rocket.x + rocket.width * 0.5:
                continue
            if self._circle_rect_overlap(player.x, player.y, player.radius, rocket.rect()):
                return True
        return False

    def _eliminate_player(self, player: JetpackFollower):
        if not player.alive:
            return
        player.eliminate()
        player.survival_time = self.game_time
        if player.username:
            self.recent_eliminations.insert(0, player.username)
            if len(self.recent_eliminations) > self.max_recent_eliminations:
                self.recent_eliminations.pop()

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        difficulty = self._difficulty()
        self.current_world_speed = self.base_world_speed + self.speed_boost * difficulty
        self.world_distance += self.current_world_speed * dt * self.distance_scale
        self.background_scroll += self.current_world_speed * dt * self.background_scroll_factor

        self._update_obstacles(dt, difficulty)
        self._update_rockets(dt, difficulty)

        alive_players = [player for player in self.players if player.alive]
        for player in alive_players:
            upcoming_obstacles = self._find_upcoming_obstacles_for(player, max_count=3)
            next_rocket = self._find_next_rocket_for(player)
            player.update(
                dt,
                self.arena,
                upcoming_obstacles,
                next_rocket,
                self.game_time,
                difficulty,
                self.current_world_speed,
                nearby_players=alive_players,
            )

        for player in alive_players:
            if not player.alive:
                continue

            if not self.arena.is_inside_vertical(player.y, player.radius):
                self._eliminate_player(player)
                continue
            if self._player_collides_with_obstacle(player):
                self._eliminate_player(player)
                continue
            if self._player_collides_with_rocket(player):
                self._eliminate_player(player)

        alive_count = sum(1 for player in self.players if player.alive)
        has_time_limit = self.max_game_time > 0
        if alive_count <= 1 or (has_time_limit and self.game_time >= self.max_game_time):
            self._finish_game()

    def _finish_game(self):
        if self.game_over:
            return

        for player in self.players:
            if player.alive and player.survival_time <= 0:
                player.survival_time = self.game_time

        sorted_players = sorted(
            self.players,
            key=lambda player: (
                not player.alive,
                -(getattr(player, "survival_time", 0.0) or 0.0),
                player.username,
            ),
        )

        self.finish_game(sorted_players)

    def render(self):
        alive_count = sum(1 for player in self.players if player.alive)
        global_day = int(getattr(config, "DAY_NUMBER", 1))
        day_offset = int(getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71))
        club_day = max(1, global_day - day_offset)
        game_state = {
            "phase": self.phase,
            "obstacles": self.obstacles,
            "rockets": self.rockets,
            "alive_count": alive_count,
            "elapsed_time": self.game_time,
            "distance": self.world_distance,
            "speed": self.current_world_speed,
            "bg_scroll": self.background_scroll,
            "highscore": self.statistics.get_game_highscore("jetpack_followers"),
            "recent_eliminations": self.recent_eliminations,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
            "club_day_number": club_day,
            "global_day_number": global_day,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[JetpackFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "jetpack_followers"
        game_display_name = "Jetpack Followers"
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
            game_history_results.append(
                {
                    "username": player.username,
                    "placement": placement,
                    "points": points,
                    "survival_time": survival_time,
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

        if sorted_players:
            self.statistics.update_game_highscore(
                game_type=game_type,
                score=int(self.world_distance),
                username=sorted_players[0].username,
                label="Meters",
            )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
