from __future__ import annotations

import base64
import math
import re
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .levels import normalize_smb_mode, scene_path_for_mode, world_label_for_mode


TILE_SIZE = 16


_EXT_RESOURCE_RE = re.compile(
    r'^\[ext_resource type="(?P<type>[^"]+)"(?:[^]]*?) path="(?P<path>[^"]+)"[^]]* id="(?P<id>[^"]+)"\]'
)
_NODE_START_RE = re.compile(r"^\[node ")
_VECTOR2_RE = re.compile(r"Vector2\(([-+]?[0-9]*\.?[0-9]+),\s*([-+]?[0-9]*\.?[0-9]+)\)")
_TILE_DATA_RE = re.compile(r'PackedByteArray\("([A-Za-z0-9+/=]+)"\)')
_WORLD_NAME_RE = re.compile(r"([1-8])[-_]([1-4])")


SCENE_TILE_BLOCKS: dict[int, tuple[str, str | None]] = {
    1: ("brick", None),         # BrickBlock
    2: ("coin_box", "coin"),    # QuestionBlock
    5: ("brick", "6coins"),     # CoinBrickBlock
    6: ("brick", "mushroom"),   # OneUpBrickBlock
    7: ("brick", "mushroom"),   # PowerUpBrickBlock
    8: ("coin_box", "mushroom"),  # PowerUpQuestionBlock
    9: ("coin_box", "coin"),    # InvisibleQuestionBlock
    10: ("brick", "star"),      # StarBrickBlock
    11: ("coin_box", "mushroom"),  # InvisibleOneUpQuestionBlock
    12: ("coin_box", "coin"),   # PoisonQuestionBlock (fallback behavior)
    13: ("brick", None),        # PoisonMushroomBrickBlock
    18: ("coin_box", "mushroom"),  # InvisiblePowerUpQuestionBlock
}

INVISIBLE_SCENE_BLOCK_TILES = {9, 11, 18}
NON_SOLID_SCENE_TILES = {3, 4}  # Coin + DeathPit
HAZARD_SCENE_TILES = {4}        # DeathPit

# Some levels place bumpable blocks as explicit scene nodes instead of tile IDs.
# Map known block scene paths to the synthetic tile IDs used by SCENE_TILE_BLOCKS.
SCENE_BLOCK_INSTANCE_TILE_IDS: tuple[tuple[str, int], ...] = (
    ("/brickblocks/brickblock.tscn", 1),
    ("/brickblocks/coinbrickblock.tscn", 5),
    ("/brickblocks/oneupbrickblock.tscn", 6),
    ("/brickblocks/powerupbrickblock.tscn", 7),
    ("/brickblocks/starbrickblock.tscn", 10),
    ("/brickblocks/poisonmushroombrickblock.tscn", 13),
    ("/questionblocks/questionblock.tscn", 2),
    ("/questionblocks/powerupquestionblock.tscn", 8),
    ("/questionblocks/poisonquestionblock.tscn", 12),
    ("/invisibleblocks/invisiblequestionblock.tscn", 9),
    ("/invisibleblocks/invisibleoneupquestionblock.tscn", 11),
    ("/invisibleblocks/invisiblepowerupquestionblock.tscn", 18),
)


@dataclass(frozen=True)
class TileCell:
    x: int
    y: int
    source_id: int
    atlas_x: int
    atlas_y: int
    tile_id: int
    layer: str


@dataclass(frozen=True)
class EnemySpawn:
    x: float
    y: float
    kind: str


@dataclass(frozen=True)
class MovingPlatformSpec:
    x: float
    y_min: float
    y_max: float
    start_y: float
    width: float
    height: float
    speed: float
    direction: float


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class ParsedSmbLevel:
    mode: str
    scene_path: str
    world_label: str
    theme: str
    subtitle: str
    start_x: float
    start_y: float
    finish_x: float
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    width: float
    height: float
    camera_right_limit: float | None
    render_tiles: tuple[TileCell, ...]
    solid_tiles: tuple[TileCell, ...]
    block_tiles: tuple[TileCell, ...]
    hazard_tiles: tuple[TileCell, ...]
    enemies: tuple[EnemySpawn, ...]
    moving_platforms: tuple[MovingPlatformSpec, ...]
    checkpoints: tuple[Point, ...]
    checkpoint_flags: tuple[Point, ...]


