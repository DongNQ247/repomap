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


def _line(loc):
    m = re.search(r"\d+", loc or "")
    return int(m.group()) if m else 0


def build_model(nodes, links):
    # Symbol = code node contained (contains/method) by a node of the same file; value = parent id.
    # Doc/config files (JSON/YAML keys) get no symbols even if the extractor marks them code.
    code = lambda nid: nodes[nid].get("file_type") == "code" and nodes[nid].get("source_file") \
        and classify(nodes[nid]["source_file"]) != "doc"
    parent_of, has_method = {}, set()
    for l in links:
        if l["relation"] in ("contains", "method") and code(l["tgt"]) \
                and nodes[l["src"]].get("source_file") == nodes[l["tgt"]]["source_file"]:
            parent_of.setdefault(l["tgt"], l["src"])
        if l["relation"] == "method":
            has_method.add(l["src"])
    # Break contains cycles: a parent whose chain leads back to the child -> attach to the file.
    for nid in list(parent_of):
        p, seen = parent_of[nid], set()
        while p in parent_of and p != nid and p not in seen:
            seen.add(p)
            p = parent_of[p]
        if p == nid:
            parent_of[nid] = None

    def end(nid, rel=""):
        if rel == "calls" and nid in parent_of:
            return "sym:" + nid
        n = nodes[nid]
        return n.get("source_file") or "ext:" + str(n.get("label", nid))

    files = sorted({n["source_file"] for n in nodes.values() if n.get("source_file")})
    external = {}
    edges = {}
    for l in links:
        if l["relation"] not in ARROW_RELS:
            continue
        s, t = end(l["src"], l["relation"]), end(l["tgt"], l["relation"])
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
    symbols = []
    for nid, p in parent_of.items():
        n = nodes[nid]
        symbols.append({
            "id": "sym:" + nid, "name": n.get("label", nid), "file": n["source_file"],
            "parent": "sym:" + p if p in parent_of else n["source_file"],
            "kind": "class" if nid in has_method or n.get("_callable_class") else "func",
            "loc": n.get("source_location") or "",
        })
    symbols.sort(key=lambda x: (x["file"], _line(x["loc"]), x["name"]))
    return {
        "symbols": symbols,
        "files": [{"path": f, "kind": classify(f)} for f in files],
        "external": sorted(external.values(), key=lambda x: x["id"]),
        "edges": list(edges.values()),
    }
