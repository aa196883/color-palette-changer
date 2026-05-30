"""Utility functions for palette visualization."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from palette import Pallette
from palette_generation import hex_to_rgb


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = chunk_type + data
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)


def save_palette_png(
    palette: list[str],
    output_path: str | Path = "palettes/palette.png",
    stripe_width: int = 120,
    height: int = 120,
) -> Path:
    """Save a palette as a PNG made of vertical color stripes."""
    if not palette:
        raise ValueError("Palette must contain at least one color.")
    if stripe_width < 1:
        raise ValueError("Stripe width must be at least 1 pixel.")
    if height < 1:
        raise ValueError("Height must be at least 1 pixel.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    width = stripe_width * len(palette)
    row = bytearray()
    for color in palette:
        row.extend(bytes(hex_to_rgb(color)) * stripe_width)

    raw_image = b"".join(b"\x00" + bytes(row) for _ in range(height))
    png_data = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw_image))
        + _png_chunk(b"IEND", b"")
    )

    output.write_bytes(png_data)
    return output


def save_palette_json(
    palette: list[str],
    seed_color: str,
    hue_step: float,
    saturation_step: float,
    brightness_step: float,
    palette_size: int,
    output_path: str | Path = "palettes/palette.json",
) -> Path:
    """Save palette colors and generation parameters as JSON."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "colors": palette,
        "seed": seed_color,
        "step_values": {
            "hue": hue_step,
            "saturation": saturation_step,
            "brightness": brightness_step,
        },
        "palette_size": palette_size,
    }
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return output


def save_palette_outputs(
    palette: list[str],
    seed_color: str,
    hue_step: float,
    saturation_step: float,
    brightness_step: float,
    palette_size: int,
    output_path: str | Path = "palettes/palette.png",
) -> tuple[Path, Path]:
    """Save a palette as both a PNG preview and same-name JSON metadata."""
    png_path = save_palette_png(palette, output_path)
    json_path = save_palette_json(
        palette=palette,
        seed_color=seed_color,
        hue_step=hue_step,
        saturation_step=saturation_step,
        brightness_step=brightness_step,
        palette_size=palette_size,
        output_path=png_path.with_suffix(".json"),
    )
    return png_path, json_path


def load_palette_json(path: str | Path) -> Pallette:
    """Load palette JSON metadata from disk."""
    source = Path(path)
    with source.open(encoding="utf-8") as file:
        data = json.load(file)

    return Pallette.from_json_data(data)
