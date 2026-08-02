---
name: learn-up
description: Create or extend a local, self-hosted study web app for any topic, grounded in user-provided and authoritative source material. Use when explicitly invoked as learn-up, when the user asks to "learn up" a topic, or when they want blueprint-mapped lessons, explained quizzes, hands-on labs, spaced repetition, progress tracking, multilingual content, or a specific lesson's Gemini Notebook video in an existing learn-up app.
---

# learn-up — build a study app for any topic

You are building a **local, single-user study web app** for a topic the user wants to learn.
The app is a faithful generalization of a production exam-prep app: a React SPA + FastAPI
backend, content authored as version-controlled YAML/Markdown and seeded into an embedded
**DuckDB** database. One `learn-up` repo can hold **many independent topics**; the home page
is a topic picker.

This skill runs in **phases**. Do them in order. Each phase has a detailed reference doc under
`references/` — read that doc at the start of the phase before acting. Do **not** try to hold
the whole build in your head; pull each reference in as you reach its phase.

## Golden rules

1. **Ask before authoring.** Never skip the intake (Phase 1). The topic's size, the user's
   goal, and their starting knowledge decide the whole shape of the app.
2. **Everything is blueprint-tagged.** Every lesson, question, and lab references an
   `objective` code that exists in that topic's `syllabus.yaml`. Off-syllabus content is a bug.
   A content **validator** must fail loudly on any gap or dangling tag.
3. **Fail loudly.** No silent defaults, no graceful degradation that hides missing content or
   bad input. Raise/assert on unexpected shapes. This applies to the app code you generate too.
4. **Every lesson opens with the Gemini Notebook video placeholder** (exact text in Phase 4). This is
   non-negotiable and is the reason the `sources/` folder exists. Resolving it into a real video is
   user-paced and per-lesson (never bulk-generated), via one of four paths (an in-app button being
   the default) — see `references/notebooklm-automation.md`.
5. **Reuse the design system and brand assets verbatim.** Copy `assets/index.css` and the four
   favicon/app-icon assets — do not re-invent the styling or topic-neutral learn-up mark.
6. **DuckDB, not Postgres.** Synchronous SQLAlchemy + `duckdb_engine`. See `references/tech-stack.md`.
7. **Source quality sets the ceiling.** Organize, explain, and test the supplied evidence; never
   turn weak, stale, incomplete, or contradictory material into confident claims. Prefer primary
   and official sources, record limitations in `SOURCES.md`, and tell the user when the available
   material cannot support an objective reliably.

## Phase 0 — Locate/target the repo

1. Run `date` and note today's date (used for the changelog and any pacing math).
2. Check whether this invocation is actually a **GENERATE-VIDEO** run instead of a build: a request
   to generate/fetch a specific lesson's video against an app that already exists (e.g. "generate
   the video for lesson 1.1 of github-actions", "make the Gemini Notebook video for the founding-myths
   lesson"), as opposed to a topic name to build/add. If so, skip the rest of Phase 0 through
   Phase 6 entirely — go straight to `references/notebooklm-automation.md` and follow Path 2
   (MCP-driven, via chat) unless the user asks for the button, the script, or the manual path
   instead. This mode works against an existing app at any time, not just right after a build, and
   is the normal way lesson videos get resolved (never bulk — see golden rule 4).
3. Otherwise, determine the **topic** from the invocation text or the user's request. If absent,
   ask for it. Invocation syntax varies by host: Claude Code commonly uses `/learn-up`, while
   Codex uses `$learn-up`; do not assume one syntax in generated user-facing text.
4. Decide the target `learn-up` directory:
   - If the current working directory already **is** a `learn-up` repo (has `pyproject.toml`
     with name `learn-up` and a `content/` dir), or a `./learn-up` subdir exists → this is an
     **ADD-TOPIC** run. Read `references/multi-topic.md` and confirm with the user you're adding
     a new topic to the existing app, not starting over.
   - Otherwise → this is a **NEW-APP** run. You'll create the `learn-up/` folder in Phase 5.
5. Derive a `topic_slug` (kebab-case, e.g. "Ancient Rome" → `ancient-rome`). It namespaces this
   topic's content, sources, and routes; it must be unique within the repo.

## Phase 1 — Intake (interactive) → `references/intake.md`

Use the host's interactive question or selection UI when it is available; otherwise run the same
short structured interview directly in chat. You must learn:

- **Current knowledge** of the topic (novice / some / strong) — sets lesson depth and prerequisites.
- **Objective** — why they're learning it, target outcome, any deadline. Free-form; capture verbatim.
- **Existing material** — invite them to drop files into `sources/<topic_slug>/` now, or point you at
  URLs/paths. Anything they give is a first-class source.
- **Exam/certification?** — if the topic has a real cert exam, enable the **mock** + **strategy**
  modules and capture its real facts (question count, time, pass mark). Else keep them optional.
