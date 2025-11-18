"""
Video Recorder Module
Handles frame capture and video export using MoviePy
"""

import pygame
import numpy as np
from typing import List, Optional
import config


class VideoRecorder:
    """
    Records game frames and exports them to MP4 video
    Optimized to capture at specified FPS for smaller file sizes
    """

    def __init__(self, output_path: str = None, fps: int = None):
        """
        Initialize video recorder

        Args:
            output_path: Path to save video file
            fps: Frames per second for export
        """
        self.output_path = output_path or config.OUTPUT_VIDEO_PATH
        self.fps = fps or config.VIDEO_FPS
        self.frames: List[np.ndarray] = []
        self.recording = config.EXPORT_VIDEO
        self.frame_interval = config.FPS / self.fps  # Capture every Nth frame
        self.frame_counter = 0

        print(f"📹 Video Recorder initialized: {self.output_path} @ {self.fps} FPS")
        print(f"   Capturing every {self.frame_interval:.1f} game frames")

    def capture_frame(self, surface: pygame.Surface):
        """
        Capture a frame from the pygame surface
        Only captures based on frame_interval to match target FPS

        Args:
            surface: Pygame surface to capture
        """
        if not self.recording:
            return

        self.frame_counter += 1

        # Only capture every Nth frame based on interval
        if self.frame_counter >= self.frame_interval:
            self.frame_counter = 0

            # Convert pygame surface to numpy array
            # pygame uses (width, height, 3) but we need (height, width, 3)
            frame = pygame.surfarray.array3d(surface)
            frame = np.transpose(frame, (1, 0, 2))  # Swap width and height

            self.frames.append(frame)

            # Print progress every 100 frames
            if len(self.frames) % 100 == 0:
                duration = len(self.frames) / self.fps
                print(f"   Captured {len(self.frames)} frames ({duration:.1f}s of video)")

    def export_video(self):
        """
        Export captured frames to MP4 video file using MoviePy
        """
        if not self.recording or not self.frames:
            print("No frames to export")
            return

        try:
            print(f"\n🎬 Exporting video with {len(self.frames)} frames...")

            # Import MoviePy (only when needed to save startup time)
            from moviepy.editor import ImageSequenceClip

            # Create video clip from frames
            clip = ImageSequenceClip(list(self.frames), fps=self.fps)

            # Write video file
            clip.write_videofile(
                self.output_path,
                codec=config.VIDEO_CODEC,
                audio=False,
                verbose=False,
                logger=None  # Suppress MoviePy logs
            )

            duration = len(self.frames) / self.fps
            print(f"✅ Video exported successfully!")
            print(f"   File: {self.output_path}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Frames: {len(self.frames)}")
            print(f"   FPS: {self.fps}")

        except Exception as e:
            print(f"❌ Error exporting video: {e}")
            print(f"   Make sure MoviePy and ffmpeg are installed correctly")

    def get_frame_count(self) -> int:
        """
        Get number of captured frames

        Returns:
            Number of frames
        """
        return len(self.frames)

    def get_video_duration(self) -> float:
        """
        Get estimated video duration in seconds

        Returns:
            Duration in seconds
        """
        return len(self.frames) / self.fps if self.frames else 0

    def clear_frames(self):
        """
        Clear all captured frames to free memory
        """
        self.frames.clear()
        self.frame_counter = 0

    def __repr__(self):
        return f"VideoRecorder(frames={len(self.frames)}, duration={self.get_video_duration():.1f}s)"
