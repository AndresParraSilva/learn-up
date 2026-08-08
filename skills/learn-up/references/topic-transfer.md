# Topic export and import

## Contents

- Trust boundary
- Archive layout and manifest
- Export contract
- Defensive import pipeline
- Version compatibility
- New topics, updates, and Q&A merge
- Commands, API, and UI
- Validation

Use this workflow when a learner shares a prepared topic with another learn-up installation. The
wire format and all security-sensitive behavior come from the assets named below. Copy them
verbatim; do not reimplement archive handling from this prose.

## Trust boundary

Show this warning beside every import control, in import command help and startup output, in the
generated README, and on About:

> Import learn-up topics only from people and sources you trust. Validation reduces common archive
> risks, but it cannot make an untrusted archive safe.

An imported file is data, never executable input. Never run it, import it as Python, render raw HTML
from it outside the existing sanitized Markdown path, preserve its permissions, or place it outside
the fixed topic roots. The importer validates in a temporary directory before changing the live
app. Ordinary unsupported regular files are ignored and reported; an unsafe archive structure or
invalid allowlisted file rejects the entire archive.

## Canonical assets

Copy these assets byte-for-byte into every generated app:

| Skill asset                              | Generated destination                            |
| ---------------------------------------- | ------------------------------------------------ |
| `assets/topic_transfer/`                 | `app/services/topic_transfer/`                   |
| `assets/manage_topic_transfer.py`        | `scripts/manage_topic_transfer.py`               |
| `assets/topic_transfer_router.py`        | `app/api/topic_transfer.py`                      |
| `assets/TopicTransferPanel.tsx`          | `frontend/src/components/TopicTransferPanel.tsx` |
| `assets/topicTransfer.ts`                | `frontend/src/api/topicTransfer.ts`              |
| `assets/test_topic_transfer_contract.py` | `tests/test_topic_transfer_contract.py`          |

The Python package owns the format constants, canonical manifest serializer/parser, ZIP handling,
hashes, path checks, resource limits, file validation, version decisions, Q&A merge, staging,
backup/rollback, and report shapes. The generating model supplies only
`app/services/topic_transfer_adapter.py`, implementing the package's narrow `TransferAdapter`
protocol for topic lookup, staged content validation, and live reseeding. It also registers the
copied router, documents the copied CLI, and mounts the copied component. Do not edit the copied
protocol package to fit an app; fix the adapter.

The generated content validator must import `IMPLEMENTATION_ID` and compare it with the expected
value in the copied contract test. Fail if an asset is missing, its identifier differs, or the
contract test is absent.

## Archive layout

Use a ZIP file ending in `.learnup.zip`. It contains exactly one declared topic and uses these fixed
archive paths:

```text
manifest.yaml
about/ABOUT.md
about/INTAKE.md
about/SOURCES.md
about/CHANGELOG.md
content/<topic_slug>/syllabus.yaml
content/<topic_slug>/CHANGELOG.md
content/<topic_slug>/**/*.md
content/<topic_slug>/**/*.yaml
media/<topic_slug>/*.mp4
```

The four files below `about/` are the source installation's complete topic About snapshot. Require
`about/INTAKE.md`, `about/SOURCES.md`, and `about/CHANGELOG.md` to be byte-identical to their
canonical topic files. `about/ABOUT.md` is a source-app snapshot only; never overwrite the
destination's root `ABOUT.md` with it.

Only `.md`, `.yaml`, and `.mp4` regular files are transferable. Source PDFs, images, HTML,
credentials, `.env`, the DuckDB file, progress, attempts, mastery, XP, badges, NotebookLM state,
logs, caches, Python/JavaScript, nested archives, and unrelated topics are excluded.

### `manifest.yaml`

`manifest.yaml` is the machine contract. About Markdown is not parsed as a manifest. Emit the
manifest with the canonical asset serializer and parse it with `yaml.safe_load`; reject unknown or
missing keys instead of defaulting them. The schema is:

