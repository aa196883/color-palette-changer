"""Command-line interface for palette generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from palette_generation import generate_monochromatic_palette, generate_random_hex_color
from utils import save_palette_png


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def lightness_step(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or parsed > 1:
        raise argparse.ArgumentTypeError("step must be an HLS lightness value between 0 and 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate color palettes for image recoloring experiments.",
        epilog=(
            "Examples:\n"
            "  .venv/bin/python main.py --colors '#336699' --step 0.1 --palette-size 5\n"
            "  .venv/bin/python main.py -c '#cc5500' -s 0.08 -p 7 -o palettes/warm.png --verbose\n"
            "  .venv/bin/python main.py --step 0.12 --palette-size 6 --verbose"
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
        "-s",
        "--step",
        type=lightness_step,
        default=0.1,
        help="HLS lightness step between neighboring colors, in the real range [0, 1].",
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
    seed_color = args.color or generate_random_hex_color()

    if args.verbose:
        print(
            "Monochromatic color palette from seed "
            f"{seed_color}, step {args.step}, and size {args.palette_size}"
        )

    palette = generate_monochromatic_palette(
        seed_color=seed_color,
        step=args.step,
        palette_size=args.palette_size,
    )
    output_path = save_palette_png(palette, args.output)

    if args.verbose:
        print(f"Color palette generated = {palette}. Saved to {output_path}")


if __name__ == "__main__":
    main()
