# AGENTS.md — learn-up skill and plugin

This file describes conventions observed in this repository. It governs the distributable Agent
Skill and plugin sources here.

## 0. Repository Objectives

This repository distributes the `learn-up` skill for Codex and Claude Code. Its user-facing
executable code is the installer; the canonical skill, references, metadata, templates, and other
assets are packaged source material installed for an agent host.

Preserve these repository guardrails:

- Keep the Codex and Claude Code installations derived from the same canonical skill source.
- Keep installation explicit, inspectable, and safe: dry runs must not write, existing
  installations must not be overwritten by default, and `--force` must preserve a backup.
- Keep host-specific transformations narrow and preserve the source tree.
- Keep repository instructions about packaging, installation, validation, and maintenance. Put
  skill behavior in `skills/learn-up/SKILL.md` and its routed references instead of duplicating it
  here.

## 1. Technology Stack

This repository is a source distribution, not an application runtime.

- Plugin metadata: `.codex-plugin/plugin.json`, currently version `0.1.0`, plus Codex interface
  metadata in `skills/learn-up/agents/openai.yaml`.
- Canonical skill: Markdown with YAML frontmatter in `skills/learn-up/SKILL.md`; detailed Markdown
  guidance is loaded progressively from `skills/learn-up/references/`.
- Installer: the root `install.py` command delegates to the standard-library implementation in
  `learn_up_installer/`. The README requires Git and Python 3.10+ for manual installation.
- Python development tooling: `uv` with `pyproject.toml` and a committed `uv.lock`; pytest,
  pytest-cov, PyYAML, Ruff, and the pinned Git revision of `crap4py` are in the `dev` dependency
  group. The repository is not installed as a Python package.
- Cross-language formatting: Prettier is pinned in `package.json` and `package-lock.json`, with
  scripts for checking and writing Markdown, YAML, JSON, TypeScript, TSX, and CSS.
- Distributable skill payload: references, templates, scripts, components, styles, and brand assets
  under `skills/learn-up/`. These files do not define this repository's runtime stack.
- Runtime dependencies: none at this repository root. The root npm manifest is development-only;
  no database, Docker definition, or CI workflow is present.

## 2. Coding Standards

- Write code, comments, metadata, and documentation in English, matching all current sources.
- Keep the canonical `SKILL.md` compatible with the core Agent Skills format. Put host-specific
  behavior in `skills/learn-up/agents/openai.yaml` or the installer (`CONTRIBUTING.md`).
- Keep `SKILL.md` focused on phase orchestration and put detailed guidance in the relevant file
  under `skills/learn-up/references/`; do not duplicate long reference material.
- Use lowercase kebab-case for the skill/plugin name (`learn-up`) and topic/file slugs. Use
  lowercase snake_case for Python functions and variables and uppercase snake_case for constants.
- Python uses four-space indentation, type annotations, `pathlib.Path`, explicit exception types,
  and `from __future__ import annotations` where forward-compatible annotations are useful.
- User-facing CLI failures go to stderr and return a nonzero status. Unexpected content or command
  shapes raise instead of silently defaulting.
- Markdown prose is wrapped for review where practical. Preserve intentionally long literals,
  commands, URLs, and HTML.
- Adopt Ruff format/check for Python and Prettier for Markdown, YAML, JSON, TypeScript, TSX, and
  CSS; record versions and commands in root tool manifests.

## 3. Project Structure

```text
/
├── .codex-plugin/plugin.json       Codex plugin manifest and marketplace-facing metadata
├── install.py                      Stable manual-installer entry point
├── learn_up_installer/             Tested installer implementation
├── pyproject.toml                  Python, Ruff, pytest, and coverage configuration
├── package.json                    Pinned Prettier dependency and formatting scripts
├── package-lock.json               Reproducible npm development dependency lock
├── .prettierrc.json                Repository Prettier configuration
├── .prettierignore                 Paths excluded from Prettier
├── crap4py.config.json             CRAP source, coverage command, and failure threshold
├── uv.lock                         Reproducible development dependency lock
├── tests/test_install.py           Isolated installer unit and CLI tests
├── tests/test_quick_validate.py    Regression tests for the vendored skill validator
├── scripts/                        Vendored skill validator and its Apache-2.0 license
├── README.md                       User-facing positioning, install, use, and compatibility docs
├── CONTRIBUTING.md                 Issue and pull-request expectations
├── SECURITY.md                     Trust boundaries and private reporting guidance
├── LICENSE                         MIT license
├── .local/LAUNCH_PLAN.md           Gitignored local release/marketing checklist
└── skills/learn-up/
    ├── SKILL.md                    Canonical phased workflow and reference routing
    ├── agents/openai.yaml          Codex display metadata and invocation policy
    ├── references/                 Detailed skill instructions by workflow concern
    └── assets/                     Files distributed with the skill
```

Put cross-host workflow rules in `SKILL.md`, detailed skill guidance in the matching reference,
Codex-only UI metadata in `agents/openai.yaml`, installation behavior in `learn_up_installer/`, and
distributable files in `assets/`. Put repository-level tests under `tests/` and name test modules
and functions with the `test_` prefix.

## 4. Distribution Boundaries

- Treat `install.py` and `learn_up_installer/` as the product's executable implementation.
- Treat `skills/learn-up/` as the canonical payload. The installer may transform only the
  host-specific surfaces documented by the installation design.
- Do not move host-specific instructions into the canonical cross-host workflow.
- When a payload file's contract or destination changes, update the installer, references,
  metadata, documentation, and tests that describe or exercise it.
- Do not add an application runtime at the repository root.

