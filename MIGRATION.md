# ILA Migration Assessment and Log

## Status and Decisions

Migration branch: `uon2`, created from legacy `uon` at
`f7fbb5e81eb55309d535e404291be2688f6dab0b` on 2026-09-05.
The old publication remains the reference; no book content or legacy build code
has been changed for the migration.

Accepted direction:

- Use upstream PreTeXt with a small, documented customization layer.
- Keep static-site hosting. Add custom browser Python 3 + SymPy using Pyodide.
- Replace PreTeX's SVG rendering of ordinary mathematics with portable semantic
  math through the standard PreTeXt/MathJax pipeline.
- Retain existing CoffeeScript/MathBox demonstrations as independently built
  embedded applications initially. Modernize them by family later.
- Keep conventional print PDF separate from accessible electronic PDF.
- Pilot accessible PDF on representative difficult content before promising
  whole-book conformance.
- Preserve content, teaching semantics, IDs, published URLs, and demo parameters.
- The hosted book base URL remains `https://ulrikbuchholtz.dk/ila/`.
- Do not merge the aborted port wholesale.

**Phase 0 is complete as of 2026-09-06 under the documented-limitations exit
gate. Phase 1 is accepted as of 2026-09-09. Phase 2 (modern build) is accepted as
of 2026-09-10; Phase 3 (content conversion) has not started.** Two successful
isolated legacy HTML/PDF builds, source/output inventories, a static fragment-link
audit, Chromium interaction checks, desktop/mobile-viewport screenshots, and
selected PDF page captures form the reference. Its archived evidence was
recovered and reverified after the environment restart. This is not accessibility
approval or bit-for-bit reproducibility. Firefox/WebGL coverage and author review
remain open. The author owns snapshots and backups; no backup completion is
asserted by this log. See the carry-forward list and Phase 1 checkpoint below.

## Assessment

### Source and Publishing Architecture

The authoritative entry point is `src/ila.xml`. Its active XInclude graph has
45 source XML files, 8 chapters, 37 sections, and 167 MathBox embeds. Another
21 top-level XML files are outside that graph; preserve these alternate and
supplementary materials separately from the active-edition migration.

The legacy platform combines a customized MathBook schema/XSL fork, local XSL
overrides, SCons, NixOS 22.05 packages, Compass/Ruby Sass, Mako/CoffeeScript,
MathBox, and a separate renderer named **PreTeX**, not PreTeXt.

`src/xsl/mathbook-html.xsl` disables MathJax. `pretex/` compiles ordinary math
through LaTeX, PDF, patched Inkscape, font extraction, and SVG insertion. The
visual results do not preserve dependable navigable mathematical structure.
Unknown glyphs can receive arbitrary alphabetic Unicode mappings in
`pretex/tounicode.py`, compromising text extraction and assistive technology.

`src/latex/macros.sty` and `spalign.sty` implement compact matrix/vector/system
syntax and redefine familiar commands. These cannot all become simple MathJax
macros. Bare LaTeX blocks can define state used by subsequent expressions, for
example in `src/matrix-mult.xml`. Separate portable math, diagram code, and
formatting/state declarations deliberately.

Custom elements and attributes include `specialcase`, `essential`, `bluebox`,
`latex-code`, `mathbox`, per-element labels, visibility controls, and numbering
overrides. Cross-reference phrasing and assessed-content distinctions depend on
these behaviors. Valid XML alone will not establish migration correctness.

The PDF follows a separate XML-to-LaTeX pipeline (`src/SConscript`). Its current
interactive-figure fallback is a framed online link, not an equivalent diagram
or activity. Descriptions and noninteractive learning alternatives need author
input regardless of renderer.

### Accessible PDF

Upstream was checked during the initial assessment on 2026-09-05; these are
capabilities to pin and test in Phase 1, not dependencies introduced in Phase 0.

| Route | Benefit | Constraint |
| --- | --- | --- |
| Standard PreTeXt / LaTeX | Established print typography | No automatic integration of modern LaTeX tagging found in the current exporter |
| PreTeXt / XSL-FO / Apache FOP | Experimental tagged PDF targeting PDF/UA-1 | Incomplete coverage/layout; math SVG has spoken alternatives rather than navigable MathML |
| Custom modern LuaLaTeX tagging | Potential for MathML-associated/structured mathematics | Custom integration and compatibility work, with reader testing |

The FOP method is exposed in released CLI 2.52.3 as a PDF target with
`pdf-method="pdf-fo"`. The inspected core revision was
`2c8806b9988f855e94d185fb145226bf6c0a5b20`. It uses MathJax/Speech Rule Engine,
bundled fonts, and post-processing repairs. TikZ assets still need LaTeX and
explicit FO-compatible SVG preparation. Unsupported-element and overflow
diagnostics must become blockers during the pilot.

Modern LaTeX tagging requires metadata before `\documentclass`; the existing
PreTeXt early-preamble hook is too late. Do not present this alternative as a
single publication setting. Agree on the required PDF standard, mathematical
navigation, and reader/screen-reader combinations with university accessibility
staff. A validator pass does not establish usable mathematical speech.

### Python and Graphics

Native browser ActiveCode `language="python"` uses Skulpt, not full CPython with
stock SymPy. ActiveCode `language="python3"` is a Runestone server route, with
package availability dependent on the server. SageCell Python supports SymPy
but requires a remote service. The accepted custom Pyodide option supports
actual Python/SymPy while preserving static hosting, at the cost of integration,
runtime download, memory use, and accessibility maintenance.

Design the coding component around lazy loading, worker execution, Stop/Reset,
explicit state rules, pinned packages, accessible editor/errors/results, and
static code/results for PDF. A worker alone is not a security boundary: define
origin isolation and network policy. Keep Python out of rendering/drag loops.
Begin with exact RREF/nullspaces, eigenvectors, and least squares. Five existing
Python cells, four using SymPy, are in inactive `src/lu-decomposition.xml`; their
timing and floating-point narratives require revalidation.

The legacy graphics have 33 generated demo targets plus rabbits and the cover.
They include linked views, GPU picking, custom shaders, and row-operation
history. Bundled Three.js is r71. Preserve the educational behavior and URL
configuration contracts; do not attempt a blind dependency upgrade. Initial
replacement candidates are DOM/MathML row reduction, the rabbits chart with a
data table, and SVG-based 2D vectors. Linked 3D views and dynamics come later.

### Aborted-Port Findings

`aborted-port` is one commit, `e96ed016c2de348e2620af01eec9506bbbb9503a`, above
the legacy baseline: 129 changed paths, including 48 deletions. Useful ideas
include a standard project manifest, locked tooling, and a small demo adapter.
Its rewritten chapters are not a safe starting point.

