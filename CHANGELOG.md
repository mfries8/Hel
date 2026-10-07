# Changelog

All notable changes to Hel. Versions follow `MAJOR.MINOR.PATCH` for the
package. Each release lists the contract versions it defines.

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
