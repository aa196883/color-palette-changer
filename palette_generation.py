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


def _stepped_values(center: float, step: float, palette_size: int, *, wrap: bool) -> list[float]:
    if palette_size < 1:
        raise ValueError("Palette size must be at least 1.")
    if step < 0 or step > 1:
        raise ValueError("Step must be an HLS value between 0 and 1.")

    span = step * (palette_size - 1)
    if not wrap and span > 1:
        raise ValueError("Step is too large for the requested palette size in HLS range [0, 1].")

    start = center - span / 2
    if not wrap:
        start = min(max(start, 0), 1 - span)

    values = [start + index * step for index in range(palette_size)]
    if wrap:
        return [value % 1 for value in values]

    return values


def generate_palette(
    seed_color: str | None = None,
    hue_step: float = 0.0,
    saturation_step: float = 0.0,
    brightness_step: float = 0.0,
    palette_size: int = 5,
) -> list[str]:
    """Generate a palette as #RRGGBB colors by stepping through HLS channels.

    Hue, lightness, and saturation are centered around the seed color. The
    public ``brightness_step`` argument maps to HLS lightness. Each step uses
    real HLS values in the closed interval [0.0, 1.0].
    """
    if seed_color is None:
        seed_color = generate_random_hex_color()

    red, green, blue = hex_to_rgb(seed_color)
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)

    hue_values = _stepped_values(hue, hue_step, palette_size, wrap=True)
    lightness_values = _stepped_values(lightness, brightness_step, palette_size, wrap=False)
    saturation_values = _stepped_values(saturation, saturation_step, palette_size, wrap=False)

    return [
        _float_rgb_to_hex(colorsys.hls_to_rgb(next_hue, next_lightness, next_saturation))
        for next_hue, next_lightness, next_saturation in zip(hue_values, lightness_values, saturation_values)
    ]
