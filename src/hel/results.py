"""The results contract (``hel.results``): what Fenrir found for one run.

Fenrir writes one results file per finished run: the fitted terminus, each
radar blip's fragment mass and landing site, the forensics of the solved
masses, and the winds used. Other apps and Fenrir's own frontend read it.

Conventions (``docs/CONVENTIONS.md``): times are UTC ending in ``Z``; azimuth
is the direction of travel in degrees clockwise from true north; declination
is degrees below horizontal. Two choices differ from the input contracts
(Fenrir D28): **every altitude here is height above the WGS84 ellipsoid**
(the input contracts use mean sea level; displays convert back), and every
mass is in **kilograms** (displays show grams below 1000 g).

Version history:

- **1.0** (2026-10-15): first version (H-003, with Fenrir F-011b).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from hel._base import HelModel, UtcDatetime, check_contract_version

CONTRACT = "hel.results"
CONTRACT_VERSION = "1.0"
SUPPORTED_MAJOR = 1

AnalysisMode = Literal[
    "simple", "algebraic_surrogate", "centerline_alignment", "full_parameter_refinement"
]
BlipStatus = Literal["solved", "before_terminus", "solver_error"]
SearchedValue = Literal["lat", "lon", "altitude", "azimuth", "declination", "speed", "density"]

_ELLIPSOIDAL = "Height above the WGS84 ellipsoid, metres."
_LAT = "Latitude, degrees north (WGS84)."
_LON = "Longitude, degrees east (WGS84)."
_AZIMUTH = (
    "Direction of travel, degrees clockwise from true north (not the radiant "
    "direction, which differs by 180 degrees)."
)
_DECLINATION = "Trajectory angle below horizontal, degrees (90 = vertical)."


class ResultsRunInfo(HelModel):
    """Which run produced the file."""

    run_id: str = Field(min_length=1, description="The run's folder identifier.")
    generated_utc: UtcDatetime = Field(description="When the file was written (UTC).")
    fenrir_version: str = Field(description="Version of Fenrir that wrote the file.")
    analysis_mode: AnalysisMode = Field(
        description=(
            "Fit mode: 'simple' (the entered terminus), 'algebraic_surrogate', "
            "'centerline_alignment', or 'full_parameter_refinement' (all "
            "parameters fitted at once)."
        )
    )
    wind_source: str = Field(description="Wind data used, e.g. 'era5', 'raob' or 'raob_3_avg'.")
    wind_data_flagged: str | None = Field(
        default=None,
        description="Why the wind data were flagged, when the analyst accepted flagged data.",
    )
    seed: int | None = Field(default=None, description="Random seed of the searches.")
    anchor_blip_index: int | None = Field(
        default=None,
        ge=0,
        description="Centerline Alignment's anchor blip, counted among the blips with a mass.",
    )


class SearchRange(HelModel):
    """How one value was searched."""

    centre: float = Field(description="Centre of the search, in the value's unit.")
    half_width: float = Field(
        ge=0.0, description="Searched ± this much, in the value's unit (0 when fixed)."
    )
    fixed: bool = Field(description="True when the value was held fixed.")


class SearchRanges(HelModel):
    """How each value was searched (modes other than Simple)."""

    lat: SearchRange | None = Field(
        default=None, description="North-south position: centre and half-width as UTM northing, m."
    )
    lon: SearchRange | None = Field(
        default=None, description="East-west position: centre and half-width as UTM easting, m."
    )
    altitude: SearchRange | None = Field(default=None, description="Altitude, m (ellipsoidal).")
    azimuth: SearchRange | None = Field(default=None, description="Azimuth, degrees.")
    declination: SearchRange | None = Field(default=None, description="Declination, degrees.")
    speed: SearchRange | None = Field(default=None, description="Terminus speed, m/s.")
    density: SearchRange | None = Field(
        default=None,
        description="Bulk density, kg/m^3 (centre: mid-range; half-width: half the range).",
    )


class AnalysisInputs(HelModel):
    """What the analysis started from: the entered terminus and the material.

    The terminus is the event's, with the run's overrides: the fixed terminus
    in Simple mode, the centre of the search otherwise.
    """

    time_utc: UtcDatetime = Field(description="Terminus time (UTC).")
    lat: float = Field(ge=-90.0, le=90.0, description=_LAT)
    lon: float = Field(ge=-180.0, le=180.0, description=_LON)
    altitude_m: float = Field(description="Terminus altitude. " + _ELLIPSOIDAL)
    terminus_speed_mps: float = Field(gt=0.0, description="Terminus speed, m/s.")
    azimuth_deg: float = Field(ge=0.0, le=360.0, description=_AZIMUTH)
    declination_deg: float = Field(ge=0.0, le=90.0, description=_DECLINATION)
    density_kg_m3: float = Field(gt=0.0, description="Bulk density entered, kg/m^3.")
    k2_factor: float = Field(
        gt=0.0, description="Dielectric factor |K|^2 of the material (dimensionless)."
    )
    shape_factor: float = Field(
        ge=1.0, le=2.0, description="Sphere-to-cube drag blend, 1 (sphere) to 2 (cube)."
    )
    pre_atmospheric_mass_kg: float = Field(gt=0.0, description="Pre-atmospheric mass, kg.")
    mass_lost_pct: float = Field(
        ge=0.0, le=100.0, description="Share of the mass lost in bright flight, percent."
    )
    search_ranges: SearchRanges | None = None


class FittedTerminus(HelModel):
    """The fitted terminus: where dark flight begins."""

    time_utc: UtcDatetime = Field(description="Terminus time (UTC; not fitted).")
    lat: float = Field(ge=-90.0, le=90.0, description=_LAT)
    lon: float = Field(ge=-180.0, le=180.0, description=_LON)
    utm_zone: int = Field(ge=1, le=60, description="UTM zone of the fall.")
    utm_northern: bool = Field(description="True for the northern-hemisphere UTM zone.")
    utm_easting_m: float = Field(description="UTM easting of the terminus, metres.")
    utm_northing_m: float = Field(description="UTM northing of the terminus, metres.")
    altitude_m: float = Field(description="Fitted altitude. " + _ELLIPSOIDAL)
    terminus_speed_mps: float = Field(gt=0.0, description="Terminus speed, m/s.")
    azimuth_deg: float = Field(ge=0.0, le=360.0, description=_AZIMUTH)
    declination_deg: float = Field(ge=0.0, le=90.0, description=_DECLINATION)
    density_kg_m3: float = Field(
        gt=0.0,
        description=(
            "Bulk density used for the masses, kg/m^3 (fitted in Full Parameter Refinement)."
        ),
    )
    at_search_edge: list[SearchedValue] = Field(
        description="Searched values that ended within 2% of their range's edge."
    )
    mean_blip_offset_east_m: float | None = Field(
        default=None,
        description=(
            "Mean eastward offset of the blips from where the fitted path "
            "crossed their altitudes, metres."
        ),
    )
    mean_blip_offset_north_m: float | None = Field(
        default=None, description="As mean_blip_offset_east_m, northward, metres."
    )
    offset_lat: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="The terminus moved by the mean offset. " + _LAT,
    )
    offset_lon: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="The terminus moved by the mean offset. " + _LON,
    )


class SearchDiagnostics(HelModel):
    """Full Parameter Refinement's search diagnostics."""

    parameters: list[str] = Field(
        description=(
            "Order of the values in every list below: UTM easting (m), UTM "
            "northing (m), altitude (m), azimuth (deg), declination (deg), "
            "density (kg/m^3), speed (m/s)."
        )
    )
    scout_samples: list[list[float]] = Field(
        description="The Latin-hypercube scout samples, one list per sample, in parameters order."
    )
    scout_costs: list[float] = Field(
        description="Each scout sample's spline cost, m^2 (summed squared misses)."
    )
    sobol_first_order: list[float] = Field(description="First-order Sobol indices of the cost.")
    sobol_total: list[float] = Field(description="Total-order Sobol indices of the cost.")
    sobol_first_order_conf: list[float] | None = Field(
        default=None,
        description=(
            "95% confidence half-widths of sobol_first_order. From an "
            "unseeded bootstrap, so they differ from run to run."
        ),
    )
    sobol_total_conf: list[float] | None = Field(
        default=None, description="As sobol_first_order_conf, for sobol_total."
    )


