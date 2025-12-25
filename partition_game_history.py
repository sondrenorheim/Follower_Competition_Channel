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

    def partition_all(self, base_dir: str = "website/public/api"):
        """
        Create all partitioned files:
        1. Individual game files
        2. Day-aggregated files
        3. Game type indexes
        4. Master index
        """
        print("\n" + "="*60)
        print("PARTITIONING GAME HISTORY")
        print("="*60)

        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        games_dir = base_path / "games"
        days_dir = base_path / "days"
        types_dir = base_path / "types"

        games_dir.mkdir(exist_ok=True)
        days_dir.mkdir(exist_ok=True)
        types_dir.mkdir(exist_ok=True)

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

        # Step 4: Create master index
        index_data = {
            "last_updated": datetime.now().isoformat(),
            "total_games": len(self.history['games']),
            "total_days": len(all_days),
            "available_days": sorted(all_days),
            "days_metadata": day_metadata,
            "game_types": sorted(all_types),
            "types_metadata": type_metadata
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
        print(f"   Master index:     index.json")
        print(f"\n💾 Total files created: {len(self.history['games']) + len(all_days) + len(all_types) + 1}")
        print("="*60 + "\n")

        return {
            "total_games": len(self.history['games']),
            "total_days": len(all_days),
            "total_types": len(all_types),
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
