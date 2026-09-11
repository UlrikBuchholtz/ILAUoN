"""Compact-notation reader, its renderings, and the aborted port's failures."""

from collections import Counter
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOTATION = _load('phase3_notation')
PRESERVE = _load('phase3_preserve')
VERIFY = _load('phase3_verify')

BASELINE = json.loads((ROOT / 'migration/baseline-source.json').read_text())
ABORTED = json.loads((ROOT / 'migration/phase3/aborted-port-source.json').read_text())


class TokenizerTests(unittest.TestCase):
    def test_space_after_a_control_word_is_absorbed(self):
        """TeX drops the space that ends `\\frac`, so spalign sees no column break."""
        parsed = NOTATION.parse(r'\frac 12x_3 + 1')
        self.assertEqual(parsed['rows'], [[r'\frac 12x_3', '+', '1']])

    def test_space_after_a_control_symbol_separates(self):
        parsed = NOTATION.parse(r'\. \+ y')
        self.assertEqual(parsed['rows'], [[r'\.', r'\+', 'y']])

    def test_commas_separate_entries(self):
        parsed = NOTATION.parse(r'-\lambda, 2 7; 1 1 1')
        self.assertEqual(parsed['rows'], [[r'-\lambda ', '2', '7'], ['1', '1', '1']])
        self.assertEqual(parsed['maxcols'], 3)

    def test_a_comma_and_a_following_space_are_one_separator(self):
        self.assertEqual(NOTATION.parse('a, b')['rows'], [['a', 'b']])
        self.assertEqual(NOTATION.parse('a b')['rows'], [['a', 'b']])

    def test_braced_groups_stay_whole(self):
        parsed = NOTATION.parse('a_{1 2} b')
        self.assertEqual(parsed['rows'], [['a_{1 2}', 'b']])

    def test_unbalanced_braces_are_refused(self):
        with self.assertRaises(ValueError):
            NOTATION.parse('a {b')


class RenderingTests(unittest.TestCase):
    def test_matrix_matches_spalign_expansion(self):
        self.assertEqual(
            NOTATION.render_tex_equivalent('mat', ['1 2; 3 4']),
            r'\left(\hskip-\arraycolsep\,\begin{array}{rr}1&2\\3&4'
            r'\end{array}\hskip-\arraycolsep\,\right)')

    def test_vector_is_one_column(self):
        self.assertEqual(
            NOTATION.render_tex_equivalent('vec', ['1 2 3']),
            r'\left(\hskip-\arraycolsep\begin{array}{r}1\\2\\3'
            r'\end{array}\hskip-\arraycolsep\right)')

    def test_augmented_rule_sits_before_the_last_column(self):
        self.assertEqual(NOTATION.array_preamble(
            'amat', NOTATION.parse('1 2 3; 4 5 6'), 'r'), 'rr|r')

    def test_halved_matrix_splits_at_the_floor(self):
        self.assertEqual(NOTATION.array_preamble(
            'hmat', NOTATION.parse('1 2 3 4 5 6'), 'r'), 'rrr|rrr')
        self.assertEqual(NOTATION.array_preamble(
            'hmat', NOTATION.parse('1 2 3 4 5'), 'r'), 'rr|rrr')

    def test_nmat_takes_its_augmented_count_from_the_first_argument(self):
        self.assertEqual(NOTATION.array_preamble(
            'nmat', NOTATION.parse('1 2 3 4'), 'r', augmented=2), 'rr|rr')

    def test_portable_form_drops_the_arraycolsep_tightening(self):
        portable = NOTATION.render_portable('mat', ['1 2; 3 4'])
        self.assertNotIn('arraycolsep', portable)
        self.assertEqual(portable,
                         r'\left(\begin{array}{rr}1&2\\3&4\end{array}\right)')

    def test_system_delimiters_are_document_state(self):
        default = NOTATION.render_tex_equivalent('syseq', ['x = 1'])
        self.assertIn(r'\left\{', default)
        changed = NOTATION.render_tex_equivalent('syseq', ['x = 1'], delimiters=['(', ')'])
        self.assertIn(r'\left(', changed)
        self.assertIn(r'\right)', changed)


