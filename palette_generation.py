"""Color palette generation utilities."""

from __future__ import annotations

import colorsys
import random
import re


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


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(max(value, lower), upper)


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


def _linear_to_srgb(channel: float) -> float:
    if channel <= 0.0031308:
        return 12.92 * channel

    return 1.055 * channel ** (1 / 2.4) - 0.055


def _srgb_to_linear(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92

    return ((channel + 0.055) / 1.055) ** 2.4


def _float_rgb_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    red, green, blue = (_srgb_to_linear(channel) for channel in rgb)

    long_cone = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    medium_cone = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    short_cone = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue

    long_cone_root = long_cone ** (1 / 3)
    medium_cone_root = medium_cone ** (1 / 3)
    short_cone_root = short_cone ** (1 / 3)

    lightness = (
        0.2104542553 * long_cone_root
        + 0.7936177850 * medium_cone_root
        - 0.0040720468 * short_cone_root
    )
    green_red = (
        1.9779984951 * long_cone_root
        - 2.4285922050 * medium_cone_root
        + 0.4505937099 * short_cone_root
    )
    blue_yellow = (
        0.0259040371 * long_cone_root
        + 0.7827717662 * medium_cone_root
        - 0.8086757660 * short_cone_root
    )

    return lightness, green_red, blue_yellow


def _oklab_to_float_rgb(oklab: tuple[float, float, float]) -> tuple[float, float, float]:
    lightness, green_red, blue_yellow = oklab

    long_cone_root = lightness + 0.3963377774 * green_red + 0.2158037573 * blue_yellow
    medium_cone_root = lightness - 0.1055613458 * green_red - 0.0638541728 * blue_yellow
    short_cone_root = lightness - 0.0894841775 * green_red - 1.2914855480 * blue_yellow

    long_cone = long_cone_root**3
    medium_cone = medium_cone_root**3
    short_cone = short_cone_root**3

    linear_red = 4.0767416621 * long_cone - 3.3077115913 * medium_cone + 0.2309699292 * short_cone
    linear_green = -1.2684380046 * long_cone + 2.6097574011 * medium_cone - 0.3413193965 * short_cone
    linear_blue = -0.0041960863 * long_cone - 0.7034186147 * medium_cone + 1.7076147010 * short_cone

    return (
        _clamp(_linear_to_srgb(_clamp(linear_red))),
        _clamp(_linear_to_srgb(_clamp(linear_green))),
        _clamp(_linear_to_srgb(_clamp(linear_blue))),
    )


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


def generate_oklab_palette(
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
    lightness, green_red, blue_yellow = _float_rgb_to_oklab((red / 255, green / 255, blue / 255))

    span_offset = (palette_size - 1) / 2
    oklab_values = [
        (
            lightness + (index - span_offset) * lightness_step,
            green_red + (index - span_offset) * green_red_step,
            blue_yellow + (index - span_offset) * blue_yellow_step,
        )
        for index in range(palette_size)
    ]

    return [_float_rgb_to_hex(_oklab_to_float_rgb(value)) for value in oklab_values]
