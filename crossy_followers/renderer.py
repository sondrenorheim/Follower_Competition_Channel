import math
from typing import Dict, List, Optional, Tuple

import pygame

import config
from shared import RendererTemplate


class CrossyFollowersRenderer(RendererTemplate):
    GAME_TITLE = "CROSSY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers cross every day"
    PLAYER_LABEL = "followers"
    GAME_WIDTH = getattr(config, "CROSSY_ARENA_RECT", getattr(config, "DOODLE_ARENA_RECT", (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)))[2]
    GAME_HEIGHT = getattr(config, "CROSSY_ARENA_RECT", getattr(config, "DOODLE_ARENA_RECT", (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)))[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "CROSSY_ARENA_RECT",
            getattr(config, "DOODLE_ARENA_RECT", (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)),
        )
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.bg_color = getattr(config, "CROSSY_BG_COLOR", (164, 197, 226))
        self.day_counter_offset = int(getattr(config, "CROSSY_DAY_COUNTER_OFFSET", 60))
        self.player_size = float(getattr(config, "CROSSY_PLAYER_SIZE", 30.0))

        self.elimination_list_size = int(getattr(config, "CROSSY_ELIMINATION_LIST_SIZE", 6))
        elimination_text_size = int(getattr(config, "CROSSY_ELIMINATION_TEXT_SIZE", 18))
        self.elimination_text_size = max(12, elimination_text_size)
        self.elimination_name_length = int(getattr(config, "CROSSY_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "CROSSY_ELIMINATION_LABEL", "Eliminated:"))
        self.elimination_list_x_offset = int(getattr(config, "CROSSY_ELIMINATION_LIST_X_OFFSET", 0))
        self.font_eliminations = pygame.font.Font(None, self.elimination_text_size)

        self._camera_row = 0.0
        self._row_height = float(getattr(config, "CROSSY_ROW_HEIGHT", 56.0))
        self.lane_count = max(5, int(getattr(config, "CROSSY_LANE_COUNT", 9)))
        self.lane_width = (self.game_right - self.game_left) / float(self.lane_count)
        self._visible_row_lookup: Dict[int, object] = {}
        self._tile_offset_cache: Dict[Tuple[int, int, int, int], List[Tuple[float, float]]] = {}

        self._texture_cache: Dict[Tuple[str, int, int], pygame.Surface] = {}
        self._row_textures: Dict[str, Optional[pygame.Surface]] = {}
        self._load_assets()

    def _safe_load_image(self, path: str, alpha: bool = True) -> Optional[pygame.Surface]:
        try:
            image = pygame.image.load(path)
            return image.convert_alpha() if alpha else image.convert()
        except Exception:
            return None

    def _load_assets(self):
        self._row_textures = {
            "grass_light": self._safe_load_image(str(getattr(config, "CROSSY_GRASS_LIGHT_TEXTURE", "assets/crossy_followers/grass_light.png"))),
            "grass_dark": self._safe_load_image(str(getattr(config, "CROSSY_GRASS_DARK_TEXTURE", "assets/crossy_followers/grass_dark.png"))),
            "road_stripes": self._safe_load_image(str(getattr(config, "CROSSY_ROAD_STRIPES_TEXTURE", "assets/crossy_followers/road_stripes.png"))),
            "road_blank": self._safe_load_image(str(getattr(config, "CROSSY_ROAD_BLANK_TEXTURE", "assets/crossy_followers/road_blank.png"))),
            "river": self._safe_load_image(str(getattr(config, "CROSSY_RIVER_TEXTURE", "assets/crossy_followers/river.png"))),
            "railroad": self._safe_load_image(str(getattr(config, "CROSSY_RAILROAD_TEXTURE", "assets/crossy_followers/railroad.png"))),
        }

    def render_frame(self, players, game_state: dict):
        self._camera_row = float(game_state.get("camera_row", 0.0))
        self._row_height = float(game_state.get("row_height", self._row_height))
        self._visible_row_lookup = {
            int(getattr(row, "index", -1)): row
            for row in (game_state.get("rows", []) or [])
        }

        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(players, game_state)

        if game_state.get("show_leaderboards"):
            self._draw_end_game_display(
                game_state.get("current_game_leaderboard", []),
                game_state.get("all_time_leaderboard", []),
                game_state.get("winner"),
            )

    def _draw_title_and_subtitle(self):
        arena_top = self.game_top
        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_y = arena_top + 28
        subtitle_y = arena_top + 54
        if subtitle_y < 80:
            title_y = 130
            subtitle_y = 156
        title_rect = title_text.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title_text, title_rect)

        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, subtitle_y))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_font = pygame.font.Font(None, 24)
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

    def _row_to_screen_rect(self, row_index: int) -> pygame.Rect:
        row_center = self.game_bottom - ((row_index - self._camera_row + 0.5) * self._row_height)
        top = int(round(row_center - self._row_height * 0.5))
        return pygame.Rect(self.game_left, top, int(self.game_right - self.game_left), int(self._row_height) + 1)

    def _entity_screen_rect(self, entity, row_rect: pygame.Rect) -> pygame.Rect:
        width = max(8, int(round(entity.width)))
        if entity.kind == "train":
            height = max(10, int(self._row_height * 0.90))
        elif entity.kind == "car":
            height = max(10, int(self._row_height * 0.72))
        elif entity.kind == "log":
            height = max(10, int(self._row_height * 0.58))
        elif entity.kind == "lily":
            height = max(8, int(self._row_height * 0.48))
        elif entity.kind == "tree":
            height = max(12, int(self._row_height * 0.86))
        elif entity.kind == "boulder":
            height = max(10, int(self._row_height * 0.70))
        else:
            height = max(10, int(self._row_height * 0.70))
        center = (int(round(entity.x)), row_rect.centery + (2 if entity.kind in {"log", "lily"} else 0))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        return rect

    def _get_scaled_texture(self, key: str, source: Optional[pygame.Surface], width: int, height: int) -> Optional[pygame.Surface]:
        if source is None or width <= 0 or height <= 0:
            return None
        cache_key = (key, width, height)
        cached = self._texture_cache.get(cache_key)
        if cached is not None:
            return cached
        scaled = pygame.transform.smoothscale(source, (width, height))
        self._texture_cache[cache_key] = scaled
        return scaled

    def _blit_tiled_texture(self, texture_key: str, texture: Optional[pygame.Surface], rect: pygame.Rect, alpha: int = 255):
        if texture is None:
            return
        tile_h = max(2, rect.height)
        tile_w = max(8, int(tile_h * 1.8))
        tile = self._get_scaled_texture(texture_key, texture, tile_w, tile_h)
        if tile is None:
            return
        if alpha < 255:
            tile = tile.copy()
            tile.set_alpha(alpha)
        x = rect.left
        while x < rect.right:
            self.screen.blit(tile, (x, rect.top))
            x += tile_w

    def _draw_row_background(self, row, rect: pygame.Rect):
        if row.row_type == "grass":
            base = (114, 182, 104) if row.variant == 0 else (94, 164, 90)
            texture_key = "grass_light" if row.variant == 0 else "grass_dark"
            texture = self._row_textures.get(texture_key)
            alpha = 180
        elif row.row_type == "road":
            base = (76, 79, 86) if row.variant == 0 else (70, 73, 80)
            texture_key = "road_stripes" if row.variant == 0 else "road_blank"
            texture = self._row_textures.get(texture_key)
            alpha = 185
        elif row.row_type == "water":
            base = (72, 148, 198) if row.variant == 0 else (62, 136, 184)
            texture_key = "river"
            texture = self._row_textures.get("river")
            alpha = 190
        else:
            base = (122, 122, 126)
            texture_key = "railroad"
            texture = self._row_textures.get("railroad")
            alpha = 195

        pygame.draw.rect(self.screen, base, rect)
        self._blit_tiled_texture(texture_key, texture, rect, alpha=alpha)
        pygame.draw.line(self.screen, (32, 34, 38), (rect.left, rect.top), (rect.right, rect.top), 1)
        pygame.draw.line(self.screen, (32, 34, 38), (rect.left, rect.bottom), (rect.right, rect.bottom), 1)

    def _draw_train(self, entity, rect: pygame.Rect):
        body_rect = rect.inflate(0, -max(2, int(rect.height * 0.1)))
        pygame.draw.rect(self.screen, (188, 58, 58), body_rect, border_radius=max(4, body_rect.height // 6))
        pygame.draw.rect(self.screen, (82, 22, 22), body_rect, 2, border_radius=max(4, body_rect.height // 6))

        stripe_y = body_rect.centery - max(2, body_rect.height // 12)
        stripe_h = max(3, body_rect.height // 6)
        pygame.draw.rect(self.screen, (246, 218, 92), pygame.Rect(body_rect.left + 4, stripe_y, max(2, body_rect.width - 8), stripe_h))

        window_h = max(5, body_rect.height // 5)
        window_w = max(8, body_rect.height // 4)
        gap = max(3, window_w // 3)
        wx = body_rect.left + 6
        while wx + window_w < body_rect.right - 6:
            wrect = pygame.Rect(wx, body_rect.top + 4, window_w, window_h)
            pygame.draw.rect(self.screen, (198, 230, 248), wrect, border_radius=2)
            pygame.draw.rect(self.screen, (70, 90, 110), wrect, 1, border_radius=2)
            wx += window_w + gap

        facing_right = entity.speed > 0
        nose_w = max(8, int(body_rect.height * 0.5))
        if facing_right:
            nose = [
                (body_rect.right, body_rect.top + 2),
                (body_rect.right + nose_w, body_rect.centery),
                (body_rect.right, body_rect.bottom - 2),
            ]
        else:
            nose = [
                (body_rect.left, body_rect.top + 2),
                (body_rect.left - nose_w, body_rect.centery),
                (body_rect.left, body_rect.bottom - 2),
            ]
        pygame.draw.polygon(self.screen, (208, 72, 72), nose)
        pygame.draw.polygon(self.screen, (82, 22, 22), nose, 2)

    def _draw_car(self, entity, rect: pygame.Rect):
        palette = {
            "blue_car": ((84, 152, 228), (32, 70, 112)),
            "green_car": ((88, 184, 106), (36, 92, 48)),
            "orange_car": ((238, 152, 66), (120, 66, 24)),
            "police_car": ((94, 106, 128), (36, 44, 60)),
            "purple_car": ((162, 110, 210), (72, 44, 102)),
            "red_truck": ((210, 92, 92), (92, 34, 34)),
            "blue_truck": ((88, 128, 210), (38, 60, 108)),
            "taxi": ((242, 210, 72), (120, 90, 22)),
        }
        fill, border = palette.get(entity.sprite, ((220, 92, 72), (80, 25, 15)))

        body = rect.inflate(0, -max(2, int(rect.height * 0.16)))
        pygame.draw.rect(self.screen, fill, body, border_radius=max(4, body.height // 4))
        pygame.draw.rect(self.screen, border, body, 2, border_radius=max(4, body.height // 4))

        roof_w = max(8, int(body.width * 0.44))
        roof_h = max(6, int(body.height * 0.45))
        roof = pygame.Rect(0, 0, roof_w, roof_h)
        roof.center = (body.centerx, body.top + roof_h // 2 + 1)
        pygame.draw.rect(self.screen, (208, 232, 246), roof, border_radius=3)
        pygame.draw.rect(self.screen, (88, 104, 122), roof, 1, border_radius=3)

        if entity.sprite == "police_car":
            light_bar = pygame.Rect(0, 0, max(8, roof_w // 3), max(3, roof_h // 3))
            light_bar.center = (roof.centerx, roof.top + 2)
            half_w = max(2, light_bar.width // 2)
            pygame.draw.rect(self.screen, (224, 54, 54), pygame.Rect(light_bar.left, light_bar.top, half_w, light_bar.height))
            pygame.draw.rect(self.screen, (72, 110, 236), pygame.Rect(light_bar.left + half_w, light_bar.top, light_bar.width - half_w, light_bar.height))

        wheel_r = max(2, int(body.height * 0.18))
        wheel_y = body.bottom - max(1, wheel_r // 3)
        pygame.draw.circle(self.screen, (30, 30, 30), (body.left + wheel_r + 2, wheel_y), wheel_r)
        pygame.draw.circle(self.screen, (30, 30, 30), (body.right - wheel_r - 2, wheel_y), wheel_r)

    def _draw_log(self, rect: pygame.Rect):
        pygame.draw.rect(self.screen, (140, 98, 56), rect, border_radius=max(4, rect.height // 3))
        pygame.draw.rect(self.screen, (84, 56, 26), rect, 2, border_radius=max(4, rect.height // 3))
        ring_w = max(4, rect.height // 3)
        left_ring = pygame.Rect(rect.left, rect.top, ring_w, rect.height)
        right_ring = pygame.Rect(rect.right - ring_w, rect.top, ring_w, rect.height)
        pygame.draw.ellipse(self.screen, (176, 132, 84), left_ring)
        pygame.draw.ellipse(self.screen, (176, 132, 84), right_ring)
        pygame.draw.ellipse(self.screen, (94, 66, 34), left_ring, 1)
        pygame.draw.ellipse(self.screen, (94, 66, 34), right_ring, 1)

    def _draw_lily(self, rect: pygame.Rect):
        radius = max(5, min(rect.width, rect.height) // 2)
        center = rect.center
        pygame.draw.circle(self.screen, (94, 194, 112), center, radius)
        pygame.draw.circle(self.screen, (36, 112, 54), center, radius, 2)
        notch = [
            (center[0], center[1]),
            (center[0] + radius, center[1] - max(2, radius // 4)),
            (center[0] + radius, center[1] + max(2, radius // 4)),
        ]
        pygame.draw.polygon(self.screen, (62, 136, 184), notch)

    def _draw_tree(self, rect: pygame.Rect):
        trunk_w = max(4, rect.width // 5)
        trunk_h = max(6, rect.height // 3)
        trunk = pygame.Rect(0, 0, trunk_w, trunk_h)
        trunk.midbottom = (rect.centerx, rect.bottom - 1)
        pygame.draw.rect(self.screen, (116, 82, 44), trunk, border_radius=2)

        canopy_r = max(6, int(rect.height * 0.28))
        c1 = (rect.centerx - canopy_r // 2, rect.top + canopy_r + 1)
        c2 = (rect.centerx + canopy_r // 2, rect.top + canopy_r + 1)
        c3 = (rect.centerx, rect.top + max(4, canopy_r // 2))
        for c in (c1, c2, c3):
            pygame.draw.circle(self.screen, (74, 154, 82), c, canopy_r)
            pygame.draw.circle(self.screen, (32, 92, 40), c, canopy_r, 2)

    def _draw_boulder(self, rect: pygame.Rect):
        blob = rect.inflate(-max(2, rect.width // 8), -max(2, rect.height // 8))
        pygame.draw.ellipse(self.screen, (152, 152, 160), blob)
        pygame.draw.ellipse(self.screen, (82, 82, 88), blob, 2)
        highlight = pygame.Rect(blob.left + blob.width // 5, blob.top + blob.height // 5, max(3, blob.width // 4), max(3, blob.height // 4))
        pygame.draw.ellipse(self.screen, (194, 194, 202), highlight)

    def _draw_entity(self, entity, row_rect: pygame.Rect):
        rect = self._entity_screen_rect(entity, row_rect)

        if entity.kind == "train":
            self._draw_train(entity, rect)
            return

        if entity.kind == "car":
            self._draw_car(entity, rect)
        elif entity.kind == "log":
            self._draw_log(rect)
        elif entity.kind == "lily":
            self._draw_lily(rect)
        elif entity.kind == "tree":
            self._draw_tree(rect)
        elif entity.kind == "boulder":
            self._draw_boulder(rect)
        else:
            pygame.draw.rect(self.screen, (170, 170, 170), rect, border_radius=6)
            pygame.draw.rect(self.screen, (50, 50, 50), rect, 2, border_radius=6)

    def _draw_game_area(self, players, game_state: dict):
        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.bg_color, arena_rect)

        rows = game_state.get("rows", []) or []
        for row in rows:
            rect = self._row_to_screen_rect(row.index)
            if rect.bottom < self.game_top or rect.top > self.game_bottom:
                continue
            self._draw_row_background(row, rect)
            for entity in row.entities:
                self._draw_entity(entity, rect)

    def _row_center_to_screen_y(self, row_index: int) -> float:
        return self.game_bottom - ((row_index - self._camera_row + 0.5) * self._row_height)

    def _draw_avatar_at(self, player, screen_x: int, screen_y: int):
        size = max(1, int(round(self.player_size)))
        avatar_surface = self._get_avatar_surface(player, size)
        if hasattr(player, "alpha") and player.alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(player.alpha)
        rect = avatar_surface.get_rect(center=(screen_x, screen_y))
        self.screen.blit(avatar_surface, rect)

    def _lane_to_screen_x(self, lane_index: int) -> int:
        lane = max(0, min(self.lane_count - 1, int(lane_index)))
        return int(round(self.game_left + (lane + 0.5) * self.lane_width))

    def _player_screen_x(self, player) -> int:
        row = self._visible_row_lookup.get(int(getattr(player, "grid_row", 0)))
        if row is not None and getattr(row, "row_type", "") == "water":
            return int(round(player.x))
        return self._lane_to_screen_x(getattr(player, "grid_lane", 0))

    def _player_draw_key(self, player) -> Tuple[str, str, int]:
        return (
            str(getattr(player, "username", "") or ""),
            str(getattr(player, "id", "") or ""),
            id(player),
        )

    def _tile_offsets(self, count: int) -> List[Tuple[float, float]]:
        cache_key = (
            int(count),
            int(round(self.lane_width)),
            int(round(self._row_height)),
            int(round(self.player_size)),
        )
        cached = self._tile_offset_cache.get(cache_key)
        if cached is not None:
            return cached

        if count <= 1:
            offsets = [(0.0, 0.0)]
            self._tile_offset_cache[cache_key] = offsets
            return offsets

        max_x = max(3.0, min(self.lane_width * 0.28, self.player_size * 0.50))
        max_y = max(3.0, min(self._row_height * 0.18, self.player_size * 0.36))
        angle_step = math.pi * (3.0 - math.sqrt(5.0))
        offsets: List[Tuple[float, float]] = []
        for idx in range(count):
            theta = idx * angle_step
            radius = math.sqrt((idx + 1.0) / (count + 1.0))
            offsets.append((
                math.cos(theta) * max_x * radius,
                math.sin(theta) * max_y * radius,
            ))

        mean_x = sum(x for x, _ in offsets) / float(count)
        mean_y = sum(y for _, y in offsets) / float(count)
        centered = [(x - mean_x, y - mean_y) for x, y in offsets]
        self._tile_offset_cache[cache_key] = centered
        return centered

    def _draw_players(self, players):
        grouped_players: Dict[Tuple[int, int], List[Tuple[object, int, int]]] = {}
        for player in players:
            if not player.alive and not player.is_fading():
                continue
            base_x = self._player_screen_x(player)
            base_y = int(round(self._row_center_to_screen_y(player.grid_row)))
            screen_y = base_y
            if screen_y < self.game_top - 80 or screen_y > self.game_bottom + 80:
                continue
            tile_key = (int(getattr(player, "grid_lane", 0)), int(getattr(player, "grid_row", 0)))
            grouped_players.setdefault(tile_key, []).append((player, base_x, base_y))

        draw_queue: List[Tuple[int, Tuple[str, str, int], object, int, int]] = []
        for entries in grouped_players.values():
            ordered = sorted(entries, key=lambda entry: self._player_draw_key(entry[0]))
            offsets = self._tile_offsets(len(ordered))
            for (player, base_x, base_y), (offset_x, offset_y) in zip(ordered, offsets):
                screen_x = int(round(base_x + offset_x))
                screen_y = int(round(base_y + offset_y))
                draw_queue.append((screen_y, self._player_draw_key(player), player, screen_x, screen_y))

        draw_queue.sort(key=lambda item: (item[0], item[1]))
        for _, _, player, screen_x, screen_y in draw_queue:
            self._draw_avatar_at(player, screen_x, screen_y)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = int(game_state.get("participant_count", len(players)))
        day_number = game_state.get("display_day_number")
        if day_number is None:
            day_number = int(getattr(config, "DAY_NUMBER", 1))
        day_text = f"Day {day_number}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        if y_pos > self.height - 8:
            y_pos = self.height - 24
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_ui(self, players, game_state: dict):
        alive_count = game_state.get("alive_count")
        leader_progress = game_state.get("leader_progress")
        elapsed_time = game_state.get("elapsed_time")

        record = game_state.get("highscore") or {}
        record_score = int(record.get("score", 0) or 0)
        record_name = str(record.get("username", "") or "")
        show_record = record_score > 0

        panel_lines = []
        if alive_count is not None:
            panel_lines.append(f"Alive: {alive_count}")
        if leader_progress is not None:
            panel_lines.append(f"Leader: {int(leader_progress)} rows")
        if elapsed_time is not None:
            panel_lines.append(f"Time: {elapsed_time:.1f}s")
        if show_record:
            line = f"Highscore: {record_score} rows"
            if record_name:
                short_name = record_name if len(record_name) <= 12 else record_name[:12] + "..."
                line = f"{line} - {short_name}"
            panel_lines.append(line)

        if panel_lines:
            text_surfaces = [self.font_small.render(line, True, (255, 255, 255)) for line in panel_lines]
            panel_w = max(surface.get_width() for surface in text_surfaces) + 22
            panel_h = len(text_surfaces) * 20 + 14
            panel_x = self.game_left + 10
            panel_y = self.game_top + 10
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 110))
            self.screen.blit(panel, (panel_x, panel_y))
            y = panel_y + 7
            for surface in text_surfaces:
                self.screen.blit(surface, (panel_x + 10, y))
                y += 20

        eliminations = game_state.get("recent_eliminations") or []
        if not eliminations:
            return

        list_right_x = self.width - 16 + self.elimination_list_x_offset
        list_top = self.game_top + 10

        label_surface = self.font_eliminations.render(self.elimination_label, True, (0, 0, 0))
        label_rect = label_surface.get_rect(topright=(list_right_x, list_top))
        self.screen.blit(label_surface, label_rect)

        line_height = self.font_eliminations.get_linesize()
        start_y = label_rect.bottom + 4
        max_entries = self.elimination_list_size
        if max_entries <= 0:
            available_height = max(0, self.height - start_y - 6)
            max_entries = max(0, available_height // line_height)
        for idx, username in enumerate(eliminations[:max_entries]):
            display_name = username
            if len(display_name) > self.elimination_name_length:
                display_name = display_name[:self.elimination_name_length] + "..."
            entry_surface = self.font_eliminations.render(display_name, True, (0, 0, 0))
            entry_rect = entry_surface.get_rect(topright=(list_right_x, start_y + idx * line_height))
            self.screen.blit(entry_surface, entry_rect)
