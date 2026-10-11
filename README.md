# Color Palette Changer

Color Palette Changer generates color palettes in OKlab space and maps those palettes onto input images.

Generate a palette as a PNG preview and reusable JSON definition, then recolor an image using brightness levels (`grayscaled`) or OKlab color clusters (`oklab-clusters`).

## File Layout

| Location | Purpose |
| --- | --- |
| `inputs/` | Source images: `lenna.png` and `witch_shelf.png`. |
| `palettes/` | Generated palette PNG previews and JSON definitions. |
| `outputs/` | Recolored images. |
| `.cache/` | Reusable NumPy image mapping intermediates. |
| `assets/` | Committed examples displayed below. |
| `tests/` | Automated tests. |

CLI relative paths are based on the current working directory. Generated `palettes/`, `outputs/`, and `.cache/` files are ignored by Git.

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## GUI and REST API

After installing the dependencies, start the local GUI:

```bash
python app.py
```

Open **http://127.0.0.1:5000**. Generate from a hex seed or leave it blank for
a random seed. Choose Analogous or Complementary generation and adjust the
palette size. Analogous uses the OKlab steps; Complementary disables them and
uses seed lightness with a new random line each time. Preview the colors,
then **Save palette** or **Reroll seed**. Choose a palette and an existing image
or upload one, select a mapping method, and preview the result alongside the
original. **Reroll mapping** repeats the last mapping with a fresh randomized
assignment; it can produce the same appearance. **Save image** keeps the result.
Download links export palette JSON and mapped PNG files to your browser.

The GUI uses a lightness step of `0.08` and chromatic steps of `0.02` initially.
The API, like the CLI, defaults all steps to zero. A palette seed is a hex
color, not a numeric random-generator seed.

The web app resolves storage relative to `app.py` (independent of the working
directory). Existing CLI palettes in `palettes/` and images in `inputs/` and
`outputs/` appear automatically. Generated previews live in `.cache/web-drafts/`;
Save copies them into `palettes/` or `outputs/`. Only saved items appear in the
library. Uploaded images are immediately stored in `inputs/` as RGB PNGs with
unique names. Drafts remain available by ID until you remove their files; they
are not automatically expired. You can clear `.cache/web-drafts/` when no longer
using previews. Saved resources survive application restarts.

### REST endpoints

All errors return JSON with an `error` message and an appropriate HTTP status.
POST bodies are JSON except for image uploads. IDs are opaque; use the returned
IDs and URLs rather than constructing filesystem paths.

| Method and path | Behavior |
| --- | --- |
| `GET /api/palettes` | Saved palettes as `{ "palettes": [...] }`, including IDs, colors, sizes and URLs. |
| `POST /api/palettes` | Generate a draft. Returns `201` and a JSON attachment in the **unchanged CLI format**. ID is in `X-Palette-ID`; resource URL is in `Location`. |
| `GET /api/palettes/<id>` | Original palette JSON. Add `?download=1` for an attachment. |
| `POST /api/palettes/<id>/save` | Save a draft's JSON and PNG preview; returns its library record. Safe to repeat. |
| `GET /api/images` | Existing inputs and saved outputs as `{ "images": [...] }`, with IDs, names and URLs. |
| `POST /api/images` | Upload using multipart field `image`; returns `201` and an image record. |
| `GET /api/images/<id>` | Image bytes. Add `?download=1` for an attachment. |
| `POST /api/mappings` | Recolor an image using a palette ID; returns `201` and a draft image record. Repeat to reroll. |
| `POST /api/images/<id>/save` | Save a mapped draft to `outputs/`; returns its saved image record with a new ID/URL. |

Palette generation body (every field is optional):

```json
{
  "mode": "analogous",
  "seed": "#336699",
  "palette_size": 5,
  "lightness_step": 0.08,
  "green_red_step": 0.02,
  "blue_yellow_step": 0.02
}
```

