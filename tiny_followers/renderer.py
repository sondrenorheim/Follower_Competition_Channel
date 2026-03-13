import random
import math

import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class TinyFollowersRenderer(RendererTemplate):
    GAME_TITLE = "TINY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers glide every day"
    PLAYER_LABEL = "followers"
    GAME_WIDTH = config.SCREEN_WIDTH
    GAME_HEIGHT = getattr(config, "TINY_ARENA_RECT", config.FIGHTER_ARENA_RECT)[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_rect = getattr(config, "TINY_ARENA_RECT", config.FIGHTER_ARENA_RECT)
        arena_y = arena_rect[1]
        arena_h = arena_rect[3]
        self.game_left = 0
        self.game_top = arena_y
        self.game_right = config.SCREEN_WIDTH
        self.game_bottom = arena_y + arena_h
        self.game_width = self.game_right - self.game_left
        self.game_height = self.game_bottom - self.game_top

        self.zoom_x = max(0.25, float(getattr(config, "TINY_CAMERA_ZOOM_X", 1.0)))
        self.zoom_y = max(0.25, float(getattr(config, "TINY_CAMERA_ZOOM_Y", self.zoom_x)))
        self.zoom_anchor_x = max(0.0, min(1.0, float(getattr(config, "TINY_CAMERA_HORIZONTAL_ANCHOR", 0.5))))
        self.zoom_anchor_y = max(0.0, min(1.0, float(getattr(config, "TINY_CAMERA_VERTICAL_ANCHOR", 0.5))))
        self.zoom_offset_x = self.game_width * (1.0 - self.zoom_x) * self.zoom_anchor_x
        self.zoom_offset_y = self.game_height * (1.0 - self.zoom_y) * self.zoom_anchor_y

        self.sky_top_color = tuple(getattr(config, "TINY_SKY_TOP_COLOR", (180, 224, 255)))
        self.sky_bottom_color = tuple(getattr(config, "TINY_SKY_BOTTOM_COLOR", (120, 188, 240)))
        self.water_color = tuple(getattr(config, "TINY_WATER_COLOR", (72, 164, 224)))
        self.water_highlight = tuple(getattr(config, "TINY_WATER_HIGHLIGHT", (125, 213, 255)))
        self.terrain_color = tuple(getattr(config, "TINY_TERRAIN_COLOR", (96, 189, 86)))
        self.terrain_shadow = tuple(getattr(config, "TINY_TERRAIN_SHADOW_COLOR", (58, 133, 64)))
        self.terrain_ridge = tuple(getattr(config, "TINY_TERRAIN_RIDGE_COLOR", (214, 242, 148)))

        self.player_size = float(getattr(config, "TINY_PLAYER_SIZE", 30.0))
        self.day_counter_offset = int(getattr(config, "TINY_DAY_COUNTER_OFFSET", 18))
        self.render_max_players = int(getattr(config, "TINY_RENDER_MAX_PLAYERS", 6500))
        self.high_pop_render_threshold = int(getattr(config, "TINY_RENDER_HIGH_POP_THRESHOLD", 25000))
        self.min_render_players = int(getattr(config, "TINY_RENDER_MIN_PLAYERS", 1600))
        self.simple_avatar_threshold = int(getattr(config, "TINY_SIMPLE_AVATAR_THRESHOLD", 90000))
        self.visibility_padding_x = float(getattr(config, "TINY_VISIBILITY_PADDING_X", 40.0))
        self.visibility_padding_y = float(getattr(config, "TINY_VISIBILITY_PADDING_Y", 140.0))

        self.elimination_list_size = int(getattr(config, "TINY_ELIMINATION_LIST_SIZE", 0))
        elimination_text_size = int(getattr(config, "TINY_ELIMINATION_TEXT_SIZE", 18))
        self.elimination_text_size = max(12, elimination_text_size)
        self.elimination_name_length = int(getattr(config, "TINY_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "TINY_ELIMINATION_LABEL", "Splash Out:"))
        self.elimination_list_x_offset = int(getattr(config, "TINY_ELIMINATION_LIST_X_OFFSET", 0))
        self.font_eliminations = pygame.font.Font(None, self.elimination_text_size)

        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._club_panel_bottom = None
        self._background_surface = None
        self._build_background()

    def _screen_x_from_world(self, world_x: float, camera_x: float) -> float:
        return self.game_left + self.zoom_offset_x + (world_x - camera_x) * self.zoom_x

    def _screen_y_from_world(self, world_y: float) -> float:
        return self.game_top + self.zoom_offset_y + (world_y - self.game_top) * self.zoom_y

    def _world_view_bounds(self, camera_x: float) -> tuple[float, float]:
        world_left = camera_x - self.zoom_offset_x / max(1e-6, self.zoom_x)
        world_width = self.game_width / max(1e-6, self.zoom_x)
        return world_left, world_width

    def _build_background(self):
        width = int(self.game_width)
        height = int(self.game_height)
        if width <= 0 or height <= 0:
            return

        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            t = y / max(1, height - 1)
            color = (
                int(self.sky_top_color[0] + (self.sky_bottom_color[0] - self.sky_top_color[0]) * t),
                int(self.sky_top_color[1] + (self.sky_bottom_color[1] - self.sky_top_color[1]) * t),
                int(self.sky_top_color[2] + (self.sky_bottom_color[2] - self.sky_top_color[2]) * t),
            )
            pygame.draw.line(surface, color, (0, y), (width, y))

        sun_x = int(width * 0.84)
        sun_y = int(height * 0.18)
        pygame.draw.circle(surface, (255, 244, 182), (sun_x, sun_y), 42)
        pygame.draw.circle(surface, (255, 255, 232), (sun_x - 10, sun_y - 8), 22)

        rng = random.Random(int(getattr(config, "DAY_NUMBER", 1)))
        cloud_color = (246, 252, 255, 200)
        for _ in range(8):
            cloud_w = rng.randint(72, 132)
            cloud_h = rng.randint(20, 36)
            cloud_x = rng.randint(-20, max(-20, width - cloud_w + 20))
            cloud_y = rng.randint(16, int(height * 0.32))
            pygame.draw.ellipse(surface, cloud_color, pygame.Rect(cloud_x, cloud_y, cloud_w, cloud_h))
            for _ in range(rng.randint(2, 4)):
                puff_r = rng.randint(cloud_h // 3, cloud_h // 2)
                puff_x = cloud_x + rng.randint(0, max(0, cloud_w - puff_r))
                puff_y = cloud_y - rng.randint(0, cloud_h // 3)
                pygame.draw.circle(surface, cloud_color, (puff_x, puff_y), puff_r)

        noise_path = str(getattr(config, "TINY_NOISE_TEXTURE", ""))
        if noise_path:
            try:
                noise = pygame.image.load(noise_path).convert_alpha()
                noise = pygame.transform.smoothscale(noise, (width, height))
                noise.set_alpha(int(getattr(config, "TINY_NOISE_ALPHA", 34)))
                surface.blit(noise, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            except Exception:
                pass

        self._background_surface = surface

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(game_state)
        self._draw_players(players, game_state)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(game_state)

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
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70))
        self.screen.blit(title_text, title_rect)

        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 40))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_font = pygame.font.Font(None, 24)
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, subtitle_rect.bottom + 6))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, game_state: dict):
        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        if self._background_surface is not None:
            self.screen.blit(self._background_surface, (self.game_left, self.game_top))
        else:
            pygame.draw.rect(self.screen, self.sky_bottom_color, arena_rect)

        camera_x = float(game_state.get("camera_x", 0.0))
        terrain = game_state.get("terrain")
        if terrain is None:
            return

        world_left, world_width = self._world_view_bounds(camera_x)

        water_ranges = terrain.get_visible_water_ranges(world_left, world_width)
        for left, right in water_ranges:
            x = int(self.game_left + left * self.zoom_x)
            w = int(max(1.0, (right - left) * self.zoom_x))
            rect = pygame.Rect(x, self.game_top, w, self.game_bottom - self.game_top)
            pygame.draw.rect(self.screen, self.water_color, rect)
            highlight_rect = pygame.Rect(x, self.game_top + 8, w, 8)
            pygame.draw.rect(self.screen, self.water_highlight, highlight_rect)

        segments = terrain.get_visible_ground_segments(world_left, world_width)
        for segment in segments:
            self._draw_ground_segment(segment, camera_x, world_left)

        finish_x = float(game_state.get("finish_x", 0.0))
        finish_screen_x = int(self._screen_x_from_world(finish_x, camera_x))
        if self.game_left - 20 <= finish_screen_x <= self.game_right + 20:
            finish_ground_y = float(game_state.get("finish_ground_y", self.game_bottom - 20))
            self._draw_finish_marker(finish_screen_x, int(self._screen_y_from_world(finish_ground_y)))

    def _draw_ground_segment(self, segment, camera_x: float, world_left: float):
        if len(segment) < 2:
            return

        points = [
            (
                int(self._screen_x_from_world(world_left + sx, camera_x)),
                int(self._screen_y_from_world(y)),
            )
            for sx, y in segment
        ]
        if len(points) < 2:
            return

        base_polygon = list(points)
        base_polygon.append((points[-1][0], self.game_bottom))
        base_polygon.append((points[0][0], self.game_bottom))

        pygame.draw.polygon(self.screen, self.terrain_shadow, base_polygon)
        pygame.draw.lines(self.screen, self.terrain_color, False, points, 6)
        pygame.draw.lines(self.screen, self.terrain_ridge, False, points, 2)

    def _draw_finish_marker(self, x: int, ground_y: int):
        pole_top = max(self.game_top + 14, ground_y - 120)
        pygame.draw.line(self.screen, (70, 58, 38), (x, ground_y), (x, pole_top), 4)

        flag = [
            (x + 2, pole_top + 6),
            (x + 52, pole_top + 20),
            (x + 2, pole_top + 34),
        ]
        pygame.draw.polygon(self.screen, (255, 120, 80), flag)
        pygame.draw.polygon(self.screen, (120, 42, 36), flag, 2)

        label = self.font_small.render("NEXT ISLAND", True, (28, 32, 44))
        rect = label.get_rect(midbottom=(x, pole_top - 6))
        self.screen.blit(label, rect)

    def _draw_players(self, players, game_state: dict):
        camera_x = float(game_state.get("camera_x", 0.0))
        world_view_left, world_view_width = self._world_view_bounds(camera_x)
        world_left = world_view_left - self.visibility_padding_x
        world_right = world_view_left + world_view_width + self.visibility_padding_x
        world_bottom = self.game_bottom + self.visibility_padding_y
        total_count = int(game_state.get("total_count", len(players)))

        visible = []
        for player in players:
            if not (player.alive or player.is_fading() or getattr(player, "finished", False)):
                continue
            if player.x < world_left or player.x > world_right:
                continue
            if player.y - player.radius > world_bottom:
                continue
            visible.append(player)

        render_limit = self.render_max_players
        if (
            render_limit > 0
            and total_count >= self.high_pop_render_threshold
        ):
            ratio = self.high_pop_render_threshold / max(1.0, float(total_count))
            scaled_limit = int(round(render_limit * math.sqrt(max(0.05, ratio))))
            render_limit = max(self.min_render_players, min(render_limit, scaled_limit))

        if len(visible) > render_limit > 0:
            # Stable identity-based sampling avoids frame-to-frame "teleport flicker"
            # that happens when sampling by array index while visible count changes.
            keep_ratio = render_limit / float(len(visible))
            hash_threshold = int(max(1.0, min(65535.0, 65535.0 * keep_ratio)))

            sampled = []
            club_sampled = []
            for player in visible:
                if getattr(player, "is_club_member", False):
                    club_sampled.append(player)
                    continue
                if (int(getattr(player, "render_hash", 0)) & 0xFFFF) <= hash_threshold:
                    sampled.append(player)

            # Keep club members visible when possible, then fill remaining slots.
            keep_slots = max(0, render_limit - len(club_sampled))
            if len(sampled) > keep_slots > 0:
                step = len(sampled) / float(keep_slots)
                trimmed = []
                idx = 0.0
                while len(trimmed) < keep_slots and int(idx) < len(sampled):
                    trimmed.append(sampled[int(idx)])
                    idx += step
                sampled = trimmed
            elif keep_slots <= 0:
                sampled = []

            visible = sampled + club_sampled
            if len(visible) > render_limit > 0:
                step = len(visible) / float(render_limit)
                trimmed = []
                idx = 0.0
                while len(trimmed) < render_limit and int(idx) < len(visible):
                    trimmed.append(visible[int(idx)])
                    idx += step
                visible = trimmed

        simplified_avatars = total_count >= self.simple_avatar_threshold

        club_players = [p for p in visible if getattr(p, "is_club_member", False)]
        normal_players = [p for p in visible if not getattr(p, "is_club_member", False)]

        for player in normal_players:
            self._draw_world_player(player, camera_x, simplified=simplified_avatars)

        for player in club_players:
            self._draw_world_player(player, camera_x, glow=True, simplified=simplified_avatars)

    def _draw_world_player(self, player, camera_x: float, glow: bool = False, simplified: bool = False):
        screen_x = int(self._screen_x_from_world(player.x, camera_x))
        screen_y = int(self._screen_y_from_world(player.y))
        if glow:
            self._draw_club_glow(player, size=self.player_size, pos=(screen_x, screen_y))
        if simplified:
            radius = max(2, int(round(self.player_size * 0.5)))
            color = tuple(getattr(player, "color", (100, 100, 255)))
            alpha = int(getattr(player, "alpha", 255))
            if alpha < 255:
                dot = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(dot, (*color, alpha), (radius + 1, radius + 1), radius)
                pygame.draw.circle(dot, (0, 0, 0, alpha), (radius + 1, radius + 1), radius, 1)
                self.screen.blit(dot, (screen_x - radius - 1, screen_y - radius - 1))
            else:
                pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius)
                pygame.draw.circle(self.screen, (0, 0, 0), (screen_x, screen_y), radius, 1)
            return
        self._draw_player_avatar_at(player, screen_x, screen_y, self.player_size)

    def _draw_player_avatar_at(self, player, x: int, y: int, size: float):
        avatar_surface = self._get_avatar_surface(player, int(round(size)))
        if hasattr(player, "alpha") and player.alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(player.alpha)
        rect = avatar_surface.get_rect(center=(x, y))
        self.screen.blit(avatar_surface, rect)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = int(game_state.get("total_count", len(players)))
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

        anchor_y = day_rect.bottom
        panel_rect = draw_club_panel(
            self.screen,
            game_state.get("club_spotlight"),
            anchor_y=anchor_y,
            font=self.font_club_panel,
            get_avatar_surface=self._get_avatar_surface,
            glow_cache=self._club_glow_cache,
        )
        if panel_rect is not None:
            anchor_y = panel_rect.bottom
        self._club_panel_bottom = anchor_y

        eliminations = game_state.get("recent_eliminations") or []
        if eliminations:
            list_center_x = self.width // 2 + self.elimination_list_x_offset
            label_surface = self.font_eliminations.render(self.elimination_label, True, config.COLOR_TEXT)
            label_rect = label_surface.get_rect(center=(list_center_x, anchor_y + 8))
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
                entry_surface = self.font_eliminations.render(display_name, True, config.COLOR_TEXT)
                entry_rect = entry_surface.get_rect(center=(list_center_x, start_y + idx * line_height))
                self.screen.blit(entry_surface, entry_rect)

    def _draw_game_ui(self, game_state: dict):
        active_count = game_state.get("active_count")
        finished_count = game_state.get("finished_count")
        elapsed_time = game_state.get("elapsed_time")
        leader_name = game_state.get("leader_name")
        distance_to_finish = game_state.get("distance_to_finish")
        record = game_state.get("highscore") or {}
        record_score = int(record.get("score", 0) or 0)
        record_name = str(record.get("username", "") or "")

        panel_lines = []
        if active_count is not None:
            panel_lines.append(("stat", f"Racing: {active_count}"))
        if finished_count is not None:
            panel_lines.append(("small", f"Finished: {finished_count}"))
        if distance_to_finish is not None:
            panel_lines.append(("small", f"Leader to island: {distance_to_finish:.0f}m"))
        if elapsed_time is not None:
            panel_lines.append(("small", f"Time: {elapsed_time:.1f}s"))
        detail_stride = int(game_state.get("detail_stride", 1) or 1)
        if detail_stride > 1:
            panel_lines.append(("small", f"Perf mode: 1/{detail_stride} detailed"))
        if leader_name:
            display_name = leader_name[:14] + "..." if len(leader_name) > 14 else leader_name
            panel_lines.append(("small", f"Lead: {display_name}"))
        if record_score > 0:
            display_name = record_name[:12] + "..." if len(record_name) > 12 else record_name
            record_text = f"Highscore: {record_score}m"
            if display_name:
                record_text += f" - {display_name}"
            panel_lines.append(("small", record_text))

        if not panel_lines:
            return

        rendered = []
        max_w = 0
        for kind, text in panel_lines:
            font = self.font_stats if kind == "stat" else self.font_small
            surface = font.render(text, True, (255, 255, 255))
            rendered.append(surface)
            max_w = max(max_w, surface.get_width())

        pad_x = 12
        pad_y = 8
        line_gap = 20
        panel_w = max(180, max_w + pad_x * 2)
        panel_h = pad_y * 2 + line_gap * len(rendered)
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        y_cursor = panel_y + pad_y
        for surface in rendered:
            self.screen.blit(surface, (panel_x + pad_x, y_cursor))
            y_cursor += line_gap
