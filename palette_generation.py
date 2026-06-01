"""Color palette generation utilities."""

from __future__ import annotations

import random
import re

from oklab import oklab_to_rgb, rgb_to_oklab


HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def generate_random_hex_color() -> str:
    """Return a random color encoded as #RRGGBB."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def normalize_hex_color(color: str) -> str:
    """Normalize a hexadecimal color to #rrggbb."""
    match = HEX_COLOR_RE.match(color)
    if match is None:
        raise ValueError("Color must be encoded as hexadecimal #RRGGBB, for example #336699.")

    return f"#{match.group(1).lower()}"


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert a #RRGGBB color to integer RGB components."""
    value = normalize_hex_color(color)[1:]
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert integer RGB components to #RRGGBB."""
    red, green, blue = rgb
    return f"#{red:02x}{green:02x}{blue:02x}"


def _float_rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return rgb_to_hex(tuple(round(channel * 255) for channel in rgb))


def generate_palette(
    seed_color: str | None = None,
    lightness_step: float = 0.0,
    green_red_step: float = 0.0,
    blue_yellow_step: float = 0.0,
    palette_size: int = 5,
) -> list[str]:
    """Generate a palette as #RRGGBB colors by stepping through OKlab channels."""
    if palette_size < 1:
        raise ValueError("Palette size must be at least 1.")
    if seed_color is None:
        seed_color = generate_random_hex_color()

    red, green, blue = hex_to_rgb(seed_color)
    lightness, green_red, blue_yellow = rgb_to_oklab((red / 255, green / 255, blue / 255))

    span_offset = (palette_size - 1) / 2
    oklab_values = [
        (
            lightness + (index - span_offset) * lightness_step,
            green_red + (index - span_offset) * green_red_step,
            blue_yellow + (index - span_offset) * blue_yellow_step,
        )
        for index in range(palette_size)
    ]

    return [_float_rgb_to_hex(oklab_to_rgb(value)) for value in oklab_values]
