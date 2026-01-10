"""
Anime Fighting Game - Main Orchestrator

Manages 1v1 tournament bracket with anime-style combat mechanics.
Runs sequential matches through tournament rounds until a champion is crowned.
"""

import json
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import pygame
import config
from PIL import Image

from shared import InstagramAPI, VideoRecorder, ScoringSystem, PlayerStatistics, SoundManager, AudioLogger

from .fighter import AnimeFighter
from .arena import AnimeFightingArena
from .renderer import AnimeFightingRenderer
from .camera_fx import CameraFX, update_particles, update_afterimages
from .combat import (
    HitShape, Projectile, update_hitshapes, update_projectiles,
    resolve_hits, separate_fighters, detect_clash, resolve_clash
)
from .camera_fx import draw_screen_flash
from .ai import bot_brain


class AnimeAudioLogger(AudioLogger):
    """Audio logger that uses the game clock for timestamps."""

    def __init__(self, time_provider):
        super().__init__()
        self._time_provider = time_provider

    def start(self):
        """Start logging audio events using the game clock."""
        self.start_time = self._time_provider()
        self.recording = True
        print("Audio event logging started (game clock)")

    def get_timestamp(self) -> float:
        """Get current timestamp relative to the game clock."""
        if self.start_time is None:
            return 0.0
        return self._time_provider() - self.start_time


