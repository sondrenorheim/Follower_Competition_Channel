"""
Automatic Git Push Module
Automatically commits and pushes stats files to GitHub after each game
"""

import subprocess
import os
from datetime import datetime
from typing import List, Optional

import json
import config
from shared import game_history, statistics


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
    if files is None:
        files = [
            "player_statistics.json",
            "game_history.json",
            "website/public/player_statistics_web.json",
            "website/public/game_history_web.json"
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

    # Default commit message
    if commit_message is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        game_mode = getattr(config, 'GAME_MODE', 'unknown')
        day_number = getattr(config, 'DAY_NUMBER', 0)
        commit_message = f"Auto-update stats - {game_mode} Day {day_number} - {timestamp}"

    print(f"\nPushing stats to GitHub...")
    print(f"   Files: {', '.join(files)}")
    print(f"   Message: {commit_message}")

    try:
        # Before git add/commit, regenerate web bundles if not in TEST_MODE
        if not config.TEST_MODE:
            try:
                # Build website/public/player_statistics_web.json
                stats = statistics.PlayerStatistics()
                stats.export_web_stats(
                    output_path="website/public/player_statistics_web.json"
                )
                print("   + Regenerated website/public/player_statistics_web.json")
            except Exception as e:
                print(f"   ! Failed to regenerate player_statistics_web.json: {e}")
            try:
                gh = game_history.GameHistory("game_history.json")
                gh.export_web_history(
                    output_path="website/public/game_history_web.json"
                )
                print("   + Regenerated website/public/game_history_web.json")
            except Exception as e:
                print(f"   ! Failed to regenerate game_history.json (web): {e}")

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

        # Add files
        for file in files:
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

        # Push to remote
        push_result = subprocess.run(
            ['git', 'push'],
            check=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        print("   + Pushed to GitHub")

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
