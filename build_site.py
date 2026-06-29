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
    var tx = 0, ty = 0, vx = 0, vy = 0;
    var raf = 0;
    var columns = [];  // per column: {{ hk, els: [container elements] }}

    // Lay cards into independent columns. Each column tiles vertically by its own
    // height (with a trailing gutter), and the columns tile horizontally by TILE_W,
    // so every gap — interior and across the wrap seam — is exactly GUTTER.
    function layout() {{
      world.innerHTML = "";
      columns = [];
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

    document.body.appendChild(viewport);
    document.body.classList.add("canvas");
    layout();
    tx = -rnd() * TILE_W;
    ty = -rnd() * (columns.length ? columns[0].hk : 600);
    apply();

    // Card heights — and therefore every baked top — depend on the webfont.
    // The first layout runs before Literata (display=swap) has loaded, so it
    // measures fallback-font heights; once the real font swaps in each card
    // grows and the frozen tops drift out of true, making gutters uneven. Lay
    // out once more when the font is ready so positions match the final metrics.
    if (document.fonts && document.fonts.ready) {{
      document.fonts.ready.then(function () {{ layout(); apply(); }});
    }}

    var dragging = false, lastX = 0, lastY = 0, lastT = 0;
    var startX = 0, startY = 0, moved = false;

    viewport.addEventListener("pointerdown", function (e) {{
      // Reset the drag-distance flag for every press: otherwise a stale
      // moved===true left over from the last canvas drag makes the capture-phase
      // click suppressor (below) eat the next copy-button click.
      moved = false;
      // Let the copy button receive a clean click instead of starting a drag.
      if (e.target.closest && e.target.closest(".copy-btn")) return;
      dragging = true;
      try {{ viewport.setPointerCapture(e.pointerId); }} catch (_) {{}}
      startX = lastX = e.clientX; startY = lastY = e.clientY;
      lastT = performance.now(); vx = vy = 0;
      if (raf) cancelAnimationFrame(raf);
      viewport.classList.add("grabbing");
    }});

    viewport.addEventListener("pointermove", function (e) {{
      if (!dragging) return;
      var dx = e.clientX - lastX, dy = e.clientY - lastY;
      tx += dx; ty += dy;
      var now = performance.now(), dt = now - lastT || 16;
      vx = (dx / dt) * 16; vy = (dy / dt) * 16;
      lastX = e.clientX; lastY = e.clientY; lastT = now;
      if (Math.abs(e.clientX - startX) + Math.abs(e.clientY - startY) > 6) moved = true;
      apply();
    }});

    function endDrag(e) {{
      if (!dragging) return;
      dragging = false;
      viewport.classList.remove("grabbing");
      try {{ viewport.releasePointerCapture(e.pointerId); }} catch (_) {{}}
      if (!reduce) momentum();
    }}
    viewport.addEventListener("pointerup", endDrag);
    viewport.addEventListener("pointercancel", endDrag);

    function momentum() {{
      if (Math.abs(vx) < 0.1 && Math.abs(vy) < 0.1) return;
      tx += vx; ty += vy; vx *= 0.94; vy *= 0.94;
      apply();
      raf = requestAnimationFrame(momentum);
    }}

    viewport.addEventListener("click", function (e) {{
      if (moved) {{ e.preventDefault(); e.stopPropagation(); }}
    }}, true);

    var rt = 0;
    window.addEventListener("resize", function () {{
      clearTimeout(rt);
      rt = setTimeout(function () {{
        rnd = mulberry32(seed);
        layout();
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
