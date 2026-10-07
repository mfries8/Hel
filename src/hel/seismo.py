"""The seismo-acoustic contract (``hel.seismo``): Loki's ``seismo.json``.

Loki writes ``seismo.json``: the seismic and infrasound evidence for a fall,
the bolide trajectory it reconstructs from that evidence, and everything it
looked up along the way. Fenrir reads it to show Loki's trajectory beside its
own radar fit (Fenrir D22); Loki never feeds Fenrir's fit automatically.

This module adopts Loki's own contract, version 1.1.0, field for field
(decision D26). Two things differ from Loki's copy:

- the Hel header (``contract``, ``contract_version`` "1.1"). Loki's own
  ``schema_version`` ("1.1.0") is still accepted as a deprecated alias until
  Loki writes the Hel header itself;
- unknown fields are kept instead of rejected, per the Hel reader rule.

``source_event.luminous_end`` keeps Loki's own form (with ``speed_mps``)
rather than ``hel.event``'s; aligning it is a MAJOR change, left to Loki's
adoption of Hel.

Conventions (``docs/CONVENTIONS.md``): times are UTC ending in ``Z``;
distances and altitudes are metres, altitude above mean sea level; azimuth is
the direction of motion, degrees clockwise from north.

The human reference for every field is Loki's ``docs/seismo-contract.md``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from hel._base import HelModel, UtcDatetime, check_contract_version

CONTRACT = "hel.seismo"
CONTRACT_VERSION = "1.1"
SUPPORTED_MAJOR = 1
# The version string Loki itself writes in ``schema_version``.
LOKI_SCHEMA_VERSION = "1.1.0"

PhaseKind = Literal[
    "ballistic",
    "fragmentation",
    "airwave-direct",
    "air-coupled-rayleigh",
    "unknown",
]
PathType = Literal["direct", "tropospheric", "stratospheric", "thermospheric", "unknown"]
ResponseStatus = Literal["removed", "nominal", "none"]
MetadataQuality = Literal["ok", "suspect", "missing"]
ReviewStatus = Literal["approved", "rejected", "auto", "pending"]
StationRole = Literal["used", "rejected", "no_data", "not_evaluated"]
TrackSegment = Literal["constrained", "extrapolated"]
Regime = Literal["front", "broadside", "back"]


# --- Source event and provenance --------------------------------------------------


class SeismoLuminousEnd(HelModel):
    """Loki's form of the luminous-flight end (the inversion prior)."""

    time_utc: UtcDatetime
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    altitude_m: float = Field(gt=0.0, description="Altitude above mean sea level, metres.")
    speed_mps: float = Field(gt=0.0, description="Speed at the luminous-flight end, m/s.")
    azimuth_deg: float = Field(
        ge=0.0, le=360.0, description="Direction of travel, degrees clockwise from north."
    )
    declination_deg: float = Field(ge=0.0, le=90.0, description="Degrees below horizontal.")


class SeismoTrajectoryPoint(HelModel):
    """One point of an optional luminous trajectory, in Loki's form."""

    time_utc: UtcDatetime
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    altitude_m: float = Field(gt=0.0, description="Altitude above mean sea level, metres.")
    speed_mps: float | None = Field(default=None, gt=0.0, description="Speed, m/s.")


class SoftwareInfo(HelModel):
    """Software versions that affect the result, for reproducibility."""

    python: str | None = None
    platform: str | None = None
    packages: dict[str, str] = Field(default_factory=dict)


class RunInfo(HelModel):
    """What is needed to reproduce the Loki run."""

    invocation: str | None = None
    rng_seed: int | None = None
    stage_timestamps: dict[str, str] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class ManifestEntry(HelModel):
    """One file of the ``Loki_output/`` bundle, with its integrity hash."""

    relative_path: str
    role: str
    sha256: str
    bytes: int = Field(ge=0)
    media_type: str | None = None


