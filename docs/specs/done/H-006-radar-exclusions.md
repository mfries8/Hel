# H-006: Unticked Signatures in the Radar Contract (`hel.radar` 1.2, `hel.results` 1.3)

## Status

Done (2026-10-25)

## Decisions

Fenrir F-027 (the maintainer, 2026-10-25): a sweep or blip unticked in
Fenrir or Gjallerhorn is recorded in the radar file, kept for the archive,
and left out of every calculation in every app until it is ticked again.
D10/D26 (one suite data contract).

## Context

Weather radars sometimes see the bright fireball itself, and some
signatures may be noise. Analysts untick them, but `hel.radar` 1.1 had no
field for it, so the choice was lost with the session and never reached
the other apps.

## Scope

- `hel.radar` **1.2** (MINOR: optional fields only): `Exclusion` (`reason`:
  `bright_flight`, `uncertain`, `artifact`, `not_this_fall` or `other`;
  `note`; `by`, the app; `at`, UTC) on `Sweep` and on `Blip`.
- `hel.results` **1.3**: an optional `excluded` list, the unticked
  signatures a run did not use (id, radar, sweep, reason, note).
- The reader rule, `hel.radar.excluded_sweeps`: a sweep with an exclusion,
  or whose blips are all excluded, is used in no calculation.
- Upgraded legacy files are stamped 1.2 (the expected upgrade outputs
  follow); the full golden file shows an excluded blip; schema, types,
  tests; package 1.6.0.

## Out Of Scope

- The apps' writing of the field (Fenrir F-027; Gjallerhorn's blip
  editor).

## Affected Files

- `src/hel/radar.py`, `src/hel/schemas/radar.schema.json`,
  `src/hel/types/hel.d.ts`, `src/hel/golden/current/radar_full.json`,
  `src/hel/golden/upgraded/radar_*.json`, `src/hel/__init__.py`,
  `pyproject.toml`, `docs/CONVENTIONS.md`
- `tests/test_contracts.py`, `tests/test_cli.py`, `tests/test_scaffold.py`
- `CHANGELOG.md`, `docs/KANBAN.md`, this SPEC

## Acceptance Criteria

- [x] Exclusions validate on sweeps and blips; an unknown reason is
      refused; a 1.1 file still validates.
- [x] `excluded_sweeps` applies the rule (tests).
- [x] `python tools/run_ci.py` passes.

## Verification Plan

- `python tools/run_ci.py`

## Verification Results

- `python tools/run_ci.py`: All checks passed (108 tests).

## Deviations

- Updated the expected upgrade outputs and the CLI test's version line
  (1.1 → 1.2), as the version change intends.

## Follow-Up Work Discovered

- None

## Checks Skipped

- None
