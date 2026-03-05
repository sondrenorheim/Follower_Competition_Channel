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
import importlib
from datetime import datetime
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
try:
    from shared.video_variant_builder import (
        ensure_non_ig_join_variant,
        get_last_non_ig_variant_build_info,
    )
except Exception:
    ensure_non_ig_join_variant = None
    get_last_non_ig_variant_build_info = None

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


def _normalize_smb_mode(game_mode: str | None):
    try:
        from super_follower_bros_shared.levels import normalize_smb_mode
    except Exception:
        return None
    return normalize_smb_mode(game_mode)


def _get_follower_import_file(game_mode: str) -> str:
    overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
    if isinstance(overrides, dict):
        override = overrides.get(game_mode)
        if override:
            return override
        # All SMB1 levels use the same club-members source file.
        if _normalize_smb_mode(game_mode):
            smb_override = overrides.get("super_follower_bros")
            if smb_override:
                return smb_override
            smb_override = overrides.get("super_follower_bros_1_2")
            if smb_override:
                return smb_override
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


def _pid_is_running(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    try:
        os.kill(pid, 0)
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

    tunnel_provider = str(getattr(config, "TUNNEL_PROVIDER", "ngrok")).strip().lower()
    if tunnel_provider in ("cloudflare", "cloudflared"):
        tunnel_provider = "cloudflared"
    elif tunnel_provider != "ngrok":
        print(f"Warning: Unknown TUNNEL_PROVIDER '{tunnel_provider}', defaulting to ngrok.")
        tunnel_provider = "ngrok"

    if tunnel_provider == "cloudflared":
        _ensure_cloudflared_tunnel(base_dir, log_dir, hidden, webhook_port)
    else:
        _ensure_ngrok_tunnel(base_dir, log_dir, hidden)


def _ensure_cloudflared_tunnel(base_dir: Path, log_dir: Path, hidden: bool, webhook_port: int):
    metrics_port = int(getattr(config, "CLOUDFLARED_METRICS_PORT", 49312))
    tunnel_mode = str(getattr(config, "CLOUDFLARED_TUNNEL_MODE", "quick")).strip().lower()
    tunnel_name = str(getattr(config, "CLOUDFLARED_TUNNEL_NAME", "")).strip()
    config_path = str(getattr(config, "CLOUDFLARED_CONFIG_PATH", "")).strip()
    if tunnel_mode not in ("quick", "named"):
        print(f"Warning: Unknown CLOUDFLARED_TUNNEL_MODE '{tunnel_mode}', defaulting to quick.")
        tunnel_mode = "quick"
    tunnel_ok = False
    if metrics_port > 0 and _is_port_open("127.0.0.1", metrics_port):
        tunnel_ok = True

    if not tunnel_ok:
        cloudflared_path = getattr(config, "CLOUDFLARED_PATH", "cloudflared")
        cloudflared_bin = shutil.which(cloudflared_path) or cloudflared_path
        url = getattr(config, "CLOUDFLARED_URL", f"http://localhost:{webhook_port}")
        log_level = str(getattr(config, "CLOUDFLARED_LOG_LEVEL", "")).strip()
        no_autoupdate = bool(getattr(config, "CLOUDFLARED_NO_AUTOUPDATE", True))
        protocol = str(getattr(config, "CLOUDFLARED_PROTOCOL", "")).strip().lower()
        edge_ip_version = str(getattr(config, "CLOUDFLARED_EDGE_IP_VERSION", "")).strip()

        cloudflared_command = [cloudflared_bin, "tunnel"]
        if no_autoupdate:
            cloudflared_command.append("--no-autoupdate")
        if log_level:
            cloudflared_command.extend(["--loglevel", log_level])
        if metrics_port > 0:
            cloudflared_command.extend(["--metrics", f"127.0.0.1:{metrics_port}"])
        if protocol in ("auto", "quic", "http2"):
            cloudflared_command.extend(["--protocol", protocol])
        if edge_ip_version in ("4", "6", "auto"):
            cloudflared_command.extend(["--edge-ip-version", edge_ip_version])

        print("Cloudflare Tunnel not running. Starting cloudflared...")
        if tunnel_mode == "named":
            if not tunnel_name:
                print("Warning: CLOUDFLARED_TUNNEL_NAME is empty. Falling back to quick tunnel.")
                cloudflared_command.extend(["--url", url])
                tunnel_mode = "quick"
            else:
                cfg_path = Path(config_path) if config_path else (Path.home() / ".cloudflared" / "config.yml")
                if not cfg_path.exists():
                    print(f"Warning: cloudflared config not found at {cfg_path}. Falling back to quick tunnel.")
                    cloudflared_command.extend(["--url", url])
                    tunnel_mode = "quick"
                else:
                    # For named tunnels, global flags must come before `run`.
                    cloudflared_command.extend(["--config", str(cfg_path), "run", tunnel_name])
        else:
            cloudflared_command.extend(["--url", url])

        _start_process_in_new_console(
            cloudflared_command,
            str(base_dir),
            hidden=hidden,
            log_path=log_dir / "cloudflared.log",
        )


def _ensure_ngrok_tunnel(base_dir: Path, log_dir: Path, hidden: bool):
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


def _ensure_discord_bot():
    if not getattr(config, "AUTO_START_DISCORD_BOT", False):
        return

    base_dir = Path(__file__).resolve().parent
    log_dir = Path(getattr(config, "DISCORD_BOT_LOG_DIR", "logs/discord_bot"))
    hidden = bool(getattr(
        config,
        "DISCORD_BOT_HEADLESS",
        getattr(config, "WEBHOOK_SERVICE_HEADLESS", False),
    ))

    script_name = getattr(config, "DISCORD_BOT_SCRIPT", "discord_bot/bot.py")
    script_path = base_dir / script_name
    if not script_path.exists():
        print(f"Warning: Discord bot script not found at {script_path}")
        return

    pid_path = Path(getattr(config, "DISCORD_BOT_PID_FILE", "discord_bot/discord_bot.pid"))
    if not pid_path.is_absolute():
        pid_path = base_dir / pid_path

    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
        if pid and _pid_is_running(pid):
            return
        try:
            pid_path.unlink()
        except Exception:
            pass

    print("Discord bot not running. Starting discord_bot/bot.py...")
    bot_env = None
    if hidden:
        bot_env = dict(os.environ)
        bot_env["PYTHONUNBUFFERED"] = "1"
    _start_process_in_new_console(
        [sys.executable, str(script_path)],
        str(base_dir),
        hidden=hidden,
        log_path=log_dir / "discord_bot.log",
        env=bot_env,
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
    smb_mode = _normalize_smb_mode(game_mode)
    if smb_mode:
        from super_follower_bros_shared.levels import world_label_for_mode

        module_name = "super_follower_bros" if game_mode == "super_follower_bros" else smb_mode
        print(f"Starting Super Follower Bros. {world_label_for_mode(smb_mode)} mode...")
        module = importlib.import_module(module_name)

        factory = getattr(module, "create_game", None)
        if callable(factory):
            return factory()

        game_cls = getattr(module, "Game", None)
        if callable(game_cls):
            return game_cls()

        raise RuntimeError(f"{module_name} is missing create_game() or Game class")

    if game_mode == "fighter_arena":
        from fighter_arena import FighterBattleArena
        print("Starting Fighter Arena mode...")
        return FighterBattleArena()
    elif game_mode == "followers_io":
        from followers_io import FollowersIOGame
        print("Starting Followers.io mode...")
        return FollowersIOGame()
    elif game_mode == "maze_rush":
        from maze_rush import MazeRushGame
        print("Starting Maze Rush mode...")
        return MazeRushGame()
    elif game_mode == "flappy_followers":
        from flappy_followers import FlappyFollowersGame
        print("Starting Flappy Followers mode...")
        return FlappyFollowersGame()
    elif game_mode == "tiny_followers":
        from tiny_followers import TinyFollowersGame
        print("Starting Tiny Followers mode...")
        return TinyFollowersGame()
    elif game_mode == "jetpack_followers":
        from jetpack_followers import JetpackFollowersGame
        print("Starting Jetpack Followers mode...")
        return JetpackFollowersGame()
    elif game_mode == "doodle_followers":
        from doodle_followers import DoodleFollowersGame
        print("Starting Doodle Followers mode...")
        return DoodleFollowersGame()
    elif game_mode == "crossy_followers":
        if bool(getattr(config, "CROSSY_USE_3D_RENDERER", False)):
            try:
                from crossy_followers.game_3d import CrossyFollowers3DGame

                print("Starting Crossy Followers mode (3D)...")
                return CrossyFollowers3DGame()
            except Exception as exc:
                print(f"Warning: Failed to start Crossy 3D renderer ({exc}). Falling back to 2D renderer.")
        from crossy_followers import CrossyFollowersGame
        print("Starting Crossy Followers mode...")
        return CrossyFollowersGame()
    elif game_mode == "subway_followers":
        from subway_followers import SubwayFollowersGame
        print("Starting Subway Followers mode...")
        return SubwayFollowersGame()
    elif game_mode == "subway_followers_3d":
        from subway_followers_3d import SubwayFollowers3DGame
        print("Starting Subway Followers 3D mode...")
        return SubwayFollowers3DGame()
    elif game_mode == "mini_golf":
        from mini_golf import MiniGolfGame
        print("Starting Mini Golf mode...")
        return MiniGolfGame()
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
    elif game_mode == "math_drop":
        from math_drop import MathDropGame
        print("Starting Math Drop mode...")
        return MathDropGame()
    elif game_mode == "plinko":
        from plinko import PlinkoGame
        print("Starting Plinko mode...")
        return PlinkoGame()
    elif game_mode == "wheel_spinner":
        from wheel_spinner import WheelSpinnerGame
        print("Starting Wheel Spinner mode...")
        return WheelSpinnerGame()
    elif game_mode == "lava_platform":
        from lava_platform import LavaPlatformGame
        print("Starting Lava Platform mode...")
        return LavaPlatformGame()
    elif game_mode == "beacon_blitz":
        from beacon_blitz import BeaconBlitzGame
        print("Starting Beacon Blitz mode...")
        return BeaconBlitzGame()
    elif game_mode == "lane_rush":
        from lane_rush import LaneRushGame
        print("Starting Lane Rush mode...")
        return LaneRushGame()
    elif game_mode == "discord_signal":
        from discord_signal import DiscordSignalGame
        print("Starting Discord Signal mode...")
        return DiscordSignalGame()
    elif game_mode == "club_duel":
        from club_duel import ClubDuelGame
        print("Starting Club Duel mode...")
        return ClubDuelGame()
    elif game_mode == "club_relic":
        from club_relic import ClubRelicGame
        print("Starting Relic Rally mode...")
        return ClubRelicGame()
    elif game_mode == "moon_stack":
        from moon_stack import MoonStackGame
        print("Starting Moon Stack mode...")
        return MoonStackGame()

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

    if not bool(getattr(config, "EXPORT_VIDEO", False)):
        return
    if not bool(getattr(config, "NON_IG_VARIANT_ENABLED", True)):
        return
    if not bool(getattr(config, "NON_IG_VARIANT_GENERATE_AFTER_EXPORT", True)):
        return
    if ensure_non_ig_join_variant is None:
        print("[WARN] Non-IG variant builder unavailable; skipping JOIN footer variant generation.")
        return

    base_video_raw = str(getattr(config, "OUTPUT_VIDEO_PATH", "") or "").strip()
    if not base_video_raw:
        return
    base_video_path = Path(base_video_raw)

    variant_video_path = Path(
        config.get_non_ig_variant_video_path(
            game_mode=game_mode,
            day_number=getattr(config, "DAY_NUMBER", None),
            test_mode=getattr(config, "TEST_MODE", None),
        )
    )

    needs_generation = True
    try:
        if variant_video_path.exists() and variant_video_path.stat().st_mtime >= base_video_path.stat().st_mtime:
            needs_generation = False
    except Exception:
        needs_generation = True

    try:
        resolved_path = ensure_non_ig_join_variant(base_video_path, variant_video_path)
        if resolved_path == variant_video_path and variant_video_path.exists():
            if needs_generation:
                message = f"Generated non-IG JOIN variant: {variant_video_path}"
                if get_last_non_ig_variant_build_info is not None:
                    info = get_last_non_ig_variant_build_info() or {}
                    top_y = info.get("top_y")
                    mode = str(info.get("placement_mode") or "").strip()
                    if top_y is not None:
                        if mode:
                            message += f" (top_y={top_y}, mode={mode})"
                        else:
                            message += f" (top_y={top_y})"
                print(message)
        else:
            print("Variant generation failed; falling back to base video")
    except Exception as exc:
        print(f"Variant generation failed; falling back to base video ({exc})")


def _write_scheduled_upload_context() -> Path | None:
    """Persist the current ALL-mode run settings for scheduled uploads."""
    try:
        log_dir = Path(__file__).resolve().parent / "logs" / "scheduled_upload"
        log_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "day_number": int(getattr(config, "DAY_NUMBER", 0)),
            "all_game_modes": list(getattr(config, "ALL_GAME_MODES", [])),
            "game_mode": getattr(config, "GAME_MODE", ""),
            "timestamp": datetime.now().isoformat(),
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = log_dir / f"run_context_day_{payload['day_number']}_{stamp}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        return path
    except Exception as e:
        print(f"Warning: Failed to write scheduled upload context: {e}")
        return None


def _start_scheduled_upload_background(context_path: Path | None = None):
    """Start the scheduled upload process in background."""
    base_dir = Path(__file__).resolve().parent
    script_path = base_dir / "scheduled_upload.py"

    if not script_path.exists():
        print("Warning: scheduled_upload.py not found")
        return

    log_dir = base_dir / "logs" / "scheduled_upload"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"launcher_{config.DAY_NUMBER}.log"

    command = [sys.executable, str(script_path), "--background"]
    if context_path:
        command.extend(["--context-file", str(context_path)])

    try:
        log_file = open(log_path, "a", encoding="utf-8")

        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                command,
                cwd=str(base_dir),
                creationflags=flags,
                stdout=log_file,
                stderr=log_file,
            )
        else:
            subprocess.Popen(
                command,
                cwd=str(base_dir),
                start_new_session=True,
                stdout=log_file,
                stderr=log_file,
            )

        print("\n" + "=" * 60)
        print("Scheduled upload process started in background")
        print(f"Log: {log_path}")
        print("=" * 60)
    except Exception as e:
        print(f"Warning: Failed to start scheduled upload: {e}")


def _push_stats_background(game_mode: str, day_number: int):
    """Push stats to GitHub in background after a game completes."""
    base_dir = Path(__file__).resolve().parent
    log_dir = base_dir / "logs" / "stats_push"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"day_{day_number}_{game_mode}.log"

    # Simple Python command to push stats
    push_code = """
import sys
sys.path.insert(0, r'{base_dir}')
from shared import auto_push
auto_push.push_stats_to_github()
print('Stats push complete for {game_mode}')
""".format(base_dir=str(base_dir), game_mode=game_mode)

    command = [sys.executable, "-c", push_code]

    try:
        log_file = open(log_path, "a", encoding="utf-8")

        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                command,
                cwd=str(base_dir),
                creationflags=flags,
                stdout=log_file,
                stderr=log_file,
            )
        else:
            subprocess.Popen(
                command,
                cwd=str(base_dir),
                start_new_session=True,
                stdout=log_file,
                stderr=log_file,
            )

        print(f"  -> Background stats push started for {game_mode}")
    except Exception as e:
        print(f"Warning: Failed to start background stats push: {e}")


