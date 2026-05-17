"""Image processing primitives for palette-based recoloring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from PIL import Image

from palette_generation import hex_to_rgb


class ImageMapping(ABC):
    """Abstract interface for mapping image pixels to palette indices."""

    @abstractmethod
    def map_image(self, image: Image.Image, palette_size: int) -> np.ndarray:
        """Return a 2D integer array mapping each pixel to a palette index."""


class DesaturationImageMapping(ImageMapping):
    """Desaturate an image and quantize grayscale values to palette indices."""

    def map_image(self, image: Image.Image, palette_size: int) -> np.ndarray:
        if palette_size < 1:
            raise ValueError("Palette size must be at least 1.")

        grayscale = image.convert("L")
        grey_values = np.asarray(grayscale, dtype=np.float32)

        if palette_size == 1:
            return np.zeros(grey_values.shape, dtype=np.uint8)

        max_index = palette_size - 1
        return np.rint((grey_values / 255) * max_index).astype(np.uint8)


def apply_palette(image_map: np.ndarray, palette: list[str]) -> Image.Image:
    """Apply encoded palette colors to a 2D image map."""
    if image_map.ndim != 2:
        raise ValueError("Image map must be a 2D array.")
    if not palette:
        raise ValueError("Palette must contain at least one color.")

    rgb_palette = np.array([hex_to_rgb(color) for color in palette], dtype=np.uint8)
    if image_map.min(initial=0) < 0 or image_map.max(initial=0) >= len(rgb_palette):
        raise ValueError("Image map contains a palette index outside the palette range.")

    return Image.fromarray(rgb_palette[image_map])


def map_image_with_palette(
    input_image: str | Path,
    palette: list[str],
    palette_size: int,
    output_path: str | Path,
    image_mapping: ImageMapping | None = None,
) -> Path:
    """Map an input image to a palette and save the recolored result."""
    if len(palette) != palette_size:
        raise ValueError(f"Palette contains {len(palette)} colors, but palette size is {palette_size}.")

    mapping = image_mapping or DesaturationImageMapping()
    with Image.open(input_image) as image:
        image_map = mapping.map_image(image, palette_size)

    output_image = apply_palette(image_map, palette)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output_image.save(output)
    return output
