"""
Snake Escape Game Module

A survival game where followers must escape from a hungry snake.
"""

from .game import SnakeEscapeGame
from .arena import SnakeEscapeArena
from .snake import Snake
from .follower import SnakeEscapeFollower
from .renderer import SnakeEscapeRenderer

__all__ = [
    'SnakeEscapeGame',
    'SnakeEscapeArena',
    'Snake',
    'SnakeEscapeFollower',
    'SnakeEscapeRenderer',
]
