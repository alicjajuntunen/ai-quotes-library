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


def parse(text):
    """Return a flat list of {text, raw, author, title} quotes.

    Walks the file pairing each block of quote bodies with the `[[Author -
    Title]]` byline that follows it. `## headings` and other non-blockquote
    lines are ignored — they only organise the source file, not the page.
    """
    quotes = []
    pending = []  # quote bodies seen but not yet attributed to a source
    for line in text.splitlines():
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


def render_card(quote, sources, source_meta):
    """One self-contained quote card: quote glyph + copy button + quote + byline."""
    return (
        f'      <figure class="quote" data-copy="{html.escape(copy_text(quote, source_meta), quote=True)}">\n'
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


def render(quotes, sources, source_meta):
    cards = "\n".join(render_card(quote, sources, source_meta) for quote in quotes)
    return TEMPLATE.format(body=cards)


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

  @media (prefers-reduced-motion: reduce) {{
    body.canvas #world .quote {{ transition: none; }}
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

    // Lay cards into independent columns. Each column tiles vertically by its own
    // height (with a trailing gutter), and the columns tile horizontally by TILE_W,
    // so every gap — interior and across the wrap seam — is exactly GUTTER.
    function layout() {{
      world.innerHTML = "";
      columns = [];
      centers = [];
      var colW = cardWidth();
      var colCount = Math.max(3, Math.min(6, Math.round(Math.sqrt(cards.length))));
      TILE_W = colCount * (colW + GUTTER);

      // Shortest-column masonry: collect each column's cards and its total height.
      var colCards = [], colH = [];
      for (var i = 0; i < colCount; i++) {{ colCards.push([]); colH.push(0); }}
      for (var k = 0; k < cards.length; k++) {{
        cards[k].style.width = colW + "px";
        var h = cards[k].offsetHeight;
        var ci = 0;
        for (var j = 1; j < colCount; j++) if (colH[j] < colH[ci]) ci = j;
        colCards[ci].push({{ card: cards[k], y: colH[ci] }});
        colH[ci] += h + GUTTER;  // trailing gutter => vertical seam gap == GUTTER
      }}

      var vw = window.innerWidth, vh = window.innerHeight;
      var DI = Math.ceil(vw / TILE_W);  // horizontal copies to cover the viewport
      for (var ci2 = 0; ci2 < colCount; ci2++) {{
        var hk = colH[ci2] || (vh + GUTTER);
        var colCx = ci2 * (colW + GUTTER) + colW / 2;
        for (var mc = 0; mc < colCards[ci2].length; mc++) {{
          var ic = colCards[ci2][mc];
          centers.push({{ cx: colCx, cy: ic.y + ic.card.offsetHeight / 2, hk: hk }});
        }}
        var K = Math.max(1, Math.ceil(vh / hk));  // vertical copies per column
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
    }}

    function wrap(v, m) {{ var w = v % m; if (w > 0) w -= m; return w; }}
    function apply() {{
      world.style.transform = "translateX(" + wrap(tx, TILE_W) + "px)";
      for (var i = 0; i < columns.length; i++) {{
        var wy = wrap(ty, columns[i].hk);
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

    document.body.appendChild(viewport);
    document.body.classList.add("canvas");
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
        if (kEff > 0) {{ var nd = nearest(); tx += nd.dx * kEff; ty += nd.dy * kEff; }}
        apply();
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
