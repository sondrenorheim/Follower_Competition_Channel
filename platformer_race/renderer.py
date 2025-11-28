"""
Platformer Race Renderer

Handles all rendering for the platformer race game with top 5 UI.
"""

import pygame
import math
from PIL import Image
import config
from fighter_arena import FighterRenderer  # Reuse for racer avatars


class PlatformerRenderer:
    """Renders the platformer race"""

    def __init__(self, screen):
        """
        Initialize renderer

        Args:
            screen: Pygame screen surface
        """
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_title = pygame.font.Font(None, 56)
        self.font_subtitle = pygame.font.Font(None, 32)
        self.font_day = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 72)

        # Reuse fighter renderer for high-res avatar rendering
        self.fighter_renderer = FighterRenderer(screen)

        # Cached surfaces for racers
        self.racer_surfaces = {}

        # Game area position (extended viewport: 500x700 centered)
        self.game_area_x = (config.SCREEN_WIDTH - 500) // 2
        self.game_area_y = 180
        self.game_area_width = 500
        self.game_area_height = 700

    def render_frame(self, level, visible_racers, camera, game_state):
        """
        Render a complete frame

        Args:
            level: PlatformerLevel instance
            visible_racers: List of racers currently visible (dynamic culling)
            camera: PlatformerCamera instance
            game_state: Dictionary with game state info
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw title and subtitle (in screen space)
        self._draw_title_and_subtitle()

        # Draw game area border
        self._draw_game_area_border()

        # Render world (in camera/world space - static camera for vertical)
        self._draw_platforms(level.platforms, camera)
        self._draw_spikes(level.spikes, camera)
        self._draw_ladders(level.ladders, camera)
        self._draw_ropes(level.ropes, camera)
        self._draw_walls(level.walls, camera)
        self._draw_checkpoints(level.checkpoints, camera)
        self._draw_goal(level.goal, camera)
        self._draw_racers(visible_racers, camera)

        # Draw UI (in screen space)
        self._draw_day_counter(game_state.get('day', 1), game_state.get('racer_count', 0))
        self._draw_top_5_leaderboard(game_state.get('top_5', []))

        # Draw countdown text if in countdown phase
        if game_state.get('phase') == 'countdown':
            self._draw_countdown_text()

        # Draw winner display if game finished
        if game_state.get('phase') == 'finished':
            self._draw_winner_display(game_state.get('winner'), game_state.get('top_10'))

    def _draw_title_and_subtitle(self):
        """Draw title and subtitle at top of screen"""
        title_text = "PLATFORMER RACE"
        subtitle_text = "Making my followers battle every day"

        title_surface = self.font_title.render(title_text, True, config.COLOR_TEXT)
        subtitle_surface = self.font_subtitle.render(subtitle_text, True, (0, 0, 0))

        # Center titles
        title_rect = title_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 60))
        subtitle_rect = subtitle_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 100))

        self.screen.blit(title_surface, title_rect)
        self.screen.blit(subtitle_surface, subtitle_rect)

    def _draw_game_area_border(self):
        """Draw border around game area"""
        border_rect = pygame.Rect(
            self.game_area_x - 2,
            self.game_area_y - 2,
            self.game_area_width + 4,
            self.game_area_height + 4
        )
        pygame.draw.rect(self.screen, (255, 255, 255), border_rect, 2)

    def _draw_platforms(self, platforms, camera):
        """Draw static platforms"""
        for platform in platforms:
            screen_pos = camera.world_to_screen((platform.x, platform.y))

            # Only draw if visible
            if -100 <= screen_pos[0] <= self.game_area_x + self.game_area_width + 100:
                platform_rect = pygame.Rect(
                    int(screen_pos[0]),
                    int(screen_pos[1]),
                    int(platform.width),
                    int(platform.height)
                )

                # Clip to game area
                if platform_rect.right >= self.game_area_x and platform_rect.left <= self.game_area_x + self.game_area_width:
                    pygame.draw.rect(self.screen, platform.color, platform_rect)
                    # Add highlight edge
                    pygame.draw.rect(self.screen, (150, 150, 150), platform_rect, 1)

    def _draw_spikes(self, spikes, camera):
        """Draw spikes as triangular hazards"""
        for spike in spikes:
            screen_pos = camera.world_to_screen((spike.x, spike.y))

            # Only draw if visible
            if camera.is_visible(spike.x, spike.y):
                if spike.orientation == "up":
                    # Upward spikes - triangles pointing up
                    num_spikes = max(1, int(spike.width // 20))  # One spike every 20px
                    spike_width = spike.width / num_spikes
                    for i in range(num_spikes):
                        spike_x = screen_pos[0] + (i * spike_width)
                        points = [
                            (int(spike_x), int(screen_pos[1] + spike.height)),  # Bottom left
                            (int(spike_x + spike_width / 2), int(screen_pos[1])),  # Top point
                            (int(spike_x + spike_width), int(screen_pos[1] + spike.height))  # Bottom right
                        ]
                        pygame.draw.polygon(self.screen, spike.color, points)
                        pygame.draw.polygon(self.screen, (255, 0, 0), points, 1)  # Red outline
                elif spike.orientation == "down":
                    # Downward spikes - triangles pointing down
                    num_spikes = max(1, int(spike.width // 20))
                    spike_width = spike.width / num_spikes
                    for i in range(num_spikes):
                        spike_x = screen_pos[0] + (i * spike_width)
                        points = [
                            (int(spike_x), int(screen_pos[1])),  # Top left
                            (int(spike_x + spike_width / 2), int(screen_pos[1] + spike.height)),  # Bottom point
                            (int(spike_x + spike_width), int(screen_pos[1]))  # Top right
                        ]
                        pygame.draw.polygon(self.screen, spike.color, points)
                        pygame.draw.polygon(self.screen, (255, 0, 0), points, 1)  # Red outline

    def _draw_checkpoints(self, checkpoints, camera):
        """Draw checkpoints as flags or markers"""
        for checkpoint in checkpoints:
            screen_pos = camera.world_to_screen((checkpoint.x, checkpoint.y))

            # Only draw if visible
            if camera.is_visible(checkpoint.x, checkpoint.y):
                # Draw flag pole (extends upward only, stops at ground level)
                pole_height = 40
                pole_top = (int(screen_pos[0]), int(screen_pos[1]) - pole_height)
                pole_bottom = (int(screen_pos[0]), int(screen_pos[1]))
                pygame.draw.line(self.screen, (200, 200, 200), pole_top, pole_bottom, 3)

                # Draw flag at top of pole
                flag_offset = pole_height
                flag_points = [
                    (int(screen_pos[0]), int(screen_pos[1]) - flag_offset),
                    (int(screen_pos[0]) + 25, int(screen_pos[1]) - flag_offset + 10),
                    (int(screen_pos[0]), int(screen_pos[1]) - flag_offset + 20)
                ]
                pygame.draw.polygon(self.screen, (100, 200, 255), flag_points)

    def _draw_ladders(self, ladders, camera):
        """Draw ladders as vertical rungs"""
        for ladder in ladders:
            screen_pos = camera.world_to_screen((ladder.x, ladder.y))

            # Draw side rails
            pygame.draw.line(self.screen, ladder.color,
                            (int(screen_pos[0]), int(screen_pos[1])),
                            (int(screen_pos[0]), int(screen_pos[1] + ladder.height)), 3)
            pygame.draw.line(self.screen, ladder.color,
                            (int(screen_pos[0] + ladder.width), int(screen_pos[1])),
                            (int(screen_pos[0] + ladder.width), int(screen_pos[1] + ladder.height)), 3)

            # Draw rungs every 20px
            for rung_offset in range(0, int(ladder.height), 20):
                rung_y = int(screen_pos[1] + rung_offset)
                pygame.draw.line(self.screen, ladder.color,
                                (int(screen_pos[0]), rung_y),
                                (int(screen_pos[0] + ladder.width), rung_y), 2)

    def _draw_ropes(self, ropes, camera):
        """Draw ropes as wavy vertical lines"""
        for rope in ropes:
            screen_pos = camera.world_to_screen((rope.x, rope.y))

            # Draw rope with slight wave
            points = []
            for i in range(int(rope.height)):
                wave = 3 * math.sin((rope.y + i) * 0.1)
                points.append((int(screen_pos[0] + wave), int(screen_pos[1] + i)))

            if len(points) > 1:
                pygame.draw.lines(self.screen, rope.color, False, points, 4)

    def _draw_walls(self, walls, camera):
        """Draw climbable walls as vertical rectangles"""
        for wall in walls:
            screen_pos = camera.world_to_screen((wall.x, wall.y))

            wall_rect = pygame.Rect(
                int(screen_pos[0]),
                int(screen_pos[1]),
                int(wall.width),
                int(wall.height)
            )
            pygame.draw.rect(self.screen, wall.color, wall_rect)
            # Add grip texture
            for grip_offset in range(0, int(wall.height), 15):
                grip_y = int(screen_pos[1] + grip_offset)
                pygame.draw.circle(self.screen, (120, 120, 130),
                                 (int(screen_pos[0] + wall.width // 2), grip_y), 3)

    def _draw_goal(self, goal, camera):
        """Draw goal flag at top"""
        if not goal:
            return

        screen_pos = camera.world_to_screen((goal.x, goal.y))

        # Flag pole
        pygame.draw.line(self.screen, (200, 200, 200),
                        (int(screen_pos[0]), int(screen_pos[1])),
                        (int(screen_pos[0]), int(screen_pos[1] + 60)), 4)

        # Waving flag (checkered pattern)
        flag_points = [
            (int(screen_pos[0]), int(screen_pos[1])),
            (int(screen_pos[0] + 40), int(screen_pos[1] + 10)),
            (int(screen_pos[0] + 40), int(screen_pos[1] + 30)),
            (int(screen_pos[0]), int(screen_pos[1] + 40))
        ]
        pygame.draw.polygon(self.screen, (255, 215, 0), flag_points)  # Gold flag

    def _draw_racers(self, racers, camera):
        """Draw racers as circles with profile pictures"""
        for racer in racers:
            if not racer.alive:
                continue

            screen_pos = camera.world_to_screen((racer.x, racer.y))

            # Get or create racer surface
            cache_key = f"{racer.id}_{racer.alpha}"
            if cache_key not in self.racer_surfaces or racer.surface_needs_update:
                surface = self._create_racer_surface(racer)
                self.racer_surfaces[cache_key] = surface
                racer.surface_needs_update = False
            else:
                surface = self.racer_surfaces[cache_key]

            # Draw racer
            if surface:
                surface_rect = surface.get_rect(center=(int(screen_pos[0]), int(screen_pos[1])))
                self.screen.blit(surface, surface_rect)

    def _create_racer_surface(self, racer):
        """
        Create circular surface for racer with profile picture

        Args:
            racer: PlatformerRacer instance

        Returns:
            Pygame surface
        """
        size = int(racer.radius * 2)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        # Draw circle with avatar or color
        if racer.avatar_image:
            # Convert PIL image to pygame surface
            try:
                from PIL import Image

                # Resize avatar to circle size
                avatar_resized = racer.avatar_image.resize((size, size), Image.Resampling.LANCZOS)

                # Convert to pygame surface
                mode = avatar_resized.mode
                avatar_size = avatar_resized.size
                avatar_data = avatar_resized.tobytes()

                pygame_avatar = pygame.image.fromstring(avatar_data, avatar_size, mode)

                # Create circular mask
                mask_surface = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(mask_surface, (255, 255, 255, 255), (size // 2, size // 2), size // 2)

                # Apply mask
                surface.blit(pygame_avatar, (0, 0))
                surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            except Exception as e:
                # Fallback to colored circle
                pygame.draw.circle(surface, racer.color, (size // 2, size // 2), size // 2)
        else:
            # No avatar - draw colored circle
            pygame.draw.circle(surface, racer.color, (size // 2, size // 2), size // 2)

        # Draw border
        pygame.draw.circle(surface, (255, 255, 255), (size // 2, size // 2), size // 2, 2)

        # Apply alpha if fading
        if racer.alpha < 255:
            surface.set_alpha(racer.alpha)

        return surface

    def _draw_day_counter(self, day, racer_count):
        """Draw day counter below game area"""
        day_text = f"Day {day}: {racer_count} racers"
        day_surface = self.font_day.render(day_text, True, config.COLOR_TEXT)

        day_rect = day_surface.get_rect(center=(config.SCREEN_WIDTH // 2, self.game_area_y + self.game_area_height + 30))
        self.screen.blit(day_surface, day_rect)

    def _draw_top_5_leaderboard(self, top_5_data):
        """
        Draw horizontal top 5 leaderboard below day counter

        Args:
            top_5_data: List of tuples (username, progress)
        """
        if not top_5_data:
            return

        # Position colors for medals
        position_colors = [
            (255, 215, 0),    # 1st - Gold
            (192, 192, 192),  # 2nd - Silver
            (205, 127, 50),   # 3rd - Bronze
            (255, 255, 255),  # 4th - White
            (255, 255, 255),  # 5th - White
        ]

        # Starting Y position (below day counter)
        start_y = self.game_area_y + self.game_area_height + 70
        entry_width = 100  # Width per entry
        total_width = len(top_5_data) * entry_width
        start_x = (config.SCREEN_WIDTH - total_width) // 2

        for i, (username, progress) in enumerate(top_5_data):
            x = start_x + (i * entry_width)
            color = position_colors[i]

            # Position number
            position_text = f"{i+1}"
            if i == 0:
                position_text += "st"
            elif i == 1:
                position_text += "nd"
            elif i == 2:
                position_text += "rd"
            else:
                position_text += "th"

            pos_surface = self.font_small.render(position_text, True, color)
            pos_rect = pos_surface.get_rect(center=(x + entry_width // 2, start_y))
            self.screen.blit(pos_surface, pos_rect)

            # Username (truncated if too long)
            display_name = username[:8] if len(username) > 8 else username
            name_surface = self.font_small.render(display_name, True, color)
            name_rect = name_surface.get_rect(center=(x + entry_width // 2, start_y + 25))
            self.screen.blit(name_surface, name_rect)

            # Progress percentage
            progress_pct = f"{int(progress * 100)}%"
            progress_surface = self.font_small.render(progress_pct, True, (200, 200, 200))
            progress_rect = progress_surface.get_rect(center=(x + entry_width // 2, start_y + 45))
            self.screen.blit(progress_surface, progress_rect)

    def _draw_countdown_text(self):
        """Draw countdown text overlay (greenscreen video will be added during export)"""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Draw "GET READY!" text
        ready_text = "GET READY!"
        ready_surface = self.font_large.render(ready_text, True, (255, 255, 255))
        ready_rect = ready_surface.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))
        self.screen.blit(ready_surface, ready_rect)

    def _draw_winner_display(self, winner, top_10):
        """
        Draw winner podium and leaderboards

        Args:
            winner: Winner racer object
            top_10: List of top 10 finishers
        """
        if not winner:
            return

        # Draw dark overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # Winner title with pulsing effect
        winner_text = "WINNER!"
        winner_surface = self.font_large.render(winner_text, True, (255, 215, 0))
        winner_rect = winner_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 150))
        self.screen.blit(winner_surface, winner_rect)

        # Winner name
        name_surface = self.font_title.render(winner.username, True, (255, 255, 255))
        name_rect = name_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 250))
        self.screen.blit(name_surface, name_rect)

        # Draw top 10 leaderboard with profile pictures
        if top_10:
            # Title for top 10
            top_10_title = self.font_medium.render("TOP 10 FINISHERS", True, (255, 215, 0))
            top_10_rect = top_10_title.get_rect(center=(config.SCREEN_WIDTH // 2, 350))
            self.screen.blit(top_10_title, top_10_rect)

            # Draw each finisher in two columns (5 per column)
            start_y = 400
            avatar_size = 40
            row_height = 50
            left_x = config.SCREEN_WIDTH // 2 - 250
            right_x = config.SCREEN_WIDTH // 2 + 50

            for i, racer in enumerate(top_10):
                # Determine column and row
                if i < 5:
                    x = left_x
                    y = start_y + (i * row_height)
                else:
                    x = right_x
                    y = start_y + ((i - 5) * row_height)

                # Draw placement number
                placement_text = f"#{i+1}"
                placement_surface = self.font_medium.render(placement_text, True, (255, 215, 0))
                self.screen.blit(placement_surface, (x, y + 10))

                # Draw avatar (profile picture)
                if racer.avatar_image:
                    # Convert PIL image to pygame surface and scale
                    avatar_surface = self._pil_to_pygame(racer.avatar_image, avatar_size)
                    self.screen.blit(avatar_surface, (x + 50, y))
                else:
                    # Draw colored circle if no avatar
                    pygame.draw.circle(self.screen, racer.color, (x + 70, y + 20), avatar_size // 2)

                # Draw username
                username_surface = self.font_small.render(racer.username[:15], True, (255, 255, 255))
                self.screen.blit(username_surface, (x + 100, y + 12))

                # Draw finish time
                time_text = f"{racer.finish_time:.2f}s"
                time_surface = self.font_small.render(time_text, True, (200, 200, 200))
                self.screen.blit(time_surface, (x + 100, y + 28))

    def _pil_to_pygame(self, pil_image: Image.Image, size: int) -> pygame.Surface:
        """Convert PIL image to pygame surface"""
        pil_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        surface = pygame.image.fromstring(data, size, mode)
        return surface.convert_alpha()
