"""
Cloud sync helpers for API, event, and state data.

This module uses the AWS CLI against an S3-compatible endpoint (Cloudflare R2)
so both the Windows PC and the Mac can share generated data without treating
the git repo itself as a live shared folder.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import config


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_DIR = REPO_ROOT / "website" / "public" / "api"
DEFAULT_EVENTS_DIR = REPO_ROOT / "backups" / "game_results" / "events"
STATE_MANIFEST_NAME = "_state_manifest.json"
STATE_QUEUE_FILES = (
    "reply_queue_state.json",
    "reply_queue_events.jsonl",
    "reply_queue_meta.json",
)


@dataclass(frozen=True)
class SyncResult:
    ok: bool
    status: str
    message: str


def _first_non_empty(*values: str) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _repo_relative(path_value: str | Path) -> str | None:
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return None


def _r2_prefix(env_name: str, config_name: str, default: str) -> str:
    prefix = _first_non_empty(
        os.getenv(env_name, ""),
        getattr(config, config_name, ""),
        default,
    )
    return prefix.strip("/").replace("\\", "/")


def _aws_cli_path() -> str:
    return _first_non_empty(
        os.getenv("AWS_CLI_PATH", ""),
        getattr(config, "AWS_CLI_PATH", ""),
        "aws",
    )


def _aws_env() -> dict[str, str]:
    env = dict(os.environ)
    access_key = _first_non_empty(
        os.getenv("R2_ACCESS_KEY_ID", ""),
        os.getenv("AWS_ACCESS_KEY_ID", ""),
        getattr(config, "R2_ACCESS_KEY_ID", ""),
        getattr(config, "AWS_ACCESS_KEY_ID", ""),
    )
    secret_key = _first_non_empty(
        os.getenv("R2_SECRET_ACCESS_KEY", ""),
        os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        getattr(config, "R2_SECRET_ACCESS_KEY", ""),
        getattr(config, "AWS_SECRET_ACCESS_KEY", ""),
    )
    if access_key:
        env["AWS_ACCESS_KEY_ID"] = access_key
    if secret_key:
        env["AWS_SECRET_ACCESS_KEY"] = secret_key
    env.setdefault("AWS_DEFAULT_REGION", "auto")
    env.setdefault("AWS_REGION", "auto")
    env.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    env.setdefault("AWS_MAX_ATTEMPTS", "5")
    env.setdefault("AWS_RETRY_MODE", "adaptive")
    return env


def _r2_settings() -> dict[str, str]:
    return {
        "endpoint": _first_non_empty(
            os.getenv("R2_ENDPOINT", ""),
            os.getenv("AWS_ENDPOINT_URL", ""),
            getattr(config, "R2_ENDPOINT", ""),
            getattr(config, "AWS_ENDPOINT_URL", ""),
        ),
        "bucket": _first_non_empty(
            os.getenv("R2_BUCKET", ""),
            getattr(config, "R2_BUCKET", ""),
        ),
        "api_prefix": _r2_prefix("R2_API_PREFIX", "R2_API_PREFIX", "api"),
        "events_prefix": _r2_prefix("R2_EVENTS_PREFIX", "R2_EVENTS_PREFIX", "events"),
        "state_prefix": _r2_prefix("R2_STATE_PREFIX", "R2_STATE_PREFIX", "state/mac"),
    }


def _sync_timeout_seconds() -> int:
    raw = _first_non_empty(
        os.getenv("CLOUD_SYNC_TIMEOUT_SECONDS", ""),
        getattr(config, "CLOUD_SYNC_TIMEOUT_SECONDS", ""),
        "900",
    )
    try:
        return max(30, int(raw))
    except Exception:
        return 900


def _is_aws_cli_available(aws_bin: str) -> bool:
    try:
        result = subprocess.run(
            [aws_bin, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def _r2_uri(bucket: str, prefix: str) -> str:
    prefix = str(prefix or "").strip("/")
    if prefix:
        return f"s3://{bucket}/{prefix}"
    return f"s3://{bucket}"


def _run_aws_sync(source: str, destination: str, *, delete: bool) -> SyncResult:
    settings = _r2_settings()
    endpoint = settings["endpoint"]
    bucket = settings["bucket"]
    if not endpoint or not bucket:
        return SyncResult(False, "skipped", "Cloud sync skipped: R2 endpoint/bucket not configured.")

    aws_bin = _aws_cli_path()
    if not _is_aws_cli_available(aws_bin):
        return SyncResult(False, "skipped", f"Cloud sync skipped: AWS CLI not available ({aws_bin}).")

    command = [
        aws_bin,
        "s3",
        "sync",
        source,
        destination,
        "--endpoint-url",
        endpoint,
        "--only-show-errors",
    ]
    if delete:
        command.append("--delete")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=_aws_env(),
            cwd=str(REPO_ROOT),
            timeout=_sync_timeout_seconds(),
        )
    except subprocess.TimeoutExpired:
        return SyncResult(False, "failed", "Cloud sync failed: AWS CLI timed out.")
    except Exception as exc:
        return SyncResult(False, "failed", f"Cloud sync failed: {exc}")

    if result.returncode == 0:
        return SyncResult(True, "success", f"Cloud sync OK: {destination}")

    stderr = (result.stderr or result.stdout or "").strip()
    suffix = f" ({stderr})" if stderr else ""
    return SyncResult(False, "failed", f"Cloud sync failed for {destination}{suffix}")


def sync_directory_to_r2(local_dir: Path, prefix: str, *, delete: bool = True) -> SyncResult:
    local_dir = Path(local_dir)
    if not local_dir.exists():
        return SyncResult(False, "skipped", f"Cloud sync skipped: local directory missing ({local_dir}).")

    settings = _r2_settings()
    destination = _r2_uri(settings["bucket"], prefix)
    return _run_aws_sync(str(local_dir), destination, delete=delete)


def sync_r2_to_directory(prefix: str, local_dir: Path, *, delete: bool = True) -> SyncResult:
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    settings = _r2_settings()
    source = _r2_uri(settings["bucket"], prefix)
    return _run_aws_sync(source, str(local_dir), delete=delete)


def push_api_snapshot(api_dir: Path | None = None) -> SyncResult:
    settings = _r2_settings()
    return sync_directory_to_r2(api_dir or DEFAULT_API_DIR, settings["api_prefix"], delete=True)


def push_events_snapshot(events_dir: Path | None = None) -> SyncResult:
    settings = _r2_settings()
    return sync_directory_to_r2(events_dir or DEFAULT_EVENTS_DIR, settings["events_prefix"], delete=True)


def pull_events_snapshot(events_dir: Path | None = None) -> SyncResult:
    settings = _r2_settings()
    return sync_r2_to_directory(settings["events_prefix"], events_dir or DEFAULT_EVENTS_DIR, delete=True)


def list_state_snapshot_paths(*, existing_only: bool = False) -> list[str]:
    webhook_log_dir = Path(getattr(config, "WEBHOOK_SERVICE_LOG_DIR", "logs/webhook_services"))
    if not webhook_log_dir.is_absolute():
        webhook_log_dir = REPO_ROOT / webhook_log_dir

    generic_media_map = Path(
        str(
            os.getenv("WEBHOOK_MEDIA_GAME_MAP_PATH")
            or getattr(config, "WEBHOOK_MEDIA_GAME_MAP_PATH", webhook_log_dir / "media_game_mapping.json")
        )
    )

    candidates = [
        Path(getattr(config, "FOLLOWER_IMPORT_FILE", "Followers/new_followers_fresh.json")),
        Path("discord_bot/discord_links.json"),
        Path(getattr(config, "FACEBOOK_PROCESSED_COMMENT_IDS_PATH", webhook_log_dir / "processed_comment_ids.json")),
        generic_media_map,
        Path(getattr(config, "FACEBOOK_MEDIA_GAME_MAP_PATH", webhook_log_dir / "facebook_media_game_mapping.json")),
        Path(getattr(config, "YOUTUBE_MEDIA_GAME_MAP_PATH", webhook_log_dir / "youtube_media_game_mapping.json")),
    ]
    candidates.extend(webhook_log_dir / filename for filename in STATE_QUEUE_FILES)

    relative_paths: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        relative = _repo_relative(candidate)
        if not relative or relative in seen:
            continue
        absolute = REPO_ROOT / relative
        if existing_only and not absolute.exists():
            continue
        seen.add(relative)
        relative_paths.append(relative)

    return sorted(relative_paths)


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def push_state_snapshot() -> SyncResult:
    settings = _r2_settings()
    relative_paths = list_state_snapshot_paths(existing_only=True)
    if not relative_paths:
        return SyncResult(False, "skipped", "Cloud state push skipped: no snapshot files found.")

    with tempfile.TemporaryDirectory(prefix="fbg-state-push-") as tmp_dir:
        stage_root = Path(tmp_dir)
        for relative in relative_paths:
            source = REPO_ROOT / relative
            if not source.is_file():
                continue
            _copy_file(source, stage_root / relative)

        manifest_path = stage_root / STATE_MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(
                {
                    "generated_at": int(time.time()),
                    "files": relative_paths,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        result = sync_directory_to_r2(stage_root, settings["state_prefix"], delete=True)
        if result.ok:
            return SyncResult(True, "success", f"Cloud state push OK: {len(relative_paths)} file(s).")
        return result


def pull_state_snapshot() -> SyncResult:
    settings = _r2_settings()
    with tempfile.TemporaryDirectory(prefix="fbg-state-pull-") as tmp_dir:
        stage_root = Path(tmp_dir)
        sync_result = sync_r2_to_directory(settings["state_prefix"], stage_root, delete=True)
        if not sync_result.ok:
            return sync_result

        manifest_path = stage_root / STATE_MANIFEST_NAME
        if manifest_path.exists():
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                relative_paths = [
                    str(item).replace("\\", "/")
                    for item in payload.get("files", [])
                    if str(item).strip()
                ]
            except Exception as exc:
                return SyncResult(False, "failed", f"Cloud state pull failed: invalid manifest ({exc}).")
        else:
            relative_paths = [
                path.relative_to(stage_root).as_posix()
                for path in stage_root.rglob("*")
                if path.is_file() and path.name != STATE_MANIFEST_NAME
            ]

        if not relative_paths:
            return SyncResult(False, "skipped", "Cloud state pull skipped: remote snapshot is empty.")

        copied = 0
        for relative in sorted(set(relative_paths)):
            source = stage_root / relative
            if not source.is_file():
                continue
            _copy_file(source, REPO_ROOT / relative)
            copied += 1

        return SyncResult(True, "success", f"Cloud state pull OK: {copied} file(s).")
