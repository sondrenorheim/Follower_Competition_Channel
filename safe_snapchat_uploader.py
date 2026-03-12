#!/usr/bin/env python3
"""
Safe Snapchat uploader using Selenium browser automation.

This follows the same "safe uploader" concept used for X:
- Real browser session + cookies
- Manual login once to save cookies
- Reuse cookies for unattended uploads

Target behavior:
- Upload video
- Post to Spotlight (spotlight-only mode by default)
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
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)


class SafeSnapchatUploader:
    BASE_URL = "https://profile.snapchat.com/"
    LOGIN_URL = "https://profile.snapchat.com/"
    ACCOUNTS_URL = "https://accounts.snapchat.com/"
    ACCOUNTS_LOGIN_URL = "https://accounts.snapchat.com/accounts/v2/login"
    COMPOSE_URL_CANDIDATES = (
        "https://profile.snapchat.com/",
        "https://profile.snapchat.com/profiles",
    )

    def __init__(
        self,
        cookies_file: str = "snapchat_cookies.json",
        headless: bool = False,
        spotlight_only: bool = True,
        profile_dir: str | None = None,
    ):
        self.cookies_file = str(cookies_file)
        self.headless = bool(headless)
        self.spotlight_only = bool(spotlight_only)
        self.profile_dir = str(profile_dir or "").strip()
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
            if self.profile_dir:
                profile_path = Path(self.profile_dir)
                profile_path.mkdir(parents=True, exist_ok=True)
                options.add_argument(f"--user-data-dir={str(profile_path.resolve())}")
            else:
                self._temp_profile_dir = tempfile.mkdtemp(prefix="snapchat_safe_chrome_")
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
    def _sanitize_text(text: str, max_len: int = 160) -> str:
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
        # Keep valid SameSite values when present; drop unknown values.
        same_site = str(out.get("sameSite") or "").strip()
        if same_site not in {"Strict", "Lax", "None"}:
            out.pop("sameSite", None)
        # Selenium rejects unsupported keys in some cookie payloads.
        out.pop("hostOnly", None)
        out.pop("storeId", None)
        out.pop("session", None)
        return out

    @staticmethod
    def _cookie_key(cookie: dict) -> tuple[str, str, str]:
        name = str(cookie.get("name") or "").strip()
        domain = str(cookie.get("domain") or "").strip().lower()
        path = str(cookie.get("path") or "/").strip() or "/"
        return (name, domain, path)

    @staticmethod
    def _seed_url_for_cookie_domain(domain: str) -> str:
        normalized = str(domain or "").strip().lower().lstrip(".")
        if not normalized:
            return "https://profile.snapchat.com/"
        if normalized.endswith("accounts.snapchat.com"):
            return "https://accounts.snapchat.com/"
        if normalized.endswith("snapchat.com"):
            return "https://profile.snapchat.com/"
        return f"https://{normalized}/"

    def _collect_cookie_snapshot(self) -> list[dict]:
        if not self.driver:
            return []
        # Capture cookies from both profile + accounts contexts.
        probe_urls = [
            self.BASE_URL,
            self.ACCOUNTS_URL,
            self.ACCOUNTS_LOGIN_URL,
        ]
        merged: dict[tuple[str, str, str], dict] = {}
        for url in probe_urls:
            try:
                self.driver.get(url)
                self._human_delay(1.0, 2.0)
                for raw_cookie in self.driver.get_cookies():
                    cookie = self._prepare_cookie(raw_cookie)
                    if not cookie.get("name") or not cookie.get("value"):
                        continue
                    merged[self._cookie_key(cookie)] = cookie
            except Exception:
                continue
        return list(merged.values())

    def _looks_logged_in(self) -> bool:
        if not self.driver:
            return False
        current_url = str(self.driver.current_url or "").lower()
        if "accounts.snapchat.com" in current_url and ("login" in current_url or "oauth" in current_url):
            return False

        # Positive signals from profile manager UI.
        positive_selectors = [
            (By.XPATH, "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'post to snapchat')]"),
            (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'public stories')]"),
            (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'profile details')]"),
        ]
        for by, selector in positive_selectors:
            try:
                el = self.driver.find_element(by, selector)
                if el.is_displayed():
                    return True
            except Exception:
                continue

        # Hard fail only on direct login form controls.
        hard_fail_selectors = [
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[type='email']"),
        ]
        for by, selector in hard_fail_selectors:
            try:
                for el in self.driver.find_elements(by, selector):
                    if el.is_displayed():
                        return False
            except Exception:
                continue

        # Fallback: if we're on profile.snapchat.com without login form, treat session as usable.
        return "profile.snapchat.com" in current_url

    def _load_cookies(self) -> bool:
        path = Path(self.cookies_file)
        if not path.exists():
            self._log(f"Cookie file not found: {path}", "ERROR")
            self._log("Run safe_snapchat_uploader.py --save-cookies first.", "ERROR")
            return False
        try:
            cookies = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(cookies, list) or not cookies:
                self._log(f"Cookie file is empty/invalid: {path}", "ERROR")
                return False
        except Exception as exc:
            self._log(f"Failed reading cookie file {path}: {exc}", "ERROR")
            return False

        self._log("Opening Snapchat domains to attach cookies...")
        applied = 0
        current_seed = ""
        for raw_cookie in cookies:
            cookie = self._prepare_cookie(raw_cookie)
            if "name" not in cookie or "value" not in cookie:
                continue
            seed_url = self._seed_url_for_cookie_domain(cookie.get("domain", ""))
            if seed_url != current_seed:
                try:
                    self.driver.get(seed_url)
                    self._human_delay(0.5, 1.0)
                    current_seed = seed_url
                except Exception:
                    continue
            try:
                self.driver.add_cookie(cookie)
                applied += 1
            except Exception:
                continue

        self._log(f"Applied {applied}/{len(cookies)} cookies.")
        self.driver.get(self.BASE_URL)
        self._human_delay(2.0, 3.0)
        if not self._looks_logged_in():
            self._log("Cookies appear invalid or expired. Please save cookies again.", "ERROR")
            return False

        self._log("Logged in successfully using saved cookies.", "SUCCESS")
        return True

    def _check_profile_session(self) -> bool:
        if not self.driver:
            return False
        try:
            self.driver.get(self.BASE_URL)
            self._human_delay(1.5, 2.5)
            if self._looks_logged_in():
                self._log("Logged in via persistent browser profile.", "SUCCESS")
                return True
        except Exception:
            return False
        return False

    def save_cookies(self) -> bool:
        self.start_time = time.time()
        self._log("Starting Snapchat cookie save flow...")
        try:
            self._setup_driver()
            self.driver.get(self.LOGIN_URL)
            print("\n" + "=" * 74)
            print("Please log in to Snapchat in the opened browser window.")
            print("After login completes and your profile manager is visible, press Enter here.")
            print("=" * 74 + "\n")
            input("Press Enter after login is complete... ")

            self.driver.get(self.BASE_URL)
            self._human_delay(2.0, 3.0)
            if not self._looks_logged_in():
                self._log("Login not detected. Cookie save aborted.", "ERROR")
                return False

            cookies = self._collect_cookie_snapshot()
            if not cookies:
                self._log("No cookies could be captured from Snapchat session.", "ERROR")
                return False
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
            if self.profile_dir and self._check_profile_session():
                self.session_active = True
                return True
            if not self._load_cookies():
                if self.profile_dir and self._check_profile_session():
                    self.session_active = True
                    return True
                return False
            self.session_active = True
            return True
        except Exception as exc:
            self._log(f"Failed to start Snapchat session: {exc}", "ERROR")
            self.close_session()
            return False

    def _safe_click(self, element, label: str = "") -> bool:
        try:
            element.click()
            return True
        except Exception as exc:
            suffix = f" ({label})" if label else ""
            self._log(f"Click failed{suffix}: {exc}", "WARN")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_exc:
                self._log(f"JS click failed{suffix}: {js_exc}", "WARN")
                return False

    def _find_first_displayed(self, selectors: list[tuple[str, str]]):
        if not self.driver:
            return None
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
        return None

    def _wait_for_file_input(self, timeout: int = 120):
        selectors = [
            (By.CSS_SELECTOR, "input[type='file'][accept*='video']"),
            (By.CSS_SELECTOR, "input[type='file'][accept*='mp4']"),
            (By.CSS_SELECTOR, "input[type='file']"),
        ]
        end = time.time() + max(10, timeout)
        while time.time() < end:
            element = self._find_first_displayed(selectors)
            if element is not None:
                return element
            time.sleep(1.0)
        raise TimeoutException("Could not find Snapchat file input element.")

    def _open_composer(self):
        if not self.driver:
            raise RuntimeError("Driver is not started.")

        self.driver.get(self.BASE_URL)
        self._human_delay(1.0, 2.0)

        post_button_selectors = [
            (By.XPATH, "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'post to snapchat')]"),
            (By.XPATH, "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'+post to snapchat')]"),
            (By.XPATH, "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'post')]"),
        ]
        button = self._find_first_displayed(post_button_selectors)
        if button is not None:
            self._safe_click(button, "post_to_snapchat")
            self._human_delay(1.0, 2.0)
            try:
                return self._wait_for_file_input(timeout=60)
            except TimeoutException:
                pass

        for url in self.COMPOSE_URL_CANDIDATES:
            self.driver.get(url)
            self._human_delay(1.0, 2.0)
            try:
                return self._wait_for_file_input(timeout=25)
            except TimeoutException:
                continue

        raise TimeoutException("Could not open Snapchat composer/upload view.")

    def _set_caption_text(self, text: str):
        value = self._sanitize_text(text, max_len=160)
        if not value or not self.driver:
            return
        selectors = [
            (By.CSS_SELECTOR, "textarea"),
            (By.CSS_SELECTOR, "div[contenteditable='true']"),
            (By.CSS_SELECTOR, "[role='textbox']"),
        ]
        element = self._find_first_displayed(selectors)
        if element is None:
            self._log("Caption field not found; continuing without custom text.", "WARN")
            return
        try:
            element.click()
            self._human_delay(0.2, 0.4)
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.BACKSPACE)
            self._human_delay(0.2, 0.4)
            element.send_keys(value)
        except Exception as exc:
            self._log(f"Failed to set Snapchat caption text: {exc}", "WARN")

    def _set_spotlight_destination(self, spotlight_only: bool):
        if not spotlight_only or not self.driver:
            return
        selectors = [
            (By.XPATH, "//*[self::button or self::label or self::div][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'spotlight')]"),
            (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'spotlight')]"),
        ]
        element = self._find_first_displayed(selectors)
        if element is None:
            self._log("Could not explicitly confirm Spotlight selection; continuing.", "WARN")
            return
        self._safe_click(element, "spotlight_select")
        self._human_delay(0.4, 0.9)

    @staticmethod
    def _button_is_enabled(button) -> bool:
        if button is None:
            return False
        try:
            disabled_attr = str(button.get_attribute("aria-disabled") or "").strip().lower()
            if disabled_attr == "true":
                return False
            if button.get_attribute("disabled") is not None:
                return False
            return True
        except Exception:
            return False

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

    def _find_publish_buttons(self):
        if not self.driver:
            return []
        selectors = [
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'publish')]"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'post')]"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'submit')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ]
        buttons = []
        for by, selector in selectors:
            try:
                buttons.extend(self.driver.find_elements(by, selector))
            except Exception:
                continue
        return buttons

    def _wait_for_publish_ready(self, timeout: int = 300):
        end = time.time() + max(20, timeout)
        while time.time() < end:
            for button in self._find_publish_buttons():
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
                    return button
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
            time.sleep(1.2)
        raise TimeoutException("Snapchat publish button did not become ready in time.")

    def _click_publish_with_retry(self, timeout: int = 420, attempts: int = 10):
        deadline = time.time() + max(30, timeout)
        last_error = None
        max_attempts = max(1, int(attempts or 1))
        for attempt_index in range(1, max_attempts + 1):
            remaining = int(deadline - time.time())
            if remaining <= 0:
                break
            button = self._wait_for_publish_ready(timeout=max(20, remaining))
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                    button,
                )
                self._human_delay(0.1, 0.4)
                button.click()
                return
            except ElementClickInterceptedException as exc:
                last_error = exc
                self._log(
                    f"Publish click intercepted (attempt {attempt_index}/{max_attempts}); retrying...",
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
        raise TimeoutException("Timed out while trying to click Snapchat publish button.")

    def upload_post(
        self,
        video_path: str | Path,
        text: str,
        reuse_session: bool = True,
        spotlight_only: bool | None = None,
    ) -> bool:
        path = Path(video_path)
        if not path.exists():
            self._log(f"Video file not found: {path}", "ERROR")
            return False

        if not reuse_session or not self.session_active or not self.driver:
            if not self.start_session():
                return False

        only_spotlight = self.spotlight_only if spotlight_only is None else bool(spotlight_only)
        try:
            self._log(f"Opening Snapchat composer for {path.name}...")
            file_input = self._open_composer()
            file_input.send_keys(str(path.resolve()))
            self._log("Video attached. Waiting for Snapchat to process...")
            self._human_delay(2.0, 4.0)

            self._set_spotlight_destination(only_spotlight)
            self._set_caption_text(text)
            self._click_publish_with_retry(timeout=420, attempts=10)
            self._log("Snapchat post submitted. Waiting for completion...")
            self._human_delay(4.0, 7.0)
            return True
        except Exception as exc:
            self._log(f"Snapchat safe upload failed for {path.name}: {exc}", "ERROR")
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
    parser = argparse.ArgumentParser(description="Safe Snapchat uploader (Selenium)")
    parser.add_argument("--save-cookies", action="store_true", help="Login manually and save Snapchat cookies.")
    parser.add_argument("--cookies-file", default="snapchat_cookies.json", help="Path to Snapchat cookies JSON.")
    parser.add_argument(
        "--profile-dir",
        default="",
        help="Persistent Chrome user-data-dir for Snapchat session reuse.",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--video", default="", help="Video path to upload.")
    parser.add_argument("--text", default="", help="Post text for the upload.")
    parser.add_argument(
        "--allow-story",
        action="store_true",
        help="Disable Spotlight-only enforcement for this run.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    uploader = SafeSnapchatUploader(
        cookies_file=args.cookies_file,
        headless=args.headless,
        spotlight_only=not args.allow_story,
        profile_dir=args.profile_dir,
    )
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
