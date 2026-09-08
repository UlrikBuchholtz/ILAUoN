# Phase 1 Hard-Case Pilot

Status on 2026-09-08: **technical pilot implemented; review gates remain open**.
This nested project neither replaces the legacy publisher nor converts whole
chapters. The publication base remains **https://ulrikbuchholtz.dk/ila/**.
Nothing has been deployed. Pilot page names are not promised public URLs.

See `checkpoint.md` for the current results and PDF feasibility assessment,
`coverage.md` for excerpt provenance, `customizations.md` for the small HTML
customization layer, and `computation.md` for browser Python and its security
limits. `initial-results.md` preserves the earlier run-005 checkpoint.

## Current Outputs

The reference for this checkpoint is `~/tmp/ila/phase1/run-011/`:

- `output/html/index.html`: six-section HTML pilot.
- `output/print/main.pdf`: seven-page conventional, untagged PDF.
- `output/accessible/main.pdf`: seven-page FOP PDF, tagged and machine-validated
  with veraPDF's PDF/UA-1 profile; not approved for release or assistive use.
- `report.json`, `logs/`, and `tmp/`: commands, input hashes, diagnostics, and
  retained intermediate LaTeX/FO/math representations.
- `browser/`: 18 screenshots and browser measurements.
- `computation-report.json`: integrated Pyodide tests, without an asset overlay.
- `pdf-validation.json`: PDF/FO structure inspection, veraPDF report and stderr.
- `pdf-print/` and `pdf-accessible/`: every page captured and text extracted.
- `links.json`: static HTML link/fragment audit.

Earlier runs remain intact. Do not overwrite these historical evidence paths.
The author manages snapshots, backups, and eventual cleanup.

## Tooling

| Component | Pin or observed version |
| --- | --- |
| PreTeXt CLI | 2.52.3 |
| PreTeXt core | `2c8806b9988f855e94d185fb145226bf6c0a5b20` |
| Native Python | 3.12.14; minor version restricted by `pyproject.toml` |
| Native SymPy | 1.14.0 |
| Python package resolution | `uv.lock`, generated with uv 0.12.5 |
| Debian Node / npm | 20.19.2 / 9.2.0 |
| Debian Java / FOP | OpenJDK 21.0.11 / FOP 2.10 |
| MathJax / fonts / SRE | 4.1.3 / 4.1.3 / 5.0.0-rc.4, `math/package-lock.json` |
| CSS builder resolution | `theme/package-lock.json` |
| TeX / Jing | Borrowed from the unchanged pinned legacy Nix environment |
| Browser Python | Pyodide 0.29.3, Python 3.13.2, bundled SymPy 1.13.3 |
| PDF validator | veraPDF Greenfield 1.30.2, installed locally |

The Python environment is `~/tmp/ila/phase1/venv`, separate from the root
`.venv` and aborted-port leftovers. Math npm packages are installed under
`~/tmp/ila/phase1/math-node20`; `NODE_PATH` supplies them to upstream's CommonJS
math script without installing anything in its `mjsre` directory.

`run.py` verifies the math manifest/lock, checks baseline demo assets and logo
against `migration/baseline-output.json`, and requires a nonexistent output
directory outside the repository and Phase 0. It stages source, publication,
XSL, and assets there. Its subprocesses prefer Debian Node/Java/FOP and borrow
TeX/Jing from Nix. Process groups are killed and reaped on interruption/timeout.

Each run now gives the CLI its own `HOME`, so unpacked core, caches and CSS
dependencies live under `run-NNN/home/`, not the author's shared `~/.ptx`.
CSS dependencies are installed by `npm ci --ignore-scripts` using the retained
lock before HTML generation. In run-007, upstream automatically ran npm inside
the shared extracted CSS-builder cache when the new Node became available.
That side effect was discovered and contained starting with run-008; it is not
described as a pristine earlier cache. No upstream source was patched.

This is still not a fully hermetic modern build: upstream fetches Runestone
Services through `latest` (8.2.10 observed), browser runtime assets come from a
pinned CDN path, and system package closure is not locked by these files. The
CSS-builder's initial npm audit reported two high-severity issues; these are
unassessed tool reports, not an exploitability finding. No audit-fix was run.