@dataclass
class _NodeEntry:
    name: str
    parent: str | None
    instance_id: str | None
    node_type: str | None
    properties: dict[str, str]


def load_level_for_mode(game_mode: str) -> ParsedSmbLevel:
    canonical = normalize_smb_mode(game_mode)
    if canonical is None:
        raise ValueError(f"Unsupported SMB mode: {game_mode}")
    scene_path = scene_path_for_mode(canonical)
    world_label = world_label_for_mode(canonical)
    return _load_scene_file(canonical, scene_path, world_label)


@lru_cache(maxsize=64)
def _load_scene_file(mode: str, scene_path: Path, world_label: str) -> ParsedSmbLevel:
    if not scene_path.exists():
        raise FileNotFoundError(f"SMB scene file not found: {scene_path}")

    text = scene_path.read_text(encoding="utf-8")
    ext_resources = _parse_ext_resources(text)
    nodes = _parse_nodes(text)
    root_node = nodes[0] if nodes else None

    theme = _resolve_theme(root_node, ext_resources)
    subtitle = _build_subtitle(world_label, theme)

    render_tiles: list[TileCell] = []
    solid_tiles: list[TileCell] = []
    block_tiles: list[TileCell] = []
    hazard_tiles: list[TileCell] = []
    enemies: list[EnemySpawn] = []
    moving_platforms: list[MovingPlatformSpec] = []
    checkpoints: list[Point] = []
    checkpoint_flags: list[Point] = []

    start_x, start_y = -208.0, 0.0
    finish_x: float | None = None
    camera_right_limit: float | None = None

    for node in nodes:
        instance_path = _resolve_instance_path(node, ext_resources)
        parent = node.parent or ""
        node_name_lc = node.name.lower()
        parent_lc = parent.lower()

        pos_x, pos_y = _parse_vector2(node.properties.get("position", ""))
        if pos_x is None:
            pos_x = 0.0
        if pos_y is None:
            pos_y = 0.0

        if node.name == "Player":
            start_x, start_y = float(pos_x), float(pos_y)
            continue

        if instance_path and "EndFlagpole.tscn" in instance_path:
            finish_x = float(pos_x)
            continue

        if node.name == "CameraRightLimit":
            camera_right_limit = float(pos_x)
            continue

        if instance_path:
            if "CheckpointFlag.tscn" in instance_path and "challenge" not in parent_lc:
                checkpoint_flags.append(Point(float(pos_x), float(pos_y)))
            elif "Checkpoint.tscn" in instance_path and "challenge" not in parent_lc:
                checkpoints.append(Point(float(pos_x), float(pos_y)))

            platform_spec = _parse_moving_platform(node, instance_path, float(pos_x), float(pos_y))
            if platform_spec is not None:
                moving_platforms.append(platform_spec)

            enemy_kind = _detect_enemy_kind(instance_path, parent_lc)
            if enemy_kind:
                enemies.append(EnemySpawn(float(pos_x), float(pos_y), enemy_kind))

            block_cell = _parse_block_cell_from_instance(
                instance_path=instance_path,
                parent_lc=parent_lc,
                node_name_lc=node_name_lc,
                x=float(pos_x),
                y=float(pos_y),
                layer=node.name,
            )
            if block_cell is not None:
                block_tiles.append(block_cell)

        tile_cells = _parse_tile_cells_for_node(node)
        if not tile_cells:
            continue
        if _exclude_tile_layer(parent_lc, node_name_lc):
            continue

        render_tiles.extend(tile_cells)
        for cell in tile_cells:
            if _is_solid_tile(cell):
                solid_tiles.append(cell)
            if (
                cell.source_id == 1
                and cell.tile_id in SCENE_TILE_BLOCKS
                and cell.tile_id not in INVISIBLE_SCENE_BLOCK_TILES
            ):
                block_tiles.append(cell)
            if cell.source_id == 1 and cell.tile_id in HAZARD_SCENE_TILES:
                hazard_tiles.append(cell)

    if finish_x is None:
        if camera_right_limit is not None:
            finish_x = camera_right_limit - float(TILE_SIZE)
        elif render_tiles:
            finish_x = max(cell.x for cell in render_tiles) + float(TILE_SIZE)
        else:
            finish_x = start_x + 1600.0

    all_x = [start_x, finish_x]
    all_y = [start_y]
    all_x.extend(float(cell.x) for cell in render_tiles)
    all_y.extend(float(cell.y) for cell in render_tiles)
    all_x.extend(float(enemy.x) for enemy in enemies)
    all_y.extend(float(enemy.y) for enemy in enemies)
    all_x.extend(float(p.x) for p in checkpoints)
    all_y.extend(float(p.y) for p in checkpoints)
    all_x.extend(float(p.x) for p in checkpoint_flags)
    all_y.extend(float(p.y) for p in checkpoint_flags)
    all_x.extend(float(p.x) for p in moving_platforms)
    all_y.extend(float(p.start_y) for p in moving_platforms)
    all_y.extend(float(p.y_min) for p in moving_platforms)
    all_y.extend(float(p.y_max) for p in moving_platforms)
    if camera_right_limit is not None:
        all_x.append(float(camera_right_limit))

    min_x = min(all_x) if all_x else 0.0
    max_x = max(all_x) if all_x else 0.0
    min_y = min(all_y) if all_y else 0.0
    max_y = max(all_y) if all_y else 0.0

    shift_x = -min_x if min_x < 0 else 0.0
    shift_y = -min_y if min_y < 0 else 0.0

    def shift_point(point: Point) -> Point:
        return Point(point.x + shift_x, point.y + shift_y)

    render_tiles = [_shift_tile(cell, shift_x, shift_y) for cell in render_tiles]
    solid_tiles = [_shift_tile(cell, shift_x, shift_y) for cell in solid_tiles]
    block_tiles = [_shift_tile(cell, shift_x, shift_y) for cell in block_tiles]
    hazard_tiles = [_shift_tile(cell, shift_x, shift_y) for cell in hazard_tiles]
    enemies = [EnemySpawn(enemy.x + shift_x, enemy.y + shift_y, enemy.kind) for enemy in enemies]
    checkpoints = [shift_point(point) for point in checkpoints]
    checkpoint_flags = [shift_point(point) for point in checkpoint_flags]
    moving_platforms = [
        MovingPlatformSpec(
            x=platform.x + shift_x,
            y_min=platform.y_min + shift_y,
            y_max=platform.y_max + shift_y,
            start_y=platform.start_y + shift_y,
            width=platform.width,
            height=platform.height,
            speed=platform.speed,
            direction=platform.direction,
        )
        for platform in moving_platforms
    ]

    start_x += shift_x
    start_y += shift_y
    finish_x += shift_x
    if camera_right_limit is not None:
        camera_right_limit += shift_x

    width = max(float(TILE_SIZE), (max_x - min_x) + float(TILE_SIZE))
    height = max(float(TILE_SIZE), (max_y - min_y) + float(TILE_SIZE))

    if camera_right_limit is not None:
        width = max(width, camera_right_limit + float(TILE_SIZE))
    width = max(width, finish_x + float(TILE_SIZE))

    checkpoints.sort(key=lambda point: point.x)
    checkpoint_flags.sort(key=lambda point: point.x)
    enemies.sort(key=lambda enemy: enemy.x)
    moving_platforms.sort(key=lambda platform: platform.x)

    return ParsedSmbLevel(
        mode=mode,
        scene_path=str(scene_path),
        world_label=world_label,
        theme=theme,
        subtitle=subtitle,
        start_x=float(start_x),
        start_y=float(start_y),
        finish_x=float(finish_x),
        min_x=0.0,
        max_x=float(width),
        min_y=0.0,
        max_y=float(height),
        width=float(width),
        height=float(height),
        camera_right_limit=float(camera_right_limit) if camera_right_limit is not None else None,
        render_tiles=tuple(render_tiles),
        solid_tiles=tuple(solid_tiles),
        block_tiles=tuple(block_tiles),
        hazard_tiles=tuple(hazard_tiles),
        enemies=tuple(enemies),
        moving_platforms=tuple(moving_platforms),
        checkpoints=tuple(checkpoints),
        checkpoint_flags=tuple(checkpoint_flags),
    )


