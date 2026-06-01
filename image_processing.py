"""Image processing primitives for palette-based recoloring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from PIL import Image

from oklab import rgb_array_to_oklab
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


class OKlabClustersImageMapping(ImageMapping):
    """Cluster pixels in OKlab color space with deterministic k-means."""

    name = "oklab-clusters"

    def __init__(self, max_iterations: int = 20) -> None:
        if max_iterations < 1:
            raise ValueError("Max iterations must be at least 1.")

        self.max_iterations = max_iterations

    def map_image(self, image: Image.Image, palette: Pallette) -> np.ndarray:
        rgb_values = np.asarray(image.convert("RGB"), dtype=np.float32) / 255
        height, width = rgb_values.shape[:2]
        if palette.palette_size == 1:
            return np.zeros((height, width), dtype=np.uint8)

        oklab_points = rgb_array_to_oklab(rgb_values).reshape(-1, 3)
        cluster_count = min(palette.palette_size, len(np.unique(oklab_points, axis=0)))
        if cluster_count == 1:
            return np.zeros((height, width), dtype=np.uint8)

        labels, centers = _k_means(oklab_points, cluster_count, self.max_iterations)
        palette_rgb = np.array([hex_to_rgb(color) for color in palette.colors], dtype=np.float32) / 255
        palette_oklab = rgb_array_to_oklab(palette_rgb.reshape(1, palette.palette_size, 3)).reshape(palette.palette_size, 3)
        labels = _map_cluster_labels_to_palette_indices(labels, centers, palette_oklab)

        return labels.reshape(height, width).astype(_image_map_dtype(palette.palette_size))


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


def _k_means(points: np.ndarray, cluster_count: int, max_iterations: int) -> tuple[np.ndarray, np.ndarray]:
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

    return np.asarray(labels, dtype=np.int32), centers


def _map_cluster_labels_to_palette_indices(
    labels: np.ndarray,
    centers: np.ndarray,
    palette_points: np.ndarray,
) -> np.ndarray:
    distances = np.sum((centers[:, np.newaxis, :] - palette_points[np.newaxis, :, :]) ** 2, axis=2)
    cluster_to_palette = np.argmin(distances, axis=1)

    return cluster_to_palette[labels]


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


def _majority_filter_if_supported(image_map: np.ndarray, kernel_size: int) -> np.ndarray:
    if min(image_map.shape) < kernel_size:
        return image_map

    return majority_filter(image_map, kernel_size)

IMAGE_MAPPING_CLASSES = {
    DesaturationImageMapping.name: DesaturationImageMapping,
    OKlabClustersImageMapping.name: OKlabClustersImageMapping,
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

    # test palette with 8 grays
    test_palette = Pallette(
        palette_size=8,
        colors=(
            "#000000",
            "#202020",
            "#404040",
            "#606060",
            "#808080",
            "#A0A0A0",
            "#C0C0C0",
            "#E0E0E0",
        ),
    )

    # # test gray mapping
    # mapping = DesaturationImageMapping()
    # image_map = mapping.map_image(Image.open(image_input), test_palette)
    # visualization = image_map_to_grayscale(image_map)
    # visualization.save("lenna_desaturation.png")

    # test oklab clusters mapping
    mapping = OKlabClustersImageMapping()
    image_map = mapping.map_image(Image.open(image_input), test_palette)
    visualization = image_map_to_grayscale(image_map)
    visualization.save("lenna_oklab_clusters.png")
