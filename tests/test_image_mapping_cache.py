import numpy as np

from image_mapping_cache import (
    image_mapping_cache_key,
    image_mapping_cache_path,
    load_image_mapping,
    save_image_mapping,
)


def test_image_mapping_cache_key_uses_image_name_mapping_and_palette_size() -> None:
    cache_key = image_mapping_cache_key(
        input_image="images/lenna.png",
        mapping_name="oklab-clusters",
        palette_size=8,
    )

    assert cache_key == "lenna.png--oklab-clusters--8"


def test_save_and_load_image_mapping_round_trip(tmp_path) -> None:
    image_map = np.array([[0, 1], [2, 3]], dtype=np.uint8)
    cache_key = "input.png--grayscaled--abc123"

    save_image_mapping(cache_key, image_map, cache_dir=tmp_path)

    assert image_mapping_cache_path(cache_key, cache_dir=tmp_path).is_file()
    np.testing.assert_array_equal(load_image_mapping(cache_key, cache_dir=tmp_path), image_map)
