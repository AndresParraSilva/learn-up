# Phase 5 — Data model (DuckDB, multi-topic)

## Contents

- Primary-key pattern
- Topic taxonomy and content tables
- Assessment and learner state
- Gamification and strategy tables
- Relationships

SQLAlchemy 2.x declarative models in `app/models.py`, `MetaData(schema="learn")`. This generalizes
the template's model in two ways: (1) DuckDB instead of Postgres, (2) a top-level **`Topic`** so one
repo holds many independent subjects. **Everything content-side hangs off a `Topic`.**

## DuckDB PK pattern

DuckDB has no `SERIAL`. Give each table an explicit sequence:

```python
from sqlalchemy import Sequence, Integer
from sqlalchemy.orm import mapped_column, Mapped

# one per table, e.g. seq_topic, seq_domain, ...
id: Mapped[int] = mapped_column(
    Integer, Sequence("seq_topic", schema="learn"), primary_key=True
)
```

Enums are stored as `String` and validated in Python against a `StrEnum`; raise on unknown values
(fail loudly). Timestamps: `DateTime`, set in app code (`datetime.now(UTC)`); don't rely on DB
`server_default` functions that DuckDB may not support — set defaults in Python.

**Instant timestamps vs. calendar-day fields — do not use the same clock for both.** `DateTime`
columns that record _when something happened_ (`last_reviewed_at`, `responded_at`, `earned_at`,
`created_at`) are absolute instants — set those with `datetime.now(UTC)`. But `Date` columns that
represent _which calendar day it is right now_ for day-boundary logic (`last_activity_date`,
`due_on`, and any `today = ...` used to compute them — see the streak/SM-2 algorithms in
`references/backend.md`) must be derived from `datetime.now().date()` (the server's local date),
**not** `datetime.now(UTC).date()`. This app is a local single-user tool — the backend runs on the
same machine as the user, so the server's local date _is_ the user's calendar day. Using UTC here
is a real bug, not a style choice: it was shipped in a real build and surfaced as a 1-day-old user
seeing a "2 day streak," because any activity after roughly 9pm in a UTC-negative timezone (or
before roughly 3am in a UTC-positive one) falls on a different UTC calendar date than the user's
actual "today," so two same-day answers land on different `date()` values and the streak/SM-2
scheduling logic reads them as separate days.

## Core taxonomy (per topic)

- **Topic** — `id`, `slug` (unique), `name`, `description`, `syllabus_version`, plus assessment/module
  facts loaded from `syllabus.yaml`: `assessment_enabled`, `assessment_question_count`,
  `assessment_minutes`, `assessment_scoring` (`percent`|`scaled`), `pass_pct` / `pass_score_scaled` /
  `max_score_scaled`, `penalty_for_wrong_answers`, `labs_enabled`, `strategy_enabled`.
- **Domain** — `id`, `topic_id → topic.id`, `code`, `name`, `weight_pct`, `syllabus_version`.
  Unique on (`topic_id`, `code`).
- **Objective** — `id`, `domain_id → domain.id`, `code`, `title`, `description`, `syllabus_version`.
  Unique on (`topic_id` via domain, `code`) — in practice enforce unique `code` per topic.
- **Lesson** — `id`, `objective_id`, `slug` (unique), `title`, `body_markdown`,
  `why_it_matters_markdown`, `faq_markdown` (default "").
- **Question** — `id`, `objective_id`, `external_id` (unique), `question_type` (`single`|`multi`),
  `stem_markdown`, `explanation_markdown`, `difficulty` (int), `is_mock_eligible` (bool),
  `syllabus_version`.
- **Choice** — `id`, `question_id`, `position`, `text_markdown`, `is_correct` (bool),
  `distractor_explanation_markdown`.
- **Lab** — `id`, `objective_id`, `slug` (unique), `title`, `scenario_markdown`, `setup_sql`,
  `task_markdown`, `expected_result`, `faq_markdown`.
- **LabCheck** — `id`, `lab_id`, `position`, `prompt_markdown`, `kind` (StrEnum: `contains`, `exact`,
  `number_positive`, `number_less_than_previous`, `number_greater_than_previous`),
  `expected_value` (nullable), `case_sensitive` (bool). Unique (`lab_id`, `position`).

## Assessment / mock

- **MockExam** — `id`, `topic_id`, `code` (unique), `syllabus_version`.
- **MockExamQuestion** — `id`, `mock_exam_id`, `question_id`, `position`. Unique (`mock_exam_id`, `position`).

## Learner state

Single local user is fine, but scope progress **per topic** so topics stay independent.

- **User** — `id`, `display_name` (unique), `created_at`, `xp`, `current_streak`, `longest_streak`,
  `last_activity_date` (date, nullable), `streak_freeze_count`. (XP/streaks are global flavor; keep
  them global or per-topic — global is simplest and fine.)
- **Attempt** — `id`, `user_id`, `topic_id`, `attempt_type` (StrEnum: `practice`, `domain_drill`,
  `quick_drill`, `mock`), `mock_exam_id` (nullable), `started_at`, `finished_at` (nullable),
  `score_raw` (nullable), `score_scaled` (nullable), `passed` (bool nullable).
- **AttemptQuestion** — `id`, `attempt_id`, `question_id`, `position`. Unique (`attempt_id`, `position`).
- **Response** — `id`, `attempt_id`, `question_id`, `is_correct`, `responded_at`.
- **ResponseChoice** — `id`, `response_id`, `choice_id`. Unique (`response_id`, `choice_id`).
- **Mastery** — `id`, `user_id`, `objective_id`, `repetitions`, `ease_factor` (Numeric(4,2) def 2.5),
  `interval_days`, `due_on` (date), `last_reviewed_at`. Unique (`user_id`, `objective_id`). This is
  the SM-2 spaced-repetition row (algorithm in `references/backend.md`). Objective → domain → topic
  gives per-topic scoping.
- **LabAttempt** — `id`, `user_id`, `lab_id`, `passed`, `checked_at`.

## Gamification

- **Badge** — `id`, `code` (unique), `name`, `description`, `icon` (emoji string).
- **UserBadge** — `id`, `user_id`, `badge_id`, `earned_at`. Unique (`user_id`, `badge_id`).
  A fixed catalog (first attempt, perfect quick drill, streaks, pass the mock, reach GO) plus one
  **per-domain "domain master" badge generated at seed time** from the topic's domains.

## Strategy (only if strategy_enabled)

Mirrors the template's exam-mechanics tables, scoped by `topic_id` and a fixed `topic` (meaning the
strategy sub-topic, e.g. `time-management`):

- **StrategyLesson** — `id`, `topic_id`, `topic` (the strategy sub-topic string), `slug` (unique),
  `title`, `body_markdown`, `why_it_matters_markdown`, `faq_markdown`.
- **StrategyQuestion** — `id`, `topic_id`, `topic`, `external_id` (unique), `question_type`,
  `stem_markdown`, `explanation_markdown`.
- **StrategyChoice** — `id`, `question_id`, `position`, `text_markdown`, `is_correct`,
  `distractor_explanation_markdown`.
- **StrategyLessonProgress** — `id`, `user_id`, `strategy_lesson_id`, `read_at`. Unique pair.
- **StrategyAttempt** — `id`, `user_id`, `strategy_question_id`, `is_correct`, `answered_at`.

## Relationships

Domain 1─* Objective 1─* {Lesson, Question, Lab}; Question 1─* Choice; Lab 1─* LabCheck;
Attempt 1─* {AttemptQuestion, Response}; Response 1─* ResponseChoice; User 1─* {Attempt, Mastery,
UserBadge, LabAttempt}; Topic 1─* {Domain, MockExam, Attempt} and (via Domain→Objective) all content.

Use `selectinload` for eager loading in read paths (sync SQLAlchemy supports it).
