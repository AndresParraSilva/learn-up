# Phase 5 — About page and compatibility versioning

## Contents

- Version contract
- About-page source documents
- Backend and frontend contract
- Update rules
- Validation and smoke tests
- Topic-transfer trust and provenance

The About page is the human-readable record of how the app was configured, what evidence grounds
each topic, and how the generated app has changed. Do not hardcode a summary that can drift from the
repository files. Render the source documents described below.

## Compatibility version

Use a two-part `MAJOR.MINOR` app version. Set the initial generated version to `1.0` in
`pyproject.toml`:

```toml
[project]
name = "learn-up"
version = "1.0"
```

`project.version` is the authoritative app compatibility version. It is separate from:

- the distributable skill/plugin version;
- each topic's `syllabus_version`, which identifies that topic's taxonomy revision; and
- dates or headings in change logs.

Require the exact `MAJOR.MINOR` shape with a positive major, a non-negative minor, and no
prerelease, patch, or build suffix. The generated app's content validator must fail if the version
is missing or malformed.

For every later app or content change:

1. Decide compatibility by copying an existing installation's `content/` and `media/` directories
   into the updated app without transforming either tree, then seeding, validating, and opening the
   copied lessons and videos.
2. If that workflow still works unchanged, increment `MINOR` (for example, `1.0` to `1.1`).
3. If a migration, rewrite, rename, relocation, or regeneration of anything in either tree is
   required, increment `MAJOR` and reset `MINOR` to `0` (for example, `1.4` to `2.0`).
4. Never infer compatibility from a successful frontend build alone. Exercise the copied content
   and media in the live smoke test.
5. Treat the topic-transfer contract as part of content/media compatibility. If old archives need
   migration or transformation, increment `MAJOR`; a backward-compatible archive-format extension
   increments its own format minor and the app minor.

## Source documents rendered by About

Create a root `ABOUT.md` during every NEW-APP run. It describes the app itself and contains its
compatibility-version history. Start it with:

```markdown
# About learn-up

This local study app was generated from the configuration and sources shown on each topic's About
page.

## Version history

### 1.0 — YYYY-MM-DD

- Initial generated application.
```

The topic-scoped About page renders all of these files, without truncation:

1. Root `ABOUT.md` — app description and complete compatibility-version history.
2. `sources/<topic_slug>/INTAKE.md` — every questionnaire answer, follow-up answer, supplied
   constraint, and selected module/backend/language value.
3. `sources/<topic_slug>/SOURCES.md` — every user-provided and agent-gathered source, including its
   origin and limitations.
4. `content/<topic_slug>/CHANGELOG.md` — the topic's dated content changes and syllabus version.

It also shows this fixed warning near the topic-transfer controls:

> Import learn-up topics only from people and sources you trust. Validation reduces common archive
> risks, but it cannot make an untrusted archive safe.

An imported topic appends its source app `MAJOR.MINOR`, archive format, source syllabus version,
archive creation time, and archive SHA-256 to the topic changelog. That provenance therefore renders
on About. Never replace root `ABOUT.md` with the source app's archived About snapshot; the root file
always describes the destination app.

Do not put secrets in these documents or return secret environment values through the API. Intake
must never ask for credential values. When configuration depends on a secret, record only the
environment-variable name and whether the user intends to configure it.

Treat a missing file, unreadable UTF-8, malformed app version, or topic path outside the resolved
topic directories as an error. Do not replace missing About data with empty strings or generic
fallback prose.

## Backend contract

Add `GET /api/t/{topic_slug}/about` to the catalog router. Resolve the topic first, then return the
exact source documents above:

```python
class AboutOut(BaseModel):
    app_version: str
    app_markdown: str
    intake_markdown: str
    sources_markdown: str
    content_changes_markdown: str
```

Read `app_version` from `[project].version` in root `pyproject.toml` with the standard-library
`tomllib`. Read the four Markdown documents from their exact paths. Validate `topic_slug` through
the existing topic lookup before constructing paths; never accept an arbitrary filesystem segment.

The content validator must check every topic has non-empty `INTAKE.md`, `SOURCES.md`, and
`CHANGELOG.md`; root `ABOUT.md` is non-empty; the app version has the required shape; and the current
version appears as a `### <version> — <date>` entry under `ABOUT.md`'s `## Version history`. It must
also verify the intake and source contracts described in `references/intake.md` and
`references/sources.md`.

## Frontend contract

Mirror `AboutOut` exactly in `frontend/src/api/types.ts` and add an API client method for the About
endpoint. `AboutPage` must display:

- `App version <app_version>` as visible metadata;
- the rendered root `app_markdown`;
- a `Configuration` section rendering `intake_markdown`;
- a `Sources` section rendering `sources_markdown`; and
- a `Content changes` section rendering `content_changes_markdown`.

Use the shared `Markdown` component for every Markdown field. Do not summarize, select a subset,
collapse entries by default, or duplicate the values into JSX constants. The page must show every
recorded configuration parameter and source.

## Update rules

The generated `AGENTS.md` makes About maintenance mandatory. Apply it as follows:

- Every app or content change: bump the compatibility version and add a dated root `ABOUT.md`
  version entry. For a topic-only change, the root entry may point to that topic's detailed content
  changelog.
- App code, dependency, configuration, structure, or behavior change: describe it in the root
  `ABOUT.md` version entry.
- Topic content change: also add a dated entry to that topic's
  `content/<topic_slug>/CHANGELOG.md` so its details appear on the topic About page.
- Intake/configuration change: update `INTAKE.md`, bump the compatibility version, and document the
  change in the topic changelog.
- Source addition, removal, replacement, or reassessment: update `SOURCES.md`, bump the
  compatibility version, and document the change in the topic changelog.
- A change touching both app and content: update both change-log surfaces; use one version bump
  chosen by the compatibility test.
- Adding topic transfer to an existing generated app: increment `MINOR`, document the copied assets,
  and keep old content/media working unchanged. A fresh generated app still starts at `1.0` with the
  feature included.
- Importing a topic: preserve the destination app version/history, append import provenance to the
  imported topic changelog, and expose the import/update report. Importing data does not itself
  change the destination app version unless app code or its compatibility contract also changed.

Keep `pyproject.toml`, the latest root `ABOUT.md` version-history entry, generated README version
statements, and the version returned by the endpoint synchronized.

## Smoke tests

Test the endpoint for a real topic and verify every Markdown field is non-empty and the returned
version is `1.0` on a fresh build. Open About in the browser and compare every intake parameter and
source entry against the files on disk. For an ADD-TOPIC run, verify the page switches to the new
topic's intake, sources, and content changelog while showing the same current app version and root
version history as every existing topic page.
Also export and import a topic between compatible app versions. Verify the destination About page
shows the trust warning, destination app history, source app/archive versions, and archive checksum,
without rendering the source root app history as if it belonged to the destination.
