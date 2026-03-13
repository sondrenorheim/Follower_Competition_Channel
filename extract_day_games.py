#!/usr/bin/env python3
"""
Extract games for a specific day_number from a (possibly corrupted) game_history.json.
Writes a JSON list of game objects to day_{day}_games.json.
"""

from __future__ import annotations

import argparse
import json
import mmap
from pathlib import Path


def parse_object(mm: mmap.mmap, start: int) -> bytes | None:
    in_string = False
    escape = False
    depth = 0
    for idx in range(start, len(mm)):
        ch = mm[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == ord("\\"):
                escape = True
            elif ch == ord('"'):
                in_string = False
            continue

        if ch == ord('"'):
            in_string = True
        elif ch == ord("{"):
            depth += 1
        elif ch == ord("}"):
            depth -= 1
            if depth == 0:
                return mm[start:idx + 1]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=int, required=True)
    parser.add_argument("--input", default="game_history.json")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    source = Path(args.input)
    if not source.exists():
        raise SystemExit(f"Missing {source}")

    output = Path(args.output) if args.output else Path(f"day_{args.day}_games.json")

    pattern = f'\"day_number\":{args.day}'.encode("utf-8")
    game_start = b'{"game_id"'

    games = {}
    with source.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        start = 0
        while True:
            idx = mm.find(pattern, start)
            if idx == -1:
                break
            obj_start = mm.rfind(game_start, 0, idx)
            if obj_start != -1:
                raw = parse_object(mm, obj_start)
                if raw:
                    try:
                        obj = json.loads(raw.decode("utf-8"))
                    except Exception:
                        obj = None
                    if obj and obj.get("day_number") == args.day and obj.get("game_id"):
                        games[obj["game_id"]] = obj
            start = idx + len(pattern)

    payload = list(games.values())
    payload.sort(key=lambda g: g.get("timestamp", ""))
    with output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Extracted {len(payload)} games for day {args.day} -> {output}")


if __name__ == "__main__":
    main()
