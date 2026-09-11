#!/usr/bin/env python3
"""Read the book's compact matrix notation and re-render it explicitly.

`src/latex/spalign.sty` builds its array from TeX tokens: entries are separated
by spaces or commas, rows by semicolons, and the array preamble is only known
after the widest row has been seen. Nothing here expands macros or runs TeX, so
this parser is a claim about spalign's behavior that `scripts/phase3_verify.py`
checks against TeX itself, call site by call site.
"""

import re

CONTROL_SEQUENCE = re.compile(r'\\(?:[A-Za-z@]+|.)', re.DOTALL)


def strip_comments(latex):
    """Remove TeX line comments, keeping escaped percent signs."""
    return re.sub(r'(?<!\\)%.*', '', latex)


def read_group(text, start):
    """Return (content, end) for the brace group beginning at text[start] == '{'."""
    depth = 0
    for index in range(start, len(text)):
        character = text[index]
        if character == '{' and (index == start or text[index - 1] != '\\'):
            depth += 1
        elif character == '}' and text[index - 1] != '\\':
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
    return None, len(text)


def read_arguments(text, start, count):
    """Read one optional [..] argument and `count` mandatory arguments from text[start:].

    Mandatory arguments follow TeX's rule, so the book's `\\mat a` and `\\det\\mat\\cdots`
    are one-token arguments rather than malformed calls. The kind is reported because a
    control-sequence argument is only known after expansion.
    """
    index = start
    optional = None
    while index < len(text) and text[index].isspace():
        index += 1
    if index < len(text) and text[index] == '[':
        end = text.find(']', index)
        if end == -1:
            return None, None, len(text)
        optional, index = text[index + 1:end], end + 1
    arguments = []
    for _ in range(count):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return None, None, index
        if text[index] == '{':
            group, index = read_group(text, index)
            if group is None:
                return None, None, index
            arguments.append({'kind': 'group', 'text': group})
        elif text[index] == '\\':
            macro = CONTROL_SEQUENCE.match(text, index)
            if macro is None:
                return None, None, index
            arguments.append({'kind': 'macro', 'text': macro.group()})
            index = macro.end()
        else:
            arguments.append({'kind': 'token', 'text': text[index]})
            index += 1
    return optional, arguments, index

# Mandatory-argument counts and the alignment defaults src/latex/macros.sty passes.
# `nmat` takes the augmented column count first; `syseq` is \spalignsys, which has
# no optional argument because macros.sty binds it with \let.
COMPACT_MACROS = {
    'vec': {'arity': 1, 'alignment': 'r', 'kind': 'vector'},
    'mat': {'arity': 1, 'alignment': 'r', 'kind': 'matrix'},
    'amat': {'arity': 1, 'alignment': 'r', 'kind': 'augmented', 'augmented': 1},
    'nmat': {'arity': 2, 'alignment': 'r', 'kind': 'augmented'},
    'hmat': {'arity': 1, 'alignment': 'r', 'kind': 'halved'},
    'syseq': {'arity': 1, 'alignment': None, 'kind': 'system'},
}
DELIMITERS = ('(', ')')
SYSTEM_DELIMITERS = (r'\{', '.')
# \DeclareStringOption defaults in spalign.sty, as macros.sty leaves them.
MATRIX_DELIMITER_SKIP = r'\hskip-\arraycolsep\,'
VECTOR_DELIMITER_SKIP = r'\hskip-\arraycolsep'
SYSTEM_DELIMITER_SKIP = r'\,'


def tokenize(text):
    """Split LaTeX source into the tokens spalign's parser sees, one at a time."""
    tokens, index = [], 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            end = index
            while end < len(text) and text[end].isspace():
                end += 1
            tokens.append(('space', text[index:end]))
            index = end
        elif character == '{':
            depth, end = 0, index
            while end < len(text):
                if text[end] == '{' and (end == index or text[end - 1] != '\\'):
                    depth += 1
                elif text[end] == '}' and text[end - 1] != '\\':
                    depth -= 1
                    if depth == 0:
                        break
                end += 1
            if depth != 0:
                raise ValueError(f'Unbalanced brace group: {text[index:index + 40]!r}')
            tokens.append(('group', text[index + 1:end]))
            index = end + 1
        elif character == '\\':
            match = CONTROL_SEQUENCE.match(text, index)
            if match is None:
                raise ValueError(f'Dangling backslash: {text[index:index + 40]!r}')
            index = match.end()
            if match.group()[1:].isalpha():
                # TeX absorbs the spaces that terminate a control word, so `\frac 32`
                # holds no space token and spalign sees no column break there. The
                # terminator stays in the token, which is also how \the prints it.
                while index < len(text) and text[index].isspace():
                    index += 1
                tokens.append(('macro', match.group() + ' '))
            else:
                tokens.append(('macro', match.group()))
        else:
            tokens.append(('char', character))
            index += 1
    return tokens


