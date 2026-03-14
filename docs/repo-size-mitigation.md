# Repo Size Mitigation

This project now uses a split strategy:

- GitHub for source code and light API payloads
- Cloudflare R2 for large generated data and shared multi-machine snapshots
- Single-writer ownership for mutable runtime JSON/state

## What Changed

- CI checkout is shallow (`fetch-depth: 1`, `fetch-tags: false`).
- In `ALL` mode, stats push defaults to one push after all games complete (`AUTO_PUSH_ALL_MODE_STRATEGY = "final_only"`).
- Heavy API partitions are excluded from git commits by default:
  - `website/public/api/games/`
  - `website/public/api/player_history/`
- Local auto-push can sync generated data directly to R2 before git commit:
  - `api/` mirrors `website/public/api/`
  - `events/` mirrors `backups/game_results/events/`
- Mac-owned runtime state is shared through `state/mac/`:
  - `Followers/new_followers_fresh.json`
  - `discord_bot/discord_links.json`
  - webhook processed-comment/media-map/queue snapshot files
- The PC pulls `state/mac/` before game runs instead of treating the repo as a shared live folder.
- GitHub workflow R2 sync excludes heavy partitions to avoid overwriting locally-synced data.

## Local R2 Settings

Set these via environment variables (or `config.py`):

- `R2_ENDPOINT`
- `R2_BUCKET`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_API_PREFIX` (default `api`)
- `R2_EVENTS_PREFIX` (default `events`)
- `R2_STATE_PREFIX` (default `state/mac`)

## Manual Sync Commands

Use the cross-platform helper:

```bash
python maintenance/sync_cloud_state.py push-api
python maintenance/sync_cloud_state.py push-events
python maintenance/sync_cloud_state.py pull-events
python maintenance/sync_cloud_state.py push-state
python maintenance/sync_cloud_state.py pull-state
```

Recommended ownership:

- PC writes `api/` and `events/`
- Mac writes `state/mac/`
- Never let both machines write the same JSON state files

## One-Time History Cleanup

Use the helper:

```bash
python maintenance/repo_history_cleanup.py
python maintenance/repo_history_cleanup.py --execute
```

`--execute` will:

1. Ensure clean working tree
2. Create a full git bundle backup
3. Copy current heavy API data into backup snapshot
4. Rewrite history to remove heavy API paths
5. Run aggressive git GC

It does **not** push automatically. You must validate and then force-push manually.
