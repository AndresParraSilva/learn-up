from __future__ import annotations

import hashlib
import shutil
import stat
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

ASSETS = Path(__file__).resolve().parents[1] / "skills/learn-up/assets"
sys.path.insert(0, str(ASSETS))

from topic_transfer import (  # noqa: E402
    TopicTransferError,
    TransferRoots,
    dump_manifest,
    export_topic,
    import_topic,
    load_manifest,
)
from topic_transfer.types import FileRecord  # noqa: E402


class Adapter:
    def __init__(self, repo: Path, *, fail_reseed_once: bool = False) -> None:
        self.repo = repo
        self.fail_reseed_once = fail_reseed_once
        self.reseed_calls = 0

    def resolve_topic_name(self, topic_slug: str) -> str:
        data = yaml.safe_load(
            (self.repo / "content" / topic_slug / "syllabus.yaml").read_text()
        )
        return data["topic_name"]

    def validate_staged_topic(self, staging_root: Path, topic_slug: str) -> None:
        syllabus = yaml.safe_load(
            (staging_root / "content" / topic_slug / "syllabus.yaml").read_text()
        )
        assert syllabus["topic_slug"] == topic_slug
        assert (staging_root / "sources" / topic_slug / "INTAKE.md").is_file()
        assert (staging_root / "sources" / topic_slug / "SOURCES.md").is_file()

    def reseed_and_validate(self) -> None:
        self.reseed_calls += 1
        if self.fail_reseed_once:
            self.fail_reseed_once = False
            raise RuntimeError("seed failed")


def markdown_faq(entries: list[tuple[str, str | None, str]]) -> str:
    if not entries:
        return ""
    rendered = []
    for question, selected, answer in entries:
        selected_line = f"<!-- selected: {selected} -->\n" if selected else ""
        rendered.append(f"### {question}\n{selected_line}\n{answer}")
    return "\n## FAQ\n\n" + "\n\n".join(rendered) + "\n"


def make_repo(
    root: Path,
    *,
    version: str = "1.0",
    lesson_entries: list[tuple[str, str | None, str]] | None = None,
    lab_entries: list[dict[str, str]] | None = None,
    strategy_entries: list[tuple[str, str | None, str]] | None = None,
) -> None:
    (root / "content/sample-topic/lessons/1.1").mkdir(parents=True)
    (root / "content/sample-topic/questions").mkdir()
    (root / "content/sample-topic/labs/1.1").mkdir(parents=True)
    (root / "content/sample-topic/strategy/lessons").mkdir(parents=True)
    (root / "content/sample-topic/strategy").mkdir(exist_ok=True)
    (root / "sources/sample-topic").mkdir(parents=True)
    (root / "media/sample-topic").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "learn-up"\nversion = "{version}"\n'
    )
    (root / "ABOUT.md").write_text(
        f"# About learn-up\n\n## Version history\n\n### {version}\n"
    )
    (root / "sources/sample-topic/INTAKE.md").write_text("# Intake — Sample Topic\n")
    (root / "sources/sample-topic/SOURCES.md").write_text("# Sources — Sample Topic\n")
    (root / "content/sample-topic/CHANGELOG.md").write_text("# Changes\n\n## v1\n")
    syllabus = {
        "topic_slug": "sample-topic",
        "topic_name": "Sample Topic",
        "syllabus_version": "v1",
        "domains": [],
    }
    (root / "content/sample-topic/syllabus.yaml").write_text(
        yaml.safe_dump(syllabus, sort_keys=False)
    )
    lesson = (
        "---\nobjective: '1.1'\ntitle: Lesson\n---\n\nLesson body.\n\n"
        "## Why It Matters\n\nReason.\n" + markdown_faq(lesson_entries or [])
    )
    (root / "content/sample-topic/lessons/1.1/lesson.md").write_text(lesson)
    questions = {"objective": "1.1", "questions": []}
    (root / "content/sample-topic/questions/1.1.yaml").write_text(
        yaml.safe_dump(questions, sort_keys=False)
    )
    lab = {
        "objective": "1.1",
        "title": "Lab",
        "faq": lab_entries or [],
    }
    (root / "content/sample-topic/labs/1.1/lab.yaml").write_text(
        yaml.safe_dump(lab, sort_keys=False)
    )
    strategy = (
        "---\ntopic: pacing\ntitle: Pacing\n---\n\nStrategy body.\n"
        + markdown_faq(strategy_entries or [])
    )
    (root / "content/sample-topic/strategy/lessons/pacing.md").write_text(strategy)
    (root / "content/sample-topic/strategy/questions.yaml").write_text(
        "questions: []\n"
    )
    (root / "media/sample-topic/lesson.mp4").write_bytes(
        b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42"
    )


