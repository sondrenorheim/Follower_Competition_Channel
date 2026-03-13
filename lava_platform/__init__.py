"""
Lava Platform Game Module.

Survive by reaching the safe platform before lava fills the arena.
"""

from .game import LavaPlatformGame
from .arena import LavaPlatformArena, SafePlatform, Obstacle
from .player import LavaPlatformPlayer
from .renderer import LavaPlatformRenderer

__all__ = [
    "LavaPlatformGame",
    "LavaPlatformArena",
    "SafePlatform",
    "Obstacle",
    "LavaPlatformPlayer",
    "LavaPlatformRenderer",
]
