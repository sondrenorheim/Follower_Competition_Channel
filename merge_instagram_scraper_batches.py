"""
Merge Instagram scraper result files into the follower list by filling missing profile_pic_url.

Default input pattern:
  C:\\Users\\SondreNorheim\\Downloads\\dataset_instagram-scraper_*.json

Default followers file:
  config.FOLLOWER_IMPORT_FILE if available, otherwise Followers/new_followers_fresh.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DEFAULT_INPUT_PATTERN = r"C:\Users\SondreNorheim\Downloads\dataset_instagram-scraper_*.json"


def load_followers_path() -> str:
    try:
        import config  # type: ignore

        return getattr(config, "FOLLOWER_IMPORT_FILE", "Followers/new_followers_fresh.json")
    except Exception:
        return "Followers/new_followers_fresh.json"


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_atomic(path: str, data) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def iter_input_files(inputs: List[str], pattern: str) -> List[str]:
    if inputs:
        return inputs
    return sorted(glob.glob(pattern))


def extract_username_and_pic(item: dict) -> Tuple[Optional[str], Optional[str]]:
    username = (
        item.get("username")
        or item.get("userName")
        or item.get("ownerUsername")
        or (item.get("user") or {}).get("username")
    )

    pic_url = (
        item.get("profilePicUrlHD")
        or item.get("profilePicUrl")
        or item.get("hdProfilePicUrl")
        or item.get("profile_pic_url_hd")
        or item.get("profile_pic_url")
    )

    if isinstance(username, str):
        username = username.strip()
    if isinstance(pic_url, str):
        pic_url = pic_url.strip()

    if not username:
        return None, None
    if not pic_url or not pic_url.startswith("http"):
        return username, None

    return username, pic_url


def build_pic_map(items: Iterable[dict]) -> Dict[str, str]:
    profile_pics: Dict[str, str] = {}
    for item in items:
        username, pic_url = extract_username_and_pic(item)
        if username and pic_url:
            # Prefer first valid URL per user (files are processed in order)
            profile_pics.setdefault(username, pic_url)
    return profile_pics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge Instagram scraper results into follower list (fill missing profile_pic_url)."
    )
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=[],
        help="Explicit JSON files to merge. If omitted, uses --pattern.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_INPUT_PATTERN,
        help=f"Glob pattern for inputs (default: {DEFAULT_INPUT_PATTERN})",
    )
    parser.add_argument(
        "--followers",
        default=load_followers_path(),
        help="Follower JSON file to update (default: config.FOLLOWER_IMPORT_FILE or Followers/new_followers_fresh.json).",
    )
    args = parser.parse_args()

    input_files = iter_input_files(args.inputs, args.pattern)
    if not input_files:
        print(f"No input files found. Pattern: {args.pattern}")
        return

    print("Loading input files:")
    all_items: List[dict] = []
    for path in input_files:
        print(f"  - {path}")
        data = load_json(path)
        if isinstance(data, list):
            all_items.extend(data)
        else:
            print(f"    Skipped (unexpected JSON root): {Path(path).name}")

    if not all_items:
        print("No valid items found in inputs.")
        return

    profile_pics = build_pic_map(all_items)
    print(f"Found {len(profile_pics):,} profile pic URLs in inputs.")

    followers_path = args.followers
    print(f"\nLoading followers from: {followers_path}")
    followers = load_json(followers_path)
    if not isinstance(followers, list):
        print("Followers file is not a list. Aborting.")
        return

    before_count = sum(1 for f in followers if (f.get("profile_pic_url") or "").startswith("http"))

    backup_path = followers_path.replace(
        ".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    save_json_atomic(backup_path, followers)
    print(f"Backup created: {backup_path}")

    updated = 0
    already = 0
    not_found = 0

    for follower in followers:
        username = follower.get("username")
        current = (follower.get("profile_pic_url") or "").strip()

        if current.startswith("http"):
            already += 1
            continue

        if username in profile_pics:
            follower["profile_pic_url"] = profile_pics[username]
            updated += 1
        else:
            not_found += 1

    save_json_atomic(followers_path, followers)

    after_count = sum(1 for f in followers if (f.get("profile_pic_url") or "").startswith("http"))
    print("\nMerge complete.")
    print(f"  Followers: {len(followers):,}")
    print(f"  Before pics: {before_count:,}")
    print(f"  After pics:  {after_count:,}")
    print(f"  Added:       {updated:,}")
    print(f"  Already had: {already:,}")
    print(f"  Not in input:{not_found:,}")
    print(f"\nUpdated: {followers_path}")


if __name__ == "__main__":
    main()
