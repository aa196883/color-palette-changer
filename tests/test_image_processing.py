import numpy as np
import pytest
from PIL import Image

from image_processing import (
    DesaturationImageMapping,
    HSLClustersImageMapping,
    HSLPaletteDistanceImageMapping,
    HueImageMapping,
    OKlabClustersImageMapping,
    image_map_to_grayscale,
)
from palette import Pallette


def palette_data(palette_size: int) -> Pallette:
    return Pallette(palette_size=palette_size, colors=("#000000",) * palette_size)


def test_hue_image_mapping_quantizes_similar_hues_together() -> None:
    image = Image.new("RGB", (4, 1))
    image.putdata(
        [
            (255, 0, 0),
            (255, 64, 64),
            (0, 255, 0),
            (0, 0, 255),
        ]
    )

    image_map = HueImageMapping().map_image(image, palette_data(6))

    assert image_map.shape == (1, 4)
    assert image_map[0, 0] == image_map[0, 1]
    assert image_map[0, 0] == 0
    assert image_map[0, 2] == 3
    assert image_map[0, 3] == 5


def test_hue_image_mapping_clamps_max_normalized_hue_to_last_palette_index() -> None:
    image = Image.new("RGB", (2, 1))
    image.putdata([(255, 0, 0), (0, 0, 255)])

    image_map = HueImageMapping().map_image(image, palette_data(2))

    np.testing.assert_array_equal(image_map, np.array([[0, 1]], dtype=np.uint8))


def test_pallette_rejects_empty_palette_size() -> None:
    with pytest.raises(ValueError):
        Pallette(palette_size=0, colors=())


def test_desaturation_image_mapping_still_returns_2d_indices() -> None:
    image = Image.new("RGB", (2, 1))
    image.putdata([(0, 0, 0), (255, 255, 255)])

    image_map = DesaturationImageMapping().map_image(image, palette_data(3))

    np.testing.assert_array_equal(image_map, np.array([[0, 2]], dtype=np.uint8))


def test_hsl_clusters_image_mapping_clusters_pixels_by_hsl_similarity() -> None:
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

    image_map = HSLClustersImageMapping().map_image(image, palette_data(2))

    assert image_map.shape == (2, 4)
    assert image_map.dtype == np.uint8
    assert len(np.unique(image_map)) == 2
    assert image_map[0, 0] == image_map[1, 0]
    assert image_map[0, 1] == image_map[1, 1]
    assert image_map[0, 2] == image_map[1, 2]
    assert image_map[0, 3] == image_map[1, 3]
    assert image_map[0, 0] != image_map[0, 2]


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

    image_map = OKlabClustersImageMapping().map_image(image, palette_data(2))

    assert image_map.shape == (2, 4)
    assert image_map.dtype == np.uint8
    assert len(np.unique(image_map)) == 2
    assert image_map[0, 0] == image_map[1, 0]
    assert image_map[0, 1] == image_map[1, 1]
    assert image_map[0, 2] == image_map[1, 2]
    assert image_map[0, 3] == image_map[1, 3]
    assert image_map[0, 0] != image_map[0, 2]


def test_hsl_palette_distance_image_mapping_uses_nearest_palette_color() -> None:
    image = Image.new("RGB", (4, 1))
    image.putdata(
        [
            (250, 5, 5),
            (5, 250, 5),
            (5, 5, 250),
            (128, 128, 128),
        ]
    )
    palette = Pallette(
        palette_size=4,
        colors=("#ff0000", "#00ff00", "#0000ff", "#808080"),
    )

    image_map = HSLPaletteDistanceImageMapping().map_image(image, palette)

    np.testing.assert_array_equal(image_map, np.array([[0, 1, 2, 3]], dtype=np.uint8))


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
