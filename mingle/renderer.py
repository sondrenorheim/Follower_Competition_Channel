"""
Mingle Renderer - draws arena, rooms, players, and round status.
"""

import math
from pathlib import Path
from typing import List

import pygame

import config
from shared.renderer_template import RendererTemplate


class MingleRenderer(RendererTemplate):
    """Renderer for the Mingle game."""

    GAME_TITLE = "MINGLE"
    GAME_SUBTITLE = "Making my Discord Members battle every day"
    GAME_SUBTITLE_LINE2 = "Join the Discord server to enter the next battle. Link in bio"
    PLAYER_LABEL = "players"

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        self.font_status = pygame.font.Font(None, 26)
        self.font_round = pygame.font.Font(None, 30)
        self.subtitle_fonts = {
            size: pygame.font.Font(None, size) for size in (24, 22, 20, 18, 16)
        }

        self.arena_fill = (220, 220, 210)
        self.arena_border = (60, 60, 60)
        self.platform_fill = (200, 200, 190)
        self.platform_border = (80, 80, 80)
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
        title_y = self.game_top - 100
        subtitle_y = self.game_top - 60

        title_surface = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, title_y))
        self.screen.blit(title_surface, title_rect)

        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, subtitle_y))
        self.screen.blit(subtitle_surface, subtitle_rect)

    def _draw_day_counter(self, players: List, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        day_y = self.game_bottom + 12

        max_width = self.game_right - self.game_left
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, day_y))
        self.screen.blit(day_surface, day_rect)

        line2_surface = self._render_subtitle_line(self.GAME_SUBTITLE_LINE2, max_width)
        line2_rect = line2_surface.get_rect(center=(self.width // 2, day_y + (line2_surface.get_height() + 6)))
        self.screen.blit(line2_surface, line2_rect)

    def _draw_game_area(self, players: List, game_state: dict):
        arena = game_state.get("arena")
        if not arena:
            return

        center_x, center_y = arena.get_center()
        radius = int(arena.get_radius())

        pygame.draw.circle(self.screen, self.arena_fill, (int(center_x), int(center_y)), radius)
        pygame.draw.circle(self.screen, self.arena_border, (int(center_x), int(center_y)), radius, 4)

        platform_radius = int(getattr(arena, "platform_radius", radius * 0.5))
        pygame.draw.circle(self.screen, self.platform_fill, (int(center_x), int(center_y)), platform_radius)
        pygame.draw.circle(self.screen, self.platform_border, (int(center_x), int(center_y)), platform_radius, 2)

        round_phase = game_state.get("round_phase", "")
        phase = game_state.get("phase", "")
        platform_angle = game_state.get("platform_angle", 0.0)
        self._draw_discord_logo((center_x, center_y), platform_radius, platform_angle)

        rooms = game_state.get("rooms", [])
        active_ids = set(game_state.get("active_room_ids", []))
        show_all_colors = phase in ("intro", "countdown") or round_phase == "mixing"

        for room in rooms:
            half_width = room.width * 0.5
            half_height = room.height * 0.5

            radial_x = math.cos(room.angle)
            radial_y = math.sin(room.angle)
            tangent_x = -radial_y
            tangent_y = radial_x

            corners = [
                (
                    room.center[0] + tangent_x * half_width + radial_x * half_height,
                    room.center[1] + tangent_y * half_width + radial_y * half_height,
                ),
                (
                    room.center[0] - tangent_x * half_width + radial_x * half_height,
                    room.center[1] - tangent_y * half_width + radial_y * half_height,
                ),
                (
                    room.center[0] - tangent_x * half_width - radial_x * half_height,
                    room.center[1] - tangent_y * half_width - radial_y * half_height,
                ),
                (
                    room.center[0] + tangent_x * half_width - radial_x * half_height,
                    room.center[1] + tangent_y * half_width - radial_y * half_height,
                ),
            ]

            if show_all_colors or room.index in active_ids:
                fill_color = room.color
                border_color = (25, 25, 25)
            else:
                fill_color = (140, 140, 140)
                border_color = (60, 60, 60)

            pygame.draw.polygon(self.screen, fill_color, corners)
            pygame.draw.polygon(self.screen, border_color, corners, 2)

            # Remove the inner edge to suggest an opening on the short side.
            inner_center = (
                room.center[0] - radial_x * half_height,
                room.center[1] - radial_y * half_height,
            )
            inner_left = (
                inner_center[0] - tangent_x * half_width,
                inner_center[1] - tangent_y * half_width,
            )
            inner_right = (
                inner_center[0] + tangent_x * half_width,
                inner_center[1] + tangent_y * half_width,
            )
            is_active = room.index in active_ids
            if round_phase == "scramble" and is_active and not room.locked:
                pygame.draw.line(self.screen, fill_color, inner_left, inner_right, 3)
            else:
                pygame.draw.line(self.screen, border_color, inner_left, inner_right, 3)

    def _draw_discord_logo(self, center: tuple, platform_radius: int, angle: float):
        if not self.discord_logo:
            return

        size = max(40, int(platform_radius * 0.65))
        if self.discord_logo_scaled is None or self.discord_logo_scaled_size != size:
            self.discord_logo_scaled = pygame.transform.smoothscale(self.discord_logo, (size, size))
            self.discord_logo_scaled_size = size

        rotated = pygame.transform.rotate(self.discord_logo_scaled, -math.degrees(angle))
        logo_rect = rotated.get_rect(center=(int(center[0]), int(center[1])))
        self.screen.blit(rotated, logo_rect)

    def _render_subtitle_line(self, text: str, max_width: int) -> pygame.Surface:
        for size in sorted(self.subtitle_fonts.keys(), reverse=True):
            font = self.subtitle_fonts[size]
            surface = font.render(text, True, config.COLOR_TEXT)
            if surface.get_width() <= max_width:
                return surface

        smallest_font = self.subtitle_fonts[min(self.subtitle_fonts.keys())]
        return smallest_font.render(text, True, config.COLOR_TEXT)

    def _draw_players(self, players: List):
        for player in players:
            if not player.alive and player.is_fading():
                self._draw_player_avatar(player)

        for player in players:
            if player.alive:
                self._draw_player_avatar(player)

    def _draw_game_ui(self, players: List, game_state: dict):
        phase = game_state.get("phase", "playing")
        round_phase = game_state.get("round_phase", "")
        round_number = game_state.get("round_number", 0)
        round_count = game_state.get("round_count", 0)
        group_size = game_state.get("group_size", 0)
        group_min = game_state.get("group_size_min", group_size)
        group_max = game_state.get("group_size_max", group_size)
        time_left = int(math.ceil(game_state.get("phase_time_left", 0)))
        alive_count = game_state.get("alive_count", len(players))
        eliminated = game_state.get("last_eliminated", 0)

        x = self.game_left + 12
        y = self.game_top + 12

        if phase == "countdown":
            text = self.font_round.render("Get Ready...", True, config.COLOR_TEXT)
            self.screen.blit(text, (x, y))
            return

        if phase == "finished":
            return

        round_label = f"Round {round_number}/{round_count}" if round_count else f"Round {round_number}"
        round_surface = self.font_round.render(round_label, True, config.COLOR_TEXT)
        self.screen.blit(round_surface, (x, y))

        y += 28
        if round_phase == "mixing":
            phase_text = "Mixing on the platform"
        elif round_phase == "scramble":
            if group_min and group_max and group_min != group_max:
                phase_text = f"Find rooms of {group_min}-{group_max}"
            else:
                phase_text = f"Find rooms of {group_size}"
        elif round_phase == "resolve":
            phase_text = "Doors locked"
        else:
            phase_text = "Waiting"

        phase_surface = self.font_status.render(phase_text, True, config.COLOR_TEXT)
        self.screen.blit(phase_surface, (x, y))

        y += 22
        timer_surface = self.font_status.render(f"Time: {time_left}s", True, config.COLOR_TEXT)
        self.screen.blit(timer_surface, (x, y))

        y += 22
        alive_surface = self.font_status.render(f"Alive: {alive_count}", True, config.COLOR_TEXT)
        self.screen.blit(alive_surface, (x, y))

        if round_phase == "resolve" and eliminated:
            y += 22
            elim_surface = self.font_status.render(f"Eliminated: {eliminated}", True, config.COLOR_TEXT)
            self.screen.blit(elim_surface, (x, y))
