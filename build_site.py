#!/usr/bin/env python3
"""Build a static index.html from the curated Quotes.md file.

Parses the Obsidian-style quote list, which is grouped by theme:

    ## Theme name
    > "a quote"
    > — [[Author - Title]]

    > "another quote"
    > — [[Author - Title]]

and renders a single self-contained HTML page grouped by theme, with each
quote attributed back to its source. Only Quotes.md is read; the raw
transcripts under Sources/ are never published.
"""

import html
import json
import re
from itertools import chain, zip_longest
from pathlib import Path

QUOTES_FILE = Path("AI quotes library/Quotes.md")
SOURCES_FILE = Path("sources.json")
SOURCES_DIR = Path("AI quotes library/Sources")
AUTHORS_FILE = Path("authors.json")
OUTPUT_FILE = Path("dist/index.html")
# The local preview server runs sandboxed out of this (TCC-protected) folder,
# so it reads from a copy under /tmp instead. We refresh that copy here only if
# its directory already exists, so a normal build is unaffected on other setups.
PREVIEW_MIRROR = Path("/tmp/ai-quotes-preview/index.html")

THEME_RE = re.compile(r"^##\s+(?!\[\[)(.+?)\s*$")
BYLINE_RE = re.compile(r"^>\s*[—–-]?\s*\[\[(.+?)\]\]\s*$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")


def parse(text):
    """Return a list of {theme, quotes:[{text, raw, author, title}]} groups."""
    themes = []
    current = None
    pending = []  # quote bodies seen but not yet attributed to a source
    for line in text.splitlines():
        theme = THEME_RE.match(line)
        if theme:
            pending = []
            current = {"theme": theme.group(1).strip(), "quotes": []}
            themes.append(current)
            continue
        byline = BYLINE_RE.match(line)
        if byline and current is not None and pending:
            raw = byline.group(1).strip()
            author, _, title = raw.partition(" - ")
            for body in pending:
                current["quotes"].append(
                    {
                        "text": body,
                        "raw": raw,
                        "author": author.strip() if title else "",
                        "title": title.strip() if title else raw,
                    }
                )
            pending = []
            continue
        quote = QUOTE_RE.match(line)
        if quote:
            body = quote.group(1).strip()
            if body:
                pending.append(body)
    return [t for t in themes if t["quotes"]]


def interleave(themes):
    """Flatten themes into one [(quote, theme_name)] list, round-robin across
    themes so same-theme quotes are spread out across the canvas rather than
    clustered. Quotes.md is grouped by theme, so naive source order would put a
    theme's quotes adjacent; taking one quote from each theme per round mixes them.
    """
    columns = [[(q, t["theme"]) for q in t["quotes"]] for t in themes]
    return [item for item in chain.from_iterable(zip_longest(*columns)) if item is not None]


def load_sources():
    if SOURCES_FILE.exists():
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {}


def scan_frontmatter():
    """Scan Sources/ frontmatter into {file-stem: {author, role}}.

    Reads only the YAML frontmatter block at the top of each source file; the
    transcript body is never inspected or published. Returns {} when Sources/
    is absent (e.g. on CI, where transcripts are gitignored).
    """
    meta = {}
    if not SOURCES_DIR.exists():
        return meta
    for path in SOURCES_DIR.rglob("*.md"):
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            continue
        fields = {}
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, sep, val = line.partition(":")
            if sep:
                fields[key.strip()] = val.strip().strip('"')
        entry = {k: fields[k] for k in ("author", "role") if fields.get(k)}
        if entry:
            meta[path.stem] = entry
    return meta


def load_source_meta():
    """Return {file-stem: {author, role}} for attributing quotes.

    Sources/ holds the gitignored transcripts, so it's only present in local
    builds. When it is, we scan its frontmatter and refresh the tracked
    authors.json sidecar from it. On CI (Sources/ absent) we fall back to that
    committed sidecar, so roles still render on the deployed site.
    """
    meta = scan_frontmatter()
    if meta:
        AUTHORS_FILE.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return meta
    if AUTHORS_FILE.exists():
        return json.loads(AUTHORS_FILE.read_text(encoding="utf-8"))
    return {}