def _normalize_all_mode_push_strategy(value: str) -> str:
    """Normalize ALL-mode auto-push strategy names."""
    strategy = str(value or "").strip().lower()
    if strategy in {"per_game", "every_game", "each_game"}:
        return "per_game"
    if strategy in {"every_n_games", "batch", "batched", "interval"}:
        return "every_n_games"
    return "final_only"


def _compute_all_mode_batch_checkpoints(total_modes: int, batch_size: int) -> set[int]:
    """
    Return completed-game counts that should trigger intermediate pushes.
    Final push is handled separately after all games finish.
    """
    if total_modes <= 0:
        return set()
    size = max(1, int(batch_size))
    return {count for count in range(size, total_modes, size)}


def _log_all_mode_exception(game_mode: str, exc: Exception) -> Path:
    """Write a crash log for a failed ALL-mode game and return the log path."""
    base_dir = Path(__file__).resolve().parent
    log_dir = base_dir / "logs" / "run_all"
    log_dir.mkdir(parents=True, exist_ok=True)
    day_number = getattr(config, "DAY_NUMBER", 0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"day_{day_number}_{game_mode}_{timestamp}.log"

    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write("=" * 60 + "\n")
            log_file.write(f"Crash in ALL mode: {game_mode}\n")
            log_file.write(f"Day: {day_number}\n")
            log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
            log_file.write(f"Exception: {type(exc).__name__}: {exc}\n")
            log_file.write("\nTraceback:\n")
            import traceback
            traceback.print_exc(file=log_file)
            log_file.write("\n")
    except Exception:
        # If logging fails, fall back to stderr in the caller.
        pass

    return log_path


def main():
    """
    Entry point for the game
    Selects game mode based on config.GAME_MODE
    """
    try:
        _ensure_webhook_services()
        _ensure_discord_bot()

        # Select game mode based on config
        game_mode = getattr(config, 'GAME_MODE', 'battle_royale')

        # When running ALL modes, enforce production settings
        if game_mode == "ALL":
            config.TEST_MODE = False
            config.EXPORT_VIDEO = True
            config.DOWNLOAD_PROFILE_PICTURES = True
            config.LOAD_PROFILE_PICTURES = True
            config.TEST_MINIMAL_PLAYERS = False

        if game_mode == "ALL":
            print("Running ALL game modes sequentially:")
            all_modes = list(getattr(config, "ALL_GAME_MODES", []))
            print(" -> " + ", ".join(all_modes))
            push_strategy = _normalize_all_mode_push_strategy(
                getattr(config, "AUTO_PUSH_ALL_MODE_STRATEGY", "every_n_games")
            )
            push_batch_size = max(1, int(getattr(config, "AUTO_PUSH_ALL_MODE_BATCH_SIZE", 5) or 5))
            push_checkpoints = _compute_all_mode_batch_checkpoints(len(all_modes), push_batch_size)
            print(
                f"ALL-mode stats push strategy: {push_strategy}"
                + (f" (every {push_batch_size} games)" if push_strategy == "every_n_games" else "")
            )
            all_mode_push_enabled = (
                not config.TEST_MODE
                and bool(getattr(config, "AUTO_PUSH_STATS", False))
            )
            suppress_per_game_push = (
                all_mode_push_enabled
                and push_strategy != "per_game"
                and bool(getattr(config, "AUTO_PUSH_ALL_MODE_SUPPRESS_PER_GAME_PUSH", True))
            )
            original_auto_push_stats = bool(getattr(config, "AUTO_PUSH_STATS", False))
            if suppress_per_game_push:
                config.AUTO_PUSH_STATS = False
                print("ALL-mode: per-game module auto-push suppressed; using batched checkpoints only.")
            default_import_file = _DEFAULT_FOLLOWER_IMPORT_FILE
            config.FOLLOWER_IMPORT_FILE = default_import_file
            # Start scheduled uploads immediately so it can wait for the set time
            # while games are still rendering.
            context_path = _write_scheduled_upload_context()
            _start_scheduled_upload_background(context_path)
            prefetched = _prefetch_followers_for_all()
            completed_modes = 0
            try:
                for mode in all_modes:
                    # Refresh the cache reference before each run
                    mode_import_file = _get_follower_import_file(mode)
                    if prefetched and mode_import_file == default_import_file:
                        shared_api.set_prefetched_followers(prefetched)
                    else:
                        shared_api.clear_prefetched_followers()
                    try:
                        _run_single_mode(mode)
                    except Exception as e:
                        log_path = _log_all_mode_exception(mode, e)
                        print(f"\nERROR: {mode} crashed. See log: {log_path}\n")
                        continue
                    completed_modes += 1
                    if all_mode_push_enabled:
                        if push_strategy == "per_game":
                            # Legacy behavior: push after each game.
                            _push_stats_background(mode, config.DAY_NUMBER)
                        elif push_strategy == "every_n_games" and completed_modes in push_checkpoints:
                            # Batched behavior: push every N completed games.
                            _push_stats_background(f"ALL_batch_{completed_modes}", config.DAY_NUMBER)
                if (
                    all_mode_push_enabled
                    and push_strategy != "per_game"
                    and completed_modes > 0
                ):
                    # Push once after all games are complete (final_only + every_n_games).
                    config.GAME_MODE = "ALL"
                    _push_stats_background("ALL", config.DAY_NUMBER)
            finally:
                shared_api.clear_prefetched_followers()
                config.AUTO_PUSH_STATS = original_auto_push_stats
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
