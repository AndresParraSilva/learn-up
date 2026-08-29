from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ASSET = REPO_ROOT / "skills/learn-up/assets/lesson_video_service.py"


@pytest.fixture
def lesson_video_service(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    app_module = ModuleType("app")
    app_module.__path__ = []
    constants_module = ModuleType("app.constants")
    constants_module.LESSON_VIDEO_TASK_STALE_HOURS = 12
    constants_module.LESSON_VIDEO_WAIT_TIMEOUT_SECONDS = 1800
    monkeypatch.setitem(sys.modules, "app", app_module)
    monkeypatch.setitem(sys.modules, "app.constants", constants_module)

    module_name = "lesson_video_service_asset_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_ASSET)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def prepare_sources(
    module: ModuleType, tmp_path: Path, filenames: tuple[str, ...]
) -> Path:
    module.REPO_ROOT = tmp_path
    module.MEDIA_ROOT = tmp_path / "media"
    sources_dir = tmp_path / "sources" / "sample-topic"
    sources_dir.mkdir(parents=True)
    for filename in filenames:
        (sources_dir / filename).write_text(f"Source: {filename}", encoding="utf-8")
    return module.MEDIA_ROOT / "sample-topic" / ".sources_added.json"


def test_sync_sources_rejects_html_before_any_upload(
    lesson_video_service: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_sources(
        lesson_video_service,
        tmp_path,
        ("01-supported.md", "02-unsupported.HTML"),
    )
    commands: list[list[str]] = []
    monkeypatch.setattr(
        lesson_video_service, "_notebooklm_cmd", lambda *args: list(args)
    )
    monkeypatch.setattr(lesson_video_service, "_run", commands.append)

    with pytest.raises(
        lesson_video_service.LessonVideoError,
        match=r"Convert each page to \.txt, \.md, or \.pdf",
    ):
        lesson_video_service._sync_sources("sample-topic", "notebook-id")

    assert commands == []


def test_sync_sources_resumes_after_partial_failure(
    lesson_video_service: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    added_file = prepare_sources(
        lesson_video_service,
        tmp_path,
        ("01-first.md", "02-fails-once.pdf", "03-last.txt"),
    )
    attempts: list[str] = []
    failure_pending = True

    monkeypatch.setattr(
        lesson_video_service, "_notebooklm_cmd", lambda *args: list(args)
    )

    def run_with_one_failure(command: list[str]) -> None:
        nonlocal failure_pending
        source_name = Path(command[2]).name
        attempts.append(source_name)
        if source_name == "02-fails-once.pdf" and failure_pending:
            failure_pending = False
            raise lesson_video_service.LessonVideoError("simulated upload failure")

    monkeypatch.setattr(lesson_video_service, "_run", run_with_one_failure)

    with pytest.raises(
        lesson_video_service.LessonVideoError, match="simulated upload failure"
    ):
        lesson_video_service._sync_sources("sample-topic", "notebook-id")

    assert json.loads(added_file.read_text(encoding="utf-8")) == ["01-first.md"]

    lesson_video_service._sync_sources("sample-topic", "notebook-id")

    assert attempts == [
        "01-first.md",
        "02-fails-once.pdf",
        "02-fails-once.pdf",
        "03-last.txt",
    ]
    assert json.loads(added_file.read_text(encoding="utf-8")) == [
        "01-first.md",
        "02-fails-once.pdf",
        "03-last.txt",
    ]