class RadarSweep(HelModel):
    """One sweep of the radar file."""

    sweep_id: str = Field(description="The blip identifier this sweep gives, e.g. 'KGRR_3_0'.")
    radar: str = Field(description="Radar station identifier.")
    sweep_number: int = Field(description="Sweep number in its volume scan.")
    volume_scan_start_utc: UtcDatetime | None = Field(
        default=None, description="Start of the sweep's volume scan (UTC)."
    )
    sweep_elevation: float | None = Field(
        default=None, description="Antenna elevation above horizontal, degrees."
    )
    selected: bool = Field(description="True when the sweep was used in this run.")


class ReverseDiagnostic(HelModel):
    """A blip's offset carried back to the terminus.

    The fitted mass is flown from the terminus to the blip's altitude; the
    blip's horizontal offset from that crossing, moved to the terminus,
    shows where the terminus would sit to match this blip alone.
    """

    status: str = Field(
        description=(
            "'ok', or why it is missing (e.g. 'missing_mass', 'crossing_state_unavailable')."
        )
    )
    method: str = Field(description="How it was computed, e.g. 'forward_offset_diagnostic'.")
    reference_speed_mps: float = Field(description="Terminus speed used, m/s.")
    lat: float | None = Field(default=None, ge=-90.0, le=90.0, description=_LAT)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0, description=_LON)
    altitude_m: float | None = Field(default=None, description=_ELLIPSOIDAL)
    distance_to_terminus_m: float | None = Field(
        default=None, ge=0.0, description="Horizontal distance from the fitted terminus, metres."
    )
    time_s: float | None = Field(
        default=None, description="Flight time from the terminus to the blip's altitude, s."
    )


