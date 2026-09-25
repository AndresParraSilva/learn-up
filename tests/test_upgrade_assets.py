from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/learn-up/assets"))
from upgrade_assets import (  # noqa: E402
    AssetDecision,
    UpgradeAssetConflict,
    inspect_asset,
    preflight_asset_decisions,
)


def test_unknown_baseline_requires_review_and_compatible_retention_is_recorded(
    tmp_path,
):
    canonical = tmp_path / "canonical"
    installed = tmp_path / "installed"
    canonical.write_text("new version")
    installed.write_text("local adaptation")
    status = inspect_asset("frontend/src/app.tsx", canonical, installed, None)
    assert status.change == "unknown-baseline"
    with pytest.raises(UpgradeAssetConflict, match="decisions"):
        preflight_asset_decisions([status], {})
    replaced, retained = preflight_asset_decisions(
        [status], {status.path: AssetDecision("keep", True, "preserves local shortcut")}
    )
    assert replaced == []
    assert retained == {status.path: "preserves local shortcut"}


@pytest.mark.parametrize(
    "compatible,reason", [(False, "breaks next"), (None, "not checked"), (True, "")]
)
def test_incompatible_or_unresolved_retention_stops_before_mutation(
    tmp_path, compatible, reason
):
    canonical = tmp_path / "canonical"
    installed = tmp_path / "installed"
    canonical.write_text("new contract")
    installed.write_text("old contract")
    status = inspect_asset("CompletionFooter.tsx", canonical, installed, None)
    before = installed.read_bytes()
    with pytest.raises(UpgradeAssetConflict, match="Cannot retain"):
        preflight_asset_decisions(
            [status], {status.path: AssetDecision("keep", compatible, reason)}
        )
    assert installed.read_bytes() == before


def test_baseline_distinguishes_upstream_from_local_changes(tmp_path):
    canonical = tmp_path / "canonical"
    installed = tmp_path / "installed"
    canonical.write_text("baseline")
    installed.write_text("baseline")
    baseline = inspect_asset("asset.py", canonical, installed, None).canonical_sha256
    canonical.write_text("new upstream")
    assert (
        inspect_asset("asset.py", canonical, installed, baseline).change
        == "upstream-only"
    )
    canonical.write_text("baseline")
    installed.write_text("local")
    assert (
        inspect_asset("asset.py", canonical, installed, baseline).change == "local-only"
    )
    canonical.write_text("new upstream")
    assert (
        inspect_asset("asset.py", canonical, installed, baseline).change
        == "both-changed"
    )
