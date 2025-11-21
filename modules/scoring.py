"""
Scoring System Module
Handles point calculation and leaderboard management
"""

import math
from typing import Dict, List, Tuple


class ScoringSystem:
    """
    Manages scoring for the battle royale
    Balances current performance with long-term participation
    """

    # Scoring constants
    BASE_POINTS_WINNER = 100
    BASE_POINTS_LAST = 10
    LONGEVITY_BONUS_PER_GAME = 0.02  # 2% bonus per game played
    MAX_LONGEVITY_BONUS = 0.40  # Cap at 40% bonus (20 games)
    SURVIVAL_TIME_MULTIPLIER = 0.5  # Points per second survived

    @staticmethod
    def calculate_placement_points(placement: int, total_participants: int) -> float:
        """
        Calculate base points based on placement
        Uses exponential decay so higher placements get significantly more points

        Args:
            placement: Final placement (1 = winner, higher = worse)
            total_participants: Total number of participants

        Returns:
            Base points for this placement
        """
        # Normalize placement to 0-1 range (1 = best, 0 = worst)
        normalized = 1.0 - ((placement - 1) / max(total_participants - 1, 1))

        # Apply exponential curve for more dramatic point differences
        # Using power of 1.5 to reward top placements more
        curved_score = math.pow(normalized, 1.5)

        # Scale to point range
        points_range = ScoringSystem.BASE_POINTS_WINNER - ScoringSystem.BASE_POINTS_LAST
        base_points = ScoringSystem.BASE_POINTS_LAST + (curved_score * points_range)

        return base_points

    @staticmethod
    def calculate_longevity_bonus(games_played: int) -> float:
        """
        Calculate longevity multiplier based on games played
        Capped to prevent extreme advantages for veterans

        Args:
            games_played: Number of games this player has participated in

        Returns:
            Multiplier (1.0 = no bonus, 1.4 = max 40% bonus)
        """
        bonus = games_played * ScoringSystem.LONGEVITY_BONUS_PER_GAME
        capped_bonus = min(bonus, ScoringSystem.MAX_LONGEVITY_BONUS)
        return 1.0 + capped_bonus

    @staticmethod
    def calculate_survival_bonus(survival_time: float) -> float:
        """
        Calculate bonus points for survival time

        Args:
            survival_time: Time survived in seconds

        Returns:
            Bonus points for survival time
        """
        return survival_time * ScoringSystem.SURVIVAL_TIME_MULTIPLIER

    @staticmethod
    def calculate_total_points(
        placement: int,
        total_participants: int,
        survival_time: float,
        games_played: int = 0  # Kept for backwards compatibility but not used
    ) -> Dict[str, float]:
        """
        Calculate total points for a participant

        Args:
            placement: Final placement (1 = winner)
            total_participants: Total number of participants
            survival_time: Time survived in seconds
            games_played: Number of previous games played (not used in scoring)

        Returns:
            Dictionary with point breakdown
        """
        # Base points from placement
        base_points = ScoringSystem.calculate_placement_points(placement, total_participants)

        # Survival time bonus
        survival_bonus = ScoringSystem.calculate_survival_bonus(survival_time)

        # Total points (no longevity multiplier)
        total = base_points + survival_bonus

        return {
            "base_points": round(base_points, 2),
            "placement_points": round(base_points, 2),  # Same as base since no multiplier
            "survival_bonus": round(survival_bonus, 2),
            "longevity_multiplier": 1.0,  # Always 1.0 (no bonus)
            "total_points": round(total, 2)
        }

    @staticmethod
    def format_leaderboard(
        participants: List[Tuple[str, float]],
        top_n: int = 10,
        title: str = "LEADERBOARD"
    ) -> str:
        """
        Format leaderboard for display

        Args:
            participants: List of (username, points) tuples
            top_n: Number of top participants to show
            title: Title for the leaderboard

        Returns:
            Formatted leaderboard string
        """
        # Sort by points descending
        sorted_participants = sorted(participants, key=lambda x: x[1], reverse=True)
        top_participants = sorted_participants[:top_n]

        # Format output
        lines = [f"\n{'=' * 60}", f"  {title}", f"{'=' * 60}"]

        medals = ["🥇", "🥈", "🥉"]
        for i, (username, points) in enumerate(top_participants):
            rank = i + 1
            medal = medals[i] if i < 3 else f"{rank}."
            lines.append(f"{medal} {username}: {points:.1f} points")

        lines.append("=" * 60)
        return "\n".join(lines)