Evidenced regressions (paths below refer to that branch):

- `src/vector-spans.xml:58-69`: malformed equation-system conversion residue.
- `src/vectors-matrices.xml:943-950`: a three-entry vector becomes six rows.
- `src/determinant-cofactors.xml`: Cramer's rule/inverse subsection deleted.
- `scripts/build_demos.py`: required prebuilt bundles/jQuery not tracked;
  dynamics library omitted; indirectly linked `rrinter` excluded.
- Essential-definition and visibility distinctions lost without consistent
  editorial changes. Concept-library content and custom site behavior removed.
- Installed PreTeXt dependency patched outside its lockfile.

Use these failures as regression cases. Commit the new converter and its tests;
reject unfamiliar syntax rather than guessing. Avoid mass serialization churn
and keep editorial changes separate from mechanical conversions.

## Plan and Gates

1. **Phase 0: baseline.** Restore exact legacy dependencies in isolation, build
   with a fresh math cache, inventory source/outputs/URLs/configurations, record
   warnings and representative screenshots. Exit with a trustworthy reference
   or documented limitations.
2. **Phase 1: hard-case pilot.** Test nested matrices, row operations, stateful
   macros, custom blocks, hidden content, TikZ, three representative demos,
   tables/footnotes, and one SymPy cell in HTML and both PDF routes. Decide PDF
   feasibility before mass conversion.
3. **Phase 2: modern build.** Pin upstream tools, introduce standard project and
   publication files, separate demo builds, fail on missing assets/errors, and
   verify clean-checkout CI. Do not mutate installed dependencies.
4. **Phase 3: content conversion.** Use XML-aware transformation and tested
   notation parsing in reviewable batches. Preserve IDs, order, captions,
   dimensions, essential markers, and visibility semantics. Review rendered
   mathematics as well as schema validity.
5. **Phase 4: accessibility.** Author figure alternatives; improve keyboard
   controls, titles, zoom, motion, and color-independent meaning. Validate the
   selected PDF standard and actual assistive-technology behavior.
6. **Phase 5: computation and graphics.** Roll out tested Pyodide activities;
   replace demos by family without breaking parameter URLs or operation history.
7. **Phase 6: release.** Publish a parallel preview, audit links/redirects and
   complete chapters, retain rollback, and retire the old publisher only after
   approval and independently reproducible modern builds.

Initial planning ranges: 2-4 person-weeks for baseline/pilot, 6-12 additional for
build/content conversion, 4-10+ for accessibility depending on requirements,
and 1-3 for initial reusable SymPy activities. Broad graphics replacement is a
separate multi-month effort. These are preliminary ranges, not commitments;
mathematical review and descriptions require author time.

## Phase 0 Reference

### Revisions

| Component | Commit |
| --- | --- |
| Book | `f7fbb5e81eb55309d535e404291be2688f6dab0b` |
| MathBook fork | `736ac15a221976dae58b24ae61a5a1d9791eef27` |
| MathBook assets | `34eec104496255d1607b9397d55a8fe8cb25adc4` |
| MathBox | `916e4b925305d71dc36d45db39b7b282dedcccbf` |
| ShaderGraph | `7f53f38152d73e59f873f141a6eb9b11a85c85b2` |
| Threestrap | `bf301039f2f390cfb6e18a00faeb43ff3f395c4d` |
| nixpkgs | `478f3cbc8448b5852539d785fbfe9a53304133be` |

The legacy flake successfully built patched Inkscape 1.1.2. Observed tooling
includes Nix 2.35.2 (host), SCons 4.1.0, Node 16.16.0, npm 8.11.0, Python 3.9,
and TeX Live 2021. The first Nix evaluation hit a 120-second tool timeout;
retrying with a longer timeout succeeded without changing the flake or lock.

### Local Artifacts and Commands

The current persistent reference is `/home/ulrik/tmp/ila/phase0`, verified on
2026-09-06 to reside on NVMe-backed Btrfs, not tmpfs:

- `output/`: complete historical site and PDF (4,662 files).
- `evidence/baseline/`: retained first-build logs, PDF/index diagnostics, and npm
  lockfiles, preserving their original archive-relative paths.
- `evidence/checks/`: supplemental screenshots, reports, repeat-build logs, and
  repeat output inventory, preserving their original archive-relative paths.
- `archives/`: checksum-verified copies of both original archives.
- `verification/`: regenerated output inventory and link audit, both identical
  to the committed baseline reports.

Use this reference rather than `/tmp` for future comparisons. Treat `output/`
and historical evidence as immutable; write new captures/reports elsewhere.
The original checkout archives and recovered `/tmp` copy were left untouched.
Disk-backed storage avoids `/tmp` loss but is not managed backup or a guarantee
against manual cleanup; preserve this directory when cleaning `~/tmp`.

The original detached worktree and raw output locations were temporary, not
deployment paths (see recovery status below):

- Source worktree: `/tmp/opencode/ila-phase0`
- Built site and PDF: `/tmp/opencode/ila-phase0-output`
- Fresh cache and intermediate TeX/HTML: `/tmp/opencode/ila-phase0-cache`
- Logs: `/tmp/opencode/ila-phase0-subpackages.log` and
  `/tmp/opencode/ila-phase0-build.log`
- Source manifest: `migration/baseline-source.json`
- Output hashes, paths, and HTML anchors: `migration/baseline-output.json`
- Local archive (ignored by Git):
  `migration/artifacts/uon-f7fbb5e-baseline.tar.gz`

The archive retains the complete final output, both build logs, final PDF/index
logs, and the root/MathBox npm lockfiles from this build. It does not include
the full intermediate math cache or the Nix store. Archive contents were
compared successfully against the original files with `tar --diff`.

Archive SHA-256:

```text
c19b70470841fd65849473e5c9273b42f161fa47603fc88f5555d8b208bdcc5b
```

This archive survives `/tmp` cleanup but is only a local copy. Copy it into
managed backup/artifact storage before retiring this checkout. The manifests
are intended for version control; the large binary archive is not.

Recovery status on 2026-09-06: the environment restarted and `/tmp/opencode`
was empty. Both archives survived in this checkout with the exact checksums
recorded here. The baseline archive was extracted back into `/tmp/opencode`,
restoring the complete output and retained logs/lockfiles, **not** the source
worktree, installed dependencies, or full math cache. Git still lists the two
missing detached worktrees as prunable; their registrations were left untouched.
Do not run the original build commands against these partial recovered paths.
The recovered output and all archived evidence were subsequently copied to the
persistent reference above and independently verified there.

To recover and verify output again, use a new empty directory (commands below
assume `$HOME/tmp/ila` exists and `phase0-recovery` does not):

