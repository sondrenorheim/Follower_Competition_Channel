"""
Follower Battlegrounds Discord Bot
Serves game stats and player data via slash commands
"""

import atexit
import discord
from discord import app_commands
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
import time

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BASE_URL = os.getenv('BASE_URL', 'https://www.followerbattlegrounds.com')
CACHE_REFRESH_MINUTES = int(os.getenv('CACHE_REFRESH_MINUTES', '5'))

# Use partitioned API instead of monolithic files
INDEX_URL = f"{BASE_URL}/api/index.json"
PLAYER_INDEX_URL = f"{BASE_URL}/api/players/index.json"

# Rate limiting
RATE_LIMIT_COMMANDS_PER_MINUTE = 5
GLOBAL_RATE_LIMIT_PER_MINUTE = 100

# Discord username links file
DISCORD_LINKS_FILE = Path(__file__).parent / "discord_links.json"
PID_FILE = Path(__file__).parent / "discord_bot.pid"


def _write_pid_file():
    try:
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass


def _clear_pid_file():
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        return
    except Exception:
        pass

class DiscordLinks:
    """Manages Discord username to Instagram username mappings"""

    def __init__(self):
        self.links = {}
        self.load()

    def load(self):
        """Load links from JSON file"""
        if DISCORD_LINKS_FILE.exists():
            try:
                with open(DISCORD_LINKS_FILE, 'r', encoding='utf-8') as f:
                    self.links = json.load(f)
                print(f"Loaded {len(self.links)} Discord username links")
            except Exception as e:
                print(f"Error loading Discord links: {e}")
                self.links = {}
        else:
            self.links = {}

    def save(self):
        """Save links to JSON file"""
        try:
            with open(DISCORD_LINKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.links, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving Discord links: {e}")

    def link_user(self, discord_user_id: str, discord_display_name: str, instagram_username: str):
        """Link a Discord user to their Instagram username"""
        self.links[discord_user_id] = {
            "instagram_username": instagram_username,
            "discord_display_name": discord_display_name,
            "linked_at": datetime.now().isoformat(),
            "last_changed": datetime.now().isoformat()
        }
        self.save()

    def can_change_link(self, discord_user_id: str, cooldown_days: int = 30) -> tuple:
        """Check if user can change their link (rate limit)

        Returns: (can_change: bool, days_remaining: int)
        """
        if discord_user_id not in self.links:
            return (True, 0)  # No existing link, can link freely

        last_changed = self.links[discord_user_id].get("last_changed")
        if not last_changed:
            # Old link without timestamp, allow change once
            return (True, 0)

        last_changed_date = datetime.fromisoformat(last_changed)
        time_since_change = datetime.now() - last_changed_date
        days_since_change = time_since_change.days

        if days_since_change >= cooldown_days:
            return (True, 0)
        else:
            days_remaining = cooldown_days - days_since_change
            return (False, days_remaining)

    def unlink_user(self, discord_user_id: str):
        """Remove a Discord user's link"""
        if discord_user_id in self.links:
            del self.links[discord_user_id]
            self.save()
            return True
        return False

    def get_instagram_username(self, discord_user_id: str) -> Optional[str]:
        """Get Instagram username for a Discord user ID"""
        if discord_user_id in self.links:
            return self.links[discord_user_id]["instagram_username"]
        return None

    def find_by_discord_name(self, discord_name: str) -> Optional[tuple]:
        """Find Instagram username by Discord display name (case-insensitive)
        Returns: (instagram_username, discord_display_name) or None"""
        discord_name_lower = discord_name.lower()
        for user_id, data in self.links.items():
            if data["discord_display_name"].lower() == discord_name_lower:
                return (data["instagram_username"], data["discord_display_name"])
        return None

    def find_by_instagram_name(self, instagram_name: str) -> Optional[str]:
        """Find Discord display name by Instagram username (case-insensitive)
        Returns: discord_display_name or None"""
        instagram_name_lower = instagram_name.lower()
        for user_id, data in self.links.items():
            if data["instagram_username"].lower() == instagram_name_lower:
                return data["discord_display_name"]
        return None

class StatsCache:
    """Cache for partitioned game history and player statistics"""

    def __init__(self):
        self.index = None  # Day metadata
        self.player_index = None  # Player list
        self.cached_days = {}  # Map of day_number -> day_data
        self.last_update = None
        self.update_lock = asyncio.Lock()

    async def fetch_json(self, url: str) -> Optional[dict]:
        """Fetch JSON data from URL (simple version for small partitioned files)"""
        try:
            print(f"Fetching {url}...")
            loop = asyncio.get_event_loop()

            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, timeout=30)
            )
            response.raise_for_status()

            data = response.json()
            print(f"OK - Loaded successfully")
            return data

        except requests.Timeout:
            print(f"ERROR: Timeout fetching {url}")
            return None
        except requests.RequestException as e:
            print(f"ERROR: Network error fetching {url}: {e}")
            return None
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            return None

    async def update(self):
        """Update cached index data (lightweight)"""
        async with self.update_lock:
            print(f"Updating cache...")

            # Fetch day index (small file with metadata)
            index = await self.fetch_json(INDEX_URL)
            if index:
                self.index = index
                print(f"OK - Day index: {len(index.get('available_days', []))} days available")

            # Fetch player index (list of players with basic info)
            player_index = await self.fetch_json(PLAYER_INDEX_URL)
            if player_index:
                self.player_index = player_index
                print(f"OK - Player index: {player_index.get('total_players', 0)} players")

            self.last_update = datetime.now()
            print(f"Cache updated at {self.last_update.strftime('%H:%M:%S')}")

    async def get_day(self, day_number: int) -> Optional[dict]:
        """Fetch data for a specific day (cached)"""
        # Check cache first
        if day_number in self.cached_days:
            return self.cached_days[day_number]

        # Fetch from API
        day_url = f"{BASE_URL}/api/days/{day_number}.json"
        day_data = await self.fetch_json(day_url)

        if day_data:
            self.cached_days[day_number] = day_data

        return day_data

    def should_refresh(self) -> bool:
        """Check if cache should be refreshed"""
        if self.last_update is None:
            return True
        return datetime.now() - self.last_update > timedelta(minutes=CACHE_REFRESH_MINUTES)

    async def ensure_fresh(self):
        """Ensure cache is fresh, update if needed"""
        if self.should_refresh():
            await self.update()

