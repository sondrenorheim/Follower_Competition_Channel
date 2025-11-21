"""
Video Recorder Module
Handles frame capture and video export using MoviePy
Generates and mixes audio from logged events
"""

import pygame
import numpy as np
from typing import List, Optional
import config
import os
import tempfile


class VideoRecorder:
    """
    Records game frames and exports them to MP4 video
    Optimized to capture at specified FPS for smaller file sizes
    """

    def __init__(self, output_path: str = None, fps: int = None, audio_logger=None):
        """
        Initialize video recorder

        Args:
            output_path: Path to save video file
            fps: Frames per second for export
            audio_logger: AudioLogger for tracking audio events
        """
        self.output_path = output_path or config.OUTPUT_VIDEO_PATH
        self.fps = fps or config.VIDEO_FPS
        self.frames: List[np.ndarray] = []
        self.recording = config.EXPORT_VIDEO

        # Time-based capture for accurate video speed
        self.frame_time = 1.0 / self.fps  # Time between frames in seconds
        self.next_capture_time = 0.0
        self.start_time = None

        # Audio logger for post-processing
        self.audio_logger = audio_logger

        print(f"📹 Video Recorder initialized: {self.output_path} @ {self.fps} FPS")
        print(f"   Using time-based capture (1 frame every {self.frame_time*1000:.1f}ms)")
        if audio_logger:
            print(f"🎤 Audio will be generated from logged events")

    def capture_frame(self, surface: pygame.Surface, current_time: float = None):
        """
        Capture a frame from the pygame surface using time-based sampling
        This ensures the video plays at the correct speed regardless of game FPS

        Args:
            surface: Pygame surface to capture
            current_time: Current time in seconds (uses time.time() if not provided)
        """
        if not self.recording:
            return

        # Initialize start time on first frame
        if self.start_time is None:
            import time
            self.start_time = current_time if current_time is not None else time.time()
            self.next_capture_time = 0.0

        # Calculate elapsed time
        import time
        elapsed = (current_time if current_time is not None else time.time()) - self.start_time

        # Check if it's time to capture a frame
        if elapsed >= self.next_capture_time:
            # Convert pygame surface to numpy array
            # pygame uses (width, height, 3) but we need (height, width, 3)
            frame = pygame.surfarray.array3d(surface)
            frame = np.transpose(frame, (1, 0, 2))  # Swap width and height

            self.frames.append(frame)

            # Schedule next capture
            self.next_capture_time += self.frame_time

            # Print progress every 100 frames
            if len(self.frames) % 100 == 0:
                duration = len(self.frames) / self.fps
                print(f"   Captured {len(self.frames)} frames ({duration:.1f}s of video)")

    def _generate_mixed_audio(self, video_duration: float) -> Optional[str]:
        """
        Generate mixed audio track from audio files (background music and countdown)
        Note: Video recording starts from countdown phase, so day/intro audio are not included

        Args:
            video_duration: Duration of the video in seconds

        Returns:
            Path to generated audio file or None
        """
        try:
            from pydub import AudioSegment

            print(f"🎵 Mixing audio tracks...")

            # Create silent audio track of video duration
            mixed_audio = AudioSegment.silent(duration=int(video_duration * 1000))

            # Audio file paths (cached WAV files)
            audio_files = {
                'background': 'assets/background_music.wav',
                'countdown': 'assets/countdown_audio.wav',
            }

            # 1. Add background music (looped, lower volume)
            if os.path.exists(audio_files['background']):
                print(f"   Adding background music...")
                bg_music = AudioSegment.from_wav(audio_files['background'])
                bg_music = bg_music - 12  # Reduce volume by 12dB

                # Loop background music to fill video duration
                video_duration_ms = int(video_duration * 1000)
                looped_bg = bg_music
                while len(looped_bg) < video_duration_ms:
                    looped_bg = looped_bg + bg_music

                # Trim to video duration
                looped_bg = looped_bg[:video_duration_ms]

                # Overlay background music
                mixed_audio = mixed_audio.overlay(looped_bg, position=0)
                print(f"   ✓ Background music added (looped)")

            # 2. Add countdown audio at the start (video starts from countdown phase)
            if os.path.exists(audio_files['countdown']):
                print(f"   Adding countdown audio...")
                countdown_audio = AudioSegment.from_wav(audio_files['countdown'])
                countdown_audio = countdown_audio + 3  # Boost volume slightly
                mixed_audio = mixed_audio.overlay(countdown_audio, position=0)
                print(f"   ✓ Countdown audio added at 0s")

            # Save final audio mix
            output_file = tempfile.mktemp(suffix='.wav')
            mixed_audio.export(output_file, format='wav')

            print(f"✅ Audio mixed successfully ({video_duration:.1f}s)")
            return output_file

        except ImportError:
            print(f"⚠️  pydub not installed. Install with: pip install pydub")
            return None
        except Exception as e:
            print(f"⚠️  Error mixing audio: {e}")
            import traceback
            traceback.print_exc()
            return None

    def export_video(self):
        """
        Export captured frames to MP4 video file using MoviePy
        Mixes all audio tracks (background music, intro, countdown)
        """
        if not self.recording or not self.frames:
            print("No frames to export")
            return

        try:
            print(f"\n🎬 Exporting video with {len(self.frames)} frames...")

            # Import MoviePy (only when needed to save startup time)
            from moviepy.editor import ImageSequenceClip, AudioFileClip

            # Create video clip from frames
            video_clip = ImageSequenceClip(list(self.frames), fps=self.fps)
            video_duration = video_clip.duration

            # Generate mixed audio from all audio files
            audio_file = self._generate_mixed_audio(video_duration)

            audio_clip = None
            has_audio = False

            if audio_file and os.path.exists(audio_file):
                try:
                    audio_clip = AudioFileClip(audio_file)

                    # Adjust audio duration to match video
                    if audio_clip.duration > video_duration:
                        audio_clip = audio_clip.subclip(0, video_duration)

                    # Set audio to video
                    video_clip = video_clip.set_audio(audio_clip)
                    has_audio = True
                    print(f"🎵 Audio track added to video ({audio_clip.duration:.1f}s)")

                except Exception as e:
                    print(f"⚠️  Could not add audio to video: {e}")
                    has_audio = False

            # Write video file
            video_clip.write_videofile(
                self.output_path,
                codec=config.VIDEO_CODEC,
                audio=has_audio,
                verbose=False,
                logger=None,  # Suppress MoviePy logs
                preset='medium',  # Encoding speed/quality tradeoff
                ffmpeg_params=['-pix_fmt', 'yuv420p']  # Better compatibility
            )

            # Clean up
            video_clip.close()
            if audio_clip:
                audio_clip.close()

            # Remove temporary audio file
            if audio_file and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                except:
                    pass

            duration = len(self.frames) / self.fps
            print(f"✅ Video exported successfully!")
            print(f"   File: {self.output_path}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Frames: {len(self.frames)}")
            print(f"   FPS: {self.fps}")
            print(f"   Audio: {'Yes' if has_audio else 'No'}")

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
        self.start_time = None
        self.next_capture_time = 0.0

    def __repr__(self):
        return f"VideoRecorder(frames={len(self.frames)}, duration={self.get_video_duration():.1f}s)"
