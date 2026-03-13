"""
Mingle Game - Squid Game style grouping rounds.
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

from .arena import MingleArena, MingleRoom
from .player import MinglePlayer
from .renderer import MingleRenderer


class MingleGame(GameTemplate):
    """Mingle game controller with rounds and room grouping."""

    GAME_TITLE = "MINGLE"
    PLAYER_LABEL = "players"

    def __init__(self):
        super().__init__()

        self.round_group_sizes = list(getattr(config, "MINGLE_GROUP_SIZES", [2, 3, 4, 5, 6]))
        if not self.round_group_sizes:
            self.round_group_sizes = [2]
        self.max_room_size = int(
            getattr(
                config,
                "MINGLE_MAX_ROOM_SIZE",
                max(self.round_group_sizes) if self.round_group_sizes else 6,
            )
        )
        if self.max_room_size < 2:
            self.max_room_size = 2
        self.round_group_sizes = [
            size for size in self.round_group_sizes if 1 < size <= self.max_room_size
        ]
        if not self.round_group_sizes:
            self.round_group_sizes = list(range(2, self.max_room_size + 1))
        self.round_count = int(getattr(config, "MINGLE_TOTAL_ROUNDS", len(self.round_group_sizes) or 5))
        if self.round_count <= 0:
            self.round_count = len(self.round_group_sizes) or 5
        self.target_finalists = int(getattr(config, "MINGLE_TARGET_FINALISTS", 2))
        if self.target_finalists < 1:
            self.target_finalists = 1

        self.round_index = 0
        self.round_phase = "mixing"
        self.phase_time_left = 0.0
        self.current_group_size = 0
        self.current_rooms_to_open = 0
        self.target_survivors = 0
        self.current_room_size_min = 0
        self.current_room_size_max = 0
        self.active_rooms: List[MingleRoom] = []
        self.round_started = False
        self.last_eliminated = 0
        self.pending_next_round = False
        self.platform_angle = 0.0
        self.intermission_song_path = getattr(config, "MINGLE_INTERMISSION_SONG_PATH", "")
        self.intermission_volume = float(getattr(config, "MINGLE_INTERMISSION_VOLUME", 0.85))
        self.intermission_sound = None
        self.intermission_channel = self.sound.music_channel
        self.intermission_paused = False
        self.scramble_song_path = getattr(config, "MINGLE_SCRAMBLE_SONG_PATH", "")
        self.scramble_volume = float(getattr(config, "MINGLE_SCRAMBLE_SONG_VOLUME", 0.85))
        self.scramble_sound = None
        self.scramble_channel = pygame.mixer.Channel(3)
        self.scramble_playing = False
        self.intermission_segment_start = None
        self.scramble_segment_start = None
        self.music_segments = []
        self.game_history = GameHistory()
        self.recorder.music_segments = self.music_segments

    def _init_game_components(self):
        self.arena = MingleArena()
        self.renderer = MingleRenderer(self.screen)

    def setup_players(self):
        self._refresh_discord_followers()
        print(f"Setting up {self.PLAYER_LABEL}...")

        if config.TEST_MINIMAL_PLAYERS:
            follower_data = self.api.fetch_followers(config.TEST_MINIMAL_PLAYER_COUNT)
        else:
            follower_data = self.api.fetch_followers(config.FOLLOWER_COUNT)

        random.shuffle(follower_data)

        if config.USE_DYNAMIC_SCALING:
            total_players = len(follower_data)
            platform_radius = max(60, getattr(self.arena, "platform_radius", 140))
            start_radius = config.calculate_dynamic_follower_radius(
                total_players=total_players,
                alive_count=total_players,
                safe_zone_radius=platform_radius,
                initial_zone_radius=platform_radius,
            )
            config.FOLLOWER_RADIUS = start_radius
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
        if config.TEST_MINIMAL_PLAYERS:
            return

        repo_root = Path(__file__).resolve().parents[1]
        overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
        output_file = getattr(config, "FOLLOWER_IMPORT_FILE", "") or ""
        if isinstance(overrides, dict):
            output_file = overrides.get("mingle", output_file) or output_file
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

        print("Refreshing Discord followers for Mingle...")
        result = subprocess.run(command)
        if result.returncode != 0:
            if output_path.exists():
                print(
                    "Discord export failed (exit code "
                    f"{result.returncode}); using existing file: {output_path}"
                )
            else:
                print(
                    "Discord export failed (exit code "
                    f"{result.returncode}); no existing file found."
                )
        else:
            print(f"Discord followers updated: {output_path}")

    def _create_player(self, follower_data: dict, position: tuple) -> MinglePlayer:
        return MinglePlayer(follower_data, position)

    def _get_starting_position(self, index: int, total_players: int) -> tuple:
        center_x, center_y = self.arena.get_center()
        angle = random.uniform(0, 2 * math.pi)
        max_radius = max(10.0, self.arena.platform_radius - config.FOLLOWER_RADIUS)
        radius = random.uniform(0, max_radius)
        return (
            center_x + math.cos(angle) * radius,
            center_y + math.sin(angle) * radius,
        )

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        if not self.round_started:
            self._start_round()

        if self.game_over:
            return

        alive_players = None
        if self.round_phase == "scramble":
            alive_players = [p for p in self.players if p.alive]
            self._redirect_players_from_locked_rooms(alive_players)

        for player in self.players:
            player.update(dt, self.arena, self.round_phase)

        if alive_players is None:
            alive_players = [p for p in self.players if p.alive]
        self._apply_platform_rotation(alive_players, dt)

        if self.round_phase in ("mixing", "scramble"):
            self._apply_collisions()

        if self.round_phase == "scramble":
            if alive_players is None:
                alive_players = [p for p in self.players if p.alive]
            self._enforce_room_capacity(alive_players)
            self._update_room_locks(alive_players)
            self._enforce_inactive_doors(alive_players)
            self._enforce_locked_doors(alive_players)
            self._redirect_players_from_locked_rooms(alive_players)

        self.phase_time_left -= dt
        if self.phase_time_left <= 0:
            if self.round_phase == "mixing":
                self._begin_scramble()
            elif self.round_phase == "scramble":
                self._resolve_round()
            elif self.round_phase == "resolve":
                if self._should_end_game():
                    self._finish_game()
                else:
                    self._start_round()

    def render(self):
        alive_count = sum(1 for p in self.players if p.alive)

        game_state = {
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.round_index + (1 if self.round_started else 0),
            "round_count": self.round_count,
            "group_size": self.current_group_size,
            "group_size_min": self.current_room_size_min,
            "group_size_max": self.current_room_size_max,
            "phase_time_left": max(0.0, self.phase_time_left),
            "alive_count": alive_count,
            "last_eliminated": self.last_eliminated,
            "arena": self.arena,
            "rooms": self.arena.rooms,
            "active_room_ids": [room.index for room in self.active_rooms],
            "platform_angle": self.platform_angle,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _start_round(self):
        alive_players = [p for p in self.players if p.alive]
        if not alive_players:
            self._finish_game()
            return

        if self.round_index >= self.round_count:
            self._finish_game()
            return

        group_size, rooms_to_open, capacity = self._plan_round(len(alive_players))
        if not group_size or not rooms_to_open:
            self._finish_game()
            return

        self.current_group_size = group_size
        self.current_rooms_to_open = rooms_to_open
        self.target_survivors = capacity
        self.current_room_size_min = group_size
        self.current_room_size_max = group_size

        if len(alive_players) < self.current_group_size:
            self._finish_game()
            return

        self._update_player_radius_for_round(self.current_group_size)

        self.active_rooms = self._select_active_rooms(self.current_rooms_to_open)
        if not self.active_rooms:
            self._finish_game()
            return

        for player in alive_players:
            player.clear_room()

        self.round_phase = "mixing"
        self.phase_time_left = getattr(config, "MINGLE_MIX_DURATION", 6.0)
        self.round_started = True
        self.pending_next_round = False
        self.last_eliminated = 0
        self._start_intermission_song()

    def _update_player_radius_for_round(self, group_size: int):
        if group_size <= 0:
            return

        room_width = getattr(config, "MINGLE_ROOM_WIDTH", getattr(config, "MINGLE_ROOM_SIZE", 26))
        room_height = getattr(config, "MINGLE_ROOM_HEIGHT", getattr(config, "MINGLE_ROOM_SIZE", 26))
        entry_radius = getattr(config, "MINGLE_ROOM_ENTRY_RADIUS", 18)
        packing = getattr(config, "MINGLE_ROOM_PACKING_FACTOR", 0.75)

        room_area = max(1.0, float(room_width) * float(room_height))
        entry_area = math.pi * entry_radius * entry_radius
        effective_area = min(room_area, entry_area)

        target_radius = math.sqrt((packing * effective_area) / (group_size * math.pi))
        min_radius = getattr(config, "MINGLE_MIN_RADIUS", 1.0)
        max_radius = getattr(config, "FOLLOWER_MAX_RADIUS", target_radius)
        target_radius = max(min_radius, min(max_radius, target_radius))

        config.FOLLOWER_RADIUS = target_radius
        config.COLLISION_DISTANCE = config.FOLLOWER_RADIUS * 2

        for player in self.players:
            player.radius = target_radius
            player.surface_needs_update = True

    def _candidate_group_sizes(self, alive_count: int) -> List[int]:
        sizes = [size for size in self.round_group_sizes if size > 1]
        max_allowed = min(alive_count, self.max_room_size)
        if max_allowed < 2:
            return []

        if not sizes:
            sizes = list(range(2, max_allowed + 1))
        else:
            max_size = max(sizes)
            if max_allowed > max_size:
                sizes = sorted(set(sizes + list(range(2, max_allowed + 1))))

        return [size for size in sizes if size <= max_allowed]

    def _plan_round(self, alive_count: int) -> tuple:
        rounds_remaining = self.round_count - self.round_index
        if rounds_remaining <= 0 or alive_count <= self.target_finalists:
            return (0, 0, self.target_finalists)

        if rounds_remaining == 1:
            target = self.target_finalists
        else:
            ratio = self.target_finalists / alive_count
            target = int(math.ceil(alive_count * (ratio ** (1.0 / rounds_remaining))))
            target = max(self.target_finalists, min(alive_count - 1, target))

        room_count = len(self.arena.rooms)
        if room_count == 0:
            return (0, 0, target)

        best = None
        sizes = self._candidate_group_sizes(alive_count)

        for allow_divisible in (False, True):
            for size in sizes:
                if size <= 1 or size > alive_count:
                    continue
                if not allow_divisible and alive_count % size == 0:
                    continue

                max_rooms = min(room_count, (alive_count - 1) // size)
                if max_rooms < 1:
                    continue

                target_rooms = max(1, min(max_rooms, int(round(target / size))))
                room_options = {
                    target_rooms,
                    max(1, min(max_rooms, int(math.floor(target / size)))),
                    max(1, min(max_rooms, int(math.ceil(target / size)))),
                }

                for rooms in room_options:
                    capacity = size * rooms
                    if capacity < self.target_finalists:
                        continue
                    if capacity >= alive_count:
                        continue

                    overshoot = 1 if capacity > target else 0
                    score = (overshoot, abs(capacity - target), -capacity)

                    if best is None or score < best[3]:
                        best = (size, rooms, capacity, score)

            if best is not None:
                break

        if best is None:
            return (0, 0, target)

        return best[0], best[1], best[2]

    def _select_active_rooms(self, rooms_to_open: int) -> List[MingleRoom]:
        room_count = len(self.arena.rooms)
        if room_count == 0:
            return []

        rooms_to_open = max(1, min(room_count, rooms_to_open))

        rooms = list(self.arena.rooms)
        random.shuffle(rooms)
        return rooms[:rooms_to_open]

    def _begin_scramble(self):
        self.round_phase = "scramble"
        self.phase_time_left = getattr(config, "MINGLE_SCRAMBLE_DURATION", 10.0)
        self._pause_intermission_song()
        self._start_scramble_song()
        self._assign_rooms()

    def _resolve_round(self):
        self._stop_scramble_song()
        alive_before = [p for p in self.players if p.alive]
        survivors = set()

        for room in self.active_rooms:
            entered = [p for p in alive_before if p.target_room == room and p.in_room]
            if room.capacity and len(entered) == room.capacity:
                for player in entered:
                    survivors.add(player)
            else:
                for player in entered:
                    player.eliminate()

        for player in alive_before:
            if player not in survivors:
                player.eliminate()

        alive_after = [p for p in self.players if p.alive]
        self.last_eliminated = len(alive_before) - len(alive_after)

        self.round_index += 1
        self.round_phase = "resolve"
        self.phase_time_left = getattr(config, "MINGLE_RESOLVE_DURATION", 2.0)
        self.pending_next_round = True

    def _assign_rooms(self):
        alive_players = [p for p in self.players if p.alive]

        for room in self.active_rooms:
            room.reset()
            room.capacity = self.current_group_size

        random.shuffle(alive_players)

        for player in alive_players:
            room = self._find_room_for_player(player)
            if room:
                room.assigned_players.append(player)
                player.assign_room(room)
            else:
                player.clear_room()
                player.set_fallback_target(self._pick_fallback_target())

    def _update_room_locks(self, alive_players: List[MinglePlayer]):
        room_occupants = {room: [] for room in self.active_rooms}

        for player in alive_players:
            room = player.target_room
            if room and player.in_room and room in room_occupants:
                room_occupants[room].append(player)

        for room in self.active_rooms:
            occupants = room_occupants.get(room, [])
            room.occupancy = len(occupants)

            if room.locked:
                continue
            if room.capacity <= 0 or room.occupancy < room.capacity:
                continue

            if len(occupants) > room.capacity:
                occupants.sort(
                    key=lambda p: (p.x - room.center[0]) ** 2 + (p.y - room.center[1]) ** 2
                )
                sealed = occupants[:room.capacity]
            else:
                sealed = occupants

            room.locked = True
            room.sealed_players = set(sealed)
            room.assigned_players = [p for p in room.assigned_players if p in room.sealed_players]
            room.occupancy = len(room.sealed_players)

    def _enforce_room_capacity(self, alive_players: List[MinglePlayer]):
        for room in self.active_rooms:
            if room.capacity <= 0 or room.locked:
                continue

            occupants = [
                p for p in alive_players
                if p.target_room == room and p.in_room
            ]

            if len(occupants) <= room.capacity:
                continue

            occupants.sort(
                key=lambda p: (p.x - room.center[0]) ** 2 + (p.y - room.center[1]) ** 2
            )

            allowed = set(occupants[:room.capacity])
            for player in occupants[room.capacity:]:
                self._evict_player_from_room(player, room)

            for player in allowed:
                player.in_room = True

    def _evict_player_from_room(self, player: MinglePlayer, room: MingleRoom):
        if player in room.assigned_players:
            room.assigned_players.remove(player)

        radial_x = math.cos(room.angle)
        radial_y = math.sin(room.angle)
        inner_center_x = room.center[0] - radial_x * (room.height * 0.5)
        inner_center_y = room.center[1] - radial_y * (room.height * 0.5)

        offset = player.radius + 2
        player.x = inner_center_x - radial_x * offset
        player.y = inner_center_y - radial_y * offset
        player.in_room = False

    def _clamp_player_to_room(self, player: MinglePlayer, room: MingleRoom):
        dx = player.x - room.center[0]
        dy = player.y - room.center[1]

        radial_x = math.cos(room.angle)
        radial_y = math.sin(room.angle)
        tangent_x = -radial_y
        tangent_y = radial_x

        radial_dist = (dx * radial_x) + (dy * radial_y)
        tangent_dist = (dx * tangent_x) + (dy * tangent_y)

        half_width = max(0.0, room.width * 0.5 - player.radius)
        half_height = max(0.0, room.height * 0.5 - player.radius)

        radial_dist = max(-half_height, min(half_height, radial_dist))
        tangent_dist = max(-half_width, min(half_width, tangent_dist))

        player.x = room.center[0] + radial_x * radial_dist + tangent_x * tangent_dist
        player.y = room.center[1] + radial_y * radial_dist + tangent_y * tangent_dist

    def _enforce_locked_doors(self, alive_players: List[MinglePlayer]):
        for room in self.active_rooms:
            if not room.locked:
                continue

            sealed = room.sealed_players
            for player in list(sealed):
                if not player.alive or player.target_room != room:
                    sealed.discard(player)
                    continue
                self._clamp_player_to_room(player, room)
                player.in_room = True

            for player in alive_players:
                if player.target_room == room and player.in_room and player not in sealed:
                    self._evict_player_from_room(player, room)
                    player.clear_room()
                    player.set_fallback_target(self._pick_fallback_target())

            room.occupancy = len(sealed)
            self._block_closed_room_entry(alive_players, room, sealed)

    def _enforce_inactive_doors(self, alive_players: List[MinglePlayer]):
        active_set = set(self.active_rooms)
        for room in self.arena.rooms:
            if room in active_set:
                continue
            self._block_closed_room_entry(alive_players, room, set())

    def _block_closed_room_entry(
        self,
        alive_players: List[MinglePlayer],
        room: MingleRoom,
        allowed_players: set,
    ):
        if not alive_players:
            return

        radial_x = math.cos(room.angle)
        radial_y = math.sin(room.angle)
        tangent_x = -radial_y
        tangent_y = radial_x
        half_width = room.width * 0.5
        half_height = room.height * 0.5

        for player in alive_players:
            if player in allowed_players:
                continue

            dx = player.x - room.center[0]
            dy = player.y - room.center[1]
            radial_dist = (dx * radial_x) + (dy * radial_y)
            tangent_dist = (dx * tangent_x) + (dy * tangent_y)

            if abs(tangent_dist) > half_width + player.radius:
                continue

            inner_limit = -half_height - player.radius
            outer_limit = half_height + player.radius
            if radial_dist <= inner_limit or radial_dist > outer_limit:
                continue

            radial_dist = inner_limit
            player.x = room.center[0] + radial_x * radial_dist + tangent_x * tangent_dist
            player.y = room.center[1] + radial_y * radial_dist + tangent_y * tangent_dist
            if player.target_room == room:
                player.in_room = False

    def _redirect_players_from_locked_rooms(self, alive_players: List[MinglePlayer]):
        for player in alive_players:
            if player.in_room:
                continue
            room = player.target_room
            if room and room.locked:
                if player in room.assigned_players:
                    room.assigned_players.remove(player)
                new_room = self._find_room_for_player(player)
                if new_room:
                    new_room.assigned_players.append(player)
                    player.assign_room(new_room)
                else:
                    player.clear_room()
                    player.set_fallback_target(self._pick_fallback_target())

    def _find_room_for_player(self, player: MinglePlayer):
        best_room = None
        best_dist_sq = None

        for room in self.active_rooms:
            if room.locked:
                continue
            if len(room.assigned_players) >= room.capacity:
                continue
            dx = player.x - room.center[0]
            dy = player.y - room.center[1]
            dist_sq = dx * dx + dy * dy
            if best_room is None or dist_sq < best_dist_sq:
                best_room = room
                best_dist_sq = dist_sq

        return best_room

    def _pick_fallback_target(self) -> tuple:
        center_x, center_y = self.arena.get_center()
        angle = random.uniform(0, 2 * math.pi)
        radius = max(0.0, self.arena.get_room_ring_radius() - 10)
        return (
            center_x + math.cos(angle) * radius,
            center_y + math.sin(angle) * radius,
        )

    def _load_intermission_sound(self):
        if not self.intermission_song_path:
            return

        song_path = Path(self.intermission_song_path)
        if not song_path.exists():
            print(f"⚠️ Intermission song not found: {song_path}")
            return

        cache_path = song_path.with_suffix(".wav")
        try:
            if not cache_path.exists() or cache_path.stat().st_mtime < song_path.stat().st_mtime:
                try:
                    from moviepy.editor import AudioFileClip

                    print(f"   Converting intermission song: {song_path}")
                    audio = AudioFileClip(str(song_path))
                    audio.write_audiofile(str(cache_path), verbose=False, logger=None)
                    audio.close()
                except ImportError:
                    cache_path = song_path
                except Exception as exc:
                    print(f"⚠️ Could not convert intermission song: {exc}")
                    cache_path = song_path

            self.intermission_sound = pygame.mixer.Sound(str(cache_path))
        except Exception as exc:
            print(f"⚠️ Could not load intermission song: {exc}")
            self.intermission_sound = None

    def _start_intermission_song(self):
        if not self.intermission_song_path:
            return

        if self.intermission_sound is None:
            self._load_intermission_sound()
            if self.intermission_sound is None:
                return

        if not self.intermission_channel:
            return

        volume = self.intermission_volume * getattr(self.sound, "master_volume", 1.0)
        self.intermission_channel.set_volume(volume)

        if self.intermission_paused:
            self.intermission_channel.unpause()
            self.intermission_paused = False
            self._mark_intermission_music_start()
            return

        if self.intermission_channel.get_busy():
            return

        self.intermission_channel.play(self.intermission_sound)
        self._mark_intermission_music_start()

    def _pause_intermission_song(self):
        if not self.intermission_channel or not self.intermission_channel.get_busy():
            return
        if self.intermission_paused:
            return
        self.intermission_channel.pause()
        self.intermission_paused = True
        self._mark_intermission_music_end()

    def _stop_intermission_song(self):
        if self.intermission_channel and self.intermission_channel.get_busy():
            self.intermission_channel.stop()
        self.intermission_paused = False
        self._mark_intermission_music_end()

    def _load_scramble_sound(self):
        if not self.scramble_song_path:
            return

        song_path = Path(self.scramble_song_path)
        if not song_path.exists():
            print(f"Scramble song not found: {song_path}")
            return

        cache_path = song_path.with_suffix(".wav")
        try:
            if not cache_path.exists() or cache_path.stat().st_mtime < song_path.stat().st_mtime:
                try:
                    from moviepy.editor import AudioFileClip

                    print(f"   Converting scramble song: {song_path}")
                    audio = AudioFileClip(str(song_path))
                    audio.write_audiofile(str(cache_path), verbose=False, logger=None)
                    audio.close()
                except ImportError:
                    cache_path = song_path
                except Exception as exc:
                    print(f"Could not convert scramble song: {exc}")
                    cache_path = song_path

            self.scramble_sound = pygame.mixer.Sound(str(cache_path))
        except Exception as exc:
            print(f"Could not load scramble song: {exc}")
            self.scramble_sound = None

    def _start_scramble_song(self):
        if not self.scramble_song_path:
            return

        if self.scramble_sound is None:
            self._load_scramble_sound()
            if self.scramble_sound is None:
                return

        if not self.scramble_channel:
            return

        volume = self.scramble_volume * getattr(self.sound, "master_volume", 1.0)
        self.scramble_channel.set_volume(volume)
        self.scramble_channel.play(self.scramble_sound, loops=-1)
        self.scramble_playing = True
        self._mark_scramble_music_start()

    def _stop_scramble_song(self):
        if self.scramble_playing:
            if self.scramble_channel and self.scramble_channel.get_busy():
                self.scramble_channel.stop()
            self.scramble_playing = False
            self._mark_scramble_music_end()

    def _mark_scramble_music_start(self):
        if self.scramble_segment_start is not None:
            return
        self.scramble_segment_start = self._get_recording_timestamp()

    def _mark_scramble_music_end(self):
        if self.scramble_segment_start is None:
            return
        end_time = self._get_recording_timestamp()
        if end_time < self.scramble_segment_start:
            end_time = self.scramble_segment_start
        self.music_segments.append(
            {
                "path": self.scramble_song_path,
                "start": self.scramble_segment_start,
                "end": end_time,
                "volume": self.scramble_volume,
            }
        )
        self.scramble_segment_start = None

    def _mark_intermission_music_start(self):
        if self.intermission_segment_start is not None:
            return
        self.intermission_segment_start = self._get_recording_timestamp()

    def _mark_intermission_music_end(self):
        if self.intermission_segment_start is None:
            return
        end_time = self._get_recording_timestamp()
        if end_time < self.intermission_segment_start:
            end_time = self.intermission_segment_start
        self.music_segments.append(
            {
                "path": self.intermission_song_path,
                "start": self.intermission_segment_start,
                "end": end_time,
                "volume": self.intermission_volume,
            }
        )
        self.intermission_segment_start = None

    def _get_recording_timestamp(self) -> float:
        if getattr(self.recorder, "recording", False):
            return self.recorder.get_video_duration()
        if getattr(self.recorder, "start_time", None) is not None:
            return max(0.0, time.time() - self.recorder.start_time)
        return 0.0

    def _apply_collisions(self):
        alive_players = [p for p in self.players if p.alive]
        min_dist = config.FOLLOWER_RADIUS * 2
        apply_room_push = self.round_phase == "scramble"
        push_force = getattr(config, "MINGLE_ROOM_PUSH_FORCE", 0.0)
        push_margin = getattr(config, "MINGLE_ROOM_PUSH_MARGIN", 0.0)
        entry_scale = getattr(config, "MINGLE_ENTRY_COLLISION_SCALE", 1.0)
        entry_margin = getattr(config, "MINGLE_ENTRY_COLLISION_MARGIN", 0.0)
        relax_entry = self.round_phase == "scramble" and entry_scale != 1.0

        for i, player in enumerate(alive_players):
            for other in alive_players[i + 1:]:
                dx = other.x - player.x
                dy = other.y - player.y
                dist_sq = dx * dx + dy * dy

                pair_min_dist = min_dist
                if relax_entry and self._should_relax_entry_collision(player, other, entry_margin):
                    pair_min_dist = min_dist * entry_scale
                pair_min_dist_sq = pair_min_dist * pair_min_dist

                if dist_sq < pair_min_dist_sq and dist_sq > 1e-6:
                    dist = math.sqrt(dist_sq)
                    overlap = pair_min_dist - dist
                    push = overlap * 0.5
                    nx = dx / dist
                    ny = dy / dist
                    player.x -= nx * push
                    player.y -= ny * push
                    other.x += nx * push
                    other.y += ny * push
                    if apply_room_push and push_force > 0:
                        push_strength = push_force * (overlap / min_dist)
                        self._apply_room_push(player, other, push_strength, push_margin)
                        self._apply_room_push(other, player, push_strength, push_margin)

        for player in alive_players:
            if self.round_phase == "mixing":
                player.x, player.y = self.arena.clamp_to_platform(player.x, player.y, player.radius)
            else:
                player.x, player.y = self.arena.clamp_position(player.x, player.y, player.radius)

    def _should_relax_entry_collision(
        self,
        player: MinglePlayer,
        other: MinglePlayer,
        margin: float,
    ) -> bool:
        room = player.target_room
        if not room or room != other.target_room:
            return False
        if room.locked or room not in self.active_rooms:
            return False
        return self._is_near_room_entry(player, room, margin) and self._is_near_room_entry(other, room, margin)

    def _is_near_room_entry(self, player: MinglePlayer, room: MingleRoom, margin: float) -> bool:
        dx = player.x - room.center[0]
        dy = player.y - room.center[1]

        radial_x = math.cos(room.angle)
        radial_y = math.sin(room.angle)
        tangent_x = -radial_y
        tangent_y = radial_x

        radial_dist = (dx * radial_x) + (dy * radial_y)
        tangent_dist = (dx * tangent_x) + (dy * tangent_y)

        half_width = room.width * 0.5 + margin
        if abs(tangent_dist) > half_width:
            return False

        entry_band = max(0.0, margin) + (player.radius * 0.5)
        half_height = room.height * 0.5
        return abs(radial_dist + half_height) <= entry_band

    def _apply_platform_rotation(self, alive_players: List[MinglePlayer], dt: float):
        spin_speed = getattr(
            config,
            "MINGLE_PLATFORM_ROTATION_SPEED",
            getattr(config, "MINGLE_PLATFORM_SPIN_SPEED", 0.0),
        )
        if not spin_speed:
            return

        platform_radius = getattr(self.arena, "platform_radius", 0.0)
        if platform_radius <= 0:
            return

        center_x, center_y = self.arena.get_center()
        angle_step = spin_speed * dt
        self.platform_angle = (self.platform_angle + angle_step) % (2 * math.pi)

        for player in alive_players:
            dx = player.x - center_x
            dy = player.y - center_y
            dist = math.hypot(dx, dy)
            if dist <= (platform_radius - player.radius):
                angle = math.atan2(dy, dx) + angle_step
                player.x = center_x + math.cos(angle) * dist
                player.y = center_y + math.sin(angle) * dist

    def _apply_room_push(
        self,
        pusher: MinglePlayer,
        target: MinglePlayer,
        push_strength: float,
        push_margin: float,
    ):
        room = pusher.target_room
        if not room or room.locked:
            return
        if not self._is_player_near_room(pusher, room, push_margin):
            return
        if target.target_room == room and target.in_room:
            return

        dx = target.x - room.center[0]
        dy = target.y - room.center[1]
        dist = math.hypot(dx, dy)
        if dist < 1e-3:
            return

        nx = dx / dist
        ny = dy / dist
        target.x += nx * push_strength
        target.y += ny * push_strength

    def _is_player_near_room(self, player: MinglePlayer, room: MingleRoom, margin: float) -> bool:
        if margin is None:
            margin = 0.0
        dx = player.x - room.center[0]
        dy = player.y - room.center[1]

        radial_x = math.cos(room.angle)
        radial_y = math.sin(room.angle)
        tangent_x = -radial_y
        tangent_y = radial_x

        radial_dist = (dx * radial_x) + (dy * radial_y)
        tangent_dist = (dx * tangent_x) + (dy * tangent_y)

        half_width = room.width * 0.5 + margin
        half_height = room.height * 0.5 + margin

        return abs(tangent_dist) <= half_width and abs(radial_dist) <= half_height

    def _should_end_game(self) -> bool:
        alive_count = sum(1 for p in self.players if p.alive)
        if alive_count <= self.target_finalists:
            return True
        if self.round_index >= self.round_count:
            return True
        next_group_size, rooms_to_open, _ = self._plan_round(alive_count)
        if not next_group_size or not rooms_to_open:
            return True
        return False

    def _calculate_and_save_scores(self, sorted_players: List[MinglePlayer]):
        """Calculate scores and record a non-scoring game history entry."""
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "mingle"
        game_display_name = "Mingle"
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
        if self.game_over:
            return
        self._stop_scramble_song()
        self._stop_intermission_song()

        sorted_players = sorted(
            self.players,
            key=lambda p: (not p.alive, -p.get_survival_time()),
        )
        self.finish_game(sorted_players)
