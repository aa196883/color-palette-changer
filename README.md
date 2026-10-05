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

## Generate a Palette

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

### Seed Position and Stepping

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
| `oklab-clusters` | Convert pixels to OKlab and run deterministic k-means, with up to `N` clusters, limited by the number of unique colors. | Squared Euclidean distance between each cluster center and palette colors in OKlab. |

K-means starts from evenly spaced indices in the sorted unique OKlab colors, uses at most 20 iterations, and stops early when labels stop changing. Its initialization does not use randomness.

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
| `oklab-clusters` | `(height, width, 4)`, `float32` | Cluster label in channel 0 and that cluster's OKlab center `(L, a, b)` in channels 1–3, repeated for each pixel. A one-color palette stores zeros. |

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
