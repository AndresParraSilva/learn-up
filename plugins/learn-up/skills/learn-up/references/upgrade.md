# Upgrading an existing learn-up app

## Shared preflight and version routing

Resolve the target app before any ARCHIVE, TRANSFER, GENERATE-VIDEO or ADD-TOPIC operation.
Read its `AGENTS.md`, `ABOUT.md`, `[project].version` and `[tool.learn-up] skill_version` in
`pyproject.toml`. Compare skill releases numerically with `assets/skill_version.py` (strict
MAJOR.MINOR.PATCH); app versions use the separate MAJOR.MINOR parser. The installed skill's
`SKILL.md` metadata is authoritative for its own version.

- Missing skill metadata means an unknown legacy baseline. Inventory capabilities and local
  changes; do not assign an invented historical skill release.
- Older or unknown: offer once per run, “Upgrade this app to learn-up skill X.Y.Z before continuing?”
  Explicit UPGRADE already authorizes this workflow, but asset conflicts still need resolution.
- Equal: a completed upgrade is a no-op. Check for an interrupted-upgrade journal before proceeding.
- Newer than installed: stop and ask the user to update the skill. Never downgrade the app.
- Different recorded skill major: proceed only through a documented content/media migration for
  that transition; otherwise refuse and name both versions. No 1 → 2 migration is provided here.

On decline, continue the requested supported operation with the app's own copied assets and
`AGENTS.md`. Existing-app archive staging must load its own protocol, never the installed skill's
newer importer. If the requested capability is missing, explain it and stop that operation. Newly
authored question ids still carry topic prefixes, which legacy apps accept. Do not repeat the offer.

## Preconditions, inventory and recovery

1. Require a clean Git working tree and record its starting commit. Stop with concrete instructions
   for resolving outstanding edits; never stash, commit, reset or clean user work automatically.
2. Resolve the configured DuckDB path from the app configuration/environment. Stop all app processes,
   workers and writers before backup. A locked database is a failed precondition, not permission to
   kill an unidentified process or copy a database while it is changing.
3. Record whether a `.wal` exists. With writers stopped, open normally to replay/checkpoint it, close
   the connection, and require a cleanly closed database without an outstanding WAL. Back up that
   database and verify the backup opens read-only. A WAL is not required after clean shutdown.
4. Use `assets/upgrade_snapshot.py` in the app's locked Python environment: call
   `create_upgrade_snapshot(root, configured_database, changed_paths, starting_commit)` to create
   `.learnup-backups/upgrade-<UTC timestamp>/` outside every path being replaced. Inventory
   each touched path (tracked, untracked and ignored), existence, file type and SHA-256;
   preserve the original bytes and permissions, including content, metadata, source configuration and the configured
   database even when outside the repo. Record upgrade-created paths separately. Reject unexpected
   symlinks in mutation paths. Never include secrets in the report or commit backups.
5. Use `set_upgrade_phase(backup, phase)` for the atomic journal. Record planned asset decisions
   and mappings in the upgrade report alongside it; the journal records starting commit, database
   path/hash and each changed path with original existence, type and hashes. Record starting versions,
   candidate versions and phase in the report. The phases are `prepared`, `applying`, `validated`,
   `complete` or `rolled-back`. Persist each phase before the next action. If interrupted, restore the complete
   snapshot using `restore_upgrade_snapshot(root, backup)` before rerunning; never infer success
   merely from candidate version metadata.
6. On any failure, stop upgrade-started processes, call `restore_upgrade_snapshot(root, backup)`
   to restore original code, content, version/history,
   database and permissions together. Remove only recorded upgrade-created files. Remove the failed
   candidate WAL before restoring the checkpointed database; never combine it with the backup.
   Verify original hashes, database openability and learner rows. Report both the original error and
   any recovery error. Keep the backup/journal. Never use an indiscriminate Git clean/reset.

## Asset decisions and application

Inventory canonical asset source/destination paths and generated dependencies using the copy tables
in `SKILL.md`, `frontend.md`, `topic-transfer.md` and `notebooklm-automation.md`. Include authentication,
router registration, API types, About and seeder/validator contracts. Use `.learnup-skill-assets.json`
when present: it records each source, destination, generating skill version and canonical SHA-256.
A missing baseline means unknown; a byte difference alone cannot identify a local customization.
Call `assets/upgrade_assets.py`'s `inspect_asset` for each canonical source/destination pair using
the recorded baseline hash when present; it distinguishes current, upstream-only, local-only,
both-changed and unknown-baseline. Show diffs and explicitly review unknown baselines before
claiming a complete upgrade.

For each changed asset, offer replacement with the new canonical bytes or retention of a compatible
local copy. Record retained files and reasons in the candidate `ABOUT.md` entry and asset inventory.
If retaining a file violates a required contract, stop until the conflict is resolved. If mutation
has begun, restore the entire snapshot first. Never advance skill metadata or claim success for an
incompatible partial upgrade. Offer to propose useful local improvements upstream, but open no issue,
PR or message without user approval. Before writing anything, call `preflight_asset_decisions`
with a decision for every changed asset. A kept copy needs an explicit compatibility finding and
nonempty reason; an unresolved/incompatible keep raises `UpgradeAssetConflict`. Record the returned
retained reasons in the candidate About entry. If a later validation reveals incompatibility, restore
the complete snapshot before stopping.

Refresh generated `AGENTS.md` from `assets/agents.template.md`, retaining app-specific facts. Apply
all release sections between the recorded version and target in order; feature-detect existing local
implementations to avoid duplicate changes. Prepare candidate app version, skill metadata and matching
root/topic history together **before** validation. Same-major upgrades increment the app minor once;
a documented skill major change sets the new major and minor zero. For unknown legacy apps already
at app major 1, this migration retains major 1 (source app 1.11 becomes 1.12).

