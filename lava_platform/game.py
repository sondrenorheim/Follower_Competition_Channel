"""
Lava Platform Game - Survive by reaching the safe platform before lava fills the arena.
"""

import math
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import pygame

import config
import shared.api as shared_api
from shared import GameTemplate, GameHistory, auto_push

from .arena import LavaPlatformArena
from .player import LavaPlatformPlayer
from .renderer import LavaPlatformRenderer


class LavaPlatformGame(GameTemplate):
    """Lava Platform game controller with shrinking platforms and decreasing time."""

    GAME_TITLE = "LAVA ESCAPE"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()

        self.initial_platform_radius = getattr(config, "LAVA_PLATFORM_INITIAL_RADIUS", 120)
        self.platform_shrink_per_round = getattr(config, "LAVA_PLATFORM_SHRINK_RATE", 15)
        self.min_platform_radius = getattr(config, "LAVA_PLATFORM_MIN_RADIUS", 40)

        self.initial_scramble_time = getattr(config, "LAVA_PLATFORM_INITIAL_TIME", 8.0)
        self.time_decrease_per_round = getattr(config, "LAVA_PLATFORM_TIME_DECREASE", 0.5)
        self.min_scramble_time = getattr(config, "LAVA_PLATFORM_MIN_TIME", 3.0)

        self.target_finalists = getattr(config, "LAVA_PLATFORM_TARGET_FINALISTS", 1)
        self.max_rounds = getattr(config, "LAVA_PLATFORM_MAX_ROUNDS", 10)

        self.waiting_duration = getattr(config, "LAVA_PLATFORM_WAITING_DURATION", 2.0)
        self.lava_duration = getattr(config, "LAVA_PLATFORM_LAVA_DURATION", 2.0)
        self.resolve_duration = getattr(config, "LAVA_PLATFORM_RESOLVE_DURATION", 1.5)

        self.max_active_players = getattr(config, "LAVA_PLATFORM_MAX_ACTIVE_PLAYERS", 200)
        self.round_parts = []
        self.round_part_index = 0
        self.active_players = None
        self.pending_part_advance = False

        self.round_index = 0
        self.round_phase = "waiting"
        self.phase_time_left = 0.0
        self.current_platform_radius = self.initial_platform_radius
        self.current_scramble_time = self.initial_scramble_time
        self.round_started = False
        self.last_eliminated = 0

        self.game_history = GameHistory()

    def _init_game_components(self):
        """Initialize arena and renderer."""
        self.arena = LavaPlatformArena()
        self.renderer = LavaPlatformRenderer(self.screen)

    def setup_players(self):
        """Import Discord followers and spawn players."""
        self._refresh_discord_followers()
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        # Use fixed player radius for lava platform
        fixed_radius = getattr(config, "LAVA_PLATFORM_PLAYER_RADIUS", 13)
        config.FOLLOWER_RADIUS = fixed_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

        for i, data in enumerate(follower_data):
            position = self._get_starting_position(i, len(follower_data))
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]
            player = self._create_player(payload, position)
            self.players.append(player)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    def _refresh_discord_followers(self):
        """Refresh follower list from Discord (same pattern as mingle)."""
        if config.TEST_MINIMAL_PLAYERS:
            return

        repo_root = Path(__file__).resolve().parents[1]
        overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
        output_file = getattr(config, "FOLLOWER_IMPORT_FILE", "") or ""
        if isinstance(overrides, dict):
            output_file = overrides.get("lava_platform", output_file) or output_file
        if not output_file:
            output_file = "Followers/discord_followers.json"

        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = repo_root / output_path

        self.api.import_file = str(output_path)

        export_script = Path("discord_members_export.py")
        if not export_script.is_absolute():
            export_script = repo_root / export_script
        if not export_script.exists():
            print(f"Discord export script not found: {export_script}")
            return

        guild_file = Path("guild.txt")
        if not guild_file.is_absolute():
            guild_file = repo_root / guild_file

        token_file = Path("discord_bot_token.txt")
        if not token_file.is_absolute():
            token_file = repo_root / token_file

        try:
            shared_api.clear_prefetched_followers()
        except Exception:
            pass

        command = [
            sys.executable,
            str(export_script),
            "--guild-id-file",
            str(guild_file),
            "--out",
            str(output_path),
            "--token-file",
            str(token_file),
            "--use-nick",
        ]

        print("Refreshing Discord followers for Lava Platform...")
        result = subprocess.run(command)
        if result.returncode != 0:
            if output_path.exists():
                print(
                    f"Discord export failed (exit code {result.returncode}); "
                    f"using existing file: {output_path}"
                )
            else:
                print(
                    f"Discord export failed (exit code {result.returncode}); "
                    f"no existing file found."
                )
        else:
            print(f"Discord followers updated: {output_path}")

    def _create_player(self, follower_data: dict, position: tuple) -> LavaPlatformPlayer:
        """Create a LavaPlatformPlayer instance."""
        return LavaPlatformPlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        """Get random starting position within arena."""
        center_x, center_y = self.arena.get_center()
        margin = config.FOLLOWER_RADIUS + 5

        x = random.uniform(self.arena.left + margin, self.arena.right - margin)
        y = random.uniform(self.arena.top + margin, self.arena.bottom - margin)

        return (x, y)

    def _build_round_parts(self, players: List[LavaPlatformPlayer]) -> List[List[LavaPlatformPlayer]]:
        """Split players into round parts so each part fits in the arena."""
        total = len(players)
        if total == 0:
            return []

        max_active = max(1, int(self.max_active_players))
        if total <= max_active:
            return [players]

        part_count = int(math.ceil(total / max_active))
        per_part = int(math.ceil(total / part_count))

        shuffled = list(players)
        random.shuffle(shuffled)

        return [shuffled[i:i + per_part] for i in range(0, total, per_part)]

    def _has_more_parts_in_round(self) -> bool:
        """Check if the current round still has remaining parts."""
        return bool(self.round_parts) and self.round_part_index < (len(self.round_parts) - 1)

    def _get_active_players(self) -> List[LavaPlatformPlayer]:
        """Return players active in the current round part."""
        if self.active_players is not None:
            return self.active_players
        return [p for p in self.players if p.alive]

    def update(self, dt: float):
        """Main update loop."""
        if self.game_over or self.phase != "playing":
            return

        if not self.round_started:
            self._start_round()

        if self.game_over:
            return

        active_players = self._get_active_players()

        for player in active_players:
            player.update(dt, self.arena, self.round_phase, self.phase_time_left)

        if self.round_phase in ("waiting", "scramble"):
            self._apply_collisions(active_players)

        if self.round_phase == "lava":
            self.arena.update_lava_animation(dt)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            self._handle_phase_transition()

    def _start_round(self):
        """Begin a new round."""
        alive_players = [p for p in self.players if p.alive]

        if len(alive_players) <= self.target_finalists:
            self._finish_game()
            return

        if self.pending_part_advance:
            self.round_part_index += 1
            self.pending_part_advance = False

        if not self.round_parts or self.round_part_index >= len(self.round_parts):
            self.round_parts = self._build_round_parts(alive_players)
            self.round_part_index = 0

        if not self.round_parts:
            self._finish_game()
            return

        self.active_players = self.round_parts[self.round_part_index]

        # Scatter active players before spawning new platform (not on first round)
        if self.round_index > 0:
            self._scatter_players(self.active_players)

        self.current_platform_radius = max(
            self.min_platform_radius,
            self.initial_platform_radius - (self.round_index * self.platform_shrink_per_round)
        )

        self.current_scramble_time = max(
            self.min_scramble_time,
            self.initial_scramble_time - (self.round_index * self.time_decrease_per_round)
        )

        self.arena.spawn_platform(self.current_platform_radius)

        # Spawn obstacles (3-6 based on round number)
        min_obstacles = getattr(config, "LAVA_PLATFORM_MIN_OBSTACLES", 3)
        max_obstacles = getattr(config, "LAVA_PLATFORM_MAX_OBSTACLES", 6)
        obstacle_count = min(min_obstacles + self.round_index // 2, max_obstacles)
        self.arena.spawn_obstacles(obstacle_count)

        for player in self.active_players:
            player.on_platform = False

        self.round_phase = "waiting"
        self.phase_time_left = self.waiting_duration
        self.round_started = True
        self.last_eliminated = 0

    def _scatter_players(self, players: List[LavaPlatformPlayer] = None):
        """Scatter players randomly throughout arena for next round/part."""
        if players is None:
            players = [p for p in self.players if p.alive]
        margin = config.FOLLOWER_RADIUS + 10

        for player in players:
            # Random position within arena bounds
            player.x = random.uniform(self.arena.left + margin, self.arena.right - margin)
            player.y = random.uniform(self.arena.top + margin, self.arena.bottom - margin)

    def _handle_phase_transition(self):
        """Handle transition between phases."""
        if self.round_phase == "waiting":
            self._begin_scramble()
        elif self.round_phase == "scramble":
            self._trigger_lava()
        elif self.round_phase == "lava":
            self._resolve_round()
        elif self.round_phase == "resolve":
            if self._should_end_game():
                self._finish_game()
            else:
                if self._has_more_parts_in_round():
                    self.pending_part_advance = True
                else:
                    self.round_index += 1
                    self.round_parts = []
                    self.round_part_index = 0
                    self.pending_part_advance = False
                self.round_started = False

    def _begin_scramble(self):
        """Start the scramble phase - players rush to platform."""
        self.round_phase = "scramble"
        self.phase_time_left = self.current_scramble_time

    def _trigger_lava(self):
        """Activate lava - eliminate players not on platform."""
        self.round_phase = "lava"
        self.phase_time_left = self.lava_duration
        self.arena.activate_lava()

        active_players = self._get_active_players()
        alive_before = [p for p in active_players if p.alive]
        for player in alive_before:
            player._check_platform_position(self.arena)
            if not player.on_platform:
                player.eliminate()

        alive_after = [p for p in active_players if p.alive]
        self.last_eliminated = len(alive_before) - len(alive_after)

        print(f"Round {self.round_index + 1}: {self.last_eliminated} eliminated, "
              f"{len(alive_after)} remaining")

    def _resolve_round(self):
        """End of round - prepare for next."""
        self.round_phase = "resolve"
        self.phase_time_left = self.resolve_duration
        self.arena.deactivate_lava()

    def _apply_collisions(self, players: List[LavaPlatformPlayer]):
        """Apply collision detection and resolution between players."""
        alive_players = [p for p in players if p.alive]
        min_dist = config.FOLLOWER_RADIUS * 2

        # Multiple iterations for better separation in dense crowds
        # More iterations needed when many players on small platform
        for iteration in range(8):
            any_collision = False
            for i, player in enumerate(alive_players):
                for other in alive_players[i + 1:]:
                    dx = other.x - player.x
                    dy = other.y - player.y
                    dist_sq = dx * dx + dy * dy

                    if dist_sq < min_dist * min_dist:
                        any_collision = True
                        if dist_sq < 1e-6:
                            # Players at exact same position - push in random direction
                            angle = random.uniform(0, 2 * math.pi)
                            dx = math.cos(angle)
                            dy = math.sin(angle)
                            dist = 0.1
                        else:
                            dist = math.sqrt(dist_sq)

                        overlap = min_dist - dist
                        # Push each player by slightly more than half the overlap
                        # to ensure full separation
                        push = overlap * 0.52
                        nx = dx / max(dist, 0.1)
                        ny = dy / max(dist, 0.1)
                        player.x -= nx * push
                        player.y -= ny * push
                        other.x += nx * push
                        other.y += ny * push

            # Clamp after each iteration
            for player in alive_players:
                player.x, player.y = self.arena.clamp_position(
                    player.x, player.y, player.radius
                )

            # Early exit if no collisions found
            if not any_collision:
                break

    def _should_end_game(self) -> bool:
        """Check if game should end (only when one player remains)."""
        alive_count = sum(1 for p in self.players if p.alive)
        return alive_count <= self.target_finalists

    def render(self):
        """Render current frame."""
        active_players = self._get_active_players()
        alive_count = sum(1 for p in active_players if p.alive)
        active_count = len(active_players)
        total_count = len(self.players)
        part_count = len(self.round_parts) if self.round_parts else 1
        part_index = self.round_part_index + 1 if self.round_parts else 1

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index + (1 if self.round_started else 0),
            "max_rounds": self.max_rounds,
            "platform_radius": self.current_platform_radius,
            "phase_time_left": max(0.0, self.phase_time_left),
            "alive_count": alive_count,
            "active_count": active_count,
            "round_part_index": part_index,
            "round_part_count": part_count,
            "last_eliminated": self.last_eliminated,
            "total_count": total_count,
            "arena": self.arena,
            "lava_animation_progress": self.arena.lava_animation_progress,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(active_players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[LavaPlatformPlayer]):
        """Calculate scores and record game history entry."""
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "lava_platform"
        game_display_name = "Lava Escape"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=player.get_survival_time(),
                games_played=0
            )

            points_earned = points_breakdown["total_points"]
            survival_time = player.get_survival_time()

            game_results.append((player.username, placement, points_earned, survival_time))
            game_history_results.append({
                "username": player.username,
                "placement": placement,
                "points": points_earned,
                "survival_time": survival_time,
                "kills": 0,
                "damage": 0.0
            })

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
            non_scoring=True
        )

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()

    def _finish_game(self):
        """End the game and calculate scores."""
        if self.game_over:
            return

        self.arena.deactivate_lava()

        sorted_players = sorted(
            self.players,
            key=lambda p: (not p.alive, -p.get_survival_time()),
        )
        self.finish_game(sorted_players)