def parse(argument):
    """Run spalign's state machine over one argument.

    Returns the cells in document order and the widest row, which is what
    \\spalignmaxcols holds when spalign builds the array preamble.
    """
    rows, cells, current = [], [], []
    maxcols, columns = 0, 0
    ignore_spaces, saw_space = True, False

    def end_cell():
        cells.append(''.join(current))
        current.clear()

    def add_column():
        nonlocal columns
        end_cell()
        columns += 1

    def normal_token():
        nonlocal ignore_spaces
        if saw_space and not ignore_spaces:
            add_column()
        ignore_spaces = False

    def end_row():
        nonlocal columns, maxcols, ignore_spaces
        end_cell()
        columns += 1
        maxcols = max(maxcols, columns)
        columns = 0
        ignore_spaces = True
        rows.append(list(cells))
        cells.clear()

    for kind, text in tokenize(argument):
        if kind == 'space':
            saw_space = True
            continue
        if kind == 'group':
            normal_token()
            current.append('{' + text + '}')
        elif (kind, text) == ('char', ';'):
            end_row()
        elif (kind, text) == ('char', ','):
            add_column()
            ignore_spaces = True
        else:
            normal_token()
            current.append(text)
        saw_space = False
    end_row()  # \spalign@end ends the final row, even when the source ends in ';'.
    return {'rows': rows, 'maxcols': maxcols}


def token_dump(text):
    """Normalize LaTeX source the way \\the on a token register prints it.

    TeX terminates a multi-letter control sequence with one space and a single
    character control sequence, such as `\\\\` or `\\,`, with none.
    """
    text = re.sub(r'\s+', ' ', text)
    pieces, index = [], 0
    while index < len(text):
        if text[index] == '\\':
            match = CONTROL_SEQUENCE.match(text, index)
            if match is None:
                raise ValueError(f'Dangling backslash: {text[index:index + 40]!r}')
            name = match.group()[1:]
            pieces.append(match.group())
            index = match.end()
            if name.isalpha() or name == '@':
                pieces.append(' ')
                while index < len(text) and text[index] == ' ':
                    index += 1
        else:
            pieces.append(text[index])
            index += 1
    return ''.join(pieces).strip()


def render_body(parsed, vector=False, row_separator='\\\\'):
    """The token list spalign accumulates, with `&` between cells.

    A vector redefines the column separator to `\\\\` as well, so every separator
    becomes a row break and the array has a single column. A system redefines the
    row separator to `\\cr`, because it builds a `\\halign` rather than an array.
    """
    separator = row_separator if vector else '&'
    return token_dump(row_separator.join(separator.join(row) for row in parsed['rows']))


def array_preamble(macro, parsed, alignment, augmented=None):
    """Reproduce the preamble spalign builds once it knows the widest row."""
    columns = parsed['maxcols']
    kind = COMPACT_MACROS[macro]['kind']
    if kind == 'vector':
        return alignment
    if kind == 'matrix':
        return alignment * columns
    if kind == 'augmented':
        # \spalignaugmatn moves the last `augmented` columns past the rule.
        right = COMPACT_MACROS[macro].get('augmented', augmented)
        return alignment * (columns - right) + '|' + alignment * right
    if kind == 'halved':
        # \spalignaugmathalf splits at floor(maxcols / 2).
        left = columns // 2
        return alignment * left + '|' + alignment * (columns - left)
    raise ValueError(f'No array preamble for {macro}')


