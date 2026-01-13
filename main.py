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
import socket
import subprocess
import shutil
import urllib.request
import json
from pathlib import Path
from typing import List
import shared.api as shared_api

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

# Import shared modules
from shared import (
    InstagramAPI,
    PhysicsEngine,
    VideoRecorder,
    ParticleSystem,
    SoundManager,
    ScoringSystem,
    PlayerStatistics,
    GameHistory,
    AudioLogger,
    PerformanceMonitor,
    auto_push
)

# Import battle royale specific modules
from battle_royale import Follower, Arena, Renderer

_DEFAULT_FOLLOWER_IMPORT_FILE = getattr(config, "FOLLOWER_IMPORT_FILE", "")
_LOG_HANDLES = []


def _get_follower_import_file(game_mode: str) -> str:
    overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
    if isinstance(overrides, dict):
        override = overrides.get(game_mode)
        if override:
            return override
    return _DEFAULT_FOLLOWER_IMPORT_FILE


def _http_get_json(url: str, timeout: float = 0.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            data = response.read()
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def _is_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _start_process_in_new_console(
    command: list[str],
    cwd: str,
    hidden: bool = False,
    log_path: Path | None = None,
    env: dict | None = None,
):
    try:
        stdout_target = None
        stderr_target = None
        if hidden and log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8")
            _LOG_HANDLES.append(log_file)
            stdout_target = log_file
            stderr_target = log_file

        if os.name == "nt":
            if hidden:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            else:
                flags = subprocess.CREATE_NEW_CONSOLE
            subprocess.Popen(
                command,
                cwd=cwd,
                creationflags=flags,
                stdout=stdout_target,
                stderr=stderr_target,
                env=env,
            )
        else:
            subprocess.Popen(
                command,
                cwd=cwd,
                start_new_session=True,
                stdout=stdout_target,
                stderr=stderr_target,
                env=env,
            )
        return True
    except Exception as exc:
        print(f"Warning: Failed to start process {command}: {exc}")
        return False


def _ensure_webhook_services():
    if not getattr(config, "AUTO_START_WEBHOOK_SERVICES", False):
        return

    base_dir = Path(__file__).resolve().parent
    log_dir = Path(getattr(config, "WEBHOOK_SERVICE_LOG_DIR", "logs/webhook_services"))
    hidden = bool(getattr(config, "WEBHOOK_SERVICE_HEADLESS", False))

    webhook_port = int(getattr(config, "WEBHOOK_SERVER_PORT", 5000))
    webhook_ok = False
    if _is_port_open("127.0.0.1", webhook_port):
        status = _http_get_json(f"http://127.0.0.1:{webhook_port}/")
        webhook_ok = isinstance(status, dict)

    if not webhook_ok:
        script_name = getattr(config, "WEBHOOK_SERVER_SCRIPT", "instagram_webhook.py")
        script_path = base_dir / script_name
        if script_path.exists():
            print("Webhook server not running. Starting instagram_webhook.py...")
            webhook_env = None
            if hidden:
                webhook_env = dict(os.environ)
                webhook_env["WEBHOOK_DEBUG"] = "0"
                webhook_env["WEBHOOK_USE_RELOADER"] = "0"
                webhook_env["PYTHONUNBUFFERED"] = "1"
            _start_process_in_new_console(
                [sys.executable, str(script_path)],
                str(base_dir),
                hidden=hidden,
                log_path=log_dir / "instagram_webhook.log",
                env=webhook_env,
            )
        else:
            print(f"Warning: Webhook script not found at {script_path}")

    ngrok_port = int(getattr(config, "NGROK_API_PORT", 4040))
    ngrok_ok = False
    if _is_port_open("127.0.0.1", ngrok_port):
        tunnels = _http_get_json(f"http://127.0.0.1:{ngrok_port}/api/tunnels")
        if isinstance(tunnels, dict) and tunnels.get("tunnels"):
            ngrok_ok = True

    if not ngrok_ok:
        ngrok_path = getattr(config, "NGROK_PATH", "ngrok")
        ngrok_bin = shutil.which(ngrok_path) or ngrok_path
        ngrok_http_port = str(getattr(config, "NGROK_HTTP_PORT", 5000))
        ngrok_log_mode = str(getattr(config, "NGROK_LOG_MODE", "")).strip()
        print("ngrok not running. Starting ngrok tunnel...")
        ngrok_command = [ngrok_bin, "http", ngrok_http_port]
        if ngrok_log_mode:
            ngrok_command.append(f"--log={ngrok_log_mode}")
        _start_process_in_new_console(
            ngrok_command,
            str(base_dir),
            hidden=hidden,
            log_path=log_dir / "ngrok.log",
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

        # Use HIDDEN flag if headless mode is enabled (no window, faster processing)
        display_flags = pygame.HIDDEN if config.HEADLESS_MODE else 0
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), display_flags)

        if not config.HEADLESS_MODE:
            pygame.display.set_caption("Follower Battle Royale")

        self.clock = pygame.time.Clock()

        # Initialize game components
        print("\n🎮 Initializing game components...")
        self.api = InstagramAPI()
        self.arena = Arena()
        self.physics = PhysicsEngine()
        self.renderer = Renderer(self.screen)
        self.audio_logger = AudioLogger()
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.0,  # 100% size
            offset_y=0  # Centered vertically
        )
        self.particles = ParticleSystem()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.game_history = GameHistory()
        self.scoring = ScoringSystem()

        # Preload audio files before game starts (prevents delays during gameplay)
        self.sound.preload_audio()

        # Game state
        self.followers: List[Follower] = []
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()
        self.game_time = 0.0  # Track game time (for consistent video recording)
        self.recording_start_time = 0.0  # When recording started

        # Game phases: "intro", "countdown", "playing", "finished"
        self.game_phase = "intro"
        self.phase_start_time = 0
        self.phase_start_game_time = 0.0  # Track phase start in game time (for countdown)
        self.countdown_number = 3

        # Statistics
        self.total_eliminations = 0
        self.last_alive_count = 0

        # Dynamic scaling tracking
        self.initial_total_players = 0
        self.initial_zone_radius = 0
        self.fixed_follower_radius = getattr(config, "BATTLE_ROYALE_FIXED_RADIUS", None)
        if self.fixed_follower_radius is not None and self.fixed_follower_radius > 0:
            self.radius_scale = 1.0
        else:
            self.fixed_follower_radius = None
            self.radius_scale = 1.5
        self.last_follower_radius = config.FOLLOWER_RADIUS

        # Announcements tracking
        self.top_10_announced = False
        self.top_5_announced = False

        # Leaderboard data for display
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

        # Performance optimization - update throttling for large player counts
        self.update_frame_counter = 0
        self.update_batches_per_frame = config.UPDATE_BATCHES_PER_FRAME

        # Performance monitoring - track FPS, timing, etc.
        log_interval = getattr(config, 'PERFORMANCE_LOG_INTERVAL', 2.0)  # Log every 2 seconds
        enable_detailed = getattr(config, 'PERFORMANCE_DETAILED_LOGGING', True)
        self.perf_monitor = PerformanceMonitor(log_interval=log_interval, enable_detailed_logging=enable_detailed)

        print("✅ Game initialized successfully!\n")

    def _apply_battle_royale_radius_scale(self, base_radius: float) -> float:
        if self.fixed_follower_radius is not None:
            return base_radius
        return base_radius * self.radius_scale

    def _calculate_battle_royale_radius(self, alive_count: int) -> float:
        if self.fixed_follower_radius is not None:
            return float(self.fixed_follower_radius)
        if not config.USE_DYNAMIC_SCALING:
            return config.FOLLOWER_BASE_RADIUS

        total_players = self.initial_total_players or max(1, len(self.followers))

        if total_players <= 100:
            start_radius = config.FOLLOWER_BASE_RADIUS
        else:
            scale_factor = math.pow(100.0 / total_players, 0.6)
            start_radius = max(config.FOLLOWER_MIN_RADIUS, config.FOLLOWER_BASE_RADIUS * scale_factor)

        elimination_progress = 1.0 - (alive_count / total_players)
        growth_amount = elimination_progress * config.SCALING_GROWTH_RATE
        radius_range = config.FOLLOWER_MAX_RADIUS - start_radius
        current_radius = start_radius + (radius_range * growth_amount)

        return max(config.FOLLOWER_MIN_RADIUS, min(config.FOLLOWER_MAX_RADIUS, current_radius))

    def setup_followers(self):
        """
        Fetch/generate followers and place them in the arena
        """
        print(f"👥 Setting up followers...")

        # Fetch followers (support test mode)
        if config.TEST_MINIMAL_PLAYERS:
            print(f"🧪 TEST MODE: Using {config.TEST_MINIMAL_PLAYER_COUNT} test players")
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        print(f"👥 Setting up {len(follower_data)} followers...")

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
        base_radius = self._calculate_battle_royale_radius(self.initial_total_players)
        scaled_radius = self._apply_battle_royale_radius_scale(base_radius)
        config.FOLLOWER_RADIUS = scaled_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
        self.last_follower_radius = scaled_radius

        # Invalidate all follower surfaces so they render at correct size
        for follower in self.followers:
            follower.surface_needs_update = True

        if self.fixed_follower_radius is not None:
            print(f"Fixed follower radius: {scaled_radius:.1f}px")
        elif config.USE_DYNAMIC_SCALING:
            print(f"Dynamic scaling enabled: follower radius = {scaled_radius:.1f}px")
        print(f"✅ {len(self.followers)} followers spawned in arena\n")

    def update(self, dt: float):
        """
        Update game state

        Args:
            dt: Delta time in seconds
        """
        # Start performance tracking for this frame
        self.perf_monitor.start_frame()
        self.perf_monitor.start_section("update")

        if self.game_over:
            self.perf_monitor.end_section("update")
            self.perf_monitor.end_frame()
            return

        # Handle countdown phase
        if self.game_phase == "countdown":
            elapsed = self.game_time - self.phase_start_game_time
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
        # Performance optimization: Use batched updates for large player counts
        total_followers = len(self.followers)

        # Use batched updates if enabled and player count exceeds threshold
        if config.ENABLE_UPDATE_THROTTLING and total_followers > 5000:
            # Increment frame counter
            self.update_frame_counter += 1

            # Calculate which batch to update this frame
            batch_index = self.update_frame_counter % self.update_batches_per_frame
            batch_size = (total_followers + self.update_batches_per_frame - 1) // self.update_batches_per_frame

            # Calculate start and end indices for this batch
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, total_followers)

            followers_to_update = self.followers[start_idx:end_idx]
        else:
            # For smaller player counts or if throttling disabled, update all followers every frame
            followers_to_update = self.followers

        # Update the selected batch of followers
        for follower in followers_to_update:
            follower.update(
                dt,
                self.arena.center,
                self.arena.current_radius,
                self.followers,
                allow_targeting=self.game_phase == "playing",
            )

            # Only check safe zone during PLAYING phase (not during intro/countdown)
            if self.game_phase == "playing":
                was_alive = follower.alive
                follower.check_safe_zone(self.arena.center, self.arena.current_radius, self.particles)

                # If follower was just eliminated, add to kill feed and play sound
                if was_alive and not follower.alive:
                    self.renderer.add_elimination(follower.username)
                    self.sound.play_elimination()

        # Record how many players were updated
        self.perf_monitor.record_players_updated(len(followers_to_update))

        # End update section, start physics section
        self.perf_monitor.end_section("update")
        self.perf_monitor.start_section("physics")

        # Update physics (collisions) - works in all phases
        self.physics.update(self.followers, dt)

        # Skip expensive overlap resolution at high player counts (normal collision detection handles it)
        total_followers = len(self.followers)
        if total_followers < 10000:
            # Overlap resolution disabled for performance - normal collision detection handles it
            # self.physics.resolve_overlaps(self.followers)

            # Apply very gentle separation force to prevent stacking without interfering with combat
            self.physics.apply_separation_force(self.followers, strength=0.2)

        # Record collision checks from physics
        physics_stats = self.physics.get_stats()
        self.perf_monitor.record_collision_checks(physics_stats.get("collision_checks", 0))

        # End physics section
        self.perf_monitor.end_section("physics")

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
            if config.USE_DYNAMIC_SCALING and self.fixed_follower_radius is None:
                new_radius = self._calculate_battle_royale_radius(alive_count)
                scaled_radius = self._apply_battle_royale_radius_scale(new_radius)

                # If radius changed significantly, invalidate cached surfaces
                if abs(scaled_radius - self.last_follower_radius) > 0.5:
                    for follower in self.followers:
                        follower.surface_needs_update = True
                    self.last_follower_radius = scaled_radius

                config.FOLLOWER_RADIUS = scaled_radius
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
        # Start render timing
        self.perf_monitor.start_section("render")

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
        render_stats = self.renderer.render_frame(self.followers, self.arena, game_state, self.particles)

        # Record rendering stats if available
        if render_stats:
            self.perf_monitor.record_players_rendered(
                render_stats.get("rendered", 0),
                render_stats.get("culled", 0)
            )

        # Record frame for video (only from countdown onwards, skip intro)
        if self.game_phase in ("countdown", "playing", "finished"):
            recording_time = self.game_time - self.recording_start_time
            self.recorder.capture_frame(self.screen, current_time=recording_time)

        # Update display
        pygame.display.flip()

        # End render timing and complete frame
        self.perf_monitor.end_section("render")
        self.perf_monitor.end_frame()

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
        game_history_results = []

        # Game metadata
        game_type = "battle_royale"
        game_display_name = "Battle Royale"
        day_number = getattr(config, 'DAY_NUMBER', 1)

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
                kills=follower.kills,
                game_type=game_type,
                game_id=""  # Will be set after game_history.record_game_session
            )

            # Store for leaderboard
            game_results.append((
                follower.username,
                placement,
                points_earned,
                survival_time
            ))

            # Store for game history
            game_history_results.append({
                "username": follower.username,
                "placement": placement,
                "points": points_earned,
                "survival_time": survival_time,
                "kills": follower.kills,
                "damage": 0.0  # Not tracked in Battle Royale
            })

        # Record complete game session to history
        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results
        )

        # Save statistics to file
        self.statistics.save_statistics()

        # Auto-push to GitHub (if not in test mode)
        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        # Store leaderboards for display
        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []  # All-time leaderboard display removed

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

            # Use lower FPS during video export for better performance
            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0

            # Cap delta time to prevent huge jumps when system lags
            dt = min(dt, config.MAX_DELTA_TIME)

            # Apply time scaling during video export to slow down simulation
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt  # Track game time

            # Update followers so they move around during intro
            for follower in self.followers:
                follower.update(
                    dt,
                    self.arena.center,
                    self.arena.current_radius,
                    self.followers,
                    allow_targeting=self.game_phase == "playing",
                )

            # Update physics (collisions) so followers interact naturally
            self.physics.update(self.followers, dt)
            # Skip expensive overlap resolution at high player counts
            if len(self.followers) < 10000:
                # self.physics.resolve_overlaps(self.followers)
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
        self.phase_start_game_time = self.game_time  # Track phase start in game time
        self.recording_start_time = self.game_time  # Mark when recording starts
        self.countdown_number = 3
        self.renderer.start_countdown_video()  # Start the video overlay (for non-export display)
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
            # Use lower FPS during video export for better performance
            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0  # Convert to seconds

            # Cap delta time to prevent huge jumps when system lags
            dt = min(dt, config.MAX_DELTA_TIME)

            # Apply time scaling during video export to slow down simulation
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            self.game_time += dt  # Track game time

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


