from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from maintenance.bootstrap_website_api_baseline import _current_api_max_day, _iter_games_from_history_stream


class BootstrapWebsiteApiBaselineTests(unittest.TestCase):
    def test_current_api_max_day_uses_best_available_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            api_dir = Path(tmp_dir) / "website" / "public" / "api"
            (api_dir / "player_history").mkdir(parents=True, exist_ok=True)

            (api_dir / "hall_of_fame.json").write_text(
                json.dumps(
                    {
                        "daily_champions": [
                            {"day": 113},
                            {"day": 110},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (api_dir / "player_history" / "index.json").write_text(
                json.dumps(
                    {
                        "games": [
                            ["g1", "math_drop", 111, "2026-03-12T00:00:00"],
                            ["g2", "flappy_followers", 112, "2026-03-13T00:00:00"],
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (api_dir / "index.json").write_text(
                json.dumps(
                    {
                        "available_days": [108, 109],
                        "days_metadata": [{"day": 107}],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(_current_api_max_day(api_dir), 113)

    def test_current_api_max_day_returns_zero_when_metadata_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            api_dir = Path(tmp_dir) / "website" / "public" / "api"
            api_dir.mkdir(parents=True, exist_ok=True)
            self.assertEqual(_current_api_max_day(api_dir), 0)

    def test_iter_games_from_history_stream_reads_games_incrementally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "game_history.json"
            history_path.write_text(
                json.dumps(
                    {
                        "games": [
                            {
                                "game_id": "g1",
                                "day_number": 114,
                                "game_type": "math_drop",
                                "note": 'brace { test } and "quotes"',
                            },
                            {
                                "game_id": "g2",
                                "day_number": 115,
                                "game_type": "flappy_followers",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payloads = list(_iter_games_from_history_stream(history_path))
            self.assertEqual([payload["game_id"] for payload in payloads], ["g1", "g2"])
            self.assertEqual(payloads[0]["note"], 'brace { test } and "quotes"')


if __name__ == "__main__":
    unittest.main()