`mode` accepts `analogous` (default) or `complementary`. Complementary ignores
step values during generation. Omit `seed`, send `null`, or send an empty string for a random seed. The response
records the chosen seed. Palette sizes range from 1 to 256; steps must be finite
numbers from -1 to 1. The web app accepts uploads up to 16 MiB and mapping images
up to 4 million pixels. Large OKlab clustering jobs may take time; requests are
synchronous. Web mappings use the same basename-keyed cache pipeline as the CLI,
so repeated mappings reuse preprocessing for the same image and palette size.

Mapping body (upload first and use its returned ID for a new image):

```json
{
  "palette_id": "ID_FROM_GENERATION_OR_LIBRARY",
  "image_id": "inputs:lenna.png",
  "image_mapping": "oklab-clusters"
}
```

`image_mapping` defaults to `grayscaled`. A draft palette can be used immediately
without saving it first. The server binds to localhost without debug mode and is
intended for local use. For tests, `create_app({"DATA_DIR": temporary_directory,
"TESTING": True})` isolates storage.

Run the automated suite with `python -m pip install pytest` followed by
`python -m pytest -q`.

## Generate a Palette (CLI)

Generate a 16-color palette preview and JSON metadata:

```bash
python main.py --generate-palette -L -0.01 -a -0.0 -b 0.125 -p 16 -o palettes/test_3.png
```

This command writes:

- `palettes/test_3.png`: visual palette preview.
- `palettes/test_3.json`: palette metadata used by the mapper.

You can also provide a fixed seed color:

```bash
python main.py --generate-palette -c "#336699" -L 0.0 -a 0.1 -b 0.0 -p 10 -o palettes/blue_ramp.png
```

### Complementary Line Mode

`--mode analogous` is the default and preserves the existing seed-and-step
generation. Use `--mode complementary` to sample a randomly offset straight line
in the OKlab green-red (`a`) / blue-yellow (`b`) plane:

```bash
python main.py --generate-palette --mode complementary -c "#336699" -p 4 -o palettes/complementary.png
```

The seed supplies a constant lightness. Randomly choose `a` or `b` as the x axis
and cover its full normalized range `[-1, 1]`. Draw a slope `m` uniformly from
`[-1, 1]`, then an origin (y intercept) `c` uniformly from
`[-(1 - abs(m)), 1 - abs(m)]`. The line is `y = m*x + c`; this origin range keeps
the other coordinate inside `[-1, 1]` without requiring it to span that range.
Multiply both coordinates by `0.4` to use the existing OKlab working square.
The line need not pass through neutral; the square is not an sRGB gamut boundary.

For `N` colors, divide the line into `N + 1` equal segments and use the `N`
interior boundaries, excluding the outer endpoints. This gives equal spacing
along the line before RGB conversion. Odd sizes include the line's midpoint
`(0, c)` in the chosen coordinates; size one produces just that midpoint.

The `-L`, `-a`, and `-b` step options are ignored in complementary mode. The
axis, slope, and origin are randomized on each call, even with a fixed seed color. Existing
RGB clipping still applies and can distort spacing or create duplicates.
This straight-line method does not guarantee a triadic or square
arrangement around a hue circle. In the web interface, select Complementary
under Generation mode; Analogous remains the default.

PNG and JSON exports remain compatible with existing mappers. The JSON stores
the resulting colors in the existing schema; it does not record the random
line parameters or mode, so seed and step metadata alone cannot recreate a
complementary palette. Reuse its saved `colors` instead.

### Seed Position and Stepping (Analogous Mode)

The seed is the **middle of a straight line of samples in OKlab**, rather than an endpoint. The input hex color is normalized, decoded as sRGB, converted to linear RGB, and then converted to OKlab. If no color is supplied, one integer is chosen uniformly from `0x000000` through `0xFFFFFF` and interpreted as an sRGB color; it follows the same conversion and stepping process. This is not uniform sampling of OKlab.

For `N` colors, seed `S = (L, a, b)`, and step `D = (lightness_step, green_red_step, blue_yellow_step)`, each sample is:

