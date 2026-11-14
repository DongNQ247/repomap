"""Embed the model and JS into a single self-contained HTML file."""
import json
import re
from pathlib import Path

WEB = Path(__file__).parent / "web"


def _js(name):
    # Inline scripts must never contain a literal "</script".
    return (WEB / name).read_text(encoding="utf-8").replace("</script", "<\\/script")


def render_html(model):
    parts = {
        "__MODEL__": json.dumps(model).replace("<", "\\u003c"),
        "/*__ELK__*/": _js("vendor/elk.bundled.js"),
        "/*__AGGREGATE__*/": _js("aggregate.js").replace("export function", "function"),
        "/*__APP__*/": _js("app.js"),
    }
    # Single pass so inserted content is never re-scanned for placeholders.
    pattern = re.compile("|".join(re.escape(k) for k in parts))
    return pattern.sub(lambda m: parts[m.group(0)], (WEB / "template.html").read_text(encoding="utf-8"))
