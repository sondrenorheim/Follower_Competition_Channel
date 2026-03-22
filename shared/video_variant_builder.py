"""
Build platform-specific video variants without touching the Instagram base export.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import config

_SIGNATURE_VERSION = 6
_YOUTUBE_VARIANT_SIGNATURE_VERSION = 1
_LAST_VARIANT_BUILD_INFO = None
_LAST_YOUTUBE_VARIANT_BUILD_INFO = None


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_list_of_floats(value, default: list[float]) -> list[float]:
    if isinstance(value, (list, tuple, set)):
        parsed = []
        for item in value:
            try:
                parsed.append(float(item))
            except Exception:
                continue
        return parsed if parsed else list(default)
    if isinstance(value, str):
        parsed = []
        for part in value.split(","):
            try:
                parsed.append(float(part.strip()))
            except Exception:
                continue
        return parsed if parsed else list(default)
    return list(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _escape_drawtext_text(text: str) -> str:
    value = str(text or "")
    # Escape characters that ffmpeg drawtext parses specially.
    value = value.replace("\\", "\\\\")
    value = value.replace(":", "\\:")
    value = value.replace("'", "\\'")
    value = value.replace("%", "\\%")
    return value


def _resolve_placement_mode() -> str:
    mode = str(
        getattr(config, "NON_IG_JOIN_FOOTER_PLACEMENT_MODE", "above_result_prompt")
        or "above_result_prompt"
    ).strip().lower()
    if mode not in {"above_result_prompt", "fixed_bottom_margin", "auto_best_fit"}:
        mode = "above_result_prompt"
    return mode


def _compute_fixed_top_y(frame_height: int, box_height: int, bottom_margin: int) -> int:
    height = max(1, int(frame_height or 1))
    box_h = max(1, int(box_height or 1))
    margin = max(0, int(bottom_margin or 0))
    return max(0, min(height - box_h, height - box_h - margin))


def _probe_video_dimensions(base_video_path: Path) -> tuple[int, int, int]:
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        return 1080, 1920, 0
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,nb_frames",
        "-of",
        "json",
        str(base_video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode != 0:
            return 1080, 1920, 0
        payload = json.loads(result.stdout or "{}")
        streams = payload.get("streams") or []
        if not streams:
            return 1080, 1920, 0
        stream = streams[0] if isinstance(streams[0], dict) else {}
        width = max(1, _safe_int(stream.get("width"), 1080))
        height = max(1, _safe_int(stream.get("height"), 1920))
        frame_count = max(0, _safe_int(stream.get("nb_frames"), 0))
        return width, height, frame_count
    except Exception:
        return 1080, 1920, 0


def _detect_arena_top_y(base_video_path: Path) -> int | None:
    """
    Estimate arena top border y-position from a representative frame.
    Returns None if detection fails.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return None

    cap = cv2.VideoCapture(str(base_video_path))
    if not cap.isOpened():
        return None
    try:
        frame_count = max(0, _safe_int(cap.get(cv2.CAP_PROP_FRAME_COUNT), 0))
        sample_index = int(frame_count * 0.25) if frame_count > 0 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            return None

        frame_h, frame_w = frame.shape[:2]
        if frame_h <= 10 or frame_w <= 10:
            return None

        x0 = int(frame_w * 0.12)
        x1 = int(frame_w * 0.88)
        x0 = max(0, min(frame_w - 2, x0))
        x1 = max(x0 + 1, min(frame_w, x1))
        roi = frame[:, x0:x1]
        if roi.size == 0:
            return None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        dark_mask = gray < 42
        dark_fraction = dark_mask.mean(axis=1)

        search_min = max(0, int(frame_h * 0.10))
        search_max = min(frame_h - 1, int(frame_h * 0.60))
        if search_max <= search_min:
            return None

        window = dark_fraction[search_min : search_max + 1]
        if window.size == 0:
            return None
        candidate_rel = int(np.argmax(window))
        candidate_y = search_min + candidate_rel
        if float(window[candidate_rel]) < 0.35:
            return None
        return int(candidate_y)
    except Exception:
        return None
    finally:
        cap.release()