```text
sample[i] = S + (i - (N - 1) / 2) * D, for i = 0 ... N - 1
```

- Odd sizes include the seed as the central sample: five colors use offsets `-2, -1, 0, 1, 2` times the step.
- Even sizes straddle the seed: four colors use offsets `-1.5, -0.5, 0.5, 1.5`. There is no sample at the seed itself unless stepping or conversion produces a duplicate.
- Negative steps reverse the direction on their respective axes. All three steps default to zero, so omitting them produces repeated copies of the seed.

The seed and step values describe the intended OKlab samples before conversion to displayable colors. With a fixed seed, steps, and size, palette generation is deterministic. The JSON records `colors`, `seed`, `color_space`, `step_values`, and `palette_size`, including the chosen seed when it was random.

### Out-of-Gamut Colors

OKlab samples are not constrained during stepping. Each sample is converted back to linear RGB, where each channel is independently clipped to `[0, 1]`. The code then applies the sRGB transfer function, clamps again to `[0, 1]`, and rounds each channel to an 8-bit integer for hex output.

This is channel clipping, with no step reduction, resampling, or hue-preserving gamut mapping. Large steps can change the apparent hue, destroy equal spacing, and produce duplicate colors. Duplicates are retained, so the requested palette size counts entries, not necessarily distinct colors. The committed example has several identical `#ff0000` entries for this reason.

## Map an Image

Source images are stored in `inputs/`, including `lenna.png` and `witch_shelf.png`.
Relative `--input-image` paths are resolved inside `inputs/` in the current working directory;
provide the filename without the `inputs/` prefix. Absolute image paths are also supported.

Map an input image with brightness-based mapping:

```bash
python main.py --map --input-image lenna.png --palette palettes/test_3.json --image-mapping grayscaled
```

Map an input image with OKlab clustering:

```bash
python main.py --map --input-image lenna.png --palette palettes/test_3.json --image-mapping oklab-clusters
```

Write to a specific output path:

```bash
python main.py --map --input-image lenna.png --palette palettes/test_3.json --image-mapping oklab-clusters -o outputs/lenna_custom.png
```

The default output is `outputs/{input_image_stem}--{palette_stem}--{image_mapping}.png`. Repeating the command overwrites that path; use different `-o` paths to keep variants. Add `--verbose` to either workflow to print details.

### Mapping Algorithms and Randomness

Both modes first build an image-dependent intermediate, then assign palette entries to its labels:

| Mode | Intermediate construction | Distance used to assign palette colors |
| --- | --- | --- |
| `grayscaled` (default) | Convert to Pillow grayscale and quantize each pixel with `round(gray / 255 * (N - 1))`. | Compare evenly spaced grayscale reference colors to palette colors using OKlab `L` only when palette lightness varies; otherwise use all three OKlab coordinates. |
| `oklab-clusters` | Convert pixels to OKlab, quantize nearby colors, then run deterministic weighted k-means over unique colors, with up to `N` clusters. | Squared Euclidean distance between each cluster center and palette colors in OKlab. |

K-means starts from evenly spaced indices in the sorted, quantized unique OKlab colors, weights each color by its pixel frequency, uses at most 20 iterations, and stops early when labels stop changing. Its initialization does not use randomness.

**Randomness enters during palette assignment in both modes.** The mapper visits labels in a random permutation. Each label greedily claims the nearest remaining palette entry, removing that entry from consideration for later labels. When labels compete for the same entry, changing the visit order can change the result. This enforces distinct palette indices per label, although duplicate RGB entries may still look identical. It is not a global minimum-distance assignment and does not guarantee brightness ordering.

A fresh, unseeded NumPy random generator is used for each assignment in the CLI. Identical inputs and the same palette can therefore produce different outputs, even with a warm cache. Differences are not guaranteed on every run; a one-color palette, for example, always produces the same color. There is currently no CLI random-seed option. Fixing the palette's seed color makes palette generation reproducible but does not fix mapping randomness.

## Persistent Mapping Cache

CLI mapping automatically stores intermediates as `.npy` files in `.cache/` under the current working directory. The filename is:

