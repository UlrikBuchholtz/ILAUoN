# Phase 1 Checkpoint: HTML, Computation, And PDF

Date: 2026-09-08. Evidence root: `~/tmp/ila/phase1/run-011/`.
**The technical pilot is implemented. Phase 1 remains open for the remaining
diagnostic, author, and assistive-technology gates. No Phase 2 conversion or
deployment is authorized by these results.**

## Results

| Check | Result |
| --- | --- |
| Source/algebra/SymPy tests | 14 pass |
| Development schema and validation-plus | Pass; three experimental iframe constructs |
| Independent Jing | Exit 0 |
| HTML | Six sections, CHTML MathJax, three original demo contracts, progressive Pyodide enhancement |
| Chromium desktop/mobile viewports | 311 passes, 0 failures, 7 warnings; 0 JavaScript errors, 0 network errors; 18 screenshots |
| Browser computation | 27 passes, 0 failures, no overlay; actual worker execution and opaque-origin sandbox |
| Static HTML audit | 598 references across 48 HTML files; no missing files/fragments or duplicate IDs; 11 contextual references unverifiable statically |
| Conventional PDF | Seven Letter pages, untagged; no overfull box diagnostics |
| FOP PDF | Seven Letter pages, tagged; no missing/placeholder figure alt text or FO overflow diagnostics |
| Table structure | One table, five rows, six `TH` and 24 `TD` cells in tagged PDF |
| veraPDF 1.30.2, explicit `ua1` profile | 106 passed rules, 0 failed rules; 34,388 passed checks, 0 failed checks |

The source adds three shared-helper reflection diagrams, hidden paragraphs with
a separately hidden proof, a visible-proof exception, and an explicit Warning.
All seven authored TikZ diagrams generate. Editorial redrawings and the
shortened multilinearity proof are labeled, not passed off as mechanical
conversions. Selected diagrams/table pages were visually inspected; all seven
pages of each PDF were captured and text extracted for author review.

Project-owned HTML XSL/JS fixes preserve visible insights, implement the selected
visibility exceptions, remove duplicate footnote IDs, contain the upstream
missing-global keyboard error, and make wide math keyboard-scrollable without
shrinking it. Native footnote Escape closes and restores its summary. Xref
behavior improves where the trigger or ordinary descendant owns focus; three
remaining Escape observations involve MathJax focus. Four other warnings concern
legacy demo interiors, not parent iframe bounds. No original demo file changed.

The PDF static alternatives now use authored diagrams plus semantic prose/math,
not overlapping automatic screenshots and undescribed QR codes. Explicit online
links retain the real `https://ulrikbuchholtz.dk/ila/demos/` paths and parameters.
The publication base is the unchanged `/ila/` URL. Pilot pages are not published;
generated pilot URLs are not promised public redirects.

## PDF Feasibility

**Provisional engineering conclusion:** the pinned upstream FOP route can
generate a tagged, machine-valid PDF/UA-1 document for these hard cases using
ordinary source markup, authored image alternatives, and no installed-core
patches. It is a viable candidate for the accessible-electronic-PDF pilot,
not a whole-book conformance commitment.

This route represents mathematical expressions as figures with serialized
spoken alternatives. The 128 Figure tags include mathematics and authored
diagrams; no navigable mathematical tree is established in the PDF. Long nested
matrix speech must be evaluated by actual readers. CHTML in the HTML output is
not evidence of corresponding mathematical navigation in PDF.

Remaining gates:

1. FOP still reports `coverage set class table not yet supported` and font
   hyphenation substitutions. The runner deliberately treats the unsupported
   diagnostic as blocking; its default full run exits nonzero despite successful
   generation. Do not remove that gate merely because the PDF/UA profile passes.
2. veraPDF's parser emits three `Incorrect bfrange in toUnicode CMap` warnings
   even though its validation rules all pass. The combined report retains
   stderr. Verify affected glyph mapping/text extraction and reader behavior
   before accepting the PDF. No conformance repair or warning suppression was
   applied locally.
3. Author review must approve the mathematics, editorial proof/redrawings,
   static activity alternatives, and provisional custom-element mappings.
4. Accessibility staff must agree on the required PDF standard and whether
   spoken figure alternatives are sufficient, then test the chosen PDF readers
   and screen readers. If navigable PDF mathematics is required, this FOP
   result does not meet that requirement by itself; the separate modern tagged
   LuaLaTeX route remains untested.
