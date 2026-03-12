#!/usr/bin/env python3
"""
Safe X uploader using Selenium browser automation.

This follows the same "safe uploader" concept as Instagram:
- Uses a real browser session + cookies
- Mimics manual posting flow
- Avoids API credit usage
"""

from __future__ import annotations

import argparse
import datetime
import json
import random
import shutil
import tempfile
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)


class SafeXUploader:
    def __init__(
        self,
        cookies_file: str = "x_cookies.json",
        headless: bool = False,
        post_ready_timeout_seconds: int = 60,
        post_click_attempts: int = 4,
    ):
        self.cookies_file = str(cookies_file)
        self.headless = bool(headless)
        self.post_ready_timeout_seconds = max(20, int(post_ready_timeout_seconds or 60))
        self.post_click_attempts = max(1, int(post_click_attempts or 4))
        self.driver = None
        self.start_time = None
        self.session_active = False
        self._temp_profile_dir = None

    def _log(self, message: str, level: str = "INFO"):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = ""
        if self.start_time:
            elapsed_sec = time.time() - self.start_time
            elapsed = f" [{elapsed_sec:.1f}s]"
        print(f"[{now}]{elapsed} [{level}] {message}", flush=True)

    def _human_delay(self, min_seconds: float = 0.8, max_seconds: float = 1.8):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _cleanup_temp_profile(self):
        if not self._temp_profile_dir:
            return
        try:
            shutil.rmtree(self._temp_profile_dir, ignore_errors=True)
        except Exception:
            pass
        self._temp_profile_dir = None

    def _setup_driver(self):
        self._cleanup_temp_profile()
        attempts = 2
        last_error = None
        for attempt in range(1, attempts + 1):
            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
            self._temp_profile_dir = tempfile.mkdtemp(prefix="x_safe_chrome_")
            options.add_argument(f"--user-data-dir={self._temp_profile_dir}")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
            try:
                self.driver = webdriver.Chrome(options=options)
                self.driver.set_page_load_timeout(90)
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
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

    @staticmethod
    def _normalize_text(text: str, max_len: int = 280) -> str:
        value = "".join(ch for ch in str(text or "") if ord(ch) <= 0xFFFF)
        value = value.strip()
        if len(value) > max_len:
            return value[:max_len]
        return value

    @staticmethod
    def _prepare_cookie(cookie: dict) -> dict:
        out = dict(cookie or {})
        # Selenium expects int expiry.
        if "expiry" in out:
            try:
                out["expiry"] = int(out["expiry"])
            except Exception:
                out.pop("expiry", None)
        # Some exports include unsupported keys.
        out.pop("sameSite", None)
        return out

    def _looks_logged_in(self) -> bool:
        if not self.driver:
            return False
        current_url = str(self.driver.current_url or "").lower()
        if "/i/flow/login" in current_url or "/login" in current_url:
            return False
        selectors = [
            "a[data-testid='SideNav_NewTweet_Button']",
            "a[href='/compose/post']",
            "div[data-testid='primaryColumn']",
        ]
        for selector in selectors:
            try:
                self.driver.find_element(By.CSS_SELECTOR, selector)
                return True
            except Exception:
                continue
        return False

    def _load_cookies(self) -> bool:
        path = Path(self.cookies_file)
        if not path.exists():
            self._log(f"Cookie file not found: {path}", "ERROR")
            self._log("Run safe_x_uploader.py --save-cookies first.", "ERROR")
            return False
        try:
            cookies = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(cookies, list) or not cookies:
                self._log(f"Cookie file is empty/invalid: {path}", "ERROR")
                return False
        except Exception as exc:
            self._log(f"Failed reading cookie file {path}: {exc}", "ERROR")
            return False

        self._log("Opening X to attach cookies...")
        self.driver.get("https://x.com/")
        self._human_delay(1.0, 2.2)

        applied = 0
        for raw_cookie in cookies:
            try:
                cookie = self._prepare_cookie(raw_cookie)
                if "name" not in cookie or "value" not in cookie:
                    continue
                self.driver.add_cookie(cookie)
                applied += 1
            except Exception:
                continue

        self._log(f"Applied {applied}/{len(cookies)} cookies.")
        self.driver.get("https://x.com/home")
        self._human_delay(2.0, 3.0)

        if not self._looks_logged_in():
            self._log("Cookies appear invalid or expired. Please save cookies again.", "ERROR")
            return False

        self._log("Logged in successfully using saved cookies.", "SUCCESS")
        return True

    def save_cookies(self) -> bool:
        self.start_time = time.time()
        self._log("Starting X cookie save flow...")
        try:
            self._setup_driver()
            self.driver.get("https://x.com/i/flow/login")
            print("\n" + "=" * 70)
            print("Please log in to X in the opened browser window.")
            print("After login completes and your home feed is visible, press Enter here.")
            print("=" * 70 + "\n")
            input("Press Enter after login is complete...")

            self.driver.get("https://x.com/home")
            self._human_delay(2.0, 3.0)
            if not self._looks_logged_in():
                self._log("Login not detected. Cookie save aborted.", "ERROR")
                return False

            cookies = self.driver.get_cookies()
            Path(self.cookies_file).write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._log(f"Saved {len(cookies)} cookies to {self.cookies_file}", "SUCCESS")
            return True
        except Exception as exc:
            self._log(f"Cookie save failed: {exc}", "ERROR")
            return False
        finally:
            self.close_session()

    def start_session(self) -> bool:
        if self.session_active and self.driver:
            return True
        self.start_time = time.time()
        try:
            self._setup_driver()
            if not self._load_cookies():
                return False
            self.session_active = True
            return True
        except Exception as exc:
            self._log(f"Failed to start X session: {exc}", "ERROR")
            self.close_session()
            return False

    def _wait_for_compose(self, timeout: int = 60):
        if not self.driver:
            raise RuntimeError("Driver is not started.")
        selectors = [
            (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"),
            (By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']"),
        ]
        end = time.time() + max(10, timeout)
        while time.time() < end:
            for by, selector in selectors:
                try:
                    element = self.driver.find_element(by, selector)
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
            time.sleep(1.0)
        raise TimeoutException("Could not find X compose text area.")

    def _find_file_input(self):
        selectors = [
            (By.CSS_SELECTOR, "input[data-testid='fileInput']"),
            (By.CSS_SELECTOR, "input[type='file'][accept*='video']"),
            (By.CSS_SELECTOR, "input[type='file']"),
        ]
        for by, selector in selectors:
            try:
                return self.driver.find_element(by, selector)
            except Exception:
                continue
        raise TimeoutException("Could not find X file input element.")

    def _find_post_buttons(self):
        selectors = [
            (By.CSS_SELECTOR, "button[data-testid='tweetButton']"),
            (By.CSS_SELECTOR, "button[data-testid='tweetButtonInline']"),
        ]
        buttons = []
        for by, selector in selectors:
            try:
                buttons.extend(self.driver.find_elements(by, selector))
            except Exception:
                continue
        return buttons

    @staticmethod
    def _button_is_enabled(button) -> bool:
        if button is None:
            return False
        disabled_attr = str(button.get_attribute("aria-disabled") or "").strip().lower()
        if disabled_attr == "true":
            return False
        if button.get_attribute("disabled") is not None:
            return False
        return True

    def _element_is_unobstructed(self, element) -> bool:
        if not self.driver:
            return False
        try:
            return bool(
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) return false;
                    const x = rect.left + (rect.width / 2);
                    const y = rect.top + (rect.height / 2);
                    const topEl = document.elementFromPoint(x, y);
                    return !!topEl && (topEl === el || el.contains(topEl));
                    """,
                    element,
                )
            )
        except Exception:
            return False

    def _wait_for_post_ready(self, timeout: int = 240, stable_checks: int = 2):
        end = time.time() + max(20, timeout)
        stable_hits = 0
        last_ready = None
        while time.time() < end:
            ready_button = None
            for button in self._find_post_buttons():
                try:
                    if not button.is_displayed():
                        continue
                    if not self._button_is_enabled(button):
                        continue
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                        button,
                    )
                    if not self._element_is_unobstructed(button):
                        continue
                    ready_button = button
                    break
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue

            if ready_button is not None:
                stable_hits += 1
                last_ready = ready_button
                if stable_hits >= max(1, int(stable_checks or 1)):
                    return last_ready
            else:
                stable_hits = 0
                last_ready = None
            time.sleep(1.2)
        raise TimeoutException("X post button did not become ready in time (upload still processing?).")

    def _click_post_button_with_retry(self, timeout: int = 360, attempts: int = 8):
        deadline = time.time() + max(30, timeout)
        last_error = None
        max_attempts = max(1, int(attempts or 1))
        for attempt_index in range(1, max_attempts + 1):
            remaining = int(deadline - time.time())
            if remaining <= 0:
                break
            button = self._wait_for_post_ready(timeout=max(20, remaining), stable_checks=1)
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                    button,
                )
                self._human_delay(0.1, 0.3)
                button.click()
                return
            except ElementClickInterceptedException as exc:
                last_error = exc
                self._log(
                    f"Post click intercepted (attempt {attempt_index}/{max_attempts}); "
                    "waiting for processing overlay to clear...",
                    "WARN",
                )
                time.sleep(min(3.5, 1.0 + attempt_index * 0.4))
            except StaleElementReferenceException as exc:
                last_error = exc
                time.sleep(0.8)
            except Exception as exc:
                last_error = exc
                if attempt_index >= max_attempts:
                    raise
                time.sleep(1.2)

        if last_error:
            raise last_error
        raise TimeoutException("Timed out while trying to click X post button.")

    def upload_post(self, video_path: str | Path, text: str, reuse_session: bool = True) -> bool:
        path = Path(video_path)
        if not path.exists():
            self._log(f"Video file not found: {path}", "ERROR")
            return False

        if not reuse_session or not self.session_active or not self.driver:
            if not self.start_session():
                return False

        try:
            post_text = self._normalize_text(text, max_len=280)
            self._log(f"Opening X composer for {path.name}...")
            self.driver.get("https://x.com/compose/post")
            composer = self._wait_for_compose(timeout=60)
            self._human_delay(0.5, 1.2)

            composer.click()
            self._human_delay(0.2, 0.6)
            composer.send_keys(Keys.CONTROL, "a")
            composer.send_keys(Keys.BACKSPACE)
            self._human_delay(0.2, 0.4)
            composer.send_keys(post_text)

            file_input = self._find_file_input()
            file_input.send_keys(str(path.resolve()))
            self._log("Video attached. Waiting for X to finish upload/processing...")

            self._click_post_button_with_retry(
                timeout=self.post_ready_timeout_seconds,
                attempts=self.post_click_attempts,
            )
            self._log("Post submitted. Waiting for completion...")
            self._human_delay(4.0, 6.0)
            return True
        except Exception as exc:
            self._log(f"X safe upload failed for {path.name}: {exc}", "ERROR")
            return False

    def close_session(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None
        self.session_active = False
        self._cleanup_temp_profile()


def _parse_args():
    parser = argparse.ArgumentParser(description="Safe X uploader (Selenium)")
    parser.add_argument("--save-cookies", action="store_true", help="Login manually and save X cookies.")
    parser.add_argument("--cookies-file", default="x_cookies.json", help="Path to X cookies JSON.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--video", default="", help="Video path to upload.")
    parser.add_argument("--text", default="", help="Post text for the upload.")
    return parser.parse_args()


def main():
    args = _parse_args()
    uploader = SafeXUploader(cookies_file=args.cookies_file, headless=args.headless)
    if args.save_cookies:
        ok = uploader.save_cookies()
        raise SystemExit(0 if ok else 1)

    if not args.video:
        print("Use --save-cookies or provide --video and --text")
        raise SystemExit(1)

    ok = uploader.upload_post(video_path=args.video, text=args.text, reuse_session=False)
    uploader.close_session()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
