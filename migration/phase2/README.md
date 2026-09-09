# Modern Root Build

Status on 2026-09-09: root project, staged runner, tests, and CI implemented.
**Strict HTML and print generation passes from source-built demos.**
Nothing is deployed. Clean-checkout and hosted CI status are recorded below;
this scaffold is not a whole-book conversion or release approval.

## Scope

The root `project.ptx` is a standard PreTeXt v2 project with `html`, `print`, and
experimental `accessible` targets. Its source and XSL paths point directly to
`migration/phase1/source` and `migration/phase1/xsl`. There is no chapter conversion,
new source dialect, or change to the historical phase1 runner. Root
`publication/publication.ptx` retains `https://ulrikbuchholtz.dk/ila/` and the
pilot publication settings. Root project discovery does not replace SCons.

Use `scripts/build.py`, not a bare root `pretext build`, for acceptance builds.
Direct PreTeXt commands understand the standard project but do not rebuild/stage
the independent demos, isolate caches, or enforce these gates. They may write
generated files into the pilot source tree.

## Setup And Build

Provision Python 3.12.14, uv 0.12.5, Node 20.19.2, npm, Java/Jing, and a TeX
installation with TikZ and the fonts/packages used by upstream. The workflow
lists its Ubuntu packages. Optional FOP needs Java and `fop`. Then, from root:

```bash
git submodule update --init --recursive mathbox
uv sync --locked --python 3.12.14
npm ci --prefix migration/phase2/demos --ignore-scripts --engine-strict --no-audit --no-fund
uv run --locked python -B -m unittest discover -s migration/phase2/tests -v
uv run --locked python -B -m unittest discover -s migration/phase1/tests -v
uv run --locked python -B -m unittest discover -s migration/phase2/demos -v
uv run --locked python scripts/build.py --run /tmp/ila-modern-new
```

The run directory must not exist and must be outside the repository and the
known historical `~/tmp/ila/phase0` directory. No directory is cleaned or reused.
HTML and print are both required; `--accessible` adds the experimental FOP PDF.
`--demo-dependencies DIR` selects an isolated installation of the dedicated
demo npm lock, using the existing demo builder's `--dependencies` interface.
`--timeout SECONDS` changes the default 600-second per-command limit.

The runner always calls `scripts/build_demos.py --output RUN/demo-build` itself.
There is deliberately no option to supply prebuilt or phase0 demo output. See
`demos/README.md` for that builder's source allowlist and compatibility risks.

## Gates And Evidence

The runner creates a fresh source/publication/XSL staging tree, `HOME`, and
`TMPDIR`. It rejects source symlinks and excludes generated directories, Python
caches, and extracted core directories. It uses the current authored fixture
bytes, including any intentional working-tree author edits, without rewriting
them. Independent demo output is audited, hashed, then copied to staged external
assets. The historical phase0 build, manifest, and output are not read.

The sequence fails immediately on a failed gate:

1. Verify the exact PreTeXt CLI version and core commit; rebuild and audit demos.
2. Install math dependencies with `npm ci` using the unchanged phase1 math lock.
3. Run `pretext validate html`, then independently run Jing against the pinned
   core's `pretext-dev.rng` and the publication schema. Jing launch or nonzero
   exit is fatal even if the CLI reports success.
4. Install CSS-builder dependencies with the unchanged phase1 theme lock into
   this run's extracted core resource cache. No upstream Python/XSL/JS is patched.
5. Generate assets before each target. Require all seven authored latex-image
   SVGs for HTML/FO; conventional print embeds the authored TikZ directly.
6. Build with `--no-generate`, require nonempty HTML/PDF artifacts and PDF magic,
   verify the Runestone manifest version, audit HTML/CSS local assets, and verify
   every copied external asset's hash against its staged input.

Nonzero commands, timeout/interruption, missing/empty assets, escaping asset
paths, missing alt text, overfull/overflow diagnostics, unsupported features,
and explicit failure diagnostics are blocking. The one exact FOP coverage-table
warning accepted in `phase1/author-notes.md` is retained in logs and listed in
`accepted_diagnostics` for the optional accessible target, not suppressed or
generalized to other warnings. Process groups are killed
and reaped on timeout or interruption. Ordinary informational warnings remain
in logs. In particular, the CLI's production-schema warning about three
experimental fixture constructs is not conflated with development-schema
failure: the explicit development-schema and validation-plus checks pass.

