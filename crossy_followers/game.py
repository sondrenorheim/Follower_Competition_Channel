import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pygame

import config
from shared import GameHistory, GameTemplate, auto_push
from shared.club_members import load_club_member_set, normalize_username, select_club_spotlight

from .arena import CrossyFollowersArena
from .player import CrossyFollower
from .renderer import CrossyFollowersRenderer


@dataclass
class CrossyEntity:
    kind: str
    x: float
    width: float
    speed: float = 0.0
    sprite: str = ""
    collision_scale: float = 0.82


@dataclass
class CrossyRow:
    index: int
    row_type: str
    entities: List[CrossyEntity] = field(default_factory=list)
    blocked_lanes: Set[int] = field(default_factory=set)
    variant: int = 0


class CrossyFollowersGame(GameTemplate):
    GAME_TITLE = "CROSSY FOLLOWERS"
    GAME_SUBTITLE = "Making my club members cross every day"
    PLAYER_LABEL = "club members"

    def __init__(self):
        super().__init__()

        self.game_time = 0.0
        self.game_history = GameHistory()
        self.club_spotlight = None
        self.recent_eliminations: List[str] = []

        self.rows: Dict[int, CrossyRow] = {}
        self.start_row = int(getattr(config, "CROSSY_START_ROW", 8))
        self.camera_row = max(0.0, float(self.start_row - float(getattr(config, "CROSSY_CAMERA_ROW_OFFSET", 6.0))))
        self.current_leader_row = float(self.start_row)

        self.seed = int(getattr(config, "DAY_NUMBER", 1)) * 10007 + 1777
        self.root_rng = random.Random(self.seed)

        self.max_game_time = float(getattr(config, "CROSSY_MAX_GAME_TIME", 85.0))
        self.rows_ahead = int(getattr(config, "CROSSY_ROWS_AHEAD", 34))
        self.rows_behind = max(18, int(getattr(config, "CROSSY_ROWS_BEHIND", 10)))
        self.initial_rows = int(getattr(config, "CROSSY_INITIAL_ROWS", 32))
        self.camera_smooth = float(getattr(config, "CROSSY_CAMERA_SMOOTH", 7.0))
        self.camera_row_offset = float(getattr(config, "CROSSY_CAMERA_ROW_OFFSET", 6.0))
        self.fall_behind_rows = int(getattr(config, "CROSSY_FALL_BEHIND_ROWS", 4))
        self.move_cooldown_min = float(getattr(config, "CROSSY_MOVE_COOLDOWN_MIN", 0.33))
        self.move_cooldown_max = float(getattr(config, "CROSSY_MOVE_COOLDOWN_MAX", 0.45))
        if self.move_cooldown_max < self.move_cooldown_min:
            self.move_cooldown_min, self.move_cooldown_max = self.move_cooldown_max, self.move_cooldown_min
        self.move_cooldown_min = max(0.05, self.move_cooldown_min)
        self.move_cooldown_max = max(self.move_cooldown_min, self.move_cooldown_max)
        self.move_cooldown = (self.move_cooldown_min + self.move_cooldown_max) * 0.5
        self.wrap_padding_lanes = float(getattr(config, "CROSSY_WRAP_PADDING_LANES", 4.5))
        self.spawn_safe_rows = max(2, int(getattr(config, "CROSSY_SPAWN_SAFE_ROWS", 3)))
        self.difficulty_ramp_rows = max(10, int(getattr(config, "CROSSY_DIFFICULTY_RAMP_ROWS", 42)))
        self.water_unlock_rows = max(0, int(getattr(config, "CROSSY_WATER_UNLOCK_ROWS", 3)))
        self.rail_unlock_rows = max(self.water_unlock_rows, int(getattr(config, "CROSSY_RAIL_UNLOCK_ROWS", 7)))
        self.progress_weight = float(getattr(config, "CROSSY_PROGRESS_WEIGHT", 18.0))
        self.progress_weight_min = float(getattr(config, "CROSSY_PROGRESS_WEIGHT_MIN", 10.0))
        self.stall_force_move_time = float(getattr(config, "CROSSY_STALL_FORCE_MOVE_TIME", 1.75))
        self.stall_hard_force_time = float(getattr(config, "CROSSY_STALL_HARD_FORCE_TIME", 4.5))
        self.max_recent_eliminations = int(getattr(config, "CROSSY_ELIMINATION_TRACK_LIMIT", 400))
        self.club_import_file = str(
            getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {}).get(
                "crossy_followers",
                "Followers/club_members_followers.json",
            )
        )

        self.car_sprites = list(
            getattr(
                config,
                "CROSSY_CAR_SPRITES",
                [
                    "blue_car",
                    "green_car",
                    "orange_car",
                    "police_car",
                    "purple_car",
                    "red_truck",
                    "blue_truck",
                    "taxi",
                ],
            )
        )
        self.log_sprites = list(getattr(config, "CROSSY_LOG_SPRITES", ["log0", "log1", "log2", "log3"]))
        self.tree_sprites = list(getattr(config, "CROSSY_TREE_SPRITES", ["tree0", "tree1", "tree2", "tree3"]))
        self.boulder_sprites = list(getattr(config, "CROSSY_BOULDER_SPRITES", ["boulder0", "boulder1"]))

        # Keep export music behavior aligned with Jetpack Followers.
        self.sound.background_music_path = str(
            getattr(config, "JETPACK_BACKGROUND_MUSIC_PATH", "assets/Sydney Tour Song adjusted.m4a")
        )
        self.sound.preload_audio()
        self.recorder.background_music_path = self.sound.background_music_path

    def _init_game_components(self):
        self.arena = CrossyFollowersArena()
        self.renderer = CrossyFollowersRenderer(self.screen)

    def setup_players(self):
        print(f"Setting up {self.PLAYER_LABEL}...")
        target_count = 0

        if config.TEST_MINIMAL_PLAYERS:
            target_count = int(getattr(config, "TEST_MINIMAL_PLAYER_COUNT", 12))
            follower_data = self.api.fetch_followers(target_count)
        else:
            # Crossy Followers is always club-members-only.
            if self.club_import_file:
                self.api.import_file = self.club_import_file

            configured_count = getattr(config, "FOLLOWER_COUNT", None)
            if configured_count is not None and int(configured_count) > 0:
                target_count = int(configured_count)
            else:
                min_count = int(getattr(config, "CROSSY_PLAYER_COUNT_MIN", 10))
                max_count = int(getattr(config, "CROSSY_PLAYER_COUNT_MAX", 20))
                if max_count < min_count:
                    min_count, max_count = max_count, min_count
                min_count = max(2, min_count)
                max_count = max(min_count, max_count)
                target_count = self.root_rng.randint(min_count, max_count)
            follower_data = self.api.fetch_followers(target_count)

        club_members = load_club_member_set()
        if not config.TEST_MINIMAL_PLAYERS and club_members:
            filtered_followers = [
                data for data in follower_data
                if normalize_username(data.get("username")) in club_members
            ]
            if filtered_followers:
                follower_data = filtered_followers
            elif self.club_import_file:
                fallback_data = self._load_follower_import_file(self.club_import_file)
                fallback_filtered = [
                    data for data in fallback_data
                    if normalize_username(data.get("username")) in club_members
                ]
                if fallback_filtered:
                    follower_data = fallback_filtered

        self.root_rng.shuffle(follower_data)
        if target_count > 0 and len(follower_data) > target_count:
            follower_data = follower_data[:target_count]

        lane_order = list(range(self.arena.lane_count))
        self.root_rng.shuffle(lane_order)

        for idx, data in enumerate(follower_data):
            payload = dict(data)
            if "avatar_image" not in payload and "avatar" in payload:
                payload["avatar_image"] = payload["avatar"]

            lane = lane_order[idx % len(lane_order)]
            player = CrossyFollower(payload, (self.arena.lane_to_x(lane), float(self.start_row)))
            player.set_grid_position(lane, self.start_row, self.arena)
            player.move_cooldown_min = self.move_cooldown_min
            player.move_cooldown_max = self.move_cooldown_max
            player.move_cooldown = self.move_cooldown
            player.next_move_time = self.root_rng.uniform(0.0, self.move_cooldown_max)
            player.last_progress_time = self.game_time

            username = normalize_username(payload.get("username"))
            player.is_club_member = username in club_members
            self.players.append(player)

        self.club_spotlight = select_club_spotlight(self.players)

        max_initial_row = self.start_row + max(self.initial_rows, 12)
        self._ensure_rows_until(max_initial_row)

        print(f"{len(self.players)} {self.PLAYER_LABEL} ready!\n")

    @staticmethod
    def _load_follower_import_file(path_value: str) -> List[dict]:
        path = Path(path_value)
        if not path.exists():
            return []

        try:
            import json

            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            return []

        if not isinstance(raw, list):
            return []

        rows: List[dict] = []
        for entry in raw:
            if isinstance(entry, dict):
                rows.append(entry)
        return rows

    def _row_rng(self, row_index: int) -> random.Random:
        row_seed = (self.seed * 73856093 + int(row_index) * 19349663) & 0xFFFFFFFF
        return random.Random(row_seed)

    def _ensure_row(self, row_index: int) -> CrossyRow:
        row_idx = max(0, int(row_index))
        row = self.rows.get(row_idx)
        if row is None:
            row = self._generate_row(row_idx)
            self.rows[row_idx] = row
        return row

    def _ensure_rows_until(self, row_index: int):
        if row_index < 0:
            return
        for idx in range(0, int(row_index) + 1):
            self._ensure_row(idx)

    def _generate_row(self, row_index: int) -> CrossyRow:
        rng = self._row_rng(row_index)
        previous = self.rows.get(row_index - 1)

        if row_index <= self.start_row + self.spawn_safe_rows:
            row_type = "grass"
        else:
            row_type = self._choose_row_type(rng, previous, row_index)

        if row_type == "road":
            return self._generate_road_row(row_index, rng)
        if row_type == "water":
            return self._generate_water_row(row_index, rng, previous)
        if row_type == "rail":
            return self._generate_rail_row(row_index, rng)
        return self._generate_grass_row(row_index, rng, previous)

    @staticmethod
    def _weighted_choice(rng: random.Random, weighted: List[Tuple[str, float]]) -> str:
        total = sum(max(0.0, item[1]) for item in weighted)
        if total <= 0:
            return weighted[0][0]
        roll = rng.uniform(0.0, total)
        acc = 0.0
        for key, weight in weighted:
            acc += max(0.0, weight)
            if roll <= acc:
                return key
        return weighted[-1][0]

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _row_difficulty(self, row_index: int) -> float:
        start = self.start_row + self.spawn_safe_rows
        progress = max(0, int(row_index) - start)
        return self._clamp01(progress / float(max(1, self.difficulty_ramp_rows)))

    def _choose_row_type(self, rng: random.Random, previous: Optional[CrossyRow], row_index: int) -> str:
        difficulty = self._row_difficulty(row_index)
        weights = {
            "grass": self._lerp(0.68, 0.20, difficulty),
            "road": self._lerp(0.24, 0.42, difficulty),
            "water": self._lerp(0.08, 0.26, difficulty),
            "rail": self._lerp(0.00, 0.12, difficulty),
        }

        if row_index < self.start_row + self.water_unlock_rows:
            weights["water"] = 0.0
        if row_index < self.start_row + self.rail_unlock_rows:
            weights["rail"] = 0.0

        if previous is not None:
            if previous.row_type == "rail":
                weights["rail"] = 0.0
                weights["grass"] += 0.18
                weights["road"] += 0.05
            elif previous.row_type == "water":
                weights["water"] *= 0.45
                weights["grass"] += 0.12
            elif previous.row_type == "road":
                weights["road"] *= 1.08
                weights["grass"] *= 0.96

        weighted = [
            ("grass", max(0.0, weights["grass"])),
            ("road", max(0.0, weights["road"])),
            ("water", max(0.0, weights["water"])),
            ("rail", max(0.0, weights["rail"])),
        ]
        return self._weighted_choice(rng, weighted)

    def _grass_required_clear_lanes(self, previous: Optional[CrossyRow]) -> Set[int]:
        if previous is None:
            return set()
        if previous.row_type != "water":
            return set()
        lanes = []
        for entity in previous.entities:
            if entity.kind == "lily":
                lanes.append(self.arena.x_to_lane(entity.x))
        return set(lanes)

    def _generate_grass_row(self, row_index: int, rng: random.Random, previous: Optional[CrossyRow]) -> CrossyRow:
        # Provide a clear runway around the spawn area to reduce early deadlocks.
        if row_index <= self.start_row + self.spawn_safe_rows:
            return CrossyRow(
                index=row_index,
                row_type="grass",
                entities=[],
                blocked_lanes=set(),
                variant=rng.randint(0, 1),
            )

        blocked_lanes: Set[int] = set()
        entities: List[CrossyEntity] = []
        required_clear = self._grass_required_clear_lanes(previous)
        difficulty = self._row_difficulty(row_index)

        edge_block_chance = self._lerp(0.60, 0.90, difficulty)
        if 0 not in required_clear and rng.random() < edge_block_chance:
            blocked_lanes.add(0)
        if (self.arena.lane_count - 1) not in required_clear and rng.random() < edge_block_chance:
            blocked_lanes.add(self.arena.lane_count - 1)

        free_candidates = [
            lane
            for lane in range(1, self.arena.lane_count - 1)
            if lane not in required_clear
        ]
        inner_lane_count = max(1, len(free_candidates))
        min_obstacles = 0 if difficulty < 0.20 else 1
        max_obstacles = max(
            min_obstacles,
            int(round(inner_lane_count * self._lerp(0.18, 0.45, difficulty))),
        )
        obstacle_count = rng.randint(min_obstacles, max_obstacles)
        rng.shuffle(free_candidates)
        for lane in free_candidates[:min(obstacle_count, len(free_candidates))]:
            blocked_lanes.add(lane)

        if len(blocked_lanes) >= self.arena.lane_count:
            blocked_lanes.discard(rng.randrange(self.arena.lane_count))

        for lane in sorted(blocked_lanes):
            sprite = rng.choice(self.tree_sprites if rng.random() < 0.6 else self.boulder_sprites)
            kind = "tree" if sprite.startswith("tree") else "boulder"
            entities.append(
                CrossyEntity(
                    kind=kind,
                    x=self.arena.lane_to_x(lane),
                    width=self.arena.lane_width * (0.84 if kind == "tree" else 0.78),
                    speed=0.0,
                    sprite=sprite,
                    collision_scale=0.92,
                )
            )

        return CrossyRow(
            index=row_index,
            row_type="grass",
            entities=entities,
            blocked_lanes=blocked_lanes,
            variant=rng.randint(0, 1),
        )

    def _spawn_moving_row_entities(
        self,
        rng: random.Random,
        count: int,
        speed: float,
        min_width: float,
        max_width: float,
        spacing_min: float,
        spacing_max: float,
        sprites: List[str],
        kind: str,
        collision_scale: float,
    ) -> List[CrossyEntity]:
        entities: List[CrossyEntity] = []
        x: Optional[float] = None

        for _ in range(max(1, count)):
            width = self.arena.lane_width * rng.uniform(min_width, max_width)
            left, right = self._wrap_bounds(width)
            if x is None:
                x = left if speed > 0 else right
            sprite = rng.choice(sprites) if sprites else ""
            entities.append(
                CrossyEntity(
                    kind=kind,
                    x=x,
                    width=width,
                    speed=speed * rng.uniform(0.9, 1.15),
                    sprite=sprite,
                    collision_scale=collision_scale,
                )
            )
            x -= self.arena.lane_width * rng.uniform(spacing_min, spacing_max) * (1 if speed > 0 else -1)

        return entities

    def _generate_road_row(self, row_index: int, rng: random.Random) -> CrossyRow:
        difficulty = self._row_difficulty(row_index)
        direction = 1 if rng.random() < 0.5 else -1
        speed = self.arena.lane_width * rng.uniform(
            self._lerp(1.05, 1.85, difficulty),
            self._lerp(1.90, 3.15, difficulty),
        ) * direction
        max_count = 2 if difficulty < 0.40 else 3
        count = rng.randint(1, max_count)
        entities = self._spawn_moving_row_entities(
            rng=rng,
            count=count,
            speed=speed,
            min_width=0.90,
            max_width=1.65,
            spacing_min=self._lerp(3.6, 2.3, difficulty),
            spacing_max=self._lerp(5.2, 3.8, difficulty),
            sprites=self.car_sprites,
            kind="car",
            collision_scale=0.80,
        )
        return CrossyRow(
            index=row_index,
            row_type="road",
            entities=entities,
            blocked_lanes=set(),
            variant=rng.randint(0, 1),
        )

    def _generate_water_row(self, row_index: int, rng: random.Random, previous: Optional[CrossyRow]) -> CrossyRow:
        difficulty = self._row_difficulty(row_index)
        static_row = (row_index % 2) == 0
        entities: List[CrossyEntity] = []

        if static_row:
            lily_min = 3 if difficulty < 0.45 else 2
            lily_max = 5 if difficulty < 0.20 else (4 if difficulty < 0.70 else 3)
            if lily_max < lily_min:
                lily_max = lily_min
            lily_count = rng.randint(lily_min, lily_max)
            lanes = list(range(self.arena.lane_count))
            rng.shuffle(lanes)
            lily_lanes = lanes[:lily_count]

            if previous is not None and previous.row_type == "grass":
                previous_clear = [lane for lane in range(self.arena.lane_count) if lane not in previous.blocked_lanes]
                if previous_clear and not any(lane in previous_clear for lane in lily_lanes):
                    lily_lanes[0] = rng.choice(previous_clear)

            for lane in sorted(set(lily_lanes)):
                entities.append(
                    CrossyEntity(
                        kind="lily",
                        x=self.arena.lane_to_x(lane),
                        width=self.arena.lane_width * 0.92,
                        speed=0.0,
                        sprite="lily_pad",
                        collision_scale=0.88,
                    )
                )
        else:
            direction = 1 if rng.random() < 0.5 else -1
            speed = self.arena.lane_width * rng.uniform(
                self._lerp(0.45, 0.85, difficulty),
                self._lerp(1.00, 1.55, difficulty),
            ) * direction
            max_count = 2 if difficulty < 0.35 else 3
            count = rng.randint(2, max_count)
            entities = self._spawn_moving_row_entities(
                rng=rng,
                count=count,
                speed=speed,
                min_width=1.7,
                max_width=2.9,
                spacing_min=self._lerp(3.5, 2.5, difficulty),
                spacing_max=self._lerp(5.0, 4.0, difficulty),
                sprites=self.log_sprites,
                kind="log",
                collision_scale=0.86,
            )

        return CrossyRow(
            index=row_index,
            row_type="water",
            entities=entities,
            blocked_lanes=set(),
            variant=rng.randint(0, 1),
        )

    def _rail_direction(self, row_index: int, rng: random.Random) -> int:
        mode = str(getattr(config, "CROSSY_RAIL_DIRECTION_MODE", "expo")).strip().lower()
        if mode in {"alternate", "alternating"}:
            return 1 if (row_index % 2 == 0) else -1
        if mode in {"random", "legacy"}:
            return 1 if rng.random() < 0.5 else -1
        # Expo default: trains move in one fixed direction and wrap around.
        return 1

    def _generate_rail_row(self, row_index: int, rng: random.Random) -> CrossyRow:
        difficulty = self._row_difficulty(row_index)
        direction = self._rail_direction(row_index, rng)
        speed = self.arena.lane_width * rng.uniform(
            self._lerp(4.4, 5.8, difficulty),
            self._lerp(6.6, 8.8, difficulty),
        ) * direction
        width = self.arena.lane_width * rng.uniform(
            self._lerp(3.6, 4.6, difficulty),
            self._lerp(5.9, 7.2, difficulty),
        )
        left, right = self._wrap_bounds(width)
        x = left if speed > 0 else right
        entities = [
            CrossyEntity(
                kind="train",
                x=x,
                width=width,
                speed=speed,
                sprite="train_middle",
                collision_scale=0.94,
            )
        ]
        return CrossyRow(
            index=row_index,
            row_type="rail",
            entities=entities,
            blocked_lanes=set(),
            variant=rng.randint(0, 1),
        )

    def _wrap_bounds(self, width: float) -> Tuple[float, float]:
        pad = self.arena.lane_width * max(1.0, self.wrap_padding_lanes)
        half_w = max(0.0, width * 0.5)
        left = self.arena.screen_left - half_w - pad
        right = self.arena.screen_right + half_w + pad
        return left, right

    def _advance_wrapped(self, x: float, speed: float, dt: float, width: float) -> float:
        if abs(speed) <= 1e-6 or dt <= 0:
            return x
        value = x + speed * dt
        left, right = self._wrap_bounds(width)
        span = right - left
        if span <= 0:
            return value
        while value < left:
            value += span
        while value > right:
            value -= span
        return value

    def _predict_entity_x(self, entity: CrossyEntity, delta_time: float) -> float:
        return self._advance_wrapped(entity.x, entity.speed, max(0.0, delta_time), entity.width)

    def _update_rows(self, dt: float):
        for row in self.rows.values():
            for entity in row.entities:
                if abs(entity.speed) > 1e-6:
                    entity.x = self._advance_wrapped(entity.x, entity.speed, dt, entity.width)

    def _update_camera(self, dt: float):
        alive = [p for p in self.players if p.alive]
        candidates = alive if alive else self.players
        if not candidates:
            return

        self.current_leader_row = float(max(player.max_row for player in candidates))
        target_camera = max(0.0, self.current_leader_row - self.camera_row_offset)
        lerp = min(1.0, max(0.0, dt * self.camera_smooth))
        self.camera_row += (target_camera - self.camera_row) * lerp

    def _maintain_rows(self):
        highest_needed = int(math.ceil(self.current_leader_row + self.rows_ahead))
        self._ensure_rows_until(highest_needed)

        min_keep = max(0, int(math.floor(self.camera_row)) - self.rows_behind)
        stale_rows = [idx for idx in self.rows.keys() if idx < min_keep]
        for idx in stale_rows:
            self.rows.pop(idx, None)

    def _collides_with_entity(self, x: float, entity: CrossyEntity, radius: float) -> bool:
        half = entity.width * 0.5 * max(0.5, entity.collision_scale)
        return abs(x - entity.x) <= (half + radius * 0.88)

    def _find_ridable(self, row: CrossyRow, x: float, delta_time: float = 0.0) -> Optional[CrossyEntity]:
        for entity in row.entities:
            if entity.kind not in {"log", "lily"}:
                continue
            entity_x = self._predict_entity_x(entity, delta_time) if delta_time > 0 else entity.x
            half = entity.width * 0.5 * max(0.4, entity.collision_scale)
            if abs(x - entity_x) <= half:
                return entity
        return None

    def _eliminate_player(self, player: CrossyFollower):
        if not player.alive:
            return
        player.eliminate_at(self.game_time)
        if player.username:
            self.recent_eliminations.insert(0, player.username)
            if len(self.recent_eliminations) > self.max_recent_eliminations:
                self.recent_eliminations.pop()

    def _apply_environment(self, player: CrossyFollower, dt: float):
        if not player.alive:
            return

        row = self._ensure_row(player.grid_row)

        if row.row_type == "water":
            ridable = self._find_ridable(row, player.x)
            if ridable is None:
                self._eliminate_player(player)
                return
            if dt > 0 and abs(ridable.speed) > 1e-6:
                player.x = self._advance_wrapped(player.x, ridable.speed, dt, player.radius * 2.0)
        elif row.row_type == "road":
            for entity in row.entities:
                if entity.kind == "car" and self._collides_with_entity(player.x, entity, player.radius):
                    self._eliminate_player(player)
                    return
        elif row.row_type == "rail":
            for entity in row.entities:
                if entity.kind == "train" and self._collides_with_entity(player.x, entity, player.radius):
                    self._eliminate_player(player)
                    return
        elif row.row_type == "grass":
            lane = self.arena.x_to_lane(player.x)
            if lane in row.blocked_lanes:
                lane_x = self.arena.lane_to_x(lane)
                if player.x <= lane_x:
                    player.x = lane_x - self.arena.lane_width * 0.45
                else:
                    player.x = lane_x + self.arena.lane_width * 0.45

        side_margin = self.arena.lane_width * 0.65
        if player.x < self.arena.screen_left - side_margin or player.x > self.arena.screen_right + side_margin:
            self._eliminate_player(player)
            return

        if player.grid_row < int(self.camera_row) - self.fall_behind_rows:
            self._eliminate_player(player)

    def _evaluate_position_safety(
        self,
        x: float,
        lane: int,
        row_idx: int,
        now: float,
        radius: float,
        horizon: float,
    ) -> float:
        row = self._ensure_row(row_idx)
        step_horizon = max(self.move_cooldown_min, float(horizon))
        sample_offsets = (0.0, step_horizon * 0.45, step_horizon * 0.9)
        min_clear = float("inf")

        if row.row_type == "grass":
            if lane in row.blocked_lanes:
                return -1200.0
            return 4.0

        if row.row_type == "road":
            for t_off in sample_offsets:
                for entity in row.entities:
                    if entity.kind != "car":
                        continue
                    ex = self._predict_entity_x(entity, now + t_off - self.game_time)
                    clear = abs(x - ex) - ((entity.width * 0.5 * entity.collision_scale) + radius * 0.88)
                    min_clear = min(min_clear, clear)
            if min_clear < 0:
                return -1500.0
            return min(6.0, min_clear / max(1.0, self.arena.lane_width))

        if row.row_type == "rail":
            for t_off in sample_offsets:
                for entity in row.entities:
                    if entity.kind != "train":
                        continue
                    ex = self._predict_entity_x(entity, now + t_off - self.game_time)
                    clear = abs(x - ex) - ((entity.width * 0.5 * entity.collision_scale) + radius)
                    min_clear = min(min_clear, clear)
            if min_clear < 0:
                return -2200.0
            return min(5.0, min_clear / max(1.0, self.arena.lane_width)) - 0.6

        # Water row
        ridable_now = self._find_ridable(row, x, delta_time=max(0.0, now - self.game_time))
        if ridable_now is None:
            return -1800.0
        if abs(ridable_now.speed) > 1e-6:
            drift_x = x + ridable_now.speed * step_horizon
            edge_pad = self.arena.lane_width * 0.55
            if drift_x < self.arena.screen_left - edge_pad or drift_x > self.arena.screen_right + edge_pad:
                return -900.0
        return 3.0

    def _player_stall_time(self, player: CrossyFollower) -> float:
        last_progress = float(getattr(player, "last_progress_time", self.game_time))
        return max(0.0, self.game_time - last_progress)

    def _next_row_alignment_bonus(self, lane: int, row_idx: int) -> float:
        """Reward lateral positioning that sets up a valid forward path."""
        base_row = self._ensure_row(row_idx)
        next_row = self._ensure_row(row_idx + 1)
        if next_row.row_type != "water":
            return 0.0
        if not next_row.entities or not all(entity.kind == "lily" for entity in next_row.entities):
            return 0.0

        lily_lanes = sorted({
            self.arena.x_to_lane(entity.x)
            for entity in next_row.entities
            if self.arena.x_to_lane(entity.x) not in base_row.blocked_lanes
        })
        if not lily_lanes:
            return 0.0

        distance = min(abs(lane - lily_lane) for lily_lane in lily_lanes)
        return max(-2.0, 4.0 - distance * 2.0)

    def _score_move(self, player: CrossyFollower, target_lane: int, target_row: int, delta_lane: int, delta_row: int) -> float:
        target_x = self.arena.lane_to_x(target_lane)
        player_cooldown = (
            float(getattr(player, "move_cooldown_min", self.move_cooldown_min))
            + float(getattr(player, "move_cooldown_max", self.move_cooldown_max))
        ) * 0.5
        arrival_time = self.game_time + (player_cooldown * 0.5 if (delta_lane or delta_row) else player_cooldown)
        safety = self._evaluate_position_safety(
            target_x,
            target_lane,
            target_row,
            arrival_time,
            player.radius,
            player_cooldown,
        )
        if safety <= -1000:
            return safety

        stall_time = self._player_stall_time(player)
        progress_weight = self.progress_weight
        if stall_time > 1.0:
            progress_weight = max(
                self.progress_weight_min,
                self.progress_weight - (stall_time - 1.0) * 5.0,
            )
        progress_gain = float(target_row - player.grid_row)
        score = progress_gain * progress_weight + safety * 2.4

        if delta_row < 0:
            score -= max(0.0, 4.0 - stall_time * 2.5)
        elif delta_row > 0:
            score += 1.5 + min(2.0, stall_time * 0.4)
        if delta_lane != 0:
            score -= 0.25
        if delta_lane == 0 and delta_row == 0:
            score -= 1.0 + min(18.0, stall_time * 4.5)

        center_lane = (self.arena.lane_count - 1) * 0.5
        center_bias = 1.0 - abs(target_lane - center_lane) / max(1.0, center_lane)
        score += center_bias * 0.35

        if delta_row == 0:
            score += self._next_row_alignment_bonus(target_lane, target_row)

        score += player.decision_jitter * 0.25
        return score

    def _choose_move(self, player: CrossyFollower) -> Tuple[int, int]:
        current_lane = self.arena.x_to_lane(player.x)
        current_row = player.grid_row
        options = [
            (0, 1),   # up
            (-1, 0),  # left
            (1, 0),   # right
            (0, 0),   # wait
            (0, -1),  # down
        ]

        best_lane = current_lane
        best_row = current_row
        best_score = -1e9
        scored_options: List[Tuple[float, int, int, int, int]] = []

        for dl, dr in options:
            lane = current_lane + dl
            row = current_row + dr
            if lane < 0 or lane >= self.arena.lane_count:
                continue
            if row < 0:
                continue

            score = self._score_move(player, lane, row, dl, dr)
            scored_options.append((score, lane, row, dl, dr))
            if score > best_score:
                best_score = score
                best_lane = lane
                best_row = row

        stall_time = self._player_stall_time(player)
        up_options = [item for item in scored_options if item[3] == 0 and item[4] == 1]
        if stall_time >= self.stall_force_move_time and up_options:
            up_best = max(up_options, key=lambda item: item[0])
            if up_best[0] > -1000.0:
                return up_best[1], up_best[2]

        if stall_time >= self.stall_force_move_time and (best_lane == current_lane and best_row == current_row):
            non_wait = [
                item for item in scored_options
                if not (item[3] == 0 and item[4] == 0)
            ]
            non_wait.sort(key=lambda item: item[0], reverse=True)
            for score, lane, row, _, _ in non_wait:
                # Avoid instantly suicidal forced moves when a safer reroute exists.
                if score > -1000.0:
                    return lane, row
            if stall_time >= self.stall_hard_force_time and non_wait:
                return non_wait[0][1], non_wait[0][2]

        return best_lane, best_row

    def update(self, dt: float):
        if self.game_over or self.phase != "playing":
            return

        dt = min(dt, config.MAX_DELTA_TIME)
        if config.EXPORT_VIDEO:
            dt *= config.EXPORT_TIME_SCALE

        self.game_time += dt

        self._update_camera(dt)
        self._maintain_rows()
        self._update_rows(dt)

        alive_players = [player for player in self.players if player.alive]

        for player in alive_players:
            self._apply_environment(player, dt)

        for player in alive_players:
            if not player.alive:
                continue
            if player.can_move(self.game_time):
                lane, row = self._choose_move(player)
                player.apply_move(lane, row, self.arena, self.game_time)

        for player in alive_players:
            if not player.alive:
                continue
            self._apply_environment(player, 0.0)
            if player.alive:
                previous_max = player.max_row
                player.max_row = max(player.max_row, player.grid_row)
                if player.max_row > previous_max:
                    player.last_progress_time = self.game_time

        for player in self.players:
            if not player.alive:
                player.update_fade()

        alive_count = sum(1 for player in self.players if player.alive)
        if alive_count <= 1 or self.game_time >= self.max_game_time:
            self._finish_game()

    def _finish_game(self):
        if self.game_over:
            return

        for player in self.players:
            if player.alive and player.survival_time <= 0:
                player.survival_time = self.game_time

        sorted_players = sorted(
            self.players,
            key=lambda p: (-p.progress_score(self.start_row), p.username),
        )

        self.finish_game(sorted_players)

    def _apply_tied_placements(self, sorted_players: List[CrossyFollower]):
        placement = 1
        last_progress = None

        for idx, player in enumerate(sorted_players):
            progress = player.progress_score(self.start_row)
            if last_progress is None:
                placement = 1
            elif progress != last_progress:
                placement = idx + 1
            player.placement = placement
            last_progress = progress

    def finish_game(self, sorted_players: List[CrossyFollower]):
        self.game_over = True
        self.phase = "finished"

        self._apply_tied_placements(sorted_players)

        if sorted_players:
            self.winner = sorted_players[0]

        print("\n" + "=" * 60)
        print("  GAME COMPLETE")
        print("=" * 60)

        print("\nTop 10:")
        for idx, player in enumerate(sorted_players[:10], start=1):
            progress = player.progress_score(self.start_row)
            print(f"{idx}. {player.username} ({progress} rows)")

        self._calculate_and_save_scores(sorted_players)

    def render(self):
        alive_count = sum(1 for player in self.players if player.alive)
        highest_progress = 0
        if self.players:
            highest_progress = max(player.progress_score(self.start_row) for player in self.players)

        visible_top = max(0, int(math.floor(self.camera_row)) - 2)
        visible_bottom = int(math.ceil(self.camera_row + (self.arena.height / max(1.0, self.arena.row_height)))) + 3
        visible_rows = [row for idx, row in self.rows.items() if visible_top <= idx <= visible_bottom]
        visible_rows.sort(key=lambda row: row.index)

        global_day = int(getattr(config, "DAY_NUMBER", 1))
        day_offset = int(
            getattr(
                config,
                "CROSSY_FOLLOWERS_DAY_OFFSET",
                getattr(config, "JETPACK_FOLLOWERS_DAY_OFFSET", getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71)),
            )
        )
        club_day = max(1, global_day - day_offset)

        game_state = {
            "phase": self.phase,
            "rows": visible_rows,
            "camera_row": self.camera_row,
            "row_height": self.arena.row_height,
            "alive_count": alive_count,
            "elapsed_time": self.game_time,
            "leader_progress": highest_progress,
            "highscore": self.statistics.get_game_highscore("crossy_followers"),
            "recent_eliminations": self.recent_eliminations,
            "show_leaderboards": self.show_leaderboards,
            "current_game_leaderboard": self.current_game_leaderboard,
            "all_time_leaderboard": self.all_time_leaderboard,
            "winner": self.winner,
            "club_spotlight": self.club_spotlight,
            "club_day_number": club_day,
            "global_day_number": global_day,
        }

        self.renderer.render_frame(self.players, game_state)
        pygame.display.flip()
        self.recorder.capture_frame(self.screen)

    def _calculate_and_save_scores(self, sorted_players: List[CrossyFollower]):
        print("\nCalculating scores...")

        total_participants = len(self.players)
        game_results = []
        game_history_results = []

        game_type = "crossy_followers"
        game_display_name = "Crossy Followers"
        day_number = getattr(config, "DAY_NUMBER", 1)

        for player in sorted_players:
            placement = player.placement
            games_played = self.statistics.get_games_played(player.username)
            survival_time = getattr(player, "survival_time", 0.0)
            progress = player.progress_score(self.start_row)

            points_breakdown = self.scoring.calculate_total_points(
                placement=placement,
                total_participants=total_participants,
                survival_time=survival_time,
                games_played=games_played,
            )
            points = points_breakdown["total_points"]

            self.statistics.update_player_stats(
                username=player.username,
                placement=placement,
                points_earned=points,
                survival_time=survival_time,
                total_participants=total_participants,
                game_type=game_type,
                game_id="",
            )

            game_results.append((player.username, placement, points, progress))
            game_history_results.append(
                {
                    "username": player.username,
                    "placement": placement,
                    "points": points,
                    "survival_time": survival_time,
                    "kills": 0,
                    "damage": 0.0,
                }
            )

        self.game_history.record_game_session(
            game_type=game_type,
            game_display_name=game_display_name,
            day_number=day_number,
            results=game_history_results,
        )

        if sorted_players:
            top = sorted_players[0]
            self.statistics.update_game_highscore(
                game_type=game_type,
                score=int(top.progress_score(self.start_row)),
                username=top.username,
                label="Rows",
            )

        self.statistics.save_statistics()

        if not config.TEST_MODE and getattr(config, "AUTO_PUSH_STATS", False):
            auto_push.push_stats_to_github()

        self.current_game_leaderboard = self.statistics.get_current_game_leaderboard(game_results)
        self.all_time_leaderboard = []
        self.show_leaderboards = True
        self.leaderboard_display_start = time.time()
