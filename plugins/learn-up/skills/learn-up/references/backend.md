# Phase 5 — Backend (FastAPI + DuckDB)

## Contents

- Configuration, database, media, topic transfer, and API contract
- Constants and core algorithms
- Gamification and select-to-ask FAQ
- Claude CLI, Codex CLI, and OpenHands backends
- Content seeding and validation

Synchronous FastAPI backend. Path operations are plain `def`; the DB session is a sync SQLAlchemy
session yielded by a dependency. Models per `references/data-model.md`.

## `app/config.py`

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LEARNUP_", extra="ignore")
    database_url: str = "duckdb:///learn_up.duckdb"
    db_schema: str = "learn"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## `app/db.py`

```python
from collections.abc import Iterator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
with engine.begin() as conn:
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
```

`app/main.py` creates the FastAPI app, calls `Base.metadata.create_all(engine)` on startup,
includes routers, exposes `GET /api/health` (`SELECT 1`), and configures the mandatory localhost
security middleware stack. It also mounts a static `/media` directory for lesson videos — see
"Media static mount" below.

## Localhost security & origin/host validation stack

Generated apps run locally and use a single default learner user (no user login/password system),
but **must protect the loopback API against DNS rebinding, cross-origin data exfiltration, and
drive-by browser requests from foreign websites**.

In `app/main.py`, configure this mandatory multi-layer defense stack:

### 1. Loopback Host header validation (`TrustedHostMiddleware`)

