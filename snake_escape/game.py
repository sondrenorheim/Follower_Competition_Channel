"""
Snake Escape Game - Main game controller.

A survival game where followers must escape from a hungry snake.
Last survivor wins!
"""

import pygame
import random
import math
import time
from typing import List, Optional

import config
from shared import (
    InstagramAPI,
    PlayerStatistics,
    GameHistory,
    ScoringSystem,
    SoundManager,
    AudioLogger,
    VideoRecorder,
    ParticleSystem,
    PhysicsEngine,
    auto_push
)

from .arena import SnakeEscapeArena
from .snake import Snake
from .follower import SnakeEscapeFollower
from .renderer import SnakeEscapeRenderer


class SnakeEscapeGame:
    """
    Snake Escape game controller.

    Game flow:
    1. Followers spawn in the arena
    2. Countdown begins
    3. Snake spawns and starts hunting
    4. Followers try to survive by fleeing and pushing others toward the snake
    5. Snake gets faster as followers are eliminated
    6. Last survivor wins
    """

    GAME_TITLE = "SNAKE ESCAPE"
    PLAYER_LABEL = "survivors"

    def __init__(self):
        """Initialize the game."""
        print("=" * 60)
        print(f"  {self.GAME_TITLE}")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()

        # Use HIDDEN flag if headless mode is enabled (no window, faster processing)
        display_flags = pygame.HIDDEN if config.HEADLESS_MODE else 0
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), display_flags)

        if not config.HEADLESS_MODE:
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
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.5,
            offset_y=70
        )
        self.statistics = PlayerStatistics()
        self.game_history = GameHistory()
        self.scoring = ScoringSystem()
        self.particles = ParticleSystem()
        self.physics = PhysicsEngine()  # Optimized collision detection with spatial grid + Numba

        # Preload audio
        self.sound.preload_audio()

        # Initialize game-specific components
        self.arena = SnakeEscapeArena()
        self.renderer = SnakeEscapeRenderer(self.screen)
        self.snakes: List[Snake] = []  # Support multiple snakes
        self.followers: List[SnakeEscapeFollower] = []

        # Game state
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Game phases: "intro" -> "countdown" -> "playing" -> "finished"
        self.phase = "intro"

        # Leaderboards
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []
        self.show_leaderboards = False
        self.leaderboard_display_start = None
        self.winner = None

        # Countdown
        self.countdown_start_time = None
        self.countdown_duration = 3.5  # Will be updated from sound

        # Statistics
        self.total_eliminations = 0
        self.initial_follower_count = 0

        # Performance optimization - update throttling for large player counts
        self.update_frame_counter = 0
        self.update_batches_per_frame = config.UPDATE_BATCHES_PER_FRAME

        print(f"{self.GAME_TITLE} initialized!\n")

    def setup_players(self):
        """Set up followers and spawn them in the arena."""
        print(f"Setting up {self.PLAYER_LABEL}...")

        # Fetch followers (support test mode)
        if config.TEST_MINIMAL_PLAYERS:
            print(f"🧪 TEST MODE: Using {config.TEST_MINIMAL_PLAYER_COUNT} test players")
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)
        random.shuffle(follower_data)

        # Store initial count for dynamic scaling
        self.initial_follower_count = len(follower_data)

        # Calculate initial dynamic radius based on player count
        if config.USE_DYNAMIC_SCALING:
            arena_bounds = self.arena.get_bounds()
            arena_width = arena_bounds[2] - arena_bounds[0]
            arena_height = arena_bounds[3] - arena_bounds[1]
            arena_radius = min(arena_width, arena_height) // 2

            initial_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_follower_count,
                alive_count=self.initial_follower_count,
                safe_zone_radius=arena_radius,
                initial_zone_radius=arena_radius
            )
            config.FOLLOWER_RADIUS = initial_radius
            config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

            print(f"🔧 Dynamic scaling: follower radius = {initial_radius:.1f}px")

        # Create followers at random positions
        for data in follower_data:
            position = self.arena.get_random_position(config.FOLLOWER_RADIUS + 10)
            follower = SnakeEscapeFollower(data, position)
            self.followers.append(follower)

        print(f"{len(self.followers)} {self.PLAYER_LABEL} ready!\n")

    def spawn_snakes(self):
        """Spawn snakes at random edges of the arena."""
        snake_count = getattr(config, 'SNAKE_COUNT', 1)
        bounds = self.arena.get_bounds()
        left, top, right, bottom = bounds

        edges = ['top', 'bottom', 'left', 'right']
        random.shuffle(edges)

        for i in range(snake_count):
            # Each snake spawns on a different edge if possible
            edge = edges[i % len(edges)]

            if edge == 'top':
                x = random.uniform(left + 50, right - 50)
                y = top + 30
            elif edge == 'bottom':
                x = random.uniform(left + 50, right - 50)
                y = bottom - 30
            elif edge == 'left':
                x = left + 30
                y = random.uniform(top + 50, bottom - 50)
            else:  # right
                x = right - 30
                y = random.uniform(top + 50, bottom - 50)

            snake = Snake((x, y))
            self.snakes.append(snake)

        print(f"{len(self.snakes)} snake(s) have entered the arena!")

    def update(self, dt: float):
        """
        Update game state.

        Args:
            dt: Delta time in seconds
        """
        if self.game_over:
            return

        current_time = time.time()

        # Get alive count
        alive_followers = [f for f in self.followers if f.alive]
        alive_count = len(alive_followers)

        # Update all snakes
        for snake in self.snakes:
            snake.update(dt, self.arena, self.followers)

            # Update snake speed based on eliminations
            snake.update_speed_scaling(alive_count, self.initial_follower_count)

            # Check if snake eats any followers
            for follower in self.followers:
                if follower.alive and snake.check_eat_follower(follower):
                    placement = alive_count  # Current place when eliminated
                    follower.eliminate(placement, self.particles)
                    self.total_eliminations += 1
                    self.renderer.add_elimination(follower.username) if hasattr(self.renderer, 'add_elimination') else None
                    self.sound.play_elimination()
                    print(f"Snake ate {follower.username}! {alive_count - 1} survivors remaining")

        # CRITICAL OPTIMIZATION: Only process ALIVE followers!
        # Dead followers don't need updates, physics, or repulsion
        alive_followers = [f for f in self.followers if f.alive]
        total_alive = len(alive_followers)

        # Performance optimization: Update throttling for large player counts
        if config.ENABLE_UPDATE_THROTTLING and total_alive > 5000:
            # Increment frame counter
            self.update_frame_counter += 1

            # Calculate which batch to update this frame
            batch_index = self.update_frame_counter % self.update_batches_per_frame
            batch_size = (total_alive + self.update_batches_per_frame - 1) // self.update_batches_per_frame

            # Calculate start and end indices for this batch
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, total_alive)

            followers_to_update = alive_followers[start_idx:end_idx]
        else:
            # For smaller player counts or if throttling disabled, update all ALIVE followers every frame
            followers_to_update = alive_followers

        # Update followers with simple random movement
        # No individual AI - they just wander!
        fake_snake = type('FakeSnake', (), {'x': -1000, 'y': -1000})()
        for follower in followers_to_update:
            follower.update(dt, self.arena, fake_snake, alive_followers)

        # Apply snake repulsion field (THIS IS THE MAGIC!)
        # Only affects ALIVE players near the snake
        if self.snakes and alive_followers:
            self._apply_snake_repulsion_field(dt, alive_followers)

        # Use PhysicsEngine for collision detection - ONLY for alive followers!
        # This is the fix for the Numba allocation error with 30 players
        if alive_followers:
            self.physics.update(alive_followers, dt)

        # Update particles
        self.particles.update(dt)

        # Update dynamic radius as players are eliminated
        if config.USE_DYNAMIC_SCALING:
            arena_bounds = self.arena.get_bounds()
            arena_width = arena_bounds[2] - arena_bounds[0]
            arena_height = arena_bounds[3] - arena_bounds[1]
            arena_radius = min(arena_width, arena_height) // 2

            new_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_follower_count,
                alive_count=alive_count,
                safe_zone_radius=arena_radius,
                initial_zone_radius=arena_radius
            )

            # Only update if radius changed significantly
            if abs(new_radius - config.FOLLOWER_RADIUS) > 0.5:
                config.FOLLOWER_RADIUS = new_radius
                config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

                # Update follower radius
                for follower in self.followers:
                    follower.radius = config.FOLLOWER_RADIUS

        # Update music
        self.sound.update_music_volume()
        self.sound.update_music_intensity(alive_count, self.initial_follower_count)

        # Recalculate alive count after eliminations
        alive_followers = [f for f in self.followers if f.alive]
        alive_count = len(alive_followers)

        # Check win condition
        if alive_count <= 1 and not self.game_over:
            self._handle_game_over(alive_followers)

    def render(self):
        """Render the current game state."""
        game_state = {
            'phase': self.phase,
            'arena': self.arena,
            'snakes': self.snakes,  # Pass all snakes
            'alive_count': sum(1 for f in self.followers if f.alive),
            'total_count': len(self.followers),
            'show_leaderboards': self.show_leaderboards,
            'current_game_leaderboard': self.current_game_leaderboard,
            'all_time_leaderboard': self.all_time_leaderboard,
            'winner': self.winner,
        }

        self.renderer.render_frame(self.followers, game_state)

        # Draw particles
        self.particles.render(self.screen)

        pygame.display.flip()

        # Capture frame for video
        if self.phase in ("countdown", "playing", "finished"):
            self.recorder.capture_frame(self.screen)

    def run(self):
        """Main game loop."""
        # Setup
        self.setup_players()

        # Start audio logging
        self.audio_logger.start()

        # Countdown phase - no intro, go straight to countdown like obstacle course
        print("\nStarting countdown...")
        self.phase = "countdown"
        self.countdown_start_time = time.time()

        # Start background music at low volume
        self.sound.start_background_music()
        self.sound.set_music_volume_low()

        # Play the Smash Ultimate countdown audio
        # The green screen overlay will be added during video export
        self.sound.play_smash_countdown_audio()
        self.countdown_duration = self.sound.countdown_audio_duration

        # Spawn snakes during countdown (but they can't eat yet)
        self.spawn_snakes()

        # Countdown phase - followers wander, snakes move but don't eat
        while time.time() - self.countdown_start_time < self.countdown_duration and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
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

            current_time = time.time()

            # Update snakes (moving but not eating)
            for snake in self.snakes:
                snake.update(dt, self.arena, self.followers)

            # OPTIMIZED: Only process alive followers during countdown too!
            alive_followers = [f for f in self.followers if f.alive]

            # Update followers with simple random movement
            # No individual AI - they just wander!
            fake_snake = type('FakeSnake', (), {'x': -1000, 'y': -1000})()
            for follower in alive_followers:
                follower.update(dt, self.arena, fake_snake, alive_followers)

            # Apply snake repulsion field (makes them appear to flee intelligently)
            if self.snakes and alive_followers:
                self._apply_snake_repulsion_field(dt, alive_followers)

            # Use PhysicsEngine for collision detection - only alive followers!
            if alive_followers:
                self.physics.update(alive_followers, dt)

            self.render()

        # Reset countdown start time
        self.countdown_start_time = None

        # Game starts - enable snake hunting and eating
        print("\nGO! Game started!")
        self.phase = "playing"
        self.sound.set_music_volume_high()

        # Enable snakes to hunt and eat
        for snake in self.snakes:
            snake.hunting = True
            snake.can_eat = True

        # Main game loop
        game_over_start_time = None

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            # Use lower FPS during video export for better performance
            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0

            # Cap delta time to prevent huge jumps when system lags
            dt = min(dt, config.MAX_DELTA_TIME)

            # Apply time scaling during video export to slow down simulation
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.update(dt)
            self.render()

            # Track game over display time
            if self.game_over and game_over_start_time is None:
                game_over_start_time = time.time()

            # Auto-close after 5 seconds of leaderboards
            if self.game_over and game_over_start_time:
                if time.time() - game_over_start_time > 5.0:
                    self.running = False

        self.cleanup()

    def _apply_snake_repulsion_field(self, dt: float, alive_followers: list):
        """
        Apply repulsion force from snakes to nearby followers.
        Makes followers appear to intelligently flee without individual AI.

        This is the MAGIC that makes random wandering look like intelligent behavior!
        Instead of each follower computing paths and making decisions, we just
        push them away from snakes with a simple force field.

        Performance: O(k*m) where k=alive followers, m=snakes

        Args:
            dt: Delta time (unused but kept for consistency)
            alive_followers: List of alive followers only (critical optimization!)
        """
        # Configuration
        repulsion_radius = 200  # Distance at which repulsion starts
        panic_radius = 80       # Inner radius with extra strong repulsion
        base_force = 3.5        # Base repulsion strength

        # For each snake, apply repulsion to nearby followers
        for snake in self.snakes:
            snake_x = snake.x
            snake_y = snake.y
            repulsion_radius_sq = repulsion_radius * repulsion_radius

            # OPTIMIZED: Only loop through ALIVE followers (not all 1M!)
            for follower in alive_followers:

                # Calculate squared distance first (cheaper than sqrt)
                dx = follower.x - snake_x
                dy = follower.y - snake_y
                dist_sq = dx * dx + dy * dy

                # Quick reject: skip if too far
                # For 500k players with 2 snakes, this rejects ~99.9% of followers!
                if dist_sq > repulsion_radius_sq:
                    continue

                # Only ~100-500 followers reach this point per snake
                # Calculate actual distance
                dist = math.sqrt(dist_sq)

                # Avoid division by zero
                if dist < 1.0:
                    # Directly on top of snake - push in random direction
                    angle = random.uniform(0, 2 * math.pi)
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                    dist = 1.0

                # Calculate repulsion strength (inversely proportional to distance)
                # Closer = stronger push
                strength = (repulsion_radius - dist) / repulsion_radius

                # Extra panic mode when very close to snake
                if dist < panic_radius:
                    strength *= 2.5  # Much stronger push in panic zone!

                # Normalize direction (away from snake)
                dx_norm = dx / dist
                dy_norm = dy / dist

                # Apply repulsion force to velocity
                repulsion_force = strength * base_force
                follower.vx += dx_norm * repulsion_force
                follower.vy += dy_norm * repulsion_force

    def _handle_game_over(self, survivors: List[SnakeEscapeFollower]):
        """Handle game over."""
        self.game_over = True
        self.phase = "finished"

        print("\n" + "=" * 60)
        print("  GAME OVER")
        print("=" * 60)

        if survivors:
            self.winner = survivors[0]
            self.winner.placement = 1
            print(f"Winner: {self.winner.username}")
            self.sound.play_winner_celebration()
        else:
            print("No survivors - Snake wins!")

        # Calculate and save scores
        self._calculate_and_save_scores()

    def _calculate_and_save_scores(self):
        """Calculate scores for all followers and update statistics."""
        print("\nCalculating scores...")

        # Sort followers by survival (alive first, then by survival time)
        sorted_followers = sorted(
            self.followers,
            key=lambda f: (not f.alive, -f.get_survival_time())
        )

        # Assign placements
        for i, follower in enumerate(sorted_followers):
            if follower.placement is None:
                follower.placement = i + 1

        total_participants = len(self.followers)
        game_results = []

        for follower in sorted_followers:
            games_played = self.statistics.get_games_played(follower.username)

            points_breakdown = self.scoring.calculate_total_points(
                placement=follower.placement,
                total_participants=total_participants,
                survival_time=follower.get_survival_time(),
                games_played=games_played
            )

            points = points_breakdown["total_points"]

            game_results.append((
                follower.username,
                follower.placement,
                points,
                follower.get_survival_time()
            ))

        # Game metadata
        game_type = "snake_escape"
        game_display_name = "Snake Escape"
        day_number = getattr(config, 'DAY_NUMBER', 1)

        game_history_results = []

        for follower in sorted_followers:
            games_played = self.statistics.get_games_played(follower.username)

            points_breakdown = self.scoring.calculate_total_points(
                placement=follower.placement,
                total_participants=total_participants,
                survival_time=follower.get_survival_time(),
                games_played=games_played
            )

            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=follower.username,
                placement=follower.placement,
                points_earned=points,
                survival_time=follower.get_survival_time(),
                total_participants=total_participants,
                game_type=game_type,
                game_id=""  # Will be set after game_history.record_game_session
            )

            # Store for game history
            game_history_results.append({
                "username": follower.username,
                "placement": follower.placement,
                "points": points,
                "survival_time": follower.get_survival_time(),
                "kills": 0,
                "damage": 0.0
            })

        # Record complete game session to history
        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results
        )

        # Save statistics
        self.statistics.save_statistics()
        print("Statistics saved!")

        # Auto-push to GitHub (if not in test mode)
        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        # Generate leaderboards
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []  # All-time leaderboard display removed

        # Show leaderboards
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()

        # Print top 10
        print("\nTop 10:")
        for i, result in enumerate(game_results[:10]):
            print(f"{i + 1}. {result[0]} - {result[2]:.1f} pts")

    def cleanup(self):
        """Clean up and export video."""
        self.audio_logger.stop()

        print("\n" + "=" * 60)
        print("  GAME STATISTICS")
        print("=" * 60)
        print(f"Total Survivors: {len(self.followers)}")
        print(f"Total Eliminations: {self.total_eliminations}")
        if self.snakes:
            total_kills = sum(s.kills for s in self.snakes)
            print(f"Snake Count: {len(self.snakes)}")
            print(f"Total Snake Kills: {total_kills}")
        print(f"Video Frames: {self.recorder.get_frame_count()}")
        print(f"Video Duration: {self.recorder.get_video_duration():.1f}s")
        print("=" * 60)

        # Export video
        if config.EXPORT_VIDEO:
            self.recorder.export_video()

        self.sound.cleanup()
        pygame.quit()

        print(f"\nThanks for playing {self.GAME_TITLE}!")
