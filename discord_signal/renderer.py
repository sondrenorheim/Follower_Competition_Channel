"""Discord Signal renderer."""
from pathlib import Path
from typing import List

import pygame

import config
from shared.renderer_template import RendererTemplate


class DiscordSignalRenderer(RendererTemplate):
    """Renderer for the Discord Signal game."""

    GAME_TITLE = "DISCORD SIGNAL"
    GAME_SUBTITLE = "Making my Discord Members battle every day"
    PLAYER_LABEL = "players"
    GAME_WIDTH = getattr(
        config,
        "DISCORD_SIGNAL_ARENA_RECT",
        getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
    )[2]
    GAME_HEIGHT = getattr(
        config,
        "DISCORD_SIGNAL_ARENA_RECT",
        getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
    )[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "DISCORD_SIGNAL_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.subtitle_fonts = {size: pygame.font.Font(None, size) for size in (24, 22, 20, 18, 16)}
        self.font_status = pygame.font.Font(None, 26)
        self.font_timer = pygame.font.Font(None, 40)
        self.font_name = pygame.font.Font(None, 16)
        self.day_counter_offset = int(
            getattr(
                config,
                "DISCORD_SIGNAL_DAY_COUNTER_OFFSET",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_OFFSET", 14),
            )
        )
        day_counter_size = int(
            getattr(
                config,
                "DISCORD_SIGNAL_DAY_COUNTER_FONT_SIZE",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_FONT_SIZE", 32),
            )
        )
        self.day_counter_font = pygame.font.Font(None, day_counter_size)
        self.prompt_above_arena_margin = int(
            getattr(
                config,
                "DISCORD_SIGNAL_PROMPT_ABOVE_ARENA_MARGIN",
                getattr(config, "MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN", 8),
            )
        )
        self.show_names_max = int(getattr(config, "DISCORD_SIGNAL_SHOW_NAMES_MAX", 300))

        self.zone_colors = [
            (170, 200, 230),
            (190, 180, 220),
            (180, 220, 200),
            (220, 190, 190),
        ]
        self.safe_glow = (90, 220, 120)
        self.spinner_glow = (110, 255, 140)
        self.zone_border = (40, 40, 40)
        self.open_floor_color = getattr(config, "DISCORD_SIGNAL_OPEN_FLOOR_COLOR", (55, 55, 62))
        self.open_pit_color = getattr(config, "DISCORD_SIGNAL_OPEN_PIT_COLOR", (24, 24, 28))
        self.open_pit_rim_color = getattr(config, "DISCORD_SIGNAL_OPEN_PIT_RIM_COLOR", (82, 82, 90))
        self.discord_logo = None
        self.discord_logo_scaled = None
        self.discord_logo_scaled_size = None
        self._load_discord_logo()

    def _load_discord_logo(self):
        logo_path = Path("discord_logo.png")
        if not logo_path.exists():
            return
        try:
            self.discord_logo = pygame.image.load(str(logo_path)).convert_alpha()
        except pygame.error:
            self.discord_logo = None

    def _draw_title_and_subtitle(self):
        center_x = self.width // 2
        title_y = self.game_top - 70
        subtitle_y = self.game_top - 40

        title_surface = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, title_y))
        self.screen.blit(title_surface, title_rect)

        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, subtitle_y))
        self.screen.blit(subtitle_surface, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_surface = self.font_small.render(prompt_text, True, config.COLOR_TEXT)
            prompt_y = int(self.game_top - self.prompt_above_arena_margin)
            prompt_y = max(prompt_y, subtitle_rect.bottom + 6)
            prompt_rect = prompt_surface.get_rect(center=(center_x, prompt_y))
            self.screen.blit(prompt_surface, prompt_rect)

    def _render_subtitle_line(self, text: str, max_width: int) -> pygame.Surface:
        for size in sorted(self.subtitle_fonts.keys(), reverse=True):
            font = self.subtitle_fonts[size]
            surface = font.render(text, True, config.COLOR_TEXT)
            if surface.get_width() <= max_width:
                return surface
        smallest_font = self.subtitle_fonts[min(self.subtitle_fonts.keys())]
        return smallest_font.render(text, True, config.COLOR_TEXT)

    def _draw_day_counter(self, players: List, game_state: dict):
        total_count = game_state.get("total_count", len(players))
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.day_counter_font.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_area(self, players: List, game_state: dict):
        arena = game_state.get("arena")
        if not arena:
            return
        safe_zone = game_state.get("safe_zone")
        spinner_zone = game_state.get("spinner_zone")
        round_phase = game_state.get("round_phase")
        open_zones = set(game_state.get("open_zones") or [])
        result_elapsed = float(game_state.get("result_elapsed", 0.0))
        result_duration = float(game_state.get("result_duration", 0.0))
        if result_duration > 0:
            open_progress = max(0.0, min(1.0, result_elapsed / result_duration))
        else:
            open_progress = 1.0

        highlight_zone = spinner_zone if round_phase == "spin" else safe_zone

        for zone_id in arena.zones:
            left, top, right, bottom = arena.get_zone_rect(zone_id)
            rect = pygame.Rect(int(left), int(top), int(right - left), int(bottom - top))
            color = self.zone_colors[zone_id % len(self.zone_colors)]
            is_open = round_phase == "result" and zone_id in open_zones
            if is_open:
                self._draw_open_zone(rect, color, open_progress)
            else:
                pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, self.zone_border, rect, 2)
            if highlight_zone is not None and zone_id == highlight_zone:
                glow_rect = rect.inflate(6, 6)
                glow_color = self.spinner_glow if round_phase == "spin" else self.safe_glow
                pygame.draw.rect(self.screen, glow_color, glow_rect, 3)

        border_rect = pygame.Rect(
            int(arena.left),
            int(arena.top),
            int(arena.right - arena.left),
            int(arena.bottom - arena.top),
        )
        pygame.draw.rect(self.screen, self.zone_border, border_rect, 3)

        self._draw_discord_logo(arena)

    def _draw_open_zone(self, rect: pygame.Rect, base_color: tuple, progress: float):
        progress = max(0.0, min(1.0, progress))
        pygame.draw.rect(self.screen, self.open_floor_color, rect)

        panel_color = self._shade_color(base_color, 0.7)
        gap_width = int(rect.width * progress)
        gap_width = min(rect.width, max(0, gap_width))
        left_panel_width = max(0, (rect.width - gap_width) // 2)
        right_panel_width = max(0, rect.width - gap_width - left_panel_width)

        if left_panel_width > 0:
            left_panel = pygame.Rect(rect.left, rect.top, left_panel_width, rect.height)
            pygame.draw.rect(self.screen, panel_color, left_panel)
        if right_panel_width > 0:
            right_panel = pygame.Rect(rect.right - right_panel_width, rect.top, right_panel_width, rect.height)
            pygame.draw.rect(self.screen, panel_color, right_panel)

        if gap_width > 0:
            pit_rect = pygame.Rect(rect.left + left_panel_width, rect.top, gap_width, rect.height)
            pygame.draw.rect(self.screen, self.open_pit_color, pit_rect)
            rim_rect = pit_rect.inflate(0, -max(2, int(rect.height * 0.14)))
            if rim_rect.width > 2 and rim_rect.height > 2:
                pygame.draw.rect(self.screen, self.open_pit_rim_color, rim_rect, 2)

    @staticmethod
    def _shade_color(color: tuple, factor: float) -> tuple:
        return tuple(max(0, min(255, int(channel * factor))) for channel in color)

    def _draw_discord_logo(self, arena):
        if not self.discord_logo:
            return
        size = max(40, int(min(arena.current_width, arena.current_height) * 0.25))
        if self.discord_logo_scaled is None or self.discord_logo_scaled_size != size:
            self.discord_logo_scaled = pygame.transform.smoothscale(self.discord_logo, (size, size))
            self.discord_logo_scaled_size = size
        logo_rect = self.discord_logo_scaled.get_rect(center=(int(arena.center_x), int(arena.center_y)))
        self.screen.blit(self.discord_logo_scaled, logo_rect)

    def _draw_players(self, players: List, game_state: dict = None):
        alive_count = game_state.get("alive_count", len(players)) if game_state else len(players)
        show_names = alive_count <= self.show_names_max

        for player in players:
            if not player.alive and not player.falling:
                continue
            self._draw_player_avatar(player, size=player.radius * 2)
            if show_names and player.alive:
                self._draw_player_name(player)

    def _draw_player_name(self, player):
        name_surface = self.font_name.render(player.username, True, config.COLOR_TEXT)
        offset_y = int(player.radius + (name_surface.get_height() / 2) + 2)
        name_rect = name_surface.get_rect(center=(int(player.x), int(player.y) + offset_y))
        self.screen.blit(name_surface, name_rect)

    def _draw_game_ui(self, players: List, game_state: dict):
        round_number = game_state.get("round_number", 0)
        time_left = game_state.get("phase_time_left", 0.0)
        alive_count = game_state.get("alive_count", len(players))
        last_eliminated = game_state.get("last_eliminated", 0)
        safe_zone = game_state.get("safe_zone")
        spinner_zone = game_state.get("spinner_zone")
        round_phase = game_state.get("round_phase")

        panel_x = self.game_left + 12
        panel_y = self.game_top + 12
        panel = pygame.Surface((220, 92), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        round_text = self.font_status.render(f"Round {round_number}", True, (255, 255, 255))
        self.screen.blit(round_text, (panel_x + 12, panel_y + 8))

        phase_label = "Pick"
        if round_phase == "spin":
            phase_label = "Spin"
        elif round_phase == "result":
            phase_label = "Drop"
        timer_text = self.font_status.render(f"{phase_label}: {time_left:.1f}s", True, (255, 255, 255))
        self.screen.blit(timer_text, (panel_x + 12, panel_y + 30))

        alive_text = self.font_status.render(f"Alive: {alive_count}", True, (255, 255, 255))
        self.screen.blit(alive_text, (panel_x + 12, panel_y + 52))

        zone_label = None
        zone_color = (120, 255, 160)
        if round_phase == "spin" and spinner_zone is not None:
            zone_label = f"Spinner: {spinner_zone + 1}"
        elif round_phase == "result" and safe_zone is not None:
            zone_label = f"Safe Zone: {safe_zone + 1}"
        elif round_phase == "selection":
            zone_label = "Choose your square"

        if zone_label:
            zone_surface = self.font_status.render(zone_label, True, zone_color)
            self.screen.blit(zone_surface, (panel_x + 12, panel_y + 72))

        if last_eliminated:
            elim_text = self.font_status.render(f"Eliminated: {last_eliminated}", True, (255, 200, 200))
            elim_rect = elim_text.get_rect(center=(self.width // 2, self.game_top - 12))
            self.screen.blit(elim_text, elim_rect)
