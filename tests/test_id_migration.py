from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/learn-up/assets"))
from topic_transfer.id_migration import (  # noqa: E402
    migrate_topic_ids,
    plan_id_migration,
    validate_destination_ids,
)
from topic_transfer.types import TopicTransferError  # noqa: E402


def test_scalar_only_rewrite_and_idempotence(tmp_path):
    question = (
        "# 日本語\r\nquestions:\r\n"
        '  - external_id: "1.1-001" # keep\r\n'
        "    stem: |\r\n      external_id: 1.1-001\r\n"
        "  - {external_id: 'ga4-1.1-002', stem: é}\r\n"
    ).encode()
    files = {
        "questions/1.1.yaml": question,
        "strategy/questions.yaml": b"questions: [{external_id: strategy-pacing-001}]\n",
        "mocks/a.yaml": b'questions: ["1.1-001", ga4-1.1-002] # keep\n',
    }
    rewrites, mappings = plan_id_migration(files, "sample-topic")
    assert len(mappings) == 3
    assert {m.kind for m in mappings} == {"question", "strategy_question"}
    rewritten = {**files, **{r.path: r.after for r in rewrites}}
    assert rewritten["questions/1.1.yaml"] == question.replace(
        b'"1.1-001"', b'"sample-topic-1.1-001"'
    ).replace(b"'ga4-1.1-002'", b"'sample-topic-ga4-1.1-002'")
    assert yaml.safe_load(rewritten["mocks/a.yaml"])["questions"] == [
        "sample-topic-1.1-001",
        "sample-topic-ga4-1.1-002",
    ]
    assert plan_id_migration(rewritten, "sample-topic") == ([], [])
    for path, data in files.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    assert migrate_topic_ids(tmp_path, "sample-topic") == mappings
    assert all(
        (tmp_path / path).read_bytes() == data for path, data in rewritten.items()
    )


@pytest.mark.parametrize(
    "data",
    [
        b"questions: [{external_id: a}, {external_id: sample-topic-a}]",
        b"questions: [{external_id: a, external_id: b}]",
        b"questions: [{external_id: &id a}, {external_id: *id}]",
        b"questions: [{external_id: 123}]",
        b"questions: {}",
        b"[]",
        b"questions: [{stem: missing}]",
    ],
)
def test_invalid_shapes_never_write(tmp_path, data):
    target = tmp_path / "questions/a.yaml"
    target.parent.mkdir()
    target.write_bytes(data)
    with pytest.raises(TopicTransferError):
        migrate_topic_ids(tmp_path, "sample-topic")
    assert target.read_bytes() == data


def test_unknown_mock_and_global_duplicate_rejected():
    with pytest.raises(TopicTransferError, match="unknown"):
        plan_id_migration({"mocks/a.yaml": b"questions: [missing]"}, "sample-topic")
    with pytest.raises(TopicTransferError, match="collision"):
        plan_id_migration(
            {
                "questions/a.yaml": b"questions: [{external_id: a}]",
                "strategy/questions.yaml": b"questions: [{external_id: a}]",
            },
            "sample-topic",
        )


def test_live_legacy_tree_rejected_before_update(tmp_path):
    topic = tmp_path / "content/sample-topic"
    (topic / "questions").mkdir(parents=True)
    (topic / "questions/a.yaml").write_text("questions: [{external_id: a}]")
    with pytest.raises(TopicTransferError, match="complete the app upgrade"):
        validate_destination_ids(tmp_path / "content", topic, "sample-topic")


def test_archive_mapping_report_and_original_hashes(tmp_path):
    from test_topic_transfer import Adapter, export_fixture, make_repo, rewrite_archive
    from topic_transfer import TransferRoots, import_topic, stage_topic_archive

    source = tmp_path / "source"
    make_repo(source, version="1.11")
    (source / "content/sample-topic/questions/1.1.yaml").write_text(
        "questions: [{external_id: ga4-1.1-001}]\n"
    )
    archive = export_fixture(source, tmp_path)
    original = archive.read_bytes()
    destination = tmp_path / "destination"
    make_repo(destination)
    report = import_topic(
        archive,
        TransferRoots.from_repo(destination),
        Adapter(destination),
        confirm=False,
    )
    assert report.id_migrations[0].new_id == "sample-topic-ga4-1.1-001"
    assert asdict(report)["id_migrations"][0]["topic_slug"] == "sample-topic"
    mappings = []
    with stage_topic_archive(archive, "1.0", migration_report=mappings) as (
        _,
        stage,
        _,
    ):
        assert (
            b"sample-topic-ga4"
            in (stage / "content/sample-topic/questions/1.1.yaml").read_bytes()
        )
    assert mappings == report.id_migrations
    installed = import_topic(
        archive,
        TransferRoots.from_repo(destination),
        Adapter(destination),
        confirm=True,
    )
    assert installed.id_migrations == mappings
    assert (
        "ga4-1.1-001" in (destination / "content/sample-topic/CHANGELOG.md").read_text()
    )
    assert archive.read_bytes() == original
    corrupt = rewrite_archive(
        archive,
        tmp_path / "corrupt.learnup.zip",
        {
            "content/sample-topic/questions/1.1.yaml": b"questions: [{external_id: other-id001}]\n"
        },
        update_manifest=False,
    )
    with pytest.raises(TopicTransferError, match="mismatch"):
        with stage_topic_archive(corrupt, "1.0"):
            pytest.fail("corrupt archive accepted")
