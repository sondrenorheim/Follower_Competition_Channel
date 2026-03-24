import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared import result_lookup_worker, results_store


def _sample_game_record(*, game_id: str = "game_123", day_number: int = 122, game_type: str = "maze_rush") -> dict:
    return {
        "game_id": game_id,
        "game_type": game_type,
        "game_display_name": "Maze Rush",
        "day_number": day_number,
        "timestamp": "2026-03-24T21:47:53+00:00",
        "total_participants": 3,
        "results": [
            {"username": "alice", "placement": 1},
            {"username": "bob", "placement": 2},
            {"username": "carol", "placement": 3},
        ],
    }


class EventResultCacheTests(unittest.TestCase):
    def test_append_game_event_writes_game_and_day_caches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            events_root = root / "events"
            manifests_root = root / "manifests"
            with mock.patch.object(results_store, "EVENTS_ROOT", events_root):
                with mock.patch.object(results_store, "EVENT_GAMES_ROOT", events_root / "games"):
                    with mock.patch.object(results_store, "EVENT_DAYS_ROOT", events_root / "days"):
                        with mock.patch.object(results_store, "MANIFESTS_ROOT", manifests_root):
                            with mock.patch.object(results_store, "EVENTS_INDEX_PATH", manifests_root / "events_index.jsonl"):
                                with mock.patch.object(results_store, "SNAPSHOTS_ROOT", root / "snapshots"):
                                    with mock.patch.object(results_store, "SNAPSHOTS_INDEX_PATH", manifests_root / "snapshots_index.jsonl"):
                                        with mock.patch.object(results_store, "RECOVERY_LOG_PATH", root / "logs" / "recovery.log"):
                                            event_path = results_store.append_game_event(_sample_game_record())

            self.assertIsNotNone(event_path)
            self.assertTrue((events_root / "games" / "game_123.json").exists())
            self.assertTrue((events_root / "days" / "122.json").exists())

            game_payload = json.loads((events_root / "games" / "game_123.json").read_text(encoding="utf-8"))
            self.assertEqual(game_payload["game_id"], "game_123")
            self.assertEqual(len(game_payload["results"]), 3)

            day_payload = json.loads((events_root / "days" / "122.json").read_text(encoding="utf-8"))
            self.assertEqual(day_payload["day_number"], 122)
            self.assertEqual(day_payload["total_games"], 1)
            self.assertEqual(day_payload["games"][0]["game_id"], "game_123")
            self.assertEqual(day_payload["games"][0]["game_type"], "maze_rush")

    def test_append_game_event_updates_existing_day_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            events_root = root / "events"
            manifests_root = root / "manifests"
            patches = [
                mock.patch.object(results_store, "EVENTS_ROOT", events_root),
                mock.patch.object(results_store, "EVENT_GAMES_ROOT", events_root / "games"),
                mock.patch.object(results_store, "EVENT_DAYS_ROOT", events_root / "days"),
                mock.patch.object(results_store, "MANIFESTS_ROOT", manifests_root),
                mock.patch.object(results_store, "EVENTS_INDEX_PATH", manifests_root / "events_index.jsonl"),
                mock.patch.object(results_store, "SNAPSHOTS_ROOT", root / "snapshots"),
                mock.patch.object(results_store, "SNAPSHOTS_INDEX_PATH", manifests_root / "snapshots_index.jsonl"),
                mock.patch.object(results_store, "RECOVERY_LOG_PATH", root / "logs" / "recovery.log"),
            ]
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
                results_store.append_game_event(_sample_game_record(game_id="game_a", game_type="maze_rush"))
                results_store.append_game_event(_sample_game_record(game_id="game_b", game_type="fighter_arena"))

            day_payload = json.loads((events_root / "days" / "122.json").read_text(encoding="utf-8"))
            game_ids = [entry["game_id"] for entry in day_payload["games"]]
            self.assertEqual(day_payload["total_games"], 2)
            self.assertEqual(game_ids, ["game_a", "game_b"])

    def test_result_lookup_worker_uses_event_game_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir) / "events"
            game_dir = events_dir / "games"
            game_dir.mkdir(parents=True, exist_ok=True)
            payload = _sample_game_record(game_id="lookup_game")
            (game_dir / "lookup_game.json").write_text(json.dumps(payload), encoding="utf-8")

            loaded = result_lookup_worker._latest_game_payload_from_events(events_dir, "lookup_game", scan_max_files=1)
            self.assertIsInstance(loaded, dict)
            self.assertEqual(loaded["game_id"], "lookup_game")
            self.assertEqual(len(loaded["results"]), 3)


if __name__ == "__main__":
    unittest.main()
