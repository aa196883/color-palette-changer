"""Image processing primitives for palette-based recoloring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from PIL import Image

from palette import Pallette
from palette_generation import hex_to_rgb


class ImageMapping(ABC):
    """Abstract interface for mapping image pixels to palette indices."""

    name: str

    @abstractmethod
    def map_image(self, image: Image.Image, palette: Pallette) -> np.ndarray:
        """Return a 2D integer array mapping each pixel to a palette index."""


class DesaturationImageMapping(ImageMapping):
    """Desaturate an image and quantize grayscale values to palette indices."""

    name = "grayscaled"

    def map_image(self, image: Image.Image, palette: Pallette) -> np.ndarray:
        grayscale = image.convert("L")
        grey_values = np.asarray(grayscale, dtype=np.float32)

        if palette.palette_size == 1:
            return np.zeros(grey_values.shape, dtype=np.uint8)

        max_index = palette.palette_size - 1
        return np.rint((grey_values / 255) * max_index).astype(np.uint8)


class HueImageMapping(ImageMapping):
    """Quantize pixels by hue in HSV/HSL-like color space."""

    name = "hue"

    def map_image(self, image: Image.Image, palette: Pallette) -> np.ndarray:
        hue_values = np.asarray(image.convert("HSV"), dtype=np.float32)[:, :, 0]

        if palette.palette_size == 1:
            return np.zeros(hue_values.shape, dtype=np.uint8)

        min_hue = hue_values.min()
        max_hue = hue_values.max()
        if min_hue == max_hue:
            return np.zeros(hue_values.shape, dtype=np.uint8)

        normalized_hues = (hue_values - min_hue) / (max_hue - min_hue)
        image_map = np.floor(normalized_hues * palette.palette_size).astype(_image_map_dtype(palette.palette_size))
        image_map[image_map == palette.palette_size] = palette.palette_size - 1

        # apply majority filter to smooth out small hue clusters
        for _ in range(1):
            image_map = majority_filter(image_map, kernel_size=3)
        return image_map


class HSLClustersImageMapping(ImageMapping):
    """Cluster pixels in HSL color space with deterministic k-means."""

    name = "hsl-clusters"

    def __init__(self, max_iterations: int = 20) -> None:
        if max_iterations < 1:
            raise ValueError("Max iterations must be at least 1.")

        self.max_iterations = max_iterations

    def map_image(self, image: Image.Image, palette: Pallette) -> np.ndarray:
        rgb_values = np.asarray(image.convert("RGB"), dtype=np.float32) / 255
        height, width = rgb_values.shape[:2]
        if palette.palette_size == 1:
            return np.zeros((height, width), dtype=np.uint8)

        hsl_points = _rgb_to_hsl(rgb_values).reshape(-1, 3)
        cluster_count = min(palette.palette_size, len(np.unique(hsl_points, axis=0)))
        if cluster_count == 1:
            return np.zeros((height, width), dtype=np.uint8)

        labels = _k_means_labels(hsl_points, cluster_count, self.max_iterations)

        # apply majority filter to smooth out small clusters
        for _ in range(3):
            labels = majority_filter(labels.reshape(height, width), kernel_size=3)
        return labels.astype(_image_map_dtype(palette.palette_size))


def image_map_to_grayscale(image_map: np.ndarray) -> Image.Image:
    """Convert a 2D integer image map to an 8-bit grayscale visualization."""
    if image_map.ndim != 2:
        raise ValueError("Image map must be a 2D array.")
    if image_map.size == 0:
        raise ValueError("Image map must not be empty.")
    if not np.issubdtype(image_map.dtype, np.integer):
        raise TypeError("Image map must contain integer values.")

    min_value = image_map.min()
    max_value = image_map.max()
    if min_value == max_value:
        return Image.fromarray(np.zeros(image_map.shape, dtype=np.uint8), mode="L")

    scaled = ((image_map.astype(np.float32) - min_value) / (max_value - min_value) * 255).astype(np.uint8)
    return Image.fromarray(scaled, mode="L")


def _rgb_to_hsl(rgb_values: np.ndarray) -> np.ndarray:
    """Convert RGB values in the [0, 1] range to HSL points."""
    red = rgb_values[:, :, 0]
    green = rgb_values[:, :, 1]
    blue = rgb_values[:, :, 2]

    max_channel = rgb_values.max(axis=2)
    min_channel = rgb_values.min(axis=2)
    delta = max_channel - min_channel

    lightness = (max_channel + min_channel) / 2
    hue = np.zeros_like(lightness)
    saturation = np.zeros_like(lightness)

    colored = delta != 0
    saturation[colored] = np.where(
        lightness[colored] > 0.5,
        delta[colored] / (2 - max_channel[colored] - min_channel[colored]),
        delta[colored] / (max_channel[colored] + min_channel[colored]),
    )

    red_is_max = colored & (max_channel == red)
    green_is_max = colored & (max_channel == green)
    blue_is_max = colored & (max_channel == blue)

    hue[red_is_max] = ((green[red_is_max] - blue[red_is_max]) / delta[red_is_max]) % 6
    hue[green_is_max] = ((blue[green_is_max] - red[green_is_max]) / delta[green_is_max]) + 2
    hue[blue_is_max] = ((red[blue_is_max] - green[blue_is_max]) / delta[blue_is_max]) + 4
    hue /= 6

    return np.stack((hue, saturation, lightness), axis=2)


def _k_means_labels(points: np.ndarray, cluster_count: int, max_iterations: int) -> np.ndarray:
    centers = _initial_cluster_centers(points, cluster_count)
    labels: np.ndarray | None = None

    for _ in range(max_iterations):
        distances = np.sum((points[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2, axis=2)
        new_labels = np.argmin(distances, axis=1)

        new_centers = centers.copy()
        nearest_distances = distances[np.arange(len(points)), new_labels]
        for cluster_id in range(cluster_count):
            cluster_points = points[new_labels == cluster_id]
            if len(cluster_points) > 0:
                new_centers[cluster_id] = cluster_points.mean(axis=0)
            else:
                new_centers[cluster_id] = points[np.argmax(nearest_distances)]

        if labels is not None and np.array_equal(labels, new_labels):
            break

        labels = new_labels
        centers = new_centers

    return np.asarray(labels, dtype=np.int32)


def _initial_cluster_centers(points: np.ndarray, cluster_count: int) -> np.ndarray:
    unique_points = np.unique(points, axis=0)
    if cluster_count == len(unique_points):
        return unique_points.astype(np.float32)

    center_indices = np.linspace(0, len(unique_points) - 1, cluster_count, dtype=np.int32)
    return unique_points[center_indices].astype(np.float32)


def _image_map_dtype(palette_size: int) -> np.dtype:
    if palette_size <= np.iinfo(np.uint8).max + 1:
        return np.dtype(np.uint8)

    return np.dtype(np.int32)


# majority filter
def majority_filter(image_map: np.ndarray, kernel_size: int) -> np.ndarray:
    """Apply a majority filter to a 2D image map."""
    if image_map.ndim != 2:
        raise ValueError("Image map must be a 2D array.")
    if kernel_size < 2:
        raise ValueError("Kernel size must be at least 2.")

    pad_size = kernel_size // 2
    padded_map = np.pad(image_map, pad_size, mode="edge")
    filtered_map = np.zeros_like(image_map)

    for i in range(image_map.shape[0]):
        for j in range(image_map.shape[1]):
            kernel = padded_map[i : i + kernel_size, j : j + kernel_size]
            values, counts = np.unique(kernel, return_counts=True)
            filtered_map[i, j] = values[np.argmax(counts)]

    return filtered_map

IMAGE_MAPPING_CLASSES = {
    DesaturationImageMapping.name: DesaturationImageMapping,
    HueImageMapping.name: HueImageMapping,
    HSLClustersImageMapping.name: HSLClustersImageMapping,
}


DEFAULT_IMAGE_MAPPING_NAME = DesaturationImageMapping.name


def image_mapping_names() -> tuple[str, ...]:
    """Return CLI-stable image mapping names."""
    return tuple(IMAGE_MAPPING_CLASSES)


def create_image_mapping(name: str) -> ImageMapping:
    """Create an image mapping by CLI-stable name."""
    try:
        mapping_class = IMAGE_MAPPING_CLASSES[name]
    except KeyError as error:
        raise ValueError(f"Unknown image mapping: {name}") from error

    return mapping_class()


def apply_palette(image_map: np.ndarray, palette: Pallette) -> Image.Image:
    """Apply encoded palette colors to a 2D image map."""
    if image_map.ndim != 2:
        raise ValueError("Image map must be a 2D array.")

    rgb_palette = np.array([hex_to_rgb(color) for color in palette.colors], dtype=np.uint8)
    if image_map.min(initial=0) < 0 or image_map.max(initial=0) >= len(rgb_palette):
        raise ValueError("Image map contains a palette index outside the palette range.")

    return Image.fromarray(rgb_palette[image_map])


def map_image_with_palette(
    input_image: str | Path,
    palette: Pallette,
    output_path: str | Path,
    image_mapping: ImageMapping | None = None,
) -> Path:
    """Map an input image to a palette and save the recolored result."""
    mapping = image_mapping or DesaturationImageMapping()
    with Image.open(input_image) as image:
        image_map = mapping.map_image(image, palette)

    output_image = apply_palette(image_map, palette)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output_image.save(output)
    return output

# Test code for mapper
if __name__ == "__main__":
    image_input = "lenna.png"
    test_palette = Pallette(palette_size=8, colors=("#000000",) * 8)
    # test hsl clusters mapping
    mapping = HSLClustersImageMapping()
    image_map = mapping.map_image(Image.open(image_input), test_palette)
    visualization = image_map_to_grayscale(image_map)
    visualization.save("lenna_hsl_clusters.png")

    # test gray mapping
    mapping = DesaturationImageMapping()
    image_map = mapping.map_image(Image.open(image_input), test_palette)
    visualization = image_map_to_grayscale(image_map)
    visualization.save("lenna_desaturation.png")

    # test hue mapping
    mapping = HueImageMapping()
    image_map = mapping.map_image(Image.open(image_input), test_palette)
    visualization = image_map_to_grayscale(image_map)
    visualization.save("lenna_hue.png")
