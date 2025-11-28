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
from .game_history import GameHistory
from .audio_logger import AudioLogger, AudioEvent
from . import auto_push

# Templates for creating new games
from .game_template import GameTemplate
from .renderer_template import RendererTemplate
from .arena_template import ArenaTemplate, ArenaShape
from .entity_template import EntityTemplate, MovingEntity

__all__ = [
    # Core shared modules
    'InstagramAPI',
    'PhysicsEngine',
    'ParticleSystem',
    'Particle',
    'SoundManager',
    'VideoRecorder',
    'ScoringSystem',
    'PlayerStatistics',
    'GameHistory',
    'AudioLogger',
    'AudioEvent',
    'auto_push',
    # Templates for new games
    'GameTemplate',
    'RendererTemplate',
    'ArenaTemplate',
    'ArenaShape',
    'EntityTemplate',
    'MovingEntity',
]
