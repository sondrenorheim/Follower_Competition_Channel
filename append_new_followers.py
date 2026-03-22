"""
Append New Followers - Preserves Existing Data
Merges new Instagram export into existing follower list WITHOUT overwriting
"""
import json
import os
import re
import html
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote

try:
    import config
    DEFAULT_FOLLOWER_FILE = getattr(config, "FOLLOWER_IMPORT_FILE", "Followers/all_followers_fresh.json")
except Exception:
    DEFAULT_FOLLOWER_FILE = "Followers/all_followers_fresh.json"

# Paths
# Path to latest Instagram export to merge in
NEW_EXPORT_DIR = r"C:\Users\SondreNorheim\Downloads\instagram-followerbattlegrounds-2026-03-20-LyG7QKk0\connections\followers_and_following"
EXISTING_FILE = DEFAULT_FOLLOWER_FILE
_base_name = Path(EXISTING_FILE).stem
BACKUP_FILE = f"Followers/{_base_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


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


def convert_html_anchor_to_follower(href: str, anchor_text: str):
    """Convert an Instagram HTML export anchor to our follower format."""
    try:
        href = html.unescape((href or "").strip())
        anchor_text = html.unescape((anchor_text or "").strip())

        parsed = urlparse(href)
        netloc = (parsed.netloc or "").lower()
        if netloc not in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
            return None

        path = (parsed.path or "").strip("/")
        if not path:
            return None

        username_from_path = unquote(path.split("/", 1)[0].strip())
        if not username_from_path:
            return None

        reserved = {
            "accounts", "about", "directory", "explore", "developer",
            "reel", "reels", "stories", "p", "tv", "direct",
        }
        if username_from_path.lower() in reserved:
            return None

        username = anchor_text or username_from_path

        return {
            "username": username,
            "profile_url": f"https://www.instagram.com/{username_from_path}",
            "profile_pic_url": "",
        }
    except Exception as e:
        print(f"Error converting HTML anchor: {e}")
        return None


