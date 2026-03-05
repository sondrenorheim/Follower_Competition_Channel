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
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    import config
except Exception:
    config = None

DEFAULT_SQUARE_ASPECT_GAME_MODES = {
    "fighter_arena",
    "maze_rush",
    "mini_golf",
    "obstacle_course",
    "discord_signal",
    "snake_escape",
    "math_drop",
    "heads_or_tails",
    "side_choice",
}


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
        self.session_active = False
        self._temp_profile_dir = None
        self.mute_browser_audio = bool(
            getattr(config, "MUTE_BROWSER_AUDIO_DURING_UPLOADS", False)
        )

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
        self._cleanup_temp_profile()
        attempts = 2
        last_error = None

        for attempt in range(1, attempts + 1):
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument("--headless=new")

            # Keep Selenium runs isolated from your normal Chrome profile.
            self._temp_profile_dir = tempfile.mkdtemp(prefix="ig_safe_chrome_")
            chrome_options.add_argument(f"--user-data-dir={self._temp_profile_dir}")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-features=RendererCodeIntegrity")
            if self.mute_browser_audio:
                chrome_options.add_argument("--mute-audio")

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

            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(90)
                # Execute script to avoid detection
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                self._apply_runtime_audio_mute()
                return
            except Exception as exc:
                last_error = exc
                self._log(f"Chrome startup attempt {attempt}/{attempts} failed: {exc}", "WARN")
                try:
                    if self.driver:
                        self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                self._cleanup_temp_profile()
                if attempt < attempts:
                    time.sleep(2)

        raise RuntimeError(f"Chrome startup failed after {attempts} attempts: {last_error}")

    def _apply_runtime_audio_mute(self):
        """Best-effort runtime mute in case Chrome flag is ignored."""
        if not self.driver or not self.mute_browser_audio:
            return

        try:
            self.driver.execute_cdp_cmd("Media.setAudioMuted", {"muted": True})
            self._log("Browser audio muted for upload session.")
            return
        except Exception:
            pass

        try:
            self.driver.execute_script(
                "document.querySelectorAll('video,audio').forEach((el) => {"
                "el.muted = true; el.volume = 0;"
                "});"
            )
            self._log("Muted media elements in current page.")
        except Exception as exc:
            self._log(f"Could not apply runtime browser mute: {exc}", "WARN")

    def _cleanup_temp_profile(self):
        if not self._temp_profile_dir:
            return
        try:
            shutil.rmtree(self._temp_profile_dir, ignore_errors=True)
        except Exception:
            pass
        self._temp_profile_dir = None

    def _human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def _human_type(self, element, text: str):
        """Type text character by character with random delays (like a human)"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))  # 50-150ms between keystrokes

    def _sanitize_caption(self, text: str) -> str:
        """Strip non-BMP characters to avoid ChromeDriver send_keys errors."""
        if not text:
            return text
        sanitized = "".join(char for char in text if ord(char) <= 0xFFFF)
        if sanitized != text:
            removed = len(text) - len(sanitized)
            self._log(f"Caption contained {removed} non-BMP characters; stripped for ChromeDriver.", "WARN")
        return sanitized

    def _safe_click(self, element, label: str = "") -> bool:
        try:
            element.click()
            return True
        except Exception as e:
            suffix = f" ({label})" if label else ""
            self._log(f"Click failed{suffix}: {e}", "WARN")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_e:
                self._log(f"JS click failed{suffix}: {js_e}", "WARN")
                return False

    @staticmethod
    def _normalize_game_mode(game_mode: Optional[str]) -> str:
        return str(game_mode or "").strip().lower().replace("-", "_").replace(" ", "_")

    def _extract_game_mode_from_video_path(self, video_path: Path) -> str:
        stem = video_path.stem
        if "_day_" in stem:
            stem = stem.split("_day_", 1)[0]
        return self._normalize_game_mode(stem)

    def _get_square_aspect_modes(self) -> set[str]:
        configured = getattr(config, "INSTAGRAM_SQUARE_ASPECT_GAME_MODES", None) if config else None
        if configured:
            normalized = {
                self._normalize_game_mode(mode)
                for mode in configured
                if mode
            }
            # Support legacy alias in case only one of these is configured.
            if "heads_or_tails" in normalized:
                normalized.add("side_choice")
            if "side_choice" in normalized:
                normalized.add("heads_or_tails")
            return normalized
        return set(DEFAULT_SQUARE_ASPECT_GAME_MODES)

    def _resolve_target_aspect_ratio(self, video_path: Path, game_mode: Optional[str]) -> tuple[str, str]:
        resolved_mode = self._normalize_game_mode(game_mode) if game_mode else self._extract_game_mode_from_video_path(video_path)
        if resolved_mode in self._get_square_aspect_modes():
            return "1:1", resolved_mode
        return "9:16", resolved_mode

    def _select_upload_aspect_ratio(self, target_ratio: str) -> None:
        self._log(f"Checking for aspect ratio options (target: {target_ratio})...")
        try:
            aspect_selectors = [
                "//button[@aria-label='Select crop']",
                "//*[contains(@aria-label, 'crop')]",
                "//*[contains(@aria-label, 'Crop')]",
                "//button[contains(@aria-label, 'aspect')]",
                "//*[@role='button' and .//*[contains(text(), 'Original')]]",
                "//*[@role='button' and .//*[contains(text(), '1:1')]]",
                "//*[@role='button' and .//*[contains(text(), '9:16')]]",
                "//*[contains(text(), 'Original')]/ancestor::button[1]",
                "//*[contains(text(), '1:1')]/ancestor::button[1]",
                "//*[contains(text(), '9:16')]/ancestor::button[1]",
            ]

            for selector in aspect_selectors:
                try:
                    aspect_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self._log("Found aspect ratio button, clicking...")
                    self._safe_click(aspect_button, "aspect button")
                    self._human_delay(1, 2)
                    break
                except TimeoutException:
                    continue
                except Exception as e:
                    self._log(f"Aspect button error for selector {selector}: {e}", "WARN")
                    continue

            if target_ratio == "1:1":
                target_selectors = [
                    "//*[@aria-label='1:1']",
                    "//*[contains(text(), '1:1')]/ancestor::button[1]",
                    "//*[contains(text(), '1:1')]/ancestor::*[@role='button'][1]",
                    "//*[@role='menuitemradio' and .//*[contains(text(), '1:1')]]",
                    "//*[@role='menuitem' and .//*[contains(text(), '1:1')]]",
                    "//*[contains(text(), 'Square')]",
                ]
                option_label = "1:1 option"
            else:
                target_selectors = [
                    "//*[@aria-label='9:16']",
                    "//*[@aria-label='Portrait']",
                    "//*[@aria-label='Vertical']",
                    "//*[contains(text(), '9:16')]/ancestor::button[1]",
                    "//*[contains(text(), '9:16')]/ancestor::*[@role='button'][1]",
                    "//*[@role='menuitemradio' and .//*[contains(text(), '9:16')]]",
                    "//*[@role='menuitem' and .//*[contains(text(), '9:16')]]",
                    "//*[contains(text(), '9:16')]",
                    "//*[contains(text(), 'Portrait')]",
                    "//*[contains(text(), 'Vertical')]",
                ]
                option_label = "9:16 option"

            target_clicked = False
            for selector in target_selectors:
                try:
                    target_option = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self._log(f"Found {target_ratio} option, clicking...")
                    if self._safe_click(target_option, option_label):
                        target_clicked = True
                        self._human_delay(1, 2)
                        break
                except TimeoutException:
                    continue
                except Exception as e:
                    self._log(f"Aspect ratio option error for selector {selector}: {e}", "WARN")
                    continue

            if not target_clicked:
                self._log(
                    f"Could not find {target_ratio} option - using current/default aspect ratio",
                    "WARN",
                )
        except Exception as e:
            self._log(f"Aspect ratio selection skipped: {e}", "WARN")

    def _attempt_cover_selection(self) -> bool:
        self._log("Checking for cover/thumbnail options...")
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            slider_selectors = [
                'input[type="range"]',
                'input[role="slider"]',
                '//*[@role="slider"]'
            ]

            def read_slider_state(slider) -> tuple[float | None, float | None]:
                value = None
                transform_x = None
                try:
                    value_raw = slider.get_attribute("aria-valuenow")
                    if value_raw is not None:
                        value = float(value_raw)
                except Exception:
                    value = None

                try:
                    style = slider.get_attribute("style") or ""
                    match = re.search(r"translate3d\\(([-0-9.]+)px", style)
                    if match:
                        transform_x = float(match.group(1))
                except Exception:
                    transform_x = None

                return value, transform_x

            def slider_moved(before: tuple[float | None, float | None], after: tuple[float | None, float | None]) -> bool:
                before_val, before_x = before
                after_val, after_x = after
                if before_val is not None and after_val is not None and abs(after_val - before_val) > 0.01:
                    return True
                if before_x is not None and after_x is not None and abs(after_x - before_x) > 0.5:
                    return True
                return False

            def find_slider():
                for slider_sel in slider_selectors:
                    try:
                        if slider_sel.startswith('//'):
                            sliders = self.driver.find_elements(By.XPATH, slider_sel)
                        else:
                            sliders = self.driver.find_elements(By.CSS_SELECTOR, slider_sel)
                        for candidate in sliders:
                            try:
                                if not candidate.is_displayed():
                                    continue
                            except Exception:
                                pass
                            size = candidate.size or {}
                            if size.get("width", 0) > 0 and size.get("height", 0) > 0:
                                return candidate
                    except Exception:
                        continue
                return None

            def drag_slider_to_middle(slider) -> bool:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                        slider,
                    )
                except Exception:
                    pass

                before_state = read_slider_state(slider)
                actions = ActionChains(self.driver)
                rect = slider.rect or {}
                width = float(rect.get("width", 0) or 0)
                height = float(rect.get("height", 0) or 0)
                if width <= 0 or height <= 0:
                    self._log("Slider rect unavailable, clicking as fallback", "WARN")
                    actions.move_to_element(slider).click().perform()
                    return False

                track_rect = self.driver.execute_script(
                    """
                    const el = arguments[0];
                    const elRect = el.getBoundingClientRect();
                    let parent = el.parentElement;
                    while (parent) {
                        const r = parent.getBoundingClientRect();
                        if (r.width > elRect.width + 10 && r.height >= elRect.height) {
                            return {x: r.x, y: r.y, width: r.width, height: r.height};
                        }
                        parent = parent.parentElement;
                    }
                    return null;
                    """,
                    slider,
                )

                rect_x = float(rect.get("x", rect.get("left", 0)) or 0)
                rect_y = float(rect.get("y", rect.get("top", 0)) or 0)
                center_x = rect_x + width / 2
                center_y = rect_y + height / 2
                offset_x = int(width * 0.5)
                current_val, current_transform = before_state
                if track_rect and track_rect.get("width", 0):
                    track_x = float(track_rect.get("x", track_rect.get("left", 0)) or 0)
                    track_width = float(track_rect.get("width", 0) or 0)
                    target_x = track_x + (track_width * 0.5)
                    offset_x = int(target_x - center_x)
                    if current_transform is not None:
                        offset_x = int((track_width * 0.5) - current_transform)

                steps = 5
                step_offset = offset_x / steps if steps else offset_x
                actions.move_to_element_with_offset(slider, int(width / 2), int(height / 2))
                actions.click_and_hold()
                for _ in range(steps):
                    actions.move_by_offset(step_offset, 0)
                actions.release()
                actions.perform()

                after_state = read_slider_state(slider)
                if slider_moved(before_state, after_state):
                    return True

                try:
                    if track_rect and track_rect.get("width", 0):
                        track_x = float(track_rect.get("x", track_rect.get("left", 0)) or 0)
                        track_y = float(track_rect.get("y", track_rect.get("top", 0)) or 0)
                        track_width = float(track_rect.get("width", 0) or 0)
                        track_height = float(track_rect.get("height", 0) or 0)
                        start_x = track_x + 2
                        start_y = track_y + (track_height / 2)
                        target_x = track_x + (track_width * 0.5)
                        target_y = start_y
                    else:
                        start_x = center_x
                        start_y = center_y
                        target_x = center_x + offset_x
                        target_y = center_y

                    self._log("Attempting JS drag on cover track...")
                    self.driver.execute_script(
                        """
                        const el = arguments[0];
                        const sx = arguments[1];
                        const sy = arguments[2];
                        const ex = arguments[3];
                        const ey = arguments[4];
                        function fire(type, x, y, target) {
                            const evt = new PointerEvent(type, {
                                bubbles: true,
                                cancelable: true,
                                clientX: x,
                                clientY: y,
                                pointerType: 'mouse',
                                buttons: 1
                            });
                            target.dispatchEvent(evt);
                        }
                        const startTarget = document.elementFromPoint(sx, sy) || el;
                        const endTarget = document.elementFromPoint(ex, ey) || el;
                        fire('pointerdown', sx, sy, startTarget);
                        fire('pointermove', ex, ey, endTarget);
                        fire('pointerup', ex, ey, endTarget);
                        startTarget.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: sx, clientY: sy}));
                        endTarget.dispatchEvent(new MouseEvent('mousemove', {bubbles: true, clientX: ex, clientY: ey}));
                        endTarget.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, clientX: ex, clientY: ey}));
                        """,
                        slider,
                        float(start_x),
                        float(start_y),
                        float(target_x),
                        float(target_y),
                    )
                    after_state = read_slider_state(slider)
                    if slider_moved(before_state, after_state):
                        return True
                except Exception as js_error:
                    self._log(f"JS drag failed: {js_error}", "WARN")

                if track_rect and track_rect.get("width", 0):
                    try:
                        track_x = float(track_rect.get("x", track_rect.get("left", 0)) or 0)
                        track_y = float(track_rect.get("y", track_rect.get("top", 0)) or 0)
                        track_width = float(track_rect.get("width", 0) or 0)
                        track_height = float(track_rect.get("height", 0) or 0)
                        click_x = track_x + (track_width * 0.5)
                        click_y = track_y + (track_height / 2)
                        self._log("Attempting JS click on cover track midpoint...")
                        self.driver.execute_script(
                            """
                            const x = arguments[0];
                            const y = arguments[1];
                            const target = document.elementFromPoint(x, y);
                            if (target) {
                                target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: x, clientY: y}));
                                target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, clientX: x, clientY: y}));
                                target.click();
                            }
                            """,
                            float(click_x),
                            float(click_y),
                        )
                        after_state = read_slider_state(slider)
                        if slider_moved(before_state, after_state):
                            return True
                    except Exception as click_error:
                        self._log(f"Track midpoint click failed: {click_error}", "WARN")

                return False

            def adjust_slider() -> tuple[bool, bool]:
                self._log("Looking for thumbnail slider...")
                slider = find_slider()
                if not slider:
                    self._log("No slider found, using default frame")
                    return False, False

                try:
                    if drag_slider_to_middle(slider):
                        self._human_delay(1, 2)
                        self._log("Selected middle frame of video for thumbnail")
                        return True, True
                except Exception as slider_error:
                    self._log(f"Could not drag slider: {slider_error}", "WARN")

                try:
                    self.driver.execute_script("arguments[0].focus();", slider)
                    slider.click()
                    self._human_delay(0.2, 0.4)
                    try:
                        min_val = float(slider.get_attribute("aria-valuemin") or 0)
                        max_val = float(slider.get_attribute("aria-valuemax") or 100)
                        current_val = float(slider.get_attribute("aria-valuenow") or 0)
                        target_val = (min_val + max_val) / 2
                        step_count = int(abs(target_val - current_val))
                    except Exception:
                        step_count = 50

                    step_count = max(1, min(120, step_count))
                    step_key = Keys.ARROW_RIGHT
                    before_state = read_slider_state(slider)
                    for _ in range(step_count):
                        slider.send_keys(step_key)
                    self._human_delay(0.4, 0.8)
                    after_state = read_slider_state(slider)
                    if slider_moved(before_state, after_state):
                        self._log("Selected middle frame of video for thumbnail (keys)")
                        return True, True
                    self._log("Slider key adjustment had no effect", "WARN")
                    return True, False
                except Exception as key_error:
                    self._log(f"Slider key adjustment failed: {key_error}", "WARN")
                    return True, False

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
                    if not self._safe_click(cover_button, "cover button"):
                        continue
                    self._human_delay(2, 3)

                    found_slider, moved = adjust_slider()
                    if found_slider and not moved:
                        self._log("Cover slider found but could not move", "WARN")

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
                                if self._safe_click(done_button, "cover done"):
                                    self._log("Closed cover selector")
                                    self._human_delay(1, 2)
                                    break
                            except TimeoutException:
                                continue
                    except Exception:
                        self._log("Cover selector closed automatically")

                    return True
                except TimeoutException:
                    continue
                except Exception as e:
                    self._log(f"Cover selector error for {selector}: {e}", "WARN")
                    continue

            if not cover_button:
                self._log("No cover selection option - trying slider directly")
                found_slider, moved = adjust_slider()
                if moved:
                    return True
                if found_slider:
                    self._log("Cover slider found but could not move - using default thumbnail", "WARN")
                else:
                    self._log("No slider found after cover check - using default thumbnail")
            return False

        except Exception as e:
            self._log(f"Cover selection skipped - using default thumbnail: {e}", "WARN")
            return False

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
        self._cleanup_temp_profile()

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
            self._log("Opening Instagram page to attach cookies...")
            self.driver.get("https://www.instagram.com")
            self._human_delay(2, 3)

            # Add cookies
            self._log(f"Applying {len(cookies)} cookies...")
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
                self.session_active = True
                return True

        except Exception as e:
            self._log(f"Error loading cookies: {e}", "ERROR")
            return False

    def _is_logged_in(self) -> bool:
        if not self.driver:
            return False
        try:
            self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
            return False
        except NoSuchElementException:
            return True
        except Exception:
            return True

    def start_session(self) -> bool:
        """
        Start a browser session and load cookies once for multiple uploads.
        """
        self.start_time = time.time()
        self._log("=" * 50)
        self._log("STARTING SAFE INSTAGRAM SESSION")
        self._log("=" * 50)

        try:
            if not self.driver:
                self._log("Setting up Chrome browser...")
                self._setup_driver()
                self._log("Browser started successfully")

            self._log("Loading saved cookies...")
            if not self._load_cookies():
                self._log("Failed to load cookies", "ERROR")
                return False

            self._log("Navigating to Instagram home...")
            self.driver.get("https://www.instagram.com/")
            self._human_delay(3, 5)
            self.session_active = True
            return True
        except Exception as e:
            self._log(f"Failed to start session: {e}", "ERROR")
            return False

    def close_session(self):
        """
        Close the browser session.
        """
        if self.driver:
            try:
                self._human_delay(1, 2)
                self.driver.quit()
            except Exception:
                pass
        self.driver = None
        self.session_active = False
        self._cleanup_temp_profile()

    def upload_reel(
        self,
        video_path: str,
        caption: str = "",
        reuse_session: bool = False,
        game_mode: Optional[str] = None,
    ) -> bool:
        """
        Upload a video as an Instagram Reel

        Args:
            video_path: Path to video file
            caption: Caption text
            reuse_session: Keep browser open and reuse existing session
            game_mode: Optional explicit game mode (used for aspect ratio selection)

        Returns:
            True if upload successful
        """
        self.start_time = time.time()
        video_path = Path(video_path).resolve()
        target_aspect_ratio, resolved_game_mode = self._resolve_target_aspect_ratio(video_path, game_mode)

        self._log("=" * 50)
        self._log("INSTAGRAM REEL UPLOAD STARTED")
        self._log("=" * 50)

        if not video_path.exists():
            self._log(f"Video not found: {video_path}", "ERROR")
            return False

        caption = self._sanitize_caption(caption)
        self._log(f"Video file: {video_path.name}")
        self._log(f"Video size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
        self._log(f"Caption: {caption[:50]}..." if len(caption) > 50 else f"Caption: {caption}")
        self._log(f"Game mode: {resolved_game_mode or 'unknown'} | Target aspect: {target_aspect_ratio}")

        try:
            if not self.driver:
                self._log("STEP 1: Setting up Chrome browser...")
                self._setup_driver()
                self._log("Browser started successfully")

            if not self.session_active:
                self._log("STEP 2: Loading saved cookies...")
                if not self._load_cookies():
                    self._log("Failed to load cookies", "ERROR")
                    return False
            elif not self._is_logged_in():
                self._log("Session appears logged out; reloading cookies...", "WARN")
                if not self._load_cookies():
                    self._log("Failed to reload cookies", "ERROR")
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

            # Select upload framing per game mode.
            self._select_upload_aspect_ratio(target_aspect_ratio)

            # Click "Next" button to proceed (there might be multiple Next buttons)
            self._log("STEP 7: Clicking Next button...")
            next_selectors = [
                "//button[contains(text(), 'Next')]",
                "//button[text()='Next']",
                "//div[contains(text(), 'Next')]",
                "//*[@role='button' and contains(text(), 'Next')]"
            ]

            # First Next button
            first_next_clicked = False
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
                    first_next_clicked = self._safe_click(next_button, "first next")
                    self._human_delay(2, 3)
                else:
                    self._log("First Next button not found, trying to continue...", "WARN")
            except Exception as e:
                self._log(f"Error clicking first Next: {e}", "WARN")

            cover_selected = False
            if first_next_clicked:
                cover_selected = self._attempt_cover_selection()

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
                    self._safe_click(next_button, "second next")
                    self._human_delay(2, 3)
                else:
                    self._log("No second Next button (OK)")
            except Exception:
                self._log("No second Next button (OK)")

            if not cover_selected:
                self._attempt_cover_selection()

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

                # No confirmation yet - check for obvious, visible errors
                self._log("No explicit confirmation message found", "WARN")
                self._log("Checking page for error messages...")
                try:
                    error_elements = self.driver.find_elements(
                        By.XPATH,
                        "//*[contains(translate(normalize-space(text()), "
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'error') "
                        "or contains(translate(normalize-space(text()), "
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'failed') "
                        "or contains(translate(normalize-space(text()), "
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'try again') "
                        "or contains(translate(normalize-space(text()), "
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'couldn') "
                        "or contains(translate(normalize-space(text()), "
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'went wrong')]",
                    )
                    visible_error_texts = []
                    for candidate in error_elements:
                        try:
                            if not candidate.is_displayed():
                                continue
                        except Exception:
                            continue
                        text_value = (candidate.text or "").strip()
                        if text_value:
                            visible_error_texts.append(text_value)
                    if visible_error_texts:
                        self._log(f"Found error message on page: {visible_error_texts[0]}", "ERROR")
                        return False
                except Exception:
                    pass

                try:
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
                        # Heuristic fallback: if the Share UI is gone, Instagram likely accepted the upload.
                        share_still_visible = False
                        for selector in share_selectors:
                            try:
                                for element in self.driver.find_elements(By.XPATH, selector):
                                    try:
                                        if element.is_displayed():
                                            share_still_visible = True
                                            break
                                    except Exception:
                                        continue
                                if share_still_visible:
                                    break
                            except Exception:
                                continue

                        if not share_still_visible:
                            self._log(
                                "No confirmation message, but Share UI is gone; assuming upload likely succeeded.",
                                "WARN",
                            )
                            return True

                        self._log("No confirmation message found after extended wait - upload likely failed", "ERROR")
                        self._log("Upload timed out without confirmation", "ERROR")
                        return False
                except Exception:
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
            if self.driver and not reuse_session:
                self._human_delay(2, 3)
                self.driver.quit()
                self.driver = None
                self.session_active = False
                self._cleanup_temp_profile()


def main():
    parser = argparse.ArgumentParser(description="Safe Instagram Reel Uploader using Selenium")
    parser.add_argument("--save-cookies", action="store_true", help="Login and save cookies for future use")
    parser.add_argument("--video", help="Path to video file to upload")
    parser.add_argument("--caption", default="", help="Caption for the reel")
    parser.add_argument("--game-mode", default="", help="Optional game mode override for aspect ratio rules")
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
        success = uploader.upload_reel(args.video, args.caption, game_mode=args.game_mode or None)
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
