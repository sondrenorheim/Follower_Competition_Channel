# Example Import Files

This folder contains example files showing how to import your own follower lists.

## File Formats Supported

### 1. Simple CSV (`followers_example.csv`)
- Most common format
- Must have a `username` column header
- Easy to create in Excel or Google Sheets

### 2. Plain Text (`followers_example.txt`)
- Simplest format
- One username per line
- No headers needed

### 3. Simple JSON Array (`followers_simple.json`)
- JSON array of usernames
- Easy to create manually

### 4. Instagram Data Download Format (`followers_instagram_format.json`)
- Official Instagram export format
- From Instagram's "Download Your Data" feature
- Automatically parsed by the game

## How to Use

1. **Choose or create your file** in one of the formats above
2. **Place it anywhere** (e.g., in this `examples/` folder or root directory)
3. **Edit `config.py`:**
   ```python
   FOLLOWER_IMPORT_FILE = "examples/followers_example.csv"
   ```
4. **Run the game:**
   ```bash
   python main.py
   ```

## Getting Real Follower Data (100% Safe & Legal)

### Option 1: Instagram Data Download (Best!)

1. **Request your data:**
   - Instagram App → Settings → Security → Download Data
   - Or: instagram.com/download/request

2. **Wait for email** (24-48 hours)

3. **Download and extract** the ZIP file

4. **Find `followers.json`** in the extracted folder

5. **Use it:**
   ```python
   FOLLOWER_IMPORT_FILE = "path/to/followers.json"
   ```

### Option 2: Manual Entry

Create your own CSV file:
```csv
username
your_friend1
your_friend2
your_follower3
```

### Option 3: Mix Real + Generated

Import a small list of real followers, the game will generate more to reach your target count!

## Notes

- Imported followers will have **colored circle avatars** (not profile pictures)
- This is the **safest and legal** way to use real usernames
- No account risk, no API needed, no scraping required
- Works offline after initial import
