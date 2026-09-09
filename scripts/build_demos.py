#!/usr/bin/env python3
"""Build legacy demos from tracked working-tree sources into a new directory."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'migration/phase2/demos'
DEMOS = '''Axequalsb bestfit bestfit-implicit bestfit-implicit1 compose2d compose3d
dynamics dynamics2 dynamics3 eigenspace fund_subspaces leastsquares parametric1
parametric1h parametric2 plane planes point projection similarity spans steps
twobytwo vector-add vector vector-mul vector-sub rowred1 rowred2 rowred3 rowred4
rowred5 rrinter'''.split()


def stage_tracked(repo, target, prefixes):
    """Use the Git index as an allowlist, not recursive directory copies."""
    entries = subprocess.check_output(
        ['git', '-C', str(repo), 'ls-files', '--stage', '-z', '--', *prefixes]
    ).decode().split('\0')
    if not entries[0]:
        raise RuntimeError(f'No tracked sources in {repo}; initialize submodules')
    for entry in filter(None, entries):
        metadata, name = entry.split('\t', 1)
        if metadata.split()[0] == '160000':
            continue
        source = repo / name
        if source.is_symlink():
            raise RuntimeError(f'Refusing source symlink: {source}')
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def concat(output, sources, separator='\n'):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(separator.join(p.read_text() for p in sources) + '\n')


def rabbits_css(css, consumers):
    """Drop the unused Bootstrap icon module, not missing-asset diagnostics."""
    if any('glyphicon' in text.lower() for text in consumers):
        raise RuntimeError('Rabbits uses glyphicons; supply licensed fonts before building')
    # Match the complete, flat icon module in the tracked Bootstrap version.
    pattern = (r"(?m)^@font-face \{\n  font-family: 'Glyphicons Halflings';\n[^{}]*\}\n"
               r"(?:\.glyphicon(?:[-\w]+)?(?::before)? \{[^{}]*\}\n)+(?=\.caret \{)")
    css, count = re.subn(pattern, '', css)
    if count != 1 or 'Glyphicons Halflings' in css or 'glyphicons-halflings' in css:
        raise RuntimeError('Bootstrap glyphicon module changed; review staged CSS pruning')
    return css


def build(output, dependencies):
    try:
        from mako.lookup import TemplateLookup
    except ImportError as error:
        raise RuntimeError(f'Install Python dependencies from {TOOLS / "requirements.txt"}') from error

    if output.exists():
        raise ValueError(f'Output must be a new directory: {output}')
    version = subprocess.check_output(['node', '--version'], text=True).strip()
    if int(version.lstrip('v').split('.')[0]) < 20:
        raise RuntimeError('Node 20 or newer is required')
    for name in ['package.json', 'package-lock.json']:
        if (dependencies / name).read_bytes() != (TOOLS / name).read_bytes():
            raise RuntimeError(f'Dependency {name} differs from the dedicated manifest/lock')
    manifest = json.loads((TOOLS / 'package.json').read_text())
    for name, expected in manifest['dependencies'].items():
        package = dependencies / 'node_modules' / name / 'package.json'
        if not package.exists() or json.loads(package.read_text())['version'] != expected:
            raise RuntimeError(f'Install pinned dependencies with npm ci in {dependencies}')
    command = ['node', str(TOOLS / 'compile.cjs'), str(dependencies)]

    def compile_coffee(text, bare=False):
        return subprocess.check_output(
            command + ['coffee', 'bare' if bare else 'wrapped'], input=text, text=True)

    with tempfile.TemporaryDirectory(prefix='ila-demos-') as temporary:
        stage = Path(temporary)
        stage_tracked(ROOT, stage, [
            'demos/*.mako', 'demos/*.coffee', 'demos/lib', 'demos/css',
            'demos/vendor', 'demos/img', 'demos/cover.html', 'demos/rabbits.html',
            'vendor/jquery.min.js', 'static/theme-duke/logo.png',
        ])
        mathbox = stage / 'mathbox'
        stage_tracked(ROOT / 'mathbox', mathbox, ['src', 'vendor/three.js'])
        for name in ['shadergraph', 'threestrap']:
            relative = Path('mathbox/vendor') / name
            stage_tracked(ROOT / relative, stage / relative, ['src', 'vendor'])
        shaders = {}
        for source in sorted((mathbox / 'src/shaders/glsl').rglob('*.glsl')):
            if source.stem in shaders:
                raise RuntimeError(f'Duplicate shader: {source.stem}')
            shaders[source.stem] = source.read_text()
        (mathbox / 'build').mkdir()
        (mathbox / 'build/shaders.js').write_text(
            'module.exports = ' + json.dumps(shaders, sort_keys=True) + ';\n')
        subprocess.run(command + [str(stage)], check=True)

        strap = mathbox / 'vendor/threestrap'
        core = '''binder api bootstrap plugin aliases core/fallback core/renderer
        core/bind core/size core/fill core/loop core/time core/scene core/camera
        core/render core/warmup'''.split()
        extra = 'stats controls cursor fullscreen vr ui'.split()
        concat(strap / 'build/threestrap.js', [
            dependencies / 'node_modules/lodash/dist/lodash.js',
            *[strap / f'src/{name}.js' for name in core],
            strap / 'vendor/stats.min.js',
            *sorted((strap / 'vendor/controls').glob('*.js')),
            *[strap / f'src/extra/{name}.js' for name in extra],
        ], '\n;\n')
        bundle = mathbox / 'build/mathbox-bundle.js'
        concat(bundle, [mathbox / 'vendor/three.js', strap / 'build/threestrap.js',
                       *[strap / f'vendor/{name}.js' for name in [
                           'renderers/VRRenderer', 'controls/VRControls',
                           'controls/OrbitControls', 'controls/DeviceOrientationControls',
                           'controls/TrackballControls']],
                       mathbox / 'build/mathbox-core.js'], '\n;\n')
        mathcss = mathbox / 'build/mathbox.css'
        concat(mathcss, [*sorted((mathbox / 'vendor/shadergraph/src').rglob('*.css')),
                         *sorted((mathbox / 'src').rglob('*.css'))])
        source = stage / 'demos'
        result = stage / 'result'
        demos = result / 'demos'
        libs = {}
        for name in ['demo2', 'dynamics', 'animstate', 'rrinter', 'rrmat', 'cover']:
            libs[name] = stage / f'{name}.js'
            libs[name].write_text(compile_coffee((source / f'lib/{name}.coffee').read_text()))
        vendor = source / 'vendor'
        common = [bundle, vendor / 'katex.js', vendor / 'domready.js']
        end = [vendor / 'expreval.js', vendor / 'compat.js']
        js = {
            'demo': [libs['demo2'], *common, vendor / 'dat.gui.js',
                     vendor / 'screenfull.js', vendor / 'roots.js', *end],
            'dynamics': [libs['dynamics']],
            'slideshow': [libs['animstate'], libs['rrmat'], *common, *end],
            'rrinter': [libs['animstate'], libs['rrmat'], libs['rrinter'], *common, *end],
            'rabbits': [stage / 'vendor/jquery.min.js', vendor / 'bootstrap.js',
                        vendor / 'plotly.js'],
            'cover': [libs['dynamics'], bundle, vendor / 'domready.js', libs['cover']],
        }
        bootstrap = vendor / 'bootstrap.css'
        bootstrap.write_text(rabbits_css(bootstrap.read_text(), [
            (source / 'rabbits.html').read_text(), *[path.read_text() for path in js['rabbits']],
        ]))
        css = {
            'demo': [source / 'css/demo.css', vendor / 'katex.css', mathcss],
            'slideshow': [vendor / 'katex.css', mathcss, source / 'css/rrmat.css',
                          source / 'css/slideshow.css'],
            'rabbits': [vendor / 'bootstrap.css'],
            'cover': [source / 'css/cover.css', mathcss],
        }
        css['rrinter'] = [*css['slideshow'], source / 'css/rrinter.css']
        for name, files in js.items():
            concat(demos / f'js/{name}.js', files, '\n;\n')
        for name, files in css.items():
            concat(demos / f'css/{name}.css', files)

        def vers(name):
            data = (demos / name).read_bytes()
            digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            return f'{name}?vers={digest[:6]}'

        lookup = TemplateLookup(directories=[str(source)], input_encoding='utf-8')
        for name in DEMOS:
            html = lookup.get_template(f'{name}.mako').render_unicode(
                coffee=lambda text: compile_coffee(text, bare=True), vers=vers)
            (demos / f'{name}.html').write_text(html)
        for name in ['rabbits', 'cover']:
            shutil.copyfile(source / f'{name}.html', demos / f'{name}.html')
        shutil.copytree(vendor / 'fonts', demos / 'css/fonts')
        shutil.copytree(source / 'img', demos / 'img')
        (result / 'images').mkdir()
        shutil.copyfile(stage / 'static/theme-duke/logo.png', result / 'images/logo.png')
        # Keep the historical root cover entry point as well as demos/cover.html.
        shutil.copyfile(source / 'cover.html', result / 'cover.html')
        for kind in ['js', 'css']:
            (result / kind).mkdir()
            shutil.copyfile(demos / kind / f'cover.{kind}', result / kind / f'cover.{kind}')
        shutil.copytree(result, output)
    print(f'Built {len(DEMOS) + 2} demos with {version}: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    parser.add_argument('--dependencies', type=Path, default=TOOLS,
                        help='Directory containing the dedicated package.json and node_modules')
    args = parser.parse_args()
    try:
        build(args.output.resolve(), args.dependencies.resolve())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Demo build failed: {error}\n')


if __name__ == '__main__':
    main()