def _create_game_instance(game_mode: str):
    """Instantiate the correct game class for the given mode."""
    if game_mode == "fighter_arena":
        from fighter_arena import FighterBattleArena
        print("Starting Fighter Arena mode...")
        return FighterBattleArena()
    elif game_mode == "anime_fighting":
        from anime_fighting import AnimeFightingGame
        print("Starting Anime Fighting mode...")
        return AnimeFightingGame()
    elif game_mode == "gorillas_vs_followers":
        from gorillas_vs_followers import GorillasVsFollowersGame
        print("Starting Gorillas vs Followers mode...")
        return GorillasVsFollowersGame()
    elif game_mode == "obstacle_course":
        from obstacle_course import ObstacleCourseGame
        print("Starting Obstacle Course mode...")
        return ObstacleCourseGame()
    elif game_mode == "snake_escape":
        from snake_escape import SnakeEscapeGame
        print("Starting Snake Escape mode...")
        return SnakeEscapeGame()
    elif game_mode == "team_battle":
        from team_battle import TeamBattleGame
        print("Starting Team Battle mode...")
        return TeamBattleGame()
    elif game_mode == "platformer_race":
        from platformer_race import PlatformerRaceGame
        print("Starting Platformer Race mode...")
        return PlatformerRaceGame()
    elif game_mode == "spleef":
        from spleef import SpleefGame
        print("Starting Spleef mode...")
        return SpleefGame()
    elif game_mode == "meteor_mayhem":
        from meteor_mayhem import MeteorMayhemGame
        print("Starting Meteor Mayhem mode...")
        return MeteorMayhemGame()
    elif game_mode == "mingle":
        from mingle import MingleGame
        print("Starting Mingle mode...")
        return MingleGame()
    elif game_mode in ("heads_or_tails", "side_choice"):
        from side_choice import SideChoiceGame
        print("Starting Heads/Tails mode...")
        return SideChoiceGame()
    elif game_mode == "wheel_spinner":
        from wheel_spinner import WheelSpinnerGame
        print("Starting Wheel Spinner mode...")
        return WheelSpinnerGame()

    print("Starting Battle Royale mode...")
    return FollowerBattleRoyale()


