import json
import sys
from pathlib import Path


def _load_json(path: Path):
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _event_game_cache_path(events_dir: Path, game_id: str) -> Path:
    return events_dir / "games" / f"{str(game_id or '').strip()}.json"


def _lookup_in_payload(payload, candidates):
    if not isinstance(payload, dict):
        return {
            "data_ready": False,
            "found": False,
            "placement": None,
            "matched_username": None,
            "day_number": None,
        }
    results = payload.get("results")
    if not isinstance(results, list):
        return {
            "data_ready": False,
            "found": False,
            "placement": None,
            "matched_username": None,
            "day_number": payload.get("day_number"),
        }

    candidate_pairs = []
    seen = set()
    for candidate in candidates or []:
        text = str(candidate or "").strip()
        key = text.lstrip("@").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        candidate_pairs.append((text, key))

    if not candidate_pairs:
        return {
            "data_ready": True,
            "found": False,
            "placement": None,
            "matched_username": None,
            "day_number": payload.get("day_number"),
        }

    for original, key in candidate_pairs:
        for entry in results:
            if not isinstance(entry, dict):
                continue
            username = str(entry.get("username") or "").strip().lower()
            if username != key:
                continue
            return {
                "data_ready": True,
                "found": True,
                "placement": entry.get("placement"),
                "matched_username": original,
                "day_number": payload.get("day_number"),
            }

    return {
        "data_ready": True,
        "found": False,
        "placement": None,
        "matched_username": None,
        "day_number": payload.get("day_number"),
    }


def _latest_game_payload_from_events(events_dir: Path, game_id: str, scan_max_files: int):
    if not events_dir.exists():
        return None
    cache_payload = _load_json(_event_game_cache_path(events_dir, game_id))
    if isinstance(cache_payload, dict) and str(cache_payload.get("game_id") or "").strip() == str(game_id or "").strip():
        return cache_payload
    try:
        files = sorted(
            events_dir.rglob("*.ndjson"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
            reverse=True,
        )
    except Exception:
        return None
    if scan_max_files > 0:
        files = files[:scan_max_files]

    best = None
    best_ts = ""
    target = str(game_id or "").strip()
    if not target:
        return None
    for path in files:
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(payload, dict):
                        continue
                    if str(payload.get("game_id") or "").strip() != target:
                        continue
                    ts = str(payload.get("timestamp") or "")
                    if best is None or ts > best_ts:
                        best = payload
                        best_ts = ts
        except Exception:
            continue
    return best


def main():
    raw = sys.stdin.read()
    request = {}
    if raw.strip():
        try:
            request = json.loads(raw)
        except Exception:
            request = {}

    repo_root = Path(str(request.get("repo_root") or ".")).resolve()
    game_id = str(request.get("game_id") or "").strip()
    candidates = list(request.get("candidates") or [])
    events_dir = Path(str(request.get("events_dir") or "")).resolve() if request.get("events_dir") else None
    events_scan_max_files = int(request.get("events_scan_max_files") or 0)

    if not game_id:
        print(
            json.dumps(
                {
                    "ok": True,
                    "data_ready": False,
                    "found": False,
                    "placement": None,
                    "matched_username": None,
                    "day_number": None,
                },
                separators=(",", ":"),
            )
        )
        return

    game_path = repo_root / "website" / "public" / "api" / "games" / f"{game_id}.json"
    payload = _load_json(game_path)
    if payload is None and events_dir is not None:
        payload = _latest_game_payload_from_events(events_dir, game_id, events_scan_max_files)

    lookup = _lookup_in_payload(payload, candidates)
    lookup["ok"] = True
    print(json.dumps(lookup, separators=(",", ":")))


if __name__ == "__main__":
    main()
