from palette_generation import generate_oklab_palette, generate_palette, normalize_hex_color


def test_generate_palette_returns_requested_size() -> None:
    palette = generate_palette(
        seed_color="#336699",
        hue_step=0.08,
        saturation_step=0.02,
        brightness_step=0.05,
        palette_size=7,
    )

    assert len(palette) == 7
    assert all(color.startswith("#") and len(color) == 7 for color in palette)


def test_generate_oklab_palette_accepts_signed_steps() -> None:
    palette = generate_oklab_palette(
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
