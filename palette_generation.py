"""Color palette generation utilities."""

from __future__ import annotations

import colorsys
import random
import re


HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def generate_random_hex_color() -> str:
    """Return a random color encoded as #RRGGBB."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert a #RRGGBB color to integer RGB components."""
    match = HEX_COLOR_RE.match(color)
    if match is None:
        raise ValueError("Color must be encoded as hexadecimal #RRGGBB, for example #336699.")

    value = match.group(1)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert integer RGB components to #RRGGBB."""
    red, green, blue = rgb
    return f"#{red:02x}{green:02x}{blue:02x}"


def _float_rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return rgb_to_hex(tuple(round(channel * 255) for channel in rgb))


def _lightness_values(seed_lightness: float, step: float, palette_size: int) -> list[float]:
    if palette_size < 1:
        raise ValueError("Palette size must be at least 1.")
    if step < 0:
        raise ValueError("Step must be a non-negative HLS lightness value.")

    span = step * (palette_size - 1)
    if span > 1:
        raise ValueError("Step is too large for the requested palette size in lightness range [0, 1].")

    start = seed_lightness - span / 2
    start = min(max(start, 0), 1 - span)
    return [start + index * step for index in range(palette_size)]


def generate_monochromatic_palette(
    seed_color: str | None = None,
    step: float = 0.1,
    palette_size: int = 5,
) -> list[str]:
    """Generate a monochromatic palette as #RRGGBB colors.

    The palette is computed in HLS color space. Hue and saturation are copied
    from the seed color; only lightness changes. HLS lightness uses real values
    in the closed interval [0.0, 1.0].
    """
    if seed_color is None:
        seed_color = generate_random_hex_color()

    red, green, blue = hex_to_rgb(seed_color)
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)

    palette = []
    for next_lightness in _lightness_values(lightness, step, palette_size):
        palette.append(_float_rgb_to_hex(colorsys.hls_to_rgb(hue, next_lightness, saturation)))

    return palette
