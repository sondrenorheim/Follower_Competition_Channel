import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    GAME_SUBTITLE = "Making my followers cross every day"
    PLAYER_LABEL = "followers"

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
        self.row_node_keys: Dict[int, str] = {}
        self.row_pool: Dict[str, List[NodePath]] = {}
        self.entity_nodes: Dict[int, NodePath] = {}
        self.entity_node_keys: Dict[int, Optional[Tuple[str, Tuple[float, float, float]]]] = {}
        self.entity_pool: Dict[Tuple[str, Tuple[float, float, float]], List[NodePath]] = {}
        self.player_nodes: Dict[int, NodePath] = {}
        self._tile_offset_cache: Dict[int, List[Tuple[float, float, float]]] = {}

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
        self.status_text = OnscreenText(
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
        return node

    def _texture_for_player(self, player):
        avatar = getattr(player, "avatar_image", None)
        if avatar is None:
            return self._fallback_texture_for_player(player)
        try:
            pil = avatar.convert("RGBA")
            pil = self._apply_circle_mask(pil)
            return self._pil_to_texture(pil)
        except Exception:
            return self._fallback_texture_for_player(player)

    def _fallback_texture_for_player(self, player):
        if Image is None or ImageDraw is None:
            return None
        try:
            size = 256
            color = tuple(getattr(player, "color", random.choice(getattr(config, "RANDOM_COLORS", [(220, 220, 220)]))))
            if len(color) >= 3 and max(color[:3]) <= 1.0:
                fill = tuple(int(max(0.0, min(1.0, channel)) * 255) for channel in color[:3])
            else:
                fill = tuple(int(max(0, min(255, channel))) for channel in color[:3])

            border_width = max(2, int(getattr(config, "FOLLOWER_BORDER_WIDTH", 2)))
            image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.ellipse((0, 0, size - 1, size - 1), fill=(*fill, 255))
            inset = border_width // 2
            draw.ellipse(
                (inset, inset, size - 1 - inset, size - 1 - inset),
                outline=(0, 0, 0, 255),
                width=border_width,
            )
            return self._pil_to_texture(image)
        except Exception:
            return None

    @staticmethod
    def _pil_to_texture(pil) -> Texture:
        tex = Texture()
        tex.setup2dTexture(pil.width, pil.height, Texture.T_unsigned_byte, Texture.F_rgba)
        tex.setRamImage(pil.tobytes())
        tex.setMinfilter(Texture.FTLinear)
        tex.setMagfilter(Texture.FTLinear)
        return tex

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
        border_width = max(2, int(getattr(config, "FOLLOWER_BORDER_WIDTH", 2)))
        inset = border_width // 2
        draw = ImageDraw.Draw(pil)
        draw.ellipse(
            (inset, inset, pil.size[0] - 1 - inset, pil.size[1] - 1 - inset),
            outline=(0, 0, 0, 255),
            width=border_width,
        )
        return pil

    def _x_to_world(self, x_value: float) -> float:
        lane_coord = (x_value - self.sim.arena.screen_left) / max(1e-6, self.sim.arena.lane_width) - 0.5
        return lane_coord - self.center_lane

    def _row_to_world(self, row_value: float) -> float:
        return float(row_value) * self.row_depth

    def _player_world_x(self, player) -> float:
        row = self.sim._ensure_row(player.grid_row)
        if getattr(row, "row_type", "") == "water":
            source_x = player.x
        else:
            source_x = self.sim.arena.lane_to_x(getattr(player, "grid_lane", 0))
        return self._x_to_world(source_x)

    def _player_draw_key(self, player) -> Tuple[str, str, int]:
        return (
            str(getattr(player, "username", "") or ""),
            str(getattr(player, "id", "") or ""),
            id(player),
        )

    def _tile_offsets(self, count: int) -> List[Tuple[float, float, float]]:
        cached = self._tile_offset_cache.get(int(count))
        if cached is not None:
            return cached

        if count <= 1:
            offsets = [(0.0, 0.0, 0.0)]
            self._tile_offset_cache[int(count)] = offsets
            return offsets

        max_x = 0.22
        max_y = 0.14
        angle_step = math.pi * (3.0 - math.sqrt(5.0))
        offsets_2d: List[Tuple[float, float]] = []
        for idx in range(count):
            theta = idx * angle_step
            radius = math.sqrt((idx + 1.0) / (count + 1.0))
            offsets_2d.append((
                math.cos(theta) * max_x * radius,
                math.sin(theta) * max_y * radius,
            ))

        mean_x = sum(x for x, _ in offsets_2d) / float(count)
        mean_y = sum(y for _, y in offsets_2d) / float(count)
        centered = [
            (x - mean_x, y - mean_y, idx * 0.0015)
            for idx, (x, y) in enumerate(offsets_2d)
        ]
        self._tile_offset_cache[int(count)] = centered
        return centered

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

    def _entity_target_size(self, entity) -> Tuple[float, float, float]:
        width_lanes = max(0.25, float(entity.width) / max(1e-6, self.sim.arena.lane_width))
        if entity.kind == "car":
            return (width_lanes, 0.9, 0.58)
        if entity.kind == "log":
            return (width_lanes, 0.65, 0.32)
        if entity.kind == "lily":
            return (max(0.45, width_lanes), 0.55, 0.08)
        if entity.kind == "tree":
            return (max(0.5, width_lanes), 0.6, 1.05)
        if entity.kind == "boulder":
            return (max(0.5, width_lanes), 0.6, 0.72)
        return (max(0.45, width_lanes), 0.7, 0.5)

    def _entity_pool_key(self, entity) -> Optional[Tuple[str, Tuple[float, float, float]]]:
        if entity.kind == "train":
            return None
        model_key = self._entity_model_key(entity) or f"fallback_{entity.kind}"
        size = tuple(round(value, 2) for value in self._entity_target_size(entity))
        return model_key, size

    def _acquire_row_node(self, key: str, row_name: str, thickness: float) -> NodePath:
        pool = self.row_pool.get(key)
        if pool:
            node = pool.pop()
            node.reparentTo(self.world_root)
            node.setName(row_name)
            node.show()
            return node

        row_np = self.world_root.attachNewNode(row_name)
        model = self.models.instantiate(
            key,
            row_np,
            (self.row_visual_width, self.row_depth, thickness),
        )
        if model is None:
            cm = CardMaker(f"{row_name}_fallback")
            cm.setFrame(-self.row_visual_width * 0.5, self.row_visual_width * 0.5, -0.5, 0.5)
            fallback = row_np.attachNewNode(cm.generate())
            fallback.setP(-90)
            fallback.setScale(1.0, self.row_depth, 1.0)
            fallback.setPos(0, 0, thickness)
            if key == "row_river":
                fallback.setColor(0.28, 0.56, 0.8, 1.0)
            elif key.startswith("row_road"):
                fallback.setColor(0.3, 0.32, 0.36, 1.0)
            elif key == "row_rail":
                fallback.setColor(0.48, 0.48, 0.5, 1.0)
            else:
                fallback.setColor(0.4, 0.62, 0.36, 1.0)
        return row_np

    def _release_row_node(self, row_index: int):
        node = self.row_nodes.pop(row_index, None)
        key = self.row_node_keys.pop(row_index, None)
        if node is None:
            return
        node.hide()
        node.detachNode()
        if key is None:
            node.removeNode()
            return
        self.row_pool.setdefault(key, []).append(node)

    def _acquire_entity_node(self, entity) -> Tuple[NodePath, Optional[Tuple[str, Tuple[float, float, float]]]]:
        pool_key = self._entity_pool_key(entity)
        if pool_key is not None:
            pool = self.entity_pool.get(pool_key)
            if pool:
                node = pool.pop()
                node.reparentTo(self.world_root)
                node.show()
                return node, pool_key
        node = self._create_entity_node(entity)
        return node, pool_key

    def _release_entity_node(self, entity_id: int):
        node = self.entity_nodes.pop(entity_id, None)
        pool_key = self.entity_node_keys.pop(entity_id, None)
        if node is None:
            return
        node.hide()
        node.detachNode()
        if pool_key is None:
            node.removeNode()
            return
        self.entity_pool.setdefault(pool_key, []).append(node)

    def _ensure_row_node(self, row):
        idx = int(row.index)
        if idx in self.row_nodes:
            return
        key = self._row_model_key(row)

        thickness = self.base_ground_height
        if row.row_type == "water":
            thickness = 0.07
        elif row.row_type == "rail":
            thickness = 0.13

        row_np = self._acquire_row_node(key, f"row_{idx}", thickness)
        row_np.setPos(0, self._row_to_world(idx) + self.row_depth * 0.5, 0)
        self.row_nodes[idx] = row_np
        self.row_node_keys[idx] = key

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

        if entity.kind == "train":
            width_lanes = max(0.25, float(entity.width) / max(1e-6, self.sim.arena.lane_width))
            self._build_train_node(entity, root, width_lanes)
            return root

        key = self._entity_model_key(entity)
        target_size = self._entity_target_size(entity)

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
                    node, pool_key = self._acquire_entity_node(entity)
                    self.entity_nodes[entity_id] = node
                    self.entity_node_keys[entity_id] = pool_key

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
            self._release_row_node(idx)

        stale_entities = [entity_id for entity_id in self.entity_nodes.keys() if entity_id not in active_entities]
        for entity_id in stale_entities:
            self._release_entity_node(entity_id)

        grouped_players: Dict[Tuple[int, int], List[object]] = {}
        for player in self.sim.players:
            if not player.alive and not player.is_fading():
                continue
            tile_key = (int(getattr(player, "grid_lane", 0)), int(getattr(player, "grid_row", 0)))
            grouped_players.setdefault(tile_key, []).append(player)

        player_offsets: Dict[int, Tuple[float, float, float]] = {}
        for group in grouped_players.values():
            ordered = sorted(group, key=self._player_draw_key)
            offsets = self._tile_offsets(len(ordered))
            for player, offset in zip(ordered, offsets):
                player_offsets[id(player)] = offset

        for player in self.sim.players:
            node = self.player_nodes.get(id(player))
            if node is None:
                continue
            if not player.alive and not player.is_fading():
                node.hide()
                continue
            node.show()
            offset_x, offset_y, offset_z = player_offsets.get(id(player), (0.0, 0.0, 0.0))
            player_world_x = self._player_world_x(player) + offset_x
            player_world_y = self._row_to_world(player.grid_row) + 0.52 + offset_y
            player_world_z = 0.25 + offset_z
            node.setPos(player_world_x, player_world_y, player_world_z)
            if not self._is_world_visible(player_world_x, player_world_y, player_world_z):
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

        target_local_y = -(float(self.sim.camera_row) - float(self.sim.start_row))
        target_local_x = 0.0

        # Match Expo's CAMERA_EASING behavior (~0.03 at 60fps).
        steps = max(1.0, dt * 60.0)
        blend = 1.0 - math.pow(max(0.0, 1.0 - self.world_follow_easing), steps)

        current = self.world_root.getPos()
        desired = Vec3(target_local_x, target_local_y, 0.0)
        self.world_root.setPos(current + (desired - current) * blend)

    def _display_day(self) -> int:
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
        leader_name = ""
        if self.sim.players:
            leader = max(
                self.sim.players,
                key=lambda player: (player.progress_score(self.sim.start_row), player.alive, player.username),
            )
            leader_progress = leader.progress_score(self.sim.start_row)
            leader_name = str(getattr(leader, "username", "") or "")

        record = self.sim.statistics.get_game_highscore("crossy_followers") or {}
        record_score = int(record.get("score", 0) or 0)
        record_name = str(record.get("username", "") or "")

        stats_lines = [
            f"Alive: {alive_count}",
            f"Leader: {leader_progress} rows",
            f"Time: {self.sim.game_time:.1f}s",
        ]
        if record_score > 0:
            record_line = f"Highscore: {record_score} rows"
            if record_name:
                short_name = record_name if len(record_name) <= 12 else record_name[:12] + "..."
                record_line = f"{record_line} - {short_name}"
            stats_lines.append(record_line)
        self.stats_text.setText("\n".join(stats_lines))

        self.day_counter.setText(f"Day {self._display_day()}: {len(self.sim.players)} {self.PLAYER_LABEL}")

        eliminations = list(self.sim.recent_eliminations[:6])
        if eliminations:
            self.elim_text.setText("Eliminated:\n" + "\n".join(eliminations))
        else:
            self.elim_text.setText("")

        if self.sim.game_over and self.sim.winner is not None:
            self.status_text.setText(f"Winner: {self.sim.winner.username}")
        elif leader_name:
            self.status_text.setText(f"Front-runner: {leader_name}")
        else:
            self.status_text.setText("")

    def _show_end_card(self):
        if self.end_card is not None:
            return
        sorted_players = sorted(
            self.sim.players,
            key=lambda player: (player.placement if player.placement is not None else 10**9, player.username),
        )
        record = self.sim.statistics.get_game_highscore("crossy_followers") or {}
        record_score = int(record.get("score", 0) or 0)
        record_name = str(record.get("username", "") or "")

        lines = ["GAME COMPLETE", ""]
        if self.sim.winner is not None:
            winner_progress = self.sim.winner.progress_score(self.sim.start_row)
            lines.append(f"Winner: {self.sim.winner.username} ({winner_progress} rows)")
        if record_score > 0:
            record_line = f"Highscore: {record_score} rows"
            if record_name:
                record_line = f"{record_line} - {record_name}"
            lines.append(record_line)
        lines.append("")
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

        for ui in (self.title, self.subtitle, self.prompt, self.day_counter, self.stats_text, self.elim_text, self.status_text, self.end_card):
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
