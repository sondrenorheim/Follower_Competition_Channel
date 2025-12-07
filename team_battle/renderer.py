"""
Team Battle Renderer Module
Handles rendering for Team Battle game mode with team colors and walls
"""

import pygame
import math
import os
import time
from typing import List, Dict, Optional
from PIL import Image

import config
from .team_fighter import TeamFighter, Team, TEAM_COLORS
from .team_arena import TeamArena


class TeamBattleRenderer:
    """
    Handles all rendering for Team Battle game mode.
    Includes team-colored rings, walls, and phase announcements.
    """

    def __init__(self, screen: pygame.Surface, arena: TeamArena):
        """
        Initialize the renderer

        Args:
            screen: Pygame display surface
            arena: TeamArena instance for wall state
        """
        self.screen = screen
        self.arena = arena
        self.width = config.SCREEN_WIDTH
        self.height = config.SCREEN_HEIGHT

        # Initialize fonts
        pygame.font.init()
        self.font_small = pygame.font.Font(None, config.FOLLOWER_NAME_FONT_SIZE)
        self.font_medium = pygame.font.Font(None, config.SCOREBOARD_FONT_SIZE)
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 72)
        self.font_phase = pygame.font.Font(None, 56)

        # Cache for fighter surfaces
        self.fighter_surfaces = {}

        # Animation state
        self.show_podium = False
        self.podium_animation_progress = 0
        self.game_state = None

        # Phase announcement
        self.phase_announcement = None
        self.phase_announcement_text = None
        self.phase_announcement_start = None
        self.phase_announcement_duration = 2.0

        # Team labels display at start
        self.show_team_labels = True
        self.team_labels_start = None
        self.team_labels_duration = 2.5

        # Countdown video overlay
        self.countdown_video_frames = []
        self.countdown_video_fps = 30
        self.countdown_video_loaded = False
        self.countdown_start_time = None
        self._load_countdown_video()

    def render_frame(self, fighters: List[TeamFighter], arena: TeamArena,
                    game_state: dict, particle_system=None):
        """
        Render complete frame

        Args:
            fighters: List of all fighters
            arena: TeamArena object
            game_state: Game state dictionary
            particle_system: Optional ParticleSystem
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw arena with quadrants and walls
        self._draw_arena(arena, game_state)

        # Draw fighters with team rings
        self._draw_fighters(fighters)

        # Draw particles
        if particle_system:
            particle_system.render(self.screen)

        # Draw UI
        self._draw_scoreboard(fighters, game_state)

        # Draw team status
        self._draw_team_status(game_state)

        # Draw intro overlay if in intro phase
        if game_state.get("phase") == "intro":
            self._draw_intro(game_state.get("day_number", 1))
            # Draw team labels during intro
            self._draw_team_labels_overlay(arena)
            return

        # Draw countdown if in any countdown phase
        phase = game_state.get("phase", "")
        if phase in ("countdown", "finals_countdown", "freeforall_countdown"):
            self._draw_countdown(game_state.get("countdown_number", 3))
            return

        # Draw matchup announcement phases
        if phase in ("matchup_announce", "finals_announce", "freeforall_announce"):
            self._draw_matchup_announcement(game_state)
            return

        # Draw phase announcements for active combat phases
        if self.phase_announcement:
            self._draw_phase_announcement()

        # Draw podium if game is over
        if game_state.get("game_over", False) and not self.show_podium:
            self.show_podium = True
            self.podium_animation_progress = 0
            self.game_state = game_state

        if self.show_podium:
            self._draw_podium(game_state)

    def _draw_arena(self, arena: TeamArena, game_state: dict):
        """Draw the arena with quadrants and walls"""
        rect = arena.get_rect()

        # Draw quadrant backgrounds with subtle team tints
        for team in Team:
            qx, qy, qw, qh = arena.get_quadrant_bounds(team)
            team_color = TEAM_COLORS[team]

            # Create subtle tint (blend with arena color)
            tint_strength = 0.15
            base_color = config.COLOR_FIGHTER_ARENA
            tinted = tuple(
                int(base_color[i] * (1 - tint_strength) + team_color[i] * tint_strength)
                for i in range(3)
            )

            pygame.draw.rect(self.screen, tinted, (qx, qy, qw, qh))

        # Draw arena border
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 3)

        # Draw walls with animation
        wall_color = (60, 60, 60)
        wall_thickness = arena.wall_thickness

        # Vertical wall (center, left-right division) - shrinks from top and bottom
        if arena.vertical_wall_closed or arena.vertical_wall_open_progress < 1.0:
            wall_height = int(arena.height * (1.0 - arena.vertical_wall_open_progress))
            if wall_height > 0:
                wall_y = arena.center_y - wall_height // 2
                pygame.draw.rect(
                    self.screen,
                    wall_color,
                    (arena.center_x - wall_thickness // 2, wall_y,
                     wall_thickness, wall_height)
                )

        # Horizontal wall (center, top-bottom division) - shrinks from left and right
        if arena.horizontal_wall_closed or arena.horizontal_wall_open_progress < 1.0:
            wall_width = int(arena.width * (1.0 - arena.horizontal_wall_open_progress))
            if wall_width > 0:
                wall_x = arena.center_x - wall_width // 2
                pygame.draw.rect(
                    self.screen,
                    wall_color,
                    (wall_x, arena.center_y - wall_thickness // 2,
                     wall_width, wall_thickness)
                )

    def _draw_fighters(self, fighters: List[TeamFighter]):
        """Draw all fighters with team-colored rings"""
        for fighter in fighters:
            if not fighter.alive and not fighter.is_fading():
                continue

            # Get or create fighter surface
            surface = self._get_fighter_surface(fighter)

            # Apply alpha for fade out
            if fighter.alpha < 255:
                surface = surface.copy()
                surface.set_alpha(fighter.alpha)

            # Draw fighter
            pos = fighter.get_position()
            display_size = int(config.FOLLOWER_RADIUS * 2)

            if surface.get_width() != display_size:
                display_surface = pygame.transform.smoothscale(surface, (display_size, display_size))
            else:
                display_surface = surface

            rect = display_surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(display_surface, rect)

            # Draw HP bar - DISABLED
            # if fighter.alive or fighter.is_fading():
            #     self._draw_hp_bar(fighter)

    def _get_fighter_surface(self, fighter: TeamFighter) -> pygame.Surface:
        """Get or create cached surface with team-colored ring"""
        # Use cache key that includes team to ensure correct team colors
        cache_key = f"{fighter.id}_{fighter.team.value}"

        if cache_key in self.fighter_surfaces and not fighter.surface_needs_update:
            return self.fighter_surfaces[cache_key]

        # Create new surface
        size = int(config.FOLLOWER_RADIUS * 2)
        radius = int(config.FOLLOWER_RADIUS)

        # Upscale for quality
        upscale_multiplier = config.UPSCALE_FACTOR if config.UPSCALE_VIDEO else 1.0
        render_size = int(size * upscale_multiplier)
        render_radius = int(radius * upscale_multiplier)

        surface = pygame.Surface((render_size, render_size), pygame.SRCALPHA)

        # Team ring thickness (outer ring) - made thinner
        team_ring_thickness = int(1.5 * upscale_multiplier)
        inner_radius = render_radius - team_ring_thickness

        # Draw team color ring (outer)
        pygame.draw.circle(
            surface,
            fighter.team_color,
            (render_radius, render_radius),
            render_radius
        )

        # Draw avatar or colored circle (inner)
        if fighter.avatar_image:
            avatar_surface = self._pil_to_pygame(fighter.avatar_image, int(inner_radius * 2))
            if avatar_surface:
                self._draw_circular_image(surface, avatar_surface, inner_radius, render_radius)
            else:
                # Avatar had invalid dimensions, use colored circle fallback
                pygame.draw.circle(
                    surface,
                    fighter.team_color,
                    (render_radius, render_radius),
                    inner_radius
                )
        else:
            # Always use team_color for inner circle to ensure consistent team appearance
            pygame.draw.circle(
                surface,
                fighter.team_color,
                (render_radius, render_radius),
                inner_radius
            )

        # Cache
        self.fighter_surfaces[cache_key] = surface
        fighter.surface_needs_update = False

        return surface

    def _draw_circular_image(self, surface: pygame.Surface,
                           image_surface: pygame.Surface,
                           inner_radius: int, center: int):
        """Draw an image clipped to a circle at the center"""
        size = inner_radius * 2
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (inner_radius, inner_radius),
                         inner_radius - config.FOLLOWER_BORDER_WIDTH)

        scaled_image = pygame.transform.scale(image_surface, (size, size))
        scaled_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Center the image
        offset = center - inner_radius
        surface.blit(scaled_image, (offset, offset))

    def _draw_hp_bar(self, fighter: TeamFighter):
        """Draw HP bar above fighter"""
        pos = fighter.get_position()
        hp_pct = fighter.get_hp_percentage()

        bar_width = config.FIGHTER_HP_BAR_WIDTH
        bar_height = config.FIGHTER_HP_BAR_HEIGHT
        bar_x = int(pos[0] - bar_width // 2)
        bar_y = int(pos[1] - config.FOLLOWER_RADIUS - 8)

        # Background
        pygame.draw.rect(self.screen, config.COLOR_HP_BAR_BG,
                        (bar_x, bar_y, bar_width, bar_height))

        # HP color
        if hp_pct > 0.6:
            hp_color = config.COLOR_HP_BAR_FULL
        elif hp_pct > 0.3:
            hp_color = config.COLOR_HP_BAR_MID
        else:
            hp_color = config.COLOR_HP_BAR_LOW

        # HP fill
        fill_width = int(bar_width * hp_pct)
        if fill_width > 0:
            pygame.draw.rect(self.screen, hp_color,
                           (bar_x, bar_y, fill_width, bar_height))

        # Border
        pygame.draw.rect(self.screen, (0, 0, 0),
                        (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_scoreboard(self, fighters: List[TeamFighter], game_state: dict):
        """Draw title and stats"""
        arena_rect = config.FIGHTER_ARENA_RECT
        arena_top = arena_rect[1]
        arena_bottom = arena_rect[1] + arena_rect[3]

        # Title
        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render("TEAM BATTLE", True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 50))
        self.screen.blit(title_text, title_rect)

        # Subtitle
        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render("Making my followers battle every day", True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 20))
        self.screen.blit(subtitle_text, subtitle_rect)

        # Day and stats below arena (no background)
        day_number = game_state.get("day_number", getattr(config, 'DAY_NUMBER', 1))
        day_font = pygame.font.Font(None, 36)
        day_text = day_font.render(f"Day {day_number}: {len(fighters)} fighters", True, config.COLOR_TEXT)
        day_rect = day_text.get_rect(center=(self.width // 2, arena_bottom + 25))
        self.screen.blit(day_text, day_rect)

    def _draw_team_status(self, game_state: dict):
        """Draw team alive counts and average HP with background"""
        team_counts = game_state.get("team_counts", {})
        eliminated_teams = game_state.get("eliminated_teams", [])
        all_followers = game_state.get("all_followers", [])
        phase = game_state.get("phase", "")

        arena_rect = config.FIGHTER_ARENA_RECT
        arena_bottom = arena_rect[1] + arena_rect[3]

        status_y = arena_bottom + 55
        status_font = pygame.font.Font(None, 24)
        hp_font = pygame.font.Font(None, 18)

        # Render all team texts first to calculate total width
        teams = [Team.RED, Team.BLUE, Team.GREEN, Team.YELLOW]
        team_surfaces = []

        for team in teams:
            count = team_counts.get(team, 0)
            color = TEAM_COLORS[team] if team not in eliminated_teams else (100, 100, 100)
            text = f"{team.value.upper()}: {count}"
            text_surface = status_font.render(text, True, color)
            team_surfaces.append(text_surface)

        # Calculate spacing and total width
        spacing = 30  # Space between team texts
        total_text_width = sum(surf.get_width() for surf in team_surfaces) + spacing * (len(teams) - 1)

        # Calculate team average HP (hide during free-for-all)
        show_hp = phase not in ("freeforall", "freeforall_announce", "freeforall_countdown")
        box_height = 50 if show_hp else 28  # Taller box if showing HP

        # Draw background box for entire team status row
        padding = 15
        total_width = total_text_width + padding * 2
        box_x = (self.width - total_width) // 2
        box_y = status_y - (28 // 2)  # Align to original position

        status_bg = pygame.Surface((total_width, box_height), pygame.SRCALPHA)
        status_bg.fill((0, 0, 0, 180))
        self.screen.blit(status_bg, (box_x, box_y))

        # Draw each team's count
        current_x = box_x + padding
        for i, team in enumerate(teams):
            text_surface = team_surfaces[i]
            text_rect = text_surface.get_rect(left=current_x, centery=status_y)
            self.screen.blit(text_surface, text_rect)

            # Draw average HP below count (if not free-for-all)
            if show_hp:
                # Calculate team average HP
                team_fighters = [f for f in all_followers if hasattr(f, 'team') and f.team == team]
                if team_fighters:
                    total_hp = sum(f.current_hp for f in team_fighters)
                    max_possible_hp = sum(f.max_hp for f in team_fighters)
                    avg_hp_pct = (total_hp / max_possible_hp * 100) if max_possible_hp > 0 else 0

                    color = TEAM_COLORS[team] if team not in eliminated_teams else (100, 100, 100)
                    hp_text = f"{avg_hp_pct:.0f}%"
                    hp_surface = hp_font.render(hp_text, True, color)
                    hp_rect = hp_surface.get_rect(left=current_x, centery=status_y + 18)
                    self.screen.blit(hp_surface, hp_rect)

            current_x += text_surface.get_width() + spacing

    def _draw_intro(self, day_number: int):
        """Draw intro overlay (text removed, just shows teams positioning)"""
        # No overlay or text - just let the team labels show
        pass

    def _draw_countdown(self, number: int):
        """Draw countdown - skip if exporting video (recorder handles it with greenscreen)"""
        import config

        # Don't draw countdown overlay during video export - the recorder's greenscreen handles it
        if config.EXPORT_VIDEO:
            return

        if self.countdown_video_loaded and self.countdown_start_time is not None:
            self._draw_countdown_video()
            return

        self._draw_countdown_text(number)

    def _draw_countdown_video(self):
        """Draw countdown video frame"""
        if self.countdown_start_time is None:
            return

        elapsed = time.time() - self.countdown_start_time
        frame_index = int(elapsed * self.countdown_video_fps)

        if frame_index >= len(self.countdown_video_frames):
            return

        frame = self.countdown_video_frames[frame_index]

        target_height = int(self.height * 0.3)
        scale = target_height / frame.get_height()
        new_width = int(frame.get_width() * scale)

        scaled_frame = pygame.transform.scale(frame, (new_width, target_height))

        x = (self.width - new_width) // 2
        y = (self.height - target_height) // 2

        self.screen.blit(scaled_frame, (x, y))

    def _draw_countdown_text(self, number: int):
        """Fallback text countdown"""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        pulse = abs(math.sin(pygame.time.get_ticks() / 150.0))
        scale = 1.0 + pulse * 0.2

        if number == 0:
            text = "FIGHT!"
            color = (255, 50, 50)
        else:
            text = str(number)
            color = (255, 215, 0)

        countdown_font = pygame.font.Font(None, int(200 * scale))
        countdown_text = countdown_font.render(text, True, color)
        rect = countdown_text.get_rect(center=(self.width // 2, self.height // 2))

        shadow_text = countdown_font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(self.width // 2 + 5, self.height // 2 + 5))
        self.screen.blit(shadow_text, shadow_rect)
        self.screen.blit(countdown_text, rect)

    def _draw_team_labels_overlay(self, arena: TeamArena):
        """Draw team labels with semi-transparent backgrounds in each quadrant"""
        label_font = pygame.font.Font(None, 32)

        for team in Team:
            qx, qy, qw, qh = arena.get_quadrant_bounds(team)
            team_color = TEAM_COLORS[team]

            # Create label text
            label_text = f"{team.value.upper()} TEAM"
            text_surface = label_font.render(label_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect()

            # Create background box with padding
            padding = 8
            box_width = text_rect.width + padding * 2
            box_height = text_rect.height + padding * 2

            # Position in center of quadrant
            box_x = qx + (qw - box_width) // 2
            box_y = qy + (qh - box_height) // 2

            # Draw semi-transparent background with team color tint
            box_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            # Mix team color with black for background
            bg_color = (
                team_color[0] // 3,
                team_color[1] // 3,
                team_color[2] // 3,
                200
            )
            box_surface.fill(bg_color)

            # Draw border in team color
            pygame.draw.rect(box_surface, team_color, (0, 0, box_width, box_height), 2)

            self.screen.blit(box_surface, (box_x, box_y))

            # Draw text centered in box
            text_x = box_x + padding
            text_y = box_y + padding
            self.screen.blit(text_surface, (text_x, text_y))

    def _draw_matchup_announcement(self, game_state: dict):
        """Draw matchup announcement with team-colored text"""
        phase = game_state.get("phase", "")
        arena_rect = config.FIGHTER_ARENA_RECT
        arena_top = arena_rect[1]
        arena_bottom = arena_rect[1] + arena_rect[3]
        arena_center_y = arena_top + arena_rect[3] // 2

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        matchup_font = pygame.font.Font(None, 48)
        vs_font = pygame.font.Font(None, 40)

        if phase == "matchup_announce":
            # Semifinals: Two horizontal fights
            # Top half: Red vs Blue - centered in top half of arena
            top_center_y = arena_top + arena_rect[3] // 4
            self._draw_colored_matchup(
                "RED", TEAM_COLORS[Team.RED],
                "BLUE", TEAM_COLORS[Team.BLUE],
                self.width // 2, top_center_y,
                matchup_font, vs_font
            )

            # Bottom half: Green vs Yellow - centered in bottom half of arena
            bottom_center_y = arena_top + 3 * arena_rect[3] // 4
            self._draw_colored_matchup(
                "GREEN", TEAM_COLORS[Team.GREEN],
                "YELLOW", TEAM_COLORS[Team.YELLOW],
                self.width // 2, bottom_center_y,
                matchup_font, vs_font
            )

        elif phase == "finals_announce":
            # Finals: Vertical stacked layout
            # Team 1 name above top half, Team 2 name above bottom half, "vs" in middle
            semifinal_winners = game_state.get("semifinal_winners", [])
            if len(semifinal_winners) >= 2:
                team_a = semifinal_winners[0]
                team_b = semifinal_winners[1]
            else:
                team_a, team_b = Team.RED, Team.GREEN  # Fallback

            # Team A name - centered in top half
            top_center_y = arena_top + arena_rect[3] // 4
            team_a_text = matchup_font.render(f"{team_a.value.upper()} TEAM", True, TEAM_COLORS[team_a])
            team_a_rect = team_a_text.get_rect(center=(self.width // 2, top_center_y))
            self.screen.blit(team_a_text, team_a_rect)

            # "vs" in the middle (on the horizontal wall line)
            vs_text = vs_font.render("vs", True, (255, 255, 255))
            vs_rect = vs_text.get_rect(center=(self.width // 2, arena_center_y))
            self.screen.blit(vs_text, vs_rect)

            # Team B name - centered in bottom half
            bottom_center_y = arena_top + 3 * arena_rect[3] // 4
            team_b_text = matchup_font.render(f"{team_b.value.upper()} TEAM", True, TEAM_COLORS[team_b])
            team_b_rect = team_b_text.get_rect(center=(self.width // 2, bottom_center_y))
            self.screen.blit(team_b_text, team_b_rect)

        elif phase == "freeforall_announce":
            # Last Man Standing announcement
            lms_font = pygame.font.Font(None, 56)
            lms_text = lms_font.render("LAST MAN STANDING", True, (255, 215, 0))
            lms_rect = lms_text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(lms_text, lms_rect)

    def _draw_colored_matchup(self, team1_name: str, team1_color: tuple,
                               team2_name: str, team2_color: tuple,
                               center_x: int, center_y: int,
                               team_font, vs_font):
        """Draw a matchup with team-colored names: 'RED vs BLUE'"""
        # Render each part
        team1_text = team_font.render(team1_name, True, team1_color)
        vs_text = vs_font.render(" vs ", True, (255, 255, 255))
        team2_text = team_font.render(team2_name, True, team2_color)

        # Calculate total width
        total_width = team1_text.get_width() + vs_text.get_width() + team2_text.get_width()
        start_x = center_x - total_width // 2

        # Draw each part
        team1_rect = team1_text.get_rect(left=start_x, centery=center_y)
        self.screen.blit(team1_text, team1_rect)

        vs_rect = vs_text.get_rect(left=team1_rect.right, centery=center_y)
        self.screen.blit(vs_text, vs_rect)

        team2_rect = team2_text.get_rect(left=vs_rect.right, centery=center_y)
        self.screen.blit(team2_text, team2_rect)

    def _start_phase_announcement(self, phase: str, game_state: dict):
        """Start a phase announcement"""
        self.phase_announcement = phase
        self.phase_announcement_start = time.time()

    def _draw_phase_announcement(self):
        """Draw current phase announcement"""
        if self.phase_announcement_start is None:
            return

        elapsed = time.time() - self.phase_announcement_start
        if elapsed > self.phase_announcement_duration:
            self.phase_announcement = None
            return

        # Fade in/out
        if elapsed < 0.3:
            alpha = int(255 * (elapsed / 0.3))
        elif elapsed > self.phase_announcement_duration - 0.3:
            alpha = int(255 * ((self.phase_announcement_duration - elapsed) / 0.3))
        else:
            alpha = 255

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(150 * alpha / 255)))
        self.screen.blit(overlay, (0, 0))

        # Use custom text if set
        text = self.phase_announcement_text or self.phase_announcement
        text_surface = self.font_phase.render(text, True, (255, 215, 0))
        text_surface.set_alpha(alpha)
        rect = text_surface.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(text_surface, rect)

    def set_phase_announcement(self, text: str):
        """Set a custom phase announcement text"""
        self.phase_announcement = "custom"
        self.phase_announcement_text = text
        self.phase_announcement_start = time.time()

    def _draw_podium(self, game_state: dict):
        """Draw winner podium"""
        self.podium_animation_progress += 0.02
        if self.podium_animation_progress > 1.0:
            self.podium_animation_progress = 1.0

        # Overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * self.podium_animation_progress)))
        self.screen.blit(overlay, (0, 0))

        if self.podium_animation_progress < 1.0:
            return

        # Winner title
        pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))
        title_color = (255, int(215 + pulse * 40), 0)
        title = self.font_huge.render("WINNER!", True, title_color)
        title_y = int(self.height * 0.08)
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title, title_rect)

        # Winner display
        winner = game_state.get("winner")
        if winner:
            winner_y = int(self.height * 0.22)

            # Team color spotlight
            team_color = winner.team_color
            spotlight_radius = int(80 + pulse * 20)
            for i in range(3):
                spotlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                radius = spotlight_radius + i * 25
                alpha = int(50 / (i + 1))
                pygame.draw.circle(spotlight, (*team_color, alpha),
                                 (self.width // 2, winner_y), radius)
                self.screen.blit(spotlight, (0, 0))

            # Avatar
            avatar_size = int(self.width * 0.15)
            avatar = self._get_fighter_surface(winner)
            avatar = pygame.transform.scale(avatar, (avatar_size, avatar_size))
            avatar_rect = avatar.get_rect(center=(self.width // 2, winner_y))
            self.screen.blit(avatar, avatar_rect)

            # Username
            name_text = self.font_large.render(winner.username, True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(self.width // 2, winner_y + avatar_size // 2 + 25))
            self.screen.blit(name_text, name_rect)

            # Team and stats
            team_text = self.font_medium.render(
                f"Team {winner.team.value.upper()} | Kills: {winner.kills}",
                True, winner.team_color
            )
            team_rect = team_text.get_rect(center=(self.width // 2, winner_y + avatar_size // 2 + 55))
            self.screen.blit(team_text, team_rect)

        # Leaderboards
        self._draw_leaderboards(game_state)

    def _draw_leaderboards(self, game_state: dict):
        """Draw current game leaderboard centered."""
        current_lb = game_state.get("current_game_leaderboard", [])

        if not current_lb:
            return

        start_y = int(self.height * 0.45)
        board_width = int(self.width * 0.55)
        left_x = (self.width - board_width) // 2

        self._draw_leaderboard_panel(
            "CURRENT GAME", "TOP 10",
            current_lb[:10], left_x, start_y, board_width,
            (0, 200, 255)
        )

    def _draw_leaderboard_panel(self, title_line1: str, title_line2: str,
                               leaderboard: list, x: int, y: int, width: int,
                               color: tuple):
        """Draw a single leaderboard panel"""
        if not leaderboard:
            return

        entry_height = int(self.height * 0.026)
        header_height = int(self.height * 0.047)
        panel_height = header_height + len(leaderboard) * entry_height + 20

        panel = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        self.screen.blit(panel, (x, y))

        title1_text = self.font_medium.render(title_line1, True, color)
        title1_rect = title1_text.get_rect(center=(x + width // 2, y + int(self.height * 0.013)))
        self.screen.blit(title1_text, title1_rect)

        title2_text = self.font_medium.render(title_line2, True, color)
        title2_rect = title2_text.get_rect(center=(x + width // 2, y + int(self.height * 0.029)))
        self.screen.blit(title2_text, title2_rect)

        medals = ["1.", "2.", "3."]
        entry_y = y + header_height

        for i, (username, points) in enumerate(leaderboard):
            rank_str = medals[i] if i < 3 else f"{i + 1}."
            rank_text = self.font_small.render(rank_str, True, (200, 200, 200))

            max_len = 16
            display_name = username if len(username) <= max_len else username[:max_len-2] + ".."
            name_font = pygame.font.Font(None, 14)
            name_text = name_font.render(display_name, True, (255, 255, 255))

            points_text = self.font_small.render(f"{points:.1f}", True, (0, 255, 150))

            self.screen.blit(rank_text, (x + 10, entry_y - 6))
            self.screen.blit(name_text, (x + 40, entry_y - 4))
            points_rect = points_text.get_rect(right=x + width - 10, top=entry_y - 6)
            self.screen.blit(points_text, points_rect)

            entry_y += entry_height

    def _load_countdown_video(self):
        """Load countdown video frames"""
        video_path = "assets/3 2 1 fight.mp4"
        if not os.path.exists(video_path):
            print(f"Countdown video not found: {video_path}")
            return

        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(video_path)
            self.countdown_video_fps = cap.get(cv2.CAP_PROP_FPS) or 30

            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_with_alpha = self._apply_chroma_key(frame_rgb)

                pygame_surface = pygame.image.frombuffer(
                    frame_with_alpha.tobytes(),
                    (frame_with_alpha.shape[1], frame_with_alpha.shape[0]),
                    'RGBA'
                )
                frames.append(pygame_surface)

            cap.release()
            self.countdown_video_frames = frames
            self.countdown_video_loaded = len(frames) > 0
            print(f"Loaded countdown video: {len(frames)} frames")

        except ImportError:
            print("OpenCV not installed")
        except Exception as e:
            print(f"Error loading countdown video: {e}")

    def _apply_chroma_key(self, frame_rgb, tolerance: int = 80):
        """Remove green screen"""
        import numpy as np

        alpha = np.ones((frame_rgb.shape[0], frame_rgb.shape[1]), dtype=np.uint8) * 255

        r = frame_rgb[:, :, 0].astype(np.int16)
        g = frame_rgb[:, :, 1].astype(np.int16)
        b = frame_rgb[:, :, 2].astype(np.int16)

        green_mask = (g > 100) & (g > r + 30) & (g > b + 30)
        alpha[green_mask] = 0

        return np.dstack((frame_rgb, alpha))

    def start_countdown_video(self):
        """Start countdown video playback"""
        self.countdown_start_time = time.time()
        print("Countdown video started")

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """Convert PIL image to pygame surface"""
        try:
            # Validate image exists and has valid dimensions
            if pil_image is None:
                return None
            if not hasattr(pil_image, 'width') or not hasattr(pil_image, 'height'):
                return None
            if pil_image.width == 0 or pil_image.height == 0:
                return None

            pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)
            mode = pil_image.mode
            data = pil_image.tobytes()
            surface = pygame.image.fromstring(data, pil_image.size, mode)
            return surface.convert_alpha()
        except Exception as e:
            # Any error during conversion, return None to use fallback
            return None

    def reset(self):
        """Reset renderer state"""
        self.fighter_surfaces.clear()
        self.show_podium = False
        self.podium_animation_progress = 0
        self.phase_announcement = None
        self.phase_announcement_start = None
