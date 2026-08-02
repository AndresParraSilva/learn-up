# Phase 5 — Frontend (React + Vite + TypeScript)

## Contents

- Project setup, icons, and routing
- Topic picker, top bar, and pages
- Shared components and AI-content disclosure
- Back navigation and page memory
- Markdown, Mermaid, video, and FAQ behavior
- Grading feedback and styling

React 19 SPA, Vite, TypeScript (strict), React Router, react-markdown + remark-gfm, mermaid.
Mirror the template's structure; the one addition is a **topic picker** so one app hosts many topics.

**`src/api/types.ts` must mirror `references/backend.md`'s "API contract" section field-for-field.**
That section is the literal, verified source of truth for every response shape — do not invent your
own field names, nesting, or grouping from the prose Pages/Components description below alone. If
the backend doesn't exist yet when you write the frontend, copy the Pydantic models from that section
directly into TypeScript interfaces (same field names, same nullability, same flat-vs-nested shape).
This was the single biggest source of bugs in a real build: a frontend written independently from
prose diverged from the backend on nearly every endpoint (nested vs. flat dashboard data, `checks` vs
`self_check`, a raw FAQ string vs. a parsed list, an objective-lessons endpoint treated as returning
one lesson when it returns a list, `total_questions`/`xp_awarded`/`badges_earned` fields the frontend
expected but the backend didn't return) and the dashboard crashed with `Cannot read properties of
undefined (reading 'map')` on first load.

## `frontend/package.json` (deps)

```json
{
  "dependencies": {
    "mermaid": "^11",
    "react": "^19",
    "react-dom": "^19",
    "react-markdown": "^10",
    "react-router-dom": "^7",
    "remark-gfm": "^4"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^6",
    "typescript": "~5.6",
    "vite": "^6",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@types/node": "^24",
    "oxlint": "^1"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "oxlint",
    "preview": "vite preview"
  }
}
```

`vite.config.ts` proxies `/api` → `http://127.0.0.1:8011`. `index.html` loads the fonts
(Space Grotesk, IBM Plex Sans, IBM Plex Mono), sets a topic-neutral `<title>` like "learn-up", and
uses the canonical favicon assets below.

## Favicon and app icon

For a **NEW-APP** run, copy these assets verbatim:

```
assets/favicon.ico            → frontend/public/favicon.ico
assets/favicon-32.png         → frontend/public/favicon-32.png
assets/favicon-512.png        → frontend/public/favicon-512.png
assets/apple-touch-icon.png   → frontend/public/apple-touch-icon.png
```

Add these tags inside `frontend/index.html`'s `<head>`, after the viewport meta tag:

```html
<meta name="theme-color" content="#0e2a47" />
<link rel="icon" href="/favicon.ico" sizes="any" />
<link rel="icon" type="image/png" href="/favicon-32.png" sizes="32x32" />
<link rel="icon" type="image/png" href="/favicon-512.png" sizes="512x512" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
```

The open-book-and-three-fruit-tree mark represents self-directed learning across diverse topics.
Keep it topic-neutral: an **ADD-TOPIC** run must not regenerate, retheme, or replace these app-wide
assets.

## Routing (`src/App.tsx`)

The home route is the **topic picker**. Everything else is nested under a topic slug so topics are
independent:

```
/                                  → HomePage (topic picker; if exactly 1 topic, redirect into it)
/t/:topicSlug                      → DashboardPage (that topic's readiness + study plan + start drills)
/t/:topicSlug/lessons              → LessonsPage
/t/:topicSlug/lessons/:slug        → LessonDetailPage
/t/:topicSlug/lessons/objective/:objectiveCode → LessonDetailPage
/t/:topicSlug/quiz/:attemptId      → QuizPage
/t/:topicSlug/mock/:attemptId      → MockPage        (if assessment enabled)
/t/:topicSlug/review/:attemptId    → ReviewPage
/t/:topicSlug/labs                 → LabsPage         (if labs enabled)
/t/:topicSlug/labs/:slug           → LabDetailPage
/t/:topicSlug/strategy             → StrategyPage     (if strategy enabled)
/t/:topicSlug/strategy/lessons/:slug, /t/:topicSlug/strategy/drill
/t/:topicSlug/badges               → BadgesPage
/t/:topicSlug/about                → AboutPage
```

`<AppShell>` renders `<TopBar/>` + `<Outlet/>`; `<TopicLayout>` resolves `:topicSlug` and wraps its
own `<Outlet/>` in `<TopicContext.Provider>`. **`AppShell` must be nested _inside_ `TopicLayout` for
every topic-scoped route — not the other way around** — otherwise `TopBar` is instantiated by the
_parent_ of `TopicLayout`, which places it structurally outside `TopicContext.Provider`'s subtree, so
`useTopicContextOptional()` inside `TopBar` returns `null` forever regardless of route or data-loading
state. This is a real bug that shipped in a real build: the topbar rendered with just the wordmark and
no nav links (Lessons/Labs/Strategy/Badges/About) or topic name on every single page, because the
provider genuinely never wrapped the component reading from it — no fetch ever completes, no state
update ever helps, because the tree shape itself is wrong. Structure the routes like this:

```tsx
<Routes>
  <Route element={<AppShell />}>
    <Route index element={<HomePage />} />{" "}
    {/* no topic yet — TopBar renders wordmark only */}
    <Route path="*" element={<NotFoundPage />} />
  </Route>
  <Route path="t/:topicSlug" element={<TopicLayout />}>
    {" "}
    {/* provides TopicContext first */}
    <Route element={<AppShell />}>
      {" "}
      {/* AppShell nested INSIDE the provider */}
      <Route index element={<DashboardPage />} />
      <Route path="lessons" element={<LessonsPage />} />
      {/* ...every other topic-scoped route... */}
      <Route path="*" element={<NotFoundPage />} />
    </Route>
  </Route>
</Routes>
```

`AppShell` is mounted twice in the tree (once for the topic-less home/404 routes, once nested inside
`TopicLayout` for every topic route) — that's fine and cheap; React Router only ever mounts the
matched branch, never both simultaneously. After wiring this up, **verify it live**: open a topic page
in a browser and confirm the topbar actually shows the nav links and topic name, not just that the
page's own content rendered — a correct dashboard body next to a broken topbar is easy to miss in a
quick glance.

**`lessons/objective/:objectiveCode` fetches in two steps**, because
`GET /lessons/objective/{code}` returns a **list** (`LessonListItem[]`), not a single lesson (an
objective can have more than one lesson): fetch that list, take the first match, then fetch the full
lesson via `GET /lessons/{slug}` using that match's `slug`. A single-step "treat the list response as
a lesson object" implementation silently renders a blank page (no thrown error — the lesson object
just has `undefined` for `body_markdown` etc., so the page has nothing to show and nothing to log).

