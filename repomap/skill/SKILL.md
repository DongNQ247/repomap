---
name: repomap
description: Use when the developer explicitly asks to save, update or delete an explanation of a code component (folder, file, class, function) on the repomap map - "save this note", "save it", "note this down", "ghi lai", "luu note" - or asks about repomap notes marked "may be outdated".
---

# repomap notes

repomap draws a map of the repo from graphify's `graphify-out/graph.json`. Notes attach a short
explanation to a folder, file or symbol; they are stored in `repomap-out/notes.json` and shown in the
map's details panel.

## Only when asked

Save a note **only** when the developer explicitly says so ("save this note", "save it", "ghi lai", ...).
Never save answers on your own initiative.

## Commands (run from anywhere inside the project)

```
repomap note add <name> "<text>"   # save, or replace the existing note
repomap note delete <name>
repomap note ok <name>             # code changed, note still correct
repomap .                          # re-render repomap-out/map.html (from the project root)
```

After `note add`, `note delete` or `note ok`, run `repomap .` from the project root so the map shows the change.

## Naming components

Paths are relative to the project root (the folder holding `graphify-out/`):

- folder: `app/db` (no trailing slash; the project root itself cannot have a note)
- file: `app/db/store.py` (doc files such as `README.md` too)
- symbol: `<file>::<name>`, e.g. `app/db/store.py::save`
- method or nested symbol: join parents with `.`, e.g. `app/models.py::User.display`
- two symbols with the same name in one file: add the start line, e.g. `app/dup.py::helper@L40`.
  If a name is ambiguous, repomap lists the valid `@L` names; pick the right one.

## Writing the note

- Short: a few sentences, plain text (no Markdown). Line breaks are kept.
- Say what the component means and why it exists or works this way - not what the code literally does.
- Do not paste code.

## Outdated notes

A note is marked "may be outdated" when the code it describes changed. Re-read the code, then either
`repomap note add <name> "<corrected text>"` or, if it is still right, `repomap note ok <name>`.
`repomap` also lists notes whose component no longer exists; ask the developer before `note delete`.

## Errors

- `<name> is not on the map`: check the name against the rules above. If the code is new, the graph
  may be stale: run `graphify update .` first, then retry.
- `graphify-out/graph.json not found`: build the graph with `graphify update .`.