```bash
sha256sum "$HOME/tmp/ila/phase0/archives/"*.tar.gz
gzip -t "$HOME/tmp/ila/phase0/archives/"*.tar.gz
mkdir "$HOME/tmp/ila/phase0-recovery"
tar -xzf "$HOME/tmp/ila/phase0/archives/uon-f7fbb5e-baseline.tar.gz" -C "$HOME/tmp/ila/phase0-recovery"
python3 scripts/phase0_output_inventory.py --root "$HOME/tmp/ila/phase0-recovery/ila-phase0-output" --output "$HOME/tmp/ila/phase0-recovery/output.json"
cmp migration/baseline-output.json "$HOME/tmp/ila/phase0-recovery/output.json"
python3 scripts/phase0_links.py --root "$HOME/tmp/ila/phase0-recovery/ila-phase0-output" --output "$HOME/tmp/ila/phase0-recovery/links.json"
cmp migration/baseline-links.json "$HOME/tmp/ila/phase0-recovery/links.json"
```

Compare both printed SHA-256 values with those recorded in this document before
extracting. The inventory and link comparisons passed byte-for-byte during
recovery; this checks the saved baseline, not a third build.

Commands run from the main checkout to prepare isolation:

```bash
git worktree add --detach /tmp/opencode/ila-phase0 f7fbb5e81eb55309d535e404291be2688f6dab0b
```

Commands run from that detached worktree:

```bash
git submodule update --init --recursive
nix develop --no-update-lock-file -c scons --version
nix develop --no-update-lock-file -c scons subpackages --build-dir=/tmp/opencode/ila-phase0-output --cache-dir=/tmp/opencode/ila-phase0-cache
nix develop --no-update-lock-file -c scons --build-pdf --build-dir=/tmp/opencode/ila-phase0-output --cache-dir=/tmp/opencode/ila-phase0-cache
```

Use `--option=value` for the path options: the space-separated invocation
failed with `--cache-dir option requires an argument`. Build logs were captured
with `tee` and shell `pipefail`. This first build used new output/cache paths,
so no cache deletion or production/scratch flags were necessary. A second cold
build must use different fresh paths or deliberately clear only its own cache.

SCons automatically ran `npm install` at the root and in MathBox. Submodule
revisions and Nix dependencies are pinned, but the full npm resolution is not
equivalently locked; this and generated dates prevent a claim of complete
reproducibility. No audit-fix command was run. The reference worktree's tracked
files remained unchanged after the build.

The original inventory-generation commands used a standard-library Python 3
interpreter from the main checkout (for example inside the legacy Nix
development environment). These are historical commands, not recovery steps:

```bash
python3 scripts/phase0_inventory.py --root /tmp/opencode/ila-phase0 --output migration/baseline-source.json
python3 scripts/phase0_output_inventory.py --root /tmp/opencode/ila-phase0-output --output migration/baseline-output.json
```

These are historical baseline manifests: do not overwrite them with migrated
output. Source paths/hashes are independent of checkout location. Source
element positions are parsed preorder indices, not line numbers. The output
manifest distinguishes knowl fragments from standalone pages and records
actual generated paths/anchors; it does not validate fragment links or runtime.

### Verified Results

| Check | Result |
| --- | --- |
| Source include closure | 45 files, 44 active XIncludes |
| Source divisions / demos | 8 chapters, 37 sections, 167 MathBox elements |
| Source IDs | 391 occurrences, 389 unique IDs |
| Source xrefs | 664 targets; none missing, 3 occurrences ambiguous |
| Final artifact files | 4,662, all nonempty |
| Intermediate HTML covered by final output | 4,511 / 4,511 |
| Final HTML | 4,547 files: 4,451 knowls and 96 other HTML files |
| Demo HTML | 34 files |
| Unprocessed final `text/x-latex` scripts | 0 (35,248 in intermediate HTML, including duplicated knowl content) |
| PDF | 501 pages, 4,680,426 bytes; no tag structure |
| Local HTML URL references audited | 12,596; no missing file targets |
| Demo embed references audited | 572 references to 26 distinct existing demo paths |
| CSS URL references audited | 196; four missing font files |

Logs and output coverage were checked independently of the successful SCons
exit because PreTeX waits on asynchronous workers without retrieving their
results. No hidden worker failure was found. Inventory repeat runs were
byte-identical; active source hashes match the untouched main checkout.

### Known Baseline Defects

- Duplicate `linear-trans-pick-columns` ID in `src/linear-trans.xml` and
  `src/matrix-coords.xml`.
- Duplicate `solnsets-nontrivial` ID in `src/solnsets.xml` and
  `src/similarity.xml`. Both duplicates also produce PDF label warnings.
- Four absent `demos/fonts/glyphicons-halflings-regular` files (`eot`, `woff`,
  `ttf`, `svg`) referenced five times by rabbits' bundled Bootstrap CSS. No
  glyphicon use was found in the rabbits HTML; runtime effect is untested.
- Final PDF index pass rejects `\indexentry{|hyperpage}{349}` (illegal null
  field), accepts 706 entries, and reports three conflicting-entry warnings.
- PDF reports overfull/underfull boxes, nullfont missing-character diagnostics,
  invalid `\tiny` uses in math, and two invalid `split` placements. Final pass
  has no undefined-reference warnings. Visual significance needs review.
- PDF is not tagged: neither `MarkInfo` nor a structure tree is present.
- Install-time npm reports: root 14 vulnerabilities (1 critical), MathBox 69
  (18 critical). These are tool reports, not assessed exploitability or a
  completed security audit.
- Sixty pages reference external SageCell-hosted jQuery. External availability
  was not checked in the initial static audit. The subsequent Chromium sample
  recorded no request failures, but this is not an offline-availability test;
  static hosting does not currently mean self-contained assets.

Do not silently fix these in the reference. Future fixes belong in separately
reviewed migration changes so they remain distinguishable from regressions.

### Browser, Link, and PDF Checks

System tools installed by the author and verified on 2026-09-05:
Chromium 150.0.7871.100, Firefox 140.12.0esr, and Poppler 25.03.0.
The existing `.venv` has Playwright, but its native Python extension needs
`LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6` in this environment.
This is a per-command workaround; no global environment or legacy flake edits
were made. Setting the entire system `LD_LIBRARY_PATH` instead stalled the
initial attempt and is not the tested invocation. The following commands record
the original run; new runs should use the persistent output root above and
fresh report/capture destinations, not overwrite the historical evidence.