class BlipResult(HelModel):
    """One radar blip: what was observed, and the fragment that explains it."""

    blip_id: str = Field(description="Radar, sweep and index, e.g. 'KGRR_3_0'.")
    label: str = Field(
        description="Display name: radar, volume start HHMM, elevation (e.g. 'KGRR_0551_1.50')."
    )
    radar: str = Field(description="Radar station identifier.")
    sweep_number: int = Field(description="Sweep number in its volume scan.")
    observed_time_utc: UtcDatetime = Field(
        description="Reflectivity-weighted time of the blip (UTC)."
    )
    volume_scan_start_utc: UtcDatetime | None = Field(
        default=None, description="Start of the sweep's volume scan (UTC)."
    )
    volume_file_start_utc: UtcDatetime | None = Field(
        default=None, description="Start of the radar file holding the sweep (UTC)."
    )
    sweep_elevation: float | None = Field(
        default=None, description="Antenna elevation above horizontal, degrees."
    )
    sweep_mode: str | None = Field(
        default=None, description="Sweep type, e.g. 'single' or 'doppler'."
    )
    is_tdwr: bool = Field(description="True for a TDWR (C-band) station.")
    vcp_mode: str | None = Field(default=None, description="Volume coverage pattern.")
    lat: float = Field(ge=-90.0, le=90.0, description="Observed position. " + _LAT)
    lon: float = Field(ge=-180.0, le=180.0, description="Observed position. " + _LON)
    altitude_m: float = Field(description="Observed altitude. " + _ELLIPSOIDAL)
    range_to_radar_m: float = Field(ge=0.0, description="Distance from the radar, metres.")
    reflectivity_dbz: float | None = Field(
        default=None, description="The blip's strongest pixel reflectivity, dBZ."
    )
    z_min_dbz: float | None = Field(
        default=None,
        description=(
            "Mean detection floor of the blip's pixels, dBZ (dBZ0 + 20 log10 of the range in km)."
        ),
    )
    delta_z_db: float | None = Field(
        default=None, description="Largest margin of a pixel above its detection floor, dB."
    )
    time_after_terminus_s: float = Field(
        description="Observed time minus terminus time, s (negative before the terminus)."
    )
    status: BlipStatus = Field(
        description=(
            "'solved'; 'before_terminus' (observed before the terminus time); or 'solver_error'."
        )
    )
    status_detail: str | None = Field(default=None, description="Why the blip was not solved.")
    mass_kg: float | None = Field(
        default=None, ge=0.0, description="Fitted fragment mass, kg (0 when not solved)."
    )
    fragment_count: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Fragments of that mass the blip's reflectivity implies "
            "(dimensionless). Absent for Doppler sweeps and TDWR."
        ),
    )
    fall_time_s: float | None = Field(
        default=None, description="Flight time from the terminus to the ground, s."
    )
    time_residual_s: float | None = Field(
        default=None, description="Model arrival at the blip's altitude minus observed, s."
    )
    distance_residual_m: float | None = Field(
        default=None, ge=0.0, description="Horizontal miss at the blip's altitude, metres."
    )
    fit_cost: float | None = Field(
        default=None,
        ge=0.0,
        description="(time residual / 2 s)^2 + (distance residual / 250 m)^2 (dimensionless).",
    )
    crossing_utm_easting_m: float | None = Field(
        default=None,
        description="Where the fitted mass crossed the blip's altitude: UTM easting, m.",
    )
    crossing_utm_northing_m: float | None = Field(
        default=None, description="As crossing_utm_easting_m: UTM northing, m."
    )
    landing_lat: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description=(
            "Canonical landing site (radar-corrected; as calculated in "
            "Centerline Alignment, where an unsolved blip has none). " + _LAT
        ),
    )
    landing_lon: float | None = Field(
        default=None, ge=-180.0, le=180.0, description="As landing_lat. " + _LON
    )
    radar_corrected_landing_lat: float = Field(
        ge=-90.0,
        le=90.0,
        description="Landing flown on from the blip's observed position. " + _LAT,
    )
    radar_corrected_landing_lon: float = Field(
        ge=-180.0, le=180.0, description="As radar_corrected_landing_lat. " + _LON
    )
    reverse: ReverseDiagnostic | None = None