def _prefetch_followers_for_all() -> list:
    """Prefetch followers (including avatars) once so ALL mode can reuse them."""
    try:
        api_client = InstagramAPI()
        # Support test mode
        if config.TEST_MINIMAL_PLAYERS:
            print(f"🧪 TEST MODE: Prefetching {config.TEST_MINIMAL_PLAYER_COUNT} test players for ALL mode")
            followers = api_client.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            followers = api_client.fetch_followers(config.FOLLOWER_COUNT)
        shared_api.set_prefetched_followers(followers)
        return followers
    except Exception as e:
        print(f"Warning: Failed to prefetch followers once for ALL mode: {e}")
        return []


def _run_single_mode(game_mode: str):
    """Set per-game config and run one game mode."""
    config.GAME_MODE = game_mode
    config.OUTPUT_VIDEO_PATH = config.get_output_video_path(game_mode=game_mode)
    config.FOLLOWER_IMPORT_FILE = _get_follower_import_file(game_mode)
    game = _create_game_instance(game_mode)
    game.run()


def main():
    """
    Entry point for the game
    Selects game mode based on config.GAME_MODE
    """
    try:
        _ensure_webhook_services()

        # Select game mode based on config
        game_mode = getattr(config, 'GAME_MODE', 'battle_royale')

        if game_mode == "ALL":
            print("Running ALL game modes sequentially:")
            print(" -> " + ", ".join(getattr(config, "ALL_GAME_MODES", [])))
            default_import_file = _DEFAULT_FOLLOWER_IMPORT_FILE
            config.FOLLOWER_IMPORT_FILE = default_import_file
            prefetched = _prefetch_followers_for_all()
            for mode in getattr(config, "ALL_GAME_MODES", []):
                # Refresh the cache reference before each run
                mode_import_file = _get_follower_import_file(mode)
                if prefetched and mode_import_file == default_import_file:
                    shared_api.set_prefetched_followers(prefetched)
                else:
                    shared_api.clear_prefetched_followers()
                _run_single_mode(mode)
            shared_api.clear_prefetched_followers()
            # Restore GAME_MODE for downstream references (e.g., manual push)
            config.GAME_MODE = "ALL"
            config.OUTPUT_VIDEO_PATH = config.get_output_video_path(game_mode="ALL")
            config.FOLLOWER_IMPORT_FILE = default_import_file
        else:
            _run_single_mode(game_mode)
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
