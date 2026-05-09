"""
Game History Module
Manages individual game session records for website display
"""

import json
import os
import re
import shutil
from datetime import datetime
from typing import Dict, List, Optional

import config
from . import results_store
from .platform_targets import (
    is_noncanonical_record_game_type,
    resolve_record_game_display_name,
    resolve_record_game_type,
)
from .website_platforms import export_platform_partitions


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
        self.skip_persistence_loads = bool(getattr(config, "TEST_SKIP_PERSISTENCE_LOADS", False))
        self.light_mode = (
            bool(getattr(config, "SIMULATION_LIGHT_MODE", False))
            or bool(getattr(config, "TEST_MINIMAL_PLAYERS", False))
            or self.skip_persistence_loads
        )
        self._light_id_counter = 0
        self._light_save_notice_printed = False

        if self.light_mode:
            if bool(getattr(config, "TEST_MINIMAL_PLAYERS", False)):
                print("TEST_MINIMAL_PLAYERS: Skipping game history load.")
            elif self.skip_persistence_loads:
                print("TEST MODE: Skipping game history load for this render run.")
            else:
                print("SIMULATION-LIGHT MODE: Skipping game history load (event append only).")
        else:
            self.load_history()

    @staticmethod
    def resolve_history_file(preferred: str = "game_history.json") -> str:
        """
        Pick the most complete history file available.
        Preference order is based on file size and valid JSON structure.
        """
        candidates = []
        preferred_path = preferred
        if os.path.exists(preferred_path):
            candidates.append(preferred_path)

        recovered = "game_history_recovered.json"
        if os.path.exists(recovered):
            candidates.append(recovered)

        try:
            for name in os.listdir("."):
                if name.startswith("game_history_backup_") and name.endswith(".json"):
                    candidates.append(name)
        except Exception:
            pass

        def _size(path: str) -> int:
            try:
                return os.path.getsize(path)
            except Exception:
                return 0

        # Try largest files first.
        candidates = sorted(set(candidates), key=_size, reverse=True)

        for path in candidates:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("games"), list):
                    return path
            except Exception:
                continue

        return preferred

    @staticmethod
    def merge_history_files(primary_path: str, secondary_path: str) -> Dict:
        """
        Merge two history files, keeping the most complete entry per game_id.
        """
        history = {"games": []}
        games_by_id: Dict[str, Dict] = {}

        def _load(path: str) -> Dict:
            if not path or not os.path.exists(path):
                return {"games": []}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("games"), list):
                    return data
            except Exception:
                pass
            return {"games": []}

        primary = _load(primary_path)
        secondary = _load(secondary_path)

        for game in secondary.get("games", []):
            game_id = game.get("game_id")
            if not game_id:
                continue
            games_by_id[game_id] = game

        for game in primary.get("games", []):
            game_id = game.get("game_id")
            if not game_id:
                continue
            existing = games_by_id.get(game_id)
            if existing is None or len(game.get("results", []) or []) > len(existing.get("results", []) or []):
                games_by_id[game_id] = game

        history["games"] = list(games_by_id.values())
        return history

    def load_history(self):
        """
        Load game history from JSON file
        Creates new file if it doesn't exist
        """
        history_path = os.path.abspath(self.history_file)
        best_payload, best_source = results_store.load_best_game_history(self.history_file)
        if not isinstance(best_payload, dict):
            best_payload = {"games": []}
        if not isinstance(best_payload.get("games"), list):
            best_payload["games"] = []
        self.history = best_payload

        game_count = len(self.history.get("games", []))
        if game_count == 0 and not os.path.exists(self.history_file):
            print("No existing game history file, starting fresh")
            return

        source_text = best_source or history_path
        print(f"Loaded history for {game_count} games")

        if best_source and os.path.abspath(best_source) != history_path:
            try:
                results_store.atomic_write_json(self.history_file, self.history)
                results_store.write_recovery_log(
                    {
                        "type": "history_recovered",
                        "target_file": self.history_file,
                        "source": source_text,
                        "game_count": game_count,
                    }
                )
                print(f"Recovered {self.history_file} from {source_text}")
            except Exception as e:
                print(f"Warning: failed to persist recovered history: {e}")

    def save_history(self):
        """
        Save game history to JSON file
        Skips saving if TEST_MODE is enabled in config
        """
        if self.light_mode:
            if not self._light_save_notice_printed:
                print(
                    "SIMULATION-LIGHT MODE: game_history.json not persisted now "
                    "(run rebuild post-step)."
                )
                self._light_save_notice_printed = True
            return

        if config.TEST_MODE:
            print("TEST MODE: Game history not saved")
            return

        try:
            results_store.atomic_write_json(self.history_file, self.history)
            print(f"Game history saved ({len(self.history['games'])} total games)")
        except Exception as e:
            print(f"Error saving game history: {e}")

    def _resolved_runtime_game_identity(self, game_type: str, game_display_name: str) -> tuple[str, str]:
        current_mode = str(getattr(config, "GAME_MODE", "") or "").strip().lower()
        normalized_type = str(game_type or "").strip().lower()
        if current_mode and normalized_type == current_mode:
            platform_target = getattr(config, "PLATFORM_TARGET", "instagram")
            audience_variant = getattr(config, "FOLLOWER_AUDIENCE_VARIANT", "default")
            resolved_type = resolve_record_game_type(
                current_mode,
                platform_target,
                audience_variant=audience_variant,
            )
            resolved_display_name = resolve_record_game_display_name(
                current_mode,
                platform_target,
                audience_variant=audience_variant,
            )
            return resolved_type, resolved_display_name
        return str(game_type or ""), str(game_display_name or "")

    def _canonical_games(self, games: Optional[List[Dict]] = None) -> List[Dict]:
        source_games = self.history.get("games", []) if games is None else games
        return [
            game for game in source_games
            if not is_noncanonical_record_game_type(game.get("game_type"))
        ]

    def export_web_history(self, output_path: str = "website/public/game_history_web.json"):
        """
        Export the game history to the website/public path.
        Uses the current in-memory history structure.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        payload = {"games": self._canonical_games()}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        print(f"Exported web game history to {output_path}")

    def _generate_monthly_leaderboards(self, leaderboards_dir) -> tuple[dict, set[str]]:
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
        preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)

        written_files: set[str] = set()

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

        canonical_games = self._canonical_games()

        for game in canonical_games:
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
            written_files.add(filename)

            if preview_limit > 0 and len(leaderboard) > preview_limit:
                preview_filename = f"{month_key}_top.json" if not game_type else f"{month_key}_{game_type}_top.json"
                preview_data = {
                    "month": month_key,
                    "game_type": game_type or "all",
                    "total_players": len(leaderboard),
                    "is_preview": True,
                    "preview_limit": preview_limit,
                    "total_results": len(leaderboard),
                    "leaderboard": leaderboard[:preview_limit]
                }
                with open(leaderboards_dir / preview_filename, 'w', encoding='utf-8') as f:
                    json.dump(preview_data, f, ensure_ascii=False, separators=(',', ':'))
                written_files.add(preview_filename)

        # Write monthly leaderboard files
        monthly_stats = {}

        for month_key in sorted(monthly_data.keys()):
            players = monthly_data[month_key]
            write_leaderboard_file(month_key, players)

            for game_type, typed_players in sorted(monthly_data_by_type[month_key].items()):
                write_leaderboard_file(month_key, typed_players, game_type)

            monthly_stats[month_key] = {
                "players": len(players),
                "games": len([g for g in canonical_games if g.get("timestamp", "").startswith(month_key)])
            }

        return monthly_stats, written_files

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

        preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)
        non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])

        # Create directory structure
        games_dir = base_path / "games"
        days_dir = base_path / "days"
        types_dir = base_path / "types"
        leaderboards_dir = base_path / "leaderboards"

        games_dir.mkdir(exist_ok=True)
        days_dir.mkdir(exist_ok=True)
        types_dir.mkdir(exist_ok=True)
        leaderboards_dir.mkdir(exist_ok=True)

        def remove_stale_json(directory: Path, expected_files: set[str], pattern: Optional[re.Pattern] = None):
            removed = 0
            for path in directory.glob("*.json"):
                if pattern is not None and not pattern.match(path.name):
                    continue
                if path.name in expected_files:
                    continue
                try:
                    path.unlink()
                    removed += 1
                except Exception:
                    continue
            return removed

        # Organize games
        games_by_day = defaultdict(list)
        games_by_type = defaultdict(list)
        all_days = set()
        all_types = set()
        expected_game_files: set[str] = set()

        # Step 1: Export individual game files
        canonical_games = self._canonical_games()

        for game in canonical_games:
            game_id = game.get("game_id")
            day = game.get("day_number")
            game_type = game.get("game_type")

            if not game_id:
                continue

            # Write individual game file
            game_file = games_dir / f"{game_id}.json"
            with open(game_file, 'w', encoding='utf-8') as f:
                json.dump(game, f, ensure_ascii=False, separators=(',', ':'))
            expected_game_files.add(game_file.name)

            if preview_limit > 0:
                results = game.get("results") or []
                preview_game = {
                    "game_id": game_id,
                    "game_type": game.get("game_type"),
                    "game_display_name": game.get("game_display_name"),
                    "day_number": game.get("day_number"),
                    "timestamp": game.get("timestamp"),
                    "total_participants": game.get("total_participants"),
                    "results": results[:preview_limit],
                    "non_scoring": game.get("non_scoring", False),
                    "is_preview": True,
                    "preview_limit": preview_limit,
                    "total_results": len(results)
                }
                preview_file = games_dir / f"{game_id}_top.json"
                with open(preview_file, 'w', encoding='utf-8') as f:
                    json.dump(preview_game, f, ensure_ascii=False, separators=(',', ':'))
                expected_game_files.add(preview_file.name)

            # Organize for aggregation
            if day is not None:
                games_by_day[day].append(game)
                all_days.add(day)

            if game_type:
                games_by_type[game_type].append(game)
                all_types.add(game_type)

        remove_stale_json(games_dir, expected_game_files)

        # Step 2: Export day summary files (metadata only, not full results)
        day_metadata = []
        expected_day_files: set[str] = set()
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
            expected_day_files.add(day_file.name)

            scoring_games = [
                g for g in day_games
                if not g.get("non_scoring") and g.get("game_type") not in non_scoring_types
            ]
            aggregated = {}
            for game in scoring_games:
                for result in game.get("results", []):
                    username = result.get("username")
                    if not username:
                        continue
                    entry = aggregated.setdefault(username, {
                        "username": username,
                        "points": 0,
                        "kills": 0,
                        "survival_time": 0,
                        "appearances": 0
                    })
                    entry["points"] += result.get("points", 0) or 0
                    entry["kills"] += result.get("kills", 0) or 0
                    entry["survival_time"] += result.get("survival_time", 0) or 0
                    entry["appearances"] += 1

            aggregated_results = sorted(
                aggregated.values(),
                key=lambda x: x.get("points", 0),
                reverse=True
            )
            total_participants = len(aggregated_results)
            timestamp = max(
                (g.get("timestamp") for g in scoring_games if g.get("timestamp")),
                default=None
            )

            aggregate_game = {
                "game_id": f"all_day_{day_num}",
                "game_type": "all",
                "game_display_name": "All Games",
                "day_number": day_num,
                "timestamp": timestamp,
                "total_participants": total_participants,
                "results": aggregated_results
            }
            aggregate_file = days_dir / f"{day_num}_aggregate.json"
            with open(aggregate_file, 'w', encoding='utf-8') as f:
                json.dump(aggregate_game, f, ensure_ascii=False, separators=(',', ':'))
            expected_day_files.add(aggregate_file.name)

            if preview_limit > 0:
                aggregate_preview = {
                    "game_id": aggregate_game["game_id"],
                    "game_type": aggregate_game["game_type"],
                    "game_display_name": aggregate_game["game_display_name"],
                    "day_number": aggregate_game["day_number"],
                    "timestamp": aggregate_game["timestamp"],
                    "total_participants": total_participants,
                    "results": aggregated_results[:preview_limit],
                    "is_preview": True,
                    "preview_limit": preview_limit,
                    "total_results": total_participants
                }
                aggregate_preview_file = days_dir / f"{day_num}_aggregate_top.json"
                with open(aggregate_preview_file, 'w', encoding='utf-8') as f:
                    json.dump(aggregate_preview, f, ensure_ascii=False, separators=(',', ':'))
                expected_day_files.add(aggregate_preview_file.name)

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

        remove_stale_json(days_dir, expected_day_files)

        # Step 3: Export game type indexes
        type_metadata = []
        expected_type_files: set[str] = set()
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
            expected_type_files.add(type_file.name)

            type_metadata.append({
                "type": game_type,
                "games": len(type_games)
            })

        remove_stale_json(types_dir, expected_type_files)

        # Step 4: Generate monthly leaderboards
        monthly_stats, monthly_files = self._generate_monthly_leaderboards(leaderboards_dir)
        monthly_pattern = re.compile(r"^\d{4}-\d{2}(?:_.+)?(?:_top)?\.json$")
        remove_stale_json(leaderboards_dir, monthly_files, monthly_pattern)

        # Step 5: Export player history index (compact, per-letter)
        player_history_dir = base_path / "player_history"
        player_history_dir.mkdir(exist_ok=True)
        expected_player_history_files: set[str] = set()

        points_scale = 10
        player_histories = defaultdict(lambda: defaultdict(list))
        game_meta = []

        games_sorted = sorted(
            canonical_games,
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
            expected_player_history_files.add(letter_file.name)

        history_index = {
            "lu": datetime.now().isoformat(),
            "points_scale": points_scale,
            "game_count": len(game_meta),
            "games": game_meta
        }
        history_index_file = player_history_dir / "index.json"
        with open(history_index_file, 'w', encoding='utf-8') as f:
            json.dump(history_index, f, ensure_ascii=False, separators=(',', ':'))
        expected_player_history_files.add(history_index_file.name)
        remove_stale_json(player_history_dir, expected_player_history_files)

        # Step 6: Create master index
        # Load follower count from all_followers_fresh.json
        total_followers = 0
        try:
            from pathlib import Path
            followers_file = Path(config.FOLLOWER_IMPORT_FILE)
            if followers_file.exists():
                with open(followers_file, 'r', encoding='utf-8') as f:
                    followers_data = json.load(f)
                    if isinstance(followers_data, list):
                        total_followers = len(followers_data)
                    elif isinstance(followers_data, dict) and 'followers' in followers_data:
                        total_followers = len(followers_data['followers'])
        except Exception:
            pass

        platforms_metadata, _platform_changed_paths = export_platform_partitions(
            base_path,
            self.history.get("games", []),
            repo_root=Path(".").resolve(),
            avatar_cache_dir="avatar_cache",
            preview_limit=preview_limit,
            total_followers=total_followers,
        )

        index_data = {
            "last_updated": datetime.now().isoformat(),
            "total_games": len(canonical_games),
            "total_days": len(all_days),
            "total_followers": total_followers,
            "results_preview_limit": preview_limit,
            "available_days": sorted(all_days),
            "days_metadata": day_metadata,
            "game_types": sorted(all_types),
            "types_metadata": type_metadata,
            "available_months": sorted(monthly_stats.keys()),
            "platforms": platforms_metadata,
        }

        index_file = base_path / "index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(',', ':'))

        print(f"Exported partitioned game history:")
        print(f"   {len(canonical_games)} individual game files -> {games_dir}/")
        print(f"   {len(all_days)} day summaries -> {days_dir}/")
        print(f"   {len(all_types)} game type indexes -> {types_dir}/")
        print(f"   {len(monthly_stats)} monthly leaderboards -> {leaderboards_dir}/")
        print(f"   {len(player_histories)} player history letter files -> {player_history_dir}/")
        print(f"   Player history index -> {history_index_file}")
        print(f"   Master index -> {index_file}")

    def export_hall_of_fame(
        self,
        base_dir: str = "website/public/api",
        avatar_cache_dir: str = "avatar_cache",
    ):
        """
        Export Hall of Fame data for daily and monthly champions.

        Outputs:
            - {base_dir}/hall_of_fame.json
            - {base_dir}/avatars/{username}.jpg (copied from avatar_cache when available)
        """
        from collections import defaultdict
        from pathlib import Path

        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        avatars_dir = base_path / "avatars"
        avatars_dir.mkdir(exist_ok=True)

        non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])

        daily_points = defaultdict(lambda: defaultdict(float))
        daily_timestamps = {}
        monthly_points = defaultdict(lambda: defaultdict(float))

        for game in self._canonical_games():
            if game.get("non_scoring") or game.get("game_type") in non_scoring_types:
                continue

            day_number = game.get("day_number")
            timestamp = game.get("timestamp") or ""

            if day_number is not None:
                if timestamp and (day_number not in daily_timestamps or timestamp > daily_timestamps[day_number]):
                    daily_timestamps[day_number] = timestamp
                for result in game.get("results", []):
                    username = result.get("username")
                    if not username:
                        continue
                    points = result.get("points", 0) or 0
                    daily_points[day_number][username] += points

            if timestamp and len(timestamp) >= 7:
                month_key = timestamp[:7]
                for result in game.get("results", []):
                    username = result.get("username")
                    if not username:
                        continue
                    points = result.get("points", 0) or 0
                    monthly_points[month_key][username] += points

        def pick_champion(points_map: dict) -> tuple[str, float]:
            sorted_entries = sorted(points_map.items(), key=lambda x: (-x[1], x[0]))
            return sorted_entries[0]

        daily_champions = []
        for day_number, totals in daily_points.items():
            if not totals:
                continue
            winner, points = pick_champion(totals)
            daily_champions.append({
                "day": day_number,
                "username": winner,
                "points": round(points, 2),
                "timestamp": daily_timestamps.get(day_number, "")
            })

        daily_champions.sort(key=lambda x: x["day"], reverse=True)

        monthly_champions = []
        for month_key, totals in monthly_points.items():
            if not totals:
                continue
            winner, points = pick_champion(totals)
            monthly_champions.append({
                "month": month_key,
                "username": winner,
                "points": round(points, 2)
            })

        monthly_champions.sort(key=lambda x: x["month"], reverse=True)

        def safe_filename(value: str) -> str:
            cleaned = []
            for char in value:
                if char.isalnum() or char in ("_", "-", "."):
                    cleaned.append(char)
                else:
                    cleaned.append("_")
            return "".join(cleaned) or "user"

        def find_avatar_file(cache_dir: Path, username: str) -> Optional[Path]:
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                candidate = cache_dir / f"{username}{ext}"
                if candidate.exists():
                    return candidate
            matches = list(cache_dir.glob(f"{username}.*"))
            if matches:
                return matches[0]
            return None

        avatar_cache = Path(avatar_cache_dir)
        avatar_map = {}
        champions = {entry["username"] for entry in daily_champions}
        champions.update(entry["username"] for entry in monthly_champions)

        for username in champions:
            if not avatar_cache.exists():
                break
            src = find_avatar_file(avatar_cache, username)
            if not src:
                continue
            safe_name = safe_filename(username)
            dest = avatars_dir / f"{safe_name}{src.suffix.lower()}"
            try:
                if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
                    shutil.copy2(src, dest)
                avatar_map[username] = f"api/avatars/{dest.name}"
            except Exception:
                continue

        for entry in daily_champions:
            entry["avatar"] = avatar_map.get(entry["username"])

        for entry in monthly_champions:
            entry["avatar"] = avatar_map.get(entry["username"])

        output_path = base_path / "hall_of_fame.json"
        payload = {
            "last_updated": datetime.now().isoformat(),
            "daily_champions": daily_champions,
            "monthly_champions": monthly_champions
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

        print(f"Exported hall of fame data -> {output_path}")

    def record_game_session(
        self,
        game_type: str,
        game_display_name: str,
        day_number: int,
        results: List[Dict],
        non_scoring: bool = False,
        extra_data: Optional[Dict] = None,
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
        game_type, game_display_name = self._resolved_runtime_game_identity(game_type, game_display_name)
        if is_noncanonical_record_game_type(game_type):
            non_scoring = True

        # Generate unique game ID
        timestamp = datetime.now().isoformat()
        date_prefix = datetime.now().strftime("%Y%m%d")
        if self.light_mode:
            # In simulation-light mode, history is not loaded, so use time+counter for uniqueness.
            self._light_id_counter += 1
            time_token = datetime.now().strftime("%H%M%S%f")
            game_id = f"{date_prefix}_{time_token}_{self._light_id_counter:03d}_{game_type}"
        else:
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
        if extra_data:
            for key, value in extra_data.items():
                if key not in game_record:
                    game_record[key] = value

        # Add to in-memory history.
        # In simulation-light mode we keep a compact in-memory record to limit RAM growth.
        if self.light_mode:
            self.history["games"].append({
                "game_id": game_id,
                "game_type": game_type,
                "game_display_name": game_display_name,
                "day_number": day_number,
                "timestamp": timestamp,
                "total_participants": len(results),
                "non_scoring": non_scoring,
            })
        else:
            self.history["games"].append(game_record)

        print(f"\nGame session recorded:")
        print(f"   ID: {game_id}")
        print(f"   Type: {game_display_name}")
        print(f"   Day: {day_number}")
        print(f"   Participants: {len(results)}")

        try:
            results_store.append_game_event(game_record)
        except Exception as e:
            print(f"Warning: failed to append event backup for {game_id}: {e}")

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
