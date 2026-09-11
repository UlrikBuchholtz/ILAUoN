#!/usr/bin/env python3
"""Census the legacy constructs and mathematical notation Phase 3 must convert.

This measures the active source only. It does not convert anything, and it does
not decide whether a construct or macro is supportable upstream.
"""

import argparse
from collections import Counter, defaultdict
import importlib.resources
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

SCRIPTS = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOTATION = _load('phase3_notation')
strip_comments = NOTATION.strip_comments
read_arguments = NOTATION.read_arguments
split_top_level = NOTATION.split_top_level
spalign_shape = NOTATION.spalign_shape
SPALIGN_MACROS = {name: data['arity'] for name, data in NOTATION.COMPACT_MACROS.items()}

SPEC = importlib.util.spec_from_file_location('phase0_inventory', SCRIPTS / 'phase0_inventory.py')
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)

BUILD_SPEC = importlib.util.spec_from_file_location('build', SCRIPTS / 'build.py')
BUILD = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD)

# Legacy math carriers. <md>/<mdn> hold their LaTeX in <mrow> children.
MATH_ELEMENTS = ('m', 'me', 'men', 'mrow')
MATH_CONTAINERS = ('md', 'mdn')
# Raw LaTeX that PreTeX compiled outside the math elements; state can escape a block.
RAW_LATEX_ELEMENTS = ('latex-code', 'latex-image-code')

PACKAGES = ('src/latex/macros.sty', 'src/latex/spalign.sty', 'src/latex/jdr-tikz.sty')

CONTROL_SEQUENCE = NOTATION.CONTROL_SEQUENCE
BEGIN_ENVIRONMENT = re.compile(r'\\begin\s*\{([^}]*)\}')
DEFINITIONS = (
    ('def', re.compile(r'\\[egx]?def\s*\\([A-Za-z@]+)')),
    ('let', re.compile(r'\\let\s*\\([A-Za-z@]+)')),
    ('newcommand', re.compile(r'\\(?:re)?newcommand\*?\s*\{?\\([A-Za-z@]+)')),
    ('paired-delimiter', re.compile(r'\\DeclarePairedDelimiter(?:X)?\s*\{?\\([A-Za-z@]+)')),
    # spalign.sty defines its public entry points through its own starred definer.
    ('spalign-definer', re.compile(r'\\spalign@def@star\s*\\([A-Za-z@]+)')),
)
ENVIRONMENT_DEFINITIONS = re.compile(r'\\(?:re)?newenvironment\s*\{([^}]*)\}')


def package_definitions(root):
    """Collect the control sequences and environments the book's LaTeX packages define."""
    macros, environments = {}, {}
    for name in PACKAGES:
        path = root / name
        if not path.exists():
            raise ValueError(f'Missing LaTeX package: {name}')
        body = strip_comments(path.read_text(encoding='utf-8'))
        for kind, pattern in DEFINITIONS:
            for macro in pattern.findall(body):
                macros.setdefault(macro, {'file': name, 'kind': kind})
        for environment in ENVIRONMENT_DEFINITIONS.findall(body):
            environments.setdefault(environment, {'file': name})
    return macros, environments


def upstream_core_names(core):
    """Names appearing in pinned-core XSL match patterns, with entities expanded."""
    with importlib.resources.path('pretext.resources', 'core.zip') as archive:
        with zipfile.ZipFile(archive) as bundle:
            prefix = f'pretext-{core}/'
            if not any(name.startswith(prefix) for name in bundle.namelist()):
                raise ValueError(f'core.zip does not contain the pinned core {core}')
            entities = dict(re.findall(
                r'<!ENTITY\s+([A-Za-z0-9._-]+)\s+"([^"]*)"',
                bundle.read(prefix + 'xsl/entities.ent').decode('utf-8')))
            tokens, schema = set(), set()
            for name in bundle.namelist():
                if name.startswith(prefix + 'xsl/') and name.endswith('.xsl'):
                    body = bundle.read(name).decode('utf-8', 'replace')
                    for pattern in re.findall(r'match="([^"]+)"', body):
                        for _ in range(8):
                            expanded = re.sub(
                                r'&([A-Za-z0-9._-]+);',
                                lambda match: entities.get(match.group(1), match.group(0)),
                                pattern)
                            if expanded == pattern:
                                break
                            pattern = expanded
                        tokens.update(re.findall(r'[A-Za-z][A-Za-z0-9._-]*', pattern))
                elif name.startswith(prefix + 'schema/') and name.endswith('.rng'):
                    schema.update(re.findall(
                        r'element name="([^"]+)"',
                        bundle.read(name).decode('utf-8', 'replace')))
    return tokens, schema


