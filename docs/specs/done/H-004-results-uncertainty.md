# H-004: Probability Areas in the Results Contract (`hel.results` 1.1)

## Status

Done (2026-10-25)

## Decisions

Fenrir D19 (Level 1 probability areas, search grid, error tables), D5
(probability-based results first), D5a (the error tables), D17 (geometry
penalties reported, not scored), D10/D26 (one suite data contract). With
Fenrir F-025b, which writes the section; the maintainer, 2026-10-24: put
Level 1's areas on Fenrir's Search Map.

## Context

Fenrir F-025a computes Level 1 uncertainty (each blip's 50 %/90 % landing
ellipses, highest-density regions per decadal mass class and for the fall,
a search grid, parameter uncertainties, error tables), but `hel.results`
1.0 has nowhere to put them, and Fenrir refuses undeclared results fields.
F-020's search fields (the cost used, the blips behind the terminus) were
held back for the same reason.

## Scope

- `hel.results` **1.1** (MINOR: optional fields only):
  - `uncertainty` (optional): `method`, `samples`, `area_scale` (the
    calibration factor, 1 when none), `fit_quality`, `parameters` (value,
    σ, capped at the search range), `correlations`, `error_table` (per
    decadal mass class), `blip_areas` (per blip, its probability
    ellipses), `regions` (per class and `fall`: probability, area,
    outlines), `search_grid` (cells and their probabilities),
    `sources_included`, `sources_excluded`;
  - `search.cost`, `search.blips_behind_terminus`;
  - `files.uncertainty_kmz`, `files.areas_geojson`.
- The generated schema and TypeScript types; the full golden file with an
  example section; tests; package 1.4.0.

## Out Of Scope

- Fenrir's writing of the section (Fenrir F-025b).

## Affected Files

- `src/hel/results.py`, `src/hel/schemas/results.schema.json`,
  `src/hel/types/hel.d.ts`, `src/hel/golden/current/results_full.json`,
  `src/hel/__init__.py`, `pyproject.toml`
- `tests/test_contracts.py`
- `CHANGELOG.md`, `docs/KANBAN.md`, this SPEC

## Acceptance Criteria

- [x] The new fields validate; a 1.0 file still validates.
- [x] `python tools/run_ci.py` passes.

## Verification Plan

- `python tools/run_ci.py`

## Verification Results

- `python tools/run_ci.py`: All checks passed (106 tests, coverage 98 %).

## Deviations

- None

## Follow-Up Work Discovered

- None

## Checks Skipped

- None
