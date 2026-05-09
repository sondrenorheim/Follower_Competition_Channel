import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config
from shared.website_platforms import (
    build_platform_game_buckets,
    classify_game_platforms,
    normalize_website_game_display_name,
    normalize_website_game_type,
)


class WebsitePlatformTests(unittest.TestCase):
    def test_base_game_defaults_to_instagram(self):
        game = {"game_id": "g1", "game_type": "flappy_followers", "day_number": 1}

        self.assertEqual(classify_game_platforms(game, {"youtube": set(), "facebook": set()}), {"instagram"})

    def test_legacy_native_youtube_game_is_youtube_only(self):
        game = {
            "game_id": "g1",
            "game_type": "youtube_flappy_followers",
            "game_display_name": "Flappy Followers (YouTube)",
            "day_number": 1,
        }

        self.assertEqual(classify_game_platforms(game, {"youtube": set(), "facebook": set()}), {"youtube"})
        self.assertEqual(normalize_website_game_type(game["game_type"]), "flappy_followers")
        self.assertEqual(normalize_website_game_display_name(game["game_type"], game["game_display_name"]), "Flappy Followers")

    def test_audience_only_game_is_hidden_without_post_mapping(self):
        game = {"game_id": "g1", "game_type": "youtube_followers_fighter_arena", "day_number": 1}

        self.assertEqual(classify_game_platforms(game, {"youtube": set(), "facebook": set()}), set())

    def test_post_mappings_promote_only_the_mapped_platform(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            youtube_map = root / "youtube_map.json"
            facebook_map = root / "facebook_map.json"
            youtube_map.write_text(
                json.dumps({"video:abc": {"game_type": "youtube_followers_fighter_arena", "day_number": 10}}),
                encoding="utf-8",
            )
            facebook_map.write_text(
                json.dumps({"video:def": {"game_type": "battle_royale", "day_number": 10}}),
                encoding="utf-8",
            )

            games = [
                {
                    "game_id": "yt_followers",
                    "game_type": "youtube_followers_fighter_arena",
                    "game_display_name": "Fighter Arena (YouTube Followers)",
                    "day_number": 10,
                    "timestamp": "2026-05-01T10:00:00",
                    "total_participants": 1,
                    "results": [{"username": "yt", "placement": 1, "points": 5}],
                    "non_scoring": True,
                },
                {
                    "game_id": "ig_and_fb",
                    "game_type": "battle_royale",
                    "game_display_name": "Battle Royale",
                    "day_number": 10,
                    "timestamp": "2026-05-01T10:05:00",
                    "total_participants": 1,
                    "results": [{"username": "fb", "placement": 1, "points": 5}],
                },
            ]

            with (
                mock.patch.object(config, "YOUTUBE_MEDIA_GAME_MAP_PATH", str(youtube_map), create=True),
                mock.patch.object(config, "FACEBOOK_MEDIA_GAME_MAP_PATH", str(facebook_map), create=True),
            ):
                buckets = build_platform_game_buckets(games, repo_root=root)

        self.assertEqual([game["game_id"] for game in buckets["youtube"]], ["yt_followers"])
        self.assertEqual([game["game_id"] for game in buckets["facebook"]], ["ig_and_fb"])
        self.assertEqual([game["game_id"] for game in buckets["instagram"]], ["ig_and_fb"])
        self.assertFalse(buckets["youtube"][0]["non_scoring"])
        self.assertEqual(buckets["youtube"][0]["game_type"], "fighter_arena")


if __name__ == "__main__":
    unittest.main()
