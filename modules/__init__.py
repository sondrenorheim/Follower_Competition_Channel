"""
Follower Battle Royale & Fighter Arena Game Modules
"""

# Battle Royale modules
from .api import InstagramAPI
from .follower import Follower
from .arena import Arena
from .physics import PhysicsEngine
from .renderer import Renderer
from .recorder import VideoRecorder
from .particles import ParticleSystem
from .sound_manager import SoundManager
from .scoring import ScoringSystem
from .statistics import PlayerStatistics
from .audio_logger import AudioLogger

# Fighter Arena modules
from .fighter import Fighter
from .fighter_arena import FighterArena
from .fighter_renderer import FighterRenderer
from .fighter_game import FighterBattleArena

__all__ = [
    # Battle Royale
    'InstagramAPI',
    'Follower',
    'Arena',
    'PhysicsEngine',
    'Renderer',
    'VideoRecorder',
    'ParticleSystem',
    'SoundManager',
    'ScoringSystem',
    'PlayerStatistics',
    'AudioLogger',
    # Fighter Arena
    'Fighter',
    'FighterArena',
    'FighterRenderer',
    'FighterBattleArena',
]
