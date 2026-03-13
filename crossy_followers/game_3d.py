import math
import random
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

import config

from panda3d.core import (
    AmbientLight,
    CardMaker,
    ClockObject,
    DirectionalLight,
    Point2,
    Point3,
    NodePath,
    OrthographicLens,
    TextNode,
    Texture,
    TransparencyAttrib,
    Vec3,
    WindowProperties,
    loadPrcFileData,
)
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase

from subway_followers_3d.recorder import PandaVideoRecorder
from .game import CrossyFollowersGame

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None


class _ModelLibrary:
    def __init__(self, base: ShowBase, root: Path):
        self.base = base
        self.root = root
        self.templates: Dict[str, NodePath] = {}
        self.sizes: Dict[str, Tuple[float, float, float]] = {}

    def register(self, key: str, obj_rel: str, tex_rel: Optional[str] = None):
        obj_path = self.root / obj_rel
        if not obj_path.exists():
            return
        try:
            source = self.base.loader.loadModel(str(obj_path))
        except Exception:
            return

        if tex_rel:
            tex_path = self.root / tex_rel
            if tex_path.exists():
                try:
                    texture = self.base.loader.loadTexture(str(tex_path))
                    # Match Expo's crisp nearest-neighbor voxel style.
                    texture.setMinfilter(Texture.FTNearest)
                    texture.setMagfilter(Texture.FTNearest)
                    texture.setAnisotropicDegree(1)
                    source.setTexture(texture, 1)
                except Exception:
                    pass

        source.setTwoSided(True)
        source.setTransparency(TransparencyAttrib.MAlpha)

        pivot = NodePath(f"{key}_pivot")
        mesh = source.copyTo(pivot)

        # Expo models are authored in Y-up coordinates; rotate to Panda's Z-up.
        mesh.setP(90)

        bounds = pivot.getTightBounds()
        if not bounds:
            pivot.removeNode()
            return
        lo, hi = bounds
        center_x = (lo.x + hi.x) * 0.5
        center_y = (lo.y + hi.y) * 0.5
        mesh.setPos(mesh.getX() - center_x, mesh.getY() - center_y, mesh.getZ() - lo.z)

        bounds = pivot.getTightBounds()
        if not bounds:
            pivot.removeNode()
            return
        lo, hi = bounds
        sx = max(1e-4, float(hi.x - lo.x))
        sy = max(1e-4, float(hi.y - lo.y))
        sz = max(1e-4, float(hi.z - lo.z))
        self.templates[key] = pivot
        self.sizes[key] = (sx, sy, sz)

    def instantiate(self, key: str, parent: NodePath, target_size: Tuple[float, float, float]) -> Optional[NodePath]:
        template = self.templates.get(key)
        size = self.sizes.get(key)
        if template is None or size is None:
            return None
        node = template.copyTo(parent)
        tw, td, th = target_size
        sx, sy, sz = size
        node.setScale(tw / sx, td / sy, th / sz)
        return node


