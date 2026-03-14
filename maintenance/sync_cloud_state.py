#!/usr/bin/env python3
"""
Sync generated API/events data and Mac-owned runtime state through Cloudflare R2.

Examples:
  python maintenance/sync_cloud_state.py push-api
  python maintenance/sync_cloud_state.py push-events
  python maintenance/sync_cloud_state.py pull-events
  python maintenance/sync_cloud_state.py push-state
  python maintenance/sync_cloud_state.py pull-state
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SHARED_ROOT = REPO_ROOT / "shared"
if str(SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_ROOT))

import cloud_sync


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync API/events/state data through Cloudflare R2.")
    parser.add_argument(
        "command",
        choices=("push-api", "push-events", "pull-events", "push-state", "pull-state"),
        help="Cloud sync action to run.",
    )
    return parser.parse_args()


def _run_command(command: str) -> cloud_sync.SyncResult:
    if command == "push-api":
        return cloud_sync.push_api_snapshot()
    if command == "push-events":
        return cloud_sync.push_events_snapshot()
    if command == "pull-events":
        return cloud_sync.pull_events_snapshot()
    if command == "push-state":
        return cloud_sync.push_state_snapshot()
    if command == "pull-state":
        return cloud_sync.pull_state_snapshot()
    raise ValueError(f"Unknown command: {command}")


def main() -> int:
    args = _parse_args()
    result = _run_command(args.command)

    if result.ok:
        print(result.message)
        return 0

    if result.status == "skipped":
        print(result.message)
        return 1

    print(result.message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
