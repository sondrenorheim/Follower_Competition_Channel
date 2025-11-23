"""
Game Template - Blueprint for creating new games
Copy this file to your new game folder and customize it.

This template provides:
- Standard pygame initialization (540x960 screen)
- Instagram/TikTok follower import
- Standard game phases (intro -> countdown -> playing -> finished)
- Scoring system (100 points descending by placement)
- Persistent player statistics
- Video recording/export
- Leaderboard display at the end

Usage:
1. Copy this file to your_game/game.py
2. Rename the class to match your game (e.g., YourGameGame)
3. Implement the abstract methods marked with # TODO
4. Customize game-specific logic
"""

import pygame
import time
import cv2
import numpy as np
from typing import List, Optional, Dict, Any

import config
from shared import (
    InstagramAPI,
    PlayerStatistics,
    ScoringSystem,
    SoundManager,
    AudioLogger,
    VideoRecorder
)

# TODO: Import your custom modules
# from .player import Player
# from .arena import Arena
# from .renderer import GameRenderer


# =============================================================================
# GAME AREA CONSTANTS - Standard layout for all games
# =============================================================================

# Default game area dimensions (matches obstacle course track width)
DEFAULT_GAME_WIDTH = 500  # Same as config.OBSTACLE_COURSE_WIDTH
DEFAULT_GAME_HEIGHT = 700  # Full vertical simulation area

# Calculated positions (centered on 540x960 screen)
GAME_AREA_LEFT = (config.SCREEN_WIDTH - DEFAULT_GAME_WIDTH) // 2  # 20px
GAME_AREA_TOP = 160  # Below title/subtitle
GAME_AREA_RIGHT = GAME_AREA_LEFT + DEFAULT_GAME_WIDTH  # 520px
GAME_AREA_BOTTOM = GAME_AREA_TOP + DEFAULT_GAME_HEIGHT  # 860px

# Title positions
TITLE_Y = 60  # Title text Y position
SUBTITLE_Y = 100  # "Making my followers battle every day" Y position
DAY_COUNTER_Y = GAME_AREA_BOTTOM + 30  # Day counter below game area


