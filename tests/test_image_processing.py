import numpy as np
import pytest
from PIL import Image

from image_processing import (
    DesaturationImageMapping,
    OKlabClustersImageMapping,
    _map_cluster_labels_to_palette_indices,
    _map_grayscale_labels_to_palette_indices,
    image_map_to_grayscale,
)
from palette import Pallette


def palette_data(palette_size: int) -> Pallette:
    return Pallette(palette_size=palette_size, colors=("#000000",) * palette_size)


def test_pallette_rejects_empty_palette_size() -> None:
    with pytest.raises(ValueError):
        Pallette(palette_size=0, colors=())


def test_desaturation_image_mapping_still_returns_2d_indices() -> None:
    image = Image.new("RGB", (2, 1))
    image.putdata([(0, 0, 0), (255, 255, 255)])
    palette = Pallette(palette_size=3, colors=("#000000", "#808080", "#ffffff"))

    image_map = DesaturationImageMapping().map_image(image, palette)

    np.testing.assert_array_equal(image_map, np.array([[0, 2]], dtype=np.uint8))


def test_desaturation_image_mapping_uses_palette_lightness() -> None:
    image = Image.new("RGB", (2, 1))
    image.putdata([(0, 0, 0), (255, 255, 255)])
    palette = Pallette(palette_size=2, colors=("#ffffff", "#000000"))

    image_map = DesaturationImageMapping().map_image(image, palette)

    np.testing.assert_array_equal(image_map, np.array([[1, 0]], dtype=np.uint8))


def test_varying_lightness_grayscale_mapping_uses_one_to_one_assignment() -> None:
    palette_points = np.array(
        [
            [0.90, 0.0, 0.0],
            [1.00, 0.0, 0.0],
            [0.95, 0.0, 0.0],
        ],
        dtype=np.float32,
    )

    label_to_palette = _map_grayscale_labels_to_palette_indices(
        palette_size=3,
        palette_points=palette_points,
        rng=np.random.default_rng(0),
    )

    assert set(label_to_palette.tolist()) == {0, 1, 2}


def test_identical_lightness_grayscale_mapping_uses_one_to_one_oklab_assignment() -> None:
    palette_points = np.array(
        [
            [0.5, 0.0, 0.0],
            [0.5, 0.1, 0.0],
        ],
        dtype=np.float32,
    )

    label_to_palette = _map_grayscale_labels_to_palette_indices(
        palette_size=2,
        palette_points=palette_points,
        rng=np.random.default_rng(0),
    )

    assert set(label_to_palette.tolist()) == {0, 1}


def test_oklab_clusters_image_mapping_clusters_pixels_by_oklab_similarity() -> None:
    image = Image.new("RGB", (4, 2))
    image.putdata(
        [
            (255, 0, 0),
            (245, 10, 10),
            (0, 255, 0),
            (10, 245, 10),
            (255, 0, 0),
            (245, 10, 10),
            (0, 255, 0),
            (10, 245, 10),
        ]
    )

    palette = Pallette(palette_size=2, colors=("#00ff00", "#ff0000"))

    image_map = OKlabClustersImageMapping().map_image(image, palette)

    assert image_map.shape == (2, 4)
    assert image_map.dtype == np.uint8
    assert len(np.unique(image_map)) == 2
    assert image_map[0, 0] == image_map[1, 0]
    assert image_map[0, 1] == image_map[1, 1]
    assert image_map[0, 2] == image_map[1, 2]
    assert image_map[0, 3] == image_map[1, 3]
    assert image_map[0, 0] != image_map[0, 2]
    assert image_map[0, 0] == 1
    assert image_map[0, 2] == 0


def test_cluster_centers_map_to_distinct_palette_points() -> None:
    labels = np.array([0, 1], dtype=np.int32)
    centers = np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]], dtype=np.float32)
    palette_points = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], dtype=np.float32)

    mapped_labels = _map_cluster_labels_to_palette_indices(
        labels,
        centers,
        palette_points,
        rng=np.random.default_rng(0),
    )

    assert set(mapped_labels.tolist()) == {0, 1}


def test_pallette_rejects_size_that_does_not_match_colors() -> None:
    with pytest.raises(ValueError):
        Pallette(palette_size=2, colors=("#000000",))


def test_image_map_to_grayscale_scales_low_to_dark_and_high_to_light() -> None:
    image_map = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint8)

    grayscale = image_map_to_grayscale(image_map)

    assert grayscale.mode == "L"
    np.testing.assert_array_equal(
        np.asarray(grayscale),
        np.array([[0, 51, 102], [153, 204, 255]], dtype=np.uint8),
    )


def test_image_map_to_grayscale_rejects_non_2d_arrays() -> None:
    with pytest.raises(ValueError):
        image_map_to_grayscale(np.array([0, 1, 2], dtype=np.uint8))
