"""Hel's verification baseline: the exact checks CI runs (Fenrir D12).

Run it locally before committing:

    python tools/run_ci.py

GitHub Actions calls this same script, so "passes locally" and "passes in
CI" mean the same thing. Steps stop at the first failure.

New steps are added here, never in the workflow file alone.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Coverage bar (Fenrir D12).
COVERAGE_FAIL_UNDER = 80

# The widget kit's checks run its tools through Node directly (no npm
# wrapper, so the same command works on Windows and Linux).
NODE = shutil.which("node") or "node"

STEPS: list[tuple[str, list[str]]] = [
    ("Repository rules (names, file sizes)", [sys.executable, "tools/check_repo_rules.py"]),
    (
        "Ruff lint (incl. docstring and annotation rules)",
        [sys.executable, "-m", "ruff", "check", "."],
    ),
    ("Ruff format check", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("Mypy (strict)", [sys.executable, "-m", "mypy"]),
    (
        "Generated schemas and TypeScript types are current",
        [sys.executable, "tools/generate_artifacts.py", "--check"],
    ),
    (
        "Widget kit type check (strict TypeScript)",
        [NODE, "node_modules/typescript/bin/tsc", "-p", "widgets/tsconfig.json"],
    ),
    (
        "Widget kit tests",
        [NODE, "node_modules/vitest/vitest.mjs", "run", "--root", "widgets"],
    ),
    (
        "Pytest with coverage",
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=hel",
            "--cov-report=term-missing",
            f"--cov-fail-under={COVERAGE_FAIL_UNDER}",
        ],
    ),
]


def run_step(name: str, command: list[str]) -> None:
    """Run one verification step from the repo root, exiting on failure.

    Args:
        name: Label printed before the step runs.
        command: The command and its arguments.
    """
    print(f"\n==> {name}", flush=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        print(f"\nFAILED: {name} (exit code {completed.returncode})")
        sys.exit(completed.returncode)


def main() -> None:
    """Run every verification step in order."""
    for name, command in STEPS:
        run_step(name, command)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
