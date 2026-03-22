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
    DEFAULT_CLUB_MEMBER_POINTS_MULTIPLIER = 0.10
    CLUB_MEMBER_IMPORT_SUFFIX = "club_members_followers.json"

    @staticmethod
    def _get_runtime_config():
        try:
            import config  # Imported lazily to avoid hard coupling at module import time.
        except Exception:
            return None
        return config

    @staticmethod
    def _get_club_member_points_multiplier() -> float:
        runtime_config = ScoringSystem._get_runtime_config()
        raw_multiplier = getattr(
            runtime_config,
            "CLUB_MEMBER_GAME_POINTS_MULTIPLIER",
            ScoringSystem.DEFAULT_CLUB_MEMBER_POINTS_MULTIPLIER,
        ) if runtime_config is not None else ScoringSystem.DEFAULT_CLUB_MEMBER_POINTS_MULTIPLIER
        try:
            return max(0.0, float(raw_multiplier))
        except Exception:
            return ScoringSystem.DEFAULT_CLUB_MEMBER_POINTS_MULTIPLIER

    @staticmethod
    def _uses_club_member_import(game_mode: str | None = None) -> bool:
        runtime_config = ScoringSystem._get_runtime_config()
        if runtime_config is None:
            return False

        current_import = str(getattr(runtime_config, "FOLLOWER_IMPORT_FILE", "") or "")
        normalized_import = current_import.replace("\\", "/").lower()
        if normalized_import.endswith(ScoringSystem.CLUB_MEMBER_IMPORT_SUFFIX):
            return True

        overrides = getattr(runtime_config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
        if not isinstance(overrides, dict):
            return False

        active_mode = str(game_mode or getattr(runtime_config, "GAME_MODE", "") or "").strip().lower()
        if not active_mode:
            return False

        mode_candidates = {active_mode}
        if active_mode.startswith("super_follower_bros"):
            mode_candidates.add("super_follower_bros")
            mode_candidates.add("super_follower_bros_1_2")

        for mode_candidate in mode_candidates:
            override = str(overrides.get(mode_candidate, "") or "").replace("\\", "/").lower()
            if override.endswith(ScoringSystem.CLUB_MEMBER_IMPORT_SUFFIX):
                return True

        return False

    @staticmethod
    def _apply_game_mode_points_multiplier(points: float, game_mode: str | None = None) -> tuple[float, float]:
        multiplier = 1.0
        if ScoringSystem._uses_club_member_import(game_mode):
            multiplier = ScoringSystem._get_club_member_points_multiplier()
        return points * multiplier, multiplier

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
        games_played: int = 0,
        game_mode: str | None = None,
    ) -> Dict[str, float]:
        """
        Calculate total points for a participant.
        Only placement matters - no bonuses.

        Args:
            placement: Final placement (1 = winner)
            total_participants: Total number of participants
            survival_time: Not used (kept for compatibility)
            games_played: Not used (kept for compatibility)
            game_mode: Optional explicit game mode override for mode-based scoring rules

        Returns:
            Dictionary with point breakdown
        """
        raw_points = ScoringSystem.calculate_placement_points(placement, total_participants)
        points, mode_multiplier = ScoringSystem._apply_game_mode_points_multiplier(
            raw_points,
            game_mode=game_mode,
        )

        return {
            "base_points": round(points, 2),
            "placement_points": round(points, 2),
            "survival_bonus": 0,
            "longevity_multiplier": 1.0,
            "mode_multiplier": round(mode_multiplier, 4),
            "total_points": round(points, 2)
        }

    @staticmethod
    def calculate_scores(results: List[Dict], game_mode: str = "spleef") -> List[Dict]:
        """
        Calculate scores for all participants based on placement.

        Args:
            results: List of result dictionaries with 'username', 'display_name', 'placement', 'score'
            game_mode: Game mode name (for compatibility)

        Returns:
            List of result dictionaries with calculated points added
        """
        if not results:
            return []

        total_participants = len(results)

        # Calculate points for each participant
        scored_results = []
        for result in results:
            placement = result['placement']
            raw_points = ScoringSystem.calculate_placement_points(placement, total_participants)
            points, _ = ScoringSystem._apply_game_mode_points_multiplier(
                raw_points,
                game_mode=game_mode,
            )

            scored_results.append({
                'username': result['username'],
                'display_name': result['display_name'],
                'placement': placement,
                'score': result.get('score', 0),  # Keep original score if exists
                'points': round(points, 2),
                'total_points': round(points, 2)
            })

        # Sort by placement
        scored_results.sort(key=lambda x: x['placement'])

        return scored_results

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
