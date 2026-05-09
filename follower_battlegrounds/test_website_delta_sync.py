import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared.website_delta_sync import WebsiteDeltaSync


class WebsiteDeltaSyncTests(unittest.TestCase):
    def _write_json(self, path: Path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def _read_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_sync_day_updates_incrementally_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            api_dir = root / "website" / "public" / "api"
            events_days_dir = root / "backups" / "game_results" / "events" / "days"
            events_games_dir = root / "backups" / "game_results" / "events" / "games"
            avatar_cache_dir = root / "avatar_cache"
            sync_state_path = root / "logs" / "website_sync" / "state.json"
            followers_dir = root / "Followers"

            self._write_json(
                followers_dir / "new_followers_fresh.json",
                [{"username": "alice"}, {"username": "bob"}, {"username": "charlie"}],
            )
            (avatar_cache_dir / "alice.jpg").parent.mkdir(parents=True, exist_ok=True)
            (avatar_cache_dir / "alice.jpg").write_bytes(b"avatar")

            self._write_json(
                api_dir / "index.json",
                {
                    "last_updated": "2026-04-09T10:00:00",
                    "total_games": 1,
                    "total_days": 1,
                    "total_followers": 2,
                    "results_preview_limit": 200,
                    "available_days": [135],
                    "days_metadata": [{"day": 135, "games": 1, "types": ["battle_royale"], "participants": 1}],
                    "game_types": ["battle_royale"],
                    "types_metadata": [{"type": "battle_royale", "games": 1}],
                    "available_months": ["2026-04"],
                },
            )
            self._write_json(
                api_dir / "types" / "battle_royale.json",
                {
                    "game_type": "battle_royale",
                    "total_games": 1,
                    "games": [
                        {
                            "game_id": "old_br",
                            "day_number": 135,
                            "timestamp": "2026-04-09T10:00:00",
                            "total_participants": 1,
                        }
                    ],
                },
            )
            self._write_json(
                api_dir / "players" / "index.json",
                {
                    "lu": "2026-04-09T10:00:00",
                    "tgr": 1,
                    "total_players": 1,
                    "letters": ["a"],
                    "players": [{"u": "alice", "p": 20.0, "g": 1, "l": "a"}],
                },
            )
            self._write_json(
                api_dir / "players" / "a.json",
                {
                    "letter": "a",
                    "count": 1,
                    "players": {
                        "alice": {
                            "s": [20.0, 1, 2, 2, 0, 1, 1, 100.0, 0, 1, 1, 1, 0.0],
                            "gb": {"battle_royale": 1},
                            "rg": ["old_br"],
                        }
                    },
                },
            )
            self._write_json(
                api_dir / "player_history" / "index.json",
                {
                    "lu": "2026-04-09T10:00:00",
                    "points_scale": 10,
                    "game_count": 1,
                    "games": [["old_br", "battle_royale", 135, "2026-04-09T10:00:00"]],
                },
            )
            self._write_json(
                api_dir / "player_history" / "a.json",
                {"letter": "a", "count": 1, "players": {"alice": [[0, 2, 200, 1]]}},
            )
            self._write_json(
                api_dir / "leaderboards" / "2026-04.json",
                {
                    "month": "2026-04",
                    "game_type": "all",
                    "total_players": 1,
                    "leaderboard": [{"u": "alice", "p": 20.0, "g": 1, "w": 0, "b": 2, "k": 1, "t": 2, "r": 1}],
                },
            )
            self._write_json(
                api_dir / "leaderboards" / "2026-04_battle_royale.json",
                {
                    "month": "2026-04",
                    "game_type": "battle_royale",
                    "total_players": 1,
                    "leaderboard": [{"u": "alice", "p": 20.0, "g": 1, "w": 0, "b": 2, "k": 1, "t": 2, "r": 1}],
                },
            )
            self._write_json(
                api_dir / "hall_of_fame.json",
                {"last_updated": "2026-04-09T10:00:00", "daily_champions": [], "monthly_champions": []},
            )

            canonical_game = {
                "game_id": "20260410_001_battle_royale",
                "game_type": "battle_royale",
                "game_display_name": "Battle Royale",
                "day_number": 136,
                "timestamp": "2026-04-10T10:00:00",
                "total_participants": 2,
                "results": [
                    {"username": "alice", "placement": 1, "points": 10.0, "survival_time": 50.0, "kills": 2},
                    {"username": "bob", "placement": 2, "points": 5.0, "survival_time": 30.0, "kills": 0},
                ],
                "non_scoring": False,
            }
            noncanonical_game = {
                "game_id": "20260410_001_youtube_followers_battle_royale",
                "game_type": "youtube_followers_battle_royale",
                "game_display_name": "Battle Royale (YouTube Followers)",
                "day_number": 136,
                "timestamp": "2026-04-10T10:05:00",
                "total_participants": 2,
                "results": [
                    {"username": "alice", "placement": 1, "points": 10.0, "survival_time": 50.0, "kills": 2},
                    {"username": "bob", "placement": 2, "points": 5.0, "survival_time": 30.0, "kills": 0},
                ],
                "non_scoring": True,
            }

            self._write_json(
                events_days_dir / "136.json",
                {
                    "day_number": 136,
                    "total_games": 2,
                    "games": [
                        {
                            "game_id": canonical_game["game_id"],
                            "game_type": canonical_game["game_type"],
                            "game_display_name": canonical_game["game_display_name"],
                            "timestamp": canonical_game["timestamp"],
                            "total_participants": canonical_game["total_participants"],
                            "non_scoring": canonical_game["non_scoring"],
                        },
                        {
                            "game_id": noncanonical_game["game_id"],
                            "game_type": noncanonical_game["game_type"],
                            "game_display_name": noncanonical_game["game_display_name"],
                            "timestamp": noncanonical_game["timestamp"],
                            "total_participants": noncanonical_game["total_participants"],
                            "non_scoring": noncanonical_game["non_scoring"],
                        },
                    ],
                },
            )
            self._write_json(events_games_dir / f"{canonical_game['game_id']}.json", canonical_game)
            self._write_json(events_games_dir / f"{noncanonical_game['game_id']}.json", noncanonical_game)

            syncer = WebsiteDeltaSync(
                repo_root=root,
                api_dir=api_dir,
                public_dir=root / "website" / "public",
                events_days_dir=events_days_dir,
                events_games_dir=events_games_dir,
                avatar_cache_dir=avatar_cache_dir,
                sync_state_path=sync_state_path,
            )

            with mock.patch("shared.website_delta_sync.GameHistory", side_effect=AssertionError("should not load game history")):
                result = syncer.sync_day(136, publish_to_r2=False, refresh_club_member_stats=False)

            self.assertTrue(result.ok)
            self.assertTrue((api_dir / "games" / f"{canonical_game['game_id']}.json").exists())
            self.assertFalse((api_dir / "games" / f"{noncanonical_game['game_id']}.json").exists())

            day_payload = self._read_json(api_dir / "days" / "136.json")
            self.assertEqual(day_payload["total_games"], 1)
            self.assertEqual(day_payload["games"][0]["game_id"], canonical_game["game_id"])

            aggregate_payload = self._read_json(api_dir / "days" / "136_aggregate.json")
            self.assertEqual(aggregate_payload["total_participants"], 2)
            self.assertEqual(aggregate_payload["results"][0]["username"], "alice")
            self.assertEqual(aggregate_payload["results"][0]["points"], 10.0)

            players_a = self._read_json(api_dir / "players" / "a.json")
            players_b = self._read_json(api_dir / "players" / "b.json")
            self.assertEqual(players_a["players"]["alice"]["s"][0], 30.0)
            self.assertEqual(players_a["players"]["alice"]["s"][1], 2)
            self.assertEqual(players_a["players"]["alice"]["rg"][0], canonical_game["game_id"])
            self.assertEqual(players_b["players"]["bob"]["s"][0], 5.0)
            self.assertEqual(players_b["players"]["bob"]["s"][1], 1)

            players_index = self._read_json(api_dir / "players" / "index.json")
            alice_entry = next(entry for entry in players_index["players"] if entry["u"] == "alice")
            bob_entry = next(entry for entry in players_index["players"] if entry["u"] == "bob")
            self.assertEqual(alice_entry["p"], 30.0)
            self.assertEqual(alice_entry["w"], 1)
            self.assertEqual(bob_entry["p"], 5.0)
            self.assertIn("t3", alice_entry)
            self.assertIn("t10", alice_entry)

            history_index = self._read_json(api_dir / "player_history" / "index.json")
            self.assertEqual(history_index["game_count"], 2)
            self.assertEqual(history_index["games"][-1][0], canonical_game["game_id"])

            leaderboard = self._read_json(api_dir / "leaderboards" / "2026-04.json")
            self.assertEqual(leaderboard["leaderboard"][0]["u"], "alice")
            self.assertEqual(leaderboard["leaderboard"][0]["p"], 30.0)

            index_payload = self._read_json(api_dir / "index.json")
            self.assertEqual(index_payload["total_games"], 2)
            self.assertEqual(index_payload["total_days"], 2)
            self.assertIn(136, index_payload["available_days"])
            self.assertIn("platforms", index_payload)

            instagram_day = self._read_json(api_dir / "platforms" / "instagram" / "days" / "136.json")
            self.assertEqual(instagram_day["platform"], "instagram")
            self.assertEqual(instagram_day["total_games"], 1)
            self.assertEqual(instagram_day["games"][0]["game_type"], "battle_royale")

            instagram_players = self._read_json(api_dir / "platforms" / "instagram" / "players" / "a.json")
            self.assertEqual(instagram_players["players"]["alice"]["s"][0], 10.0)
            self.assertEqual(instagram_players["players"]["alice"]["gb"]["battle_royale"], 1)

            youtube_index = self._read_json(api_dir / "platforms" / "youtube" / "index.json")
            self.assertEqual(youtube_index["total_games"], 0)

            hall_payload = self._read_json(api_dir / "hall_of_fame.json")
            self.assertEqual(hall_payload["daily_champions"][0]["day"], 136)
            self.assertEqual(hall_payload["daily_champions"][0]["username"], "alice")

            second = syncer.sync_day(136, publish_to_r2=False, refresh_club_member_stats=False)
            self.assertTrue(second.ok)

            players_a_second = self._read_json(api_dir / "players" / "a.json")
            history_index_second = self._read_json(api_dir / "player_history" / "index.json")
            leaderboard_second = self._read_json(api_dir / "leaderboards" / "2026-04.json")
            self.assertEqual(players_a_second["players"]["alice"]["s"][0], 30.0)
            self.assertEqual(history_index_second["game_count"], 2)
            self.assertEqual(leaderboard_second["leaderboard"][0]["p"], 30.0)
