import json
import re
import shutil
import subprocess
import threading
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from app.constants import (
    LESSON_VIDEO_TASK_STALE_HOURS,
    LESSON_VIDEO_WAIT_TIMEOUT_SECONDS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = REPO_ROOT / "media"
HTML_SOURCE_SUFFIXES = {".htm", ".html"}
PLACEHOLDER_RE = re.compile(
    r"\[placeholder\].*?Limit the topics to what's in (?P<doc>.+?)\.\".*?\[/placeholder\]",
    re.DOTALL,
)


class LessonVideoError(Exception):
    pass


@dataclass
class VideoJobState:
    status: str  # "running" | "done" | "error"
    started_at: datetime
    error: str | None = None


_JOBS: dict[str, VideoJobState] = {}
_JOBS_LOCK = threading.Lock()
_SOURCE_SYNC_LOCK = threading.Lock()
_NOTEBOOKLM_GENERATION_LOCK = threading.Lock()


def _notebooklm_profile() -> str:
    from app.config import get_settings

    profile = get_settings().notebooklm_profile.strip()
    if not profile:
        raise LessonVideoError("LEARNUP_NOTEBOOKLM_PROFILE must not be empty")
    return profile


def _notebooklm_cmd(*args: str) -> list[str]:
    return ["notebooklm", "--profile", _notebooklm_profile(), *args]


def _job_key(topic_slug: str, lesson_slug: str) -> str:
    return f"{topic_slug}:{lesson_slug}"


def find_lesson_path(topic_slug: str, lesson_slug: str) -> Path:
    matches = list(
        (REPO_ROOT / "content" / topic_slug / "lessons").rglob(f"{lesson_slug}.md")
    )
    if len(matches) != 1:
        raise LessonVideoError(
            f"Expected exactly one lesson file for slug {lesson_slug!r}, found {len(matches)}"
        )
    return matches[0]


def find_lesson_slug_by_objective(topic_slug: str, objective: str) -> str:
    matches = list(
        (REPO_ROOT / "content" / topic_slug / "lessons" / objective).glob("*.md")
    )
    if len(matches) != 1:
        raise LessonVideoError(
            f"Expected exactly one lesson file for objective {objective!r}, found {len(matches)}"
        )
    return matches[0].stem


def read_topic_name(topic_slug: str) -> str:
    syllabus_path = REPO_ROOT / "content" / topic_slug / "syllabus.yaml"
    return yaml.safe_load(syllabus_path.read_text())["topic_name"]


def read_notebooklm_output_language(topic_slug: str) -> str:
    syllabus_path = REPO_ROOT / "content" / topic_slug / "syllabus.yaml"
    syllabus = yaml.safe_load(syllabus_path.read_text())
    language = syllabus.get("notebooklm_output_language")
    if not isinstance(language, str) or not language.strip():
        raise LessonVideoError(
            f"Syllabus {syllabus_path} must declare a non-empty notebooklm_output_language"
        )
    return language.strip()


def build_video_instructions(title: str, source_document: str) -> str:
    return (
        f'Create a video titled "{title}". '
        f"Limit the topics to what's in {source_document}, and pick up to 6 topics to cover "
        "from that document."
    )


def get_job_status(topic_slug: str, lesson_slug: str) -> dict:
    key = _job_key(topic_slug, lesson_slug)
    with _JOBS_LOCK:
        job = _JOBS.get(key)
    if job is not None:
        return {"status": job.status, "error": job.error}
    video_path = MEDIA_ROOT / topic_slug / f"{lesson_slug}.mp4"
    if video_path.exists():
        return {"status": "done", "error": None}
    # No in-memory job (e.g. server restarted mid-generation) but Gemini Notebook may still be
    # working on a task we submitted earlier — surface it as running rather than idle so the
    # caller doesn't think generation was never requested.
    if _load_pending_task(topic_slug, lesson_slug) is not None:
        return {"status": "running", "error": None}
    return {"status": "idle", "error": None}


def start_generation(topic_slug: str, lesson_slug: str) -> None:
    key = _job_key(topic_slug, lesson_slug)
    with _JOBS_LOCK:
        existing = _JOBS.get(key)
        if existing is not None and existing.status == "running":
            raise LessonVideoError(
                "A generation job is already running for this lesson."
            )

    lesson_path = find_lesson_path(topic_slug, lesson_slug)
    if not PLACEHOLDER_RE.search(lesson_path.read_text()):
        raise LessonVideoError("This lesson's video is already set.")

    with _JOBS_LOCK:
        _JOBS[key] = VideoJobState(status="running", started_at=datetime.now(UTC))
    threading.Thread(
        target=_run_job, args=(topic_slug, lesson_slug), daemon=True
    ).start()


def _run_job(topic_slug: str, lesson_slug: str) -> None:
    key = _job_key(topic_slug, lesson_slug)
    try:
        generate_lesson_video(topic_slug, lesson_slug)
        with _JOBS_LOCK:
            _JOBS[key] = VideoJobState(status="done", started_at=_JOBS[key].started_at)
    except (
        Exception
    ) as exc:  # surfaced to the frontend via get_job_status, not swallowed
        print(
            f"[video] generation failed for {topic_slug}/{lesson_slug}: {exc}",
            flush=True,
        )
        traceback.print_exc()
        with _JOBS_LOCK:
            _JOBS[key] = VideoJobState(
                status="error", started_at=_JOBS[key].started_at, error=str(exc)
            )


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, text=True, capture_output=True)
    print(
        f"[video] notebooklm command exited {result.returncode}: {' '.join(cmd)}",
        flush=True,
    )
    if result.stdout.strip():
        print(f"[video] notebooklm stdout:\n{result.stdout.rstrip()}", flush=True)
    if result.stderr.strip():
        print(f"[video] notebooklm stderr:\n{result.stderr.rstrip()}", flush=True)
    if result.returncode != 0:
        output = result.stderr or result.stdout
        if "RateLimitError" in output or "Rate limited" in output:
            raise LessonVideoError(
                "Gemini Notebook's video generation is rate-limited right now. Try later."
            )
        raise LessonVideoError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n{output}"
        )
    return result


