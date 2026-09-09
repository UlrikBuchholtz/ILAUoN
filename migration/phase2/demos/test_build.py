"""Integration tests: python -m unittest discover -s migration/phase2/demos -v."""

import hashlib
from html.parser import HTMLParser
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('build_demos', ROOT / 'scripts/build_demos.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.scripts = []
        self.inline = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'img', 'link'):
            self.urls.extend(attrs[key] for key in ('src', 'href') if key in attrs)
        self.inline = tag == 'script' and 'src' not in attrs

    def handle_endtag(self, tag):
        if tag == 'script':
            self.inline = False

    def handle_data(self, data):
        if self.inline:
            self.scripts.append(data)


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='ila-demo-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name) / 'first'
        cls.dependencies = Path(os.environ.get('DEMO_DEPENDENCIES', BUILDER.TOOLS)).resolve()
        BUILDER.build(cls.output, cls.dependencies)

    def test_legacy_inventory(self):
        legacy = (ROOT / 'demos/SConscript').read_text()
        # Read the final Split block (the preceding block defines CoffeeScript libraries).
        names = re.findall(r"for src in Split\('''(.*?)'''\):", legacy, re.S)[-1].split()
        self.assertEqual(set(names), set(BUILDER.DEMOS))
        self.assertEqual({p.stem for p in (self.output / 'demos').glob('*.html')},
                         set(names) | {'rabbits', 'cover'})
        self.assertEqual((self.output / 'images/logo.png').read_bytes(),
                         (ROOT / 'static/theme-duke/logo.png').read_bytes())

    def test_html_assets_and_javascript(self):
        for html in self.output.rglob('*.html'):
            parser = Assets()
            parser.feed(html.read_text())
            for url in parser.urls:
                parsed = urlsplit(url)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                asset = (html.parent / unquote(parsed.path)).resolve()
                self.assertTrue(asset.is_relative_to(self.output), (html, url))
                self.assertTrue(asset.is_file(), (html, url))
                if parsed.query.startswith('vers='):
                    data = asset.read_bytes()
                    digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data)
                    self.assertEqual(parsed.query, 'vers=' + digest.hexdigest()[:6])
            for script in parser.scripts:
                subprocess.run(['node', '--check'], input=script, text=True, check=True,
                               capture_output=True)
        for script in self.output.rglob('*.js'):
            subprocess.run(['node', '--check', str(script)], check=True, capture_output=True)

    def test_repeat_and_preserve_existing_output(self):
        other = Path(self.temp.name) / 'second'
        dependencies = Path(self.temp.name) / 'alternate-dependencies'
        dependencies.mkdir()
        for name in ['package.json', 'package-lock.json']:
            (dependencies / name).write_bytes((self.dependencies / name).read_bytes())
        (dependencies / 'node_modules').symlink_to(self.dependencies / 'node_modules',
                                                   target_is_directory=True)
        BUILDER.build(other, dependencies)
        def hashes(root):
            return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob('*') if p.is_file()}
        self.assertEqual(hashes(self.output), hashes(other))
        with self.assertRaises(ValueError):
            BUILDER.build(self.output, self.dependencies)
        (dependencies / 'package-lock.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'differs'):
            BUILDER.build(Path(self.temp.name) / 'mismatched-lock', dependencies)

    def test_css_assets(self):
        for css in self.output.rglob('*.css'):
            for url in re.findall(r'url\(([^)]+)\)', css.read_text()):
                parsed = urlsplit(url.strip(' \"\''))
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                asset = (css.parent / unquote(parsed.path)).resolve()
                self.assertTrue(asset.is_relative_to(self.output), (css, url))
                self.assertTrue(asset.is_file(), (css, url))
                self.assertGreater(asset.stat().st_size, 0, (css, url))

    def test_rabbits_unused_glyphicons(self):
        original = (ROOT / 'demos/vendor/bootstrap.css').read_text()
        generated = (self.output / 'demos/css/rabbits.css').read_text()
        start = original.index('@font-face {')
        end = original.index('.caret {', start)
        self.assertEqual(generated, original[:start] + original[end:] + '\n')
        self.assertIn('glyphicons-halflings-regular.eot', original)
        self.assertNotIn('Glyphicons Halflings', generated)
        self.assertNotIn('glyphicons-halflings', generated)
        self.assertNotIn('.glyphicon {', generated)
        for consumer in ['demos/rabbits.html', 'demos/js/rabbits.js']:
            self.assertNotIn('glyphicon', (self.output / consumer).read_text().lower())
        with self.assertRaisesRegex(RuntimeError, 'uses glyphicons'):
            BUILDER.rabbits_css(original, ['<span class="glyphicon glyphicon-plus"></span>'])
        with self.assertRaisesRegex(RuntimeError, 'module changed'):
            BUILDER.rabbits_css(original.replace('Glyphicons Halflings', 'Other Icons'), [''])

    def test_untracked_sources_are_not_staged(self):
        repo = Path(self.temp.name) / 'fixture'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        (repo / 'source.coffee').write_text('answer = 42\n')
        (repo / 'prebuilt.js').write_text('throw "not a build input";\n')
        subprocess.run(['git', '-C', str(repo), 'add', 'source.coffee'], check=True)
        stage = Path(self.temp.name) / 'stage'
        BUILDER.stage_tracked(repo, stage, ['.'])
        self.assertEqual([p.name for p in stage.iterdir()], ['source.coffee'])


if __name__ == '__main__':
    unittest.main()
