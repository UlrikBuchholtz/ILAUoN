#!/usr/bin/env python3
"""Build the unchanged pilot fixture in a new workspace, never historical output."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PILOT = Path('migration/phase1')
VERSION = '2.52.3'
CORE = '2c8806b9988f855e94d185fb145226bf6c0a5b20'
RUNESTONE = '8.2.10'
RUNESTONE_ASSETS = Path('migration/phase2/runestone-assets.json')
ACCEPTED_FOP_WARNING = '[WARN] GlyphClassTable$CoverageSetClassTable - coverage set class table not yet supported'
# Upstream's preview server prefers port 8888 and its own earlier target still
# holds it; it retries on a random port and continues, so this exact line is
# recovered rather than failed.  Any other port diagnostic stays blocking.
ACCEPTED_PORT_COLLISION = 'debug: http.server error: port 8888 in use; (error [Errno 98] Address already in use)'


def hashes(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink is not an input/artifact: {path}')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def require_file(path):
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f'Missing or empty required artifact: {path}')


def blocking_diagnostics(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    return [line for line in text.splitlines() if re.search(
        r'(^|\s)(error:|critical:|fatal:|\[error\])|PTX:(ERROR|FATAL)|Traceback \(most recent|'
        r'alternate text is missing|exceed the available area|overfull|unsupported|'
        r'not yet supported|failed to|cannot execute', line, re.I)]


def check_assets(root):
    """Check local HTML/CSS assets, not external networks or navigation semantics."""
    root = root.resolve()
    refs = []

    class Assets(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if value and (key in ('src', 'poster', 'data-knowl', 'knowl') or
                              (tag == 'link' and key == 'href') or
                              (tag == 'object' and key == 'data')):
                    refs.append((self.path, value))

    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink in output: {path}')
        # Runestone's archive includes binary AppleDouble resource-fork metadata.
        if path.name.startswith('._'):
            continue
        if path.suffix == '.html':
            parser = Assets()
            parser.path = path
            parser.feed(path.read_text())
            parser.close()
        elif path.suffix == '.css':
            refs.extend((path, url.strip(' \"\'')) for url in
                        re.findall(r'url\(([^)]+)\)', path.read_text()))
    checked = 0
    for source, ref in refs:
        url = urlsplit(ref)
        if url.scheme or url.netloc or not url.path:
            continue
        target = (source.parent / unquote(url.path)).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f'Asset escapes output: {source}: {ref}')
        require_file(target)
        checked += 1
    return checked


def check_runestone(output, manifest, record=False):
    """Compare the fetched Runestone assets against recorded content hashes.

    The version selector alone does not make remote content immutable, so the
    extracted tarball is pinned by content here.  `_static/pretext` is excluded:
    those resources come from the pinned CLI, not from Runestone.
    """
    found = {name: digest for name, digest in hashes(output / '_static').items()
             if not name.startswith('pretext/')}
    if not found:
        raise ValueError('No Runestone assets found to verify')
    if record:
        manifest.write_text(json.dumps(
            {'version': RUNESTONE, 'files': found}, indent=2, sort_keys=True) + '\n')
        return {'recorded': len(found), 'gate': 'not verified in this run'}
    if not manifest.is_file():
        raise ValueError(f'Missing Runestone manifest {manifest}; record it with --record-runestone')
    expected = json.loads(manifest.read_text())
    if expected.get('version') != RUNESTONE:
        raise ValueError(f'Runestone manifest records {expected.get("version")}, not {RUNESTONE}')
    expected = expected['files']
    differences = {
        'added': sorted(set(found) - set(expected)),
        'removed': sorted(set(expected) - set(found)),
        'changed': sorted(name for name in set(expected) & set(found)
                          if expected[name] != found[name]),
    }
    if any(differences.values()):
        raise ValueError('Runestone assets differ from recorded hashes; upstream content '
                         f'changed under version {RUNESTONE}: '
                         + '; '.join(f'{kind} {names[:5]}' for kind, names in differences.items() if names))
    return {'verified': len(found)}


def build(args):
    import pretext

    if (pretext.VERSION, pretext.CORE_COMMIT) != (VERSION, CORE):
        raise ValueError('PreTeXt version/core mismatch; use uv sync --locked')
    run = args.run.resolve()
    if run.is_relative_to(ROOT) or run.is_relative_to(Path.home() / 'tmp/ila/phase0'):
        raise ValueError('Run must be outside the repository and historical phase0 directory')
    run.mkdir(parents=True, exist_ok=False)
    report = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'run': str(run),
              'pretext': VERSION, 'core': CORE, 'runestone': RUNESTONE,
              'python': sys.version, 'steps': [], 'status': 'failed'}
    try:
        for name in ['logs', 'home', 'tmp']:
            (run / name).mkdir()
        environment = os.environ.copy()
        environment.pop('PYTHONPATH', None)
        environment['PATH'] = str(Path(sys.executable).parent) + ':' + environment['PATH']
        environment['HOME'] = str(run / 'home')
        environment['TMPDIR'] = str(run / 'tmp')
        cli = [sys.executable, '-I', '-c',
               "import os; os.environ.pop('LD_PRELOAD', None); from pretext.cli import main; main()",
               '-v', 'debug', '--save-tmp-dirs']

        def accepted(step_name, line):
            """Two exact upstream diagnostics, each documented; never a widened pattern."""
            line = line.strip()
            if step_name == 'accessible':
                return line == ACCEPTED_FOP_WARNING
            return step_name.startswith('generate-') and line == ACCEPTED_PORT_COLLISION

        def command(name, argv, python=False):
            step = {'name': name, 'command': list(map(str, argv))}
            report['steps'].append(step)
            log_path = run / 'logs' / f'{name}.log'
            step['log'] = str(log_path.relative_to(run))
            print(f'Running {name}; log: {log_path}', flush=True)
            env = environment.copy()
            if not python:
                env.pop('LD_PRELOAD', None)
            with log_path.open('w') as log:
                process = subprocess.Popen(step['command'], cwd=run, env=env, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    step['returncode'] = process.wait(timeout=args.timeout)
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
            diagnostics = blocking_diagnostics(log_path.read_text(errors='replace'))
            # The author accepted this one known FOP limitation, not arbitrary warnings.
            step['accepted_diagnostics'] = [line for line in diagnostics if accepted(name, line)]
            step['blocking_diagnostics'] = [line for line in diagnostics
                                            if line not in step['accepted_diagnostics']]
            if step['returncode'] or step['blocking_diagnostics']:
                raise RuntimeError(f'{name} failed; inspect {log_path}')

        # Copy only authored trees, never generated assets or an extracted core.
        for relative in [PILOT / 'source', PILOT / 'xsl', Path('publication')]:
            source = ROOT / relative
            hashes(source)  # Reject symlinks before copytree can follow them.
            shutil.copytree(source, run / relative, ignore=shutil.ignore_patterns(
                'generated', '__pycache__', 'core', '.cache'))
        shutil.copyfile(ROOT / 'project.ptx', run / 'project.ptx')
        command('demos', [sys.executable, ROOT / 'scripts/build_demos.py',
                         '--output', run / 'demo-build', '--dependencies', args.demo_dependencies.resolve()], True)
        report['demo_hashes'] = hashes(run / 'demo-build')
        report['demo_asset_references'] = check_assets(run / 'demo-build')
        external = run / PILOT / 'source/external'
        for name in ['demos', 'images']:
            shutil.copytree(run / 'demo-build' / name, external / name)
        report['inputs'] = {str(relative / Path(name)): digest
                            for relative in [PILOT / 'source', PILOT / 'xsl', Path('publication')]
                            for name, digest in hashes(run / relative).items()}
        report['inputs']['project.ptx'] = hashlib.sha256((run / 'project.ptx').read_bytes()).hexdigest()
        report['implementation'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                     for name in ['scripts/build.py', 'scripts/build_demos.py',
                                                  'migration/phase2/demos/compile.cjs']}

        # Install math from retained locks in this run, not from a shared cache.
        math = run / 'math'
        math.mkdir()
        for name in ['package.json', 'package-lock.json']:
            shutil.copyfile(ROOT / PILOT / 'math' / name, math / name)
        command('math', ['npm', 'ci', '--prefix', math, '--ignore-scripts',
                         '--engine-strict', '--no-audit', '--no-fund'])
        environment['NODE_PATH'] = str(math / 'node_modules')
        report['locks'] = {str(path): hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                           for path in [Path('uv.lock'), PILOT / 'math/package-lock.json',
                                        PILOT / 'theme/package-lock.json',
                                        Path('migration/phase2/demos/package-lock.json')]}
        report['executables'] = {name: shutil.which(name, path=environment['PATH'])
                                 for name in ['node', 'npm', 'java', 'jing', 'pdflatex', 'fop']}
        command('validate', cli + ['validate', 'html'], True)
        core = run / 'home/.ptx' / VERSION / 'core'
        # CLI launch failures have historically returned success: Jing is mandatory.
        command('schema', ['jing', '-i', core / 'schema/pretext-dev.rng', run / PILOT / 'source/main.ptx'])
        command('publication-schema', ['jing', '-i', core / 'schema/publication-schema.rng',
                                       run / 'publication/publication.ptx'])
        theme = core / 'script/cssbuilder'
        shutil.copyfile(ROOT / PILOT / 'theme/package-lock.json', theme / 'package-lock.json')
        command('theme', ['npm', 'ci', '--prefix', theme, '--ignore-scripts',
                          '--engine-strict', '--no-audit', '--no-fund'])
        source = ET.parse(run / PILOT / 'source/main.ptx')
        image_ids = [image.get('{http://www.w3.org/XML/1998/namespace}id')
                     for image in source.findall('.//image') if image.find('latex-image') is not None]
        if not image_ids or not all(image_ids):
            raise ValueError('Generated image gate requires explicitly identified latex-images')
        for target in ['html', 'print'] + (['accessible'] if args.accessible else []):
            command(f'generate-{target}', cli + ['generate', '-t', target], True)
            # pdflatex embeds authored TikZ; HTML and FO consume generated SVGs.
            if target != 'print':
                for image_id in image_ids:
                    require_file(run / PILOT / f'source/generated/latex-image/{image_id}.svg')
            command(target, cli + ['build', target, '--no-generate'], True)
            output = run / 'output' / target
            require_file(output / ('index.html' if target == 'html' else 'main.pdf'))
            if target == 'html':
                services = ET.parse(output / '_static/_runestone-services.xml')
                if services.findtext('version') != RUNESTONE:
                    raise ValueError('Runestone version mismatch in generated services manifest')
                report['runestone_assets'] = check_runestone(
                    output, ROOT / RUNESTONE_ASSETS, args.record_runestone)
                report['html_asset_references'] = check_assets(output)
                for name, digest in hashes(external).items():
                    if hashlib.sha256((output / 'external' / name).read_bytes()).hexdigest() != digest:
                        raise ValueError(f'External asset changed during publication: {name}')
            elif not (output / 'main.pdf').read_bytes().startswith(b'%PDF-'):
                raise ValueError(f'Invalid PDF: {target}')
        report['outputs'] = hashes(run / 'output')
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True, help='New directory outside repository')
    parser.add_argument('--demo-dependencies', type=Path, default=ROOT / 'migration/phase2/demos')
    parser.add_argument('--accessible', action='store_true', help='Also attempt experimental FOP PDF')
    parser.add_argument('--record-runestone', action='store_true',
                        help='Rewrite the Runestone asset hashes from this run instead of verifying them')
    parser.add_argument('--timeout', type=int, default=600, help='Per-command timeout in seconds')
    args = parser.parse_args()
    try:
        run = build(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Build failed: {error}\n')
    print(f'HTML and print gates passed: {run / "report.json"}')


if __name__ == '__main__':
    main()