def _shift_tile(cell: TileCell, shift_x: float, shift_y: float) -> TileCell:
    return TileCell(
        x=int(round(cell.x + shift_x)),
        y=int(round(cell.y + shift_y)),
        source_id=cell.source_id,
        atlas_x=cell.atlas_x,
        atlas_y=cell.atlas_y,
        tile_id=cell.tile_id,
        layer=cell.layer,
    )


def _parse_ext_resources(text: str) -> dict[str, tuple[str, str]]:
    resources: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        match = _EXT_RESOURCE_RE.match(line.strip())
        if not match:
            continue
        resources[match.group("id")] = (match.group("type"), match.group("path"))
    return resources


def _parse_nodes(text: str) -> list[_NodeEntry]:
    nodes: list[_NodeEntry] = []
    current: _NodeEntry | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if _NODE_START_RE.match(stripped):
            if current is not None:
                nodes.append(current)
            current = _NodeEntry(
                name=_extract_attr(stripped, "name") or "",
                parent=_extract_attr(stripped, "parent"),
                instance_id=_extract_ext_resource_id(stripped, "instance"),
                node_type=_extract_attr(stripped, "type"),
                properties={},
            )
            continue
        if current is None:
            continue
        if stripped.startswith("["):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        current.properties[key.strip()] = value.strip()

    if current is not None:
        nodes.append(current)
    return nodes


