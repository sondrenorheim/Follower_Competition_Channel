"""
Obstacle Course Renderer Module
Handles rendering for the obstacle course race
"""

import pygame
from typing import List
import config
from .racer import Racer
from .obstacle_course import ObstacleCourse
from .obstacle_course_camera import ObstacleCourseCamera
from .fighter_renderer import FighterRenderer  # Reuse for racer avatars


class ObstacleCourseRenderer:
    """
    Renders the obstacle course race
    """

    def __init__(self, screen: pygame.Surface):
        """
        Initialize renderer

        Args:
            screen: Pygame screen surface
        """
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        self.font_title = pygame.font.Font(None, 56)      # For main title
        self.font_subtitle = pygame.font.Font(None, 32)   # For subtitle
        self.font_day = pygame.font.Font(None, 36)        # For day counter

        # Reuse fighter renderer for high-res avatar rendering
        self.fighter_renderer = FighterRenderer(screen)

    def render_frame(self, racers: List[Racer], course: ObstacleCourse,
                    camera: ObstacleCourseCamera, game_state: dict):
        """
        Render a complete frame

        Args:
            racers: List of all racers
            course: Obstacle course
            camera: Camera object
            game_state: Dictionary with game state info
        """
        # Clear screen
        self.screen.fill(config.COLOR_BACKGROUND)

        # Draw course elements (in world space, transformed by camera)
        self._draw_track(course, camera)
        self._draw_obstacles(course, camera)
        self._draw_racers(racers, camera)

        # Draw title and day counter (in screen space)
        self._draw_title_and_day(len(racers))

        # Draw UI (in screen space)
        self._draw_ui(game_state)

        # Draw countdown video overlay if provided
        countdown_frame = game_state.get('countdown_frame')
        if countdown_frame is not None:
            self._draw_countdown_overlay(countdown_frame)

    def _draw_track(self, course: ObstacleCourse, camera: ObstacleCourseCamera):
        """Draw the track with continuous curved barriers and checkered lines (horizontal)"""
        # Draw continuous barrier lines that follow the track curves
        # Build lists of top and bottom barrier points for ALL waypoints
        top_barrier_points = []
        bottom_barrier_points = []
        top_barrier_outer = []
        bottom_barrier_outer = []

        barrier_thickness = 12  # Thick barriers

        for waypoint in course.waypoints:
            # Get track bounds at this waypoint
            track_top, track_bottom = course.get_track_bounds_at_x(waypoint[0])

            # Convert to screen coordinates - inner edge (track side)
            top_screen = camera.world_to_screen((waypoint[0], track_top))
            bottom_screen = camera.world_to_screen((waypoint[0], track_bottom))

            # Outer edge of barrier
            top_outer = camera.world_to_screen((waypoint[0], track_top - barrier_thickness))
            bottom_outer = camera.world_to_screen((waypoint[0], track_bottom + barrier_thickness))

            top_barrier_points.append(top_screen)
            bottom_barrier_points.append(bottom_screen)
            top_barrier_outer.append(top_outer)
            bottom_barrier_outer.append(bottom_outer)

        # Draw thick barriers with stripe pattern
        if len(top_barrier_points) >= 2:
            # Draw top barrier as polygon (filled thick barrier)
            self._draw_striped_barrier(top_barrier_outer, top_barrier_points, barrier_thickness)
            # Draw bottom barrier
            self._draw_striped_barrier(bottom_barrier_points, bottom_barrier_outer, barrier_thickness)

        # Draw checkered starting line (vertical for horizontal track, within track bounds)
        start_screen = camera.world_to_screen(course.start_line)
        if -50 <= start_screen[0] <= config.SCREEN_WIDTH + 50:
            start_top, start_bottom = course.get_track_bounds_at_x(course.start_line[0])
            start_top_screen = camera.world_to_screen((course.start_line[0], start_top))[1]
            start_bottom_screen = camera.world_to_screen((course.start_line[0], start_bottom))[1]
            self._draw_checkered_line_vertical(start_screen[0], start_top_screen, start_bottom_screen, (255, 0, 0), (255, 255, 255))

        # Draw checkered finish line (vertical for horizontal track, within track bounds)
        finish_screen = camera.world_to_screen(course.finish_line)
        if -50 <= finish_screen[0] <= config.SCREEN_WIDTH + 50:
            finish_top, finish_bottom = course.get_track_bounds_at_x(course.finish_line[0])
            finish_top_screen = camera.world_to_screen((course.finish_line[0], finish_top))[1]
            finish_bottom_screen = camera.world_to_screen((course.finish_line[0], finish_bottom))[1]
            self._draw_checkered_line_vertical(finish_screen[0], finish_top_screen, finish_bottom_screen, (255, 0, 0), (255, 255, 255))

    def _draw_striped_barrier(self, outer_points, inner_points, thickness):
        """Draw a thick barrier with checkered square pattern"""
        if len(outer_points) < 2 or len(inner_points) < 2:
            return

        # Colors for the barrier - blue and white checkers
        color1 = (50, 100, 180)   # Blue
        color2 = (220, 220, 230)  # Light gray/white

        # First draw the full barrier as a base
        for i in range(len(outer_points) - 1):
            p1_outer = outer_points[i]
            p2_outer = outer_points[i + 1]
            p1_inner = inner_points[i]
            p2_inner = inner_points[i + 1]

            polygon_points = [p1_outer, p2_outer, p2_inner, p1_inner]
            try:
                # Draw base color
                pygame.draw.polygon(self.screen, color2, polygon_points)
            except:
                pass

        # Now draw checkered squares on top
        square_size = 20  # Size of each checker square

        # Calculate total length along the barrier
        for i in range(len(outer_points) - 1):
            p1_outer = outer_points[i]
            p2_outer = outer_points[i + 1]
            p1_inner = inner_points[i]
            p2_inner = inner_points[i + 1]

            # Calculate segment length
            import math
            segment_length = math.sqrt((p2_outer[0] - p1_outer[0])**2 + (p2_outer[1] - p1_outer[1])**2)

            # Draw checkers along this segment
            num_squares = max(1, int(segment_length / square_size))

            for j in range(num_squares):
                # Determine checker color (alternating pattern)
                checker_row = i
                checker_col = j
                is_blue = (checker_row + checker_col) % 2 == 0

                if is_blue:
                    # Interpolate positions along the segment
                    t1 = j / num_squares
                    t2 = (j + 1) / num_squares

                    # Calculate quad corners
                    q1_outer = (
                        p1_outer[0] + t1 * (p2_outer[0] - p1_outer[0]),
                        p1_outer[1] + t1 * (p2_outer[1] - p1_outer[1])
                    )
                    q2_outer = (
                        p1_outer[0] + t2 * (p2_outer[0] - p1_outer[0]),
                        p1_outer[1] + t2 * (p2_outer[1] - p1_outer[1])
                    )
                    q1_inner = (
                        p1_inner[0] + t1 * (p2_inner[0] - p1_inner[0]),
                        p1_inner[1] + t1 * (p2_inner[1] - p1_inner[1])
                    )
                    q2_inner = (
                        p1_inner[0] + t2 * (p2_inner[0] - p1_inner[0]),
                        p1_inner[1] + t2 * (p2_inner[1] - p1_inner[1])
                    )

                    # Draw blue square
                    try:
                        pygame.draw.polygon(self.screen, color1, [q1_outer, q2_outer, q2_inner, q1_inner])
                    except:
                        pass

        # Draw border outline
        try:
            pygame.draw.lines(self.screen, (30, 30, 30), False, outer_points, 2)
            pygame.draw.lines(self.screen, (30, 30, 30), False, inner_points, 2)
        except:
            pass


    def _draw_checkered_line_vertical(self, x_pos: int, y_top: int, y_bottom: int, color1: tuple, color2: tuple):
        """
        Draw a vertical checkered pattern line (like a race finish line) within track bounds

        Args:
            x_pos: X position of the line
            y_top: Top Y boundary of the track
            y_bottom: Bottom Y boundary of the track
            color1: First color (red)
            color2: Second color (white)
        """
        square_size = 20  # Size of each checkered square
        line_width = 10  # Width of the checkered line

        # Draw alternating squares between top and bottom bounds
        y = int(y_top)
        i = 0
        while y < y_bottom:
            color = color1 if i % 2 == 0 else color2

            # Clamp the square height to not exceed bottom boundary
            square_height = min(square_size, int(y_bottom) - y)

            rect = pygame.Rect(int(x_pos - line_width // 2), y, line_width, square_height)
            pygame.draw.rect(self.screen, color, rect)

            y += square_size
            i += 1

    def _draw_obstacles(self, course: ObstacleCourse, camera: ObstacleCourseCamera):
        """Draw all visible obstacles"""
        from .obstacles import Spinner, Bumper, SpeedBoost, SlowZone, Crusher

        for obstacle in course.obstacles:
            if not camera.is_visible((obstacle.x, obstacle.y)):
                continue

            # Handle different obstacle types
            if isinstance(obstacle, Spinner):
                self._draw_spinner(obstacle, camera)
            elif isinstance(obstacle, Bumper):
                self._draw_bumper(obstacle, camera)
            elif isinstance(obstacle, (SpeedBoost, SlowZone)):
                self._draw_zone(obstacle, camera)
            elif isinstance(obstacle, Crusher):
                self._draw_crusher(obstacle, camera)
            else:
                # Default rectangle drawing for walls
                screen_pos = camera.world_to_screen((obstacle.x, obstacle.y))
                rect = pygame.Rect(screen_pos[0], screen_pos[1],
                                 obstacle.width, obstacle.height)
                pygame.draw.rect(self.screen, obstacle.color, rect)
                pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)  # Border

    def _draw_spinner(self, spinner, camera):
        """Draw a spinning bar obstacle"""
        # Get bar endpoints
        end1, end2 = spinner.get_bar_endpoints()

        # Convert to screen coordinates
        end1_screen = camera.world_to_screen(end1)
        end2_screen = camera.world_to_screen(end2)
        center_screen = camera.world_to_screen((spinner.center_x, spinner.center_y))

        # Draw the spinning bar
        pygame.draw.line(self.screen, spinner.color, end1_screen, end2_screen, int(spinner.bar_width))

        # Draw center pivot
        pygame.draw.circle(self.screen, (50, 50, 50), center_screen, 8)
        pygame.draw.circle(self.screen, (150, 150, 150), center_screen, 5)

    def _draw_bumper(self, bumper, camera):
        """Draw a circular bumper"""
        center_screen = camera.world_to_screen((bumper.center_x, bumper.center_y))

        # Use hit color if recently hit
        color = bumper.hit_color if bumper.is_hit else bumper.color

        # Draw bumper circle
        pygame.draw.circle(self.screen, color, center_screen, int(bumper.radius))
        pygame.draw.circle(self.screen, (0, 0, 0), center_screen, int(bumper.radius), 3)

        # Draw inner highlight
        pygame.draw.circle(self.screen, (255, 255, 255), center_screen, int(bumper.radius * 0.4))

    def _draw_zone(self, zone, camera):
        """Draw a speed boost or slow zone"""
        screen_pos = camera.world_to_screen((zone.x, zone.y))

        # Draw semi-transparent zone
        zone_surface = pygame.Surface((int(zone.width), int(zone.height)), pygame.SRCALPHA)
        zone_color = (*zone.color, 150)  # Add alpha
        zone_surface.fill(zone_color)

        self.screen.blit(zone_surface, screen_pos)

        # Draw border
        rect = pygame.Rect(screen_pos[0], screen_pos[1], zone.width, zone.height)
        pygame.draw.rect(self.screen, zone.color, rect, 2)

        # Draw arrows or pattern to indicate effect
        if hasattr(zone, 'boost_multiplier'):  # Speed boost
            # Draw forward arrows
            self._draw_arrows(screen_pos, zone.width, zone.height, (100, 255, 100))
        else:  # Slow zone
            # Draw wavy lines for mud
            self._draw_mud_pattern(screen_pos, zone.width, zone.height)

    def _draw_arrows(self, pos, width, height, color):
        """Draw forward-pointing arrows inside a zone"""
        import math
        arrow_spacing = 25
        arrow_size = 8

        for y_offset in range(15, int(height) - 10, arrow_spacing):
            for x_offset in range(15, int(width) - 10, arrow_spacing):
                cx = pos[0] + x_offset
                cy = pos[1] + y_offset

                # Draw simple arrow pointing right
                points = [
                    (cx - arrow_size, cy - arrow_size // 2),
                    (cx + arrow_size, cy),
                    (cx - arrow_size, cy + arrow_size // 2)
                ]
                pygame.draw.polygon(self.screen, color, points)

    def _draw_mud_pattern(self, pos, width, height):
        """Draw mud/slow zone pattern"""
        import math
        # Draw wavy horizontal lines
        for y_offset in range(10, int(height) - 5, 15):
            points = []
            for x in range(0, int(width), 5):
                wave_y = pos[1] + y_offset + math.sin(x * 0.2) * 3
                points.append((pos[0] + x, wave_y))
            if len(points) > 1:
                pygame.draw.lines(self.screen, (100, 70, 30), False, points, 2)

    def _draw_crusher(self, crusher, camera):
        """Draw a crusher/piston obstacle"""
        screen_pos = camera.world_to_screen((crusher.x, crusher.y))

        # Use extended color if extended
        color = crusher.extended_color if crusher.is_extended else crusher.color

        # Draw the crusher rectangle
        rect = pygame.Rect(screen_pos[0], screen_pos[1],
                         crusher.current_width, crusher.height)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)

        # Draw warning stripes if extended
        if crusher.is_extended:
            stripe_width = 10
            for i in range(0, int(crusher.current_width), stripe_width * 2):
                stripe_rect = pygame.Rect(screen_pos[0] + i, screen_pos[1],
                                         stripe_width, crusher.height)
                pygame.draw.rect(self.screen, (200, 200, 50), stripe_rect)

    def _draw_racers(self, racers: List[Racer], camera: ObstacleCourseCamera):
        """Draw all visible racers"""
        for racer in racers:
            if not racer.alive and not racer.is_fading():
                continue

            if camera.is_visible((racer.x, racer.y)):
                # Get racer surface (reuse fighter renderer)
                surface = self.fighter_renderer._get_fighter_surface(racer)

                # Apply fade if needed
                if racer.alpha < 255:
                    surface = surface.copy()
                    surface.set_alpha(racer.alpha)

                # Convert to screen coordinates
                screen_pos = camera.world_to_screen((racer.x, racer.y))

                # Scale down high-res surface for display
                display_size = int(config.FOLLOWER_RADIUS * 2)
                if surface.get_width() != display_size:
                    display_surface = pygame.transform.smoothscale(surface, (display_size, display_size))
                else:
                    display_surface = surface

                # Draw
                rect = display_surface.get_rect(center=screen_pos)
                self.screen.blit(display_surface, rect)

    def _draw_title_and_day(self, total_racers: int):
        """
        Draw title above track and day counter below track

        Args:
            total_racers: Total number of racers in the game
        """
        # Calculate track top position (approximate, based on screen center)
        # Track is roughly centered vertically, so we can use screen height
        track_top = 80  # Approximate top of visible track area
        track_bottom = config.SCREEN_HEIGHT - 80  # Approximate bottom

        # Draw title above track
        title_text = "OBSTACLE COURSE RACE"
        title_surface = self.font_title.render(title_text, True, (0, 0, 0))
        title_rect = title_surface.get_rect(center=(config.SCREEN_WIDTH // 2, track_top - 50))
        self.screen.blit(title_surface, title_rect)

        # Draw subtitle above track
        subtitle_text = "Making my followers battle every day"
        subtitle_surface = self.font_subtitle.render(subtitle_text, True, (0, 0, 0))
        subtitle_rect = subtitle_surface.get_rect(center=(config.SCREEN_WIDTH // 2, track_top - 15))
        self.screen.blit(subtitle_surface, subtitle_rect)

        # Draw day counter below track
        day_text = f"Day {config.DAY_NUMBER}: {total_racers} racers"
        day_surface = self.font_day.render(day_text, True, (0, 0, 0))
        day_rect = day_surface.get_rect(center=(config.SCREEN_WIDTH // 2, track_bottom + 25))
        self.screen.blit(day_surface, day_rect)

    def _draw_ui(self, game_state: dict):
        """Draw UI elements"""
        # Race info top-left
        alive_count = game_state.get('alive_count', 0)
        finished_count = game_state.get('finished_count', 0)

        info_text = f"Racing: {alive_count} | Finished: {finished_count}"
        text_surface = self.font_small.render(info_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))

        # Timer (if grace period active)
        grace_timer = game_state.get('grace_timer')
        if grace_timer is not None and grace_timer > 0:
            timer_text = f"Time Remaining: {grace_timer:.1f}s"
            text_surface = self.font.render(timer_text, True, (255, 0, 0))
            rect = text_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 50))
            self.screen.blit(text_surface, rect)

        # Progress bar for leader
        leader_progress = game_state.get('leader_progress', 0.0)
        if leader_progress > 0:
            self._draw_progress_bar(leader_progress)

        # Top 5 leaderboard (right side)
        top_5 = game_state.get('top_5', [])
        if top_5:
            self._draw_leaderboard(top_5)

        # End-game leaderboards (instead of "game over" message)
        if game_state.get('show_leaderboards'):
            self._draw_end_game_leaderboards(
                game_state.get('current_game_leaderboard', []),
                game_state.get('all_time_leaderboard', [])
            )

    def _draw_progress_bar(self, progress: float):
        """
        Draw a progress bar showing how close the leader is to the finish

        Args:
            progress: Progress value from 0.0 to 1.0
        """
        # Progress bar dimensions
        bar_width = 400
        bar_height = 25
        bar_x = (config.SCREEN_WIDTH - bar_width) // 2
        bar_y = 10

        # Draw background (dark gray)
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (50, 50, 50), bg_rect)

        # Draw progress (gradient from yellow to green)
        if progress > 0:
            progress_width = int(bar_width * progress)
            progress_rect = pygame.Rect(bar_x, bar_y, progress_width, bar_height)

            # Color: yellow at start, green near finish
            if progress < 0.5:
                color = (255, 215, 0)  # Gold
            elif progress < 0.8:
                color = (255, 165, 0)  # Orange
            else:
                color = (50, 205, 50)  # Green

            pygame.draw.rect(self.screen, color, progress_rect)

        # Draw border
        pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 2)

        # Draw percentage text
        percentage_text = f"{progress * 100:.1f}%"
        text_surface = self.font_small.render(percentage_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2))
        self.screen.blit(text_surface, text_rect)

    def _draw_leaderboard(self, top_5: list):
        """
        Draw top 5 leaderboard on the right side

        Args:
            top_5: List of (username, progress) tuples
        """
        # Leaderboard position (top-right)
        board_x = config.SCREEN_WIDTH - 250
        board_y = 10
        board_width = 240
        row_height = 28
        board_height = len(top_5) * row_height + 35

        # Draw semi-transparent background
        bg_surface = pygame.Surface((board_width, board_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        self.screen.blit(bg_surface, (board_x, board_y))

        # Draw title
        title_surface = self.font_small.render("TOP 5 RACERS", True, (255, 215, 0))
        title_rect = title_surface.get_rect(center=(board_x + board_width // 2, board_y + 15))
        self.screen.blit(title_surface, title_rect)

        # Draw each racer
        for i, (username, progress) in enumerate(top_5):
            y_pos = board_y + 35 + i * row_height

            # Position number with color
            position_colors = [
                (255, 215, 0),   # 1st - Gold
                (192, 192, 192), # 2nd - Silver
                (205, 127, 50),  # 3rd - Bronze
                (255, 255, 255), # 4th - White
                (255, 255, 255), # 5th - White
            ]
            pos_color = position_colors[i] if i < len(position_colors) else (255, 255, 255)

            # Draw position number
            pos_text = f"{i + 1}."
            pos_surface = self.font_small.render(pos_text, True, pos_color)
            self.screen.blit(pos_surface, (board_x + 10, y_pos))

            # Draw username (truncated if too long)
            max_username_length = 15
            display_username = username[:max_username_length] + "..." if len(username) > max_username_length else username
            name_surface = self.font_small.render(display_username, True, (255, 255, 255))
            self.screen.blit(name_surface, (board_x + 35, y_pos))

            # Draw progress percentage
            progress_text = f"{progress * 100:.1f}%"
            progress_surface = self.font_small.render(progress_text, True, (100, 255, 100))
            progress_rect = progress_surface.get_rect(right=board_x + board_width - 10, top=y_pos)
            self.screen.blit(progress_surface, progress_rect)

    def _draw_end_game_leaderboards(self, current_game_board: list, all_time_board: list):
        """
        Draw two side-by-side leaderboards: current game and all-time

        Args:
            current_game_board: List of (username, points) tuples for current race
            all_time_board: List of (username, total_points, stats) tuples for all-time
        """
        # Screen dimensions
        screen_w = config.SCREEN_WIDTH
        screen_h = config.SCREEN_HEIGHT

        # Panel dimensions (matching battle royale layout)
        panel_width = int(screen_w * 0.44)  # 44% of screen width
        panel_spacing = int(screen_w * 0.037)  # 3.7% spacing between panels

        # Positioning
        start_y = int(screen_h * 0.365)  # 36.5% down screen
        left_panel_x = (screen_w - (panel_width * 2 + panel_spacing)) // 2
        right_panel_x = left_panel_x + panel_width + panel_spacing

        # Fonts
        font_header = pygame.font.Font(None, 28)
        font_entry = pygame.font.Font(None, 14)
        font_medium = pygame.font.Font(None, 18)

        # Draw left panel - Current Race
        self._draw_leaderboard_panel(
            current_game_board[:10],
            left_panel_x,
            start_y,
            panel_width,
            "CURRENT RACE",
            "TOP 10",
            (0, 200, 255),  # Cyan
            font_header,
            font_entry,
            is_current_game=True
        )

        # Draw right panel - All-Time
        self._draw_leaderboard_panel(
            all_time_board[:10],
            right_panel_x,
            start_y,
            panel_width,
            "ALL-TIME",
            "TOP 10",
            (255, 215, 0),  # Gold
            font_header,
            font_entry,
            is_current_game=False
        )

    def _draw_leaderboard_panel(self, entries: list, x: int, y: int, width: int,
                                title_line1: str, title_line2: str, title_color: tuple,
                                font_header, font_entry, is_current_game: bool):
        """
        Draw a single leaderboard panel

        Args:
            entries: List of tuples (username, points) or (username, total_points, stats)
            x, y: Top-left position
            width: Panel width
            title_line1, title_line2: Two-line title
            title_color: Color for title
            font_header, font_entry: Fonts to use
            is_current_game: True if current game board, False if all-time
        """
        entry_height = int(config.SCREEN_HEIGHT * 0.026)  # 2.6% of screen height
        header_height = 60
        panel_height = header_height + (len(entries) * entry_height) + 20

        # Draw semi-transparent background
        bg_surface = pygame.Surface((width, panel_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 200))
        self.screen.blit(bg_surface, (x, y))

        # Draw title (two lines)
        title1_surface = font_header.render(title_line1, True, title_color)
        title1_rect = title1_surface.get_rect(center=(x + width // 2, y + 20))
        self.screen.blit(title1_surface, title1_rect)

        title2_surface = font_header.render(title_line2, True, title_color)
        title2_rect = title2_surface.get_rect(center=(x + width // 2, y + 42))
        self.screen.blit(title2_surface, title2_rect)

        # Draw entries
        for i, entry in enumerate(entries):
            entry_y = y + header_height + (i * entry_height)

            # Medals for top 3
            medals = ["🥇", "🥈", "🥉"]
            if i < 3:
                rank_text = medals[i]
            else:
                rank_text = f"{i + 1}."

            # Extract data based on leaderboard type
            if is_current_game:
                username, points = entry
            else:
                username, total_points, _ = entry
                points = total_points

            # Draw rank
            rank_surface = font_entry.render(rank_text, True, (255, 255, 255))
            self.screen.blit(rank_surface, (x + 10, entry_y + 2))

            # Draw username (truncated)
            max_username_len = 18
            display_username = username[:max_username_len] + "..." if len(username) > max_username_len else username
            name_surface = font_entry.render(display_username, True, (255, 255, 255))
            self.screen.blit(name_surface, (x + 50, entry_y + 2))

            # Draw points
            points_text = f"{int(points)}"
            points_surface = font_entry.render(points_text, True, (0, 255, 150))
            points_rect = points_surface.get_rect(right=x + width - 10, top=entry_y + 2)
            self.screen.blit(points_surface, points_rect)

    def _draw_countdown_overlay(self, frame_surface: pygame.Surface):
        """
        Draw countdown video overlay centered on screen

        Args:
            frame_surface: Pygame surface of current video frame
        """
        # Center the video on screen
        rect = frame_surface.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))
        self.screen.blit(frame_surface, rect)
