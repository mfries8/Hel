"""The radar-signature contract (``hel.radar``): ``RADAR_*.json`` files.

Gjallerhorn writes one radar file per fall: the weather-radar pixels the
analyst selected as meteorite signatures, grouped by sweep. Fenrir reads it
to fit the dark-flight trajectory and to model the falling fragment
population.

Structure: ``sweeps -> pixels``, with each pixel a flat record. Geometry
field names (``pixel_lat``, ``pixel_long``, ``gate_size_m``, ...) are kept
from the legacy export, where tens of thousands of existing pixels already
use them (decision D26). Radar products use one canonical name across all
networks (``PRODUCTS``); ``hel upgrade`` renames the known aliases.

Conventions (``docs/CONVENTIONS.md``): times are UTC ending in ``Z``; angles
are degrees; azimuths are clockwise from true north; ``pixel_altitude`` is
metres above mean sea level.

Version history:

- **1.0** (2026-10-06): first version. The legacy structure plus optional
  per-sweep radar metadata (band, beam widths, calibration constant, SNR
  threshold, noise level, detection floor), per-pixel quality flags, and
  blips with uncertainty ellipses.
- **1.1** (2026-10-06): optional pixel fields ``velocity_time`` and
  ``dual_pol_time`` (the oldest exports timed each product group
  separately) and ``sweep_elevation`` (a per-pixel copy some exports carry).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from hel._base import HelModel, UtcDatetime, check_contract_version

CONTRACT = "hel.radar"
CONTRACT_VERSION = "1.1"
SUPPORTED_MAJOR = 1

# Canonical radar product names and their units. Every network's product is
# stored under one of these names (Gjallerhorn G5).
PRODUCTS: dict[str, str] = {
    "reflectivity": "dBZ",
    "velocity": "m/s (radial; positive away from the radar)",
    "spectrum_width": "m/s",
    "differential_reflectivity": "dB",
    "correlation_coefficient": "dimensionless (0 to 1)",
    "differential_phase": "degrees",
    "clutter_filter_power_removed": "dB",
}

# Product names written by the legacy code or by other networks, and the
# canonical name each one becomes on upgrade.
PRODUCT_ALIASES: dict[str, str] = {
    "cross_correlation_ratio": "correlation_coefficient",
    "corr_coeff": "correlation_coefficient",
    "diff_reflectivity": "differential_reflectivity",
    "diff_phase": "differential_phase",
}


class PixelQuality(HelModel):
    """Per-pixel quality flags (Gjallerhorn G13). Absent means not assessed."""

    clutter_filtered: bool | None = Field(
        default=None,
        description=(
            "True when the clutter filter removed power at this gate "
            "(see the clutter_filter_power_removed product for how much)."
        ),
    )
    near_detection_floor: bool | None = Field(
        default=None,
        description="True when reflectivity is within the sweep's floor uncertainty of the floor.",
    )
    range_folding_risk: bool | None = Field(
        default=None,
        description="True when the gate may hold a range-folded (second-trip) echo.",
    )


class Pixel(HelModel):
    """One exported radar gate group (a "pixel") selected as a signature."""

    # --- Geometry (required) ---------------------------------------------------
    pixel_lat: float = Field(ge=-90.0, le=90.0, description="Gate-centre latitude, degrees north.")
    pixel_long: float = Field(
        ge=-180.0, le=180.0, description="Gate-centre longitude, degrees east."
    )
    pixel_altitude: float = Field(
        description="Gate-centre altitude above mean sea level, metres (4/3 effective-Earth model)."
    )
    pixel_azimuth: float = Field(
        ge=0.0,
        le=360.0,
        description="Ray azimuth, degrees clockwise from true north, as seen from the radar.",
    )
    pixel_distance: float = Field(ge=0.0, description="Mean slant range of the gate group, metres.")
    gate_size_m: float = Field(
        gt=0.0, description="Range depth of the exported gate group, metres."
    )
    reflectivity_time: UtcDatetime = Field(description="Time of this pixel's source ray (UTC).")
    velocity_time: UtcDatetime | None = Field(
        default=None,
        description="Time of this gate's velocity data, when timed separately (UTC).",
    )
    dual_pol_time: UtcDatetime | None = Field(
        default=None,
        description="Time of this gate's dual-polarization data, when timed separately (UTC).",
    )

    # --- Identity and provenance (optional) -----------------------------------------
    file_name: str | None = Field(default=None, description="Source radar volume file name.")
    radar_name: str | None = Field(default=None, description="Radar station identifier.")
    sweep_number: int | None = Field(default=None, ge=1, description="1-based sweep number.")
    source_sweep_index: int | None = Field(
        default=None, ge=0, description="0-based sweep index in the source volume."
    )
    volume_scan_start_time: UtcDatetime | None = Field(
        default=None, description="First-ray time of the sweep (UTC)."
    )
    selection_plot_field: str | None = Field(
        default=None, description="Radar product used to draw the selection grid."
    )
    selection_gate_size_m: float | None = Field(
        default=None, gt=0.0, description="Width of the selected plot cell, metres."
    )
    selection_ray_index: int | None = Field(
        default=None, ge=0, description="0-based ray index of the selected plot cell."
    )
    selection_plot_range_index: int | None = Field(
        default=None, ge=0, description="0-based plot-resolution range index of the selected cell."
    )
    source_ray_index: int | None = Field(
        default=None, ge=0, description="0-based source ray index of this gate group."
    )
    source_gate_start_index: int | None = Field(
        default=None, ge=0, description="0-based first native gate (inclusive)."
    )
    source_gate_end_index_exclusive: int | None = Field(
        default=None, ge=0, description="0-based last native gate (exclusive)."
    )
    source_field_multiplier: int | None = Field(
        default=None, ge=1, description="Gate replication factor of the source product."
    )
    azimuth_spacing_deg: float | None = Field(
        default=None, gt=0.0, description="Median ray-to-ray azimuth spacing, degrees."
    )
    radar_x_m: float | None = Field(
        default=None, description="East offset of the gate from the radar, metres."
    )
    radar_y_m: float | None = Field(
        default=None, description="North offset of the gate from the radar, metres."
    )
    pixel_utm_zone: int | None = Field(
        default=None, ge=1, le=60, description="UTM zone number (from longitude only)."
    )
    pixel_utm_easting: float | None = Field(default=None, description="UTM easting, metres.")
    pixel_utm_northing: float | None = Field(default=None, description="UTM northing, metres.")
    cut_type: str | None = Field(
        default=None,
        description="Scan cut type, e.g. 'SUR' (surveillance) or 'DOP' (Doppler).",
    )
    prf_hz: float | None = Field(
        default=None, gt=0.0, description="Pulse repetition frequency, Hz."
    )
    range_gate_spacing: float | None = Field(
        default=None, gt=0.0, description="Copy of the sweep's base gate spacing, metres."
    )
    azimuthal_resolution: float | None = Field(
        default=None, gt=0.0, description="Copy of the sweep's azimuth spacing, degrees."
    )
    vcp_mode: int | None = Field(
        default=None, description="Copy of the sweep's NEXRAD volume coverage pattern."
    )
    sweep_elevation: float | None = Field(
        default=None, description="Copy of the sweep's elevation angle, degrees above horizontal."
    )

    # --- Radar products (optional; null means the source value was not finite) -----
    reflectivity: float | None = Field(default=None, description="Reflectivity, dBZ.")
    velocity: float | None = Field(
        default=None, description="Radial velocity, m/s; positive away from the radar."
    )
    spectrum_width: float | None = Field(default=None, description="Spectrum width, m/s.")
    differential_reflectivity: float | None = Field(
        default=None, description="Differential reflectivity ZDR, dB."
    )
    correlation_coefficient: float | None = Field(
        default=None, description="Co-polar correlation coefficient (dimensionless)."
    )
    differential_phase: float | None = Field(
        default=None, description="Differential phase, degrees."
    )
    clutter_filter_power_removed: float | None = Field(
        default=None, description="Power removed by the clutter filter, dB."
    )

    quality: PixelQuality | None = None


class Sweep(HelModel):
    """One radar sweep (one elevation scan) and its selected pixels."""

    radar_name: str = Field(min_length=1, description="Radar station identifier, e.g. 'KGRR'.")
    sweep_number: int = Field(ge=1, description="1-based sweep number in the volume.")
    pixels: list[Pixel]

    source_sweep_index: int | None = Field(
        default=None, ge=0, description="0-based sweep index in the source volume."
    )
    volume_scan_start_time: UtcDatetime | None = Field(
        default=None, description="First-ray time of this sweep (UTC)."
    )
    radar_volume_start_time: UtcDatetime | None = Field(
        default=None, description="Start time of the whole volume scan (UTC)."
    )
    sweep_elevation: float | None = Field(
        default=None, description="Elevation angle of the sweep, degrees above horizontal."
    )
    range_gate_spacing: float | None = Field(
        default=None, gt=0.0, description="Base range-gate spacing of the sweep, metres."
    )
    azimuthal_resolution: float | None = Field(
        default=None, gt=0.0, description="Median ray-to-ray azimuth spacing, degrees."
    )
    pulse_width_m: float | None = Field(
        default=None, gt=0.0, description="Transmitted pulse length expressed as range, metres."
    )
    vcp_mode: int | None = Field(default=None, description="NEXRAD volume coverage pattern number.")
    scan_pattern: str | None = Field(
        default=None, description="Scan-strategy name, for networks without VCP numbers."
    )

    # --- Radar characteristics (Gjallerhorn G5, G12) --------------------------------
    band: Literal["S", "C", "X"] | None = Field(
        default=None, description="Radar band: S (~10 cm), C (~5 cm) or X (~3 cm)."
    )
    wavelength_m: float | None = Field(default=None, gt=0.0, description="Wavelength, metres.")
    beamwidth_h_deg: float | None = Field(
        default=None, gt=0.0, description="Horizontal half-power beam width, degrees."
    )
    beamwidth_v_deg: float | None = Field(
        default=None, gt=0.0, description="Vertical half-power beam width, degrees."
    )
    calibration_constant_dbz0: float | None = Field(
        default=None,
        description=(
            "Reflectivity calibration constant dBZ0: the reflectivity at 1 km "
            "range that gives a signal-to-noise ratio of 0 dB, dBZ."
        ),
    )
    snr_threshold_db: float | None = Field(
        default=None, description="Reflectivity signal-to-noise threshold for this cut, dB."
    )
    noise_level_dbm: float | None = Field(
        default=None, description="Receiver noise level for this cut, dBm."
    )
    detection_floor_dbz_at_1km: float | None = Field(
        default=None,
        description=(
            "Weakest detectable reflectivity at 1 km range, dBZ: "
            "calibration_constant_dbz0 + snr_threshold_db. At range R (km) the "
            "floor is this value + 20*log10(R)."
        ),
    )
    radar_latitude: float | None = Field(
        default=None, ge=-90.0, le=90.0, description="Radar latitude, degrees north."
    )
    radar_longitude: float | None = Field(
        default=None, ge=-180.0, le=180.0, description="Radar longitude, degrees east."
    )
    radar_altitude_m: float | None = Field(
        default=None, description="Radar antenna altitude above mean sea level, metres."
    )

    # --- Legacy selection record (kept from the oldest export layout) -----------------
    selection_polygon: list[tuple[float, float]] | None = Field(
        default=None,
        description="Legacy lasso polygon as (azimuth degrees, range-gate index) vertices.",
    )
    deselected_pixels: list[object] | None = Field(
        default=None, description="Legacy record of pixels removed from the selection."
    )


class BlipUncertainty(HelModel):
    """A blip's 1-sigma position uncertainty (Fenrir D17)."""

    semi_major_m: float = Field(ge=0.0, description="Horizontal ellipse semi-major axis, metres.")
    semi_minor_m: float = Field(ge=0.0, description="Horizontal ellipse semi-minor axis, metres.")
    azimuth_deg: float = Field(
        ge=0.0,
        le=360.0,
        description="Direction of the semi-major axis, degrees clockwise from true north.",
    )
    altitude_sigma_m: float = Field(ge=0.0, description="Altitude uncertainty, metres.")


