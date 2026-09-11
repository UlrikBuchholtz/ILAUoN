"""Phase 3 census tests: notation reading, and the legacy source it must describe."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('phase3_census', ROOT / 'scripts/phase3_census.py')
CENSUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CENSUS)


class ReaderTests(unittest.TestCase):
    def test_strip_comments_keeps_escaped_percent(self):
        self.assertEqual(CENSUS.strip_comments('a \\% b % gone\nc'), 'a \\% b \nc')

    def test_brace_argument(self):
        optional, arguments, end = CENSUS.read_arguments('\\mat{1 2; 3 4} rest', 4, 1)
        self.assertIsNone(optional)
        self.assertEqual(arguments, [{'kind': 'group', 'text': '1 2; 3 4'}])
        self.assertEqual('\\mat{1 2; 3 4} rest'[end:], ' rest')

    def test_optional_argument(self):
        optional, arguments, _ = CENSUS.read_arguments('\\mat[r]{1 2}', 4, 1)
        self.assertEqual(optional, 'r')
        self.assertEqual(arguments, [{'kind': 'group', 'text': '1 2'}])

    def test_two_mandatory_arguments(self):
        _, arguments, _ = CENSUS.read_arguments('\\nmat[r]{2}{1 2 3 4}', 5, 2)
        self.assertEqual([argument['text'] for argument in arguments], ['2', '1 2 3 4'])

    def test_single_token_argument(self):
        """`\\det\\mat a` is a legitimate one-token TeX argument, not a malformed call."""
        _, arguments, _ = CENSUS.read_arguments('\\det\\mat a=a.', 9, 1)
        self.assertEqual(arguments, [{'kind': 'token', 'text': 'a'}])

    def test_control_sequence_argument_is_flagged(self):
        _, arguments, _ = CENSUS.read_arguments('\\det\\mat\\cdots + 0', 8, 1)
        self.assertEqual(arguments, [{'kind': 'macro', 'text': '\\cdots'}])

    def test_unterminated_group_is_unparsed(self):
        _, arguments, _ = CENSUS.read_arguments('\\mat{1 2', 4, 1)
        self.assertIsNone(arguments)

    def test_split_top_level_respects_braces(self):
        self.assertEqual(CENSUS.split_top_level('a {b; c} d', ';'), ['a {b; c} d'])
        self.assertEqual(CENSUS.split_top_level('a; b', ';'), ['a', 'b'])
        self.assertEqual(CENSUS.split_top_level('a_{1} a_{2}', ' \t\n'), ['a_{1}', 'a_{2}'])


class ShapeTests(unittest.TestCase):
    def test_three_entry_vector_is_one_row_of_three(self):
        """Regression for the aborted port, where a three-entry vector became six rows."""
        shape = CENSUS.spalign_shape('1 2 3')
        self.assertEqual(shape['rows'], 1)
        self.assertEqual(shape['entry_counts'], [3])
        self.assertEqual(shape['entries'], 3)

    def test_subscripted_matrix(self):
        shape = CENSUS.spalign_shape('a_{11} a_{12} a_{13}; a_{21} a_{22} a_{23}')
        self.assertEqual((shape['rows'], shape['entry_counts']), (2, [3]))
        self.assertFalse(shape['ragged'])
        self.assertEqual(shape['braced_entries'], 6)

    def test_ragged_rows_are_reported(self):
        shape = CENSUS.spalign_shape('1 2 3; 4 5')
        self.assertEqual(shape['entry_counts'], [2, 3])
        self.assertTrue(shape['ragged'])

    def test_nested_spalign_is_reported(self):
        shape = CENSUS.spalign_shape('{\\vec{1 2}} {\\vec{3 4}}')
        self.assertEqual(shape['nested_spalign'], 2)
        self.assertEqual(shape['macro_entries'], 2)


class PackageTests(unittest.TestCase):
    def test_compact_notation_macros_are_defined_by_the_book(self):
        macros, environments = CENSUS.package_definitions(ROOT)
        for name in CENSUS.SPALIGN_MACROS:
            self.assertIn(name, macros, name)
        self.assertEqual(macros['mat']['file'], 'src/latex/macros.sty')
        self.assertEqual(macros['syseq']['kind'], 'let')
        self.assertIn('spalignmat', macros)
        self.assertEqual(macros['spalignmat']['file'], 'src/latex/spalign.sty')
        self.assertIn('smm', environments)

    def test_missing_package_is_an_error(self):
        with self.assertRaises(ValueError):
            CENSUS.package_definitions(Path(__file__).parent)


class LegacySourceTests(unittest.TestCase):
    """These read the frozen legacy book source; they change only if that source changes."""

    @classmethod
    def setUpClass(cls):
        cls.census = CENSUS.census(ROOT, examples=3)

    def test_every_compact_notation_call_is_delimited(self):
        self.assertEqual(self.census['summary']['spalign_unparsed'], 0)
        self.assertEqual(self.census['summary']['spalign_calls'], 2437)

    def test_expansion_dependent_call_sites_are_enumerated(self):
        """Six call sites take a control sequence and have no shape before expansion."""
        sites = sorted((example['file'], example['source_element'])
                       for usage in self.census['spalign'].values()
                       for example in usage['expansion_examples'])
        self.assertEqual(sites, [
            ('src/determinant-cofactors.xml', 358),
            ('src/determinant-cofactors.xml', 358),
            ('src/determinant-cofactors.xml', 358),
            ('src/leastsquares.xml', 530),
            ('src/leastsquares.xml', 546),
            ('src/overview.xml', 100),
        ])

    def test_vectors_are_single_rows(self):
        sizes = self.census['spalign']['vec']['shape_totals']['sizes']
        self.assertTrue(sizes)
        for size in sizes:
            self.assertTrue(size.startswith('1x'), size)

    def test_legacy_only_constructs_are_identified(self):
        unmatched = self.census['elements_without_core_xsl_match']
        for name in ('latex-code', 'mathbox', 'bluebox', 'specialcase', 'essential',
                     'concept', 'concept-library', 'latex-image-code'):
            self.assertIn(name, unmatched, name)
        constructs = self.census['constructs']
        self.assertTrue(constructs['m']['in_core_xsl_match'])
        self.assertGreater(constructs['mathbox']['count'], 0)

    def test_stateful_source_macros_are_reported(self):
        defined = self.census['macros_defined_in_source']
        for name in ('r', 'v', 'w', 'b', 'theo'):
            self.assertGreater(defined[name]['uses_in_other_elements'], 0, name)
            self.assertGreater(len(defined[name]['definitions']), 1, name)

    def test_report_is_self_describing(self):
        self.assertEqual(self.census['schema_version'], 1)
        self.assertEqual(self.census['pretext']['version'], CENSUS.BUILD.VERSION)
        self.assertEqual(self.census['pretext']['core'], CENSUS.BUILD.CORE)
        self.assertTrue(self.census['limitations'])


if __name__ == '__main__':
    unittest.main()
