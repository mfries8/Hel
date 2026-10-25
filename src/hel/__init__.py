"""Hel: the shared data contracts of the Yggdrasil meteorite-fall suite.

Gjallerhorn (radar extraction), Loki (seismo-acoustics) and Fenrir (dark-flight
analysis) exchange four kinds of file, each defined here as a versioned
contract:

- ``hel.event`` (``event.json``): what is known about a fall;
- ``hel.radar`` (``RADAR_*.json``): the selected radar signatures;
- ``hel.seismo`` (``seismo.json``): Loki's seismo-acoustic evidence and trajectory;
- ``hel.results`` (``results.json``): what Fenrir found for one run.

Typical use, in any app::

    import hel
    loaded = hel.load("event.json")  # upgrades legacy files, then validates
    loaded.document                   # the validated model
    loaded.upgrade.changes            # what the upgrader changed, if anything

Each app keeps a pinned copy of this package (decision D26); edit Hel itself,
never an app's copy. The rules every contract follows are in
``docs/CONVENTIONS.md``.
"""

from __future__ import annotations

from hel import event, radar, results, seismo
from hel.upgrade import NotAContractFileError, UpgradeResult, upgrade
from hel.validate import (
    ContractValidationError,
    Loaded,
    load,
    upgrade_and_validate,
    validate,
)

__version__ = "1.6.0"

# Every contract and the version this release of Hel writes.
CONTRACT_VERSIONS: dict[str, str] = {
    event.CONTRACT: event.CONTRACT_VERSION,
    radar.CONTRACT: radar.CONTRACT_VERSION,
    seismo.CONTRACT: seismo.CONTRACT_VERSION,
    results.CONTRACT: results.CONTRACT_VERSION,
}

__all__ = [
    "CONTRACT_VERSIONS",
    "ContractValidationError",
    "Loaded",
    "NotAContractFileError",
    "UpgradeResult",
    "__version__",
    "event",
    "load",
    "radar",
    "results",
    "seismo",
    "upgrade",
    "upgrade_and_validate",
    "validate",
]
