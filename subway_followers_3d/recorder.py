import os
import shutil
import tempfile
from pathlib import Path

import numpy as np


class PandaVideoRecorder:
    def __init__(self, base, output_path: str, fps: int, record: bool = True, audio_path: str | None = None):
        self.base = base
        self.output_path = output_path
        self.fps = fps
        self.record = record
        self.audio_path = audio_path
        self.frame_time = 1.0 / max(1, fps)
        self.next_capture_time = 0.0
        self.start_time = None

        self.use_streaming = False
        self.video_writer = None
        self.frame_count = 0
        self.frames = []

        if self.record:
            try:
                import cv2  # noqa: F401
                self.use_streaming = True
            except Exception:
                self.use_streaming = False

    def capture_frame(self, current_time: float):
        if not self.record:
            return

        if self.start_time is None:
            self.start_time = current_time
            self.next_capture_time = 0.0

        elapsed = current_time - self.start_time
        if elapsed < self.next_capture_time:
            return

        frame = self._grab_frame()
        if frame is None:
            return

        if self.use_streaming:
            self._write_frame_streaming(frame)
        else:
            self.frames.append(frame)
            self.frame_count = len(self.frames)

        self.next_capture_time += self.frame_time

    def _grab_frame(self):
        try:
            from panda3d.core import PNMImage
            pnm = PNMImage()
            if not self.base.win.getScreenshot(pnm):
                return None
            width = pnm.getXSize()
            height = pnm.getYSize()
            data = pnm.getRamImageAs("RGB")
            frame = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
            frame = np.flipud(frame)
            return frame
        except Exception:
            return None

    def _write_frame_streaming(self, frame: np.ndarray):
        import cv2

        if self.video_writer is None:
            temp_dir = tempfile.gettempdir()
            self.temp_video_path = os.path.join(temp_dir, f"panda_stream_{os.getpid()}.mp4")
            height, width = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(self.temp_video_path, fourcc, self.fps, (width, height))
            if not self.video_writer.isOpened():
                self.use_streaming = False
                self.frames.append(frame)
                return

        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self.video_writer.write(frame_bgr)
        self.frame_count += 1

    def finalize(self, include_audio: bool = True):
        if not self.record:
            return

        if self.use_streaming and self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            self._export_streaming_video(include_audio=include_audio)
        else:
            self._export_buffered_video(include_audio=include_audio)

    def _export_streaming_video(self, include_audio: bool = True):
        if not getattr(self, "temp_video_path", None) or not os.path.exists(self.temp_video_path):
            return

        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if include_audio and self._try_attach_audio(self.temp_video_path, output_path):
            pass
        else:
            shutil.copy2(self.temp_video_path, output_path)

        try:
            os.remove(self.temp_video_path)
        except Exception:
            pass

    def _export_buffered_video(self, include_audio: bool = True):
        if not self.frames:
            return

        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from moviepy.editor import ImageSequenceClip
            clip = ImageSequenceClip(self.frames, fps=self.fps)
            clip.write_videofile(str(output_path), codec="libx264", audio=False, verbose=False, logger=None)
            clip.close()
        except Exception:
            return

        if include_audio:
            self._try_attach_audio(str(output_path), output_path)

    def _try_attach_audio(self, video_path: str, output_path: Path) -> bool:
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip
            from moviepy.audio.fx.all import audio_loop
        except Exception:
            return False

        audio_path = None
        if self.audio_path:
            candidate = Path(self.audio_path)
            if candidate.exists():
                audio_path = candidate

        if audio_path is None:
            base_dir = Path(__file__).resolve().parents[1]
            wav_path = base_dir / "assets" / "sydney_tour_music.wav"
            m4a_path = base_dir / "assets" / "Sydney Tour Song adjusted.m4a"
            if wav_path.exists():
                audio_path = wav_path
            elif m4a_path.exists():
                audio_path = m4a_path
        if not audio_path:
            return False

        try:
            clip = VideoFileClip(video_path)
            audio = AudioFileClip(str(audio_path))
            if audio.duration < clip.duration:
                audio = audio_loop(audio, duration=clip.duration)
            else:
                audio = audio.subclip(0, clip.duration)
            clip = clip.set_audio(audio)
            clip.write_videofile(str(output_path), codec="libx264", audio_codec="aac", verbose=False, logger=None)
            clip.close()
            audio.close()
            return True
        except Exception:
            return False
