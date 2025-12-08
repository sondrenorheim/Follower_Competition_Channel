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

        print(f"\nSUCCESS: Cookies saved to {self.cookies_file}")
        print("You can now upload videos without logging in each time!")

        self.driver.quit()

    def _load_cookies(self) -> bool:
        """
        Load saved cookies

        Returns:
            True if cookies loaded successfully
        """
        if not Path(self.cookies_file).exists():
            print(f"ERROR: Cookie file not found: {self.cookies_file}")
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
                print("WARNING: Cookies expired or invalid. Please run --save-cookies again.")
                return False
            except NoSuchElementException:
                # Good! No login button means we're logged in
                print("SUCCESS: Logged in successfully using saved cookies")
                return True

        except Exception as e:
            print(f"ERROR: Error loading cookies: {e}")
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
            print(f"ERROR: Video not found: {video_path}")
            return False

        print(f"Uploading: {video_path.name}")
        print(f"Caption: {caption[:50]}..." if len(caption) > 50 else f"Caption: {caption}")

        try:
            self._setup_driver()

            if not self._load_cookies():
                return False

            # Navigate to create page
            print("Opening create page...")
            self.driver.get("https://www.instagram.com/")
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

            # Click the Create/New Post button
            print("Looking for Create button...")
            try:
                # Try multiple selectors for the create button
                create_selectors = [
                    "//span[contains(text(), 'Create')]",
                    "//a[contains(@href, '/create/')]",
                    "//*[@aria-label='New post']",
                    "//*[@aria-label='Create']",
                    "//svg[@aria-label='New post']/..",
                    "//svg[@aria-label='Create']/.."
                ]

                create_button = None
                for selector in create_selectors:
                    try:
                        create_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print(f"Found create button with selector: {selector}")
                        break
                    except TimeoutException:
                        continue

                if not create_button:
                    print("ERROR: Could not find Create button")
                    return False

                create_button.click()
                self._human_delay(2, 4)

                # After clicking Create, there might be a menu. Look for "Post" or "Reel" option
                print("Checking for Post/Reel menu...")
                try:
                    post_selectors = [
                        "//span[text()='Post']",
                        "//div[text()='Post']",
                        "//*[contains(text(), 'Post') and not(contains(text(), 'New'))]"
                    ]

                    post_option = None
                    for selector in post_selectors:
                        try:
                            post_option = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            print(f"Found Post option, clicking...")
                            post_option.click()
                            self._human_delay(1, 2)
                            break
                        except TimeoutException:
                            continue
                except Exception as e:
                    print(f"No Post menu found (this is okay): {e}")

            except Exception as e:
                print(f"ERROR: Failed to click Create button: {e}")
                return False

            # Find file input and upload video
            print("Selecting video file...")

            # Try multiple approaches to find the file input
            file_input = None

            # Approach 1: Direct file input
            try:
                file_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )
                print("Found file input directly")
            except TimeoutException:
                print("File input not immediately visible, looking for 'Select from computer' button...")

                # Approach 2: Click "Select from computer" button first
                try:
                    select_buttons = [
                        "//button[contains(text(), 'Select from computer')]",
                        "//button[contains(text(), 'Select from Computer')]",
                        "//*[contains(text(), 'computer')]",
                        "//*[contains(text(), 'Computer')]"
                    ]

                    for selector in select_buttons:
                        try:
                            select_btn = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            print(f"Found select button, clicking...")
                            select_btn.click()
                            self._human_delay(1, 2)
                            break
                        except TimeoutException:
                            continue

                    # Now try to find file input again
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                    )
                    print("Found file input after clicking select button")
                except TimeoutException:
                    pass

            if not file_input:
                print("ERROR: Could not find file upload input after all attempts")
                return False

            # Upload the file
            print(f"Uploading file: {video_path.name}")
            file_input.send_keys(str(video_path))
            self._human_delay(3, 5)

            # Wait for video to load
            print("Waiting for video to load...")
            time.sleep(5)

            # Handle "Video posts are now shared as reels" popup
            print("Checking for Reels info popup...")
            try:
                ok_button_selectors = [
                    "//button[text()='OK']",
                    "//button[contains(text(), 'OK')]",
                    "//*[@role='button' and text()='OK']"
                ]

                for selector in ok_button_selectors:
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print("Found OK button on Reels popup, clicking...")
                        ok_button.click()
                        self._human_delay(1, 2)
                        break
                    except TimeoutException:
                        continue
            except Exception as e:
                print(f"No Reels popup found (this is okay): {e}")

            # Check for crop/aspect ratio options and select 9:16 (vertical)
            print("Looking for aspect ratio options...")
            try:
                # Look for aspect ratio button or crop button
                aspect_selectors = [
                    "//button[@aria-label='Select crop']",
                    "//*[contains(@aria-label, 'crop')]",
                    "//*[contains(@aria-label, 'Crop')]",
                    "//button[contains(@aria-label, 'aspect')]"
                ]

                aspect_button = None
                for selector in aspect_selectors:
                    try:
                        aspect_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print(f"Found aspect ratio button, clicking...")
                        aspect_button.click()
                        self._human_delay(1, 2)
                        break
                    except TimeoutException:
                        continue

                # If we opened a menu, look for 9:16 or vertical option
                if aspect_button:
                    vertical_selectors = [
                        "//*[contains(text(), '9:16')]",
                        "//*[contains(text(), 'Portrait')]",
                        "//*[contains(text(), 'Vertical')]",
                        "//button[@aria-label='Portrait']"
                    ]

                    for selector in vertical_selectors:
                        try:
                            vertical_option = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            print(f"Found vertical/9:16 option, clicking...")
                            vertical_option.click()
                            self._human_delay(1, 2)
                            break
                        except TimeoutException:
                            continue

            except Exception as e:
                print(f"Aspect ratio selection: {e}")
                print("Note: Video may use default aspect ratio. Ensure your videos are already 9:16 format.")

            # Click "Next" button to proceed (there might be multiple Next buttons)
            print("Clicking Next...")
            next_selectors = [
                "//button[contains(text(), 'Next')]",
                "//button[text()='Next']",
                "//div[contains(text(), 'Next')]",
                "//*[@role='button' and contains(text(), 'Next')]"
            ]

            # First Next button
            try:
                next_button = None
                for selector in next_selectors:
                    try:
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        break
                    except TimeoutException:
                        continue

                if next_button:
                    next_button.click()
                    self._human_delay(2, 3)
                else:
                    print("WARNING: First Next button not found, trying to continue...")
            except Exception as e:
                print(f"WARNING: Error clicking first Next: {e}")

            # Click Next again if there's a second step
            try:
                next_button = None
                for selector in next_selectors:
                    try:
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        break
                    except TimeoutException:
                        continue

                if next_button:
                    next_button.click()
                    self._human_delay(2, 3)
            except Exception:
                pass  # No second Next button

            # Try to select a better cover/thumbnail from middle of video
            print("Looking for cover/thumbnail options...")
            try:
                # Look for "Add cover" or "Edit cover" button
                cover_selectors = [
                    "//button[contains(text(), 'Add cover')]",
                    "//button[contains(text(), 'Edit cover')]",
                    "//div[contains(text(), 'Add cover')]",
                    "//*[@aria-label='Add cover']",
                    "//*[@aria-label='Edit cover']"
                ]

                cover_button = None
                for selector in cover_selectors:
                    try:
                        cover_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print(f"Found cover button, clicking...")
                        cover_button.click()
                        self._human_delay(2, 3)

                        # Try to find and drag the thumbnail slider to the middle
                        print("Looking for thumbnail slider...")
                        try:
                            from selenium.webdriver.common.action_chains import ActionChains

                            # Look for slider/range input
                            slider_selectors = [
                                'input[type="range"]',
                                'input[role="slider"]',
                                '//*[@role="slider"]'
                            ]

                            slider = None
                            for slider_sel in slider_selectors:
                                try:
                                    if slider_sel.startswith('//'):
                                        slider = self.driver.find_element(By.XPATH, slider_sel)
                                    else:
                                        slider = self.driver.find_element(By.CSS_SELECTOR, slider_sel)
                                    print(f"Found slider!")
                                    break
                                except NoSuchElementException:
                                    continue

                            if slider:
                                # Get slider dimensions
                                slider_width = slider.size['width']

                                # Click/drag to middle of slider (50% position)
                                # Move to center of slider element
                                actions = ActionChains(self.driver)
                                actions.move_to_element(slider).perform()
                                self._human_delay(0.5, 1)

                                # Click at the center of the slider
                                actions.click().perform()
                                print("Selected middle frame of video for thumbnail")
                                self._human_delay(1, 2)
                            else:
                                print("No slider found, using default frame")

                        except Exception as slider_error:
                            print(f"Could not adjust slider: {slider_error}")

                        # Close cover selector if there's a done/save button
                        try:
                            done_selectors = [
                                "//button[contains(text(), 'Done')]",
                                "//div[contains(text(), 'Done') and @role='button']",
                                "//*[@role='button' and text()='Done']"
                            ]

                            for done_sel in done_selectors:
                                try:
                                    done_button = WebDriverWait(self.driver, 2).until(
                                        EC.element_to_be_clickable((By.XPATH, done_sel))
                                    )
                                    done_button.click()
                                    print("Closed cover selector")
                                    self._human_delay(1, 2)
                                    break
                                except TimeoutException:
                                    continue
                        except Exception:
                            print("Cover selector closed automatically")

                        break
                    except TimeoutException:
                        continue

                if not cover_button:
                    print("No cover selection option found - using Instagram's default thumbnail")

            except Exception as e:
                print(f"Cover selection: Using default thumbnail - {e}")

            # Add caption
            if caption:
                print("Adding caption...")
                caption_selectors = [
                    'textarea[aria-label*="caption"]',
                    'textarea[aria-label*="Caption"]',
                    'textarea[placeholder*="caption"]',
                    'textarea[placeholder*="Write a caption"]',
                    'div[contenteditable="true"][aria-label*="caption"]'
                ]

                try:
                    caption_field = None
                    for selector in caption_selectors:
                        try:
                            caption_field = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            print(f"Found caption field with selector: {selector}")
                            break
                        except TimeoutException:
                            continue

                    if caption_field:
                        caption_field.click()
                        self._human_delay(0.5, 1)
                        self._human_type(caption_field, caption)
                        self._human_delay(1, 2)
                    else:
                        print("WARNING: Could not find caption field")
                except Exception as e:
                    print(f"WARNING: Error adding caption: {e}")

            # Click "Share" button
            print("Sharing reel...")
            share_selectors = [
                "//button[contains(text(), 'Share')]",
                "//button[text()='Share']",
                "//div[contains(text(), 'Share') and @role='button']",
                "//*[@role='button' and contains(text(), 'Share')]"
            ]

            try:
                share_button = None
                for selector in share_selectors:
                    try:
                        share_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        print(f"Found Share button with selector: {selector}")
                        break
                    except TimeoutException:
                        continue

                if not share_button:
                    print("ERROR: Could not find Share button")
                    return False

                share_button.click()

                # Wait for upload to complete
                print("Uploading... (this may take a while)")
                print("Instagram is processing your video. Waiting 3+ minutes to ensure completion...")

                # Wait a solid 3 minutes for Instagram to process and upload
                # Instagram can be slow, especially with video processing
                print("Initial wait: 180 seconds (3 minutes) for Instagram to process...")
                for i in range(18):  # 18 x 10 seconds = 180 seconds
                    time.sleep(10)
                    elapsed = (i + 1) * 10
                    remaining = 180 - elapsed
                    if remaining > 0:
                        print(f"  Waiting... {elapsed}s elapsed, {remaining}s remaining")
                    else:
                        print(f"  Waited {elapsed}s total")

                # Check if we see "Post shared" or "Reel shared" message
                print("Checking for confirmation message...")
                success_selectors = [
                    "//*[contains(text(), 'shared') or contains(text(), 'Shared')]",
                    "//*[contains(text(), 'Your reel has been shared')]",
                    "//*[contains(text(), 'Post shared')]",
                    "//*[contains(text(), 'Reel shared')]"
                ]

                shared_found = False
                for selector in success_selectors:
                    try:
                        # Short wait since we already waited 3 minutes
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        print("SUCCESS: Found confirmation message!")
                        shared_found = True
                        break
                    except TimeoutException:
                        continue

                if shared_found:
                    print("Waiting additional 30 seconds to ensure upload is fully finalized...")
                    time.sleep(30)
                    print("Upload complete! Video should now be visible on your profile.")
                    return True
                else:
                    # Check for error messages
                    print("WARNING: Didn't see confirmation message")
                    print("Checking for errors...")
                    try:
                        error_msg = self.driver.find_element(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error') or contains(text(), 'failed')]")
                        print(f"ERROR: Found error message: {error_msg.text}")
                        return False
                    except NoSuchElementException:
                        print("No error found. Waiting extra 60 seconds then assuming success...")
                        time.sleep(60)
                        print("Upload likely succeeded (no errors detected after 4 minutes total)")
                        return True

            except TimeoutException:
                print("ERROR: Could not find Share button")
                return False

        except Exception as e:
            print(f"ERROR: Upload failed: {e}")
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