def _ensure_notebooklm_cli() -> None:
    if shutil.which("notebooklm") is None:
        raise LessonVideoError(
            "The `notebooklm` CLI isn't installed on this machine. Run `uv sync --group notebooklm` "
            "then `uv run notebooklm login`, or use the manual/ask-your-LLM alternative instead."
        )
    check = subprocess.run(
        _notebooklm_cmd("auth", "check", "--test", "--json"),
        text=True,
        capture_output=True,
    )
    print(f"[video] notebooklm auth check exited {check.returncode}", flush=True)
    if check.stdout.strip():
        print(f"[video] notebooklm auth stdout:\n{check.stdout.rstrip()}", flush=True)
    if check.stderr.strip():
        print(f"[video] notebooklm auth stderr:\n{check.stderr.rstrip()}", flush=True)
    if check.returncode != 0:
        raise LessonVideoError(
            "Not logged in to Gemini Notebook. Run `uv run notebooklm login`, then retry."
        )


def _set_notebooklm_output_language(language_code: str) -> None:
    result = _run(_notebooklm_cmd("language", "list", "--json"))
    try:
        languages = json.loads(result.stdout)["languages"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LessonVideoError(
            f"Unexpected `notebooklm language list --json` output: {result.stdout}"
        ) from exc
    if not isinstance(languages, dict) or not all(
        isinstance(code, str) and isinstance(name, str)
        for code, name in languages.items()
    ):
        raise LessonVideoError(
            f"Unexpected `notebooklm language list --json` output: {result.stdout}"
        )
    if language_code not in languages:
        supported = ", ".join(sorted(languages))
        raise LessonVideoError(
            f"NotebookLM does not support output language {language_code!r}. "
            f"Supported codes: {supported}"
        )
    _run(_notebooklm_cmd("language", "set", language_code, "--json"))
    print(
        f"[video] NotebookLM output language set to {languages[language_code]} ({language_code})",
        flush=True,
    )


def _get_or_create_notebook(topic_slug: str) -> str:
    state_file = MEDIA_ROOT / topic_slug / ".notebook.json"
    profile = _notebooklm_profile()
    if state_file.exists():
        state = json.loads(state_file.read_text())
        if state.get("profile", "default") == profile:
            return state["notebook_id"]
        print(
            f"[video] NotebookLM profile changed from {state.get('profile', 'default')} to {profile}; "
            "creating a new topic notebook",
            flush=True,
        )
    result = _run(_notebooklm_cmd("create", read_topic_name(topic_slug), "--json"))
    data = json.loads(result.stdout)
    notebook_id = (
        data.get("id") or data.get("notebook_id") or data.get("notebook", {}).get("id")
    )
    if not notebook_id:
        raise LessonVideoError(
            f"No notebook id in `notebooklm create` output: {result.stdout}"
        )
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"notebook_id": notebook_id, "profile": profile}))
    added_file = MEDIA_ROOT / topic_slug / ".sources_added.json"
    if added_file.exists():
        added_file.unlink()
    return notebook_id


