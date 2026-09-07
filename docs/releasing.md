# Releasing learn-up

The portable root `plugin.json` owns shared package identity. Copy its shared fields into
`plugins/learn-up/.codex-plugin/plugin.json`, retaining the Codex-only `skills` and `interface`
fields. `skills/learn-up/` is the only human-maintained skill payload. The marketplace tracks
`main` in the documented installation command; a user can explicitly select another Git ref.

Use semantic versions: patch for compatible fixes, minor for compatible capabilities, major for
breaking behavior or installation changes. This migration is **0.4.0**. Update the two manifests,
`pyproject.toml`, the version assertion in `tests/test_agent_plugin.py`, then run `uv lock`.
Do not add a development cachebuster suffix to a published release; publish a new version when
contents change.

## Release readiness

Run from the repository root:

```bash
python3 scripts/sync_codex_plugin.py
uv run python scripts/validate_agent_plugin.py
uv run python scripts/validate_marketplace.py
uv run python scripts/sync_codex_plugin.py --check
uv run python scripts/quick_validate.py skills/learn-up
uv run python -m compileall -q install.py learn_up_installer scripts
uv run ruff format --check .
uv run ruff check .
npm run format:check
uv run pytest
uv run crap4py
python3 install.py --agent codex --scope project --project-dir . --dry-run
python3 install.py --agent claude-code --scope project --project-dir . --dry-run
python3 scripts/check_release_tag.py v0.4.0
python3 scripts/smoke_codex_marketplace.py
git diff --check
```

Inspect generated changes before committing. The synchronization check must leave no stale payload.
CI validates Linux and Windows packaging, Git-backed installation/update, and fresh-process skill
discovery. It does not establish Desktop invocation support.
With the current bundled Codex plugin-creator skill, also run its
`scripts/validate_plugin.py plugins/learn-up` through `uv run python` using the installed skill's
absolute script path. This optional external validator is not a repository dependency.

Before release, run the fresh-install and update checks below on clean Linux and Windows profiles.
Record the actual CLI/Desktop versions and results in release notes; do not claim untested hosts.

## Clean profile verification

Use a separate OS account or temporary `CODEX_HOME` and home directory, outside the checkout, with
no standalone learn-up skill. Never edit your normal Codex configuration to simulate a clean user.

```bash
codex plugin marketplace add AndresParraSilva/learn-up --ref main
codex plugin list --marketplace learn-up --available --json
codex plugin add learn-up@learn-up
codex plugin list --marketplace learn-up --json
```

Check installed/enabled state and version. Open a new thread, invoke `$learn-up`, and verify that
the intake instructions and packaged references/assets load. Stop after intake; a packaging test
does not require generating an application.

For an update test, use a controlled Git repository served over HTTP with the same marketplace
layout. Install version A, change the manifest to version B and change a payload marker, commit,
and refresh the Git server. Run `codex plugin marketplace upgrade learn-up` followed by
`codex plugin add learn-up@learn-up`. Verify version B, the new marker, and the active skill path
in a new thread. Old versioned cache directories may remain; they must not supply the active skill.
No manual clone or skill copy may be required of the installing user.

## Publish

Update `CHANGELOG.md` with scope and test evidence. Commit directly on `main` after checks pass,
tag that commit, then push both refs:

```bash
git commit -m "feat: distribute learn-up through a Codex marketplace"
git tag v0.4.0
git push origin main v0.4.0
```

Do not include local plans, private files, or generated application output. If the project adopts
GitHub Releases, publish the changelog entry there after the tag is pushed. Repeat the clean
profile install from GitHub and verify the published version. Check GitHub Actions results.

## Rollback

Prefer a patch release fixing forward. Never rewrite a published tag. To select a known-good
marketplace release (only v0.4.0 and later have this layout), use supported ref selection:

```bash
codex plugin marketplace remove learn-up
codex plugin marketplace add AndresParraSilva/learn-up --ref v0.4.0
codex plugin add learn-up@learn-up
```

Open a new thread and verify the version. To resume upgrades, remove/re-add the marketplace with
`--ref main` and reinstall. Document affected versions and the fix in release notes. Pre-marketplace
versions require the documented manual installer and a backed-up standalone skill instead.
