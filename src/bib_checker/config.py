"""Load bib-checker configuration (ignore list) from pyproject.toml or .bibcheckerignore."""

from __future__ import annotations

import tomllib
from pathlib import Path


def load_ignore_keys(bib_path: str | Path | None = None) -> set[str]:
    """Return the set of citation keys that should be skipped during checking.

    Keys are collected from two sources (both are read and merged):

    1. A ``.bibcheckerignore`` file — searched first next to *bib_path*,
       then in the current working directory.  Each non-blank, non-comment
       line is treated as a citation key to ignore.

    2. A ``[tool.bib-checker] ignore = [...]`` list in ``pyproject.toml`` —
       searched upward from the current working directory.

    Parameters
    ----------
    bib_path : str or Path, optional
        Path to the ``.bib`` file being checked.  When given, its parent
        directory is also searched for ``.bibcheckerignore``.

    Returns
    -------
    ignored : set[str]
        Citation keys to skip.
    """
    ignored: set[str] = set()

    # --- .bibcheckerignore --------------------------------------------------
    search_dirs: list[Path] = []
    if bib_path is not None:
        search_dirs.append(Path(bib_path).parent)
    cwd = Path.cwd()
    if not search_dirs or search_dirs[0] != cwd:
        search_dirs.append(cwd)

    for d in search_dirs:
        ignore_file = d / ".bibcheckerignore"
        if ignore_file.exists():
            for line in ignore_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    ignored.add(line)
            break  # first file found wins

    # --- pyproject.toml -----------------------------------------------------
    for candidate in [cwd, *cwd.parents]:
        pyproject = candidate / "pyproject.toml"
        if pyproject.exists():
            try:
                with pyproject.open("rb") as fh:
                    data = tomllib.load(fh)
                keys = data.get("tool", {}).get("bib-checker", {}).get("ignore", [])
                ignored.update(keys)
            except Exception:  # noqa: BLE001
                pass
            break

    return ignored
