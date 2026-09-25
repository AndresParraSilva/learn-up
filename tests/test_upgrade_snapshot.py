from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/learn-up/assets"))
from upgrade_snapshot import (  # noqa: E402
    create_upgrade_snapshot,
    restore_upgrade_snapshot,
    set_upgrade_phase,
)


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, query):
        assert query == "SELECT 1"
        return self

    def fetchone(self):
        return (1,)


def test_interrupted_upgrade_restores_exact_recorded_paths_and_database(
    tmp_path, monkeypatch
):
    monkeypatch.setitem(
        sys.modules, "duckdb", SimpleNamespace(connect=lambda *a, **k: FakeConnection())
    )
    database = tmp_path / "app.duckdb"
    database.write_bytes(b"original database")
    (tmp_path / "content").mkdir()
    (tmp_path / "content/lesson.md").write_text("original")
    (tmp_path / "content/ignored.txt").write_text("private")
    (tmp_path / "ABOUT.md").write_text("version 1.11")
    (tmp_path / "unrelated.txt").write_text("old unrelated")
    original_hash = hashlib.sha256(database.read_bytes()).hexdigest()

    backup = create_upgrade_snapshot(
        tmp_path,
        database,
        [Path("content"), Path("ABOUT.md"), Path("new.py")],
        "abc123",
    )
    set_upgrade_phase(backup, "applying")
    (tmp_path / "content/lesson.md").write_text("new")
    (tmp_path / "content/added.md").write_text("new")
    (tmp_path / "ABOUT.md").write_text("version 1.12")
    (tmp_path / "new.py").write_text("new")
    (tmp_path / "unrelated.txt").write_text("updated unrelated")
    database.write_bytes(b"bad candidate")

    restore_upgrade_snapshot(tmp_path, backup)
    restore_upgrade_snapshot(tmp_path, backup)
    assert (tmp_path / "content/lesson.md").read_text() == "original"
    assert (tmp_path / "content/ignored.txt").read_text() == "private"
    assert not (tmp_path / "content/added.md").exists()
    assert not (tmp_path / "new.py").exists()
    assert (tmp_path / "ABOUT.md").read_text() == "version 1.11"
    assert (tmp_path / "unrelated.txt").read_text() == "updated unrelated"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == original_hash


def test_snapshot_rejects_overlap_and_backup_path(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules, "duckdb", SimpleNamespace(connect=lambda *a, **k: FakeConnection())
    )
    database = tmp_path / "app.duckdb"
    database.write_bytes(b"database")
    for paths in ([Path("content"), Path("content/topic")], [Path(".learnup-backups")]):
        with pytest.raises(ValueError):
            create_upgrade_snapshot(tmp_path, database, paths, "abc123")
    assert (
        not list((tmp_path / ".learnup-backups").glob("upgrade-*"))
        if (tmp_path / ".learnup-backups").exists()
        else True
    )
