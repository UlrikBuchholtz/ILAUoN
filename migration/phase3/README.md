# Phase 3: Content Conversion

**Phase 3 commenced on 2026-09-11 and has produced measurement and verification
tooling only.** No book content has been converted, no legacy source has been
changed, and the pilot fixture remains the only thing the modern build builds.
The author accepted the compact-notation verification proposal on 2026-09-11 and
it is now implemented and passing; the remaining gates below are still a
proposal, not an accepted contract.

`MIGRATION.md` states the phase gate: "Use XML-aware transformation and tested
notation parsing in reviewable batches. Preserve IDs, order, captions,
dimensions, essential markers, and visibility semantics. Review rendered
mathematics as well as schema validity."

## The Census

`scripts/phase3_census.py` measures what conversion has to handle. It reuses
`phase0_inventory.load_active_source`, so it sees exactly the active XInclude
graph that Phase 0 inventoried, and it reads the pinned core's XSL and schema
out of the installed `pretext.resources/core.zip`, keyed by the pinned core
commit, rather than from a mutable `~/.ptx` cache.

```bash
uv run --locked python scripts/phase3_census.py --output migration/phase3/census.json
uv run --locked python -B -m unittest discover -s migration/phase3/tests -v
```

The run takes under a second, writes deterministic JSON, and executes no LaTeX.
`migration/phase3/census.json` is the committed result for `ba732a8`.

What it is not: it expands no macro and runs no TeX, so macro counts are lexical
occurrences and include the arguments of macros that suppress them. It does not
decide whether anything is supported upstream. `in_core_xsl_match` records only
whether an element name appears in a pinned-core XSL match pattern after entity
expansion; `in_pinned_schema` is weaker still, because the pinned RelaxNG schema
is incomplete and omits genuine PreTeXt elements such as `me` and `men`.

## Measured Scope

| Measure | Value |
| --- | --- |
| Active source files / elements / distinct element names | 45 / 20,723 / 100 |
| Element names with no pinned-core XSL match | 16 |
| Math elements (`m`, `me`, `men`, `mrow`) | 10,214, 221,797 characters |
| Raw LaTeX blocks (`latex-code`, `latex-image-code`) | 268, 235,053 characters |
| Distinct control sequences in that LaTeX | 273 |
| Of those, defined by `src/latex/*.sty` | 48 used, 134 defined |
| Compact-notation call sites | 2,437, all delimited |
| Macros defined inside the book source | 31, of which 20 are used outside their defining element |

The 16 element names with no upstream XSL match are `latex-code`, `mathbox`,
`bluebox`, `specialcase`, `essential`, `concept`, `desc`, `latex-image-code`,
`contributortype`, `brandlogo`, `concept-library`, `holder`, `macros`,
`minilicense`, `shortlicense` and `solution-list`. Some have obvious upstream
counterparts with different names; `bluebox`, `specialcase`, `essential`,
`concept-library` and `mathbox` carry teaching semantics and need an explicit
decision each.

Behavior also rides on attributes upstream does not have: `hide-type` (117
occurrences), `type-name` (36), `visible` (15) and `mode` on `latex-code` (17).
These control numbering, cross-reference phrasing and visibility, which the
Phase 0 assessment already identified as the reason valid XML alone will not
establish correctness.

## Compact Notation

`\vec`, `\mat`, `\amat`, `\nmat`, `\hmat` and `\syseq` are not MathJax-shaped
macros. `spalign.sty` reads TeX tokens to decide the array preamble: entries are
separated by spaces or commas, rows by `;`, and `\spalignmat` counts the widest
row before it emits `\begin{array}`. A converter has to expand every call site
itself.

`scripts/phase3_notation.py` does that, and `scripts/phase3_verify.py` is its
gate. Nothing is assumed about spalign's behavior: the gate asks TeX.

| Macro | Calls | Shapes | Notes |
| --- | --- | --- | --- |
| `\vec` | 1,161 | one row; 7 widths, 2 and 3 entries dominate (415 and 635) | |
| `\mat` | 1,036 | 21 sizes, `2x2` 464 and `3x3` 303 | 63 cells nest another compact macro |
| `\amat` | 116 | 10 sizes, `3x4` most common | augmented, last column past the rule |
| `\syseq` | 105 | 18 sizes, `3x7` most common | 8 ragged, using the local `\+`, `\=`, `\.` |
| `\hmat` | 19 | all `3x6` | split at the floor of half the width |
| `\nmat` | 0 | | defined but unused |

