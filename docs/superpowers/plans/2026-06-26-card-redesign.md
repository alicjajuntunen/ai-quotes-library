# Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the generated site into a grid of editorial quote cards within each theme section, keeping the existing serif identity, sharp corners, big quote-mark glyph, square source-link arrow, and auto dark mode.

**Architecture:** Presentation-only change to `build_site.py`. The parser, data files (`Quotes.md`, `sources.json`, `authors.json`, `Sources/`), and data model are untouched. We add a `render_cardtop()` helper, insert a card top-row into the `<figure>` markup in `render()`, and rewrite the relevant CSS in `TEMPLATE`. Verification is by building and visually inspecting the output — this repo has no unit-test tooling.

**Tech Stack:** Python 3 standard library (no deps), inline HTML/CSS template, Google Fonts (Playfair Display + Spectral).

---

## File Structure

- Modify: `build_site.py` — only `render_byline()` neighborhood (new `render_cardtop()` helper), `render()` figure markup, and the `TEMPLATE` `<style>` block. No other files change.

The change is small and localized to one file; no new files or restructuring.

---

### Task 1: Add the card top-row helper and wire it into `render()`

**Files:**
- Modify: `build_site.py` (add `render_cardtop()` near `render_byline()` ~line 126; edit the `<figure>` markup in `render()` ~lines 153–159)

- [ ] **Step 1: Add the `render_cardtop` helper**

Insert this function immediately above `def render_byline(` (around line 126):

```python
def render_cardtop(quote, sources):
    """Top row of a card: a big quote-mark glyph and, when the quote has a
    source URL, a square arrow link to it. The arrow is omitted entirely when
    there is no URL, so no dead button is rendered."""
    url = sources.get(quote["raw"])
    arrow = ""
    if url:
        href = html.escape(url, quote=True)
        arrow = (
            f'<a class="arrow" href="{href}" target="_blank" rel="noopener" '
            f'aria-label="Open source">'
            f'<svg viewBox="0 0 24 24" width="17" height="17" fill="none" '
            f'stroke="currentColor" stroke-width="1.6">'
            f'<path d="M7 17 17 7M9 7h8v8"/></svg></a>'
        )
    return (
        f'<div class="card-top">'
        f'<span class="qmark" aria-hidden="true">&ldquo;</span>'
        f"{arrow}"
        f"</div>"
    )
```

- [ ] **Step 2: Insert the top row into the figure markup in `render()`**

In `render()`, the per-quote `entries` join currently builds:

```python
        entries = "\n".join(
            f'          <figure class="quote">\n'
            f'            <blockquote>{html.escape(q["text"])}</blockquote>\n'
            f"            {render_byline(q, sources, source_meta)}\n"
            f"          </figure>"
            for q in t["quotes"]
        )
```

Replace it with (adds the card-top line before the blockquote):

```python
        entries = "\n".join(
            f'          <figure class="quote">\n'
            f"            {render_cardtop(q, sources)}\n"
            f'            <blockquote>{html.escape(q["text"])}</blockquote>\n'
            f"            {render_byline(q, sources, source_meta)}\n"
            f"          </figure>"
            for q in t["quotes"]
        )
```

- [ ] **Step 3: Verify the script still runs and emits the new markup**

Run: `python3 "build_site.py"`
Expected: prints `Wrote dist/index.html: N quotes across M themes` (no traceback).

Run: `grep -c 'class="card-top"' dist/index.html`
Expected: a number equal to the total quote count printed above.

Run: `grep -c 'class="qmark"' dist/index.html`
Expected: same total quote count (one glyph per card).

- [ ] **Step 4: Commit**

```bash
git add build_site.py
git commit -m "Add card top-row (quote glyph + source arrow) to quote markup"
```

---

### Task 2: Rewrite the `TEMPLATE` CSS for the card grid

**Files:**
- Modify: `build_site.py` — the `:root` blocks, `.wrap`, the Quotes section CSS, and the mobile media query inside `TEMPLATE` (~lines 193–344)

- [ ] **Step 1: Add a `--card` surface to both palettes**

In the light `:root` (after `--rule: #e0dccf;`, ~line 197) add:

```css
    --card: #fffdf8;
```

In the dark `:root` block (`@media (prefers-color-scheme: dark)`, after `--rule: #2c2a23;`, ~line 342) add:

```css
      --card: #1c1a16;
```

- [ ] **Step 2: Widen the content column**

Change `.wrap` (~line 214) `max-width` from `760px` to `960px`:

```css
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 14vh 28px 20vh; }}
```

(Note: braces are doubled because `TEMPLATE` is a `str.format` string — match the surrounding style exactly.)

- [ ] **Step 3: Replace the Quotes CSS block with card + grid styles**

Find the block beginning `/* Quotes */` and ending just before `footer {{` (currently `.quotes`, `.quote`, `.quote:last-child`, `blockquote`, `.source`, `.source .author`, `.source .role`, `.source .title`, `.source .sep`, `a.title`, `a.title:hover`, ~lines 269–317). Replace that entire block with:

