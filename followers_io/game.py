import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

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
    vx: float
    vy: float
    mass: float
    ttl: float


class FollowersIOGame(GameTemplate):
    GAME_TITLE = "FOLLOWERS.IO"
    GAME_SUBTITLE = "Making my followers fight every day"
    PLAYER_LABEL = "followers"

    def __init__(self):
        super().__init__()

        self.game_history = GameHistory()
        self.game_time = 0.0
        self.sim_step = 0
        self.total_consumptions = 0
        self.recent_eliminations: List[str] = []
        self.max_recent_eliminations = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_TRACK_LIMIT", 400))
        self.club_spotlight = None

        self.players: List[IOFollower] = []
        self.alive_players: List[IOFollower] = []
        self.food_particles: List[FoodParticle] = []
        self.food_bank = 0.0
        self._pending_compaction = 0
        self._detail_update_phase = 0
        self._last_detail_stride = 1
        self._grid_cell_size = 24

        self.max_game_time = float(getattr(config, "FOLLOWERS_IO_MAX_GAME_TIME", 720.0))
        self.initial_mass = float(getattr(config, "FOLLOWERS_IO_INITIAL_MASS", 36.0))
        self.min_mass = float(getattr(config, "FOLLOWERS_IO_MIN_MASS", 8.0))
        self.radius_scale = float(getattr(config, "FOLLOWERS_IO_RADIUS_SCALE", 0.62))
        self.base_speed = float(getattr(config, "FOLLOWERS_IO_BASE_SPEED", 6.0))
        self.speed_exponent = float(getattr(config, "FOLLOWERS_IO_SPEED_EXPONENT", 0.34))
        self.mass_decay_rate = float(getattr(config, "FOLLOWERS_IO_MASS_DECAY_RATE", 0.016))
        self.food_gain_rate = float(getattr(config, "FOLLOWERS_IO_FOOD_GAIN_RATE", 0.20))
        self.absorb_ratio = float(getattr(config, "FOLLOWERS_IO_ABSORB_RATIO", 0.90))
        self.eat_ratio = float(getattr(config, "FOLLOWERS_IO_EAT_RATIO", 1.12))

        self.simplified_threshold = int(getattr(config, "FOLLOWERS_IO_SIMPLIFIED_THRESHOLD", 12000))
        self.collision_full_threshold = int(getattr(config, "FOLLOWERS_IO_COLLISION_FULL_THRESHOLD", 6500))
        self.target_detailed_updates = int(getattr(config, "FOLLOWERS_IO_TARGET_DETAILED_UPDATES", 16000))

        self.random_consumption_rate = float(getattr(config, "FOLLOWERS_IO_RANDOM_CONSUMPTION_RATE", 0.020))
        self.random_consumption_min = int(getattr(config, "FOLLOWERS_IO_RANDOM_CONSUMPTION_MIN", 16))
        self.random_consumption_max = int(getattr(config, "FOLLOWERS_IO_RANDOM_CONSUMPTION_MAX", 1300))
        self.max_detailed_consumptions = int(getattr(config, "FOLLOWERS_IO_MAX_DETAILED_CONSUMPTIONS", 1800))

        self.split_min_mass = float(getattr(config, "FOLLOWERS_IO_SPLIT_MIN_MASS", 92.0))
        self.split_cooldown = float(getattr(config, "FOLLOWERS_IO_SPLIT_COOLDOWN", 2.0))
        self.split_boost_duration = float(getattr(config, "FOLLOWERS_IO_SPLIT_BOOST_DURATION", 0.55))
        self.split_boost_multiplier = float(getattr(config, "FOLLOWERS_IO_SPLIT_BOOST_MULTIPLIER", 1.9))
        self.split_mass_cost_ratio = float(getattr(config, "FOLLOWERS_IO_SPLIT_MASS_COST_RATIO", 0.18))
        self.split_chance_per_second = float(getattr(config, "FOLLOWERS_IO_SPLIT_CHANCE_PER_SECOND", 0.10))

        self.eject_min_mass = float(getattr(config, "FOLLOWERS_IO_EJECT_MIN_MASS", 64.0))
        self.eject_mass_amount = float(getattr(config, "FOLLOWERS_IO_EJECT_MASS_AMOUNT", 2.0))
        self.eject_chance_per_second = float(getattr(config, "FOLLOWERS_IO_EJECT_CHANCE_PER_SECOND", 0.35))
        self.eject_speed = float(getattr(config, "FOLLOWERS_IO_EJECT_SPEED", 7.0))

        self.max_food_particles = int(getattr(config, "FOLLOWERS_IO_MAX_FOOD_PARTICLES", 3000))
        self.food_ttl = float(getattr(config, "FOLLOWERS_IO_FOOD_TTL", 10.0))
        self.food_bank_release_rate = float(getattr(config, "FOLLOWERS_IO_FOOD_BANK_RELEASE_RATE", 90.0))

        self.export_speedup_factor = float(getattr(config, "FOLLOWERS_IO_EXPORT_SPEEDUP_FACTOR", 8.0))
        self.export_speedup_end_alive_count = int(getattr(config, "FOLLOWERS_IO_EXPORT_SPEEDUP_END_ALIVE", 500))
        self.recording_time = 0.0

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
            payload["avatar_image"] = None
            payload["avatar"] = None

            x, y = self.arena.get_random_position(margin=2.0)
            player = IOFollower(
                payload,
                (x, y),
                mass=self.initial_mass * random.uniform(0.9, 1.1),
                radius_scale=self.radius_scale,
            )
            norm_username = normalize_username(username)
            player.is_club_member = norm_username in club_members
            self.players.append(player)

        self.alive_players = list(self.players)
        self.club_spotlight = select_club_spotlight(self.players)
        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def run(self):
        self.setup_players()

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
        if not config.EXPORT_VIDEO:
            return 1.0
        if self.phase != "playing":
            return 1.0
        if len(self.alive_players) <= self.export_speedup_end_alive_count:
            return 1.0
        return max(1.0, self.export_speedup_factor)

    def _compute_detail_stride(self, alive_count: int) -> int:
        if self.target_detailed_updates <= 0:
            return 1
        if alive_count <= self.target_detailed_updates:
            return 1
        return max(1, int(math.ceil(alive_count / float(self.target_detailed_updates))))

    def _update_player_motion(self, player: IOFollower, dt: float, decision_scale: float):
        if self.game_time >= player.next_turn_time:
            angle = random.random() * math.tau
            player.vx = math.cos(angle)
            player.vy = math.sin(angle)
            turn_min = 0.18 * decision_scale
            turn_max = 0.52 * decision_scale
            player.next_turn_time = self.game_time + random.uniform(turn_min, turn_max)

        move_speed = self.base_speed / max(1.0, player.mass ** self.speed_exponent)
        if self.game_time < player.split_boost_end:
            move_speed *= self.split_boost_multiplier

        norm = math.sqrt(player.vx * player.vx + player.vy * player.vy)
        if norm < 1e-6:
            angle = random.random() * math.tau
            player.vx = math.cos(angle)
            player.vy = math.sin(angle)
            norm = 1.0

        vx = (player.vx / norm) * move_speed
        vy = (player.vy / norm) * move_speed

        player.x += vx * dt * 60.0
        player.y += vy * dt * 60.0

        if player.x <= self.arena.left + player.radius:
            player.x = self.arena.left + player.radius
            player.vx = abs(player.vx)
        elif player.x >= self.arena.right - player.radius:
            player.x = self.arena.right - player.radius
            player.vx = -abs(player.vx)

        if player.y <= self.arena.top + player.radius:
            player.y = self.arena.top + player.radius
            player.vy = abs(player.vy)
        elif player.y >= self.arena.bottom - player.radius:
            player.y = self.arena.bottom - player.radius
            player.vy = -abs(player.vy)

    def _fast_motion(self, player: IOFollower, dt: float):
        move_speed = self.base_speed / max(1.0, player.mass ** self.speed_exponent)
        player.x += player.vx * move_speed * dt * 60.0
        player.y += player.vy * move_speed * dt * 60.0
        player.x = max(self.arena.left + player.radius, min(self.arena.right - player.radius, player.x))
        player.y = max(self.arena.top + player.radius, min(self.arena.bottom - player.radius, player.y))

    def _maybe_split_dash(self, player: IOFollower, effective_dt: float, allow_split: bool):
        if not allow_split:
            return
        if not player.can_split(self.game_time, min_mass=self.split_min_mass, cooldown=self.split_cooldown):
            return
        chance = max(0.0, self.split_chance_per_second * effective_dt)
        if random.random() >= chance:
            return
        player.trigger_split_dash(
            game_time=self.game_time,
            boost_duration=self.split_boost_duration,
            mass_cost_ratio=self.split_mass_cost_ratio,
            min_mass=self.min_mass,
            radius_scale=self.radius_scale,
        )

    def _maybe_eject_mass(self, player: IOFollower, effective_dt: float, simplified_mode: bool):
        if player.mass < self.eject_min_mass:
            return
        chance = max(0.0, self.eject_chance_per_second * effective_dt)
        if random.random() >= chance:
            return

        amount = min(self.eject_mass_amount, max(0.0, player.mass - self.min_mass))
        if amount <= 0.0:
            return
        player.lose_mass(amount, min_mass=self.min_mass, radius_scale=self.radius_scale)

        if simplified_mode:
            self.food_bank += amount
            return

        if len(self.food_particles) >= self.max_food_particles:
            return

        norm = math.sqrt(player.vx * player.vx + player.vy * player.vy)
        if norm < 1e-6:
            angle = random.random() * math.tau
            dx = math.cos(angle)
            dy = math.sin(angle)
        else:
            dx = player.vx / norm
            dy = player.vy / norm

        spawn_x = player.x + dx * max(2.0, player.radius * 0.75)
        spawn_y = player.y + dy * max(2.0, player.radius * 0.75)
        self.food_particles.append(
            FoodParticle(
                x=spawn_x,
                y=spawn_y,
                vx=dx * self.eject_speed,
                vy=dy * self.eject_speed,
                mass=amount,
                ttl=self.food_ttl,
            )
        )

    def _consume(self, killer: IOFollower, victim: IOFollower):
        if not killer.alive or not victim.alive:
            return False
        if killer is victim:
            return False

        gained_mass = victim.mass * self.absorb_ratio
        killer.gain_mass(gained_mass, radius_scale=self.radius_scale)
        killer.kills += 1
        killer.consumed_mass += victim.mass

        victim.mark_eliminated(step=self.sim_step, game_time=self.game_time)
        self.total_consumptions += 1
        self._pending_compaction += 1

        if victim.username:
            self.recent_eliminations.insert(0, victim.username)
            if len(self.recent_eliminations) > self.max_recent_eliminations:
                self.recent_eliminations.pop()
        return True

    def _compact_alive_players(self, force: bool = False):
        if not force and self._pending_compaction < 96:
            return
        self.alive_players = [p for p in self.alive_players if p.alive]
        self._pending_compaction = 0

    def _build_spatial_grid(self) -> Dict[tuple[int, int], List[IOFollower]]:
        if not self.alive_players:
            return {}
        max_radius = max(1.0, max(p.radius for p in self.alive_players))
        self._grid_cell_size = max(8, int(max_radius * 2.8))
        grid: Dict[tuple[int, int], List[IOFollower]] = {}
        for player in self.alive_players:
            cx = int(player.x // self._grid_cell_size)
            cy = int(player.y // self._grid_cell_size)
            key = (cx, cy)
            if key not in grid:
                grid[key] = []
            grid[key].append(player)
        return grid

    def _update_food_particles(self, dt: float):
        if not self.food_particles:
            return
        kept: List[FoodParticle] = []
        for food in self.food_particles:
            food.x += food.vx * dt * 60.0
            food.y += food.vy * dt * 60.0
            food.ttl -= dt

            if food.x <= self.arena.left:
                food.x = self.arena.left
                food.vx = abs(food.vx) * 0.5
            elif food.x >= self.arena.right:
                food.x = self.arena.right
                food.vx = -abs(food.vx) * 0.5

            if food.y <= self.arena.top:
                food.y = self.arena.top
                food.vy = abs(food.vy) * 0.5
            elif food.y >= self.arena.bottom:
                food.y = self.arena.bottom
                food.vy = -abs(food.vy) * 0.5

            if food.ttl > 0.0 and food.mass > 0.05:
                kept.append(food)
            else:
                self.food_bank += max(0.0, food.mass * 0.35)
        self.food_particles = kept

    def _consume_food_for_player(self, player: IOFollower, max_checks: int = 14):
        if not self.food_particles:
            return
        checks = min(max_checks, len(self.food_particles))
        if checks <= 0:
            return

        eaten_indices = []
        for _ in range(checks):
            idx = random.randrange(len(self.food_particles))
            food = self.food_particles[idx]
            dx = player.x - food.x
            dy = player.y - food.y
            threshold = max(1.0, player.radius)
            if dx * dx + dy * dy <= threshold * threshold:
                eaten_indices.append(idx)
                player.gain_mass(food.mass, radius_scale=self.radius_scale)

        if eaten_indices:
            for idx in sorted(set(eaten_indices), reverse=True):
                if 0 <= idx < len(self.food_particles):
                    self.food_particles.pop(idx)

    def _release_food_bank(self, updated_players: List[IOFollower], effective_dt: float):
        if self.food_bank <= 0.0 or not updated_players:
            return
        release = min(self.food_bank, self.food_bank_release_rate * effective_dt)
        self.food_bank -= release
        per_player = release / len(updated_players)
        if per_player <= 0.0:
            return
        for player in updated_players:
            player.gain_mass(per_player, radius_scale=self.radius_scale)

    def _update_simplified(self, dt: float):
        alive_count = len(self.alive_players)
        detail_stride = self._compute_detail_stride(alive_count)
        self._last_detail_stride = detail_stride
        decision_scale = min(3.8, 1.0 + (detail_stride - 1) * 0.45)

        updated_players: List[IOFollower] = []
        for idx, player in enumerate(self.alive_players):
            if not player.alive:
                continue
            if detail_stride <= 1 or ((idx + self._detail_update_phase) % detail_stride == 0):
                effective_dt = dt * detail_stride
                self._update_player_motion(player, dt, decision_scale=decision_scale)
                player.apply_mass_decay(
                    effective_dt,
                    decay_rate=self.mass_decay_rate,
                    min_mass=self.min_mass,
                    radius_scale=self.radius_scale,
                )
                player.gain_mass(
                    self.food_gain_rate * effective_dt * random.uniform(0.7, 1.4),
                    radius_scale=self.radius_scale,
                )
                self._maybe_split_dash(player, effective_dt, allow_split=True)
                self._maybe_eject_mass(player, effective_dt, simplified_mode=True)
                updated_players.append(player)
            else:
                self._fast_motion(player, dt)

        if detail_stride > 1:
            self._detail_update_phase = (self._detail_update_phase + 1) % detail_stride
        else:
            self._detail_update_phase = 0

        self._release_food_bank(updated_players, dt * detail_stride)

        if alive_count <= 1:
            return

        pop_scale = max(0.0, (alive_count - self.simplified_threshold) / max(1.0, float(self.simplified_threshold)))
        rate = self.random_consumption_rate * (1.0 + pop_scale * 0.75)
        expected = alive_count * rate * dt
        consumptions = int(expected)
        if random.random() < (expected - consumptions):
            consumptions += 1
        consumptions = max(self.random_consumption_min, consumptions)
        consumptions = min(consumptions, self.random_consumption_max, alive_count - 1)

        for _ in range(consumptions):
            if len(self.alive_players) <= 1:
                break
            sample_victims = random.sample(self.alive_players, min(3, len(self.alive_players)))
            sample_killers = random.sample(self.alive_players, min(4, len(self.alive_players)))
            victim = min(sample_victims, key=lambda p: p.mass)
            killer = max(sample_killers, key=lambda p: p.mass)
            if victim is killer:
                alternatives = [p for p in sample_killers if p is not victim]
                if not alternatives:
                    continue
                killer = max(alternatives, key=lambda p: p.mass)
            if killer.mass <= victim.mass * self.eat_ratio:
                continue
            self._consume(killer, victim)

        self._compact_alive_players()

    def _update_detailed(self, dt: float):
        alive_count = len(self.alive_players)
        detail_stride = self._compute_detail_stride(alive_count)
        self._last_detail_stride = detail_stride
        updated_players: List[IOFollower] = []

        for idx, player in enumerate(self.alive_players):
            if not player.alive:
                continue
            if detail_stride <= 1 or ((idx + self._detail_update_phase) % detail_stride == 0):
                effective_dt = dt * detail_stride
                self._update_player_motion(player, dt, decision_scale=1.0)
                player.apply_mass_decay(
                    effective_dt,
                    decay_rate=self.mass_decay_rate,
                    min_mass=self.min_mass,
                    radius_scale=self.radius_scale,
                )
                player.gain_mass(
                    self.food_gain_rate * effective_dt * random.uniform(0.8, 1.3),
                    radius_scale=self.radius_scale,
                )
                self._maybe_split_dash(player, effective_dt, allow_split=True)
                self._maybe_eject_mass(player, effective_dt, simplified_mode=False)
                updated_players.append(player)
            else:
                self._fast_motion(player, dt)

        if detail_stride > 1:
            self._detail_update_phase = (self._detail_update_phase + 1) % detail_stride
        else:
            self._detail_update_phase = 0

        self._update_food_particles(dt)
        self._release_food_bank(updated_players, dt * detail_stride)

        if not self.alive_players:
            return

        grid = self._build_spatial_grid()
        candidates = self.alive_players if alive_count <= self.collision_full_threshold else updated_players

        consumed_this_frame = 0
        for eater in candidates:
            if not eater.alive:
                continue

            self._consume_food_for_player(eater)

            cell_x = int(eater.x // max(1, self._grid_cell_size))
            cell_y = int(eater.y // max(1, self._grid_cell_size))
            found_target = False

            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    key = (cell_x + dx, cell_y + dy)
                    nearby = grid.get(key)
                    if not nearby:
                        continue
                    for other in nearby:
                        if other is eater or not other.alive:
                            continue
                        if eater.mass <= other.mass * self.eat_ratio:
                            continue
                        consume_radius = max(1.0, eater.radius - other.radius * 0.35)
                        diff_x = eater.x - other.x
                        diff_y = eater.y - other.y
                        if diff_x * diff_x + diff_y * diff_y <= consume_radius * consume_radius:
                            if self._consume(eater, other):
                                consumed_this_frame += 1
                                found_target = True
                            break
                    if found_target:
                        break
                if found_target:
                    break

            if consumed_this_frame >= self.max_detailed_consumptions:
                break

        self._compact_alive_players()

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt
        self.sim_step += 1
        self.sound.update_music_volume()

        if self.alive_players:
            if len(self.alive_players) > self.simplified_threshold:
                self._update_simplified(dt)
            else:
                self._update_detailed(dt)

        if self.alive_players:
            speed_multiplier = self._get_recording_speed_multiplier()
            self.recording_time += dt / max(1.0, speed_multiplier)
        else:
            self.recording_time += dt

        if len(self.alive_players) <= 1 or self.game_time >= self.max_game_time:
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

    def render(self):
        alive_count = len(self.alive_players)
        speedup_factor = self._get_recording_speed_multiplier()
        game_state = {
            "phase": self.phase,
            "alive_count": alive_count,
            "total_count": len(self.players),
            "elapsed_time": self.game_time,
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
        }
        self.renderer.render_frame(self.players, game_state)
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
