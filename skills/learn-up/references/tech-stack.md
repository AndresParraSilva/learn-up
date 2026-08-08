# Phase 5 — Tech stack

## Contents

- Stack and generated repository layout
- Python dependencies and DuckDB constraints
- Development commands and cross-platform port checks

The generated `learn-up` repo mirrors the template app's stack, with **DuckDB replacing Postgres**.
Because DuckDB is an embedded, single-writer, synchronous engine, the backend is **synchronous
SQLAlchemy** (not async) — this is the one deliberate divergence from the template's async design.

## Stack

- **Language/runtime:** Python **3.12+**, managed with **`uv`** (`.python-version`, `pyproject.toml`).
- **Backend:** FastAPI serving a JSON API; uvicorn for dev. Path operations are plain `def`
  (FastAPI runs them in a threadpool) since the DB layer is synchronous.
- **ORM/DB:** SQLAlchemy 2.x (**sync**) + **`duckdb_engine`**. Database is a single embedded file
  `learn_up.duckdb` at the repo root. All app tables live in the DuckDB schema **`learn`**.
- **Migrations:** none needed for the embedded DB — create the schema + tables at startup via
  `Base.metadata.create_all(engine)` guarded by a `CREATE SCHEMA IF NOT EXISTS learn`. (Alembic is
  optional and usually overkill for a local single-file DuckDB; skip it unless the user asks.)
- **Config:** pydantic-settings; read config from the environment, never hardcode. **Namespace every
  env var with a `LEARNUP_` prefix** (`SettingsConfigDict(env_prefix="LEARNUP_")`) — the user's shell
  may already export a bare `DATABASE_URL` for an unrelated project (commonly a Postgres URL for
  something else on their machine), and pydantic-settings lets OS env vars silently win over your
  `Settings` field default. An unprefixed `DATABASE_URL` will get clobbered by that and the app will
  try to load whatever driver the other URL's scheme implies (e.g. crash with
  `ModuleNotFoundError: No module named 'asyncpg'`) instead of using DuckDB. This bit a real build —
  don't reintroduce it.
- **Version:** two-part `MAJOR.MINOR`, starting at `1.0`; `[project].version` is authoritative. See
  `references/about.md` for compatibility and update rules.
- **Content:** version-controlled **YAML/Markdown** under `content/<topic_slug>/`, seeded into DuckDB.
- **Frontend:** **React SPA** — Vite + **TypeScript** under `frontend/`, React Router, react-markdown
  - remark-gfm, mermaid.

## Repository layout (generated app)

```
learn-up/
  pyproject.toml  .python-version  README.md  ABOUT.md  AGENTS.md
  learn_up.duckdb (gitignored)
  .env.example                    # documents every LEARNUP_* setting; .env is gitignored
  main.py                         # entrypoint: `from app.main import app`
  app/                            # FastAPI backend (see references/backend.md)
    config.py  db.py  models.py  schemas.py  constants.py  badges.py  main.py
    api/       # attempts, catalog, labs, lessons, progress, strategy, topics
    services/  # attempts, grading, mastery, progress, gamification, labs, teaching, strategy
      lesson_qa/            # FAQ core + backends/{claude_cli,codex_cli,openhands}.py
      topic_transfer/       # verbatim protocol package from assets/topic_transfer/
      topic_transfer_adapter.py # narrow generated catalog/validation adapter
    content/   # seed.py, validate.py, faq.py
  content/<topic_slug>/...         # per-topic YAML/Markdown (see references/content-schema.md)
  sources/<topic_slug>/...         # downloaded study sources + INTAKE.md + SOURCES.md
  media/<topic_slug>/...           # generated lesson videos, gitignored (see notebooklm-automation.md)
  scripts/generate_lesson_video.py # optional notebooklm-py-driven video generation
  scripts/manage_topic_transfer.py # verbatim export/import CLI
  frontend/                        # React + Vite + TS (see references/frontend.md)
  tests/test_topic_transfer_contract.py # verbatim protocol contract test
  .learnup-backups/                # gitignored recoverable import-update backups
```

## `pyproject.toml`