```yaml
archive_format: "1.0"
implementation: "learn-up-topic-transfer/1"
topic_slug: ancient-rome
topic_name: Ancient Rome
source_app_version: "1.0"
syllabus_version: v1
created_at: "2026-08-08T13:00:00Z"
files:
  - path: about/ABOUT.md
    size: 1234
    sha256: 64-lowercase-hex-characters
```

Sort file entries by path. Use UTF-8, LF line endings, stable key ordering, explicit string
versions, and no YAML aliases or custom tags. The manifest does not inventory itself. Every other
regular archive entry must appear exactly once in `files`, and every inventory entry must exist
exactly once. Archive member order is `manifest.yaml` followed by inventory order. Normalize ZIP
timestamps and permission metadata so identical inputs plus the same explicit `created_at` produce
the same logical manifest and member order.

Keep these versions separate:

- `archive_format` versions the compressed-file wire protocol.
- `source_app_version` is the source app compatibility `MAJOR.MINOR` from `pyproject.toml`.
- `syllabus_version` is the topic taxonomy version from `syllabus.yaml`.
- `implementation` identifies the copied protocol implementation and contract tests.

## Export contract

The copied service must:

1. Resolve the topic through the adapter/catalog, then construct paths only beneath the fixed
   `content/`, `sources/`, and `media/` roots.
2. Validate the exact two-part app version, required About files, syllabus identity, and topic
   content before collecting files.
3. Walk without following symlinks. Reject a symlink, non-regular file, disallowed suffix under an
   allowlisted tree, path collision, or file that changes size while read.
4. Include all topic `.md` and `.yaml` content, the four About snapshots, and only direct expected
   `media/<topic_slug>/*.mp4` lesson videos. Do not scan outside the topic roots.
5. Validate each file by content, calculate its size and SHA-256, build the canonical manifest, and
   write a new archive. Refuse to overwrite an output unless the user explicitly passes
   `--overwrite`.
6. Return a structured report with the output path, topic, versions, file counts, bytes, and
   omitted categories. Never include secret values in a report.

## Defensive import pipeline

Run the copied pipeline in this order:

1. Stream the uploaded or local archive to a bounded temporary file. Never trust a browser filename
   or load an unbounded request body into memory.
2. Open it as ZIP and enumerate every member before extraction. Enforce the asset constants for
   maximum archive bytes, entries, per-file uncompressed bytes, total uncompressed bytes, and
   compression ratio.
3. Reject absolute paths, drive/UNC paths, `..`, `.`, empty segments, backslashes, NULs, non-NFC
   names, duplicate normalized names, case-fold collisions, encrypted members, data descriptors
   with inconsistent sizes, nested archives, symlinks, hard links, devices, sockets, and other
   non-regular entries. Directory entries may only describe parents of valid members.
4. Read and strictly validate `manifest.yaml`, then apply version compatibility before extracting
   content.
5. Ignore and report an ordinary regular member whose suffix is not `.md`, `.yaml`, or `.mp4` only
   when it is not inventoried and is beneath no protected archive path. Reject executable/nested
   archive suffixes, an unsupported member at a required path, and any inventory mismatch.
6. Extract inventoried members into `tempfile.TemporaryDirectory` using paths constructed by the
   service. Do not call `ZipFile.extract()` or `extractall()` and do not preserve permissions.
7. Hash while copying and reject any declared size/checksum mismatch.
8. Validate Markdown as strict UTF-8 without NULs. Require the expected heading/frontmatter shape
   for About, lesson, strategy, and changelog paths. Validate YAML with `yaml.safe_load`, reject
   aliases/custom tags and unexpected shapes, then run the adapter's complete staged content
   validator. Verify MP4 by parsing the leading ISO Base Media File Format boxes and requiring a
   plausible `ftyp` box plus the expected direct lesson-media path; a renamed executable is not an
   MP4.
9. Produce a side-effect-free dry-run report. Do not change live paths until the user confirms an
   update after reviewing that report.

Any structural, limit, manifest, checksum, allowlisted-content, compatibility, or required-file
error rejects the whole import with a nonzero command exit or explicit HTTP error. Do not silently
salvage a partial topic.