class SourceEvent(HelModel):
    """The ``event.json`` prior Loki started from."""

    luminous_end: SeismoLuminousEnd
    luminous_start: SeismoLuminousEnd | None = None
    luminous_trajectory: list[SeismoTrajectoryPoint] | None = None
    priors_used: list[str] = Field(default_factory=list)
    sigmas: dict[str, float] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    raw_sha256: str | None = None


class Provenance(HelModel):
    """What Loki looked up: data centres, atmosphere and ray tracing."""

    fdsn: dict[str, Any] | None = None
    atmosphere: dict[str, Any] | None = None
    ray_tracer: dict[str, Any] | None = None
    run_config: dict[str, Any] = Field(default_factory=dict)


# --- Stations ------------------------------------------------------------------


class ChannelDetail(HelModel):
    """Metadata for one recording channel."""

    channel: str
    location: str = ""
    sample_rate_hz: float | None = None
    orientation_azimuth_deg: float | None = None
    orientation_dip_deg: float | None = None
    gain: float | None = None
    epoch_start: str | None = None
    epoch_end: str | None = None


class WaveformFile(HelModel):
    """A raw waveform file in the bundle."""

    path: str
    sha256: str | None = None
    bytes: int | None = None
    format: str = "MSEED"
    actual_start: str | None = None
    actual_end: str | None = None
    npts: int | None = None
    sample_rate_hz: float | None = None
    gap_count: int = 0
    requested_window: tuple[str, str] | None = None


class Instrument(HelModel):
    """The station's instrument and its response status."""

    model: str | None = None
    channels: list[str] = Field(default_factory=list)
    response_status: ResponseStatus = "none"
    metadata_quality: MetadataQuality = "missing"


class StationAspect(HelModel):
    """Where a station sits relative to the fireball before the solve.

    ``front`` is ahead of the fireball, ``broadside`` beside it, ``back``
    behind it; ``borderline`` when the label changes within the assumed
    azimuth tolerance.
    """

    regime: Regime
    aspect_deg: float = Field(ge=0.0, le=180.0)
    borderline: bool = False


class SeismoStation(HelModel):
    """One discovered seismic or infrasound station."""

    id: str
    network: str
    station: str
    location: str = ""
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    elevation_m: float = 0.0
    site_name: str | None = None
    instrument: Instrument = Field(default_factory=Instrument)
    channels_detail: list[ChannelDetail] = Field(default_factory=list)
    role: StationRole = "not_evaluated"
    distance_km: float | None = None
    azimuth_deg: float | None = None
    distance_to_trajectory_km: float | None = None
    distance_to_ground_track_km: float | None = None
    waveform_files: dict[str, WaveformFile | str] = Field(default_factory=dict)
    stationxml_file: dict[str, Any] | None = None
    noise: dict[str, Any] | None = None
    usable: bool = True
    exclusion_reason: str | None = None
    aspect: StationAspect | None = None


# --- Picks ----------------------------------------------------------------------


class Detector(HelModel):
    """The automatic detector's verdict on a pick."""

    confidence: float = Field(ge=0.0, le=1.0)
    method: str = ""
    features: dict[str, Any] = Field(default_factory=dict)


class Review(HelModel):
    """The analyst's review of a pick."""

    status: ReviewStatus = "pending"
    reviewer: str | None = None
    reviewed_utc: UtcDatetime | None = None
    notes: str | None = None


class PointTime(HelModel):
    """A point in space and (optionally) time."""

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float = Field(description="Altitude above mean sea level, metres.")
    time_utc: UtcDatetime | None = None


class PickPrediction(HelModel):
    """What the solved trajectory predicts for one pick."""

    time_utc: UtcDatetime | None = None
    residual_s: float | None = None
    celerity_mps: float | None = None
    source_point: PointTime | None = None
    turning_height_m: float | None = None
    ground_distance_m: float | None = Field(default=None, ge=0.0)
    slant_distance_m: float | None = Field(default=None, ge=0.0)
    path_type: str | None = None


