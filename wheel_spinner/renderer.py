"""
Wheel Spinner renderer.
"""

import math
from typing import Optional, Tuple

import pygame

import config
from shared import RendererTemplate


class WheelSpinnerRenderer(RendererTemplate):
    GAME_TITLE = "WHEEL SPINNER"
    PLAYER_LABEL = "players"

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)

        self.wheel_radius = int(getattr(config, "WHEEL_SPINNER_RADIUS", 220))
        self.wheel_center_offset = int(getattr(config, "WHEEL_SPINNER_CENTER_Y_OFFSET", 0))
        self.wheel_border_color = getattr(config, "WHEEL_SPINNER_BORDER_COLOR", (0, 0, 0))
        self.wheel_divider_color = getattr(config, "WHEEL_SPINNER_DIVIDER_COLOR", (30, 30, 30))
        self.pointer_color = getattr(config, "WHEEL_SPINNER_POINTER_COLOR", (20, 20, 20))
        self.pointer_outline = getattr(config, "WHEEL_SPINNER_POINTER_OUTLINE", (240, 240, 240))
        self.pointer_angle = -math.pi / 2

        option_size = int(getattr(config, "WHEEL_SPINNER_OPTION_TEXT_SIZE", 24))
        indicator_size = int(getattr(config, "WHEEL_SPINNER_INDICATOR_TEXT_SIZE", 32))
        status_size = int(getattr(config, "WHEEL_SPINNER_STATUS_TEXT_SIZE", 28))
        selected_size = int(getattr(config, "WHEEL_SPINNER_SELECTED_TEXT_SIZE", 28))

        self.font_indicator = pygame.font.Font(None, indicator_size)
        self.font_status = pygame.font.Font(None, status_size)
        self.font_selected = pygame.font.Font(None, selected_size)
        self.option_base_size = option_size
        self._option_fonts = {}

        self.arrow_gap = int(getattr(config, "WHEEL_SPINNER_POINTER_GAP", 8))
        self.arrow_width = int(getattr(config, "WHEEL_SPINNER_POINTER_WIDTH", 32))
        self.arrow_height = int(getattr(config, "WHEEL_SPINNER_POINTER_HEIGHT", 22))
        self.indicator_offset = int(getattr(config, "WHEEL_SPINNER_INDICATOR_OFFSET", 10))
        self.status_panel_offset = int(getattr(config, "WHEEL_SPINNER_STATUS_PANEL_OFFSET", 16))
        self.status_panel_width = int(getattr(config, "WHEEL_SPINNER_STATUS_PANEL_WIDTH", 240))
        self.selected_offset = int(getattr(config, "WHEEL_SPINNER_SELECTED_OFFSET", 36))
        self.selected_max_shown = int(getattr(config, "WHEEL_SPINNER_SELECTED_MAX_SHOWN", 10))
        self.selected_color = getattr(config, "WHEEL_SPINNER_SELECTED_COLOR", (255, 230, 160))
        self.selected_panel_alpha = int(getattr(config, "WHEEL_SPINNER_SELECTED_PANEL_ALPHA", 180))
        self.selected_panel_bg = getattr(config, "WHEEL_SPINNER_SELECTED_PANEL_BG", (28, 28, 36))
        self.selected_panel_border = getattr(config, "WHEEL_SPINNER_SELECTED_PANEL_BORDER", (80, 80, 95))
        self.selected_panel_radius = int(getattr(config, "WHEEL_SPINNER_SELECTED_PANEL_RADIUS", 12))
        self.selected_panel_padding = int(getattr(config, "WHEEL_SPINNER_SELECTED_PANEL_PADDING", 12))
        self.selected_panel_gap = int(getattr(config, "WHEEL_SPINNER_SELECTED_PANEL_GAP", 8))
        badge_size = int(getattr(config, "WHEEL_SPINNER_BADGE_TEXT_SIZE", selected_size))
        self.font_badge = pygame.font.Font(None, badge_size)
        self.badge_bg = getattr(config, "WHEEL_SPINNER_BADGE_BG", (235, 235, 245))
        self.badge_border = getattr(config, "WHEEL_SPINNER_BADGE_BORDER", (120, 120, 140))
        self.badge_text = getattr(config, "WHEEL_SPINNER_BADGE_TEXT", (30, 30, 40))
        self.badge_radius = int(getattr(config, "WHEEL_SPINNER_BADGE_RADIUS", 8))
        self.badge_padding = int(getattr(config, "WHEEL_SPINNER_BADGE_PADDING", 6))

        self.pointer_panel_bg = getattr(config, "WHEEL_SPINNER_POINTER_PANEL_BG", (28, 28, 36))
        self.pointer_panel_border = getattr(config, "WHEEL_SPINNER_POINTER_PANEL_BORDER", (80, 80, 95))
        self.pointer_panel_alpha = int(getattr(config, "WHEEL_SPINNER_POINTER_PANEL_ALPHA", 180))
        self.pointer_panel_radius = int(getattr(config, "WHEEL_SPINNER_POINTER_PANEL_RADIUS", 10))
        self.pointer_panel_padding = int(getattr(config, "WHEEL_SPINNER_POINTER_PANEL_PADDING", 10))

        self.segment_colors = list(
            getattr(
                config,
                "WHEEL_SPINNER_SEGMENT_COLORS",
                [
                    (245, 174, 99),
                    (129, 201, 149),
                    (132, 181, 232),
                    (233, 146, 165),
                    (238, 210, 119),
                    (174, 156, 214),
                    (118, 210, 201),
                    (247, 189, 132),
                    (150, 212, 133),
                    (128, 164, 222),
                    (232, 160, 130),
                    (210, 222, 156),
                ],
            )
        )
        self.light_angle = math.radians(float(getattr(config, "WHEEL_SPINNER_LIGHT_ANGLE_DEG", -55.0)))
        self.rim_thickness = int(
            getattr(config, "WHEEL_SPINNER_RIM_THICKNESS", max(10, int(self.wheel_radius * 0.08)))
        )
        self.bevel_depth = int(getattr(config, "WHEEL_SPINNER_BEVEL_DEPTH", max(8, int(self.wheel_radius * 0.06))))
        self.rim_base_color = getattr(config, "WHEEL_SPINNER_RIM_COLOR", (54, 54, 64))
        self.rim_highlight_color = getattr(config, "WHEEL_SPINNER_RIM_HIGHLIGHT", (255, 255, 255))
        self.rim_shadow_color = getattr(config, "WHEEL_SPINNER_RIM_SHADOW", (25, 25, 30))
        self.face_border_color = getattr(config, "WHEEL_SPINNER_FACE_BORDER", (20, 20, 20))
        self.face_inner_ring_color = getattr(config, "WHEEL_SPINNER_FACE_INNER_RING", (250, 250, 255))
        self.face_inner_ring_shadow = getattr(config, "WHEEL_SPINNER_FACE_INNER_RING_SHADOW", (120, 120, 135))
        self.face_inner_ring_width = int(getattr(config, "WHEEL_SPINNER_FACE_INNER_RING_WIDTH", 4))
        self.face_glow_color = getattr(config, "WHEEL_SPINNER_FACE_GLOW", (255, 255, 255))
        self.hub_radius = int(
            getattr(config, "WHEEL_SPINNER_HUB_RADIUS", max(18, int(self.wheel_radius * 0.12)))
        )
        self.hub_color = getattr(config, "WHEEL_SPINNER_HUB_COLOR", (235, 235, 240))
        self.hub_ring_color = getattr(config, "WHEEL_SPINNER_HUB_RING_COLOR", (70, 70, 80))
        self.hub_glint_color = getattr(config, "WHEEL_SPINNER_HUB_GLINT_COLOR", (255, 255, 255))
        self.shadow_alpha = int(getattr(config, "WHEEL_SPINNER_SHADOW_ALPHA", 90))
        self.shadow_offset = int(getattr(config, "WHEEL_SPINNER_SHADOW_OFFSET", 18))
        self.shadow_scale = float(getattr(config, "WHEEL_SPINNER_SHADOW_SCALE", 0.65))
        self.label_color = getattr(config, "WHEEL_SPINNER_LABEL_COLOR", (20, 20, 20))
        self.label_shadow_alpha = int(getattr(config, "WHEEL_SPINNER_LABEL_SHADOW_ALPHA", 120))
        self.label_shadow_offset = int(getattr(config, "WHEEL_SPINNER_LABEL_SHADOW_OFFSET", 2))
        self._overlay_radius = None
        self._overlay_surfaces = None

    def _draw_game_area(self, players, game_state: dict):
        arena = game_state.get("arena")

        options = game_state.get("options") or []
        wheel_angle = float(game_state.get("wheel_angle", 0.0))
        center = self._get_wheel_center(arena)

        if options:
            highlight_index = self._get_pointer_index(options, wheel_angle)
            self._draw_wheel(center, options, wheel_angle, highlight_index)

        self._draw_pointer(center)

    def _draw_players(self, players):
        return

    def _draw_game_ui(self, players, game_state: dict):
        round_phase = game_state.get("round_phase") or ""
        round_number = game_state.get("round_number", 0)
        char_index = game_state.get("char_index", 0)
        alive_count = game_state.get("alive_count", 0)
        total_count = game_state.get("total_count", len(players))
        last_eliminated = game_state.get("last_eliminated", 0)
        options = game_state.get("options") or []
        wheel_angle = float(game_state.get("wheel_angle", 0.0))
        winning_option = game_state.get("winning_option")
        selected_sequence = game_state.get("selected_sequence") or []
        username_length_hint = int(game_state.get("username_length_hint", 0) or 0)

        arena = game_state.get("arena")
        center = self._get_wheel_center(arena)
        radius = self._get_wheel_radius()

        self._draw_pointer_indicator(center, radius, options, wheel_angle, round_phase)
        self._draw_selected_sequence(center, radius, selected_sequence, username_length_hint)

        panel_y = int(center[1] + radius + self.status_panel_offset)
        panel_rect = pygame.Rect(0, panel_y, self.status_panel_width, 92)
        panel_rect.centerx = self.width // 2
        panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 110))
        self.screen.blit(panel, panel_rect.topleft)

        round_text = self.font_stats.render(f"Round {round_number}", True, (255, 255, 255))
        round_rect = round_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 18))
        self.screen.blit(round_text, round_rect)

        letter_text = self.font_stats.render(f"Letter {char_index + 1}", True, (255, 255, 255))
        letter_rect = letter_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 42))
        self.screen.blit(letter_text, letter_rect)

        alive_text = self.font_stats.render(
            f"Alive {alive_count}/{total_count}",
            True,
            (255, 255, 255),
        )
        alive_rect = alive_text.get_rect(center=(panel_rect.centerx, panel_rect.y + 66))
        self.screen.blit(alive_text, alive_rect)

        status_text = ""
        if round_phase in ("windup", "spin"):
            status_text = "Spinning..."
        elif round_phase == "resolve" and winning_option is not None:
            status_text = f"Selected: {self._format_option(winning_option)}"

        if status_text:
            status_surface = self.font_status.render(status_text, True, (255, 230, 160))
            status_rect = status_surface.get_rect(center=(self.width // 2, int(self.game_top - 22)))
            self.screen.blit(status_surface, status_rect)

        if last_eliminated and round_phase == "resolve":
            elim_surface = self.font_small.render(
                f"Eliminated: {last_eliminated}",
                True,
                (255, 200, 200),
            )
            elim_rect = elim_surface.get_rect(center=(panel_rect.centerx, panel_rect.y + 86))
            self.screen.blit(elim_surface, elim_rect)

    def _get_wheel_center(self, arena) -> Tuple[int, int]:
        if arena:
            center_x, center_y = arena.get_center()
        else:
            center_x = self.width // 2
            center_y = (self.game_top + self.game_bottom) // 2
        return (int(center_x), int(center_y + self.wheel_center_offset))

    def _get_wheel_radius(self) -> int:
        return self.wheel_radius

    def _get_face_overlays(self, radius: int):
        if self._overlay_surfaces is not None and self._overlay_radius == radius:
            return self._overlay_surfaces

        diameter = radius * 2
        highlight = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        shadow = pygame.Surface((diameter, diameter), pygame.SRCALPHA)

        highlight_center = (int(radius * 0.6), int(radius * 0.45))
        for i in range(9):
            alpha = max(0, 70 - i * 7)
            ring_radius = int(radius * (0.92 - i * 0.07))
            if ring_radius <= 0:
                continue
            pygame.draw.circle(highlight, (255, 255, 255, alpha), highlight_center, ring_radius)

        shadow_center = (int(radius * 1.15), int(radius * 1.12))
        for i in range(10):
            alpha = max(0, 60 - i * 6)
            ring_radius = int(radius * (0.9 - i * 0.06))
            if ring_radius <= 0:
                continue
            pygame.draw.circle(shadow, (0, 0, 0, alpha), shadow_center, ring_radius)

        self._overlay_radius = radius
        self._overlay_surfaces = (highlight, shadow)
        return self._overlay_surfaces

    def _draw_wheel_shadow(self, center: Tuple[int, int], radius: int):
        shadow_w = int(radius * 2.0)
        shadow_h = max(10, int(radius * self.shadow_scale))
        shadow_surface = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)

        for i in range(6):
            alpha = int(self.shadow_alpha * (1.0 - (i / 6)))
            inset_x = i * 2
            inset_y = i
            rect = pygame.Rect(
                inset_x,
                inset_y,
                max(1, shadow_w - inset_x * 2),
                max(1, shadow_h - inset_y * 2),
            )
            pygame.draw.ellipse(shadow_surface, (0, 0, 0, alpha), rect)

        shadow_x = center[0] - shadow_w // 2
        shadow_y = center[1] + self.shadow_offset
        self.screen.blit(shadow_surface, (shadow_x, shadow_y))

    def _draw_wheel_backdrop(self, center: Tuple[int, int], radius: int):
        glow_radius = int(radius * 1.12)
        diameter = glow_radius * 2
        glow_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        for i in range(10):
            alpha = max(0, 50 - i * 4)
            ring_radius = int(glow_radius * (1 - i * 0.06))
            pygame.draw.circle(
                glow_surface,
                (*self.face_glow_color, alpha),
                (glow_radius, glow_radius),
                ring_radius,
            )
        self.screen.blit(glow_surface, (center[0] - glow_radius, center[1] - glow_radius))

    def _draw_wheel_rim(self, center: Tuple[int, int], radius: int):
        pygame.draw.circle(self.screen, self.rim_base_color, center, radius)
        if self.rim_thickness > 0:
            for i in range(self.rim_thickness):
                t = i / max(1, self.rim_thickness)
                shade = 0.9 - 0.25 * t
                color = self._shade_color(self.rim_base_color, shade)
                pygame.draw.circle(self.screen, color, center, radius - i, 1)

    def _draw_rim_highlights(self, center: Tuple[int, int], radius: int):
        diameter = radius * 2
        rim_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        rim_rect = rim_surface.get_rect()
        rim_width = max(3, int(self.rim_thickness * 0.7))

        highlight = (*self.rim_highlight_color, 150)
        shadow = (*self.rim_shadow_color, 170)

        pygame.draw.arc(
            rim_surface,
            highlight,
            rim_rect,
            math.radians(210),
            math.radians(330),
            rim_width,
        )
        pygame.draw.arc(
            rim_surface,
            shadow,
            rim_rect,
            math.radians(30),
            math.radians(150),
            rim_width,
        )

        self.screen.blit(rim_surface, (center[0] - radius, center[1] - radius))

    def _draw_face_overlays(self, center: Tuple[int, int], radius: int):
        highlight, shadow = self._get_face_overlays(radius)
        pos = (center[0] - radius, center[1] - radius)
        self.screen.blit(shadow, pos)
        self.screen.blit(highlight, pos)

    def _draw_face_inner_ring(self, center: Tuple[int, int], face_radius: int):
        ring_radius = max(0, face_radius - max(6, int(face_radius * 0.24)))
        if ring_radius <= 0 or self.face_inner_ring_width <= 0:
            return
        pygame.draw.circle(
            self.screen,
            self.face_inner_ring_shadow,
            center,
            ring_radius + self.face_inner_ring_width,
            self.face_inner_ring_width,
        )
        pygame.draw.circle(
            self.screen,
            self.face_inner_ring_color,
            center,
            ring_radius,
            self.face_inner_ring_width,
        )

    def _draw_hub(self, center: Tuple[int, int], face_radius: int):
        hub_radius = min(self.hub_radius, int(face_radius * 0.22))
        if hub_radius <= 0:
            return

        pygame.draw.circle(self.screen, self.hub_ring_color, center, hub_radius + 6)
        pygame.draw.circle(self.screen, self.hub_color, center, hub_radius)

        glint_surface = pygame.Surface((hub_radius * 2, hub_radius * 2), pygame.SRCALPHA)
        glint_center = (int(hub_radius * 0.65), int(hub_radius * 0.6))
        for i in range(4):
            alpha = max(0, 140 - i * 30)
            radius_step = int(hub_radius * (0.45 - i * 0.08))
            if radius_step <= 0:
                continue
            pygame.draw.circle(glint_surface, (*self.hub_glint_color, alpha), glint_center, radius_step)

        self.screen.blit(glint_surface, (center[0] - hub_radius, center[1] - hub_radius))
        pygame.draw.circle(self.screen, self.hub_ring_color, center, max(2, hub_radius // 6))

    def _draw_wheel(
        self,
        center: Tuple[int, int],
        options: list,
        wheel_angle: float,
        highlight_index: Optional[int],
    ):
        count = len(options)
        if count == 0:
            return

        radius = self._get_wheel_radius()
        face_radius = max(20, radius - self.rim_thickness)
        slice_angle = (2 * math.pi) / count
        start_angle = wheel_angle - slice_angle / 2

        self._draw_wheel_backdrop(center, radius)
        self._draw_wheel_shadow(center, radius)
        self._draw_wheel_rim(center, radius)

        segments = []
        bevel = max(4, min(self.bevel_depth, face_radius - 6))
        for index, option in enumerate(options):
            seg_start = start_angle + slice_angle * index
            seg_end = seg_start + slice_angle
            base_color = self.segment_colors[index % len(self.segment_colors)]
            mid_angle = (seg_start + seg_end) / 2
            light_factor = 0.86 + 0.18 * math.cos(mid_angle - self.light_angle)
            color = self._shade_color(base_color, light_factor)
            if highlight_index is not None and index == highlight_index:
                color = self._shade_color(color, 1.08)

            outer_color = self._shade_color(color, 1.08)
            inner_color = self._shade_color(color, 0.82)
            self._draw_wedge(center, face_radius, seg_start, seg_end, outer_color)
            self._draw_wedge(center, face_radius - bevel, seg_start, seg_end, color)
            self._draw_wedge(center, face_radius - bevel * 2, seg_start, seg_end, inner_color)
            segments.append((seg_start, seg_end, option))

        self._draw_face_overlays(center, face_radius)

        for seg_start, seg_end, option in segments:
            self._draw_wedge_outline(center, face_radius, seg_start)
            self._draw_option_label(center, face_radius, seg_start, seg_end, option, count)

        pygame.draw.circle(self.screen, self.face_border_color, center, face_radius, 2)
        self._draw_face_inner_ring(center, face_radius)
        self._draw_rim_highlights(center, radius)
        self._draw_hub(center, face_radius)

    def _draw_wedge(self, center: Tuple[int, int], radius: int, start_angle: float, end_angle: float, color: tuple):
        steps = max(12, int(radius * abs(end_angle - start_angle) / 18))
        points = [center]
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * (i / steps)
            x = center[0] + math.cos(angle) * radius
            y = center[1] + math.sin(angle) * radius
            points.append((x, y))
        pygame.draw.polygon(self.screen, color, points)

    def _draw_wedge_outline(self, center: Tuple[int, int], radius: int, angle: float):
        x = center[0] + math.cos(angle) * radius
        y = center[1] + math.sin(angle) * radius
        pygame.draw.line(self.screen, self.wheel_divider_color, center, (x, y), 2)

    def _draw_option_label(
        self,
        center: Tuple[int, int],
        radius: int,
        start_angle: float,
        end_angle: float,
        option: str,
        option_count: int,
    ):
        label = self._format_option(option)
        if not label:
            return

        font = self._get_option_font(option_count, label)
        text_surface = font.render(label, True, self.label_color)
        shadow_surface = font.render(label, True, (0, 0, 0))
        shadow_surface.set_alpha(self.label_shadow_alpha)

        angle = (start_angle + end_angle) / 2
        distance = radius * 0.62
        x = center[0] + math.cos(angle) * distance
        y = center[1] + math.sin(angle) * distance

        rotation = math.degrees(angle)
        if 90 < rotation < 270:
            rotation += 180

        text_surface = pygame.transform.rotozoom(text_surface, -rotation, 1.0)
        shadow_surface = pygame.transform.rotozoom(shadow_surface, -rotation, 1.0)

        shadow_rect = shadow_surface.get_rect(
            center=(int(x + self.label_shadow_offset), int(y + self.label_shadow_offset))
        )
        self.screen.blit(shadow_surface, shadow_rect)

        text_rect = text_surface.get_rect(center=(int(x), int(y)))
        self.screen.blit(text_surface, text_rect)

    def _get_option_font(self, option_count: int, label: str) -> pygame.font.Font:
        size = self.option_base_size
        if option_count > 12:
            size = max(14, size - (option_count - 12))
        if len(label) > 1:
            size = max(12, size - (len(label) - 1))

        if size not in self._option_fonts:
            self._option_fonts[size] = pygame.font.Font(None, size)
        return self._option_fonts[size]

    def _draw_pointer(self, center: Tuple[int, int]):
        tip_y = int(center[1] - self._get_wheel_radius() - self.arrow_gap)
        base_y = tip_y - self.arrow_height
        half_width = self.arrow_width // 2

        shadow_w = self.arrow_width + 12
        shadow_h = self.arrow_height + 12
        shadow_surface = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        shadow_tip = (shadow_w // 2, shadow_h - 4)
        shadow_base_y = shadow_tip[1] - self.arrow_height
        shadow_points = [
            shadow_tip,
            (shadow_w // 2 - half_width, shadow_base_y),
            (shadow_w // 2 + half_width, shadow_base_y),
        ]
        pygame.draw.polygon(shadow_surface, (0, 0, 0, 120), shadow_points)
        shadow_x = center[0] - shadow_w // 2
        shadow_y = base_y - 2 + 4
        self.screen.blit(shadow_surface, (shadow_x, shadow_y))

        points = [
            (center[0], tip_y),
            (center[0] - half_width, base_y),
            (center[0] + half_width, base_y),
        ]
        pygame.draw.polygon(self.screen, self.pointer_outline, points)
        inner_points = [
            (center[0], tip_y - 2),
            (center[0] - max(2, half_width - 2), base_y + 2),
            (center[0] + max(2, half_width - 2), base_y + 2),
        ]
        pygame.draw.polygon(self.screen, self.pointer_color, inner_points)
        highlight_color = self._shade_color(self.pointer_outline, 1.05)
        pygame.draw.line(
            self.screen,
            highlight_color,
            (center[0] - half_width + 4, base_y + 3),
            (center[0] + half_width - 4, base_y + 3),
            2,
        )

    def _draw_pointer_indicator(
        self,
        center: Tuple[int, int],
        radius: int,
        options: list,
        wheel_angle: float,
        round_phase: str,
    ):
        pointer_option = self._get_pointer_option(options, wheel_angle)
        if pointer_option is None:
            return

        label = self._format_option(pointer_option)
        if not label:
            return

        indicator_text = f"Pointer: {label}"
        color = (255, 255, 255) if round_phase in ("windup", "spin") else (230, 230, 230)
        surface = self.font_indicator.render(indicator_text, True, color)

        tip_y = int(center[1] - radius - self.arrow_gap)
        text_y = tip_y - self.arrow_height - self.indicator_offset
        rect = surface.get_rect(center=(center[0], text_y))

        panel = pygame.Surface(
            (
                rect.width + self.pointer_panel_padding * 2,
                rect.height + self.pointer_panel_padding * 2,
            ),
            pygame.SRCALPHA,
        )
        panel.fill((0, 0, 0, 0))
        panel_rect = panel.get_rect(center=rect.center)
        pygame.draw.rect(
            panel,
            (*self.pointer_panel_bg, self.pointer_panel_alpha),
            panel.get_rect(),
            border_radius=self.pointer_panel_radius,
        )
        pygame.draw.rect(
            panel,
            (*self.pointer_panel_border, self.pointer_panel_alpha),
            panel.get_rect(),
            width=2,
            border_radius=self.pointer_panel_radius,
        )
        self.screen.blit(panel, panel_rect.topleft)
        self.screen.blit(surface, rect)

    def _draw_selected_sequence(
        self,
        center: Tuple[int, int],
        radius: int,
        selected_sequence: list,
        username_length_hint: int,
    ):
        display_len = max(username_length_hint, len(selected_sequence))
        if display_len <= 0:
            display_len = max(1, self.selected_max_shown)

        slots = []
        for i in range(display_len):
            if i < len(selected_sequence):
                option = selected_sequence[i]
                if option is None or option == "":
                    slot = "_"
                else:
                    slot = str(option).upper()
            else:
                slot = "_"
            slots.append(slot)

        line = "Username: " + " ".join(slots)
        text_surface = self.font_selected.render(line, True, self.selected_color)

        panel_padding = max(6, self.selected_panel_padding)
        max_text_width = max(1, self.width - (panel_padding * 2) - 20)
        if text_surface.get_width() > max_text_width:
            scale = max_text_width / text_surface.get_width()
            target_w = max(1, int(text_surface.get_width() * scale))
            target_h = max(1, int(text_surface.get_height() * scale))
            text_surface = pygame.transform.smoothscale(text_surface, (target_w, target_h))

        panel_width = text_surface.get_width() + panel_padding * 2
        panel_height = text_surface.get_height() + panel_padding * 2

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(
            panel,
            (*self.selected_panel_bg, self.selected_panel_alpha),
            panel.get_rect(),
            border_radius=self.selected_panel_radius,
        )
        pygame.draw.rect(
            panel,
            (*self.selected_panel_border, self.selected_panel_alpha),
            panel.get_rect(),
            width=2,
            border_radius=self.selected_panel_radius,
        )

        text_rect = text_surface.get_rect(center=(panel_width // 2, panel_height // 2))
        panel.blit(text_surface, text_rect)

        tip_y = int(center[1] - radius - self.arrow_gap)
        panel_y = tip_y - self.arrow_height - self.indicator_offset - self.selected_offset
        panel_rect = panel.get_rect(center=(center[0], panel_y))
        self.screen.blit(panel, panel_rect.topleft)

    def _get_pointer_index(self, options: list, wheel_angle: float) -> Optional[int]:
        if not options:
            return None
        slice_angle = (2 * math.pi) / len(options)
        start_angle = wheel_angle - slice_angle / 2
        relative = (self.pointer_angle - start_angle) % (2 * math.pi)
        return int(relative / slice_angle)

    def _get_pointer_option(self, options: list, wheel_angle: float) -> Optional[str]:
        index = self._get_pointer_index(options, wheel_angle)
        if index is None:
            return None
        if index < 0 or index >= len(options):
            return None
        return options[index]

    def _format_option(self, option: Optional[str]) -> str:
        if option is None:
            return "BLANK"
        if isinstance(option, str) and option == "":
            return "BLANK"
        return str(option).upper()

    def _shade_color(self, color: tuple, factor: float) -> tuple:
        return tuple(max(0, min(255, int(c * factor))) for c in color)
