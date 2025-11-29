import json
from datetime import datetime

# Read existing game history
with open('website/public/game_history.json', 'r') as f:
    data = json.load(f)

# Sample usernames for test data
test_users = [
    "player_alpha", "player_beta", "player_gamma", "player_delta",
    "player_epsilon", "player_zeta", "player_eta", "player_theta",
    "player_iota", "player_kappa", "player_lambda", "player_mu",
    "player_nu", "player_xi", "player_omicron", "player_pi"
]

# Create test games for each game type
test_games = [
    {
        "game_id": "20251129_003_battle_royale",
        "game_type": "battle_royale",
        "game_display_name": "Battle Royale",
        "day_number": 5,
        "timestamp": "2025-11-29T14:30:00.000000",
        "total_participants": 16,
        "results": []
    },
    {
        "game_id": "20251129_004_fighter_arena",
        "game_type": "fighter_arena",
        "game_display_name": "Fighter Arena",
        "day_number": 7,
        "timestamp": "2025-11-29T15:15:00.000000",
        "total_participants": 16,
        "results": []
    },
    {
        "game_id": "20251129_005_obstacle_course",
        "game_type": "obstacle_course",
        "game_display_name": "Obstacle Course",
        "day_number": 3,
        "timestamp": "2025-11-29T13:45:00.000000",
        "total_participants": 16,
        "results": []
    },
    {
        "game_id": "20251129_006_snake_escape",
        "game_type": "snake_escape",
        "game_display_name": "Snake Escape",
        "day_number": 6,
        "timestamp": "2025-11-29T14:50:00.000000",
        "total_participants": 16,
        "results": []
    },
    {
        "game_id": "20251129_007_team_battle",
        "game_type": "team_battle",
        "game_display_name": "Team Battle",
        "day_number": 4,
        "timestamp": "2025-11-29T14:00:00.000000",
        "total_participants": 16,
        "results": []
    }
]

# Generate results for each test game
for game in test_games:
    base_points = 100
    for i, username in enumerate(test_users):
        # Generate varied stats
        placement = i + 1
        points = max(0, base_points - (i * 6))  # Decreasing points
        survival_time = round(120 - (i * 5), 2)  # Decreasing survival time
        kills = max(0, 8 - i)  # Decreasing kills
        damage = round(kills * 150.5, 1)

        result = {
            "username": username,
            "placement": placement,
            "points": points,
            "survival_time": survival_time,
            "kills": kills,
            "damage": damage,
            "rank": placement
        }
        game["results"].append(result)

# Add test games to existing data
data["games"].extend(test_games)

# Write updated game history
with open('website/public/game_history.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"Added {len(test_games)} test games!")
print("Game types added:")
for game in test_games:
    print(f"  - Day {game['day_number']}: {game['game_display_name']} ({game['total_participants']} players)")
