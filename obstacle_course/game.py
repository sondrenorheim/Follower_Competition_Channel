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
from shared import (
    InstagramAPI,
    PlayerStatistics,
    GameHistory,
    ScoringSystem,
    SoundManager,
    AudioLogger,
    VideoRecorder,
    auto_push
)
from .racer import Racer
from .generator import CourseGenerator
from .camera import ObstacleCourseCamera
from .renderer import ObstacleCourseRenderer


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
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        # Set green screen overlay to be applied during video export
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.5,
            offset_y=70
        )
        self.statistics = PlayerStatistics()
        self.game_history = GameHistory()
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

        # Top 5 race leaderboard (locks once 5 have finished)
        self.top_5_finishers = []
        self.top_5_locked = False

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

        # Convert BGR to HSV for better chroma keying
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Apply chroma key using HSV color space (more accurate for green screen)
        # Green hue is around 35-85 in OpenCV's 0-180 range
        lower_green = np.array([35, 80, 80])   # Hue, Saturation, Value
        upper_green = np.array([85, 255, 255])

        # Create mask where green pixels are white (255), others are black (0)
        mask = cv2.inRange(frame_hsv, lower_green, upper_green)

        # Erode the mask to trim green fringe from edges
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)  # Expand green area to catch edges

        # Invert mask so green pixels are 0 (transparent), non-green are 255 (opaque)
        alpha_channel = cv2.bitwise_not(mask)

        # Feather the edges slightly for smoother blending
        alpha_channel = cv2.GaussianBlur(alpha_channel, (3, 3), 0)

        # Apply green spill suppression on edge pixels
        # Reduce green channel where there's partial transparency
        edge_mask = (alpha_channel > 0) & (alpha_channel < 255)
        frame_rgb[edge_mask, 1] = np.minimum(
            frame_rgb[edge_mask, 1],
            np.maximum(frame_rgb[edge_mask, 0], frame_rgb[edge_mask, 2])
        )

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

        # Randomize order so followers aren't always in the same starting positions
        import random
        random.shuffle(follower_data)

        # Place racers at starting line - spread out vertically for visibility
        start_x = self.course.start_line[0]
        start_y = self.course.start_line[1]

        # Track boundaries - racers must fit within track width
        track_half_width = config.OBSTACLE_COURSE_WIDTH / 2
        track_top = start_y - track_half_width + config.FOLLOWER_RADIUS
        track_bottom = start_y + track_half_width - config.FOLLOWER_RADIUS

        # Calculate available space
        available_height = track_bottom - track_top

        # All racers spread out vertically (same as intro animation layout)
        num_racers = len(follower_data)

        # Small horizontal offset to ensure all racers start behind the starting line
        start_offset = config.FOLLOWER_RADIUS * 2  # Push back from start line

        # Use the same layout as intro animation - 30 players per vertical line
        max_racers_per_vertical_line = 30

        for i, data in enumerate(follower_data):
            # Determine position in spread-out layout (same as intro)
            position_in_line = i % max_racers_per_vertical_line

            # All racers at the same X position (single vertical column at start line)
            x = start_x - start_offset

            # Distribute vertically within track bounds (30 per column)
            if max_racers_per_vertical_line > 1:
                vertical_spacing = available_height / (max_racers_per_vertical_line - 1)
                y = track_top + (position_in_line * vertical_spacing)
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
                print("\nTime's up! Ranking remaining racers by distance from finish...")
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

        # Get leader (stop tracking progress once first finisher crosses)
        leader = self._get_leader()
        leader_name = leader.username if leader else None
        # If someone has finished, show 100% and stop updating
        if self.first_finisher is not None:
            leader_progress = 1.0
        else:
            leader_progress = leader.progress if leader else 0.0

        # Get top 5 racers - prioritize finishers, then by progress
        if not self.top_5_locked:
            # Get finishers sorted by finish time
            finishers = [r for r in self.racers if r.finished]
            finishers_sorted = sorted(finishers, key=lambda r: r.finish_time if r.finish_time else 9999)

            # Get remaining racers by progress
            alive_racers = [r for r in self.racers if r.alive and not r.finished]
            alive_sorted = sorted(alive_racers, key=lambda r: r.progress, reverse=True)

            # Combine: finishers first, then alive racers
            combined = finishers_sorted + alive_sorted
            top_5 = combined[:5]
            top_5_data = [(r.username, r.progress) for r in top_5]

            # Lock the top 5 once we have 5 finishers or game is over
            if len(finishers_sorted) >= 5 or self.game_over:
                self.top_5_finishers = top_5_data
                self.top_5_locked = True
        else:
            top_5_data = self.top_5_finishers

        game_state = {
            "alive_count": alive_count,
            "finished_count": finished_count,
            "grace_timer": self.grace_timer,
            "leader_username": leader_name,
            "leader_progress": leader_progress,
            "top_5": top_5_data,
            "game_over": self.game_over,
            "countdown_frame": None,  # Green screen overlay added during video export
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.first_finisher,
        }

        self.renderer.render_frame(self.racers, self.course, self.camera, game_state)
        pygame.display.flip()

        # Capture frame for video export
        self.recorder.capture_frame(self.screen)

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

        # Game metadata
        game_type = "obstacle_course"
        game_display_name = "Obstacle Course"
        day_number = getattr(config, 'DAY_NUMBER', 1)

        game_history_results = []

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
                total_participants=total_participants,
                game_type=game_type,
                game_id=""  # Will be set after game_history.record_game_session
            )

            # Store for game history
            game_history_results.append({
                "username": racer.username,
                "placement": placement,
                "points": points_earned,
                "survival_time": racer.get_survival_time(),
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

        # Save
        self.statistics.save_statistics()
        print("Statistics saved!")

        # Auto-push to GitHub (if not in test mode)
        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        # Generate leaderboards for display
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []  # All-time leaderboard display removed

        # Enable leaderboard display
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()

    def run(self):
        """Main game loop"""
        # Setup
        self.setup_racers()

        # Start background music at low volume
        self.sound.start_background_music()
        self.sound.set_music_volume_low()

        # INTRO PHASE - Racers slide in from left in vertical lines
        print("\nIntro animation: Racers entering...")
        intro_duration = 8.0  # 8 seconds for intro animation (extended for more vertical lines)
        intro_start_time = time.time()

        # Get track boundaries to keep intro rows within finish line area
        start_y = self.course.start_line[1]
        track_half_width = config.OBSTACLE_COURSE_WIDTH / 2
        track_top = start_y - track_half_width + config.FOLLOWER_RADIUS
        track_bottom = start_y + track_half_width - config.FOLLOWER_RADIUS
        available_height = track_bottom - track_top

        # Store original positions and arrange racers in vertical lines
        original_positions = []

        # Max 30 players per vertical line
        max_racers_per_vertical_line = 30

        # Calculate how many vertical lines we need
        num_vertical_lines = (len(self.racers) + max_racers_per_vertical_line - 1) // max_racers_per_vertical_line

        # Horizontal spacing between vertical lines
        horizontal_line_spacing = 30  # pixels between each vertical line

        for i, racer in enumerate(self.racers):
            original_positions.append((racer.x, racer.y))

            # Determine which vertical line this racer is in
            vertical_line_index = i // max_racers_per_vertical_line
            position_in_line = i % max_racers_per_vertical_line

            # Calculate vertical position within the line (spread within track bounds)
            if max_racers_per_vertical_line > 1:
                # Distribute the 10 (or fewer) racers evenly within track height
                vertical_spacing = available_height / (max_racers_per_vertical_line - 1)
                intro_y = track_top + (position_in_line * vertical_spacing)
            else:
                intro_y = start_y

            # Calculate horizontal starting position (off-screen, each vertical line staggered)
            # Each vertical line starts further back from the previous one
            intro_x = -300 - (vertical_line_index * horizontal_line_spacing)

            # Set racer to intro position
            racer.x = intro_x
            racer.y = intro_y  # Y stays constant during intro - no vertical movement

        # Intro animation loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        return

            dt = self.clock.tick(config.FPS) / 1000.0

            # Calculate intro animation progress (0.0 to 1.0)
            elapsed = time.time() - intro_start_time
            progress = min(1.0, elapsed / intro_duration)

            # Use easing function for smooth animation (ease-out)
            eased_progress = 1.0 - (1.0 - progress) ** 3  # Cubic ease-out

            # Animate each racer sliding in horizontally (NO vertical movement during intro)
            # All racers move at the SAME SPEED, so lines arrive sequentially
            constant_speed = 150  # pixels per second (slower for better viewing)
            distance_traveled = constant_speed * elapsed  # All racers travel the same distance

            all_racers_in_position = True  # Track if all racers have arrived

            for i, racer in enumerate(self.racers):
                vertical_line_index = i // max_racers_per_vertical_line
                position_in_line = i % max_racers_per_vertical_line

                # Intro Y position (within track bounds) - stays constant
                if max_racers_per_vertical_line > 1:
                    vertical_spacing = available_height / (max_racers_per_vertical_line - 1)
                    intro_y = track_top + (position_in_line * vertical_spacing)
                else:
                    intro_y = start_y

                # Intro X position (off-screen left, each vertical line staggered)
                intro_x = -300 - (vertical_line_index * horizontal_line_spacing)

                # Target X position (from original_positions)
                target_x = original_positions[i][0]

                # All racers move at SAME SPEED from their starting position
                # This means lines arrive sequentially (first line arrives first, etc.)
                current_x = intro_x + distance_traveled

                # Clamp to target position (don't overshoot)
                racer.x = min(current_x, target_x)
                racer.y = intro_y  # Y stays constant - NO VERTICAL MOVEMENT

                # Check if this racer has reached their position
                if racer.x < target_x:
                    all_racers_in_position = False

            self.render()

            # End intro when ALL racers have reached their starting positions
            if all_racers_in_position:
                print("All racers have lined up!")
                break

        # After intro completes, move racers to their actual starting positions
        for i, racer in enumerate(self.racers):
            racer.x, racer.y = original_positions[i]

        if not self.running:
            return

        # COUNTDOWN PHASE - Start countdown AFTER lineup is complete
        print("\nAll racers ready! Starting countdown...")
        self.countdown_start_time = time.time()

        # Mark this frame as the countdown start for video overlay
        self.recorder.mark_countdown_start()

        # Play the Smash Ultimate countdown audio
        self.sound.play_smash_countdown_audio()

        # Countdown phase - racers wait at starting line
        # The green screen overlay will be added during video export
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

            # Render (no green screen overlay in simulation)
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
        print(f"Video Frames Captured: {self.recorder.get_frame_count()}")
        print(f"Video Duration: {self.recorder.get_video_duration():.1f}s")
        print("=" * 60)

        # Export video if enabled
        if config.EXPORT_VIDEO:
            self.recorder.export_video()

        pygame.quit()
        print("\nThanks for racing!")
