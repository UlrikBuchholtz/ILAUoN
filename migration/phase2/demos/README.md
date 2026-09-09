# Independent Demo Build

`scripts/build_demos.py` builds the complete legacy demo inventory independently
of SCons, PreTeXt, historical published output, and `demos/prebuilt/`. It writes
35 HTML pages under `demos/` (33 Mako templates, rabbits, cover), their JavaScript,
CSS, KaTeX fonts and images, and `images/logo.png` for book staging. It also
preserves the historical root `cover.html`, `js/cover.js`, and `css/cover.css`
entry points. Copying just `demos/` and `images/logo.png` is sufficient for the
book's demo iframe staging; the cover is also available as `demos/cover.html`.

## Setup and Build

Run from the repository root with Git, Node 20 or newer, npm, and Python 3.10+
with venv/pip support. Tested with Node 20.19.2, npm 9.2.0, Python 3.12.14.

```bash
git submodule update --init --recursive mathbox
python3 -m venv migration/phase2/demos/.venv
migration/phase2/demos/.venv/bin/python -m pip install -r migration/phase2/demos/requirements.txt
npm ci --prefix migration/phase2/demos --ignore-scripts --engine-strict --no-audit --no-fund
migration/phase2/demos/.venv/bin/python scripts/build_demos.py --output /tmp/ila-demos-new
```

With that environment activated, the coordinated interface is simply:

```bash
python scripts/build_demos.py --output NEW_DIR
```

`NEW_DIR` must not exist. An existing destination is rejected, not cleaned or
merged. Compilation happens in an automatically cleaned temporary directory;
the output is only copied after all compilation and rendering succeed. The
build itself does not download dependencies or initialize submodules.

To keep npm installations elsewhere, copy this directory's `package.json` and
`package-lock.json` to a dedicated directory, run `npm ci --ignore-scripts
--engine-strict` there, and pass `--dependencies /absolute/path/to/that/directory`.
The argument names the directory containing the manifest and `node_modules`,
not `node_modules` itself. The builder checks both manifests against the
dedicated originals and checks installed direct dependency versions. Use
`DEMO_DEPENDENCIES` for the equivalent override in the integration tests.

On this machine system Python lacks pip/ensurepip; an isolated environment was
successfully provisioned using the existing uv executable instead:

```bash
$HOME/tmp/ila/phase1/venv/bin/uv venv migration/phase2/demos/.venv --python 3.12.14
$HOME/tmp/ila/phase1/venv/bin/uv pip install --python migration/phase2/demos/.venv/bin/python -r migration/phase2/demos/requirements.txt
```

Only uv's executable was reused, not Phase 1 output or build assets.

## Source Contract

- `git ls-files --stage` is an allowlist for working-tree source files; untracked
  caches, generated output and prebuilt demo directories are not copied.
- Root inputs are selected `demos/` templates, CoffeeScript, CSS, vendored browser
  libraries, fonts and images, tracked `vendor/jquery.min.js`, and the Duke logo.
  In particular, the untracked `demos/vendor/jquery.min.js` is not an input.
- MathBox inputs are `src/` and tracked `vendor/three.js`. ShaderGraph and
  Threestrap inputs are their `src/` and `vendor/` trees at initialized submodule
  revisions. No `build/`, `.tmp/`, or installed source `node_modules/` is read.
- GLSL snippets are converted to a generated CommonJS module in the staging
  tree. ShaderGraph is compiled as part of MathBox's dependency graph, and its
  CSS is rebuilt from source. Threestrap is concatenated from its source list
  and pinned Lodash, rather than copied from its tracked historical `build/`.
- Original source and installed dependencies are never patched. The compiler
  reads staged files, resolves npm modules explicitly from the isolated install,
  and writes generated code only into staging. No npm scripts or Gulp run.

