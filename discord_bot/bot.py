"""
Follower Battlegrounds Discord Bot
Serves game stats and player data via slash commands
"""

import discord
from discord import app_commands
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
from dotenv import load_dotenv
from collections import defaultdict
import time
import ijson
import io
import gzip

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GAME_HISTORY_URL = os.getenv('GAME_HISTORY_URL', 'https://www.followerbattlegrounds.com/game_history_web.json')
PLAYER_STATS_URL = os.getenv('PLAYER_STATS_URL', 'https://www.followerbattlegrounds.com/player_statistics_web.json')
CACHE_REFRESH_MINUTES = int(os.getenv('CACHE_REFRESH_MINUTES', '5'))

# Rate limiting
RATE_LIMIT_COMMANDS_PER_MINUTE = 5
GLOBAL_RATE_LIMIT_PER_MINUTE = 100

class StatsCache:
    """Cache for game history and player statistics"""

    def __init__(self):
        self.game_history = None
        self.player_stats = None
        self.last_update = None
        self.update_lock = asyncio.Lock()

    async def fetch_json(self, url: str) -> Optional[dict]:
        """Fetch JSON data from URL using streaming parser for memory efficiency"""
        try:
            print(f"📥 Fetching {url}...")
            loop = asyncio.get_event_loop()

            # Download with streaming to avoid loading entire response in memory
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, timeout=60, stream=True)
            )
            response.raise_for_status()

            print(f"✓ Downloaded, streaming parse (memory-efficient)...")

            # Use ijson to parse the JSON incrementally
            # This builds the complete object while using minimal memory
            data = await loop.run_in_executor(
                None,
                lambda: self._parse_json_stream(response.raw)
            )

            print(f"✓ Parsed successfully ({len(str(data))} chars)")
            return data

        except requests.Timeout:
            print(f"❌ Timeout fetching {url} (took longer than 60s)")
            return None
        except requests.RequestException as e:
            print(f"❌ Network error fetching {url}: {e}")
            return None
        except MemoryError as e:
            print(f"❌ Out of memory parsing {url}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing {url}: {type(e).__name__}: {e}")
            return None

    def _parse_json_stream(self, stream) -> dict:
        """Parse JSON from stream using ijson for memory efficiency"""
        result = {}

        try:
            # Check if stream is gzip-compressed by reading first few bytes
            # Read some data to check for gzip magic number
            initial_bytes = stream.read(3)

            # Check for gzip magic number (1f 8b 08)
            if initial_bytes[:2] == b'\x1f\x8b':
                print(f"  Detected gzip compression, decompressing...")
                # Reset and wrap in gzip decompressor
                # We need to read the rest and decompress
                remaining = stream.read()
                compressed_data = initial_bytes + remaining
                decompressed_data = gzip.decompress(compressed_data)
                # Create a file-like object from decompressed data
                stream = io.BytesIO(decompressed_data)
            else:
                # Not gzipped, create BytesIO with what we read plus the rest
                remaining = stream.read()
                stream = io.BytesIO(initial_bytes + remaining)

            # Parse top-level key-value pairs using ijson
            parser = ijson.kvitems(stream, '')
            for key, value in parser:
                result[key] = value
                print(f"  Parsed key: {key} ({type(value).__name__})")

        except Exception as e:
            print(f"  Error during parsing: {type(e).__name__}: {e}")
            # If parsing failed, return empty dict
            result = {}

        return result

    async def update(self):
        """Update cached data from URLs"""
        async with self.update_lock:
            print(f"🔄 Updating cache from URLs...")

            # Fetch game history
            game_history = await self.fetch_json(GAME_HISTORY_URL)
            if game_history:
                self.game_history = game_history
                print(f"✅ Game history updated ({len(game_history.get('games', []))} games)")

            # Fetch player stats
            player_stats = await self.fetch_json(PLAYER_STATS_URL)
            if player_stats:
                self.player_stats = player_stats
                # Handle both full and compact format
                players = player_stats.get('players', player_stats.get('p', {}))
                print(f"✅ Player stats updated ({len(players)} players)")

            self.last_update = datetime.now()
            print(f"✅ Cache updated at {self.last_update}")

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

