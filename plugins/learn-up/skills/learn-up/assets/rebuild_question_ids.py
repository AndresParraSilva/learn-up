from __future__ import annotations

import re
import tempfile
from pathlib import Path


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def rebuild_question_ids(source: Path, destination: Path, mappings: list) -> None:
    """Build and verify a separate DuckDB file. Caller owns backup, shutdown and swap."""
    import duckdb

    if not source.is_file() or source.is_symlink():
        raise ValueError(f"Source must be a regular database: {source}")
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Destination already exists: {destination}")
    if Path(str(source) + ".wal").exists():
        raise ValueError(
            "Checkpoint and close all writers before rebuilding a database with a WAL"
        )
    try:
        with duckdb.connect(str(source), read_only=True) as old:
            changes = _resolve_mappings(old, mappings)
            with tempfile.TemporaryDirectory(prefix="learnup-db-rebuild-") as directory:
                export = Path(directory) / "export"
                old.execute(f"EXPORT DATABASE {_literal(str(export))} (FORMAT PARQUET)")
                # Use DuckDB's own dependency-ordered schema and load statements.
                for table, replacements in changes.items():
                    parquet = export / f"learn_{table}.parquet"
                    if not parquet.is_file():
                        raise ValueError(f"Expected export file missing: {parquet}")
                    with duckdb.connect() as scratch:
                        scratch.execute(
                            f"CREATE TABLE data AS SELECT * FROM read_parquet({_literal(str(parquet))})"
                        )
                        scratch.executemany(
                            "UPDATE data SET external_id = ? WHERE id = ?",
                            [(new, pk) for pk, new in replacements.items()],
                        )
                        scratch.execute(
                            f"COPY data TO {_literal(str(parquet))} (FORMAT PARQUET)"
                        )
                with duckdb.connect(str(destination)) as new:
                    new.execute(f"IMPORT DATABASE {_literal(str(export))}")
                    _verify_rows(old, new, changes)
                    for query in (
                        "SELECT schema_name, table_name, sql FROM duckdb_tables() WHERE NOT internal ORDER BY 1, 2",
                        "SELECT schema_name, index_name, sql FROM duckdb_indexes() ORDER BY 1, 2",
                        "SELECT schema_name, view_name, sql FROM duckdb_views() WHERE NOT internal ORDER BY 1, 2",
                        "SELECT schema_name, sequence_name, sql FROM duckdb_sequences() ORDER BY 1, 2",
                    ):
                        if (
                            old.execute(query).fetchall()
                            != new.execute(query).fetchall()
                        ):
                            raise ValueError(
                                f"Rebuilt database metadata differs: {query}"
                            )
                    new.execute("CHECKPOINT")
    except BaseException:
        destination.unlink(missing_ok=True)
        Path(str(destination) + ".wal").unlink(missing_ok=True)
        raise


def _resolve_mappings(connection, mappings: list) -> dict[str, dict[int, str]]:
    inventory = {}
    for kind, join in (
        (
            "question",
            "JOIN learn.objective o ON o.id = q.objective_id JOIN learn.domain d ON d.id = o.domain_id JOIN learn.topic t ON t.id = d.topic_id",
        ),
        ("strategy_question", "JOIN learn.topic t ON t.id = q.topic_id"),
    ):
        inventory[kind] = connection.execute(
            f"SELECT q.id, q.external_id, t.slug FROM learn.{kind} q {join}"
        ).fetchall()
    changes: dict[str, dict[int, str]] = {}
    seen = set()
    for item in mappings:
        if item.kind not in inventory or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", item.topic_slug
        ):
            raise ValueError(f"Invalid mapping kind or topic: {item}")
        key = (item.kind, item.topic_slug, item.old_id)
        if (
            key in seen
            or item.old_id.startswith(item.topic_slug + "-")
            or item.new_id != item.topic_slug + "-" + item.old_id
        ):
            raise ValueError(f"Duplicate or invalid migration mapping: {item}")
        seen.add(key)
        matches = [
            (pk, value)
            for pk, value, slug in inventory[item.kind]
            if slug == item.topic_slug and value == item.old_id
        ]
        if len(matches) != 1:
            raise ValueError(f"Missing or stale database mapping: {item}")
        if any(value == item.new_id for _, value, _ in inventory[item.kind]):
            raise ValueError(f"Database id collision: {item.new_id}")
        changes.setdefault(item.kind, {})[matches[0][0]] = item.new_id
    for kind, replacements in changes.items():
        if len(set(replacements.values())) != len(replacements):
            raise ValueError(f"Duplicate proposed ids for {kind}")
    return changes


def _verify_rows(old, new, changes: dict[str, dict[int, str]]) -> None:
    for schema, table in old.execute(
        "SELECT schema_name, table_name FROM duckdb_tables() WHERE NOT internal ORDER BY 1, 2"
    ).fetchall():
        name = f"{_identifier(schema)}.{_identifier(table)}"
        cursor = old.execute(f"SELECT * FROM {name}")
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        if schema == "learn" and table in changes:
            external = columns.index("external_id")
            primary = columns.index("id")
            rows = [
                tuple(
                    changes[table].get(row[primary], value)
                    if index == external
                    else value
                    for index, value in enumerate(row)
                )
                for row in rows
            ]
        if sorted(rows, key=repr) != sorted(
            new.execute(f"SELECT * FROM {name}").fetchall(), key=repr
        ):
            raise ValueError(f"Rebuilt database rows differ: {name}")