class PowerLawFit(HelModel):
    """Least-squares fit of log10 fragment count on log10 mass in grams."""

    slope_b: float = Field(description="Slope b of N = k * m^b (m in grams).")
    log10_intercept: float = Field(description="log10 k (m in grams).")
    slope_std_error: float = Field(ge=0.0, description="Standard error of the slope.")
    r2: float = Field(description="Coefficient of determination.")
    r2_adjusted: float = Field(description="R^2 adjusted for the fit's degrees of freedom.")
    n_points: int = Field(ge=3, description="Blips in the fit.")


class RegimeFit(HelModel):
    """A log10 count on log10 mass (grams) line for one scattering regime."""

    slope: float = Field(description="Slope (m in grams).")
    log10_intercept: float = Field(description="Intercept (m in grams).")
    r2: float = Field(description="Coefficient of determination.")


class Confidence(HelModel):
    """Informational confidence in the result (never gates a calculation)."""

    score: float = Field(ge=0.0, le=1.0, description="Product of the factors, 0 to 1.")
    tier: Literal["low", "medium", "high"] = Field(description="low < 0.2 <= medium < 0.5 <= high.")
    n_blips: int = Field(ge=0, description="Blips with a landing site.")
    n_radars: int = Field(ge=1, description="Radars counted.")
    centerline_ssr_m2: float | None = Field(
        default=None, ge=0.0, description="Squared cross-track misses of the landings, m^2."
    )
    centerline_rmse_m: float | None = Field(
        default=None, ge=0.0, description="Root-mean-square cross-track miss, metres."
    )
    blip_count_factor: float = Field(ge=0.0, le=1.0, description="From the number of blips.")
    spatial_consistency_factor: float | None = Field(
        default=None, ge=0.0, le=1.0, description="From the landings' scatter about the centreline."
    )
    radar_diversity_factor: float = Field(ge=0.0, le=1.0, description="From the number of radars.")


