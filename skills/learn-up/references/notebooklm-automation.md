# Resolving the Gemini Notebook video placeholder

## Contents

- Four generation paths and shared service behavior
- In-app generation button
- MCP-driven generation from Claude Code or Codex
- Terminal script and manual placement
- Static serving and scaffolding checklist
- Adding videos to an existing multi-topic app

Every lesson opens with the mandatory placeholder (`references/content-schema.md`) telling the
learner which source document(s) to feed Gemini Notebook. There are **four ways** to turn that into a
real `.mp4` link — offer all four, let the user pick. None of them are automatic/bulk: Gemini
Notebook's free tier caps video generation to roughly **3 per day** (the user's own reported experience; this
is undocumented and account/tier-dependent, so treat it as an approximate caution, not a hard
constant, and never hardcode a counter against it). **Generate one lesson's video at a time, only
when asked** — never loop over every lesson in a topic.

## The four paths

1. **In-app "Generate Gemini Notebook video" button (default, easiest)** — the placeholder itself renders
   as this button (not a button plus a separate call-out). The user clicks it, the backend runs
   generation as a background job, the page polls and swaps in the video when ready. Needs
   `notebooklm-py`'s CLI installed + logged in _on the machine running the backend_ — no chat, no
   terminal command, just a click.
2. **MCP-driven, on demand, via chat** — the user configures the `notebooklm-mcp-cli` MCP server
   once; from then on, whenever they reach a lesson and want its video, they just ask you in chat
   (e.g. "generate the Gemini Notebook video for lesson 1.1") and **you** do it live via MCP tool calls.
   No installs on the backend machine, no button click — useful when the backend runs somewhere you
   can't easily `uv sync --group notebooklm` (e.g. a remote/hosted deploy of this local app).
3. **Terminal script**, `scripts/generate_lesson_video.py` — for a user who wants a repeatable
   command instead of clicking a button or opening a chat. Runs the _same_ underlying code as the
   button (both call `app/services/lesson_video.py`), just from a shell instead of an HTTP request.
   Requires the backend dev server to be stopped first (DuckDB is single-writer — see "Shared
   service module" below).
4. **Fully manual** — unchanged from before this feature existed: the user uploads sources to
   notebooklm.google.com themselves, generates a video, downloads it, and either pastes the link in
   themselves or asks you to splice it into the lesson file. Always available, needs no installs.

All four converge on the same artifact convention (see "Static serving" below), so a topic can
freely mix paths lesson by lesson.

## Shared service module: `app/services/lesson_video.py`

Paths 1 and 3 are two thin front-ends over one piece of app code — **never duplicate the
generation logic between the button's backend endpoint and the script**, that's exactly the kind
of divergence that bit this app's API contract before (`references/backend.md`'s API contract
section). Full source: `assets/lesson_video_service.py`, copied verbatim to
`app/services/lesson_video.py` (never re-derive it from prose, same rule as `assets/index.css`).

It wraps the `notebooklm` CLI (from `notebooklm-py`) via `subprocess`, not its Python API — the CLI
surface documented in that project's README is the more stable of the two, and shelling out means
failures surface the tool's own error text instead of silently mis-guessing an internal method
signature. Key functions:

The generated app must expose `LEARNUP_NOTEBOOKLM_PROFILE` (default `default`) and pass that
profile to every NotebookLM CLI command, including the auth check. This lets video generation use
a named Plus-account profile when the default browser account is different. Authenticate that
profile with NotebookLM's `--profile-name`/`--account` browser-cookie options, then set the app
variable before generating videos; never silently switch accounts.

The shared service must print the auth-check result and every CLI command's exit code, stdout, and
stderr with a `[video]` prefix. The background worker must also print the full traceback when a
generation fails. Video generation is asynchronous, so returning an error only through the HTTP
status response is insufficient for diagnosing NotebookLM failures in a systemd/uvicorn log.

