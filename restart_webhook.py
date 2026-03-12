#!/usr/bin/env python3
"""
Restart the webhook server and tunnel with health-gated sequencing.

Usage:
    python restart_webhook.py
    python restart_webhook.py --hidden
    python restart_webhook.py --force-restart
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Iterable

import config

try:
    import psutil  # Optional; used for robust PID/command-line inspection.
except Exception:
    psutil = None


BASE_DIR = Path(__file__).resolve().parent
WEBHOOK_SCRIPT = BASE_DIR / "instagram_webhook.py"
WEBHOOK_PORT = int(getattr(config, "WEBHOOK_SERVER_PORT", 5000))
LOG_DIR = BASE_DIR / "logs" / "webhook_services"
LOCK_PATH = LOG_DIR / "restart_webhook.lock"
DISCORD_AUTO_START = bool(getattr(config, "AUTO_START_DISCORD_BOT", False))
DISCORD_SCRIPT = BASE_DIR / str(getattr(config, "DISCORD_BOT_SCRIPT", "discord_bot/bot.py"))
DISCORD_PID_FILE = Path(str(getattr(config, "DISCORD_BOT_PID_FILE", "discord_bot/discord_bot.pid")))
if not DISCORD_PID_FILE.is_absolute():
    DISCORD_PID_FILE = BASE_DIR / DISCORD_PID_FILE
DISCORD_LOG_DIR = Path(str(getattr(config, "DISCORD_BOT_LOG_DIR", "logs/discord_bot")))
if not DISCORD_LOG_DIR.is_absolute():
    DISCORD_LOG_DIR = BASE_DIR / DISCORD_LOG_DIR
DISCORD_LOG_PATH = DISCORD_LOG_DIR / "discord_bot.log"

NGROK_EXE = os.getenv("NGROK_EXE", getattr(config, "NGROK_PATH", "ngrok"))
NGROK_API_PORT = int(getattr(config, "NGROK_API_PORT", 4040))
NGROK_LOG_PATH = LOG_DIR / "ngrok.log"

TUNNEL_PROVIDER = str(getattr(config, "TUNNEL_PROVIDER", "ngrok")).strip().lower()
if TUNNEL_PROVIDER in ("cloudflare", "cloudflared"):
    TUNNEL_PROVIDER = "cloudflared"
elif TUNNEL_PROVIDER != "ngrok":
    print(f"Warning: Unknown TUNNEL_PROVIDER '{TUNNEL_PROVIDER}', defaulting to ngrok.")
    TUNNEL_PROVIDER = "ngrok"

CLOUDFLARED_EXE = os.getenv("CLOUDFLARED_EXE", getattr(config, "CLOUDFLARED_PATH", "cloudflared"))
CLOUDFLARED_URL = str(getattr(config, "CLOUDFLARED_URL", f"http://localhost:{WEBHOOK_PORT}")).strip()
CLOUDFLARED_METRICS_PORT = int(getattr(config, "CLOUDFLARED_METRICS_PORT", 49312))
CLOUDFLARED_LOG_LEVEL = str(getattr(config, "CLOUDFLARED_LOG_LEVEL", "info")).strip()
CLOUDFLARED_NO_AUTOUPDATE = bool(getattr(config, "CLOUDFLARED_NO_AUTOUPDATE", True))
CLOUDFLARED_PROTOCOL = str(getattr(config, "CLOUDFLARED_PROTOCOL", "")).strip().lower()
CLOUDFLARED_EDGE_IP_VERSION = str(getattr(config, "CLOUDFLARED_EDGE_IP_VERSION", "")).strip()
CLOUDFLARED_TUNNEL_MODE = str(getattr(config, "CLOUDFLARED_TUNNEL_MODE", "quick")).strip().lower()
CLOUDFLARED_TUNNEL_NAME = str(getattr(config, "CLOUDFLARED_TUNNEL_NAME", "")).strip()
CLOUDFLARED_HOSTNAME = str(getattr(config, "CLOUDFLARED_HOSTNAME", "")).strip()
CLOUDFLARED_CONFIG_PATH = str(getattr(config, "CLOUDFLARED_CONFIG_PATH", "")).strip()
CLOUDFLARED_LOG_PATH = LOG_DIR / "cloudflared.log"


def log(message: str, level: str = "INFO") -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{stamp} [{level}] {message}")


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _normalize_path_fragment(value: str) -> str:
    return str(value or "").replace("\\", "/").lower()


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port accepts a connection."""
    if port <= 0:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def is_pid_running(pid: int) -> bool:
    """Best-effort check if PID exists."""
    pid = _safe_int(pid, 0)
    if pid <= 0:
        return False

    if psutil is not None:
        try:
            return psutil.pid_exists(pid)
        except Exception:
            pass

    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in (result.stdout or "")
        except Exception:
            return False

    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _listening_pids_via_psutil(port: int) -> set[int]:
    pids: set[int] = set()
    if psutil is None or port <= 0:
        return pids
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status != psutil.CONN_LISTEN:
                continue
            if not conn.laddr:
                continue
            if _safe_int(conn.laddr.port, -1) != port:
                continue
            if conn.pid:
                pids.add(int(conn.pid))
    except Exception:
        return set()
    return pids