class Forensics(HelModel):
    """What the solved masses add up to."""

    radar_total_mass_kg: float = Field(
        ge=0.0, description="Sum of mass times fragment count over valid blips, kg."
    )
    findable_mass_kg: float = Field(
        ge=0.0, description="As radar_total_mass_kg, for fragments of 1 g and more, kg."
    )
    global_total_mass_kg: float = Field(
        ge=0.0, description="Pre-atmospheric mass times (1 - loss), kg."
    )
    power_law: PowerLawFit | None = None
    rayleigh_fit: RegimeFit | None = None
    mie_fit: RegimeFit | None = None
    transition_mass_kg: float = Field(
        gt=0.0,
        description="Rayleigh/Mie transition mass rho * lambda^3 / (6 pi^2) at S band, kg.",
    )
    empirical_transition_mass_kg: float | None = Field(
        default=None, gt=0.0, description="Where the two regime lines cross, kg."
    )
    empirical_density_kg_m3: float | None = Field(
        default=None, gt=0.0, description="The density that crossing implies, kg/m^3."
    )
    empirical_transition_in_sample: bool | None = Field(
        default=None,
        description="True when the crossing lies between the regimes' observed masses.",
    )
    largest_fragment_statistical_kg: float = Field(
        ge=0.0,
        description=(
            "Mass at which the power law reaches one fragment, kg (0 when the fit is poor)."
        ),
    )
    largest_fragment_radar_budget_kg: float = Field(
        ge=0.0,
        description="Largest fragment for which the power law holds the radar total, kg.",
    )
    largest_fragment_global_budget_kg: float = Field(
        ge=0.0,
        description="Largest fragment for which the power law holds the global total, kg.",
    )
    confidence: Confidence | None = None


class ReverseOffsets(HelModel):
    """Spread of the solved blips' reverse-diagnostic distances to the terminus."""

    median_m: float | None = Field(default=None, ge=0.0, description="Median, metres.")
    p90_m: float | None = Field(default=None, ge=0.0, description="90th percentile, metres.")
    max_m: float | None = Field(default=None, ge=0.0, description="Maximum, metres.")
    success_count: int = Field(ge=0, description="Solved blips with a diagnostic.")
    failed_count: int = Field(ge=0, description="Solved blips without one.")


class WindLevel(HelModel):
    """The wind at one altitude above the fitted terminus."""

    altitude_m: float = Field(description=_ELLIPSOIDAL)
    east_mps: float = Field(description="Eastward wind component (toward the east), m/s.")
    north_mps: float = Field(description="Northward wind component (toward the north), m/s.")
    speed_mps: float = Field(ge=0.0, description="Horizontal wind speed, m/s.")
    direction_from_deg: float = Field(
        ge=0.0,
        lt=360.0,
        description="Direction the wind blows from, degrees clockwise from true north.",
    )


class ScatteringModel(HelModel):
    """The fragment-count model's provenance."""

    name: str = Field(description="Model identifier, e.g. 'rayleigh_geometric_optics_v1'.")
    wavelength_m: float = Field(gt=0.0, description="Radar wavelength, metres.")
    band: str | None = Field(default=None, description="Radar band, e.g. 'S'.")
    k2_material: float = Field(gt=0.0, description="Dielectric factor |K|^2 of the material.")
    k2_water: float = Field(gt=0.0, description="Dielectric factor |K|^2 of water.")


class OutputFiles(HelModel):
    """The run's output files, as paths relative to the run folder."""

    full_kmz: str = Field(description="The full science KMZ.")
    contours_geojson: str | None = Field(
        default=None, description="Concentration contours (when the map layers were on)."
    )
    legacy_results: str | None = Field(
        default=None, description="The legacy-layout results file (Phase 1)."
    )


class ResultsDocument(HelModel):
    """A complete Fenrir results file."""

    contract: Literal["hel.results"] = Field(description="Contract name; always 'hel.results'.")
    contract_version: str = Field(description="Contract version, MAJOR.MINOR (e.g. '1.0').")
    event_id: str = Field(min_length=1, description="The fall's identifier, as in its event.json.")
    run: ResultsRunInfo
    inputs: AnalysisInputs
    terminus: FittedTerminus
    search: SearchDiagnostics | None = None
    radar_sweeps: list[RadarSweep]
    blips: list[BlipResult]
    forensics: Forensics | None = Field(default=None, description="Absent when no blip was solved.")
    reverse_offsets: ReverseOffsets
    wind_profile: list[WindLevel] = Field(
        description="The wind above the fitted terminus, from the ground up, every 250 m."
    )
    radar_detection_span_s: float | None = Field(
        default=None,
        ge=0.0,
        description="Time from the first to the last sweep start in the radar file, s.",
    )
    scattering_model: ScatteringModel
    files: OutputFiles

    @field_validator("contract_version")
    @classmethod
    def _version(cls, value: str) -> str:
        return check_contract_version(CONTRACT, value, SUPPORTED_MAJOR)
