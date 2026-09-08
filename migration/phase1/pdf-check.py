#!/usr/bin/env python3
"""Inspect pilot PDF structure and retained FO; this is not a PDF/UA validator."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from PyPDF2 import PdfReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--fo', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--verapdf', type=Path, help='optional pinned veraPDF CLI executable')
    args = parser.parse_args()
    report_path = args.report.resolve()
    repo = Path(__file__).resolve().parents[2]
    baseline = (Path.home() / 'tmp/ila/phase0').resolve()
    if report_path.is_relative_to(repo) or report_path.is_relative_to(baseline):
        parser.error('Report must be outside the repository and baseline')
    with report_path.open('x') as destination:
        reader = PdfReader(str(args.pdf))
        catalog = reader.trailer['/Root'].get_object()
        counts = Counter()
        figures = []
        seen = set()

        def walk(value):
            if hasattr(value, 'get_object'):
                value = value.get_object()
            if isinstance(value, list):
                for child in value:
                    walk(child)
            elif isinstance(value, dict) and id(value) not in seen:
                seen.add(id(value))
                role = str(value.get('/S', ''))
                if role:
                    counts[role] += 1
                if role in ('/Figure', '/Formula'):
                    figures.append({'role': role, 'alt': str(value.get('/Alt', '')),
                                    'actual_text': str(value.get('/ActualText', ''))})
                if '/K' in value:
                    walk(value['/K'])

        structure = catalog.get('/StructTreeRoot')
        if structure:
            walk(structure)
        fo_text = args.fo.read_text()
        tree = ET.fromstring(fo_text)
        ns = {'fo': 'http://www.w3.org/1999/XSL/Format'}
        alt = '{http://xmlgraphics.apache.org/fop/extensions}alt-text'
        graphics = [{'src': item.get('src'), 'alt': item.get(alt)}
                    for item in tree.findall('.//fo:external-graphic', ns)]
        log = args.log.read_text(errors='replace')
        warnings = [line for line in log.splitlines() if '[WARN]' in line]
        overflow = []
        for line in warnings:
            if 'exceed the available area' in line:
                match = re.search(r'position 1:(\d+)', line)
                offset = int(match[1]) if match else 0
                overflow.append({'message': line, 'fo_context': fo_text[max(0, offset - 300):offset + 150]})
        result = {
            'limitations': ['Structural inspection, not PDF/UA validation or screen-reader approval.',
                            'A Figure with spoken Alt text is not navigable mathematical structure.',
                            'FOP log coordinates are approximate diagnostic contexts, not source positions.'],
            'inputs': {name: {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                       for name, path in [('pdf', args.pdf), ('fo', args.fo), ('log', args.log)]},
            'pages': len(reader.pages), 'language': str(catalog.get('/Lang', '')),
            'has_structure_tree': bool(structure), 'structure_roles': dict(counts),
            'figures': figures, 'figures_missing_alt': sum(not item['alt'] for item in figures),
            'figures_placeholder_alt': sum(item['alt'] == 'No alternate text specified' for item in figures),
            'fo_external_graphics': graphics,
            'fo_graphics_missing_alt': sum(item['alt'] is None or not item['alt'].strip() for item in graphics),
            'fop_warnings': warnings, 'overflow': overflow,
        }
        if args.verapdf:
            validation = subprocess.run([str(args.verapdf), '--format', 'json', '--flavour', 'ua1', str(args.pdf)],
                                        capture_output=True, text=True, timeout=120)
            validation_report = json.loads(validation.stdout)
            jobs = validation_report['report']['jobs']
            checks = [check for job in jobs for check in job.get('validationResult', [])]
            result['verapdf'] = {'executable': str(args.verapdf.resolve()),
                                 'returncode': validation.returncode, 'stderr': validation.stderr,
                                 'report': validation_report,
                                 'passed': validation.returncode == 0 and len(jobs) == 1 and len(checks) == 1
                                 and checks[0].get('compliant') is True and checks[0].get('jobEndStatus') == 'normal'}
        json.dump(result, destination, indent=2)
        destination.write('\n')
    print(json.dumps({key: result[key] for key in ['pages', 'has_structure_tree', 'structure_roles',
                                                   'figures_missing_alt', 'figures_placeholder_alt', 'fo_graphics_missing_alt']}))
    return int(bool(result['figures_missing_alt'] or result['figures_placeholder_alt'] or
                    result['fo_graphics_missing_alt'] or overflow or counts['/TH'] < 6 or
                    (args.verapdf and not result['verapdf']['passed'])))


if __name__ == '__main__':
    raise SystemExit(main())
