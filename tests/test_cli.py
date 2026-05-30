import json
from pathlib import Path

import pytest
from PIL import Image

from image_processing import HueImageMapping
from main import build_parser, default_mapped_output_path, generate_palette_command, map_command


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
    assert args.image_mapping == "grayscaled"


def test_map_image_mapping_cli_inputs() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--map",
            "--input-image",
            "input.png",
            "--palette",
            "palette.json",
            "--image-mapping=hue",
        ]
    )

    assert args.image_mapping == "hue"


def test_help_lists_image_mapping_option(capsys) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])

    help_text = capsys.readouterr().out
    assert "--image-mapping" in help_text
    assert "grayscaled" in help_text
    assert "hue" in help_text
    assert "hsl-clusters" in help_text
    assert "outputs/{input_image}--{palette}--{image_mapping}.png" in help_text


def test_default_mapped_output_path_uses_input_palette_and_mapping_stems() -> None:
    output_path = default_mapped_output_path(
        input_image=Path("images/lenna.png"),
        palette=Path("palettes/warm.json"),
        image_mapping="hsl-clusters",
    )

    assert output_path == Path("outputs/lenna--warm--hsl-clusters.png")


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
        ]
    )

    with pytest.raises(SystemExit):
        map_command(args, parser)


def test_map_rejects_palette_size_that_does_not_match_colors(tmp_path) -> None:
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
            "-o",
            str(output_path),
        ]
    )

    map_command(args, parser)

    assert output_path.is_file()


def test_map_command_uses_selected_image_mapping(tmp_path, monkeypatch) -> None:
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
            "--image-mapping=hue",
            "-o",
            str(output_path),
        ]
    )
    captured = {}

    def fake_map_image_with_palette(**kwargs):
        captured.update(kwargs)
        return output_path

    monkeypatch.setattr("main.map_image_with_palette", fake_map_image_with_palette)

    map_command(args, parser)

    assert isinstance(captured["image_mapping"], HueImageMapping)
