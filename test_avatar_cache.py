"""
Test script for avatar cache functionality
"""
from shared.api import InstagramAPI
import config

print("=== Avatar Cache Test ===\n")

# Check configuration
print(f"DOWNLOAD_PROFILE_PICTURES: {config.DOWNLOAD_PROFILE_PICTURES}")
print(f"FOLLOWER_IMPORT_FILE: {config.FOLLOWER_IMPORT_FILE}")
print()

# Initialize API
api = InstagramAPI()
print(f"Avatar cache directory: {api.avatar_cache_dir}")
print(f"Cache directory exists: {api.avatar_cache_dir.exists()}")
print()

# Load followers (should trigger avatar downloads or cache loads)
print("Loading 10 followers...")
followers = api.fetch_followers(10)
print(f"Loaded {len(followers)} followers")
print()

if followers:
    print(f"Sample follower: {followers[0]['username']}")
    print(f"Has avatar: {followers[0].get('avatar') is not None}")
    print()

# Check cache directory
cache_files = list(api.avatar_cache_dir.glob('*.jpg'))
print(f"Cached avatar files: {len(cache_files)}")
if cache_files:
    print(f"Sample cached files: {[f.name for f in cache_files[:5]]}")
print()

print("=== Test Complete ===")
