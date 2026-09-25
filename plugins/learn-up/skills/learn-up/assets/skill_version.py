from __future__ import annotations

import re


def parse_skill_version(value: object) -> tuple[int, int, int]:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value)
        is None
    ):
        raise ValueError(f"Skill version must be MAJOR.MINOR.PATCH, got {value!r}")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)