- **Hands-on?** — if practical (a tool/language/craft), enable **labs** (guided self-check exercises).
- **Content language** — the language every lesson/question/lab is authored in for _this topic_.
  Defaults to English. Never changes the app's UI chrome, even on an ADD-TOPIC run into an app whose
  UI is in a different language than the new topic's content — see `references/multi-topic.md`.
- **NotebookLM output language** — the exact supported locale code for generated artifacts, selected
  from `notebooklm language list --json` (for example, `en`, `es`, or `es_419`). Prefer a regional
  variant when the user specifies one; do not infer a generic locale when their preference is known.
- **FAQ LLM backend** — choose `claude_cli`, `codex_cli`, or `openhands` based on the user's active
  agent and preference. Prefer the authenticated CLI they are already using; never silently switch
  providers or introduce an API charge.

Write the answers into a working `sources/<topic_slug>/INTAKE.md` so later phases (and the user)
can see them. Do not proceed until the objective and the two module toggles are settled.

## Phase 2 — Gather sources → `references/sources.md`

Use the host's web search/browsing capability to find the most authoritative, current sources for
this topic (official docs, standards, canonical textbooks/guides, reputable references). Download the best ones into
`sources/<topic_slug>/` (PDFs/HTML/markdown), alongside anything the user provided. Keep a
`sources/<topic_slug>/SOURCES.md` index: filename, title, URL, one-line why. These files are what
the user will feed to Gemini Notebook per lesson, so name them clearly.

## Phase 3 — Design the syllabus → `references/content-schema.md`

Size the topic and write `content/<topic_slug>/syllabus.yaml` (the generalized "blueprint"):

- **Small topic** → a **single domain** with several subdomains (objectives).
- **Bigger topic** → **up to 10 domains**, each with subdomains (objectives).
  Record the intake's authoring language as `content_language` (for example, `English` or `Español`)
  and its validated NotebookLM locale code as `notebooklm_output_language` (for example, `en` or
  `es_419`) in `syllabus.yaml`. Assign each domain a `weight_pct` by importance; weights **must sum to 100**. Every objective gets
  a stable `code` (`"1.1"`, `"1.2"`, …), a `title`, and a `topics:` list. Confirm the outline with the
  user before authoring lessons.

## Phase 4 — Author content → `references/content-schema.md`

For every objective, author (all tagged with the objective `code`):

- **A lesson** `content/<topic_slug>/lessons/<objective>/<slug>.md` — Markdown with frontmatter,
  a body, and a `## Why It Matters` section. **The very first line of every lesson body is the
  video placeholder** (see below).
- **3–5 questions** `content/<topic_slug>/questions/<objective>.yaml` — single/multi choice, each
  choice (including distractors) carrying an explanation.
- **Optionally a lab** if hands-on was enabled.
  Plus, if enabled: the **mock/assessment** `mocks/<code>.yaml` and **strategy** content.

The mandatory first line of each lesson body (replace `<this document name>` with the lesson's own
source filename, and `<topic_slug>`/`<slug>` with this lesson's own values — the same ones used in
its file path `content/<topic_slug>/lessons/<objective>/<slug>.md`):

```
[placeholder]Upload this document and the documents in /sources to Gemini Notebook and ask it to create a video summary with the prompt "Limit the topics to what's in <this document name>.", then put it here. There's no drag-and-drop: click Generate Video above to do this automatically, or if you generate the video yourself, either ask your LLM assistant to place it, or do it yourself — save the download as media/<topic_slug>/<slug>.mp4, replace this entire placeholder block with a markdown video link to that file, then re-seed the content.[/placeholder]
```

The added sentence exists because the naive fix — just dropping the `.mp4` at the right path — is
not enough and silently looks like it worked: the video-status check falls back to "does the file
exist on disk," which flips to done immediately, while the lesson's actual body/DB row still holds
the raw placeholder text until something rewrites it. See `references/notebooklm-automation.md`'s
"manual-placement pitfall" note for the mechanism.

## Phase 5 — Scaffold or extend the app