HTML/CSS auditing checks local `src`, poster/object resources, knowls, stylesheet
links, and CSS `url(...)` references. It is not a JavaScript execution test, a
complete CSS parser, navigation/fragment audit, external CDN availability check,
or accessibility review. Binary AppleDouble metadata in the upstream Runestone
archive is not parsed as CSS; actual referenced files must still exist.

Every run retains `report.json` and command logs, including failure evidence.
The report records staged input and implementation hashes, demo hashes, lock
hashes, command lines, return codes, blocking diagnostics, executable paths,
and successful output hashes. `tmp/` retains upstream scratch files for diagnosis.
Neither successful generation nor this evidence is author/release approval.

## Pins And Runestone

| Component | Pin |
| --- | --- |
| Python / uv | 3.12.14 / 0.12.5 in CI; Python 3.12 minor required by project |
| PreTeXt CLI / core | 2.52.3 / `2c8806b9988f855e94d185fb145226bf6c0a5b20` |
| Native SymPy | 1.14.0 |
| Mako / MarkupSafe | 1.3.10 / 3.0.3 |
| Python resolution | root `uv.lock`, generated by uv 0.12.5 |
| Node | 20.19.2 in CI and local verification |
| Demo dependencies | `migration/phase2/demos/package-lock.json` |
| Math / theme dependencies | unchanged `migration/phase1/{math,theme}/package-lock.json` |
| Runestone Services | 8.2.10 via target `stringparams debug.rs.version` |

The Runestone pin uses the upstream `_runestone_services()` implementation's
existing `debug.rs.version` interface, not a monkeypatch of an installation.
It requests `https://runestone.academy/cdn/runestone/8.2.10/webpack_static_imports.xml`
instead of `latest`. The runner verifies `output/html/_static/_runestone-services.xml`
and audits the emitted local assets. Merely setting `rs-version` would not pin
the downloader because upstream overwrites it from the discovered manifest.

**Upstream explicitly labels this version selector DEBUGGING, not PRODUCTION.**
It is the available version-selection interface in this pinned release, not a
claim of upstream-supported production reproducibility. The manifest/tarball
have no retained expected content hashes; output hashes record what was fetched
but do not make remote content immutable. Browser Pyodide/fonts and other
external resources remain network dependencies. Ubuntu apt packages and GitHub
Action major tags are not content-locked. This is not a hermetic or security-
approved publication pipeline. CI uses Node's bundled npm; local npm was 9.2.0.

## CI

`.github/workflows/modern-build.yml` runs on pushes, pull requests, and manual
dispatch. It installs locked Python/demo dependencies, runs runner, source and
demo tests, then requires fresh HTML and print. Manual dispatch can also request
FOP. Locked Playwright Chromium runs the HTML and computation regression gates;
tracked files must remain unchanged. Outputs, reports, and logs are uploaded even on failure; no deployment or
write permission is configured. The workflow has not been executed on GitHub
from this workspace. Its apt/TeX package selection still needs a hosted run.
On the ephemeral Ubuntu runner the workflow permits unprivileged user namespaces
for downloaded Chromium, while the computation test keeps Chromium sandboxing
enabled. No host sandbox policy was changed during local verification.

## Observed Results

The root lock was installed in `/tmp/opencode/ila-phase2-venv`, leaving the
existing root and historical phase1 environments unchanged. Exact commands:

```bash
env UV_PROJECT_ENVIRONMENT=/tmp/opencode/ila-phase2-venv "$HOME/tmp/ila/phase1/venv/bin/uv" sync --locked --python 3.12.14
/tmp/opencode/ila-phase2-venv/bin/python -B -m unittest discover -s migration/phase2/tests -v
/tmp/opencode/ila-phase2-venv/bin/python -B -m unittest discover -s migration/phase1/tests -v
/tmp/opencode/ila-phase2-venv/bin/python -B -m unittest discover -s migration/phase2/demos -v
nix develop --no-update-lock-file -c bash -c 'export PATH="/usr/bin:/bin:$PATH"; exec env -u PYTHONPATH LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 /tmp/opencode/ila-phase2-venv/bin/python scripts/build.py --run /tmp/opencode/ila-phase2-build-002'
```

