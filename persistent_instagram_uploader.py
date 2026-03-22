"""
Persistent Instagram Uploader
Keeps browser session open between uploads for daily automation
Handles 2FA manually once at the start, then reuses session all day
"""

import time
import json
import random
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

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


class PersistentInstagramUploader:
    """
    Instagram uploader that keeps browser session alive between uploads
    Perfect for daily automation - login once (with 2FA), upload multiple videos
    """

    def __init__(
        self,
        cookies_file: str = "instagram_cookies.json",
        headless: bool = False,
        download_dir: Optional[str] = None,
    ):
        """
        Initialize persistent uploader

        Args:
            cookies_file: Path to save/load cookies
            headless: Run browser in headless mode (not recommended for 2FA)
            download_dir: Directory for export downloads (defaults to Followers/exports)
        """
        self.cookies_file = cookies_file
        self.headless = headless
        base_dir = Path(__file__).resolve().parent
        if download_dir:
            download_path = Path(download_dir).expanduser()
            if not download_path.is_absolute():
                download_path = base_dir / download_path
            self.download_dir = download_path
        else:
            self.download_dir = base_dir / "Followers" / "exports"
        self.driver = None
        self.session_active = False
        self.owns_driver = True
        self.start_time = None
        self.export_requested_at = None
        self._temp_profile_dir = None
        fb_crosspost_env = os.getenv("IG_ENABLE_FB_CROSSPOST", "1").strip().lower()
        self.enable_facebook_crosspost = fb_crosspost_env not in {"0", "false", "no", "off"}
        self.mute_browser_audio = bool(
            getattr(config, "MUTE_BROWSER_AUDIO_DURING_UPLOADS", False)
        )
        try:
            self.page_load_timeout_seconds = max(
                30,
                int(getattr(config, "INSTAGRAM_PAGE_LOAD_TIMEOUT_SECONDS", 60) or 60),
            )
        except Exception:
            self.page_load_timeout_seconds = 60
        try:
            self.dom_ready_timeout_seconds = max(
                5,
                int(getattr(config, "INSTAGRAM_DOM_READY_TIMEOUT_SECONDS", 20) or 20),
            )
        except Exception:
            self.dom_ready_timeout_seconds = 20

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
        self._cleanup_temp_profile()
        attempts = 2
        last_error = None

        for attempt in range(1, attempts + 1):
            chrome_options = Options()
            chrome_options.page_load_strategy = "eager"

            if self.headless:
                chrome_options.add_argument("--headless=new")
                self._log("Running in headless mode (2FA may not work!)", "WARN")

            # Keep Selenium runs isolated from your normal Chrome profile.
            self._temp_profile_dir = tempfile.mkdtemp(prefix="ig_persistent_chrome_")
            chrome_options.add_argument(f"--user-data-dir={self._temp_profile_dir}")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-features=RendererCodeIntegrity")
            if self.mute_browser_audio:
                chrome_options.add_argument("--mute-audio")

            # Anti-detection
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            prefs = {}
            if self.download_dir:
                try:
                    self.download_dir.mkdir(parents=True, exist_ok=True)
                    prefs["download.default_directory"] = str(self.download_dir)
                    prefs["download.prompt_for_download"] = False
                    prefs["download.directory_upgrade"] = True
                    prefs["safebrowsing.enabled"] = True
                except Exception as e:
                    self._log(f"Could not prepare download dir {self.download_dir}: {e}", "WARN")

            if prefs:
                chrome_options.add_experimental_option("prefs", prefs)

            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(self.page_load_timeout_seconds)
                self.owns_driver = True
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                self._apply_runtime_audio_mute()
                self._configure_download_behavior()
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

    def _get_download_dirs(self) -> list[Path]:
        dirs = []
        if self.download_dir:
            dirs.append(self.download_dir)
        fallback = Path.home() / "Downloads"
        if fallback not in dirs:
            dirs.append(fallback)
        return [d for d in dirs if d.exists()]

    def _configure_download_behavior(self):
        if not self.driver or not self.download_dir:
            return
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._log(f"Could not prepare download dir {self.download_dir}: {e}", "WARN")
        try:
            self.driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": str(self.download_dir)},
            )
            self._log(f"Download directory set to {self.download_dir}")
        except Exception as e:
            self._log(
                f"Could not set Chrome download directory to {self.download_dir}: {e}",
                "WARN",
            )

    def _has_partial_download(self, recent_seconds: int = 3600) -> bool:
        now = time.time()
        for directory in self._get_download_dirs():
            for path in directory.glob("*"):
                if not path.is_file():
                    continue
                if not path.name.lower().endswith((".crdownload", ".part", ".tmp")):
                    continue
                try:
                    if now - path.stat().st_mtime <= recent_seconds:
                        return True
                except Exception:
                    continue
        return False

    def _is_logged_in(self) -> bool:
        """Best-effort check for an authenticated Instagram session."""
        try:
            if self.driver.find_elements(By.NAME, "username") or self.driver.find_elements(By.NAME, "password"):
                return False

            logged_in_markers = [
                "//a[contains(@href, '/direct/inbox')]",
                "//a[contains(@href, '/accounts/edit/')]",
                "//a[contains(@href, '/explore')]",
                "//a[contains(@href, '/create')]",
                "//svg[@aria-label='Home']",
                "//a[@aria-label='Home']",
            ]
            for selector in logged_in_markers:
                if self.driver.find_elements(By.XPATH, selector):
                    return True

            current_url = (self.driver.current_url or "").lower()
            if "instagram.com" in current_url and "login" not in current_url:
                return True
        except Exception as e:
            self._log(f"Login state check failed: {e}", "WARN")
        return False

    def attach_existing_driver(self, driver):
        """Attach an existing Selenium driver and reuse its session."""
        self.driver = driver
        self.session_active = True
        self.owns_driver = False
        self.start_time = time.time()
        self._apply_runtime_audio_mute()
        self._configure_download_behavior()

    def _human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _stop_page_load(self):
        """Best-effort stop for pages that keep loading indefinitely."""
        if not self.driver:
            return

        try:
            self.driver.execute_cdp_cmd("Page.stopLoading", {})
            return
        except Exception:
            pass

        try:
            self.driver.execute_script("window.stop();")
        except Exception:
            pass

    def _wait_for_dom_ready(self, timeout_seconds: Optional[int] = None) -> bool:
        """Treat Instagram as usable once the DOM is interactive."""
        if not self.driver:
            return False

        timeout = timeout_seconds or self.dom_ready_timeout_seconds
        deadline = time.time() + timeout
        last_state = None

        while time.time() < deadline:
            try:
                last_state = str(
                    self.driver.execute_script("return document.readyState") or ""
                ).strip().lower()
            except Exception:
                last_state = None

            if last_state in {"interactive", "complete"}:
                return True
            time.sleep(0.25)

        if last_state:
            self._log(
                f"Document readyState stayed at '{last_state}' for {timeout}s.",
                "WARN",
            )
        return False

    def _run_page_load_action(self, action, label: str) -> bool:
        """Run a navigation/refresh action without requiring a full network-idle load."""
        if not self.driver:
            raise RuntimeError("Chrome driver is not initialized.")

        timed_out = False
        try:
            action()
        except TimeoutException:
            timed_out = True
        except WebDriverException as exc:
            message = str(exc)
            if "Timed out receiving message from renderer" in message or "timeout:" in message.lower():
                timed_out = True
            else:
                raise

        if timed_out:
            self._log(
                f"{label} hit the Selenium page-load timeout; stopping the load and continuing.",
                "WARN",
            )
            self._stop_page_load()

        ready = self._wait_for_dom_ready()
        if not ready:
            self._log(
                f"{label} never reached an interactive DOM state; continuing with best-effort page state.",
                "WARN",
            )
        return ready

    def _navigate_to(self, url: str, label: str) -> bool:
        return self._run_page_load_action(lambda: self.driver.get(url), label)

    def _refresh_page(self, label: str) -> bool:
        return self._run_page_load_action(self.driver.refresh, label)

    def _safe_click(self, element, label: str = "") -> bool:
        try:
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    element,
                )
                self._human_delay(0.1, 0.3)
            except Exception:
                pass
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

    @staticmethod
    def _coerce_toggle_state(raw_value) -> Optional[bool]:
        if raw_value is None:
            return None
        value = str(raw_value).strip().lower()
        if value in {"true", "1", "on", "yes", "checked", "selected"}:
            return True
        if value in {"false", "0", "off", "no", "unchecked", "unselected"}:
            return False
        return None

    def _read_toggle_state(self, toggle) -> Optional[bool]:
        attrs = ("aria-checked", "aria-pressed", "data-checked", "checked")
        for attr in attrs:
            state = self._coerce_toggle_state(toggle.get_attribute(attr))
            if state is not None:
                return state
        try:
            tag = (toggle.tag_name or "").lower()
            if tag == "input":
                return bool(toggle.is_selected())
        except Exception:
            pass
        return None

    def _enable_facebook_crosspost_toggle(self) -> bool:
        if not self.enable_facebook_crosspost:
            self._log("Facebook cross-post toggle disabled via IG_ENABLE_FB_CROSSPOST", "INFO")
            return False

        self._log("Checking for Facebook cross-post toggle...")
        lower = "translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
        aria_lower = "translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
        toggle_relative = (
            ".//*[@role='switch' or @role='checkbox' or "
            "self::input[@type='checkbox'] or self::button[@role='switch'] or self::button[@role='checkbox']]"
        )

        row_selectors = [
            f"//*[(@role='row' or @role='button' or self::div or self::li or self::label) and contains({lower}, 'facebook')]",
            f"//*[(@role='switch' or @role='checkbox') and contains({aria_lower}, 'facebook')]",
        ]

        candidates = []
        for selector in row_selectors:
            try:
                candidates.extend(self.driver.find_elements(By.XPATH, selector))
            except Exception:
                continue

        for row in candidates:
            try:
                if not row.is_displayed():
                    continue
            except Exception:
                continue

            try:
                toggles = row.find_elements(By.XPATH, toggle_relative)
            except Exception:
                toggles = []

            if not toggles:
                if (row.get_attribute("role") or "").lower() in {"switch", "checkbox"}:
                    toggles = [row]

            for toggle in toggles:
                try:
                    if not toggle.is_displayed():
                        continue
                except Exception:
                    continue

                state = self._read_toggle_state(toggle)
                if state is True:
                    self._log("Facebook cross-post is already enabled.")
                    return True
                if state is False:
                    if not self._safe_click(toggle, "facebook crosspost toggle"):
                        continue
                    self._human_delay(0.4, 1.0)
                    state_after = self._read_toggle_state(toggle)
                    if state_after is False:
                        self._log("Facebook cross-post toggle click did not enable it.", "WARN")
                        continue
                    self._log("Enabled Facebook cross-post toggle.")
                    return True

        self._log("Facebook cross-post toggle not found on this publish screen.", "WARN")
        return False

    def _attempt_cover_selection(self) -> bool:
        self._log("Checking for cover/thumbnail options...")
        try:
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

                    self._log("Looking for thumbnail slider...")
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains

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
                            actions = ActionChains(self.driver)
                            actions.move_to_element(slider).perform()
                            self._human_delay(0.5, 1)
                            actions.click().perform()
                            self._log("Selected middle frame of video for thumbnail")
                            self._human_delay(1, 2)
                        else:
                            self._log("No slider found, using default frame")

                    except Exception as slider_error:
                        self._log(f"Could not adjust slider: {slider_error}")

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
                self._log("No cover selection option - using default thumbnail")
            return False

        except Exception as e:
            self._log(f"Cover selection skipped - using default thumbnail: {e}", "WARN")
            return False

    def _ci_contains(self, text: str) -> str:
        lowered = text.lower()
        return (
            "contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
            f"'{lowered}')"
        )

    def _ci_contains_word(self, text: str) -> str:
        lowered = " ".join(text.lower().split())
        return (
            "contains(concat(' ', translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), ' '), "
            f"' {lowered} ')"
        )

    def _click_first(self, selectors: list[str], timeout: int = 5, label: str = "") -> bool:
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if self._safe_click(element, label or selector):
                    return True
            except TimeoutException:
                continue
            except Exception as e:
                self._log(f"Click failed for selector {selector}: {e}", "WARN")
                continue
        return False

    def _click_by_text(
        self,
        text: str,
        timeout: int = 5,
        label: str = "",
        whole_word: bool = False,
    ) -> bool:
        ci = self._ci_contains_word(text) if whole_word else self._ci_contains(text)
        selectors = [
            f"//button[{ci}]",
            f"//*[@role='button' and {ci}]",
            f"//div[@role='button' and {ci}]",
            f"//a[{ci}]",
            f"//*[@role='link' and {ci}]",
            f"//*[self::span or self::div or self::a][{ci}]/ancestor::button[1]",
            f"//*[self::span or self::div or self::a][{ci}]/ancestor::*[@role='button'][1]",
            f"//*[self::span or self::div or self::a][{ci}]/ancestor::a[1]",
            f"//*[self::span or self::div or self::a][{ci}]/ancestor::*[@role='link'][1]",
        ]
        return self._click_first(selectors, timeout=timeout, label=label or text)

    def _click_all_by_text(self, text: str, timeout: int = 3, max_passes: int = 4) -> int:
        ci = self._ci_contains(text)
        selectors = [
            f"//button[{ci}]",
            f"//*[@role='button' and {ci}]",
            f"//a[{ci}]",
            f"//*[@role='link' and {ci}]",
        ]
        total_clicked = 0
        for _ in range(max_passes):
            elements = []
            for selector in selectors:
                try:
                    elements.extend(
                        WebDriverWait(self.driver, timeout).until(
                            EC.presence_of_all_elements_located((By.XPATH, selector))
                        )
                    )
                except TimeoutException:
                    continue

            if not elements:
                break

            clicked_this_pass = 0
            for element in elements:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    self._human_delay(0.2, 0.5)
                    if self._safe_click(element, f"{text}"):
                        clicked_this_pass += 1
                        total_clicked += 1
                        self._human_delay(0.3, 0.8)
                except Exception:
                    continue

            if clicked_this_pass == 0:
                break

        return total_clicked

    def _click_by_href_fragment(self, fragment: str, timeout: int = 5, label: str = "") -> bool:
        fragment = fragment.lower()
        selectors = [
            "//a[contains(translate(@href, "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
            f"'{fragment}')]",
            "//*[@role='link' and contains(translate(@href, "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
            f"'{fragment}')]",
        ]
        return self._click_first(selectors, timeout=timeout, label=label or fragment)

    def _wait_for_any_text(self, texts: list[str], timeout: int = 8) -> bool:
        end_time = time.time() + timeout
        while time.time() < end_time:
            for text in texts:
                if not text:
                    continue
                ci = self._ci_contains(text)
                selectors = [
                    f"//*[self::h1 or self::h2 or self::h3 or self::span or self::div][{ci}]",
                    f"//*[@role='status' and {ci}]",
                    f"//*[@aria-live and {ci}]",
                ]
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if any(el.is_displayed() for el in elements):
                            return True
                    except Exception:
                        continue
            time.sleep(0.4)
        return False

    def _open_export_info_page(
        self,
        account_center_url: str,
        info_permissions_label: str,
        export_info_label: str,
    ) -> bool:
        if not account_center_url:
            account_center_url = "https://accountscenter.instagram.com/"

        self._log("Opening Account Center...")
        self._navigate_to(account_center_url, "Instagram Account Center navigation")
        self._human_delay(3, 5)

        info_labels = [
            info_permissions_label,
            "Your information and permissions",
            "Your information",
            "Information and permissions",
            "Information",
            "Your info",
        ]
        info_clicked = False
        for label in info_labels:
            if label and self._click_by_text(label, timeout=6, label=f"info:{label}"):
                info_clicked = True
                break

        if not info_clicked:
            if self._click_by_href_fragment("info_and_permissions", timeout=6, label="info:href"):
                info_clicked = True
            elif self._click_by_href_fragment("your_information", timeout=6, label="info:href"):
                info_clicked = True

        if not info_clicked:
            self._log("Could not find info/permissions section", "ERROR")
            return False
        self._human_delay(1, 2)

        export_labels = [
            export_info_label,
            "Export your information",
            "Export information",
            "Download your information",
            "Download your info",
            "Download information",
            "Export info",
        ]
        export_clicked = False
        for label in export_labels:
            if label and self._click_by_text(label, timeout=6, label=f"export:{label}"):
                export_clicked = True
                break
        if not export_clicked:
            if self._click_by_href_fragment("download", timeout=6, label="export:href"):
                export_clicked = True
            elif self._click_by_href_fragment("export", timeout=6, label="export:href"):
                export_clicked = True
        if not export_clicked:
            self._log("Could not find export information entry", "ERROR")
            return False
        self._human_delay(2, 3)
        return True

    def _click_download_button(self) -> bool:
        return self._click_latest_download_button()

    def _click_available_download(self) -> bool:
        return self._click_latest_download_button(context_hint="available downloads")

    def _click_latest_download_button(
        self,
        context_hint: Optional[str] = None,
        min_timestamp=None,
    ) -> bool:
        buttons = self._collect_download_buttons()
        if not buttons:
            return False

        if min_timestamp is None:
            min_timestamp = self.export_requested_at
        try:
            if min_timestamp is not None:
                import datetime

                if isinstance(min_timestamp, datetime.datetime):
                    min_epoch = min_timestamp.timestamp()
                else:
                    min_epoch = float(min_timestamp)
            else:
                min_epoch = None
        except Exception:
            min_epoch = None

        scored = []
        for idx, btn in enumerate(buttons):
            try:
                if not btn.is_displayed():
                    continue
            except Exception:
                continue

            context_text = self._get_button_context_text(btn)
            lower = context_text.lower()
            if context_hint and context_hint.lower() not in lower:
                continue

            ts = self._parse_export_timestamp(context_text)
            if ts is not None:
                ts_value = ts
            else:
                ts_value = -1.0

            if min_epoch is not None and ts_value >= 0 and ts_value < min_epoch:
                continue

            priority = 0
            if "ready to download" in lower or "available to download" in lower:
                priority += 100
            if "export" in lower:
                priority += 10
            if context_hint and context_hint.lower() in lower:
                priority += 5

            scored.append(((priority, ts_value, idx), btn))

        if not scored:
            return False

        scored.sort(key=lambda item: item[0], reverse=True)
        _, chosen = scored[0]
        return self._safe_click(chosen, "download latest")

    def _collect_download_buttons(self):
        selectors = [
            "//*[@role='button' and normalize-space(.)='Download']",
            "//button[normalize-space(.)='Download']",
            "//*[@role='button' and normalize-space(.)='Download file']",
            "//button[normalize-space(.)='Download file']",
            "//*[@role='button' and normalize-space(.)='Download ZIP']",
            "//button[normalize-space(.)='Download ZIP']",
            "//*[@role='link' and normalize-space(.)='Download']",
            "//a[normalize-space(.)='Download']",
            "//*[@aria-label='Download']",
            "//*[@aria-label='Download file']",
        ]
        buttons = []
        for selector in selectors:
            try:
                buttons.extend(self.driver.find_elements(By.XPATH, selector))
            except Exception:
                continue

        unique = []
        seen = set()
        for btn in buttons:
            try:
                key = btn.id
            except Exception:
                key = id(btn)
            if key in seen:
                continue
            seen.add(key)
            unique.append(btn)
        return unique

    def _get_button_context_text(self, button, max_levels: int = 6) -> str:
        texts = []
        try:
            if button.text:
                texts.append(button.text)
        except Exception:
            pass
        node = button
        for _ in range(max_levels):
            try:
                node = node.find_element(By.XPATH, "..")
            except Exception:
                break
            try:
                text = node.text
            except Exception:
                text = ""
            if text:
                texts.append(text)
        return "\n".join(texts)

    def _parse_export_timestamp(self, text: str):
        if not text:
            return None
        import datetime
        import re

        lower = text.lower()
        now = datetime.datetime.now()

        if "just now" in lower or "moments ago" in lower:
            return now.timestamp()

        rel_match = re.search(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", lower)
        if rel_match:
            value = int(rel_match.group(1))
            unit = rel_match.group(2)
            if unit == "minute":
                return (now - datetime.timedelta(minutes=value)).timestamp()
            if unit == "hour":
                return (now - datetime.timedelta(hours=value)).timestamp()
            if unit == "day":
                return (now - datetime.timedelta(days=value)).timestamp()
            if unit == "week":
                return (now - datetime.timedelta(weeks=value)).timestamp()
            if unit == "month":
                return (now - datetime.timedelta(days=value * 30)).timestamp()
            if unit == "year":
                return (now - datetime.timedelta(days=value * 365)).timestamp()

        if "yesterday" in lower:
            return (now - datetime.timedelta(days=1)).timestamp()
        if "today" in lower:
            return now.timestamp()

        month_map = {
            "jan": 1, "january": 1,
            "feb": 2, "february": 2,
            "mar": 3, "march": 3,
            "apr": 4, "april": 4,
            "may": 5,
            "jun": 6, "june": 6,
            "jul": 7, "july": 7,
            "aug": 8, "august": 8,
            "sep": 9, "sept": 9, "september": 9,
            "oct": 10, "october": 10,
            "nov": 11, "november": 11,
            "dec": 12, "december": 12,
        }

        date_match = re.search(
            r"\b([a-z]+)\s+(\d{1,2}),\s*(\d{4})\b", lower
        )
        if date_match:
            month_name = date_match.group(1)
            day = int(date_match.group(2))
            year = int(date_match.group(3))
            month = month_map.get(month_name)
            if month:
                try:
                    return datetime.datetime(year, month, day).timestamp()
                except Exception:
                    pass

        return None

    def _click_download_in_modal(self) -> bool:
        dialog = self._find_dialog_by_text(["Download your files", "Download files"], timeout=2)
        if not dialog:
            return False
        try:
            buttons = dialog.find_elements(
                By.XPATH,
                ".//button[normalize-space(.)='Download'] | .//*[@role='button' and normalize-space(.)='Download']",
            )
            for btn in buttons:
                if btn.is_displayed() and self._safe_click(btn, "modal download"):
                    return True
        except Exception:
            return False
        return False

    def _handle_password_prompt(self, export_password: Optional[str]) -> bool:
        try:
            password_field = WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
            )
        except TimeoutException:
            return False
        if not password_field.is_displayed():
            return False

        password = export_password or os.getenv("IG_EXPORT_PASSWORD", "")
        if password:
            try:
                password_field.clear()
            except Exception:
                pass
            password_field.send_keys(password)
            self._human_delay(0.5, 1.0)
            self._click_by_text("Continue", timeout=4, label="download continue", whole_word=True)
            self._click_by_text("Confirm", timeout=4, label="download confirm", whole_word=True)
            return True

        input("Enter your Instagram password in the browser, then press Enter to continue...")
        return True

    def _list_download_files(self) -> set[Path]:
        files = set()
        for directory in self._get_download_dirs():
            files.update({p for p in directory.glob("*") if p.is_file()})
        return files

    def _wait_for_download(self, before_files: set[Path], timeout_seconds: int = 600) -> Optional[Path]:
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            files = []
            for directory in self._get_download_dirs():
                files.extend([p for p in directory.glob("*") if p.is_file()])
            completed = [
                p for p in files
                if not p.name.lower().endswith((".crdownload", ".part", ".tmp"))
            ]
            completed = [p for p in completed if p.suffix.lower() == ".zip"]
            new_files = [p for p in completed if p not in before_files]
            if new_files:
                newest = max(new_files, key=lambda p: p.stat().st_mtime)
                return newest
            time.sleep(2)
        return None

    def _is_download_after_request(self, download_path: Path) -> bool:
        if not self.export_requested_at:
            return True
        try:
            import datetime
            import re

            match = re.search(r"\d{4}-\d{2}-\d{2}", download_path.name)
            if not match:
                return True
            file_date = datetime.datetime.strptime(match.group(0), "%Y-%m-%d").date()
            if isinstance(self.export_requested_at, datetime.datetime):
                request_date = self.export_requested_at.date()
            else:
                request_date = datetime.datetime.fromtimestamp(
                    float(self.export_requested_at)
                ).date()
            return file_date >= request_date
        except Exception:
            return True

    def _extract_export_zip(self, zip_path: Path) -> Optional[Path]:
        if not zip_path.exists():
            self._log(f"Zip not found: {zip_path}", "ERROR")
            return None
        if zip_path.suffix.lower() != ".zip":
            self._log(f"Not a zip file: {zip_path}", "ERROR")
            return None
        if not self.download_dir:
            self._log("Download directory not configured.", "ERROR")
            return None

        extract_base = self.download_dir / zip_path.stem
        if extract_base.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            extract_base = self.download_dir / f"{zip_path.stem}_{timestamp}"
        try:
            extract_base.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_base)
        except Exception as e:
            self._log(f"Failed to extract zip: {e}", "ERROR")
            return None

        candidates = []
        for path in extract_base.rglob("followers_and_following"):
            if path.is_dir():
                candidates.append(path)

        if candidates:
            for candidate in candidates:
                if any(part.lower() == "connections" for part in candidate.parts):
                    return candidate
            return candidates[0]

        for file_path in extract_base.rglob("followers_1.json"):
            return file_path.parent

        self._log("Could not find followers_and_following folder in export.", "ERROR")
        return None

    def _append_followers_from_export_dir(self, export_dir: Path) -> bool:
        try:
            from append_new_followers import append_from_export_dir
        except Exception as e:
            self._log(f"Could not import append_new_followers: {e}", "ERROR")
            return False

        try:
            result = append_from_export_dir(str(export_dir))
            if result:
                self._log(
                    "Follower append complete: "
                    f"+{result.get('new', 0)} new, "
                    f"{result.get('total', 0)} total",
                    "INFO",
                )
            return True
        except Exception as e:
            self._log(f"Failed to append followers: {e}", "ERROR")
            return False

    def wait_for_export_ready_and_download(
        self,
        account_center_url: str,
        info_permissions_label: str,
        export_info_label: str,
        export_password: Optional[str] = None,
        max_wait_minutes: int = 90,
        poll_interval_seconds: int = 60,
    ) -> Optional[Path]:
        if not self.session_active:
            self._log("No active session! Call start_session() first.", "ERROR")
            return None

        if not self.download_dir:
            self._log("Download directory not configured.", "ERROR")
            return None

        max_wait_minutes = max(1, int(max_wait_minutes))
        poll_interval_seconds = max(10, int(poll_interval_seconds))
        before_files = self._list_download_files()
        deadline = time.time() + (max_wait_minutes * 60)
        attempt = 0

        self._log(f"Waiting up to {max_wait_minutes} minutes for export to be ready...")
        self._log(f"Download folder: {self.download_dir}")

        while time.time() < deadline:
            attempt += 1
            self._log(f"Checking export status (attempt {attempt})...")

            if self._has_partial_download():
                self._log("Download in progress; waiting for completion...", "INFO")
                downloaded = self._wait_for_download(before_files, timeout_seconds=600)
                if downloaded:
                    if not self._is_download_after_request(downloaded):
                        self._log(
                            f"Downloaded export is older than the request: {downloaded}",
                            "WARN",
                        )
                        before_files.add(downloaded)
                    else:
                        self._log(f"Download complete: {downloaded}", "INFO")
                        return downloaded
                self._log("Download still not detected; continuing checks.", "WARN")
                time.sleep(poll_interval_seconds)
                continue

            if not self._open_export_info_page(account_center_url, info_permissions_label, export_info_label):
                self._log("Could not open export page; retrying.", "WARN")
                time.sleep(poll_interval_seconds)
                continue

            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception:
                pass

            if self._click_download_button():
                self._log("Download clicked; waiting for file...")
                self._human_delay(1, 2)
                if self._click_download_in_modal():
                    self._human_delay(1, 2)
                self._handle_password_prompt(export_password)
                if self._click_download_in_modal():
                    self._human_delay(1, 2)
                downloaded = self._wait_for_download(before_files, timeout_seconds=600)
                if downloaded:
                    if not self._is_download_after_request(downloaded):
                        self._log(
                            f"Downloaded export is older than the request: {downloaded}",
                            "WARN",
                        )
                        before_files.add(downloaded)
                    else:
                        self._log(f"Download complete: {downloaded}", "INFO")
                        return downloaded
                self._log("Download not detected yet; will retry.", "WARN")
            elif self._click_available_download():
                self._human_delay(1, 2)
                if self._click_download_in_modal():
                    self._human_delay(1, 2)
                self._handle_password_prompt(export_password)
                if self._click_download_in_modal():
                    self._human_delay(1, 2)
                downloaded = self._wait_for_download(before_files, timeout_seconds=600)
                if downloaded:
                    if not self._is_download_after_request(downloaded):
                        self._log(
                            f"Downloaded export is older than the request: {downloaded}",
                            "WARN",
                        )
                        before_files.add(downloaded)
                    else:
                        self._log(f"Download complete: {downloaded}", "INFO")
                        return downloaded
                self._log("Download not detected yet; will retry.", "WARN")
            else:
                status_texts = [
                    "Requested",
                    "Preparing your information",
                    "Your information is being prepared for export",
                    "We're preparing your information",
                    "Export in progress",
                    "In progress",
                    "Export requested",
                    "Ready to download",
                    "Available to download",
                ]
                if self._wait_for_any_text(status_texts, timeout=4):
                    self._log("Export not ready yet; waiting...", "INFO")
                else:
                    self._log("No export status detected; waiting...", "INFO")

            time.sleep(poll_interval_seconds)

        return None

    def _find_dialog_by_text(self, texts: list[str], timeout: int = 3):
        for text in texts:
            if not text:
                continue
            ci = self._ci_contains(text)
            selectors = [
                f"//*[@role='dialog' and {ci}]",
                f"//*[@role='dialog']//*[self::h1 or self::h2 or self::h3 or self::div or self::span][{ci}]/ancestor::*[@role='dialog'][1]",
            ]
            for selector in selectors:
                try:
                    return WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                except TimeoutException:
                    continue
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//*[@role='dialog']"))
            )
        except TimeoutException:
            return None

    def _click_profile_in_dialog(self, dialog, profile_name: str) -> bool:
        if profile_name:
            ci = self._ci_contains(profile_name)
            selectors = [
                f".//*[@role='button' and {ci}]",
                f".//button[{ci}]",
                f".//a[{ci}]",
                f".//*[self::div or self::span][{ci}]/ancestor::*[@role='button'][1]",
                f".//*[self::div or self::span][{ci}]/ancestor::button[1]",
                f".//*[self::div or self::span][{ci}]/ancestor::a[1]",
                f".//*[self::div or self::span][{ci}]/ancestor::*[@tabindex='0'][1]",
                f".//*[@role='row' and {ci}]",
            ]
            for selector in selectors:
                try:
                    candidates = dialog.find_elements(By.XPATH, selector)
                    for candidate in candidates:
                        if candidate.is_displayed() and self._safe_click(candidate, "profile"):
                            return True
                except Exception:
                    continue

        try:
            instagram_rows = dialog.find_elements(
                By.XPATH,
                ".//*[@role='button' and .//*[contains(translate(., "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'instagram')]]"
            )
            if instagram_rows:
                mid = instagram_rows[len(instagram_rows) // 2]
                return self._safe_click(mid, "profile instagram fallback")
        except Exception:
            pass

        try:
            buttons = dialog.find_elements(By.XPATH, ".//*[@role='button']")
            if buttons:
                mid = buttons[len(buttons) // 2]
                return self._safe_click(mid, "profile fallback")
        except Exception:
            pass

        return False

    def _select_option_by_text(self, text: str, timeout: int = 5, label: str = "") -> bool:
        ci = self._ci_contains(text)
        selectors = [
            f"//*[@role='menuitemradio' and {ci}]",
            f"//*[@role='radio' and {ci}]",
            f"//*[@role='option' and {ci}]",
            f"//*[@role='button' and {ci}]",
            f"//button[{ci}]",
            f"//*[self::span or self::div or self::label][{ci}]/ancestor::label[1]",
            f"//*[self::span or self::div or self::label][{ci}]/ancestor::*[@role='button'][1]",
        ]
        return self._click_first(selectors, timeout=timeout, label=label or text)

    def _close_panel(self) -> bool:
        if self._click_by_text("Save", timeout=4, label="save", whole_word=True):
            return True
        if self._click_by_text("Done", timeout=4, label="done", whole_word=True):
            return True
        if self._click_by_text("Apply", timeout=4, label="apply", whole_word=True):
            return True
        if self._click_by_text("Next", timeout=4, label="next", whole_word=True):
            return True
        if self._click_by_text("Back", timeout=4, label="back", whole_word=True):
            return True
        back_selectors = [
            "//*[@aria-label='Back']",
            "//*[@aria-label='Close']",
            "//button[@aria-label='Back']",
            "//button[@aria-label='Close']",
        ]
        if self._click_first(back_selectors, timeout=3, label="back/close"):
            return True
        try:
            from selenium.webdriver.common.keys import Keys

            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            self._human_delay(0.3, 0.8)
            return True
        except Exception:
            return False

    def export_followers_from_account_center(
        self,
        profile_name: str,
        account_center_url: str = "https://accountscenter.instagram.com/",
        info_permissions_label: str = "Your information and permissions",
        export_info_label: str = "Export your information",
        export_to_device_label: str = "Export to device",
        date_range_label: str = "Last week",
        followers_label: str = "Followers and following",
        format_label: str = "JSON",
        media_quality_label: str = "Low",
        export_password: Optional[str] = None,
        wait_for_ready: bool = True,
        max_wait_minutes: int = 90,
        poll_interval_seconds: int = 60,
    ) -> bool:
        if not self.session_active:
            self._log("No active session! Call start_session() first.", "ERROR")
            return False

        self._log("=" * 60)
        self._log("ACCOUNT CENTER EXPORT FLOW")
        self._log("=" * 60)

        try:
            if not self._open_export_info_page(
                account_center_url=account_center_url,
                info_permissions_label=info_permissions_label,
                export_info_label=export_info_label,
            ):
                return False

            self._log("Looking for Create export...")
            create_clicked = self._click_by_text("Create export", timeout=6, label="create export")
            if create_clicked:
                self._human_delay(1, 2)

            self._log("Looking for profile picker...")
            profile_clicked = False
            export_to_device_clicked = False
            profile_dialog = self._find_dialog_by_text(
                ["Choose a profile", "Select a profile", "Choose profile", "Select profile"],
                timeout=3
            )
            if profile_dialog:
                self._log("Profile dialog detected")
                profile_clicked = self._click_profile_in_dialog(profile_dialog, profile_name)
                if not profile_clicked:
                    self._log("Profile click failed; select profile manually.", "WARN")
                    input("Select the profile in the browser, then press Enter to continue...")
                    profile_clicked = True
                self._human_delay(1, 2)

            self._log("Looking for export destination...")
            export_to_device_labels = [
                export_to_device_label,
                "Export to this device",
                "Export to device",
                "Export to your device",
                "Export to computer",
                "Export to your computer",
            ]
            for label in export_to_device_labels:
                if label and self._click_by_text(label, timeout=4, label=f"export:{label}"):
                    export_to_device_clicked = True
                    if not profile_clicked:
                        profile_clicked = True
                    break

            if not profile_clicked:
                self._log("Selecting export profile...")
                dialog = self._find_dialog_by_text(
                    ["Choose a profile", "Select a profile", "Choose profile", "Select profile"],
                    timeout=3
                )
                if dialog:
                    profile_clicked = self._click_profile_in_dialog(dialog, profile_name)
                if not profile_clicked:
                    if profile_name:
                        profile_clicked = self._click_by_text(profile_name, timeout=6, label="profile")
                if not profile_clicked:
                    self._log("Profile not found; select manually.", "WARN")
                    input("Select the profile in the browser, then press Enter to continue...")
                    profile_clicked = True

            if not profile_clicked:
                for label in export_to_device_labels:
                    if label and self._click_by_text(label, timeout=4, label=f"export:{label}"):
                        export_to_device_clicked = True
                        profile_clicked = True
                        break

            if not profile_clicked:
                self._log("Failed to select export profile", "ERROR")
                return False

            self._human_delay(1, 2)
            if not export_to_device_clicked:
                export_clicked = False
                for label in export_to_device_labels:
                    if label and self._click_by_text(label, timeout=8, label=f"export:{label}"):
                        export_clicked = True
                        break
                if not export_clicked:
                    self._log("Could not find export-to-device option", "ERROR")
                    return False

            self._human_delay(2, 3)
            if not self._click_by_text("Customize information", timeout=8):
                self._log("Could not open 'Customize information'", "ERROR")
                return False

            self._human_delay(1, 2)
            clear_labels = [
                "Clear all",
                "Deselect all",
                "Unselect all",
                "Uncheck all",
            ]
            cleared_count = 0
            for label in clear_labels:
                cleared_count += self._click_all_by_text(label, timeout=3, max_passes=6)
            if cleared_count == 0:
                self._log("Could not clear selections; continuing anyway.", "WARN")
            self._select_option_by_text(followers_label, timeout=5, label="followers and following")
            self._close_panel()

            self._human_delay(1, 2)
            if self._click_by_text("Date range", timeout=6, whole_word=True):
                if not self._select_option_by_text(date_range_label, timeout=5):
                    self._select_option_by_text("Last 7 days", timeout=5)
                self._close_panel()

            self._human_delay(1, 2)
            if self._click_by_text("Format", timeout=6, whole_word=True):
                self._select_option_by_text(format_label, timeout=5)
                self._close_panel()

            self._human_delay(1, 2)
            if self._click_by_text("Media quality", timeout=6, whole_word=True):
                if not self._select_option_by_text(media_quality_label, timeout=5):
                    self._select_option_by_text("Lower quality", timeout=5)
                self._close_panel()

            self._human_delay(1, 2)
            if not self._click_by_text("Start export", timeout=8):
                self._log("Could not find 'Start export'", "ERROR")
                return False
            try:
                import datetime

                self.export_requested_at = datetime.datetime.now()
                self._log(f"Export requested at {self.export_requested_at.isoformat(timespec='seconds')}")
            except Exception:
                self.export_requested_at = time.time()

            self._human_delay(1, 2)
            try:
                password_field = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
                )
                import getpass

                password = export_password or os.getenv("IG_EXPORT_PASSWORD", "")
                if not password:
                    password = getpass.getpass("Enter Instagram password (leave blank to type in browser): ")
                if password:
                    try:
                        password_field.clear()
                    except Exception:
                        pass
                    password_field.send_keys(password)
                    self._human_delay(1, 2)
                else:
                    input("Enter password in the browser, then press Enter to continue...")

                confirm_labels = [
                    "Continue",
                    "Confirm",
                    "Submit",
                    "Next",
                    "Start export",
                ]
                confirmed = False
                for label in confirm_labels:
                    if self._click_by_text(label, timeout=8, label=f"export:{label}", whole_word=True):
                        confirmed = True
                        break
                if not confirmed:
                    self._log("Could not find confirm button; continue manually.", "WARN")
                    input("Click the confirm button in the browser, then press Enter to continue...")
            except TimeoutException:
                self._log("Password prompt not detected; export may already be in progress.", "WARN")

            self._human_delay(2, 3)
            status_texts = [
                "Requested",
                "Your information is being prepared for export",
                "Preparing your information",
                "We're preparing your information",
                "Export in progress",
                "In progress",
                "Export started",
                "Export requested",
                "We'll notify you",
                "We will notify you",
                "Export created",
            ]
            if not self._wait_for_any_text(status_texts, timeout=10):
                self._log("Export status not detected; verify in browser.", "WARN")
                input("If you see a final confirm/export status, click it now, then press Enter...")

            if wait_for_ready:
                self._log("Waiting for export to finish before downloading...")
                download_path = self.wait_for_export_ready_and_download(
                    account_center_url=account_center_url,
                    info_permissions_label=info_permissions_label,
                    export_info_label=export_info_label,
                    export_password=export_password,
                    max_wait_minutes=max_wait_minutes,
                    poll_interval_seconds=poll_interval_seconds,
                )
                if not download_path:
                    self._log("Export did not become ready before timeout.", "WARN")
                    return False
                self._log(f"Export downloaded: {download_path}", "INFO")
                if download_path.suffix.lower() == ".zip":
                    export_dir = self._extract_export_zip(download_path)
                    if not export_dir:
                        return False
                    if not self._append_followers_from_export_dir(export_dir):
                        return False
                else:
                    self._log("Downloaded export is not a zip; skipping auto-append.", "WARN")

            self._log("Export flow completed.", "INFO")
            return True

        except Exception as e:
            self._log(f"Export flow failed: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

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
            self._navigate_to("https://www.instagram.com", "Instagram cookie attach page")
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

                    self._refresh_page("Instagram cookie refresh")
                    self._human_delay(2, 4)
                    self._log("Cookies applied")

                except Exception as e:
                    self._log(f"Could not load cookies: {e}", "WARN")

            # Check if we're already logged in (skip manual prompt when cookies work)
            self._log("STEP 3: Checking login status...")

            # Wait for initial page load
            self._human_delay(3, 5)

            if self._is_logged_in():
                self._log("Already logged in; skipping manual verification.")
            else:
                self._log("Manual login verification required...")
                self._handle_manual_login()

            # Verify we're on the home feed
            self._log("STEP 4: Verifying we're on Instagram home...")
            self._navigate_to("https://www.instagram.com/", "Instagram home verification")
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
        print("=" * 70)
        print("  IMPORTANT: DO NOT TOUCH THE BROWSER YET!")
        print("=" * 70)
        print()
        print("The Chrome browser is open showing Instagram.")
        print()
        print("WAIT for the script to ask you to interact!")
        print()
        print("In a few seconds, you'll be prompted to:")
        print("  1. Login with your credentials (if not logged in)")
        print("  2. Enter your 2FA code (if prompted)")
        print("  3. Complete any security verification")
        print()
        print("=" * 70)
        print()

        # Give page time to fully load before user interacts
        self._log("Waiting for page to fully load...")
        self._human_delay(5, 7)

        print()
        print("=" * 70)
        print("  NOW YOU CAN INTERACT WITH THE BROWSER")
        print("=" * 70)
        print()
        print("Please complete the following in the browser:")
        print("  1. Login with username + password (if needed)")
        print("  2. Enter 2FA code (if prompted)")
        print("  3. Click through any popups/notifications")
        print("  4. Wait until you see your Instagram home feed")
        print()
        print("IMPORTANT:")
        print("  - Take your time, no rush")
        print("  - Don't close or refresh the browser")
        print("  - Wait until you see the home feed with posts")
        print()
        print("=" * 70)
        print()

        input("Press Enter ONLY AFTER you see your Instagram home feed... ")

        self._log("Thank you! Continuing automation...")
        self._log("Waiting for session to stabilize...")
        self._human_delay(3, 5)

    def upload_video(self, video_path: str, caption: str = "", game_mode: Optional[str] = None) -> bool:
        """
        Upload a video using the existing session

        Args:
            video_path: Path to video file
            caption: Caption text
            game_mode: Optional explicit game mode (used for aspect ratio selection)

        Returns:
            True if upload successful
        """
        if not self.session_active:
            self._log("No active session! Call start_session() first.", "ERROR")
            return False

        upload_start = time.time()
        video_path = Path(video_path).resolve()
        target_aspect_ratio, resolved_game_mode = self._resolve_target_aspect_ratio(video_path, game_mode)

        self._log("="*50)
        self._log(f"UPLOADING: {video_path.name}")
        self._log("="*50)

        if not video_path.exists():
            self._log(f"Video not found: {video_path}", "ERROR")
            return False

        self._log(f"Video size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
        self._log(f"Caption: {caption[:50]}{'...' if len(caption) > 50 else ''}")
        self._log(f"Game mode: {resolved_game_mode or 'unknown'} | Target aspect: {target_aspect_ratio}")

        try:
            # Navigate to home (in case we're somewhere else)
            self._log("Navigating to Instagram home...")
            self._navigate_to("https://www.instagram.com/", "Instagram upload home navigation")
            self._log("Waiting for page to fully load...")
            self._human_delay(4, 6)  # Longer wait to ensure page is stable

            # Click Create button
            self._log("Looking for Create button...")
            create_selectors = [
                # Text-based selectors
                "//span[contains(text(), 'Create')]",
                "//span[text()='Create']",
                "//div[contains(text(), 'Create')]",
                "//a[contains(text(), 'Create')]",

                # Href-based selectors
                "//a[contains(@href, '/create/')]",
                "//a[@href='#']//span[contains(text(), 'Create')]",

                # Aria-label selectors
                "//*[@aria-label='New post']",
                "//*[@aria-label='Create']",
                "//*[@aria-label='Create Post']",
                "//svg[@aria-label='New post']/..",
                "//svg[@aria-label='Create']/..",

                # SVG-based (Instagram uses SVG icons)
                "//svg[contains(@aria-label, 'Create')]//ancestor::*[@role='link']",
                "//svg[contains(@aria-label, 'New')]//ancestor::*[@role='link']",

                # Generic clickable with Create
                "//*[@role='link'][contains(., 'Create')]",
                "//*[@role='button'][contains(., 'Create')]",

                # Plus icon (Instagram's create button is often a + icon)
                "//*[name()='svg']/*[name()='path' and contains(@d, 'M12 2')]//ancestor::a",

                # Fallback: any clickable element with "Create"
                "//*[contains(@class, 'create') or contains(@class, 'Create')]",
            ]

            create_button = None
            for selector in create_selectors:
                try:
                    self._log(f"  Trying selector: {selector[:50]}...")
                    create_button = WebDriverWait(self.driver, 10).until(  # Increased timeout
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self._log(f"  Found Create button!")
                    break
                except TimeoutException:
                    self._log(f"  Not found with this selector")
                    continue

            if not create_button:
                self._log("Could not find Create button after trying all selectors", "ERROR")
                self._log("HINT: Make sure you're logged in and on the home feed", "ERROR")
                return False

            self._log("Clicking Create button...")
            self._safe_click(create_button, "create")
            self._log("Waiting for upload dialog...")
            self._human_delay(3, 5)  # Longer wait for dialog to appear

            # Select media from computer
            self._log("Uploading video file...")
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(str(video_path))
            self._log("File path sent to input, waiting for upload...")
            self._human_delay(3, 5)

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
                        self._safe_click(ok_button, "reels ok")
                        self._human_delay(1, 2)
                        break
                    except TimeoutException:
                        continue
            except Exception:
                self._log("No Reels popup found (OK)")

            # Select upload framing per game mode.
            self._select_upload_aspect_ratio(target_aspect_ratio)

            # Click Next button to proceed (there might be multiple Next buttons)
            self._log("Clicking Next button...")
            next_selectors = [
                "//button[contains(text(), 'Next')]",
                "//button[text()='Next']",
                "//div[contains(text(), 'Next')]",
                "//*[@role='button' and contains(text(), 'Next')]"
            ]

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

            # Enter caption
            if caption:
                self._log("Entering caption...")
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
                            break
                        except TimeoutException:
                            continue

                    if caption_field:
                        caption_field.click()
                        self._human_delay(0.5, 1)
                        try:
                            caption_field.clear()
                        except Exception:
                            pass
                        caption_field.send_keys(caption)
                        self._human_delay(2, 3)
                    else:
                        self._log("Could not find caption field (skipping)", "WARN")
                except Exception as e:
                    self._log(f"Error adding caption: {e}", "WARN")

            # Click Share button
            self._log("Clicking Share button...")
            share_selectors = [
                "//button[contains(text(), 'Share')]",
                "//button[text()='Share']",
                "//div[contains(text(), 'Share') and @role='button']",
                "//*[@role='button' and contains(text(), 'Share')]"
            ]

            share_button = None
            for selector in share_selectors:
                try:
                    share_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not share_button:
                self._log("Could not find Share button - upload failed", "ERROR")
                return False

            if not self._safe_click(share_button, "share"):
                self._log("Share click failed - upload failed", "ERROR")
                return False

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
            if self.owns_driver:
                self.driver.quit()
            self.driver = None
            self.session_active = False
            self._log("Browser closed. Session ended.")
        self._cleanup_temp_profile()

    def __del__(self):
        """Cleanup on deletion"""
        if self.driver and getattr(self, "owns_driver", True):
            try:
                self.driver.quit()
            except:
                pass
        self._cleanup_temp_profile()


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
