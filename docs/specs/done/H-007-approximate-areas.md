# H-007: Approximate Probability Areas in the Results Contract (`hel.results` 1.4)

## Status

Done (2026-10-26)

## Decisions

Fenrir D19 (Level 1). The maintainer, 2026-10-26 (Fenrir F-029, option B):
when a fall has no more blips than free parameters, Level 1 still draws
its areas, from a typical fit error, and says they are approximate.

## Context

Fenrir F-028 found that falls with 1-3 blips got near-zero fit errors and
tiny areas. Fenrir F-029 draws approximate areas instead; the results file
needs to say so.

## Scope

- `hel.results` **1.4** (MINOR: optional field): `uncertainty.fit_quality.
  approximate`, why the areas are approximate, or absent.
- Schema, TypeScript types, the full golden file, a test; package 1.7.0.

## Out Of Scope

- Fenrir's writing of the field (Fenrir F-029).

## Affected Files

- `src/hel/results.py`, `src/hel/schemas/results.schema.json`,
  `src/hel/types/hel.d.ts`, `src/hel/golden/current/results_full.json`,
  `src/hel/__init__.py`, `pyproject.toml`, `tests/test_contracts.py`,
  `tests/test_scaffold.py`, `CHANGELOG.md`, `docs/KANBAN.md`, this SPEC

## Acceptance Criteria

- [x] The field validates; a 1.3 file still validates.
- [x] `python tools/run_ci.py` passes.

## Verification Plan

- `python tools/run_ci.py`

## Verification Results

- `python tools/run_ci.py`: All checks passed.

## Deviations

- None

## Follow-Up Work Discovered

- None

## Checks Skipped

- None