## Build

Commands are run from the repository root. Debian prerequisites are `nodejs`,
`npm`, `default-jre-headless`, and `fop`; Nix and uv 0.12.5 are also required.
The local uv binary currently lives in the pilot venv, not the default PATH.
On a fresh machine, provision uv first and substitute that executable.

```bash
env UV_PROJECT_ENVIRONMENT="$HOME/tmp/ila/phase1/venv" "$HOME/tmp/ila/phase1/venv/bin/uv" sync --locked --project migration/phase1 --python 3.12.14
mkdir -p "$HOME/tmp/ila/phase1/math-node20"
cp migration/phase1/math/package.json migration/phase1/math/package-lock.json "$HOME/tmp/ila/phase1/math-node20/"
npm ci --prefix "$HOME/tmp/ila/phase1/math-node20" --ignore-scripts --engine-strict --no-audit --no-fund
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 PLAYWRIGHT_BROWSERS_PATH="$HOME/tmp/ila/phase1/browsers" "$HOME/tmp/ila/phase1/venv/bin/playwright" install chromium
"$HOME/tmp/ila/phase1/venv/bin/python" -B -m unittest discover -s migration/phase1/tests -v
nix develop --no-update-lock-file -c env -u PYTHONPATH LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 PLAYWRIGHT_BROWSERS_PATH="$HOME/tmp/ila/phase1/browsers" "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase1/run.py --run "$HOME/tmp/ila/phase1/run-012"
```

Choose a new run number each time. `--targets html print` omits FOP. Generation
continues after validation failures for diagnosis, but the overall command
fails on a failed step or blocking diagnostics. Missing alt text, overflow and
unsupported-feature diagnostics are not silently waived. Run-011 therefore
exits nonzero on FOP's unsupported font coverage-table warning even though all
three outputs generate. Independent Jing validation checks the single-file
fixture rather than trusting only the CLI's validator-launch behavior.

The library preload is specific to this mixed Nix/Debian Python environment.
The runner removes it from the CLI's environment after Python starts so it
does not break old Nix child executables. `PYTHONPATH` is also removed to avoid
loading Nix Python 3.9 modules into Python 3.12. Debug verbosity **and**
`--save-tmp-dirs` are required to retain core scratch files in this CLI version.

## Verify And View

These commands repeat measurements against run-011 using fresh destinations:

```bash
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase1/browser.py --root "$HOME/tmp/ila/phase1/run-011/output/html" --output "$HOME/tmp/ila/phase1/run-011/browser-next/report.json" --artifacts "$HOME/tmp/ila/phase1/run-011/browser-next/screenshots"
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 "$HOME/tmp/ila/phase1/venv/bin/python" migration/phase1/computation-check.py "$HOME/tmp/ila/phase1/run-011/output/html" "$HOME/tmp/ila/phase1/run-011/computation-next.json"
"$HOME/tmp/ila/phase1/venv/bin/python" migration/phase1/pdf-check.py --pdf "$HOME/tmp/ila/phase1/run-011/output/accessible/main.pdf" --fo "$HOME/tmp/ila/phase1/run-011/tmp/ptx-a1m8khb7/main.fo" --log "$HOME/tmp/ila/phase1/run-011/logs/accessible-command.log" --report "$HOME/tmp/ila/phase1/run-011/pdf-validation-next.json" --verapdf "$HOME/tmp/ila/phase1/verapdf-1.30.2/verapdf"
python3 -m http.server 8128 --bind 127.0.0.1 --directory "$HOME/tmp/ila/phase1/run-011/output/html"
```

For another build, use its FO path from `logs/accessible-command.log`; scratch
directory names are generated. The optional `--verapdf` adds the actual PDF/UA-1
validator; without it `pdf-check.py` performs structural checks only. The local
validator's signed download/provenance is recorded in `checkpoint.md`.

`browser.py` fails on assertions, JavaScript or network errors; warnings remain
review items. Its input-tree hash is SHA-256 over sorted JSON
`[relative_path, file_sha256]` lines. Screenshot hashes and computation input
hashes bind evidence to the tested bytes. None of these checks is an author
review, screen-reader test, or release authorization.
