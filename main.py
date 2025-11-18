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
from typing import List

# Import configuration
import config

# Import game modules
from modules import (
    InstagramAPI,
    Follower,
    Arena,
    PhysicsEngine,
    Renderer,
    VideoRecorder
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
        self.recorder = VideoRecorder()

        # Game state
        self.followers: List[Follower] = []
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Statistics
        self.total_eliminations = 0
        self.last_alive_count = 0

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

        print(f"✅ {len(self.followers)} followers spawned in arena\n")

    def update(self, dt: float):
        """
        Update game state

        Args:
            dt: Delta time in seconds
        """
        if self.game_over:
            return

        # Update arena (zone shrinking)
        zone_shrunk = self.arena.update(dt)

        # Update all followers
        for follower in self.followers:
            follower.update(dt, self.arena.center, self.arena.current_radius, self.followers)

            # Check safe zone
            follower.check_safe_zone(self.arena.center, self.arena.current_radius)

        # Update physics (collisions)
        self.physics.update(self.followers, dt)

        # Apply gentle separation to prevent stacking
        if random.random() < 0.1:  # Only apply occasionally for performance
            self.physics.apply_separation_force(self.followers)

        # Check game over conditions
        alive_followers = [f for f in self.followers if f.alive]
        alive_count = len(alive_followers)

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
                self._handle_game_over(alive_followers)

    def render(self):
        """
        Render current game state
        """
        # Prepare game state dictionary for renderer
        game_state = {
            "game_over": self.game_over,
            "total_eliminations": self.total_eliminations,
        }

        # Render frame
        self.renderer.render_frame(self.followers, self.arena, game_state)

        # Record frame for video
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

        # Show podium animation for a few seconds
        print("\n🎬 Showing final podium animation...")

    def run(self):
        """
        Main game loop
        """
        # Setup
        self.setup_followers()
        self.last_alive_count = len(self.followers)

        print("🎮 Starting game loop...\n")
        print("=" * 60)

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

        # Quit pygame
        pygame.quit()
        print("\n👋 Thanks for playing!")


def main():
    """
    Entry point for the game
    """
    try:
        game = FollowerBattleRoyale()
        game.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Game interrupted by user")
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
