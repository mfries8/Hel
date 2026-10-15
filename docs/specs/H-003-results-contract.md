# H-003: Fenrir Results Contract (`hel.results` 1.0)

## Status

In Progress

## Decisions

Fenrir D10 (one suite data contract, including Fenrir results), D26 (Hel
design; the results contract arrives with Fenrir F-011), D28 (units: computed
vs shown, decided 2026-10-15). Delivered together with Fenrir F-011b, which
writes the files.

## Context

Hel defines the input contracts (`hel.event`, `hel.radar`, `hel.seismo`).
Fenrir's results have no contract yet: the legacy code wrote an
un-versioned `Results.json` with legacy names (some with spaces), implied
units (grams, kilometres, `HHMM` text times) and duplicated fields. Other
apps (and the Fenrir frontend) need a stable, documented results file.

The field list was reviewed and approved by the maintainer on 2026-10-15
("Hel Results Contract" page), with these decisions (D28):

1. **Altitudes in this contract are heights above the WGS84 ellipsoid.**
   Displays convert to height above mean sea level. (The input contracts
   keep mean sea level.)
2. The mode that fits all parameters at once is
   `full_parameter_refinement`; "decadal series" is a technique, not a mode.
3. **Masses in kilograms.** Displays show grams below 1000 g.
4. Full Parameter Refinement's search diagnostics go in an optional
   `search` section.
5. (Fenrir) Phase 1 also writes the legacy layout as `legacy_results.json`.

## Scope

- `src/hel/results.py`: `ResultsDocument` and its parts (`run`, `inputs`,
  `terminus`, `search`, `radar_sweeps`, `blips`, `forensics`,
  `reverse_offsets`, `wind_profile`, `radar_detection_span_s`,
  `scattering_model`, `files`), every field with its units and reference
  direction, as on the approved page.
- `hel.load`/`hel validate` recognize `hel.results`; generated JSON Schema
  and TypeScript types.
- `docs/CONVENTIONS.md`: the contract's row, and the altitude exception
  (ellipsoidal heights in `hel.results`).
- Golden files: a minimal and a full example (the full one from a real
  Fenrir run of Park Forest, trimmed under 1 MB).
- Tests: the models, validation of the golden files, version rules.
- Release `v1.2.0` (MINOR: a new contract; existing contracts unchanged),
  tagged only after the maintainer confirms.

## Out Of Scope

- An upgrader for the legacy `Results.json` (nothing reads it besides the
  legacy code; Fenrir writes its legacy layout directly in Phase 1).
- Probabilistic (Monte Carlo) results: a later MINOR version.

## Affected Files

- `src/hel/results.py`, `src/hel/__init__.py`, `src/hel/validate.py`,
  `src/hel/cli.py` (if contract lists live there)
- `src/hel/schemas/results.schema.json`, `src/hel/types/hel.d.ts`
- `src/hel/golden/current/results_*.json`
- `tools/generate_artifacts.py`, `tests/test_contracts.py`
- `docs/CONVENTIONS.md`, `docs/KANBAN.md`, `CHANGELOG.md`, `pyproject.toml`
  (version), this SPEC

## Acceptance Criteria

- [x] `hel.results` 1.0 models match the approved field list, with units and
      reference directions in every description (one change: Deviations).
- [x] Schemas and types regenerate cleanly (`generate_artifacts.py --check`).
- [x] Golden results files validate; a wrong contract name, an unknown MAJOR
      version, or a missing required field is rejected.
- [x] `python tools/run_ci.py` passes.
- [ ] Tagged `v1.2.0` after the maintainer's go-ahead.

## Verification Plan

- `python tools/run_ci.py`

## Verification Results

- `python tools/run_ci.py` (Hel `.venv`): all checks pass; 105 passed,
  coverage 98%. Schemas and TypeScript types current (the types compile with
  `tsc --strict`).
- Golden: `results_minimal.json` (hand-written) and `results_full.json` (a
  real Park Forest Full Parameter Refinement result from Fenrir F-011b,
  102 KB) validate with no warnings and round-trip.
- Fenrir F-011b: `results.json` for all 12 real-fall runs validates, and
  its fields in every section (terminus, blips, forensics, offsets, wind
  profile, provenance) equal their legacy sources after the D28 conversions.

## Deviations

- **`blips[].landing_lat`/`landing_lon` are optional** (the approved list
  showed them required). In Centerline Alignment the canonical landing is
  the calculated one, so a blip observed before the terminus time has none
  (found on Park Forest). Absent means not recorded.
- **Upgrader dispatch order** (CHANGELOG): a results file has a `terminus`
  field, which the upgrader took as a legacy event layout; files are now
  identified by their header first. Found by this SPEC's tests.
- The run section is the model `ResultsRunInfo` (TypeScript
  `ResultsRunInfo`): `RunInfo` already names `hel.seismo`'s run record, and
  TypeScript merges same-named declarations.
- The search ranges are an object with one optional entry per searched
  value, not a map keyed by name (a keyed map gave TypeScript two index
  signatures).

## Follow-Up Work Discovered

- Tag `v1.2.0` after the maintainer's go-ahead; Fenrir then syncs its pin.

## Checks Skipped

- None
