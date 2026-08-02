# Phase 5 — UI design system

The look is a **"blueprint" study aesthetic**: an ink-on-paper palette on a faint blueprint grid,
technical mono labels, and bordered "sheet" panels with registration-mark corners. Reuse it verbatim
— **copy `assets/index.css` to `frontend/src/index.css`**. Do not hand-roll new styling; compose
the existing classes.

## Fonts (load in `index.html`)

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
  rel="stylesheet"
/>
```

- `--display` **Space Grotesk** — headings, wordmark.
- `--sans` **IBM Plex Sans** — body.
- `--mono` **IBM Plex Mono** — eyebrows, nav, chips, tabular numbers.

## Color tokens (top of `index.css`)

`--ink #0e2a47` / `--ink-soft #35526d` (text), `--paper #f4f6f1` / `--paper-raised #fdfdfb`
(background/cards), `--line #2f6fa6` / `--line-soft` / `--line-faint` (blueprint blue + rules),
`--amber #d97f2c` (accent/active), `--moss #3f7d58` + `--moss-bg` (success/highlight),
`--rust #b03a2e` + `--rust-bg` (error/danger). `--radius 3px`, subtle `--shadow`.

**Per-topic retheme (optional):** to give a topic its own feel, change **only** these token values
(e.g. a warmer palette for a history topic) — every component reads the tokens, so nothing else
needs touching. Keep contrast accessible.

## Signature treatments (already in the CSS)

- **Blueprint grid** background on `body` (two faint linear-gradients at 32px).
- **`.panel`** — a raised sheet with `::before`/`::after` registration-mark corners.
  `.panel--highlight` uses moss for success states.
- **`.topbar`** — sticky ink bar with an amber underline; gains a shadow on scroll
  (`.topbar--scrolled`).
- **`.title-block`** — per-page header: back link, mono eyebrow, title, lede, meta `.chip`s.
- **`.shell`** (max-width 46rem), `.shell--wide` (58rem), `.shell--narrow` (38rem) content columns.
- Utility classes: `.chip`, `.muted`, `.mono`, `.row` / `.row--between`, `.banner` /
  `.banner--error`, buttons, progress bars, `.modal` (for the streak-freeze confirm), toasts.
- `pre`/`code`, tables, `img`, `video`, and `.pdf-embed` are all styled for lesson Markdown. Plain
  Markdown tables get bordered cells (`--line-soft`, 1px) via `table:not(.table) th`/`td` — scoped
  with `:not(.table)` so it doesn't touch the `.table`-class component used for dashboard/quiz
  tables, which keeps its own row-underline look (`.table th`/`td`, see below).
- **`.video-placeholder`** (added for learn-up) — the dashed amber call-out the Gemini Notebook
  placeholder renders into; `.video-placeholder--panel` is the interactive variant holding the
  "Generate Gemini Notebook video" button + a one-line reminder, `.video-placeholder__error` for its
  error text
  (see `references/frontend.md` for the render hook).
- **`.disclaimer`** (added for learn-up) — small italic muted text with a `--line-soft` top rule,
  used for the AI-generated-content footer on every LLM-generated content page (see
  `references/frontend.md`'s "AI-generated content disclaimer" section).

## Accessibility / motion

- `:focus-visible` gets a 2px amber outline. Keep it.
- `@media (prefers-reduced-motion: reduce)` neutralizes animations — already handled.
- The CSS is light-theme only (`color-scheme: light`) by design; keep it unless the user asks for dark.

## Don'ts

- Don't add a CSS framework (Tailwind/Bootstrap) — this is hand-authored CSS by design.
- Don't inline styles beyond tiny one-offs; extend `index.css` with a new class if you truly need one.
- Don't change class names the components rely on.
