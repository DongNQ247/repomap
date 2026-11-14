import argparse
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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="repomap", description="Render graph.json as a nested file/folder call map.")
    ap.add_argument("graph", type=Path, help="path to graphify graph.json")
    ap.add_argument("-o", "--out", type=Path, help="output HTML (default: repomap.html next to graph.json)")
    ap.add_argument("--version", action="version", version=f"repomap {VERSION}")
    args = ap.parse_args(argv)
    out = args.out or args.graph.with_name("repomap.html")
    try:
        html = render_html(build_model(*load_graph(args.graph)))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"repomap: error: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