No matrix or vector in the book is ragged; only systems are, which is what `\+`
and `\.` pad. The earlier ragged counts in this file came from an approximate
splitter that treated `,` as ordinary text, and are gone.

### The Two Gates

Run together, over the frozen legacy source:

```bash
uv run --locked python scripts/phase3_verify.py --run ~/tmp/ila/phase3/verify-NNN --typeset
```

**Token gate.** A generated LaTeX document runs `spalign.sty`'s own parser,
`\spalign@process`, over every call site's argument and writes back the token
list it accumulated and `\spalignmaxcols`. The reader must agree exactly on both.
This covers every call site it can delimit and needs no macro to be defined,
because `\the` on a token register does not expand.

**Typeset gate.** The legacy call and the reader's re-rendering are typeset on
consecutive pages under the book's own `macros.sty`, each shipped out as a single
box, and their PDF content streams must be byte-identical. Cases whose entries
use a control sequence the book's packages do not define, or one the book source
redefines, are excluded: outside the source's own state `\r`, `\b`, `\g`, `\o`,
`\p` and `\a` are LaTeX accents, not the author's colour macros.

Result for `ba732a8`, run `~/tmp/ila/phase3/verify-011`:

| Gate | Coverage | Result |
| --- | --- | --- |
| Token | 1,213 distinct cases, 2,431 of 2,437 call sites | 0 mismatches |
| Typeset | 1,165 cases, 2,381 of 2,437 call sites | 0 differing |

The six uncovered sites are the expansion-dependent ones below. Getting there
took three real defects out of the reader, each caught by the gate and none
visible by inspection: a wrong row separator, TeX's rule that the space ending a
control word is absorbed rather than separating entries, and the loss of that
same space as a token terminator.

The typeset gate is itself checked for discrimination, because a gate that never
rejects anything proves nothing. `tests/test_notation.py` mutates the rendering
and requires rejection: changing one column's alignment from `r` to `l`, or
dropping the `\hskip-\arraycolsep` tightening, both produce differing content
streams, and neither is visible to the token gate. Those three tests skip when
`pdflatex` is absent and say so.

`render_portable` is derived from the same parse but is not compared here. It
drops spalign's `\hskip-\arraycolsep` tightening, which MathJax has no
`\arraycolsep` for, and rebuilds `\syseq`'s `\halign` as an array of alternating
right- and left-aligned columns. Those are deliberate spacing changes to the same
cells; the system form still needs `\+`, `\=` and `\.` declared as MathJax
macros, and it needs author review.

### Call Sites That Are Decisions

Every one of the 2,437 call sites is delimited: none is unreadable. Fourteen are
not plain brace groups:

- Eight take a single token, as TeX allows: `\det\mat a=a` in
  `src/determinant-cofactors.xml` and `src/determinant-volume.xml`.
- Three take `\cdots` as the whole matrix, in a `split` in
  `src/determinant-cofactors.xml`, so the printed object is an ellipsis standing
  in for a matrix.
- Three take a control sequence built by `\def`/`\edef` earlier in the same
  `latex-code` block: `\syseq\eqs` in `src/overview.xml` and
  `src/leastsquares.xml`. These have no shape until TeX expands them, and they
  are the only sites neither gate covers.

### System Delimiters Are Document State

`\spalignsysdelims` changes a system's delimiters, and the source calls it 18
times. Of the 105 system call sites, only 18 set their delimiters in their own
element; 82 inherit them from an earlier element and 5 use the document default.
Twenty-three of the inherited sites are set to `.` and `.`, that is to no
delimiters at all, so a converter that read each `\syseq` locally would put
braces around twenty-three systems that have none. `\spalignsystabspace` is
inherited the same way at 9 sites.

This is the same class of problem as the stateful macros below, and it is
exactly what the aborted port got wrong in `src/vector-spans.xml`.

## Stateful Source Macros

Thirty-one control sequences are defined inside the book source. Twenty are used
outside the element that first defines them, and the short names are redefined
repeatedly with different meanings: `\r` 27 times, `\v` 24, `\w` 20, `\theo` 19,
`\b` 17, `\g` 9. A page-global MathJax macro block cannot reproduce this, so
conversion has to localize each definition or inline it at its use sites. The
same applies to `\rowop`, which `macros.sty` defines and the source redefines
seven times.

