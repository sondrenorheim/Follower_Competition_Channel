"""
Instagram API Integration Module
Handles fetching followers and profile images from Instagram Graph API
Also supports web scraping via Instaloader as an alternative
Also supports importing from CSV/JSON files (SAFE - recommended!)
Falls back to offline mode if API is unavailable

⚠️ WARNING: Web scraping violates Instagram's Terms of Service
   and may result in account suspension. Use at your own risk.
"""

import requests
from PIL import Image
import io
import random
import os
import json
import csv
from typing import List, Dict, Optional
import config


class InstagramAPI:
    """
    Handles Instagram data fetching via multiple methods:
    1. CSV/JSON Import (✅ SAFE - recommended! Use Instagram Data Download)
    2. Official Instagram Graph API (recommended, requires business account)
    3. Web scraping via Instaloader (⚠️ violates ToS, account risk)
    4. Offline mode with placeholder data (safe, no authentication)
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
        self.scraper_mode = getattr(config, 'USE_INSTALOADER_SCRAPER', False)
        self.insta_username = getattr(config, 'INSTAGRAM_USERNAME', '')
        self.insta_password = getattr(config, 'INSTAGRAM_PASSWORD', '')
        self.import_file = getattr(config, 'FOLLOWER_IMPORT_FILE', '')

    def fetch_followers(self, count: int = 500) -> List[Dict[str, any]]:
        """
        Fetch followers using configured method (Import, API, Scraper, or Offline)

        Args:
            count: Number of followers to fetch/generate

        Returns:
            List of follower dictionaries with 'id', 'username', and 'avatar' keys
        """
        # Priority 1: Import from file if specified (SAFE!)
        if self.import_file and os.path.exists(self.import_file):
            print(f"✅ Importing followers from file: {self.import_file}")
            try:
                followers = self._import_from_file(self.import_file, count)
                if followers:
                    print(f"✅ Successfully imported {len(followers)} followers")
                    return followers
            except Exception as e:
                print(f"❌ Import failed: {e}")
                print(f"Falling back to offline mode")
                return self._generate_placeholder_followers(count)

        # Priority 2: Use Instaloader scraper if enabled (RISKY!)
        if self.scraper_mode and self.insta_username:
            print(f"⚠️  Using INSTALOADER SCRAPER (violates Instagram ToS)")
            try:
                followers = self._fetch_via_instaloader(count)
                if followers:
                    print(f"✅ Successfully scraped {len(followers)} followers")
                    return followers
            except Exception as e:
                print(f"❌ Scraper failed: {e}")
                print(f"Falling back to offline mode")
                return self._generate_placeholder_followers(count)

        # Priority 3: Use official API if credentials available (SAFE)
        if not config.USE_OFFLINE_MODE and self.access_token and self.user_id:
            try:
                print(f"Attempting to fetch followers from Instagram Graph API...")
                followers = self._fetch_from_api(count)
                if followers:
                    print(f"✅ Successfully fetched {len(followers)} followers from API")
                    return followers
                else:
                    print("API returned no data, falling back to offline mode")
            except Exception as e:
                print(f"❌ API fetch failed: {e}")
                print(f"Falling back to offline mode")

        # Priority 4: Offline mode (default, safe)
        print(f"Running in OFFLINE MODE - Generating {count} placeholder followers")
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

    def _fetch_via_instaloader(self, count: int) -> Optional[List[Dict[str, any]]]:
        """
        Fetch followers using Instaloader web scraping library

        ⚠️ WARNING: This violates Instagram's Terms of Service!
        - Your account may be banned or suspended
        - Use a burner account if possible
        - Don't run this frequently (Instagram has rate limits)
        - Two-factor authentication must be disabled or handled manually

        Args:
            count: Number of followers to fetch

        Returns:
            List of follower data or None if failed
        """
        try:
            import instaloader
        except ImportError:
            print("❌ Instaloader not installed. Run: pip install instaloader")
            return None

        print(f"Initializing Instaloader...")
        L = instaloader.Instaloader(
            download_pictures=True,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True  # Suppress verbose output
        )

        # Login (required to access follower lists)
        try:
            print(f"Logging in as @{self.insta_username}...")

            # Try to load existing session first
            session_file = f".instaloader_session_{self.insta_username}"
            try:
                L.load_session_from_file(self.insta_username, session_file)
                print("✅ Loaded existing session")
            except FileNotFoundError:
                # No existing session, need to login
                if not self.insta_password:
                    print("❌ No password provided and no existing session found")
                    return None

                L.login(self.insta_username, self.insta_password)
                L.save_session_to_file(session_file)
                print("✅ Login successful, session saved")

        except instaloader.exceptions.TwoFactorAuthRequiredException:
            print("❌ Two-factor authentication required!")
            print("   Please disable 2FA temporarily or handle it manually")
            return None
        except instaloader.exceptions.BadCredentialsException:
            print("❌ Invalid username or password")
            return None
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return None

        # Get target username (use logged-in user's followers)
        target_username = getattr(config, 'INSTAGRAM_TARGET_USERNAME', self.insta_username)

        try:
            print(f"Fetching profile for @{target_username}...")
            profile = instaloader.Profile.from_username(L.context, target_username)

            print(f"Found @{target_username}: {profile.full_name}")
            print(f"Total followers: {profile.followers}")
            print(f"Fetching up to {count} followers (this may take a while)...")

            followers = []

            # Iterate through followers
            for i, follower in enumerate(profile.get_followers()):
                if i >= count:
                    break

                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"   Scraped {i + 1}/{count} followers...")

                # Download profile picture
                avatar_img = None
                try:
                    # Download profile picture to memory
                    L.download_profilepic(follower, target=f".temp_avatar_{follower.username}")

                    # Find the downloaded image
                    import glob
                    avatar_files = glob.glob(f".temp_avatar_{follower.username}/*")
                    if avatar_files:
                        avatar_img = Image.open(avatar_files[0]).convert("RGBA")

                        # Clean up temporary files
                        import shutil
                        shutil.rmtree(f".temp_avatar_{follower.username}")
                except Exception as e:
                    # If profile pic download fails, continue without it
                    pass

                follower_data = {
                    "id": str(follower.userid),
                    "username": follower.username,
                    "avatar": avatar_img
                }
                followers.append(follower_data)

                # Be nice to Instagram's servers (rate limiting)
                import time
                time.sleep(0.5)  # 500ms delay between each follower

            print(f"✅ Successfully scraped {len(followers)} followers")
            return followers

        except instaloader.exceptions.ProfileNotExistsException:
            print(f"❌ Profile @{target_username} does not exist")
            return None
        except instaloader.exceptions.LoginRequiredException:
            print("❌ Login required but session expired")
            return None
        except Exception as e:
            print(f"❌ Error fetching followers: {e}")
            return None

    def _import_from_file(self, file_path: str, count: int) -> Optional[List[Dict[str, any]]]:
        """
        Import followers from CSV or JSON file

        ✅ SAFE METHOD - Use Instagram's Data Download feature to get this file!

        Supports multiple formats:
        1. Instagram Data Download JSON (followers.json from Instagram export)
        2. Custom CSV with 'username' column
        3. Custom JSON array with username field

        Args:
            file_path: Path to CSV or JSON file
            count: Maximum number of followers to import

        Returns:
            List of follower data or None if failed
        """
        followers = []
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            # Handle JSON files
            if file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Instagram Data Download format (various structures)
                    if isinstance(data, dict):
                        # Try common Instagram export structures
                        if 'followers' in data:
                            # Format: {"followers": [{"string_list_data": [{"value": "username"}]}]}
                            follower_list = data['followers']
                        elif 'relationships_followers' in data:
                            follower_list = data['relationships_followers']
                        else:
                            # Assume dict with usernames somewhere
                            follower_list = data.get('data', [])
                    elif isinstance(data, list):
                        # Simple array format
                        follower_list = data
                    else:
                        print(f"❌ Unsupported JSON format")
                        return None

                    # Extract usernames from various formats
                    for i, item in enumerate(follower_list):
                        if i >= count:
                            break

                        username = None

                        # Instagram export format
                        if isinstance(item, dict):
                            # Format 1: {"string_list_data": [{"value": "username"}]}
                            if 'string_list_data' in item:
                                username = item['string_list_data'][0].get('value')
                            # Format 2: {"username": "username"}
                            elif 'username' in item:
                                username = item['username']
                            # Format 3: {"value": "username"}
                            elif 'value' in item:
                                username = item['value']
                        # Simple string array
                        elif isinstance(item, str):
                            username = item

                        if username:
                            followers.append({
                                "id": f"imported_{i}",
                                "username": username,
                                "avatar": None,
                                "color": random.choice(config.RANDOM_COLORS)
                            })

            # Handle CSV files
            elif file_ext == '.csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)

                    for i, row in enumerate(reader):
                        if i >= count:
                            break

                        # Look for username column (case-insensitive)
                        username = None
                        for key in row.keys():
                            if key.lower() in ['username', 'user', 'name', 'follower']:
                                username = row[key]
                                break

                        if username:
                            followers.append({
                                "id": f"imported_{i}",
                                "username": username,
                                "avatar": None,
                                "color": random.choice(config.RANDOM_COLORS)
                            })

            # Handle plain text files (one username per line)
            elif file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= count:
                            break

                        username = line.strip()
                        if username:
                            followers.append({
                                "id": f"imported_{i}",
                                "username": username,
                                "avatar": None,
                                "color": random.choice(config.RANDOM_COLORS)
                            })

            else:
                print(f"❌ Unsupported file format: {file_ext}")
                print(f"   Supported formats: .json, .csv, .txt")
                return None

            if followers:
                return followers
            else:
                print(f"❌ No followers found in file")
                return None

        except Exception as e:
            print(f"❌ Error reading file: {e}")
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
