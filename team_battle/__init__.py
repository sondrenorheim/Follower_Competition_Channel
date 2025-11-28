"""
Team Battle Module
4-team battle arena with phased combat
"""

from .game import TeamBattleGame
from .team_fighter import TeamFighter, Team
from .team_arena import TeamArena
from .renderer import TeamBattleRenderer

__all__ = [
    'TeamBattleGame',
    'TeamFighter',
    'Team',
    'TeamArena',
    'TeamBattleRenderer',
]
