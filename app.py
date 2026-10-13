"""Local Flask GUI and REST API. Run with ``python app.py``."""
from __future__ import annotations

import math
import re
import shutil
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template, request, send_file, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException

from image_processing import create_image_mapping, map_image_with_palette
from openapi import openapi_document
from palette_generation import augment_palette, generate_palette, generate_random_hex_color, normalize_hex_color
from utils import load_palette_json, save_palette_outputs


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(DATA_DIR=Path(__file__).parent, MAX_CONTENT_LENGTH=16 * 1024 * 1024,
                      MAX_IMAGE_PIXELS=4_000_000)
    app.config.update(config or {})
    root = Path(app.config['DATA_DIR']).resolve()
    folders = {key: root / value for key, value in {
        'palettes': 'palettes', 'inputs': 'inputs', 'outputs': 'outputs',
        'drafts': '.cache/web-drafts'}.items()}
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)

    def find_file(folder, name):
        if not isinstance(name, str) or not name or '/' in name or '\\' in name or ':' in name:
            abort(404, description='Unknown resource ID.')
        path = (folder / name).resolve()
        if path.parent != folder.resolve() or not path.is_file():
            abort(404, description='Resource not found.')
        return path

    def palette_path(identifier):
        name = identifier + '.json'
        folder = folders['palettes'] if (folders['palettes'] / name).is_file() else folders['drafts']
        return find_file(folder, name)

    def image_path(identifier):
        kind, separator, name = identifier.partition(':')
        if not separator or kind not in ('inputs', 'outputs', 'drafts'):
            abort(404, description='Unknown image ID.')
        path = find_file(folders[kind], name)
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff'):
            abort(404)
        return path

    def palette_info(path):
        palette = load_palette_json(path)
        for color in palette.colors:
            normalize_hex_color(color)
        return dict(id=path.stem, colors=palette.colors, palette_size=palette.palette_size,
                    saved=path.parent == folders['palettes'],
                    url=url_for('get_palette', identifier=path.stem))

    def image_info(path, kind):
        identifier = f'{kind}:{path.name}'
        return dict(id=identifier, name=path.name, saved=kind != 'drafts',
                    url=url_for('get_image', identifier=identifier))

    def body():
        data = request.get_json()
        if not isinstance(data, dict):
            abort(400, description='Expected a JSON object.')
        return data

    def optional_save_name():
        data = request.get_json(silent=True)
        if data is None:
            return None
        if not isinstance(data, dict):
            abort(400, description='Expected a JSON object.')
        name = data.get('name')
        if name is None:
            return None
        if not isinstance(name, str) or not name.strip():
            raise ValueError('name must be a non-empty string.')
        name = re.sub(r'\s+', '_', name.strip())
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
            raise ValueError('name may contain only letters, numbers, spaces, dots, underscores, and hyphens.')
        return name.removesuffix('.json')

    def check_image(image):
        if image.width * image.height > app.config['MAX_IMAGE_PIXELS']:
            raise ValueError('Image exceeds the configured pixel limit.')
        image.load()

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(ValueError)
    @app.errorhandler(UnidentifiedImageError)
    @app.errorhandler(Image.DecompressionBombError)
    def invalid_data(error):
        return jsonify(error=str(error)), 400

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/openapi.json')
    @app.get('/api/openapi.json')
    def openapi_spec():
        return jsonify(openapi_document())

    @app.get('/api/palettes')
    def list_palettes():
        items = []
        for path in sorted(folders['palettes'].glob('*.json')):
            if path.is_symlink():
                continue
            try:
                items.append(palette_info(path))
            except (ValueError, OSError, TypeError):
                continue
        return jsonify(palettes=items)

    @app.post('/api/palettes')
    def new_palette():
        data = body()
        mode = data.get('mode', 'analogous')
        if mode not in ('analogous', 'complementary'):
            raise ValueError('mode must be analogous or complementary.')
        size = data.get('palette_size', 5)
        if type(size) is not int or not 1 <= size <= 256:
            raise ValueError('palette_size must be an integer between 1 and 256.')
        seed = data.get('seed')
        if seed is not None and not isinstance(seed, str):
            raise ValueError('seed must be a hex color string or null.')
        seed = normalize_hex_color(seed) if seed else generate_random_hex_color()
        steps = {}
        for name in ('lightness_step', 'green_red_step', 'blue_yellow_step'):
            value = data.get(name, 0.0)
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1:
                raise ValueError(f'{name} must be a finite number between -1 and 1.')
            steps[name] = value
        colors = generate_palette(seed_color=seed, palette_size=size, mode=mode, **steps)
        identifier = uuid4().hex
        _, path = save_palette_outputs(colors, seed, size, folders['drafts'] / f'{identifier}.png', **steps)
        response = send_file(path, mimetype='application/json', as_attachment=True)
        response.status_code = 201
        response.headers['Location'] = url_for('get_palette', identifier=identifier)
        response.headers['X-Palette-ID'] = identifier
        return response

    @app.get('/api/palettes/<identifier>')
    def get_palette(identifier):
        return send_file(palette_path(identifier), mimetype='application/json',
                         as_attachment=request.args.get('download') == '1')

    @app.post('/api/palettes/<identifier>/save')
    def save_palette(identifier):
        path = palette_path(identifier)
        name = optional_save_name() or identifier
        target_json = folders['palettes'] / f'{name}.json'
        target_png = folders['palettes'] / f'{name}.png'
        if path.parent != folders['palettes'] or path != target_json:
            shutil.copy2(path, target_json)
            shutil.copy2(path.with_suffix('.png'), target_png)
        return jsonify(palette_info(target_json))

    @app.post('/api/palettes/<identifier>/augment')
    def augment_palette_route(identifier):
        data = body()
        factor = data.get('factor')
        if type(factor) is not int or factor < 1:
            raise ValueError('factor must be an integer of at least 1.')
        source = load_palette_json(palette_path(identifier))
        if source.palette_size * factor > 256:
            raise ValueError('Augmented palette cannot contain more than 256 colors.')
        steps = {}
        for name in ('lightness_step', 'green_red_step', 'blue_yellow_step'):
            value = data.get(name)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1):
                raise ValueError(f'{name} must be a finite number between -1 and 1.')
            steps[name] = value
        colors, chosen_steps = augment_palette(source.colors, factor, **steps)
        identifier = uuid4().hex
        _, path = save_palette_outputs(
            colors, source.colors[0], len(colors), folders['drafts'] / f'{identifier}.png',
            lightness_step=chosen_steps[0], green_red_step=chosen_steps[1], blue_yellow_step=chosen_steps[2],
        )
        response = send_file(path, mimetype='application/json', as_attachment=True)
        response.status_code = 201
        response.headers['Location'] = url_for('get_palette', identifier=identifier)
        response.headers['X-Palette-ID'] = identifier
        return response

    @app.get('/api/images')
    def list_images():
        items = []
        for kind in ('inputs', 'outputs'):
            for path in sorted(folders[kind].iterdir()):
                if path.is_file() and not path.is_symlink():
                    try:
                        with Image.open(path) as image:
                            check_image(image)
                        items.append(image_info(path, kind))
                    except (OSError, ValueError, Image.DecompressionBombError, UnidentifiedImageError):
                        continue
        return jsonify(images=items)

    @app.post('/api/images')
    def upload_image():
        upload = request.files.get('image')
        if upload is None:
            abort(400, description='Provide an image multipart field.')
        path = folders['inputs'] / f'{uuid4().hex}.png'
        try:
            with Image.open(upload.stream) as image:
                check_image(image)
                image.convert('RGB').save(path)
        except OSError as error:
            raise ValueError('Cannot decode this image.') from error
        return jsonify(image_info(path, 'inputs')), 201

    @app.get('/api/images/<identifier>')
    def get_image(identifier):
        return send_file(image_path(identifier), as_attachment=request.args.get('download') == '1')

    @app.post('/api/mappings')
    def new_mapping():
        data = body()
        for field in ('palette_id', 'image_id'):
            if not isinstance(data.get(field), str):
                raise ValueError(f'{field} is required and must be a string.')
        mode = data.get('image_mapping', 'grayscaled')
        if mode not in ('grayscaled', 'oklab-clusters'):
            raise ValueError('Unknown image_mapping.')
        palette = load_palette_json(palette_path(data['palette_id']))
        if palette.palette_size > 256:
            raise ValueError('Web mapping supports at most 256 colors.')
        for color in palette.colors:
            normalize_hex_color(color)
        source = image_path(data['image_id'])
        with Image.open(source) as image:
            check_image(image)
        output = folders['drafts'] / f'{uuid4().hex}.png'
        map_image_with_palette(
            source,
            palette,
            output,
            create_image_mapping(mode),
            palette_json_path=palette_path(data['palette_id']),
        )
        return jsonify(image_info(output, 'drafts')), 201

    @app.post('/api/images/<identifier>/save')
    def save_image(identifier):
        path = image_path(identifier)
        kind = identifier.split(':', 1)[0]
        if kind == 'drafts':
            shutil.copy2(path, folders['outputs'] / path.name)
            kind = 'outputs'
        return jsonify(image_info(path, kind))

    return app


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the local color palette web application.')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on (default: 5000).')
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error('port must be between 1 and 65535')
    create_app().run(host='127.0.0.1', port=arguments.port)