5. Firefox/WebGL, real touch-device behavior, and assistive-technology use remain
   unverified. Legacy iframe interior overflow/overlap is still present. The
   independent demos require their own accessibility work rather than CSS that
   silently hides the problem in the host page.

The validator pass is therefore a machine-check result, not an assertion of
usable accessibility or permission to migrate/publish the entire book.

## Computation

The optional cell derives its initial program from the rendered static listing.
It uses a sandboxed iframe with only `allow-scripts`, a pinned CDN and CSP, and
a fresh dedicated worker/interpreter for every run. Run/Stop/Reset, bounded
output, real execution timeout, load failure/timeout, stale-result suppression,
fresh state, keyboard controls, and blocked parent-origin access were tested.

Versions: Pyodide 0.29.3, Python 3.13.2, SymPy 1.13.3 and mpmath 1.3.0. The
native comparison uses Python 3.12.14 and SymPy 1.14.0. The historical wrong-answer
example produces identical output, but this does not establish package-version
parity or correctness of other activities. The iframe is the origin boundary;
the worker is not a security sandbox. Allowlisted CDN communication, memory
exhaustion and other hostile-code risks remain explicit in `computation.md`.

## Tooling And Reproducibility

Debian tools observed: Node 20.19.2, npm 9.2.0, OpenJDK 21.0.11, FOP 2.10.
PreTeXt CLI/core and Python dependencies retain their earlier pins. MathJax 4.1.3,
New Computer Modern fonts 4.1.3, SRE 5.0.0-rc.4 and yargs 17.7.2 are installed
with a committed npm lock in an isolated directory and supplied via `NODE_PATH`.

Run-007 exposed upstream's automatic CSS-builder npm installation in shared
`~/.ptx/2.52.3/core/script/cssbuilder`. Subsequent runs use a private `HOME` and
an explicit locked `npm ci --ignore-scripts` in disposable extracted resources.
No upstream source is patched. The initial CSS audit reported two high-severity
issues; no audit-fix or exploitability assessment was performed. Runestone
Services still resolves through `latest` (8.2.10 observed); pinning that and
modern clean-checkout CI remain Phase 2 work, not completed reproducibility.

veraPDF was installed without system changes at
`~/tmp/ila/phase1/verapdf-1.30.2/`. Official download:
`https://software.verapdf.org/releases/1.30/verapdf-greenfield-1.30.2-installer.zip`.
SHA-256: `6cc6341cb1af644044054b81f00a6590a7918abb18f762243de115258bcad838`.
Its detached signature verified against the fingerprint published in the
official installation documentation:
`13DD102B4DD69354D12DE5A83184863278B17FE7`. The public key was imported into an
isolated local keyring, not the author's keyring. This records cryptographic
verification against the published key, not independent identity certification.

## Evidence Integrity

Report paths below are relative to run-011. Reports retain input hashes,
commands, versions, warnings, and screenshot/PDF hashes; source and lock hashes
below are repository-relative to this project. Prior runs remain unchanged.

| File | SHA-256 |
| --- | --- |
| `report.json` | `0f35a6551d5696adb583d22e378031c1a9860de84e6420061ad121d65da001bb` |
| `browser/report.json` | `b82711c68f863ba08eb4746aaa48abcb9855118e647bfba3f52d487efad1f9bc` |
| `computation-report.json` | `b11a2383720972378cf1205f36ed4d56f3ccdbe428320dfed4f8d291a39bab26` |
| `pdf-validation.json` | `7bffc6079dc6e95ca05b79ecd8f1e3d2afa5ac5f8f105b5675e41b7619e2dbb4` |
| `pdf-accessible.json` | `7f110dab7ed7b07d8122b0aa7109cad33fcbc8ffd7bb7d5d41454f2a0ae07816` |
| `pdf-print.json` | `9d08e75b16e1ca221a202669a0765b306b5f67a948aa2f8b3fd0de41677cc6a2` |
| `math/package-lock.json` | `43400128facb896e5b89df975e1a5be9d108e8fefb3ead8d6dec717fe30d1130` |
| `theme/package-lock.json` | `fcd656b51d8fb2901c1695792a0eb3fa0bf7e2b86ab0489f65581d3fdb2a77a0` |
| `source/main.ptx` | `43d49ec522b22543bb3f3dd47c7820fbb02d39bf06ce8d0cf3fe9480c72d85d9` |

Snapshots and backups are author-owned. These persistent local files and recorded
hashes do not assert that a backup has completed.
