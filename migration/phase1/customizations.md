# Pilot HTML Customizations

The HTML target uses `xsl="html.xsl"`. Its import of
`./core/pretext-html.xsl` is resolved by the CLI against the pinned core in each
run's private resource cache. No upstream source file is patched.

## XSL Boundary

- Standard `is-hidden` overrides leave insights/warnings visible, hide only
  `pilot-multilinearity`, and expose `pilot-product-invertible-proof`.
  `pilot-multilinearity-proof` and ordinary remarks retain publication defaults.
- The footnote override preserves upstream markup and forwards `b-original` and
  `heading-level`, adding `block-type='hidden'` to the body. The original outer
  details owns the ID; the body and knowl duplicates do not repeat it.
- CSS extras already accept multiple URLs upstream. The local `extra-js-footer`
  override gives JS extras equivalent comma/space tokenization so compatibility
  and computation scripts can load in order.

The upstream generic block customization modes are documented in
`pretext-html.xsl:2618-2689`. `paragraphs` participates in them, so no semantic
type substitution or hand-built details wrapper was needed. The publication
also requests responsive iframe sizing.

## Browser Boundary

`external/pilot/compat.js` initializes the absent legacy focus globals to contain
the 2.52.3 Enter/Escape reference error. This does not reconstruct the upstream
focus stack. A scoped Escape handler additionally closes focused native details
and restores its summary, or toggles a dynamic xref knowl through its existing
trigger and restores that trigger. It honors already-handled events; in
particular, MathJax-focused Escape can remain inside MathJax rather than closing
the surrounding knowl. This is not a blanket keyboard-event suppression.

Wide display math keeps its intrinsic size. Only overflowing outer boxes gain
a labeled, focusable group; arrows and Home/End scroll that focused box, not an
unfocused MathJax child. Attributes are removed when overflow disappears.
Resize, disclosure, fonts and new knowl content trigger remeasurement. CSS
preserves reachable start edges instead of shrinking mathematical text.

Iframe CSS removes the parent theme's minimum width, but does not rewrite or
hide the legacy demos' own overflow. The independently built applications still
need their own responsive/accessibility work. The Pyodide iframe has a separate
opaque-origin sandbox and policy; see `computation.md`.

## Run-011 Evidence

`browser.py` exercises all six sections at 1440x1000 and 390x844, with individual
visibility contracts, nested proof disclosure, direct fragments, footnotes,
xrefs, duplicate-ID scans, image loading, CHTML math, keyboard scroll edges,
iframe URL/size contracts, and demo runtime state/handoff history.

Results: **311 passes, 0 failures, 7 warnings**, zero JavaScript errors and zero
network errors; 18 screenshots. The seven warnings comprise four legacy demo
interior-overflow observations and three xref Escape observations with focus
inside MathJax. Native footnote Escape now closes and retains usable focus;
ordinary xref-trigger handling improves, but MathJax's own keyboard behavior is
not overridden merely to force a green test.

The hidden multilinearity ancestor opens on direct fragment navigation without
opening its nested proof. Footnote IDs are unique before and after knowl loading.
All sampled wide math responds to arrows and exposes both content edges. All
outer iframe bounds fit. These are Chromium measurements, not full visual,
touch-device, screen-reader, or cross-browser approval.
