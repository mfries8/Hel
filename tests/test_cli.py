"""Tests for the ``hel`` command and ``hel.load``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import hel
from hel.cli import main

GOLDEN = Path(hel.__file__).parent / "golden"


def test_load_upgrades_and_validates_a_legacy_file() -> None:
    loaded = hel.load(GOLDEN / "legacy" / "event_terminus.json")
    assert loaded.contract == "hel.event"
    assert loaded.upgrade.changed
    assert loaded.document.contract_version == "1.0"


def test_validate_reports_ok_legacy_and_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"contract": "hel.event", "contract_version": "1.0"}', encoding="utf-8")
    notjson = tmp_path / "broken.json"
    notjson.write_text("{", encoding="utf-8")
    extra = tmp_path / "extra.json"
    data = json.loads((GOLDEN / "current" / "event_minimal.json").read_text(encoding="utf-8"))
    data["surprise"] = 1
    extra.write_text(json.dumps(data), encoding="utf-8")

    status = main(
        [
            "validate",
            str(GOLDEN / "current" / "radar_full.json"),
            str(GOLDEN / "legacy" / "radar_legacy_oldest.json"),
            str(extra),
            str(bad),
            str(notjson),
        ]
    )

    out = capsys.readouterr().out
    assert status == 1
    assert "OK   " in out and "radar_full.json: hel.radar 1.1" in out
    assert "legacy layout 'legacy_oldest'" in out
    assert "unknown field kept: (top level): 'surprise'" in out
    assert out.count("FAIL") == 2


def test_validate_all_good_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(GOLDEN / "current" / "event_full.json")]) == 0
    assert "OK" in capsys.readouterr().out


def test_upgrade_writes_a_new_file_with_the_upgrader_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "event.json"
    shutil.copy(GOLDEN / "legacy" / "event_labels.json", source)
    out = tmp_path / "event_v1.json"

    assert main(["upgrade", str(source), "--out", str(out)]) == 0

    expected = json.loads((GOLDEN / "upgraded" / "event_labels.json").read_text(encoding="utf-8"))
    assert json.loads(out.read_text(encoding="utf-8")) == expected
    assert "became 'entry_speed_mps'" in capsys.readouterr().out
    # The original is untouched.
    assert source.read_bytes() == (GOLDEN / "legacy" / "event_labels.json").read_bytes()


def test_upgrade_refuses_to_overwrite(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "event.json"
    shutil.copy(GOLDEN / "legacy" / "event_labels.json", source)
    assert main(["upgrade", str(source), "--out", str(source)]) == 1
    existing = tmp_path / "existing.json"
    existing.write_text("{}", encoding="utf-8")
    assert main(["upgrade", str(source), "--out", str(existing)]) == 1
    assert existing.read_text(encoding="utf-8") == "{}"
    assert main(["upgrade", str(source), "--out", str(existing), "--force"]) == 0
    assert "never overwrites its input" in capsys.readouterr().out


def test_upgrade_reports_already_current_and_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "copy.json"
    assert main(["upgrade", str(GOLDEN / "current" / "event_full.json"), "--out", str(out)]) == 0
    assert "already current" in capsys.readouterr().out
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    assert main(["upgrade", str(bad), "--out", str(tmp_path / "x.json")]) == 1


def test_versions_lists_every_contract(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["versions"]) == 0
    out = capsys.readouterr().out
    for contract, version in hel.CONTRACT_VERSIONS.items():
        assert f"{contract} {version}" in out