All 6 runner tests, 14 source tests, and 6 demo integration tests passed.
The mixed Nix/Debian command deliberately prefers system Node/Java over the old
Nix versions, borrowing TeX and Jing from the unchanged flake. The preload is a
local Python-extension workaround, removed before launching upstream child
executables. Normal Ubuntu CI does not use it or Nix.

Early strict runs stopped on the four known missing Glyphicons fonts. The demo
builder now removes only the unused icon module from staged Bootstrap CSS,
with negative tests for new icon use and changed module structure. No gate is
waived and historical source/output remains unchanged.

To investigate beyond that blocker, a one-off Python invocation imported the
runner and replaced only `check_assets` with a function returning
`DIAGNOSTIC ONLY: asset audit bypassed`. It used a fresh directory, rebuilt demos,
and did not modify upstream or repository code. The second diagnostic run,
`/tmp/opencode/ila-phase2-diagnostic-002`, generated `output/html/index.html` and
`output/print/main.pdf`; schema, publication schema, generation, and command
diagnostic checks passed, and Runestone 8.2.10 was confirmed. Its report's
`status: passed` reflects that instrumented execution and **must not be treated
as a strict gate pass**; both asset-reference fields carry the diagnostic marker.
A subsequent audit examined 449 references and found only the four fonts above.
The first diagnostic run exposed a services-manifest path mistake, fixed in the
runner before the second run. Neither diagnostic is release evidence.

The strict integrated build in `~/tmp/ila/phase2/run-001` passed HTML and print,
independent source/publication schema validation, generated-image requirements,
and demo/publication asset checks. Its HTML passed 669 browser assertions with
zero failures, network errors or runtime errors, and the 27 computation checks.
The seven known browser warnings remain visible. Eighteen screenshots and
input-bound reports are retained beside the outputs. `/tmp` filled during an
earlier strict run; new evidence uses disk-backed storage instead.

Accessible PDF was not rerun here. It remains optional/experimental; phase1
records FOP limitations and separate PDF/UA evidence. No new screen-reader,
PDF/UA, or human review was performed for this root integration. PDF end-marker
placement and print/FO differences from the author notes remain follow-up work.

## Checkout Cleanup

Pre-existing untracked `.cache`, `.python-version`, `logs`, `output`,
`demos/prebuilt`, `demos/vendor/jquery.min.js`, `src/external`, and `src/gen`
were moved, not deleted, to `~/tmp/ila/phase2/checkout-leftovers/` with their
relative paths preserved. Existing ignored environments, legacy npm installs,
and historical evidence were left alone. This is local preservation, not a
managed-backup claim. These leftovers are not inputs to the modern build.

## Clean-Checkout Checkpoint

A fresh local clone of `ce41543` at `~/tmp/ila/phase2/clean-checkout` initialized
MathBox and its two nested submodules from their upstream GitHub repositories.
`uv sync --locked --python 3.12.14` created a new Python environment; `npm ci`
created a new demo dependency installation. No local prebuilt files or Phase 0
output were copied. Download caches and the host Nix store were shared, so this
is clean-checkout verification, not an air-gapped or hermetic build.

- `~/tmp/ila/phase2/clean-run-001/report.json`: strict HTML and print pass.
- All 6 runner, 6 demo integration, and 14 source tests pass in the new checkout.
- `browser/report.json`: locked Playwright Chromium, 669 passes, zero failures,
  zero network/runtime errors, 7 known warnings, and 18 screenshots.
- `computation-system.json`: sandboxed system Chromium, all 27 checks pass.
- `computation.json`: downloaded Chromium could not launch with its sandbox under
  the host policy. Retained as a failed infrastructure attempt, not a site failure
  or a pass. The subsequent system-browser run did not disable sandboxing.
- `git status --short` in both checkouts was empty after building and testing.

The strict build command was the mixed Nix/Debian invocation above, using the
fresh clone's `.venv/bin/python` and a fresh persistent run directory. The modern
CI workflow is implemented but has not run on GitHub; full system-tool closure
and immutable Runestone asset hashes remain open Phase 2 reproducibility gates.
Do not mark Phase 2 fully closed on the strength of a local build alone.
