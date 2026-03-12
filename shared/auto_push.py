"""
Automatic Git Push Module
Automatically commits and pushes stats files to GitHub after each game
"""

import subprocess
import os
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import json
import config
from shared import game_history, statistics, media_kit, results_store


def _load_partitioned_games(base_dir: str = "website/public/api") -> list[dict]:
    try:
        from pathlib import Path
        games_dir = Path(base_dir) / "games"
        if not games_dir.exists():
            return []
        games = []
        for path in games_dir.glob("*.json"):
            if path.name.endswith("_top.json"):
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("game_id"):
                    games.append(data)
            except Exception:
                continue
        return games
    except Exception:
        return []


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _first_non_empty(*values: str) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _sync_api_to_r2(api_dir: Path) -> bool:
    """
    Sync API payload directly to R2 from the local machine.
    Returns True on success, False when unavailable or failed.
    """
    endpoint = _first_non_empty(
        os.getenv("R2_ENDPOINT", ""),
        os.getenv("AWS_ENDPOINT_URL", ""),
        getattr(config, "R2_ENDPOINT", ""),
    )
    bucket = _first_non_empty(
        os.getenv("R2_BUCKET", ""),
        getattr(config, "R2_BUCKET", ""),
    )
    if not endpoint or not bucket:
        print("   i R2 sync skipped (missing endpoint/bucket)")
        return False

    aws_bin = _first_non_empty(getattr(config, "AWS_CLI_PATH", ""), "aws")
    try:
        check = subprocess.run([aws_bin, "--version"], capture_output=True, text=True, check=False)
        if check.returncode != 0:
            print("   ! R2 sync skipped (AWS CLI not available)")
            return False
    except Exception as e:
        print(f"   ! R2 sync skipped (AWS CLI check failed): {e}")
        return False

    sync_cmd = [
        aws_bin,
        "s3",
        "sync",
        os.fspath(api_dir),
        f"s3://{bucket}/api",
        "--endpoint-url",
        endpoint,
        "--only-show-errors",
    ]
    if getattr(config, "AUTO_PUSH_R2_SYNC_DELETE", True):
        sync_cmd.append("--delete")

    sync_env = dict(os.environ)
    access_key = _first_non_empty(
        os.getenv("R2_ACCESS_KEY_ID", ""),
        os.getenv("AWS_ACCESS_KEY_ID", ""),
        getattr(config, "R2_ACCESS_KEY_ID", ""),
    )
    secret_key = _first_non_empty(
        os.getenv("R2_SECRET_ACCESS_KEY", ""),
        os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        getattr(config, "R2_SECRET_ACCESS_KEY", ""),
    )
    if access_key and secret_key:
        sync_env["AWS_ACCESS_KEY_ID"] = access_key
        sync_env["AWS_SECRET_ACCESS_KEY"] = secret_key
    sync_env.setdefault("AWS_DEFAULT_REGION", "auto")
    sync_env.setdefault("AWS_REGION", "auto")
    sync_env.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    sync_env.setdefault("AWS_MAX_ATTEMPTS", "5")
    sync_env.setdefault("AWS_RETRY_MODE", "adaptive")

    retries = int(getattr(config, "AUTO_PUSH_R2_SYNC_RETRIES", 3) or 3)
    delay = int(getattr(config, "AUTO_PUSH_R2_SYNC_RETRY_DELAY_SECONDS", 5) or 5)
    for attempt in range(1, retries + 1):
        result = subprocess.run(sync_cmd, capture_output=True, text=True, check=False, env=sync_env)
        if result.returncode == 0:
            print("   + Synced website/public/api to R2 from local pipeline")
            return True
        print(f"   ! R2 sync failed (attempt {attempt}/{retries})")
        if result.stderr:
            print(f"      {result.stderr.strip()}")
        if attempt < retries:
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return False