def _extract_attr(line: str, attr: str) -> str | None:
    match = re.search(rf'{re.escape(attr)}="([^"]+)"', line)
    return match.group(1) if match else None


def _extract_ext_resource_id(line: str, attr: str) -> str | None:
    match = re.search(rf'{re.escape(attr)}=ExtResource\("([^"]+)"\)', line)
    return match.group(1) if match else None


def _resolve_instance_path(node: _NodeEntry, resources: dict[str, tuple[str, str]]) -> str | None:
    if not node.instance_id:
        return None
    entry = resources.get(node.instance_id)
    if entry is None:
        return None
    _, path = entry
    return path


def _parse_vector2(raw_value: str) -> tuple[float | None, float | None]:
    if not raw_value:
        return None, None
    match = _VECTOR2_RE.search(raw_value)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _resolve_theme(root_node: _NodeEntry | None, resources: dict[str, tuple[str, str]]) -> str:
    if root_node is not None:
        explicit = root_node.properties.get("theme")
        if explicit:
            return explicit.strip().strip('"')
        music_ref = _extract_ext_resource_id(f'music={root_node.properties.get("music", "")}', "music")
        if music_ref and music_ref in resources:
            _, music_path = resources[music_ref]
            for token in ("Underground", "Overworld", "Castle", "Underwater"):
                if token.lower() in music_path.lower():
                    return token
    return "Overworld"


def _build_subtitle(world_label: str, theme: str) -> str:
    suffix_map = {
        "Underground": "Underground Run",
        "Overworld": "Overworld Run",
        "Castle": "Castle Run",
        "Underwater": "Underwater Run",
    }
    suffix = suffix_map.get(theme, "Run")
    return f"World {world_label} {suffix}"


def _exclude_tile_layer(parent_lc: str, node_name_lc: str) -> bool:
    if "challenge" in parent_lc or "challenge" in node_name_lc:
        return True
    if "minusworldclip" in parent_lc or "minusworldclip" in node_name_lc:
        return True
    return False


