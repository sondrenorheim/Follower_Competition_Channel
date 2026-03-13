import random
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from panda3d.core import Filename, Material, TextureStage


@dataclass
class TrackSegment:
    node: object
    length: float
    road_node: object = None
    tex_offset: float = 0.0


class SubwayTrack3D:
    def __init__(
        self,
        render,
        loader,
        width: float,
        segment_length: float,
        segment_count: int,
        lane_count: int,
        lane_padding: float,
        floor_color: tuple,
        lane_line_color: tuple,
        config=None,
    ):
        config = config or SimpleNamespace()
        self.render = render
        self.loader = loader
        self.width = width
        self.segment_length = segment_length
        self.segment_count = max(2, segment_count)
        self.lane_count = max(1, lane_count)
        self.lane_padding = lane_padding
        self.road_thickness = float(getattr(config, "SUBWAY_3D_ROAD_THICKNESS", 0.15))
        self.road_color = getattr(config, "SUBWAY_3D_ROAD_COLOR", floor_color)
        self.edge_line_color = getattr(config, "SUBWAY_3D_EDGE_LINE_COLOR", (0.95, 0.95, 0.95))
        self.dash_color = getattr(config, "SUBWAY_3D_LANE_DASH_COLOR", lane_line_color)
        self.dash_length = float(getattr(config, "SUBWAY_3D_LANE_DASH_LENGTH", 2.2))
        self.dash_gap = float(getattr(config, "SUBWAY_3D_LANE_DASH_GAP", 1.4))
        self.dash_width = float(getattr(config, "SUBWAY_3D_LANE_DASH_WIDTH", 0.18))
        self.dash_thickness = float(getattr(config, "SUBWAY_3D_LANE_DASH_THICKNESS", 0.03))
        self.curb_width = float(getattr(config, "SUBWAY_3D_CURB_WIDTH", 0.5))
        self.curb_height = float(getattr(config, "SUBWAY_3D_CURB_HEIGHT", 0.18))
        self.curb_color = getattr(config, "SUBWAY_3D_CURB_COLOR", (0.82, 0.82, 0.86))
        self.sand_width = float(getattr(config, "SUBWAY_3D_SAND_WIDTH", 4.0))
        self.sand_height = float(getattr(config, "SUBWAY_3D_SAND_HEIGHT", 0.08))
        self.sand_color = getattr(config, "SUBWAY_3D_SAND_COLOR", (0.78, 0.64, 0.4))
        self.palm_trunk_color = getattr(config, "SUBWAY_3D_PALM_TRUNK_COLOR", (0.6, 0.38, 0.2))
        self.palm_leaf_color = getattr(config, "SUBWAY_3D_PALM_LEAF_COLOR", (0.28, 0.78, 0.28))
        self.palm_height = float(getattr(config, "SUBWAY_3D_PALM_HEIGHT", 2.8))
        self.palm_leaf_size = float(getattr(config, "SUBWAY_3D_PALM_LEAF_SIZE", 1.3))
        self.palm_per_segment = int(getattr(config, "SUBWAY_3D_PALM_PER_SEGMENT", 1))
        self.road_texture_path = getattr(config, "SUBWAY_3D_ROAD_TEXTURE", "")
        self.road_texture_scale = getattr(config, "SUBWAY_3D_ROAD_TEXTURE_SCALE", 1.0)
        self.road_specular = getattr(config, "SUBWAY_3D_ROAD_SPECULAR", (0.25, 0.25, 0.25))
        self.road_shininess = float(getattr(config, "SUBWAY_3D_ROAD_SHININESS", 32.0))
        self.road_overlap = float(getattr(config, "SUBWAY_3D_ROAD_OVERLAP", 0.35))
        self.root_dir = Path(__file__).resolve().parents[1]
        self.road_tex_scale_u, self.road_tex_scale_v = self._resolve_tex_scale(self.road_texture_scale)

        usable_width = max(0.1, self.width - self.lane_padding * 2)
        self.lane_width = usable_width / self.lane_count
        self.lane_centers = [
            -self.width * 0.5 + self.lane_padding + self.lane_width * (idx + 0.5)
            for idx in range(self.lane_count)
        ]

        self.root = self.render.attachNewNode("track_root")
        self.segments = []
        self.base_model = self.loader.loadModel("models/box")
        self.base_model.clearTexture()
        self.road_texture = self._load_texture(self.road_texture_path)
        self.road_material = self._build_road_material()
        self._build_segments()

    def _build_segments(self):
        for idx in range(self.segment_count):
            seg_root = self.root.attachNewNode(f"segment_{idx}")
            seg_root.setPos(0, idx * self.segment_length, 0)

            road = self._copy_box(seg_root, allow_texture=True)
            road_length = self.segment_length + self.road_overlap
            road.setScale(self.width * 0.5, road_length * 0.5, self.road_thickness)
            road.setPos(0, 0, -self.road_thickness)
            road.setColor(*self.road_color)
            road.setTransparency(False)
            tex_offset = 0.0
            if self.road_texture:
                road.setTexture(self.road_texture, 1)
                self._apply_tex_scale(road, (self.road_tex_scale_u, self.road_tex_scale_v))
                tex_offset = idx * self.road_tex_scale_v
                road.setTexOffset(TextureStage.getDefault(), 0.0, tex_offset)
            if self.road_material:
                road.setMaterial(self.road_material, 1)

            self._build_edge_lines(seg_root)
            self._build_lane_dashes(seg_root)
            self._build_curbs(seg_root)
            self._build_sand(seg_root)
            self._build_palms(seg_root)

            self.segments.append(
                TrackSegment(
                    node=seg_root,
                    length=self.segment_length,
                    road_node=road,
                    tex_offset=tex_offset,
                )
            )

    def _copy_box(self, parent, allow_texture: bool = False):
        node = self.base_model.copyTo(parent)
        node.clearTexture()
        if not allow_texture:
            node.setTextureOff(1)
        return node

    def _build_edge_lines(self, parent):
        edge_width = max(0.04, self.dash_width * 0.6)
        edge_height = self.dash_thickness * 0.5
        for side in (-1, 1):
            edge = self._copy_box(parent)
            edge.setScale(edge_width * 0.5, self.segment_length * 0.5, edge_height)
            edge.setPos(side * (self.width * 0.5 - edge_width * 0.5), 0, edge_height)
            edge.setColor(*self.edge_line_color)

    def _build_lane_dashes(self, parent):
        if self.lane_count <= 1:
            return
        dash_count = max(1, int(self.segment_length / max(self.dash_length + self.dash_gap, 0.1)))
        start_y = -self.segment_length * 0.5 + self.dash_length * 0.5
        for dash_idx in range(dash_count):
            dash_y = start_y + dash_idx * (self.dash_length + self.dash_gap)
            for idx in range(1, self.lane_count):
                x_pos = -self.width * 0.5 + self.lane_padding + self.lane_width * idx
                dash = self._copy_box(parent)
                dash.setScale(self.dash_width * 0.5, self.dash_length * 0.5, self.dash_thickness * 0.5)
                dash.setPos(x_pos, dash_y, self.dash_thickness)
                dash.setColor(*self.dash_color)

    def _build_curbs(self, parent):
        if self.curb_width <= 0:
            return
        curb_z = -self.road_thickness + self.curb_height * 0.5
        for side in (-1, 1):
            curb = self._copy_box(parent)
            curb.setScale(self.curb_width * 0.5, self.segment_length * 0.5, self.curb_height * 0.5)
            curb.setPos(side * (self.width * 0.5 + self.curb_width * 0.5), 0, curb_z)
            curb.setColor(*self.curb_color)

    def _build_sand(self, parent):
        if self.sand_width <= 0:
            return
        sand_z = -self.road_thickness - self.sand_height * 0.5
        for side in (-1, 1):
            sand = self._copy_box(parent)
            sand.setScale(self.sand_width * 0.5, self.segment_length * 0.5, self.sand_height * 0.5)
            sand.setPos(side * (self.width * 0.5 + self.curb_width + self.sand_width * 0.5), 0, sand_z)
            sand.setColor(*self.sand_color)

    def _build_palms(self, parent):
        if self.palm_per_segment <= 0:
            return
        for side in (-1, 1):
            for _ in range(self.palm_per_segment):
                y_offset = 0.0
                if self.sand_width > 0:
                    x_offset = side * (self.width * 0.5 + self.curb_width + self.sand_width * 0.5)
                else:
                    x_offset = side * (self.width * 0.5 + self.curb_width * 0.6)
                self._build_palm_tree(parent, x_offset, y_offset)

    def _build_palm_tree(self, parent, x_pos, y_pos):
        tree_root = parent.attachNewNode("palm_tree")
        tree_root.setPos(x_pos, y_pos, -self.road_thickness)

        trunk = self._copy_box(tree_root)
        trunk_height = self.palm_height * random.uniform(0.85, 1.1)
        self._place_box_centered_on_base(trunk, 0.12, 0.12, trunk_height, 0.0)
        trunk.setColor(*self.palm_trunk_color)

        leaf_size = self.palm_leaf_size * random.uniform(0.85, 1.1)
        leaf_z = trunk_height
        for idx in range(4):
            leaf = self._copy_box(tree_root)
            leaf_thickness = 0.06
            self._place_box_centered_on_base(leaf, leaf_size, leaf_size * 0.2, leaf_thickness, leaf_z - leaf_thickness * 0.5)
            leaf.setPos(leaf.getX(), leaf.getY() + leaf_size * 0.35, leaf.getZ())
            leaf.setHpr(idx * 90, -35, 0)
            leaf.setColor(*self.palm_leaf_color)

    @staticmethod
    def _place_box_centered_on_base(node, size_x: float, size_y: float, size_z: float, base_z: float):
        node.setScale(size_x, size_y, size_z)
        node.setPos(-size_x * 0.5, -size_y * 0.5, base_z)

    def _build_road_material(self):
        spec = self._normalize_color(self.road_specular)
        material = Material()
        material.setSpecular((spec[0], spec[1], spec[2], 1.0))
        material.setShininess(self.road_shininess)
        return material

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
    def _apply_tex_scale(node, scale):
        if isinstance(scale, (list, tuple)) and len(scale) >= 2:
            u_scale, v_scale = float(scale[0]), float(scale[1])
        else:
            u_scale = v_scale = float(scale)
        node.setTexScale(TextureStage.getDefault(), u_scale, v_scale)

    @staticmethod
    def _resolve_tex_scale(scale):
        if isinstance(scale, (list, tuple)) and len(scale) >= 2:
            return float(scale[0]), float(scale[1])
        value = float(scale) if scale else 1.0
        return value, value

    @staticmethod
    def _normalize_color(color):
        if max(color) > 1.0:
            return (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
        return color

    def lane_center(self, lane_index: int) -> float:
        lane_index = int(round(lane_index))
        lane_index = max(0, min(self.lane_count - 1, lane_index))
        return self.lane_centers[lane_index]

    def update(self, dt: float, speed: float, recycle_y: float = -5.0):
        if not self.segments:
            return
        max_y = max(seg.node.getY() for seg in self.segments)
        for seg in self.segments:
            seg.node.setY(seg.node.getY() - speed * dt)
            if seg.node.getY() + (seg.length * 0.5) < recycle_y:
                seg.node.setY(max_y + seg.length)
                max_y = seg.node.getY()
                if self.road_texture and seg.road_node is not None:
                    seg.tex_offset += self.segment_count * self.road_tex_scale_v
                    seg.road_node.setTexOffset(TextureStage.getDefault(), 0.0, seg.tex_offset)
