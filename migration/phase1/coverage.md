# Fixture Coverage

This is a hand-authored, six-section pilot, not a converter or an accepted
whole-book migration. Legacy sources remain authoritative and unchanged.
New IDs use `pilot-`; selected existing IDs are retained as regression cases.

| Legacy source | Pilot coverage |
| --- | --- |
| `src/matrix-mult.xml:350-381` | `matrix-mult-eg-mult1`: nested products expanded manually to standard matrices, retaining vector-valued columns. Stateful dimension colors become self-contained `textcolor` expressions with a color-independent explanation. |
| `src/matrix-mult.xml:704-774` | Reflection across `xy`, projection onto `yz`, all three basis vectors, and matrices `B`, `A`, `AB`. Three independently generated images reuse a scoped helper in `latex-image-preamble`. These are explicitly editorial redrawings, not pixel-identical graphics or a fourth interactive. |
| `src/row-reduction.xml:217-309` | `systems-eqns-example1b`: system, all six row operations, augmented matrices, back-substitution and solution-set invariant. External excerpt xrefs become self-contained text. |
| `src/dimension.xml:33-64` | `dimension-defn-basis`: essential distinction stated in the title, ordered-basis remark, visible insight for the former bluebox. The infinite-bases assertion explicitly excludes the zero subspace. |
| `src/vectors.xml:55-68` | Visible number-line example, standard TikZ image and short description. No legacy ID existed for this special case. |
| `src/linindep.xml:317-322` | `linindep-not-any`: explicit `warning`, retaining the any-versus-at-least-one distinction and the three-vector counterexample. |
| `src/fundamental-subspaces.xml:367-417` | All six columns and four data rows preserved. Added acronym context and a clearly synthetic footnote. Header cells now use `row header="yes"`; paragraph cells and widths `16/8/10/10/18/16%` make widths effective in both PDF exporters and leave room for LaTeX cell spacing. |
| `src/determinant-definitions-properties.xml:768-781` | Complete determinant argument for invertibility of a product iff every square factor is invertible; proof explicitly visible. External references become statements of the properties used. |
| `src/determinant-definitions-properties.xml:1036-1124` | Hidden `pilot-multilinearity` container retaining `det-defn-linear-prop`, with a separately hidden proof. Explicitly shortened editorial cofactor proof replaces the legacy row-operation case analysis, proving additivity and scaling for every row, including `n=1`. This changes the proof dependency/order and requires author approval. |
| `src/lu-decomposition.xml:1318-1338` | Inactive-source float example inside `mpp-eg1`. Static Python listing and result remain; HTML progressively enhances that same rendered code with sandboxed worker execution. Browser and native versions differ, but the recorded result matches byte-for-byte. |

## Demos And Static Alternatives

Exactly three legacy MathBox embeds retain their actual query contracts:
`vector.html` and `rowred1.html` without queries, and `compose3d.html` with the
original rectangular matrices, range toggles, range 5, and closed GUI.
The separately sandboxed computation frame is not a fourth MathBox demo.

Each interactive now has an authored `static/image` alternative with concise
alt text, standard TikZ, and adjacent semantic formulas/prose. Composition traces
`(-1,2) -> (-1,2,-1) -> (1,1)`; row reduction shows the initial system and RREF
with solution `(1,-2,3)`; the vector drawing shows displacement `(5,3,4)`.
These replace unusable automatic previews and undescribed QR graphics in PDF.
Explicit links preserve the hosted `/ila/demos/` paths and parameters. The
interactive iframe paths remain relative to managed `external/` assets in the
pilot HTML. Static alternatives are engineering drafts requiring author review.

The publication base is `https://ulrikbuchholtz.dk/ila/`, not a new deployment
prefix. Pilot pages have not been published, and their generated names are not
promised redirects or replacements for existing book URLs.

## Semantics And Verification

`xsl/html.xsl` makes insights/warnings visible, hides only the selected paragraphs
container, and exposes only the selected proof exception. Remarks keep their
publication-wide hidden policy. No unsupported legacy visibility attributes are
copied into upstream source. This is a small explicit pilot contract, not a
general preservation algorithm for numbering, labels, visibility, and styling.

Run-011 passes development-schema validation and validation-plus, with the three
iframe constructs identified as experimental. All 14 source tests pass, covering
source-derived nested products and row operations, wrong-sign mutation rejection,
shared TikZ semantics, multilinearity identities, warning content, table contents
and header markup, static alternatives, URL contracts, and native SymPy output.
All seven authored diagrams build. Browser checks exercise all six sections.
Both PDFs build; see `checkpoint.md` for detailed evidence and remaining gates.

No general compact-notation parser or automatic converter exists yet. Editorial
rewrites here are explicitly labeled and must not be folded silently into later
mechanical conversion. Copyright/license provenance remains in the source
comment; a public standalone distribution also needs the applicable license
material and review.
