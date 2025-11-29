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
