"""links.json storage (manual nodes and arrows) and merging them into the model."""
import json
import os
import tempfile
from pathlib import Path

from .model import classify

RELS = ("calls", "imports", "creates", "reads")


def load_links(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"nodes": {}, "edges": []}
    try:
        d = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(str(e)) from None
    ok = isinstance(d, dict) and isinstance(d.get("nodes"), dict) and isinstance(d.get("edges"), list) \
        and all(isinstance(v, dict) and v.get("kind") in ("file", "concept") for v in d["nodes"].values()) \
        and all(isinstance(e, dict) and isinstance(e.get("src"), str) and isinstance(e.get("tgt"), str)
                and e.get("rel") in RELS for e in d["edges"])
    if not ok:
        raise ValueError('expected {"version": 1, "nodes": {...}, "edges": [...]}')
    return {"nodes": d["nodes"], "edges": d["edges"]}


def save_links(path, links):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    edges = sorted(links["edges"], key=lambda e: (e["src"], e["rel"], e["tgt"]))
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".links-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "nodes": links["nodes"], "edges": edges}, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, 0o644)  # mkstemp makes 0600; links are meant to be shared
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def link_components(links, comps):
    out = dict(comps)
    for name, n in links["nodes"].items():
        if name in out:
            continue
        if n["kind"] == "concept":
            out[name] = {"box": "concept:" + name, "kind": "concept", "file": None, "start": 0, "end": None, "manual": True}
            continue
        parts = name.split("/")
        for i in range(1, len(parts)):
            d = "/".join(parts[:i])
            out.setdefault(d, {"box": d + "/", "kind": "dir", "file": None, "start": 0, "end": None, "manual": True})
        out[name] = {"box": name, "kind": "file", "file": None, "start": 0, "end": None, "manual": True}
    return out


def merge_links(model, links, comps):
    found = sorted(k for k, c in comps.items() if k in links["nodes"] and not c.get("manual"))
    model["concepts"] = []
    for name, n in sorted(links["nodes"].items()):
        if name in found:
            continue
        if n["kind"] == "concept":
            model["concepts"].append({"id": "concept:" + name, "label": name})
        else:
            model["files"].append({"path": name, "kind": classify(name), "manual": True})
    model["files"].sort(key=lambda f: f["path"])
    missing = []
    for e in links["edges"]:
        s, t = comps.get(e["src"]), comps.get(e["tgt"])
        if s is None or t is None:
            missing.append(f"{e['src']} {e['rel']} {e['tgt']}")
            continue
        model["edges"].append({"src": s["box"], "tgt": t["box"], "count": 1, "manual_count": 1, "by_rel": {e["rel"]: 1},
                               "samples": [{"from": e["src"], "to": e["tgt"], "rel": e["rel"], "loc": "manual"}]})
    return {"missing": missing, "found": found}
