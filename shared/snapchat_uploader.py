#!/usr/bin/env python3
"""
Snapchat Public Profile uploader helpers.

This module handles:
- OAuth token bootstrap + refresh
- AES-256-CBC media encryption
- Multipart media upload (ADD/FINALIZE)
- Story + Spotlight post creation
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

SNAP_AUTH_BASE = "https://accounts.snapchat.com"
SNAP_AUTHORIZE_PATH = "/login/oauth2/authorize"
SNAP_TOKEN_PATH = "/login/oauth2/access_token"
MAX_UPLOAD_CHUNK_BYTES = 32 * 1024 * 1024


def _now_ts() -> int:
    return int(time.time())


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _truncate(value: str, max_length: int) -> str:
    text = str(value or "").strip()
    return text[:max_length] if len(text) > max_length else text


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_url(base: str, path_or_url: str) -> str:
    value = str(path_or_url or "").strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    base = str(base or "").rstrip("/")
    return f"{base}/{value.lstrip('/')}"


def _format_response_error(response: requests.Response) -> str:
    status = getattr(response, "status_code", "unknown")
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return f"{status}: {text[:500]}"
    header_parts = []
    grpc_message = str(response.headers.get("grpc-message") or "").strip()
    if grpc_message:
        header_parts.append(grpc_message)
    internal_code = str(response.headers.get("x-internal_error_code") or "").strip()
    if internal_code:
        header_parts.append(f"internal_code={internal_code}")
    request_id = str(response.headers.get("x-request_id") or "").strip()
    if request_id:
        header_parts.append(f"request_id={request_id}")
    if header_parts:
        return f"{status}: " + " | ".join(header_parts)
    return str(status)


def _deep_find_first(payload: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        for value in payload.values():
            found = _deep_find_first(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _deep_find_first(item, keys)
            if found not in (None, ""):
                return found
    return None


def build_authorize_url(
    client_id: str,
    redirect_uri: str,
    scope: str = "snapchat-profile-api",
    state: str = "",
    auth_base: str = SNAP_AUTH_BASE,
) -> str:
    client_id = str(client_id or "").strip()
    redirect_uri = str(redirect_uri or "").strip()
    if not client_id:
        raise ValueError("Missing Snapchat client_id.")
    if not redirect_uri:
        raise ValueError("Missing Snapchat redirect_uri.")
    from urllib.parse import urlencode

    query = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": str(scope or "snapchat-profile-api").strip() or "snapchat-profile-api",
    }
    if str(state or "").strip():
        query["state"] = str(state).strip()
    return f"{auth_base.rstrip('/')}{SNAP_AUTHORIZE_PATH}?{urlencode(query)}"


def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    auth_code: str,
    auth_base: str = SNAP_AUTH_BASE,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    client_id = str(client_id or "").strip()
    client_secret = str(client_secret or "").strip()
    redirect_uri = str(redirect_uri or "").strip()
    auth_code = str(auth_code or "").strip()
    if not client_id:
        raise ValueError("Missing Snapchat client_id.")
    if not client_secret:
        raise ValueError("Missing Snapchat client_secret.")
    if not redirect_uri:
        raise ValueError("Missing Snapchat redirect_uri.")
    if not auth_code:
        raise ValueError("Missing Snapchat authorization code.")

    url = f"{str(auth_base or SNAP_AUTH_BASE).rstrip('/')}{SNAP_TOKEN_PATH}"
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }
    # Snap docs use HTTP basic auth for client credentials.
    response = requests.post(
        url,
        data=data,
        auth=(client_id, client_secret),
        timeout=(20, max(20, _coerce_int(timeout_seconds, 120))),
    )
    if not response.ok:
        raise RuntimeError(f"Token exchange failed ({response.status_code}): {response.text[:400]}")
    payload = response.json() if response.content else {}
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected token exchange response format.")
    payload.setdefault("obtained_at", _now_ts())
    return payload


def write_token_payload(
    access_token_path: Path,
    refresh_token_path: Path,
    token_payload: dict[str, Any],
) -> None:
    payload = dict(token_payload or {})
    payload["obtained_at"] = _coerce_int(payload.get("obtained_at"), _now_ts())
    _atomic_write_json(access_token_path, payload)
    refresh_token = str(payload.get("refresh_token") or "").strip()
    if refresh_token:
        _atomic_write_json(
            refresh_token_path,
            {
                "refresh_token": refresh_token,
                "updated_at": _now_ts(),
            },
        )


class SnapchatTokenManager:
    def __init__(
        self,
        *,
        access_token_path: Path,
        refresh_token_path: Path,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        auth_base: str = SNAP_AUTH_BASE,
        timeout_seconds: int = 120,
        logger=print,
    ) -> None:
        self.access_token_path = Path(access_token_path)
        self.refresh_token_path = Path(refresh_token_path)
        self.client_id = str(client_id or "").strip()
        self.client_secret = str(client_secret or "").strip()
        self.redirect_uri = str(redirect_uri or "").strip()
        self.auth_base = str(auth_base or SNAP_AUTH_BASE).strip() or SNAP_AUTH_BASE
        self.timeout_seconds = max(20, _coerce_int(timeout_seconds, 120))
        self.logger = logger or (lambda *_args, **_kwargs: None)
        self._payload: dict[str, Any] | None = None

    def _load_payload(self) -> dict[str, Any]:
        if self._payload is not None:
            return self._payload
        payload = _read_json_file(self.access_token_path)
        if not payload:
            payload = {}
        refresh_fallback = _read_json_file(self.refresh_token_path)
        if not payload.get("refresh_token") and refresh_fallback.get("refresh_token"):
            payload["refresh_token"] = refresh_fallback.get("refresh_token")
        self._payload = payload
        return self._payload

    def _save_payload(self, payload: dict[str, Any]) -> None:
        write_token_payload(self.access_token_path, self.refresh_token_path, payload)
        self._payload = dict(payload)

    def _is_expiring_soon(self, payload: dict[str, Any], window_seconds: int = 120) -> bool:
        expires_in = _coerce_int(payload.get("expires_in"), 0)
        obtained_at = _coerce_int(payload.get("obtained_at"), 0)
        if expires_in <= 0 or obtained_at <= 0:
            return False
        return (_now_ts() + max(30, window_seconds)) >= (obtained_at + expires_in)

    def _refresh(self, payload: dict[str, Any]) -> dict[str, Any]:
        refresh_token = str(payload.get("refresh_token") or "").strip()
        if not refresh_token:
            raise RuntimeError("No Snapchat refresh token available.")
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Cannot refresh Snapchat token: missing client credentials.")

        url = f"{self.auth_base.rstrip('/')}{SNAP_TOKEN_PATH}"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(
            url,
            data=data,
            auth=(self.client_id, self.client_secret),
            timeout=(20, self.timeout_seconds),
        )
        if not response.ok:
            raise RuntimeError(f"Snapchat token refresh failed ({response.status_code}): {response.text[:400]}")
        refreshed = response.json() if response.content else {}
        if not isinstance(refreshed, dict):
            raise RuntimeError("Unexpected Snapchat refresh response format.")
        refreshed.setdefault("refresh_token", refresh_token)
        refreshed["obtained_at"] = _now_ts()
        self._save_payload(refreshed)
        self.logger(f"[OK] Snapchat token refreshed: {self.access_token_path}")
        return refreshed

    def get_access_token(self, force_refresh: bool = False) -> str:
        payload = self._load_payload()
        if not payload:
            raise RuntimeError(
                f"Missing Snapchat token payload at {self.access_token_path}. "
                "Run OAuth bootstrap first."
            )
        if force_refresh or self._is_expiring_soon(payload):
            payload = self._refresh(payload)
        access_token = str(payload.get("access_token") or "").strip()
        if not access_token:
            raise RuntimeError("Snapchat access token missing from token payload.")
        return access_token


def _request_with_retries(
    *,
    method: str,
    url: str,
    token_manager: SnapchatTokenManager,
    timeout_seconds: int,
    retry_count: int = 3,
    json_payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    logger=print,
) -> requests.Response:
    retries = max(1, _coerce_int(retry_count, 3))
    refreshed_after_401 = False
    token = token_manager.get_access_token(force_refresh=False)
    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(1, retries + 1):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_payload,
                params=params,
                data=data,
                files=files,
                timeout=(20, max(20, _coerce_int(timeout_seconds, 120))),
            )
        except Exception as exc:
            if attempt >= retries:
                raise RuntimeError(f"Snapchat request failed after {attempt} attempts: {exc}") from exc
            backoff = min(30.0, (2 ** (attempt - 1)) + random_jitter())
            logger(f"[WARN] Snapchat request error (attempt {attempt}/{retries}): {exc}. Retrying in {backoff:.1f}s...")
            time.sleep(backoff)
            continue

        if response.status_code == 401 and not refreshed_after_401:
            refreshed_after_401 = True
            token = token_manager.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            continue

        if response.status_code in {429, 500, 502, 503, 504} and attempt < retries:
            backoff = min(60.0, (2 ** attempt) + random_jitter())
            logger(
                f"[WARN] Snapchat request status {response.status_code} "
                f"(attempt {attempt}/{retries}). Retrying in {backoff:.1f}s..."
            )
            time.sleep(backoff)
            continue

        return response

    raise RuntimeError("Snapchat request retry loop exhausted unexpectedly.")


def random_jitter() -> float:
    return float((time.time() * 1000) % 1000) / 1000.0


def encrypt_video_aes_cbc(video_path: Path) -> tuple[Path, str, str]:
    try:
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'cryptography' for Snapchat AES encryption. "
            "Install with: pip install cryptography"
        ) from exc

    key = os.urandom(32)  # AES-256
    iv = os.urandom(16)   # CBC IV

    fd, temp_path = tempfile.mkstemp(prefix="snap_enc_", suffix=".bin")
    os.close(fd)
    encrypted_path = Path(temp_path)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()

    with video_path.open("rb") as src, encrypted_path.open("wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            padded = padder.update(chunk)
            if padded:
                dst.write(encryptor.update(padded))
        padded_tail = padder.finalize()
        dst.write(encryptor.update(padded_tail))
        dst.write(encryptor.finalize())

    key_b64 = base64.b64encode(key).decode("ascii")
    iv_b64 = base64.b64encode(iv).decode("ascii")
    return encrypted_path, key_b64, iv_b64


def create_media(
    *,
    api_base: str,
    profile_id: str,
    video_name: str,
    key_b64: str,
    iv_b64: str,
    token_manager: SnapchatTokenManager,
    retry_count: int,
    timeout_seconds: int,
    logger=print,
) -> dict[str, str]:
    endpoint = _build_url(
        api_base,
        f"/v1/public_profiles/{profile_id}/media",
    )
    payload = {
        "type": "VIDEO",
        "name": _truncate(video_name, 100),
        "key": str(key_b64).strip(),
        "iv": str(iv_b64).strip(),
    }
    response = _request_with_retries(
        method="POST",
        url=endpoint,
        token_manager=token_manager,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        json_payload=payload,
        logger=logger,
    )
    if not response.ok:
        raise RuntimeError(f"Create media failed ({_format_response_error(response)})")
    body = response.json() if response.content else {}
    media_id = str(_deep_find_first(body, ("media_id", "id")) or "").strip()
    add_path = str(_deep_find_first(body, ("add_path", "add_url")) or "").strip()
    finalize_path = str(_deep_find_first(body, ("finalize_path", "finalize_url")) or "").strip()
    if not media_id or not add_path or not finalize_path:
        raise RuntimeError(f"Create media missing fields in response: {body}")
    return {
        "media_id": media_id,
        "add_path": add_path,
        "finalize_path": finalize_path,
    }


def upload_media_parts(
    *,
    api_base: str,
    add_path: str,
    finalize_path: str,
    encrypted_path: Path,
    token_manager: SnapchatTokenManager,
    retry_count: int,
    timeout_seconds: int,
    logger=print,
) -> int:
    add_url = _build_url(api_base, add_path)
    finalize_url = _build_url(api_base, finalize_path)
    part_count = 0
    with encrypted_path.open("rb") as handle:
        while True:
            chunk = handle.read(MAX_UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            part_count += 1
            response = _request_with_retries(
                method="POST",
                url=add_url,
                token_manager=token_manager,
                retry_count=retry_count,
                timeout_seconds=timeout_seconds,
                data={"action": "ADD", "part_number": part_count},
                files={"file": (f"part_{part_count}.bin", chunk, "application/octet-stream")},
                logger=logger,
            )
            if not response.ok:
                raise RuntimeError(
                    f"Media ADD failed for part {part_count} "
                    f"({_format_response_error(response)})"
                )

    if part_count <= 0:
        raise RuntimeError("Encrypted media produced zero upload parts.")

    response = _request_with_retries(
        method="POST",
        url=finalize_url,
        token_manager=token_manager,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        data={"action": "FINALIZE"},
        logger=logger,
    )
    if not response.ok:
        raise RuntimeError(f"Media FINALIZE failed ({_format_response_error(response)})")
    return part_count


def post_story(
    *,
    api_base: str,
    profile_id: str,
    media_id: str,
    token_manager: SnapchatTokenManager,
    retry_count: int,
    timeout_seconds: int,
    logger=print,
) -> dict[str, Any]:
    endpoint = _build_url(api_base, f"/v1/public_profiles/{profile_id}/stories")
    payload = {"media_id": str(media_id).strip()}
    response = _request_with_retries(
        method="POST",
        url=endpoint,
        token_manager=token_manager,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        json_payload=payload,
        logger=logger,
    )
    if not response.ok:
        return {
            "ok": False,
            "error": f"Story post failed ({_format_response_error(response)})",
        }
    body = response.json() if response.content else {}
    story_post_id = str(_deep_find_first(body, ("story_post_id", "id")) or "").strip()
    return {"ok": True, "id": story_post_id, "raw": body}


def post_spotlight(
    *,
    api_base: str,
    profile_id: str,
    media_id: str,
    description: str,
    locale: str,
    skip_save_to_profile: bool,
    token_manager: SnapchatTokenManager,
    retry_count: int,
    timeout_seconds: int,
    logger=print,
) -> dict[str, Any]:
    endpoint = _build_url(api_base, f"/v1/public_profiles/{profile_id}/spotlights")
    payload = {
        "media_id": str(media_id).strip(),
        "description": _truncate(description, 160),
        "locale": str(locale or "en_US").strip() or "en_US",
        "skip_save_to_profile": bool(skip_save_to_profile),
    }
    response = _request_with_retries(
        method="POST",
        url=endpoint,
        token_manager=token_manager,
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
        json_payload=payload,
        logger=logger,
    )
    if not response.ok:
        return {
            "ok": False,
            "error": f"Spotlight post failed ({_format_response_error(response)})",
        }
    body = response.json() if response.content else {}
    spotlight_id = str(_deep_find_first(body, ("spotlight_id", "id")) or "").strip()
    return {"ok": True, "id": spotlight_id, "raw": body}


def _build_spotlight_description(caption: str, game_mode: str, day_number: int) -> str:
    first_line = ""
    for line in str(caption or "").splitlines():
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break
    if not first_line:
        mode = str(game_mode or "").replace("_", " ").strip().title() or "Follower Battlegrounds"
        first_line = f"{mode} - Day {day_number}"
    return _truncate(first_line, 160)


def upload_snapchat(
    *,
    video_path: Path,
    game_mode: str,
    day_number: int,
    caption: str,
    profile_id: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    access_token_path: Path,
    refresh_token_path: Path,
    scope: str = "snapchat-profile-api",
    api_base: str = "https://businessapi.snapchat.com",
    enable_story_post: bool = True,
    enable_spotlight_post: bool = True,
    spotlight_locale: str = "en_US",
    spotlight_skip_save_to_profile: bool = False,
    retry_count: int = 3,
    timeout_seconds: int = 120,
    logger=print,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "media_id": "",
        "parts_uploaded": 0,
        "story": {"ok": False},
        "spotlight": {"ok": False},
        "errors": [],
        "scope": str(scope or "").strip(),
    }
    if not video_path.exists():
        result["errors"].append(f"Missing Snapchat video file: {video_path}")
        return result
    if not str(profile_id or "").strip():
        result["errors"].append("Missing Snapchat profile id.")
        return result
    if not enable_story_post and not enable_spotlight_post:
        result["errors"].append("Both Snapchat story and spotlight posting are disabled.")
        return result

    token_manager = SnapchatTokenManager(
        access_token_path=Path(access_token_path),
        refresh_token_path=Path(refresh_token_path),
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        auth_base=SNAP_AUTH_BASE,
        timeout_seconds=timeout_seconds,
        logger=logger,
    )

    encrypted_path: Path | None = None
    try:
        encrypted_path, key_b64, iv_b64 = encrypt_video_aes_cbc(Path(video_path))
        logger(f"[INFO] Snapchat: encrypted media ready ({encrypted_path.name})")

        media = create_media(
            api_base=api_base,
            profile_id=str(profile_id).strip(),
            video_name=Path(video_path).stem,
            key_b64=key_b64,
            iv_b64=iv_b64,
            token_manager=token_manager,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            logger=logger,
        )
        media_id = str(media.get("media_id") or "").strip()
        result["media_id"] = media_id

        parts_uploaded = upload_media_parts(
            api_base=api_base,
            add_path=str(media.get("add_path") or ""),
            finalize_path=str(media.get("finalize_path") or ""),
            encrypted_path=encrypted_path,
            token_manager=token_manager,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            logger=logger,
        )
        result["parts_uploaded"] = parts_uploaded
        logger(f"[OK] Snapchat media uploaded: media_id={media_id}, parts={parts_uploaded}")

        if enable_story_post:
            story_result = post_story(
                api_base=api_base,
                profile_id=str(profile_id).strip(),
                media_id=media_id,
                token_manager=token_manager,
                retry_count=retry_count,
                timeout_seconds=timeout_seconds,
                logger=logger,
            )
            result["story"] = story_result
            if not story_result.get("ok"):
                result["errors"].append(str(story_result.get("error") or "Story post failed"))

        if enable_spotlight_post:
            spotlight_result = post_spotlight(
                api_base=api_base,
                profile_id=str(profile_id).strip(),
                media_id=media_id,
                description=_build_spotlight_description(caption, game_mode, int(day_number)),
                locale=str(spotlight_locale or "en_US"),
                skip_save_to_profile=bool(spotlight_skip_save_to_profile),
                token_manager=token_manager,
                retry_count=retry_count,
                timeout_seconds=timeout_seconds,
                logger=logger,
            )
            result["spotlight"] = spotlight_result
            if not spotlight_result.get("ok"):
                result["errors"].append(str(spotlight_result.get("error") or "Spotlight post failed"))

        result["ok"] = bool(result["story"].get("ok") or result["spotlight"].get("ok"))
        return result
    except Exception as exc:
        result["errors"].append(str(exc))
        return result
    finally:
        if encrypted_path is not None:
            try:
                encrypted_path.unlink(missing_ok=True)
            except Exception:
                pass
