"""
Fighter Battle Arena - Main Game Class
Orchestrates the Fighter Arena game mode
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
    VideoRecorder,
    AudioLogger
)
from .fighter import Fighter
from .arena import FighterArena
from .renderer import FighterRenderer


class FighterBattleArena:
    """
    Main game class for the Fighter Arena game mode
    Fighters battle until only one remains
    """

    def __init__(self):
        """
        Initialize the game
        """
        print("=" * 60)
        print("  FIGHTER ARENA")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Fighter Arena")
        self.clock = pygame.time.Clock()

        # Initialize game components
        print("\n🎮 Initializing Fighter Arena...")
        self.api = InstagramAPI()
        self.arena = FighterArena()
        self.renderer = FighterRenderer(self.screen)
        self.physics = PhysicsEngine()
        self.audio_logger = AudioLogger()
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.0,  # 100% scale
            offset_y=0  # Centered vertically
        )
        self.particles = ParticleSystem()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()

        # Preload audio
        self.sound.preload_audio()

        # Game state
        self.fighters: List[Fighter] = []
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Track game time for consistent video recording with time scaling
        self.game_time = 0.0
        self.recording_start_time = None  # Will be set when recording starts

        # Game phases: "intro", "countdown", "playing", "finished"
        self.game_phase = "intro"
        self.phase_start_time = 0
        self.countdown_number = 3

        # Combat delay: 1 second after countdown ends before combat starts
        self.combat_delay_duration = 2.0
        self.combat_start_time = None

        # Statistics
        self.total_eliminations = 0
        self.last_alive_count = 0

        # Dynamic scaling tracking
        self.initial_total_players = 0
        self.last_fighter_radius = config.FOLLOWER_RADIUS

        # Leaderboard data
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

        print("✅ Fighter Arena initialized!\n")

    def setup_fighters(self):
        """
        Fetch/generate followers and create fighters
        """
        print(f"🥊 Setting up {config.FOLLOWER_COUNT} fighters...")

        # Fetch followers from API or generate placeholders
        follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        # Place fighters randomly in arena
        arena_rect = self.arena.get_rect()

        for data in follower_data:
            # Random position within arena
            x, y = self.arena.get_random_position(config.FOLLOWER_RADIUS)

            fighter = Fighter(data, (x, y))
            self.fighters.append(fighter)

        # Randomize fighter update order to ensure fair attack priority
        random.shuffle(self.fighters)

        # Store initial values for dynamic scaling
        self.initial_total_players = len(self.fighters)

        # Calculate initial dynamic radius
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
            self.last_fighter_radius = initial_radius

            for fighter in self.fighters:
                fighter.surface_needs_update = True

            print(f"🔧 Dynamic scaling: fighter radius = {initial_radius:.1f}px")

        print(f"✅ {len(self.fighters)} fighters ready for battle!\n")

    def update(self, dt: float):
        """
        Update game state

        Args:
            dt: Delta time in seconds
        """
        if self.game_over:
            return

        current_time = time.time()

        # Handle countdown phase
        if self.game_phase == "countdown":
            elapsed = self.game_time - self.phase_start_time
            countdown_duration = self.sound.countdown_audio_duration

            # Scale countdown duration when exporting video with time scaling
            if config.EXPORT_VIDEO:
                countdown_duration *= config.EXPORT_TIME_SCALE

            if elapsed >= countdown_duration:
                import time as time_module
                print(f"🔊 [{time_module.time():.2f}] FIGHT! (elapsed: {elapsed:.2f}s, duration: {countdown_duration:.2f}s)")
                self.game_phase = "playing"
                self.combat_start_time = self.game_time  # Set combat start time (will delay by 1 second)
                self.sound.set_music_volume_high()
                print(f"[{time_module.time():.2f}] ⚔️  Battle phase starting (combat delayed by {self.combat_delay_duration}s)!\n")
            else:
                self.countdown_number = max(0, 3 - int(elapsed))
                # Debug: Log countdown number changes
                if not hasattr(self, '_last_countdown_number'):
                    self._last_countdown_number = None
                if self._last_countdown_number != self.countdown_number:
                    import time as time_module
                    print(f"⏱️  [{time_module.time():.2f}] Countdown: {self.countdown_number}")
                    self._last_countdown_number = self.countdown_number

        # Update fighters during all phases
        arena_rect = self.arena.get_rect()

        # Combat only enabled during "playing" phase AND after combat delay has elapsed
        combat_enabled = False
        if self.game_phase == "playing" and self.combat_start_time is not None:
            # Calculate delay duration (scale for video export)
            delay_duration = self.combat_delay_duration
            if config.EXPORT_VIDEO:
                delay_duration *= config.EXPORT_TIME_SCALE

            # Check if delay has elapsed
            time_since_combat_start = self.game_time - self.combat_start_time
            combat_enabled = time_since_combat_start >= delay_duration

            # Debug: Log when combat becomes enabled
            if combat_enabled and not hasattr(self, '_combat_enabled_logged'):
                import time as time_module
                print(f"⚔️  [{time_module.time():.2f}] COMBAT ENABLED! (delay: {delay_duration:.2f}s, elapsed: {time_since_combat_start:.2f}s)")
                self._combat_enabled_logged = True

        # Debug: Log phase transitions and combat state
        if not hasattr(self, '_last_combat_state'):
            self._last_combat_state = None
        if self._last_combat_state != combat_enabled:
            import time as time_module
            print(f"🎮 [{time_module.time():.2f}] Phase: {self.game_phase} | Combat: {'ENABLED' if combat_enabled else 'DISABLED'}")
            self._last_combat_state = combat_enabled

        for fighter in self.fighters:
            # Always use fighter-specific update (no zone avoidance)
            fighter.update_fighter(dt, arena_rect, self.fighters, current_time, combat_enabled)

        # Physics: collision detection and overlap resolution
        self.physics.update(self.fighters, current_time)
        self.physics.resolve_overlaps(self.fighters)

        # Update particles
        self.particles.update(dt)

        # Update music volume
        self.sound.update_music_volume()

        # Only do game logic during PLAYING phase
        if self.game_phase == "playing":
            # Check for eliminations
            alive_fighters = [f for f in self.fighters if f.alive]
            alive_count = len(alive_fighters)

            # Update dynamic radius
            if config.USE_DYNAMIC_SCALING:
                new_radius = config.calculate_dynamic_follower_radius(
                    total_players=self.initial_total_players,
                    alive_count=alive_count,
                    safe_zone_radius=min(arena_rect[2], arena_rect[3]) // 2,
                    initial_zone_radius=min(arena_rect[2], arena_rect[3]) // 2
                )

                if abs(new_radius - self.last_fighter_radius) > 0.5:
                    for fighter in self.fighters:
                        fighter.surface_needs_update = True
                    self.last_fighter_radius = new_radius

                config.FOLLOWER_RADIUS = new_radius
                config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
                config.FIGHTER_ATTACK_RANGE = config.FOLLOWER_RADIUS * 2.5

            # Update music intensity
            self.sound.update_music_intensity(alive_count, len(self.fighters))

            # Print elimination updates
            if alive_count != self.last_alive_count:
                eliminated = self.last_alive_count - alive_count
                if eliminated > 0:
                    self.total_eliminations += eliminated
                    print(f"💀 {eliminated} eliminated - {alive_count} remaining")
                self.last_alive_count = alive_count

            # Game over when 1 or 0 fighters remain
            if alive_count <= 1:
                if not self.game_over:
                    self.game_over = True
                    self.sound.play_winner_celebration()
                    self._handle_game_over(alive_fighters)

    def render(self):
        """
        Render current game state
        """
        game_state = {
            "game_over": self.game_over,
            "total_eliminations": self.total_eliminations,
            "game_phase": self.game_phase,
            "countdown_number": self.countdown_number,
            "day_number": getattr(config, 'DAY_NUMBER', 1),
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "all_followers": self.fighters,
        }

        self.renderer.render_frame(self.fighters, self.arena, game_state, self.particles)

        # Record frame (only from countdown onwards)
        if self.game_phase in ("countdown", "playing", "finished"):
            # Set recording start time on first frame
            if self.recording_start_time is None:
                self.recording_start_time = self.game_time

            # Pass recording time (time since recording started) to capture_frame
            recording_time = self.game_time - self.recording_start_time
            self.recorder.capture_frame(self.screen, current_time=recording_time)

        pygame.display.flip()

    def _handle_game_over(self, survivors: List[Fighter]):
        """
        Handle game over logic
        """
        duration = time.time() - self.game_start_time
        print("\n" + "=" * 60)
        print("  🏆 GAME OVER 🏆")
        print("=" * 60)
        print(f"Duration: {duration:.1f}s")
        print(f"Total Eliminations: {self.total_eliminations}")

        if survivors:
            winner = survivors[0]
            print(f"\n🥇 WINNER: {winner.username}")
            print(f"   Kills: {winner.kills} | Damage Dealt: {winner.damage_dealt:.0f}")
        else:
            print("\n💀 No survivors!")

        print("=" * 60)

        # Calculate scores
        self._calculate_and_save_scores()

        print("\n🎬 Showing final results...")

    def _calculate_and_save_scores(self):
        """
        Calculate scores for all fighters and update statistics
        """
        print("\n📊 Calculating scores...")

        # Sort fighters by survival time (alive first, then by elimination time)
        sorted_fighters = sorted(
            self.fighters,
            key=lambda f: (not f.alive, -f.get_survival_time()),
            reverse=False
        )

        total_participants = len(self.fighters)
        game_results = []

        for placement, fighter in enumerate(sorted_fighters, start=1):
            games_played = self.statistics.get_games_played(fighter.username)

            survival_time = fighter.get_survival_time()
            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played
            )

            points_earned = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=fighter.username,
                placement=placement,
                points_earned=points_earned,
                survival_time=survival_time,
                total_participants=total_participants,
                kills=fighter.kills,
                damage_dealt=fighter.damage_dealt
            )

            game_results.append((
                fighter.username,
                placement,
                points_earned,
                survival_time
            ))

        # Save statistics
        self.statistics.save_statistics()

        # Store leaderboards
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = self.statistics.get_all_time_leaderboard(top_n=10)

        # Display leaderboards
        print(self.scoring.format_leaderboard(
            self.current_game_leaderboard,
            top_n=10,
            title="CURRENT GAME - TOP 10"
        ))

        self.statistics.print_all_time_stats(top_n=10)

    def run(self):
        """
        Main game loop
        """
        # Setup
        self.setup_fighters()
        self.last_alive_count = len(self.fighters)

        # Start audio logging
        self.audio_logger.start()

        # Start background music
        self.sound.start_background_music()

        # Intro sequence
        print("🎮 Starting intro sequence...\n")
        self.game_phase = "intro"
        day_number = getattr(config, 'DAY_NUMBER', 1)

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

            # Use lower FPS during video export for better performance
            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0

            # Cap delta time to prevent huge jumps when system lags
            dt = min(dt, config.MAX_DELTA_TIME)

            # Apply time scaling during video export to slow down simulation
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt  # Track game time during intro

            # Update fighters during intro (no combat, just movement)
            arena_rect = self.arena.get_rect()
            current_time = time.time()
            for fighter in self.fighters:
                fighter.update_fighter(dt, arena_rect, self.fighters, current_time, combat_enabled=False)

            # Physics: collision detection and overlap resolution
            self.physics.update(self.fighters, current_time)
            self.physics.resolve_overlaps(self.fighters)

            self.particles.update(dt)
            self.sound.update_music_volume()
            self.render()

        # Start countdown
        print("\n⏱️  Starting countdown...")
        self.game_phase = "countdown"
        self.phase_start_time = self.game_time  # Use game_time instead of real time
        self.countdown_number = 3
        self.renderer.start_countdown_video()  # Start the video overlay
        self.sound.play_countdown_audio()

        # Track podium display time
        game_over_start_time = None

        # Main loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Use lower FPS during video export for better performance
            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0

            # Cap delta time to prevent huge jumps when system lags
            dt = min(dt, config.MAX_DELTA_TIME)

            # Apply time scaling during video export to slow down simulation
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt  # Track game time

            self.update(dt)
            self.render()

            if self.game_over and game_over_start_time is None:
                game_over_start_time = self.game_time

            if self.game_over and game_over_start_time is not None:
                outro_duration = 5.0
                # Scale outro duration when exporting video with time scaling
                if config.EXPORT_VIDEO:
                    outro_duration *= config.EXPORT_TIME_SCALE

                if self.game_time - game_over_start_time > outro_duration:
                    print("\n🎬 Game complete!")
                    self.running = False

        self.cleanup()

    def cleanup(self):
        """
        Clean up and export video
        """
        self.audio_logger.stop()

        print("\n" + "=" * 60)
        print("  GAME STATISTICS")
        print("=" * 60)
        print(f"Total Fighters: {len(self.fighters)}")
        print(f"Total Eliminations: {self.total_eliminations}")
        print(f"Video Frames Captured: {self.recorder.get_frame_count()}")
        print(f"Video Duration: {self.recorder.get_video_duration():.1f}s")
        print("=" * 60)

        # Export video
        if config.EXPORT_VIDEO:
            self.recorder.export_video()

        self.sound.cleanup()
        pygame.quit()
        print("\n👋 Thanks for playing!")
