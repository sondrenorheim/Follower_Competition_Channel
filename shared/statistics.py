"""
Statistics Persistence Module
Handles saving and loading player statistics across games
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import config
from . import results_store


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
        self.light_mode = bool(getattr(config, "SIMULATION_LIGHT_MODE", False))
        self.light_disable_updates = bool(
            getattr(config, "SIMULATION_LIGHT_DISABLE_STATS_UPDATES", True)
        )
        self._light_save_notice_printed = False

        if self.light_mode:
            self.metadata = {
                "last_updated": "",
                "total_games_recorded": 0,
                "game_highscores": {},
            }
            print("SIMULATION-LIGHT MODE: Skipping player statistics load (deferred rebuild).")
        else:
            self.load_statistics()

    def load_statistics(self):
        """
        Load statistics from JSON file.
        Supports both legacy (flat dict) and new format (metadata + players).
        """
        best_payload, best_source = results_store.load_best_player_stats(self.stats_file)
        target_abs = os.path.abspath(self.stats_file)
        loaded = False

        if isinstance(best_payload, dict):
            if "players" in best_payload and isinstance(best_payload.get("players"), dict):
                self.stats = best_payload.get("players", {})
                self.metadata = {key: value for key, value in best_payload.items() if key != "players"}
                self.metadata.setdefault("last_updated", "")
                self.metadata.setdefault("total_games_recorded", 0)
                loaded = True
            elif best_payload:
                self.stats = best_payload
                self.metadata = {"last_updated": "", "total_games_recorded": 0}
                loaded = True

        if not loaded:
            if os.path.exists(self.stats_file):
                print(f"Error loading statistics: could not parse valid payload from {self.stats_file}")
            else:
                print("No existing statistics file, starting fresh")
            self.stats = {}
            self.metadata = {"last_updated": "", "total_games_recorded": 0}
        else:
            print(f"Loaded statistics for {len(self.stats)} players")

        if best_source and os.path.abspath(best_source) != target_abs:
            try:
                payload = dict(self.metadata)
                payload["players"] = self.stats
                results_store.atomic_write_json(self.stats_file, payload)
                results_store.write_recovery_log(
                    {
                        "type": "stats_recovered",
                        "target_file": self.stats_file,
                        "source": best_source,
                        "player_count": len(self.stats),
                    }
                )
                print(f"Recovered {self.stats_file} from {best_source}")
            except Exception as e:
                print(f"Warning: failed to persist recovered statistics: {e}")

        if "game_highscores" not in self.metadata:
            self.metadata["game_highscores"] = {}

    def save_statistics(self):
        """
        Save statistics to JSON file in new format with metadata.
        Skips saving if TEST_MODE is enabled in config.
        """
        if self.light_mode:
            if not self._light_save_notice_printed:
                print(
                    "SIMULATION-LIGHT MODE: Statistics not persisted now "
                    "(run rebuild post-step)."
                )
                self._light_save_notice_printed = True
            return

        if config.TEST_MODE:
            print("TEST MODE: Statistics not saved")
            return

        try:
            self.metadata["last_updated"] = datetime.now().isoformat()
            if "total_games_recorded" not in self.metadata:
                self.metadata["total_games_recorded"] = 0

            data = dict(self.metadata)
            data["players"] = self.stats

            results_store.atomic_write_json(self.stats_file, data)
            results_store.create_snapshot("stats_save", ["game_history.json", self.stats_file])
            print(f"Statistics saved for {len(self.stats)} players")
        except Exception as e:
            print(f"Error saving statistics: {e}")

    def get_game_highscore(self, game_type: str) -> Dict[str, object]:
        if not game_type:
            return {"score": 0, "username": "", "label": ""}
        highscores = self.metadata.get("game_highscores", {})
        record = highscores.get(game_type)
        if not record:
            return {"score": 0, "username": "", "label": ""}
        return record

    def update_game_highscore(self, game_type: str, score: float, username: str, label: str = "") -> bool:
        if not game_type:
            return False

        highscores = self.metadata.setdefault("game_highscores", {})
        current = highscores.get(game_type, {})
        try:
            current_score = float(current.get("score", 0) or 0)
        except (TypeError, ValueError):
            current_score = 0.0

        if score > current_score:
            highscores[game_type] = {
                "score": score,
                "username": username or "",
                "label": label or "",
            }
            return True

        return False

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
        if self.light_mode and self.light_disable_updates:
            return

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

    def get_monthly_leaderboard(self, year: int, month: int, top_n: int = 16) -> List[Tuple[str, list]]:
        """
        Get top N players for a specific month based on points earned in that month.

        Args:
            year: Year to filter (e.g., 2025)
            month: Month to filter (1-12)
            top_n: Number of top players to return

        Returns:
            List of tuples: (username, stats_array)
            Empty list if game_history.json doesn't exist or has no games for that month
        """
        game_history_file = "game_history.json"

        if not os.path.exists(game_history_file):
            print(f"âš ï¸  Monthly leaderboard: game_history.json not found")
            return []

        try:
            with open(game_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            games = data.get("games", [])

            # Filter games by month/year
            month_prefix = f"{year}-{month:02d}"
            non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])
            monthly_games = [
                g for g in games
                if g.get("timestamp", "").startswith(month_prefix)
                and not g.get("non_scoring")
                and g.get("game_type") not in non_scoring_types
            ]

            if not monthly_games:
                print(f"âš ï¸  No games found for {year}-{month:02d}")
                return []

            # Aggregate points per player for the month
            monthly_points = {}
            for game in monthly_games:
                for result in game.get("results", []):
                    username = result.get("username")
                    points = result.get("points", 0)
                    if username:
                        monthly_points[username] = monthly_points.get(username, 0.0) + points

            # Build leaderboard with full stats arrays
            leaderboard = []
            for username, month_pts in monthly_points.items():
                # Get full stats for this player (for avatar fetching, etc.)
                stats = self.get_player_stats(username)
                leaderboard.append((username, stats))

            # Sort by monthly points descending
            leaderboard.sort(key=lambda x: monthly_points[x[0]], reverse=True)

            print(f"ðŸ“Š Monthly leaderboard for {year}-{month:02d}: {len(leaderboard)} players")

            return leaderboard[:top_n]

        except Exception as e:
            print(f"âŒ Error loading monthly leaderboard: {e}")
            return []

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

        medals = ["ðŸ¥‡", "ðŸ¥ˆ", "ðŸ¥‰"]
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
                    extras.append(f"ðŸ”¥ Streak: {best_streak}")
                if first_out > 0:
                    extras.append(f"ðŸ’€ First out: {first_out}")
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

    def export_web_stats(self, output_path: str = "website/public/player_statistics_web.json"):
        """
        Export a compact web-friendly stats file for the website.
        """
        last_updated = self.metadata.get("last_updated") or datetime.now().isoformat()
        total_games_recorded = self.metadata.get("total_games_recorded", 0)

        short_map = {
            "platformer_race": "pr",
            "obstacle_course": "oc",
            "battle_royale": "br",
            "fighter_arena": "fa",
            "snake_escape": "se",
            "team_battle": "tb",
            "gorillas_vs_followers": "gv",
            "heads_or_tails": "ht",
            "wheel_spinner": "ws",
            "mini_golf": "mg",
            "math_drop": "md",
            "followers_io": "fio",
        }

        compact_players = {}
        for username, entry in self.stats.items():
            if isinstance(entry, list):
                stats_list = entry
                gb_full = {}
                recent = []
            else:
                stats_list = entry.get("stats", [])
                gb_full = entry.get("game_breakdown", {}) or {}
                recent = entry.get("recent_games", [])

            gb = {short_map.get(k, k): v for k, v in gb_full.items()}
            compact_entry = {"s": stats_list}
            if gb:
                compact_entry["gb"] = gb
            if recent:
                compact_entry["rg"] = recent
            compact_players[username] = compact_entry

        web_data = {"lu": last_updated, "tgr": total_games_recorded, "p": compact_players}

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(web_data, f, ensure_ascii=False, separators=(",", ":"))
        print(f"Exported web stats to {output_path}")

    def export_partitioned_stats(self, base_dir: str = "website/public/api"):
        """
        Export player statistics partitioned by first letter for efficient loading.
        Creates:
        - api/players/a.json, api/players/b.json, etc. (one file per letter)
        - api/players/index.json (list of all players with basic info)
        """
        from collections import defaultdict

        short_map = {
            "platformer_race": "pr",
            "obstacle_course": "oc",
            "battle_royale": "br",
            "fighter_arena": "fa",
            "snake_escape": "se",
            "team_battle": "tb",
            "gorillas_vs_followers": "gv",
            "heads_or_tails": "ht",
            "wheel_spinner": "ws",
            "mini_golf": "mg",
            "math_drop": "md",
            "followers_io": "fio",
        }

        # Group players by first letter
        players_by_letter = defaultdict(dict)
        player_index = []
        all_time_leaderboard = []
        preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)

        for username, entry in self.stats.items():
            # Get first letter (lowercase)
            first_letter = username[0].lower() if username else 'z'
            # Handle non-alphabetic characters
            if not first_letter.isalpha():
                first_letter = '0'

            # Prepare compact entry
            if isinstance(entry, list):
                stats_list = entry
                gb_full = {}
                recent = []
            else:
                stats_list = entry.get("stats", [])
                gb_full = entry.get("game_breakdown", {}) or {}
                recent = entry.get("recent_games", [])

            gb = {short_map.get(k, k): v for k, v in gb_full.items()}
            compact_entry = {"s": stats_list}
            if gb:
                compact_entry["gb"] = gb
            if recent:
                compact_entry["rg"] = recent

            players_by_letter[first_letter][username] = compact_entry

            points = stats_list[0] if stats_list else 0
            games = stats_list[1] if len(stats_list) > 1 else 0
            best = stats_list[2] if len(stats_list) > 2 else 0
            total_placement = stats_list[3] if len(stats_list) > 3 else 0
            wins = stats_list[4] if len(stats_list) > 4 else 0
            top3 = stats_list[5] if len(stats_list) > 5 else 0
            top10 = stats_list[6] if len(stats_list) > 6 else 0
            total_kills = stats_list[11] if len(stats_list) > 11 else 0

            # Add to index (just basic info for quick lookups)
            player_index.append({
                "u": username,  # username
                "p": points,  # total points
                "g": games,  # games played
                "l": first_letter  # letter group
            })

            all_time_leaderboard.append({
                "u": username,
                "p": round(points, 1),
                "g": games,
                "w": wins,
                "b": best,
                "t": total_placement,
                "k": total_kills,
                "t3": top3,
                "t10": top10
            })

        # Create players directory
        players_dir = os.path.join(base_dir, "players")
        os.makedirs(players_dir, exist_ok=True)

        # Export each letter group to its own file
        for letter in sorted(players_by_letter.keys()):
            letter_file = os.path.join(players_dir, f"{letter}.json")
            letter_data = {
                "letter": letter,
                "count": len(players_by_letter[letter]),
                "players": players_by_letter[letter]
            }

            with open(letter_file, "w", encoding="utf-8") as f:
                json.dump(letter_data, f, ensure_ascii=False, separators=(",", ":"))

        # Sort index by points descending
        player_index.sort(key=lambda x: x["p"], reverse=True)

        # Create index file
        index_data = {
            "lu": self.metadata.get("last_updated") or datetime.now().isoformat(),
            "tgr": self.metadata.get("total_games_recorded", 0),
            "total_players": len(player_index),
            "letters": sorted(players_by_letter.keys()),
            "players": player_index
        }

        index_file = os.path.join(players_dir, "index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))

        # Export all-time leaderboard (compact)
        leaderboards_dir = os.path.join(base_dir, "leaderboards")
        os.makedirs(leaderboards_dir, exist_ok=True)

        all_time_leaderboard.sort(key=lambda x: x["p"], reverse=True)
        for i, entry in enumerate(all_time_leaderboard):
            entry["r"] = i + 1

        last_updated = self.metadata.get("last_updated") or datetime.now().isoformat()
        all_time_data = {
            "scope": "all_time",
            "lu": last_updated,
            "total_players": len(all_time_leaderboard),
            "leaderboard": all_time_leaderboard
        }

        all_time_file = os.path.join(leaderboards_dir, "all_time.json")
        with open(all_time_file, "w", encoding="utf-8") as f:
            json.dump(all_time_data, f, ensure_ascii=False, separators=(",", ":"))

        if preview_limit > 0 and len(all_time_leaderboard) > preview_limit:
            preview_data = {
                "scope": "all_time",
                "lu": last_updated,
                "total_players": len(all_time_leaderboard),
                "is_preview": True,
                "preview_limit": preview_limit,
                "total_results": len(all_time_leaderboard),
                "leaderboard": all_time_leaderboard[:preview_limit]
            }
            preview_file = os.path.join(leaderboards_dir, "all_time_top.json")
            with open(preview_file, "w", encoding="utf-8") as f:
                json.dump(preview_data, f, ensure_ascii=False, separators=(",", ":"))

        print(f"Exported partitioned player stats:")
        print(f"   {len(players_by_letter)} letter files -> {players_dir}/")
        print(f"   Index file -> {index_file}")
        print(f"   Total players: {len(player_index)}")

    @staticmethod
    def rebuild_from_games(
        games: List[Dict],
        stats_file: str = "player_statistics.json",
        preserve_highscores: bool = True,
        progress_interval: int | None = None,
    ) -> "PlayerStatistics":
        """
        Rebuild player statistics from a list of game dicts.
        Returns a PlayerStatistics instance with updated stats.
        """
        stats = PlayerStatistics(stats_file)
        existing_metadata = dict(stats.metadata)
        stats.stats = {}
        stats.metadata = {
            "last_updated": existing_metadata.get("last_updated", ""),
            "total_games_recorded": 0,
            "game_highscores": existing_metadata.get("game_highscores", {}) if preserve_highscores else {},
        }

        non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])
        if progress_interval is None:
            try:
                progress_interval = int(getattr(config, "STATS_REBUILD_PROGRESS_INTERVAL", 50))
            except Exception:
                progress_interval = 50

        def _to_int(value, default=0):
            try:
                return int(value)
            except Exception:
                return default

        def _to_float(value, default=0.0):
            try:
                return float(value)
            except Exception:
                return default

        processed = 0
        for game in games or []:
            if not isinstance(game, dict):
                continue
            if game.get("non_scoring") or game.get("game_type") in non_scoring_types:
                continue
            results = game.get("results") or []
            total_participants = game.get("total_participants") or len(results)
            game_type = game.get("game_type") or ""
            game_id = game.get("game_id") or ""

            for result in results:
                if not isinstance(result, dict):
                    continue
                username = result.get("username")
                if not username:
                    continue
                placement = result.get("placement") or result.get("rank") or 0
                points = result.get("points", 0) or 0
                survival_time = result.get("survival_time", 0) or 0
                kills = result.get("kills", 0) or 0
                damage = result.get("damage", result.get("damage_dealt", 0)) or 0

                stats.update_player_stats(
                    username=username,
                    placement=_to_int(placement, 0),
                    points_earned=_to_float(points, 0.0),
                    survival_time=_to_float(survival_time, 0.0),
                    total_participants=_to_int(total_participants, 0),
                    kills=_to_int(kills, 0),
                    damage_dealt=_to_float(damage, 0.0),
                    game_type=game_type,
                    game_id=game_id,
                )

            processed += 1
            if progress_interval and processed % progress_interval == 0:
                print(f"Processed {processed}/{len(games)} games for stats rebuild")

        stats.metadata["total_games_recorded"] = processed
        stats.save_statistics()
        return stats

