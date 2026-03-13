"""Helpers for avatar fallbacks that show username initials."""

from __future__ import annotations

from typing import Tuple

import pygame


def get_avatar_initials(username: str, max_chars: int = 2) -> str:
    """Return up to `max_chars` initials derived from a username."""
    clean = str(username or "").strip().lstrip("@")
    if not clean:
        return "?"

    max_chars = max(1, int(max_chars))
    letters_only = "".join(ch for ch in clean if ch.isalpha())
    source = letters_only if letters_only else clean
    return source[:max_chars].upper()


def draw_avatar_initials(
    surface: pygame.Surface,
    username: str,
    center: Tuple[int, int],
    diameter: int,
    color: Tuple[int, int, int] = (255, 255, 255),
) -> None:
    """
    Draw username initials centered inside an avatar circle area.

    The text is skipped for very tiny avatars where it is unreadable.
    """
    diameter = max(1, int(diameter))
    if diameter < 12:
        return

    initials = get_avatar_initials(username)
    max_text_width = max(1, int(diameter * 0.72))
    max_text_height = max(1, int(diameter * 0.62))

    font_size = max(10, int(diameter * 0.58))
    text_surface = None
    while font_size >= 8:
        font = pygame.font.Font(None, font_size)
        candidate = font.render(initials, True, color)
        if candidate.get_width() <= max_text_width and candidate.get_height() <= max_text_height:
            text_surface = candidate
            break
        font_size -= 1

    if text_surface is None:
        font = pygame.font.Font(None, 8)
        text_surface = font.render(initials, True, color)

    text_rect = text_surface.get_rect(center=(int(center[0]), int(center[1])))
    surface.blit(text_surface, text_rect)
