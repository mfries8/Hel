"""The ``event.json`` contract (``hel.event``): what is known about a fall.

An event file describes one meteorite fall as the analyst knows it before any
analysis: where and when the luminous flight ended, optionally where it began,
the assumed meteorite properties, and any recovered meteorites. Fenrir reads
it as the starting point of dark-flight analysis; Loki reads it as the prior
for its trajectory inversion.

Conventions (``docs/CONVENTIONS.md``): times are UTC ending in ``Z``; altitude
is metres above mean sea level; azimuth is the direction of travel in degrees
clockwise from true north; declination is degrees below horizontal.

Version history:

- **1.0** (2026-10-06): first version. Replaces the legacy un-versioned
  layouts (``terminus`` or ``luminous_end`` blocks, with an ambiguous
  ``speed_mps``); ``hel upgrade`` converts them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from hel._base import HelModel, UtcDatetime, check_contract_version

CONTRACT = "hel.event"
CONTRACT_VERSION = "1.0"
SUPPORTED_MAJOR = 1


class LuminousEnd(HelModel):
    """The end of the luminous (bright) flight: where dark flight begins.

    This is the terminus that dark-flight analysis starts from, and the prior
    that Loki's inversion refines.
    """

    time_utc: UtcDatetime = Field(description="Time of the luminous-flight end (UTC).")
    lat: float = Field(ge=-90.0, le=90.0, description="Latitude, degrees north (WGS84).")
    lon: float = Field(ge=-180.0, le=180.0, description="Longitude, degrees east (WGS84).")
    altitude_m: float = Field(gt=0.0, description="Altitude above mean sea level, metres.")
    terminus_speed_mps: float = Field(
        gt=0.0,
        description=(
            "Speed at the luminous-flight end, m/s. Often an assumed value "
            "(conventionally 3000 m/s) rather than a measurement."
        ),
    )
    azimuth_deg: float = Field(
        ge=0.0,
        le=360.0,
        description=(
            "Direction of travel, degrees clockwise from true north (not the "
            "radiant direction, which differs by 180 degrees)."
        ),
    )
    declination_deg: float = Field(
        ge=0.0, le=90.0, description="Trajectory angle below horizontal, degrees (90 = vertical)."
    )


class LuminousStart(HelModel):
    """The beginning of the luminous flight, when it was observed."""

    time_utc: UtcDatetime = Field(description="Time of the luminous-flight start (UTC).")
    lat: float = Field(ge=-90.0, le=90.0, description="Latitude, degrees north (WGS84).")
    lon: float = Field(ge=-180.0, le=180.0, description="Longitude, degrees east (WGS84).")
    altitude_m: float = Field(gt=0.0, description="Altitude above mean sea level, metres.")
    entry_speed_mps: float | None = Field(
        default=None, gt=0.0, description="Speed at the luminous-flight start, m/s."
    )
    azimuth_deg: float | None = Field(
        default=None,
        ge=0.0,
        le=360.0,
        description="Direction of travel, degrees clockwise from true north.",
    )
    declination_deg: float | None = Field(
        default=None, ge=0.0, le=90.0, description="Trajectory angle below horizontal, degrees."
    )


class TrajectoryPoint(HelModel):
    """One observed point on the luminous trajectory."""

    time_utc: UtcDatetime = Field(description="Time at this point (UTC).")
    lat: float = Field(ge=-90.0, le=90.0, description="Latitude, degrees north (WGS84).")
    lon: float = Field(ge=-180.0, le=180.0, description="Longitude, degrees east (WGS84).")
    altitude_m: float = Field(gt=0.0, description="Altitude above mean sea level, metres.")
    speed_mps: float | None = Field(
        default=None, gt=0.0, description="Speed at this point along the trajectory, m/s."
    )


class MeteoriteProperties(HelModel):
    """Assumed or known properties of the meteoroid and its fragments."""

    density_kg_m3: float | None = Field(
        default=None, gt=0.0, description="Bulk density used for analysis, kg/m^3."
    )
    density_mode: Literal["literature", "known", "unknown"] | None = Field(
        default=None,
        description=(
            "Where density_kg_m3 comes from: 'known' (measured on recovered "
            "meteorites), 'literature' (a class average), or 'unknown' (a default)."
        ),
    )
    k2_factor: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Dielectric factor |K|^2 used for radar reflectivity (dimensionless).",
    )
    shape_factor: float | None = Field(
        default=None,
        gt=0.0,
        description="Shape factor A = area / volume^(2/3) (dimensionless; global value).",
    )
    pre_atmospheric_mass_kg: float | None = Field(
        default=None, gt=0.0, description="Estimated pre-atmospheric mass, kg."
    )
    solved_density_kg_m3: float | None = Field(
        default=None,
        gt=0.0,
        description="Density solved by a previous analysis, kg/m^3. A result, not an input.",
    )
    toughness_index: float | None = Field(
        default=None, description="Toughness index from a previous analysis (dimensionless)."
    )


class Find(HelModel):
    """One recovered meteorite."""

    lat: float = Field(ge=-90.0, le=90.0, description="Latitude, degrees north (WGS84).")
    lon: float = Field(ge=-180.0, le=180.0, description="Longitude, degrees east (WGS84).")
    mass_kg: float = Field(ge=0.0, description="Recovered mass, kg.")


class EventDocument(HelModel):
    """A complete ``event.json`` file."""

    contract: Literal["hel.event"] = Field(description="Contract name; always 'hel.event'.")
    contract_version: str = Field(description="Contract version, MAJOR.MINOR (e.g. '1.0').")
    event_id: str = Field(min_length=1, description="Short identifier for the fall.")
    luminous_end: LuminousEnd
    luminous_start: LuminousStart | None = None
    luminous_trajectory: list[TrajectoryPoint] | None = None
    entry_speed_mps: float | None = Field(
        default=None, gt=0.0, description="Speed at atmospheric entry, m/s."
    )
    meteorite_properties: MeteoriteProperties | None = None
    mass_lost_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Share of the pre-atmospheric mass lost in bright flight, percent.",
    )
    radar_duration_s: float | None = Field(
        default=None,
        ge=0.0,
        description="Time after the terminus over which radar signatures are sought, s.",
    )
    radar_duration_nexrad_s: float | None = Field(
        default=None,
        ge=0.0,
        description="As radar_duration_s, for NEXRAD radars specifically, s.",
    )
    tnt_equivalent_kt: float | None = Field(
        default=None, ge=0.0, description="Energy of the fireball, kilotons of TNT."
    )
    finds: list[Find] | None = Field(
        default=None,
        description=(
            "Recovered meteorites. Absent means not recorded; an empty list means none recovered."
        ),
    )

    @field_validator("contract_version")
    @classmethod
    def _version(cls, value: str) -> str:
        return check_contract_version(CONTRACT, value, SUPPORTED_MAJOR)

    @field_validator("event_id")
    @classmethod
    def _event_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("event_id must not be blank")
        return value