## HomePage — the topic picker (new vs. template)

- Fetches `GET /api/topics`. Renders each topic as a `.panel` card: name, description, and progress
  (overall_ready_pct) with a "Start / Continue" link to `/t/:slug`.
- If there's exactly **one** topic, redirect straight into it (so a single-topic install feels like
  the original app).
- A "＋ Add a topic" note tells the user to invoke the `learn-up` skill with a new topic in their
  coding agent (for example, `/learn-up <topic>` in Claude Code or `$learn-up <topic>` in Codex) —
  topics never share content or progress.

## TopBar

- Wordmark links to `/` (the picker). When inside a topic, it also shows the topic name and the
  in-topic nav (Lessons / Labs? / Strategy? / Badges / About), each link scoped to `/t/:topicSlug/…`.
  Hide Labs/Strategy links when those modules are disabled for the topic.
- The topic name span must use `className="mono topbar__topic"`, **not** the generic `.muted`
  utility — `.muted` is `var(--ink-soft)`, tuned for the light `--paper` background, and reads as
  near-invisible low-contrast text against the topbar's dark `--ink` background. `.topbar__topic`
  (in `assets/index.css`, next to `.topbar__mark`) uses the same lighter `#b9c9d8` tone the nav
  links already use for exactly this reason — reuse it, don't reach for `.muted` here.

## Pages (behavior, mirrors template)

