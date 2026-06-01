import numpy as np
import pytest
from PIL import Image

from image_processing import (
    DesaturationImageMapping,
    OKlabClustersImageMapping,
    _map_cluster_labels_to_palette_indices,
    _map_grayscale_labels_to_palette_indices,
    image_map_to_grayscale,
    map_image_with_palette,
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


def test_map_image_with_palette_uses_cached_mapping(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "input.png"
    palette_path = tmp_path / "palette.json"
    output_path = tmp_path / "mapped.png"
    Image.new("RGB", (2, 1), (255, 255, 255)).save(image_path)
    palette_path.write_text('{"colors":["#000000","#ffffff"],"palette_size":2}\n', encoding="utf-8")
    cached_map = np.array([[0, 1]], dtype=np.uint8)
    captured = {}

    class FailingMapping(DesaturationImageMapping):
        name = "grayscaled"

        def map_image(self, image, palette):
            raise AssertionError("mapping should be loaded from cache")

    def fake_load_image_mapping(cache_key):
        captured["cache_key"] = cache_key
        return cached_map

    def fake_save_image_mapping(cache_key, image_map):
        raise AssertionError("cached mapping should not be regenerated")

    monkeypatch.setattr("image_processing.load_image_mapping", fake_load_image_mapping)
    monkeypatch.setattr("image_processing.save_image_mapping", fake_save_image_mapping)

    map_image_with_palette(
        input_image=image_path,
        palette=Pallette(palette_size=2, colors=("#000000", "#ffffff")),
        output_path=output_path,
        image_mapping=FailingMapping(),
        palette_json_path=palette_path,
    )

    assert output_path.is_file()
    assert captured["cache_key"] == "input.png--grayscaled--2"


def test_map_image_with_palette_saves_generated_mapping_on_cache_miss(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "input.png"
    palette_path = tmp_path / "palette.json"
    output_path = tmp_path / "mapped.png"
    image = Image.new("RGB", (2, 1))
    image.putdata([(0, 0, 0), (255, 255, 255)])
    image.save(image_path)
    palette_path.write_text('{"colors":["#000000","#ffffff"],"palette_size":2}\n', encoding="utf-8")
    saved = {}

    def fake_load_image_mapping(cache_key):
        return None

    def fake_save_image_mapping(cache_key, image_map):
        saved["cache_key"] = cache_key
        saved["image_map"] = image_map.copy()

    monkeypatch.setattr("image_processing.load_image_mapping", fake_load_image_mapping)
    monkeypatch.setattr("image_processing.save_image_mapping", fake_save_image_mapping)

    map_image_with_palette(
        input_image=image_path,
        palette=Pallette(palette_size=2, colors=("#000000", "#ffffff")),
        output_path=output_path,
        image_mapping=DesaturationImageMapping(),
        palette_json_path=palette_path,
    )

    assert output_path.is_file()
    assert saved["cache_key"] == "input.png--grayscaled--2"
    np.testing.assert_array_equal(saved["image_map"], np.array([[0, 1]], dtype=np.uint8))


def test_cached_grayscale_intermediate_is_reused_for_same_palette_size(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "input.png"
    first_palette_path = tmp_path / "first.json"
    second_palette_path = tmp_path / "second.json"
    first_output_path = tmp_path / "first.png"
    second_output_path = tmp_path / "second.png"
    image = Image.new("RGB", (2, 1))
    image.putdata([(0, 0, 0), (255, 255, 255)])
    image.save(image_path)
    first_palette_path.write_text('{"colors":["#000000","#ffffff"],"palette_size":2}\n', encoding="utf-8")
    second_palette_path.write_text('{"colors":["#ff0000","#00ff00"],"palette_size":2}\n', encoding="utf-8")
    cache = {}

    def fake_load_image_mapping(cache_key):
        return cache.get(cache_key)

    def fake_save_image_mapping(cache_key, image_map):
        cache[cache_key] = image_map.copy()

    monkeypatch.setattr("image_processing.load_image_mapping", fake_load_image_mapping)
    monkeypatch.setattr("image_processing.save_image_mapping", fake_save_image_mapping)

    map_image_with_palette(
        input_image=image_path,
        palette=Pallette(palette_size=2, colors=("#000000", "#ffffff")),
        output_path=first_output_path,
        image_mapping=DesaturationImageMapping(),
        palette_json_path=first_palette_path,
    )
    map_image_with_palette(
        input_image=image_path,
        palette=Pallette(palette_size=2, colors=("#ff0000", "#00ff00")),
        output_path=second_output_path,
        image_mapping=DesaturationImageMapping(),
        palette_json_path=second_palette_path,
    )

    assert list(cache) == ["input.png--grayscaled--2"]
    np.testing.assert_array_equal(np.asarray(Image.open(first_output_path)), np.array([[[0, 0, 0], [255, 255, 255]]]))
    np.testing.assert_array_equal(np.asarray(Image.open(second_output_path)), np.array([[[255, 0, 0], [0, 255, 0]]]))


def test_cached_oklab_cluster_intermediate_is_reused_for_same_palette_size(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "input.png"
    first_palette_path = tmp_path / "first.json"
    second_palette_path = tmp_path / "second.json"
    first_output_path = tmp_path / "first.png"
    second_output_path = tmp_path / "second.png"
    image = Image.new("RGB", (2, 1))
    image.putdata([(255, 0, 0), (0, 255, 0)])
    image.save(image_path)
    first_palette_path.write_text('{"colors":["#00ff00","#ff0000"],"palette_size":2}\n', encoding="utf-8")
    second_palette_path.write_text('{"colors":["#ff0000","#00ff00"],"palette_size":2}\n', encoding="utf-8")
    cache = {}

    def fake_load_image_mapping(cache_key):
        return cache.get(cache_key)

    def fake_save_image_mapping(cache_key, image_map):
        cache[cache_key] = image_map.copy()

    monkeypatch.setattr("image_processing.load_image_mapping", fake_load_image_mapping)
    monkeypatch.setattr("image_processing.save_image_mapping", fake_save_image_mapping)

    map_image_with_palette(
        input_image=image_path,
        palette=Pallette(palette_size=2, colors=("#00ff00", "#ff0000")),
        output_path=first_output_path,
        image_mapping=OKlabClustersImageMapping(),
        palette_json_path=first_palette_path,
    )
    map_image_with_palette(
        input_image=image_path,
        palette=Pallette(palette_size=2, colors=("#ff0000", "#00ff00")),
        output_path=second_output_path,
        image_mapping=OKlabClustersImageMapping(),
        palette_json_path=second_palette_path,
    )

    assert list(cache) == ["input.png--oklab-clusters--2"]
    np.testing.assert_array_equal(np.asarray(Image.open(first_output_path)), np.array([[[255, 0, 0], [0, 255, 0]]]))
    np.testing.assert_array_equal(np.asarray(Image.open(second_output_path)), np.array([[[255, 0, 0], [0, 255, 0]]]))
