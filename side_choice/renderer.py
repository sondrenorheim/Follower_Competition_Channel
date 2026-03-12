"""
Side Choice renderer.
"""

import math
import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class SideChoiceRenderer(RendererTemplate):
    GAME_TITLE = "HEADS / TAILS"
    PLAYER_LABEL = "players"

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "SIDE_CHOICE_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", (20, 230, 500, 500)),
        )
        self.game_left = int(arena_x)
        self.game_top = int(arena_y)
        self.game_right = self.game_left + int(arena_w)
        self.game_bottom = self.game_top + int(arena_h)
        self.left_color = getattr(config, "SIDE_CHOICE_LEFT_COLOR", (190, 200, 210))
        self.right_color = getattr(config, "SIDE_CHOICE_RIGHT_COLOR", (210, 190, 200))
        self.open_color = getattr(config, "SIDE_CHOICE_OPEN_COLOR", (45, 45, 50))
        self.border_color = getattr(config, "SIDE_CHOICE_BORDER_COLOR", (0, 0, 0))
        self.split_color = getattr(config, "SIDE_CHOICE_SPLIT_LINE_COLOR", (40, 40, 40))
        self.day_counter_offset = int(
            getattr(
                config,
                "SIDE_CHOICE_DAY_COUNTER_OFFSET",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_OFFSET", 14),
            )
        )
        day_counter_size = int(
            getattr(
                config,
                "SIDE_CHOICE_DAY_COUNTER_FONT_SIZE",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_FONT_SIZE", 32),
            )
        )
        self.day_counter_font = pygame.font.Font(None, day_counter_size)
        self.prompt_above_arena_margin = int(
            getattr(
                config,
                "SIDE_CHOICE_PROMPT_ABOVE_ARENA_MARGIN",
                getattr(config, "MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN", 8),
            )
        )
        status_size = int(getattr(config, "SIDE_CHOICE_STATUS_TEXT_SIZE", 36))
        self.font_status = pygame.font.Font(None, status_size)
        coin_size = int(getattr(config, "SIDE_CHOICE_COIN_TEXT_SIZE", 26))
        self.font_coin = pygame.font.Font(None, coin_size)
        self.coin_color = getattr(config, "SIDE_CHOICE_COIN_COLOR", (240, 200, 80))
        self.coin_edge_color = getattr(config, "SIDE_CHOICE_COIN_EDGE_COLOR", (120, 90, 30))
        self.coin_text_color = getattr(config, "SIDE_CHOICE_COIN_TEXT_COLOR", (40, 30, 10))
        self.coin_rim_color = getattr(
            config,
            "SIDE_CHOICE_COIN_RIM_COLOR",
            self.coin_edge_color,
        )
        inner_color = getattr(config, "SIDE_CHOICE_COIN_INNER_COLOR", None)
        if inner_color is None:
            inner_color = self._shade_color(self.coin_color, 1.08)
        self.coin_inner_color = inner_color
        self.coin_shine_color = getattr(config, "SIDE_CHOICE_COIN_SHINE_COLOR", (255, 250, 220))
        self.coin_radius = int(getattr(config, "SIDE_CHOICE_COIN_RADIUS", 26))
        self.coin_offset = int(getattr(config, "SIDE_CHOICE_COIN_OFFSET", 32))
        self.coin_flips = int(getattr(config, "SIDE_CHOICE_COIN_FLIP_TURNS", 8))
        self.coin_shadow_alpha = int(getattr(config, "SIDE_CHOICE_COIN_SHADOW_ALPHA", 120))
        self.coin_shadow_offset = int(getattr(config, "SIDE_CHOICE_COIN_SHADOW_OFFSET", 10))
        self.coin_bob = float(getattr(config, "SIDE_CHOICE_COIN_BOB", 12.0))
        self.coin_trail_count = int(getattr(config, "SIDE_CHOICE_COIN_TRAIL_COUNT", 2))
        self.coin_trail_alpha = int(getattr(config, "SIDE_CHOICE_COIN_TRAIL_ALPHA", 80))
        self.coin_edge_width = int(getattr(config, "SIDE_CHOICE_COIN_EDGE_WIDTH", 2))
        self.coin_face_scale = float(getattr(config, "SIDE_CHOICE_COIN_FACE_SCALE", 0.9))
        self.show_names_max = int(getattr(config, "SIDE_CHOICE_SHOW_NAMES_MAX", 5000))
        self.name_offset = int(getattr(config, "SIDE_CHOICE_NAME_OFFSET", 18))
        name_font_size = int(getattr(config, "SIDE_CHOICE_NAME_FONT_SIZE", 16))
        self.font_name = pygame.font.Font(None, name_font_size)
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._day_counter_bottom = None
        self._below_day_bottom = None

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)

        self._draw_game_area(players, game_state)
        self._draw_players(players, game_state)
        self._draw_title_and_subtitle()
        self._draw_day_counter(players, game_state)
        self._draw_game_ui(players, game_state)
        self._draw_club_panel(game_state)

        if game_state.get('show_leaderboards'):
            self._draw_end_game_display(
                game_state.get('current_game_leaderboard', []),
                game_state.get('all_time_leaderboard', []),
                game_state.get('winner')
            )

    def _draw_title_and_subtitle(self):
        center_x = self.width // 2
        header_y_shift = int(getattr(config, "SQUARE_ARENA_HEADER_Y_SHIFT", -4))
        title_y = self.game_top - 70 + header_y_shift
        subtitle_y = self.game_top - 40 + header_y_shift

        title_surface = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, title_y))
        self.screen.blit(title_surface, title_rect)

        subtitle_surface = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_surface.get_rect(center=(center_x, subtitle_y))
        self.screen.blit(subtitle_surface, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_surface = self.font_small.render(prompt_text, True, config.COLOR_TEXT)
            prompt_y = max(self.game_top - self.prompt_above_arena_margin, subtitle_rect.bottom + 6)
            prompt_rect = prompt_surface.get_rect(center=(center_x, prompt_y))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, players, game_state: dict):
        arena = game_state.get("arena")
        if arena is None:
            return

        open_side = game_state.get("open_side")
        phase = game_state.get("round_phase")

        left, top, right, bottom = arena.get_bounds()
        arena_rect = pygame.Rect(left, top, right - left, bottom - top)

        if arena.orientation == "horizontal":
            top_rect = pygame.Rect(left, top, right - left, arena.split_y - top)
            bottom_rect = pygame.Rect(left, arena.split_y, right - left, bottom - arena.split_y)
            self._draw_half(top_rect, self.left_color, open_side == "top" and phase == "result")
            self._draw_half(bottom_rect, self.right_color, open_side == "bottom" and phase == "result")
            pygame.draw.line(
                self.screen,
                self.split_color,
                (int(left), int(arena.split_y)),
                (int(right), int(arena.split_y)),
                3,
            )
        else:
            left_rect = pygame.Rect(left, top, arena.split_x - left, bottom - top)
            right_rect = pygame.Rect(arena.split_x, top, right - arena.split_x, bottom - top)
            self._draw_half(left_rect, self.left_color, open_side == "left" and phase == "result")
            self._draw_half(right_rect, self.right_color, open_side == "right" and phase == "result")
            pygame.draw.line(
                self.screen,
                self.split_color,
                (int(arena.split_x), int(top)),
                (int(arena.split_x), int(bottom)),
                3,
            )

        pygame.draw.rect(self.screen, self.border_color, arena_rect, 3)
        self._draw_side_labels(arena)

    def _draw_half(self, rect: pygame.Rect, base_color: tuple, is_open: bool):
        color = self.open_color if is_open else base_color
        pygame.draw.rect(self.screen, color, rect)

    def _draw_side_labels(self, arena):
        label_color = (20, 20, 20)
        if arena.orientation == "horizontal":
            top_center = (arena.center_x, (arena.top + arena.split_y) / 2)
            bottom_center = (arena.center_x, (arena.split_y + arena.bottom) / 2)
            top_label = self.font_small.render(self._side_label(arena, "top"), True, label_color)
            bottom_label = self.font_small.render(self._side_label(arena, "bottom"), True, label_color)
            self.screen.blit(top_label, top_label.get_rect(center=top_center))
            self.screen.blit(bottom_label, bottom_label.get_rect(center=bottom_center))
        else:
            left_center = ((arena.left + arena.split_x) / 2, arena.center_y)
            right_center = ((arena.split_x + arena.right) / 2, arena.center_y)
            left_label = self.font_small.render(self._side_label(arena, "left"), True, label_color)
            right_label = self.font_small.render(self._side_label(arena, "right"), True, label_color)
            self.screen.blit(left_label, left_label.get_rect(center=left_center))
            self.screen.blit(right_label, right_label.get_rect(center=right_center))

    def _side_label(self, arena, side: str) -> str:
        sides = list(arena.get_sides())
        if len(sides) >= 2:
            if side == sides[0]:
                return "HEADS"
            if side == sides[1]:
                return "TAILS"
        return str(side).upper()

    def _draw_players(self, players, game_state: dict = None):
        alive_count = None
        if game_state:
            alive_count = game_state.get("alive_count")
        if alive_count is None:
            alive_count = sum(1 for player in players if player.alive)
        show_names = self.show_names_max > 0 and alive_count <= self.show_names_max

        club_players = []
        for player in players:
            if not player.alive and not player.falling:
                continue
            size = player.radius * 2
            if getattr(player, "is_club_member", False):
                club_players.append(player)
                continue
            self._draw_player_avatar(player, size=size)
            if show_names and player.alive:
                self._draw_player_name(player, offset_y=self.name_offset)

        for player in club_players:
            size = player.radius * 2
            self._draw_club_glow(player, size=size)
            self._draw_player_avatar(player, size=size)
            if show_names and player.alive:
                self._draw_player_name(player, offset_y=self.name_offset)

    def _draw_player_name(self, player, offset_y: int = 20):
        name_surface = self.font_name.render(player.username, True, config.COLOR_TEXT)
        name_rect = name_surface.get_rect(center=(int(player.x), int(player.y) + offset_y))
        self.screen.blit(name_surface, name_rect)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"

        arena = game_state.get("arena")
        if arena:
            y_pos = int(arena.bottom + self.day_counter_offset)
        else:
            y_pos = int(self.game_bottom + self.day_counter_offset)

        day_surface = self.day_counter_font.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)
        self._day_counter_bottom = day_rect.bottom

    def _draw_game_ui(self, players, game_state: dict):
        round_phase = game_state.get("round_phase") or ""
        round_number = game_state.get("round_number", 0)
        time_left = game_state.get("phase_time_left", 0.0)
        alive_count = game_state.get("alive_count", 0)
        total_count = game_state.get("total_count", len(players))
        open_side = game_state.get("open_side")
        last_eliminated = game_state.get("last_eliminated", 0)

        arena = game_state.get("arena")
        day_offset = int(getattr(config, "SIDE_CHOICE_DAY_COUNTER_OFFSET", self.day_counter_offset))
        panel_offset = int(getattr(config, "SIDE_CHOICE_STATUS_PANEL_OFFSET", 8))
        if arena:
            day_y = int(arena.bottom + day_offset)
            panel_y = day_y + panel_offset
        else:
            panel_y = self.game_bottom + day_offset + panel_offset

        panel_width = int(getattr(config, "SIDE_CHOICE_STATUS_PANEL_WIDTH", 200))
        panel_rect = pygame.Rect(0, panel_y, panel_width, 92)
        panel_rect.centerx = self.width // 2
        panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, panel_rect.topleft)

        round_text = self.font_stats.render(f"Round {round_number}", True, (255, 255, 255))
        round_rect = round_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 18))
        self.screen.blit(round_text, round_rect)

        timer_text = self.font_stats.render(f"{time_left:.1f}s", True, (255, 255, 255))
        timer_rect = timer_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 42))
        self.screen.blit(timer_text, timer_rect)

        alive_text = self.font_stats.render(
            f"Alive {alive_count}/{total_count}",
            True,
            (255, 255, 255),
        )
        alive_rect = alive_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 66))
        self.screen.blit(alive_text, alive_rect)

        self._below_day_bottom = panel_rect.bottom

        if round_phase == "selection":
            status_text = "Pick heads or tails!"
        elif round_phase == "result":
            status_label = self._side_label(arena, open_side) if arena and open_side else ""
            status_text = f"{status_label} drops!" if status_label else "Flipping..."
        else:
            status_text = ""

        if status_text:
            status_surface = self.font_status.render(status_text, True, (255, 220, 120))
            status_offset = int(getattr(config, "SIDE_CHOICE_STATUS_TEXT_OFFSET", 18))
            status_rect = status_surface.get_rect(
                center=(self.width // 2, int(self.game_top - status_offset))
            )
            self.screen.blit(status_surface, status_rect)

        if round_phase == "result" and last_eliminated:
            elim_surface = self.font_small.render(
                f"Eliminated: {last_eliminated}",
                True,
                (255, 200, 200),
            )
            elim_rect = elim_surface.get_rect(center=(panel_rect.centerx, panel_rect.y + 86))
            self.screen.blit(elim_surface, elim_rect)

        self._draw_coin_flip(game_state)

    def _draw_club_panel(self, game_state: dict):
        anchor_y = self._below_day_bottom or self._day_counter_bottom
        if anchor_y is None:
            return
        draw_club_panel(
            self.screen,
            game_state.get("club_spotlight"),
            anchor_y=anchor_y,
            font=self.font_club_panel,
            get_avatar_surface=self._get_avatar_surface,
            glow_cache=self._club_glow_cache,
        )

    def _draw_coin_flip(self, game_state: dict):
        if game_state.get("round_phase") != "result":
            return

        duration = float(game_state.get("coin_flip_duration", 0.0))
        if duration <= 0:
            return

        elapsed = float(game_state.get("coin_flip_elapsed", 0.0))
        progress = max(0.0, min(1.0, elapsed / duration))
        flips = max(1, int(self.coin_flips))
        ease = 0.5 - 0.5 * math.cos(math.pi * progress)
        angle = ease * flips * math.pi

        spin_cos = math.cos(angle)
        spin_sin = math.sin(angle)
        scale_x = max(0.08, abs(spin_cos))
        scale_y = 0.88 + 0.12 * abs(spin_sin)

        width = max(2, int(self.coin_radius * 2 * scale_x))
        height = max(2, int(self.coin_radius * 2 * scale_y))

        center_x = self.width // 2
        bob = math.sin(progress * math.pi) * self.coin_bob
        center_y = int(self.game_top + self.coin_offset - bob)

        arena = game_state.get("arena")
        resolved = bool(game_state.get("coin_flip_resolved"))
        result_side = game_state.get("coin_flip_side")
        if resolved and arena and result_side:
            label = self._side_label(arena, result_side)
        else:
            label = "HEADS" if spin_cos >= 0 else "TAILS"

        face_char = "H" if label.startswith("H") else "T"
        show_face = resolved or scale_x > 0.55
        highlight = 0.25 + (0.75 * scale_x)

        if not resolved and self.coin_trail_count > 0:
            step = 0.04
            for i in range(self.coin_trail_count, 0, -1):
                trail_progress = max(0.0, progress - i * step)
                trail_ease = 0.5 - 0.5 * math.cos(math.pi * trail_progress)
                trail_angle = trail_ease * flips * math.pi
                trail_scale_x = max(0.08, abs(math.cos(trail_angle)))
                trail_scale_y = 0.88 + 0.12 * abs(math.sin(trail_angle))
                trail_width = max(2, int(self.coin_radius * 2 * trail_scale_x))
                trail_height = max(2, int(self.coin_radius * 2 * trail_scale_y))
                trail_bob = math.sin(trail_progress * math.pi) * self.coin_bob * 0.6
                trail_alpha = int(self.coin_trail_alpha * (1.0 - (i / (self.coin_trail_count + 1))))
                trail_label = "HEADS" if math.cos(trail_angle) >= 0 else "TAILS"
                trail_face = "H" if trail_label.startswith("H") else "T"
                self._draw_coin_layer(
                    center_x,
                    int(self.game_top + self.coin_offset - trail_bob),
                    trail_width,
                    trail_height,
                    trail_face,
                    trail_scale_x > 0.6,
                    trail_alpha,
                    trail_scale_x,
                    0.25,
                )

        shadow_width = max(6, int(self.coin_radius * 2 * 0.85))
        shadow_height = max(4, int(self.coin_radius * 0.55 * (0.5 + 0.5 * scale_x)))
        shadow_surface = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        shadow_alpha = int(self.coin_shadow_alpha * (0.6 + 0.4 * (1 - scale_x)))
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, shadow_alpha), shadow_surface.get_rect())
        shadow_x = center_x - shadow_width // 2
        shadow_y = center_y + self.coin_shadow_offset
        self.screen.blit(shadow_surface, (shadow_x, shadow_y))

        self._draw_coin_layer(
            center_x,
            center_y,
            width,
            height,
            face_char,
            show_face,
            255,
            scale_x,
            highlight,
        )

    def _draw_coin_layer(
        self,
        center_x: int,
        center_y: int,
        width: int,
        height: int,
        face_char: str,
        show_face: bool,
        alpha: int,
        scale_x: float,
        highlight_strength: float,
    ):
        if width <= 1 or height <= 1 or alpha <= 0:
            return

        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        rect = surface.get_rect()

        base_color = (*self.coin_color, alpha)
        pygame.draw.ellipse(surface, base_color, rect)

        inset = max(1, int(min(width, height) * 0.12))
        inner_rect = rect.inflate(-inset * 2, -inset * 2)
        if inner_rect.width > 0 and inner_rect.height > 0:
            inner_color = (*self.coin_inner_color, alpha)
            pygame.draw.ellipse(surface, inner_color, inner_rect)

        rim_width = max(1, int(self.coin_edge_width + (1 - scale_x) * 2))
        rim_color = (*self.coin_rim_color, alpha)
        pygame.draw.ellipse(surface, rim_color, rect, rim_width)

        if scale_x < 0.35:
            band_height = max(2, int(height * 0.18))
            band_rect = pygame.Rect(0, (height - band_height) // 2, width, band_height)
            band_color = (*self._shade_color(self.coin_edge_color, 0.85), alpha)
            pygame.draw.rect(surface, band_color, band_rect)

        if highlight_strength > 0.05:
            glint_alpha = int(alpha * min(1.0, highlight_strength))
            glint_w = max(2, int(width * 0.45))
            glint_h = max(2, int(height * 0.45))
            glint_rect = pygame.Rect(0, 0, glint_w, glint_h)
            glint_rect.center = (int(width * 0.35), int(height * 0.35))
            glint_color = (*self.coin_shine_color, glint_alpha)
            pygame.draw.ellipse(surface, glint_color, glint_rect)

        if show_face and face_char:
            face_surface = self.font_coin.render(face_char, True, self.coin_text_color)
            if self.coin_face_scale != 1.0:
                target_w = max(1, int(face_surface.get_width() * self.coin_face_scale))
                target_h = max(1, int(face_surface.get_height() * self.coin_face_scale))
                face_surface = pygame.transform.smoothscale(face_surface, (target_w, target_h))
            if alpha < 255:
                face_surface = face_surface.copy()
                face_surface.set_alpha(alpha)
            face_rect = face_surface.get_rect(center=rect.center)
            surface.blit(face_surface, face_rect)

        self.screen.blit(surface, (center_x - width // 2, center_y - height // 2))

    def _shade_color(self, color: tuple, factor: float) -> tuple:
        return tuple(max(0, min(255, int(c * factor))) for c in color)
