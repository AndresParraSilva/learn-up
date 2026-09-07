#!/usr/bin/env python3
"""Exercise Git marketplace install/update in a disposable, unauthenticated Codex profile."""

from __future__ import annotations

import functools
import http.server
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed: {args!r}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def verify_discovery(base: Path, env: dict[str, str], installed: Path) -> None:
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("codex is required")
    process = subprocess.Popen(
        [executable, "app-server", "--stdio"],
        cwd=base,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    messages: queue.Queue = queue.Queue()

    def read() -> None:
        for line in process.stdout:
            messages.put(json.loads(line))

    threading.Thread(target=read, daemon=True).start()

    def request(identifier: int, method: str, params: dict) -> dict:
        process.stdin.write(
            json.dumps({"id": identifier, "method": method, "params": params}) + "\n"
        )
        process.stdin.flush()
        while True:
            message = messages.get(timeout=30)
            if message.get("id") == identifier:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]

    try:
        request(
            1,
            "initialize",
            {
                "clientInfo": {"name": "learn-up-smoke", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
        result = request(2, "skills/list", {"cwds": [str(base)], "forceReload": True})
        entry = result["data"][0]
        assert not entry["errors"], entry["errors"]
        skills = [
            skill
            for skill in entry["skills"]
            if skill.get("pluginId") == "learn-up@learn-up"
        ]
        assert len(skills) == 1 and skills[0]["enabled"], skills
        assert (
            Path(skills[0]["path"]).resolve()
            == (installed / "skills/learn-up/SKILL.md").resolve()
        )
    finally:
        if os.name == "nt":
            run(["taskkill", "/PID", str(process.pid), "/T", "/F"], base)
        else:
            process.terminate()
        process.wait(timeout=10)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def smoke(base: Path) -> None:
    source = base / "source"
    source.mkdir()
    profile = base / "profile"
    profile.mkdir()
    home = base / "home"
    home.mkdir()
    env = {
        **os.environ,
        "CODEX_HOME": str(profile),
        "HOME": str(home),
        "USERPROFILE": str(home),
    }
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("Install Codex CLI before running the smoke test")

    def git(*args: str, cwd: Path = source) -> None:
        run(["git", *args], cwd)

    def codex(*args: str) -> dict:
        return json.loads(run([executable, "plugin", *args, "--json"], base, env))

    for name in (".agents", "plugins"):
        shutil.copytree(ROOT / name, source / name)
    git("init", "-b", "main")
    git("config", "user.name", "Smoke Test")
    git("config", "user.email", "smoke@example.invalid")
    manifest = source / "plugins/learn-up/.codex-plugin/plugin.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    marker = source / "plugins/learn-up/skills/learn-up/smoke-marker.txt"
    data["version"] = "0.4.0-test.1"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    marker.write_text("A", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "version A")
    bare = base / "market.git"
    git("clone", "--bare", str(source), str(bare))
    git("update-server-info", cwd=bare)
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(base))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        codex(
            "marketplace",
            "add",
            f"http://127.0.0.1:{server.server_port}/market.git",
            "--ref",
            "main",
        )
        for version, content in (("0.4.0-test.1", "A"), ("0.4.0-test.2", "B")):
            if content == "B":
                data["version"] = version
                manifest.write_text(json.dumps(data), encoding="utf-8")
                marker.write_text(content, encoding="utf-8")
                git("add", ".")
                git("commit", "-m", "version B")
                git("push", str(bare), "main")
                git("update-server-info", cwd=bare)
                assert not codex("marketplace", "upgrade", "learn-up")["errors"]
            result = codex("add", "learn-up@learn-up")
            assert result["version"] == version, result
            installed = Path(result["installedPath"])
            assert (
                installed / "skills/learn-up/smoke-marker.txt"
            ).read_text() == content
            listed = codex("list", "--marketplace", "learn-up")["installed"]
            assert (
                len(listed) == 1
                and listed[0]["enabled"]
                and listed[0]["version"] == version
            ), listed
            verify_discovery(base, env, installed)
            print(f"Git install and fresh-process skill discovery passed: {version}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="learn-up-marketplace-") as directory:
        smoke(Path(directory).resolve())
