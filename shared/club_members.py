"""
Utilities for working with club member lists.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional, Set

import random


def normalize_username(username: str | None) -> str:
    if not username:
        return ""
    return str(username).strip().lstrip("@").lower()


@lru_cache(maxsize=1)
def load_club_member_set() -> Set[str]:
    base_dir = Path(__file__).resolve().parents[1]
    club_path = base_dir / "Followers" / "club_members_followers.json"
    if not club_path.exists():
        return set()

    try:
        with club_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to load club members from {club_path}: {exc}")
        return set()

    members: Set[str] = set()
    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            username = normalize_username(entry.get("username"))
            if username:
                members.add(username)
    return members


def is_club_member(username: str | None) -> bool:
    if not username:
        return False
    return normalize_username(username) in load_club_member_set()


def _ensure_avatar_image(player, cache_dir: Path) -> bool:
    if getattr(player, "avatar_image", None) is not None:
        return True

    raw_username = getattr(player, "username", "") or ""
    username = normalize_username(raw_username)
    candidates = []
    if raw_username:
        candidates.append(str(raw_username).strip().lstrip("@"))
    if username and username not in candidates:
        candidates.append(username)

    if not candidates:
        return False

    try:
        from PIL import Image
    except Exception:
        return False

    for base in candidates:
        for ext in (".jpg", ".jpeg", ".png"):
            path = cache_dir / f"{base}{ext}"
            if not path.exists():
                continue
            try:
                with Image.open(path) as img:
                    player.avatar_image = img.convert("RGBA")
                return True
            except Exception:
                continue
    return False


def select_club_spotlight(players: Iterable, day_seed: Optional[int] = None):
    club_players = [
        player for player in players
        if getattr(player, "is_club_member", False)
    ]
    if not club_players:
        return None

    if day_seed is None:
        try:
            import config
            day_seed = int(getattr(config, "DAY_NUMBER", 1))
        except Exception:
            day_seed = 1

    rng = random.Random(int(day_seed) + 1337)
    candidates = club_players[:]
    rng.shuffle(candidates)

    cache_dir = Path("avatar_cache")
    for player in candidates:
        if _ensure_avatar_image(player, cache_dir):
            return player

    return rng.choice(club_players)
