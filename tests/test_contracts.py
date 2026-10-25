"""Tests for the contract models: what each contract accepts and rejects."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import hel
from hel import ContractValidationError
from hel._base import check_contract_version
from hel.event import EventDocument
from hel.radar import PRODUCT_ALIASES, PRODUCTS, RadarDocument, excluded_sweeps
from hel.results import ResultsDocument
from hel.seismo import SeismoDocument

GOLDEN = Path(hel.__file__).parent / "golden"


def _golden(group: str, name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((GOLDEN / group / name).read_text(encoding="utf-8"))
    return data


# --- Shared rules -----------------------------------------------------------------


@pytest.mark.parametrize("version", ["1.0", "1.7", "1.12"])
def test_reader_accepts_any_minor_of_its_major(version: str) -> None:
    assert check_contract_version("hel.event", version, 1) == version


@pytest.mark.parametrize("version", ["2.0", "0.9", "1", "1.0.0", "one"])
def test_reader_rejects_other_majors_and_bad_versions(version: str) -> None:
    with pytest.raises(ValueError):
        check_contract_version("hel.event", version, 1)


def test_newer_minor_with_unknown_fields_loads_and_warns() -> None:
    data = _golden("current", "event_minimal.json")
    data["contract_version"] = "1.3"
    data["new_optional_field"] = 5
    data["luminous_end"]["another_new_field"] = "x"
    document, warnings = hel.validate(data)
    assert document.contract_version == "1.3"
    assert "(top level): 'new_optional_field'" in warnings
    assert "luminous_end: 'another_new_field'" in warnings
    # Unknown fields survive a save, so newer files round-trip through old readers.
    assert json.loads(document.to_json())["new_optional_field"] == 5


def test_times_must_be_utc_with_zone() -> None:
    data = _golden("current", "event_minimal.json")
    data["luminous_end"]["time_utc"] = "2003-03-27T05:50:26.4"
    with pytest.raises(ContractValidationError, match="no time zone"):
        hel.validate(data)
    data["luminous_end"]["time_utc"] = "2003-03-27T00:50:26.4-05:00"
    with pytest.raises(ContractValidationError, match="not UTC"):
        hel.validate(data)


def test_times_serialize_with_z_and_trimmed_fraction() -> None:
    data = _golden("current", "event_minimal.json")
    document, _ = hel.validate(data)
    assert isinstance(document, EventDocument)
    assert document.luminous_end.time_utc == datetime(2003, 3, 27, 5, 50, 26, 400000, UTC)
    assert json.loads(document.to_json())["luminous_end"]["time_utc"] == "2003-03-27T05:50:26.4Z"
    document.luminous_end.time_utc = datetime(2003, 3, 27, 5, 50, 26, tzinfo=UTC)
    assert '"2003-03-27T05:50:26Z"' in document.to_json()


def test_to_json_omits_fields_never_set() -> None:
    document, _ = hel.validate(_golden("current", "event_minimal.json"))
    assert "luminous_start" not in json.loads(document.to_json())


def test_validate_requires_a_known_header() -> None:
    with pytest.raises(ContractValidationError, match="contract"):
        hel.validate({"event_id": "x"})
    with pytest.raises(ContractValidationError, match="contract"):
        hel.validate(["not", "an", "object"])


def test_validation_error_lists_every_problem() -> None:
    data = _golden("current", "event_minimal.json")
    data["luminous_end"]["lat"] = 95.0
    data["luminous_end"]["declination_deg"] = -3.0
    with pytest.raises(ContractValidationError) as info:
        hel.validate(data)
    assert len(info.value.problems) == 2
    assert any(p.startswith("luminous_end.lat:") for p in info.value.problems)


def test_validation_error_message_is_capped() -> None:
    error = ContractValidationError("hel.radar", [f"p{i}: bad" for i in range(25)])
    assert "... and 5 more" in str(error)


# --- hel.event ----------------------------------------------------------------------


@pytest.mark.parametrize("name", ["event_minimal.json", "event_full.json"])
def test_event_golden_files_validate(name: str) -> None:
    document, warnings = hel.validate(_golden("current", name))
    assert isinstance(document, EventDocument)
    assert warnings == []


def test_event_rejects_blank_id_and_bad_ranges() -> None:
    data = _golden("current", "event_full.json")
    bad = copy.deepcopy(data)
    bad["event_id"] = "   "
    with pytest.raises(ContractValidationError, match="event_id"):
        hel.validate(bad)
    for path, value in (
        (("luminous_end", "azimuth_deg"), 361.0),
        (("luminous_end", "terminus_speed_mps"), 0.0),
        (("meteorite_properties", "k2_factor"), 1.5),
        (("meteorite_properties", "density_mode"), "guessed"),
    ):
        bad = copy.deepcopy(data)
        bad[path[0]][path[1]] = value
        with pytest.raises(ContractValidationError, match=path[1]):
            hel.validate(bad)
    bad = copy.deepcopy(data)
    bad["mass_lost_pct"] = 101.0
    with pytest.raises(ContractValidationError, match="mass_lost_pct"):
        hel.validate(bad)


# --- hel.radar ----------------------------------------------------------------------


@pytest.mark.parametrize("name", ["radar_minimal.json", "radar_full.json"])
def test_radar_golden_files_validate(name: str) -> None:
    document, warnings = hel.validate(_golden("current", name))
    assert isinstance(document, RadarDocument)
    assert warnings == []


def test_radar_full_carries_metadata_quality_and_blips() -> None:
    document, _ = hel.validate(_golden("current", "radar_full.json"))
    assert isinstance(document, RadarDocument)
    sweep = document.sweeps[0]
    assert sweep.band == "S"
    assert sweep.detection_floor_dbz_at_1km == pytest.approx(
        sweep.calibration_constant_dbz0 + sweep.snr_threshold_db  # type: ignore[operator]
    )
    assert sweep.pixels[1].quality is not None and sweep.pixels[1].quality.near_detection_floor
    assert document.blips is not None
    blip = document.blips[0]
    assert all(0 <= i < len(sweep.pixels) for i in blip.pixel_indices)
    assert blip.uncertainty is not None and blip.uncertainty.semi_major_m == 410.0


def test_radar_exclusions_and_the_reader_rule() -> None:
    # 1.2 (H-006): an unticked sweep or blip stays in the file and is used
    # in no calculation; a sweep whose blips are all excluded counts too.
    data = _golden("current", "radar_full.json")
    document, warnings = hel.validate(data)
    assert isinstance(document, RadarDocument) and warnings == []
    assert document.blips is not None and document.blips[0].exclusion is not None
    assert document.blips[0].exclusion.reason == "bright_flight"
    assert excluded_sweeps(document) == {0}  # its only blip is excluded
    data["blips"][0].pop("exclusion")
    document, _ = hel.validate(data)
    assert isinstance(document, RadarDocument) and excluded_sweeps(document) == set()
    data["sweeps"][0]["exclusion"] = {
        "reason": "uncertain", "by": "Fenrir", "at": "2026-10-25T12:00:00Z"
    }  # fmt: skip
    document, _ = hel.validate(data)
    assert isinstance(document, RadarDocument) and excluded_sweeps(document) == {0}
    data["sweeps"][0]["exclusion"]["reason"] = "boring"
    with pytest.raises(ContractValidationError, match="reason"):
        hel.validate(data)
    # A 1.1 file still validates.
    old, _ = hel.validate(_golden("current", "radar_minimal.json"))
    assert isinstance(old, RadarDocument) and excluded_sweeps(old) == set()


def test_radar_requires_sweeps_and_pixel_geometry() -> None:
    data = _golden("current", "radar_minimal.json")
    empty = copy.deepcopy(data)
    empty["sweeps"] = []
    with pytest.raises(ContractValidationError, match="sweeps"):
        hel.validate(empty)
    for key in ("pixel_lat", "pixel_long", "pixel_altitude", "gate_size_m", "reflectivity_time"):
        missing = copy.deepcopy(data)
        del missing["sweeps"][0]["pixels"][0][key]
        with pytest.raises(ContractValidationError, match=key):
            hel.validate(missing)


def test_radar_rejects_unknown_band() -> None:
    data = _golden("current", "radar_minimal.json")
    data["sweeps"][0]["band"] = "L"
    with pytest.raises(ContractValidationError, match="band"):
        hel.validate(data)


def test_every_product_alias_maps_to_a_canonical_product() -> None:
    assert set(PRODUCT_ALIASES.values()) <= set(PRODUCTS)
    assert not set(PRODUCT_ALIASES) & set(PRODUCTS)
    pixel_fields = RadarDocument.model_fields["sweeps"].annotation
    assert pixel_fields is not None
    from hel.radar import Pixel

    assert set(PRODUCTS) <= set(Pixel.model_fields)


# --- hel.seismo ---------------------------------------------------------------------


def test_seismo_minimal_validates() -> None:
    document, warnings = hel.validate(_golden("current", "seismo_minimal.json"))
    assert isinstance(document, SeismoDocument)
    assert warnings == []
    assert document.solution is None


def test_seismo_backfills_declination_from_elevation() -> None:
    data = _golden("upgraded", "seismo_loki.json")
    trajectory = data["solution"]["trajectory"]
    trajectory.pop("travel_declination_deg", None)
    trajectory["travel_elevation_deg"] = -35.0
    document, _ = hel.validate(data)
    assert isinstance(document, SeismoDocument)
    assert document.solution is not None
    assert document.solution.trajectory.travel_declination_deg == 35.0


# --- hel.results --------------------------------------------------------------------


def test_results_minimal_validates() -> None:
    document, warnings = hel.validate(_golden("current", "results_minimal.json"))
    assert isinstance(document, ResultsDocument)
    assert warnings == []
    assert document.forensics is None and document.search is None
    assert document.blips[0].status == "solved"


def test_results_load_through_the_upgrader_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    path.write_text(json.dumps(_golden("current", "results_minimal.json")), encoding="utf-8")
    loaded = hel.load(path)
    assert loaded.contract == "hel.results"
    assert loaded.upgrade.layout == "current" and loaded.upgrade.changes == []


def test_results_round_trip_leaves_absent_fields_out() -> None:
    data = _golden("current", "results_minimal.json")
    document, _ = hel.validate(data)
    assert json.loads(document.to_json()) == data


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("run", "analysis_mode"), "decadal_series"),
        (("blips", 0, "status"), "Solved"),
        (("terminus", "declination_deg"), 95.0),
        (("contract_version",), "2.0"),
    ],
)
def test_results_reject_bad_values(path: tuple[str | int, ...], value: object) -> None:
    data = copy.deepcopy(_golden("current", "results_minimal.json"))
    target: Any = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ContractValidationError):
        hel.validate(data)


def test_results_require_the_fitted_terminus() -> None:
    data = _golden("current", "results_minimal.json")
    del data["terminus"]
    with pytest.raises(ContractValidationError, match="terminus"):
        hel.validate(data)


def test_results_version_is_registered() -> None:
    assert hel.CONTRACT_VERSIONS["hel.results"] == "1.3"


def test_results_uncertainty_section() -> None:
    # 1.1 (H-004): Level 1's probability areas; a 1.0 file stays valid without them.
    document, warnings = hel.validate(_golden("current", "results_full.json"))
    assert isinstance(document, ResultsDocument) and warnings == []
    u = document.uncertainty
    assert u is not None and u.samples == 200 and u.area_scale == 1.0
    assert [a.probability for a in u.blip_areas[0].areas] == [0.5, 0.9]
    assert u.regions[0].mass_class == "fall" and u.search_grid is not None
    assert document.search is not None and document.search.cost == "direct"
    minimal, _ = hel.validate(_golden("current", "results_minimal.json"))
    assert isinstance(minimal, ResultsDocument) and minimal.uncertainty is None


def test_results_list_the_excluded_signatures() -> None:
    # 1.3 (H-006): the unticked signatures the run did not use.
    document, _ = hel.validate(_golden("current", "results_full.json"))
    assert isinstance(document, ResultsDocument) and document.excluded is not None
    assert document.excluded[0].reason == "bright_flight"
    minimal, _ = hel.validate(_golden("current", "results_minimal.json"))
    assert isinstance(minimal, ResultsDocument) and minimal.excluded is None


def test_results_wind_uncertainty() -> None:
    # 1.2 (H-005): the wind's share per mass class and the ensemble's re-fits.
    document, _ = hel.validate(_golden("current", "results_full.json"))
    assert isinstance(document, ResultsDocument)
    u = document.uncertainty
    assert u is not None and u.error_table[0].wind_share == 0.35
    assert u.wind is not None and u.wind.refit and u.wind.members == 10
    assert u.wind.member_fits[0].shift_m == 62.0
    bad = _golden("current", "results_full.json")
    bad["uncertainty"]["error_table"][0]["wind_share"] = 1.5
    with pytest.raises(ContractValidationError, match="wind_share"):
        hel.validate(bad)


def test_results_full_example_validates() -> None:
    # A real Park Forest Full Parameter Refinement run (Fenrir F-011b).
    document, warnings = hel.validate(_golden("current", "results_full.json"))
    assert isinstance(document, ResultsDocument)
    assert warnings == []
    assert document.run.analysis_mode == "full_parameter_refinement"
    assert document.search is not None and len(document.search.scout_samples) == 250
    assert document.forensics is not None and document.forensics.confidence is not None
    statuses = {blip.status for blip in document.blips}
    assert statuses == {"solved", "before_terminus"}
