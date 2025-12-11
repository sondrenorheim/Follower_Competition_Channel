"""
Fighter Renderer Module
Handles rendering for Fighter Arena game mode
Includes HP bars, rectangular arena, and combat effects
"""

import pygame
import math
import os
from typing import List, Tuple, Optional
from PIL import Image
import config
from .fighter import Fighter
from .arena import FighterArena


class FighterRenderer:
    """
    Handles all rendering operations for the Fighter Arena game mode
    """

    def __init__(self, screen: pygame.Surface):
        """
        Initialize the renderer

        Args:
            screen: Pygame display surface to render to
        """
        self.screen = screen
        self.width = config.SCREEN_WIDTH
        self.height = config.SCREEN_HEIGHT

        # Initialize fonts
        pygame.font.init()
        self.font_small = pygame.font.Font(None, config.FOLLOWER_NAME_FONT_SIZE)
        self.font_medium = pygame.font.Font(None, config.SCOREBOARD_FONT_SIZE)
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 72)

        # Cache for fighter surfaces - stores (surface, radius) tuples
        self.fighter_surfaces = {}
        self.cached_radius = {}

        # Animation state
        self.show_podium = False
        self.podium_animation_progress = 0
        self.winners = []

        # Kill feed
        self.kill_feed = []
        self.kill_feed_duration = 3.0

        # Countdown video overlay
        self.countdown_video_frames = []
        self.countdown_video_fps = 30
        self.countdown_video_loaded = False
        self.countdown_start_time = None
        self._load_countdown_video()

    def render_frame(self, fighters: List[Fighter], arena: FighterArena,
                    game_state: dict, particle_system=None):
        """
        Render complete frame

        Args:
            fighters: List of all fighters
            arena: FighterArena object
            game_state: Dictionary with game state info
            particle_system: Optional ParticleSystem for effects
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw arena
        self._draw_arena(arena)

        # Draw fighters with HP bars
        self._draw_fighters(fighters)

        # Draw particles
        if particle_system:
            particle_system.render(self.screen)

        # Draw UI
        self._draw_scoreboard(fighters, game_state)

        # Draw intro overlay if in intro phase
        if game_state.get("game_phase") == "intro":
            self._draw_intro(game_state.get("day_number", 1))
            return

        # Draw countdown if in countdown phase
        if game_state.get("game_phase") == "countdown":
            self._draw_countdown(game_state.get("countdown_number", 3))
            return

        # Draw podium if game is over
        if game_state.get("game_over", False) and not self.show_podium:
            self.show_podium = True
            self.podium_animation_progress = 0
            self.winners = [f for f in fighters if f.alive]
            self.game_state = game_state

        if self.show_podium:
            self._draw_podium(self.winners, self.game_state)

    def _draw_arena(self, arena: FighterArena):
        """
        Draw the rectangular arena

        Args:
            arena: FighterArena object
        """
        rect = arena.get_rect()

        # Draw arena floor
        pygame.draw.rect(
            self.screen,
            config.COLOR_FIGHTER_ARENA,
            rect
        )

        # Draw arena border
        pygame.draw.rect(
            self.screen,
            (0, 0, 0),
            rect,
            3  # Border width
        )

    def _draw_fighters(self, fighters: List[Fighter]):
        """
        Draw all fighters with their avatars and HP bars

        Args:
            fighters: List of all fighters
        """
        # Count alive fighters to determine if we should show HP bars
        alive_count = sum(1 for f in fighters if f.alive)
        show_hp_bars = alive_count <= 1000

        for fighter in fighters:
            # Skip if completely faded out
            if not fighter.alive and not fighter.is_fading():
                continue

            # Get or create fighter surface
            surface = self._get_fighter_surface(fighter)

            # Apply alpha for fade out
            if fighter.alpha < 255:
                surface = surface.copy()
                surface.set_alpha(fighter.alpha)

            # Draw fighter (scale down high-res surface to display size)
            pos = fighter.get_position()
            display_size = int(config.FOLLOWER_RADIUS * 2)

            # If surface is higher resolution, scale it down for display
            if surface.get_width() != display_size:
                display_surface = pygame.transform.smoothscale(surface, (display_size, display_size))
            else:
                display_surface = surface

            rect = display_surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(display_surface, rect)

            # Draw HP bar above fighter (only if <= 1000 fighters alive)
            if show_hp_bars and (fighter.alive or fighter.is_fading()):
                self._draw_hp_bar(fighter)

    def _get_fighter_surface(self, fighter: Fighter) -> pygame.Surface:
        """
        Get or create cached surface for a fighter

        Args:
            fighter: Fighter object

        Returns:
            Pygame surface with rendered avatar
        """
        # Use composite key (id, username) to prevent any ID collisions
        cache_key = (fighter.id, fighter.username)

        # Check if cache is valid (same radius and no update needed)
        cache_valid = (
            cache_key in self.fighter_surfaces and
            not fighter.surface_needs_update and
            cache_key in self.cached_radius and
            abs(self.cached_radius[cache_key] - config.FOLLOWER_RADIUS) < 0.01
        )

        if cache_valid:
            return self.fighter_surfaces[cache_key]

        # Create new surface
        size = int(config.FOLLOWER_RADIUS * 2)
        radius = int(config.FOLLOWER_RADIUS)

        # Use higher resolution for better quality when upscaling video
        # Multiply by upscale factor to maintain quality
        upscale_multiplier = config.UPSCALE_FACTOR if config.UPSCALE_VIDEO else 1.0
        render_size = int(size * upscale_multiplier)
        render_radius = int(radius * upscale_multiplier)

        surface = pygame.Surface((render_size, render_size), pygame.SRCALPHA)

        # Draw avatar circle
        if fighter.avatar_image:
            avatar_surface = self._pil_to_pygame(fighter.avatar_image, render_size)
            self._draw_circular_image(surface, avatar_surface, render_radius)
        else:
            # Draw colored circle for placeholder
            pygame.draw.circle(
                surface,
                fighter.color,
                (render_radius, render_radius),
                render_radius - int(config.FOLLOWER_BORDER_WIDTH * upscale_multiplier)
            )

        # Draw white border
        pygame.draw.circle(
            surface,
            config.COLOR_BORDER,
            (render_radius, render_radius),
            render_radius,
            int(config.FOLLOWER_BORDER_WIDTH * upscale_multiplier)
        )

        # Cache the surface along with the radius it was created at
        cache_key = (fighter.id, fighter.username)
        self.fighter_surfaces[cache_key] = surface
        self.cached_radius[cache_key] = config.FOLLOWER_RADIUS
        fighter.surface_needs_update = False

        return surface

    def _draw_circular_image(self, surface: pygame.Surface,
                           image_surface: pygame.Surface, radius: int):
        """Draw an image clipped to a circle"""
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius),
                         radius - config.FOLLOWER_BORDER_WIDTH)

        scaled_image = pygame.transform.scale(image_surface, (radius * 2, radius * 2))
        scaled_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(scaled_image, (0, 0))

    def _draw_hp_bar(self, fighter: Fighter):
        """
        Draw HP bar above a fighter
        HP bar scales with fighter size (dynamic scaling)

        Args:
            fighter: Fighter to draw HP bar for
        """
        pos = fighter.get_position()
        hp_pct = fighter.get_hp_percentage()

        # HP bar dimensions - scale with current follower radius
        # Base dimensions are for FOLLOWER_BASE_RADIUS (14px)
        scale_factor = config.FOLLOWER_RADIUS / config.FOLLOWER_BASE_RADIUS
        bar_width = max(int(config.FIGHTER_HP_BAR_WIDTH * scale_factor), 18)  # Min 18px width
        bar_height = max(int(config.FIGHTER_HP_BAR_HEIGHT * scale_factor), 3)  # Min 3px height
        bar_x = int(pos[0] - bar_width // 2)
        bar_y = int(pos[1] - config.FOLLOWER_RADIUS - max(int(8 * scale_factor), 5))

        # Determine HP color based on percentage
        if hp_pct > 0.6:
            hp_color = config.COLOR_HP_BAR_FULL
        elif hp_pct > 0.3:
            hp_color = config.COLOR_HP_BAR_MID
        else:
            hp_color = config.COLOR_HP_BAR_LOW

        # Draw HP fill (with 1px padding to create border effect)
        fill_width = int((bar_width - 2) * hp_pct)  # -2 for 1px border on each side
        if fill_width > 0:
            pygame.draw.rect(
                self.screen,
                hp_color,
                (bar_x + 1, bar_y + 1, fill_width, bar_height - 2)  # +1 for border, -2 for top/bottom border
            )

        # Draw background for unfilled portion
        unfilled_width = (bar_width - 2) - fill_width
        if unfilled_width > 0:
            pygame.draw.rect(
                self.screen,
                config.COLOR_HP_BAR_BG,
                (bar_x + 1 + fill_width, bar_y + 1, unfilled_width, bar_height - 2)
            )

        # Draw border around entire bar
        pygame.draw.rect(
            self.screen,
            (0, 0, 0),
            (bar_x, bar_y, bar_width, bar_height),
            1
        )

    def _draw_attack_indicator(self, fighter: Fighter):
        """
        Draw attack animation indicator

        Args:
            fighter: Fighter who is attacking
        """
        pos = fighter.get_position()
        # Draw a brief flash around the fighter
        pygame.draw.circle(
            self.screen,
            (255, 255, 100, 100),  # Yellow flash
            (int(pos[0]), int(pos[1])),
            int(config.FOLLOWER_RADIUS * 1.5),
            2
        )

    def _draw_scoreboard(self, fighters: List[Fighter], game_state: dict):
        """
        Draw scoreboard with title and stats

        Args:
            fighters: List of all fighters
            game_state: Game state dictionary
        """
        alive_count = sum(1 for f in fighters if f.alive)
        total_count = len(fighters)

        # Get arena for positioning
        arena_rect = config.FIGHTER_ARENA_RECT
        arena_top = arena_rect[1]
        arena_bottom = arena_rect[1] + arena_rect[3]

        # === TOP: FIGHTER ARENA title ===
        title_font = pygame.font.Font(None, 56)
        title_text = title_font.render("FIGHTER ARENA", True, config.COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.width // 2, arena_top - 50))
        self.screen.blit(title_text, title_rect)

        # "Making my followers battle every day" subtitle
        subtitle_font = pygame.font.Font(None, 32)
        subtitle_text = subtitle_font.render("Making my followers battle every day", True, config.COLOR_TEXT)
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, arena_top - 20))
        self.screen.blit(subtitle_text, subtitle_rect)

        # === BELOW ARENA: Day and stats ===
        day_number = game_state.get("day_number", getattr(config, 'DAY_NUMBER', 1))
        day_font = pygame.font.Font(None, 36)
        day_text = day_font.render(f"Day {day_number}: {total_count} fighters", True, config.COLOR_TEXT)
        day_rect = day_text.get_rect(center=(self.width // 2, arena_bottom + 25))
        self.screen.blit(day_text, day_rect)

        # Alive stat
        stats_font = pygame.font.Font(None, 28)
        alive_text = stats_font.render(f"Alive: {alive_count}/{total_count}", True, config.COLOR_TEXT)
        alive_rect = alive_text.get_rect(center=(self.width // 2, arena_bottom + 55))
        self.screen.blit(alive_text, alive_rect)

    def _draw_intro(self, day_number: int):
        """Draw intro overlay"""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        intro_text = f"Day {day_number} of making my"
        intro_text2 = "followers fight each other"

        text1 = self.font_large.render(intro_text, True, (255, 255, 255))
        text2 = self.font_large.render(intro_text2, True, (255, 255, 255))

        rect1 = text1.get_rect(center=(self.width // 2, self.height // 2 - 40))
        rect2 = text2.get_rect(center=(self.width // 2, self.height // 2 + 20))

        self.screen.blit(text1, rect1)
        self.screen.blit(text2, rect2)

    def _draw_countdown(self, number: int):
        """Draw countdown - skip if exporting video (recorder handles it with greenscreen)"""
        import config

        # Don't draw countdown overlay during video export - the recorder's greenscreen handles it
        if config.EXPORT_VIDEO:
            return

        # Try to use video overlay
        if self.countdown_video_loaded and self.countdown_start_time is not None:
            self._draw_countdown_video()
            return

        # Fallback to text-based countdown
        self._draw_countdown_text(number)

    def _draw_countdown_video(self):
        """Draw the current frame of the countdown video overlay"""
        import time

        if self.countdown_start_time is None:
            return

        elapsed = time.time() - self.countdown_start_time
        frame_index = int(elapsed * self.countdown_video_fps)

        if frame_index >= len(self.countdown_video_frames):
            return

        frame = self.countdown_video_frames[frame_index]

        # Scale frame to 30% of screen height
        frame_width = frame.get_width()
        frame_height = frame.get_height()

        target_height = int(self.height * 0.3)
        scale = target_height / frame_height
        new_width = int(frame_width * scale)
        new_height = target_height

        scaled_frame = pygame.transform.scale(frame, (new_width, new_height))

        # Center on screen
        x = (self.width - new_width) // 2
        y = (self.height - new_height) // 2

        self.screen.blit(scaled_frame, (x, y))

    def _draw_countdown_text(self, number: int):
        """Fallback text-based countdown display"""
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

        # Shadow
        shadow_text = countdown_font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(self.width // 2 + 5, self.height // 2 + 5))
        self.screen.blit(shadow_text, shadow_rect)
        self.screen.blit(countdown_text, rect)

    def _load_countdown_video(self):
        """Load countdown video frames from green screen video file"""
        video_path = "assets/3 2 1 fight.mp4"
        if not os.path.exists(video_path):
            print(f"Countdown video not found: {video_path}")
            return

        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            self.countdown_video_fps = cap.get(cv2.CAP_PROP_FPS) or 30

            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Apply chroma key (remove green screen)
                frame_with_alpha = self._apply_chroma_key(frame_rgb)

                # Convert to pygame surface
                pygame_surface = pygame.image.frombuffer(
                    frame_with_alpha.tobytes(),
                    (frame_with_alpha.shape[1], frame_with_alpha.shape[0]),
                    'RGBA'
                )
                frames.append(pygame_surface)

            cap.release()
            self.countdown_video_frames = frames
            self.countdown_video_loaded = len(frames) > 0
            print(f"Loaded countdown video: {len(frames)} frames at {self.countdown_video_fps:.0f} FPS")

        except ImportError:
            print("OpenCV not installed. Install with: pip install opencv-python")
        except Exception as e:
            print(f"Error loading countdown video: {e}")

    def _apply_chroma_key(self, frame_rgb, tolerance: int = 80):
        """Remove green screen from frame and return RGBA image"""
        import numpy as np

        # Create alpha channel (default fully opaque)
        alpha = np.ones((frame_rgb.shape[0], frame_rgb.shape[1]), dtype=np.uint8) * 255

        # Extract RGB channels
        r = frame_rgb[:, :, 0].astype(np.int16)
        g = frame_rgb[:, :, 1].astype(np.int16)
        b = frame_rgb[:, :, 2].astype(np.int16)

        # Green screen detection
        green_mask = (
            (g > 100) &
            (g > r + 30) &
            (g > b + 30)
        )

        # Make green pixels transparent
        alpha[green_mask] = 0

        # Combine RGB with alpha
        frame_rgba = np.dstack((frame_rgb, alpha))

        return frame_rgba

    def start_countdown_video(self):
        """Start the countdown video playback timer"""
        import time
        self.countdown_start_time = time.time()
        print("Countdown video started")

    def _draw_podium(self, winners: List[Fighter], game_state: dict):
        """Draw final podium with winners"""
        self.podium_animation_progress += 0.02
        if self.podium_animation_progress > 1.0:
            self.podium_animation_progress = 1.0

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * self.podium_animation_progress)))
        self.screen.blit(overlay, (0, 0))

        if self.podium_animation_progress < 1.0:
            return

        # Draw title
        pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))
        title_color = (255, int(215 + pulse * 40), 0)
        title = self.font_huge.render("WINNER!", True, title_color)
        title_y = int(self.height * 0.08)
        title_rect = title.get_rect(center=(self.width // 2, title_y))
        self.screen.blit(title, title_rect)

        # Draw winner
        if winners:
            winner = winners[0]
            winner_y = int(self.height * 0.25)

            # Spotlight
            spotlight_radius = int(80 + pulse * 20)
            for i in range(3):
                spotlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                radius = spotlight_radius + i * 25
                alpha = int(50 / (i + 1))
                pygame.draw.circle(spotlight, (255, 255, 0, alpha),
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
            name_rect = name_text.get_rect(center=(self.width // 2, winner_y + avatar_size // 2 + 30))
            self.screen.blit(name_text, name_rect)

            # Stats
            stats_text = self.font_medium.render(
                f"Kills: {winner.kills} | Damage: {winner.damage_dealt:.0f}",
                True, (200, 200, 200)
            )
            stats_rect = stats_text.get_rect(center=(self.width // 2, winner_y + avatar_size // 2 + 60))
            self.screen.blit(stats_text, stats_rect)

        # Draw leaderboards
        all_followers = game_state.get("all_followers", [])
        self._draw_leaderboards(game_state, all_followers)

    def _draw_leaderboards(self, game_state: dict, followers: list):
        """Draw current game leaderboard (centered)."""
        current_lb = game_state.get("current_game_leaderboard", [])

        if not current_lb:
            return

        follower_map = {f.username: f for f in followers}

        start_y = int(self.height * 0.45)
        board_width = int(self.width * 0.55)
        left_x = (self.width - board_width) // 2

        self._draw_leaderboard_panel(
            "CURRENT GAME", "TOP 10",
            current_lb[:10], left_x, start_y, board_width,
            (0, 200, 255), follower_map
        )

    def _draw_leaderboard_panel(self, title_line1: str, title_line2: str,
                               leaderboard: list, x: int, y: int, width: int,
                               color: tuple, follower_map: dict):
        """Draw a single leaderboard panel"""
        if not leaderboard:
            return

        entry_height = int(self.height * 0.026)
        header_height = int(self.height * 0.047)
        panel_height = header_height + len(leaderboard) * entry_height + 20

        panel = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 200))
        self.screen.blit(panel, (x, y))

        # Titles
        title1_text = self.font_medium.render(title_line1, True, color)
        title1_rect = title1_text.get_rect(center=(x + width // 2, y + int(self.height * 0.013)))
        self.screen.blit(title1_text, title1_rect)

        title2_text = self.font_medium.render(title_line2, True, color)
        title2_rect = title2_text.get_rect(center=(x + width // 2, y + int(self.height * 0.029)))
        self.screen.blit(title2_text, title2_rect)

        # Entries
        medals = ["1.", "2.", "3."]
        entry_y = y + header_height

        for i, (username, points) in enumerate(leaderboard):
            rank = i + 1
            rank_str = medals[i] if i < 3 else f"{rank}."
            rank_text = self.font_small.render(rank_str, True, (200, 200, 200))

            max_len = 16
            display_name = username if len(username) <= max_len else username[:max_len-2] + ".."
            name_font = pygame.font.Font(None, 14)
            name_text = name_font.render(display_name, True, (255, 255, 255))

            points_text = self.font_small.render(f"{points:.1f}", True, (0, 255, 150))

            rank_rect = rank_text.get_rect(left=x + 10, centery=entry_y)
            name_rect = name_text.get_rect(left=x + 40, centery=entry_y)
            points_rect = points_text.get_rect(right=x + width - 10, centery=entry_y)

            self.screen.blit(rank_text, rank_rect)
            self.screen.blit(name_text, name_rect)
            self.screen.blit(points_text, points_rect)

            entry_y += entry_height

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """Convert PIL image to pygame surface"""
        pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        surface = pygame.image.fromstring(data, size, mode)
        return surface.convert_alpha()

    def add_elimination(self, username: str):
        """Add an elimination to the kill feed"""
        import time
        self.kill_feed.append((username, time.time()))
        if len(self.kill_feed) > 5:
            self.kill_feed.pop(0)

    def reset(self):
        """Reset renderer state"""
        self.fighter_surfaces.clear()
        self.show_podium = False
        self.podium_animation_progress = 0
        self.winners = []
        self.kill_feed = []