def census(root, examples):
    root = Path(root).resolve()
    import pretext  # Imported here so the notation readers stay testable without it.
    if (pretext.VERSION, pretext.CORE_COMMIT) != (BUILD.VERSION, BUILD.CORE):
        raise ValueError(f'Installed PreTeXt {pretext.VERSION}/{pretext.CORE_COMMIT} '
                         f'does not match the pinned {BUILD.VERSION}/{BUILD.CORE}')
    xsl_tokens, schema_elements = upstream_core_names(BUILD.CORE)
    defined_macros, defined_environments = package_definitions(root)
    book, files, origins, _ = INVENTORY.load_active_source(root)

    element_counts = Counter()
    element_attributes = defaultdict(Counter)
    macro_usage = defaultdict(lambda: {'count': 0, 'files': Counter(), 'examples': []})
    environment_usage = defaultdict(lambda: {'count': 0, 'files': Counter()})
    spalign_usage = {name: {'count': 0, 'files': Counter(), 'unparsed': 0, 'shapes': [],
                            'token_arguments': 0, 'expansion_dependent': 0,
                            'examples': [], 'unparsed_examples': [], 'expansion_examples': []}
                     for name in SPALIGN_MACROS}
    math_counts = Counter()
    container_text = []
    source_definitions = defaultdict(list)
    usage_positions = defaultdict(list)
    order = [0]

    def snippet(text):
        return ' '.join(text.split())[:160]

    def record_latex(latex, where, kind):
        latex = strip_comments(latex)
        order[0] += 1
        position = {**where, 'order': order[0]}
        for definition_kind, pattern in DEFINITIONS:
            for macro in pattern.findall(latex):
                source_definitions[macro].append({**position, 'definition': definition_kind})
        math_counts[kind] += 1
        math_counts[f'{kind}_characters'] += len(latex)
        for macro in CONTROL_SEQUENCE.findall(latex):
            name = macro[1:]
            entry = macro_usage[name]
            entry['count'] += 1
            entry['files'][where['file']] += 1
            usage_positions[name].append(position)
            if len(entry['examples']) < examples:
                entry['examples'].append({**where, 'latex': snippet(latex)})
        for environment in BEGIN_ENVIRONMENT.findall(latex):
            entry = environment_usage[environment]
            entry['count'] += 1
            entry['files'][where['file']] += 1
        for name, arity in SPALIGN_MACROS.items():
            for match in re.finditer(r'\\' + name + r'(?![A-Za-z@])', latex):
                usage = spalign_usage[name]
                usage['count'] += 1
                usage['files'][where['file']] += 1
                _, arguments, _ = read_arguments(latex, match.end(), arity)
                if arguments is None:
                    usage['unparsed'] += 1
                    usage['unparsed_examples'].append({**where, 'latex': snippet(latex)})
                    continue
                kinds = {argument['kind'] for argument in arguments}
                if 'macro' in kinds:
                    usage['expansion_dependent'] += 1
                    usage['expansion_examples'].append({**where, 'latex': snippet(latex)})
                    continue
                if 'token' in kinds:
                    usage['token_arguments'] += 1
                usage['shapes'].append(spalign_shape(arguments[-1]['text']))
                if len(usage['examples']) < examples:
                    usage['examples'].append({**where, 'latex': snippet(latex)})

    def walk(element):
        element_counts[element.tag] += 1
        for attribute in element.attrib:
            element_attributes[element.tag][attribute] += 1
        where = dict(origins[element])
        if element.tag in MATH_ELEMENTS:
            record_latex(''.join(element.itertext()), where, 'math')
        elif element.tag in RAW_LATEX_ELEMENTS:
            record_latex(''.join(element.itertext()), where, 'raw_latex')
        elif element.tag in MATH_CONTAINERS:
            if (element.text or '').strip() or any((child.tail or '').strip() for child in element):
                container_text.append(where)
        for child in element:
            walk(child)

    walk(book)

    def summarize(entry):
        return {**entry, 'files': dict(sorted(entry['files'].items()))}

    def shape_totals(shapes):
        sizes = Counter(f"{shape['rows']}x{'/'.join(map(str, shape['entry_counts']))}"
                        for shape in shapes)
        return {
            'parsed': len(shapes),
            'ragged': sum(1 for shape in shapes if shape['ragged']),
            'nested_spalign': sum(shape['nested_spalign'] for shape in shapes),
            'braced_entries': sum(shape['braced_entries'] for shape in shapes),
            'macro_entries': sum(shape['macro_entries'] for shape in shapes),
            'entries': sum(shape['entries'] for shape in shapes),
            'sizes': dict(sorted(sizes.items(), key=lambda item: (-item[1], item[0]))),
        }

    constructs = {}
    for tag, count in element_counts.items():
        constructs[tag] = {
            'count': count,
            'attributes': dict(sorted(element_attributes[tag].items())),
            'in_pinned_schema': tag in schema_elements,
            'in_core_xsl_match': tag in xsl_tokens,
        }
    unhandled = sorted((tag for tag, data in constructs.items()
                        if not data['in_core_xsl_match']),
                       key=lambda tag: (-constructs[tag]['count'], tag))

    in_source_macros = {}
    for name, definitions in source_definitions.items():
        first = min(definition['order'] for definition in definitions)
        elsewhere = [position for position in usage_positions.get(name, [])
                     if position['order'] != first]
        in_source_macros[name] = {
            'definitions': definitions,
            'uses': len(usage_positions.get(name, [])),
            'uses_in_other_elements': len(elsewhere),
            'files_using': dict(sorted(Counter(position['file'] for position in elsewhere).items())),
        }

    book_macros = {name: data for name, data in macro_usage.items() if name in defined_macros}
    other_macros = {name: data for name, data in macro_usage.items() if name not in defined_macros}
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                              check=True, capture_output=True, text=True).stdout.strip()
    return {
        'schema_version': 1,
        'git_revision': revision,
        'entrypoint': 'src/ila.xml',
        'pretext': {'version': BUILD.VERSION, 'core': BUILD.CORE},
        'limitations': [
            'Census of the active XInclude graph only; inactive src/*.xml and demos are excluded.',
            'Macro counts are lexical control-sequence occurrences in <m>, <me>, <men>, <mrow>, '
            '<latex-code> and <latex-image-code> text after removing TeX line comments. '
            'No macro is expanded and no LaTeX is executed, so counts include arguments of '
            'macros that suppress them and exclude anything produced by expansion.',
            'book_macros are names defined in src/latex/*.sty. other_macros are every remaining '
            'control sequence: this is not a claim that they are or are not supported by MathJax.',
            'in_core_xsl_match records whether the element name appears in a pinned-core XSL '
            'match pattern after entity expansion. It is a review signal, not proof of support; '
            'in_pinned_schema is weaker still, because the pinned RelaxNG schema is incomplete.',
            'spalign shapes are parsed from the source token text: rows split on top-level ";" '
            'and entries on top-level whitespace, matching spalign.sty but not its TeX-level '
            'grouping and expansion. Mandatory arguments follow TeX\'s rule, so a single token '
            'or control sequence is an argument. expansion_dependent call sites take a control '
            'sequence and have no shape until TeX expands it; unparsed call sites are those this '
            'reader could not delimit at all. Both are conversion risks, not parser defects.',
            'macros_defined_in_source are control sequences defined inside the book source '
            'itself. uses_in_other_elements counts occurrences outside the element that first '
            'defines the name, which is where LaTeX state crosses a block boundary; a name '
            'redefined several times is only compared against its first definition.',
            'Attribute counts are raw source attribute names; their publisher semantics, '
            'numbering, visibility and cross-reference behavior are not modeled here.',
        ],
        'summary': {
            'source_xml_files': len(files),
            'elements': sum(element_counts.values()),
            'distinct_elements': len(element_counts),
            'elements_without_core_xsl_match': len(unhandled),
            'math_elements': math_counts['math'],
            'raw_latex_elements': math_counts['raw_latex'],
            'math_characters': math_counts['math_characters'],
            'raw_latex_characters': math_counts['raw_latex_characters'],
            'distinct_macros': len(macro_usage),
            'book_macros_used': len(book_macros),
            'book_macros_defined': len(defined_macros),
            'other_macros_used': len(other_macros),
            'macro_occurrences': sum(entry['count'] for entry in macro_usage.values()),
            'spalign_calls': sum(usage['count'] for usage in spalign_usage.values()),
            'spalign_unparsed': sum(usage['unparsed'] for usage in spalign_usage.values()),
            'spalign_token_arguments': sum(usage['token_arguments']
                                           for usage in spalign_usage.values()),
            'spalign_expansion_dependent': sum(usage['expansion_dependent']
                                               for usage in spalign_usage.values()),
            'math_containers_with_direct_text': len(container_text),
            'macros_defined_in_source': len(in_source_macros),
            'macros_defined_in_source_used_elsewhere': sum(
                1 for data in in_source_macros.values() if data['uses_in_other_elements']),
        },
        'constructs': dict(sorted(constructs.items())),
        'elements_without_core_xsl_match': unhandled,
        'book_macro_definitions': dict(sorted(defined_macros.items())),
        'book_environment_definitions': dict(sorted(defined_environments.items())),
        'book_macros': {name: summarize(book_macros[name])
                        for name in sorted(book_macros, key=lambda n: (-book_macros[n]['count'], n))},
        'other_macros': {name: summarize(other_macros[name])
                         for name in sorted(other_macros, key=lambda n: (-other_macros[n]['count'], n))},
        'environments': {name: summarize(entry)
                         for name, entry in sorted(environment_usage.items(),
                                                   key=lambda item: (-item[1]['count'], item[0]))},
        'spalign': {name: {'count': usage['count'], 'unparsed': usage['unparsed'],
                           'token_arguments': usage['token_arguments'],
                           'expansion_dependent': usage['expansion_dependent'],
                           'files': dict(sorted(usage['files'].items())),
                           'shape_totals': shape_totals(usage['shapes']),
                           'examples': usage['examples'],
                           'unparsed_examples': usage['unparsed_examples'],
                           'expansion_examples': usage['expansion_examples']}
                    for name, usage in spalign_usage.items()},
        'macros_defined_in_source': dict(sorted(in_source_macros.items())),
        'math_containers_with_direct_text': container_text,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=SCRIPTS.parent,
                        help='source Git checkout containing src/ila.xml')
    parser.add_argument('--examples', type=int, default=3,
                        help='retained example occurrences per macro (default 3)')
    parser.add_argument('--output', type=Path,
                        help='write generated JSON here instead of stdout; parent must exist')
    args = parser.parse_args()
    try:
        result = json.dumps(census(args.root, args.examples),
                            indent=2, sort_keys=True, ensure_ascii=True) + '\n'
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Census failed: {error}\n')
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        sys.stdout.write(result)


if __name__ == '__main__':
    main()
