"""Source-level fixture checks; no schema, browser, or build required."""

from collections import Counter
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import sympy as sp


SOURCE = Path(__file__).resolve().parents[1] / "source" / "main.ptx"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def matrix(body):
    return sp.Matrix([
        [sp.Rational(cell.strip()) for cell in row.split("&")]
        for row in body.strip().split(r"\\")
    ])


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(SOURCE).getroot()
        cls.by_id = {el.get(XML_ID): el for el in cls.root.iter() if el.get(XML_ID)}

    def test_ids_and_xrefs(self):
        ids = [el.get(XML_ID) for el in self.root.iter() if XML_ID in el.attrib]
        self.assertTrue(ids, "Fixture must contain IDs")
        self.assertNotIn("", ids, "Empty xml:id")
        self.assertEqual(
            [key for key, count in Counter(ids).items() if count > 1], [],
            "Duplicate xml:ids",
        )
        xrefs = self.root.findall(".//xref")
        self.assertTrue(xrefs, "Fixture must exercise internal cross-references")
        for xref in xrefs:
            self.assertIn(xref.get("ref"), self.by_id, f"Unresolved xref: {xref.attrib}")
        for key, tag in {
            "matrix-mult-eg-mult1": "example",
            "systems-eqns-example1b": "example",
            "dimension-defn-basis": "definition",
            "mpp-eg1": "example",
            "det-defn-linear-prop": "proposition",
            "linindep-not-any": "warning",
        }.items():
            self.assertIn(key, self.by_id, f"Missing retained legacy ID {key}")
            self.assertEqual(self.by_id[key].tag, tag)

    def test_demo_urls(self):
        demos = self.root.findall(".//interactive")
        self.assertEqual(len(demos), 3, "Expected exactly three local demos")
        expected = {
            "pilot-vector": ("demos/vector.html", {}),
            "pilot-rowred1": ("demos/rowred1.html", {}),
            "pilot-compose3d": ("demos/compose3d.html", {
                "mat2": ["1,1,0:0,1,1"], "mat1": ["1,0:0,1:1,0"],
                "rangeT": ["off"], "rangeU": ["off"], "rangeTU": ["off"],
                "range": ["5"], "closed": ["true"],
            }),
        }
        self.assertEqual({el.get(XML_ID) for el in demos}, set(expected))
        self.assertEqual(self.root.find("docinfo/directories").get("external"), "external")
        for demo in demos:
            with self.subTest(demo=demo.get(XML_ID)):
                url = urlsplit(demo.get("iframe"))
                path, query = expected[demo.get(XML_ID)]
                self.assertEqual((url.scheme, url.netloc, url.fragment), ("", "", ""))
                self.assertEqual(url.path, path)
                self.assertEqual(parse_qs(url.query, keep_blank_values=True, strict_parsing=True), query)
                self.assertTrue(demo.findtext("shortdescription", "").strip())

    def test_all_table_rows(self):
        table = self.by_id["pilot-four-subspaces"].find("tabular")
        self.assertEqual(len(table.findall("col")), 6)
        self.assertEqual([col.get("width") for col in table.findall("col")],
                         ["23%", "10%", "14%", "12%", "23%", "18%"])
        self.assertEqual(len(table.findall("row/cell/line")), 10)
        rows = table.findall("row")
        expected = [
            ["Subspace", "of", "row/col", "dim", "basis", "changed by row ops?"],
            [r"\operatorname{Col}(A)", r"\mathbb{R}^m", "col", "r", "pivot cols of A", "yes"],
            [r"\operatorname{Nul}(A)", r"\mathbb{R}^n", "row", "n-r", "vectors in PVF", "no"],
            [r"\operatorname{Row}(A)", r"\mathbb{R}^n", "row", "r", "nonzero rows of REF", "no"],
            [r"\operatorname{Nul}(A^T)", r"\mathbb{R}^m", "col", "m-r", "last m-r rows of E", "yes"],
        ]
        self.assertEqual(len(rows), len(expected), "Header and all four subspaces required")
        for index, (row, values) in enumerate(zip(rows, expected)):
            with self.subTest(row=index):
                cells = row.findall("cell")
                self.assertEqual(len(cells), 6, "Each row must have six cells")
                self.assertEqual([" ".join("".join(cell.itertext()).split()) for cell in cells], values)

    def test_disclosure_source_contract(self):
        self.assertEqual(self.by_id["pilot-multilinearity"].tag, "paragraphs")
        prop = self.by_id["pilot-multilinearity"].find("proposition")
        self.assertEqual(prop.get(XML_ID), "det-defn-linear-prop")
        self.assertEqual(prop.find("proof").get(XML_ID), "pilot-multilinearity-proof")
        self.assertEqual(self.by_id["pilot-product-invertible"].find("proof").get(XML_ID),
                         "pilot-product-invertible-proof")
        for el in self.root.iter():
            self.assertNotIn("visible", el.attrib)
            self.assertNotIn("hide-type", el.attrib)
        self.assertEqual(self.root.findall(".//me"), [])
        self.assertEqual(len(self.root.findall(".//p/ol")), len(self.root.findall(".//ol")))

    def test_composition_displays(self):
        self.assertEqual([el.text for el in self.by_id["pilot-composition-demo"].findall("p/md")], [
            "U(a,b)=(a,b,a),", "T(x,y,z)=(x+y,y+z),", r"(T\circ U)(a,b)=(a+b,a+b).",
        ])

    def test_shared_tikz_and_reflection_semantics(self):
        preamble = self.root.findtext("docinfo/latex-image-preamble")
        self.assertEqual(preamble.count(r"\newcommand{\pilotreflection}[3]"), 1)
        self.assertIn(r"\begin{scope}", preamble)
        self.assertIn(r"\end{scope}", preamble)
        example = self.by_id["pilot-reflection-steps"]
        images = example.findall("image")
        self.assertEqual(len(images), 3)
        reflection = sp.diag(1, 1, -1)
        projection = sp.diag(0, 1, 1)
        for i, image in enumerate(images):
            self.assertEqual(image.get(XML_ID), f"pilot-reflection-e{i + 1}")
            self.assertTrue(image.findtext("shortdescription").strip())
            match = re.fullmatch(r"\\pilotreflection\{([123])\}\{([^}]+)\}\{([^}]+)\}",
                                 image.findtext("latex-image"))
            self.assertIsNotNone(match)
            self.assertEqual(int(match[1]), i + 1)
            before, after = [sp.Matrix([int(x) for x in match[j].split(",")]) for j in (2, 3)]
            self.assertEqual(before, sp.eye(3)[:, i])
            self.assertEqual(after, reflection * before)
        displays = [el.text.strip() for el in example.findall("p/md")]
        self.assertEqual(displays[:3], ["U(x,y,z)=(x,y,-z),", "T(x,y,z)=(0,y,z),",
                                       r"S(x,y,z)=(T\circ U)(x,y,z)=(0,y,-z)."])
        expected_chains = [
            r"U(e_1)=e_1=\begin{pmatrix}1\\0\\0\end{pmatrix},\qquad T(e_1)=S(e_1)=\begin{pmatrix}0\\0\\0\end{pmatrix}.",
            r"U(e_2)=T(e_2)=S(e_2)=e_2=\begin{pmatrix}0\\1\\0\end{pmatrix}.",
            r"U(e_3)=S(e_3)=-e_3=\begin{pmatrix}0\\0\\-1\end{pmatrix},\qquad T(e_3)=e_3=\begin{pmatrix}0\\0\\1\end{pmatrix}.",
        ]
        self.assertEqual(displays[3:6], expected_chains)
        bodies = re.findall(r"\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}", " ".join(displays[6:]))
        self.assertEqual([matrix(body) for body in bodies], [reflection, projection, projection * reflection])

    def test_multilinearity_proof(self):
        proof = self.by_id["pilot-multilinearity-proof"]
        self.assertIn("Editorial shortened proof", "".join(proof.itertext()))
        self.assertEqual([el.text.strip() for el in proof.findall("p/md")], [
            r"T(x)=\sum_{j=1}^n x_j C_{ij}.",
            r"T(v+w)=\sum_{j=1}^n(v_j+w_j)C_{ij}=T(v)+T(w),",
            r"T(cx)=\sum_{j=1}^n c x_j C_{ij}=cT(x).",
        ])
        # Check both identities for every variable row, including the empty-minor case.
        c = sp.Symbol("c")
        for n in (1, 2, 3):
            fixed = sp.Matrix(n, n, sp.symbols(f"a0:{n*n}"))
            v = sp.Matrix(1, n, sp.symbols(f"v0:{n}"))
            w = sp.Matrix(1, n, sp.symbols(f"w0:{n}"))
            for i in range(n):
                determinants = []
                for row in (v, w, v + w, c * v):
                    current = fixed.copy()
                    current[i, :] = row
                    determinants.append(current.det())
                dv, dw, dsum, dscale = determinants
                self.assertEqual(sp.expand(dsum - dv - dw), 0)
                self.assertEqual(sp.expand(dscale - c * dv), 0)

    def test_visible_proof_and_warning_content(self):
        proof = self.by_id["pilot-product-invertible-proof"]
        self.assertEqual(proof.findtext("p/md").strip(),
                         r"\det(A_1A_2\cdots A_k)=\det(A_1)\det(A_2)\cdots\det(A_k).")
        self.assertIn("each factor determinant is nonzero", "".join(proof.itertext()))
        warning = "".join(self.by_id["linindep-not-any"].itertext())
        self.assertIn("at least one", warning)
        self.assertIn(r"\{(1,0),(2,0),(0,1)\}", warning)
        self.assertIn("2(1,0)-(2,0)=(0,0)", warning)
        self.assertIn("has second coordinate zero", warning)
        vectors = sp.Matrix([[1, 2, 0], [0, 0, 1]])
        self.assertLess(vectors.rank(), vectors.cols)
        self.assertEqual(vectors[:, :2].rank(), 1)
        self.assertEqual(vectors.rank(), 2)

    def test_nested_product(self):
        text = self.by_id["matrix-mult-eg-mult1"].findtext(".//md")
        values = {}
        # Reduce innermost matrices first, assembling block columns from their values.
        pattern = re.compile(r"\\begin\{pmatrix\}((?:(?!\\begin\{pmatrix\}).)*?)\\end\{pmatrix\}", re.S)
        while match := pattern.search(text):
            body = match[1]
            if "@" not in body:
                value = matrix(body)
            else:
                block_rows = []
                for row in body.strip().split(r"\\"):
                    blocks = []
                    for cell in row.split("&"):
                        tokens = re.findall(r"@\d+@", cell)
                        self.assertTrue(tokens, f"Empty block in {body}")
                        self.assertEqual(re.sub(r"@\d+@", "", cell).strip(), "", f"Unsupported block: {cell}")
                        product = values[tokens[0]]
                        for token in tokens[1:]:
                            product = product * values[token]
                        blocks.append(product)
                    block_rows.append(sp.Matrix.hstack(*blocks))
                value = sp.Matrix.vstack(*block_rows)
            token = f"@{len(values)}@"
            values[token] = value
            text = text[:match.start()] + token + text[match.end():]
        self.assertNotIn("pmatrix", text, "Unparsed matrix markup")
        stages = text.split("=")
        self.assertEqual(len(stages), 4, "Expected factors, column products, columns, result")
        for index, stage in enumerate(stages):
            remainder = re.sub(r"@\d+@", "", stage)
            for markup in (r"\begin{aligned}", r"\end{aligned}", r"\\", "&"):
                remainder = remainder.replace(markup, "")
            self.assertEqual(re.sub(r"\s+", "", remainder), "." if index == 3 else "",
                             "Unexpected operator or syntax outside displayed matrices")
        tokens = [re.findall(r"@\d+@", stage) for stage in stages]
        self.assertEqual([len(stage) for stage in tokens], [2, 1, 1, 1])
        left, right = (values[token] for token in tokens[0])
        for index, stage in enumerate(tokens[1:], 1):
            self.assertEqual(values[stage[0]], left * right, f"Incorrect nested product stage {index}")
        query = parse_qs(urlsplit(self.by_id["pilot-compose3d"].get("iframe")).query)
        for key, factor in (("mat2", left), ("mat1", right)):
            self.assertEqual(matrix(query[key][0].replace(":", r"\\").replace(",", "&")), factor,
                             f"Demo {key} disagrees with displayed factor")

    def test_nested_product_rejects_wrong_sign(self):
        display = self.by_id["matrix-mult-eg-mult1"].find(".//md")
        original = display.text
        try:
            display.text = original.replace(r"=\begin{pmatrix}1&1", r"=-\begin{pmatrix}1&1")
            self.assertNotEqual(display.text, original)
            with self.assertRaises(AssertionError):
                self.test_nested_product()
        finally:
            display.text = original

    def test_row_operation_chain(self):
        example = self.by_id["systems-eqns-example1b"]
        text = "\n".join(el.text for el in example.findall("solution/p/md"))
        arrays = re.findall(r"\\begin\{array\}\{ccc\|c\}(.*?)\\end\{array\}", text, re.S)
        operations = re.findall(r"\\xrightarrow\{([^{}]+)\}", text)
        self.assertEqual(len(arrays), 7, "Expected initial matrix and six resulting matrices")
        self.assertEqual(len(operations), 6, "Expected six labeled row operations")
        matrices = [matrix(body) for body in arrays]
        for index, operation in enumerate(operations):
            with self.subTest(step=index + 1, operation=operation):
                current = matrices[index].copy()
                if match := re.fullmatch(r"R_(\d)\\leftarrow R_\1([+-]\d+)R_(\d)", operation):
                    target, scale, source = map(int, match.groups())
                    current[target - 1, :] += scale * current[source - 1, :]
                elif match := re.fullmatch(r"R_(\d)\\leftarrow R_\1/\(?(-?\d+)\)?", operation):
                    target, divisor = map(int, match.groups())
                    self.assertNotEqual(divisor, 0, "Row scaling must be invertible")
                    current[target - 1, :] /= divisor
                elif match := re.fullmatch(r"R_(\d)\\leftrightarrow R_(\d)", operation):
                    first, second = map(int, match.groups())
                    current.row_swap(first - 1, second - 1)
                else:
                    self.fail(f"Unsupported row-operation label: {operation}")
                self.assertEqual(current, matrices[index + 1], "Displayed matrix does not follow its arrow")
        x, y, z = sp.symbols("x y z")
        system = example.findtext("statement/p/md")
        equations = re.search(r"\\begin\{aligned\}(.*?)\\end\{aligned\}", system)[1]
        residuals = []
        for equation in equations.split(r"\\"):
            lhs, rhs = equation.rstrip(".").split("&=")
            lhs = re.sub(r"(\d)([xyz])", r"\1*\2", lhs)
            residuals.append(sp.sympify(lhs) - sp.sympify(rhs))
        coefficients, rhs = sp.linear_eq_to_matrix(residuals, (x, y, z))
        self.assertEqual(coefficients.row_join(rhs), matrices[0], "Augmented matrix disagrees with stated system")
        answers = [el.text for el in example.findall("solution/p/m") if el.text.startswith("(x,y,z)=")]
        self.assertEqual(len(answers), 1, "Expected one stated solution triple")
        answer = sp.Matrix([sp.Rational(v) for v in answers[0].split("=(")[1].rstrip(")").split(",")])
        self.assertEqual(coefficients * answer, rhs, "Stated answer does not solve original system")
        self.assertEqual(matrices[-1][:, :3] * answer, matrices[-1][:, 3])

    def test_static_sympy_output(self):
        self.assertEqual(sp.__version__, "1.14.0", "Run with the pinned phase1 SymPy environment")
        program = self.by_id["pilot-floating-point-program"]
        self.assertEqual(program.get("language"), "python")
        self.assertEqual(program.get("interactive"), "no")
        code = program.findtext("code")
        self.assertTrue(code and code.strip(), "Missing static Python listing")
        # -I ignores user Python paths; a fresh cwd and timeout contain execution.
        # This executes trusted repository code, not a security sandbox.
        with tempfile.TemporaryDirectory(prefix="ila-fixture-") as cwd:
            try:
                result = subprocess.run(
                    [sys.executable, "-I", "-c", code], cwd=cwd,
                    capture_output=True, text=True, encoding="utf-8", timeout=15,
                )
            except subprocess.TimeoutExpired:
                self.fail("Static SymPy listing exceeded the 15-second timeout")
        self.assertEqual(result.returncode, 0, f"Static listing failed:\n{result.stderr}")
        self.assertEqual(result.stderr, "", "Unexpected diagnostics from static listing")
        expected = (
            "\u23a11.0e-17    1.0       1.0   \u23a4\n"
            "\u23a2                           \u23a5\n"
            "\u23a3   0     -1.0e+17  -1.0e+17\u23a6\n"
            "\u23a11  0   0 \u23a4\n"
            "\u23a2         \u23a5\n"
            "\u23a30  1  1.0\u23a6\n"
        )
        self.assertEqual(result.stdout, expected, "SymPy 1.14.0 output changed; review the explanatory prose")


if __name__ == "__main__":
    unittest.main()
