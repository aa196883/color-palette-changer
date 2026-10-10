# Project guide

## Goals

Generate color palettes in OKlab, export PNG previews and reusable JSON, and
recolor images through a CLI and a local web interface. Keep both interfaces
compatible with the same palette files and shared processing code.

## Architecture

- `main.py`: argparse CLI for palette generation and image mapping.
- `app.py`: Flask app factory, REST API, uploads, drafts, and saved resources.
- `templates/index.html`, `static/`: browser interface using plain JS and CSS.
- `palette_generation.py`, `oklab.py`: seed normalization, palette stepping,
  and color-space conversions.
- `palette.py`: validated immutable `Pallette` model (existing spelling).
- `image_processing.py`: grayscale and OKlab cluster mappings and RGB output.
- `image_mapping_cache.py`: persistent NumPy preprocessing cache.
- `utils.py`: palette PNG/JSON serialization and loading.
- `tests/`: pytest coverage for the CLI, web API, generation, mapping, and cache.
- `inputs/` and `assets/`: source images and committed examples. Generated
  `palettes/`, `outputs/`, and `.cache/` are ignored by Git.

## Useful commands

Run from the project root with the project virtual environment activated.
On Windows, you can replace `python` with `.venv\Scripts\python.exe`.

```sh
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
python app.py
python main.py --help
python main.py --generate-palette -c "#336699" -L 0.08 -p 5 -o palettes/demo.png
python main.py --map --input-image lenna.png --palette palettes/demo.json --image-mapping grayscaled
python main.py --map --input-image lenna.png --palette palettes/demo.json --image-mapping oklab-clusters
```

The web interface runs at `http://127.0.0.1:5000`. For isolated web tests, use
`create_app({"TESTING": True, "DATA_DIR": tmp_path})`.

## Invariant behaviors

- Palette samples follow `seed + (i - (N - 1) / 2) * step` in OKlab. Fixed
  seed, steps, and size produce deterministic colors. Odd sizes include the
  central seed; even sizes straddle it. A seed is a hex color, not an RNG seed.
- CLI/API steps default to zero; the GUI initially uses lightness `0.08` and
  chromatic steps `0.02`. Clip out-of-gamut RGB channels and retain duplicate
  colors; palette size counts entries, not unique colors.
- Palette JSON retains `colors`, `seed`, `color_space`, `step_values`, and
  `palette_size`. Generation writes a PNG and same-stem JSON. Web exports use
  the same JSON format as the CLI.
- Keep mapping names `grayscaled` (default) and `oklab-clusters`. Preprocessing
  is deterministic; both modes randomly visit labels and greedily assign
  distinct palette indices. Rerolls can produce the same appearance.
- Cache only image-dependent intermediates, never final palette assignments.
  CLI cache keys use image basename, mapping name, and palette size; they do
  not detect changed image content. Web mapping bypasses this cache. Load
  NumPy cache files with `allow_pickle=False`.
- CLI paths are relative to the working directory; relative input image paths
  resolve under `inputs/`. Web storage defaults to the directory of `app.py`.
- Web generation/mapping creates drafts in `.cache/web-drafts/`; explicit
  saves add them to the library. Uploads immediately become RGB PNG inputs.
  Saved resources survive restarts, and drafts do not expire automatically.
- Keep web file access confined to resource directories, return JSON errors,
  and preserve upload/image limits. The server runs on localhost without debug.

Keep changes focused, run relevant pytest coverage for behavior changes, and
update the README when public commands or behavior change. See `README.md` for
the full API, algorithms, and cache limitations.