def _save_added_sources(added_file: Path, added: set[str]) -> None:
    added_file.parent.mkdir(parents=True, exist_ok=True)
    pending_file = added_file.with_name(f"{added_file.name}.tmp")
    pending_file.write_text(json.dumps(sorted(added)), encoding="utf-8")
    pending_file.replace(added_file)


def _sync_sources(topic_slug: str, notebook_id: str) -> None:
    sources_dir = REPO_ROOT / "sources" / topic_slug
    added_file = MEDIA_ROOT / topic_slug / ".sources_added.json"
    with _SOURCE_SYNC_LOCK:
        added = (
            set(json.loads(added_file.read_text(encoding="utf-8")))
            if added_file.exists()
            else set()
        )
        skip = {"INTAKE.md", "SOURCES.md"}
        source_paths = [
            path
            for path in sorted(sources_dir.iterdir())
            if path.is_file() and path.name not in skip
        ]
        html_paths = [
            path for path in source_paths if path.suffix.lower() in HTML_SOURCE_SUFFIXES
        ]
        if html_paths:
            names = ", ".join(path.name for path in html_paths)
            raise LessonVideoError(
                "NotebookLM's upload endpoint does not support HTML files: "
                f"{names}. Convert each page to .txt, .md, or .pdf, move the .html/.htm "
                f"file outside sources/{topic_slug}, update SOURCES.md and any affected "
                "lesson placeholder, then retry."
            )

        for path in source_paths:
            if path.name in added:
                continue
            _run(_notebooklm_cmd("source", "add", str(path), "--notebook", notebook_id))
            added.add(path.name)
            _save_added_sources(added_file, added)


def _pending_tasks_file(topic_slug: str) -> Path:
    return MEDIA_ROOT / topic_slug / ".video_tasks.json"


def _is_stale(started_at: str) -> bool:
    age = datetime.now(UTC) - datetime.fromisoformat(started_at)
    return age > timedelta(hours=LESSON_VIDEO_TASK_STALE_HOURS)


def _load_pending_task(topic_slug: str, lesson_slug: str) -> str | None:
    tasks_file = _pending_tasks_file(topic_slug)
    if not tasks_file.exists():
        return None
    entry = json.loads(tasks_file.read_text()).get(lesson_slug)
    if entry is None:
        return None
    # `started_at` is missing for entries saved before this field existed — treat those as stale
    # too (we have no way to know their age, and the safe assumption is that anything without a
    # timestamp is old). A task this old getting reported as "running" forever is exactly the bug
    # this staleness check exists to close: the run that saved it crashed or errored without ever
    # calling `_clear_pending_task`, so the entry outlives the actual (long-finished-or-abandoned)
    # generation and makes the UI show "Generating…" indefinitely for a lesson nothing is doing.
    started_at = entry.get("started_at") if isinstance(entry, dict) else None
    if started_at is None or _is_stale(started_at):
        _clear_pending_task(topic_slug, lesson_slug)
        return None
    return entry["task_id"]


def _save_pending_task(topic_slug: str, lesson_slug: str, task_id: str) -> None:
    tasks_file = _pending_tasks_file(topic_slug)
    tasks = json.loads(tasks_file.read_text()) if tasks_file.exists() else {}
    tasks[lesson_slug] = {
        "task_id": task_id,
        "started_at": datetime.now(UTC).isoformat(),
    }
    tasks_file.parent.mkdir(parents=True, exist_ok=True)
    tasks_file.write_text(json.dumps(tasks))


def _clear_pending_task(topic_slug: str, lesson_slug: str) -> None:
    tasks_file = _pending_tasks_file(topic_slug)
    if not tasks_file.exists():
        return
    tasks = json.loads(tasks_file.read_text())
    tasks.pop(lesson_slug, None)
    tasks_file.write_text(json.dumps(tasks))