- **NEW-APP:** build the repo per `references/tech-stack.md`, `references/backend.md`,
  `references/frontend.md`, `references/ui-design.md`. Copy `assets/index.css` verbatim into
  `frontend/src/index.css`. Copy `assets/favicon.ico`, `assets/favicon-32.png`,
  `assets/favicon-512.png`, and `assets/apple-touch-icon.png` verbatim into `frontend/public/`, then
  add the canonical favicon and theme-color tags from `references/frontend.md` to
  `frontend/index.html`. Copy `assets/gitignore.template` to `.gitignore` at the repo root, then run
  `git init`. Do **not** make an initial commit — leave that for the user to review and do themselves.
  Write the generated repo's own `AGENTS.md` and `README.md`.
  Also scaffold the Gemini Notebook video-placeholder resolution tooling per
  `references/notebooklm-automation.md`: the `media/` static mount in `app/main.py`, the `/media`
  vite proxy entry, `assets/lesson_video_service.py` → `app/services/lesson_video.py`,
  `assets/generate_lesson_video.py` → `scripts/generate_lesson_video.py`,
  `assets/VideoGenerationPanel.tsx` → `frontend/src/components/VideoGenerationPanel.tsx`, the two
  `video/generate` + `video/status` API endpoints and `VideoStatusOut` schema, the lesson page's
  "Generate Gemini Notebook video" button wiring (rendered inline by `Markdown` in place of the
  placeholder, not a separate box — see `references/frontend.md`), the opt-in `notebooklm`
  dependency group in `pyproject.toml`, and a "Generating lesson videos" section in the generated
  `README.md`. Also copy
  `assets/SelectionAsk.tsx` → `frontend/src/components/SelectionAsk.tsx` verbatim for the
  select-to-ask FAQ widget — see `references/frontend.md`'s Components section for why.
- **ADD-TOPIC:** follow `references/multi-topic.md` — usually you only add content + seed the new
  topic; no app-code changes if the app was built topic-aware (it should be).
- **If you parallelize backend and frontend work (e.g. across two subagents), both MUST be pinned to
  the exact API contract in `references/backend.md`'s "API contract" section** — that section is the
  literal source of truth (field names, nullability, flat-vs-nested shapes), not a paraphrase. Two
  independently-built halves working only from prose descriptions of "what the dashboard shows" or
  "what a lesson looks like" _will_ diverge — this happened in a real build (nested vs. flat dashboard
  data, `checks` vs `self_check`, a raw FAQ string vs. a parsed list, a list-returning endpoint treated
  as single-object, several fields the frontend expected that the backend never returned) and produced
  an app that built cleanly on both sides but crashed on first page load. A clean `npm run build` only
  proves the frontend's own types are internally consistent — it proves nothing about whether they
  match the real backend.
- **Before moving to Phase 6, run a live integration smoke test no matter how confident either side
  seemed in isolation:** start the backend, `curl` every endpoint the frontend calls with real seeded
  data, and diff the JSON response against `frontend/src/api/types.ts` field-for-field. Fix every
  mismatch (prefer adjusting the frontend to match the backend's contract, since the backend's tests
  already pin its behavior) and rebuild both sides before considering Phase 5 done. Then actually open
  the app in a browser (dashboard, a lesson detail page reached via the objective route, a quiz
  question, a lab) and check the browser console for errors — a 200 response on every network request
  does not mean the page rendered anything. **Explicitly check the topbar itself while inside a topic**
  (nav links to Lessons/Labs?/Strategy?/Badges/About, and the topic name) — a route-nesting mistake
  (`AppShell` as the parent of `TopicLayout` instead of nested inside it, see `references/frontend.md`
  Routing section) leaves the topbar silently stuck on "no topic loaded" on every page forever, with a
  perfectly fine-looking page body right below it and zero console errors. Don't just glance at whether
  the main content rendered — check the chrome around it too.

## Phase 6 — Seed, validate, run

Per the generated `README.md`:

1. Install the dependencies for the configured FAQ backend before seeding or starting the app.
   Build one `uv sync` command containing every optional group needed for this run; `uv sync`
   prunes packages from groups that are not selected, so syncing one group separately can remove
   another feature's dependencies:
   - With the intake-selected `claude_cli` or `codex_cli` backend, run `uv sync`; neither CLI
     backend needs a Python dependency group or an app-specific API key.
   - With `LEARNUP_LLM_BACKEND=openhands`, include `--group openhands`. This is required even
     though OpenHands is an optional dependency group; `uv sync` alone does not install
     `openhands.sdk`.
   - When NotebookLM tooling is enabled or being used, include `--group notebooklm` as well. For
     example, an OpenHands app that also generates lesson videos must run
     `uv sync --group openhands --group notebooklm`, not two separate sync commands.
   - If `.env` exists, read its `LEARNUP_LLM_BACKEND` value without exposing secrets. Treat an
     unset value as the backend selected during intake and compiled into `Settings`; fail loudly on
     an unknown value rather than silently selecting a different backend.
2. After syncing, verify the selected backend's availability with the app's backend check before
   starting the FAQ smoke test. For `openhands`, this must check both that `openhands.sdk` imports
   and that the configured provider settings are present. Do not auto-detect or fall back to
   another backend.