def _parse_tile_cells_for_node(node: _NodeEntry) -> list[TileCell]:
    raw = node.properties.get("tile_map_data")
    if not raw:
        return []
    payload_match = _TILE_DATA_RE.search(raw)
    if not payload_match:
        return []
    payload = payload_match.group(1)
    try:
        data = base64.b64decode(payload)
    except Exception:
        return []
    if len(data) < 2:
        return []
    body = data[2:]
    if len(body) % 12 != 0:
        return []

    offset_x, offset_y = _parse_vector2(node.properties.get("position", ""))
    if offset_x is None:
        offset_x = 0.0
    if offset_y is None:
        offset_y = 0.0

    out: list[TileCell] = []
    for idx in range(0, len(body), 12):
        coord_pack, atlas_pack, src_pack = struct.unpack_from("<iii", body, idx)
        cell_x = _signed_16(coord_pack & 0xFFFF)
        cell_y = _signed_16((coord_pack >> 16) & 0xFFFF)
        atlas_x = _signed_16(atlas_pack & 0xFFFF)
        atlas_y = _signed_16((atlas_pack >> 16) & 0xFFFF)
        source_id = int(src_pack & 0xFFFF)
        tile_id = int((src_pack >> 16) & 0xFFFF)

        world_x = int(round(cell_x * TILE_SIZE + offset_x))
        world_y = int(round(cell_y * TILE_SIZE + offset_y))
        out.append(
            TileCell(
                x=world_x,
                y=world_y,
                source_id=source_id,
                atlas_x=atlas_x,
                atlas_y=atlas_y,
                tile_id=tile_id,
                layer=node.name,
            )
        )
    return out


def _signed_16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _is_solid_tile(cell: TileCell) -> bool:
    return cell.source_id == 0


def _detect_enemy_kind(instance_path: str, parent_lc: str) -> str | None:
    if "enemies" not in parent_lc:
        return None
    path = instance_path.lower()
    if "goomba" in path:
        return "goomba"
    if "koopa" in path:
        return "koopa"
    if "piranha" in path:
        return "piranha"
    if "enemy" in path:
        return "goomba"
    return None


def _parse_moving_platform(
    node: _NodeEntry,
    instance_path: str,
    pos_x: float,
    pos_y: float,
) -> MovingPlatformSpec | None:
    path_lc = instance_path.lower()
    if "elevatorplatform.tscn" not in path_lc and "ropeelevatorplatform.tscn" not in path_lc:
        return None

    vertical_dir = _parse_float(node.properties.get("vertical_direction"), default=1.0)
    top = _parse_float(node.properties.get("top"), default=-244.0)
    width = _parse_float(node.properties.get("width"), default=48.0)
    height = _parse_float(node.properties.get("height"), default=8.0)
    speed = _parse_float(node.properties.get("speed"), default=50.0)

    y_min = min(top, 64.0)
    y_max = max(top, 64.0)
    return MovingPlatformSpec(
        x=pos_x,
        y_min=y_min,
        y_max=y_max,
        start_y=pos_y,
        width=width,
        height=height,
        speed=speed,
        direction=1.0 if vertical_dir >= 0 else -1.0,
    )


def _parse_float(raw_value: str | None, default: float) -> float:
    if not raw_value:
        return float(default)
    try:
        return float(str(raw_value).strip().strip('"'))
    except Exception:
        return float(default)


def _parse_block_cell_from_instance(
    instance_path: str,
    parent_lc: str,
    node_name_lc: str,
    x: float,
    y: float,
    layer: str,
) -> TileCell | None:
    if _exclude_tile_layer(parent_lc, node_name_lc):
        return None

    # Prefer explicit level "Blocks" containers; fall back to clear block node names.
    if "blocks" not in parent_lc and "block" not in node_name_lc:
        return None

    tile_id = _scene_block_tile_id_from_instance(instance_path)
    if tile_id is None:
        return None

    return TileCell(
        x=int(round(x)),
        y=int(round(y)),
        source_id=1,
        atlas_x=0,
        atlas_y=0,
        tile_id=tile_id,
        layer=layer,
    )


def _scene_block_tile_id_from_instance(instance_path: str) -> int | None:
    path_lc = str(instance_path).replace("\\", "/").lower()
    for token, tile_id in SCENE_BLOCK_INSTANCE_TILE_IDS:
        if token in path_lc:
            return int(tile_id)
    return None