def _generate_and_download(
    topic_slug: str,
    lesson_slug: str,
    notebook_id: str,
    instructions: str,
    output_language: str,
) -> Path:
    out_path = MEDIA_ROOT / topic_slug / f"{lesson_slug}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for a task already started in a previous (possibly crashed/rebooted) run before
    # asking Gemini Notebook to generate another one — video generation eats one of a handful of
    # daily quota slots, so re-requesting on every retry would burn quota and leave duplicate
    # artifacts sitting in the notebook.
    task_id = _load_pending_task(topic_slug, lesson_slug)
    if task_id is None:
        # NotebookLM's output language is global to the selected account. Keep setting it and
        # submitting the generation request in one critical section so concurrent topics cannot
        # switch the language between these two commands.
        with _NOTEBOOKLM_GENERATION_LOCK:
            _set_notebooklm_output_language(output_language)
            result = _run(
                _notebooklm_cmd(
                    "generate",
                    "video",
                    instructions,
                    "--notebook",
                    notebook_id,
                    "--style",
                    "whiteboard",
                    "--json",
                )
            )
        task_id = json.loads(result.stdout)["task_id"]
        # Persisted immediately, before the (multi-minute) wait below — so a killed process or
        # a reboot mid-wait doesn't lose track of a generation that's already in flight server-side.
        _save_pending_task(topic_slug, lesson_slug, task_id)

    wait_result = _run(
        _notebooklm_cmd(
            "artifact",
            "wait",
            task_id,
            "--notebook",
            notebook_id,
            "--timeout",
            str(LESSON_VIDEO_WAIT_TIMEOUT_SECONDS),
        )
    )
    if re.search(
        r"^Status:\s*failed\s*$", wait_result.stdout, re.IGNORECASE | re.MULTILINE
    ):
        _clear_pending_task(topic_slug, lesson_slug)
        raise LessonVideoError(
            f"NotebookLM video artifact failed (task {task_id}). "
            "Check the NotebookLM notebook for the provider-side failure details."
        )
    _run(
        _notebooklm_cmd(
            "download",
            "video",
            str(out_path),
            "--notebook",
            notebook_id,
            "--artifact",
            task_id,
            "--force",
        )
    )
    if not out_path.exists():
        raise LessonVideoError(
            "Download reported success but the output file is missing."
        )
    _clear_pending_task(topic_slug, lesson_slug)
    return out_path


def generate_lesson_video(topic_slug: str, lesson_slug: str) -> Path:
    lesson_path = find_lesson_path(topic_slug, lesson_slug)
    text = lesson_path.read_text()
    match = PLACEHOLDER_RE.search(text)
    if not match:
        raise LessonVideoError("This lesson's video is already set.")

    # Lazy: app.db opens a DuckDB connection at import time (single-writer), so only pull it in
    # once we're actually about to write — not on every import of this module (--dry-run etc).
    from app.content.seed import load_lesson_file, split_why_it_matters
    from app.db import SessionLocal
    from app.models import Lesson
    from sqlalchemy import select

    frontmatter, _ = load_lesson_file(lesson_path)
    title = frontmatter.get("title", lesson_slug)
    instructions = build_video_instructions(title, match.group("doc"))
    output_language = read_notebooklm_output_language(topic_slug)
    print(
        f"[video] Gemini Notebook prompt for {topic_slug}/{lesson_slug}: {instructions}"
    )

    _ensure_notebooklm_cli()
    notebook_id = _get_or_create_notebook(topic_slug)
    _sync_sources(topic_slug, notebook_id)
    video_path = _generate_and_download(
        topic_slug, lesson_slug, notebook_id, instructions, output_language
    )

    link = f"[Watch the video summary](/media/{topic_slug}/{lesson_slug}.mp4)"
    lesson_path.write_text(PLACEHOLDER_RE.sub(link, text, count=1))

    _, body = load_lesson_file(lesson_path)
    main_body, why = split_why_it_matters(body)
    with SessionLocal() as session:
        lesson = session.execute(
            select(Lesson).where(Lesson.slug == lesson_slug)
        ).scalar_one()
        lesson.body_markdown = main_body
        lesson.why_it_matters_markdown = why
        session.commit()

    return video_path