Run full content validation, database migration, reseed, backend tests, frontend tests/build and a
live smoke test. Verify About sees the candidate metadata. Only after all pass, finalize
“Upgraded to learn-up skill X.Y.Z”, applied changes and retained deviations in root `ABOUT.md`, update
the asset inventory and mark the journal complete. Report results and offer a commit; never commit
automatically. This workflow never drops learner progress.

## Apps built before 1.0.0 → 1.0.0

This release migrates question identifiers; it does **not** transform `media/`. The archive wire
format stays `1.0` and `learn-up-topic-transfer/1`. Legacy app major 1 remains major 1, with a minor
increment for the upgrade. Release minors thereafter must preserve readability across app major 1.

- Refresh canonical `topic_transfer/`, CLI/router, TypeScript report helper, transfer panel and
  contract tests as a coordinated unit. Install missing transfer integration/authentication before
  claiming success; preserve the session-token contract and loopback protections.
- Refresh `lesson_video_service.py`, `CompletionFooter.tsx`, `completion.ts`, `completion.test.ts`
  and `index.css`; retain newer canonical console logging, HTML rejection, resumable source sync,
  viewport-clamped SelectionAsk, token handling and archive staging.
- Generate per-topic `sequence.py` and required nullable `next` fields from `backend.md`. Remove
  cross-topic chains; update page routes, completion gating and list ordering per `frontend.md`.
- Set video wait to 21600 seconds. Course mention applies only to objectives whose last dotted
  segment is exactly `1`; missing/blank objectives fail.
- Add prefix/duplicate validation and cross-topic seeder ownership guards for both question kinds.
  Preserve selected Choice and StrategyChoice identities during reseed; update unchanged rows in
  place. Strict new authoring grammar must accept migrated legacy suffixes during validation.
- Record `[tool.learn-up] skill_version = "1.0.0"`; expose it on About, with null only for an
  unrecorded legacy baseline. Use strict numeric release parsing.
- Apply the lab self-check non-disclosure rule to newly authored/changed lab prompts. Do not import
  source-app topic-specific content or free-trial lab guidance as canonical behavior.

### Question IDs and DuckDB rebuild (before reseeding)

DuckDB 1.5.5 rejects an UPDATE of the unique indexed `external_id` when dependent rows exist, even
inside a transaction. Use a separate rebuilt database. The procedure was verified on 169 questions,
19 strategy questions and synthetic learner history in an isolated source-app 1.11 checkout.

1. For every topic, call `plan_id_migration(topic_id_files(topic_path), topic_slug)` from the copied
   `topic_transfer.id_migration` module. Save all proposed rewrites and mappings before writing any
   live file. Each mapping carries topic, entity kind, relative file path, old id and new id. Check
   all destination topics for collisions, and run full content validation on a staged rewritten tree.
2. Copy `assets/rebuild_question_ids.py` to an upgrade workspace and call
   `rebuild_question_ids(source_database, new_database, mappings)` using the app's locked Python
   environment. The destination must not exist. This helper:
   - resolves every old row through real topic relationships and entity kind;
   - rejects missing/stale/ambiguous mappings, duplicate targets and conflicts before mutation;
   - exports the closed source database with DuckDB's own `EXPORT DATABASE ... (FORMAT PARQUET)`;
   - changes only mapped `external_id` fields in temporary, unconstrained Parquet copies;
   - imports into a new database using DuckDB's dependency-ordered schema/load files, preserving
     constraints, explicit indexes, primary keys and sequence state;
   - compares every table's complete row multiset (allowing only the mapped id changes), schema,
     indexes, views and sequence definitions, then checkpoints/closes the candidate;
   - removes a failed candidate while leaving the source untouched.
     The current helper expects the `learn` schema and canonical question ownership model; a different
     schema requires an explicitly reviewed adaptation and the same preservation proof.
3. Verify backup and rebuilt database with the app's actual locked DuckDB version. Compare next
   sequence values on **disposable copies**, never by consuming live sequences. Record checksums.
   Close all connections and atomically replace the configured live database on the same filesystem.
   Apply the already validated content rewrites before starting/reseeding the app.
4. Reseed and validate. Compare identities, values and links for attempts, attempt questions,
   responses, selected choices, mastery, lesson/strategy read state, lab/strategy attempts, XP,
   streaks and badges. Counts alone are insufficient. No-op content must not recreate choices or
   invalidate selected answers. Any discrepancy invokes the complete rollback above.
5. Append the mapping to each affected topic changelog; keep original archive hashes as source
   provenance. Already-prefixed content yields no rewrites. A completed upgrade is a no-op; a stale
   map against an already migrated database fails, so recover interrupted runs before replanning.

### Acceptance cases

Use a clean temporary checkout and independently seeded database; never modify the source app.
Add synthetic learner history when the original database lacks it. An original topic archive is
supplementary; a canonical export of source-app-1.11 real content with legacy ids is an accepted
substitute. Record commit, versions, fixture origin, checksums and baseline results.

Test both importer directions (old receivers retain their minor rule), real content staging into
1.0, both question kinds, legacy suffixes, collisions, missing/stale mappings, reseed/build/smoke
failures with complete rollback, completed/interrupted reruns and compatible/incompatible retained
assets. Frontend tests must execute in an app, since this distribution's root npm runs formatting
only. Report unavailable host/provider checks as unverified.

## Future releases

Every release changing generated-app behavior adds an ordered “X → Y” section here. Every skill
major declares a new app compatibility family and must document content/media migration, even when
a breaking installation change needs a no-op content migration. Highlight it in `CHANGELOG.md`.