class CrossyFollowers3DGame(ShowBase):
    GAME_TITLE = "CROSSY FOLLOWERS"
    GAME_SUBTITLE = "Making my club members cross every day"
    PLAYER_LABEL = "club members"

    def __init__(self):
        loadPrcFileData("", f"win-size {config.SCREEN_WIDTH} {config.SCREEN_HEIGHT}")
        loadPrcFileData("", "sync-video #f")
        loadPrcFileData("", "show-frame-rate-meter #f")
        if getattr(config, "HEADLESS_MODE", False):
            loadPrcFileData("", "window-type offscreen")

        super().__init__()
        self.disableMouse()
        self.clock = ClockObject.getGlobalClock()
        self._shutting_down = False

        props = WindowProperties()
        props.setTitle(self.GAME_TITLE)
        if self.win is not None and hasattr(self.win, "requestProperties"):
            self.win.requestProperties(props)

        # Expo scene background (0x87C6FF).
        self.setBackgroundColor(0.529, 0.776, 1.0, 1.0)
        self._setup_camera_and_lens()

        self._setup_lighting()
        self.sim = self._create_simulation_backend()
        self.sim.setup_players()
        self.sim.phase = "playing"

        self.world_with_camera = self.render.attachNewNode("crossy_world_with_camera")
        base_offset = float(getattr(config, "CROSSY_3D_WORLD_BASE_OFFSET", -0.8))
        self.world_with_camera.setY(-float(self.sim.start_row) + base_offset)
        self.world_root = self.world_with_camera.attachNewNode("crossy_world")
        self.model_root = Path("_external/Expo-Crossy-Road/assets/models")
        self.models = _ModelLibrary(self, self.model_root)
        self._register_models()

        self.lane_count = int(self.sim.arena.lane_count)
        self.center_lane = (self.lane_count - 1) * 0.5
        self.row_depth = 1.0
        self.base_ground_height = 0.11
        self.row_visual_width = float(getattr(config, "CROSSY_3D_ROW_VISUAL_WIDTH", 25.0))

        self.row_nodes: Dict[int, NodePath] = {}
        self.entity_nodes: Dict[int, NodePath] = {}
        self.player_nodes: Dict[int, NodePath] = {}

        self._spawn_player_nodes()
        self._create_ui()

        self.world_follow_easing = float(getattr(config, "CROSSY_3D_WORLD_EASING", 0.03))
        self.world_follow_x_min = float(getattr(config, "CROSSY_3D_WORLD_X_MIN", -3.0))
        self.world_follow_x_max = float(getattr(config, "CROSSY_3D_WORLD_X_MAX", 2.0))
        self.sync_rows_behind = int(getattr(config, "CROSSY_3D_SYNC_ROWS_BEHIND", 18))
        self.sync_rows_ahead = int(getattr(config, "CROSSY_3D_SYNC_ROWS_AHEAD", 40))
        self.screen_cull_margin = float(getattr(config, "CROSSY_3D_SCREEN_CULL_MARGIN", 0.06))

        self.end_duration = float(getattr(config, "CROSSY_3D_END_SCREEN_DURATION", 5.0))
        self.end_timer = 0.0
        self.end_card = None
        self._manual_exit = False
        self.accept("escape", self._request_exit)

        background_music_path = str(
            getattr(config, "JETPACK_BACKGROUND_MUSIC_PATH", "assets/Sydney Tour Song adjusted.m4a")
        )
        self.video_recorder = PandaVideoRecorder(
            base=self,
            output_path=config.get_output_video_path(game_mode="crossy_followers"),
            fps=int(getattr(config, "VIDEO_FPS", 30)),
            record=bool(getattr(config, "EXPORT_VIDEO", True)),
            audio_path=background_music_path,
        )

        self.taskMgr.add(self._update_task, "crossy_followers_3d_update")

    def _create_simulation_backend(self) -> CrossyFollowersGame:
        old_headless = bool(getattr(config, "HEADLESS_MODE", False))
        old_export = bool(getattr(config, "EXPORT_VIDEO", True))
        try:
            # Keep the legacy pygame surface hidden while Panda renders the real output.
            config.HEADLESS_MODE = True
            config.EXPORT_VIDEO = False
            sim = CrossyFollowersGame()
        finally:
            config.HEADLESS_MODE = old_headless
            config.EXPORT_VIDEO = old_export
        return sim

    def _setup_lighting(self):
        ambient = AmbientLight("crossy_ambient")
        ambient_intensity = float(getattr(config, "CROSSY_3D_AMBIENT_INTENSITY", 1.8))
        ambient.setColor((ambient_intensity, ambient_intensity, ambient_intensity, 1.0))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        directional = DirectionalLight("crossy_sun")
        directional_intensity = float(getattr(config, "CROSSY_3D_DIRECTIONAL_INTENSITY", 1.0))
        directional.setColor((directional_intensity, directional_intensity, directional_intensity, 1.0))
        directional_np = self.render.attachNewNode(directional)
        light_pos = getattr(config, "CROSSY_3D_LIGHT_POS", (20.0, 0.05, 30.0))
        directional_np.setPos(float(light_pos[0]), float(light_pos[1]), float(light_pos[2]))
        directional_np.lookAt(0, 0, 0)
        self.render.setLight(directional_np)

    def _setup_camera_and_lens(self):
        lens = OrthographicLens()
        lens.setNearFar(-100.0, 100.0)
        self.cam.node().setLens(lens)
        self._ortho_lens = lens
        self._last_lens_size = (0, 0)
        self._ortho_view_height = float(getattr(config, "CROSSY_3D_ORTHO_VIEW_HEIGHT", 12.0))

        # Mirror Expo's orthographic camera orientation.
        cam_pos = getattr(config, "CROSSY_3D_CAMERA_POS", (-1.0, -2.9, 2.8))
        cam_look = getattr(config, "CROSSY_3D_CAMERA_LOOK_AT", (0.0, 0.0, 0.0))
        self.camera.setPos(float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2]))
        self.camera.lookAt(float(cam_look[0]), float(cam_look[1]), float(cam_look[2]))
        self._update_lens_if_needed(force=True)

    def _update_lens_if_needed(self, force: bool = False):
        if self.win is None or not hasattr(self.win, "getXSize") or not hasattr(self.win, "getYSize"):
            return
        width = int(self.win.getXSize())
        height = int(self.win.getYSize())
        if width <= 0 or height <= 0:
            return
        if not force and (width, height) == self._last_lens_size:
            return
        self._last_lens_size = (width, height)
        aspect = float(width) / float(max(1, height))
        film_height = self._ortho_view_height
        film_width = film_height * aspect
        self._ortho_lens.setFilmSize(film_width, film_height)

    def _register_models(self):
        self.models.register("row_grass_light", "environment/grass/model.obj", "environment/grass/light-grass.png")
        self.models.register("row_grass_dark", "environment/grass/model.obj", "environment/grass/dark-grass.png")
        self.models.register("row_road_stripes", "environment/road/model.obj", "environment/road/stripes-texture.png")
        self.models.register("row_road_blank", "environment/road/model.obj", "environment/road/blank-texture.png")
        self.models.register("row_river", "environment/river/0.obj", "environment/river/0.png")
        self.models.register("row_rail", "environment/railroad/0.obj", "environment/railroad/0.png")

        self.models.register("car_blue_car", "vehicles/blue_car/0.obj", "vehicles/blue_car/0.png")
        self.models.register("car_green_car", "vehicles/green_car/0.obj", "vehicles/green_car/0.png")
        self.models.register("car_orange_car", "vehicles/orange_car/0.obj", "vehicles/orange_car/0.png")
        self.models.register("car_police_car", "vehicles/police_car/0.obj", "vehicles/police_car/0.png")
        self.models.register("car_purple_car", "vehicles/purple_car/0.obj", "vehicles/purple_car/0.png")
        self.models.register("car_red_truck", "vehicles/red_truck/0.obj", "vehicles/red_truck/0.png")
        self.models.register("car_blue_truck", "vehicles/blue_truck/0.obj", "vehicles/blue_truck/0.png")
        self.models.register("car_taxi", "vehicles/taxi/0.obj", "vehicles/taxi/0.png")

        self.models.register("log0", "environment/log/0/0.obj", "environment/log/0/0.png")
        self.models.register("log1", "environment/log/1/0.obj", "environment/log/1/0.png")
        self.models.register("log2", "environment/log/2/0.obj", "environment/log/2/0.png")
        self.models.register("log3", "environment/log/3/0.obj", "environment/log/3/0.png")

        self.models.register("tree0", "environment/tree/0/0.obj", "environment/tree/0/0.png")
        self.models.register("tree1", "environment/tree/1/0.obj", "environment/tree/1/0.png")
        self.models.register("tree2", "environment/tree/2/0.obj", "environment/tree/2/0.png")
        self.models.register("tree3", "environment/tree/3/0.obj", "environment/tree/3/0.png")

        self.models.register("boulder0", "environment/boulder/0/0.obj", "environment/boulder/0/0.png")
        self.models.register("boulder1", "environment/boulder/1/0.obj", "environment/boulder/1/0.png")
        self.models.register("lily_pad", "environment/lily_pad/0.obj", "environment/lily_pad/0.png")

        self.models.register("train_front", "vehicles/train/front/0.obj", "vehicles/train/front/0.png")
        self.models.register("train_middle", "vehicles/train/middle/0.obj", "vehicles/train/middle/0.png")
        self.models.register("train_back", "vehicles/train/back/0.obj", "vehicles/train/back/0.png")

    def _create_ui(self):
        self.title = OnscreenText(
            text=self.GAME_TITLE,
            parent=self.a2dTopCenter,
            pos=(0, -0.12),
            scale=0.082,
            fg=(0, 0, 0, 1),
            bg=(0.82, 0.9, 0.98, 0.38),
            align=TextNode.ACenter,
        )
        self.subtitle = OnscreenText(
            text=self.GAME_SUBTITLE,
            parent=self.a2dTopCenter,
            pos=(0, -0.20),
            scale=0.05,
            fg=(0, 0, 0, 1),
            bg=(0.82, 0.9, 0.98, 0.34),
            align=TextNode.ACenter,
        )
        prompt = str(getattr(config, "COMMENT_RESULT_PROMPT_TEXT", "") or "")
        self.prompt = OnscreenText(
            text=prompt,
            parent=self.a2dTopCenter,
            pos=(0, -0.26),
            scale=0.045,
            fg=(0, 0, 0, 1),
            bg=(0.82, 0.9, 0.98, 0.32),
            align=TextNode.ACenter,
        )

        self.day_counter = OnscreenText(
            text="",
            parent=self.a2dBottomCenter,
            pos=(0, 0.09),
            scale=0.06,
            fg=(0, 0, 0, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )
        self.stats_text = OnscreenText(
            text="",
            parent=self.a2dTopLeft,
            pos=(0.06, -0.34),
            scale=0.045,
            fg=(1, 1, 1, 1),
            bg=(0, 0, 0, 0.45),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.elim_text = OnscreenText(
            text="",
            parent=self.a2dTopRight,
            pos=(-0.06, -0.34),
            scale=0.04,
            fg=(0, 0, 0, 1),
            align=TextNode.ARight,
            mayChange=True,
        )
        self.club_text = OnscreenText(
            text="",
            parent=self.a2dBottomCenter,
            pos=(0, 0.17),
            scale=0.035,
            fg=(1, 1, 1, 1),
            bg=(0, 0, 0, 0.45),
            align=TextNode.ACenter,
            mayChange=True,
        )

    def _spawn_player_nodes(self):
        for player in self.sim.players:
            card = self._build_avatar_card(player)
            self.player_nodes[id(player)] = card

    def _build_avatar_card(self, player) -> NodePath:
        cm = CardMaker(f"avatar_{getattr(player, 'id', id(player))}")
        cm.setFrame(-0.34, 0.34, 0.0, 0.68)
        node = self.world_root.attachNewNode(cm.generate())
        node.setBillboardPointEye()
        node.setTransparency(TransparencyAttrib.MAlpha)

        texture = self._texture_for_player(player)
        if texture is not None:
            node.setTexture(texture, 1)
        else:
            color = random.choice(getattr(config, "RANDOM_COLORS", [(220, 220, 220)]))
            if max(color) > 1.0:
                color = (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
            node.setColor(color[0], color[1], color[2], 1.0)

        if getattr(player, "is_club_member", False):
            ring_cm = CardMaker(f"ring_{getattr(player, 'id', id(player))}")
            ring_cm.setFrame(-0.4, 0.4, -0.02, 0.76)
            ring = node.attachNewNode(ring_cm.generate())
            ring.setPos(0, -0.01, 0.02)
            ring.setColor(1.0, 0.94, 0.76, 0.5)
            ring.setTransparency(TransparencyAttrib.MAlpha)
        return node

    def _texture_for_player(self, player):
        avatar = getattr(player, "avatar_image", None)
        if avatar is None:
            return None
        try:
            pil = avatar.convert("RGBA")
            pil = self._apply_circle_mask(pil)
            tex = Texture()
            tex.setup2dTexture(pil.width, pil.height, Texture.T_unsigned_byte, Texture.F_rgba)
            tex.setRamImage(pil.tobytes())
            return tex
        except Exception:
            return None

    @staticmethod
    def _apply_circle_mask(pil):
        if Image is None or ImageDraw is None:
            return pil
        size = min(pil.size)
        if pil.size[0] != pil.size[1]:
            left = (pil.size[0] - size) // 2
            top = (pil.size[1] - size) // 2
            pil = pil.crop((left, top, left + size, top + size))
        if size != 256:
            pil = pil.resize((256, 256), Image.LANCZOS)
        mask = Image.new("L", pil.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, pil.size[0] - 1, pil.size[1] - 1), fill=255)
        pil.putalpha(mask)
        return pil

    def _x_to_world(self, x_value: float) -> float:
        lane_coord = (x_value - self.sim.arena.screen_left) / max(1e-6, self.sim.arena.lane_width) - 0.5
        return lane_coord - self.center_lane

    def _row_to_world(self, row_value: float) -> float:
        return float(row_value) * self.row_depth

    def _row_model_key(self, row) -> str:
        if row.row_type == "grass":
            return "row_grass_light" if row.variant == 0 else "row_grass_dark"
        if row.row_type == "road":
            return "row_road_stripes" if row.variant == 0 else "row_road_blank"
        if row.row_type == "water":
            return "row_river"
        return "row_rail"

    def _entity_model_key(self, entity) -> Optional[str]:
        if entity.kind == "car":
            return f"car_{entity.sprite}" if f"car_{entity.sprite}" in self.models.templates else "car_blue_car"
        if entity.kind == "log":
            return entity.sprite if entity.sprite in self.models.templates else "log0"
        if entity.kind == "tree":
            return entity.sprite if entity.sprite in self.models.templates else "tree0"
        if entity.kind == "boulder":
            return entity.sprite if entity.sprite in self.models.templates else "boulder0"
        if entity.kind == "lily":
            return "lily_pad"
        if entity.kind == "train":
            return "train_middle"
        return None

    def _ensure_row_node(self, row):
        idx = int(row.index)
        if idx in self.row_nodes:
            return
        row_np = self.world_root.attachNewNode(f"row_{idx}")
        key = self._row_model_key(row)

        thickness = self.base_ground_height
        if row.row_type == "water":
            thickness = 0.07
        elif row.row_type == "rail":
            thickness = 0.13

        model = self.models.instantiate(
            key,
            row_np,
            (self.row_visual_width, self.row_depth, thickness),
        )
        if model is None:
            cm = CardMaker(f"row_fallback_{idx}")
            cm.setFrame(-self.row_visual_width * 0.5, self.row_visual_width * 0.5, -0.5, 0.5)
            fallback = row_np.attachNewNode(cm.generate())
            fallback.setP(-90)
            fallback.setScale(1.0, self.row_depth, 1.0)
            fallback.setPos(0, 0, thickness)
            if row.row_type == "water":
                fallback.setColor(0.28, 0.56, 0.8, 1.0)
            elif row.row_type == "road":
                fallback.setColor(0.3, 0.32, 0.36, 1.0)
            elif row.row_type == "rail":
                fallback.setColor(0.48, 0.48, 0.5, 1.0)
            else:
                fallback.setColor(0.4, 0.62, 0.36, 1.0)
        row_np.setPos(0, self._row_to_world(idx) + self.row_depth * 0.5, 0)
        self.row_nodes[idx] = row_np

    def _build_train_node(self, entity, parent: NodePath, width_lanes: float) -> NodePath:
        train_np = parent.attachNewNode("train")
        body_width = max(0.6, width_lanes - 1.2)
        front_w = max(0.5, min(1.0, width_lanes * 0.2))
        back_w = front_w

        mid = self.models.instantiate("train_middle", train_np, (body_width, 0.9, 0.7))
        front = self.models.instantiate("train_front", train_np, (front_w, 0.9, 0.7))
        back = self.models.instantiate("train_back", train_np, (back_w, 0.9, 0.7))

        if mid:
            mid.setPos(0, 0, 0)
        if front:
            front.setPos(body_width * 0.5 + front_w * 0.5, 0, 0)
        if back:
            back.setPos(-(body_width * 0.5 + back_w * 0.5), 0, 0)

        if mid is None and front is None and back is None:
            cm = CardMaker("train_fallback")
            cm.setFrame(-width_lanes * 0.5, width_lanes * 0.5, 0, 0.7)
            card = train_np.attachNewNode(cm.generate())
            card.setColor(0.78, 0.26, 0.26, 1.0)
            card.setTransparency(TransparencyAttrib.MAlpha)

        return train_np

    def _create_entity_node(self, entity) -> NodePath:
        root = self.world_root.attachNewNode(f"entity_{id(entity)}")
        width_lanes = max(0.25, float(entity.width) / max(1e-6, self.sim.arena.lane_width))

        if entity.kind == "train":
            self._build_train_node(entity, root, width_lanes)
            return root

        key = self._entity_model_key(entity)
        if entity.kind == "car":
            target_size = (width_lanes, 0.9, 0.58)
        elif entity.kind == "log":
            target_size = (width_lanes, 0.65, 0.32)
        elif entity.kind == "lily":
            target_size = (max(0.45, width_lanes), 0.55, 0.08)
        elif entity.kind == "tree":
            target_size = (max(0.5, width_lanes), 0.6, 1.05)
        elif entity.kind == "boulder":
            target_size = (max(0.5, width_lanes), 0.6, 0.72)
        else:
            target_size = (max(0.45, width_lanes), 0.7, 0.5)

        node = None
        if key:
            node = self.models.instantiate(key, root, target_size)
        if node is None:
            cm = CardMaker(f"entity_fallback_{id(entity)}")
            cm.setFrame(-target_size[0] * 0.5, target_size[0] * 0.5, 0, target_size[2])
            fallback = root.attachNewNode(cm.generate())
            fallback.setColor(0.7, 0.7, 0.7, 1.0)
            fallback.setTransparency(TransparencyAttrib.MAlpha)
        return root

    def _is_world_visible(self, x: float, y: float, z: float, margin: Optional[float] = None) -> bool:
        lens = self.cam.node().getLens()
        # Input coordinates are in world_root-local space.
        # Project from world_root -> camera space so culling follows camera/world transforms.
        camera_point = self.cam.getRelativePoint(self.world_root, Point3(float(x), float(y), float(z)))
        projected = Point2()
        if not lens.project(camera_point, projected):
            return False
        pad = self.screen_cull_margin if margin is None else float(margin)
        return (
            -1.0 - pad <= projected.x <= 1.0 + pad
            and -1.0 - pad <= projected.y <= 1.0 + pad
        )

    def _is_row_visible(self, row_y: float) -> bool:
        depth_half = self.row_depth * 0.55
        x_half = self.row_visual_width * 0.42
        samples = [
            (0.0, row_y, 0.04),
            (0.0, row_y - depth_half, 0.04),
            (0.0, row_y + depth_half, 0.04),
        ]
        for sx in (-x_half, x_half):
            samples.append((sx, row_y, 0.04))
        for sx, sy, sz in samples:
            if self._is_world_visible(sx, sy, sz):
                return True
        return False

    def _is_entity_visible(self, x: float, row_y: float, half_width_lanes: float) -> bool:
        half_w = max(0.18, float(half_width_lanes))
        samples = (
            (x, row_y, 0.16),
            (x - half_w, row_y, 0.16),
            (x + half_w, row_y, 0.16),
        )
        for sx, sy, sz in samples:
            if self._is_world_visible(sx, sy, sz):
                return True
        return False

    def _sync_world(self):
        visible_min = max(0, int(math.floor(self.sim.camera_row)) - max(6, self.sync_rows_behind))
        visible_max = int(math.ceil(self.sim.camera_row + max(16, self.sync_rows_ahead)))

        active_rows = set()
        active_entities = set()

        for row_index, row in list(self.sim.rows.items()):
            if row_index < visible_min or row_index > visible_max:
                continue
            active_rows.add(row_index)
            self._ensure_row_node(row)

            row_y = self._row_to_world(row_index) + self.row_depth * 0.5
            row_node = self.row_nodes.get(row_index)
            row_visible = self._is_row_visible(row_y)
            if row_node is not None:
                if row_visible:
                    row_node.show()
                else:
                    row_node.hide()

            for entity in row.entities:
                entity_id = id(entity)
                active_entities.add(entity_id)
                node = self.entity_nodes.get(entity_id)
                if node is None:
                    node = self._create_entity_node(entity)
                    self.entity_nodes[entity_id] = node

                node.setPos(self._x_to_world(entity.x), row_y, 0.01)
                if entity.kind in {"car", "log"}:
                    node.setH(90 if entity.speed >= 0 else -90)
                elif entity.kind == "train":
                    # Trains are assembled along +X/-X in _build_train_node, so keep
                    # heading on that axis instead of rotating like car/log meshes.
                    node.setH(0 if entity.speed >= 0 else 180)
                elif entity.kind in {"tree", "boulder"}:
                    node.setH((row_index * 17 + entity_id) % 360)

                entity_half_width = (float(entity.width) / max(1e-6, self.sim.arena.lane_width)) * 0.5
                if row_visible and self._is_entity_visible(self._x_to_world(entity.x), row_y, entity_half_width):
                    node.show()
                else:
                    node.hide()

        stale_rows = [idx for idx in self.row_nodes.keys() if idx not in active_rows]
        for idx in stale_rows:
            try:
                self.row_nodes[idx].removeNode()
            except Exception:
                pass
            self.row_nodes.pop(idx, None)

        stale_entities = [entity_id for entity_id in self.entity_nodes.keys() if entity_id not in active_entities]
        for entity_id in stale_entities:
            try:
                self.entity_nodes[entity_id].removeNode()
            except Exception:
                pass
            self.entity_nodes.pop(entity_id, None)

        for player in self.sim.players:
            node = self.player_nodes.get(id(player))
            if node is None:
                continue
            if not player.alive and not player.is_fading():
                node.hide()
                continue
            node.show()
            player_world_x = self._x_to_world(player.x)
            player_world_y = self._row_to_world(player.grid_row) + 0.52
            node.setPos(player_world_x, player_world_y, 0.25)
            if not self._is_world_visible(player_world_x, player_world_y, 0.25):
                node.hide()
                continue
            alpha = 1.0
            if hasattr(player, "alpha"):
                alpha = max(0.0, min(1.0, float(player.alpha) / 255.0))
            node.setColorScale(1.0, 1.0, 1.0, alpha)

    def _update_world_transform(self, dt: float):
        alive = [player for player in self.sim.players if player.alive]
        candidates = alive if alive else self.sim.players
        if not candidates:
            return

        leader = max(candidates, key=lambda player: (player.grid_row, player.max_row, player.username))
        target_row = float(leader.grid_row)
        target_local_y = -(target_row - float(self.sim.start_row))
        target_local_x = max(
            self.world_follow_x_min,
            min(self.world_follow_x_max, -self._x_to_world(leader.x)),
        )

        # Match Expo's CAMERA_EASING behavior (~0.03 at 60fps).
        steps = max(1.0, dt * 60.0)
        blend = 1.0 - math.pow(max(0.0, 1.0 - self.world_follow_easing), steps)

        current = self.world_root.getPos()
        desired = Vec3(target_local_x, target_local_y, 0.0)
        self.world_root.setPos(current + (desired - current) * blend)

    def _club_day(self) -> int:
        global_day = int(getattr(config, "DAY_NUMBER", 1))
        offset = int(
            getattr(
                config,
                "CROSSY_FOLLOWERS_DAY_OFFSET",
                getattr(config, "JETPACK_FOLLOWERS_DAY_OFFSET", getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71)),
            )
        )
        return max(1, global_day - offset)

    def _update_ui(self):
        alive_count = sum(1 for player in self.sim.players if player.alive)
        leader_progress = 0
        if self.sim.players:
            leader_progress = max(player.progress_score(self.sim.start_row) for player in self.sim.players)
        self.stats_text.setText(
            f"Alive: {alive_count}\nLeader: {leader_progress} rows\nTime: {self.sim.game_time:.1f}s"
        )

        self.day_counter.setText(f"Day {self._club_day()}: {len(self.sim.players)} {self.PLAYER_LABEL}")

        eliminations = list(self.sim.recent_eliminations[:6])
        if eliminations:
            self.elim_text.setText("Eliminated:\n" + "\n".join(eliminations))
        else:
            self.elim_text.setText("")

        spotlight = self.sim.club_spotlight
        if spotlight is not None and getattr(spotlight, "username", ""):
            self.club_text.setText(f"Club members are always visible and have a holy light.\nSpotlight: {spotlight.username}")
        else:
            self.club_text.setText("Club members are always visible and have a holy light.")

    def _show_end_card(self):
        if self.end_card is not None:
            return
        sorted_players = sorted(
            self.sim.players,
            key=lambda player: (player.placement if player.placement is not None else 10**9, player.username),
        )
        lines = ["GAME COMPLETE", ""]
        for player in sorted_players[:10]:
            placement = player.placement if player.placement is not None else 0
            progress = player.progress_score(self.sim.start_row)
            lines.append(f"{placement}. {player.username} ({progress} rows)")
        self.end_card = OnscreenText(
            text="\n".join(lines),
            pos=(0, 0.2),
            scale=0.055,
            fg=(1.0, 0.95, 0.78, 1.0),
            bg=(0.0, 0.0, 0.0, 0.5),
            align=TextNode.ACenter,
        )

    def _request_exit(self):
        self._manual_exit = True

    def _update_task(self, task):
        if self._manual_exit:
            self._shutdown()
            return task.done

        self._update_lens_if_needed()
        dt = self.clock.getDt()
        dt = min(dt, float(getattr(config, "MAX_DELTA_TIME", 0.05)))

        if not self.sim.game_over:
            self.sim.update(dt)
            self._update_world_transform(dt)
            self._sync_world()
            self._update_ui()
        else:
            self._update_world_transform(dt)
            self._sync_world()
            self._update_ui()
            self._show_end_card()
            self.end_timer += dt
            if self.end_timer >= self.end_duration:
                self._shutdown()
                return task.done

        self.video_recorder.capture_frame(self.sim.game_time)
        return task.cont

    def _shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            self.video_recorder.finalize(include_audio=True)
        except Exception:
            pass

        for ui in (self.title, self.subtitle, self.prompt, self.day_counter, self.stats_text, self.elim_text, self.club_text, self.end_card):
            if ui is not None:
                try:
                    ui.destroy()
                except Exception:
                    pass

        try:
            self.sim.audio_logger.stop()
        except Exception:
            pass
        try:
            self.sim.sound.cleanup()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass

        self.userExit()
