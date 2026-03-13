"""
Meteor Mayhem (Dodge Royale)
Top-down arena where meteors rain randomly; players bump and try to stay out of impact zones
while a shrinking safe circle squeezes them together.
"""

import math
import os
import random
import time
from dataclasses import dataclass
from typing import List, Tuple

import pygame
from PIL import Image

import config
from shared import (
    InstagramAPI,
    SoundManager,
    VideoRecorder,
    PlayerStatistics,
    ScoringSystem,
    GameHistory,
    AudioLogger,
    auto_push,
)
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight
from shared.club_panel import draw_club_panel
from shared.avatar_initials import draw_avatar_initials


@dataclass
class Meteor:
    x: float
    y: float
    target_x: float
    target_y: float
    speed: float
    radius: float
    impact_radius: float

    def update(self, dt: float) -> bool:
        """Move toward target; return True if impacted."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist <= self.speed * dt or dist < 1e-3:
            self.x, self.y = self.target_x, self.target_y
            return True

        step = self.speed * dt
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step
        return False


@dataclass
class Explosion:
    x: float
    y: float
    radius: float
    timer: float = 0.0
    duration: float = 0.7

    def update(self, dt: float) -> bool:
        """Advance timer; return True if expired."""
        self.timer += dt
        return self.timer >= self.duration

    @property
    def progress(self) -> float:
        return min(1.0, self.timer / self.duration)


class MeteorPlayer:
    def __init__(
        self,
        player_id: str,
        username: str,
        display_name: str,
        color: Tuple[int, int, int],
        avatar_image=None
    ):
        self.id = player_id
        self.username = username
        self.display_name = display_name
        self.avatar_image = avatar_image
        self.color = color
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.radius = 15
        self.alive = True
        self.placement = None
        self.elimination_time = None
        self.surface_needs_update = True
        self.wander_angle = random.random() * math.pi * 2
        self.wander_timer = 0.0
        self.wander_interval = random.uniform(0.6, 1.4)

    def set_spawn(self, x: float, y: float):
        self.x = x
        self.y = y

    def apply_input(self, direction: Tuple[float, float], speed: float, dt: float):
        dx, dy = direction
        self.vx += dx * speed * dt
        self.vy += dy * speed * dt

    def update(self, dt: float):
        # Dampen velocity for smooth drift
        self.vx *= 0.93
        self.vy *= 0.93
        self.x += self.vx * dt
        self.y += self.vy * dt


class MeteorMayhemGame:
    """Main game orchestrator."""

    def __init__(self):
        print("=" * 60)
        print("  METEOR MAYHEM - DODGE ROYALE")
        print("=" * 60)

        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Meteor Mayhem")
        self.clock = pygame.time.Clock()
        pygame.font.init()
        self.width = config.SCREEN_WIDTH
        self.height = config.SCREEN_HEIGHT

        # Shared systems
        self.api = InstagramAPI()
        self.sound = SoundManager()
        self.audio_logger = AudioLogger()
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.0,
            offset_y=0
        )
        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()
        self.game_history = GameHistory()

        self.sound.preload_audio()

        # Game state
        self.players: List[MeteorPlayer] = []
        self.meteors: List[Meteor] = []
        self.explosions: List[Explosion] = []
        self.player_surfaces = {}
        self.cached_radius = {}
        self._club_glow_cache = {}
        self.club_spotlight = None
        self.running = True
        self.game_over = False
        self.phase = "intro"  # intro -> countdown -> playing -> finished
        self.game_time = 0.0
        self.phase_start_time = time.time()
        self.countdown_number = 3
        self.winner_display_time = 4.0
        self.winner_display_started = None

        # Arena and pacing
        self.center = (config.SCREEN_WIDTH / 2, config.SCREEN_HEIGHT / 2 + 20)
        self.safe_radius = config.METEOR_ZONE_INITIAL_RADIUS
        self.initial_safe_radius = config.METEOR_ZONE_INITIAL_RADIUS
        self.target_safe_radius = config.METEOR_ZONE_INITIAL_RADIUS
        self.last_spawn_time = 0.0
        self.next_spawn_delay = 0.0
        self.meteor_impact_count = 0
        self.player_radius = 15
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

        # Fonts
        self.font_title = pygame.font.Font(None, 56)
        self.font_subtitle = pygame.font.Font(None, 32)
        self.font_day = pygame.font.Font(None, 36)
        self.font_stats = pygame.font.Font(None, 28)
        self.font_big = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 18)
        self.font_mini = pygame.font.Font(None, 14)
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self.font_promo = pygame.font.Font(None, 24)
        self.promo_text_left = "Join Discord, link in bio"
        self.promo_text_right = "Check your results in bio"
        self.discord_logo = None
        self.trophy_logo = None
        self._load_promo_assets()
        self._schedule_next_spawn()

        print("Meteor Mayhem initialized!\n")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def load_players(self):
        print(f"Spawning followers for Meteor Mayhem...")
        if config.TEST_MINIMAL_PLAYERS:
            print(f"🧪 TEST MODE: Using {config.TEST_MINIMAL_PLAYER_COUNT} test players")
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)
        self.player_surfaces.clear()
        self.cached_radius.clear()
        colors = config.METEOR_PLAYER_COLORS
        color_count = len(colors)
        club_members = load_club_member_set()

        for idx, data in enumerate(follower_data):
            player_id = data.get('id') or f"meteor_{idx}"
            color = data.get('color')
            if color is None:
                color = colors[idx % color_count] if color_count else (200, 200, 200)
            p = MeteorPlayer(
                player_id=player_id,
                username=data['username'],
                display_name=data.get('display_name', data['username']),
                color=color,
                avatar_image=data.get('avatar')
            )
            username = normalize_username(data.get("username"))
            p.is_club_member = username in club_members

            # Spawn within the current safe zone
            angle = random.random() * math.pi * 2
            dist = random.random() * (self.safe_radius - 20)
            spawn_x = self.center[0] + math.cos(angle) * dist
            spawn_y = self.center[1] + math.sin(angle) * dist
            p.set_spawn(spawn_x, spawn_y)
            self.players.append(p)

        self.club_spotlight = select_club_spotlight(self.players)
        print(f"  Spawned {len(self.players)} players\n")

    # ------------------------------------------------------------------
    # Game logic
    # ------------------------------------------------------------------
    def _current_spawn_interval(self) -> Tuple[float, float]:
        start_min, start_max = config.METEOR_SPAWN_INTERVAL
        end_min, end_max = getattr(
            config,
            'METEOR_SPAWN_INTERVAL_MIN',
            (start_min * 0.5, start_max * 0.5)
        )
        ramp_duration = getattr(config, 'METEOR_SPAWN_RAMP_DURATION', 60.0)
        if ramp_duration <= 0:
            progress = 1.0
        else:
            progress = min(self.game_time / ramp_duration, 1.0)

        current_min = start_min + (end_min - start_min) * progress
        current_max = start_max + (end_max - start_max) * progress
        frequency_multiplier = 1.25
        current_min = current_min / frequency_multiplier
        current_max = current_max / frequency_multiplier
        current_min = max(0.05, current_min)
        current_max = max(current_min, current_max)
        return current_min, current_max

    def _schedule_next_spawn(self):
        min_delay, max_delay = self._current_spawn_interval()
        self.next_spawn_delay = random.uniform(min_delay, max_delay)

    def _impact_radius_bonus(self) -> float:
        return (self.meteor_impact_count // 10) * 3

    def spawn_meteor(self):
        angle = random.random() * math.pi * 2
        dist = random.random() * (self.safe_radius * 0.9)
        target_x = self.center[0] + math.cos(angle) * dist
        target_y = self.center[1] + math.sin(angle) * dist

        start_x = target_x + random.uniform(-60, 60)
        start_y = -40.0

        speed = random.uniform(*config.METEOR_FALL_SPEED)
        radius = random.uniform(*config.METEOR_RADIUS)
        impact_radius = random.uniform(*config.METEOR_IMPACT_RADIUS) + self._impact_radius_bonus()

        self.meteors.append(Meteor(start_x, start_y, target_x, target_y, speed, radius, impact_radius))
        self.last_spawn_time = self.game_time
        self._schedule_next_spawn()

    def update_meteors(self, dt: float):
        impacts = []
        remaining = []
        for meteor in self.meteors:
            impacted = meteor.update(dt)
            if impacted:
                impacts.append(meteor)
            else:
                remaining.append(meteor)
        self.meteors = remaining

        for meteor in impacts:
            self.meteor_impact_count += 1
            self.explosions.append(Explosion(meteor.target_x, meteor.target_y, meteor.impact_radius))
            self.handle_meteor_impact(meteor)

    def handle_meteor_impact(self, meteor: Meteor):
        for player in self.players:
            if not player.alive:
                continue
            dx = player.x - meteor.target_x
            dy = player.y - meteor.target_y
            dist = math.hypot(dx, dy)
            if dist <= meteor.impact_radius + player.radius:
                player.alive = False
                player.elimination_time = self.game_time
                player.placement = len([p for p in self.players if p.alive]) + 1
                if player.placement <= 10:
                    self.sound.play_elimination()

    def update_explosions(self, dt: float):
        self.explosions = [exp for exp in self.explosions if not exp.update(dt)]

    def shrink_zone(self, dt: float):
        if self.safe_radius > config.METEOR_ZONE_MIN_RADIUS:
            self.safe_radius = max(
                config.METEOR_ZONE_MIN_RADIUS,
                self.safe_radius - config.METEOR_ZONE_SHRINK_RATE * dt
            )

    def apply_player_ai(self, dt: float):
        for player in self.players:
            if not player.alive:
                continue

            # Avoid nearest incoming meteor target
            threat = None
            threat_dist = 9999
            for meteor in self.meteors:
                dx = player.x - meteor.target_x
                dy = player.y - meteor.target_y
                dist = math.hypot(dx, dy)
                if dist < threat_dist:
                    threat_dist = dist
                    threat = meteor

            move_x = 0.0
            move_y = 0.0

            if threat and threat_dist < 90:
                # Run away from impact point
                dx = player.x - threat.target_x
                dy = player.y - threat.target_y
                dist = math.hypot(dx, dy) or 1.0
                move_x += dx / dist
                move_y += dy / dist
            else:
                # Wander in a steady direction and refresh periodically
                player.wander_timer += dt
                if player.wander_timer >= player.wander_interval:
                    player.wander_angle = random.random() * math.pi * 2
                    player.wander_timer = 0.0
                    player.wander_interval = random.uniform(0.6, 1.4)
                move_x += math.cos(player.wander_angle)
                move_y += math.sin(player.wander_angle)

            # Add jitter so paths differ
            move_x += random.uniform(-config.METEOR_PLAYER_JITTER, config.METEOR_PLAYER_JITTER)
            move_y += random.uniform(-config.METEOR_PLAYER_JITTER, config.METEOR_PLAYER_JITTER)

            norm = math.hypot(move_x, move_y) or 1.0
            direction = (move_x / norm, move_y / norm)
            player.apply_input(direction, config.METEOR_PLAYER_SPEED, dt)

    def resolve_collisions(self):
        alive_players = [p for p in self.players if p.alive]
        for i in range(len(alive_players)):
            for j in range(i + 1, len(alive_players)):
                a = alive_players[i]
                b = alive_players[j]
                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy)
                min_dist = a.radius + b.radius
                if dist < min_dist and dist > 0:
                    overlap = min_dist - dist
                    push = overlap / 2
                    nx = dx / dist
                    ny = dy / dist
                    a.x -= nx * push
                    a.y -= ny * push
                    b.x += nx * push
                    b.y += ny * push
                    # Apply small velocity bump
                    a.vx -= nx * config.METEOR_PUSH_FORCE * 0.1
                    a.vy -= ny * config.METEOR_PUSH_FORCE * 0.1
                    b.vx += nx * config.METEOR_PUSH_FORCE * 0.1
                    b.vy += ny * config.METEOR_PUSH_FORCE * 0.1

    def clamp_players_to_zone(self):
        for player in self.players:
            if not player.alive:
                continue
            dx = player.x - self.center[0]
            dy = player.y - self.center[1]
            dist = math.hypot(dx, dy)
            max_dist = self.safe_radius - player.radius
            if dist > max_dist and dist > 0:
                player.x = self.center[0] + dx / dist * max_dist
                player.y = self.center[1] + dy / dist * max_dist

    def update_players(self, dt: float):
        self.apply_player_ai(dt)
        for player in self.players:
            if player.alive:
                player.update(dt)
        self.clamp_players_to_zone()

    def check_game_over(self):
        alive = [p for p in self.players if p.alive]
        if len(alive) <= 1 and self.phase == "playing":
            self.phase = "finished"
            if len(alive) == 1:
                alive[0].placement = 1
                alive[0].elimination_time = self.game_time
                print(f"Winner: {alive[0].display_name}")
                self.sound.play_winner_celebration()
            self._calculate_leaderboard_for_display()
            self.winner_display_started = time.time()

    def _calculate_leaderboard_for_display(self):
        results = self.get_results()
        scored_results = []
        for result in results:
            scored_results.append({
                "username": result["username"],
                "display_name": result["display_name"],
                "placement": result["placement"],
                "score": result["score"]
            })
        self.current_game_leaderboard = self.scoring.calculate_scores(
            results=scored_results,
            game_mode="meteor_mayhem"
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw_zone(self):
        initial_radius = int(self.initial_safe_radius)
        pygame.draw.circle(self.screen, config.COLOR_ARENA, self.center, initial_radius)

        if self.safe_radius < self.initial_safe_radius:
            danger_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.circle(
                danger_surface,
                (*config.COLOR_DANGER_ZONE, 200),
                self.center,
                initial_radius
            )
            pygame.draw.circle(
                danger_surface,
                (0, 0, 0, 0),
                self.center,
                int(self.safe_radius)
            )
            self.screen.blit(danger_surface, (0, 0))

        pygame.draw.circle(self.screen, config.COLOR_BORDER, self.center, initial_radius, 4)

    def draw_meteors(self):
        effects_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        for meteor in self.meteors:
            visual_radius = max(2, int(meteor.radius * 1.6))

            # Impact pre-visual (soft ring)
            impact_radius = int(meteor.impact_radius)
            impact_surface = pygame.Surface((impact_radius * 2, impact_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                impact_surface,
                (*config.METEOR_IMPACT_COLOR, 40),
                (impact_radius, impact_radius),
                impact_radius,
                width=4,
            )
            effects_surface.blit(
                impact_surface,
                (meteor.target_x - impact_radius, meteor.target_y - impact_radius)
            )

            # Fire trail behind meteor
            dx = meteor.x - meteor.target_x
            dy = meteor.y - meteor.target_y
            dist = math.hypot(dx, dy)
            if dist > 1e-3:
                ux = dx / dist
                uy = dy / dist
            else:
                ux, uy = 0.0, -1.0

            flame_length = visual_radius * 4.2
            flame_steps = 6
            inner = (255, 235, 180)
            outer = (255, 90, 20)
            for i in range(flame_steps):
                t = i / (flame_steps - 1) if flame_steps > 1 else 1.0
                radius = visual_radius * (1.2 - t * 0.8)
                alpha = int(190 * (1 - t) + 20)
                r = int(inner[0] + (outer[0] - inner[0]) * t)
                g = int(inner[1] + (outer[1] - inner[1]) * t)
                b = int(inner[2] + (outer[2] - inner[2]) * t)
                pos_x = meteor.x + ux * flame_length * t
                pos_y = meteor.y + uy * flame_length * t
                pygame.draw.circle(
                    effects_surface,
                    (r, g, b, alpha),
                    (int(pos_x), int(pos_y)),
                    max(1, int(radius))
                )

            # Soft glow around meteor
            pygame.draw.circle(
                effects_surface,
                (*config.METEOR_IMPACT_COLOR, 80),
                (int(meteor.x), int(meteor.y)),
                max(1, int(visual_radius * 1.8))
            )

        self.screen.blit(effects_surface, (0, 0))

        for meteor in self.meteors:
            visual_radius = max(2, int(meteor.radius * 1.6))
            base_color = config.METEOR_COLOR
            rim_color = self._shade_color(config.METEOR_IMPACT_COLOR, 0.9)
            core_color = self._shade_color(base_color, 1.2)
            dark_color = self._shade_color(base_color, 0.6)

            pygame.draw.circle(self.screen, base_color, (int(meteor.x), int(meteor.y)), visual_radius)
            pygame.draw.circle(
                self.screen,
                rim_color,
                (int(meteor.x), int(meteor.y)),
                visual_radius,
                max(1, int(visual_radius * 0.12))
            )
            pygame.draw.circle(
                self.screen,
                core_color,
                (int(meteor.x), int(meteor.y)),
                max(1, int(visual_radius * 0.6))
            )

            seed = (int(meteor.target_x) * 73856093) ^ (int(meteor.target_y) * 19349663)
            rng = random.Random(seed)
            for _ in range(3):
                offset_x = rng.uniform(-0.35, 0.35) * visual_radius
                offset_y = rng.uniform(-0.35, 0.35) * visual_radius
                crater_radius = max(1, int(visual_radius * rng.uniform(0.12, 0.2)))
                pygame.draw.circle(
                    self.screen,
                    dark_color,
                    (int(meteor.x + offset_x), int(meteor.y + offset_y)),
                    crater_radius
                )

            highlight = (255, 220, 150)
            hx = int(meteor.x + rng.uniform(-0.15, 0.15) * visual_radius)
            hy = int(meteor.y + rng.uniform(-0.15, 0.15) * visual_radius)
            pygame.draw.circle(
                self.screen,
                highlight,
                (hx, hy),
                max(1, int(visual_radius * 0.18))
            )
        for exp in self.explosions:
            alpha = 255 * (1 - exp.progress)
            radius = exp.radius * (0.5 + 0.8 * exp.progress)
            surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*config.METEOR_IMPACT_COLOR, int(alpha)), (int(radius), int(radius)), int(radius), 3)
            self.screen.blit(surface, (exp.x - radius, exp.y - radius))

    def _shade_color(self, color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
        return tuple(max(0, min(255, int(c * factor))) for c in color)

    def draw_players(self):
        club_players = []
        for player in self.players:
            if not player.alive:
                continue
            if getattr(player, "is_club_member", False):
                club_players.append(player)
            else:
                self._draw_player(player)

        for player in club_players:
            self._draw_club_glow(player)
            self._draw_player(player)

    def _draw_player(self, player: MeteorPlayer):
        surface = self._get_player_surface(player)
        display_size = max(1, int(player.radius * 2))
        if surface.get_width() != display_size:
            display_surface = pygame.transform.smoothscale(surface, (display_size, display_size))
        else:
            display_surface = surface
        rect = display_surface.get_rect(center=(int(player.x), int(player.y)))
        self.screen.blit(display_surface, rect)

    def _draw_club_glow(self, player: MeteorPlayer):
        size = max(1, int(round(player.radius * 2)))
        radius = max(1, size // 2)
        color = getattr(config, "CLUB_GLOW_COLOR", (255, 240, 190))
        alpha = int(getattr(config, "CLUB_GLOW_ALPHA", 180))
        layers = int(getattr(config, "CLUB_GLOW_LAYERS", 3))
        padding = int(getattr(config, "CLUB_GLOW_PADDING", 3))

        cache_key = (radius, color, alpha, layers, padding)
        surface = self._club_glow_cache.get(cache_key)
        if surface is None:
            glow_radius = radius + padding + layers
            size_px = glow_radius * 2 + 4
            surface = pygame.Surface((size_px, size_px), pygame.SRCALPHA)
            center = (size_px // 2, size_px // 2)

            base_radius = radius + padding
            for i in range(max(1, layers)):
                layer_alpha = int(alpha * (1.0 - (i / max(1, layers))))
                ring_radius = base_radius + i
                pygame.draw.circle(
                    surface,
                    (*color, layer_alpha),
                    center,
                    ring_radius,
                    width=2,
                )

            inner_alpha = min(255, alpha + 40)
            pygame.draw.circle(
                surface,
                (*color, inner_alpha),
                center,
                radius + 1,
                width=2,
            )

            self._club_glow_cache[cache_key] = surface

        rect = surface.get_rect(center=(int(player.x), int(player.y)))
        self.screen.blit(surface, rect)

    def _get_player_surface(self, player: MeteorPlayer) -> pygame.Surface:
        cache_key = (player.id, player.username)
        cache_valid = (
            cache_key in self.player_surfaces
            and not player.surface_needs_update
            and cache_key in self.cached_radius
            and abs(self.cached_radius[cache_key] - player.radius) < 0.01
        )
        if cache_valid:
            return self.player_surfaces[cache_key]

        size = max(1, int(player.radius * 2))
        radius = max(1, int(player.radius))
        upscale_multiplier = (
            getattr(config, 'UPSCALE_FACTOR', 1.0)
            if getattr(config, 'UPSCALE_VIDEO', False)
            else 1.0
        )
        render_size = max(1, int(size * upscale_multiplier))
        render_radius = max(1, int(radius * upscale_multiplier))
        surface = pygame.Surface((render_size, render_size), pygame.SRCALPHA)

        border_width = max(1, int(config.FOLLOWER_BORDER_WIDTH * upscale_multiplier))
        inner_radius = max(1, render_radius - border_width)
        is_club_member = getattr(player, "is_club_member", False)
        show_profile_pic = is_club_member or player.radius >= getattr(config, 'PROFILE_PICTURE_MIN_RADIUS', 0)

        if player.avatar_image and show_profile_pic:
            avatar_surface = self._pil_to_pygame(player.avatar_image, render_size)
            self._draw_circular_image(surface, avatar_surface, render_radius, border_width)
        else:
            pygame.draw.circle(
                surface,
                player.color,
                (render_radius, render_radius),
                inner_radius
            )
            draw_avatar_initials(
                surface,
                player.username,
                center=(render_radius, render_radius),
                diameter=render_size,
            )

        pygame.draw.circle(
            surface,
            config.COLOR_BORDER,
            (render_radius, render_radius),
            render_radius,
            border_width
        )

        self.player_surfaces[cache_key] = surface
        self.cached_radius[cache_key] = player.radius
        player.surface_needs_update = False

        return surface

    def _get_club_panel_avatar(self, player: MeteorPlayer, size: int) -> pygame.Surface:
        surface = self._get_player_surface(player)
        target = int(size)
        if surface.get_width() != target:
            surface = pygame.transform.smoothscale(surface, (target, target))
        return surface

    def _draw_circular_image(self, surface: pygame.Surface,
                             image_surface: pygame.Surface, radius: int, border_width: int):
        inner_radius = max(1, radius - border_width)
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius), inner_radius)
        scaled_image = pygame.transform.smoothscale(image_surface, (radius * 2, radius * 2))
        scaled_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(scaled_image, (0, 0))

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
        pil_image = pil_image.resize((size, size), resample)
        mode = pil_image.mode
        data = pil_image.tobytes()
        surface = pygame.image.fromstring(data, pil_image.size, mode)
        return surface.convert_alpha()

    def _load_promo_assets(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        discord_path = os.path.join(base_dir, "discord_logo.png")
        self.discord_logo = self._load_logo([discord_path])

        trophy_paths = [
            os.path.join(base_dir, "trophy.png"),
            os.path.join(base_dir, "trophy_icon.png"),
            os.path.join(base_dir, "assets", "trophy.png"),
            os.path.join(base_dir, "website", "src", "assets", "trophy.png"),
            os.path.join(base_dir, "website", "public", "trophy.png"),
            os.path.join(base_dir, "website", "dist", "trophy.png"),
        ]
        self.trophy_logo = self._load_logo(trophy_paths)

    def _load_logo(self, paths: List[str]):
        target_height = max(16, int(self.font_promo.get_height() * 1.2))
        for logo_path in paths:
            if not os.path.exists(logo_path):
                continue
            try:
                logo = pygame.image.load(logo_path).convert_alpha()
                if logo.get_height() <= 0:
                    return None
                scale = target_height / logo.get_height()
                target_width = max(1, int(logo.get_width() * scale))
                return pygame.transform.smoothscale(logo, (target_width, target_height))
            except Exception:
                return None
        return None

    def _get_pill_size(self, text: str, logo_surface):
        text_surface = self.font_promo.render(text, True, (245, 245, 245))
        text_width, text_height = text_surface.get_size()

        logo_width = logo_surface.get_width() if logo_surface else 0
        logo_height = logo_surface.get_height() if logo_surface else 0

        gap = 8 if logo_surface else 0
        padding_x = 16
        padding_y = 8

        content_width = text_width + logo_width + gap
        content_height = max(text_height, logo_height)
        pill_width = content_width + padding_x * 2
        pill_height = content_height + padding_y * 2

        return pill_width, pill_height

    def _draw_pill(self, text: str, logo_surface, center_pos: Tuple[int, int]):
        text_surface = self.font_promo.render(text, True, (245, 245, 245))
        text_width, text_height = text_surface.get_size()

        logo_width = logo_surface.get_width() if logo_surface else 0
        logo_height = logo_surface.get_height() if logo_surface else 0

        gap = 8 if logo_surface else 0
        padding_x = 16
        padding_y = 8

        content_width = text_width + logo_width + gap
        content_height = max(text_height, logo_height)
        pill_width = content_width + padding_x * 2
        pill_height = content_height + padding_y * 2

        pill_rect = pygame.Rect(0, 0, pill_width, pill_height)
        pill_rect.center = center_pos

        shadow_surface = pygame.Surface((pill_width, pill_height), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surface,
            (0, 0, 0, 90),
            shadow_surface.get_rect(),
            border_radius=pill_height // 2
        )
        self.screen.blit(shadow_surface, (pill_rect.x + 2, pill_rect.y + 2))

        pill_surface = pygame.Surface((pill_width, pill_height), pygame.SRCALPHA)
        pygame.draw.rect(
            pill_surface,
            (30, 30, 35, 210),
            pill_surface.get_rect(),
            border_radius=pill_height // 2
        )
        pygame.draw.rect(
            pill_surface,
            (200, 200, 200, 40),
            pill_surface.get_rect(),
            width=1,
            border_radius=pill_height // 2
        )
        self.screen.blit(pill_surface, pill_rect.topleft)

        content_x = pill_rect.x + padding_x
        if logo_surface:
            logo_y = pill_rect.y + (pill_height - logo_height) // 2
            self.screen.blit(logo_surface, (content_x, logo_y))
            content_x += logo_width + gap

        text_center_y = pill_rect.y + pill_height // 2
        shadow_text = self.font_promo.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(midleft=(content_x, text_center_y))
        self.screen.blit(shadow_text, shadow_rect.move(1, 1))

        text_rect = text_surface.get_rect(midleft=(content_x, text_center_y))
        self.screen.blit(text_surface, text_rect)

    def _draw_promo_overlay(self):
        base_y = self.height - 28
        gap_between = 12
        margin_x = 24

        left_width, left_height = self._get_pill_size(self.promo_text_left, self.discord_logo)
        right_width, right_height = self._get_pill_size(self.promo_text_right, self.trophy_logo)

        left_center = (margin_x + left_width // 2, base_y)
        right_center = (self.width - margin_x - right_width // 2, base_y)

        left_rect = pygame.Rect(0, 0, left_width, left_height)
        left_rect.center = left_center
        right_rect = pygame.Rect(0, 0, right_width, right_height)
        right_rect.center = right_center

        if left_rect.right + gap_between > right_rect.left:
            total_width = left_width + right_width + gap_between
            start_x = (self.width - total_width) // 2
            left_center = (start_x + left_width // 2, base_y)
            right_center = (start_x + left_width + gap_between + right_width // 2, base_y)

        self._draw_pill(self.promo_text_left, self.discord_logo, left_center)
        self._draw_pill(self.promo_text_right, self.trophy_logo, right_center)

    def draw_leaderboard(self):
        if not self.current_game_leaderboard:
            return

        leaderboard = self.current_game_leaderboard[:10]
        panel_width = int(config.SCREEN_WIDTH * 0.72)
        entry_height = 24
        header_height = 44
        panel_height = header_height + entry_height * len(leaderboard) + 12
        x = (config.SCREEN_WIDTH - panel_width) // 2
        y = int(config.SCREEN_HEIGHT * 0.22)

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((15, 18, 28, 220))
        pygame.draw.rect(panel, (60, 70, 95, 220), panel.get_rect(), 2)

        title_color = (255, 215, 120)
        title1 = self.font_small.render("FINAL", True, title_color)
        title2 = self.font_small.render("TOP 10", True, title_color)
        title1_x = (panel_width - title1.get_width()) // 2
        title2_x = (panel_width - title2.get_width()) // 2
        panel.blit(title1, (title1_x, 6))
        panel.blit(title2, (title2_x, 6 + title1.get_height()))

        player_map = {p.username: p for p in self.players}
        row_y = header_height
        avatar_size = entry_height - 6

        for index, result in enumerate(leaderboard):
            username = result.get("username", "Unknown")
            points = result.get("points", result.get("total_points", 0))
            rank_text = self.font_mini.render(f"{index + 1}.", True, (220, 220, 230))
            rank_y = row_y + (entry_height - rank_text.get_height()) // 2
            panel.blit(rank_text, (10, rank_y))

            avatar_x = 34
            avatar_y = row_y + (entry_height - avatar_size) // 2
            player = player_map.get(username)
            if player:
                avatar_surface = self._get_player_surface(player)
                avatar_surface = pygame.transform.smoothscale(avatar_surface, (avatar_size, avatar_size))
                panel.blit(avatar_surface, (avatar_x, avatar_y))
            else:
                center = (avatar_x + avatar_size // 2, avatar_y + avatar_size // 2)
                pygame.draw.circle(panel, (40, 40, 40), center, avatar_size // 2)
                draw_avatar_initials(
                    panel,
                    username,
                    center=center,
                    diameter=avatar_size,
                )
                pygame.draw.circle(panel, (220, 220, 230), center, avatar_size // 2, 1)

            name_text = self.font_mini.render(username, True, (240, 240, 245))
            name_y = row_y + (entry_height - name_text.get_height()) // 2
            panel.blit(name_text, (avatar_x + avatar_size + 8, name_y))

            points_text = self.font_mini.render(f"{points:.1f}", True, (120, 220, 160))
            points_y = row_y + (entry_height - points_text.get_height()) // 2
            panel.blit(points_text, (panel_width - points_text.get_width() - 12, points_y))

            row_y += entry_height

        self.screen.blit(panel, (x, y))

    def draw_hud(self):
        alive = sum(1 for p in self.players if p.alive)
        total = len(self.players)

        arena_top = self.center[1] - self.initial_safe_radius
        arena_bottom = self.center[1] + self.initial_safe_radius

        title_text = self.font_title.render("METEOR MAYHEM", True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, int(arena_top - 50)))

        subtitle_text = self.font_subtitle.render(
            "Dodge the meteors - last follower standing wins",
            True,
            config.COLOR_TEXT
        )
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, int(arena_top - 15)))

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_surface = self.font_stats.render(prompt_text, True, config.COLOR_TEXT)
            spacing = 6
            prompt_y = subtitle_rect.bottom + spacing
            max_prompt_y = arena_top - spacing - (prompt_surface.get_height() // 2)
            if prompt_y > max_prompt_y:
                shift = prompt_y - max_prompt_y
                top_margin = 8
                max_shift = max(0, subtitle_rect.top - top_margin)
                if shift > 0 and max_shift > 0:
                    shift = min(shift, max_shift)
                    title_rect.centery -= int(shift)
                    subtitle_rect.centery -= int(shift)
                    prompt_y = subtitle_rect.bottom + spacing
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, int(prompt_y)))
            self.screen.blit(title_text, title_rect)
            self.screen.blit(subtitle_text, subtitle_rect)
            self.screen.blit(prompt_surface, prompt_rect)
        else:
            self.screen.blit(title_text, title_rect)
            self.screen.blit(subtitle_text, subtitle_rect)

        day_number = getattr(config, 'DAY_NUMBER', 1)
        day_text = self.font_day.render(f"Day {day_number}: {total} followers", True, config.COLOR_TEXT)
        day_rect = day_text.get_rect(center=(self.width // 2, int(arena_bottom + 25)))
        self.screen.blit(day_text, day_rect)

        alive_text = self.font_stats.render(f"Alive: {alive}/{total}", True, config.COLOR_TEXT)
        alive_rect = alive_text.get_rect(center=(self.width // 2, int(arena_bottom + 55)))
        self.screen.blit(alive_text, alive_rect)

        draw_club_panel(
            self.screen,
            self.club_spotlight,
            anchor_y=alive_rect.bottom,
            font=self.font_club_panel,
            get_avatar_surface=self._get_club_panel_avatar,
            glow_cache=self._club_glow_cache,
        )

        if self.phase == "countdown":
            countdown_text = self.font_title.render(str(self.countdown_number), True, (255, 200, 120))
            rect = countdown_text.get_rect(center=(self.width // 2, 120))
            self.screen.blit(countdown_text, rect)
        elif self.phase == "finished":
            self.draw_leaderboard()

    def render(self):
        self.screen.fill(config.COLOR_BACKGROUND)
        self.draw_zone()
        self.draw_meteors()
        self.draw_players()
        self.draw_hud()
        self._draw_promo_overlay()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Results / stats
    # ------------------------------------------------------------------
    def get_results(self) -> List[dict]:
        results = []
        if not self.players:
            return results

        def survival_time(player: MeteorPlayer) -> float:
            return player.elimination_time if player.elimination_time is not None else self.game_time

        sorted_players = sorted(
            self.players,
            key=lambda p: (-survival_time(p), p.username)
        )

        for placement, player in enumerate(sorted_players, start=1):
            player.placement = placement
            results.append({
                "username": player.username,
                "display_name": player.display_name,
                "placement": placement,
                "survival_time": survival_time(player),
                "score": 0
            })
        return results

    def save_statistics(self):
        print("\nCalculating scores...")
        results = self.get_results()
        if not results:
            print("No results to save.")
            return

        total_participants = len(results)
        game_results = []
        game_history_results = []
        game_type = "meteor_mayhem"
        game_display_name = "Meteor Mayhem"
        day_number = getattr(config, 'DAY_NUMBER', 1)

        for result in results:
            placement = result["placement"]
            survival_time = result["survival_time"]
            username = result["username"]
            games_played = self.statistics.get_games_played(username)

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played
            )
            points_earned = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=username,
                placement=placement,
                points_earned=points_earned,
                survival_time=survival_time,
                total_participants=total_participants,
                game_type=game_type,
                game_id=""
            )

            game_results.append((username, placement, points_earned, survival_time))
            game_history_results.append({
                "username": username,
                "placement": placement,
                "points": points_earned,
                "survival_time": survival_time,
                "kills": 0,
                "damage": 0.0
            })

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results
        )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def update_phase(self, dt: float):
        if self.phase == "intro":
            if self.game_time >= 1.0:
                self.phase = "countdown"
                self.phase_start_time = time.time()
                self.sound.play_countdown_audio()
        elif self.phase == "countdown":
            elapsed = time.time() - self.phase_start_time
            remaining = max(0, 3 - int(elapsed))
            self.countdown_number = max(0, remaining)
            if elapsed >= self.sound.countdown_audio_duration:
                self.phase = "playing"
                self.sound.start_background_music()
        elif self.phase == "finished":
            if self.winner_display_started and (time.time() - self.winner_display_started) > self.winner_display_time:
                self.game_over = True

    def run(self):
        print("Starting Meteor Mayhem...")
        self.load_players()
        self.phase_start_time = time.time()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            dt = self.clock.tick(config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS) / 1000.0
            dt = min(dt, config.MAX_DELTA_TIME)
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt
            self.update_phase(dt)

            if self.phase == "playing":
                if (self.game_time - self.last_spawn_time) >= self.next_spawn_delay:
                    self.spawn_meteor()
                self.update_meteors(dt)
                self.update_explosions(dt)
                self.update_players(dt)
                self.check_game_over()

            self.render()
            if config.EXPORT_VIDEO:
                self.recorder.capture_frame(self.screen, time.time())

            if self.game_over:
                break

        # Cleanup and export
        if config.EXPORT_VIDEO:
            self.recorder.export_video()
        self.save_statistics()
        self.sound.cleanup()
        pygame.quit()
        print("Meteor Mayhem finished.")
