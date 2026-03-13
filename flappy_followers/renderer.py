import random

import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class FlappyFollowersRenderer(RendererTemplate):
    GAME_TITLE = "FLAPPY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers flap every day"
    PLAYER_LABEL = "birds"
    GAME_WIDTH = config.SCREEN_WIDTH
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_y = config.FIGHTER_ARENA_RECT[1]
        arena_h = config.FIGHTER_ARENA_RECT[3]
        self.game_left = 0
        self.game_top = arena_y
        self.game_right = config.SCREEN_WIDTH
        self.game_bottom = arena_y + arena_h

        self.bg_color = getattr(config, "FLAPPY_BG_COLOR", (172, 214, 246))
        self.pipe_color = getattr(config, "FLAPPY_PIPE_COLOR", (70, 180, 90))
        self.pipe_border = getattr(config, "FLAPPY_PIPE_BORDER_COLOR", (30, 120, 50))
        self.pipe_highlight = getattr(config, "FLAPPY_PIPE_HIGHLIGHT_COLOR", (110, 210, 120))
        self.day_counter_offset = int(getattr(config, "FLAPPY_DAY_COUNTER_OFFSET", 18))
        self.player_size = float(getattr(config, "FLAPPY_BIRD_SIZE", 16))
        self.elimination_list_size = int(getattr(config, "FLAPPY_ELIMINATION_LIST_SIZE", 6))
        elimination_text_size = int(getattr(config, "FLAPPY_ELIMINATION_TEXT_SIZE", 18))
        self.elimination_text_size = max(12, elimination_text_size)
        self.elimination_name_length = int(getattr(config, "FLAPPY_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "FLAPPY_ELIMINATION_LABEL", "Eliminated:"))
        self.elimination_list_x_offset = int(getattr(config, "FLAPPY_ELIMINATION_LIST_X_OFFSET", 0))
        self.font_eliminations = pygame.font.Font(None, self.elimination_text_size)
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

        ground_h = int(height * 0.18)
        ground_y = height - ground_h
        skyline_h = int(height * 0.18)
        skyline_y = max(0, ground_y - skyline_h)
        skyline_color = (192, 222, 230)
        skyline_shadow = (168, 204, 212)
        pygame.draw.rect(surface, skyline_color, pygame.Rect(0, skyline_y, width, skyline_h))

        x = 0
        while x < width:
            building_w = rng.randint(16, 36)
            building_h = rng.randint(int(skyline_h * 0.35), int(skyline_h * 0.95))
            building_y = skyline_y + skyline_h - building_h
            pygame.draw.rect(surface, skyline_shadow, pygame.Rect(x, building_y, building_w, building_h))
            x += building_w + rng.randint(6, 14)

        cloud_color = (238, 248, 255)
        for _ in range(7):
            cloud_w = rng.randint(90, 150)
            cloud_h = rng.randint(22, 36)
            cloud_x = rng.randint(-20, max(-20, width - cloud_w + 20))
            cloud_y = rng.randint(18, int(height * 0.28))
            pygame.draw.ellipse(surface, cloud_color, pygame.Rect(cloud_x, cloud_y, cloud_w, cloud_h))
            puff_count = rng.randint(3, 5)
            for i in range(puff_count):
                puff_r = rng.randint(int(cloud_h * 0.4), int(cloud_h * 0.7))
                puff_x = cloud_x + rng.randint(0, cloud_w - puff_r)
                puff_y = cloud_y - rng.randint(0, int(cloud_h * 0.3))
                pygame.draw.circle(surface, cloud_color, (puff_x, puff_y), puff_r)

        ground_color = (106, 200, 98)
        ground_top = (84, 176, 76)
        pygame.draw.rect(surface, ground_color, pygame.Rect(0, ground_y, width, ground_h))
        pygame.draw.rect(surface, ground_top, pygame.Rect(0, ground_y, width, max(6, ground_h // 6)))

        for _ in range(8):
            hill_w = rng.randint(40, 90)
            hill_h = rng.randint(10, 22)
            hill_x = rng.randint(-10, width - 10)
            hill_y = ground_y + rng.randint(0, ground_h - hill_h)
            pygame.draw.ellipse(surface, (90, 180, 84), pygame.Rect(hill_x, hill_y, hill_w, hill_h))

        self._background_surface = surface

    def render_frame(self, players, game_state: dict):
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
                game_state.get("winner")
            )

    def _draw_title_and_subtitle(self):
        arena_top = config.FIGHTER_ARENA_RECT[1]

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
        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        if self._background_surface is not None:
            self.screen.blit(self._background_surface, (self.game_left, self.game_top))
        else:
            pygame.draw.rect(self.screen, self.bg_color, arena_rect)

        pipes = game_state.get("pipes", [])
        for pipe in pipes:
            self._draw_pipe(pipe)

        # No side walls/border for full-width arena

    def _draw_pipe(self, pipe):
        gap_half = pipe.gap_size * 0.5
        gap_top = pipe.gap_center - gap_half
        gap_bottom = pipe.gap_center + gap_half

        top_height = max(0, int(gap_top - self.game_top))
        bottom_height = max(0, int(self.game_bottom - gap_bottom))

        pipe_x = int(pipe.x)
        pipe_w = int(pipe.width)
        cap_height = max(10, int(pipe_w * 0.28))
        cap_overhang = max(4, int(pipe_w * 0.12))
        cap_w = pipe_w + cap_overhang * 2
        cap_x = pipe_x - cap_overhang

        top_rect = pygame.Rect(pipe_x, int(self.game_top), pipe_w, top_height)
        bottom_rect = pygame.Rect(pipe_x, int(gap_bottom), pipe_w, bottom_height)

        pygame.draw.rect(self.screen, self.pipe_color, top_rect)
        pygame.draw.rect(self.screen, self.pipe_color, bottom_rect)

        highlight_width = max(2, int(pipe.width * 0.12))
        highlight_rect_top = pygame.Rect(top_rect.x + 4, top_rect.y + 4, highlight_width, max(0, top_rect.height - 8))
        highlight_rect_bottom = pygame.Rect(bottom_rect.x + 4, bottom_rect.y + 4, highlight_width, max(0, bottom_rect.height - 8))
        if highlight_rect_top.height > 0:
            pygame.draw.rect(self.screen, self.pipe_highlight, highlight_rect_top)
        if highlight_rect_bottom.height > 0:
            pygame.draw.rect(self.screen, self.pipe_highlight, highlight_rect_bottom)

        pygame.draw.rect(self.screen, self.pipe_border, top_rect, 2)
        pygame.draw.rect(self.screen, self.pipe_border, bottom_rect, 2)

        if top_height > 0:
            cap_top_y = top_rect.bottom - cap_height
            cap_top_rect = pygame.Rect(cap_x, cap_top_y, cap_w, cap_height)
            pygame.draw.rect(self.screen, self.pipe_color, cap_top_rect)
            pygame.draw.rect(self.screen, self.pipe_border, cap_top_rect, 2)
            cap_highlight = pygame.Rect(cap_top_rect.x + 4, cap_top_rect.y + 4, highlight_width, max(0, cap_height - 8))
            if cap_highlight.height > 0:
                pygame.draw.rect(self.screen, self.pipe_highlight, cap_highlight)

        if bottom_height > 0:
            cap_bottom_rect = pygame.Rect(cap_x, bottom_rect.y, cap_w, cap_height)
            pygame.draw.rect(self.screen, self.pipe_color, cap_bottom_rect)
            pygame.draw.rect(self.screen, self.pipe_border, cap_bottom_rect, 2)
            cap_highlight = pygame.Rect(cap_bottom_rect.x + 4, cap_bottom_rect.y + 4, highlight_width, max(0, cap_height - 8))
            if cap_highlight.height > 0:
                pygame.draw.rect(self.screen, self.pipe_highlight, cap_highlight)

    def _draw_players(self, players):
        club_players = []
        for player in players:
            if player.alive or player.is_fading():
                if getattr(player, "is_club_member", False):
                    club_players.append(player)
                    continue
                self._draw_player_avatar(player, size=self.player_size)

        for player in club_players:
            self._draw_club_glow(player, size=self.player_size)
            self._draw_player_avatar(player, size=self.player_size)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
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
        pipes_cleared = game_state.get("pipes_cleared")
        elapsed_time = game_state.get("elapsed_time")
        record = game_state.get("highscore") or {}
        record_score = record.get("score", 0) or 0
        record_name = record.get("username", "") or ""
        record_label = "Highscore"
        show_record = record_score > 0

        if alive_count is None and pipes_cleared is None and elapsed_time is None and not show_record:
            return

        line_count = 0
        if alive_count is not None:
            line_count += 1
        if pipes_cleared is not None:
            line_count += 1
        if elapsed_time is not None:
            line_count += 1
        if show_record:
            line_count += 1

        # Auto-size panel width based on the longest rendered line.
        panel_padding_x = 12
        panel_padding_y = 8
        max_line_w = 0
        sample_lines = []
        if alive_count is not None:
            sample_lines.append(self.font_stats.render(f"Alive: {alive_count}", True, (255, 255, 255)))
        if pipes_cleared is not None:
            sample_lines.append(self.font_stats.render(f"Pipes: {pipes_cleared}", True, (255, 255, 255)))
        if elapsed_time is not None:
            sample_lines.append(self.font_small.render(f"Time {elapsed_time:.1f}s", True, (255, 255, 255)))
        if show_record:
            name = record_name
            if len(name) > 12:
                name = name[:12] + "..."
            record_text = f"Highscore: {int(record_score)}"
            if name:
                record_text = f"{record_text} - {name}"
            sample_lines.append(self.font_small.render(record_text, True, (255, 255, 255)))

        for surface in sample_lines:
            max_line_w = max(max_line_w, surface.get_width())

        panel_w = max(140, max_line_w + panel_padding_x * 2)
        panel_h = panel_padding_y * 2 + line_count * 22
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        y_cursor = panel_y + panel_padding_y
        if alive_count is not None:
            alive_text = self.font_stats.render(f"Alive: {alive_count}", True, (255, 255, 255))
            self.screen.blit(alive_text, (panel_x + panel_padding_x, y_cursor))
            y_cursor += 22

        if pipes_cleared is not None:
            pipes_text = self.font_stats.render(f"Pipes: {pipes_cleared}", True, (255, 255, 255))
            self.screen.blit(pipes_text, (panel_x + panel_padding_x, y_cursor))
            y_cursor += 22

        if elapsed_time is not None:
            time_text = self.font_small.render(f"Time {elapsed_time:.1f}s", True, (255, 255, 255))
            self.screen.blit(time_text, (panel_x + panel_padding_x, y_cursor))
            y_cursor += 20

        if show_record:
            name = record_name
            if len(name) > 12:
                name = name[:12] + "..."
            record_text = f"{record_label}: {int(record_score)}"
            if name:
                record_text = f"{record_text} - {name}"
            record_surface = self.font_small.render(record_text, True, (255, 255, 255))
            self.screen.blit(record_surface, (panel_x + panel_padding_x, y_cursor))