```css
  /* Quotes — card grid */
  .quotes {{
    margin-top: 2rem;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
  }}
  .quote {{
    margin: 0;
    display: flex;
    flex-direction: column;
    padding: 18px 26px 22px;
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 0;
    box-shadow: 0 14px 30px -24px rgba(24, 23, 18, 0.5);
  }}
  .card-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .qmark {{
    font-family: var(--serif-display);
    font-size: 5.2rem;
    line-height: 0.8;
    color: var(--ink);
  }}
  .arrow {{
    width: 38px;
    height: 38px;
    margin-top: 14px;
    border: 1px solid var(--ink);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    transition: background 0.18s ease, color 0.18s ease;
  }}
  .arrow:hover {{ background: var(--ink); color: var(--card); }}
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
    border-bottom: 1px solid var(--faint);
    transition: border-color 0.18s ease, color 0.18s ease;
  }}
  a.title:hover {{ color: var(--ink); border-bottom-color: var(--ink); }}
```

- [ ] **Step 4: Update the mobile media query to a single column**

Replace the existing `@media (max-width: 600px)` block (~lines 330–334) with:

```css
  @media (max-width: 700px) {{
    .wrap {{ padding: 9vh 20px 14vh; }}
    .quotes {{ grid-template-columns: 1fr; }}
    .theme-head {{ grid-template-columns: 1fr auto; }}
    .theme-index {{ display: none; }}
  }}
```

- [ ] **Step 5: Rebuild**

Run: `python3 "build_site.py"`
Expected: `Wrote dist/index.html: N quotes across M themes` (no traceback).

Run: `grep -c 'grid-template-columns: 1fr 1fr' dist/index.html`
Expected: `1` (the `.quotes` grid rule is present).

- [ ] **Step 6: Commit**

```bash
git add build_site.py
git commit -m "Restyle site as editorial card grid within theme sections"
```

---

### Task 3: Visual verification in the preview server

**Files:** none (verification only)

- [ ] **Step 1: Ensure the preview mirror exists and rebuild**

The build writes a preview mirror to `/tmp/ai-quotes-preview/index.html` only if that directory already exists. Create it, then rebuild so the mirror is fresh:

Run: `mkdir -p /tmp/ai-quotes-preview && python3 "build_site.py"`
Expected: build prints its summary line; `/tmp/ai-quotes-preview/index.html` now exists.

- [ ] **Step 2: Start/point the preview server at the output and load it**

Use the `Claude_Preview` MCP tools (`preview_start`, then `preview_snapshot` / `preview_screenshot`). Load the built `dist/index.html` (or the `/tmp` mirror the sandboxed server can read).

- [ ] **Step 3: Confirm the design against the spec**

Verify visually and via `preview_snapshot`:
- Each theme section shows a 2-column grid of cards (sharp corners, off-white surface, border + soft shadow).
- A large black quote glyph sits top-left of every card.
- The square ↗ arrow appears top-right **only** on cards whose quote has a source URL; cards without a URL have no arrow.
- Byline at the card bottom shows author · optional role · source title (title underlined and linking out when a URL exists).
- `preview_resize` to a narrow width → single column; theme index hidden.
- Toggle dark mode (`preview_eval` emulating `prefers-color-scheme: dark`, or `preview_resize`/emulation) → cards use the lifted `--card` dark surface; text/borders legible.

- [ ] **Step 4: Capture proof and report**

Take `preview_screenshot` of a theme section in both light and dark, plus a narrow-width shot. Share with the user. No commit (verification only).

---

## Self-Review

**Spec coverage:**
- Card grid within theme sections → Task 2 Step 3 (`.quotes` grid) + Task 1 markup. ✓
- Editorial serif identity / sharp corners kept → `border-radius: 0`, existing font vars reused. ✓
- Big bare black quote mark top-left → `.qmark` (Task 2 S3) + glyph (Task 1 S1). ✓
- Square ↗ source link top-right, omitted when no URL → `render_cardtop` (Task 1 S1). ✓
- Byline author · role · linked title at bottom → `.source { margin-top:auto }` + unchanged `render_byline`. ✓
- Auto dark mode + lifted card surface → `--card` in both `:root` blocks (Task 2 S1). ✓
- Wider column for two cards → `.wrap` max-width 960px (Task 2 S2). ✓
- Single column on mobile → media query (Task 2 S4). ✓
- Parsing/data files untouched → only `build_site.py` render/template touched. ✓

**Placeholder scan:** No TBD/TODO; all code shown in full. ✓

**Type consistency:** `render_cardtop(quote, sources)` is called in `render()` with `(q, sources)`; matches signature. Class names `card-top`, `qmark`, `arrow` used identically in markup (Task 1) and CSS (Task 2). `--card` defined before use. ✓
