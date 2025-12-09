"""
Meteor Mayhem (Dodge Royale)
Top-down arena where meteors rain randomly; players bump and try to stay out of impact zones
while a shrinking safe circle squeezes them together.
"""

import math
import random
import time
from dataclasses import dataclass
from typing import List, Tuple

import pygame

import config
from shared import (
    InstagramAPI,
    SoundManager,
    VideoRecorder,
    PlayerStatistics,
    ScoringSystem,
    GameHistory,
    AudioLogger,
)


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
    def __init__(self, username: str, display_name: str, color: Tuple[int, int, int]):
        self.username = username
        self.display_name = display_name
        self.color = color
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.radius = 10
        self.alive = True
        self.placement = None
        self.elimination_time = None

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
        self.target_safe_radius = config.METEOR_ZONE_INITIAL_RADIUS
        self.last_spawn_time = 0.0
        self.next_spawn_delay = random.uniform(*config.METEOR_SPAWN_INTERVAL)
        self.player_radius = 10

        # Fonts
        self.font_big = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 18)
        self.font_mini = pygame.font.SysFont("Arial", 14)

        print("Meteor Mayhem initialized!\n")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def load_players(self):
        print(f"Spawning followers for Meteor Mayhem...")
        follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)
        colors = config.METEOR_PLAYER_COLORS
        color_count = len(colors)

        for idx, data in enumerate(follower_data):
            color = colors[idx % color_count] if color_count else (200, 200, 200)
            p = MeteorPlayer(
                username=data['username'],
                display_name=data.get('display_name', data['username']),
                color=color
            )

            # Spawn within the current safe zone
            angle = random.random() * math.pi * 2
            dist = random.random() * (self.safe_radius - 20)
            spawn_x = self.center[0] + math.cos(angle) * dist
            spawn_y = self.center[1] + math.sin(angle) * dist
            p.set_spawn(spawn_x, spawn_y)
            self.players.append(p)

        print(f"  Spawned {len(self.players)} players\n")

    # ------------------------------------------------------------------
    # Game logic
    # ------------------------------------------------------------------
    def spawn_meteor(self):
        angle = random.random() * math.pi * 2
        dist = random.random() * (self.safe_radius * 0.9)
        target_x = self.center[0] + math.cos(angle) * dist
        target_y = self.center[1] + math.sin(angle) * dist

        start_x = target_x + random.uniform(-60, 60)
        start_y = -40.0

        speed = random.uniform(*config.METEOR_FALL_SPEED)
        radius = random.uniform(*config.METEOR_RADIUS)
        impact_radius = random.uniform(*config.METEOR_IMPACT_RADIUS)

        self.meteors.append(Meteor(start_x, start_y, target_x, target_y, speed, radius, impact_radius))
        self.last_spawn_time = self.game_time
        self.next_spawn_delay = random.uniform(*config.METEOR_SPAWN_INTERVAL)

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

            if threat and threat_dist < 180:
                # Run away from impact point
                dx = player.x - threat.target_x
                dy = player.y - threat.target_y
                dist = math.hypot(dx, dy) or 1.0
                move_x += dx / dist
                move_y += dy / dist
            else:
                # Drift toward center to stay in zone
                dx = self.center[0] - player.x
                dy = self.center[1] - player.y
                dist = math.hypot(dx, dy) or 1.0
                move_x += dx / dist * 0.4
                move_y += dy / dist * 0.4

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
        self.resolve_collisions()
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
            self.winner_display_started = time.time()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw_zone(self):
        # Subtle inner glow plus outline for the safe zone
        glow_radius = int(self.safe_radius * 1.02)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (*config.METEOR_ZONE_COLOR, 30), (glow_radius, glow_radius), glow_radius)
        self.screen.blit(glow_surface, (self.center[0] - glow_radius, self.center[1] - glow_radius))
        pygame.draw.circle(self.screen, config.METEOR_ZONE_COLOR, self.center, int(self.safe_radius), 2)

    def draw_meteors(self):
        for meteor in self.meteors:
            # Impact pre-visual (soft ring)
            impact_surface = pygame.Surface((meteor.impact_radius * 2, meteor.impact_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                impact_surface,
                (*config.METEOR_IMPACT_COLOR, 40),
                (int(meteor.impact_radius), int(meteor.impact_radius)),
                int(meteor.impact_radius),
                width=4,
            )
            self.screen.blit(impact_surface, (meteor.target_x - meteor.impact_radius, meteor.target_y - meteor.impact_radius))

            # Meteor body with a subtle rim
            pygame.draw.circle(self.screen, config.METEOR_COLOR, (int(meteor.x), int(meteor.y)), int(meteor.radius))
            pygame.draw.circle(
                self.screen,
                config.METEOR_IMPACT_COLOR,
                (int(meteor.x), int(meteor.y)),
                max(1, int(meteor.radius * 0.55)),
                width=0,
            )

            # Trailing line toward impact
            pygame.draw.line(
                self.screen,
                config.METEOR_IMPACT_COLOR,
                (int(meteor.x), int(meteor.y)),
                (int(meteor.target_x), int(meteor.target_y)),
                2,
            )
        for exp in self.explosions:
            alpha = 255 * (1 - exp.progress)
            radius = exp.radius * (0.5 + 0.8 * exp.progress)
            surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*config.METEOR_IMPACT_COLOR, int(alpha)), (int(radius), int(radius)), int(radius), 3)
            self.screen.blit(surface, (exp.x - radius, exp.y - radius))

    def draw_players(self):
        for player in self.players:
            if not player.alive:
                continue
            pygame.draw.circle(self.screen, player.color, (int(player.x), int(player.y)), player.radius)

    def draw_hud(self):
        title = self.font_big.render("METEOR MAYHEM", True, (230, 230, 240))
        self.screen.blit(title, (20, 20))

        subtitle = self.font_small.render("Dodge the meteors • Last follower standing wins", True, (180, 180, 190))
        self.screen.blit(subtitle, (20, 55))

        alive = sum(1 for p in self.players if p.alive)
        alive_text = self.font_small.render(f"Alive: {alive}", True, (200, 220, 255))
        self.screen.blit(alive_text, (20, 80))

        if self.phase == "countdown":
            countdown_text = self.font_big.render(str(self.countdown_number), True, (255, 200, 120))
            rect = countdown_text.get_rect(center=(config.SCREEN_WIDTH // 2, 120))
            self.screen.blit(countdown_text, rect)

    def render(self):
        self.screen.fill(config.METEOR_BG_COLOR)
        self.draw_zone()
        self.draw_meteors()
        self.draw_players()
        self.draw_hud()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Results / stats
    # ------------------------------------------------------------------
    def get_results(self) -> List[dict]:
        results = []
        total = len(self.players)
        for player in self.players:
            placement = player.placement if player.placement else total
            results.append({
                "username": player.username,
                "display_name": player.display_name,
                "placement": placement,
                "score": 0
            })
        results.sort(key=lambda r: r["placement"])
        return results

    def save_statistics(self):
        print("\nSaving Meteor Mayhem statistics...")
        results = self.get_results()
        scored = self.scoring.calculate_scores(results, game_mode="meteor_mayhem")
        self.current_game_leaderboard = scored

        if not config.TEST_MODE:
            self.statistics.update_from_game_results(
                scored,
                game_mode="meteor_mayhem",
                day=config.DAY_NUMBER
            )
            self.all_time_leaderboard = self.statistics.get_all_time_leaderboard()
            self.game_history.save_game_session(
                game_mode="meteor_mayhem",
                day_number=config.DAY_NUMBER,
                date=time.strftime("%Y-%m-%d"),
                results=scored
            )
            print("Statistics saved.")
        else:
            print("TEST MODE: Skipping persistent stats.")

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
                self.shrink_zone(dt)
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
