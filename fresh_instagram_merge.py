"""
Fresh Instagram Export Merger
Merges all Instagram export files into a single clean follower list
"""
import json
import os
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent
FOLLOWERS_DIR = ROOT / "Followers"
DEFAULT_EXPORT_DIR = (
    FOLLOWERS_DIR
    / "instagram-followerbattlegrounds-2025-12-13-dg9RzcMr"
    / "connections"
    / "followers_and_following"
)
OUTPUT_FILE = FOLLOWERS_DIR / "all_followers_fresh.json"


def resolve_export_dir() -> Path:
    env_dir = os.getenv("INSTAGRAM_EXPORT_DIR")
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        if candidate.exists():
            return candidate
        print(f"Warning: INSTAGRAM_EXPORT_DIR not found: {candidate}")

    if DEFAULT_EXPORT_DIR.exists():
        return DEFAULT_EXPORT_DIR

    export_roots = sorted(
        (path for path in FOLLOWERS_DIR.glob("instagram-followerbattlegrounds-*") if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for export_root in export_roots:
        candidate = export_root / "connections" / "followers_and_following"
        if candidate.exists():
            return candidate

    return DEFAULT_EXPORT_DIR

def convert_instagram_entry(entry):
    """Convert Instagram export format to our format"""
    try:
        string_data = entry.get('string_list_data', [])
        if not string_data:
            return None

        first_entry = string_data[0]
        username = first_entry.get('value', '')
        profile_url = first_entry.get('href', '')

        if not username:
            return None

        return {
            'username': username,
            'profile_url': profile_url,
            'profile_pic_url': ''  # Empty - to be filled by scraper
        }
    except Exception as e:
        print(f"Error converting entry: {e}")
        return None

def main():
    print("="*60)
    print("  FRESH INSTAGRAM EXPORT MERGER")
    print("="*60)

    # Read all Instagram export files
    all_followers = {}  # Use dict to deduplicate by username

    export_dir = resolve_export_dir()
    print(f"Using export directory: {export_dir}")

    export_files = ['followers_1.json', 'followers_2.json', 'followers_3.json']

    for fname in export_files:
        fpath = export_dir / fname
        if not fpath.exists():
            print(f"Warning: {fname} not found")
            continue

        print(f"\nProcessing {fname}...")
        with fpath.open('r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"  Entries in file: {len(data):,}")

        for entry in data:
            follower = convert_instagram_entry(entry)
            if follower:
                username = follower['username']
                # Deduplicate - keep first occurrence
                if username not in all_followers:
                    all_followers[username] = follower

    # Convert to sorted list
    followers_list = sorted(all_followers.values(), key=lambda x: x['username'].lower())

    print(f"\n{'='*60}")
    print(f"MERGE COMPLETE:")
    print(f"  Unique followers: {len(followers_list):,}")
    print(f"  With profile pics: 0 (ready for scraping)")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'='*60}")

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open('w', encoding='utf-8') as f:
        json.dump(followers_list, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
