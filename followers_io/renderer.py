import random
import time

import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class FollowersIORenderer(RendererTemplate):
    GAME_TITLE = "FOLLOWERS.IO"
    GAME_SUBTITLE = "Making my followers fight every day"
    PLAYER_LABEL = "followers"
    GAME_WIDTH = config.FIGHTER_ARENA_RECT[2]
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)

        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.bg_color = tuple(getattr(config, "FOLLOWERS_IO_BG_COLOR", (232, 239, 244)))
        self.grid_color = tuple(getattr(config, "FOLLOWERS_IO_GRID_COLOR", (202, 216, 225)))
        self.border_color = tuple(getattr(config, "FOLLOWERS_IO_BORDER_COLOR", (20, 20, 20)))
        self.food_color = tuple(getattr(config, "FOLLOWERS_IO_FOOD_COLOR", (115, 168, 121)))

        self.simple_render_threshold = int(getattr(config, "FOLLOWERS_IO_SIMPLE_RENDER_THRESHOLD", 12000))
        self.render_max_players = int(getattr(config, "FOLLOWERS_IO_RENDER_MAX_PLAYERS", 8000))
        self.render_min_players = int(getattr(config, "FOLLOWERS_IO_RENDER_MIN_PLAYERS", 1800))
        self.render_high_pop_threshold = int(getattr(config, "FOLLOWERS_IO_RENDER_HIGH_POP_THRESHOLD", 50000))
        self.food_draw_limit = int(getattr(config, "FOLLOWERS_IO_FOOD_DRAW_LIMIT", 1600))

        self.day_counter_offset = int(getattr(config, "FOLLOWERS_IO_DAY_COUNTER_OFFSET", 18))
        self.elimination_list_size = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_LIST_SIZE", 0))
        self.elimination_name_length = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "FOLLOWERS_IO_ELIMINATION_LABEL", "Consumed:"))
        self.elimination_list_x_offset = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_LIST_X_OFFSET", 0))
        elimination_text_size = int(getattr(config, "FOLLOWERS_IO_ELIMINATION_TEXT_SIZE", 18))
        self.font_eliminations = pygame.font.Font(None, max(12, elimination_text_size))
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._club_panel_bottom = None

        self._background_surface = None
        self._build_background()

    def _build_background(self):
        width = int(self.game_right - self.game_left)
        height = int(self.game_bottom - self.game_top)
        if width <= 0 or height <= 0:
            return

        rng = random.Random(int(getattr(config, "DAY_NUMBER", 1)))
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill(self.bg_color)

        # Petri-dish style subtle circles.
        for _ in range(18):
            radius = rng.randint(18, 85)
            cx = rng.randint(0, width)
            cy = rng.randint(0, height)
            alpha = rng.randint(12, 26)
            circle_color = (255, 255, 255, alpha)
            pygame.draw.circle(surface, circle_color, (cx, cy), radius)

        # Grid.
        grid_step = max(24, int(getattr(config, "FOLLOWERS_IO_GRID_STEP", 32)))
        for x in range(0, width, grid_step):
            pygame.draw.line(surface, self.grid_color, (x, 0), (x, height), 1)
        for y in range(0, height, grid_step):
            pygame.draw.line(surface, self.grid_color, (0, y), (width, y), 1)

        self._background_surface = surface

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players, game_state)
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

    def _draw_game_area(self, players, game_state: dict):
        area_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )

        if self._background_surface is not None:
            self.screen.blit(self._background_surface, (self.game_left, self.game_top))
        else:
            pygame.draw.rect(self.screen, self.bg_color, area_rect)

        food_particles = game_state.get("food_particles", []) or []
        if food_particles:
            max_food = self.food_draw_limit
            food_list = food_particles if len(food_particles) <= max_food else food_particles[:max_food]
            for food in food_list:
                radius = max(1, min(4, int(food.mass ** 0.5)))
                pygame.draw.circle(
                    self.screen,
                    self.food_color,
                    (int(food.x), int(food.y)),
                    radius,
                )

        pygame.draw.rect(self.screen, self.border_color, area_rect, 3)

    def _draw_players(self, players, game_state: dict):
        fade_duration = float(getattr(config, "FADE_DURATION", 0.5))
        renderable = []
        for player in players:
            if player.alive:
                renderable.append(player)
                continue
            if player.is_fading(fade_duration):
                player.update_fade(fade_duration)
                renderable.append(player)

        total_count = int(game_state.get("total_count", len(players)))
        render_limit = self.render_max_players
        if render_limit > 0 and total_count >= self.render_high_pop_threshold:
            ratio = self.render_high_pop_threshold / max(1.0, float(total_count))
            scaled_limit = int(round(render_limit * (ratio ** 0.5)))
            render_limit = max(self.render_min_players, min(render_limit, scaled_limit))

        if len(renderable) > render_limit > 0:
            keep_ratio = render_limit / float(len(renderable))
            hash_threshold = int(max(1.0, min(65535.0, 65535.0 * keep_ratio)))
            sampled = []
            club_sampled = []
            for player in renderable:
                if getattr(player, "is_club_member", False):
                    club_sampled.append(player)
                    continue
                if (int(getattr(player, "render_hash", 0)) & 0xFFFF) <= hash_threshold:
                    sampled.append(player)

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
            renderable = sampled + club_sampled

        simple_mode = total_count >= self.simple_render_threshold
        club_players = [p for p in renderable if getattr(p, "is_club_member", False)]
        normal_players = [p for p in renderable if not getattr(p, "is_club_member", False)]

        for player in normal_players:
            if simple_mode:
                self._draw_dot_player(player)
            else:
                size = max(6, min(42, int(player.radius * 2.0)))
                self._draw_player_avatar(player, size=size)

        for player in club_players:
            size = max(8, min(48, int(player.radius * 2.0)))
            if simple_mode:
                self._draw_club_glow(player, size=size)
                self._draw_dot_player(player)
            else:
                self._draw_club_glow(player, size=size)
                self._draw_player_avatar(player, size=size)

    def _draw_dot_player(self, player):
        radius = max(1, min(8, int(player.radius)))
        color = tuple(getattr(player, "color", (100, 100, 255)))
        alpha = int(getattr(player, "alpha", 255))
        if alpha < 255:
            dot_surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(dot_surface, (*color, alpha), (radius + 1, radius + 1), radius)
            pygame.draw.circle(dot_surface, (0, 0, 0, alpha), (radius + 1, radius + 1), radius, 1)
            self.screen.blit(dot_surface, (int(player.x - radius - 1), int(player.y - radius - 1)))
        else:
            pygame.draw.circle(self.screen, color, (int(player.x), int(player.y)), radius)
            pygame.draw.circle(self.screen, (0, 0, 0), (int(player.x), int(player.y)), radius, 1)

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
                entry_rect = entry_surface.get_rect(
                    center=(list_center_x, start_y + idx * line_height)
                )
                self.screen.blit(entry_surface, entry_rect)

    def _draw_game_ui(self, players, game_state: dict):
        alive_count = game_state.get("alive_count")
        elapsed_time = game_state.get("elapsed_time")
        consumptions = game_state.get("total_consumptions")
        detail_stride = int(game_state.get("detail_stride", 1) or 1)
        speedup_active = bool(game_state.get("speedup_active", False))
        speedup_factor = float(game_state.get("speedup_factor", 1.0) or 1.0)

        record = game_state.get("highscore") or {}
        record_score = float(record.get("score", 0) or 0)
        record_name = str(record.get("username", "") or "")

        lines = []
        if alive_count is not None:
            lines.append(("stat", f"Alive: {alive_count:,}"))
        if consumptions is not None:
            lines.append(("stat", f"Consumed: {int(consumptions):,}"))
        if elapsed_time is not None:
            lines.append(("small", f"Time: {elapsed_time:.1f}s"))
        if detail_stride > 1:
            lines.append(("small", f"Perf mode: 1/{detail_stride} detailed"))
        if speedup_active and speedup_factor > 1.0:
            lines.append(("small", f"Export speedup: {speedup_factor:.1f}x"))
        if record_score > 0:
            display_name = record_name
            if len(display_name) > 12:
                display_name = display_name[:12] + "..."
            record_text = f"Highscore: {int(record_score)} mass"
            if display_name:
                record_text = f"{record_text} - {display_name}"
            lines.append(("small", record_text))

        if not lines:
            return

        rendered = []
        max_w = 0
        for kind, text in lines:
            font = self.font_stats if kind == "stat" else self.font_small
            surface = font.render(text, True, (255, 255, 255))
            rendered.append(surface)
            max_w = max(max_w, surface.get_width())

        pad_x = 12
        pad_y = 8
        line_h = 21
        panel_w = max(170, max_w + pad_x * 2)
        panel_h = pad_y * 2 + line_h * len(rendered)
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 115))
        self.screen.blit(panel, (panel_x, panel_y))

        y = panel_y + pad_y
        for surface in rendered:
            self.screen.blit(surface, (panel_x + pad_x, y))
            y += line_h
