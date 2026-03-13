from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path


_SMB1_ROOT = Path("_external") / "Super-Mario-Bros.-Remastered-Public" / "Scenes" / "Levels" / "SMB1"


# Canonical SMB1 campaign route (1-1 .. 8-4).
SMB1_MAIN_LEVELS = OrderedDict(
    [
        ("super_follower_bros_1_1", _SMB1_ROOT / "World1" / "1-1.tscn"),
        ("super_follower_bros_1_2", _SMB1_ROOT / "World1" / "1-2.tscn"),
        ("super_follower_bros_1_3", _SMB1_ROOT / "World1" / "1-3.tscn"),
        ("super_follower_bros_1_4", _SMB1_ROOT / "World1" / "1-4.tscn"),
        ("super_follower_bros_2_1", _SMB1_ROOT / "World2" / "2-1.tscn"),
        ("super_follower_bros_2_2", _SMB1_ROOT / "World2" / "2-2.tscn"),
        ("super_follower_bros_2_3", _SMB1_ROOT / "World2" / "2-3.tscn"),
        ("super_follower_bros_2_4", _SMB1_ROOT / "World2" / "2-4.tscn"),
        ("super_follower_bros_3_1", _SMB1_ROOT / "World3" / "3-1.tscn"),
        ("super_follower_bros_3_2", _SMB1_ROOT / "World3" / "3-2.tscn"),
        ("super_follower_bros_3_3", _SMB1_ROOT / "World3" / "3-3.tscn"),
        ("super_follower_bros_3_4", _SMB1_ROOT / "World3" / "3-4.tscn"),
        ("super_follower_bros_4_1", _SMB1_ROOT / "World4" / "4-1.tscn"),
        ("super_follower_bros_4_2", _SMB1_ROOT / "World4" / "4-2.tscn"),
        ("super_follower_bros_4_3", _SMB1_ROOT / "World4" / "4-3.tscn"),
        ("super_follower_bros_4_4", _SMB1_ROOT / "World4" / "4-4.tscn"),
        ("super_follower_bros_5_1", _SMB1_ROOT / "World5" / "5-1.tscn"),
        ("super_follower_bros_5_2", _SMB1_ROOT / "World5" / "5-2.tscn"),
        ("super_follower_bros_5_3", _SMB1_ROOT / "World5" / "5-3.tscn"),
        ("super_follower_bros_5_4", _SMB1_ROOT / "World5" / "5-4.tscn"),
        ("super_follower_bros_6_1", _SMB1_ROOT / "World6" / "6-1.tscn"),
        ("super_follower_bros_6_2", _SMB1_ROOT / "World6" / "6-2.tscn"),
        ("super_follower_bros_6_3", _SMB1_ROOT / "World6" / "6-3.tscn"),
        ("super_follower_bros_6_4", _SMB1_ROOT / "World6" / "6-4.tscn"),
        ("super_follower_bros_7_1", _SMB1_ROOT / "World7" / "7-1.tscn"),
        ("super_follower_bros_7_2", _SMB1_ROOT / "World7" / "7-2.tscn"),
        ("super_follower_bros_7_3", _SMB1_ROOT / "World7" / "7-3.tscn"),
        ("super_follower_bros_7_4", _SMB1_ROOT / "World7" / "7-4.tscn"),
        ("super_follower_bros_8_1", _SMB1_ROOT / "World8" / "8-1.tscn"),
        ("super_follower_bros_8_2", _SMB1_ROOT / "World8" / "8-2.tscn"),
        ("super_follower_bros_8_3", _SMB1_ROOT / "World8" / "8-3.tscn"),
        ("super_follower_bros_8_4", _SMB1_ROOT / "World8" / "8-4.tscn"),
    ]
)


SMB_MODE_ALIASES = {
    "super_follower_bros": "super_follower_bros_1_1",
}


_WORLD_LEVEL_RE = re.compile(r"^super_follower_bros_(\d)_(\d)$")


def normalize_smb_mode(mode: str | None) -> str | None:
    if not mode:
        return None
    raw = str(mode).strip().lower()
    aliased = SMB_MODE_ALIASES.get(raw, raw)
    if aliased in SMB1_MAIN_LEVELS:
        return aliased
    match = _WORLD_LEVEL_RE.match(aliased)
    if not match:
        return None
    if aliased in SMB1_MAIN_LEVELS:
        return aliased
    return None


def is_smb_mode(mode: str | None) -> bool:
    return normalize_smb_mode(mode) is not None


def scene_path_for_mode(mode: str) -> Path:
    canonical = normalize_smb_mode(mode)
    if canonical is None:
        raise ValueError(f"Unsupported SMB mode: {mode}")
    return SMB1_MAIN_LEVELS[canonical]


def world_label_for_mode(mode: str) -> str:
    canonical = normalize_smb_mode(mode)
    if canonical is None:
        return "1-1"
    match = _WORLD_LEVEL_RE.match(canonical)
    if not match:
        return "1-1"
    return f"{match.group(1)}-{match.group(2)}"


def display_name_for_mode(mode: str) -> str:
    return f"Super Follower Bros. {world_label_for_mode(mode)}"

