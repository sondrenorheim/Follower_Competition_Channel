#!/usr/bin/env python3
"""
Find Followers Missing Profile Pictures
Creates batches of usernames that don't have profile picture URLs.

Usage:
    python find_missing_profile_pics.py
    python find_missing_profile_pics.py --batch-size 100
    python find_missing_profile_pics.py --export-json
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

# Configuration
FOLLOWERS_FILE = Path("Followers/all_followers_fresh.json")
OUTPUT_DIR = Path("missing_profile_pics")
BATCH_SIZE = 4500  # Default batch size


def load_followers():
    """Load followers from JSON file."""
    if not FOLLOWERS_FILE.exists():
        print(f"❌ Followers file not found: {FOLLOWERS_FILE}")
        return None

    print(f"📂 Loading followers from: {FOLLOWERS_FILE}")
    with open(FOLLOWERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both list and dict formats
    if isinstance(data, list):
        followers = data
    elif isinstance(data, dict) and 'followers' in data:
        followers = data['followers']
    else:
        followers = data

    print(f"✅ Loaded {len(followers)} followers")
    return followers


def find_missing_profile_pics(followers):
    """Find all followers without profile picture URLs."""
    missing = []

    for follower in followers:
        username = follower.get('username', follower.get('pk', 'unknown'))

        # Check for missing or invalid profile_pic_url
        profile_pic_url = follower.get('profile_pic_url', '')

        if not profile_pic_url or profile_pic_url.strip() == '':
            missing.append({
                'username': username,
                'pk': follower.get('pk', ''),
                'full_name': follower.get('full_name', ''),
            })

    return missing


def create_batches(missing_followers, batch_size):
    """Split followers into batches."""
    batches = []
    for i in range(0, len(missing_followers), batch_size):
        batch = missing_followers[i:i + batch_size]
        batches.append(batch)
    return batches


def save_batches_as_text(batches, output_dir):
    """Save batches as text files (one username per line)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for idx, batch in enumerate(batches, 1):
        filename = output_dir / f"batch_{idx:03d}_usernames.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            for follower in batch:
                f.write(f"{follower['username']}\n")

        saved_files.append(filename)
        print(f"📝 Batch {idx}: {len(batch)} usernames → {filename}")

    return saved_files


def save_batches_as_json(batches, output_dir):
    """Save batches as JSON files (with full follower data)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for idx, batch in enumerate(batches, 1):
        filename = output_dir / f"batch_{idx:03d}_followers.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)

        saved_files.append(filename)
        print(f"📦 Batch {idx}: {len(batch)} followers → {filename}")

    return saved_files


def save_summary(missing_followers, batches, output_dir):
    """Save summary report."""
    summary_file = output_dir / "summary.txt"

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("MISSING PROFILE PICTURES SUMMARY\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total missing: {len(missing_followers)}\n")
        f.write(f"Number of batches: {len(batches)}\n")
        f.write(f"Batch size: {len(batches[0]) if batches else 0}\n\n")

        f.write("=" * 70 + "\n")
        f.write("BATCH BREAKDOWN\n")
        f.write("=" * 70 + "\n\n")

        for idx, batch in enumerate(batches, 1):
            f.write(f"Batch {idx}: {len(batch)} followers\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("ALL USERNAMES (ALPHABETICAL)\n")
        f.write("=" * 70 + "\n\n")

        sorted_usernames = sorted([f['username'] for f in missing_followers])
        for username in sorted_usernames:
            f.write(f"{username}\n")

    print(f"📊 Summary saved: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Find followers without profile picture URLs and create batches.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find missing profile pics with default batch size (50)
  python find_missing_profile_pics.py

  # Use custom batch size
  python find_missing_profile_pics.py --batch-size 100

  # Export as JSON instead of text
  python find_missing_profile_pics.py --export-json

  # Both text and JSON
  python find_missing_profile_pics.py --export-json --export-text
        """
    )
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Number of usernames per batch")
    parser.add_argument("--export-json", action="store_true", help="Export batches as JSON files")
    parser.add_argument("--export-text", action="store_true", help="Export batches as text files (default if neither specified)")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output directory for batches")

    args = parser.parse_args()

    # Default to text export if neither specified
    if not args.export_json and not args.export_text:
        args.export_text = True

    print("=" * 70)
    print("🔍 FINDING FOLLOWERS WITHOUT PROFILE PICTURES")
    print("=" * 70)
    print()

    # Load followers
    followers = load_followers()
    if followers is None:
        return

    # Find missing profile pics
    print("\n🔎 Scanning for missing profile pictures...")
    missing = find_missing_profile_pics(followers)

    if not missing:
        print("\n✅ All followers have profile pictures!")
        return

    print(f"\n⚠️  Found {len(missing)} followers without profile pictures")
    print(f"   That's {len(missing) / len(followers) * 100:.1f}% of total followers")

    # Create batches
    print(f"\n📦 Creating batches (size: {args.batch_size})...")
    batches = create_batches(missing, args.batch_size)
    print(f"✅ Created {len(batches)} batches")

    # Save batches
    print(f"\n💾 Saving to: {args.output_dir}")
    print()

    if args.export_text:
        save_batches_as_text(batches, args.output_dir)

    if args.export_json:
        save_batches_as_json(args.output_dir)

    # Save summary
    print()
    save_summary(missing, batches, args.output_dir)

    # Print summary
    print()
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Total followers: {len(followers)}")
    print(f"Missing profile pics: {len(missing)}")
    print(f"Percentage missing: {len(missing) / len(followers) * 100:.1f}%")
    print(f"Batches created: {len(batches)}")
    print(f"Files saved to: {args.output_dir}")
    print()
    print("📝 Next steps:")
    print(f"   1. Check {args.output_dir}/ for batch files")
    print("   2. Use these usernames to fetch missing profile pictures")
    print("   3. Run your profile picture downloader on each batch")
    print("=" * 70)


if __name__ == "__main__":
    main()
