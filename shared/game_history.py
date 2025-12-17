"""
Game History Module
Manages individual game session records for website display
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import config


class GameHistory:
    """
    Manages persistent game episode history for website stats display
    Stores complete results from each game session
    """

    def __init__(self, history_file: str = "game_history.json"):
        """
        Initialize game history manager

        Args:
            history_file: Path to JSON file for storing game history
        """
        self.history_file = history_file
        self.history: Dict = {"games": []}
        self.load_history()

    def load_history(self):
        """
        Load game history from JSON file
        Creates new file if it doesn't exist
        """
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                    # Ensure 'games' key exists
                    if "games" not in self.history:
                        self.history["games"] = []
                print(f"Loaded history for {len(self.history['games'])} games")
            except Exception as e:
                print(f"Error loading game history: {e}")
                self.history = {"games": []}
        else:
            print("No existing game history file, starting fresh")
            self.history = {"games": []}

    def save_history(self):
        """
        Save game history to JSON file
        Skips saving if TEST_MODE is enabled in config
        """
        if config.TEST_MODE:
            print("TEST MODE: Game history not saved")
            return

        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            print(f"Game history saved ({len(self.history['games'])} total games)")
        except Exception as e:
            print(f"Error saving game history: {e}")

    def export_web_history(self, output_path: str = "website/public/game_history_web.json"):
        """
        Export the game history to the website/public path.
        Uses the current in-memory history structure.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, separators=(",", ":"))
        print(f"Exported web game history to {output_path}")

    def export_partitioned_history(self, base_dir: str = "website/public/api"):
        """
        Export game history partitioned by day for efficient loading.
        Creates:
        - api/days/1.json, api/days/2.json, etc. (one file per day)
        - api/index.json (metadata about available days)
        """
        from collections import defaultdict

        # Group games by day
        games_by_day = defaultdict(list)
        all_days = set()

        for game in self.history.get("games", []):
            day = game.get("day_number")
            if day is not None:
                games_by_day[day].append(game)
                all_days.add(day)

        # Create days directory
        days_dir = os.path.join(base_dir, "days")
        os.makedirs(days_dir, exist_ok=True)

        # Export each day to its own file
        day_metadata = []
        for day_num in sorted(all_days):
            day_games = games_by_day[day_num]
            day_file = os.path.join(days_dir, f"{day_num}.json")

            # Get unique game types for this day
            game_types = list(set(g.get("game_type") for g in day_games))
            total_participants = len(set(
                r.get("username")
                for g in day_games
                for r in g.get("results", [])
            ))

            day_data = {
                "day_number": day_num,
                "games": day_games,
                "total_games": len(day_games),
                "game_types": game_types,
                "total_participants": total_participants
            }

            with open(day_file, "w", encoding="utf-8") as f:
                json.dump(day_data, f, ensure_ascii=False, separators=(",", ":"))

            # Add to metadata
            day_metadata.append({
                "day": day_num,
                "games": len(day_games),
                "types": game_types,
                "participants": total_participants
            })

        # Create index file with metadata
        index_data = {
            "last_updated": datetime.now().isoformat(),
            "total_days": len(all_days),
            "total_games": len(self.history.get("games", [])),
            "available_days": sorted(all_days),
            "days_metadata": day_metadata
        }

        index_file = os.path.join(base_dir, "index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))

        print(f"Exported partitioned game history:")
        print(f"   {len(all_days)} day files -> {days_dir}/")
        print(f"   Index file -> {index_file}")
        print(f"   Total games: {len(self.history.get('games', []))}")

    def record_game_session(
        self,
        game_type: str,
        game_display_name: str,
        day_number: int,
        results: List[Dict]
    ):
        """
        Record a complete game session with all player results

        Args:
            game_type: Game type identifier (e.g., "battle_royale")
            game_display_name: Human-readable game name (e.g., "Battle Royale")
            day_number: Episode/day number for this game
            results: List of player result dictionaries with keys:
                - username: str
                - placement: int (final rank)
                - points: float (points earned)
                - survival_time: float (seconds survived)
                - kills: int (optional)
                - damage: float (optional)
        """
        # Generate unique game ID
        timestamp = datetime.now().isoformat()
        date_prefix = datetime.now().strftime("%Y%m%d")

        # Count games of this type today to create unique ID
        games_today = [
            g for g in self.history["games"]
            if g.get("game_id", "").startswith(f"{date_prefix}_") and
            g.get("game_type") == game_type
        ]
        game_sequence = len(games_today) + 1

        game_id = f"{date_prefix}_{game_sequence:03d}_{game_type}"

        # Sort results by placement
        sorted_results = sorted(results, key=lambda x: x.get("placement", 999))

        # Add rank (1-indexed placement for display)
        for i, result in enumerate(sorted_results, start=1):
            result["rank"] = i

        # Create game record
        game_record = {
            "game_id": game_id,
            "game_type": game_type,
            "game_display_name": game_display_name,
            "day_number": day_number,
            "timestamp": timestamp,
            "total_participants": len(results),
            "results": sorted_results
        }

        # Add to history
        self.history["games"].append(game_record)

        print(f"\nGame session recorded:")
        print(f"   ID: {game_id}")
        print(f"   Type: {game_display_name}")
        print(f"   Day: {day_number}")
        print(f"   Participants: {len(results)}")

        # Save to file
        self.save_history()

    def get_game_by_id(self, game_id: str) -> Optional[Dict]:
        """
        Get a specific game by its ID

        Args:
            game_id: Unique game identifier

        Returns:
            Game record dictionary or None if not found
        """
        for game in self.history["games"]:
            if game.get("game_id") == game_id:
                return game
        return None

    def get_games_by_type(self, game_type: str) -> List[Dict]:
        """
        Get all games of a specific type

        Args:
            game_type: Game type identifier (e.g., "battle_royale")

        Returns:
            List of game records
        """
        return [
            game for game in self.history["games"]
            if game.get("game_type") == game_type
        ]

    def get_recent_games(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent games

        Args:
            limit: Maximum number of games to return

        Returns:
            List of game records, sorted by most recent first
        """
        sorted_games = sorted(
            self.history["games"],
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        return sorted_games[:limit]

    def get_player_game_history(self, username: str, limit: int = 10) -> List[Dict]:
        """
        Get game history for a specific player

        Args:
            username: Player username
            limit: Maximum number of games to return

        Returns:
            List of game records where player participated
        """
        player_games = []

        for game in self.history["games"]:
            # Check if player participated in this game
            for result in game.get("results", []):
                if result.get("username") == username:
                    # Add game info with player's result
                    player_game = {
                        "game_id": game.get("game_id"),
                        "game_type": game.get("game_type"),
                        "game_display_name": game.get("game_display_name"),
                        "day_number": game.get("day_number"),
                        "timestamp": game.get("timestamp"),
                        "placement": result.get("placement"),
                        "points": result.get("points"),
                        "survival_time": result.get("survival_time"),
                        "kills": result.get("kills", 0),
                        "damage": result.get("damage", 0.0)
                    }
                    player_games.append(player_game)
                    break

        # Sort by timestamp, most recent first
        player_games.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return player_games[:limit]
