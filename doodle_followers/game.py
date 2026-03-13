import math
import random
import time
from dataclasses import dataclass
from typing import List

import pygame

import config
from shared import GameTemplate, GameHistory, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import DoodleFollowersArena
from .player import DoodleFollower
from .renderer import DoodleFollowersRenderer


@dataclass
class DoodlePlatform:
    id: int
    index: int
    x: float
    y: float
    width: float
    height: float
    kind: str = "normal"
    vx: float = 0.0
    broken: bool = False
    break_time: float = 0.0
    spring: bool = False


@dataclass
class DoodleMonster:
    x: float
    y: float
    width: float
    height: float
    vx: float
    base_y: float
    bob_amp: float
    bob_speed: float
    bob_phase: float

    def update(self, dt: float, arena_width: float):
        self.x += self.vx * dt
        half_w = self.width * 0.5
        if self.x - half_w < 0:
            self.x = half_w
            self.vx *= -1
        elif self.x + half_w > arena_width:
            self.x = arena_width - half_w
            self.vx *= -1

        self.bob_phase += self.bob_speed * dt
        self.y = self.base_y + math.sin(self.bob_phase) * self.bob_amp


class DoodleFollowersGame(GameTemplate):
    GAME_TITLE = "DOODLE FOLLOWERS"
    GAME_SUBTITLE = "Making my followers doodle every day"
    PLAYER_LABEL = "doodles"

    def __init__(self):
        super().__init__()
        self.game_time = 0.0
        self.game_history = GameHistory()

        self.arena: DoodleFollowersArena
        self.renderer: DoodleFollowersRenderer

        self.platforms: List[DoodlePlatform] = []
        self.monsters: List[DoodleMonster] = []
        self.recent_eliminations: List[str] = []
        self.club_spotlight = None

        self.camera_y = 0.0
        self.starting_platform_y = 0.0
        self.highest_platform_y = 0.0
        self.next_platform_id = 1
        self.last_leader_best = None
        self.last_progress_time = 0.0

        seed = int(getattr(config, "DAY_NUMBER", 1))
        self.rng = random.Random(seed)

        self._init_platforms()

    def _init_game_components(self):
        self.arena = DoodleFollowersArena()
        self.renderer = DoodleFollowersRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        self.rng.shuffle(follower_data)
        club_members = load_club_member_set()

        for data in follower_data:
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]

            x = self.rng.uniform(20.0, self.arena.width - 20.0)
            player = DoodleFollower(payload, (x, self.starting_platform_y - 10.0))
            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            player.y = self.starting_platform_y - player.radius - 2.0
            self.players.append(player)

        self.club_spotlight = select_club_spotlight(self.players)
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _init_platforms(self):
        self.platforms = []
        self.monsters = []
        self.next_platform_id = 1

        start_margin = float(getattr(config, "DOODLE_START_PLATFORM_MARGIN", 6.0))
        base_width = max(60.0, self.arena.width - start_margin * 2.0)
        base_height = float(getattr(config, "DOODLE_PLATFORM_HEIGHT", 16.0))
        self.starting_platform_y = self.arena.height - base_height - 10.0

        base_id = self._next_platform_id()
        base_platform = DoodlePlatform(
            id=base_id,
            index=base_id,
            x=self.arena.width * 0.5,
            y=self.starting_platform_y,
            width=base_width,
            height=base_height,
            kind="normal",
        )
        self.platforms.append(base_platform)
        self.highest_platform_y = self.starting_platform_y

        initial_buffer = self.arena.height * 2.2
        current_y = self.starting_platform_y
        while current_y > -initial_buffer:
            spacing = self._platform_spacing(0.0, self.starting_platform_y - current_y)
            current_y -= spacing
            self._spawn_platform(current_y, 0.0)

    def _next_platform_id(self) -> int:
        value = self.next_platform_id
        self.next_platform_id += 1
        return value

    def _platform_spacing(self, difficulty: float, height_from_start: float = None) -> float:
        spacing_min = float(getattr(config, "DOODLE_PLATFORM_SPACING_MIN", 55.0))
        spacing_max = float(getattr(config, "DOODLE_PLATFORM_SPACING_MAX", 95.0))
        ramp = float(getattr(config, "DOODLE_PLATFORM_SPACING_RAMP", 0.6))
        scale = 1.0 + difficulty * ramp
        raw_gap = self.rng.uniform(spacing_min, spacing_max) * scale
        if height_from_start is not None:
            early_height = float(getattr(config, "DOODLE_EARLY_DENSITY_HEIGHT", 1200.0))
            early_scale = float(getattr(config, "DOODLE_EARLY_SPACING_SCALE", 0.7))
            if height_from_start < early_height:
                raw_gap *= max(0.4, min(1.0, early_scale))
        safe_ratio = float(getattr(config, "DOODLE_SAFE_GAP_RATIO", 0.85))
        max_gap = max(spacing_min, self._max_jump_height() * safe_ratio)
        return min(raw_gap, max_gap)

    def _max_jump_height(self) -> float:
        gravity = float(getattr(config, "DOODLE_GRAVITY", 1200.0))
        jump_velocity = abs(float(getattr(config, "DOODLE_JUMP_VELOCITY", -620.0)))
        if gravity <= 0:
            return 160.0
        return (jump_velocity * jump_velocity) / (2.0 * gravity)

    def _spawn_platform(self, y: float, difficulty: float):
        width_base = float(getattr(config, "DOODLE_PLATFORM_WIDTH", 90.0))
        height = float(getattr(config, "DOODLE_PLATFORM_HEIGHT", 16.0))
        width = width_base * self.rng.uniform(0.85, 1.15)
        edge_padding = float(getattr(config, "DOODLE_PLATFORM_EDGE_PADDING", 30.0))
        boosters_cutoff = float(getattr(config, "DOODLE_DISABLE_BOOSTERS_HEIGHT", 10000.0))
        platform_height = max(0.0, self.starting_platform_y - y)
        boosters_allowed = platform_height >= boosters_cutoff

        min_x = edge_padding + width * 0.5
        max_x = self.arena.width - edge_padding - width * 0.5
        if max_x <= min_x:
            min_x = width * 0.5
            max_x = self.arena.width - width * 0.5

        x = self.rng.uniform(min_x, max_x)

        kind = "normal"
        moving_chance = float(getattr(config, "DOODLE_MOVING_PLATFORM_CHANCE", 0.18))
        break_chance = 0.0
        trampoline_chance = float(getattr(config, "DOODLE_TRAMPOLINE_CHANCE", 0.06)) if boosters_allowed else 0.0

        roll = self.rng.random()
        if roll < trampoline_chance * (0.4 + difficulty):
            kind = "trampoline"
        elif roll < trampoline_chance + break_chance * (0.6 + difficulty):
            kind = "breakable"
        elif roll < trampoline_chance + break_chance + moving_chance * (0.5 + difficulty):
            kind = "moving"

        vx = 0.0
        if kind == "moving":
            speed = float(getattr(config, "DOODLE_MOVING_PLATFORM_SPEED", 50.0))
            vx = speed * self.rng.choice([-1.0, 1.0])

        new_id = self._next_platform_id()
        platform = DoodlePlatform(
            id=new_id,
            index=new_id,
            x=x,
            y=y,
            width=width,
            height=height,
            kind=kind,
            vx=vx,
        )

        spring_chance = float(getattr(config, "DOODLE_SPRING_CHANCE", 0.25))
        if boosters_allowed and kind in ("normal", "moving"):
            if self.rng.random() < spring_chance * (0.7 + 0.6 * difficulty):
                platform.spring = True

        self.platforms.append(platform)
        if y < self.highest_platform_y:
            self.highest_platform_y = y

        monster_chance = float(getattr(config, "DOODLE_MONSTER_CHANCE", 0.08))
        if self.rng.random() < monster_chance * (0.4 + difficulty):
            self._spawn_monster(y - self.rng.uniform(40.0, 110.0), difficulty)

    def _spawn_monster(self, y: float, difficulty: float):
        max_monsters = int(getattr(config, "DOODLE_MAX_MONSTERS", 8))
        if len(self.monsters) >= max_monsters:
            return

        width = float(getattr(config, "DOODLE_MONSTER_WIDTH", 36.0))
        height = float(getattr(config, "DOODLE_MONSTER_HEIGHT", 34.0))
        x = self.rng.uniform(width * 0.6, self.arena.width - width * 0.6)
        speed = float(getattr(config, "DOODLE_MONSTER_SPEED", 40.0))
        vx = speed * (0.6 + difficulty * 0.8) * self.rng.choice([-1.0, 1.0])

        monster = DoodleMonster(
            x=x,
            y=y,
            width=width,
            height=height,
            vx=vx,
            base_y=y,
            bob_amp=self.rng.uniform(4.0, 10.0),
            bob_speed=self.rng.uniform(1.2, 2.2),
            bob_phase=self.rng.uniform(0.0, math.tau),
        )
        self.monsters.append(monster)

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE
            dt *= float(getattr(config, "DOODLE_EXPORT_TIME_SCALE", 1.0))

        self.game_time += dt

        difficulty = self._difficulty()

        self._update_platforms(dt)
        self._update_monsters(dt)

        leader = self._get_leader()
        for player in self.players:
            prev_y = player.y
            player.update(
                dt,
                self.arena,
                self.platforms,
                difficulty,
                self.camera_y,
                is_leader=player is leader,
            )

            if not player.alive:
                continue

            self._handle_platform_collision(player, prev_y, difficulty)

        self._update_camera(dt)
        self._ensure_progress()

        for player in self.players:
            if not player.alive:
                continue

            if self._collides_with_monster(player):
                player.eliminate()
                player.survival_time = self.game_time
                self._record_elimination(player)
                continue

            offscreen_margin = float(getattr(config, "DOODLE_OFFSCREEN_MARGIN", 0.0))
            fall_margin = float(getattr(config, "DOODLE_FALL_MARGIN", 0.0))
            if player.y + player.radius < self.camera_y - offscreen_margin:
                player.eliminate()
                player.survival_time = self.game_time
                self._record_elimination(player)
                continue

            if player.y - player.radius > self.camera_y + self.arena.height + fall_margin:
                player.eliminate()
                player.survival_time = self.game_time
                self._record_elimination(player)

        self._cleanup_offscreen()
        self._ensure_platforms(difficulty)

        alive_count = sum(1 for p in self.players if p.alive)
        if alive_count <= 1:
            self._finish_game()

    def _difficulty(self) -> float:
        height_ramp = float(getattr(config, "DOODLE_DIFFICULTY_HEIGHT", 2200.0))
        if height_ramp <= 0:
            return 0.0
        height = max(0.0, -self.camera_y)
        return min(1.0, height / height_ramp)

    def _fall_margin(self) -> float:
        return float(getattr(config, "DOODLE_FALL_MARGIN", 60.0))

    def _update_platforms(self, dt: float):
        for platform in self.platforms:
            if platform.kind == "moving" and not platform.broken:
                platform.x += platform.vx * dt
                half_w = platform.width * 0.5
                if platform.x - half_w < 0:
                    platform.x = half_w
                    platform.vx *= -1
                elif platform.x + half_w > self.arena.width:
                    platform.x = self.arena.width - half_w
                    platform.vx *= -1

        break_delay = float(getattr(config, "DOODLE_BREAK_DELAY", 0.1))
        for platform in self.platforms:
            if platform.broken and self.game_time - platform.break_time > break_delay:
                platform.height = 0.0

    def _update_monsters(self, dt: float):
        for monster in self.monsters:
            monster.update(dt, self.arena.width)

    def _handle_platform_collision(self, player: DoodleFollower, prev_y: float, difficulty: float):
        if player.vy <= 0:
            return

        player_bottom_prev = prev_y + player.radius
        player_bottom = player.y + player.radius

        for platform in self.platforms:
            if platform.broken or platform.height <= 0:
                continue

            if player_bottom_prev <= platform.y <= player_bottom:
                half_w = platform.width * 0.5
                if player.x + player.radius < platform.x - half_w:
                    continue
                if player.x - player.radius > platform.x + half_w:
                    continue

                player.y = platform.y - player.radius
                player.last_platform_id = platform.id
                player.last_platform_y = platform.y
                player.current_platform_index = platform.index
                player.target_platform_index = platform.index + 1
                player.roll_jump_multiplier()

                if platform.kind == "trampoline":
                    player.vy = player.base_trampoline_velocity * player.jump_height_multiplier
                elif platform.spring:
                    player.vy = player.base_spring_velocity * player.jump_height_multiplier
                else:
                    player.vy = player.base_jump_velocity * player.jump_height_multiplier

                player.lock_jump_target(self.platforms, self.arena.width)

                if platform.kind == "breakable":
                    platform.broken = True
                    platform.break_time = self.game_time
                return

    def _collides_with_monster(self, player: DoodleFollower) -> bool:
        for monster in self.monsters:
            dx = abs(player.x - monster.x)
            dy = abs(player.y - monster.y)
            if dx < player.radius + monster.width * 0.4 and dy < player.radius + monster.height * 0.4:
                return True
        return False

    def _update_camera(self, dt: float):
        leader = self._get_leader()
        if not leader:
            return

        follow_ratio = float(getattr(config, "DOODLE_CAMERA_FOLLOW_RATIO", 0.42))
        view_height = float(getattr(config, "DOODLE_CAMERA_VIEW_HEIGHT", self.arena.height))
        follow_y = view_height * follow_ratio
        target_camera = leader.y - follow_y
        if target_camera < self.camera_y:
            smooth = float(getattr(config, "DOODLE_CAMERA_SMOOTH", 10.0))
            max_speed = float(getattr(config, "DOODLE_CAMERA_MAX_SPEED", 700.0))

            if smooth > 0:
                step = 1.0 - math.exp(-smooth * dt)
                desired = self.camera_y + (target_camera - self.camera_y) * step
            else:
                desired = target_camera

            if max_speed > 0:
                max_step = max_speed * dt
                if desired < self.camera_y - max_step:
                    self.camera_y -= max_step
                    return

            self.camera_y = desired

    def _ensure_progress(self):
        leader = self._get_leader()
        if not leader:
            return

        progress_delta = float(getattr(config, "DOODLE_SOFTLOCK_PROGRESS_DELTA", 40.0))
        timeout = float(getattr(config, "DOODLE_SOFTLOCK_TIMEOUT", 4.0))

        if self.last_leader_best is None or leader.best_height < self.last_leader_best - progress_delta:
            self.last_leader_best = leader.best_height
            self.last_progress_time = self.game_time
            return

        if self.game_time - self.last_progress_time < timeout:
            return

        self._spawn_rescue_platform(leader)
        self.last_progress_time = self.game_time
        self.last_leader_best = leader.best_height

    def _spawn_rescue_platform(self, leader: DoodleFollower):
        gap_ratio = float(getattr(config, "DOODLE_RESCUE_GAP_RATIO", 0.6))
        height = float(getattr(config, "DOODLE_PLATFORM_HEIGHT", 16.0))
        width_base = float(getattr(config, "DOODLE_PLATFORM_WIDTH", 90.0))
        width = width_base * 1.15

        gap = max(40.0, self._max_jump_height() * gap_ratio)
        y = leader.y - gap

        for platform in self.platforms:
            if platform.broken or platform.height <= 0:
                continue
            if abs(platform.y - y) < gap * 0.25 and abs(platform.x - leader.x) < width:
                return

        x_offset = self.rng.uniform(-self.arena.width * 0.2, self.arena.width * 0.2)
        x = leader.x + x_offset
        half_w = width * 0.5
        x = max(half_w, min(self.arena.width - half_w, x))

        new_id = self._next_platform_id()
        platform = DoodlePlatform(
            id=new_id,
            index=new_id,
            x=x,
            y=y,
            width=width,
            height=height,
            kind="normal",
            vx=0.0,
        )
        self.platforms.append(platform)
        if y < self.highest_platform_y:
            self.highest_platform_y = y

    def _ensure_platforms(self, difficulty: float):
        buffer = self.arena.height * 1.6
        target_top = self.camera_y - buffer
        while self.highest_platform_y > target_top:
            spacing = self._platform_spacing(difficulty, self.starting_platform_y - self.highest_platform_y)
            self.highest_platform_y -= spacing
            self._spawn_platform(self.highest_platform_y, difficulty)

    def _cleanup_offscreen(self):
        remove_threshold = self.camera_y + self.arena.height + 200.0
        self.platforms = [
            platform for platform in self.platforms
            if platform.y <= remove_threshold and platform.height > 0
        ]

        self.monsters = [
            monster for monster in self.monsters
            if monster.y <= remove_threshold
        ]

    def _record_elimination(self, player: DoodleFollower):
        if not player or not getattr(player, "username", ""):
            return
        self.recent_eliminations.insert(0, player.username)

    def _get_leader(self):
        alive = [p for p in self.players if p.alive]
        if not alive:
            return None
        return min(alive, key=lambda p: p.best_height)

    def _leader_height(self):
        leader = self._get_leader()
        if not leader:
            return 0.0
        return max(0.0, self.starting_platform_y - leader.best_height)

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
                p.best_height,
                -getattr(p, "survival_time", 0.0),
                p.username,
            ),
        )

        self.finish_game(sorted_players)

    def render(self):
        alive_count = sum(1 for p in self.players if p.alive)
        game_state = {
            "phase": self.phase,
            "platforms": self.platforms,
            "monsters": self.monsters,
            "camera_y": self.camera_y,
            "alive_count": alive_count,
            "leader_height": self._leader_height(),
            "highscore": self.statistics.get_game_highscore("doodle_followers"),
            "recent_eliminations": self.recent_eliminations,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[DoodleFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "doodle_followers"
        game_display_name = "Doodle Followers"
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

        record_player = None
        record_height = 0.0
        for player in self.players:
            height = max(0.0, self.starting_platform_y - player.best_height)
            if height > record_height:
                record_height = height
                record_player = player

        if record_player is not None:
            self.statistics.update_game_highscore(
                game_type=game_type,
                score=int(round(record_height)),
                username=record_player.username,
                label="Height",
            )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
