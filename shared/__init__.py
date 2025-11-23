"""
Shared modules used across all games
"""

from .api import InstagramAPI
from .physics import PhysicsEngine
from .particles import ParticleSystem, Particle
from .sound_manager import SoundManager
from .recorder import VideoRecorder
from .scoring import ScoringSystem
from .statistics import PlayerStatistics
from .audio_logger import AudioLogger, AudioEvent

__all__ = [
    'InstagramAPI',
    'PhysicsEngine',
    'ParticleSystem',
    'Particle',
    'SoundManager',
    'VideoRecorder',
    'ScoringSystem',
    'PlayerStatistics',
    'AudioLogger',
    'AudioEvent',
]
