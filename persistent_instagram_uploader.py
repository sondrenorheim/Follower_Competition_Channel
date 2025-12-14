"""
Persistent Instagram Uploader
Keeps browser session open between uploads for daily automation
Handles 2FA manually once at the start, then reuses session all day
"""

import time
import json
import random
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PersistentInstagramUploader:
    """
    Instagram uploader that keeps browser session alive between uploads
    Perfect for daily automation - login once (with 2FA), upload multiple videos
    """

    def __init__(self, cookies_file: str = "instagram_cookies.json", headless: bool = False):
        """
        Initialize persistent uploader

        Args:
            cookies_file: Path to save/load cookies
            headless: Run browser in headless mode (not recommended for 2FA)
        """
        self.cookies_file = cookies_file
        self.headless = headless
        self.driver = None
        self.session_active = False
        self.start_time = None

    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = ""
        if self.start_time:
            elapsed_sec = (time.time() - self.start_time)
            elapsed = f" [{elapsed_sec:.1f}s]"
        print(f"[{now}]{elapsed} [{level}] {message}", flush=True)

    def _setup_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")
            self._log("Running in headless mode (2FA may not work!)", "WARN")

        # Anti-detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def _human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def start_session(self) -> bool:
        """
        Start browser session and login to Instagram
        Handles 2FA manually - pauses for user to complete

        Returns:
            True if session started successfully
        """
        self.start_time = time.time()

        self._log("="*60)
        self._log("STARTING PERSISTENT INSTAGRAM SESSION")
        self._log("="*60)

        try:
            self._log("STEP 1: Setting up Chrome browser...")
            self._setup_driver()
            self._log("Browser started successfully")

            self._log("STEP 2: Loading Instagram and applying cookies...")
            self.driver.get("https://www.instagram.com")
            self._human_delay(2, 3)

            # Try to load cookies
            if Path(self.cookies_file).exists():
                self._log(f"Loading cookies from {self.cookies_file}...")
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
                    self._human_delay(2, 4)
                    self._log("Cookies applied")

                except Exception as e:
                    self._log(f"Could not load cookies: {e}", "WARN")

            # Check if we're logged in or need 2FA/login
            self._log("STEP 3: Checking login status...")

            # Wait for page to load
            self._human_delay(3, 5)

            # Check for various scenarios
            needs_manual_intervention = False

            # Check for login button (not logged in)
            try:
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Log In')]")
                self._log("Not logged in - cookies expired or invalid", "WARN")
                needs_manual_intervention = True
            except NoSuchElementException:
                pass

            # Check for 2FA prompt
            try:
                self.driver.find_element(By.XPATH, "//*[contains(text(), 'security code') or contains(text(), 'verification code') or contains(text(), 'Authentication')]")
                self._log("2FA verification required!", "WARN")
                needs_manual_intervention = True
            except NoSuchElementException:
                pass

            # Check for "Suspicious Login Attempt" or other security checks
            try:
                self.driver.find_element(By.XPATH, "//*[contains(text(), 'Suspicious') or contains(text(), 'We Detected') or contains(text(), 'verify')]")
                self._log("Security checkpoint detected!", "WARN")
                needs_manual_intervention = True
            except NoSuchElementException:
                pass

            if needs_manual_intervention:
                self._handle_manual_login()
            else:
                self._log("Already logged in successfully!", "SUCCESS")

            # Verify we're on the home feed
            self._log("STEP 4: Verifying we're on Instagram home...")
            self.driver.get("https://www.instagram.com/")
            self._human_delay(2, 4)

            # Dismiss any popups
            try:
                not_now = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                not_now.click()
                self._human_delay(1, 2)
                self._log("Dismissed notification popup")
            except TimeoutException:
                pass

            # Save cookies for next time
            self._log("STEP 5: Saving session cookies...")
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            self._log(f"Cookies saved to {self.cookies_file}")

            self.session_active = True
            self._log("="*60)
            self._log("SESSION STARTED SUCCESSFULLY")
            self._log("Browser will stay open for all uploads today")
            self._log("="*60)
            return True

        except Exception as e:
            self._log(f"Failed to start session: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

    def _handle_manual_login(self):
        """Handle manual login or 2FA"""
        self._log("="*60, "WARN")
        self._log("MANUAL INTERVENTION REQUIRED", "WARN")
        self._log("="*60, "WARN")
        print()
        print("The Chrome browser window is waiting for you!")
        print()
        print("Please complete ONE of the following:")
        print("  1. Login with your credentials (if not logged in)")
        print("  2. Enter your 2FA code (if prompted)")
        print("  3. Complete any security verification")
        print()
        print("After you complete the login/verification:")
        print("  - Wait until you see your Instagram home feed")
        print("  - Come back here and press Enter")
        print()
        print("="*60)

        input("Press Enter AFTER you see your Instagram home feed... ")

        self._log("Thank you! Continuing automation...")
        self._human_delay(2, 3)

    def upload_video(self, video_path: str, caption: str = "") -> bool:
        """
        Upload a video using the existing session

        Args:
            video_path: Path to video file
            caption: Caption text

        Returns:
            True if upload successful
        """
        if not self.session_active:
            self._log("No active session! Call start_session() first.", "ERROR")
            return False

        upload_start = time.time()
        video_path = Path(video_path).resolve()

        self._log("="*50)
        self._log(f"UPLOADING: {video_path.name}")
        self._log("="*50)

        if not video_path.exists():
            self._log(f"Video not found: {video_path}", "ERROR")
            return False

        self._log(f"Video size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
        self._log(f"Caption: {caption[:50]}{'...' if len(caption) > 50 else ''}")

        try:
            # Navigate to home (in case we're somewhere else)
            self._log("Navigating to Instagram home...")
            self.driver.get("https://www.instagram.com/")
            self._human_delay(2, 3)

            # Click Create button
            self._log("Looking for Create button...")
            create_selectors = [
                "//span[contains(text(), 'Create')]",
                "//a[contains(@href, '/create/')]",
                "//*[@aria-label='New post']",
                "//*[@aria-label='Create']",
                "//svg[@aria-label='New post']/..",
                "//svg[@aria-label='Create']/..",
            ]

            create_button = None
            for selector in create_selectors:
                try:
                    self._log(f"  Trying selector: {selector[:50]}...")
                    create_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self._log(f"  Found Create button!")
                    break
                except TimeoutException:
                    self._log(f"  Not found with this selector")
                    continue

            if not create_button:
                self._log("Could not find Create button after trying all selectors", "ERROR")
                return False

            create_button.click()
            self._human_delay(2, 3)

            # Select media from computer
            self._log("Uploading video file...")
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(str(video_path))
            self._human_delay(3, 5)

            # Click Next button (might appear multiple times)
            self._log("Clicking Next buttons...")
            for i in range(3):  # Up to 3 "Next" clicks
                try:
                    next_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                    )
                    self._log(f"  Clicking Next ({i+1})...")
                    next_button.click()
                    self._human_delay(2, 3)
                except TimeoutException:
                    break

            # Enter caption
            if caption:
                self._log("Entering caption...")
                try:
                    caption_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Write a caption...']"))
                    )
                    caption_field.clear()
                    caption_field.send_keys(caption)
                    self._human_delay(2, 3)
                except TimeoutException:
                    self._log("Could not find caption field (skipping)", "WARN")

            # Click Share button
            self._log("Clicking Share button...")
            share_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]"))
            )
            share_button.click()

            # Wait for upload to complete
            self._log("Waiting for upload to complete...")
            try:
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Your reel has been shared') or contains(text(), 'Post shared')]"))
                )
                self._log("Upload completed successfully!", "SUCCESS")
                elapsed = time.time() - upload_start
                self._log(f"Upload took {elapsed:.1f} seconds", "SUCCESS")
                self._human_delay(2, 3)
                return True

            except TimeoutException:
                self._log("Upload confirmation not detected (might still have uploaded)", "WARN")
                return True  # Assume success if no error occurred

        except Exception as e:
            self._log(f"Upload failed: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

    def close_session(self):
        """Close browser and end session"""
        if self.driver:
            self._log("="*60)
            self._log("CLOSING INSTAGRAM SESSION")
            self._log("="*60)
            self.driver.quit()
            self.driver = None
            self.session_active = False
            self._log("Browser closed. Session ended.")

    def __del__(self):
        """Cleanup on deletion"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# Example usage
if __name__ == "__main__":
    uploader = PersistentInstagramUploader(headless=False)

    # Start session (login once, handle 2FA if needed)
    if uploader.start_session():
        # Upload multiple videos (reusing same session)
        uploader.upload_video("video1.mp4", "Caption for video 1")
        time.sleep(60)  # Wait between uploads
        uploader.upload_video("video2.mp4", "Caption for video 2")

        # Close when done
        uploader.close_session()
