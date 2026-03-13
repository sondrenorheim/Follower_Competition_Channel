from __future__ import annotations

from collections import defaultdict

import pygame

import config
from .scene_parser import ParsedSmbLevel, SCENE_TILE_BLOCKS, TILE_SIZE, TileCell


class SuperFollowerBrosSceneLevel:
    def __init__(self, parsed_level: ParsedSmbLevel, arena_height: float | None = None):
        self.parsed = parsed_level
        self.theme = parsed_level.theme
        self.world_label = parsed_level.world_label
        self.subtitle = parsed_level.subtitle

        target_height = arena_height or getattr(
            config,
            "SUPER_FOLLOWER_BROS_ARENA_RECT",
            config.FIGHTER_ARENA_RECT,
        )[3]
        self.scene_unit_scale = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
        if self.scene_unit_scale <= 0:
            self.scene_unit_scale = 1.0
        self.scene_origin_x = 0.0
        self.scene_origin_y = self._detect_scene_origin_y()
        self.design_height = max(
            float(TILE_SIZE),
            float(getattr(config, "SUPER_FOLLOWER_BROS_SCENE_DESIGN_HEIGHT", 600.0)),
        )
        self.scale = float(target_height) / float(self.design_height)
        self.vertical_offset = 0.0

        scene_width = max(float(TILE_SIZE), float(parsed_level.width))
        scene_width = max(scene_width, float(parsed_level.finish_x) + float(TILE_SIZE))
        if parsed_level.camera_right_limit is not None:
            scene_width = max(scene_width, float(parsed_level.camera_right_limit) + float(TILE_SIZE))
        self.design_width = self._scene_len_to_design(scene_width)

        self.pixel_width = int(round(self._scene_len_to_world(scene_width)))
        self.pixel_height = int(round(target_height))
        self.flag_x = self.scene_x_to_world(float(parsed_level.finish_x))
        self.start_x = self.scene_x_to_world(float(parsed_level.start_x))
        self.start_y = self.scene_y_to_world(float(parsed_level.start_y))
        self.camera_right_limit = (
            self.scene_x_to_world(float(parsed_level.camera_right_limit))
            if parsed_level.camera_right_limit is not None
            else None
        )

        self.solid_rects: list[pygame.Rect] = []
        self.static_solid_rects: list[pygame.Rect] = []
        self.moving_platforms: list[dict] = []
        self._moving_platform_rect_ids: set[int] = set()
        self.blocks: list[dict] = []
        self.block_rect_map: dict[int, dict] = {}
        self.hazard_rects: list[pygame.Rect] = []

        self.render_tiles: tuple[TileCell, ...] = parsed_level.render_tiles
        self.enemy_spawns = [
            {
                "x": self.scene_x_to_world(float(spawn.x)),
                "y": self.scene_y_to_world(float(spawn.y)),
                "kind": spawn.kind,
            }
            for spawn in parsed_level.enemies
        ]
        self.checkpoint_points = [
            {
                "x": self.scene_x_to_world(float(point.x)),
                "y": self.scene_y_to_world(float(point.y)),
            }
            for point in parsed_level.checkpoints
        ]
        self.checkpoint_flag_points = [
            {
                "x": self.scene_x_to_world(float(point.x)),
                "y": self.scene_y_to_world(float(point.y)),
            }
            for point in parsed_level.checkpoint_flags
        ]

        self._build_colliders()
        self.ground_y = self._estimate_ground_y()
        self.brick_size = max(1.0, self._scene_len_to_world(float(TILE_SIZE)))

    def _detect_scene_origin_y(self) -> float:
        source0_tiles = [cell for cell in self.parsed.render_tiles if int(cell.source_id) == 0]
        if source0_tiles:
            return float(min(cell.y for cell in source0_tiles))
        if self.parsed.render_tiles:
            return float(min(cell.y for cell in self.parsed.render_tiles))
        return 0.0

    def _scene_len_to_design(self, value: float) -> float:
        return float(value) * self.scene_unit_scale

    def _scene_len_to_world(self, value: float) -> float:
        return float(value) * self.scene_unit_scale * self.scale

    def scene_x_to_world(self, x: float) -> float:
        return (float(x) - self.scene_origin_x) * self.scene_unit_scale * self.scale

    def scene_y_to_world(self, y: float) -> float:
        y_units = float(y) - self.scene_origin_y + self.vertical_offset
        return y_units * self.scene_unit_scale * self.scale

    def scene_length_to_world(self, length: float) -> float:
        return self._scene_len_to_world(length)

    def _build_colliders(self) -> None:
        self._build_static_solid_rects()
        self.static_solid_rects = list(self.solid_rects)
        self._build_blocks()
        self._build_hazards()
        self._build_moving_platforms()

    def _build_static_solid_rects(self) -> None:
        rows: dict[int, list[int]] = defaultdict(list)
        for cell in self.parsed.solid_tiles:
            rows[int(cell.y)].append(int(cell.x))

        for y, xs in rows.items():
            sorted_x = sorted(set(xs))
            if not sorted_x:
                continue
            run_start = sorted_x[0]
            run_end = sorted_x[0]
            for x in sorted_x[1:]:
                if x == run_end + TILE_SIZE:
                    run_end = x
                    continue
                self.solid_rects.append(self._scene_rect_to_scaled(run_start, y, run_end - run_start + TILE_SIZE, TILE_SIZE))
                run_start = x
                run_end = x
            self.solid_rects.append(self._scene_rect_to_scaled(run_start, y, run_end - run_start + TILE_SIZE, TILE_SIZE))

    def _build_blocks(self) -> None:
        seen: set[tuple[int, int]] = set()
        for cell in sorted(self.parsed.block_tiles, key=lambda tile: (tile.y, tile.x)):
            key = (int(cell.x), int(cell.y))
            if key in seen:
                continue
            seen.add(key)

            kind, contents = SCENE_TILE_BLOCKS.get(cell.tile_id, ("brick", None))
            rect = self._scene_rect_to_scaled(cell.x, cell.y, TILE_SIZE, TILE_SIZE)
            block = {
                "kind": kind,
                "rect": rect,
                "contents": contents,
                "state": "closed" if contents is not None else "solid",
                "cooldown_until": None,
                "mushroom_toggle": False,
                "index": len(self.blocks),
            }
            self.blocks.append(block)
            self.block_rect_map[id(rect)] = block
            if rect not in self.solid_rects:
                self.solid_rects.append(rect)

    def _build_hazards(self) -> None:
        seen: set[tuple[int, int]] = set()
        for cell in self.parsed.hazard_tiles:
            key = (int(cell.x), int(cell.y))
            if key in seen:
                continue
            seen.add(key)
            self.hazard_rects.append(self._scene_rect_to_scaled(cell.x, cell.y, TILE_SIZE, TILE_SIZE))

    def _build_moving_platforms(self) -> None:
        for platform in self.parsed.moving_platforms:
            width = max(1, int(round(self._scene_len_to_world(float(platform.width)))))
            height = max(1, int(round(self._scene_len_to_world(float(platform.height)))))
            center_x = self.scene_x_to_world(float(platform.x))
            y_min = self.scene_y_to_world(float(platform.y_min))
            y_max = self.scene_y_to_world(float(platform.y_max))
            if y_max < y_min:
                y_min, y_max = y_max, y_min
            start_y = min(y_max, max(y_min, self.scene_y_to_world(float(platform.start_y))))

            rect = pygame.Rect(
                int(round(center_x - width * 0.5)),
                int(round(start_y)),
                width,
                height,
            )
            entry = {
                "rect": rect,
                "center_x": center_x,
                "y_min": y_min,
                "y_max": y_max,
                "speed": self._scene_len_to_world(float(platform.speed)),
                "dir": float(platform.direction),
                "delta_x": 0.0,
                "delta_y": 0.0,
            }
            self.moving_platforms.append(entry)
            self.solid_rects.append(rect)
            self._moving_platform_rect_ids.add(id(rect))

    def _estimate_ground_y(self) -> float:
        if not self.static_solid_rects:
            return float(self.pixel_height) - self._scene_len_to_world(float(TILE_SIZE))
        max_bottom = max(rect.bottom for rect in self.static_solid_rects)
        return min(float(self.pixel_height), float(max_bottom))

    def _scene_rect_to_scaled(self, x: float, y: float, w: float, h: float) -> pygame.Rect:
        return pygame.Rect(
            int(round(self.scene_x_to_world(float(x)))),
            int(round(self.scene_y_to_world(float(y)))),
            max(1, int(round(self._scene_len_to_world(float(w))))),
            max(1, int(round(self._scene_len_to_world(float(h))))),
        )

    def is_solid_at(self, x: float, y: float) -> bool:
        if x < 0 or y < 0:
            return False
        point = pygame.Rect(int(x), int(y), 1, 1)
        return any(rect.colliderect(point) for rect in self.solid_rects)

    def iter_solid_tiles(self, rect: pygame.Rect):
        for solid in self.solid_rects:
            if rect.colliderect(solid):
                yield solid

    def collides_hazard(self, rect: pygame.Rect) -> bool:
        for hazard in self.hazard_rects:
            if rect.colliderect(hazard):
                return True
        return False

    def update(self, dt: float) -> None:
        if not self.moving_platforms:
            return

        dt = max(0.0, float(dt))
        for platform in self.moving_platforms:
            rect = platform["rect"]
            old_x = rect.x
            old_y = rect.y

            travel = platform["speed"] * dt
            next_y = float(rect.y) + travel * platform["dir"]
            hit_min = next_y <= platform["y_min"]
            hit_max = next_y >= platform["y_max"]
            if hit_min:
                next_y = platform["y_min"]
                platform["dir"] = 1.0
            elif hit_max:
                next_y = platform["y_max"]
                platform["dir"] = -1.0

            rect.x = int(round(platform["center_x"] - rect.width * 0.5))
            rect.y = int(round(next_y))
            platform["delta_x"] = float(rect.x - old_x)
            platform["delta_y"] = float(rect.y - old_y)

    def get_platform_motion_for_entity(self, entity_rect: pygame.Rect):
        if entity_rect is None:
            return 0.0, 0.0

        foot_y = entity_rect.bottom
        for platform in self.moving_platforms:
            rect = platform["rect"]
            if platform["delta_x"] == 0.0 and platform["delta_y"] == 0.0:
                continue
            x_overlap = entity_rect.right > rect.left and entity_rect.left < rect.right
            close_to_top = abs(foot_y - rect.top) <= 4
            if x_overlap and close_to_top:
                return platform["delta_x"], platform["delta_y"]
        return 0.0, 0.0

    def is_moving_platform_rect(self, rect: pygame.Rect) -> bool:
        if rect is None:
            return False
        return id(rect) in self._moving_platform_rect_ids

    def get_block_for_rect(self, rect: pygame.Rect):
        return self.block_rect_map.get(id(rect))
