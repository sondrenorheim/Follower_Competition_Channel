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

    def _generate_monthly_leaderboards(self, leaderboards_dir) -> dict:
        """
        Generate pre-computed monthly leaderboards.
        Creates one file per month: leaderboards/2024-12.json, leaderboards/2025-01.json, etc.
        Also creates per-game-type leaderboards: leaderboards/2024-12_battle_royale.json, etc.

        Args:
            leaderboards_dir: Path object for the leaderboards directory

        Returns:
            Dict mapping month keys (YYYY-MM) to metadata about that month's leaderboard
        """
        from collections import defaultdict

        # Aggregate stats by month (all games) and by game type
        def stats_bucket():
            return {
                "points": 0.0,
                "games": 0,
                "wins": 0,
                "best_placement": float('inf'),
                "total_kills": 0,
                "total_placement": 0
            }

        monthly_data = defaultdict(lambda: defaultdict(stats_bucket))
        monthly_data_by_type = defaultdict(lambda: defaultdict(lambda: defaultdict(stats_bucket)))

        non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])

        for game in self.history.get('games', []):
            if game.get("non_scoring") or game.get("game_type") in non_scoring_types:
                continue
            timestamp = game.get("timestamp", "")
            if not timestamp or len(timestamp) < 7:
                continue

            # Extract YYYY-MM from timestamp
            month_key = timestamp[:7]  # "2024-12" format

            game_type = game.get("game_type") or ""

            for result in game.get("results", []):
                username = result.get("username")
                if not username:
                    continue

                player = monthly_data[month_key][username]
                player["points"] += result.get("points", 0)
                player["games"] += 1
                placement = result.get("placement", 9999)
                if placement == 1:
                    player["wins"] += 1
                if placement < player["best_placement"]:
                    player["best_placement"] = placement
                player["total_kills"] += result.get("kills", 0)
                player["total_placement"] += placement

                if game_type:
                    typed_player = monthly_data_by_type[month_key][game_type][username]
                    typed_player["points"] += result.get("points", 0)
                    typed_player["games"] += 1
                    if placement == 1:
                        typed_player["wins"] += 1
                    if placement < typed_player["best_placement"]:
                        typed_player["best_placement"] = placement
                    typed_player["total_kills"] += result.get("kills", 0)
                    typed_player["total_placement"] += placement

        def write_leaderboard_file(month_key, players, game_type=None):
            leaderboard = []
            for username, stats in players.items():
                leaderboard.append({
                    "u": username,
                    "p": round(stats["points"], 1),
                    "g": stats["games"],
                    "w": stats["wins"],
                    "b": stats["best_placement"] if stats["best_placement"] != float('inf') else 0,
                    "k": stats["total_kills"],
                    "t": stats["total_placement"]
                })

            leaderboard.sort(key=lambda x: x["p"], reverse=True)
            for i, entry in enumerate(leaderboard):
                entry["r"] = i + 1

            filename = f"{month_key}.json" if not game_type else f"{month_key}_{game_type}.json"
            month_data = {
                "month": month_key,
                "game_type": game_type or "all",
                "total_players": len(leaderboard),
                "leaderboard": leaderboard
            }

            with open(leaderboards_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(month_data, f, ensure_ascii=False, separators=(',', ':'))

        # Write monthly leaderboard files
        monthly_stats = {}

        for month_key in sorted(monthly_data.keys()):
            players = monthly_data[month_key]
            write_leaderboard_file(month_key, players)

            for game_type, typed_players in sorted(monthly_data_by_type[month_key].items()):
                write_leaderboard_file(month_key, typed_players, game_type)

            monthly_stats[month_key] = {
                "players": len(players),
                "games": len([g for g in self.history.get('games', []) if g.get("timestamp", "").startswith(month_key)])
            }

        return monthly_stats

    def export_partitioned_history(self, base_dir: str = "website/public/api"):
        """
        Export game history partitioned into:
        1. Individual game files: api/games/{game_id}.json
        2. Day summary files: api/days/{day_number}.json
        3. Game type indexes: api/types/{game_type}.json
        4. Monthly leaderboards: api/leaderboards/{YYYY-MM}.json (plus per-game-type files)
        5. Player history index: api/player_history/{letter}.json + index.json
        6. Master index: api/index.json

        This creates many small files instead of one giant file,
        solving LFS budget issues and improving load performance.
        """
        from collections import defaultdict
        from pathlib import Path

        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        games_dir = base_path / "games"
        days_dir = base_path / "days"
        types_dir = base_path / "types"
        leaderboards_dir = base_path / "leaderboards"

        games_dir.mkdir(exist_ok=True)
        days_dir.mkdir(exist_ok=True)
        types_dir.mkdir(exist_ok=True)
        leaderboards_dir.mkdir(exist_ok=True)

        # Organize games
        games_by_day = defaultdict(list)
        games_by_type = defaultdict(list)
        all_days = set()
        all_types = set()

        # Step 1: Export individual game files
        for game in self.history.get("games", []):
            game_id = game.get("game_id")
            day = game.get("day_number")
            game_type = game.get("game_type")

            if not game_id:
                continue

            # Write individual game file
            game_file = games_dir / f"{game_id}.json"
            with open(game_file, 'w', encoding='utf-8') as f:
                json.dump(game, f, ensure_ascii=False, separators=(',', ':'))

            # Organize for aggregation
            if day is not None:
                games_by_day[day].append(game)
                all_days.add(day)

            if game_type:
                games_by_type[game_type].append(game)
                all_types.add(game_type)

        # Step 2: Export day summary files (metadata only, not full results)
        day_metadata = []
        for day_num in sorted(all_days):
            day_games = games_by_day[day_num]
            day_file = days_dir / f"{day_num}.json"

            day_summary = {
                "day_number": day_num,
                "total_games": len(day_games),
                "games": [
                    {
                        "game_id": g.get("game_id"),
                        "game_type": g.get("game_type"),
                        "game_display_name": g.get("game_display_name"),
                        "timestamp": g.get("timestamp"),
                        "total_participants": g.get("total_participants"),
                        "non_scoring": g.get("non_scoring", False)
                    }
                    for g in day_games
                ]
            }

            with open(day_file, 'w', encoding='utf-8') as f:
                json.dump(day_summary, f, ensure_ascii=False, separators=(',', ':'))

            game_types = list(set(g.get("game_type") for g in day_games if g.get("game_type")))
            total_participants = len(set(
                r.get("username")
                for g in day_games
                for r in g.get("results", [])
                if r.get("username")
            ))

            day_metadata.append({
                "day": day_num,
                "games": len(day_games),
                "types": game_types,
                "participants": total_participants
            })

        # Step 3: Export game type indexes
        type_metadata = []
        for game_type in sorted(all_types):
            type_games = games_by_type[game_type]
            type_file = types_dir / f"{game_type}.json"

            type_index = {
                "game_type": game_type,
                "total_games": len(type_games),
                "games": [
                    {
                        "game_id": g.get("game_id"),
                        "day_number": g.get("day_number"),
                        "timestamp": g.get("timestamp"),
                        "total_participants": g.get("total_participants")
                    }
                    for g in sorted(type_games, key=lambda x: x.get("timestamp", ""), reverse=True)
                ]
            }

            with open(type_file, 'w', encoding='utf-8') as f:
                json.dump(type_index, f, ensure_ascii=False, separators=(',', ':'))

            type_metadata.append({
                "type": game_type,
                "games": len(type_games)
            })

        # Step 4: Generate monthly leaderboards
        monthly_stats = self._generate_monthly_leaderboards(leaderboards_dir)

        # Step 5: Export player history index (compact, per-letter)
        player_history_dir = base_path / "player_history"
        player_history_dir.mkdir(exist_ok=True)

        points_scale = 10
        player_histories = defaultdict(lambda: defaultdict(list))
        game_meta = []

        games_sorted = sorted(
            self.history.get("games", []),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        for game in games_sorted:
            game_id = game.get("game_id")
            if not game_id:
                continue

            game_index = len(game_meta)
            game_meta.append([
                game_id,
                game.get("game_type"),
                game.get("day_number"),
                game.get("timestamp")
            ])

            for result in game.get("results", []):
                username = result.get("username")
                if not username:
                    continue

                first_char = username[0].lower()
                letter = first_char if first_char.isalpha() else "0"

                placement = result.get("placement", 0) or 0
                points = result.get("points", 0) or 0
                kills = result.get("kills", 0) or 0
                points_scaled = int(round(points * points_scale))

                player_histories[letter][username].append([
                    game_index,
                    placement,
                    points_scaled,
                    kills
                ])

        for letter in sorted(player_histories.keys()):
            letter_players = player_histories[letter]
            letter_data = {
                "letter": letter,
                "count": len(letter_players),
                "players": letter_players
            }
            letter_file = player_history_dir / f"{letter}.json"
            with open(letter_file, 'w', encoding='utf-8') as f:
                json.dump(letter_data, f, ensure_ascii=False, separators=(',', ':'))

        history_index = {
            "lu": datetime.now().isoformat(),
            "points_scale": points_scale,
            "game_count": len(game_meta),
            "games": game_meta
        }
        history_index_file = player_history_dir / "index.json"
        with open(history_index_file, 'w', encoding='utf-8') as f:
            json.dump(history_index, f, ensure_ascii=False, separators=(',', ':'))

        # Step 6: Create master index
        index_data = {
            "last_updated": datetime.now().isoformat(),
            "total_games": len(self.history.get("games", [])),
            "total_days": len(all_days),
            "available_days": sorted(all_days),
            "days_metadata": day_metadata,
            "game_types": sorted(all_types),
            "types_metadata": type_metadata,
            "available_months": sorted(monthly_stats.keys())
        }

        index_file = base_path / "index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(',', ':'))

        print(f"Exported partitioned game history:")
        print(f"   {len(self.history.get('games', []))} individual game files -> {games_dir}/")
        print(f"   {len(all_days)} day summaries -> {days_dir}/")
        print(f"   {len(all_types)} game type indexes -> {types_dir}/")
        print(f"   {len(monthly_stats)} monthly leaderboards -> {leaderboards_dir}/")
        print(f"   {len(player_histories)} player history letter files -> {player_history_dir}/")
        print(f"   Player history index -> {history_index_file}")
        print(f"   Master index -> {index_file}")

    def record_game_session(
        self,
        game_type: str,
        game_display_name: str,
        day_number: int,
        results: List[Dict],
        non_scoring: bool = False
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
            non_scoring: If True, this game should not affect overall leaderboards
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
            "results": sorted_results,
            "non_scoring": non_scoring
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
