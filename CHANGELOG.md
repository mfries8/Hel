# Changelog

All notable changes to Hel. Versions follow `MAJOR.MINOR.PATCH` for the
package. Each release lists the contract versions it defines.

## 1.6.0 (2026-10-25)

Contracts: `hel.radar` 1.2, `hel.results` 1.3 (`hel.event` 1.0,
`hel.seismo` 1.1 unchanged).

### Added

- `hel.radar` 1.2 (H-006, with Fenrir F-027): an optional `exclusion` on a
  sweep or blip the analyst unticked (reason, note, app, time), kept in the
  file and left out of every calculation; `hel.radar.excluded_sweeps` is
  the rule every reader applies.
- `hel.results` 1.3: `excluded`, the unticked signatures a run did not use.

## 1.5.0 (2026-10-25)

Contracts: `hel.results` 1.2 (`hel.event` 1.0, `hel.radar` 1.1, `hel.seismo`
1.1 unchanged).

### Added

- `hel.results` 1.2 (H-005, with Fenrir F-026a): the wind's share of each
  mass class's landing error (`uncertainty.error_table[].wind_share`) and
  the wind ensemble's record (`uncertainty.wind`: the members, whether the
  fit was re-run in each, and each re-fit's shift and cost).

## 1.4.2 (2026-10-25)

Contracts: as 1.4.0 (`hel.results` 1.1); the files are unchanged.

### Fixed

- `uncertainty.regions[].outlines` is typed as lists of `[lat, lon]` lists
  instead of tuples: generated TypeScript clients typed the same field as a
  tuple in one place and an array in another (found in Fenrir F-025b).

## 1.4.1 (2026-10-25)

Contracts: as 1.4.0 (`hel.results` 1.1).

### Fixed

- The package-version test, left at 1.3.0 in the 1.4.0 release (its CI
  failed on that test alone; the contracts are unchanged). Apps pin 1.4.1.

## 1.4.0 (2026-10-25)

Contracts: `hel.results` 1.1 (`hel.event` 1.0, `hel.radar` 1.1, `hel.seismo`
1.1 unchanged).

### Added

- `hel.results` 1.1 (H-004, with Fenrir F-025b): the optional `uncertainty`
  section (Level 1 probability areas per blip, per decadal mass class and
  for the fall; the search grid; parameter uncertainties and correlations;
  the error table; fit quality; the sources included and excluded), the
  search's `cost` and `blips_behind_terminus`, and the `uncertainty_kmz`
  and `areas_geojson` output files.

## 1.3.0 (2026-10-19)

Contracts: unchanged (`hel.event` 1.0, `hel.radar` 1.1, `hel.seismo` 1.1,
`hel.results` 1.0).

### Added

- The widget kit (H-002; `widgets/`): the suite's shared React components
  and dark theme, started from the legacy radar app's components, with a
  `hel-` class prefix and new `NumberInput`, `Tabs`, `Expander` and
  `StatusPill`. Strict TypeScript and Vitest checks in `tools/run_ci.py`.
  Apps copy `widgets/src/` from a tagged release and pin it.

## 1.2.0 (2026-10-15)

Contracts: `hel.event` 1.0, `hel.radar` 1.1, `hel.seismo` 1.1, `hel.results` 1.0.

### Added

- `hel.results` 1.0: Fenrir's results file (H-003, with Fenrir F-011b): the
  run, the entered inputs, the fitted terminus, Full Parameter Refinement's
  search diagnostics, the radar sweeps, every blip's mass, landing and
  diagnostics, forensics, the wind profile and the output files. Altitudes
  are heights above the WGS84 ellipsoid and masses kilograms (Fenrir D28).
  Minimal and full (Park Forest) golden examples.

### Changed

- The upgrader dispatches on a file's own `contract` header before guessing
  a legacy layout from its keys, so a results file (which has a `terminus`)
  is not mistaken for a legacy event file. A file whose header names an
  unknown contract is now rejected instead of being guessed from its keys.

## 1.1.0 (2026-10-06)

Contracts: `hel.event` 1.0, `hel.radar` 1.1, `hel.seismo` 1.1.

### Added

- `hel.radar` 1.1: optional pixel fields `velocity_time` and `dual_pol_time`
  (the oldest exports timed each product group separately) and
  `sweep_elevation` (a per-pixel copy some exports carry).
- The upgrader converts the oldest exports' per-product-group times (`timeR`,
  `timeV`, `timeD`, in seconds after midnight). Found in Fenrir's frozen
  Sutter's Mill and Park Forest inputs, which the archive survey had not
  covered. Both are now legacy golden samples.

## 1.0.0 (2026-10-06)

Contracts: `hel.event` 1.0, `hel.radar` 1.0, `hel.seismo` 1.1.

### Added

- The three contracts as pydantic models, with JSON Schemas and TypeScript
  types generated from them (H-001, under Fenrir F-003).
- The upgrader for every legacy layout in the recovered-falls archive, and
  the validator.
- The `hel` command (`validate`, `upgrade`, `versions`).
- Golden files: current examples, plus real legacy files with their expected
  upgrades.
- The conventions document, repository rules and CI.
