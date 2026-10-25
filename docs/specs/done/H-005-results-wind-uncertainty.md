# H-005: The Wind's Share in the Results Contract (`hel.results` 1.2)

## Status

Done (2026-10-25)

## Decisions

Fenrir D20 (wind uncertainty: the ERA5 ensemble, a re-fit per member, the
wind's share shown in the error tables), D5a (the error tables), D10/D26
(one suite data contract). With Fenrir F-026a, which writes the fields.

## Context

Fenrir F-026a re-fits each run in each ERA5 ensemble member's wind and
measures the wind's share of every mass class's landing error, but
`hel.results` 1.1 has nowhere to put either.

## Scope

- `hel.results` **1.2** (MINOR: optional fields only):
  - `uncertainty.error_table[].wind_share` (0–1): the share of the class's
    landing variance from the wind;
  - `uncertainty.wind` (`WindUncertainty`): the source, the member count,
    whether the fit was re-run per member, and each member's re-fit
    (`MemberFit`: its horizontal and height shift from the main fit, its
    cost).
- The generated schema and TypeScript types; the full golden file with an
  example; tests; package 1.5.0.

## Out Of Scope

- Fenrir's writing of the fields (Fenrir F-026a).

## Affected Files

- `src/hel/results.py`, `src/hel/schemas/results.schema.json`,
  `src/hel/types/hel.d.ts`, `src/hel/golden/current/results_full.json`,
  `src/hel/__init__.py`, `pyproject.toml`
- `tests/test_contracts.py`, `tests/test_scaffold.py`
- `CHANGELOG.md`, `docs/KANBAN.md`, this SPEC

## Acceptance Criteria

- [x] The new fields validate, a share outside 0–1 is refused, and a 1.1
      file still validates.
- [x] `python tools/run_ci.py` passes.

## Verification Plan

- `python tools/run_ci.py`

## Verification Results

- `python tools/run_ci.py`: All checks passed (107 tests, coverage 98 %).

## Deviations

- None

## Follow-Up Work Discovered

- None

## Checks Skipped

- None
