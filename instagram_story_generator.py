#!/usr/bin/env python3
"""
Instagram Story Generator
Generates branded story images showing top 3 daily performers
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math


def _load_game_history(history_file: str = "game_history.json") -> dict:
    """Load game history JSON file"""
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {history_file} not found")
        return {"games": []}
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {history_file}: {e}")
        return {"games": []}


def get_top_3_daily_performers(day_number: int) -> List[Dict]:
    """
    Get top 3 performers for a specific day based on total points

    Args:
        day_number: The day number to query

    Returns:
        List of dicts with username, total_points, rank, avatar_path
        Example: [
            {"username": "player1", "total_points": 2847, "rank": 1, "avatar_path": "avatar_cache/player1.jpg"},
            ...
        ]
    """
    history = _load_game_history()

    # Filter games for this day
    day_games = [g for g in history.get('games', []) if g.get('day_number') == day_number]

    if not day_games:
        print(f"WARNING: No games found for day {day_number}")
        return []

    # Aggregate points by player
    player_points = {}
    for game in day_games:
        for result in game.get('results', []):
            username = result.get('username')
            points = result.get('points', 0)

            if username:
                if username not in player_points:
                    player_points[username] = 0
                player_points[username] += points

    # Sort by points descending
    sorted_players = sorted(player_points.items(), key=lambda x: x[1], reverse=True)

    # Get top 3
    top_3 = []
    for i, (username, total_points) in enumerate(sorted_players[:3]):
        avatar_path = Path("avatar_cache") / f"{username}.jpg"

        top_3.append({
            "username": username,
            "total_points": int(total_points),
            "rank": i + 1,
            "avatar_path": str(avatar_path) if avatar_path.exists() else None
        })

    return top_3


def _draw_gradient_background(width: int, height: int, color_top: Tuple[int, int, int],
                              color_bottom: Tuple[int, int, int]) -> Image.Image:
    """
    Create a vertical gradient background

    Args:
        width: Image width
        height: Image height
        color_top: RGB tuple for top color
        color_bottom: RGB tuple for bottom color

    Returns:
        PIL Image with gradient
    """
    base = Image.new('RGB', (width, height), color_top)
    gradient = Image.new('RGB', (width, height), color_top)
    draw = ImageDraw.Draw(gradient)

    # Draw gradient line by line
    for y in range(height):
        # Interpolate between top and bottom colors
        ratio = y / height
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)

        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return gradient


def _load_and_resize_avatar(avatar_path: Optional[str], size: int) -> Optional[Image.Image]:
    """
    Load and resize avatar image

    Args:
        avatar_path: Path to avatar image file (or None)
        size: Target size (diameter)

    Returns:
        PIL Image or None if not found
    """
    if not avatar_path or not Path(avatar_path).exists():
        return None

    try:
        img = Image.open(avatar_path)
        img = img.convert('RGB')
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"WARNING: Failed to load avatar {avatar_path}: {e}")
        return None


def _create_circular_avatar(img: Optional[Image.Image], size: int, username: str,
                            border_width: int = 6, border_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    Create circular avatar with border and shadow

    Args:
        img: Avatar image or None (will generate initials if None)
        size: Diameter of circle
        username: Username for fallback initials
        border_width: Border thickness
        border_color: Border RGB color

    Returns:
        PIL Image (RGBA) with circular avatar
    """
    # Create canvas with transparency
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # If no avatar, create gradient circle with initials
    if img is None:
        # Draw gradient background circle
        gradient_colors = [
            (100, 150, 255),  # Blue
            (255, 100, 150),  # Pink
            (150, 255, 100),  # Green
            (255, 200, 100),  # Orange
        ]
        # Pick color based on username hash
        color = gradient_colors[hash(username) % len(gradient_colors)]

        # Draw filled circle
        draw.ellipse([0, 0, size, size], fill=color)

        # Draw initials
        initials = username[:2].upper()
        try:
            font = ImageFont.truetype("arial.ttf", size // 3)
        except:
            font = ImageFont.load_default()

        # Center text
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2

        draw.text((x, y), initials, fill=(255, 255, 255), font=font)
    else:
        # Create circular mask
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, size, size], fill=255)

        # Apply mask to avatar
        img.putalpha(mask)
        canvas.paste(img, (0, 0), img)

    # Add border
    if border_width > 0:
        for i in range(border_width):
            offset = i
            draw.ellipse([offset, offset, size - offset, size - offset],
                        outline=border_color, width=1)

    return canvas