## Version compatibility and import provenance

Read the destination app version from `pyproject.toml`:

- Different major: reject and name both versions.
- Same major, incoming minor greater than destination minor: reject and tell the recipient to
  upgrade the destination app.
- Same major, incoming minor equal to or older than destination: accept.
- Malformed or unsupported archive/app version: reject.

A new generated app remains version `1.0`. When adding this feature to an already generated app,
it is a backward-compatible app change: increment that app's minor version and document it in root
`ABOUT.md`. A later change that requires rewriting or migrating old archives, `content/`, or
`media/` increments the app major and resets the minor to zero. A backward-compatible extension of
the archive format increments its format minor; an incompatible wire change increments its format
major.

Before live installation, append a dated import entry to the staged topic `CHANGELOG.md` containing
the source app version, archive format, source topic/syllabus version, creation time, and archive
SHA-256. This preserves provenance on the destination About page without replacing the
destination's app history.

## New topic, update, and Q&A merge

For a new slug, install only the staged `content/<slug>/`, `sources/<slug>/INTAKE.md`,
`sources/<slug>/SOURCES.md`, and `media/<slug>/` trees. Then reseed and run live validation.

For an existing slug:

1. Treat the import as an update and show the dry-run report before confirmation.
2. Copy the existing topic content, About source records, and media into a timestamped backup
   outside all live roots.
3. Merge Q&A into the incoming staged authored content before installation. Match by content kind
   plus stable objective/topic and slug. Parse the exact FAQ formats from `app/content/faq.py`:
   trailing `## FAQ` sections for lesson/strategy Markdown and `faq:` lists for lab YAML.
4. Normalize whitespace only for deduplication. Retain the incoming entry order, then append unique
   local entries in their original order. Keep question, optional selected text, and answer
   together. Write the canonical FAQ representation back to staged Markdown/YAML.
5. Skip and report a well-formed Q&A entry whose stable target no longer exists or is ambiguous.
   Reject malformed FAQ syntax rather than guessing.
6. Replace only that topic's live content/About records/media, reseed, and validate. On any write,
   seed, or validation failure, restore the backup and rerun reseed/validation before returning a
   failure.

Imported authored content wins conflicts; unique local and incoming Q&A are retained. Do not merge
the database or learner progress, attempts, mastery, XP, badges, or settings. Report installed,
replaced, merged, skipped, ignored, and restored items plus the backup path.

## Commands, API, and UI

The copied CLI uses the shared package and adapter:

```bash
uv run python scripts/manage_topic_transfer.py export <topic_slug> --output <file.learnup.zip>
uv run python scripts/manage_topic_transfer.py import <file.learnup.zip> --dry-run
uv run python scripts/manage_topic_transfer.py import <file.learnup.zip> --confirm
```

The copied router exposes raw ZIP bodies without adding multipart dependencies:

- `GET /api/t/{topic_slug}/export` downloads the archive.
- `POST /api/topics/import?dry_run=true` validates a capped streamed request and returns the report.
- `POST /api/topics/import?confirm=true` repeats validation and performs the confirmed import.

The copied frontend API helper and `TopicTransferPanel` provide Export, choose archive, Validate,
review report, and Confirm import controls. Mount the panel on the topic picker and link/export from
About. Confirmation is a separate user action for updates. Refresh the catalog after success and
show all compatibility, ignored-file, merged-Q&A, and backup details returned by the backend.

## Validation

Copy and run `assets/test_topic_transfer_contract.py`. Add adapter/integration tests for the
generated app. Cover canonical manifests, new-topic round trips, update/Q&A merge, About provenance,
dry runs, rollback, and every hostile archive class listed above. The content validator must also
assert that every canonical asset and contract test exists with the expected implementation ID.

Smoke-test one export/import between two clean generated apps with the same major version, then an
update with local-only and incoming-only Q&A. Confirm imported videos play and the destination About
page shows both its own app version/history and the imported topic provenance.
