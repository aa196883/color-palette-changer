import math

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
@pytest.mark.parametrize("angle", [0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4])
def test_complementary_samples_are_evenly_spaced_on_centered_line(monkeypatch, size, angle):
    samples = []
    monkeypatch.setattr("palette_generation.random.uniform", lambda low, high: angle)

    def capture(sample):
        samples.append(sample)
        return (0.5, 0.5, 0.5)

    monkeypatch.setattr("palette_generation.oklab_to_rgb", capture)
    colors = generate_palette("#336699", palette_size=size, mode="complementary")
    points = np.array(samples)
    assert len(colors) == size
    assert np.allclose(points[:, 0], points[0, 0])
    assert np.allclose(points[:, 1:].mean(axis=0), 0)
    assert np.all(np.abs(points[:, 1:]) < 0.4)
    if size > 1:
        deltas = np.diff(points[:, 1:], axis=0)
        assert np.allclose(deltas, deltas[0])
        # Extending one segment beyond each end reaches opposite square edges.
        assert max(abs(points[0, 1:] - deltas[0])) == pytest.approx(0.4)
        assert max(abs(points[-1, 1:] + deltas[0])) == pytest.approx(0.4)
        assert np.allclose(points[:, 1] * math.sin(angle), points[:, 2] * math.cos(angle))


def test_complementary_ignores_steps_and_uses_random_direction(monkeypatch):
    monkeypatch.setattr("palette_generation.random.uniform", lambda low, high: 0.0)
    horizontal = generate_palette("#336699", palette_size=4, mode="complementary")
    assert horizontal == generate_palette(
        "#336699", lightness_step=0.2, green_red_step=-0.1,
        blue_yellow_step=0.3, palette_size=4, mode="complementary",
    )
    monkeypatch.setattr("palette_generation.random.uniform", lambda low, high: math.pi / 2)
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