def render_tex_equivalent(macro, arguments, alignment=None, delimiters=None):
    """Exactly what spalign expands this call site to, for differential checking.

    A system's delimiters are document state: the source calls \\spalignsysdelims
    before some call sites, so they are passed in rather than assumed.
    """
    definition = COMPACT_MACROS[macro]
    alignment = alignment or definition['alignment']
    parsed = parse(arguments[-1])
    if definition['kind'] == 'system':
        left, right = delimiters or SYSTEM_DELIMITERS
        # \spalignsys sets up its own \halign; \+, \= and \. are local to it.
        body = render_body(parsed, row_separator=r'\cr ')
        return (f'\\left{left}{SYSTEM_DELIMITER_SKIP}'
                r'\vcenter{\openup1pt\tabskip=0pt'
                r'\def\+{\mathbin{\phantom{+}}}\def\={\mathrel{\phantom{=}}}\def\.{}'
                r'\halign{\tabskip=\spalignsystabspace&$\hfil#$&${}#{}$\cr '
                f'{body}' r'\crcr}}\hskip-\spalignsystabspace'
                f'{SYSTEM_DELIMITER_SKIP}\\right{right}')
    vector = definition['kind'] == 'vector'
    skip = VECTOR_DELIMITER_SKIP if vector else MATRIX_DELIMITER_SKIP
    augmented = int(arguments[0]) if macro == 'nmat' else None
    preamble = array_preamble(macro, parsed, alignment, augmented)
    body = render_body(parsed, vector=vector)
    return (f'\\left{DELIMITERS[0]}{skip}\\begin{{array}}{{{preamble}}}'
            f'{body}\\end{{array}}{skip}\\right{DELIMITERS[1]}')


def render_portable(macro, arguments, alignment=None, delimiters=None):
    """A MathJax-renderable form of the same array.

    This drops spalign's `\\hskip-\\arraycolsep` delimiter tightening, which MathJax
    has no `\\arraycolsep` for, and replaces the system's `\\halign` with an array of
    alternating right- and left-aligned columns. Both are spacing changes to the
    same parsed cells, not a different reading of the notation.
    """
    definition = COMPACT_MACROS[macro]
    alignment = alignment or definition['alignment']
    parsed = parse(arguments[-1])
    if definition['kind'] == 'system':
        left, right = delimiters or SYSTEM_DELIMITERS
        width = max((len(row) for row in parsed['rows']), default=0)
        preamble = ''.join('rl'[index % 2] for index in range(width))
        body = token_dump(r'\\'.join('&'.join(row) for row in parsed['rows']))
        return (f'\\left{left}\\begin{{array}}{{{preamble}}}{body}'
                f'\\end{{array}}\\right{right}')
    vector = definition['kind'] == 'vector'
    augmented = int(arguments[0]) if macro == 'nmat' else None
    preamble = array_preamble(macro, parsed, alignment, augmented)
    body = render_body(parsed, vector=vector)
    return (f'\\left{DELIMITERS[0]}\\begin{{array}}{{{preamble}}}'
            f'{body}\\end{{array}}\\right{DELIMITERS[1]}')


def split_top_level(text, separators):
    """Split on separators that sit outside braces; returns stripped, nonempty parts."""
    parts, current, depth = [], [], 0
    for character in text:
        if character == '{':
            depth += 1
        elif character == '}':
            depth -= 1
        if depth == 0 and character in separators:
            parts.append(''.join(current))
            current = []
        else:
            current.append(character)
    parts.append(''.join(current))
    return [part.strip() for part in parts if part.strip()]


def spalign_shape(argument):
    """Describe a parsed argument: rows, per-row cell counts, and what the cells hold."""
    parsed = parse(argument)
    rows = parsed['rows']
    widths = sorted({len(row) for row in rows})
    cells = [cell for row in rows for cell in row]
    return {
        'rows': len(rows),
        'maxcols': parsed['maxcols'],
        'entry_counts': widths,
        'ragged': len(widths) > 1,
        'entries': len(cells),
        'empty_entries': sum(1 for cell in cells if not cell.strip()),
        'braced_entries': sum(1 for cell in cells if '{' in cell),
        'macro_entries': sum(1 for cell in cells if '\\' in cell),
        'nested_spalign': sum(1 for cell in cells
                              if any(f'\\{name}' in cell for name in COMPACT_MACROS)),
    }