- **DashboardPage** — overall readiness ("GO"/keep going), per-domain mastery bars with expandable
  objective lists (each objective: mastered badge, "practice" button, estimated study week), Labs
  progress and Strategy progress (see below), the review queue (weak/due/new), start buttons (quick
  drill, domain drill, practice, mock), attempt history, XP/streak + buy-streak-freeze, and the
  folded-in suggested study plan by week.
  **The "Streak freeze" panel spells out the mechanism in prose, not just the held/longest-streak
  numbers** — it's a purchase with no in-app confirmation of _when_ it gets spent (spending happens
  silently server-side inside `update_streak`, see `references/backend.md`'s gamification section), so
  a bare "Held: 2" chip leaves a learner unable to tell whether buying one will actually save a streak
  they're about to break. State it explicitly: one freeze covers one missed day, it's consumed
  automatically the next time you answer a question after a gap (not on purchase, not on the missed
  day itself), and `STREAK_FREEZE_MAX_HELD` (frontend `src/constants.ts`, mirroring the backend
  constant) caps how many you can hold at once.
  **`GET /progress/dashboard` returns everything flat** (`domain_readiness`, `review_queue`,
  `study_plan` are all flat lists — see `references/backend.md`'s API contract). Build every nested
  view client-side: group `study_plan` by `estimated_week` for the study-plan section; derive each
  domain's objective list by filtering `study_plan` on `objective_code.startsWith(domain.code + ".")`;
  derive per-objective "mastered" as `!reviewQueueMap.has(code) || reviewQueueMap.get(code) === "due"`
  (an objective in `review_queue` with status `"due"` is mastered but due for review, not unmastered —
  only `"weak"`/`"new"` mean not mastered; an objective absent from `review_queue` entirely is
  mastered and not due). Do not expect the backend to pre-group any of this.
  **Labs progress / Strategy progress are gated on `topic.labs_enabled` / `topic.strategy_enabled`,
  not on whether the arrays came back non-empty** — a topic can have the module on with zero seeded
  labs/lessons yet (shows "No labs yet." / "No strategy lessons yet.") vs. the module off entirely
  (section omitted). `DashboardOut` does **not** carry lab/strategy lists — fetch them with the
  existing `api.listLabs()` / `api.listStrategyLessons()` calls (same ones `LabsPage`/`StrategyPage`
  use) in their own gated `useEffect`s, reusing the `card-list`/`card-link`/`card-link__title`/
  `card-link__meta` classes so the section matches those pages' look. Each section also shows an
  "N of M passed/read" count line above the list, and the Strategy section additionally links to
  `/t/:topicSlug/strategy/drill`.
- **LessonsPage / LessonDetailPage** — list by domain→objective; detail renders `body_markdown`, then
  a `## Why It Matters` block, then the FAQ + select-to-ask widget. If `body_markdown` still contains
  `[placeholder]` (video not generated yet), the placeholder renders inline as a `VideoGenerationPanel`
  in place of the call-out — not a separate box above the body, see "Markdown component" below — full
  wiring (types, `http.ts` calls, `TeachingArticle`/`LessonDetailPage` props) in
  `references/notebooklm-automation.md`'s "Path 1" section; don't reach into `useTopicContext` from
  inside the panel itself, follow the existing `onAsk`/`onDeleteFaq` delegation pattern instead.
  **LessonsPage also has a client-side search box** (`.search-box` in `assets/index.css`, plain
  `input[type="text"]` styling) above the domain groups: filters the already-fetched list in a
  `useMemo`, re-grouping by domain from the filtered set rather than filtering the grouped output.
  **It searches full lesson content, not just the title/objective/domain strings** — a title-only
  search was shipped first and immediately found too narrow in practice (a learner searching a
  concept mentioned mid-lesson got zero results). `LessonListItem` therefore also carries
  `body_markdown` + `why_it_matters_markdown` (full text, straight off the `Lesson` row — no
  markdown stripping, substring matching against raw markdown is good enough), and the filter
  joins all six fields (`title`, `objective_code`, `objective_title`, `domain_name`,
  `body_markdown`, `why_it_matters_markdown`) into one lowercase string before matching. No new
  endpoint or search index — the full list already round-trips to the client, so this is just more
  fields on an existing response. Show a "No lessons match “‹query›”." message only when the query
  is non-empty and the filtered set is empty (don't reuse that message for a topic that
  legitimately has zero lessons).
  **Each row also shows a small video-status marker before the title**, keyed off
  `LessonListItem.video_status` (`references/backend.md`): `"done"` → ▶️ "Video available",
  `"running"` → ⏳ "Video requested", `"error"` → ⚠️ "Video generation failed". **`"idle"` renders no
  icon at all** — an earlier pass used 🎥 for "not requested yet", but a camera emoji reads as "a
  video exists here", which is backwards for the one state where it doesn't; omitting the marker
  entirely turned out clearer than any icon choice for "nothing has happened yet". Keep the mapping
  as a lookup object (`Partial<Record<VideoJobStatus, {icon, label}>>`) rather than a chain of
  ternaries — the icon doubles as the `title=` tooltip text, and a missing map entry (the idle case)
  is the signal to render nothing, not a fallback icon.
- **QuizPage / MockPage** — one question at a time; submit → immediate feedback (correct/incorrect +
  every choice's explanation, see "Grading feedback" below). Mock is timed to the topic's
  `assessment_minutes` and submits each answer once. On finish → summary + link to ReviewPage.
  QuizPage's title is `attempt.label` (backend-computed, see `AttemptOut.label` in
  `references/backend.md`) — not a static "Drill" string — so it reads e.g. "Domain drill:
  Foundations & Architecture" or "Practice: What OpenHands Is and When to Use It". `QuizRunner`'s
  "Finish attempt" button is only rendered once every question is answered (`allAnswered`) — it does
  not render disabled beforehand, since a visible-but-unclickable button invites clicking it to see
  what happens. Same pattern for `StrategyDrillPage`'s per-question "Submit answer" button, which is
  disabled (not hidden) because no-selection is the normal starting state, not a not-yet-eligible one.
  **The question-navigator buttons (`.progress-nav__item`) are colored by correctness, not just
  "answered."** For each question, resolve `results[question_id]?.is_correct ?? question.is_correct`
  — the live `results` map (populated this session, right after `submit()`) wins when present;
  `AttemptQuestion.is_correct` (server-provided, see `references/backend.md`'s `_attempt_out` note)
  is the fallback for anything answered in an earlier session before a reload/resume, which the
  local `results` map has no record of. `null`/`undefined` (not yet answered) adds no extra class;
  otherwise add `is-correct-nav` or `is-incorrect-nav` alongside the existing `is-answered`/
  `is-current` classes — `assets/index.css`'s `.progress-nav__item.is-correct-nav` /
  `.is-incorrect-nav` set a light `--moss-bg`/`--rust-bg` background plus a matching border/text
  color, applied on top of (not instead of) `is-answered`, so an unanswered-vs-answered distinction
  still exists independent of correctness.
- **ReviewPage** — full per-question review with explanations (see "Grading feedback" below).
  It also re-fetches the attempt fresh via `GET .../review`, whose `Review` shape has **no**
  `badges_earned` field — badges only ride on `POST .../finish`'s response (`FinishResult`). Real bug
  that shipped: `QuizRunner.finishAttempt()` already passes that `FinishResult` through
  `navigate(..., { state: { finishResult } })`, but ReviewPage never read `location.state`, so a badge
  earned exactly at finish time (e.g. a 100%-score "Clean Sweep") was awarded server-side (the
  `UserBadge` row existed, so it showed up later on BadgesPage) but never displayed anywhere at the
  moment it was earned. Fix: read `useLocation().state?.finishResult?.badges_earned` into local state
  and render it through `BadgeToast`, same as `LabDetailPage` already does with its own check-result
  response — `badges_earned` is a transient, one-shot payload attached to the mutating endpoint's
  response, not something a subsequent GET will ever hand back, so any page reached via navigation
  after a finish/check call needs to carry it through router state (or the caller needs to hold onto
  the mutation response) rather than expecting a refetch to reproduce it.
  **The score chip shows a percentage alongside the raw fraction**: `{score_raw}/{total_questions}
({pct}%)`, where `pct = ((score_raw / total_questions) * 100).toFixed(1)` — one decimal, computed
  client-side from fields the `Review` shape already carries, no new backend field needed.
- **LabsPage / LabDetailPage** — scenario + task + self-check inputs graded by the backend; no creds.
  `LabOut.self_check` (not `checks`) drives the input list; `POST .../check` takes `{answers: string[]}`
  positional (matching `self_check` order) and returns results keyed by `position`.
  Each self-check field also renders a `"Hint"` / `"Show answer"` button pair (`.btn--ghost.btn--small`,
  `.self-check__reveal-actions` wrapper) — both call `GET .../self-check/{position}/hint` /
  `.../answer` on click and render the returned text inline (`.self-check__reveal`, `p` below the
  input), not upfront in `LabOut` (see `references/backend.md`'s hint algorithm section for why: the
  raw answer shouldn't ride along in the page's initial payload). Fetch once per position and cache
  in local component state (`Record<number, {hint?: string; answer?: string}>`) rather than
  refetching on every click — the hint endpoint is genuinely randomized per request (see backend doc),
  so refetching on toggle would make a revealed hint change out from under the learner, which reads as
  broken. **The Hint button is `disabled` (not hidden) when `check.hint_available` is `false`** — same
  disabled-vs-hidden convention as `QuizRunner`'s "Finish attempt"/`StrategyDrillPage`'s "Submit
  answer" above: a yes/no question always has `hint_available: false` from the backend (a `"y..."`
  hint would just be the answer), and hiding the button entirely would look inconsistent against the
  other self-check rows that do have a working Hint button. "Show answer" is never disabled — giving
  up is always available, even on a yes/no question.
  **LabsPage has the same client-side search box as LessonsPage, also over full content.**
  `LabListItem` carries `scenario_markdown`, `task_markdown`, and `self_check_markdown` (a
  `list[str]` of just each check's `prompt_markdown`, in position order — requires
  `selectinload(Lab.checks)` on the list query, which the plain list endpoint didn't need before
  this). The filter joins `title` + `objective_code` + `objective_title` + `scenario_markdown` +
  `task_markdown` + the joined `self_check_markdown` entries (no `domain_name` field on
  `LabSummary`, so it's left out of the match string there). **Deliberately excluded:**
  `expected_result` and each self-check's answer/hint value — those are the spoilers a learner
  hasn't earned yet (same "don't ship the answer in the initial payload" rule as the hint
  endpoints below), so a search box that matched on them would leak a lab's answer to anyone
  typing a guess into the search box before attempting it.
- **Strategy pages** — lessons + a strategy drill (cert topics only).
- **BadgesPage / AboutPage** — earned/locked badges; about = what the app is + content version.
  `GET /progress/badges` returns a flat `list[BadgeOut]` — split it into earned/locked client-side via
  `earned_at !== null`, don't expect the backend to pre-split it.

## Components

`AppShell`, `TopBar`, `TitleBlock` (page header w/ back link + eyebrow + meta chips), `Markdown`,
`Mermaid`, `QuizRunner`, `FaqSection`, `TeachingArticle` (wraps lesson body + FAQ + select-to-ask),
`BadgeToast`, `VideoGenerationPanel` (copy `assets/VideoGenerationPanel.tsx` verbatim — the "Generate
Gemini Notebook video" button + poll/error/retry states, rendered by `Markdown` in place of the
placeholder call-out, see `references/notebooklm-automation.md`).

**Don't set `TitleBlock`'s `eyebrow` to the topic name.** `TopBar` already renders the current
topic's name persistently (`topbar__topic`, next to the `learn-up` mark) on every page inside a
topic, so `eyebrow={topic.name}` is a plain visual duplicate directly under it — caught live across
9 pages in a real build (`LessonsPage`, `LabsPage`, `QuizPage`, `BadgesPage`, `AboutPage`,
`StrategyPage`, `StrategyDrillPage` ×2, `MockPage`, `ReviewPage`), all fixed by dropping the prop
(`eyebrow` is optional; omitting it renders nothing). Only pass `eyebrow` when it carries information
`TopBar` doesn't already show — domain/objective context (`LessonDetailPage`, `LabDetailPage`),
syllabus version (`DashboardPage`), a strategy sub-topic (`StrategyLessonPage`), or a page-specific
tag like `"404"` (`NotFoundPage`).

**`SelectionAsk` — copy `assets/SelectionAsk.tsx` verbatim, don't re-derive it.** It listens for
`document`'s `selectionchange` to show an "Ask about this" trigger near the user's text selection,
then opens a question panel on click. A build that re-derives this from the prose description alone
reintroduced a real bug: the naive version keeps listening to `selectionchange` while the panel is
open, and clicking into the panel's own `<textarea>` collapses `window.getSelection()` (the page's
selection, not the textarea's internal one) — which the naive handler reads as "selection cleared"
and nulls out the trigger state, which the component treats as "nothing to show," unmounting the
whole open panel out from under the user's cursor. Net effect: the box appears, is unclickable, and
vanishes on click — exactly the failure mode it looks like. The fix baked into the asset: the
`selectionchange` handler bails out early (`if (panelOpen) return`) once the panel is open, so
in-panel interactions can't clobber it.
It also drives the cost-mitigation confirm flow: `onAsk` takes a `useFullSources` flag and returns
an `AskOutcome` (`{type: "answered", entry}` or `{type: "insufficient"}`), not a bare `FaqEntry` —
see `references/backend.md`'s "Select-to-ask FAQ" section for the full narrow-then-confirm-then-full
mechanics this drives on the backend. `FaqEntry.selected_text: string | null` rides along on `entry`
so the newly-answered passage can be highlighted in the body immediately — see "Link a FAQ answer's
source passage back into the body" below.

### AI-generated content disclaimer

Every page that renders LLM-generated prose ends with a `<p className="disclaimer">` footer: _"This
text was automatically generated by an LLM and may contain errors. Read it with a critical eye and
verify any sensitive topic elsewhere."_ There are two wiring points, not one — `TeachingArticle`
does **not** cover every content page:

- **`TeachingArticle`** renders it once, after the FAQ section — this covers every page that goes
  through it (`LessonDetailPage`, `StrategyLessonPage`), so lessons and strategy lessons get it for
  free with no per-page wiring.
- **`LabDetailPage`** lays out Scenario/Task/Self-check/FAQ inline rather than via `TeachingArticle`
  (see "Components" above), so it carries its own copy of the same `<p className="disclaimer">`
  paragraph after its FAQ section — don't assume `TeachingArticle`-only coverage is enough when
  adding a new content page; check whether it goes through `TeachingArticle` or lays out its own
  sections before deciding the footer is already handled.

Style: `.disclaimer` in `assets/index.css` (see `references/ui-design.md`).

### Back link reflects the actual calling page, plus scroll/accordion memory

A lesson/lab detail page's `TitleBlock` `backTo`/`backLabel` isn't a hardcoded "Lessons"/"Labs" —
those pages can also be reached **directly from the Dashboard** (review queue, suggested study
plan, domain-mastery accordion rows, and the labs-progress list all link straight to a lesson/lab
detail page, bypassing `LessonsPage`/`LabsPage` entirely). **Copy `assets/backNav.ts` and
`assets/usePageMemory.ts` verbatim** — both encode fixes for real bugs (below), not just a
straightforward feature. `backNav.ts` exports `BackNavState` (`{ from: string; label: string }`)
and `resolveBackNav(state, fallback)`: pages that can jump straight to a detail page pass
`state={{ from: "/t/<slug>", label: "Dashboard" }}` on the `<Link>` (see `DashboardPage`'s 4 such
links); `LessonDetailPage`/`LabDetailPage` read `useLocation().state` through `resolveBackNav`,
falling back to `{ from: "/t/<slug>/lessons", label: "Lessons" }` / `.../labs` when no state is
present (i.e. reached from the list page, which needs no extra wiring since that's already the
fallback).

The calling page's scroll position (and, for the Dashboard, which domain-mastery rows were
expanded) is restored when the learner comes back. `assets/usePageMemory.ts`:

