import unittest
from pathlib import Path

from repomap.load import load_graph
from repomap.model import build_model, classify

FIXTURE = Path(__file__).parent / "fixtures" / "mini_graph.json"
SYM = Path(__file__).parent / "fixtures" / "sym_graph.json"


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


def ms():
    return build_model(*load_graph(SYM))


class TestSymbols(unittest.TestCase):
    def test_symbols(self):
        s = {x["id"]: x for x in ms()["symbols"]}
        self.assertEqual(set(s), {"sym:run", "sym:K", "sym:km", "sym:g", "sym:t1"})
        self.assertEqual(s["sym:km"]["parent"], "sym:K")
        self.assertEqual(s["sym:run"]["parent"], "pkg/a.py")
        self.assertEqual((s["sym:K"]["kind"], s["sym:run"]["kind"]), ("class", "func"))
        self.assertEqual(s["sym:run"]["loc"], "L3")

    def test_endpoints(self):
        e = {(x["src"], x["tgt"]): x for x in ms()["edges"]}
        self.assertIn(("sym:run", "sym:g"), e)
        self.assertEqual(e[("sym:run", "sym:g")]["by_rel"], {"calls": 1})      # indirect_call bỏ
        self.assertIn(("sym:km", "sym:g"), e)
        self.assertIn(("sym:run", "sym:km"), e)                                # cùng file, khác ký hiệu
        self.assertIn(("pkg/a.py", "pkg/b.py"), e)                             # import ở cấp file
        self.assertIn(("pkg/a.py", "sym:g"), e)                                # cấp module → hàm

    def test_v1_fixture_unchanged(self):
        self.assertEqual(m()["symbols"], [])   # mini_graph không có contains cùng file

    def test_doc_files_have_no_symbols(self):
        nodes = {"f": {"source_file": "conf.json", "file_type": "code"},
                 "k": {"source_file": "conf.json", "file_type": "code", "label": "key"},
                 "F": {"source_file": "a.py", "file_type": "code"},
                 "g": {"source_file": "a.py", "file_type": "code", "label": "g()"}}
        links = [{"src": "f", "tgt": "k", "relation": "contains"},
                 {"src": "F", "tgt": "g", "relation": "contains"}]
        self.assertEqual([s["id"] for s in build_model(nodes, links)["symbols"]], ["sym:g"])

    def test_contains_cycle_attaches_to_file(self):
        n = lambda: {"source_file": "a.py", "file_type": "code"}
        nodes = {"x": n(), "y": n(), "z": n()}
        links = [{"src": "x", "tgt": "y", "relation": "contains"},
                 {"src": "y", "tgt": "x", "relation": "contains"},
                 {"src": "z", "tgt": "z", "relation": "contains"}]
        par = {s["id"]: s["parent"] for s in build_model(nodes, links)["symbols"]}
        self.assertEqual(par["sym:z"], "a.py")
        self.assertIn("a.py", (par["sym:x"], par["sym:y"]))  # chain terminates at the file


if __name__ == "__main__":
    unittest.main()
