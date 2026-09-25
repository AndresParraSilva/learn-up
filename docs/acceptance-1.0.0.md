# Learn-up 1.0.0 acceptance record

## Fixture and scope

- Date: 2026-09-25; platform: Linux x86_64, Python 3.12 app environment, DuckDB 1.5.5.
- Isolated checkout: `/tmp/learnup-acceptance-gjAhGq/app`, cloned from
  `learn-up-work` commit `e7fb14171f7263f88770501ca7dacdb8877faa89`.
- The original app stayed untouched. Its database was locked by a running process, so the
  isolated checkout was seeded independently. Its baseline suite: 64 passed, 1 skipped.
- Added synthetic history in the isolated database: one attempt, attempt question, response,
  selected response choice, mastery row, lesson read, lab attempt, strategy lesson read,
  strategy attempt, user badge, XP and streak. No original learner-history rows were used.
- The original `snowpro-core.learnup.zip` was unavailable. The accepted substitute was exported
  through the canonical exporter from source-app-1.11 content in the isolated checkout.
  SHA-256: `e24b7f52b1033da1a453c278fe4a3acbcf089de6993bf430904a33cd74f5dc40`.

## Database and content

- Populated source database SHA-256 before migration: `5cbbcd4eb9a91a1caa3fc435ce525eb6bbea1456b7f5951d0cd652dc702c7d3d`.
- A populated DuckDB 1.5.5 UPDATE of unique `external_id` with dependent rows failed with a
  foreign-key constraint, confirming the planned rebuild prerequisite.
- The separately rebuilt candidate migrated 169 question and 19 strategy-question ids. Complete
  row comparisons proved all other values, identities and relationships equal, including selected
  choices, mastery, read/passed state, XP and badges. Schema, indexes and sequence definitions
  matched; next sequence values matched on disposable copies.
- After upgrading and reseeding the isolated app, exact comparisons still matched all learner
  history tables (attempt, response, selected choice, mastery, read/passed and badge) and 679
  choices plus 76 strategy choices. Its content validator passed.
- The real-content archive staged into app 1.0 with 124 proposed ID migrations. Its bytes and
  original manifest/hash remain source provenance. A dry run and a confirmed update passed in a
  separate smoke copy; confirmation produced a topic backup and full content validation passed.
- The old importer accepted real-content 1.0 → 1.11 and rejected 1.11 → 1.0, preserving its old
  minor rule. The new importer accepted 1.11 → 1.0. Root protocol tests cover both new directions,
  major rejection, malformed versions, collisions, mock rewrite, legacy suffixes and corrupt hashes.
- Stale and wrong-owner database mappings failed without changing the source database or leaving
  a candidate. A simulated interrupted upgrade restored code, content, version metadata and database
  bytes, removed upgrade-created paths, preserved unrelated files, and was idempotent on rerun.

## Application and release checks

- Isolated upgraded app: version 1.12, recorded skill 1.0.0; 61 backend tests passed, 1 skipped.
  The per-topic Next tests cover both topics, numeric/mixed order and final null items.
- Frontend: 16 Vitest tests passed, including completion states, routing/back navigation and read
  persistence failure; TypeScript/Vite production build passed. The app smoke test passed health,
  token rejection/acceptance, About versions, final Next and archive dry run.
- Repository: 140 pytest tests passed; installer coverage 91.91%. Agent Plugins and marketplace
  validators, skill validator, Python compile/Ruff, Prettier, installer dry runs, release tag check,
  Codex payload sync check and marketplace fresh-process smoke passed. CRAP maximum 8 (gate passed).
- Host/provider checks: CLI packaging discovery and installed Claude-policy validation were exercised locally. Windows, desktop invocation,
  a fresh interactive skill session, live NotebookLM generation and external LLM calls remain
  unverified. No claims are made for those environments.

The isolated fixture and scripts remain under `/tmp/learnup-acceptance-gjAhGq` for inspection.
They are not part of the distributable payload.

## Shared local installation

- `~/.agents/skills/learn-up` and `~/.claude/skills/learn-up` resolve to
  `/home/andres/dotfiles/.agents/skills/learn-up`.
- The Claude user-scope `--force --dry-run` left the prior SKILL.md hash unchanged. The one
  subsequent `--force` refresh preserved the previous 25-file install at
  `/home/andres/dotfiles/.agents/skills/learn-up.backup-20260925T063502Z`.
- All 47 installed payload files match the canonical source, except SKILL.md's retained
  `disable-model-invocation: true` and `allowed-tools` frontmatter fields. The shared aliases,
  skill metadata version 1.0.0 and backup's prior hash were verified. The installed copy passed
  `quick_validate.py --claude-code`; the canonical copy passed strict validation.
- A fresh interactive Codex or Claude session was unavailable for direct invocation testing.
  Fresh-process marketplace package discovery passed separately.
