# Phase 1 Hard-Case Pilot

Status: **started, not approved or complete** (2026-09-06). This nested project
does not replace the root legacy publisher or convert whole chapters. See
`coverage.md` for excerpt provenance and provisional semantic mappings.

## Tooling and Isolation

- CLI: PreTeXt 2.52.3, core `2c8806b9988f855e94d185fb145226bf6c0a5b20`.
- Python: 3.12.14 observed; `pyproject.toml` restricts the minor version to 3.12.
- `uv.lock` locks Python packages and distribution hashes, including SymPy 1.14.0
  and Playwright 1.62.0. Lock generated with uv 0.12.5.
- Fresh environment: `~/tmp/ila/phase1/venv`. The existing root `.venv` and
  installed dependencies from the aborted port were not modified or reused as
  the pilot environment. Its interpreter was used to bootstrap the new venv.
- Each `run.py` invocation requires a nonexistent external directory. It copies
  project inputs and verifies historical demo files plus `images/logo.png`
  against `migration/baseline-output.json` before staging them.
- The demo bundles are deliberately historical binaries, not a Phase 1 rebuild.
  The source worktree, baseline outputs, and baseline reports remain unchanged.
- Generated output, logs, previews, scratch files, and reports live under the
  run directory on disk, not tmpfs. Browser downloads live in
  `~/tmp/ila/phase1/browsers`. No cleanup or overwrite of previous runs is done.
- The CLI unpacks its bundled core under `~/.ptx/2.52.3/`. No installed source
  was patched and no npm install was run inside that core.

This is not yet a hermetic build: the legacy Nix flake supplies TeX Live 2021,
Jing and Node 16; upstream HTML fetches Runestone Services (8.2.10 observed) and
uses its bundled prebuilt theme. Runestone resolution is not yet locked.

## Commands

Run these commands from the repository root. Prerequisites are Nix and uv
0.12.5; the latter currently exists at `~/tmp/ila/phase1/venv/bin/uv` rather than
on the default PATH. On a fresh machine, provision uv first and use that binary
in the first command instead. `uv sync` may download Python when necessary.

```bash
env UV_PROJECT_ENVIRONMENT="$HOME/tmp/ila/phase1/venv" "$HOME/tmp/ila/phase1/venv/bin/uv" sync --locked --project migration/phase1 --python 3.12.14
"$HOME/tmp/ila/phase1/venv/bin/python" -B -m unittest discover -s migration/phase1/tests -v
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 PLAYWRIGHT_BROWSERS_PATH="$HOME/tmp/ila/phase1/browsers" "$HOME/tmp/ila/phase1/venv/bin/playwright" install chromium
nix develop --no-update-lock-file -c env -u PYTHONPATH LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 PLAYWRIGHT_BROWSERS_PATH="$HOME/tmp/ila/phase1/browsers" "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase1/run.py --run "$HOME/tmp/ila/phase1/run-007"
```

Choose a fresh run number each time. `--targets html print` omits the currently
blocked FOP route. All requested targets are attempted even if validation fails,
so failure evidence can be collected. A nonzero validation/build result, timeout,
or absent expected artifact makes the runner exit nonzero. An independent Jing
invocation also checks the single-file fixture, since the CLI can misreport a
validator launch failure as success. Child process groups are killed and reaped
on timeout or interruption. A `generated` status
does not waive diagnostics or establish semantic/visual/accessibility approval.

The per-command preload is needed by native Python extensions in this mixed
Nix/Debian environment. `run.py` removes `LD_PRELOAD` from the CLI's environment
after its Python process starts, before child tools are launched: propagating
Debian's library into old Nix executables causes GLIBC version failures.
`PYTHONPATH` must also be removed to avoid loading Nix Python 3.9 modules into
the Python 3.12 environment. These are launch adaptations, not dependency edits.

Measurement commands for the existing checkpoint (use fresh evidence paths if
repeating them):

```bash
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase1/browser.py --root "$HOME/tmp/ila/phase1/run-005/output/html" --output "$HOME/tmp/ila/phase1/run-005/browser-next/report.json" --artifacts "$HOME/tmp/ila/phase1/run-005/browser-next/screenshots"
python3 scripts/phase0_pdf.py --pdf "$HOME/tmp/ila/phase1/run-005/output/print/main.pdf" --artifacts "$HOME/tmp/ila/phase1/run-005/pdf-next" --report "$HOME/tmp/ila/phase1/run-005/pdf-next.json" --pages 1 2 3 4
python3 -m http.server 8128 --bind 127.0.0.1 --directory "$HOME/tmp/ila/phase1/run-005/output/html"
```

`browser.py` fails on assertion, JavaScript, or network errors. It hashes each
screenshot and binds the run to an aggregate input-tree SHA-256: sorted file
paths, each encoded as one JSON `[relative_path, file_sha256]` line. Counts of
CHTML containers and document scroll width are smoke checks, not a substitute
for examining equations, embedded content, or accessible mathematical speech.

## First Checkpoint

Evidence: `~/tmp/ila/phase1/run-005/`; earlier unsuccessful environment and source
probes remain in `run-001` through `run-004`. Run-006 verifies the hardened runner
with independent Jing validation and another HTML build. See `initial-results.md` for results,
checksums, and the open gates. HTML opens at `output/html/index.html`; print PDF
is `output/print/main.pdf`. No tagged PDF was produced.

Next system packages requested from the author, for Debian Trixie:

```bash
sudo apt-get install nodejs npm default-jre-headless fop
```

Use Node 20 or newer for the current math toolchain, not Nix's Node 16. Before
retrying FOP, create an isolated npm project outside installed core, pin
`@mathjax/src@4.1.3`, `@mathjax/mathjax-newcm-font@4.1.3`,
`speech-rule-engine@5.0.0-rc.4`, and `yargs@17.7.2`, and retain its npm lockfile.
Install with `--ignore-scripts --engine-strict` and pass that project's
`node_modules` through `NODE_PATH`; the inspected upstream script uses CommonJS
resolution. Verify actual resolution and SVG/speech generation before relying
on this route. This isolated npm setup is identified, not yet executed or locked.
Ensure the Debian Node executable takes precedence when borrowing TeX from Nix.

Snapshots and backups are managed by the author. Local copies and this log do
not attest to backup completion. The fixture is a private engineering excerpt;
standalone distribution needs appropriate license material and author review.