def _add_api_for_commit(track_heavy_api: bool):
    api_root = "website/public/api/"
    subprocess.run(["git", "add", "-A", api_root], check=True)
    if track_heavy_api:
        # Force-add ignored heavy paths when fallback requires git tracking.
        subprocess.run(
            ["git", "add", "-A", "-f", "website/public/api/games/", "website/public/api/player_history/"],
            capture_output=True,
            text=True,
            check=False,
        )
        print("   + Added website/public/api/ (full)")
        return

    # Keep heavyweight churn out of git commits; these are synced to R2 directly.
    subprocess.run(
        ["git", "restore", "--staged", "website/public/api/games/", "website/public/api/player_history/"],
        capture_output=True,
        text=True,
        check=False,
    )
    print("   + Added website/public/api/ (excluding games/ and player_history/)")


def _is_api_root_path(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").rstrip("/")
    return normalized == "website/public/api"


def _stats_push_lock_path() -> Path:
    return _repo_root() / "logs" / "stats_push" / "auto_push.lock"


def _export_club_members(api_dir: Path) -> bool:
    """
    Ensure website/public/api/club_members.json is refreshed from Followers/club_members_followers.json.
    Returns True if exported, False if source missing or export failed.
    """
    try:
        root = _repo_root()
        source = root / "Followers" / "club_members_followers.json"
        if not source.exists():
            print("   ! Club members source not found; skipping export")
            return False
        api_dir.mkdir(parents=True, exist_ok=True)
        dest = api_dir / "club_members.json"
        dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        print("   + Refreshed club_members.json from Followers/club_members_followers.json")
        return True
    except Exception as e:
        print(f"   ! Failed to export club_members.json: {e}")
        return False


def _pid_is_running(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _git_process_running() -> bool:
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq git.exe"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "git.exe" in result.stdout.lower()
        except Exception:
            return False
    try:
        result = subprocess.run(
            ["pgrep", "-f", "git"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _acquire_push_lock(timeout_seconds: int = 900, poll_seconds: int = 2) -> Optional[Path]:
    lock_path = _stats_push_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(f"pid={os.getpid()}\n")
                f.write(f"started={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            return lock_path
        except FileExistsError:
            # Check if lock holder is dead
            try:
                contents = lock_path.read_text(encoding="utf-8")
                pid = None
                for line in contents.splitlines():
                    if line.startswith("pid="):
                        try:
                            pid = int(line.split("=", 1)[1].strip())
                        except Exception:
                            pid = None
                        break
                if pid and not _pid_is_running(pid):
                    lock_path.unlink(missing_ok=True)
                    continue
            except Exception:
                pass

            if time.time() - start >= timeout_seconds:
                return None
            time.sleep(poll_seconds)


def _release_push_lock(lock_path: Optional[Path]):
    if lock_path is None:
        return
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def _wait_for_git_index_lock(timeout_seconds: int = 120) -> bool:
    lock_path = _repo_root() / ".git" / "index.lock"
    if not lock_path.exists():
        return True

    start = time.time()
    while lock_path.exists():
        # If no git process is running, treat the lock as stale
        if not _git_process_running():
            try:
                lock_path.unlink(missing_ok=True)
                return True
            except Exception:
                pass
        if time.time() - start >= timeout_seconds:
            return False
        time.sleep(1)
    return True


def push_stats_to_github(
    files: Optional[List[str]] = None,
    commit_message: Optional[str] = None
) -> bool:
    """
    Automatically commit and push stats files to GitHub

    Args:
        files: List of files to commit (defaults to stats JSON files)
        commit_message: Custom commit message (defaults to timestamp)

    Returns:
        True if successful, False otherwise
    """
    # Skip if in test mode
    if config.TEST_MODE:
        print("TEST MODE: Skipping git push")
        return True

    # Default files to commit
    # NOTE: We now ONLY push partitioned files in website/public/api/
    # The monolithic player_statistics.json and game_history.json are kept local only
    # to avoid LFS budget issues (game_history.json is 836MB!)
    if files is None:
        files = [
            "website/public/api/"  # Partitioned player stats and game history
        ]

        # Conditionally add video files based on config
        if getattr(config, 'AUTO_PUSH_INCLUDE_VIDEOS', False):
            import glob
            day_number = getattr(config, 'DAY_NUMBER', 0)
            game_mode = getattr(config, 'GAME_MODE', 'unknown')

            # Add video files matching common patterns
            video_patterns = [
                f"*_day_{day_number}.mp4",  # Root directory videos
                f"Videos/Day_{day_number}/*.mp4",  # Videos in day folder
                f"Uploaded videos/*_day_{day_number}.mp4",  # Uploaded videos folder
            ]

            for pattern in video_patterns:
                matching_files = glob.glob(pattern)
                files.extend(matching_files)

    requested_track_heavy_api = bool(getattr(config, "AUTO_PUSH_TRACK_HEAVY_API", True))
    track_heavy_api = requested_track_heavy_api

    # Default commit message
    if commit_message is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        game_mode = getattr(config, 'GAME_MODE', 'unknown')
        day_number = getattr(config, 'DAY_NUMBER', 0)
        commit_message = f"Auto-update stats - {game_mode} Day {day_number} - {timestamp}"

    print(f"\nPushing stats to GitHub...")
    print(f"   Files: {', '.join(files)}")
    print(f"   Message: {commit_message}")
    print(f"   Heavy API in git: {'yes' if track_heavy_api else 'no'}")

    lock_timeout = getattr(config, "AUTO_PUSH_LOCK_TIMEOUT_SECONDS", 900)
    index_lock_timeout = getattr(config, "GIT_INDEX_LOCK_TIMEOUT_SECONDS", 120)
    lock_path = _acquire_push_lock(lock_timeout)
    if lock_path is None:
        print("ERROR: Timed out waiting for stats push lock. Skipping push.")
        return False

    try:
        # Before git add/commit, regenerate partitioned API files if not in TEST_MODE
        # We no longer export the monolithic web.json files - only partitioned API
        if not config.TEST_MODE:
            gh = None
            api_dir = _repo_root() / "website" / "public" / "api"
            try:
                # Export partitioned game history (merge API baseline + local new games)
                api_games = _load_partitioned_games("website/public/api")
                gh = game_history.GameHistory("game_history.json")
                merged_games = results_store.merge_games(api_games, gh.history.get("games", []) or [])
                gh.history["games"] = merged_games
                if api_games:
                    print(f"   + Using existing API history ({len(api_games)} games) as baseline")
                gh.save_history()
                print(f"   + Persisted canonical game_history.json ({len(merged_games)} games)")
                _export_club_members(api_dir)
                gh.export_partitioned_history(str(api_dir))
                print("   + Regenerated partitioned game history")
                try:
                    gh.export_hall_of_fame(str(api_dir))
                    print("   + Regenerated hall of fame data")
                except Exception as e:
                    print(f"   ! Failed to regenerate hall of fame data: {e}")
            except Exception as e:
                print(f"   ! Failed to regenerate game history: {e}")

            try:
                media_kit.export_media_kit(str(api_dir))
            except Exception as e:
                print(f"   ! Failed to regenerate media kit stats: {e}")

            try:
                # Trigger stats auto-recovery before rebuild.
                statistics.PlayerStatistics("player_statistics.json")
                games = gh.history.get("games", []) if gh else []
                stats = statistics.PlayerStatistics.rebuild_from_games(
                    games,
                    stats_file="player_statistics.json",
                )
                stats.export_partitioned_stats(str(api_dir))
                stats.export_web_stats("website/public/player_statistics_web.json")
                print("   + Regenerated player stats from merged history")
            except Exception as e:
                print(f"   ! Failed to regenerate player stats: {e}")

            try:
                root = _repo_root()
                script = root / "build_club_member_stats.py"
                if script.exists():
                    subprocess.run(
                        [os.fspath(sys.executable), os.fspath(script)],
                        check=False,
                        cwd=str(root),
                    )
                    print("   + Regenerated club member stats")
                else:
                    print("   ! build_club_member_stats.py not found; skipping club stats")
            except Exception as e:
                print(f"   ! Failed to regenerate club member stats: {e}")

            if getattr(config, "AUTO_PUSH_SYNC_R2_FROM_LOCAL", False):
                api_dir = _repo_root() / "website" / "public" / "api"
                r2_synced = _sync_api_to_r2(api_dir)
                if not r2_synced and not requested_track_heavy_api:
                    print("   ! R2 sync unavailable; temporarily including heavy API in git to avoid data loss")
                    track_heavy_api = True

        # Check if we're in a git repository
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print("ERROR: Not a git repository. Skipping push.")
            return False

        if not _wait_for_git_index_lock(index_lock_timeout):
            print("ERROR: Git index lock did not clear in time. Skipping push.")
            return False

        # Add files
        for file in files:
            if _is_api_root_path(file):
                _add_api_for_commit(track_heavy_api)
                continue

            if os.path.exists(file):
                subprocess.run(['git', 'add', file], check=True)
                print(f"   + Added {file}")
            else:
                print(f"   ! File not found: {file}")

        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'diff', '--staged', '--quiet'],
            capture_output=True,
            check=False
        )

        if result.returncode == 0:
            # No changes to commit
            print("   i No changes to commit")
            return True

        # Commit changes
        subprocess.run(
            ['git', 'commit', '-m', commit_message],
            check=True,
            capture_output=True,
            text=True
        )
        print("   + Committed changes")

        # Push to remote (with retry + longer timeout)
        push_timeout = getattr(config, "GIT_PUSH_TIMEOUT_SECONDS", 300)
        push_retries = getattr(config, "GIT_PUSH_RETRIES", 2)
        last_timeout = None

        for attempt in range(1, push_retries + 1):
            try:
                subprocess.run(
                    ['git', 'push'],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=push_timeout
                )
                print("   + Pushed to GitHub")
                last_timeout = None
                break
            except subprocess.TimeoutExpired as e:
                last_timeout = e
                print(f"ERROR: Git push timed out after {push_timeout}s (attempt {attempt}/{push_retries})")
                if attempt < push_retries:
                    time.sleep(5)

        if last_timeout is not None:
            raise last_timeout

        print("SUCCESS: Stats successfully pushed to GitHub!")
        print("   -> Website will auto-update via GitHub Actions\n")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Git push timed out (check network connection)")
        return False

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Git command failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")

        # Check if it's an authentication error
        if "authentication" in str(e).lower() or "permission" in str(e).lower():
            print("\nAuthentication Error:")
            print("   You need to set up git authentication. Choose one:")
            print("   1. SSH Keys (Recommended):")
            print("      - Generate: ssh-keygen -t ed25519")
            print("      - Add public key to GitHub account")
            print("   2. Personal Access Token:")
            print("      - Generate token on GitHub")
            print("      - Store in environment: set GITHUB_PAT=your_token")
            print("   3. GitHub CLI:")
            print("      - Install: gh auth login")

        return False

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False
    finally:
        _release_push_lock(lock_path)


def check_git_status() -> dict:
    """
    Check current git status

    Returns:
        Dictionary with git status information
    """
    try:
        # Check if git is available
        subprocess.run(['git', '--version'], capture_output=True, check=True)

        # Check if in a git repo
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return {
                "is_git_repo": False,
                "has_remote": False,
                "current_branch": None,
                "has_changes": False
            }

        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = branch_result.stdout.strip()

        # Check for remote
        remote_result = subprocess.run(
            ['git', 'remote'],
            capture_output=True,
            text=True,
            check=True
        )
        has_remote = len(remote_result.stdout.strip()) > 0

        # Check for uncommitted changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        has_changes = len(status_result.stdout.strip()) > 0

        return {
            "is_git_repo": True,
            "has_remote": has_remote,
            "current_branch": current_branch,
            "has_changes": has_changes
        }

    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "is_git_repo": False,
            "has_remote": False,
            "current_branch": None,
            "has_changes": False
        }


if __name__ == "__main__":
    # Test the git status check
    status = check_git_status()
    print("Git Status:")
    print(f"  Is git repo: {status['is_git_repo']}")
    print(f"  Has remote: {status['has_remote']}")
    print(f"  Current branch: {status['current_branch']}")
    print(f"  Has changes: {status['has_changes']}")
