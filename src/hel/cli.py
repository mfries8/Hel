"""The ``hel`` command: validate and upgrade contract files.

    hel validate FILE [FILE ...]      check files (legacy files are upgraded in memory first)
    hel upgrade FILE --out NEWFILE    write the upgraded file to a new path
    hel versions                      list the contracts and versions this Hel writes

``hel upgrade`` never writes over a file, including its input: the original
is kept so the conversion can always be checked or redone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hel import CONTRACT_VERSIONS, __version__
from hel.upgrade import NotAContractFileError
from hel.validate import ContractValidationError, load


def _cmd_validate(files: list[Path]) -> int:
    """Validate each file and print one verdict per file.

    Args:
        files: Paths to check.

    Returns:
        0 when every file is valid, 1 otherwise.
    """
    failed = 0
    for path in files:
        try:
            loaded = load(path)
        except (
            OSError,
            json.JSONDecodeError,
            NotAContractFileError,
            ContractValidationError,
        ) as exc:
            print(f"FAIL {path}: {exc}")
            failed += 1
            continue
        note = ""
        if loaded.upgrade.changed:
            note = f" (legacy layout '{loaded.upgrade.layout}'; run 'hel upgrade')"
        print(f"OK   {path}: {loaded.contract} {loaded.document.contract_version}{note}")
        for warning in loaded.warnings:
            print(f"     unknown field kept: {warning}")
    return 1 if failed else 0


def _cmd_upgrade(source: Path, out: Path, force: bool) -> int:
    """Upgrade one file and write the result to a new path.

    Args:
        source: The file to upgrade.
        out: Where to write the upgraded file.
        force: Allow replacing an existing ``out`` (never ``source`` itself).

    Returns:
        0 on success, 1 on failure.
    """
    if out.resolve() == source.resolve():
        print("FAIL: --out must be a new file; hel upgrade never overwrites its input")
        return 1
    if out.exists() and not force:
        print(f"FAIL: {out} exists; choose another path or pass --force")
        return 1
    try:
        loaded = load(source)
    except (OSError, json.JSONDecodeError, NotAContractFileError, ContractValidationError) as exc:
        print(f"FAIL {source}: {exc}")
        return 1
    # Write the upgrader's own output, not a re-serialized model, so values it
    # did not touch are written exactly as they were read.
    out.write_text(
        json.dumps(loaded.upgrade.document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} ({loaded.contract} {loaded.document.contract_version})")
    for change in loaded.upgrade.changes or ["no changes: already current"]:
        print(f"  - {change}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the ``hel`` command.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(prog="hel", description="Yggdrasil suite data contracts.")
    parser.add_argument("--version", action="version", version=f"hel {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="validate contract files")
    check.add_argument("files", nargs="+", type=Path)
    convert = commands.add_parser("upgrade", help="upgrade a legacy file to a new file")
    convert.add_argument("file", type=Path)
    convert.add_argument("--out", type=Path, required=True, help="path for the upgraded file")
    convert.add_argument("--force", action="store_true", help="replace an existing --out file")
    commands.add_parser("versions", help="list contract versions")
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _cmd_validate(args.files)
    if args.command == "upgrade":
        return _cmd_upgrade(args.file, args.out, args.force)
    for contract, version in CONTRACT_VERSIONS.items():
        print(f"{contract} {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