```bash
env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 .venv/bin/python scripts/phase0_browser.py --root /tmp/opencode/ila-phase0-output
.venv/bin/python scripts/phase0_links.py --root /tmp/opencode/ila-phase0-output --output migration/baseline-links.json
.venv/bin/python scripts/phase0_pdf.py --pdf /tmp/opencode/ila-phase0-output/ila.pdf --artifacts migration/artifacts/pdf --report migration/baseline-pdf.json
```

`phase0_browser.py` owns a temporary loopback HTTP server and closes it and its
browser contexts. The report records actual launch flags, network/console
events, viewports, and evidence for assertions. The runner does not intercept
or substitute dependencies. Baseline assertion failures are recorded, not
treated as process failures: this is a measurement tool, not yet a CI gate.
For future browser runs, pass fresh `--output` and `--artifacts` destinations rather
than the historical defaults. An infrastructure exception can leave an old
report alongside partially overwritten screenshots; process success alone
also does not establish complete test coverage or clean browser events.

Chromium results (`migration/baseline-browser.json`): **21 passes, 10 failures**.
Twenty-three viewport screenshots are in `migration/artifacts/browser/`.

- Seven representative sections fit the 1440x1000 desktop viewport. All seven
  overflow horizontally at 390x844 (scroll widths 543-647px). This is viewport
  testing, not real-phone or touch emulation.
- Vector rendering has active canvas pixels and coordinate controls update the
  vector. Pixel activity alone is not mathematical correctness verification.
- Rowred1 Next works; the handoff opens rrinter with the matrix and two prior
  operations preserved. A row multiplication updates the matrix and URL.
- Composition renders three active scenes with the expected transformed
  vectors; the common axes control works.
- Knowl disclosure and collapse work by keyboard on desktop and mobile.
- The mobile menu is Tab-reachable and opens with Enter, but has no
  `aria-expanded` and does not close with Escape.
- Dynamics renders, but the Multiply GUI is absent. Source confirms
  `autoPlace: false` with no DOM attachment.
- No page JavaScript errors, request failures, or HTTP errors were recorded in
  the final sampled run. Rendering performance warnings were retained.

The generated-link audit (`migration/baseline-links.json`) checks 13,172
references across 4,547 HTML files. It found no missing files, but **1,372
missing static fragment targets**: 1,368 references from knowls and four index
letters (`indexletter-j/x/y/z`). These counts are not all browser-confirmed
failures. This audit includes knowl attributes and therefore has a different
reference count from the earlier file-only audit.

Browser follow-up confirmed failures for these direct URLs:

- `characteristic-polynomial.html#charpoly-eg-0-eval`
- `characteristic-polynomial.html#charpoly-eg-22`
- `complex-eigenvalues.html#cplx-evals-eg22-a`
- `index-1.html#indexletter-j` and the corresponding `x`, `y`, and `z` links.

The three example links did not instantiate a target or scroll on startup.
Clicking their knowl controls loaded content successfully, but still did not
create the semantic fragment ID. `knowl-id` attributes and generated numeric
`kuid-*` IDs are not the promised anchors. The other knowl references were not
systematically browser-tested; audit counts are reference occurrences, not
distinct targets. Preserve this distinction when planning link fixes.

Poppler confirms the original PDF is 501 pages, Letter size, and untagged.
Physical pages 1, 30, 50, 180, 245, 296, 426, and 458 were rendered and their
text extracted to `migration/artifacts/pdf/`; hashes and metadata are in
`migration/baseline-pdf.json`. Physical page numbers differ from printed labels.
Selected composition diagrams, determinant calculations, and projection
matrices were visually inspected. This is not a full proofreading or semantic
math-accessibility review.

Firefox starts, but system Firefox does not provide Playwright's patched
Juggler protocol. The direct Playwright launch failed; that does not indicate
a book failure. A separate native headless `file://` screenshot of the vector
demo displayed the WebGL fallback, with `libpci`/GPU diagnostics. It is retained
as `migration/artifacts/browser/firefox-vector-file-smoke.png`, not counted as
a successful Firefox interaction test. Use a working headed/WebGL session
with Selenium/geckodriver, or Playwright's own Firefox build, for full coverage.

### Repeat Build

A second detached worktree, `/tmp/opencode/ila-phase0-repeat`, built the same
commit with newly installed submodules, root/MathBox node_modules, npm download
cache, output, and math cache. Exact commands and comparison results are in
`migration/baseline-repeat-build.json`. The Nix store was shared; investigation
also found the legacy hard-coded `/tmp/mako_modules` cache is shared. Thus this
is not a fully hermetic build experiment.

- Both SCons commands succeeded; tracked files/submodules remain unchanged.
- Same 4,662 artifact paths, all nonempty; all 4,511 intermediate HTML files
  processed, with zero final unprocessed LaTeX scripts.
- Root and MathBox npm lockfiles match the first build.
- PDF again has 501 pages and 4,680,426 bytes.
- 965 artifact hashes match; 3,697 differ. Investigated differences include
  embedded-font timestamps, generated SVG IDs, worktree paths in JavaScript
  source maps and dependent hashes, and PDF dates/document ID.
- HTML ID inventories differ in 145 files, confined to generated SVG path and
  clipPath numbers. These are not changed book-level semantic anchors.
- Four changed JS bundles match outside source maps; PDFs match outside dates
  and document ID. No baseline files were normalized or overwritten.

This supports repeatable generation of the same artifact structure, not
byte-deterministic output or exhaustive visual equivalence.

Supplemental screenshots, reports, repeat-build logs, and the repeat output
manifest are archived in the ignored local file
`migration/artifacts/uon-f7fbb5e-phase0-checks.tar.gz`. Compression integrity was
verified with `gzip -t`. SHA-256:

```text
e383b95c9b709a0d29056975e8e51afcd314015b7566a66697df0fe995c6cbdc
```

### Phase 0 Exit and Carry-Forward

The Phase 0 gate is satisfied: pinned legacy revisions were built in isolation,
the source and generated publication were inventoried, warnings and known
defects were recorded, representative visual/interaction evidence was retained,
and archived output survived recovery with exact manifest agreement. No legacy
content or publisher changes were needed. This closes baseline collection, not
mathematical, accessibility, security, or release approval.

Carry these items into subsequent phases; they do not block the hard-case pilot:

- Author review of representative screenshots/PDFs and difficult mathematical
  content against intended teaching behavior.
- Full Firefox testing in a working WebGL environment; real-device/touch and
  assistive-technology checks remain outside the completed Chromium sample.
- Reconcile duplicate source IDs and broken fragment targets in separately
  reviewed changes, not by altering the historical baseline.
- Snapshots and managed backups are author-owned as of 2026-09-06. Preserve both
  local artifact archives and the persistent reference until the author decides
  cleanup is safe; engineering verification does not attest to backup completion.
