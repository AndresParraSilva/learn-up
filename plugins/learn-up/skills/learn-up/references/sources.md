# Phase 2 — Gather sources

The `sources/<topic_slug>/` folder is central: the user feeds these files to **Gemini Notebook** to
generate the per-lesson video summaries referenced by every lesson's placeholder. So sources must
be authoritative, readable, clearly named, and supported by NotebookLM's upload endpoint. Raw
`.html` and `.htm` files are not supported; convert each page to `.txt`, `.md`, or `.pdf` before it
enters this top-level upload corpus.

## Steps

1. **Include user-provided material first.** Anything the user dropped into `sources/<topic_slug>/`
   or linked is a first-class source. If they gave URLs, fetch them (Phase 2 step 3). Apply the same
   HTML conversion rule to user-provided pages; never send a raw `.html` or `.htm` file to
   NotebookLM.
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
3. **Download and convert** the best sources into `sources/<topic_slug>/` with the host's
   fetch/download tool (or a platform-appropriate HTTP client for direct PDF links). Save readable
   `.txt`, `.md`, or `.pdf` files, not paywalled stubs. When a fetched or user-provided page is
   HTML, extract its meaningful content to text/Markdown or render it to PDF **before** placing it
   in the top-level upload corpus. Inspect the converted file to ensure it contains the source's
   actual content rather than navigation, a cookie wall, or an empty browser shell. Changing only
   the filename extension is not conversion. Keep any raw HTML original that must be preserved
   outside the upload corpus; do not delete user-provided material without authorization. Give the
   converted file a clear, human filename that maps to what it covers (you'll reference it by name
   in lesson placeholders), e.g. `01-architecture-overview.pdf`, not `download(3).pdf`.
4. **Respect access & licensing.** Only download openly available material. If a key source is
   paywalled, note it in `SOURCES.md` and point the user to it rather than scraping it.
5. **Record every source.** Add user-provided files and URLs as well as agent-gathered material to
   `SOURCES.md`. The generated About page renders this index verbatim, so an unindexed source is a
   missing provenance record. Mark each source's origin explicitly as `User provided` or
   `Agent gathered`. For a converted web page, record its original URL but put the converted
   `.txt`, `.md`, or `.pdf` filename in the `File` column.

## `sources/<topic_slug>/SOURCES.md`

Maintain an index the user (and Gemini Notebook) can navigate:

```markdown
# Sources — <Topic>

| File                  | Title                  | Origin         | URL       | Authority / freshness                | Why it's here                      |
| --------------------- | ---------------------- | -------------- | --------- | ------------------------------------ | ---------------------------------- |
| 01-official-guide.pdf | Official Study Guide   | User provided  | https://… | Primary; checked YYYY-MM-DD          | Canonical scope + terminology      |
| 02-architecture.md    | Architecture deep-dive | Agent gathered | https://… | Maintainer guide; checked YYYY-MM-DD | Best explanation of the core model |
```

Use a stable local label such as `Local file supplied during intake` when a user-provided file has
no URL. After the table, record known conflicts, staleness, language differences, paywalls, and
coverage gaps under `## Limitations`; write `None identified.` when the review found none. Never
omit a received source because it was not ultimately used for a lesson—retain it and explain that
decision in `Why it's here` or `Limitations`.

## How sources map to lessons

Each lesson's video placeholder tells the user to upload **that lesson's own source document plus
everything in `/sources`** to Gemini Notebook, scoped with: _"Limit the topics to what's in
`<this document name>`."_ So when you author a lesson (Phase 4), pick the single source file that
best covers it and use **that uploadable filename** as `<this document name>` in the placeholder.
For a converted HTML page, this must be the resulting `.txt`, `.md`, or `.pdf` filename, never the
original `.html` or `.htm` name. Every objective should be traceable to at least one file in
`sources/<topic_slug>/`.

If web search yields nothing solid for an objective, tell the user — don't fabricate a source.
If sources conflict, are outdated, or leave material gaps, record that limitation in `SOURCES.md`
and surface it before authoring. For certification topics, distinguish the official exam blueprint
from third-party preparation material and let the official scope win.

## Topic archives

Topic export carries `INTAKE.md` and `SOURCES.md` so the receiving About page preserves the complete
configuration and provenance record. It deliberately does not carry the source PDFs, HTML, images,
or other binaries: the transfer allowlist is validated Markdown, YAML, and MP4 only. State this
limitation in the export/import UI and generated README. A recipient who needs the original source
corpus must obtain it separately from the trusted sender and review it before placing it under
`sources/<topic_slug>/`; never smuggle it into the topic archive under a renamed suffix.