def parse_html_followers_file(path: Path):
    """Parse followers from an Instagram followers_*.html export file."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    anchor_matches = re.findall(
        r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    followers = []
    for href, text in anchor_matches:
        follower = convert_html_anchor_to_follower(href, re.sub(r"<[^>]+>", "", text))
        if follower:
            followers.append(follower)
    return followers


def append_from_export_dir(export_dir, existing_file=EXISTING_FILE, backup_file=None):
    if not backup_file:
        backup_base = Path(existing_file).stem
        backup_file = f"Followers/{backup_base}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    print("=" * 60)
    print("  APPEND NEW FOLLOWERS (PRESERVES EXISTING DATA)")
    print("=" * 60)

    # Step 1: Read existing followers
    existing_followers = {}
    if os.path.exists(existing_file):
        print()
        print(f"Reading existing file: {existing_file}")
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_list = json.load(f)

        # Convert to dict for fast lookup, preserve all existing data
        for follower in existing_list:
            username = follower.get('username', '')
            if username:
                existing_followers[username] = follower

        print(f"  Existing followers: {len(existing_followers):,}")

        # Count how many have profile pics
        with_pics = sum(1 for f in existing_followers.values() if f.get('profile_pic_url', ''))
        print(f"  With profile pics: {with_pics:,}")

        # Create backup
        print()
        print(f"Creating backup: {backup_file}")
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(existing_list, f, indent=2, ensure_ascii=False)
    else:
        print()
        print(f"No existing file found at {existing_file}")
        print("Will create new file")

    # Step 2: Read new Instagram export files
    print()
    export_dir_path = Path(export_dir)
    if not export_dir_path.exists():
        print(f"  Export folder not found: {export_dir}")
        return None

    json_files = list(export_dir_path.glob("followers_*.json"))
    html_files = list(export_dir_path.glob("followers_*.html"))
    plain_followers_json = export_dir_path / "followers.json"
    plain_followers_html = export_dir_path / "followers.html"
    if plain_followers_json.exists():
        json_files.append(plain_followers_json)
    if plain_followers_html.exists():
        html_files.append(plain_followers_html)
    export_files = json_files + html_files

    if not export_files:
        fallback_dir = next(export_dir_path.rglob("followers_and_following"), None)
        if fallback_dir and fallback_dir != export_dir_path:
            export_dir_path = fallback_dir
            json_files = list(export_dir_path.glob("followers_*.json"))
            html_files = list(export_dir_path.glob("followers_*.html"))
            plain_followers_json = export_dir_path / "followers.json"
            plain_followers_html = export_dir_path / "followers.html"
            if plain_followers_json.exists():
                json_files.append(plain_followers_json)
            if plain_followers_html.exists():
                html_files.append(plain_followers_html)
            export_files = json_files + html_files
    print(f"Reading new export from: {export_dir_path}")

    def _export_sort_key(path: Path):
        match = re.search(r"followers_(\d+)\.(json|html)$", path.name, re.IGNORECASE)
        if match:
            ext = match.group(2).lower()
            ext_order = 0 if ext == "json" else 1
            return (0, int(match.group(1)), ext_order)
        lowered = path.name.lower()
        if lowered in {"followers.json", "followers.html"}:
            ext_order = 0 if lowered.endswith(".json") else 1
            return (1, 0, ext_order)
        return (2, path.name.lower(), 2)

    export_files = sorted(export_files, key=_export_sort_key)
    if not export_files:
        print("  No followers_*.json or followers_*.html files found in the export folder.")
        return None

    print(f"  Found {len(export_files)} follower file(s).")
    new_count = 0
    skipped_count = 0
    total_entries = 0

    for fpath in export_files:
        fname = fpath.name

        print()
        print(f"  Processing {fname}...")
        if fpath.suffix.lower() == ".html":
            data = parse_html_followers_file(fpath)
        else:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            data = []
            for entry in raw_data:
                follower = convert_instagram_entry(entry)
                if follower:
                    data.append(follower)

        print(f"    Parsed entries in file: {len(data):,}")
        total_entries += len(data)

        for entry in data:
            username = entry['username']

            # Only add if NOT already in existing followers
            if username not in existing_followers:
                existing_followers[username] = entry
                new_count += 1
            else:
                skipped_count += 1

    # Step 3: Convert to sorted list and save
    followers_list = sorted(existing_followers.values(), key=lambda x: x['username'].lower())

    print()
    print("=" * 60)
    print("MERGE COMPLETE:")
    print(f"  Total unique followers: {len(followers_list):,}")
    print(f"  New followers added: {new_count:,}")
    print(f"  Existing followers preserved: {skipped_count:,}")

    # Count profile pics
    with_pics = sum(1 for f in followers_list if f.get('profile_pic_url', ''))
    print(f"  With profile pics: {with_pics:,}")
    print(f"  Output: {existing_file}")
    print("=" * 60)
    if existing_followers and total_entries < (len(existing_followers) * 0.5):
        print("WARNING: Export contains far fewer entries than the existing list.")
        print("         Check the export date range or ensure the newest export was downloaded.")

    # Save
    os.makedirs(os.path.dirname(existing_file), exist_ok=True)
    with open(existing_file, 'w', encoding='utf-8') as f:
        json.dump(followers_list, f, indent=2, ensure_ascii=False)

    print()
    print(f"OK. Saved to: {existing_file}")
    print(f"OK. Backup saved to: {backup_file}")
    return {
        "total": len(followers_list),
        "new": new_count,
        "existing": skipped_count,
        "with_pics": with_pics,
        "output": existing_file,
        "backup": backup_file,
    }


def main():
    append_from_export_dir(NEW_EXPORT_DIR, EXISTING_FILE, BACKUP_FILE)


if __name__ == '__main__':
    main()
