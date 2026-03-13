"""Beacon Blitz renderer."""

import math
from typing import List

import pygame

import config
from shared.renderer_template import RendererTemplate


class BeaconBlitzRenderer(RendererTemplate):
    """Renderer for Beacon Blitz."""

    GAME_TITLE = "BEACON BLITZ"
    GAME_SUBTITLE = "Making my followers battle every day"
    GAME_SUBTITLE_LINE2 = 'Comment "RESULT" to see how you did'
    PLAYER_LABEL = "players"
    GAME_WIDTH = config.FIGHTER_ARENA_RECT[2]
    GAME_HEIGHT = config.FIGHTER_ARENA_RECT[3]

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = config.FIGHTER_ARENA_RECT
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.font_status = pygame.font.Font(None, 26)
        self.font_timer = pygame.font.Font(None, 44)
        self.subtitle_fonts = {size: pygame.font.Font(None, size) for size in (24, 22, 20, 18, 16)}

        self.arena_fill = (210, 210, 215)
        self.arena_border = (40, 40, 40)
        self.grid_color = (200, 200, 205)
        self.beacon_color = (255, 200, 90)
        self.beacon_glow = (255, 230, 160)
        self.pulse_color = (255, 120, 80)
        self.beacon_radius = int(getattr(config, "BEACON_BLITZ_BEACON_RADIUS", 16))
        self.day_counter_offset = int(getattr(config, "BEACON_BLITZ_DAY_COUNTER_OFFSET", 16))

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

        max_width = self.game_right - self.game_left
        line2_surface = self._render_subtitle_line(self.GAME_SUBTITLE_LINE2, max_width)
        line2_rect = line2_surface.get_rect(
            center=(center_x, subtitle_rect.bottom + 6 + (line2_surface.get_height() // 2))
        )
        self.screen.blit(line2_surface, line2_rect)

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
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)

    def _draw_game_area(self, players: List, game_state: dict):
        arena_rect = pygame.Rect(
            self.game_left,
            self.game_top,
            self.game_right - self.game_left,
            self.game_bottom - self.game_top,
        )
        pygame.draw.rect(self.screen, self.arena_fill, arena_rect)
        self._draw_grid(arena_rect)
        pygame.draw.rect(self.screen, self.arena_border, arena_rect, 3)

        beacon = game_state.get("beacon_pos")
        if beacon:
            elapsed = float(game_state.get("elapsed_time", 0.0))
            pulse = game_state.get("round_phase") == "pulse"
            glow_radius = int(self.beacon_radius + 8 + 4 * math.sin(elapsed * 4.0))
            pygame.draw.circle(self.screen, self.beacon_glow, (int(beacon[0]), int(beacon[1])), glow_radius)

            color = self.pulse_color if pulse else self.beacon_color
            pygame.draw.circle(self.screen, color, (int(beacon[0]), int(beacon[1])), self.beacon_radius)
            pygame.draw.circle(self.screen, (50, 50, 50), (int(beacon[0]), int(beacon[1])), self.beacon_radius, 2)

            if pulse:
                ring_radius = int(self.beacon_radius + 22 + 10 * math.sin(elapsed * 6.0))
                pygame.draw.circle(self.screen, self.pulse_color, (int(beacon[0]), int(beacon[1])), ring_radius, 2)

    def _draw_grid(self, arena_rect: pygame.Rect):
        step = 40
        for x in range(arena_rect.left, arena_rect.right, step):
            pygame.draw.line(self.screen, self.grid_color, (x, arena_rect.top), (x, arena_rect.bottom))
        for y in range(arena_rect.top, arena_rect.bottom, step):
            pygame.draw.line(self.screen, self.grid_color, (arena_rect.left, y), (arena_rect.right, y))

    def _draw_players(self, players: List, game_state: dict = None):
        elapsed = 0.0
        if game_state:
            elapsed = float(game_state.get("elapsed_time", 0.0))
        fade_duration = float(getattr(config, "BEACON_BLITZ_FADE_DURATION", config.FADE_DURATION))

        for player in players:
            if not player.alive and not player.is_fading(elapsed, fade_duration):
                continue
            player.update_alpha(elapsed, fade_duration)
            size = player.radius * 2
            self._draw_player_avatar(player, size=size)

    def _draw_game_ui(self, players: List, game_state: dict):
        round_number = game_state.get("round_number", 0)
        time_left = game_state.get("phase_time_left", 0.0)
        alive_count = game_state.get("alive_count", len(players))
        last_eliminated = game_state.get("last_eliminated", 0)
        round_phase = game_state.get("round_phase", "")

        panel_x = self.game_left + 12
        panel_y = self.game_top + 12
        panel = pygame.Surface((200, 86), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, (panel_x, panel_y))

        round_text = self.font_status.render(f"Round {round_number}", True, (255, 255, 255))
        self.screen.blit(round_text, (panel_x + 12, panel_y + 8))

        timer_label = "Pulse" if round_phase == "pulse" else "Rush"
        timer_text = self.font_status.render(f"{timer_label}: {time_left:.1f}s", True, (255, 255, 255))
        self.screen.blit(timer_text, (panel_x + 12, panel_y + 30))

        alive_text = self.font_status.render(f"Alive: {alive_count}", True, (255, 255, 255))
        self.screen.blit(alive_text, (panel_x + 12, panel_y + 52))

        if round_phase == "pulse" and last_eliminated:
            elim_text = self.font_status.render(f"Eliminated: {last_eliminated}", True, (255, 200, 200))
            self.screen.blit(elim_text, (panel_x + 12, panel_y + 72))
