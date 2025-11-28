"""Test script to check data migration"""
from shared import PlayerStatistics

ps = PlayerStatistics()

# Check if players exist
if ps.stats:
    print(f"Loaded {len(ps.stats)} players")

    # Check first player
    first_user = list(ps.stats.keys())[0]
    print(f"\nFirst user: {first_user}")

    player_data = ps.stats[first_user]
    print(f"Data type: {type(player_data)}")

    if isinstance(player_data, dict):
        print(f"Has 'stats' key: {'stats' in player_data}")
        print(f"Has 'game_breakdown' key: {'game_breakdown' in player_data}")
        print(f"Has 'recent_games' key: {'recent_games' in player_data}")
        if 'stats' in player_data:
            print(f"Stats array length: {len(player_data['stats'])}")
    elif isinstance(player_data, list):
        print(f"Legacy list format, length: {len(player_data)}")
        # This should have been converted by get_player_stats
        stats = ps.get_player_stats(first_user)
        print(f"After get_player_stats call:")
        player_data = ps.stats[first_user]
        print(f"Now type: {type(player_data)}")
        if isinstance(player_data, dict):
            print(f"Has 'stats' key: {'stats' in player_data}")
else:
    print("No existing players found")
