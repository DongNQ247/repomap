"""Read graph.json as raw JSON; link order (or _src/_tgt) is the edge direction."""
import json
from pathlib import Path


def load_graph(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in d.get("nodes", [])}
    links = []
    for l in d.get("links", d.get("edges", [])):
        src, tgt = l.get("_src", l.get("source")), l.get("_tgt", l.get("target"))
        if src in nodes and tgt in nodes:
            links.append({**l, "src": src, "tgt": tgt, "relation": l.get("relation", "")})
    return nodes, links
