#!/usr/bin/env python3
"""
Safe Lemon8 uploader using Selenium browser automation.

This mirrors the "safe uploader" approach used for Instagram/X:
- Real browser session
- Cookie-based login persistence
- Best-effort web composer automation
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
from selenium.common.exceptions import TimeoutException


class SafeLemon8Uploader:
    BASE_URL = "https://lemon8-app.com/"
    LOGIN_URL = "https://lemon8-app.com/"
    COMPOSE_URL_CANDIDATES = (
        "https://lemon8-app.com/post/publish",
        "https://lemon8-app.com/publish",
        "https://lemon8-app.com/create",
        "https://lemon8-app.com/creator/publish",
        "https://www.lemon8-app.com/post/publish",
        "https://www.lemon8-app.com/publish",
        "https://www.lemon8-app.com/create",
        "https://www.lemon8-app.com/creator/publish",
    )

    def __init__(self, cookies_file: str = "lemon8_cookies.json", headless: bool = False):
        self.cookies_file = str(cookies_file)
        self.headless = bool(headless)
        self.driver = None
        self.start_time = None
        self.session_active = False
        self._temp_profile_dir = None

    def _log(self, message: str, level: str = "INFO"):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = ""
        if self.start_time:
            elapsed = f" [{(time.time() - self.start_time):.1f}s]"
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
            self._temp_profile_dir = tempfile.mkdtemp(prefix="lemon8_safe_chrome_")
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
    def _sanitize_text(text: str, max_len: int = 400) -> str:
        value = "".join(ch for ch in str(text or "") if ord(ch) <= 0xFFFF).strip()
        if len(value) > max_len:
            return value[:max_len]
        return value

    @staticmethod
    def _prepare_cookie(cookie: dict) -> dict:
        out = dict(cookie or {})
        if "expiry" in out:
            try:
                out["expiry"] = int(out["expiry"])
            except Exception:
                out.pop("expiry", None)
        out.pop("sameSite", None)
        return out

    def _looks_logged_in(self) -> bool:
        if not self.driver:
            return False
        current_url = str(self.driver.current_url or "").lower()
        if "login" in current_url and "redirect" in current_url:
            return False
        selectors = [
            "input[type='file']",
            "button[aria-label*='Publish']",
            "button[aria-label*='Post']",
            "textarea",
            "[contenteditable='true']",
        ]
        for selector in selectors:
            try:
                self.driver.find_element(By.CSS_SELECTOR, selector)
                return True
            except Exception:
                continue
        return True

    def _load_cookies(self) -> bool:
        path = Path(self.cookies_file)
        if not path.exists():
            self._log(f"Cookie file not found: {path}", "ERROR")
            self._log("Run safe_lemon8_uploader.py --save-cookies first.", "ERROR")
            return False
        try:
            cookies = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(cookies, list) or not cookies:
                self._log(f"Cookie file is empty/invalid: {path}", "ERROR")
                return False
        except Exception as exc:
            self._log(f"Failed reading cookie file {path}: {exc}", "ERROR")
            return False

        self.driver.get(self.BASE_URL)
        self._human_delay(1.0, 2.0)
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

        self._log(f"Applied {applied}/{len(cookies)} Lemon8 cookies.")
        self.driver.get(self.BASE_URL)
        self._human_delay(2.0, 3.0)
        return self._looks_logged_in()

    def save_cookies(self) -> bool:
        self.start_time = time.time()
        self._log("Starting Lemon8 cookie save flow...")
        try:
            self._setup_driver()
            self.driver.get(self.LOGIN_URL)
            print("\n" + "=" * 72)
            print("Please log in to Lemon8 in the opened browser window.")
            print("After login is complete, press Enter here to save cookies.")
            print("=" * 72 + "\n")
            input("Press Enter after login is complete...")

            self.driver.get(self.BASE_URL)
            self._human_delay(1.5, 2.5)
            cookies = self.driver.get_cookies()
            if not cookies:
                self._log("No cookies captured. Save failed.", "ERROR")
                return False
            Path(self.cookies_file).write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._log(f"Saved {len(cookies)} cookies to {self.cookies_file}", "SUCCESS")
            return True
        except Exception as exc:
            self._log(f"Lemon8 cookie save failed: {exc}", "ERROR")
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
                self._log("Failed to load Lemon8 cookies.", "ERROR")
                return False
            self.session_active = True
            self._log("Lemon8 session started.", "SUCCESS")
            return True
        except Exception as exc:
            self._log(f"Failed to start Lemon8 session: {exc}", "ERROR")
            self.close_session()
            return False

    def _find_textarea(self):
        selectors = [
            (By.CSS_SELECTOR, "textarea"),
            (By.CSS_SELECTOR, "div[contenteditable='true']"),
            (By.CSS_SELECTOR, "[role='textbox']"),
        ]
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element.is_displayed():
                    return element
            except Exception:
                continue
        return None

    def _find_file_input(self):
        selectors = [
            (By.CSS_SELECTOR, "input[type='file'][accept*='video']"),
            (By.CSS_SELECTOR, "input[type='file'][accept*='mp4']"),
            (By.CSS_SELECTOR, "input[type='file']"),
        ]
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element.is_displayed():
                    return element
            except Exception:
                continue
        return None

    def _find_publish_button(self):
        selectors = [
            (By.XPATH, "//button[contains(., 'Publish')]"),
            (By.XPATH, "//button[contains(., 'Post')]"),
            (By.XPATH, "//button[contains(., 'Share')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ]
        for by, selector in selectors:
            try:
                button = self.driver.find_element(by, selector)
                if button.is_displayed():
                    return button
            except Exception:
                continue
        return None

    @staticmethod
    def _button_is_enabled(button) -> bool:
        if button is None:
            return False
        aria_disabled = str(button.get_attribute("aria-disabled") or "").strip().lower()
        if aria_disabled == "true":
            return False
        if button.get_attribute("disabled") is not None:
            return False
        return True

    def _open_compose_page(self) -> bool:
        for url in self.COMPOSE_URL_CANDIDATES:
            try:
                self._log(f"Trying Lemon8 compose URL: {url}")
                self.driver.get(url)
                self._human_delay(1.2, 2.0)
                if self._find_file_input() is not None:
                    return True
            except Exception:
                continue
        try:
            self.driver.get(self.BASE_URL)
            self._human_delay(1.0, 1.8)
            for selector in (
                "a[href*='publish']",
                "a[href*='create']",
                "button[aria-label*='Create']",
                "button[aria-label*='Publish']",
            ):
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector).click()
                    self._human_delay(1.0, 2.0)
                    if self._find_file_input() is not None:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return self._find_file_input() is not None

    def upload_post(self, video_path: str | Path, text: str, reuse_session: bool = True) -> bool:
        path = Path(video_path)
        if not path.exists():
            self._log(f"Video file not found: {path}", "ERROR")
            return False
        if not reuse_session or not self.session_active or not self.driver:
            if not self.start_session():
                return False

        try:
            if not self._open_compose_page():
                self._log("Could not find Lemon8 compose/upload UI.", "ERROR")
                return False

            file_input = self._find_file_input()
            if file_input is None:
                self._log("Lemon8 file input not found.", "ERROR")
                return False
            file_input.send_keys(str(path.resolve()))
            self._log("Video attached on Lemon8. Waiting for processing...")
            self._human_delay(8.0, 12.0)

            desc = self._find_textarea()
            if desc is not None:
                safe_text = self._sanitize_text(text)
                desc.click()
                self._human_delay(0.2, 0.6)
                desc.send_keys(Keys.CONTROL, "a")
                desc.send_keys(Keys.BACKSPACE)
                self._human_delay(0.2, 0.4)
                desc.send_keys(safe_text)

            end = time.time() + 240
            publish_button = None
            while time.time() < end:
                publish_button = self._find_publish_button()
                if self._button_is_enabled(publish_button):
                    break
                time.sleep(1.5)

            if not self._button_is_enabled(publish_button):
                self._log("Lemon8 publish button never became ready.", "ERROR")
                return False

            publish_button.click()
            self._log("Lemon8 post submitted.")
            self._human_delay(4.0, 6.0)
            return True
        except TimeoutException as exc:
            self._log(f"Lemon8 timeout: {exc}", "ERROR")
            return False
        except Exception as exc:
            self._log(f"Lemon8 safe upload failed: {exc}", "ERROR")
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
    parser = argparse.ArgumentParser(description="Safe Lemon8 uploader (Selenium)")
    parser.add_argument("--save-cookies", action="store_true", help="Login manually and save Lemon8 cookies.")
    parser.add_argument("--cookies-file", default="lemon8_cookies.json", help="Path to Lemon8 cookies JSON.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--video", default="", help="Video path to upload.")
    parser.add_argument("--text", default="", help="Caption text for the upload.")
    return parser.parse_args()


def main():
    args = _parse_args()
    uploader = SafeLemon8Uploader(cookies_file=args.cookies_file, headless=args.headless)

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
