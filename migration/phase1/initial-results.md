# Initial Phase 1 Results

Date: 2026-09-06. Reference run: `~/tmp/ila/phase1/run-005`.
**Phase 1 remains open; there is no accessible-PDF feasibility decision yet.**

## Verified

| Check | Observation |
| --- | --- |
| Source regression tests | Seven pass: IDs/xrefs, demo URLs, full table, source-derived nested products, wrong-sign mutation rejection, all six row operations, and native SymPy output |
| Upstream validation | No development-schema errors or validation-plus messages; three experimental iframe interactives |
| HTML build | Generated, with upstream warnings retained |
| Browser | 96 assertion passes, 0 assertion failures; 10 runtime errors, 0 network errors; **overall exit 1** |
| HTML mathematics | CHTML MathJax rendering in all four sections at both viewport sizes; no sampled `merror`, SVG math output, or unprocessed math |
| Interactions | Essential title visible; keyboard disclosure/collapse; footnote target exists; TikZ number-line image loads; vector default, linked composition, and rowred1 handoff state/history checked |
| Print PDF | Four Letter pages, untagged; all four pages captured and text extracted |
| Tagged PDF | Failed before FOP: missing `@mathjax/src/js/util/asyncLoad/node.js`, then empty MathJax output; no PDF produced |

The browser sample uses system Chromium 150 with SwiftShader, not physical
mobile/touch devices. Automatic PDF previews use Playwright's Chromium 151.
The staging-only missing-logo error from run-004 was fixed by copying and
verifying the baseline's `images/logo.png`; no baseline file was changed.

## Open Gates

1. **PDF tooling and feasibility.** Install the requested Node/npm and Java/FOP
   packages, then provision locked MathJax/SRE dependencies outside installed
   core. Test FOP SVG/speech/TikZ support, tagging, reading order, and overflow.
   A tagged file or validator pass will not establish navigable mathematics or
   usable screen-reader output. Agree on required PDF standard and reader stack
   with accessibility staff before choosing a release route.
2. **Disclosure and custom semantics.** Keyboard use records ten
   `knowl_focus_stack is not defined` exceptions, despite disclosure opening and
   closing. Global `remark="yes"` also hides `insight` blocks, unlike visible
   legacy blueboxes. The synthetic footnote ID occurs twice in generated HTML.
   Standard-element mappings are provisional, not accepted replacements for
   essential/type-name/visibility/numbering behavior.
3. **Layout and alternatives.** All sampled document scroll widths fit, but the
   mobile products screenshot clips wide mathematics and iframe content; demo
   captions overlap. The print table extends beyond the text block, with a
   51.3495pt overfull hbox. Composition's automatic PDF preview has overlapping
   captions. These are blockers, not permitted warnings. Adjacent formulas and
   prose provide static alternatives, but need author review for equivalence.
4. **URLs and asset pinning.** No publication base URL is set for this unpublished
   fixture, so generated PDF QR codes contain relative paths and are unusable as
   publication links. Runestone Services 8.2.10 was fetched through `latest`;
   pin its assets before claiming a fully locked modern build. The CLI warns
   that it cannot find its conventional `requirements.txt`; the actual Python
   lock is `uv.lock`. Build-time base-schema warnings for the three interactives
   are distinguished from the explicit development-schema validation result.
5. **Remaining fixtures.** Add the stateful reusable TikZ helper from matrix
   multiplication, per-element hidden paragraphs/proofs and explicit Warning
   type override, plus aborted-port notation regression cases. The current
   ordinary-math color-state example is manually made self-contained; no general
   converter or compact-notation parser has been implemented.
6. **Browser computation.** The inactive float example reproduces its original
   wrong answer in native Python 3.12/SymPy 1.14.0. It is still a static listing,
   not a Pyodide cell. Worker execution, lazy loading, package pins, Stop/Reset,
   accessible results, isolation/network policy, and browser output equivalence
   remain to implement and test.
7. **Review.** Full Firefox/WebGL, assistive-technology checks, complete visual
   review, and author mathematical approval remain outstanding. PDF pages 1 and
   4 and selected mobile screenshots were visually examined, not proofread in
   full. No whole-book conversion or Phase 2 work has begun.

## Evidence Integrity

Paths below are relative to `~/tmp/ila/phase1/run-005`, except the last two which
are relative to this directory in the repository. JSON reports retain commands,
input hashes, diagnostics, and screenshot/PDF hashes. Raw logs and binary
captures stay in persistent local storage managed by the author.

| File | SHA-256 |
| --- | --- |
| `report.json` | `d407141a36c283c299e9b6f8ce48734ddf817e0960971c257cc0fd7338755113` |
| `browser/report.json` | `c3260a2a12f8d986a6c5a07851af0c9ecc5b2b7c65bfa80334ca0e3281b9c516` |
| `pdf-report.json` | `d210b0144578a7b75240c916cf766771a5e258b0750e7008b57a56ab85291e0c` |
| `uv.lock` | `a130c862d85f65eeb84c8370708d9078c92a62f57676b7e86c16a707098987e6` |
| `source/main.ptx` | `1f502a47de9c65ecb067f1cb787be1271b51a58e36d99eab41a2e3542d0872bf` |

Early probes exposed two environment failures: legacy `PYTHONPATH` contaminated
the fresh Python environment, and a propagated system `LD_PRELOAD` broke Nix
child executables. In run-002 the explicit upstream validator even reported
success while its executable could not launch; that result is invalid. The
successful run-005 validator ran after those launch issues were corrected and
reported the expected three experimental constructs. Installed upstream files
were not patched to bypass these failures.

After code review, run-006 reconfirmed development-schema validation and HTML
generation with an additional direct Jing invocation (exit 0), avoiding reliance
on the CLI's validation exit status alone. The runner now cleans up process
groups on interruption as well as timeout. The browser harness rejects evidence
destinations under the historical baseline before writing anything; that
rejection was exercised. A mutation test verifies that negating the final
displayed product cannot pass the source-derived algebra check. Run-005 remains
the recorded browser/PDF checkpoint above; those files were not overwritten.