class RateLimiter:
    """Simple rate limiter for bot commands"""

    def __init__(self):
        self.user_commands = defaultdict(list)
        self.global_commands = []

    def check_user_limit(self, user_id: int) -> bool:
        """Check if user is within rate limit"""
        now = time.time()
        minute_ago = now - 60

        # Clean old entries
        self.user_commands[user_id] = [
            t for t in self.user_commands[user_id]
            if t > minute_ago
        ]

        # Check limit
        if len(self.user_commands[user_id]) >= RATE_LIMIT_COMMANDS_PER_MINUTE:
            return False

        # Add new command
        self.user_commands[user_id].append(now)
        return True

    def check_global_limit(self) -> bool:
        """Check if global rate limit is exceeded"""
        now = time.time()
        minute_ago = now - 60

        # Clean old entries
        self.global_commands = [t for t in self.global_commands if t > minute_ago]

        # Check limit
        if len(self.global_commands) >= GLOBAL_RATE_LIMIT_PER_MINUTE:
            return False

        # Add new command
        self.global_commands.append(now)
        return True

# Initialize bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Initialize cache, rate limiter, and discord links
cache = StatsCache()
rate_limiter = RateLimiter()
discord_links = DiscordLinks()

async def get_games_for_day(day: int) -> List[dict]:
    """Get all games for a specific day"""
    day_data = await cache.get_day(day)
    if not day_data:
        return []

    return day_data.get('games', [])