def _listening_pids_via_netstat(port: int) -> set[int]:
    pids: set[int] = set()
    if port <= 0:
        return pids
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return pids

    target = str(port)
    for line in (result.stdout or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split()
        if len(parts) < 5:
            continue
        local_addr = parts[1]
        state = parts[3].upper()
        pid_text = parts[-1]
        if state != "LISTENING":
            continue
        if local_addr.rsplit(":", 1)[-1] != target:
            continue
        if pid_text.isdigit():
            pids.add(int(pid_text))
    return pids


def list_listening_pids(port: int) -> set[int]:
    """Return all PIDs listening on a specific port."""
    pids = _listening_pids_via_psutil(port)
    if pids:
        return pids
    return _listening_pids_via_netstat(port)


def find_pids_by_cmdline(
    required_terms: Iterable[str],
    *,
    process_name_hint: str = "",
) -> set[int]:
    """
    Find PIDs where command line contains all required terms.
    Falls back to empty set when command-line inspection is unavailable.
    """
    required = [str(t).strip().lower() for t in required_terms if str(t).strip()]
    if not required:
        return set()
    if psutil is None:
        return set()

    hint = str(process_name_hint or "").strip().lower()
    found: set[int] = set()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            if pid <= 0 or pid == os.getpid():
                continue

            name = str(proc.info.get("name") or "").lower()
            if hint and hint not in name:
                continue

            cmd = " ".join(proc.info.get("cmdline") or []).lower()
            if not cmd:
                continue
            if all(term in cmd for term in required):
                found.add(pid)
        except Exception:
            continue
    return found


def kill_pid(pid: int) -> bool:
    """Best-effort kill PID and return True if no longer running."""
    pid = _safe_int(pid, 0)
    if pid <= 0 or pid == os.getpid():
        return False

    if not is_pid_running(pid):
        return True

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.2)
            if is_pid_running(pid):
                os.kill(pid, signal.SIGKILL)
    except Exception:
        pass

    # Allow termination to settle.
    for _ in range(10):
        if not is_pid_running(pid):
            return True
        time.sleep(0.1)
    return not is_pid_running(pid)


def kill_pids(pids: Iterable[int], label: str) -> tuple[list[int], list[int]]:
    """Kill all provided PIDs, returning (killed, failed)."""
    unique = sorted({int(pid) for pid in pids if _safe_int(pid, 0) > 0 and int(pid) != os.getpid()})
    if not unique:
        return [], []

    log(f"Killing {label} PIDs: {', '.join(str(pid) for pid in unique)}")
    killed: list[int] = []
    failed: list[int] = []
    for pid in unique:
        if kill_pid(pid):
            killed.append(pid)
        elif is_pid_running(pid):
            failed.append(pid)
    return killed, failed


