"""
Math Drop renderer.
"""

import pygame

import config
from shared import RendererTemplate
from shared.club_panel import draw_club_panel


class MathDropRenderer(RendererTemplate):
    GAME_TITLE = "MATH DROP"
    PLAYER_LABEL = "players"
    GAME_WIDTH = int(
        getattr(
            config,
            "MATH_DROP_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )[2]
    )
    GAME_HEIGHT = int(
        getattr(
            config,
            "MATH_DROP_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )[3]
    )

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        arena_x, arena_y, arena_w, arena_h = getattr(
            config,
            "MATH_DROP_ARENA_RECT",
            getattr(config, "MAZE_RUSH_ARENA_RECT", config.FIGHTER_ARENA_RECT),
        )
        self.game_left = arena_x
        self.game_top = arena_y
        self.game_right = arena_x + arena_w
        self.game_bottom = arena_y + arena_h

        self.upper_color = getattr(config, "MATH_DROP_UPPER_BG", (210, 212, 220))
        self.lower_color = getattr(config, "MATH_DROP_LOWER_BG", (190, 190, 200))
        self.square_color = getattr(config, "MATH_DROP_SQUARE_COLOR", (240, 240, 245))
        self.square_open_color = getattr(config, "MATH_DROP_SQUARE_OPEN_COLOR", (55, 55, 65))
        self.square_border_color = getattr(config, "MATH_DROP_SQUARE_BORDER_COLOR", (0, 0, 0))
        self.square_text_color = getattr(config, "MATH_DROP_SQUARE_TEXT_COLOR", (20, 20, 20))
        self.square_open_text_color = getattr(config, "MATH_DROP_SQUARE_OPEN_TEXT_COLOR", (230, 230, 230))
        self.answer_outline_width = int(getattr(config, "MATH_DROP_ANSWER_OUTLINE_WIDTH", 2))
        self.answer_outline_color = getattr(config, "MATH_DROP_ANSWER_OUTLINE_COLOR", None)
        self.equation_outline_width = int(getattr(config, "MATH_DROP_EQUATION_OUTLINE_WIDTH", 3))
        self.equation_outline_color = getattr(config, "MATH_DROP_EQUATION_OUTLINE_COLOR", None)
        self.correct_color = getattr(config, "MATH_DROP_CORRECT_COLOR", (170, 220, 170))
        self.split_color = getattr(config, "MATH_DROP_SPLIT_LINE_COLOR", (40, 40, 40))
        self.zone_line_color = getattr(config, "MATH_DROP_ZONE_LINE_COLOR", (150, 150, 160))
        self.border_color = getattr(config, "MATH_DROP_BORDER_COLOR", (0, 0, 0))

        equation_size = int(getattr(config, "MATH_DROP_EQUATION_TEXT_SIZE", 40))
        answer_size = int(getattr(config, "MATH_DROP_ANSWER_TEXT_SIZE", 34))
        status_size = int(getattr(config, "MATH_DROP_STATUS_TEXT_SIZE", 34))
        self.font_equation = pygame.font.Font(None, equation_size)
        self.font_answer = pygame.font.Font(None, answer_size)
        self.font_status = pygame.font.Font(None, status_size)
        teleport_size = int(getattr(config, "MATH_DROP_TELEPORT_TEXT_SIZE", 30))
        self.font_teleport = pygame.font.Font(None, teleport_size)
        self.teleport_text_color = getattr(config, "MATH_DROP_TELEPORT_TEXT_COLOR", (30, 30, 30))

        self.show_names_max = int(getattr(config, "MATH_DROP_SHOW_NAMES_MAX", 1000))
        self.name_offset = int(getattr(config, "MATH_DROP_NAME_OFFSET", 18))
        name_font_size = int(getattr(config, "MATH_DROP_NAME_FONT_SIZE", 16))
        self.font_name = pygame.font.Font(None, name_font_size)

        self.day_counter_offset = int(
            getattr(
                config,
                "MATH_DROP_DAY_COUNTER_OFFSET",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_OFFSET", 14),
            )
        )
        day_counter_size = int(
            getattr(
                config,
                "MATH_DROP_DAY_COUNTER_FONT_SIZE",
                getattr(config, "MAZE_RUSH_DAY_COUNTER_FONT_SIZE", 32),
            )
        )
        self.day_counter_font = pygame.font.Font(None, day_counter_size)
        self.header_y_shift = int(getattr(config, "SQUARE_ARENA_HEADER_Y_SHIFT", -4))
        self.prompt_above_arena_margin = int(
            getattr(
                config,
                "MATH_DROP_PROMPT_ABOVE_ARENA_MARGIN",
                getattr(config, "MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN", 8),
            )
        )
        club_text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        self.font_club_panel = pygame.font.Font(None, club_text_size)
        self._day_counter_bottom = None
        self._below_day_bottom = None

    def render_frame(self, players, game_state: dict):
        self.screen.fill(config.COLOR_BACKGROUND)

        self._draw_game_area(players, game_state)
        self._draw_players(players, game_state)
        self._draw_answer_overlay(game_state)
        self._draw_teleport_flash(game_state)
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
        arena_top = self.game_top
        subtitle_rect = None

        title_text = self.font_title.render(self.GAME_TITLE, True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 70 + self.header_y_shift))
        self.screen.blit(title_text, title_rect)

        subtitle_text = self.font_subtitle.render(self.GAME_SUBTITLE, True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 40 + self.header_y_shift))
        self.screen.blit(subtitle_text, subtitle_rect)

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        if prompt_text:
            prompt_surface = self.font_small.render(prompt_text, True, config.COLOR_TEXT)
            prompt_y = int(arena_top - self.prompt_above_arena_margin)
            if subtitle_rect is not None:
                prompt_y = max(prompt_y, subtitle_rect.bottom + 6)
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, prompt_y))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_game_area(self, players, game_state: dict):
        arena = game_state.get("arena")
        if arena is None:
            return

        left = arena.left
        right = arena.right
        top = arena.top
        bottom = arena.bottom
        mid_y = arena.mid_y

        upper_rect = pygame.Rect(int(left), int(top), int(right - left), int(mid_y - top))
        lower_rect = pygame.Rect(int(left), int(mid_y), int(right - left), int(bottom - mid_y))

        pygame.draw.rect(self.screen, self.upper_color, upper_rect)
        pygame.draw.rect(self.screen, self.lower_color, lower_rect)

        pygame.draw.line(
            self.screen,
            self.split_color,
            (int(left), int(mid_y)),
            (int(right), int(mid_y)),
            3,
        )

        choice_rects = arena.get_choice_rects()
        open_choices = set(game_state.get("open_choices") or [])
        round_phase = game_state.get("round_phase")
        reveal_resolved = bool(game_state.get("reveal_resolved"))
        correct_choice = game_state.get("correct_choice")

        for idx, rect in enumerate(choice_rects):
            rect_left, rect_top, rect_right, rect_bottom = rect
            rect_w = rect_right - rect_left
            rect_h = rect_bottom - rect_top
            pygame_rect = pygame.Rect(int(rect_left), int(rect_top), int(rect_w), int(rect_h))

            is_open = round_phase == "result" and reveal_resolved and idx in open_choices
            if round_phase == "result" and reveal_resolved and idx == correct_choice:
                fill_color = self.correct_color
            else:
                fill_color = self.square_open_color if is_open else self.square_color

            pygame.draw.rect(self.screen, fill_color, pygame_rect)
            pygame.draw.rect(self.screen, self.square_border_color, pygame_rect, 3)

        arena_rect = pygame.Rect(int(left), int(top), int(right - left), int(bottom - top))
        pygame.draw.rect(self.screen, self.border_color, arena_rect, 3)

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

    def _draw_teleport_flash(self, game_state: dict):
        flash_alpha = float(game_state.get("teleport_flash_alpha") or 0.0)
        if flash_alpha <= 0:
            return

        arena = game_state.get("arena")
        if arena is None:
            return

        base_alpha = int(getattr(config, "MATH_DROP_TELEPORT_FLASH_ALPHA", 140))
        alpha = max(0, min(255, int(base_alpha * flash_alpha)))
        overlay = pygame.Surface(
            (int(arena.right - arena.left), int(arena.bottom - arena.top)),
            pygame.SRCALPHA,
        )
        overlay.fill((255, 255, 255, alpha))
        self.screen.blit(overlay, (int(arena.left), int(arena.top)))

        teleport_text = game_state.get("teleport_text") or ""
        if teleport_text:
            text_surface = self.font_teleport.render(teleport_text, True, self.teleport_text_color)
            if alpha < 255:
                text_surface = text_surface.copy()
                text_surface.set_alpha(alpha)
            text_rect = text_surface.get_rect(center=(self.width // 2, int(arena.center_y)))
            self.screen.blit(text_surface, text_rect)

    def _draw_answer_overlay(self, game_state: dict):
        arena = game_state.get("arena")
        if arena is None:
            return

        answers = game_state.get("answer_options") or []
        open_choices = set(game_state.get("open_choices") or [])
        round_phase = game_state.get("round_phase")
        reveal_resolved = bool(game_state.get("reveal_resolved"))
        correct_choice = game_state.get("correct_choice")

        for idx, rect in enumerate(arena.get_choice_rects()):
            if idx >= len(answers):
                continue
            rect_left, rect_top, rect_right, rect_bottom = rect
            rect_w = rect_right - rect_left
            rect_h = rect_bottom - rect_top
            center = (int(rect_left + rect_w / 2), int(rect_top + rect_h / 2))

            is_open = round_phase == "result" and reveal_resolved and idx in open_choices
            if round_phase == "result" and reveal_resolved and idx == correct_choice:
                text_color = self.square_text_color
            else:
                text_color = self.square_open_text_color if is_open else self.square_text_color

            max_w = rect_w * 0.85
            max_h = rect_h * 0.75
            answer_surface = self._render_scaled_text(
                self.font_answer,
                str(answers[idx]),
                text_color,
                max_w,
                max_h,
                outline_color=self.answer_outline_color,
                outline_width=self.answer_outline_width,
            )
            answer_rect = answer_surface.get_rect(center=center)
            self.screen.blit(answer_surface, answer_rect)

        equation_text = game_state.get("equation_text")
        if equation_text:
            lower_height = arena.lower_bottom - arena.lower_top
            eq_y = int((arena.lower_top + arena.lower_bottom) / 2)
            max_w = (arena.right - arena.left) * 0.92
            max_h = lower_height * 0.45
            eq_surface = self._render_scaled_text(
                self.font_equation,
                equation_text,
                config.COLOR_TEXT,
                max_w,
                max_h,
                outline_color=self.equation_outline_color,
                outline_width=self.equation_outline_width,
            )
            eq_rect = eq_surface.get_rect(center=(self.width // 2, eq_y))
            self.screen.blit(eq_surface, eq_rect)

    def _draw_day_counter(self, players, game_state: dict):
        total_count = len(players)
        day_text = f"Day {config.DAY_NUMBER}: {total_count} {self.PLAYER_LABEL}"
        y_pos = int(self.game_bottom + self.day_counter_offset)
        day_surface = self.day_counter_font.render(day_text, True, config.COLOR_TEXT)
        day_rect = day_surface.get_rect(center=(self.width // 2, y_pos))
        self.screen.blit(day_surface, day_rect)
        self._day_counter_bottom = day_rect.bottom

    def _draw_game_ui(self, players, game_state: dict):
        arena = game_state.get("arena")
        if arena is None:
            return

        round_phase = game_state.get("round_phase") or ""
        round_number = game_state.get("round_number", 0)
        time_left = game_state.get("phase_time_left", 0.0)
        alive_count = game_state.get("alive_count", 0)
        total_count = game_state.get("total_count", len(players))
        last_eliminated = game_state.get("last_eliminated", 0)

        day_offset = int(
            getattr(
                config,
                "MATH_DROP_DAY_COUNTER_OFFSET",
                self.day_counter_offset,
            )
        )
        panel_offset = int(getattr(config, "MATH_DROP_STATUS_PANEL_OFFSET", 24))
        day_y = int(arena.bottom + day_offset)
        panel_y = day_y + panel_offset

        panel_width = int(getattr(config, "MATH_DROP_STATUS_PANEL_WIDTH", 200))
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

        if round_phase == "result" and last_eliminated:
            elim_surface = self.font_small.render(
                f"Eliminated: {last_eliminated}",
                True,
                (255, 200, 200),
            )
            elim_rect = elim_surface.get_rect(center=(panel_rect.centerx, panel_rect.y + 86))
            self.screen.blit(elim_surface, elim_rect)

        self._below_day_bottom = panel_rect.bottom

    def _render_scaled_text(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple,
        max_width: float,
        max_height: float,
        outline_color: tuple = None,
        outline_width: int = 0,
    ) -> pygame.Surface:
        surface = self._render_outlined_text(
            font=font,
            text=text,
            color=color,
            outline_color=outline_color,
            outline_width=outline_width,
        )
        width = surface.get_width()
        height = surface.get_height()
        if width <= 0 or height <= 0:
            return surface
        scale = min(max_width / width, max_height / height, 1.0)
        if scale >= 1.0:
            return surface

        target_w = max(1, int(width * scale))
        target_h = max(1, int(height * scale))
        return pygame.transform.smoothscale(surface, (target_w, target_h))

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

    @staticmethod
    def _auto_outline_color(color: tuple) -> tuple:
        r, g, b = color
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return (0, 0, 0) if luminance >= 140 else (255, 255, 255)

    def _render_outlined_text(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple,
        outline_color: tuple = None,
        outline_width: int = 0,
    ) -> pygame.Surface:
        fill_surface = font.render(text, True, color)
        outline_px = max(0, int(outline_width))
        if outline_px == 0:
            return fill_surface

        resolved_outline = outline_color or self._auto_outline_color(color)
        outline_surface = font.render(text, True, resolved_outline)

        width, height = fill_surface.get_size()
        composed = pygame.Surface((width + outline_px * 2, height + outline_px * 2), pygame.SRCALPHA)

        for dx in range(-outline_px, outline_px + 1):
            for dy in range(-outline_px, outline_px + 1):
                if dx == 0 and dy == 0:
                    continue
                if dx * dx + dy * dy > outline_px * outline_px:
                    continue
                composed.blit(outline_surface, (dx + outline_px, dy + outline_px))

        composed.blit(fill_surface, (outline_px, outline_px))
        return composed