def get_latest_day() -> Optional[int]:
    """Get the latest day number"""
    if not cache.index:
        return None

    available_days = cache.index.get('available_days', [])
    if not available_days:
        return None

    return max(available_days)

def expand_compact_stats(compact_stats: dict) -> dict:
    """
    Expand compact player stats format to full format

    Compact format:
    - 's': [13-item array]
    - 'gb': {game_type_code: count}

    Array indices:
    [0] total_points, [1] games_played, [2] best_placement,
    [3] total_placements, [4] wins, [5] top_3_finishes,
    [6] top_10%_finishes, [7] total_survival_time,
    [8] first_eliminations, [9] current_hot_streak,
    [10] best_hot_streak, [11] total_kills, [12] total_damage
    """
    s = compact_stats.get('s', [])

    # Ensure we have enough values
    while len(s) < 13:
        s.append(0)

    expanded = {
        'total_points': s[0],
        'games_played': s[1],
        'best_placement': s[2],
        'total_placements': s[3],
        'wins': s[4],
        'top_3_finishes': s[5],
        'top_10_percent_finishes': s[6],
        'total_survival_time': s[7],
        'first_eliminations': s[8],
        'current_hot_streak': s[9],
        'best_hot_streak': s[10],
        'total_kills': s[11],
        'total_damage': s[12],
        'average_points': s[0] / s[1] if s[1] > 0 else 0,
        'game_breakdown': compact_stats.get('gb', {})
    }

    return expanded

async def resolve_username(username: str) -> tuple:
    """Resolve username to Instagram username and display name

    Returns: (instagram_username, display_name) tuple
    - Tries exact Instagram username match first
    - Then tries Discord username lookup
    - Returns original username if no link found
    """
    # First, try to find by Discord display name
    discord_result = discord_links.find_by_discord_name(username)
    if discord_result:
        instagram_username, discord_display_name = discord_result
        return (instagram_username, discord_display_name)

    # Check if this Instagram username has a linked Discord name
    discord_name = discord_links.find_by_instagram_name(username)
    if discord_name:
        return (username, discord_name)

    # No link found, use original username for both
    return (username, username)

async def get_player_stats(username: str) -> Optional[dict]:
    """Get stats for a specific player"""
    if not cache.player_index:
        return None

    # Find player in index
    players = cache.player_index.get('players', [])
    player_info = None

    username_lower = username.lower()
    for p in players:
        if p.get('u', '').lower() == username_lower:
            player_info = p
            break

    if not player_info:
        return None

    # Fetch full stats for the player
    letter = player_info.get('l', 'z')
    player_url = f"{BASE_URL}/api/players/{letter}.json"
    letter_data = await cache.fetch_json(player_url)

    if not letter_data or 'players' not in letter_data:
        return None

    # Find the specific player in the letter group
    actual_username = player_info.get('u')
    player_data = letter_data['players'].get(actual_username)

    if not player_data:
        return None

    # Expand compact format
    stats = expand_compact_stats(player_data)
    return {'username': actual_username, **stats}

