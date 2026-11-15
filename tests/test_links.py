import json
import shutil
import tempfile
import unittest
from pathlib import Path

from repomap import links as L
from repomap.notes import components, fingerprint


def model():
    return {"files": [{"path": "a/x.py", "kind": "code"}],
            "symbols": [{"id": "sym:f", "name": "f()", "file": "a/x.py", "parent": "a/x.py", "loc": "L1", "kind": "func"}],
            "external": [], "edges": []}


def merged(nodes, edges):
    m = model()
    links = {"nodes": nodes, "edges": edges}
    res = L.merge_links(m, links, L.link_components(links, components(m)))
    return m, res


class LinksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_load_missing_returns_empty(self):
        self.assertEqual(L.load_links(self.tmp / "x.json"), {"nodes": {}, "edges": []})

    def test_save_load_roundtrip(self):
        p = self.tmp / "out" / "links.json"
        links = {"nodes": {"SSD": {"kind": "concept"}},
                 "edges": [{"src": "b", "rel": "reads", "tgt": "SSD"}, {"src": "a", "rel": "calls", "tgt": "SSD"}]}
        L.save_links(p, links)
        got = L.load_links(p)
        self.assertEqual(got["nodes"], links["nodes"])
        self.assertEqual([e["src"] for e in got["edges"]], ["a", "b"])
        self.assertTrue(p.read_text().endswith("\n"))
        self.assertEqual(p.stat().st_mode & 0o777, 0o644)

    def test_load_bad_shape(self):
        p = self.tmp / "l.json"
        for text in ('{"version":1}', "[1]", "{"):
            p.write_text(text)
            with self.assertRaises(ValueError):
                L.load_links(p)

    def test_merge_runtime_file_and_concept(self):
        m, res = merged({"out/map.html": {"kind": "file"}, "SSD": {"kind": "concept"}},
                        [{"src": "a/x.py", "rel": "creates", "tgt": "out/map.html"},
                         {"src": "a/x.py", "rel": "reads", "tgt": "SSD"}])
        f = [f for f in m["files"] if f["path"] == "out/map.html"]
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0]["manual"])
        self.assertEqual(m["concepts"], [{"id": "concept:SSD", "label": "SSD"}])
        tgts = {e["tgt"]: e for e in m["edges"]}
        self.assertEqual(tgts["out/map.html"]["src"], "a/x.py")
        self.assertEqual(tgts["concept:SSD"]["manual_count"], 1)
        self.assertEqual(tgts["out/map.html"]["manual_count"], 1)
        self.assertEqual(res, {"missing": [], "found": []})

    def test_merge_missing_end(self):
        m, res = merged({}, [{"src": "a/x.py", "rel": "calls", "tgt": "a/gone.py"}])
        self.assertEqual(m["edges"], [])
        self.assertEqual(res["missing"], ["a/x.py calls a/gone.py"])

    def test_concept_shadowed(self):
        m, res = merged({"a": {"kind": "concept"}}, [])
        self.assertEqual(m["concepts"], [])
        self.assertEqual(res["found"], ["a"])

    def test_folder_note_not_stale_after_runtime_file(self):
        comps = components(model())
        before = fingerprint(comps["a"], comps, self.tmp)
        ext = L.link_components({"nodes": {"a/out.html": {"kind": "file"}}, "edges": []}, comps)
        self.assertIn("a/out.html", ext)
        self.assertIsNone(fingerprint(ext["a/out.html"], ext, self.tmp))
        self.assertEqual(fingerprint(ext["a"], ext, self.tmp), before)

    def test_merge_found_by_graphify(self):
        m, res = merged({"a/x.py": {"kind": "file"}}, [])
        self.assertEqual(res["found"], ["a/x.py"])
        self.assertEqual([f["path"] for f in m["files"]], ["a/x.py"])

    def test_symbol_and_folder_ends_kept(self):
        m, _ = merged({}, [{"src": "a/x.py::f", "rel": "calls", "tgt": "a/x.py"},
                           {"src": "a", "rel": "reads", "tgt": "a/x.py"}])
        self.assertEqual(sorted(e["src"] for e in m["edges"]), ["a/", "sym:f"])


if __name__ == "__main__":
    unittest.main()
