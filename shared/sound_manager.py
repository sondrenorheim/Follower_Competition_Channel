"""
Sound Manager Module
Handles all sound effects and music for the battle royale game
"""

import hashlib
import math
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pygame

import config


class SoundManager:
    """
    Manages sound effects and background music
    Generates synthetic sounds using pygame.sndarray
    """

    def __init__(self, audio_logger=None):
        """
        Initialize the sound manager

        Args:
            audio_logger: Optional AudioLogger for logging events
        """
        # Initialize pygame mixer
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

        # Sound channels
        self.sfx_channel = pygame.mixer.Channel(0)
        self.music_channel = pygame.mixer.Channel(1)
        self.announcer_channel = pygame.mixer.Channel(2)

        # Mute local playback when running headless or when explicitly requested.
        headless = getattr(config, 'HEADLESS_MODE', False)
        mute_local_audio = getattr(config, 'MUTE_LOCAL_GAME_AUDIO', False)
        self.local_audio_muted = bool(headless or mute_local_audio)

        # Volume settings (audio logger still works even when local playback is muted)
        self.master_volume = 0.0 if self.local_audio_muted else 0.5
        self.sfx_volume = 0.0 if self.local_audio_muted else 0.7
        self.music_volume = 0.0 if self.local_audio_muted else 0.3
        self.announcer_volume = 0.0 if self.local_audio_muted else 0.8

        # Background music volume levels
        self.music_volume_low = 0.0 if self.local_audio_muted else 0.15   # During announcer speaking
        self.music_volume_high = 0.0 if self.local_audio_muted else 0.4   # During gameplay
        self.current_music_volume = self.music_volume_low
        self.target_music_volume = self.music_volume_low

        # Music intensity (0.0 to 1.0)
        self.music_intensity = 0.0
        self.target_intensity = 0.0

        # Background music file
        self.background_music_path = "assets/Sydney Tour Song adjusted.m4a"
        self.music_playing = False

        # Audio durations (will be set when audio is loaded)
        self.intro_audio_duration = 3.0  # Default fallback
        self.countdown_audio_duration = 5.36  # Default fallback

        # Sound effect cache
        self.sounds = {}
        self._generate_sound_effects()

        # Preloaded audio
        self.day_sound = None
        self.intro_sound = None
        self.countdown_sound = None
        self.smash_countdown_sound = None
        self.smash_countdown_duration = 0.0
        self.day_audio_duration = 0.5  # Default fallback

        # Background music
        self.base_bpm = 120
        self.current_music = None

        # Announcements
        self.last_announcement = ""

        # TTS engine
        self.tts_engine = None
        self._init_tts()

        # Audio logger for event tracking
        self.audio_logger = audio_logger

    def _generate_sound_effects(self):
        """
        Generate synthetic sound effects using numpy
        """
        try:
            # Elimination sound - descending pitch
            self.sounds['elimination'] = self._generate_elimination_sound()

            # Collision sound - short pop
            self.sounds['collision'] = self._generate_collision_sound()

            # Zone warning - alarm beep
            self.sounds['zone_warning'] = self._generate_zone_warning_sound()

            # Announcement fanfare - ascending notes
            self.sounds['announcement'] = self._generate_announcement_sound()

            # Winner celebration - triumphant chord
            self.sounds['winner'] = self._generate_winner_sound()

        except Exception as e:
            print(f"⚠️  Warning: Could not generate sound effects: {e}")
            print("   Game will continue without sound")

    def _generate_tone(self, frequency: float, duration: float,
                      sample_rate: int = 22050, volume: float = 0.3) -> pygame.Surface:
        """
        Generate a simple tone

        Args:
            frequency: Frequency in Hz
            duration: Duration in seconds
            sample_rate: Sample rate in Hz
            volume: Volume (0.0 to 1.0)

        Returns:
            Pygame Sound object
        """
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * volume)

        for i in range(num_samples):
            t = i / sample_rate
            value = int(max_amplitude * math.sin(2 * math.pi * frequency * t))
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_elimination_sound(self) -> pygame.Surface:
        """Generate elimination sound effect (descending tone)"""
        duration = 0.3
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * 0.2)

        for i in range(num_samples):
            t = i / sample_rate
            # Descending frequency from 800 Hz to 200 Hz
            freq = 800 - (600 * t / duration)
            # Envelope (fade out)
            envelope = 1.0 - (t / duration)
            value = int(max_amplitude * envelope * math.sin(2 * math.pi * freq * t))
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_collision_sound(self) -> pygame.Surface:
        """Generate collision sound effect (short pop)"""
        duration = 0.1
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * 0.15)

        for i in range(num_samples):
            t = i / sample_rate
            # Mix of frequencies for "thud" sound
            freq1 = 150
            freq2 = 300
            envelope = 1.0 - (t / duration)
            value = int(max_amplitude * envelope * (
                math.sin(2 * math.pi * freq1 * t) * 0.7 +
                math.sin(2 * math.pi * freq2 * t) * 0.3
            ))
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_zone_warning_sound(self) -> pygame.Surface:
        """Generate zone warning sound (alarm beep)"""
        duration = 0.2
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * 0.25)
        freq = 1000  # High pitched beep

        for i in range(num_samples):
            t = i / sample_rate
            # Square wave for alarm effect
            value = max_amplitude if math.sin(2 * math.pi * freq * t) > 0 else -max_amplitude
            # Envelope
            envelope = 1.0 if t < duration * 0.5 else (1.0 - (t - duration * 0.5) / (duration * 0.5))
            value = int(value * envelope * 0.5)
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_announcement_sound(self) -> pygame.Surface:
        """Generate announcement fanfare (ascending notes)"""
        duration = 0.5
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * 0.3)

        for i in range(num_samples):
            t = i / sample_rate
            # Ascending arpeggio
            freq = 400 + (t / duration) * 400
            envelope = math.sin(math.pi * t / duration)  # Bell curve
            value = int(max_amplitude * envelope * math.sin(2 * math.pi * freq * t))
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_winner_sound(self) -> pygame.Surface:
        """Generate winner celebration (triumphant chord)"""
        duration = 1.0
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * 0.25)

        # Major chord frequencies (C major: C-E-G)
        frequencies = [523, 659, 784]

        for i in range(num_samples):
            t = i / sample_rate
            envelope = 1.0 if t < 0.1 else (1.0 - (t - 0.1) / 0.9)
            value = 0
            for freq in frequencies:
                value += math.sin(2 * math.pi * freq * t) / len(frequencies)
            value = int(max_amplitude * envelope * value)
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def play_elimination(self):
        """Play elimination sound effect"""
        if 'elimination' in self.sounds:
            sound = self.sounds['elimination']
            volume = self.sfx_volume * self.master_volume
            sound.set_volume(volume)
            self.sfx_channel.play(sound)

            # Log to audio logger for video export
            if self.audio_logger:
                self.audio_logger.log_sound_effect('elimination', volume)

    def play_collision(self):
        """Play collision sound effect"""
        if 'collision' in self.sounds and not self.sfx_channel.get_busy():
            sound = self.sounds['collision']
            sound.set_volume(self.sfx_volume * self.master_volume * 0.5)
            self.sfx_channel.play(sound)

    def play_zone_warning(self):
        """Play zone warning sound"""
        if 'zone_warning' in self.sounds:
            sound = self.sounds['zone_warning']
            sound.set_volume(self.sfx_volume * self.master_volume)
            self.sfx_channel.play(sound)

    def play_announcement(self, announcement_type: str):
        """
        Play announcement sound

        Args:
            announcement_type: Type of announcement ("top10", "final_survivor", etc)
        """
        if self.last_announcement == announcement_type:
            return  # Don't repeat same announcement

        self.last_announcement = announcement_type

        if 'announcement' in self.sounds:
            sound = self.sounds['announcement']
            sound.set_volume(self.announcer_volume * self.master_volume)
            self.announcer_channel.play(sound)

    def play_winner_celebration(self):
        """Play winner celebration sound"""
        if 'winner' in self.sounds:
            sound = self.sounds['winner']
            sound.set_volume(self.announcer_volume * self.master_volume)
            self.announcer_channel.play(sound)

    def update_music_intensity(self, alive_count: int, total_count: int):
        """
        Update background music intensity based on game state

        Args:
            alive_count: Number of alive followers
            total_count: Total number of followers
        """
        # Intensity increases as fewer followers remain
        survival_ratio = alive_count / total_count if total_count > 0 else 0
        self.target_intensity = 1.0 - survival_ratio

        # Smooth transition
        if self.music_intensity < self.target_intensity:
            self.music_intensity = min(self.target_intensity, self.music_intensity + 0.01)
        elif self.music_intensity > self.target_intensity:
            self.music_intensity = max(self.target_intensity, self.music_intensity - 0.01)

    def preload_audio(self):
        """
        Preload and convert all audio files before the game starts.
        This prevents delays during gameplay.
        """
        print("\n🔊 Preloading audio files...")

        # Preload day number audio (e.g., "Day 1", "Day 2", etc.)
        self._preload_day_audio()

        # Preload intro audio ("making my followers fight each other")
        self._preload_intro_audio()

        # Preload countdown audio
        self._preload_countdown_audio()

        # Preload Smash Ultimate countdown audio (for obstacle course)
        self._preload_smash_countdown_audio()

        # Preload background music
        self._preload_background_music()

        total_intro = self.day_audio_duration + self.intro_audio_duration
        print(f"✅ Audio preloaded: day={self.day_audio_duration:.2f}s, intro={self.intro_audio_duration:.2f}s, countdown={self.countdown_audio_duration:.2f}s")
        print(f"   Total intro duration: {total_intro:.2f}s\n")

    def _preload_background_music(self):
        """Preload and convert background music to WAV"""
        raw_path = self.background_music_path
        if raw_path:
            stem = Path(raw_path).stem
        else:
            stem = "background_music"
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "background_music"
        cache_hash = hashlib.md5((raw_path or "").encode("utf-8")).hexdigest()[:8]
        music_cache = f"assets/{safe_stem}_{cache_hash}.wav"
        self.background_music_cache_path = music_cache

        try:
            # Check if we have a cached audio file
            if os.path.exists(music_cache):
                self.background_music_path = music_cache
                print(f"   ✓ Background music loaded (cached)")
                return

            # Convert audio using moviepy
            if os.path.exists(self.background_music_path):
                try:
                    from moviepy.editor import AudioFileClip
                    print(f"   Converting background music...")
                    audio = AudioFileClip(self.background_music_path)
                    audio.write_audiofile(music_cache, verbose=False, logger=None)
                    audio.close()

                    self.background_music_path = music_cache
                    print(f"   ✓ Background music converted")
                except ImportError:
                    print("   ⚠️ moviepy not installed. Install with: pip install moviepy")
                except Exception as e:
                    print(f"   ⚠️ Could not convert background music: {e}")
            else:
                print(f"   ⚠️ Background music not found: {self.background_music_path}")
        except Exception as e:
            print(f"   ⚠️ Could not preload background music: {e}")

    def _preload_day_audio(self):
        """Preload the day number audio file (always uses Day 1 audio)"""
        # Always use Day 1 audio file regardless of DAY_NUMBER setting
        day_audio_path = "assets/Day 1.m4a"
        day_audio_cache = "assets/day_1_audio.wav"

        try:
            import os

            # Check if we have a cached audio file
            if os.path.exists(day_audio_cache):
                self.day_sound = pygame.mixer.Sound(day_audio_cache)
                self.day_audio_duration = self.day_sound.get_length()
                print(f"   ✓ Day audio loaded (cached, {self.day_audio_duration:.2f}s)")
                return

            # Convert audio using moviepy
            if os.path.exists(day_audio_path):
                try:
                    from moviepy.editor import AudioFileClip
                    print(f"   Converting Day audio...")
                    audio = AudioFileClip(day_audio_path)
                    self.day_audio_duration = audio.duration
                    audio.write_audiofile(day_audio_cache, verbose=False, logger=None)
                    audio.close()

                    self.day_sound = pygame.mixer.Sound(day_audio_cache)
                    print(f"   ✓ Day audio converted ({self.day_audio_duration:.2f}s)")
                except ImportError:
                    print("   ⚠️ moviepy not installed. Install with: pip install moviepy")
                except Exception as e:
                    print(f"   ⚠️ Could not convert Day audio: {e}")
            else:
                print(f"   ⚠️ Day audio not found: {day_audio_path}")
        except Exception as e:
            print(f"   ⚠️ Could not preload Day audio: {e}")

    def _preload_intro_audio(self):
        """Preload the intro audio file"""
        intro_audio_path = "assets/making my followers fight eachother.m4a"
        intro_audio_cache = "assets/intro_audio.wav"

        try:
            import os

            # Check if we have a cached audio file
            if os.path.exists(intro_audio_cache):
                self.intro_sound = pygame.mixer.Sound(intro_audio_cache)
                self.intro_audio_duration = self.intro_sound.get_length()
                print(f"   ✓ Intro audio loaded (cached, {self.intro_audio_duration:.2f}s)")
                return

            # Extract/convert audio using moviepy
            if os.path.exists(intro_audio_path):
                try:
                    from moviepy.editor import AudioFileClip
                    print(f"   Converting intro audio...")
                    audio = AudioFileClip(intro_audio_path)
                    self.intro_audio_duration = audio.duration
                    audio.write_audiofile(intro_audio_cache, verbose=False, logger=None)
                    audio.close()

                    self.intro_sound = pygame.mixer.Sound(intro_audio_cache)
                    print(f"   ✓ Intro audio converted ({self.intro_audio_duration:.2f}s)")
                except ImportError:
                    print("   ⚠️ moviepy not installed. Install with: pip install moviepy")
                except Exception as e:
                    print(f"   ⚠️ Could not convert intro audio: {e}")
            else:
                print(f"   ⚠️ Intro audio not found: {intro_audio_path}")
        except Exception as e:
            print(f"   ⚠️ Could not preload intro audio: {e}")

    def _preload_countdown_audio(self):
        """Preload the countdown audio file"""
        countdown_video_path = "assets/3 2 1 fight.mp4"
        countdown_audio_cache = "assets/countdown_audio.wav"

        try:
            import os

            # Check if we have a cached audio file
            if os.path.exists(countdown_audio_cache):
                self.countdown_sound = pygame.mixer.Sound(countdown_audio_cache)
                self.countdown_audio_duration = self.countdown_sound.get_length()
                print(f"   ✓ Countdown audio loaded (cached, {self.countdown_audio_duration:.2f}s)")
                return

            # Extract audio from video using moviepy
            if os.path.exists(countdown_video_path):
                try:
                    from moviepy.editor import VideoFileClip
                    print(f"   Extracting countdown audio from video...")
                    video = VideoFileClip(countdown_video_path)
                    self.countdown_audio_duration = video.duration
                    video.audio.write_audiofile(countdown_audio_cache, verbose=False, logger=None)
                    video.close()

                    self.countdown_sound = pygame.mixer.Sound(countdown_audio_cache)
                    print(f"   ✓ Countdown audio extracted ({self.countdown_audio_duration:.2f}s)")
                except ImportError:
                    print("   ⚠️ moviepy not installed. Install with: pip install moviepy")
                except Exception as e:
                    print(f"   ⚠️ Could not extract countdown audio: {e}")
            else:
                print(f"   ⚠️ Countdown video not found: {countdown_video_path}")
        except Exception as e:
            print(f"   ⚠️ Could not preload countdown audio: {e}")

    def _preload_smash_countdown_audio(self):
        """Preload the Smash Ultimate countdown audio file (for obstacle course)"""
        smash_video_path = "assets/smash ultimate 3 2 1 go green screen.mp4"
        smash_audio_cache = "assets/smash_countdown_audio.wav"

        try:
            import os

            # Check if we have a cached audio file
            if os.path.exists(smash_audio_cache):
                self.smash_countdown_sound = pygame.mixer.Sound(smash_audio_cache)
                self.smash_countdown_duration = self.smash_countdown_sound.get_length()
                print(f"   ✓ Smash countdown audio loaded (cached, {self.smash_countdown_duration:.2f}s)")
                return

            # Extract audio from video using moviepy
            if os.path.exists(smash_video_path):
                try:
                    from moviepy.editor import VideoFileClip
                    print(f"   Extracting Smash countdown audio from video...")
                    video = VideoFileClip(smash_video_path)
                    self.smash_countdown_duration = video.duration
                    video.audio.write_audiofile(smash_audio_cache, verbose=False, logger=None)
                    video.close()

                    self.smash_countdown_sound = pygame.mixer.Sound(smash_audio_cache)
                    print(f"   ✓ Smash countdown audio extracted ({self.smash_countdown_duration:.2f}s)")
                except ImportError:
                    print("   ⚠️ moviepy not installed. Install with: pip install moviepy")
                except Exception as e:
                    print(f"   ⚠️ Could not extract Smash countdown audio: {e}")
            else:
                print(f"   ⚠️ Smash countdown video not found: {smash_video_path}")
        except Exception as e:
            print(f"   ⚠️ Could not preload Smash countdown audio: {e}")

    def play_smash_countdown_audio(self):
        """Play the Smash Ultimate countdown audio"""
        if self.local_audio_muted:
            print("Audio muted: smash countdown playback disabled for local processing")
            return
        if self.smash_countdown_sound:
            self.smash_countdown_sound.set_volume(self.announcer_volume * self.master_volume)
            self.announcer_channel.play(self.smash_countdown_sound)
            print(f"🔊 Smash countdown audio started ({self.smash_countdown_duration:.2f}s)")
        else:
            print("⚠️  Smash countdown audio not preloaded")

    def start_background_music(self):
        """Start playing background music on loop (skipped during video export)"""
        try:
            import os

            # Skip playing background music during simulation if we're exporting video
            # Audio will be added during video export instead
            if config.EXPORT_VIDEO:
                print(f"🎵 Background music skipped during simulation (will be added during video export)")
                return

            if self.local_audio_muted:
                print("Audio muted: background music playback disabled for local processing")
                return

            if os.path.exists(self.background_music_path):
                pygame.mixer.music.load(self.background_music_path)
                pygame.mixer.music.set_volume(self.current_music_volume * self.master_volume)
                pygame.mixer.music.play(-1)  # -1 = loop forever
                self.music_playing = True
                print(f"🎵 Background music started: {self.background_music_path}")
            else:
                print(f"⚠️  Background music not found: {self.background_music_path}")
        except Exception as e:
            print(f"⚠️  Could not load background music: {e}")

    def play_intro_audio(self):
        """Play the day number audio followed by 'making my followers fight each other' (skipped during video export)"""
        # Skip intro audio during simulation if we're exporting video
        if config.EXPORT_VIDEO:
            print(f"🔊 Intro audio skipped during simulation (not needed for video)")
            return

        if self.local_audio_muted:
            print("Audio muted: intro playback disabled for local processing")
            return

        import threading

        def play_sequence():
            import time as time_module

            # Play day number audio first
            if self.day_sound:
                self.day_sound.set_volume(self.announcer_volume * self.master_volume)
                self.announcer_channel.play(self.day_sound)
                # Wait for day audio to finish
                time_module.sleep(self.day_audio_duration)

            # Then play "making my followers fight each other"
            if self.intro_sound:
                self.intro_sound.set_volume(self.announcer_volume * self.master_volume)
                self.announcer_channel.play(self.intro_sound)

        # Run in background thread so it doesn't block
        thread = threading.Thread(target=play_sequence, daemon=True)
        thread.start()

        total_duration = self.day_audio_duration + self.intro_audio_duration
        print(f"🔊 Intro audio started (Day + intro = {total_duration:.2f}s)")

    def get_total_intro_duration(self):
        """Get the total duration of day + intro audio"""
        return self.day_audio_duration + self.intro_audio_duration

    def play_countdown_audio(self):
        """Play the countdown video audio"""
        if self.local_audio_muted:
            print("Audio muted: countdown playback disabled for local processing")
            return
        if self.countdown_sound:
            self.countdown_sound.set_volume(self.announcer_volume * self.master_volume)
            self.announcer_channel.play(self.countdown_sound)
            print(f"🔊 Countdown audio started ({self.countdown_audio_duration:.2f}s)")
        else:
            print("⚠️  Countdown audio not preloaded")

    def set_music_volume_low(self):
        """Set music to low volume (during announcer speaking)"""
        self.target_music_volume = self.music_volume_low

    def set_music_volume_high(self):
        """Set music to high volume (during gameplay)"""
        self.target_music_volume = self.music_volume_high

    def update_music_volume(self):
        """Smoothly transition music volume toward target"""
        if not self.music_playing:
            return

        # Smooth transition
        transition_speed = 0.02
        if self.current_music_volume < self.target_music_volume:
            self.current_music_volume = min(
                self.target_music_volume,
                self.current_music_volume + transition_speed
            )
        elif self.current_music_volume > self.target_music_volume:
            self.current_music_volume = max(
                self.target_music_volume,
                self.current_music_volume - transition_speed
            )

        # Apply volume
        pygame.mixer.music.set_volume(self.current_music_volume * self.master_volume)

    def _init_tts(self):
        """Initialize text-to-speech engine"""
        if self.local_audio_muted:
            self.tts_engine = None
            print("Audio muted: TTS disabled for local processing")
            return
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            # Set properties
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            print("✅ TTS engine initialized")
        except Exception as e:
            print(f"⚠️  TTS engine not available: {e}")
            print("   Install with: pip install pyttsx3")
            self.tts_engine = None

    def speak(self, text: str, wait: bool = True):
        """
        Speak text using TTS

        Args:
            text: Text to speak
            wait: Whether to wait for speech to complete
        """
        # Log TTS event for post-processing
        if self.audio_logger:
            self.audio_logger.log_tts(text, wait)

        if self.local_audio_muted:
            return

        if self.tts_engine:
            try:
                if wait:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                else:
                    # Use threading for non-blocking speech
                    import threading
                    def speak_thread():
                        try:
                            self.tts_engine.say(text)
                            self.tts_engine.runAndWait()
                        except:
                            pass

                    thread = threading.Thread(target=speak_thread, daemon=True)
                    thread.start()
            except Exception as e:
                print(f"⚠️  TTS error: {e}")
        else:
            # Fallback: just print to console
            print(f"🔊 [TTS]: {text}")

    def set_master_volume(self, volume: float):
        """
        Set master volume

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if self.local_audio_muted:
            self.master_volume = 0.0
            return
        self.master_volume = max(0.0, min(1.0, volume))

    def stop(self):
        """
        Stop all audio playback (music, SFX, announcer). Used during game teardown.
        """
        try:
            pygame.mixer.stop()
        except Exception:
            pass

    def cleanup(self):
        """Clean up sound resources"""
        if self.music_playing:
            try:
                pygame.mixer.music.stop()
            except:
                pass
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except:
                pass
        pygame.mixer.quit()

    # =========================================================================
    # ANIME FIGHTING SOUND EFFECTS
    # =========================================================================

    def _generate_sweep_sound(self, freq_start: float, freq_end: float,
                              duration: float, volume: float = 0.5) -> pygame.mixer.Sound:
        """
        Generate a frequency sweep sound (whoosh effect)

        Args:
            freq_start: Starting frequency in Hz
            freq_end: Ending frequency in Hz
            duration: Duration in seconds
            volume: Volume (0.0 to 1.0)
        """
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * volume)

        for i in range(num_samples):
            t = i / sample_rate
            progress = t / duration
            # Linear frequency interpolation
            freq = freq_start + (freq_end - freq_start) * progress
            # Envelope (attack + decay)
            envelope = min(1.0, t * 20) * (1.0 - progress * 0.5)
            value = int(max_amplitude * envelope * math.sin(2 * math.pi * freq * t))
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_noise_burst(self, duration: float, volume: float = 0.3) -> pygame.mixer.Sound:
        """
        Generate a short noise burst (whoosh/dash sound)

        Args:
            duration: Duration in seconds
            volume: Volume (0.0 to 1.0)
        """
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * volume)

        for i in range(num_samples):
            t = i / sample_rate
            progress = t / duration
            # Quick attack, gradual decay
            envelope = min(1.0, t * 50) * (1.0 - progress)
            # White noise
            noise = np.random.uniform(-1, 1)
            value = int(max_amplitude * envelope * noise)
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def _generate_impact_sound(self, freq: float, duration: float,
                               volume: float = 0.5, noise_mix: float = 0.0,
                               decay: float = 0.7) -> pygame.mixer.Sound:
        """
        Generate an impact sound with optional noise

        Args:
            freq: Base frequency in Hz
            duration: Duration in seconds
            volume: Volume (0.0 to 1.0)
            noise_mix: Amount of noise to mix in (0.0 to 1.0)
            decay: Decay rate (higher = faster decay)
        """
        sample_rate = 22050
        num_samples = int(duration * sample_rate)
        samples = np.zeros((num_samples, 2), dtype=np.int16)

        max_amplitude = int(32767 * volume)

        for i in range(num_samples):
            t = i / sample_rate
            progress = t / duration
            # Exponential decay envelope
            envelope = math.exp(-decay * progress * 10)
            # Tone
            tone = math.sin(2 * math.pi * freq * t)
            # Mix with noise if specified
            if noise_mix > 0:
                noise = np.random.uniform(-1, 1)
                signal = tone * (1 - noise_mix) + noise * noise_mix
            else:
                signal = tone
            value = int(max_amplitude * envelope * signal)
            samples[i] = [value, value]

        return pygame.sndarray.make_sound(samples)

    def play_light_hit(self):
        """Play light attack impact sound (quick punch pop)"""
        sound = self._generate_impact_sound(freq=700, duration=0.05, volume=0.4, decay=0.8)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('light_hit', self.sfx_volume)

    def play_heavy_hit(self):
        """Play heavy attack impact sound (deep thud)"""
        sound = self._generate_impact_sound(freq=180, duration=0.12, volume=0.6, decay=0.6)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('heavy_hit', self.sfx_volume)

    def play_finisher_hit(self):
        """Play finisher attack impact sound (strong slam)"""
        sound = self._generate_impact_sound(freq=120, duration=0.15, volume=0.7, decay=0.5)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('finisher_hit', self.sfx_volume)

    def play_ki_blast_fire(self):
        """Play projectile launch sound (rising whoosh)"""
        sound = self._generate_sweep_sound(freq_start=800, freq_end=1200, duration=0.1, volume=0.5)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('ki_blast_fire', self.sfx_volume)

    def play_ki_blast_hit(self):
        """Play projectile impact sound (energy burst)"""
        sound = self._generate_impact_sound(freq=500, duration=0.08, volume=0.5, noise_mix=0.3)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('ki_blast_hit', self.sfx_volume)

    def play_block(self):
        """Play blocked attack sound (shield clang)"""
        sound = self._generate_impact_sound(freq=1000, duration=0.1, volume=0.4, decay=0.9)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('block', self.sfx_volume)

    def play_final_smash_charge(self):
        """Play Final Smash charge-up sound (rising power)"""
        sound = self._generate_sweep_sound(freq_start=100, freq_end=500, duration=0.5, volume=0.6)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('final_smash_charge', self.sfx_volume)

    def play_final_smash_impact(self):
        """Play Final Smash impact sound (massive explosion)"""
        sound = self._generate_impact_sound(freq=80, duration=0.3, volume=0.8, noise_mix=0.4)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('final_smash_impact', self.sfx_volume)

    def play_teleport(self):
        """Play teleportation sound (warp effect)"""
        sound = self._generate_sweep_sound(freq_start=400, freq_end=800, duration=0.05, volume=0.4)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('teleport', self.sfx_volume)

    def play_dash(self):
        """Play dash/roll movement sound (quick whoosh)"""
        sound = self._generate_noise_burst(duration=0.08, volume=0.3)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('dash', self.sfx_volume)

    def play_clash(self):
        """Play clash sound (both fighters attack simultaneously - metal clash)"""
        sound = self._generate_impact_sound(freq=600, duration=0.15, volume=0.7)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('clash', self.sfx_volume)

    def play_counter_hit(self):
        """Play counter-attack hit sound (satisfying parry impact)"""
        sound = self._generate_impact_sound(freq=400, duration=0.1, volume=0.6)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('counter_hit', self.sfx_volume)

    def play_desperation_activate(self):
        """Play desperation mode activation sound (power-up whoosh)"""
        sound = self._generate_sweep_sound(freq_start=200, freq_end=800, duration=0.3, volume=0.6)
        sound.set_volume(self.sfx_volume * self.master_volume)
        self.sfx_channel.play(sound)

        if self.audio_logger:
            self.audio_logger.log_sound_effect('desperation_activate', self.sfx_volume)
