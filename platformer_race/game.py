"""
Platformer Race Game - Main Game Class

2D side-scrolling platformer race where followers compete to reach the finish line.
"""

import pygame
import random
import time
from datetime import datetime

import config
from shared import (
    InstagramAPI,
    SoundManager,
    ScoringSystem,
    PlayerStatistics,
    VideoRecorder,
    AudioLogger
)
from .racer import PlatformerRacer
from .level import PlatformerLevel
from .camera import PlatformerCamera
from .physics import PlatformerPhysics
from .ai import JumpAI
from .renderer import PlatformerRenderer


class PlatformerRaceGame:
    """
    Platformer Race Game

    Phases:
    1. intro - Show title and racer count (3 sec)
    2. countdown - 3-2-1-GO countdown
    3. race - Main gameplay
    4. finished - Winner podium and leaderboards

    Features:
    - 1000+ racers with dynamic culling
    - Independent platformer physics with gravity and jumping
    - Intelligent pathfinding AI with mistakes
    - Spike hazards and precision platforming
    - 5-tier level design (bottom-left to top-right)
    - Camera follows first place
    """

    def __init__(self):
        """Initialize the game"""
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Platformer Race")
        self.clock = pygame.time.Clock()

        # Initialize shared systems
        self.api = InstagramAPI()
        self.audio_logger = AudioLogger()
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.5,
            offset_y=70
        )
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.scoring = ScoringSystem()

        # Use Sydney Tour music
        self.sound.background_music_path = "assets/sydney_tour_music.wav"
        self.sound.preload_audio()

        # Game components
        self.physics = PlatformerPhysics()
        self.ai = JumpAI()
        self.level = None  # Will be generated
        self.camera = None  # Will be created after level
        self.renderer = PlatformerRenderer(self.screen)

        # Game state
        self.racers = []
        self.visible_racers = []  # Dynamic culling
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()
        self.game_time = 0.0

        # Phase management
        self.phase = "intro"
        self.phase_start_time = 0.0
        self.recording_start_time = None

        # Race state
        self.first_finisher = None
        self.grace_period_start = None
        self.grace_period_duration = 5.0  # Seconds after first finisher
        self.top_10_finishers = []

        # Statistics
        self.day_number = 1
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

    def setup_racers(self):
        """Fetch followers and place at starting line"""
        # Fetch followers
        follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        # All racers start at exact same position (bottom-left of starting platform)
        # Starting platform is at x=10, y=600, width=140 (Floor 1)
        # Place all racers at left side of platform, just above surface
        start_x = 70  # Left side of starting platform
        start_y = 580  # Just above platform surface (platform is at y=600)

        for i, data in enumerate(follower_data):
            # All racers at same position - creates exciting mass start
            racer = PlatformerRacer(data, (start_x, start_y))
            self.racers.append(racer)

    def setup_level(self):
        """Generate the platformer level"""
        self.level = PlatformerLevel.generate_level()

        # Create camera with extended viewport (500x700)
        game_area_x = (config.SCREEN_WIDTH - 500) // 2
        game_area_y = 180
        self.camera = PlatformerCamera(game_area_x, game_area_y, game_area_width=500, game_area_height=700)

    def run(self):
        """Main game loop (matches interface of other games)"""
        self.start_game()

    def start_game(self):
        """Start the game loop"""
        self.setup_level()
        self.setup_racers()

        # Start with intro phase
        self.phase = "intro"
        self.phase_start_time = time.time()
        self.game_start_time = time.time()

        # Start background music
        self.sound.start_background_music()

        # Main game loop
        while self.running:
            self.handle_events()
            self.update()
            self.render()

        # Export video if enabled
        if config.EXPORT_VIDEO:
            self.export_video()

        # Cleanup
        pygame.quit()

    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        """Main update loop"""
        # Calculate delta time
        if config.EXPORT_VIDEO:
            dt = 1.0 / config.SIMULATION_FPS_DURING_EXPORT
            dt *= config.EXPORT_TIME_SCALE
        else:
            dt = self.clock.tick(config.FPS) / 1000.0
            dt = min(dt, 0.1)  # Cap dt to prevent huge jumps

        self.game_time = time.time() - self.game_start_time

        # Update based on phase
        if self.phase == "intro":
            self._update_intro_phase()
        elif self.phase == "countdown":
            self._update_countdown_phase()
        elif self.phase == "race":
            self._update_race_phase(dt)
        elif self.phase == "finished":
            self._update_finished_phase()

    def _update_intro_phase(self):
        """Intro phase - show title (3 seconds)"""
        elapsed = time.time() - self.phase_start_time
        if elapsed >= 3.0:
            # Transition to countdown
            self.phase = "countdown"
            self.phase_start_time = time.time()
            self.sound.play_countdown_audio()

    def _update_countdown_phase(self):
        """Countdown phase - play countdown video/audio"""
        elapsed = time.time() - self.phase_start_time
        countdown_duration = self.sound.countdown_audio_duration

        if config.EXPORT_VIDEO:
            countdown_duration *= config.EXPORT_TIME_SCALE

        if elapsed >= countdown_duration:
            # Start the race!
            self.phase = "race"
            self.phase_start_time = time.time()
            self.recording_start_time = time.time()
            self.sound.set_music_volume_high()

    def _update_race_phase(self, dt):
        """Race phase - main gameplay"""
        current_time = time.time()
        race_time = current_time - self.phase_start_time  # Time since race started

        # Update all racers (physics + AI)
        for racer in self.racers:
            racer.update_racer(dt, self.level, self.camera, self.physics, self.ai, race_time)

        # Update camera to follow first place
        self.camera.update(self.racers, self.level, self.first_finisher)

        # Get visible racers for rendering (dynamic culling)
        self.visible_racers = self._get_visible_racers()

        # Check for finishers and count them
        finished_count = sum(1 for racer in self.racers if racer.finished)

        # Track first finisher for camera
        for racer in self.racers:
            if racer.finished and self.first_finisher is None:
                self.first_finisher = racer

        # Update placements for new finishers
        if not hasattr(self, '_last_finished_count'):
            self._last_finished_count = 0

        if finished_count > self._last_finished_count:
            for racer in self.racers:
                if racer.finished and racer.placement == 0:
                    racer.placement = finished_count
            self._last_finished_count = finished_count

        # End race when 10 racers finish
        if finished_count >= 10:
            self._finish_race()

    def _update_finished_phase(self):
        """Finished phase - show winner (5.27 seconds) then leaderboards (6 seconds)"""
        elapsed = time.time() - self.phase_start_time

        # Sub-phase 1: Show top 10 finishers (0-5.27 seconds)
        if elapsed < 5.27:
            if not hasattr(self, '_leaderboards_prepared'):
                self._leaderboards_prepared = False

        # Sub-phase 2: Show leaderboards (5.27-11.27 seconds)
        elif elapsed < 11.27:
            # Prepare leaderboards once when entering this sub-phase
            if not self._leaderboards_prepared:
                self._prepare_leaderboards()
                self._leaderboards_prepared = True

        # End game after both phases
        else:
            self.running = False

    def _get_visible_racers(self):
        """Get racers visible on camera (with buffer) for rendering"""
        if not self.camera:
            return self.racers

        # For vertical climbing, all racers in the game area are visible
        # (static camera shows entire 500x500 area)
        visible_bounds = self.camera.get_visible_bounds()

        visible = [
            r for r in self.racers
            if (0 <= r.y <= self.level.height)  # In vertical game area
        ]
        return visible

    def _get_top_5_racers(self):
        """Get top 5 racers by progress"""
        # Finished racers sorted by finish time
        finishers = [r for r in self.racers if r.finished]
        finishers.sort(key=lambda r: r.finish_time)

        # Racing racers sorted by progress
        racing = [r for r in self.racers if not r.finished and r.alive]
        racing.sort(key=lambda r: r.progress, reverse=True)

        # Combine and take top 5
        top_5 = (finishers + racing)[:5]
        return [(r.username, r.progress) for r in top_5]

    def _finish_race(self):
        """Called when race finishes"""
        # Get all finishers sorted by finish time
        finishers = [r for r in self.racers if r.finished]
        finishers.sort(key=lambda r: r.finish_time)

        # Assign placements and points for finishers
        for i, racer in enumerate(finishers):
            racer.placement = i + 1
            # Top 10 get 100, 99, 98... down to 91 points
            if i < 10:
                racer.points = 100 - i
            else:
                # Other finishers get checkpoint-based points (they reached all checkpoints)
                racer.points = 80  # All 4 checkpoints

        # Assign points for non-finishers based on checkpoints reached
        non_finishers = [r for r in self.racers if not r.finished]
        for racer in non_finishers:
            # 20 points per checkpoint reached
            racer.points = racer.checkpoint_index * 20
            racer.placement = 0  # DNF

        # Get top 10
        self.top_10_finishers = finishers[:10]

        # Transition to finished phase
        self.phase = "finished"
        self.phase_start_time = time.time()

    def _prepare_leaderboards(self):
        """Prepare leaderboard data after race finishes"""
        # Update statistics for each racer
        total_participants = len(self.racers)
        for racer in self.racers:
            placement = racer.placement if racer.placement > 0 else total_participants
            self.statistics.update_player_stats(
                username=racer.username,
                placement=placement,
                points_earned=racer.points,
                survival_time=racer.finish_time if racer.finished else 0.0,
                total_participants=total_participants
            )

        # Build game results for leaderboard display
        game_results = []
        for racer in self.racers:
            placement = racer.placement if racer.placement > 0 else total_participants
            game_results.append((
                racer.username,
                placement,
                racer.points,
                racer.finish_time if racer.finished else 0.0
            ))

        # Get leaderboards
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = self.statistics.get_all_time_leaderboard(top_n=10)

    def render(self):
        """Render the current frame"""
        # Build game state dict
        finished_count = sum(1 for racer in self.racers if racer.finished)

        # Determine finished sub-phase
        finished_sub_phase = "top_10"  # Default
        if self.phase == "finished":
            elapsed = time.time() - self.phase_start_time
            if elapsed >= 5.27:
                finished_sub_phase = "leaderboards"

        game_state = {
            'day': self.day_number,
            'racer_count': len(self.racers),
            'phase': self.phase,
            'finished_sub_phase': finished_sub_phase,
            'top_5': self._get_top_5_racers() if self.phase == "race" else [],
            'winner': self.first_finisher if self.phase == "finished" else None,
            'top_10': self.top_10_finishers if self.phase == "finished" else [],
            'finished_count': finished_count,
            'current_game_leaderboard': self.current_game_leaderboard,
            'all_time_leaderboard': self.all_time_leaderboard
        }

        # Render frame
        self.renderer.render_frame(
            self.level,
            self.visible_racers,
            self.camera,
            game_state
        )

        # Capture frame for video if exporting
        if config.EXPORT_VIDEO and self.phase in ["countdown", "race", "finished"]:
            self.recorder.capture_frame(self.screen, self.game_time)

        # Update display
        pygame.display.flip()

    def export_video(self):
        """Export recorded video"""
        if config.EXPORT_VIDEO:
            self.recorder.export_video()


# Main entry point
if __name__ == "__main__":
    game = PlatformerRaceGame()
    game.start_game()

    # Export video if enabled
    if config.EXPORT_VIDEO:
        game.export_video()