```toml
[project]
name = "learn-up"
version = "1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "sqlalchemy>=2.0.30",
    "duckdb-engine>=0.13",
    "duckdb>=1.1",
    "pydantic-settings>=2.4",
    "pyyaml>=6.0",
    "pypdf>=6.14",
]

[dependency-groups]
dev = ["pytest>=8.0"]
notebooklm = ["notebooklm-py[browser]>=0.8.0a3"]  # opt-in; check PyPI for the current version
# opt-in; only for LEARNUP_LLM_BACKEND=openhands. The claude_cli and codex_cli FAQ
# backends shell out to installed CLIs and need no Python dependency (see backend.md).
openhands = ["openhands-sdk>=1.36.1", "openhands-tools>=1.36.1"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

## Generated `AGENTS.md`

For a NEW-APP run, copy `assets/agents.template.md` to root `AGENTS.md`; do not reconstruct it from
the reference prose. Replace `<app_version>` with `1.0` and `<faq_llm_backend>` with the exact intake
value, remove the template note, and tailor optional-module and command statements to the generated
implementation. Fail the build if an angle-bracket placeholder remains. Before handoff, compare the
finished file against the generated README, `pyproject.toml`, settings, repository layout, and
enabled modules and correct every mismatch.

## DuckDB specifics (important)

- **Connection URL:** `duckdb:///learn_up.duckdb` (via env var `LEARNUP_DATABASE_URL`, default to
  that — see the namespacing note above; do not name it bare `DATABASE_URL`).
  No `+asyncpg`/`+psycopg` dance — DuckDB is sync.
- **Schema:** DuckDB supports schemas. On startup run `CREATE SCHEMA IF NOT EXISTS learn;` then
  `Base.metadata.create_all(engine)` (models use `MetaData(schema="learn")`).
- **Single writer:** DuckDB allows one read-write process. That's fine for this local single-user
  app — run one uvicorn worker. Don't design for concurrent writers.
- **Types:** use `Integer`, `String`, `Text`, `Boolean`, `Date`, `DateTime`, `Numeric`, `Float`.
  For auto-increment PKs, use a DuckDB **sequence** per table or `Integer primary_key` populated by a
  sequence default — DuckDB has no `SERIAL`. Simplest robust approach: define
  `Sequence("seq_<table>", schema="learn")` and set it as the column default. (See
  `references/data-model.md` for the exact pattern.)
- **Booleans/enums:** store enums as `String` with app-level validation (DuckDB enum support via
  SQLAlchemy is fragile); validate against the Python `StrEnum` on write and fail loudly on bad values.

## Commands (put these in the generated README + AGENTS.md)

- Sync backend deps: `uv sync`
- Add backend dep: `uv add <pkg>`
- Run backend (dev): `uv run uvicorn app.main:app --reload --port 8011`
- Seed content: `uv run python -m app.content.seed`
- Validate coverage: `uv run python -m app.content.validate`
- Export topic: `uv run python scripts/manage_topic_transfer.py export <slug> --output <file.learnup.zip>`
- Validate import: `uv run python scripts/manage_topic_transfer.py import <file.learnup.zip> --dry-run`
- Confirm import: `uv run python scripts/manage_topic_transfer.py import <file.learnup.zip> --confirm`
- Tests: `uv run pytest`
- Frontend (from `frontend/`): `npm install`, `npm run dev`, `npm run build`, `npm run lint`

The frontend dev server proxies `/api/*` to `http://127.0.0.1:8011` (port 8000 is often taken), and
identically proxies `/media/*` for lesson videos (see `references/notebooklm-automation.md`) — add
both entries to `frontend/vite.config.ts`'s `server.proxy`, pointed at whatever port you actually run
the backend on (see "Port conflicts" below).

## Port conflicts (check before you launch anything)

`8011` and `5173` are just defaults — on a dev machine running several projects they are frequently
**already bound by an unrelated process** (a different app's backend/frontend). Before Phase 6 starts
either server, use an available platform-native check: `ss -ltn` on Linux, `lsof -i :<port>` on
Linux/macOS, `Get-NetTCPConnection -LocalPort <port>` in PowerShell, or a short Python `socket.bind`
probe. Do not require a Unix-only command when the host is Windows.
If it's taken by something that isn't this repo's own leftover process, **do not kill it** — pick a
free port instead (e.g. `--port 8012` for uvicorn, `--port 5180 --strictPort` for `npm run dev`),
update `frontend/vite.config.ts`'s proxy `target` to match the backend port you actually used, and
report the real ports you launched on to the user instead of assuming the defaults.
