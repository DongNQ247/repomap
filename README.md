# repomap

Draws a whole-repo map from graphify's `graph.json`: folders are frames, files are boxes, and
file→file arrows (`calls`, `imports`, `imports_from`) carry a count. Output is one self-contained HTML file that works offline.

```
python3 -m repomap path/to/graphify-out/graph.json -o out/map.html
```

By default it writes `repomap.html` next to `graph.json`. Python 3.10+ standard library only.

## Usage

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

## Test

```
python3 -m unittest discover tests -v
node --test tests/*.test.mjs
```
