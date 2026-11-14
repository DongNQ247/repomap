"""Collapse node-level graph into a file-level model."""
import re
from pathlib import PurePosixPath

ARROW_RELS = {"calls", "imports", "imports_from"}
DOC_EXT = {"md", "rst", "txt", "json", "yml", "yaml", "toml", "ini", "cfg", "csv", "xml", "csproj", "sln"}
TEST_DIRS = {"tests", "test", "__tests__"}
TEST_NAME = re.compile(r"^test_|_test\.|\.test\.|\.spec\.")
MAX_SAMPLES = 20


def classify(path):
    p = PurePosixPath(path)
    if TEST_DIRS & set(p.parts[:-1]) or TEST_NAME.search(p.name):
        return "test"
    if p.suffix[1:].lower() in DOC_EXT:
        return "doc"
    return "code"


def build_model(nodes, links):
    def end(nid):
        n = nodes[nid]
        return n.get("source_file") or "ext:" + str(n.get("label", nid))

    files = sorted({n["source_file"] for n in nodes.values() if n.get("source_file")})
    external = {}
    edges = {}
    for l in links:
        if l["relation"] not in ARROW_RELS:
            continue
        s, t = end(l["src"]), end(l["tgt"])
        if s == t:
            continue
        for key in (s, t):
            if key.startswith("ext:"):
                external[key] = {"id": key, "label": key[4:]}
        e = edges.setdefault((s, t), {"src": s, "tgt": t, "count": 0, "by_rel": {}, "samples": []})
        e["count"] += 1
        e["by_rel"][l["relation"]] = e["by_rel"].get(l["relation"], 0) + 1
        if len(e["samples"]) < MAX_SAMPLES:
            e["samples"].append({
                "from": nodes[l["src"]].get("label", l["src"]),
                "to": nodes[l["tgt"]].get("label", l["tgt"]),
                "rel": l["relation"],
                "loc": f"{l.get('source_file', '')}:{l.get('source_location', '')}",
            })
    return {
        "files": [{"path": f, "kind": classify(f)} for f in files],
        "external": sorted(external.values(), key=lambda x: x["id"]),
        "edges": list(edges.values()),
    }
