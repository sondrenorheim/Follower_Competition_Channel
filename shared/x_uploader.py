#!/usr/bin/env python3
"""
X (Twitter) upload helpers.

This module handles:
- OAuth1-authenticated chunked video upload (INIT/APPEND/FINALIZE/STATUS)
- Tweet creation with uploaded media
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

X_UPLOAD_API = "https://upload.twitter.com/1.1/media/upload.json"
X_V2_API_BASE = "https://api.x.com"
MAX_MEDIA_CHUNK_BYTES = 4 * 1024 * 1024


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _truncate(value: str, max_length: int) -> str:
    text = str(value or "").strip()
    return text[:max_length] if len(text) > max_length else text


def _format_response_error(response: requests.Response) -> str:
    status = getattr(response, "status_code", "unknown")
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return f"{status}: {text[:600]}"
    return str(status)


def _compute_retry_sleep_seconds(response: requests.Response | None, attempt: int) -> float:
    if response is not None and response.status_code == 429:
        reset_raw = (response.headers or {}).get("x-rate-limit-reset")
        try:
            reset_ts = int(str(reset_raw or "0").strip())
        except Exception:
            reset_ts = 0
        if reset_ts > 0:
            wait_seconds = max(1, reset_ts - int(time.time()) + 1)
            return float(min(180, wait_seconds))
    return float(min(60, (2 ** max(1, attempt)) + ((time.time() * 1000) % 1000) / 1000.0))


def _request_with_retries(
    *,
    method: str,
    url: str,
    auth,
    retry_count: int,
    timeout_seconds: int,
    logger=print,
    **kwargs,
) -> requests.Response:
    retries = max(1, _coerce_int(retry_count, 3))
    timeout_value = (20, max(20, _coerce_int(timeout_seconds, 120)))

    for attempt in range(1, retries + 1):
        response = None
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=auth,
                timeout=timeout_value,
                **kwargs,
            )
        except Exception as exc:
            if attempt >= retries:
                raise RuntimeError(f"X request failed after {attempt} attempts: {exc}") from exc
            sleep_seconds = _compute_retry_sleep_seconds(None, attempt)
            logger(
                f"[WARN] X request error (attempt {attempt}/{retries}): {exc}. "
                f"Retrying in {sleep_seconds:.1f}s..."
            )
            time.sleep(sleep_seconds)
            continue

        if response.status_code in {429, 500, 502, 503, 504} and attempt < retries:
            sleep_seconds = _compute_retry_sleep_seconds(response, attempt)
            logger(
                f"[WARN] X request status {response.status_code} (attempt {attempt}/{retries}). "
                f"Retrying in {sleep_seconds:.1f}s..."
            )
            time.sleep(sleep_seconds)
            continue

        return response

    raise RuntimeError("X request retry loop exhausted unexpectedly.")


def _build_oauth1_auth(
    *,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
):
    try:
        from requests_oauthlib import OAuth1
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'requests-oauthlib' for X uploads. "
            "Install with: pip install requests-oauthlib"
        ) from exc

    return OAuth1(
        str(consumer_key or "").strip(),
        str(consumer_secret or "").strip(),
        str(access_token or "").strip(),
        str(access_token_secret or "").strip(),
    )


def _extract_x_error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                message = str(first.get("message") or first.get("detail") or "").strip()
                if message:
                    return message
                code = first.get("code")
                if code is not None:
                    return f"code={code}"
        for key in ("title", "detail", "error", "message"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
    return ""


def _poll_media_status(
    *,
    media_id: str,
    auth,
    upload_api: str,
    retry_count: int,
    timeout_seconds: int,
    logger=print,
    initial_processing_info: dict[str, Any] | None = None,
) -> None:
    processing_info = initial_processing_info or {}
    deadline = time.time() + max(60, timeout_seconds)

    while True:
        state = str(processing_info.get("state") or "").strip().lower()
        if state == "succeeded":
            return
        if state == "failed":
            error_info = processing_info.get("error") if isinstance(processing_info, dict) else None
            if isinstance(error_info, dict):
                message = str(error_info.get("message") or error_info.get("name") or "").strip()
                if message:
                    raise RuntimeError(f"X media processing failed: {message}")
            raise RuntimeError(f"X media processing failed: {processing_info}")

        check_after_secs = _coerce_int(processing_info.get("check_after_secs"), 5)
        time.sleep(max(1, min(30, check_after_secs)))

        if time.time() > deadline:
            raise RuntimeError("X media processing timed out.")

        response = _request_with_retries(
            method="GET",
            url=upload_api,
            auth=auth,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            params={
                "command": "STATUS",
                "media_id": media_id,
            },
            logger=logger,
        )
        if not response.ok:
            raise RuntimeError(f"X media STATUS failed ({_format_response_error(response)})")
        body = response.json() if response.content else {}
        if not isinstance(body, dict):
            raise RuntimeError("X media STATUS response was not a JSON object.")
        processing_info = body.get("processing_info") if isinstance(body.get("processing_info"), dict) else {"state": "succeeded"}


def upload_video_media(
    *,
    video_path: Path,
    auth,
    upload_api: str = X_UPLOAD_API,
    retry_count: int = 3,
    timeout_seconds: int = 120,
    logger=print,
) -> str:
    if not Path(video_path).exists():
        raise RuntimeError(f"Missing X upload video file: {video_path}")
    total_bytes = Path(video_path).stat().st_size
    if total_bytes <= 0:
        raise RuntimeError(f"Invalid X upload video size: {video_path}")

    init_resp = _request_with_retries(
        method="POST",
        url=upload_api,
        auth=auth,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        data={
            "command": "INIT",
            "total_bytes": str(total_bytes),
            "media_type": "video/mp4",
            "media_category": "tweet_video",
        },
        logger=logger,
    )
    if not init_resp.ok:
        raise RuntimeError(f"X media INIT failed ({_format_response_error(init_resp)})")
    init_body = init_resp.json() if init_resp.content else {}
    media_id = str((init_body or {}).get("media_id_string") or (init_body or {}).get("media_id") or "").strip()
    if not media_id:
        raise RuntimeError(f"X media INIT missing media_id: {init_body}")

    segment_index = 0
    with Path(video_path).open("rb") as handle:
        while True:
            chunk = handle.read(MAX_MEDIA_CHUNK_BYTES)
            if not chunk:
                break
            append_resp = _request_with_retries(
                method="POST",
                url=upload_api,
                auth=auth,
                retry_count=retry_count,
                timeout_seconds=timeout_seconds,
                data={
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": str(segment_index),
                },
                files={"media": (f"chunk_{segment_index}.bin", chunk, "application/octet-stream")},
                logger=logger,
            )
            if not append_resp.ok:
                raise RuntimeError(
                    f"X media APPEND failed for segment {segment_index} "
                    f"({_format_response_error(append_resp)})"
                )
            segment_index += 1

    finalize_resp = _request_with_retries(
        method="POST",
        url=upload_api,
        auth=auth,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        data={
            "command": "FINALIZE",
            "media_id": media_id,
        },
        logger=logger,
    )
    if not finalize_resp.ok:
        raise RuntimeError(f"X media FINALIZE failed ({_format_response_error(finalize_resp)})")

    finalize_body = finalize_resp.json() if finalize_resp.content else {}
    if isinstance(finalize_body, dict) and isinstance(finalize_body.get("processing_info"), dict):
        _poll_media_status(
            media_id=media_id,
            auth=auth,
            upload_api=upload_api,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            logger=logger,
            initial_processing_info=finalize_body.get("processing_info"),
        )

    return media_id


def _build_tweet_text(caption: str, game_mode: str, day_number: int, max_length: int = 280) -> str:
    lines = [line.strip() for line in str(caption or "").splitlines() if line.strip()]
    primary = lines[0] if lines else f"Day {day_number} of making my followers battle every day."
    mode_label = str(game_mode or "").replace("_", " ").strip().title() or "Follower Battlegrounds"
    game_line = f"Game: {mode_label} | Day {day_number}"
    hashtags = "#followerbattlegrounds"
    combined = f"{primary}\n{game_line}\n{hashtags}".strip()
    return _truncate(combined, max_length)


def post_tweet(
    *,
    media_id: str,
    text: str,
    auth,
    api_base: str = X_V2_API_BASE,
    retry_count: int = 3,
    timeout_seconds: int = 120,
    logger=print,
) -> dict[str, Any]:
    endpoint = f"{str(api_base or X_V2_API_BASE).rstrip('/')}/2/tweets"
    payload = {
        "text": _truncate(str(text or "").strip(), 280),
        "media": {"media_ids": [str(media_id).strip()]},
    }
    response = _request_with_retries(
        method="POST",
        url=endpoint,
        auth=auth,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        json=payload,
        logger=logger,
    )
    if not response.ok:
        details = ""
        try:
            details = _extract_x_error_message(response.json())
        except Exception:
            details = ""
        suffix = f": {details}" if details else ""
        raise RuntimeError(f"X tweet create failed ({_format_response_error(response)}){suffix}")

    body = response.json() if response.content else {}
    tweet_id = ""
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, dict):
            tweet_id = str(data.get("id") or "").strip()
    if not tweet_id:
        raise RuntimeError(f"X tweet response missing id: {body}")
    return {"tweet_id": tweet_id, "raw": body}


def upload_x(
    *,
    video_path: Path,
    caption: str,
    game_mode: str,
    day_number: int,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
    upload_api: str = X_UPLOAD_API,
    api_base: str = X_V2_API_BASE,
    retry_count: int = 3,
    timeout_seconds: int = 120,
    logger=print,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "media_id": "",
        "tweet_id": "",
        "tweet_text": "",
        "errors": [],
    }
    if not Path(video_path).exists():
        result["errors"].append(f"Missing X video file: {video_path}")
        return result

    required_values = {
        "X_CONSUMER_KEY": str(consumer_key or "").strip(),
        "X_CONSUMER_SECRET": str(consumer_secret or "").strip(),
        "X_ACCESS_TOKEN": str(access_token or "").strip(),
        "X_ACCESS_TOKEN_SECRET": str(access_token_secret or "").strip(),
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        result["errors"].append("Missing X credentials: " + ", ".join(missing))
        return result

    try:
        auth = _build_oauth1_auth(
            consumer_key=required_values["X_CONSUMER_KEY"],
            consumer_secret=required_values["X_CONSUMER_SECRET"],
            access_token=required_values["X_ACCESS_TOKEN"],
            access_token_secret=required_values["X_ACCESS_TOKEN_SECRET"],
        )
        media_id = upload_video_media(
            video_path=Path(video_path),
            auth=auth,
            upload_api=str(upload_api or X_UPLOAD_API).strip() or X_UPLOAD_API,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            logger=logger,
        )
        result["media_id"] = media_id
        tweet_text = _build_tweet_text(caption=caption, game_mode=game_mode, day_number=_coerce_int(day_number, 0))
        result["tweet_text"] = tweet_text
        tweet_result = post_tweet(
            media_id=media_id,
            text=tweet_text,
            auth=auth,
            api_base=str(api_base or X_V2_API_BASE).strip() or X_V2_API_BASE,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            logger=logger,
        )
        result["tweet_id"] = str(tweet_result.get("tweet_id") or "").strip()
        result["ok"] = True
        return result
    except Exception as exc:
        result["errors"].append(str(exc))
        return result
