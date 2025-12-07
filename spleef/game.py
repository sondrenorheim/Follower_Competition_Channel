"""
SpleefGame Module
Main game orchestrator for Spleef mode
"""

import pygame
import time
from typing import List
from PIL import Image
import numpy as np

import config
from shared import (
    InstagramAPI,
    SoundManager,
    ScoringSystem,
    PlayerStatistics,
    GameHistory,
    VideoRecorder,
    AudioLogger,
    auto_push
)
from spleef.arena import SpleefArena
from spleef.player import SpleefPlayer
from spleef.physics import SpleefPhysics
from spleef.ai import SpleefAI
from spleef.renderer import SpleefRenderer


class SpleefGame:
    """
    Main Spleef game orchestrator
    Integrates with shared systems and manages game flow
    """

    def __init__(self):
        """Initialize Spleef game"""
        print("=" * 60)
        print("  SPLEEF - FALLING FLOOR BATTLE")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Spleef - Falling Floor Battle")
        self.clock = pygame.time.Clock()

        # Initialize shared systems
        print("\n🎮 Initializing game components...")
        self.api = InstagramAPI()
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
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.game_history = GameHistory()
        self.scoring = ScoringSystem()

        # Preload audio
        self.sound.preload_audio()

        # Game systems
        self.arena = SpleefArena(center_x=270, top_y=200)
        self.physics = SpleefPhysics()
        self.ai = SpleefAI()
        self.renderer = SpleefRenderer(width=config.SCREEN_WIDTH, height=config.SCREEN_HEIGHT)

        # Players
        self.players: List[SpleefPlayer] = []

        # Game state
        self.phase = "intro"  # intro, countdown, playing, finished
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()
        self.game_time = 0.0
        self.last_update_time = time.time()
        self.recording_start_time = None

        # Phase durations
        self.intro_duration = 3.0
        self.countdown_duration = 3.5
        self.winner_display_duration = 10.0

        # Statistics
        self.elimination_order = []  # Track order of eliminations
        self.day_number = config.DAY_NUMBER
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

        print(f"Arena initialized: {self.arena}")
        print(f"Physics system: {self.physics}")
        print(f"AI system: {self.ai}")
        print(f"Renderer: {self.renderer}")

    def load_players_from_instagram(self):
        """Load players from Instagram followers or generate test players"""

        # Check if we should use minimal test players
        if getattr(config, 'TEST_MINIMAL_PLAYERS', False):
            print("\n🧪 Generating test players...")
            test_count = getattr(config, 'TEST_MINIMAL_PLAYER_COUNT', 50)

            # Generate test players
            for i in range(test_count):
                player = SpleefPlayer(
                    username=f"player_{i+1}",
                    display_name=f"TestPlayer{i+1}",
                    avatar=None
                )
                self.players.append(player)

            print(f"✅ Generated {len(self.players)} test players")
        else:
            print("\n📥 Loading players from Instagram followers...")

            # Fetch followers using shared API
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)
            print(f"Loaded {len(follower_data)} followers")

            # Create SpleefPlayer instances
            for data in follower_data:
                player = SpleefPlayer(
                    username=data['username'],
                    display_name=data.get('display_name', data['username']),
                    avatar=data.get('avatar')
                )
                self.players.append(player)

        # Spawn players on top layer
        spawn_positions = self.arena.get_spawn_positions(len(self.players))

        for player, (spawn_x, spawn_y, layer) in zip(self.players, spawn_positions):
            player.set_spawn_position(spawn_x, spawn_y, layer)

        print(f"✅ Spawned {len(self.players)} players on arena")

    def update_phase(self):
        """Update game phase based on time and conditions"""
        if self.phase == "intro":
            if self.game_time >= self.intro_duration:
                self.phase = "countdown"
                self.game_start_time = time.time()  # Reset for countdown
                print("\n⏰ Phase: COUNTDOWN")

        elif self.phase == "countdown":
            if self.game_time >= self.countdown_duration:
                self.phase = "playing"
                self.game_start_time = time.time()  # Reset for gameplay
                self.sound.start_background_music()
                print("\n🎮 Phase: PLAYING")

        elif self.phase == "playing":
            # Check if only one player remains
            alive_players = [p for p in self.players if p.alive]
            if len(alive_players) <= 1:
                self.phase = "finished"
                self.game_start_time = time.time()  # Reset for winner display
                print("\n🏆 Phase: FINISHED")

                # Assign final placement to winner
                if len(alive_players) == 1:
                    winner = alive_players[0]
                    winner.placement = 1
                    winner.elimination_time = time.time()
                    print(f"👑 Winner: {winner.display_name}")
                    self.sound.play_winner_celebration()

        elif self.phase == "finished":
            if self.game_time >= self.winner_display_duration:
                self.game_over = True

    def update_players(self, dt: float):
        """Update all player logic"""
        if self.phase != "playing":
            return

        # AI decisions
        ai_decisions = self.ai.update_all_players_ai(self.players, self.arena, self.game_time)

        # Apply AI movement to physics
        for player in self.players:
            if player.alive:
                direction = ai_decisions.get(player.username, (0, 0))
                self.physics.apply_movement_input(player, direction[0], direction[1])

        # Update physics for all players
        self.physics.update_all_players(self.players, self.arena, dt)

        # Track newly eliminated players
        for player in self.players:
            if not player.alive and player.placement is None:
                # Player just got eliminated
                placement = len(self.players) - len(self.elimination_order)
                player.placement = placement
                self.elimination_order.append(player)
                print(f"💀 Eliminated: {player.display_name} (Placement: #{placement})")

                # Play elimination sound
                if placement <= 10:
                    self.sound.play_elimination()

    def update_arena(self, dt: float):
        """Update arena blocks"""
        if self.phase == "playing":
            self.arena.update(self.players, dt)

    def update(self, dt: float):
        """
        Main game update loop

        Args:
            dt: Delta time in seconds
        """
        # Cap delta time to prevent huge jumps
        dt = min(dt, config.MAX_DELTA_TIME)

        # Calculate game time
        self.game_time = time.time() - self.game_start_time

        # Update phase transitions
        self.update_phase()

        # Update game logic
        self.update_players(dt)
        self.update_arena(dt)

    def render_to_pil(self) -> Image.Image:
        """
        Render current game state to PIL Image

        Returns:
            PIL Image of current frame
        """
        return self.renderer.render_frame(
            arena=self.arena,
            players=self.players,
            game_time=self.game_time,
            phase=self.phase
        )

    def render(self):
        """Render current frame to pygame screen"""
        # Render to PIL image
        pil_image = self.render_to_pil()

        # Convert PIL to pygame surface
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()

        pygame_surface = pygame.image.fromstring(data, size, mode)

        # Blit to screen
        self.screen.blit(pygame_surface, (0, 0))
        pygame.display.flip()

    def get_results(self) -> List[dict]:
        """
        Get final game results

        Returns:
            List of player result dictionaries sorted by placement
        """
        results = []

        for player in self.players:
            result = {
                'username': player.username,
                'display_name': player.display_name,
                'placement': player.placement if player.placement else len(self.players),
                'score': player.calculate_score(),
                'blocks_broken': player.blocks_broken,
                'layer_reached': player.current_layer,
            }
            results.append(result)

        # Sort by placement
        results.sort(key=lambda x: x['placement'])

        return results

    def save_statistics(self):
        """Save game statistics and update leaderboards"""
        print("\n📊 Saving statistics...")

        results = self.get_results()

        # Convert to scoring format
        scored_results = []
        for result in results:
            scored_results.append({
                'username': result['username'],
                'display_name': result['display_name'],
                'placement': result['placement'],
                'score': result['score']
            })

        # Calculate scores using scoring system
        self.current_game_leaderboard = self.scoring.calculate_scores(
            results=scored_results,
            game_mode="spleef"
        )

        # Update all-time leaderboard
        if not config.TEST_MODE:
            self.statistics.update_from_game_results(
                self.current_game_leaderboard,
                game_mode="spleef",
                day=self.day_number
            )
            self.all_time_leaderboard = self.statistics.get_all_time_leaderboard()

            # Save to history
            self.game_history.save_game_session(
                game_mode="spleef",
                day_number=self.day_number,
                date=time.strftime("%Y-%m-%d"),
                results=self.current_game_leaderboard
            )

            print("✅ Statistics saved successfully")
        else:
            print("⚠️  TEST MODE - Statistics not saved to all-time leaderboard")

    def run(self):
        """Main game loop (matches interface of other games)"""
        print("\n🚀 Starting Spleef game...")

        # Load players
        self.load_players_from_instagram()

        # Start phase timers
        self.phase = "intro"
        self.game_start_time = time.time()
        self.last_update_time = time.time()

        # Main game loop
        frame_count = 0

        while self.running and not self.game_over:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Calculate delta time
            current_time = time.time()
            dt = current_time - self.last_update_time
            self.last_update_time = current_time

            # Update game state
            self.update(dt)

            # Render frame
            self.render()

            # Record frame if enabled
            if config.EXPORT_VIDEO:
                self.recorder.capture_frame(self.screen, current_time)

            # Cap framerate
            target_fps = config.FPS
            if config.EXPORT_VIDEO:
                target_fps = config.SIMULATION_FPS_DURING_EXPORT
            self.clock.tick(target_fps)

            frame_count += 1

            # Progress update every 60 frames
            if frame_count % 60 == 0 and self.phase == "playing":
                alive = sum(1 for p in self.players if p.alive)
                solid = self.arena.get_total_solid_blocks()
                print(f"📊 Frame {frame_count}: {alive} players alive, {solid} blocks solid")

        # Game finished
        print("\n" + "=" * 60)
        print("GAME FINISHED")
        print("=" * 60)

        # Export video
        if config.EXPORT_VIDEO:
            print("\n🎬 Finalizing video...")
            self.recorder.export_video()
            print(f"✅ Video saved to: {self.recorder.output_path}")

        # Save statistics
        self.save_statistics()

        # Print top results
        results = self.get_results()
        print("\n🏆 Top 10 Results:")
        for i, result in enumerate(results[:10], 1):
            print(f"  {i}. {result['display_name']} - "
                  f"Score: {result['score']} - "
                  f"Blocks: {result['blocks_broken']} - "
                  f"Layer: {result['layer_reached']}")

        # Auto-push stats if enabled
        if config.AUTO_PUSH_STATS and not config.TEST_MODE:
            print("\n📤 Auto-pushing statistics...")
            auto_push()

        # Cleanup
        print("\n🧹 Cleaning up...")
        self.sound.cleanup()
        pygame.quit()
        print("\n👋 Thanks for playing Spleef!")

    def __repr__(self):
        alive = sum(1 for p in self.players if p.alive)
        return f"SpleefGame(phase={self.phase}, players={len(self.players)}, alive={alive})"
