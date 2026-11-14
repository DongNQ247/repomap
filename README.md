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

## Test

```
python3 -m unittest discover tests -v
node --test tests/*.test.mjs
```
