# Changelog

## 1.0.0 — 2026-09-24

**Compatibility migration:** generated app major now follows the skill major. Same-major topic
packages import regardless of minor. Older receiving apps retain their minor restriction until
upgraded. New skill majors require a documented content/media migration, including no-op migrations
for installation-only breaking changes.

- Namespace question and strategy ids by topic; migrate legacy YAML scalar values and mock
  references after hash verification, with typed dry-run/confirm/provenance reports. Archive wire
  format remains 1.0 and `learn-up-topic-transfer/1`.
- Add explicit existing-app upgrades, complete rollback, compatible local-asset retention, and a
  separately rebuilt DuckDB migration preserving learner identities/history.
- Add ordered per-topic Next navigation and persisted completion footers, including stale-payload
  detection. Chains end within their topic.
- Wait up to six hours for lesson video generation; mention the course only on domain openers.
- Add the lab self-check answer non-disclosure rule and recorded skill version on About.
- Validation platform: Linux. Windows, Desktop invocation and live external video/LLM providers
  were not exercised for this release; see the release acceptance record for local results.

## 0.4.1

- Have generated app agents offer to contribute every improvement back to the learn-up skill
  through an upstream issue or pull request, with user approval before opening it.

Local verification on Linux: pytest with coverage through the CRAP gate; Ruff and Prettier;
manifest, skill, and release-tag validation; both host installer dry runs; Codex CLI 0.153.4
Git-backed install/update and fresh-process skill discovery smoke tests. Windows and Desktop
were not tested locally for this patch.

## 0.4.0

- Distribute Codex through the Git-backed `learn-up` marketplace and its nested plugin package.
- Keep the portable skill canonical and generate the checked-in Codex payload deterministically.
- Preserve Claude Code and manual installation, including overwrite refusal and forced backups.
- Document marketplace upgrades, migration from standalone skills, release checks, and rollback.
- Validate metadata, payload synchronization, and installation on Linux and Windows in CI.

Local verification: Codex CLI 0.153.4 on Linux; clean Git-backed installation and version-A to
version-B upgrade; a fresh app-server process discovers only the active installed plugin skill.
Desktop interaction and a model-driven `$learn-up` intake conversation remain manual acceptance
checks. CI results provide the Windows test evidence; configuring the job alone is not a pass.