def _draw_rank_badge(draw: ImageDraw.Draw, x: int, y: int, rank: int, size: int = 80):
    """
    Draw rank badge (1st, 2nd, 3rd)

    Args:
        draw: ImageDraw object
        x: Center X coordinate
        y: Center Y coordinate
        rank: Rank number (1, 2, or 3)
        size: Badge size
    """
    # Badge colors
    badge_colors = {
        1: (255, 215, 0),    # Gold
        2: (192, 192, 192),  # Silver
        3: (205, 127, 50),   # Bronze
    }

    color = badge_colors.get(rank, (128, 128, 128))

    # Draw rounded rectangle badge
    radius = size // 4
    bbox = [x - size // 2, y - size // 2, x + size // 2, y + size // 2]

    # Draw filled rounded rectangle
    draw.rounded_rectangle(bbox, radius=radius, fill=color)

    # Draw rank number
    rank_text = str(rank)
    try:
        font = ImageFont.truetype("arialbd.ttf", size // 2)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", size // 2)
        except:
            font = ImageFont.load_default()

    # Center text
    text_bbox = draw.textbbox((0, 0), rank_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = x - text_width // 2
    text_y = y - text_height // 2

    draw.text((text_x, text_y), rank_text, fill=(255, 255, 255), font=font)


def generate_story_image(day_number: int, output_path: str = "story_generated.png") -> bool:
    """
    Generate Instagram story image for top 3 daily performers

    Args:
        day_number: Day number to generate story for
        output_path: Output file path

    Returns:
        True if successful, False otherwise
    """
    try:
        # Import config for colors and settings
        import config

        # Get settings (with fallbacks)
        width, height = getattr(config, 'STORY_IMAGE_SIZE', (1080, 1920))
        bg_top = getattr(config, 'STORY_BG_COLOR_TOP', (26, 26, 46))
        bg_bottom = getattr(config, 'STORY_BG_COLOR_BOTTOM', (22, 33, 62))
        text_color = getattr(config, 'STORY_TEXT_COLOR', (255, 255, 255))
        accent_color = getattr(config, 'STORY_ACCENT_COLOR', (255, 215, 0))
        avatar_1st_size = getattr(config, 'STORY_AVATAR_SIZE_1ST', 200)
        avatar_2_3_size = getattr(config, 'STORY_AVATAR_SIZE_2_3', 140)
        border_width = getattr(config, 'STORY_AVATAR_BORDER', 6)

        # Get top 3 performers
        print(f"Fetching top 3 performers for day {day_number}...")
        top_3 = get_top_3_daily_performers(day_number)

        if not top_3:
            print("ERROR: No performers found")
            return False

        print(f"Found {len(top_3)} top performers")

        # Create gradient background
        img = _draw_gradient_background(width, height, bg_top, bg_bottom)
        draw = ImageDraw.Draw(img)

        # --- Title Section (top 15%) ---
        title_y = int(height * 0.12)
        title_text = f"DAILY LEADERBOARD"
        day_text = f"DAY {day_number}"

        try:
            title_font = ImageFont.truetype("arialbd.ttf", 70)
            day_font = ImageFont.truetype("arialbd.ttf", 60)
        except:
            try:
                title_font = ImageFont.truetype("arial.ttf", 70)
                day_font = ImageFont.truetype("arial.ttf", 60)
            except:
                title_font = ImageFont.load_default()
                day_font = ImageFont.load_default()

        # Draw title centered
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, title_y), title_text, fill=text_color, font=title_font)

        # Draw day number
        day_bbox = draw.textbbox((0, 0), day_text, font=day_font)
        day_width = day_bbox[2] - day_bbox[0]
        day_x = (width - day_width) // 2
        day_y = title_y + 90
        draw.text((day_x, day_y), day_text, fill=accent_color, font=day_font)

        # Draw accent line
        line_y = day_y + 80
        line_width = 300
        line_x = (width - line_width) // 2
        draw.rectangle([line_x, line_y, line_x + line_width, line_y + 3], fill=accent_color)

        # --- Podium Section (middle 60%) ---
        podium_y_start = int(height * 0.30)
        podium_height = int(height * 0.50)

        # Positions for podium (2nd, 1st, 3rd)
        positions = {
            1: (width // 2, podium_y_start + 50),          # Center, higher
            2: (width // 2 - 280, podium_y_start + 150),   # Left, lower
            3: (width // 2 + 280, podium_y_start + 150),   # Right, lower
        }

        # Font for names and points
        try:
            name_font = ImageFont.truetype("arialbd.ttf", 32)
            points_font = ImageFont.truetype("arialbd.ttf", 40)
        except:
            try:
                name_font = ImageFont.truetype("arial.ttf", 32)
                points_font = ImageFont.truetype("arial.ttf", 40)
            except:
                name_font = ImageFont.load_default()
                points_font = ImageFont.load_default()

        # Draw each performer
        for performer in top_3:
            rank = performer['rank']
            username = performer['username']
            total_points = performer['total_points']
            avatar_path = performer.get('avatar_path')

            # Get position
            x, y = positions[rank]

            # Avatar size based on rank
            avatar_size = avatar_1st_size if rank == 1 else avatar_2_3_size

            # Load and create circular avatar
            avatar_img = _load_and_resize_avatar(avatar_path, avatar_size)
            circular_avatar = _create_circular_avatar(avatar_img, avatar_size, username, border_width)

            # Paste avatar on canvas
            avatar_x = x - avatar_size // 2
            avatar_y = y
            img.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)

            # Draw username below avatar
            name_y = avatar_y + avatar_size + 20
            # Truncate long usernames
            display_name = username if len(username) <= 18 else username[:15] + "..."
            name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = x - name_width // 2
            draw.text((name_x, name_y), display_name, fill=text_color, font=name_font)

            # Draw points below username
            points_text = f"{total_points:,} PTS"
            points_y = name_y + 45
            points_bbox = draw.textbbox((0, 0), points_text, font=points_font)
            points_width = points_bbox[2] - points_bbox[0]
            points_x = x - points_width // 2
            draw.text((points_x, points_y), points_text, fill=accent_color, font=points_font)

            # Draw rank badge below points (increased spacing to avoid overlap)
            badge_y = points_y + 120
            _draw_rank_badge(draw, x, badge_y, rank, size=100 if rank == 1 else 80)

        # --- Bottom CTA Banner (bottom 10%) ---
        cta_y = int(height * 0.78)
        next_day = day_number + 1
        cta_text = f"Follow to compete in Day {next_day}!"

        try:
            cta_font = ImageFont.truetype("arialbd.ttf", 52)
        except:
            try:
                cta_font = ImageFont.truetype("arial.ttf", 52)
            except:
                cta_font = ImageFont.load_default()

        cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        cta_width = cta_bbox[2] - cta_bbox[0]
        cta_x = (width - cta_width) // 2
        draw.text((cta_x, cta_y), cta_text, fill=text_color, font=cta_font)

        # Save image
        img.save(output_path, 'PNG', quality=95)
        print(f"SUCCESS: Story image saved to {output_path}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to generate story image: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Test the generator
    import sys

    day = 20
    if len(sys.argv) > 1:
        day = int(sys.argv[1])

    print(f"Generating story for Day {day}...")

    # Test data aggregation
    top_3 = get_top_3_daily_performers(day)
    print(f"\nTop 3 performers for Day {day}:")
    for performer in top_3:
        print(f"  {performer['rank']}. {performer['username']}: {performer['total_points']:,} points")

    # Test image generation
    output = f"test_story_day_{day}.png"
    if generate_story_image(day, output):
        print(f"\nTest image generated: {output}")
    else:
        print("\nFailed to generate test image")
