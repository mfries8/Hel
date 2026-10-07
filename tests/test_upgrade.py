"""Tests for the upgrader: legacy layouts become valid current files."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import hel
from hel import NotAContractFileError
from hel.upgrade import upgrade_event, upgrade_radar, upgrade_seismo

GOLDEN = Path(hel.__file__).parent / "golden"
LEGACY_NAMES = sorted(p.name for p in (GOLDEN / "legacy").glob("*.json"))


def _read(group: str, name: str) -> Any:
    return json.loads((GOLDEN / group / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", LEGACY_NAMES)
def test_each_legacy_sample_upgrades_to_exactly_its_expected_file(name: str) -> None:
    legacy = _read("legacy", name)
    before = copy.deepcopy(legacy)
    loaded = hel.upgrade_and_validate(legacy)
    assert loaded.upgrade.document == _read("upgraded", name)
    assert loaded.warnings == []
    assert legacy == before  # the input is never changed


@pytest.mark.parametrize("name", LEGACY_NAMES)
def test_upgrading_twice_changes_nothing_more(name: str) -> None:
    once = hel.upgrade(_read("legacy", name))
    twice = hel.upgrade(once.document)
    assert twice.layout == "current"
    assert not twice.changed
    assert twice.document == once.document


def test_legacy_samples_cover_every_layout() -> None:
    layouts = {
        (r.contract, r.layout) for r in (hel.upgrade(_read("legacy", n)) for n in LEGACY_NAMES)
    }
    expected = {
        (c, layout) for c, names in hel.upgrade.__globals__["LAYOUTS"].items() for layout in names
    }
    assert expected <= layouts


def test_every_upgraded_file_has_a_legacy_source() -> None:
    upgraded = sorted(p.name for p in (GOLDEN / "upgraded").glob("*.json"))
    assert upgraded == LEGACY_NAMES


# --- event ------------------------------------------------------------------------


def test_event_terminus_and_speed_are_renamed_and_time_assumed_utc() -> None:
    result = upgrade_event(_read("legacy", "event_terminus.json"))
    end = result.document["luminous_end"]
    assert "terminus" not in result.document
    assert "speed_mps" not in end and end["terminus_speed_mps"] > 0
    assert end["time_utc"].endswith("Z")
    assert any("treated as UTC" in c for c in result.changes)
    assert list(result.document)[:2] == ["contract", "contract_version"]


def test_event_finds_become_kilograms() -> None:
    legacy = _read("legacy", "event_terminus.json")
    result = upgrade_event(legacy)
    assert [f["mass_kg"] for f in result.document["finds"]] == [
        f["mass_g"] / 1000.0 for f in legacy["finds"]
    ]


def test_event_spreadsheet_labels_are_converted_with_units() -> None:
    result = upgrade_event(_read("legacy", "event_labels.json"))
    doc = result.document
    assert doc["entry_speed_mps"] == 14000.0  # 14 km/s
    assert doc["meteorite_properties"]["toughness_index"] > 0
    assert not any("(" in key for key in doc)  # no labels left


def test_event_offset_times_are_converted_to_utc() -> None:
    legacy = _read("legacy", "event_luminous_end.json")
    legacy["luminous_end"]["time_utc"] = "1998-03-22T19:36:00-05:00"
    result = upgrade_event(legacy)
    assert result.document["luminous_end"]["time_utc"] == "1998-03-23T00:36:00Z"
    assert any("converted" in c for c in result.changes)


def test_event_start_and_trajectory_are_upgraded() -> None:
    legacy = _read("legacy", "event_luminous_end.json")
    legacy["luminous_start"] = {
        "time_utc": "1998-03-23T00:35:56",
        "lat": 31.4,
        "lon": -102.7,
        "altitude_m": 80000.0,
        "speed_mps": 15000.0,
    }
    legacy["luminous_trajectory"] = [
        {"time_utc": "1998-03-23T00:35:58", "lat": 31.45, "lon": -102.75, "altitude_m": 50000.0}
    ]
    loaded = hel.upgrade_and_validate(legacy)
    doc = loaded.upgrade.document
    assert doc["luminous_start"]["entry_speed_mps"] == 15000.0
    assert doc["luminous_trajectory"][0]["time_utc"].endswith("Z")


def test_event_keeps_and_reports_unknown_fields() -> None:
    legacy = _read("legacy", "event_luminous_end.json")
    legacy["observer_notes"] = "bright flash"
    loaded = hel.upgrade_and_validate(legacy)
    assert loaded.upgrade.document["observer_notes"] == "bright flash"
    assert "event: kept unrecognized field 'observer_notes'" in loaded.upgrade.changes
    assert loaded.warnings == ["(top level): 'observer_notes'"]


def test_event_conflicts_are_kept_not_overwritten() -> None:
    legacy = _read("legacy", "event_labels.json")
    legacy["meteorite_properties"] = {"density_kg_m3": 3000.0}
    legacy["entry_speed_mps"] = 12000.0
    result = upgrade_event(legacy)
    doc = result.document
    assert doc["meteorite_properties"]["density_kg_m3"] == 3000.0
    assert doc["Meteorite Density (kg/m^3)"] == legacy["Meteorite Density (kg/m^3)"]
    assert doc["entry_speed_mps"] == 12000.0
    assert any("already present" in c for c in result.changes)


def test_event_cosmic_velocity_kept_when_entry_speed_exists() -> None:
    legacy = _read("legacy", "event_luminous_end.json")
    legacy["entry_speed_mps"] = 15500.0
    doc = upgrade_event(legacy).document
    assert doc["entry_speed_mps"] == 15500.0
    assert doc["cosmic_velocity_kms"] == legacy["cosmic_velocity_kms"]


def test_event_rename_drops_exact_duplicates() -> None:
    legacy = _read("legacy", "event_luminous_end.json")
    legacy["radar_duration_s"] = legacy["radar_duration_seconds"]
    result = upgrade_event(legacy)
    assert "radar_duration_seconds" not in result.document
    assert any("duplicate" in c for c in result.changes)


def test_event_with_both_terminus_blocks_is_refused() -> None:
    legacy = _read("legacy", "event_terminus.json")
    legacy["luminous_end"] = legacy["terminus"]
    with pytest.raises(NotAContractFileError, match="both"):
        upgrade_event(legacy)


def test_event_without_terminus_object_is_refused() -> None:
    with pytest.raises(NotAContractFileError, match="luminous_end"):
        upgrade_event({"event_id": "x", "luminous_end": "not an object"})


# --- radar ------------------------------------------------------------------------


def test_radar_legacy_renames_products_and_drops_display_fields() -> None:
    result = upgrade_radar(_read("legacy", "radar_legacy.json"))
    pixels = [p for s in result.document["sweeps"] for p in s["pixels"]]
    assert not any("sweep_desc" in p or "source_file" in p for p in pixels)
    assert not any(alias in p for p in pixels for alias in hel.radar.PRODUCT_ALIASES)
    assert any("correlation_coefficient" in p for p in pixels)


def test_radar_oldest_layout_rebuilds_times_from_seconds_after_midnight() -> None:
    legacy = _read("legacy", "radar_legacy_oldest.json")
    result = upgrade_radar(legacy)
    sweep = result.document["sweeps"][0]
    seconds = legacy["sweeps"][0]["pixels"][0]["reflectivity_time"]
    hours, rest = divmod(seconds, 3600)
    assert sweep["pixels"][0]["reflectivity_time"].startswith(
        f"{legacy['sweeps'][0]['year']:04d}-{legacy['sweeps'][0]['month']:02d}-"
        f"{legacy['sweeps'][0]['day']:02d}T{int(hours):02d}:{int(rest // 60):02d}"
    )
    assert "year" not in sweep and "file" not in sweep
    assert sweep["volume_scan_start_time"].endswith("Z")


def test_radar_oldest_layout_drops_empty_products() -> None:
    legacy = _read("legacy", "radar_legacy_oldest.json")
    empty = sum(1 for s in legacy["sweeps"] for p in s["pixels"] for v in p.values() if v == "")
    assert empty > 0
    result = upgrade_radar(legacy)
    assert not any(
        v == "" for s in result.document["sweeps"] for p in s["pixels"] for v in p.values()
    )


def test_radar_oldest_layout_handles_midnight_crossing() -> None:
    legacy = _read("legacy", "radar_legacy_oldest.json")
    sweep = legacy["sweeps"][0]
    sweep["time_stamp"] = "23:59:30"
    sweep["exceeds_midnight"] = True
    sweep["pixels"][0]["reflectivity_time"] = 15.25  # 00:00:15.250 the next day
    result = upgrade_radar(legacy)
    day = f"{sweep['year']:04d}-{sweep['month']:02d}-{sweep['day'] + 1:02d}"
    assert result.document["sweeps"][0]["pixels"][0]["reflectivity_time"] == (
        f"{day}T00:00:15.250Z"
    )


def test_radar_oldest_layout_with_unusable_date_keeps_pixel_times() -> None:
    legacy = _read("legacy", "radar_legacy_oldest.json")
    legacy["sweeps"][0]["month"] = 13
    result = upgrade_radar(legacy)
    assert isinstance(result.document["sweeps"][0]["pixels"][0]["reflectivity_time"], float)
    assert any("unusable" in c for c in result.changes)


def test_radar_without_sweeps_is_refused() -> None:
    with pytest.raises(NotAContractFileError, match="no sweeps"):
        upgrade_radar({"sweeps": []})


def test_radar_unknown_fields_are_kept_and_counted() -> None:
    legacy = _read("legacy", "radar_legacy.json")
    for pixel in legacy["sweeps"][0]["pixels"]:
        pixel["analyst_note"] = "x"
    legacy["sweeps"][0]["mystery"] = 1
    legacy["export_tool"] = "old"
    result = upgrade_radar(legacy)
    n = len(legacy["sweeps"][0]["pixels"])
    assert f"pixels: kept unrecognized field 'analyst_note' (x{n})" in result.changes
    assert "sweeps: kept unrecognized field 'mystery' (x1)" in result.changes
    assert "radar: kept unrecognized field 'export_tool'" in result.changes


def test_radar_source_file_duplicate_is_dropped() -> None:
    legacy = _read("legacy", "radar_legacy.json")
    pixel = legacy["sweeps"][0]["pixels"][0]
    pixel["file_name"] = pixel["source_file"]
    result = upgrade_radar(legacy)
    assert "source_file" not in result.document["sweeps"][0]["pixels"][0]


# --- seismo -------------------------------------------------------------------------


def test_seismo_gets_header_and_keeps_loki_version() -> None:
    result = upgrade_seismo(_read("legacy", "seismo_loki.json"))
    assert result.document["contract"] == "hel.seismo"
    assert result.document["schema_version"] == "1.1.0"


def test_seismo_other_loki_versions_are_refused() -> None:
    with pytest.raises(NotAContractFileError, match="1.0.0"):
        upgrade_seismo({"schema_version": "1.0.0", "event_id": "x"})


# --- dispatch -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [[], "text", {}, {"overall": {}, "per_station": [], "blips": []}],
)
def test_non_contract_data_is_refused(data: Any) -> None:
    with pytest.raises(NotAContractFileError):
        hel.upgrade(data)


@pytest.mark.parametrize(
    ("name", "contract"),
    [
        ("event_minimal.json", "hel.event"),
        ("radar_minimal.json", "hel.radar"),
        ("seismo_minimal.json", "hel.seismo"),
    ],
)
def test_current_files_pass_through_unchanged(name: str, contract: str) -> None:
    data = _read("current", name)
    result = hel.upgrade(data)
    assert result.contract == contract
    assert result.layout == "current"
    assert result.document == data
