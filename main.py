"""Command-line interface for palette generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from palette_generation import generate_palette, generate_random_hex_color, normalize_hex_color
from utils import save_palette_outputs


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def hls_step(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 1:
        raise argparse.ArgumentTypeError("step must be an HLS value between 0 and 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate color palettes for image recoloring experiments.",
        allow_abbrev=False,
        epilog=(
            "Examples:\n"
            "  .venv/bin/python main.py --colors '#336699' --brightness-step 0.1 --palette-size 5\n"
            "  .venv/bin/python main.py -c '#cc5500' -H 0.08 -S 0.02 -B 0.05 -p 7 -o palettes/warm.png --verbose\n"
            "  .venv/bin/python main.py --hue-step 0.12 --saturation-step 0.03 --brightness-step 0.04 --palette-size 6 --verbose"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--colors",
        "--color",
        dest="color",
        default=None,
        help="Seed color encoded as hexadecimal #RRGGBB. If omitted, a random seed is used.",
    )
    parser.add_argument(
        "-H",
        "--hue-step",
        type=hls_step,
        default=0.0,
        help="HLS hue step between neighboring colors, in the real range [0, 1]. Hue wraps around the color wheel.",
    )
    parser.add_argument(
        "-S",
        "--saturation-step",
        type=hls_step,
        default=0.0,
        help="HLS saturation step between neighboring colors, in the real range [0, 1].",
    )
    parser.add_argument(
        "-B",
        "--brightness-step",
        type=hls_step,
        default=0.0,
        help="Brightness step between neighboring colors, mapped to HLS lightness in the real range [0, 1].",
    )
    parser.add_argument(
        "-p",
        "--palette-size",
        type=positive_int,
        default=5,
        help="Number of colors to generate.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("palettes/palette.png"),
        help="Output PNG path.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print generation parameters and output details.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        seed_color = normalize_hex_color(args.color) if args.color else generate_random_hex_color()
    except ValueError as error:
        parser.error(str(error))

    try:
        palette = generate_palette(
            seed_color=seed_color,
            hue_step=args.hue_step,
            saturation_step=args.saturation_step,
            brightness_step=args.brightness_step,
            palette_size=args.palette_size,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.verbose:
        print(
            "Color palette from seed "
            f"{seed_color}, hue step {args.hue_step}, saturation step {args.saturation_step}, "
            f"brightness step {args.brightness_step}, and size {args.palette_size}"
        )

    image_path, json_path = save_palette_outputs(
        palette=palette,
        seed_color=seed_color,
        hue_step=args.hue_step,
        saturation_step=args.saturation_step,
        brightness_step=args.brightness_step,
        palette_size=args.palette_size,
        output_path=args.output,
    )

    if args.verbose:
        print(f"Color palette generated = {palette}. Saved to {image_path} and {json_path}")


if __name__ == "__main__":
    main()
