# YouTube Shorts Reset Guide

This repo now supports a dedicated YouTube Shorts reset for `Follower Battlegrounds`.

The important change is structural:
- Instagram exports stay untouched.
- YouTube uploads now prefer a dedicated `_youtube_short.mp4` variant.
- YouTube metadata no longer uses `Day X` series framing.
- OAuth can be pointed at a separate new-channel token so the old channel stays isolated.

## Channel Setup

1. Create the new YouTube channel you want to test.
2. Save that channel's OAuth client secret at `secrets/youtube_follower_battlegrounds_client_secret.json`.
3. Let the uploader create its token at `secrets/youtube_follower_battlegrounds_token.pickle`.
4. Connect only the new channel to vidIQ free.
5. Leave the old 178K-subscriber channel untouched during the 21-day reset.

If you want different paths, pass them explicitly:

```bash
python youtube_uploader.py \
  --video "Videos/Day_99/maze_rush_day_99_youtube_short.mp4" \
  --day 99 \
  --game maze_rush \
  --client-secret-path "secrets/youtube_follower_battlegrounds_client_secret.json" \
  --token-path "secrets/youtube_follower_battlegrounds_token.pickle"
```

## What Changed In Code

- `post_run_publish.py` now prefers a dedicated YouTube Shorts variant before generic non-IG routing.
- `shared/video_variant_builder.py` can generate `_youtube_short.mp4` files with a cold-open overlay:
  - `Every dot = a real follower`
  - `Only one survives`
- `youtube_uploader.py` now generates standalone Shorts titles and descriptions instead of `Day X` titles.

## Test One Short First

Use the test script before you run the full workflow:

```bash
python test_youtube_upload.py \
  --video "Videos/Day_99/maze_rush_day_99_youtube_short.mp4" \
  --day 99 \
  --game maze_rush \
  --privacy private \
  --client-secret-path "secrets/youtube_follower_battlegrounds_client_secret.json" \
  --token-path "secrets/youtube_follower_battlegrounds_token.pickle"
```

Check that:
- the upload lands on the new channel
- the title is standalone and not serialized
- the description matches the new Shorts framing
- the first seconds of the video show the YouTube hook overlay

## Daily Workflow

For the 21-day reset, publish at most one YouTube Short per day.

If you want a YouTube-only test, use the direct uploader:

```bash
python youtube_uploader.py \
  --video "Videos/Day_99/maze_rush_day_99_youtube_short.mp4" \
  --day 99 \
  --game maze_rush \
  --privacy public
```

If you use `post_run_publish.py` as part of a wider upload run, YouTube will now prefer the dedicated `_youtube_short.mp4` variant automatically whenever YouTube uploads are enabled.

Recommended operating rules:
- Upload `1 Short/day` for the first 21 days.
- Do not use `Day X` in titles or descriptions.
- Treat each Short as standalone.
- Use vidIQ free for hook/title questions, not for broad channel management.

## Tracking Pack

Use the files in [docs/youtube_shorts](s:\Follower Battlegrounds\docs\youtube_shorts):
- [README.md](s:\Follower Battlegrounds\docs\youtube_shorts\README.md)
- [21_day_tracker.csv](s:\Follower Battlegrounds\docs\youtube_shorts\21_day_tracker.csv)
- [vidiq_free_prompts.md](s:\Follower Battlegrounds\docs\youtube_shorts\vidiq_free_prompts.md)
- [short_brief_template.md](s:\Follower Battlegrounds\docs\youtube_shorts\short_brief_template.md)

## Legacy Note

`batch_youtube_upload.py` and `batch_youtube_upload_smart.py` still exist, but they are legacy bulk-upload tools. They are not the recommended workflow for this reset because the new plan is intentionally `1 Short/day`, not multi-upload batching.