The inspected specifications were `demos/SConscript`, `mathbox/SConstruct`,
`mathbox/gulpfile.js`, and the nested Threestrap/ShaderGraph gulpfiles. The tested
source revisions are MathBox `916e4b925305d71dc36d45db39b7b282dedcccbf`, ShaderGraph
`7f53f38152d73e59f873f141a6eb9b11a85c85b2`, and Threestrap
`bf301039f2f390cfb6e18a00faeb43ff3f395c4d` (the repository's gitlinks).

## Compatibility Decisions

- CoffeeScript 1.10.0 retains legacy syntax and generated semantics; standalone
  libraries are wrapped, while Mako's inline CoffeeScript filter uses bare mode.
  Mako 1.3.10 and MarkupSafe 3.0.3 are separately pinned.
- Browserify 17.0.1 runs on modern Node. Its `bare` option must **not** be enabled:
  unlike the historical Gulp wrapper's behavior, it omits the browser stream
  shims required by cssauron. A real browser check caught this failure even
  though compilation and JavaScript syntax checks passed.
- The old MathBox Gulp list misspells `TrackballControls.js` as
  `TrackBallControls.js`. This builder uses the tracked filename with correct
  case; no original file is renamed or patched.
- Bundle order follows SConscript, including dynamics, slideshow, rrinter,
  rabbits and cover. Output is intentionally unminified, like the ordinary
  legacy build without `--minify`. Cache-busting values use Git blob hashes of
  the actual generated assets, not historical output hashes.
- Rabbits does not use Bootstrap's Glyphicons Halflings module. The builder
  removes that module (font-face and base/icon definitions) only from staged
  Bootstrap CSS, preserving every other byte and the original license header.
  This eliminates references to four absent font files without an asset-check
  whitelist or an unlicensed font download. It checks rabbits HTML and all its
  bundled scripts for glyphicon use and rejects an unexpected Bootstrap module
  shape. Introducing icons requires supplying licensed fonts and revisiting this
  explicit pruning step; original `demos/vendor/bootstrap.css` is never edited.

## Verification

```bash
migration/phase2/demos/.venv/bin/python -B -m unittest discover -s migration/phase2/demos -v
```

Six integration tests check inventory against SConscript, HTML/CSS asset existence
and version hashes, Node syntax checks for every bundled and inline script,
byte-identical repeated builds, refusal to overwrite output, and exclusion of
an untracked poisoned prebuilt fixture. The glyphicon regression checks that
only the unused module is removed, original source remains intact, and both new
icon use and unexpected module changes fail rather than silently pruning.

Optional browser testing requires Playwright and its Chromium installation in
a separate test environment. It is not a build dependency. The existing pilot
test environment (Playwright 1.62.0) was reused here:

```bash
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 PLAYWRIGHT_BROWSERS_PATH="$HOME/tmp/ila/phase1/browsers" "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase2/demos/browser_check.py --output /tmp/opencode/ila-phase2-demos-002
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 PLAYWRIGHT_BROWSERS_PATH="$HOME/tmp/ila/phase1/browsers" "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase2/demos/browser_check.py --output /tmp/opencode/ila-phase2-demos-002 --width 390 --pages dynamics dynamics2 dynamics3 rrinter rabbits cover
```

The preload is specific to this mixed Debian/Nix test environment. The checker
serves the new build locally, uses software WebGL, reports uncaught page errors
and HTTP failures, checks canvas creation, submits a matrix and swaps rows in
rrinter, and checks a deterministic rabbit-population step and its SVG plot.

Observed results on 2026-09-09: all 35 pages started at desktop width without
page errors or HTTP failures. The six mobile-width pages listed above also
passed, including the rrinter and rabbits interactions. The successful output
is `/tmp/opencode/ila-phase2-demos-002`; `-001` was an earlier diagnostic build
with the Browserify shim error, not a valid staging input. No original tracked
files were modified, and the MathBox worktree remained clean.

## Remaining Risks

This is a reproducible legacy compatibility build, not a dependency security
upgrade or a complete visual/interaction regression suite. On 2026-09-09,
`npm audit --omit=dev` reported five advisories: four low through Browserify's
crypto dependencies and one critical on legacy Lodash 2.4.2. Lodash is shipped
in the generated browser bundle, not just a build tool. No automatic audit fix
was applied because upgrading its major version changes Threestrap's runtime
contract. Deployment security review remains necessary. Original vendored
Three.js, KaTeX, jQuery, Bootstrap and Plotly likewise remain legacy versions.
Browser startup and selected interactions do not certify every URL parameter,
animation, mobile layout, accessibility behavior, or browser engine.
