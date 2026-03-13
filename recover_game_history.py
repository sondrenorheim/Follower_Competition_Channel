#!/usr/bin/env python3
"""
Recover a valid game_history.json from a possibly corrupted JSON file.
Parses the "games" array object-by-object and re-serializes valid entries.
"""

from __future__ import annotations

import json
import mmap
from pathlib import Path


def iter_game_objects(mm: mmap.mmap, start: int):
    in_string = False
    escape = False
    depth = 0
    collecting = False
    buf = bytearray()

    for idx in range(start, len(mm)):
        ch = mm[idx]

        if not collecting:
            if ch == ord("{"):
                collecting = True
                depth = 1
                in_string = False
                escape = False
                buf = bytearray()
                buf.append(ch)
            elif ch == ord("]"):
                break
            continue

        buf.append(ch)

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
                yield bytes(buf)
                collecting = False
                buf = bytearray()


def main() -> None:
    source = Path("game_history.json")
    target = Path("game_history_recovered.json")
    if not source.exists():
        raise SystemExit("game_history.json not found.")

    with source.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        marker = b"\"games\":["
        pos = mm.find(marker)
        if pos == -1:
            raise SystemExit("Could not find games array in game_history.json")
        start = pos + len(marker)

        total = 0
        kept = 0
        with target.open("w", encoding="utf-8") as out:
            out.write("{\"games\":[")
            first = True
            for raw in iter_game_objects(mm, start):
                total += 1
                try:
                    obj = json.loads(raw.decode("utf-8"))
                except Exception:
                    continue
                if not obj.get("game_id"):
                    continue
                if not first:
                    out.write(",")
                json.dump(obj, out, ensure_ascii=False, separators=(",", ":"))
                first = False
                kept += 1
            out.write("]}")

    print(f"Recovered {kept} games (parsed {total} objects) -> {target}")


if __name__ == "__main__":
    main()
