#!/usr/bin/env python3
"""Build a static index.html from the curated Quotes.md file.

Parses the Obsidian-style quote list:

    ## [[Author - Title]]
    > "a quote"
    > "another quote"

and renders a single self-contained HTML page grouped by source.
Only Quotes.md is read; the raw transcripts under Sources/ are never published.
"""

import html
import json
import re
from pathlib import Path

QUOTES_FILE = Path("AI quotes library/Quotes.md")
SOURCES_FILE = Path("sources.json")
OUTPUT_FILE = Path("dist/index.html")

HEADER_RE = re.compile(r"^##\s*\[\[(.+?)\]\]\s*$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")


def parse(text):
    """Return a list of {author, title, raw, quotes:[...]} groups."""
    groups = []
    current = None
    for line in text.splitlines():
        header = HEADER_RE.match(line)
        if header:
            raw = header.group(1).strip()
            author, _, title = raw.partition(" - ")
            current = {
                "raw": raw,
                "author": author.strip() if title else "",
                "title": title.strip() if title else raw,
                "quotes": [],
            }
            groups.append(current)
            continue
        quote = QUOTE_RE.match(line)
        if quote and current is not None:
            body = quote.group(1).strip()
            if body:
                current["quotes"].append(body)
    return [g for g in groups if g["quotes"]]


def load_sources():
    if SOURCES_FILE.exists():
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {}


def render(groups, sources):
    total = sum(len(g["quotes"]) for g in groups)
    sections = []
    for g in groups:
        quotes_html = "\n".join(
            f"        <blockquote>{html.escape(q)}</blockquote>" for q in g["quotes"]
        )
        author = html.escape(g["author"])
        url = sources.get(g["raw"])
        if url:
            href = html.escape(url, quote=True)
            title = (
                f'<a class="title" href="{href}" target="_blank" rel="noopener">'
                f'{html.escape(g["title"])}</a>'
            )
        else:
            title = f'<span class="title">{html.escape(g["title"])}</span>'
        byline = (
            f'<p class="source"><span class="author">{author}</span>'
            f'<span class="sep">·</span>{title}</p>'
            if author
            else f'<p class="source">{title}</p>'
        )
        sections.append(
            f'      <section class="entry">\n{quotes_html}\n        {byline}\n      </section>'
        )
    body = "\n".join(sections)
    return TEMPLATE.format(
        body=body,
        total=total,
        sources=len(groups),
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Quotes Library</title>
<meta name="description" content="A curated collection of notable quotes about AI, design, and craft.">
<style>
  :root {{
    --bg: #f6f4ef;
    --ink: #1c1b19;
    --muted: #6b6760;
    --rule: #d9d4ca;
    --accent: #b4541f;
  }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
    line-height: 1.5;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 8vh 24px 16vh; }}
  header {{ margin-bottom: 7vh; }}
  h1 {{
    font-size: clamp(2.2rem, 6vw, 3.4rem);
    line-height: 1.05;
    letter-spacing: -0.02em;
    margin: 0 0 0.6rem;
    font-weight: 700;
  }}
  .lede {{ color: var(--muted); font-size: 1.05rem; margin: 0; font-style: italic; }}
  .count {{
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-style: normal;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-top: 1.4rem;
  }}
  .entry {{ padding: 4vh 0; border-top: 1px solid var(--rule); }}
  .entry:first-of-type {{ border-top: none; }}
  blockquote {{
    margin: 0 0 1.4rem;
    font-size: 1.3rem;
    line-height: 1.45;
    text-indent: -0.5em;
  }}
  blockquote:last-of-type {{ margin-bottom: 1.6rem; }}
  .source {{
    margin: 0;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 0.82rem;
    letter-spacing: 0.02em;
    color: var(--muted);
  }}
  .source .author {{ color: var(--ink); }}
  .source .sep {{ margin: 0 0.5em; opacity: 0.5; }}
  .source a.title {{
    color: var(--accent);
    text-decoration: none;
    border-bottom: 1px solid transparent;
  }}
  .source a.title:hover {{ border-bottom-color: currentColor; }}
  footer {{
    margin-top: 10vh;
    padding-top: 4vh;
    border-top: 1px solid var(--rule);
    color: var(--muted);
    font-size: 0.85rem;
  }}
  footer a {{ color: var(--accent); }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #16150f; --ink: #ece8df; --muted: #9c968a;
      --rule: #34322a; --accent: #e08a4e;
    }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AI Quotes Library</h1>
      <p class="lede">Notable quotes on AI, design, and craft.</p>
      <p class="count">{total} quotes · {sources} sources</p>
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
    groups = parse(text)
    sources = load_sources()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(render(groups, sources), encoding="utf-8")
    total = sum(len(g["quotes"]) for g in groups)
    print(f"Wrote {OUTPUT_FILE}: {total} quotes from {len(groups)} sources")


if __name__ == "__main__":
    main()
