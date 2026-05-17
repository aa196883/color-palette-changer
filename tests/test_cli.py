import json

import pytest
from PIL import Image

from main import build_parser, generate_palette_command, map_command


def test_generate_palette_cli_inputs() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--generate-palette",
            "-c",
            "#336699",
            "-H",
            "0.08",
            "-S",
            "0.02",
            "-B",
            "0.05",
            "-p",
            "7",
        ]
    )

    assert args.generate_palette is True
    assert args.map is False
    assert args.color == "#336699"
    assert args.hue_step == 0.08
    assert args.saturation_step == 0.02
    assert args.brightness_step == 0.05
    assert args.palette_size == 7


def test_generate_palette_command_writes_png_and_json(tmp_path) -> None:
    parser = build_parser()
    output = tmp_path / "palette.png"
    args = parser.parse_args(
        [
            "--generate-palette",
            "-c",
            "#336699",
            "-B",
            "0.1",
            "-p",
            "5",
            "-o",
            str(output),
        ]
    )

    generate_palette_command(args, parser)

    json_path = tmp_path / "palette.json"
    assert output.is_file()
    assert json_path.is_file()
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    assert metadata["seed"] == "#336699"
    assert metadata["palette_size"] == 5
    assert len(metadata["colors"]) == 5


def test_map_requires_existing_palette(tmp_path) -> None:
    parser = build_parser()
    image_path = tmp_path / "input.png"
    Image.new("RGB", (2, 2), (128, 128, 128)).save(image_path)
    args = parser.parse_args(
        [
            "--map",
            "--input-image",
            str(image_path),
            "--palette",
            str(tmp_path / "missing.json"),
            "-p",
            "3",
        ]
    )

    with pytest.raises(SystemExit):
        map_command(args, parser)


def test_map_rejects_wrong_palette_size(tmp_path) -> None:
    parser = build_parser()
    image_path = tmp_path / "input.png"
    palette_path = tmp_path / "palette.json"
    Image.new("RGB", (2, 2), (128, 128, 128)).save(image_path)
    palette_path.write_text(
        json.dumps(
            {
                "colors": ["#000000", "#ffffff"],
                "seed": "#336699",
                "step_values": {"hue": 0.0, "saturation": 0.0, "brightness": 0.1},
                "palette_size": 2,
            }
        ),
        encoding="utf-8",
    )
    args = parser.parse_args(
        [
            "--map",
            "--input-image",
            str(image_path),
            "--palette",
            str(palette_path),
            "-p",
            "3",
        ]
    )

    with pytest.raises(SystemExit):
        map_command(args, parser)


def test_map_command_writes_output_image(tmp_path) -> None:
    parser = build_parser()
    image_path = tmp_path / "input.png"
    palette_path = tmp_path / "palette.json"
    output_path = tmp_path / "mapped.png"
    Image.new("RGB", (2, 2), (128, 128, 128)).save(image_path)
    palette_path.write_text(
        json.dumps(
            {
                "colors": ["#000000", "#808080", "#ffffff"],
                "seed": "#336699",
                "step_values": {"hue": 0.0, "saturation": 0.0, "brightness": 0.1},
                "palette_size": 3,
            }
        ),
        encoding="utf-8",
    )
    args = parser.parse_args(
        [
            "--map",
            "--input-image",
            str(image_path),
            "--palette",
            str(palette_path),
            "-p",
            "3",
            "-o",
            str(output_path),
        ]
    )

    map_command(args, parser)

    assert output_path.is_file()