3. `uv run python -m app.content.seed` (loads every topic's content into DuckDB)
4. `uv run python -m app.content.validate` (fails loudly on coverage gaps / dangling tags)
5. Before starting either server, **check whether the default ports (8011 backend, 5173 frontend) are
   already bound by an unrelated process** using a platform-appropriate command or Python socket
   probe (see `references/tech-stack.md`). If so, do
   not kill it — pick free ports instead, update `frontend/vite.config.ts`'s proxy `target` to match
   the backend port you actually used, and report the real ports to the user (don't assume 8011/5173).
6. `uv run uvicorn app.main:app --reload --port <port>` and, from `frontend/`, `npm install && npm run
dev -- --port <port>`. Confirm `uv run uvicorn ...` works with **zero env-var overrides** — if it
   needs `LEARNUP_DATABASE_URL` (or any prefix) set manually to avoid a collision, that's a bug in
   `app/config.py`'s env-prefix setup, fix it rather than documenting the workaround.
7. Smoke-test the select-to-ask FAQ using the backend actually selected by configuration. With
   `claude_cli`, test the authenticated `claude` CLI on PATH. With
   `codex_cli`, test the authenticated `codex` CLI on PATH. With
   `LEARNUP_LLM_BACKEND=openhands`, test the configured provider/model (including a local Ollama
   endpoint when used) after installing the `openhands` group. If the selected backend cannot answer,
   report its concrete missing dependency, executable, credential, model, or endpoint; do not switch
   backends silently. See `references/backend.md`'s "Select-to-ask FAQ".
   Report the URLs. If validation fails, fix the content gap it names — do not weaken the validator.

## Reference index

| File                                  | Read during                                                                                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `references/intake.md`                | Phase 1 — the interview questions & module toggles                                                                                                      |
| `references/sources.md`               | Phase 2 — searching + downloading sources                                                                                                               |
| `references/content-schema.md`        | Phases 3–4 — syllabus, lessons, questions, labs, mocks, placeholder                                                                                     |
| `references/tech-stack.md`            | Phase 5 — stack, deps, DuckDB adaptation, commands                                                                                                      |
| `references/data-model.md`            | Phase 5 — DuckDB schema (multi-topic), SQLAlchemy models                                                                                                |
| `references/backend.md`               | Phase 5 — FastAPI structure, API surface, algorithms (SM-2, grading, readiness, mock), and the **authoritative API contract** every response must match |
| `references/frontend.md`              | Phase 5 — React pages, routing, topic picker, components                                                                                                |
| `references/ui-design.md`             | Phase 5 — design tokens, fonts, components (uses `assets/index.css`)                                                                                    |
| `references/multi-topic.md`           | ADD-TOPIC runs — extending an existing learn-up repo                                                                                                    |
| `references/notebooklm-automation.md` | Phase 5 scaffolding, and any GENERATE-VIDEO run — resolving the video placeholder (button / MCP on-demand / script / manual)                            |

**Assets (copy into the generated repo):**

- `assets/index.css` → `frontend/src/index.css` **verbatim** (the whole design system, incl. the
  `.video-placeholder` call-out). Optionally retheme only the color tokens at the top per topic.
- `assets/favicon.ico`, `assets/favicon-32.png`, `assets/favicon-512.png`, and
  `assets/apple-touch-icon.png` → `frontend/public/` **verbatim**. These are the topic-neutral
  learn-up book-and-fruit-tree mark; wire all four into `frontend/index.html` exactly as shown in
  `references/frontend.md`. Never regenerate or retheme them per topic.
- `assets/agents.template.md` → the generated repo's `AGENTS.md` (fill the `<…>` blanks).
- `assets/gitignore.template` → the repo root's `.gitignore` **verbatim** (excludes `learn_up.duckdb`
  and its `.wal` sidecar, `.claude/` runtime state, `.venv/`, `node_modules/`, `frontend/dist/`, `.env`,
  and — critically — `*.mp4`, since generated lesson videos under `media/<topic_slug>/` can be tens of
  MB each and don't belong in git history).
  Run `git init` right after copying it, before any files are ever staged.
- `assets/lesson_video_service.py` → `app/services/lesson_video.py` **verbatim**.
- `assets/generate_lesson_video.py` → `scripts/generate_lesson_video.py` **verbatim**.
- `assets/VideoGenerationPanel.tsx` → `frontend/src/components/VideoGenerationPanel.tsx` **verbatim**.
  All three are the "Generate Gemini Notebook video" button / script (Paths 1 & 3 of
  `references/notebooklm-automation.md`) — don't re-derive any of them from prose.
- `assets/SelectionAsk.tsx` → `frontend/src/components/SelectionAsk.tsx` **verbatim** — the
  select-to-ask trigger + question panel. A from-scratch reimplementation shipped a real bug once
  (panel unmounts itself the instant you click into its own textbox); see `references/frontend.md`'s
  Components section for the mechanism.

Work through the phases top-down. Keep the user in the loop at the syllabus outline (Phase 3) and
before a long content-authoring pass (Phase 4).
