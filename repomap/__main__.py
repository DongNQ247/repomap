import argparse
import json
import os
import sys
from importlib.resources import files
from importlib.metadata import PackageNotFoundError, version
from datetime import date
from pathlib import Path

from .load import load_graph
from .model import build_model
from .links import RELS, link_components, load_links, merge_links, save_links
from .notes import annotate, components, fingerprint, load_notes, note_view, resolve, save_notes
from .render import render_html

try:
    VERSION = version("repomap")
except PackageNotFoundError:
    VERSION = "0+unknown"

GUIDE = """
repomap draws a map from graphify's output. To create it:
  1. install graphify:   uv tool install graphifyy
  2. build the graph:    graphify update .
  3. run again:          repomap .
Or pass a path:          repomap path/to/graph.json"""


def find_graph(arg, cwd):
    if arg is None:
        return cwd / "graphify-out" / "graph.json"
    arg = cwd / arg
    if arg.is_dir():
        nested = arg / "graphify-out" / "graph.json"
        return nested if nested.exists() else arg / "graph.json"
    return arg


def style(stream):
    return stream.isatty() and not os.environ.get("NO_COLOR")


def rel(p, cwd):
    p = p.resolve()
    try:
        return str(p.relative_to(cwd.resolve()))
    except ValueError:
        return str(p)