Colour also carries meaning: `\color` appears 191 times, `\textcolor` 95, plus
the book's own `\leading`. Phase 1 handled the pilot's instance by making the
distinction explicit in prose; the rest needs the same treatment and belongs
with the Phase 4 accessibility work.

## Proposed Gates

For author acceptance before conversion begins:

1. The converter and its tests are committed. It refuses unfamiliar syntax
   instead of guessing, and a refusal fails the batch.
2. **Implemented and passing.** Compact notation is verified against TeX rather
   than by inspection, by the two gates above. Sites neither gate covers are
   listed in the run's `report.json` and reviewed by hand.
3. Each batch preserves IDs, document order, captions, image dimensions,
   `essential` markers and visibility, checked mechanically against
   `migration/baseline-source.json` rather than by reading diffs.
   `scripts/phase3_preserve.py` implements the well-defined part of this today:
   it fails on a lost `xml:id`, a lost MathBox demo contract, a change in
   division order or titles, or an xref that used to resolve and no longer does,
   and it reports changes in content-carrying element counts without gating on
   them, because conversion renames markup on purpose. Captions and visibility
   wait on the `hide-type`/`type-name`/`visible` mapping.
4. Each batch passes `scripts/build.py`'s existing gates unchanged, including
   schema validation, asset auditing and the diagnostic blockers.
5. The author reviews rendered mathematics per batch. Schema validity is not
   review.
6. Mechanical conversion and editorial change stay in separate commits, as
   `migration/phase1/coverage.md` requires of the pilot's labelled rewrites.

Batches are proposed in reading order, one chapter at a time. The notation-only
spike that gate 2 called for is done; what remains before the first batch is the
element and attribute mapping in Open Decisions below.

## Open Decisions

- Mapping for each of `bluebox`, `specialcase`, `essential`, `concept-library`
  and the `hide-type`/`type-name`/`visible` attributes. Phase 1 settled these
  only for six hand-authored sections, and `coverage.md` explicitly forbids
  folding its editorial choices into mechanical conversion.
- Treatment of the three expansion-dependent `\syseq` sites and the three
  `\det\mat\cdots` sites: expand once and inline, or rewrite editorially.
- Whether the 268 `latex-code` blocks convert to `latex-image` or to semantic
  markup, per block. Seventeen carry a `mode` attribute.
- The two duplicate `xml:id`s recorded as Phase 0 baseline defects
  (`linear-trans-pick-columns`, `solnsets-nontrivial`) must be resolved during
  conversion, and that changes at least one published anchor.

## Aborted-Port Regression Cases

The author refetched `aborted-port` on 2026-09-11, so commit
`e96ed016c2de348e2620af01eec9506bbbb9503a` is readable again. Its source
inventory is committed here as `aborted-port-source.json`, produced by the
unchanged Phase 0 tool, so these cases survive the branch disappearing a second
time. Against the Phase 0 baseline it loses 6 `xml:id` values, all 167 MathBox
demo contracts, and every `essential` (7), `bluebox` (100), `specialcase` (62)
and `latex-code` (264) element, and it changes the division sequence.

`scripts/phase3_preserve.py` fails on that tree and passes the baseline against
itself. `tests/test_notation.py` pins the specific failures:

- `src/vectors-matrices.xml:688`. `\vec{1\cdot 2+4\cdot(-1) ...}` is three
  entries. The aborted port produced six rows, by splitting on the space that
  ends `\cdot` instead of absorbing it — the same rule the token gate later
  caught the reader getting wrong.
- `src/vector-spans.xml:37`. `\spalignsysdelims()\syseq{ x - y; 2x - 2y; 6x - y}`
  became `\left\{\begin{aligned}&{}<\end{aligned}|(|)|>{ x - y; ...}`: a broken
  template with the delimiter arguments left as literal residue and the argument
  never parsed.
- `src/determinant-cofactors.xml`. The "Cramer's Rule and Matrix Inverses"
  subsection was deleted, taking `det-cofact-cramers-rule`, `det-cofact-cramer-ss`,
  `det-cofact-inv-cramer` and `det-cofact-inv-cramer-fn` with it.
- Essential, visibility and demo markup was dropped wholesale rather than mapped.

The build and dependency failures recorded in `MIGRATION.md`'s Aborted-Port
Findings are not encoded here; they belong to the demo builder and the
dependency pins, both of which Phase 2 already gates.
