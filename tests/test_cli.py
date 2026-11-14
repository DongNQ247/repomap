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


if __name__ == "__main__":
    unittest.main()