- Before using the measurement tools as migration CI gates, add explicit expected
  test coverage and failure policy, bind browser evidence to input/output hashes,
  and make the original ad hoc build-completeness checks reusable. Inventory
  regeneration alone does not repeat the intermediate-output or warning audits.

## Phase 1 Checkpoint

The isolated project is `migration/phase1/`; setup and commands are in its
`README.md`, excerpt mappings in `coverage.md`, and evidence/checksums/open gates
in `checkpoint.md`. `initial-results.md` preserves the earlier run-005 checkpoint.
This is a hand-authored pilot, not a converter or a replacement for the root
build. **The author accepted the pilot in `migration/phase1/author-notes.md`.
HTML is the accessibility target; accessible PDF is optional and deferred.**

- Pinned PreTeXt 2.52.3 and core `2c8806b9988f855e94d185fb145226bf6c0a5b20`
  in a fresh environment, with Python dependencies locked in `uv.lock`.
- The six sections cover nested matrix products, all row-operation steps,
  self-contained color notation, shared-helper TikZ diagrams, provisional custom
  blocks, hidden paragraphs/nested proofs and a visible-proof exception, an
  explicit Warning, a semantic-header table, footnote, three preserved demo
  contracts and their authored static alternatives, and browser SymPy.
- Fourteen source/algebra/SymPy tests pass. Development-schema validation,
  validation-plus, and independent Jing pass, with three experimental iframe
  constructs. No general notation converter has been implemented.
- Current run: `~/tmp/ila/phase1/run-011`. HTML browser checks have 311 passes,
  zero failures, zero JavaScript/network errors, and seven warnings: four legacy
  demo-interior overflow observations and three MathJax-focused Escape cases.
  All six sections were checked in desktop/mobile viewports; 18 captures retained.
- The sandboxed Pyodide component passes 27 integrated checks, including lazy
  worker execution, Stop/Reset, fresh runtime state, keyboard controls, and
  opaque-origin isolation. Its bundled SymPy 1.13.3 differs from native 1.14.0;
  the selected float example nevertheless produces identical output. Security
  and CDN limitations are explicit in `computation.md`.
- Conventional and FOP PDFs both build to seven Letter pages. The FOP PDF is
  tagged, has six table-header cells, and has no missing/placeholder image alt
  text or FO overflow diagnostics. Both PDFs' full page sets were captured.
- veraPDF 1.30.2 reports a PDF/UA-1 profile pass: 106 rules and 34,388 checks
  passed, no failures. This establishes machine-check feasibility for the sample,
  not usable mathematical navigation or whole-book conformance. Mathematics is
  represented as figures with spoken alternatives, not a navigable math tree.
- FOP's unsupported font coverage-table warning and veraPDF's ToUnicode parser
  warnings remain review blockers; they were not suppressed. The full runner
  deliberately exits nonzero on the unsupported diagnostic. Author and actual
  reader/screen-reader review, Firefox/WebGL and real-device checks remain open.
- Math and CSS dependency resolutions are now locked. Each run has its own
  extracted core/resource HOME to contain upstream automatic npm installs;
  Runestone's `latest` resolution remains unpinned. No upstream source patches,
  legacy source changes, mass conversion, Phase 2 work, or deployment occurred.

## Phase 2 Checkpoint

The modern build is `project.ptx`, `publication/`, `scripts/build.py`,
`scripts/build_demos.py` and `migration/phase2/`; commands, gates, pins and
accepted scope limits are in `migration/phase2/README.md`. **The author accepted
Phase 2 on 2026-09-10.** It builds the Phase 1 pilot fixture, not the book, and
nothing is deployed.

- Upstream tools are pinned: PreTeXt CLI 2.52.3 and core
  `2c8806b9988f855e94d185fb145226bf6c0a5b20`, Python 3.12 with `uv.lock`, the
  demo, math and theme npm locks, Runestone Services 8.2.10, and every GitHub
  Action by commit SHA. No installed dependency is patched, and each run gets its
  own `HOME`, `TMPDIR` and extracted core.
- Runestone assets are pinned by content, not only by version selector: 451 files
  hashed in `migration/phase2/runestone-assets.json` and verified on every build.
- Demos build independently of SCons, PreTeXt and historical output, from a Git
  index allowlist, with byte-identical repeated builds.
- The runner fails on nonzero commands, timeouts, schema failures, missing or
  empty assets, escaping asset paths, missing alt text, overflow, unsupported
  features and explicit failure diagnostics. Exactly two upstream lines are
  accepted, each by exact string and only where it can arise.
- Verified locally on Debian without Nix in `~/tmp/ila/phase2/run-003` (HTML and
  print) and `run-008` (all three targets), from a clean clone in
  `clean-run-001`, and hosted on GitHub Actions in runs 1 through 3, the last on
  commit `c516ecf` with the Action pins and the Runestone gate active.
- Evidence per run: `report.json` with input, implementation, lock, demo and
  output hashes, command lines, return codes and diagnostics, plus full logs.
  669 browser assertions, 27 Pyodide computation checks and 29 Python tests pass.

Accepted scope limits, recorded in `migration/phase2/README.md`: system-tool
drift is intended rather than tolerated, and byte-for-byte reproducible output is
out of scope. Neither is an unmet gate.

Carry these into later phases:

- The accessible FOP target stays optional and experimental. `run-008` produces a
  tagged seven-page PDF, but no new PDF/UA, screen-reader or human review was
  performed, and phase1's FOP limitations stand.
- Legacy demo dependencies remain at their historical versions, including a
  critical advisory in bundled Lodash 2.4.2. Deployment security review is still
  required before release.
- The two accepted diagnostics should be revisited if upstream fixes the
  preview-server port collision or FOP's coverage-table support. The collision is
  an upstream defect worth reporting.
- Refreshing `runestone-assets.json` after an intentional upstream repackage is a
  deliberate, reviewed act via `--record-runestone`, not a routine build step.
- Phase 0 and Phase 1 carry-forward items are unchanged: author review of
  mathematics, Firefox and real-device coverage, assistive-technology testing,
  and reconciling duplicate source IDs and broken fragment targets.

## Migration Log

### 2026-09-10: Phase 2 Acceptance

- The author accepted Phase 2 after the pinned workflow passed on GitHub in
  `UlrikBuchholtz/ILAUoN` run 3 for commit `c516ecf`:
  <https://github.com/UlrikBuchholtz/ILAUoN/actions/runs/34504841576>,
  conclusion `success`. That run exercised the Action SHA pins and the new
  Runestone content gate on runner hardware, against an independent fetch of the
  same tarball, so the recorded 451 hashes now hold across three machines.