class AnimeFightingGame:
    """
    Main game class for Anime Fighting tournament mode

    Manages:
    - Fighter initialization and bracket seeding
    - Tournament round progression
    - Individual match execution (1v1 combat)
    - Statistics tracking and video recording
    """

    def __init__(self):
        """Initialize game systems"""
        pygame.init()

        # Screen setup (540x960 vertical)
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Anime Fighting Tournament")

        # World surface for camera effects
        self.world_surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.world_surface.convert_alpha()

        # Clock for timing
        self.clock = pygame.time.Clock()

        # Game systems
        self.api = InstagramAPI()
        self.arena = AnimeFightingArena(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.renderer = AnimeFightingRenderer(self.screen)
        self.camera_fx = CameraFX(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

        # Statistics and scoring
        self.scoring = ScoringSystem()
        self.statistics = PlayerStatistics()

        # Sound system (must be initialized before VideoRecorder for audio logging)
        self.audio_logger = AnimeAudioLogger(self._get_audio_time)
        self.sound = SoundManager(audio_logger=self.audio_logger)

        # Video recording (with audio logger for sound effects in export)
        self.recorder = None
        if config.EXPORT_VIDEO:
            output_path = config.get_output_video_path("anime_fighting")
            self.recorder = VideoRecorder(
                output_path=output_path,
                fps=config.VIDEO_FPS,
                audio_logger=self.audio_logger,
                countdown_audio_path=""
            )

        # Tournament state
        self.all_fighters: List[AnimeFighter] = []
        self.bracket: List[List[AnimeFighter]] = []  # List of rounds, each round is list of fighters
        self.current_round = 0
        self.current_match = 0

        # Match state
        self.fighter1: Optional[AnimeFighter] = None
        self.fighter2: Optional[AnimeFighter] = None
        self.hitshapes: List[HitShape] = []
        self.projectiles: List[Projectile] = []
        self.particles = []
        self.afterimages = []

        # Game phase
        self.phase = "intro"  # intro, round_intro, top16_overview, bracket_display, countdown, fighting, winner, bracket_transition, finished
        self.phase_start_time = 0.0
        self.match_time = 0.0
        self.match_start_time = 0.0

        # Game time accumulator (replaces time.time() for video sync)
        # This ensures video playback speed matches game simulation
        self.game_time = 0.0

        # Best-of-3 Finals state
        self.is_finals = False
        self.finals_wins = {1: 0, 2: 0}  # Fighter1 wins, Fighter2 wins
        self.finals_match_number = 0  # Current match in finals (0, 1, or 2)

        # Round intro tracking
        self.last_round_intro_round = -1
        self.round_intro_header = ""
        self.round_intro_label = ""
        self.pending_top16_overview = False
        self.top16_overview_entries = []
        self.top16_overview_duration = 3.0

        # Monthly points map (username -> points)
        self.monthly_points_map = {}

        # Running flag
        self.running = True

    def run(self):
        """Main game loop (entry point called by main.py)"""
        # Setup fighters and bracket
        self.setup_followers()
        self.create_bracket()

        # Start with intro phase
        self.phase = "intro"
        self.phase_start_time = 0.0  # Use game_time (starts at 0)

        # Main loop
        while self.running:
            # Use VIDEO_FPS for anime fighting to match video export rate
            dt_real = self.clock.tick(config.VIDEO_FPS) / 1000.0

            # Cap delta time to prevent simulation "catch up" issues
            dt_real = min(dt_real, config.MAX_DELTA_TIME)

            # Accumulate game time (ensures video sync - 1 second of video = 1 second of game time)
            self.game_time += dt_real

            # Start audio logging once the game clock is running
            if not self.audio_logger.recording:
                self.audio_logger.start()

            # Update camera FX (runs in real time)
            self.camera_fx.update(dt_real)

            # Get simulation dt (freezes during hitstop)
            dt_sim = self.camera_fx.sim_dt(dt_real)

            # Handle events
            self._handle_events()

            # Update game state
            self._update(dt_sim, dt_real)

            # Render
            self._render()

            # Record frame (no time parameter - recorder uses internal time tracking)
            if self.recorder:
                self.recorder.capture_frame(self.screen, current_time=self.game_time)

        # Cleanup
        self._cleanup()

    def setup_followers(self):
        """Fetch followers and create fighters from monthly leaderboard"""
        print("Fetching top fighters from monthly leaderboard...")

        # Get bracket size from config (default 16)
        bracket_size = getattr(config, 'ANIME_FIGHTING_BRACKET_SIZE', 16)

        # Get current month/year for monthly tournament
        current_year = datetime.now().year
        current_month = datetime.now().month
        self.monthly_points_map = self._get_monthly_points_map(current_year, current_month)

        # Fetch top fighters from monthly leaderboard
        monthly_top = self._get_monthly_leaderboard_from_points(bracket_size)

        # If fewer than bracket_size fighters in monthly leaderboard, fall back to all-time
        if len(monthly_top) < bracket_size:
            print(f"⚠️  Only {len(monthly_top)} fighters in monthly leaderboard, falling back to all-time top {bracket_size}")
            all_time_top = self.statistics.get_all_time_leaderboard(top_n=bracket_size)
            # Convert all-time format (username, points, stats) to monthly format (username, stats)
            monthly_top = [(username, stats) for username, points, stats in all_time_top]
            self.tournament_type = "ALL-TIME"
        else:
            self.tournament_type = f"{datetime.now().strftime('%B %Y').upper()}"

        if not monthly_top:
            print("No leaderboard data found! Using random followers.")
            # Fall back to random follower selection
            follower_data = self.api.fetch_followers(bracket_size)

            if not follower_data:
                print("No followers found! Using test data.")
                # Create test fighters
                for i in range(bracket_size):
                    test_data = {
                        'id': i,
                        'username': f'Fighter_{i+1}',
                        'avatar': None,
                        'color': (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                    }
                    fighter = AnimeFighter(test_data, (0, 0))
                    self.all_fighters.append(fighter)
            else:
                # Create fighters from random follower data
                for data in follower_data[:bracket_size]:
                    fighter = AnimeFighter(data, (0, 0))
                    self.all_fighters.append(fighter)

            self.monthly_rankings = {}
            self.tournament_type = "RANDOM"
        else:
            # Extract usernames from monthly leaderboard
            top_usernames = [username for username, _ in monthly_top]

            # Create a username -> follower_data map for qualifiers
            follower_map = self._fetch_follower_data_for_usernames(top_usernames)

            # Create fighters for top monthly performers
            for rank, (username, stats) in enumerate(monthly_top, start=1):
                # Get follower data (with avatar) for this username
                follower_data = follower_map.get(username, {
                    'id': rank,
                    'username': username,
                    'avatar': None,
                    'color': random.choice(config.RANDOM_COLORS)
                })

                fighter = AnimeFighter(follower_data, (0, 0))
                self.all_fighters.append(fighter)

            # Store monthly rankings for seeding (username -> rank 1-16)
            self.monthly_rankings = {username: idx + 1 for idx, (username, _) in enumerate(monthly_top)}

            print(f"✅ Created {len(self.all_fighters)} fighters from {self.tournament_type} tournament leaderboard")

        self._build_top16_overview_entries()
        print(f"Created {len(self.all_fighters)} fighters")

    def _get_monthly_points_map(self, year: int, month: int) -> dict:
        """Build a username -> monthly points map from game history."""
        game_history_file = "game_history.json"
        if not os.path.exists(game_history_file):
            return {}

        try:
            with open(game_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            games = data.get("games", [])
            month_prefix = f"{year}-{month:02d}"
            monthly_games = [g for g in games if g.get("timestamp", "").startswith(month_prefix)]

            monthly_points = {}
            for game in monthly_games:
                for result in game.get("results", []):
                    username = result.get("username")
                    points = result.get("points", 0)
                    if username:
                        monthly_points[username] = monthly_points.get(username, 0.0) + points

            return monthly_points
        except Exception as exc:
            print(f"Error loading monthly points: {exc}")
            return {}

    def _get_monthly_leaderboard_from_points(self, top_n: int) -> List[Tuple[str, list]]:
        """Build a monthly leaderboard using the cached monthly points map."""
        if not self.monthly_points_map:
            return []

        leaderboard = []
        for username in self.monthly_points_map.keys():
            stats = self.statistics.get_player_stats(username)
            leaderboard.append((username, stats))

        leaderboard.sort(key=lambda x: self.monthly_points_map.get(x[0], 0.0), reverse=True)
        return leaderboard[:top_n]

    def _fetch_follower_data_for_usernames(self, usernames: List[str]) -> dict:
        """Fetch follower data for specific usernames with correct avatars."""
        follower_map = {}
        if not usernames:
            return follower_map

        remaining = set(usernames)

        # First pass: load from avatar cache if available
        for username in list(remaining):
            avatar_img = self._load_cached_avatar(username)
            if avatar_img is not None:
                follower_map[username] = self._build_follower_data(username, avatar_img)
                remaining.remove(username)

        if not remaining:
            return follower_map

        import_file = getattr(config, 'FOLLOWER_IMPORT_FILE', '')
        if import_file and os.path.exists(import_file):
            try:
                with open(import_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    follower_list = data
                elif isinstance(data, dict):
                    if 'followers' in data:
                        follower_list = data.get('followers', [])
                    elif 'relationships_followers' in data:
                        follower_list = data.get('relationships_followers', [])
                    else:
                        follower_list = data.get('data', [])
                else:
                    follower_list = []

                for item in follower_list:
                    username, profile_pic_url = self._extract_username_entry(item)
                    if not username or username not in remaining:
                        continue

                    avatar_img = None
                    if profile_pic_url and getattr(config, 'DOWNLOAD_PROFILE_PICTURES', False):
                        avatar_img = self.api._download_avatar(profile_pic_url, username=username)
                    if avatar_img is None:
                        avatar_img = self._load_cached_avatar(username)

                    follower_map[username] = self._build_follower_data(username, avatar_img)
                    remaining.remove(username)
                    if not remaining:
                        break
            except Exception as exc:
                print(f"Error loading follower import file: {exc}")

        if remaining:
            sample = ", ".join(sorted(list(remaining))[:5])
            print(f"Missing avatar data for {len(remaining)} qualifiers: {sample}")

        return follower_map

    def _load_cached_avatar(self, username: str) -> Optional[Image.Image]:
        """Load avatar from disk cache if it exists."""
        if not getattr(config, 'LOAD_PROFILE_PICTURES', True):
            return None

        cache_file = Path("avatar_cache") / f"{username}.jpg"
        if not cache_file.exists():
            return None

        try:
            return Image.open(cache_file).convert("RGBA")
        except Exception:
            return None

    def _extract_username_entry(self, item) -> Tuple[Optional[str], Optional[str]]:
        """Extract username and profile_pic_url from an import entry."""
        username = None
        profile_pic_url = None

        if isinstance(item, dict):
            if 'string_list_data' in item and item['string_list_data']:
                username = item['string_list_data'][0].get('value')
            elif 'username' in item:
                username = item.get('username')
                profile_pic_url = item.get('profile_pic_url') or item.get('profile_pic_url_hd')
            elif 'value' in item:
                username = item.get('value')
            else:
                username = item.get('user')

            if not profile_pic_url:
                profile_pic_url = item.get('avatar_url') or item.get('avatarurl')
        elif isinstance(item, str):
            username = item

        return username, profile_pic_url

    def _build_follower_data(self, username: str, avatar_img: Optional[Image.Image]) -> dict:
        """Build follower data dict for AnimeFighter."""
        return {
            'id': username,
            'username': username,
            'avatar': avatar_img,
            'color': random.choice(config.RANDOM_COLORS)
        }

    def _build_top16_overview_entries(self):
        """Prepare overview entries with fighter avatars and monthly points."""
        self.top16_overview_entries = []
        max_entries = min(16, len(self.all_fighters))
        for fighter in self.all_fighters[:max_entries]:
            points = 0.0
            if hasattr(fighter, 'username'):
                points = self.monthly_points_map.get(fighter.username, 0.0)
            self.top16_overview_entries.append((fighter, points))

    def _get_audio_time(self) -> float:
        """Return audio timeline time aligned to exported video frames."""
        if self.recorder and getattr(config, "EXPORT_VIDEO", False):
            frame_count = self.recorder.get_frame_count()
            fps = self.recorder.fps
            if not self.recorder.use_streaming:
                fps = fps * self.recorder.export_speed_factor
            if fps > 0:
                return frame_count / fps
            return 0.0
        return self.game_time

    def create_bracket(self):
        """Create single-elimination tournament bracket with ranked seeding"""
        fighters = list(self.all_fighters)

        # Ensure power of 2
        bracket_size = len(fighters)
        if bracket_size & (bracket_size - 1) != 0:
            # Round down to nearest power of 2
            bracket_size = 2 ** int(math.log2(bracket_size))
            fighters = fighters[:bracket_size]

        # Apply ranked seeding if monthly rankings exist
        if hasattr(self, 'monthly_rankings') and self.monthly_rankings:
            # Sort fighters by monthly ranking (1-16)
            sorted_fighters = sorted(
                fighters,
                key=lambda f: self.monthly_rankings.get(f.username, 999)
            )

            # Apply tournament-style seeding for 16-fighter bracket
            # Matchups: (1,16), (8,9), (5,12), (4,13), (3,14), (6,11), (7,10), (2,15)
            if bracket_size == 16:
                seeded_bracket = [
                    sorted_fighters[0],   # Rank 1
                    sorted_fighters[15],  # Rank 16
                    sorted_fighters[7],   # Rank 8
                    sorted_fighters[8],   # Rank 9
                    sorted_fighters[4],   # Rank 5
                    sorted_fighters[11],  # Rank 12
                    sorted_fighters[3],   # Rank 4
                    sorted_fighters[12],  # Rank 13
                    sorted_fighters[2],   # Rank 3
                    sorted_fighters[13],  # Rank 14
                    sorted_fighters[5],   # Rank 6
                    sorted_fighters[10],  # Rank 11
                    sorted_fighters[6],   # Rank 7
                    sorted_fighters[9],   # Rank 10
                    sorted_fighters[1],   # Rank 2
                    sorted_fighters[14],  # Rank 15
                ]
                fighters = seeded_bracket
                print(f"✅ Applied ranked seeding (1v16, 8v9, 5v12, 4v13, 3v14, 6v11, 7v10, 2v15)")
            else:
                # For other bracket sizes, use standard top-vs-bottom pairing
                # Example for 8: (1,8), (4,5), (3,6), (2,7)
                seeded_bracket = []
                for i in range(bracket_size // 2):
                    seeded_bracket.append(sorted_fighters[i])
                    seeded_bracket.append(sorted_fighters[bracket_size - 1 - i])
                fighters = seeded_bracket
                print(f"✅ Applied ranked seeding (top vs bottom pairing)")
        else:
            # Random seeding (fallback for test data)
            random.shuffle(fighters)
            print(f"Random seeding applied (no monthly rankings)")

        # First round is all fighters
        self.bracket = [fighters]

        print(f"Tournament bracket created: {bracket_size} fighters, {int(math.log2(bracket_size))} rounds")

    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def _update(self, dt_sim: float, dt_real: float):
        """
        Update game state

        Args:
            dt_sim: Simulation delta time (frozen during hitstop)
            dt_real: Real delta time (always running)
        """
        # Use game_time instead of time.time() to ensure video playback is synchronized
        current_time = self.game_time
        elapsed = current_time - self.phase_start_time

        if self.phase == "intro":
            # Show title for 3 seconds, then set up first match
            if elapsed >= 3.0:
                self._start_next_match()  # Sets up fighters and transitions to bracket_display

        elif self.phase == "bracket_display":
            # Show tournament bracket for 2 seconds, then start countdown
            if elapsed >= 2.0:
                self.phase = "countdown"
                self.phase_start_time = current_time

        elif self.phase == "round_intro":
            # Show round intro before bracket overview
            if elapsed >= 2.0:
                if self.pending_top16_overview:
                    self.pending_top16_overview = False
                    self.phase = "top16_overview"
                    self.phase_start_time = current_time
                else:
                    self.phase = "bracket_display"
                    self.phase_start_time = current_time

        elif self.phase == "top16_overview":
            if elapsed >= self.top16_overview_duration:
                self.phase = "bracket_display"
                self.phase_start_time = current_time

        elif self.phase == "countdown":
            # 3-2-1-FIGHT countdown (3 seconds)
            if elapsed >= 3.0:
                self.phase = "fighting"
                self.phase_start_time = current_time
                self.match_start_time = current_time

        elif self.phase == "fighting":
            if dt_sim > 0:  # Only update during non-hitstop
                self._update_match(dt_sim, current_time)

        elif self.phase == "winner":
            # Show winner for 2 seconds
            if elapsed >= 2.0:
                self._advance_bracket()

        elif self.phase == "bracket_transition":
            # Show bracket status for 3 seconds
            if elapsed >= 3.0:
                self._start_next_match()

        elif self.phase == "finished":
            # Show podium for 10 seconds then exit
            if elapsed >= 10.0:
                self.running = False

    def _update_match(self, dt: float, current_time: float):
        """
        Update active 1v1 match

        Args:
            dt: Delta time
            current_time: Current time
        """
        if not self.fighter1 or not self.fighter2:
            return

        self.match_time = current_time - self.match_start_time

        # Check for timeout
        time_limit = getattr(config, 'ANIME_FIGHTING_MATCH_TIME_LIMIT', 60)
        if self.match_time >= time_limit:
            self._end_match_timeout()
            return

        # AI for both fighters
        bot_brain(self.fighter1, self.fighter2, dt, self.match_time)
        bot_brain(self.fighter2, self.fighter1, dt, self.match_time)

        # Update fighters
        for fighter in [self.fighter1, self.fighter2]:
            fighter.update_cooldowns(dt)
            fighter.update_final_smash_meter(dt)  # Charge Final Smash meter over time
            # Desperation mode visual effects
            was_desperate = getattr(fighter, '_was_desperate', False)
            fighter.update_desperation_mode(dt, self.particles)
            # Play sound when entering desperation mode
            if fighter.is_desperate and not was_desperate and self.sound:
                if hasattr(self.sound, 'play_desperation_activate'):
                    self.sound.play_desperation_activate()

        # Update fighter states (with other_fighter and camera_fx for Final Smash choreography)
        self.fighter1.update_state(dt, self.hitshapes, self.projectiles, self.particles,
                                   other_fighter=self.fighter2, camera_fx=self.camera_fx, sound=self.sound)
        self.fighter2.update_state(dt, self.hitshapes, self.projectiles, self.particles,
                                   other_fighter=self.fighter1, camera_fx=self.camera_fx, sound=self.sound)

        # Update movement and afterimages
        for fighter in [self.fighter1, self.fighter2]:
            fighter.move(dt, self.arena.get_bounds())
            fighter.update_afterimages(dt, self.afterimages)

        # Individual random teleportation for each fighter (8-15 seconds on average)
        if not hasattr(self, 'teleport_timer_f1'):
            self.teleport_timer_f1 = random.uniform(8.0, 15.0)
            self.teleport_timer_f2 = random.uniform(8.0, 15.0)

        self.teleport_timer_f1 -= dt
        if self.teleport_timer_f1 <= 0:
            self._teleport_fighter(self.fighter1, self.fighter2)
            self.teleport_timer_f1 = random.uniform(8.0, 15.0)

        self.teleport_timer_f2 -= dt
        if self.teleport_timer_f2 <= 0:
            self._teleport_fighter(self.fighter2, self.fighter1)
            self.teleport_timer_f2 = random.uniform(8.0, 15.0)

        # Prevent overlap
        separate_fighters(self.fighter1, self.fighter2)

        # Update combat systems
        update_hitshapes(self.hitshapes, dt, [self.fighter1, self.fighter2])
        update_projectiles(self.projectiles, dt, self.arena.get_bounds(), self.particles)

        # Check for clash (both fighters attacking simultaneously)
        clash = detect_clash(self.hitshapes, [self.fighter1, self.fighter2])
        if clash:
            resolve_clash(clash, [self.fighter1, self.fighter2],
                         self.particles, self.camera_fx, self.sound)
            # Clear hitshapes after clash to prevent double-hits
            self.hitshapes.clear()
        else:
            # Normal hit resolution
            resolve_hits(
                self.hitshapes, self.projectiles,
                [self.fighter1, self.fighter2],
                self.particles, self.camera_fx, self.match_time,
                sound=self.sound
            )

        # Update visual effects
        update_particles(self.particles, dt)
        update_afterimages(self.afterimages, dt)

        # Check for KO
        if not self.fighter1.is_alive() or not self.fighter2.is_alive():
            self._end_match_ko()

    def _teleport_fighter(self, fighter, other_fighter):
        """
        Randomly teleport a single fighter to a new position
        Creates dynamic repositioning during combat

        Args:
            fighter: The fighter to teleport
            other_fighter: The opponent (used to avoid teleporting too close)
        """
        from .camera_fx import Particle

        bounds = self.arena.get_bounds()
        center_x = bounds.centerx
        center_y = bounds.centery

        # Create departure particles at current position
        for _ in range(15):
            self.particles.append(
                Particle(
                    pos=pygame.Vector2(fighter.pos.x, fighter.pos.y),
                    vel=pygame.Vector2(
                        random.uniform(-150, 150),
                        random.uniform(-150, 150)
                    ),
                    life=random.uniform(0.3, 0.6),
                    radius=random.uniform(3, 8),
                    color=(150, 100, 255)  # Purple teleport effect
                )
            )

        # Choose random location in arena, but avoid teleporting too close to opponent
        max_attempts = 10
        for _ in range(max_attempts):
            # Pick random position in arena
            new_x = random.uniform(bounds.left + 60, bounds.right - 60)
            new_y = random.uniform(bounds.top + 60, bounds.bottom - 60)

            # Check distance to opponent
            dist_to_other = ((new_x - other_fighter.pos.x) ** 2 +
                           (new_y - other_fighter.pos.y) ** 2) ** 0.5

            # Accept if far enough from opponent (min 150px distance)
            if dist_to_other > 150:
                break

        # Update position
        fighter.pos = pygame.Vector2(new_x, new_y)
        fighter.vel = pygame.Vector2(0, 0)

        # Create arrival particles
        for _ in range(15):
            self.particles.append(
                Particle(
                    pos=pygame.Vector2(fighter.pos.x, fighter.pos.y),
                    vel=pygame.Vector2(
                        random.uniform(-150, 150),
                        random.uniform(-150, 150)
                    ),
                    life=random.uniform(0.3, 0.6),
                    radius=random.uniform(3, 8),
                    color=(100, 150, 255)  # Blue arrival effect
                )
            )

    def _end_match_ko(self):
        """End match due to KO"""
        winner = self.fighter1 if self.fighter1.is_alive() else self.fighter2
        self.phase = "winner"
        self.phase_start_time = self.game_time

        print(f"KO! {winner.username} wins!")

    def _end_match_timeout(self):
        """End match due to timeout"""
        # Fighter with more HP wins
        if self.fighter1.hp > self.fighter2.hp:
            winner = self.fighter1
        elif self.fighter2.hp > self.fighter1.hp:
            winner = self.fighter2
        else:
            # Tie - random winner
            winner = random.choice([self.fighter1, self.fighter2])

        # Mark loser as eliminated
        loser = self.fighter2 if winner == self.fighter1 else self.fighter1
        loser.hp = 0
        loser.alive = False

        self.phase = "winner"
        self.phase_start_time = self.game_time

        print(f"Time! {winner.username} wins by HP!")

    def _start_next_match(self):
        """Start the next match in the tournament"""
        # Check if current round is complete
        current_round_fighters = self.bracket[self.current_round]
        matches_in_round = len(current_round_fighters) // 2

        if self.current_match >= matches_in_round:
            # Round complete - advance to next round
            self._advance_round()
            return

        # Get fighters for this match
        idx1 = self.current_match * 2
        idx2 = self.current_match * 2 + 1

        if idx1 >= len(current_round_fighters) or idx2 >= len(current_round_fighters):
            # No more matches
            self._finish_tournament()
            return

        self.fighter1 = current_round_fighters[idx1]
        self.fighter2 = current_round_fighters[idx2]

        # Check if this is the Finals (only 2 fighters in round)
        if len(current_round_fighters) == 2 and not self.is_finals:
            # Initialize best-of-3 finals
            self.is_finals = True
            self.finals_wins = {1: 0, 2: 0}
            self.finals_match_number = 0
            print(f"\n{'='*40}")
            print(f"GRAND FINALS - BEST OF 3")
            print(f"{'='*40}")

        # Reset fighters with HP multiplier based on round
        # Round of 16 (round 0) has half HP for faster matches
        hp_multiplier = 0.5 if self.current_round == 0 else 1.0

        spawn_positions = self.arena.get_spawn_positions()
        self.fighter1.reset_for_match(spawn_positions[0], hp_multiplier)
        self.fighter2.reset_for_match(spawn_positions[1], hp_multiplier)

        # Face each other
        self.fighter1.facing = pygame.Vector2(1, 0)
        self.fighter2.facing = pygame.Vector2(-1, 0)

        # Clear combat state
        self.hitshapes.clear()
        self.projectiles.clear()
        self.particles.clear()
        self.afterimages.clear()

        # Show bracket display with this matchup highlighted, then countdown
        show_round_intro = self.current_match == 0 and self.current_round != self.last_round_intro_round
        if show_round_intro:
            self.last_round_intro_round = self.current_round
            self.round_intro_header, self.round_intro_label = self._get_round_intro_text()
            fighters_in_round = len(self.bracket[self.current_round]) if self.current_round < len(self.bracket) else 0
            self.pending_top16_overview = fighters_in_round == 16 and bool(self.top16_overview_entries)
            self.phase = "round_intro"
            self.phase_start_time = self.game_time
        else:
            self.phase = "bracket_display"
            self.phase_start_time = self.game_time

        round_name = self._get_round_name()
        if self.is_finals:
            print(f"\n{round_name} - Game {self.finals_match_number + 1} (First to 2 wins)")
            print(f"{self.fighter1.username} [{self.finals_wins[1]}] vs [{self.finals_wins[2]}] {self.fighter2.username}")
        else:
            print(f"\n{round_name} - Match {self.current_match + 1}/{matches_in_round}")
            print(f"{self.fighter1.username} vs {self.fighter2.username}")

    def _advance_bracket(self):
        """Record match winner and prepare for next match"""
        # Determine winner of this game
        game_winner = self.fighter1 if self.fighter1.is_alive() else self.fighter2
        game_loser = self.fighter2 if game_winner == self.fighter1 else self.fighter1

        # Handle best-of-3 finals
        if self.is_finals:
            # Record the win
            if game_winner == self.fighter1:
                self.finals_wins[1] += 1
            else:
                self.finals_wins[2] += 1

            self.finals_match_number += 1

            print(f"Game {self.finals_match_number} Winner: {game_winner.username}")
            print(f"Score: {self.fighter1.username} [{self.finals_wins[1]}] - [{self.finals_wins[2]}] {self.fighter2.username}")

            # Check if someone has won the best-of-3 (first to 2 wins)
            if self.finals_wins[1] >= 2 or self.finals_wins[2] >= 2:
                # Finals complete - determine champion
                champion = self.fighter1 if self.finals_wins[1] >= 2 else self.fighter2
                runner_up = self.fighter2 if champion == self.fighter1 else self.fighter1

                # Mark runner_up as eliminated for tournament results
                runner_up.hp = 0
                runner_up.alive = False

                print(f"\n{'='*40}")
                print(f"CHAMPION: {champion.username} wins {self.finals_wins[1]}-{self.finals_wins[2]}!")
                print(f"{'='*40}")

                # Add champion to next round bracket for display
                if not hasattr(self, '_next_round_fighters'):
                    self._next_round_fighters = []
                self._next_round_fighters.append(champion)

                next_round_index = self.current_round + 1
                while len(self.bracket) <= next_round_index:
                    self.bracket.append([])
                self.bracket[next_round_index] = self._next_round_fighters.copy()

                # Move to finished state
                self.current_match += 1
                self.phase = "bracket_transition"
                self.phase_start_time = self.game_time
            else:
                # More games needed - reset for next finals game
                # Don't increment current_match, just show transition and restart
                self.phase = "bracket_transition"
                self.phase_start_time = self.game_time
            return

        # Normal bracket advancement (non-finals)
        # Initialize next round bracket if needed
        if not hasattr(self, '_next_round_fighters'):
            self._next_round_fighters = []

        # Add winner to temporary list
        self._next_round_fighters.append(game_winner)

        # Immediately update the bracket display for visual feedback
        # Ensure bracket has a slot for the next round
        next_round_index = self.current_round + 1
        while len(self.bracket) <= next_round_index:
            self.bracket.append([])

        # Update the bracket with current winners (for display purposes)
        self.bracket[next_round_index] = self._next_round_fighters.copy()

        # Move to next match
        self.current_match += 1

        # Show bracket transition before next match
        self.phase = "bracket_transition"
        self.phase_start_time = self.game_time

    def _advance_round(self):
        """Advance to next round of tournament"""
        # Clear temporary fighters list (bracket already updated in _advance_bracket)
        if hasattr(self, '_next_round_fighters'):
            self._next_round_fighters = []

        self.current_round += 1
        self.current_match = 0

        # Check if tournament is complete
        if self.current_round >= len(self.bracket):
            self._finish_tournament()
            return

        # Show bracket transition
        self.phase = "bracket_transition"
        self.phase_start_time = self.game_time

        round_name = self._get_round_name()
        matches_remaining = self._count_remaining_matches()
        print(f"\n=== {round_name} ===")
        print(f"{len(self.bracket[self.current_round])} fighters remaining")
        print(f"{matches_remaining} total matches left in tournament")

    def _get_round_name(self) -> str:
        """Get name of current round"""
        fighters_in_round = len(self.bracket[self.current_round]) if self.current_round < len(self.bracket) else 0

        if fighters_in_round == 2:
            return "Finals"
        elif fighters_in_round == 4:
            return "Semifinals"
        elif fighters_in_round == 8:
            return "Quarterfinals"
        elif fighters_in_round == 16:
            return "Round of 16"
        elif fighters_in_round == 32:
            return "Round of 32"
        else:
            return f"Round of {fighters_in_round}"

    def _get_round_intro_text(self) -> Tuple[str, str]:
        """Build round intro header and label text"""
        fighters_in_round = len(self.bracket[self.current_round]) if self.current_round < len(self.bracket) else 0

        if fighters_in_round == 16:
            round_label = "Top 16"
        elif fighters_in_round == 8:
            round_label = "Quarterfinals"
        elif fighters_in_round == 4:
            round_label = "Semifinals"
        elif fighters_in_round == 2:
            round_label = "Final"
        elif fighters_in_round > 0:
            round_label = f"Top {fighters_in_round}"
        else:
            round_label = "Tournament"

        month_name = datetime.now().strftime("%B")
        header = f"{month_name} Leaderboard"
        return header, round_label

    def _count_remaining_matches(self) -> int:
        """Count total matches remaining in tournament"""
        total = 0
        for round_idx in range(self.current_round, len(self.bracket)):
            fighters_in_round = len(self.bracket[round_idx])
            total += fighters_in_round // 2
        return total

    def _finish_tournament(self):
        """Tournament complete - show podium and calculate scores"""
        self.phase = "finished"
        self.phase_start_time = self.game_time

        # Get placements
        winner = self.bracket[-1][0]  # Last fighter standing
        runner_up = self.fighter2 if winner == self.fighter1 else self.fighter1
        semifinalists = self.bracket[-2][:2] if len(self.bracket) >= 2 else []

        print(f"\n=== TOURNAMENT COMPLETE ===")
        print(f"Champion: {winner.username}")
        print(f"Runner-up: {runner_up.username}")

        # Calculate and save statistics
        self._calculate_and_save_scores()

    def _calculate_and_save_scores(self):
        """Calculate final scores and save statistics"""
        # Assign placements based on bracket rounds
        # Finals winner = 1st
        # Finals loser = 2nd
        # Semifinals losers = 3rd/4th
        # Etc.

        placement = 1
        for round_idx in range(len(self.bracket) - 1, -1, -1):
            fighters_in_round = self.bracket[round_idx]

            for fighter in fighters_in_round:
                if not fighter.is_alive():
                    # Calculate points
                    points = self._calculate_placement_points(placement, len(self.all_fighters))

                    # Update statistics
                    self.statistics.update_player_stats(
                        username=fighter.username,
                        placement=placement,
                        points_earned=points,
                        survival_time=0,  # Not applicable for 1v1 tournament
                        total_participants=len(self.all_fighters),
                        damage_dealt=fighter.damage_dealt
                    )

                    placement += 1

        # Save statistics
        self.statistics.save_statistics()
        print("Statistics saved")

    def _calculate_placement_points(self, placement: int, total_fighters: int) -> int:
        """Calculate points based on placement"""
        # Points by placement
        points_map = {
            1: 200,  # Champion
            2: 150,  # Runner-up
            3: 100,  # Semifinals
            4: 100,
            5: 75,   # Quarterfinals
            6: 75,
            7: 75,
            8: 75,
        }

        if placement <= 8:
            return points_map.get(placement, 50)
        elif placement <= 16:
            return 50
        else:
            return 25

    def _render(self):
        """Render current frame"""
        # Clear screen
        self.screen.fill((14, 14, 18))

        if self.phase == "intro":
            self._render_intro()

        elif self.phase == "round_intro":
            self.renderer.render_round_intro(self.round_intro_header, self.round_intro_label)

        elif self.phase == "top16_overview":
            self.renderer.render_top16_overview(self.round_intro_header, self.top16_overview_entries)

        elif self.phase == "bracket_display":
            # Render tournament bracket overview
            if self.fighter1 and self.fighter2:
                self.renderer.render_tournament_bracket(
                    self.bracket,
                    self.current_round,
                    self.current_match,
                    (self.fighter1, self.fighter2),
                    getattr(self, 'tournament_type', 'TOURNAMENT'),
                    getattr(self, 'monthly_rankings', {})
                )

        elif self.phase in ("countdown", "fighting", "winner"):
            # Render match
            match_state = {
                "round_name": self._get_round_name(),
                "match_num": self.current_match + 1,
                "total_matches": len(self.bracket[self.current_round]) // 2 if self.current_round < len(self.bracket) else 1,
                "timer": getattr(config, 'ANIME_FIGHTING_MATCH_TIME_LIMIT', 60) - self.match_time,
                "is_finals": self.is_finals,
                "finals_wins": self.finals_wins.copy() if self.is_finals else None,
                "finals_game": self.finals_match_number + 1 if self.is_finals else None
            }

            # Draw arena background
            arena_bounds = self.arena.get_bounds()
            pygame.draw.rect(self.world_surface, (34, 34, 44), arena_bounds, border_radius=14)
            pygame.draw.rect(self.world_surface, (75, 75, 95), arena_bounds, 3, border_radius=14)

            # Render match world elements
            self.renderer.render_match(
                self.world_surface,
                self.fighter1,
                self.fighter2,
                self.hitshapes,
                self.projectiles,
                self.particles,
                self.afterimages,
                match_state
            )

            # Apply camera effects (zoom, shake)
            self.camera_fx.blit_world(self.screen, self.world_surface)

            # Screen flash overlay (for finisher hits and clashes)
            flash_intensity = self.camera_fx.get_flash_intensity()
            if flash_intensity > 0:
                draw_screen_flash(self.screen, flash_intensity, self.camera_fx.screen_flash_color)

            # Render UI on top
            self.renderer.render_ui(self.fighter1, self.fighter2, match_state)

            # Countdown overlay
            if self.phase == "countdown":
                elapsed = self.game_time - self.phase_start_time
                count = 3 - int(elapsed)
                if count >= 0:
                    self.renderer.render_countdown(count)

            # Winner overlay
            if self.phase == "winner":
                winner = self.fighter1 if self.fighter1.is_alive() else self.fighter2

                # Build finals info if in finals
                finals_info = None
                if self.is_finals:
                    # Check if series is over (someone has 2 wins after this game)
                    wins_after = self.finals_wins.copy()
                    if winner == self.fighter1:
                        wins_after[1] += 1
                    else:
                        wins_after[2] += 1
                    is_series_over = wins_after[1] >= 2 or wins_after[2] >= 2

                    finals_info = {
                        'wins': wins_after,
                        'game': self.finals_match_number + 1,
                        'is_series_over': is_series_over,
                        'fighter1_name': self.fighter1.username,
                        'fighter2_name': self.fighter2.username
                    }

                self.renderer.render_winner_announcement(winner, finals_info)

        elif self.phase == "bracket_transition":
            # Show updated bracket after winner advances
            # Highlight will show all remaining fighters (no specific matchup yet)
            self.renderer.render_tournament_bracket(
                self.bracket,
                self.current_round,
                self.current_match,
                None,  # No specific matchup highlighted during transition
                getattr(self, 'tournament_type', 'TOURNAMENT'),
                getattr(self, 'monthly_rankings', {})
            )

        elif self.phase == "finished":
            # Podium
            winner = self.bracket[-1][0]  # Champion

            # Runner-up is the other finalist
            finals_bracket = self.bracket[-2] if len(self.bracket) >= 2 else []
            runner_up = None
            for fighter in finals_bracket:
                if fighter != winner:
                    runner_up = fighter
                    break

            # 3rd/4th place are the semifinal losers (not in finals)
            semifinals_bracket = self.bracket[-3] if len(self.bracket) >= 3 else []
            semifinalists = [f for f in semifinals_bracket if f not in finals_bracket]

            self.renderer.render_podium(winner, runner_up, semifinalists)

        self.renderer.render_promo_overlay()
        pygame.display.flip()

    def _render_intro(self):
        """Render intro screen"""
        title = self.renderer.font_title.render("ANIME FIGHTING", True, (255, 215, 0))
        subtitle = self.renderer.font_medium.render("TOURNAMENT", True, (255, 255, 255))

        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 40))
        subtitle_rect = subtitle.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 20))

        self.screen.blit(title, title_rect)
        self.screen.blit(subtitle, subtitle_rect)

    def _cleanup(self):
        """Cleanup and save video"""
        if self.recorder:
            print("Exporting video...")
            self.recorder.export_video()
            print(f"Video saved to {self.recorder.output_path}")

        self.audio_logger.stop()

        pygame.quit()
