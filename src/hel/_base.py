"""Building blocks shared by every Hel contract.

Each contract file (``event.json``, ``RADAR_*.json``, ``seismo.json``) is a
pydantic model built from the pieces here:

- ``HelModel``: the base class. Unknown fields are **kept, not rejected**, so a
  reader of version 1.0 can load a 1.1 file that added optional fields (the
  MINOR-version rule in ``docs/CONVENTIONS.md``). ``hel validate`` still
  reports unknown fields as warnings, so producers notice typos.
- ``UtcDatetime``: a time that must carry a UTC designator. Times with no
  time zone are rejected here; ``hel upgrade`` is the one place that converts
  legacy zone-less times, and it records that it did.
- ``check_contract_version``: the reader rule. A reader accepts any MINOR
  version of the MAJOR version it was written for.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, PlainSerializer

# MAJOR.MINOR, e.g. "1.0". Patch numbers are not used in contract versions:
# a change either adds optional fields (MINOR) or breaks readers (MAJOR).
CONTRACT_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)$")


class HelModel(BaseModel):
    """Base class for every contract object.

    Unknown fields are preserved on load and written back on save, so files
    from a newer MINOR version round-trip through older readers without loss.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize for saving: only the fields present, times ending in ``Z``.

        Optional fields that were never set are left out rather than written
        as ``null``, matching the contract rule that an absent field means
        "not recorded".

        Args:
            indent: JSON indentation; None for compact output.

        Returns:
            The JSON text.
        """
        return self.model_dump_json(exclude_unset=True, indent=indent)


def _require_utc(value: datetime) -> datetime:
    """Accept only timezone-aware UTC times, normalized to UTC.

    Args:
        value: The parsed time.

    Returns:
        The same instant with ``tzinfo=UTC``.

    Raises:
        ValueError: If the time has no time zone, or a non-zero UTC offset.
    """
    offset = value.utcoffset()
    if offset is None:
        raise ValueError(
            "time has no time zone; contract times end in 'Z' (run 'hel upgrade' "
            "to convert a legacy file, which treats zone-less times as UTC)"
        )
    if offset != timedelta(0):
        raise ValueError("time is not UTC; contract times end in 'Z'")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    """Serialize a UTC time as ISO 8601 with a ``Z`` suffix.

    Whole seconds are written without a fraction; otherwise the fraction is
    written to the microsecond with trailing zeros removed, so a time read as
    ``05:51:55.402Z`` is written back as ``05:51:55.402Z``.

    Args:
        value: A timezone-aware UTC time.

    Returns:
        The ISO 8601 string, e.g. ``"2003-03-27T05:51:55.402Z"``.
    """
    text = value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    if value.microsecond:
        text += f".{value.microsecond:06d}".rstrip("0")
    return text + "Z"


# A UTC instant: ISO 8601 ending in "Z" in JSON, an aware datetime in Python.
UtcDatetime = Annotated[
    datetime,
    AfterValidator(_require_utc),
    PlainSerializer(_format_utc, return_type=str, when_used="json"),
]


def check_contract_version(contract: str, version: str, supported_major: int) -> str:
    """Apply the reader rule: same MAJOR version, any MINOR version.

    Args:
        contract: Contract name, e.g. ``"hel.event"``, for the error message.
        version: The file's ``contract_version``, e.g. ``"1.0"``.
        supported_major: The MAJOR version this reader understands.

    Returns:
        ``version`` unchanged, when it is acceptable.

    Raises:
        ValueError: If ``version`` is not ``MAJOR.MINOR`` or has another MAJOR.
    """
    match = CONTRACT_VERSION_PATTERN.match(version)
    if match is None:
        raise ValueError(f"{contract}: contract_version {version!r} is not MAJOR.MINOR")
    if int(match.group(1)) != supported_major:
        raise ValueError(
            f"{contract}: contract_version {version} has MAJOR version {match.group(1)}; "
            f"this reader supports {supported_major}.x only"
        )
    return version
