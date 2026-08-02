# Phase 2 — Gather sources

The `sources/<topic_slug>/` folder is central: the user feeds these files to **Gemini Notebook** to
generate the per-lesson video summaries referenced by every lesson's placeholder. So sources must
be authoritative, readable, and clearly named.

## Steps

1. **Include user-provided material first.** Anything the user dropped into `sources/<topic_slug>/`
   or linked is a first-class source. If they gave URLs, fetch them (Phase 2 step 3).
2. **Search the web** using the host's available browsing/search tools. Prefer, in order:
   - Official documentation / standards bodies / primary sources.
   - Canonical textbooks, official study guides, well-regarded references.
   - Reputable tutorials/overviews only to fill gaps.
     Search a few angles (e.g. `"<topic> official documentation"`, `"<topic> study guide pdf"`,
     `"<topic> comprehensive reference"`). Use the current year for anything time-sensitive.
     If this topic's `content_language` (Phase 1) isn't English, search in that language first (native
     sources are usually better-fitted to how the lessons will read) — but don't force it: if the best
     authoritative material for this topic is only available in English (common for niche technical
     subjects), use it as grounding and author the lessons in the target language anyway. Note in
     `SOURCES.md` when a source's language differs from the topic's `content_language`.
3. **Download** the best sources into `sources/<topic_slug>/` with the host's fetch/download tool
   (or a platform-appropriate HTTP client for direct PDF links). Save readable text/markdown/PDF — not paywalled stubs. Give each a
   clear, human filename that maps to what it covers (you'll reference it by name in lesson
   placeholders), e.g. `01-architecture-overview.pdf`, not `download(3).pdf`.
4. **Respect access & licensing.** Only download openly available material. If a key source is
   paywalled, note it in `SOURCES.md` and point the user to it rather than scraping it.

## `sources/<topic_slug>/SOURCES.md`

Maintain an index the user (and Gemini Notebook) can navigate:

```markdown
# Sources — <Topic>

| File                  | Title                  | URL       | Authority / freshness                | Why it's here                      |
| --------------------- | ---------------------- | --------- | ------------------------------------ | ---------------------------------- |
| 01-official-guide.pdf | Official Study Guide   | https://… | Primary; checked YYYY-MM-DD          | Canonical scope + terminology      |
| 02-architecture.md    | Architecture deep-dive | https://… | Maintainer guide; checked YYYY-MM-DD | Best explanation of the core model |
```

## How sources map to lessons

Each lesson's video placeholder tells the user to upload **that lesson's own source document plus
everything in `/sources`** to Gemini Notebook, scoped with: _"Limit the topics to what's in
`<this document name>`."_ So when you author a lesson (Phase 4), pick the single source file that
best covers it and use **that filename** as `<this document name>` in the placeholder. Every
objective should be traceable to at least one file in `sources/<topic_slug>/`.

If web search yields nothing solid for an objective, tell the user — don't fabricate a source.
If sources conflict, are outdated, or leave material gaps, record that limitation in `SOURCES.md`
and surface it before authoring. For certification topics, distinguish the official exam blueprint
from third-party preparation material and let the official scope win.