def _cloudflared_match_terms() -> list[list[str]]:
    terms: list[list[str]] = [["cloudflared", "tunnel"]]
    if CLOUDFLARED_TUNNEL_MODE == "named" and CLOUDFLARED_TUNNEL_NAME:
        terms.append(["cloudflared", CLOUDFLARED_TUNNEL_NAME.lower()])
    if CLOUDFLARED_CONFIG_PATH:
        terms.append(["cloudflared", _normalize_path_fragment(CLOUDFLARED_CONFIG_PATH)])
    return terms


def _ngrok_match_terms() -> list[list[str]]:
    terms: list[list[str]] = [["ngrok", "http", str(WEBHOOK_PORT)]]
    if NGROK_API_PORT > 0:
        terms.append(["ngrok", str(NGROK_API_PORT)])
    return terms


def collect_tunnel_pids() -> set[int]:
    """Collect tunnel process PIDs via ports + command-line matching."""
    pids: set[int] = set()
    if TUNNEL_PROVIDER == "cloudflared":
        if CLOUDFLARED_METRICS_PORT > 0:
            pids |= list_listening_pids(CLOUDFLARED_METRICS_PORT)
        for terms in _cloudflared_match_terms():
            pids |= find_pids_by_cmdline(terms, process_name_hint="cloudflared")
        return pids

    # ngrok
    if NGROK_API_PORT > 0:
        pids |= list_listening_pids(NGROK_API_PORT)
    for terms in _ngrok_match_terms():
        pids |= find_pids_by_cmdline(terms, process_name_hint="ngrok")
    return pids


def collect_webhook_pids() -> set[int]:
    """Collect webhook server PIDs via webhook port + command-line match."""
    pids = set(list_listening_pids(WEBHOOK_PORT))
    pids |= find_pids_by_cmdline(["instagram_webhook.py"], process_name_hint="python")
    pids |= find_pids_by_cmdline(["result_lookup_worker.py"], process_name_hint="python")
    return pids


def collect_discord_pids() -> set[int]:
    """Collect Discord bot PIDs via command-line match and pid file."""
    pids = set()
    pids |= find_pids_by_cmdline(["discord_bot", "bot.py"], process_name_hint="python")

    if DISCORD_PID_FILE.exists():
        try:
            pid_text = DISCORD_PID_FILE.read_text(encoding="utf-8").strip()
            pid = _safe_int(pid_text, 0)
            if pid > 0:
                pids.add(pid)
        except Exception:
            pass
    return pids


def collect_main_runner_pids() -> set[int]:
    """Detect running main.py processes which often consume large RAM while simulating."""
    return find_pids_by_cmdline(["main.py"], process_name_hint="python")


def discord_bot_running_status() -> tuple[bool, int]:
    pids = collect_discord_pids()
    alive = [pid for pid in pids if is_pid_running(pid)]
    return bool(alive), len(alive)


def stop_tunnel_processes() -> tuple[list[int], list[int]]:
    pids = collect_tunnel_pids()
    if not pids:
        log(f"No existing {TUNNEL_PROVIDER} tunnel process found.")
        return [], []
    killed, failed = kill_pids(pids, f"{TUNNEL_PROVIDER} tunnel")
    if failed:
        log(f"Failed to kill some tunnel PIDs: {', '.join(str(pid) for pid in failed)}", "WARN")
    if killed:
        log(f"Killed tunnel PIDs: {', '.join(str(pid) for pid in killed)}")
    return killed, failed


def stop_webhook_processes() -> tuple[list[int], list[int]]:
    pids = collect_webhook_pids()
    if not pids:
        log("No existing webhook process found.")
        return [], []
    killed, failed = kill_pids(pids, "webhook")
    if failed:
        log(f"Failed to kill some webhook PIDs: {', '.join(str(pid) for pid in failed)}", "WARN")
    if killed:
        log(f"Killed webhook PIDs: {', '.join(str(pid) for pid in killed)}")
    return killed, failed


