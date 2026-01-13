"""
Video Recorder Module
Handles frame capture and video export using MoviePy
Generates and mixes audio from logged events
"""

import math
from pathlib import Path
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
        # Playback speed scaling during export (e.g., 0.5 = slow down 2x, 2.0 = speed up 2x)
        self.export_speed_factor = getattr(config, "EXPORT_SPEED_FACTOR", 1.0)
        self.frames: List[np.ndarray] = []
        self.recording = config.EXPORT_VIDEO

        # Streaming mode - write frames directly to disk (for long videos)
        self.use_streaming = getattr(config, "VIDEO_STREAMING_MODE", True)
        self.video_writer = None
        self.temp_video_path = None
        self.frame_count = 0

        # Time-based capture for accurate video speed
        self.frame_time = 1.0 / self.fps  # Time between frames in seconds
        self.next_capture_time = 0.0
        self.start_time = None

        # Audio logger for post-processing
        self.audio_logger = audio_logger
        self.background_music_start_time = None
        self.include_background_music = True
        self.music_segments = []

        # Custom countdown audio path (empty string disables countdown audio)
        if countdown_audio_path is None:
            self.countdown_audio_path = 'assets/countdown_audio.wav'
        else:
            self.countdown_audio_path = countdown_audio_path

        # Green screen overlay video (for obstacle course)
        self.greenscreen_video_path = None
        self.greenscreen_scale = 0.5  # Scale factor for overlay
        self.greenscreen_offset_y = 120  # Pixels to move down from center
        self.greenscreen_start_frame = None  # Frame index where countdown starts

        print(f"📹 Video Recorder initialized: {self.output_path} @ {self.fps} FPS")
        print(f"   Mode: {'Streaming (low memory)' if self.use_streaming else 'Buffered (high quality)'}")
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

            # Write frame based on mode
            if self.use_streaming:
                self._write_frame_streaming(frame)
            else:
                self.frames.append(frame)

            # Schedule next capture (only advance if not forced)
            if not force:
                self.next_capture_time += self.frame_time

            # Print progress every 100 frames
            frame_count = self.frame_count if self.use_streaming else len(self.frames)
            if frame_count % 100 == 0:
                duration = frame_count / self.fps
                print(f"   Captured {frame_count} frames ({duration:.1f}s of video)")

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

    def _write_frame_streaming(self, frame: np.ndarray):
        """
        Write frame directly to disk using OpenCV VideoWriter (streaming mode)

        Args:
            frame: Frame to write (height, width, 3) in RGB format
        """
        import cv2

        # Initialize video writer on first frame
        if self.video_writer is None:
            # Create temporary file for video
            import tempfile
            temp_dir = tempfile.gettempdir()
            self.temp_video_path = os.path.join(temp_dir, f"video_stream_{os.getpid()}.mp4")

            height, width = frame.shape[:2]

            # Use H264 codec for MP4 (widely compatible)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 'mp4v' works on all platforms

            self.video_writer = cv2.VideoWriter(
                self.temp_video_path,
                fourcc,
                self.fps,
                (width, height)
            )

            if not self.video_writer.isOpened():
                print(f"❌ Failed to initialize video writer")
                print(f"   Falling back to buffered mode")
                self.use_streaming = False
                self.frames.append(frame)
                return

            print(f"✅ Streaming video writer initialized: {self.temp_video_path}")

        # Convert RGB to BGR (OpenCV uses BGR)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Write frame
        self.video_writer.write(frame_bgr)
        self.frame_count += 1

    def _close_streaming_writer(self):
        """Close the streaming video writer"""
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            print(f"✅ Video stream closed: {self.frame_count} frames written")

    def _generate_elimination_sfx(self):
        """
        Generate elimination sound effect (descending tone)
        Returns pydub AudioSegment
        """
        try:
            from pydub import AudioSegment
            from pydub.generators import Sine
            import numpy as np

            # Create a descending tone (similar to the pygame version)
            duration_ms = 300  # 0.3 seconds
            start_freq = 800
            end_freq = 200

            # Generate frequency sweep
            samples = []
            sample_rate = 22050
            num_samples = int(sample_rate * duration_ms / 1000)

            for i in range(num_samples):
                t = i / sample_rate
                progress = i / num_samples
                freq = start_freq + (end_freq - start_freq) * progress
                envelope = (1 - progress) * 0.3  # Fade out

                # Generate sine wave
                value = int(32767 * envelope * np.sin(2 * np.pi * freq * t))
                samples.append(value)

            # Convert to bytes for pydub
            audio_data = np.array(samples, dtype=np.int16).tobytes()
            sfx = AudioSegment(
                data=audio_data,
                sample_width=2,  # 16-bit
                frame_rate=sample_rate,
                channels=1  # Mono
            )

            # Convert to stereo
            sfx = sfx.set_channels(2)
            return sfx

        except Exception as e:
            print(f"⚠️  Error generating elimination SFX: {e}")
            return None

    def _generate_impact_sfx(self, freq: int = 400, duration_ms: int = 80, volume: float = 0.5, decay: float = 0.7):
        """
        Generate impact sound effect (hit sounds for fighting games)
        Returns pydub AudioSegment
        """
        try:
            from pydub import AudioSegment
            import numpy as np

            sample_rate = 22050
            num_samples = int(sample_rate * duration_ms / 1000)
            samples = []

            for i in range(num_samples):
                t = i / sample_rate
                progress = i / num_samples
                envelope = volume * (1 - progress) ** decay

                # Mix sine wave with noise for punch feel
                sine_val = np.sin(2 * np.pi * freq * t)
                noise_val = np.random.uniform(-0.3, 0.3)
                value = int(32767 * envelope * (sine_val * 0.7 + noise_val * 0.3))
                samples.append(value)

            audio_data = np.array(samples, dtype=np.int16).tobytes()
            sfx = AudioSegment(
                data=audio_data,
                sample_width=2,
                frame_rate=sample_rate,
                channels=1
            )
            return sfx.set_channels(2)

        except Exception as e:
            return None

    def _generate_sweep_sfx(self, freq_start: int = 400, freq_end: int = 800, duration_ms: int = 100, volume: float = 0.5):
        """
        Generate frequency sweep sound effect (whoosh, charge-up sounds)
        Returns pydub AudioSegment
        """
        try:
            from pydub import AudioSegment
            import numpy as np

            sample_rate = 22050
            num_samples = int(sample_rate * duration_ms / 1000)
            samples = []

            for i in range(num_samples):
                t = i / sample_rate
                progress = i / num_samples
                freq = freq_start + (freq_end - freq_start) * progress
                envelope = volume * (1 - abs(progress - 0.5) * 0.5)  # Peak in middle

                value = int(32767 * envelope * np.sin(2 * np.pi * freq * t))
                samples.append(value)

            audio_data = np.array(samples, dtype=np.int16).tobytes()
            sfx = AudioSegment(
                data=audio_data,
                sample_width=2,
                frame_rate=sample_rate,
                channels=1
            )
            return sfx.set_channels(2)

        except Exception as e:
            return None

    def _generate_combat_sfx(self, sound_name: str):
        """
        Generate combat sound effect based on name
        Returns pydub AudioSegment or None
        """
        # Map sound names to generation parameters
        sfx_params = {
            'light_hit': ('impact', {'freq': 700, 'duration_ms': 50, 'volume': 0.4, 'decay': 0.8}),
            'heavy_hit': ('impact', {'freq': 180, 'duration_ms': 120, 'volume': 0.6, 'decay': 0.6}),
            'finisher_hit': ('impact', {'freq': 120, 'duration_ms': 150, 'volume': 0.7, 'decay': 0.5}),
            'ki_blast_fire': ('sweep', {'freq_start': 800, 'freq_end': 1200, 'duration_ms': 100, 'volume': 0.5}),
            'ki_blast_hit': ('impact', {'freq': 500, 'duration_ms': 80, 'volume': 0.5, 'decay': 0.7}),
            'block': ('impact', {'freq': 1000, 'duration_ms': 100, 'volume': 0.4, 'decay': 0.9}),
            'final_smash_charge': ('sweep', {'freq_start': 100, 'freq_end': 500, 'duration_ms': 500, 'volume': 0.6}),
            'final_smash_impact': ('impact', {'freq': 80, 'duration_ms': 300, 'volume': 0.8, 'decay': 0.5}),
            'teleport': ('sweep', {'freq_start': 400, 'freq_end': 800, 'duration_ms': 50, 'volume': 0.4}),
            'dash': ('impact', {'freq': 300, 'duration_ms': 80, 'volume': 0.3, 'decay': 0.9}),
            # New dynamic fight sounds
            'clash': ('impact', {'freq': 600, 'duration_ms': 150, 'volume': 0.7, 'decay': 0.6}),
            'counter_hit': ('impact', {'freq': 400, 'duration_ms': 100, 'volume': 0.6, 'decay': 0.7}),
            'desperation_activate': ('sweep', {'freq_start': 200, 'freq_end': 800, 'duration_ms': 300, 'volume': 0.6}),
        }

        if sound_name not in sfx_params:
            return None

        sfx_type, params = sfx_params[sound_name]

        if sfx_type == 'impact':
            return self._generate_impact_sfx(**params)
        elif sfx_type == 'sweep':
            return self._generate_sweep_sfx(**params)

        return None

    def _generate_mixed_audio(self, video_duration: float, export_fps: int) -> Optional[str]:
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
            }
            base_dir = Path(__file__).resolve().parents[1]
            background_path = Path(audio_files['background'])
            if not background_path.is_absolute():
                background_path = base_dir / background_path
            audio_files['background'] = str(background_path)

            countdown_path = None
            if self.countdown_audio_path:
                countdown_path = Path(self.countdown_audio_path)
                if not countdown_path.is_absolute():
                    countdown_path = base_dir / countdown_path
                countdown_path = str(countdown_path)

            # 1. Add background music (trimmed from beginning to sync ending)
            include_background = getattr(self, "include_background_music", True)
            if include_background and os.path.exists(audio_files['background']):
                print(f"   Adding background music...")
                bg_music = AudioSegment.from_wav(audio_files['background'])
                bg_music = bg_music - 12  # Reduce volume by 12dB

                video_duration_ms = int(video_duration * 1000)
                bg_duration_ms = len(bg_music)
                bg_start_ms = 0
                if self.background_music_start_time is not None:
                    bg_start_ms = max(0, int(self.background_music_start_time * 1000))

                if bg_start_ms >= video_duration_ms:
                    print("   Background music start is after video end; skipping music")
                else:
                    available_duration_ms = video_duration_ms - bg_start_ms

                    # If video segment is longer than music, we need to loop
                    # If video segment is shorter than music, we trim from the beginning
                    if available_duration_ms > bg_duration_ms:
                        # Loop background music to fill video duration
                        print(f"   Background music shorter than video, looping...")
                        looped_bg = bg_music
                        while len(looped_bg) < available_duration_ms:
                            looped_bg = looped_bg + bg_music

                        # Trim from beginning to keep the ending
                        # We want the last available_duration_ms of the looped music
                        start_trim = len(looped_bg) - available_duration_ms
                        looped_bg = looped_bg[start_trim:]
                    else:
                        # Music is longer than segment, trim from beginning to keep ending
                        print(f"   Trimming {(bg_duration_ms - available_duration_ms)/1000:.2f}s from beginning of music...")
                        start_trim = bg_duration_ms - available_duration_ms
                        looped_bg = bg_music[start_trim:]

                    # Overlay background music at the requested offset
                    mixed_audio = mixed_audio.overlay(looped_bg, position=bg_start_ms)
                    if bg_start_ms > 0:
                        print(f"   Background music added at {bg_start_ms/1000:.1f}s (ending synced)")
                    else:
                        print(f"   Background music added (ending synced)")
            elif not include_background:
                print("   Background music disabled for this export")

            # 2. Add custom music segments (if any)
            music_segments = getattr(self, "music_segments", [])
            if music_segments:
                print(f"   Adding {len(music_segments)} custom music segment(s)...")
            for segment in music_segments:
                if not isinstance(segment, dict):
                    continue
                path = segment.get("path", "")
                if not path or not os.path.exists(path):
                    print(f"   Warning: music segment not found: {path}")
                    continue

                start_time = float(segment.get("start", 0.0))
                end_time = segment.get("end", None)
                if end_time is None:
                    end_time = video_duration
                else:
                    end_time = float(end_time)

                if start_time >= video_duration:
                    continue
                if end_time <= start_time:
                    continue

                start_ms = max(0, int(start_time * 1000))
                end_ms = max(start_ms, int(min(end_time, video_duration) * 1000))
                segment_duration_ms = end_ms - start_ms
                if segment_duration_ms <= 0:
                    continue

                segment_audio = AudioSegment.from_file(path)
                volume_scale = segment.get("volume", 1.0)
                try:
                    volume_scale = float(volume_scale)
                except (TypeError, ValueError):
                    volume_scale = 1.0
                volume_scale = max(0.001, volume_scale)
                volume_db = 20 * math.log10(volume_scale)
                segment_audio = segment_audio + volume_db

                if len(segment_audio) < segment_duration_ms:
                    loops = segment_duration_ms // max(1, len(segment_audio)) + 1
                    segment_audio = (segment_audio * loops)[:segment_duration_ms]
                else:
                    segment_audio = segment_audio[:segment_duration_ms]

                mixed_audio = mixed_audio.overlay(segment_audio, position=start_ms)

            # 3. Add countdown audio at the correct position (when countdown actually starts)
            if countdown_path and os.path.isfile(countdown_path):
                print(f"   Adding countdown audio...")
                countdown_audio = AudioSegment.from_wav(countdown_path)
                countdown_audio = countdown_audio + 3  # Boost volume slightly

                # Calculate countdown start position in milliseconds
                countdown_start_frame = self.greenscreen_start_frame if self.greenscreen_start_frame is not None else 0
                countdown_start_time_ms = int((countdown_start_frame / export_fps) * 1000)

                mixed_audio = mixed_audio.overlay(countdown_audio, position=countdown_start_time_ms)
                print(f"   ✓ Countdown audio added at {countdown_start_time_ms/1000:.1f}s (frame {countdown_start_frame})")

            # 3. Add sound effects from audio logger
            if self.audio_logger and hasattr(self.audio_logger, 'events'):
                sound_effects = [e for e in self.audio_logger.events if e.event_type == 'sound_effect']
                if sound_effects:
                    print(f"   Adding {len(sound_effects)} sound effects...")
                    sfx_added = 0
                    for event in sound_effects:
                        sound_name = event.data.get('sound_name', '')
                        timestamp_ms = int(event.timestamp * 1000)
                        volume_db = event.data.get('volume', 1.0)

                        # Skip if timestamp is beyond video duration
                        if timestamp_ms >= int(video_duration * 1000):
                            continue

                        sfx = None

                        # Generate elimination sound effect
                        if sound_name == 'elimination':
                            sfx = self._generate_elimination_sfx()
                        else:
                            # Try to generate combat sound effect
                            sfx = self._generate_combat_sfx(sound_name)

                        if sfx:
                            # Adjust volume
                            sfx = sfx + (20 * (volume_db - 1.0))  # Convert to dB adjustment
                            mixed_audio = mixed_audio.overlay(sfx, position=timestamp_ms)
                            sfx_added += 1

                    print(f"   ✓ {sfx_added} sound effects added")

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

    def _apply_greenscreen_overlay(self, frames: List[np.ndarray], export_fps: int) -> List[np.ndarray]:
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

            # Calculate how many output frames the overlay covers (respect export fps)
            overlay_frame_count = int(gs_duration * export_fps)
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
        # Close streaming writer if active
        if self.use_streaming and self.video_writer is not None:
            self._close_streaming_writer()

        # Handle streaming mode differently
        if self.use_streaming:
            return self._export_streaming_video()

        if not self.recording or not self.frames:
            print("No frames to export")
            return

        try:
            print(f"\n🎬 Exporting video with {len(self.frames)} frames...")
            print(f"   Greenscreen path configured: {self.greenscreen_video_path}")

            # Import MoviePy (only when needed to save startup time)
            from moviepy.editor import ImageSequenceClip, AudioFileClip

            # Adjust playback speed by scaling the fps used for export
            out_fps = max(1, int(self.fps * self.export_speed_factor))

            # Apply green screen overlay if set (needs export fps for timing)
            frames_to_export = self._apply_greenscreen_overlay(list(self.frames), out_fps)

            # Create video clip from frames
            video_clip = ImageSequenceClip(frames_to_export, fps=out_fps)
            video_duration = video_clip.duration

            # Generate mixed audio from all audio files
            audio_file = self._generate_mixed_audio(video_duration, out_fps)

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

    def _export_streaming_video(self):
        """
        Export video in streaming mode (already written to temp file)
        Only adds audio and moves to final location
        """
        if self.temp_video_path is None or not os.path.exists(self.temp_video_path):
            print("❌ No streaming video file found")
            return

        try:
            print(f"\n🎬 Exporting streaming video...")
            print(f"   Frames: {self.frame_count}")
            print(f"   Duration: {self.frame_count / self.fps:.1f}s")

            # If audio is needed, use MoviePy to add it
            if self.audio_logger:
                from moviepy.editor import VideoFileClip, AudioFileClip

                video_duration = self.frame_count / self.fps
                audio_file = self._generate_mixed_audio(video_duration, self.fps)

                if audio_file and os.path.exists(audio_file):
                    try:
                        video_clip = VideoFileClip(self.temp_video_path)
                        audio_clip = AudioFileClip(audio_file)

                        # Adjust audio duration to match video
                        if audio_clip.duration > video_duration:
                            audio_clip = audio_clip.subclip(0, video_duration)

                        video_clip = video_clip.set_audio(audio_clip)
                        video_clip.write_videofile(
                            self.output_path,
                            codec='libx264',
                            audio_codec='aac',
                            temp_audiofile='temp-audio.m4a',
                            remove_temp=True,
                            logger=None
                        )

                        video_clip.close()
                        audio_clip.close()

                        # Remove temp audio file
                        if os.path.exists(audio_file):
                            os.remove(audio_file)

                        print(f"🎵 Audio track added to video")

                    except Exception as e:
                        print(f"⚠️  Could not add audio: {e}")
                        print(f"   Copying video without audio")
                        import shutil
                        shutil.copy2(self.temp_video_path, self.output_path)
                else:
                    # No audio - just copy the file
                    import shutil
                    shutil.copy2(self.temp_video_path, self.output_path)
            else:
                # No audio needed - just move the file
                import shutil
                shutil.copy2(self.temp_video_path, self.output_path)

            # Clean up temp file
            if os.path.exists(self.temp_video_path):
                os.remove(self.temp_video_path)
                self.temp_video_path = None

            print(f"✅ Video exported successfully!")
            print(f"   File: {self.output_path}")
            print(f"   Duration: {self.frame_count / self.fps:.1f}s")
            print(f"   Frames: {self.frame_count}")
            print(f"   FPS: {self.fps}")
            print(f"   Mode: Streaming (low memory)")

        except Exception as e:
            print(f"❌ Error exporting streaming video: {e}")
            import traceback
            traceback.print_exc()

    def get_frame_count(self) -> int:
        """
        Get number of captured frames

        Returns:
            Number of frames
        """
        return self.frame_count if self.use_streaming else len(self.frames)

    def finalize(self):
        """
        Finalize the recording safely.
        - If recording is disabled or no frames were captured, do nothing.
        - Otherwise export the video and expose the saved path as `video_path`
          for callers that expect it.
        - Always clear frames afterward to free memory.
        """
        if not self.recording:
            return

        # Expose a stable path attribute for callers (some use `video_path`)
        self.video_path = getattr(self, "output_path", None)

        try:
            self.export_video()
        finally:
            self.clear_frames()

    def get_video_duration(self) -> float:
        """
        Get estimated video duration in seconds

        Returns:
            Duration in seconds
        """
        frame_count = self.frame_count if self.use_streaming else len(self.frames)
        return frame_count / self.fps if frame_count > 0 else 0

    def clear_frames(self):
        """
        Clear all captured frames to free memory
        """
        self.frames.clear()
        self.start_time = None
        self.next_capture_time = 0.0

    def __repr__(self):
        return f"VideoRecorder(frames={len(self.frames)}, duration={self.get_video_duration():.1f}s)"
