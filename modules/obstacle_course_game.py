"""
Obstacle Course Game - Main Game Class
Orchestrates the obstacle course race mode
"""

import pygame
import time
import cv2
import numpy as np
from typing import List, Optional

import config
from .api import InstagramAPI
from .racer import Racer
from .course_generator import CourseGenerator
from .obstacle_course_camera import ObstacleCourseCamera
from .obstacle_course_renderer import ObstacleCourseRenderer
from .statistics import PlayerStatistics
from .scoring import ScoringSystem
from .sound_manager import SoundManager
from .audio_logger import AudioLogger


class ObstacleCourseGame:
    """
    Main game class for the Obstacle Course race mode
    Racers compete to reach the finish line first
    """

    def __init__(self):
        """Initialize the game"""
        print("=" * 60)
        print("  OBSTACLE COURSE RACE")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Obstacle Course Race")
        self.clock = pygame.time.Clock()

        # Initialize game components
        print("\nInitializing Obstacle Course...")
        self.api = InstagramAPI()
        self.camera = ObstacleCourseCamera()
        self.renderer = ObstacleCourseRenderer(self.screen)
        self.audio_logger = AudioLogger()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()

        # Preload audio
        self.sound.preload_audio()

        # Generate course
        self.course_generator = CourseGenerator(config.DAY_NUMBER)
        self.course = self.course_generator.generate_course()

        # Game state
        self.racers: List[Racer] = []
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Race state
        self.first_finisher = None
        self.grace_timer = None

        # Leaderboards for end-game display
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []
        self.show_leaderboards = False
        self.leaderboard_display_start = None

        # Countdown video
        self.countdown_video = None
        self.countdown_fps = 30
        self.countdown_duration = 0
        self.countdown_start_time = None
        self._load_countdown_video()

        print("Obstacle Course initialized!\n")

    def _load_countdown_video(self):
        """Load the Smash Ultimate countdown video"""
        video_path = "assets/smash ultimate 3 2 1 go green screen.mp4"

        try:
            self.countdown_video = cv2.VideoCapture(video_path)

            if not self.countdown_video.isOpened():
                print(f"Could not load countdown video: {video_path}")
                self.countdown_video = None
                return

            # Get video properties
            self.countdown_fps = self.countdown_video.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.countdown_video.get(cv2.CAP_PROP_FRAME_COUNT))
            self.countdown_duration = frame_count / self.countdown_fps

            print(f"Loaded countdown video: {self.countdown_duration:.1f}s @ {self.countdown_fps} FPS")

        except Exception as e:
            print(f"Error loading countdown video: {e}")
            self.countdown_video = None

    def _get_countdown_frame(self) -> Optional[pygame.Surface]:
        """
        Get current frame from countdown video based on elapsed time
        Applies chroma key to remove green screen

        Returns:
            Pygame surface of current frame with transparency, or None if video not available
        """
        if self.countdown_video is None or self.countdown_start_time is None:
            return None

        # Calculate elapsed time
        elapsed = time.time() - self.countdown_start_time

        if elapsed >= self.countdown_duration:
            return None  # Video finished

        # Calculate which frame to show
        frame_number = int(elapsed * self.countdown_fps)

        # Set video to correct frame
        self.countdown_video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        # Read frame
        ret, frame = self.countdown_video.read()

        if not ret:
            return None

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Apply chroma key (remove green screen)
        # Green screen typically has high green channel, low red and blue
        lower_green = np.array([0, 100, 0])    # Lower bound for green
        upper_green = np.array([100, 255, 100]) # Upper bound for green

        # Create mask where green pixels are white (255), others are black (0)
        mask = cv2.inRange(frame_rgb, lower_green, upper_green)

        # Invert mask so green pixels are 0 (transparent), non-green are 255 (opaque)
        alpha_channel = cv2.bitwise_not(mask)

        # Create RGBA image by adding alpha channel
        frame_rgba = np.dstack([frame_rgb, alpha_channel])

        # Transpose to match pygame format (width, height, channels)
        frame_rgba = np.transpose(frame_rgba, (1, 0, 2))

        # Create surface from RGBA array
        # Pygame needs RGBA in correct format
        surface = pygame.Surface((frame_rgba.shape[0], frame_rgba.shape[1]), pygame.SRCALPHA)

        # Use surfarray to set pixels
        pygame.surfarray.pixels_alpha(surface)[:] = frame_rgba[:, :, 3]  # Set alpha
        pygame.surfarray.pixels3d(surface)[:] = frame_rgba[:, :, :3]     # Set RGB

        return surface

    def setup_racers(self):
        """Fetch/generate followers and create racers"""
        print(f"Setting up {config.FOLLOWER_COUNT} racers...")

        # Fetch followers
        follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        # Place all racers at starting line within track boundaries
        start_x = self.course.start_line[0]
        start_y = self.course.start_line[1]

        # Track boundaries - racers must fit within track width
        track_half_width = config.OBSTACLE_COURSE_WIDTH / 2
        track_top = start_y - track_half_width + config.FOLLOWER_RADIUS
        track_bottom = start_y + track_half_width - config.FOLLOWER_RADIUS

        # Calculate available space
        available_height = track_bottom - track_top

        # Calculate grid dimensions to fit all racers within track bounds
        # Use smaller spacing to allow overlap (racers can overlap at start)
        spacing = config.FOLLOWER_RADIUS * 1.5  # Allow overlap

        # Calculate how many racers fit per column within track height
        racers_per_column = max(1, int(available_height / spacing))

        # Calculate how many columns we need
        num_columns = (len(follower_data) + racers_per_column - 1) // racers_per_column

        # Offset to ensure all racers start behind the starting line
        start_offset = config.FOLLOWER_RADIUS * 3  # Push back from start line

        for i, data in enumerate(follower_data):
            col = i // racers_per_column
            row = i % racers_per_column

            # Calculate position in grid (left of starting line, within track bounds)
            x = start_x - start_offset - (col * spacing)  # Behind start line

            # Distribute vertically within track bounds
            if racers_per_column > 1:
                y = track_top + (row / (racers_per_column - 1)) * available_height
            else:
                y = start_y

            racer = Racer(data, (x, y))
            self.racers.append(racer)

        print(f"{len(self.racers)} racers ready to race!\n")

    def update(self, dt: float):
        """Update game state"""
        if self.game_over:
            return

        current_time = time.time()

        # Update racers
        for racer in self.racers:
            racer.update_racer(dt, self.course, self.racers, current_time)

        # Update obstacles
        for obstacle in self.course.obstacles:
            obstacle.update(dt)

        # Check obstacle collisions
        for racer in self.racers:
            if not racer.alive or racer.finished:
                continue

            for obstacle in self.course.obstacles:
                if obstacle.check_collision((racer.x, racer.y), config.FOLLOWER_RADIUS):
                    obstacle.apply_collision_effect(racer)

        # Track first finisher
        for racer in self.racers:
            if racer.finished and self.first_finisher is None:
                self.first_finisher = racer
                self.grace_timer = config.FINISH_GRACE_PERIOD
                print(f"\n{racer.username} finished first!")
                print(f"{config.FINISH_GRACE_PERIOD} second grace period started...")

        # Count down grace period
        if self.grace_timer is not None:
            self.grace_timer -= dt

            if self.grace_timer <= 0:
                print("\nTime's up! Ranking remaining racers...")
                self._finish_race()

        # Find leader for camera
        leader = self._get_leader()
        if leader:
            self.camera.update((leader.x, leader.y), self.course.length, self.course.finish_line[0])

    def render(self):
        """Render current game state"""
        # Count racers
        alive_count = sum(1 for r in self.racers if r.alive and not r.finished)
        finished_count = sum(1 for r in self.racers if r.finished)

        # Get leader
        leader = self._get_leader()
        leader_name = leader.username if leader else None
        leader_progress = leader.progress if leader else 0.0

        # Get top 5 racers by progress
        alive_racers = [r for r in self.racers if r.alive and not r.finished]
        top_5 = sorted(alive_racers, key=lambda r: r.progress, reverse=True)[:5]
        top_5_data = [(r.username, r.progress) for r in top_5]

        # Get countdown frame if in countdown phase
        countdown_frame = self._get_countdown_frame()

        game_state = {
            "alive_count": alive_count,
            "finished_count": finished_count,
            "grace_timer": self.grace_timer,
            "leader_username": leader_name,
            "leader_progress": leader_progress,
            "top_5": top_5_data,
            "game_over": self.game_over,
            "countdown_frame": countdown_frame,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
        }

        self.renderer.render_frame(self.racers, self.course, self.camera, game_state)
        pygame.display.flip()

    def _get_leader(self) -> Racer:
        """Get the leading racer"""
        alive_racers = [r for r in self.racers if r.alive and not r.finished]
        if not alive_racers:
            return None

        # Leader is furthest along course
        return max(alive_racers, key=lambda r: r.progress)

    def _finish_race(self):
        """Finish the race and calculate rankings"""
        self.game_over = True

        # Calculate final rankings
        # Sort by: finished (yes/no), finish time, distance to finish
        sorted_racers = sorted(self.racers, key=lambda r: (
            not r.finished,
            r.finish_time if r.finish_time else 9999,
            self.course.get_distance_to_finish((r.x, r.y))
        ))

        # Assign placements
        for i, racer in enumerate(sorted_racers):
            racer.placement = i + 1

        # Print results
        print("\n" + "=" * 60)
        print("  RACE COMPLETE")
        print("=" * 60)

        print("\nTop 10 Finishers:")
        for i, racer in enumerate(sorted_racers[:10]):
            status = "FINISHED" if racer.finished else f"DNF ({racer.progress*100:.1f}%)"
            print(f"{i+1}. {racer.username} - {status}")

        # Calculate and save scores
        self._calculate_and_save_scores(sorted_racers)

    def _calculate_and_save_scores(self, sorted_racers: List[Racer]):
        """Calculate scores for all racers and update statistics"""
        print("\nCalculating scores...")

        total_participants = len(self.racers)
        game_results = []  # For current game leaderboard

        for racer in sorted_racers:
            placement = racer.placement
            games_played = self.statistics.get_games_played(racer.username)

            # Calculate points
            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=racer.get_survival_time(),
                games_played=games_played
            )

            points_earned = points_breakdown["total_points"]

            # Store for current game leaderboard
            game_results.append((racer.username, placement, points_earned, racer.get_survival_time()))

            # Update stats
            self.statistics.update_player_stats(
                username=racer.username,
                placement=placement,
                points_earned=points_earned,
                survival_time=racer.get_survival_time(),
                total_participants=total_participants
            )

        # Save
        self.statistics.save_statistics()
        print("Statistics saved!")

        # Generate leaderboards for display
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = self.statistics.get_all_time_leaderboard(top_n=10)

        # Enable leaderboard display
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()

    def run(self):
        """Main game loop"""
        # Setup
        self.setup_racers()

        # Countdown phase
        print("\nStarting countdown...")
        self.countdown_start_time = time.time()

        # Start background music at low volume
        self.sound.start_background_music()
        self.sound.set_music_volume_low()

        # Show countdown video while racers are at starting line
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
                print("\nGO! Race started!")
                # Increase music volume for race
                self.sound.set_music_volume_high()

            # Render (countdown frame will be shown in overlay)
            self.render()

        # Race has started - reset countdown start time
        self.countdown_start_time = None

        # Main race loop
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

    def cleanup(self):
        """Clean up"""
        print("\n" + "=" * 60)
        print("  RACE STATISTICS")
        print("=" * 60)
        print(f"Total Racers: {len(self.racers)}")
        if self.first_finisher:
            print(f"Winner: {self.first_finisher.username}")
        print("=" * 60)

        pygame.quit()
        print("\nThanks for racing!")