- **`usePersistedState(key, initial)`** — a drop-in `useState` replacement backed by
  `sessionStorage`, so state survives the component unmounting when the user navigates away and
  back (Dashboard's `expanded` domain-accordion map uses this, keyed `expanded:/t/<slug>`).
- **`useScrollRestoration(ready)`** — saves `window.scrollY` to `sessionStorage` (keyed
  `scrollY:<pathname>`) and restores it once `ready` flips true. Wired into `DashboardPage`,
  `LessonsPage`, `LabsPage`.

Two non-obvious bugs were hit building this, both confirmed live (not just in theory) — reproduce
them if re-deriving this instead of copying the asset:

1. **The scroll save is debounced (300ms), not saved on every `scroll` event or in an unmount
   cleanup.** Navigating away swaps in the new route's DOM in place (no full page reload); the new
   route's _initial_ render is briefly short (a "Loading…" placeholder), and the browser physically
   clamps `window.scrollY` to fit — a genuine `scroll` event firing with `y=0` on the **old** page's
   still-registered listener, moments before it unmounts. Saving immediately (or in the unmount
   cleanup) durably overwrites the real position with that clamp artifact. Debouncing means the old
   component has already unmounted (clearing the pending timeout) before the artifact would
   otherwise get persisted.
2. **`useScrollRestoration`'s `ready` flag must wait for every async section that affects page
   height, not just the primary fetch.** `DashboardPage` originally passed `!!dashboard` alone; but
   `labs`/`strategyLessons` load via separate `useEffect`s slightly later, and their sections start
   as a one-line "Loading…" placeholder that gets replaced by a full list once that fetch resolves.
   Restoring scroll before that settles lets the browser's native **scroll anchoring** compensate
   for the late height change (it tries to keep whatever's under the viewport visually stable),
   dragging the restored position hundreds of pixels further down than intended. Fix: `const
dashboardReady = !!dashboard && (!topic.labs_enabled || labs !== null) &&
(!topic.strategy_enabled || strategyLessons !== null)`, passed to `useScrollRestoration`.

## Markdown component (`src/components/Markdown.tsx`)

react-markdown + remark-gfm, with these custom renderers (carry over from the template):

- ` ```mermaid ` fenced blocks → `<Mermaid>`.
- links ending `.mp4` → `<video controls src=…/>` — **this is how a lesson's Gemini Notebook video
  shows up** once the placeholder is replaced with an `.mp4` link. The `href` is passed straight through
  as `src`, so the convention `/media/<topic_slug>/<slug>.mp4` (see
  `references/notebooklm-automation.md`) resolves correctly through the dev proxy and in
  production alike — no per-link URL rewriting needed here.
- links ending `.pdf` → an `<iframe>` embed + open-in-new-tab link.

### Link a FAQ answer's source passage back into the body

`Markdown` takes an optional `faqHighlights: { index: number; text: string }[]` prop, fed into
`remarkPlugins` as `[remarkFaqHighlights, faqHighlights ?? []]` (`src/lib/remarkFaqHighlights.ts`,
same hand-rolled-AST style as `remarkVideoPlaceholder.ts`, no extra deps). It finds each entry's
`text` as an exact substring of a single markdown text node and replaces it with a `link` mdast node
pointing at `#faq-<index>`, so the exact passage the learner highlighted to ask a question becomes a
clickable citation-style link back to its answer — before this, the FAQ panel opened with a quote of
the selection but that context vanished the moment the panel closed, with no way back to it.
**Do the matching as a remark AST transform, not a `useEffect` DOM walk on the rendered body** — a
DOM-surgery version (find text nodes via `TreeWalker`, wrap the match in an injected `<a>`) risks
React's next reconciliation pass operating on node references that DOM mutation moved out from under
it (`insertBefore`/`removeChild` against a node that's no longer where React last rendered it),
since React doesn't re-read the DOM before diffing. A remark plugin runs before React ever sees the
tree, so there's no foreign-node conflict. Matching is single-text-node: the full quote is tried
first, and if a selection crosses a `**bold**`/`` `code` `` boundary so no single run contains it
whole, the longest leading prefix of the quote that the run ends with gets linked instead (down to
one word or character if the boundary falls that early) rather than linking nothing.
`TeachingArticle` computes `faqHighlights` from its `faq` prop (`entries.filter(e =>
e.selected_text).map(e => ({ index: e.index, text: e.selected_text }))`) and passes it to **both**
`Markdown` calls (body and "Why It Matters" — a selection can come from either). `LabDetailPage`
(which lays out `SelectionAsk`/`FaqSection` inline rather than via `TeachingArticle`) does the same
from `lab.faq` for its Scenario and Task `Markdown` calls. No extra wiring needed on the _landing_
side — `FaqSection.tsx` already gives every entry `id={`faq-${entry.index}`}`, and `.faq-entry:target`
in `index.css` already highlights it; the remark plugin is the other half of an already-half-built
affordance. Style the link itself with `.faq-source-link` (amber, solid underline via
`text-decoration-color` — it should read as an actual clickable hyperlink, not a subtle
dotted-underline emphasis; an earlier `color: inherit` + dotted-border version tested as too subtle
for users to notice it was clickable).
See `references/backend.md`'s "Select-to-ask FAQ" section for the `selected_text` storage format
(`<!-- selected: ... -->` comment in `faq_markdown`) this depends on.

### Test that every content mermaid diagram actually parses

A mermaid syntax error (e.g. bare parentheses inside an unquoted `{...}` diamond node label — mermaid
treats `(`/`)` as shape-delimiter tokens even inside a label) doesn't fail content validation or the
TS build; it only shows up as a rendering error in the browser (`<Mermaid>`'s catch block, or an
in-SVG "Syntax error in text mermaid version..." diagram) once a learner opens that lesson. Add
`vitest` + `jsdom` as frontend devDependencies (`npm install -D vitest jsdom`) and a `test` block to
`vite.config.ts` (`/// <reference types="vitest/config" />` at the top, `test: { environment: "jsdom" }`
in the config object) plus an `npm test` script (`"vitest run"`). Write a test
(`src/lib/mermaidContent.test.ts` in the reference implementation) that walks every `content/**/*.md`
file, regexes out every ` ```mermaid ` fenced block, and calls `mermaid.parse(code, { suppressErrors:
true })` (the same `mermaid` package/version the app renders with) on each — `mermaid.parse` is
mermaid's own documented "validate without rendering" API, returning `false` on invalid syntax rather
than needing a full render pass or a headless browser. Use `it.each(blocks)` (one test per diagram,
title interpolated from `$file`/`$index`) so a broken diagram is reported by file, not buried in one
aggregate failure. This is the only frontend test in the template as of writing — it's a content
sanity check, not app logic.

### Render the Gemini Notebook placeholder as a single button + reminder

`Markdown` takes an optional `video` prop (`{ onGenerate, onPollStatus, onReady }`, same shape
`TeachingArticle` receives) and threads it straight through — do **not** render
`VideoGenerationPanel` as a separate box above the body. The user sees this on every lesson, learns
it once, and afterward either clicks the button or ignores it, so it must read as one call-out, not
two stacked boxes.

`VideoGenerationPanel` checks `onPollStatus` once on mount (not just after the user clicks
"Generate") and, if a job is already `"running"` server-side, starts straight into the
"Generating your video… this can take a few minutes." message and resumes polling — without this,
a generation triggered in one page visit silently "forgets" it's in flight the moment the learner
navigates away and back (or across a page refresh), showing the "Generate" button again and inviting
a duplicate, quota-burning request. `status` starts as `null` (not `"idle"`) so the panel renders
nothing during that initial check instead of flashing the button before the real state is known; if
the check comes back `"done"` (job finished while the learner was away), it calls `onReady()`
immediately rather than showing anything transitional. This only covers same-process navigation —
`app/services/lesson_video.py`'s in-memory `_JOBS` dict is what `onPollStatus` reads, so a full
backend restart still resets to "idle" on the frontend, but the `.video_tasks.json` resume logic
(see `references/notebooklm-automation.md`'s "Resumable generation" section) still prevents that
next "Generate" click from actually duplicating the request.

A small remark/rehype step (or pre-render string transform) converts
`[placeholder]TEXT[/placeholder]` into `<div class="video-placeholder">TEXT</div>` — a small custom
`div` renderer in `Markdown`'s `components` map then intercepts `className === "video-placeholder"`
and, when a `video` prop was passed, renders `<VideoGenerationPanel {...video} />` in its place
(ignoring the raw inner text entirely — that text only matters server-side, where
`app/services/lesson_video.py`'s regex pulls the source-doc name out of it). If no `video` prop is
passed, fall back to rendering the div with its raw text, dashed-amber-box style, so the component
degrades gracefully wherever `Markdown` is used without video wiring (e.g. FAQ answer bodies).
Style `.video-placeholder` in `index.css` (dashed `--amber` border, `--amber-ink` text, a 🎬
lead-in) and the `.video-placeholder--panel` flex-row modifier (see `assets/index.css`) for the
button+text layout. `TeachingArticle` just passes its own `video` prop down to
`<Markdown video={video}>{bodyMarkdown}</Markdown>` — see
`references/notebooklm-automation.md`'s "Path 1" section for the exact wiring.

## Grading feedback (`QuizRunner`, `ReviewPage`, `StrategyDrillPage`)

Every place that renders a graded choice's `explanation_markdown` (`QuizRunner`'s immediate
post-submit feedback, `ReviewPage`'s per-question breakdown, `StrategyDrillPage` if it shows full
choice lists) must apply the same display rule: per
`references/content-schema.md`'s authoring convention, every correct choice's `explanation` is
authored starting with the literal prefix `Correct — `. When rendering a **correct choice the
learner did not select**, strip that leading `Correct — ` before display — a choice the learner
didn't pick shouldn't visually assert "Correct" at the start of its own explanation line, it should
just read as the reason it was the right answer. Leave the prefix intact for a correct choice that
**was** selected, and never touch a distractor's explanation (distractors are never authored with
the prefix in the first place).

Implement this as one small shared helper (e.g. `stripCorrectPrefix(explanation, isCorrect,
isSelected)`), not three copy-pasted conditionals — `QuizRunner` knows "selected" from its own local
answer state at submit time; `ReviewPage`/`StrategyDrillPage` get it from `selected_choice_ids` /
`GradedChoice` equivalents already in the API response (`references/backend.md`'s API contract).
Do the stripping client-side, at render time only — never mutate the stored/served
`explanation_markdown` itself, so the canonical authored text (with its prefix) stays the single
source of truth and the same API response renders correctly regardless of which choices a
particular learner happened to select.

## Styling

Copy `assets/index.css` verbatim to `frontend/src/index.css` and import it in `main.tsx`. See
`references/ui-design.md` for the design system and the small additions (`.video-placeholder`).
Optionally retheme per topic by editing only the color tokens at the top of `index.css`.

Prose block elements (`p`, `h1`-`h3`) use a margin-bottom-only rhythm (`margin: 0 0 <x>em`, no
margin-top) — vertical spacing between blocks comes entirely from the preceding element's bottom
margin. `table` has no browser-default margin (unlike `pre`/`ul`/`blockquote`, which get UA-stylesheet
margins for free), so it needs an explicit `margin: 0 0 0.9em` in this rule set or markdown tables
render glued to whatever heading/paragraph follows them.
