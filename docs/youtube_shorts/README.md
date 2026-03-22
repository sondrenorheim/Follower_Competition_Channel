# YouTube Shorts Reset Pack

This folder is the operating pack for the new `Follower Battlegrounds` YouTube Shorts channel.

Use it with the updated uploader flow:
- YouTube uploads prefer `_youtube_short.mp4`
- titles/descriptions are standalone
- the old channel stays dormant during the reset

## Files

- `21_day_tracker.csv`: one row per upload slot and result check
- `vidiq_free_prompts.md`: prompt bank for the free vidIQ workflow
- `short_brief_template.md`: pre-upload brief for each Short

## Launch Checklist

- Create the new YouTube channel.
- Authenticate it with `youtube_uploader.py` or `test_youtube_upload.py`.
- Keep the token separate from the older channel token.
- Connect only the new channel to vidIQ free.
- Stop uploading new Shorts to the old channel for the first 21 uploads.

## Daily Workflow

1. Pick one `_youtube_short.mp4` candidate.
2. Fill out `short_brief_template.md` for that Short.
3. Run the vidIQ prompts from `vidiq_free_prompts.md`.
4. Upload one Short only.
5. Log the first 24h numbers in `21_day_tracker.csv`.

## What To Watch

- `viewed_vs_swiped` should trend up quickly if the first seconds are clearer.
- `average_percentage_viewed` should stop collapsing early.
- Winners should cross the current baseline materially, not just inch upward.
- If the first 21 uploads still fail, change packaging before you blame the channel again.
