import pygame

import config

from .level_data import (
    LEVEL_HEIGHT,
    LEVEL_WIDTH,
    GROUND_Y,
    FLAG_X,
    GROUND_RECTS,
    PIPE_RECTS,
    STEP_RECTS,
    BRICK_SIZE,
    BRICK_TILE_POSITIONS,
    COIN_BOX_TILE_POSITIONS,
    BRICK_CONTENTS,
    COIN_BOX_CONTENTS,
    MOVING_PLATFORMS,
    SOURCE_TILEMAP_PATH,
    SOURCE_MAP_WIDTH,
    SOURCE_MAP_HEIGHT,
    SOURCE_TILE_SIZE,
    SOURCE_SOLID_PIXEL_THRESHOLD,
    SOURCE_NON_BLACK_THRESHOLD,
)


class SuperFollowerBrosLevel:
    def __init__(self, arena_height: float = None):
        target_height = arena_height or getattr(
            config,
            "SUPER_FOLLOWER_BROS_ARENA_RECT",
            config.FIGHTER_ARENA_RECT,
        )[3]
        self.scale = float(target_height) / float(LEVEL_HEIGHT)
        self.vertical_offset = float(getattr(config, "SUPER_FOLLOWER_BROS_1_2_VERTICAL_OFFSET", 0.0))

        self.source_tile_size = max(
            1,
            int(getattr(config, "SUPER_FOLLOWER_BROS_1_2_SOURCE_TILE_SIZE", SOURCE_TILE_SIZE)),
        )
        self.source_solid_pixel_threshold = max(
            1,
            int(
                getattr(
                    config,
                    "SUPER_FOLLOWER_BROS_1_2_SOURCE_SOLID_PIXEL_THRESHOLD",
                    SOURCE_SOLID_PIXEL_THRESHOLD,
                )
            ),
        )
        self.source_non_black_threshold = max(
            0,
            int(
                getattr(
                    config,
                    "SUPER_FOLLOWER_BROS_1_2_SOURCE_NON_BLACK_THRESHOLD",
                    SOURCE_NON_BLACK_THRESHOLD,
                )
            ),
        )
        self._source_art_path = getattr(
            config,
            "SUPER_FOLLOWER_BROS_1_2_COLLISION_ART_PATH",
            SOURCE_TILEMAP_PATH,
        )
        self._source_art = None
        self._source_art_size = (int(SOURCE_MAP_WIDTH), int(SOURCE_MAP_HEIGHT))
        self._load_collision_art()

        source_w = max(1, self._source_art_size[0])
        source_h = max(1, self._source_art_size[1])
        self.source_to_design_x = float(LEVEL_WIDTH) / float(source_w)
        self.source_to_design_y = float(LEVEL_HEIGHT) / float(source_h)

        self.solid_rects = []
        self.static_solid_rects = []
        self.moving_platforms = []
        self._moving_platform_rect_ids = set()
        self.blocks = []
        self.block_rect_map = {}
        self._build_colliders()

        self.pixel_height = int(round(target_height))
        self.pixel_width = int(round(float(LEVEL_WIDTH) * self.scale))
        self.ground_y = (float(GROUND_Y) + self.vertical_offset) * self.scale
        self.flag_x = float(FLAG_X) * self.scale
        self.brick_size = float(BRICK_SIZE) * self.scale

    def _scale_rect(self, rect):
        x, y, w, h = rect
        return pygame.Rect(
            int(round(x * self.scale)),
            int(round((y + self.vertical_offset) * self.scale)),
            max(1, int(round(w * self.scale))),
            max(1, int(round(h * self.scale))),
        )

    def _source_rect_to_scaled_rect(self, x: float, y: float, w: float, h: float) -> pygame.Rect:
        design_x = x * self.source_to_design_x
        design_y = y * self.source_to_design_y
        design_w = w * self.source_to_design_x
        design_h = h * self.source_to_design_y
        return self._scale_rect((design_x, design_y, design_w, design_h))

    def _tile_to_scaled_rect(self, tx: int, ty: int) -> pygame.Rect:
        return self._source_rect_to_scaled_rect(
            float(tx * self.source_tile_size),
            float(ty * self.source_tile_size),
            float(self.source_tile_size),
            float(self.source_tile_size),
        )

    def _build_colliders(self):
        self._build_static_colliders_from_tilemap()
        self.static_solid_rects = list(self.solid_rects)

        for platform in MOVING_PLATFORMS:
            width = max(1, int(round(float(platform.get("width", BRICK_SIZE)) * self.scale)))
            height = max(1, int(round(float(platform.get("height", BRICK_SIZE)) * self.scale)))
            center_x = float(platform.get("x", 0.0)) * self.scale
            y_min = (float(platform.get("y_min", 0.0)) + self.vertical_offset) * self.scale
            y_max = (float(platform.get("y_max", 0.0)) + self.vertical_offset) * self.scale
            if y_max < y_min:
                y_min, y_max = y_max, y_min

            start_y = (float(platform.get("start_y", platform.get("y_max", 0.0))) + self.vertical_offset) * self.scale
            start_y = max(y_min, min(y_max, start_y))

            rect = pygame.Rect(
                int(round(center_x - width / 2.0)),
                int(round(start_y)),
                width,
                height,
            )
            self.moving_platforms.append(
                {
                    "rect": rect,
                    "center_x": center_x,
                    "y_min": y_min,
                    "y_max": y_max,
                    "speed": float(platform.get("speed", 64.0)) * self.scale,
                    "dir": float(platform.get("dir", -1.0)),
                    "delta_x": 0.0,
                    "delta_y": 0.0,
                }
            )
            self.solid_rects.append(rect)
            self._moving_platform_rect_ids.add(id(rect))

        for tx, ty in BRICK_TILE_POSITIONS:
            rect = self._tile_to_scaled_rect(tx, ty)
            self.solid_rects.append(rect)
            block = {
                "kind": "brick",
                "rect": rect,
                "contents": BRICK_CONTENTS.get((tx, ty)),
            }
            if block["contents"]:
                block["state"] = "closed"
                block["cooldown_until"] = None
                block["mushroom_toggle"] = False
            else:
                block["state"] = "solid"
            block["index"] = len(self.blocks)
            self.blocks.append(block)
            self.block_rect_map[id(rect)] = block

        for tx, ty in COIN_BOX_TILE_POSITIONS:
            rect = self._tile_to_scaled_rect(tx, ty)
            self.solid_rects.append(rect)
            block = {
                "kind": "coin_box",
                "rect": rect,
                "contents": COIN_BOX_CONTENTS.get((tx, ty), "coin"),
                "state": "closed",
                "cooldown_until": None,
                "mushroom_toggle": False,
            }
            block["index"] = len(self.blocks)
            self.blocks.append(block)
            self.block_rect_map[id(rect)] = block

    def _load_collision_art(self) -> None:
        try:
            surface = pygame.image.load(self._source_art_path)
            self._source_art = surface
            self._source_art_size = surface.get_size()
        except Exception:
            self._source_art = None
            self._source_art_size = (int(SOURCE_MAP_WIDTH), int(SOURCE_MAP_HEIGHT))

    def _build_static_colliders_from_tilemap(self) -> None:
        if self._source_art is None:
            # Safety fallback if tilemap art cannot be loaded.
            for rect in GROUND_RECTS:
                self.solid_rects.append(self._scale_rect(rect))
            for rect in PIPE_RECTS:
                self.solid_rects.append(self._scale_rect(rect))
            for rect in STEP_RECTS:
                self.solid_rects.append(self._scale_rect(rect))
            return

        src_w, src_h = self._source_art_size
        tile = self.source_tile_size
        cols = max(1, src_w // tile)
        rows = max(1, src_h // tile)

        for ty in range(rows):
            run_start = None
            for tx in range(cols + 1):
                solid = False
                if tx < cols:
                    x0 = tx * tile
                    y0 = ty * tile
                    non_black = 0
                    for sy in range(y0, y0 + tile):
                        for sx in range(x0, x0 + tile):
                            color = self._source_art.get_at((sx, sy))
                            if color.a <= 0:
                                continue
                            if (int(color.r) + int(color.g) + int(color.b)) > self.source_non_black_threshold:
                                non_black += 1
                    solid = non_black >= self.source_solid_pixel_threshold

                if solid and run_start is None:
                    run_start = tx
                elif (not solid) and run_start is not None:
                    x = run_start * tile
                    y = ty * tile
                    w = (tx - run_start) * tile
                    rect = self._source_rect_to_scaled_rect(float(x), float(y), float(w), float(tile))
                    if rect.width > 0 and rect.height > 0:
                        self.solid_rects.append(rect)
                    run_start = None

    def is_solid_at(self, x: float, y: float) -> bool:
        if x < 0 or y < 0:
            return False
        point = pygame.Rect(int(x), int(y), 1, 1)
        for rect in self.solid_rects:
            if rect.colliderect(point):
                return True
        return False

    def iter_solid_tiles(self, rect: pygame.Rect):
        for solid in self.solid_rects:
            if rect.colliderect(solid):
                yield solid

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

            rect.x = int(round(platform["center_x"] - rect.width / 2.0))
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
