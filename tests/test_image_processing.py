import numpy as np
import pytest
from PIL import Image

from image_processing import DesaturationImageMapping, HueImageMapping, image_map_to_grayscale


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

    image_map = HueImageMapping().map_image(image, palette_size=6)

    assert image_map.shape == (1, 4)
    assert image_map[0, 0] == image_map[0, 1]
    assert image_map[0, 0] == 0
    assert image_map[0, 2] == 2
    assert image_map[0, 3] == 4


def test_hue_image_mapping_rejects_empty_palette_size() -> None:
    with pytest.raises(ValueError):
        HueImageMapping().map_image(Image.new("RGB", (1, 1)), palette_size=0)


def test_desaturation_image_mapping_still_returns_2d_indices() -> None:
    image = Image.new("RGB", (2, 1))
    image.putdata([(0, 0, 0), (255, 255, 255)])

    image_map = DesaturationImageMapping().map_image(image, palette_size=3)

    np.testing.assert_array_equal(image_map, np.array([[0, 2]], dtype=np.uint8))


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
