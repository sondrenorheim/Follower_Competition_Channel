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

    def __init__(self, output_path: str = None, fps: int = None, audio_logger=None, countdown_audio_path: str = None):
        """
        Initialize video recorder

        Args:
            output_path: Path to save video file
            fps: Frames per second for export
            audio_logger: AudioLogger for tracking audio events
            countdown_audio_path: Custom path to countdown audio file (default: assets/countdown_audio.wav)
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

        # Custom countdown audio path
        self.countdown_audio_path = countdown_audio_path or 'assets/countdown_audio.wav'

        # Green screen overlay video (for obstacle course)
        self.greenscreen_video_path = None
        self.greenscreen_scale = 0.5  # Scale factor for overlay
        self.greenscreen_offset_y = 120  # Pixels to move down from center
        self.greenscreen_start_frame = None  # Frame index where countdown starts

        print(f"📹 Video Recorder initialized: {self.output_path} @ {self.fps} FPS")
        print(f"   Using time-based capture (1 frame every {self.frame_time*1000:.1f}ms)")

        if config.UPSCALE_VIDEO and config.UPSCALE_FACTOR > 1.0:
            output_width = int(config.SCREEN_WIDTH * config.UPSCALE_FACTOR)
            output_height = int(config.SCREEN_HEIGHT * config.UPSCALE_FACTOR)
            print(f"🔍 Upscaling enabled: {config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT} -> {output_width}x{output_height} ({config.UPSCALE_FACTOR}x)")

        if audio_logger:
            print(f"🎤 Audio will be generated from logged events")

    def capture_frame(self, surface: pygame.Surface, current_time: float = None, force: bool = False):
        """
        Capture a frame from the pygame surface using time-based sampling
        This ensures the video plays at the correct speed regardless of game FPS

        Args:
            surface: Pygame surface to capture
            current_time: Current time in seconds (uses time.time() if not provided)
            force: If True, capture this frame regardless of timing (useful for countdown sync)
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

        # Check if it's time to capture a frame (or if forced)
        if force or elapsed >= self.next_capture_time:
            # Convert pygame surface to numpy array
            # pygame uses (width, height, 3) but we need (height, width, 3)
            frame = pygame.surfarray.array3d(surface)
            frame = np.transpose(frame, (1, 0, 2))  # Swap width and height

            # Upscale frame if enabled
            if config.UPSCALE_VIDEO and config.UPSCALE_FACTOR > 1.0:
                frame = self._upscale_frame(frame, config.UPSCALE_FACTOR)

            self.frames.append(frame)

            # Schedule next capture (only advance if not forced)
            if not force:
                self.next_capture_time += self.frame_time

            # Print progress every 100 frames
            if len(self.frames) % 100 == 0:
                duration = len(self.frames) / self.fps
                print(f"   Captured {len(self.frames)} frames ({duration:.1f}s of video)")

    def _upscale_frame(self, frame: np.ndarray, scale_factor: float) -> np.ndarray:
        """
        Upscale a frame using high-quality interpolation

        Args:
            frame: Input frame as numpy array (height, width, 3)
            scale_factor: Scaling factor (e.g., 2.0 for 2x upscale)

        Returns:
            Upscaled frame
        """
        try:
            # Use OpenCV for high-quality upscaling (LANCZOS interpolation)
            import cv2
            height, width = frame.shape[:2]
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            upscaled = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            return upscaled
        except ImportError:
            # Fallback to scipy if OpenCV not available
            try:
                from scipy.ndimage import zoom
                upscaled = zoom(frame, (scale_factor, scale_factor, 1), order=3)
                return upscaled.astype(np.uint8)
            except ImportError:
                # Final fallback: use numpy simple repeat (blocky but works)
                print("⚠️  Warning: opencv-python or scipy not installed. Using simple upscaling.")
                print("   Install opencv-python for better quality: pip install opencv-python")
                upscaled = np.repeat(np.repeat(frame, int(scale_factor), axis=0), int(scale_factor), axis=1)
                return upscaled

    def _generate_mixed_audio(self, video_duration: float) -> Optional[str]:
        """
        Generate mixed audio track from audio files (background music and countdown)
        Note: Video recording starts from countdown phase, so day/intro audio are not included

        The background music is trimmed from the BEGINNING so that the ending of the audio
        lines up perfectly with the end of the video (since outro is always 5.27s).

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
                'background': 'assets/sydney_tour_music.wav',
                'countdown': self.countdown_audio_path,
            }

            # 1. Add background music (trimmed from beginning to sync ending)
            if os.path.exists(audio_files['background']):
                print(f"   Adding background music...")
                bg_music = AudioSegment.from_wav(audio_files['background'])
                bg_music = bg_music - 12  # Reduce volume by 12dB

                video_duration_ms = int(video_duration * 1000)
                bg_duration_ms = len(bg_music)

                # If video is longer than music, we need to loop
                # If video is shorter than music, we trim from the beginning
                if video_duration_ms > bg_duration_ms:
                    # Loop background music to fill video duration
                    print(f"   Background music shorter than video, looping...")
                    looped_bg = bg_music
                    while len(looped_bg) < video_duration_ms:
                        looped_bg = looped_bg + bg_music

                    # Trim from beginning to keep the ending
                    # We want the last video_duration_ms of the looped music
                    start_trim = len(looped_bg) - video_duration_ms
                    looped_bg = looped_bg[start_trim:]
                else:
                    # Music is longer than video, trim from beginning to keep ending
                    print(f"   Trimming {(bg_duration_ms - video_duration_ms)/1000:.2f}s from beginning of music...")
                    start_trim = bg_duration_ms - video_duration_ms
                    looped_bg = bg_music[start_trim:]

                # Overlay background music
                mixed_audio = mixed_audio.overlay(looped_bg, position=0)
                print(f"   ✓ Background music added (ending synced)")

            # 2. Add countdown audio at the correct position (when countdown actually starts)
            if os.path.exists(audio_files['countdown']):
                print(f"   Adding countdown audio...")
                countdown_audio = AudioSegment.from_wav(audio_files['countdown'])
                countdown_audio = countdown_audio + 3  # Boost volume slightly

                # Calculate countdown start position in milliseconds
                countdown_start_frame = self.greenscreen_start_frame if self.greenscreen_start_frame is not None else 0
                countdown_start_time_ms = int((countdown_start_frame / self.fps) * 1000)

                mixed_audio = mixed_audio.overlay(countdown_audio, position=countdown_start_time_ms)
                print(f"   ✓ Countdown audio added at {countdown_start_time_ms/1000:.1f}s (frame {countdown_start_frame})")

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

    def set_greenscreen_overlay(self, video_path: str, scale: float = 0.5, offset_y: int = 120):
        """
        Set a green screen video to overlay on the first frames during export

        Args:
            video_path: Path to the green screen video file
            scale: Scale factor for the overlay (0.5 = 50% size)
            offset_y: Pixels to offset down from center
        """
        self.greenscreen_video_path = video_path
        self.greenscreen_scale = scale
        self.greenscreen_offset_y = offset_y
        print(f"🎬 Green screen overlay set: {video_path}")

    def mark_countdown_start(self):
        """Mark the current frame as the start of the countdown for green screen overlay"""
        self.greenscreen_start_frame = len(self.frames)
        print(f"🎬 Countdown start marked at frame {self.greenscreen_start_frame}")

    def _apply_greenscreen_overlay(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        """
        Apply green screen video overlay starting from the countdown start frame

        Args:
            frames: List of frames to modify

        Returns:
            Modified frames with green screen overlay
        """
        if not self.greenscreen_video_path or not os.path.exists(self.greenscreen_video_path):
            print(f"⚠️  Green screen video not found: {self.greenscreen_video_path}")
            return frames

        # If countdown start frame not marked, default to frame 0
        start_frame_idx = self.greenscreen_start_frame if self.greenscreen_start_frame is not None else 0

        try:
            import cv2

            print(f"🎬 Applying green screen overlay: {self.greenscreen_video_path}")
            print(f"   Starting from frame {start_frame_idx}")

            # Open the green screen video
            gs_video = cv2.VideoCapture(self.greenscreen_video_path)

            if not gs_video.isOpened():
                print(f"⚠️  Could not open green screen video: {self.greenscreen_video_path}")
                return frames

            gs_fps = gs_video.get(cv2.CAP_PROP_FPS)
            gs_frame_count = int(gs_video.get(cv2.CAP_PROP_FRAME_COUNT))
            gs_duration = gs_frame_count / gs_fps

            # Calculate how many output frames the overlay covers
            overlay_frame_count = int(gs_duration * self.fps)
            # Ensure we don't exceed available frames after start point
            overlay_frame_count = min(overlay_frame_count, len(frames) - start_frame_idx)

            print(f"   Overlay duration: {gs_duration:.1f}s ({overlay_frame_count} frames)")
            print(f"   Green screen video: {gs_frame_count} frames @ {gs_fps:.1f} FPS")

            # Get frame dimensions
            frame_height, frame_width = frames[0].shape[:2]
            print(f"   Output frame size: {frame_width}x{frame_height}")

            # Get green screen video dimensions
            gs_orig_w = int(gs_video.get(cv2.CAP_PROP_FRAME_WIDTH))
            gs_orig_h = int(gs_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"   Green screen original size: {gs_orig_w}x{gs_orig_h}")

            # Calculate scale to fit overlay within frame while respecting user's scale preference
            # The user's scale is relative to the frame width
            # E.g., scale=0.75 means overlay should be 75% of frame width
            target_width = int(frame_width * self.greenscreen_scale)

            # Calculate the actual scale factor to apply to the green screen video
            actual_scale = target_width / gs_orig_w

            # Account for video upscaling for offset
            upscale_factor = config.UPSCALE_FACTOR if config.UPSCALE_VIDEO else 1.0
            adjusted_offset_y = int(self.greenscreen_offset_y * upscale_factor)

            print(f"   Target overlay width: {target_width}px ({self.greenscreen_scale*100:.0f}% of frame)")
            print(f"   Actual scale factor: {actual_scale:.3f}")
            print(f"   Overlay offset_y: {self.greenscreen_offset_y} -> {adjusted_offset_y}")

            # Process each frame that needs overlay (starting from countdown start frame)
            for i in range(overlay_frame_count):
                # Calculate actual frame index in the frames array
                frame_idx = start_frame_idx + i

                # Calculate which green screen frame to use
                gs_frame_idx = int((i / overlay_frame_count) * gs_frame_count)
                gs_video.set(cv2.CAP_PROP_POS_FRAMES, gs_frame_idx)
                ret, gs_frame = gs_video.read()

                if not ret:
                    continue

                # Convert BGR to RGB
                gs_frame = cv2.cvtColor(gs_frame, cv2.COLOR_BGR2RGB)

                # Scale the green screen frame to fit within output frame
                gs_h, gs_w = gs_frame.shape[:2]
                new_w = int(gs_w * actual_scale)
                new_h = int(gs_h * actual_scale)
                gs_frame = cv2.resize(gs_frame, (new_w, new_h))

                # Apply chroma key (remove green)
                gs_hsv = cv2.cvtColor(gs_frame, cv2.COLOR_RGB2HSV)
                lower_green = np.array([35, 80, 80])
                upper_green = np.array([85, 255, 255])
                mask = cv2.inRange(gs_hsv, lower_green, upper_green)

                # Dilate mask to catch green edges
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.dilate(mask, kernel, iterations=2)

                # Create alpha channel (inverted mask)
                alpha = cv2.bitwise_not(mask)
                alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

                # Calculate position (centered horizontally, offset vertically with upscale adjustment)
                x_pos = (frame_width - new_w) // 2
                y_pos = (frame_height - new_h) // 2 + adjusted_offset_y

                # Handle overlay larger than frame by cropping
                # Calculate the region of the overlay that fits in the frame
                overlay_x_start = 0
                overlay_y_start = 0
                overlay_x_end = new_w
                overlay_y_end = new_h

                # Crop left edge if overlay extends past left of frame
                if x_pos < 0:
                    overlay_x_start = -x_pos
                    x_pos = 0

                # Crop top edge if overlay extends past top of frame
                if y_pos < 0:
                    overlay_y_start = -y_pos
                    y_pos = 0

                # Crop right edge if overlay extends past right of frame
                if x_pos + (overlay_x_end - overlay_x_start) > frame_width:
                    overlay_x_end = overlay_x_start + (frame_width - x_pos)

                # Crop bottom edge if overlay extends past bottom of frame
                if y_pos + (overlay_y_end - overlay_y_start) > frame_height:
                    overlay_y_end = overlay_y_start + (frame_height - y_pos)

                # Get the cropped overlay region
                cropped_gs = gs_frame[overlay_y_start:overlay_y_end, overlay_x_start:overlay_x_end]
                cropped_alpha = alpha[overlay_y_start:overlay_y_end, overlay_x_start:overlay_x_end]

                # Calculate destination region size
                dest_h, dest_w = cropped_gs.shape[:2]

                # Blend the green screen frame onto the game frame
                frame = frames[frame_idx].copy()
                for c in range(3):
                    frame[y_pos:y_pos+dest_h, x_pos:x_pos+dest_w, c] = (
                        frame[y_pos:y_pos+dest_h, x_pos:x_pos+dest_w, c] * (1 - cropped_alpha/255.0) +
                        cropped_gs[:, :, c] * (cropped_alpha/255.0)
                    ).astype(np.uint8)

                frames[frame_idx] = frame

            gs_video.release()
            print(f"   ✓ Green screen overlay applied to {overlay_frame_count} frames")
            return frames

        except Exception as e:
            print(f"⚠️  Error applying green screen overlay: {e}")
            import traceback
            traceback.print_exc()
            return frames

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
            print(f"   Greenscreen path configured: {self.greenscreen_video_path}")

            # Apply green screen overlay if set
            frames_to_export = self._apply_greenscreen_overlay(list(self.frames))

            # Import MoviePy (only when needed to save startup time)
            from moviepy.editor import ImageSequenceClip, AudioFileClip

            # Create video clip from frames
            video_clip = ImageSequenceClip(frames_to_export, fps=self.fps)
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
