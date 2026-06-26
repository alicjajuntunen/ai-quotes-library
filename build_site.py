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
from pathlib import Path

QUOTES_FILE = Path("AI quotes library/Quotes.md")
SOURCES_FILE = Path("sources.json")
OUTPUT_FILE = Path("dist/index.html")

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


def load_sources():
    if SOURCES_FILE.exists():
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {}


def render_byline(quote, sources):
    author = html.escape(quote["author"])
    url = sources.get(quote["raw"])
    if url:
        href = html.escape(url, quote=True)
        title = (
            f'<a class="title" href="{href}" target="_blank" rel="noopener">'
            f'{html.escape(quote["title"])}</a>'
        )
    else:
        title = f'<span class="title">{html.escape(quote["title"])}</span>'
    if author:
        return (
            f'<p class="source"><span class="author">{author}</span>'
            f'<span class="sep">·</span>{title}</p>'
        )
    return f'<p class="source">{title}</p>'


def render(themes, sources):
    total = sum(len(t["quotes"]) for t in themes)
    sections = []
    for t in themes:
        entries = "\n".join(
            f'        <div class="entry">\n'
            f'          <blockquote>{html.escape(q["text"])}</blockquote>\n'
            f"          {render_byline(q, sources)}\n"
            f"        </div>"
            for q in t["quotes"]
        )
        sections.append(
            f'      <section class="theme">\n'
            f'        <h2 class="theme-title">{html.escape(t["theme"])}</h2>\n'
            f"{entries}\n"
            f"      </section>"
        )
    body = "\n".join(sections)
    return TEMPLATE.format(
        body=body,
        total=total,
        themes=len(themes),
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
  .theme {{ margin-top: 7vh; }}
  .theme:first-of-type {{ margin-top: 0; }}
  .theme-title {{
    font-size: clamp(1.4rem, 3.5vw, 1.9rem);
    line-height: 1.1;
    letter-spacing: -0.01em;
    font-weight: 700;
    margin: 0 0 1vh;
    padding-bottom: 2vh;
    border-bottom: 2px solid var(--accent);
  }}
  .entry {{ padding: 3.5vh 0; border-top: 1px solid var(--rule); }}
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
      <p class="count">{total} quotes · {themes} themes</p>
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
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(render(themes, sources), encoding="utf-8")
    total = sum(len(t["quotes"]) for t in themes)
    print(f"Wrote {OUTPUT_FILE}: {total} quotes across {len(themes)} themes")


if __name__ == "__main__":
    main()