def stop_discord_processes() -> tuple[list[int], list[int]]:
    pids = collect_discord_pids()
    if not pids:
        log("No existing Discord bot process found.")
        return [], []
    killed, failed = kill_pids(pids, "discord bot")
    if failed:
        log(f"Failed to kill some Discord bot PIDs: {', '.join(str(pid) for pid in failed)}", "WARN")
    if killed:
        log(f"Killed Discord bot PIDs: {', '.join(str(pid) for pid in killed)}")
    try:
        DISCORD_PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    return killed, failed


def wait_for_ports_closed(
    ports: Iterable[int],
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[bool, list[int]]:
    watch_ports = sorted({int(port) for port in ports if _safe_int(port, 0) > 0})
    if not watch_ports:
        return True, []

    deadline = time.time() + max(0.5, float(timeout_seconds))
    poll = max(0.1, float(poll_interval_seconds))
    while True:
        open_ports = [port for port in watch_ports if is_port_open("127.0.0.1", port, timeout=0.2)]
        if not open_ports:
            return True, []
        if time.time() >= deadline:
            return False, open_ports
        time.sleep(poll)


def _normalize_health_path(path: str) -> str:
    value = str(path or "").strip()
    if not value:
        value = "/status"
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def probe_webhook_health(
    *,
    port: int,
    health_path: str,
    timeout_seconds: float = 2.0,
) -> tuple[bool, str]:
    """Check webhook health endpoint; accept JSON or HTTP 200 response."""
    path = _normalize_health_path(health_path)
    url = f"http://127.0.0.1:{port}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=max(0.5, timeout_seconds)) as resp:
            code = int(getattr(resp, "status", resp.getcode()))
            body = resp.read(4096).decode("utf-8", errors="replace")
            if code != 200:
                return False, f"http_{code}"
            stripped = body.strip()
            if not stripped:
                return True, "http_200_empty"
            try:
                payload = json.loads(stripped)
                if isinstance(payload, (dict, list)):
                    return True, "http_200_json"
            except Exception:
                pass
            return True, "http_200_non_json"
    except urllib.error.HTTPError as exc:
        return False, f"http_{exc.code}"
    except urllib.error.URLError as exc:
        return False, f"url_error:{exc.reason}"
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def wait_for_webhook_health(
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
    health_path: str,
) -> tuple[bool, str]:
    deadline = time.time() + max(1.0, float(timeout_seconds))
    poll = max(0.1, float(poll_interval_seconds))
    last_reason = "timeout"
    while time.time() < deadline:
        ok, reason = probe_webhook_health(port=WEBHOOK_PORT, health_path=health_path, timeout_seconds=2.0)
        if ok:
            return True, reason
        last_reason = reason
        time.sleep(poll)
    return False, last_reason


def is_tunnel_running() -> bool:
    if TUNNEL_PROVIDER == "cloudflared":
        if CLOUDFLARED_METRICS_PORT > 0 and is_port_open("127.0.0.1", CLOUDFLARED_METRICS_PORT, timeout=0.3):
            return True
        return bool(collect_tunnel_pids())

    if NGROK_API_PORT > 0 and is_port_open("127.0.0.1", NGROK_API_PORT, timeout=0.3):
        return True
    return bool(collect_tunnel_pids())


def acquire_restart_lock(lock_path: Path, stale_seconds: float) -> bool:
    """Acquire exclusive restart lock, removing stale locks when safe."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    stale_after = max(30.0, float(stale_seconds))

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "pid": os.getpid(),
                        "created_at": time.time(),
                        "created_at_iso": datetime.now().isoformat(),
                    },
                    fh,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            log(f"Acquired restart lock: {lock_path}")
            return True
        except FileExistsError:
            info = {}
            try:
                with lock_path.open("r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                    if isinstance(loaded, dict):
                        info = loaded
            except Exception:
                info = {}

            lock_pid = _safe_int(info.get("pid"), 0)
            created_at = _safe_float(info.get("created_at"), 0.0)
            age = time.time() - created_at if created_at > 0 else None
            stale = False
            reasons: list[str] = []

            if age is not None and age > stale_after:
                stale = True
                reasons.append(f"age={age:.1f}s")
            if lock_pid > 0 and not is_pid_running(lock_pid):
                stale = True
                reasons.append(f"pid_not_running={lock_pid}")
            if lock_pid <= 0:
                stale = True
                reasons.append("missing_pid")

            if stale:
                log(
                    f"Removing stale restart lock ({', '.join(reasons) if reasons else 'stale'}).",
                    "WARN",
                )
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception as exc:
                    log(f"Failed to remove stale lock: {exc}", "ERROR")
                    return False
                continue

            log(
                "Another restart_webhook instance appears active. "
                f"Lock held by PID {lock_pid}. Aborting.",
                "ERROR",
            )
            return False
        except Exception as exc:
            log(f"Failed to acquire restart lock: {exc}", "ERROR")
            return False


def release_restart_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
        log(f"Released restart lock: {lock_path}")
    except Exception as exc:
        log(f"Failed to release restart lock: {exc}", "WARN")


def start_webhook(*, hidden: bool = False, debug: bool = False) -> bool:
    """Start webhook process."""
    if not WEBHOOK_SCRIPT.exists():
        log(f"Webhook script not found: {WEBHOOK_SCRIPT}", "ERROR")
        return False

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "instagram_webhook.log"

    env = dict(os.environ)
    if not debug:
        env["WEBHOOK_DEBUG"] = "0"
        env["WEBHOOK_USE_RELOADER"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    # Enforce conservative defaults to keep webhook memory stable on local machines.
    safe_defaults = {
        "WEBHOOK_USE_LOCAL_HISTORY": "0",
        "WEBHOOK_LOCAL_HISTORY_ALLOW_HUGE": "0",
        "WEBHOOK_EVENTS_RECENT_DAYS_WINDOW": "0",
        "WEBHOOK_EVENTS_DAY_CACHE_MAX": "32",
        "WEBHOOK_EVENTS_GAME_CACHE_MAX": "0",
        "WEBHOOK_EVENTS_SCAN_MAX_FILES": "3",
        "WEBHOOK_ISOLATE_RESULT_LOOKUP": "1",
        "WEBHOOK_RESULT_LOOKUP_MAX_CONCURRENCY": "1",
        "WEBHOOK_LOG_FULL_EVENTS": "0",
        "WEBHOOK_MAX_CONTENT_LENGTH_MB": "1",
        "WEBHOOK_THREADED": "0",
        "WEBHOOK_EVENT_QUEUE_MAX": "2000",
        "WEBHOOK_EVENT_WORKERS": "1",
    }
    for key, value in safe_defaults.items():
        env.setdefault(key, value)

    try:
        if os.name == "nt":
            if hidden:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
                log_file = open(log_path, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        [sys.executable, str(WEBHOOK_SCRIPT)],
                        cwd=str(BASE_DIR),
                        creationflags=flags,
                        stdout=log_file,
                        stderr=log_file,
                        env=env,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    [sys.executable, str(WEBHOOK_SCRIPT)],
                    cwd=str(BASE_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    env=env,
                )
        else:
            if hidden:
                log_file = open(log_path, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        [sys.executable, str(WEBHOOK_SCRIPT)],
                        cwd=str(BASE_DIR),
                        start_new_session=True,
                        stdout=log_file,
                        stderr=log_file,
                        env=env,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    [sys.executable, str(WEBHOOK_SCRIPT)],
                    cwd=str(BASE_DIR),
                    start_new_session=True,
                    env=env,
                )
    except Exception as exc:
        log(f"Failed to start webhook process: {exc}", "ERROR")
        return False

    log(f"Webhook process launched ({'hidden' if hidden else 'new console'}).")
    return True


def start_discord_bot(*, hidden: bool = False) -> bool:
    """Start Discord bot process."""
    if not DISCORD_SCRIPT.exists():
        log(f"Discord bot script not found: {DISCORD_SCRIPT}", "ERROR")
        return False

    DISCORD_LOG_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"

    command = [sys.executable, str(DISCORD_SCRIPT)]
    try:
        if os.name == "nt":
            if hidden:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
                log_file = open(DISCORD_LOG_PATH, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        command,
                        cwd=str(BASE_DIR),
                        creationflags=flags,
                        stdout=log_file,
                        stderr=log_file,
                        env=env,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    env=env,
                )
        else:
            if hidden:
                log_file = open(DISCORD_LOG_PATH, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        command,
                        cwd=str(BASE_DIR),
                        start_new_session=True,
                        stdout=log_file,
                        stderr=log_file,
                        env=env,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    start_new_session=True,
                    env=env,
                )
    except Exception as exc:
        log(f"Failed to start Discord bot process: {exc}", "ERROR")
        return False

    log(f"Discord bot process launched ({'hidden' if hidden else 'new console'}).")
    return True


def start_cloudflared(*, hidden: bool = False) -> bool:
    """Start cloudflared tunnel."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    tunnel_mode = CLOUDFLARED_TUNNEL_MODE
    if tunnel_mode not in ("quick", "named"):
        log(f"Unknown CLOUDFLARED_TUNNEL_MODE '{tunnel_mode}', defaulting to quick.", "WARN")
        tunnel_mode = "quick"

    command = [CLOUDFLARED_EXE, "tunnel"]
    if CLOUDFLARED_NO_AUTOUPDATE:
        command.append("--no-autoupdate")
    if CLOUDFLARED_LOG_LEVEL:
        command.extend(["--loglevel", CLOUDFLARED_LOG_LEVEL])
    if CLOUDFLARED_METRICS_PORT > 0:
        command.extend(["--metrics", f"127.0.0.1:{CLOUDFLARED_METRICS_PORT}"])
    if CLOUDFLARED_PROTOCOL in ("auto", "quic", "http2"):
        command.extend(["--protocol", CLOUDFLARED_PROTOCOL])
    if CLOUDFLARED_EDGE_IP_VERSION in ("4", "6", "auto"):
        command.extend(["--edge-ip-version", CLOUDFLARED_EDGE_IP_VERSION])

    if tunnel_mode == "named":
        if not CLOUDFLARED_TUNNEL_NAME:
            log("CLOUDFLARED_TUNNEL_NAME is empty. Falling back to quick tunnel.", "WARN")
            command.extend(["--url", CLOUDFLARED_URL])
        else:
            config_path = (
                Path(CLOUDFLARED_CONFIG_PATH)
                if CLOUDFLARED_CONFIG_PATH
                else (Path.home() / ".cloudflared" / "config.yml")
            )
            if not config_path.exists():
                log(f"cloudflared config not found at {config_path}. Falling back to quick tunnel.", "WARN")
                command.extend(["--url", CLOUDFLARED_URL])
            else:
                command.extend(["--config", str(config_path), "run", CLOUDFLARED_TUNNEL_NAME])
    else:
        command.extend(["--url", CLOUDFLARED_URL])

    try:
        if os.name == "nt":
            if hidden:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
                log_file = open(CLOUDFLARED_LOG_PATH, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        command,
                        cwd=str(BASE_DIR),
                        creationflags=flags,
                        stdout=log_file,
                        stderr=log_file,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
        else:
            if hidden:
                log_file = open(CLOUDFLARED_LOG_PATH, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        command,
                        cwd=str(BASE_DIR),
                        start_new_session=True,
                        stdout=log_file,
                        stderr=log_file,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    start_new_session=True,
                )
    except Exception as exc:
        log(f"Failed to start cloudflared: {exc}", "ERROR")
        return False

    log(f"cloudflared launched ({'hidden' if hidden else 'new console'}).")
    return True


def start_ngrok(*, hidden: bool = False) -> bool:
    """Start ngrok tunnel."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    command = [NGROK_EXE, "http", str(WEBHOOK_PORT)]
    try:
        if os.name == "nt":
            if hidden:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
                log_file = open(NGROK_LOG_PATH, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        command,
                        cwd=str(BASE_DIR),
                        creationflags=flags,
                        stdout=log_file,
                        stderr=log_file,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
        else:
            if hidden:
                log_file = open(NGROK_LOG_PATH, "a", encoding="utf-8")
                try:
                    subprocess.Popen(
                        command,
                        cwd=str(BASE_DIR),
                        start_new_session=True,
                        stdout=log_file,
                        stderr=log_file,
                    )
                finally:
                    log_file.close()
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    start_new_session=True,
                )
    except Exception as exc:
        log(f"Failed to start ngrok: {exc}", "ERROR")
        return False

    log(f"ngrok launched ({'hidden' if hidden else 'new console'}).")
    return True


def start_tunnel(*, hidden: bool = False) -> bool:
    if TUNNEL_PROVIDER == "cloudflared":
        return start_cloudflared(hidden=hidden)
    return start_ngrok(hidden=hidden)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restart webhook server and tunnel with lock + health gating."
    )
    parser.add_argument("--hidden", action="store_true", help="Run child processes in background/no window.")
    parser.add_argument("--debug", action="store_true", help="Start webhook in debug/reloader mode.")
    parser.add_argument("--force-restart", action="store_true", help="Force cleanup/restart even if already healthy.")
    parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=60.0,
        help="Seconds to wait for webhook health endpoint.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=1.0,
        help="Polling interval for port/health checks.",
    )
    parser.add_argument(
        "--health-path",
        default="/status",
        help="Webhook health path (default: /status).",
    )
    parser.add_argument(
        "--skip-tunnel",
        action="store_true",
        help="Restart only webhook, skip tunnel startup.",
    )
    parser.add_argument(
        "--skip-discord",
        action="store_true",
        help="Do not manage Discord bot during restart.",
    )
    parser.add_argument(
        "--lock-stale-seconds",
        type=float,
        default=300.0,
        help="Treat lock as stale after this many seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log("=" * 60)
    log("Webhook Restart (safe mode)")
    log("=" * 60)

    if psutil is None:
        log("psutil not available; command-line PID matching will be limited.", "WARN")

    manage_discord = DISCORD_AUTO_START and not args.skip_discord
    if args.skip_discord:
        log("Discord bot management disabled via --skip-discord.")
    elif not DISCORD_AUTO_START:
        log("Discord bot autostart disabled in config (AUTO_START_DISCORD_BOT=False).")
    else:
        log("Discord bot management enabled.")

    main_pids = sorted(collect_main_runner_pids())
    if main_pids:
        log(
            "Detected running main.py process(es): "
            + ", ".join(str(pid) for pid in main_pids)
            + ". This can consume large RAM while webhook/uploads run.",
            "WARN",
        )

    if not acquire_restart_lock(LOCK_PATH, stale_seconds=args.lock_stale_seconds):
        return 1

    try:
        if not args.force_restart:
            webhook_ok, webhook_reason = probe_webhook_health(
                port=WEBHOOK_PORT,
                health_path=args.health_path,
                timeout_seconds=2.0,
            )
            tunnel_ok = is_tunnel_running() if not args.skip_tunnel else True
            discord_ok = True
            discord_count = 0
            if manage_discord:
                discord_ok, discord_count = discord_bot_running_status()
            if webhook_ok and tunnel_ok and discord_ok:
                log("Webhook is healthy and tunnel is already running. No-op restart.")
                log("Use --force-restart to restart anyway.")
                return 0
            log(
                "Pre-check state: "
                f"webhook_ok={webhook_ok} ({webhook_reason}), tunnel_ok={tunnel_ok}, "
                f"discord_ok={discord_ok}"
            )
            if manage_discord and not discord_ok:
                log(f"Discord bot appears down (detected running instances: {discord_count}).")
        else:
            log("Force restart requested; proceeding with cleanup.")

        log("Stopping tunnel processes...")
        stop_tunnel_processes()

        log("Stopping webhook processes...")
        stop_webhook_processes()

        if manage_discord:
            log("Stopping Discord bot processes...")
            stop_discord_processes()

        wait_ports = [WEBHOOK_PORT]
        if TUNNEL_PROVIDER == "cloudflared" and CLOUDFLARED_METRICS_PORT > 0:
            wait_ports.append(CLOUDFLARED_METRICS_PORT)
        elif TUNNEL_PROVIDER == "ngrok" and NGROK_API_PORT > 0:
            wait_ports.append(NGROK_API_PORT)

        log(f"Waiting for ports to close: {', '.join(str(p) for p in wait_ports)}")
        released, still_open = wait_for_ports_closed(
            wait_ports,
            timeout_seconds=20.0,
            poll_interval_seconds=max(0.2, args.poll_interval_seconds),
        )
        if not released:
            log(f"Some ports are still open after wait: {', '.join(str(p) for p in still_open)}", "WARN")
        else:
            log("Ports released.")

        log("Starting webhook process...")
        if not start_webhook(hidden=args.hidden, debug=args.debug):
            return 1

        log(
            "Waiting for webhook health: "
            f"http://127.0.0.1:{WEBHOOK_PORT}{_normalize_health_path(args.health_path)}"
        )
        healthy, health_reason = wait_for_webhook_health(
            timeout_seconds=max(1.0, args.health_timeout_seconds),
            poll_interval_seconds=max(0.2, args.poll_interval_seconds),
            health_path=args.health_path,
        )
        if not healthy:
            log(f"Webhook failed health check: {health_reason}", "ERROR")
            log("Tunnel startup aborted because webhook is unhealthy.", "ERROR")
            return 1
        log(f"Webhook healthy: {health_reason}")

        tunnel_status = "SKIPPED"
        if args.skip_tunnel:
            log("Skipping tunnel startup (--skip-tunnel).")
        else:
            log(f"Starting {TUNNEL_PROVIDER} tunnel...")
            if not start_tunnel(hidden=args.hidden):
                return 1

            time.sleep(2.0)
            if is_tunnel_running():
                tunnel_status = "OK"
                log(f"{TUNNEL_PROVIDER} tunnel is running.")
            else:
                tunnel_status = "NOT_OK"
                log(f"{TUNNEL_PROVIDER} tunnel not confirmed yet.", "WARN")

        discord_status = "SKIPPED"
        if manage_discord:
            log("Starting Discord bot...")
            if not start_discord_bot(hidden=args.hidden):
                log("Discord bot startup failed.", "ERROR")
                return 1
            time.sleep(1.5)
            discord_ok, discord_count = discord_bot_running_status()
            if discord_ok:
                discord_status = "OK"
                log(f"Discord bot is running (instances={discord_count}).")
            else:
                discord_status = "NOT_OK"
                log("Discord bot not confirmed running after startup.", "ERROR")
                return 1

        final_web_ok, final_web_reason = probe_webhook_health(
            port=WEBHOOK_PORT,
            health_path=args.health_path,
            timeout_seconds=2.0,
        )
        if final_web_ok:
            log(f"Final webhook check OK ({final_web_reason}).")
        else:
            log(f"Final webhook check failed ({final_web_reason}).", "WARN")

        if not args.skip_tunnel and TUNNEL_PROVIDER == "cloudflared" and CLOUDFLARED_TUNNEL_MODE == "named":
            if CLOUDFLARED_HOSTNAME:
                log(f"Callback URL: https://{CLOUDFLARED_HOSTNAME}/webhook")

        tunnel_report = tunnel_status if not args.skip_tunnel else "SKIPPED"
        log(
            f"Final status: webhook={'OK' if final_web_ok else 'NOT_OK'} | "
            f"tunnel={tunnel_report} | discord={discord_status}"
        )
        if args.skip_tunnel:
            return 0 if final_web_ok and discord_status in ("OK", "SKIPPED") else 1
        return 0 if final_web_ok and tunnel_status == "OK" and discord_status in ("OK", "SKIPPED") else 1
    finally:
        release_restart_lock(LOCK_PATH)


if __name__ == "__main__":
    sys.exit(main())
