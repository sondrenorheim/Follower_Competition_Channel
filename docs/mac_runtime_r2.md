# Mac Runtime With R2

This project now expects a split runtime:

- Windows PC: render, export, publish, generate API, generate event logs
- Mac Pro: webhook, Cloudflare tunnel, Discord bot, follower intake, webhook state

## Shared Data Model

R2 prefixes:

- `api/` -> mirror of `website/public/api/`
- `events/` -> mirror of `backups/game_results/events/`
- `state/mac/` -> Mac-owned runtime state snapshot

Writer ownership:

- PC writes `api/` and `events/`
- Mac writes `state/mac/`

Do not use Git, Dropbox, OneDrive, or a shared live repo folder for mutable JSON runtime state.

## Mac Prerequisites

Install:

- Python 3.11+
- AWS CLI v2
- `cloudflared`

Clone the repo and create a virtualenv:

```bash
git clone <repo-url>
cd follower-battlegrounds
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy private files outside Git:

- root `.env`
- `facebook_page_publish.local.env`
- `discord_bot/.env`
- `secrets/youtube_client_secret.json`
- `secrets/youtube_comment_token.pickle`
- `secrets/youtube_token.json`

## Required Environment

Set these for the Mac services:

- `R2_ENDPOINT`
- `R2_BUCKET`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_API_PREFIX=api`
- `R2_EVENTS_PREFIX=events`
- `R2_STATE_PREFIX=state/mac`

Webhook runtime:

- `WEBHOOK_USE_LOCAL_HISTORY=0`
- `WEBHOOK_EVENTS_FALLBACK=1`
- `WEBHOOK_ISOLATE_RESULT_LOOKUP=1`
- `WEBHOOK_EVENTS_DIR=__REPO_ROOT__/backups/game_results/events`
- `PYTHONUNBUFFERED=1`

Discord bot runtime:

- `API_BASE_URL=https://www.followerbattlegrounds.com`

## Startup Flow

1. Pull current event logs:

```bash
python maintenance/sync_cloud_state.py pull-events
```

2. Start the webhook:

```bash
WEBHOOK_USE_LOCAL_HISTORY=0 \
WEBHOOK_EVENTS_FALLBACK=1 \
WEBHOOK_ISOLATE_RESULT_LOOKUP=1 \
WEBHOOK_EVENTS_DIR="$PWD/backups/game_results/events" \
python instagram_webhook.py
```

3. Start the Discord bot:

```bash
API_BASE_URL=https://www.followerbattlegrounds.com \
python discord_bot/bot.py
```

4. Start the named Cloudflare tunnel on the same Mac:

```bash
cloudflared tunnel --config ~/.cloudflared/config.yml run fbg-webhook
```

5. Push Mac-owned state snapshots on a schedule:

```bash
python maintenance/sync_cloud_state.py push-state
```

## launchd Templates

Templates are provided in [docs/launchd](./launchd):

- `com.followerbattlegrounds.webhook.plist`
- `com.followerbattlegrounds.cloudflare-tunnel.plist`
- `com.followerbattlegrounds.discord-bot.plist`
- `com.followerbattlegrounds.pull-events.plist`
- `com.followerbattlegrounds.push-state.plist`

Replace placeholder values:

- `__REPO_ROOT__`
- `__PYTHON_BIN__`
- `__CLOUDFLARED_BIN__`
- `__CLOUDFLARED_CONFIG__`
- `__TUNNEL_NAME__`
- `__LOG_DIR__`

Install user agents:

```bash
mkdir -p ~/Library/LaunchAgents
cp docs/launchd/com.followerbattlegrounds.*.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.followerbattlegrounds.webhook.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.followerbattlegrounds.cloudflare-tunnel.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.followerbattlegrounds.discord-bot.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.followerbattlegrounds.pull-events.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.followerbattlegrounds.push-state.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.followerbattlegrounds.webhook.plist
launchctl load ~/Library/LaunchAgents/com.followerbattlegrounds.cloudflare-tunnel.plist
launchctl load ~/Library/LaunchAgents/com.followerbattlegrounds.discord-bot.plist
launchctl load ~/Library/LaunchAgents/com.followerbattlegrounds.pull-events.plist
launchctl load ~/Library/LaunchAgents/com.followerbattlegrounds.push-state.plist
```

## Operational Checks

Webhook:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/status`

Discord bot:

- bot logs in after reboot
- slash commands resolve current data from the public API

Cloud sync:

- `pull-events` refreshes the local event mirror
- `push-state` uploads follower intake and webhook/bot state

Cutover rule:

- once the Mac-hosted tunnel is live, stop running the Windows tunnel/webhook pair
- do not let both machines own the same inbound-service state files
