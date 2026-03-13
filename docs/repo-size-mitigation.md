# Repo Size Mitigation

This project now uses a mixed strategy to reduce git growth while preserving data.

## What Changed

- CI checkout is shallow (`fetch-depth: 1`, `fetch-tags: false`).
- In `ALL` mode, stats push defaults to one push after all games complete (`AUTO_PUSH_ALL_MODE_STRATEGY = "final_only"`).
- Heavy API partitions are excluded from git commits by default:
  - `website/public/api/games/`
  - `website/public/api/player_history/`
- Local auto-push can sync full API directly to R2 before git commit (`AUTO_PUSH_SYNC_R2_FROM_LOCAL = True`).
- If R2 sync is unavailable, auto-push temporarily re-includes heavy API in git for that run to avoid data loss.
- GitHub workflow R2 sync excludes heavy partitions to avoid overwriting locally-synced data.

## Local R2 Settings

Set these via environment variables (or `config.py`):

- `R2_ENDPOINT`
- `R2_BUCKET`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

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