def size(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{round(n / 1e3)} KB"


def fail(msg):
    err = "\033[31merror:\033[0m" if style(sys.stderr) else "error:"
    print(f"repomap: {err} {msg}", file=sys.stderr)
    return 1


def project_root(graph):
    return graph.parent.parent if graph.parent.name == "graphify-out" else graph.parent


def find_project(cwd):
    for d in (cwd, *cwd.parents):
        if (d / "graphify-out" / "graph.json").is_file():
            return d
    return None


def read_model(graph, shown):
    """Model from graph.json, or an exit code after printing the error."""
    try:
        data = json.loads(graph.read_text(encoding="utf-8"))
    except OSError as e:
        return fail(f"cannot read {shown}: {e.strerror}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return fail(f"{shown} is not valid JSON: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        return fail(f"{shown} does not look like a graphify graph.json (no nodes/links)")
    try:
        return build_model(*load_graph(graph))  # shortcut: re-reads the file; fine for one CLI run
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        return fail(f"{shown} does not look like a graphify graph.json (no nodes/links): {e}")


def note_main(argv):
    ap = argparse.ArgumentParser(prog="repomap note", description="Save, delete or confirm a note on a map component.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="save or replace the note for a component")
    a.add_argument("name", help="folder (app/db), file (app/db/store.py) or symbol (app/models.py::User.display)")
    a.add_argument("text")
    for cmd, h in (("delete", "delete the note"), ("ok", "mark the note as still correct")):
        sub.add_parser(cmd, help=h).add_argument("name")
    args = ap.parse_args(argv)
    cwd = Path.cwd()
    root = find_project(cwd)
    if root is None:
        fail(f"graphify-out/graph.json not found in {cwd.resolve()} or any parent folder")
        print(GUIDE, file=sys.stderr)
        return 1
    if args.cmd == "add" and not args.text.strip():
        return fail("note text is empty")
    graph = root / "graphify-out" / "graph.json"
    model = read_model(graph, rel(graph, cwd))
    if isinstance(model, int):
        return model
    links_path = root / "repomap-out" / "links.json"
    try:
        comps = link_components(load_links(links_path), components(model))
    except ValueError as e:
        return fail(f"{rel(links_path, root)} is not valid JSON: {e}")
    except OSError as e:
        return fail(f"cannot read {rel(links_path, root)}: {e.strerror}")
    path = root / "repomap-out" / "notes.json"
    try:
        notes = load_notes(path)
        key = args.name.rstrip("/")
        # notes on renamed/removed components must stay deletable
        name = key if args.cmd == "delete" and key in notes else resolve(args.name, comps)
    except ValueError as e:
        return fail(f"{rel(path, root)} is not valid JSON: {e}")
    except OSError as e:
        return fail(f"cannot read {rel(path, root)}: {e.strerror}")
    except KeyError as e:
        return fail(e.args[0])
    if args.cmd != "add" and name not in notes:
        return fail(f"no note for {name}")
    if args.cmd == "delete":
        del notes[name]
        done = "deleted note for"
    else:
        text = args.text if args.cmd == "add" else notes[name]["text"]
        notes[name] = {"text": text, "hash": fingerprint(comps[name], comps, root), "updated": date.today().isoformat()}
        done = "saved note for" if args.cmd == "add" else "marked note for"
    try:
        save_notes(path, notes)
    except OSError as e:
        return fail(f"cannot write {rel(path, cwd)}: {e.strerror}")
    ok = "\033[32m✓\033[0m" if style(sys.stdout) else "OK"
    print(f"{ok} {done} {name}" + (" as up to date" if args.cmd == "ok" else ""))
    return 0


def link_main(argv):
    ap = argparse.ArgumentParser(prog="repomap link", description="Add or delete manual nodes and arrows graphify missed.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("node", help="add a runtime file (out/map.html) or, with --concept, a concept (SSD)")
    n.add_argument("name")
    n.add_argument("--concept", action="store_true", help="something outside the code, e.g. SSD or an external service")
    a = sub.add_parser("add", help="add an arrow")
    a.add_argument("src")
    a.add_argument("rel", choices=RELS)
    a.add_argument("tgt")
    sub.add_parser("delete", help="delete an arrow (src rel tgt) or a manual node (name)").add_argument("args", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "delete" and len(args.args) not in (1, 3):
        ap.error("delete takes <name> or <src> <rel> <tgt>")
    cwd = Path.cwd()
    root = find_project(cwd)
    if root is None:
        fail(f"graphify-out/graph.json not found in {cwd.resolve()} or any parent folder")
        print(GUIDE, file=sys.stderr)
        return 1
    graph = root / "graphify-out" / "graph.json"
    model = read_model(graph, rel(graph, cwd))
    if isinstance(model, int):
        return model
    path = root / "repomap-out" / "links.json"
    try:
        links = load_links(path)
    except ValueError as e:
        return fail(f"{rel(path, root)} is not valid JSON: {e}")
    except OSError as e:
        return fail(f"cannot read {rel(path, root)}: {e.strerror}")
    comps = link_components(links, components(model))
    nodes, edges = links["nodes"], links["edges"]
    show = lambda e: f"{e['src']} {e['rel']} {e['tgt']}"
    if args.cmd == "node":
        name, kind = args.name.strip(), "concept" if args.concept else "file"
        if nodes.get(name, {}).get("kind") == kind:
            print(f"already exists: {name}")
            return 0
        parents = ["/".join(name.split("/")[:i]) for i in range(1, name.count("/") + 1)]
        if not name:
            return fail("name is empty")
        if name in comps:
            return fail(f"{name} is already on the map")
        if args.concept and ("/" in name or "::" in name):
            return fail(f"a concept name cannot contain '/' or '::': {name}")
        if not args.concept and (name.endswith("/") or "::" in name):
            return fail(f"a runtime node must be a file path (folders are made from it): {name}")
        if not args.concept and any(comps.get(p, {}).get("kind") == "file" for p in parents):
            return fail(f"{name} would be inside a file")
        nodes[name] = {"kind": kind}
        done = f"added node {name}"
    elif args.cmd == "add":
        try:
            e = {"src": resolve(args.src, comps), "rel": args.rel, "tgt": resolve(args.tgt, comps)}
        except KeyError as err:
            return fail(err.args[0])
        if e["src"] == e["tgt"]:
            return fail("a link needs two different components")
        if e in edges:
            print(f"already exists: {show(e)}")
            return 0
        edges.append(e)
        done = f"added link {show(e)}"
    elif len(args.args) == 3:
        def key(x):  # links to renamed/removed components must stay deletable
            try:
                return resolve(x, comps)
            except KeyError:
                return x.strip() if "::" in x else x.strip().rstrip("/")
        e = {"src": key(args.args[0]), "rel": args.args[1], "tgt": key(args.args[2])}
        if e not in edges:
            return fail(f"no link {show(e)}")
        edges.remove(e)
        done = f"deleted link {show(e)}"
    else:
        name = args.args[0].strip()
        if name not in nodes:
            return fail(f"no manual node {name}")
        used = [show(e) for e in edges if name in (e["src"], e["tgt"])]
        if used:
            return fail(f"{name} still has links: {', '.join(used)}; delete them first")
        del nodes[name]
        done = f"deleted node {name}"
    try:
        save_links(path, links)
    except OSError as e:
        return fail(f"cannot write {rel(path, cwd)}: {e.strerror}")
    ok = "\033[32m✓\033[0m" if style(sys.stdout) else "OK"
    print(f"{ok} {done}")
    return 0


def skill_main(argv):
    ap = argparse.ArgumentParser(prog="repomap skill", description="Manage the bundled Claude Code skill.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("install", help="copy SKILL.md to ~/.claude/skills/repomap/")
    ap.parse_args(argv)
    dst = Path.home() / ".claude" / "skills" / "repomap" / "SKILL.md"
    try:
        text = (files("repomap") / "skill" / "SKILL.md").read_text(encoding="utf-8")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
    except OSError as e:
        return fail(f"cannot write {dst}: {e.strerror}")
    ok = "\033[32m✓\033[0m" if style(sys.stdout) else "OK"
    print(f"{ok} installed Claude Code skill: {dst}")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["note"]:
        return note_main(argv[1:])
    if argv[:1] == ["link"]:
        return link_main(argv[1:])
    if argv[:1] == ["skill"]:
        return skill_main(argv[1:])
    ap = argparse.ArgumentParser(prog="repomap", description="Render graphify's graph.json as a nested file/folder call map.")
    ap.add_argument("graph", nargs="?", type=Path,
                    help="graph.json, or a project folder (default: ./graphify-out/graph.json)")
    ap.add_argument("-o", "--out", type=Path, help="output HTML (default: repomap-out/map.html in the project)")
    ap.add_argument("-q", "--quiet", action="store_true", help="print only the output path")
    ap.add_argument("--version", action="version", version=f"repomap {VERSION}")
    args = ap.parse_args(argv)
    cwd = Path.cwd()
    graph = find_graph(args.graph, cwd)
    if not graph.is_file():
        fail(f"{rel(graph, cwd)} not found in {cwd.resolve()}" if args.graph is None else f"{rel(graph, cwd)} not found")
        print(GUIDE, file=sys.stderr)
        return 1
    shown = rel(graph, cwd)
    model = read_model(graph, shown)
    if isinstance(model, int):
        return model
    root = project_root(graph)
    notes_path = root / "repomap-out" / "notes.json"
    try:
        notes = load_notes(notes_path)
    except ValueError as e:
        return fail(f"{rel(notes_path, root)} is not valid JSON: {e}")
    except OSError as e:
        return fail(f"cannot read {rel(notes_path, root)}: {e.strerror}")
    links_path = root / "repomap-out" / "links.json"
    try:
        links = load_links(links_path)
    except ValueError as e:
        return fail(f"{rel(links_path, root)} is not valid JSON: {e}")
    except OSError as e:
        return fail(f"cannot read {rel(links_path, root)}: {e.strerror}")
    comps = link_components(links, components(model))
    lost = merge_links(model, links, comps)
    annotate(model, comps)
    model["notes"], missing = note_view(notes, comps, root)
    html = render_html(model)
    out = cwd / args.out if args.out else root / "repomap-out" / "map.html"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    except OSError as e:
        return fail(f"cannot write {rel(out, cwd)}: {e.strerror}")
    if args.quiet:
        print(out.resolve())
        return 0
    fancy = style(sys.stdout)
    dot = "·" if fancy else "-"
    ok = "\033[32m✓\033[0m" if fancy else "OK"
    n = lambda k: f"{len(model.get(k, [])):,}"
    print(f"repomap {VERSION} {dot} reading {shown}")
    print(f"  {n('files')} files {dot} {n('symbols')} symbols {dot} {n('edges')} arrows")
    if model["notes"]:
        k = sum(v["stale"] for v in model["notes"].values())
        print(f"  {len(model['notes'])} notes" + (f" {dot} {k} may be outdated" if k else ""))
    if missing:
        print(f"  {len(missing)} notes point to missing components: {', '.join(missing)}")
    if links["edges"]:
        print(f"  {len(links['edges'])} manual links")
    if lost["missing"]:
        print(f"  {len(lost['missing'])} links point to missing components: {', '.join(lost['missing'])}"
              " — remove with: repomap link delete <src> <rel> <tgt>")
    if lost["found"]:
        print(f"  {len(lost['found'])} manual nodes now found by graphify: {', '.join(lost['found'])}"
              f" — remove with: repomap link delete {lost['found'][0]}")
    print(f"{ok} wrote {rel(out, cwd)} ({size(out.stat().st_size)})")
    print(f"  open it in your browser: {out.resolve().as_uri()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