def format_number(num: float) -> str:
    """Format large numbers with K/M suffix"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{int(num)}"

@tree.command(name="link", description="Link your Discord account to your Instagram username (private)")
async def link_command(interaction: discord.Interaction, instagram_username: str):
    """Link Discord account to Instagram username (ephemeral)"""

    await interaction.response.defer(ephemeral=True)
    await cache.ensure_fresh()

    discord_user_id = str(interaction.user.id)
    discord_display_name = interaction.user.display_name

    # Check if user can change their link (30-day cooldown)
    can_change, days_remaining = discord_links.can_change_link(discord_user_id, cooldown_days=30)

    if not can_change:
        await interaction.followup.send(
            f"You can only change your linked username once per month.\n\n"
            f"You can change again in **{days_remaining} days**.\n\n"
            f"This prevents abuse and protects other users' privacy.",
            ephemeral=True
        )
        return

    # Verify the Instagram username exists in player data
    instagram_username_resolved, _ = await resolve_username(instagram_username)
    stats = await get_player_stats(instagram_username_resolved)

    if not stats:
        await interaction.followup.send(
            f"Instagram username not found: **{instagram_username}**\n\n"
            f"Make sure you've participated in at least one game first!",
            ephemeral=True
        )
        return

    # Link the user
    discord_links.link_user(discord_user_id, discord_display_name, instagram_username)

    # Check if this is a new link or an update
    is_update = discord_user_id in discord_links.links and discord_links.links[discord_user_id].get("linked_at") != discord_links.links[discord_user_id].get("last_changed")

    if is_update:
        await interaction.followup.send(
            f"Successfully updated your linked Instagram username to: **{instagram_username}**\n\n"
            f"Now others can use `/player {discord_display_name}` to see your stats!\n"
            f"You won't be able to change this again for 30 days.",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"Successfully linked your Discord account to Instagram username: **{instagram_username}**\n\n"
            f"Now others can use `/player {discord_display_name}` to see your stats!\n"
            f"Your stats will be displayed with your Discord username.\n\n"
            f"You can only change this once per month to prevent abuse.",
            ephemeral=True
        )

@tree.command(name="unlink", description="Unlink your Discord account from Instagram (private)")
async def unlink_command(interaction: discord.Interaction):
    """Unlink Discord account from Instagram username (ephemeral)"""

    discord_user_id = str(interaction.user.id)

    if discord_links.unlink_user(discord_user_id):
        await interaction.response.send_message(
            f"Successfully unlinked your Discord account.\n\n"
            f"Your Instagram username is no longer connected to Discord.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"You don't have a linked Instagram account.\n\n"
            f"Use `/link <instagram_username>` to link your account first.",
            ephemeral=True
        )

@tree.command(name="day", description="Get stats for a specific day")
async def day_command(interaction: discord.Interaction, day: int):
    """Show stats for a specific day"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Defer response for longer operations
    await interaction.response.defer()

    # Ensure cache is fresh
    await cache.ensure_fresh()

    if not cache.index:
        await interaction.followup.send(
            "Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    # Get games for the day
    games = await get_games_for_day(day)

    if not games:
        await interaction.followup.send(
            f"No games found for Day {day}.",
            ephemeral=True
        )
        return

    # Calculate stats
    total_participants = set()
    player_points = {}  # Aggregate points per player
    game_types = set()

    for game in games:
        game_types.add(game.get('game_type', 'unknown'))
        results = game.get('results', [])
        for result in results:
            username = result.get('username')
            if username:
                total_participants.add(username)
                # Sum up points for each player across all games
                points = result.get('points', 0)
                if username in player_points:
                    player_points[username] += points
                else:
                    player_points[username] = points

    # Get top 3 players by total points for the day
    top_players = sorted(
        [{'username': u, 'points': p} for u, p in player_points.items()],
        key=lambda r: r.get('points', 0),
        reverse=True
    )[:3]

    # Create embed
    embed = discord.Embed(
        title=f"Day {day} Stats",
        description=f"**{len(games)} games played** across {len(game_types)} game modes",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Participants",
        value=format_number(len(total_participants)),
        inline=True
    )

    embed.add_field(
        name="Games",
        value=f"{len(games)}",
        inline=True
    )

    # Add top players
    if top_players:
        top_text = "\n".join([
            f"{i+1}. **{p.get('username', 'Unknown')}** - {format_number(p.get('points', 0))} pts"
            for i, p in enumerate(top_players)
        ])
        embed.add_field(
            name="Top Players",
            value=top_text,
            inline=False
        )

    # Add game types
    game_types_text = ", ".join(sorted(game_types))
    if len(game_types_text) > 100:
        game_types_text = game_types_text[:97] + "..."

    embed.add_field(
        name="Game Modes",
        value=game_types_text,
        inline=False
    )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")

    await interaction.followup.send(embed=embed)

@tree.command(name="player", description="Get stats for a specific player")
async def player_command(interaction: discord.Interaction, username: str):
    """Show stats for a specific player"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Defer response
    await interaction.response.defer()

    # Ensure cache is fresh
    await cache.ensure_fresh()

    if not cache.player_index:
        await interaction.followup.send(
            "Could not fetch player data. Please try again later.",
            ephemeral=True
        )
        return

    # Resolve username (Discord → Instagram if linked)
    instagram_username, display_name = await resolve_username(username)

    # Get player stats using Instagram username
    stats = await get_player_stats(instagram_username)

    if not stats:
        await interaction.followup.send(
            f"Player `{username}` not found.",
            ephemeral=True
        )
        return

    # Create embed with display name (Discord username if linked)
    embed = discord.Embed(
        title=f"{display_name}",
        color=discord.Color.gold()
    )

    # Basic stats
    embed.add_field(
        name="Games Played",
        value=format_number(stats.get('games_played', 0)),
        inline=True
    )

    embed.add_field(
        name="Total Points",
        value=format_number(stats.get('total_points', 0)),
        inline=True
    )

    embed.add_field(
        name="Avg Points",
        value=format_number(stats.get('average_points', 0)),
        inline=True
    )

    # Best placement
    if 'best_placement' in stats:
        embed.add_field(
            name="Best Placement",
            value=f"#{stats['best_placement']}",
            inline=True
        )

    # Kills and damage
    if 'total_kills' in stats:
        embed.add_field(
            name="Total Kills",
            value=format_number(stats['total_kills']),
            inline=True
        )

    if 'total_damage' in stats:
        embed.add_field(
            name="Total Damage",
            value=format_number(stats['total_damage']),
            inline=True
        )

    # Win rate
    if 'games_played' in stats and stats['games_played'] > 0:
        wins = stats.get('wins', 0)
        win_rate = (wins / stats['games_played']) * 100
        embed.add_field(
            name="Win Rate",
            value=f"{win_rate:.1f}%",
            inline=True
        )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")

    await interaction.followup.send(embed=embed)

@tree.command(name="latest", description="Get stats for the most recent day")
async def latest_command(interaction: discord.Interaction):
    """Show stats for the latest day"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Defer response
    await interaction.response.defer()

    # Ensure cache is fresh
    await cache.ensure_fresh()

    if not cache.index:
        await interaction.followup.send(
            "Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    # Get latest day
    latest_day = get_latest_day()

    if latest_day is None:
        await interaction.followup.send(
            "No games found.",
            ephemeral=True
        )
        return

    # Get games for the latest day
    games = await get_games_for_day(latest_day)

    # Calculate stats
    total_participants = set()
    game_types = set()

    for game in games:
        game_types.add(game.get('game_type', 'unknown'))
        results = game.get('results', [])
        for result in results:
            username = result.get('username')
            if username:
                total_participants.add(username)

    # Create embed
    embed = discord.Embed(
        title=f"Latest Day - Day {latest_day}",
        description=f"**{len(games)} games played** across {len(game_types)} game modes",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Participants",
        value=format_number(len(total_participants)),
        inline=True
    )

    embed.add_field(
        name="Games",
        value=f"{len(games)}",
        inline=True
    )

    # Add game types
    game_types_text = ", ".join(sorted(game_types))
    if len(game_types_text) > 100:
        game_types_text = game_types_text[:97] + "..."

    embed.add_field(
        name="Game Modes",
        value=game_types_text,
        inline=False
    )

    embed.add_field(
        name="Tip",
        value=f"Use `/day {latest_day}` to see top players!",
        inline=False
    )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")

    await interaction.followup.send(embed=embed)

@tree.command(name="today", description="Get top 10 players from today")
async def today_command(interaction: discord.Interaction):
    """Show top 10 players from today"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await cache.ensure_fresh()

    if not cache.index:
        await interaction.followup.send(
            "Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    # Get latest day
    latest_day = get_latest_day()
    if latest_day is None:
        await interaction.followup.send(
            "No games found.",
            ephemeral=True
        )
        return

    games = await get_games_for_day(latest_day)
    if not games:
        await interaction.followup.send(
            f"No games found for today.",
            ephemeral=True
        )
        return

    # Aggregate points per player
    player_points = {}
    for game in games:
        for result in game.get('results', []):
            username = result.get('username')
            if username:
                points = result.get('points', 0)
                player_points[username] = player_points.get(username, 0) + points

    # Get top 10
    top_players = sorted(
        [{'username': u, 'points': p} for u, p in player_points.items()],
        key=lambda r: r['points'],
        reverse=True
    )[:10]

    # Create embed
    embed = discord.Embed(
        title=f"Top 10 Players Today (Day {latest_day})",
        description=f"{len(games)} games played",
        color=discord.Color.gold()
    )

    if top_players:
        leaderboard_text = "\n".join([
            f"{i+1}. **{p['username']}** - {format_number(p['points'])} pts"
            for i, p in enumerate(top_players)
        ])
        embed.add_field(
            name="Leaderboard",
            value=leaderboard_text,
            inline=False
        )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")
    await interaction.followup.send(embed=embed)

@tree.command(name="gameleaderboard", description="Top 10 players for a specific game mode")
async def gameleaderboard_command(interaction: discord.Interaction, game_type: str):
    """Show top 10 players for a specific game type"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await cache.ensure_fresh()

    # Normalize game type
    game_type = game_type.lower().replace(' ', '_')

    # Load all available days and aggregate
    player_stats = {}

    if not cache.index:
        await interaction.followup.send(
            "Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    available_days = cache.index.get('available_days', [])

    for day_num in available_days:
        games = await get_games_for_day(day_num)
        if not games:
            continue

        for game in games:
            if game.get('game_type', '').lower() != game_type:
                continue

            for result in game.get('results', []):
                username = result.get('username')
                if username:
                    if username not in player_stats:
                        player_stats[username] = {
                            'points': 0,
                            'games': 0,
                            'wins': 0,
                            'best_placement': float('inf')
                        }

                    player_stats[username]['points'] += result.get('points', 0)
                    player_stats[username]['games'] += 1

                    placement = result.get('placement', 999)
                    if placement == 1:
                        player_stats[username]['wins'] += 1
                    if placement < player_stats[username]['best_placement']:
                        player_stats[username]['best_placement'] = placement

    if not player_stats:
        await interaction.followup.send(
            f"No games found for game type: **{game_type}**\n\nAvailable types: battle_royale, fighter_arena, platformer_race, obstacle_course, snake_escape, team_battle, gorillas_vs_followers",
            ephemeral=True
        )
        return

    # Get top 10
    top_players = sorted(
        [{'username': u, **stats} for u, stats in player_stats.items()],
        key=lambda r: r['points'],
        reverse=True
    )[:10]

    # Create embed
    game_display = game_type.replace('_', ' ').title()
    embed = discord.Embed(
        title=f"Top 10 Players - {game_display}",
        description=f"All-time leaderboard for {game_display}",
        color=discord.Color.purple()
    )

    if top_players:
        leaderboard_text = "\n".join([
            f"{i+1}. **{p['username']}** - {format_number(p['points'])} pts ({p['games']} games, {p['wins']} wins)"
            for i, p in enumerate(top_players)
        ])
        embed.add_field(
            name="Leaderboard",
            value=leaderboard_text,
            inline=False
        )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")
    await interaction.followup.send(embed=embed)

@tree.command(name="compare", description="Compare stats between two players")
async def compare_command(interaction: discord.Interaction, player1: str, player2: str):
    """Compare stats between two players"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await cache.ensure_fresh()

    # Resolve usernames (Discord → Instagram if linked)
    instagram_username1, display_name1 = await resolve_username(player1)
    instagram_username2, display_name2 = await resolve_username(player2)

    # Get stats for both players using Instagram usernames
    stats1 = await get_player_stats(instagram_username1)
    stats2 = await get_player_stats(instagram_username2)

    if not stats1:
        await interaction.followup.send(
            f"Player not found: **{player1}**",
            ephemeral=True
        )
        return

    if not stats2:
        await interaction.followup.send(
            f"Player not found: **{player2}**",
            ephemeral=True
        )
        return

    # Create comparison embed with display names
    embed = discord.Embed(
        title=f"Player Comparison",
        description=f"**{display_name1}** vs **{display_name2}**",
        color=discord.Color.red()
    )

    # Total Points
    p1_points = stats1.get('total_points', 0)
    p2_points = stats2.get('total_points', 0)
    winner1 = "" if p1_points > p2_points else ""
    winner2 = "" if p2_points > p1_points else ""
    embed.add_field(
        name="Total Points",
        value=f"{winner1} {format_number(p1_points)} vs {format_number(p2_points)} {winner2}",
        inline=False
    )

    # Games Played
    p1_games = stats1.get('games_played', 0)
    p2_games = stats2.get('games_played', 0)
    embed.add_field(
        name="Games Played",
        value=f"{p1_games} vs {p2_games}",
        inline=True
    )

    # Wins
    p1_wins = stats1.get('wins', 0)
    p2_wins = stats2.get('wins', 0)
    winner1 = "" if p1_wins > p2_wins else ""
    winner2 = "" if p2_wins > p1_wins else ""
    embed.add_field(
        name="Wins",
        value=f"{winner1} {p1_wins} vs {p2_wins} {winner2}",
        inline=True
    )

    # Win Rate
    p1_winrate = (p1_wins / p1_games * 100) if p1_games > 0 else 0
    p2_winrate = (p2_wins / p2_games * 100) if p2_games > 0 else 0
    winner1 = "" if p1_winrate > p2_winrate else ""
    winner2 = "" if p2_winrate > p1_winrate else ""
    embed.add_field(
        name="Win Rate",
        value=f"{winner1} {p1_winrate:.1f}% vs {p2_winrate:.1f}% {winner2}",
        inline=True
    )

    # Best Placement
    p1_best = stats1.get('best_placement', 999)
    p2_best = stats2.get('best_placement', 999)
    winner1 = "" if p1_best < p2_best else ""
    winner2 = "" if p2_best < p1_best else ""
    embed.add_field(
        name="Best Placement",
        value=f"{winner1} #{p1_best} vs #{p2_best} {winner2}",
        inline=True
    )

    # Total Kills
    p1_kills = stats1.get('total_kills', 0)
    p2_kills = stats2.get('total_kills', 0)
    winner1 = "" if p1_kills > p2_kills else ""
    winner2 = "" if p2_kills > p1_kills else ""
    embed.add_field(
        name="Total Kills",
        value=f"{winner1} {format_number(p1_kills)} vs {format_number(p2_kills)} {winner2}",
        inline=True
    )

    # Total Damage
    p1_damage = stats1.get('total_damage', 0)
    p2_damage = stats2.get('total_damage', 0)
    winner1 = "" if p1_damage > p2_damage else ""
    winner2 = "" if p2_damage > p1_damage else ""
    embed.add_field(
        name="Total Damage",
        value=f"{winner1} {format_number(p1_damage)} vs {format_number(p2_damage)} {winner2}",
        inline=True
    )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")
    await interaction.followup.send(embed=embed)

@tree.command(name="monthly", description="Top 10 players for a specific month")
async def monthly_command(interaction: discord.Interaction, year: int, month: int):
    """Show top 10 players for a specific month"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Validate month
    if month < 1 or month > 12:
        await interaction.response.send_message(
            "Month must be between 1 and 12.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await cache.ensure_fresh()

    if not cache.index:
        await interaction.followup.send(
            "Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    # Load all days and filter by month
    player_stats = {}
    available_days = cache.index.get('available_days', [])

    for day_num in available_days:
        day_data = await cache.get_day(day_num)
        if not day_data or 'games' not in day_data:
            continue

        for game in day_data['games']:
            # Check if game is in the specified month
            timestamp = game.get('timestamp')
            if not timestamp:
                continue

            from datetime import datetime
            game_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            if game_date.year != year or game_date.month != month:
                continue

            # Aggregate player stats
            for result in game.get('results', []):
                username = result.get('username')
                if username:
                    if username not in player_stats:
                        player_stats[username] = {
                            'points': 0,
                            'games': 0,
                            'wins': 0
                        }

                    player_stats[username]['points'] += result.get('points', 0)
                    player_stats[username]['games'] += 1
                    if result.get('placement', 999) == 1:
                        player_stats[username]['wins'] += 1

    if not player_stats:
        month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1]
        await interaction.followup.send(
            f"No games found for {month_name} {year}.",
            ephemeral=True
        )
        return

    # Get top 10
    top_players = sorted(
        [{'username': u, **stats} for u, stats in player_stats.items()],
        key=lambda r: r['points'],
        reverse=True
    )[:10]

    # Create embed
    month_name = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December'][month-1]
    embed = discord.Embed(
        title=f"Top 10 Players - {month_name} {year}",
        description=f"Monthly leaderboard",
        color=discord.Color.blue()
    )

    if top_players:
        leaderboard_text = "\n".join([
            f"{i+1}. **{p['username']}** - {format_number(p['points'])} pts ({p['games']} games)"
            for i, p in enumerate(top_players)
        ])
        embed.add_field(
            name="Leaderboard",
            value=leaderboard_text,
            inline=False
        )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")
    await interaction.followup.send(embed=embed)

@tree.command(name="alltime", description="Top 10 all-time players")
async def alltime_command(interaction: discord.Interaction):
    """Show top 10 all-time players"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await cache.ensure_fresh()

    if not cache.player_index:
        await interaction.followup.send(
            "Could not fetch player data. Please try again later.",
            ephemeral=True
        )
        return

    # Get top 10 from player index (already sorted by points)
    players = cache.player_index.get('players', [])[:10]

    if not players:
        await interaction.followup.send(
            "No player data available.",
            ephemeral=True
        )
        return

    # Create embed
    embed = discord.Embed(
        title=f"Top 10 All-Time Players",
        description=f"Total of {cache.player_index.get('total_players', 0):,} players",
        color=discord.Color.gold()
    )

    leaderboard_text = "\n".join([
        f"{i+1}. **{p['u']}** - {format_number(p['p'])} pts ({p['g']} games)"
        for i, p in enumerate(players)
    ])
    embed.add_field(
        name="Leaderboard",
        value=leaderboard_text,
        inline=False
    )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")
    await interaction.followup.send(embed=embed)

@client.event
async def on_ready():
    """Bot startup event"""
    print(f'Logged in as {client.user}')
    print(f'Base URL: {BASE_URL}')
    print(f'Cache refresh interval: {CACHE_REFRESH_MINUTES} minutes')

    # Sync commands first (don't wait for data)
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    # Start background task for cache refresh
    # This runs continuously and handles errors gracefully
    client.loop.create_task(cache_refresh_task())

    # Trigger initial cache update in background (non-blocking)
    print(f'Starting initial cache update in background...')
    client.loop.create_task(initial_cache_update())

async def initial_cache_update():
    """Initial cache update with error handling"""
    try:
        await cache.update()
        print(f"Initial cache loaded successfully")
    except Exception as e:
        print(f"WARNING: Initial cache update failed: {type(e).__name__}: {e}")
        print(f"Bot will retry in {CACHE_REFRESH_MINUTES} minutes")
        print(f"Commands will work once data is loaded")

async def cache_refresh_task():
    """Background task to refresh cache periodically"""
    await client.wait_until_ready()

    while not client.is_closed():
        await asyncio.sleep(CACHE_REFRESH_MINUTES * 60)

        try:
            await cache.update()
        except Exception as e:
            print(f"Error in cache refresh task: {e}")

def main():
    """Main entry point"""
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
        return

    print("Starting Follower Battlegrounds Discord Bot...")
    _write_pid_file()
    atexit.register(_clear_pid_file)
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