def export_fixture(source: Path, destination: Path) -> Path:
    archive = destination / "sample-topic.learnup.zip"
    export_topic(
        TransferRoots.from_repo(source),
        Adapter(source),
        "sample-topic",
        archive,
        created_at="2026-08-08T12:00:00Z",
    )
    return archive


def rewrite_archive(
    original: Path,
    destination: Path,
    changes: dict[str, bytes],
    *,
    update_manifest: bool = True,
) -> Path:
    with zipfile.ZipFile(original) as source:
        members = {
            info.filename: source.read(info)
            for info in source.infolist()
            if not info.is_dir()
        }
    members.update(changes)
    manifest = load_manifest(members["manifest.yaml"])
    if update_manifest:
        records = []
        for record in manifest.files:
            data = members[record.path]
            records.append(
                FileRecord(record.path, len(data), hashlib.sha256(data).hexdigest())
            )
        members["manifest.yaml"] = dump_manifest(
            replace(manifest, files=tuple(records))
        )
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as target:
        target.writestr("manifest.yaml", members.pop("manifest.yaml"))
        for name in sorted(members):
            target.writestr(name, members[name])
    return destination


def test_new_topic_round_trip_and_canonical_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    destination.mkdir()
    (destination / "pyproject.toml").write_text(
        '[project]\nname = "learn-up"\nversion = "1.0"\n'
    )
    archive = export_fixture(source, tmp_path)
    second_archive = tmp_path / "second.learnup.zip"
    export_topic(
        TransferRoots.from_repo(source),
        Adapter(source),
        "sample-topic",
        second_archive,
        created_at="2026-08-08T12:00:00Z",
    )
    assert archive.read_bytes() == second_archive.read_bytes()

    with zipfile.ZipFile(archive) as first:
        manifest_bytes = first.read("manifest.yaml")
        assert first.namelist()[0] == "manifest.yaml"
        assert first.namelist()[1:] == sorted(first.namelist()[1:])
    assert dump_manifest(load_manifest(manifest_bytes)) == manifest_bytes

    adapter = Adapter(destination)
    dry_run = import_topic(
        archive, TransferRoots.from_repo(destination), adapter, confirm=False
    )
    assert dry_run.mode == "new"
    assert dry_run.status == "validated"
    assert not (destination / "content/sample-topic").exists()

    report = import_topic(
        archive, TransferRoots.from_repo(destination), adapter, confirm=True
    )
    assert report.status == "installed"
    assert (destination / "content/sample-topic/syllabus.yaml").is_file()
    assert (destination / "media/sample-topic/lesson.mp4").is_file()
    assert (
        "Source app version: `1.0`"
        in (destination / "content/sample-topic/CHANGELOG.md").read_text()
    )


