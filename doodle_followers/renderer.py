import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class DoodleFollowersRenderer(RendererTemplate):
    GAME_TITLE = "DOODLE FOLLOWERS"
    GAME_SUBTITLE = "Making my followers doodle every day"
    PLAYER_LABEL = "doodles"
    GAME_WIDTH = getattr(config, "DOODLE_ARENA_RECT", config.FIGHTER_ARENA_RECT)[2]
    GAME_HEIGHT = getattr(config, "DOODLE_ARENA_RECT", config.FIGHTER_ARENA_RECT)[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(config, "DOODLE_ARENA_RECT", config.FIGHTER_ARENA_RECT)
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.bg_color = getattr(config, "DOODLE_BG_COLOR", (248, 243, 224))
        self.grid_color = getattr(config, "DOODLE_GRID_COLOR", (220, 210, 190))
        self.grid_size = int(getattr(config, "DOODLE_GRID_SIZE", 40))
        self.grid_subdiv = int(getattr(config, "DOODLE_GRID_SUBDIV", 20))

        self.platform_color = getattr(config, "DOODLE_PLATFORM_COLOR", (86, 185, 106))
        self.platform_shadow = getattr(config, "DOODLE_PLATFORM_SHADOW", (60, 150, 80))
        self.platform_highlight = getattr(config, "DOODLE_PLATFORM_HIGHLIGHT", (110, 210, 130))
        self.platform_border = getattr(config, "DOODLE_PLATFORM_BORDER", (30, 80, 50))

        self.moving_platform_color = getattr(config, "DOODLE_MOVING_PLATFORM_COLOR", (70, 150, 210))
        self.break_platform_color = getattr(config, "DOODLE_BREAK_PLATFORM_COLOR", (186, 120, 60))
        self.trampoline_color = getattr(config, "DOODLE_TRAMPOLINE_COLOR", (220, 70, 70))

        self.spring_color = getattr(config, "DOODLE_SPRING_COLOR", (40, 40, 40))
        self.spring_highlight = getattr(config, "DOODLE_SPRING_HIGHLIGHT", (220, 220, 220))

        self.monster_color = getattr(config, "DOODLE_MONSTER_COLOR", (90, 160, 200))
        self.monster_border = getattr(config, "DOODLE_MONSTER_BORDER", (30, 60, 90))
        self.monster_eye = getattr(config, "DOODLE_MONSTER_EYE", (255, 255, 255))

        self.player_size = float(getattr(config, "DOODLE_PLAYER_SIZE", config.FOLLOWER_RADIUS * 2))
        self.day_counter_offset = int(getattr(config, "DOODLE_DAY_COUNTER_OFFSET", 18))

        self.elimination_list_size = int(getattr(config, "DOODLE_ELIMINATION_LIST_SIZE", 6))
        elimination_text_size = int(getattr(config, "DOODLE_ELIMINATION_TEXT_SIZE", 18))
        self.elimination_text_size = max(12, elimination_text_size)
        self.elimination_name_length = int(getattr(config, "DOODLE_ELIMINATION_NAME_LENGTH", 16))
        self.elimination_label = str(getattr(config, "DOODLE_ELIMINATION_LABEL", "Eliminated:"))
        self.elimination_list_x_offset = int(getattr(config, "DOODLE_ELIMINATION_LIST_X_OFFSET", 0))
        self.font_eliminations = pygame.font.Font(None, self.elimination_text_size)
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._club_panel_anchor_y = None
        self._club_panel_bottom = None

        self._bg_tile = None
        self._build_background_tile()
        self._camera_y = 0.0

    def _build_background_tile(self):
        grid_size = max(10, self.grid_size)
        tile = pygame.Surface((grid_size, grid_size))
        tile.fill(self.bg_color)
        pygame.draw.line(tile, self.grid_color, (0, 0), (grid_size, 0), 1)
        pygame.draw.line(tile, self.grid_color, (0, 0), (0, grid_size), 1)
        if self.grid_subdiv > 0 and self.grid_subdiv < grid_size:
            pygame.draw.line(tile, self.grid_color, (self.grid_subdiv, 0), (self.grid_subdiv, grid_size), 1)
            pygame.draw.line(tile, self.grid_color, (0, self.grid_subdiv), (grid_size, self.grid_subdiv), 1)
        self._bg_tile = tile

    def render_frame(self, players, game_state: dict):
        self._camera_y = float(game_state.get("camera_y", 0.0))
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_club_panel(game_state)
        self._draw_game_ui(players, game_state)

        if game_state.get("show_leaderboards"):
            self._draw_end_game_display(
                game_state.get("current_game_leaderboard", []),
                game_state.get("all_time_leaderboard", []),
                game_state.get("winner")
            )

    def _draw_title_and_subtitle(self):
        arena_top = self.game_top
        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        # Move title/subtitle closer to the center of the upper third.
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

    def _draw_game_area(self, players, game_state: dict):
        self._draw_background()

        platforms = game_state.get("platforms", [])
        for platform in platforms:
            self._draw_platform(platform)

        monsters = game_state.get("monsters", [])
        for monster in monsters:
            self._draw_monster(monster)

    def _draw_background(self):
        if not self._bg_tile:
            return

        tile_w, tile_h = self._bg_tile.get_size()
        offset_y = (-self._camera_y) % tile_h
        start_y = self.game_top - tile_h + offset_y

        x = 0
        while x < self.width:
            y = start_y
            while y < self.game_bottom + tile_h:
                self.screen.blit(self._bg_tile, (int(x), int(round(y))))
                y += tile_h
            x += tile_w

    def _draw_platform(self, platform):
        screen_x = self.game_left + platform.x - platform.width * 0.5
        screen_y = self.game_top + platform.y - self._camera_y
        if screen_y > self.game_bottom + 60 or screen_y < self.game_top - 80:
            return

        rect = pygame.Rect(int(screen_x), int(screen_y), int(platform.width), int(platform.height))

        if platform.kind == "moving":
            base_color = self.moving_platform_color
        elif platform.kind == "breakable":
            base_color = self.break_platform_color
        elif platform.kind == "trampoline":
            base_color = self.trampoline_color
        else:
            base_color = self.platform_color

        border_radius = max(2, int(platform.height * 0.5))
        pygame.draw.rect(self.screen, base_color, rect, border_radius=border_radius)

        highlight_rect = pygame.Rect(
            rect.x + 3,
            rect.y + 2,
            rect.width - 6,
            max(2, rect.height // 3),
        )
        highlight_color = self.platform_highlight if platform.kind == "normal" else base_color
        pygame.draw.rect(self.screen, highlight_color, highlight_rect, border_radius=border_radius)

        shadow_rect = pygame.Rect(
            rect.x + 2,
            rect.bottom - max(4, rect.height // 3),
            rect.width - 4,
            max(4, rect.height // 3),
        )
        shadow_color = self.platform_shadow if platform.kind == "normal" else base_color
        pygame.draw.rect(self.screen, shadow_color, shadow_rect, border_radius=border_radius)

        pygame.draw.rect(self.screen, self.platform_border, rect, 2, border_radius=border_radius)

        if platform.kind == "breakable":
            self._draw_platform_cracks(rect)

        if platform.kind == "moving":
            self._draw_platform_arrows(rect)

        if platform.spring:
            self._draw_spring(rect)

        if platform.kind == "trampoline":
            self._draw_trampoline_detail(rect)

    def _draw_platform_cracks(self, rect: pygame.Rect):
        crack_color = (90, 60, 30)
        center_x = rect.centerx
        for offset in (-rect.width * 0.2, 0, rect.width * 0.2):
            x1 = center_x + offset
            y1 = rect.top + 2
            x2 = center_x + offset + 6
            y2 = rect.bottom - 2
            pygame.draw.line(self.screen, crack_color, (int(x1), int(y1)), (int(x2), int(y2)), 2)

    def _draw_platform_arrows(self, rect: pygame.Rect):
        chevron_color = (245, 245, 245)
        chevron_shadow = (180, 180, 180)
        thickness = max(2, int(rect.height * 0.15))
        size = max(6, int(rect.height * 0.6))
        max_size = int(rect.width * 0.22)
        size = min(size, max_size)

        center_y = rect.centery
        center_x = rect.centerx
        gap = max(6, int(rect.width * 0.08))

        def draw_chevron(cx: int, direction: int):
            half = size * 0.5
            if direction < 0:
                points = [
                    (cx + half, center_y - half),
                    (cx - half, center_y),
                    (cx + half, center_y + half),
                ]
            else:
                points = [
                    (cx - half, center_y - half),
                    (cx + half, center_y),
                    (cx - half, center_y + half),
                ]
            shadow_points = [(x + 1, y + 1) for x, y in points]
            pygame.draw.lines(self.screen, chevron_shadow, False, shadow_points, thickness)
            pygame.draw.lines(self.screen, chevron_color, False, points, thickness)

        draw_chevron(int(center_x - gap), -1)
        draw_chevron(int(center_x + gap), 1)

    def _draw_trampoline_detail(self, rect: pygame.Rect):
        band_rect = pygame.Rect(rect.x + 6, rect.centery - 2, rect.width - 12, 4)
        pygame.draw.rect(self.screen, (255, 220, 220), band_rect)

    def _draw_spring(self, rect: pygame.Rect):
        spring_w = max(12, rect.width * 0.2)
        spring_h = max(8, rect.height * 0.6)
        spring_x = rect.centerx - spring_w * 0.5
        spring_y = rect.top - spring_h + 2
        spring_rect = pygame.Rect(int(spring_x), int(spring_y), int(spring_w), int(spring_h))
        pygame.draw.rect(self.screen, self.spring_color, spring_rect, 2)

        coil_spacing = max(2, int(spring_h // 4))
        for i in range(1, 3):
            y = spring_rect.top + i * coil_spacing
            pygame.draw.line(
                self.screen,
                self.spring_highlight,
                (spring_rect.left + 2, y),
                (spring_rect.right - 2, y),
                2,
            )

    def _draw_monster(self, monster):
        screen_x = self.game_left + monster.x
        screen_y = self.game_top + monster.y - self._camera_y
        if screen_y > self.game_bottom + 80 or screen_y < self.game_top - 120:
            return

        rect = pygame.Rect(
            int(screen_x - monster.width * 0.5),
            int(screen_y - monster.height * 0.5),
            int(monster.width),
            int(monster.height),
        )

        pygame.draw.ellipse(self.screen, self.monster_color, rect)
        pygame.draw.ellipse(self.screen, self.monster_border, rect, 2)

        eye_offset_x = rect.width * 0.2
        eye_offset_y = rect.height * 0.15
        eye_radius = max(4, int(rect.width * 0.12))
        left_eye = (int(rect.centerx - eye_offset_x), int(rect.centery - eye_offset_y))
        right_eye = (int(rect.centerx + eye_offset_x), int(rect.centery - eye_offset_y))
        pygame.draw.circle(self.screen, self.monster_eye, left_eye, eye_radius)
        pygame.draw.circle(self.screen, self.monster_eye, right_eye, eye_radius)
        pygame.draw.circle(self.screen, (20, 20, 20), left_eye, max(2, eye_radius // 2))
        pygame.draw.circle(self.screen, (20, 20, 20), right_eye, max(2, eye_radius // 2))

        tooth_color = (250, 250, 250)
        mouth_y = rect.centery + rect.height * 0.2
        tooth_w = max(4, int(rect.width * 0.1))
        for i in range(-1, 2):
            x = rect.centerx + i * tooth_w * 1.1
            points = [
                (x, mouth_y),
                (x + tooth_w * 0.5, mouth_y + tooth_w),
                (x - tooth_w * 0.5, mouth_y + tooth_w),
            ]
            pygame.draw.polygon(self.screen, tooth_color, points)

    def _draw_players(self, players):
        club_players = []
        for player in players:
            if not player.alive and not player.is_fading():
                continue
            screen_x = int(self.game_left + player.x)
            screen_y = int(self.game_top + player.y - self._camera_y)
            if screen_y < self.game_top - 60 or screen_y > self.game_bottom + 60:
                continue
            if getattr(player, "is_club_member", False):
                club_players.append((player, screen_x, screen_y))
                continue
            self._draw_avatar_at(player, screen_x, screen_y)

        for player, screen_x, screen_y in club_players:
            self._draw_club_glow(player, size=self.player_size, pos=(screen_x, screen_y))
            self._draw_avatar_at(player, screen_x, screen_y)

    def _draw_avatar_at(self, player, screen_x: int, screen_y: int):
        size = max(1, int(round(self.player_size)))
        avatar_surface = self._get_avatar_surface(player, size)
        if hasattr(player, "alpha") and player.alpha < 255:
            avatar_surface = avatar_surface.copy()
            avatar_surface.set_alpha(player.alpha)
        rect = avatar_surface.get_rect(center=(screen_x, screen_y))
        self.screen.blit(avatar_surface, rect)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        if y_pos > self.height - 8:
            y_pos = self.height - 24
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)
        self._club_panel_anchor_y = day_rect.bottom

        # Eliminations list is rendered in _draw_game_ui to align with stats.

    def _draw_club_panel(self, game_state: dict):
        anchor_y = self._club_panel_anchor_y
        self._club_panel_bottom = anchor_y
        if anchor_y is None:
            return
        panel_rect = draw_club_panel(
            self.screen,
            game_state.get("club_spotlight"),
            anchor_y=anchor_y,
            font=self.font_club_panel,
            get_avatar_surface=self._get_avatar_surface,
            glow_cache=self._club_glow_cache,
        )
        if panel_rect is not None:
            self._club_panel_bottom = panel_rect.bottom

    def _draw_game_ui(self, players, game_state: dict):
        alive_count = game_state.get("alive_count")
        leader_height = game_state.get("leader_height")
        record = game_state.get("highscore") or {}
        record_score = record.get("score", 0) or 0
        record_name = record.get("username", "") or ""
        record_label = record.get("label") or "Record"
        show_record = record_score > 0

        if alive_count is None and leader_height is None and not show_record:
            return

        line_count = 0
        if alive_count is not None:
            line_count += 1
        if leader_height is not None:
            line_count += 1
        if show_record:
            line_count += 1

        panel_x = self.game_left + 10
        panel_y = self.game_top + 10
        y_cursor = panel_y
        text_color = (0, 0, 0)
        if alive_count is not None:
            alive_text = self.font_stats.render(f"Alive: {alive_count}", True, text_color)
            self.screen.blit(alive_text, (panel_x, y_cursor))
            y_cursor += 22

        if leader_height is not None:
            height_text = self.font_stats.render(f"Height: {leader_height:.0f}", True, text_color)
            self.screen.blit(height_text, (panel_x, y_cursor))
            y_cursor += 22

        if show_record:
            name = record_name
            if len(name) > 12:
                name = name[:12] + "..."
            record_text = f"Highscore: {int(record_score)}"
            if name:
                record_text = f"{record_text} - {name}"
            record_surface = self.font_small.render(record_text, True, text_color)
            self.screen.blit(record_surface, (panel_x, y_cursor))

        eliminations = game_state.get("recent_eliminations") or []
        if not eliminations:
            return
        list_right_x = self.game_left + self.width - 16
        list_top = panel_y
        if self._club_panel_bottom is not None:
            list_top = max(list_top, int(self._club_panel_bottom + 8))
        label_surface = self.font_eliminations.render(self.elimination_label, True, text_color)
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
            entry_surface = self.font_eliminations.render(display_name, True, text_color)
            entry_rect = entry_surface.get_rect(
                topright=(list_right_x, start_y + idx * line_height)
            )
            self.screen.blit(entry_surface, entry_rect)
