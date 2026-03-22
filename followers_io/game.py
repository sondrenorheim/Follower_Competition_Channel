import heapq
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pygame

import config
from shared import GameHistory, GameTemplate, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import FollowersIOArena
from .player import IOFollower
from .renderer import FollowersIORenderer


@dataclass(slots=True)
class FoodParticle:
    x: float
    y: float
    mass: float


class FollowersIOGame(GameTemplate):
    GAME_TITLE = "FOLLOWERS.IO"
    GAME_SUBTITLE = "Making my followers fight every day"
    PLAYER_LABEL = "followers"

    def __init__(self):
        super().__init__()

        self.game_history = GameHistory()
        self.game_time = 0.0
        self.recording_time = 0.0
        self.sim_step = 0

        self.players: List[IOFollower] = []
        self.alive_players: List[IOFollower] = []
        self.fading_players: List[IOFollower] = []
        self.club_players: List[IOFollower] = []
        self.food_particles: List[FoodParticle] = []

        self.current_alive_count = 0
        self.total_consumptions = 0
        self.recent_eliminations: List[str] = []
        self.max_recent_eliminations = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_TRACK_LIMIT", 400))
        self.club_spotlight = None
        self.live_leaders: List[IOFollower] = []

        self.play_phase_name = "cull"
        self.phase_progress = 0.0
        self.phase_start_recording_time = 0.0
        self.phase_start_alive_count = 0
        self.cull_start_alive_count = 0
        self.readable_start_alive_count = 0
        self.showdown_start_alive_count = 0
        self.readable_started = False
        self.showdown_started = False

        self._detail_update_phase = 0
        self._last_detail_stride = 1
        self._grid_cell_size = 18
        self._food_grid_cell_size = 18

        self.max_game_time = float(getattr(config, "FOLLOWERS_IO_MAX_GAME_TIME", 240.0))
        self.max_recorded_play_time = float(getattr(config, "FOLLOWERS_IO_MAX_RECORDED_PLAY_TIME", 46.0))
        self.initial_mass = float(getattr(config, "FOLLOWERS_IO_INITIAL_MASS", 10.0))
        self.min_mass = float(getattr(config, "FOLLOWERS_IO_MIN_MASS", 4.0))
        self.radius_scale = float(getattr(config, "FOLLOWERS_IO_RADIUS_SCALE", 0.62))
        self.base_speed = float(getattr(config, "FOLLOWERS_IO_BASE_SPEED", 7.2))
        self.speed_exponent = float(getattr(config, "FOLLOWERS_IO_SPEED_EXPONENT", 0.28))
        self.mass_decay_rate = float(getattr(config, "FOLLOWERS_IO_MASS_DECAY_RATE", 0.018))
        self.decay_free_mass_multiplier = float(
            getattr(config, "FOLLOWERS_IO_DECAY_FREE_MASS_MULTIPLIER", 1.25)
        )
        self.food_orb_mass = float(getattr(config, "FOLLOWERS_IO_FOOD_ORB_MASS", 0.75))
        self.absorb_ratio = float(getattr(config, "FOLLOWERS_IO_ABSORB_RATIO", 0.90))
        self.eat_ratio = float(getattr(config, "FOLLOWERS_IO_EAT_RATIO", 1.10))
        self.consume_overlap_ratio = float(getattr(config, "FOLLOWERS_IO_CONSUME_OVERLAP_RATIO", 0.22))
        self.player_gap = float(getattr(config, "FOLLOWERS_IO_PLAYER_GAP", 0.80))

        self.cull_video_seconds = float(getattr(config, "FOLLOWERS_IO_CULL_VIDEO_SECONDS", 8.5))
        self.cull_progress_curve = float(getattr(config, "FOLLOWERS_IO_CULL_PROGRESS_CURVE", 0.72))
        self.cull_target_alive = int(getattr(config, "FOLLOWERS_IO_CULL_TARGET_ALIVE", 8500))
        self.readable_min_alive = int(getattr(config, "FOLLOWERS_IO_READABLE_MIN_ALIVE", 5000))
        self.readable_max_alive = int(getattr(config, "FOLLOWERS_IO_READABLE_MAX_ALIVE", 12000))
        self.readable_visibility_radius = float(
            getattr(config, "FOLLOWERS_IO_READABLE_VISIBILITY_RADIUS", 5.0)
        )
        self.readable_estimate_scale = float(
            getattr(config, "FOLLOWERS_IO_READABLE_ESTIMATE_SCALE", 1.15)
        )
        self.showdown_alive = int(getattr(config, "FOLLOWERS_IO_SHOWDOWN_ALIVE", 250))

        self.reseed_mass_min_multiplier = float(
            getattr(config, "FOLLOWERS_IO_RESEED_MASS_MIN_MULTIPLIER", 0.90)
        )
        self.reseed_mass_max_multiplier = float(
            getattr(config, "FOLLOWERS_IO_RESEED_MASS_MAX_MULTIPLIER", 1.25)
        )
        self.reseed_cluster_min_scale = float(
            getattr(config, "FOLLOWERS_IO_RESEED_CLUSTER_MIN_SCALE", 0.62)
        )
        self.reseed_cluster_max_scale = float(
            getattr(config, "FOLLOWERS_IO_RESEED_CLUSTER_MAX_SCALE", 0.94)
        )
        self.reseed_jitter = float(getattr(config, "FOLLOWERS_IO_RESEED_JITTER", 0.18))

        self.food_density = float(getattr(config, "FOLLOWERS_IO_FOOD_DENSITY", 0.35))
        self.food_min_count = int(getattr(config, "FOLLOWERS_IO_FOOD_MIN_COUNT", 600))
        self.food_max_count = int(getattr(config, "FOLLOWERS_IO_FOOD_MAX_COUNT", 1800))

        self.collision_full_threshold = int(
            getattr(config, "FOLLOWERS_IO_COLLISION_FULL_THRESHOLD", 5000)
        )
        self.target_detailed_updates = int(
            getattr(config, "FOLLOWERS_IO_TARGET_DETAILED_UPDATES", 6000)
        )
        self.max_detailed_consumptions = int(
            getattr(config, "FOLLOWERS_IO_MAX_DETAILED_CONSUMPTIONS", 2200)
        )

        self.cull_capture_speed = float(getattr(config, "FOLLOWERS_IO_CULL_CAPTURE_SPEED", 1.0))
        self.readable_capture_speed = float(
            getattr(config, "FOLLOWERS_IO_READABLE_CAPTURE_SPEED", 1.0)
        )
        self.showdown_capture_speed = float(
            getattr(config, "FOLLOWERS_IO_SHOWDOWN_CAPTURE_SPEED", 1.0)
        )

        self.camera_padding = float(getattr(config, "FOLLOWERS_IO_CAMERA_PADDING", 34))
        self.camera_focus_padding = float(getattr(config, "FOLLOWERS_IO_CAMERA_FOCUS_PADDING", 52))
        self.camera_smoothing = float(getattr(config, "FOLLOWERS_IO_CAMERA_SMOOTHING", 0.18))
        self.camera_zoom_min = float(getattr(config, "FOLLOWERS_IO_CAMERA_ZOOM_MIN", 1.0))
        self.camera_zoom_max = float(getattr(config, "FOLLOWERS_IO_CAMERA_ZOOM_MAX", 2.2))
        self.live_leader_count = int(getattr(config, "FOLLOWERS_IO_LIVE_LEADER_COUNT", 5))
        self.current_camera_rect = tuple(float(value) for value in self.arena.get_rect())

        # Keep same background music flow used elsewhere.
        self.recorder.background_music_path = self.sound.background_music_path

    def _init_game_components(self):
        self.arena = FollowersIOArena()
        self.renderer = FollowersIORenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            target_count = config.TEST_MINIMAL_PLAYER_COUNT
        else:
            target_count = config.FOLLOWER_COUNT

        # 250k+ runs are not practical with profile images loaded.
        previous_load = getattr(config, "LOAD_PROFILE_PICTURES", True)
        previous_download = getattr(config, "DOWNLOAD_PROFILE_PICTURES", False)
        config.LOAD_PROFILE_PICTURES = False
        config.DOWNLOAD_PROFILE_PICTURES = False
        try:
            follower_data = self.api.fetch_followers(target_count)
        finally:
            config.LOAD_PROFILE_PICTURES = previous_load
            config.DOWNLOAD_PROFILE_PICTURES = previous_download

        random.shuffle(follower_data)
        club_members = load_club_member_set()

        for data in follower_data:
            payload = dict(data)
            username = payload.get("username") or "unknown"
            payload["username"] = username
            payload["avatar_image"] = payload.get("avatar_image") or payload.get("avatar")

            x, y = self.arena.get_random_position(margin=1.0)
            player = IOFollower(
                payload,
                (x, y),
                mass=self.initial_mass,
                radius_scale=self.radius_scale,
            )
            norm_username = normalize_username(username)
            player.is_club_member = norm_username in club_members
            self.players.append(player)
            if player.is_club_member:
                self.club_players.append(player)

        self.alive_players = list(self.players)
        self.current_alive_count = len(self.alive_players)
        self.club_spotlight = select_club_spotlight(self.players)
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def run(self):
        self.setup_players()

        if self.minimal_test_startup:
            print("\nTEST_MINIMAL_PLAYERS: Starting Followers.io simulation immediately.")
            self.phase = "playing"
            self.current_alive_count = len(self.alive_players)
            self._set_play_phase(
                "cull" if self.current_alive_count > self.readable_max_alive else "readable"
            )
            if self.play_phase_name == "readable":
                self._enter_readable_phase()
        else:
            print("\nStarting countdown...")
            self.countdown_start_time = time.time()
            self.phase = "countdown"

            self.sound.start_background_music()
            self.sound.set_music_volume_low()
            self.sound.play_smash_countdown_audio()

            countdown_active = True
            while countdown_active and self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        return
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.running = False
                        return

                target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
                self.clock.tick(target_fps)

                elapsed = time.time() - self.countdown_start_time
                if elapsed >= self.countdown_duration:
                    countdown_active = False
                    self.phase = "playing"
                    self.current_alive_count = len(self.alive_players)
                    self._set_play_phase(
                        "cull" if self.current_alive_count > self.readable_max_alive else "readable"
                    )
                    if self.play_phase_name == "readable":
                        self._enter_readable_phase()
                    print("\nGO! Game started!")
                    self.sound.set_music_volume_high()

                self.sound.update_music_volume()
                self.render()

            self.countdown_start_time = None

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0

            self.update(dt)
            self.render()

            if self.game_over and self.show_leaderboards and self.leaderboard_display_start is not None:
                if time.time() - self.leaderboard_display_start >= 5.0:
                    self.running = False

        self.cleanup()

    def _get_recording_speed_multiplier(self) -> float:
        if not config.EXPORT_VIDEO or self.phase != "playing":
            return 1.0
        if self.play_phase_name == "cull":
            return max(1.0, self.cull_capture_speed)
        if self.play_phase_name == "showdown":
            return max(1.0, self.showdown_capture_speed)
        return max(1.0, self.readable_capture_speed)

    def _compute_detail_stride(self, alive_count: int) -> int:
        if self.target_detailed_updates <= 0 or alive_count <= self.target_detailed_updates:
            return 1
        return max(1, int(math.ceil(alive_count / float(self.target_detailed_updates))))

    def _set_play_phase(self, phase_name: str):
        self.play_phase_name = phase_name
        self.phase_start_recording_time = self.recording_time
        self.phase_start_alive_count = len(self.alive_players)

        if phase_name == "cull":
            self.cull_start_alive_count = self.phase_start_alive_count
            self.readable_started = False
            self.showdown_started = False
        elif phase_name == "readable":
            self.readable_start_alive_count = self.phase_start_alive_count
            self.showdown_started = False
        elif phase_name == "showdown":
            self.showdown_start_alive_count = self.phase_start_alive_count
            self.showdown_started = True

        self.phase_progress = 0.0

    def _phase_recorded_elapsed(self) -> float:
        return max(0.0, self.recording_time - self.phase_start_recording_time)

    def _estimate_readable_render_radius(self, alive_count: int) -> float:
        if alive_count <= 0:
            return 0.0
        area = max(1.0, float(self.arena.width * self.arena.height))
        return math.sqrt(area / float(alive_count)) * self.readable_estimate_scale

    def _get_player_speed(self, player: IOFollower) -> float:
        return self.base_speed / max(1.0, player.mass ** self.speed_exponent)

    def _clamp_player_to_arena(self, player: IOFollower):
        if player.x <= self.arena.left + player.radius:
            player.x = self.arena.left + player.radius
            player.vx = abs(player.vx) or 0.1
        elif player.x >= self.arena.right - player.radius:
            player.x = self.arena.right - player.radius
            player.vx = -abs(player.vx) or -0.1

        if player.y <= self.arena.top + player.radius:
            player.y = self.arena.top + player.radius
            player.vy = abs(player.vy) or 0.1
        elif player.y >= self.arena.bottom - player.radius:
            player.y = self.arena.bottom - player.radius
            player.vy = -abs(player.vy) or -0.1

    def _fast_motion(self, player: IOFollower, dt: float):
        move_speed = self._get_player_speed(player)
        player.x += player.vx * move_speed * dt * 60.0
        player.y += player.vy * move_speed * dt * 60.0
        self._clamp_player_to_arena(player)

    def _build_player_grid(self, players: Iterable[IOFollower]) -> Dict[tuple[int, int], List[IOFollower]]:
        players = list(players)
        if not players:
            self._grid_cell_size = 18
            return {}

        max_radius = max(1.0, max(player.radius for player in players))
        self._grid_cell_size = max(14, int(math.ceil(max_radius * 4.2)))
        grid: Dict[tuple[int, int], List[IOFollower]] = {}
        for player in players:
            key = (int(player.x // self._grid_cell_size), int(player.y // self._grid_cell_size))
            grid.setdefault(key, []).append(player)
        return grid

    def _build_food_grid(self) -> Dict[tuple[int, int], List[FoodParticle]]:
        if not self.food_particles:
            self._food_grid_cell_size = max(14, self._grid_cell_size)
            return {}

        self._food_grid_cell_size = max(14, self._grid_cell_size)
        grid: Dict[tuple[int, int], List[FoodParticle]] = {}
        for orb in self.food_particles:
            if orb.mass <= 0.0:
                continue
            key = (int(orb.x // self._food_grid_cell_size), int(orb.y // self._food_grid_cell_size))
            grid.setdefault(key, []).append(orb)
        return grid

    def _iter_nearby_players(
        self,
        grid: Dict[tuple[int, int], List[IOFollower]],
        player: IOFollower,
        radius_cells: int = 1,
    ):
        if not grid:
            return
        cell_x = int(player.x // max(1, self._grid_cell_size))
        cell_y = int(player.y // max(1, self._grid_cell_size))
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                nearby = grid.get((cell_x + dx, cell_y + dy))
                if not nearby:
                    continue
                for other in nearby:
                    yield other

    def _iter_nearby_food(
        self,
        food_grid: Dict[tuple[int, int], List[FoodParticle]],
        player: IOFollower,
        radius_cells: int = 2,
    ):
        if not food_grid:
            return
        cell_x = int(player.x // max(1, self._food_grid_cell_size))
        cell_y = int(player.y // max(1, self._food_grid_cell_size))
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                nearby = food_grid.get((cell_x + dx, cell_y + dy))
                if not nearby:
                    continue
                for orb in nearby:
                    if orb.mass > 0.0:
                        yield orb

    def _compute_ai_vector(
        self,
        player: IOFollower,
        player_grid: Dict[tuple[int, int], List[IOFollower]],
        food_grid: Dict[tuple[int, int], List[FoodParticle]],
    ) -> tuple[float, float]:
        threat_x = 0.0
        threat_y = 0.0
        prey_x = 0.0
        prey_y = 0.0
        space_x = 0.0
        space_y = 0.0

        for other in self._iter_nearby_players(player_grid, player, radius_cells=1):
            if other is player or not other.alive:
                continue

            dx = other.x - player.x
            dy = other.y - player.y
            dist_sq = dx * dx + dy * dy
            if dist_sq <= 1e-6:
                continue

            dist = math.sqrt(dist_sq)
            if other.mass > player.mass * self.eat_ratio:
                weight = min(4.0, other.mass / max(1.0, player.mass)) / max(18.0, dist)
                threat_x -= dx * weight
                threat_y -= dy * weight
            elif player.mass > other.mass * self.eat_ratio:
                weight = min(3.0, player.mass / max(1.0, other.mass)) / max(24.0, dist)
                prey_x += dx * weight
                prey_y += dy * weight

            spacing = player.radius + other.radius + self.player_gap * 1.5
            if dist < spacing:
                weight = (spacing - dist) / max(1.0, spacing)
                space_x -= dx * weight
                space_y -= dy * weight

        food_candidates = []
        for orb in self._iter_nearby_food(food_grid, player, radius_cells=2):
            dx = orb.x - player.x
            dy = orb.y - player.y
            dist_sq = dx * dx + dy * dy
            food_candidates.append((dist_sq, dx, dy))
        food_candidates.sort(key=lambda item: item[0])

        food_x = 0.0
        food_y = 0.0
        for dist_sq, dx, dy in food_candidates[:4]:
            dist = math.sqrt(max(1.0, dist_sq))
            weight = 1.0 / max(16.0, dist)
            food_x += dx * weight
            food_y += dy * weight

        wall_x = 0.0
        wall_y = 0.0
        wall_margin = max(24.0, player.radius * 5.0)
        if player.x < self.arena.left + wall_margin:
            wall_x += (self.arena.left + wall_margin - player.x) / wall_margin
        elif player.x > self.arena.right - wall_margin:
            wall_x -= (player.x - (self.arena.right - wall_margin)) / wall_margin
        if player.y < self.arena.top + wall_margin:
            wall_y += (self.arena.top + wall_margin - player.y) / wall_margin
        elif player.y > self.arena.bottom - wall_margin:
            wall_y -= (player.y - (self.arena.bottom - wall_margin)) / wall_margin

        threat_mag = math.hypot(threat_x, threat_y)
        vector_x = 0.0
        vector_y = 0.0
        if threat_mag > 0.02:
            vector_x += threat_x * 2.8
            vector_y += threat_y * 2.8
            vector_x += prey_x * 0.25
            vector_y += prey_y * 0.25
            vector_x += food_x * 0.40
            vector_y += food_y * 0.40
        else:
            vector_x += prey_x * 1.45
            vector_y += prey_y * 1.45
            vector_x += food_x * 1.15
            vector_y += food_y * 1.15

        vector_x += space_x * 1.1
        vector_y += space_y * 1.1
        vector_x += wall_x * 1.8
        vector_y += wall_y * 1.8

        if abs(vector_x) < 1e-5 and abs(vector_y) < 1e-5:
            if abs(player.vx) < 1e-5 and abs(player.vy) < 1e-5:
                angle = random.random() * math.tau
                return (math.cos(angle), math.sin(angle))
            return (player.vx, player.vy)

        norm = math.hypot(vector_x, vector_y)
        return (vector_x / norm, vector_y / norm)

    def _update_readable_player(
        self,
        player: IOFollower,
        effective_dt: float,
        player_grid: Dict[tuple[int, int], List[IOFollower]],
        food_grid: Dict[tuple[int, int], List[FoodParticle]],
    ):
        desired_x, desired_y = self._compute_ai_vector(player, player_grid, food_grid)
        blend = min(1.0, effective_dt * 3.5)
        player.vx = (player.vx * (1.0 - blend)) + (desired_x * blend)
        player.vy = (player.vy * (1.0 - blend)) + (desired_y * blend)

        norm = math.hypot(player.vx, player.vy)
        if norm < 1e-6:
            angle = random.random() * math.tau
            player.vx = math.cos(angle)
            player.vy = math.sin(angle)
            norm = 1.0

        move_speed = self._get_player_speed(player)
        player.x += (player.vx / norm) * move_speed * effective_dt * 60.0
        player.y += (player.vy / norm) * move_speed * effective_dt * 60.0
        self._clamp_player_to_arena(player)
        self._apply_mass_decay(player, effective_dt)

    def _apply_mass_decay(self, player: IOFollower, dt: float):
        floor_mass = max(self.min_mass, self.initial_mass * self.decay_free_mass_multiplier)
        if player.mass <= floor_mass or self.mass_decay_rate <= 0.0:
            return
        decay_factor = max(0.0, 1.0 - self.mass_decay_rate * dt)
        new_mass = floor_mass + ((player.mass - floor_mass) * decay_factor)
        player.mass = max(floor_mass, new_mass)
        player.update_radius(self.radius_scale)

    def _target_food_count(self, alive_count: Optional[int] = None) -> int:
        if self.play_phase_name not in ("readable", "showdown"):
            return 0
        if alive_count is None:
            alive_count = self.current_alive_count
        target = int(round(alive_count * self.food_density))
        return max(self.food_min_count, min(self.food_max_count, target))

    def _spawn_food_particle(self):
        x, y = self.arena.get_random_position(margin=2.0)
        self.food_particles.append(FoodParticle(x=x, y=y, mass=self.food_orb_mass))

    def _sync_food_budget(self):
        if self.play_phase_name not in ("readable", "showdown"):
            self.food_particles.clear()
            return

        self.food_particles = [orb for orb in self.food_particles if orb.mass > 0.0]
        target = self._target_food_count()
        if len(self.food_particles) > target:
            self.food_particles = random.sample(self.food_particles, target) if target > 0 else []
        while len(self.food_particles) < target:
            self._spawn_food_particle()

    def _consume_food_for_players(
        self,
        players: Iterable[IOFollower],
        food_grid: Dict[tuple[int, int], List[FoodParticle]],
    ):
        for player in players:
            if not player.alive:
                continue
            for orb in self._iter_nearby_food(food_grid, player, radius_cells=1):
                if orb.mass <= 0.0:
                    continue
                dx = player.x - orb.x
                dy = player.y - orb.y
                consume_radius = max(1.0, player.radius + (math.sqrt(orb.mass) * self.radius_scale * 0.6))
                if dx * dx + dy * dy <= consume_radius * consume_radius:
                    player.gain_mass(orb.mass, radius_scale=self.radius_scale)
                    orb.mass = 0.0

        self.food_particles = [orb for orb in self.food_particles if orb.mass > 0.0]

    def _resolve_player_spacing(
        self,
        player_grid: Dict[tuple[int, int], List[IOFollower]],
        candidates: Iterable[IOFollower],
    ):
        processed_pairs = set()
        for player in candidates:
            if not player.alive:
                continue
            for other in self._iter_nearby_players(player_grid, player, radius_cells=1):
                if other is player or not other.alive:
                    continue

                pair_key = tuple(sorted((id(player), id(other))))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                dx = other.x - player.x
                dy = other.y - player.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= 1e-6:
                    angle = random.random() * math.tau
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                    dist_sq = 1.0

                dist = math.sqrt(dist_sq)
                if player.mass > other.mass * self.eat_ratio:
                    consume_limit = max(1.0, player.radius - (other.radius * self.consume_overlap_ratio))
                    if dist <= consume_limit:
                        continue
                elif other.mass > player.mass * self.eat_ratio:
                    consume_limit = max(1.0, other.radius - (player.radius * self.consume_overlap_ratio))
                    if dist <= consume_limit:
                        continue

                min_spacing = player.radius + other.radius + self.player_gap
                if dist >= min_spacing:
                    continue

                overlap = min_spacing - dist
                nx = dx / dist
                ny = dy / dist
                total_mass = max(1.0, player.mass + other.mass)
                player_share = other.mass / total_mass
                other_share = player.mass / total_mass
                player.x -= nx * overlap * player_share * 0.55
                player.y -= ny * overlap * player_share * 0.55
                other.x += nx * overlap * other_share * 0.55
                other.y += ny * overlap * other_share * 0.55
                self._clamp_player_to_arena(player)
                self._clamp_player_to_arena(other)

    def _consume(self, killer: IOFollower, victim: IOFollower, *, record_feed: bool = True) -> bool:
        if not killer.alive or not victim.alive or killer is victim:
            return False
        if killer.mass <= victim.mass * self.eat_ratio:
            return False

        gained_mass = victim.mass * self.absorb_ratio
        killer.gain_mass(gained_mass, radius_scale=self.radius_scale)
        killer.kills += 1
        killer.consumed_mass += victim.mass

        victim.mark_eliminated(step=self.sim_step, game_time=self.game_time)
        self.total_consumptions += 1
        self.fading_players.append(victim)
        if victim in self.alive_players:
            self.alive_players.remove(victim)
        self.current_alive_count = len(self.alive_players)

        if record_feed and victim.username:
            self.recent_eliminations.insert(0, victim.username)
            if len(self.recent_eliminations) > self.max_recent_eliminations:
                self.recent_eliminations.pop()
        return True

    def _resolve_player_consumption(
        self,
        player_grid: Dict[tuple[int, int], List[IOFollower]],
        candidates: Iterable[IOFollower],
    ):
        consumed_this_frame = 0
        for eater in candidates:
            if not eater.alive:
                continue
            for other in self._iter_nearby_players(player_grid, eater, radius_cells=1):
                if other is eater or not other.alive:
                    continue
                if eater.mass <= other.mass * self.eat_ratio:
                    continue

                dx = eater.x - other.x
                dy = eater.y - other.y
                consume_radius = max(1.0, eater.radius - (other.radius * self.consume_overlap_ratio))
                if dx * dx + dy * dy <= consume_radius * consume_radius:
                    if self._consume(eater, other):
                        consumed_this_frame += 1
                        break

            if consumed_this_frame >= self.max_detailed_consumptions:
                break

    def _prune_fading_players(self):
        fade_duration = float(getattr(config, "FADE_DURATION", 0.5))
        self.fading_players = [
            player for player in self.fading_players if player.is_fading(fade_duration)
        ]

    def _mark_cull_elimination(self, player: IOFollower):
        player.mark_eliminated(step=self.sim_step, game_time=self.game_time)

    def _eliminate_random_alive(self, count: int):
        alive_count = len(self.alive_players)
        count = max(0, min(count, alive_count - 1))
        if count <= 0:
            return

        indices = random.sample(range(alive_count), count)
        indices.sort(reverse=True)
        for idx in indices:
            player = self.alive_players[idx]
            self._mark_cull_elimination(player)
            last_index = len(self.alive_players) - 1
            self.alive_players[idx] = self.alive_players[last_index]
            self.alive_players.pop()

        self.current_alive_count = len(self.alive_players)

    def _enter_readable_phase(self):
        self.readable_started = True
        self.fading_players.clear()
        self.recent_eliminations.clear()
        self.food_particles.clear()
        self._reseed_alive_players()
        self._detail_update_phase = 0
        self._set_play_phase("readable")
        self._sync_food_budget()
        self.live_leaders = self._compute_live_leaders()
        self.current_camera_rect = self._compute_camera_target()
        self.renderer.clear_avatar_cache()

    def _maybe_enter_showdown(self):
        if self.play_phase_name != "readable":
            return
        if len(self.alive_players) > self.showdown_alive:
            return
        self._set_play_phase("showdown")
        self._sync_food_budget()
        self.live_leaders = self._compute_live_leaders()
        self.current_camera_rect = self._compute_camera_target()
        self.renderer.clear_avatar_cache()

    def _reseed_alive_players(self):
        alive_count = len(self.alive_players)
        if alive_count <= 0:
            return

        pop_ratio = min(1.0, math.sqrt(alive_count / max(1.0, float(self.cull_target_alive))))
        cluster_scale = self.reseed_cluster_min_scale + (
            (self.reseed_cluster_max_scale - self.reseed_cluster_min_scale) * pop_ratio
        )
        cluster_width = self.arena.width * cluster_scale
        cluster_height = self.arena.height * cluster_scale
        cols = max(1, int(math.ceil(math.sqrt(alive_count * (cluster_width / max(1.0, cluster_height))))))
        rows = max(1, int(math.ceil(alive_count / cols)))
        cell_w = cluster_width / cols
        cell_h = cluster_height / rows

        cluster_left = self.arena.center_x - (cluster_width * 0.5)
        cluster_top = self.arena.center_y - (cluster_height * 0.5)

        random.shuffle(self.alive_players)
        for idx, player in enumerate(self.alive_players):
            row = idx // cols
            col = idx % cols
            player.mass = self.initial_mass * random.uniform(
                self.reseed_mass_min_multiplier,
                self.reseed_mass_max_multiplier,
            )
            player.update_radius(self.radius_scale)
            player.alpha = 255

            jitter_x = random.uniform(-self.reseed_jitter, self.reseed_jitter) * cell_w
            jitter_y = random.uniform(-self.reseed_jitter, self.reseed_jitter) * cell_h
            player.x = cluster_left + ((col + 0.5) * cell_w) + jitter_x
            player.y = cluster_top + ((row + 0.5) * cell_h) + jitter_y

            angle = random.random() * math.tau
            player.vx = math.cos(angle)
            player.vy = math.sin(angle)
            self._clamp_player_to_arena(player)

        self.current_alive_count = len(self.alive_players)

    def _compute_live_leaders(self) -> List[IOFollower]:
        if not self.alive_players:
            return []
        return heapq.nlargest(
            self.live_leader_count,
            self.alive_players,
            key=lambda player: (player.mass, player.kills, player.consumed_mass, player.username),
        )

    def _compute_camera_target(self) -> tuple[float, float, float, float]:
        full_rect = (
            float(self.arena.left),
            float(self.arena.top),
            float(self.arena.width),
            float(self.arena.height),
        )
        if self.play_phase_name == "cull" or not self.alive_players:
            return full_rect

        focus_players = self.live_leaders if self.play_phase_name == "showdown" and self.live_leaders else self.alive_players
        min_x = min(player.x - player.radius for player in focus_players)
        max_x = max(player.x + player.radius for player in focus_players)
        min_y = min(player.y - player.radius for player in focus_players)
        max_y = max(player.y + player.radius for player in focus_players)

        padding = self.camera_focus_padding if self.play_phase_name == "showdown" else self.camera_padding
        target_width = max(1.0, (max_x - min_x) + padding * 2.0)
        target_height = max(1.0, (max_y - min_y) + padding * 2.0)

        min_width = self.arena.width / max(1.0, self.camera_zoom_max)
        min_height = self.arena.height / max(1.0, self.camera_zoom_max)
        max_width = self.arena.width / max(1.0, self.camera_zoom_min)
        max_height = self.arena.height / max(1.0, self.camera_zoom_min)
        target_width = max(min_width, min(target_width, max_width))
        target_height = max(min_height, min(target_height, max_height))

        aspect = self.arena.width / max(1.0, float(self.arena.height))
        if target_width / target_height > aspect:
            target_height = target_width / aspect
        else:
            target_width = target_height * aspect

        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        left = center_x - target_width * 0.5
        top = center_y - target_height * 0.5
        left = max(self.arena.left, min(self.arena.right - target_width, left))
        top = max(self.arena.top, min(self.arena.bottom - target_height, top))
        return (left, top, target_width, target_height)

    def _update_camera(self, dt: float, *, force: bool = False):
        target = self._compute_camera_target()
        if force:
            self.current_camera_rect = target
            return
        blend = min(1.0, dt * 60.0 * self.camera_smoothing)
        current = self.current_camera_rect
        self.current_camera_rect = tuple(
            current[index] + ((target[index] - current[index]) * blend) for index in range(4)
        )

    def _update_phase_progress(self):
        if self.play_phase_name == "cull":
            self.phase_progress = min(1.0, self._phase_recorded_elapsed() / max(0.001, self.cull_video_seconds))
            return

        if self.play_phase_name == "showdown":
            start_alive = max(2, self.showdown_start_alive_count)
            self.phase_progress = 1.0 - (
                (max(1, self.current_alive_count) - 1) / max(1.0, float(start_alive - 1))
            )
            self.phase_progress = max(0.0, min(1.0, self.phase_progress))
            return

        start_alive = max(self.showdown_alive + 1, self.readable_start_alive_count)
        self.phase_progress = 1.0 - (
            (max(self.showdown_alive, self.current_alive_count) - self.showdown_alive)
            / max(1.0, float(start_alive - self.showdown_alive))
        )
        self.phase_progress = max(0.0, min(1.0, self.phase_progress))

    def _update_cull(self, dt: float):
        alive_count = len(self.alive_players)
        self._last_detail_stride = 1
        if alive_count <= self.readable_max_alive and (
            alive_count <= self.readable_min_alive
            or self._estimate_readable_render_radius(alive_count) >= self.readable_visibility_radius
        ):
            self._enter_readable_phase()
            return

        progress = min(1.0, self._phase_recorded_elapsed() / max(0.001, self.cull_video_seconds))
        eased = math.pow(progress, self.cull_progress_curve)
        start_alive = max(2, self.cull_start_alive_count)
        target_alive = max(self.readable_min_alive, min(self.readable_max_alive, self.cull_target_alive))
        desired_alive = int(
            round(
                math.exp(
                    (math.log(start_alive) * (1.0 - eased))
                    + (math.log(target_alive) * eased)
                )
            )
        )
        desired_alive = max(target_alive, min(start_alive, desired_alive))

        if alive_count > desired_alive:
            self._eliminate_random_alive(alive_count - desired_alive)

        alive_count = len(self.alive_players)
        if alive_count <= self.readable_min_alive:
            self._enter_readable_phase()
            return
        if progress >= 1.0 and alive_count <= self.readable_max_alive:
            self._enter_readable_phase()

    def _update_readable_phase(self, dt: float):
        alive_count = len(self.alive_players)
        if alive_count <= 0:
            return

        self._sync_food_budget()
        detail_stride = self._compute_detail_stride(alive_count)
        self._last_detail_stride = detail_stride

        player_grid = self._build_player_grid(self.alive_players)
        food_grid = self._build_food_grid()
        updated_players: List[IOFollower] = []

        for idx, player in enumerate(self.alive_players):
            if detail_stride <= 1 or ((idx + self._detail_update_phase) % detail_stride == 0):
                effective_dt = dt * detail_stride
                self._update_readable_player(player, effective_dt, player_grid, food_grid)
                updated_players.append(player)
            else:
                self._fast_motion(player, dt)

        if detail_stride > 1:
            self._detail_update_phase = (self._detail_update_phase + 1) % detail_stride
        else:
            self._detail_update_phase = 0

        player_grid = self._build_player_grid(self.alive_players)
        food_grid = self._build_food_grid()
        self._consume_food_for_players(updated_players if detail_stride > 1 else self.alive_players, food_grid)

        player_grid = self._build_player_grid(self.alive_players)
        spacing_candidates = self.alive_players if alive_count <= self.collision_full_threshold else updated_players
        self._resolve_player_spacing(player_grid, spacing_candidates)

        player_grid = self._build_player_grid(self.alive_players)
        consume_candidates = self.alive_players if alive_count <= self.collision_full_threshold else updated_players
        self._resolve_player_consumption(player_grid, consume_candidates)

        self.current_alive_count = len(self.alive_players)
        self._sync_food_budget()

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        self.sim_step += 1
        self.sound.update_music_volume()
        self._prune_fading_players()

        self.current_alive_count = len(self.alive_players)
        if self.play_phase_name == "cull":
            self._update_cull(dt)
        else:
            self._update_readable_phase(dt)

        self.current_alive_count = len(self.alive_players)
        self.live_leaders = self._compute_live_leaders()
        self._maybe_enter_showdown()
        self._update_phase_progress()
        self._update_camera(dt)

        speed_multiplier = self._get_recording_speed_multiplier()
        self.recording_time += dt / max(1.0, speed_multiplier)

        if (
            self.current_alive_count <= 1
            or self.recording_time >= self.max_recorded_play_time
            or self.game_time >= self.max_game_time
        ):
            self._finish_game()

    def _rank_key(self, player: IOFollower):
        if player.alive:
            return (0, -player.mass, player.username)
        return (1, -(player.elimination_step or 0), player.username)

    def _apply_tied_placements(self, sorted_players: List[IOFollower]):
        placement = 1
        last_tie_key = None

        for idx, player in enumerate(sorted_players):
            if player.alive:
                tie_key = ("alive", round(float(player.mass), 3))
            else:
                tie_key = ("dead", int(player.elimination_step or 0))

            if last_tie_key is None:
                placement = 1
            elif tie_key != last_tie_key:
                placement = idx + 1

            player.placement = placement
            last_tie_key = tie_key

    def _finish_game(self):
        if self.game_over:
            return

        for player in self.players:
            if player.alive:
                player.survival_time = self.game_time
            elif player.survival_time <= 0.0:
                player.survival_time = self.game_time

        sorted_players = sorted(self.players, key=self._rank_key)
        self.finish_game(sorted_players)

    def finish_game(self, sorted_players: List[IOFollower]):
        self.game_over = True
        self.phase = "finished"
        self._apply_tied_placements(sorted_players)

        if sorted_players:
            self.winner = sorted_players[0]

        print("\n" + "=" * 60)
        print("  GAME COMPLETE")
        print("=" * 60)
        print("\nTop 10:")
        for i, player in enumerate(sorted_players[:10]):
            print(f"{i+1}. {player.username}")

        self._calculate_and_save_scores(sorted_players)

    def _get_render_players(self) -> List[IOFollower]:
        if self.play_phase_name == "cull" and self.phase == "playing":
            limit = int(getattr(config, "FOLLOWERS_IO_CULL_RENDER_LIMIT", 3200))
            if len(self.alive_players) <= limit:
                sampled = list(self.alive_players)
            else:
                step = len(self.alive_players) / float(limit)
                sampled = [self.alive_players[int(idx * step)] for idx in range(limit)]

            seen = {id(player) for player in sampled}
            for player in self.club_players:
                if player.alive and id(player) not in seen:
                    sampled.append(player)
                    seen.add(id(player))
            return sampled

        return list(self.alive_players) + list(self.fading_players)

    def render(self):
        render_players = self._get_render_players()
        speedup_factor = self._get_recording_speed_multiplier()
        game_state = {
            "phase": self.phase,
            "phase_name": self.play_phase_name if self.phase == "playing" else self.phase,
            "phase_progress": self.phase_progress,
            "showdown_active": self.play_phase_name == "showdown",
            "alive_count": self.current_alive_count,
            "total_count": len(self.players),
            "elapsed_time": self.game_time,
            "recorded_time": self.recording_time,
            "total_consumptions": self.total_consumptions,
            "food_particles": self.food_particles,
            "recent_eliminations": self.recent_eliminations,
            "highscore": self.statistics.get_game_highscore("followers_io"),
            "detail_stride": self._last_detail_stride,
            "speedup_active": config.EXPORT_VIDEO and speedup_factor > 1.0,
            "speedup_factor": speedup_factor,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
            "live_leaders": self.live_leaders,
            "camera_rect": self.current_camera_rect,
        }
        self.renderer.render_frame(render_players, game_state)
        pygame.display.flip()

        if self.phase == "playing":
            self.recorder.capture_frame(self.screen, current_time=self.recording_time)
        else:
            self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[IOFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "followers_io"
        game_display_name = "Followers.io"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)
            survival_time = float(getattr(player, "survival_time", 0.0) or 0.0)

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
                kills=int(getattr(player, "kills", 0) or 0),
                damage_dealt=float(getattr(player, "consumed_mass", 0.0) or 0.0),
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
                    "kills": int(getattr(player, "kills", 0) or 0),
                    "damage": float(getattr(player, "consumed_mass", 0.0) or 0.0),
                }
            )

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
        )

        if self.players:
            record_player = max(self.players, key=lambda p: float(getattr(p, "mass", 0.0) or 0.0))
            self.statistics.update_game_highscore(
                game_type=game_type,
                score=float(getattr(record_player, "mass", 0.0) or 0.0),
                username=record_player.username,
                label="Mass",
            )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
