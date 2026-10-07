"""Convert legacy, un-versioned files to the current Hel contracts.

Every app that reads a contract file calls ``upgrade`` first, so files from
before Hel (the recovered-falls archive holds hundreds) keep working. The
upgrader:

- recognizes each legacy layout found in the 2026-10-06 survey of the
  recovered-falls folders (see ``LAYOUTS``);
- works on a copy and never changes its input, and never writes over a file
  (the CLI refuses to);
- records every change it makes, in plain words, in ``UpgradeResult.changes``,
  including any assumption (zone-less times are treated as UTC);
- keeps fields it does not recognize, and reports them, rather than dropping
  data silently. The only fields it drops are legacy display or bookkeeping
  values whose information it moves elsewhere, and it reports each one;
- refuses anything that isn't a contract file, with ``NotAContractFileError``.

The upgrader works on plain JSON data (dicts and lists), not on the models,
so values it doesn't touch are written back exactly as they were read.
Validate the result with ``hel.validate``.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from hel import event as event_contract
from hel import radar as radar_contract
from hel import seismo as seismo_contract

# The legacy layouts the upgrader converts, by contract.
LAYOUTS: dict[str, tuple[str, ...]] = {
    "hel.event": (
        "terminus",  # terminus block; meteorite_properties; optional finds
        "luminous_end",  # luminous_end block; otherwise as "terminus"
        # Either of the above may carry spreadsheet-style labels such as
        # "Meteorite Density (kg/m^3)"; those are converted too.
    ),
    "hel.radar": (
        "legacy",  # sweeps -> pixels with pixel_lat/pixel_long/... (74 of 76 surveyed)
        "legacy_oldest",  # per-sweep date fields, theta/"distance (m)" pixels (2 of 76)
    ),
    "hel.seismo": ("loki-1.1",),  # Loki's own schema_version "1.1.0"
}


class NotAContractFileError(ValueError):
    """Raised when data matches no Hel contract or known legacy layout."""


@dataclass
class UpgradeResult:
    """The outcome of upgrading one file.

    Attributes:
        contract: The contract the data now follows, e.g. ``"hel.event"``.
        layout: The layout it was read as: ``"current"`` when it already
            carried a Hel header, else one of ``LAYOUTS[contract]``.
        document: The upgraded data, ready to validate and save.
        changes: Every change made, in plain words, in the order made.
    """

    contract: str
    layout: str
    document: dict[str, Any]
    changes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        """True when the upgrader changed anything."""
        return bool(self.changes)


def upgrade(data: Any) -> UpgradeResult:
    """Upgrade parsed JSON of any Hel contract to its current version.

    Args:
        data: Parsed JSON (``json.load`` output) of an event, radar or seismo
            file, in a current or legacy layout.

    Returns:
        The upgraded document and a record of every change.

    Raises:
        NotAContractFileError: If ``data`` matches no contract or legacy layout.
    """
    if not isinstance(data, dict):
        raise NotAContractFileError("not a JSON object, so not a Hel contract file")
    contract = data.get("contract")
    if contract == event_contract.CONTRACT or "terminus" in data or "luminous_end" in data:
        return upgrade_event(data)
    if contract == radar_contract.CONTRACT or "sweeps" in data:
        return upgrade_radar(data)
    if contract == seismo_contract.CONTRACT or "schema_version" in data:
        return upgrade_seismo(data)
    keys = ", ".join(list(data)[:6]) or "none"
    raise NotAContractFileError(
        f"not a recognized Hel contract file (top-level keys: {keys}); "
        "expected an event, radar or seismo file"
    )


# --- Shared helpers --------------------------------------------------------------


def _with_header(contract: str, version: str, body: dict[str, Any]) -> dict[str, Any]:
    """Return ``body`` with the Hel header as its first two keys.

    Args:
        contract: Contract name.
        version: Contract version.
        body: The document's other fields, in their original order.

    Returns:
        A new dict: ``contract``, ``contract_version``, then ``body``.
    """
    rest = {k: v for k, v in body.items() if k not in ("contract", "contract_version")}
    return {"contract": contract, "contract_version": version, **rest}


def _utc_text(value: Any, where: str, changes: list[str], assumed: set[str]) -> Any:
    """Make a legacy time string end in ``Z``.

    Zone-less times are treated as UTC (every legacy producer wrote UTC
    without saying so). Times with an offset are converted to UTC. Anything
    else is returned unchanged for validation to report.

    Args:
        value: The time as read.
        where: Field label for the change record.
        changes: The change record to append to.
        assumed: Labels already reported as assumed UTC, so each field is
            reported once per file rather than once per pixel.

    Returns:
        The time in ISO 8601 ending in ``Z``, or ``value`` unchanged.
    """
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.endswith(("Z", "z")):
        return text[:-1] + "Z" if text.endswith("z") else text
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        if where not in assumed:
            assumed.add(where)
            changes.append(f"{where}: no time zone given; treated as UTC")
        return text + "Z"
    as_utc = parsed.astimezone(UTC).replace(tzinfo=None).isoformat()
    changes.append(f"{where}: converted {text} to UTC")
    return as_utc + "Z"


def _rename(obj: dict[str, Any], old: str, new: str, where: str, changes: list[str]) -> None:
    """Rename one key in place, keeping its position, unless ``new`` exists.

    Args:
        obj: The JSON object.
        old: Legacy key.
        new: Contract key.
        where: Label for the change record.
        changes: The change record to append to.
    """
    if old not in obj:
        return
    if new in obj:
        if obj[new] == obj[old]:
            del obj[old]
            changes.append(f"{where}: dropped '{old}' (duplicate of '{new}')")
        else:
            changes.append(f"{where}: kept '{old}' as is; '{new}' already present")
        return
    items = list(obj.items())
    obj.clear()
    for key, value in items:
        obj[new if key == old else key] = value
    changes.append(f"{where}: renamed '{old}' to '{new}'")


# --- event.json ------------------------------------------------------------------

# Spreadsheet-style labels written by an early tool: label -> (block, key, scale).
# block None means the top level of the event.
_EVENT_LABELS: dict[str, tuple[str | None, str, float]] = {
    "Meteorite Density (kg/m^3)": ("meteorite_properties", "density_kg_m3", 1.0),
    "Dielectric Factor (|K|^2)": ("meteorite_properties", "k2_factor", 1.0),
    "Meteorite Shape Factor": ("meteorite_properties", "shape_factor", 1.0),
    "Pre-Atmospheric Mass (kg)": ("meteorite_properties", "pre_atmospheric_mass_kg", 1.0),
    "Toughness Index": ("meteorite_properties", "toughness_index", 1.0),
    "%Mass Lost in Fireball": (None, "mass_lost_pct", 1.0),
    "Cosmic Velocity (km/s)": (None, "entry_speed_mps", 1000.0),
}

# Top-level legacy keys and their contract names.
_EVENT_RENAMES: dict[str, str] = {
    "radar_duration_seconds": "radar_duration_s",
    "radar_duration_seconds_nexrad": "radar_duration_nexrad_s",
    "TNT_equivalent_kilotons": "tnt_equivalent_kt",
}

_EVENT_FIELDS = frozenset(event_contract.EventDocument.model_fields)


def upgrade_event(data: dict[str, Any]) -> UpgradeResult:
    """Upgrade an ``event.json`` to ``hel.event`` 1.0.

    Args:
        data: Parsed ``event.json`` in a current or legacy layout.

    Returns:
        The upgraded event and the change record.

    Raises:
        NotAContractFileError: If there is no luminous-end (terminus) block.
    """
    doc = copy.deepcopy(data)
    changes: list[str] = []
    assumed: set[str] = set()
    if doc.get("contract") == event_contract.CONTRACT:
        return UpgradeResult(event_contract.CONTRACT, "current", doc)

    layout = "luminous_end" if "luminous_end" in doc else "terminus"
    if "terminus" in doc:
        if "luminous_end" in doc:
            raise NotAContractFileError(
                "event has both 'terminus' and 'luminous_end' blocks; keep one"
            )
        _rename(doc, "terminus", "luminous_end", "event", changes)
    end = doc.get("luminous_end")
    if not isinstance(end, dict):
        raise NotAContractFileError("event has no luminous_end (terminus) object")

    # The legacy speed_mps at the luminous end is the terminus speed (D10).
    _rename(end, "speed_mps", "terminus_speed_mps", "luminous_end", changes)
    end["time_utc"] = _utc_text(end.get("time_utc"), "luminous_end.time_utc", changes, assumed)

    start = doc.get("luminous_start")
    if isinstance(start, dict):
        _rename(start, "speed_mps", "entry_speed_mps", "luminous_start", changes)
        start["time_utc"] = _utc_text(
            start.get("time_utc"), "luminous_start.time_utc", changes, assumed
        )
    for point in doc.get("luminous_trajectory") or []:
        if isinstance(point, dict):
            point["time_utc"] = _utc_text(
                point.get("time_utc"), "luminous_trajectory[].time_utc", changes, assumed
            )

    # Entry speed in km/s becomes m/s.
    if "cosmic_velocity_kms" in doc:
        kms = doc.pop("cosmic_velocity_kms")
        if isinstance(kms, int | float) and "entry_speed_mps" not in doc:
            doc["entry_speed_mps"] = float(kms) * 1000.0
            changes.append("event: 'cosmic_velocity_kms' (km/s) became 'entry_speed_mps' (m/s)")
        else:
            doc["cosmic_velocity_kms"] = kms
            changes.append("event: kept 'cosmic_velocity_kms' as is (not a number, or duplicate)")

    for old, new in _EVENT_RENAMES.items():
        _rename(doc, old, new, "event", changes)
    if "tnt_equivalent_kt" in doc and doc["tnt_equivalent_kt"] is None:
        del doc["tnt_equivalent_kt"]
        changes.append("event: dropped empty 'tnt_equivalent_kt' (null)")

    # Spreadsheet-style labels from the earliest tool.
    for label, (block, key, scale) in _EVENT_LABELS.items():
        if label not in doc:
            continue
        value = doc.pop(label)
        target = doc if block is None else doc.setdefault(block, {})
        if key in target:
            doc[label] = value
            changes.append(f"event: kept '{label}' as is; '{key}' already present")
            continue
        target[key] = value * scale if isinstance(value, int | float) else value
        unit_note = " (km/s to m/s)" if scale != 1.0 else ""
        place = key if block is None else f"{block}.{key}"
        changes.append(f"event: label '{label}' became '{place}'{unit_note}")

    props = doc.get("meteorite_properties")
    if isinstance(props, dict) and props.get("density_mode", "") is None:
        del props["density_mode"]
        changes.append("meteorite_properties: dropped empty 'density_mode' (null)")

    # Recovered masses: grams become kilograms (SI, D26).
    finds = doc.get("finds")
    if isinstance(finds, list):
        converted = 0
        for find in finds:
            if isinstance(find, dict) and "mass_g" in find and "mass_kg" not in find:
                grams = find.pop("mass_g")
                find["mass_kg"] = grams / 1000.0 if isinstance(grams, int | float) else grams
                converted += 1
        if converted:
            changes.append(f"finds: {converted} masses converted from 'mass_g' to 'mass_kg'")

    for key in doc:
        if key not in _EVENT_FIELDS:
            changes.append(f"event: kept unrecognized field '{key}'")

    changes.insert(0, f"added header {event_contract.CONTRACT} {event_contract.CONTRACT_VERSION}")
    return UpgradeResult(
        event_contract.CONTRACT,
        layout,
        _with_header(event_contract.CONTRACT, event_contract.CONTRACT_VERSION, doc),
        changes,
    )


# --- RADAR_*.json ----------------------------------------------------------------

# Display-only pixel fields the legacy exporter wrote; their information is
# already in other fields.
_PIXEL_DROPPED: dict[str, str] = {
    "sweep_desc": "display label (radar, time and elevation are in other fields)",
}

# Oldest layout: pixel key -> contract key.
_OLDEST_PIXEL_RENAMES: dict[str, str] = {
    "theta": "pixel_azimuth",
    "distance (m)": "pixel_distance",
    "altitude (m)": "pixel_altitude",
    "lat": "pixel_lat",
    "lon": "pixel_long",
    "utm_easting": "pixel_utm_easting",
    "utm_northing": "pixel_utm_northing",
    "utm_zone": "pixel_utm_zone",
    "SUR/DOP": "cut_type",
    "prf": "prf_hz",
    "azimuthal_resolution": "azimuth_spacing_deg",
    "range_gate_spacing": "gate_size_m",
}

# Oldest layout: sweep key -> contract key.
_OLDEST_SWEEP_RENAMES: dict[str, str] = {
    "radar_elevation": "radar_altitude_m",
    "vcp": "vcp_mode",
    "horizontal_beamwidth": "beamwidth_h_deg",
    "selection_points": "selection_polygon",
}

_PIXEL_FIELDS = frozenset(radar_contract.Pixel.model_fields)
_SWEEP_FIELDS = frozenset(radar_contract.Sweep.model_fields)
_RADAR_FIELDS = frozenset(radar_contract.RadarDocument.model_fields)


def upgrade_radar(data: dict[str, Any]) -> UpgradeResult:
    """Upgrade a ``RADAR_*.json`` to ``hel.radar`` 1.0.

    Args:
        data: Parsed radar export in a current or legacy layout.

    Returns:
        The upgraded radar file and the change record.

    Raises:
        NotAContractFileError: If there are no sweeps.
    """
    doc = copy.deepcopy(data)
    changes: list[str] = []
    if doc.get("contract") == radar_contract.CONTRACT:
        return UpgradeResult(radar_contract.CONTRACT, "current", doc)
    sweeps = doc.get("sweeps")
    if not isinstance(sweeps, list) or not sweeps:
        raise NotAContractFileError("radar file has no sweeps (empty legacy export?)")

    oldest = any(isinstance(s, dict) and "year" in s and "time_stamp" in s for s in sweeps)
    layout = "legacy_oldest" if oldest else "legacy"
    assumed: set[str] = set()
    tally: dict[str, int] = {}

    def count(message: str) -> None:
        # Pixel-level changes are counted and reported once per kind, so a
        # file with thousands of pixels gets a readable change record.
        tally[message] = tally.get(message, 0) + 1

    for sweep in sweeps:
        if not isinstance(sweep, dict):
            continue
        date_info: tuple[date, float, bool] | None = None
        if oldest:
            date_info = _upgrade_oldest_sweep(sweep, count)
        for key in ("volume_scan_start_time", "radar_volume_start_time"):
            if key in sweep:
                sweep[key] = _utc_text(sweep[key], f"sweep.{key}", changes, assumed)
        for pixel in sweep.get("pixels") or []:
            if not isinstance(pixel, dict):
                continue
            if oldest:
                _upgrade_oldest_pixel(pixel, sweep, date_info, count)
            _upgrade_pixel(pixel, count, changes, assumed)
        if oldest:
            # Each pixel now carries the source file name itself.
            sweep.pop("file", None)
        for key in sweep:
            if key not in _SWEEP_FIELDS:
                count(f"sweeps: kept unrecognized field '{key}'")

    for key in doc:
        if key not in _RADAR_FIELDS:
            changes.append(f"radar: kept unrecognized field '{key}'")
    changes.extend(f"{message} (x{n})" for message, n in tally.items())
    changes.insert(0, f"added header {radar_contract.CONTRACT} {radar_contract.CONTRACT_VERSION}")
    return UpgradeResult(
        radar_contract.CONTRACT,
        layout,
        _with_header(radar_contract.CONTRACT, radar_contract.CONTRACT_VERSION, doc),
        changes,
    )


def _upgrade_pixel(
    pixel: dict[str, Any],
    count: Callable[[str], None],
    changes: list[str],
    assumed: set[str],
) -> None:
    """Apply the upgrades every legacy pixel layout needs, in place.

    Args:
        pixel: One pixel record.
        count: Records one pixel-level change (tallied per kind).
        changes: The file's change record (for time-zone assumptions).
        assumed: Time fields already reported as assumed UTC.
    """
    if "source_file" in pixel:
        if "file_name" not in pixel:
            _rename(pixel, "source_file", "file_name", "pixels", [])
            count("pixels: renamed 'source_file' to 'file_name'")
        elif pixel["file_name"] == pixel["source_file"]:
            del pixel["source_file"]
            count("pixels: dropped 'source_file' (duplicate of 'file_name')")
    for old, new in radar_contract.PRODUCT_ALIASES.items():
        if old in pixel and new not in pixel:
            _rename(pixel, old, new, "pixels", [])
            count(f"pixels: renamed product '{old}' to '{new}'")
    for key, reason in _PIXEL_DROPPED.items():
        if key in pixel:
            del pixel[key]
            count(f"pixels: dropped '{key}' ({reason})")
    for key in ("reflectivity_time", "volume_scan_start_time"):
        if key in pixel:
            pixel[key] = _utc_text(pixel[key], f"pixel.{key}", changes, assumed)
    for key in pixel:
        if key not in _PIXEL_FIELDS:
            count(f"pixels: kept unrecognized field '{key}'")


def _upgrade_oldest_sweep(
    sweep: dict[str, Any], count: Callable[[str], None]
) -> tuple[date, float, bool] | None:
    """Convert one sweep of the oldest layout, in place.

    The oldest layout stores the volume date and start time on the sweep
    (``year``, ``month``, ``day``, ``time_stamp``) and each pixel's time as
    seconds after midnight. This moves the date into an ISO time and returns
    what the pixels need to rebuild their own times.

    Args:
        sweep: One sweep record.
        count: Records one sweep-level change (tallied per kind).

    Returns:
        ``(volume date, volume start in seconds after midnight, whether the
        volume crosses midnight)``, or None when the date fields are unusable.
    """
    for old, new in _OLDEST_SWEEP_RENAMES.items():
        if old in sweep and new not in sweep:
            _rename(sweep, old, new, "sweeps", [])
            count(f"sweeps: renamed '{old}' to '{new}'")
    try:
        day = date(int(sweep["year"]), int(sweep["month"]), int(sweep["day"]))
        start = time.fromisoformat(str(sweep["time_stamp"]))
    except (KeyError, TypeError, ValueError):
        count("sweeps: date fields unusable; pixel times left as they were")
        return None
    start_s = start.hour * 3600 + start.minute * 60 + start.second
    crosses = bool(sweep.get("exceeds_midnight", False))
    if "volume_scan_start_time" not in sweep:
        sweep["volume_scan_start_time"] = datetime.combine(day, start).isoformat() + "Z"
    for key in ("year", "month", "day", "time_stamp", "exceeds_midnight"):
        sweep.pop(key, None)
    count(
        "sweeps: 'year'/'month'/'day'/'time_stamp' became 'volume_scan_start_time'; "
        "'exceeds_midnight' used for pixel times, then dropped"
    )
    if "file" in sweep:
        count("sweeps: sweep 'file' copied to each pixel's 'file_name', then dropped")
    return day, float(start_s), crosses


def _upgrade_oldest_pixel(
    pixel: dict[str, Any],
    sweep: dict[str, Any],
    date_info: tuple[date, float, bool] | None,
    count: Callable[[str], None],
) -> None:
    """Convert one pixel of the oldest layout, in place.

    Args:
        pixel: One pixel record.
        sweep: Its sweep (for the source file name).
        date_info: What ``_upgrade_oldest_sweep`` returned for the sweep.
        count: Records one pixel-level change (tallied per kind).
    """
    for old, new in _OLDEST_PIXEL_RENAMES.items():
        if old in pixel and new not in pixel:
            _rename(pixel, old, new, "pixels", [])
            count(f"pixels: renamed '{old}' to '{new}'")
    if "range_gate" in pixel and "source_gate_start_index" not in pixel:
        gate = pixel.pop("range_gate")
        pixel["source_gate_start_index"] = gate
        pixel["source_gate_end_index_exclusive"] = gate + 1 if isinstance(gate, int) else gate
        count("pixels: 'range_gate' became 'source_gate_start_index' (one gate)")
    if "file" in sweep and "file_name" not in pixel:
        pixel["file_name"] = sweep["file"]
    # The oldest exporter wrote "" for a product with no value at the gate.
    # The contract omits such products instead.
    for product in (*radar_contract.PRODUCTS, *radar_contract.PRODUCT_ALIASES):
        if pixel.get(product) == "":
            del pixel[product]
            count(f"pixels: dropped empty product '{product}' (\"\" meant no value)")
    seconds = pixel.get("reflectivity_time")
    if date_info is not None and isinstance(seconds, int | float) and math.isfinite(seconds):
        day, start_s, crosses = date_info
        # A volume that crosses midnight has pixel times that wrap to small
        # values; those belong to the next day.
        if crosses and seconds < start_s:
            day = day + timedelta(days=1)
        whole_ms = round(seconds * 1000.0)
        stamp = datetime.combine(day, time()) + timedelta(milliseconds=whole_ms)
        text = stamp.strftime("%Y-%m-%dT%H:%M:%S")
        if whole_ms % 1000:
            text += f".{whole_ms % 1000:03d}"
        pixel["reflectivity_time"] = text + "Z"
        count("pixels: 'reflectivity_time' converted from seconds after midnight to UTC time")


# --- seismo.json -----------------------------------------------------------------


def upgrade_seismo(data: dict[str, Any]) -> UpgradeResult:
    """Upgrade a Loki ``seismo.json`` to ``hel.seismo`` 1.1.

    Loki's 1.1.0 files differ from ``hel.seismo`` 1.1 only by the header, so
    this adds the header and keeps Loki's ``schema_version`` as a deprecated
    alias.

    Args:
        data: Parsed ``seismo.json``.

    Returns:
        The upgraded file and the change record.

    Raises:
        NotAContractFileError: If the Loki version is not 1.1.x.
    """
    doc = copy.deepcopy(data)
    if doc.get("contract") == seismo_contract.CONTRACT:
        return UpgradeResult(seismo_contract.CONTRACT, "current", doc)
    version = str(doc.get("schema_version", ""))
    if not version.startswith("1.1."):
        raise NotAContractFileError(
            f"seismo.json schema_version {version!r} is not supported; only Loki 1.1.x is"
        )
    changes = [
        f"added header {seismo_contract.CONTRACT} {seismo_contract.CONTRACT_VERSION}; "
        f"kept Loki's schema_version {version} as a deprecated alias"
    ]
    return UpgradeResult(
        seismo_contract.CONTRACT,
        "loki-1.1",
        _with_header(seismo_contract.CONTRACT, seismo_contract.CONTRACT_VERSION, doc),
        changes,
    )
