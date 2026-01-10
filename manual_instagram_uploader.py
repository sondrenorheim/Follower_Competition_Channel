"""
Manual Instagram Uploader with Persistent Session
===================================================
Opens browser once, you upload manually, session stays open all day.
Perfect for avoiding automation detection and 2FA issues.
"""

import time
import json
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class ManualInstagramUploader:
    """
    Opens Instagram in a persistent browser session.
    You do all uploads manually through the browser.
    Browser stays open all day - no re-authentication needed.
    """

    def __init__(self, cookies_file: str = "instagram_cookies.json"):
        """
        Initialize manual uploader

        Args:
            cookies_file: Path to save/load cookies
        """
        self.cookies_file = cookies_file
        self.driver = None
        self.session_active = False

    def _log(self, message: str):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}", flush=True)

    def start_session(self):
        """
        Open browser and navigate to Instagram.
        You handle login/2FA manually.
        """
        self._log("=" * 60)
        self._log("STARTING MANUAL INSTAGRAM SESSION")
        self._log("=" * 60)

        try:
            # Setup Chrome
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            self._log("Opening Chrome browser...")
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Navigate to Instagram
            self._log("Loading Instagram...")
            self.driver.get("https://www.instagram.com")
            time.sleep(3)

            # Try to load cookies
            if Path(self.cookies_file).exists():
                self._log(f"Loading saved cookies from {self.cookies_file}...")
                try:
                    with open(self.cookies_file, 'r') as f:
                        cookies = json.load(f)

                    for cookie in cookies:
                        if 'domain' in cookie and cookie['domain'].startswith('.'):
                            cookie['domain'] = cookie['domain'][1:]
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            pass

                    self.driver.refresh()
                    time.sleep(3)
                    self._log("Cookies loaded - you may already be logged in!")
                except Exception as e:
                    self._log(f"Could not load cookies: {e}")

            # Prompt user to login/verify
            self._log("")
            self._log("=" * 60)
            self._log("MANUAL LOGIN/VERIFICATION REQUIRED")
            self._log("=" * 60)
            print()
            print("The Chrome browser is now open showing Instagram.")
            print()
            print("Please complete the following in the browser:")
            print("  1. Login if needed (username + password)")
            print("  2. Complete 2FA verification if prompted")
            print("  3. Dismiss any popups (notifications, etc.)")
            print("  4. Wait until you see your Instagram home feed")
            print()
            print("After you're logged in and on the home feed:")
            print("  - Come back here and press Enter")
            print()
            print("=" * 60)
            print()

            input("Press Enter AFTER you're logged in and see your home feed... ")

            # Save cookies for next time
            self._log("Saving session cookies for future use...")
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            self._log(f"Cookies saved to {self.cookies_file}")

            self.session_active = True
            self._log("")
            self._log("=" * 60)
            self._log("SESSION STARTED SUCCESSFULLY")
            self._log("Browser will stay open - keep it open all day!")
            self._log("=" * 60)
            return True

        except Exception as e:
            self._log(f"Failed to start session: {e}")
            import traceback
            traceback.print_exc()
            return False

    def wait_for_manual_upload(self, video_name: str):
        """
        Pause and let you upload manually in the browser.

        Args:
            video_name: Name of video to upload (for logging)
        """
        if not self.session_active:
            self._log("ERROR: No active session! Call start_session() first.")
            return False

        self._log("")
        self._log("=" * 60)
        self._log(f"READY TO UPLOAD: {video_name}")
        self._log("=" * 60)
        print()
        print("Now upload this video MANUALLY in the browser:")
        print(f"  Video: {video_name}")
        print()
        print("Steps:")
        print("  1. Click the '+' (Create) button in Instagram")
        print("  2. Select your video file")
        print("  3. Add caption, hashtags, etc.")
        print("  4. Click 'Share' to upload")
        print("  5. Wait for 'Your reel has been shared' confirmation")
        print("  6. Come back here and press Enter")
        print()
        print("=" * 60)
        print()

        input(f"Press Enter AFTER '{video_name}' has been uploaded... ")

        self._log(f"Upload confirmed for: {video_name}")
        return True

    def close_session(self):
        """Close the browser"""
        if self.driver:
            self._log("")
            self._log("=" * 60)
            self._log("CLOSING INSTAGRAM SESSION")
            self._log("=" * 60)
            self.driver.quit()
            self.driver = None
            self.session_active = False
            self._log("Browser closed. Session ended.")

    def keep_alive(self):
        """
        Keep browser open indefinitely until user closes it.
        Useful for keeping session alive all day.
        """
        if not self.session_active:
            self._log("ERROR: No active session!")
            return

        self._log("")
        self._log("=" * 60)
        self._log("SESSION IS ACTIVE")
        self._log("=" * 60)
        print()
        print("The browser is open and logged in to Instagram.")
        print("You can upload videos manually whenever you want.")
        print()
        print("Browser will stay open until you:")
        print("  - Close the browser window manually, OR")
        print("  - Press Ctrl+C here to end the session")
        print()
        print("=" * 60)
        print()

        try:
            while True:
                time.sleep(60)  # Check every minute if browser still open
                try:
                    # Check if browser is still alive
                    self.driver.current_url
                except:
                    self._log("Browser was closed. Ending session.")
                    break
        except KeyboardInterrupt:
            self._log("Session stopped by user (Ctrl+C)")

        self.session_active = False


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("MANUAL INSTAGRAM UPLOADER")
    print("=" * 60)
    print()
    print("This will open Instagram in Chrome.")
    print("You upload videos manually through the browser.")
    print("Browser stays open all day - no re-authentication!")
    print()

    uploader = ManualInstagramUploader()

    # Start session (login once, handle 2FA)
    if uploader.start_session():
        # Example: Upload multiple videos manually
        videos = [
            "battle_royale_day_29.mp4",
            "obstacle_course_day_29.mp4",
            "snake_escape_day_29.mp4",
        ]

        for video in videos:
            uploader.wait_for_manual_upload(video)
            print()
            print("Waiting 2 minutes before next upload...")
            time.sleep(120)  # 2 minute delay

        # Keep browser open
        print()
        print("All uploads done! Browser will stay open...")
        uploader.keep_alive()

        # Close when done
        uploader.close_session()
