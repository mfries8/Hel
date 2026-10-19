# H-002: Shared Widget Kit

## Status

Done

## Decisions

Fenrir D11 (frontend structure: a shared suite widget set), D11a (a small
package kept in Hel, copied by each app and pinned with a drift check, the
same mechanism as the contracts; starts from Gjallerhorn's widget kit),
Gjallerhorn G3 (FastAPI + React with Hel's shared widgets).

## Context

The suite's apps share one look: a dark "glass" theme with a sidebar of
inputs and a main area. The legacy radar app's React front end built that
look from a small set of components (headers, alerts, inputs, sliders,
buttons, a file drop zone, progress, dialogs, toasts, tables), each matching
one element of its earlier Streamlit interface. Fenrir's frontend (F-013)
is the first app to need them in the new suite; Gjallerhorn's (G-008)
follows.

## Scope

- `widgets/`: the kit, as TypeScript React source that apps copy:
  - `src/widgets.tsx`: `Header`, `Subheader`, `Caption`, `Divider`,
    `Alert`, `Spinner`, `Help`, `Metric`, `Radio`, `Select`, `TextInput`,
    `NumberInput`, `Slider`, `Checkbox`, `Button`, `FileDrop`, `Progress`,
    `Dialog`, `Toasts`, `DataTable`, `Tabs`, `Expander`, `StatusPill`;
  - `src/inline.tsx`: the small inline-markup renderer (bold, italic, code,
    links) the components use for text;
  - `src/hel-widgets.css`: the theme tokens and every component's styles,
    with a `hel-` class prefix;
  - `src/index.ts`: the public exports;
  - tests (Vitest, Testing Library) and a strict TypeScript check.
- `widgets/README.md`: what the kit holds and how an app pins a copy.
- Hel's CI runs the widget type check and tests.
- Release: a MINOR Hel version (contracts unchanged), tagged only after the
  maintainer confirms.

## Out Of Scope

- Maps and charts (each app chooses its own libraries).
- App layouts beyond the shared sidebar and main-area classes.

## Affected Files

- `widgets/**`, `package.json`, `package-lock.json`, `tools/run_ci.py`
- `README.md`, `docs/KANBAN.md`, `CHANGELOG.md`, `pyproject.toml` and
  `src/hel/__init__.py` (version), `tests/test_scaffold.py`, this SPEC

## Acceptance Criteria

- [x] Every component type-checks under strict TypeScript and has a test of
      its behaviour (rendering, input, events).
- [x] No predecessor name appears anywhere in the kit.
- [x] `python tools/run_ci.py` runs the widget checks and passes.
- [x] Tagged `v1.3.0` after the maintainer's go-ahead (2026-10-19); Fenrir pins the tag.

## Verification Plan

- `python tools/run_ci.py`

## Verification Results

- Pending

## Deviations

- None

## Follow-Up Work Discovered

- None

## Checks Skipped

- None
