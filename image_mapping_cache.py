"""Persistent storage for generated image mapping arrays."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np


DEFAULT_CACHE_DIR = Path(".cache")
SAFE_CACHE_KEY_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def image_mapping_cache_key(
    input_image: str | Path,
    mapping_name: str,
    palette_size: int,
) -> str:
    """Build a cache key from image name, mapping method, and palette size."""
    image_name = Path(input_image).name
    raw_key = f"{image_name}--{mapping_name}--{palette_size}"
    return SAFE_CACHE_KEY_RE.sub("_", raw_key)


def image_mapping_cache_path(cache_key: str, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> Path:
    return Path(cache_dir) / f"{cache_key}.npy"


def load_image_mapping(cache_key: str, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> np.ndarray | None:
    cache_path = image_mapping_cache_path(cache_key, cache_dir)
    if not cache_path.is_file():
        return None

    return np.load(cache_path, allow_pickle=False)


def save_image_mapping(
    cache_key: str,
    image_map: np.ndarray,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
) -> Path:
    cache_path = image_mapping_cache_path(cache_key, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, image_map)
    return cache_path
