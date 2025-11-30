"""
Scoring System Module
Handles point calculation and leaderboard management
"""

import math
from typing import Dict, List, Tuple


class ScoringSystem:
    """
    Manages scoring for the battle royale and obstacle course
    Simple placement-based scoring: 1st place = 10000 points, last place = ~100 points
    """

    # Scoring constants
    MAX_POINTS = 10000

    @staticmethod
    def calculate_placement_points(placement: int, total_participants: int) -> float:
        """
        Calculate points based on placement using simple linear formula.
        1st place gets 10000 points, last place gets ~100 points.

        Formula: points = ((total - placement + 1) / total) * 10000
        Example: 39th out of 100 racers = ((100 - 39 + 1) / 100) * 10000 = 6200 points

        Args:
            placement: Final placement (1 = winner, higher = worse)
            total_participants: Total number of participants

        Returns:
            Points for this placement (100-10000)
        """
        # Calculate percentage of racers you beat (including yourself)
        # placement 1 out of 100 = 100%, placement 100 out of 100 = 1%
        points = ((total_participants - placement + 1) / total_participants) * ScoringSystem.MAX_POINTS
        return points

    @staticmethod
    def calculate_total_points(
        placement: int,
        total_participants: int,
        survival_time: float = 0,
        games_played: int = 0
    ) -> Dict[str, float]:
        """
        Calculate total points for a participant.
        Only placement matters - no bonuses.

        Args:
            placement: Final placement (1 = winner)
            total_participants: Total number of participants
            survival_time: Not used (kept for compatibility)
            games_played: Not used (kept for compatibility)

        Returns:
            Dictionary with point breakdown
        """
        points = ScoringSystem.calculate_placement_points(placement, total_participants)

        return {
            "base_points": round(points, 2),
            "placement_points": round(points, 2),
            "survival_bonus": 0,
            "longevity_multiplier": 1.0,
            "total_points": round(points, 2)
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
