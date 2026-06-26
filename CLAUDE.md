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
  folder per source/publication (e.g. `Sources/Dive Club/`). Each source file begins with
  the source **URL on line 1**, followed by a blank line and then the full text / transcript
  the quotes are drawn from.
- `.obsidian/` — Obsidian app configuration. Do not hand-edit unless explicitly asked; the
  app manages these files. Sync and the `bases` plugin are enabled.

## Working conventions

- **Adding a source:** create `Sources/<Source Name>/<Author> - <Title>.md` with the URL on
  the first line, then the transcript/body. Match the existing folder-per-publication
  grouping rather than inventing a flat structure.
- **Extracting a quote:** pull the verbatim text into `Quotes.md` and attribute it back to
  its source. Use Obsidian-style wiki-links (`[[Author - Title]]`) so backlinks and the graph
  view connect quotes to their origin — the `backlink`, `outgoing-link`, and `graph` plugins
  are on and rely on this.
- Preserve quotes **verbatim**; do not paraphrase or "clean up" wording when moving text from
  a source into `Quotes.md`.
- Transcripts may contain auto-captioning artifacts (e.g. `[music]`, misheard words). Leave
  source files as-is unless asked to clean them; only tidy text when it lands in `Quotes.md`.
