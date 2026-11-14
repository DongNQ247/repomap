import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "tests" / "fixtures" / "sym_graph.json"


def run(args, cwd, env=None):
    env = {**os.environ, "PYTHONPATH": str(ROOT), **(env or {})}
    return subprocess.run([sys.executable, "-m", "repomap", *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


class CliTest(unittest.TestCase):
    def test_version(self):
        r = run(["--version"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "repomap 1.0.0")

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
        self.assertTrue((proj / "graphify-out" / "map.html").exists())
        self.assertIn("repomap 1.0.0 - reading graphify-out/graph.json", r.stdout)
        self.assertRegex(r.stdout, r"\d+ files - \d+ symbols - \d+ arrows")
        self.assertIn("OK wrote graphify-out/map.html (", r.stdout)
        self.assertIn("file://", r.stdout)
        self.assertNotIn("\033[", r.stdout)

    def test_missing_graph_gives_guide(self):
        r = run([], cwd=self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"graphify-out/graph.json not found in {self.tmp.resolve()}", r.stderr)
        self.assertIn("uv tool install graphifyy", r.stderr)
        self.assertIn("graphify update .", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

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
        self.assertEqual(r.stdout.strip(), str((proj / "graphify-out" / "map.html").resolve()))

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


if __name__ == "__main__":
    unittest.main()