class Pick(HelModel):
    """One approved arrival used in the solve."""

    pick_id: str
    station_id: str
    channels: list[str] = Field(default_factory=list)
    phase: PhaseKind = "unknown"
    path_type: PathType = "unknown"
    time_utc: UtcDatetime
    time_uncertainty_s: float = Field(ge=0.0)
    back_azimuth_deg: float | None = Field(default=None, ge=0.0, le=360.0)
    back_azimuth_uncertainty_deg: float | None = Field(default=None, ge=0.0)
    back_azimuth_ambiguous: bool | None = None
    incidence_deg: float | None = Field(default=None, ge=0.0, le=180.0)
    incidence_uncertainty_deg: float | None = Field(default=None, ge=0.0)
    rectilinearity: float | None = Field(default=None, ge=0.0, le=1.0)
    amplitude: float | None = None
    amplitude_unit: str | None = None
    dominant_freq_hz: float | None = Field(default=None, ge=0.0)
    snr_db: float | None = None
    detector: Detector
    review: Review = Field(default_factory=Review)
    predicted: PickPrediction | None = None
    associated_source: str | None = None


# --- Solution -------------------------------------------------------------------


class Velocity(HelModel):
    """Speed at the reference point and the deceleration model."""

    at_reference_mps: float = Field(gt=0.0)
    deceleration_model: str = "none"
    params: dict[str, Any] = Field(default_factory=dict)


class PathSample(HelModel):
    """One sample along the solved trajectory."""

    t_utc: UtcDatetime
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float
    velocity_mps: float | None = None
    mach: float | None = None


class AltitudeMarker(HelModel):
    """A fixed-altitude waypoint (20/30/40/50 km) along the solved trajectory."""

    altitude_km: float = Field(ge=0.0)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float
    time_utc: UtcDatetime | None = None
    velocity_mps: float | None = None
    extrapolated: bool = False


class DarkFlightTerminus(HelModel):
    """Where a fragment of one mass slows to the dark-flight target speed.

    Loki reports these per mass as alternative starting points for Fenrir's
    coarse scan when the true fragment mass is unknown.
    """

    mass_kg: float = Field(gt=0.0)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float
    time_utc: UtcDatetime | None = None
    velocity_mps: float | None = None
    extrapolated: bool = True


class TrajectoryUncertainty(HelModel):
    """Uncertainty of the solved trajectory.

    ``radiant_sigma_deg`` is the azimuth component only, despite its name
    (kept for compatibility with Loki).
    """

    method: str = "monte-carlo"
    n_samples: int | None = None
    param_names: list[str] = Field(default_factory=list)
    param_covariance: list[list[float]] = Field(default_factory=list)
    ground_track_sigma_m: list[float] = Field(default_factory=list)
    radiant_sigma_deg: float | None = None
    declination_sigma_deg: float | None = None
    velocity_sigma_mps: float | None = None
    ensemble: list[dict[str, Any]] = Field(default_factory=list)
    ensemble_file: str | None = None


class Trajectory(HelModel):
    """The solved bolide trajectory."""

    model: str = "constrained-line-with-deceleration"
    reference_point: PointTime
    travel_azimuth_deg: float = Field(ge=0.0, le=360.0)
    travel_elevation_deg: float = Field(ge=-90.0, le=90.0)
    travel_declination_deg: float | None = Field(default=None, ge=0.0, le=90.0)
    velocity: Velocity
    constrained_altitude_range_m: tuple[float, float]
    endpoints: dict[str, PointTime] = Field(default_factory=dict)
    path_samples: list[PathSample] = Field(default_factory=list)
    uncertainty: TrajectoryUncertainty = Field(default_factory=TrajectoryUncertainty)
    dark_flight_speed_mps: float | None = Field(default=None, ge=0.0)
    dark_flight_speed_point: PointTime | None = None
    dark_flight_speed_point_extrapolated: bool | None = None
    altitude_markers: list[AltitudeMarker] = Field(default_factory=list)
    dark_flight_termini: list[DarkFlightTerminus] = Field(default_factory=list)
    azimuth_at_bound: bool = False
    declination_at_bound: bool = False

    @model_validator(mode="after")
    def _backfill_declination(self) -> Trajectory:
        # Files written before travel_declination_deg existed get it from the
        # elevation angle, exactly as Loki does when it loads them.
        if self.travel_declination_deg is None:
            self.travel_declination_deg = min(max(-self.travel_elevation_deg, 0.0), 90.0)
        return self


