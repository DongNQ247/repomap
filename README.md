# repomap

Draws a whole-repo map from graphify's `graph.json`: folders are frames, files are boxes, and
file→file arrows (`calls`, `imports`, `imports_from`) carry a count. Output is one self-contained HTML file that works offline.

## Requirements

- Python 3.10+ (standard library only).
- [graphify](https://pypi.org/project/graphifyy/) to build the graph: `uv tool install graphifyy`, then `graphify update .` in your project.

## Install

```
uv tool install git+https://github.com/DongNQ247/repomap
uv tool install git+https://github.com/DongNQ247/repomap@v1.0.0   # pinned version
uv tool upgrade repomap
uv tool uninstall repomap
```

## Command line

```
repomap                    # reads ./graphify-out/graph.json, writes graphify-out/map.html
repomap PATH               # PATH is a graph.json, or a folder containing graphify-out/graph.json
repomap -o out/map.html    # write somewhere else
repomap -q                 # print only the absolute path of the written file
repomap --version
```

An existing `map.html` is overwritten. The browser is not opened; the command prints a `file://` link.
If `graph.json` is missing, repomap prints how to install graphify and build it, and exits with code 1.
Invalid JSON, a file that is not a graphify graph, or an unwritable output also exit with code 1; bad arguments exit with code 2.

## Using the map

- Click a folder to expand/collapse it. All folders start collapsed; arrows into a collapsed folder are merged and their counts summed.
- Hover an arrow to see its breakdown by relation and the symbol pairs with `file:line`. Click to pin, click the background to unpin.
- Scroll to zoom, drag to pan.
- **Test arrows**: show arrows that start from test files (test boxes are always shown).
- **Docs/config**: show `.md`, `.json`, `.yml`, `.toml`… files.
- **External**: show a frame of symbols outside the repo (nodes without `source_file`), by symbol name.
- **Collapse all**: back to the initial state.
- If expanding would show more than 400 boxes + arrows, you are asked to confirm first.

## Tree panel

- The left panel shows the repo's folder tree; **Tree** in the top bar opens/closes it (closed by default on narrow screens).
- Expanding/collapsing in the tree is only for browsing and does not change the map.
- Uncheck a file or folder to remove it, and every arrow into or out of it, from the map. A folder's checkbox shows a partial state when only some of its contents are hidden. **Show all** brings everything back; hidden state is not kept on reload.
- **Search files…** filters the tree by name (case-insensitive substring) and shows the path to each match.
- Click a name to open its parent folders on the map, center it and highlight it.
- The tree only lists items the filter buttons allow (docs with **Docs/config**, the external frame with **External**). Counts and the 400-item check exclude hidden items.

## Expanding files

- Click a file with functions/classes (`▸ a.py (N symbols)`) to open it as a frame showing them; click a class (`▸ K (N methods)`) to see its methods. Files and classes start collapsed. Files with no symbols (e.g. an empty `__init__.py`) do not open.
- `calls` arrows attach to the function when it is visible and merge up to the nearest visible class/file when collapsed. Imports and module-level calls stay on the file frame. Arrow counts at file level are unchanged.
- Symbols appear in the tree panel too (classes in bold, functions in italics); hide, search and click-to-jump work the same. Hover shows `file:line`.

## Test

```
python3 -m unittest discover tests -v
node --test tests/*.test.mjs
```

## License

MIT