- The Phase 2 gate is met: upstream tools pinned, standard project and
  publication files in place, demos built separately, the runner failing on
  missing assets and errors, clean-checkout and hosted CI verified, and no
  installed dependency mutated. See the Phase 2 Checkpoint above for evidence and
  carry-forward items.
- This closes the modern build scaffold. It is not a whole-book conversion,
  accessibility approval, security review, or release authorization, and nothing
  is deployed. The legacy publisher remains the live publication route.
- Phase 3, content conversion, has not started.

### 2026-09-10: Phase 2 Scope Decisions, Action Pinning and FOP Evidence

- Pinned every GitHub Action to a commit SHA with its release tag in a trailing
  comment: `checkout@3d3c42e`, `setup-uv@20cfd1b`, `setup-node@8207627` and
  `upload-artifact@043fb46`. No Action content can now change under a moving tag.
- **Accepted: system-tool drift.** The distribution's TeX, Java, Node, browser
  and Jing packages are not pinned by digest and differ between the author's
  workstation and the CI runner. Keeping tooling current is an objective of this
  migration, so this is a decision rather than an unmet gate. The CLI/core,
  Python, npm, Runestone and Action pins still bound what may change, and a
  build that breaks because a system package moved remains a real signal.
- **Accepted: byte-for-byte reproducible output is out of scope.** The print PDF
  embeds creation/modification timestamps, PreTeXt emits the build date through
  `<today/>`, and external assets are fetched at build time. No gate compares one
  run's output hashes with another's. Input-side determinism is what is checked:
  per-run input/implementation/lock/demo hashes, the demo builder's byte-identical
  repeat-build test, and external-asset hash matching between staging and output.
  Both decisions are recorded in `migration/phase2/README.md`.
- Drafted a Runestone content gate. `scripts/build.py` now hashes every file
  under `output/html/_static` except `_static/pretext`, which comes from the
  pinned CLI, and compares them with `migration/phase2/runestone-assets.json`.
  Added, removed or changed files fail the build. `--record-runestone` rewrites
  the manifest and marks the run as not gate-verified, so recording cannot be
  mistaken for passing. This addresses the version selector's inability to make
  remote content immutable.
- The recorded manifest holds 451 files from `run-003` and verifies clean against
  `run-004`, an independent fetch of the same tarball: identical file set, zero
  content differences. Eight runner tests pass, including tamper cases for each
  difference kind, the `_static/pretext` exclusion, a version mismatch and a
  missing manifest.
- The optional accessible target failed its gate in `run-004`, `run-005` and
  `run-006` for a reason unrelated to FOP. `generate-print` starts upstream's
  preview server on port 8888; the immediately following `generate-accessible`
  finds it still bound, logs `debug: http.server error: port 8888 in use`, falls
  back to a random port and completes with return code 0. The runner's pattern
  matches `error:` in that recovered debug line and blocked the build.
- Waiting for the port was implemented first and then reverted. In `run-006` the
  wait timed out after thirty seconds, and an isolated reproduction of upstream's
  server pattern showed the port is bindable immediately after that process ends,
  so no socket-reuse window is involved. Sampling `ss` during a build showed
  upstream's own live `python3` process holding `127.0.0.1:8888` in `LISTEN`, so
  a wait inside the same run cannot succeed.
- Accepted instead: that one exact line, only in a `generate-` step, alongside the
  existing FOP warning. Both are matched by exact string, kept in the logs and
  listed in `accepted_diagnostics`. The diagnostic pattern itself is unchanged, so
  every other port or server error remains blocking.
- Building the accessible target directly in `run-005`, after its generation had
  already completed, produced a tagged seven-page PDF from Apache FOP 2.10 whose
  only diagnostic is the accepted coverage-table warning. That was a labelled
  diagnostic continuation; `run-008` then passed all three targets through the
  ordinary gated runner: twelve steps at return code 0, no blocking diagnostics,
  451 Runestone assets verified, 657 output artifacts, and exactly one accepted
  diagnostic in each of the two steps that can raise one. Its accessible PDF is
  again tagged and seven pages. This is a local gate pass, not accessibility
  approval; no PDF/UA or screen-reader review was repeated.

### 2026-09-10: Hosted CI Pass and Action Runtime Update

- The modern build workflow completed successfully on GitHub Actions in
  `UlrikBuchholtz/ILAUoN`, run 1 of `Modern Fixture Build`, for commit `a6e66bc`
  on `uon2`: <https://github.com/UlrikBuchholtz/ILAUoN/actions/runs/34470464637>,
  conclusion `success` in about seven and a half minutes. This is the first
  hosted run and it exercises the apt/TeX selection, including the added
  `texlive-xetex`, that Phase 2 listed as unverified.
- The hosted runner warned that `actions/checkout@v4`, `actions/setup-node@v4`,
  `actions/upload-artifact@v4` and `astral-sh/setup-uv@v6` target Node.js 20 and
  are being forced onto Node.js 24, per GitHub's 2025-09-19 deprecation notice.
- Updated the workflow to `actions/checkout@v7`, `actions/setup-node@v7`,
  `actions/upload-artifact@v7` and `astral-sh/setup-uv@v10.0.1`. Each was checked
  at that ref for `runs.using: node24` and for the inputs this workflow passes.
- `astral-sh/setup-uv` publishes no floating major tag after v7; the `v8`, `v9`
  and `v10` refs do not exist. It is therefore pinned to an exact release, which
  also removes one of the un-pinned Action major tags recorded as a
  reproducibility gap. The other three remain floating major tags.
- Reviewed the skipped majors rather than assuming compatibility: checkout v5
  requires runner 2.327.1 or newer, satisfied by `ubuntu-24.04`; setup-node v5
  added automatic caching keyed on a `packageManager` field that the root
  `package.json` does not have, narrowed to npm in v6, and the workflow passes no
  `cache` input; upload-artifact v5 and v6 were the Node.js 24 moves and v7 adds
  an optional `archive` input defaulting to the existing zip behavior. This is a
  static review of upstream metadata and release notes, not a hosted rerun.
- The workflow's `node-version: '20.19.2'` is deliberately unchanged. The
  deprecation concerns the runtime that Actions themselves execute on, not the
  pinned Node used to build the demos.
- The updated workflow then completed successfully as run 2 for commit
  `42f8d5e`: <https://github.com/UlrikBuchholtz/ILAUoN/actions/runs/34487715338>,
  conclusion `success`, with the Node.js 20 deprecation warning gone. Two hosted
  runs on an ephemeral `ubuntu-24.04` runner are now recorded.