def test_update_merges_unique_lesson_lab_and_strategy_q_and_a(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    common = ("Common?", None, "Common answer.")
    make_repo(
        source,
        lesson_entries=[common, ("Incoming?", "incoming text", "Incoming answer.")],
        lab_entries=[{"question": "Incoming lab?", "answer": "Incoming lab answer."}],
        strategy_entries=[("Incoming strategy?", None, "Incoming strategy answer.")],
    )
    make_repo(
        destination,
        lesson_entries=[common, ("Local?", "local text", "Local answer.")],
        lab_entries=[{"question": "Local lab?", "answer": "Local lab answer."}],
        strategy_entries=[("Local strategy?", None, "Local strategy answer.")],
    )
    archive = export_fixture(source, tmp_path)

    report = import_topic(
        archive,
        TransferRoots.from_repo(destination),
        Adapter(destination),
        confirm=True,
    )

    assert report.mode == "update"
    assert report.merged_q_and_a == 3
    assert report.backup is not None
    lesson = (destination / "content/sample-topic/lessons/1.1/lesson.md").read_text()
    assert lesson.count("### Common?") == 1
    assert "### Incoming?" in lesson
    assert "### Local?" in lesson
    lab = yaml.safe_load(
        destination.joinpath("content/sample-topic/labs/1.1/lab.yaml").read_text()
    )
    assert [entry["question"] for entry in lab["faq"]] == [
        "Incoming lab?",
        "Local lab?",
    ]
    strategy = destination.joinpath(
        "content/sample-topic/strategy/lessons/pacing.md"
    ).read_text()
    assert "### Incoming strategy?" in strategy
    assert "### Local strategy?" in strategy


@pytest.mark.parametrize(
    "unsafe_name",
    ["../escape.md", "/absolute.md", "bad\\path.md", "bad//path.md", "bad/./path.md"],
)
def test_import_rejects_unsafe_paths(tmp_path: Path, unsafe_name: str) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    malicious = tmp_path / "malicious.learnup.zip"
    shutil.copy2(archive, malicious)
    with zipfile.ZipFile(malicious, "a") as target:
        target.writestr(unsafe_name, "payload")
    with pytest.raises(TopicTransferError, match="path|Absolute"):
        import_topic(
            malicious,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_discards_and_reports_unsupported_regular_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    with zipfile.ZipFile(archive, "a") as target:
        target.writestr("sender-note.txt", "not imported")

    report = import_topic(
        archive,
        TransferRoots.from_repo(destination),
        Adapter(destination),
        confirm=False,
    )

    assert report.ignored == ["sender-note.txt"]
    assert not (destination / "sender-note.txt").exists()
    import_topic(
        archive,
        TransferRoots.from_repo(destination),
        Adapter(destination),
        confirm=True,
    )
    assert not (destination / "sender-note.txt").exists()


def test_export_excludes_source_binaries_and_runtime_media_state(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    make_repo(source)
    (source / "sources/sample-topic/private.pdf").write_bytes(b"private source")
    (source / "media/sample-topic/.notebook.json").write_text("{}")

    archive = tmp_path / "sample-topic.learnup.zip"
    report = export_topic(
        TransferRoots.from_repo(source), Adapter(source), "sample-topic", archive
    )

    assert "sources/sample-topic/private.pdf" in report.ignored
    assert "media/sample-topic/.notebook.json" in report.ignored
    with zipfile.ZipFile(archive) as transferred:
        assert all("private.pdf" not in name for name in transferred.namelist())
        assert all(".notebook.json" not in name for name in transferred.namelist())


@pytest.mark.parametrize(
    ("member", "payload", "message"),
    [
        ("about/INTAKE.md", b"\xff\xfe", "UTF-8"),
        ("content/sample-topic/syllabus.yaml", b"topic_slug: [", "Malformed YAML"),
        ("media/sample-topic/lesson.mp4", b"MZ executable", "MP4"),
    ],
)
def test_import_rejects_spoofed_allowlisted_files(
    tmp_path: Path, member: str, payload: bytes, message: str
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    malicious = rewrite_archive(
        archive, tmp_path / "malicious.learnup.zip", {member: payload}
    )
    with pytest.raises(TopicTransferError, match=message):
        import_topic(
            malicious,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_rejects_checksum_tampering_and_newer_versions(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source, version="1.1")
    make_repo(destination, version="1.0")
    archive = export_fixture(source, tmp_path)
    with pytest.raises(TopicTransferError, match="upgrade destination"):
        import_topic(
            archive,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )

    (destination / "pyproject.toml").write_text(
        '[project]\nname = "learn-up"\nversion = "1.1"\n'
    )
    tampered = rewrite_archive(
        archive,
        tmp_path / "tampered.learnup.zip",
        {"about/ABOUT.md": b"# Tampered\n"},
        update_manifest=False,
    )
    with pytest.raises(
        TopicTransferError, match="Declared size mismatch|Checksum mismatch"
    ):
        import_topic(
            tampered,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_rejects_symlink_and_nested_archive(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    symlink_archive = tmp_path / "symlink.learnup.zip"
    shutil.copy2(archive, symlink_archive)
    info = zipfile.ZipInfo("link.md")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(symlink_archive, "a") as target:
        target.writestr(info, "target")
    with pytest.raises(TopicTransferError, match="regular file"):
        import_topic(
            symlink_archive,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )
    nested_archive = tmp_path / "nested.learnup.zip"
    shutil.copy2(archive, nested_archive)
    with zipfile.ZipFile(nested_archive, "a") as target:
        target.writestr("payload.zip", b"PK")
    with pytest.raises(TopicTransferError, match="nested archive"):
        import_topic(
            nested_archive,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_rejects_case_collisions_and_protected_unknown_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    collision = tmp_path / "collision.learnup.zip"
    shutil.copy2(archive, collision)
    with zipfile.ZipFile(collision, "a") as target:
        target.writestr("ABOUT/about.md", "# collision")
        target.writestr("about/ABOUT.MD", "# collision")
    with pytest.raises(TopicTransferError, match="case-colliding"):
        import_topic(
            collision,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )

    protected = tmp_path / "protected.learnup.zip"
    shutil.copy2(archive, protected)
    with zipfile.ZipFile(protected, "a") as target:
        target.writestr("content/sample-topic/payload.txt", "payload")
    with pytest.raises(TopicTransferError, match="protected archive path"):
        import_topic(
            protected,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_transfer_rejects_symlinked_fixed_root(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    real_media = destination / "real-media"
    real_media.mkdir()
    shutil.rmtree(destination / "media")
    (destination / "media").symlink_to(real_media, target_is_directory=True)

    with pytest.raises(TopicTransferError, match="root cannot be a symlink"):
        import_topic(
            archive,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_rejects_missing_required_file_and_unsafe_yaml_alias(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    missing = tmp_path / "missing.learnup.zip"
    with zipfile.ZipFile(archive) as original, zipfile.ZipFile(missing, "w") as target:
        for info in original.infolist():
            if info.filename != "about/SOURCES.md":
                target.writestr(info.filename, original.read(info))
    with pytest.raises(TopicTransferError, match="inventory mismatch"):
        import_topic(
            missing,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )

    aliased = rewrite_archive(
        archive,
        tmp_path / "aliased.learnup.zip",
        {
            "content/sample-topic/syllabus.yaml": b"topic_slug: &slug sample-topic\ntopic_name: *slug\n"
        },
    )
    with pytest.raises(TopicTransferError, match="aliases|anchors"):
        import_topic(
            aliased,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_rejects_major_and_archive_format_incompatibility(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source, version="2.0")
    make_repo(destination, version="1.9")
    archive = export_fixture(source, tmp_path)
    with pytest.raises(TopicTransferError, match="major versions"):
        import_topic(
            archive,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )

    with zipfile.ZipFile(archive) as original:
        members = {
            info.filename: original.read(info)
            for info in original.infolist()
            if not info.is_dir()
        }
    manifest = load_manifest(members["manifest.yaml"])
    members["manifest.yaml"] = dump_manifest(replace(manifest, archive_format="1.1"))
    newer_format = tmp_path / "newer-format.learnup.zip"
    with zipfile.ZipFile(newer_format, "w") as target:
        for name, data in members.items():
            target.writestr(name, data)
    with pytest.raises(TopicTransferError, match="archive format|Archive format"):
        import_topic(
            newer_format,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_import_enforces_entry_and_compression_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import topic_transfer.core as core

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source)
    make_repo(destination)
    archive = export_fixture(source, tmp_path)
    monkeypatch.setattr(core, "MAX_ENTRIES", 2)
    with pytest.raises(TopicTransferError, match="too many entries"):
        import_topic(
            archive,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )
    monkeypatch.setattr(core, "MAX_ENTRIES", 4096)
    monkeypatch.setattr(core, "MAX_COMPRESSION_RATIO", 1)
    compressed = rewrite_archive(
        archive,
        tmp_path / "compressed.learnup.zip",
        {
            "content/sample-topic/lessons/1.1/lesson.md": (
                b"---\nobjective: '1.1'\ntitle: Lesson\n---\n\n"
                + b"A" * (2 * 1024 * 1024)
            )
        },
    )
    with pytest.raises(TopicTransferError, match="compression-ratio"):
        import_topic(
            compressed,
            TransferRoots.from_repo(destination),
            Adapter(destination),
            confirm=False,
        )


def test_failed_reseed_restores_existing_topic(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    make_repo(source, lesson_entries=[("Incoming?", None, "Incoming answer.")])
    make_repo(destination, lesson_entries=[("Local?", None, "Local answer.")])
    original = (destination / "content/sample-topic/lessons/1.1/lesson.md").read_bytes()
    archive = export_fixture(source, tmp_path)
    adapter = Adapter(destination, fail_reseed_once=True)

    with pytest.raises(RuntimeError, match="seed failed"):
        import_topic(
            archive, TransferRoots.from_repo(destination), adapter, confirm=True
        )

    assert (
        destination / "content/sample-topic/lessons/1.1/lesson.md"
    ).read_bytes() == original
    assert adapter.reseed_calls == 2
