"""
Team Battle Game - Main Game Class
4-team battle with phased combat: semifinals -> finals -> free-for-all
"""

import pygame
import random
import math
import time
import csv
from datetime import datetime
from typing import List, Dict, Optional

import config
from shared import (
    InstagramAPI,
    PhysicsEngine,
    ParticleSystem,
    SoundManager,
    ScoringSystem,
    PlayerStatistics,
    GameHistory,
    VideoRecorder,
    AudioLogger,
    auto_push
)
from .team_fighter import TeamFighter, Team, TEAM_COLORS
from .team_arena import TeamArena
from .renderer import TeamBattleRenderer


class TeamBattleGame:
    """
    Team Battle Arena game mode.

    Phases:
    1. intro - Show day announcement, teams in quadrants
    2. countdown - 3-2-1 countdown
    3. semifinals - Red vs Blue (top), Green vs Yellow (bottom)
    4. semifinal_transition - Revive winning teams
    5. finals - Two remaining teams fight
    6. final_transition - Revive winning team
    7. freeforall - Winning team fights each other
    8. finished - Winner display

    Scoring:
    - 4th place team: 25 base points
    - 3rd place team: 50 base points
    - 2nd place team: 75 base points
    - 1st place team: 75-100 points based on individual placement
    - Bonus: +1 point per kill
    """

    # Team placement scores
    TEAM_PLACEMENT_SCORES = {
        4: 25,   # First team eliminated
        3: 50,   # Second team eliminated
        2: 75,   # Lost finals
        1: 75,   # Won finals (individual placement adds 0-25)
    }

    def __init__(self):
        """Initialize the game"""
        print("=" * 60)
        print("  TEAM BATTLE ARENA")
        print("=" * 60)

        # Initialize Pygame
        pygame.init()

        # Use HIDDEN flag if headless mode is enabled (no window, faster processing)
        display_flags = pygame.HIDDEN if config.HEADLESS_MODE else 0
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), display_flags)

        if not config.HEADLESS_MODE:
            pygame.display.set_caption("Team Battle Arena")

        self.clock = pygame.time.Clock()

        # Initialize game components
        print("\nInitializing Team Battle Arena...")
        self.api = InstagramAPI()
        self.arena = TeamArena()
        self.physics = PhysicsEngine()
        self.audio_logger = AudioLogger()
        self.recorder = VideoRecorder(
            audio_logger=self.audio_logger,
            countdown_audio_path='assets/smash_countdown_audio.wav'
        )
        self.recorder.set_greenscreen_overlay(
            video_path='assets/smash ultimate 3 2 1 go green screen.mp4',
            scale=1.0,  # 100% bigger (was 0.5, now 1.0)
            offset_y=0  # Centered vertically (was 120, now 0)
        )
        self.particles = ParticleSystem()
        self.sound = SoundManager(audio_logger=self.audio_logger)
        self.statistics = PlayerStatistics()
        self.game_history = GameHistory()
        self.scoring = ScoringSystem()

        # Use custom background music for team battle
        self.sound.background_music_path = "assets/Tour Sydney Sprint - Mario Kart 8 Deluxe OST.mp3"

        # Renderer initialized after we know arena
        self.renderer = TeamBattleRenderer(self.screen, self.arena)

        # Preload audio
        self.sound.preload_audio()

        # Game state
        self.fighters: List[TeamFighter] = []
        self.teams: Dict[Team, List[TeamFighter]] = {
            Team.RED: [],
            Team.BLUE: [],
            Team.GREEN: [],
            Team.YELLOW: [],
        }
        self.running = True
        self.game_over = False
        self.game_start_time = time.time()

        # Phase management
        # Phases: intro, matchup_announce, countdown, semifinals, semifinal_transition,
        #         finals_announce, finals_countdown, finals, final_transition,
        #         freeforall_announce, freeforall_countdown, freeforall, finished
        self.phase = "intro"
        self.phase_start_time = 0
        self.countdown_number = 3

        # Matchup announcement text
        self.matchup_text = ""
        self.matchup_text_2 = ""

        # Team elimination tracking
        self.eliminated_teams: List[Team] = []  # Order of elimination
        self.team_placements: Dict[Team, int] = {}  # Team -> placement (1-4)

        # Semifinal matchups - VERTICAL fights (top teams fight, bottom teams fight)
        # Red (top-left) vs Blue (top-right)
        # Green (bottom-left) vs Yellow (bottom-right)
        self.semifinal_matchups = [
            (Team.RED, Team.BLUE),      # Top row - fight horizontally
            (Team.GREEN, Team.YELLOW),  # Bottom row - fight horizontally
        ]
        self.semifinal_winners: List[Team] = []

        # Speed multiplier for team battle (slower movement)
        self.speed_multiplier = 0.7

        # Statistics
        self.total_eliminations = 0
        self.last_alive_count = 0

        # Dynamic scaling
        self.initial_total_players = 0
        self.last_fighter_radius = config.FOLLOWER_RADIUS

        # Leaderboard data
        self.current_game_leaderboard = []
        self.all_time_leaderboard = []

        # Winner tracking
        self.winner = None
        self.winning_team = None

        # HP logging
        self.hp_log_file = None
        self.hp_log_writer = None
        self.frame_number = 0

        # Performance optimization - update throttling for large player counts
        self.update_frame_counter = 0
        self.update_batches_per_frame = config.UPDATE_BATCHES_PER_FRAME

        print("Team Battle Arena initialized!\n")

    def setup_fighters(self):
        """Fetch followers and assign to teams"""
        print(f"Setting up fighters in 4 teams...")

        # Fetch followers (support test mode)
        if config.TEST_MINIMAL_PLAYERS:
            print(f"🧪 TEST MODE: Using {config.TEST_MINIMAL_PLAYER_COUNT} test players")
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        print(f"Setting up {len(follower_data)} fighters in 4 teams...")
        random.shuffle(follower_data)

        # Split into 4 equal groups
        team_list = list(Team)
        fighters_per_team = len(follower_data) // 4

        for i, data in enumerate(follower_data):
            # Assign to team based on index
            team_index = min(i // fighters_per_team, 3)
            team = team_list[team_index]

            # Get spawn position in team's quadrant
            position = self.arena.get_random_position_in_quadrant(team)

            # Create fighter
            fighter = TeamFighter(data, position, team)
            fighter.set_spawn_position(position[0], position[1])
            fighter.speed_multiplier = self.speed_multiplier  # Slower movement for team battle

            self.fighters.append(fighter)
            self.teams[team].append(fighter)

        # Randomize update order for fair combat
        random.shuffle(self.fighters)

        # Force all fighters to be strictly within their quadrants after initial placement
        # This handles any edge cases from random positioning
        for fighter in self.fighters:
            fighter.x, fighter.y = self.arena.clamp_to_quadrant(
                fighter.x, fighter.y, config.FOLLOWER_RADIUS + 5, fighter.team
            )
            # Update spawn position to clamped position
            fighter.set_spawn_position(fighter.x, fighter.y)
            fighter.death_x = fighter.x
            fighter.death_y = fighter.y

        # Store initial values for dynamic scaling
        self.initial_total_players = len(self.fighters)

        # Apply dynamic scaling
        if config.USE_DYNAMIC_SCALING:
            arena_rect = self.arena.get_rect()
            initial_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=self.initial_total_players,
                safe_zone_radius=min(arena_rect[2], arena_rect[3]) // 2,
                initial_zone_radius=min(arena_rect[2], arena_rect[3]) // 2
            )
            config.FOLLOWER_RADIUS = initial_radius
            config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
            config.FIGHTER_ATTACK_RANGE = config.FOLLOWER_RADIUS * 2.5
            self.last_fighter_radius = initial_radius

            for fighter in self.fighters:
                fighter.surface_needs_update = True

        # Print team sizes
        for team in Team:
            print(f"  {team.value.upper()}: {len(self.teams[team])} fighters")

        print(f"Total: {len(self.fighters)} fighters ready!\n")

        # Initialize HP logging CSV
        self._init_hp_logging()

    def _init_hp_logging(self):
        """Initialize CSV file for HP logging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"hp_log_{timestamp}.csv"

        self.hp_log_file = open(log_filename, 'w', newline='')
        self.hp_log_writer = csv.writer(self.hp_log_file)

        # Write header row
        header = ['frame', 'phase', 'time']
        for fighter in self.fighters:
            header.append(f"{fighter.username}_hp")
            header.append(f"{fighter.username}_alive")
            header.append(f"{fighter.username}_team")

        self.hp_log_writer.writerow(header)
        print(f"HP logging initialized: {log_filename}\n")

    def _log_hp_frame(self):
        """Log HP of fighters from non-eliminated teams only"""
        if not self.hp_log_writer:
            return

        row = [self.frame_number, self.phase, time.time() - self.game_start_time]

        for fighter in self.fighters:
            # Only log fighters from teams that haven't been eliminated
            if fighter.team not in self.eliminated_teams:
                row.append(f"{fighter.current_hp:.1f}")
                row.append(1 if fighter.alive else 0)
                row.append(fighter.team.value)

        self.hp_log_writer.writerow(row)
        self.frame_number += 1

    def get_alive_count_by_team(self) -> Dict[Team, int]:
        """Get count of alive fighters per team"""
        counts = {}
        for team in Team:
            counts[team] = sum(1 for f in self.teams[team] if f.alive)
        return counts

    def get_alive_teams(self) -> List[Team]:
        """Get list of teams with alive fighters"""
        counts = self.get_alive_count_by_team()
        return [team for team, count in counts.items() if count > 0]

    def check_semifinal_results(self) -> Optional[List[Team]]:
        """
        Check if semifinals are complete.
        Returns list of winning teams if both matchups decided, None otherwise.
        """
        winners = []

        for team_a, team_b in self.semifinal_matchups:
            alive_a = sum(1 for f in self.teams[team_a] if f.alive)
            alive_b = sum(1 for f in self.teams[team_b] if f.alive)

            if alive_a > 0 and alive_b == 0:
                winners.append(team_a)
                if team_b not in self.eliminated_teams:
                    self.eliminated_teams.append(team_b)
            elif alive_b > 0 and alive_a == 0:
                winners.append(team_b)
                if team_a not in self.eliminated_teams:
                    self.eliminated_teams.append(team_a)
            elif alive_a == 0 and alive_b == 0:
                # Both eliminated - this shouldn't happen, but handle it
                # Pick the one with more recent eliminations as winner
                winners.append(team_a)  # Arbitrary
                if team_b not in self.eliminated_teams:
                    self.eliminated_teams.append(team_b)
            else:
                # Match still ongoing
                return None

        return winners if len(winners) == 2 else None

    def revive_team(self, team: Team, at_death_position: bool = True):
        """
        Revive all fighters in a team

        Args:
            team: Team to revive
            at_death_position: If True, respawn at death location. If False, random position.
        """
        print(f"Reviving Team {team.value.upper()}...")
        revived_count = 0
        for fighter in self.teams[team]:
            if not fighter.alive:
                if at_death_position:
                    # Respawn at death position
                    position = (fighter.death_x, fighter.death_y)
                else:
                    # Get random position in team's original quadrant
                    position = self.arena.get_random_position_in_quadrant(team)
                fighter.respawn(position)
                revived_count += 1

                # Create revival particle effect
                self.particles.create_elimination_explosion(
                    fighter.x, fighter.y,
                    fighter.team_color
                )

        print(f"  {revived_count} fighters revived!")

    def _revive_team_spread_out(self, team: Team):
        """
        Revive team with fighters spread out evenly across entire arena.
        Used for free-for-all to give all fighters a fair starting position.

        Args:
            team: Team to revive
        """
        import random
        import math

        print(f"Reviving Team {team.value.upper()} for FREE-FOR-ALL...")

        # Get arena bounds
        arena_rect = self.arena.get_rect()
        arena_x, arena_y, arena_width, arena_height = arena_rect
        padding = config.FOLLOWER_RADIUS * 3  # Extra padding from edges

        # Get all fighters from the team
        team_fighters = self.teams[team]
        alive_fighters = [f for f in team_fighters if f.alive]
        dead_fighters = [f for f in team_fighters if not f.alive]
        total_fighters = len(team_fighters)

        # Calculate grid dimensions for even spacing
        grid_cols = int(math.ceil(math.sqrt(total_fighters)))
        grid_rows = int(math.ceil(total_fighters / grid_cols))

        # Calculate spacing between fighters
        available_width = arena_width - 2 * padding
        available_height = arena_height - 2 * padding
        spacing_x = available_width / (grid_cols + 1)
        spacing_y = available_height / (grid_rows + 1)

        # Assign positions to all fighters
        revived_count = 0
        all_fighters = alive_fighters + dead_fighters
        for i, fighter in enumerate(all_fighters):
            # Calculate grid position
            row = i // grid_cols
            col = i % grid_cols

            # Calculate base position
            base_x = arena_x + padding + spacing_x * (col + 1)
            base_y = arena_y + padding + spacing_y * (row + 1)

            # Add small random offset to avoid perfect grid
            offset_range = min(spacing_x, spacing_y) * 0.3
            offset_x = random.uniform(-offset_range, offset_range)
            offset_y = random.uniform(-offset_range, offset_range)

            position = (base_x + offset_x, base_y + offset_y)

            # Revive dead fighters or reposition alive fighters
            if not fighter.alive:
                fighter.respawn(position)
                revived_count += 1
            else:
                fighter.x, fighter.y = position

            # Create revival/repositioning particle effect
            self.particles.create_elimination_explosion(
                fighter.x, fighter.y,
                fighter.team_color
            )

        print(f"  {revived_count} fighters revived and {len(alive_fighters)} repositioned for fair free-for-all!")

    def reset_hp_for_alive_fighters(self, teams: List[Team] = None):
        """
        Reset HP to full for all alive fighters in specified teams.

        Args:
            teams: List of teams to reset HP for. If None, resets all teams.
        """
        if teams is None:
            teams = list(Team)

        for team in teams:
            for fighter in self.teams[team]:
                if fighter.alive:
                    fighter.current_hp = fighter.max_hp

    def set_targeting_enabled(self, enabled: bool, teams: List[Team] = None):
        """
        Enable or disable targeting for fighters.

        Args:
            enabled: Whether targeting should be enabled
            teams: List of teams to update. If None, updates all fighters.
        """
        if teams is None:
            fighters_to_update = self.fighters
        else:
            fighters_to_update = []
            for team in teams:
                fighters_to_update.extend(self.teams[team])

        for fighter in fighters_to_update:
            fighter.targeting_enabled = enabled
            if not enabled:
                fighter.target_follower = None

    def update(self, dt: float):
        """Update game state"""
        if self.game_over:
            return

        # Performance profiling
        prof_start = time.time()
        current_time = time.time()
        arena_rect = self.arena.get_rect()

        # Update arena (for wall animations)
        self.arena.update(dt)

        # Handle matchup announcement phase
        if self.phase == "matchup_announce":
            elapsed = self.game_time - self.phase_start_time
            if elapsed >= 2.0:  # Show matchup for 2 seconds
                self.phase = "countdown"
                self.phase_start_time = self.game_time
                self.renderer.start_countdown_video()
                self.sound.play_countdown_audio()

        # Handle countdown phase
        elif self.phase == "countdown":
            elapsed = self.game_time - self.phase_start_time
            countdown_duration = self.sound.countdown_audio_duration

            # Scale countdown duration when exporting video with time scaling
            if config.EXPORT_VIDEO:
                countdown_duration *= config.EXPORT_TIME_SCALE

            if elapsed >= countdown_duration:
                print("FIGHT!")
                self.phase = "semifinals"
                # Open VERTICAL wall for horizontal fights (Red vs Blue, Green vs Yellow)
                self.arena.vertical_wall_closed = False  # Start animation
                self.sound.set_music_volume_high()

                # Set opponent teams for targeting: Red vs Blue, Green vs Yellow
                for fighter in self.teams[Team.RED]:
                    fighter.current_opponent_team = Team.BLUE
                for fighter in self.teams[Team.BLUE]:
                    fighter.current_opponent_team = Team.RED
                for fighter in self.teams[Team.GREEN]:
                    fighter.current_opponent_team = Team.YELLOW
                for fighter in self.teams[Team.YELLOW]:
                    fighter.current_opponent_team = Team.GREEN

                # Enable targeting for all fighters
                self.set_targeting_enabled(True)

                print("\nSEMIFINALS: Red vs Blue, Green vs Yellow!\n")
            else:
                self.countdown_number = max(0, 3 - int(elapsed))

        # Handle finals announcement phase
        elif self.phase == "finals_announce":
            elapsed = self.game_time - self.phase_start_time
            if elapsed >= 2.0:
                self.phase = "finals_countdown"
                self.phase_start_time = self.game_time
                self.renderer.start_countdown_video()
                self.sound.play_countdown_audio()
                # Disable targeting during countdown
                self.set_targeting_enabled(False, self.semifinal_winners)

        # Handle finals countdown
        elif self.phase == "finals_countdown":
            elapsed = self.game_time - self.phase_start_time
            countdown_duration = self.sound.countdown_audio_duration

            # Scale countdown duration when exporting video with time scaling
            if config.EXPORT_VIDEO:
                countdown_duration *= config.EXPORT_TIME_SCALE

            if elapsed >= countdown_duration:
                print("FIGHT!")
                self.phase = "finals"
                # Open HORIZONTAL wall for vertical fights
                self.arena.horizontal_wall_closed = False  # Start animation
                self.sound.set_music_volume_high()
                # Reset HP for alive fighters and enable targeting
                self.reset_hp_for_alive_fighters(self.semifinal_winners)
                self.set_targeting_enabled(True, self.semifinal_winners)
            else:
                self.countdown_number = max(0, 3 - int(elapsed))

        # Handle freeforall announcement phase
        elif self.phase == "freeforall_announce":
            elapsed = self.game_time - self.phase_start_time
            if elapsed >= 2.0:
                self.phase = "freeforall_countdown"
                self.phase_start_time = self.game_time
                self.renderer.start_countdown_video()
                self.sound.play_countdown_audio()
                # Disable targeting during countdown
                self.set_targeting_enabled(False, [self.winning_team])

        # Handle freeforall countdown
        elif self.phase == "freeforall_countdown":
            elapsed = self.game_time - self.phase_start_time
            countdown_duration = self.sound.countdown_audio_duration

            # Scale countdown duration when exporting video with time scaling
            if config.EXPORT_VIDEO:
                countdown_duration *= config.EXPORT_TIME_SCALE

            if elapsed >= countdown_duration:
                print("FIGHT!")
                self.phase = "freeforall"
                self.sound.set_music_volume_high()
                # Reset HP for alive fighters and enable targeting
                self.reset_hp_for_alive_fighters([self.winning_team])
                self.set_targeting_enabled(True, [self.winning_team])
            else:
                self.countdown_number = max(0, 3 - int(elapsed))

        # Determine if combat is enabled
        combat_enabled = self.phase in ("semifinals", "finals", "freeforall")

        # Performance optimization: Update throttling for large player counts
        total_fighters = len(self.fighters)
        if config.ENABLE_UPDATE_THROTTLING and total_fighters > 5000:
            # Increment frame counter
            self.update_frame_counter += 1

            # Calculate which batch to update this frame
            batch_index = self.update_frame_counter % self.update_batches_per_frame
            batch_size = (total_fighters + self.update_batches_per_frame - 1) // self.update_batches_per_frame

            # Calculate start and end indices for this batch
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, total_fighters)

            fighters_to_update = self.fighters[start_idx:end_idx]
        else:
            # For smaller player counts or if throttling disabled, update all fighters every frame
            fighters_to_update = self.fighters

        # Update fighters
        for fighter in fighters_to_update:
            prev_x, prev_y = fighter.x, fighter.y

            # Use fighter update
            fighter.update_fighter(dt, arena_rect, self.fighters, current_time, combat_enabled)

            # Apply wall collision constraints
            fighter.x, fighter.y = self.arena.clamp_position_with_walls(
                fighter.x, fighter.y, config.FOLLOWER_RADIUS, prev_x, prev_y
            )

            # Bounce off walls
            if abs(fighter.x - prev_x) < 0.01 and abs(fighter.vx) > 0.1:
                fighter.vx *= -0.5
                fighter.push_vx *= -0.5
            if abs(fighter.y - prev_y) < 0.01 and abs(fighter.vy) > 0.1:
                fighter.vy *= -0.5
                fighter.push_vy *= -0.5

        # Physics - handle collision knockback and resolve overlaps
        prof_physics_start = time.time()
        self.physics.update(self.fighters, dt)  # Enabled: knockback from collisions
        prof_physics_time = (time.time() - prof_physics_start) * 1000

        # DISABLED: resolve_overlaps is O(n²) and too slow for large counts
        # self.physics.resolve_overlaps(self.fighters)

        # Re-apply wall/quadrant clamping after physics resolution
        # This prevents fighters from being pushed through walls
        # OPTIMIZED: Only clamp fighters that were updated this frame
        prof_clamp_start = time.time()
        for fighter in fighters_to_update:
            if not fighter.alive:
                continue

            # Get arena bounds
            left, top, right, bottom = self.arena.get_bounds()
            radius = config.FOLLOWER_RADIUS

            # Always clamp to arena bounds
            fighter.x = max(left + radius, min(right - radius, fighter.x))
            fighter.y = max(top + radius, min(bottom - radius, fighter.y))

            # If both walls are closed, clamp to quadrant
            if self.arena.horizontal_wall_closed and self.arena.vertical_wall_closed:
                fighter.x, fighter.y = self.arena.clamp_to_quadrant(
                    fighter.x, fighter.y, config.FOLLOWER_RADIUS, fighter.team
                )
            else:
                # Apply specific wall constraints based on which walls are still closed
                wall_margin = self.arena.wall_thickness // 2 + radius

                # Horizontal wall still closed - keep fighters on their side (top/bottom)
                if self.arena.horizontal_wall_closed:
                    is_top_team = fighter.team in (Team.RED, Team.BLUE)
                    if is_top_team:
                        # Top teams stay above horizontal wall
                        fighter.y = min(fighter.y, self.arena.center_y - wall_margin)
                    else:
                        # Bottom teams stay below horizontal wall
                        fighter.y = max(fighter.y, self.arena.center_y + wall_margin)

                # Vertical wall still closed - keep fighters on their side (left/right)
                if self.arena.vertical_wall_closed:
                    is_left_team = fighter.team in (Team.RED, Team.GREEN)
                    if is_left_team:
                        # Left teams stay left of vertical wall
                        fighter.x = min(fighter.x, self.arena.center_x - wall_margin)
                    else:
                        # Right teams stay right of vertical wall
                        fighter.x = max(fighter.x, self.arena.center_x + wall_margin)

        # Particles
        self.particles.update(dt)

        # Music
        self.sound.update_music_volume()

        # Phase-specific logic
        if self.phase == "semifinals":
            self._update_semifinals()
        elif self.phase == "semifinal_transition":
            self._update_semifinal_transition()
        elif self.phase == "finals":
            self._update_finals()
        elif self.phase == "final_transition":
            self._update_final_transition()
        elif self.phase == "freeforall":
            self._update_freeforall()

        # Update dynamic radius
        if combat_enabled and config.USE_DYNAMIC_SCALING:
            alive_count = sum(1 for f in self.fighters if f.alive)
            new_radius = config.calculate_dynamic_follower_radius(
                total_players=self.initial_total_players,
                alive_count=alive_count,
                safe_zone_radius=min(arena_rect[2], arena_rect[3]) // 2,
                initial_zone_radius=min(arena_rect[2], arena_rect[3]) // 2
            )

            if abs(new_radius - self.last_fighter_radius) > 0.5:
                for fighter in self.fighters:
                    fighter.surface_needs_update = True
                self.last_fighter_radius = new_radius

            config.FOLLOWER_RADIUS = new_radius
            config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2
            config.FIGHTER_ATTACK_RANGE = config.FOLLOWER_RADIUS * 2.5

        # Print elimination updates
        alive_count = sum(1 for f in self.fighters if f.alive)
        if alive_count != self.last_alive_count:
            eliminated = self.last_alive_count - alive_count
            if eliminated > 0:
                self.total_eliminations += eliminated
                team_counts = self.get_alive_count_by_team()
                print(f"{eliminated} eliminated - R:{team_counts[Team.RED]} B:{team_counts[Team.BLUE]} G:{team_counts[Team.GREEN]} Y:{team_counts[Team.YELLOW]}")
            self.last_alive_count = alive_count

    def _update_semifinals(self):
        """Update semifinal phase"""
        winners = self.check_semifinal_results()
        if winners:
            self.semifinal_winners = winners
            print(f"\nSEMIFINALS COMPLETE!")
            print(f"Winners: {[w.value.upper() for w in winners]}")
            print(f"Eliminated: {[e.value.upper() for e in self.eliminated_teams]}")

            # Assign placements to eliminated teams (they're 3rd and 4th)
            for i, team in enumerate(self.eliminated_teams):
                self.team_placements[team] = 4 - i  # First eliminated = 4th, second = 3rd

            # Disable targeting during transition
            self.set_targeting_enabled(False)

            # Start transition
            self.phase = "semifinal_transition"
            self.phase_start_time = self.game_time

    def eliminate_team(self, team: Team):
        """Eliminate all remaining alive fighters from a team"""
        current_time = time.time()
        eliminated_count = 0
        for fighter in self.teams[team]:
            if fighter.alive:
                fighter.alive = False
                fighter.alpha = 0  # Instantly hide them
                fighter.elimination_time = current_time  # Set proper elimination time
                eliminated_count += 1
        if eliminated_count > 0:
            print(f"  Eliminated {eliminated_count} stragglers from {team.value}")

    def _update_semifinal_transition(self):
        """Handle transition between semifinals and finals"""
        elapsed = self.game_time - self.phase_start_time

        # Brief pause, then revive winners
        if elapsed >= 1.0:
            # First, eliminate any remaining fighters from losing teams
            for team in self.eliminated_teams:
                self.eliminate_team(team)

            # Revive winning teams at their death positions
            for team in self.semifinal_winners:
                self.revive_team(team, at_death_position=True)

            # Reset HP to full for surviving fighters (revived fighters already have full HP)
            self.reset_hp_for_alive_fighters(self.semifinal_winners)

            # Disable targeting during announcement/countdown
            self.set_targeting_enabled(False, self.semifinal_winners)

            # Update alive count
            self.last_alive_count = sum(1 for f in self.fighters if f.alive)

            # Set up finals announcement
            team_a = self.semifinal_winners[0]
            team_b = self.semifinal_winners[1]
            self.matchup_text = f"{team_a.value.upper()} vs {team_b.value.upper()}"
            self.matchup_text_2 = ""

            # Set opponent teams for finals: the two semifinal winners fight each other
            for fighter in self.teams[team_a]:
                fighter.current_opponent_team = team_b
                fighter.target_follower = None  # Reset targeting
            for fighter in self.teams[team_b]:
                fighter.current_opponent_team = team_a
                fighter.target_follower = None  # Reset targeting

            self.phase = "finals_announce"
            self.phase_start_time = self.game_time
            print(f"\nFINALS: {team_a.value.upper()} vs {team_b.value.upper()}!\n")

    def _update_finals(self):
        """Update finals phase"""
        alive_teams = self.get_alive_teams()

        if len(alive_teams) <= 1:
            if alive_teams:
                self.winning_team = alive_teams[0]
                loser = [t for t in self.semifinal_winners if t != self.winning_team][0]
                self.eliminated_teams.append(loser)
                self.team_placements[loser] = 2  # Finals loser = 2nd place
                self.team_placements[self.winning_team] = 1  # Winner = 1st place

                print(f"\nFINALS COMPLETE!")
                print(f"WINNING TEAM: {self.winning_team.value.upper()}!")

                # Disable targeting during transition
                self.set_targeting_enabled(False)

                # Start final transition
                self.phase = "final_transition"
                self.phase_start_time = self.game_time
            else:
                # No one alive - shouldn't happen
                self._end_game()

    def _update_final_transition(self):
        """Handle transition to free-for-all"""
        elapsed = self.game_time - self.phase_start_time

        if elapsed >= 1.0:
            # Eliminate any remaining fighters from losing teams (including finals loser)
            for team in Team:
                if team != self.winning_team:
                    self.eliminate_team(team)

            # Revive winning team for free-for-all spread across entire arena
            self._revive_team_spread_out(self.winning_team)

            # Reset HP to full for surviving fighters (revived fighters already have full HP)
            self.reset_hp_for_alive_fighters([self.winning_team])

            # Disable targeting during announcement/countdown
            self.set_targeting_enabled(False, [self.winning_team])

            # Enable free-for-all mode on all fighters of the winning team
            # This allows them to target and attack their own teammates when combat resumes
            for fighter in self.teams[self.winning_team]:
                fighter.freeforall_mode = True
                fighter.target_follower = None  # Reset target to find new one

            # Update alive count
            self.last_alive_count = sum(1 for f in self.fighters if f.alive)

            # Set up freeforall announcement
            self.matchup_text = "LAST MAN STANDING"
            self.matchup_text_2 = ""

            self.phase = "freeforall_announce"
            self.phase_start_time = self.game_time
            print(f"\nFREE-FOR-ALL: Team {self.winning_team.value.upper()} fights for individual glory!\n")

    def _update_freeforall(self):
        """Update free-for-all phase"""
        alive_fighters = [f for f in self.fighters if f.alive]

        if len(alive_fighters) <= 1:
            if alive_fighters:
                self.winner = alive_fighters[0]
            self._end_game()

    def _end_game(self):
        """Handle game over"""
        self.game_over = True
        self.phase = "finished"
        self.sound.play_winner_celebration()
        self._calculate_and_save_scores()

        print("\n" + "=" * 60)
        print("  GAME OVER")
        print("=" * 60)
        if self.winner:
            print(f"WINNER: {self.winner.username} (Team {self.winner.team.value.upper()})")
            print(f"Kills: {self.winner.kills}")
        print("=" * 60)

    def _calculate_and_save_scores(self):
        """Calculate scores based on team placement and individual performance"""
        print("\nCalculating scores...")

        # Ensure all teams have placements
        for team in Team:
            if team not in self.team_placements:
                # Shouldn't happen, but default to worst
                self.team_placements[team] = 4

        total_participants = len(self.fighters)

        # Game metadata
        game_type = "team_battle"
        game_display_name = "Team Battle"
        day_number = getattr(config, 'DAY_NUMBER', 1)

        game_results = []  # For current game leaderboard display
        game_history_results = []

        # Get fighters from winning team (free-for-all survivors) sorted by survival
        winning_team_fighters = sorted(
            self.teams[self.winning_team] if self.winning_team else [],
            key=lambda f: (not f.alive, -f.get_survival_time()),
            reverse=False
        )

        # Calculate scores for each fighter
        for fighter in self.fighters:
            team_placement = self.team_placements.get(fighter.team, 4)

            # Base points based on team placement
            # 4th place team (eliminated first): 2500 points
            # 3rd place team (eliminated second): 5000 points
            # 2nd place team (eliminated third): 7500 points
            # 1st place team (free-for-all winners): 7500-10000 points based on individual placement
            if team_placement == 4:
                base_points = 2500.0
            elif team_placement == 3:
                base_points = 5000.0
            elif team_placement == 2:
                base_points = 7500.0
            else:  # team_placement == 1 (winning team / free-for-all)
                if winning_team_fighters:
                    try:
                        # Find this fighter's rank in the winning team
                        individual_rank = winning_team_fighters.index(fighter)
                        team_size = len(winning_team_fighters)

                        # Calculate percentile: how many players they beat
                        # If rank 0 (1st place), they beat everyone: (team_size - 1) / (team_size - 1) = 1.0
                        # If last place, they beat no one: 0 / (team_size - 1) = 0.0
                        if team_size > 1:
                            percentile = (team_size - 1 - individual_rank) / (team_size - 1)
                        else:
                            percentile = 1.0

                        # Points: 7500 + (2500 * percentile)
                        # 1st place: 7500 + 2500 = 10000
                        # Last place: 7500 + 0 = 7500
                        base_points = 7500.0 + (2500.0 * percentile)
                    except ValueError:
                        base_points = 7500.0  # Fallback
                else:
                    base_points = 7500.0  # Fallback if no winning team

            # Kill bonus: 100 points per kill
            kill_bonus = fighter.kills * 100

            # Total points
            total_points = round(base_points + kill_bonus, 1)

            # Determine overall placement for stats
            # Team placement determines bulk placement, then individual within team
            team_base_placement = sum(
                len(self.teams[t]) for t in Team
                if self.team_placements.get(t, 4) < team_placement
            )

            fighters_in_team = self.teams[fighter.team]
            sorted_team = sorted(
                fighters_in_team,
                key=lambda f: (not f.alive, -f.get_survival_time())
            )
            try:
                in_team_rank = sorted_team.index(fighter)
            except ValueError:
                in_team_rank = len(sorted_team)

            overall_placement = team_base_placement + in_team_rank + 1

            # Get survival time
            survival_time = fighter.get_survival_time()
            games_played = self.statistics.get_games_played(fighter.username)

            # Add to game results for leaderboard display
            game_results.append((
                fighter.username,
                overall_placement,
                total_points,
                survival_time
            ))

            # Update statistics
            self.statistics.update_player_stats(
                username=fighter.username,
                placement=overall_placement,
                points_earned=total_points,
                survival_time=survival_time,
                total_participants=total_participants,
                kills=fighter.kills,
                damage_dealt=fighter.damage_dealt,
                game_type=game_type,
                game_id=""  # Will be set after game_history.record_game_session
            )

            # Store for game history
            game_history_results.append({
                "username": fighter.username,
                "placement": overall_placement,
                "points": total_points,
                "survival_time": survival_time,
                "kills": fighter.kills,
                "damage": fighter.damage_dealt
            })

        # Record complete game session to history
        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results
        )

        # Save and display
        self.statistics.save_statistics()

        # Auto-push to GitHub (if not in test mode)
        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []  # All-time leaderboard display removed

        print(self.scoring.format_leaderboard(
            self.current_game_leaderboard,
            top_n=10,
            title="CURRENT GAME - TOP 10"
        ))

    def render(self):
        """Render current game state"""
        game_state = {
            "game_over": self.game_over,
            "phase": self.phase,
            "countdown_number": self.countdown_number,
            "day_number": getattr(config, 'DAY_NUMBER', 1),
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "all_followers": self.fighters,
            "team_counts": self.get_alive_count_by_team(),
            "eliminated_teams": self.eliminated_teams,
            "winning_team": self.winning_team,
            "winner": self.winner,
            "matchup_text": self.matchup_text,
            "matchup_text_2": self.matchup_text_2,
            "semifinal_winners": self.semifinal_winners,
        }

        self.renderer.render_frame(self.fighters, self.arena, game_state, self.particles)

        # Record frame
        recording_phases = ("intro", "matchup_announce", "countdown", "semifinals", "semifinal_transition",
                           "finals_announce", "finals_countdown", "finals", "final_transition",
                           "freeforall_announce", "freeforall_countdown", "freeforall", "finished")
        if self.phase in recording_phases:
            # Initialize recording start time on first recording frame
            if self.recording_start_time is None:
                self.recording_start_time = self.game_time

            # Pass recording time (time since recording started) to capture_frame
            recording_time = self.game_time - self.recording_start_time
            self.recorder.capture_frame(self.screen, current_time=recording_time)

            # Debug: Track finished phase frames
            if self.phase == "finished":
                if not hasattr(self, 'finished_frames'):
                    self.finished_frames = 0
                    self.first_finished_frame_time = self.game_time
                    print(f"DEBUG: First 'finished' frame at game_time = {self.game_time:.3f}s")
                self.finished_frames += 1

        pygame.display.flip()

    def run(self):
        """Main game loop"""
        # Setup
        self.setup_fighters()
        self.last_alive_count = len(self.fighters)

        # Start audio logging
        self.audio_logger.start()

        # Start background music
        self.sound.start_background_music()

        # Track game time for consistent video recording
        self.game_time = 0.0
        self.recording_start_time = None  # Will be set when recording starts

        # Performance monitoring
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.last_fps_print = time.time()

        # Intro sequence
        print("Starting intro sequence...\n")
        self.phase = "intro"

        # No intro audio for team battle - just show the intro screen
        # Display intro for a fixed duration
        intro_start = time.time()
        intro_duration = 3.0  # 3 seconds of intro

        while time.time() - intro_start < intro_duration:
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

            self.game_time += dt  # Track game time during intro

            # Update fighters during intro (no combat)
            arena_rect = self.arena.get_rect()
            current_time = time.time()
            for fighter in self.fighters:
                prev_x, prev_y = fighter.x, fighter.y
                fighter.update_fighter(dt, arena_rect, self.fighters, current_time, combat_enabled=False)
                fighter.x, fighter.y = self.arena.clamp_position_with_walls(
                    fighter.x, fighter.y, config.FOLLOWER_RADIUS, prev_x, prev_y
                )

            # Physics - handle collision knockback and resolve overlaps
            self.physics.update(self.fighters, dt)  # Enabled: knockback from collisions
            self.physics.resolve_overlaps(self.fighters)

            # Re-apply wall clamping after physics (fighters can be pushed through walls)
            for fighter in self.fighters:
                fighter.x, fighter.y = self.arena.clamp_to_quadrant(
                    fighter.x, fighter.y, config.FOLLOWER_RADIUS, fighter.team
                )
            self.particles.update(dt)
            self.sound.update_music_volume()
            self.render()

        # Start matchup announcement (before countdown)
        print("\nAnnouncing matchups...")
        self.phase = "matchup_announce"
        self.phase_start_time = self.game_time

        # Set matchup text for semifinals
        team_a, team_b = self.semifinal_matchups[0]
        team_c, team_d = self.semifinal_matchups[1]
        self.matchup_text = f"{team_a.value.upper()} vs {team_b.value.upper()}"
        self.matchup_text_2 = f"{team_c.value.upper()} vs {team_d.value.upper()}"

        # Track podium display time
        game_over_start_time = None

        # Main loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Use lower FPS during video export for better performance
            target_fps = config.SIMULATION_FPS_DURING_EXPORT if config.EXPORT_VIDEO else config.FPS
            dt = self.clock.tick(target_fps) / 1000.0

            # Cap delta time to prevent huge jumps when system lags
            dt = min(dt, config.MAX_DELTA_TIME)

            # Apply time scaling during video export to slow down simulation
            if config.EXPORT_VIDEO:
                dt *= config.EXPORT_TIME_SCALE

            # Update game time for consistent video recording
            self.game_time += dt

            self.update(dt)
            self._log_hp_frame()  # Log HP after each update
            self.render()

            # Performance monitoring - print FPS every 3 seconds
            self.frame_count += 1
            if time.time() - self.last_fps_print >= 3.0:
                elapsed = time.time() - self.fps_start_time
                current_fps = self.frame_count / elapsed if elapsed > 0 else 0
                alive_count = sum(1 for f in self.fighters if f.alive)
                print(f"[PERF] FPS: {current_fps:.1f} | Alive: {alive_count:,} | Phase: {self.phase}")
                self.last_fps_print = time.time()

            if self.game_over and game_over_start_time is None:
                game_over_start_time = self.game_time
                print(f"DEBUG: game_over_start_time set to {game_over_start_time:.3f}s")

            if self.game_over and game_over_start_time:
                # Outro should always be 5.27 seconds in the final video
                # Since game_time advances slower with time scaling, we need to scale the duration
                # to ensure we capture exactly 5.27 seconds worth of video frames
                if config.EXPORT_VIDEO:
                    # Calculate how much game_time needs to pass to capture 5.27 seconds of video
                    # We need to capture exactly 5.27 * FPS frames
                    target_frames = 5.27 * config.VIDEO_FPS  # ~158 frames
                    # Each frame advances game_time by: (1/SIMULATION_FPS) * EXPORT_TIME_SCALE
                    game_time_per_frame = (1.0 / config.SIMULATION_FPS_DURING_EXPORT) * config.EXPORT_TIME_SCALE
                    # Total game time needed
                    outro_duration = target_frames * game_time_per_frame
                    print(f"DEBUG: Outro target = {outro_duration:.3f}s game time (for 5.27s video, {target_frames:.0f} frames)")
                else:
                    outro_duration = 5.27  # Regular game time

                outro_elapsed = self.game_time - game_over_start_time
                print(f"DEBUG: Outro elapsed = {outro_elapsed:.3f}s / {outro_duration:.3f}s")

                if outro_elapsed > outro_duration:
                    finished_frames = getattr(self, 'finished_frames', 0)
                    first_frame_time = getattr(self, 'first_finished_frame_time', 0)
                    print(f"\nDEBUG: Captured {finished_frames} frames during 'finished' phase")
                    print(f"DEBUG: Expected ~{5.27 * 30:.0f} frames for 5.27s video")
                    print(f"DEBUG: First finished frame at {first_frame_time:.3f}s, timer started at {game_over_start_time:.3f}s")
                    print(f"DEBUG: Time difference = {game_over_start_time - first_frame_time:.3f}s ({(game_over_start_time - first_frame_time) / 0.00833:.1f} frames)")
                    print("\nGame complete!")
                    self.running = False

        self.cleanup()

    def cleanup(self):
        """Clean up and export video"""
        self.audio_logger.stop()

        # Close HP log file
        if self.hp_log_file:
            self.hp_log_file.close()
            print("HP log saved successfully")

        print("\n" + "=" * 60)
        print("  GAME STATISTICS")
        print("=" * 60)
        print(f"Total Fighters: {len(self.fighters)}")
        print(f"Total Eliminations: {self.total_eliminations}")
        print(f"Video Frames Captured: {self.recorder.get_frame_count()}")
        print(f"Video Duration: {self.recorder.get_video_duration():.1f}s")
        print("=" * 60)

        if config.EXPORT_VIDEO:
            self.recorder.export_video()

        self.sound.cleanup()
        pygame.quit()
        print("\nThanks for playing!")