class Blip(HelModel):
    """A group of pixels treated as one detection (Gjallerhorn G14)."""

    blip_id: str = Field(min_length=1, description="Identifier, unique within the file.")
    radar_name: str = Field(min_length=1, description="Radar station identifier.")
    sweep_number: int = Field(ge=1, description="1-based sweep number of the member pixels.")
    volume_scan_start_time: UtcDatetime | None = Field(
        default=None, description="First-ray time of that sweep (UTC); identifies the volume."
    )
    pixel_indices: list[int] = Field(
        min_length=1, description="0-based indices into that sweep's pixels list."
    )
    lat: float = Field(ge=-90.0, le=90.0, description="Centroid latitude, degrees north.")
    lon: float = Field(ge=-180.0, le=180.0, description="Centroid longitude, degrees east.")
    altitude_m: float = Field(description="Centroid altitude above mean sea level, metres.")
    time_utc: UtcDatetime = Field(description="Representative time of the blip (UTC).")
    centroid_weighting: Literal["reflectivity", "equal"] = Field(
        default="reflectivity",
        description="How member pixels are weighted in the centroid (linear Z for 'reflectivity').",
    )
    uncertainty: BlipUncertainty | None = None


class Producer(HelModel):
    """The software that wrote the file."""

    name: str = Field(min_length=1, description="Program name, e.g. 'Gjallerhorn'.")
    version: str | None = Field(default=None, description="Program version.")


class RadarDocument(HelModel):
    """A complete ``RADAR_*.json`` file."""

    contract: Literal["hel.radar"] = Field(description="Contract name; always 'hel.radar'.")
    contract_version: str = Field(description="Contract version, MAJOR.MINOR (e.g. '1.0').")
    file_name: str | None = Field(default=None, description="Export name given by the producer.")
    producer: Producer | None = None
    sweeps: list[Sweep] = Field(min_length=1)
    blips: list[Blip] | None = None

    @field_validator("contract_version")
    @classmethod
    def _version(cls, value: str) -> str:
        return check_contract_version(CONTRACT, value, SUPPORTED_MAJOR)
