#!/usr/bin/env python3
"""
Enhanced Game History Partitioner
Splits the monolithic game_history.json into:
1. Individual day files: api/days/{day_number}.json
2. Individual game files: api/games/{game_id}.json
3. Metadata indexes for efficient querying

This solves the LFS budget issue by creating many small files instead of one giant file.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List
import config

# Fix Windows console encoding for UTF-8 emojis
if os.name == 'nt':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass


class EnhancedGameHistoryPartitioner:
    """
    Enhanced partitioner that splits game history into:
    - Per-day aggregated files
    - Per-game individual files
    - Multiple index files for efficient queries
    """

    def __init__(self, history_file: str = "game_history.json"):
        self.history_file = history_file
        self.history = {"games": []}
        self.load_history()

    def load_history(self):
        """Load the monolithic game history file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                    if "games" not in self.history:
                        self.history["games"] = []
                print(f"✅ Loaded {len(self.history['games'])} games from {self.history_file}")
            except Exception as e:
                print(f"❌ Error loading game history: {e}")
                self.history = {"games": []}
        else:
            print(f"⚠️  No existing game history file found: {self.history_file}")
            self.history = {"games": []}

    def _generate_monthly_leaderboards(self, leaderboards_dir: Path) -> Dict[str, dict]:
        """
        Generate pre-computed monthly leaderboards.
        Creates one file per month: leaderboards/2024-12.json, leaderboards/2025-01.json, etc.

        Returns:
            Dict mapping month keys (YYYY-MM) to metadata about that month's leaderboard
        """
        preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)
        # Aggregate stats by month
        monthly_data = defaultdict(lambda: defaultdict(lambda: {
            "points": 0.0,
            "games": 0,
            "wins": 0,
            "best_placement": float('inf'),
            "total_kills": 0
        }))

        non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])

        for game in self.history.get('games', []):
            if game.get("non_scoring") or game.get("game_type") in non_scoring_types:
                continue
            timestamp = game.get("timestamp", "")
            if not timestamp or len(timestamp) < 7:
                continue

            # Extract YYYY-MM from timestamp
            month_key = timestamp[:7]  # "2024-12" format

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

        # Write monthly leaderboard files
        monthly_stats = {}

        for month_key in sorted(monthly_data.keys()):
            players = monthly_data[month_key]

            # Build leaderboard sorted by points
            leaderboard = []
            for username, stats in players.items():
                leaderboard.append({
                    "u": username,
                    "p": round(stats["points"], 1),
                    "g": stats["games"],
                    "w": stats["wins"],
                    "b": stats["best_placement"] if stats["best_placement"] != float('inf') else 0,
                    "k": stats["total_kills"]
                })

            # Sort by points descending
            leaderboard.sort(key=lambda x: x["p"], reverse=True)

            # Add rank
            for i, entry in enumerate(leaderboard):
                entry["r"] = i + 1

            # Write to file
            month_file = leaderboards_dir / f"{month_key}.json"
            month_data = {
                "month": month_key,
                "total_players": len(leaderboard),
                "total_games": sum(p["g"] for p in leaderboard) // max(1, len(set(
                    g.get("game_id") for g in self.history.get('games', [])
                    if g.get("timestamp", "").startswith(month_key)
                ))),
                "leaderboard": leaderboard
            }

            with open(month_file, 'w', encoding='utf-8') as f:
                json.dump(month_data, f, ensure_ascii=False, separators=(',', ':'))

            if preview_limit > 0 and len(leaderboard) > preview_limit:
                preview_file = leaderboards_dir / f"{month_key}_top.json"
                preview_data = {
                    "month": month_key,
                    "total_players": len(leaderboard),
                    "is_preview": True,
                    "preview_limit": preview_limit,
                    "total_results": len(leaderboard),
                    "leaderboard": leaderboard[:preview_limit]
                }
                with open(preview_file, 'w', encoding='utf-8') as f:
                    json.dump(preview_data, f, ensure_ascii=False, separators=(',', ':'))

            monthly_stats[month_key] = {
                "players": len(leaderboard),
                "games": len([g for g in self.history.get('games', []) if g.get("timestamp", "").startswith(month_key)])
            }

        return monthly_stats

    def partition_all(self, base_dir: str = "website/public/api"):
        """
        Create all partitioned files:
        1. Individual game files
        2. Day-aggregated files
        3. Game type indexes
        4. Monthly leaderboards (pre-computed)
        5. Master index
        """
        print("\n" + "="*60)
        print("PARTITIONING GAME HISTORY")
        print("="*60)

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

        # Organize games
        games_by_day = defaultdict(list)
        games_by_type = defaultdict(list)
        all_days = set()
        all_types = set()

        print(f"\n📊 Processing {len(self.history['games'])} games...")

        # Step 1: Export individual game files
        for game in self.history['games']:
            game_id = game.get("game_id")
            day = game.get("day_number")
            game_type = game.get("game_type")

            if not game_id:
                continue

            # Write individual game file
            game_file = games_dir / f"{game_id}.json"
            with open(game_file, 'w', encoding='utf-8') as f:
                json.dump(game, f, ensure_ascii=False, separators=(',', ':'))

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

            # Organize for day/type aggregation
            if day is not None:
                games_by_day[day].append(game)
                all_days.add(day)

            if game_type:
                games_by_type[game_type].append(game)
                all_types.add(game_type)

        print(f"   ✅ Created {len(self.history['games'])} individual game files in {games_dir}/")

        # Step 2: Export day-aggregated files
        day_metadata = []
        for day_num in sorted(all_days):
            day_games = games_by_day[day_num]
            day_file = days_dir / f"{day_num}.json"

            # Create compact summary (no full results, just metadata)
            day_summary = {
                "day_number": day_num,
                "total_games": len(day_games),
                "games": [
                    {
                        "game_id": g.get("game_id"),
                        "game_type": g.get("game_type"),
                        "game_display_name": g.get("game_display_name"),
                        "timestamp": g.get("timestamp"),
                        "total_participants": g.get("total_participants")
                    }
                    for g in day_games
                ]
            }

            with open(day_file, 'w', encoding='utf-8') as f:
                json.dump(day_summary, f, ensure_ascii=False, separators=(',', ':'))

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

            # Calculate stats for metadata
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

        print(f"   ✅ Created {len(all_days)} day summary files in {days_dir}/")

        # Step 3: Export game type indexes
        type_metadata = []
        for game_type in sorted(all_types):
            type_games = games_by_type[game_type]
            type_file = types_dir / f"{game_type}.json"

            # Create index of games for this type
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

        print(f"   ✅ Created {len(all_types)} game type indexes in {types_dir}/")

        # Step 4: Generate monthly leaderboards
        monthly_stats = self._generate_monthly_leaderboards(leaderboards_dir)
        print(f"   ✅ Created {len(monthly_stats)} monthly leaderboard files in {leaderboards_dir}/")

        # Step 5: Create master index
        # Load follower count from all_followers_fresh.json
        total_followers = 0
        try:
            followers_file = Path(config.FOLLOWER_IMPORT_FILE)
            if followers_file.exists():
                with open(followers_file, 'r', encoding='utf-8') as f:
                    followers_data = json.load(f)
                    if isinstance(followers_data, list):
                        total_followers = len(followers_data)
                    elif isinstance(followers_data, dict) and 'followers' in followers_data:
                        total_followers = len(followers_data['followers'])
                print(f"   📊 Loaded follower count: {total_followers:,}")
        except Exception as e:
            print(f"   ⚠️ Could not load follower count: {e}")

        index_data = {
            "last_updated": datetime.now().isoformat(),
            "total_games": len(self.history['games']),
            "total_days": len(all_days),
            "total_followers": total_followers,
            "results_preview_limit": preview_limit,
            "available_days": sorted(all_days),
            "days_metadata": day_metadata,
            "game_types": sorted(all_types),
            "types_metadata": type_metadata,
            "available_months": sorted(monthly_stats.keys())
        }

        index_file = base_path / "index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, separators=(',', ':'))

        print(f"   ✅ Created master index: {index_file}")

        # Summary
        print("\n" + "="*60)
        print("✅ PARTITIONING COMPLETE")
        print("="*60)
        print(f"📁 Output directory: {base_path}")
        print(f"   Individual games: {len(self.history['games'])} files in games/")
        print(f"   Day summaries:    {len(all_days)} files in days/")
        print(f"   Game type indexes: {len(all_types)} files in types/")
        print(f"   Monthly leaderboards: {len(monthly_stats)} files in leaderboards/")
        print(f"   Master index:     index.json")
        total_files = len(self.history['games']) + len(all_days) + len(all_types) + len(monthly_stats) + 1
        print(f"\n💾 Total files created: {total_files}")
        print("="*60 + "\n")

        return {
            "total_games": len(self.history['games']),
            "total_days": len(all_days),
            "total_types": len(all_types),
            "total_months": len(monthly_stats),
            "output_dir": str(base_path)
        }


def main():
    """Run the enhanced partitioner"""
    partitioner = EnhancedGameHistoryPartitioner()

    if len(partitioner.history['games']) == 0:
        print("⚠️  No games to partition!")
        return

    # Partition to website API directory
    result = partitioner.partition_all("website/public/api")

    print("📋 Next steps:")
    print("   1. Review the partitioned files in website/public/api/")
    print("   2. Update your website to load from partitioned API")
    print("   3. Update .gitignore to exclude game_history.json (keep it local only)")
    print("   4. Update auto_push.py to only push website/public/api/ directory")
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
