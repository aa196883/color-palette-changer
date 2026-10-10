import io
import json

import pytest
from PIL import Image

from app import create_app
from palette_generation import generate_palette


@pytest.fixture
def client(tmp_path):
    app = create_app({'TESTING': True, 'DATA_DIR': tmp_path})
    with app.test_client() as client:
        yield client


def generate(client, **kwargs):
    response = client.post('/api/palettes', json=kwargs)
    assert response.status_code == 201
    result = response.headers['X-Palette-ID'], response.json
    response.close()
    return result


def upload(client):
    stream = io.BytesIO()
    image = Image.new('RGB', (3, 2))
    image.putdata([(0, 0, 0), (128, 128, 128), (255, 255, 255)] * 2)
    image.save(stream, format='PNG')
    stream.seek(0)
    response = client.post('/api/images', data={'image': (stream, '../../example.png')})
    assert response.status_code == 201
    return response.json


def test_gui_and_assets(client):
    assert b'Palette Studio' in client.get('/').data
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/static/style.css').status_code == 200


def test_palette_format_determinism_save_and_download(client, tmp_path):
    identifier, data = generate(client, seed='#336699', palette_size=5, lightness_step=0.08)
    assert set(data) == {'colors', 'seed', 'color_space', 'step_values', 'palette_size'}
    assert data['colors'] == generate_palette('#336699', lightness_step=0.08)
    assert data['step_values'] == {'lightness': 0.08, 'a': 0.0, 'b': 0.0}
    assert client.get('/api/palettes').json == {'palettes': []}
    response = client.get(f'/api/palettes/{identifier}?download=1')
    assert response.json == data
    assert 'attachment' in response.headers['Content-Disposition']
    response.close()
    for _ in range(2):
        assert client.post(f'/api/palettes/{identifier}/save').json['saved']
    assert client.get('/api/palettes').json['palettes'][0]['id'] == identifier
    assert json.loads((tmp_path / 'palettes' / f'{identifier}.json').read_text()) == data
    assert (tmp_path / 'palettes' / f'{identifier}.png').is_file()


def test_random_seed_is_recorded(client, monkeypatch):
    monkeypatch.setattr('app.generate_random_hex_color', lambda: '#abcdef')
    _, data = generate(client)
    assert data['seed'] == '#abcdef'


@pytest.mark.parametrize('mode', ['grayscaled', 'oklab-clusters'])
def test_upload_map_reroll_save_and_retrieve(client, tmp_path, mode):
    identifier, palette = generate(client, seed='#336699', palette_size=3, lightness_step=0.2)
    source = upload(client)
    payload = {'palette_id': identifier, 'image_id': source['id'], 'image_mapping': mode}
    first = client.post('/api/mappings', json=payload)
    assert first.status_code == 201
    second = client.post('/api/mappings', json=payload)
    assert first.json['id'] != second.json['id']
    assert len(client.get('/api/images').json['images']) == 1
    response = client.get(first.json['url'])
    result = Image.open(io.BytesIO(response.data))
    response.close()
    assert result.size == (3, 2)
    allowed = {tuple(bytes.fromhex(color[1:])) for color in palette['colors']}
    assert {result.getpixel((x, y)) for x in range(3) for y in range(2)} <= allowed
    saved = client.post(f"/api/images/{first.json['id']}/save").json
    assert saved['id'].startswith('outputs:') and saved['saved']
    assert len(client.get('/api/images').json['images']) == 2
    download = client.get(saved['url'] + '?download=1')
    assert download.status_code == 200
    assert 'attachment' in download.headers['Content-Disposition']
    download.close()
    # Library and IDs survive an app restart.
    other = create_app({'TESTING': True, 'DATA_DIR': tmp_path}).test_client()
    assert len(other.get('/api/images').json['images']) == 2


@pytest.mark.parametrize('payload', [[], None, {'seed': 5}, {'seed': 'bad'},
    {'palette_size': True}, {'palette_size': 0}, {'palette_size': 257},
    {'lightness_step': 'bad'}, {'lightness_step': float('inf')}, {'blue_yellow_step': 2}])
def test_bad_palette_requests(client, payload):
    response = client.post('/api/palettes', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    assert 'error' in response.json


def test_invalid_upload_and_mapping(client):
    assert client.post('/api/images').status_code == 400
    assert client.post('/api/images', data={'image': (io.BytesIO(b'bad'), 'test.png')}).status_code == 400
    assert client.post('/api/mappings', json={}).status_code == 400
    assert client.post('/api/mappings', json={'palette_id': 'missing', 'image_id': 'inputs:x.png'}).status_code == 404
    assert client.post('/api/palettes', data='{', content_type='application/json').status_code == 400


def test_file_access_is_confined(client, tmp_path):
    (tmp_path / 'private.json').write_text('{"secret": true}')
    for path in ['/api/palettes/..%5Cprivate', '/api/images/inputs:..%5Cprivate.json',
                 '/api/images/drafts:private.json', '/api/images/unknown:test.png']:
        response = client.get(path)
        assert response.status_code == 404
        assert 'error' in response.json


def test_existing_cli_files_are_listed(client, tmp_path):
    Image.new('RGB', (2, 2)).save(tmp_path / 'inputs' / 'existing.png')
    (tmp_path / 'palettes' / 'existing.json').write_text(json.dumps({'colors': ['#112233'], 'palette_size': 1}))
    (tmp_path / 'palettes' / 'broken.json').write_text('bad')
    assert client.get('/api/palettes').json['palettes'][0]['id'] == 'existing'
    assert client.get('/api/images').json['images'][0]['id'] == 'inputs:existing.png'


def test_upload_limits(tmp_path):
    client = create_app({'TESTING': True, 'DATA_DIR': tmp_path, 'MAX_IMAGE_PIXELS': 1}).test_client()
    stream = io.BytesIO()
    Image.new('RGB', (2, 2)).save(stream, format='PNG')
    stream.seek(0)
    assert client.post('/api/images', data={'image': (stream, 'large.png')}).status_code == 400
    client.application.config['MAX_CONTENT_LENGTH'] = 4
    response = client.post('/api/palettes', data='{"seed":null}', content_type='application/json')
    assert response.status_code == 413 and 'error' in response.json
