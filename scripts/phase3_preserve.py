#!/usr/bin/env python3
"""Compare a candidate source tree with the Phase 0 baseline inventory.

Phase 3's gate requires conversion to preserve IDs, order, captions, dimensions,
essential markers and visibility semantics. This checks the part of that which is
well defined before the target markup is chosen: every baseline xml:id still
exists, division order and titles are unchanged, every MathBox demo contract is
still present, every resolved xref still resolves, and preservation-critical
elements have not silently disappeared.

It deliberately does not compare element names one to one. Conversion renames
markup on purpose; losing content is what this refuses.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('phase0_inventory', SCRIPTS / 'phase0_inventory.py')
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)

# Elements whose disappearance is content loss rather than a change of markup.
# Renaming these is expected; a converted tree simply must still carry as many of
# the things they mark, which is why they are reported rather than gated on name.
CARRIERS = ('chapter', 'section', 'subsection', 'figure', 'caption', 'example',
            'definition', 'theorem', 'proposition', 'corollary', 'fact', 'proof',
            'remark', 'note', 'objectives', 'exercise', 'solution', 'essential',
            'bluebox', 'specialcase', 'mathbox', 'latex-code', 'latex-image-code',
            'm', 'me', 'men', 'md', 'mdn', 'mrow', 'idx', 'term', 'notation')


def divisions(report):
    return [(division['id'], division['title']) for division in report['ordered_divisions']]


def mathbox_contracts(report):
    """The demo URL contracts: each embed's source and its published height."""
    return sorted((box['attributes'].get('source'), box['attributes'].get('height'))
                  for box in report['mathboxes'])


def compare(baseline, candidate):
    lost_ids = sorted(set(baseline['xml_ids']) - set(candidate['xml_ids']))
    added_ids = sorted(set(candidate['xml_ids']) - set(baseline['xml_ids']))
    baseline_boxes, candidate_boxes = mathbox_contracts(baseline), mathbox_contracts(candidate)
    lost_boxes = [box for box in baseline_boxes if box not in candidate_boxes]
    baseline_divisions, candidate_divisions = divisions(baseline), divisions(candidate)
    reordered = baseline_divisions != candidate_divisions
    baseline_targets = {(xref['file'], xref['source_element'], target['id'])
                        for xref in baseline['xrefs'] for target in xref['targets']
                        if target['status'] != 'unresolved'}
    unresolved = {(entry['file'], entry['source_element'], entry['id'])
                  for entry in candidate['unresolved_xref_targets']}
    broken = sorted(target for target in baseline_targets
                    if target[2] in {entry[2] for entry in unresolved})
    deltas = {}
    for name in CARRIERS:
        before = baseline['element_counts'].get(name, 0)
        after = candidate['element_counts'].get(name, 0)
        if before != after:
            deltas[name] = {'baseline': before, 'candidate': after}
    failures = []
    if lost_ids:
        failures.append(f'{len(lost_ids)} baseline xml:id values are missing')
    if lost_boxes:
        failures.append(f'{len(lost_boxes)} MathBox demo contracts are missing')
    if reordered:
        failures.append('division order or titles changed')
    if broken:
        failures.append(f'{len(broken)} previously resolved xref targets no longer resolve')
    return {
        'schema_version': 1,
        'baseline_revision': baseline['git_revision'],
        'candidate_revision': candidate['git_revision'],
        'limitations': [
            'Source comparison only: no rendering, numbering, cross-reference phrasing or '
            'accessibility claim is made here.',
            'Element deltas are reported, not gated. Conversion renames markup on purpose, '
            'so a drop in bluebox or latex-code is expected; a drop in figure or proof is '
            'a question for the reviewer.',
            'Captions and visibility are not compared, because that needs the target '
            'mapping for hide-type, type-name and visible, which is still an open decision.',
            'Added xml:id values are listed, not refused: conversion may need new ids.',
        ],
        'summary': {
            'baseline_ids': len(baseline['xml_ids']),
            'candidate_ids': len(candidate['xml_ids']),
            'lost_ids': len(lost_ids),
            'added_ids': len(added_ids),
            'baseline_mathboxes': len(baseline_boxes),
            'lost_mathbox_contracts': len(lost_boxes),
            'divisions_unchanged': not reordered,
            'broken_xref_targets': len(broken),
            'changed_carrier_elements': len(deltas),
        },
        'failures': failures,
        'lost_ids': lost_ids,
        'added_ids': added_ids,
        'lost_mathbox_contracts': lost_boxes,
        'broken_xref_targets': broken,
        'carrier_deltas': deltas,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path,
                        default=SCRIPTS.parent / 'migration/baseline-source.json',
                        help='Phase 0 baseline source inventory')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--root', type=Path,
                       help='candidate checkout containing src/ila.xml, inventoried here')
    group.add_argument('--candidate', type=Path,
                       help='candidate source inventory JSON produced earlier')
    parser.add_argument('--output', type=Path,
                        help='write generated JSON here instead of stdout; parent must exist')
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
        candidate = (json.loads(args.candidate.read_text(encoding='utf-8'))
                     if args.candidate else INVENTORY.inventory(args.root))
        report = compare(baseline, candidate)
    except (OSError, ValueError, KeyError, ET.ParseError,
            subprocess.CalledProcessError) as error:
        parser.exit(1, f'Comparison failed: {error}\n')
    result = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        sys.stdout.write(result)
    for failure in report['failures']:
        print(f'FAIL: {failure}', file=sys.stderr)
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
