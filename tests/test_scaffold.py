"""Tests for the scaffold: package metadata and repository rules."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_repo_rules as rules  # noqa: E402
import hel  # noqa: E402


def _hash(word: str) -> str:
    return hashlib.sha256(rules.normalize_word(word).encode("ascii")).hexdigest()


def test_package_exposes_version() -> None:
    assert hel.__version__ == "1.4.1"


def test_normalize_word_folds_case_and_accents() -> None:
    assert rules.normalize_word("ÖsterReich") == "osterreich"


def test_forbidden_hashes_are_well_formed() -> None:
    # The suite's three predecessor names (Fenrir D16, Gjallerhorn G16).
    assert len(rules.FORBIDDEN_WORD_HASHES) == 3
    assert all(len(h) == 64 for h in rules.FORBIDDEN_WORD_HASHES)


def test_is_forbidden_matches_only_listed_hashes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Use a stand-in word so the test never contains a forbidden name itself.
    monkeypatch.setattr(rules, "FORBIDDEN_WORD_HASHES", frozenset({_hash("tyr")}))
    assert rules.is_forbidden("Tyr")
    assert rules.is_forbidden("TŸR")  # accents are folded before hashing
    assert not rules.is_forbidden("hel")


def test_find_forbidden_words_reports_line_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rules, "FORBIDDEN_WORD_HASHES", frozenset({_hash("tyr")}))
    text = "first line\nsee tyr_output/ here\nlast"
    assert rules.find_forbidden_words(text) == [(2, "tyr")]


def test_check_flags_names_paths_and_large_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rules, "FORBIDDEN_WORD_HASHES", frozenset({_hash("tyr")}))
    monkeypatch.setattr(rules, "MAX_FILE_BYTES", 10)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "ok.txt").write_text("fine", encoding="utf-8")
    (tmp_path / "named.txt").write_text("mentions Tyr once", encoding="utf-8")
    (tmp_path / "tyr_notes.md").write_text("x", encoding="utf-8")
    (tmp_path / "big.bin").write_bytes(b"\0" * 20)

    problems = rules.check(tmp_path)

    assert any(p.startswith("named.txt:1:") for p in problems)
    assert any(p.startswith("tyr_notes.md:") and "file path" in p for p in problems)
    assert any(p.startswith("big.bin:") and "exceeds" in p for p in problems)
    assert not any(p.startswith("ok.txt") for p in problems)


def test_repository_itself_is_clean() -> None:
    assert rules.check(REPO_ROOT) == []