- Full system-tool closure, immutable Runestone asset hashes, and the optional
  accessible target remain open Phase 2 gates. Hosted success does not establish
  hermetic reproducibility or release approval.

### 2026-09-10: Debian-Native Phase 2 Verification

- Reproduced the strict Phase 2 build on the author's primary Debian trixie
  workstation using only system packages and the root lock, with **no Nix
  development shell and no `LD_PRELOAD` workaround**. The mixed Nix/Debian
  invocation recorded in `migration/phase2/README.md` is therefore one working
  route, not a requirement. Observed tools: uv 0.12.12, Python 3.12.14,
  Node 22.23.2, npm 10.9.8, Java 21.0.11, Jing 20241231, TeX Live 2025/dev
  Debian, FOP 2.10, system Chromium 150.0.7871.100.
- The recorded pins for uv (0.12.5) and Node (20.19.2) were not required here:
  `uv sync --locked` accepted the lock unchanged under the newer uv, and the
  demo builder still produced byte-identical repeated builds under Node 22.
  This is an observation about these two tools, not a general pin relaxation.
- `~/tmp/ila/phase2/run-002` failed `generate-html` because `xelatex` was absent:
  `PTX:ERROR: cannot locate executable ... as command 'xelatex'`, followed by
  LaTeX compilation failure for all seven authored latex-images. Upstream
  `pretext/utils.py` requires `xelatex` for `latex-image`, while SVG conversion
  goes through pyMuPDF, so `pdf2svg`/`librsvg2-bin` are not needed for it.
  Previous runs borrowed TeX from the flake's `scheme-full`, which includes
  XeTeX, so this gap had not been exercised. The failed run is retained.
- Added `texlive-xetex` to the workflow's apt list. Debian's recursive
  dependency closure for `texlive-latex-extra` does not include it and the
  workflow installs with `--no-install-recommends`, so a hosted run would very
  likely have failed identically. This removes one demonstrated blocker; the
  remainder of the apt/TeX selection is still unverified on GitHub.
- After the author installed `jing`, `texlive-xetex` and `fop`,
  `~/tmp/ila/phase2/run-003` passed the strict HTML and print gates: ten steps
  at return code 0 with no blocking diagnostics, independent Jing source and
  publication schema validation, all seven generated latex-image SVGs, Runestone
  8.2.10 verified in the emitted services manifest, 287 demo and 444 HTML local
  asset references checked, 656 output artifacts, and every copied external
  asset hash-matched to its staged input.
- Gates against that output: 6 runner, 14 source and 6 demo integration tests;
  669 browser assertions with zero failures, network errors and runtime errors,
  the same seven known warnings, and 18 screenshots under system Chromium;
  and 27 of 27 Pyodide computation checks. The browser and computation counts
  match the `clean-run-001` evidence.
- The seven warnings remain legacy-iframe interior overflow and the compat
  shim's Escape-restoration limitation on MathJax containers, both previously
  documented and accepted.
- The optional `accessible` FOP target was not exercised in this run, and no new
  PDF/UA, screen-reader or human review was performed. `git status` showed no
  build-created files in the checkout. This is local verification on one machine,
  not hosted CI verification, reproducibility closure, or release approval.

### 2026-09-09: Author Acceptance and Modern Build Commencement

- Accepted the Phase 1 checkpoint and authorization to clean the working directory
  and proceed to Phase 2. The historical results above remain unchanged.
- Author confirms keyboard/mobile behavior, Pyodide, Firefox/WebGL and touch
  behavior. Browser speech varies; these observations are not conformance claims.
- FOP's known coverage-table diagnostic is accepted for now; glyph-mapping
  warnings remain visible. Accessible PDF is not a required build/release gate.
- Corrected HTML equation scrolling, stable desktop menu layout, and consistent
  Charter typography, with regression assertions. PDF end markers and print/FO
  typography differences remain follow-up work, not Phase 2 blockers.
- Whole-book proofreading remains required after conversion. No legacy source,
  baseline evidence, published URL, or deployed site was changed.
- Committed HTML acceptance/fixes as `48f1dc9`, the independent source-built
  35-demo pipeline as `921b9e1`, and modern root project/runner/CI as `ce41543`.
- The runner pins CLI/core, Python and npm resolutions and Runestone version;
  fails on schema, command, generated-image, missing/empty-asset and diagnostic
  failures; and isolates upstream mutable caches without patching installed code.
- Strict HTML/print builds passed in `~/tmp/ila/phase2/run-001` and from a fresh
  clone in `~/tmp/ila/phase2/clean-run-001`. The fresh checkout passed 26 Python
  tests, 669 HTML browser assertions, and 27 sandboxed system-Chromium computation
  checks; both worktrees remained clean. Seven known HTML warnings remain.
- Downloaded Chromium's sandbox launch failed locally for the computation suite;
  its failed report is retained separately from the successful system-browser run.
  CI configures user namespaces on its ephemeral runner, not the author's host.
- Preserved pre-existing untracked checkout files under
  `~/tmp/ila/phase2/checkout-leftovers/`, rather than deleting them. New build
  evidence uses disk-backed storage after an earlier run filled `/tmp`.
- Phase 2 remains in progress pending hosted CI verification and stronger
  system-tool/Runestone content locking. See `migration/phase2/README.md` for
  commands, evidence, security limitations and explicit remaining gates.

### 2026-09-05: Assessment and Phase 0 Commencement

- Accepted the architecture and staged plan above, including custom Pyodide.
- Created `uon2` from local `uon` at `f7fbb5e`; retained `aborted-port` at `e96ed01`.
- Confirmed `origin` is the local bare repo `/home/ulrik/repo/ila.git`.
- Restored its `uon` with an explicit expected-old-commit lease:

  ```bash
  git push --force-with-lease=refs/heads/uon:e96ed016c2de348e2620af01eec9506bbbb9503a origin refs/heads/uon:refs/heads/uon
  ```

- Verified remote `uon` now points to `f7fbb5e`. No push to GitHub/upstream.
- Left existing untracked caches, outputs, prebuilt demos, and Python settings
  in the main checkout untouched.
- Restored all five pinned submodules in a separate detached worktree.
- Successfully built the legacy environment, subpackages, HTML, and PDF.
- Added source and generated-output inventory tools/manifests and this log.
- Audited artifacts and recorded defects without changing the legacy sources.
- Archived outputs/logs/npm resolutions outside `/tmp`, verified archive contents,
  and recorded its checksum. Re-ran both inventories using the pinned legacy
  Python environment and verified identical generated manifests.
- At this initial checkpoint, migration changes had not yet been committed or
  `uon2` pushed; see the recovery entry for the subsequently verified state.

### 2026-09-05: Browser Tools and Baseline Verification

