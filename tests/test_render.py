import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from repomap.load import load_graph
from repomap.model import build_model
from repomap.render import render_html

FIXTURE = Path(__file__).parent / "fixtures" / "mini_graph.json"
ROOT = Path(__file__).parent.parent


class TestRender(unittest.TestCase):
    def test_self_contained(self):
        html = render_html(build_model(*load_graph(FIXTURE)))
        self.assertNotIn("http://", html.split("<script")[0])
        self.assertNotIn('src="http', html)
        self.assertNotIn("<link", html)
        self.assertIn("pkg/sub/b.py", html)
        self.assertFalse("export function" in html)
        self.assertFalse("/*__" in html)

    def test_html_escaping(self):
        model = {"files": [{"path": "x</script><b>&/*__APP__*/.py", "kind": "code"}], "external": [], "edges": []}
        html = render_html(model)
        self.assertEqual(html.count("</script>"), html.count("<script"))
        self.assertEqual(html.count("/*__APP__*/"), 1)  # only the file name; slot replaced once

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            r = subprocess.run([sys.executable, "-m", "repomap", str(FIXTURE), "-o", str(out)],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())
            self.assertIn(str(out), r.stdout)
            r = subprocess.run([sys.executable, "-m", "repomap", str(Path(tmp) / "missing.json")],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(r.stderr)


if __name__ == "__main__":
    unittest.main()
