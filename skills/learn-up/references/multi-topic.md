# ADD-TOPIC — extending an existing learn-up repo

When a `learn-up` repo already exists and the user invokes learn-up with a new topic (for example,
`/learn-up <new topic>` in Claude Code or `$learn-up <new topic>` in Codex), you are **adding an
independent topic**, not rebuilding. Topics never share content, sources, or progress.

## Preconditions

1. Confirm you're in (or targeting) the existing `learn-up` repo: `pyproject.toml` name `learn-up`,
   a `content/` dir with at least one `<topic_slug>/syllabus.yaml`, and the topic-aware app code.
2. Pick a **new unique `topic_slug`**. If it collides with an existing topic dir, ask the user for a
   different name or confirm they want to update the existing topic instead.

## Steps

1. **Intake** (Phase 1) and **Sources** (Phase 2) exactly as for a new app, writing into
   `sources/<new_topic_slug>/`.
2. **Syllabus + content** (Phases 3–4) under `content/<new_topic_slug>/` — same schemas, same
   mandatory lesson placeholder.
3. **No app-code changes** should be needed if the app was built topic-aware (routes under
   `/t/:topicSlug`, API under `/api/t/{topic_slug}`, a `Topic` table, and a HomePage picker). If you
   find the existing app is **single-topic** (older build), you must first upgrade it:
   - Add the `Topic` table and a `topic_id` FK on `Domain`, `MockExam`, `Attempt` (and backfill the
     existing topic as row 1).
   - Move existing `content/*` under `content/<original_topic_slug>/`.
   - Introduce the topic-scoped routes/prefixes and the HomePage picker (`references/frontend.md`).
     Do this as a clearly separate step and tell the user before touching their working app.
4. **Seed + validate + run** (Phase 6). Seeding is idempotent and loads all topics; validation checks
   every topic. The HomePage picker will now show the new topic automatically.
5. **Expose and document the new topic on About.** Confirm its complete `INTAKE.md`, `SOURCES.md`,
   and `content/<new_topic_slug>/CHANGELOG.md` render at `/t/<new_topic_slug>/about`. Adding a topic
   preserves the existing content/media contract, so increment the app's `MINOR` version, add a
   dated entry to root `ABOUT.md`, and follow `references/about.md`. If upgrading an older app first
   makes existing `content/` or `media/` incompatible without migration, use a major bump instead.

## Importing a shared topic

Import is the only path where an existing slug intentionally means an update instead of a naming
collision. Follow `references/topic-transfer.md` and use the copied service: validate/dry-run first,
show compatibility and replacement details, require confirmation, back up the existing topic, merge
unique Q&A, then reseed and validate. Never treat an archive as an ADD-TOPIC source folder or unpack
it manually. A new imported slug appears in the picker after reseeding; an updated slug retains its
topic route and topic-scoped learner progress while authored files/media are replaced and Q&A is
merged best-effort.

## Content language across topics

Topics in one repo can have **different content languages** — e.g. an existing English-content
`aws-certified-developer` topic and a new Spanish-content `historia-de-roma` topic living side by
side. When Phase 1's language question surfaces a different language than the repo's existing
topic(s):

- **Author the new topic's content in the selected language** — its `syllabus.yaml`, lessons,
  questions, labs, mock, all per `references/content-schema.md`'s language note. Nothing about
  existing topics changes.
- Record the topic's exact NotebookLM artifact locale separately as
  `notebooklm_output_language`. Video generation sets this account-wide value immediately before
  each new request, so topics with different content languages can safely share one app/profile.
- **Do not touch the app's UI chrome for this.** Nav labels, buttons ("Quick Drill", "Start Mock
  Exam"), page titles, empty states, error banners — all of that is shared, hardcoded English JSX in
  `frontend/src/`, and stays exactly as it already is. Do not add i18n/localization infrastructure,
  a language switcher, or per-topic UI translations unless the user explicitly asks for that as a
  separate feature — it's out of scope for adding a topic. The learner will see English nav chrome
  around non-English lesson content; that's expected, not a bug to fix.
- The one thing that's still English regardless of topic language: the mandatory Gemini Notebook
  placeholder line in every lesson (see `references/content-schema.md`) — never translate it.

## Home page behavior

With ≥2 topics, `/` lists all topics as cards (name, description, progress, continue link). With
exactly 1 topic it redirects straight in. Each topic keeps its own dashboard, mastery, attempts, XP
context, badges, and enabled modules — verify the new topic's `labs`/`strategy`/`assessment` toggles
come from **its own** `syllabus.yaml`, independent of other topics.

## Sanity check before finishing

- The new topic appears on the HomePage and links to `/t/<new_topic_slug>`.
- Its lessons, quizzes, and (if enabled) labs/mock/strategy work in isolation.
- Existing topics are untouched: their content, progress, and routes still work.
- The new topic's About page exactly matches its recorded intake, sources, and content changelog;
  the app version and root app history match every other topic's About page.
