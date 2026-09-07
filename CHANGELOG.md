# Changelog

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
