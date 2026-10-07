"""Repository rules that ruff, mypy and pytest don't cover.

Run by ``tools/run_ci.py`` (and so by CI) over every file git tracks:

1. **Forbidden names (suite rule, Fenrir D16 and Gjallerhorn G16).** Hel
   never names the suite's predecessor codebases, in code, docs, file names
   or anywhere else. To keep the names out of this checker too, forbidden
   words are stored only as SHA-256 hashes of their normalized spelling.
   Text is split into alphanumeric words, lower-cased, and accent-stripped
   (so a spelling with an umlaut matches too) before hashing.
2. **Large files (Fenrir D15).** Tracked files over ``MAX_FILE_BYTES`` fail,
   so radar volumes and survey outputs can't creep into the repository.
   Golden files are deliberately small.

Exit status is 0 when clean and 1 when any rule is violated. Each violation
is printed with its file (and line, for names).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# SHA-256 of the normalized forbidden words (see module docstring).
FORBIDDEN_WORD_HASHES: frozenset[str] = frozenset(
    {
        "b6f6a982dcc4aba2061e1dbd572f2c55fab9abf2cc597671c259424849713fff",
        "a499068b8f456a03adaf1064efe8fb54c8f0fd204468f27e168642eab19d883b",
        "77f1d1c04d32a84a569b4aed05ef453ec4f464fcac98de97bb2f5033df2c4a04",
    }
)

# 1 MB: comfortably above any source file, well below a radar volume (~4 MB+).
MAX_FILE_BYTES = 1_000_000

_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def normalize_word(word: str) -> str:
    """Return ``word`` lower-cased and stripped of accents.

    Args:
        word: One alphanumeric token.

    Returns:
        The ASCII-folded, lower-case form used for hashing, so that accented
        and unaccented spellings compare equal.
    """
    decomposed = unicodedata.normalize("NFKD", word.lower())
    return decomposed.encode("ascii", "ignore").decode("ascii")


def is_forbidden(word: str) -> bool:
    """Return True if ``word`` is one of the forbidden names.

    Args:
        word: One alphanumeric token, in any case, with or without accents.

    Returns:
        Whether the token's normalized hash is in ``FORBIDDEN_WORD_HASHES``.
    """
    digest = hashlib.sha256(normalize_word(word).encode("ascii")).hexdigest()
    return digest in FORBIDDEN_WORD_HASHES


def find_forbidden_words(text: str) -> list[tuple[int, str]]:
    """Find forbidden names in a block of text.

    Args:
        text: File contents or a file path.

    Returns:
        ``(line_number, word)`` pairs, with line numbers starting at 1.
    """
    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        hits.extend((line_no, w) for w in _WORD.findall(line) if is_forbidden(w))
    return hits


def tracked_files(root: Path) -> list[Path]:
    """List the files git tracks (plus staged new files) under ``root``.

    Args:
        root: The repository root.

    Returns:
        Absolute paths, in git's order.
    """
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [root / line for line in out.splitlines() if line.strip()]


def check(root: Path) -> list[str]:
    """Apply every rule to the repository at ``root``.

    Args:
        root: The repository root.

    Returns:
        Human-readable violation messages; empty when the repository is clean.
    """
    problems: list[str] = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if not path.is_file():
            continue
        for _line, word in find_forbidden_words(rel):
            problems.append(
                f"{rel}: forbidden name in file path ({word!r}), see the suite naming rule"
            )
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            problems.append(f"{rel}: {size:,} bytes exceeds {MAX_FILE_BYTES:,}, see Fenrir D15")
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary files: only the name and size rules apply
        for line_no, word in find_forbidden_words(text):
            problems.append(f"{rel}:{line_no}: forbidden name {word!r}, see the suite naming rule")
    return problems


def main() -> int:
    """Check the repository this script lives in and report violations.

    Returns:
        Process exit status: 0 when clean, 1 otherwise.
    """
    problems = check(REPO_ROOT)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} repository-rule violation(s).")
        return 1
    print("Repository rules: clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
