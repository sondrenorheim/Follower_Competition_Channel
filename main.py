#!/usr/bin/env python3
"""
Follower Battle Royale - Main Game Loop
A Battle Royale simulation for Instagram followers using Pygame

Author: Claude AI
Description: Simulates a shrinking-zone battle royale with followers
             competing to be the last one standing in a circular arena.
"""

import pygame
import random
import math
import time
import sys
import os
from typing import List

# Fix Windows console encoding to support UTF-8 characters
if os.name == 'nt':  # Windows
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass  # If this fails, emojis will be skipped but game will still run

# Import configuration
import config

# Import game modules
from modules import (
    InstagramAPI,
    Follower,
    Arena,
    PhysicsEngine,
    Renderer,
    VideoRecorder,
    ParticleSystem,
    SoundManager,
    ScoringSystem,
    PlayerStatistics,
    AudioLogger
)


class FollowerBattleRoyale:
    """
    Main game class orchestrating the battle royale simulation
    """

    def __init__(self):
        """
        Initialize the game
        """
        print("=" * 60)
        print("  FOLLOWER BATTLE ROYALE")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Follower Battle Royale")
        self.clock = pygame.time.Clock()

        # Initialize game components
        print("\n🎮 Initializing game components...")
        self.api = InstagramAPI()
        self.arena = Arena()
        self.physics = PhysicsEngine()
        self.renderer = Renderer(self.screen)
        self.audio_logger = AudioLogger()
        self.recorder = VideoRecorder(audio_logger=self.audio_logger)
        self.particles = ParticleSystem()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()

        # Preload audio files before game starts (prevents delays during gameplay)
        self.sound.preload_audio()

        # Game state
        self.followers: List[Follower] = []
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Game phases: "intro", "countdown", "playing", "finished"
        self.game_phase = "intro"
        self.phase_start_time = 0
        self.countdown_number = 3

        # Statistics
        self.total_eliminations = 0
        self.last_alive_count = 0

        # Dynamic scaling tracking
        self.initial_total_players = 0
        self.initial_zone_radius = 0
        self.last_follower_radius = config.FOLLOWER_RADIUS

        # Announcements tracking
        self.top_10_announced = False
        self.top_5_announced = False

        # Leaderboard data for display
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

        print("✅ Game initialized successfully!\n")

    def setup_followers(self):
        """
        Fetch/generate followers and place them in the arena
        """
        print(f"👥 Setting up {config.FOLLOWER_COUNT} followers...")

        # Fetch followers from API or generate placeholders
        follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        # Place followers randomly in arena
        for data in follower_data:
            # Random position within arena
            angle = random.random() * 2 * math.pi
            # Place within 80% of arena radius to give space from edge
            distance = random.random() * config.ARENA_INITIAL_RADIUS * 0.8
            x = config.ARENA_CENTER[0] + math.cos(angle) * distance
            y = config.ARENA_CENTER[1] + math.sin(angle) * distance

            follower = Follower(data, (x, y))
            self.followers.append(follower)

        # Store initial values for dynamic scaling
        self.initial_total_players = len(self.followers)
        self.initial_zone_radius = self.arena.initial_radius

        # Calculate and apply initial dynamic radius before game starts
        if config.USE_DYNAMIC_SCALING:
            initial_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=self.initial_total_players,  # All alive at start
                safe_zone_radius=self.arena.initial_radius,
                initial_zone_radius=self.initial_zone_radius
            )
            config.FOLLOWER_RADIUS = initial_radius
            config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
            self.last_follower_radius = initial_radius

            # Invalidate all follower surfaces so they render at correct size
            for follower in self.followers:
                follower.surface_needs_update = True

            print(f"🔧 Dynamic scaling enabled: follower radius = {initial_radius:.1f}px")

        print(f"✅ {len(self.followers)} followers spawned in arena\n")

    def update(self, dt: float):
        """
        Update game state

        Args:
            dt: Delta time in seconds
        """
        if self.game_over:
            return

        # Handle countdown phase
        if self.game_phase == "countdown":
            elapsed = time.time() - self.phase_start_time
            # Wait for countdown video/audio to finish before starting game
            countdown_duration = self.sound.countdown_audio_duration

            if elapsed >= countdown_duration:
                # Video finished, start game
                print("🔊 FIGHT!")
                self.game_phase = "playing"
                self.arena.start_shrinking()  # Activate continuous zone shrinking
                self.sound.set_music_volume_high()  # Raise music volume for gameplay
                print("\n🎮 Game starting!\n")
            else:
                # Update countdown number for display (if video not loaded)
                self.countdown_number = max(0, 3 - int(elapsed))

        # Update followers during ALL phases (intro, countdown, playing)
        # This makes them move around in the background
        for follower in self.followers:
            follower.update(dt, self.arena.center, self.arena.current_radius, self.followers)

            # Only check safe zone during PLAYING phase (not during intro/countdown)
            if self.game_phase == "playing":
                was_alive = follower.alive
                follower.check_safe_zone(self.arena.center, self.arena.current_radius, self.particles)

                # If follower was just eliminated, add to kill feed and play sound
                if was_alive and not follower.alive:
                    self.renderer.add_elimination(follower.username)
                    self.sound.play_elimination()

        # Update physics (collisions) - works in all phases
        self.physics.update(self.followers, dt)

        # Resolve any overlaps immediately (prevents followers from overlapping)
        self.physics.resolve_overlaps(self.followers)

        # Apply very gentle separation force to prevent stacking without interfering with combat
        self.physics.apply_separation_force(self.followers, strength=0.2)

        # Update particle system
        self.particles.update(dt)

        # Update background music volume (smooth transitions)
        self.sound.update_music_volume()

        # Only do game logic updates during PLAYING phase
        if self.game_phase == "playing":
            # Update arena (zone shrinking)
            zone_shrunk = self.arena.update(dt)
            if zone_shrunk:
                self.sound.play_zone_warning()

            # Check game over conditions
            alive_followers = [f for f in self.followers if f.alive]
            alive_count = len(alive_followers)

            # Update dynamic follower radius based on player count
            if config.USE_DYNAMIC_SCALING:
                new_radius = config.calculate_dynamic_follower_radius(
                    total_players=self.initial_total_players,
                    alive_count=alive_count,
                    safe_zone_radius=self.arena.current_radius,
                    initial_zone_radius=self.initial_zone_radius
                )

                # If radius changed significantly, invalidate cached surfaces
                if abs(new_radius - self.last_follower_radius) > 0.5:
                    for follower in self.followers:
                        follower.surface_needs_update = True
                    self.last_follower_radius = new_radius

                config.FOLLOWER_RADIUS = new_radius
                # Update collision distance to match new radius
                config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

            # Update music intensity based on alive count
            self.sound.update_music_intensity(alive_count, len(self.followers))

            # Announcements for milestones
            if alive_count == 10 and not self.top_10_announced:
                self.top_10_announced = True
                self.sound.play_announcement("top10")
                print("\n🎺 TOP 10 SURVIVORS!\n")
            elif alive_count == 5 and not self.top_5_announced:
                self.top_5_announced = True
                self.sound.play_announcement("top5")
                print("\n🎺 FINAL 5!\n")

            # Print elimination updates
            if alive_count != self.last_alive_count:
                eliminated = self.last_alive_count - alive_count
                if eliminated > 0:
                    self.total_eliminations += eliminated
                    print(f"💀 {eliminated} eliminated - {alive_count} remaining")
                self.last_alive_count = alive_count

            # Game over when 1 or 0 survivors remain
            if alive_count <= 1:
                if not self.game_over:
                    self.game_over = True
                    self.sound.play_winner_celebration()
                    self._handle_game_over(alive_followers)

    def render(self):
        """
        Render current game state
        """
        # Prepare game state dictionary for renderer
        game_state = {
            "game_over": self.game_over,
            "total_eliminations": self.total_eliminations,
            "game_phase": self.game_phase,
            "countdown_number": self.countdown_number,
            "day_number": getattr(config, 'DAY_NUMBER', 1),
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "all_followers": self.followers,  # For avatar lookup in leaderboards
        }

        # Render frame with particle system
        self.renderer.render_frame(self.followers, self.arena, game_state, self.particles)

        # Record frame for video (only from countdown onwards, skip intro)
        if self.game_phase in ("countdown", "playing", "finished"):
            self.recorder.capture_frame(self.screen)

        # Update display
        pygame.display.flip()

    def _handle_game_over(self, survivors: List[Follower]):
        """
        Handle game over logic

        Args:
            survivors: List of surviving followers
        """
        duration = time.time() - self.game_start_time
        print("\n" + "=" * 60)
        print("  🏆 GAME OVER 🏆")
        print("=" * 60)
        print(f"Duration: {duration:.1f}s")
        print(f"Total Eliminations: {self.total_eliminations}")
        print(f"Zone Shrinks: {self.arena.total_shrinks}")

        if survivors:
            print(f"\n🥇 WINNER: {survivors[0].username}")
        else:
            print("\n💀 No survivors!")

        print("=" * 60)

        # Calculate scores and update statistics
        self._calculate_and_save_scores()

        # Show podium animation for a few seconds
        print("\n🎬 Showing final podium animation...")

    def _calculate_and_save_scores(self):
        """
        Calculate scores for all followers and update statistics
        """
        print("\n📊 Calculating scores...")

        # Sort followers by survival time (alive followers first, then by elimination time)
        sorted_followers = sorted(
            self.followers,
            key=lambda f: (not f.alive, -f.get_survival_time()),
            reverse=False
        )

        # Calculate points for each follower
        total_participants = len(self.followers)
        game_results = []

        for placement, follower in enumerate(sorted_followers, start=1):
            # Get number of games played before this game
            games_played = self.statistics.get_games_played(follower.username)

            # Calculate points
            survival_time = follower.get_survival_time()
            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played
            )

            points_earned = points_breakdown["total_points"]

            # Update player statistics (including kills from pushing)
            self.statistics.update_player_stats(
                username=follower.username,
                placement=placement,
                points_earned=points_earned,
                survival_time=survival_time,
                total_participants=total_participants,
                kills=follower.kills
            )

            # Store for leaderboard
            game_results.append((
                follower.username,
                placement,
                points_earned,
                survival_time
            ))

        # Save statistics to file
        self.statistics.save_statistics()

        # Store leaderboards for display
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = self.statistics.get_all_time_leaderboard(top_n=10)

        # Display current game leaderboard
        print(self.scoring.format_leaderboard(
            self.current_game_leaderboard,
            top_n=10,
            title="CURRENT GAME - TOP 10"
        ))

        # Display all-time leaderboard
        self.statistics.print_all_time_stats(top_n=10)

        # Display summary statistics
        summary = self.statistics.get_summary()
        print(f"\n📈 Total players tracked: {summary['total_players']}")
        if summary['highest_scorer']:
            print(f"🏆 All-time leader: {summary['highest_scorer']} "
                  f"({summary['highest_score']:.1f} points)")

    def run(self):
        """
        Main game loop
        """
        # Setup
        self.setup_followers()
        self.last_alive_count = len(self.followers)

        # Start audio event logging
        self.audio_logger.start()

        # Start background music (low volume during intro)
        self.sound.start_background_music()

        # Intro sequence
        print("🎮 Starting intro sequence...\n")
        print("=" * 60)

        # Set to intro phase
        self.game_phase = "intro"
        day_number = getattr(config, 'DAY_NUMBER', 1)
        intro_text = f"Day {day_number} of making my followers fight each other"

        # Play intro audio file (Day X + "making my followers fight each other")
        self.sound.play_intro_audio()

        # Display intro for the duration of the audio
        intro_start = time.time()
        intro_duration = self.sound.get_total_intro_duration() + 0.5  # Add small buffer

        print(f"🔊 {intro_text}")

        # Keep rendering intro until duration is up or speech is done
        while time.time() - intro_start < intro_duration:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return

            dt = self.clock.tick(config.FPS) / 1000.0

            # Update followers so they move around during intro
            for follower in self.followers:
                follower.update(dt, self.arena.center, self.arena.current_radius, self.followers)

            # Update physics (collisions) so followers interact naturally
            self.physics.update(self.followers, dt)
            self.physics.resolve_overlaps(self.followers)
            self.physics.apply_separation_force(self.followers, strength=0.2)

            # Update particle system
            self.particles.update(dt)

            # Update music volume (smooth transitions)
            self.sound.update_music_volume()

            self.render()

        # Start countdown
        print("\n⏱️  Starting countdown...")
        self.game_phase = "countdown"
        self.phase_start_time = time.time()
        self.countdown_number = 3
        self.renderer.start_countdown_video()  # Start the video overlay
        self.sound.play_countdown_audio()  # Play the countdown video audio

        # Track time for podium display
        game_over_start_time = None

        # Main loop
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Calculate delta time
            dt = self.clock.tick(config.FPS) / 1000.0  # Convert to seconds

            # Update game state
            self.update(dt)

            # Render
            self.render()

            # If game just ended, start timer for podium display
            if self.game_over and game_over_start_time is None:
                game_over_start_time = time.time()

            # After showing podium for 5 seconds, end the game
            if self.game_over and game_over_start_time:
                if time.time() - game_over_start_time > 5.0:
                    print("\n🎬 Game complete!")
                    self.running = False

        # Cleanup
        self.cleanup()

    def cleanup(self):
        """
        Clean up and export video
        """
        # Stop audio event logging
        self.audio_logger.stop()

        print("\n" + "=" * 60)
        print("  GAME STATISTICS")
        print("=" * 60)
        print(f"Total Followers: {len(self.followers)}")
        print(f"Total Eliminations: {self.total_eliminations}")
        print(f"Zone Shrinks: {self.arena.total_shrinks}")
        print(f"Collision Checks: {self.physics.collision_checks}")
        print(f"Collisions Detected: {self.physics.collisions_detected}")
        print(f"Video Frames Captured: {self.recorder.get_frame_count()}")
        print(f"Video Duration: {self.recorder.get_video_duration():.1f}s")
        print("=" * 60)

        # Export video
        if config.EXPORT_VIDEO:
            self.recorder.export_video()

        # Cleanup sound
        self.sound.cleanup()

        # Quit pygame
        pygame.quit()
        print("\n👋 Thanks for playing!")


def main():
    """
    Entry point for the game
    Selects game mode based on config.GAME_MODE
    """
    try:
        # Select game mode based on config
        game_mode = getattr(config, 'GAME_MODE', 'battle_royale')

        if game_mode == "fighter_arena":
            # Import and run Fighter Arena
            from modules import FighterBattleArena
            print("🥊 Starting Fighter Arena mode...")
            game = FighterBattleArena()
        elif game_mode == "obstacle_course":
            # Import and run Obstacle Course
            from modules import ObstacleCourseGame
            print("Starting Obstacle Course mode...")
            game = ObstacleCourseGame()
        else:
            # Default to Battle Royale
            print("Starting Battle Royale mode...")
            game = FollowerBattleRoyale()

        game.run()
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
