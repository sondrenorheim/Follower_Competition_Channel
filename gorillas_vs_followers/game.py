"""
Gorillas vs Followers - Main Game Class
Orchestrates the Gorillas vs Followers game mode
Team-based combat: Followers must defeat all gorillas to win
"""

import pygame
import random
import math
import time
import sys
from typing import List

import config
from shared import (
    InstagramAPI,
    PhysicsEngine,
    ParticleSystem,
    SoundManager,
    ScoringSystem,
    PlayerStatistics,
    GameHistory,
    VideoRecorder,
    AudioLogger,
    auto_push
)
from .gorilla_follower import GorillaFollower
from .gorilla import Gorilla
from .arena import GorillasArena
from .renderer import GorillasRenderer


class GorillasVsFollowersGame:
    """
    Main game class for Gorillas vs Followers mode
    Followers team up to fight gorilla bosses
    Victory condition: All gorillas must die for followers to win
    """

    def __init__(self):
        """Initialize the game"""
        print("=" * 60)
        print("  GORILLAS VS FOLLOWERS")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()

        # Use HIDDEN flag if headless mode is enabled
        display_flags = pygame.HIDDEN if config.HEADLESS_MODE else 0
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), display_flags)

        if not config.HEADLESS_MODE:
            pygame.display.set_caption("Gorillas vs Followers")

        self.clock = pygame.time.Clock()

        # Initialize game components
        print("\n🎮 Initializing Gorillas vs Followers...")
        self.api = InstagramAPI()
        self.arena = GorillasArena()
        self.renderer = GorillasRenderer(self.screen)
        self.physics = PhysicsEngine()
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
        self.particles = ParticleSystem()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.game_history = GameHistory()
        self.scoring = ScoringSystem()

        # Preload audio
        self.sound.preload_audio()

        # Game state
        self.followers: List[GorillaFollower] = []
        self.gorillas: List[Gorilla] = []
        self.all_entities = []  # Combined list for combat
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Track game time for video recording
        self.game_time = 0.0
        self.recording_start_time = None

        # Game phases: "intro", "countdown", "playing", "finished"
        self.game_phase = "intro"
        self.phase_start_time = 0
        self.countdown_number = 3

        # Combat delay
        self.combat_delay_duration = 2.0
        self.combat_start_time = None

        # Victory tracking
        self.victory_team = None  # "followers" or "gorillas"

        # Gate/gap between teams
        self.gate_open_progress = 0.0
        self.gate_open_start_time = None
        self.gate_open_duration = getattr(config, "GORILLA_GATE_OPEN_DURATION", 2.0)

        # Statistics
        self.total_eliminations = 0
        self.last_alive_followers = 0
        self.last_alive_gorillas = 0

        # Leaderboard data
        self.current_game_leaderboard = []

        # Dynamic scaling tracking
        self.initial_total_players = 0
        self.last_follower_radius = config.FOLLOWER_RADIUS

        print("✅ Gorillas vs Followers initialized!\n")

    def setup_game(self):
        """
        Fetch followers and create game entities
        """
        print(f"🎯 Setting up game...")

        # Fetch followers (support test mode)
        if config.TEST_MINIMAL_PLAYERS:
            print(f"🧪 TEST MODE: Using {config.TEST_MINIMAL_PLAYER_COUNT} test players")
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        follower_count = len(follower_data)

        # Calculate gorilla count (1 per 100 followers)
        gorilla_count = max(1, follower_count // 100)

        print(f"📊 {follower_count} followers vs {gorilla_count} gorillas")

        # Store initial values for dynamic scaling
        self.initial_total_players = follower_count

        # Calculate initial dynamic radius
        arena_rect = self.arena.get_rect()
        if config.USE_DYNAMIC_SCALING:
            initial_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=self.initial_total_players,
                safe_zone_radius=min(arena_rect[2], arena_rect[3]) // 2,
                initial_zone_radius=min(arena_rect[2], arena_rect[3]) // 2
            )
            config.FOLLOWER_RADIUS = initial_radius
            config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
            config.FIGHTER_ATTACK_RANGE = config.FOLLOWER_RADIUS * 2.5
            self.last_follower_radius = initial_radius

            print(f"🔧 Dynamic scaling: follower radius = {initial_radius:.1f}px")

        # Create followers
        left, top, right, bottom = self.arena.get_bounds()
        gate_y = (top + bottom) / 2.0
        for data in follower_data:
            x = random.uniform(left + config.FOLLOWER_RADIUS, right - config.FOLLOWER_RADIUS)
            y = random.uniform(gate_y + config.FOLLOWER_RADIUS, bottom - config.FOLLOWER_RADIUS)
            follower = GorillaFollower(data, (x, y))
            self.followers.append(follower)

        # Create gorillas
        for i in range(gorilla_count):
            radius = config.FOLLOWER_RADIUS * config.GORILLA_SIZE_MULTIPLIER
            x = random.uniform(left + radius, right - radius)
            y = random.uniform(top + radius, gate_y - radius)
            gorilla = Gorilla((x, y), i + 1)
            self.gorillas.append(gorilla)

        # Combine into single list for combat
        self.all_entities = self.followers + self.gorillas

        # Randomize update order for fairness
        random.shuffle(self.all_entities)

        self.last_alive_followers = len(self.followers)
        self.last_alive_gorillas = len(self.gorillas)

        print(f"✅ Game ready!\n")

    def update(self, dt: float):
        """Update game state"""
        if self.game_over:
            return

        current_time = time.time()

        # Update gate progress (0 closed, 1 fully open)
        if self.game_phase == "playing" and self.gate_open_start_time is None:
            self.gate_open_start_time = self.game_time
        if self.gate_open_start_time is not None:
            elapsed_gate = self.game_time - self.gate_open_start_time
            self.gate_open_progress = min(1.0, max(0.0, elapsed_gate / self.gate_open_duration))
        else:
            self.gate_open_progress = 0.0

        # Handle countdown phase
        if self.game_phase == "countdown":
            elapsed = self.game_time - self.phase_start_time
            countdown_duration = self.sound.countdown_audio_duration

            if config.EXPORT_VIDEO:
                countdown_duration *= config.EXPORT_TIME_SCALE

            if elapsed >= countdown_duration:
                import time as time_module
                print(f"🔊 [{time_module.time():.2f}] FIGHT!")
                self.game_phase = "playing"
                self.combat_start_time = self.game_time
                self.sound.set_music_volume_high()
                print(f"[{time_module.time():.2f}] ⚔️  Battle phase starting!\n")
            else:
                self.countdown_number = max(0, 3 - int(elapsed))

        # Combat enabled during playing phase after delay
        combat_enabled = False
        if self.game_phase == "playing" and self.combat_start_time is not None:
            delay_duration = self.combat_delay_duration
            if config.EXPORT_VIDEO:
                delay_duration *= config.EXPORT_TIME_SCALE

            time_since_combat_start = self.game_time - self.combat_start_time
            combat_enabled = time_since_combat_start >= delay_duration

            if combat_enabled and not hasattr(self, '_combat_enabled_logged'):
                import time as time_module
                print(f"⚔️  [{time_module.time():.2f}] COMBAT ENABLED!")
                self._combat_enabled_logged = True

        # Update all entities
        arena_rect = self.arena.get_rect()
        for entity in self.all_entities:
            if hasattr(entity, 'update_fighter'):
                # Followers use fighter update
                entity.update_fighter(dt, arena_rect, self.all_entities, current_time, combat_enabled, gate_progress=self.gate_open_progress)
            else:
                # Gorillas use their own update
                entity.update(dt, self.arena, self.all_entities, combat_enabled)

        # Gate clamping: keep followers bottom and gorillas top until gate opens
        left, top, right, bottom = self.arena.get_bounds()
        gate_y = (top + bottom) / 2.0
        center_x = (left + right) / 2.0
        gap_width = (right - left) * self.gate_open_progress
        half_gap = gap_width / 2.0
        gap_left = center_x - half_gap
        gap_right = center_x + half_gap

        for entity in self.all_entities:
            radius = getattr(entity, "radius", config.FOLLOWER_RADIUS)
            is_gorilla = getattr(entity, "__class__", None).__name__ == "Gorilla"

            if self.gate_open_progress < 1.0:
                # Horizontal gate segments still block movement outside the widening center gap
                if is_gorilla:
                    # Gorillas start top; block crossing below gate unless within gap
                    if entity.y + radius > gate_y:
                        if not (gap_left + radius <= entity.x <= gap_right - radius):
                            entity.y = gate_y - radius
                else:
                    # Followers start bottom; block crossing above gate unless within gap
                    if entity.y - radius < gate_y:
                        if not (gap_left + radius <= entity.x <= gap_right - radius):
                            entity.y = gate_y + radius
            # Always keep inside arena bounds
            entity.x = max(left + radius, min(right - radius, entity.x))
            entity.y = max(top + radius, min(bottom - radius, entity.y))

        # Physics
        self.physics.update(self.all_entities, current_time)

        # Custom collision resolution: Only separate followers from gorillas
        # Followers can cluster together without pushing each other
        self._resolve_gorilla_collisions()

        # Update particles and sound
        self.particles.update(dt)
        self.sound.update_music_volume()

        # Game logic during playing phase
        if self.game_phase == "playing":
            alive_followers = [f for f in self.followers if f.alive]
            alive_gorillas = [g for g in self.gorillas if g.alive]
            alive_follower_count = len(alive_followers)
            alive_gorilla_count = len(alive_gorillas)

            # Update dynamic radius (only count alive followers for scaling)
            if config.USE_DYNAMIC_SCALING:
                new_radius = config.calculate_dynamic_follower_radius(
                    total_players=self.initial_total_players,
                    alive_count=alive_follower_count,
                    safe_zone_radius=min(arena_rect[2], arena_rect[3]) // 2,
                    initial_zone_radius=min(arena_rect[2], arena_rect[3]) // 2
                )

                # Invalidate surfaces when radius changes
                if abs(new_radius - self.last_follower_radius) > 0.01:
                    for follower in self.followers:
                        follower.surface_needs_update = True

                    # Clear the renderer's cache
                    self.renderer.follower_surfaces.clear()
                    self.renderer.cached_radius.clear()

                    self.last_follower_radius = new_radius

                    # Update radius and dependent values
                    config.FOLLOWER_RADIUS = new_radius
                    config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
                    config.FIGHTER_ATTACK_RANGE = config.FOLLOWER_RADIUS * 2.5
                    # Scale gorillas along with followers
                    for gorilla in self.gorillas:
                        gorilla.radius = config.FOLLOWER_RADIUS * config.GORILLA_SIZE_MULTIPLIER
                        scaled_range = config.FIGHTER_ATTACK_RANGE * config.GORILLA_SIZE_MULTIPLIER
                        # Use the dynamically scaled range without clamping to the original size
                        gorilla.attack_range = scaled_range

            # Update music intensity based on total alive entities
            total_alive = alive_follower_count + alive_gorilla_count
            total_entities = len(self.all_entities)
            self.sound.update_music_intensity(total_alive, total_entities)

            # Print elimination updates
            if alive_follower_count != self.last_alive_followers:
                eliminated = self.last_alive_followers - alive_follower_count
                if eliminated > 0:
                    print(f"💀 {eliminated} follower(s) eliminated - {alive_follower_count} remaining")
                self.last_alive_followers = alive_follower_count

            if alive_gorilla_count != self.last_alive_gorillas:
                eliminated = self.last_alive_gorillas - alive_gorilla_count
                if eliminated > 0:
                    print(f"🦍 {eliminated} gorilla(s) defeated - {alive_gorilla_count} remaining")
                self.last_alive_gorillas = alive_gorilla_count

            # Check victory conditions
            if alive_gorilla_count == 0:
                # Followers win - all gorillas defeated
                if not self.game_over:
                    self.game_over = True
                    self.victory_team = "followers"
                    self.sound.play_winner_celebration()
                    self._handle_game_over()
            elif alive_follower_count == 0:
                # Gorillas win - all followers defeated
                if not self.game_over:
                    self.game_over = True
                    self.victory_team = "gorillas"
                    self.sound.play_winner_celebration()
                    self._handle_game_over()

    def render(self):
        """Render current game state"""
        game_state = {
            "game_over": self.game_over,
            "game_phase": self.game_phase,
            "countdown_number": self.countdown_number,
            "day_number": getattr(config, 'DAY_NUMBER', 1),
            "victory_team": self.victory_team,
            "current_game_leaderboard": self.current_game_leaderboard,
            "gate_progress": self.gate_open_progress,
        }

        self.renderer.render_frame(
            self.followers, self.gorillas, self.arena,
            game_state, self.particles
        )

        # Record frame
        if self.game_phase in ("countdown", "playing", "finished"):
            if self.recording_start_time is None:
                self.recording_start_time = self.game_time

            recording_time = self.game_time - self.recording_start_time
            self.recorder.capture_frame(self.screen, current_time=recording_time)

        pygame.display.flip()

    def _handle_game_over(self):
        """Handle game over logic"""
        duration = time.time() - self.game_start_time
        print("\n" + "=" * 60)
        print("  🏆 GAME OVER 🏆")
        print("=" * 60)
        print(f"Duration: {duration:.1f}s")

        if self.victory_team == "followers":
            print(f"\n🥇 FOLLOWERS WIN! All gorillas defeated!")
            alive_followers = [f for f in self.followers if f.alive]
            print(f"   Survivors: {len(alive_followers)}/{len(self.followers)}")
        else:
            print(f"\n🦍 GORILLAS WIN! All followers eliminated!")
            alive_gorillas = [g for g in self.gorillas if g.alive]
            print(f"   Survivors: {len(alive_gorillas)}/{len(self.gorillas)}")

        print("=" * 60)

        # Calculate scores
        self._calculate_and_save_scores()

        print("\n🎬 Showing final results...")

    def _resolve_gorilla_collisions(self):
        """
        Custom collision resolution for gorillas vs followers
        GORILLAS ARE COMPLETELY IMMOVABLE
        Only followers get pushed away from gorillas
        Followers do NOT push each other
        """
        # Allow followers to overlap with gorilla so they can attack
        # Collision distance should be less than attack range (35 pixels)
        min_distance_follower_gorilla = config.FIGHTER_ATTACK_RANGE * 0.8  # 28 pixels - within attack range

        # Push followers away from gorillas (gorillas stay perfectly still)
        for follower in self.followers:
            if not follower.alive:
                continue

            for gorilla in self.gorillas:
                if not gorilla.alive:
                    continue

                dx = gorilla.x - follower.x
                dy = gorilla.y - follower.y
                distance_sq = dx * dx + dy * dy
                min_dist_sq = min_distance_follower_gorilla * min_distance_follower_gorilla

                if distance_sq < min_dist_sq and distance_sq > 0.01:
                    distance = distance_sq ** 0.5
                    overlap = min_distance_follower_gorilla - distance

                    # Normalize direction
                    sep_x = dx / distance
                    sep_y = dy / distance

                    # ONLY move the follower away (gorilla stays completely still)
                    follower.x -= sep_x * overlap
                    follower.y -= sep_y * overlap

        # Gorillas can overlap each other - they are immovable objects
        # No gorilla-to-gorilla collision resolution needed

    def _calculate_and_save_scores(self):
        """
        Calculate scores for followers
        Points awarded ONLY if followers won (all gorillas dead)
        Individual points based on damage dealt to gorillas
        """
        print("\n📊 Calculating scores...")

        game_type = "gorillas_vs_followers"
        game_display_name = "Gorillas vs Followers"
        day_number = getattr(config, 'DAY_NUMBER', 1)

        total_participants = len(self.followers)
        game_results = []
        game_history_results = []

        if self.victory_team == "followers":
            # FOLLOWERS WON - Award points based on gorilla damage
            print("✅ Followers won! Awarding points based on gorilla damage...")

            # Sort by gorilla damage dealt (descending)
            sorted_followers = sorted(
                self.followers,
                key=lambda f: f.gorilla_damage_dealt,
                reverse=True
            )

            for placement, follower in enumerate(sorted_followers, start=1):
                # Score is raw damage dealt to gorillas
                points_earned = follower.gorilla_damage_dealt

                self.statistics.update_player_stats(
                    username=follower.username,
                    placement=placement,
                    points_earned=points_earned,
                    survival_time=follower.get_survival_time(),
                    total_participants=total_participants,
                    kills=follower.kills,
                    damage_dealt=follower.gorilla_damage_dealt,  # Use gorilla damage
                    game_type=game_type,
                    game_id=""
                )

                game_results.append((
                    follower.username,
                    placement,
                    points_earned,
                    follower.gorilla_damage_dealt
                ))

                game_history_results.append({
                    "username": follower.username,
                    "placement": placement,
                    "points": points_earned,
                    "survival_time": follower.get_survival_time(),
                    "kills": follower.kills,
                    "damage": follower.gorilla_damage_dealt
                })

        else:
            # GORILLAS WON - No points awarded
            print("❌ Gorillas won! No points awarded.")

            for follower in self.followers:
                game_history_results.append({
                    "username": follower.username,
                    "placement": 0,
                    "points": 0,
                    "survival_time": follower.get_survival_time(),
                    "kills": follower.kills,
                    "damage": follower.gorilla_damage_dealt
                })

        # Record game session
        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results
        )

        # Save statistics
        self.statistics.save_statistics()

        # Auto-push to GitHub
        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        # Store leaderboard (for display)
        if game_results:
            self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)

            # Display leaderboard
            print(self.scoring.format_leaderboard(
                self.current_game_leaderboard,
                top_n=10,
                title="TOP DAMAGE DEALERS"
            ))
        else:
            self.current_game_leaderboard = []

        self.statistics.print_all_time_stats(top_n=10)

    def run(self):
        """Main game loop"""
        # Setup
        self.setup_game()

        # Start audio logging
        self.audio_logger.start()

        # Intro sequence
        print("🎮 Starting intro sequence...\n")
        self.game_phase = "intro"

        # Play intro audio
        self.sound.play_intro_audio()

        # Display intro
        intro_start = time.time()
        intro_duration = self.sound.get_total_intro_duration() + 0.5

        while time.time() - intro_start < intro_duration:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return

            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0
            dt = min(dt, config.MAX_DELTA_TIME)

            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt

            # Update entities during intro (no combat)
            arena_rect = self.arena.get_rect()
            current_time = time.time()
            for entity in self.all_entities:
                if hasattr(entity, 'update_fighter'):
                    entity.update_fighter(dt, arena_rect, self.all_entities, current_time, False, gate_progress=0.0)
                else:
                    entity.update(dt, self.arena, self.all_entities, False, gate_progress=0.0)

            # Skip physics during intro to prevent drift
            self.particles.update(dt)
            self.sound.update_music_volume()
            self.render()

        # Start countdown
        print("\n⏱️  Starting countdown...")
        self.game_phase = "countdown"
        self.phase_start_time = self.game_time
        self.sound.play_countdown_audio()

        # Main game loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0
            dt = min(dt, config.MAX_DELTA_TIME)

            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt

            self.update(dt)
            self.render()

            # End game after podium display
            if self.game_over:
                if not hasattr(self, '_game_over_start'):
                    self._game_over_start = self.game_time

                elapsed = self.game_time - self._game_over_start
                podium_duration = 8.0

                if config.EXPORT_VIDEO:
                    podium_duration *= config.EXPORT_TIME_SCALE

                if elapsed >= podium_duration:
                    print("\n✅ Game complete!")
                    self.game_phase = "finished"
                    break

        # Cleanup
        self._cleanup()

    def _cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up...")

        # Stop recording
        if config.EXPORT_VIDEO:
            print("💾 Finalizing video...")
            self.recorder.finalize()
            print(f"✅ Video saved: {self.recorder.video_path}")

        # Stop audio logging
        self.audio_logger.stop()

        # Stop sound
        self.sound.stop()

        pygame.quit()
        print("✅ Cleanup complete!\n")


if __name__ == "__main__":
    game = GorillasVsFollowersGame()
    game.run()
