# Contributing to Hel

## Start here

- [docs/CONVENTIONS.md](docs/CONVENTIONS.md): the contract rules.
- [docs/KANBAN.md](docs/KANBAN.md): current work.
- AI agents also follow [AGENTS.md](AGENTS.md).

Hel's design decisions are recorded with the suite's other decisions in
Fenrir's decision log (D10, D10a, D11a, D16, D26).

## Rules that apply to every change

1. **Contracts are external interfaces.** Every app reads and writes these
   files.
   - Follow the version rules in CONVENTIONS.md: adding an optional field is
     MINOR; anything else is MAJOR.
   - Never edit a released version's meaning.
2. **Models are the source of truth.** Change the pydantic model, then
   regenerate the schemas and types with `python tools/generate_artifacts.py`.
   Never edit generated files by hand.
3. **Annotation standard (Fenrir D7).**
   - Every module, class and function has a docstring.
   - Every field's description gives its units, and its reference direction
     for angles.
   - Comments explain *why*.
4. **The upgrader never loses data silently.** Every change it makes is
   recorded in plain words, and unknown fields are kept.
5. **No predecessor names** (suite rule). Say "the legacy code".
   `tools/check_repo_rules.py` enforces this.
6. **Small repository.** Golden files are trimmed real examples; no file may
   exceed 1 MB.

## When a SPEC is required

- **Required:** contract changes, new contracts, upgrader changes, workflow
  or CI changes, and dependency changes.
- **Not required:** read-only work, and editorial documentation fixes.

SPECs follow [docs/TEMPLATE-SPEC.md](docs/TEMPLATE-SPEC.md), are numbered
`H-NNN`, and are archived in `docs/specs/done/`. Work driven by an app's SPEC
(for example Fenrir F-003, which created Hel v1) may be tracked in that app's
SPEC instead, with a pointer on this KANBAN.

## Verification baseline

```bash
python tools/run_ci.py
```

It runs the repository rules, ruff (lint and format), strict mypy, the
generated-artifact check, and pytest with the 80% coverage bar. CI runs the
same script on Linux for every push, and on Windows for pull requests and
nightly.

## Releases

Tag releases `vMAJOR.MINOR.PATCH` (the package version), and record in the
CHANGELOG which contract versions each release defines. Apps pin a tag.

## Git

- Stage only the files that belong to the change.
- Commit messages: `type: summary (SPEC)`, then a body explaining why.
