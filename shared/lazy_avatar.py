"""
Lazy avatar image wrapper.

Keeps follower/avatar references lightweight by delaying image decode until a
renderer actually needs pixel data.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from threading import Lock

from PIL import Image


_IMAGE_CACHE: "OrderedDict[str, Image.Image]" = OrderedDict()
_CACHE_LOCK = Lock()


def _cache_limit() -> int:
    try:
        import config

        return max(0, int(getattr(config, "AVATAR_LAZY_IMAGE_CACHE_LIMIT", 512) or 0))
    except Exception:
        return 512


def clear_lazy_avatar_cache() -> None:
    with _CACHE_LOCK:
        _IMAGE_CACHE.clear()


class LazyAvatarImage:
    """PIL-compatible proxy that decodes avatar files on demand."""
    __slots__ = ("source_path", "max_size", "cache_key")

    def __init__(self, source_path: str | Path, *, max_size: int = 0, cache_key: str | None = None):
        self.source_path = str(Path(source_path))
        self.max_size = max(0, int(max_size or 0))
        self.cache_key = str(cache_key or f"{self.source_path}|{self.max_size}")

    def _load_image(self) -> Image.Image:
        with _CACHE_LOCK:
            cached = _IMAGE_CACHE.get(self.cache_key)
            if cached is not None:
                _IMAGE_CACHE.move_to_end(self.cache_key)
                return cached

        with Image.open(self.source_path) as img:
            loaded = img.convert("RGBA")

        if self.max_size > 0 and (loaded.width > self.max_size or loaded.height > self.max_size):
            loaded.thumbnail((self.max_size, self.max_size), Image.LANCZOS)

        with _CACHE_LOCK:
            _IMAGE_CACHE[self.cache_key] = loaded
            _IMAGE_CACHE.move_to_end(self.cache_key)
            limit = _cache_limit()
            while limit > 0 and len(_IMAGE_CACHE) > limit:
                _IMAGE_CACHE.popitem(last=False)

        return loaded

    def as_pil(self) -> Image.Image:
        return self._load_image()

    @property
    def width(self) -> int:
        return self._load_image().width

    @property
    def height(self) -> int:
        return self._load_image().height

    @property
    def size(self):
        return self._load_image().size

    @property
    def mode(self) -> str:
        return self._load_image().mode

    def __getattr__(self, name):
        return getattr(self._load_image(), name)

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"LazyAvatarImage(source_path={self.source_path!r}, max_size={self.max_size})"
