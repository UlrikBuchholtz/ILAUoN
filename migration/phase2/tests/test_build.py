"""Fast fail-closed runner tests; no TeX, Node, or network required."""

import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class BuildTests(unittest.TestCase):
    def test_standard_project_and_pin(self):
        from pretext.project import Project
        project = Project.parse(ROOT / 'project.ptx')
        self.assertEqual([t.name for t in project.targets], ['html', 'print', 'accessible'])
        self.assertEqual(project.targets[0].stringparams, {'debug.rs.version': BUILD.RUNESTONE})
        self.assertEqual(project.source, BUILD.PILOT / 'source')
        self.assertEqual(project.xsl, BUILD.PILOT / 'xsl')
        publication = ET.parse(ROOT / 'publication/publication.ptx')
        self.assertEqual(publication.find('html/baseurl').get('href'), 'https://ulrikbuchholtz.dk/ila/')

    def test_blocking_diagnostics(self):
        for message in ['\x1b[31merror: \x1b[0mzero-exit failure', 'Overfull \\hbox',
                        'alternate text is missing', 'Failed to download all Runestone Services files',
                        'WARNING: unsupported font table', 'Traceback (most recent call last):']:
            self.assertTrue(BUILD.blocking_diagnostics(message), message)
        self.assertEqual(BUILD.blocking_diagnostics(
            'Completed without errors.\nMessages: logs/schema-errors.log\nwarning: Now generating QR codes'), [])

    def test_asset_gate_and_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'index.html').write_text('<script src="a.js?v=123"></script><link href="a.css">')
            (root / 'a.js').write_text('true;')
            (root / 'a.css').write_text('p { background: url("icon.svg#id") }')
            with self.assertRaisesRegex(ValueError, 'icon.svg'):
                BUILD.check_assets(root)
            (root / 'icon.svg').write_text('<svg/>')
            (root / '._a.css').write_bytes(b'\x00\x05\x16\x07\xa3')
            self.assertEqual(BUILD.check_assets(root), 3)
            (root / 'a.js').write_text('')
            with self.assertRaisesRegex(ValueError, 'a.js'):
                BUILD.check_assets(root)

    def test_asset_escape_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'index.html').write_text('<img src="%2e%2e/outside.png">')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                BUILD.check_assets(root)
            (root / 'index.html').write_text('<img src="https://example.org/x.png">')
            self.assertEqual(BUILD.check_assets(root), 0)
            (root / 'link').symlink_to(root / 'index.html')
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                BUILD.hashes(root)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                BUILD.check_assets(root)

    def test_existing_run_and_repository_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            args = argparse.Namespace(run=Path(temp))
            with self.assertRaises(FileExistsError):
                BUILD.build(args)
        with self.assertRaisesRegex(ValueError, 'outside'):
            BUILD.build(argparse.Namespace(run=ROOT / 'output/new'))

    def test_failure_stops_before_validation_and_reports(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            args = argparse.Namespace(run=run, demo_dependencies=Path(temp), timeout=1, accessible=False)
            with patch.object(BUILD.subprocess, 'Popen', side_effect=OSError('cannot execute node')) as popen:
                with self.assertRaisesRegex(OSError, 'cannot execute'):
                    BUILD.build(args)
                self.assertEqual(popen.call_count, 1)
            report = json.loads((run / 'report.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual([step['name'] for step in report['steps']], ['demos'])
            self.assertFalse((run / 'output').exists())

    def test_runestone_asset_gate(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'html'
            static = output / '_static'
            (static / 'pretext').mkdir(parents=True)
            (static / 'runestone.js').write_text('bundle;')
            (static / '_runestone-services.xml').write_text('<all/>')
            # Resources from the pinned CLI are not Runestone content.
            (static / 'pretext' / 'theme.css').write_text('p {}')
            manifest = Path(temp) / 'runestone-assets.json'

            recorded = BUILD.check_runestone(output, manifest, record=True)
            self.assertEqual(recorded['recorded'], 2)
            self.assertEqual(BUILD.check_runestone(output, manifest), {'verified': 2})

            (static / 'pretext' / 'theme.css').write_text('p { color: red }')
            self.assertEqual(BUILD.check_runestone(output, manifest), {'verified': 2})

            (static / 'runestone.js').write_text('tampered;')
            with self.assertRaisesRegex(ValueError, 'changed'):
                BUILD.check_runestone(output, manifest)
            (static / 'runestone.js').write_text('bundle;')
            (static / 'extra.js').write_text('surprise;')
            with self.assertRaisesRegex(ValueError, 'added'):
                BUILD.check_runestone(output, manifest)
            (static / 'extra.js').unlink()
            (static / '_runestone-services.xml').unlink()
            with self.assertRaisesRegex(ValueError, 'removed'):
                BUILD.check_runestone(output, manifest)

            manifest.write_text(json.dumps({'version': '0.0.0', 'files': {}}))
            with self.assertRaisesRegex(ValueError, '0.0.0'):
                BUILD.check_runestone(output, manifest)
            manifest.unlink()
            with self.assertRaisesRegex(ValueError, 'record it'):
                BUILD.check_runestone(output, manifest)

    def test_accepted_diagnostics_are_exact(self):
        # Both accepted lines are still recognised as diagnostics in the first place.
        self.assertTrue(BUILD.blocking_diagnostics(BUILD.ACCEPTED_FOP_WARNING))
        self.assertTrue(BUILD.blocking_diagnostics(BUILD.ACCEPTED_PORT_COLLISION))
        self.assertIn('8888', BUILD.ACCEPTED_PORT_COLLISION)

    def test_recorded_runestone_manifest(self):
        import json
        recorded = json.loads((ROOT / BUILD.RUNESTONE_ASSETS).read_text())
        self.assertEqual(recorded['version'], BUILD.RUNESTONE)
        self.assertTrue(recorded['files'])
        self.assertTrue(all(len(digest) == 64 for digest in recorded['files'].values()))


if __name__ == '__main__':
    unittest.main()