- Verified newly installed Chromium, Firefox, and Poppler. Used a launch-only
  library preload for the existing Playwright Python environment.
- Added reusable browser, link-audit, and PDF-capture scripts and JSON reports.
- Captured desktop/mobile viewport baselines and tested vector controls,
  elimination handoff, row operations, linked composition, and keyboard controls.
- Recorded mobile overflow, missing dynamics UI, and missing menu semantics
  without modifying the legacy site.
- Audited static fragments and browser-confirmed seven direct-link failures.
- Captured eight PDF pages and inspected selected mathematical illustrations.
- Completed the repeat build and documented nondeterministic output sources.
- Preserved supplemental evidence in a checksum-recorded local archive.
- Firefox automation/WebGL coverage remains limited as described above.

### 2026-09-06: Interruption Recovery and Phase 0 Closure

- Found the full Phase 0 baseline committed as `e6cd9f0` on 2026-09-05 at
  19:57 BST. Confirmed `origin`'s `uon2` points to that same commit; this is the
  local bare remote, not evidence of a GitHub push or binary-artifact backup.
- Tracked files were clean on resumption. Existing untracked caches, outputs,
  and settings were left untouched. No surviving old build/browser processes
  were present; `/tmp/opencode` had been emptied across an environment restart.
- The accessible previous-boot journal ends with user-session shutdown at
  20:28 BST; the current boot is dated 2026-09-06. Kernel/system logs require
  unavailable elevated access. The cause of the reported harness interruption
  is therefore undetermined; no OOM, browser crash, or build failure is inferred.
- Verified both archive SHA-256 values and gzip integrity, then recovered the
  baseline output without rebuilding or changing historical manifests.
- Regenerated output inventory and link audit matched their committed JSON
  byte-for-byte: 4,662 files, no missing file targets, 1,372 missing static
  fragment reference occurrences. The current source inventory matched in full
  except for the expected Git revision change from `f7fbb5e` to `e6cd9f0`.
- Compared all 44 supplemental archived reports/captures with the checkout
  byte-for-byte. Verified the PDF and all eight PDF capture hashes against the
  PDF report; Poppler reconfirmed 501 pages, Letter size, and no tagging.
- Accepted the Phase 0 documented-limitations exit. Browser interactions and
  builds were not rerun during recovery; their original evidence is preserved.
  Author review, Firefox/WebGL coverage, managed backup, and future regression
  gate hardening remain explicit carry-forward work. Phase 1 was not started.

### 2026-09-06: Persistent Baseline Storage

- Established `/home/ulrik/tmp/ila/phase0` on NVMe-backed Btrfs and copied the
  recovered site/PDF there as `output/`, without deleting the temporary copy.
- Copied both archives into `archives/` and extracted retained build evidence
  into `evidence/baseline/` and supplemental evidence into `evidence/checks/`.
  Archive-relative paths and historical reports were preserved unchanged.
- Verified both copied archive SHA-256 values against this log; `tar --diff`
  passed for both extracted evidence sets. Regenerated the relocated output
  inventory and link audit into `verification/`; both match the committed
  manifests byte-for-byte.
- Updated the reference and recovery locations. Original build commands remain
  historical records; no source worktrees or full build caches were restored.
  The persistent local copies do not satisfy the managed-backup follow-up.

### 2026-09-06: Phase 1 Commencement

- Author accepted responsibility for snapshots and backups and authorized the
  hard-case pilot. Baseline references remain immutable; no backup operation
  was performed or claimed by the assistant.
- Added the isolated upstream project, lockfile, source regression tests, fresh
  run staging/build runner, and Chromium measurement tool. Existing root `.venv`,
  untracked outputs, legacy build files, and book sources were left untouched.
- Verified staged demos and their logo against the historical output manifest.
  Built HTML and conventional PDF, captured twelve browser screenshots and all
  four PDF pages, and retained failed-run diagnostics outside tmpfs.
- Corrected pilot source for current `md` syntax, paragraph-contained lists,
  and table titles. Adapted process launch to keep legacy Python paths and
  Debian library preloads from contaminating Nix child executables, without
  changing upstream installed files.
- Recorded partial success and concrete blockers in the Phase 1 checkpoint.
  Phase 1 is in progress, not finalized; tagged-PDF feasibility and browser
  computation remain unestablished.

### 2026-09-08: Phase 1 Integrated Pilot and PDF Validation

- Confirmed the retained publication base `https://ulrikbuchholtz.dk/ila/` and
  newly installed Debian Node 20.19.2, npm 9.2.0, OpenJDK 21.0.11 and FOP 2.10.
- Provisioned locked MathJax/SRE packages outside installed core via `NODE_PATH`.
  Discovered upstream's automatic CSS npm install in run-007; subsequent builds
  use private resource HOME directories and a retained CSS npm lock. No installed
  upstream source was patched and no audit-fix command was run.
- Extended the source fixtures and tests; introduced project-owned HTML
  visibility/footnote/keyboard fixes, reachable local math scrolling, and a
  sandboxed lazy Pyodide worker component with tested Stop/Reset and fresh state.
- Replaced deficient PDF previews/QR graphics with authored static diagrams and
  preserved online demo links. Corrected table header markup and paragraph widths
  to remove PDF overlap and supply six tagged header cells.
- Installed signed veraPDF 1.30.2 locally without system changes. Verified its
  release signature against the official published key fingerprint, then ran
  the explicit PDF/UA-1 profile. Recorded the pass and separate parser warnings.
- Retained all intermediate/failed runs, raw logs, screenshots, PDFs and hashed
  reports under persistent Phase 1 storage. `checkpoint.md` records a viable
  FOP candidate with remaining diagnostic and human-review gates, not release
  accessibility approval. Snapshots and backups remain author-owned.

## Upstream References

- [PreTeXt PDF via XSL-FO](https://pretextbook.org/doc/guide/html/pdf-xsl-fo.html)
- [PreTeXt CLI 2.52.3](https://github.com/PreTeXtBook/pretext-cli/releases/tag/v2.52.3)
- [PreTeXt accessibility guidance](https://pretextbook.org/doc/guide/html/topic-accessibility.html)
- [LaTeX tagging instructions](https://latex3.github.io/tagging-project/documentation/usage-instructions)
- [PreTeXt program capabilities](https://pretextbook.org/doc/guide/html/topic-program.html#interactive-program-capabilities)
- [SageCell design](https://pretextbook.org/doc/guide/html/topic-sage.html#sage-cell-design)
- [Pyodide packages](https://pyodide.org/en/stable/usage/packages-in-pyodide.html)
- [veraPDF installation and signing key](https://docs.verapdf.org/install/)
