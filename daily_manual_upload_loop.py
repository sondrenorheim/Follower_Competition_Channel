"""
Daily Automation Loop with MANUAL Instagram Uploads
====================================================
Opens Instagram browser once at start.
You handle login + 2FA once.
Browser stays open all day.
You upload each video manually when prompted.

This avoids automation detection and 2FA prompts for every upload!
"""

import time
import sys
from pathlib import Path
from datetime import datetime
import json

import config
from manual_instagram_uploader import ManualInstagramUploader


class DailyManualUploadLoop:
    """
    Daily automation with manual Instagram uploads
    """

    def __init__(self):
        self.log_file = "manual_upload_loop.log"
        self.state_file = "manual_upload_state.json"
        self.load_state()
        self.manual_uploader = None

    def log(self, message: str):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')

    def load_state(self):
        """Load state from file"""
        if Path(self.state_file).exists():
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'current_day': config.DAY_NUMBER,
                'videos_uploaded_today': []
            }

    def save_state(self):
        """Save state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_videos_to_upload(self) -> list:
        """Get list of videos for current day"""
        day_number = self.state['current_day']
        videos = []

        game_modes = getattr(config, 'ALL_GAME_MODES', [
            'battle_royale',
            'fighter_arena',
            'obstacle_course',
            'snake_escape',
            'team_battle',
            'platformer_race',
            'gorillas_vs_followers'
        ])

        for game_mode in game_modes:
            video_path = config.get_output_video_path(
                game_mode=game_mode,
                day_number=day_number,
                test_mode=False
            )
            video_path = Path(video_path)

            if video_path.exists():
                videos.append((str(video_path), game_mode))
                self.log(f"   Found: {video_path.name}")
            else:
                self.log(f"   Missing: {video_path.name}")

        return videos

    def upload_videos_manually(self):
        """
        Upload videos manually through persistent browser session
        """
        self.log("=" * 60)
        self.log("STARTING MANUAL VIDEO UPLOAD SESSION")
        self.log("=" * 60)

        videos = self.get_videos_to_upload()

        if not videos:
            self.log("WARNING: No videos found to upload")
            return

        self.log(f"Found {len(videos)} videos to upload manually")

        # Start persistent Instagram session
        self.log("\nStarting Instagram session...")
        self.manual_uploader = ManualInstagramUploader(
            cookies_file="instagram_cookies.json"
        )

        if not self.manual_uploader.start_session():
            self.log("ERROR: Failed to start Instagram session")
            return

        self.log("\nSUCCESS: Instagram session active!")
        self.log("Browser is now open and logged in.")
        print()

        # Upload each video manually
        for idx, (video_path, game_mode) in enumerate(videos):
            video_name = Path(video_path).name

            # Check if already uploaded
            if video_path in self.state.get('videos_uploaded_today', []):
                self.log(f"SKIP: {video_name} (already uploaded)")
                continue

            # Show caption suggestion
            caption = self.build_caption(game_mode, self.state['current_day'])

            print()
            print("=" * 60)
            print(f"VIDEO {idx + 1}/{len(videos)}: {game_mode}")
            print("=" * 60)
            print(f"File: {video_path}")
            print()
            print("Suggested caption (copy/paste):")
            print("-" * 60)
            print(caption)
            print("-" * 60)
            print()

            # Wait for manual upload
            self.manual_uploader.wait_for_manual_upload(video_name)

            # Mark as uploaded
            if video_path not in self.state['videos_uploaded_today']:
                self.state['videos_uploaded_today'].append(video_path)
                self.save_state()

            self.log(f"SUCCESS: {video_name} uploaded!")

            # Delay before next upload (except last one)
            if idx < len(videos) - 1:
                delay_minutes = 120  # 2 hours
                self.log(f"\nWaiting {delay_minutes} minutes before next upload...")
                self.log("(Browser will stay open - you can leave it)")
                print()
                print(f"Next upload in {delay_minutes} minutes.")
                print("You can minimize the browser and do other things.")
                print()

                # Wait in 10-minute chunks
                for i in range(delay_minutes // 10):
                    time.sleep(600)  # 10 minutes
                    remaining = delay_minutes - ((i + 1) * 10)
                    if remaining > 0:
                        self.log(f"   {remaining} minutes until next upload...")

        self.log("\nAll videos uploaded!")
        print()
        print("=" * 60)
        print("All uploads complete!")
        print("You can close the browser now, or leave it open.")
        print("=" * 60)
        print()

        input("Press Enter to close browser and end session...")
        self.manual_uploader.close_session()

    def build_caption(self, game_mode: str, day_number: int) -> str:
        """Build caption for video"""
        caption = f"""Day {day_number} of making my followers battle every day! Follow to enter the battle

Check the link in the bio for your result and overall monthly ranking!

#followerbattlegrounds #battle #gaming"""
        return caption

    def run(self):
        """Main execution"""
        self.log("\n" + "=" * 60)
        self.log(f"DAILY MANUAL UPLOAD - Day {self.state['current_day']}")
        self.log("=" * 60)

        try:
            self.upload_videos_manually()
            self.log("\nSUCCESS: Upload session completed!")

        except KeyboardInterrupt:
            self.log("\nWARNING: Session interrupted by user (Ctrl+C)")
            if self.manual_uploader:
                try:
                    self.manual_uploader.close_session()
                except:
                    pass

        except Exception as e:
            self.log(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    print()
    print("=" * 60)
    print("DAILY MANUAL INSTAGRAM UPLOAD")
    print("=" * 60)
    print()
    print("This script will:")
    print("  1. Open Instagram in Chrome (once)")
    print("  2. You login + handle 2FA (once)")
    print("  3. Browser stays open all day")
    print("  4. You upload each video manually when prompted")
    print("  5. No more 2FA prompts!")
    print()
    print("Benefits:")
    print("  - Avoids Instagram automation detection")
    print("  - No 2FA for every upload")
    print("  - You control the uploads")
    print("  - Browser stays logged in all day")
    print()
    print("=" * 60)
    print()

    input("Press Enter to start...")

    loop = DailyManualUploadLoop()
    loop.run()


if __name__ == "__main__":
    main()
