"""Generate Hel's JSON Schemas and TypeScript types from the contract models.

The pydantic models in ``src/hel`` are the single source of truth (decision
D26). This tool writes, from them:

- ``src/hel/schemas/<contract>.schema.json``: one JSON Schema per contract,
  for non-Python readers and for documentation;
- ``src/hel/types/hel.d.ts``: TypeScript types for the frontends, compiled
  from those schemas by ``tools/schema_to_ts.mjs`` (needs Node and
  ``npm install``).

    python tools/generate_artifacts.py           # regenerate
    python tools/generate_artifacts.py --check   # fail if anything is stale (CI)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema

from hel.event import EventDocument
from hel.radar import RadarDocument
from hel.results import ResultsDocument
from hel.seismo import SeismoDocument

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "src" / "hel"
SCHEMA_DIR = PACKAGE / "schemas"
TYPES_FILE = PACKAGE / "types" / "hel.d.ts"

DOCUMENTS: dict[str, type[BaseModel]] = {
    "event": EventDocument,
    "radar": RadarDocument,
    "seismo": SeismoDocument,
    "results": ResultsDocument,
}


class _NoFieldTitles(GenerateJsonSchema):
    """JSON Schema without per-field titles.

    Pydantic titles every field ("Lat", "Lon", ...). The TypeScript generator
    turns each title into its own exported type, which buries the real types
    and collides across contracts; the descriptions already say what each
    field means.
    """

    def field_title_should_be_set(self, schema: object) -> bool:  # noqa: D102
        return False


def schema_texts() -> dict[str, str]:
    """Build every contract's JSON Schema text.

    Returns:
        File name to JSON text, e.g. ``{"event.schema.json": "{...}"}``.
    """
    texts: dict[str, str] = {}
    for name, model in DOCUMENTS.items():
        schema = model.model_json_schema(mode="validation", schema_generator=_NoFieldTitles)
        contract = f"hel.{name}"
        module = sys.modules[model.__module__]
        header = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{contract}/{module.CONTRACT_VERSION}",
            "title": schema.pop("title"),
        }
        texts[f"{name}.schema.json"] = json.dumps({**header, **schema}, indent=2) + "\n"
    return texts


def types_text(schema_dir: Path) -> str:
    """Compile the schemas in ``schema_dir`` into TypeScript declarations.

    Args:
        schema_dir: Folder holding the ``*.schema.json`` files.

    Returns:
        The ``.d.ts`` text.

    Raises:
        RuntimeError: If Node or the generator is missing.
    """
    node = shutil.which("node")
    if node is None or not (REPO_ROOT / "node_modules" / "json-schema-to-typescript").is_dir():
        raise RuntimeError("TypeScript generation needs Node and 'npm install' in the Hel repo")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "hel.d.ts"
        subprocess.run(
            [node, str(REPO_ROOT / "tools" / "schema_to_ts.mjs"), str(schema_dir), str(out)],
            cwd=REPO_ROOT,
            check=True,
        )
        text = out.read_text(encoding="utf-8")
        # Prove the declarations compile, so a broken type file never ships.
        # A throwaway tsconfig keeps the check to this one file (no ambient
        # @types packages from node_modules).
        config = {
            "compilerOptions": {"strict": True, "noEmit": True, "types": [], "lib": ["es2022"]},
            "files": ["hel.d.ts"],
        }
        (Path(tmp) / "tsconfig.json").write_text(json.dumps(config), encoding="utf-8")
        tsc = REPO_ROOT / "node_modules" / "typescript" / "bin" / "tsc"
        subprocess.run([node, str(tsc), "-p", tmp], cwd=REPO_ROOT, check=True)
        return text


def main(argv: list[str] | None = None) -> int:
    """Regenerate the artifacts, or check that they are current.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 on success; 1 when ``--check`` finds a stale or missing file.
    """
    parser = argparse.ArgumentParser(description="Generate Hel schemas and TypeScript types.")
    parser.add_argument("--check", action="store_true", help="fail if anything is out of date")
    args = parser.parse_args(argv)

    wanted = {SCHEMA_DIR / name: text for name, text in schema_texts().items()}
    with tempfile.TemporaryDirectory() as tmp:
        for path, text in wanted.items():
            (Path(tmp) / path.name).write_bytes(text.encode("utf-8"))
        wanted[TYPES_FILE] = types_text(Path(tmp))

    stale = [
        path
        for path, text in wanted.items()
        if not path.is_file() or path.read_bytes().decode("utf-8") != text
    ]
    if args.check:
        for path in stale:
            print(f"stale: {path.relative_to(REPO_ROOT).as_posix()}")
        if stale:
            print("Run: python tools/generate_artifacts.py")
            return 1
        print("Generated artifacts are current.")
        return 0
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(wanted[path].encode("utf-8"))
        print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
