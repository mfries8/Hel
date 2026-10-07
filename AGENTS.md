# Hel Agent Instructions

[CONTRIBUTING.md](CONTRIBUTING.md) owns the shared workflow. This file adds
agent-specific rules only.

## Rules

- **Never name the suite's predecessor codebases,** in anything you write,
  including commit messages. Say "the legacy code".
- **A contract change is a change to every app.** Check the version rules in
  docs/CONVENTIONS.md before changing a model, and say whether the change is
  MINOR or MAJOR.
- **Golden files are evidence.** Never regenerate an expected upgrade output
  just to make a test pass. Find out why it changed, and report it.
- **Don't weaken a failing check to make it pass.** Report the failure and
  its cause.
- Never overwrite or revert unrelated user changes.

## Handoff (for SPEC-scoped changes)

- `SPEC`, `STATUS`, `COMMIT`, `FILES CHANGED`
- `TESTS`, `TYPECHECK`, `LINT` (exact commands and results)
- `ACCEPTANCE CRITERIA`, `DEVIATIONS`
- `FOLLOW-UP WORK DISCOVERED`, `CHECKS SKIPPED`
