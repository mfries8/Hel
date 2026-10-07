"""Validate contract files, and load them in one step with upgrade.

Producers validate before saving; readers validate on load (Fenrir D10).
``load`` is what an app normally calls: it reads a file, upgrades it if it's a
legacy layout (``hel.upgrade``), validates it, and returns the model with the
upgrade's change record and any warnings.

Validation errors raise ``ContractValidationError`` with every problem listed.
Unknown fields are not errors (the MINOR-version reader rule) but come back as
warnings, so a typo in a producer's field name does not go unnoticed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from hel.event import EventDocument
from hel.radar import RadarDocument
from hel.seismo import SeismoDocument
from hel.upgrade import UpgradeResult, upgrade

ContractDocument = EventDocument | RadarDocument | SeismoDocument

MODELS: dict[str, type[EventDocument] | type[RadarDocument] | type[SeismoDocument]] = {
    "hel.event": EventDocument,
    "hel.radar": RadarDocument,
    "hel.seismo": SeismoDocument,
}

# Unknown-field warnings stop after this many, so a file with the same unknown
# field on every one of thousands of pixels gives a readable report.
MAX_WARNINGS = 50


class ContractValidationError(ValueError):
    """Raised when data does not satisfy its contract.

    Attributes:
        contract: The contract checked, e.g. ``"hel.radar"``.
        problems: One line per problem: location and message.
    """

    def __init__(self, contract: str, problems: list[str]) -> None:
        self.contract = contract
        self.problems = problems
        shown = "\n  ".join(problems[:20])
        more = f"\n  ... and {len(problems) - 20} more" if len(problems) > 20 else ""
        super().__init__(f"{contract}: {len(problems)} problem(s)\n  {shown}{more}")


@dataclass
class Loaded:
    """A validated contract file.

    Attributes:
        contract: The contract name.
        document: The validated model.
        upgrade: The upgrade record (``upgrade.changed`` is False for a file
            that was already current).
        warnings: Unknown fields found, as ``location: field`` lines.
    """

    contract: str
    document: ContractDocument
    upgrade: UpgradeResult
    warnings: list[str] = field(default_factory=list)


def validate(data: Any) -> tuple[ContractDocument, list[str]]:
    """Validate data that carries a Hel header (no upgrading).

    Args:
        data: Parsed JSON with ``contract`` and ``contract_version``.

    Returns:
        The validated model and the unknown-field warnings.

    Raises:
        ContractValidationError: If the header is missing or unknown, or the
            data breaks its contract.
    """
    contract = data.get("contract") if isinstance(data, dict) else None
    model = MODELS.get(contract) if isinstance(contract, str) else None
    if model is None:
        raise ContractValidationError(
            str(contract), [f"unknown or missing 'contract' header: {contract!r}"]
        )
    try:
        document = model.model_validate(data)
    except ValidationError as exc:
        problems = [
            f"{'.'.join(str(p) for p in err['loc']) or '(top level)'}: {err['msg']}"
            for err in exc.errors()
        ]
        raise ContractValidationError(str(contract), problems) from exc
    return document, unknown_fields(document)


def upgrade_and_validate(data: Any) -> Loaded:
    """Upgrade (if needed) and validate parsed JSON.

    Args:
        data: Parsed JSON of any contract, current or legacy.

    Returns:
        The validated file, its upgrade record and warnings.

    Raises:
        NotAContractFileError: If the data matches no contract (from ``upgrade``).
        ContractValidationError: If the upgraded data breaks its contract.
    """
    result = upgrade(data)
    document, warnings = validate(result.document)
    return Loaded(result.contract, document, result, warnings)


def load(path: str | Path) -> Loaded:
    """Read, upgrade (if needed) and validate one contract file.

    Args:
        path: Path to an event, radar or seismo JSON file.

    Returns:
        The validated file, its upgrade record and warnings.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If it is not valid JSON.
        NotAContractFileError: If it matches no contract.
        ContractValidationError: If it breaks its contract.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return upgrade_and_validate(data)


def unknown_fields(model: BaseModel) -> list[str]:
    """List fields that no contract model declares, wherever they occur.

    Repeated occurrences of the same field at the same place (for example on
    every pixel) are reported once, with a count.

    Args:
        model: A validated contract model.

    Returns:
        Lines like ``"sweeps[].pixels[]: 'sweep_note' (x120)"``, at most
        ``MAX_WARNINGS`` of them.
    """
    counts: dict[str, int] = {}

    def walk(obj: Any, where: str) -> None:
        if isinstance(obj, BaseModel):
            for key in obj.model_extra or {}:
                line = f"{where or '(top level)'}: '{key}'"
                counts[line] = counts.get(line, 0) + 1
            for name in type(obj).model_fields:
                walk(getattr(obj, name), f"{where}.{name}" if where else name)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, f"{where}[]")

    walk(model, "")
    lines = [f"{line} (x{n})" if n > 1 else line for line, n in counts.items()]
    return lines[:MAX_WARNINGS]