- `find_lesson_path` / `find_lesson_slug_by_objective` — locate a lesson file; no DB needed.
- `start_generation(topic_slug, lesson_slug)` — validates synchronously (not already running, has a
  placeholder), then spawns a **background thread** running `generate_lesson_video`. Used by the
  API endpoint so a click returns immediately instead of blocking the request for minutes.
- `get_job_status(topic_slug, lesson_slug)` — in-memory job status (`idle`/`running`/`done`/`error`);
  if no job is tracked (e.g. after a backend restart), falls back first to checking whether the
  `.mp4` already exists on disk (`"done"`), then to whether `.video_tasks.json` has a pending
  `task_id` for this lesson (`"running"`) — only reporting `"idle"` once both come up empty. That
  second fallback matters: without it, a restart mid-generation would report `"idle"` even though
  Gemini Notebook is still working on a task this app already submitted, and the UI would show the
  "Generate" button again as if nothing had been requested (see "Resumable generation" below).
- `generate_lesson_video(topic_slug, lesson_slug)` — the actual work: ensures the CLI is
  installed/logged in, gets-or-creates one Gemini Notebook per topic
  (`media/<topic_slug>/.notebook.json`), syncs any not-yet-added source files
  (`media/<topic_slug>/.sources_added.json`), generates + downloads the video, rewrites the
  lesson's placeholder in the `.md` file, **and updates the DB row directly** (`Lesson.body_markdown`
  / `why_it_matters_markdown`) by reusing `app/content/seed.py`'s own `load_lesson_file` /
  `split_why_it_matters` — reuse those exact functions, don't re-derive the frontmatter/body-split
  parsing a second time, or the two will drift the moment either one is edited.

