# Card redesign for the AI Quotes Library site

**Date:** 2026-06-26
**Status:** Approved for planning

## Goal

Restyle the static site produced by `build_site.py` from today's single-column
editorial reading list into a **grid of quote cards within each theme section**,
inspired by a clean card reference the user shared — while keeping the vault's
existing editorial serif identity rather than the reference's bold sans look.

This is a presentation-only change. The content pipeline (parsing `Quotes.md`,
`sources.json`, `authors.json` / `Sources/` frontmatter) and the data model are
untouched. Only `render()`, `render_byline()`, and the `TEMPLATE` CSS/markup in
`build_site.py` change.

## What stays the same

- Theme grouping and ordering from `Quotes.md` (numbered `01`, `02`, … headers).
- Masthead (`h1` + lede) and footer.
- Per-quote attribution: author, role, source title, and the source URL link.
- Auto dark mode via `prefers-color-scheme` (palette kept, extended to cards).
- The Playfair Display (display) + Spectral (body) + Helvetica Neue (labels)
  type system and the warm paper palette (`--bg`, `--ink`, `--muted`, etc.).
- Single self-contained HTML file; Google Fonts preconnect/link as today.

## The card design

Each theme section keeps its existing header (`theme-index` · `theme-name` ·
`theme-count`, rule underneath). Beneath it, quotes render as a **2-column grid
of cards** (`.quotes` becomes a CSS grid; 1 column on narrow screens).

Each card (`figure.quote`):

- **Sharp corners** (`border-radius: 0`), off-white surface (`--card`), 1px
  `--rule` border, soft shadow (`0 14px 30px -24px` ink).
- **Top row**, space-between:
  - **Top-left:** a large bare black Playfair quotation mark (`“`, ~5rem,
    `color: --ink`). Decorative only — `aria-hidden`.
  - **Top-right:** a 38px square outlined ↗ button linking to the source URL
    (`target=_blank rel=noopener`). When a quote has **no** source URL, the
    arrow button is omitted entirely (no dead square).
- **Quote text:** Spectral, ~1.16rem, `--ink`, `text-wrap: pretty`.
- **Byline at card bottom** (pushed down with `margin-top:auto` so cards in a
  row align): author (uppercase Helvetica label) · optional role (italic
  Spectral) · source title (italic Spectral). The title is the underlined link
  when a URL exists, else plain text. The arrow and the title point to the same
  URL — intentional redundancy (icon affordance + readable label).

### Dark mode

Extend `:root` dark block with a `--card` surface slightly lifted from `--bg`
(e.g. `#1c1a16`). Quote mark and arrow border use `--ink`; shadow softened.

## Layout / responsive

- Grid: `grid-template-columns: 1fr 1fr; gap: 18px` on the `.quotes` container.
- `max-width` of `.wrap` widens from 760px to ~960px to give two cards room.
- `@media (max-width: 700px)`: single column; existing rule hiding `.theme-index`
  and collapsing the header grid is preserved/adjusted.

## Markup changes in `build_site.py`

- `render_byline()` — restructure into the card's byline block; add the arrow
  link (only when `url` present); keep author/role/title spans and classes so
  the change is mostly CSS. Add a separate helper or inline snippet for the
  top-row (quote mark + arrow) so the `<figure>` contains: top row → blockquote
  → figcaption.
- `render()` — `.quotes` div stays as the grid container; each `figure.quote`
  gains the top row. Theme header markup unchanged.
- `TEMPLATE` — replace the quote/source CSS with the card CSS above; add
  `--card` to both light and dark `:root`; widen `.wrap`; update the mobile
  media query.

## Out of scope (YAGNI)

- Author photographs / per-author avatars (resolved: use the quote-mark glyph,
  no per-author assets).
- Filtering, search, carousel/interactivity, or masonry/variable card heights.
- Any change to `Quotes.md`, `Sources/`, `sources.json`, or `authors.json`
  formats or to the parsing logic.

## Verification

Run `python3 build_site.py`, then open `dist/index.html` (and the
`/tmp/ai-quotes-preview/` mirror via the preview server) to confirm: cards grid
within each theme, big quote glyph, arrow link present only when a URL exists,
byline intact, light + dark palettes correct, single-column on mobile.
