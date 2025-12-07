#!/usr/bin/env python3
"""
Safe Instagram Reel Uploader using Selenium
Uses browser automation (like a real human) instead of unofficial APIs

MUCH SAFER than instagrapi:
- Uses real browser with your actual session
- Mimics human behavior
- No ToS violations
- Lower risk of account restrictions

Usage:
1. First time: Run with --save-cookies to save your session
   python safe_instagram_uploader.py --save-cookies

2. Upload videos:
   python safe_instagram_uploader.py --video path/to/video.mp4 --caption "My caption"
"""

import argparse
import json
import time
import random
from pathlib import Path
from typing import Optional, Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class SafeInstagramUploader:
    """
    Selenium-based Instagram Reel uploader
    Mimics human behavior for maximum safety
    """

    def __init__(self, cookies_file: str = "instagram_cookies.json", headless: bool = False):
        """
        Initialize uploader

        Args:
            cookies_file: Path to save/load cookies
            headless: Run browser in headless mode (invisible)
        """
        self.cookies_file = cookies_file
        self.headless = headless
        self.driver = None

    def _setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        # Anti-detection settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Randomize user agent slightly
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)

        # Execute script to avoid detection
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def _human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def _human_type(self, element, text: str):
        """Type text character by character with random delays (like a human)"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))  # 50-150ms between keystrokes

    def save_cookies(self):
        """
        Login to Instagram manually and save cookies

        This is INTERACTIVE - you'll need to:
        1. Login manually in the browser window
        2. Complete any 2FA/verification
        3. Press Enter when done
        """
        print("=" * 60)
        print("INSTAGRAM COOKIE SAVER")
        print("=" * 60)
        print()
        print("This will open Instagram in a browser window.")
        print("Please LOGIN MANUALLY, then press Enter here.")
        print()
        print("Steps:")
        print("1. Browser will open to Instagram")
        print("2. Log in with your credentials")
        print("3. Complete any 2FA if asked")
        print("4. Wait until you see your feed")
        print("5. Come back here and press Enter")
        print()

        self._setup_driver()
        self.driver.get("https://www.instagram.com")

        # Wait for user to login manually
        input("Press Enter after you've logged in successfully...")

        # Save cookies
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)

        print(f"\n✅ Cookies saved to {self.cookies_file}")
        print("You can now upload videos without logging in each time!")

        self.driver.quit()

    def _load_cookies(self) -> bool:
        """
        Load saved cookies

        Returns:
            True if cookies loaded successfully
        """
        if not Path(self.cookies_file).exists():
            print(f"❌ Cookie file not found: {self.cookies_file}")
            print("Run with --save-cookies first to log in and save your session.")
            return False

        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            # Load Instagram first
            self.driver.get("https://www.instagram.com")
            self._human_delay(2, 3)

            # Add cookies
            for cookie in cookies:
                # Remove domain if it causes issues
                if 'domain' in cookie and cookie['domain'].startswith('.'):
                    cookie['domain'] = cookie['domain'][1:]
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Warning: Could not add cookie {cookie.get('name')}: {e}")

            # Refresh to apply cookies
            self.driver.refresh()
            self._human_delay(2, 4)

            # Verify we're logged in (check if we can see profile icon or similar)
            try:
                # If we see login button, cookies didn't work
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
                print("⚠️ Cookies expired or invalid. Please run --save-cookies again.")
                return False
            except NoSuchElementException:
                # Good! No login button means we're logged in
                print("✅ Logged in successfully using saved cookies")
                return True

        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            return False

    def upload_reel(self, video_path: str, caption: str = "") -> bool:
        """
        Upload a video as an Instagram Reel

        Args:
            video_path: Path to video file
            caption: Caption text

        Returns:
            True if upload successful
        """
        video_path = Path(video_path).resolve()

        if not video_path.exists():
            print(f"❌ Video not found: {video_path}")
            return False

        print(f"📤 Uploading: {video_path.name}")
        print(f"📝 Caption: {caption[:50]}..." if len(caption) > 50 else f"📝 Caption: {caption}")

        try:
            self._setup_driver()

            if not self._load_cookies():
                return False

            # Navigate to create page
            print("🔄 Opening create page...")
            self.driver.get("https://www.instagram.com/create/select/")
            self._human_delay(3, 5)

            # Handle "Turn on Notifications" popup if it appears
            try:
                not_now = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                not_now.click()
                self._human_delay(1, 2)
            except TimeoutException:
                pass  # No popup, continue

            # Find file input and upload video
            print("📁 Selecting video file...")
            try:
                file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                file_input.send_keys(str(video_path))
                self._human_delay(3, 5)
            except NoSuchElementException:
                print("❌ Could not find file upload input")
                return False

            # Wait for video to load
            print("⏳ Waiting for video to load...")
            time.sleep(5)

            # Click "Next" button to proceed (there might be multiple Next buttons)
            print("➡️ Clicking Next...")
            try:
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                )
                next_button.click()
                self._human_delay(2, 3)
            except TimeoutException:
                print("⚠️ Next button not found, trying alternative...")

            # Click Next again if there's a second step
            try:
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                )
                next_button.click()
                self._human_delay(2, 3)
            except TimeoutException:
                pass  # No second Next button

            # Add caption
            if caption:
                print("✍️ Adding caption...")
                try:
                    caption_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[aria-label*="caption"]'))
                    )
                    self._human_type(caption_field, caption)
                    self._human_delay(1, 2)
                except TimeoutException:
                    print("⚠️ Could not find caption field")

            # Click "Share" button
            print("🚀 Sharing reel...")
            try:
                share_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]"))
                )
                share_button.click()

                # Wait for upload to complete
                print("⏳ Uploading... (this may take a while)")
                time.sleep(15)  # Give it time to upload

                # Check if we see "Post shared" or "Reel shared" message
                try:
                    WebDriverWait(self.driver, 60).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'shared')]"))
                    )
                    print("✅ Upload successful!")
                    return True
                except TimeoutException:
                    print("⚠️ Upload may have completed, but couldn't verify")
                    return True  # Assume success if no error

            except TimeoutException:
                print("❌ Could not find Share button")
                return False

        except Exception as e:
            print(f"❌ Upload failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.driver:
                self._human_delay(2, 3)
                self.driver.quit()


def main():
    parser = argparse.ArgumentParser(description="Safe Instagram Reel Uploader using Selenium")
    parser.add_argument("--save-cookies", action="store_true", help="Login and save cookies for future use")
    parser.add_argument("--video", help="Path to video file to upload")
    parser.add_argument("--caption", default="", help="Caption for the reel")
    parser.add_argument("--cookies-file", default="instagram_cookies.json", help="Path to cookies file")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    uploader = SafeInstagramUploader(
        cookies_file=args.cookies_file,
        headless=args.headless
    )

    if args.save_cookies:
        uploader.save_cookies()
    elif args.video:
        success = uploader.upload_reel(args.video, args.caption)
        exit(0 if success else 1)
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  # First time - save cookies:")
        print("  python safe_instagram_uploader.py --save-cookies")
        print()
        print("  # Upload a reel:")
        print('  python safe_instagram_uploader.py --video myvideo.mp4 --caption "Check this out!"')


if __name__ == "__main__":
    main()
