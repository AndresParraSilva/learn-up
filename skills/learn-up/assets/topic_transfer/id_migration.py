from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml
from yaml.events import AliasEvent, NodeEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from .types import IdMigration, TopicTransferError, validate_topic_slug


@dataclass(frozen=True, slots=True)
class IdRewrite:
    path: str
    before: bytes
    after: bytes


def _mapping(node: Node) -> dict[str, Node]:
    if not isinstance(node, MappingNode):
        raise TopicTransferError("Expected a YAML mapping")
    result: dict[str, Node] = {}
    for key, value in node.value:
        if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
            raise TopicTransferError("YAML mapping keys must be strings")
        if key.value in result:
            raise TopicTransferError(f"Duplicate YAML mapping key: {key.value}")
        result[key.value] = value
    return result


def _check_tree(node: Node) -> None:
    if isinstance(node, MappingNode):
        for value in _mapping(node).values():
            _check_tree(value)
    elif isinstance(node, SequenceNode):
        for value in node.value:
            _check_tree(value)
    elif not isinstance(node, ScalarNode):
        raise TopicTransferError("Unsupported YAML node")


def _id(node: Node) -> str:
    if (
        not isinstance(node, ScalarNode)
        or node.tag != "tag:yaml.org,2002:str"
        or not node.value
        or any(char.isspace() for char in node.value)
        or node.style in ("|", ">")
    ):
        raise TopicTransferError(
            "Question ids must be nonempty, single-line string scalars"
        )
    return node.value


def _parse(data: bytes) -> tuple[str, Node, object]:
    try:
        text = data.decode("utf-8")
        for event in yaml.parse(text):
            if isinstance(event, AliasEvent) or (
                isinstance(event, NodeEvent) and event.anchor is not None
            ):
                raise TopicTransferError("YAML aliases and anchors are unsupported")
        node = yaml.compose(text)
        if node is None:
            raise TopicTransferError("Empty question or mock YAML")
        _check_tree(node)
        return text, node, yaml.safe_load(text)
    except (UnicodeError, yaml.YAMLError) as exc:
        raise TopicTransferError(f"Invalid migration YAML: {exc}") from exc


def plan_id_migration(
    files: dict[str, bytes], topic_slug: str
) -> tuple[list[IdRewrite], list[IdMigration]]:
    """Plan scalar-only edits to a topic-relative content inventory without writing."""
    slug = validate_topic_slug(topic_slug)
    parsed = {}
    known: dict[str, dict[str, str]] = {"question": {}, "strategy_question": {}}
    mappings: list[IdMigration] = []
    edits: dict[str, list[tuple[Node, str]]] = {}
    expected = {}
    all_ids: set[str] = set()
    for path, data in sorted(files.items()):
        parts = PurePosixPath(path).parts
        if not parts or ".." in parts or PurePosixPath(path).is_absolute():
            raise TopicTransferError(f"Unsafe migration path: {path}")
        kind = (
            "question"
            if parts[0] == "questions" and path.endswith(".yaml")
            else "strategy_question"
            if path == "strategy/questions.yaml"
            else "mock"
            if parts[0] == "mocks" and path.endswith(".yaml")
            else None
        )
        if kind is None:
            continue
        text, node, value = _parse(data)
        fields = _mapping(node)
        field = "questions"
        items = fields.get(field)
        if not isinstance(items, SequenceNode):
            raise TopicTransferError(f"{path}: {field} must be a list")
        parsed[path] = (text, items, kind)
        expected[path] = copy.deepcopy(value)
        edits[path] = []
        if kind == "mock":
            continue
        for index, item in enumerate(items.value):
            scalar = _mapping(item).get("external_id")
            old = _id(scalar)
            new = old if old.startswith(slug + "-") else slug + "-" + old
            if old in known[kind] or new in all_ids:
                raise TopicTransferError(f"Question id collision: {new}")
            known[kind][old] = new
            all_ids.add(new)
            if old != new:
                mappings.append(IdMigration(slug, kind, path, old, new))
                edits[path].append((scalar, new))
                expected[path]["questions"][index]["external_id"] = new
    for path, (_, items, kind) in parsed.items():
        if kind != "mock":
            continue
        for index, scalar in enumerate(items.value):
            old = _id(scalar)
            if old not in known["question"]:
                raise TopicTransferError(
                    f"{path}: mock references unknown question id {old}"
                )
            new = known["question"][old]
            if old != new:
                edits[path].append((scalar, new))
                expected[path]["questions"][index] = new
    rewrites = []
    for path, changes in edits.items():
        text = parsed[path][0]
        for node, new in sorted(
            changes, key=lambda item: item[0].start_mark.index, reverse=True
        ):
            if node.style == "'":
                replacement = "'" + new.replace("'", "''") + "'"
            elif node.style == '"':
                replacement = json.dumps(new, ensure_ascii=False)
            else:
                replacement = new
            text = (
                text[: node.start_mark.index]
                + replacement
                + text[node.end_mark.index :]
            )
        after = text.encode("utf-8")
        if _parse(after)[2] != expected[path]:
            raise TopicTransferError(f"{path}: migration changed data beyond ids")
        if after != files[path]:
            rewrites.append(IdRewrite(path, files[path], after))
    return rewrites, mappings


def topic_id_files(topic_path: Path) -> dict[str, bytes]:
    files = {}
    for path in sorted(topic_path.rglob("*")):
        if path.is_symlink():
            raise TopicTransferError(f"Migration refuses symlink: {path}")
        if path.is_file() and path.suffix == ".yaml":
            files[path.relative_to(topic_path).as_posix()] = path.read_bytes()
    return files


def migrate_topic_ids(topic_path: Path, topic_slug: str) -> list[IdMigration]:
    """Apply a fully preflighted plan to a staging tree (never a live app)."""
    rewrites, mappings = plan_id_migration(topic_id_files(topic_path), topic_slug)
    for rewrite in rewrites:
        (topic_path / rewrite.path).write_bytes(rewrite.after)
    return mappings


def validate_destination_ids(content_root: Path, staged_topic: Path, slug: str) -> None:
    """Reject legacy live ids and collisions across the complete candidate content."""
    seen: set[str] = set()
    for topic in sorted(content_root.iterdir()) if content_root.exists() else []:
        if not topic.is_dir():
            continue
        _, migrations = plan_id_migration(topic_id_files(topic), topic.name)
        if migrations:
            raise TopicTransferError(
                "Destination has legacy ids; complete the app upgrade before import"
            )
    topics = (
        [p for p in content_root.iterdir() if p.is_dir() and p.name != slug]
        if content_root.exists()
        else []
    )
    for topic in [*topics, staged_topic]:
        files = topic_id_files(topic)
        plan_id_migration(files, topic.name)
        for path, data in files.items():
            if path.startswith("questions/") or path == "strategy/questions.yaml":
                for question in yaml.safe_load(data)["questions"]:
                    external_id = question["external_id"]
                    if external_id in seen:
                        raise TopicTransferError(
                            f"Destination question id collision: {external_id}"
                        )
                    seen.add(external_id)