class AbortedPortRegressionTests(unittest.TestCase):
    """The failures recorded in MIGRATION.md, taken from commit e96ed01."""

    def test_three_entry_vector_stays_three_entries(self):
        """src/vectors-matrices.xml:688. The aborted port split this into six rows,
        because it split on the space that ends `\\cdot` rather than absorbing it."""
        argument = r'1\cdot 2+4\cdot(-1) 2\cdot 2+5\cdot(-1) 3\cdot 2+6\cdot(-1)'
        parsed = NOTATION.parse(argument)
        self.assertEqual(len(parsed['rows']), 1)
        self.assertEqual(parsed['rows'][0],
                         [r'1\cdot 2+4\cdot (-1)', r'2\cdot 2+5\cdot (-1)',
                          r'3\cdot 2+6\cdot (-1)'])
        rendered = NOTATION.render_tex_equivalent('vec', [argument])
        self.assertEqual(rendered.count(r'\\'), 2)

    def test_system_keeps_its_source_delimiters(self):
        """src/vector-spans.xml:37. The aborted port emitted a broken template with
        `|(|)|` residue instead of reading \\spalignsysdelims and the argument."""
        latex = r'\spalignsysdelims()\syseq{ x - y; 2x - 2y; 6x - y} = \vec{8 16 3}.'
        _, delimiters, end = NOTATION.read_arguments(latex, len(r'\spalignsysdelims'), 2)
        self.assertEqual([argument['text'] for argument in delimiters], ['(', ')'])
        _, arguments, _ = NOTATION.read_arguments(latex, latex.index(r'\syseq') + 6, 1)
        rendered = NOTATION.render_tex_equivalent(
            'syseq', [arguments[0]['text']], delimiters=['(', ')'])
        self.assertIn(r'\left(', rendered)
        self.assertEqual(rendered.count(r'\cr '), 3)
        self.assertNotIn('aligned', rendered)

    def test_preservation_gate_catches_the_deleted_subsection(self):
        report = PRESERVE.compare(BASELINE, ABORTED)
        for identifier in ('det-cofact-cramers-rule', 'det-cofact-cramer-ss',
                           'det-cofact-inv-cramer', 'det-cofact-inv-cramer-fn'):
            self.assertIn(identifier, report['lost_ids'], identifier)
        self.assertFalse(report['summary']['divisions_unchanged'])

    def test_preservation_gate_catches_the_lost_demo_contracts(self):
        report = PRESERVE.compare(BASELINE, ABORTED)
        self.assertEqual(report['summary']['baseline_mathboxes'], 167)
        self.assertEqual(report['summary']['lost_mathbox_contracts'], 167)

    def test_preservation_gate_reports_the_lost_markers(self):
        report = PRESERVE.compare(BASELINE, ABORTED)
        for name, baseline in (('essential', 7), ('bluebox', 100),
                               ('specialcase', 62), ('latex-code', 264)):
            self.assertEqual(report['carrier_deltas'][name],
                             {'baseline': baseline, 'candidate': 0}, name)

    def test_preservation_gate_passes_the_baseline_against_itself(self):
        report = PRESERVE.compare(BASELINE, BASELINE)
        self.assertEqual(report['failures'], [])
        self.assertEqual(report['carrier_deltas'], {})


@unittest.skipUnless(shutil.which('pdflatex'), 'pdflatex is required for the typeset gate')
class TypesetGateTests(unittest.TestCase):
    """A gate that never rejects anything proves nothing, so check that it rejects."""

    CASES = [{'macro': 'mat', 'optional': None, 'arguments': ['1 22; 333 4'],
              'delimiters': None, 'tabspace': None, 'sites': []}]

    def compare(self, mutate=None):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            if mutate is None:
                VERIFY.write_typeset(directory / 'typeset.tex', self.CASES, [0])
            else:
                original = NOTATION.render_tex_equivalent
                with patch.object(VERIFY.NOTATION, 'render_tex_equivalent',
                                  lambda *args: mutate(original(*args))):
                    VERIFY.write_typeset(directory / 'typeset.tex', self.CASES, [0])
            code = VERIFY.run_latex(directory / 'typeset.tex', directory,
                                    directory / 'log.txt')
            self.assertEqual(code, 0, (directory / 'log.txt').read_text()[-2000:])
            return VERIFY.compare_streams(directory / 'typeset.pdf', [0])

    def test_the_rendering_matches_the_legacy_call(self):
        self.assertEqual(self.compare(), [])

    def test_a_wrong_column_alignment_is_rejected(self):
        self.assertEqual(self.compare(lambda tex: tex.replace('{rr}', '{ll}')), [0])

    def test_a_missing_delimiter_skip_is_rejected(self):
        self.assertEqual(
            self.compare(lambda tex: tex.replace(r'\hskip-\arraycolsep\,', '')), [0])


class SourceStateTests(unittest.TestCase):
    """These read the frozen legacy source; they change only if that source changes."""

    @classmethod
    def setUpClass(cls):
        cls.sites = VERIFY.call_sites(ROOT)

    def test_every_call_site_is_delimited(self):
        self.assertEqual(len(self.sites), 2437)
        self.assertEqual([site for site in self.sites if site['status'] == 'undelimited'], [])

    def test_systems_carry_their_delimiter_state(self):
        """Only 18 of the 105 systems set their own delimiters; the rest inherit them,
        and 23 inherit a non-default pair, so a local reading would render them wrong."""
        systems = [site for site in self.sites if site['macro'] == 'syseq']
        self.assertEqual(len(systems), 105)
        sources = Counter(site['delimiter_source'] for site in systems)
        self.assertEqual(sources, Counter({'earlier-element': 82, 'element': 18,
                                           'default': 5}))
        inherited = Counter(tuple(site['delimiters']) for site in systems
                            if site['delimiter_source'] == 'earlier-element')
        self.assertEqual(inherited[('.', '.')], 23)

    def test_system_tab_space_is_also_inherited(self):
        systems = [site for site in self.sites if site['macro'] == 'syseq']
        self.assertEqual(Counter(site['tabspace_source'] for site in systems),
                         Counter({'default': 95, 'earlier-element': 9, 'element': 1}))


if __name__ == '__main__':
    unittest.main()
