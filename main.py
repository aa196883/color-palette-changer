"""Command-line interface for palette generation and image mapping."""

from __future__ import annotations

import argparse
from pathlib import Path

from image_processing import DEFAULT_IMAGE_MAPPING_NAME, create_image_mapping, image_mapping_names, map_image_with_palette
from palette_generation import generate_palette, generate_random_hex_color, normalize_hex_color
from utils import load_palette_json, save_palette_outputs


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
        description="Generate palettes and map input images to generated palettes.",
        allow_abbrev=False,
        epilog=(
            "Examples:\n"
            "  .venv/bin/python main.py --generate-palette --colors '#336699' --brightness-step 0.1 --palette-size 5\n"
            "  .venv/bin/python main.py --generate-palette -c '#cc5500' -H 0.08 -S 0.02 -B 0.05 -p 7 -o palettes/warm.png --verbose\n"
            "  .venv/bin/python main.py --map --input-image lenna.png --palette palettes/warm.json --image-mapping=hue -o outputs/lenna.png"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--generate-palette",
        action="store_true",
        help="Generate a color palette PNG preview and same-name JSON metadata.",
    )
    mode.add_argument(
        "--map",
        action="store_true",
        help="Map an input image to a palette JSON using the default posterisation technique.",
    )

    parser.add_argument(
        "-c",
        "--colors",
        "--color",
        dest="color",
        default=None,
        help="Seed color encoded as hexadecimal #RRGGBB. If omitted during palette generation, a random seed is used.",
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
        default=None,
        help="Number of colors to generate. Defaults to 5.",
    )
    parser.add_argument(
        "--input-image",
        type=Path,
        default=None,
        help="Input image path used with --map.",
    )
    parser.add_argument(
        "--palette",
        type=Path,
        default=None,
        help="Palette JSON path used with --map.",
    )
    parser.add_argument(
        "--image-mapping",
        choices=image_mapping_names(),
        default=DEFAULT_IMAGE_MAPPING_NAME,
        help=(
            "Image mapper used with --map. "
            f"Defaults to {DEFAULT_IMAGE_MAPPING_NAME}."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path. Defaults to palettes/palette.png for --generate-palette and outputs/mapped.png for --map.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print generation or mapping details.",
    )
    return parser


def generate_palette_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    palette_size = args.palette_size or 5
    output_path = args.output or Path("palettes/palette.png")

    try:
        seed_color = normalize_hex_color(args.color) if args.color else generate_random_hex_color()
        palette = generate_palette(
            seed_color=seed_color,
            hue_step=args.hue_step,
            saturation_step=args.saturation_step,
            brightness_step=args.brightness_step,
            palette_size=palette_size,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.verbose:
        print(
            "Color palette from seed "
            f"{seed_color}, hue step {args.hue_step}, saturation step {args.saturation_step}, "
            f"brightness step {args.brightness_step}, and size {palette_size}"
        )

    image_path, json_path = save_palette_outputs(
        palette=palette,
        seed_color=seed_color,
        hue_step=args.hue_step,
        saturation_step=args.saturation_step,
        brightness_step=args.brightness_step,
        palette_size=palette_size,
        output_path=output_path,
    )

    if args.verbose:
        print(f"Color palette generated = {palette}. Saved to {image_path} and {json_path}")


def map_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.input_image is None:
        parser.error("--map requires --input-image")
    if not args.input_image.is_file():
        parser.error(f"input image missing: {args.input_image}")
    if args.palette is None:
        parser.error("--map requires --palette")
    if not args.palette.is_file():
        parser.error(f"palette missing: {args.palette}")
    try:
        palette_data = load_palette_json(args.palette)
        colors = palette_data["colors"]
        palette_size = palette_data["palette_size"]
        if len(colors) != palette_size:
            raise ValueError(f"Palette contains {len(colors)} colors, but palette size is {palette_size}.")

        output_path = args.output or Path("outputs/mapped.png")
        mapped_path = map_image_with_palette(
            input_image=args.input_image,
            palette=colors,
            palette_size=palette_size,
            output_path=output_path,
            image_mapping=create_image_mapping(args.image_mapping),
        )
    except ValueError as error:
        parser.error(str(error))

    if args.verbose:
        print(
            f"Mapped {args.input_image} with palette {args.palette}, "
            f"palette size {palette_size}, image mapping {args.image_mapping}. Saved to {mapped_path}"
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.generate_palette:
        generate_palette_command(args, parser)
    elif args.map:
        map_command(args, parser)


if __name__ == "__main__":
    main()
