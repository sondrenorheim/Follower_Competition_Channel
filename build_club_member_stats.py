"""
Build precomputed club member stats for the website.
Outputs: website/public/api/club_members_stats.json
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "website" / "public" / "api"

CLUB_MEMBERS_PATH = API_DIR / "club_members.json"
PLAYERS_INDEX = API_DIR / "players" / "index.json"
PLAYER_HISTORY_INDEX = API_DIR / "player_history" / "index.json"
PLAYER_HISTORY_DIR = API_DIR / "player_history"
PLAYERS_DIR = API_DIR / "players"

OUT_PATH = API_DIR / "club_members_stats.json"
AVATAR_DIR = API_DIR.parent / "club_avatars"
AVATAR_CACHE_DIR = ROOT / "avatar_cache"

MEMBER_ONLY_GAMES = {"super_follower_bros"}
EXCLUDED_USERNAMES = {"followerbattlegrounds"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _club_sort_key(entry: dict):
    """Sort club members by total all-time points, then member-only points."""
    stats = entry.get("stats", [])
    try:
        total_points = float(stats[0]) if isinstance(stats, list) and stats else 0.0
    except Exception:
        total_points = 0.0
    member_only_points = float((entry.get("member_only") or {}).get("points", 0) or 0)
    username = str(entry.get("username", "")).lower()
    return (-total_points, -member_only_points, username)


def main():
    if not CLUB_MEMBERS_PATH.exists():
        raise SystemExit(f"Missing {CLUB_MEMBERS_PATH}")
    if not PLAYERS_INDEX.exists():
        raise SystemExit(f"Missing {PLAYERS_INDEX}")
    if not PLAYER_HISTORY_INDEX.exists():
        raise SystemExit(f"Missing {PLAYER_HISTORY_INDEX}")

    club_members = load_json(CLUB_MEMBERS_PATH)
    players_index = load_json(PLAYERS_INDEX)
    history_index = load_json(PLAYER_HISTORY_INDEX)
    history_games = history_index.get("games", [])
    points_scale = history_index.get("points_scale", 1) or 1

    players_by_letter = {}
    for letter in players_index.get("letters", []):
        letter_path = PLAYERS_DIR / f"{letter}.json"
        if not letter_path.exists():
            continue
        data = load_json(letter_path)
        players_by_letter[letter] = data.get("players", {})

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    stats_output = []
    for entry in club_members:
        if not isinstance(entry, dict):
            continue
        username = str(entry.get("username", "")).strip()
        if not username:
            continue
        if username.lower() in EXCLUDED_USERNAMES:
            continue

        letter = username[0].lower()
        letter = letter if letter.isalpha() else "0"
        player_data = players_by_letter.get(letter, {}).get(username, {})
        stats_arr = player_data.get("s", []) if isinstance(player_data, dict) else []

        member_games = []
        history_path = PLAYER_HISTORY_DIR / f"{letter}.json"
        if history_path.exists():
            hist = load_json(history_path)
            entries = (hist.get("players") or {}).get(username, [])
            for h in entries:
                if not history_games:
                    continue
                game_meta = history_games[h[0]]
                game_type = game_meta[1]
                if game_type not in MEMBER_ONLY_GAMES:
                    continue
                member_games.append({
                    "gameId": game_meta[0],
                    "gameType": game_type,
                    "dayNumber": game_meta[2],
                    "timestamp": game_meta[3],
                    "placement": h[1] or 0,
                    "points": (h[2] or 0) / points_scale,
                    "kills": h[3] or 0,
                })

        total_points = sum(g["points"] for g in member_games)
        placements = [g["placement"] for g in member_games if g.get("placement")]
        best = min(placements) if placements else 0
        total_places = sum(placements) if placements else 0
        avg = (total_places / len(placements)) if placements else 0
        wins = len([p for p in placements if p == 1])
        latest_game = member_games[0] if member_games else None

        profile_pic_url = entry.get("profile_pic_url", "")
        cache_candidate = AVATAR_CACHE_DIR / f"{username}.jpg"
        if cache_candidate.exists():
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", username).strip("._") or "member"
            dest = AVATAR_DIR / f"{safe_name}.jpg"
            try:
                dest.write_bytes(cache_candidate.read_bytes())
                profile_pic_url = f"/club_avatars/{dest.name}"
            except Exception:
                pass
        elif profile_pic_url and str(profile_pic_url).startswith("http"):
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", username).strip("._") or "member"
            dest = AVATAR_DIR / f"{safe_name}.jpg"
            try:
                if not dest.exists():
                    req = urllib.request.Request(
                        profile_pic_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                            "Referer": "https://www.instagram.com/",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        dest.write_bytes(resp.read())
                profile_pic_url = f"/club_avatars/{dest.name}"
            except Exception:
                pass

        stats_output.append({
            "username": username,
            "profile_pic_url": profile_pic_url,
            "stats": stats_arr,
            "member_only": {
                "games": len(member_games),
                "points": total_points,
                "bestPlacement": best,
                "avgPlacement": round(avg, 1) if avg else 0,
                "wins": wins,
                "latestGame": latest_game,
            },
        })

    stats_output.sort(key=_club_sort_key)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(stats_output, handle, ensure_ascii=False)

    print(f"Wrote {OUT_PATH} with {len(stats_output)} members")


if __name__ == "__main__":
    main()
