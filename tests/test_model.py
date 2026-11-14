import unittest
from pathlib import Path

from repomap.load import load_graph
from repomap.model import build_model, classify

FIXTURE = Path(__file__).parent / "fixtures" / "mini_graph.json"


def m():
    return build_model(*load_graph(FIXTURE))


class TestModel(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("tests/fixtures/x.go"), "test")
        self.assertEqual(classify("src/foo.spec.ts"), "test")
        self.assertEqual(classify("pkg/test_x.py"), "test")
        self.assertEqual(classify("pkg/x_test.go"), "test")
        self.assertEqual(classify("tests/data.json"), "test")
        self.assertEqual(classify("README.md"), "doc")
        self.assertEqual(classify("pkg/a.py"), "code")

    def test_counts_merge_relations(self):
        e = {(x["src"], x["tgt"]): x for x in m()["edges"]}
        self.assertEqual(e[("pkg/a.py", "pkg/sub/b.py")]["count"], 2)
        self.assertEqual(e[("pkg/a.py", "lib/c.py")]["by_rel"], {"imports_from": 1})
        self.assertIn(("lib/c.py", "pkg/sub/b.py"), e)
        s = e[("pkg/a.py", "lib/c.py")]["samples"][0]
        self.assertEqual(s, {"from": "a1()", "to": "c1()", "rel": "imports_from", "loc": "pkg/a.py:L1"})

    def test_ignored(self):
        e = {(x["src"], x["tgt"]) for x in m()["edges"]}
        self.assertNotIn(("pkg/a.py", "pkg/a.py"), e)
        self.assertNotIn(("README.md", "pkg/a.py"), e)

    def test_external_and_lonely(self):
        model = m()
        self.assertIn({"id": "ext:Path", "label": "Path"}, model["external"])
        self.assertIn(("pkg/a.py", "ext:Path"), {(x["src"], x["tgt"]) for x in model["edges"]})
        self.assertIn("pkg/lone.py", [f["path"] for f in model["files"]])
        self.assertEqual([f["path"] for f in model["files"]], sorted(f["path"] for f in model["files"]))


if __name__ == "__main__":
    unittest.main()
