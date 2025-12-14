"""
Performance Monitor Module
Tracks and logs performance metrics for game simulation
"""

import time
from typing import Dict, Optional
from collections import deque


class PerformanceMonitor:
    """
    Monitors and logs performance metrics for the game simulation
    Provides insights into FPS, update times, rendering times, etc.
    """

    def __init__(self, log_interval: float = 1.0, enable_detailed_logging: bool = True):
        """
        Initialize performance monitor

        Args:
            log_interval: How often to print performance logs (in seconds)
            enable_detailed_logging: If True, print detailed metrics
        """
        self.log_interval = log_interval
        self.enable_detailed_logging = enable_detailed_logging

        # Timing
        self.last_log_time = time.time()
        self.frame_start_time = 0
        self.section_start_time = 0

        # Frame tracking
        self.frame_count = 0
        self.fps_samples = deque(maxlen=60)  # Track last 60 frames for FPS
        self.last_frame_time = time.time()

        # Section timings (averaged over interval)
        self.section_times: Dict[str, list] = {
            "update": [],
            "physics": [],
            "render": [],
            "total": []
        }

        # Counters
        self.collision_checks = 0
        self.players_updated = 0
        self.players_rendered = 0
        self.players_culled = 0

        # Totals for logging
        self.total_collision_checks = 0
        self.total_players_updated = 0
        self.total_players_rendered = 0
        self.total_players_culled = 0

    def start_frame(self):
        """Mark the start of a new frame"""
        current_time = time.time()
        self.frame_start_time = current_time

        # Calculate FPS
        frame_time = current_time - self.last_frame_time
        if frame_time > 0:
            fps = 1.0 / frame_time
            self.fps_samples.append(fps)
        self.last_frame_time = current_time

        self.frame_count += 1

        # Reset frame counters
        self.collision_checks = 0
        self.players_updated = 0
        self.players_rendered = 0
        self.players_culled = 0

    def end_frame(self):
        """Mark the end of a frame and record total frame time"""
        frame_time = (time.time() - self.frame_start_time) * 1000  # Convert to ms
        self.section_times["total"].append(frame_time)

        # Add to totals
        self.total_collision_checks += self.collision_checks
        self.total_players_updated += self.players_updated
        self.total_players_rendered += self.players_rendered
        self.total_players_culled += self.players_culled

        # Check if we should log
        if time.time() - self.last_log_time >= self.log_interval:
            self._log_performance()
            self._reset_interval_stats()

    def start_section(self, section_name: str):
        """Mark the start of a timed section"""
        self.section_start_time = time.time()

    def end_section(self, section_name: str):
        """Mark the end of a timed section"""
        elapsed = (time.time() - self.section_start_time) * 1000  # Convert to ms
        if section_name in self.section_times:
            self.section_times[section_name].append(elapsed)

    def record_collision_checks(self, count: int):
        """Record number of collision checks this frame"""
        self.collision_checks = count

    def record_players_updated(self, count: int):
        """Record number of players updated this frame"""
        self.players_updated = count

    def record_players_rendered(self, rendered: int, culled: int):
        """Record number of players rendered vs culled this frame"""
        self.players_rendered = rendered
        self.players_culled = culled

    def get_current_fps(self) -> float:
        """Get current FPS (average of last 60 frames)"""
        if len(self.fps_samples) == 0:
            return 0.0
        return sum(self.fps_samples) / len(self.fps_samples)

    def get_average_time(self, section: str) -> float:
        """Get average time for a section over the interval"""
        if section not in self.section_times or len(self.section_times[section]) == 0:
            return 0.0
        return sum(self.section_times[section]) / len(self.section_times[section])

    def _log_performance(self):
        """Print performance statistics"""
        elapsed = time.time() - self.last_log_time
        frames_in_interval = len(self.section_times["total"])

        if frames_in_interval == 0:
            return

        # Calculate averages
        avg_fps = self.get_current_fps()
        avg_total = self.get_average_time("total")
        avg_update = self.get_average_time("update")
        avg_physics = self.get_average_time("physics")
        avg_render = self.get_average_time("render")

        # Calculate per-frame averages
        avg_collision_checks = self.total_collision_checks / frames_in_interval if frames_in_interval > 0 else 0
        avg_players_updated = self.total_players_updated / frames_in_interval if frames_in_interval > 0 else 0
        avg_players_rendered = self.total_players_rendered / frames_in_interval if frames_in_interval > 0 else 0
        avg_players_culled = self.total_players_culled / frames_in_interval if frames_in_interval > 0 else 0

        # Print summary
        print(f"\n{'='*70}")
        print(f"PERFORMANCE STATS ({elapsed:.1f}s interval, {frames_in_interval} frames)")
        print(f"{'='*70}")
        print(f"FPS: {avg_fps:.1f} | Frame Time: {avg_total:.2f}ms")
        print(f"  Update: {avg_update:.2f}ms | Physics: {avg_physics:.2f}ms | Render: {avg_render:.2f}ms")

        if self.enable_detailed_logging:
            print(f"\nDetailed Metrics:")
            print(f"  Collision Checks: {avg_collision_checks:.0f}/frame")
            print(f"  Players Updated: {avg_players_updated:.0f}/frame")
            print(f"  Players Rendered: {avg_players_rendered:.0f}/frame")
            print(f"  Players Culled: {avg_players_culled:.0f}/frame")

            # Calculate percentages
            total_visible = avg_players_rendered + avg_players_culled
            if total_visible > 0:
                cull_percentage = (avg_players_culled / total_visible) * 100
                print(f"  Culling Efficiency: {cull_percentage:.1f}% off-screen")

        print(f"{'='*70}\n")

    def _reset_interval_stats(self):
        """Reset statistics for next interval"""
        self.last_log_time = time.time()

        # Clear section times
        for key in self.section_times:
            self.section_times[key].clear()

        # Reset totals
        self.total_collision_checks = 0
        self.total_players_updated = 0
        self.total_players_rendered = 0
        self.total_players_culled = 0

    def get_summary(self) -> dict:
        """
        Get current performance summary as a dictionary

        Returns:
            Dictionary with current performance metrics
        """
        return {
            "fps": self.get_current_fps(),
            "avg_frame_time": self.get_average_time("total"),
            "avg_update_time": self.get_average_time("update"),
            "avg_physics_time": self.get_average_time("physics"),
            "avg_render_time": self.get_average_time("render"),
            "total_frames": self.frame_count
        }

    def __repr__(self):
        return f"PerformanceMonitor(fps={self.get_current_fps():.1f}, frames={self.frame_count})"
