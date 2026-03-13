import random
from pathlib import Path

from panda3d.core import (
    CardMaker,
    Filename,
    PNMImage,
    Texture,
    TextureStage,
    TransparencyAttrib,
)


class SubwayScenery3D:
    def __init__(self, render, track, config):
        self.render = render
        self.track = track
        self.loader = track.loader
        self.config = config
        self.root = self.render.attachNewNode("subway_scenery")
        self.root_dir = Path(__file__).resolve().parents[1]
        self.cloud_offset = 0.0
        self.cloud_stage = None
        self.cloud_node = None
        self.cloud_speed = float(getattr(self.config, "SUBWAY_3D_CLOUD_SPEED", 0.004))
        self.city_layers = []

        self._build_sky()
        self._build_city()

    def update(self, dt: float, speed: float):
        if self.cloud_node and self.cloud_stage:
            self.cloud_offset = (self.cloud_offset + dt * self.cloud_speed) % 1.0
            self.cloud_node.setTexOffset(self.cloud_stage, self.cloud_offset, 0)

        for layer in self.city_layers:
            layer["offset"] = (layer["offset"] + dt * speed * layer["parallax"]) % 1.0
            layer["node"].setTexOffset(layer["stage"], layer["offset"], 0)

    def _build_sky(self):
        top_color = getattr(self.config, "SUBWAY_3D_SKY_TOP_COLOR", (0.32, 0.63, 0.92))
        bottom_color = getattr(self.config, "SUBWAY_3D_SKY_BOTTOM_COLOR", (0.72, 0.86, 0.98))
        width = float(getattr(self.config, "SUBWAY_3D_BACKDROP_WIDTH", 120.0))
        height = float(getattr(self.config, "SUBWAY_3D_BACKDROP_HEIGHT", 70.0))
        y_pos = float(getattr(self.config, "SUBWAY_3D_BACKDROP_Y", 160.0))

        texture = self._gradient_texture(top_color, bottom_color, 512, 512)
        card = CardMaker("sky_card")
        card.setFrame(-1, 1, 0, 1)
        node = self.root.attachNewNode(card.generate())
        node.setPos(0, y_pos, -8)
        node.setScale(width * 0.5, 1, height)
        node.setTexture(texture, 1)
        node.setDepthWrite(False)
        node.setDepthTest(False)
        node.setBin("background", 0)

        cloud_texture = self._load_texture(getattr(self.config, "SUBWAY_3D_CLOUD_TEXTURE", ""))
        if cloud_texture:
            cloud_card = CardMaker("clouds_card")
            cloud_card.setFrame(-1, 1, 0, 1)
            cloud_node = self.root.attachNewNode(cloud_card.generate())
            cloud_node.setPos(0, y_pos, -6)
            cloud_node.setScale(width * 0.5, 1, height)
            cloud_node.setTransparency(TransparencyAttrib.MAlpha)
            cloud_node.setColor(1, 1, 1, 0.9)
            cloud_stage = TextureStage("clouds")
            cloud_node.setTexture(cloud_stage, cloud_texture)
            cloud_node.setTexScale(cloud_stage, 2.4, 1.2)
            cloud_node.setDepthWrite(False)
            cloud_node.setDepthTest(False)
            cloud_node.setBin("background", 1)
            self.cloud_node = cloud_node
            self.cloud_stage = cloud_stage

    def _build_city(self):
        base_color = getattr(self.config, "SUBWAY_3D_CITY_COLOR", (0.5, 0.7, 0.95))
        accent_color = getattr(self.config, "SUBWAY_3D_CITY_ACCENT", (0.4, 0.6, 0.85))
        near_base = getattr(self.config, "SUBWAY_3D_CITY_NEAR_COLOR", (0.45, 0.66, 0.92))
        near_accent = getattr(self.config, "SUBWAY_3D_CITY_NEAR_ACCENT", (0.35, 0.55, 0.82))
        far_parallax = float(getattr(self.config, "SUBWAY_3D_CITY_PARALLAX_FAR", 0.008))
        near_parallax = float(getattr(self.config, "SUBWAY_3D_CITY_PARALLAX_NEAR", 0.014))

        width = float(getattr(self.config, "SUBWAY_3D_BACKDROP_WIDTH", 120.0))
        height = float(getattr(self.config, "SUBWAY_3D_BACKDROP_HEIGHT", 70.0))
        y_pos = float(getattr(self.config, "SUBWAY_3D_BACKDROP_Y", 160.0)) - 6.0

        self._add_city_layer(
            name="city_far",
            base_color=base_color,
            accent_color=accent_color,
            width=width,
            height=height * 0.5,
            y_pos=y_pos,
            z_pos=-5.5,
            parallax=far_parallax,
            bin_index=2,
            alpha=0.75,
        )
        self._add_city_layer(
            name="city_near",
            base_color=near_base,
            accent_color=near_accent,
            width=width * 1.02,
            height=height * 0.62,
            y_pos=y_pos - 4.0,
            z_pos=-3.5,
            parallax=near_parallax,
            bin_index=3,
            alpha=0.88,
        )

    def _add_city_layer(
        self,
        name: str,
        base_color,
        accent_color,
        width: float,
        height: float,
        y_pos: float,
        z_pos: float,
        parallax: float,
        bin_index: int,
        alpha: float = 1.0,
    ):
        texture = self._city_texture(base_color, accent_color, 512, 256)
        card = CardMaker(name)
        card.setFrame(-1, 1, 0, 1)
        node = self.root.attachNewNode(card.generate())
        node.setPos(0, y_pos, z_pos)
        node.setScale(width * 0.5, 1, height)

        stage = TextureStage(f"{name}_stage")
        node.setTexture(stage, texture)
        node.setTexScale(stage, 1.8, 1.0)
        if alpha < 1.0:
            node.setTransparency(TransparencyAttrib.MAlpha)
            node.setColor(1, 1, 1, alpha)
        node.setDepthWrite(False)
        node.setDepthTest(False)
        node.setBin("background", bin_index)

        self.city_layers.append({
            "node": node,
            "stage": stage,
            "parallax": parallax,
            "offset": 0.0,
        })

    @staticmethod
    def _gradient_texture(top_color, bottom_color, width, height):
        image = PNMImage(width, height)
        for y in range(height):
            t = y / max(1, height - 1)
            r = bottom_color[0] + (top_color[0] - bottom_color[0]) * t
            g = bottom_color[1] + (top_color[1] - bottom_color[1]) * t
            b = bottom_color[2] + (top_color[2] - bottom_color[2]) * t
            for x in range(width):
                image.setXel(x, y, r, g, b)

        texture = Texture()
        texture.load(image)
        texture.setWrapU(Texture.WM_clamp)
        texture.setWrapV(Texture.WM_clamp)
        return texture

    @staticmethod
    def _city_texture(base_color, accent_color, width, height):
        image = PNMImage(width, height)
        for y in range(height):
            t = y / max(1, height - 1)
            shade = 0.75 + 0.25 * t
            r = max(0.0, min(1.0, base_color[0] * shade))
            g = max(0.0, min(1.0, base_color[1] * shade))
            b = max(0.0, min(1.0, base_color[2] * shade))
            for x in range(width):
                image.setXel(x, y, r, g, b)

        rng = random.Random(42)
        x = 0
        while x < width:
            building_w = rng.randint(18, 60)
            building_h = rng.randint(int(height * 0.35), int(height * 0.85))
            color_variation = rng.uniform(-0.05, 0.05)
            r = max(0.0, min(1.0, accent_color[0] + color_variation))
            g = max(0.0, min(1.0, accent_color[1] + color_variation))
            b = max(0.0, min(1.0, accent_color[2] + color_variation))
            for xi in range(x, min(width, x + building_w)):
                for yi in range(building_h):
                    image.setXel(xi, yi, r, g, b)
            x += building_w + rng.randint(8, 18)

        # Sprinkle subtle window lights.
        window_count = int(width * height * 0.003)
        for _ in range(window_count):
            wx = rng.randint(0, width - 1)
            wy = rng.randint(0, height - 1)
            if wy < int(height * 0.15):
                continue
            window_r = min(1.0, accent_color[0] + 0.2)
            window_g = min(1.0, accent_color[1] + 0.2)
            window_b = min(1.0, accent_color[2] + 0.2)
            image.setXel(wx, wy, window_r, window_g, window_b)

        texture = Texture()
        texture.load(image)
        texture.setWrapU(Texture.WM_clamp)
        texture.setWrapV(Texture.WM_clamp)
        return texture

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