Add Starlette/FastAPI `TrustedHostMiddleware` to reject any request carrying a foreign or
attacker-controlled `Host` header (such as `Host: evil.com:8011` resulting from DNS rebinding):

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "[::1]",
        "testclient",
        "localhost:*",
        "127.0.0.1:*",
        "[::1]:*",
    ],
)
```

Requests with unlisted `Host` headers fail immediately with `400 Bad Request`.

### 2. Browser Origin & Fetch-Metadata validation middleware

Add middleware (or an app-level base HTTP middleware) to validate browser-initiated calls:

- **Fetch-Metadata:** If `Sec-Fetch-Site: cross-site` is present on any `/api/*` request, reject
  immediately with `403 Forbidden`. Requests with `same-origin`, `same-site`, or `none` (non-browser
  tools / direct top-level navigation) are permitted.
- **Origin / Referer:** When an `Origin` header is present, verify that its origin matches allowed
  loopback origins (`http://localhost:<frontend_port>`, `http://127.0.0.1:<frontend_port>`,
  `http://[::1]:<frontend_port>`, and backend loopback origins). If a foreign `Origin` is present,
  reject with `403 Forbidden`.
- **No permissive CORS or PNA:** Do **not** add `CORSMiddleware` with `allow_origins=["*"]` or allow
  arbitrary origins. Do not enable `Access-Control-Allow-Private-Network`.

### 3. Per-run unguessable API token (`X-LearnUp-Token`)

Generate an unguessable cryptographic token on backend startup (`secrets.token_urlsafe(32)`),
stored in `app.state.api_token` (or read from `LEARNUP_API_TOKEN` if set in settings):

- **Bootstrap endpoint:** Expose `GET /api/auth/token` returning `{"token": app.state.api_token}`.
  This endpoint is strictly restricted: it requires the client to connect from loopback (`127.0.0.1` /
  `::1`) and rejects `Sec-Fetch-Site: cross-site`. The local frontend calls this endpoint once on
  initial startup to retrieve its session token.
- **Header enforcement:** All `/api/*` requests (except `GET /api/health` and `GET /api/auth/token`)
  must include header `X-LearnUp-Token: <token>`. Requests with missing or mismatched tokens are
  rejected with `401 Unauthorized`.

## Media static mount (Gemini Notebook lesson videos)

`app/main.py` must also serve `media/<topic_slug>/<slug>.mp4` files at `/media/...`, regardless of
whether the user ever generates a video — the mount just needs to exist so the frontend's `.mp4`
link renderer (`references/frontend.md`) has something to point at once one does exist:

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

MEDIA_ROOT = Path(__file__).resolve().parents[1] / "media"
...
MEDIA_ROOT.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")
```

`app/api/lessons.py` also gets two endpoints backing the lesson page's "Generate Gemini Notebook video" button —
`POST /{slug}/video/generate` (starts a background job, 409 if already running or already has a
video) and `GET /{slug}/video/status` (polled by the frontend). Both are thin wrappers over
`app/services/lesson_video.py` (copied from `assets/lesson_video_service.py`) — full endpoint code,
the service module's contract, and why its DB-touching imports must stay lazy (not module-level) in
`references/notebooklm-automation.md`'s "Path 1" and "Shared service module" sections. Add
`VideoStatusOut` to `app/schemas.py`'s API contract (below) alongside the rest.

## API surface

Same shape as the template plus a **topics** router for the multi-topic picker. All content/attempt
routes take a topic via the path (`/api/t/{topic_slug}/…`) or a query/body `topic_slug`, so topics
stay isolated. Recommended routers:

- `app/api/auth.py` (or in `app/main.py`) → `GET /api/auth/token` — session token bootstrap for the
  local frontend.
- `app/api/topics.py` → prefix `/api/topics`
  - `GET  /api/topics` — list topics (slug, name, description, counts) for the home picker.
  - `GET  /api/topics/{slug}` — one topic's metadata + enabled modules.
- `app/api/topic_transfer.py` — copy `assets/topic_transfer_router.py` verbatim and include its
  router without changing the wire behavior:
  - `GET /api/t/{topic_slug}/export` — export one `.learnup.zip` archive.
  - `POST /api/topics/import?dry_run=true` — validate a capped raw ZIP request in a temporary
    directory and return a side-effect-free report.
  - `POST /api/topics/import?dry_run=false&confirm=true` — repeat validation and perform a confirmed
    import/update with backup and rollback.
- `app/api/catalog.py` → prefix `/api`
  - `GET  /api/t/{topic_slug}/domains` — domains with nested objectives.
  - `GET  /api/t/{topic_slug}/content-info` — version/counts.
  - `GET  /api/t/{topic_slug}/about` — app version plus the complete app, intake, source, and
    topic-change Markdown used by AboutPage. Implement the path and fail-loud file handling exactly
    as specified in `references/about.md`.
- `app/api/lessons.py` → prefix `/api/t/{topic_slug}/lessons`
  - `GET  ""` (list), `GET /objective/{code}`, `GET /{slug}`.
  - **`GET /objective/{code}` returns a `list[LessonListItem]`, not a single lesson** — an objective
    can in principle have more than one lesson. Callers that want "the lesson for this objective"
    (e.g. the frontend's "practice this objective" link) must take the first match and then fetch
    the full lesson via `GET /{slug}` using that item's `slug`. Do not make this endpoint return a
    single `LessonOut` — see `references/frontend.md` for the matching client-side pattern.
  - `POST /{slug}/questions` (select-to-ask FAQ — see below), `DELETE /{slug}/faq/{index}`.
  - **`video_status` on `LessonListItem`** — both list endpoints' `_lesson_list_item(lesson,
topic_slug)` helper (note it takes `topic_slug`, not just the ORM row) computes it as `"done"`
    if `"[placeholder]"` is no longer in `body_markdown`, else
    `lesson_video.get_job_status(topic_slug, lesson.slug)["status"]` — reusing the exact same
    in-memory-job/pending-task/file-existence check the video status endpoint already does (see
    `references/notebooklm-automation.md`), so the list and the detail page's polling can never
    disagree about a given lesson's state. Cheap to call per lesson: no Gemini Notebook network calls,
    just an in-memory dict lookup plus, at worst, one small JSON file read.
- `app/api/attempts.py` → prefix `/api/t/{topic_slug}/attempts`
  - `POST ""` create (`attempt_type` + optional `domain_code`/`objective_code`/`question_count`).
  - `GET  /{id}`, `POST /{id}/responses`, `POST /{id}/finish`, `GET /{id}/review`.
  - **`_attempt_out`'s per-question `is_correct`** — build a `{question_id: is_correct}` dict from
    `attempt.responses` (not just the `answered_ids` set the "was this answered" flag alone would
    need) and pass `correctness_by_question.get(aq.question.id)` through as `QuestionPromptOut.is_correct`
    for every question, answered or not (`None` if unanswered). This is what lets `QuizRunner`'s
    question-navigator color a _resumed_ attempt's already-answered buttons by correctness, not just
    grey out "answered" — a freshly-submitted answer in the current session already has its result
    in local state, but a question answered in an earlier session before a reload has nothing else
    to go on.
- `app/api/progress.py` → prefix `/api/t/{topic_slug}/progress`
  - `GET /dashboard`, `GET /review-queue`, `GET /badges`, `POST /streak-freeze`.
  - `GET /badges` returns a **flat** `list[BadgeOut]` (each with `earned_at: datetime | None`) — it
    does not pre-split into earned/locked. The frontend groups by `earned_at is not None` itself.
- `app/api/labs.py` (if enabled) → prefix `/api/t/{topic_slug}/labs`
  - `GET ""`, `GET /{slug}`, `POST /{slug}/check`, `POST /{slug}/questions`, `DELETE /{slug}/faq/{index}`.
  - `GET /{slug}/self-check/{position}/hint`, `GET /{slug}/self-check/{position}/answer` — back the
    self-check "Hint" / "Show answer" buttons. Both are on-demand `GET`s, not fields embedded in
    `LabOut` — the raw `expected_value` never rides along in the initial page load, only gets computed
    and returned when the learner explicitly asks. See "Algorithm: lab self-check hints" below.
- `app/api/strategy.py` (if enabled) → prefix `/api/t/{topic_slug}/strategy`
  - `GET /lessons`, `GET /lessons/{slug}`, `POST /lessons/{slug}/read`, `GET /drill`,
    `POST /questions/{id}/check`, plus the FAQ routes.

A single **default user** is used (create-on-first-use, tolerate the race). No multi-user login or
password system is used, but all `/api/*` requests are secured by the localhost Host, Origin,
Fetch-Metadata, and token validation stack specified above.

## Topic-transfer service and adapter

Follow `references/topic-transfer.md`. Copy the protocol package, router, CLI, frontend helper, and
contract test byte-for-byte. The copied router deliberately accepts a raw `application/zip` body so
the app needs no multipart dependency and streams it into a bounded temporary file before parsing.
Never call `request.body()` for an import and never extract directly into a live topic path.

Generate only `app/services/topic_transfer_adapter.py`, exposing `get_adapter()` for the copied CLI
and router. Its adapter implements exactly:

```python
class TransferAdapter(Protocol):
    def resolve_topic_name(self, topic_slug: str) -> str: ...
    def validate_staged_topic(self, staging_root: Path, topic_slug: str) -> None: ...
    def reseed_and_validate(self) -> None: ...
```

Resolve the name through the normal topic catalog. Run the complete content/About validator against
the supplied staged root without mutating live paths. Reseed and validate the live app after an
install or rollback. Do not move ZIP, manifest, compatibility, hashing, file validation, merge, or
backup logic into the adapter.

## API contract — the literal source of truth (`app/schemas.py`)

**If the backend and frontend are built in separate passes (e.g. two subagents working from this
doc and `references/frontend.md` in parallel), they _will_ invent different field names and response
shapes unless both are pinned to one literal contract.** This happened in practice — an independently
built frontend expected nested/renamed shapes almost everywhere, and the app crashed on first load.
Treat the Pydantic models below as **exact and non-negotiable**. The frontend's `src/api/types.ts`
interfaces must mirror every field name and nullability here precisely — do not let either side
"clean up" or reshape a name while implementing. This is the actual, verified-working contract from
a real build (GitHub Actions topic):

```python
class TopicOut(BaseModel):                    # GET /api/topics/{slug}
    id: int; slug: str; name: str; description: str; syllabus_version: str
    assessment_enabled: bool; assessment_question_count: int; assessment_minutes: int
    assessment_scoring: str; pass_pct: int | None; pass_score_scaled: int | None
    max_score_scaled: int | None; penalty_for_wrong_answers: bool
    labs_enabled: bool; strategy_enabled: bool

class TopicSummaryOut(BaseModel):              # GET /api/topics (list, for the picker)
    slug: str; name: str; description: str; syllabus_version: str
    domain_count: int; objective_count: int; overall_ready_pct: int

class ObjectiveOut(BaseModel):
    id: int; code: str; title: str; description: str

class DomainOut(BaseModel):                    # GET /api/t/{topic}/domains (list)
    id: int; code: str; name: str; weight_pct: int
    objectives: list[ObjectiveOut] = []

class ContentInfoOut(BaseModel):               # GET /api/t/{topic}/content-info
    syllabus_version: str; domain_count: int; objective_count: int
    lesson_count: int; question_count: int; lab_count: int

class AboutOut(BaseModel):                     # GET /api/t/{topic}/about
    app_version: str
    app_markdown: str
    intake_markdown: str
    sources_markdown: str
    content_changes_markdown: str

class FaqEntryOut(BaseModel):                  # parsed from faq_markdown, see FAQ section above
    index: int; question: str; selected_text: str | None = None; answer_markdown: str

class LessonListItem(BaseModel):               # GET /lessons (list), GET /lessons/objective/{code} (LIST)
    id: int; slug: str; title: str
    objective_code: str; objective_title: str; domain_code: str; domain_name: str
    body_markdown: str; why_it_matters_markdown: str   # full content, so LessonsPage's search box
                                                        # can match more than just title/objective
    video_status: str                          # "idle" | "running" | "done" | "error" — computed
                                                # server-side per lesson (see "Lesson list video
                                                # status" below), drives LessonsPage's marker icon

class LessonOut(BaseModel):                    # GET /lessons/{slug}
    id: int; slug: str; title: str
    objective_code: str; objective_title: str; domain_code: str; domain_name: str
    body_markdown: str; why_it_matters_markdown: str
    faq: list[FaqEntryOut]                     # parsed, never a raw string

class VideoStatusOut(BaseModel):               # GET/POST .../lessons/{slug}/video/*
    status: str                                # "idle" | "running" | "done" | "error"
    error: str | None = None

class ChoiceOut(BaseModel):
    id: int; position: int; text_markdown: str

class ChoiceReviewOut(ChoiceOut):
    is_correct: bool; explanation_markdown: str

class BadgeOut(BaseModel):                     # GET /progress/badges returns list[BadgeOut] (FLAT)
    code: str; name: str; description: str; icon: str
    earned_at: datetime | None = None          # frontend derives earned/locked from this itself

class QuestionPromptOut(BaseModel):            # inside AttemptOut.questions
    question_id: int; external_id: str; position: int; question_type: str
    stem_markdown: str; choices: list[ChoiceOut]; answered: bool
    is_correct: bool | None = None             # None until answered; lets a resumed attempt's
                                                # nav buttons show correctness for prior answers too

class QuestionReviewOut(BaseModel):            # inside AttemptReviewOut.questions
    question_id: int; external_id: str; position: int; question_type: str
    stem_markdown: str; explanation_markdown: str
    choices: list[ChoiceReviewOut]; selected_choice_ids: list[int]; is_correct: bool

class AttemptOut(BaseModel):                   # POST/GET .../attempts, .../attempts/{id}
    id: int; topic_slug: str; attempt_type: str
    label: str                                 # human-readable title, e.g. "Domain drill: <domain>",
                                                # "Practice: <objective title>", "Quick drill" — computed
                                                # server-side in _attempt_label() (app/api/attempts.py),
                                                # not stored; QuizPage renders it instead of a static "Drill"
    started_at: datetime; finished_at: datetime | None
    score_raw: int | None; score_scaled: int | None; passed: bool | None
    minutes_allowed: int | None                # set only for mock attempts, from assessment_minutes
    questions: list[QuestionPromptOut]

class ResponseResult(BaseModel):               # POST .../attempts/{id}/responses
    question_id: int; is_correct: bool; explanation_markdown: str
    choices: list[ChoiceReviewOut]             # full graded choices, for immediate feedback UI
    xp_awarded: int; badges_earned: list[BadgeOut]   # gamification side effects, surfaced inline

class AttemptFinishOut(BaseModel):             # POST .../attempts/{id}/finish
    id: int; score_raw: int; total_questions: int
    score_scaled: int | None; passed: bool | None
    xp_awarded: int; badges_earned: list[BadgeOut]

class AttemptReviewOut(BaseModel):             # GET .../attempts/{id}/review
    attempt_id: int; attempt_type: str         # NOTE: attempt_id, not id, here
    score_raw: int | None; total_questions: int; score_scaled: int | None; passed: bool | None
    finished_at: datetime | None
    questions: list[QuestionReviewOut]

class LabSelfCheckOut(BaseModel):
    position: int; prompt_markdown: str; kind: str   # kind is safe to expose (not a secret)
    hint_available: bool                       # False for yes/no checks — hinting "y..." gives it away

class LabOut(BaseModel):                       # GET /labs/{slug}
    id: int; slug: str; title: str
    objective_code: str; objective_title: str; domain_code: str
    scenario_markdown: str; setup_sql: str; task_markdown: str; expected_result: str
    faq: list[FaqEntryOut]
    self_check: list[LabSelfCheckOut]          # NOTE: key is `self_check`, not `checks`
    passed: bool                               # joined against LabAttempt for the current user

class LabListItem(BaseModel):                  # GET /labs (list)
    id: int; slug: str; title: str
    objective_code: str; objective_title: str; domain_code: str
    scenario_markdown: str; task_markdown: str         # full content for LabsPage's search box —
    self_check_markdown: list[str]                     # prompts only, in position order; NOT the
                                                        # answers (see LabOut's self_check note —
                                                        # never leak an answer ahead of the check)
    passed: bool

class LabCheckRequest(BaseModel):              # POST /labs/{slug}/check body
    answers: list[str]                         # positional, matching self_check order — no check ids needed

class LabCheckResultItem(BaseModel):
    position: int; prompt_markdown: str; passed: bool   # keyed by position, not an internal check id

class LabCheckResult(BaseModel):               # POST /labs/{slug}/check response
    passed: bool; results: list[LabCheckResultItem]; badges_earned: list[BadgeOut]

class LabCheckHintOut(BaseModel):              # GET /labs/{slug}/self-check/{position}/hint
    position: int; hint: str

class LabCheckAnswerOut(BaseModel):            # GET /labs/{slug}/self-check/{position}/answer
    position: int; answer: str

class ReviewQueueItem(BaseModel):
    objective_code: str; objective_title: str; status: str   # "weak" | "due" | "new" — see note above

class DomainReadiness(BaseModel):
    code: str; name: str; weight_pct: int; ready_pct: int

class AttemptSummary(BaseModel):               # inside DashboardOut.attempt_history
    id: int; attempt_type: str; started_at: datetime; finished_at: datetime | None
    score_raw: int | None; score_scaled: int | None; passed: bool | None
    total_questions: int                       # count of AttemptQuestion rows, computed not stored

class StudyPlanItem(BaseModel):
    objective_code: str; objective_title: str; estimated_week: int

class DashboardOut(BaseModel):                 # GET /progress/dashboard — all lists are FLAT, see note above
    domain_readiness: list[DomainReadiness]
    domain_ready_pct: int; labs_pct: int; strategy_pct: int; overall_ready_pct: int
    exam_ready: bool; xp: int; current_streak: int; longest_streak: int; streak_freeze_count: int
    review_queue: list[ReviewQueueItem]
    attempt_history: list[AttemptSummary]
    study_plan: list[StudyPlanItem]

class StrategyLessonListItem(BaseModel):
    id: int; slug: str; title: str; topic: str; read: bool

class StrategyLessonOut(BaseModel):
    id: int; slug: str; title: str; topic: str
    body_markdown: str; why_it_matters_markdown: str
    faq: list[FaqEntryOut]; read: bool

class StrategyQuestionOut(BaseModel):
    id: int; external_id: str; topic: str; question_type: str
    stem_markdown: str; choices: list[ChoiceOut]

class StrategyCheckResult(BaseModel):
    question_id: int; is_correct: bool; explanation_markdown: str; choices: list[ChoiceReviewOut]
```

When building the frontend (`references/frontend.md`), copy these field names into
`src/api/types.ts` verbatim — do not re-derive shapes from the prose Pages/Components description
alone. When building the backend, implement `app/schemas.py` to match this exactly (it's fine to
add fields nothing here mentions, e.g. internal-only ones, but never rename or drop one of these).

**Before Phase 6:** run a live integration smoke test regardless of how backend/frontend were built —
start the backend, `curl` every endpoint above with real seeded data, and diff the JSON against
`frontend/src/api/types.ts` field-for-field. Fix any mismatch (prefer changing the frontend to match
this contract, since it's the source of truth) and rebuild before moving on. Don't skip this even if
both sides seemed to build cleanly in isolation — a clean `npm run build` only proves the frontend's
types are internally consistent, not that they match what the backend actually returns.

## `app/constants.py`

Encode exam/assessment facts and tuning as constants (no magic numbers in logic). Defaults for a
generic (non-cert) topic; override from `syllabus.yaml`'s `assessment:` block at seed time:

```python
DEFAULT_PRACTICE_QUESTION_COUNT = 10
QUICK_DRILL_QUESTION_COUNT = 10
DEFAULT_DOMAIN_DRILL_QUESTION_COUNT = 10

# SM-2 spaced repetition. Quality derived from correctness only.
SM2_QUALITY_CORRECT = 5
SM2_QUALITY_INCORRECT = 2
SM2_MIN_EASE_FACTOR = 1.3
SM2_MAX_INTERVAL_DAYS = 365          # cap: without it, due_on overflows date's year-9999 ceiling

MASTERY_MIN_REPETITIONS = 2
MASTERY_MIN_EASE_FACTOR = 2.3

# Blended readiness = domain mastery + labs done + strategy read. Shares sum to 100.
DOMAIN_READINESS_WEIGHT_PCT = 70
LABS_READINESS_WEIGHT_PCT = 20
STRATEGY_READINESS_WEIGHT_PCT = 10
READY_THRESHOLD_PCT = 80             # blended %, plus a passed mock, => "GO"

ATTEMPT_HISTORY_LIMIT = 20
STUDY_OBJECTIVES_PER_WEEK = 3        # pacing hint on the dashboard

# Gamification (flavor only; no bearing on mastery/readiness).
XP_PER_CORRECT_ANSWER = 10
XP_MOCK_PASS_BONUS = 200
STREAK_BADGE_THRESHOLDS = [3, 7]
XP_STREAK_FREEZE_COST = 150
STREAK_FREEZE_MAX_HELD = 2

# Strategy module (cert topics only).
STRATEGY_TOPICS = ["time-management", "process-of-elimination", "multi-select-strategy",
                   "exam-gotchas", "no-penalty-scoring"]
MIN_STRATEGY_QUESTIONS_PER_TOPIC = 2

# Select-to-ask FAQ (backend choice, model and API key are user config and live in
# Settings, not here — see below).
LESSON_QA_TIMEOUT_SECONDS = 180
# claude_cli backend only: a spend guard on the subprocess, not a user preference.
LESSON_QA_MAX_BUDGET_USD = 2.00

# Gemini Notebook video generation can take several minutes for whiteboard-style videos.
LESSON_VIDEO_WAIT_TIMEOUT_SECONDS = 1800

# A persisted .video_tasks.json entry older than this is treated as abandoned rather than still
# in progress — see references/notebooklm-automation.md's "Resumable generation" section.
LESSON_VIDEO_TASK_STALE_HOURS = 12
```

If assessment scoring is `percent`, `passed = score_raw/total >= pass_pct/100`. If `scaled`, map
raw→scaled linearly and compare to `pass_score_scaled` (template default 750/1000).

## Algorithm: SM-2 mastery (`app/services/mastery.py`)

Update one objective's mastery after each graded answer. `quality = 5` if correct else `2`.

**`today` here must be `datetime.now().date()` (server-local date), never `datetime.now(UTC).date()`.**
This app runs locally on the user's own machine, so the server's local date is the user's calendar
day. Computing `today` from UTC instead is a real bug (confirmed in a real build, not hypothetical):
it silently miscounts streaks/due-dates for anyone outside UTC — e.g. a user in UTC-3 answering a
question after ~9pm local time gets a UTC date one day ahead of their actual "today," so two
same-evening answers land on different `date()` values and register as two separate days. Only the
`Date`-typed day-boundary fields (`due_on`, `last_activity_date`, and the `today` used to derive
them) need local date; instant `DateTime` timestamps (`last_reviewed_at` below, `responded_at`,
`earned_at`) correctly stay `datetime.now(UTC)`. See `references/data-model.md` for the general rule.

```python
def _apply_sm2(mastery, quality, today):
    ef = float(mastery.ease_factor)
    if quality < 3:
        mastery.repetitions = 0
        mastery.interval_days = 1
    else:
        if mastery.repetitions == 0:   mastery.interval_days = 1
        elif mastery.repetitions == 1: mastery.interval_days = 6
        else: mastery.interval_days = min(round(mastery.interval_days * ef), SM2_MAX_INTERVAL_DAYS)
        mastery.repetitions += 1
    ef += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    mastery.ease_factor = max(SM2_MIN_EASE_FACTOR, ef)
    mastery.due_on = today + timedelta(days=mastery.interval_days)
    mastery.last_reviewed_at = datetime.now(UTC)

def is_mastered(m, min_reps, min_ef):
    return m is not None and m.repetitions >= min_reps and float(m.ease_factor) >= min_ef
```

## Algorithm: grading (`app/services/grading.py`)

Multi-select is all-or-nothing per exam convention: a response is correct iff the selected choice-id
set **equals** the correct choice-id set. Serialize choices with per-choice `is_correct` +
explanation for the review screen. Shuffle choice order deterministically per (attempt, question)
so the same attempt is stable but order isn't guessable across attempts.

## Algorithm: attempt creation & scoring (`app/services/attempts.py`)

- **mock**: pull the fixed `mocks/<code>.yaml` question set for the topic, shuffle presentation order.
  Reject domain/objective/count args.
- **quick_drill**: `QUICK_DRILL_QUESTION_COUNT` random mock-eligible questions across the topic.
- **domain_drill**: random questions within one domain.
- **practice**: random questions within one objective (or topic-wide) — `DEFAULT_PRACTICE_QUESTION_COUNT`.
- On **finish**: `score_raw` = count correct; `score_scaled`/`passed` per the topic's scoring mode;
  award XP + badges; the per-answer path updates SM-2 mastery and streaks.
- `AttemptOut.label` (`_attempt_label()` in `app/api/attempts.py`) gives each attempt a human title —
  "Quick drill" / "Mock exam" outright; "Domain drill: `<domain.name>`" / "Practice: `<objective.title>`"
  derived from `attempt.questions[0].question.objective` (and its `.domain`). Not persisted on
  `Attempt` — domain/objective aren't stored on the row, only implied by which questions got attached
  at creation, so the label is recomputed from the first question every time the attempt is fetched.
  This means `_get_attempt_or_404`'s eager-load must also pull
  `Question.objective` → `Objective.domain`, not just `Question.choices`.

## Algorithm: lab self-check hints (`app/services/labs.py`)

Two learner-facing "give up gradually" affordances sit next to `check_lab`/`_check_passes`:
`build_check_hint` and `build_check_answer`, both taking a single `LabCheck` and reading its stored
`expected_value` — never the learner's submitted answer (grading and hinting are independent code
paths; a hint must be computable before the learner has answered anything).

- **`build_check_answer`** — for `contains`/`exact` checks, returns `expected_value` verbatim. For the
  three relative kinds (`number_positive`, `number_less_than_previous`, `number_greater_than_previous`)
  there is no stored `expected_value` at all (the check is a _relationship_, not a fixed number — see
  `references/content-schema.md`), so both the hint and the answer fall back to a plain-English
  description of the rule, e.g. `"Must be a positive number."` / `"Must be less than your previous
answer."` Raise `LabCheckError` (→ 400) if `expected_value` is blank for a kind that's supposed to
  have one — fail loudly rather than returning an empty string.
- **`check_hint_available`** — `False` when `expected_value.strip().lower()` is `"yes"` or `"no"`,
  `True` otherwise (including the three relative kinds, whose hint is already just the rule, not a
  leak). This is a `LabOut.self_check[].hint_available` field the frontend disables the "Hint" button
  on directly — **don't rely on the frontend refusing to call the endpoint as the only guard**;
  `build_check_hint` also raises `LabCheckError` if called against a yes/no check, so a manually-crafted
  request can't bypass the UI disable. The reason yes/no needs special-casing at all: the generic
  word-initial hint below (`"yes"` → `"y..."`) trivially reveals a 2-option answer, unlike a real
  multi-word phrase where the first letters are a genuine partial hint.
- **`build_check_hint` for `contains`/`exact`** — branches on whether `expected_value` parses as
  `float`:
  - **Word/phrase answers** (`"plain chat assistant"`, `"Cloud"`, `"--json"`) → `random.random() < 0.5`
    picks one of two equally-likely formats, decided independently on every fetch:
    - first letter of each whitespace-split word, lowercased, each followed by `"..."`, joined with a
      space: `"plain chat assistant"` → `"p... c... a..."`. Single-token answers just get one group
      (`"Cloud"` → `"c..."`).
    - a same-length dot mask per word instead of the first letter — one `"."` per character, joined
      with a space: `"plain chat assistant"` → `"..... .... ........."`. This still tells the learner
      the word count and lengths without leaking any letters, for the fetches where the first-letter
      form would give away too much.
  - **Numeric answers** (`"2000"`, `"0.035"`, `"24"` — plenty of `exact`-kind checks store a number as
    a string, not just the three relative kinds) → a randomized `"more than <lower>"` /
    `"less than <upper>"` bound **close to the real value, same order of magnitude, not a full decade
    away**. Get this wrong and the hint is either useless (jumps a full `×10`, e.g. `"less than
10000"` for an answer of `2000`) or a giveaway (bound sits right on top of the answer). The
    working formula: `magnitude = 10 ** floor(log10(abs(value)))` (or `1` if `value == 0`);
    `increment = magnitude / 10` if `magnitude >= 10` else `magnitude` itself (so single/double-digit
    answers get integer-sized steps, not fractional ones); `delta = increment * random.randint(1, 9)`;
    bound = `value ∓ delta`. Clamp the lower bound to `0` when `value > 0` (most answers here are
    non-negative counts/ports/timeouts) — but **only** clamp, never floor-then-compare, or a
    small-`value` check can produce a false "more than 0" for an answer that's actually `0`. Then
    `random.random() < 0.5` picks which side to report. - **Use unseeded `random`, not `random.Random(check.id)`.** A per-check seed was tried first for
    "stable hint across repeated fetches of the same question" — but it back fires: every fetch of
    that check's hint returns the _exact same_ bound forever, which reads as broken/deterministic
    to a learner clicking "Hint" more than once (confirmed — real complaint: "for '1' I'm getting
    always 'less than 10'"). Genuine per-request randomness is the actual desired behavior; nothing
    here needs cross-request stability.
  - Checks with no `expected_value` at all (the three relative kinds) never reach this branch — they're
    handled by the shared description fallback above.

## Algorithm: readiness dashboard (`app/services/progress.py`)

- Both `build_dashboard` and `build_review_queue` compute their own `today = datetime.now().date()`
  (local, not UTC — same rule as SM-2/streaks above) to classify review-queue items as weak/due/new.
- Per domain: `ready_pct = round(100 * mastered_objectives / total_objectives)`.
- `domain_ready_pct = round(Σ(ready_pct * weight_pct) / Σ weight_pct)`.
- `labs_pct` = % labs passed; `strategy_pct` = % strategy lessons read (0 if module off).
- `overall_ready_pct = round((domain_ready_pct*70 + labs_pct*20 + strategy_pct*10) / 100)` using the
  weight constants. If a module is disabled, set its component to 0 **and** redistribute its weight to
  domain mastery (so a reading-only topic's readiness = domain mastery). Keep the weights summing to 100.
- `exam_ready` (GO) = `overall_ready_pct >= READY_THRESHOLD_PCT` **and** last mock attempt passed
  (for non-mock topics, GO = `overall_ready_pct >= threshold`).
- Also return: review queue (weak / due / new per objective, sorted weak→due→new), attempt history
  (last `ATTEMPT_HISTORY_LIMIT`), XP/streak state, and a per-objective `estimated_week`
  (`objective_index // STUDY_OBJECTIVES_PER_WEEK + 1`) for a suggested study plan.
- **All three of these are flat lists, not pre-grouped/nested structures**: `domain_readiness` is
  `list[DomainReadiness]` with no nested objectives; `review_queue` is a flat `list[ReviewQueueItem]`
  (each item carries its own `status: "weak"|"due"|"new"` — note `"due"` means _mastered but due for
  spaced-repetition review_, not "not yet mastered"; only `"weak"`/`"new"` mean not mastered);
  `study_plan` is a flat `list[StudyPlanItem]`, one entry per objective in the whole syllabus, each
  carrying its own `estimated_week`. **Do not invent a nested/grouped dashboard shape** (e.g. domains
  with embedded per-objective mastery lists, or a study plan pre-grouped by week) — the frontend
  derives any such view client-side from these flat lists (see `references/frontend.md`). This flat
  shape is deliberate and already matches what `_review_queue()`/the study-plan builder naturally
  produce; a richer nested shape was tried once by a frontend built independently from prose and it
  didn't match reality, which crashed the dashboard page outright.

## Gamification (`app/services/gamification.py`)

Per answered question: update streak (same day = no change; yesterday = +1; a gap covered by held
streak-freezes = consume freezes and +1; else reset to 1), add XP if correct, award any newly earned
badges (first attempt, perfect quick drill, streak thresholds, mock pass, domain-master when all of a
domain's objectives are mastered, "exam ready" at GO). Streak-freeze is bought with XP. The `today`
passed into this update — same as SM-2 above — must be `datetime.now().date()`, not UTC.

## Select-to-ask FAQ (`app/services/lesson_qa/` + `teaching.py`)

A distinctive feature: the learner selects text in a lesson and asks a question; the backend calls an
LLM, streams the answer back (SSE/streaming response), and appends the Q&A to the lesson's
`faq_markdown` (persisted back into the source `.md` file so it survives re-seeding).

**Three pluggable LLM backends, chosen by config — never auto-detected.** `lesson_qa` is a package,
not a module: prompting and parsing are backend-agnostic and live in `lesson_qa/__init__.py`, while
each transport is one small module in `lesson_qa/backends/` exposing exactly three names — `name:
str`, `check_available() -> None` (raises `LessonQAError` naming both the missing piece _and_ the
config change that fixes it), and `stream(prompt) -> Iterator[str]`. `stream()` yields text deltas
when the transport exposes them and **`return`s the authoritative full answer** (read by the core
via `StopIteration.value`). A final-message-only transport such as `codex_cli` returns without
yielding deltas.
`lesson_qa/backends/__init__.py` maps `Settings.llm_backend` to a module, importing it lazily.

| `LEARNUP_LLM_BACKEND` | Transport                                    | Needs                                                            |
| --------------------- | -------------------------------------------- | ---------------------------------------------------------------- |
| `claude_cli`          | `claude -p` subprocess                       | the authenticated `claude` CLI on PATH — no app-specific API key |
| `codex_cli`           | ephemeral, read-only `codex exec` subprocess | an authenticated `codex` CLI on PATH                             |
| `openhands`           | `openhands.sdk.LLM` in-process (LiteLLM)     | optional dep group + `.env` config                               |

**Default to the backend selected during intake.** When the user is already running Claude Code or
Codex, prefer that matching CLI backend so the FAQ works without another signup, app-specific API
key, or `.env` file. Generate the selected enum value as `Settings.llm_backend`'s default and record
it in the generated README and AGENTS.md. Do not universalize one author's environment by always
defaulting to Claude. Requiring a paid API key before the headline feature works is an adoption
barrier, so recommend OpenHands only when the user wants a hosted or local LiteLLM-compatible model.

**No auto-detection and no fallback between backends.** Do not "try a CLI, fall back to the API"
or pick a backend by sniffing what's installed. If the configured backend can't run, raise — a
silent fallback means a learner gets a billed API answer when they expected their subscription, with
nothing in the UI explaining why. The corollary is that a correctly configured backend is _known_,
so nothing needs to report at runtime which one answered.

**Config (`Settings`, all `LEARNUP_`-prefixed, every one with a working default):**

- `llm_backend: LLMBackend` — a `StrEnum` (`claude_cli` | `codex_cli` | `openhands`), so a typo
  fails loudly at startup via pydantic rather than silently selecting something. Its generated
  default is the `faq_llm_backend` recorded in `INTAKE.md`.
- `claude_cli_model` — a `claude --model` **alias** (`sonnet`/`opus`/`haiku`), default `sonnet`.
  Keep this separate from `llm_model`: a LiteLLM id like `anthropic/claude-sonnet-4-5` is _not_ a
  valid `--model` argument, and sharing one field across different backends silently breaks one of
  them. `codex_cli` deliberately uses the user's Codex configuration and default model, matching a
  plain `codex exec` invocation; it has no app-specific model setting.
- `llm_model` / `llm_api_key` / `llm_base_url` — the `openhands` backend's LiteLLM id (default
  `anthropic/claude-sonnet-4-5`), provider key, and optional custom API base.

**Ship a checked-in `.env.example` documenting all of it** (`.env` itself is git-ignored; the
`.env` pattern in `.gitignore` doesn't match `.env.example`, so no exception is needed). It is the
discoverable config surface — a user should never have to read source to find a setting.
**Storage is a single `faq_markdown` blob, but every API response that includes FAQ content
(`LessonOut.faq`, `LabOut.faq`, `StrategyLessonOut.faq`) must expose it as a parsed
`list[FaqEntryOut]` (`{index, question, selected_text, answer_markdown}`)** — parse the blob into
entries at read time (e.g. split on a stable heading marker you control when appending). Returning
the raw markdown string instead of the parsed list is a real bug that was hit in practice: the
frontend's FAQ component calls `.map()` on it and crashes with no server-side error to hint at the
cause. Keep the template's approach for generating the answer:

- **Two-tier context, cheap by default.** Every ask defaults to context = just the current
  lesson/lab's own body (cheap, fast — the common case, since most questions are answerable from
  the document the learner is already reading). Only when the learner explicitly opts in does the
  context expand to the whole topic's `sources/<topic_slug>/` corpus (can be hundreds of KB —
  expensive and slower). Never default straight to the full-topic corpus on every question; that
  was tried and reliably blew past a lesson-sized cost/latency budget on any topic with a
  nontrivial `sources/` folder — see the two bullets below for the mechanics.
- **`INSUFFICIENT_CONTEXT` sentinel escalation.** `lesson_qa.build_prompt(..., allow_insufficient=)`
  — when `True` (the narrow, single-document pass), the prompt instructs the model to respond with
  exactly the literal line `INSUFFICIENT_CONTEXT` (see `lesson_qa.INSUFFICIENT_CONTEXT_SENTINEL`)
  instead of guessing, if the provided document doesn't contain enough to answer confidently.
  `lesson_qa.ask()` detects an exact match on that sentinel and yields `{"type": "insufficient"}`
  instead of a `result` event — no FAQ entry is persisted for that pass. `teaching.ask_about_lesson`
  / `ask_about_lab` (and `strategy.py`'s inline copy) take a `use_full_sources: bool = False` param:
  `False` builds the narrow context and passes `allow_insufficient=True`; `True` appends
  `topic_sources_markdown(topic_slug)` and passes `allow_insufficient=False` (already at maximum
  context, no further escalation to offer). That helper recursively reads the topic's source tree:
  exclude `INTAKE.md`/`SOURCES.md`; extract PDF text with `pypdf.PdfReader`; decode every other
  textual source as strict UTF-8; and skip known image/audio/video suffixes while appending an
  explicit "Non-text assets omitted" list to the context. Raise `LessonQAError` with the exact file
  name for a malformed PDF, a PDF with no extractable text, or an unknown binary/non-UTF-8 file.
  Do not call `Path.read_text()` blindly on every source—topics are expected to contain PDFs and
  image assets, and doing so crashes the full-source SSE stream with `UnicodeDecodeError` before
  the LLM is called. Keep source loading inside the API stream's `try` block (including the strategy
  route's inline handler) so ingestion failures become JSON SSE error events rather than uncaught
  ASGI exceptions.
- **Frontend confirmation gate.** `QuestionAskRequest` carries `use_full_sources: bool = False` from
  the client. On the wire, an `insufficient` event is a third SSE `type` alongside `delta`/`result`
  (`AskOutcome` in `frontend/src/api/types.ts`: `{type: "answered", entry}` or
  `{type: "insufficient"}`). `SelectionAsk.tsx` calls `onAsk(..., useFullSources=false)` first;
  on `{type: "insufficient"}` it shows a plain-language prompt ("this lesson alone doesn't have
  enough information — search the whole topic's source material instead? that's slower and costs
  more") with an explicit opt-in button before ever calling `onAsk(..., useFullSources=true)`. If
  the full-source pass _also_ comes back insufficient, that's terminal — show a "no answer found"
  message, don't loop or re-offer the confirmation (there's nothing bigger left to search).
- Prompt the model, in prose (not an angle-bracket placeholder template), to write a first line
  starting with `Title: ` followed by a clean restatement of the question, then a blank line, then
  the answer as plain prose beneath it — and to explicitly say not to wrap the answer in tags,
  brackets, or other placeholder markup. **Do not phrase the instruction as literal template text
  like `Title: <clean question>\n\n<answer>`** — a real build did this and the model would
  sometimes echo the `<answer>` placeholder itself as a literal wrapping tag around its response
  (Claude commonly uses that convention for structured output), which then rendered verbatim as
  `<answer>`/`</answer>` text in the frontend, since the markdown renderer shows unrecognized raw
  HTML-like tags as literal text rather than parsing them. As a defense-in-depth backstop, also
  strip a leading `<answer>`/trailing `</answer>` from the parsed answer in `lesson_qa.ask()` before
  yielding the `result` event, in case the model wraps it anyway despite the clearer prompt. Use the
  title as the FAQ heading.

### `claude_cli` backend (`lesson_qa/backends/claude_cli.py`)

- `check_available()` is `shutil.which("claude") is not None`; its error message must point at
  `LEARNUP_LLM_BACKEND=codex_cli` and `LEARNUP_LLM_BACKEND=openhands` as alternatives, not just
  report the CLI is missing.
- Invoke `claude -p --output-format stream-json --include-partial-messages --verbose --tools ""
--no-session-persistence --model <claude_cli_model> --max-budget-usd <LESSON_QA_MAX_BUDGET_USD>`.
  `--tools ""` matters: this is a pure text completion, and leaving the agent's tools enabled lets
  it wander off reading files instead of answering.
- **Pipe the prompt via stdin, never as an argv positional.** The full-source pass can run into the
  hundreds of KB, well past Linux's ~128KB `MAX_ARG_STRLEN`, which fails with "Argument list too
  long". `claude -p` reads the prompt from stdin when given no positional prompt.
- **Write stdin on a separate thread**, concurrently with the stdout read loop. Writing it all
  synchronously first deadlocks once the pipe buffer fills, since the child won't drain stdin and
  produce stdout at the same time.
- Parse newline-delimited JSON off stdout: `type == "stream_event"` →
  `event.event.delta.text` is a delta to yield; `type == "result"` → `event.result` is the
  authoritative final text to return. Ignore lines that fail `json.loads` rather than crashing.
- **A nonzero exit _after_ a well-formed `result` line is not an error.** Observed live: some
  post-response step in the CLI can fail after the complete answer was already emitted. Treat a
  parsed result as authoritative and only raise on nonzero exit when no result was captured —
  otherwise a perfectly good answer gets thrown away.
- `LESSON_QA_MAX_BUDGET_USD` (~2.00) lives in `app/constants.py`, not `Settings`: it's a spend
  guard on a subprocess, not a user preference. The `codex_cli` and `openhands` backends have no
  equivalent — their own limits apply.

### `codex_cli` backend (`lesson_qa/backends/codex_cli.py`)

- `check_available()` is `shutil.which("codex") is not None`; its error names both
  `LEARNUP_LLM_BACKEND=claude_cli` and `LEARNUP_LLM_BACKEND=openhands` as alternatives.
- Invoke `codex exec --json --ephemeral --sandbox read-only --skip-git-repo-check -`. The explicit
  `-` makes stdin the complete prompt, which avoids the argv-size ceiling on a full-source pass.
  Use `subprocess.run(..., input=prompt, capture_output=True, text=True,
timeout=LESSON_QA_TIMEOUT_SECONDS)` so stdin, stdout, and stderr are drained without pipe
  deadlocks.
- Run it with `cwd` set to a fresh `tempfile.TemporaryDirectory`. This isolates the FAQ completion
  from the study app's repo instructions and files; read-only sandboxing adds a second guard.
  `--ephemeral` prevents a Q&A request from leaving a resumable Codex session behind.
- Parse JSONL from stdout. The authoritative answer is the last `item.completed` event whose
  `item.type == "agent_message"`; surface `error`/`turn.failed`, stderr, a nonzero exit with no
  answer, timeout, and an empty result as `LessonQAError`. Ignore malformed/non-JSON lines.
- Codex non-interactive JSON mode exposes completed items, not token-level message deltas. Return
  the final agent message without yielding deltas; the shared core still emits the same final SSE
  result and persists the FAQ entry. Document that this backend's answer appears when Codex
  completes.
- Reuse the user's existing Codex authentication and configured default model. Do not add API-key
  settings or silently choose a model in the app.

### `openhands` backend (`lesson_qa/backends/openhands.py`)

- **Make it an optional dependency group**, not a base dependency: `[dependency-groups] openhands =
["openhands-sdk>=1.36.1", "openhands-tools>=1.36.1"]` (matched-version set; requires Python
  3.12+), installed with `uv sync --group openhands`. A default `uv sync` should install nothing for
  the LLM feature at all. `check_available()` checks `importlib.util.find_spec("openhands.sdk")`
  first and names that command in the error.
- `check_available()` also requires `llm_api_key`. Keep it required even for local models that
  ignore keys — the convention is to set a placeholder (`LEARNUP_LLM_API_KEY=local-llm`), which
  keeps one uniform rule instead of a conditional "unless a base URL is set" carve-out. Say so in
  the error message and in `.env.example`, or the local-model path looks broken.
- Build `openhands.sdk.LLM(usage_id=..., model=<Settings.llm_model>, api_key=<Settings.llm_api_key>,
base_url=<Settings.llm_base_url>, timeout=LESSON_QA_TIMEOUT_SECONDS)` and call
  `llm.completion(messages, on_token=<callback>, stream=True)` **in-process** — no subprocess and no
  argv ceiling (the prompt travels as a `Message`/`TextContent` payload).
  `LLM.completion()` is a **blocking call** that only invokes `on_token` per streaming chunk — it
  does not return a generator — so run it on a **background thread** and relay chunks through a
  `queue.Queue`: `on_token` pushes each chunk's `choices[0].delta.content`, the generator reads off
  the queue and yields each, and a sentinel value signals the worker is done. Enforce
  `LESSON_QA_TIMEOUT_SECONDS` as an overall wall-clock deadline on the queue reads (independent of
  `LLM.timeout`, which only bounds the underlying HTTP request) and raise `LessonQAError` on timeout
  / a provider error (`openhands.sdk.llm.exceptions.LLMError` and subclasses) / an empty result.
- **`import openhands.sdk` has global side effects — neutralize them before the first import, at the
  top of this module.** Importing the package (a) prints a startup banner to stderr on every
  process launch/reload, and (b) auto-configures the **root** logger with a Rich handler at `INFO`
  level (`openhands.sdk.logger.logger`'s `setup_logging()`, run at import time unless disabled). (b)
  is the more dangerous one: any logger without its own explicit level — e.g. `sqlalchemy.engine` —
  inherits that root `INFO` level and starts emitting noisy per-statement echo/cache-stats lines
  (`"dialect duckdb+duckdb_engine does not support caching ...s"`), rendered with Rich's
  `[HH:MM:SS] LEVEL ... file.py:NNN` formatting, on **every DB query in the whole process** — not
  just wherever `lesson_qa` is used. Confirmed live in a real build: it showed up on plain backend
  requests, because `lesson_qa` gets imported into the `teaching.py` / `strategy.py` chain during
  app startup. Set both env vars via `os.environ.setdefault(...)` **before** the `from openhands.sdk
import ...` line: `OPENHANDS_SUPPRESS_BANNER=1` and `LOG_AUTO_CONFIG=false`. `setdefault` (not a
  hard set) so a user who genuinely wants OpenHands' logging can opt back in via their own env.
  **The registry's lazy import is what makes this containable**: keep the SDK imports inside this
  module (module-level env setdefault + the `from openhands.sdk import ...` inside `stream()`), so a
  CLI-only install never triggers any of it — and never import the SDK from the package
  `__init__.py` or a test helper at collection time.
- **Size `LESSON_QA_TIMEOUT_SECONDS` for the full-source pass, not the narrow one.** The narrow pass
  is cheap regardless of topic size (single lesson/lab body). The full-source pass on a large topic
  (~800KB+, e.g. a big software-product topic) pushes input cost and processing latency well past a
  lesson-sized budget. `LESSON_QA_TIMEOUT_SECONDS = 180` is a reasonable default with headroom for a
  large topic; a build with an unusually large `sources/` corpus may need to raise it further.

### Documenting and testing the backends

- **README must present all three backends as first-class**, with a comparison table (backend / what
  it needs / when to pick it) and copy-pasteable `.env` blocks for both CLI backends, a hosted
  provider, and a **fully local model with no subscription and no paid API**
  (e.g. Ollama — `LEARNUP_LLM_MODEL=ollama_chat/llama3`, `LEARNUP_LLM_BASE_URL=http://localhost:11434`,
  placeholder key). The local path is worth calling out explicitly: because the FAQ answers strictly
  from material supplied in the prompt rather than from the model's own knowledge, a small local
  model is generally good enough, which makes the whole app usable with no LLM spend whatsoever.
- **Test the shared core once, parametrized over every backend, with only the transport faked** —
  fake `subprocess.Popen` (yielding real `stream-json` lines) for `claude_cli`, `subprocess.run`
  (returning real Codex JSONL item events) for `codex_cli`, and `openhands.sdk.LLM` for `openhands`,
  then assert identical `result`/`insufficient` outcomes from `ask(..., backend=...)`; assert delta
  pass-through for the two streaming transports and no deltas for Codex. This pins the invariant
  that the three backends are interchangeable at the app contract even though Codex exposes only a
  final message. Give `ask()` an optional
  `backend` parameter for exactly this (it also keeps tests independent of ambient `.env`), and
  guard SDK-dependent tests with `pytest.importorskip("openhands.sdk")` so the suite still passes on
  a default, CLI-only install. Cover the config errors too: each backend's unavailability message
  must name the escape hatch, and a broken backend must never invoke another one.

**`selected_text` is part of the FAQ entry, not just the prompt.** The learner's highlighted passage
(`QuestionAskRequest.selected_text`) is used to build the LLM prompt, but it must **also** be
persisted alongside the question/answer, or the frontend has no way to link the answer back to where
it came from — the "select-to-ask" feature is otherwise a dead end once the panel closes. Storage
format in `faq_markdown` (`app/content/faq.py`): an optional HTML comment right after the `###`
heading, `<!-- selected: <text, whitespace-collapsed to one line> -->`, before the blank line and
answer body:

```
### <title>
<!-- selected: <the exact highlighted text> -->

<answer>
```

The comment is optional in the parsing regex (`_ENTRY_RE`) — entries created before this field
existed simply omit it and parse with `selected_text = None`. `append_faq_entry`/`render_faq_entries`
take/emit a 3-tuple (`title, selected_text, body`) instead of 2; every call site
(`teaching.ask_about_lesson`, `ask_about_lab`, `strategy.py`'s inline handler) must pass the
`selected_text` it already has through to `append_faq_entry`, and the `result` SSE event must include
it too (see the wire contract below) so a freshly-answered entry can be highlighted immediately
without a refetch. `sync_lab_yaml_faq` mirrors it into the lab YAML's `faq:` list as a `selected_text`
key alongside `question`/`answer`.

**Frontend: link the highlighted passage in the body to its answer, don't just store it.** Storing
`selected_text` is only half the feature — `frontend/src/lib/remarkFaqHighlights.ts` is a remark
plugin (same hand-rolled-`MdastNode` style as `remarkVideoPlaceholder.ts`, no extra deps) that, given
`{index, text}` pairs, finds the first exact-substring match of `text` **within a single markdown
text node** and replaces it with a `link` mdast node (`url: "#faq-<index>"`,
`data.hProperties.className: ["faq-source-link"]`) so it renders through the same `<a>` component as
any other lesson link. `Markdown.tsx` takes an optional `faqHighlights: FaqHighlightEntry[]` prop and
adds `[remarkFaqHighlights, faqHighlights ?? []]` to `remarkPlugins`. `TeachingArticle.tsx` computes
`faqHighlights` from its `faq` prop (filtering out entries with `selected_text: null`) and passes it
to **both** `Markdown` calls (body and "Why It Matters" — a selection can originate from either).
`LabDetailPage.tsx` does the same for `lab.faq`, passed to its Scenario and Task `Markdown` calls (labs
don't use `TeachingArticle`, they lay out `SelectionAsk`/`FaqSection` inline).

- **Do this as an AST transform, not DOM surgery.** The natural-seeming alternative — a `useEffect`
  that walks the rendered `bodyRef` DOM with `TreeWalker`/`Range` and wraps matched text nodes in an
  injected `<a>` — was considered and rejected before writing any code: React owns that subtree, and
  mutating its DOM out-of-band (splitting text nodes, inserting foreign elements) risks React's next
  reconciliation pass calling `insertBefore`/`removeChild` against node references that are no longer
  where React last left them, throwing `NotFoundError` or silently corrupting the tree. A remark
  plugin runs before React ever sees the tree, so the highlight is just normal vdom output — no
  imperative DOM ownership conflict possible.
- **Matching is single-text-node, but a boundary-crossing selection still gets a partial link.**
  Each text run is checked for the full quote first; if a selection spans a formatting boundary
  (crosses into/out of `**bold**`/`` `code` ``/an inline tag) so no run contains the whole phrase,
  fall back to linking the longest leading prefix of the quote that the run containing its start
  ends with — down to a single word or even a single character if that's all that's left before the
  boundary — rather than silently dropping the link. `remarkFaqHighlights.ts`'s `longestPrefixAtEnd`
  helper does this: it only matches a prefix anchored at the _end_ of the run's text (not a free
  substring search), so a short fallback match still corresponds to the real start of the selection
  rather than a coincidental short string elsewhere in the document. Most real selections are plain
  prose within one run and match in full; the prefix fallback only kicks in for the boundary-crossing
  minority.
- `#faq-<index>` needs no extra frontend wiring to "arrive" — `FaqSection.tsx` already renders each
  entry with `id={`faq-${entry.index}`}`, and `index.css` already has `.faq-entry:target` (amber
  border + glow) from before this feature existed. The highlight-link is the missing other half of an
  already-half-built affordance, not a new one.
- CSS: `.faq-source-link` — dotted amber underline, solid + amber-ink on hover, `color: inherit` (it
  must not look like a generic blue link; it's a citation-style backlink, not real navigation away
  from the page).

**A markdown-body seed-time bug this format sits next to, worth knowing about:**
`faq.sync_markdown_faq_section`/`sync_lab_yaml_faq` write `faq_markdown` back into the lesson's `.md`
file (a trailing `## FAQ` heading block) purely as a human-readable mirror — it is **never** meant to
be re-ingested into `body_markdown`/`why_it_matters_markdown` on the next seed. `seed.py`'s
`split_why_it_matters` originally didn't know about this trailing block; since `## FAQ` always sits
_after_ `## Why It Matters` in the file, a reseed after any live FAQ append pulled the whole `## FAQ`
block into `why_it_matters_markdown`, and the FAQ rendered twice — once raw inside the "Why It
Matters" panel, once via the real, live "Questions & Answers" section. Confirmed live in a real build.
Fix: `split_why_it_matters` strips everything from `faq.FAQ_SECTION_MARKER` (`"\n## FAQ\n"`, a shared
constant so the writer and the stripper can't drift) onward **before** doing the "Why It Matters"
split. Any new template that parses a lesson `.md` file's body for something other than the FAQ blob
must apply this same strip first, or it will re-absorb the FAQ mirror the same way.

**SSE wire contract — every `data:` line must be a JSON object, matching the frontend's `StreamEvent`
type exactly.** This is a distinct layer from the LiteLLM streaming chunks above: those
(`ModelResponseStream` objects, delivered via the `on_token` callback) are what `lesson_qa.ask()`
consumes internally and re-yields as its own two plain-dict event shapes,
`{"type": "delta", "text": ...}` and `{"type": "result", "title": ..., "answer": ...}` — but
those dicts are **not** what goes over the wire. The service layer (`teaching.ask_about_lesson` /
`ask_about_lab`, one function per content type, both wrapping `lesson_qa.ask()`) must translate them
into the frontend's actual contract before the API layer serializes them:

- delta → `{"type": "delta", "delta": <text>}` (frontend field is `delta`, not `text`).
- result → `{"type": "result", "index": <int>, "question": <title>, "selected_text": <selected_text>,
"answer_markdown": <answer>}`, where `index` is `len(faq.parse_faq_entries(<current faq_markdown>))`
  computed **before** appending the new entry (0-based position of the entry about to be added).
  `selected_text` lets the client highlight the newly-answered entry's source passage immediately,
  without a refetch.
- **The result event must actually be yielded to the stream, not just used to update the DB/file and
  then dropped.** A real build got this wrong: the service function persisted the FAQ entry
  (`faq.append_faq_entry` + `faq.sync_*_faq`) on the result branch but never `yield`ed anything for it
  — only delta text ever reached the stream. Combined with sending raw un-JSON-encoded delta text (the
  other half of this bug), the frontend's `JSON.parse` on the very first delta line threw
  `unexpected character at line 1 column 1`; even after JSON-encoding, without the result event the
  frontend has nothing to resolve its "wait for the final answer" promise with and hangs, then times
  out with "stream ended without a result event". Both halves must be right together.
- The API endpoint (`lessons.py`/`labs.py`/`strategy.py`) just wraps each yielded dict with
  `f"data: {json.dumps(event)}\n\n"` — don't interpolate raw text/dicts into the SSE line directly.
  The `event: error\ndata: ...` error path needs the same treatment: `json.dumps({"error": str(exc)})`,
  not the bare exception text (which fails `JSON.parse` for the same reason).
- **`strategy.py`'s ask-question endpoint does not go through `teaching.py`** — it calls
  `lesson_qa.ask()` directly and inlines its own copy of this delta/result handling. Keep that inline
  copy byte-for-byte consistent with `teaching.py`'s translation logic (same field names, same `index`
  computation) rather than letting it drift; a full refactor to share the code is fine too if the
  routing (`SessionLocal()` per stream, committing/rolling back the _stream's own_ session rather than
  the request-scoped one) is preserved.

## `app/content/seed.py` and `validate.py`

- **seed**: for each `content/<topic_slug>/`, load `syllabus.yaml` (validating weights sum to 100 and
  required keys), upsert Topic/Domain/Objective, then lessons (split body at `## Why It Matters`),
  questions/choices, labs/checks, mock, strategy, and the badge catalog (+ per-domain master badges).
  Idempotent: safe to re-run.
- **validate**: the coverage rule in `references/content-schema.md`; non-zero exit on any gap.
- **Both `main()`s call `logging.basicConfig(level=logging.INFO, ...)`, which also flips on
  SQLAlchemy's per-statement echo/cache-stats logging** (`"dialect duckdb+duckdb_engine does not
support caching ..."`, one line per query) — `sqlalchemy.engine` has no level of its own, so it
  inherits root's `INFO`. Same root cause as the `openhands.sdk` root-logger note above, different
  trigger (plain stdlib `basicConfig`, not an SDK import). Fix in both files, right after
  `basicConfig`: `logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)`. Without it,
  every `seed`/`validate` run drowns its own real progress/error output in query-cache noise.
