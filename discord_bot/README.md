# Follower Battlegrounds Discord Bot

A Discord bot that serves game statistics and player data from [followerbattlegrounds.com](https://www.followerbattlegrounds.com).

## Features

- 📊 **Day Stats**: Get comprehensive statistics for any day
- 👤 **Player Stats**: Look up individual player statistics
- 🆕 **Latest Day**: Quick access to the most recent day's data
- ⚡ **Smart Caching**: Data is cached and refreshed every 5 minutes to minimize server load
- 🛡️ **Rate Limiting**: Built-in rate limiting to prevent spam

## Commands

### `/day <number>`
Get stats for a specific day including:
- Total participants
- Number of games played
- Top 3 players with points
- Game modes played

**Example:**
```
/day 26
```

### `/player <username>`
Get comprehensive stats for a player including:
- Games played
- Total and average points
- Best placement
- Total kills and damage
- Win rate

**Example:**
```
/player example_user
```

### `/latest`
Get stats for the most recent day available.

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot"
5. Under "TOKEN", click "Copy" to copy your bot token
6. Under "Privileged Gateway Intents", you can leave all disabled (default intents are sufficient)

### 2. Invite Bot to Your Server

1. In the Developer Portal, go to "OAuth2" > "URL Generator"
2. Select scopes:
   - `bot`
   - `applications.commands`
3. Select bot permissions:
   - `Send Messages`
   - `Embed Links`
   - `Use Slash Commands`
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Install Dependencies

```bash
# Navigate to the discord_bot directory
cd discord_bot

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure the Bot

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env  # Windows
   cp .env.example .env    # Linux/Mac
   ```

2. Edit `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```

3. (Optional) Customize the data URLs and cache refresh interval if needed

### 5. Run the Bot

```bash
python bot.py
```

You should see:
```
🤖 Starting Follower Battlegrounds Discord Bot...
✅ Logged in as YourBotName#1234
📊 Game History URL: https://www.followerbattlegrounds.com/game_history_web.json
👥 Player Stats URL: https://www.followerbattlegrounds.com/player_statistics_web.json
🔄 Cache refresh interval: 5 minutes
✅ Synced 3 command(s)
```

### 6. Keep the Bot Running (Production)

For production deployment, use a process manager:

#### Option A: PM2 (Recommended for Node.js/Python)
```bash
npm install -g pm2
pm2 start bot.py --name follower-bot --interpreter python
pm2 save
pm2 startup  # Follow the instructions to enable auto-start on reboot
```

#### Option B: systemd (Linux)
Create a service file at `/etc/systemd/system/follower-bot.service`:
```ini
[Unit]
Description=Follower Battlegrounds Discord Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/discord_bot
Environment=PATH=/path/to/discord_bot/venv/bin
ExecStart=/path/to/discord_bot/venv/bin/python bot.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable follower-bot
sudo systemctl start follower-bot
sudo systemctl status follower-bot
```

#### Option C: Screen (Simple)
```bash
screen -S follower-bot
python bot.py
# Press Ctrl+A, then D to detach
# Reattach with: screen -r follower-bot
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Your Discord bot token | *Required* |
| `GAME_HISTORY_URL` | URL to game history JSON | `https://www.followerbattlegrounds.com/game_history_web.json` |
| `PLAYER_STATS_URL` | URL to player stats JSON | `https://www.followerbattlegrounds.com/player_statistics_web.json` |
| `CACHE_REFRESH_MINUTES` | Minutes between cache refreshes | `5` |

### Rate Limiting

- **Per User**: 5 commands per minute
- **Global**: 100 commands per minute

Users exceeding limits will see a friendly message asking them to wait.

## Troubleshooting

### Bot doesn't respond to commands

1. Make sure the bot is online (check Discord server member list)
2. Verify bot has permission to send messages in the channel
3. Wait a minute after startup for commands to sync
4. Try re-syncing commands: restart the bot

### "Could not fetch game data" error

1. Check that the URLs in `.env` are correct
2. Verify the website is accessible: try opening the URLs in a browser
3. Check bot logs for connection errors
4. The bot will use cached data if available when fetch fails

### Commands not showing in Discord

1. Make sure you invited the bot with `applications.commands` scope
2. Restart the bot to trigger command sync
3. Wait a few minutes for Discord to update command cache
4. Try in a different channel or server

## Development

### Adding New Commands

1. Add a new command function decorated with `@tree.command`:
   ```python
   @tree.command(name="mycommand", description="My command description")
   async def my_command(interaction: discord.Interaction):
       await interaction.response.send_message("Hello!")
   ```

2. Restart the bot to sync the new command

### Modifying Data Processing

The main data processing functions are:
- `get_games_for_day(day)`: Get all games for a specific day
- `get_latest_day()`: Get the most recent day number
- `get_player_stats(username)`: Get stats for a player

## Support

For issues related to:
- **The bot**: Check this README and bot logs
- **Game data**: Contact the Follower Battlegrounds team
- **Discord bot development**: Check [discord.py documentation](https://discordpy.readthedocs.io/)

## License

This bot is part of the Follower Battlegrounds project.
