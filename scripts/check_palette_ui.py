"""Run an isolated browser check and save desktop screenshots in .cache/ui-check."""
import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from utils import save_palette_outputs
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', action='store_true')
    args = parser.parse_args()
    output = Path('.cache/ui-check').resolve()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for index in range(12):
            save_palette_outputs(['#336699', '#d99b66', '#79ac96'], '#336699', 3,
                                 root / 'palettes' / f'Palette_{index:02}_with_a_long_descriptive_name.png')
        server = make_server('127.0.0.1', 0, create_app({'TESTING': True, 'DATA_DIR': root}))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                executables = list((Path(os.environ['LOCALAPPDATA']) / 'ms-playwright').glob('chromium-*/chrome-win*/chrome.exe'))
                browser = playwright.chromium.launch(executable_path=str(executables[-1]) if executables else None)
                page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#augmentation-palette-snapshots button')).to_have_count(12)
                section = page.locator('section').nth(1)
                section.screenshot(path=str(output / ('before.png' if args.before else 'picker.png')))
                if not args.before:
                    assert not page.locator('#augmentation-source').is_visible()
                    assert page.locator('#augmentation-palette-snapshots').evaluate('(el) => el.scrollWidth <= el.clientWidth')
                    page.locator('#seed').fill('#336699')
                    page.locator('#size').fill('2')
                    page.locator('#generate-form button[type=submit]').click()
                    expect(page.locator('#palette-detail')).to_contain_text('2 colors')
                    expect(page.locator('#augmentation-palette-snapshots button')).to_have_count(13)
                    assert page.locator('#augmentation-source').input_value()
                    page.locator('#augmentation-form button[type=submit]').click()
                    expect(page.locator('#augmentation-detail')).to_contain_text('8 colors')
                    expect(page.locator('#swatches .swatch')).to_have_count(2)
                    expect(page.locator('#augmentation-swatches .swatch')).to_have_count(8)
                    expect(page.locator('#palette-snapshots button')).to_have_count(14)
                    page.locator('#augmentation-palette-snapshots button').last.click()
                    expect(page.locator('#augmentation-palette-snapshots .selected')).to_have_count(1)
                    section.screenshot(path=str(output / 'augmented.png'))
                    page.screenshot(path=str(output / 'full-page.png'), full_page=True)
                    assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            thread.join()
    print(f'Browser check passed. Screenshots: {output}')


if __name__ == '__main__':
    main()