**Resumable generation — never re-request a video the CLI already asked Gemini Notebook for.**
`_JOBS` is in-memory only, so a backend restart (crash, reboot, `--reload` picking up an unrelated
change) mid-generation loses all record of it. Left unaddressed this is a two-part failure: (1) the
status endpoint would report `"idle"` (nothing to fall back to yet — this is the gap
`get_job_status`'s `.video_tasks.json` check above closes) so the UI shows the "Generate" button
again as if nothing happened, and (2) clicking it naively would call `notebooklm generate video` a
second time, burning another of the ~3 daily quota slots and leaving a duplicate artifact sitting in
the notebook for a video that may already be sitting there finished. Part 2 is fixed by splitting
the single blocking `generate video --wait` call into three steps, with the task/artifact ID
persisted to disk **before** the long wait:

1. `notebooklm generate video <instructions> --notebook <id> --style whiteboard --json` (no
   `--wait` — returns `{"task_id": ..., "status": "pending"}` almost immediately).
2. Persist `{lesson_slug: {"task_id": ..., "started_at": <iso8601 UTC>}}` to
   `media/<topic_slug>/.video_tasks.json` right away.
3. `notebooklm artifact wait <task_id> --notebook <id> --timeout <LESSON_VIDEO_WAIT_TIMEOUT_SECONDS>`
   (Gemini Notebook's own `generate video --wait` default is 1800s; match it explicitly since
   `artifact wait`'s own default is only 300s), then `notebooklm download video <out_path>
--notebook <id> --artifact <task_id> --force`, then clear the entry from `.video_tasks.json`.

`_generate_and_download` checks `.video_tasks.json` for this lesson **first**, before step 1 — if a
task ID is already recorded (a previous run got past step 2 but never reached the "clear" at the
end), it skips straight to step 3 with the existing task_id instead of generating again. This is
retry-safe at every point: crash before step 1 finishes → nothing persisted yet, safe to retry from
scratch; crash during the wait or download → task_id already on disk, retry resumes without a new
`generate` call. Confirmed live: a real generation was killed and resumed mid-wait during this
feature's build, and the resumed run correctly skipped straight to `artifact wait` + `download`
instead of calling `generate` again.

**A persisted task_id must expire, or a crash/error turns "resumable" into "stuck forever."**
`_clear_pending_task` only ever runs after a fully successful download (`_generate_and_download`'s
last line) — if the run instead _errors_ partway through step 3 (rate limit, network error,
Gemini Notebook-side failure, an unhandled exception of any kind), the exception propagates up to
`_run_job`, which records the job as `"error"` in `_JOBS`, but the `.video_tasks.json` entry is
never touched. `_JOBS` itself is only in-memory, so the moment the backend restarts that error
state is gone too — and `get_job_status` falls through to the `.video_tasks.json` check, finds the
still-there task_id, and reports `"running"` again, forever, for a generation nothing is actually
doing anything about. **Confirmed live in this app**: a lesson's video sat reported as "running" for
several days after a generation attempt had silently failed, with the stale task_id its only trace.
Fixed by making `_load_pending_task` treat any entry older than
`LESSON_VIDEO_TASK_STALE_HOURS` (`app/constants.py`, default 12 — real generations finish in
minutes, so anything measured in hours is abandoned, not in progress) as gone: it self-heals by
calling `_clear_pending_task` and returning `None`, which flows through to both callers correctly —
`get_job_status` reports `"idle"` again (button reappears) and `_generate_and_download` starts a
fresh `generate` call instead of trying to resume a task that's probably long gone from Gemini
Notebook's own side too. Entries saved before this field existed (a bare `{lesson_slug: task_id}`
string, no `started_at`) are treated as stale unconditionally, since their age can't be verified —
don't special-case "old format, assume fresh," that's exactly backwards for a bug whose entire
symptom is an old entry being trusted forever.
`media/**/.video_tasks.json` is gitignored alongside `.notebook.json`/`.sources_added.json` (see
"Static serving" below).

**Non-obvious gotcha, worth preserving in the generated code:** `app/db.py` opens a DuckDB
connection and runs `CREATE SCHEMA IF NOT EXISTS` **at import time** (existing app behavior, not
introduced by this feature). That means anything importing `app.db` — directly or transitively —
requires exclusive DB access. If `lesson_video.py` imported `app.db`/`app.content.seed`/`app.models`
at module level, even `--dry-run` in the script (which never touches the DB) would fail whenever
the backend dev server is already running and holding DuckDB's single-writer lock. Fix: those three
imports are **local, inside `generate_lesson_video()`**, not at module top level — keep them that
way. This was caught by actually running `--dry-run` while the dev server was up during this
feature's build, not by reasoning about it in the abstract; don't skip the equivalent live check
when building this from scratch.

**Set NotebookLM's output language explicitly, then keep language out of the prompt.** NotebookLM's
artifact language is a global setting for the selected account/profile, not a per-notebook prompt
option. `generate_lesson_video()` reads the topic's exact locale code from
`notebooklm_output_language` in `content/<topic_slug>/syllabus.yaml`. Immediately before submitting
a new generation, it must:

1. Run `notebooklm --profile <profile> language list --json`.
2. Fail loudly unless the configured code exists in the returned `languages` map.
3. Run `notebooklm --profile <profile> language set <code> --json`.
4. Submit `notebooklm generate video` without any language wording in its instruction.

The setting affects every notebook in the account, so protect steps 3–4 with one process-wide lock.
That prevents two in-app jobs for topics with different locales from switching the global setting
between the `language set` and `generate video` commands. External NotebookLM clients can still
change the same account setting, so keep the two commands adjacent. A resumed task does not need a
new language change because its generation request was already submitted.

**Prompt quality — give Gemini Notebook the lesson title and let it pick the topics, don't
pre-extract them.** The original instruction text was just `Limit the topics to what's in <source filename>.` —
enough to scope the _source_, but nothing tells Gemini Notebook what the _lesson itself_ emphasizes within
that source, or gives the video a sensible title, so generated videos could drift from what the
lesson actually covers. `generate_lesson_video()` now builds:

```python
frontmatter, _ = load_lesson_file(lesson_path)
title = frontmatter.get("title", lesson_slug)
instructions = (
    f'Create a video titled "{title}". '
    f"Limit the topics to what's in {match.group('doc')}, and pick up to 6 topics to cover "
    "from that document."
)
```

Deliberately **not** pre-extracting topics ourselves (e.g. by scraping `##` headings) — that would
need either a second LLM call or a brittle heuristic; simpler and more robust to just tell Gemini
Notebook to pick up to 6 topics from the named source document itself. A `print(f"[video] Gemini
Notebook prompt for {topic_slug}/{lesson_slug}: {instructions}")` right after building it is the debug line for
seeing the exact prompt sent — deliberately a bare `print`, not `logger.info`: this app never calls
`logging.basicConfig`/configures the root logger for the live FastAPI process (only the standalone
`seed.py`/`validate.py` scripts do, in their own `main()`), and uvicorn's default logging config only
touches its own `uvicorn`/`uvicorn.access`/`uvicorn.error` loggers — confirmed by inspecting
`uvicorn.config.LOGGING_CONFIG` — so a `logger.info()` call here would silently never print under
`uvicorn --reload`. `print()` always reaches the tmux pane / terminal running the dev server.

## Path 1 — in-app button

**Backend** (`app/api/lessons.py`, alongside the existing lesson routes):

```python
from app.services import lesson_video
from app.schemas import VideoStatusOut

@router.post("/{slug}/video/generate", response_model=VideoStatusOut)
def trigger_lesson_video_generation(
    topic_slug: str, slug: str, session: Session = Depends(get_session)
) -> VideoStatusOut:
    topic = get_topic_or_404(topic_slug, session)
    lesson = _get_lesson_by_slug(session, topic.id, slug)
    try:
        lesson_video.start_generation(topic_slug, lesson.slug)
    except lesson_video.LessonVideoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return VideoStatusOut(status="running")


@router.get("/{slug}/video/status", response_model=VideoStatusOut)
def get_lesson_video_status(
    topic_slug: str, slug: str, session: Session = Depends(get_session)
) -> VideoStatusOut:
    topic = get_topic_or_404(topic_slug, session)
    lesson = _get_lesson_by_slug(session, topic.id, slug)
    return VideoStatusOut(**lesson_video.get_job_status(topic_slug, lesson.slug))
```

Add to `app/schemas.py` (see `references/backend.md`'s API contract section — this belongs there
too):

```python
class VideoStatusOut(BaseModel):          # GET/POST .../lessons/{slug}/video/*
    status: str                            # "idle" | "running" | "done" | "error"
    error: str | None = None
```

`start_generation` raises `LessonVideoError` synchronously for "already running" or "already has a
video" (both map to 409) — those are checked before the background thread spawns, so a bad click
fails fast instead of after a slow no-op job. Async failures (CLI missing, not logged in, Gemini
Notebook API errors) only surface later, via the status endpoint's `error` field.

**Frontend:**

- `frontend/src/api/types.ts` — add:
  ```typescript
  export type VideoJobStatus = "idle" | "running" | "done" | "error";
  export interface VideoStatus {
    status: VideoJobStatus;
    error: string | null;
  }
  ```
- `frontend/src/api/http.ts` — add to `createTopicApi`:
  ```typescript
  generateLessonVideo: (slug: string): Promise<VideoStatus> =>
    post<VideoStatus>(`${base}/lessons/${slug}/video/generate`),
  getLessonVideoStatus: (slug: string): Promise<VideoStatus> =>
    get<VideoStatus>(`${base}/lessons/${slug}/video/status`),
  ```
- `frontend/src/components/VideoGenerationPanel.tsx` — copy `assets/VideoGenerationPanel.tsx`
  verbatim. Self-contained: takes `onGenerate`/`onPollStatus`/`onReady` callbacks (delegation
  pattern, matching how `TeachingArticle` already takes `onAsk`/`onDeleteFaq` rather than reaching
  into `useTopicContext` itself), polls every 5s while `running`, renders nothing once `done`
  (the lesson refetch already swapped the placeholder for the real `<video>`). Renders as a single
  amber `.video-placeholder.video-placeholder--panel` box — the button plus one short line
  ("Rate-limited — see README..."), not a separate box: the user sees this on every lesson and
  should get a glance-and-move-on reminder, not a paragraph.
- `Markdown.tsx` — accepts an optional `video` prop (same `{ onGenerate, onPollStatus, onReady }`
  shape) and renders `<VideoGenerationPanel {...video} />` in place of the `[placeholder]` call-out
  itself (via the custom `div` renderer keyed on `className === "video-placeholder"`) — see
  `references/frontend.md`'s "Render the Gemini Notebook placeholder" section for the exact mechanism.
- `TeachingArticle.tsx` — accepts an optional `video` prop
  (`{ onGenerate, onPollStatus, onReady }`) and threads it straight through to `Markdown`, it does
  **not** render `VideoGenerationPanel` itself:
  ```tsx
  <Markdown video={video}>{bodyMarkdown}</Markdown>
  ```
- `LessonDetailPage.tsx` — decide whether to pass `video` at all by checking the lesson's own
  markdown for the placeholder marker (cheap, no extra schema field needed):
  ```tsx
  const videoPending = lesson.body_markdown.includes("[placeholder]");
  async function handleVideoReady() {
    setLesson(await api.getLessonBySlug(lesson!.slug));
  }
  // ...
  video={videoPending ? {
    onGenerate: () => api.generateLessonVideo(lesson.slug),
    onPollStatus: () => api.getLessonVideoStatus(lesson.slug),
    onReady: handleVideoReady,
  } : undefined}
  ```
- `index.css` — add the `.video-placeholder--panel` (flex-row layout for the button + text) and
  `.video-placeholder__error` (uses `--rust-ink`) modifiers near the existing `.video-placeholder`
  rules — see `assets/index.css`. **Don't invent new custom properties** like
  `--border`/`--surface-muted` that don't exist in `assets/index.css`; grep the token list at the
  top of the file first.

**Verify like this feature was verified in the real build:** click the button live (chrome-devtools
MCP or by hand), confirm it shows "Generating…", and — since the `notebooklm` CLI won't be
installed on most dev/build machines — confirm the poll cycle surfaces a clean error banner with a
retry button rather than hanging forever. That's the realistic path most builds will actually
exercise; don't skip it just because a real end-to-end video generation isn't testable without a
live Gemini Notebook login.

## Path 2 — MCP-driven, via chat

### One-time setup you guide the user through

```bash
uv tool install notebooklm-mcp-cli   # ships two binaries: `nlm` (CLI) and `notebooklm-mcp` (server)
nlm login                            # opens a browser, extracts session cookies; --profile NAME for multiple accounts
nlm setup add claude-code            # Claude Code
nlm setup add codex                  # Codex CLI and app
```

Run only the setup command for the user's active host. If that client name is unavailable in the
installed version, generate a generic config with `nlm setup add json`, or register the
`notebooklm-mcp` executable through the host's own MCP command. Claude Code uses `claude mcp add`;
Codex uses `codex mcp add <name> -- <command>`. Locate the executable with `command -v`/`which` on
POSIX or `where.exe` on Windows. Reload the host's MCP configuration as its current UI/CLI directs,
then verify the NotebookLM session with `nlm login --check`.

This is a **third-party, unofficial client for an undocumented Google API** — its own README says
so. Exact MCP tool names can drift between versions. Before relying on a specific tool name, check
what's actually connected (list available MCP tools) rather than assuming the names below are
still current.

### What you do when the user asks for a specific lesson's video

1. Identify the topic_slug and the lesson file (`content/<topic_slug>/lessons/<objective>/<slug>.md`).
   Read its placeholder line to get the referenced source filename (the `<this document name>` from
   `references/content-schema.md`'s exact placeholder text).
2. **Reuse one Gemini Notebook per topic** — don't create a new one per lesson. Check whether
   one already exists (list notebooks, match by the topic's `topic_name` from `syllabus.yaml`); if
   not, create it.
3. Make sure every file in `sources/<topic_slug>/` (except `INTAKE.md`/`SOURCES.md`, which are your
   own bookkeeping, not study material) has been added as a source to that notebook. Skip files
   already added — check the notebook's current source list first, don't blindly re-add.
4. Read `notebooklm_output_language` from the topic syllabus. List the currently supported
   NotebookLM languages, fail if the configured code is absent, and set that exact code before
   triggering generation. Then use an instruction of the form `Create a video titled "<lesson
title>". Limit the topics to what's in <source filename>, and pick up to 6 topics to cover from
that document.` Do not duplicate the language in the prompt.
5. Poll/wait for the generation to finish, then download the artifact to
   `media/<topic_slug>/<slug>.mp4` (create the directory if needed).
6. Edit the lesson file: replace the whole `[placeholder]...[/placeholder]` block with
   `[Watch the video summary](/media/<topic_slug>/<slug>.mp4)`. Also update the DB row directly if
   you have DB access in this session (same fields `generate_lesson_video` updates) so the running
   app reflects it without a manual re-seed; if you don't have DB access, tell the user a re-seed
   (`uv run python -m app.content.seed`) or backend restart will be needed to see it in the app.
7. Tell the user it's done and where it's linked from.

If generation fails or the account appears rate-limited, say so plainly and suggest the manual path
as a same-day fallback — don't retry in a loop burning more of the daily quota.

## Path 3 — terminal script

```bash
uv sync --group notebooklm    # installs notebooklm-py[browser,cookies] as an opt-in dependency group
uv run notebooklm login       # once
uv run python scripts/generate_lesson_video.py <topic_slug> --objective <code>
uv run python scripts/generate_lesson_video.py <topic_slug> --objective <code> --dry-run   # preview only
```

Full source: `assets/generate_lesson_video.py`, copied verbatim to
`scripts/generate_lesson_video.py`. It's a thin `argparse` wrapper — all the real logic lives in
`app/services/lesson_video.py` (see above), imported with `sys.path.insert(0, ...)` at the top
since the script isn't run as a package module (`uv run python scripts/foo.py` does **not** put the
repo root on `sys.path` the way `uv run python -m app.main` would — this was caught by actually
running the script, not assumed).

**Must run with the backend dev server stopped** — DuckDB is single-writer, and
`generate_lesson_video()`'s DB update will fail with a lock error otherwise. If the user wants to
generate a video while the app is running, point them at Path 1 (the button) instead, which runs
in-process and doesn't hit this.

## Path 4 — fully manual

Unchanged: the user (or you, if asked) uploads the files named in the placeholder to
notebooklm.google.com, generates a video with the same "Create a video titled..." prompt (see
above), downloads it, and it needs to land at `media/<topic_slug>/<slug>.mp4` with the lesson's
placeholder replaced
by `[Watch the video summary](/media/<topic_slug>/<slug>.mp4)`. If the user hands you the
downloaded file's path, do the move + edit for them (and the DB update, per Path 2 step 6, if you
have DB access).

**Manual-placement pitfall (confirmed in a real build — don't skip either half of this):** dropping
the `.mp4` at the right path is necessary but not sufficient, and the failure mode is silent rather
than a visible error. `get_job_status` has no way to know a video was placed by hand, so it falls
back to "does `media/<topic_slug>/<slug>.mp4` exist on disk" — which flips to `"done"` the instant
the file lands there, regardless of whether anything else happened. But the lesson's actual
`body_markdown` (both the `.md` file and the DB row `generate_lesson_video()` would normally update)
still holds the raw `[placeholder]...[/placeholder]` text until _something_ rewrites it — the status
endpoint and the displayed content are two independent signals that only the button/script/MCP paths
keep in sync automatically. A user who places a file by hand and reloads the page will see the
"Generate Gemini Notebook video" flow report done while the placeholder call-out is still literally shown
instead of a video. Both steps are required every time a video is placed outside the button: (1) the file at
`media/<topic_slug>/<slug>.mp4`, (2) the lesson file's placeholder block replaced with
`[Watch the video summary](/media/<topic_slug>/<slug>.mp4)`, followed by either a DB update (Path 2
step 6) or a full re-seed (`uv run python -m app.content.seed`, which requires the backend dev
server to be stopped first per Path 3's DuckDB single-writer note, then restarted).

## Static serving (required app scaffolding — Phase 5)

Every generated app must be able to serve whatever path produced the video, at the same URL
convention, whether or not the user ever configures notebooklm-py/notebooklm-mcp-cli:

- A `media/` directory at the repo root, sibling to `content/` and `sources/`, holding
  `<topic_slug>/<slug>.mp4` (plus the three small per-topic JSON bookkeeping files — all gitignored:
  `media/**/*.mp4`, `media/**/.notebook.json`, `media/**/.sources_added.json`,
  `media/**/.video_tasks.json`).
- `app/main.py` mounts it: `MEDIA_ROOT.mkdir(exist_ok=True)` then
  `app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")`, where
  `MEDIA_ROOT = Path(__file__).resolve().parents[1] / "media"` (same pattern `app/content/seed.py`
  already uses for `CONTENT_ROOT`, one directory shallower since `main.py` lives at `app/main.py`).
- `frontend/vite.config.ts` proxies `/media` to the backend, identically to the existing `/api`
  entry.
- The Markdown renderer's existing `.mp4` → `<video controls src=…>` rule (`references/frontend.md`)
  needs no change — it already passes the `href` straight through as `src`, so a leading
  `/media/<topic_slug>/<slug>.mp4` link resolves through the dev proxy and in production alike.

## Phase 5 scaffolding checklist (NEW-APP)

- Copy `assets/lesson_video_service.py` verbatim to `app/services/lesson_video.py`.
- Copy `assets/generate_lesson_video.py` verbatim to `scripts/generate_lesson_video.py`.
- Copy `assets/VideoGenerationPanel.tsx` verbatim to `frontend/src/components/VideoGenerationPanel.tsx`.
- Add the two API endpoints to `app/api/lessons.py` and `VideoStatusOut` to `app/schemas.py` (Path 1
  section above).
- Add the `types.ts`/`http.ts` entries and wire `TeachingArticle`/`LessonDetailPage` (Path 1 section
  above).
- Add the `.video-placeholder--panel` / `.video-placeholder__error` CSS blocks.
- Add an **opt-in** dependency group to `pyproject.toml` (not a default dependency — most users
  won't touch paths 1 or 3 immediately):
  ```toml
  [dependency-groups]
  dev = ["pytest>=8.0"]
  notebooklm = ["notebooklm-py[browser]>=0.8.0a3"]
  ```
  (Check PyPI for the current latest version at build time — `notebooklm-py` was pre-1.0/alpha as
  of this writing, so a bare `>=0.8` can be unsatisfiable if only alpha releases exist; pin to
  whatever's actually published, prereleases included.)
- Document all four paths in the generated `README.md` (a "Generating lesson videos" section) and
  add the one-line mention of user-paced/rate-limited generation to the generated `AGENTS.md`
  (see `assets/agents.template.md`).
- Run the live-button smoke test described at the end of the Path 1 section before considering
  Phase 5 done.

## ADD-TOPIC runs

Nothing topic-specific to scaffold — `media/`, the static mount, the service module, the endpoints,
and the button are all app-level and already exist after the first topic's build. A new topic just
gets its own `media/<new_topic_slug>/` subdirectory, created lazily the first time any path is used
for that topic's first video.
