"""
Heads/Tails game module.

Players pick heads or tails each round. One side drops.
"""

from .game import SideChoiceGame
from .arena import SideChoiceArena
from .player import SideChoicePlayer
from .renderer import SideChoiceRenderer

__all__ = [
    "SideChoiceGame",
    "SideChoiceArena",
    "SideChoicePlayer",
    "SideChoiceRenderer",
]
