"""
Shared helper for rendering the club member spotlight panel.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

import pygame

import config


def _wrap_panel_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        words = raw_line.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            test_line = f"{current} {word}"
            if font.size(test_line)[0] <= max_width:
                current = test_line
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _draw_glow_at(
    screen: pygame.Surface,
    pos: tuple[int, int],
    size: int,
    glow_cache: dict,
) -> None:
    size = max(1, int(size))
    radius = max(1, size // 2)
    color = getattr(config, "CLUB_GLOW_COLOR", (255, 240, 190))
    alpha = int(getattr(config, "CLUB_GLOW_ALPHA", 180))
    layers = int(getattr(config, "CLUB_GLOW_LAYERS", 3))
    padding = int(getattr(config, "CLUB_GLOW_PADDING", 3))

    cache_key = (radius, color, alpha, layers, padding)
    surface = glow_cache.get(cache_key)
    if surface is None:
        glow_radius = radius + padding + layers
        size_px = glow_radius * 2 + 4
        surface = pygame.Surface((size_px, size_px), pygame.SRCALPHA)
        center = (size_px // 2, size_px // 2)

        base_radius = radius + padding
        for i in range(max(1, layers)):
            layer_alpha = int(alpha * (1.0 - (i / max(1, layers))))
            ring_radius = base_radius + i
            pygame.draw.circle(
                surface,
                (*color, layer_alpha),
                center,
                ring_radius,
                width=2,
            )

        inner_alpha = min(255, alpha + 40)
        pygame.draw.circle(
            surface,
            (*color, inner_alpha),
            center,
            radius + 1,
            width=2,
        )

        glow_cache[cache_key] = surface

    rect = surface.get_rect(center=(int(pos[0]), int(pos[1])))
    screen.blit(surface, rect)


def draw_club_panel(
    screen: pygame.Surface,
    spotlight,
    *,
    anchor_y: int,
    font: Optional[pygame.font.Font] = None,
    get_avatar_surface: Optional[Callable[[object, int], pygame.Surface]] = None,
    glow_cache: Optional[dict] = None,
    panel_text: Optional[str] = None,
    panel_width: Optional[int] = None,
    panel_padding: Optional[int] = None,
    panel_alpha: Optional[int] = None,
    panel_spacing: Optional[int] = None,
    avatar_size_hint: Optional[int] = None,
    panel_text_color: Sequence[int] = (245, 245, 245),
) -> Optional[pygame.Rect]:
    if spotlight is None:
        return None

    if not bool(getattr(config, "CLUB_PANEL_ENABLED", True)):
        return None

    if panel_text is None:
        panel_text = str(getattr(
            config,
            "CLUB_PANEL_TEXT",
            "Club members stay visible and have a holy light.",
        ))
    if not panel_text:
        return None

    if panel_width is None:
        panel_width = int(getattr(config, "CLUB_PANEL_WIDTH", 160))
    if panel_padding is None:
        panel_padding = int(getattr(config, "CLUB_PANEL_PADDING", 6))
    if panel_alpha is None:
        panel_alpha = int(getattr(config, "CLUB_PANEL_ALPHA", 150))
    if panel_spacing is None:
        panel_spacing = int(getattr(config, "CLUB_PANEL_SPACING", 8))
    if avatar_size_hint is None:
        avatar_size_hint = int(getattr(config, "CLUB_PANEL_AVATAR_SIZE", 42))

    if font is None:
        text_size = int(getattr(config, "CLUB_PANEL_TEXT_SIZE", 16))
        font = pygame.font.Font(None, text_size)

    panel_w = max(1, int(panel_width))
    panel_x = int((screen.get_width() - panel_w) / 2)

    line_height = font.get_height()
    line_gap = max(0, font.get_linesize() - line_height)
    min_avatar_size = 16
    max_avatar_size = max(min_avatar_size, int(panel_w * 0.45))
    avatar_size = max(min_avatar_size, min(max_avatar_size, int(avatar_size_hint)))
    lines: list[str] = []
    text_height = line_height

    for _ in range(4):
        text_area_w = panel_w - (panel_padding * 3) - avatar_size
        if text_area_w < 40:
            text_area_w = 40
        lines = _wrap_panel_text(panel_text, font, text_area_w)
        if not lines:
            lines = [""]
        text_height = (line_height * len(lines)) + (line_gap * max(0, len(lines) - 1))
        new_avatar_size = max(min_avatar_size, min(max_avatar_size, int(text_height)))
        if new_avatar_size == avatar_size:
            break
        avatar_size = new_avatar_size

    text_area_w = panel_w - (panel_padding * 3) - avatar_size
    if text_area_w < 40:
        text_area_w = 40
    lines = _wrap_panel_text(panel_text, font, text_area_w)
    if not lines:
        lines = [""]
    text_height = (line_height * len(lines)) + (line_gap * max(0, len(lines) - 1))
    panel_h = max(1, int(text_height))

    panel_y = int(anchor_y + panel_spacing)
    if panel_y + panel_h > screen.get_height() - 6:
        panel_y = max(6, screen.get_height() - panel_h - 6)

    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, max(0, min(255, panel_alpha))))
    screen.blit(panel, (panel_x, panel_y))

    text_x = panel_x + panel_padding
    text_y = panel_y + max(0, int((panel_h - text_height) / 2))
    for line in lines:
        text_surface = font.render(line, True, panel_text_color)
        screen.blit(text_surface, (text_x, text_y))
        text_y += line_height + line_gap

    avatar_center_x = panel_x + panel_w - panel_padding - (avatar_size // 2)
    avatar_center_y = panel_y + (panel_h // 2)

    if glow_cache is not None:
        _draw_glow_at(
            screen,
            (avatar_center_x, avatar_center_y),
            avatar_size,
            glow_cache,
        )

    if get_avatar_surface is not None:
        avatar_surface = get_avatar_surface(spotlight, avatar_size)
        avatar_rect = avatar_surface.get_rect(center=(avatar_center_x, avatar_center_y))
        screen.blit(avatar_surface, avatar_rect)

    return pygame.Rect(panel_x, panel_y, panel_w, panel_h)