```text
.cache/{input_basename}--{mapping_name}--{palette_size}.npy
# Example: .cache/lenna.png--oklab-clusters--16.npy
```

The input extension is retained. Characters outside `A-Z`, `a-z`, `0-9`, `_`, `.`, and `-` in the key are replaced with underscores.

| Mode | Stored NumPy array | Contents |
| --- | --- | --- |
| `grayscaled` | `(height, width)`, `uint8` for up to 256 entries, otherwise `int32` | Quantized grayscale labels, before palette assignment. |
| `oklab-clusters` | NPZ with `labels` and `centers` arrays | One integer cluster label per pixel and one OKlab center per cluster. Nearby colors are quantized at `1/256` before clustering. |

On a cache miss, the image is decoded and the intermediate is computed and saved. On a hit, that intermediate is loaded with `allow_pickle=False`, skipping image decoding and preprocessing, including expensive clustering. Palette assignment and RGB output are performed anew on every call. Neither the final color assignment nor the recolored image is stored in this cache.

Intermediates depend on palette size but not on palette colors, so different palettes with the same size reuse the same file for a given image basename and mapping mode. In the Python API, caching is enabled when `map_image_with_palette` receives a non-`None` `palette_json_path`; the CLI always supplies it. That path's value is not part of the cache key.

### Cache Invalidation

The cache key includes no image content hash, directory, modification time, dimensions, or algorithm version/settings. Replacing an image under the same name, using different images with the same basename, or changing preprocessing code can reuse an obsolete intermediate. Sanitized filenames can also collide. There is no automatic freshness check or CLI cache-reset option.

Delete the corresponding `.cache/*.npy` file, or clear `.cache/`, to force preprocessing on the next call. Changing mapping mode or palette size selects a different cache entry. Clearing the cache does not remove palette definitions or output images, and it does not make randomized palette assignment reproducible.

## Command Reference

```text
python main.py (--generate-palette | --map) [options]
```

Palette generation options:

- `--mode`: `analogous` (default) or `complementary` straight-line sampling.
- `-c`, `--color`, `--colors`: seed color as `#RRGGBB`. If omitted, a random seed color is used.
- `-L`, `--lightness-step`: OKlab `L` channel step.
- `-a`, `--green-red-step`: OKlab `a` channel step.
- `-b`, `--blue-yellow-step`: OKlab `b` channel step.
- `-p`, `--palette-size`: number of colors to generate (default: 5).
- `-o`, `--output`: output PNG path (default: `palettes/palette.png`). A same-name JSON file is written beside it.

Image mapping options:

- `--input-image`: source image path relative to `inputs/`, or an absolute path.
- `--palette`: palette JSON file.
- `--image-mapping`: mapping strategy, either `grayscaled` or `oklab-clusters`.
- `-o`, `--output`: output image path. If omitted, the file is written under `outputs/`.

Shared option:

- `-v`, `--verbose`: print additional generation or mapping details.

## Visual Example

The committed palette records seed `#f3b2ac`. Recreate its colors with:

```bash
python main.py --generate-palette -c "#f3b2ac" -L -0.01 -a -0.0 -b 0.125 -p 16 -o palettes/test_3.png
```

The recolored examples illustrate possible assignments; new mapping runs may differ. The committed example files are stored in `assets/`:

- `assets/palette_example.png`
- `assets/palette_example.json`
- `assets/lenna--test_3--grayscaled.png`
- `assets/lenna--test_3--oklab-clusters.png`

### Generated Palette

![Generated 16-color palette](assets/palette_example.png)

### Grayscaled Mapping

This output maps the source image's brightness values to the generated palette.

![Lenna mapped with grayscaled palette mapping](assets/lenna--test_3--grayscaled.png)

### OKlab Cluster Mapping

This output clusters the source image in OKlab space, then maps those clusters to the generated palette.

![Lenna mapped with OKlab cluster palette mapping](assets/lenna--test_3--oklab-clusters.png)
