import random
from pathlib import Path

from panda3d.core import Filename

from .obstacle import SubwayObstacle3D


class SubwayObstacleSpawner3D:
    def __init__(self, render, loader, track, config):
        self.render = render
        self.loader = loader
        self.track = track
        self.config = config
        self.spawn_timer = 0.0

        self.base_model = self.loader.loadModel("models/box")
        self.base_model.clearTexture()
        self.root_dir = Path(__file__).resolve().parents[1]
        self.model_templates = self._load_models()
        self.textures = self._load_textures()
        self.tint_models = bool(getattr(self.config, "SUBWAY_3D_TINT_MODELS", False))

    def update(self, dt: float, difficulty: float, obstacles: list):
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return

        interval = random.uniform(
            float(getattr(self.config, "SUBWAY_SPAWN_INTERVAL_MIN", 0.45)),
            float(getattr(self.config, "SUBWAY_SPAWN_INTERVAL_MAX", 0.9)),
        )
        interval *= 1.0 - 0.35 * difficulty
        self.spawn_timer = max(0.2, interval)

        obstacle = self._spawn_obstacle(obstacles)
        if obstacle:
            obstacles.append(obstacle)

    def _spawn_obstacle(self, obstacles: list):
        lane_count = self.track.lane_count
        lane_width = self.track.lane_width
        lane_gap = float(getattr(self.config, "SUBWAY_3D_LANE_GAP", 0.15))
        spawn_y = float(getattr(self.config, "SUBWAY_3D_SPAWN_Y", 80.0))

        kinds = ["train", "barrier", "pole", "tunnel_wall"]
        weights = [0.35, 0.3, 0.2, 0.15]
        kind = random.choices(kinds, weights=weights, k=1)[0]

        lane_span = 1
        if kind == "train" and random.random() < float(getattr(self.config, "SUBWAY_TRAIN_DOUBLE_CHANCE", 0.25)):
            lane_span = 2

        max_lane = max(0, lane_count - lane_span)
        lane_index = random.randint(0, max_lane)

        if not self._is_spawn_clear(lane_index, lane_span, obstacles):
            return None

        width = max(0.3, lane_width * lane_span - lane_gap)
        length = max(0.6, lane_width * 0.9)
        height = self._obstacle_height(kind, lane_width)

        if lane_span <= 1:
            x = self.track.lane_center(lane_index)
        else:
            left_center = self.track.lane_center(lane_index)
            right_center = self.track.lane_center(lane_index + lane_span - 1)
            x = (left_center + right_center) * 0.5

        template = self.model_templates.get(kind, self.base_model)
        node = template.copyTo(self.render)
        node.clearTexture()
        node.setPos(x, spawn_y, height * 0.5)
        color, required = self._obstacle_style(kind)
        texture = self.textures.get(kind)

        if template is self.base_model:
            node.setScale(width * 0.5, length * 0.5, height * 0.5)
            if texture:
                node.setTexture(texture, 1)
                node.setColor(1, 1, 1, 1)
            else:
                node.clearTexture()
                node.setTextureOff(1)
                node.setColor(*color)
        else:
            self._scale_model(node, width, length, height)
            if texture:
                node.setTexture(texture, 1)
                node.setColor(1, 1, 1, 1)
            else:
                node.clearTexture()
                node.setTextureOff(1)
                if self.tint_models:
                    node.setColor(*color)

        return SubwayObstacle3D(
            node=node,
            kind=kind,
            lane_index=lane_index,
            lane_span=lane_span,
            width=width,
            length=length,
            height=height,
            required_action=required,
            speed_multiplier=1.0 + random.uniform(-0.05, 0.15),
        )

    def _obstacle_height(self, kind: str, lane_width: float) -> float:
        if kind == "train":
            return float(getattr(self.config, "SUBWAY_3D_TRAIN_HEIGHT", lane_width * 2.2))
        if kind == "pole":
            return float(getattr(self.config, "SUBWAY_3D_POLE_HEIGHT", lane_width * 0.9))
        if kind == "tunnel_wall":
            return float(getattr(self.config, "SUBWAY_3D_WALL_HEIGHT", lane_width * 1.1))
        return float(getattr(self.config, "SUBWAY_3D_BARRIER_HEIGHT", lane_width * 0.6))

    def _obstacle_style(self, kind: str):
        def normalize(color):
            if max(color) > 1.0:
                return (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
            return color

        if kind == "train":
            color = normalize(
                getattr(
                    self.config,
                    "SUBWAY_3D_TRAIN_COLOR",
                    getattr(self.config, "SUBWAY_TRAIN_COLOR", (0.7, 0.25, 0.25)),
                )
            )
            return (color[0], color[1], color[2], 1.0), "lane"
        if kind == "pole":
            color = normalize(
                getattr(
                    self.config,
                    "SUBWAY_3D_POLE_COLOR",
                    getattr(self.config, "SUBWAY_POLE_COLOR", (0.4, 0.55, 0.8)),
                )
            )
            return (color[0], color[1], color[2], 1.0), "lane"
        if kind == "tunnel_wall":
            color = normalize(
                getattr(
                    self.config,
                    "SUBWAY_3D_WALL_COLOR",
                    getattr(self.config, "SUBWAY_WALL_COLOR", (0.35, 0.35, 0.45)),
                )
            )
            return (color[0], color[1], color[2], 1.0), "roll"
        color = normalize(
            getattr(
                self.config,
                "SUBWAY_3D_BARRIER_COLOR",
                getattr(self.config, "SUBWAY_BARRIER_COLOR", (0.8, 0.5, 0.2)),
            )
        )
        return (color[0], color[1], color[2], 1.0), "jump"

    def _is_spawn_clear(self, lane_index: int, lane_span: int, obstacles: list) -> bool:
        gap_min = float(getattr(self.config, "SUBWAY_3D_OBSTACLE_GAP_MIN", 12.0))
        for obstacle in obstacles:
            if not self._lanes_overlap(lane_index, lane_span, obstacle.lane_index, obstacle.lane_span):
                continue
            if obstacle.y() > (float(getattr(self.config, "SUBWAY_3D_SPAWN_Y", 80.0)) - gap_min):
                return False
        return True

    def _load_models(self):
        model_paths = {
            "train": getattr(
                self.config,
                "SUBWAY_3D_MODEL_TRAIN",
                "assets/subway_followers_3d/models/train.bam",
            ),
            "barrier": getattr(
                self.config,
                "SUBWAY_3D_MODEL_BARRIER",
                "assets/subway_followers_3d/models/barrier.bam",
            ),
            "tunnel_wall": getattr(
                self.config,
                "SUBWAY_3D_MODEL_TUNNEL",
                "assets/subway_followers_3d/models/tunnel.bam",
            ),
        }

        templates = {}
        for kind, model_path in model_paths.items():
            model = self._load_model(model_path)
            if model is None:
                continue
            model.clearTexture()
            model.setTextureOff(1)
            self._center_model(model)
            templates[kind] = model
        return templates

    def _load_textures(self):
        texture_paths = {
            "train": getattr(
                self.config,
                "SUBWAY_3D_TEXTURE_TRAIN",
                "assets/subway_followers_3d/textures/train.png",
            ),
            "barrier": getattr(
                self.config,
                "SUBWAY_3D_TEXTURE_BARRIER",
                "assets/subway_followers_3d/textures/barrier.png",
            ),
            "tunnel_wall": getattr(
                self.config,
                "SUBWAY_3D_TEXTURE_TUNNEL",
                "assets/subway_followers_3d/textures/tunnel.png",
            ),
        }

        textures = {}
        for kind, texture_path in texture_paths.items():
            texture = self._load_texture(texture_path)
            if texture is None:
                continue
            textures[kind] = texture
        return textures

    def _load_model(self, model_path: str):
        if not model_path:
            return None
        path = Path(model_path)
        if not path.is_absolute():
            path = self.root_dir / path
        if not path.exists():
            return None
        try:
            return self.loader.loadModel(Filename.fromOsSpecific(str(path)))
        except Exception:
            return None

    def _load_texture(self, texture_path: str):
        if not texture_path:
            return None
        path = Path(texture_path)
        if not path.is_absolute():
            path = self.root_dir / path
        if not path.exists():
            return None
        try:
            return self.loader.loadTexture(Filename.fromOsSpecific(str(path)))
        except Exception:
            return None

    @staticmethod
    def _center_model(model):
        bounds = model.getTightBounds()
        if not bounds or bounds[0] is None:
            return
        min_b, max_b = bounds
        center = (min_b + max_b) * 0.5
        model.setPos(-center)
        model.flattenStrong()

    @staticmethod
    def _scale_model(model, width: float, length: float, height: float):
        bounds = model.getTightBounds()
        if not bounds or bounds[0] is None:
            model.setScale(width * 0.5, length * 0.5, height * 0.5)
            return
        min_b, max_b = bounds
        size = max_b - min_b
        scale_x = width / size.x if size.x else 1.0
        scale_y = length / size.y if size.y else 1.0
        scale_z = height / size.z if size.z else 1.0
        model.setScale(scale_x, scale_y, scale_z)

    @staticmethod
    def _lanes_overlap(start_a: int, span_a: int, start_b: int, span_b: int) -> bool:
        end_a = start_a + max(1, span_a) - 1
        end_b = start_b + max(1, span_b) - 1
        return not (end_a < start_b or end_b < start_a)
