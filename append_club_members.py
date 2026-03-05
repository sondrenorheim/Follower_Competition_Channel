"""
Append Club Members - Preserves Existing Data
Reads a CSV entry form and updates Followers/club_members_followers.json
using profile data from Followers/new_followers_fresh.json.
"""
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Inputs
PROJECT_ROOT = Path(__file__).resolve().parent
CSV_GLOB = "Follower Battlegrounds*Club Battles Entry Form .csv"
NEW_FOLLOWERS_FILE = "Followers/new_followers_fresh.json"
EXISTING_FILE = "Followers/club_members_followers.json"
MISSING_FILE = "Followers/club_members_missing.txt"
BACKUP_FILE = f"Followers/club_members_followers_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Optional per-username profile pic overrides (absolute paths or URLs)
PROFILE_PIC_OVERRIDES = {
    "followerbattlegrounds": str((PROJECT_ROOT / "587390168_17846184561621697_4596488283905039046_n.jpg").resolve()),
}


def _find_csv_path(cli_arg: str | None) -> str | None:
    if cli_arg and os.path.exists(cli_arg):
        return cli_arg

    for root in [Path.cwd(), Path.home() / "Downloads", Path.home() / "Documents"]:
        if not root.exists():
            continue
        match = next(root.rglob(CSV_GLOB), None)
        if match:
            return str(match)
    return None


def _load_csv_usernames(csv_path: str) -> list[str]:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return []

    col = None
    for key in rows[0].keys():
        if "instagram" in key.lower():
            col = key
            break
    if not col:
        raise ValueError("No instagram username column found in CSV.")

    usernames = []
    for row in rows:
        val = (row.get(col) or "").strip()
        if not val:
            continue
        val = val.lstrip("@").strip()
        if val:
            usernames.append(val)

    # de-dupe, preserve order
    seen = set()
    unique = []
    for u in usernames:
        key = u.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(u)
    return unique


def _load_followers_map(path: str) -> dict[str, dict]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {f.get("username", "").lower(): f for f in data if f.get("username")}


def _load_existing_list(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: list[dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_club_members(csv_path: str):
    print("=" * 60)
    print("  APPEND CLUB MEMBERS (PRESERVES EXISTING DATA)")
    print("=" * 60)
    print(f"CSV: {csv_path}")
    print(f"Existing: {EXISTING_FILE}")
    print(f"Followers source: {NEW_FOLLOWERS_FILE}")

    usernames = _load_csv_usernames(csv_path)
    print(f"Usernames in CSV: {len(usernames)}")

    existing_list = _load_existing_list(EXISTING_FILE)
    existing_map = {f.get("username", "").lower(): f for f in existing_list if f.get("username")}

    followers_map = _load_followers_map(NEW_FOLLOWERS_FILE)

    updated = 0
    added = 0
    missing = []

    for username in usernames:
        key = username.lower()
        override_pic = PROFILE_PIC_OVERRIDES.get(key)
        source = followers_map.get(key)

        if key in existing_map:
            entry = existing_map[key]
            if override_pic:
                entry["profile_pic_url"] = override_pic
                updated += 1
            elif not entry.get("profile_pic_url") and source:
                entry["profile_pic_url"] = source.get("profile_pic_url", "")
                updated += 1
            existing_map[key] = entry
        else:
            if source:
                entry = {
                    "username": source.get("username", username),
                    "profile_url": source.get("profile_url", f"https://www.instagram.com/{username}"),
                    "profile_pic_url": override_pic or source.get("profile_pic_url", ""),
                }
                added += 1
                existing_map[key] = entry
            else:
                entry = {
                    "username": username,
                    "profile_url": f"https://www.instagram.com/{username}",
                    "profile_pic_url": override_pic or "",
                }
                added += 1
                existing_map[key] = entry
                missing.append(username)

    # Backup
    if existing_list:
        _write_json(BACKUP_FILE, existing_list)
        print(f"Backup: {BACKUP_FILE}")

    # Save updated list (sorted)
    out_list = sorted(existing_map.values(), key=lambda x: x.get("username", "").lower())
    _write_json(EXISTING_FILE, out_list)

    if missing:
        os.makedirs(os.path.dirname(MISSING_FILE), exist_ok=True)
        with open(MISSING_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(missing))
        print(f"Missing list: {MISSING_FILE}")
    elif os.path.exists(MISSING_FILE):
        os.remove(MISSING_FILE)

    print()
    print("DONE")
    print(f"Total club members: {len(out_list)}")
    print(f"Added: {added}")
    print(f"Updated pics: {updated}")
    print(f"Missing from new_followers_fresh.json: {len(missing)}")


def main():
    csv_path = _find_csv_path(sys.argv[1] if len(sys.argv) > 1 else None)
    if not csv_path:
        print("CSV file not found. Provide a path as the first argument.")
        sys.exit(1)
    append_club_members(csv_path)


if __name__ == "__main__":
    main()