class Ellipse(HelModel):
    """A horizontal 1-sigma error ellipse."""

    semi_major_m: float = Field(ge=0.0)
    semi_minor_m: float = Field(ge=0.0)
    azimuth_deg: float = Field(ge=0.0, le=360.0)


class FragmentationUncertainty(HelModel):
    """Uncertainty of a located fragmentation."""

    horizontal_sigma_m: float | None = None
    vertical_sigma_m: float | None = None
    time_sigma_s: float | None = None
    ellipse: Ellipse | None = None


class Fragmentation(HelModel):
    """One located fragmentation burst."""

    id: str
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float
    time_utc: UtcDatetime
    uncertainty: FragmentationUncertainty = Field(default_factory=FragmentationUncertainty)
    supporting_picks: list[str] = Field(default_factory=list)
    n_stations: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    relative_energy: float | None = Field(default=None, ge=0.0)
    is_terminal: bool = False


class GroundTrackPoint(HelModel):
    """One point of the trajectory's ground track."""

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    t_utc: UtcDatetime | None = None
    alt_m_above: float | None = None
    segment: TrackSegment | None = None
    horizontal_sigma_m: float | None = Field(default=None, ge=0.0)


class Solution(HelModel):
    """Loki's inversion result."""

    converged: bool = False
    method: str = ""
    trajectory: Trajectory
    fragmentations: list[Fragmentation] = Field(default_factory=list)
    ground_track: list[GroundTrackPoint] = Field(default_factory=list)
    residual_summary: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    comparison_to_prior: dict[str, Any] | None = None
    strewn_field_handoff: PointTime | None = None


# --- Wavefronts and the document -----------------------------------------------------


class WavefrontFrame(HelModel):
    """One animation frame of wavefront rings."""

    t_offset_s: float
    polygons: list[list[tuple[float, float]]] = Field(default_factory=list)


class Wavefronts(HelModel):
    """Optional wavefront animation keyframes."""

    reference_time_utc: UtcDatetime
    frames: list[WavefrontFrame] = Field(default_factory=list)
    frames_file: str | None = None


class SeismoDocument(HelModel):
    """A complete ``seismo.json`` file."""

    contract: Literal["hel.seismo"] = Field(description="Contract name; always 'hel.seismo'.")
    contract_version: str = Field(description="Contract version, MAJOR.MINOR (e.g. '1.1').")
    schema_version: str | None = Field(
        default=None, description="Deprecated: Loki's own version string ('1.1.0')."
    )
    event_id: str
    generated_utc: UtcDatetime | None = None
    loki_version: str | None = None
    software: SoftwareInfo = Field(default_factory=SoftwareInfo)
    run: RunInfo = Field(default_factory=RunInfo)
    bundle_manifest: list[ManifestEntry] = Field(default_factory=list)
    source_event: SourceEvent
    provenance: Provenance = Field(default_factory=Provenance)
    stations: list[SeismoStation] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    picks: list[Pick] = Field(default_factory=list)
    solution: Solution | None = None
    wavefronts: Wavefronts | None = None
    geojson: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contract_version")
    @classmethod
    def _version(cls, value: str) -> str:
        return check_contract_version(CONTRACT, value, SUPPORTED_MAJOR)