def strip_quotes(text):
    """Drop a single pair of surrounding quotation marks, if present.

    Quotes.md stores each quote with its literal wrapping quote marks; the card
    shows the quote-glyph icon instead, so we strip the redundant marks here
    rather than editing the verbatim source."""
    pairs = (('"', '"'), ("“", "”"), ("‘", "’"), ("'", "'"))
    for open_q, close_q in pairs:
        if text.startswith(open_q) and text.endswith(close_q) and len(text) >= 2:
            return text[len(open_q):-len(close_q)].strip()
    return text


def render_card(quote, theme, sources, source_meta):
    """One self-contained quote card: theme chip + quote glyph + quote + byline.

    The theme is shown as a small chip (it is a label, not a control); themes do
    not drive layout. data-theme is also set for SEO / future use.
    """
    return (
        f'      <figure class="quote" data-theme="{html.escape(theme, quote=True)}">\n'
        f'        <div class="card-top">\n'
        f'          <span class="qmark" aria-hidden="true">&ldquo;</span>\n'
        f'          <span class="chip">{html.escape(theme)}</span>\n'
        f"        </div>\n"
        f'        <blockquote>{html.escape(strip_quotes(quote["text"]))}</blockquote>\n'
        f"        {render_byline(quote, sources, source_meta)}\n"
        f"      </figure>"
    )


def render_byline(quote, sources, source_meta):
    meta = source_meta.get(quote["raw"], {})
    author = html.escape(meta.get("author") or quote["author"])
    role = html.escape(meta.get("role", ""))
    url = sources.get(quote["raw"])
    if url:
        href = html.escape(url, quote=True)
        title = (
            f'<a class="title" href="{href}" target="_blank" rel="noopener">'
            f'{html.escape(quote["title"])}</a>'
        )
    else:
        title = f'<span class="title">{html.escape(quote["title"])}</span>'
    parts = []
    if author:
        parts.append(f'<span class="author">{author}</span>')
    if role:
        parts.append(f'<span class="role">{role}</span>')
    parts.append(title)
    inner = '<span class="sep">·</span>'.join(parts)
    return f'<figcaption class="source">{inner}</figcaption>'