class GameTemplate:
    """
    Template for creating new follower battle games.

    This class provides the standard structure and features that all games should have:
    - Follower import from Instagram/TikTok
    - Scoring based on placement (100 points for 1st, descending)
    - Persistent statistics tracking
    - Video export when enabled
    - Consistent UI layout with title, subtitle, and day counter
    - End-game leaderboard display

    Subclasses should override methods marked with # TODO to implement
    game-specific behavior.
    """

    # =============================================================================
    # CONFIGURATION - Override these in your subclass
    # =============================================================================

    GAME_TITLE = "GAME TITLE"  # Override with your game title
    GAME_SUBTITLE = "Making my followers battle every day"  # Standard subtitle
    PLAYER_LABEL = "players"  # e.g., "racers", "fighters", "followers"

    # Game area dimensions (override if needed)
    GAME_WIDTH = DEFAULT_GAME_WIDTH
    GAME_HEIGHT = DEFAULT_GAME_HEIGHT

    def __init__(self):
        """Initialize the game with all standard components."""
        print("=" * 60)
        print(f"  {self.GAME_TITLE}")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(self.GAME_TITLE)
        self.clock = pygame.time.Clock()

        # Initialize shared components
        print(f"\nInitializing {self.GAME_TITLE}...")
        self.api = InstagramAPI()
        self.audio_logger = AudioLogger()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        # Set green screen overlay for video export
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.5,
            offset_y=70
        )
        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()

        # Preload audio
        self.sound.preload_audio()

        # Game state
        self.players: List[Any] = []  # Override type hint with your player class
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Game phases: "intro" -> "countdown" -> "playing" -> "finished"
        self.phase = "intro"

        # Leaderboards for end-game display
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []
        self.show_leaderboards = False
        self.leaderboard_display_start = None
        self.winner = None

        # Countdown video
        self.countdown_video = None
        self.countdown_fps = 30
        self.countdown_duration = 0
        self.countdown_start_time = None
        self._load_countdown_video()

        # Initialize game-specific components
        self._init_game_components()

        print(f"{self.GAME_TITLE} initialized!\n")

    def _init_game_components(self):
        """
        Initialize game-specific components.
        Override this method to set up your arena, renderer, etc.

        Example:
            self.arena = Arena()
            self.renderer = GameRenderer(self.screen)
            self.particles = ParticleSystem()
        """
        # TODO: Initialize your game-specific components
        pass

    def _load_countdown_video(self):
        """Load the Smash Ultimate countdown video for the countdown phase."""
        video_path = "assets/smash ultimate 3 2 1 go green screen.mp4"

        try:
            self.countdown_video = cv2.VideoCapture(video_path)

            if not self.countdown_video.isOpened():
                print(f"Could not load countdown video: {video_path}")
                self.countdown_video = None
                return

            self.countdown_fps = self.countdown_video.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.countdown_video.get(cv2.CAP_PROP_FRAME_COUNT))
            self.countdown_duration = frame_count / self.countdown_fps

            print(f"Loaded countdown video: {self.countdown_duration:.1f}s @ {self.countdown_fps} FPS")

        except Exception as e:
            print(f"Error loading countdown video: {e}")
            self.countdown_video = None

    # =============================================================================
    # PLAYER SETUP
    # =============================================================================

    def setup_players(self):
        """
        Fetch followers and create player entities.
        This method handles the standard follower import from Instagram/TikTok.

        Override _create_player() to customize how players are created.
        Override _get_starting_position() to customize starting positions.
        """
        print(f"Setting up {config.FOLLOWER_COUNT} {self.PLAYER_LABEL}...")

        # Fetch followers using the standard API
        follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        # Randomize order for varied starting positions
        import random
        random.shuffle(follower_data)

        # Create players
        for i, data in enumerate(follower_data):
            position = self._get_starting_position(i, len(follower_data))
            player = self._create_player(data, position)
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _create_player(self, follower_data: dict, position: tuple) -> Any:
        """
        Create a player entity from follower data.
        Override this method to create your specific player type.

        Args:
            follower_data: Dictionary with 'id', 'username', 'avatar', optionally 'color'
            position: (x, y) starting position

        Returns:
            Player entity

        Example:
            return Player(follower_data, position)
        """
        # TODO: Return your player type
        raise NotImplementedError("Override _create_player() to create your player type")

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        """
        Calculate starting position for a player.
        Override this method to customize starting positions.

        Args:
            index: Player index (0 to total_players-1)
            total_players: Total number of players

        Returns:
            (x, y) tuple for starting position

        Default: Random position within game area
        """
        import random

        # Calculate game area bounds
        left = GAME_AREA_LEFT + config.FOLLOWER_RADIUS
        right = GAME_AREA_RIGHT - config.FOLLOWER_RADIUS
        top = GAME_AREA_TOP + config.FOLLOWER_RADIUS
        bottom = GAME_AREA_BOTTOM - config.FOLLOWER_RADIUS

        x = random.uniform(left, right)
        y = random.uniform(top, bottom)

        return (x, y)

    # =============================================================================
    # GAME LOOP
    # =============================================================================

    def run(self):
        """Main game loop with standard phases."""
        # Setup players
        self.setup_players()

        # Countdown phase
        print("\nStarting countdown...")
        self.countdown_start_time = time.time()
        self.phase = "countdown"

        # Start background music at low volume
        self.sound.start_background_music()
        self.sound.set_music_volume_low()

        # Play the countdown audio
        self.sound.play_smash_countdown_audio()

        # Countdown loop - players wait at starting positions
        countdown_active = True
        while countdown_active and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return

            dt = self.clock.tick(config.FPS) / 1000.0

            # Check if countdown finished
            elapsed = time.time() - self.countdown_start_time
            if elapsed >= self.countdown_duration:
                countdown_active = False
                self.phase = "playing"
                print("\nGO! Game started!")
                self.sound.set_music_volume_high()

            # Render (countdown frame will be added during video export)
            self.render()

        # Reset countdown start time
        self.countdown_start_time = None

        # Main game loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            dt = self.clock.tick(config.FPS) / 1000.0

            self.update(dt)
            self.render()

            # Auto-close after leaderboards shown for 5 seconds
            if self.game_over and self.show_leaderboards:
                if time.time() - self.leaderboard_display_start >= 5.0:
                    self.running = False

        self.cleanup()

    def update(self, dt: float):
        """
        Update game state.
        Override this method to implement your game logic.

        Args:
            dt: Delta time in seconds
        """
        if self.game_over:
            return

        # TODO: Implement your game update logic
        # Example:
        # - Update player positions
        # - Check collisions
        # - Check win/lose conditions
        # - Update particles
        # - Check for game over
        pass

    def render(self):
        """
        Render the current game state.
        Override this method to implement your rendering.
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # TODO: Implement your rendering
        # Example:
        # self.renderer.render_frame(self.players, self.arena, game_state)

        pygame.display.flip()

        # Capture frame for video export
        self.recorder.capture_frame(self.screen)

    # =============================================================================
    # SCORING AND STATISTICS
    # =============================================================================

    def finish_game(self, sorted_players: List[Any]):
        """
        Finish the game and calculate final scores.
        Call this method when the game ends.

        Args:
            sorted_players: List of players sorted by placement (1st place first)
        """
        self.game_over = True
        self.phase = "finished"

        # Assign placements
        for i, player in enumerate(sorted_players):
            player.placement = i + 1

        # Set winner
        if sorted_players:
            self.winner = sorted_players[0]

        # Print results
        print("\n" + "=" * 60)
        print("  GAME COMPLETE")
        print("=" * 60)

        print("\nTop 10:")
        for i, player in enumerate(sorted_players[:10]):
            print(f"{i+1}. {player.username}")

        # Calculate and save scores
        self._calculate_and_save_scores(sorted_players)

    def _calculate_and_save_scores(self, sorted_players: List[Any]):
        """Calculate scores for all players and update statistics."""
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)

            # Calculate base points from placement
            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=getattr(player, 'survival_time', 0),
                games_played=games_played
            )

            # Apply game-specific bonus points
            base_points = points_breakdown["total_points"]
            bonus_points = self._calculate_bonus_points(player)
            total_points = base_points + bonus_points

            # Store for current game leaderboard
            survival_time = getattr(player, 'survival_time', 0)
            game_results.append((player.username, placement, total_points, survival_time))

            # Update persistent stats
            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=total_points,
                survival_time=survival_time,
                total_participants=total_participants
            )

        # Save statistics
        self.statistics.save_statistics()
        print("Statistics saved!")

        # Generate leaderboards for display
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = self.statistics.get_all_time_leaderboard(top_n=10)

        # Enable leaderboard display
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()

    def _calculate_bonus_points(self, player: Any) -> float:
        """
        Calculate game-specific bonus points for a player.
        Override this method to add custom bonuses.

        Args:
            player: The player to calculate bonuses for

        Returns:
            Bonus points to add to the base placement points

        Example bonuses:
            - Most kills bonus
            - Speed bonus
            - Survival time bonus
        """
        # Default: no bonus points
        return 0.0

    # =============================================================================
    # CLEANUP
    # =============================================================================

    def cleanup(self):
        """Clean up and export video."""
        print("\n" + "=" * 60)
        print("  GAME STATISTICS")
        print("=" * 60)
        print(f"Total {self.PLAYER_LABEL.capitalize()}: {len(self.players)}")
        if self.winner:
            print(f"Winner: {self.winner.username}")
        print(f"Video Frames Captured: {self.recorder.get_frame_count()}")
        print(f"Video Duration: {self.recorder.get_video_duration():.1f}s")
        print("=" * 60)

        # Export video if enabled in config
        if config.EXPORT_VIDEO:
            self.recorder.export_video()

        pygame.quit()
        print(f"\nThanks for playing {self.GAME_TITLE}!")

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def get_game_area_bounds(self) -> tuple:
        """
        Get the game area boundaries.

        Returns:
            (left, top, right, bottom) tuple
        """
        left = (config.SCREEN_WIDTH - self.GAME_WIDTH) // 2
        top = GAME_AREA_TOP
        right = left + self.GAME_WIDTH
        bottom = top + self.GAME_HEIGHT
        return (left, top, right, bottom)

    def get_game_area_center(self) -> tuple:
        """
        Get the center of the game area.

        Returns:
            (x, y) tuple
        """
        left, top, right, bottom = self.get_game_area_bounds()
        return ((left + right) // 2, (top + bottom) // 2)

    def is_inside_game_area(self, x: float, y: float, margin: float = 0) -> bool:
        """
        Check if a point is inside the game area.

        Args:
            x, y: Position to check
            margin: Optional margin (positive = inside, negative = outside)

        Returns:
            True if inside game area
        """
        left, top, right, bottom = self.get_game_area_bounds()
        return (left + margin <= x <= right - margin and
                top + margin <= y <= bottom - margin)