## 5. Testing & Documentation

The repository uses pytest and pytest-cov, configured in `pyproject.toml`. Tests live under
`tests/`. The default run measures statement and branch coverage for `learn_up_installer/`, writes
`coverage.json`, and fails below 90%. The current verified result is 22 passing tests and 97%
displayed coverage (96.55% total) on Python 3.14.6.

Installer tests must use pytest's `tmp_path` and `monkeypatch` fixtures so they never write to the
real `~/.agents` or `~/.claude` directories. Cover user/project destination resolution, invalid
argument combinations, missing project roots, side-effect-free dry runs, both host transformations,
overwrite refusal and forced backups, source preservation, malformed/missing skills, and CLI return
codes.

For every change, use checks proportionate to the changed surface:

- Compile `install.py`, `learn_up_installer/`, and the vendored validator; parse
  `.codex-plugin/plugin.json` as JSON.
- Exercise `install.py --dry-run` for both `codex` and `claude-code`. For installer behavior
  changes, test clean installation, refusal to overwrite, `--force` backup behavior, and both user
  and project scopes in temporary directories.
- For canonical skill changes, run the vendored validator and preserve the documented reference
  routing.
- For payload changes, run the applicable static syntax, lint, and formatting checks without
  treating the payload as this repository's runtime.
- Keep README install/compatibility claims, `CONTRIBUTING.md`, `SECURITY.md`, the manifest version,
  host metadata, and affected reference files synchronized with behavior.
- `scripts/quick_validate.py`, vendored from OpenAI's built-in skill creator under Apache-2.0,
  validates the canonical skill's frontmatter, required fields, naming, and length constraints.
  Its license is retained in `scripts/OPENAI_SKILL_VALIDATOR_LICENSE.txt`.
- `crap4py` is pinned through `[tool.uv.sources]` to
  `https://github.com/AndresParraSilva/crap4py.git` at
  `fix/silent-100pct-on-coverage-miss`. Scores 10 or higher fail, 5–9 require inspection, and scores
  below 5 are low risk. `crap4py.config.json` selects `learn_up_installer/`, runs `uv run pytest` for
  coverage, and sets the failure threshold. The verified baseline passes: maximum CRAP is 6.0 and
  no functions have N/A coverage.

## 6. Commands

The package is distributed as source and has no build step. Use `uv` for development dependencies.
Use `python3` for direct installer commands on this machine; the README also supports `python` where
that executable exists.

Install/sync development dependencies:

```bash
uv sync --group dev
npm ci
```

Show installer help:

```bash
python3 install.py --help
```

Preview project-scoped installation without writing:

```bash
python3 install.py --agent codex --scope project --project-dir . --dry-run
python3 install.py --agent claude-code --scope project --project-dir . --dry-run
```

Install manually for the current user:

```bash
python3 install.py --agent codex
python3 install.py --agent claude-code
```

Compile-check repository Python code:

```bash
python3 -m compileall -q install.py learn_up_installer scripts
```

Validate the plugin manifest's JSON syntax:

```bash
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
```

Validate the canonical Agent Skill:

```bash
uv run python scripts/quick_validate.py skills/learn-up
```

Check Python formatting and linting, then check the other supported text formats:

```bash
uv run ruff format --check .
uv run ruff check .
npm run format:check
```

Apply formatting:

```bash
uv run ruff format .
npm run format
```

Run all tests with the configured 90% coverage gate:

```bash
uv run pytest
```

Run one test:

```bash
uv run pytest --no-cov tests/test_install.py::test_successful_codex_installation
```

Combined complexity/coverage quality gate:

```bash
uv run crap4py
```

This repository has no server. Use the project-scoped dry runs above, or install the skill and
invoke `$learn-up <topic>` in Codex or `/learn-up <topic>` in Claude Code.

## 7. Git Operations

The repository is on `main`, has no commits, remotes, other branches, CI workflows, or pull-request
templates. All current project files are untracked, so no historical convention can be inferred.

- Use Conventional Commits in imperative English, for example `feat: add learn-up skill`.
- Work directly on `main` by default. Short-lived branches are optional when a change benefits from
  isolation; name them `<type>/<kebab-case-description>`, such as `fix/installer-backup` or
  `docs/source-policy`, merge them back into `main`, and delete them afterward.
- Changes made directly by the repository owner do not require a separate review. Any change
  proposed by another collaborator requires the owner's explicit approval before it is merged.
  Run the applicable installer, manifest, skill-validation, and test checks documented here before
  merging a contribution.

Keep commits and pull requests focused. State the operating systems and agent hosts actually tested.
Do not commit or push unless the user explicitly requests it.

## 8. Three-Tier Boundaries

### 1. Always Do

- Preserve canonical skill sources, host compatibility, safe installer behavior, and fail-loud
  validation.
- Update the relevant README, host metadata, reference, template, manifest, and test surfaces when
  a public distribution or installation contract changes.
- Run the relevant pytest/coverage, CRAP, skill-validator, manifest, installer, and documentation
  checks before handing off a change.
- Keep changes compatible with both Codex and Claude Code unless compatibility documentation is
  deliberately narrowed.

### 2. Ask First

- Ask before changing the public plugin name, versioning strategy, license, supported hosts,
  invocation policy, or installation destination.
- Ask before adding dependencies or committing binary artifacts beyond the existing brand assets.

### 3. Never Do

- Never commit `.env` files, API keys, credentials, private source material, or generated user
  output.
- Never overwrite an existing installation unexpectedly; preserve a timestamped backup when
  `--force` is explicitly used.
- Never silently drop, rewrite, or omit canonical payload files during installation.
