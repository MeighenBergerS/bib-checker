"""Tests for bib_checker.config."""

from __future__ import annotations

from pathlib import Path

from bib_checker.config import load_ignore_keys


def test_absent_config_returns_empty_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_ignore_keys() == set()


# ---------------------------------------------------------------------------
# .bibcheckerignore
# ---------------------------------------------------------------------------


def test_load_from_bibcheckerignore_in_cwd(tmp_path, monkeypatch):
    (tmp_path / ".bibcheckerignore").write_text("Key:2000ab\nKey:2001cd\n")
    monkeypatch.chdir(tmp_path)
    keys = load_ignore_keys()
    assert "Key:2000ab" in keys
    assert "Key:2001cd" in keys


def test_ignore_file_skips_comment_lines(tmp_path, monkeypatch):
    (tmp_path / ".bibcheckerignore").write_text("# a comment\nKey:2000ab\n")
    monkeypatch.chdir(tmp_path)
    keys = load_ignore_keys()
    assert "Key:2000ab" in keys
    assert len(keys) == 1


def test_ignore_file_skips_blank_lines(tmp_path, monkeypatch):
    (tmp_path / ".bibcheckerignore").write_text("\n\nKey:2000ab\n\n")
    monkeypatch.chdir(tmp_path)
    keys = load_ignore_keys()
    assert keys == {"Key:2000ab"}


def test_ignore_file_next_to_bib_takes_priority(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / ".bibcheckerignore").write_text("NearBib:2000ab\n")
    (tmp_path / ".bibcheckerignore").write_text("InCwd:2001cd\n")
    bib = subdir / "paper.bib"
    bib.touch()
    keys = load_ignore_keys(bib_path=bib)
    # The file next to the bib wins; CWD file is not read.
    assert "NearBib:2000ab" in keys


# ---------------------------------------------------------------------------
# pyproject.toml
# ---------------------------------------------------------------------------


def test_load_from_pyproject_toml(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.bib-checker]\nignore = ["Key:2002ef", "Key:2003gh"]\n'
    )
    monkeypatch.chdir(tmp_path)
    keys = load_ignore_keys()
    assert "Key:2002ef" in keys
    assert "Key:2003gh" in keys


def test_pyproject_without_bib_checker_section_is_ignored(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[tool.other]\nfoo = true\n")
    monkeypatch.chdir(tmp_path)
    assert load_ignore_keys() == set()


# ---------------------------------------------------------------------------
# Both sources merged
# ---------------------------------------------------------------------------


def test_both_sources_merged(tmp_path, monkeypatch):
    (tmp_path / ".bibcheckerignore").write_text("FromIgnore:2000ab\n")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.bib-checker]\nignore = ["FromToml:2001cd"]\n'
    )
    monkeypatch.chdir(tmp_path)
    keys = load_ignore_keys()
    assert "FromIgnore:2000ab" in keys
    assert "FromToml:2001cd" in keys
