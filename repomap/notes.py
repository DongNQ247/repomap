"""Component ids, fingerprints (sha256) and notes.json storage."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .model import _line


def _name(label):
    label = str(label)
    if label.endswith("()"):
        label = label[:-2]
    return label.lstrip(".")


def components(model):
    comps = {}
    for f in model["files"]:
        parts = f["path"].split("/")
        for i in range(1, len(parts)):
            d = "/".join(parts[:i])
            comps[d] = {"box": d + "/", "kind": "dir", "file": None, "start": 0, "end": None}
        comps[f["path"]] = {"box": f["path"], "kind": "file", "file": f["path"], "start": 0, "end": None}
    syms = {s["id"]: s for s in model.get("symbols", [])}

    def chain(s):  # ancestor symbol ids, nearest first
        out, p = [], s["parent"]
        while p in syms and p not in out:
            out.append(p)
            p = syms[p]["parent"]
        return out

    def qual(s):
        return ".".join(_name(syms[a]["name"]) for a in reversed(chain(s))) + ("." if chain(s) else "") + _name(s["name"])

    by_file = {}
    for s in syms.values():
        by_file.setdefault(s["file"], []).append(s)
    for file, ss in by_file.items():
        ss.sort(key=lambda s: _line(s["loc"]))
        names = [qual(s) for s in ss]
        for i, s in enumerate(ss):
            start = _line(s["loc"])
            end = None
            if start:
                for t in ss[i + 1:]:
                    if _line(t["loc"]) > start and s["id"] not in chain(t):
                        end = _line(t["loc"])
                        break
            ident = f"{file}::{names[i]}" + (f"@L{start}" if names.count(names[i]) > 1 else "")
            comps[ident] = {"box": s["id"], "kind": "symbol", "file": file, "start": start, "end": end}
    return comps


def annotate(model, comps):
    ref = {c["box"]: k for k, c in comps.items() if c["kind"] == "symbol"}
    for s in model.get("symbols", []):
        s["ref"] = ref.get(s["id"])


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(comp, comps, root):
    root = Path(root)
    if comp["kind"] == "dir":
        prefix = comp["box"]
        rows = []
        for k, c in comps.items():
            if c["kind"] == "file" and k.startswith(prefix):
                rows.append(f"{k}\0{fingerprint(c, comps, root) or '?'}\n")
        return _sha("".join(sorted(rows)).encode())
    try:
        data = (root / comp["file"]).read_bytes()
    except OSError:
        return None
    if comp["kind"] == "symbol" and comp["start"]:
        lines = data.splitlines(keepends=True)
        data = b"".join(lines[comp["start"] - 1:comp["end"] - 1 if comp["end"] else None])
    return _sha(data)


def load_notes(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        d = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(str(e)) from None
    if not isinstance(d, dict) or not isinstance(d.get("notes"), dict) \
            or not all(isinstance(v, dict) and isinstance(v.get("text"), str) for v in d["notes"].values()):
        raise ValueError('expected {"version": 1, "notes": {...}}')
    return d["notes"]


def save_notes(path, notes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".notes-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "notes": notes}, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, 0o644)  # mkstemp makes 0600; notes are meant to be shared
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def note_view(notes, comps, root):
    view, missing = {}, []
    for k, n in notes.items():
        c = comps.get(k)
        if c is None:
            missing.append(k)
            continue
        view[c["box"]] = {"name": k, "text": n["text"], "stale": fingerprint(c, comps, root) != n.get("hash")}
    return view, sorted(missing)


def resolve(name, comps):
    name = name.strip().rstrip("/") if "::" not in name else name.strip()
    if name in comps:
        return name
    dups = sorted(k for k in comps if k.startswith(name + "@L"))
    if dups:
        raise KeyError(f"{name} is ambiguous: use one of {', '.join(dups)}")
    raise KeyError(f"{name} is not on the map")
