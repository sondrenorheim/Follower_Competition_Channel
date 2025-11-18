"""
Instagram API Integration Module
Handles fetching followers and profile images from Instagram Graph API
Falls back to offline mode if API is unavailable
"""

import requests
from PIL import Image
import io
import random
from typing import List, Dict, Optional
import config


class InstagramAPI:
    """
    Handles Instagram Graph API integration for fetching followers
    Provides offline mode with placeholder data if API is unavailable
    """

    def __init__(self, access_token: str = "", user_id: str = ""):
        """
        Initialize Instagram API client

        Args:
            access_token: Instagram Graph API access token
            user_id: Instagram user ID to fetch followers from
        """
        self.access_token = access_token or config.INSTAGRAM_ACCESS_TOKEN
        self.user_id = user_id or config.INSTAGRAM_USER_ID
        self.base_url = "https://graph.instagram.com"

    def fetch_followers(self, count: int = 500) -> List[Dict[str, any]]:
        """
        Fetch followers from Instagram API or generate placeholder data

        Args:
            count: Number of followers to fetch/generate

        Returns:
            List of follower dictionaries with 'id', 'username', and 'avatar' keys
        """
        # Check if we should use offline mode
        if config.USE_OFFLINE_MODE or not self.access_token or not self.user_id:
            print(f"Running in OFFLINE MODE - Generating {count} placeholder followers")
            return self._generate_placeholder_followers(count)

        # Try to fetch from Instagram API
        try:
            print(f"Attempting to fetch followers from Instagram API...")
            followers = self._fetch_from_api(count)
            if followers:
                print(f"Successfully fetched {len(followers)} followers from API")
                return followers
            else:
                print("API returned no data, falling back to offline mode")
                return self._generate_placeholder_followers(count)
        except Exception as e:
            print(f"API fetch failed: {e}")
            print(f"Falling back to offline mode")
            return self._generate_placeholder_followers(count)

    def _fetch_from_api(self, count: int) -> Optional[List[Dict[str, any]]]:
        """
        Fetch real followers from Instagram Graph API

        Args:
            count: Number of followers to fetch

        Returns:
            List of follower data or None if failed
        """
        followers = []
        url = f"{self.base_url}/{self.user_id}/followers"
        params = {
            "access_token": self.access_token,
            "limit": min(count, 100),  # API limit per request
            "fields": "id,username,profile_picture_url"
        }

        while len(followers) < count:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "data" not in data or not data["data"]:
                break

            # Process each follower
            for follower_data in data["data"]:
                if len(followers) >= count:
                    break

                follower = {
                    "id": follower_data.get("id", f"user_{len(followers)}"),
                    "username": follower_data.get("username", f"user_{len(followers)}"),
                    "avatar": self._download_avatar(
                        follower_data.get("profile_picture_url")
                    )
                }
                followers.append(follower)

            # Check for pagination
            if "paging" in data and "next" in data["paging"]:
                url = data["paging"]["next"]
            else:
                break

        return followers if followers else None

    def _download_avatar(self, url: Optional[str]) -> Optional[Image.Image]:
        """
        Download avatar image from URL

        Args:
            url: URL of the avatar image

        Returns:
            PIL Image object or None if failed
        """
        if not url:
            return None

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            return img.convert("RGBA")
        except Exception as e:
            print(f"Failed to download avatar from {url}: {e}")
            return None

    def _generate_placeholder_followers(self, count: int) -> List[Dict[str, any]]:
        """
        Generate placeholder followers for offline mode
        Creates followers with random colored avatars

        Args:
            count: Number of placeholder followers to generate

        Returns:
            List of placeholder follower dictionaries
        """
        followers = []

        # Generate diverse placeholder names
        name_prefixes = ["Shadow", "Storm", "Nova", "Echo", "Blade", "Frost",
                        "Phoenix", "Raven", "Viper", "Ghost", "Thunder", "Mystic",
                        "Cyber", "Neon", "Luna", "Solar", "Void", "Stellar"]
        name_suffixes = ["Hunter", "Warrior", "Master", "Knight", "Ranger", "Sage",
                        "Champion", "Slayer", "Guardian", "Assassin", "Mage", "Ninja"]

        for i in range(count):
            # Generate unique username
            if i < len(name_prefixes) * len(name_suffixes):
                prefix = name_prefixes[i % len(name_prefixes)]
                suffix = name_suffixes[i // len(name_prefixes)]
                username = f"{prefix}{suffix}{random.randint(1, 999)}"
            else:
                username = f"Player{i + 1}"

            # Create colored avatar (will be generated in renderer)
            color = random.choice(config.RANDOM_COLORS)

            follower = {
                "id": f"placeholder_{i}",
                "username": username,
                "avatar": None,  # Will be generated as colored circle
                "color": color   # Random color for placeholder
            }
            followers.append(follower)

        return followers