def _detect_result_prompt_center_y(base_video_path: Path, arena_top_hint: int | None = None) -> int | None:
    """
    Detect the center-y of the in-video RESULT prompt text by scanning the
    centered header area above the arena.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return None

    cap = cv2.VideoCapture(str(base_video_path))
    if not cap.isOpened():
        return None
    try:
        frame_count = max(0, _safe_int(cap.get(cv2.CAP_PROP_FRAME_COUNT), 0))
        sample_index = int(frame_count * 0.20) if frame_count > 0 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            return None

        frame_h, frame_w = frame.shape[:2]
        if frame_h <= 20 or frame_w <= 20:
            return None

        x0 = int(frame_w * 0.18)
        x1 = int(frame_w * 0.82)
        x0 = max(0, min(frame_w - 2, x0))
        x1 = max(x0 + 1, min(frame_w, x1))
        roi = frame[:, x0:x1]
        if roi.size == 0:
            return None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        text_mask = gray < 78

        # Keep only the top area where title/subtitle/result prompt live.
        if arena_top_hint is None:
            search_end = int(frame_h * 0.36)
        else:
            search_end = min(frame_h - 1, int(arena_top_hint) - 10)
        search_end = max(20, search_end)

        row_fraction = text_mask[:search_end, :].mean(axis=1)
        active_rows = np.where(row_fraction > 0.012)[0]
        if active_rows.size == 0:
            return None

        runs: list[tuple[int, int]] = []
        start = int(active_rows[0])
        prev = start
        for raw in active_rows[1:]:
            y = int(raw)
            if y <= prev + 2:
                prev = y
                continue
            if prev - start >= 2:
                runs.append((start, prev))
            start = y
            prev = y
        if prev - start >= 2:
            runs.append((start, prev))
        if not runs:
            return None

        # Prompt is the lowest text run above the arena.
        run_start, run_end = runs[-1]
        return int(round((run_start + run_end) / 2.0))
    except Exception:
        return None
    finally:
        cap.release()


def _estimate_result_prompt_center_y(base_video_path: Path, frame_height: int) -> int:
    """
    Estimate the existing RESULT prompt center-y using arena/top-text layout.
    """
    screen_height = max(1, _safe_int(getattr(config, "SCREEN_HEIGHT", 960), 960))
    scale = float(max(1, frame_height)) / float(screen_height)

    default_arena_top = _safe_int(
        getattr(
            config,
            "MAZE_RUSH_ARENA_RECT",
            getattr(config, "FIGHTER_ARENA_RECT", (40, 180, 500, 500)),
        )[1],
        180,
    )
    default_arena_top_scaled = int(round(default_arena_top * scale))
    arena_top_detected = _detect_arena_top_y(base_video_path)
    arena_top = float(default_arena_top_scaled)
    if arena_top_detected is not None:
        # CV detection occasionally locks onto wrong dark rows.
        # Only trust it when it is reasonably close to configured layout.
        if abs(int(arena_top_detected) - int(default_arena_top_scaled)) <= max(24, int(round(32 * scale))):
            arena_top = float(arena_top_detected)

    prompt_margin = max(
        1,
        int(
            round(
                _safe_int(getattr(config, "MAZE_RUSH_PROMPT_ABOVE_ARENA_MARGIN", 8), 8) * scale
            )
        ),
    )
    header_shift = int(round(_safe_int(getattr(config, "SQUARE_ARENA_HEADER_Y_SHIFT", -4), -4) * scale))
    subtitle_center_y = int(round(arena_top - (40.0 * scale) + header_shift))
    subtitle_half_height = max(5, int(round(0.34 * 32 * scale)))
    subtitle_bottom_plus_margin = subtitle_center_y + subtitle_half_height + max(2, int(round(6 * scale)))

    prompt_center_y = int(round(max(arena_top - prompt_margin, subtitle_bottom_plus_margin)))

    prompt_detected = _detect_result_prompt_center_y(base_video_path, int(round(arena_top)))
    if prompt_detected is not None:
        if abs(int(prompt_detected) - int(prompt_center_y)) <= max(20, int(round(60 * scale))):
            prompt_center_y = int(prompt_detected)

    return max(0, min(max(1, frame_height - 1), prompt_center_y))


def _compute_join_above_result_center_y(base_video_path: Path, frame_height: int) -> int:
    result_center_y = _estimate_result_prompt_center_y(base_video_path, frame_height)
    screen_height = max(1, _safe_int(getattr(config, "SCREEN_HEIGHT", 960), 960))
    scale = float(max(1, frame_height)) / float(screen_height)
    configured_gap = max(
        8,
        int(
            round(
                _safe_int(getattr(config, "NON_IG_JOIN_ABOVE_RESULT_LINE_GAP", 20), 20) * scale
            )
        ),
    )
    join_font_px = max(
        10,
        int(
            round(
                _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_FONT_SIZE", 18), 18) * scale
            )
        ),
    )
    # Approximate rendered glyph heights (text pixels are smaller than font size).
    result_text_px = max(10, int(round(24 * scale * 0.55)))
    join_text_px = max(8, int(round(join_font_px * 0.60)))
    non_overlap_gap = int(round((join_text_px + result_text_px) * 0.5)) + max(2, int(round(3 * scale)))
    line_gap = max(configured_gap, non_overlap_gap)

    join_center_y = result_center_y - line_gap
    return max(0, min(max(1, frame_height - 1), int(join_center_y)))


def _analyze_video_occupied_rows(
    base_video_path: Path,
    sample_ratios: list[float],
    center_x_min_pct: float,
    center_x_max_pct: float,
    pixel_diff_threshold: int,
    row_occupancy_threshold: float,
) -> dict:
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        return {
            "ok": False,
            "error": f"opencv_or_numpy_unavailable: {exc}",
            "occupied_rows": set(),
            "sampled_frames": 0,
            "width": 0,
            "height": 0,
            "frame_count": 0,
        }

    cap = cv2.VideoCapture(str(base_video_path))
    if not cap.isOpened():
        return {
            "ok": False,
            "error": "opencv_open_failed",
            "occupied_rows": set(),
            "sampled_frames": 0,
            "width": 0,
            "height": 0,
            "frame_count": 0,
        }

    width = max(1, _safe_int(cap.get(cv2.CAP_PROP_FRAME_WIDTH), 1080))
    height = max(1, _safe_int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT), 1920))
    frame_count = max(0, _safe_int(cap.get(cv2.CAP_PROP_FRAME_COUNT), 0))

    ratios = [float(_clamp(r, 0.0, 1.0)) for r in sample_ratios]
    if not ratios:
        ratios = [0.05, 0.25, 0.5, 0.75, 0.95]

    if frame_count > 0:
        sample_indices = sorted({min(frame_count - 1, max(0, int(frame_count * ratio))) for ratio in ratios})
    else:
        sample_indices = [0]

    x_min = _clamp(center_x_min_pct, 0.0, 0.95)
    x_max = _clamp(center_x_max_pct, x_min + 0.01, 1.0)

    occupied_rows: set[int] = set()
    sampled_frames = 0

    for frame_index in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        sampled_frames += 1
        frame_h, frame_w = frame.shape[:2]
        if frame_h <= 0 or frame_w <= 0:
            continue

        roi_x0 = int(round(frame_w * x_min))
        roi_x1 = int(round(frame_w * x_max))
        roi_x0 = max(0, min(frame_w - 2, roi_x0))
        roi_x1 = max(roi_x0 + 1, min(frame_w, roi_x1))
        roi = frame[:, roi_x0:roi_x1]
        if roi.size == 0:
            continue

        roi_h, roi_w = roi.shape[:2]
        patch_h = max(40, min(220, roi_h // 6))
        patch_w = max(40, min(220, roi_w // 3))
        py1 = max(1, roi_h - 20)
        py0 = max(0, py1 - patch_h)
        px1 = max(1, roi_w - 20)
        px0 = max(0, px1 - patch_w)
        patch = roi[py0:py1, px0:px1]
        if patch.size == 0:
            py0 = max(0, roi_h - 120)
            px0 = max(0, roi_w - 120)
            patch = roi[py0:roi_h, px0:roi_w]
        if patch.size == 0:
            continue

        bg_color = np.median(patch.reshape(-1, 3), axis=0)
        diff = np.abs(roi.astype(np.int16) - bg_color.astype(np.int16)).sum(axis=2)
        row_mask = diff > int(max(1, pixel_diff_threshold))
        row_fraction = row_mask.mean(axis=1)
        active_rows = np.where(row_fraction > float(max(0.001, row_occupancy_threshold)))[0]
        for row_idx in active_rows:
            if 0 <= int(row_idx) < frame_h:
                occupied_rows.add(int(row_idx))

    cap.release()

    return {
        "ok": sampled_frames > 0,
        "error": "" if sampled_frames > 0 else "no_sampled_frames",
        "occupied_rows": occupied_rows,
        "sampled_frames": sampled_frames,
        "width": width,
        "height": height,
        "frame_count": frame_count,
    }


def _compute_join_footer_top_y(base_video_path: Path, box_height: int) -> int:
    placement_mode = _resolve_placement_mode()
    _, probed_height, _ = _probe_video_dimensions(base_video_path)

    if placement_mode == "fixed_bottom_margin":
        fixed_margin = max(
            0,
            _safe_int(
                getattr(
                    config,
                    "NON_IG_JOIN_FOOTER_FIXED_BOTTOM_MARGIN",
                    getattr(config, "NON_IG_JOIN_FOOTER_BOTTOM_MARGIN", 10),
                ),
                10,
            ),
        )
        return _compute_fixed_top_y(probed_height, box_height, fixed_margin)

    sample_ratios = _safe_list_of_floats(
        getattr(config, "NON_IG_JOIN_FOOTER_AUTO_SAMPLE_RATIOS", [0.05, 0.25, 0.5, 0.75, 0.95]),
        [0.05, 0.25, 0.5, 0.75, 0.95],
    )
    center_x_min_pct = _safe_float(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MIN_PCT", 0.20), 0.20)
    center_x_max_pct = _safe_float(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MAX_PCT", 0.80), 0.80)
    pixel_diff_threshold = max(
        1,
        _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_PIXEL_DIFF_THRESHOLD", 28), 28),
    )
    row_occupancy_threshold = _safe_float(
        getattr(config, "NON_IG_JOIN_FOOTER_AUTO_ROW_OCCUPANCY_THRESHOLD", 0.02),
        0.02,
    )
    reserved_bottom_ui_px = max(
        0,
        _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_RESERVED_BOTTOM_UI_PX", 180), 180),
    )
    min_top_px = max(0, _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_MIN_TOP_PX", 1480), 1480))
    max_top_px = max(0, _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_MAX_TOP_PX", 1760), 1760))
    row_gap_px = max(0, _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_ROW_GAP_PX", 10), 10))
    fallback_bottom_margin = max(
        0,
        _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_AUTO_FALLBACK_BOTTOM_MARGIN", 220), 220),
    )

    analysis = _analyze_video_occupied_rows(
        base_video_path=base_video_path,
        sample_ratios=sample_ratios,
        center_x_min_pct=center_x_min_pct,
        center_x_max_pct=center_x_max_pct,
        pixel_diff_threshold=pixel_diff_threshold,
        row_occupancy_threshold=row_occupancy_threshold,
    )

    frame_height = max(1, _safe_int(analysis.get("height"), probed_height))
    max_top_by_ui = max(0, frame_height - int(box_height) - reserved_bottom_ui_px)
    search_min = max(0, min(min_top_px, max_top_by_ui))
    search_max = max(0, min(max_top_px, max_top_by_ui))
    if search_max < search_min:
        search_min = search_max

    occupied_rows = analysis.get("occupied_rows") or set()
    if analysis.get("ok"):
        if not occupied_rows:
            return search_max
        for candidate_top in range(search_max, search_min - 1, -1):
            band_start = max(0, candidate_top - row_gap_px)
            band_end = min(frame_height - 1, candidate_top + int(box_height) + row_gap_px - 1)
            intersects = False
            for row in range(band_start, band_end + 1):
                if row in occupied_rows:
                    intersects = True
                    break
            if not intersects:
                return candidate_top

    fallback_top = _compute_fixed_top_y(frame_height, box_height, fallback_bottom_margin)
    return max(0, min(max_top_by_ui, fallback_top))


def _build_filter_expression(base_video_path: Path) -> tuple[str, int, str]:
    text = str(getattr(config, "NON_IG_JOIN_FOOTER_TEXT", "") or "").strip()
    if not text:
        return "", 0, _resolve_placement_mode()

    placement_mode = _resolve_placement_mode()
    base_font_size = max(10, _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_FONT_SIZE", 18), 18))
    escaped_text = _escape_drawtext_text(text)
    _, frame_height, _ = _probe_video_dimensions(base_video_path)

    if placement_mode == "above_result_prompt":
        screen_height = max(1, _safe_int(getattr(config, "SCREEN_HEIGHT", 960), 960))
        scale = float(max(1, frame_height)) / float(screen_height)
        font_size = max(10, int(round(base_font_size * scale)))
        anchor_center_y = _compute_join_above_result_center_y(base_video_path, frame_height)
        font_color = str(getattr(config, "NON_IG_JOIN_ABOVE_RESULT_FONT_COLOR", "black") or "black").strip() or "black"
        border_opacity = _clamp(
            _safe_float(getattr(config, "NON_IG_JOIN_ABOVE_RESULT_SHADOW_OPACITY", 0.45), 0.45),
            0.0,
            1.0,
        )
        return (
            f"drawtext=text='{escaped_text}':x=(w-text_w)/2:y={anchor_center_y}-(text_h/2):"
            f"fontsize={font_size}:fontcolor={font_color}:borderw=2:bordercolor=white@{border_opacity}",
            anchor_center_y,
            placement_mode,
        )

    font_size = base_font_size
    box_height = max(24, _safe_int(getattr(config, "NON_IG_JOIN_FOOTER_BOX_HEIGHT", 56), 56))
    box_opacity = _clamp(
        _safe_float(getattr(config, "NON_IG_JOIN_FOOTER_BOX_OPACITY", 0.55), 0.55),
        0.0,
        1.0,
    )
    top_y = _compute_join_footer_top_y(base_video_path, box_height)
    text_y_expr = f"{top_y}+(({box_height}-text_h)/2)"
    return (
        f"drawbox=x=0:y={top_y}:w=iw:h={box_height}:color=black@{box_opacity}:t=fill,"
        f"drawtext=text='{escaped_text}':x=(w-text_w)/2:y={text_y_expr}:"
        f"fontsize={font_size}:fontcolor=white:shadowcolor=black@0.7:shadowx=2:shadowy=2",
        top_y,
        placement_mode,
    )


def _build_youtube_short_filter_expression(base_video_path: Path) -> tuple[str, dict]:
    context_text = str(getattr(config, "YOUTUBE_SHORTS_CONTEXT_TEXT", "") or "").strip()
    stakes_text = str(getattr(config, "YOUTUBE_SHORTS_STAKES_TEXT", "") or "").strip()
    if not context_text or not stakes_text:
        return "", {}

    _, frame_height, _ = _probe_video_dimensions(base_video_path)
    screen_height = max(1, _safe_int(getattr(config, "SCREEN_HEIGHT", 1920), 1920))
    scale = float(max(1, frame_height)) / float(screen_height)

    duration = max(
        0.25,
        _safe_float(getattr(config, "YOUTUBE_SHORTS_HOOK_DURATION_SECONDS", 3.0), 3.0),
    )
    overlay_opacity = _clamp(
        _safe_float(getattr(config, "YOUTUBE_SHORTS_HOOK_OVERLAY_OPACITY", 0.38), 0.38),
        0.0,
        1.0,
    )
    context_font_size = max(
        14,
        int(round(_safe_int(getattr(config, "YOUTUBE_SHORTS_CONTEXT_FONT_SIZE", 26), 26) * scale)),
    )
    stakes_font_size = max(
        18,
        int(round(_safe_int(getattr(config, "YOUTUBE_SHORTS_STAKES_FONT_SIZE", 40), 40) * scale)),
    )
    context_color = str(getattr(config, "YOUTUBE_SHORTS_CONTEXT_COLOR", "white") or "white").strip() or "white"
    stakes_color = str(getattr(config, "YOUTUBE_SHORTS_STAKES_COLOR", "white") or "white").strip() or "white"
    border_color = str(
        getattr(config, "YOUTUBE_SHORTS_TEXT_BORDER_COLOR", "black@0.75") or "black@0.75"
    ).strip() or "black@0.75"
    border_width = max(
        1,
        _safe_int(getattr(config, "YOUTUBE_SHORTS_TEXT_BORDER_WIDTH", 3), 3),
    )
    context_center_y = int(round(frame_height * 0.43))
    stakes_center_y = int(round(frame_height * 0.50))
    enable_expr = f"between(t,0,{duration:.2f})"

    escaped_context = _escape_drawtext_text(context_text)
    escaped_stakes = _escape_drawtext_text(stakes_text)
    filter_expression = ",".join(
        [
            (
                "drawbox="
                f"x=0:y=0:w=iw:h=ih:color=black@{overlay_opacity}:t=fill:"
                f"enable='{enable_expr}'"
            ),
            (
                "drawtext="
                f"text='{escaped_context}':x=(w-text_w)/2:y={context_center_y}-(text_h/2):"
                f"fontsize={context_font_size}:fontcolor={context_color}:"
                f"borderw={border_width}:bordercolor={border_color}:"
                f"enable='{enable_expr}'"
            ),
            (
                "drawtext="
                f"text='{escaped_stakes}':x=(w-text_w)/2:y={stakes_center_y}-(text_h/2):"
                f"fontsize={stakes_font_size}:fontcolor={stakes_color}:"
                f"borderw={border_width}:bordercolor={border_color}:"
                f"enable='{enable_expr}'"
            ),
        ]
    )
    build_meta = {
        "context_text": context_text,
        "stakes_text": stakes_text,
        "duration_seconds": duration,
        "overlay_opacity": overlay_opacity,
        "context_font_size": context_font_size,
        "stakes_font_size": stakes_font_size,
    }
    return filter_expression, build_meta


def _meta_path(output_video_path: Path) -> Path:
    output_path = Path(output_video_path)
    return output_path.with_suffix(f"{output_path.suffix}.meta.json")


def _read_variant_meta(output_video_path: Path) -> dict | None:
    path = _meta_path(output_video_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_variant_meta(output_video_path: Path, payload: dict) -> None:
    path = _meta_path(output_video_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def read_non_ig_variant_meta(output_video_path: Path) -> dict | None:
    """Read non-IG variant metadata sidecar if present."""
    return _read_variant_meta(output_video_path)


def _build_variant_signature(base_video_path: Path) -> dict:
    base_path = Path(base_video_path)
    try:
        base_stat = base_path.stat()
        base_size = int(base_stat.st_size)
        base_mtime_ns = int(base_stat.st_mtime_ns)
    except Exception:
        base_size = 0
        base_mtime_ns = 0

    payload = {
        "signature_version": _SIGNATURE_VERSION,
        "base_video": {
            "filename": base_path.name,
            "size": base_size,
            "mtime_ns": base_mtime_ns,
        },
        "config": {
            "NON_IG_JOIN_FOOTER_ENABLED": _safe_bool(
                getattr(config, "NON_IG_JOIN_FOOTER_ENABLED", True), True
            ),
            "NON_IG_JOIN_FOOTER_TEXT": str(getattr(config, "NON_IG_JOIN_FOOTER_TEXT", "") or ""),
            "NON_IG_JOIN_FOOTER_FONT_SIZE": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_FONT_SIZE", 18), 18
            ),
            "NON_IG_JOIN_ABOVE_RESULT_LINE_GAP": _safe_int(
                getattr(config, "NON_IG_JOIN_ABOVE_RESULT_LINE_GAP", 20), 20
            ),
            "NON_IG_JOIN_ABOVE_RESULT_FONT_COLOR": str(
                getattr(config, "NON_IG_JOIN_ABOVE_RESULT_FONT_COLOR", "black") or "black"
            ),
            "NON_IG_JOIN_ABOVE_RESULT_SHADOW_OPACITY": _safe_float(
                getattr(config, "NON_IG_JOIN_ABOVE_RESULT_SHADOW_OPACITY", 0.45), 0.45
            ),
            "SQUARE_ARENA_HEADER_Y_SHIFT": _safe_int(
                getattr(config, "SQUARE_ARENA_HEADER_Y_SHIFT", -4), -4
            ),
            "NON_IG_JOIN_FOOTER_BOX_HEIGHT": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_BOX_HEIGHT", 56), 56
            ),
            "NON_IG_JOIN_FOOTER_BOX_OPACITY": _safe_float(
                getattr(config, "NON_IG_JOIN_FOOTER_BOX_OPACITY", 0.55), 0.55
            ),
            "NON_IG_JOIN_FOOTER_BOTTOM_MARGIN": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_BOTTOM_MARGIN", 10), 10
            ),
            "NON_IG_JOIN_FOOTER_PLACEMENT_MODE": _resolve_placement_mode(),
            "NON_IG_JOIN_FOOTER_FIXED_BOTTOM_MARGIN": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_FIXED_BOTTOM_MARGIN", 10), 10
            ),
            "NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MIN_PCT": _safe_float(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MIN_PCT", 0.20), 0.20
            ),
            "NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MAX_PCT": _safe_float(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_CENTER_X_MAX_PCT", 0.80), 0.80
            ),
            "NON_IG_JOIN_FOOTER_AUTO_SAMPLE_RATIOS": _safe_list_of_floats(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_SAMPLE_RATIOS", [0.05, 0.25, 0.5, 0.75, 0.95]),
                [0.05, 0.25, 0.5, 0.75, 0.95],
            ),
            "NON_IG_JOIN_FOOTER_AUTO_PIXEL_DIFF_THRESHOLD": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_PIXEL_DIFF_THRESHOLD", 28), 28
            ),
            "NON_IG_JOIN_FOOTER_AUTO_ROW_OCCUPANCY_THRESHOLD": _safe_float(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_ROW_OCCUPANCY_THRESHOLD", 0.02), 0.02
            ),
            "NON_IG_JOIN_FOOTER_AUTO_RESERVED_BOTTOM_UI_PX": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_RESERVED_BOTTOM_UI_PX", 180), 180
            ),
            "NON_IG_JOIN_FOOTER_AUTO_MIN_TOP_PX": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_MIN_TOP_PX", 1480), 1480
            ),
            "NON_IG_JOIN_FOOTER_AUTO_MAX_TOP_PX": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_MAX_TOP_PX", 1760), 1760
            ),
            "NON_IG_JOIN_FOOTER_AUTO_ROW_GAP_PX": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_ROW_GAP_PX", 10), 10
            ),
            "NON_IG_JOIN_FOOTER_AUTO_FALLBACK_BOTTOM_MARGIN": _safe_int(
                getattr(config, "NON_IG_JOIN_FOOTER_AUTO_FALLBACK_BOTTOM_MARGIN", 220), 220
            ),
        },
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    return {"hash": digest, "payload": payload}


def _build_youtube_variant_signature(base_video_path: Path) -> dict:
    base_path = Path(base_video_path)
    try:
        base_stat = base_path.stat()
        base_size = int(base_stat.st_size)
        base_mtime_ns = int(base_stat.st_mtime_ns)
    except Exception:
        base_size = 0
        base_mtime_ns = 0

    payload = {
        "signature_version": _YOUTUBE_VARIANT_SIGNATURE_VERSION,
        "base_video": {
            "filename": base_path.name,
            "size": base_size,
            "mtime_ns": base_mtime_ns,
        },
        "config": {
            "YOUTUBE_SHORTS_CONTEXT_TEXT": str(
                getattr(config, "YOUTUBE_SHORTS_CONTEXT_TEXT", "") or ""
            ),
            "YOUTUBE_SHORTS_STAKES_TEXT": str(
                getattr(config, "YOUTUBE_SHORTS_STAKES_TEXT", "") or ""
            ),
            "YOUTUBE_SHORTS_HOOK_DURATION_SECONDS": _safe_float(
                getattr(config, "YOUTUBE_SHORTS_HOOK_DURATION_SECONDS", 3.0), 3.0
            ),
            "YOUTUBE_SHORTS_HOOK_OVERLAY_OPACITY": _safe_float(
                getattr(config, "YOUTUBE_SHORTS_HOOK_OVERLAY_OPACITY", 0.38), 0.38
            ),
            "YOUTUBE_SHORTS_CONTEXT_FONT_SIZE": _safe_int(
                getattr(config, "YOUTUBE_SHORTS_CONTEXT_FONT_SIZE", 26), 26
            ),
            "YOUTUBE_SHORTS_STAKES_FONT_SIZE": _safe_int(
                getattr(config, "YOUTUBE_SHORTS_STAKES_FONT_SIZE", 40), 40
            ),
            "YOUTUBE_SHORTS_CONTEXT_COLOR": str(
                getattr(config, "YOUTUBE_SHORTS_CONTEXT_COLOR", "white") or "white"
            ),
            "YOUTUBE_SHORTS_STAKES_COLOR": str(
                getattr(config, "YOUTUBE_SHORTS_STAKES_COLOR", "white") or "white"
            ),
            "YOUTUBE_SHORTS_TEXT_BORDER_COLOR": str(
                getattr(config, "YOUTUBE_SHORTS_TEXT_BORDER_COLOR", "black@0.75")
                or "black@0.75"
            ),
            "YOUTUBE_SHORTS_TEXT_BORDER_WIDTH": _safe_int(
                getattr(config, "YOUTUBE_SHORTS_TEXT_BORDER_WIDTH", 3), 3
            ),
        },
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    return {"hash": digest, "payload": payload}


def get_last_non_ig_variant_build_info() -> dict | None:
    if not isinstance(_LAST_VARIANT_BUILD_INFO, dict):
        return None
    return dict(_LAST_VARIANT_BUILD_INFO)


def get_last_youtube_variant_build_info() -> dict | None:
    if not isinstance(_LAST_YOUTUBE_VARIANT_BUILD_INFO, dict):
        return None
    return dict(_LAST_YOUTUBE_VARIANT_BUILD_INFO)


def build_non_ig_join_variant(base_video_path: Path, output_video_path: Path) -> bool:
    """
    Build the non-IG JOIN-footer variant from a base video.
    Returns True on success, False on failure.
    """
    global _LAST_VARIANT_BUILD_INFO

    base_path = Path(base_video_path)
    output_path = Path(output_video_path)
    placement_mode = _resolve_placement_mode()

    if not base_path.exists():
        print(f"[WARN] Variant generation skipped: missing base video {base_path}")
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "missing_base",
            "output_path": str(output_path),
        }
        return False

    if not _safe_bool(getattr(config, "NON_IG_VARIANT_ENABLED", True), True):
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "variant_disabled",
            "output_path": str(output_path),
        }
        return False
    if not _safe_bool(getattr(config, "NON_IG_JOIN_FOOTER_ENABLED", True), True):
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "footer_disabled",
            "output_path": str(output_path),
        }
        return False

    filter_expression, top_y, placement_mode = _build_filter_expression(base_path)
    if not filter_expression:
        print("[WARN] Variant generation skipped: NON_IG_JOIN_FOOTER_TEXT is empty.")
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "empty_text",
            "output_path": str(output_path),
        }
        return False

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        print("[WARN] Variant generation failed: ffmpeg is not available on PATH.")
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "missing_ffmpeg",
            "output_path": str(output_path),
        }
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(base_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        filter_expression,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except Exception as exc:
        print(f"[WARN] Variant generation failed: {exc}")
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "ffmpeg_exec_error",
            "error": str(exc),
            "output_path": str(output_path),
            "top_y": int(top_y),
        }
        return False

    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()
        if len(stderr_tail) > 500:
            stderr_tail = stderr_tail[-500:]
        print(f"[WARN] Variant generation failed (ffmpeg exit {result.returncode}): {stderr_tail}")
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception:
            pass
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "placement_mode": placement_mode,
            "status": "ffmpeg_failed",
            "output_path": str(output_path),
            "top_y": int(top_y),
        }
        return False

    signature = _build_variant_signature(base_path)
    meta_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output_path),
        "base_video_path": str(base_path),
        "placement_mode": placement_mode,
        "top_y": int(top_y),
        "signature": signature.get("hash"),
        "signature_payload": signature.get("payload"),
    }
    try:
        _write_variant_meta(output_path, meta_payload)
    except Exception as exc:
        print(f"[WARN] Failed to write variant metadata sidecar for {output_path.name}: {exc}")

    _LAST_VARIANT_BUILD_INFO = {
        "generated": True,
        "placement_mode": placement_mode,
        "status": "generated",
        "output_path": str(output_path),
        "top_y": int(top_y),
    }
    return output_path.exists()


def ensure_non_ig_join_variant(base_video_path: Path, output_video_path: Path) -> Path:
    """
    Ensure variant exists and is fresh. Returns variant path on success,
    otherwise returns the base path.
    """
    global _LAST_VARIANT_BUILD_INFO

    base_path = Path(base_video_path)
    output_path = Path(output_video_path)

    if not base_path.exists():
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "missing_base",
            "output_path": str(output_path),
        }
        return base_path

    rebuild_reasons: list[str] = []
    signature = _build_variant_signature(base_path)

    if not output_path.exists():
        rebuild_reasons.append("variant_missing")
    else:
        meta = _read_variant_meta(output_path)
        if meta is None:
            rebuild_reasons.append("meta_missing")
        else:
            existing_sig = str(meta.get("signature") or "").strip()
            expected_sig = str(signature.get("hash") or "").strip()
            if not existing_sig or existing_sig != expected_sig:
                rebuild_reasons.append("signature_mismatch")
        try:
            if output_path.stat().st_mtime < base_path.stat().st_mtime:
                rebuild_reasons.append("base_newer")
        except Exception:
            rebuild_reasons.append("mtime_check_failed")

    if not rebuild_reasons:
        meta = _read_variant_meta(output_path) or {}
        _LAST_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "up_to_date",
            "output_path": str(output_path),
            "top_y": meta.get("top_y"),
            "placement_mode": meta.get("placement_mode"),
        }
        return output_path

    if build_non_ig_join_variant(base_path, output_path):
        info = dict(_LAST_VARIANT_BUILD_INFO or {})
        info["rebuild_reasons"] = list(dict.fromkeys(rebuild_reasons))
        _LAST_VARIANT_BUILD_INFO = info
        return output_path

    info = dict(_LAST_VARIANT_BUILD_INFO or {})
    info["rebuild_reasons"] = list(dict.fromkeys(rebuild_reasons))
    _LAST_VARIANT_BUILD_INFO = info
    return base_path


def build_youtube_short_variant(base_video_path: Path, output_video_path: Path) -> bool:
    """
    Build a YouTube-specific Shorts variant from a base export.
    The overlay masks the IG-centric intro and replaces it with clear context
    and stakes for cold Shorts viewers.
    """
    global _LAST_YOUTUBE_VARIANT_BUILD_INFO

    base_path = Path(base_video_path)
    output_path = Path(output_video_path)

    if not base_path.exists():
        print(f"[WARN] YouTube variant generation skipped: missing base video {base_path}")
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "missing_base",
            "output_path": str(output_path),
        }
        return False

    if not _safe_bool(getattr(config, "YOUTUBE_VARIANT_ENABLED", True), True):
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "variant_disabled",
            "output_path": str(output_path),
        }
        return False

    filter_expression, build_meta = _build_youtube_short_filter_expression(base_path)
    if not filter_expression:
        print("[WARN] YouTube variant generation skipped: hook text is empty.")
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "empty_hook_text",
            "output_path": str(output_path),
        }
        return False

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        print("[WARN] YouTube variant generation failed: ffmpeg is not available on PATH.")
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "missing_ffmpeg",
            "output_path": str(output_path),
        }
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(base_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        filter_expression,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except Exception as exc:
        print(f"[WARN] YouTube variant generation failed: {exc}")
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "ffmpeg_exec_error",
            "error": str(exc),
            "output_path": str(output_path),
        }
        return False

    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()
        if len(stderr_tail) > 500:
            stderr_tail = stderr_tail[-500:]
        print(
            f"[WARN] YouTube variant generation failed (ffmpeg exit {result.returncode}): {stderr_tail}"
        )
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception:
            pass
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "ffmpeg_failed",
            "output_path": str(output_path),
        }
        return False

    signature = _build_youtube_variant_signature(base_path)
    meta_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output_path),
        "base_video_path": str(base_path),
        "signature": signature.get("hash"),
        "signature_payload": signature.get("payload"),
        "build_meta": build_meta,
        "variant_type": "youtube_short",
    }
    try:
        _write_variant_meta(output_path, meta_payload)
    except Exception as exc:
        print(f"[WARN] Failed to write YouTube variant metadata for {output_path.name}: {exc}")

    _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
        "generated": True,
        "status": "generated",
        "output_path": str(output_path),
        "build_meta": build_meta,
    }
    return output_path.exists()


def ensure_youtube_short_variant(base_video_path: Path, output_video_path: Path) -> Path:
    """
    Ensure the YouTube Shorts variant exists and matches the current config.
    Returns the variant path on success, otherwise the base path.
    """
    global _LAST_YOUTUBE_VARIANT_BUILD_INFO

    base_path = Path(base_video_path)
    output_path = Path(output_video_path)

    if not base_path.exists():
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "missing_base",
            "output_path": str(output_path),
        }
        return base_path

    rebuild_reasons: list[str] = []
    signature = _build_youtube_variant_signature(base_path)

    if not output_path.exists():
        rebuild_reasons.append("variant_missing")
    else:
        meta = _read_variant_meta(output_path)
        if meta is None:
            rebuild_reasons.append("meta_missing")
        else:
            existing_sig = str(meta.get("signature") or "").strip()
            expected_sig = str(signature.get("hash") or "").strip()
            if not existing_sig or existing_sig != expected_sig:
                rebuild_reasons.append("signature_mismatch")
        try:
            if output_path.stat().st_mtime < base_path.stat().st_mtime:
                rebuild_reasons.append("base_newer")
        except Exception:
            rebuild_reasons.append("mtime_check_failed")

    if not rebuild_reasons:
        meta = _read_variant_meta(output_path) or {}
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = {
            "generated": False,
            "status": "up_to_date",
            "output_path": str(output_path),
            "build_meta": meta.get("build_meta"),
        }
        return output_path

    if build_youtube_short_variant(base_path, output_path):
        info = dict(_LAST_YOUTUBE_VARIANT_BUILD_INFO or {})
        info["rebuild_reasons"] = list(dict.fromkeys(rebuild_reasons))
        _LAST_YOUTUBE_VARIANT_BUILD_INFO = info
        return output_path

    info = dict(_LAST_YOUTUBE_VARIANT_BUILD_INFO or {})
    info["rebuild_reasons"] = list(dict.fromkeys(rebuild_reasons))
    _LAST_YOUTUBE_VARIANT_BUILD_INFO = info
    return base_path
