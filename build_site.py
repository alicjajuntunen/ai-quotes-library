#!/usr/bin/env python3
"""Build a static index.html from the curated Quotes.md file.

Parses the Obsidian-style quote list:

    > "a quote"
    > — [[Author - Title]]

    > "another quote"
    > — [[Author - Title]]

and renders a single self-contained HTML page, each quote attributed back to
its source. Any `## headings` in Quotes.md are just editorial section markers
for the source file; the build flattens past them. Only Quotes.md is read; the
raw transcripts under Sources/ are never published.
"""

import html
import json
import re
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

BYLINE_RE = re.compile(r"^>\s*[—–-]?\s*\[\[(.+?)\]\]\s*$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
HEADING_RE = re.compile(r"^##\s+(.*)$")


def parse(text):
    """Return a flat list of {text, raw, author, title, theme} quotes.

    Walks the file pairing each block of quote bodies with the `[[Author -
    Title]]` byline that follows it, tagging each with the most recent `##`
    heading (its editorial theme). Non-blockquote lines other than headings are
    ignored — they only organise the source file, not the page.
    """
    quotes = []
    pending = []  # quote bodies seen but not yet attributed to a source
    theme = ""    # most recent `## heading`, stamped onto each quote
    for line in text.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            theme = heading.group(1).strip()
            continue
        byline = BYLINE_RE.match(line)
        if byline and pending:
            raw = byline.group(1).strip()
            author, _, title = raw.partition(" - ")
            for body in pending:
                quotes.append(
                    {
                        "text": body,
                        "raw": raw,
                        "author": author.strip() if title else "",
                        "title": title.strip() if title else raw,
                        "theme": theme,
                    }
                )
            pending = []
            continue
        quote = QUOTE_RE.match(line)
        if quote:
            body = quote.group(1).strip()
            if body:
                pending.append(body)
    return quotes


URL_RE = re.compile(r"https?://\S+")


def scan_source_urls():
    """Scan Sources/ for {file-stem: url}, reading the URL line per source file.

    Each source file is `--- frontmatter --- / <URL line> / blank / body`. We
    take the first URL on the first non-empty line after the frontmatter block,
    so a stray link buried in a transcript can't be mistaken for the source URL.
    Returns {} when Sources/ is absent (e.g. on CI, where transcripts are
    gitignored)."""
    urls = {}
    if not SOURCES_DIR.exists():
        return urls
    for path in SOURCES_DIR.rglob("*.md"):
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        if lines and lines[0].strip() == "---":
            i = 1
            while i < len(lines) and lines[i].strip() != "---":
                i += 1
            i += 1
        for line in lines[i:]:
            stripped = line.strip()
            if not stripped:
                continue
            match = URL_RE.search(stripped)
            if match:
                urls[path.stem] = match.group(0).rstrip('">).,')
            break  # only the first content line after frontmatter is the URL line
    return urls


def load_sources():
    """Return {file-stem: url} for linking quotes to their original source.

    Mirrors load_source_meta: when Sources/ is present (local builds) we scan
    the URL line out of each file and refresh the tracked sources.json sidecar
    from it; on CI (Sources/ absent) we fall back to that committed sidecar, so
    links still render on the deployed site. This keeps sources.json in sync
    automatically instead of by hand."""
    urls = scan_source_urls()
    if urls:
        SOURCES_FILE.write_text(
            json.dumps(urls, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return urls
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


COPY_ICON = (
    '<svg class="i-copy" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="9" y="9" width="13" height="13" rx="2"/>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
)
DONE_ICON = (
    '<svg class="i-done" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20 6 9 17l-5-5"/></svg>'
)
# Source-type glyphs prefixed to the byline so a quote's origin reads at a
# glance: a camera for video sources, a globe for everything else on the web.
VIDEO_ICON = (
    '<svg class="src-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="3" y="4" width="18" height="14" rx="2"/>'
    '<path d="M10 8.5l5 3-5 3z" fill="currentColor" stroke="none"/></svg>'
)
WEB_ICON = (
    '<svg class="src-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1"/>'
    '<path d="M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>'
)

VIDEO_HOSTS = ("youtube.com", "youtu.be")


def source_icon(url):
    """Return the byline glyph for a source URL: video camera for known video
    hosts, globe otherwise. Empty when there's no URL to classify."""
    if not url:
        return ""
    return VIDEO_ICON if any(host in url for host in VIDEO_HOSTS) else WEB_ICON


def copy_text(quote, source_meta):
    """The self-contained line placed on the clipboard: quote + attribution."""
    meta = source_meta.get(quote["raw"], {})
    author = meta.get("author") or quote["author"]
    title = quote["title"]
    line = "“" + strip_quotes(quote["text"]) + "”"
    attribution = ", ".join(p for p in (author, title) if p)
    if attribution:
        line += " — " + attribution
    return line


def search_text(quote, source_meta):
    """Lowercased haystack for live search: quote body + author name."""
    meta = source_meta.get(quote["raw"], {})
    author = meta.get("author") or quote["author"]
    return (strip_quotes(quote["text"]) + " " + author).lower().strip()


def render_card(quote, sources, source_meta):
    """One self-contained quote card: quote glyph + copy button + quote + byline."""
    return (
        f'      <figure class="quote" data-copy="{html.escape(copy_text(quote, source_meta), quote=True)}"'
        f' data-theme="{html.escape(quote.get("theme", ""), quote=True)}"'
        f' data-search="{html.escape(search_text(quote, source_meta), quote=True)}">\n'
        f'        <div class="card-top">\n'
        f'          <span class="qmark" aria-hidden="true">&ldquo;</span>\n'
        f"        </div>\n"
        f'        <div class="copy-corner">\n'
        f'          <span class="copy-flash" role="status" aria-live="polite"></span>\n'
        f'          <button class="copy-btn" type="button" aria-label="Copy quote" title="Copy quote">'
        f"{COPY_ICON}{DONE_ICON}</button>\n"
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
    icon = source_icon(url)
    if url:
        href = html.escape(url, quote=True)
        title = (
            f'<a class="title" href="{href}" target="_blank" rel="noopener">'
            f'{icon}{html.escape(quote["title"])}</a>'
        )
    else:
        title = f'<span class="title">{html.escape(quote["title"])}</span>'
    parts = []
    if author:
        parts.append(f'<span class="author">{author}</span>')
    if role:
        parts.append(f'<span class="role">{role}</span>')
    parts.append(title)
    # Each separator is glued to the end of the part it follows (one flex item
    # per "part ·") so the byline only ever wraps *between* parts — a lone "·"
    # can never get orphaned onto a new line with a leading gap before the title.
    sep = '<span class="sep">·</span>'
    inner = "".join(f'<span class="byl">{p}{sep}</span>' for p in parts[:-1]) + parts[-1]
    return f'<figcaption class="source">{inner}</figcaption>'


def ordered_themes(quotes):
    """Unique non-empty themes in first-seen (document) order."""
    seen, out = set(), []
    for q in quotes:
        t = q.get("theme", "")
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def render(quotes, sources, source_meta):
    cards = "\n".join(render_card(quote, sources, source_meta) for quote in quotes)
    themes_json = json.dumps(ordered_themes(quotes), ensure_ascii=False)
    return TEMPLATE.format(body=cards, themes=themes_json)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Quotes Library</title>
<meta name="description" content="A curated collection of notable quotes about AI, design, and craft.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Literata:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #f3f3f1;
    --ink: #1a1a18;
    --muted: #888884;
    --faint: #c6c5c1;
    --rule: #e3e2de;
    --card: #fcfcfb;
    --serif-display: "Literata", Georgia, "Times New Roman", serif;
    --serif-text: "Literata", Georgia, "Iowan Old Style", serif;
    --sans: "Helvetica Neue", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  html, body {{ height: 100%; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--serif-text);
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }}

  /* No-JS fallback: a plain, readable, centered column of every quote. */
  #field {{
    max-width: 640px;
    margin: 0 auto;
    padding: 8vh 24px 12vh;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }}

  /* Card (shared by fallback + canvas). In canvas mode the engine sets
     position/left/top/width inline; nothing here forces absolute positioning. */
  .quote {{
    position: relative;
    margin: 0;
    width: 100%;
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
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
  }}
  /* Copy control + its in-place confirmation, pinned to the card corner. */
  .copy-corner {{
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .copy-flash {{
    font-family: var(--sans);
    font-size: 0.72rem;
    letter-spacing: 0.04em;
    color: var(--muted);
    opacity: 0;
    transform: translateX(4px);
    transition: opacity 0.18s ease, transform 0.18s ease;
    pointer-events: none;
    white-space: nowrap;
  }}
  .copy-corner:has(.copy-btn.copied) .copy-flash {{
    opacity: 1;
    transform: translateX(0);
  }}
  .qmark {{
    font-family: var(--serif-display);
    font-size: 5.2rem;
    line-height: 0.8;
    color: var(--ink);
  }}
  .copy-btn {{
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    padding: 0;
    border: 1px solid var(--rule);
    border-radius: 8px;
    background: var(--bg);
    color: var(--muted);
    cursor: pointer;
    transition: color 0.18s ease, background 0.18s ease,
      border-color 0.18s ease;
  }}
  .copy-btn:hover {{
    color: var(--ink);
    background: var(--card);
    border-color: var(--muted);
  }}
  .copy-btn:focus-visible {{
    outline: none;
    border-color: var(--ink);
  }}
  .copy-btn svg {{ width: 15px; height: 15px; display: block; }}
  .copy-btn .i-done {{ display: none; color: var(--ink); }}
  .copy-btn.copied {{ color: var(--ink); border-color: var(--muted); }}
  .copy-btn.copied .i-copy {{ display: none; }}
  .copy-btn.copied .i-done {{ display: block; }}

  @media (prefers-reduced-motion: reduce) {{
    .copy-flash {{ transition: opacity 0.18s ease; transform: none; }}
    .copy-corner:has(.copy-btn.copied) .copy-flash {{ transform: none; }}
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
  /* Source-type glyph sitting just before the source title. */
  .src-icon {{
    width: 0.95em;
    height: 0.95em;
    margin-right: 0.4em;
    vertical-align: -0.14em;
    flex: 0 0 auto;
  }}
  a.title {{ text-decoration: none; transition: color 0.18s ease; }}
  a.title:hover {{ color: var(--ink); }}

  /* Canvas mode (added to <body> by the engine once it is set up). */
  body.canvas {{ overflow: hidden; }}
  /* Keep the source cards in the DOM but off-screen so the engine can measure
     them and so screen readers still reach the originals; clones fill the world. */
  body.canvas #field {{
    position: absolute;
    visibility: hidden;
    left: -100000px;
    top: 0;
    width: auto;
    max-width: none;
    padding: 0;
    margin: 0;
    height: 0;
    overflow: hidden;
  }}
  #viewport {{
    position: fixed;
    inset: 0;
    overflow: hidden;
    cursor: grab;
    touch-action: none;
    -webkit-user-select: none;
    user-select: none;
  }}
  #viewport.grabbing {{ cursor: grabbing; }}
  #world {{ position: absolute; top: 0; left: 0; will-change: transform; }}
  body.canvas #world .quote {{
    position: absolute;
    transition: transform 0.16s ease, box-shadow 0.16s ease;
  }}
  body.canvas #world .quote:hover {{
    transform: translateY(-4px);
    box-shadow: 0 20px 44px -20px rgba(0, 0, 0, 0.38);
    z-index: 5;
  }}

  #dock {{
    position: fixed;
    left: 50%;
    bottom: 22px;
    transform: translateX(-50%);
    z-index: 20;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    background: var(--ink);
    color: var(--bg);
    border: 1px solid transparent;
    border-radius: 999px;
    box-shadow: 0 12px 34px -10px rgba(0, 0, 0, 0.55);
    font-family: var(--sans);
    font-size: 0.8rem;
  }}
  .dock-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: none;
    border-radius: 999px;
    background: transparent;
    color: var(--bg);
    font: inherit;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    transition: opacity 0.22s ease, max-width 0.28s ease, padding 0.22s ease,
      background 0.18s ease, color 0.18s ease;
  }}
  .dock-btn:hover {{ background: rgba(255, 255, 255, 0.12); }}
  .dock-btn.on {{ background: var(--bg); color: var(--ink); }}
  .dock-sep {{ width: 1px; height: 16px; background: rgba(255, 255, 255, 0.18); }}
  .dock-ic {{ width: 15px; height: 15px; display: block; flex: 0 0 auto; }}
  #theme-pills {{
    position: fixed;
    left: 50%;
    bottom: 74px;
    transform: translateX(-50%);
    z-index: 19;
    width: min(560px, 92vw);
    max-height: calc(3 * 40px);
    overflow: hidden;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
  }}
  #theme-pills.open {{ opacity: 1; pointer-events: auto; }}
  .theme-pill {{
    padding: 7px 14px;
    border: none;
    border-radius: 999px;
    background: var(--ink);
    color: var(--bg);
    font-family: var(--serif-text);
    font-style: italic;
    font-size: 0.82rem;
    cursor: pointer;
    box-shadow: 0 8px 22px -10px rgba(0, 0, 0, 0.5);
    white-space: nowrap;
    opacity: 0;
    transform: translateY(10px);
    transition: opacity 0.28s ease, transform 0.28s ease,
      background 0.18s ease, color 0.18s ease;
  }}
  /* Staggered rise-in when the tray opens; pills exit together (no delay). */
  #theme-pills.open .theme-pill {{
    opacity: 1;
    transform: none;
    transition-delay: calc(var(--i, 0) * 22ms);
  }}
  .theme-pill.on {{ background: var(--bg); color: var(--ink); font-style: normal; font-weight: 500; }}
  #dock .dock-sep {{ transition: opacity 0.2s ease; }}
  #dock.searching .dock-sep {{ opacity: 0.35; }}
  #dock.searching #themes-btn,
  #dock.searching #shuffle-btn {{
    opacity: 0.5;
    padding-left: 6px;
    padding-right: 6px;
  }}
  /* Search morph: the button collapses to nothing while the field grows out of
     the same spot, so the two cross-fade in place instead of snapping. */
  #search-btn {{ max-width: 160px; }}
  #dock.searching #search-btn {{
    max-width: 0;
    padding-left: 0;
    padding-right: 0;
    opacity: 0;
    pointer-events: none;
  }}
  #dock-search {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    max-width: 0;
    padding: 6px 0;
    opacity: 0;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.14);
    pointer-events: none;
    transition: max-width 0.3s ease, opacity 0.24s ease, padding 0.24s ease;
  }}
  #dock.searching #dock-search {{
    max-width: 240px;
    padding: 6px 12px;
    opacity: 1;
    pointer-events: auto;
  }}
  #dock-search input {{
    border: none;
    background: transparent;
    color: var(--bg);
    font: inherit;
    outline: none;
    width: 170px;
  }}
  #dock-search input::placeholder {{ color: rgba(255, 255, 255, 0.5); }}
  #empty-note {{
    position: fixed;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    z-index: 15;
    font-family: var(--serif-text);
    font-style: italic;
    font-size: 1.1rem;
    color: var(--muted);
    pointer-events: none;
  }}
  #empty-note[hidden] {{ display: none; }}
  /* Dark mode: charcoal dock on a near-black bg needs a hairline to separate. */
  @media (prefers-color-scheme: dark) {{
    #dock {{ border-color: var(--rule); }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    body.canvas #world .quote {{ transition: none; }}
    .dock-btn, #dock-search, #theme-pills, .theme-pill {{ transition: none; }}
    #theme-pills.open .theme-pill {{ transition-delay: 0s; }}
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
  <main id="field">
{body}
  </main>
  <script>window.__THEMES__ = {themes};</script>
  <script>
  (function () {{
    // Copy-to-clipboard, wired at document level via delegation so it covers
    // both the static fallback cards and the cloned cards on the canvas.
    function writeClipboard(text) {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        return navigator.clipboard.writeText(text).catch(legacyCopy.bind(null, text));
      }}
      legacyCopy(text);
    }}
    function legacyCopy(text) {{
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {{ document.execCommand("copy"); }} catch (_) {{}}
      document.body.removeChild(ta);
    }}
    document.addEventListener("click", function (e) {{
      var btn = e.target.closest && e.target.closest(".copy-btn");
      if (!btn) return;
      var fig = btn.closest(".quote");
      var text = fig && fig.getAttribute("data-copy");
      if (!text) return;
      writeClipboard(text);
      var flash = btn.parentNode.querySelector(".copy-flash");
      if (flash) flash.textContent = "Copied";
      btn.classList.add("copied");
      btn.setAttribute("aria-label", "Copied");
      clearTimeout(btn._copyTimer);
      btn._copyTimer = setTimeout(function () {{
        btn.classList.remove("copied");
        btn.setAttribute("aria-label", "Copy quote");
        if (flash) flash.textContent = "";
      }}, 1400);
    }});

    var field = document.getElementById("field");
    if (!field) return;
    var cards = Array.prototype.slice.call(field.querySelectorAll(".quote"));
    if (cards.length < 2) return;

    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var GUTTER = 30, MARGIN = 48;

    function mulberry32(a) {{
      return function () {{
        a |= 0; a = (a + 0x6d2b79f5) | 0;
        var t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      }};
    }}
    var seed = (Date.now() >>> 0) || 1;
    var rnd = mulberry32(seed);

    function cardWidth() {{
      var w = window.innerWidth;
      if (w < 560) return 280;
      if (w < 900) return 320;
      return 340;
    }}

    var viewport = document.createElement("div");
    viewport.id = "viewport";
    var world = document.createElement("div");
    world.id = "world";
    viewport.appendChild(world);

    var TILE_W = 0;
    var tx = 0, ty = 0, vx = 0, vy = 0;  // vx/vy are velocities in px per second
    var raf = 0, prevFrame = 0;
    var columns = [];  // per column: {{ hk, els: [container elements] }}
    var centers = [];  // per card: {{ cx, cy, hk }} — its centre in world coords

    // Filter state. When both are empty the field is the infinite default;
    // any active filter switches layout() into finite (bounded) mode.
    var filter = {{ query: "", theme: null }};
    function filtered() {{ return !!(filter.query || filter.theme); }}
    function matches(card) {{
      if (filter.theme && card.getAttribute("data-theme") !== filter.theme) return false;
      if (filter.query) {{
        var hay = card.getAttribute("data-search") || "";
        if (hay.indexOf(filter.query) === -1) return false;
      }}
      return true;
    }}
    function visibleCards() {{
      return filtered() ? cards.filter(matches) : cards;
    }}

    // Lay cards into independent columns. Each column tiles vertically by its own
    // height (with a trailing gutter), and the columns tile horizontally by TILE_W,
    // so every gap — interior and across the wrap seam — is exactly GUTTER.
    var finite = false;      // true while a filter is active
    var boundW = 0, boundH = 0;  // finite-mode content extents (world coords)
    function layout() {{
      world.innerHTML = "";
      columns = [];
      centers = [];
      var active = visibleCards();
      finite = filtered();
      var colW = cardWidth();
      var colCount = Math.max(3, Math.min(6, Math.round(Math.sqrt(Math.max(1, active.length)))));
      TILE_W = colCount * (colW + GUTTER);

      // Shortest-column masonry: collect each column's cards and its total height.
      var colCards = [], colH = [];
      for (var i = 0; i < colCount; i++) {{ colCards.push([]); colH.push(0); }}
      for (var k = 0; k < active.length; k++) {{
        active[k].style.width = colW + "px";
        var h = active[k].offsetHeight;
        var ci = 0;
        for (var j = 1; j < colCount; j++) if (colH[j] < colH[ci]) ci = j;
        colCards[ci].push({{ card: active[k], y: colH[ci] }});
        colH[ci] += h + GUTTER;  // trailing gutter => vertical seam gap == GUTTER
      }}

      var vw = window.innerWidth, vh = window.innerHeight;
      var DI = finite ? 0 : Math.ceil(vw / TILE_W);  // horizontal copies to cover the viewport
      for (var ci2 = 0; ci2 < colCount; ci2++) {{
        var hk = colH[ci2] || (vh + GUTTER);
        var colCx = ci2 * (colW + GUTTER) + colW / 2;
        for (var mc = 0; mc < colCards[ci2].length; mc++) {{
          var ic = colCards[ci2][mc];
          centers.push({{ cx: colCx, cy: ic.y + ic.card.offsetHeight / 2, hk: hk }});
        }}
        var K = finite ? 0 : Math.max(1, Math.ceil(vh / hk));  // vertical copies per column
        var els = [];
        for (var di = 0; di <= DI; di++) {{
          var col = document.createElement("div");
          col.className = "col";
          col.style.position = "absolute";
          col.style.top = "0";
          col.style.left = (di * TILE_W + ci2 * (colW + GUTTER)) + "px";
          col.style.width = colW + "px";
          col.style.willChange = "transform";
          for (var c = 0; c <= K; c++) {{
            for (var m = 0; m < colCards[ci2].length; m++) {{
              var item = colCards[ci2][m];
              var clone = item.card.cloneNode(true);
              clone.style.width = colW + "px";
              clone.style.left = "0";
              clone.style.top = (c * hk + item.y) + "px";
              col.appendChild(clone);
            }}
          }}
          world.appendChild(col);
          els.push(col);
        }}
        columns.push({{ hk: hk, els: els }});
      }}
      if (finite) {{
        boundW = colCount * (colW + GUTTER) - GUTTER;
        boundH = 0;
        for (var bi = 0; bi < colH.length; bi++) boundH = Math.max(boundH, colH[bi] - GUTTER);
      }}
    }}

    function wrap(v, m) {{ var w = v % m; if (w > 0) w -= m; return w; }}
    function apply() {{
      var wx = finite ? tx : wrap(tx, TILE_W);
      world.style.transform = "translateX(" + wx + "px)";
      for (var i = 0; i < columns.length; i++) {{
        var wy = finite ? ty : wrap(ty, columns[i].hk);
        var els = columns[i].els;
        for (var e = 0; e < els.length; e++) {{
          els[e].style.transform = "translateY(" + wy + "px)";
        }}
      }}
    }}

    // Signed distance from v to the nearest multiple of m, in (-m/2, m/2].
    function modc(v, m) {{ if (!(m > 0)) return 0; return v - m * Math.round(v / m); }}
    // {{dx, dy}} that slides the on-screen card instance nearest the viewport
    // centre exactly onto it. The field is periodic — TILE_W across, hk down
    // each column — so a copy of every card always sits within one period of
    // centre, and shifting tx/ty by this delta lands one dead-centre.
    function nearest() {{
      var cx = window.innerWidth / 2, cy = window.innerHeight / 2;
      var bd = Infinity, bdx = 0, bdy = 0;
      for (var i = 0; i < centers.length; i++) {{
        var c = centers[i];
        var ox = modc(c.cx + tx - cx, TILE_W);
        var oy = modc(c.cy + ty - cy, c.hk);
        var d = ox * ox + oy * oy;
        if (d < bd) {{ bd = d; bdx = -ox; bdy = -oy; }}
      }}
      return {{ dx: bdx, dy: bdy }};
    }}
    function centerNow() {{ var n = nearest(); tx += n.dx; ty += n.dy; }}

    // Finite mode: allowed pan range so the block stays reachable but bounded.
    function panRange() {{
      var vw = window.innerWidth, vh = window.innerHeight;
      var minX = Math.min(0, vw - boundW - MARGIN * 2);
      var minY = Math.min(0, vh - boundH - MARGIN * 2);
      return {{ minX: minX, maxX: 0, minY: minY, maxY: 0 }};
    }}
    // Pull an out-of-range value back toward [lo, hi]; k controls softness.
    function clampSoft(v, lo, hi, k) {{
      if (v < lo) return lo + (v - lo) * k;
      if (v > hi) return hi + (v - hi) * k;
      return v;
    }}

    // FLIP animation across a filter change. layout() rebuilds #world from
    // scratch, so we can't tween the same nodes; instead we snapshot on-screen
    // card positions by quote key (data-search) BEFORE the relayout, then after
    // it slide each surviving card from its old screen spot to the new one and
    // fade+rise the newcomers. Cards filtered *out* are already gone — the
    // survivors' motion covers their absence.
    var FLIP_MS = 460, FLIP_PAD = 60;
    function onScreen(r, vh, vw) {{
      return r.bottom > -FLIP_PAD && r.top < vh + FLIP_PAD &&
             r.right > -FLIP_PAD && r.left < vw + FLIP_PAD;
    }}
    function snapshotRects() {{
      var map = {{}};
      var vw = window.innerWidth, vh = window.innerHeight;
      var els = world.querySelectorAll(".quote");
      for (var i = 0; i < els.length; i++) {{
        var r = els[i].getBoundingClientRect();
        if (!onScreen(r, vh, vw)) continue;
        var key = els[i].getAttribute("data-search");
        // Keep the instance nearest viewport centre per key (infinite mode tiles
        // multiple clones of each quote); survivors then travel the least.
        var cx = r.left + r.width / 2 - vw / 2, cy = r.top + r.height / 2 - vh / 2;
        var d = cx * cx + cy * cy;
        if (!map[key] || d < map[key].d) map[key] = {{ left: r.left, top: r.top, d: d }};
      }}
      return map;
    }}
    function playFlip(oldRects) {{
      var vw = window.innerWidth, vh = window.innerHeight;
      var els = world.querySelectorAll(".quote");
      var anim = [];
      for (var i = 0; i < els.length; i++) {{
        var el = els[i];
        var r = el.getBoundingClientRect();
        if (!onScreen(r, vh, vw)) continue;
        var old = oldRects[el.getAttribute("data-search")];
        el.style.transition = "none";
        if (old) {{
          el.style.transform = "translate(" + (old.left - r.left) + "px," + (old.top - r.top) + "px)";
        }} else {{
          el.style.transform = "translateY(16px)";
          el.style.opacity = "0";
        }}
        anim.push(el);
      }}
      void world.offsetWidth;  // flush the inverted start state before playing
      anim.forEach(function (e) {{
        e.style.transition = "transform " + FLIP_MS + "ms cubic-bezier(0.22, 0.61, 0.36, 1), " +
          "opacity " + FLIP_MS + "ms ease";
        e.style.transform = "";
        e.style.opacity = "";
        window.setTimeout(function () {{
          e.style.transition = ""; e.style.transform = ""; e.style.opacity = "";
        }}, FLIP_MS + FLIP_PAD);
      }});
    }}

    // Recompute the visible subset and relayout. Called by every dock control.
    function applyFilter() {{
      // Drop any in-flight glide/spring so a filter change starts from rest
      // instead of carrying stale velocity or a stale spring target into the
      // rebuilt layout.
      if (raf) {{ cancelAnimationFrame(raf); raf = 0; }}
      prevFrame = 0;
      var oldRects = reduce ? null : snapshotRects();  // measure BEFORE relayout
      layout();
      emptyNote.hidden = !(finite && visibleCards().length === 0);
      if (finite) {{
        tx = MARGIN; ty = MARGIN;   // land at the block's top-left with breathing room
        committed = false; vx = vy = 0;
        apply();
      }} else {{
        rnd = mulberry32(seed);
        committed = false; vx = vy = 0;
        centerNow();
        apply();
      }}
      if (oldRects) playFlip(oldRects);  // slide survivors, fade+rise newcomers
    }}

    document.body.appendChild(viewport);
    document.body.classList.add("canvas");

    // --- Dock: floating Search / Themes / Shuffle control ---------------------
    var themes = Array.isArray(window.__THEMES__) ? window.__THEMES__ : [];
    // Inline SVG glyphs (Feather/Lucide style, matching COPY_ICON et al.) so the
    // dock reads with the rest of the site rather than using emoji.
    var IC = '<svg class="dock-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
    var SEARCH_ICON = IC + '<circle cx="11" cy="11" r="8"></circle><path d="M21 21l-4.35-4.35"></path></svg>';
    var THEMES_ICON = IC + '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>';
    var SHUFFLE_ICON = IC + '<polyline points="16 3 21 3 21 8"></polyline><line x1="4" y1="20" x2="21" y2="3"></line><polyline points="21 16 21 21 16 21"></polyline><line x1="15" y1="15" x2="21" y2="21"></line><line x1="4" y1="4" x2="9" y2="9"></line></svg>';
    var dock = document.createElement("div");
    dock.id = "dock";
    var searchBtn = document.createElement("button");
    searchBtn.type = "button";
    searchBtn.className = "dock-btn";
    searchBtn.id = "search-btn";
    searchBtn.innerHTML = SEARCH_ICON + "<span>Search</span>";
    var themesBtn = document.createElement("button");
    themesBtn.type = "button";
    themesBtn.className = "dock-btn";
    themesBtn.id = "themes-btn";
    themesBtn.innerHTML = THEMES_ICON + "<span>Themes</span>";
    var shuffleBtn = document.createElement("button");
    shuffleBtn.type = "button";
    shuffleBtn.className = "dock-btn";
    shuffleBtn.id = "shuffle-btn";
    shuffleBtn.setAttribute("aria-label", "Shuffle");
    shuffleBtn.innerHTML = SHUFFLE_ICON;
    function sep() {{ var s = document.createElement("span"); s.className = "dock-sep"; return s; }}
    dock.appendChild(searchBtn); dock.appendChild(sep());
    dock.appendChild(themesBtn); dock.appendChild(sep());
    dock.appendChild(shuffleBtn);
    document.body.appendChild(dock);

    // Theme pills float above the dock; single-select.
    var pills = document.createElement("div");
    pills.id = "theme-pills";
    pills.inert = true;  // closed: not focusable/clickable (visible state is the .open class)
    themes.forEach(function (name, i) {{
      var p = document.createElement("button");
      p.type = "button";
      p.className = "theme-pill";
      p.textContent = name;
      p.dataset.name = name;  // compared in syncThemePills — independent of the label markup
      p.style.setProperty("--i", i);  // per-pill stagger index for the rise-in
      p.addEventListener("click", function () {{
        if (filter.theme === name) {{ filter.theme = null; }}  // re-click clears
        else {{ filter.theme = name; }}
        syncThemePills();
        applyFilter();
      }});
      pills.appendChild(p);
    }});
    document.body.appendChild(pills);

    var emptyNote = document.createElement("div");
    emptyNote.id = "empty-note";
    emptyNote.hidden = true;
    emptyNote.textContent = "No quotes match";
    document.body.appendChild(emptyNote);

    function syncThemePills() {{
      var kids = pills.querySelectorAll(".theme-pill");
      for (var i = 0; i < kids.length; i++) {{
        kids[i].classList.toggle("on", kids[i].dataset.name === filter.theme);
      }}
      themesBtn.classList.toggle("on", pills.classList.contains("open") || !!filter.theme);
    }}

    function openThemes() {{ pills.classList.add("open"); pills.inert = false; syncThemePills(); }}
    function closeThemes() {{ pills.classList.remove("open"); pills.inert = true; syncThemePills(); }}
    themesBtn.addEventListener("click", function () {{
      if (!pills.classList.contains("open")) {{
        if (dock.classList.contains("searching")) closeSearch();
        openThemes();
      }} else {{
        closeThemes();
      }}
    }});

    // Search morphs the button into an inline field (reusing the dock search glyph).
    var searchWrap = document.createElement("span");
    searchWrap.id = "dock-search";
    searchWrap.innerHTML = SEARCH_ICON;
    var searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search quotes";
    searchInput.setAttribute("aria-label", "Search quotes");
    searchWrap.appendChild(searchInput);
    dock.insertBefore(searchWrap, searchBtn);

    function openSearch() {{
      closeThemes();
      dock.classList.add("searching");
      searchInput.focus();
    }}
    function closeSearch() {{
      searchInput.value = "";                 // clear before hiding so a reopen shows no stale text
      dock.classList.remove("searching");
      if (filter.query) {{ filter.query = ""; applyFilter(); }}
    }}
    searchBtn.addEventListener("click", openSearch);
    searchInput.addEventListener("input", function () {{
      filter.query = searchInput.value.trim().toLowerCase();
      applyFilter();
    }});
    searchInput.addEventListener("keydown", function (e) {{
      if (e.key === "Escape") {{ closeSearch(); searchInput.blur(); }}
    }});
    searchInput.addEventListener("blur", function () {{
      if (!filter.query) closeSearch();  // empty field on blur restores resting pill
    }});

    // Shuffle cancels any active filter, returns to the infinite field, and
    // springs to a random quote.
    shuffleBtn.addEventListener("click", function () {{
      filter.query = ""; filter.theme = null;
      searchInput.value = "";
      dock.classList.remove("searching");
      closeThemes();
      if (raf) {{ cancelAnimationFrame(raf); raf = 0; }}
      prevFrame = 0;
      layout();
      tx = -rnd() * TILE_W;
      ty = -rnd() * (columns.length ? columns[0].hk : 600);
      centerNow();
      committed = false; vx = vy = 0;
      if (!reduce) startLoop(); else apply();
    }});

    layout();
    tx = -rnd() * TILE_W;
    ty = -rnd() * (columns.length ? columns[0].hk : 600);
    centerNow();  // open resting on a centred quote
    apply();

    // Card heights — and therefore every baked top — depend on the webfont.
    // The first layout runs before Literata (display=swap) has loaded, so it
    // measures fallback-font heights; once the real font swaps in each card
    // grows and the frozen tops drift out of true, making gutters uneven. Lay
    // out once more when the font is ready so positions match the final metrics.
    if (document.fonts && document.fonts.ready) {{
      document.fonts.ready.then(function () {{
        layout();
        if (!dragging && !raf) centerNow();
        apply();
      }});
    }}

    var dragging = false, lastX = 0, lastY = 0, lastT = 0;
    var startX = 0, startY = 0, moved = false;

    // Magnet tuning, all rescaled by real elapsed time each frame so the feel is
    // identical on 60 Hz and 120 Hz displays.
    //   MOM_DECAY  — inertia retained per 1/60 s during the free glide.
    //   COMMIT_V   — once the glide slows below this (px/s) we lock onto the
    //                nearest quote and spring to it; above it motion stays free.
    //   OMEGA      — spring stiffness (rad/s). Critically damped, so it eases in
    //                and out and never overshoots/oscillates — the un-snappy part.
    //   DRAG_PULL / DRAG_V — a soft assist while dragging: it only wakes up below
    //                DRAG_V (px/s), so steady panning tracks the finger 1:1 and a
    //                pause lets the nearest quote drift gently to centre.
    var MOM_DECAY = 0.94, COMMIT_V = 300, OMEGA = 8.5;
    var DRAG_PULL = 0.05, DRAG_V = 240;
    var committed = false, targetTx = 0, targetTy = 0;

    viewport.addEventListener("pointerdown", function (e) {{
      // Reset the drag-distance flag for every press: otherwise a stale
      // moved===true left over from the last canvas drag makes the capture-phase
      // click suppressor (below) eat the next copy-button click.
      moved = false;
      // Let the copy button and source links receive a clean click instead of
      // starting a drag. setPointerCapture (below) retargets the click to the
      // viewport, so anything that relies on the click reaching its own element
      // — the delegated copy handler, an <a>'s native navigation — must skip it.
      if (e.target.closest && e.target.closest(".copy-btn, a[href]")) return;
      dragging = true;
      try {{ viewport.setPointerCapture(e.pointerId); }} catch (_) {{}}
      startX = lastX = e.clientX; startY = lastY = e.clientY;
      lastT = performance.now(); vx = vy = 0;
      committed = false;  // grabbing again drops any in-flight spring target
      viewport.classList.add("grabbing");
      if (!reduce) startLoop();  // run the magnet for the gentle in-drag pull
    }});

    viewport.addEventListener("pointermove", function (e) {{
      if (!dragging) return;
      var dx = e.clientX - lastX, dy = e.clientY - lastY;
      tx += dx; ty += dy;
      var now = performance.now(), dt = now - lastT || 16;
      // Track velocity in px/s, lightly smoothed so a jittery trackpad doesn't
      // turn into a jittery fling on release.
      var nvx = (dx / dt) * 1000, nvy = (dy / dt) * 1000;
      vx = vx * 0.5 + nvx * 0.5; vy = vy * 0.5 + nvy * 0.5;
      lastX = e.clientX; lastY = e.clientY; lastT = now;
      if (Math.abs(e.clientX - startX) + Math.abs(e.clientY - startY) > 6) moved = true;
      apply();
    }});

    function endDrag(e) {{
      if (!dragging) return;
      dragging = false;
      viewport.classList.remove("grabbing");
      try {{ viewport.releasePointerCapture(e.pointerId); }} catch (_) {{}}
      if (reduce) {{ centerNow(); apply(); }}  // reduced motion: settle instantly
      else startLoop();
    }}
    viewport.addEventListener("pointerup", endDrag);
    viewport.addEventListener("pointercancel", endDrag);

    // The motion loop. Three smooth regimes, no abrupt hand-offs:
    //   dragging  — the finger owns position; a soft spring only assists once you
    //               slow below DRAG_V, so steady panning is 1:1 and a pause drifts
    //               the nearest quote to centre.
    //   gliding   — after release, free inertia (no pull) until it slows to
    //               COMMIT_V, at which point we lock onto the nearest quote.
    //   settling  — a critically-damped spring eases into that committed quote and
    //               stops. Critical damping means it never overshoots or buzzes,
    //               which is what kills the old snap/jitter.
    function tick(now) {{
      var dt = prevFrame ? Math.min((now - prevFrame) / 1000, 0.05) : 1 / 60;
      prevFrame = now;
      var frames = dt * 60;

      if (dragging) {{
        // Idle velocity bleeds off so a held pause wakes the assist.
        var hold = Math.pow(0.02, dt);
        vx *= hold; vy *= hold;
        var dspeed = Math.sqrt(vx * vx + vy * vy);
        var gate = Math.max(0, 1 - dspeed / DRAG_V);
        var kEff = (1 - Math.pow(1 - DRAG_PULL, frames)) * gate * gate;
        if (!finite && kEff > 0) {{ var nd = nearest(); tx += nd.dx * kEff; ty += nd.dy * kEff; }}
        if (finite) {{
          var r = panRange();
          tx = clampSoft(tx, r.minX, r.maxX, 0.5);
          ty = clampSoft(ty, r.minY, r.maxY, 0.5);
        }}
        apply();
        raf = requestAnimationFrame(tick);
        return;
      }}

      if (finite) {{
        // Momentum decay, a spring that pulls any out-of-range axis back to
        // bound, then a SINGLE position integration — matching the committed
        // branch below. Integrating before and after the spring (as an earlier
        // version did) doubles the per-frame step and overshoots the boundary.
        var md2 = Math.pow(MOM_DECAY, frames);
        vx *= md2; vy *= md2;
        var r2 = panRange();
        var tgx = Math.min(r2.maxX, Math.max(r2.minX, tx));
        var tgy = Math.min(r2.maxY, Math.max(r2.minY, ty));
        var ox = tx - tgx, oy = ty - tgy;
        if (ox || oy) {{
          vx += (-OMEGA * OMEGA * ox - 2 * OMEGA * vx) * dt;
          vy += (-OMEGA * OMEGA * oy - 2 * OMEGA * vy) * dt;
        }}
        tx += vx * dt; ty += vy * dt;
        apply();
        // Converged when in-bounds and nearly stopped — measured on the final
        // (post-integration) position, not the pre-step offset.
        var fx = tx - Math.min(r2.maxX, Math.max(r2.minX, tx));
        var fy = ty - Math.min(r2.maxY, Math.max(r2.minY, ty));
        if (Math.abs(fx) < 0.3 && Math.abs(fy) < 0.3 &&
            Math.sqrt(vx * vx + vy * vy) < 4) {{ raf = 0; prevFrame = 0; return; }}
        raf = requestAnimationFrame(tick);
        return;
      }}

      if (!committed) {{
        tx += vx * dt; ty += vy * dt;            // free inertia glide
        var md = Math.pow(MOM_DECAY, frames);
        vx *= md; vy *= md;
        if (Math.sqrt(vx * vx + vy * vy) < COMMIT_V) {{
          var n = nearest();                     // lock onto one quote, once
          targetTx = tx + n.dx; targetTy = ty + n.dy;
          committed = true;
        }}
      }}

      if (committed) {{
        // Critically-damped spring (damping = 2*sqrt(stiffness)) toward the target.
        var ex = tx - targetTx, ey = ty - targetTy;
        vx += (-OMEGA * OMEGA * ex - 2 * OMEGA * vx) * dt;
        vy += (-OMEGA * OMEGA * ey - 2 * OMEGA * vy) * dt;
        tx += vx * dt; ty += vy * dt;
        if (Math.abs(tx - targetTx) < 0.3 && Math.abs(ty - targetTy) < 0.3 &&
            Math.sqrt(vx * vx + vy * vy) < 4) {{
          tx = targetTx; ty = targetTy; apply();
          committed = false; raf = 0; prevFrame = 0;
          return;
        }}
      }}

      apply();
      raf = requestAnimationFrame(tick);
    }}
    function startLoop() {{ if (!raf) {{ prevFrame = 0; raf = requestAnimationFrame(tick); }} }}

    viewport.addEventListener("click", function (e) {{
      if (moved) {{ e.preventDefault(); e.stopPropagation(); }}
    }}, true);

    var rt = 0;
    window.addEventListener("resize", function () {{
      clearTimeout(rt);
      rt = setTimeout(function () {{
        rnd = mulberry32(seed);
        layout();
        if (!dragging && !raf) centerNow();
        apply();
      }}, 200);
    }});
  }})();
  </script>
</body>
</html>
"""


def main():
    text = QUOTES_FILE.read_text(encoding="utf-8")
    quotes = parse(text)
    sources = load_sources()
    source_meta = load_source_meta()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    page = render(quotes, sources, source_meta)
    OUTPUT_FILE.write_text(page, encoding="utf-8")
    if PREVIEW_MIRROR.parent.is_dir():
        PREVIEW_MIRROR.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}: {len(quotes)} quotes")


if __name__ == "__main__":
    main()
