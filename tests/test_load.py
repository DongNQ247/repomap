import json
import tempfile
import unittest
from pathlib import Path

from repomap.load import load_graph

FIXTURE = Path(__file__).parent / "fixtures" / "mini_graph.json"


class TestLoad(unittest.TestCase):
    def test_direction_marker_wins(self):
        _, links = load_graph(FIXTURE)
        l = [x for x in links if {x["src"], x["tgt"]} == {"b1", "c1"}][0]
        self.assertEqual((l["src"], l["tgt"]), ("c1", "b1"))

    def test_arc_order_is_direction(self):
        _, links = load_graph(FIXTURE)
        self.assertIn(("a1", "b1", "calls"), {(x["src"], x["tgt"], x["relation"]) for x in links})

    def test_edges_key_fallback(self):
        d = json.loads(FIXTURE.read_text())
        d["edges"] = d.pop("links")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "g.json"
            p.write_text(json.dumps(d))
            _, links = load_graph(p)
        self.assertEqual(len(links), 9)

    def test_dangling_link_dropped(self):
        _, links = load_graph(FIXTURE)
        self.assertNotIn("ghost", {x["tgt"] for x in links})


if __name__ == "__main__":
    unittest.main()
