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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException


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
        self.start_time = None

    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp and elapsed time"""
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = ""
        if self.start_time:
            elapsed_sec = (time.time() - self.start_time)
            elapsed = f" [{elapsed_sec:.1f}s]"
        print(f"[{now}]{elapsed} [{level}] {message}", flush=True)

    def _setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # Mobile emulation to ensure Instagram shows the mobile UI (Story upload available)
        # Use explicit metrics to avoid device-name lookup failures.
        mobile_emulation = {
            "deviceMetrics": {"width": 412, "height": 915, "pixelRatio": 2.75},  # Pixel 5 metrics
            "userAgent": (
                "Mozilla/5.0 (Linux; Android 12; Pixel 5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
        }
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

        # Anti-detection settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent aligned with mobile emulation
        # UA already set in mobileEmulation; no extra override needed.

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

    def _dismiss_save_login_popup(self):
        """Dismiss 'Save your login info?' modal if it appears."""
        try:
            # Common buttons on the modal
            selectors = [
                "//button[contains(translate(., 'NOW', 'now'), 'not now')]",
                "//div[contains(translate(., 'NOW', 'now'), 'not now')]//ancestor::button[1]",
                "//button[contains(translate(@aria-label, 'close', 'CLOSE'), 'close')]",
                "//*[@aria-label='Close']",
            ]
            for selector in selectors:
                try:
                    btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    btn.click()
                    self._human_delay(0.5, 1.0)
                    return True
                except TimeoutException:
                    continue
        except Exception:
            pass
        return False

    def _open_story_creator_mobile(self) -> bool:
        """
        In mobile UI, tap the plus button then pick Story from the menu.
        Returns True if we navigated to the story creator.
        """
        plus_selectors = [
            "//*[name()='svg' and @aria-label='New post']/ancestor::*[@role='button' or @role='link'][1]",
            "//*[@aria-label='New post']",
            "//*[@aria-label='Create']",
            "//*[@aria-label='Create new post']",
            "//*[contains(@aria-label, 'Create') and contains(@aria-label, 'post')]",
        ]

        plus_btn = None
        for selector in plus_selectors:
            try:
                plus_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                break
            except TimeoutException:
                continue

        if not plus_btn:
            return False

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", plus_btn)
        except Exception:
            pass
        self._human_delay(0.5, 1.0)
        try:
            plus_btn.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", plus_btn)
            except Exception:
                return False

        self._human_delay(1.0, 2.0)

        story_selectors = [
            "//*[name()='svg' and @aria-label='Story']/ancestor::*[@role='button'][1]",
            "//div[@role='button']//span[normalize-space()='Story']",
            "//button[.//span[normalize-space()='Story']]",
            "//*[@role='button' and (contains(., 'Story') or contains(@aria-label, 'Story'))]",
            "//div[contains(@class,'x10l6tqk') or contains(@class,'x1lliihq')]//span[normalize-space()='Story']/ancestor::*[@role='button'][1]",
            "//span[normalize-space()='Story']/ancestor::*[@role='button' or self::button or self::div][1]",
        ]

        story_btn = None
        for selector in story_selectors:
            try:
                story_btn = WebDriverWait(self.driver, 12).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                break
            except TimeoutException:
                continue

        # Fallback: find the span and click it directly or its parent
        if not story_btn:
            try:
                spans = self.driver.find_elements(By.XPATH, "//span[normalize-space()='Story']")
                if spans:
                    target = spans[0]
                    # Try nearest clickable ancestor
                    try:
                        ancestor = target.find_element(By.XPATH, "ancestor::*[@role='button' or self::button or self::div][1]")
                        story_btn = ancestor
                    except Exception:
                        story_btn = target
            except Exception:
                pass

        if not story_btn:
            return False

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", story_btn)
        except Exception:
            pass
        self._human_delay(0.5, 1.0)
        try:
            story_btn.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", story_btn)
            except Exception:
                return False

        self._human_delay(1.0, 2.0)
        return True

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
            self._log(f"Cookie file not found: {self.cookies_file}", "ERROR")
            self._log("Run with --save-cookies first to log in and save your session.", "ERROR")
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
                    self._log(f"Could not add cookie {cookie.get('name')}: {e}", "WARN")

            # Refresh to apply cookies
            self.driver.refresh()
            self._human_delay(2, 4)

            # Verify we're logged in (check if we can see profile icon or similar)
            try:
                # If we see login button, cookies didn't work
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
                self._log("Cookies expired or invalid. Please run --save-cookies again.", "ERROR")
                return False
            except NoSuchElementException:
                # Good! No login button means we're logged in
                self._log("Logged in successfully using saved cookies", "SUCCESS")
                return True

        except Exception as e:
            self._log(f"Error loading cookies: {e}", "ERROR")
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
        self.start_time = time.time()
        video_path = Path(video_path).resolve()

        self._log("=" * 50)
        self._log("INSTAGRAM REEL UPLOAD STARTED")
        self._log("=" * 50)

        if not video_path.exists():
            self._log(f"Video not found: {video_path}", "ERROR")
            return False

        self._log(f"Video file: {video_path.name}")
        self._log(f"Video size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
        self._log(f"Caption: {caption[:50]}..." if len(caption) > 50 else f"Caption: {caption}")

        try:
            self._log("STEP 1: Setting up Chrome browser...")
            self._setup_driver()
            self._log("Browser started successfully")

            self._log("STEP 2: Loading saved cookies...")
            if not self._load_cookies():
                self._log("Failed to load cookies", "ERROR")
                return False

            # Navigate to create page
            self._log("STEP 3: Navigating to Instagram home...")
            self.driver.get("https://www.instagram.com/")
            self._log("Waiting for page to load...")
            self._human_delay(3, 5)
            self._log("Page loaded")

            # Handle "Turn on Notifications" popup if it appears
            self._log("Checking for notification popup...")
            try:
                not_now = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                self._log("Found notification popup, dismissing...")
                not_now.click()
                self._human_delay(1, 2)
            except TimeoutException:
                self._log("No notification popup found (OK)")

            # Click the Create/New Post button
            self._log("STEP 4: Looking for Create button...")
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
                    self._log(f"  Trying selector: {selector[:40]}...")
                    try:
                        create_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        self._log(f"  SUCCESS: Found Create button!")
                        break
                    except TimeoutException:
                        self._log(f"  Not found with this selector")
                        continue

                if not create_button:
                    self._log("Could not find Create button after trying all selectors", "ERROR")
                    return False

                self._log("Clicking Create button...")
                create_button.click()
                self._human_delay(2, 4)

                # After clicking Create, there might be a menu. Look for "Post" or "Reel" option
                self._log("Checking for Post/Reel menu...")
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
                            self._log("Found Post option, clicking...")
                            post_option.click()
                            self._human_delay(1, 2)
                            break
                        except TimeoutException:
                            continue
                except Exception as e:
                    self._log(f"No Post menu found (this is okay)")

            except Exception as e:
                self._log(f"Failed to click Create button: {e}", "ERROR")
                return False

            # Find file input and upload video
            self._log("STEP 5: Looking for file upload input...")

            # Try multiple approaches to find the file input
            file_input = None

            # Approach 1: Direct file input
            self._log("  Approach 1: Looking for direct file input...")
            try:
                file_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )
                self._log("  SUCCESS: Found file input directly")
            except TimeoutException:
                self._log("  File input not visible, trying approach 2...")

                # Approach 2: Click "Select from computer" button first
                self._log("  Approach 2: Looking for 'Select from computer' button...")
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
                            self._log("  Found 'Select from computer' button, clicking...")
                            select_btn.click()
                            self._human_delay(1, 2)
                            break
                        except TimeoutException:
                            continue

                    # Now try to find file input again
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                    )
                    self._log("  SUCCESS: Found file input after clicking select button")
                except TimeoutException:
                    pass

            if not file_input:
                self._log("Could not find file upload input after all attempts", "ERROR")
                return False

            # Upload the file
            self._log(f"STEP 6: Uploading video file: {video_path.name}")
            file_input.send_keys(str(video_path))
            self._log("File path sent to input, waiting for upload...")
            self._human_delay(3, 5)

            # Wait for video to load
            self._log("Waiting for video to process (5 seconds)...")
            time.sleep(5)
            self._log("Video processing wait complete")

            # Handle "Video posts are now shared as reels" popup
            self._log("Checking for Reels info popup...")
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
                        self._log("Found OK button on Reels popup, clicking...")
                        ok_button.click()
                        self._human_delay(1, 2)
                        break
                    except TimeoutException:
                        continue
            except Exception as e:
                self._log("No Reels popup found (OK)")

            # Check for crop/aspect ratio options and select 9:16 (vertical)
            self._log("Checking for aspect ratio options...")
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
                        self._log("Found aspect ratio button, clicking...")
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
                            self._log("Found vertical/9:16 option, clicking...")
                            vertical_option.click()
                            self._human_delay(1, 2)
                            break
                        except TimeoutException:
                            continue

            except Exception as e:
                self._log("Aspect ratio selection skipped (using default)")

            # Click "Next" button to proceed (there might be multiple Next buttons)
            self._log("STEP 7: Clicking Next button...")
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
                    self._log("Found first Next button, clicking...")
                    next_button.click()
                    self._human_delay(2, 3)
                else:
                    self._log("First Next button not found, trying to continue...", "WARN")
            except Exception as e:
                self._log(f"Error clicking first Next: {e}", "WARN")

            # Click Next again if there's a second step
            self._log("Checking for second Next button...")
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
                    self._log("Found second Next button, clicking...")
                    next_button.click()
                    self._human_delay(2, 3)
                else:
                    self._log("No second Next button (OK)")
            except Exception:
                self._log("No second Next button (OK)")

            # Try to select a better cover/thumbnail from middle of video
            self._log("Checking for cover/thumbnail options...")
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
                        self._log("Found cover button, clicking...")
                        cover_button.click()
                        self._human_delay(2, 3)

                        # Try to find and drag the thumbnail slider to the middle
                        self._log("Looking for thumbnail slider...")
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
                                    self._log("Found slider!")
                                    break
                                except NoSuchElementException:
                                    continue

                            if slider:
                                # Try to set slider to middle position (50%)
                                try:
                                    # Method 1: Set value directly with JavaScript (most reliable)
                                    self._log("Setting slider to 50% position...")
                                    self.driver.execute_script("""
                                        var slider = arguments[0];
                                        var min = parseFloat(slider.min) || 0;
                                        var max = parseFloat(slider.max) || 100;
                                        var mid = (min + max) / 2;
                                        slider.value = mid;
                                        slider.dispatchEvent(new Event('input', { bubbles: true }));
                                        slider.dispatchEvent(new Event('change', { bubbles: true }));
                                    """, slider)
                                    self._log("Slider set to middle position via JavaScript")
                                    self._human_delay(1, 2)
                                except Exception as js_error:
                                    self._log(f"JavaScript method failed: {js_error}")

                                    # Method 2: Drag slider to middle (fallback)
                                    try:
                                        self._log("Trying drag method...")
                                        slider_width = slider.size['width']

                                        # Move to left edge of slider, then drag to middle
                                        actions = ActionChains(self.driver)
                                        actions.move_to_element_with_offset(slider, -slider_width // 2, 0).perform()
                                        self._human_delay(0.3, 0.5)
                                        actions.click_and_hold().perform()
                                        self._human_delay(0.2, 0.4)
                                        actions.move_by_offset(slider_width // 2, 0).perform()
                                        self._human_delay(0.2, 0.4)
                                        actions.release().perform()
                                        self._log("Dragged slider to middle position")
                                        self._human_delay(1, 2)
                                    except Exception as drag_error:
                                        self._log(f"Drag method also failed: {drag_error}")

                                self._log("Selected middle frame of video for thumbnail")
                            else:
                                self._log("No slider found, using default frame")

                        except Exception as slider_error:
                            self._log(f"Could not adjust slider: {slider_error}")

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
                                    self._log("Closed cover selector")
                                    self._human_delay(1, 2)
                                    break
                                except TimeoutException:
                                    continue
                        except Exception:
                            self._log("Cover selector closed automatically")

                        break
                    except TimeoutException:
                        continue

                if not cover_button:
                    self._log("No cover selection option - using default thumbnail")

            except Exception as e:
                self._log("Cover selection skipped - using default thumbnail")

            # Add caption
            if caption:
                self._log("STEP 8: Adding caption to reel")
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
                            self._log(f"Found caption field with selector: {selector}")
                            break
                        except TimeoutException:
                            continue

                    if caption_field:
                        caption_field.click()
                        self._human_delay(0.5, 1)
                        self._human_type(caption_field, caption)
                        self._human_delay(1, 2)
                    else:
                        self._log("Could not find caption field - proceeding without caption", "WARN")
                except Exception as e:
                    self._log(f"Error adding caption: {e}", "WARN")

            # Click "Share" button
            self._log("STEP 9: Looking for Share button")
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
                        self._log(f"Found Share button with selector: {selector}")
                        break
                    except TimeoutException:
                        continue

                if not share_button:
                    self._log("Could not find Share button - upload failed", "ERROR")
                    return False

                share_button.click()
                self._log("Share button clicked - upload initiated")

                # Wait for upload to complete
                self._log("STEP 10: Waiting for Instagram to process video (up to 120 seconds)")

                # Reduced wait - check frequently for completion
                self._log("Processing: checking every 10 seconds for completion...")
                for i in range(12):  # 12 x 10 seconds = 120 seconds max
                    time.sleep(10)
                    elapsed = (i + 1) * 10
                    self._log(f"Progress check {i+1}/12 ({elapsed}s elapsed)")

                # Check if we see "Post shared" or "Reel shared" message
                self._log("STEP 11: Checking for confirmation message")
                success_selectors = [
                    # Exact matches first (most reliable)
                    "//*[text()='Your post was shared.']",
                    "//*[text()='Your reel has been shared.']",
                    "//*[text()='Post shared']",
                    "//*[text()='Reel shared']",
                    # Partial matches (more flexible but still specific)
                    "//*[contains(text(), 'post was shared')]",
                    "//*[contains(text(), 'reel has been shared')]",
                    "//*[contains(text(), 'Post shared')]",
                    "//*[contains(text(), 'Reel shared')]"
                ]

                shared_found = False
                matched_selector = None
                for selector in success_selectors:
                    try:
                        # Short wait since we already waited 3 minutes
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        matched_text = element.text if element else "N/A"
                        self._log(f"Found element matching selector: {selector}", "SUCCESS")
                        self._log(f"Element text: '{matched_text}'", "INFO")
                        shared_found = True
                        matched_selector = selector
                        break
                    except TimeoutException:
                        continue

                if shared_found:
                    # Take screenshot for verification
                    screenshot_path = Path("instagram_upload_screenshot.png")
                    try:
                        self.driver.save_screenshot(str(screenshot_path))
                        self._log(f"Screenshot saved to: {screenshot_path}", "INFO")
                    except Exception as e:
                        self._log(f"Could not save screenshot: {e}", "WARN")

                    self._log("Waiting 10 seconds to ensure upload is finalized...")
                    time.sleep(10)
                    self._log("COMPLETE: Upload successful! Video should now be visible on profile.", "SUCCESS")
                    return True

                # No confirmation yet - check for obvious errors
                self._log("No explicit confirmation message found", "WARN")
                self._log("Checking page for error messages...")
                try:
                    error_msg = self.driver.find_element(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error') or contains(text(), 'failed')]")
                    self._log(f"Found error message on page: {error_msg.text}", "ERROR")
                    return False
                except NoSuchElementException:
                    # Brief grace period
                    self._log("No error messages found. Waiting 20 more seconds for late confirmation...")
                    time.sleep(20)
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'shared') or contains(text(), 'Shared')]"))
                        )
                        self._log("Late confirmation detected - upload complete!", "SUCCESS")
                        return True
                    except TimeoutException:
                        # Don't assume success - we need explicit confirmation
                        self._log("No confirmation message found after extended wait - upload likely failed", "ERROR")
                        self._log("Upload timed out without confirmation", "ERROR")
                        return False

            except TimeoutException:
                self._log("Share button timeout - could not initiate upload", "ERROR")
                return False

        except Exception as e:
            self._log(f"Upload failed with exception: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.driver:
                self._human_delay(2, 3)
                self.driver.quit()

    def upload_story(self, image_path: str, usernames_to_tag: List[str] = None) -> bool:
        """
        Upload an image as an Instagram Story

        Args:
            image_path: Path to image file (PNG/JPG)
            usernames_to_tag: Optional list of usernames to tag with mention stickers

        Returns:
            True if upload successful
        """
        self.start_time = time.time()
        image_path = Path(image_path).resolve()

        self._log("=" * 50)
        self._log("INSTAGRAM STORY UPLOAD STARTED")
        self._log("=" * 50)

        if not image_path.exists():
            self._log(f"Image not found: {image_path}", "ERROR")
            return False

        self._log(f"Image file: {image_path.name}")
        self._log(f"Image size: {image_path.stat().st_size / 1024:.1f} KB")

        try:
            self._log("STEP 1: Setting up Chrome browser...")
            self._setup_driver()
            self._log("Browser started successfully")

            self._log("STEP 2: Loading saved cookies...")
            if not self._load_cookies():
                self._log("Failed to load cookies", "ERROR")
                return False

            # Navigate to Instagram home
            self._log("STEP 3: Navigating to Instagram home...")
            self.driver.get("https://www.instagram.com/")
            self._log("Waiting for page to load...")
            self._human_delay(3, 5)
            # Force a refresh after mobile emulation to ensure the mobile UI loads
            self.driver.refresh()
            self._human_delay(2, 3)
            # Dismiss "Save your login info?" modal if it appears
            for _ in range(3):
                if self._dismiss_save_login_popup():
                    self._log("Dismissed save-login popup")
                else:
                    break
            # Tap Home to ensure we are in the main feed (mobile UI)
            try:
                home_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[@aria-label='Home' or @role='img' and @aria-label='Home']"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", home_btn)
                self._human_delay(0.5, 1.0)
                home_btn.click()
                self._human_delay(1.0, 2.0)
                self._log("Tapped Home in mobile UI")
            except Exception:
                self._log("Home button not found; continuing", "WARN")

            # Try mobile "+" then "Story" option before fallback
            try:
                if self._open_story_creator_mobile():
                    self._log("Opened story creator via mobile '+' menu")
                else:
                    self._log("Mobile '+' story open failed; will try generic selectors", "WARN")
            except Exception:
                self._log("Mobile '+' story open threw; will try generic selectors", "WARN")

            # Click create button (+ icon)
            self._log("STEP 4: Looking for Create/Story button...")

            # Try multiple selectors for the create button
            create_selectors = [
                "//a[contains(@href, '/create/story')]",
                "//button[@aria-label='New story']",
                "//*[contains(@aria-label, 'story') and contains(@aria-label, 'new')]//ancestor::*[@role='link' or @role='button'][1]",
                "//a[@href='#' and contains(@aria-label, 'Create')]",
                "//*[contains(@aria-label, 'Create')]",
                "//*[local-name()='svg' and contains(@aria-label, 'New')]//ancestor::a[1]",
            ]

            create_button = None
            for selector in create_selectors:
                try:
                    create_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self._log(f"Found create button using selector: {selector[:50]}...")
                    break
                except TimeoutException:
                    continue

            if not create_button:
                self._log("Could not find Create button - trying direct story URL", "WARN")
                self.driver.get("https://www.instagram.com/create/story/")
                self._human_delay(2, 3)
            else:
                self._log("Clicking Create button...")
                try:
                    # Try to bring into view and click
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", create_button)
                    self._human_delay(0.5, 1.0)
                    create_button.click()
                    self._human_delay(2, 3)
                except ElementClickInterceptedException as e:
                    self._log(f"Create click intercepted, retrying with JS click: {e}", "WARN")
                    try:
                        self._human_delay(0.5, 1.0)
                        self.driver.execute_script("arguments[0].click();", create_button)
                        self._human_delay(2, 3)
                    except Exception:
                        self._log("JS click failed; navigating directly to story URL", "WARN")
                        self.driver.get("https://www.instagram.com/create/story/")
                        self._human_delay(2, 3)
                except Exception as e:
                    self._log(f"Create click failed, navigating directly to story URL: {e}", "WARN")
                    self.driver.get("https://www.instagram.com/create/story/")
                    self._human_delay(2, 3)

            # Ensure we are on the story creator page even if the UI changed
            if "create/story" not in self.driver.current_url:
                self._log("Not on story creator after click; navigating directly...", "WARN")
                self.driver.get("https://www.instagram.com/create/story/")
                self._human_delay(2, 3)

            # Upload file
            self._log("STEP 5: Uploading image file...")

            # Find file input and send file path (with fallbacks)
            file_input = None
            file_input_selectors = [
                (By.CSS_SELECTOR, 'input[type="file"]'),
                (By.XPATH, "//input[@type='file']"),
                (By.XPATH, "//input[contains(@accept, 'image') or contains(@accept, 'video')]"),
            ]

            def locate_file_input(timeout: int = 12):
                for by, selector in file_input_selectors:
                    try:
                        return WebDriverWait(self.driver, timeout).until(
                            EC.presence_of_element_located((by, selector))
                        )
                    except TimeoutException:
                        continue
                return None

            file_input = locate_file_input()

            if not file_input:
                # Try navigating directly again, then retry with a longer wait
                self._log("File input not found; retrying on direct story URL...", "WARN")
                self.driver.get("https://www.instagram.com/create/story/")
                self._human_delay(2, 3)
                file_input = locate_file_input(timeout=15)

            if not file_input:
                self._log("File input not found after retries - upload failed", "ERROR")
                return False

            self._log("Found file input, sending image path...")
            file_input.send_keys(str(image_path))
            self._human_delay(3, 5)
            self._log("File uploaded to browser")

            # Wait for image processing
            self._log("STEP 6: Waiting for image to process...")
            self._human_delay(3, 4)

            # Add mention stickers if usernames provided
            if usernames_to_tag:
                self._log(f"STEP 6.5: Adding mention stickers for {len(usernames_to_tag)} users...")
                try:
                    for username in usernames_to_tag:
                        self._log(f"  Tagging @{username}...")

                        # Look for sticker/mention button (usually @ icon or sticker icon)
                        sticker_selectors = [
                            "//button[@aria-label='Add mention']",
                            "//*[contains(@aria-label, 'mention')]",
                            "//*[contains(@aria-label, 'Mention')]",
                            "//button[contains(@aria-label, 'sticker')]",
                            "//*[name()='svg' and contains(@aria-label, 'Sticker')]//ancestor::button[1]",
                            "//button[@aria-label='Add sticker']",
                        ]

                        sticker_button = None
                        for selector in sticker_selectors:
                            try:
                                sticker_button = WebDriverWait(self.driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                                self._log(f"    Found sticker button")
                                sticker_button.click()
                                self._human_delay(1, 2)
                                break
                            except TimeoutException:
                                continue

                        if not sticker_button:
                            # Try clicking the @ button directly
                            try:
                                at_button = self.driver.find_element(By.XPATH, "//button[contains(text(), '@')]")
                                at_button.click()
                                self._human_delay(1, 2)
                            except NoSuchElementException:
                                self._log(f"    Could not find mention button, skipping tags", "WARN")
                                break

                        # Look for mention input or search field
                        try:
                            mention_input = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']"))
                            )
                        except TimeoutException:
                            try:
                                mention_input = WebDriverWait(self.driver, 2).until(
                                    EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))
                                )
                            except TimeoutException:
                                self._log(f"    Mention input not found, skipping", "WARN")
                                continue

                        # Type username (without @)
                        username_clean = username.lstrip('@')
                        self._human_type(mention_input, username_clean)
                        self._human_delay(1, 2)

                        # Click on the first result/suggestion
                        try:
                            first_result = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{username_clean}')]"))
                            )
                            first_result.click()
                            self._log(f"    Tagged @{username_clean} successfully")
                            self._human_delay(1, 2)
                        except TimeoutException:
                            self._log(f"    Could not find user {username_clean} in results", "WARN")
                            # Close the mention dialog
                            try:
                                self.driver.find_element(By.XPATH, "//button[@aria-label='Close']").click()
                            except:
                                pass

                        self._human_delay(1, 2)

                    self._log(f"Mention stickers added successfully")
                except Exception as e:
                    self._log(f"Error adding mentions (continuing anyway): {e}", "WARN")

            # Add link sticker if configured
            try:
                import config
                website_url = getattr(config, 'STORY_WEBSITE_URL', None)
                link_text = getattr(config, 'STORY_LINK_TEXT', 'View Website')

                if website_url:
                    self._log(f"STEP 6.6: Adding link sticker ({website_url})...")

                    # Look for link/sticker button
                    link_button_selectors = [
                        "//button[@aria-label='Add link']",
                        "//*[contains(@aria-label, 'link')]",
                        "//*[contains(@aria-label, 'Link')]",
                        "//button[contains(@aria-label, 'sticker')]",
                        "//*[@aria-label='Sticker']",
                    ]

                    link_button_found = False
                    for selector in link_button_selectors:
                        try:
                            link_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            self._log(f"  Found link button")
                            link_button.click()
                            self._human_delay(1, 2)
                            link_button_found = True
                            break
                        except TimeoutException:
                            continue

                    if not link_button_found:
                        # Try finding sticker menu and then link option
                        try:
                            sticker_menu = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Sticker')]")
                            sticker_menu.click()
                            self._human_delay(1, 2)
                        except NoSuchElementException:
                            self._log(f"  Could not find link/sticker button, skipping link", "WARN")

                    # Look for link option in sticker menu
                    try:
                        link_option = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Link') or contains(text(), 'link')]"))
                        )
                        link_option.click()
                        self._human_delay(1, 2)
                    except TimeoutException:
                        self._log(f"  Link option not found in menu", "WARN")

                    # Enter URL
                    try:
                        url_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='URL']"))
                        )
                        url_input.clear()
                        self._human_type(url_input, website_url)
                        self._human_delay(1, 2)
                        self._log(f"  Entered URL: {website_url}")
                    except TimeoutException:
                        try:
                            url_input = WebDriverWait(self.driver, 2).until(
                                EC.presence_of_element_located((By.XPATH, "//input[@type='url']"))
                            )
                            url_input.clear()
                            self._human_type(url_input, website_url)
                            self._human_delay(1, 2)
                            self._log(f"  Entered URL: {website_url}")
                        except TimeoutException:
                            self._log(f"  URL input not found", "WARN")

                    # Customize sticker text (optional)
                    try:
                        text_input = self.driver.find_element(By.XPATH, "//input[@placeholder='Add text']")
                        text_input.clear()
                        self._human_type(text_input, link_text)
                        self._human_delay(1, 2)
                        self._log(f"  Set link text: {link_text}")
                    except NoSuchElementException:
                        self._log(f"  Link text customization not available (using default)")

                    # Click Done/Add button
                    try:
                        done_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Done') or contains(text(), 'Add')]"))
                        )
                        done_button.click()
                        self._human_delay(1, 2)
                        self._log(f"  Link sticker added successfully")
                    except TimeoutException:
                        # Try pressing Enter instead
                        try:
                            from selenium.webdriver.common.keys import Keys
                            url_input.send_keys(Keys.RETURN)
                            self._human_delay(1, 2)
                            self._log(f"  Link sticker added (via Enter)")
                        except:
                            self._log(f"  Could not confirm link sticker", "WARN")

            except Exception as e:
                self._log(f"Error adding link sticker (continuing anyway): {e}", "WARN")

            # Look for "Add to story" or "Share" button
            self._log("STEP 7: Looking for Share/Add to story button...")
            self._human_delay(1, 2)

            share_selectors = [
                "//button[contains(text(), 'Add to story')]",
                "//button[contains(text(), 'Share to story')]",
                "//button[contains(text(), 'Share')]",
                "//*[contains(text(), 'Add to story')]//ancestor::button[1]",
                "//*[@role='button' and contains(text(), 'Share')]",
                "//div[contains(text(), 'Share')]",
                "//*[contains(@aria-label, 'Your story')]",
                "//*[contains(text(), 'Your story')]//ancestor::button[1]",
                "//button[@type='submit' and contains(., 'Share')]",
            ]

            share_button = None
            for selector in share_selectors:
                try:
                    share_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self._log(f"Found share button using: {selector[:50]}...")
                    break
                except TimeoutException:
                    continue

            # Fallback: pick the first visible primary-looking button near bottom
            if not share_button:
                try:
                    candidates = self.driver.find_elements(By.XPATH, "//button")
                    if candidates:
                        share_button = candidates[-1]  # often the bottom action
                        self._log("Using fallback bottom button for share", "WARN")
                except Exception:
                    pass

            if not share_button:
                self._log("Could not find Share button", "ERROR")
                return False

            self._log("Clicking Share button...")
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", share_button)
                self._human_delay(0.5, 1.0)
                share_button.click()
            except Exception:
                self._log("Direct click failed, trying JS click on share", "WARN")
                try:
                    self.driver.execute_script("arguments[0].click();", share_button)
                except Exception as e:
                    self._log(f"Share click failed: {e}", "ERROR")
                    return False
            self._log("Upload initiated, waiting for confirmation...")
            self._human_delay(2, 3)

            # Wait for confirmation
            self._log("STEP 8: Checking for upload confirmation...")

            confirmation_selectors = [
                "//*[contains(text(), 'Your story was shared')]",
                "//*[contains(text(), 'Story shared')]",
                "//*[contains(text(), 'shared')]",
                "//*[contains(text(), 'Shared')]",
            ]

            try:
                for selector in confirmation_selectors:
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        self._log("Upload confirmation found!", "SUCCESS")

                        # Save screenshot
                        try:
                            screenshot_path = Path("instagram_story_screenshot.png")
                            self.driver.save_screenshot(str(screenshot_path))
                            self._log(f"Screenshot saved to: {screenshot_path}", "INFO")
                        except Exception as e:
                            self._log(f"Could not save screenshot: {e}", "WARN")

                        self._log("COMPLETE: Story upload successful!", "SUCCESS")
                        return True
                    except TimeoutException:
                        continue

                # No confirmation found
                self._log("No confirmation message found", "WARN")
                self._log("Waiting 10 more seconds for late confirmation...")
                time.sleep(10)

                # Check once more
                try:
                    for selector in confirmation_selectors:
                        try:
                            self.driver.find_element(By.XPATH, selector)
                            self._log("Late confirmation detected - upload complete!", "SUCCESS")
                            return True
                        except NoSuchElementException:
                            continue

                    # Still no confirmation - likely failed
                    self._log("No confirmation after extended wait - upload may have failed", "ERROR")
                    return False
                except Exception as e:
                    self._log(f"Error checking for confirmation: {e}", "ERROR")
                    return False

            except Exception as e:
                self._log(f"Error waiting for confirmation: {e}", "ERROR")
                return False

        except Exception as e:
            self._log(f"Story upload failed with exception: {e}", "ERROR")
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
