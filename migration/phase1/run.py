#!/usr/bin/env python3
"""Stage and measure a fresh pilot run; successful generation is not approval."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True, help='new, nonexistent run directory')
    parser.add_argument('--baseline', type=Path, default=Path.home() / 'tmp/ila/phase0/output')
    parser.add_argument('--targets', nargs='+', choices=['html', 'print', 'accessible'],
                        default=['html', 'print', 'accessible'])
    parser.add_argument('--math-dir', type=Path, default=Path.home() / 'tmp/ila/phase1/math-node20',
                        help='isolated npm ci installation of math/package-lock.json')
    args = parser.parse_args()
    import pretext

    if (pretext.VERSION, pretext.CORE_COMMIT) != (
        '2.52.3', '2c8806b9988f855e94d185fb145226bf6c0a5b20'
    ):
        parser.error('Use the locked pilot environment; upstream version/core mismatch')
    pilot = Path(__file__).resolve().parent
    repo = pilot.parents[1]
    baseline = args.baseline.resolve(strict=True)
    run = args.run.resolve()
    if run.is_relative_to(repo) or run.is_relative_to(baseline.parent):
        parser.error('Run must be outside the repository and historical baseline directory')
    run.mkdir(parents=True, exist_ok=False)
    report = {
        'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'pretext': pretext.VERSION, 'core': pretext.CORE_COMMIT,
        'python': sys.version, 'baseline': str(baseline), 'run': str(run),
        'limitations': ['Generation and schema results only; not visual, behavioral or accessibility approval.',
                        'Demo bundles are verified historical artifacts, not independently rebuilt here.',
                        'All targets are attempted even if schema validation fails, for diagnosis only.'],
        'steps': [],
    }
    try:
        manifest_path = repo / 'migration/baseline-output.json'
        manifest_bytes = manifest_path.read_bytes()
        report['baseline_manifest_sha256'] = hashlib.sha256(manifest_bytes).hexdigest()
        manifest = json.loads(manifest_bytes)
        expected = {item['path']: item for item in manifest['artifacts']
                    if item['path'].startswith('demos/') or item['path'] == 'images/logo.png'}
        actual = {path.relative_to(baseline).as_posix()
                  for path in (baseline / 'demos').rglob('*') if path.is_file()}
        if (baseline / 'images/logo.png').is_file():
            actual.add('images/logo.png')
        if actual != expected.keys():
            raise ValueError('Baseline demo file set does not match historical manifest')
        for path, item in expected.items():
            content = (baseline / path).read_bytes()
            if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
                raise ValueError(f'Baseline demo hash mismatch: {path}')
        report['verified_baseline_files'] = len(expected)
        math_dir = args.math_dir.resolve()
        for name in ['package.json', 'package-lock.json']:
            if (math_dir / name).read_bytes() != (pilot / 'math' / name).read_bytes():
                raise ValueError(f'Isolated math environment does not match math/{name}')
        report['math_lock_sha256'] = hashlib.sha256((math_dir / 'package-lock.json').read_bytes()).hexdigest()
        report['math_directory'] = str(math_dir)
        for name in ['source', 'publication', 'xsl']:
            shutil.copytree(pilot / name, run / name, ignore=shutil.ignore_patterns('generated', '__pycache__'))
        shutil.copy2(pilot / 'project.ptx', run / 'project.ptx')
        for name in expected:
            destination = run / 'source/external' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(baseline / name, destination)
        report['inputs'] = {
            path.relative_to(run).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(run.rglob('*')) if path.is_file()
        }
        (run / 'logs').mkdir()
        # The Python extension workaround must not leak into older Nix executables.
        cli = [sys.executable, '-I', '-c',
               "import os; os.environ.pop('LD_PRELOAD', None); from pretext.cli import main; main()",
               '-v', 'debug', '--save-tmp-dirs']
        environment = os.environ.copy()
        environment.pop('PYTHONPATH', None)
        # Prefer the verified Debian Node/Java/FOP; borrow only missing tools from Nix.
        environment['PATH'] = str(Path(sys.executable).parent) + ':/usr/bin:/bin:' + environment['PATH']
        environment['NODE_PATH'] = str(math_dir / 'node_modules')
        # Upstream installs CSS packages into its extracted core. Keep that
        # mutable resource cache inside this run, never in the author's HOME.
        environment['HOME'] = str(run / 'home')
        (run / 'home').mkdir()
        report['resource_home'] = environment['HOME']
        theme_lock = pilot / 'theme/package-lock.json'
        report['theme_lock_sha256'] = hashlib.sha256(theme_lock.read_bytes()).hexdigest()
        report['executables'] = {name: shutil.which(name, path=environment['PATH'])
                                 for name in ['node', 'npm', 'java', 'fop', 'pdflatex', 'jing']}
        environment['TMPDIR'] = str(run / 'tmp')
        (run / 'tmp').mkdir()
        commands = [('validate', cli + ['validate', 'html'])]
        core = run / 'home/.ptx' / pretext.VERSION / 'core'
        schema = core / 'schema/pretext-dev.rng'
        # Independently check Jing's exit status; the CLI can misreport launch failures.
        commands += [('schema', ['jing', '-i', str(schema), str(run / 'source/main.ptx')])]
        if 'html' in args.targets:
            commands += [('theme', ['npm', 'ci', '--prefix', str(core / 'script/cssbuilder'),
                                    '--ignore-scripts', '--engine-strict', '--no-audit', '--no-fund'])]
        commands += [(target, cli + ['build', target]) for target in args.targets]
        for name, command in commands:
            if name == 'theme':
                shutil.copy2(theme_lock, core / 'script/cssbuilder/package-lock.json')
            log_path = run / 'logs' / f'{name}-command.log'
            step = {'name': name, 'command': command, 'log': str(log_path)}
            report['steps'].append(step)
            print(f'Running {name}; log: {log_path}', flush=True)
            command_environment = environment.copy()
            if name in ('schema', 'theme'):
                command_environment.pop('LD_PRELOAD', None)
            with log_path.open('w') as log:
                process = None
                try:
                    process = subprocess.Popen(command, cwd=run, stdout=log,
                                               stderr=subprocess.STDOUT, env=command_environment,
                                               start_new_session=True)
                    step['returncode'] = process.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    step['returncode'] = None
                    step['error'] = '600-second timeout; output is incomplete'
                except OSError as error:
                    step['returncode'] = None
                    step['error'] = str(error)
                except BaseException:
                    step['status'] = 'interrupted'
                    raise
                finally:
                    if process is not None:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait()
            if name in ('validate', 'schema', 'theme'):
                step['status'] = 'valid' if step['returncode'] == 0 else 'failed'
            else:
                output = run / 'output' / name
                candidates = [output / 'index.html'] if name == 'html' else list(output.glob('*.pdf'))
                step['artifacts'] = [str(path.relative_to(run)) for path in candidates
                                     if path.is_file() and path.stat().st_size]
                step['status'] = 'generated' if step['returncode'] == 0 and step['artifacts'] else 'failed'
            step['diagnostics'] = [line for line in log_path.read_text(errors='replace').splitlines()
                                   if any(word in line.lower() for word in
                                          ['warning', '[warn]', 'error', 'overflow', 'overfull', 'underfull', 'unsupported'])]
            step['blocking_diagnostics'] = [line for line in step['diagnostics']
                                            if any(word in line.lower() for word in
                                                   ['alternate text is missing', 'exceed the available area',
                                                    'overfull', 'unsupported', 'not yet supported'])]
            (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return int(any(step['status'] == 'failed' or step['blocking_diagnostics'] for step in report['steps']))


if __name__ == '__main__':
    sys.exit(main())
