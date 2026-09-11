#!/usr/bin/env python3
"""Check the compact-notation reader against TeX itself, at every call site.

Two independent gates, both run against the frozen legacy source:

1. Token gate. LaTeX runs `spalign.sty`'s own parser over every call site's
   argument and writes back the accumulated token list and widest row.
   `phase3_notation.parse` must agree exactly on both.
2. Typeset gate. For every call site whose argument uses no undefined control
   sequence, the legacy call and the reader's re-rendering are typeset on
   consecutive pages and their PDF content streams must be identical.

The typeset gate covers a subset by construction, because entries often use
macros the surrounding source defines. The token gate covers every call site
the reader can delimit. Neither gate expands macros on the Python side.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOTATION = _load('phase3_notation')
INVENTORY = _load('phase0_inventory')
CENSUS = _load('phase3_census')

PROBE_FILE = 'probe.out'
# TeX's \ifcsname cannot be generated for a single-character control sequence here,
# and those in this source are primitives or plain TeX; they are not probed.
PROBEABLE = re.compile(r'\\([A-Za-z@]+)')


SYSDELIMS = re.compile(r'\\spalignsysdelims(?![A-Za-z@])')
SYSTABSPACE = re.compile(r'\\spalignsystabspace\s*=\s*([^\s\\;,}]+)')


def call_sites(root):
    """Every compact-notation call site in the active source, with its arguments.

    A system's delimiters and tab space are document state that the source changes
    with \\spalignsysdelims and \\spalignsystabspace. State is carried in document
    order, because that is what a single LaTeX run does, and each site records
    whether its state was set in its own element or inherited from an earlier one.
    """
    book, _, origins, _ = INVENTORY.load_active_source(root)
    sites = []
    order = 0
    delimiters, delimiter_order = list(NOTATION.SYSTEM_DELIMITERS), None
    tabspace, tabspace_order = None, None
    for element in book.iter():
        if element.tag not in CENSUS.MATH_ELEMENTS + CENSUS.RAW_LATEX_ELEMENTS:
            continue
        latex = NOTATION.strip_comments(''.join(element.itertext()))
        order += 1
        events = []
        for match in SYSDELIMS.finditer(latex):
            events.append((match.start(), 'sysdelims', match))
        for match in SYSTABSPACE.finditer(latex):
            events.append((match.start(), 'systabspace', match))
        for name, definition in NOTATION.COMPACT_MACROS.items():
            for match in re.finditer(r'\\' + name + r'(?![A-Za-z@])', latex):
                events.append((match.start(), name, match))
        for _, kind, match in sorted(events, key=lambda event: event[0]):
            if kind == 'sysdelims':
                _, arguments, _ = NOTATION.read_arguments(latex, match.end(), 2)
                if arguments is not None:
                    delimiters = [argument['text'] for argument in arguments]
                    delimiter_order = order
                continue
            if kind == 'systabspace':
                tabspace, tabspace_order = match.group(1), order
                continue
            definition = NOTATION.COMPACT_MACROS[kind]
            optional, arguments, _ = NOTATION.read_arguments(
                latex, match.end(), definition['arity'])
            site = {**origins[element], 'order': order, 'macro': kind,
                    'optional': optional,
                    'latex': ' '.join(latex.split())[:160]}
            if definition['kind'] == 'system':
                site['delimiters'] = list(delimiters)
                site['delimiter_source'] = (
                    'default' if delimiter_order is None else
                    'element' if delimiter_order == order else 'earlier-element')
                site['tabspace'] = tabspace
                site['tabspace_source'] = (
                    'default' if tabspace_order is None else
                    'element' if tabspace_order == order else 'earlier-element')
            if arguments is None:
                sites.append({**site, 'status': 'undelimited'})
            elif any(argument['kind'] == 'macro' for argument in arguments):
                sites.append({**site, 'status': 'expansion-dependent',
                              'arguments': [argument['text'] for argument in arguments]})
            else:
                sites.append({**site, 'status': 'read',
                              'arguments': [argument['text'] for argument in arguments]})
    return sites


def distinct_cases(sites):
    """Group read call sites by the exact call they make, preserving first appearance."""
    cases, index = [], {}
    for site in sites:
        if site['status'] != 'read':
            continue
        key = (site['macro'], site['optional'], tuple(site['arguments']),
               tuple(site.get('delimiters') or ()), site.get('tabspace'))
        if key not in index:
            index[key] = len(cases)
            cases.append({'macro': site['macro'], 'optional': site['optional'],
                          'arguments': list(site['arguments']),
                          'delimiters': site.get('delimiters'),
                          'tabspace': site.get('tabspace'), 'sites': []})
        cases[index[key]]['sites'].append(
            {'file': site['file'], 'source_element': site['source_element']})
    return cases


def write_probe(path, cases):
    """A LaTeX document that runs spalign's parser and reports what it built."""
    # macros.sty is the book's own preamble and loads spalign; using it here means
    # the undefined-name probe is evaluated against the typeset gate's preamble.
    lines = [r'\documentclass{article}', r'\usepackage{macros}',
             r'\makeatletter', r'\newwrite\probe',
             f'\\immediate\\openout\\probe={PROBE_FILE}',
             # \the on a token register prints the tokens spalign accumulated.
             r'\def\probecase#1#2#3{%',
             r'  \begingroup#2\spalign@process#3\spalign@end',
             r'  \immediate\write\probe{CASE #1}%',
             r'  \immediate\write\probe{BODY \the\spaligntoks}%',
             r'  \immediate\write\probe{COLS \the\spalignmaxcols}%',
             r'  \endgroup}',
             r'\def\probemacro#1#2{%',
             r'  \expandafter\ifx\csname #2\endcsname\relax',
             r'    \immediate\write\probe{UNDEFINED #1 #2}\fi}',
             r'\makeatother', r'\begin{document}']
    for number, case in enumerate(cases):
        vector = NOTATION.COMPACT_MACROS[case['macro']]['kind'] == 'vector'
        setup = r'\def\spalignaligntab{\\}' if vector else ''
        lines.append(f'\\probecase{{{number}}}{{{setup}}}{{{case["arguments"][-1]}}}')
        for name in sorted(set(PROBEABLE.findall(case['arguments'][-1]))):
            lines.append(f'\\probemacro{{{number}}}{{{name}}}')
    lines += [r'\immediate\closeout\probe', r'\end{document}', '']
    path.write_text('\n'.join(lines), encoding='utf-8')


