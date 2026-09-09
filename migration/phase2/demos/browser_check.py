"""Optional Playwright startup check of every generated demo, served locally."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--width', type=int, default=1000)
    parser.add_argument('--pages', nargs='+', help='Optional demo stems; defaults to all')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(
        QuietHandler, directory=str(args.output.resolve())))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=[
                '--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader',
                '--enable-unsafe-swiftshader',
            ])
            for html in sorted((args.output / 'demos').glob('*.html')):
                if args.pages and html.stem not in args.pages:
                    continue
                page = browser.new_page(viewport={'width': args.width, 'height': 800})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: errors.append(
                    f'HTTP {response.status}: {response.url}') if response.status >= 400 else None)
                page.goto(f'http://127.0.0.1:{server.server_port}/demos/{html.name}')
                page.wait_for_timeout(1500)
                if html.stem == 'rrinter':
                    page.locator('textarea').fill('1,2,3\n4,5,6')
                    page.get_by_role('button', name='Use this matrix').click()
                    page.wait_for_url('**/rrinter.html?mat=*')
                    page.locator('canvas').wait_for()
                    page.locator('.row-swap .row-selector').nth(0).get_by_text('1').click()
                    page.locator('.row-swap .row-selector').nth(1).get_by_text('2').click()
                    page.get_by_role('button', name='Swap rows').click()
                    page.wait_for_timeout(1500)
                elif html.stem == 'rabbits':
                    for name, value in [('zero', '10'), ('one', '20'), ('two', '30')]:
                        page.locator(f'#{name}_input').fill(value)
                    page.get_by_role('button', name='Advance 1 year').click()
                    values = [page.locator(f'#{name}_input').input_value()
                              for name in ['zero', 'one', 'two']]
                    if values != ['360', '5', '10'] or not page.locator('#plot svg').count():
                        errors.append(f'Rabbit iteration/plot failed: {values}')
                if html.stem != 'rabbits' and not page.locator('canvas').count():
                    errors.append('No visualization canvas')
                results.append({'page': html.name, 'errors': errors,
                                'canvases': page.locator('canvas').count()})
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    print(json.dumps(results, indent=2))
    raise SystemExit(1 if not results or any(result['errors'] for result in results) else 0)


if __name__ == '__main__':
    main()
