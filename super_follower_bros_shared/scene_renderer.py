from __future__ import annotations

import math

import pygame

import config
from super_follower_bros_1_2.renderer import SuperFollowerBrosRenderer as _BaseRenderer

from .scene_parser import HAZARD_SCENE_TILES, TILE_SIZE


class SuperFollowerBrosSceneRenderer(_BaseRenderer):
    def __init__(self, screen: pygame.Surface, subtitle: str, world_label: str):
        super().__init__(screen)
        self.GAME_SUBTITLE = subtitle
        self._world_label = world_label
        self.background_path = ""
        self._level_surface = None
        self._level_surface_key = None
        self._minimap_source_key = None

    def _theme_palette_y(self, level) -> int:
        theme = str(getattr(level, "theme", "Overworld")).strip().lower()
        if theme == "underground":
            return 96
        if theme == "castle":
            return 64
        if theme == "underwater":
            return 32
        return 0

    def _theme_bg_color(self, level) -> tuple[int, int, int]:
        theme = str(getattr(level, "theme", "Overworld")).strip().lower()
        if theme == "underground":
            return (17, 18, 62)
        if theme == "castle":
            return (10, 10, 12)
        if theme == "underwater":
            return (46, 87, 151)
        return (92, 148, 252)

    def _slice_tile(self, sheet: pygame.Surface, atlas_x: int, atlas_y: int, tile_px: int):
        source_x = atlas_x * TILE_SIZE
        source_y = atlas_y * TILE_SIZE
        if source_x < 0 or source_y < 0:
            return None
        if source_x + TILE_SIZE > sheet.get_width() or source_y + TILE_SIZE > sheet.get_height():
            return None
        image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        image.blit(sheet, (0, 0), (source_x, source_y, TILE_SIZE, TILE_SIZE))
        if tile_px != TILE_SIZE:
            image = pygame.transform.scale(image, (tile_px, tile_px))
        return image

    def _build_level_surface(self, level):
        if level is None:
            return None
        target_size = (int(level.pixel_width), int(level.pixel_height))
        length_to_world = getattr(level, "scene_length_to_world", None)
        if callable(length_to_world):
            tile_px = max(1, int(round(float(length_to_world(float(TILE_SIZE))))))
        else:
            tile_px = max(1, int(round(TILE_SIZE * float(getattr(level, "scale", 1.0)))))
        theme_row_offset = int(self._theme_palette_y(level) // TILE_SIZE)
        cache_key = (
            target_size,
            tile_px,
            float(getattr(level, "scene_unit_scale", 1.0)),
            float(getattr(level, "scene_origin_x", 0.0)),
            float(getattr(level, "scene_origin_y", 0.0)),
            float(getattr(level, "scale", 1.0)),
            str(getattr(level, "theme", "")),
            len(getattr(level, "render_tiles", ()) or ()),
        )
        if self._level_surface is not None and self._level_surface_key == cache_key:
            return self._level_surface

        surface = pygame.Surface(target_size).convert()
        surface.fill(self._theme_bg_color(level))

        sheet = self._load_tileset_sheet()
        x_to_world = getattr(level, "scene_x_to_world", None)
        y_to_world = getattr(level, "scene_y_to_world", None)
        for cell in getattr(level, "render_tiles", ()) or ():
            source_id = int(getattr(cell, "source_id", 0))
            tile_id = int(getattr(cell, "tile_id", 0))
            if callable(x_to_world):
                x = int(round(float(x_to_world(float(getattr(cell, "x", 0.0))))))
            else:
                x = int(round(float(getattr(cell, "x", 0.0)) * float(level.scale)))
            if callable(y_to_world):
                y = int(round(float(y_to_world(float(getattr(cell, "y", 0.0))))))
            else:
                y = int(round(float(getattr(cell, "y", 0.0)) * float(level.scale)))

            if x + tile_px < 0 or y + tile_px < 0 or x >= target_size[0] or y >= target_size[1]:
                continue

            if source_id == 1:
                if tile_id in HAZARD_SCENE_TILES:
                    pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(x, y, tile_px, tile_px))
                continue

            # The external SMB scenes use additional tile sources for helper/deco layers.
            # Keep only the core terrain source here to avoid rendering collision/helper tiles.
            if source_id != 0:
                continue

            tile_image = None
            if sheet is not None:
                tile_image = self._slice_tile(
                    sheet,
                    int(getattr(cell, "atlas_x", 0)),
                    int(getattr(cell, "atlas_y", 0)) + theme_row_offset,
                    tile_px,
                )

            if tile_image is not None:
                surface.blit(tile_image, (x, y))
                continue

            fallback_color = (36, 36, 40)
            if source_id in (0, 6):
                fallback_color = (18, 157, 178)
            elif source_id in (4, 5):
                fallback_color = (143, 102, 49)
            elif source_id == 2:
                fallback_color = (40, 88, 170)
            elif source_id == 3:
                fallback_color = (28, 28, 32)
            pygame.draw.rect(surface, fallback_color, pygame.Rect(x, y, tile_px, tile_px))

        self._level_surface = surface
        self._level_surface_key = cache_key
        self._minimap_source_key = None
        return self._level_surface

    def _draw_level(self, level, camera_x: float):
        surface = self._build_level_surface(level)
        if surface is None:
            arena_rect = pygame.Rect(
                self.game_left,
                self.game_top,
                self.game_right - self.game_left,
                self.game_bottom - self.game_top,
            )
            pygame.draw.rect(self.screen, self.sky_color, arena_rect)
            return
        self.screen.blit(surface, (self.game_left - camera_x, self.game_top))

    def _get_minimap_background(self, map_w: int, map_h: int):
        target_size = (int(map_w), int(map_h))
        source = self._level_surface
        source_key = self._level_surface_key
        if source is None:
            return None
        if (
            self._minimap_surface is not None
            and self._minimap_size == target_size
            and self._minimap_source_key == source_key
        ):
            return self._minimap_surface
        try:
            self._minimap_surface = pygame.transform.scale(source, target_size)
            self._minimap_size = target_size
            self._minimap_source_key = source_key
        except Exception:
            self._minimap_surface = None
            self._minimap_size = None
            self._minimap_source_key = None
        return self._minimap_surface

    def _get_tileset_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        theme_y = self._theme_palette_y(level)
        key = (scale, theme_y)
        if self._tileset_frames is not None and self._tileset_scale == key:
            return self._tileset_frames

        sheet = self._load_tileset_sheet()
        if sheet is None:
            self._tileset_frames = None
            self._tileset_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        brick_frame = slice_frame(16, theme_y, 16, 16)
        open_frame = slice_frame(432, theme_y + 16, 16, 16)
        question_frames = [
            slice_frame(384, theme_y, 16, 16),
            slice_frame(400, theme_y, 16, 16),
            slice_frame(416, theme_y, 16, 16),
        ]

        self._tileset_frames = {
            "brick": brick_frame,
            "open": open_frame,
            "question": question_frames,
        }
        self._tileset_scale = key
        return self._tileset_frames

    def _get_moving_platform_frames(self, level):
        if level is None:
            return None
        scale_multiplier = float(getattr(config, "SUPER_FOLLOWER_BROS_TILESET_SCALE", 2.69))
        scale = scale_multiplier * float(getattr(level, "scale", 1.0))
        if scale <= 0:
            return None
        theme_y = self._theme_palette_y(level)
        key = (scale, theme_y)
        if self._moving_platform_frames is not None and self._moving_platform_scale == key:
            return self._moving_platform_frames

        sheet = self._load_tileset_sheet()
        if sheet is None:
            self._moving_platform_frames = None
            self._moving_platform_scale = None
            return None

        def slice_frame(x, y, w, h):
            image = pygame.Surface((w, h), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, w, h))
            if scale != 1.0:
                image = pygame.transform.scale(
                    image,
                    (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                )
            return image

        left = slice_frame(16, theme_y, 16, 16)
        middle = slice_frame(16, theme_y, 16, 16)
        right = slice_frame(16, theme_y, 16, 16)
        self._moving_platform_frames = {"left": left, "middle": middle, "right": right}
        self._moving_platform_scale = key
        return self._moving_platform_frames

    def _draw_flag(self, level, camera_x: float):
        if level is None or not hasattr(level, "flag_x"):
            return
        margin = int(getattr(config, "SUPER_FOLLOWER_BROS_RENDER_MARGIN", 140))
        pole_color = getattr(config, "SUPER_FOLLOWER_BROS_FLAG_POLE_COLOR", (245, 245, 245))
        flag_color = getattr(config, "SUPER_FOLLOWER_BROS_FLAG_COLOR", (248, 216, 48))
        pole_width = float(getattr(config, "SUPER_FOLLOWER_BROS_FLAG_POLE_WIDTH", 4.0)) * float(getattr(level, "scale", 1.0))
        pole_height = float(getattr(config, "SUPER_FOLLOWER_BROS_FLAG_HEIGHT", 170.0)) * float(getattr(level, "scale", 1.0))
        flag_width = float(getattr(config, "SUPER_FOLLOWER_BROS_FLAG_WIDTH", 18.0)) * float(getattr(level, "scale", 1.0))

        pole_x = self.game_left + level.flag_x - camera_x
        block_height = float(getattr(level, "brick_size", 0.0))
        base_y = self.game_top + level.ground_y - block_height
        top_y = base_y - pole_height

        if pole_x < self.game_left - margin or pole_x > self.game_right + margin:
            return

        pole_rect = pygame.Rect(
            int(pole_x - pole_width * 0.5),
            int(top_y),
            max(1, int(pole_width)),
            max(1, int(pole_height)),
        )
        pygame.draw.rect(self.screen, pole_color, pole_rect)

        flag_rect = pygame.Rect(
            int(pole_rect.left - flag_width),
            int(top_y + pole_height * 0.15),
            max(1, int(flag_width)),
            max(1, int(pole_height * 0.18)),
        )
        pygame.draw.rect(self.screen, flag_color, flag_rect)

    def _draw_game_ui(self, players, game_state: dict):
        elapsed = game_state.get("elapsed_time")
        if elapsed is None:
            return

        world_label = str(game_state.get("world_label") or self._world_label)
        time_limit = int(getattr(config, "SUPER_FOLLOWER_BROS_TIME_LIMIT", 400))
        remaining = max(0, time_limit - int(elapsed))

        panel_x = self.game_left + 12
        panel_y = self.game_top + 8
        world_surface = self.font_small.render(f"WORLD {world_label}", True, (255, 255, 255))
        time_surface = self.font_small.render(f"TIME {remaining:03d}", True, (255, 255, 255))
        self.screen.blit(world_surface, (panel_x, panel_y))
        self.screen.blit(time_surface, (panel_x, panel_y + 18))