def read_probe(path):
    """Parse the probe's report back into per-case bodies, widths and undefined names."""
    results, undefined = {}, {}
    current = None
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('CASE '):
            current = int(line[5:])
            results[current] = {}
        elif line.startswith('BODY ') and current is not None:
            results[current]['body'] = line[5:]
        elif line.startswith('COLS ') and current is not None:
            results[current]['maxcols'] = int(line[5:])
        elif line.startswith('UNDEFINED '):
            _, number, name = line.split(' ', 2)
            undefined.setdefault(int(number), []).append(name)
    return results, undefined


def write_typeset(path, cases, numbers):
    """Legacy call and re-rendered call on consecutive pages, for stream comparison.

    Each page is shipped out as a single box. Going through the page builder
    instead loops forever on a display taller than any page, and a shipped box
    also keeps the two pages positioned identically.
    """
    lines = [r'\documentclass{article}', r'\usepackage{macros}',
             r'\pdfpagewidth=200cm', r'\pdfpageheight=200cm',
             r'\newcommand{\shipmath}[1]{\shipout\vbox{\hbox{$\displaystyle #1$}}}',
             r'\begin{document}']
    for number in numbers:
        case = cases[number]
        optional = f'[{case["optional"]}]' if case['optional'] else ''
        arguments = ''.join('{' + argument + '}' for argument in case['arguments'])
        legacy = f'\\{case["macro"]}{optional}{arguments}'
        rendered = NOTATION.render_tex_equivalent(
            case['macro'], case['arguments'], case['optional'], case.get('delimiters'))
        state = ''
        if case.get('delimiters'):
            state += r'\spalignsysdelims' + ''.join(case['delimiters'])
        if case.get('tabspace'):
            state += r'\spalignsystabspace=' + case['tabspace'] + r'\relax'
        lines.append(r'\begingroup' + state)
        for expression in (legacy, rendered):
            lines.append(r'\shipmath{' + expression + '}')
        lines.append(r'\endgroup')
    lines += [r'\end{document}', '']
    path.write_text('\n'.join(lines), encoding='utf-8')


