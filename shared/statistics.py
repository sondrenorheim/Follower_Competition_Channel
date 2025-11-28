"""
Statistics Persistence Module
Handles saving and loading player statistics across games
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import config


class PlayerStatistics:
    """
    Manages persistent player statistics across multiple games
    """

    def __init__(self, stats_file: str = "player_statistics.json"):
        """
        Initialize statistics manager

        Args:
            stats_file: Path to JSON file for storing statistics
        """
        self.stats_file = stats_file
        self.stats: Dict[str, Dict] = {}
        self.metadata: Dict = {}  # Stores last_updated, total_games, etc.
        self.load_statistics()

    def load_statistics(self):
        """
        Load statistics from JSON file
        Creates new file if it doesn't exist
        Supports both legacy format (dict of username->stats) and new format (with metadata)
        """
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if new format with 'players' and metadata
                if isinstance(data, dict) and "players" in data:
                    self.stats = data.get("players", {})
                    self.metadata = {
                        "last_updated": data.get("last_updated", ""),
                        "total_games_recorded": data.get("total_games_recorded", 0)
                    }
                else:
                    # Legacy format: flat dict of username->stats
                    self.stats = data
                    self.metadata = {
                        "last_updated": "",
                        "total_games_recorded": 0
                    }

                print(f"Loaded statistics for {len(self.stats)} players")
            except Exception as e:
                print(f"Error loading statistics: {e}")
                self.stats = {}
                self.metadata = {"last_updated": "", "total_games_recorded": 0}
        else:
            print("No existing statistics file, starting fresh")
            self.stats = {}
            self.metadata = {"last_updated": "", "total_games_recorded": 0}

    def save_statistics(self):
        """
        Save statistics to JSON file in new format with metadata
        Skips saving if TEST_MODE is enabled in config
        """
        if config.TEST_MODE:
            print("🧪 TEST MODE: Statistics not saved")
            return

        try:
            # Update metadata
            self.metadata["last_updated"] = datetime.now().isoformat()

            # Create new format with metadata
            data = {
                "last_updated": self.metadata.get("last_updated"),
                "total_games_recorded": self.metadata.get("total_games_recorded", 0),
                "players": self.stats
            }

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Statistics saved for {len(self.stats)} players")
        except Exception as e:
            print(f"❌ Error saving statistics: {e}")

    # List index reference for player stats:
    # [0] total_points, [1] games_played, [2] best_placement, [3] total_placements,
    # [4] wins, [5] top_3_finishes, [6] top_10_pct_finishes, [7] total_survival_time,
    # [8] first_eliminations (first out), [9] current_hot_streak, [10] best_hot_streak,
    # [11] total_kills, [12] total_damage_dealt
    P, G, B, T, W, T3, T10P, S, FIRST_OUT, STREAK, BEST_STREAK, KILLS, DAMAGE = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12

    def get_player_stats(self, username: str) -> list:
        """
        Get statistics for a specific player
        Creates new entry if player doesn't exist

        New format (dict):
        {
            "stats": [array of 13 values],
            "game_breakdown": {"game_type": count, ...},
            "recent_games": ["game_id", ...]
        }

        List format (index reference):
        [0]  total_points
        [1]  games_played
        [2]  best_placement
        [3]  total_placements (for calculating average)
        [4]  wins
        [5]  top_3_finishes
        [6]  top_10%_finishes (top 10 percent)
        [7]  total_survival_time
        [8]  first_eliminations (times eliminated first - "most unlucky")
        [9]  current_hot_streak (consecutive top 10% finishes)
        [10] best_hot_streak (best consecutive top 10% finishes)
        [11] total_kills (eliminations caused by this player)
        [12] total_damage_dealt (damage dealt in Fighter Arena)

        Derived stats (not stored, calculated):
        - average_placement = [3] / [1]

        Args:
            username: Player username

        Returns:
            List with player statistics
        """
        if username not in self.stats:
            # Initialize new player with enhanced format
            self.stats[username] = {
                "stats": [0.0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0.0],
                "game_breakdown": {},
                "recent_games": []
            }

        # Handle legacy formats
        player_data = self.stats[username]

        # If it's an old list format, convert to new dict format
        if isinstance(player_data, list):
            self.stats[username] = {
                "stats": player_data if len(player_data) == 13 else player_data + [0] * (13 - len(player_data)),
                "game_breakdown": {},
                "recent_games": []
            }
        # If it's an old dict format (very legacy)
        elif isinstance(player_data, dict) and "stats" not in player_data:
            old = player_data
            self.stats[username] = {
                "stats": [
                    old.get("p", old.get("total_points", 0.0)),
                    old.get("g", old.get("games_played", 0)),
                    old.get("b", old.get("best_placement", 0)),
                    old.get("t", old.get("total_placements", 0)),
                    old.get("w", old.get("wins", 0)),
                    old.get("t3", old.get("top_3_finishes", 0)),
                    old.get("t10", old.get("top_10_finishes", 0)),
                    old.get("s", old.get("total_survival_time", 0.0)),
                    0, 0, 0, 0, 0.0
                ],
                "game_breakdown": {},
                "recent_games": []
            }
        # Ensure new format has all required fields
        elif isinstance(player_data, dict):
            if "stats" not in player_data:
                player_data["stats"] = [0.0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0.0]
            if "game_breakdown" not in player_data:
                player_data["game_breakdown"] = {}
            if "recent_games" not in player_data:
                player_data["recent_games"] = []
            # Extend stats array if needed
            while len(player_data["stats"]) < 13:
                player_data["stats"].append(0)

        return self.stats[username]["stats"]

    def update_player_stats(
        self,
        username: str,
        placement: int,
        points_earned: float,
        survival_time: float,
        total_participants: int,
        kills: int = 0,
        damage_dealt: float = 0.0,
        game_type: str = "",
        game_id: str = ""
    ):
        """
        Update statistics for a player after a game

        Args:
            username: Player username
            placement: Final placement in the game
            points_earned: Points earned this game
            survival_time: Time survived in seconds
            total_participants: Total number of participants
            kills: Number of eliminations caused by this player
            damage_dealt: Total damage dealt (Fighter Arena)
            game_type: Type of game (e.g., "battle_royale", "platformer_race")
            game_id: Unique game session ID for tracking
        """
        s = self.get_player_stats(username)

        # Update basic stats
        s[self.P] = round(s[self.P] + points_earned, 1)
        s[self.G] += 1
        s[self.T] += placement
        s[self.S] = round(s[self.S] + survival_time, 1)

        # Update kills and damage
        s[self.KILLS] += kills
        s[self.DAMAGE] = round(s[self.DAMAGE] + damage_dealt, 1)

        # Update best placement
        if s[self.B] == 0 or placement < s[self.B]:
            s[self.B] = placement

        # Update milestone counts
        if placement == 1:
            s[self.W] += 1
        if placement <= 3:
            s[self.T3] += 1

        # Top 10% finish check
        top_10_pct_threshold = max(1, int(total_participants * 0.1))
        is_top_10_pct = placement <= top_10_pct_threshold

        if is_top_10_pct:
            s[self.T10P] += 1
            s[self.STREAK] += 1  # Increment hot streak
            if s[self.STREAK] > s[self.BEST_STREAK]:
                s[self.BEST_STREAK] = s[self.STREAK]
        else:
            s[self.STREAK] = 0  # Reset hot streak

        # First elimination (most unlucky)
        if placement == total_participants:
            s[self.FIRST_OUT] += 1

        # Update game breakdown (track games played by type)
        if game_type:
            player_data = self.stats[username]
            if game_type not in player_data["game_breakdown"]:
                player_data["game_breakdown"][game_type] = 0
            player_data["game_breakdown"][game_type] += 1

        # Track recent games (keep last 20)
        if game_id:
            player_data = self.stats[username]
            if game_id not in player_data["recent_games"]:
                player_data["recent_games"].insert(0, game_id)  # Add to front
                # Keep only last 20 games
                player_data["recent_games"] = player_data["recent_games"][:20]

    def get_all_time_leaderboard(self, top_n: int = 10) -> List[Tuple[str, float, list]]:
        """
        Get all-time leaderboard sorted by total points

        Args:
            top_n: Number of top players to return

        Returns:
            List of (username, total_points, stats_list) tuples
        """
        leaderboard = []
        for username, player_data in self.stats.items():
            # Handle both new dict format and legacy list format
            if isinstance(player_data, dict) and "stats" in player_data:
                stats = player_data["stats"]
                points = stats[self.P]
            elif isinstance(player_data, list):
                stats = player_data
                points = stats[self.P]
            else:
                # Very legacy dict format
                points = player_data.get("p", player_data.get("total_points", 0))
                stats = player_data
            leaderboard.append((username, points, stats))

        # Sort by total points descending
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        return leaderboard[:top_n]

    def get_current_game_leaderboard(
        self,
        game_results: List[Tuple[str, int, float, float]]
    ) -> List[Tuple[str, float]]:
        """
        Get leaderboard for current game

        Args:
            game_results: List of (username, placement, points_earned, survival_time) tuples

        Returns:
            List of (username, points_earned) tuples sorted by points
        """
        leaderboard = [(username, points) for username, _, points, _ in game_results]
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        return leaderboard

    def get_games_played(self, username: str) -> int:
        """
        Get number of games played by a player

        Args:
            username: Player username

        Returns:
            Number of games played (0 for new players)
        """
        if username in self.stats:
            player_data = self.stats[username]
            if isinstance(player_data, dict) and "stats" in player_data:
                return player_data["stats"][self.G]
            elif isinstance(player_data, list):
                return player_data[self.G]
            else:
                return player_data.get("g", player_data.get("games_played", 0))
        return 0

    def _get_stat(self, stats, index: int, fallback_keys: tuple = None) -> float:
        """Helper to get stat from list or legacy dict format"""
        if isinstance(stats, list):
            if index < len(stats):
                return stats[index]
            return 0
        if fallback_keys:
            return stats.get(fallback_keys[0], stats.get(fallback_keys[1], 0))
        return 0

    def get_average_placement(self, username: str) -> float:
        """Calculate average placement for a player"""
        if username not in self.stats:
            return 0
        s = self.get_player_stats(username)  # This returns the stats array
        games = s[self.G]
        if games == 0:
            return 0
        return round(s[self.T] / games, 1)

    def print_all_time_stats(self, top_n: int = 10):
        """
        Print formatted all-time statistics

        Args:
            top_n: Number of top players to show
        """
        leaderboard = self.get_all_time_leaderboard(top_n)

        if not leaderboard:
            print("\nNo statistics available yet")
            return

        print("\n" + "=" * 70)
        print("  ALL-TIME LEADERBOARD")
        print("=" * 70)

        medals = ["🥇", "🥈", "🥉"]
        for i, (username, total_points, stats) in enumerate(leaderboard):
            rank = i + 1
            medal = medals[i] if i < 3 else f"{rank}."

            games = self._get_stat(stats, self.G, ("g", "games_played")) or 1
            wins = self._get_stat(stats, self.W, ("w", "wins"))
            best = self._get_stat(stats, self.B, ("b", "best_placement"))
            total_placements = self._get_stat(stats, self.T, ("t", "total_placements"))
            avg_placement = total_placements / max(games, 1)
            best_streak = self._get_stat(stats, self.BEST_STREAK)
            first_out = self._get_stat(stats, self.FIRST_OUT)

            print(f"{medal} {username}")
            print(f"   Points: {total_points:.1f} | Games: {games} | "
                  f"Wins: {wins} | Best: #{best} | Avg: #{avg_placement:.1f}")
            if best_streak > 1 or first_out > 0:
                extras = []
                if best_streak > 1:
                    extras.append(f"🔥 Streak: {best_streak}")
                if first_out > 0:
                    extras.append(f"💀 First out: {first_out}")
                print(f"   {' | '.join(extras)}")

        print("=" * 70)

    def get_summary(self) -> Dict:
        """
        Get summary statistics across all players

        Returns:
            Dictionary with summary statistics
        """
        if not self.stats:
            return {
                "total_players": 0,
                "total_games": 0,
                "most_experienced_player": None,
                "highest_scorer": None
            }

        def get_games(player_data):
            if isinstance(player_data, dict) and "stats" in player_data:
                return player_data["stats"][self.G]
            elif isinstance(player_data, list):
                return player_data[self.G]
            return player_data.get("g", player_data.get("games_played", 0))

        def get_points(player_data):
            if isinstance(player_data, dict) and "stats" in player_data:
                return player_data["stats"][self.P]
            elif isinstance(player_data, list):
                return player_data[self.P]
            return player_data.get("p", player_data.get("total_points", 0))

        total_games_sum = sum(get_games(s) for s in self.stats.values())
        most_experienced = max(self.stats.items(), key=lambda x: get_games(x[1]))
        highest_scorer = max(self.stats.items(), key=lambda x: get_points(x[1]))

        return {
            "total_players": len(self.stats),
            "total_games": total_games_sum,
            "most_experienced_player": most_experienced[0],
            "most_experienced_games": get_games(most_experienced[1]),
            "highest_scorer": highest_scorer[0],
            "highest_score": get_points(highest_scorer[1])
        }
