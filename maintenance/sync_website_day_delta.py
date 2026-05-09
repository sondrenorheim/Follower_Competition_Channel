#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.website_delta_sync import WebsiteDeltaSync


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh website API data for one completed day using event caches.")
    parser.add_argument("--day-number", type=int, required=True, help="Logical day number to refresh.")
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Update local website/public/api only; skip the changed-file R2 publish step.",
    )
    args = parser.parse_args()

    syncer = WebsiteDeltaSync()
    result = syncer.sync_day(int(args.day_number), publish_to_r2=not bool(args.no_publish))
    print(result.output_excerpt)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
