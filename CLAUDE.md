# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

This is an **Obsidian vault**, not a software project. There is no build, lint, or test
tooling — work happens entirely in Markdown files. The purpose of the vault is to collect
notable quotes about AI (and the surrounding design/craft conversation) along with the
sources they came from.

## Layout

The actual vault lives one level down, inside `AI quotes library/` (the working directory
contains a single nested folder of the same name). All content paths below are relative to
that vault root:

- `Quotes.md` — the central, hand-curated list of extracted quotes. This is the primary
  deliverable; sources exist to feed it.
- `Sources/<Source Name>/<Author> - <Title>.md` — one file per source, grouped into a
  folder per source/publication (e.g. `Sources/Dive Club/`). Each source file begins with a
  YAML frontmatter block carrying `author` and `role` (the speaker/writer and their title +
  org, e.g. `role: Chief Design Officer, Figma`), then the source **URL** line, a blank line,
  and the full text / transcript the quotes are drawn from. `role` may be left empty when
  unknown.
- `.obsidian/` — Obsidian app configuration. Do not hand-edit unless explicitly asked; the
  app manages these files. Sync and the `bases` plugin are enabled.

## Working conventions

- **Adding a source:** create `Sources/<Source Name>/<Author> - <Title>.md` beginning with
  `author`/`role` frontmatter, then the URL line, a blank line, and the transcript/body. Match
  the existing folder-per-publication grouping rather than inventing a flat structure. The site
  build (`build_site.py`) reads `author`/`role` from this frontmatter — only the frontmatter,
  never the transcript — to attribute each quote, and reads the URL line (the first content line
  after the frontmatter) to link each quote to its original source. Because `Sources/` is
  gitignored, the build writes two tracked sidecars from the source files: `authors.json` (from
  the `author`/`role` frontmatter) and `sources.json` (the `{Author - Title: URL}` map). CI
  (which has no `Sources/`) renders roles and source links from these. So after adding/editing a
  source's frontmatter or URL line, run `python3 build_site.py` and commit the updated
  `authors.json` **and** `sources.json` for roles and links to reach the live site.
- **Extracting a quote:** pull the verbatim text into `Quotes.md` and attribute it back to
  its source. Use Obsidian-style wiki-links (`[[Author - Title]]`) so backlinks and the graph
  view connect quotes to their origin — the `backlink`, `outgoing-link`, and `graph` plugins
  are on and rely on this.
- Preserve quotes **verbatim**; do not paraphrase or "clean up" wording when moving text from
  a source into `Quotes.md`.
- Transcripts may contain auto-captioning artifacts (e.g. `[music]`, misheard words). Leave
  source files as-is unless asked to clean them; only tidy text when it lands in `Quotes.md`.
