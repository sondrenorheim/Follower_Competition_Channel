import pygame

import config
from shared import RendererTemplate


class SubwayFollowersRenderer(RendererTemplate):
    GAME_TITLE = "SUBWAY FOLLOWERS"
    GAME_SUBTITLE = "Making my followers run every day"
    PLAYER_LABEL = "runners"
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

        self.bg_color = getattr(config, "SUBWAY_BG_COLOR", (34, 36, 44))
        self.track_color = getattr(config, "SUBWAY_TRACK_COLOR", (48, 50, 58))
        self.lane_line_color = getattr(config, "SUBWAY_LANE_LINE_COLOR", (90, 92, 100))
        self.rail_color = getattr(config, "SUBWAY_RAIL_COLOR", (120, 120, 130))
        self.day_counter_offset = int(getattr(config, "SUBWAY_DAY_COUNTER_OFFSET", 18))
        self.player_size = float(getattr(config, "SUBWAY_PLAYER_SIZE", 30.0))

        self.lane_count = int(getattr(config, "SUBWAY_LANE_COUNT", 3))
        self.lane_padding = float(getattr(config, "SUBWAY_LANE_PADDING", 24))
        usable_width = max(1.0, (self.game_right - self.game_left) - self.lane_padding * 2)
        self.lane_width = usable_width / max(1, self.lane_count)

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

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_area(self, players, game_state: dict):
        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.bg_color, arena_rect)

        track_rect = arena_rect.inflate(-self.lane_padding * 2, -20)
        pygame.draw.rect(self.screen, self.track_color, track_rect, border_radius=8)

        for i in range(1, self.lane_count):
            x = self.game_left + self.lane_padding + self.lane_width * i
            pygame.draw.line(self.screen, self.lane_line_color, (x, self.game_top + 10), (x, self.game_bottom - 10), 2)

        for i in range(self.lane_count):
            center_x = self.game_left + self.lane_padding + self.lane_width * (i + 0.5)
            rail_offset = self.lane_width * 0.18
            pygame.draw.line(self.screen, self.rail_color, (center_x - rail_offset, self.game_top + 10), (center_x - rail_offset, self.game_bottom - 10), 1)
            pygame.draw.line(self.screen, self.rail_color, (center_x + rail_offset, self.game_top + 10), (center_x + rail_offset, self.game_bottom - 10), 1)

        for obstacle in game_state.get("obstacles", []):
            self._draw_obstacle(obstacle)

    def _draw_obstacle(self, obstacle):
        rect = pygame.Rect(
            int(obstacle.x - obstacle.width / 2),
            int(obstacle.y),
            int(obstacle.width),
            int(obstacle.height),
        )
        color = getattr(obstacle, "color", (180, 60, 60))
        outline = getattr(obstacle, "outline", (30, 30, 30))
        accent = getattr(obstacle, "accent", (230, 200, 90))

        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        pygame.draw.rect(self.screen, outline, rect, 2, border_radius=6)

        kind = getattr(obstacle, "kind", "")
        if kind == "train":
            window_w = max(8, rect.width // 5)
            window_h = max(6, rect.height // 6)
            window_y = rect.y + max(6, rect.height // 5)
            for i in range(3):
                window_x = rect.x + 6 + i * (window_w + 6)
                if window_x + window_w < rect.right - 4:
                    pygame.draw.rect(self.screen, accent, pygame.Rect(window_x, window_y, window_w, window_h), border_radius=3)
            stripe_y = rect.y + rect.height - max(8, rect.height // 5)
            pygame.draw.rect(self.screen, accent, pygame.Rect(rect.x + 4, stripe_y, rect.width - 8, max(4, rect.height // 10)))
        elif kind == "barrier":
            stripe_h = max(6, rect.height // 4)
            pygame.draw.rect(self.screen, accent, pygame.Rect(rect.x + 4, rect.y + rect.height // 2 - stripe_h // 2, rect.width - 8, stripe_h))
        elif kind == "pole":
            cap_h = max(6, rect.height // 5)
            pygame.draw.rect(self.screen, accent, pygame.Rect(rect.x - 3, rect.y, rect.width + 6, cap_h), border_radius=3)
        elif kind == "tunnel_wall":
            pygame.draw.rect(self.screen, accent, pygame.Rect(rect.x + 4, rect.y + 6, rect.width - 8, rect.height - 12), 2)

    def _draw_players(self, players):
        for player in players:
            if player.alive or player.is_fading():
                self._draw_player_avatar(player, size=self.player_size)

    def _draw_game_ui(self, players, game_state: dict):
        alive_count = game_state.get("alive_count")
        speed = game_state.get("speed")
        elapsed_time = game_state.get("elapsed_time")

        panel_w = 220
        panel_h = 70
        panel_x = self.game_left + 12
        panel_y = self.game_top + 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 120))
        self.screen.blit(panel, (panel_x, panel_y))

        y_cursor = panel_y + 8
        if alive_count is not None:
            alive_text = self.font_stats.render(f"Alive: {alive_count}", True, (255, 255, 255))
            self.screen.blit(alive_text, (panel_x + 12, y_cursor))
            y_cursor += 22

        if speed is not None:
            speed_text = self.font_small.render(f"Speed: {speed:.0f}", True, (255, 255, 255))
            self.screen.blit(speed_text, (panel_x + 12, y_cursor))
            y_cursor += 20

        if elapsed_time is not None:
            time_text = self.font_small.render(f"Time {elapsed_time:.1f}s", True, (255, 255, 255))
            self.screen.blit(time_text, (panel_x + 12, y_cursor))
