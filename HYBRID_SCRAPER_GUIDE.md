# Hybrid Alphabet Scraper Guide

## What It Does

The hybrid scraper uses a **two-pass approach** to maximize follower collection while minimizing time:

### Pass 1: 2-Character Search (aa-zz)
- Searches all 676 two-character patterns
- Tracks which patterns return lots of followers (high-density)
- Time: ~2-3 hours

### Pass 2: 3-Character Deep Dive (automatic)
- For patterns that returned ≥25 followers, searches 3-char variations
- Example: If "jo" returned 50 followers, searches "joa", "job", "joc", ... "joz"
- Only searches where it matters most!
- Time: Depends on how many high-density patterns found (~1-2 hours)

**Total Time: ~4-5 hours**
**Expected Results: 4,000-6,000 unique followers per burner!**

---

## Configuration

Edit these settings in `alphabet_follower_scraper.py`:

```python
# Line 36: Threshold for 3-char deep dive
HIGH_DENSITY_THRESHOLD = 25  # If pattern returns ≥25 followers, do 3-char search

# Line 39: Enable/disable hybrid mode
USE_HYBRID_MODE = True  # True = 2-char + selective 3-char, False = just 2-char

# Line 30: Your burner account
BURNER_USERNAME = "stinsonoscar2burner2"  # Change for each burner!

# Line 32: Cookie file
COOKIE_FILE = "instagram_cookies_burner2.pkl"  # Change for each burner!
```

---

## How to Run

1. **Update credentials** (lines 30, 32)
2. **Run the scraper**:
   ```
   python alphabet_follower_scraper.py
   ```
3. **Go do something else** - this takes 4-5 hours!

---

## What You'll See

### Pass 1 Output:
```
PASS 1: 2-CHARACTER SEARCH
Searching 676 patterns (aa-zz)

[PROGRESS] Pattern 1/676: 'aa'
[SEARCH] Searching for: 'aa'
[RESULT] Found 15 followers for 'aa'
[STATS] Found 15 total | 15 new unique
[STATS] Total unique followers so far: 15
```

### Between Passes:
```
PASS 1 COMPLETE!
Total unique followers from 2-char search: 3,247

PASS 2: 3-CHARACTER DEEP DIVE
Found 87 high-density patterns (≥25 followers)
Patterns: jo, ma, ch, al, an, mi, sa, br, da, ja...
Will search 2,262 3-character patterns
Estimated time: 107 minutes
```

### Pass 2 Output:
```
[PROGRESS] 3-Char 1/2262: 'joa'
[SEARCH] Searching for: 'joa'
[RESULT] Found 8 followers for 'joa'
[STATS] Found 8 total | 5 new unique
[STATS] Total unique followers: 3,252
```

### Final Results:
```
PASS 2 COMPLETE!
New unique followers from 3-char deep dive: 1,847

HYBRID SCRAPING COMPLETE!
Final unique follower count: 5,094

[SAVED] Saved to followers_alphabet_20251213_1430.json
```

---

## Adjusting the Threshold

If you want MORE 3-char searches (more thorough):
```python
HIGH_DENSITY_THRESHOLD = 15  # Lower = more 3-char searches, more time
```

If you want FEWER 3-char searches (faster):
```python
HIGH_DENSITY_THRESHOLD = 40  # Higher = fewer 3-char searches, less time
```

If you want to DISABLE Pass 2 entirely (just 2-char):
```python
USE_HYBRID_MODE = False  # Only does Pass 1
```

---

## Expected Results by Mode

| Mode | Patterns | Time | Expected Followers |
|------|----------|------|-------------------|
| 2-char only | 676 | 2-3 hrs | 3,000-4,000 |
| **Hybrid (recommended)** | **676 + ~2,000** | **4-5 hrs** | **4,000-6,000** |
| Full 3-char | 17,576 | 17+ hrs | 8,000-12,000 |

---

## Multiple Burners Strategy

Run this hybrid scraper with **3-4 burner accounts**:

**Burner #1**: 5,000 followers
**Burner #2**: 5,000 followers
**Burner #3**: 5,000 followers
**Burner #4**: 5,000 followers

**Total: 15,000-20,000 unique followers!**

Each burner takes 4-5 hours, so you can run one per day and have all followers in a week.

---

## Troubleshooting

**"No high-density patterns found"**
- Your threshold is too high! Lower HIGH_DENSITY_THRESHOLD to 10-15

**Takes too long**
- Increase HIGH_DENSITY_THRESHOLD to 40-50
- Or set USE_HYBRID_MODE = False

**Account gets blocked**
- Use longer pauses (edit line 374, 426)
- Run for shorter periods, resume later

---

## Files Created

The scraper saves to: `followers_alphabet_YYYYMMDD_HHMM.json`

Example: `followers_alphabet_20251213_1430.json`

This contains all unique followers with:
- username
- profile_url
- profile_pic_url
