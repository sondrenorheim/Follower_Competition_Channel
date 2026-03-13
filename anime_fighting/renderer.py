"""
Rendering System for Anime Fighting

Handles all visual output for the anime fighting game:
- Match rendering (fighters, effects, UI)
- HP bars
- Tournament bracket transitions
- Winner podium

Adapted for 540x960 vertical screen layout.
"""

from datetime import datetime
import os
from typing import List, Tuple, Optional
import pygame

import config
from shared.avatar_initials import draw_avatar_initials
from .camera_fx import (
    draw_particles, draw_afterimages, draw_hitfields, draw_projectiles, clamp
)


class AnimeFightingRenderer:
    """
    Renders all visual elements for anime fighting mode

    Screen layout (540x960 vertical):
    - Top 100px: Match info and timer
    - Middle 660px: Combat arena with effects
    - Bottom 200px: HP bars and stats
    """

    def __init__(self, screen: pygame.Surface):
        """
        Initialize renderer

        Args:
            screen: Pygame screen surface (540x960)
        """
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()

        # Fonts
        self.font_large = pygame.font.Font(None, 72)
        self.font_title = pygame.font.Font(None, 56)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 18)
        self.font_promo = pygame.font.Font(None, 24)

        # Promo overlay
        self.promo_text_left = "Join Discord, link in bio"
        self.promo_text_right = "Check your results in bio"
        self.discord_logo = None
        self.trophy_logo = None
        self._load_promo_assets()

        # Colors
        self.bg_color = (14, 14, 18)
        self.arena_floor_color = (34, 34, 44)
        self.arena_border_color = (75, 75, 95)

        # HP bar colors
        self.hp_fg = (235, 85, 85)
        self.hp_bg = (25, 25, 30)

    def render_match(
        self,
        world_surface: pygame.Surface,
        fighter1,
        fighter2,
        hitshapes: List,
        projectiles: List,
        particles: List,
        afterimages: List,
        match_state: dict
    ):
        """
        Render active 1v1 match

        Args:
            world_surface: Surface to draw world elements on
            fighter1: First fighter
            fighter2: Second fighter
            hitshapes: Active hitboxes
            projectiles: Active projectiles
            particles: Active particles
            afterimages: Active afterimages
            match_state: Dict with match info (round_name, match_num, timer, etc.)
        """
        # Clear world surface
        world_surface.fill((0, 0, 0, 0))

        # Draw visual effects in layers
        draw_afterimages(world_surface, afterimages)
        draw_hitfields(world_surface, hitshapes)
        draw_projectiles(world_surface, projectiles)
        draw_particles(world_surface, particles)

        # Draw energy beams (Kamehameha) - rendered before fighters for layering
        for fighter in [fighter1, fighter2]:
            if fighter:
                beam_data = fighter.get_beam_data()
                if beam_data:
                    self._render_energy_beam(world_surface, beam_data)

        # Draw fighters
        if fighter1:
            fighter1.draw(world_surface)
        if fighter2:
            fighter2.draw(world_surface)

    def _render_energy_beam(self, surface: pygame.Surface, beam_data: dict):
        """
        Render a Kamehameha-style energy beam as a solid laser with glow

        Args:
            surface: Surface to draw on
            beam_data: Dict with 'start', 'end', 'intensity', 'color'
        """
        start = beam_data['start']
        end = beam_data['end']
        intensity = beam_data.get('intensity', 1.0)

        # Convert to integer coordinates
        start_pos = (int(start.x), int(start.y))
        end_pos = (int(end.x), int(end.y))

        # Beam colors (blue/white energy)
        # Outer glow layers (drawn first, widest)
        glow_colors = [
            ((50, 80, 180), 28),    # Deep blue outer glow
            ((80, 120, 220), 22),   # Medium blue
            ((120, 160, 255), 16),  # Light blue
            ((180, 200, 255), 10),  # Pale blue inner glow
        ]

        # Core beam layers
        core_colors = [
            ((200, 220, 255), 8),   # Bright blue-white
            ((240, 245, 255), 5),   # Near white
            ((255, 255, 255), 3),   # Pure white core
        ]

        # Apply intensity scaling
        alpha_mult = intensity

        # Draw glow layers (outer to inner)
        for color, width in glow_colors:
            scaled_width = max(1, int(width * intensity))
            # Slight alpha effect via color dimming for glow
            dimmed = (
                int(color[0] * alpha_mult),
                int(color[1] * alpha_mult),
                int(color[2] * alpha_mult)
            )
            pygame.draw.line(surface, dimmed, start_pos, end_pos, scaled_width)

        # Draw core layers (bright center)
        for color, width in core_colors:
            scaled_width = max(1, int(width * intensity))
            pygame.draw.line(surface, color, start_pos, end_pos, scaled_width)

        # Add bright endpoint circles for energy feel
        # Origin point (at hands)
        pygame.draw.circle(surface, (200, 220, 255), start_pos, int(12 * intensity))
        pygame.draw.circle(surface, (255, 255, 255), start_pos, int(6 * intensity))

        # Impact point (at target)
        pygame.draw.circle(surface, (255, 200, 100), end_pos, int(18 * intensity))
        pygame.draw.circle(surface, (255, 255, 200), end_pos, int(10 * intensity))
        pygame.draw.circle(surface, (255, 255, 255), end_pos, int(5 * intensity))

    def render_ui(
        self,
        fighter1,
        fighter2,
        match_state: dict
    ):
        """
        Render UI elements (HP bars, timer, match info)

        Args:
            fighter1: First fighter
            fighter2: Second fighter
            match_state: Dict with match info
        """
        # Top section: Match info and timer
        self._draw_match_header(match_state)

        # Bottom section: HP/Stamina bars
        if fighter1 and fighter2:
            self._draw_fighter_bars(fighter1, fighter2)

    def _draw_match_header(self, match_state: dict):
        """
        Draw match info and timer at top of screen

        Args:
            match_state: Dict with round_name, match_num, total_matches, timer,
                        is_finals, finals_wins, finals_game
        """
        y_pos = 20

        # Check if this is the Best-of-3 Finals
        is_finals = match_state.get("is_finals", False)
        finals_wins = match_state.get("finals_wins")
        finals_game = match_state.get("finals_game")

        prompt_text = getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "")
        prompt_y = None

        if is_finals and finals_wins:
            # GRAND FINALS header
            title_text = "GRAND FINALS"
            text = self.font_medium.render(title_text, True, (255, 215, 0))  # Gold
            text_rect = text.get_rect(center=(self.width // 2, y_pos + 15))
            self.screen.blit(text, text_rect)

            # Best of 3 - Game X
            game_text = f"Best of 3 - Game {finals_game}"
            text = self.font_small.render(game_text, True, (200, 200, 210))
            text_rect = text.get_rect(center=(self.width // 2, y_pos + 42))
            self.screen.blit(text, text_rect)

            # Score display: [Fighter1 Wins] - [Fighter2 Wins]
            score_text = f"[ {finals_wins.get(1, 0)} ] - [ {finals_wins.get(2, 0)} ]"
            text = self.font_medium.render(score_text, True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.width // 2, y_pos + 68))
            self.screen.blit(text, text_rect)

            # Timer (positioned lower for finals)
            timer = match_state.get("timer", 0.0)
            timer_text = f"{int(timer)}"
            text = self.font_large.render(timer_text, True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.width // 2, y_pos + 105))
            self.screen.blit(text, text_rect)
            prompt_y = text_rect.bottom + 10
        else:
            # Standard match header
            # Round name (e.g., "Finals", "Semifinals")
            round_name = match_state.get("round_name", "Match")
            text = self.font_medium.render(round_name, True, (200, 200, 210))
            text_rect = text.get_rect(center=(self.width // 2, y_pos + 15))
            self.screen.blit(text, text_rect)

            # Match number (e.g., "Match 1/8")
            if "match_num" in match_state and "total_matches" in match_state:
                match_text = f"Match {match_state['match_num']}/{match_state['total_matches']}"
                text = self.font_small.render(match_text, True, (160, 160, 170))
                text_rect = text.get_rect(center=(self.width // 2, y_pos + 50))
                self.screen.blit(text, text_rect)

            # Timer
            timer = match_state.get("timer", 0.0)
            timer_text = f"{int(timer)}"
            text = self.font_large.render(timer_text, True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.width // 2, y_pos + 85))
            self.screen.blit(text, text_rect)
            prompt_y = text_rect.bottom + 10

        if prompt_text and prompt_y is not None:
            prompt_surface = self.font_tiny.render(prompt_text, True, (200, 200, 210))
            prompt_rect = prompt_surface.get_rect(center=(self.width // 2, prompt_y))
            self.screen.blit(prompt_surface, prompt_rect)

    def _draw_fighter_bars(self, fighter1, fighter2):
        """
        Draw HP bars for both fighters

        Args:
            fighter1: First fighter (left side)
            fighter2: Second fighter (right side)
        """
        # Bottom section starting position
        y_start = self.height - 190

        # Fighter 1 (left side) - HP only
        self._draw_bar(
            x=20,
            y=y_start,
            width=240,
            height=24,
            value=fighter1.hp,
            max_value=fighter1.match_start_hp if hasattr(fighter1, 'match_start_hp') else fighter1.max_hp,
            fg_color=self.hp_fg,
            bg_color=self.hp_bg,
            label=fighter1.username[:12],
            label_size="medium"
        )

        # Fighter 2 (right side) - HP only
        self._draw_bar(
            x=self.width - 260,
            y=y_start,
            width=240,
            height=24,
            value=fighter2.hp,
            max_value=fighter2.match_start_hp if hasattr(fighter2, 'match_start_hp') else fighter2.max_hp,
            fg_color=self.hp_fg,
            bg_color=self.hp_bg,
            label=fighter2.username[:12],
            label_size="medium"
        )

        # Final Smash meters (below HP bars)
        fs_meter_y = y_start + 30  # 30px below HP bar
        self._draw_final_smash_meter(x=20, y=fs_meter_y, width=240, fighter=fighter1)
        self._draw_final_smash_meter(x=self.width-260, y=fs_meter_y, width=240, fighter=fighter2)

    def _draw_bar(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        value: float,
        max_value: float,
        fg_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
        label: str,
        label_size: str = "small"
    ):
        """
        Draw a horizontal bar (HP or stamina)

        Args:
            x, y: Top-left position
            width, height: Bar dimensions
            value: Current value
            max_value: Maximum value
            fg_color: Foreground color (ignored - uses HP-based gradient)
            bg_color: Background color
            label: Text label
            label_size: Font size ("small", "medium", "large")
        """
        # Calculate HP percentage
        hp_percent = clamp(value / max_value, 0, 1)

        # Background
        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=8)

        # Foreground with gradient from green (100%) to red (0%)
        fill = int(width * hp_percent)
        if fill > 0:
            # Interpolate color: green (0, 255, 0) -> yellow (255, 255, 0) -> red (255, 0, 0)
            if hp_percent > 0.5:
                # Green to yellow (100% to 50%)
                t = (hp_percent - 0.5) * 2  # 0.0 to 1.0
                r = int(255 * (1 - t))
                g = 255
                b = 0
            else:
                # Yellow to red (50% to 0%)
                t = hp_percent * 2  # 0.0 to 1.0
                r = 255
                g = int(255 * t)
                b = 0

            bar_color = (r, g, b)
            pygame.draw.rect(self.screen, bar_color, (x, y, fill, height), border_radius=8)

        # Label centered above bar
        font = {
            "small": self.font_tiny,
            "medium": self.font_small,
            "large": self.font_medium
        }.get(label_size, self.font_small)

        text = font.render(label, True, (235, 235, 240))
        text_rect = text.get_rect(center=(x + width // 2, y - 15))
        self.screen.blit(text, text_rect)

        # Percentage counter centered on the bar
        percent_text = f"{int(hp_percent * 100)}%"
        percent_surf = self.font_tiny.render(percent_text, True, (255, 255, 255))
        percent_rect = percent_surf.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(percent_surf, percent_rect)

    def _draw_final_smash_meter(
        self,
        x: int,
        y: int,
        width: int,
        fighter
    ):
        """
        Draw Final Smash meter below HP bar

        Visual design:
        - Height: 18px (smaller than HP bar's 24px)
        - Background: Dark purple/black
        - Foreground: Gradient gold/orange when charging, pulsing rainbow when ready
        - Border: Glowing when ready
        - Text: "FINAL SMASH!" when full
        """
        import time
        import math

        height = 18
        meter_percent = fighter.final_smash_meter / 100.0

        # Background
        bg_color = (20, 10, 30)  # Dark purple
        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=6)

        # Foreground fill
        fill_width = int(width * meter_percent)
        if fill_width > 0:
            if fighter.final_smash_ready:
                # Rainbow pulsing effect when ready
                pulse = (math.sin(time.time() * 5) + 1) / 2  # 0 to 1
                color_offset = int(pulse * 60)
                colors = [
                    (max(0, 255 - color_offset), min(255, 215 + color_offset), 0),      # Gold
                    (255, min(255, 140 + color_offset), 0),                              # Orange
                    (max(0, 255 - color_offset), min(255, 69 + color_offset), 0)        # Red-orange
                ]
                # Draw gradient stripes
                stripe_width = fill_width // 3
                for i, color in enumerate(colors):
                    stripe_x = x + i * stripe_width
                    stripe_w = min(stripe_width, fill_width - i * stripe_width)
                    if stripe_w > 0:
                        pygame.draw.rect(self.screen, color,
                                       (stripe_x, y, stripe_w, height),
                                       border_radius=6)
            else:
                # Orange-gold gradient when charging
                for i in range(fill_width):
                    t = i / width
                    r = int(255)
                    g = int(140 + 75 * t)  # 140 to 215 (orange to gold)
                    b = 0
                    pygame.draw.line(self.screen, (r, g, b), (x + i, y), (x + i, y + height))

        # Border (glowing when ready)
        if fighter.final_smash_ready:
            border_color = (255, 215, 0)  # Gold
            border_width = 3
        else:
            border_color = (80, 60, 100)  # Muted purple
            border_width = 2
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), border_width, border_radius=6)

        # Label text
        if fighter.final_smash_ready:
            text_str = "FINAL SMASH!"
            text_color = (255, 255, 100)  # Bright yellow
            text = self.font_small.render(text_str, True, text_color)
        else:
            text_str = f"{int(fighter.final_smash_meter)}%"
            text_color = (200, 180, 220)  # Light purple
            text = self.font_tiny.render(text_str, True, text_color)

        text_rect = text.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text, text_rect)

    def render_countdown(self, count: int):
        """
        Render countdown overlay (3, 2, 1, FIGHT!)

        Args:
            count: Countdown number (3, 2, 1, 0 for "FIGHT!")
        """
        text = str(count) if count > 0 else "FIGHT!"
        rendered = self.font_large.render(text, True, (255, 255, 255))
        rect = rendered.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(rendered, rect)

    def render_winner_announcement(self, winner, finals_info: dict = None):
        """
        Render winner announcement overlay

        Args:
            winner: Winning fighter
            finals_info: Optional dict with 'wins' ({1: int, 2: int}), 'game' (int),
                        'is_series_over' (bool), 'fighter1_name', 'fighter2_name'
        """
        # Check if this is a finals game win
        if finals_info:
            wins = finals_info.get('wins', {1: 0, 2: 0})
            game_num = finals_info.get('game', 1)
            is_series_over = finals_info.get('is_series_over', False)
            f1_name = finals_info.get('fighter1_name', 'Fighter 1')
            f2_name = finals_info.get('fighter2_name', 'Fighter 2')

            if is_series_over:
                # Series winner announcement
                text = self.font_title.render(f"{winner.username}", True, (255, 215, 0))
                rect = text.get_rect(center=(self.width // 2, self.height // 2 - 80))
                self.screen.blit(text, rect)

                champ_text = self.font_medium.render("CHAMPION!", True, (255, 255, 255))
                champ_rect = champ_text.get_rect(center=(self.width // 2, self.height // 2 - 40))
                self.screen.blit(champ_text, champ_rect)

                # Final score
                score_text = f"{wins.get(1, 0)} - {wins.get(2, 0)}"
                score_surf = self.font_large.render(score_text, True, (255, 215, 0))
                score_rect = score_surf.get_rect(center=(self.width // 2, self.height // 2 + 10))
                self.screen.blit(score_surf, score_rect)
            else:
                # Game win (series continues)
                text = self.font_title.render(f"{winner.username}", True, (255, 215, 0))
                rect = text.get_rect(center=(self.width // 2, self.height // 2 - 60))
                self.screen.blit(text, rect)

                wins_text = self.font_medium.render(f"WINS GAME {game_num}!", True, (255, 255, 255))
                wins_rect = wins_text.get_rect(center=(self.width // 2, self.height // 2 - 20))
                self.screen.blit(wins_text, wins_rect)

                # Current score
                score_text = f"[ {wins.get(1, 0)} ] - [ {wins.get(2, 0)} ]"
                score_surf = self.font_medium.render(score_text, True, (200, 200, 210))
                score_rect = score_surf.get_rect(center=(self.width // 2, self.height // 2 + 20))
                self.screen.blit(score_surf, score_rect)

            # Draw winner avatar (large)
            if hasattr(winner, 'avatar_surface') and winner.avatar_surface:
                avatar_size = 100
                scaled_avatar = pygame.transform.smoothscale(winner.avatar_surface, (avatar_size, avatar_size))
                avatar_rect = scaled_avatar.get_rect(center=(self.width // 2, self.height // 2 + 90))
                self.screen.blit(scaled_avatar, avatar_rect)
        else:
            # Standard winner announcement
            text = self.font_title.render(f"{winner.username} WINS!", True, (255, 215, 0))
            rect = text.get_rect(center=(self.width // 2, self.height // 2 - 50))
            self.screen.blit(text, rect)

            # Draw winner avatar (large)
            if hasattr(winner, 'avatar_surface') and winner.avatar_surface:
                avatar_size = 120
                scaled_avatar = pygame.transform.smoothscale(winner.avatar_surface, (avatar_size, avatar_size))
                avatar_rect = scaled_avatar.get_rect(center=(self.width // 2, self.height // 2 + 60))
                self.screen.blit(scaled_avatar, avatar_rect)

    def render_bracket_transition(self, current_round: str, matches_remaining: int):
        """
        Render bracket transition screen between rounds

        Args:
            current_round: Round name (e.g., "Semifinals")
            matches_remaining: Number of matches left in tournament
        """
        # Clear screen
        self.screen.fill(self.bg_color)

        # Round name
        text = self.font_title.render(current_round, True, (255, 255, 255))
        rect = text.get_rect(center=(self.width // 2, self.height // 2 - 40))
        self.screen.blit(text, rect)

        # Matches remaining
        matches_text = f"{matches_remaining} matches remaining"
        text = self.font_medium.render(matches_text, True, (180, 180, 190))
        rect = text.get_rect(center=(self.width // 2, self.height // 2 + 20))
        self.screen.blit(text, rect)

    def render_round_intro(self, header_text: str, round_label: str):
        """
        Render a round intro screen before the bracket overview

        Args:
            header_text: Top line (e.g., "March Leaderboard")
            round_label: Round label (e.g., "Top 16", "Quarterfinals")
        """
        # Clear screen
        self.screen.fill(self.bg_color)

        # Header line
        header = self.font_medium.render(header_text, True, (255, 215, 0))
        header_rect = header.get_rect(center=(self.width // 2, self.height // 2 - 30))
        self.screen.blit(header, header_rect)

        # Round label
        label = self.font_title.render(round_label, True, (255, 255, 255))
        label_rect = label.get_rect(center=(self.width // 2, self.height // 2 + 20))
        self.screen.blit(label, label_rect)

    def render_top16_overview(self, header_text: str, entries: List[Tuple]):
        """
        Render a grid of top 16 qualifiers with avatars and monthly points.

        Args:
            header_text: Header line (e.g., "March Leaderboard")
            entries: List of (fighter, points) tuples
        """
        # Clear screen
        self.screen.fill(self.bg_color)

        # Header
        header = self.font_medium.render(header_text, True, (255, 215, 0))
        header_rect = header.get_rect(center=(self.width // 2, 30))
        self.screen.blit(header, header_rect)

        subheader = self.font_small.render("Top 16 Qualifiers", True, (180, 180, 190))
        subheader_rect = subheader.get_rect(center=(self.width // 2, 60))
        self.screen.blit(subheader, subheader_rect)

        if not entries:
            return

        columns = 4
        card_width = 120
        card_height = 130
        spacing_x = 10
        spacing_y = 12

        rows = (len(entries) + columns - 1) // columns
        total_width = columns * card_width + (columns - 1) * spacing_x
        total_height = rows * card_height + (rows - 1) * spacing_y

        start_x = (self.width - total_width) // 2
        start_y = max(110, (self.height - total_height) // 2)

        for idx, (fighter, points) in enumerate(entries):
            row = idx // columns
            col = idx % columns
            x = start_x + col * (card_width + spacing_x)
            y = start_y + row * (card_height + spacing_y)
            self._draw_top16_overview_card(fighter, points, x, y, card_width, card_height)

    def _draw_top16_overview_card(self, fighter, points, x: int, y: int, width: int, height: int):
        """Draw a single qualifier card with avatar, name, and points."""
        bg_color = (40, 40, 45)
        border_color = (90, 90, 100)
        text_color = (255, 255, 255)
        points_color = (200, 200, 210)

        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=6)
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), 1, border_radius=6)

        avatar_size = 64
        avatar_x = x + (width - avatar_size) // 2
        avatar_y = y + 8

        if hasattr(fighter, 'avatar_surface') and fighter.avatar_surface:
            try:
                scaled_avatar = pygame.transform.smoothscale(fighter.avatar_surface, (avatar_size, avatar_size))
                self.screen.blit(scaled_avatar, (avatar_x, avatar_y))
            except Exception:
                pygame.draw.circle(
                    self.screen,
                    fighter.color if hasattr(fighter, 'color') else (100, 100, 255),
                    (x + width // 2, avatar_y + avatar_size // 2),
                    avatar_size // 2
                )
        else:
            pygame.draw.circle(
                self.screen,
                fighter.color if hasattr(fighter, 'color') else (100, 100, 255),
                (x + width // 2, avatar_y + avatar_size // 2),
                avatar_size // 2
            )

        name = fighter.username[:10] if hasattr(fighter, 'username') else "Unknown"
        name_surf = self.font_tiny.render(name, True, text_color)
        name_rect = name_surf.get_rect(center=(x + width // 2, avatar_y + avatar_size + 14))
        self.screen.blit(name_surf, name_rect)

        points_text = f"{self._format_points(points)} pts"
        points_surf = self.font_tiny.render(points_text, True, points_color)
        points_rect = points_surf.get_rect(center=(x + width // 2, avatar_y + avatar_size + 32))
        self.screen.blit(points_surf, points_rect)

    def _format_points(self, points) -> str:
        """Format points for display."""
        try:
            value = float(points)
        except (TypeError, ValueError):
            return "0"

        if abs(value - int(value)) < 0.01:
            return str(int(value))
        return f"{value:.1f}"

    def render_promo_overlay(self):
        """Render promo pills at the bottom of the screen."""
        self._draw_promo_overlay()

    def _get_pill_size(self, text: str, logo_surface: Optional[pygame.Surface]) -> Tuple[int, int]:
        """Compute size for a pill with text and optional icon."""
        padding_x = 12
        padding_y = 6
        gap = 8

        text_surface = self.font_promo.render(text, True, (255, 255, 255))
        text_width, text_height = text_surface.get_size()

        logo_width = logo_surface.get_width() if logo_surface else 0
        logo_height = logo_surface.get_height() if logo_surface else 0

        pill_height = max(text_height, logo_height) + padding_y * 2
        pill_width = text_width + padding_x * 2 + (logo_width + gap if logo_surface else 0)

        return pill_width, pill_height

    def _draw_pill(self, text: str, logo_surface: Optional[pygame.Surface], center: Tuple[int, int]):
        """Draw a single promo pill with optional icon."""
        text_surface = self.font_promo.render(text, True, (255, 255, 255))
        text_width, text_height = text_surface.get_size()
        logo_width = logo_surface.get_width() if logo_surface else 0
        logo_height = logo_surface.get_height() if logo_surface else 0
        padding_x = 12
        padding_y = 6
        gap = 8

        pill_width = text_width + padding_x * 2 + (logo_width + gap if logo_surface else 0)
        pill_height = max(text_height, logo_height) + padding_y * 2

        pill_rect = pygame.Rect(0, 0, pill_width, pill_height)
        pill_rect.center = center

        # Background and border
        pygame.draw.rect(self.screen, (30, 30, 36), pill_rect, border_radius=16)
        pygame.draw.rect(self.screen, (90, 90, 105), pill_rect, 1, border_radius=16)

        # Content (icon + text)
        content_x = pill_rect.x + padding_x
        if logo_surface:
            logo_y = pill_rect.y + (pill_height - logo_height) // 2
            self.screen.blit(logo_surface, (content_x, logo_y))
            content_x += logo_width + gap

        text_center_y = pill_rect.y + pill_height // 2
        shadow_text = self.font_promo.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(midleft=(content_x, text_center_y))
        self.screen.blit(shadow_text, shadow_rect.move(1, 1))

        text_rect = text_surface.get_rect(midleft=(content_x, text_center_y))
        self.screen.blit(text_surface, text_rect)

    def _draw_promo_overlay(self):
        """Draw promo pills in the bottom banner area."""
        base_y = self.height - 28
        gap_between = 12
        margin_x = 24

        left_width, left_height = self._get_pill_size(self.promo_text_left, self.discord_logo)
        right_width, right_height = self._get_pill_size(self.promo_text_right, self.trophy_logo)

        left_center = (margin_x + left_width // 2, base_y)
        right_center = (self.width - margin_x - right_width // 2, base_y)

        left_rect = pygame.Rect(0, 0, left_width, left_height)
        left_rect.center = left_center
        right_rect = pygame.Rect(0, 0, right_width, right_height)
        right_rect.center = right_center

        if left_rect.right + gap_between > right_rect.left:
            total_width = left_width + right_width + gap_between
            start_x = (self.width - total_width) // 2
            left_center = (start_x + left_width // 2, base_y)
            right_center = (start_x + left_width + gap_between + right_width // 2, base_y)

        self._draw_pill(self.promo_text_left, self.discord_logo, left_center)
        self._draw_pill(self.promo_text_right, self.trophy_logo, right_center)

    def _load_promo_assets(self):
        """Load and scale promo logos for the overlay pills."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        discord_path = os.path.join(base_dir, "discord_logo.png")
        self.discord_logo = self._load_logo([discord_path])

        trophy_paths = [
            os.path.join(base_dir, "trophy.png"),
            os.path.join(base_dir, "trophy_icon.png"),
            os.path.join(base_dir, "assets", "trophy.png"),
            os.path.join(base_dir, "website", "src", "assets", "trophy.png"),
            os.path.join(base_dir, "website", "public", "trophy.png"),
            os.path.join(base_dir, "website", "dist", "trophy.png"),
        ]
        self.trophy_logo = self._load_logo(trophy_paths)
        if self.trophy_logo is None:
            self.trophy_logo = self._render_emoji_icon("\U0001F3C6")

    def _load_logo(self, paths: List[str]) -> Optional[pygame.Surface]:
        """Load and scale a logo from the first existing path."""
        target_height = max(16, int(self.font_promo.get_height() * 1.2))
        for logo_path in paths:
            if not os.path.exists(logo_path):
                continue

            try:
                logo = pygame.image.load(logo_path).convert_alpha()
                if logo.get_height() <= 0:
                    return None
                scale = target_height / logo.get_height()
                target_width = max(1, int(logo.get_width() * scale))
                return pygame.transform.smoothscale(logo, (target_width, target_height))
            except Exception:
                return None

        return None

    def _render_emoji_icon(self, emoji_text: str) -> Optional[pygame.Surface]:
        """Render a small emoji icon as a surface fallback."""
        target_height = max(16, int(self.font_promo.get_height() * 1.2))
        try:
            emoji_font = pygame.font.SysFont("Segoe UI Emoji", target_height)
            emoji_surface = emoji_font.render(emoji_text, True, (255, 255, 255))
            if emoji_surface is None:
                return None
            return emoji_surface.convert_alpha()
        except Exception:
            return None

    def render_podium(self, winner, runner_up, semifinalists: List):
        """
        Render professional tournament results screen with top 4 finishers

        Args:
            winner: 1st place fighter
            runner_up: 2nd place fighter
            semifinalists: List of 3rd/4th place fighters
        """
        # Clear screen with gradient effect
        for y in range(self.height):
            blend = y / self.height
            color = (
                int(12 + 24 * blend),
                int(12 + 20 * blend),
                int(18 + 30 * blend)
            )
            pygame.draw.line(self.screen, color, (0, y), (self.width, y))

        # Dark overlay for dramatic effect
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 35))
        self.screen.blit(overlay, (0, 0))

        # Championship banner
        banner_height = 110
        pygame.draw.rect(self.screen, (28, 28, 34), (0, 0, self.width, banner_height))
        pygame.draw.line(self.screen, (255, 215, 0), (0, banner_height - 2), (self.width, banner_height - 2), 2)
        pygame.draw.line(self.screen, (120, 90, 30), (0, banner_height - 6), (self.width, banner_height - 6), 1)

        # Gold glow behind header
        glow = pygame.Surface((self.width, banner_height), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 215, 0, 60), (self.width // 2, banner_height), 240)
        self.screen.blit(glow, (0, 0))

        # Title
        month_name = datetime.now().strftime("%B")
        title_text = f"{month_name} Champion"
        title = self.font_title.render(title_text, True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.width // 2, 36))
        self.screen.blit(title, title_rect)

        subtitle = self.font_small.render("Monthly Tournament Winner", True, (190, 190, 200))
        subtitle_rect = subtitle.get_rect(center=(self.width // 2, 72))
        self.screen.blit(subtitle, subtitle_rect)

        # Results list with clean card design
        y_offset = 130

        # Champion spotlight
        spotlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.circle(spotlight, (255, 215, 120, 35), (self.width // 2, y_offset + 10), 220)
        self.screen.blit(spotlight, (0, 0))

        # 1st Place - Champion (large, centered, gold)
        self._draw_result_card(winner, self.width // 2, y_offset, 1, is_champion=True)

        # 2nd Place - Runner Up
        if runner_up:
            self._draw_result_card(runner_up, self.width // 2, y_offset + 180, 2)

        # 3rd/4th Place - Semifinalists (side by side)
        if semifinalists and len(semifinalists) >= 2:
            semi_y = y_offset + 340
            self._draw_result_card(semifinalists[0], self.width // 2, semi_y, 3, compact=True)
            if len(semifinalists) > 1:
                self._draw_result_card(semifinalists[1], self.width // 2, semi_y + 100, 4, compact=True)

    def _draw_result_card(self, fighter, x: int, y: int, placement: int, is_champion: bool = False, compact: bool = False):
        """
        Draw a clean result card for tournament finisher

        Args:
            fighter: Fighter instance
            x, y: Center position
            placement: Placement number (1, 2, 3, 4)
            is_champion: True for 1st place (larger, gold themed)
            compact: True for 3rd/4th (smaller cards)
        """
        # Placement colors and styling
        colors = {
            1: (255, 215, 0),    # Gold
            2: (192, 192, 192),  # Silver
            3: (205, 127, 50),   # Bronze
            4: (150, 120, 90),   # Dark Bronze
        }
        placement_label = {1: "1ST", 2: "2ND", 3: "3RD", 4: "4TH"}

        color = colors.get(placement, (150, 150, 150))

        # Card dimensions
        if is_champion:
            card_width = 460
            card_height = 140
            avatar_size = 100
        elif compact:
            card_width = 460
            card_height = 70
            avatar_size = 50
        else:
            card_width = 460
            card_height = 100
            avatar_size = 70

        # Card background
        card_x = x - card_width // 2
        card_y = y - card_height // 2

        # Background with subtle gradient effect
        bg_color = (45, 45, 50) if not is_champion else (55, 50, 40)
        pygame.draw.rect(self.screen, bg_color, (card_x, card_y, card_width, card_height), border_radius=8)

        # Border
        border_color = color if is_champion else (70, 70, 75)
        border_width = 3 if is_champion else 2
        pygame.draw.rect(self.screen, border_color, (card_x, card_y, card_width, card_height), border_width, border_radius=8)

        # Left section: Placement
        placement_x = card_x + 50

        # Placement label (ASCII)
        if not compact:
            label_text = self.font_small.render(placement_label.get(placement, ""), True, color)
            label_rect = label_text.get_rect(center=(placement_x, y - 18))
            self.screen.blit(label_text, label_rect)

        place_text = self.font_title.render(f"{placement}", True, color) if is_champion else self.font_large.render(f"{placement}", True, color)
        place_rect = place_text.get_rect(center=(placement_x, y + 15 if not compact else y))
        self.screen.blit(place_text, place_rect)

        # Middle section: Avatar
        avatar_x = card_x + 140 if not compact else card_x + 120

        if hasattr(fighter, 'avatar_surface') and fighter.avatar_surface:
            try:
                scaled_avatar = pygame.transform.smoothscale(fighter.avatar_surface, (avatar_size, avatar_size))
                avatar_rect = scaled_avatar.get_rect(center=(avatar_x, y))
                self.screen.blit(scaled_avatar, avatar_rect)

                # Avatar border
                pygame.draw.circle(self.screen, color, (avatar_x, y), avatar_size // 2 + 2, 2)
            except:
                # Fallback circle
                pygame.draw.circle(self.screen, fighter.color if hasattr(fighter, 'color') else (100, 100, 255),
                                 (avatar_x, y), avatar_size // 2)
                draw_avatar_initials(
                    self.screen,
                    fighter.username if hasattr(fighter, "username") else "",
                    center=(avatar_x, y),
                    diameter=avatar_size,
                )
                pygame.draw.circle(self.screen, color, (avatar_x, y), avatar_size // 2 + 2, 2)
        else:
            # Fallback circle
            pygame.draw.circle(self.screen, fighter.color if hasattr(fighter, 'color') else (100, 100, 255),
                             (avatar_x, y), avatar_size // 2)
            draw_avatar_initials(
                self.screen,
                fighter.username if hasattr(fighter, "username") else "",
                center=(avatar_x, y),
                diameter=avatar_size,
            )
            pygame.draw.circle(self.screen, color, (avatar_x, y), avatar_size // 2 + 2, 2)

        # Right section: Name and title
        name_x = card_x + 220 if not compact else card_x + 180

        # Champion title for 1st place
        if is_champion:
            crown_text = self.font_medium.render("CHAMPION", True, color)
            crown_rect = crown_text.get_rect(left=name_x, centery=y - 25)
            self.screen.blit(crown_text, crown_rect)

        # Username
        font_size = self.font_medium if is_champion else (self.font_small if not compact else self.font_tiny)
        username_text = font_size.render(fighter.username[:20], True, (255, 255, 255))
        username_rect = username_text.get_rect(left=name_x, centery=y + 10 if is_champion else y)
        self.screen.blit(username_text, username_rect)

    def render_tournament_bracket(
        self,
        bracket: List[List],
        current_round: int,
        current_match: int,
        highlight_matchup: Tuple,
        tournament_type: str = "TOURNAMENT",
        monthly_rankings: dict = None
    ):
        """
        Render full tournament bracket visualization with clean, readable design

        Args:
            bracket: Tournament bracket (list of rounds, each round is list of fighters)
            current_round: Current round index (0 = Round of 16)
            current_match: Current match index within the round
            highlight_matchup: Tuple of (fighter1, fighter2) to highlight
            tournament_type: Tournament title (e.g., "DECEMBER 2025")
            monthly_rankings: Dict mapping username to rank (1-16)
        """
        # Clear screen
        self.screen.fill(self.bg_color)

        # Header - Tournament title
        title = self.font_medium.render("TOURNAMENT BRACKET", True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.width // 2, 20))
        self.screen.blit(title, title_rect)

        # Subtitle - Month/Year
        subtitle = self.font_tiny.render(tournament_type, True, (150, 150, 160))
        subtitle_rect = subtitle.get_rect(center=(self.width // 2, 42))
        self.screen.blit(subtitle, subtitle_rect)

        if not bracket or len(bracket) == 0 or len(bracket[0]) == 0:
            return

        # Get all fighters from first round
        round_of_16 = bracket[0]
        if len(round_of_16) != 16:
            text = self.font_small.render(f"{len(round_of_16)} Fighter Tournament", True, (255, 255, 255))
            rect = text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(text, rect)
            return

        # Colors
        white = (255, 255, 255)
        gold = (255, 215, 0)
        gray = (80, 80, 90)
        dark_gray = (40, 40, 45)

        # Track which fighters are still alive (in current and later rounds)
        alive_fighters = set()
        for round_idx in range(current_round + 1):
            if round_idx < len(bracket):
                for fighter in bracket[round_idx]:
                    alive_fighters.add(fighter.username if hasattr(fighter, 'username') else str(fighter))

        # Traditional tournament bracket tree with connecting lines
        y_start = 75
        spacing_unit = 46  # Base spacing between adjacent fighters
        item_width = 95    # Narrower boxes to fit all columns on 540px screen
        item_height = 20
        connector_len = 15  # Shorter connectors

        # Column X positions for each round (total width ~530px)
        col_r16 = 8
        col_qf = col_r16 + item_width + connector_len + 8
        col_sf = col_qf + item_width + connector_len + 8
        col_final = col_sf + item_width + connector_len + 8

        # Round labels at top
        round_labels_info = [
            ("R16", col_r16 + item_width // 2),
            ("QF", col_qf + item_width // 2),
            ("SF", col_sf + item_width // 2),
            ("FINAL", col_final + item_width // 2)
        ]
        for label_text, x_center in round_labels_info:
            label_surf = self.font_tiny.render(label_text, True, gray)
            label_rect = label_surf.get_rect(centerx=x_center, y=60)
            self.screen.blit(label_surf, label_rect)

        # Draw Round of 16 with proper bracket tree connections
        for matchup_idx in range(8):
            y1 = y_start + matchup_idx * spacing_unit * 2
            y2 = y1 + spacing_unit

            f1 = round_of_16[matchup_idx * 2]
            f2 = round_of_16[matchup_idx * 2 + 1]

            f1_alive = f1.username in alive_fighters if hasattr(f1, 'username') else False
            f2_alive = f2.username in alive_fighters if hasattr(f2, 'username') else False
            f1_highlight = highlight_matchup and f1 in highlight_matchup
            f2_highlight = highlight_matchup and f2 in highlight_matchup

            # Draw fighter name boxes
            self._draw_bracket_fighter_compact(
                f1, col_r16, y1, item_width, item_height,
                is_highlighted=f1_highlight,
                is_eliminated=not f1_alive,
                rank=monthly_rankings.get(f1.username) if monthly_rankings and hasattr(f1, 'username') else None
            )
            self._draw_bracket_fighter_compact(
                f2, col_r16, y2, item_width, item_height,
                is_highlighted=f2_highlight,
                is_eliminated=not f2_alive,
                rank=monthly_rankings.get(f2.username) if monthly_rankings and hasattr(f2, 'username') else None
            )

            # Connecting lines to next round
            line_color = gold if (f1_highlight or f2_highlight) else (white if (f1_alive or f2_alive) else dark_gray)

            # Horizontal lines from each fighter to merge point
            x_merge = col_r16 + item_width + connector_len
            pygame.draw.line(self.screen, line_color if f1_alive else dark_gray,
                           (col_r16 + item_width, y1 + item_height // 2),
                           (x_merge, y1 + item_height // 2), 2)
            pygame.draw.line(self.screen, line_color if f2_alive else dark_gray,
                           (col_r16 + item_width, y2 + item_height // 2),
                           (x_merge, y2 + item_height // 2), 2)

            # Vertical line connecting the two fighters
            pygame.draw.line(self.screen, line_color,
                           (x_merge, y1 + item_height // 2),
                           (x_merge, y2 + item_height // 2), 2)

        # Draw Quarterfinals (8 winners -> 4 matches)
        if len(bracket) > 1 and len(bracket[1]) > 0:
            for qf_idx in range(min(8, len(bracket[1]))):
                # Position QF fighters centered between their R16 matchup positions
                # qf_idx represents which R16 matchup they won (0-7)
                y_qf = y_start + qf_idx * spacing_unit * 2 + spacing_unit // 2
                qf_fighter = bracket[1][qf_idx]
                qf_highlight = highlight_matchup and qf_fighter in highlight_matchup

                self._draw_bracket_fighter_compact(
                    qf_fighter, col_qf, y_qf, item_width, item_height,
                    is_highlighted=qf_highlight,
                    is_eliminated=False,
                    rank=None
                )

                # Line to semifinals (only for winners, every other fighter)
                if current_round >= 2 and qf_idx % 2 == 0:
                    line_color = gold if qf_highlight else white
                    pygame.draw.line(self.screen, line_color,
                                   (col_qf + item_width, y_qf + item_height // 2),
                                   (col_qf + item_width + connector_len, y_qf + item_height // 2), 2)

        # Draw Semifinals (4 winners -> 2 matches)
        # SF fighter 0 = winner of QF 0vs1, SF fighter 1 = winner of QF 2vs3
        # SF fighter 2 = winner of QF 4vs5, SF fighter 3 = winner of QF 6vs7
        # SF Match 1: SF fighters 0 vs 1 (top half)
        # SF Match 2: SF fighters 2 vs 3 (bottom half)
        sf_positions = []  # Store Y positions for connector lines
        if len(bracket) > 2 and len(bracket[2]) > 0:
            for sf_idx in range(min(4, len(bracket[2]))):
                # Each SF fighter comes from a QF match (pairs of 2 QF fighters)
                # SF idx 0 -> QF match 0 (QF 0,1) -> center between QF positions 0 and 1
                # SF idx 1 -> QF match 1 (QF 2,3) -> center between QF positions 2 and 3
                # etc.
                qf_match_idx = sf_idx  # SF fighter index = their source QF match index
                qf_first = qf_match_idx * 2  # First QF fighter in that match

                # QF positions
                y_qf1 = y_start + qf_first * spacing_unit * 2 + spacing_unit // 2
                y_qf2 = y_start + (qf_first + 1) * spacing_unit * 2 + spacing_unit // 2

                # SF fighter positioned at center of their source QF match
                y_sf = (y_qf1 + y_qf2) // 2

                sf_positions.append(y_sf)
                sf_fighter = bracket[2][sf_idx]
                sf_highlight = highlight_matchup and sf_fighter in highlight_matchup

                self._draw_bracket_fighter_compact(
                    sf_fighter, col_sf, y_sf, item_width, item_height,
                    is_highlighted=sf_highlight,
                    is_eliminated=False,
                    rank=None
                )

        # Connect QF pairs to SF (vertical merge lines from QF, horizontal to SF)
        if len(bracket) > 2 and len(sf_positions) > 0:
            x_qf_merge = col_qf + item_width + connector_len
            for sf_idx in range(len(sf_positions)):
                qf_first = sf_idx * 2

                # QF pair positions
                y_qf1 = y_start + qf_first * spacing_unit * 2 + spacing_unit // 2
                y_qf2 = y_start + (qf_first + 1) * spacing_unit * 2 + spacing_unit // 2

                # Vertical line connecting QF pair
                pygame.draw.line(self.screen, white,
                               (x_qf_merge, y_qf1 + item_height // 2),
                               (x_qf_merge, y_qf2 + item_height // 2), 2)

                # Horizontal line from QF merge point to SF fighter
                y_sf = sf_positions[sf_idx]
                y_merge = (y_qf1 + y_qf2) // 2 + item_height // 2
                pygame.draw.line(self.screen, white,
                               (x_qf_merge, y_merge),
                               (col_sf, y_sf + item_height // 2), 2)

        # Connect SF pairs to Finals
        y_sf1_center = None
        y_sf2_center = None
        if len(bracket) > 3 and len(sf_positions) >= 2:
            x_sf_merge = col_sf + item_width + connector_len

            # SF Match 1: fighters 0 and 1
            if len(sf_positions) >= 2:
                y_sf_m1_top = sf_positions[0] + item_height // 2
                y_sf_m1_bot = sf_positions[1] + item_height // 2
                y_sf1_center = (y_sf_m1_top + y_sf_m1_bot) // 2

                # Vertical line connecting SF match 1 pair
                pygame.draw.line(self.screen, white,
                               (x_sf_merge, y_sf_m1_top),
                               (x_sf_merge, y_sf_m1_bot), 2)

            # SF Match 2: fighters 2 and 3
            if len(sf_positions) >= 4:
                y_sf_m2_top = sf_positions[2] + item_height // 2
                y_sf_m2_bot = sf_positions[3] + item_height // 2
                y_sf2_center = (y_sf_m2_top + y_sf_m2_bot) // 2

                # Vertical line connecting SF match 2 pair
                pygame.draw.line(self.screen, white,
                               (x_sf_merge, y_sf_m2_top),
                               (x_sf_merge, y_sf_m2_bot), 2)

                # Horizontal lines from SF merge to Finals column
                pygame.draw.line(self.screen, white,
                               (x_sf_merge, y_sf1_center),
                               (col_final, y_sf1_center), 2)
                pygame.draw.line(self.screen, white,
                               (x_sf_merge, y_sf2_center),
                               (col_final, y_sf2_center), 2)

                # Vertical line at Finals column connecting the two SF winners
                pygame.draw.line(self.screen, white,
                               (col_final, y_sf1_center),
                               (col_final, y_sf2_center), 2)

        # Draw Finals (finalists or champion)
        if len(bracket) > 3 and len(sf_positions) >= 2:
            finals_fighters = bracket[3]
            champion = None
            if len(bracket) > 4 and len(bracket[4]) >= 1:
                champion = bracket[4][0]

            if champion is None:
                if y_sf1_center is not None and len(finals_fighters) >= 1:
                    finalist = finals_fighters[0]
                    finalist_highlight = highlight_matchup and finalist in highlight_matchup
                    self._draw_bracket_fighter_compact(
                        finalist,
                        col_final,
                        y_sf1_center - item_height // 2,
                        item_width,
                        item_height,
                        is_highlighted=finalist_highlight,
                        is_eliminated=False,
                        rank=None
                    )
                if y_sf2_center is not None and len(finals_fighters) >= 2:
                    finalist = finals_fighters[1]
                    finalist_highlight = highlight_matchup and finalist in highlight_matchup
                    self._draw_bracket_fighter_compact(
                        finalist,
                        col_final,
                        y_sf2_center - item_height // 2,
                        item_width,
                        item_height,
                        is_highlighted=finalist_highlight,
                        is_eliminated=False,
                        rank=None
                    )
            elif y_sf1_center is not None and y_sf2_center is not None:
                y_final = (y_sf1_center + y_sf2_center) // 2 - item_height // 2
                champ_highlight = highlight_matchup and champion in highlight_matchup
                self._draw_bracket_fighter_compact(
                    champion, col_final, y_final, item_width, item_height,
                    is_highlighted=champ_highlight,
                    is_eliminated=False,
                    rank=None,
                    is_champion=True
                )

        # Footer - Next match info
        if highlight_matchup and len(highlight_matchup) == 2:
            fighter1, fighter2 = highlight_matchup
            next_text = f"NEXT: {fighter1.username} vs {fighter2.username}"
            text = self.font_small.render(next_text, True, gold)
            rect = text.get_rect(center=(self.width // 2, self.height - 50))
            self.screen.blit(text, rect)

            starting_text = "Starting in 2s..."
            text2 = self.font_tiny.render(starting_text, True, (180, 180, 190))
            rect2 = text2.get_rect(center=(self.width // 2, self.height - 25))
            self.screen.blit(text2, rect2)

    def _draw_bracket_fighter_box(
        self,
        fighter,
        x: int,
        y: int,
        size: int,
        is_highlighted: bool = False,
        is_eliminated: bool = False,
        rank: int = None
    ):
        """
        Draw a single fighter box in the bracket

        Args:
            fighter: Fighter instance
            x, y: Top-left position
            size: Box size (width and height)
            is_highlighted: Whether this fighter is in the current match
            is_eliminated: Whether this fighter has been eliminated
            rank: Optional rank number to display (1-16)
        """
        # Border color
        if is_highlighted:
            border_color = (255, 215, 0)  # Gold
            border_width = 3
        elif is_eliminated:
            border_color = (80, 80, 80)  # Dark gray
            border_width = 2
        else:
            border_color = (255, 255, 255)  # White
            border_width = 2

        # Draw avatar if available
        if hasattr(fighter, 'avatar_surface') and fighter.avatar_surface:
            try:
                scaled_avatar = pygame.transform.smoothscale(fighter.avatar_surface, (size, size))
                self.screen.blit(scaled_avatar, (x, y))
            except:
                # Fallback: draw colored circle
                pygame.draw.circle(self.screen, fighter.color if hasattr(fighter, 'color') else (100, 100, 255),
                                 (x + size // 2, y + size // 2), size // 2 - 2)
                draw_avatar_initials(
                    self.screen,
                    fighter.username if hasattr(fighter, "username") else "",
                    center=(x + size // 2, y + size // 2),
                    diameter=size,
                )
        else:
            # No avatar: draw colored circle
            pygame.draw.circle(self.screen, fighter.color if hasattr(fighter, 'color') else (100, 100, 255),
                             (x + size // 2, y + size // 2), size // 2 - 2)
            draw_avatar_initials(
                self.screen,
                fighter.username if hasattr(fighter, "username") else "",
                center=(x + size // 2, y + size // 2),
                diameter=size,
            )

        # Border
        pygame.draw.rect(self.screen, border_color, (x, y, size, size), border_width, border_radius=4)

        # Rank overlay (small number in top-left corner)
        if rank is not None and size >= 30:
            rank_text = self.font_tiny.render(f"#{rank}", True, (255, 255, 255))
            rank_bg = pygame.Surface((20, 14))
            rank_bg.fill((0, 0, 0))
            rank_bg.set_alpha(180)
            self.screen.blit(rank_bg, (x + 2, y + 2))
            self.screen.blit(rank_text, (x + 3, y + 2))

    def _draw_bracket_fighter_compact(
        self, fighter, x: int, y: int, width: int, height: int,
        is_highlighted: bool = False,
        is_eliminated: bool = False,
        rank: int = None,
        is_champion: bool = False
    ):
        """Draw a compact fighter name box for tournament bracket tree"""
        gold = (255, 215, 0)
        white = (255, 255, 255)
        dark_gray = (50, 50, 55)

        # Background
        bg_color = dark_gray if is_eliminated else ((40, 40, 45) if not is_highlighted else (55, 50, 40))
        pygame.draw.rect(self.screen, bg_color, (x, y, width, height), border_radius=3)

        # Border
        border_color = gold if is_highlighted else ((100, 100, 110) if not is_eliminated else (60, 60, 65))
        border_width = 2 if is_highlighted else 1
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), border_width, border_radius=3)

        # Champion marker
        if is_champion:
            marker = self.font_small.render("C", True, gold)
            self.screen.blit(marker, (x - 12, y + 2))

        # Text content
        text_x = x + 3
        text_color = white if not is_eliminated else (100, 100, 110)

        # Rank number (if provided)
        if rank is not None:
            rank_color = gold if rank <= 3 else white
            rank_text = self.font_tiny.render(f"#{rank}", True, rank_color)
            self.screen.blit(rank_text, (text_x, y + 4))
            text_x += 20

        # Fighter name (truncate to fit narrower boxes)
        name = fighter.username[:8] if hasattr(fighter, 'username') else "???"
        name_surf = self.font_tiny.render(name, True, text_color)
        self.screen.blit(name_surf, (text_x, y + 4))

    def _draw_bracket_list_item(
        self, fighter, x: int, y: int,
        is_highlighted: bool = False,
        is_eliminated: bool = False,
        rank: int = None,
        show_connector_right: bool = False,
        is_champion: bool = False
    ):
        """Draw a fighter as a clean list item with avatar, rank, and name"""
        # Colors
        gold = (255, 215, 0)
        white = (255, 255, 255)
        gray = (100, 100, 110)
        dark_gray = (50, 50, 55)

        # Dimensions
        item_width = 130
        item_height = 22
        avatar_size = 18

        # Background rectangle
        bg_color = dark_gray if is_eliminated else ((45, 45, 50) if not is_highlighted else (60, 50, 40))
        pygame.draw.rect(self.screen, bg_color, (x, y, item_width, item_height), border_radius=3)

        # Border
        border_color = gold if is_highlighted else (gray if not is_eliminated else (60, 60, 65))
        border_width = 2 if is_highlighted else 1
        pygame.draw.rect(self.screen, border_color, (x, y, item_width, item_height), border_width, border_radius=3)

        # Champion marker
        if is_champion:
            marker = self.font_small.render("C", True, gold)
            self.screen.blit(marker, (x - 15, y + 2))

        # Rank number (if provided)
        if rank is not None:
            rank_text = self.font_tiny.render(f"#{rank}", True, gold if rank <= 3 else white)
            self.screen.blit(rank_text, (x + 3, y + 5))
            text_x_offset = 25
        else:
            text_x_offset = 5

        # Avatar (small circle or image)
        avatar_x = x + text_x_offset
        if hasattr(fighter, 'avatar_surface') and fighter.avatar_surface:
            try:
                scaled_avatar = pygame.transform.smoothscale(fighter.avatar_surface, (avatar_size, avatar_size))
                self.screen.blit(scaled_avatar, (avatar_x, y + 2))
            except:
                # Fallback to colored circle
                pygame.draw.circle(self.screen, fighter.color if hasattr(fighter, 'color') else white,
                                 (avatar_x + avatar_size // 2, y + item_height // 2), avatar_size // 2)
                draw_avatar_initials(
                    self.screen,
                    fighter.username if hasattr(fighter, "username") else "",
                    center=(avatar_x + avatar_size // 2, y + item_height // 2),
                    diameter=avatar_size,
                )
        else:
            # Colored circle fallback
            pygame.draw.circle(self.screen, fighter.color if hasattr(fighter, 'color') else white,
                             (avatar_x + avatar_size // 2, y + item_height // 2), avatar_size // 2)
            draw_avatar_initials(
                self.screen,
                fighter.username if hasattr(fighter, "username") else "",
                center=(avatar_x + avatar_size // 2, y + item_height // 2),
                diameter=avatar_size,
            )

        # Fighter name
        name = fighter.username[:10] if hasattr(fighter, 'username') else "Unknown"
        name_color = white if not is_eliminated else (100, 100, 110)
        name_surf = self.font_tiny.render(name, True, name_color)
        self.screen.blit(name_surf, (avatar_x + avatar_size + 4, y + 5))

        # Connector line to next round
        if show_connector_right:
            line_color = gold if is_highlighted else white
            pygame.draw.line(self.screen, line_color,
                           (x + item_width, y + item_height // 2),
                           (x + item_width + 8, y + item_height // 2), 1)
