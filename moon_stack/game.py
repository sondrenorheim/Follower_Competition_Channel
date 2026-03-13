from __future__ import annotations

import bisect
import hashlib
import io
import json
import math
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import config

try:
    from PIL import Image
except Exception:
    Image = None

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight,
    ClockObject,
    DirectionalLight,
    TextNode,
    Texture,
    WindowProperties,
    loadPrcFileData,
)

from shared.club_members import normalize_username
from subway_followers_3d.recorder import PandaVideoRecorder


class MoonStackGame(ShowBase):
    GAME_TITLE = "EARTH TO MOON STACK"

    def __init__(self):
        loadPrcFileData("", f"win-size {config.SCREEN_WIDTH} {config.SCREEN_HEIGHT}")
        loadPrcFileData("", "sync-video #f")
        loadPrcFileData("", "show-frame-rate-meter #f")

        super().__init__()
        self.disableMouse()

        props = WindowProperties()
        props.setTitle(self.GAME_TITLE)
        if self.win:
            self.win.requestProperties(props)

        self.base_dir = Path(__file__).resolve().parents[1]
        self.clock = ClockObject.getGlobalClock()

        self.target_km = int(getattr(config, "MOON_STACK_TARGET_KM", 383400))
        self.duration_seconds = float(getattr(config, "MOON_STACK_VIDEO_DURATION_SECONDS", 45.0))
        self.km_to_units = float(getattr(config, "MOON_STACK_KM_TO_WORLD_UNITS", 0.03))
        self.max_visible_balls = int(getattr(config, "MOON_STACK_MAX_VISIBLE_BALLS", 420))
        self.allow_network_avatars = bool(getattr(config, "MOON_STACK_ALLOW_NETWORK_AVATAR_DOWNLOAD", False))
        self.test_empty_mode = bool(getattr(config, "MOON_STACK_TEST_EMPTY", False))
        self.test_minimal_mode = bool(getattr(config, "TEST_MINIMAL_PLAYERS", False)) and not self.test_empty_mode
        self.test_minimal_count = max(0, int(getattr(config, "TEST_MINIMAL_PLAYER_COUNT", 0) or 0))

        self.follower_weight = int(getattr(config, "MOON_STACK_FOLLOWER_WEIGHT", 1))
        self.discord_weight = int(getattr(config, "MOON_STACK_DISCORD_WEIGHT", 10))
        self.club_weight = int(getattr(config, "MOON_STACK_CLUB_WEIGHT", 100))

        self.follower_diameter = float(getattr(config, "MOON_STACK_FOLLOWER_DIAMETER_MULT", 1.0))
        self.discord_diameter = float(getattr(config, "MOON_STACK_DISCORD_DIAMETER_MULT", 10.0))
        self.club_diameter = float(getattr(config, "MOON_STACK_CLUB_DIAMETER_MULT", 100.0))

        self.camera_base_distance = float(getattr(config, "MOON_STACK_CAMERA_BASE_DISTANCE", 3.0))
        self.camera_zoom_amplitude = float(getattr(config, "MOON_STACK_CAMERA_ZOOM_AMPLITUDE", 0.9))
        self.camera_side_sway = float(getattr(config, "MOON_STACK_CAMERA_SIDE_SWAY", 0.5))
        self.camera_height_offset = float(getattr(config, "MOON_STACK_CAMERA_HEIGHT_OFFSET", 0.8))
        self.camera_look_offset = float(getattr(config, "MOON_STACK_CAMERA_LOOK_OFFSET", 0.4))

        self.state_path = self._resolve_path(getattr(config, "MOON_STACK_STATE_FILE", "Followers/moon_stack_state.json"))
        self.instagram_path = self._resolve_path(
            getattr(config, "MOON_STACK_INSTAGRAM_FILE", "Followers/new_followers_fresh.json")
        )
        self.discord_path = self._resolve_path(
            getattr(config, "MOON_STACK_DISCORD_FILE", "Followers/discord_followers.json")
        )
        self.club_path = self._resolve_path(
            getattr(config, "MOON_STACK_CLUB_FILE", "Followers/club_members_followers.json")
        )

        self.avatar_cache_dir = self._resolve_path(getattr(config, "MOON_STACK_AVATAR_CACHE_DIR", "avatar_cache"))
        self.avatar_texture_size = int(getattr(config, "MOON_STACK_AVATAR_TEXTURE_SIZE", 128))

        self.setBackgroundColor(*getattr(config, "MOON_STACK_BACKGROUND_COLOR", (0.02, 0.02, 0.05)))
        if hasattr(self, "camLens") and self.camLens:
            self.camLens.setNearFar(0.01, 50000.0)
            self.camLens.setFov(float(getattr(config, "MOON_STACK_CAMERA_FOV", 42.0)))

        self._setup_lighting()

        self.stack_root = self.render.attachNewNode("moon_stack_root")

        self.sphere_template = self.loader.loadModel("models/misc/sphere")
        self.sphere_template.setTwoSided(True)

        self._setup_planets()
        self._setup_overlay()

        self.state = self._load_state()
        ordered_sources, source_map = self._build_current_sources()
        self.summary = self._reconcile_state(ordered_sources, source_map)
        self.active_entries = [entry for entry in self.state["history"] if entry.get("active")]
        self._build_stack_index()

        self.tier_counts = {"follower": 0, "discord": 0, "club": 0}
        self.tier_km = {"follower": 0, "discord": 0, "club": 0}
        for entry in self.active_entries:
            tier = str(entry.get("tier", "follower"))
            if tier not in self.tier_counts:
                tier = "follower"
            self.tier_counts[tier] += 1
            self.tier_km[tier] += int(entry.get("km_value", 1) or 1)

        self.visible_nodes: dict[int, Any] = {}
        self.avatar_texture_cache: dict[str, Texture | None] = {}
        self.fallback_texture_cache: dict[str, Texture | None] = {}

        self.current_time = 0.0
        self.shutdown_started = False

        self.video_recorder = PandaVideoRecorder(
            base=self,
            output_path=config.get_output_video_path(game_mode="moon_stack"),
            fps=getattr(config, "VIDEO_FPS", 30),
            record=getattr(config, "EXPORT_VIDEO", True),
        )

        self.accept("escape", self._shutdown)
        self.taskMgr.add(self._update_task, "moon_stack_update")

        print("=" * 60)
        print("  EARTH TO MOON STACK")
        print("=" * 60)
        print(f"Target distance: {self.target_km:,} km")
        print(f"Current stack: {self.total_km:,} km ({self.progress_pct:.2f}%)")
        print(f"Remaining: {max(0, self.target_km - self.total_km):,} km")
        print(f"Active players: {len(self.active_entries):,}")
        print(f"  Followers: {self.tier_counts['follower']:,}")
        print(f"  Discord: {self.tier_counts['discord']:,}")
        print(f"  Club: {self.tier_counts['club']:,}")
        print(f"Added this run: {self.summary['added']:,}")
        print(f"Removed this run: {self.summary['removed']:,}")
        if self.test_empty_mode:
            print("TEST MODE: Moon stack running with zero users.")
        elif self.test_minimal_mode:
            print(f"TEST MODE: Moon stack using {self.test_minimal_count:,} synthetic users.")
        print("=" * 60)

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.base_dir / path).resolve()

    def _setup_lighting(self):
        ambient = AmbientLight("moon_stack_ambient")
        ambient.setColor((0.52, 0.52, 0.58, 1))
        ambient_node = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_node)

        key_light = DirectionalLight("moon_stack_key")
        key_light.setColor((0.92, 0.92, 0.95, 1))
        key_node = self.render.attachNewNode(key_light)
        key_node.setHpr(32, -35, 0)
        self.render.setLight(key_node)

        rim_light = DirectionalLight("moon_stack_rim")
        rim_light.setColor((0.35, 0.35, 0.45, 1))
        rim_node = self.render.attachNewNode(rim_light)
        rim_node.setHpr(-148, -18, 0)
        self.render.setLight(rim_node)

    def _setup_planets(self):
        earth_radius = float(getattr(config, "MOON_STACK_EARTH_RADIUS_UNITS", 2.6))
        moon_radius = float(getattr(config, "MOON_STACK_MOON_RADIUS_UNITS", 1.9))

        self.earth = self.sphere_template.copyTo(self.render)
        self.earth.setScale(earth_radius)
        self.earth.setPos(0, 0, -earth_radius)
        self.earth.setColorScale(0.2, 0.45, 0.95, 1.0)

        moon_z = (self.target_km * self.km_to_units) + moon_radius
        self.moon = self.sphere_template.copyTo(self.render)
        self.moon.setScale(moon_radius)
        self.moon.setPos(0, 0, moon_z)
        self.moon.setColorScale(0.84, 0.84, 0.88, 1.0)

        self.top_marker = self.sphere_template.copyTo(self.render)
        self.top_marker.setScale(float(getattr(config, "MOON_STACK_TOP_MARKER_RADIUS_UNITS", 0.35)))
        self.top_marker.setColorScale(1.0, 0.85, 0.2, 1.0)

    def _setup_overlay(self):
        title_color = getattr(config, "MOON_STACK_TITLE_COLOR", (0.95, 0.95, 1.0, 1.0))
        text_color = getattr(config, "MOON_STACK_TEXT_COLOR", (0.92, 0.94, 1.0, 1.0))

        self.title_text = OnscreenText(
            text="Earth to Moon Objective",
            pos=(0.0, 0.92),
            scale=0.058,
            fg=title_color,
            align=TextNode.ACenter,
            mayChange=True,
        )

        self.progress_text = OnscreenText(
            text="",
            pos=(-1.28, 0.83),
            scale=0.042,
            fg=text_color,
            align=TextNode.ALeft,
            mayChange=True,
        )

        self.counts_text = OnscreenText(
            text="",
            pos=(-1.28, 0.67),
            scale=0.036,
            fg=text_color,
            align=TextNode.ALeft,
            mayChange=True,
        )

        self.milestones_text = OnscreenText(
            text="",
            pos=(-1.28, 0.51),
            scale=0.035,
            fg=text_color,
            align=TextNode.ALeft,
            mayChange=True,
        )

        self.flash_text = OnscreenText(
            text="",
            pos=(0.0, 0.1),
            scale=0.09,
            fg=(1.0, 0.94, 0.6, 0.0),
            align=TextNode.ACenter,
            mayChange=True,
        )

        milestones = [25, 50, 75, 100]
        reached = [value for value in milestones if self._get_progress_pct_preview() >= value]
        spacing = max(3.5, self.duration_seconds / float(max(2, len(reached) + 1)))
        self.milestone_schedule = [(4.0 + i * spacing, value) for i, value in enumerate(reached)]
        self.flash_message = ""
        self.flash_end_time = 0.0

    def _get_progress_pct_preview(self) -> float:
        ordered_sources, source_map = self._build_current_sources()
        if not ordered_sources:
            return 0.0

        current_map = {entry["username_norm"]: entry for entry in ordered_sources}
        active = [entry for entry in self._load_state().get("history", []) if entry.get("active")]
        total = 0

        for entry in active:
            username_norm = normalize_username(entry.get("username_norm") or entry.get("username"))
            if username_norm in current_map:
                total += int(current_map[username_norm].get("km_value", 1) or 1)

        # Include any current users that are not in active state yet.
        active_norms = {normalize_username(entry.get("username_norm") or entry.get("username")) for entry in active}
        for entry in ordered_sources:
            if entry["username_norm"] not in active_norms:
                total += int(entry.get("km_value", 1) or 1)

        if self.target_km <= 0:
            return 0.0
        return min(100.0, (float(total) / float(self.target_km)) * 100.0)

    def _safe_load_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return [row for row in data if isinstance(row, dict)]
            return []
        except Exception as exc:
            print(f"Warning: failed to load {path}: {exc}")
            return []

    def _build_current_sources(self) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        if self.test_empty_mode:
            return [], {}
        if self.test_minimal_mode:
            ordered: list[dict[str, Any]] = []
            by_username: dict[str, dict[str, Any]] = {}
            for i in range(self.test_minimal_count):
                username_norm = f"test_player_{i + 1:05d}"
                entry = {
                    "username": username_norm,
                    "username_norm": username_norm,
                    "profile_url": f"https://www.instagram.com/{username_norm}",
                    "profile_pic_url": "",
                    "source": "test",
                    "tier": "follower",
                    "km_value": int(self.follower_weight),
                    "diameter_mult": float(self.follower_diameter),
                }
                ordered.append(entry)
                by_username[username_norm] = entry
            return ordered, by_username

        instagram_rows = self._safe_load_list(self.instagram_path)
        discord_rows = self._safe_load_list(self.discord_path)
        club_rows = self._safe_load_list(self.club_path)

        ordered_keys: list[str] = []
        by_username: dict[str, dict[str, Any]] = {}

        def merge_entry(raw: dict[str, Any], *, source: str, tier: str, km_value: int, diameter_mult: float):
            username = str(raw.get("username") or raw.get("discord_username") or "").strip()
            username_norm = normalize_username(username)
            if not username_norm:
                return

            profile_url = str(raw.get("profile_url") or "").strip()
            if not profile_url:
                profile_url = f"https://www.instagram.com/{username_norm}"

            profile_pic_url = str(raw.get("profile_pic_url") or "").strip()

            candidate = {
                "username": username or username_norm,
                "username_norm": username_norm,
                "profile_url": profile_url,
                "profile_pic_url": profile_pic_url,
                "source": source,
                "tier": tier,
                "km_value": int(km_value),
                "diameter_mult": float(diameter_mult),
            }

            existing = by_username.get(username_norm)
            if existing is None:
                by_username[username_norm] = candidate
                ordered_keys.append(username_norm)
                return

            existing_km = int(existing.get("km_value", 1) or 1)
            if km_value > existing_km:
                existing["source"] = source
                existing["tier"] = tier
                existing["km_value"] = int(km_value)
                existing["diameter_mult"] = float(diameter_mult)
                if profile_pic_url:
                    existing["profile_pic_url"] = profile_pic_url
                if profile_url:
                    existing["profile_url"] = profile_url
                existing["username"] = username or existing.get("username") or username_norm
                return

            if not existing.get("profile_pic_url") and profile_pic_url:
                existing["profile_pic_url"] = profile_pic_url
            if not existing.get("profile_url") and profile_url:
                existing["profile_url"] = profile_url
            if username and len(username) >= len(str(existing.get("username") or "")):
                existing["username"] = username

        for row in instagram_rows:
            merge_entry(
                row,
                source="instagram",
                tier="follower",
                km_value=self.follower_weight,
                diameter_mult=self.follower_diameter,
            )

        for row in discord_rows:
            merge_entry(
                row,
                source="discord",
                tier="discord",
                km_value=self.discord_weight,
                diameter_mult=self.discord_diameter,
            )

        for row in club_rows:
            merge_entry(
                row,
                source="club",
                tier="club",
                km_value=self.club_weight,
                diameter_mult=self.club_diameter,
            )

        ordered = [by_username[key] for key in ordered_keys]
        return ordered, by_username

    def _load_state(self) -> dict[str, Any]:
        if self.test_empty_mode or self.test_minimal_mode:
            return {
                "version": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "target_km": self.target_km,
                "next_id": 1,
                "history": [],
            }

        if self.state_path.exists():
            try:
                with self.state_path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict) and isinstance(data.get("history"), list):
                    data.setdefault("version", 1)
                    data.setdefault("next_id", 1)
                    data.setdefault("target_km", self.target_km)
                    data.setdefault("created_at", datetime.now().isoformat())
                    return data
            except Exception as exc:
                print(f"Warning: failed to load moon stack state {self.state_path}: {exc}")

        return {
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "target_km": self.target_km,
            "next_id": 1,
            "history": [],
        }

    def _save_state(self):
        if self.test_empty_mode or self.test_minimal_mode:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state["updated_at"] = datetime.now().isoformat()
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(self.state, handle, ensure_ascii=False, separators=(",", ":"))

    def _reconcile_state(
        self,
        ordered_sources: list[dict[str, Any]],
        source_map: dict[str, dict[str, Any]],
    ) -> dict[str, int]:
        history = self.state.get("history", [])
        now = datetime.now().isoformat()

        active_index: dict[str, int] = {}
        for idx, entry in enumerate(history):
            username_norm = normalize_username(entry.get("username_norm") or entry.get("username"))
            entry["username_norm"] = username_norm
            entry.setdefault("active", False)
            if not username_norm:
                entry["active"] = False
                continue
            if entry.get("active"):
                prev = active_index.get(username_norm)
                if prev is not None:
                    history[prev]["active"] = False
                active_index[username_norm] = idx

        removed = 0
        for username_norm, idx in list(active_index.items()):
            if username_norm in source_map:
                continue
            history[idx]["active"] = False
            removed += 1
            active_index.pop(username_norm, None)

        added = 0
        updated = 0
        next_id = int(self.state.get("next_id", 1) or 1)

        for candidate in ordered_sources:
            username_norm = candidate["username_norm"]
            idx = active_index.get(username_norm)
            if idx is None:
                entry = {
                    "id": next_id,
                    "username": candidate["username"],
                    "username_norm": username_norm,
                    "profile_url": candidate.get("profile_url", ""),
                    "profile_pic_url": candidate.get("profile_pic_url", ""),
                    "source": candidate.get("source", "instagram"),
                    "tier": candidate.get("tier", "follower"),
                    "km_value": int(candidate.get("km_value", 1) or 1),
                    "diameter_mult": float(candidate.get("diameter_mult", 1.0) or 1.0),
                    "first_seen": now,
                    "last_seen": now,
                    "active": True,
                }
                history.append(entry)
                active_index[username_norm] = len(history) - 1
                next_id += 1
                added += 1
                continue

            entry = history[idx]
            changed = False

            def set_if_changed(key: str, value: Any):
                nonlocal changed
                if value is None:
                    return
                if isinstance(value, str) and not value:
                    return
                if entry.get(key) != value:
                    entry[key] = value
                    changed = True

            set_if_changed("username", candidate.get("username", ""))
            set_if_changed("profile_url", candidate.get("profile_url", ""))
            set_if_changed("profile_pic_url", candidate.get("profile_pic_url", ""))
            set_if_changed("source", candidate.get("source", "instagram"))
            set_if_changed("tier", candidate.get("tier", "follower"))
            set_if_changed("km_value", int(candidate.get("km_value", 1) or 1))
            set_if_changed("diameter_mult", float(candidate.get("diameter_mult", 1.0) or 1.0))

            entry["active"] = True
            entry["last_seen"] = now
            if not entry.get("first_seen"):
                entry["first_seen"] = now

            if changed:
                updated += 1

        self.state["next_id"] = next_id
        self.state["target_km"] = self.target_km
        self._save_state()
        return {"added": added, "removed": removed, "updated": updated}

    def _build_stack_index(self):
        self.diameters_km: list[float] = []
        self.centers_km: list[float] = []
        self.centers_units: list[float] = []
        self.total_km = 0

        cursor_km = 0.0
        for entry in self.active_entries:
            km_value = float(entry.get("km_value", 1) or 1)
            diameter_mult = float(entry.get("diameter_mult", km_value) or km_value)
            diameter_km = max(0.0001, diameter_mult)
            center_km = cursor_km + (diameter_km * 0.5)

            self.diameters_km.append(diameter_km)
            self.centers_km.append(center_km)
            self.centers_units.append(center_km * self.km_to_units)

            cursor_km += diameter_km
            self.total_km += int(round(km_value))

        self.stack_height_km = cursor_km
        if self.target_km <= 0:
            self.progress_pct = 0.0
        else:
            self.progress_pct = min(100.0, (self.total_km / float(self.target_km)) * 100.0)

    def _update_task(self, task):
        if self.shutdown_started:
            return task.done

        dt = min(self.clock.getDt(), getattr(config, "MAX_DELTA_TIME", 1.0 / 20.0))
        if getattr(config, "EXPORT_VIDEO", False):
            dt *= float(getattr(config, "EXPORT_TIME_SCALE", 1.0) or 1.0)

        self.current_time += max(0.0, dt)
        self._update_camera()
        self._update_visible_stack()
        self._update_top_marker()
        self._update_overlay()

        self.video_recorder.capture_frame(self.current_time)

        if self.current_time >= self.duration_seconds:
            self._shutdown()
            return task.done

        return task.cont

    def _update_camera(self):
        if self.stack_height_km <= 0:
            climb_target_km = 0.0
        else:
            climb_target_km = min(self.stack_height_km, float(self.target_km))

        progress = 0.0
        if self.duration_seconds > 0:
            progress = max(0.0, min(1.0, self.current_time / self.duration_seconds))

        if progress < 0.82:
            t = progress / 0.82 if 0.82 > 0 else progress
            eased = (3.0 * t * t) - (2.0 * t * t * t)
            camera_km = climb_target_km * eased
        else:
            tail = (progress - 0.82) / 0.18 if 0.18 > 0 else 1.0
            hover_from = max(0.0, climb_target_km * 0.92)
            camera_km = hover_from + (climb_target_km - hover_from) * tail

        camera_z = (camera_km * self.km_to_units) + self.camera_height_offset
        wobble = math.sin(self.current_time * 0.85) * self.camera_zoom_amplitude
        micro_wobble = math.sin(self.current_time * 0.31) * (self.camera_zoom_amplitude * 0.45)
        camera_distance = max(0.8, self.camera_base_distance + wobble + micro_wobble)
        camera_x = math.sin(self.current_time * 0.25) * self.camera_side_sway

        self.camera.setPos(camera_x, -camera_distance, camera_z)

        look_km = min(float(self.target_km), camera_km + 5000.0)
        look_z = (look_km * self.km_to_units) + self.camera_look_offset
        self.camera.lookAt(0.0, 0.0, look_z)

    def _focus_index(self, camera_km: float) -> int:
        if not self.centers_km:
            return 0
        idx = bisect.bisect_left(self.centers_km, camera_km)
        if idx <= 0:
            return 0
        if idx >= len(self.centers_km):
            return len(self.centers_km) - 1
        prev_dist = abs(self.centers_km[idx - 1] - camera_km)
        next_dist = abs(self.centers_km[idx] - camera_km)
        return idx if next_dist < prev_dist else idx - 1

    def _update_visible_stack(self):
        if not self.active_entries:
            for node in self.visible_nodes.values():
                node.removeNode()
            self.visible_nodes.clear()
            return

        camera_km = max(0.0, (self.camera.getZ() - self.camera_height_offset) / self.km_to_units)
        focus = self._focus_index(camera_km)

        half = max(1, self.max_visible_balls // 2)
        start = max(0, focus - half)
        end = min(len(self.active_entries), start + self.max_visible_balls)
        start = max(0, end - self.max_visible_balls)

        desired = set(range(start, end))
        existing = set(self.visible_nodes.keys())

        for idx in existing - desired:
            node = self.visible_nodes.pop(idx, None)
            if node is not None:
                node.removeNode()

        for idx in sorted(desired - existing):
            self.visible_nodes[idx] = self._create_ball_node(idx)

    def _create_ball_node(self, idx: int):
        entry = self.active_entries[idx]
        node = self.sphere_template.copyTo(self.stack_root)

        diameter_units = max(0.0001, self.diameters_km[idx] * self.km_to_units)
        radius_units = max(0.00005, diameter_units * 0.5)
        node.setScale(radius_units)
        node.setPos(0.0, 0.0, self.centers_units[idx])

        texture = self._get_avatar_texture(entry)
        if texture is not None:
            node.setTexture(texture, 1)
        else:
            color = self._fallback_color(entry.get("username_norm") or entry.get("username") or "")
            node.setColorScale(color[0], color[1], color[2], 1.0)

        return node

    def _fallback_color(self, seed_text: str) -> tuple[float, float, float]:
        digest = hashlib.sha1(seed_text.encode("utf-8", errors="ignore")).digest()
        base = [digest[0], digest[1], digest[2]]
        return (
            0.35 + (base[0] / 255.0) * 0.55,
            0.35 + (base[1] / 255.0) * 0.55,
            0.35 + (base[2] / 255.0) * 0.55,
        )

    def _fallback_texture(self, username_norm: str) -> Texture | None:
        cached = self.fallback_texture_cache.get(username_norm)
        if cached is not None:
            return cached
        if Image is None:
            self.fallback_texture_cache[username_norm] = None
            return None

        color = self._fallback_color(username_norm)
        rgb = tuple(int(channel * 255) for channel in color)

        size = max(32, self.avatar_texture_size)
        image = Image.new("RGB", (size, size), rgb)
        texture = self._texture_from_image(image)
        self.fallback_texture_cache[username_norm] = texture
        return texture

    def _get_avatar_texture(self, entry: dict[str, Any]) -> Texture | None:
        username_norm = normalize_username(entry.get("username_norm") or entry.get("username"))
        profile_pic_url = str(entry.get("profile_pic_url") or "").strip()

        cache_key = f"{username_norm}|{profile_pic_url}"
        if cache_key in self.avatar_texture_cache:
            return self.avatar_texture_cache[cache_key]

        image = None
        if Image is not None:
            image = self._load_avatar_image(username_norm, profile_pic_url)

        if image is not None:
            texture = self._texture_from_image(image)
            self.avatar_texture_cache[cache_key] = texture
            return texture

        texture = self._fallback_texture(username_norm)
        self.avatar_texture_cache[cache_key] = texture
        return texture

    def _load_avatar_image(self, username_norm: str, profile_pic_url: str):
        if Image is None:
            return None

        path_candidate = None
        if profile_pic_url and not profile_pic_url.startswith(("http://", "https://")):
            local_path = profile_pic_url
            if local_path.startswith("file://"):
                local_path = local_path[7:]
            path_candidate = Path(local_path)
            if not path_candidate.is_absolute():
                path_candidate = (self.base_dir / path_candidate).resolve()

        if path_candidate and path_candidate.exists():
            try:
                with Image.open(path_candidate) as img:
                    return img.convert("RGB")
            except Exception:
                pass

        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            cached_file = self.avatar_cache_dir / f"{username_norm}{ext}"
            if not cached_file.exists():
                continue
            try:
                with Image.open(cached_file) as img:
                    return img.convert("RGB")
            except Exception:
                continue

        if self.allow_network_avatars and profile_pic_url.startswith(("http://", "https://")):
            try:
                request = urllib.request.Request(
                    profile_pic_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                        )
                    },
                )
                with urllib.request.urlopen(request, timeout=6) as response:
                    payload = response.read()
                with Image.open(io.BytesIO(payload)) as img:
                    converted = img.convert("RGB")
                self.avatar_cache_dir.mkdir(parents=True, exist_ok=True)
                try:
                    converted.save(self.avatar_cache_dir / f"{username_norm}.jpg", "JPEG", quality=82, optimize=True)
                except Exception:
                    pass
                return converted
            except Exception:
                return None

        return None

    def _texture_from_image(self, image):
        if Image is None:
            return None
        try:
            size = max(32, self.avatar_texture_size)
            if image.size[0] != image.size[1]:
                min_side = min(image.size[0], image.size[1])
                left = (image.size[0] - min_side) // 2
                top = (image.size[1] - min_side) // 2
                image = image.crop((left, top, left + min_side, top + min_side))
            if image.size[0] != size:
                image = image.resize((size, size), Image.LANCZOS)

            rgb = image.convert("RGB")
            texture = Texture()
            texture.setup2dTexture(size, size, Texture.T_unsigned_byte, Texture.F_rgb)
            texture.setRamImage(rgb.tobytes())
            texture.setMinfilter(Texture.FTLinearMipmapLinear)
            texture.setMagfilter(Texture.FTLinear)
            texture.generateRamMipmapImages()
            return texture
        except Exception:
            return None

    def _update_top_marker(self):
        z = (self.stack_height_km * self.km_to_units) + float(
            getattr(config, "MOON_STACK_TOP_MARKER_OFFSET_UNITS", 0.25)
        )
        self.top_marker.setPos(0.0, 0.0, z)

    def _update_overlay(self):
        remaining = max(0, self.target_km - self.total_km)
        self.progress_text.setText(
            f"Day {getattr(config, 'DAY_NUMBER', 1)}\n"
            f"Progress: {self.total_km:,} / {self.target_km:,} km ({self.progress_pct:.2f}%)\n"
            f"Remaining: {remaining:,} km"
        )

        self.counts_text.setText(
            "Contribution tiers\n"
            f"Follower x1: {self.tier_counts['follower']:,} ({self.tier_km['follower']:,} km)\n"
            f"Discord x10: {self.tier_counts['discord']:,} ({self.tier_km['discord']:,} km)\n"
            f"Club x100: {self.tier_counts['club']:,} ({self.tier_km['club']:,} km)"
        )

        milestones = [25, 50, 75, 100]
        status_bits = []
        for value in milestones:
            if self.progress_pct >= value:
                status_bits.append(f"[x] {value}%")
            else:
                status_bits.append(f"[ ] {value}%")
        self.milestones_text.setText("Milestones  " + "  ".join(status_bits))

        if self.milestone_schedule and self.current_time >= self.milestone_schedule[0][0] and self.current_time >= self.flash_end_time:
            _, value = self.milestone_schedule.pop(0)
            if value >= 100:
                self.flash_message = "MOON REACHED"
            else:
                self.flash_message = f"{value}% MILESTONE REACHED"
            self.flash_end_time = self.current_time + 2.4

        if self.current_time < self.flash_end_time:
            time_left = self.flash_end_time - self.current_time
            alpha = 1.0
            if time_left < 0.8:
                alpha = max(0.0, time_left / 0.8)
            self.flash_text.setText(self.flash_message)
            self.flash_text.setFg((1.0, 0.94, 0.6, alpha))
        else:
            self.flash_text.setText("")

    def _shutdown(self):
        if self.shutdown_started:
            return
        self.shutdown_started = True
        try:
            self.video_recorder.finalize(include_audio=True)
        finally:
            self.userExit()