# Initialize cache and rate limiter
cache = StatsCache()
rate_limiter = RateLimiter()

def get_games_for_day(day: int) -> List[dict]:
    """Get all games for a specific day"""
    if not cache.game_history:
        return []

    games = cache.game_history.get('games', [])
    return [g for g in games if g.get('day_number') == day]

def get_latest_day() -> Optional[int]:
    """Get the latest day number"""
    if not cache.game_history:
        return None

    games = cache.game_history.get('games', [])
    if not games:
        return None

    return max(g.get('day_number', 0) for g in games)

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

def get_player_stats(username: str) -> Optional[dict]:
    """Get stats for a specific player"""
    if not cache.player_stats:
        return None

    # Handle both full and compact format ('players' or 'p')
    players = cache.player_stats.get('players', cache.player_stats.get('p', {}))

    # Case-insensitive search
    username_lower = username.lower()
    for player_name, stats in players.items():
        if player_name.lower() == username_lower:
            # Check if stats are in compact format
            if isinstance(stats, dict) and 's' in stats:
                stats = expand_compact_stats(stats)
            return {'username': player_name, **stats}

    return None

def format_number(num: float) -> str:
    """Format large numbers with K/M suffix"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{int(num)}"

@tree.command(name="day", description="Get stats for a specific day")
async def day_command(interaction: discord.Interaction, day: int):
    """Show stats for a specific day"""

    # Rate limiting
    if not rate_limiter.check_user_limit(interaction.user.id):
        await interaction.response.send_message(
            "⏱️ You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "⏱️ The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Defer response for longer operations
    await interaction.response.defer()

    # Ensure cache is fresh
    await cache.ensure_fresh()

    if not cache.game_history:
        await interaction.followup.send(
            "❌ Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    # Get games for the day
    games = get_games_for_day(day)

    if not games:
        await interaction.followup.send(
            f"❌ No games found for Day {day}.",
            ephemeral=True
        )
        return

    # Calculate stats
    total_participants = set()
    all_results = []
    game_types = set()

    for game in games:
        game_types.add(game.get('game_type', 'unknown'))
        results = game.get('results', [])
        for result in results:
            username = result.get('username')
            if username:
                total_participants.add(username)
                all_results.append(result)

    # Get top 3 players by points
    top_players = sorted(
        all_results,
        key=lambda r: r.get('points', 0),
        reverse=True
    )[:3]

    # Create embed
    embed = discord.Embed(
        title=f"📊 Day {day} Stats",
        description=f"**{len(games)} games played** across {len(game_types)} game modes",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="👥 Participants",
        value=format_number(len(total_participants)),
        inline=True
    )

    embed.add_field(
        name="🎮 Games",
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
            name="🏆 Top Players",
            value=top_text,
            inline=False
        )

    # Add game types
    game_types_text = ", ".join(sorted(game_types))
    if len(game_types_text) > 100:
        game_types_text = game_types_text[:97] + "..."

    embed.add_field(
        name="🎯 Game Modes",
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
            "⏱️ You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "⏱️ The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Defer response
    await interaction.response.defer()

    # Ensure cache is fresh
    await cache.ensure_fresh()

    if not cache.player_stats:
        await interaction.followup.send(
            "❌ Could not fetch player data. Please try again later.",
            ephemeral=True
        )
        return

    # Get player stats
    stats = get_player_stats(username)

    if not stats:
        await interaction.followup.send(
            f"❌ Player `{username}` not found.",
            ephemeral=True
        )
        return

    # Create embed
    embed = discord.Embed(
        title=f"📊 {stats['username']}",
        color=discord.Color.gold()
    )

    # Basic stats
    embed.add_field(
        name="🎮 Games Played",
        value=format_number(stats.get('games_played', 0)),
        inline=True
    )

    embed.add_field(
        name="💰 Total Points",
        value=format_number(stats.get('total_points', 0)),
        inline=True
    )

    embed.add_field(
        name="📈 Avg Points",
        value=format_number(stats.get('average_points', 0)),
        inline=True
    )

    # Best placement
    if 'best_placement' in stats:
        embed.add_field(
            name="🏆 Best Placement",
            value=f"#{stats['best_placement']}",
            inline=True
        )

    # Kills and damage
    if 'total_kills' in stats:
        embed.add_field(
            name="💀 Total Kills",
            value=format_number(stats['total_kills']),
            inline=True
        )

    if 'total_damage' in stats:
        embed.add_field(
            name="⚔️ Total Damage",
            value=format_number(stats['total_damage']),
            inline=True
        )

    # Win rate
    if 'games_played' in stats and stats['games_played'] > 0:
        wins = stats.get('wins', 0)
        win_rate = (wins / stats['games_played']) * 100
        embed.add_field(
            name="🎯 Win Rate",
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
            "⏱️ You're using commands too quickly! Please wait a moment.",
            ephemeral=True
        )
        return

    if not rate_limiter.check_global_limit():
        await interaction.response.send_message(
            "⏱️ The bot is receiving too many requests. Please try again in a moment.",
            ephemeral=True
        )
        return

    # Defer response
    await interaction.response.defer()

    # Ensure cache is fresh
    await cache.ensure_fresh()

    if not cache.game_history:
        await interaction.followup.send(
            "❌ Could not fetch game data. Please try again later.",
            ephemeral=True
        )
        return

    # Get latest day
    latest_day = get_latest_day()

    if latest_day is None:
        await interaction.followup.send(
            "❌ No games found.",
            ephemeral=True
        )
        return

    # Get games for the latest day
    games = get_games_for_day(latest_day)

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
        title=f"📊 Latest Day - Day {latest_day}",
        description=f"**{len(games)} games played** across {len(game_types)} game modes",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👥 Participants",
        value=format_number(len(total_participants)),
        inline=True
    )

    embed.add_field(
        name="🎮 Games",
        value=f"{len(games)}",
        inline=True
    )

    # Add game types
    game_types_text = ", ".join(sorted(game_types))
    if len(game_types_text) > 100:
        game_types_text = game_types_text[:97] + "..."

    embed.add_field(
        name="🎯 Game Modes",
        value=game_types_text,
        inline=False
    )

    embed.add_field(
        name="💡 Tip",
        value=f"Use `/day {latest_day}` to see top players!",
        inline=False
    )

    embed.set_footer(text=f"Data from followerbattlegrounds.com")

    await interaction.followup.send(embed=embed)

@client.event
async def on_ready():
    """Bot startup event"""
    print(f'✅ Logged in as {client.user}')
    print(f'📊 Game History URL: {GAME_HISTORY_URL}')
    print(f'👥 Player Stats URL: {PLAYER_STATS_URL}')
    print(f'🔄 Cache refresh interval: {CACHE_REFRESH_MINUTES} minutes')

    # Sync commands first (don't wait for data)
    try:
        synced = await tree.sync()
        print(f'✅ Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

    # Start background task for cache refresh
    # This runs continuously and handles errors gracefully
    client.loop.create_task(cache_refresh_task())

    # Trigger initial cache update in background (non-blocking)
    print(f'🔄 Starting initial cache update in background...')
    client.loop.create_task(initial_cache_update())

async def initial_cache_update():
    """Initial cache update with error handling"""
    try:
        await cache.update()
        print(f"✅ Initial cache loaded successfully")
    except Exception as e:
        print(f"⚠️ Initial cache update failed: {type(e).__name__}: {e}")
        print(f"   Bot will retry in {CACHE_REFRESH_MINUTES} minutes")
        print(f"   Commands will work once data is loaded")

async def cache_refresh_task():
    """Background task to refresh cache periodically"""
    await client.wait_until_ready()

    while not client.is_closed():
        await asyncio.sleep(CACHE_REFRESH_MINUTES * 60)

        try:
            await cache.update()
        except Exception as e:
            print(f"❌ Error in cache refresh task: {e}")

def main():
    """Main entry point"""
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
        return

    print("🤖 Starting Follower Battlegrounds Discord Bot...")
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
