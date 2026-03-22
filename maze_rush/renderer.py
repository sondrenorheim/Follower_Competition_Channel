import pygame
import math

import config
from shared import RendererTemplate
from shared.platform_targets import (
    format_profile_text,
    get_youtube_game_profile,
    is_native_youtube_game,
    normalize_platform_target,
)


class MazeRushRenderer(RendererTemplate):
    GAME_TITLE = "MAZE RUSH"
    PLAYER_LABEL = "players"
    GAME_WIDTH = getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT)[2]
    GAME_HEIGHT = getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT)[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "MAZE_RUSH_ARENA_RECT",
            config.FIGHTER_ARENA_RECT,
        )
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.wall_color = getattr(config, "MAZE_RUSH_WALL_COLOR", (30, 30, 30))
        self.floor_color = getattr(config, "MAZE_RUSH_FLOOR_COLOR", (180, 180, 190))
        self.border_color = getattr(config, "MAZE_RUSH_BORDER_COLOR", (0, 0, 0))
        self.start_color = getattr(config, "MAZE_RUSH_START_COLOR", (80, 200, 120))
        self.exit_color = getattr(config, "MAZE_RUSH_EXIT_COLOR", (255, 120, 80))
        self.wall_thickness = int(getattr(config, "MAZE_RUSH_WALL_THICKNESS", 3))
        self.marker_scale = float(getattr(config, "MAZE_RUSH_MARKER_SCALE", 0.55))
        self.player_size = float(getattr(config, "MAZE_RUSH_PLAYER_SIZE", 12))
        self.day_counter_offset = int(getattr(config, "MAZE_RUSH_DAY_COUNTER_OFFSET", 18))
        day_counter_size = int(getattr(config, "MAZE_RUSH_DAY_COUNTER_FONT_SIZE", 32))
        self.day_counter_font = pygame.font.Font(None, day_counter_size)
        self.show_title = bool(getattr(config, "MAZE_RUSH_SHOW_TITLE", False))
        self.show_subtitle = bool(getattr(config, "MAZE_RUSH_SHOW_SUBTITLE", False))
        self.header_y_shift = int(getattr(config, "SQUARE_ARENA_HEADER_Y_SHIFT", -4))
        self.prompt_above_arena_margin = int(getattr(config, "MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN", 8))
        self.endscreen_y_offset = int(getattr(config, "MAZE_RUSH_ENDSCREEN_Y_OFFSET", 24))
        self.platform_target = normalize_platform_target(getattr(config, "PLATFORM_TARGET", "instagram"))
        self.native_youtube_mode = is_native_youtube_game("maze_rush", self.platform_target)
        self.youtube_profile = get_youtube_game_profile("maze_rush")
        self.font_youtube_hook = pygame.font.Font(None, 42)
        self.font_youtube_subhook = pygame.font.Font(None, 28)
        self.font_youtube_cta = pygame.font.Font(None, 30)
        self.font_youtube_result = pygame.font.Font(None, 34)

        self.club_glow_color = getattr(config, "MAZE_RUSH_CLUB_GLOW_COLOR", (255, 240, 190))
        self.club_glow_alpha = int(getattr(config, "MAZE_RUSH_CLUB_GLOW_ALPHA", 180))
        self.club_glow_layers = int(getattr(config, "MAZE_RUSH_CLUB_GLOW_LAYERS", 3))
        self.club_glow_padding = int(getattr(config, "MAZE_RUSH_CLUB_GLOW_PADDING", 3))
        self._club_glow_cache = {}
        self.club_panel_enabled = bool(getattr(config, "MAZE_RUSH_CLUB_PANEL_ENABLED", True))
        self.club_panel_text = str(getattr(
            config,
            "MAZE_RUSH_CLUB_PANEL_TEXT",
            "Club members stay visible\nwith a holy light.",
        ))
        self.club_panel_width = int(getattr(config, "MAZE_RUSH_CLUB_PANEL_WIDTH", 160))
        self.club_panel_height = int(getattr(config, "MAZE_RUSH_CLUB_PANEL_HEIGHT", 80))
        self.club_panel_padding = int(getattr(config, "MAZE_RUSH_CLUB_PANEL_PADDING", 6))
        self.club_panel_alpha = int(getattr(config, "MAZE_RUSH_CLUB_PANEL_ALPHA", 150))
        self.club_avatar_size = int(getattr(config, "MAZE_RUSH_CLUB_PANEL_AVATAR_SIZE", 42))
        self.club_panel_text_size = int(getattr(config, "MAZE_RUSH_CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, self.club_panel_text_size)

        self._maze_surface = None
        self._maze_signature = None

    def render_frame(self, players, game_state: dict):
        self._latest_game_state = dict(game_state)
        self.screen.fill(config.COLOR_BACKGROUND)
        self._draw_game_area(players, game_state)
        self._draw_players(players)
        if self.native_youtube_mode:
            self._draw_youtube_hook(players, game_state)
        else:
            self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(players, game_state)
        if not self.native_youtube_mode:
            self._draw_club_panel(game_state)

        if game_state.get('show_leaderboards'):
            self._draw_end_game_display(
                game_state.get('current_game_leaderboard', []),
                game_state.get('all_time_leaderboard', []),
                game_state.get('winner')
            )

    def _draw_youtube_hook(self, players, game_state: dict):
        elapsed = float(game_state.get("elapsed_time") or 0.0)
        hook_end = float(self.youtube_profile.get("hook_end_seconds", 1.8) or 1.8)
        if elapsed > hook_end:
            return

        participant_count = int(game_state.get("requested_count") or len(players) or 0)
        primary_text = format_profile_text(self.youtube_profile.get("hook_primary"), participant_count)
        secondary_text = format_profile_text(self.youtube_profile.get("hook_secondary"), participant_count)

        panel_width = int(self.width * 0.84)
        panel_height = 74 if secondary_text else 52
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 172))
        panel_rect = panel.get_rect(center=(self.width // 2, max(40, self.game_top - 46)))
        self.screen.blit(panel, panel_rect)

        if primary_text:
            primary_surface = self.font_youtube_hook.render(primary_text, True, (255, 255, 255))
            primary_rect = primary_surface.get_rect(center=(self.width // 2, panel_rect.y + 22))
            self.screen.blit(primary_surface, primary_rect)

        if secondary_text:
            secondary_surface = self.font_youtube_subhook.render(secondary_text, True, (255, 220, 120))
            secondary_rect = secondary_surface.get_rect(center=(self.width // 2, panel_rect.y + panel_height - 18))
            self.screen.blit(secondary_surface, secondary_rect)

    def _draw_title_and_subtitle(self):
        arena_top = self.game_top
        subtitle_rect = None

        if self.show_title:
            title_font = pygame.font.Font(None, 56)
            title_text = title_font.render(self.GAME_TITLE, True, config.COLOR_TEXT)
            title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70 + self.header_y_shift))
            self.screen.blit(title_text, title_rect)

        if self.show_subtitle:
            subtitle_font = pygame.font.Font(None, 32)
            subtitle_text = subtitle_font.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
            subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 40 + self.header_y_shift))
            self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_font = pygame.font.Font(None, 24)
            prompt_surface = prompt_font.render(prompt_text, True, config.COLOR_TEXT)
            prompt_y = int(arena_top - self.prompt_above_arena_margin)
            if subtitle_rect is not None:
                prompt_y = max(prompt_y, subtitle_rect.bottom + 6)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, prompt_y))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, players, game_state: dict):
        maze = game_state.get("maze")
        if maze:
            self._ensure_maze_surface(maze)
            if self._maze_surface:
                self.screen.blit(self._maze_surface, (maze.origin_x, maze.origin_y))

        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.border_color, arena_rect, 3)

    def _ensure_maze_surface(self, maze):
        if self._maze_signature == maze.signature and self._maze_surface is not None:
            return

        self._maze_signature = maze.signature
        surface = pygame.Surface((maze.width, maze.height))
        surface.fill(self.floor_color)

        marker_size = max(4, int(maze.cell_size * self.marker_scale))
        start_center = maze.cell_center(maze.start_cell, local=True)
        exit_center = maze.cell_center(maze.exit_cell, local=True)
        start_rect = pygame.Rect(0, 0, marker_size, marker_size)
        start_rect.center = (int(start_center[0]), int(start_center[1]))
        exit_rect = pygame.Rect(0, 0, marker_size, marker_size)
        exit_rect.center = (int(exit_center[0]), int(exit_center[1]))
        pygame.draw.rect(surface, self.start_color, start_rect)
        pygame.draw.rect(surface, self.exit_color, exit_rect)

        for (x1, y1), (x2, y2) in maze.wall_segments:
            pygame.draw.line(
                surface,
                self.wall_color,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                self.wall_thickness,
            )

        self._maze_surface = surface

    def _draw_players(self, players):
        for player in players:
            if not self.native_youtube_mode and getattr(player, "is_club_member", False):
                self._draw_club_glow(player)
            self._draw_player_avatar(player, size=self.player_size)

    def _get_avatar_surface(self, player, size: int) -> pygame.Surface:
        size = max(1, int(round(size)))
        username = str(getattr(player, "username", "") or "")
        avatar_image = getattr(player, "avatar_image", None)
        has_avatar = bool(avatar_image)
        fallback_color = tuple(getattr(player, "color", (100, 100, 255)))
        initials = self._get_avatar_initials(username)
        cache_key = (username, size, has_avatar, fallback_color, initials)
        cached = self.avatar_cache.get(cache_key)
        if cached is not None:
            return cached

        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        radius = size // 2

        if has_avatar:
            pil_resized = avatar_image.resize((size, size))
            mode = pil_resized.mode
            data = pil_resized.tobytes()
            img_surface = pygame.image.fromstring(data, (size, size), mode)
            mask = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(mask, (255, 255, 255, 255), center, radius)
            img_surface = img_surface.convert_alpha()
            img_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(img_surface, (0, 0))
        else:
            pygame.draw.circle(surface, fallback_color, center, radius)
            self._draw_avatar_initials(surface, initials, size)

        pygame.draw.circle(surface, (0, 0, 0), center, radius, config.FOLLOWER_BORDER_WIDTH)
        self.avatar_cache[cache_key] = surface
        return surface

    def _get_avatar_initials(self, username: str) -> str:
        clean = username.strip().lstrip("@")
        if not clean:
            return "?"
        letters = "".join(ch for ch in clean if ch.isalpha())
        if letters:
            return letters[:2].upper()
        return clean[:2].upper()

    def _draw_avatar_initials(self, avatar_surface: pygame.Surface, initials: str, size: int) -> None:
        if not initials:
            return

        max_text_width = int(size * 0.72)
        max_text_height = int(size * 0.62)
        font_size = max(10, int(size * 0.58))
        text_surface = None
        while font_size >= 8:
            font = pygame.font.Font(None, font_size)
            candidate = font.render(initials, True, (255, 255, 255))
            if candidate.get_width() <= max_text_width and candidate.get_height() <= max_text_height:
                text_surface = candidate
                break
            font_size -= 1

        if text_surface is None:
            font = pygame.font.Font(None, 8)
            text_surface = font.render(initials, True, (255, 255, 255))

        text_rect = text_surface.get_rect(center=(size // 2, size // 2))
        avatar_surface.blit(text_surface, text_rect)

    def _draw_club_glow(self, player, size: float = None, pos: tuple = None):
        if size is None:
            size = self.player_size
        radius = max(2, int(round(float(size) * 0.5)))
        cache_key = (radius, self.club_glow_color, self.club_glow_alpha, self.club_glow_layers, self.club_glow_padding)
        surface = self._club_glow_cache.get(cache_key)

        if surface is None:
            glow_radius = radius + self.club_glow_padding + self.club_glow_layers
            size = glow_radius * 2 + 4
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            center = (size // 2, size // 2)

            base_radius = radius + self.club_glow_padding
            for i in range(self.club_glow_layers):
                alpha = int(self.club_glow_alpha * (1.0 - (i / max(1, self.club_glow_layers))))
                ring_radius = base_radius + i
                pygame.draw.circle(
                    surface,
                    (*self.club_glow_color, alpha),
                    center,
                    ring_radius,
                    width=2,
                )

            inner_alpha = min(255, self.club_glow_alpha + 40)
            pygame.draw.circle(
                surface,
                (*self.club_glow_color, inner_alpha),
                center,
                radius + 1,
                width=2,
            )

            self._club_glow_cache[cache_key] = surface

        if pos is None:
            pos = (int(player.x), int(player.y))
        rect = surface.get_rect(center=(int(pos[0]), int(pos[1])))
        self.screen.blit(surface, rect)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = int(game_state.get("requested_count") or len(players) or 0)
        if self.native_youtube_mode:
            day_text = f"{total_count:,} players in this maze"
        else:
            day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.day_counter_font.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_ui(self, players, game_state: dict):
        elapsed = game_state.get("elapsed_time")
        leader_name = game_state.get("leader_name")
        if self.native_youtube_mode:
            remaining_count = int(game_state.get("remaining_count") or 0)
            escaped_count = int(game_state.get("escaped_count") or 0)
            panel_w = 220
            panel_h = 76
            panel_x = self.game_left + 10
            panel_y = self.game_top + 10
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 118))
            self.screen.blit(panel, (panel_x, panel_y))

            remaining_surface = self.font_stats.render(f"Remaining: {remaining_count}", True, (255, 255, 255))
            escaped_surface = self.font_stats.render(f"Escaped: {escaped_count}", True, (255, 255, 255))
            self.screen.blit(remaining_surface, (panel_x + 12, panel_y + 8))
            self.screen.blit(escaped_surface, (panel_x + 12, panel_y + 30))
            if elapsed is not None:
                time_surface = self.font_small.render(f"Time {elapsed:.1f}s", True, (255, 255, 255))
                self.screen.blit(time_surface, (panel_x + 12, panel_y + 54))
            return

        if elapsed is None and not leader_name:
            return

        panel_w = 220
        panel_h = 56
        panel_x = self.game_left + 10
        panel_y = self.game_top + 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        if elapsed is not None:
            time_text = self.font_stats.render(f"Time {elapsed:.1f}s", True, (255, 255, 255))
            self.screen.blit(time_text, (panel_x + 12, panel_y + 8))

        if leader_name:
            leader_surface = self.font_small.render(f"Leader: {leader_name}", True, (255, 255, 255))
            self.screen.blit(leader_surface, (panel_x + 12, panel_y + 30))

    def _draw_club_panel(self, game_state: dict):
        if self.native_youtube_mode:
            return
        if not self.club_panel_enabled:
            return
        spotlight = game_state.get("club_spotlight")
        if spotlight is None:
            return

        panel_w = self.club_panel_width
        panel_x = int((self.width - panel_w) / 2)

        # Measure text and size the panel/portrait to match text height.
        min_avatar_size = 16
        max_avatar_size = max(min_avatar_size, int(panel_w * 0.45))
        avatar_size = max(min_avatar_size, min(max_avatar_size, int(self.club_avatar_size)))
        line_height = self.font_club_panel.get_height()
        line_gap = max(0, self.font_club_panel.get_linesize() - line_height)
        lines = []
        text_height = line_height

        for _ in range(4):
            text_area_w = panel_w - (self.club_panel_padding * 3) - avatar_size
            if text_area_w < 40:
                text_area_w = 40
            lines = self._wrap_panel_text(self.club_panel_text, text_area_w)
            if not lines:
                lines = [""]
            text_height = (line_height * len(lines)) + (line_gap * max(0, len(lines) - 1))
            new_avatar_size = max(min_avatar_size, min(max_avatar_size, int(text_height)))
            if new_avatar_size == avatar_size:
                break
            avatar_size = new_avatar_size

        text_area_w = panel_w - (self.club_panel_padding * 3) - avatar_size
        if text_area_w < 40:
            text_area_w = 40
        lines = self._wrap_panel_text(self.club_panel_text, text_area_w)
        if not lines:
            lines = [""]
        text_height = (line_height * len(lines)) + (line_gap * max(0, len(lines) - 1))
        panel_h = text_height

        day_y = int(self.game_bottom + self.day_counter_offset)
        panel_y = int(day_y + (self.font_day.get_height() / 2) + 8)
        if panel_y + panel_h > self.height - 6:
            panel_y = max(6, self.height - panel_h - 6)

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, max(0, min(255, self.club_panel_alpha))))
        self.screen.blit(panel, (panel_x, panel_y))

        text_x = panel_x + self.club_panel_padding
        text_y = panel_y + max(0, int((panel_h - text_height) / 2))

        for line in lines:
            text_surface = self.font_club_panel.render(line, True, (245, 245, 245))
            self.screen.blit(text_surface, (text_x, text_y))
            text_y += line_height + line_gap

        avatar_center_x = panel_x + panel_w - self.club_panel_padding - (avatar_size // 2)
        avatar_center_y = panel_y + (panel_h // 2)
        self._draw_club_glow(
            spotlight,
            size=avatar_size,
            pos=(avatar_center_x, avatar_center_y),
        )
        avatar_surface = self._get_avatar_surface(spotlight, avatar_size)
        avatar_rect = avatar_surface.get_rect(center=(avatar_center_x, avatar_center_y))
        self.screen.blit(avatar_surface, avatar_rect)

    def _wrap_panel_text(self, text: str, max_width: int):
        lines = []
        for raw_line in text.splitlines():
            words = raw_line.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                test = f"{current} {word}"
                if self.font_club_panel.size(test)[0] <= max_width:
                    current = test
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def _draw_end_game_display(self, current_game_board: list, all_time_board: list, winner=None):
        """
        Maze Rush override:
        Shift winner + leaderboard down so they fit better inside Instagram 1:1 crop.
        """
        if self.native_youtube_mode:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            self.screen.blit(overlay, (0, 0))
            latest_state = getattr(self, "_latest_game_state", {}) or {}
            escaped_count = int(latest_state.get("escaped_count") or 0)
            participant_count = int(latest_state.get("participant_count") or 0)

            title = self.font_winner.render("MAZE COMPLETE", True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.width // 2, int(self.height * 0.16)))
            self.screen.blit(title, title_rect)

            if winner:
                avatar_size = int(self.width * 0.15)
                avatar_surface = self._get_avatar_surface(winner, avatar_size)
                avatar_rect = avatar_surface.get_rect(center=(self.width // 2, int(self.height * 0.31)))
                self.screen.blit(avatar_surface, avatar_rect)

                winner_surface = self.font_youtube_result.render(
                    f"Winner: {winner.username}",
                    True,
                    (255, 255, 255),
                )
                winner_rect = winner_surface.get_rect(center=(self.width // 2, int(self.height * 0.43)))
                self.screen.blit(winner_surface, winner_rect)

            summary_surface = self.font_youtube_result.render(
                f"Escaped: {escaped_count}/{participant_count}",
                True,
                (255, 255, 255),
            )
            summary_rect = summary_surface.get_rect(center=(self.width // 2, int(self.height * 0.50)))
            self.screen.blit(summary_surface, summary_rect)

            cta_text = str(self.youtube_profile.get("cta_text", "") or "")
            ending_text = str(self.youtube_profile.get("ending_text", "") or "")
            if ending_text:
                ending_surface = self.font_youtube_result.render(ending_text, True, (255, 220, 120))
                ending_rect = ending_surface.get_rect(center=(self.width // 2, int(self.height * 0.58)))
                self.screen.blit(ending_surface, ending_rect)

            if cta_text:
                cta_panel = pygame.Surface((int(self.width * 0.82), 52), pygame.SRCALPHA)
                cta_panel.fill((255, 255, 255, 24))
                cta_rect = cta_panel.get_rect(center=(self.width // 2, int(self.height * 0.72)))
                self.screen.blit(cta_panel, cta_rect)
                cta_surface = self.font_youtube_cta.render(cta_text, True, (255, 255, 255))
                cta_text_rect = cta_surface.get_rect(center=cta_rect.center)
                self.screen.blit(cta_surface, cta_text_rect)
            return

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        y_shift = self.endscreen_y_offset
        if winner:
            self._draw_winner_display(winner, y_offset=y_shift)

        panel_width = int(self.width * 0.44 * 1.2)
        start_y = int(self.height * 0.365) + y_shift
        center_panel_x = (self.width - panel_width) // 2

        self._draw_leaderboard_panel(
            entries=current_game_board[:10],
            x=center_panel_x,
            y=start_y,
            width=panel_width,
            title_line1="CURRENT GAME",
            title_line2="TOP 10",
            title_color=(0, 200, 255),
            is_current_game=True,
        )

    def _draw_winner_display(self, winner, y_offset: int = 0):
        """
        Draw winner spotlight with optional vertical offset for square-crop safety.
        """
        pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))
        title_color = (255, int(215 + pulse * 40), 0)

        title = self.font_winner.render("WINNER!", True, title_color)
        title_y = int(self.height * 0.08) + y_offset
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title, title_rect)

        winner_y = int(self.height * 0.22) + y_offset

        spotlight_radius = int(60 + pulse * 15)
        for i in range(3):
            spotlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            radius = spotlight_radius + i * 20
            alpha = int(50 / (i + 1))
            pygame.draw.circle(
                spotlight,
                (255, 255, 0, alpha),
                (self.width // 2, winner_y),
                radius,
            )
            self.screen.blit(spotlight, (0, 0))

        avatar_size = int(self.width * 0.15)
        avatar_surface = self._get_avatar_surface(winner, avatar_size)
        avatar_rect = avatar_surface.get_rect(center=(self.width // 2, winner_y))
        self.screen.blit(avatar_surface, avatar_rect)

        name_text = self.font_winner_name.render(winner.username, True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(self.width // 2, winner_y + avatar_size // 2 + 30))
        self.screen.blit(name_text, name_rect)