def run_latex(source, directory, log):
    """Run pdflatex over the book's own LaTeX search path; never stop for input."""
    environment = {'TEXINPUTS': f'{ROOT / "src/latex"}:', 'HOME': str(directory),
                   'PATH': '/usr/bin:/bin', 'TEXMFVAR': str(directory / 'texmf')}
    completed = subprocess.run(
        ['pdflatex', '-interaction=nonstopmode', '-file-line-error', source.name],
        cwd=directory, env=environment, capture_output=True, text=True, timeout=1800)
    log.write_text(completed.stdout + completed.stderr, encoding='utf-8')
    return completed.returncode


def compare_streams(pdf, numbers):
    """Compare the two pages of each typeset case byte for byte."""
    import pymupdf
    document = pymupdf.open(pdf)
    if document.page_count != 2 * len(numbers):
        raise ValueError(f'Expected {2 * len(numbers)} pages, found {document.page_count}')
    differing = []
    for index, number in enumerate(numbers):
        legacy = document[2 * index].read_contents()
        rendered = document[2 * index + 1].read_contents()
        if legacy != rendered:
            differing.append(number)
    document.close()
    return differing


def verify(root, run, typeset):
    root, run = Path(root).resolve(), Path(run).resolve()
    if run.exists():
        raise ValueError(f'Run directory already exists: {run}')
    if root in run.parents or run == root:
        raise ValueError(f'Run directory must lie outside the checkout: {run}')
    if shutil.which('pdflatex') is None:
        raise ValueError('pdflatex is required and was not found on PATH')
    run.mkdir(parents=True)

    sites = call_sites(root)
    cases = distinct_cases(sites)
    write_probe(run / 'probe.tex', cases)
    if run_latex(run / 'probe.tex', run, run / 'probe.log.txt') != 0:
        raise ValueError(f'The token probe failed; see {run / "probe.log.txt"}')
    observed, undefined = read_probe(run / PROBE_FILE)
    if len(observed) != len(cases):
        raise ValueError(f'Probe reported {len(observed)} of {len(cases)} cases')

    mismatches = []
    for number, case in enumerate(cases):
        parsed = NOTATION.parse(case['arguments'][-1])
        vector = NOTATION.COMPACT_MACROS[case['macro']]['kind'] == 'vector'
        expected = {'body': NOTATION.render_body(parsed, vector=vector),
                    'maxcols': parsed['maxcols']}
        actual = {'body': NOTATION.token_dump(observed[number]['body']),
                  'maxcols': observed[number]['maxcols']}
        if expected != actual:
            mismatches.append({'case': number, 'macro': case['macro'],
                               'argument': case['arguments'][-1],
                               'expected': expected, 'observed': actual,
                               'sites': case['sites']})

    # Names the book source defines itself mean something else in a bare LaTeX run:
    # `\r`, `\b`, `\v` and friends are LaTeX accents, so those cases are excluded
    # from the typeset gate rather than compared against the wrong macro.
    shadowed = set(CENSUS.census(root, examples=0)['macros_defined_in_source'])
    for number, case in enumerate(cases):
        names = set(PROBEABLE.findall(case['arguments'][-1])) & shadowed
        if names:
            undefined.setdefault(number, [])
        cases[number]['shadowed'] = sorted(names)

    typeset_result = {'status': 'not requested'}
    if typeset:
        numbers = [number for number in range(len(cases))
                   if not undefined.get(number) and not cases[number]['shadowed']]
        write_typeset(run / 'typeset.tex', cases, numbers)
        code = run_latex(run / 'typeset.tex', run, run / 'typeset.log.txt')
        pdf = run / 'typeset.pdf'
        if code != 0 or not pdf.exists():
            raise ValueError(f'Typesetting failed; see {run / "typeset.log.txt"}')
        differing = compare_streams(pdf, numbers)
        typeset_result = {
            'status': 'compared',
            'cases': len(numbers),
            'sites': sum(len(cases[number]['sites']) for number in numbers),
            'excluded_cases': len(cases) - len(numbers),
            'undefined_control_sequences': dict(sorted(
                Counter(name for names in undefined.values() for name in names).items())),
            'shadowed_control_sequences': dict(sorted(
                Counter(name for case in cases for name in case['shadowed']).items())),
            'differing_cases': [{'case': number, 'macro': cases[number]['macro'],
                                 'argument': cases[number]['arguments'][-1],
                                 'sites': cases[number]['sites']}
                                for number in differing],
        }

    read = [site for site in sites if site['status'] == 'read']
    report = {
        'schema_version': 1,
        'root': str(root),
        'run': str(run),
        'limitations': [
            'The token gate compares spalign\'s own accumulated token list and widest row '
            'with the reader\'s. It does not check the array preamble, the delimiters or '
            'the resulting typography; the typeset gate does.',
            'The typeset gate compares PDF content streams, so it establishes identical '
            'typesetting of the legacy call and the re-rendering, not mathematical review.',
            'Cases whose argument uses a control sequence the book\'s LaTeX packages do not '
            'define are excluded from the typeset gate, because the surrounding source '
            'defines them. They remain covered by the token gate.',
            'render_portable is not compared here. It drops spalign\'s \\hskip-\\arraycolsep '
            'delimiter tightening, which MathJax has no \\arraycolsep for, and rebuilds the '
            'system as alignedat; those are deliberate spacing changes to the same cells, '
            'measured and accepted by the author rather than gated here.',
            'Verification of the frozen legacy source at one revision. It is not a '
            'conversion, and no book content is changed or reviewed here.',
        ],
        'summary': {
            'call_sites': len(sites),
            'read_call_sites': len(read),
            'expansion_dependent': sum(1 for site in sites
                                       if site['status'] == 'expansion-dependent'),
            'undelimited': sum(1 for site in sites if site['status'] == 'undelimited'),
            'distinct_cases': len(cases),
            'token_gate_mismatches': len(mismatches),
            'typeset_gate': typeset_result['status'],
            'typeset_gate_differing': (len(typeset_result['differing_cases'])
                                       if typeset else None),
        },
        'by_macro': {name: Counter(site['status'] for site in sites
                                   if site['macro'] == name)
                     for name in NOTATION.COMPACT_MACROS},
        'token_gate': {'cases': len(cases), 'mismatches': mismatches},
        'typeset_gate': typeset_result,
        'excluded_sites': [site for site in sites if site['status'] != 'read'],
    }
    (run / 'report.json').write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + '\n',
        encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT,
                        help='source Git checkout containing src/ila.xml')
    parser.add_argument('--run', type=Path, required=True,
                        help='fresh evidence directory; must not exist and must lie '
                             'outside the checkout')
    parser.add_argument('--typeset', action='store_true',
                        help='also run the typeset gate, which needs a full TeX installation')
    args = parser.parse_args()
    try:
        report = verify(args.root, args.run, args.typeset)
    except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Verification failed: {error}\n')
    summary = report['summary']
    for key in sorted(summary):
        print(f'{key}: {summary[key]}')
    failed = summary['token_gate_mismatches'] or (summary['typeset_gate_differing'] or 0)
    if failed:
        print(f'\nSee {args.run / "report.json"}', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
