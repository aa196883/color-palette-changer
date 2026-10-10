import numpy as np
import pytest

from palette_generation import generate_palette, normalize_hex_color


def test_generate_palette_returns_requested_size() -> None:
    palette = generate_palette(
        seed_color="#336699",
        lightness_step=0.0,
        green_red_step=-0.1,
        blue_yellow_step=0.05,
        palette_size=7,
    )

    assert len(palette) == 7
    assert all(color.startswith("#") and len(color) == 7 for color in palette)


def test_normalize_hex_color_accepts_hashless_input() -> None:
    assert normalize_hex_color("336699") == "#336699"


@pytest.mark.parametrize("size", [1, 2, 3, 4, 7])
@pytest.mark.parametrize("axis", ["a", "b"])
@pytest.mark.parametrize("slope,origin_fraction", [(0, 0.5), (0.5, -1), (-0.5, 1), (1, 0), (-1, 0)])
def test_complementary_samples_cover_axis_with_random_offset(monkeypatch, size, axis, slope, origin_fraction):
    samples = []
    origin = origin_fraction * (1 - abs(slope))
    draws = iter([slope, origin])

    def uniform(low, high):
        value = next(draws)
        assert low <= value <= high
        return value

    monkeypatch.setattr("palette_generation.random.choice", lambda choices: axis)
    monkeypatch.setattr("palette_generation.random.uniform", uniform)

    def capture(sample):
        samples.append(sample)
        return (0.5, 0.5, 0.5)

    monkeypatch.setattr("palette_generation.oklab_to_rgb", capture)
    colors = generate_palette("#336699", palette_size=size, mode="complementary")
    points = np.array(samples)
    assert len(colors) == size
    assert np.allclose(points[:, 0], points[0, 0])
    x = points[:, 1 if axis == "a" else 2] / 0.4
    y = points[:, 2 if axis == "a" else 1] / 0.4
    assert np.allclose(y, slope * x + origin)
    assert np.mean(x) == pytest.approx(0)
    assert np.mean(y) == pytest.approx(origin)
    assert np.all(np.abs(points[:, 1:]) <= 0.4)
    # Include the excluded endpoints: the selected axis covers its full range.
    assert x[0] - 2 / (size + 1) == pytest.approx(-1)
    assert x[-1] + 2 / (size + 1) == pytest.approx(1)
    if size > 1:
        deltas = np.diff(points[:, 1:], axis=0)
        assert np.allclose(deltas, deltas[0])


def test_complementary_ignores_steps_and_uses_random_direction(monkeypatch):
    monkeypatch.setattr("palette_generation.random.choice", lambda choices: "a")
    monkeypatch.setattr("palette_generation.random.uniform", lambda low, high: 0.0)
    horizontal = generate_palette("#336699", palette_size=4, mode="complementary")
    assert horizontal == generate_palette(
        "#336699", lightness_step=0.2, green_red_step=-0.1,
        blue_yellow_step=0.3, palette_size=4, mode="complementary",
    )
    monkeypatch.setattr("palette_generation.random.choice", lambda choices: "b")
    assert horizontal != generate_palette("#336699", palette_size=4, mode="complementary")


def test_analogous_default_preserves_seed_and_steps():
    assert generate_palette("#336699") == ["#336699"] * 5
    kwargs = dict(seed_color="#336699", green_red_step=0.02, palette_size=3)
    assert generate_palette(**kwargs) == generate_palette(**kwargs, mode="analogous")
    assert generate_palette(**kwargs)[1] == "#336699"


@pytest.mark.parametrize("mode", ["analogous", "complementary"])
def test_palette_rejects_empty_size(mode):
    with pytest.raises(ValueError, match="at least 1"):
        generate_palette(palette_size=0, mode=mode)


def test_palette_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unknown palette mode"):
        generate_palette(mode="unknown")
