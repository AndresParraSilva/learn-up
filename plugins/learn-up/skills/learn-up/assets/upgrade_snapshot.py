from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(path: Path) -> dict[str, str]:
    if path.is_symlink():
        raise ValueError(f"Upgrade path is a symlink: {path}")
    if path.is_file():
        return {".": _hash(path)}
    if path.is_dir():
        result = {}
        for child in sorted(path.rglob("*")):
            if child.is_symlink():
                raise ValueError(f"Upgrade path contains a symlink: {child}")
            if child.is_file():
                result[child.relative_to(path).as_posix()] = _hash(child)
        return result
    if path.exists():
        raise ValueError(f"Unsupported upgrade path: {path}")
    return {}


def _write_journal(backup: Path, data: dict) -> None:
    target = backup / "journal.json"
    temporary = backup / ".journal.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def create_upgrade_snapshot(
    root: Path,
    database: Path,
    changed_paths: list[Path],
    starting_commit: str,
) -> Path:
    """Capture explicit targets. Stop writers and checkpoint DuckDB before calling."""
    import duckdb

    root = root.resolve(strict=True)
    database = database.resolve(strict=True)
    if not database.is_file() or Path(str(database) + ".wal").exists():
        raise ValueError("Database must be a closed, checkpointed regular DuckDB file")
    paths = sorted({path.as_posix() for path in changed_paths})
    if not paths or not starting_commit:
        raise ValueError("Upgrade snapshot needs changed paths and starting commit")
    for path in paths:
        relative = Path(path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative == Path(".")
            or relative.parts[0] == ".learnup-backups"
            or not (root / relative).resolve(strict=False).is_relative_to(root)
        ):
            raise ValueError(f"Unsafe upgrade path: {path}")
        if any(parent.as_posix() in paths for parent in relative.parents):
            raise ValueError(f"Overlapping upgrade paths: {path}")
    if database.is_relative_to(root) and any(
        database.is_relative_to(root / path) for path in paths
    ):
        raise ValueError("Database must be snapshotted separately from changed paths")
    base = root / ".learnup-backups"
    base.mkdir(exist_ok=True)
    backup = base / ("upgrade-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f"))
    backup.mkdir()
    try:
        entries = {}
        for number, path in enumerate(paths):
            target = root / path
            if target.resolve(strict=False) != target and target.is_symlink():
                raise ValueError(f"Upgrade path is a symlink: {target}")
            manifest = _inventory(target)
            exists = target.exists()
            entries[path] = {
                "exists": exists,
                "is_dir": target.is_dir(),
                "hashes": manifest,
            }
            if exists:
                saved = backup / "files" / str(number)
                saved.parent.mkdir(parents=True, exist_ok=True)
                if target.is_dir():
                    shutil.copytree(target, saved, symlinks=False)
                else:
                    shutil.copy2(target, saved)
        shutil.copy2(database, backup / "database.duckdb")
        with duckdb.connect(
            str(backup / "database.duckdb"), read_only=True
        ) as connection:
            connection.execute("SELECT 1").fetchone()
        data = {
            "state": "prepared",
            "starting_commit": starting_commit,
            "database": str(database),
            "database_sha256": _hash(database),
            "paths": entries,
        }
        _write_journal(backup, data)
        return backup
    except BaseException:
        shutil.rmtree(backup, ignore_errors=True)
        raise


def set_upgrade_phase(backup: Path, phase: str) -> None:
    if phase not in {"applying", "validated", "complete", "rolled-back"}:
        raise ValueError(f"Unknown upgrade phase: {phase}")
    journal = json.loads((backup / "journal.json").read_text())
    current = journal["state"]
    allowed = {
        "prepared": {"applying", "rolled-back"},
        "applying": {"validated", "rolled-back"},
        "validated": {"complete", "rolled-back"},
        "complete": set(),
        "rolled-back": set(),
    }
    if phase not in allowed[current]:
        raise ValueError(f"Invalid upgrade phase transition: {current} → {phase}")
    journal["state"] = phase
    _write_journal(backup, journal)


def restore_upgrade_snapshot(root: Path, backup: Path) -> None:
    """Restore only recorded targets and the DB; keep unrelated ignored files."""
    import duckdb

    root = root.resolve(strict=True)
    backup = backup.resolve(strict=True)
    if not backup.is_relative_to(root / ".learnup-backups"):
        raise ValueError("Backup path is outside this app's upgrade backup directory")
    journal = json.loads((backup / "journal.json").read_text())
    if journal["state"] == "complete":
        raise ValueError("Completed upgrade cannot be rolled back as an interruption")
    database = Path(journal["database"])
    if database.is_symlink():
        raise ValueError("Refusing to replace symlinked database")
    for path in journal["paths"]:
        target = root / path
        if target.is_symlink() or not target.resolve(strict=False).is_relative_to(root):
            raise ValueError(f"Refusing to restore over symlink: {target}")
    # The caller has stopped all processes. Remove candidate WAL before replacing the DB.
    Path(str(database) + ".wal").unlink(missing_ok=True)
    replacement = database.with_name(database.name + ".learnup-restore")
    shutil.copy2(backup / "database.duckdb", replacement)
    os.replace(replacement, database)
    for number, (path, record) in enumerate(journal["paths"].items()):
        target = root / path
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        if record["exists"]:
            saved = backup / "files" / str(number)
            target.parent.mkdir(parents=True, exist_ok=True)
            if record["is_dir"]:
                shutil.copytree(saved, target)
            else:
                shutil.copy2(saved, target)
        if _inventory(target) != record["hashes"]:
            raise ValueError(f"Upgrade rollback verification failed: {path}")
    if _hash(database) != journal["database_sha256"]:
        raise ValueError("Upgrade database rollback hash mismatch")
    with duckdb.connect(str(database), read_only=True) as connection:
        connection.execute("SELECT 1").fetchone()
    if journal["state"] != "rolled-back":
        set_upgrade_phase(backup, "rolled-back")
