#!/usr/bin/env python3
"""
Generate batches of Instagram profile URLs for users missing profile picture URLs.

Defaults:
- Input: config.FOLLOWER_IMPORT_FILE if it exists, otherwise Followers/new_followers_fresh.json
- Batch size: 1800 URLs per JSON batch
- Output dir: Followers/missing_profile_pic_batches

Usage:
  python generate_missing_profile_pic_batches.py
  python generate_missing_profile_pic_batches.py --input Followers/new_followers_fresh.json
  python generate_missing_profile_pic_batches.py --batch-size 1800 --output-dir Followers/missing_profile_pic_batches
  python generate_missing_profile_pic_batches.py --format csv
  python generate_missing_profile_pic_batches.py --payload usernames --batch-size 4500
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import config

PIC_KEYS = (
    "profile_pic_url",
    "profile_picture_url",
    "profile_picture",
    "profile_pic",
    "profile_picture_link",
    "avatar_url",
    "avatar",
    "avatar_image",
)

PLACEHOLDER_PREFIXES = (
    "http://via.placeholder.com",
    "https://via.placeholder.com",
)


def detect_input_file(provided: str | None) -> Path | None:
    if provided:
        path = Path(provided)
        return path if path.exists() else None

    configured = getattr(config, "FOLLOWER_IMPORT_FILE", "")
    if configured:
        path = Path(configured)
        if path.exists():
            return path

    candidates = [
        Path("Followers/new_followers_fresh.json"),
        Path("Followers/all_followers_fresh.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    followers_dir = Path("Followers")
    if followers_dir.exists():
        json_files = sorted(
            followers_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if json_files:
            return json_files[0]

    return None


def load_followers(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "followers" in data:
            return data["followers"]
        if "relationships_followers" in data:
            return data["relationships_followers"]
        if "data" in data:
            return data["data"]
    return []


def extract_username(item) -> str | None:
    if not isinstance(item, dict):
        return None

    username = item.get("username")
    if username:
        return username

    string_list = item.get("string_list_data")
    if isinstance(string_list, list):
        for entry in string_list:
            if not isinstance(entry, dict):
                continue
            value = entry.get("value") or entry.get("username")
            if value:
                return value

    return None


def has_profile_pic(item) -> bool:
    if not isinstance(item, dict):
        return False

    for key in PIC_KEYS:
        value = item.get(key)
        if value and str(value).strip():
            value_str = str(value).strip()
            if value_str.startswith(PLACEHOLDER_PREFIXES):
                continue
            return True

    string_list = item.get("string_list_data")
    if isinstance(string_list, list):
        for entry in string_list:
            if not isinstance(entry, dict):
                continue
            for key in PIC_KEYS:
                value = entry.get(key)
                if value and str(value).strip():
                    return True

    return False


def chunk_list(items, batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def build_profile_urls(usernames: list[str]) -> list[str]:
    return [f"https://www.instagram.com/{username}/" for username in usernames]


def write_json_batches(items: list[str], output_dir: Path, batch_size: int, item_label: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_files = []

    for idx, batch in enumerate(chunk_list(items, batch_size), start=1):
        filename = output_dir / f"missing_profile_pic_batch_{idx:03d}.json"
        with filename.open("w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        batch_files.append(filename)
        print(f"Wrote batch {idx:03d}: {len(batch)} {item_label} -> {filename}")

    return batch_files


def write_summary(output_dir: Path, total_followers: int, missing_count: int, batch_files: list[Path], output_format: str):
    summary_path = output_dir / "summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("MISSING PROFILE PICTURE SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total followers scanned: {total_followers}\n")
        f.write(f"Missing profile pics: {missing_count}\n")
        if batch_files:
            if output_format == "json":
                first_batch = json.loads(batch_files[0].read_text(encoding="utf-8"))
                batch_size = len(first_batch)
            else:
                batch_size = len(batch_files[0].read_text(encoding="utf-8").splitlines()) - 1
        else:
            batch_size = 0
        f.write(f"Batch size: {batch_size}\n")
        f.write(f"Batches created: {len(batch_files)}\n")
        f.write("\nFiles:\n")
        for path in batch_files:
            f.write(f"  - {path}\n")

    print(f"Summary saved -> {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate batches of Instagram profile URLs for missing profile pics.")
    parser.add_argument("--input", help="Path to follower list JSON file")
    parser.add_argument("--output-dir", default="Followers/missing_profile_pic_batches", help="Output directory for batches")
    parser.add_argument("--batch-size", type=int, default=1800, help="Max usernames per batch")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")
    parser.add_argument(
        "--payload",
        choices=["urls", "usernames"],
        default="urls",
        help="Content of output batches (default: urls)",
    )

    args = parser.parse_args()

    input_path = detect_input_file(args.input)
    if not input_path:
        raise SystemExit("Follower import file not found. Provide --input.")

    followers = load_followers(input_path)
    if not followers:
        raise SystemExit(f"No followers found in {input_path}")

    missing_usernames = []
    seen = set()

    for item in followers:
        if has_profile_pic(item):
            continue
        username = extract_username(item)
        if not username:
            continue
        if username in seen:
            continue
        seen.add(username)
        missing_usernames.append(username)

    print(f"Input file: {input_path}")
    print(f"Total followers: {len(followers)}")
    print(f"Missing profile pics: {len(missing_usernames)}")

    output_dir = Path(args.output_dir)
    payload_items = (
        build_profile_urls(missing_usernames)
        if args.payload == "urls"
        else missing_usernames
    )

    if args.format == "json":
        item_label = "URLs" if args.payload == "urls" else "usernames"
        batch_files = write_json_batches(payload_items, output_dir, args.batch_size, item_label)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        batch_files = []
        for idx, batch in enumerate(chunk_list(missing_usernames, args.batch_size), start=1):
            filename = output_dir / f"missing_profile_pic_batch_{idx:03d}.csv"
            with filename.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if args.payload == "urls":
                    writer.writerow(["username", "url"])
                    for username in batch:
                        writer.writerow([username, f"https://www.instagram.com/{username}/"])
                else:
                    writer.writerow(["username"])
                    for username in batch:
                        writer.writerow([username])
            batch_files.append(filename)
            print(f"Wrote batch {idx:03d}: {len(batch)} usernames -> {filename}")

    write_summary(output_dir, len(followers), len(missing_usernames), batch_files, args.format)


if __name__ == "__main__":
    main()
