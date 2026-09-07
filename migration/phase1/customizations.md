# Pilot HTML Customizations

The custom stylesheet imports `./core/pretext-html.xsl`, resolved by the CLI
against the pinned `/home/ulrik/.ptx/2.52.3/core/xsl`. No installed core edits.

Parent integration:

- Set the HTML target attribute `xsl="html.xsl"` in `project.ptx` (relative to the project's default `xsl/` directory).
- Copy the pilot `xsl/` directory into each staged run alongside `source/` and `publication/`.
- Keep publication `<knowl ... remark="yes"/>` (proofs remain hidden by default).
- Add `<interactives><iframe resize-behavior="responsive"/></interactives>` inside publication `<html>`.
- Stage `source/external/pilot/` as `external/pilot/` in HTML output, including the other agent's `python-adapter.js`.
- Use `html.css.extra = external/pilot/compat.css` and `html.js.extra = external/pilot/compat.js external/pilot/python-adapter.js`. These are also stylesheet defaults.

The pinned core documents the generic block customization modes in
`pretext-html.xsl:2618-2689`. `paragraphs` participates in that dispatch and has
an `is-hidden` mode, so the ID-specific override needs no wrapper or renamed
semantic type. Only `pilot-multilinearity` is made hidden and only
`pilot-product-invertible-proof` is made visible. `pilot-multilinearity-proof`
retains the publication default. Insights and warnings remain visible while
remarks retain the publication setting.

The footnote override preserves upstream markup and forwards `b-original` and
`heading-level`, adding `block-type='hidden'` to the body. Only the original
outer details owns the footnote ID; duplicates receive no IDs through this path.

CSS extras accept comma/space separators upstream (`css-common`); JS extras
accept only a single URL upstream (`extra-js-footer`). The local footer override
tokenizes the JS string with the same separators, emitting scripts in order.

The missing focus globals are initialized only when undefined. This prevents
the legacy Enter/Escape reference error without replacing handlers or suppressing
events. Empty stacks are containment, not a complete knowl focus implementation.

Math scroll regions keep intrinsic MathJax sizing and a reachable start edge.
Only measured overflow boxes gain a tab stop and accessible label; those added
attributes are removed when the box no longer overflows. Resize, disclosure,
font loading, and dynamically inserted knowls trigger measurement. Iframe CSS
removes the theme minimum width without hiding overflow inside legacy demos.

Verification without a build: the stylesheet compiled against the pinned core;
`node --check` passed. Browser-only injection into existing run-006
`pilot-products.html` checked three visible displays at 390px and 1440px.
Respectively two and one overflowed; all had reachable start/end scroll edges,
and only overflowing displays had labeled tab stops. Enter/Escape produced no
runtime errors during the check. This is not a rebuilt-output or full iframe,
cross-reference, or accessibility acceptance test.

## Run-007 Browser Evidence

`browser.py` now visits five sections at desktop and mobile widths, including
`pilot-determinants`. It checks individual semantic IDs instead of total
remark-like disclosure counts. It also checks nested disclosure keyboards,
direct fragment access, duplicate IDs before/after knowls, footnote and xref
Enter/Escape behavior, math arrow scrolling and both content edges, and iframe
outer bounds separately from legacy interior overflow.

Latest evidence: `/home/ulrik/tmp/ila/phase1/run-007/browser/report-recheck.json`,
with 16 screenshots in the sibling `screenshots-recheck/` directory. There are
258 passing assertions, zero failures, ten warnings, zero network errors, and
zero runtime errors. The original `browser/report.json` and `screenshots/` are
preserved: that first measurement had two stale harness failures because it
expected no iframe on the computation page. The corrected contract expects the
local `external/pilot/python.html` iframe, without testing its computation.

- Both basis remarks start closed and toggle with Enter/Space; insights and the warning are visible.
- Multilinearity starts closed, opens with Enter, and leaves its nested proof closed until separately opened. Both can close with Space. The invertible-product proof is visible initially.
- Direct `pilot-determinants.html#det-defn-linear-prop` navigation opens the ancestor disclosure and brings the proposition into view, without opening the nested proof, in tested Chromium.
- The XSL footnote correction works in actual run-007 HTML: exactly one `pilot-synthetic-footnote` ID, visible content on Enter, and no duplicate IDs detected on any tested section or after inserting xref knowls.
- Overflowing display math, including newly revealed proof and xref content, has labeled tab stops, responds to Left/Right arrows, and has reachable left/right content bounds. Short displays have no added tab stop. No global shrinking was introduced.
- All tested outer iframe bounds fit their containers and page viewports. This does not establish usability inside the legacy demos.

The ten warnings comprise four legacy interior overflow observations and six
Escape behavior observations. On mobile the row-reduction demo remains 800px
wide inside a 334px iframe. The composition demo has its own hidden overflow;
the mobile screenshot also shows overlapping/clipped internal labels. These
legacy interiors are not repaired or silently hidden by the compatibility CSS.
The screenshots are not full visual acceptance, and locally scrollable wide
math is necessarily only partly visible in an unscrolled screenshot.

Escape leaves the footnote open with focus on its summary. Xref knowls remain
open, and focus placed inside a knowl is not restored to its trigger. Focus
remains usable and Enter on the trigger closes the knowl, but the missing-global
shim is still only error containment, not complete focus restoration.

This verification pass changed only the browser harness and this document.
No compatibility/XSL changes or rebuild are required for these harness updates.
