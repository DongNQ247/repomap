import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "tests" / "fixtures" / "sym_graph.json"
NOTES_PROJ = ROOT / "tests" / "fixtures" / "notes_proj"


def run(args, cwd, env=None):
    env = {**os.environ, "PYTHONPATH": str(ROOT), **(env or {})}
    return subprocess.run([sys.executable, "-m", "repomap", *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


class CliTest(unittest.TestCase):
    def test_version(self):
        r = run(["--version"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "repomap 1.1.4")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def project(self, name="proj", text=None):
        proj = self.tmp / name
        (proj / "graphify-out").mkdir(parents=True)
        g = proj / "graphify-out" / "graph.json"
        if text is None:
            shutil.copy(SAMPLE, g)
        else:
            g.write_text(text)
        return proj

    def test_default_finds_graphify_out(self):
        proj = self.project()
        r = run([], cwd=proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((proj / "repomap-out" / "map.html").exists())
        self.assertIn("repomap 1.1.4 - reading graphify-out/graph.json", r.stdout)
        self.assertRegex(r.stdout, r"\d+ files - \d+ symbols - \d+ arrows")
        self.assertIn("OK wrote repomap-out/map.html (", r.stdout)
        self.assertIn("file://", r.stdout)
        self.assertNotIn("\033[", r.stdout)

    def test_missing_graph_gives_guide(self):
        r = run([], cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"graphify-out/graph.json not found in {self.tmp.resolve()}", r.stderr)
        self.assertIn("uv tool install graphifyy", r.stderr)
        self.assertIn("graphify update .", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_dir_without_graph_names_tried_path(self):
        (self.tmp / "empty").mkdir()
        r = run(["empty"], cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("empty/graph.json not found", r.stderr)
        self.assertIn("uv tool install graphifyy", r.stderr)

    def test_style_respects_tty_and_no_color(self):
        from unittest import mock
        from repomap.__main__ import style

        class Tty:
            def __init__(self, tty): self.tty = tty
            def isatty(self): return self.tty

        env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(style(Tty(True)))
            self.assertFalse(style(Tty(False)))
        for val, want in (("", True), ("1", False)):
            with mock.patch.dict(os.environ, {"NO_COLOR": val}):
                self.assertEqual(style(Tty(True)), want)

    def test_path_dir_and_file(self):
        proj = self.project()
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        self.assertEqual(run([str(proj)], cwd=elsewhere).returncode, 0)
        self.assertEqual(run([str(proj / "graphify-out" / "graph.json")], cwd=elsewhere).returncode, 0)
        r = run(["nope.json"], cwd=elsewhere)
        self.assertEqual(r.returncode, 1)
        self.assertIn("repomap: error: nope.json not found", r.stderr)
        self.assertIn("uv tool install graphifyy", r.stderr)

    def test_bad_json_and_wrong_shape(self):
        cases = [("{oops", "is not valid JSON"), ("[]", "does not look like a graphify graph.json"),
                 ("{}", "does not look like a graphify graph.json")]
        for i, (text, msg) in enumerate(cases):
            r = run([], cwd=self.project(f"bad{i}", text))
            self.assertEqual(r.returncode, 1)
            self.assertIn(msg, r.stderr)
            self.assertEqual(len(r.stderr.strip().splitlines()), 1)
            self.assertNotIn("Traceback", r.stderr)

    def test_quiet(self):
        proj = self.project()
        r = run(["-q"], cwd=proj)
        self.assertEqual(r.stdout.strip(), str((proj / "repomap-out" / "map.html").resolve()))

    def test_space_in_path(self):
        r = run([], cwd=self.project("my project"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("my%20project", r.stdout)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores permissions")
    def test_unwritable_out(self):
        proj = self.project()
        ro = self.tmp / "ro"
        ro.mkdir()
        os.chmod(ro, 0o500)
        self.addCleanup(os.chmod, ro, 0o700)
        r = run(["-o", str(ro / "map.html")], cwd=proj)
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot write", r.stderr)

    def test_bad_args_exit_2(self):
        self.assertEqual(run(["--nope"], cwd=self.tmp).returncode, 2)

    def test_skill_install(self):
        home = self.tmp / "home"
        r = run(["skill", "install"], cwd=self.tmp, env={"HOME": str(home)})
        self.assertEqual(r.returncode, 0, r.stderr)
        dst = home / ".claude" / "skills" / "repomap" / "SKILL.md"
        self.assertIn(f"OK installed Claude Code skill: {dst}", r.stdout)
        self.assertTrue(dst.read_text().startswith("---\nname: repomap\n"))
        self.assertIn("repomap note add", dst.read_text())
        self.assertEqual(run(["skill", "install"], cwd=self.tmp, env={"HOME": str(home)}).returncode, 0)

    def test_skill_bad_args(self):
        self.assertEqual(run(["skill"], cwd=self.tmp).returncode, 2)


class NoteCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.proj = self.tmp / "proj"
        shutil.copytree(NOTES_PROJ, self.proj)

    def notes(self):
        return json.loads((self.proj / "repomap-out" / "notes.json").read_text())["notes"]

    def test_default_writes_repomap_out(self):
        proj = self.proj
        r = run([], cwd=proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((proj / "repomap-out" / "map.html").exists())
        self.assertFalse((proj / "graphify-out" / "map.html").exists())
        self.assertIn("OK wrote repomap-out/map.html (", r.stdout)
        self.assertNotIn("notes", r.stdout)

    def test_note_add_render_delete(self):
        proj = self.proj
        r = run(["note", "add", "app/db/store.py", "Saves users\nas JSON"], cwd=proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK saved note for app/db/store.py", r.stdout)
        self.assertEqual(self.notes()["app/db/store.py"]["text"], "Saves users\nas JSON")
        r = run([], cwd=proj)
        self.assertIn("1 notes", r.stdout)
        self.assertNotIn("outdated", r.stdout)
        self.assertIn("Saves users", (proj / "repomap-out" / "map.html").read_text())
        r = run(["note", "delete", "app/db/store.py"], cwd=proj)
        self.assertEqual(r.returncode, 0)
        self.assertIn("OK deleted note for app/db/store.py", r.stdout)
        r = run(["note", "delete", "app/db/store.py"], cwd=proj)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no note for app/db/store.py", r.stderr)

    def test_add_replaces(self):
        run(["note", "add", "app", "one"], cwd=self.proj)
        run(["note", "add", "app/", "two"], cwd=self.proj)
        self.assertEqual({k: v["text"] for k, v in self.notes().items()}, {"app": "two"})

    def test_unknown_component(self):
        r = run(["note", "add", "app/nope.py", "x"], cwd=self.proj)
        self.assertEqual(r.returncode, 1)
        self.assertIn("app/nope.py is not on the map", r.stderr)
        self.assertFalse((self.proj / "repomap-out" / "notes.json").exists())
        r = run(["note", "add", "app/dup.py::helper", "x"], cwd=self.proj)
        self.assertIn("ambiguous: use one of app/dup.py::helper@L1, app/dup.py::helper@L4", r.stderr)

    def test_stale_then_ok(self):
        proj = self.proj
        run(["note", "add", "app/db/store.py::save", "x"], cwd=proj)
        p = proj / "app" / "db" / "store.py"
        p.write_text(p.read_text().replace("dumps(u)", "dumps(u, indent=2)"))
        self.assertIn("1 notes - 1 may be outdated", run([], cwd=proj).stdout)
        r = run(["note", "ok", "app/db/store.py::save"], cwd=proj)
        self.assertEqual(r.returncode, 0)
        self.assertIn("OK marked note for app/db/store.py::save as up to date", r.stdout)
        self.assertNotIn("outdated", run([], cwd=proj).stdout)
        self.assertEqual(run(["note", "ok", "app"], cwd=proj).returncode, 1)

    def test_missing_component_listed_not_deleted(self):
        run(["note", "add", "app", "A"], cwd=self.proj)
        path = self.proj / "repomap-out" / "notes.json"
        d = json.loads(path.read_text())
        d["notes"]["app/old.py"] = {"text": "gone", "hash": None, "updated": "2026-01-01"}
        path.write_text(json.dumps(d))
        r = run([], cwd=self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 notes point to missing components: app/old.py", r.stdout)
        self.assertIn("app/old.py", self.notes())
        r = run(["note", "delete", "app/old.py"], cwd=self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("app/old.py", self.notes())
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_note_from_subfolder(self):
        r = run(["note", "add", "app/models.py::User", "The user"], cwd=self.proj / "app" / "db")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("app/models.py::User", self.notes())
        self.assertFalse((self.proj / "app" / "db" / "repomap-out").exists())

    def test_note_outside_project(self):
        r = run(["note", "add", "x", "y"], cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("or any parent folder", r.stderr)
        self.assertIn("graphify update .", r.stderr)

    def test_bad_notes_json(self):
        path = self.proj / "repomap-out" / "notes.json"
        path.parent.mkdir()
        path.write_text("{oops")
        for args in ([], ["note", "add", "app", "x"]):
            r = run(args, cwd=self.proj)
            self.assertEqual(r.returncode, 1)
            self.assertIn("repomap-out/notes.json is not valid JSON", r.stderr)
            self.assertEqual(len(r.stderr.strip().splitlines()), 1)
            self.assertEqual(path.read_text(), "{oops")

    def test_note_text_with_script_tag(self):
        run([], cwd=self.proj)
        before = (self.proj / "repomap-out" / "map.html").read_text().count("</script>")
        run(["note", "add", "app", "</script><b>"], cwd=self.proj)
        run([], cwd=self.proj)
        html = (self.proj / "repomap-out" / "map.html").read_text()
        self.assertEqual(html.count("</script>"), before)
        self.assertEqual(html.count("</script>"), html.count("<script"))

    def test_note_bad_args_exit_2(self):
        self.assertEqual(run(["note"], cwd=self.proj).returncode, 2)
        self.assertEqual(run(["note", "add", "x"], cwd=self.proj).returncode, 2)

    def test_empty_text(self):
        r = run(["note", "add", "app", "   "], cwd=self.proj)
        self.assertEqual(r.returncode, 1)
        self.assertIn("note text is empty", r.stderr)


class LinkCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.proj = self.tmp / "proj"
        shutil.copytree(NOTES_PROJ, self.proj)
        self.path = self.proj / "repomap-out" / "links.json"

    def link(self, *args, cwd=None):
        return run(["link", *args], cwd=cwd or self.proj)

    def links(self):
        return json.loads(self.path.read_text())

    def test_link_node_and_add(self):
        r = self.link("node", "out/map.html")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK added node out/map.html", r.stdout)
        self.assertEqual(self.link("node", "SSD", "--concept").returncode, 0)
        r = self.link("add", "app/db/store.py::save", "creates", "out/map.html")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK added link app/db/store.py::save creates out/map.html", r.stdout)
        self.assertEqual(self.link("add", "app/db/", "reads", "SSD").returncode, 0)
        self.assertEqual(self.links(), {"version": 1,
            "nodes": {"SSD": {"kind": "concept"}, "out/map.html": {"kind": "file"}},
            "edges": [{"src": "app/db", "rel": "reads", "tgt": "SSD"},
                      {"src": "app/db/store.py::save", "rel": "creates", "tgt": "out/map.html"}]})

    def test_link_bad_rel_exit2(self):
        self.assertEqual(self.link("add", "app", "uses", "README.md").returncode, 2)
        self.assertEqual(self.link("delete", "a", "b").returncode, 2)

    def test_link_unknown_end_exit1(self):
        r = self.link("add", "app", "calls", "app/nope.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("app/nope.py is not on the map", r.stderr)
        self.assertFalse(self.path.exists())

    def test_link_duplicate_noop(self):
        self.link("add", "app", "calls", "README.md")
        r = self.link("add", "app", "calls", "README.md")
        self.assertEqual(r.returncode, 0)
        self.assertIn("already exists", r.stdout)
        self.assertEqual(len(self.links()["edges"]), 1)
        self.link("node", "SSD", "--concept")
        self.assertIn("already exists", self.link("node", "SSD", "--concept").stdout)

    def test_delete_edge(self):
        self.link("add", "app", "calls", "README.md")
        r = self.link("delete", "app/", "calls", "README.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK deleted", r.stdout)
        self.assertEqual(self.links()["edges"], [])
        self.assertEqual(self.link("delete", "app", "calls", "README.md").returncode, 1)

    def test_delete_edge_after_rename(self):
        self.link("add", "app", "calls", "README.md")
        d = self.links()
        d["edges"][0]["tgt"] = "app/gone.py"
        self.path.write_text(json.dumps(d))
        r = self.link("delete", "app", "calls", "app/gone.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.links()["edges"], [])

    def test_delete_node_with_edges_refused(self):
        self.link("node", "SSD", "--concept")
        self.link("add", "app", "reads", "SSD")
        before = self.path.read_bytes()
        r = self.link("delete", "SSD")
        self.assertEqual(r.returncode, 1)
        self.assertIn("SSD still has links: app reads SSD; delete them first", r.stderr)
        self.assertEqual(self.path.read_bytes(), before)
        self.link("delete", "app", "reads", "SSD")
        self.assertEqual(self.link("delete", "SSD").returncode, 0)
        self.assertEqual(self.links()["nodes"], {})

    def test_concept_name_rules(self):
        for name in ("a/b", "x::y", "app"):
            self.assertEqual(self.link("node", name, "--concept").returncode, 1, name)
        self.assertFalse(self.path.exists())

    def test_corrupt_links_json(self):
        self.path.parent.mkdir()
        self.path.write_text("{oops")
        r = self.link("node", "SSD", "--concept")
        self.assertEqual(r.returncode, 1)
        self.assertIn("repomap-out/links.json is not valid JSON", r.stderr)
        self.assertEqual(self.path.read_text(), "{oops")

    def test_link_from_subfolder(self):
        r = self.link("add", "app/models.py::User", "calls", "app/db", cwd=self.proj / "app" / "db")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.path.exists())

    def test_node_under_file_refused(self):
        self.assertEqual(self.link("node", "app/models.py/out.txt").returncode, 1)
        self.link("node", "out/a.txt")
        self.assertEqual(self.link("node", "out/a.txt/b").returncode, 1)
        self.link("node", "SSD", "--concept")
        self.assertEqual(self.link("node", "SSD/x.bin").returncode, 1)

    def test_node_trailing_slash_refused(self):
        self.assertEqual(self.link("node", "out/").returncode, 1)
        self.assertEqual(self.link("node", "app/x.py::f").returncode, 1)

    def test_self_link_refused(self):
        r = self.link("add", "app", "calls", "app/")
        self.assertEqual(r.returncode, 1)
        self.assertIn("a link needs two different components", r.stderr)

    def test_render_with_links(self):
        self.link("node", "SSD", "--concept")
        self.link("add", "app/db/store.py::save", "reads", "SSD")
        r = run([], cwd=self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 manual links", r.stdout)
        html = (self.proj / "repomap-out" / "map.html").read_text()
        self.assertIn('"concept:SSD"', html)
        self.assertIn('"manual_count"', html)

    def test_render_lists_missing_links(self):
        self.link("add", "app", "calls", "README.md")
        d = self.links()
        d["edges"][0]["tgt"] = "app/gone.py"
        d["nodes"]["app/models.py"] = {"kind": "file"}
        self.path.write_text(json.dumps(d))
        r = run([], cwd=self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 links point to missing components: app calls app/gone.py", r.stdout)
        self.assertIn("repomap link delete <src> <rel> <tgt>", r.stdout)
        self.assertIn("1 manual nodes now found by graphify: app/models.py", r.stdout)
        self.assertEqual(len(self.links()["edges"]), 1)

    def test_render_corrupt_links(self):
        self.path.parent.mkdir()
        self.path.write_text("{oops")
        r = run([], cwd=self.proj)
        self.assertEqual(r.returncode, 1)
        self.assertIn("repomap-out/links.json is not valid JSON", r.stderr)
        self.assertEqual(self.path.read_text(), "{oops")

    def test_note_on_concept(self):
        self.link("node", "SSD", "--concept")
        r = run(["note", "add", "SSD", "disk"], cwd=self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        run([], cwd=self.proj)
        html = (self.proj / "repomap-out" / "map.html").read_text()
        self.assertRegex(html, r'"concept:SSD": \{[^}]*"stale": false')

    def test_note_corrupt_links(self):
        self.path.parent.mkdir()
        self.path.write_text("{oops")
        r = run(["note", "add", "app", "x"], cwd=self.proj)
        self.assertEqual(r.returncode, 1)
        self.assertIn("links.json", r.stderr)


if __name__ == "__main__":
    unittest.main()
