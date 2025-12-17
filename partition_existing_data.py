"""
Partition Existing Data
Converts existing monolithic JSON files into partitioned structure
Run this once to migrate to the new partitioned system
"""

import sys
import os

# Add shared directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.game_history import GameHistory
from shared.statistics import PlayerStatistics


def main():
    print("=" * 70)
    print("  PARTITIONING EXISTING DATA")
    print("=" * 70)
    print()

    # Load existing data
    print("Loading existing game history...")
    game_history = GameHistory("game_history.json")
    print(f"   Loaded {len(game_history.history.get('games', []))} games")
    print()

    print("Loading existing player statistics...")
    player_stats = PlayerStatistics("player_statistics.json")
    print(f"   Loaded {len(player_stats.stats)} players")
    print()

    # Export partitioned game history
    print("Partitioning game history by day...")
    game_history.export_partitioned_history("website/public/api")
    print()

    # Export partitioned player stats
    print("Partitioning player statistics by letter...")
    player_stats.export_partitioned_stats("website/public/api")
    print()

    # Also keep the old monolithic files for backwards compatibility
    print("Exporting monolithic files (for backwards compatibility)...")
    game_history.export_web_history("website/public/game_history_web.json")
    player_stats.export_web_stats("website/public/player_statistics_web.json")
    print()

    print("=" * 70)
    print("MIGRATION COMPLETE!")
    print()
    print("New partitioned structure:")
    print("  website/public/api/")
    print("  ├── index.json                (day metadata)")
    print("  ├── days/")
    print("  │   ├── 1.json")
    print("  │   ├── 2.json")
    print("  │   └── ...")
    print("  └── players/")
    print("      ├── index.json            (player index)")
    print("      ├── a.json                (players starting with 'a')")
    print("      ├── b.json")
    print("      └── ...")
    print()
    print("Old monolithic files (kept for compatibility):")
    print("  website/public/game_history_web.json")
    print("  website/public/player_statistics_web.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
