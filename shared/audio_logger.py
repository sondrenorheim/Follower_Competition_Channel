"""
Audio Logger Module
Logs audio events for post-game audio generation and mixing
"""

import time
from typing import List, Dict, Tuple
import json


class AudioEvent:
    """Represents a single audio event (TTS, sound effect, etc.)"""

    def __init__(self, event_type: str, timestamp: float, **kwargs):
        """
        Initialize audio event

        Args:
            event_type: Type of event ('tts', 'sound_effect', 'music')
            timestamp: Time in seconds from game start
            **kwargs: Additional event-specific data
        """
        self.event_type = event_type
        self.timestamp = timestamp
        self.data = kwargs

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'type': self.event_type,
            'timestamp': self.timestamp,
            **self.data
        }


class AudioLogger:
    """
    Logs all audio events during gameplay for post-processing
    """

    def __init__(self):
        """Initialize audio logger"""
        self.events: List[AudioEvent] = []
        self.start_time = None
        self.recording = False

    def start(self):
        """Start logging audio events"""
        self.start_time = time.time()
        self.recording = True
        print("🎙️  Audio event logging started")

    def stop(self):
        """Stop logging audio events"""
        self.recording = False
        print(f"🎙️  Audio event logging stopped ({len(self.events)} events)")

    def get_timestamp(self) -> float:
        """Get current timestamp relative to start"""
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time

    def log_tts(self, text: str, wait: bool = False):
        """
        Log a text-to-speech event

        Args:
            text: Text to be spoken
            wait: Whether TTS should wait for completion
        """
        if not self.recording:
            return

        event = AudioEvent(
            'tts',
            self.get_timestamp(),
            text=text,
            wait=wait
        )
        self.events.append(event)
        print(f"   📝 Logged TTS: '{text[:30]}...' at {event.timestamp:.2f}s")

    def log_sound_effect(self, sound_name: str, volume: float = 1.0):
        """
        Log a sound effect event

        Args:
            sound_name: Name of the sound effect
            volume: Volume level (0.0 to 1.0)
        """
        if not self.recording:
            return

        event = AudioEvent(
            'sound_effect',
            self.get_timestamp(),
            sound_name=sound_name,
            volume=volume
        )
        self.events.append(event)

    def log_music(self, action: str, track_name: str = None, volume: float = 1.0):
        """
        Log a music event

        Args:
            action: Music action ('play', 'stop', 'volume')
            track_name: Name of the music track
            volume: Volume level
        """
        if not self.recording:
            return

        event = AudioEvent(
            'music',
            self.get_timestamp(),
            action=action,
            track_name=track_name,
            volume=volume
        )
        self.events.append(event)

    def save_to_file(self, filepath: str):
        """
        Save event log to JSON file

        Args:
            filepath: Path to save log file
        """
        log_data = {
            'events': [event.to_dict() for event in self.events],
            'total_duration': self.get_timestamp() if self.start_time else 0.0,
            'event_count': len(self.events)
        }

        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"💾 Audio event log saved: {filepath}")

    def get_events(self) -> List[AudioEvent]:
        """Get all logged events"""
        return self.events

    def get_tts_events(self) -> List[AudioEvent]:
        """Get only TTS events"""
        return [e for e in self.events if e.event_type == 'tts']

    def clear(self):
        """Clear all logged events"""
        self.events.clear()
        self.start_time = None
