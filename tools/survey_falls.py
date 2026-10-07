"""Upgrade and validate every contract file under a folder of falls.

A local check, not part of CI (the falls archive is not in the repository).
It is how Hel is shown to handle every real file the suite has written
(F-003 acceptance criterion):

    python tools/survey_falls.py --root "PATH/TO/AAA_falls"

It looks for ``event*.json``, ``RADAR_*.json`` (case-sensitive, so similarly
named non-radar files are skipped) and ``Loki_output/seismo.json``, upgrades
each in memory, validates it, and prints counts by contract and layout plus
every failure. Nothing is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from hel import ContractValidationError, NotAContractFileError, upgrade_and_validate


def contract_files(root: Path) -> list[Path]:
    """Find the candidate contract files under ``root``.

    Args:
        root: Folder to search recursively.

    Returns:
        Matching paths, sorted.
    """
    found: set[Path] = set()
    for path in root.rglob("*.json"):
        name = path.name
        if name.startswith("event") or name.startswith("RADAR_"):
            found.add(path)
        elif name == "seismo.json" and path.parent.name == "Loki_output":
            found.add(path)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    """Run the survey and print the summary.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 when every file upgraded and validated, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, required=True, help="Folder of falls to survey.")
    args = parser.parse_args(argv)

    outcomes: Counter[str] = Counter()
    warned: Counter[str] = Counter()
    failures: list[str] = []
    for path in contract_files(args.root):
        rel = path.relative_to(args.root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            loaded = upgrade_and_validate(data)
        except (json.JSONDecodeError, NotAContractFileError, ContractValidationError) as exc:
            failures.append(f"{rel}\n    {type(exc).__name__}: {exc}")
            outcomes["FAILED"] += 1
            continue
        outcomes[f"{loaded.contract} ({loaded.upgrade.layout})"] += 1
        for warning in loaded.warnings:
            warned[f"{loaded.contract}: {warning.split(' (x')[0]}"] += 1

    print(f"Surveyed {sum(outcomes.values())} files under {args.root}")
    for outcome, n in sorted(outcomes.items()):
        print(f"  {n:5d}  {outcome}")
    if warned:
        print("Unknown fields kept (files affected):")
        for warning, n in warned.most_common():
            print(f"  {n:5d}  {warning}")
    for failure in failures:
        print(f"FAILED {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
