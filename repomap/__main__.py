import argparse
import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .load import load_graph
from .model import build_model
from .render import render_html

try:
    VERSION = version("repomap")
except PackageNotFoundError:
    VERSION = "0+unknown"

GUIDE = """
repomap draws a map from graphify's output. To create it:
  1. install graphify:   uv tool install graphifyy
  2. build the graph:    graphify update .
  3. run again:          repomap
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
    return stream.isatty() and "NO_COLOR" not in os.environ


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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="repomap", description="Render graphify's graph.json as a nested file/folder call map.")
    ap.add_argument("graph", nargs="?", type=Path,
                    help="graph.json, or a project folder (default: ./graphify-out/graph.json)")
    ap.add_argument("-o", "--out", type=Path, help="output HTML (default: map.html next to graph.json)")
    ap.add_argument("-q", "--quiet", action="store_true", help="print only the output path")
    ap.add_argument("--version", action="version", version=f"repomap {VERSION}")
    args = ap.parse_args(argv)
    cwd = Path.cwd()
    graph = find_graph(args.graph, cwd)
    if not graph.is_file():
        fail(f"{rel(graph, cwd)} not found in {cwd.resolve()}" if args.graph is None else f"{args.graph} not found")
        print(GUIDE, file=sys.stderr)
        return 1
    shown = rel(graph, cwd)
    try:
        data = json.loads(graph.read_text(encoding="utf-8"))
    except OSError as e:
        return fail(f"cannot read {shown}: {e.strerror}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return fail(f"{shown} is not valid JSON: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        return fail(f"{shown} does not look like a graphify graph.json (no nodes/links)")
    try:
        model = build_model(*load_graph(graph))  # shortcut: re-reads the file; fine for one CLI run
        html = render_html(model)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        return fail(f"{shown} does not look like a graphify graph.json (no nodes/links): {e}")
    out = cwd / args.out if args.out else graph.with_name("map.html")
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
    print(f"{ok} wrote {rel(out, cwd)} ({size(out.stat().st_size)})")
    print(f"  open it in your browser: {out.resolve().as_uri()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
