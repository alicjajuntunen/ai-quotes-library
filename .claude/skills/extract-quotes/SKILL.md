---
name: extract-quotes
description: >-
  Extract insightful, surprising, and thought-provoking quotes from one or more
  source files in this AI-quotes Obsidian vault, then present them in an inline
  accept/reject card UI so the user can curate which ones get added to Quotes.md.
  Use this whenever the user points at a source (a file under Sources/, or names
  a talk/article/transcript already in the vault) and wants to pull quotes from
  it, harvest highlights, find the best lines, mine it for quotes, or "go through"
  a source — even if they don't say the word "extract". This is the right skill
  for turning raw transcripts into curated, themed entries in Quotes.md.
---

# Extracting and curating quotes

This vault collects notable quotes about AI, design, and craft. Raw sources live
under `Sources/<Source>/<Author> - <Title>.md`; the curated deliverable is
`AI quotes library/Quotes.md`, grouped under `## Theme` headers. This skill turns
the slow manual step — reading a source and hand-picking the good lines — into a
fast loop: you extract candidates, the user accepts/rejects them in a card UI, and
the accepted ones land under the right theme in `Quotes.md`.

Read `CLAUDE.md` conventions first; the hard rule that matters most here:
**quotes are verbatim**. Never paraphrase, tidy, or "improve" the wording when it
moves into `Quotes.md`.

## The loop

### 1. Identify the source file(s)

The user points you at what they're interested in right now — a path, a folder, or
a talk/author name. Resolve it to one or more files under
`AI quotes library/Sources/`. If a name is ambiguous, list the matches and ask which.

For each file, read:
- the **YAML frontmatter** (`author`, `role`) — used for the byline,
- the **filename stem** (`<Author> - <Title>`) — this is the exact wiki-link target
  the byline must use: `> — [[<stem>]]`,
- the **body/transcript** — the text you pull candidates from.

Transcripts may carry auto-caption noise (`[music]`, misheard words). Don't fix the
source. Only the text you lift into a candidate gets cleaned, and even then only
trivially (a stray caption artifact); the words themselves stay verbatim.

### 2. Read the existing theme palette

Open `AI quotes library/Quotes.md` and collect the current `## Theme` headers (the
lines starting with `##` that are *not* `## [[...]]`). These are the themes you
prefer to file new quotes under. Also skim the quotes already present so you don't
re-surface a line that's already in the library.

### 3. Select candidates

Pull the lines genuinely worth keeping. You are filtering hard, not transcribing —
a good source might yield 5–12 candidates, not 40. Favor a quote when it is:

- **Insightful** — names something true that most people haven't articulated.
- **Surprising** — cuts against the obvious take, or reframes a familiar idea.
- **Thought-provoking** — leaves the reader chewing on it; quotable on its own.

Skip throat-clearing, generic advice ("collaboration is important"), context-bound
remarks that don't stand alone, and anything that only makes sense with the
surrounding paragraph. A quote should survive being read cold, out of context.

Pull each candidate **verbatim**. Keep it self-contained: trim to the sentence(s)
that carry the idea, but never alter the words inside. A candidate may use `...` to
elide a digression mid-quote (the existing library does this), but the kept words
stay exact.

### 4. Assign a theme to each candidate

Give every candidate a theme. Strongly prefer an **existing** theme from step 2 —
reuse keeps the library coherent. Propose a **new** theme only when nothing existing
genuinely fits; phrase it as a short editorial line in the voice of the existing
themes (e.g. "Taste is the human edge", "The last mile is ours"), not a dry category.
Flag which candidates carry a new theme so the user can see them in the UI.

### 5. Show the review UI

Render the card grid as an inline widget so the user can accept/reject each candidate
and adjust its theme.

- Before your first `show_widget` call, silently call `read_me` (visualize) once.
- Read the template at `assets/review-widget.html` from this skill directory.
- Replace `__CANDIDATES__` with a JSON array and `__THEMES__` with a JSON array of
  the existing theme names (strings). Each candidate object:
  ```json
  {
    "i": 1,
    "text": "the verbatim quote",
    "author": "Loredana Crisan",
    "role": "Chief Design Officer, Figma",
    "title": "Figma's big bets for the future of AI design",
    "theme": "Taste is the human edge",
    "isNewTheme": false
  }
  ```
  Use `role: ""` when unknown. `i` is a stable 1-based index — it is how selections
  come back to you.
- Pass the filled HTML as `widget_code` to `show_widget`.

**Keep the verbatim text on your side.** The widget returns only the chosen indices
and their final theme — not the quote text. You already hold the exact wording from
step 3, so apply *that*. This is deliberate: round-tripping text through the UI risks
silent edits, and verbatim integrity is the whole point.

### 6. Apply the accepted quotes

The widget's "Apply" button sends a message back listing the accepted indices and the
theme chosen for each (the user may have changed a theme via the dropdown). For each
accepted candidate, insert its verbatim text into `AI quotes library/Quotes.md`:

- **Existing theme** → insert after the last quote in that `## Theme` section (before
  the next `##` or end of file).
- **New theme** → append a new `## Theme` section at the end of the file.

Match the existing formatting exactly — a blank line between entries, then:
```
> "the verbatim quote"
> — [[<Author> - <Title>]]
```
The `[[...]]` target is the source's filename stem from step 1. Group consecutive
quotes from the same source under a single byline only if the source already does so;
otherwise give each quote its own byline, which is the dominant pattern.

If the user accepted nothing, say so and stop — don't touch `Quotes.md`.

### 7. Offer to rebuild

Quotes only reach the rendered site through `build_site.py`. Offer to run
`python3 build_site.py` so the new quotes appear in the preview. (Adding quotes alone
doesn't need an `authors.json` commit — that's only for new source frontmatter.)

## Notes

- Works across **multiple sources** in one pass: each candidate keeps its own byline,
  so you can mix candidates from several files in a single review grid.
- If `show_widget` is unavailable in the session, fall back gracefully: present the
  candidates as a numbered list grouped by proposed theme and ask which to keep.
