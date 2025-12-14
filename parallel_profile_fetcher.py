"""
Parallel Profile Picture Fetcher
Splits follower list into chunks and runs multiple Selenium browsers in parallel
Merges results when done
"""

import json
import subprocess
import sys
import time
from pathlib import Path

# Configuration
INPUT_FILE = "Followers/all_followers_fresh.json"
OUTPUT_FILE = "Followers/all_followers_fresh.json"
NUM_WORKERS = 8  # Number of parallel browsers (4-12 recommended for 80GB RAM)
CHUNK_DIR = Path("Followers/chunks")


def load_followers(filename):
    """Load follower data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[LOADED] {len(data):,} followers from {filename}")
            return data
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return []


def save_followers(followers, filename):
    """Save followers to JSON file"""
    try:
        # Create parent directory if needed
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(followers, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {len(followers):,} followers to {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save {filename}: {e}")
        return False


def split_followers_into_chunks(followers, num_chunks):
    """
    Split followers into N chunks, prioritizing those without profile pics

    Args:
        followers: List of follower dicts
        num_chunks: Number of chunks to create

    Returns:
        List of follower chunks
    """
    # Separate followers by whether they have profile pics
    need_pics = [f for f in followers if not f.get('profile_pic_url', '').strip()]
    have_pics = [f for f in followers if f.get('profile_pic_url', '').strip()]

    print(f"\n[ANALYSIS]")
    print(f"   Need profile pics: {len(need_pics):,}")
    print(f"   Already have pics: {len(have_pics):,}")
    print(f"   Splitting into {num_chunks} chunks...")

    # Calculate chunk size for those needing pics
    chunk_size = (len(need_pics) + num_chunks - 1) // num_chunks

    chunks = []
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, len(need_pics))

        chunk = need_pics[start_idx:end_idx]

        # Add proportional share of those who already have pics
        # (in case we want to re-fetch or verify)
        have_pics_chunk_size = len(have_pics) // num_chunks
        have_pics_start = i * have_pics_chunk_size
        have_pics_end = min(have_pics_start + have_pics_chunk_size, len(have_pics))

        if i == num_chunks - 1:  # Last chunk gets remainder
            have_pics_end = len(have_pics)

        chunk.extend(have_pics[have_pics_start:have_pics_end])

        chunks.append(chunk)
        print(f"   Chunk {i+1}: {len(chunk):,} followers ({len(chunk) - len(have_pics[have_pics_start:have_pics_end]):,} need pics)")

    return chunks


def create_chunk_files(chunks):
    """
    Save each chunk to a separate file

    Args:
        chunks: List of follower chunks

    Returns:
        List of chunk file paths
    """
    # Create chunks directory
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_file = CHUNK_DIR / f"chunk_{i+1}.json"
        save_followers(chunk, str(chunk_file))
        chunk_files.append(chunk_file)

    return chunk_files


def create_worker_script(chunk_file, output_file, worker_id):
    """
    Create a modified version of the selenium script for this chunk

    Args:
        chunk_file: Input chunk file
        output_file: Output file for this worker
        worker_id: Worker number (for display)

    Returns:
        Path to worker script
    """
    worker_script = CHUNK_DIR / f"worker_{worker_id}.py"

    # Read the original selenium script
    with open("fetch_profile_pics_selenium.py", 'r', encoding='utf-8') as f:
        original_script = f.read()

    # Modify INPUT_FILE and OUTPUT_FILE
    modified_script = original_script.replace(
        'INPUT_FILE = "Followers/all_followers.json"',
        f'INPUT_FILE = "{chunk_file}"'
    ).replace(
        'OUTPUT_FILE = "Followers/all_followers_with_pics.json"',
        f'OUTPUT_FILE = "{output_file}"'
    )

    # CRITICAL FIX: Remove the interactive prompt that blocks subprocess execution
    # Replace the user confirmation section with auto-accept
    modified_script = modified_script.replace(
        '''    response = input("Ready to start? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return''',
        '''    # Auto-start for parallel execution (no user prompt needed)
    print("Starting fetch (parallel worker mode)...")'''
    )

    # CRITICAL FIX #2: Remove emoji characters that cause UnicodeEncodeError on Windows
    # when running via subprocess (cp1252 encoding can't handle these)
    emoji_replacements = [
        ('⚠️', '[!]'),
        ('✅', '[OK]'),
        ('❌', '[X]'),
        ('⏭️', '[>>]'),
        ('📁', '[FILE]'),
        ('ℹ️', '[i]'),
    ]
    for emoji, replacement in emoji_replacements:
        modified_script = modified_script.replace(emoji, replacement)

    # Write worker script
    with open(worker_script, 'w', encoding='utf-8') as f:
        f.write(modified_script)

    return worker_script


def merge_chunks(chunk_output_files, final_output_file):
    """
    SAFELY merge all chunk results into final output file
    ALWAYS preserves existing profile_pic_url data!

    Args:
        chunk_output_files: List of chunk output files
        final_output_file: Final merged output file
    """
    print("\n" + "="*60)
    print("  MERGING RESULTS")
    print("="*60)

    # Load existing file to preserve all profile_pic_urls
    all_followers = {}
    if Path(final_output_file).exists():
        print(f"   Loading existing file to preserve profile pics...")
        existing = load_followers(final_output_file)
        existing_with_pics = sum(1 for f in existing if f.get('profile_pic_url', '').strip())
        print(f"   Existing: {len(existing):,} followers, {existing_with_pics:,} with pics")
        all_followers = {f.get('username', ''): f for f in existing if f.get('username', '')}

    # Merge all chunks
    for chunk_file in chunk_output_files:
        if Path(chunk_file).exists():
            chunk_data = load_followers(str(chunk_file))
            for follower in chunk_data:
                username = follower.get('username', '')
                if not username:
                    continue

                if username in all_followers:
                    # CRITICAL: Preserve existing profile_pic_url if chunk doesn't have one
                    existing_pic = all_followers[username].get('profile_pic_url', '')
                    new_pic = follower.get('profile_pic_url', '').strip()

                    if new_pic and not existing_pic:
                        # Chunk has new pic, existing doesn't - use new pic
                        all_followers[username]['profile_pic_url'] = new_pic
                    elif new_pic and existing_pic:
                        # Both have pics - keep existing (should be same anyway)
                        pass
                    # If chunk doesn't have pic, keep existing (already preserved)
                else:
                    # New follower from chunk
                    all_followers[username] = follower

    # Convert to list and sort
    final_followers = sorted(all_followers.values(), key=lambda x: x.get('username', '').lower())

    # VALIDATION: Make sure we didn't lose any profile pics
    final_with_pics = sum(1 for f in final_followers if f.get('profile_pic_url', '').strip())
    if Path(final_output_file).exists():
        existing = load_followers(final_output_file)
        existing_with_pics = sum(1 for f in existing if f.get('profile_pic_url', '').strip())
        if final_with_pics < existing_with_pics:
            print(f"\n   ERROR: Would lose {existing_with_pics - final_with_pics} profile pics!")
            print(f"   Merge ABORTED - your data is safe!")
            return

    # Create backup before saving
    from datetime import datetime
    if Path(final_output_file).exists():
        backup_file = Path(final_output_file).parent / f"all_followers_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import shutil
        shutil.copy2(final_output_file, backup_file)
        print(f"   Backup created: {backup_file.name}")

    # Save merged result
    save_followers(final_followers, final_output_file)

    # Stats
    print(f"\n[FINAL STATS]")
    print(f"   Total followers: {len(final_followers):,}")
    print(f"   With profile pics: {final_with_pics:,}")
    print(f"   Without pics: {len(final_followers) - final_with_pics:,}")
    if len(final_followers) > 0:
        print(f"   Completion: {final_with_pics / len(final_followers) * 100:.1f}%")
    else:
        print(f"   Completion: 0.0%")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  PARALLEL PROFILE PICTURE FETCHER")
    print("="*60)
    print(f"\n[CONFIG]")
    print(f"   Input file: {INPUT_FILE}")
    print(f"   Output file: {OUTPUT_FILE}")
    print(f"   Number of workers: {NUM_WORKERS}")
    print(f"   Chunk directory: {CHUNK_DIR}")

    # Load followers
    print(f"\n[STEP 1] Loading followers...")
    followers = load_followers(INPUT_FILE)
    if not followers:
        return

    # Split into chunks
    print(f"\n[STEP 2] Splitting into {NUM_WORKERS} chunks...")
    chunks = split_followers_into_chunks(followers, NUM_WORKERS)

    # Create chunk files
    print(f"\n[STEP 3] Creating chunk files...")
    chunk_files = create_chunk_files(chunks)

    # Create output file paths
    chunk_output_files = [
        CHUNK_DIR / f"chunk_{i+1}_with_pics.json"
        for i in range(NUM_WORKERS)
    ]

    print(f"\n[STEP 4] Starting {NUM_WORKERS} parallel workers...")
    print(f"\n   IMPORTANT:")
    print(f"   - {NUM_WORKERS} Chrome browser windows will open")
    print(f"   - Each worker saves progress independently")
    print(f"   - You can monitor progress in separate terminal windows")
    print(f"   - Press Ctrl+C in ANY window to stop ALL workers")
    print(f"   - Partial progress is saved and can be resumed")

    response = input(f"\nReady to start {NUM_WORKERS} workers? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Start workers as subprocess
    processes = []
    for i in range(NUM_WORKERS):
        print(f"\n   Starting Worker {i+1}/{NUM_WORKERS}...")

        # Run the selenium script directly with modified input/output
        # We'll use environment variables to pass config
        cmd = [
            sys.executable,  # python
            "fetch_profile_pics_selenium.py"
        ]

        # Create modified script inline by passing parameters
        # Actually, easier to just create worker scripts
        worker_script = create_worker_script(
            chunk_files[i],
            chunk_output_files[i],
            i + 1
        )

        # Start worker
        process = subprocess.Popen(
            [sys.executable, str(worker_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        processes.append({
            'process': process,
            'worker_id': i + 1,
            'chunk_file': chunk_files[i],
            'output_file': chunk_output_files[i]
        })

        # Small delay between starting workers
        time.sleep(2)

    print(f"\n[RUNNING] All {NUM_WORKERS} workers started!")
    print(f"   Monitor progress by checking chunk output files")
    print(f"   Waiting for all workers to complete...")

    try:
        # Wait for all processes to complete
        for worker in processes:
            worker['process'].wait()
            print(f"\n   Worker {worker['worker_id']} completed!")
    except KeyboardInterrupt:
        print(f"\n\n[INTERRUPTED] Stopping all workers...")
        for worker in processes:
            worker['process'].terminate()
        print("   All workers stopped.")
        return

    # Merge results
    print(f"\n[STEP 5] Merging results...")
    merge_chunks(chunk_output_files, OUTPUT_FILE)

    print(f"\n" + "="*60)
    print("  PARALLEL FETCH COMPLETE!")
    print("="*60)
    print(f"\n   Final output: {OUTPUT_FILE}")
    print(f"   Chunk files saved in: {CHUNK_DIR}")
    print(f"   You can delete the chunks folder if desired")


if __name__ == "__main__":
    main()
