import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from repomap import notes as N
from repomap.load import load_graph
from repomap.model import build_model

FIX = Path(__file__).parent / "fixtures" / "notes_proj"


class NotesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "proj"
        shutil.copytree(FIX, self.root)
        self.model = build_model(*load_graph(self.root / "graphify-out" / "graph.json"))
        self.comps = N.components(self.model)

    def fp(self, name):
        return N.fingerprint(self.comps[name], self.comps, self.root)

    def edit(self, rel, old, new):
        p = self.root / rel
        p.write_text(p.read_text().replace(old, new))

    def test_ids(self):
        c = self.comps
        for k in ("app", "app/db", "app/db/store.py", "app/models.py::User", "app/models.py::User.display", "README.md"):
            self.assertIn(k, c)
        self.assertNotIn("", c)
        self.assertEqual(c["app/db"]["box"], "app/db/")
        self.assertEqual(c["app/db/store.py::save"]["box"], "sym:sv")

    def test_duplicate_names_get_line_suffix(self):
        self.assertIn("app/dup.py::helper@L1", self.comps)
        self.assertIn("app/dup.py::helper@L4", self.comps)
        self.assertNotIn("app/dup.py::helper", self.comps)
        with self.assertRaisesRegex(KeyError, "ambiguous: use one of app/dup.py::helper@L1"):
            N.resolve("app/dup.py::helper", self.comps)
        with self.assertRaisesRegex(KeyError, "is not on the map"):
            N.resolve("app/nope.py", self.comps)
        self.assertEqual(N.resolve("app/db/", self.comps), "app/db")

    def test_class_range_covers_methods(self):
        self.assertEqual(self.comps["app/models.py::User"]["end"], 9)
        self.assertEqual(self.comps["app/models.py::User.__init__"]["end"], 5)
        self.assertIsNone(self.comps["app/models.py::make_user"]["end"])

    def test_fingerprints_change(self):
        before = {k: self.fp(k) for k in ("app/models.py::User", "app/models.py::User.display", "app/db/store.py::save")}
        self.edit("app/models.py", "title()", "upper()")
        self.assertNotEqual(self.fp("app/models.py::User"), before["app/models.py::User"])
        self.assertNotEqual(self.fp("app/models.py::User.display"), before["app/models.py::User.display"])
        self.assertEqual(self.fp("app/db/store.py::save"), before["app/db/store.py::save"])

    def test_dir_changes_on_any_inner_edit(self):
        a, db, m = self.fp("app"), self.fp("app/db"), self.fp("app/models.py")
        self.edit("app/db/store.py", "dumps", "dump")
        self.assertNotEqual(self.fp("app"), a)
        self.assertNotEqual(self.fp("app/db"), db)
        self.assertEqual(self.fp("app/models.py"), m)

    def test_symbol_unaffected_by_other_symbol(self):
        ld = self.fp("app/db/store.py::load")
        self.edit("app/db/store.py", "json.dumps(u)", "json.dumps(u, indent=1)")
        self.assertEqual(self.fp("app/db/store.py::load"), ld)

    def test_missing_source_is_stale(self):
        notes = {"app/db/store.py::save": {"text": "x", "hash": self.fp("app/db/store.py::save"), "updated": "2026-11-15"}}
        (self.root / "app/db/store.py").unlink()
        self.assertIsNone(self.fp("app/db/store.py::save"))
        self.assertIsNotNone(self.fp("app/db"))
        view, missing = N.note_view(notes, self.comps, self.root)
        self.assertTrue(view["sym:sv"]["stale"])
        self.assertEqual(missing, [])

    def test_view_lists_missing(self):
        notes = {"app/old.py": {"text": "o", "hash": None, "updated": "2026-11-15"},
                 "app": {"text": "A", "hash": self.fp("app"), "updated": "2026-11-15"}}
        view, missing = N.note_view(notes, self.comps, self.root)
        self.assertEqual(missing, ["app/old.py"])
        self.assertEqual(view, {"app/": {"name": "app", "text": "A", "stale": False}})

    def test_save_is_atomic(self):
        path = self.root / "repomap-out" / "notes.json"
        N.save_notes(path, {"a": {"text": "old", "hash": None, "updated": "x"}})
        old = path.read_text()
        self.assertTrue(old.endswith("\n"))

        def boom(obj, f, **kw):
            f.write('{"version": 1, "no')
            raise OSError("disk full")
        with mock.patch("repomap.notes.json.dump", boom), self.assertRaises(OSError):
            N.save_notes(path, {"a": {"text": "new", "hash": None, "updated": "x"}})
        self.assertEqual(path.read_text(), old)
        self.assertEqual([p.name for p in path.parent.iterdir()], ["notes.json"])

    def test_load_bad_json(self):
        p = self.tmp / "n.json"
        self.assertEqual(N.load_notes(p), {})
        for text in ("{oops", "[]", '{"notes": []}'):
            p.write_text(text)
            with self.assertRaises(ValueError):
                N.load_notes(p)
        p.write_text(json.dumps({"version": 1, "notes": {"a": {"text": "t"}}}))
        self.assertEqual(N.load_notes(p), {"a": {"text": "t"}})

    def test_annotate_sets_ref(self):
        N.annotate(self.model, self.comps)
        refs = {s["id"]: s["ref"] for s in self.model["symbols"]}
        self.assertEqual(refs["sym:Ud"], "app/models.py::User.display")
        self.assertEqual(refs["sym:h2"], "app/dup.py::helper@L4")


if __name__ == "__main__":
    unittest.main()