def render(themes, sources, source_meta):
    pool = interleave(themes)
    cards = "\n".join(
        render_card(quote, theme, sources, source_meta) for quote, theme in pool
    )
    return TEMPLATE.format(
        body=cards,
        total=len(pool),
        themes=len(themes),
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Quotes Library</title>
<meta name="description" content="A curated collection of notable quotes about AI, design, and craft.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;1,400&family=Spectral:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #f3f3f1;
    --ink: #1a1a18;
    --muted: #888884;
    --faint: #c6c5c1;
    --rule: #e3e2de;
    --card: #fcfcfb;
    --serif-display: "Playfair Display", Georgia, "Times New Roman", serif;
    --serif-text: "Spectral", Georgia, "Iowan Old Style", serif;
    --sans: "Helvetica Neue", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--serif-text);
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 14vh 28px 20vh; }}

  /* Masthead */
  .masthead {{ margin-bottom: 16vh; }}
  h1 {{
    margin: 0;
    font-family: var(--serif-display);
    font-weight: 400;
    font-size: clamp(2.8rem, 9vw, 5rem);
    line-height: 1.02;
    letter-spacing: -0.015em;
  }}

  /* Theme sections */
  .theme {{ margin-top: 15vh; }}
  .theme:first-of-type {{ margin-top: 0; }}
  .theme-head {{
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: baseline;
    column-gap: 1.2rem;
    padding-bottom: 1.8rem;
    cursor: pointer;
    list-style: none;
  }}
  .theme-head::-webkit-details-marker {{ display: none; }}
  .theme-head:focus-visible {{
    outline: 2px solid var(--ink);
    outline-offset: 4px;
  }}
  .theme-toggle {{
    align-self: center;
    width: 0.6rem;
    height: 0.6rem;
    border-right: 1.5px solid var(--muted);
    border-bottom: 1.5px solid var(--muted);
    transform: rotate(45deg);
    transform-origin: center;
    transition: transform 0.2s ease, border-color 0.18s ease;
  }}
  .theme[open] .theme-toggle {{ transform: rotate(-135deg); }}
  .theme-head:hover .theme-toggle {{ border-color: var(--ink); }}
  .theme-name {{
    margin: 0;
    font-family: var(--serif-display);
    font-weight: 400;
    font-size: clamp(1.6rem, 4.2vw, 2.4rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }}

  /* Quotes — card grid */
  .quotes {{
    margin-top: 2.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 24px;
    align-items: stretch;
  }}
  .quote {{
    margin: 0;
    display: flex;
    flex-direction: column;
    padding: 24px 28px 26px;
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 14px;
    box-shadow: 0 10px 30px -18px rgba(0, 0, 0, 0.25);
  }}
  .card-top {{
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
  }}
  .qmark {{
    font-family: var(--serif-display);
    font-size: 5.2rem;
    line-height: 0.8;
    color: var(--ink);
  }}
  blockquote {{
    margin: 0;
    font-size: clamp(1.1rem, 2vw, 1.18rem);
    line-height: 1.45;
    text-wrap: pretty;
  }}
  .source {{
    margin-top: auto;
    padding-top: 20px;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    font-family: var(--sans);
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    color: var(--muted);
  }}
  .source .author {{
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: var(--ink);
  }}
  .source .role {{
    font-family: var(--serif-text);
    font-style: italic;
    font-size: 0.95rem;
    letter-spacing: 0;
  }}
  .source .title {{
    font-family: var(--serif-text);
    font-style: italic;
    font-size: 0.92rem;
    letter-spacing: 0;
    color: var(--muted);
  }}
  .source .sep {{ margin: 0 0.7em; color: var(--faint); }}
  a.title {{
    text-decoration: none;
    transition: color 0.18s ease;
  }}
  a.title:hover {{ color: var(--ink); }}

  footer {{
    margin-top: 18vh;
    padding-top: 3rem;
    border-top: 1px solid var(--rule);
    font-family: var(--sans);
    font-size: 0.72rem;
    letter-spacing: 0.04em;
    color: var(--muted);
  }}
  footer code {{ font-family: var(--sans); font-style: italic; }}

  @media (max-width: 700px) {{
    .wrap {{ padding: 9vh 20px 14vh; }}
    .quotes {{ gap: 18px; }}
  }}

  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #131312;
      --ink: #eae9e5;
      --muted: #918f8a;
      --faint: #46453f;
      --rule: #2a2a27;
      --card: #1b1b19;
    }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header class="masthead">
      <h1>AI Quotes Library</h1>
    </header>
    <main>
{body}
    </main>
    <footer>
      Curated collection. Built from <code>Quotes.md</code>.
    </footer>
  </div>
</body>
</html>
"""


def main():
    text = QUOTES_FILE.read_text(encoding="utf-8")
    themes = parse(text)
    sources = load_sources()
    source_meta = load_source_meta()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    page = render(themes, sources, source_meta)
    OUTPUT_FILE.write_text(page, encoding="utf-8")
    if PREVIEW_MIRROR.parent.is_dir():
        PREVIEW_MIRROR.write_text(page, encoding="utf-8")
    total = sum(len(t["quotes"]) for t in themes)
    print(f"Wrote {OUTPUT_FILE}: {total} quotes across {len(themes)} themes")


if __name__ == "__main__":
    main()
