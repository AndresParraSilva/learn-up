from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


class UpgradeAssetConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AssetStatus:
    path: str
    canonical_sha256: str
    installed_sha256: str | None
    baseline_sha256: str | None
    change: str


@dataclass(frozen=True, slots=True)
class AssetDecision:
    action: str
    compatible: bool | None = None
    reason: str = ""


def _sha256(path: Path) -> str | None:
    if path.is_symlink():
        raise UpgradeAssetConflict(f"Asset is a symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise UpgradeAssetConflict(f"Asset is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_asset(
    relative_path: str, canonical: Path, installed: Path, baseline_sha256: str | None
) -> AssetStatus:
    if (
        not relative_path
        or Path(relative_path).is_absolute()
        or ".." in Path(relative_path).parts
    ):
        raise UpgradeAssetConflict(f"Unsafe asset path: {relative_path}")
    source_hash = _sha256(canonical)
    if source_hash is None:
        raise UpgradeAssetConflict(f"Canonical asset missing: {canonical}")
    installed_hash = _sha256(installed)
    if baseline_sha256 is not None and (
        len(baseline_sha256) != 64
        or any(c not in "0123456789abcdef" for c in baseline_sha256)
    ):
        raise UpgradeAssetConflict(f"Malformed baseline hash for {relative_path}")
    if installed_hash == source_hash:
        change = "current"
    elif baseline_sha256 is None:
        change = "unknown-baseline"
    elif installed_hash == baseline_sha256:
        change = "upstream-only"
    elif source_hash == baseline_sha256:
        change = "local-only"
    else:
        change = "both-changed"
    return AssetStatus(
        relative_path, source_hash, installed_hash, baseline_sha256, change
    )


def preflight_asset_decisions(
    statuses: list[AssetStatus], decisions: dict[str, AssetDecision]
) -> tuple[list[str], dict[str, str]]:
    """Reject unresolved/incompatible retention before any file copy or version bump."""
    expected = {item.path for item in statuses if item.change != "current"}
    if set(decisions) != expected:
        raise UpgradeAssetConflict(
            f"Asset decisions do not match changed paths: missing={sorted(expected - decisions.keys())}, extra={sorted(decisions.keys() - expected)}"
        )
    replaced: list[str] = []
    retained: dict[str, str] = {}
    for status in statuses:
        if status.path not in expected:
            continue
        decision = decisions[status.path]
        if decision.action == "replace":
            replaced.append(status.path)
        elif (
            decision.action == "keep"
            and decision.compatible is True
            and decision.reason.strip()
        ):
            retained[status.path] = decision.reason.strip()
        elif decision.action == "keep":
            raise UpgradeAssetConflict(
                f"Cannot retain incompatible or unresolved asset {status.path}"
            )
        else:
            raise UpgradeAssetConflict(f"Unknown asset decision for {status.path}")
    return replaced, retained
